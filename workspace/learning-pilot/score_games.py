"""Learning pilot: scores every model decision of the pilot games at 2-ply, as tools/site/score_plays.py does for
the leagues (same rules, engine, ply and descriptions). Runs inside gnubg's embedded Python from the repo root:

    SCORE_ARGS="smoke/learning-pilot.db smoke/learning-pilot-plays.db" gnubg -t -q -p workspace/learning-pilot/score_games.py

Incremental: decisions already in `plays` or `skipped` are not scored again. `data` holds, in legal order,
[notation, equity_2ply, hitting_rolls, description]; `board_key` is the pilot's position id (mover's board).
"""

import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "tools", "v3"))
sys.path.insert(0, os.path.join(ROOT, "tools", "site"))

from classify import phase, tag  # noqa: E402
from describe import describe_with_shots  # noqa: E402
from engine import PLY2, classify, equity, position_id  # noqa: E402
from rules import apply_notation, from_json, key, legal_plays  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS plays (
    turn_id INTEGER PRIMARY KEY, match_id INTEGER, game_id INTEGER, n INTEGER, chosen INTEGER, best REAL, loss REAL,
    gnubg_class INTEGER, phase TEXT, tag TEXT, board_key TEXT, gnubg_position_id TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS skipped (turn_id INTEGER PRIMARY KEY, reason TEXT);
"""


def skip_reason(plays, legal_count, chosen_index, move, pos):
    if len(plays) != legal_count:
        return f"{len(plays)} plays, stored {legal_count}"
    after = apply_notation(pos, move)
    index = None if after is None else next((i for i, (_, r) in enumerate(plays) if key(r) == key(after)), None)
    if index is None:
        return f"chosen play {move} not legal"
    if index != chosen_index:
        return f"chosen play {move} is play {index}, stored chosen_index {chosen_index}"
    return None


def main():
    args = os.environ["SCORE_ARGS"].split()
    src, dst = args[0], args[1]
    only = int(args[2]) if len(args) > 2 else None
    db = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
    out = sqlite3.connect(dst, timeout=60)
    out.executescript(SCHEMA)
    done = {r[0] for r in out.execute("SELECT turn_id FROM plays UNION SELECT turn_id FROM skipped")}
    rows = db.execute("""
        SELECT t.id, g.match_id, t.game_id, t.turn_no, t.side, t.die1, t.die2, t.move, t.legal_count,
               t.chosen_index, t.position
        FROM turns t JOIN games g ON g.id = t.game_id
        WHERE t.decided_by IN ('model', 'fallback') AND t.player = 1 AND (? IS NULL OR g.match_id = ?)
        ORDER BY t.id""", (only, only)).fetchall()
    db.close()
    n = 0
    for tid, mid, gid, turn_no, side, d1, d2, move, legal, chosen, position in rows:
        if tid in done:
            continue
        pos = from_json(json.loads(position), side)
        plays = legal_plays(pos, d1, d2)
        reason = skip_reason(plays, legal, chosen, move, pos)
        if reason:
            out.execute("INSERT INTO skipped VALUES (?, ?)", (tid, reason))
            continue
        data = []
        for play in plays:
            text, shots = describe_with_shots(pos, play)
            data.append([play[0], equity(play[1], PLY2), shots, text])
        best = max(d[1] for d in data)
        cls = classify(pos)
        ph = phase(pos, cls, turn_no)
        bk = hashlib.sha1(repr(key(pos)).encode()).hexdigest()[:16]
        out.execute("INSERT INTO plays VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (tid, mid, gid, legal, chosen, best, best - data[chosen][1], cls, ph, tag(pos, ph), bk,
                     position_id(pos), json.dumps(data, separators=(",", ":"))))
        n += 1
        out.commit()
    out.commit()
    print(f"{n} decisions scored", flush=True)


main()
