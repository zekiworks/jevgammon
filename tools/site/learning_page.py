#!/usr/bin/env python3
"""Learning from experience (preliminary, running): the learning pilot's page, render-only candidate.

    python3 tools/site/learning_page.py [--out DIR] [--plan MD] [--results JSON] [--runs DIR] [--prompts DIR]
                                        [--check SITE]

Writes OUT/learning/index.html and its data file OUT/data/v3/learning-pilot.json (OUT defaults to a new temporary
directory, never the live site). Every source is read at render time:

- the plan (--plan, default mailbox/Learning pilot - plan 2026-11-07.md): the single source of the protocol text, shown
  section by section, with its commitment line near the top;
- the lesson prompt (--prompts, default workspace/learning-pilot: lessons_system.txt and lessons_user.txt) and its
  sha256, one hash over the system file's bytes immediately followed by the user file's bytes; when the plan states a
  64-hex hash, the render fails unless the files hash to it;
- the results (--results, default workspace/learning-pilot/out/learning-pilot.json), absent before the first series:
  "No results yet" and progress 0 / planned. Numbers per arm x test round and progress appear as series finish; the
  learning lift and the signal rule's result only once "complete" is true (plan §9); never positions, answers or
  contexts;
- the lessons the model wrote (--runs, default workspace/learning-pilot/runs: lessons/sNN/lessons-gKK.txt), each next
  to its game (series, game, result from the series aggregate's games), for finished series only.

Only what the page shows goes into the data file (aggregates; whitelisted keys), so every number on the page traces to
it (checks.py check 1). --check SITE runs checks.py's page checks on the output: numbers trace (against the output's
own data file and the site's content files), no mixing, links and ids (resolved with the built site SITE laid under
the output, read-only), and the private-strings scan of every output file. The page is not in the site's navigation
or build: build.py would wire it as the Clear risk page is (data(), body(), a put() and a write_json()).
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))

from common import BANNED, NA, ROOT, count, esc, fmt, nm, status_badge  # noqa: E402

import pages as P  # noqa: E402

PATH = "learning/"
DATA = "data/v3/learning-pilot.json"
TITLE = "Learning from experience (preliminary, running)"
COMMITMENT = "Results will be published whichever way they go, including no lift."
PLAN = ROOT / "mailbox/Learning pilot - plan 2026-11-07.md"
PILOT = ROOT / "workspace/learning-pilot"
CHECKPOINTS = ("T0", "T5", "T10")
# Shown per arm x test round; the keys copied to the data file are exactly these.
METRICS = [("error_rate", "Error rate (PR)", 1, ""), ("risk_judgement", "Risk judgement", 1, ""),
           ("risks_found", "Risks found", 1, "%"), ("right_safety", "Right safety", 1, "%"),
           ("risk_appetite", "Risk appetite", 1, "%"), ("invalid", "Invalid answers", 0, ""),
           ("failed", "Failed requests", 0, ""), ("input_tokens_per_decision", "Input tokens per decision", 0, ""),
           ("request_seconds", "Request s", 1, ""), ("cost_usd", "Cost $", 2, ""), ("series", "Series", 0, "")]
GAME_METRICS = [("series", "Series", 0), ("games", "Games", 0), ("wins", "Wins", 0), ("decisions", "Decisions", 0),
                ("invalid", "Invalid answers", 0), ("error_rate", "Error rate (PR)", 1)]
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
                hashes=HEX64.findall(text))


def read_prompt(prompts: Path, plan: dict) -> dict:
    system, user = (prompts / "lessons_system.txt").read_bytes(), (prompts / "lessons_user.txt").read_bytes()
    sha = hashlib.sha256(system + user).hexdigest()
    if plan["hashes"] and sha not in plan["hashes"]:
        raise SystemExit(f"lesson prompt sha256 {sha} is not the one the plan states ({', '.join(plan['hashes'])})")
    return dict(system=system.decode(), user=user.decode(), sha256=sha, stated_in_plan=sha in plan["hashes"])


def pick(row, keys):
    return None if row is None else {k: row.get(k) for k in keys if k in row} | (
        {"shared": True} if row.get("shared") else {})


def read_results(path: Path | None) -> dict | None:
    """The results file, cut down to what the page shows. The learning lift and the signal stay out unless complete."""
    if path is None or not path.exists():
        return None
    R = json.loads(path.read_text())
    keys = [k for k, *_ in METRICS]
    out = dict(updated_at=R["updated_at"], planned_series_per_arm=R["planned_series_per_arm"],
               series_done=R["series_done"], complete=bool(R["complete"]),
               table={arm: {cp: pick(by_cp.get(cp), keys) for cp in CHECKPOINTS if cp in by_cp}
                      for arm, by_cp in R["table"].items()})
    if "t0_done" in R:
        out["t0_done"] = R["t0_done"]
    if R.get("games"):
        out["games"] = {arm: pick(g, [k for k, *_ in GAME_METRICS]) for arm, g in R["games"].items()}
    if out["complete"]:
        for k in ("learning_lift", "signal", "paired_series"):
            if k in R:
                out[k] = R[k]
    return out


def read_lessons(runs: Path | None, results_path: Path | None) -> list:
    """Every lesson file of a finished series of the lessons arm, with its game's result from the series aggregate."""
    if runs is None or results_path is None or not results_path.exists():
        return []
    finished = {s["series"]: s for s in json.loads(results_path.read_text()).get("series", []) if s["arm"] == "lessons"}
    out = []
    for s in sorted(finished):
        games = {g["game"]: g for g in finished[s].get("games", [])}
        for f in sorted((runs / "lessons" / f"s{s:02d}").glob("lessons-g*.txt")):
            g = int(f.stem.removeprefix("lessons-g"))
            text = f.read_text().strip()
            if text:
                out.append(dict(series=s, text=text, **{k: games.get(g, {}).get(k) for k in GAME_KEYS} | {"game": g}))
    return out


def data(plan_path: Path, results_path: Path | None, runs: Path | None, prompts: Path) -> dict:
    plan = read_plan(plan_path)
    L = dict(version="v3", plan={k: v for k, v in plan.items() if k not in ("redacted", "hashes")},
             redacted=plan["redacted"], lesson_prompt=read_prompt(prompts, plan),
             results=read_results(results_path), lessons=read_lessons(runs, results_path))
    L["source_sha256"] = hashlib.sha256(json.dumps(L, sort_keys=True).encode()).hexdigest()
    return L


# --- Page ---------------------------------------------------------------------------------------------------

def inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]*)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def md_table(rows: list[str], caption: str) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    body = [r for r in cells[1:] if not all(set(c) <= set("-: ") for c in r)]
    return P.table([inline(c) for c in cells[0]],
                   ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body],
                   esc(caption), cls="board list")


def markdown(text: str, caption: str) -> str:
    """The plan's Markdown as the plan uses it: paragraphs, nested "- " lists, pipe tables, `code` and **bold**."""
    out, para, rows, depth = [], [], [], 0

    def close(level=0):
        """Ends the paragraph and the table, and closes lists deeper than level."""
        nonlocal depth
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if rows:
            out.append(md_table(rows, caption))
            rows.clear()
        if depth > level:
            out.append("</li></ul>" * (depth - level))
            depth = level

    for line in text.splitlines():
        item = re.match(r"^( *)- (.*)", line)
        if not line.strip():
            close()
        elif line.lstrip().startswith("|"):
            if not rows:
                close()
            rows.append(line)
        elif item:
            level = len(item.group(1)) // 2 + 1
            if para or rows:
                close(depth)
            if level > depth:
                out.append("<ul>" * (level - depth))
                depth = level
            else:
                close(level)
                out.append("</li>")
            out.append(f"<li>{inline(item.group(2))}")
        elif depth:
            out.append(" " + inline(line.strip()))
        else:
            para.append(line.strip())
    close()
    return "".join(out)


def num(v, digits, unit="") -> str:
    return nm(NA) if v is None else fmt(v, digits) + unit


def progress(L) -> str:
    R = L["results"]
    if R is None:
        return (f'<p class="note"><strong>No results yet.</strong></p><p>Progress: 0 / planned series per arm '
                f'(the planned count appears with the first results file).</p>')
    planned = R["planned_series_per_arm"]
    rows = [f'<tr><th scope="row">{esc(a)}</th><td class="num">{count(n)} / {count(planned)}</td></tr>'
            for a, n in R["series_done"].items()]
    t0 = (f'<p class="note">Shared T0 test (before any context): {"done" if R["t0_done"] else "not yet done"}.</p>'
          if "t0_done" in R else "")
    state = "All planned series are done." if R["complete"] else "Running: not all planned series are done."
    return (f'<p class="note">{status_badge("Preliminary")} {esc(state)} Updated {esc(R["updated_at"])}.</p>{t0}'
            + P.table(["Arm", "Series done / planned"], rows, "Progress per arm"))


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
        return '<p class="note"><strong>No results yet.</strong> Numbers appear here as each series finishes.</p>'
    out = [results_table(R)]
    if R.get("games"):
        out.append(games_table(R))
    if not R["complete"]:
        out.append('<p class="note">The learning lift and any verdict are shown only when every planned series of '
                   'every arm is done.</p>')
        return "".join(out)
    arms = list(R["table"])
    if "learning_lift" in R:
        out.append("<h3>Learning lift</h3>" + arm_table(R["learning_lift"], arms,
                                                       "Learning lift per arm (definition: the plan's Metrics)"))
    if "signal" in R:
        out.append("<h3>Signal rule</h3>" + arm_table(R["signal"], arms,
                                                      "Signal rule per arm (definition: the plan's Signal rule)"))
    return "".join(out)


def lessons(L) -> str:
    if not L["lessons"]:
        return '<p class="note">No lessons yet: they appear with each finished series of the lessons arm.</p>'
    out = []
    for x in L["lessons"]:
        res = (f'{"won" if x["won"] else "lost"} {count(x["points"])} point{"s" if x["points"] != 1 else ""}'
               f' ({esc(x["result"])})' if x["won"] is not None else nm(NA))
        out.append(f'<li><p class="small">Series {x["series"]}, game {x["game"]}: {res}</p>'
                   f'<pre class="citation">{esc(x["text"])}</pre></li>')
    return f'<ul class="notes">{"".join(out)}</ul>'


def prompt(L) -> str:
    p = L["lesson_prompt"]
    stated = ("" if p["stated_in_plan"] else
              '<p class="note">The plan does not state this hash yet.</p>')
    return (f'<p>sha256 of the system file\'s bytes immediately followed by the user file\'s bytes: '
            f'<code>{p["sha256"]}</code></p>{stated}<h3>System</h3><pre class="citation">{esc(p["system"])}</pre>'
            f'<h3>User</h3><pre class="citation">{esc(p["user"])}</pre>')


def section_id(title: str) -> str:
    return "plan-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def body(L) -> str:
    plan = L["plan"]
    parts = [("learning-status", "Status and progress", progress(L)), ("learning-results", "Results", results(L)),
             ("learning-lessons", "Lessons the model wrote", lessons(L)),
             ("learning-prompt", "Lesson prompt", prompt(L))]
    parts += [(section_id(s["title"]), s["title"], markdown(s["markdown"], s["title"])) for s in plan["sections"]]
    toc = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t, _ in parts)
    withheld = (f'<p class="note">{count(L["redacted"])} private address(es) in the plan are withheld here.</p>'
                if L["redacted"] else "")
    status = f'<p class="note">{inline(plan["status"])}</p>' if plan["status"] else ""
    head = (f'<header class="card hero page-head"><p class="eyebrow">Preliminary · running</p><h1>{esc(TITLE)}</h1>'
            f'<p class="intro"><strong>{esc(plan["commitment"])}</strong></p>'
            f'<p class="intro">The pre-registered plan, the lesson prompt and the results as they come in. Data: '
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
    page.write_text(P.layout(S, site_base(), PATH, TITLE, body(L),
                             description="The learning pilot of the backgammon benchmark (preliminary, running): does "
                                         "a model play better after seeing its own earlier games? The pre-registered "
                                         "plan, the lesson prompt and the results as they come in."))
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


def check(out: Path, site: Path, L: dict) -> list[str]:
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
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="output directory (default: a new temporary directory)")
    ap.add_argument("--plan", default=str(PLAN))
    ap.add_argument("--results", default=str(PILOT / "out/learning-pilot.json"),
                    help="the harness's learning-pilot.json; a missing file means no results yet")
    ap.add_argument("--runs", default=str(PILOT / "runs"), help="the harness's runs directory (lessons/sNN/)")
    ap.add_argument("--prompts", default=str(PILOT), help="directory of lessons_system.txt and lessons_user.txt")
    ap.add_argument("--check", metavar="SITE", help="run checks.py's page checks, links resolved against SITE")
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(tempfile.mkdtemp(prefix="learning-page-"))
    L = data(Path(a.plan), Path(a.results), Path(a.runs), Path(a.prompts))
    if L["redacted"]:
        print(f"warning: {L['redacted']} private address(es) in the plan withheld", file=sys.stderr)
    print(render(out, L))
    if a.check:
        bad = check(out, Path(a.check), L)
        for b in bad:
            print(b)
        print(f"checks: {len(bad)} failure(s)")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
