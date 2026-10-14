"""Builds the v3 position files from the self-play games and the v1 replay set.

Runs inside gnubg's embedded Python from the repo root (gnubg classifies the v1 positions):

    gnubg -t -q -p tools/v3/build.py

Reads seeds.json, positions/games/*.jsonl.gz (tools/v3/selfplay.py), replay.db and league.db
(read-only), and writes:

- positions/new.jsonl: 1,000 positions, 200 per phase, from the new-set games. The opening phase
  holds each of the 15 first-roll positions once (turn 1) and 185 positions from turns 2 to 6.
- positions/extension.jsonl: 4,000 positions, 800 per phase, from the extension games; no turn-1
  positions (all 15 are in the new set).
- positions/nackgammon.jsonl: 500 positions from Nackgammon games: 300 from turns 1 to 6, with 14
  of its 15 first-roll positions among them, and 200 from later turns. Its 3-2 first roll has 27
  legal plays, above the 2-to-25 rule, so it is left out and logged (agreed deviation).
- positions/opening-control.jsonl: the new set's 200 opening positions, prompt nack-v2.
- positions/v1.jsonl: the 1,000 v1 shared positions of replay.db, reshuffled.
- positions/build-log.json: counts per set and phase, holding counts, duplicates skipped.

Sampling rules: every position has 2 to 25 legal plays; each game gives at most one position per
phase (Nackgammon: one from turns 1-6 and one later); games are taken in order and, within a game
and phase, the turn is drawn at random (random.Random(f"{sampling_seed}:{set}:{game}:{phase}"));
duplicates are skipped across the new set and the extension, and within the Nackgammon set. A
duplicate is the same board seen by the mover with the same dice (GNUbg position ID + dice), which
is stricter than board + dice + side: the same decision for white and for black counts once. If a
phase cannot be filled from its games (holding positions may be scarce), all distinct ones are used
and the shortfall is logged.

Every row: id, set, variant, prompt (the prompt version: bg-v2, or nack-v2 without the opening
table), phase, tag, gnubg_class, position_id (GNUbg, mover on roll), position_key, dice, side,
turn, first_roll, source_game, legal_plays (runner notation, Board::legal_plays order for the dice
as listed), option_order (order.option_order with seeds.json's option_order_seed: option k shows
legal_plays[option_order[k]]), position (the runner's white-view JSON), race_deficit (holding only).
Generated sets list the dice high first; v1 rows keep the recorded dice order.
"""

import glob
import gzip
import json
import os
import random
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.getcwd(), "tools", "v3"))  # gnubg runs scripts without __file__

import classify  # noqa: E402
import engine  # noqa: E402
from order import option_order, position_key  # noqa: E402
from rules import from_json, legal_plays, start, to_json  # noqa: E402

MIN_PLAYS, MAX_PLAYS = 2, 25
OUT = "positions"


def eligible_first_rolls(variant):
    """The first rolls whose position has 2 to 25 legal plays, and the others with their counts.
    Standard: all 15. Nackgammon: 14; its 3-2 has 27 plays and is excluded (agreed deviation)."""
    ok, excluded = [], {}
    for hi in range(2, 7):
        for lo in range(1, hi):
            n = len(legal_plays(start(variant), hi, lo))
            if MIN_PLAYS <= n <= MAX_PLAYS:
                ok.append((hi, lo))
            else:
                excluded[f"{hi}-{lo}"] = n
    return ok, excluded


def load_games(variant):
    games = {}
    for path in sorted(glob.glob(f"{OUT}/games/{variant}-*.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            for line in f:
                g = json.loads(line)
                games[g["game"]] = g
    return games


def label(t):
    pos = (t["pts"], t["bar"], t["off"])
    ph = classify.phase(pos, t["cls"], t["t"])
    return pos, ph


def row(set_name, variant, prompt, seed, game, t, ph, pos):
    hi, lo = max(t["dice"]), min(t["dice"])
    plays = [n for n, _ in legal_plays(pos, hi, lo)]
    assert len(plays) == t["n"]
    pkey = position_key(t["pid"], hi, lo, t["side"])
    r = {"id": None, "set": set_name, "variant": variant, "prompt": prompt, "phase": ph,
         "tag": classify.tag(pos, ph), "gnubg_class": t["cls"], "position_id": t["pid"],
         "position_key": pkey, "dice": [hi, lo], "side": t["side"], "turn": t["t"],
         "first_roll": t["t"] == 1, "source_game": f"{variant}:{game}", "legal_plays": plays,
         "option_order": option_order(seed, pkey, len(plays)), "position": to_json(pos, t["side"])}
    if ph == "holding":
        r["race_deficit"] = classify.race_deficit(pos)
    return r


def dedupe_key(t):
    return (t["pid"], max(t["dice"]), min(t["dice"]))


def sample_standard(set_name, games, lo, hi, quota, first_rolls, seen, seeds, log):
    """Fills `quota` positions per phase from games lo..hi-1. With first_rolls, the opening phase
    takes each of the 15 first-roll positions once; otherwise turn 1 is excluded."""
    taken = {ph: [] for ph in classify.PHASES}
    rolls = set()
    eligible, excluded = eligible_first_rolls("standard")
    n_first = len(eligible)
    dupes = 0
    used = lo
    for game in range(lo, hi):
        if game not in games:
            continue
        if all(len(taken[ph]) >= quota for ph in classify.PHASES):
            break
        used = game + 1
        by_phase = {ph: [] for ph in classify.PHASES}
        for t in games[game]["turns"]:
            if MIN_PLAYS <= t["n"] <= MAX_PLAYS:
                pos, ph = label(t)
                by_phase[ph].append((t, pos))
        for ph, cands in by_phase.items():
            rng = random.Random(f"{seeds['sampling_seed']}:{set_name}:{game}:{ph}")
            rng.shuffle(cands)
            if ph == "opening":
                first = [c for c in cands if c[0]["t"] == 1]
                cands = [c for c in cands if c[0]["t"] != 1]
                roll = first and (max(first[0][0]["dice"]), min(first[0][0]["dice"]))
                if first_rolls and first and roll not in rolls:
                    k = dedupe_key(first[0][0])
                    if k not in seen:
                        rolls.add(roll)
                        seen.add(k)
                        taken[ph].append((game, *first[0]))
                        continue
                limit = quota - (n_first - len(rolls) if first_rolls else 0)
            else:
                limit = quota
            if len(taken[ph]) >= limit:
                continue
            for t, pos in cands:
                k = dedupe_key(t)
                if k in seen:
                    dupes += 1
                    continue
                seen.add(k)
                taken[ph].append((game, t, pos))
                break
    rows = []
    for ph in classify.PHASES:
        for game, t, pos in taken[ph]:
            rows.append(row(set_name, "standard", "bg-v2", seeds["option_order_seed"], game, t, ph, pos))
    log[set_name] = {"games_used": [lo, used], "per_phase": {ph: len(taken[ph]) for ph in classify.PHASES},
                     "first_roll_positions": len(rolls) if first_rolls else 0,
                     "first_rolls_excluded": excluded if first_rolls else {},
                     "holding_found": len(taken["holding"]), "holding_quota": quota,
                     "duplicates_skipped": dupes}
    if len(taken["holding"]) < quota:
        log[set_name]["holding_note"] = f"only {len(taken['holding'])} distinct holding positions; all used"
    for ph in classify.PHASES:
        if ph != "holding" and len(taken[ph]) < quota:
            raise RuntimeError(f"{set_name}: phase {ph} has {len(taken[ph])} of {quota}; play more games")
    if first_rolls and len(rolls) < n_first:
        raise RuntimeError(f"{set_name}: {len(rolls)} of {n_first} first-roll positions; play more games")
    return rows


def sample_nackgammon(games, lo, hi, seeds, log, early_quota=300, late_quota=200):
    early, late, rolls, seen = [], [], set(), set()
    eligible, excluded = eligible_first_rolls("nackgammon")
    n_first = len(eligible)
    dupes = 0
    for game in range(lo, hi):
        if game not in games:
            continue
        if len(early) >= early_quota and len(late) >= late_quota:
            break
        cands = {"early": [], "late": []}
        for t in games[game]["turns"]:
            if MIN_PLAYS <= t["n"] <= MAX_PLAYS:
                pos, ph = label(t)
                cands["early" if t["t"] <= classify.OPENING_TURNS else "late"].append((t, pos, ph))
        for part, items in cands.items():
            rng = random.Random(f"{seeds['sampling_seed']}:nackgammon:{game}:{part}")
            rng.shuffle(items)
            if part == "early":
                first = [c for c in items if c[0]["t"] == 1]
                items = [c for c in items if c[0]["t"] != 1]
                if first:
                    roll = (max(first[0][0]["dice"]), min(first[0][0]["dice"]))
                    if roll not in rolls and dedupe_key(first[0][0]) not in seen:
                        rolls.add(roll)
                        seen.add(dedupe_key(first[0][0]))
                        early.append((game, *first[0]))
                        continue
                if len(early) >= early_quota - (n_first - len(rolls)):
                    continue
                bucket = early
            else:
                if len(late) >= late_quota:
                    continue
                bucket = late
            for t, pos, ph in items:
                k = dedupe_key(t)
                if k in seen:
                    dupes += 1
                    continue
                seen.add(k)
                bucket.append((game, t, pos, ph))
                break
    if len(early) < early_quota or len(late) < late_quota or len(rolls) < n_first:
        raise RuntimeError(f"nackgammon: {len(early)} early, {len(late)} late, {len(rolls)} first rolls")
    rows = [row("nackgammon", "nackgammon", "nack-v2", seeds["option_order_seed"], g, t, ph, pos)
            for g, t, pos, ph in early + late]
    phases = {}
    for r in rows:
        phases[r["phase"]] = phases.get(r["phase"], 0) + 1
    log["nackgammon"] = {"games_used": [lo, max(g for g, *_ in early + late) + 1], "turns_1_to_6": len(early),
                         "later_turns": len(late), "first_roll_positions": len(rolls),
                         "first_rolls_excluded": excluded, "per_phase": phases,
                         "duplicates_skipped": dupes}
    return rows


def v1_rows(seeds, log):
    """The 1,000 v1 shared positions (replay.db), with phase labels and the seeded option order."""
    rdb = sqlite3.connect("file:replay.db?mode=ro", uri=True)
    ldb = sqlite3.connect("file:league.db?mode=ro", uri=True)
    rows, mismatched = [], []
    for pid, turn_id, league_id, position, side, d1, d2, options in rdb.execute(
            "SELECT id, turn_id, league_id, position, side, die1, die2, options FROM positions ORDER BY id"):
        turn_no, game_id = ldb.execute("SELECT turn_no, game_id FROM turns WHERE id = ?", (turn_id,)).fetchone()
        # replay.db stores the options as a JSON object with sorted keys, not in generation order;
        # the rows list them in Board::legal_plays order like every other set, after checking
        # that the plays are the same.
        stored = set(json.loads(options))
        pos = from_json(json.loads(position), side)
        plays = [n for n, _ in legal_plays(pos, d1, d2)]
        if set(plays) != stored:
            mismatched.append(pid)
        cls = engine.classify(pos)
        ph = classify.phase(pos, cls, turn_no)
        gid = engine.position_id(pos)
        pkey = position_key(gid, d1, d2, side)
        r = {"id": f"v1-{pid:04d}", "set": "v1", "variant": "standard", "prompt": "bg-v2", "phase": ph,
             "tag": classify.tag(pos, ph), "gnubg_class": cls, "position_id": gid, "position_key": pkey,
             "dice": [d1, d2], "side": side, "turn": turn_no, "first_roll": turn_no == 1,
             "source_game": f"league.db:{game_id}", "source_turn_id": turn_id, "league_id": league_id,
             "replay_position_id": pid, "legal_plays": plays,
             "option_order": option_order(seeds["option_order_seed"], pkey, len(plays)),
             "position": json.loads(position)}
        if ph == "holding":
            r["race_deficit"] = classify.race_deficit(pos)
        rows.append(r)
    phases = {}
    for r in rows:
        phases[r["phase"]] = phases.get(r["phase"], 0) + 1
    log["v1"] = {"positions": len(rows), "per_phase": phases, "games": len({r["source_game"] for r in rows}),
                 "legal_plays_differ_from_stored": mismatched}
    if mismatched:
        raise RuntimeError(f"v1: legal plays differ from replay.db for {len(mismatched)} positions")
    return rows


def write(name, rows, prefix):
    for i, r in enumerate(rows, 1):
        if r["id"] is None:
            r["id"] = f"{prefix}-{i:04d}"
    with open(f"{OUT}/{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


def main():
    t0 = time.time()
    with open("seeds.json") as f:
        seeds_all = json.load(f)
    seeds = dict(seeds_all["positions"], option_order_seed=seeds_all["option_order_seed"])
    log = {}
    std = load_games("standard")
    seen = set()
    new = sample_standard("new", std, *seeds["new_set_games"], 200, True, seen, seeds, log)
    ext = sample_standard("extension", std, *seeds["extension_games"], 800, False, seen, seeds, log)
    write("new", new, "new")
    write("extension", ext, "ext")
    control = [dict(r, id=r["id"].replace("new-", "ctl-"), set="opening-control", prompt="nack-v2",
                    paired_with=r["id"]) for r in new if r["phase"] == "opening"]
    write("opening-control", control, "ctl")
    log["opening-control"] = {"positions": len(control), "first_roll_positions": sum(r["first_roll"] for r in control)}
    nack = sample_nackgammon(load_games("nackgammon"), *seeds["nackgammon_games"], seeds, log)
    write("nackgammon", nack, "nack")
    write("v1", v1_rows(seeds, log), "v1")
    # build-log.json is hashed at the freeze, so it holds no timings.
    with open(f"{OUT}/build-log.json", "w") as f:
        json.dump(log, f, indent=2)
        f.write("\n")
    print(json.dumps(log, indent=2), flush=True)
    print(f"built in {time.time() - t0:.1f} s", flush=True)


try:
    main()
    os._exit(0)
except Exception:
    import traceback
    traceback.print_exc()
    os._exit(1)
