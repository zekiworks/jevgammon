"""Regression tests of the exploratory file's validator (Ümit #2950/#2952), run against a given tools/site tree: each
fault case fails on the tree before this work (origin/main, which has no exploratory validation: the file is ignored)
and passes on the branch. Every case starts from a fresh copy of the explore state (make_states.py: the REAL pilot and
the REAL exploratory file as snapshot.py copies them) and puts one fault into explore.json. Where a fault would leave
the file's own spread inconsistent, the spread is recomputed from the faulted rows, so only the intended check can
catch it. The page is rendered from each result and checked (checks.check_learning).

    python3 explore_regressions.py SITE_TOOLS EXPLORE_SRC NO_EXPLORE_SRC TEST_SET

A fault case PASSES when the file is refused with its fixed code, the data file carries only the codes (no number, no
name from the file), the page shows the refusal note and no exploratory number, and check_learning finds nothing.
The control cases pass when the real file is accepted and shown (and, missing, when there is no block at all).
The agreement cases (final file) cover its schema (known run names, counts 0-200), symmetry, completeness, summary
and the bounds of the not-unanimous count.
"""
import json
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

tools, src_explore, src_none, test_set = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(tools))
import checks  # noqa: E402
import learning_page as LP  # noqa: E402

REL = "explore/explore.json"
CANARY = "CANARY_e81c"
METRICS = ("risks_found", "right_safety", "error_rate", "risk_judgement", "risk_appetite")


def edit(change, respread=False):
    def f(src):
        p = src / REL
        E = json.loads(p.read_text())
        change(E)
        if respread:
            runs = E["empty_context_runs"]
            groups = {"all": runs, "t0+retests": [r for r in runs if r["kind"] in ("t0", "retest")],
                      "retests": [r for r in runs if r["kind"] == "retest"],
                      "budget": [r for r in runs if r["kind"] == "budget"]}
            for g, rs in groups.items():
                for m in METRICS:
                    xs = [r[m] for r in rs if r[m] is not None]
                    E["spread"][g][m] = dict(n=len(xs), mean=statistics.fmean(xs), min=min(xs), max=max(xs),
                                             sd=statistics.stdev(xs) if len(xs) > 1 else None)
        p.write_text(json.dumps(E))
    return f


def run_named(E, name):
    return next(r for r in E["empty_context_runs"] if r["run"] == name)


def drop_retest_row(E):
    E["empty_context_runs"].remove(run_named(E, "retest r3 (4 in flight)"))


def drop_r5_everywhere(E):
    """Zeki #2993's missing-key case: r5 gone from the counts, the rows, the agreement counts and summary (recomputed),
    as a coherent file that simply does not name the 5th retest."""
    E["retest_answer_counts"].pop("5")
    E["empty_context_runs"].remove(run_named(E, "retest r5 (4 in flight)"))
    P = E["agreement"]["pairwise"]
    P.pop("r5")
    for m in P.values():
        m.pop("r5")
    retests = [f"r{k}" for k in range(1, 5)]
    budgets = [n for n in P if n.startswith("budget")]
    pair = lambda xs, ys: [P[a][b] for a in xs for b in ys if a != b]  # noqa: E731
    tri = lambda xs: [P[a][b] for i, a in enumerate(xs) for b in xs[i + 1:]]  # noqa: E731
    groups = {"T0 vs retests": pair(["T0"], retests), "retest vs retest": tri(retests),
              "T0 vs budget": pair(["T0"], budgets), "retests vs budget": pair(retests, budgets),
              "budget vs budget": tri(budgets)}
    for g, xs in groups.items():
        E["agreement"]["summary"][g] = dict(n=len(xs), mean=statistics.fmean(xs), min=min(xs), max=max(xs),
                                            sd=statistics.stdev(xs) if len(xs) > 1 else None)


ACCEPTED, NONE = "accepted", "no block"
CASES = [
    ("control", "the real exploratory file", None, ACCEPTED),
    ("control", "no exploratory file", "NONE", NONE),
    ("schema", "an unknown top-level key (a canary name)", edit(lambda E: E.update({CANARY: 1})), "schema"),
    ("schema", "the label changed", edit(lambda E: E.update(label="exploratory")), "schema"),
    ("schema", "lessons T10 risks found with 9 series", edit(
        lambda E: E["arm_minus_budget"]["lessons"]["T10"]["risks_found"]["per_series"].pop()), "schema"),
    ("schema", "a run with an extra key", edit(lambda E: E["empty_context_runs"][0].update(note="x")), "schema"),
    ("schema", "a run's risks found as a string", edit(lambda E: E["empty_context_runs"][3].update(risks_found="28")),
     "schema"),
    ("test-set", "another evaluation set's hash", edit(lambda E: E.update(test_set_sha256="0" * 64)), "test-set"),
    ("counts", "budget s02 T5 answered 199 (valid 199), spread recomputed",
     edit(lambda E: run_named(E, "budget s02 T5 (1 in flight)").update(answered=199, valid=199), True), "counts"),
    ("counts", "T0 invalid 1 with valid 200 (201 of 200)",
     edit(lambda E: run_named(E, "T0 (shared, 4 in flight)").update(invalid=1)), "counts"),
    ("arm-minus-budget", "records T5 risks found mean +0.1",
     edit(lambda E: E["arm_minus_budget"]["records"]["T5"]["risks_found"].update(
         mean=E["arm_minus_budget"]["records"]["T5"]["risks_found"]["mean"] + 0.1)), "arm-minus-budget"),
    ("arm-minus-budget", "lessons T10 error rate interval's upper bound moved",
     edit(lambda E: E["arm_minus_budget"]["lessons"]["T10"]["error_rate"]["ci"].__setitem__(1, 0.0)),
     "arm-minus-budget"),
    ("arm-minus-budget", "records T10 right safety series 4 changed (mean kept)",
     edit(lambda E: E["arm_minus_budget"]["records"]["T10"]["right_safety"]["per_series"].__setitem__(3, 9.0)),
     "arm-minus-budget"),
    ("rows", "budget s03 T5 risks found +1 (spread recomputed)",
     edit(lambda E: run_named(E, "budget s03 T5 (1 in flight)").update(
         risks_found=run_named(E, "budget s03 T5 (1 in flight)")["risks_found"] + 1), True), "rows"),
    ("rows", "the T0 row's error rate +0.5 (spread recomputed)",
     edit(lambda E: run_named(E, "T0 (shared, 4 in flight)").update(
         error_rate=run_named(E, "T0 (shared, 4 in flight)")["error_rate"] + 0.5), True), "rows"),
    ("rows", "budget s10 T10 row missing (spread recomputed)",
     edit(lambda E: E["empty_context_runs"].remove(run_named(E, "budget s10 T10 (1 in flight)")), True), "rows"),
    ("retests", "retest r2 counted 150 answers but its row is there", edit(
        lambda E: E["retest_answer_counts"].update({"2": 150})), "retests"),
    ("retests", "retest r3 counted 200 answers but no row (spread recomputed)", edit(drop_retest_row, True),
     "retests"),
    ("agreement", "pairwise not symmetric (r1 vs T0 changed only)",
     edit(lambda E: E["agreement"]["pairwise"]["r1"].update(T0=E["agreement"]["pairwise"]["r1"]["T0"] + 1)),
     "agreement"),
    ("agreement", "summary mean changed (T0 vs retests)",
     edit(lambda E: E["agreement"]["summary"]["T0 vs retests"].update(mean=7.0)), "agreement"),
    ("agreement", "a run name outside the known set (budget s11 T5)",
     edit(lambda E: E["agreement"]["pairwise"].update({"budget s11 T5": {}})), "schema"),
    ("agreement", "a count above 200", edit(lambda E: E["agreement"]["pairwise"]["T0"].update(r2=201)), "schema"),
    ("agreement", "a run of the rows missing from the counts (r5)",
     edit(lambda E: [E["agreement"]["pairwise"].pop("r5")] + [m.pop("r5") for m in E["agreement"]["pairwise"]
                                                               .values()]), "agreement"),
    ("agreement", "positions not unanimous across retests below the largest retest-vs-retest count",
     edit(lambda E: E["agreement"].update(positions_not_unanimous_across_retests=0)), "agreement"),
    ("spread", "budget risks found SD changed", edit(lambda E: E["spread"]["budget"]["risks_found"].update(sd=0.5)),
     "spread"),
    ("retests", "r5 missing everywhere (counts, row, agreement), the rest recomputed (Zeki #2993)",
     edit(drop_r5_everywhere, True), "retests"),
    ("spread", "retests (r1-r5) error rate SD changed (Zeki #2991's group)",
     edit(lambda E: E["spread"]["retests"]["error_rate"].update(sd=0.5)), "spread"),
    ("spread", "retests (r1-r5) risks found max changed",
     edit(lambda E: E["spread"]["retests"]["risks_found"].update(max=30.0)), "spread"),
    ("spread", "all-runs error rate max changed", edit(lambda E: E["spread"]["all"]["error_rate"].update(max=60.0)),
     "spread"),
    ("unreadable", "not JSON", lambda src: (src / REL).write_text("{not json"), "unreadable"),
]

passed = 0
for fix, name, fault, want in CASES:
    with tempfile.TemporaryDirectory(prefix="lp-explore-") as t:
        src, out = Path(t) / "src", Path(t) / "out"
        shutil.copytree(src_none if fault == "NONE" else src_explore, src)
        if callable(fault):
            fault(src)
        why = []
        try:
            L = LP.data(LP.PLAN, src, test_set, preregistration_only=False)
            X = L.get("explore")
            got = NONE if X is None else ACCEPTED if X["accepted"] else ", ".join(
                p.split(":")[0].removeprefix("explore.") for p in X["problems"])
            LP.render(out, L)
            page, data = (out / LP.PATH / "index.html").read_text(), (out / LP.DATA).read_text()
            if want not in (ACCEPTED, NONE):
                if X is None or set(X) != {"accepted", "problems"}:
                    why.append("the refused file is not reduced to its codes in the data file")
                if "Exploratory file not accepted" not in page:
                    why.append("no refusal note on the page")
            if CANARY in page or CANARY in data:
                why.append("a name from the file is published")
            why += checks.check_learning(out, test_set)
            ok = (got == want or want in got.split(", ")) and not why
        except Exception as e:  # noqa: BLE001
            got, ok = f"crash: {type(e).__name__}: {e}", False
        passed += ok
        print(f"\n== [{fix}] {name}: expected {want}, got {got}: {'PASS' if ok else 'FAIL'}")
        for w in why[:4]:
            print("   ", w)
print(f"\n{passed} / {len(CASES)} pass ({tools})")
sys.exit(0 if passed == len(CASES) else 1)
