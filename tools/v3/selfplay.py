"""GNUbg 1.08 expert-level self-play games, the raw material of the v3 position sets.

Runs inside gnubg's embedded Python from the repo root, one process per shard:

    V3_ARGS="VARIANT SEED FIRST COUNT OUT.jsonl.gz" gnubg -t -q -p tools/v3/selfplay.py

Plays games FIRST .. FIRST+COUNT-1 from the VARIANT start ("standard" or "nackgammon", GNUbg's
own setup). Dice for game g come from random.Random(f"{SEED}:{VARIANT}:{g}"): the opening roll is
re-rolled until the dice differ and its higher die decides who starts (white on the first die);
every play is gnubg.findbestmove at GNUbg's expert level (0-ply, no noise, cubeless: no cube).
The game ends when a side has borne off, or after 300 turns as in the runner.

Writes one JSON line per game: {"game", "variant", "seed", "turns", "result"}, where "turns"
lists every position with 2 or more legal plays before the play: turn number (1 = first move),
side to move, dice as rolled, GNUbg position ID with the mover on roll, gnubg class, legal play
count and the position from the mover's side (pts, bar, off).
"""

import gzip
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.getcwd(), "tools", "v3"))  # gnubg runs scripts without __file__

import engine  # noqa: E402
from rules import apply_gnubg_move, flip, key, legal_plays, start  # noqa: E402

TURN_LIMIT = 300


def play_game(variant, seed, game):
    rng = random.Random(f"{seed}:{variant}:{game}")
    while True:
        a, b = rng.randint(1, 6), rng.randint(1, 6)
        if a != b:
            break
    side = "white" if a > b else "black"
    dice = (a, b)
    pos = start(variant)  # from the side to move
    turns = []
    for turn in range(1, TURN_LIMIT + 1):
        d1, d2 = dice
        plays = legal_plays(pos, d1, d2)
        if len(plays) >= 2:
            turns.append({"t": turn, "side": side, "dice": [d1, d2], "pid": engine.position_id(pos),
                          "cls": engine.classify(pos, variant), "n": len(plays),
                          "pts": pos[0], "bar": pos[1], "off": pos[2]})
        if plays:
            after = apply_gnubg_move(pos, engine.best_move(pos, d1, d2))
            if key(after) not in {key(p) for _, p in plays}:
                raise RuntimeError(f"game {game} turn {turn}: gnubg's play is not legal here")
            pos = after
        if pos[2][0] == 15:
            return turns, {"winner": side, "turns": turn}
        pos = flip(pos)
        side = "black" if side == "white" else "white"
        dice = (rng.randint(1, 6), rng.randint(1, 6))
    return turns, {"winner": None, "turns": TURN_LIMIT}


def main():
    variant, seed, first, count, out = os.environ["V3_ARGS"].split()
    first, count = int(first), int(count)
    t0 = time.time()
    with gzip.open(out, "wt") as f:
        for game in range(first, first + count):
            turns, result = play_game(variant, seed, game)
            f.write(json.dumps({"game": game, "variant": variant, "seed": seed, "turns": turns,
                                "result": result}, separators=(",", ":")) + "\n")
    print(f"{variant} games {first}..{first + count - 1}: {time.time() - t0:.0f} s", flush=True)
    os._exit(0)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    os._exit(1)
