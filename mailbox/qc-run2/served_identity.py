"""QC 2026-11-12: the served model identity of every stored reply of one learning-lane arm, counted per step (tests),
per series game (games) and per series (lesson calls). Read-only; identities and counts only.
Usage: python3 served_identity.py MODEL-KEY POINTER   e.g. gemini-4-argon-on /response/modelVersion"""
import collections, json, sqlite3, sys
from pathlib import Path

key, ptr = sys.argv[1], sys.argv[2]
runs = Path("/home/cbasaran/code/jevgammon/workspace/improve/runs") / key
db = sqlite3.connect(f"file:/home/cbasaran/code/jevgammon/smoke/improve/{key}.db?mode=ro", uri=True)


def ident(raw):
    try:
        v = json.loads(raw)
    except (TypeError, ValueError):
        return None
    for part in ptr.strip("/").split("/"):
        v = v.get(part) if isinstance(v, dict) else None
    return v


c = collections.defaultdict(collections.Counter)
for setup, raw in db.execute("SELECT a.setup, x.response FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id"):
    c["test " + setup.split("| improve | ")[1]][ident(raw)] += 1
series = {int((runs / f"S{s}" / "match.done").read_text()): s for s in range(1, 6)}
for m, rnd, leg, raw in db.execute("SELECT g.match_id, g.round_no, g.leg, x.response FROM exchanges x JOIN turns t ON "
                                   "t.id = x.turn_id JOIN games g ON g.id = t.game_id WHERE t.player = 1"):
    if m in series:
        c[f"S{series[m]} game {2 * (rnd - 1) + leg:02d}"][ident(raw)] += 1
for s in range(1, 6):
    for g in range(1, 11):
        call = json.loads((runs / f"S{s}" / f"lessons-g{g:02d}.call.json").read_text())
        for x in call["exchanges"]:
            c[f"S{s} lesson g{g:02d}"][ident(x["response"])] += 1
print(json.dumps(dict(model=key, pointer=ptr, counts={k: dict(v) for k, v in sorted(c.items())}), indent=1))
