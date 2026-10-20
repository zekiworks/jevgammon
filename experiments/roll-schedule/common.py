"""Shared pieces of the roll-schedule experiment: dice, players, games and matches.

Runs inside gnubg's embedded Python (gnubg 1.08, `gnubg -t -q -p`). gnubg runs scripts without
`__file__`, so the experiment folder and the repo come from RS_DIR and RS_REPO.

Dice and match flow mirror the runner exactly:
- `Dice`, `mix`, `round_seed`, `derive_seed` are src/dice.rs (SplitMix64, FNV-1a labels), bit for
  bit, so scheme A's rolls are the ones the runner would roll for the same seeds.
- A game (src/runner.rs `play_game`): `Dice::new(round seed)`, opening roll (one die per side,
  ties rerolled) is the first turn's roll, white starts if its die is higher; a turn with one
  distinct legal result is forced, none is a pass; turn 300 ends the game on pip count (lower
  pips wins, equal pips goes to the side due to roll next), worth 1 point.
- A match (`play_match`, `rounds_after`): rounds of two games on the same round seed, model1
  white in game 1, model2 white in game 2; 3 rounds, or over after the round in which a player
  reaches 5 if ahead; level then (or level after round 3) adds exactly one round, and a tie
  after it is a draw (league fixtures are not decisive).
- The fixture is `draw_fixture` of src/league.rs (circle method, model1 drawn per match), and
  each match seed is `derive_seed(league seed, "matchday D: M1 v M2")`.
"""

import os
import sys

REPO = os.environ.get("RS_REPO", "/home/cbasaran/code/jevgammon")
sys.path.insert(0, os.path.join(REPO, "tools", "v3"))

import gnubg  # noqa: E402

from engine import CUBE, terminal  # noqa: E402
from rules import apply_gnubg_move, flip, gnubg_board, key, legal_results, pips, start  # noqa: E402

M64 = (1 << 64) - 1
ROUNDS = 3
FIRST_TO = 5
MAX_TURNS = 300


# --- src/dice.rs ------------------------------------------------------------------------------

def mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def round_seed(match_seed, rnd):
    return mix(match_seed ^ mix(0x6A09E667F3BCC909 ^ rnd))


def derive_seed(seed, label):
    h = 0xCBF29CE484222325
    for b in label.encode():
        h = ((h ^ b) * 0x100000001B3) & M64
    return mix(seed ^ mix(h))


class Dice:
    def __init__(self, seed):
        self.state = seed

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & M64
        return mix(self.state)

    def die(self):
        while True:
            v = self.next_u64() >> 61
            if v < 6:
                return v + 1

    def opening(self):
        while True:
            w, b = self.die(), self.die()
            if w != b:
                return w, b

    def roll(self):
        return self.die(), self.die()

    def below(self, n):
        zone = M64 - M64 % n
        while True:
            v = self.next_u64()
            if v < zone:
                return v % n


# --- Players ----------------------------------------------------------------------------------

def ctx(plies, noise, deterministic=1, prune=0):
    return {"cubeful": 0, "plies": plies, "deterministic": deterministic, "prune": prune,
            "noise": noise}


# The round-robin field, strongest first by v1-set PR (pr.py; PR in the results note). The
# named ones are gnubg's predefined levels (eval.c); n0.055 is Casual's near-equal twin.
PLAYERS = [
    ("1-ply", ctx(1, 0.0)),
    ("Advanced", ctx(0, 0.015)),
    ("n0.030", ctx(0, 0.030)),
    ("Intermediate", ctx(0, 0.040)),
    ("Casual", ctx(0, 0.050)),
    ("n0.055", ctx(0, 0.055)),
    ("Beginner", ctx(0, 0.060)),
    ("n0.100", ctx(0, 0.100)),
]


# --- Games and matches ------------------------------------------------------------------------

def choose(pos, roll, context):
    """Position after the mover's play: forced and pass turns ask no one, like the runner."""
    results = legal_results(pos, roll[0], roll[1])
    if not results:
        return pos, 0
    if len(results) == 1:
        return results[0], 0
    after = apply_gnubg_move(pos, gnubg.findbestmove(gnubg_board(pos), CUBE, context, roll))
    if key(after) not in {key(r) for r in results}:
        raise RuntimeError(f"gnubg play not legal: {pos} {roll}")
    return after, 1


def play_game(white, black, seed):
    """One game, `white` and `black` eval contexts. Returns (winner side 0 = white / 1 = black,
    kind, points, turns, decisions)."""
    dice = Dice(seed)
    opening = dice.opening()
    side = 0 if opening[0] > opening[1] else 1
    contexts = (white, black)
    pos = start()
    turn = 1
    decisions = 0
    while True:
        roll = opening if turn == 1 else dice.roll()
        pos, asked = choose(pos, roll, contexts[side])
        decisions += asked
        won = terminal(pos)
        if won is not None:
            kind = {1.0: "single", 2.0: "gammon", 3.0: "backgammon"}[won]
            return side, kind, int(won), turn, decisions
        if turn == MAX_TURNS:
            mine, theirs = pips(pos)
            return (side if mine < theirs else 1 - side), "turn_limit", 1, turn, decisions
        pos = flip(pos)
        side = 1 - side
        turn += 1


def rounds_after(rnd, rounds, score, tie_break, decisive=False):
    if rnd < rounds and all(s < FIRST_TO for s in score):
        return rounds, tie_break
    if score[0] == score[1] and (not tie_break or decisive):
        return rnd + 1, True
    return rnd, tie_break


def play_match(ctx1, ctx2, seed_of_round, rounds=ROUNDS):
    """A match, model1 = ctx1. `seed_of_round(r)` is round r's dice seed. Returns
    (score, games_won, winner 1/2/None, games), games as (round, leg, winner 1/2, kind, points,
    turns, decisions)."""
    score, games_won, games = [0, 0], [0, 0], []
    tie_break = False
    rnd = 1
    while rnd <= rounds:
        seed = seed_of_round(rnd)
        for leg in (1, 2):
            white, black = (ctx1, ctx2) if leg == 1 else (ctx2, ctx1)
            side, kind, points, turns, decisions = play_game(white, black, seed)
            winner = (1 if side == 0 else 2) if leg == 1 else (2 if side == 0 else 1)
            score[winner - 1] += points
            games_won[winner - 1] += 1
            games.append((rnd, leg, winner, kind, points, turns, decisions))
        rounds, tie_break = rounds_after(rnd, rounds, score, tie_break)
        rnd += 1
    winner = 1 if score[0] > score[1] else 2 if score[1] > score[0] else None
    return score, games_won, winner, games


def draw_fixture(names, seed):
    """src/league.rs draw_fixture: [(matchday, model1, model2)]."""
    rng = Dice(derive_seed(seed, "fixture"))
    teams = list(names)
    for i in range(len(teams) - 1, 0, -1):
        j = rng.below(i + 1)
        teams[i], teams[j] = teams[j], teams[i]
    if len(teams) % 2 == 1:
        teams.append(None)
    n = len(teams)
    fixture = []
    for day in range(1, n):
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            if a is not None and b is not None:
                m1, m2 = (a, b) if rng.below(2) == 0 else (b, a)
                fixture.append((day, m1, m2))
        teams[1:] = teams[-1:] + teams[1:-1]
    return fixture
