"""Learning pilot, step 1: the fixed test set (200 League 2 positions, 100 Risk pays + 100 Safety pays).

Reads v3.db read-only and the site's GNUbg 2-ply play scores ($XDG_STATE_HOME/bg-site/plays/s*.db).
Position class as the site (tools/site/analysis.py play_call): hitting rolls as shown to the model, stake = the
best safe play's equity loss against the engine's best play; 'safety' when stake < 0.001, else 'risk'; 'none'
(no trade-off) when every legal play leaves the same number of hitting rolls. One decision per distinct
position (board from the mover's side + dice); positions with one legal play are skipped. Fixed seed.

Writes workspace/learning-pilot/test_set.json and test_positions.jsonl (the `jevgammon ask` input).
"""

import glob
import hashlib
import json
import os
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "v3"))
from rules import from_json, key  # noqa: E402

SEED = 20261107
MARGIN = 0.001
PER_CLASS = 100
OUT = Path(__file__).resolve().parent
PLAYS = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "bg-site" / "plays"


def board_key(position_json: dict, side: str) -> str:
    """Position id used for leakage checks: the board from the mover's side (dice not included)."""
    return hashlib.sha1(repr(key(from_json(position_json, side))).encode()).hexdigest()[:16]


def classify(shots, losses):
    least = min(shots)
    if all(s == least for s in shots):
        return "none", None
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    return ("safety" if stake < MARGIN else "risk"), stake


def main():
    scored = {}
    for path in sorted(glob.glob(str(PLAYS / "s*.db"))):
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for tid, n, data in db.execute("SELECT turn_id, n, data FROM plays WHERE league_id = 2 AND n > 1"):
            scored[tid] = (n, data)
        db.close()
    v3 = sqlite3.connect(f"file:{ROOT / 'v3.db'}?mode=ro", uri=True)
    v3.row_factory = sqlite3.Row
    rows = v3.execute("""
        SELECT t.id, t.game_id, t.turn_no, t.side, t.player, t.die1, t.die2, t.position, t.legal_count,
               t.option_order, t.prompt_version, g.round_no, g.leg, g.match_id, m.rounds_planned, m.max_turns
        FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
        WHERE t.decided_by IN ('model', 'fallback') ORDER BY t.id""").fetchall()
    # Score shown at the start of each game: points of the match's earlier games (runner order: round, leg;
    # winner_player is the match side 1/2). With mirror_concurrent both games of a round show the round-start score.
    games = v3.execute("SELECT g.id, g.match_id, g.round_no, g.leg, g.winner_player, g.points, "
                       "COALESCE(m.mirror_concurrent, 0) AS mc FROM games g JOIN matches m ON m.id = g.match_id "
                       "ORDER BY g.match_id, g.round_no, g.leg").fetchall()
    start_score, running, round_start = {}, {}, {}
    for g in games:
        s = running.setdefault(g["match_id"], [0, 0])
        if g["leg"] == 1:
            round_start[g["match_id"]] = tuple(s)
        start_score[g["id"]] = round_start[g["match_id"]] if g["mc"] else tuple(s)
        if g["winner_player"] is not None and g["points"]:
            s[g["winner_player"] - 1] += g["points"]

    seen, pool = set(), {"risk": [], "safety": []}
    for r in rows:
        if r["id"] not in scored:
            continue
        n, data = scored[r["id"]]
        data = json.loads(data)
        eq = [d[1] for d in data]
        best = max(eq)
        losses = [best - e for e in eq]
        shots = [d[2] for d in data]
        cls, stake = classify(shots, losses)
        if cls == "none":
            continue
        pos = json.loads(r["position"])
        bk = board_key(pos, r["side"])
        pkey = f"{bk}:{r['die1']}{r['die2']}"
        if pkey in seen:
            continue
        seen.add(pkey)
        my, opp = start_score[r["game_id"]]
        if r["player"] == 2:
            my, opp = opp, my
        pool[cls].append(dict(
            id=f"lp-{r['id']}", turn_id=r["id"], board_key=bk, cls=cls, stake=stake,
            position=pos, side=r["side"], dice=[r["die1"], r["die2"]], player=r["player"],
            round=r["round_no"], rounds=max(r["rounds_planned"], r["round_no"]), leg=r["leg"], turn_no=r["turn_no"],
            max_turns=r["max_turns"], my_score=my, opp_score=opp, prompt=r["prompt_version"] or "bg-v2",
            legal_plays=[d[0] for d in data], option_order=json.loads(r["option_order"]) if r["option_order"] else None,
            equities=eq, losses=losses, shots=shots, best=eq.index(best)))
    rng = random.Random(SEED)
    chosen = []
    for cls in ("risk", "safety"):
        chosen += rng.sample(pool[cls], PER_CLASS)
    meta = dict(seed=SEED, margin=MARGIN, source="v3.db League 2 (plays.league_id = 2) decisions, 2-ply site scores",
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
