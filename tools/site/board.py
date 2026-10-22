"""The backgammon board as SVG, server-side: the site's visual signature on the home page and the social preview.

Same geometry and classes as the board in assets/decisions.js (Every decision), so one stylesheet (decisions.css)
draws both. The board is shown from the mover's side: the mover at the bottom, moving 24 -> 1. A play can be drawn
on it as arrows (class bd-move), one per checker step of its notation ("13/11*", "bar/22", "6/off")."""

from common import esc

P, R, BAR, FRAME, TRAY, BAND, H, GAP = 32, 15, 30, 8, 40, 18, 150, 34
LEFT = FRAME
MID = FRAME + 6 * P
RIGHT = MID + BAR
EDGE = RIGHT + 6 * P
WIDTH = EDGE + FRAME + TRAY
TOP = BAND + 6
BOTTOM = TOP + 2 * H + GAP
HEIGHT = BOTTOM + 6 + BAND
MID_Y = TOP + H + GAP / 2


def point_x(p: int) -> float:
    if p <= 6:
        return EDGE - (p - .5) * P
    if p <= 12:
        return MID - (p - 6.5) * P
    if p <= 18:
        return LEFT + (p - 12.5) * P
    return RIGHT + (p - 18.5) * P


def _checkers(x, n, mine, from_top, base) -> str:
    cls = "ck-me" if mine else "ck-opp"
    out = []
    shown = min(n, 5)
    for k in range(shown):
        y = base + R + k * 2 * R if from_top else base - R - k * 2 * R
        out.append(f'<circle class="ck {cls}" cx="{x:g}" cy="{y:g}" r="{R - 1}"/>')
        if k == shown - 1 and n > 5:
            out.append(f'<text class="ck-count {cls}-text" x="{x:g}" y="{y + 4:g}">{n}</text>')
    return "".join(out)


def _die(x, y, value) -> str:
    s, q = 26, 26 / 4
    spots = {1: [(2, 2)], 2: [(1, 1), (3, 3)], 3: [(1, 1), (2, 2), (3, 3)], 4: [(1, 1), (3, 1), (1, 3), (3, 3)],
             5: [(1, 1), (3, 1), (2, 2), (1, 3), (3, 3)], 6: [(1, 1), (3, 1), (1, 2), (3, 2), (1, 3), (3, 3)]}[value]
    return (f'<rect class="die" x="{x:g}" y="{y:g}" width="{s}" height="{s}" rx="4"/>'
            + "".join(f'<circle class="pip" cx="{x + i * q:g}" cy="{y + j * q:g}" r="2.6"/>' for i, j in spots))


def _stack_y(p: int, depth: int) -> float:
    """Centre of the depth-th checker (0 = at the edge) on point p."""
    depth = min(depth, 4)
    return TOP + R + depth * 2 * R if p >= 13 else BOTTOM - R - depth * 2 * R


def _anchor(p, points, bar_me) -> tuple[float, float]:
    if p == 25:
        return MID + BAR / 2, MID_Y + 4 + R + max(bar_me - 1, 0) * 2 * R
    if p == 0:
        return EDGE + FRAME + TRAY / 2, BOTTOM - 20
    return point_x(p), _stack_y(p, max(abs(points[p - 1]) - 1, 0))


def moves(notation: str) -> list[tuple[int, int]]:
    out = []
    for token in notation.split():
        token = token.split("(")[0].replace("*", "")
        parts = token.split("/")
        steps = [25 if s == "bar" else 0 if s == "off" else int(s) for s in parts]
        out += list(zip(steps, steps[1:]))
    return out


def board_svg(board: dict, dice, pips, play: str | None = None, label_extra: str = "", cls: str = "bd") -> str:
    points, bar, off = board["points"], board["bar"], board["off"]
    s = [f'<rect class="bd-frame" x="0" y="{BAND}" width="{EDGE + FRAME}" height="{BOTTOM - BAND + 6}" rx="6"/>',
         f'<rect class="bd-felt" x="{LEFT}" y="{TOP}" width="{6 * P}" height="{BOTTOM - TOP}"/>',
         f'<rect class="bd-felt" x="{RIGHT}" y="{TOP}" width="{6 * P}" height="{BOTTOM - TOP}"/>',
         f'<rect class="bd-tray" x="{EDGE + FRAME + 4}" y="{BAND}" width="{TRAY - 4}" height="{BOTTOM - BAND + 6}" rx="4"/>']
    for p in range(1, 25):
        x, top = point_x(p), p >= 13
        tip, base = (TOP + H, TOP) if top else (BOTTOM - H, BOTTOM)
        s.append(f'<path class="bd-point {"bd-a" if p % 2 else "bd-b"}" d="M{x - P / 2:g} {base}L{x + P / 2:g} {base}L{x:g} {tip}Z"/>')
        s.append(f'<text class="bd-num" x="{x:g}" y="{BAND - 5 if top else HEIGHT - 4}">{p}</text>')
        n = points[p - 1]
        if n:
            s.append(_checkers(x, abs(n), n > 0, top, base))
    bar_x = MID + BAR / 2
    if bar[1]:
        s.append(_checkers(bar_x, bar[1], False, False, MID_Y - 4))
    if bar[0]:
        s.append(_checkers(bar_x, bar[0], True, True, MID_Y + 4))
    tray_x, tray_w = EDGE + FRAME + 4, TRAY - 4
    for k in range(off[1]):
        s.append(f'<rect class="ck-off ck-opp" x="{tray_x + 5}" y="{TOP + 2 + k * 7}" width="{tray_w - 10}" height="6" rx="1.5"/>')
    for k in range(off[0]):
        s.append(f'<rect class="ck-off ck-me" x="{tray_x + 5}" y="{BOTTOM - 8 - k * 7}" width="{tray_w - 10}" height="6" rx="1.5"/>')
    dx = RIGHT + 3 * P
    s.append(_die(dx - 30, MID_Y - 13, dice[0]) + _die(dx + 4, MID_Y - 13, dice[1]))
    if play:
        s.append('<defs><marker id="bd-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" '
                 'orient="auto-start-reverse"><path class="bd-move-head" d="M0 0L10 5L0 10Z"/></marker></defs>')
        for a, b in moves(play):
            x1, y1 = _anchor(a, points, bar[0])
            x2 = point_x(b) if b else EDGE + FRAME + TRAY / 2
            y2 = _stack_y(b, 0) if b else BOTTOM - 20
            lift = 46 if (a >= 13) == (b >= 13) and b else 0
            cy = (min(y1, y2) + lift) if a >= 13 and b >= 13 else (max(y1, y2) - lift)
            s.append(f'<path class="bd-move" d="M{x1:g} {y1:g}Q{(x1 + x2) / 2:g} {cy:g} {x2:g} {y2:g}" marker-end="url(#bd-arrow)"/>')
    label = (f"Board from the mover's side, the mover at the bottom: dice {dice[0]}-{dice[1]}; pip count: you {pips[0]}, "
             f"opponent {pips[1]}.{(' ' + label_extra) if label_extra else ''}")
    return (f'<svg class="{cls}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(label)}">'
            + "".join(s) + "</svg>")
