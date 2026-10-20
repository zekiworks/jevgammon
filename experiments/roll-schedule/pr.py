"""True strength of gnubg configurations: error rate on the v1 set (replay.db, 1,000 positions
with every option's 2-ply equity from tools/gnubg_eval.py), PR = 500 x mean equity loss.

    RS_DIR=<this folder> RS_PR_ARGS="OUT.json NAME..." nice -n 19 gnubg -t -q -p pr.py

Non-deterministic noise is sampled SAMPLES times per position. Positions and equities are read
from replay.db read-only.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.environ["RS_DIR"])

from common import REPO, ctx  # noqa: E402

import gnubg  # noqa: E402

from engine import CUBE  # noqa: E402
from rules import apply_gnubg_move, apply_notation, from_json, gnubg_board, key  # noqa: E402

SAMPLES = 5
CANDIDATES = {f"0p n{n:.3f}": ctx(0, n) for n in
              (0.0, 0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050, 0.055,
               0.060, 0.070, 0.080, 0.100, 0.120)}
CANDIDATES.update({
    "1p n0.000": ctx(1, 0.0),
    "1p prune n0.000": ctx(1, 0.0, prune=1),
    "1p n0.020": ctx(1, 0.020),
    "0p n0.030 nondet": ctx(0, 0.030, deterministic=0),
    "0p n0.060 nondet": ctx(0, 0.060, deterministic=0),
})

out_path, *names = os.environ["RS_PR_ARGS"].split("|")
db = sqlite3.connect(f"file:{os.path.join(REPO, 'replay.db')}?mode=ro", uri=True)
loss = {}
for pid, play, l in db.execute("SELECT position_id, play, loss FROM equities"):
    loss.setdefault(pid, {})[play] = l
positions = []
for pid, position, side, d1, d2 in db.execute(
        "SELECT id, position, side, die1, die2 FROM positions ORDER BY id"):
    pos = from_json(json.loads(position), side)
    by_key = {key(apply_notation(pos, p)): l for p, l in loss[pid].items()}
    positions.append((pid, pos, (d1, d2), by_key))

result = {}
for name in names:
    context = CANDIDATES[name]
    samples = 1 if context["deterministic"] else SAMPLES
    losses = []
    for pid, pos, dice, by_key in positions:
        for _ in range(samples):
            after = apply_gnubg_move(pos, gnubg.findbestmove(gnubg_board(pos), CUBE, context, dice))
            losses.append(by_key[key(after)])
    per_position = [sum(losses[i:i + samples]) / samples for i in range(0, len(losses), samples)]
    result[name] = {"context": context, "positions": len(per_position),
                    "pr": 500 * sum(per_position) / len(per_position), "losses": per_position}
    print(f"{name}: PR {result[name]['pr']:.2f}", flush=True)
json.dump(result, open(out_path, "w"))
