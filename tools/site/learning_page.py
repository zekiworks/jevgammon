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
    0 / planned. Numbers per arm x test round and progress appear as series finish; the learning lift and the signal
    rule's result only once "complete" is true (plan §9);
  - runs/lessons/sNN/aggregate.json and lessons-gKK.txt: every lesson the model wrote, next to its game (series, game,
    result from the series aggregate's games), for finished series only;
  - lessons_system.txt and lessons_user.txt, the lesson prompt, and its sha256: one hash over the system file's bytes
    immediately followed by the user file's bytes; when the plan states a 64-hex hash, the render fails unless the
    files hash to it.

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
PREREGISTRATION_ONLY = True
COMMITMENT = "Results will be published whichever way they go, including no lift."
PLAN = ROOT / "mailbox/Learning pilot - plan 2026-11-07.md"
# The pilot's files as snapshot.py copies them (STATE/learning): the build's only source besides the plan.
SOURCE = "learning"
DESCRIPTION = ("The learning pilot of the backgammon benchmark (preliminary, running): does a model play better after "
               "seeing its own earlier games? The pre-registered plan, the lesson prompt and the results as they come in.")
# Ids of the blocks that only a complete results file may carry (checks.check_learning): the lift, the signal rule's
# result and the Learning tab's leaders.
COMPLETE_ONLY_IDS = ("learning-lift", "learning-signal", "learning-leaders")
COMPLETE_ONLY_KEYS = ("learning_lift", "signal", "paired_series")
# The plan's bullet that fixes the Learning tab's order (section 9, amended before any model call, 09bcbc4).
TAB_ORDER = "Learning tab order"
# The plan's fixed reading of an empty budget context (section 11, Zeki #2577), shown with the budget arm's points.
BUDGET_READING = "Interpretation, fixed now"
# The pilot's evaluation set: private, never published; read at build time only for its hash (learning_validate) and
# for checks.check_learning (no evaluation position on the page).
TEST_SET = ROOT / "workspace/learning-pilot/test_set.json"
CHECKPOINTS = ("T0", "T5", "T10")
CHECKPOINT_LABEL = {"T0": "Before game 1", "T5": "After game 5", "T10": "After game 10"}
# The chart's measures (the evaluation set, per arm and checkpoint): key, label, unit.
CHART_MEASURES = [("error_rate", "Error rate (PR), lower is better", ""),
                  ("risks_found", "Risks found, higher is better", "%")]
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
RESULT_LABELS = {"lift": "Learning lift", "lift_ci": "95% interval", "vs_control": "Minus control's lift",
                 "vs_control_ci": "95% interval (minus control)", "per_arm": "Learning lift",
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
    out = dict(updated_at=pub["updated_at"], planned_series_per_arm=pub["planned_series_per_arm"],
               series_done=pub["series_done"], complete=pub["complete"], t0_done=pub["t0_done"],
               table={arm: {cp: pick(by_cp.get(cp), keys) for cp in CHECKPOINTS if cp in by_cp}
                      for arm, by_cp in pub["table"].items()},
               series_total_done=pub["series_total_done"], series_total_planned=pub["series_total_planned"],
               series_finished=pub["series_finished"],
               games={arm: pick(g, [k for k, *_ in GAME_METRICS]) for arm, g in pub["games"].items()},
               budget_empty_points=pub["budget_empty_points"], provenance=pub["provenance"])
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


def title(L) -> str:
    """The page title and heading follow the validated status, like the top label."""
    if L.get("preregistration_only"):
        return TITLE_PREREG
    return TITLE_COMPLETE if is_complete(L) else TITLE


def status_label(L) -> str:
    """The page's top label, from the validated status: "Complete" only when learning_validate accepts complete. The
    Experiments page's card shows the same label."""
    return "Pre-registration" if L.get("preregistration_only") else "Complete" if is_complete(L) else "Preliminary · running"


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
        return none | dict(validation=validation)
    lessons = []
    for s, g, f, game in v["lessons"]:
        text = f.read_text().strip()
        if text:
            lessons.append(dict(series=s, text=text, **{k: game.get(k) for k in GAME_KEYS} | {"game": g}))
    budget = [dict(series=s, points=[pick(p, ("after_game", "games_shown", "games_dropped", "tokens",
                                              "budget_tokens")) for p in points]) for s, points in v["budget"]]
    return dict(results=shown_results(v["public"]), lessons=lessons, budget=budget, validation=validation)


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


def progress(L) -> str:
    R = L["results"]
    if R is None:
        return validation_note(L) or ('<p class="note"><strong>No results yet.</strong></p><p>Progress: 0 / planned '
                                      'series per arm (the planned count appears with the first results file).</p>')
    planned = R["planned_series_per_arm"]
    rows = [f'<tr><th scope="row">{esc(a)}</th><td class="num">{count(len(s))} / {count(planned)}</td></tr>'
            for a, s in R["series_finished"].items()]
    t0 = (f'<p class="note">Shared T0 test (before any context): {"done" if R["t0_done"] else "not yet done"}.</p>'
          if "t0_done" in R else "")
    state = "All planned series are done." if R["complete"] else "Running: not all planned series are done."
    return (f'<p class="note">{status_badge("Preliminary")} {esc(state)} Updated {esc(R["updated_at"])}.</p>{t0}'
            + validation_note(L) + P.table(["Arm", "Series finished / planned"], rows, "Progress per arm"))


def results_table(R) -> str:
    rows = []
    t0s = [by_cp.get("T0") for by_cp in R["table"].values()]
    shared = all(t and t.get("shared") for t in t0s)
    for i, (arm, by_cp) in enumerate(R["table"].items()):
        for cp in CHECKPOINTS:
            if cp not in by_cp or (shared and cp == "T0" and i):
                continue
            row = by_cp[cp]
            label = "All arms (shared)" if shared and cp == "T0" else arm
            cells = ("".join(f'<td class="num">{num(row.get(k), d, u)}</td>' for k, _, d, u in METRICS)
                     if row else f'<td colspan="{len(METRICS)}">{nm("Not yet run")}</td>')
            rows.append(f'<tr><th scope="row">{esc(label)}</th><td>{cp}</td>{cells}</tr>')
    return P.SWIPE + P.table(["Arm", "Test"] + [h for _, h, *_ in METRICS], rows,
                             "The evaluation set per arm and test round: means over the arm's finished series",
                             cls="board list")


def games_table(R) -> str:
    rows = [f'<tr><th scope="row">{esc(arm)}</th>'
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
    rows = [f'<tr><th scope="row">{esc(a)}</th>' + "".join(f'<td class="num">{flat(v.get(c))}</td>' for c in cols)
            + "</tr>" for a, v in d.items()]
    head = ["Arm"] + [esc(RESULT_LABELS.get(c, c.replace("_", " "))) for c in cols]
    return P.SWIPE + P.table(head, rows, esc(caption), cls="board list")


def results(L) -> str:
    R = L["results"]
    if R is None:
        if L["validation"]:
            return '<p class="note"><strong>Results file not accepted:</strong> see Status and progress.</p>'
        return '<p class="note"><strong>No results yet.</strong> Numbers appear here as each series finishes.</p>'
    out = [results_table(R)]
    if R.get("games"):
        out.append(games_table(R))
    out.append(f'<p class="table-note">{esc(COST_NOTE)}</p>')
    if not R["complete"]:
        out.append('<p class="note">The learning lift and any verdict are shown only when every planned series of '
                   'every arm is done.</p>')
        return "".join(out)
    arms = list(R["table"])
    if "learning_lift" in R:
        out.append('<div id="learning-lift"><h3>Learning lift</h3>'
                   + arm_table(R["learning_lift"], arms, "Learning lift per arm (definition: the plan's Metrics)")
                   + "</div>")
    if "signal" in R:
        out.append('<div id="learning-signal"><h3>Signal rule</h3>'
                   + arm_table(R["signal"], arms, "Signal rule per arm (definition: the plan's Signal rule)")
                   + "</div>")
    return "".join(out)


def lessons(L) -> str:
    if not L["lessons"]:
        return '<p class="note">No lessons yet: they appear with each finished series of the lessons arm.</p>'
    out = []
    for x in L["lessons"]:
        res = (f'{"won" if x["won"] else "lost"} {count(x["points"])} point{"s" if x["points"] != 1 else ""}'
               f' ({esc(x["result"])})' if x["won"] is not None else nm(NA))
        out.append(f'<li><p class="small">Series {esc(str(x["series"]))}, game {esc(str(x["game"]))}: {res}</p>'
                   f'<pre class="citation">{esc(x["text"])}</pre></li>')
    return f'<ul class="notes">{"".join(out)}</ul>'


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
        items = "".join(f'<li><strong>{esc(a)}</strong>: signal rule {flat((sig.get(a) or {}).get("signal"))}; '
                        f'learning lift minus control\'s {flat((lift.get(a) or {}).get("vs_control"))}</li>'
                        for a in leader_order(R))
        block = (f'<div id="learning-leaders"><h3>Arms in order</h3><ol class="leaders-list">{items}</ol>'
                 '<p class="table-note">control: the reference, not ranked.</p></div>')
    else:
        state = (("Results file not accepted: see Status and progress." if L["validation"] else
                  "Not started: no series has finished.") if R is None else
                 f'Running, {count(R["series_total_done"])} of {count(R["series_total_planned"])} series.')
        rows = []
        for arm, by_cp in (R["table"].items() if R else []):
            cp, row = latest(by_cp)
            g = (R.get("games") or {}).get(arm) or {}
            rows.append(f'<tr><th scope="row">{esc(arm)}</th>'
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


def chart(L) -> str:
    """Error rate and risks found on the evaluation set by checkpoint (before game 1, after game 5, after game 10), one
    line per arm, filled as series finish (Ümit #2564, after 'The village learns, or doesn't'). Values from the data
    file only; no lift or verdict line."""
    R = L["results"]
    arms = list(R["table"]) if R else []
    vals = [(arm, cp, k, row[k]) for arm in arms for cp in CHECKPOINTS for k, *_ in CHART_MEASURES
            if (row := R["table"][arm].get(cp)) and row.get(k) is not None]
    if not vals:
        return ('<p class="note"><strong>No results yet.</strong> The chart fills in as series finish: error rate and '
                'risks found before game 1, after game 5 and after game 10, one line per arm.</p>')
    # One small chart per measure, side by side on wide screens and stacked on phones (bg.css .lp-charts), so each
    # keeps readable text at 390 px.
    W, H, L0, R0, T, B = 360, 260, 46, 46, 28, 40  # R0 = L0: the last checkpoint label ("After game 10") fits
    pw = W - L0 - R0
    svgs = []
    for key, label, unit in CHART_MEASURES:
        ys = [v for _, _, k, v in vals if k == key]
        if not ys:
            continue
        parts = []
        lo, hi = min(ys), max(ys)
        step = nice_step(hi - lo)
        pad = step if lo == hi else 0
        lo, hi = math.floor(lo / step) * step - pad, math.ceil(hi / step) * step + pad
        x0 = L0
        x = lambda c, x0=x0: x0 + pw * CHECKPOINTS.index(c) / (len(CHECKPOINTS) - 1)  # noqa: E731
        y = lambda v, lo=lo, hi=hi: H - B - (H - B - T) * (v - lo) / ((hi - lo) or 1)  # noqa: E731
        parts.append(f'<text x="{x0:.1f}" y="{T - 12}" class="lp-title">{esc(label)}</text>')
        v = lo
        while v <= hi + step / 2:
            parts.append(f'<line class="grid" x1="{x0:.1f}" x2="{x0 + pw:.1f}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                         f'<text class="muted" x="{x0 - 6:.1f}" y="{y(v) + 4:.1f}" text-anchor="end">{v:g}{unit}</text>')
            v += step
        for c in CHECKPOINTS:
            parts.append(f'<text class="muted" x="{x(c):.1f}" y="{H - B + 16}" text-anchor="middle">'
                         f'{esc(CHECKPOINT_LABEL[c])}</text>')
        for arm in arms:
            pts = [(c, val) for a, c, k, val in vals if a == arm and k == key]
            if len(pts) > 1:
                d = " ".join(f"{x(c):.1f},{y(val):.1f}" for c, val in pts)
                parts.append(f'<polyline class="lp-line lp-{esc(arm)}" points="{d}"/>')
            for c, val in pts:
                parts.append(f'<circle class="lp-dot lp-{esc(arm)}" cx="{x(c):.1f}" cy="{y(val):.1f}" r="4">'
                             f'<title>{esc(arm)}, {esc(CHECKPOINT_LABEL[c])}: {fmt(val, 1)}{unit}</title></circle>')
        svgs.append(f'<svg class="chart-svg" data-chart="learning-{esc(key)}" viewBox="0 0 {W} {H}" role="img" '
                    f'aria-label="{esc(label)}: the evaluation set before game 1, after game 5 and after game 10, one '
                    f'line per arm">' + "".join(parts) + "</svg>")
    legend = "".join(f'<span><i class="swatch lp-swatch lp-{esc(a)}"></i>{esc(a)}</span>' for a in arms)
    return (f'<figure class="lp-chart"><div class="lp-charts">' + "".join(svgs) + "</div>"
            f'<p class="chart-legend">{legend}</p><p class="table-note">Means over each arm\'s finished series. Before '
            'game 1 is one shared run with no context; control has no later test rounds. No lift or verdict is drawn '
            'until every planned series is done.</p></figure>')


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
    out = ([f'<p class="note">Points where the budget arm\'s context was empty: {count(empty)}.</p>']
           if empty is not None else [])
    for b in L["budget"]:
        rows = [f'<tr><th scope="row">{count(p["after_game"])}</th>'
                f'<td>{esc(", ".join(str(g) for g in p["games_shown"])) or nm("none: empty")}</td>'
                f'<td class="num">{count(p["games_dropped"])}</td>'
                f'<td class="num">{count(p["tokens"])} / {num(p["budget_tokens"], 0)}</td></tr>' for p in b["points"]]
        out.append(P.SWIPE + P.table(["After game", "Games included", "Games dropped",
                                      "Tokens used / lessons arm's tokens"], rows,
                                     f'Budget arm, series {esc(str(b["series"]))}', cls="board list"))
    if not L["budget"]:
        out.append('<p class="note">No finished budget series yet: its points appear here, after every game, as each '
                   'series finishes.</p>')
    return "".join(out) + reading


def body(L) -> str:
    plan = L["plan"]
    prereg = L.get("preregistration_only")
    parts = [] if prereg else [
        ("learning-tab", f"{P.TAB_LEARNING}: arms, not models", tab_card(L)),
        ("learning-chart", "Before and after: the evaluation set by checkpoint", chart(L)),
        ("learning-status", "Status and progress", progress(L)), ("learning-results", "Results", results(L)),
        ("learning-budget", "Budget arm: what its context held", budget(L)),
        ("learning-lessons", "Lessons the model wrote", lessons(L))]
    parts += [("learning-prompt", "Lesson prompt", prompt(L))]
    parts += [(section_id(s["title"]), s["title"], spec_markdown(s["markdown"])) for s in plan["sections"]]
    toc = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t, _ in parts)
    withheld = (f'<p class="note">{count(L["redacted"])} private address(es) in the plan are withheld here.</p>'
                if L["redacted"] else "")
    status = f'<div class="note">{spec_markdown(plan["status"])}</div>' if plan["status"] else ""
    label = status_label(L)
    intro = ("The pre-registered plan and lesson prompt. No results or lessons are published on this page yet: they "
             "are not read by the build." if prereg else
             "The pre-registered plan, the lesson prompt and the results as they come in.")
    head = (f'<header class="card hero page-head"><p class="eyebrow">{label}</p><h1>{esc(title(L))}</h1>'
            f'<p class="intro"><strong>{esc(plan["commitment"])}</strong></p>'
            f'<p class="intro">{intro} Data: '
            f'<a href="../{DATA}">learning-pilot.json</a>.</p>{status}'
            f'<p class="small">Plan: {esc(plan["file"])}, sha256 <code>{plan["sha256"]}</code></p>{withheld}</header>')
    return "\n".join([head, f'<nav class="toc card" aria-label="On this page"><ul>{toc}</ul></nav>']
                     + [f'<section class="card" id="{i}"><h2>{esc(t)}</h2>{h}</section>' for i, t, h in parts])


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
