"""Self-play gammon rates of the anchor and of the noise-free 0-ply player, per machine. Runs
inside gnubg:

    AC_LIB=<folder with rules.py, engine.py> AC_RS=<experiments/roll-schedule> AC_GAMES=300 \
        AC_OUT=out.json nice -n 19 gnubg -t -q -p selfplay.py

Games are experiments/roll-schedule/common.py play_game (the runner's game flow and dice), game i
on seed derive_seed(20261020, "anchor selfplay i"), identical on every machine.
"""

import json
import os
import platform
import sys
import time
from collections import Counter

sys.path.insert(0, os.environ["AC_LIB"])
sys.path.insert(0, os.environ["AC_RS"])

from common import ctx, derive_seed, play_game  # noqa: E402

GAMES = int(os.environ["AC_GAMES"])
SETUPS = {"Beginner (0-ply, det. noise 0.06)": ctx(0, float("0.06")),
          "Expert (0-ply, noise 0)": ctx(0, 0.0)}

out = {"machine": platform.node(), "arch": platform.machine(), "games": GAMES, "setups": {}}
for name, context in SETUPS.items():
    t0 = time.time()
    kinds, turns, records = Counter(), 0, []
    for i in range(GAMES):
        winner, kind, points, n, decisions = play_game(
            context, context, derive_seed(20261020, f"anchor selfplay {i}"))
        kinds[kind] += 1
        turns += n
        records.append([winner, kind, n])
    out["setups"][name] = {"kinds": dict(kinds), "mean_turns": turns / GAMES,
                           "seconds": time.time() - t0, "games": records}
    print(name, dict(kinds), f"{turns / GAMES:.1f} turns", flush=True)
json.dump(out, open(os.environ["AC_OUT"], "w"))
