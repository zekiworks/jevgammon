"""Exports the positions for the x86-vs-ARM check to data/positions.json (plain Python 3).

- `v1`: the 1,000 v1 positions of replay.db (positions table), with every play's 2-ply equity
  and loss from its equities table (tools/gnubg_eval.py).
- `v3`: every decision the anchor (spec `gnubg-weak`) made in v3.db, with the index the runner
  recorded (turns.chosen_index, into Board::legal_plays order = tools/v3/rules.py legal_plays).

Both databases are opened read-only.
"""

import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def ro(name):
    return sqlite3.connect(f"file:{os.path.join(REPO, name)}?mode=ro", uri=True)


replay = ro("replay.db")
equities = {}
for pid, play, eq, loss in replay.execute("SELECT position_id, play, equity, loss FROM equities"):
    equities.setdefault(pid, {})[play] = [eq, loss]
v1 = [{"id": pid, "position": json.loads(p), "side": side, "dice": [d1, d2],
       "equities": equities[pid]}
      for pid, p, side, d1, d2 in replay.execute(
          "SELECT id, position, side, die1, die2 FROM positions ORDER BY id")]

v3db = ro("v3.db")
v3 = [{"turn_id": tid, "match_id": mid, "position": json.loads(p), "side": side,
       "dice": [d1, d2], "chosen_index": ci, "legal_count": n}
      for tid, mid, p, side, d1, d2, ci, n in v3db.execute("""
          SELECT t.id, m.id, t.position, t.side, t.die1, t.die2, t.chosen_index, t.legal_count
          FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
          WHERE t.decided_by = 'model'
            AND ((m.model1 = 'gnubg-weak' AND t.player = 1)
              OR (m.model2 = 'gnubg-weak' AND t.player = 2))
          ORDER BY t.id""")]

os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
with open(os.path.join(HERE, "data", "positions.json"), "w") as f:
    json.dump({"v1": v1, "v3": v3}, f)
print(f"v1 {len(v1)} positions, v3 {len(v3)} anchor decisions")
