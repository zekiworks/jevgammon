"""Scores every model decision in the league database with GNU Backgammon.

Runs inside gnubg's embedded Python, one shard per process. gnubg passes no command-line
arguments to the script, so they come from GNUBG_EVAL_ARGS:

    GNUBG_EVAL_ARGS="league.db out.db SHARD SHARDS LEAGUE..." gnubg -t -q -p tools/gnubg_eval.py
    GNUBG_EVAL_ARGS="replay replay.db out.db SHARD SHARDS" gnubg -t -q -p tools/gnubg_eval.py

For each decision (turns.decided_by = 'model' or 'fallback'), the legal plays are generated
here with the same rules as `src/board.rs`; their count must equal `turns.legal_count`, or the
decision is skipped and counted. Every resulting position is evaluated at 0-ply; the five best
and the chosen play are then re-evaluated at 2-ply (gnubg's own move filter works the same way).
Equity is cubeless money equity for the side that moved (there is no doubling cube in these
games). The equity lost is best minus chosen at 2-ply; a game-winning play scores its points
exactly. Results go to `out.db`, table `decisions`.

In replay mode, every option of every position in tools/replay.py's database is evaluated at
2-ply (at most 25 per position), into `out.db` table `equities`.
"""

import json
import os
import sqlite3

import gnubg

FILTER = 5  # plays re-evaluated at 2-ply besides the chosen one
BAR, OFF = 25, 0

args = os.environ["GNUBG_EVAL_ARGS"].split()
if args[0] != "replay":
    src, dst, shard, shards = args[0], args[1], int(args[2]), int(args[3])
    leagues = [int(x) for x in args[4:]]

CUBE = gnubg.cubeinfo(1, 0, 1, 0)  # money game; only cubeless equity is used
PLY0 = {"cubeful": 0, "plies": 0, "deterministic": 1, "prune": 0, "noise": 0.0}
PLY2 = {"cubeful": 0, "plies": 2, "deterministic": 1, "prune": 1, "noise": 0.0}


# --- Positions: (pts, bar, off) from the mover's side, as in src/board.rs --------------------

def from_json(position, side):
    """The stored position (white's view) as seen by `side`."""
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


def all_home(pts, bar):
    return bar[0] == 0 and all(n <= 0 for n in pts[6:])


def step(pos, frm, die):
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


def legal_results(pos, d1, d2):
    """Distinct positions after every legal play, as in Board::legal_plays."""
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
    if d1 != d2 and longest == 1:
        high = max(d1, d2)
        if any(s[0][3] == high for s, _ in leaves):
            leaves = [l for l in leaves if l[0][0][3] == high]
    seen, out = set(), []
    for _, p in leaves:
        k = key(p)
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def apply_notation(pos, notation):
    """The position after a play written as in Play::notation (`bar/22 13/11*`, `6/off`)."""
    for part in notation.split():
        frm, to = part.rstrip("*").split("/")
        frm = BAR if frm == "bar" else int(frm)
        to = OFF if to == "off" else int(to)
        die = frm - to if to != OFF else None
        if die is None:
            # Bearing off: the smallest legal die that takes this checker off.
            for d in range(frm, 7):
                r = step(pos, frm, d)
                if r and r[1][1] == OFF:
                    break
            else:
                return None
        else:
            r = step(pos, frm, die)
        if not r:
            return None
        pos = r[0]
    return pos


# --- Evaluation -------------------------------------------------------------------------------

def gnubg_board_opponent_on_roll(pos):
    """gnubg board after the mover's play: index 1 is the side on roll (the opponent)."""
    pts, bar, _ = pos
    mover = [max(pts[i], 0) for i in range(24)] + [bar[0]]
    opp = [max(-pts[23 - i], 0) for i in range(24)] + [bar[1]]
    return (mover, opp)


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
    """Cubeless money equity for the side that just moved."""
    done = terminal(pos)
    if done is not None:
        return done
    return -gnubg.evaluate(gnubg_board_opponent_on_roll(pos), CUBE, ctx)[5]


# --- Main -------------------------------------------------------------------------------------

def replay():
    """Every option of every position in replay.db (tools/replay.py), at 2-ply: equity and loss
    against the best option. Arguments: `replay REPLAY_DB OUT_DB SHARD SHARDS`."""
    _, rdb, odb, shard_s, shards_s = args
    shard_n, shards_n = int(shard_s), int(shards_s)
    db = sqlite3.connect(f"file:{rdb}?mode=ro", uri=True)
    out = sqlite3.connect(odb)
    out.execute("CREATE TABLE IF NOT EXISTS equities (position_id INTEGER, play TEXT, equity REAL, loss REAL, "
                "PRIMARY KEY (position_id, play))")
    out.execute("CREATE TABLE IF NOT EXISTS skipped (position_id INTEGER PRIMARY KEY, reason TEXT)")
    done = {r[0] for r in out.execute("SELECT position_id FROM equities UNION SELECT position_id FROM skipped")}
    n = 0
    for pid, position, side, d1, d2, options in db.execute(
            "SELECT id, position, side, die1, die2, options FROM positions WHERE id % ? = ? ORDER BY id",
            (shards_n, shard_n)).fetchall():
        if pid in done:
            continue
        pos = from_json(json.loads(position), side)
        legal = {key(r) for r in legal_results(pos, d1, d2)}
        plays = list(json.loads(options))
        after = {p: apply_notation(pos, p) for p in plays}
        if len(legal) != len(plays) or any(a is None or key(a) not in legal for a in after.values()):
            out.execute("INSERT INTO skipped VALUES (?, ?)", (pid, "options do not match the legal plays"))
            continue
        eq = {p: equity(a, PLY2) for p, a in after.items()}
        best = max(eq.values())
        out.executemany("INSERT INTO equities VALUES (?,?,?,?)", [(pid, p, e, best - e) for p, e in eq.items()])
        n += 1
    out.commit()
    print(f"replay shard {shard_n}/{shards_n}: {n} positions scored", flush=True)


def main():
    db = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    out.execute("""CREATE TABLE IF NOT EXISTS decisions (
        turn_id INTEGER PRIMARY KEY, league_id INTEGER, match_id INTEGER, model TEXT,
        plays INTEGER, best_equity REAL, chosen_equity REAL, loss REAL, chosen_rank INTEGER)""")
    out.execute("CREATE TABLE IF NOT EXISTS skipped (turn_id INTEGER PRIMARY KEY, reason TEXT)")
    done = {r[0] for r in out.execute("SELECT turn_id FROM decisions UNION SELECT turn_id FROM skipped")}
    marks = ",".join("?" * len(leagues))
    rows = db.execute(f"""
        SELECT t.id, lm.league_id, g.match_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END,
               t.side, t.die1, t.die2, t.move, t.legal_count, t.position
        FROM turns t JOIN games g ON g.id = t.game_id
        JOIN league_matches lm ON lm.match_id = g.match_id
        WHERE lm.league_id IN ({marks}) AND t.decided_by IN ('model', 'fallback') AND t.id % ? = ?
        ORDER BY t.id""", (*leagues, shards, shard)).fetchall()
    n = 0
    for tid, lid, mid, model, side, d1, d2, move, legal, position in rows:
        if tid in done:
            continue
        pos = from_json(json.loads(position), side)
        results = legal_results(pos, d1, d2)
        chosen = apply_notation(pos, move)
        if len(results) != legal:
            out.execute("INSERT INTO skipped VALUES (?, ?)", (tid, f"{len(results)} plays, stored {legal}"))
            continue
        if chosen is None or key(chosen) not in {key(r) for r in results}:
            out.execute("INSERT INTO skipped VALUES (?, ?)", (tid, f"chosen play {move} not legal"))
            continue
        quick = sorted(((equity(r, PLY0), i) for i, r in enumerate(results)), reverse=True)
        chosen_i = next(i for i, r in enumerate(results) if key(r) == key(chosen))
        candidates = {i for _, i in quick[:FILTER]} | {chosen_i}
        deep = {i: equity(results[i], PLY2) for i in candidates}
        best = max(deep.values())
        rank = 1 + [i for _, i in quick].index(chosen_i)
        out.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?)",
                    (tid, lid, mid, model, legal, best, deep[chosen_i], best - deep[chosen_i], rank))
        n += 1
        if n % 200 == 0:
            out.commit()
    out.commit()
    print(f"shard {shard}/{shards}: {n} decisions scored", flush=True)


replay() if args[0] == "replay" else main()
