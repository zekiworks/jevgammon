"""The learning pilot's results, checked by the site before anything of them is shown (Zeki #2575, #2676). Nothing the
harness wrote is trusted or passed through:

- every per-series aggregate (runs/<arm>/sNN/aggregate.json) and the shared T0 aggregate is checked against a closed,
  recursive schema (every key, type and range), against its place (arm and series), the series' dice seed, the lesson
  prompt files present at build time and the private evaluation set present at build time, and against pilot.py's own
  counting (Zeki #2931): each evaluation's valid + invalid + failed = answered and its calls = valid; the budget arm's
  points one per game played, agreeing with the context records and with its empty points;
- the harness's summary (learning-pilot.json) is recomputed here from those aggregates exactly as pilot.py's summary()
  writes it, and refused unless every field agrees (table, games, series, inventory, finished series, completion, and
  once complete the learning lift, the signal and their intervals);
- what the page publishes is not the summary: it is a projection built here from the validated aggregates of finished
  series only, each with the sha256 of its aggregate (provenance).

validate() returns a Result. A refused summary publishes nothing of it. Public problem texts name fields of the schema,
never values or names (keys, directories) taken from the pilot's files: those are in the private problems only (stderr).
"""

import hashlib
import json
import random
import re
from datetime import datetime
from pathlib import Path

# The site's copy of the protocol (plan: 4 arms, 10 series of 10 games, T0 shared, T5 and T10 for the other arms, 200
# evaluation positions; the learning lift compares games 1-3 with games 8-10).
PROTOCOL = dict(arms=["control", "records", "lessons", "budget"], planned_series_per_arm=10, games_per_series=10,
                checkpoints={"shared": ["T0"], "non_control": ["T5", "T10"]}, evaluation_positions=200)
ARMS = PROTOCOL["arms"]
N, G, POSITIONS = PROTOCOL["planned_series_per_arm"], PROTOCOL["games_per_series"], PROTOCOL["evaluation_positions"]
LIFT_GAMES = ((1, 3), (8, 10))
SIGNAL = dict(risks_found_at_least=10, right_safety_at_least=-5)  # plan section 8, in percentage points
SCALE = 500  # the site's equity scale (thresholds.json equity_scale): error rate = 500 x mean loss
TOL = 1e-9
# pilot.py's fixed constants (harness ba8b011): the dice seed of each series and the intervals' bootstrap.
MASTER_SEED = "learning-pilot 2026-11-07"
BOOT_SEED, BOOT = 20261107, 10000
DISPLAY_RULE = ("Numbers per arm and evaluation as series finish; no verdict and no learning lift until every planned "
                "series of every arm is done.")
TABLE_KEYS = ["error_rate", "risk_judgement", "risks_found", "right_safety", "risk_appetite"]


def series_seed(s: int) -> int:
    return int(hashlib.sha256(f"{MASTER_SEED} series {s}".encode()).hexdigest()[:16], 16) & (2**63 - 1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Closed recursive schemas ---------------------------------------------------------------------------------------
# A spec is one of: ("int", lo, hi), ("num", lo, hi) (lo/hi None: open), ("bool",), ("str", regex), ("enum", values),
# ("opt", spec) (null allowed), ("list", spec, max_len), ("dict", required, optional) (closed: no other key),
# ("map", key_regex, spec) (closed key pattern), ("const", value).

def INT(lo=0, hi=None):
    return ("int", lo, hi)


def NUM(lo=0, hi=None):
    return ("num", lo, hi)


def OPT(spec):
    return ("opt", spec)


def LIST(spec, n=None):
    return ("list", spec, n)


def DICT(required, optional=None):
    return ("dict", required, optional or {})


BOOL, ISO = ("bool",), ("str", r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(\+00:00|Z)")
HEX64 = ("str", r"[0-9a-f]{64}")
GAME_NO, GAME_KEY = INT(1, G), ("map", r"(10|[1-9])", None)
PCT = OPT(NUM(0, 100))
EVAL = DICT(dict(answered=INT(0, POSITIONS), expected=INT(POSITIONS, POSITIONS), valid=INT(0, POSITIONS),
                 invalid=INT(0, POSITIONS), failed=INT(0, POSITIONS), error_rate=OPT(NUM()), risk_judgement=PCT,
                 risks_found=PCT, right_safety=PCT, risk_appetite=PCT, risk_pays=INT(0, POSITIONS),
                 safety_pays=INT(0, POSITIONS),
                 calls=DICT({k: INT(0, POSITIONS) for k in ("right_risk", "wrong_risk", "needless", "missed",
                                                            "right_safety", "none")}),
                 input_tokens_per_decision=OPT(NUM()), output_tokens_per_decision=OPT(NUM()), request_seconds=NUM(),
                 latency_median_s=OPT(NUM()), cost_usd=NUM(0, 0)))
# dry: written by pilot.py's dry run only (dry=True); a real T0 aggregate has no such key (absent: not dry).
T0_AGG = DICT(dict(name=("str", r"[^<>&]{1,120}"), wall_seconds=NUM(), finished_at=ISO, metrics=EVAL,
                   test_set_sha256=HEX64), dict(dry=BOOL))
GAME = DICT(dict(game=GAME_NO, decisions=INT(), invalid=INT(), unscored=INT(), valid=INT(), loss_sum=NUM(),
                 error_rate=OPT(NUM()), input_tokens_per_decision=OPT(NUM()), latency_median_s=OPT(NUM()),
                 request_seconds=NUM()),
            dict(won=BOOL, result=("enum", ("single", "gammon", "backgammon")), points=INT(1, 64), turns=INT()))
BUDGET_POINT = DICT(dict(after_game=GAME_NO, games_shown=LIST(GAME_NO, G), games_dropped=INT(0, G), tokens=INT(),
                         budget_tokens=OPT(INT())))
SERIES_AGG = DICT(dict(
    arm=("enum", tuple(ARMS)), series=INT(1, N), seed=INT(0, 2**63 - 1), finished_at=ISO, wall_seconds=NUM(),
    evaluations=("evaluations",), games=LIST(GAME, G), games_error_rate_1_3=OPT(NUM()),
    games_error_rate_8_10=OPT(NUM()), context_tokens_after_game=("map", r"(10|[1-9])", INT()),
    records_dropped_after_game=("map", r"(10|[1-9])", INT(0, G)), budget_context_empty_after_game=LIST(GAME_NO, G),
    budget_points=LIST(BUDGET_POINT, G),
    context_drops=LIST(DICT(dict(after_game=GAME_NO, dropped_game=GAME_NO, tokens=INT(), budget=OPT(INT()))), 100),
    evaluation_positions_excluded=INT(0, POSITIONS),
    lessons_calls=LIST(DICT(dict(game=GAME_NO, seconds=OPT(NUM()), input_tokens=OPT(INT()), output_tokens=OPT(INT()),
                                 finish=OPT(("str", r"[a-z_]{1,20}")), lessons_written=OPT(INT()),
                                 words_written=OPT(INT()), cut=OPT(BOOL))), 100),
    restarts=INT(0, 100), lesson_prompt_sha256=HEX64, test_set_sha256=HEX64,
    lessons_files=("map", r"(10|[1-9])", HEX64), cost_usd=NUM(0, 0)))
PROTOCOL_SPEC = DICT(dict(arms=LIST(("str", r"[a-z]{1,20}"), 8), planned_series_per_arm=INT(), games_per_series=INT(),
                          checkpoints=DICT(dict(shared=LIST(("str", r"T\d{1,2}"), 4),
                                                non_control=LIST(("str", r"T\d{1,2}"), 4))),
                          evaluation_positions=INT(), lesson_prompt_sha256=HEX64, test_set_sha256=HEX64, dry_run=BOOL))
# learning-pilot.json's top level; its other fields are compared whole with the recomputed summary.
SUMMARY_TOP = dict(updated_at=ISO, protocol=PROTOCOL_SPEC, planned_series_per_arm=INT(), complete=BOOL,
                   lesson_prompt_sha256=HEX64, t0_done=BOOL, display_rule=("str", r".{1,400}"),
                   series_done=("any",), series_finished=("any",), inventory=("any",), table=("any",),
                   games=("any",), series=("any",))
SUMMARY_COMPLETE = dict(signal=("any",), learning_lift=("any",), paired_series=("any",))


# Problem texts are public (the page and its data file show why a file was refused), so a name taken from the
# pilot's files (an unknown key, a key outside a map's pattern, a directory name) never goes into them: it is wrapped by
# untrusted() and replaced by WITHHELD_NAME in the public text; the private text (stderr) keeps it (Zeki #2931, 2).
WITHHELD_NAME = "[name withheld]"


def untrusted(name) -> str:
    return f"\x1f{str(name)!r}\x1f"


def public_problems(problems: list) -> list:
    return [re.sub("\x1f[^\x1f]*\x1f", WITHHELD_NAME, p) for p in problems]


def private_problems(problems: list) -> list:
    return [p.replace("\x1f", "") for p in problems]


def check(v, spec, where: str) -> list:
    """Problems of v against spec (empty: it conforms). bool is never an int; an int is a number, a float is not an
    int; NaN and infinities are refused. `where` only ever holds names of the schema or keys that matched it."""
    kind = spec[0]
    if kind == "any":
        return []
    if kind == "opt":
        return [] if v is None else check(v, spec[1], where)
    if kind == "const":
        return [] if v == spec[1] and type(v) is type(spec[1]) else [f"{where}: not the expected value"]
    if kind == "bool":
        return [] if type(v) is bool else [f"{where}: not a JSON bool"]
    if kind in ("int", "num"):
        ok = type(v) is int if kind == "int" else (type(v) in (int, float) and v == v and abs(v) != float("inf"))
        if not ok:
            return [f"{where}: not a JSON {'int' if kind == 'int' else 'number'}"]
        lo, hi = spec[1], spec[2]
        return [] if (lo is None or v >= lo) and (hi is None or v <= hi) else [f"{where}: out of range"]
    if kind == "str":
        return [] if isinstance(v, str) and re.fullmatch(spec[1], v) else [f"{where}: not an allowed string"]
    if kind == "enum":
        return [] if isinstance(v, str) and v in spec[1] else [f"{where}: not an allowed value"]
    if kind == "list":
        if not isinstance(v, list):
            return [f"{where}: not a JSON list"]
        if spec[2] is not None and len(v) > spec[2]:
            return [f"{where}: too long"]
        return [p for i, x in enumerate(v) for p in check(x, spec[1], f"{where}[{i}]")]
    if kind == "map":
        if not isinstance(v, dict):
            return [f"{where}: not a JSON object"]
        bad = [f"{where}: key {untrusted(k)} not allowed" for k in v if not re.fullmatch(spec[1], k)]
        return bad + ([p for k, x in v.items() if re.fullmatch(spec[1], k)
                       for p in check(x, spec[2], f"{where}.{k}")] if spec[2] else [])
    if kind == "dict":
        if not isinstance(v, dict):
            return [f"{where}: not a JSON object"]
        req, opt = spec[1], spec[2]
        bad = [f"{where}: unknown key {untrusted(k)}" for k in v if k not in req and k not in opt]
        bad += [f"{where}: {k} missing" for k in req if k not in v]
        return bad + [p for k, x in v.items() if k in req or k in opt for p in check(x, (req | opt)[k], f"{where}.{k}")]
    if kind == "evaluations":  # control: none; the other arms: exactly T5 and T10
        return check(v, DICT({}), where) if v == {} else check(v, DICT({"T5": EVAL, "T10": EVAL}), where)
    raise ValueError(kind)


# --- pilot.py's summary, recomputed from the aggregates ------------------------------------------------------------

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sub(a, b):
    return a - b if a is not None and b is not None else None


def pooled(games: list, lo: int, hi: int):
    """Error rate over games lo..hi, decisions pooled (pilot.py pooled_rate)."""
    sel = [x for x in games if lo <= x["game"] <= hi]
    n = sum(x["valid"] for x in sel)
    return SCALE * sum(x["loss_sum"] for x in sel) / n if n else None


def boot_ci(values_by_series, rng_seed):
    """pilot.py boot_ci: 95% percentile interval of the mean, resampling whole series by index."""
    n = len(values_by_series)
    if sum(v is not None for v in values_by_series) < 2:
        return None
    rng = random.Random(rng_seed)
    means = []
    for _ in range(BOOT):
        draw = [values_by_series[rng.randrange(n)] for _ in range(n)]
        draw = [v for v in draw if v is not None]
        if draw:
            means.append(sum(draw) / len(draw))
    means.sort()
    return [means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1]]


def finished(arm: str, a: dict, test_sha: str, prompt_sha: str) -> bool:
    """pilot.py series_finished: all 10 games played, both evaluations answered in full (not control), a lesson file
    after every game (lessons arm), the evaluation set's and the lesson prompt's hashes."""
    if [g["game"] for g in a["games"]] != list(range(1, G + 1)) or any(not g["decisions"] for g in a["games"]):
        return False
    if arm != "control" and any(a["evaluations"].get(cp, {}).get("answered") != POSITIONS for cp in ("T5", "T10")):
        return False
    if arm == "lessons" and sorted(int(g) for g in a.get("lessons_files", {})) != list(range(1, G + 1)):
        return False
    return a.get("test_set_sha256") == test_sha and a.get("lesson_prompt_sha256") == prompt_sha


def table_rows(t0m, aggs: dict) -> dict:
    table = {arm: {} for arm in ARMS}
    for arm in ARMS:
        table[arm]["T0"] = dict(t0m, shared=True) if t0m else None
        if arm == "control":
            continue
        for cp in (5, 10):
            ms = [a["evaluations"][f"T{cp}"] for a in aggs[arm].values()]
            row = {k: mean([m[k] for m in ms]) for k in TABLE_KEYS + ["input_tokens_per_decision", "latency_median_s"]}
            row.update(invalid=sum(m["invalid"] for m in ms), failed=sum(m["failed"] for m in ms),
                       request_seconds=round(sum(m["request_seconds"] for m in ms), 1), cost_usd=0.0, series=len(ms),
                       records_dropped=sum(a["records_dropped_after_game"].get(str(cp), a["records_dropped_after_game"]
                                                                               .get(cp, 0)) for a in aggs[arm].values()))
            table[arm][f"T{cp}"] = row
    return table


def games_rows(aggs: dict) -> dict:
    games = {}
    for arm in ARMS:
        gs = [g for a in aggs[arm].values() for g in a["games"]]
        lat = [g["latency_median_s"] for g in gs if g["latency_median_s"] is not None]
        games[arm] = dict(series=len(aggs[arm]), games=len(gs), decisions=sum(g["decisions"] for g in gs),
                          invalid=sum(g["invalid"] for g in gs),
                          error_rate=SCALE * sum(g["loss_sum"] for g in gs) / max(1, sum(g["valid"] for g in gs))
                          if gs else None,
                          input_tokens_per_decision=mean([g["input_tokens_per_decision"] for g in gs]),
                          latency_median_s=sorted(lat)[len(lat) // 2] if lat else None,
                          records_dropped=sum(max(a["records_dropped_after_game"].values() or [0])
                                              for a in aggs[arm].values()),
                          context_drops=sum(len(a["context_drops"]) for a in aggs[arm].values()),
                          budget_empty_points=sum(len(a.get("budget_context_empty_after_game", []))
                                                  for a in aggs[arm].values()),
                          wins=sum(bool(g.get("won")) for g in gs), cost_usd=0.0)
    return games


def lift_and_signal(t0m, aggs: dict) -> dict:
    series = sorted(set.intersection(*(set(aggs[a]) for a in ARMS)))
    signal, lift = {}, {}
    for arm in ARMS[1:]:
        rf = [sub(aggs[arm][s]["evaluations"]["T10"]["risks_found"], t0m["risks_found"]) for s in series]
        rs = [sub(aggs[arm][s]["evaluations"]["T10"]["right_safety"], t0m["right_safety"]) for s in series]
        ok = mean(rf) is not None and mean(rs) is not None
        signal[arm] = dict(risks_found_change=mean(rf), risks_found_ci=boot_ci(rf, BOOT_SEED),
                           right_safety_change=mean(rs), right_safety_ci=boot_ci(rs, BOOT_SEED),
                           signal=(mean(rf) >= SIGNAL["risks_found_at_least"]
                                   and mean(rs) >= SIGNAL["right_safety_at_least"]) if ok else None)
    for arm in ARMS:
        own = [sub(aggs[arm][s]["games_error_rate_1_3"], aggs[arm][s]["games_error_rate_8_10"]) for s in series]
        row = dict(lift=mean(own), lift_ci=boot_ci(own, BOOT_SEED))
        if arm != "control":
            vs = [sub(o, sub(aggs["control"][s]["games_error_rate_1_3"], aggs["control"][s]["games_error_rate_8_10"]))
                  for o, s in zip(own, series)]
            row.update(vs_control=mean(vs), vs_control_ci=boot_ci(vs, BOOT_SEED))
        lift[arm] = row
    return dict(signal=signal, learning_lift=lift, paired_series=series)


def summary(t0, aggs: dict, protocol: dict, test_sha: str, prompt_sha: str) -> dict:
    """pilot.py summary() on these aggregates, without updated_at; protocol is the (validated) file's own."""
    t0m = t0["metrics"] if t0 else None
    fin = {arm: sorted(s for s, a in aggs[arm].items() if finished(arm, a, test_sha, prompt_sha)) for arm in ARMS}
    t0_ok = bool(t0) and t0["metrics"]["answered"] == POSITIONS
    complete = not protocol["dry_run"] and t0_ok and all(fin[arm] == list(range(1, N + 1)) for arm in ARMS)
    out = dict(protocol=protocol, planned_series_per_arm=N, series_done={arm: len(aggs[arm]) for arm in ARMS},
               series_finished=fin, complete=complete, lesson_prompt_sha256=prompt_sha, t0_done=t0_ok,
               inventory={arm: {str(s): dict(games=[g["game"] for g in a["games"]],
                                             lessons_files=a.get("lessons_files", {}),
                                             test_set_sha256=a.get("test_set_sha256"),
                                             lesson_prompt_sha256=a.get("lesson_prompt_sha256"))
                                for s, a in sorted(aggs[arm].items())} for arm in ARMS},
               display_rule=DISPLAY_RULE, table=table_rows(t0m, aggs), games=games_rows(aggs),
               series=[{k: v for k, v in a.items() if k != "games"} | dict(games=[{k: v for k, v in g.items()
                                                                                    if k != "loss_sum"}
                                                                                   for g in a["games"]])
                       for arm in ARMS for a in aggs[arm].values()])
    if complete:
        out.update(lift_and_signal(t0m, aggs))
    return out


def same(a, b) -> bool:
    """Equal as JSON: same keys, same types (a bool is not a number), numbers equal within rounding."""
    if type(a) is bool or type(b) is bool:
        return type(a) is type(b) and a == b
    if type(a) in (int, float) and type(b) in (int, float):
        return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


# --- Validation and the public projection --------------------------------------------------------------------------

def rejected(problems: list) -> dict:
    """A refused file: the public problems (no name from the pilot's files) and the private ones (stderr only)."""
    return dict(accepted=False, producer_complete=False, complete=False, problems=public_problems(problems),
                private_problems=private_problems(problems), public=None, lessons=[], budget=[])


def eval_counts(m: dict, where: str) -> list:
    """pilot.py eval_metrics partitions the answered positions: each is failed, invalid or valid (exactly one), and each
    valid answer gets exactly one call. Failures and invalid answers may be nonzero; the totals must add up."""
    bad = []
    if m["valid"] + m["invalid"] + m["failed"] != m["answered"]:
        bad.append(f"{where}: valid + invalid + failed is not answered")
    if sum(m["calls"].values()) != m["valid"]:
        bad.append(f"{where}: the calls do not add up to the valid answers")
    return bad


def budget_coverage(A: dict, arm: str, where: str) -> list:
    """The budget arm's points as pilot.py records them, one context event after each game played: exactly one point
    per game 1..n in order (n = 10 for a finished series), each agreeing with the same event's tokens and dropped games
    in context_tokens_after_game and records_dropped_after_game, and the empty points exactly those with no game shown.
    The other arms have no empty budget point."""
    if arm != "budget":
        return [f"{where}: empty budget points outside the budget arm"] if A["budget_context_empty_after_game"] else []
    pts = A["budget_points"]
    if [p["after_game"] for p in pts] != list(range(1, len(A["games"]) + 1)):
        return [f"{where}: budget points are not one per game played, in order"]
    bad = [f"{where}: budget point after game {p['after_game']} disagrees with the context records" for p in pts
           if A["context_tokens_after_game"].get(str(p["after_game"])) != p["tokens"]
           or A["records_dropped_after_game"].get(str(p["after_game"])) != p["games_dropped"]]
    if A["budget_context_empty_after_game"] != [p["after_game"] for p in pts if not p["games_shown"]]:
        bad.append(f"{where}: empty budget points are not the points with no game shown")
    return bad


def load(p: Path):
    try:
        return json.loads(p.read_text()), None
    except (OSError, ValueError):
        return None, f"{p.name}: not readable JSON"


def aggregates(src: Path, test_sha: str, prompt_sha: str) -> tuple:
    """The T0 aggregate and every series aggregate, each checked (schema, place, seed, hashes); with their sha256."""
    bad, aggs, shas = [], {arm: {} for arm in ARMS}, {arm: {} for arm in ARMS}
    runs = src / "runs"
    t0 = t0_sha = None
    if (runs / "t0" / "aggregate.json").exists():
        t0, e = load(runs / "t0" / "aggregate.json")
        bad += [f"T0 aggregate: {e}"] if e else check(t0, T0_AGG, "T0 aggregate")
        if not e and not bad:
            bad += eval_counts(t0["metrics"], "T0 aggregate metrics")
            if t0["test_set_sha256"] != test_sha:
                bad.append("T0 aggregate: made with another evaluation set")
        t0_sha = sha256(runs / "t0" / "aggregate.json")
    for arm_dir in sorted(runs.iterdir()) if runs.is_dir() else []:
        if arm_dir.name == "t0":
            continue
        if arm_dir.name not in ARMS:
            if any(arm_dir.rglob("aggregate.json")):
                bad.append(f"runs/{untrusted(arm_dir.name)}: not an arm of the protocol")
            continue
        arm = arm_dir.name
        for p in sorted(arm_dir.glob("*/aggregate.json")):
            m = re.fullmatch(r"s(\d\d)", p.parent.name)
            if not m or not 1 <= int(m.group(1)) <= N:
                bad.append(f"{arm} {untrusted(p.parent.name)}: not a series 1-{N} of the protocol")
                continue
            where = f"{arm} {p.parent.name}"
            s = int(m.group(1))
            A, e = load(p)
            e = [f"{where}: {e}"] if e else check(A, SERIES_AGG, f"{where} aggregate")
            if e:
                bad += e
                continue
            if A["arm"] != arm or A["series"] != s:
                bad.append(f"{where}: aggregate names another arm or series")
            if A["seed"] != series_seed(s):
                bad.append(f"{where}: dice seed is not the series' seed")
            if A["test_set_sha256"] != test_sha:
                bad.append(f"{where}: made with another evaluation set")
            if A["lesson_prompt_sha256"] != prompt_sha:
                bad.append(f"{where}: made with another lesson prompt")
            games = [g["game"] for g in A["games"]]
            if games != list(range(1, len(games) + 1)):
                bad.append(f"{where}: games are not 1..n in order")
            for g in A["games"]:
                if g["valid"] + g["invalid"] + g["unscored"] != g["decisions"]:
                    bad.append(f"{where} game {g['game']}: decision counts do not add up")
                rate = SCALE * g["loss_sum"] / g["valid"] if g["valid"] else None
                if not same(rate, g["error_rate"]):
                    bad.append(f"{where} game {g['game']}: error rate does not follow from its losses")
            for k, (lo, hi) in zip(("games_error_rate_1_3", "games_error_rate_8_10"), LIFT_GAMES):
                if not same(pooled(A["games"], lo, hi), A[k]):
                    bad.append(f"{where}: {k} does not follow from its games")
            if (arm == "control") != (A["evaluations"] == {}):
                bad.append(f"{where}: evaluations do not match the arm")
            if arm != "budget" and A["budget_points"]:
                bad.append(f"{where}: budget points outside the budget arm")
            if arm != "lessons" and A["lessons_files"]:
                bad.append(f"{where}: lesson files outside the lessons arm")
            for cp, m in A["evaluations"].items():
                bad += eval_counts(m, f"{where} {cp}")
            bad += budget_coverage(A, arm, where)
            for i, bp in enumerate(A["budget_points"]):
                shown = bp["games_shown"]
                if len(set(shown)) != len(shown) or any(x > bp["after_game"] for x in shown) or (
                        bp["games_dropped"] != bp["after_game"] - len(shown)):
                    bad.append(f"{where}: budget_points[{i}] games shown/dropped inconsistent")
            aggs[arm][s], shas[arm][s] = A, sha256(p)
    return t0, t0_sha, aggs, shas, bad


def validate(R, src: Path, prompt: dict | None, plan_hashes: list, test_sha: str) -> dict:
    """The site's reading of the pilot's files. test_sha: the private evaluation set's hash (required)."""
    if prompt is None:
        return rejected(["the lesson prompt files are not present: the results cannot be bound to the prompt"])
    prompt_sha = prompt["sha256"]
    if not isinstance(R, dict):
        return rejected(["learning-pilot.json is not an object"])
    top = DICT({k: v for k, v in SUMMARY_TOP.items()}, SUMMARY_COMPLETE)
    bad = check(R, top, "learning-pilot.json")
    if bad:
        return rejected(bad)
    P = R["protocol"]
    for k, want in PROTOCOL.items():
        if P[k] != want:
            bad.append(f"protocol.{k} differs from the site's copy of the protocol")
    if R["planned_series_per_arm"] != N:
        bad.append("planned_series_per_arm differs from the protocol")
    if P["lesson_prompt_sha256"] not in plan_hashes:
        bad.append("protocol.lesson_prompt_sha256 is not the hash the plan states")
    if P["lesson_prompt_sha256"] != prompt_sha:
        bad.append("protocol.lesson_prompt_sha256 is not the hash of the lesson prompt files")
    if R["lesson_prompt_sha256"] != P["lesson_prompt_sha256"]:
        bad.append("lesson_prompt_sha256 differs from protocol.lesson_prompt_sha256")
    if P["test_set_sha256"] != test_sha:
        bad.append("protocol.test_set_sha256 is not the hash of the evaluation set present at build time")
    try:
        datetime.fromisoformat(R["updated_at"])
    except ValueError:
        bad.append("updated_at is not a time")
    if bad:
        return rejected(bad)
    t0, t0_sha, aggs, shas, bad = aggregates(src, test_sha, prompt_sha)
    if not bad and t0 is not None and t0.get("dry", False) != P["dry_run"]:
        bad.append("T0 aggregate: dry flag differs from the protocol's")
    if bad:
        return rejected(bad)
    want = summary(t0, aggs, P, test_sha, prompt_sha)
    keys = set(R) - {"updated_at"}
    bad = [f"{k} does not follow from the aggregates" for k in sorted(keys | set(want))
           if k not in R or k not in want or not same(R[k], want[k])]
    if bad:
        return rejected(bad)
    # Every finished series is published with its files: the lessons arm's lesson files must be there, unchanged.
    fin = want["series_finished"]
    lessons = []
    for s in fin["lessons"]:
        A = aggs["lessons"][s]
        for g in range(1, G + 1):
            f = src / "runs" / "lessons" / f"s{s:02d}" / f"lessons-g{g:02d}.txt"
            if not f.exists() or sha256(f) != A["lessons_files"][str(g)]:
                bad.append(f"lessons s{s:02d} game {g}: lesson file missing or not the aggregate's")
            else:
                lessons.append((s, g, f, next(x for x in A["games"] if x["game"] == g)))
    if bad:
        return rejected(bad)
    budget = [(s, aggs["budget"][s]["budget_points"]) for s in fin["budget"]]
    # The summary agreed field by field, so the file's "complete" is the recomputed one: nothing left to note.
    return dict(accepted=True, producer_complete=R["complete"], complete=want["complete"], problems=[],
                public=public(R["updated_at"], t0, t0_sha, aggs, shas, fin, want, test_sha, prompt_sha),
                lessons=lessons, budget=budget, private_problems=[])


def game_curve(done: dict) -> dict:
    """Per arm, the error rate of game 1..10 averaged over the finished series (the mean of the series' own game error
    rates; a game with no valid decision is left out of its mean): {arm: {"1": rate or None, ..., "10": ...}}."""
    return {arm: {str(g): mean([x["error_rate"] for a in done[arm].values() for x in a["games"] if x["game"] == g])
                  for g in range(1, G + 1)} for arm in ARMS}


def last_update(t0, done: dict):
    """The latest finished_at of the validated aggregates behind the page (the shared T0 and the finished series), as
    written (ISO, UTC); None when there is none."""
    times = ([t0["finished_at"]] if t0 else []) + [a["finished_at"] for arm in ARMS for a in done[arm].values()]
    return max(times, key=datetime.fromisoformat) if times else None


def public(updated_at, t0, t0_sha, aggs, shas, fin, want, test_sha, prompt_sha) -> dict:
    """What the page and its data file publish: rebuilt from the finished series' validated aggregates only."""
    done = {arm: {s: aggs[arm][s] for s in fin[arm]} for arm in ARMS}
    out = dict(updated_at=updated_at, last_update=last_update(t0, done), planned_series_per_arm=N,
               series_done={arm: len(fin[arm]) for arm in ARMS}, complete=want["complete"],
               t0_done=want["t0_done"], table=table_rows(t0["metrics"] if t0 else None, done),
               games=games_rows(done), game_error_rate=game_curve(done), series_finished=fin,
               series_total_done=sum(len(v) for v in fin.values()), series_total_planned=N * len(ARMS),
               budget_empty_points={"budget": sum(len(a["budget_context_empty_after_game"])
                                                  for a in done["budget"].values())},
               budget_points_total={"budget": sum(len(a["budget_points"]) for a in done["budget"].values())},
               signal_rule=dict(SIGNAL),
               provenance=dict(test_set_sha256=test_sha, lesson_prompt_sha256=prompt_sha, t0_aggregate_sha256=t0_sha,
                               series_aggregate_sha256={arm: {str(s): shas[arm][s] for s in fin[arm]}
                                                        for arm in ARMS}))
    if want["complete"]:
        out.update({k: want[k] for k in ("signal", "learning_lift", "paired_series")})
    return out
