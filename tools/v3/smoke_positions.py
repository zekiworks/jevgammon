"""Draws the 50 smoke-test positions (design, run order step 1): 10 per phase from expert
self-play games that no shared set uses, so the smoke answers never overlap the frozen sets.

    python3 tools/v3/smoke_positions.py            # writes positions/smoke.jsonl

Games 11000-11999 of the standard self-play run (seeds.json; positions/games/) are taken in order;
the extension set stops near game 6000 and the new set before game 1000. Each game gives at most
one position per phase, drawn with random.Random(f"{sampling_seed}:smoke:{game}:{phase}"); turn 1
is left out (all 15 first-roll positions are in the new set) and every position has 2 to 25 legal
plays. A position (GNUbg ID + dice) that appears in any positions/*.jsonl set is skipped. Rows have
the same fields as the shared sets (tools/v3/build.py), with set "smoke".

Standard library only (the gnubg class of every turn is stored in the game files).
"""

import glob
import gzip
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import classify  # noqa: E402
from order import option_order, position_key  # noqa: E402
from rules import legal_plays, to_json  # noqa: E402

GAMES = (11000, 12000)
PER_PHASE = 10
SHARED = ["new", "extension", "nackgammon", "v1", "opening-control"]


def main():
    with open("seeds.json") as f:
        seeds = json.load(f)
    sampling, order_seed = seeds["positions"]["sampling_seed"], seeds["option_order_seed"]
    seen = set()
    for name in SHARED:
        with open(f"positions/{name}.jsonl") as f:
            for line in f:
                r = json.loads(line)
                seen.add((r["position_id"], max(r["dice"]), min(r["dice"])))
    games = {}
    for path in sorted(glob.glob("positions/games/standard-*.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            for line in f:
                g = json.loads(line)
                if GAMES[0] <= g["game"] < GAMES[1]:
                    games[g["game"]] = g
    taken = {ph: [] for ph in classify.PHASES}
    for game in sorted(games):
        if all(len(v) >= PER_PHASE for v in taken.values()):
            break
        by_phase = {ph: [] for ph in classify.PHASES}
        for t in games[game]["turns"]:
            if t["t"] > 1 and 2 <= t["n"] <= 25:
                pos = (t["pts"], t["bar"], t["off"])
                by_phase[classify.phase(pos, t["cls"], t["t"])].append((t, pos))
        for ph, cands in by_phase.items():
            if len(taken[ph]) >= PER_PHASE:
                continue
            random.Random(f"{sampling}:smoke:{game}:{ph}").shuffle(cands)
            for t, pos in cands:
                key = (t["pid"], max(t["dice"]), min(t["dice"]))
                if key in seen:
                    continue
                seen.add(key)
                taken[ph].append((game, t, pos))
                break
    rows = []
    for ph in classify.PHASES:
        if len(taken[ph]) < PER_PHASE:
            raise SystemExit(f"phase {ph}: only {len(taken[ph])} positions")
        for game, t, pos in taken[ph]:
            hi, lo = max(t["dice"]), min(t["dice"])
            plays = [n for n, _ in legal_plays(pos, hi, lo)]
            assert len(plays) == t["n"]
            pkey = position_key(t["pid"], hi, lo, t["side"])
            r = {"id": f"smoke-{len(rows) + 1:04d}", "set": "smoke", "variant": "standard",
                 "prompt": "bg-v2", "phase": ph, "tag": classify.tag(pos, ph), "gnubg_class": t["cls"],
                 "position_id": t["pid"], "position_key": pkey, "dice": [hi, lo], "side": t["side"],
                 "turn": t["t"], "first_roll": False, "source_game": f"standard:{game}",
                 "legal_plays": plays, "option_order": option_order(order_seed, pkey, len(plays)),
                 "position": to_json(pos, t["side"])}
            if ph == "holding":
                r["race_deficit"] = classify.race_deficit(pos)
            rows.append(r)
    with open("positions/smoke.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    print(f"{len(rows)} positions from games {min(g for g, *_ in sum(taken.values(), []))}-"
          f"{max(g for g, *_ in sum(taken.values(), []))}")


if __name__ == "__main__":
    main()
