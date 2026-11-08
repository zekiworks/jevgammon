"""Zeki's synthetic_checks.py (sha256 in 03), its 8 cases ported to the current candidate. The original asserts each
VULNERABILITY (a raw summary normalised by read_results with no aggregates; an orphan lesson admitted by read_lessons;
...); it cannot run unchanged against this candidate (read_lessons and the summary-only read_results no longer exist:
see 03, part c3). Each case here puts Zeki's fault into a fresh copy of the REAL-derived fixtures (make_states.py) and
asserts the fixed outcome: the file is refused (nothing of it published, the refused page passes check_learning), the
build fails, or the check fails. Nothing is published; no model call.

    python3 zeki_synthetic_ported.py SITE_TOOLS REAL_COMPLETE_SRC SYNTHETIC_SMOKE_SRC TEST_SET
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

tools, real, smoke, test_set = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(tools))
import checks  # noqa: E402
import learning_page as LP  # noqa: E402

MISSING = Path(tempfile.gettempdir()) / "lp-no-such-test-set.json"


def summary(change):
    def f(src):
        p = src / "learning-pilot.json"
        R = json.loads(p.read_text())
        change(R)
        p.write_text(json.dumps(R))
    return f


def orphan_lesson(src):
    d = src / "runs/lessons/s99"
    d.mkdir(parents=True)
    (d / "aggregate.json").write_text(json.dumps({"series": 99, "games": []}))
    (d / "lessons-g01.txt").write_text("- Synthetic stale lesson.")


def html_series(src):
    p = src / "runs/lessons/s01/aggregate.json"
    A = json.loads(p.read_text())
    A["series"] = '<script>void("synthetic")</script>'
    p.write_text(json.dumps(A))


def no_checkpoints(src):
    for arm in ("records", "lessons", "budget"):
        for p in (src / "runs" / arm).glob("s*/aggregate.json"):
            A = json.loads(p.read_text())
            A["evaluations"] = {}
            p.write_text(json.dumps(A))


def no_prompt(src):
    for f in ("lessons_system.txt", "lessons_user.txt"):
        (src / f).unlink()


def no_lessons(src):
    for p in (src / "runs/lessons").glob("s*/lessons-g*.txt"):
        p.unlink()


# (Zeki's case, fixture, fault, test set, expected: "refused" | "build failed")
CASES = [
    ("incomplete_series_gate: complete true on 3 finished series", smoke,
     summary(lambda R: R.update(complete=True, learning_lift={"records": {"lift": 12}},
                                signal={"records": {"signal": True}})), test_set, "refused"),
    ("incomplete_series_gate: complete as the string 'false'", real, summary(lambda R: R.update(complete="false")),
     test_set, "refused"),
    ("incomplete_series_gate: planned 3 instead of 10", smoke,
     summary(lambda R: R.update(planned_series_per_arm=3)), test_set, "refused"),
    ("missing_private_set: lessons present, evaluation set missing", real, None, MISSING, "build failed"),
    ("nested_withheld_data: t0_done an object with lift, signal and answers", smoke,
     summary(lambda R: R.update(t0_done={"learning_lift": 12, "signal": True, "answers": ["synthetic-answer"],
                                         "per_position_evaluations": [0.125]})), test_set, "refused"),
    ("orphan_lesson: lessons s99 with no games", real, orphan_lesson, test_set, "refused"),
    ("series_metadata_html: series as a script tag (lessons s01)", real, html_series, test_set, "refused"),
    ("missing_prompt_binding: lesson prompt files absent", real, no_prompt, test_set, "refused"),
    ("completion_without_checkpoints_or_lessons: no T5/T10 in any arm", real, no_checkpoints, test_set, "refused"),
    ("completion_without_checkpoints_or_lessons: no lesson files", real, no_lessons, test_set, "refused"),
    ("producer_prompt_hash_not_bound: summary's lesson prompt hash 0...0", real,
     summary(lambda R: R.update(lesson_prompt_sha256="0" * 64)), test_set, "refused"),
]

passed = 0
for name, fixture, fault, ts, want in CASES:
    with tempfile.TemporaryDirectory(prefix="lp-zeki-") as t:
        src = Path(t) / "src"
        shutil.copytree(fixture, src)
        if fault:
            fault(src)
        errs, problems = [], []
        try:
            L = LP.data(LP.PLAN, src, ts, preregistration_only=False)
            v = L["validation"]
            got = "refused" if v and not v["accepted"] else "accepted"
            problems = (v or {}).get("problems", [])
            out = Path(t) / "out"
            LP.render(out, L)
            if L["results"] is not None or L["lessons"] or L["budget"]:
                errs.append("something of the refused file is published")
            errs += checks.check_learning(out, test_set)
        except LP.TestSetRequired as e:
            got, problems = "build failed", [str(e).replace(str(ts), "<test set>")]
        ok = got == want and not errs
        passed += ok
        print(f"\n== {name}: expected {want}, got {got}{'; ' + '; '.join(errs) if errs else ''}: "
              f"{'OK' if ok else 'FAIL'}")
        for p in problems[:4]:
            print("   ", p.replace(str(src), "<src>"))
print(f"\n{passed} / {len(CASES)} of Zeki's synthetic cases end as fixed")
sys.exit(0 if passed == len(CASES) else 1)
