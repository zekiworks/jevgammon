"""Backgammon rules in pure Python, the same as `src/board.rs`.

A position is (pts, bar, off) from the mover's side: pts[i] is point i + 1 in the mover's
numbering, positive for the mover's checkers and negative for the opponent's; bar and off are
[mover, opponent]. Plays are generated in the runner's order and written in its notation
(`bar/22 13/11*`, `6/off`), so the legal play lists here match `Board::legal_plays`.

Standard library only: used by tools/gnubg_eval.py and the v3 tools, inside or outside gnubg.
"""

BAR, OFF = 25, 0
CHECKERS = 15

# Starting positions from the mover's side. Nackgammon is GNUbg 1.08's own (InitBoard,
# position ID 4Dl4ADbgOXgANg): 2 on 24, 2 on 23, 4 on 13, 3 on 8, 4 on 6.
STARTS = {
    "standard": {24: 2, 13: 5, 8: 3, 6: 5},
    "nackgammon": {24: 2, 23: 2, 13: 4, 8: 3, 6: 4},
}


def start(variant="standard"):
    pts = [0] * 24
    for point, n in STARTS[variant].items():
        pts[point - 1] = n
        pts[24 - point] = -n
    return pts, [0, 0], [0, 0]


def flip(pos):
    """The same position seen by the opponent."""
    pts, bar, off = pos
    return [-pts[23 - i] for i in range(24)], [bar[1], bar[0]], [off[1], off[0]]


def from_json(position, side):
    """The runner's stored position (white's view, `turns.position`) as seen by `side`."""
    white = position["points"]
    if side == "white":
        pts = list(white)
        bar = [position["bar"]["white"], position["bar"]["black"]]
        off = [position["off"]["white"], position["off"]["black"]]
    else:
        pts = [-white[23 - i] for i in range(24)]
        bar = [position["bar"]["black"], position["bar"]["white"]]
        off = [position["off"]["black"], position["off"]["white"]]
    return pts, bar, off


def to_json(pos, side):
    """The runner's stored form (white's view) of a position seen by `side`, to move."""
    pts, bar, off = pos if side == "white" else flip(pos)
    return {"bar": {"black": bar[1], "white": bar[0]}, "off": {"black": off[1], "white": off[0]},
            "points": list(pts), "to_move": side}


def pips(pos):
    """(mover, opponent) pip counts; a checker on the bar counts 25."""
    pts, bar, _ = pos
    mine = sum((i + 1) * n for i, n in enumerate(pts) if n > 0) + 25 * bar[0]
    theirs = sum((24 - i) * -n for i, n in enumerate(pts) if n < 0) + 25 * bar[1]
    return mine, theirs


def all_home(pts, bar):
    return bar[0] == 0 and all(n <= 0 for n in pts[6:])


def step(pos, frm, die):
    """Moves one checker from `frm` by `die` pips: (position, (from, to, hit)), or None."""
    pts, bar, off = pos
    pts, bar, off = list(pts), list(bar), list(off)
    if frm == BAR:
        if bar[0] == 0:
            return None
        bar[0] -= 1
    else:
        if bar[0] > 0 or pts[frm - 1] <= 0:
            return None
        pts[frm - 1] -= 1
    target = frm - die
    if target >= 1:
        if pts[target - 1] < -1:
            return None
        hit = pts[target - 1] == -1
        if hit:
            pts[target - 1] = 0
            bar[1] += 1
        pts[target - 1] += 1
        return (pts, bar, off), (frm, target, hit)
    if frm == BAR or not all_home(pos[0], pos[1]):
        return None
    # Overshooting bear-off is only allowed from the highest occupied point.
    if target < 0 and any(n > 0 for n in pos[0][frm:6]):
        return None
    off[0] += 1
    return (pts, bar, off), (frm, OFF, False)


def sources(pos):
    pts, bar, _ = pos
    if bar[0] > 0:
        return [BAR]
    return [p for p in range(24, 0, -1) if pts[p - 1] > 0]


def search(pos, dice, steps, leaves):
    if not dice:
        leaves.append((list(steps), pos))
        return
    moved = False
    for frm in sources(pos):
        r = step(pos, frm, dice[0])
        if r:
            moved = True
            steps.append(r[1] + (dice[0],))
            search(r[0], dice[1:], steps, leaves)
            steps.pop()
    if not moved:
        leaves.append((list(steps), pos))


def key(pos):
    return (tuple(pos[0]), tuple(pos[1]), tuple(pos[2]))


def notation(steps):
    """Play::notation: `bar/22 13/11*`, `6/off`."""
    parts = []
    for frm, to, hit, _ in steps:
        a = "bar" if frm == BAR else str(frm)
        b = "off" if to == OFF else str(to)
        parts.append(f"{a}/{b}{'*' if hit else ''}")
    return " ".join(parts)


def legal_plays(pos, d1, d2):
    """Every legal play as (notation, position after), in Board::legal_plays order: dice tried
    as (d1, d2) then (d2, d1), deduplicated by resulting position, first notation kept."""
    leaves = []
    if d1 == d2:
        search(pos, [d1] * 4, [], leaves)
    else:
        search(pos, [d1, d2], [], leaves)
        search(pos, [d2, d1], [], leaves)
    longest = max(len(s) for s, _ in leaves)
    if longest == 0:
        return []
    leaves = [l for l in leaves if len(l[0]) == longest]
    # With only one die playable, the higher die must be used when possible.
    if d1 != d2 and longest == 1:
        high = max(d1, d2)
        if any(s[0][3] == high for s, _ in leaves):
            leaves = [l for l in leaves if l[0][0][3] == high]
    seen, out = set(), []
    for s, p in leaves:
        k = key(p)
        if k not in seen:
            seen.add(k)
            out.append((notation(s), p))
    return out


def legal_results(pos, d1, d2):
    """Distinct positions after every legal play."""
    return [p for _, p in legal_plays(pos, d1, d2)]


def apply_notation(pos, text):
    """The position after a play written as in Play::notation (`bar/22 13/11*`, `6/off`)."""
    for part in text.split():
        frm, to = part.rstrip("*").split("/")
        frm = BAR if frm == "bar" else int(frm)
        to = OFF if to == "off" else int(to)
        if to == OFF:
            # Bearing off: the smallest legal die that takes this checker off.
            for d in range(frm, 7):
                r = step(pos, frm, d)
                if r and r[1][1] == OFF:
                    break
            else:
                return None
        else:
            r = step(pos, frm, frm - to)
        if not r:
            return None
        pos = r[0]
    return pos


def apply_gnubg_move(pos, move):
    """The position after a gnubg move: (from, to) pairs in the mover's numbering, 25 = bar,
    0 = off, as returned by gnubg.findbestmove or gnubg.parsemove. Hits follow from the board."""
    pairs = [(move[i], move[i + 1]) for i in range(0, len(move) - 1, 2)]
    pts, bar, off = list(pos[0]), list(pos[1]), list(pos[2])
    for frm, to in pairs:
        if frm == BAR:
            bar[0] -= 1
        else:
            pts[frm - 1] -= 1
        if to == OFF:
            off[0] += 1
        else:
            if pts[to - 1] == -1:
                pts[to - 1] = 0
                bar[1] += 1
            pts[to - 1] += 1
    return pts, bar, off


def gnubg_board(pos):
    """gnubg board with the mover on roll: (opponent, mover), each 24 points + bar from its
    own side."""
    pts, bar, _ = pos
    mover = [max(pts[i], 0) for i in range(24)] + [bar[0]]
    opp = [max(-pts[23 - i], 0) for i in range(24)] + [bar[1]]
    return (opp, mover)
