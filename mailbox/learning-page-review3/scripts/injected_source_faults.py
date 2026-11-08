"""Injected faults in the pilot's files (not the page): each is put into a fresh copy of the SYNTHETIC complete fixture
(make_fixture.py) and the site's reading (learning_page.data -> learning_validate) must either refuse the file (no
number shown) or refuse "complete" (no lift, signal or ranking). The unaltered fixture must be accepted as complete.

    python3 injected_source_faults.py SITE_TOOLS FIXTURE_COMPLETE TEST_SET

Problem texts name fields only; no private value is printed.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

tools, fixture, test_set = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(tools))
import learning_page as LP  # noqa: E402


def summary(change):
    def f(src):
        p = src / "learning-pilot.json"
        R = json.loads(p.read_text())
        change(R)
        p.write_text(json.dumps(R))
    return f


def agg(arm, s, change):
    def f(src):
        p = src / "runs" / arm / f"s{s:02d}" / "aggregate.json"
        A = json.loads(p.read_text())
        change(A)
        p.write_text(json.dumps(A))
    return f


def edit_file(rel, text):
    def f(src):
        (src / rel).write_text(text)
    return f


def remove(rel):
    def f(src):
        (src / rel).unlink()
    return f


REJECT, NOT_COMPLETE = "file refused", "complete refused"
FAULTS = [
    ('complete as the string "true"', summary(lambda R: R.update(complete="true")), REJECT),
    ("an unknown top-level key", summary(lambda R: R.update(verdict="learns")), REJECT),
    ("a fifth arm", summary(lambda R: R["protocol"].update(arms=R["protocol"]["arms"] + ["extra"])), REJECT),
    ("planned series 2 instead of 10", summary(lambda R: R.update(planned_series_per_arm=2)), REJECT),
    ("another lesson prompt hash", summary(lambda R: R["protocol"].update(lesson_prompt_sha256="0" * 64)), REJECT),
    ("another evaluation set hash", summary(lambda R: R["protocol"].update(test_set_sha256="0" * 64)), REJECT),
    ("an inventory entry with another evaluation set hash",
     summary(lambda R: R["inventory"]["records"]["3"].update(test_set_sha256="0" * 64)), REJECT),
    ("t0_done as 1, not true", summary(lambda R: R.update(t0_done=1)), REJECT),
    ("a dry run claiming complete", summary(lambda R: R["protocol"].update(dry_run=True)), NOT_COMPLETE),
    ("series 10 of budget not finished", summary(lambda R: R["series_finished"].update(budget=list(range(1, 10)))),
     NOT_COMPLETE),
    ("a tampered learning lift", summary(lambda R: R["learning_lift"]["records"].update(vs_control=9.9)), NOT_COMPLETE),
    ("a signal flag not following the rule", summary(lambda R: R["signal"]["records"].update(signal=True)),
     NOT_COMPLETE),
    ("T10 answered 199 of 200 (records s04)", agg("records", 4, lambda A: A["evaluations"]["T10"].update(answered=199)),
     NOT_COMPLETE),
    ("games 8-10 error rate not following from the games (lessons s02)",
     agg("lessons", 2, lambda A: A.update(games_error_rate_8_10=(A["games_error_rate_8_10"] or 0) + 1)), NOT_COMPLETE),
    ("a lesson file changed after the inventory (lessons s05 game 3)",
     edit_file("runs/lessons/s05/lessons-g03.txt", "- an edited lesson\n"), NOT_COMPLETE),
    ("the T0 aggregate missing", remove("runs/t0/aggregate.json"), NOT_COMPLETE),
    ("a budget point with tokens as a string (budget s01)",
     agg("budget", 1, lambda A: A.update(budget_points=[dict(after_game=1, games_shown=[], games_dropped=1,
                                                             tokens="0", budget_tokens=226)])), NOT_COMPLETE),
]


def outcome(src: Path):
    L = LP.data(LP.PLAN, src, test_set)
    v = L["validation"] or {}
    return L, v


L, v = outcome(fixture)
base_ok = v.get("accepted") and v.get("complete") and not v.get("problems")
print(f"baseline (synthetic complete fixture): accepted={v.get('accepted')} complete={v.get('complete')} "
      f"problems={len(v.get('problems', []))}")
passed = 0
for name, inject, want in FAULTS:
    with tempfile.TemporaryDirectory(prefix="lp-srcfault-") as t:
        src = Path(t) / "src"
        shutil.copytree(fixture, src)
        inject(src)
        L, v = outcome(src)
        got = REJECT if not v.get("accepted") else NOT_COMPLETE if not v.get("complete") else "accepted as complete"
        hidden = not L["results"] or not any(k in L["results"] for k in LP.COMPLETE_ONLY_KEYS)
        ok = got == want and hidden
        passed += ok
        print(f"\n== {name}: expected {want}, got {got}{'' if hidden else ' (lift/signal still in data!)'}: "
              f"{'OK' if ok else 'FAIL'}")
        for p in v.get("problems", []):
            print("   ", p)
print(f"\n{passed} / {len(FAULTS)} source faults handled as expected; baseline {'accepted' if base_ok else 'NOT accepted'}")
sys.exit(0 if passed == len(FAULTS) and base_ok else 1)
