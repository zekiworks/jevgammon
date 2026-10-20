"""The anchor's move choice and raw evaluations, for comparing machines. Runs inside gnubg:

    AC_LIB=<folder with rules.py, engine.py> AC_IN=positions.json AC_OUT=out.json \
        nice -n 19 gnubg -t -q -p moves.py

Same call as the league player (tools/gnubg_player.py): engine.best_move, i.e.
gnubg.findbestmove(board, CUBE, context, dice), with the player's context (cubeless, 0-ply,
deterministic noise, no pruning). Run with noise 0.06 (the anchor) and noise 0 (to separate
floating point from the noise computation).

Per v1 position it also records gnubg.evaluate at 0-ply of the position on roll and of every
legal result (from the opponent's side, as findbestmove scores it), with and without noise, so
the two machines can be compared value by value (the noise is noisy minus clean). Per v3 anchor
decision it records the noisy move and its index in the runner's legal-play order.
"""

import json
import os
import platform
import sys
import time

sys.path.insert(0, os.environ["AC_LIB"])

import gnubg  # noqa: E402

from engine import CUBE, best_move  # noqa: E402
from rules import apply_gnubg_move, flip, from_json, gnubg_board, key, legal_plays  # noqa: E402

CONTEXTS = {name: {"cubeful": 0, "plies": 0, "deterministic": 1, "prune": 0, "noise": noise}
            for name, noise in (("n0.06", float("0.06")), ("n0", 0.0))}

data = json.load(open(os.environ["AC_IN"]))
t0 = time.time()


def evaluate(pos, ctx):
    return [float(x) for x in gnubg.evaluate(gnubg_board(pos), CUBE, ctx)]


v1 = []
for p in data["v1"]:
    pos = from_json(p["position"], p["side"])
    d1, d2 = p["dice"]
    plays = legal_plays(pos, d1, d2)
    keys = [key(r) for _, r in plays]
    row = {"id": p["id"], "plays": [n for n, _ in plays]}
    for name, ctx in CONTEXTS.items():
        move = list(best_move(pos, d1, d2, ctx))
        row[name] = {
            "move": move,
            "index": keys.index(key(apply_gnubg_move(pos, move))),
            "eval_root": evaluate(pos, ctx),
            "eval_results": [evaluate(flip(r), ctx) for _, r in plays],
        }
    v1.append(row)
t1 = time.time()

v3 = []
for p in data["v3"]:
    pos = from_json(p["position"], p["side"])
    d1, d2 = p["dice"]
    keys = [key(r) for _, r in legal_plays(pos, d1, d2)]
    move = list(best_move(pos, d1, d2, CONTEXTS["n0.06"]))
    v3.append({"turn_id": p["turn_id"], "move": move, "legal": len(keys),
               "index": keys.index(key(apply_gnubg_move(pos, move)))})
t2 = time.time()

json.dump({"machine": platform.node(), "arch": platform.machine(), "python": sys.version,
           "contexts": CONTEXTS, "seconds": {"v1": t1 - t0, "v3": t2 - t1},
           "v1": v1, "v3": v3}, open(os.environ["AC_OUT"], "w"))
print(f"done v1 {len(v1)} in {t1 - t0:.0f}s, v3 {len(v3)} in {t2 - t1:.0f}s", flush=True)
