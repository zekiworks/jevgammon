"""One regression test per fix of Zeki's final review of ad2fb4d (#2931), run against a given tools/site tree: each
fails on the tree before the fix (4149a01, ad2fb4d rebased) and passes on the fixed tree. Fault cases start from a
fresh copy of the REAL complete state (make_states.py: copied as snapshot.py copies it) with one fault put in; where
the producer would agree with its own faulted aggregates, the summary is recomputed (an honest producer), so only the
aggregate-level check can catch it. For cases 2-4, the copy's T0 aggregate also carries "dry": false, which the tree
before the fix needs to read a T0 at all (case 1), so that each case tests its own fix only.

    python3 zeki2931_regressions.py SITE_TOOLS REAL_SRC TEST_SET

Every case renders the full page from the result (learning_page.render) and checks it. A case PASSES when:
1. malformed T0 ({}, a list) -> refused (no exception), the refused page renders; the real T0 (no "dry" key) ->
   accepted complete;
2. canary names in an unknown top-level key, an unknown aggregate key, a map key outside its pattern, an arm
   directory and a series directory -> refused, and the canary is in neither the page nor its data file;
3. a finished budget series with a point missing, a point duplicated, or an empty-point list contradicting a point
   that shows a game -> refused;
4. an evaluation whose valid + invalid + failed is not answered (records s01 T5; the T0) -> refused; consistent
   nonzero failures (1 failed of 200) -> accepted (a control case: it passes before and after; the fix must not
   refuse disclosed failures).
The map-key canary's value is also not an int, so that the tree before the fix reaches the key's path.
No model call; nothing published.
"""
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

tools, real, test_set = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(tools))
import learning_page as LP  # noqa: E402
import learning_validate as V  # noqa: E402

CANARY = "CANARY_7f3a"


def jedit(rel, change):
    def f(src):
        p = src / rel
        d = json.loads(p.read_text())
        change(d)
        p.write_text(json.dumps(d))
    return f


def jreplace(rel, value):
    def f(src):
        (src / rel).write_text(json.dumps(value))
    return f


def resummarize(src):
    p = src / "learning-pilot.json"
    R = json.loads(p.read_text())
    T = json.loads((src / "runs/t0/aggregate.json").read_text())
    aggs = {arm: {int(d.name[1:]): json.loads((d / "aggregate.json").read_text())
                  for d in sorted((src / "runs" / arm).glob("s*")) if (d / "aggregate.json").exists()}
            for arm in V.ARMS}
    S = V.summary(T, aggs, R["protocol"], R["protocol"]["test_set_sha256"], R["protocol"]["lesson_prompt_sha256"])
    p.write_text(json.dumps(dict(updated_at=R["updated_at"]) | S))


def then(*fs):
    def f(src):
        for g in fs:
            g(src)
    return f


def with_dry(src):
    jedit("runs/t0/aggregate.json", lambda T: T.update(dry=False))(src)


def copy_dir(a, b):
    def f(src):
        shutil.copytree(src / a, src / b)
    return f


def dup_point(A):
    A["budget_points"][5] = dict(A["budget_points"][4])


def conflict_point(A):
    # point 3 shows game 3 (its tokens and drops agree with the context records), but 3 stays in the empty list
    A["budget_points"][2].update(games_shown=[3], games_dropped=2, tokens=100)
    A["context_tokens_after_game"]["3"], A["records_dropped_after_game"]["3"] = 100, 2


def impossible_eval(m):
    m.update(invalid=200)  # answered 200, valid 200, invalid 200


def one_failed(m):
    m.update(failed=1, valid=199)
    k = next(k for k, v in m["calls"].items() if v)
    m["calls"][k] -= 1


REFUSED, COMPLETE = "refused", "accepted complete"
CASES = [
    ("1", "malformed T0: an empty object", jreplace("runs/t0/aggregate.json", {}), REFUSED, False),
    ("1", "malformed T0: a list", jreplace("runs/t0/aggregate.json", [1, 2]), REFUSED, False),
    ("1", "the real T0 aggregate (no 'dry' key) with the real results", None, COMPLETE, False),
    ("2", "canary in an unknown top-level key of learning-pilot.json",
     jedit("learning-pilot.json", lambda R: R.update({CANARY: 1})), REFUSED, True),
    ("2", "canary in an unknown key of an aggregate (records s02)",
     jedit("runs/records/s02/aggregate.json", lambda A: A.update({CANARY: 1})), REFUSED, True),
    ("2", "canary as a map key outside its pattern (lessons s03 context_tokens_after_game)",
     jedit("runs/lessons/s03/aggregate.json", lambda A: A["context_tokens_after_game"].update({CANARY: "x"})),
     REFUSED, True),
    ("2", "canary as an arm directory (runs/<canary>/s01)", copy_dir("runs/records/s01", f"runs/{CANARY}/s01"),
     REFUSED, True),
    ("2", "canary as a series directory (runs/records/s<canary>)", copy_dir("runs/records/s01", f"runs/records/s{CANARY}"),
     REFUSED, True),
    ("3", "finished budget series with its last point missing (s04), summary recomputed",
     then(jedit("runs/budget/s04/aggregate.json", lambda A: A["budget_points"].pop()), resummarize), REFUSED, True),
    ("3", "finished budget series with a point duplicated (s05: point 5 twice, no point 6), summary recomputed",
     then(jedit("runs/budget/s05/aggregate.json", dup_point), resummarize), REFUSED, True),
    ("3", "empty-point list contradicting a point that shows a game (s06 game 3), summary recomputed",
     then(jedit("runs/budget/s06/aggregate.json", conflict_point), resummarize), REFUSED, True),
    ("4", "records s01 T5: valid 200 + invalid 200 for 200 answered, summary recomputed",
     then(jedit("runs/records/s01/aggregate.json", lambda A: impossible_eval(A["evaluations"]["T5"])), resummarize),
     REFUSED, True),
    ("4", "T0: valid 200 + invalid 200 for 200 answered, summary recomputed",
     then(jedit("runs/t0/aggregate.json", lambda T: impossible_eval(T["metrics"])), resummarize), REFUSED, True),
    ("4", "control: lessons s07 T10 with 1 failed of 200 (consistent), summary recomputed: still accepted",
     then(jedit("runs/lessons/s07/aggregate.json", lambda A: one_failed(A["evaluations"]["T10"])), resummarize),
     COMPLETE, True),
]

passed = 0
for fix, name, fault, want, dry in CASES:
    with tempfile.TemporaryDirectory(prefix="lp-2931-") as t:
        src, out = Path(t) / "src", Path(t) / "out"
        shutil.copytree(real, src)
        if dry:
            with_dry(src)
        why = ""
        try:
            if fault:
                fault(src)
            L = LP.data(LP.PLAN, src, test_set, preregistration_only=False)
            v = L["validation"]
            got = REFUSED if not v["accepted"] else COMPLETE if v["complete"] else "accepted, not complete"
            LP.render(out, L)
            page, data = (out / LP.PATH / "index.html").read_text(), (out / LP.DATA).read_text()
            if got == REFUSED and "Results file not accepted" not in page:
                why = "refused page without its note"
            if CANARY in page or CANARY in data:
                why = f"canary in the {'page' if CANARY in page else 'data file'}"
            problems = v["problems"]
        except Exception as e:  # noqa: BLE001 - a crash is the finding before fix 1
            got, problems = f"crash: {type(e).__name__}", [traceback.format_exception_only(e)[-1].strip()[:160]]
        ok = got == want and not why
        passed += ok
        print(f"\n== fix {fix}: {name}: expected {want}, got {got}{'; ' + why if why else ''}: "
              f"{'PASS' if ok else 'FAIL'}")
        for p in problems[:4]:
            print("   ", p.replace(str(src), "<src>"))
print(f"\n{passed} / {len(CASES)} pass ({tools})")
sys.exit(0 if passed == len(CASES) else 1)
