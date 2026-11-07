"""Saved regression cases for the learning page's publication boundary (Zeki #2671/#2676 and earlier review faults).
SYNTHETIC data only: every case starts from a fresh copy of a SYNTHETIC fixture (make_fixture.py) and puts one fault
in it. Each case states the expected outcome:

- "build failed": learning_page.data raises TestSetRequired (nothing is built);
- "file refused": the site publishes no number, lesson or budget point of the file; the refused file's page is then
  rendered (learning_page.render, full page): it must render, show the "not accepted" note, no results, no
  complete-only block, and pass the leakage check;
- "not complete": accepted as running (no lift, signal or ranking published);
- "builds": the no-results state, which needs no evaluation set;
- page-level cases call checks.check_learning or render a page body directly.

Zeki's executed cases (his results.json, candidate 9d8c29b) are the ones marked [Zeki]; each is rebuilt here on the
fixture's real aggregate format.

    python3 regression_cases.py SITE_TOOLS FIXTURE_COMPLETE FIXTURE_RUNNING TEST_SET

Problem texts name fields only; no private value is printed.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

tools, fix_complete, fix_running, test_set = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(tools))
import checks  # noqa: E402
import learning_page as LP  # noqa: E402
import learning_validate as V  # noqa: E402

BUILD_FAIL, REJECT, NOT_COMPLETE, COMPLETE, BUILDS = ("build failed", "file refused", "not complete",
                                                       "accepted as complete", "builds")
MISSING = Path(tempfile.gettempdir()) / "lp-no-such-test-set.json"


# --- Fault helpers --------------------------------------------------------------------------------------------------

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


def edit_t0(change):
    def f(src):
        p = src / "runs/t0/aggregate.json"
        T = json.loads(p.read_text())
        change(T)
        p.write_text(json.dumps(T))
    return f


def edit_file(rel, text):
    def f(src):
        (src / rel).write_text(text)
    return f


def remove(rel):
    def f(src):
        p = src / rel
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    return f


def resummarize(src):
    """The summary an honest pilot.py would write for the (faulted) aggregates: the producer agrees with them."""
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


def set_path(path, value):
    """Sets R[path...] = value."""
    def change(R):
        d = R
        for k in path[:-1]:
            d = d[k]
        d[path[-1]] = value
    return change


C, RUN = "complete", "running"
# name, fixture, fault, expected, test set (None: the real one)
CASES = [
    # [Zeki] string_complete, wrong_prompt
    ('[Zeki] complete as the string "true"', C, summary(set_path(["complete"], "true")), REJECT),
    ("[Zeki] protocol lesson prompt hash not the plan's", C,
     summary(set_path(["protocol", "lesson_prompt_sha256"], "0" * 64)), REJECT),
    # [Zeki] running_missing_test_and_prompt_orphan_aggregate, split into its three faults
    ("[Zeki] running lessons, evaluation set missing", RUN, None, BUILD_FAIL, MISSING),
    ("[Zeki] running lessons, lesson prompt files missing", RUN,
     then(remove("lessons_system.txt"), remove("lessons_user.txt")), REJECT),
    ("[Zeki] running lessons, inventory claims a series whose aggregate is missing (lessons s03)", RUN,
     remove("runs/lessons/s03/aggregate.json"), REJECT),
    ("running lessons, aggregate missing and the summary recomputed without it (lessons s03 not published)", RUN,
     then(remove("runs/lessons/s03/aggregate.json"), resummarize), NOT_COMPLETE),
    ("running lessons, a lesson file edited after its aggregate (lessons s02 game 4)", RUN,
     edit_file("runs/lessons/s02/lessons-g04.txt", "- an edited lesson\n"), REJECT),
    ("running lessons, a lesson file missing (lessons s01 game 7)", RUN, remove("runs/lessons/s01/lessons-g07.txt"),
     REJECT),
    # [Zeki] nested_budget, budget_cell_exact_expression (render-level escape: see page cases below)
    ("[Zeki] literal HTML in budget games_shown (budget s01), summary recomputed", RUN,
     then(agg("budget", 1, lambda A: A["budget_points"][0].update(games_shown=["<b>SYNTHETIC_EARLY_VERDICT</b>"])),
          resummarize), REJECT),
    ("budget games_shown a game after the point (budget s02)", RUN,
     then(agg("budget", 2, lambda A: A["budget_points"][0].update(games_shown=[5], games_dropped=0)), resummarize),
     REJECT),
    # [Zeki] complete_wrong_run_identity
    ("[Zeki] aggregate names another arm (control s02 says records), summary recomputed", C,
     then(agg("control", 2, lambda A: A.update(arm="records")), resummarize), REJECT),
    ("[Zeki] aggregate names another series (records s04 says 999)", C,
     agg("records", 4, lambda A: A.update(series=999)), REJECT),
    ("[Zeki] aggregate with an unknown key run_id (lessons s01)", C,
     agg("lessons", 1, lambda A: A.update(run_id="SAME-RUN")), REJECT),
    ("aggregate with another series' dice seed (budget s05), summary recomputed", C,
     then(agg("budget", 5, lambda A: A.update(seed=V.series_seed(6))), resummarize), REJECT),
    ("an aggregate in a directory that is not a series (records s11)", C,
     lambda src: shutil.copytree(src / "runs/records/s01", src / "runs/records/s11"), REJECT),
    ("an aggregate under an arm the protocol does not have (runs/extra/s01)", C,
     lambda src: shutil.copytree(src / "runs/records/s01", src / "runs/extra/s01"), REJECT),
    # [Zeki] complete_unbound_table_and_nested_extra
    ("[Zeki] table records T0 and T10 risks found changed with a signal agreeing with the table", C,
     then(summary(lambda R: (R["table"]["records"]["T0"].update(risks_found=3.0),
                             R["table"]["records"]["T10"].update(risks_found=90.0),
                             R["signal"]["records"].update(risks_found_change=87.0, signal=True))), lambda s: None),
     REJECT),
    ("[Zeki] an extra literal field inside learning_lift.records", C,
     summary(lambda R: R["learning_lift"]["records"].update(extra_literal="SYNTHETIC_LITERAL_DATA")), REJECT),
    ("an extra literal field inside a table row", C,
     summary(lambda R: R["table"]["lessons"]["T5"].update(note="<i>SYNTHETIC</i>")), REJECT),
    ("a T0 row of one arm differing from the shared T0", C,
     summary(lambda R: R["table"]["budget"]["T0"].update(error_rate=20.0)), REJECT),
    ("T0 aggregate changed after the summary (risks found)", C,
     edit_t0(lambda T: T["metrics"].update(risks_found=60.0)), REJECT),
    ("T0 aggregate changed and the summary recomputed: published T0 and signal follow the aggregate", C,
     then(edit_t0(lambda T: T["metrics"].update(risks_found=60.0)), resummarize), COMPLETE),
    # earlier review faults, on the new boundary
    ("an unknown top-level key", C, summary(lambda R: R.update(verdict="learns")), REJECT),
    ("a fifth arm in the protocol", C, summary(lambda R: R["protocol"].update(arms=R["protocol"]["arms"] + ["x"])),
     REJECT),
    ("planned series 2 instead of 10", C, summary(set_path(["planned_series_per_arm"], 2)), REJECT),
    ("another evaluation set hash in the protocol", C, summary(set_path(["protocol", "test_set_sha256"], "0" * 64)),
     BUILD_FAIL),
    ("an aggregate made with another evaluation set (records s03), summary recomputed", C,
     then(agg("records", 3, lambda A: A.update(test_set_sha256="0" * 64)), resummarize), REJECT),
    ("an aggregate made with another lesson prompt (budget s07)", C,
     agg("budget", 7, lambda A: A.update(lesson_prompt_sha256="1" * 64)), REJECT),
    ("the results file not JSON", C, edit_file("learning-pilot.json", "{not json"), REJECT),
    ("t0_done as 1, not true", C, summary(set_path(["t0_done"], 1)), REJECT),
    ("a dry run claiming complete", C, summary(set_path(["protocol", "dry_run"], True)), REJECT),
    ("a dry run, summary recomputed (T0 dry too)", C,
     then(edit_t0(lambda T: T.update(dry=True)), summary(set_path(["protocol", "dry_run"], True)), resummarize),
     NOT_COMPLETE),
    ("series 10 of budget not finished in the summary only", C,
     summary(lambda R: R["series_finished"].update(budget=list(range(1, 10)))), REJECT),
    ("a tampered learning lift", C, summary(lambda R: R["learning_lift"]["records"].update(vs_control=9.9)), REJECT),
    ("a tampered lift interval", C, summary(lambda R: R["learning_lift"]["lessons"].update(lift_ci=[0.0, 1.0])),
     REJECT),
    ("a signal flag not following the rule", C, summary(lambda R: R["signal"]["records"].update(signal=True)), REJECT),
    ("T10 answered 199 of 200 (records s04), summary not updated", C,
     agg("records", 4, lambda A: A["evaluations"]["T10"].update(answered=199)), REJECT),
    ("T10 answered 199 of 200 (records s04), summary recomputed: not complete, s04 not published", C,
     then(agg("records", 4, lambda A: A["evaluations"]["T10"].update(answered=199)), resummarize), NOT_COMPLETE),
    ("games 8-10 error rate not following from the games (lessons s02)", C,
     agg("lessons", 2, lambda A: A.update(games_error_rate_8_10=(A["games_error_rate_8_10"] or 0) + 1)), REJECT),
    ("a game's error rate not following from its losses (control s06)", C,
     then(agg("control", 6, lambda A: A["games"][0].update(error_rate=1.0)), resummarize), REJECT),
    ("a lesson file changed after the aggregate (lessons s05 game 3)", C,
     edit_file("runs/lessons/s05/lessons-g03.txt", "- an edited lesson\n"), REJECT),
    ("the T0 aggregate missing", C, remove("runs/t0/aggregate.json"), REJECT),
    ("a budget point with tokens as a string (budget s01)", C,
     agg("budget", 1, lambda A: A["budget_points"][0].update(tokens="0")), REJECT),
    ("an evaluation metric as an object (records s02 T5 risks_found)", C,
     agg("records", 2, lambda A: A["evaluations"]["T5"].update(risks_found={"v": 1})), REJECT),
    ("an evaluation rate out of range (lessons s08 T10 right_safety 140)", C,
     then(agg("lessons", 8, lambda A: A["evaluations"]["T10"].update(right_safety=140.0)), resummarize), REJECT),
    ("a game result not in the allowed values (records s01 game 2)", C,
     then(agg("records", 1, lambda A: A["games"][1].update(result="<script>")), resummarize), REJECT),
    ("missing evaluation set, SYNTHETIC complete results", C, None, BUILD_FAIL, MISSING),
    ("unreadable evaluation set (a directory), SYNTHETIC running results", RUN, None, BUILD_FAIL, "DIR"),
    ("missing evaluation set, aggregates but no results file", RUN, remove("learning-pilot.json"), BUILD_FAIL,
     MISSING),
    ("missing evaluation set, a lesson file but no results file and no aggregates", RUN,
     then(remove("learning-pilot.json"), lambda src: [p.unlink() for p in (src / "runs").rglob("aggregate.json")]),
     BUILD_FAIL, MISSING),
    ("missing evaluation set, no results (empty source)", "empty", None, BUILDS, MISSING),
]


def outcome(src: Path, ts: Path):
    try:
        L = LP.data(LP.PLAN, src, ts, preregistration_only=False)
    except LP.TestSetRequired as e:
        return None, BUILD_FAIL, [str(e).replace(str(ts), "<test set>")]
    v = L["validation"]
    if v is None:
        return L, BUILDS, []
    got = REJECT if not v["accepted"] else COMPLETE if v["complete"] else NOT_COMPLETE
    return L, got, v["problems"]


def render_refused(L) -> list:
    """A refused file's whole page: renders, shows no results and no complete-only block, says the file was not
    accepted, passes the leakage check."""
    errs = []
    with tempfile.TemporaryDirectory(prefix="lp-render-") as t:
        try:
            page = LP.render(Path(t), L).read_text()
        except Exception as e:  # noqa: BLE001 - any crash is the finding
            return [f"render crashed: {type(e).__name__}: {e}"]
        if L["results"] is not None or L["lessons"] or L["budget"]:
            errs.append("results, lessons or budget points published")
        if "Results file not accepted" not in page:
            errs.append("no 'not accepted' note")
        tree = checks.Tree()
        tree.feed(page)
        ids = {n.attrs.get("id") for n in checks.walk(tree.root)}
        errs += [f"block #{i} shown" for i in LP.COMPLETE_ONLY_IDS if i in ids]
        errs += checks.check_learning(Path(t), test_set)
    return errs


def published_ok(L, got) -> list:
    """Accepted states: the data file carries only the projection's keys; no complete-only key unless complete."""
    if got not in (NOT_COMPLETE, COMPLETE):
        return []
    R = L["results"]
    errs = []
    if got == NOT_COMPLETE and any(k in R for k in LP.COMPLETE_ONLY_KEYS):
        errs.append("complete-only key published while not complete")
    for arm, by_cp in R["table"].items():
        for cp, row in by_cp.items():
            extra = set(row or {}) - {k for k, *_ in LP.METRICS} - {"shared"}
            if extra:
                errs.append(f"table.{arm}.{cp}: unexpected keys published")
    return errs


passed = total = 0
unreadable = Path(tempfile.mkdtemp(prefix="lp-test-set-dir-"))
for case in CASES:
    name, which, inject, want = case[:4]
    ts = case[4] if len(case) > 4 else test_set
    ts = unreadable if ts == "DIR" else ts
    with tempfile.TemporaryDirectory(prefix="lp-case-") as t:
        src = Path(t) / "src"
        if which == "empty":
            src.mkdir()
        else:
            shutil.copytree(fix_complete if which == C else fix_running, src)
        if inject:
            inject(src)
        L, got, problems = outcome(src, ts)
        extra = render_refused(L) if got == REJECT else published_ok(L, got)
        ok = got == want and not extra
        passed += ok
        total += 1
        print(f"\n== {name}: expected {want}, got {got}"
              f"{'; refused-file page render: ' + ('clean' if not extra else '; '.join(extra)) if got == REJECT else ''}"
              f"{'; projection: ' + '; '.join(extra) if extra and got != REJECT else ''}: {'OK' if ok else 'FAIL'}")
        for p in problems[:6]:
            print("   ", p.replace(str(src), "<src>").replace(str(unreadable), "<directory>"))
        if len(problems) > 6:
            print(f"    … {len(problems) - 6} more")
unreadable.rmdir()

# Page-level cases: the leakage check without the evaluation set, and escaping of every published budget value.
print("\n# page-level cases")


def page_case(name, ok, detail=""):
    global passed, total
    passed += ok
    total += 1
    print(f"\n== {name}: {'OK' if ok else 'FAIL'}{(' (' + detail + ')') if detail else ''}")


with tempfile.TemporaryDirectory(prefix="lp-empty-") as empty:
    for name, src, want_fail in [("[Zeki] leakage check, SYNTHETIC running page, evaluation set missing",
                                  fix_running, True),
                                 ("leakage check, SYNTHETIC complete page, evaluation set missing", fix_complete, True),
                                 ("leakage check, no-results page, evaluation set missing", Path(empty), False)]:
        with tempfile.TemporaryDirectory(prefix="lp-page-") as t:
            LP.render(Path(t), LP.data(LP.PLAN, src, test_set, preregistration_only=False))
            bad = checks.check_learning(Path(t), MISSING)
            page_case(name, bool(bad) == want_fail, f"{len(bad)} failure(s)")

L = LP.data(LP.PLAN, fix_running, test_set, preregistration_only=False)
L["budget"][0]["points"][0]["games_shown"] = ["<b>SYNTHETIC_EARLY_VERDICT</b>"]
L["lessons"][0]["text"] = "<script>SYNTHETIC</script>"
html = LP.body(L)
page_case("[Zeki] budget cell and lesson text with literal HTML are escaped in the body",
          "<b>SYNTHETIC" not in html and "<script>SYNTHETIC" not in html and "&lt;b&gt;SYNTHETIC" in html)
for name, v in [("[Zeki] body of a rejected file's validation shape (accepted/problems only)",
                 dict(accepted=False, problems=["synthetic"])),
                ("body of the typed rejected shape", LP.rejected(["synthetic"]))]:
    Lr = dict(L, results=None, lessons=[], budget=[], validation=v)
    try:
        h = LP.body(Lr)
        page_case(name, "Results file not accepted" in h and "Pre-registration" not in h)
    except Exception as e:  # noqa: BLE001
        page_case(name, False, f"{type(e).__name__}: {e}")

print(f"\n{passed} / {total} regression cases handled as expected")
sys.exit(0 if passed == total else 1)
