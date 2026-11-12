"""QC 2026-11-12, Zeki #5362 item 2: measured counts around a lane's step-boundary binary switch (read-only).
For MODEL and the step started on the old build and paused by the switch hold (e.g. qwen3.8-27b-on E3): from the
lane database, the answers, answer exchanges (request attempts) and harness commit per answer of that step, split
by build (the runner records git HEAD of its build tree: the old 1270c04 copy reports the jevgammon-improve checkout
HEAD, the new copy reports 8b6f9a1); the first request on the new build (ids, time, sha256 of the request body);
the step's log events and files with times. Counts, ids, times and hashes only.
Usage: python3 boundary_counts.py MODEL STEP NEW_COMMIT"""
import hashlib, json, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

key, step, new = sys.argv[1:4]
DB = Path("/home/cbasaran/code/jevgammon/smoke/improve") / f"{key}.db"
D = Path("/home/cbasaran/code/jevgammon/workspace/improve/runs") / key
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
like = f"% | improve | {step}" if step.startswith("E") else f"% | improve | s{int(step[1:]):02d} | %"
ev = [json.loads(x) for x in (D / "log.jsonl").read_text().splitlines()]
switch = [e for e in ev if e["event"] == "binary_switch"]
answers = {}
for commit, dirty, n, first, last in db.execute(
        "SELECT harness_commit, harness_dirty, COUNT(*), MIN(created_at), MAX(created_at) FROM answers WHERE setup LIKE ? "
        "GROUP BY 1, 2", (like,)):
    answers[f"{commit} dirty={dirty}"] = dict(answers=n, first_created=first, last_created=last,
                                              build="new" if commit.startswith(new) else "old")
attempts = {}
for commit, n, mx, first_id in db.execute(
        "SELECT a.harness_commit, COUNT(x.id), MAX(x.attempt), MIN(x.id) FROM answer_exchanges x JOIN answers a ON "
        "a.id = x.answer_id WHERE a.setup LIKE ? GROUP BY 1", (like,)):
    attempts[commit] = dict(exchanges=n, max_attempt=mx, first_exchange_id=first_id)
first = db.execute("SELECT x.id, x.answer_id, x.attempt, a.created_at, a.harness_commit, x.request FROM answer_exchanges x "
                   "JOIN answers a ON a.id = x.answer_id WHERE a.setup LIKE ? ORDER BY x.id LIMIT 1", (like,)).fetchone()
files = {p.name: datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="milliseconds")
         for p in sorted((D / step).iterdir())} if (D / step).exists() else {}
out = dict(
    model=key, step=step, setup_pattern=like,
    switch=[dict(at=s["at"], after_step=s["after_step"], from_sha256=s["from_sha256"], to_sha256=s["to_sha256"]) for s in switch],
    step_events=[dict(at=e["at"], event=e["event"], binary_commit=(e.get("binary") or {}).get("commit"),
                      reason_prefix=(e.get("reason") or "")[:60] or None)
                 for e in ev if e.get("step") == step or (e["event"] in ("paused", "binary_switch") and e["at"] >= (switch[0]["at"][:13] if switch else "9"))],
    answers_by_recorded_harness=answers,
    answers_on_old_build=sum(v["answers"] for v in answers.values() if v["build"] == "old"),
    exchanges_by_recorded_harness=attempts,
    exchanges_on_old_build=sum(v["exchanges"] for c, v in attempts.items() if not c.startswith(new)),
    first_request=dict(exchange_id=first[0], answer_id=first[1], attempt=first[2], answer_created=first[3],
                       harness_commit=first[4], request_sha256=hashlib.sha256(first[5].encode()).hexdigest()) if first else None,
    step_files_mtime_utc=files,
    note="the old process wrote test-<step>.json and paused in improve.held() before any `jevgammon ask` started; the "
         "test log is written only after an asking round")
print(json.dumps(out, indent=1))
