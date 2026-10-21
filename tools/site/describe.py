"""Option descriptions exactly as the runner shows them (`src/players/prompt.rs` describe()).

Pure Python on top of tools/v3/rules.py. Positions are (pts, bar, off) from the mover's side, plays
are (notation, position after) pairs as returned by rules.legal_plays:

    describe(pos, play) -> "13/7 8/7: hits 0; makes the 7 point; leaves 1 blot, the opponent hits
    with 11 of 36 rolls; you hold 4 points (2 in your home board), longest prime 2; pips: you 159,
    opponent 167"   (plus "; borne off N" when the play bears a checker off)

hitting_rolls(pos) is Board::hitting_rolls (`src/board.rs`): how many of the 36 rolls give the
mover a legal play that hits a blot. It gives the same answer as generating every legal play per
roll, but searches only (length, hit) outcomes with memoisation, which is much faster.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v3"))

from rules import flip, key, pips, sources, step  # noqa: E402


def made(pos, point):
    """Board::made: the mover holds two or more checkers on `point` (1..24)."""
    return pos[0][point - 1] >= 2


def blots(pos):
    """Board::blots: the mover's points holding exactly one checker."""
    return sum(1 for n in pos[0] if n == 1)


def longest_prime(pos):
    """Board::longest_prime: most consecutive made points."""
    best = run = 0
    for n in pos[0]:
        run = run + 1 if n >= 2 else 0
        best = max(best, run)
    return best


def _outcomes(pos, dice, memo):
    """Every (steps played, any hit) pair a search over `dice` can end with (Board::search leaves)."""
    if not dice:
        return {(0, False)}
    k = (key(pos), dice)
    got = memo.get(k)
    if got is not None:
        return got
    out = set()
    for frm in sources(pos):
        r = step(pos, frm, dice[0])
        if r:
            hit = r[1][2]
            for n, h in _outcomes(r[0], dice[1:], memo):
                out.add((n + 1, h or hit))
    if not out:
        out = {(0, False)}
    memo[k] = out
    return out


def _roll_hits(pos, d1, d2, memo):
    """Board::legal_plays(d1, d2) contains a play with a hitting step."""
    if d1 == d2:
        leaves = _outcomes(pos, (d1,) * 4, memo)
        longest = max(n for n, _ in leaves)
        return longest > 0 and (longest, True) in leaves
    hi, lo = max(d1, d2), min(d1, d2)
    first_hi = _outcomes(pos, (hi, lo), memo)
    first_lo = _outcomes(pos, (lo, hi), memo)
    longest = max(n for n, _ in first_hi | first_lo)
    if longest == 0:
        return False
    if longest == 1:
        # With only one die playable, the higher die must be used when possible.
        if any(n == 1 for n, _ in first_hi):
            return (1, True) in first_hi
        return (1, True) in first_lo
    return (longest, True) in first_hi or (longest, True) in first_lo


def hitting_rolls(pos):
    """Board::hitting_rolls: how many of the 36 rolls give the mover a legal play that hits."""
    if -1 not in pos[0]:
        return 0
    memo = {}
    rolls = 0
    for d1 in range(1, 7):
        for d2 in range(d1, 7):
            if _roll_hits(pos, d1, d2, memo):
                rolls += 1 if d1 == d2 else 2
    return rolls


def describe_with_shots(pos, play):
    """(describe(pos, play), the hitting-rolls number in it)."""
    notation, after = play
    parts = [f"{notation}: hits {notation.count('*')}; "]
    new = [str(p) for p in range(1, 25) if made(after, p) and not made(pos, p)]
    if not new:
        parts.append("makes no new point; ")
    elif len(new) == 1:
        parts.append(f"makes the {new[0]} point; ")
    else:
        parts.append(f"makes the {', '.join(new)} points; ")
    n_blots = blots(after)
    shots = hitting_rolls(flip(after))
    parts.append(f"leaves {n_blots} blot{'' if n_blots == 1 else 's'}, "
                 f"the opponent hits with {shots} of 36 rolls; ")
    held = sum(1 for p in range(1, 25) if made(after, p))
    home = sum(1 for p in range(1, 7) if made(after, p))
    mine, theirs = pips(after)
    parts.append(f"you hold {held} points ({home} in your home board), longest prime "
                 f"{longest_prime(after)}; pips: you {mine}, opponent {theirs}")
    if after[2][0] > pos[2][0]:
        parts.append(f"; borne off {after[2][0]}")
    return "".join(parts), shots


def describe(pos, play):
    """prompt.rs describe(): the option text the runner shows for `play` = (notation, after)."""
    return describe_with_shots(pos, play)[0]
