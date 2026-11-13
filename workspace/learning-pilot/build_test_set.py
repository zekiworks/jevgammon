"""Learning pilot: the fixed evaluation set (200 League 2 positions: 100 Risk wins, 100 Safety wins).

Source: the Clear-risk scan's kept decisions (workspace/clearrisk-scratch/ana3.json `kept`; method and amendments in
mailbox/Clear-risk scan - method 2026-10-29.md): best unsafe play (12+ hitting rolls) against best safe play (0 hitting
rolls), |gap| >= 0.04 at 2-ply and at 3-ply, same direction, |gap3 - gap2| <= 0.02. League 2 decisions only.

Exclusions, in this order (counted): one legal play (none in the scan: it skips 1 and 2 legal plays); a repeated
position (board from the mover's side + dice; the first decision by turn id is kept); a position whose class by the
site's rule (tools/site/analysis.py play_call, margin 0.001) disagrees with its scan group (Risk wins must be the
site's Risk pays, Safety wins its Safety pays), so that "risks found" and "right safety" use the site's definitions on
every position. Then `random.Random(SEED).sample(pool, 100)` per group, Risk wins first.

Reads v3.db read-only and the site's 2-ply play scores. Writes test_set.json and test_positions.jsonl (`ask` input).
"""

import glob
import hashlib
import json
import os
import random
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "v3"))
from rules import from_json, key  # noqa: E402

SEED = 20261107
MARGIN = 0.001
PER_GROUP = 100
OUT = Path(__file__).resolve().parent
PLAYS = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "bg-site" / "plays"
SCAN = ROOT / "workspace/clearrisk-scratch/ana3.json"


def board_key(position_json: dict, side: str) -> str:
    """Position id for the leakage rule: the board from the mover's side (dice not included)."""
    return hashlib.sha1(repr(key(from_json(position_json, side))).encode()).hexdigest()[:16]


def site_class(shots, losses):
    least = min(shots)
    if all(s == least for s in shots):
        return "none", None
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    return ("safety" if stake < MARGIN else "risk"), stake


def main():
    kept = [k for k in json.loads(SCAN.read_text())["kept"] if k["league"] == 2]
    want = {k["turn"] for k in kept}
    scored = {}
    for path in sorted(glob.glob(str(PLAYS / "s*.db"))):
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for tid, n, data in db.execute("SELECT turn_id, n, data FROM plays"):
            if tid in want:
                scored[tid] = (n, data)
        db.close()
    v3 = sqlite3.connect(f"file:{ROOT / 'v3.db'}?mode=ro", uri=True)
    v3.row_factory = sqlite3.Row
    turns = {}
    ids = sorted(want)
    for i in range(0, len(ids), 900):
        ch = ids[i:i + 900]
        for r in v3.execute(f"""
            SELECT t.id, t.game_id, t.turn_no, t.side, t.player, t.die1, t.die2, t.position, t.option_order,
                   t.prompt_version, g.round_no, g.leg, g.match_id, m.rounds_planned, m.max_turns
            FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
            WHERE t.id IN ({','.join('?' * len(ch))})""", ch):
            turns[r["id"]] = r
    # Score shown at the start of each game (winner_player is the match side; mirror_concurrent shows the round start).
    games = v3.execute("SELECT g.id, g.match_id, g.leg, g.winner_player, g.points, COALESCE(m.mirror_concurrent, 0) "
                       "FROM games g JOIN matches m ON m.id = g.match_id ORDER BY g.match_id, g.round_no, g.leg").fetchall()
    start_score, running, round_start = {}, {}, {}
    for gid, mid, leg, winner, points, mc in games:
        s = running.setdefault(mid, [0, 0])
        if leg == 1:
            round_start[mid] = tuple(s)
        start_score[gid] = round_start[mid] if mc else tuple(s)
        if winner is not None and points:
            s[winner - 1] += points

    skips = Counter()
    seen, pool = set(), {"risk": [], "safety": []}
    for k in sorted(kept, key=lambda k: k["turn"]):
        r = turns[k["turn"]]
        n, data = scored[k["turn"]]
        if n < 2:
            skips["one legal play"] += 1
            continue
        pos = json.loads(r["position"])
        bk = board_key(pos, r["side"])
        pkey = f"{bk}:{r['die1']}{r['die2']}"
        if pkey in seen:
            skips["repeated position"] += 1
            continue
        seen.add(pkey)
        data = json.loads(data)
        eq = [d[1] for d in data]
        best = max(eq)
        losses = [best - e for e in eq]
        shots = [d[2] for d in data]
        group = "risk" if k["kind"] == "risk" else "safety"
        cls, stake = site_class(shots, losses)
        if cls != group:
            skips[f"{'Risk' if group == 'risk' else 'Safety'} wins but site class {cls}"] += 1
            continue
        my, opp = start_score[r["game_id"]]
        if r["player"] == 2:
            my, opp = opp, my
        pool[group].append(dict(
            id=f"lp-{r['id']}", turn_id=r["id"], board_key=bk, cls=group, stake=stake, gap2=k["gap"], gap3=k["g3"],
            position=pos, side=r["side"], dice=[r["die1"], r["die2"]], player=r["player"],
            round=r["round_no"], rounds=max(r["rounds_planned"], r["round_no"]), leg=r["leg"], turn_no=r["turn_no"],
            max_turns=r["max_turns"], my_score=my, opp_score=opp, prompt=r["prompt_version"] or "bg-v2",
            legal_plays=[d[0] for d in data], option_order=json.loads(r["option_order"]) if r["option_order"] else None,
            equities=eq, losses=losses, shots=shots, best=eq.index(best)))
    rng = random.Random(SEED)
    chosen = []
    for group in ("risk", "safety"):
        chosen += rng.sample(pool[group], PER_GROUP)
    meta = dict(seed=SEED, margin=MARGIN, source="Clear-risk scan kept decisions, League 2 (ana3.json)",
                kept_league2=dict(Counter(k["kind"] for k in kept)), skips=dict(skips),
                pool=dict(risk=len(pool["risk"]), safety=len(pool["safety"])), n=len(chosen))
    (OUT / "test_set.json").write_text(json.dumps(dict(meta=meta, positions=chosen), indent=1))
    with open(OUT / "test_positions.jsonl", "w") as f:
        for p in chosen:
            row = {k: p[k] for k in ("id", "position", "dice", "player", "round", "rounds", "leg", "turn_no",
                                     "max_turns", "my_score", "opp_score", "prompt", "legal_plays", "option_order")}
            row["set"] = "learning-pilot"
            row["clock"] = None
            f.write(json.dumps(row) + "\n")
    print(json.dumps(meta))


main()
