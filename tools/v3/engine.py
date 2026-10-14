"""GNUbg 1.08 helpers for the scorer and the v3 tools. Runs only inside gnubg's embedded Python.

Every gnubg call that goes through its task queue (evaluate, findbestmove, hint) costs at least
10 ms, because gnubg polls for finished tasks every 10 ms (multithread.c, WaitForAllTasks).
"""

import gnubg

from rules import flip, gnubg_board

CUBE = gnubg.cubeinfo(1, 0, 1, 0)  # money game; only cubeless equity is used
PLY0 = {"cubeful": 0, "plies": 0, "deterministic": 1, "prune": 0, "noise": 0.0}
PLY2 = {"cubeful": 0, "plies": 2, "deterministic": 1, "prune": 1, "noise": 0.0}
# GNUbg's predefined "expert" level (eval.c, aecSettings): 0-ply, no noise. Cubeless, because
# the self-play games have no cube.
EXPERT = PLY0

# gnubg's positionclass (eval.h, 1.08): pinned by tools/v3/test_classify.py.
CLASS_OVER, CLASS_BEAROFF2, CLASS_BEAROFF_TS, CLASS_BEAROFF1, CLASS_BEAROFF_OS = 0, 4, 5, 6, 7
CLASS_RACE, CLASS_CRASHED, CLASS_CONTACT = 8, 9, 10
BEAROFF_CLASSES = (CLASS_BEAROFF2, CLASS_BEAROFF_TS, CLASS_BEAROFF1, CLASS_BEAROFF_OS)
VARIATION = {"standard": 0, "nackgammon": 1}


def position_id(pos):
    """GNUbg position ID with the mover on roll."""
    return gnubg.positionid(gnubg_board(pos))


def classify(pos, variant="standard"):
    """gnubg.classifypos of the position (symmetric in the two sides)."""
    return gnubg.classifypos(gnubg_board(pos), VARIATION[variant])


def terminal(pos):
    """Points won by the mover if the play ends the game, else None."""
    pts, bar, off = pos
    if off[0] < 15:
        return None
    if off[1] > 0:
        return 1.0
    if bar[1] > 0 or any(n < 0 for n in pts[:6]):
        return 3.0
    return 2.0


def equity(pos, ctx):
    """Cubeless money equity, for the side that just moved, of the position after its play."""
    done = terminal(pos)
    if done is not None:
        return done
    return -gnubg.evaluate(gnubg_board(flip(pos)), CUBE, ctx)[5]


def best_move(pos, d1, d2, ctx=EXPERT):
    """GNUbg's play for the roll as (from, to) pairs in the mover's numbering (25 = bar,
    0 = off); empty when the mover cannot move."""
    return gnubg.findbestmove(gnubg_board(pos), CUBE, ctx, (d1, d2))


def cubeless(probs):
    """Cubeless money equity from gnubg's five outputs."""
    win, wg, wbg, lg, lbg = probs
    return 2 * win - 1 + wg - lg + wbg - lbg

