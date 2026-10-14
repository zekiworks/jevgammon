"""The `gnubg-weak` player's engine: GNU Backgammon's own move choice at a fixed level.

Runs inside gnubg's embedded Python as a long-lived subprocess of the runner, so each move costs
one gnubg call (about 10 ms). src/players/gnubg.rs embeds this file with tools/v3/rules.py and
tools/v3/engine.py, writes them to one folder and starts

    GNUBG_PLAYER_LIB=<folder> GNUBG_PLAYER_PLIES=0 GNUBG_PLAYER_NOISE=0.06 \
    GNUBG_PLAYER_DETERMINISTIC=1 gnubg -t -q -p <folder>/gnubg_player.py

Protocol, one line each way. After start-up it prints `gnubg-player ready <context JSON>`. Each
request is a JSON object: `board`, the mover's position before the play, and `plays`, the position
after every legal play in the runner's order, both as `[pts, [bar mover, bar opponent], [off mover,
off opponent]]` from the mover's side (src/board.rs, tools/v3/rules.py); and `dice`. The reply is
`gnubg-player <index>` of gnubg.findbestmove's play in `plays`, or `gnubg-player error <message>`.
gnubg prints its banner on the same stdout, so the runner ignores lines without the prefix.

The evaluation context is cubeless (the games have no doubling cube); the noise is gnubg's own,
added to every evaluation as in its predefined player levels.
"""

import json
import os
import sys

sys.path.insert(0, os.environ["GNUBG_PLAYER_LIB"])  # gnubg runs scripts without __file__

from engine import best_move  # noqa: E402
from rules import apply_gnubg_move, key  # noqa: E402

PREFIX = "gnubg-player"
CONTEXT = {
    "cubeful": 0,
    "plies": int(os.environ["GNUBG_PLAYER_PLIES"]),
    "deterministic": int(os.environ["GNUBG_PLAYER_DETERMINISTIC"]),
    "prune": 0,
    "noise": float(os.environ["GNUBG_PLAYER_NOISE"]),
}


def choose(request):
    board = request["board"]
    d1, d2 = request["dice"]
    after = key(apply_gnubg_move(board, best_move(board, d1, d2, CONTEXT)))
    for i, play in enumerate(request["plays"]):
        if key(play) == after:
            return str(i)
    return f"error gnubg's play is not among the {len(request['plays'])} legal plays"


print(f"{PREFIX} ready {json.dumps(CONTEXT, sort_keys=True)}", flush=True)
for line in sys.stdin:
    if not line.strip():
        continue
    try:
        reply = choose(json.loads(line))
    except Exception as e:  # reported to the runner, which fails the decision
        reply = "error " + repr(e).replace("\n", " ")
    print(f"{PREFIX} {reply}", flush=True)
