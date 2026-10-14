"""GNUbg 1.08 scoring of the v3 shared positions: 2-ply equities, then rollouts for near-ties.

Runs inside gnubg's embedded Python from the repo root. Arguments come from V3_ARGS (gnubg passes
none to scripts): a mode, then key=value options.

    V3_ARGS="evaluate out=score.db positions=positions/new.jsonl[,more.jsonl] [shard=0 shards=1] [limit=N]" \
        gnubg -t -q -p tools/v3/score.py
    V3_ARGS="rollout out=score.db positions=positions/new.jsonl [chosen=chosen.json] [trials=1296] \
        [plies=0] [threads=8] [seed=1] [budget=SECONDS] [limit=N] [ids=ID,ID]" gnubg -t -q -p tools/v3/score.py

evaluate: every legal play of every position (at most 25) at 2-ply, cubeless money equity for the
side that moves, into table `equities` (position, play, equity, loss against the best). A position
is a near-tie when its two best plays are within 0.02 at 2-ply; its candidates are every play
within 0.02 of the best. Near-ties go to table `near_ties`.

rollout: rolls out the candidates of every near-tie in `near_ties` through GNUbg's own rollout
(the hint move list, `cmark move set rollout`, `analyse rollout move`), cubeless, with variance
reduction and quasi-random dice; `trials` games per play (default 1296), checker play at `plies`
in the rollout. Order: near-ties where some setup chose one of the candidates go first; the rest
(no chooser: a rollout would shift every setup's loss there by the same amount) go last, and only
they are skipped once `budget` seconds have passed. `chosen` is a JSON object mapping position id
to the plays any setup chose there (the decision logs); without it every near-tie counts as
unchosen. Results go to table `rollouts` with the time each rollout took.
"""

import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.getcwd(), "tools", "v3"))  # gnubg runs scripts without __file__

import gnubg  # noqa: E402

import engine  # noqa: E402
from rules import apply_gnubg_move, from_json, gnubg_board, key, legal_plays  # noqa: E402

NEAR_TIE = 0.02

SCHEMA = """
CREATE TABLE IF NOT EXISTS equities (position TEXT, play TEXT, equity REAL, loss REAL, PRIMARY KEY (position, play));
CREATE TABLE IF NOT EXISTS near_ties (position TEXT PRIMARY KEY, gap REAL, candidates TEXT);
CREATE TABLE IF NOT EXISTS rollouts (
    position TEXT, play TEXT, equity REAL, probs TEXT, probs_std TEXT, trials INTEGER, plies INTEGER,
    seed INTEGER, chosen INTEGER, seconds REAL, PRIMARY KEY (position, play));
"""


def parse_args():
    words = os.environ["V3_ARGS"].split()
    opts = dict(w.split("=", 1) for w in words[1:])
    return words[0], opts


def load_positions(paths):
    rows = {}
    for path in paths.split(","):
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def mover_view(r):
    return from_json(r["position"], r["side"])


def evaluate(opts, db):
    rows = list(load_positions(opts["positions"]).values())
    shard, shards = int(opts.get("shard", 0)), int(opts.get("shards", 1))
    done = {p for (p,) in db.execute("SELECT DISTINCT position FROM equities")}
    todo = [r for i, r in enumerate(rows) if i % shards == shard and r["id"] not in done]
    todo = todo[: int(opts["limit"])] if "limit" in opts else todo
    t0, ties = time.time(), 0
    for r in todo:
        d1, d2 = r["dice"]
        plays = legal_plays(mover_view(r), d1, d2)
        assert [n for n, _ in plays] == r["legal_plays"], r["id"]
        eq = {n: engine.equity(p, engine.PLY2) for n, p in plays}
        best = max(eq.values())
        db.executemany("INSERT INTO equities VALUES (?,?,?,?)", [(r["id"], n, e, best - e) for n, e in eq.items()])
        top = sorted(eq.values(), reverse=True)
        if top[0] - top[1] < NEAR_TIE:
            cands = [n for n, e in sorted(eq.items(), key=lambda x: -x[1]) if best - e < NEAR_TIE]
            db.execute("INSERT INTO near_ties VALUES (?,?,?)", (r["id"], top[0] - top[1], json.dumps(cands)))
            ties += 1
        db.commit()
    print(f"evaluate: {len(todo)} positions, {ties} near-ties, {time.time() - t0:.0f} s", flush=True)


def setup_rollouts(opts):
    for c in ["set cube use off", "new session",
              f"set rollout trials {int(opts.get('trials', 1296))}", "set rollout cubeful off",
              "set rollout varredn on", "set rollout quasirandom on", "set rollout late enable off",
              "set rollout truncation enable off", "set rollout cube-equal-chequer on",
              f"set rollout chequerplay plies {int(opts.get('plies', 0))}",
              f"set rollout seed {int(opts.get('seed', 1))}",
              f"set threads {int(opts.get('threads', 8))}",
              # The hint list only maps gnubg's moves to ours; 0-ply keeps it quick.
              "set evaluation chequerplay evaluation plies 0"]:
        gnubg.command(c)


def hint_moves(pos, d1, d2):
    """Sets up the position with the mover on roll and returns gnubg's hint list."""
    board = gnubg_board(pos)
    gnubg.setgnubgid(gnubg.gnubgid(board, gnubg.cubeinfo(1, 0, 1, 0), gnubg.posinfo(1, 0, 0, 1, (d1, d2))))
    return gnubg.hint()["hint"]


def rollout_position(r, cands):
    """Rolls out the candidate plays of one position: {play: (equity, probs, probs_std, trials)}."""
    pos = mover_view(r)
    d1, d2 = r["dice"]
    ours = {key(p): n for n, p in legal_plays(pos, d1, d2)}
    hint = hint_moves(pos, d1, d2)
    index = {}
    for h in hint:
        n = ours.get(key(apply_gnubg_move(pos, sum(gnubg.parsemove(h["move"]), ()))))
        if n in cands:
            index[n] = h["movenum"]
    missing = set(cands) - set(index)
    if missing:
        raise RuntimeError(f"{r['id']}: {sorted(missing)} not in gnubg's move list")
    gnubg.command("cmark move clear")
    gnubg.command("cmark move set rollout " + " ".join(str(index[n]) for n in cands))
    gnubg.command("analyse rollout move")
    out = {}
    for h in gnubg.hint()["hint"]:
        if h["type"] != "rollout":
            continue
        n = ours[key(apply_gnubg_move(pos, sum(gnubg.parsemove(h["move"]), ())))]
        d = h["details"]
        out[n] = (engine.cubeless(d["probs"]), d["probs"], d["probs-std"], d["trials"])
    if set(out) != set(cands):
        raise RuntimeError(f"{r['id']}: rolled out {sorted(out)}, wanted {sorted(cands)}")
    return out


def rollout_queue(ties, chosen):
    """Near-ties a setup chose (one of the candidates) first, then the rest; stable by id."""
    def picked(pid, cands):
        return bool(set(chosen.get(pid, ())) & set(cands))
    items = sorted(ties.items())
    return [(pid, c, True) for pid, c in items if picked(pid, c)] + \
           [(pid, c, False) for pid, c in items if not picked(pid, c)]


def rollout(opts, db):
    rows = load_positions(opts["positions"])
    chosen = json.load(open(opts["chosen"])) if "chosen" in opts else {}
    done = {p for (p,) in db.execute("SELECT DISTINCT position FROM rollouts")}
    ties = {p: json.loads(c) for p, c in db.execute("SELECT position, candidates FROM near_ties")
            if p in rows and p not in done}
    if "ids" in opts:
        wanted = set(opts["ids"].split(","))
        ties = {p: c for p, c in ties.items() if p in wanted}
    queue = rollout_queue(ties, chosen)
    if "limit" in opts:
        queue = queue[: int(opts["limit"])]
    budget = float(opts.get("budget", "inf"))
    setup_rollouts(opts)
    t0, n, skipped = time.time(), 0, 0
    for pid, cands, was_chosen in queue:
        if not was_chosen and time.time() - t0 > budget:
            skipped += 1
            continue
        t = time.time()
        res = rollout_position(rows[pid], cands)
        secs = time.time() - t
        db.executemany("INSERT INTO rollouts VALUES (?,?,?,?,?,?,?,?,?,?)", [
            (pid, play, e, json.dumps(p), json.dumps(s), trials, int(opts.get("plies", 0)),
             int(opts.get("seed", 1)), int(was_chosen), secs) for play, (e, p, s, trials) in res.items()])
        db.commit()
        n += 1
        best = max(res.values())[0]
        print(f"{pid}: {len(cands)} plays, {secs:.1f} s, " + ", ".join(
            f"{play} {e:+.4f} ({e - best:+.4f})" for play, (e, *_rest) in sorted(res.items(), key=lambda x: -x[1][0])),
            flush=True)
    print(f"rollout: {n} near-ties in {time.time() - t0:.0f} s, {skipped} unchosen skipped for time", flush=True)


def main():
    mode, opts = parse_args()
    db = sqlite3.connect(opts["out"])
    db.executescript(SCHEMA)
    {"evaluate": evaluate, "rollout": rollout}[mode](opts, db)


try:
    main()
    os._exit(0)
except Exception:
    import traceback
    traceback.print_exc()
    os._exit(1)
