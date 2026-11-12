"""QC 2026-11-12 Run 2 planning (Zeki #5276): does every series of a learning-lane arm start from a reset, with no
context inherited from another series? Read-only (sqlite mode=ro, files read only). From the stored requests,
files and log hashes of one arm:
  1. every model game turn's request carries exactly contexts/after-g(N-1).txt of its OWN series (game 1: no notes);
  2. every T10 request carries exactly its own series' contexts/after-g10.txt; E runs carry no notes;
  3. contexts/after-gN.txt == improve.lessons_context(lessons-g01..gN of the same series), and its sha256 equals the
     log's `context` event for (step, after_game N);
  4. lessons-gN.txt == improve.limit_lessons(call.json text); the lesson call sends lesson-system.txt and
     lessons-gN.user.txt only; the user template takes {game} and {record} only;
  5. no lesson line of another series appears in any request of this series (games, T10, lesson calls).
Usage: python3 verify_series_reset.py MODEL-KEY"""
import hashlib, json, re, sqlite3, string, sys
from pathlib import Path

sys.path.insert(0, "/home/cbasaran/code/jevgammon-improve/workspace/improve")
import improve as I  # noqa: E402

key = sys.argv[1]
R = I.mdir(key)
db = sqlite3.connect(f"file:{I.db_path(key)}?mode=ro", uri=True)
NOTE = re.compile(re.escape(I.OPEN) + r".*?" + re.escape(I.CLOSE), re.S)
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def text_of(request):
    try:
        return "\n".join(strings(json.loads(request)))
    except (TypeError, ValueError):
        return request or ""


def notes(request):
    return NOTE.findall(text_of(request))


events = I.events(key)
ctx_sha = {}
for e in events:
    if e["event"] == "context":
        ctx_sha[(e["step"], e["after_game"])] = e["sha256"]  # the last one per (step, game): the used attempt

fields = [f for _, f, _, _ in string.Formatter().parse(I.LESSONS_USER.read_text()) if f]
out = dict(model=key, lesson_user_template_fields=sorted(set(fields)), series={}, empty_runs={})
lines_of = {}
for s in range(1, I.SERIES + 1):
    d = R / f"S{s}"
    lines_of[s] = {x.strip() for g in range(1, 11) if (d / f"lessons-g{g:02d}.txt").exists()
                   for x in (d / f"lessons-g{g:02d}.txt").read_text().splitlines() if x.strip().startswith("- ")}

for s in range(1, I.SERIES + 1):
    step, d = f"S{s}", R / f"S{s}"
    agg = json.loads((d / "aggregate.json").read_text())
    match_id = int((d / "match.done").read_text())
    r = dict(match=match_id, attempt=agg["attempt"])
    # 3 + 4: contexts and lessons
    ctx_ok = lesson_ok = call_ok = log_ok = 0
    call_leak = 0
    for g in range(1, 11):
        blocks = [(k, (d / f"lessons-g{k:02d}.txt").read_text().strip()) for k in range(1, g + 1)]
        ctx = (d / "contexts" / f"after-g{g:02d}.txt").read_text()
        ctx_ok += ctx == I.lessons_context(blocks)
        log_ok += ctx_sha.get((step, g)) == sha(ctx)
        call = json.loads((d / f"lessons-g{g:02d}.call.json").read_text())
        lesson_ok += (d / f"lessons-g{g:02d}.txt").read_text() == I.limit_lessons((call.get("text") or "").strip())[0] + "\n"
        sent = "\n".join(text_of(x["request"]) for x in call["exchanges"])
        call_ok += (d / "lesson-system.txt").read_text() in sent and (d / f"lessons-g{g:02d}.user.txt").read_text() in sent \
            and not NOTE.search(sent)
        call_leak += any(x in sent for o in lines_of for x in lines_of[o])
    r.update(contexts_recomputed=f"{ctx_ok}/10", contexts_log_sha=f"{log_ok}/10", lessons_recomputed=f"{lesson_ok}/10",
             lesson_calls_own_files_no_notes=f"{call_ok}/10", lesson_calls_with_any_lesson_line=call_leak)
    # 1: game turns
    games = {gid: 2 * (rnd - 1) + leg for gid, rnd, leg in
             db.execute("SELECT id, round_no, leg FROM games WHERE match_id = ?", (match_id,))}
    ok = bad = 0
    first_game_notes = 0
    foreign = 0
    for gid, req in db.execute(
            "SELECT t.game_id, x.request FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games g ON g.id = t.game_id "
            "WHERE g.match_id = ?", (match_id,)):
        g = games[gid]
        found = notes(req)
        want = [] if g == 1 else [(d / "contexts" / f"after-g{g - 1:02d}.txt").read_text()]
        want = [w for w in want if w]
        if g == 1 and found:
            first_game_notes += 1
        if found == want:
            ok += 1
        else:
            bad += 1
        t = text_of(req)
        foreign += any(x in t for o in lines_of if o != s for x in lines_of[o] - lines_of[s])
    r.update(game_exchanges_own_context=ok, game_exchanges_other=bad, game1_exchanges_with_notes=first_game_notes,
             game_exchanges_with_another_series_lesson=foreign)
    # 2: T10
    name = I.test_name(key, step, agg["attempt"])
    want = (d / "contexts" / "after-g10.txt").read_text()
    ok = bad = foreign = 0
    for (req,) in db.execute("SELECT x.request FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id "
                             "WHERE a.setup = ?", (name,)):
        if notes(req) == [want]:
            ok += 1
        else:
            bad += 1
        t = text_of(req)
        foreign += any(x in t for o in lines_of if o != s for x in lines_of[o] - lines_of[s])
    r.update(t10_setup=name, t10_exchanges_own_after_g10=ok, t10_exchanges_other=bad,
             t10_exchanges_with_another_series_lesson=foreign, after_g10_sha256=sha(want))
    out["series"][step] = r

for e in ("E1", "E2", "E3"):
    name = I.test_name(key, e)
    n, with_notes = 0, 0
    for (req,) in db.execute("SELECT x.request FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id "
                             "WHERE a.setup = ?", (name,)):
        n += 1
        with_notes += bool(notes(req))
    out["empty_runs"][e] = dict(setup=name, exchanges=n, with_notes=with_notes)
print(json.dumps(out, indent=1))
