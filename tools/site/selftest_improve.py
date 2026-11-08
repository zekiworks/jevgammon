#!/usr/bin/env python3
"""Self-test of the "Did they improve?" page (improve_page.py, improve_validate.py, checks.check_improve): writes
SYNTHETIC improve.json states to a temp dir in snapshot.py's STATE/improve layout, renders each with the results view
(review renders: preregistration_only off) and checks the outcome.

    python3 tools/site/selftest_improve.py [--keep DIR] [--workspace DIR]

--workspace: the directory holding learning-pilot/ (the lesson prompt files and the private test_set.json); default
the repository's workspace/ (untracked: a worktree points it at the main checkout's).

States (every number and lesson SYNTHETIC; never results):
  none           no improve.json: the pre-registration view, no status of any model;
  running-1      Qwen3.8 Flash (off) running, E1 and S1 (with its test after game 10) done: live numbers, "running,
                 1 of 5 series", no Yes/No;
  complete-yes   Qwen3.8 Flash (off) complete, change in risks found +6.0 against a threshold of 5, right safety -1.4:
                 Yes;
  complete-no    GLM-5.3 (on) complete, change +5.0 against its own range 6: No;
  mixed          Qwen Yes, GLM No, Kimi paused (balance), DeepSeek running mid-series 3, Gemini stopped, Gemma 4 31B
                 (on) running locally ("running on our GPU, 0 of 5 series"): the sort order and every status;
  paused         Kimi K3.1 Pro (off) paused (shared-balance priority), GPT-6.1 Sol (high) not started (waiting for the
                 ChatGPT reset 13 Nov);
  status table   the default build (pre-registration only) in states none, running-1, paused and complete-yes (done):
                 the "Models and status" table at the top, 15 rows as the data's progress fields, no outcome number
                 and no free-text reason from the file on the page or in its data file;
  status faults  the progress fields with one fault each (status outside the enum, series_done 6, missing, a reason
                 outside the fixed list, ...): refused by the full validation (in faults) and by the default build's
                 status view (every status unknown, the "Status unavailable" note, no name from the file);
  faults         complete-yes with one injected fault each (bad hashes, counts that do not add up, unknown keys, a
                 setup outside the plan, a verdict-gate violation, a test position in a lesson, ...): each refused,
                 the page the pre-registration view with the "Data refused" note, no name from the file in it;
  page faults    the complete-yes page with one fault injected each (a verdict before the gate, a wrong number, rows
                 out of order, a missing pre-registered text, a test position): each detected by check_improve.
Exit 0 when every case comes out as expected; 1 otherwise. Writes nothing outside the temp dir (or --keep DIR)."""

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks  # noqa: E402
import improve_page as IP  # noqa: E402
import improve_validate as V  # noqa: E402

WS = {"dir": IP.ROOT / "workspace"}  # set from --workspace
CANARY_KEY, CANARY_SETUP = "zz_canary_key_7f3a", "Canary Model 9 (x)"


def TS() -> Path:
    return WS["dir"] / "learning-pilot" / "test_set.json"


def test(rf, rs, er, invalid=0, failed=0, risk_pays=None, safety_pays=None):
    """One SYNTHETIC test: rf/rs risks found / right safety as counts of their positions answered validly."""
    valid = 200 - invalid - failed
    rp = risk_pays if risk_pays is not None else valid // 2
    sp = valid - rp if safety_pays is None else safety_pays
    return dict(answered=200 - failed, expected=200, valid=valid, invalid=invalid, failed=failed, risk_pays=rp,
                safety_pays=sp, risks_found=100 * rf / rp if rp else None,
                right_safety=100 * rs / sp if sp else None, error_rate=er if valid else None,
                answer_rate=100 * valid / 200, in_flight_max=4, wall_seconds=611.5)


LESSON = ("- (SYNTHETIC) Hit loose blots when the opponent's home board is weak.\n"
          "- (SYNTHETIC) Keep a back anchor while behind in the race.\n- (SYNTHETIC) Prime before attacking.")


def series(n, t10, games=10, finished=True):
    lessons = [dict(game=g, text="" if g == 4 else LESSON) for g in range(1, (games if finished else games - 1) + 1)]
    return dict(series=n, finished=finished, games=games, wins=games // 3, game_decisions=games * 21,
                game_invalid=1, lesson_calls=len(lessons) + 1, lessons_cut=1 if len(lessons) > 2 else 0,
                lessons_empty=sum(1 for x in lessons if not x["text"]), restarts=0, lessons=lessons,
                t10=t10 if finished else None)


PROGRESS_OF = {"complete": "done", "running": "running", "paused": "paused", "stopped": "stopped",
               "incomplete": "stopped"}


def model(pm, state, steps, empties, t10s, partial=None, reason=None, billed_usd=0.0, api=None, why=None):
    """why: the progress reason (one of improve_validate.PROGRESS_REASONS); paused models default to the balance one."""
    sers = [series(i + 1, t) for i, t in enumerate(t10s)]
    if partial:
        sers.append(series(len(sers) + 1, None, games=partial, finished=False))
    billed = pm["billed"]
    why = why or (V.PROGRESS_REASONS[0] if state == "paused" else None)
    return dict(key=pm["key"], setup=pm["setup"], route=pm["route"], billed=billed, state=state, reason=reason,
                steps_done=steps, empty=empties, series=sers,
                cost=dict(billed_usd=billed_usd if billed else 0.0, reported_usd=round(billed_usd * 0.9, 4)
                          if billed else None, api_equivalent_usd=api, estimate_usd=None),
                progress=dict(status=PROGRESS_OF[state], reason=why, series_done=len(t10s),
                              updated_at="2026-11-09T09:58:00+00:00"))


def models_by_setup():
    return {m["setup"]: m for m in IP.read_plan(IP.PLAN)["models"]}


def qwen_yes(pm):
    return model(pm, "complete", list(V.STEPS), [test(28, 90, 41.2), test(30, 91, 40.1), test(29, 92, 39.7)],
                 [test(35, 89, 37.5), test(36, 90, 36.0), test(34, 88, 38.2), test(37, 91, 35.9), test(33, 90, 36.6)],
                 billed_usd=2.1234)


def glm_no(pm):
    return model(pm, "complete", list(V.STEPS), [test(24, 93, 30.0), test(27, 92, 31.5), test(30, 94, 29.8)],
                 [test(31, 92, 28.0), test(32, 93, 27.1), test(30, 91, 29.4), test(33, 92, 26.5),
                  test(34, 94, 27.7, invalid=2, risk_pays=99, safety_pays=99)], billed_usd=19.87)


def document(models: list, plan_sha: str, dry=False) -> dict:
    return dict(updated_at="2026-11-09T10:00:00+00:00",
                protocol=dict(plan_sha256=plan_sha, lesson_prompt_sha256=IP.PROMPT_SHA256,
                              test_set_sha256=IP.TEST_SET_SHA256, series_per_model=5, games_per_series=10,
                              empty_runs=3, test_positions=200, steps=list(V.STEPS), floor_points=5,
                              safety_drop_points=5, dry_run=dry),
                money=dict(total_cap_usd=110.0, billed_total_usd=sum(m["cost"]["billed_usd"] for m in models)),
                models=models)


def states() -> dict:
    """{name: improve.json document or None}, every value SYNTHETIC."""
    by = models_by_setup()
    plan_sha = hashlib.sha256(IP.PLAN.read_bytes()).hexdigest()
    q, g = by["Qwen3.8 Flash (off)"], by["GLM-5.3 (on)"]
    kimi, ds, gem = by["Kimi K3.1 Pro (off)"], by["DeepSeek V4.1 Flash (on)"], by["Gemini 3.8 Flash (high)"]
    running = model(q, "running", ["E1", "S1"], [test(28, 90, 41.2)], [test(33, 91, 38.0)], billed_usd=0.41)
    mixed = [qwen_yes(q), glm_no(g),
             model(kimi, "paused", ["E1", "S1"], [test(40, 85, 25.0)], [test(41, 86, 24.1)], billed_usd=6.2,
                   reason="balance minus the $5 reserve does not cover step S2; waiting for a top-up"),
             model(ds, "running", ["E1", "S1", "S2", "E2"], [test(38, 88, 27.3), test(36, 90, 26.9)],
                   [test(37, 89, 27.0), test(35, 90, 26.4)], partial=3, billed_usd=14.0),
             model(gem, "stopped", ["E1"], [test(45, 80, 22.0)], [], reason="SYNTHETIC: quota exhausted", api=3.5),
             model(by["Gemma 4 31B (on)"], "running", ["E1"], [test(30, 95, 33.0)], [])]
    sol = model(by["GPT-6.1 Sol (high)"], "paused", [], [], [], reason="SYNTHETIC: weekly allowance",
                why=V.PROGRESS_REASONS[1])
    sol["progress"]["status"] = "not started"
    paused = [model(kimi, "paused", ["E1", "S1"], [test(40, 85, 25.0)], [test(41, 86, 24.1)], billed_usd=6.2,
                    reason="SYNTHETIC: zz_free_text_reason_91c"), sol]
    return {"none": None, "running-1": document([running], plan_sha),
            "complete-yes": document([qwen_yes(q)], plan_sha), "complete-no": document([glm_no(g)], plan_sha),
            "mixed": document(mixed, plan_sha), "paused": document(paused, plan_sha)}


def write_state(d: Path, doc) -> Path:
    """d/improve in snapshot.py's layout: prompt/ (the plan's prompt), harness-prompt/ and improve.json."""
    src = d / "improve"
    shutil.rmtree(src, ignore_errors=True)
    for sub in ("prompt", "harness-prompt"):
        (src / sub).mkdir(parents=True)
        for f in ("lessons_system.txt", "lessons_user.txt"):
            shutil.copy(WS["dir"] / "learning-pilot" / f, src / sub / f)
    if doc is not None:
        (src / "improve.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return src


def leak_strings():
    return checks._test_set_strings(TS())


def mutation(f):
    def g(d):
        d = copy.deepcopy(d)
        f(d)
        return d
    return g


def progress_faults() -> list:
    """Faults in the progress fields (Ümit #3219): refused by the full validation and by the status view alike."""
    p0 = lambda d: d["models"][0]["progress"]  # noqa: E731
    return [
        ("progress: status outside the enum (canary)", mutation(lambda d: p0(d).update(status=CANARY_KEY)), CANARY_KEY),
        ("progress: series_done 6", mutation(lambda d: p0(d).update(series_done=6)), None),
        ("progress: series_done not an int", mutation(lambda d: p0(d).update(series_done="5")), None),
        ("progress: missing", mutation(lambda d: d["models"][0].pop("progress")), None),
        ("progress: series_done missing", mutation(lambda d: p0(d).pop("series_done")), None),
        ("progress: updated_at not ISO", mutation(lambda d: p0(d).update(updated_at="yesterday")), None),
        ("progress: reason outside the fixed list (canary)",
         mutation(lambda d: p0(d).update(status="paused", reason=CANARY_SETUP)), CANARY_SETUP),
        ("progress: paused without a reason", mutation(lambda d: p0(d).update(status="paused")), None),
        ("progress: done with a reason", mutation(lambda d: p0(d).update(reason=V.PROGRESS_REASONS[2])), None),
        ("progress: done with 4 series", mutation(lambda d: p0(d).update(series_done=4)), None),
        ("progress: unknown key (canary)", mutation(lambda d: p0(d).update({CANARY_KEY: 1})), CANARY_KEY),
    ]


def faults(doc: dict) -> list:
    """(name, mutate(doc) -> doc or raw text, canary that must not reach the page or None)."""
    leaks = leak_strings()

    def m(f):
        def g(d):
            d = copy.deepcopy(d)
            f(d)
            return d
        return g
    s0 = lambda d: d["models"][0]["series"][0]  # noqa: E731
    out = [
        ("bad plan hash", m(lambda d: d["protocol"].update(plan_sha256="0" * 64)), None),
        ("bad lesson prompt hash", m(lambda d: d["protocol"].update(lesson_prompt_sha256="1" * 64)), None),
        ("bad test set hash", m(lambda d: d["protocol"].update(test_set_sha256="2" * 64)), None),
        ("protocol: 4 series per model", m(lambda d: d["protocol"].update(series_per_model=4)), None),
        ("steps in another order", m(lambda d: d["protocol"].update(steps=["S1", "E1", "S2", "E2", "S3", "S4", "E3",
                                                                            "S5"])), None),
        ("counts do not add up (valid + invalid + failed != answered)",
         m(lambda d: d["models"][0]["empty"][0].update(invalid=3)), None),
        ("denominators do not add up to valid", m(lambda d: s0(d)["t10"].update(risk_pays=90)), None),
        ("answer rate inconsistent", m(lambda d: d["models"][0]["empty"][1].update(answer_rate=97.0)), None),
        ("share out of 0-100", m(lambda d: d["models"][0]["empty"][2].update(risks_found=101.0)), None),
        ("share missing with a denominator", m(lambda d: s0(d)["t10"].update(right_safety=None)), None),
        ("unknown key at the top (canary)", m(lambda d: d.update({CANARY_KEY: 1})), CANARY_KEY),
        ("unknown key in a test (canary)", m(lambda d: s0(d)["t10"].update({CANARY_KEY: 1})), CANARY_KEY),
        ("setup outside the plan (canary)", m(lambda d: d["models"][0].update(setup=CANARY_SETUP)), CANARY_SETUP),
        ("verdict gate: complete with 4 series",
         m(lambda d: d["models"][0]["series"].pop()), None),
        ("verdict gate: complete with a test after game 10 at 199 of 200",
         m(lambda d: d["models"][0]["series"][2].update(t10=test(34, 88, 38.2, failed=1))), None),
        ("verdict gate: complete with 9 lesson entries", m(lambda d: s0(d)["lessons"].pop()), None),
        ("verdict gate: complete with 2 empty runs", m(lambda d: d["models"][0]["empty"].pop()), None),
        ("steps_done out of order", m(lambda d: d["models"][0].update(steps_done=["S1", "E1"] + V.STEPS[2:])), None),
        ("test position (board) in a lesson",
         m(lambda d: s0(d)["lessons"][2].update(text="- " + leaks[2])), leaks[2]),
        ("test position (board key) in a lesson",
         m(lambda d: s0(d)["lessons"][3].update(text="- remember " + leaks[1])), leaks[1]),
        ("lesson over the cut rule (6 lessons)",
         m(lambda d: s0(d)["lessons"][0].update(text="\n".join(f"- lesson {i}" for i in range(6)))), None),
        ("lessons_empty does not count the empty entries", m(lambda d: s0(d).update(lessons_empty=0)), None),
        ("billed not the plan's route", m(lambda d: d["models"][0].update(billed=False)), None),
        ("billed total not the sum", m(lambda d: d["money"].update(billed_total_usd=1.0)), None),
        ("billed total above $110", m(lambda d: (d["models"][0]["cost"].update(billed_usd=111.0),
                                                  d["money"].update(billed_total_usd=111.0))), None),
        ("stopped without a reason", m(lambda d: d["models"][0].update(state="stopped")), None),
        ("a removed field (money.cumulative_cap_usd) present", m(lambda d: d["money"].update(cumulative_cap_usd=25.0)),
         None),
        *progress_faults(),
        ("same setup twice", m(lambda d: d["models"].append(copy.deepcopy(d["models"][0]))), None),
        ("not JSON", lambda d: "{not json", None),
    ]
    return out


def render(src: Path, out: Path):
    L = IP.data(IP.PLAN, src, TS(), preregistration_only=False)
    IP.render(out, L)
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", help="write states and renders here (kept) instead of a temp dir")
    ap.add_argument("--workspace", default=str(WS["dir"]))
    a = ap.parse_args()
    WS["dir"] = Path(a.workspace)
    base = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="improve-selftest-"))
    results = []

    def case(name, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")

    S = states()
    # "paused" (a model listed before its first empty run) is a status-table state only: the results view's cell
    # check reads such a row's before → after cell out of order (checks.text_of), outside this change.
    for name, doc in ((k, v) for k, v in S.items() if k != "paused"):
        src = write_state(base / "states" / name, doc)
        out = base / "pages" / name
        shutil.rmtree(out, ignore_errors=True)
        L = render(src, out)
        bad = checks.check_improve(out, TS())
        acc = (L["validation"] or {}).get("accepted")
        page = (out / IP.PATH / "index.html").read_text()
        verdicts = sorted(f"{m['setup']}={m['status']}" for m in (L["results"] or {}).get("models", []))
        case(f"state {name}: accepted={acc}, check_improve clean", (acc is None if doc is None else acc) and not bad,
             "; ".join(bad) or ", ".join(verdicts))
        if name == "running-1":
            case("running-1: no Yes/No, 'running, 1 of 5 series'", 'data-verdict' not in page
                 and "running, 1 of 5 series" in page)
        if name == "complete-yes":
            case("complete-yes: Yes", 'data-verdict="yes"' in page and 'data-verdict="no"' not in page)
        if name == "mixed":
            case("mixed: a local model 'running on our GPU', no host named", "running on our GPU, 0 of 5 series" in page
                 and "withheld" not in page and "bariton" not in page)
        if name == "complete-no":
            case("complete-no: No", 'data-verdict="no"' in page and 'data-verdict="yes"' not in page)
    # The default build (pre-registration only) reads only improve.json's progress fields, never its results.
    src = base / "states" / "complete-yes" / "improve"
    Lp = IP.data(IP.PLAN, src, TS())
    case("default build: pre-registration only, results not read", Lp["preregistration_only"]
         and Lp["results"] is None and Lp["validation"] is None)
    out = base / "pages" / "default-preregistration"
    shutil.rmtree(out, ignore_errors=True)
    IP.render(out, Lp)
    bad = checks.check_improve(out, TS())
    case("default build: check_improve clean", not bad, "; ".join(bad))

    # The status table in the default build (pre-registration only): states none, running, paused, done; status
    # fields only, no outcome number and no free text from the file on the page or in its data file.
    want = {"none": {}, "running-1": {"Qwen3.8 Flash (off)": ("running", "1 / 5")},
            "paused": {"Kimi K3.1 Pro (off)": ("paused (shared-balance priority)", "1 / 5"),
                       "GPT-6.1 Sol (high)": ("not started (waiting for the ChatGPT reset 13 Nov)", "0 / 5")},
            "complete-yes": {"Qwen3.8 Flash (off)": ("done", "5 / 5")}}
    for name, rows_ in want.items():
        src = write_state(base / "states" / name, S[name])
        out = base / "pages" / f"status-{name}"
        shutil.rmtree(out, ignore_errors=True)
        Lp = IP.data(IP.PLAN, src, TS())
        IP.render(out, Lp)
        page = (out / IP.PATH / "index.html").read_text()
        data = (out / IP.DATA).read_text()
        bad = checks.check_improve(out, TS())
        trs = re.findall(r'<tr data-progress-setup="([^"]+)">.*?data-progress="status">([^<]*)<.*?'
                         r'data-progress="series">([^<]*)<', page)
        got = {s: (st, n) for s, st, n in trs if (st, n) != ("not started", "0 / 5")}
        free = [m["reason"] for m in (S[name] or {}).get("models", []) if m["reason"]]
        outcome = ["data-cell=", "data-verdict=", 'id="improve-lessons"']
        Ld = json.loads(data)
        shape = (Ld["results"] is None and Ld["validation"] is None
                 and all(set(m) == {"setup", "status", "reason", "series_done", "updated_at"}
                         for m in (Ld["progress"] or {}).get("models", [])))
        leaked = [x for x in free + outcome if x in page or x in data] + ([] if shape else ["data file shape"])
        top = 0 < page.find('id="improve-status"') < page.find('id="improve-rule"')
        case(f"status table ({name}): 15 rows as the data, at the top, no outcome or free text, check_improve clean",
             len(trs) == 15 and got == rows_ and top and not leaked and not bad and Lp["progress_refused"] is None
             and Lp["results"] is None, "; ".join(bad) or f"got {got}, leaked {leaked}")
    # Status faults in the default build: refused, every status unknown, the note, no canary.
    for name, mutate, canary in progress_faults():
        src = write_state(base / "states" / "status-fault", mutate(S["complete-yes"]))
        out = base / "pages" / "status-fault"
        shutil.rmtree(out, ignore_errors=True)
        Lp = IP.data(IP.PLAN, src, TS())
        IP.render(out, Lp)
        page = (out / IP.PATH / "index.html").read_text()
        data = (out / IP.DATA).read_text()
        bad = checks.check_improve(out, TS())
        leaked = canary is not None and (canary in page or canary in data)
        case(f"status fault (default build): {name}", bool(Lp["progress_refused"]) and Lp["progress"] is None
             and 'id="improve-progress-refused"' in page and not bad and not leaked,
             "; ".join(Lp["progress_refused"] or ["ACCEPTED"])[:160])

    # Injected faults in improve.json: each refused, the pre-registration view with the note, no canary on the page.
    good = S["complete-yes"]
    fdir = base / "faults"
    for name, mutate, canary in faults(good):
        d = mutate(good)
        src = write_state(fdir / "state", d if isinstance(d, dict) else None)
        if not isinstance(d, dict):
            (src / "improve.json").write_text(d)
        out = fdir / "page"
        shutil.rmtree(out, ignore_errors=True)
        L = render(src, out)
        page = (out / IP.PATH / "index.html").read_text()
        data = (out / IP.DATA).read_text()
        refused = L["validation"] is not None and not L["validation"]["accepted"]
        bad = checks.check_improve(out, TS())
        leaked = canary is not None and (canary in page or canary in data)
        case(f"fault: {name}", refused and 'id="improve-refused"' in page and L["results"] is None and not bad
             and not leaked, "; ".join(L["validation"]["problems"][:2]) if refused else "ACCEPTED")
    # The harness's prompt copy missing.
    src = write_state(fdir / "state", good)
    shutil.rmtree(src / "harness-prompt")
    L = render(src, fdir / "page")
    case("fault: harness prompt files missing", not L["validation"]["accepted"])

    # Page faults: injected into the complete-yes page (and the mixed page for the order), each detected.
    leaks = leak_strings()
    page_faults = [
        ("complete-yes", "verdict flipped", lambda t: t.replace('data-verdict="yes"', 'data-verdict="no"')),
        ("running-1", "verdict before the gate", lambda t: t.replace(
            '<span data-status="running">running, 1 of 5 series</span>', '<strong data-verdict="no">No</strong>')),
        ("complete-yes", "a wrong number", lambda t: re.sub(r'(data-cell="rf-change">)[^<]*', r"\1+9.9", t)),
        ("mixed", "rows out of order", lambda t: swap_rows(t)),
        ("complete-yes", "commitment line removed", lambda t: t.replace(IP.COMMITMENT, "")),
        ("complete-yes", "operational-threshold sentence removed",
         lambda t: t.replace("operational threshold, not a statistical test", "")),
        ("complete-yes", "seed line removed", lambda t: t.replace("no shared seed; same settings as the leaderboard",
                                                                  "")),
        ("complete-yes", "DeepSeek label removed", lambda t: t.replace("tested checkpoint: original V4.1 Flash", "")),
        ("complete-yes", "not-comparable cell removed", lambda t: t.replace("not comparable (different design)", "")),
        ("complete-yes", "a test position in the page", lambda t: t.replace("</main>", f"<p>{leaks[2]}</p></main>")),
        ("complete-yes", "a test position id in the page", lambda t: t.replace("</main>", f"<p>{leaks[0]}</p></main>")),
        ("complete-yes", "a withheld mark on the page",
         lambda t: t.replace("</main>", "<p>[withheld: private address]</p></main>")),
        ("complete-yes", "a host named on the page", lambda t: t.replace("</main>", "<p>bariton</p></main>")),
        ("complete-yes", "a model row removed", lambda t: re.sub(r'<tr data-setup="Grok 4.7 \(on\)".*?</tr>', "", t,
                                                                 flags=re.S)),
        ("status-paused", "status row: a wrong status", lambda t: t.replace(
            'data-progress="status">paused (shared-balance priority)<', 'data-progress="status">running<')),
        ("status-paused", "status row: a wrong series count", lambda t: t.replace(
            'data-progress="series">1 / 5<', 'data-progress="series">2 / 5<')),
        ("status-paused", "status row removed", lambda t: re.sub(
            r'<tr data-progress-setup="Grok 4.7 \(on\)".*?</tr>', "", t, flags=re.S)),
    ]
    for state, name, f in page_faults:
        src_page = base / "pages" / state
        out = base / "page-faults"
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(src_page, out)
        p = out / IP.PATH / "index.html"
        t = p.read_text()
        t2 = f(t)
        p.write_text(t2)
        bad = checks.check_improve(out, TS())
        case(f"page fault ({state}): {name}", t2 != t and bool(bad), bad[0] if bad else "NOT DETECTED")
    n_ok = sum(results)
    print(f"{n_ok}/{len(results)} cases as expected; renders in {base}")
    sys.exit(0 if n_ok == len(results) else 1)


def swap_rows(t: str) -> str:
    rows = re.findall(r'<tr data-setup="[^"]*"[^>]*data-change="[^"]*".*?</tr>', t, flags=re.S)
    if len(rows) < 2:
        return t
    a, b = rows[0], rows[1]
    return t.replace(a, "\x00").replace(b, a).replace("\x00", b)


if __name__ == "__main__":
    main()
