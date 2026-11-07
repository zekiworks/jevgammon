"""The learning pilot's results, checked by the site before anything of them is shown (Zeki #2575): the harness's
learning-pilot.json and series aggregates are not trusted. They are checked against the site's own fixed copy of the
protocol (plan sections 4-7 and 9), the lesson prompt hash the plan states, and the hash of the private evaluation set
present at build time.

validate() returns two lists of problems:
- schema problems: the file is not the closed, typed shape below, or it describes another protocol, prompt or
  evaluation set. The page then shows none of its numbers.
- completeness problems: the reasons the site does not accept "complete" (it accepts it only when the file says so AND
  every check here holds). The page then shows the numbers as running: no lift, signal or ranking.
Problem texts name fields, never values of private files.
"""

import hashlib
import json
from pathlib import Path

# The site's copy of the protocol (plan: 4 arms, 10 series of 10 games, T0 shared, T5 and T10 for the other arms, 200
# evaluation positions; the learning lift compares games 1-3 with games 8-10).
PROTOCOL = dict(arms=["control", "records", "lessons", "budget"], planned_series_per_arm=10, games_per_series=10,
                checkpoints={"shared": ["T0"], "non_control": ["T5", "T10"]}, evaluation_positions=200)
LIFT_GAMES = ((1, 3), (8, 10))
SIGNAL = dict(risks_found_at_least=10, right_safety_at_least=-5)  # plan section 8, in percentage points
SCALE = 500  # the site's equity scale (thresholds.json equity_scale): error rate = 500 x mean loss
TOL = 1e-6

STR, INT, BOOL, DICT, LIST = "str", "int", "bool", "dict", "list"
# learning-pilot.json, closed: every key the site accepts, with its type; REQUIRED must be present.
TOP = dict(updated_at=STR, protocol=DICT, planned_series_per_arm=INT, series_done=DICT, series_finished=DICT,
           complete=BOOL, lesson_prompt_sha256=STR, t0_done=BOOL, inventory=DICT, display_rule=STR, table=DICT,
           games=DICT, series=LIST, budget_empty_points=DICT, signal=DICT, learning_lift=DICT, paired_series=LIST)
REQUIRED = ("updated_at", "protocol", "planned_series_per_arm", "series_done", "series_finished", "complete", "table",
            "inventory")
PROTOCOL_KEYS = dict(arms=LIST, planned_series_per_arm=INT, games_per_series=INT, checkpoints=DICT,
                     evaluation_positions=INT, lesson_prompt_sha256=STR, test_set_sha256=STR, dry_run=BOOL)
INVENTORY_KEYS = dict(games=LIST, lessons_files=DICT, test_set_sha256=STR, lesson_prompt_sha256=STR)
BUDGET_POINT = dict(after_game=INT, games_shown=LIST, games_dropped=INT, tokens=INT, budget_tokens=INT)


def is_type(v, t: str) -> bool:
    """JSON types exactly: a bool is not an int, an int is not a bool, true is not "true"."""
    return {STR: lambda: isinstance(v, str), INT: lambda: type(v) is int, BOOL: lambda: type(v) is bool,
            DICT: lambda: isinstance(v, dict), LIST: lambda: isinstance(v, list)}[t]()


def is_num(v) -> bool:
    return type(v) in (int, float)


def closed(obj: dict, keys: dict, where: str, required=()) -> list:
    bad = [f"{where}: unknown key {k!r}" for k in obj if k not in keys]
    bad += [f"{where}: {k} missing" for k in required if k not in obj]
    bad += [f"{where}: {k} is not a JSON {keys[k]}" for k in obj if k in keys and not is_type(obj[k], keys[k])]
    return bad


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(src: Path, arm: str, s: int) -> dict | None:
    p = src / "runs" / arm / f"s{s:02d}" / "aggregate.json"
    return json.loads(p.read_text()) if p.exists() else None


def pooled(games: list, lo: int, hi: int):
    """Error rate over games lo..hi, decisions pooled: the per-game rates weighted by their valid decisions."""
    sel = [g for g in games if lo <= g["game"] <= hi and g.get("error_rate") is not None]
    n = sum(g["valid"] for g in sel)
    return sum(g["error_rate"] * g["valid"] for g in sel) / n if n else None


def close(a, b) -> bool:
    return a is not None and b is not None and abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def schema(R: dict, prompt_sha: str | None, plan_hashes: list, test_sha: str | None) -> list:
    bad = closed(R, TOP, "learning-pilot.json", REQUIRED)
    if bad:
        return bad
    P = R["protocol"]
    bad += closed(P, PROTOCOL_KEYS, "protocol", tuple(PROTOCOL_KEYS))
    if bad:
        return bad
    for k, want in PROTOCOL.items():
        if P[k] != want:
            bad.append(f"protocol.{k} differs from the site's copy of the protocol")
    arms = PROTOCOL["arms"]
    if R["planned_series_per_arm"] != PROTOCOL["planned_series_per_arm"]:
        bad.append("planned_series_per_arm differs from the protocol")
    if P["lesson_prompt_sha256"] not in plan_hashes:
        bad.append("protocol.lesson_prompt_sha256 is not the hash the plan states")
    if prompt_sha is not None and P["lesson_prompt_sha256"] != prompt_sha:
        bad.append("protocol.lesson_prompt_sha256 is not the hash of the lesson prompt files")
    if "lesson_prompt_sha256" in R and R["lesson_prompt_sha256"] != P["lesson_prompt_sha256"]:
        bad.append("lesson_prompt_sha256 differs from protocol.lesson_prompt_sha256")
    if test_sha is not None and P["test_set_sha256"] != test_sha:
        bad.append("protocol.test_set_sha256 is not the hash of the evaluation set present at build time")
    for key in ("series_done", "series_finished", "table", "inventory"):
        if sorted(R[key]) != sorted(arms):
            bad.append(f"{key}: arms differ from the protocol's")
    if bad:
        return bad
    for arm in arms:
        if not is_type(R["series_done"][arm], INT):
            bad.append(f"series_done.{arm} is not a JSON int")
        fin = R["series_finished"][arm]
        if not is_type(fin, LIST) or not all(is_type(s, INT) and 1 <= s <= PROTOCOL["planned_series_per_arm"]
                                             for s in fin) or len(set(fin)) != len(fin):
            bad.append(f"series_finished.{arm} is not a list of distinct series numbers 1-10")
        cps = ["T0"] + ([] if arm == "control" else PROTOCOL["checkpoints"]["non_control"])
        by_cp = R["table"][arm]
        if not is_type(by_cp, DICT) or sorted(by_cp) != sorted(cps):
            bad.append(f"table.{arm}: test rounds differ from the protocol's")
            continue
        for cp, row in by_cp.items():
            if row is not None and (not is_type(row, DICT) or any(v is not None and not is_num(v) and not is_type(v, BOOL)
                                                                   and not is_type(v, DICT) for v in row.values())):
                bad.append(f"table.{arm}.{cp}: not a row of numbers")
        for s, entry in R["inventory"][arm].items():
            where = f"inventory.{arm}.{s}"
            if not s.isdigit() or not is_type(entry, DICT):
                bad.append(f"{where}: not a series entry")
                continue
            e = closed(entry, INVENTORY_KEYS, where, tuple(INVENTORY_KEYS))
            bad += e
            if e:
                continue
            if entry["lesson_prompt_sha256"] != P["lesson_prompt_sha256"]:
                bad.append(f"{where}: lesson prompt hash differs")
            if test_sha is not None and entry["test_set_sha256"] != test_sha:
                bad.append(f"{where}: evaluation set hash differs from the set present at build time")
    for k in ("games", "budget_empty_points"):
        if k in R and not set(R[k]) <= set(arms):
            bad.append(f"{k}: unknown arm")
    if "budget_empty_points" in R and not all(is_type(v, INT) for v in R["budget_empty_points"].values()):
        bad.append("budget_empty_points: not JSON ints")
    return bad


def budget_points(A: dict, where: str) -> list:
    pts = A.get("budget_points")
    if pts is None:
        return []
    if not is_type(pts, LIST):
        return [f"{where}: budget_points is not a list"]
    bad = []
    for i, p in enumerate(pts):
        if not is_type(p, DICT):
            bad.append(f"{where}: budget_points[{i}] is not an object")
            continue
        bad += closed(p, BUDGET_POINT, f"{where}: budget_points[{i}]", tuple(BUDGET_POINT))
    return bad


def completeness(R: dict, src: Path, test_sha: str | None) -> list:
    """Why the site does not accept "complete" (empty: it does). Run only on a file that passed schema()."""
    bad = []
    P, n, G = R["protocol"], PROTOCOL["planned_series_per_arm"], PROTOCOL["games_per_series"]
    if P["dry_run"]:
        bad.append("a dry run")
    if test_sha is None:
        bad.append("the evaluation set is not present at build time: its hash is not confirmed")
    if R.get("t0_done") is not True:
        bad.append("the shared T0 run is not done")
    t0 = src / "runs" / "t0" / "aggregate.json"
    if not t0.exists():
        bad.append("the T0 aggregate is missing")
    else:
        T = json.loads(t0.read_text())
        if test_sha is not None and T.get("test_set_sha256") != test_sha:
            bad.append("the T0 aggregate's evaluation set hash differs")
        m = T.get("metrics") or {}
        if m.get("answered") != PROTOCOL["evaluation_positions"]:
            bad.append("T0 did not answer every evaluation position")
    lifts = {}
    for arm in PROTOCOL["arms"]:
        if sorted(R["series_finished"][arm]) != list(range(1, n + 1)):
            bad.append(f"{arm}: not every series 1-{n} finished")
        lifts[arm] = {}
        for s in range(1, n + 1):
            where = f"{arm} s{s:02d}"
            entry = R["inventory"][arm].get(str(s))
            A = aggregate(src, arm, s)
            if entry is None or A is None:
                bad.append(f"{where}: inventory entry or aggregate missing")
                continue
            if entry["games"] != list(range(1, G + 1)) or [g.get("game") for g in A.get("games", [])] != list(range(1, G + 1)):
                bad.append(f"{where}: not games 1-{G}")
            if A.get("lesson_prompt_sha256") != P["lesson_prompt_sha256"] or (
                    test_sha is not None and A.get("test_set_sha256") != test_sha):
                bad.append(f"{where}: aggregate hashes differ")
            if arm != "control":
                for cp in PROTOCOL["checkpoints"]["non_control"]:
                    ev = (A.get("evaluations") or {}).get(cp) or {}
                    if ev.get("answered") != PROTOCOL["evaluation_positions"]:
                        bad.append(f"{where}: {cp} did not answer every evaluation position")
            if arm == "lessons":
                want = {str(g) for g in range(1, G + 1)}
                if set(entry["lessons_files"]) != want:
                    bad.append(f"{where}: lesson files are not games 1-{G}")
                for g, h in entry["lessons_files"].items():
                    f = src / "runs" / "lessons" / f"s{s:02d}" / f"lessons-g{int(g):02d}.txt"
                    if not f.exists() or sha256(f) != h:
                        bad.append(f"{where}: lesson file of game {g} missing or not the inventory's")
            bad += budget_points(A, where)
            (a_lo, a_hi), (b_lo, b_hi) = LIFT_GAMES
            early, late = pooled(A.get("games", []), a_lo, a_hi), pooled(A.get("games", []), b_lo, b_hi)
            if not (close(early, A.get("games_error_rate_1_3")) and close(late, A.get("games_error_rate_8_10"))):
                bad.append(f"{where}: games 1-3 / 8-10 error rates do not follow from its games")
            lifts[arm][s] = early - late if early is not None and late is not None else None
    if bad:
        return bad
    # The lift and the signal, recomputed from the aggregates and the table.
    lift = R.get("learning_lift") or {}
    mean = lambda xs: sum(xs) / len(xs) if xs and None not in xs else None  # noqa: E731
    own = {arm: mean(list(lifts[arm].values())) for arm in PROTOCOL["arms"]}
    for arm in PROTOCOL["arms"]:
        row = lift.get(arm) or {}
        if not close(row.get("lift"), own[arm]):
            bad.append(f"learning_lift.{arm}.lift does not follow from the aggregates")
        if arm != "control":
            vs = mean([lifts[arm][s] - lifts["control"][s] for s in range(1, n + 1)])
            if not close(row.get("vs_control"), vs):
                bad.append(f"learning_lift.{arm}.vs_control does not follow from the aggregates")
            sig = (R.get("signal") or {}).get(arm) or {}
            t = R["table"][arm]
            rf = t["T10"]["risks_found"] - t["T0"]["risks_found"] if t["T10"] and t["T0"] else None
            rs = t["T10"]["right_safety"] - t["T0"]["right_safety"] if t["T10"] and t["T0"] else None
            if not (close(sig.get("risks_found_change"), rf) and close(sig.get("right_safety_change"), rs)):
                bad.append(f"signal.{arm}: changes do not follow from the table")
            elif sig.get("signal") is not (rf >= SIGNAL["risks_found_at_least"] and rs >= SIGNAL["right_safety_at_least"]):
                bad.append(f"signal.{arm}.signal is not the plan's rule applied to its changes")
    return bad


def lessons_shown(R: dict, src: Path) -> tuple[list, list]:
    """The lessons arm's lesson files that may be shown: finished series only, each file's hash equal to the
    inventory's. Returns ([(series, game, path)], problems)."""
    out, bad = [], []
    for s in sorted(R["series_finished"]["lessons"]):
        entry = R["inventory"]["lessons"].get(str(s))
        if entry is None:
            bad.append(f"lessons s{s:02d}: finished but not in the inventory")
            continue
        for g, h in sorted(entry["lessons_files"].items(), key=lambda x: int(x[0])):
            f = src / "runs" / "lessons" / f"s{s:02d}" / f"lessons-g{int(g):02d}.txt"
            if f.exists() and sha256(f) == h:
                out.append((s, int(g), f))
            else:
                bad.append(f"lessons s{s:02d} game {g}: file missing or not the inventory's (not shown)")
    return out, bad
