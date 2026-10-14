"""Phase labels and game-plan tags for the v3 shared positions (design, "Shared positions").

Positions are (pts, bar, off) from the mover's side, as in rules.py; `gnubg_class` is
gnubg.classifypos of the position (engine.classify). Standard library only.

Phase, first rule that matches:
1. opening: turns 1 to 6.
2. bear-off: any of GNUbg's bear-off classes.
3. race: GNUbg's race class.
4. holding: a contact position (GNUbg contact or crashed class) where one side has escaped all its
   back checkers (none on the bar or on its points 14 to 24) and the other side keeps one high
   anchor: 2 or more checkers on its 18-, 20- or 21-point and no other checkers on its points 18
   to 24 (nor on the bar).
5. contact: everything else, including GNUbg's crashed class.

Game-plan tag, for holding and contact positions only (None otherwise), first rule that matches,
checked for both sides:
1. blitz: a checker on the bar against a home board with 3 or more made points.
2. back game: 2 or more anchors on the side's points 18 to 24.
3. holding: the holding rule.
4. priming: 4 or more made points in a row.
5. low-anchor: the side's only anchor in the opponent's home board (its points 19 to 24) is on
   its 22-, 23- or 24-point.
6. other.

Deviation from the design's proposed order (low-anchor before priming), agreed before the freeze:
a 4+ prime defines the game plan more than a low anchor does. transformer-backgammon's
prime_building_position (5-primes on both sides, back checkers on the 24- and 23-points) is
tagged priming, its textbook label, only with this order.
"""

from rules import flip, pips

# gnubg 1.08 positionclass values (eval.h); pinned against the source by test_classify.py.
BEAROFF_CLASSES = (4, 5, 6, 7)
RACE_CLASS = 8
CONTACT_CLASSES = (9, 10)  # crashed, contact

PHASES = ("opening", "contact", "holding", "race", "bear-off")
TAGS = ("blitz", "back game", "holding", "priming", "low-anchor", "other")
OPENING_TURNS = 6
HIGH_ANCHORS = (18, 20, 21)
LOW_ANCHORS = (22, 23, 24)


def _sides(pos):
    return (pos, flip(pos))


def _own(pos, point):
    """The side's checkers on its own point (1..24)."""
    return max(pos[0][point - 1], 0)


def _theirs(pos, point):
    """The opponent's checkers on the side's point (1..24)."""
    return max(-pos[0][point - 1], 0)


def escaped(pos):
    """The side has no checker on the bar or on its points 14 to 24."""
    return pos[1][0] == 0 and all(_own(pos, p) == 0 for p in range(14, 25))


def high_anchor(pos):
    """The side's only checkers on its points 18 to 24 (and none on the bar) are 2 or more on its
    18-, 20- or 21-point."""
    held = [p for p in range(18, 25) if _own(pos, p) > 0]
    return pos[1][0] == 0 and len(held) == 1 and held[0] in HIGH_ANCHORS and _own(pos, held[0]) >= 2


def holder(pos):
    """For a holding position, the holding side: 0 = mover, 1 = opponent; else None."""
    for i, (a, b) in enumerate(((pos, flip(pos)), (flip(pos), pos))):
        # i = 0: the opponent escaped and the mover holds; i = 1: the reverse.
        if escaped(b) and high_anchor(a):
            return i
    return None


def race_deficit(pos):
    """For a holding position: the holder's pip count minus the escaped side's."""
    side = holder(pos)
    if side is None:
        return None
    mine, theirs = pips(pos)
    return mine - theirs if side == 0 else theirs - mine


def phase(pos, gnubg_class, turn):
    if gnubg_class not in BEAROFF_CLASSES + (RACE_CLASS,) + CONTACT_CLASSES:
        raise ValueError(f"unexpected gnubg class {gnubg_class}")
    if turn <= OPENING_TURNS:
        return "opening"
    if gnubg_class in BEAROFF_CLASSES:
        return "bear-off"
    if gnubg_class == RACE_CLASS:
        return "race"
    if holder(pos) is not None:
        return "holding"
    return "contact"


def blitz(pos):
    """The side has a checker on the bar against 3 or more made points in the opponent's home."""
    return pos[1][0] > 0 and sum(_theirs(pos, p) >= 2 for p in range(19, 25)) >= 3


def back_game(pos):
    return sum(_own(pos, p) >= 2 for p in range(18, 25)) >= 2


def low_anchor(pos):
    anchors = [p for p in range(19, 25) if _own(pos, p) >= 2]
    return len(anchors) == 1 and anchors[0] in LOW_ANCHORS


def longest_prime(pos):
    best = run = 0
    for p in range(1, 25):
        run = run + 1 if _own(pos, p) >= 2 else 0
        best = max(best, run)
    return best


def tag(pos, phase_label):
    if phase_label not in ("holding", "contact"):
        return None
    sides = _sides(pos)
    if any(blitz(s) for s in sides):
        return "blitz"
    if any(back_game(s) for s in sides):
        return "back game"
    if holder(pos) is not None:
        return "holding"
    if any(longest_prime(s) >= 4 for s in sides):
        return "priming"
    if any(low_anchor(s) for s in sides):
        return "low-anchor"
    return "other"
