#!/usr/bin/env python3
"""Learning from experience (preliminary, running): the learning pilot's page (learning/) and its data file
(data/v3/learning-pilot.json).

    python3 tools/site/learning_page.py [--out DIR] [--plan MD] [--src DIR] [--check SITE]

build.py renders the page with the site (S["learning"] = from_state(STATE)); this command renders the page alone, for
review: OUT/learning/index.html and OUT/data/v3/learning-pilot.json (OUT defaults to a new temporary directory, never
the live site). Every source is read at render time:

- the plan (--plan, default mailbox/Learning pilot - plan 2026-11-07.md, committed): the single source of the protocol
  text, shown section by section, with its commitment line near the top;
- the pilot's files as snapshot.py copies them to STATE/learning (--src, default ~/.local/state/bg-site/learning; a
  missing or empty directory means no results yet):
  - learning-pilot.json, the harness's summary, absent before the first series: "No results yet" and progress
    0 / planned. The status line (status()), the two charts with their tables and progress appear as series finish;
    the verdict (the signal rule per arm, the budget arm's fixed reading) and the learning lift only once the site
    accepts the results as complete (plan §9);
  - runs/lessons/sNN/aggregate.json and lessons-gKK.txt: every lesson the model wrote, next to its game (series, game,
    result from the series aggregate's games), for finished series only;
  - lessons_system.txt and lessons_user.txt, the lesson prompt, and its sha256: one hash over the system file's bytes
    immediately followed by the user file's bytes; when the plan states a 64-hex hash, the render fails unless the
    files hash to it.
  - explore/explore.json (workspace/learning-retest/out/explore.json): the exploratory block, after the verdict and
    apart from it, only once learning_validate.validate_explore accepts it against the validated pilot; missing, no
    block (Ümit #2950/#2952).

Arms are named on the page by ARM_LABEL (no memory, full records, own lessons, budget (empty: no game fit)); the data
file keeps the plan's keys.

Only what the page shows goes into the data file (aggregates; whitelisted keys): never positions, answers or contexts.
--check SITE runs checks.py's page checks on the output: numbers trace (against the output's own data file and the
site's content files), no mixing, links and ids (resolved with the built site SITE laid under the output, read-only),
the private-strings scan of every output file, and the learning page's own checks (checks.check_learning).
"""

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))

from common import BANNED, NA, ROOT, count, esc, fmt, nm, status_badge  # noqa: E402

import learning_validate as V  # noqa: E402
import pages as P  # noqa: E402
from method import spec_markdown  # noqa: E402

PATH = P.TAB_LEARNING_PATH
DATA = "data/v3/learning-pilot.json"
TITLE = "Learning from experience (preliminary, running)"
TITLE_COMPLETE = "Learning from experience (complete)"
TITLE_PREREG = "Learning from experience (pre-registered)"
# Pre-registration only (default ON): the build never reads the pilot's results, aggregates, lesson files or the
# private test set, and the page shows the protocol and the pre-registered lesson prompt only. Results and lessons are
# published only after this is switched off in a reviewed commit.
# Switched off on Zeki's GO for 34ef85e (bus #2935): the completed pilot's validated results and lessons are published.
PREREGISTRATION_ONLY = False
COMMITMENT = "Results will be published whichever way they go, including no lift."
PLAN = ROOT / "mailbox/Learning pilot - plan 2026-11-07.md"
# The pilot's files as snapshot.py copies them (STATE/learning): the build's only source besides the plan.
SOURCE = "learning"
DESCRIPTION = ("The learning pilot of the backgammon benchmark (preliminary, running): does a model play better after "
               "seeing its own earlier games? The pre-registered plan, the lesson prompt and the results as they come in.")
# Ids of the blocks that only a complete results file may carry (checks.check_learning): the verdict, the lift, the
# signal rule's result and the Learning tab's leaders.
COMPLETE_ONLY_IDS = ("learning-verdict", "learning-lift", "learning-signal", "learning-leaders")
COMPLETE_ONLY_KEYS = ("learning_lift", "signal", "paired_series")
# Plan section 5: the smoke is the first 3 series of every arm; the run then continues to 10 in total per arm.
SMOKE_SERIES = 3
# The arms' colours, fixed (Ümit #2925): the one map behind every line, dot and legend swatch of both charts (the CSS
# custom property --lp of each element). Control is also dashed (CONTROL_DASH): in the risks chart it is the flat line
# at its T0 value, as control has no later test round.
ARM_COLOUR = {"control": "var(--text-2)", "records": "var(--reading)", "lessons": "var(--good)",
              "budget": "var(--wrong)"}
CONTROL_DASH = "6 4"
# The arms' names on the page (Ümit #2950): the one map behind every legend, table, verdict line and sentence that
# names an arm. The data file and every internal key keep the plan's names (control, records, lessons, budget).
ARM_LABEL = {"control": "no memory", "records": "full records", "lessons": "own lessons",
             "budget": "budget (empty: no game fit)"}
# The one line at the top of Results (Ümit #2950/#2952; facts checked against the run by LearningPilot: Gemma 4 31B
# with reasoning off on the site's own vLLM, GNUbg 1.08 Beginner = the site's "GNUbg weak", 4 arms, 10 x 10 games).
RUN_LINE = ("One model: Gemma 4 31B (reasoning off, our GPUs) · opponent: GNUbg weak · 4 kinds of memory (one of them "
            "is no memory) · 10 series of 10 games each.")
MODEL = "Gemma 4 31B"


def arm_name(arm: str) -> str:
    """An arm's name on the page, escaped (ARM_LABEL; a key outside the map is shown as written)."""
    return esc(ARM_LABEL.get(arm, arm))


# The plan's verdict wording for an always-empty budget context (section 11, Interpretation, fixed now).
BUDGET_VERDICT = "with this budget, record memory could not be provided"
# The plan's bullet that fixes the Learning tab's order (section 9, amended before any model call, 09bcbc4).
TAB_ORDER = "Learning tab order"
# The plan's fixed reading of an empty budget context (section 11, Zeki #2577), shown with the budget arm's points.
BUDGET_READING = "Interpretation, fixed now"
# The pilot's evaluation set: private, never published; read at build time only for its hash (learning_validate) and
# for checks.check_learning (no evaluation position on the page).
TEST_SET = ROOT / "workspace/learning-pilot/test_set.json"
# The exploratory file (Ümit #2950/#2952), as snapshot.py copies it from workspace/learning-retest/out/explore.json:
# missing, no exploratory block; present, shown only after learning_validate.validate_explore accepts it.
EXPLORE = "explore/explore.json"
# The evaluation requests' settings (LearningPilot checked the sent ones against the request code and a stored request;
# the server's effective defaults by a read-only check of spark3: vLLM's log, the model's generation_config.json; Zeki
# #2964): fixed text on the page; the numbers are also in the data file, so they trace.
SAMPLING = dict(temperature=1.0, max_tokens=1, top_logprobs=20, max_options_per_request=26, grouped_positions=32,
                positions=200, in_flight_t0_and_retests=4, in_flight_budget=1,
                server_default_temperature=1.0, server_default_top_k=64, server_default_top_p=0.95,
                # Zeki #2991: what was checked in the stored records of T0, the 5 retests and the 20 budget evaluations
                answers_checked=5200, requests_checked=7202)
CHECKPOINTS = ("T0", "T5", "T10")
CHECKPOINT_LABEL = {"T0": "Before game 1", "T5": "After game 5", "T10": "After game 10"}
# Shown per arm x test round; the keys copied to the data file are exactly these.
METRICS = [("error_rate", "Error rate (PR)", 1, ""), ("risk_judgement", "Risk judgement", 1, ""),
           ("risks_found", "Risks found", 1, "%"), ("right_safety", "Right safety", 1, "%"),
           ("risk_appetite", "Risk appetite", 1, "%"), ("invalid", "Invalid answers", 0, ""),
           ("failed", "Failed requests", 0, ""), ("records_dropped", "Game records dropped from context", 0, ""),
           ("input_tokens_per_decision", "Input tokens per decision", 0, ""),
           ("latency_median_s", "Median s per request", 2, ""), ("request_seconds", "Request s", 1, ""),
           ("cost_usd", "API spend $", 2, ""), ("series", "Series", 0, "")]
GAME_METRICS = [("series", "Series", 0), ("games", "Games", 0), ("wins", "Wins", 0), ("decisions", "Decisions", 0),
                ("invalid", "Invalid answers", 0), ("error_rate", "Error rate (PR)", 1),
                ("records_dropped", "Game records dropped from context", 0),
                ("input_tokens_per_decision", "Input tokens per decision", 0),
                ("latency_median_s", "Median s per request", 2), ("cost_usd", "API spend $", 2)]
# Cost wording (Zeki #2531): never "$0 because local".
COST_NOTE = "$0 API spend; local compute cost not estimated."
GAME_KEYS = ("game", "won", "result", "points")
# Column names of the learning-lift and signal tables (pilot.py summary); any other key is shown as written.
RESULT_LABELS = {"lift": "Learning lift", "lift_ci": "95% interval", "vs_control": "Minus no memory's lift",
                 "vs_control_ci": "95% interval (minus no memory)", "per_arm": "Learning lift",
                 "risks_found_change": "Risks found, change (pp)", "risks_found_ci": "95% interval (risks found)",
                 "right_safety_change": "Right safety, change (pp)", "right_safety_ci": "95% interval (right safety)",
                 "signal": "Signal rule met"}
WITHHELD = "[withheld: private address]"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


# --- Sources ------------------------------------------------------------------------------------------------

def site_base() -> str:
    """The site's address (tools/site/build.py BASE), for the canonical link. Loaded by file: a bare "import build"
    can find tools/v3/build.py first."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("site_build", SITE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BASE


def redact(line: str) -> tuple[str, int]:
    """Safety net for the site's private-strings rule (common.BANNED): a code span, or else a word, holding a private
    address or key name is replaced by a visible mark. The plan should hold none; any use is counted and shown."""
    n = 0

    def span(m):
        nonlocal n
        if BANNED.search(m.group(0)):
            n += 1
            return WITHHELD
        return m.group(0)
    line = re.sub(r"`[^`]*`", span, line)
    line = re.sub(r"\S+", span, line)
    return line, n


def read_plan(path: Path) -> dict:
    text = path.read_text()
    if COMMITMENT not in text:
        raise SystemExit(f"{path}: the commitment line is missing: {COMMITMENT!r}")
    title, status, sections, cur, redacted = None, None, [], None, 0
    for raw in text.splitlines():
        line, n = redact(raw)
        redacted += n
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        elif line.startswith("## "):
            cur = dict(title=line[3:].strip(), lines=[])
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
        elif re.match(r"\*\*Status:", line):
            status = line.strip().strip("*").strip()
    for s in sections:
        s["markdown"] = "\n".join(s.pop("lines")).strip()
    return dict(file=path.name, title=title, status=status, commitment=COMMITMENT,
                sha256=hashlib.sha256(text.encode()).hexdigest(), sections=sections, redacted=redacted,
                hashes=HEX64.findall(text), tab_order=plan_bullet(sections, TAB_ORDER),
                budget_reading=plan_bullet(sections, BUDGET_READING))


def plan_bullet(sections: list, label: str) -> dict:
    """The plan's bullet whose bold label starts with `label`, with its sub-bullets, as written (any depth, dedented):
    the page shows it where it applies. A plan without it stops the render."""
    for s in sections:
        lines = s["markdown"].splitlines()
        for i, line in enumerate(lines):
            ind = len(line) - len(line.lstrip(" "))
            if line.lstrip(" ").startswith(f"- **{label}"):
                j = i + 1
                while j < len(lines) and len(lines[j]) - len(lines[j].lstrip(" ")) > ind:
                    j += 1
                return dict(section=s["title"], markdown="\n".join(x[ind:] for x in lines[i:j]))
    raise SystemExit(f"the plan has no '{label}' bullet")


def read_prompt(src: Path, plan: dict) -> dict | None:
    """The lesson prompt and its hash; None when the files are not in src (no snapshot yet)."""
    files = [src / "lessons_system.txt", src / "lessons_user.txt"]
    if not all(f.exists() for f in files):
        return None
    system, user = (f.read_bytes() for f in files)
    sha = hashlib.sha256(system + user).hexdigest()
    if plan["hashes"] and sha not in plan["hashes"]:
        raise SystemExit(f"lesson prompt sha256 {sha} is not the one the plan states ({', '.join(plan['hashes'])})")
    return dict(system=system.decode(), user=user.decode(), sha256=sha, stated_in_plan=sha in plan["hashes"])


def pick(row, keys):
    return None if row is None else {k: row.get(k) for k in keys if k in row} | (
        {"shared": True} if row.get("shared") else {})


# The complete-only blocks' fields, exactly (learning_validate recomputes them; nothing else is published).
LIFT_KEYS = ("lift", "lift_ci", "vs_control", "vs_control_ci")
SIGNAL_KEYS = ("risks_found_change", "risks_found_ci", "right_safety_change", "right_safety_ci", "signal")


def shown_results(pub: dict) -> dict:
    """learning_validate's public projection (rebuilt from the finished series' validated aggregates), cut down to
    the fields the page shows, by explicit keys. The learning lift and the signal are there only when complete."""
    keys = [k for k, *_ in METRICS]
    out = dict(updated_at=pub["updated_at"], last_update=pub["last_update"],
               planned_series_per_arm=pub["planned_series_per_arm"],
               series_done=pub["series_done"], complete=pub["complete"], t0_done=pub["t0_done"],
               table={arm: {cp: pick(by_cp.get(cp), keys) for cp in CHECKPOINTS if cp in by_cp}
                      for arm, by_cp in pub["table"].items()},
               series_total_done=pub["series_total_done"], series_total_planned=pub["series_total_planned"],
               series_finished=pub["series_finished"],
               games={arm: pick(g, [k for k, *_ in GAME_METRICS]) for arm, g in pub["games"].items()},
               game_error_rate=pub["game_error_rate"], budget_empty_points=pub["budget_empty_points"],
               budget_points_total=pub["budget_points_total"], signal_rule=pub["signal_rule"],
               provenance=pub["provenance"])
    if pub["complete"]:
        out.update(learning_lift={arm: pick(r, LIFT_KEYS) for arm, r in pub["learning_lift"].items()},
                   signal={arm: pick(r, SIGNAL_KEYS) for arm, r in pub["signal"].items()},
                   paired_series=pub["paired_series"])
    return out


class TestSetRequired(RuntimeError):
    """Results or lessons are present but the private evaluation set is missing, unreadable or not the one the results
    were made with: the leakage check cannot run, so the build fails (only the no-results state builds without it)."""


def rejected(problems: list) -> dict:
    """The validation of a results file the site refused: every field present, nothing complete."""
    return dict(accepted=False, producer_complete=False, complete=False, problems=problems)


def is_complete(L) -> bool:
    v = L["validation"]
    return bool(v and v.get("complete"))


def status(L) -> dict:
    """The status line at the top of the page (Ümit #2925), derived from the validated state only, exactly one of:

    - "Done": learning_validate accepts the results as complete (every planned series of every arm finished, the shared
      T0 answered in full, not a dry run);
    - "Not started": no accepted results file, or one with no finished series in any arm and no shared T0 run;
    - "Smoke running: N of 3 series per arm": N, the series finished in EVERY arm (the minimum over the arms of the
      validated finished series), is below 3. Plan section 5 runs 3 series per arm first (the smoke) and only then
      continues, so the run is in its smoke phase exactly until every arm has finished 3 series;
    - "Running: N of 10 series per arm": N is 3 or more and the results are not accepted as complete (this includes
      10 of 10 when, say, the shared T0 is not answered in full).

    The time is the latest finished_at of the validated aggregates behind the page (the shared T0 and the finished
    series: learning_validate.last_update), in UTC; none before the first one."""
    R = L["results"]
    planned = R["planned_series_per_arm"] if R else V.N
    n = min(len(s) for s in R["series_finished"].values()) if R else 0
    if is_complete(L):
        phase, line = "done", "Done"
    elif R is None or (not R["series_total_done"] and not R["t0_done"]):
        phase, line = "not-started", "Not started"
    elif n < SMOKE_SERIES:
        phase, line = "smoke", f"Smoke running: {n} of {SMOKE_SERIES} series per arm"
    else:
        phase, line = "running", f"Running: {n} of {planned} series per arm"
    return dict(phase=phase, line=line, series_per_arm=n, planned=planned, smoke_series=SMOKE_SERIES,
                last_update=R["last_update"] if R else None)


def title(L) -> str:
    """The page title and heading follow the validated status, like the top label."""
    if L.get("preregistration_only"):
        return TITLE_PREREG
    return TITLE_COMPLETE if is_complete(L) else TITLE


def status_label(L) -> str:
    """The page's top label, from the validated status (status()): "Complete" only when learning_validate accepts
    complete, "Not started" before anything validated has run. The Experiments page's card shows the same label."""
    if L.get("preregistration_only"):
        return "Pre-registration"
    phase = L["status"]["phase"]
    return "Complete" if phase == "done" else "Not started" if phase == "not-started" else "Preliminary · running"


def require_test_set(test_set: Path, why: str) -> str:
    try:
        return V.sha256(test_set)
    except OSError as e:
        raise TestSetRequired(f"{why}, but the evaluation set {test_set} is missing or unreadable ({e.strerror}): "
                              "the leakage check cannot run") from None


def read_results(src: Path, plan: dict, prompt: dict | None, test_set: Path) -> dict:
    """results, validation, lessons and the budget arm's points from src, after learning_validate. With a results
    file, an aggregate or a lesson file present, the evaluation set must be present, readable and the one the results
    were made with, else the build fails (TestSetRequired); only the no-results state builds without it."""
    path = src / "learning-pilot.json"
    none = dict(results=None, validation=None, lessons=[], budget=[])
    runs = src / "runs"
    if not path.exists():
        if any(runs.rglob("aggregate.json")) or any(runs.rglob("lessons-g*.txt")):
            require_test_set(test_set, "aggregates or lesson files are present")
        return none
    test_sha = require_test_set(test_set, "a results file is present")
    try:
        R = json.loads(path.read_text())
    except ValueError:
        return none | dict(validation=rejected(["learning-pilot.json is not JSON"]))
    stated = R.get("protocol", {}).get("test_set_sha256") if isinstance(R, dict) and isinstance(
        R.get("protocol"), dict) else None
    if stated is not None and stated != test_sha:
        raise TestSetRequired(f"the results were made with evaluation set {str(stated)[:12]}…, but {test_set} hashes "
                              f"to {test_sha[:12]}…: the leakage check would test the wrong set")
    v = V.validate(R, src, prompt, plan["hashes"], test_sha)
    validation = dict(accepted=v["accepted"], producer_complete=v["producer_complete"], complete=v["complete"],
                      problems=v["problems"])
    if not v["accepted"]:
        # The public problems name no key or directory taken from the pilot's files; the private ones, which do, go to
        # the build's stderr (its log) only, never to the page or its data file.
        for p in v["private_problems"]:
            print(f"learning_validate (private): {p}", file=sys.stderr)
        return none | dict(validation=validation)
    lessons = []
    for s, g, f, game in v["lessons"]:
        text = f.read_text().strip()
        if text:
            lessons.append(dict(series=s, text=text, **{k: game.get(k) for k in GAME_KEYS} | {"game": g}))
    budget = [dict(series=s, points=[pick(p, ("after_game", "games_shown", "games_dropped", "tokens",
                                              "budget_tokens")) for p in points]) for s, points in v["budget"]]
    out = dict(results=shown_results(v["public"]), lessons=lessons, budget=budget, validation=validation)
    if (src / EXPLORE).exists():
        out["explore"] = read_explore(src / EXPLORE, v, test_sha)
    return out


def read_explore(path: Path, v: dict, test_sha: str) -> dict:
    """The exploratory block's data: learning_validate.validate_explore's public projection and the fixed sampling
    settings, or, refused, its fixed problem codes only (the details go to stderr)."""
    e = V.validate_explore(path, v, test_sha)
    for p in e["private_problems"]:
        print(f"learning_validate explore (private): {p}", file=sys.stderr)
    if not e["accepted"]:
        return dict(accepted=False, problems=e["problems"])
    return dict(accepted=True, problems=[], **e["public"], sampling=dict(SAMPLING))


def data(plan_path: Path, src: Path, test_set: Path = TEST_SET,
         preregistration_only: bool | None = None) -> dict:
    """The page's data from the plan and src (the STATE/learning layout; missing or empty: no results yet). In
    pre-registration-only mode (PREREGISTRATION_ONLY, the default) no results file, aggregate, lesson file or test set
    is read at all: the page is the protocol and the pre-registered lesson prompt only."""
    prereg = PREREGISTRATION_ONLY if preregistration_only is None else preregistration_only
    plan = read_plan(plan_path)
    prompt = read_prompt(src, plan)
    shown = (dict(results=None, validation=None, lessons=[], budget=[]) if prereg
             else read_results(src, plan, prompt, test_set))
    L = dict(version="v3", preregistration_only=prereg,
             plan={k: v for k, v in plan.items() if k not in ("redacted", "hashes")},
             redacted=plan["redacted"], lesson_prompt=prompt, **shown)
    if not prereg:  # pre-registration only: nothing of the run is read, so there is no status to state
        L["status"] = status(L)
    L["source_sha256"] = hashlib.sha256(json.dumps(L, sort_keys=True).encode()).hexdigest()
    return L


def from_state(state: Path) -> dict:
    return data(PLAN, state / SOURCE)


# --- Page ---------------------------------------------------------------------------------------------------

def num(v, digits, unit="") -> str:
    return nm(NA) if v is None else fmt(v, digits) + unit


def validation_note(L) -> str:
    """Why the site refused the results file (learning_validate), named field by field. An accepted file has no
    problems: its summary agreed with the aggregates field by field."""
    v = L["validation"]
    if not v or v.get("accepted") or not v.get("problems"):
        return ""
    items = "".join(f"<li>{esc(p)}</li>" for p in v["problems"])
    head = ("<strong>Results file not accepted.</strong> It failed the site's checks against the pre-registered "
            "protocol and the series' own files, so none of its numbers, lessons or budget points are shown:")
    return f'<div class="note validation-note"><p>{head}</p><ul>{items}</ul></div>'


def utc(t: str) -> str:
    return datetime.fromisoformat(t).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def status_line(L) -> str:
    """The status line (status()): one of the four phrases and the time of the last update, at the top of the page."""
    st = L["status"]
    t = st["last_update"]
    when = f'<time datetime="{esc(t)}">{utc(t)}</time>' if t else "none yet"
    refused = (' <span class="small">The latest results file was not accepted: see Status and progress.</span>'
               if L["validation"] and not L["validation"].get("accepted") else "")
    return (f'<p class="lp-status" id="learning-status-line"><strong data-phase="{st["phase"]}">{esc(st["line"])}'
            f'</strong> <span class="small">· Last update: {when}</span>{refused}</p>')


def progress(L) -> str:
    R = L["results"]
    if R is None:
        return validation_note(L) or ('<p class="note"><strong>No results yet.</strong></p><p>Progress: 0 / planned '
                                      'series per arm (the planned count appears with the first results file).</p>')
    planned = R["planned_series_per_arm"]
    rows = [f'<tr><th scope="row">{arm_name(a)}</th><td class="num">{count(len(s))} / {count(planned)}</td></tr>'
            for a, s in R["series_finished"].items()]
    t0 = (f'<p class="note">Shared T0 test (before any context): {"done" if R["t0_done"] else "not yet done"}.</p>'
          if "t0_done" in R else "")
    badge = "" if R["complete"] else status_badge("Preliminary") + " "
    return (f'<p class="note">{badge}{esc(L["status"]["line"])}. Results file updated {esc(R["updated_at"])}.</p>'
            f'{t0}' + validation_note(L) + P.table(["Arm", "Series finished / planned"], rows, "Progress per arm"))


def results_table(R) -> str:
    rows = []
    t0s = [by_cp.get("T0") for by_cp in R["table"].values()]
    shared = all(t and t.get("shared") for t in t0s)
    for i, (arm, by_cp) in enumerate(R["table"].items()):
        for cp in CHECKPOINTS:
            if cp not in by_cp or (shared and cp == "T0" and i):
                continue
            row = by_cp[cp]
            label = "All arms (shared)" if shared and cp == "T0" else ARM_LABEL.get(arm, arm)
            cells = ("".join(f'<td class="num">{num(row.get(k), d, u)}</td>' for k, _, d, u in METRICS)
                     if row else f'<td colspan="{len(METRICS)}">{nm("Not yet run")}</td>')
            rows.append(f'<tr><th scope="row">{esc(label)}</th><td>{cp}</td>{cells}</tr>')
    return P.SWIPE + P.table(["Arm", "Test"] + [h for _, h, *_ in METRICS], rows,
                             "The evaluation set per arm and test round: means over the arm's finished series",
                             cls="board list")


def games_table(R) -> str:
    rows = [f'<tr><th scope="row">{arm_name(arm)}</th>'
            + "".join(f'<td class="num">{num(g.get(k), d)}</td>' for k, _, d in GAME_METRICS) + "</tr>"
            for arm, g in R["games"].items() if g]
    return P.SWIPE + P.table(["Arm"] + [h for _, h, _ in GAME_METRICS], rows,
                             "Pilot games against the opponent, all finished series", cls="board list")


def flat(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return fmt(v, 1)
    if isinstance(v, list):
        return " to ".join(flat(x) for x in v)
    return nm(NA) if v is None else esc(v)


def by_arm(d: dict, arms) -> dict:
    """{arm: {measure: value}}, whichever way round the results file keys it."""
    if any(k in arms for k in d):
        return d
    out = {}
    for measure, per in d.items():
        for arm, v in per.items():
            out.setdefault(arm, {})[measure] = v
    return out


def arm_table(d: dict, arms, caption: str) -> str:
    d = by_arm(d, arms)
    cols = list(dict.fromkeys(k for v in d.values() for k in v))
    rows = [f'<tr><th scope="row">{arm_name(a)}</th>' + "".join(f'<td class="num">{flat(v.get(c))}</td>' for c in cols)
            + "</tr>" for a, v in d.items()]
    head = ["Arm"] + [esc(RESULT_LABELS.get(c, c.replace("_", " "))) for c in cols]
    return P.SWIPE + P.table(head, rows, esc(caption), cls="board list")


def results(L) -> str:
    """Every number per arm and test round, and per arm from the games (finished series only); no lift or verdict."""
    R = L["results"]
    if R is None:
        if L["validation"]:
            return '<p class="note"><strong>Results file not accepted:</strong> see Status and progress.</p>'
        return '<p class="note"><strong>No results yet.</strong> Numbers appear here as each series finishes.</p>'
    out = [results_table(R)]
    if R.get("games"):
        out.append(games_table(R))
    out.append(f'<p class="table-note">{esc(COST_NOTE)}</p>')
    return "".join(out)


def ci(v) -> str:
    return f"95% interval {flat(v)}" if v else f"95% interval {nm(NA)}"


def verdict(L) -> str:
    """The verdict (Ümit #2925 item 3): only when learning_validate accepts the results as complete, the pre-registered
    signal rule per non-control arm (plan section 8), the plan's fixed reading of the budget arm (section 11) and the
    learning lift with its intervals; before that, only how many series are done (the numbers are in Results)."""
    R, st = L["results"], L["status"]
    if not (R and R["complete"] and is_complete(L)):
        return (f'<p class="note" id="learning-verdict-pending"><strong>No verdict and no learning lift yet.</strong> '
                'They are shown only when every planned series of every arm is done (plan section 9): '
                f'{count(st["series_per_arm"])} of {count(st["planned"])} series done in every arm. The numbers so '
                'far are under Results.</p>')
    arms = list(R["table"])
    rule, sig = R["signal_rule"], R["signal"]
    lift = by_arm(R["learning_lift"], arms)
    # Wording as the results file (mailbox, Zeki #2929): "threshold", never "effect"; the lift differences only as
    # observed; nothing stronger than the data.
    head = verdict_head(R)
    items = "".join(
        f'<li data-arm="{esc(a)}"><strong>{arm_name(a)}</strong>: '
        f'{"threshold reached" if s["signal"] else "threshold not reached"}. '
        f'Risks found {fmt(s["risks_found_change"], 1, signed=True)} points ({ci(s["risks_found_ci"])}); right safety '
        f'{fmt(s["right_safety_change"], 1, signed=True)} points ({ci(s["right_safety_ci"])}).</li>'
        for a in arms if (s := sig.get(a)))
    vs = {a: (lift.get(a) or {}).get("vs_control") for a in arms if a != "control"}
    vs_ci = {a: (lift.get(a) or {}).get("vs_control_ci") for a in vs}
    C, B, LS = ARM_LABEL["control"], ARM_LABEL["budget"], ARM_LABEL["lessons"]
    if vs and all(v is not None and v < 0 for v in vs.values()):
        lift_head = f"All observed game-lift differences are below the {C} arm."
    elif vs and all(v is not None and v > 0 for v in vs.values()):
        lift_head = f"All observed game-lift differences are above the {C} arm."
    else:
        lift_head = f"The observed game-lift differences against the {C} arm differ in sign between the arms."
    with_zero = [ARM_LABEL.get(a, a) for a, c in vs_ci.items() if c and c[0] <= 0 <= c[1]]
    names = ", ".join(with_zero[:-1]) + " and " + with_zero[-1] if len(with_zero) > 1 else "".join(with_zero)
    lift_notes = [f"For {names}, the intervals of the difference include zero."] if with_zero else []
    empty, total = R["budget_empty_points"]["budget"], R["budget_points_total"]["budget"]
    always_empty = bool(total and empty == total)
    if always_empty:
        budget_text = (f'<strong>{esc(B)}</strong>: its context was empty at all {count(empty)} of {count(total)} '
                       f'points (no whole game record fit within the {esc(LS)} arm\'s token count). The plan\'s fixed '
                       f'reading (section 11): <strong>{esc(BUDGET_VERDICT)}</strong>, not "record memory didn\'t '
                       'help".')
        c = vs_ci.get("budget")
        if c and not c[0] <= 0 <= c[1]:
            lift_notes.append(
                f"The {B} arm's interval does not include zero, although {B} and {C} had the same memory "
                "policy (an empty context) and the same dice seeds; that does not make their realized game prompts "
                "the same, as the games diverge once a play differs. The source of this unexpected difference and "
                "the calibration of the intervals were not determined in this pilot.")
    else:
        budget_text = (f'<strong>{esc(B)}</strong>: its context was empty at {count(empty)} of {count(total)} points, '
                       'so the plan\'s fixed reading for an always-empty context (section 11) does not apply.')
    return ('<div id="learning-verdict">'
            f'<p><strong>{esc(head)}</strong></p>'
            f'<p class="small">Signal rule (plan section 8, pre-registered), per arm other than {esc(C)}, averaged '
            f'over its series: risks found after game 10 minus before game 1 at least '
            f'{fmt(rule["risks_found_at_least"], 0, signed=True)} points, and right safety after game 10 minus before '
            f'game 1 at least {fmt(rule["right_safety_at_least"], 0, signed=True)} points.</p>'
            f'<ul class="notes lp-verdict">{items}</ul>'
            '<p class="small">Before game 1 (T0) is one run: the after-game-10 minus before-game-1 intervals are '
            'conditional on that single observed T0. This does not apply to the game-lift intervals.</p>'
            f'<p id="learning-budget-verdict">{budget_text}</p>'
            f'<p id="learning-lift-verdict"><strong>{esc(lift_head)}</strong> '
            + " ".join(esc(n) for n in lift_notes) + '</p></div>'
            '<div id="learning-signal"><h3>Signal rule per arm</h3>'
            + arm_table(R["signal"], arms, "Signal rule per arm (definition: the plan's Signal rule)") + "</div>"
            '<div id="learning-lift"><h3>Learning lift</h3><p class="small">Error rate in games 1-3 minus games 8-10 '
            f'(decisions pooled; positive: the arm played better later), and the same minus {esc(C)}\'s, paired by '
            'series (plan section 7). 95% intervals: 10,000 resamples of whole series.</p>'
            + arm_table(R["learning_lift"], arms, "Learning lift per arm (definition: the plan's Metrics)") + "</div>")


# --- Exploratory, after the results (Ümit #2950/#2952) ----------------------------------------------------------

EXPLORE_METRIC_LABEL = {"risks_found": "Risks found", "right_safety": "Right safety", "error_rate": "Error rate (PR)",
                        "risk_judgement": "Risk judgement", "risk_appetite": "Risk appetite"}
EXPLORE_GROUP_LABEL = {"all": "All runs", "t0+retests": "T0 and retests", "retests": "Retests r1-r5",
                       "budget": f"{ARM_LABEL['budget']}"}
# The retests' own range under their rows (Zeki #2991): these measures, min-max and SD.
RETEST_RANGE = ("risks_found", "right_safety", "error_rate")


def amb_cell(s: dict) -> str:
    """An arm-minus-budget cell: mean [95% interval] (checks.check_learning reads it back)."""
    return f'{fmt(s["mean"], 1, signed=True)} [{fmt(s["ci"][0], 1)}, {fmt(s["ci"][1], 1)}]'


def run_label(r: dict) -> str:
    if r["kind"] == "t0":
        return "Before game 1 (T0, shared)"
    if r["kind"] == "retest":
        return f"Retest r{r['retest']}"
    return f"Series {r['series']}, {CHECKPOINT_LABEL[r['checkpoint']].lower()}"


def retest_range(s: dict) -> str:
    sd = fmt(s["sd"], 2) if s["sd"] is not None else NA
    return f'{fmt(s["min"], 1)}-{fmt(s["max"], 1)} (SD {sd})'


def spread_cell(s: dict) -> str:
    sd = fmt(s["sd"], 2) if s["sd"] is not None else NA
    return f'{fmt(s["mean"], 1)} ({fmt(s["min"], 1)}-{fmt(s["max"], 1)}; SD {sd})'


def explore_agreement(X: dict, B: str) -> str:
    """How often two empty-context runs chose different plays (counts of positions, of 200; which positions stays
    private), per group of run pairs, and the facts that follow from the data file's numbers only."""
    A, runs = X["agreement"], X["runs"]
    G = A["summary"]
    label = {"T0 vs retests": "T0 vs each retest", "retest vs retest": "Retest vs retest",
             "T0 vs budget": f"T0 vs each {B} evaluation", "retests vs budget": f"Each retest vs each {B} evaluation",
             "budget vs budget": f"{B} evaluation vs {B} evaluation"}
    rows = [f'<tr><th scope="row">{label[g]}</th>'
            f'<td class="num" data-agree="{g}" data-k="n">{fmt(s["n"], 0)}</td>'
            f'<td class="num" data-agree="{g}" data-k="mean">{fmt(s["mean"], 1)}</td>'
            f'<td class="num" data-agree="{g}" data-k="range">{fmt(s["min"], 0)}-{fmt(s["max"], 0)}</td>'
            f'<td class="num" data-agree="{g}" data-k="sd">{fmt(s["sd"], 2) if s["sd"] is not None else NA}</td></tr>'
            for g, s in G.items()]
    table = P.SWIPE + P.table(["Pairs of runs", "Pairs", "Mean", "Min-max", "SD"], rows,
                              "Positions (of 200) where two empty-context runs chose different plays",
                              cls="board list lp-explore-agree")
    rr, tr = G["retest vs retest"], G["T0 vs retests"]
    t0 = next(r for r in runs if r["kind"] == "t0")
    ret = [r for r in runs if r["kind"] == "retest"]
    facts = [f'The retests differ from each other on {fmt(rr["min"], 0)}-{fmt(rr["max"], 0)} positions; T0 differs '
             f'from each retest on {fmt(tr["min"], 0)}-{fmt(tr["max"], 0)}.'] if ret else []
    if ret and len({(r["risks_found"], r["right_safety"]) for r in ret}) == 1:
        facts.append(f'Every retest has risks found {fmt(ret[0]["risks_found"], 1)} and right safety '
                     f'{fmt(ret[0]["right_safety"], 1)}, against T0\'s {fmt(t0["risks_found"], 1)} and '
                     f'{fmt(t0["right_safety"], 1)}.')
    if ret and tr["min"] > rr["max"]:
        facts.append("T0 differs from the later empty-context runs; the cause was not verified.")
    k = A["positions_not_unanimous_across_retests"]
    facts.append(f"Positions where the {fmt(len(ret), 0)} retests do not all choose the same play: {fmt(k, 0)} of "
                 f"{fmt(X['sampling']['positions'], 0)}.")
    return ('<h3>Do the empty-context runs choose the same plays?</h3>' + table
            + f'<p id="learning-explore-agreement">{esc(" ".join(facts))}</p>')


def explore(L) -> str:
    """The exploratory block, after the verdict and apart from it: each arm minus budget (the noise baseline), the
    empty-context runs and their spread, the evaluation requests' settings and the next version's note. Shown only as
    learning_validate.validate_explore accepted it; refused, only its fixed problem codes."""
    X = L["explore"]
    head = (f'<p class="lp-explore-label"><strong>{esc(V.EXPLORE_LABEL.capitalize())}.</strong> Not part of the '
            'pre-registered verdict above.</p>')
    if not X["accepted"]:
        items = "".join(f"<li>{esc(p)}</li>" for p in X["problems"])
        return (head + '<div class="note validation-note"><p><strong>Exploratory file not accepted.</strong> It failed '
                f'the site\'s checks, so none of it is shown:</p><ul>{items}</ul></div>')
    B, S = esc(ARM_LABEL["budget"]), X["sampling"]
    rows = []
    for a in V.EXPLORE_ARMS:
        for cp in V.EXPLORE_CPS:
            rows.append(f'<tr><th scope="row">{arm_name(a)}</th><td>{esc(CHECKPOINT_LABEL[cp])}</td>'
                        + "".join(f'<td class="num" data-arm="{a}" data-cp="{cp}" data-m="{m}">'
                                  f'{amb_cell(X["arm_minus_budget"][a][cp][m])}</td>' for m in V.EXPLORE_METRICS)
                        + "</tr>")
    amb = P.SWIPE + P.table(["Arm", "Test"] + [EXPLORE_METRIC_LABEL[m] for m in V.EXPLORE_METRICS],
                            rows, f"Each arm minus {B} in the same series, mean over {count(X['series'])} series "
                                  "[95% interval]; risks found and right safety in percentage points",
                            cls="board list lp-explore-amb")
    runs, ncols = [], 1 + len(V.RUN_COUNTS) + len(V.RUN_METRICS)
    for i, r in enumerate(X["runs"]):
        if i == 0 or (r["kind"] == "budget") != (X["runs"][i - 1]["kind"] == "budget"):
            group = (f"{B}: its evaluations, {count(S['in_flight_budget'])} request in flight" if r["kind"] == "budget"
                     else f"T0 and retests: {count(S['in_flight_t0_and_retests'])} requests in flight")
            runs.append(f'<tr class="lp-group"><th scope="rowgroup" colspan="{ncols}">{group}</th></tr>')
        runs.append(f'<tr><th scope="row">{esc(run_label(r))}</th>'
                    + "".join(f'<td class="num" data-run="{i}" data-k="{k}">{count(r[k])}</td>' for k in V.RUN_COUNTS)
                    + "".join(f'<td class="num" data-run="{i}" data-k="{m}">{num(r[m], 1)}</td>'
                              for m in V.RUN_METRICS) + "</tr>")
        nxt = X["runs"][i + 1]["kind"] if i + 1 < len(X["runs"]) else None
        if r["kind"] == "retest" and nxt != "retest" and "retests" in X["spread"]:
            # The retests' own range (r1-r5 only, Zeki #2991): T0's difference stays outside it.
            sp = X["spread"]["retests"]
            runs.append('<tr class="lp-group"><th scope="row">Retests r1-r5: min-max (SD)</th>'
                        + "<td></td>" * len(V.RUN_COUNTS)
                        + "".join(f'<td class="num" data-rspread="{m}">{retest_range(sp[m])}</td>'
                                  if m in RETEST_RANGE else "<td></td>" for m in V.RUN_METRICS) + "</tr>")
    # Not sortable (data-nosort): its group rows (T0 and retests; the budget arm's evaluations) keep their order.
    runs_table = P.SWIPE + P.table([(h, " data-nosort") for h in ["Run", "Answered", "Valid", "Invalid", "Failed"]
                                    + [EXPLORE_METRIC_LABEL[m] for m in V.RUN_METRICS]], runs,
                                   "The same 200 evaluation prompts with an empty context",
                                   cls="board list lp-explore-runs")
    groups = V.SPREAD_GROUPS
    spread_rows = ['<tr><th scope="row">Runs</th>' + "".join(
        f'<td class="num" data-group="{g}" data-k="n">{count(X["spread"][g]["risks_found"]["n"])}</td>' for g in groups)
        + "</tr>"] + [f'<tr><th scope="row">{EXPLORE_METRIC_LABEL[m]}</th>' + "".join(
            f'<td class="num" data-group="{g}" data-m="{m}">{spread_cell(X["spread"][g][m])}</td>' for g in groups)
        + "</tr>" for m in V.RUN_METRICS]
    spread_table = P.SWIPE + P.table(["Measure"] + [esc(EXPLORE_GROUP_LABEL[g]) for g in groups], spread_rows,
                                     "Spread over the empty-context runs: mean (min-max; SD)",
                                     cls="board list lp-explore-spread")
    short = [f"r{k} ({count(n)} of {count(S['positions'])})" for k, n in X["retest_answer_counts"].items()
             if n != S["positions"]]
    pending = (f'<p class="table-note">Retests not yet answered in full are not in the table: {esc(", ".join(short))}.'
               '</p>' if short else "")
    agree = explore_agreement(X, B)
    return (head
            + f'<h3>Each arm minus {B}, paired by series</h3>'
            f'<p>The {B} arm\'s context was empty at every point, so its evaluations after games 5 and 10 are '
            'empty-context retests of the T0 prompts: here it is the noise baseline. Each value is the arm\'s '
            f'evaluation minus {B}\'s, paired by series (same series id and dice seed; the games differ once plays '
            f'differ), averaged over the {count(X["series"])} series, with a 95% interval (10,000 resamples of whole '
            'series, the pilot\'s bootstrap). The calibration of the intervals was not determined in this pilot. This '
            'is not part of the pre-registered verdict.</p>' + amb
            + '<h3>Empty-context runs: the same prompts, again</h3>'
            '<p>The shared T0 run, the retests of the T0 prompts and the evaluations of the '
            f'{B} arm, whose context was always empty, with their spread. The retests measure the variability between '
            'empty-context runs; they do not establish its cause. The cause of the differences between empty-context '
            'runs was not verified; any sampling or numerical explanation is a hypothesis only.</p>'
            + runs_table + pending + spread_table + agree
            + '<h3>How the evaluation requests were made</h3>'
            '<p><strong>Sent</strong> with every evaluation request:</p><ul>'
            f'<li>temperature {fmt(S["temperature"], 1)};</li><li>max_tokens {count(S["max_tokens"])};</li>'
            f'<li>logprobs, with top_logprobs {count(S["top_logprobs"])};</li>'
            '<li>the assistant turn prefilled with "Answer:", with continue_final_message;</li>'
            '<li>enable_thinking false;</li><li>no top_p, top_k or seed sent.</li></ul>'
            '<p><strong>The server\'s effective defaults</strong> (a read-only check of the serving machine): vLLM\'s '
            'log says its default sampling parameters are overridden by the model\'s generation_config.json, '
            f'temperature {fmt(S["server_default_temperature"], 1)}, top_k {count(S["server_default_top_k"])}, top_p '
            f'{fmt(S["server_default_top_p"], 2)}; that file is identical on the server and in our copy of the model. '
            'No seed was sent; the server\'s seed behaviour was not checked.</p>'
            '<p>The play is the argmax of the returned option-letter probabilities (several tokens per letter are '
            'summed). The cause of differences between empty-context runs was not verified.</p>'
            '<p>Checked in the stored records of T0, the 5 retests and the 20 budget evaluations: all '
            f'{count(S["answers_checked"])} answers have probability_source "logprobs"; all '
            f'{count(S["requests_checked"])} requests are the prefill readout (max_tokens {count(S["max_tokens"])}, '
            'continue_final_message), and none carries response_format, so the constrained-letter fallback never '
            'fired; no request errors. Whether vLLM returned raw or processed logprobs (before or after '
            'temperature/top_k/top_p) cannot be shown from the stored records; it was not determined.</p>'
            f'<p>Positions with more than {count(S["max_options_per_request"])} options '
            f'({count(S["grouped_positions"])} of the {count(S["positions"])}) are asked in groups, then among the '
            f'group winners. The retests ran with {count(S["in_flight_t0_and_retests"])} requests in flight, like T0; '
            f'the {B} evaluations with {count(S["in_flight_budget"])}.</p>'
            '<h3>Next version (not run)</h3>'
            '<p>Budget-match the records at the decision level: the most recent decisions, with their verdicts, that '
            f'fit within the {arm_name("lessons")} arm\'s token count.</p>')



def game_result(x) -> str:
    if x["won"] is None:
        return nm(NA)
    return (f'{"won" if x["won"] else "lost"} {count(x["points"])} point{"s" if x["points"] != 1 else ""}'
            f' ({esc(x["result"])})')


def lessons(L) -> str:
    """Every lesson the lessons arm wrote, next to its game: series, game and the game's result, from the validated
    lesson files of finished series only (learning_validate binds each file to its aggregate's hash). One box per
    series, the first open; the text is escaped and shown as written."""
    if not L["lessons"]:
        return (f'<p class="note">No lessons yet: they appear with each finished series of the {arm_name("lessons")} '
                'arm.</p>')
    by_series = {}
    for x in L["lessons"]:
        by_series.setdefault(x["series"], []).append(x)
    out = []
    for i, (s, xs) in enumerate(by_series.items()):
        items = "".join(
            f'<li class="lp-lesson" data-series="{esc(str(x["series"]))}" data-game="{esc(str(x["game"]))}">'
            f'<p class="small"><strong>Series {esc(str(x["series"]))}, game {esc(str(x["game"]))}</strong>: '
            f'{game_result(x)}. Lessons written after this game:</p><pre class="citation">{esc(x["text"])}</pre></li>'
            for x in xs)
        out.append(f'<details class="lp-series"{" open" if i == 0 else ""}><summary>Series {esc(str(s))}: '
                   f'lessons after games {esc(str(xs[0]["game"]))}-{esc(str(xs[-1]["game"]))}</summary>'
                   f'<ul class="notes">{items}</ul></details>')
    return (f'<p class="small">The {arm_name("lessons")} arm only. Each series starts with no lessons; after each '
            'game the model wrote its lessons, which the next game read.</p>' + "".join(out))


def prompt(L) -> str:
    p = L["lesson_prompt"]
    if p is None:
        return '<p class="note">The lesson prompt files are not in this build yet.</p>'
    stated = ("" if p["stated_in_plan"] else
              '<p class="note">The plan does not state this hash yet.</p>')
    return (f'<p>sha256 of the system file\'s bytes immediately followed by the user file\'s bytes: '
            f'<code>{p["sha256"]}</code></p>{stated}<h3>System</h3><pre class="citation">{esc(p["system"])}</pre>'
            f'<h3>User</h3><pre class="citation">{esc(p["user"])}</pre>')


def leader_order(R: dict) -> list:
    """The plan's Learning tab order (section 9): the non-control arms that meet the signal rule first, then the others;
    within each group by learning lift minus control's lift, higher first. Control is the reference, never ranked."""
    lift = by_arm(R.get("learning_lift") or {}, list(R["table"]))
    met = {a: bool(((R.get("signal") or {}).get(a) or {}).get("signal")) for a in R["table"]}
    vs = {a: (lift.get(a) or {}).get("vs_control") for a in R["table"]}
    return sorted((a for a in R["table"] if a != "control"),
                  key=lambda a: (not met[a], vs[a] is None, -(vs[a] or 0)))


def latest(by_cp: dict) -> tuple:
    """The arm's latest test round with a value: (checkpoint, row)."""
    for cp in reversed(CHECKPOINTS):
        row = by_cp.get(cp)
        if row and row.get("error_rate") is not None:
            return cp, row
    return None, None


def tab_card(L) -> str:
    """The Learning tab's leaders (Ümit #2553/#2557; plan section 9, Learning tab order): none until every planned
    series is done, only 'running, n of N series' and per-arm interim numbers in the plan's arm order; then the arms in
    the plan's order. The plan's bullet is shown as written."""
    order = L["plan"]["tab_order"]
    rule = (f'<div class="tab-rule">{spec_markdown(order["markdown"])}<p class="table-note">Plan section '
            f'{esc(order["section"])}, as pre-registered.</p></div>')
    R = L["results"]
    if R and R["complete"]:
        lift = by_arm(R.get("learning_lift") or {}, list(R["table"]))
        sig = R.get("signal") or {}
        items = "".join(f'<li><strong>{arm_name(a)}</strong>: signal rule {flat((sig.get(a) or {}).get("signal"))}; '
                        f'learning lift minus {arm_name("control")}\'s {flat((lift.get(a) or {}).get("vs_control"))}'
                        '</li>' for a in leader_order(R))
        block = (f'<div id="learning-leaders"><h3>Arms in order</h3><ol class="leaders-list">{items}</ol>'
                 f'<p class="table-note">{arm_name("control")}: the reference, not ranked.</p></div>')
    else:
        state = (("Results file not accepted: see Status and progress." if L["validation"] else
                  "Not started: no series has finished.") if R is None else
                 f'Running, {count(R["series_total_done"])} of {count(R["series_total_planned"])} series.')
        rows = []
        for arm, by_cp in (R["table"].items() if R else []):
            cp, row = latest(by_cp)
            g = (R.get("games") or {}).get(arm) or {}
            rows.append(f'<tr><th scope="row">{arm_name(arm)}</th>'
                        f'<td class="num">{count(len(R["series_finished"][arm]))} / '
                        f'{count(R["planned_series_per_arm"])}</td>'
                        f'<td>{esc(CHECKPOINT_LABEL[cp]) if cp else nm(NA)}</td>'
                        f'<td class="num">{num(row.get("error_rate") if row else None, 1)}</td>'
                        f'<td class="num">{num(row.get("risks_found") if row else None, 1, "%")}</td>'
                        f'<td class="num">{num(g.get("error_rate"), 1)}</td></tr>')
        table = (P.SWIPE + P.table(["Arm", "Series finished / planned", "Latest test round", "Error rate (PR)",
                                    "Risks found", "Error rate in games (PR)"], rows,
                                   "Interim numbers per arm, in the plan's arm order (not a ranking)", cls="board list")
                 if rows else "")
        block = (f'<div id="learning-interim"><p class="note"><strong>No ranking or leader yet.</strong> '
                 f'{esc(state)}</p>{table}</div>')
    return block + rule


def nice_step(span: float) -> float:
    raw = span / 4 if span > 0 else 1
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)


def arm_style(arm: str) -> str:
    return f'style="--lp:{ARM_COLOUR[arm]}"'


def line_chart(key: str, label: str, unit: str, xs: list, lines: list, xtitle: str = "") -> str:
    """One line chart in the site's SVG chart style (chart-svg: grid, muted axis text, a bold title), one line per arm
    in its fixed colour (ARM_COLOUR). xs: [(x key, x label)]; lines: [(arm, line points, dots, dashed)] with points as
    [(x index, value)]. Every dot carries its arm, x and value (one decimal, as in the table under the chart) for
    checks.check_learning; the values are the data file's."""
    W, H, L0, R0, T = 360, 260, 46, 46, 28  # R0 = L0: the last x label ("After game 10") fits
    B = 52 if xtitle else 40
    pw = W - L0 - R0
    ys = [v for _, line, dots, _ in lines for _, v in line + dots]
    lo, hi = min(ys), max(ys)
    step = nice_step(hi - lo)
    pad = step if lo == hi else 0
    lo, hi = math.floor(lo / step) * step - pad, math.ceil(hi / step) * step + pad
    x = lambda i: L0 + pw * i / (len(xs) - 1)  # noqa: E731
    y = lambda v: H - B - (H - B - T) * (v - lo) / ((hi - lo) or 1)  # noqa: E731
    parts = [f'<text x="{L0}" y="{T - 12}" class="lp-title">{esc(label)}</text>']
    v = lo
    while v <= hi + step / 2:
        parts.append(f'<line class="grid" x1="{L0}" x2="{L0 + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="muted" x="{L0 - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:g}{unit}</text>')
        v += step
    for i, (_, xl) in enumerate(xs):
        parts.append(f'<text class="muted" x="{x(i):.1f}" y="{H - B + 16}" text-anchor="middle">{esc(xl)}</text>')
    if xtitle:
        parts.append(f'<text class="muted" x="{L0 + pw / 2:.1f}" y="{H - B + 34}" text-anchor="middle">'
                     f'{esc(xtitle)}</text>')
    for arm, line, dots, dashed in lines:
        if len(line) > 1:
            dash = f' stroke-dasharray="{CONTROL_DASH}"' if dashed else ""
            parts.append(f'<polyline class="lp-line" data-arm="{esc(arm)}" {arm_style(arm)}{dash} points="'
                         + " ".join(f"{x(i):.1f},{y(val):.1f}" for i, val in line) + '"/>')
        for i, val in dots:
            parts.append(f'<circle class="lp-dot" data-arm="{esc(arm)}" data-x="{esc(xs[i][0])}" '
                         f'data-value="{val:.1f}" {arm_style(arm)} cx="{x(i):.1f}" cy="{y(val):.1f}" r="4">'
                         f'<title>{arm_name(arm)}, {esc(xs[i][1])}: {fmt(val, 1)}{unit}</title></circle>')
    return (f'<svg class="chart-svg" data-chart="{esc(key)}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(label)}, one line per arm">' + "".join(parts) + "</svg>")


def legend(arms, dashed: tuple = ()) -> str:
    return '<p class="chart-legend">' + "".join(
        f'<span><i class="swatch lp-swatch{" lp-dashed" if a in dashed else ""}" data-arm="{esc(a)}" '
        f'{arm_style(a)}></i>{arm_name(a)}</span>' for a in arms) + "</p>"


def risks_points(R) -> dict:
    """{arm: [(checkpoint index, risks found)]} from the data file's table: the shared T0 and, for the non-control arms,
    T5 and T10 of their finished series. Control has T0 only."""
    out = {}
    for arm, by_cp in R["table"].items():
        out[arm] = [(i, row["risks_found"]) for i, cp in enumerate(CHECKPOINTS)
                    if (row := by_cp.get(cp)) and row.get("risks_found") is not None
                    and (arm != "control" or cp == "T0")]
    return out


def games_points(R) -> dict:
    """{arm: [(game index, error rate)]}: each game's error rate averaged over the arm's finished series."""
    return {arm: [(g - 1, v) for g in range(1, V.G + 1) if (v := per.get(str(g))) is not None]
            for arm, per in R["game_error_rate"].items()}


def chart_table(name: str, caption: str, xs: list, R, cells: dict) -> str:
    """The numbers under a chart: arm x checkpoint or arm x game, each cell tagged with its arm and x for
    checks.check_learning. cells: {arm: {x key: html}}."""
    rows = [f'<tr><th scope="row">{arm_name(a)}</th><td class="num">{count(len(R["series_finished"][a]))}</td>'
            + "".join(f'<td class="num" data-arm="{esc(a)}" data-x="{esc(k)}">{cells[a][k]}</td>' for k, _ in xs)
            + "</tr>" for a in R["table"]]
    return P.SWIPE + P.table(["Arm", "Series"] + [esc(lab) for _, lab in xs], rows, esc(caption),
                             cls=f"board list lp-numbers lp-{name}")


def verdict_head(R) -> str:
    """The verdict's first sentence (the page's, and the home page's learning section quotes it)."""
    met = [a for a in R["table"] if (R["signal"].get(a) or {}).get("signal")]
    return ("No arm reached the pre-registered signal threshold (plan section 8)." if not met else
            "Arms that reached the pre-registered signal threshold (plan section 8): "
            f"{', '.join(ARM_LABEL.get(a, a) for a in met)}.")


def risks_figure(R, fid: str = "learning-chart-risks") -> str:
    """Chart (a) of the Results section with its numbers table; "" while no arm has a risks-found value."""
    arms = list(R["table"])
    xs = [(cp, CHECKPOINT_LABEL[cp]) for cp in CHECKPOINTS]
    risks = risks_points(R)
    if not any(risks.values()):
        return ""
    lines = []
    for a in arms:
        pts = risks[a]
        if a == "control" and pts:  # control: T0 only, drawn flat at its T0 value across every checkpoint
            lines.append((a, [(0, pts[0][1]), (len(xs) - 1, pts[0][1])], pts, True))
        else:
            lines.append((a, pts, pts, False))
    cells = {a: {cp: (num(dict(risks[a]).get(i), 1) if a != "control" or cp == "T0" else nm("T0 only"))
                 for i, (cp, _) in enumerate(xs)} for a in arms}
    return (f'<figure class="lp-chart" id="{fid}">'
            + line_chart("learning-risks", f"{MODEL}: risks found, % (higher is better)", "%", xs, lines)
            + legend(arms, ("control",)) + chart_table("risks", "Risks found (%) on the 200 evaluation "
                                                       "positions: means over each arm's finished series; "
                                                       "before game 1 is one shared run", xs, R, cells)
            + f'<p class="table-note">{arm_name("control")} is tested before game 1 only (the shared run): its line '
              'is drawn flat and dashed at that value.</p></figure>')


def results_charts(L) -> str:
    """The two charts of the Results section (Ümit #2925 item 2), each with its numbers table, from the data file's
    validated projection only and empty until the first finished series: (a) risks found on the 200 evaluation
    positions before game 1 (T0), after game 5 and after game 10, one line per arm, control a dashed flat line at its
    T0 value; (b) the error rate of each game 1-10, averaged over each arm's finished series. No lift or verdict."""
    R = L["results"]
    if not R or not R["series_total_done"]:
        return (f'<p class="lp-run-line">{esc(RUN_LINE)}</p><p class="note"><strong>No finished series yet.</strong> '
                'Two charts appear here with the first finished series: risks found on the evaluation set before '
                'game 1, after game 5 and after game 10, and the error rate of each game, one line per arm.</p>')
    arms = list(R["table"])
    out = [f'<p class="lp-run-line" id="learning-run-line">{esc(RUN_LINE)}</p>'] + (
        [f] if (f := risks_figure(R)) else [])
    games = games_points(R)
    gx = [(str(g), str(g)) for g in range(1, V.G + 1)]
    if any(games.values()):
        lines = [(a, games[a], games[a], False) for a in arms]
        cells = {a: {k: num(dict(games[a]).get(int(k) - 1), 1) for k, _ in gx} for a in arms}
        out.append('<figure class="lp-chart" id="learning-chart-games">'
                   + line_chart("learning-games", f"{MODEL}: error rate per game (PR, lower is better)", "", gx, lines,
                                "Game")
                   + legend(arms) + chart_table("games", "Error rate (PR) of game 1 to 10, averaged over each arm's "
                                                "finished series", [(k, f"Game {k}") for k, _ in gx], R, cells)
                   + "</figure>")
    note = ("" if R["complete"] else '<p class="table-note">Numbers so far: the verdict and the learning lift are '
                                     'shown only when every planned series of every arm is done.</p>')
    return out[0] + '<div class="lp-charts">' + "".join(out[1:]) + "</div>" + note


def section_id(title: str) -> str:
    return "plan-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def budget(L) -> str:
    """The budget arm at every point (plan section 11, Zeki #2577): after each game of each finished series, the whole
    games its context included and dropped and the tokens used against the lessons arm's count; the plan's fixed reading
    of an empty context beside it."""
    reading = (f'<div class="tab-rule">{spec_markdown(L["plan"]["budget_reading"]["markdown"])}<p class="table-note">'
               f'Plan section {esc(L["plan"]["budget_reading"]["section"])}, as pre-registered.</p></div>')
    R = L["results"]
    empty = (R or {}).get("budget_empty_points", {}).get("budget")
    out = ([f'<p class="note">Points where the {arm_name("budget")} arm\'s context was empty: {count(empty)}.</p>']
           if empty is not None else [])
    for b in L["budget"]:
        rows = [f'<tr><th scope="row">{count(p["after_game"])}</th>'
                f'<td>{esc(", ".join(str(g) for g in p["games_shown"])) or nm("none: empty")}</td>'
                f'<td class="num">{count(p["games_dropped"])}</td>'
                f'<td class="num">{count(p["tokens"])} / {num(p["budget_tokens"], 0)}</td></tr>' for p in b["points"]]
        out.append(P.SWIPE + P.table(["After game", "Games included", "Games dropped",
                                      f"Tokens used / {arm_name('lessons')} arm's tokens"], rows,
                                     f'{arm_name("budget")}, series {esc(str(b["series"]))}', cls="board list"))
    if not L["budget"]:
        out.append(f'<p class="note">No finished {arm_name("budget")} series yet: its points appear here, after every '
                   'game, as each series finishes.</p>')
    return "".join(out) + reading


def body(L) -> str:
    plan = L["plan"]
    prereg = L.get("preregistration_only")
    parts = [] if prereg else [
        ("learning-results", "Results", results_charts(L)),
        ("learning-verdict-section", "Verdict and learning lift", verdict(L))]
    # Exploratory, after the results: right after the verdict, in a visually separate card (bg.css .lp-explore).
    parts += [("learning-explore", "Exploratory, after the results", explore(L))] if L.get("explore") else []
    parts += [] if prereg else [
        ("learning-tab", f"{P.TAB_LEARNING}: arms, not models", tab_card(L)),
        ("learning-status", "Status and progress", progress(L)),
        ("learning-numbers", "All numbers", results(L)),
        ("learning-budget", f"{ARM_LABEL['budget']}: what its context held", budget(L)),
        ("learning-lessons", "Lessons the model wrote", lessons(L))]
    parts += [("learning-prompt", "Lesson prompt", prompt(L))]
    parts += [(section_id(s["title"]), s["title"], spec_markdown(s["markdown"])) for s in plan["sections"]]
    toc = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t, _ in parts)
    withheld = (f'<p class="note">{count(L["redacted"])} private address(es) in the plan are withheld here.</p>'
                if L["redacted"] else "")
    plan_status = f'<div class="note">{spec_markdown(plan["status"])}</div>' if plan["status"] else ""
    label = status_label(L)
    intro = ("The pre-registered plan and lesson prompt. No results or lessons are published on this page yet: they "
             "are not read by the build." if prereg else
             "The pre-registered plan, the lesson prompt and the results as they come in.")
    head = (f'<header class="card hero page-head"><p class="eyebrow">{label}</p><h1>{esc(title(L))}</h1>'
            + ("" if prereg else status_line(L))
            + f'<p class="intro"><strong>{esc(plan["commitment"])}</strong></p>'
            f'<p class="intro">{intro} Data: '
            f'<a href="../{DATA}">learning-pilot.json</a>.</p>{plan_status}'
            f'<p class="small">Plan: {esc(plan["file"])}, sha256 <code>{plan["sha256"]}</code></p>{withheld}</header>')
    return "\n".join([head, f'<nav class="toc card" aria-label="On this page"><ul>{toc}</ul></nav>']
                     + [f'<section class="card{" lp-explore" if i == "learning-explore" else ""}" id="{i}">'
                        f'<h2>{esc(t)}</h2>{h}</section>' for i, t, h in parts])


def site_state(L) -> dict:
    """What pages.layout needs: the footer's version line names this page's sources and the update time."""
    R = L["results"]
    t = datetime.fromisoformat(R["updated_at"]) if R else datetime.now(timezone.utc)
    return dict(hash=L["source_sha256"][:12], as_of=t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                image=None, description="", leagues=[])


def render(out: Path, L: dict) -> Path:
    S = site_state(L)
    page = out / PATH / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(P.layout(S, site_base(), PATH, title(L), body(L), description=DESCRIPTION))
    (out / DATA).parent.mkdir(parents=True, exist_ok=True)
    (out / DATA).write_text(json.dumps(L, indent=1, ensure_ascii=False))
    return page


# --- Checks -------------------------------------------------------------------------------------------------

def overlay(site: Path, out: Path, tmp: Path) -> None:
    """tmp = the built site with the output's files laid over it: the site's entries as symlinks (read-only), a real
    directory wherever an output file goes."""
    for f in (p for p in out.rglob("*") if p.is_file()):
        rel = f.relative_to(out)
        for i in range(len(rel.parts) - 1):
            d = tmp.joinpath(*rel.parts[:i + 1])
            if d.is_symlink() or not d.exists():
                if d.is_symlink():
                    d.unlink()
                d.mkdir()
                src = site.joinpath(*rel.parts[:i + 1])
                for e in src.iterdir() if src.is_dir() else []:
                    (d / e.name).symlink_to(e)
        dest = tmp / rel
        if dest.is_symlink():
            dest.unlink()
        shutil.copy2(f, dest)
    for e in site.iterdir():
        if not (tmp / e.name).exists() and not (tmp / e.name).is_symlink():
            (tmp / e.name).symlink_to(e)


def check(out: Path, site: Path, L: dict, test_set: Path | None = None) -> list[str]:
    import checks
    S = site_state(L)
    page = out / PATH / "index.html"
    rel = page.relative_to(out)
    tree = checks.Tree()
    tree.feed(checks.without_suite_bar(page.read_text()))
    bad = checks.check_numbers(rel, tree.root, checks.allowed_numbers(out, S))
    bad += checks.check_mixing(rel, tree.root, S)
    with tempfile.TemporaryDirectory(prefix="learning-check-") as t:
        tmp = Path(t)
        overlay(site, out, tmp)
        bad += [f.replace(str(tmp / rel), str(rel)) for f in checks.check_links(tmp / rel, tree.root, tmp)]
    for p in (p for p in out.rglob("*") if p.is_file()):
        m = checks.scan_file(p)
        if m:
            bad.append(f"{p.relative_to(out)}: banned string {m.group(0)!r}")
    return bad + checks.check_learning(out, test_set or TEST_SET)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="output directory (default: a new temporary directory)")
    ap.add_argument("--plan", default=str(PLAN))
    ap.add_argument("--src", default=str(Path("~/.local/state/bg-site").expanduser() / SOURCE),
                    help="the pilot's files in snapshot.py's STATE/learning layout; missing or empty: no results yet")
    ap.add_argument("--check", metavar="SITE", help="run checks.py's page checks, links resolved against SITE")
    ap.add_argument("--test-set", default=str(TEST_SET),
                    help="the private evaluation set: its hash for the results' validation, its positions for the check")
    ap.add_argument("--with-results", action="store_true",
                    help="review renders only: read results and lessons although PREREGISTRATION_ONLY is on")
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(tempfile.mkdtemp(prefix="learning-page-"))
    try:
        L = data(Path(a.plan), Path(a.src), Path(a.test_set), preregistration_only=False if a.with_results else None)
    except TestSetRequired as e:
        print(f"build failed: {e}", file=sys.stderr)
        sys.exit(2)
    if L["redacted"]:
        print(f"warning: {L['redacted']} private address(es) in the plan withheld", file=sys.stderr)
    if L["validation"] and L["validation"]["problems"]:
        print("validation: " + "; ".join(L["validation"]["problems"]), file=sys.stderr)
    print(render(out, L))
    if a.check:
        bad = check(out, Path(a.check), L, Path(a.test_set))
        for b in bad:
            print(b)
        print(f"checks: {len(bad)} failure(s)")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
