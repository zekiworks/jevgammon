"""The "Did they improve?" results file (workspace/improve/out/improve.json, as snapshot.py copies it to
STATE/improve), checked by the site before anything of it is shown. Nothing the harness wrote is trusted or passed
through (learning_validate's conventions, reused: closed recursive schemas, public problem texts that never name a key
or value taken from the file, the full text on stderr only):

- the whole file against a closed, recursive schema (every key, type and range; no unknown key);
- the protocol block against the pre-registration (plan 2026-11-08): the plan file's own sha256, the lesson prompt's
  and the test set's hashes (stated in the plan and equal to the files present at build time), 5 series of 10 games,
  3 empty runs, 200 test positions, the step order E1 S1 S2 E2 S3 S4 E3 S5, the 5-point floor and the 5-point safety
  drop;
- every model: its setup one of the plan's 15 chat models (once), billed exactly when its plan route is OpenRouter,
  steps done a prefix of the step order and agreeing with its empty runs and finished series, a reason exactly when
  paused, incomplete or stopped; every test's counts adding up (valid + invalid + failed = answered <= 200, risk-pays +
  safety-pays = valid, each share defined exactly when its denominator is not zero and within 0-100, the answer rate
  100 x valid / 200); every series' games, lessons and counts consistent, its kept lessons within the pilot's cut rule
  (at most 5 lines starting "- ", 150 words) and holding no test position;
- the verdict gate (plan section 7): a model marked complete must have all 3 empty runs and all 5 tests after game 10
  answered 200 of 200 with no failed request, and all 5 series of 10 games with 10 lesson entries each;
- every model's progress (the "Models and status" table, Ümit #3219): status one of not started, running, paused,
  stopped, done; reason one of the fixed texts (PROGRESS_REASONS), required when paused, absent when running or
  done, "usage limit" and "waiting for a GPU" only when paused; series_done 0-5, the finished series in steps_done
  (5 when done; 5 only when done or stopped; 0 when not started); updated_at a real UTC calendar time
  (calendar_time); the status agreeing with the model's state. status_view() checks these fields alone for
  pre-registration-only builds;
- the money block: the billed total is the sum of the models' billed amounts, within the total cap $110 (no interim
  cap, plan section 9); a model that is not billed has $0 billed.

The producer writes no before, after or verdict: they are computed here (plan sections 2 and 6) and published as the
projection validate() returns ("public"), for the page and its data file.
"""

import re
from datetime import datetime, timedelta

from learning_validate import (BOOL, DICT, HEX64, INT, ISO, LIST, NUM, OPT, check, private_problems,  # noqa: F401
                               public_problems, untrusted)

SERIES, GAMES, EMPTY_RUNS, POSITIONS = 5, 10, 3, 200
STEPS = ["E1", "S1", "S2", "E2", "S3", "S4", "E3", "S5"]
FLOOR, SAFETY_DROP = 5, 5  # plan section 2, percentage points
TOTAL_CAP = 110.0  # plan section 9: spending approved up to $110 billed total (no interim cap, Can #3129)
MAX_LESSONS, MAX_WORDS = 5, 150  # the pilot's cut rule (plan section 5)
STATES = ("running", "paused", "complete", "incomplete", "stopped")
# States whose current step may be in progress (paused: a balance shortfall at a step boundary, plan section 9).
LIVE = ("running", "paused")
TOL = 1e-6
# The producer rounds each model's billed amount and the billed total to 4 decimals separately (the live file of
# 9 Nov: 0.9407 + 13.5513 = 14.4920 against a total of 14.4921), so the sum may differ by up to half a unit of the
# 4th decimal per rounded amount.
MONEY_ROUND = 0.00005

PCT = OPT(NUM(0, 100))
TEST = DICT(dict(answered=INT(0, POSITIONS), expected=INT(POSITIONS, POSITIONS), valid=INT(0, POSITIONS),
                 invalid=INT(0, POSITIONS), failed=INT(0, POSITIONS), risk_pays=INT(0, POSITIONS),
                 safety_pays=INT(0, POSITIONS), risks_found=PCT, right_safety=PCT, error_rate=OPT(NUM(0, 1000)),
                 answer_rate=NUM(0, 100), in_flight_max=INT(1, 4), wall_seconds=NUM()))
LESSON = DICT(dict(game=INT(1, GAMES), text=("str", r"(?s).{0,4000}")))
SERIES_SPEC = DICT(dict(series=INT(1, SERIES), finished=BOOL, games=INT(0, GAMES), wins=INT(0, GAMES),
                        game_decisions=INT(), game_invalid=INT(), lesson_calls=INT(), lessons_cut=INT(0, GAMES),
                        lessons_empty=INT(0, GAMES), restarts=INT(0, 100), lessons=LIST(LESSON, GAMES),
                        t10=OPT(TEST)))
COST = DICT(dict(billed_usd=NUM(0), reported_usd=OPT(NUM(0)), api_equivalent_usd=OPT(NUM(0)),
                 estimate_usd=OPT(NUM(0))))
TEXT = ("str", r"[^<>&\x00-\x1f]{1,400}")
# The page's "Models and status" table (Ümit #3219): each model's progress, closed values only (no free text, no
# outcome number), published even while the page is pre-registration only.
PROGRESS_STATUSES = ("not started", "running", "paused", "stopped", "done")
PROGRESS_REASONS = ("shared-balance priority", "waiting for the ChatGPT reset 13 Nov", "waiting for its turn",
                    "usage limit", "waiting for a GPU")
# Allowed with status paused only: a subscription usage-limit (429) pause; a local model held for a GPU.
PAUSE_ONLY_REASONS = ("usage limit", "waiting for a GPU")
PROGRESS = DICT(dict(status=("enum", PROGRESS_STATUSES), reason=OPT(("enum", PROGRESS_REASONS)),
                     series_done=INT(0, SERIES), updated_at=ISO))
# The harness's state each progress status may stand with (full validation only).
PROGRESS_STATE = {"not started": ("running", "paused"), "running": ("running",), "paused": ("paused",),
                  "stopped": ("stopped", "incomplete"), "done": ("complete",)}
MODEL = DICT(dict(key=("str", r"[a-z0-9.-]{1,60}"), setup=("str", r"[^<>&\x00-\x1f]{1,120}"), route=TEXT,
                  billed=BOOL, state=("enum", STATES), reason=OPT(TEXT), steps_done=LIST(("enum", tuple(STEPS)), 8),
                  empty=LIST(TEST, EMPTY_RUNS), series=LIST(SERIES_SPEC, SERIES), cost=COST, progress=PROGRESS))
PROTOCOL = DICT(dict(plan_sha256=HEX64, lesson_prompt_sha256=HEX64, test_set_sha256=HEX64,
                     series_per_model=INT(), games_per_series=INT(), empty_runs=INT(), test_positions=INT(),
                     steps=LIST(("str", r"[A-Z]\d"), 16), floor_points=NUM(), safety_drop_points=NUM(),
                     dry_run=BOOL))
MONEY = DICT(dict(total_cap_usd=NUM(0), billed_total_usd=NUM(0)))
TOP = DICT(dict(updated_at=ISO, protocol=PROTOCOL, money=MONEY, models=LIST(MODEL, 15)))
# The status view (pre-registration-only builds): the progress fields only; every other key of the file is allowed by
# name and never read.
STATUS_TOP = DICT(dict(updated_at=ISO, models=LIST(DICT(dict(setup=MODEL[1]["setup"], progress=PROGRESS),
                                                         {k: ("any",) for k in MODEL[1] if k not in ("setup", "progress")}),
                                                    15)),
                  {k: ("any",) for k in TOP[1] if k not in ("updated_at", "models")})
SHARES = ("risks_found", "right_safety", "error_rate")


def rejected(problems: list) -> dict:
    return dict(accepted=False, problems=public_problems(problems), private_problems=private_problems(problems),
                public=None)


def mean(xs):
    return sum(xs) / len(xs) if xs and all(x is not None for x in xs) else None


def test_problems(t: dict, where: str) -> list:
    """A test's own counts: they add up, shares defined exactly where their denominators are not zero."""
    bad = []
    if t["valid"] + t["invalid"] + t["failed"] != t["answered"]:
        bad.append(f"{where}: valid + invalid + failed is not answered")
    if t["answered"] > t["expected"]:
        bad.append(f"{where}: answered more than expected")
    if t["risk_pays"] + t["safety_pays"] != t["valid"]:
        bad.append(f"{where}: risk-pays + safety-pays denominators are not the valid answers")
    for share, den in (("risks_found", "risk_pays"), ("right_safety", "safety_pays"), ("error_rate", "valid")):
        if (t[share] is None) != (t[den] == 0):
            bad.append(f"{where}: {share} must be given exactly when {den} is not zero")
    if t["risk_pays"] > POSITIONS // 2 or t["safety_pays"] > POSITIONS // 2:
        bad.append(f"{where}: a denominator exceeds its 100 positions")
    if abs(t["answer_rate"] - 100 * t["valid"] / t["expected"]) > 0.005 + TOL:
        bad.append(f"{where}: answer_rate is not 100 x valid / expected")
    return bad


def full(t) -> bool:
    """Plan section 7: 200 of 200 answered (valid or invalid), no failed request left, every share defined."""
    return (t is not None and t["answered"] == t["expected"] == POSITIONS and t["failed"] == 0
            and all(t[s] is not None for s in SHARES))


def lesson_problems(text: str, where: str, leaks: list) -> list:
    bad = []
    lines = text.split("\n") if text else []
    if any(not re.fullmatch(r"- \S.*", x) for x in lines):
        bad.append(f"{where}: a kept lesson line does not start with '- '")
    if len(lines) > MAX_LESSONS:
        bad.append(f"{where}: more than {MAX_LESSONS} lessons kept")
    if sum(len(x[2:].split()) for x in lines) > MAX_WORDS:
        bad.append(f"{where}: more than {MAX_WORDS} words kept")
    if any(s in text for s in leaks):
        bad.append(f"{where}: holds a test position")
    return bad


def calendar_time(s: str) -> bool:
    """s (already of the ISO shape) is a real UTC time: datetime.fromisoformat accepts it (every field in its calendar
    range: no 30 February, no hour 29), it has a zero UTC offset, and its year is 2026-2099."""
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        return False
    return t.tzinfo is not None and t.utcoffset() == timedelta(0) and 2026 <= t.year <= 2099


def progress_problems(p: dict, where: str) -> list:
    """A model's progress fields among themselves: a reason exactly when paused (never when running or done), done
    with all 5 series and all 5 series only when done or stopped (S5 is the last step: running, paused or not started
    leave a series to play), not started with none; updated_at a real UTC calendar time (calendar_time)."""
    bad = []
    if p["status"] == "paused" and p["reason"] is None:
        bad.append(f"{where}.reason: required when paused")
    if p["reason"] in PAUSE_ONLY_REASONS and p["status"] != "paused":
        bad.append(f"{where}.reason: allowed only when paused")
    if p["status"] in ("running", "done") and p["reason"] is not None:
        bad.append(f"{where}.reason: not allowed when running or done")
    if p["status"] == "done" and p["series_done"] != SERIES:
        bad.append(f"{where}.series_done: done without all {SERIES} series")
    if p["series_done"] == SERIES and p["status"] not in ("done", "stopped"):
        bad.append(f"{where}.series_done: all {SERIES} series, but neither done nor stopped")
    if p["status"] == "not started" and p["series_done"] != 0:
        bad.append(f"{where}.series_done: series done before the start")
    if not calendar_time(p["updated_at"]):
        bad.append(f"{where}.updated_at: not a real UTC calendar time")
    return bad


def setups_problems(models: list, plan_models: dict, fields=("key", "setup")) -> list:
    bad = [f"models[{i}].setup: {untrusted(m['setup'])} is not one of the plan's chat models"
           for i, m in enumerate(models) if m["setup"] not in plan_models]
    for field in fields:
        vals = [m[field] for m in models]
        if len(set(vals)) != len(vals):
            bad.append(f"models: a {field} appears twice")
    return bad


def progress_rows(R: dict) -> dict:
    return dict(updated_at=R["updated_at"], models=[dict(setup=m["setup"], **m["progress"]) for m in R["models"]])


def status_view(R, plan_models: dict) -> dict:
    """Pre-registration-only builds: improve.json's progress fields only (STATUS_TOP, progress_problems, setups from
    the plan, once each). public: {updated_at, models: [{setup, status, reason, series_done, updated_at}]}."""
    if not isinstance(R, dict):
        return rejected(["improve.json is not an object"])
    bad = check(R, STATUS_TOP, "improve.json")
    if bad:
        return rejected(bad)
    bad = setups_problems(R["models"], plan_models, ("setup",))
    for i, m in enumerate(R["models"]):
        bad += progress_problems(m["progress"], f"models[{i}].progress")
    if bad:
        return rejected(bad)
    return dict(accepted=True, problems=[], private_problems=[], public=progress_rows(R))



def model_problems(m: dict, i: int, plan_models: dict, dry: bool, leaks: list) -> list:
    where = f"models[{i}]"
    bad = []
    pm = plan_models.get(m["setup"])
    if pm is None:
        bad.append(f"{where}.setup: {untrusted(m['setup'])} is not one of the plan's chat models")
    elif m["billed"] != pm["billed"]:
        bad.append(f"{where}.billed: not the plan's route (billed exactly on OpenRouter)")
    done = m["steps_done"]
    if done != STEPS[:len(done)]:
        bad.append(f"{where}.steps_done: not the plan's step order")
    n_e, n_s = sum(s[0] == "E" for s in done), sum(s[0] == "S" for s in done)
    nxt = STEPS[len(done)] if len(done) < len(STEPS) else None
    running = m["state"] in LIVE
    # A step in progress (running only) may already have its entry: the next empty run or the next series, unfinished.
    if not (len(m["empty"]) == n_e or (running and nxt and nxt[0] == "E" and len(m["empty"]) == n_e + 1)):
        bad.append(f"{where}.empty: does not match the empty runs in steps_done")
    ser = m["series"]
    if [s["series"] for s in ser] != list(range(1, len(ser) + 1)):
        bad.append(f"{where}.series: not numbered 1..n in order")
    fin = [s for s in ser if s["finished"]]
    if len(fin) != n_s or any(not s["finished"] for s in ser[:n_s]):
        bad.append(f"{where}.series: finished series do not match the series in steps_done")
    if len(ser) not in (n_s, n_s + 1) or (len(ser) == n_s + 1 and not (running and nxt and nxt[0] == "S")):
        bad.append(f"{where}.series: a series in progress outside a running series step")
    for j, s in enumerate(ser):
        w = f"{where}.series[{j}]"
        games = [x["game"] for x in s["lessons"]]
        if games != list(range(1, len(games) + 1)):
            bad.append(f"{w}.lessons: games not numbered 1..n in order")
        if s["finished"]:
            if s["games"] != GAMES or len(s["lessons"]) != GAMES:
                bad.append(f"{w}: finished without {GAMES} games and {GAMES} lesson entries")
            if s["t10"] is None:
                bad.append(f"{w}: finished without its test after game 10")
        else:
            if len(s["lessons"]) > s["games"]:
                bad.append(f"{w}: more lesson entries than games")
            if s["t10"] is not None:
                bad.append(f"{w}: a test after game 10 in an unfinished series")
        if s["wins"] > s["games"]:
            bad.append(f"{w}: more wins than games")
        if s["game_invalid"] > s["game_decisions"]:
            bad.append(f"{w}: more invalid game decisions than decisions")
        if s["lesson_calls"] < len(s["lessons"]):
            bad.append(f"{w}: fewer lesson calls than lesson entries")
        if s["lessons_empty"] != sum(1 for x in s["lessons"] if not x["text"]):
            bad.append(f"{w}: lessons_empty is not the count of empty lesson entries")
        if s["lessons_cut"] > len(s["lessons"]):
            bad.append(f"{w}: more cut lessons than lesson entries")
        for k, x in enumerate(s["lessons"]):
            bad += lesson_problems(x["text"], f"{w}.lessons[{k}]", leaks)
        if s["t10"] is not None:
            bad += test_problems(s["t10"], f"{w}.t10")
    for j, t in enumerate(m["empty"]):
        bad += test_problems(t, f"{where}.empty[{j}]")
    if (m["reason"] is None) != (m["state"] in ("running", "complete")):
        bad.append(f"{where}.reason: required exactly when paused, incomplete or stopped")
    if m["state"] == "complete":
        if done != STEPS:
            bad.append(f"{where}: complete before every step is done")
        elif not gate(m):
            bad.append(f"{where}: complete, but the verdict gate fails (plan section 7)")
    elif done == STEPS and running:
        bad.append(f"{where}: every step done but still running")
    if not m["billed"] and (m["cost"]["billed_usd"] != 0 or m["cost"]["reported_usd"]):
        bad.append(f"{where}.cost: billed money on a route that is not billed")
    p = m["progress"]
    bad += progress_problems(p, f"{where}.progress")
    if p["series_done"] != n_s:
        bad.append(f"{where}.progress.series_done: not the finished series in steps_done")
    if m["state"] not in PROGRESS_STATE[p["status"]] or (p["status"] == "not started" and done):
        bad.append(f"{where}.progress.status: does not match the model's state and steps")
    return bad


def gate(m: dict) -> bool:
    """Plan section 7: all 3 empty runs and all 5 tests after game 10 at 200 of 200 with no failed request; all 5 series
    finished with 10 games and 10 lesson entries."""
    ser = m["series"]
    return (len(m["empty"]) == EMPTY_RUNS and all(full(t) for t in m["empty"]) and len(ser) == SERIES
            and all(s["finished"] and s["games"] == GAMES and len(s["lessons"]) == GAMES and full(s["t10"])
                    for s in ser))


def summed(tests: list) -> dict | None:
    """The answers behind one side (before: the empty runs; after: the tests after game 10), summed over its tests."""
    if not tests:
        return None
    k = ("expected", "answered", "valid", "invalid", "failed", "risk_pays", "safety_pays")
    out = {x: sum(t[x] for t in tests) for x in k}
    out["tests"] = len(tests)
    out["answer_rate"] = 100 * out["valid"] / out["expected"]
    return out


def scores(m: dict, dry: bool, local: bool = False) -> dict:
    """Plan sections 2 and 6: before = mean of the empty runs, after = mean of the tests after game 10, change = after
    - before; range = max - min of the empty runs' risks found; threshold = max(range, 5); Improved = change in risks
    found > threshold and change in right safety >= -5. Live numbers while running; the verdict only past the gate."""
    t10 = [s["t10"] for s in m["series"] if s["t10"] is not None]
    before = {s: mean([t[s] for t in m["empty"]]) for s in SHARES}
    after = {s: mean([t[s] for t in t10]) for s in SHARES}
    change = {s: (after[s] - before[s]) if before[s] is not None and after[s] is not None else None for s in SHARES}
    rf = [t["risks_found"] for t in m["empty"]]
    rng = max(rf) - min(rf) if len(rf) == EMPTY_RUNS and None not in rf else None
    threshold = max(rng, FLOOR) if rng is not None else None
    passed = gate(m) and m["state"] == "complete" and not dry
    improved = None
    if passed:
        improved = (round(change["risks_found"], 9) > round(threshold, 9)
                    and round(change["right_safety"], 9) >= -SAFETY_DROP)
    finished = sum(1 for s in m["series"] if s["finished"])
    if passed:
        status = "Yes" if improved else "No"
    elif m["state"] == "complete":
        status = "complete (dry run): no verdict"
    elif m["state"] == "running":  # a local model runs on our GPU (the page names no host)
        status = f"running{' on our GPU' if local else ''}, {finished} of {SERIES} series"
    else:  # the producer may already prefix the reason with the state ("paused: shared-balance priority, ...")
        prefix = f"{m['state']}: "
        status = m["reason"] if m["reason"].startswith(prefix) else prefix + m["reason"]
    return dict(before=before, after=after, change=change, range=rng, threshold=threshold, verdict=passed,
                improved=improved, status=status, series_finished=finished, empty_done=len(m["empty"]),
                answers_before=summed(m["empty"]), answers_after=summed(t10))


def validate(R, plan_sha: str, prompt_sha: str, test_sha: str, harness_prompt_sha: str | None,
             plan_models: dict, leaks: list) -> dict:
    """R: improve.json, parsed. plan_sha: the plan file's sha256; prompt_sha and test_sha: the hashes the plan states
    (equal to the files present at build time, checked by the caller); harness_prompt_sha: the sha256 of the harness's
    own copy of the lesson prompt (out/prompt), None when it is missing; plan_models: {setup: {"billed": bool, "route":
    str}} from the plan's section 3 table; leaks: the strings that would reveal a test position (checks._test_set_strings)."""
    if not isinstance(R, dict):
        return rejected(["improve.json is not an object"])
    bad = check(R, TOP, "improve.json")
    if bad:
        return rejected(bad)
    P = R["protocol"]
    want = dict(plan_sha256=plan_sha, lesson_prompt_sha256=prompt_sha, test_set_sha256=test_sha,
                series_per_model=SERIES, games_per_series=GAMES, empty_runs=EMPTY_RUNS, test_positions=POSITIONS,
                steps=STEPS, floor_points=FLOOR, safety_drop_points=SAFETY_DROP)
    bad += [f"protocol.{k}: not the pre-registered value" for k, v in want.items() if P[k] != v]
    if harness_prompt_sha != prompt_sha:
        bad.append("prompt/: the harness's lesson prompt files are missing or not the pre-registered prompt")
    M = R["money"]
    if M["total_cap_usd"] != TOTAL_CAP:
        bad.append("money.total_cap_usd: not $110")
    total = sum(m["cost"]["billed_usd"] for m in R["models"])
    if abs(total - M["billed_total_usd"]) > MONEY_ROUND * (len(R["models"]) + 1) + TOL:
        bad.append("money.billed_total_usd: not the sum of the models' billed amounts")
    if M["billed_total_usd"] > TOTAL_CAP + TOL:
        bad.append("money.billed_total_usd: above the $110 cap")
    for field in ("key", "setup"):
        vals = [m[field] for m in R["models"]]
        if len(set(vals)) != len(vals):
            bad.append(f"models: a {field} appears twice")
    for i, m in enumerate(R["models"]):
        bad += model_problems(m, i, plan_models, P["dry_run"], leaks)
    if bad:
        return rejected(bad)
    models = []
    for m in R["models"]:
        out = {k: m[k] for k in ("key", "setup", "state", "reason", "steps_done", "cost", "progress")}
        out["empty"] = m["empty"]
        out["series"] = [{k: v for k, v in s.items()} for s in m["series"]]
        out.update(scores(m, P["dry_run"], plan_models[m["setup"]]["route"].startswith("local")))
        models.append(out)
    return dict(accepted=True, problems=[], private_problems=[],
                public=dict(updated_at=R["updated_at"], dry_run=P["dry_run"], money=M, models=models))
