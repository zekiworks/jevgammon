#!/usr/bin/env python3
"""Did they improve? The pre-registered experiment's page (improve/) and its data file (data/v3/improve.json).

    python3 tools/site/improve_page.py [--out DIR] [--plan MD] [--src DIR] [--check SITE] [--with-results]

build.py renders the page with the site (S["improve"] = from_state(STATE)); this command renders the page alone, for
review: OUT/improve/index.html and OUT/data/v3/improve.json (OUT defaults to a new temporary directory, never the live
site). It follows the learning page (learning_page.py) in every convention. Sources, read at render time:

- the plan (--plan, default mailbox/Did they improve - plan 2026-11-08.md, committed): the single source of the rule,
  the model list (section 3's table: setup, maker, setting, route, status), the routes and settings, the money rules
  and the commitment line. The rule (section 2) is shown first, verbatim; every other section follows as written.
- the experiment's files as snapshot.py copies them to STATE/improve (--src, default ~/.local/state/bg-site/improve):
  - prompt/lessons_system.txt and lessons_user.txt: the lesson prompt the plan names (the learning pilot's files);
    the render fails unless they hash to the plan's stated sha256 (one hash over the system file's bytes immediately
    followed by the user file's);
  - harness-prompt/: the harness's own copy of the prompt (workspace/improve/out/prompt), checked by the validator;
  - improve.json (workspace/improve/out/improve.json), absent before the first model call. Outside
    pre-registration-only mode (PREREGISTRATION_ONLY) read whole and shown only after improve_validate accepts it;
    refused, the page is the pre-registration view with a "data refused" note naming the failed fields (names taken
    from the file withheld; the full text on stderr only). In pre-registration-only mode only its progress fields are
    read (improve_validate.status_view), for the results table at the top (Ümit #3219, #3710): per plan chat model its
    status (with a fixed reason) and series done of 5; never an outcome number. The results table also lists the
    planned rows of content/improve_planned.json (status only, no numbers).

The producer writes no before, after or verdict: improve_validate computes them (plan sections 2, 6 and 7). A model
gets Yes or No only past the verdict gate; until then its row shows live numbers and "running, n of 5 series", or
"incomplete"/"stopped" with the reason. Test positions are never published: checks.check_improve scans the page and
its data file for every test position (id, board key, board), as the learning page's check does.

--check SITE runs checks.py's page checks on the output (numbers trace, links and ids against the built site SITE laid
under the output, the private-strings scan, checks.check_improve).
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))

from common import NA, ROOT, count, esc, fmt, nm  # noqa: E402

import home as H  # noqa: E402
import improve_validate as V  # noqa: E402
import learning_page as LP  # noqa: E402
import pages as P  # noqa: E402
from method import _inline, spec_markdown  # noqa: E402

PATH = "improve/"
DATA = "data/v3/improve.json"
TITLE = "Did they improve?"
TITLE_PREREG = "Did they improve? (pre-registered)"
# Pre-registration only: when True the build never reads improve.json, and the page shows the plan's rule, model
# list, lesson prompt, settings and money rules only (as the learning page's PREREGISTRATION_ONLY).
# Switched off (results mode) at Ümit/Zeki's request (#3369), per the plan's publishing rule: numbers update as each
# model finishes; no verdict text for a model until all its 5 series are done (improve_validate's verdict gate).
PREREGISTRATION_ONLY = False
COMMITMENT = "Results will be published whichever way they go."
PLAN = ROOT / "mailbox/Did they improve - plan 2026-11-08.md"
SOURCE = "improve"
# The results table's planned rows (models and setups not yet run; status only, no numbers), outside the plan.
PLANNED = SITE / "content/improve_planned.json"
DESCRIPTION = ("Did they improve? Each chat model on the leaderboard writes its own lessons over 10 games against GNUbg "
               "weak, then takes the risk test again. The pre-registered rule, model list and lesson prompt.")
# Part 3, the decision models (Ümit/Zeki, #3790): the addendum to the pre-registration, committed at ADDENDUM_COMMIT and
# bound by sha256 (the harness refuses any other file). The render fails unless the file hashes to ADDENDUM_SHA256. Its
# sections ADDENDUM_SECTIONS are shown as written in their own section, below the results table and above the plan.
ADDENDUM = ROOT / "mailbox/Did they improve - decision models - addendum 2026-11-09.md"
ADDENDUM_SHA256 = "b370f4dc9660a618aece4586b8c8f5259688372fab580305b4454aaa2d71a967"
ADDENDUM_COMMIT = "02d6145b5be01c67075511137cfee8c7ee22ad2c"
ADDENDUM_URL = ("https://github.com/zekiworks/jevgammon/blob/" + ADDENDUM_COMMIT
                + "/mailbox/Did%20they%20improve%20-%20decision%20models%20-%20addendum%202026-11-09.md?plain=1")
ADDENDUM_SECTIONS = ("1.", "2.", "3.", "4.", "7.", "9.")
# The hashes the plan states (sections 5): the lesson prompt and the test set. The render fails unless the plan states
# them and the files present hash to them.
PROMPT_SHA256 = "d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e"
TEST_SET_SHA256 = "6c92e7416745125ca3ea09c9e41e450a52716f8ad018772278b07f992f7318e6"
TEST_SET = LP.TEST_SET
RULE_SECTION = "2."
MODELS_SECTION = "3."
SETTINGS_SECTION = "4."
# Phrases the page must carry (checks.check_improve), each from the plan.
REQUIRED = ("operational threshold, not a statistical test", "not tested: cannot write lessons",
            "pilot (different design)", "not comparable (different design)", "count nowhere",
            "Provider-side load is not observable", "$110")


# --- Sources ------------------------------------------------------------------------------------------------

def section(sections: list, prefix: str) -> dict:
    s = next((s for s in sections if s["title"].startswith(prefix)), None)
    if s is None:
        raise SystemExit(f"the plan has no section {prefix}")
    return s


def paragraph(md: str, start: str) -> str:
    """The plan paragraph (one line) starting with `start`, as written."""
    line = next((x for x in md.splitlines() if x.startswith(start)), None)
    if line is None:
        raise SystemExit(f"the plan has no paragraph starting {start!r}")
    return line


def block(md: str, start: str) -> str:
    """The plan paragraph starting with `start` and the bullets right under it, as written."""
    lines = md.splitlines()
    i = next((i for i, x in enumerate(lines) if x.startswith(start)), None)
    if i is None:
        raise SystemExit(f"the plan has no block starting {start!r}")
    j = i + 1
    while j < len(lines) and lines[j].startswith("- "):
        j += 1
    return "\n".join(lines[i:j])


def sentence(text: str, phrase: str) -> str:
    """The plan sentence (or list item) holding `phrase`, as written (Markdown marks kept)."""
    for line in text.splitlines():
        if phrase in line.replace("**", ""):
            line = re.sub(r"^\s*(- |\d+\. )", "", line)
            for s in re.split(r"(?<=[.;])\s+(?=[A-Z*])", line):
                if phrase in s.replace("**", ""):
                    return s.strip()
    raise SystemExit(f"the plan has no sentence with {phrase!r}")


def plan_models(md: str) -> list:
    """Section 3's table of chat models: one dict per row, every cell as written; the setup name is the cell's text up
    to its first closing parenthesis (the v3.db setup); the rest of the cell (after ' — ', bold marks dropped) is the
    row's label; billed exactly on an OpenRouter route (plan section 9)."""
    rows = []
    for line in md.splitlines():
        if not re.match(r"\|\s*\d+\s*\|", line):
            continue
        n, model, maker, setting, route, status = [c.strip() for c in line.strip().strip("|").split("|")]
        setup = re.match(r"(.*?\))", model).group(1)
        rest = model[len(setup):]
        label = rest.split(" — ", 1)[1].replace("**", "").strip() if " — " in rest else ""
        late = rest.startswith(", late entry")
        m = re.match(r"\*\*([^*]+)\*\*\s*—\s*(.*)", route)
        rows.append(dict(n=int(n), setup=setup, label=label, late_entry=late, maker=maker, setting=setting,
                         route=m.group(1) if m else route, route_detail=m.group(2) if m else "",
                         billed="OpenRouter" in route, status=status, key=re.sub(r"[^a-z0-9.]+", "-", setup.lower())
                         .strip("-")))
    return rows


def pilot_row(md: str) -> dict:
    """The Gemma pilot row (section 3), as written, and its numbers for the table's cells."""
    text = block(md, '**The Gemma pilot row')
    m = re.search(r"Risks found ([\d.]+) → ([\d.]+) \(([+−-][\d.]+)\), right safety ([\d.]+) → ([\d.]+) "
                  r"\(([+−-][\d.]+)\), error rate ([\d.]+) → ([\d.]+)", text)
    if not m:
        raise SystemExit("the plan's Gemma pilot row has no numbers")
    f = [float(x.replace("−", "-")) for x in m.groups()]
    verdict = re.search(r"\*\*(not met|met)\*\*", text)
    setup = re.search(r"\*\*\s+([^,*]+?\([a-z]+\))", text)  # the setup named right after the bold label
    return dict(markdown=text, setup=setup.group(1) if setup else "Gemma 4 31B (off)",
                risks_found=f[0:3], right_safety=f[3:6], error_rate=f[6:8],
                own_verdict=verdict.group(1) if verdict else None)


# The page never names a host or a device (Main, via Improve): where the plan names our servers, their GPUs or a
# server-address key, the page's copy of the plan text says "our GPU" instead. Applied to the plan's text for the page
# only (the plan file is unchanged; its sha256 is the file's). Specific phrases first, then general ones; anything the
# site's private-strings rule would still withhold fails checks.check_improve (no "withheld" on the page).
HOST_REWRITES = [
    (r"bariton GPU \d+ by UUID `GPU-[0-9a-f-]+`", "our GPU"),
    (r"\(bariton [^)]*\)", "(our GPUs; not possible now)"),
    (r";? ?\bspark\d*\b is not used", ""),
    (r"; GPU set to that UUID", ""),
    (r"`base_url`", "the server address"),
    (r"`?GPU-[0-9a-f]{8}-[0-9a-f-]+`?", "our GPU"),
    (r"\bbariton(?:'s)? GPUs?(?: \d+)?", "our GPU"),
    (r"\b[Bb]ariton\b", "our GPU server"),
    (r"\bspark-?\d+\b", "our other server"),
]


def unhost(line: str) -> str:
    for pat, new in HOST_REWRITES:
        line = re.sub(pat, new, line)
    return line


def read_plan(path: Path) -> dict:
    text = path.read_text()
    if COMMITMENT not in text:
        raise SystemExit(f"{path}: the commitment line is missing: {COMMITMENT!r}")
    for h in (PROMPT_SHA256, TEST_SET_SHA256):
        if h not in text:
            raise SystemExit(f"{path}: the plan does not state {h}")
    title, sections, cur, redacted, intro = None, [], None, 0, []
    for raw in text.splitlines():
        line, n = LP.redact(unhost(raw))
        redacted += n
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        elif line.startswith("## "):
            cur = dict(title=line[3:].strip(), lines=[])
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
        else:
            intro.append(line)
    for s in sections:
        s["markdown"] = "\n".join(s.pop("lines")).strip()
    models_md = section(sections, MODELS_SECTION)["markdown"]
    settings_md = section(sections, SETTINGS_SECTION)["markdown"]
    seed = re.search(r'\*\*"([^"]+)"\*\*', settings_md)
    models = plan_models(models_md)
    if len(models) != 15:
        raise SystemExit(f"the plan's section 3 lists {len(models)} chat models, not 15")
    return dict(file=path.name, title=title, commitment=COMMITMENT,
                sha256=hashlib.sha256(text.encode()).hexdigest(), sections=sections, redacted=redacted,
                intro="\n".join(intro).strip(), models=models,
                decision_models=paragraph(models_md, "**Decision models"),
                cygnet=paragraph(models_md, "**Cygnet"), pilot=pilot_row(models_md),
                seed_line=seed.group(1) if seed else None,
                notes=[sentence(text, "count nowhere"), sentence(text, "Provider-side load is not observable")],
                prompt_sha256=PROMPT_SHA256, test_set_sha256=TEST_SET_SHA256)


def read_addendum(path: Path = ADDENDUM) -> dict:
    """The decision-model addendum: its sections ADDENDUM_SECTIONS as written (hosts rewritten as for the plan); the
    render fails unless the file hashes to ADDENDUM_SHA256, states the commitment line and needs no redaction."""
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != ADDENDUM_SHA256:
        raise SystemExit(f"{path}: sha256 {sha}, not the bound {ADDENDUM_SHA256}")
    text = raw.decode()
    if COMMITMENT not in text:
        raise SystemExit(f"{path}: the commitment line is missing: {COMMITMENT!r}")
    sections, cur = [], None
    for line in text.splitlines():
        line, n = LP.redact(unhost(line))
        if n:
            raise SystemExit(f"{path}: a private string in {line!r}")
        if line.startswith("## "):
            cur = dict(title=line[3:].strip(), lines=[])
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    shown = [dict(title=s["title"], markdown="\n".join(s["lines"]).strip()) for s in sections
             if s["title"].startswith(ADDENDUM_SECTIONS)]
    if len(shown) != len(ADDENDUM_SECTIONS):
        raise SystemExit(f"{path}: not every section of {ADDENDUM_SECTIONS} found")
    return dict(file=path.name, sha256=sha, commit=ADDENDUM_COMMIT, url=ADDENDUM_URL, commitment=COMMITMENT,
                sections=shown)


def prompt_sha(d: Path) -> str | None:
    files = [d / "lessons_system.txt", d / "lessons_user.txt"]
    if not all(f.exists() for f in files):
        return None
    return hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()


def read_prompt(src: Path) -> dict | None:
    """The lesson prompt the plan names (STATE/improve/prompt) and its hash; None when not in src yet."""
    d = src / "prompt"
    sha = prompt_sha(d)
    if sha is None:
        return None
    if sha != PROMPT_SHA256:
        raise SystemExit(f"lesson prompt sha256 {sha} is not the one the plan states ({PROMPT_SHA256})")
    return dict(system=(d / "lessons_system.txt").read_text(), user=(d / "lessons_user.txt").read_text(), sha256=sha)


def read_results(src: Path, plan: dict, test_set: Path) -> dict:
    """validation and results from src/improve.json, after improve_validate. With a results file present, the test set
    must be present, readable and the plan's, else the build fails (learning_page.TestSetRequired): the leakage checks
    cannot run without it."""
    import checks
    path = src / "improve.json"
    if not path.exists():
        return dict(results=None, validation=None)
    test_sha = LP.require_test_set(test_set, "an improve.json is present")
    if test_sha != TEST_SET_SHA256:
        raise LP.TestSetRequired(f"{test_set} hashes to {test_sha[:12]}…, not the plan's test set: the leakage check "
                                 "would test the wrong set")
    try:
        R = json.loads(path.read_text())
    except ValueError:
        return dict(results=None, validation=dict(accepted=False, problems=["improve.json is not JSON"]))
    leaks = checks._test_set_strings(test_set)
    v = V.validate(R, plan["sha256"], PROMPT_SHA256, TEST_SET_SHA256, prompt_sha(src / "harness-prompt"),
                   {m["setup"]: m for m in plan["models"]}, leaks)
    for p in v["private_problems"]:
        print(f"improve_validate (private): {p}", file=sys.stderr)
    return dict(results=v["public"], validation=dict(accepted=v["accepted"], problems=v["problems"]))


def read_progress(src: Path, plan: dict) -> dict:
    """Pre-registration-only builds: the "Models and status" table's data from src/improve.json, its progress fields
    only (improve_validate.status_view): {progress, progress_refused}; no outcome number, no free text is read."""
    path = src / "improve.json"
    if not path.exists():
        return dict(progress=None, progress_refused=None)
    try:
        R = json.loads(path.read_text())
    except ValueError:
        return dict(progress=None, progress_refused=["improve.json is not JSON"])
    v = V.status_view(R, {m["setup"]: m for m in plan["models"]})
    for p in v["private_problems"]:
        print(f"improve_validate status view (private): {p}", file=sys.stderr)
    return dict(progress=v["public"], progress_refused=None if v["accepted"] else v["problems"])


def progress_from_results(shown: dict) -> dict:
    R, v = shown["results"], shown["validation"]
    rows_ = (dict(updated_at=R["updated_at"], models=[dict(setup=m["setup"], **m["progress"]) for m in R["models"]])
             if R else None)
    return dict(progress=rows_, progress_refused=v["problems"] if v and not v["accepted"] else None)



def rows(L) -> list:
    """The table's rows: one per plan model, its validated data or None; sorted by the change in risks found (largest
    first), rows without a change after, in the plan's order (plan section 6)."""
    by = {m["setup"]: m for m in (L["results"] or {}).get("models", [])}
    out = [(pm, by.get(pm["setup"])) for pm in L["plan"]["models"]]
    ch = [x for x in out if x[1] and x[1]["change"]["risks_found"] is not None]
    rest = [x for x in out if x not in ch]
    return sorted(ch, key=lambda x: -x[1]["change"]["risks_found"]) + rest


def status(L) -> dict:
    """The page's status line, from the validated data only."""
    R = L["results"]
    ms = (R or {}).get("models", [])
    verdicts = sum(1 for m in ms if m["verdict"])
    running = sum(1 for m in ms if m["state"] == "running")
    paused = sum(1 for m in ms if m["state"] == "paused")
    stopped = sum(1 for m in ms if m["state"] in ("incomplete", "stopped"))
    total = len(L["plan"]["models"])
    if verdicts == total:
        phase = "done"
    elif not ms:
        phase = "not-started"
    else:
        phase = "running"
    line = (f"{verdicts} of {total} models with a verdict · {running} running · {paused} paused · {stopped} "
            "incomplete or stopped" if ms else "Not started")
    return dict(phase=phase, line=line, models=total, verdicts=verdicts, running=running, paused=paused,
                stopped=stopped,
                last_update=R["updated_at"] if R else None)


def read_planned(plan_setups: set, path: Path = PLANNED) -> list:
    """The results table's planned rows (content/improve_planned.json, Ümit/Zeki #3710): status only, no number; a
    file outside improve_validate.PLANNED fails the build."""
    doc = json.loads(path.read_text())
    bad = V.planned_problems(doc, plan_setups, P.PARAMS)
    if bad:
        raise SystemExit("content/improve_planned.json: " + "; ".join(bad))
    return doc["rows"]


def data(plan_path: Path, src: Path, test_set: Path = TEST_SET, preregistration_only: bool | None = None) -> dict:
    """The page's data from the plan and src (the STATE/improve layout). In pre-registration-only mode no test set is
    read and of the results file only its progress fields (read_progress)."""
    prereg = PREREGISTRATION_ONLY if preregistration_only is None else preregistration_only
    plan = read_plan(plan_path)
    prompt = read_prompt(src)
    shown = dict(results=None, validation=None) if prereg else read_results(src, plan, test_set)
    progress = read_progress(src, plan) if prereg else progress_from_results(shown)
    L = dict(version="v3", preregistration_only=prereg, plan={k: v for k, v in plan.items() if k != "redacted"},
             redacted=plan["redacted"], lesson_prompt=prompt, **shown, **progress,
             planned=read_planned({m["setup"] for m in plan["models"]}), addendum=read_addendum())
    if not prereg:
        L["status"] = status(L)
    L["source_sha256"] = hashlib.sha256(json.dumps(L, sort_keys=True).encode()).hexdigest()
    return L


def from_state(state: Path) -> dict:
    return data(PLAN, state / SOURCE)


# --- Page ---------------------------------------------------------------------------------------------------

def num(v, digits=1) -> str:
    return nm(NA) if v is None else fmt(v, digits)


def before_after(m, k) -> str:
    return f'{num(m["before"][k])} → {num(m["after"][k])}'


def label(pm) -> str:
    extra = (f'<br><span class="small">{esc(pm["label"])}</span>' if pm["label"] else "") + (
        '<br><span class="small">late entry</span>' if pm["late_entry"] else "")
    return extra


def route(pm) -> str:
    detail = (f'<details class="small"><summary>API setup</summary>{_inline(pm["route_detail"])}</details>'
              if pm["route_detail"] else "")
    return f'{_inline(pm["route"])}{detail}'


def answers(a) -> str:
    if a is None:
        return nm(NA)
    return (f'{count(a["valid"])} valid of {count(a["expected"])} ({count(a["tests"])} test'
            f'{"s" if a["tests"] != 1 else ""}): risk pays {count(a["risk_pays"])}, safety pays '
            f'{count(a["safety_pays"])}; {count(a["invalid"])} invalid, {count(a["failed"])} failed; answer rate '
            f'{fmt(a["answer_rate"], 1)}%')


def cost(pm, m) -> str:
    c = m["cost"]
    if pm["billed"]:
        rep = f' (OpenRouter reported ${fmt(c["reported_usd"], 2)})' if c["reported_usd"] is not None else ""
        return f'${fmt(c["billed_usd"], 2)} billed{rep}'
    if pm["route"].startswith("local"):
        return esc(LP.COST_NOTE)
    eq = (f'; API-list-price equivalent ${fmt(c["api_equivalent_usd"], 2)}' if c["api_equivalent_usd"] is not None
          else "; API-list-price equivalent not computed")
    return f'$0 billed (subscription quota){eq}'


def verdict_cell(m) -> str:
    if m is None:
        return ""
    if m["verdict"]:
        return f'<strong data-verdict="{"yes" if m["improved"] else "no"}">{esc(m["status"])}</strong>'
    return f'<span data-status="{esc(m["state"])}">{esc(m["status"])}</span>'


def model_row(pm, m, results: bool) -> str:
    name = (f'<a href="#lessons-{esc(pm["key"])}">{esc(pm["setup"])}</a>' if m else esc(pm["setup"]))
    head = (f'<tr data-setup="{esc(pm["setup"])}" data-key="{esc(pm["key"])}"'
            + (f' data-change="{m["change"]["risks_found"]}"' if m and m["change"]["risks_found"] is not None else "")
            + f'><th scope="row">{name}{label(pm)}</th><td>{esc(pm["maker"])}</td><td>{_inline(pm["setting"])}</td>'
            f'<td>{route(pm)}</td>')
    if not results:
        return head + f'<td>{_inline(pm["status"])}</td><td>{nm("no result yet")}</td></tr>'
    if m is None:
        return head + "".join("<td></td>" for _ in range(8)) + f'<td>{_inline(pm["status"])}</td></tr>'
    ch = m["change"]
    return head + (
        f'<td class="num" data-cell="rf">{before_after(m, "risks_found")}</td>'
        f'<td class="num" data-cell="rf-change">{fmt(ch["risks_found"], 1, signed=True) or nm(NA)}</td>'
        f'<td class="num" data-cell="range">{num(m["range"])}</td>'
        f'<td class="num" data-cell="threshold">{num(m["threshold"])}</td>'
        f'<td class="num" data-cell="rs">{before_after(m, "right_safety")} '
        f'({fmt(ch["right_safety"], 1, signed=True) or NA})</td>'
        f'<td class="num" data-cell="er">{before_after(m, "error_rate")}</td>'
        f'<td class="small" data-cell="answers"><strong>Before:</strong> {answers(m["answers_before"])}<br>'
        f'<strong>After:</strong> {answers(m["answers_after"])}</td>'
        f'<td class="small" data-cell="cost">{cost(pm, m)}</td>'
        f'<td data-cell="verdict">{verdict_cell(m)}</td></tr>')


def others(L) -> str:
    """The rows outside the rule: the decision models and Cygnet (not tested), and the Gemma pilot row with its own
    verdict and "not comparable (different design)" in this rule's column; every text as the plan writes it."""
    plan = L["plan"]
    pr = plan["pilot"]
    rf, rs, er = pr["risks_found"], pr["right_safety"], pr["error_rate"]
    pilot = (f'<tr data-row="pilot"><th scope="row">{esc(pr["setup"])}<br><span class="small">pilot (different '
             f'design)</span></th><td>Its own pre-registered verdict: <strong>{esc(pr["own_verdict"])}</strong>. Risks '
             f'found {fmt(rf[0], 1)} → {fmt(rf[1], 1)} ({fmt(rf[2], 1, signed=True)}), right safety {fmt(rs[0], 1)} → '
             f'{fmt(rs[1], 1)} ({fmt(rs[2], 1, signed=True)}), error rate {fmt(er[0], 1)} → {fmt(er[1], 1)}</td>'
             f'<td><strong>not comparable (different design)</strong></td></tr>')
    rows_ = [f'<tr data-row="decision"><th scope="row">Decision models</th><td>{_inline(plan["decision_models"])}'
             '</td><td>not tested: cannot write lessons</td></tr>',
             f'<tr data-row="cygnet"><th scope="row">Cygnet</th><td>{_inline(plan["cygnet"])}</td>'
             '<td>not tested</td></tr>', pilot]
    return (P.table(["Model", "As the plan states it", "This rule"], rows_, "Not tested, and the pilot row",
                    cls="board list improve-others")
            + f'<div class="tab-rule">{spec_markdown(pr["markdown"])}</div>')


def models_section(L) -> str:
    plan = L["plan"]
    results = not L["preregistration_only"] and L["results"] is not None
    if results:
        head = ["Model (v3.db setup)", "Maker", "Setting", "Route", "Risks found before → after", "Change",
                "Own range", "Threshold", "Right safety before → after (change)", "Error rate (PR) before → after",
                "Answers: denominators, invalid, answer rate", "Cost", "Improved?"]
        cap = (f'{count(len(plan["models"]))} chat models, sorted by the change in risks found (rows without a change '
               'after); tap a model for its lessons')
    else:
        head = ["Model (v3.db setup)", "Maker", "Setting", "Route", "Status in the plan (8 Nov)", "Improved?"]
        cap = f'{count(len(plan["models"]))} chat models (in scope), in the plan\'s order'
    body = P.SWIPE + P.table(head, [model_row(pm, m, results) for pm, m in rows(L)], esc(cap),
                             cls="board list improve-models")
    seed = (f'<p class="note" id="improve-seed"><strong>{esc(plan["seed_line"])}</strong></p>'
            if plan["seed_line"] else "")
    notes = "".join(f"<li>{_inline(n)}</li>" for n in plan["notes"])
    before = ('<p class="small">Before = the mean of the 3 empty runs; after = the mean of the 5 tests after game 10; '
              'shares over valid answers. Yes or No only once every run is complete (plan section 7).</p>'
              if results else "")
    return seed + before + body + f'<ul class="notes improve-notes">{notes}</ul>' + others(L)


def progress_status(p) -> str:
    return p["status"] + (f' ({p["reason"]})' if p["reason"] else "")


ARMS = (("notes", "notes"), ("worst_mistakes", "worst mistakes"))
ARM_LABEL = {"notes": "helper-written notes", "worst_mistakes": "worst mistakes"}


# Classes (Ümit #4217): the leaderboard's (P.model_class, P.class_label); a model the parameter file does not list, or
# one without a class: none (in the All view only).
def model_class(name: str | None) -> tuple[str, str]:
    """(the row's class key, '' for none; its class label after the name, '' for a model the file does not list)."""
    if name in P.PARAMS:
        return P.model_class(name) or "", f'<span class="hl-size">{esc(P.class_label(name))}</span>'
    return "", ""


# Each row's maker dot and details box (Ümit via Zeki #3803): the home leaderboard's (home.maker on the shared palette,
# story.box_html, bg.js headlineDetails). A row's model without a palette maker fails the build. Box lines without data
# are left out (never "n/a").


def board_links(S) -> dict:
    """{setup name or model name: the box's link line} of the leaderboard's rows (a model: its top row), relative to
    improve/."""
    import story as ST
    out = {}
    for x, others, _, _ in ST.leaderboard_rows(S)[0]:
        for y in (x, *others):
            line = ST.links_line(S, y, "../")
            if line:
                out.setdefault(y["name"], line)
                out.setdefault(y["model"], line)
    return out


def maker_dot(setup: str) -> tuple[str, str]:
    """(maker, the row's dot) as on the leaderboard."""
    mk, colour = H.maker(setup)
    return mk, f'<i class="swatch hl-dot" style="background:{colour}" title="{esc(mk)}"></i>'


def name_cell(setup: str, dot: str, bid: str, box: list, extra: str = "", sized: str = "") -> str:
    from story import box_html
    return (f'<th scope="row" class="model">{dot}<span class="model-name" tabindex="0" aria-describedby="{bid}">'
            f'{esc(setup)}</span>{sized}{extra}{box_html(bid, setup, box)}</th>')


def first_line(model: str, mk: str | None, typ: str, setting: str | None) -> str:
    return " \u00b7 ".join([f"<strong>{esc(model)}</strong>"] + [esc(p) for p in (mk, typ, setting) if p])


def answers_line(m) -> str | None:
    parts = [f'{w}: {count(a["valid"])} valid of {count(a["expected"])} ({count(a["tests"])} test'
             f'{"s" if a["tests"] != 1 else ""}), {count(a["invalid"])} invalid'
             for w, a in (("before", m["answers_before"]), ("after", m["answers_after"])) if a]
    return "Answers " + "; ".join(parts) if parts else None


def change_line(m) -> str | None:
    """A model's measures before → after (each with both values; the phone's table shows them only here) and, past
    the verdict gate, its Yes/No."""
    parts = [f'{t} {before_after(m, k)}' for t, k in (("Risks found", "risks_found"), ("right safety", "right_safety"),
                                                     ("error rate", "error_rate"))
             if m["before"][k] is not None and m["after"][k] is not None]
    parts += [f'Improved? <strong>{esc(m["status"])}</strong>'] if m["verdict"] else []
    return " \u00b7 ".join(parts) or None


def result_rows(L) -> list:
    """The plan's chat models for the results table, as (pm, progress, validated data): finished first by the change
    in risks found (largest first), then running (any other started status), then not started; plan order within a
    group."""
    prog = {m["setup"]: m for m in (L["progress"] or {}).get("models", [])}
    by = {m["setup"]: m for m in (L["results"] or {}).get("models", [])} if results_shown(L) else {}
    out = []
    for i, pm in enumerate(L["plan"]["models"]):
        p, m = prog.get(pm["setup"]), by.get(pm["setup"])
        done = m is not None and m["verdict"] and m["change"]["risks_found"] is not None
        started = not L["progress_refused"] and p is not None and p["status"] != "not started"
        key = (0, -m["change"]["risks_found"], i) if done else ((1, 0, i) if started else (2, 0, i))
        out.append((key, pm, p, m))
    return [x[1:] for x in sorted(out, key=lambda x: x[0])]


def result_row(pm, p, m, refused, i: int, links: dict) -> str:
    if refused:
        status_, done = nm(NA), nm(NA)
    elif p is None:
        status_, done = "not started", f"0 / {V.SERIES}"
    else:
        status_, done = esc(progress_status(p)), f'{p["series_done"]} / {V.SERIES}'
    if m is None:
        nums = "<td></td><td></td><td></td>"
    else:
        ch = m["change"]
        nums = (f'<td class="num" data-rcell="rf">{before_after(m, "risks_found")}</td>'
                f'<td class="num" data-rcell="rf-change">{fmt(ch["risks_found"], 1, signed=True) or nm(NA)}</td>'
                f'<td class="num" data-rcell="rs">{before_after(m, "right_safety")}</td>')
    verdict = (f'<strong data-rverdict="{"yes" if m["improved"] else "no"}">{esc(m["status"])}</strong>'
               if m is not None and m["verdict"] else "")
    name = re.sub(r" \([^()]*\)$", "", pm["setup"])
    setting = pm["setup"][len(name) + 2:-1] or None
    mk, dot = maker_dot(pm["setup"])
    bid = f"ir-{i}-box"
    box = [first_line(name, mk, "chat model", setting), f"Parameters: {P.params_html(name)}",
           "Route: " + ("our GPU" if pm["route"].startswith("local") else _inline(pm["route"])),
           None if refused else f"Status: {status_}", None if refused else f"Series done {done}",
           m and answers_line(m), m and change_line(m), links.get(pm["setup"]) or links.get(name)]
    cls, labelled = model_class(name)
    return (f'<tr data-progress-setup="{esc(pm["setup"])}" data-group="chat" data-class="{cls}" data-box="{bid}">'
            f'{name_cell(pm["setup"], dot, bid, box, sized=labelled)}<td>Chat</td><td data-progress="status">{status_}</td>'
            f'<td class="num" data-progress="series">{done}</td>{nums}<td>{verdict}</td></tr>')


def planned_row(r, arm, i: int, links: dict) -> str:
    status_ = r[arm[0]] if arm else r["status"]
    group = f"Decision · {arm[1]}" if arm else "Chat"
    tag = f'<br><span class="small">{esc(r["tag"])}</span>' if r["tag"] else ""
    listed = r["params_model"] is not None
    mk, dot = maker_dot(r["setup"])
    bid = f"ir-{i}-box"
    box = [first_line(r["setup"], mk, "decision model" if arm else "chat model", None),
           f'Parameters: {P.params_html(r["params_model"])}' if listed else None,
           f"Arm: {ARM_LABEL[arm[0]]}" if arm else None, f"Status: {esc(status_)}",
           " \u00b7 ".join(["Planned, not a result"] + ([esc(r["tag"])] if r["tag"] else [])),
           links.get(r["setup"]) or (links.get(r["params_model"]) if listed else None)]
    cls, labelled = model_class(r["params_model"])
    return (f'<tr data-planned="{esc(r["setup"])}" data-group="{r["group"]}" data-class="{cls}" '
            f'data-box="{bid}">{name_cell(r["setup"], dot, bid, box, "<br><span class=\"small\">planned, not a result</span>" + tag, labelled)}'
            f'<td>{group}</td><td>{esc(status_)}</td><td class="num">{nm(NA)}</td><td></td><td></td><td></td>'
            '<td></td></tr>')


def results_section(L, S=None) -> str:
    """The page's first table (Ümit/Zeki #3710): one row per model, the plan's chat models (status and series from
    the validated progress fields; numbers from the validated results; Yes or No only past the verdict gate), then the
    planned rows (content/improve_planned.json: status only, never a number). Filters: type (All, Chat, Decision) and
    class (P.class_keys), combined. Each
    row: its maker dot and details box; S (the site's state, absent in the page's own renders): the boxes' links to
    the leaderboard's decisions and model pages."""
    refused = L["progress_refused"]
    links = board_links(S) if S else {}
    rows_ = [result_row(pm, p, m, refused, i, links) for i, (pm, p, m) in enumerate(result_rows(L), 1)]
    rows_ += [planned_row(r, arm, i, links) for i, (r, arm) in enumerate(
        ((r, arm) for r in L["planned"] for arm in ((None,) if r["group"] == "chat" else ARMS)), len(rows_) + 1)]
    note = ('<p class="note" id="improve-progress-refused"><strong>Status unavailable.</strong> The latest results '
            'file\'s status fields failed the site\'s checks:</p><ul class="notes">'
            + "".join(f"<li>{esc(p)}</li>" for p in refused) + "</ul>" if refused else "")
    keys = ('<div class="keys needs-js" role="group" aria-label="Model type">'
            + "".join(f'<button type="button" class="key" data-improve-filter="{k}" aria-pressed="{str(k == "all").lower()}">'
                      f'{t}</button>' for k, t in (("all", "All"), ("chat", "Chat models"), ("decision", "Decision models")))
            + "</div>" + P.class_keys("improve-class"))
    cap = (f'{count(len(L["plan"]["models"]))} chat models under the pre-registered rule: finished first (by the change '
           'in risks found), then running, then not started. Rows marked "planned, not a result" are not run yet and '
           'show no numbers; a decision setup has one row per arm (notes, worst mistakes).')
    head = ["Model", "Group", "Status", f"Series (of {V.SERIES})", "Risks found before → after", "Change",
            "Right safety before → after", "Improved?"]
    return (note + keys + f'<p class="table-note" id="improve-results-note">{esc(cap)}</p>' + P.SWIPE
            + P.table(head, rows_, "Results, one row per model", cls="board list improve-progress",
                      attrs=' id="improve-results-table"'))


def validation_note(L) -> str:
    v = L["validation"]
    if not v or v.get("accepted"):
        return ""
    items = "".join(f"<li>{esc(p)}</li>" for p in v["problems"])
    return ('<div class="note validation-note" id="improve-refused"><p><strong>Data refused.</strong> The latest '
            'results file failed the site\'s checks against the pre-registration, so none of its numbers or lessons '
            f'are shown; this is the pre-registration view:</p><ul>{items}</ul></div>')


def status_line(L) -> str:
    st = L["status"]
    t = st["last_update"]
    when = f'<time datetime="{esc(t)}">{LP.utc(t)}</time>' if t else "none yet"
    return (f'<p class="lp-status" id="improve-status-line"><strong data-phase="{st["phase"]}">{esc(st["line"])}'
            f'</strong> <span class="small">· Last update: {when}</span></p>')


def money(L) -> str:
    R = L["results"]
    if L["preregistration_only"] or R is None:
        return ""
    M = R["money"]
    return (f'<p class="note" id="improve-money">Billed so far: ${fmt(M["billed_total_usd"], 2)} of the approved '
            f'${fmt(M["total_cap_usd"], 2)} (a cap, not a target). The stop rules are the plan\'s section 9, below.</p>')


def test_row(name, t) -> str:
    return (f'<tr><th scope="row">{esc(name)}</th><td class="num">{num(t["risks_found"])}</td>'
            f'<td class="num">{num(t["right_safety"])}</td><td class="num">{num(t["error_rate"])}</td>'
            f'<td class="num">{count(t["answered"])} / {count(t["expected"])}</td><td class="num">{count(t["valid"])}'
            f'</td><td class="num">{count(t["invalid"])}</td><td class="num">{count(t["failed"])}</td>'
            f'<td class="num">{count(t["risk_pays"])} / {count(t["safety_pays"])}</td>'
            f'<td class="num">{fmt(t["answer_rate"], 1)}%</td></tr>')


def lessons(L) -> str:
    """Per model (validated data only): its tests, then every series' lessons, per game, as kept after the cut rule."""
    R = L["results"]
    out = []
    for pm, m in rows(L):
        if m is None:
            continue
        tests = [test_row(f"Empty run E{i + 1}", t) for i, t in enumerate(m["empty"])]
        tests += [test_row(f"Series {s['series']}, after game 10", s["t10"]) for s in m["series"] if s["t10"]]
        table = (P.SWIPE + P.table(["Test", "Risks found", "Right safety", "Error rate (PR)", "Answered", "Valid",
                                    "Invalid", "Failed", "Risk pays / safety pays", "Answer rate"], tests,
                                   f'{esc(pm["setup"])}: every test', cls="board list") if tests else
                 '<p class="note">No test yet.</p>')
        sers = []
        for s in m["series"]:
            items = "".join(
                f'<li class="lp-lesson" data-series="{s["series"]}" data-game="{x["game"]}"><p class="small"><strong>'
                f'Game {x["game"]}</strong>: lessons written after this game:</p>'
                + (f'<pre class="citation">{esc(x["text"])}</pre>' if x["text"] else
                   f'<p>{nm("empty lesson set (kept, not re-asked)")}</p>') + "</li>" for x in s["lessons"])
            sers.append(
                f'<details class="lp-series"><summary>Series {s["series"]}'
                f'{"" if s["finished"] else " (in progress)"}: {count(s["games"])} games, {count(s["wins"])} won; '
                f'{count(s["lesson_calls"])} lesson calls, {count(s["lessons_cut"])} cut, {count(s["lessons_empty"])} '
                f'empty; {count(s["restarts"])} restarts; game decisions {count(s["game_decisions"])}, invalid '
                f'{count(s["game_invalid"])}</summary><ul class="notes">{items}</ul></details>')
        out.append(f'<details class="improve-model" id="lessons-{esc(pm["key"])}"><summary><strong>'
                   f'{esc(pm["setup"])}</strong>: {esc(m["status"])}</summary>{table}{"".join(sers)}</details>')
    if not out:
        return '<p class="note">No lessons yet.</p>'
    dry = '<p class="note">Dry run: no verdict is given.</p>' if R["dry_run"] else ""
    return (dry + '<p class="small">Each series starts with no lessons; after each game the model wrote its lessons, '
            'which the next games of the series read. Kept text after the cut rule (at most 5 lessons, 150 words).'
            '</p>' + "".join(out))


def prompt(L) -> str:
    p, plan = L["lesson_prompt"], L["plan"]
    test = (f'<p>Test set: 200 positions (never published), sha256 <code>{plan["test_set_sha256"]}</code>.</p>')
    if p is None:
        return (f'<p>sha256 stated in the plan: <code>{plan["prompt_sha256"]}</code></p>'
                '<p class="note">The lesson prompt files are not in this build yet.</p>' + test)
    return (f'<p>sha256 of the system file\'s bytes immediately followed by the user file\'s bytes: '
            f'<code>{p["sha256"]}</code> (the plan\'s).</p>{test}<h3>System</h3><pre class="citation">'
            f'{esc(p["system"])}</pre><h3>User</h3><pre class="citation">{esc(p["user"])}</pre>')


def results_shown(L) -> bool:
    return not L["preregistration_only"] and L["results"] is not None


def eyebrow(L) -> str:
    if L["preregistration_only"] or not results_shown(L):
        return "Pre-registration"
    return "Complete" if L["status"]["phase"] == "done" else "Preliminary · running"


def title(L) -> str:
    return TITLE if results_shown(L) else TITLE_PREREG


def addendum_section(A) -> str:
    """Part 3, the decision models: the addendum's sections as written, its commitment line, and its sha256 with a
    link to the committed file, so the page's copy can be checked against the file the harness is bound to."""
    secs = "".join(f'<h3>{esc(s["title"])}</h3>{spec_markdown(s["markdown"])}' for s in A["sections"])
    return (f'<p class="intro" id="improve-decision-commitment"><strong>{esc(A["commitment"])}</strong></p>'
            '<p>The decision models are pre-registered in an addendum to the plan, committed before their first '
            'call. Its rule, cohort, writer, money and open decisions follow as written; the planned rows above '
            'show each setup\'s status per arm.</p>'
            f'<p class="small" id="improve-decision-sha">Addendum: <a href="{esc(A["url"])}">{esc(A["file"])}</a>, '
            f'sha256 <code>{A["sha256"]}</code></p>{secs}')


def body(L, S=None) -> str:
    plan = L["plan"]
    rule = section(plan["sections"], RULE_SECTION)
    parts = [("improve-decision", "Decision models (added 9 Nov)", addendum_section(L["addendum"])),
             ("improve-rule", rule["title"], spec_markdown(rule["markdown"])),
             ("improve-models", "Models", models_section(L))]
    if results_shown(L):
        parts.append(("improve-lessons", "Lessons and every test, per model", lessons(L)))
    parts.append(("improve-prompt", "Lesson prompt and test set", prompt(L)))
    parts += [(LP.section_id(s["title"]), s["title"], spec_markdown(s["markdown"])) for s in plan["sections"]
              if s is not rule]
    toc = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t, _ in parts)
    withheld = (f'<p class="note">{count(L["redacted"])} private address(es) in the plan are withheld here.</p>'
                if L["redacted"] else "")
    intro = ("The pre-registered rule, model list, lesson prompt, settings and money rules. No results are on this "
             "page yet." if not results_shown(L) else
             "The pre-registered rule, the results as each model's runs come in, and every lesson.")
    head = (f'<header class="card hero page-head"><p class="eyebrow">{eyebrow(L)}</p><h1>{esc(title(L))}</h1>'
            f'</header><section class="card" id="improve-results"><h2>Results</h2>{results_section(L, S)}</section>')
    about = ('<section class="card" id="improve-about">' + (status_line(L) if results_shown(L) else "")
             + f'<p class="intro" id="improve-commitment"><strong>{esc(plan["commitment"])}</strong></p>'
             f'<p class="intro">{intro} Data: <a href="../{DATA}">improve.json</a>.</p>{validation_note(L)}{money(L)}'
             f'<p class="small">Plan: {esc(plan["file"])}, sha256 <code>{plan["sha256"]}</code></p>{withheld}</section>')
    return "\n".join([head, about, f'<nav class="toc card" aria-label="On this page"><ul>{toc}</ul></nav>']
                     + [f'<section class="card" id="{i}"><h2>{esc(t)}</h2>{h}</section>' for i, t, h in parts])


def site_state(L) -> dict:
    R = L["results"]
    t = datetime.fromisoformat(R["updated_at"]) if R else datetime.now(timezone.utc)
    return dict(hash=L["source_sha256"][:12], as_of=t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                image=None, description="", leagues=[])


def render(out: Path, L: dict) -> Path:
    S = site_state(L)
    page = out / PATH / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(P.layout(S, LP.site_base(), PATH, title(L), body(L), description=DESCRIPTION, scripts=("bg.js",)))
    (out / DATA).parent.mkdir(parents=True, exist_ok=True)
    (out / DATA).write_text(json.dumps(L, indent=1, ensure_ascii=False))
    return page


# --- Checks -------------------------------------------------------------------------------------------------

def check(out: Path, site: Path, L: dict, test_set: Path | None = None) -> list[str]:
    import checks
    S = site_state(L)
    page = out / PATH / "index.html"
    rel = page.relative_to(out)
    tree = checks.Tree()
    tree.feed(checks.without_suite_bar(page.read_text()))
    bad = checks.check_numbers(rel, tree.root, checks.allowed_numbers(out, S))
    bad += checks.check_mixing(rel, tree.root, S)
    with tempfile.TemporaryDirectory(prefix="improve-check-") as t:
        tmp = Path(t)
        LP.overlay(site, out, tmp)
        bad += [f.replace(str(tmp / rel), str(rel)) for f in checks.check_links(tmp / rel, tree.root, tmp)]
    for p in (p for p in out.rglob("*") if p.is_file()):
        m = checks.scan_file(p)
        if m:
            bad.append(f"{p.relative_to(out)}: banned string {m.group(0)!r}")
    return bad + checks.check_improve(out, test_set or TEST_SET)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="output directory (default: a new temporary directory)")
    ap.add_argument("--plan", default=str(PLAN))
    ap.add_argument("--src", default=str(Path("~/.local/state/bg-site").expanduser() / SOURCE),
                    help="the experiment's files in snapshot.py's STATE/improve layout")
    ap.add_argument("--check", metavar="SITE", help="run checks.py's page checks, links resolved against SITE")
    ap.add_argument("--test-set", default=str(TEST_SET),
                    help="the private test set: its hash, and its positions for the leakage checks")
    ap.add_argument("--with-results", action="store_true",
                    help="review renders only: read improve.json although PREREGISTRATION_ONLY is on")
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(tempfile.mkdtemp(prefix="improve-page-"))
    try:
        L = data(Path(a.plan), Path(a.src), Path(a.test_set), preregistration_only=False if a.with_results else None)
    except LP.TestSetRequired as e:
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
