"""Pre-deploy checks of a built site (brief B1). run() returns a list of failures; empty means deployable.

1. Numbers trace to data files: every number in the text of every page appears, as printed, among the values
   of the data files under data/ or the content files (tools/site/content/: thresholds, setups metadata,
   human scale, method experiments, archived earlier-page sections), allowing the formats the pages use
   (decimals, percentages, thousands separators, signs). Dates and times are taken out first.
2. Counts add up: per league, setup decisions sum to the league's decisions and match the snapshot; invalid +
   valid = decisions; risk cells and phase cells sum to the scored decisions; standings played = 2 x matches
   finished; the v1 set is setups x positions; exported decisions match the engine-scored decisions; the B6 marks
   on Every decision match the 2x2 counts; a late entry's decisions match the snapshot, its risk and phase cells
   add up, and it is in no league's setups or standings.
3. No mixing: no table holds rows of two datasets, except the home page's All leagues tables (data-dataset="all":
   league rows only, the All leagues note in their block); v1 rows only inside an Earlier-version block; every block
   of a league that has not finished says "Provisional: league still running".
4. No private addresses or credentials (B7): hostnames, IPs, ports, server paths, keys, tokens, request headers,
   the other benchmark's name, in any output file including the decompressed decision files. One exception: the
   suite strip at the top of a page, exactly as published (common.SUITE_BAR), once per HTML page (bus #2270, #2287,
   #2310); data files, decompressed .gz files and other text get the complete scan. selftest_suite_bar.py tests it.
5. Every relative link resolves; ids are unique per page and every #anchor exists.
6. Every published finding still holds (B4): findings.py reruns each finding's machine check on the built data.
7. The learning page (learning_page.py, plan §9): no verdict, learning lift, signal or Learning-tab ranking/leader block
   in the page or its data file unless the results are complete; no evaluation-set position (id, board key, board) in
   either (where the private test set is present); outside pre-registration-only mode, the status line, both charts and
   their tables, the verdict, the arms' display names, every lesson and the exploratory block (Ümit #2925, #2950)
   against the page's own data file.
8. The "Did they improve?" page (improve_page.py): the pre-registered texts, one row per plan model in the plan's sort
   order, no Yes/No before a model's verdict gate, every shown score recomputed from the data file's tests, no results
   block in pre-registration-only mode, and no test position in the page or its data file (check_improve).
"""

import gzip
import hashlib
import html
import json
import re
import sqlite3
import sys
from html.parser import HTMLParser
from pathlib import Path

import findings
from common import ALL_NOTE, BANNED, CONTENT, INTERNAL, LATE_ENTRY, PROVISIONAL, PROVISIONAL_NOTE, ROOT, SUITE_BAR

NUM = re.compile(r"(?<![\w.\u2212+-])([\u2212+-]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)?|\b\d{1,2}:\d{2}\b|"
                  r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December)"
                  r"(?: \d{4})?|\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}"
                  r"|\b\d{1,2} (?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text", "at")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.text = tag, dict(attrs), parent, [], []
        self.at = []  # per text chunk: how many children preceded it (for ordered_text)


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag in ("script", "style"):
            self.skip += 1
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            if tag in ("script", "style"):
                self.skip -= 1
            self.cur = n.parent

    def handle_data(self, data):
        if not self.skip:
            self.cur.text.append(data)
            self.cur.at.append(len(self.cur.children))


def walk(n):
    yield n
    for c in n.children:
        yield from walk(c)


def text_of(n) -> str:
    return "".join(t for x in walk(n) if x.tag not in ("script", "style") for t in x.text)


def ordered_text(n) -> str:
    """The text of n in document order (text_of puts a node's own text before its children's: "<span>N/A</span> →
    <span>N/A</span>" reads "→ N/AN/A")."""
    if n.tag in ("script", "style"):
        return ""
    out, chunks = [], list(zip(n.at, n.text))
    for i, c in enumerate(n.children + [None]):
        out += [t for at, t in chunks if at == i]
        if c is not None:
            out.append(ordered_text(c))
    return "".join(out)


def ancestors(n):
    n = n.parent
    while n is not None:
        yield n
        n = n.parent


# --- 1. Numbers ---------------------------------------------------------------------------------------------

def _forms(x: float, out: set):
    for v in (x, 100 * x):
        for d in range(4):
            out.add(f"{abs(v):.{d}f}")


def _collect(obj, nums: set, texts: list):
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        _forms(float(obj), nums)
    elif isinstance(obj, str):
        texts.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            texts.append(str(k))
            _collect(v, nums, texts)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, nums, texts)


def allowed_numbers(out: Path, S: dict) -> set:
    nums, texts = set(), []
    for p in (out / "data").rglob("*.json"):
        _collect(json.loads(p.read_text()), nums, texts)
    idx = out / "decisions/index.json"
    if idx.exists():
        _collect(json.loads(idx.read_text()), nums, texts)
    for p in CONTENT.rglob("*"):
        if p.suffix == ".json":
            _collect(json.loads(p.read_text()), nums, texts)
        elif p.suffix in (".html", ".txt", ".md"):
            texts.append(re.sub(r"<[^>]+>", " ", p.read_text()))
    texts.append(S["as_of"])
    for t in texts:
        for m in NUM.finditer(DATE.sub(" ", t)):
            nums.add((m.group(2) + (m.group(3) or "")).replace(",", ""))
            if "." not in m.group(0):
                _forms(float(m.group(2).replace(",", "")), nums)
    return nums


def check_numbers(page: Path, root: Node, nums: set) -> list[str]:
    bad = []
    for n in walk(root):
        if n.tag in ("script", "style", "code", "pre", "svg"):
            continue
        if any(a.tag in ("script", "style", "code", "pre", "svg") for a in ancestors(n)):
            continue
        for chunk in n.text:
            for m in NUM.finditer(DATE.sub(" ", chunk)):
                token = (m.group(2) + (m.group(3) or "")).replace(",", "")
                if token not in nums:
                    bad.append(f"{page}: number {m.group(0)!r} not found in any data file (in {chunk.strip()[:80]!r})")
    return bad


# --- 2. Counts ----------------------------------------------------------------------------------------------

def check_counts(S: dict) -> list[str]:
    bad = []
    snap = sqlite3.connect(f"file:{S['_state'] / 'snap.db'}?mode=ro", uri=True)
    for lg in S["leagues"]:
        n = snap.execute("""SELECT COUNT(*) FROM turns t JOIN games g ON g.id = t.game_id
                            JOIN league_match_view lm ON lm.match_id = g.match_id
                            WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')""", (lg["id"],)).fetchone()[0]
        su = sum(s["quality"]["decisions"] for s in lg["setups"].values())
        if not (n == su == lg["decisions"]):
            bad.append(f"league {lg['id']}: snapshot {n}, setups sum {su}, league {lg['decisions']} decisions")
        if sum(s["quality"]["engine_scored"] for s in lg["setups"].values()) != lg["scored"]:
            bad.append(f"league {lg['id']}: engine-scored decisions do not add up")
        played = sum(t["played"] for t in lg["standings"])
        if played != 2 * lg["matches_done"]:
            bad.append(f"league {lg['id']}: standings played {played} != 2 x {lg['matches_done']} finished matches")
    # Late entries: their own decisions add up, and they are in no league's standings or setups (S carries the shown
    # names; the snapshot the databases').
    for e in S["late_entries"]:
        n = snap.execute("""SELECT COUNT(*) FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
                            JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
                            WHERE m.valid = 1 AND m.stage = 'late-entry' AND p.name = ?
                              AND t.decided_by IN ('model', 'fallback')""", (INTERNAL.get(e["name"], e["name"]),)).fetchone()[0]
        if n != e["quality"]["decisions"]:
            bad.append(f"late entry {e['name']}: snapshot {n}, setup {e['quality']['decisions']} decisions")
        if e["played"] + e["running"] > e["total"]:
            bad.append(f"late entry {e['name']}: {e['played'] + e['running']} matches for a field of {e['total']}")
        for lg in S["leagues"]:
            if e["name"] in lg["setups"] or any(t["name"] == e["name"] for t in lg["standings"]):
                bad.append(f"late entry {e['name']} is in league {lg['id']}")
    snap.close()
    sets = ([(lg["dataset"], lg["setups"]) for lg in S["leagues"]] + [(LATE_ENTRY, {e["name"]: e for e in S["late_entries"]})]
            + [("v1-set", S["v1"]["setups"])])
    for ds, setups in sets:
        for name, s in setups.items():
            q = s["quality"]
            if q["scored"] > q["decisions"] - q["invalid"]:
                bad.append(f"{ds}/{name}: scored {q['scored']} > valid decisions")
            for m, r in s["risk"].items():
                if sum(r["calls"].values()) != r["trade_off"]:
                    bad.append(f"{ds}/{name} ({m}): risk calls do not sum to the decisions with a trade-off")
                if r["trade_off"] + r["no_trade_off"] != q["scored"]:
                    bad.append(f"{ds}/{name} ({m}): trade-off + No trade-off {r['trade_off'] + r['no_trade_off']} != scored {q['scored']}")
                parts = [v for v in r["by_call"].values() if v is not None]
                if q.get("error_rate") is not None and abs(sum(parts) - q["error_rate"]) > 1e-9:
                    bad.append(f"{ds}/{name} ({m}): error rate by risk-call category sums to {sum(parts)}, not {q['error_rate']}")
                if r["judgement"] is None and r["risk_pays"] and r["safety_pays"]:
                    bad.append(f"{ds}/{name} ({m}): risk judgement missing with both classes present")
            for field in ("phases", "options"):
                if sum(c["n"] for c in s[field].values()) != q["scored"]:
                    bad.append(f"{ds}/{name}: {field} cells sum {sum(c['n'] for c in s[field].values())} != scored {q['scored']}")
    v1 = S["v1"]
    if v1["decisions"] != len(v1["setups"]) * v1["positions"] or any(
            s["quality"]["decisions"] != v1["positions"] for s in v1["setups"].values()):
        bad.append("v1 set: decisions != setups x positions")
    exp = S.get("decisions_export") or {}
    for lg in S["leagues"]:
        got = exp.get(lg["dataset"], {})
        for name, s in lg["setups"].items():
            want = s["quality"]["engine_scored"]
            have = got.get(name, {}).get("decisions", 0)
            if want != have:
                bad.append(f"{lg['dataset']}/{name}: {want} engine-scored decisions, {have} exported")
    got = exp.get("v1-set", {})
    for name in v1["setups"]:
        if got.get(name, {}).get("decisions") != v1["positions"]:
            bad.append(f"v1-set/{name}: exported {got.get(name, {}).get('decisions')} of {v1['positions']}")
    # Every decision's B6.1 marks (Every decision filters) must match the analyses' counts at the main margin.
    for ds, setups in sets:
        for name, s in setups.items():
            r, rc = s["risk"]["main"], exp.get(ds, {}).get(name, {}).get("risk")
            if rc is None:
                continue
            want = (r["risk_pays"], r["safety_pays"], r["no_trade_off"], {k: v for k, v in r["calls"].items()})
            have = (rc["risk"], rc["safety"], rc["none"], rc["calls"])
            if want != have:
                bad.append(f"{ds}/{name}: exported risk marks {have} != analysis {want}")
            # Close choices (Method spec 2026-10-24 §9): the Every decision marks match the analysis.
            cc = s.get("close")
            if cc is not None and "close" in rc:
                want_cc = (cc["close"]["n"], cc["eligible"] - cc["close"]["n"]) if not cc["na"] else (0, 0)
                have_cc = (rc["close"]["close"], rc["close"]["other"])
                if want_cc != have_cc:
                    bad.append(f"{ds}/{name}: exported close-choice marks {have_cc} != analysis {want_cc}")
    return bad


# --- 3. Mixing ----------------------------------------------------------------------------------------------

def _is_unit(n) -> bool:
    """A ranking, table or chart: every table and every chart SVG."""
    return n.tag == "table" or n.tag == "svg" and "chart-svg" in (n.attrs.get("class") or "").split()


def check_mixing(page: Path, root: Node, S: dict) -> list[str]:
    """No table or chart combines datasets (v1 set, league 1, 2, 3): every element in it that names a dataset
    (data-dataset on rows, points or the unit itself) names the same one, and a unit inside an Earlier-version block
    (data-version="v1") holds no v3 dataset. v1 numbers sit only inside such blocks."""
    bad = []
    running = {lg["dataset"] for lg in S["leagues"] if lg["metric_status"] == PROVISIONAL}
    for t in (n for n in walk(root) if _is_unit(n)):
        ds = {r.attrs["data-dataset"] for r in walk(t) if r.attrs.get("data-dataset")}
        in_v1 = any(a.attrs.get("data-version") == "v1" for a in [t] + list(ancestors(t)))
        what = "a table" if t.tag == "table" else "a chart"
        merged = t.tag == "table" and t.attrs.get("data-dataset") == "all"
        if merged:
            # The All leagues table (Can, approved by Ümit, 30 Oct 2026): every league's rows, each with its League. The
            # leaderboard (id headline-table) also ranks the late entries, each tagged (Ümit #2921 (b)).
            ds -= {"all"}
            allowed = {lg["dataset"] for lg in S["leagues"]} | ({LATE_ENTRY} if t.attrs.get("id") == "headline-table" else set())
            if ds - allowed:
                bad.append(f"{page}: the All leagues table holds rows outside the leagues {sorted(ds)}")
            if not any(ALL_NOTE in text_of(a) for a in ancestors(t) if a.attrs.get("data-dataset") == "all"):
                bad.append(f"{page}: the All leagues table without its note '{ALL_NOTE}' in its block")
        elif len(ds) > 1:
            bad.append(f"{page}: {what} mixes datasets {sorted(ds)}")
        if in_v1 and ds - {"v1-set"}:
            bad.append(f"{page}: {what} in an Earlier-version block holds v3 rows {sorted(ds - {'v1-set'})}")
        if "v1-set" in ds and not in_v1:
            bad.append(f"{page}: v1 rows outside an Earlier-version block")
        for r in ds & running:
            if not any(PROVISIONAL_NOTE in text_of(a) for a in ancestors(t) if a.attrs.get("data-dataset") in (r, "all" if merged else r)
                       or a.tag in ("section", "div") and a.attrs.get("id", "").startswith("league-")):
                bad.append(f"{page}: {what} of running {r} without '{PROVISIONAL_NOTE}' in its block")
    return bad


# --- 5. Links and ids ---------------------------------------------------------------------------------------

def check_links(page: Path, root: Node, out: Path, anchors: bool = True) -> list[str]:
    bad, ids = [], []
    for n in walk(root):
        if n.attrs.get("id"):
            ids.append(n.attrs["id"])
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        bad.append(f"{page}: duplicate ids {dup[:5]}")
    idset = set(ids)
    for n in walk(root):
        for attr in ("href", "src"):
            v = n.attrs.get(attr)
            if not v or v.startswith(("http:", "https:", "mailto:", "data:")):
                continue
            path, _, frag = v.partition("#")
            path = path.split("?")[0]
            if not path:
                if anchors and frag and frag not in idset and not v.startswith("?"):
                    bad.append(f"{page}: anchor #{frag} missing")
                continue
            target = (page.parent / path).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                bad.append(f"{page}: link {v} does not resolve")
    return bad


def without_suite_bar(text: str) -> str:
    """The page without its suite strip, when the strip is exactly the shared one (common.SUITE_BAR), once. The one
    exception to the private-strings rule (Ümit, bus #2270; Zeki, bus #2287): the strip's first link names the other
    benchmark's address. Any other occurrence of that address or name, or a strip whose text or links differ by one
    character, stays in the scan and fails. The same strip is left out of the link check: its three links are the
    suite's sites at the server's root (/analysis/...), outside this site's files."""
    return text.replace(SUITE_BAR, "", 1)


def banned_in(text: str, page: bool):
    """The first private string (common.BANNED) in a published file's text. Only an HTML page (`page`) has the exact
    suite strip left out, once (Zeki, bus #2310): a data file, a decompressed .gz file or any other text gets the
    complete scan, the strip included."""
    return BANNED.search(without_suite_bar(text) if page else text)


def scan_file(p: Path):
    """Check 4 for one output file: the first private string in it, or None. .gz files are scanned decompressed; only
    a file ending .html is an HTML page."""
    data = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
    return banned_in(data.decode("utf-8", "replace"), page=p.suffix == ".html")


# --- 7. Learning page ---------------------------------------------------------------------------------------


def _test_set_strings(path: Path) -> list[str]:
    """What would reveal an evaluation position: its id (lp-<turn id>), its board key, and its whole board as the pilot
    writes boards in prompts, records and notes (the mover's side, the mover's point numbering). One side alone is not
    checked: the plan's own format example (the starting setup) matches one side of some positions."""
    if str(ROOT / "tools/v3") not in sys.path:
        sys.path.append(str(ROOT / "tools/v3"))  # appended: tools/v3 has its own build.py
    from rules import from_json
    out = []
    for p in json.loads(path.read_text())["positions"]:
        pts, bar, off = from_json(p["position"], p["side"])
        mine = " ".join(f"{i + 1}:{n}" for i, n in enumerate(pts) if n > 0)
        theirs = " ".join(f"{i + 1}:{-n}" for i, n in enumerate(pts) if n < 0)
        out += [p["id"], p["board_key"], f"your checkers {mine or '-'} (bar {bar[0]}, off {off[0]}); "
                f"opponent's checkers {theirs or '-'} (bar {bar[1]}, off {off[1]})"]
    return out


def _learning_status(R, validation) -> str:
    """The status line the validated data implies (learning_page.status, derived again here from the data file):
    "Done" only when complete, else "Not started", "Smoke running: N of 3 series per arm" or "Running: N of 10 series
    per arm", N the series finished in every arm."""
    from learning_page import SMOKE_SERIES
    if R and R.get("complete") and (validation or {}).get("complete"):
        return "Done"
    if not R or (not R["series_total_done"] and not R["t0_done"]):
        return "Not started"
    n = min(len(s) for s in R["series_finished"].values())
    if n < SMOKE_SERIES:
        return f"Smoke running: {n} of {SMOKE_SERIES} series per arm"
    return f"Running: {n} of {R['planned_series_per_arm']} series per arm"


def _poly(n) -> list:
    return [tuple(float(c) for c in p.split(",")) for p in n.attrs.get("points", "").split()]


def _learning_results(root, L) -> list[str]:
    """The results view of the learning page (Ümit #2925) against its own data file: the status line; both charts
    (every dot is the data file's value, no other dot; the arms' fixed colours; control flat and dashed in the risks
    chart at its T0 value, no other line dashed) and the tables under them; the verdict only as the data allows; every
    lesson next to its game, its text exactly the data file's (escaped)."""
    from common import NA, fmt
    from learning_page import ARM_COLOUR, ARM_LABEL, CHECKPOINTS, CONTROL_DASH, MODEL, PATH, RUN_LINE
    bad, R, ids = [], L.get("results"), {}
    nodes = list(walk(root))
    for n in nodes:
        ids.setdefault(n.attrs.get("id"), n)
    # Status line.
    want = _learning_status(R, L.get("validation"))
    el = ids.get("learning-status-line")
    strong = next((c for c in walk(el) if c.tag == "strong"), None) if el else None
    if strong is None:
        bad.append(f"{PATH}: status line missing")
    elif text_of(strong).strip() != want:
        bad.append(f"{PATH}: status line says {text_of(strong).strip()!r}, the data imply {want!r}")
    else:
        t = next((c.attrs.get("datetime") for c in walk(el) if c.tag == "time"), None)
        if t != (R or {}).get("last_update"):
            bad.append(f"{PATH}: status line time {t!r} is not the data's last update")
    if (L.get("status") or {}).get("line") != want:
        bad.append(f"{PATH}: the data file's status line is not the one its data imply")
    # Charts and their tables.
    expect = {}
    if R and R["series_total_done"]:
        for arm, by_cp in R["table"].items():
            for cp in CHECKPOINTS:
                row = by_cp.get(cp)
                if row and row.get("risks_found") is not None and (arm != "control" or cp == "T0"):
                    expect[("learning-risks", arm, cp)] = row["risks_found"]
        for arm, per in R["game_error_rate"].items():
            for g, v in per.items():
                if v is not None:
                    expect[("learning-games", arm, g)] = v
    for chart in ("learning-risks", "learning-games"):
        svg = next((n for n in nodes if n.tag == "svg" and n.attrs.get("data-chart") == chart), None)
        want_dots = {(a, x): f"{v:.1f}" for (c, a, x), v in expect.items() if c == chart}
        if svg is None:
            if want_dots:
                bad.append(f"{PATH}: chart {chart} missing")
            continue
        dots = {(n.attrs.get("data-arm"), n.attrs.get("data-x")): n.attrs.get("data-value")
                for n in walk(svg) if n.tag == "circle"}
        for k in sorted(set(dots) | set(want_dots), key=str):
            if dots.get(k) != want_dots.get(k):
                bad.append(f"{PATH}: chart {chart} point {k}: {dots.get(k)!r}, data {want_dots.get(k)!r}")
        lines = [n for n in walk(svg) if n.tag == "polyline"]
        for n in lines:
            dashed = n.attrs.get("stroke-dasharray")
            if chart == "learning-risks" and n.attrs.get("data-arm") == "control":
                pts = _poly(n)
                cy = next((float(c.attrs["cy"]) for c in walk(svg) if c.tag == "circle"
                           and c.attrs.get("data-arm") == "control" and c.attrs.get("data-x") == "T0"), None)
                if dashed != CONTROL_DASH or len(pts) < 2 or any(abs(p[1] - pts[0][1]) > 1e-6 for p in pts) or (
                        cy is None or abs(pts[0][1] - cy) > 1e-6):
                    bad.append(f"{PATH}: chart {chart}: control is not a flat dashed line at its T0 value")
            elif dashed:
                bad.append(f"{PATH}: chart {chart}: {n.attrs.get('data-arm')!r} line is dashed (only control's is)")
        if chart == "learning-risks" and ("control", "T0") in want_dots and not any(
                n.attrs.get("data-arm") == "control" for n in lines):
            bad.append(f"{PATH}: chart {chart}: control's flat dashed line missing")
        cells = {(n.attrs.get("data-arm"), n.attrs.get("data-x")): text_of(n).strip() for n in nodes
                 if n.tag == "td" and "data-x" in n.attrs and any(
                     a.tag == "table" and f"lp-{chart.split('-')[1]}" in a.attrs.get("class", "").split()
                     for a in ancestors(n))}
        bad += [f"{PATH}: table under {chart}: no cell for {k}" for k in want_dots if k not in cells]
        for k, txt in cells.items():
            v = expect.get((chart, *k))
            if not (txt == fmt(v, 1) if v is not None else txt in (NA, "T0 only")):
                bad.append(f"{PATH}: table under {chart}, {k}: {txt!r} is not the data's "
                           f"{fmt(v, 1) if v is not None else NA}")
    for n in nodes:
        if {"lp-dot", "lp-line", "lp-swatch"} & set(n.attrs.get("class", "").split()):
            arm = n.attrs.get("data-arm")
            if arm not in ARM_COLOUR or n.attrs.get("style") != f"--lp:{ARM_COLOUR[arm]}":
                bad.append(f"{PATH}: arm {arm!r} not in its fixed colour")
    # Verdict: before complete only "N of 10 series done"; when complete, as the data's signal and budget points.
    complete = bool((R or {}).get("complete") and (L.get("validation") or {}).get("complete"))
    if not complete:
        n = min(len(s) for s in R["series_finished"].values()) if R else 0
        planned = R["planned_series_per_arm"] if R else (L.get("status") or {}).get("planned")
        el = ids.get("learning-verdict-pending")
        if el is None or f"{n} of {planned} series done" not in text_of(el):
            bad.append(f"{PATH}: the verdict section does not say '{n} of {planned} series done'")
    else:
        from learning_page import BUDGET_VERDICT
        el = ids.get("learning-verdict")
        if el is None:
            bad.append(f"{PATH}: complete, but no verdict")
        else:
            for li in (n for n in walk(el) if n.tag == "li" and n.attrs.get("data-arm")):
                met = bool((R["signal"].get(li.attrs["data-arm"]) or {}).get("signal"))
                if ("threshold not reached" in text_of(li)) == met:
                    bad.append(f"{PATH}: verdict for {li.attrs['data-arm']!r} contradicts the data's signal")
            empty, total = R["budget_empty_points"]["budget"], R["budget_points_total"]["budget"]
            if (BUDGET_VERDICT in text_of(el)) != bool(total and empty == total):
                bad.append(f"{PATH}: the budget reading (plan section 11) does not follow the budget points")
    # Display names (Ümit #2950): every legend entry, chart-table row and verdict line names its arm by ARM_LABEL; the
    # one line at the top of Results; the model in every chart title.
    for n in nodes:
        cls = n.attrs.get("class", "").split()
        if "lp-swatch" in cls and text_of(n.parent).strip() != ARM_LABEL.get(n.attrs.get("data-arm")):
            bad.append(f"{PATH}: legend entry {text_of(n.parent).strip()!r} is not its arm's name")
        if n.tag == "tr" and any("lp-numbers" in a.attrs.get("class", "").split() for a in ancestors(n)):
            arm = next((c.attrs.get("data-arm") for c in n.children if c.attrs.get("data-arm")), None)
            th = next((c for c in n.children if c.tag == "th"), None)
            if arm and (th is None or text_of(th).strip() != ARM_LABEL.get(arm)):
                bad.append(f"{PATH}: chart table row of {arm!r} is not named by its arm's name")
        if n.tag == "li" and n.attrs.get("data-arm") and any(a.attrs.get("id") == "learning-verdict"
                                                            for a in ancestors(n)):
            strong = next((c for c in n.children if c.tag == "strong"), None)
            if strong is None or text_of(strong).strip() != ARM_LABEL.get(n.attrs["data-arm"]):
                bad.append(f"{PATH}: verdict line of {n.attrs['data-arm']!r} is not named by its arm's name")
        if n.tag == "text" and "lp-title" in cls and MODEL not in text_of(n):
            bad.append(f"{PATH}: chart title {text_of(n).strip()!r} does not name {MODEL}")
    run_line = ids.get("learning-run-line")
    if R is not None and R["series_total_done"] and (run_line is None or text_of(run_line).strip() != RUN_LINE):
        bad.append(f"{PATH}: the line at the top of Results is missing or not the fixed one")
    bad += _learning_explore(nodes, ids, L, complete)
    # Lessons: each next to its game, exactly the data's text, finished lessons series only.
    fin = set((R or {}).get("series_finished", {}).get("lessons", []))
    data_lessons = {(x["series"], x["game"]): x for x in L.get("lessons") or []}
    for (s, g), x in data_lessons.items():
        if s not in fin or x.get("won") is None or not x.get("result") or not x.get("points"):
            bad.append(f"{PATH}: lesson of series {s} game {g} without its game")
    shown = {}
    for li in (n for n in nodes if n.tag == "li" and "lp-lesson" in n.attrs.get("class", "").split()):
        try:
            k = (int(li.attrs.get("data-series")), int(li.attrs.get("data-game")))
        except (TypeError, ValueError):
            bad.append(f"{PATH}: a lesson without its series and game")
            continue
        shown[k] = li
        pre = next((c for c in walk(li) if c.tag == "pre"), None)
        x = data_lessons.get(k)
        if x is None:
            bad.append(f"{PATH}: lesson of series {k[0]} game {k[1]} is not in the data file")
        elif pre is None or text_of(pre) != x["text"] or any(c.tag != "pre" for c in walk(pre) if c is not pre):
            bad.append(f"{PATH}: lesson of series {k[0]} game {k[1]}: text is not the data's, as written and escaped")
        elif f"game {k[1]}" not in text_of(li) or ("won" if x["won"] else "lost") not in text_of(li):
            bad.append(f"{PATH}: lesson of series {k[0]} game {k[1]} not shown with its game and result")
    bad += [f"{PATH}: lesson of series {s} game {g} missing from the page" for s, g in data_lessons if (s, g) not in shown]
    return bad


def _learning_explore(nodes, ids, L, complete: bool) -> list[str]:
    """The exploratory block (Ümit #2950/#2952) against the data file: absent when the data has none; when present,
    right after the verdict and outside it, labelled "exploratory, after the results" and "not part of the
    pre-registered verdict"; accepted only with complete results, every cell exactly the data's (each arm minus budget,
    the runs, the spread); refused, no number of it at all (only the fixed problem codes)."""
    from common import NA, fmt
    from learning_page import PATH
    X, el, bad = L.get("explore"), ids.get("learning-explore"), []
    if X is None:
        return [f"{PATH}: an exploratory block without exploratory data"] if el is not None else []
    if el is None:
        return [f"{PATH}: exploratory data but no exploratory block"]
    verdict = ids.get("learning-verdict-section")
    if verdict is None or nodes.index(el) < nodes.index(verdict) or any(a is verdict for a in ancestors(el)):
        bad.append(f"{PATH}: the exploratory block is not after the verdict, apart from it")
    text = " ".join(text_of(el).split()).lower()
    label = next((n for n in walk(el) if "lp-explore-label" in n.attrs.get("class", "").split()), None)
    label = " ".join(text_of(label).split()).lower() if label else ""
    if "exploratory, after the results" not in label or "not part of the pre-registered verdict" not in label:
        bad.append(f"{PATH}: the exploratory block is not labelled as exploratory, after the results")
    cells = [n for n in walk(el) if n.tag == "td"]
    if not X.get("accepted"):
        if set(X) - {"accepted", "problems"}:
            bad.append(f"{PATH}: a refused exploratory file publishes more than its problem codes")
        if cells or "exploratory file not accepted" not in text:
            bad.append(f"{PATH}: a refused exploratory file shows numbers or no refusal note")
        return bad
    if not complete:
        bad.append(f"{PATH}: exploratory block shown before the results are complete")

    def want(n):
        a = n.attrs
        if "data-cp" in a:
            s = X["arm_minus_budget"][a["data-arm"]][a["data-cp"]][a["data-m"]]
            return f'{fmt(s["mean"], 1, signed=True)} [{fmt(s["ci"][0], 1)}, {fmt(s["ci"][1], 1)}]'
        if "data-run" in a:
            v = X["runs"][int(a["data-run"])][a["data-k"]]
            return f"{v:,}" if a["data-k"] in ("answered", "valid", "invalid", "failed") else (
                NA if v is None else fmt(v, 1))
        if "data-group" in a:
            s = X["spread"][a["data-group"]]
            if a.get("data-k") == "n":
                return f'{s["risks_found"]["n"]:,}'
            s = s[a["data-m"]]
            sd = fmt(s["sd"], 2) if s["sd"] is not None else NA
            return f'{fmt(s["mean"], 1)} ({fmt(s["min"], 1)}-{fmt(s["max"], 1)}; SD {sd})'
        if "data-rspread" in a:  # the retests' own range under their rows (r1-r5 only)
            s = X["spread"]["retests"][a["data-rspread"]]
            sd = fmt(s["sd"], 2) if s["sd"] is not None else NA
            return f'{fmt(s["min"], 1)}-{fmt(s["max"], 1)} (SD {sd})'
        if "data-agree" in a:
            s = X["agreement"]["summary"][a["data-agree"]]
            return {"n": lambda: fmt(s["n"], 0), "mean": lambda: fmt(s["mean"], 1),
                    "range": lambda: f'{fmt(s["min"], 0)}-{fmt(s["max"], 0)}',
                    "sd": lambda: fmt(s["sd"], 2) if s["sd"] is not None else NA}[a["data-k"]]()
        return None
    seen = set()
    for n in cells:
        try:
            w = want(n)
        except (KeyError, IndexError, ValueError, TypeError):
            bad.append(f"{PATH}: an exploratory cell names no value of the data file")
            continue
        if w is not None:
            seen.add(tuple(sorted(n.attrs.items())))
            if text_of(n).strip() != w:
                bad.append(f"{PATH}: exploratory cell {text_of(n).strip()!r} is not the data's {w!r}")
    expected = (sum(len(m) for cp in X["arm_minus_budget"].values() for m in cp.values())
                + len(X["runs"]) * 9 + len(X["spread"]) * 6 + len(X["agreement"]["summary"]) * 4
                + (3 if "retests" in X["spread"] else 0))
    if len(seen) != expected:
        bad.append(f"{PATH}: the exploratory tables show {len(seen)} of the data's {expected} values")
    # "T0 differs from the later empty-context runs" only where the counts say so: every T0-vs-retest count above
    # every retest-vs-retest count.
    G = X["agreement"]["summary"]
    if "t0 differs from the later empty-context runs" in text and not (
            G["T0 vs retests"]["n"] and G["T0 vs retests"]["min"] > G["retest vs retest"]["max"]):
        bad.append(f"{PATH}: 'T0 differs from the later empty-context runs' is not what the agreement counts show")
    return bad



def check_learning(out: Path, test_set: Path | None = None) -> list[str]:
    """The learning page (learning_page.py; plan §9): (a) no verdict, learning lift, signal or Learning-tab leaders
    block, in the page or its data file, unless the site accepted the results as complete; (b) no evaluation-set
    position (id, board key or board) in the page or its data file. (b) needs the private test set
    (learning_page.TEST_SET) whenever results, a validation or lessons are present: missing or unreadable is a failure,
    not a skip; only the no-results state passes without it. (c) Outside pre-registration-only mode, the results view
    against its data file (_learning_results: status line, charts and tables, verdict, names, lessons, exploratory)."""
    from learning_page import COMPLETE_ONLY_IDS, COMPLETE_ONLY_KEYS, DATA, PATH, TEST_SET
    test_set = test_set or TEST_SET
    page, data = out / PATH / "index.html", out / DATA
    if not page.exists():
        return []
    bad = []
    L = json.loads(data.read_text())
    tree = Tree()
    tree.feed(page.read_text())
    if not ((L["results"] or {}).get("complete") and (L.get("validation") or {}).get("complete")):
        ids = {n.attrs.get("id") for n in walk(tree.root)}
        bad += [f"{PATH}: block #{i} shown before the results are complete" for i in COMPLETE_ONLY_IDS if i in ids]
        bad += [f"{DATA}: {k} published before the results are complete" for k in COMPLETE_ONLY_KEYS
                if k in (L["results"] or {})]
    if not L.get("preregistration_only"):
        bad += _learning_results(tree.root, L)
        if L["results"] is not None and bool(L["results"].get("complete")) != bool(
                (L.get("validation") or {}).get("complete")):
            bad.append(f"{DATA}: results.complete and validation.complete disagree")
    no_results = L.get("results") is None and not L.get("validation") and not L.get("lessons")
    try:
        strings = _test_set_strings(test_set)
    except (OSError, ValueError, KeyError) as e:
        if not no_results:
            bad.append(f"{PATH}: results or lessons present but the evaluation set is missing or unreadable "
                       f"({type(e).__name__}): the leakage check cannot run")
        return bad
    texts = {PATH: html.unescape(page.read_text()), DATA: data.read_text()}
    for s in strings:
        hit = re.compile(r"(?<![\w-])" + re.escape(s) + r"(?!\w)")
        bad += [f"{name}: evaluation-set position {s[:24]!r}\u2026" for name, t in texts.items() if hit.search(t)]
    return bad


# --- 8. Did they improve? -----------------------------------------------------------------------------------

def _improve_expect(m: dict) -> dict:
    """Before, after, change, range, threshold and the verdict of one model, recomputed here from the data file's own
    tests (plan sections 2, 6 and 7), independently of improve_validate."""
    from improve_validate import EMPTY_RUNS, FLOOR, GAMES, POSITIONS, SAFETY_DROP, SERIES

    def mean(xs):
        return sum(xs) / len(xs) if xs and None not in xs else None
    t10 = [s["t10"] for s in m["series"] if s["t10"] is not None]
    keys = ("risks_found", "right_safety", "error_rate")
    before = {k: mean([t[k] for t in m["empty"]]) for k in keys}
    after = {k: mean([t[k] for t in t10]) for k in keys}
    change = {k: after[k] - before[k] if None not in (after[k], before[k]) else None for k in keys}
    rf = [t["risks_found"] for t in m["empty"]]
    rng = max(rf) - min(rf) if len(rf) == EMPTY_RUNS and None not in rf else None
    thr = max(rng, FLOOR) if rng is not None else None
    full = [t["answered"] == POSITIONS and t["failed"] == 0 and None not in (t[k] for k in keys)
            for t in m["empty"] + t10]
    gate = (m["state"] == "complete" and len(m["empty"]) == EMPTY_RUNS and len(m["series"]) == SERIES
            and all(s["finished"] and s["games"] == GAMES and len(s["lessons"]) == GAMES for s in m["series"])
            and len(t10) == SERIES and all(full))
    improved = (round(change["risks_found"], 9) > round(thr, 9) and round(change["right_safety"], 9) >= -SAFETY_DROP
                if gate else None)
    return dict(before=before, after=after, change=change, range=rng, threshold=thr, gate=gate, improved=improved)


def check_improve(out: Path, test_set: Path | None = None) -> list[str]:
    """The "Did they improve?" page (improve_page.py) against its data file: (a) every phrase the pre-registration
    requires is on the page (the commitment line, the rule's "operational threshold" sentence, the seed line, every
    plan model with its label, the not-tested groups, the pilot row and "not comparable (different design)", the
    notes, the lesson prompt's and the test set's hashes); (b) one row per plan model, sorted by the change in risks
    found, rows without a change after; (c) no Yes/No for a model before its verdict gate passes, every shown number
    the one recomputed here from the data's tests; no results block in pre-registration-only mode; (d) no test
    position (id, board key or board) in the page or its data file: the private test set is required whenever
    results or a validation are present."""
    from common import NA, fmt
    from improve_page import COMMITMENT, DATA, PATH, REQUIRED, TEST_SET
    page, data = out / PATH / "index.html", out / DATA
    if not page.exists():
        return []
    bad, L = [], json.loads(data.read_text())
    tree = Tree()
    tree.feed(page.read_text())
    nodes = list(walk(tree.root))
    text = " ".join(text_of(tree.root).split())
    plan = L["plan"]
    want = [COMMITMENT, *REQUIRED, plan["seed_line"] or "(seed line missing in the plan)", plan["prompt_sha256"],
            plan["test_set_sha256"], "Cygnet"]
    want += [m["setup"] for m in plan["models"]] + [m["label"] for m in plan["models"] if m["label"]]
    bad += [f"{PATH}: missing the pre-registered text {w!r}" for w in want if w not in text]
    # The page names no host or device and shows no withheld mark (improve_page.HOST_REWRITES).
    raw = page.read_text() + data.read_text()
    bad += [f"{PATH}: names a host or shows a withheld mark ({w!r})" for w in ("withheld", "bariton", "GPU-")
            if w in raw.replace("[name withheld]", "")]
    rows = [n for n in nodes if n.tag == "tr" and n.attrs.get("data-setup")]
    setups = [n.attrs["data-setup"] for n in rows]
    if sorted(setups) != sorted(m["setup"] for m in plan["models"]):
        bad.append(f"{PATH}: the model table is not one row per plan model")
    # The results table at the top (Ümit #3219, #3710): one row per plan model, finished first (by the change in risks
    # found, largest first), then started, then not started; each status cell the data's progress (a model the data
    # does not list: not started), every cell unknown when the data was refused; its numbers and Yes/No the ones
    # recomputed here. Planned rows (content/improve_planned.json): no number in any cell.
    prog = {m["setup"]: m for m in (L.get("progress") or {}).get("models", [])}
    results = None if L.get("preregistration_only") else L.get("results")
    by = {m["setup"]: m for m in (results or {}).get("models", [])}
    prows = [n for n in nodes if n.tag == "tr" and n.attrs.get("data-progress-setup")]
    psetups = [n.attrs["data-progress-setup"] for n in prows]
    if sorted(psetups) != sorted(m["setup"] for m in plan["models"]):
        bad.append(f"{PATH}: the results table is not one row per plan model")

    def rank(s):
        m, p = by.get(s), prog.get(s)
        if m is not None and _improve_expect(m)["gate"] and not results.get("dry_run"):
            return (0, -m["change"]["risks_found"])
        return (1, 0) if p is not None and p["status"] != "not started" and not L.get("progress_refused") else (2, 0)
    ranks = [rank(s) for s in psetups]
    if ranks != sorted(ranks):
        bad.append(f"{PATH}: the results table is not finished (by change), then running, then not started")
    for n in prows:
        s = n.attrs["data-progress-setup"]
        cells = {c.attrs["data-progress"]: " ".join(text_of(c).split()) for c in walk(n) if c.attrs.get("data-progress")}
        p = prog.get(s)
        if L.get("progress_refused"):
            want_s, want_d = NA, NA
        elif p is None:
            want_s, want_d = "not started", "0 / 5"
        else:
            want_s = p["status"] + (f' ({p["reason"]})' if p["reason"] else "")
            want_d = f'{p["series_done"]} / 5'
        if cells.get("status") != want_s or cells.get("series") != want_d:
            bad.append(f"{PATH}: {s}: status row not what the data gives")
        rcells = {c.attrs["data-rcell"]: " ".join(ordered_text(c).split()) for c in walk(n) if c.attrs.get("data-rcell")}
        rv = next((c.attrs["data-rverdict"] for c in walk(n) if c.attrs.get("data-rverdict")), None)
        m = by.get(s)
        if m is None:
            if rcells or rv:
                bad.append(f"{PATH}: {s}: results-table numbers without validated results")
            continue
        e = _improve_expect(m)
        g = lambda v, signed=False: fmt(v, 1, signed=signed) if v is not None else NA  # noqa: E731
        want = {"rf": f"{g(e['before']['risks_found'])} → {g(e['after']['risks_found'])}",
                "rf-change": g(e["change"]["risks_found"], True),
                "rs": f"{g(e['before']['right_safety'])} → {g(e['after']['right_safety'])}"}
        if rcells != want:
            bad.append(f"{PATH}: {s}: results-table cells {rcells!r}, the data gives {want!r}")
        if rv != (("yes" if e["improved"] else "no") if e["gate"] and not results.get("dry_run") else None):
            bad.append(f"{PATH}: {s}: results-table Yes/No {rv!r} not what the data gives")
    for n in (n for n in nodes if n.tag == "tr" and n.attrs.get("data-planned")):
        if any(re.search(r"\d", text_of(c)) for c in [c for c in walk(n) if c.tag == "td"][2:]):
            bad.append(f"{PATH}: planned row {n.attrs['data-planned']}: shows a number")

    changes = [by[s]["change"]["risks_found"] if s in by else None for s in setups]
    seen_none = False
    for i, c in enumerate(changes):
        seen_none |= c is None
        if c is not None and (seen_none or (i and changes[i - 1] is not None and changes[i - 1] < c)):
            bad.append(f"{PATH}: rows not sorted by the change in risks found (rows without a change after)")
            break
    if results is None:
        if any(n.attrs.get("data-verdict") or n.attrs.get("data-cell") for n in nodes) or any(
                n.attrs.get("id") == "improve-lessons" for n in nodes):
            bad.append(f"{PATH}: results shown without validated results")
    for n in rows:
        m = by.get(n.attrs["data-setup"])
        verdict = next((c for c in walk(n) if c.attrs.get("data-verdict")), None)
        if m is None:
            if verdict is not None:
                bad.append(f"{PATH}: {n.attrs['data-setup']}: a verdict without data")
            continue
        e = _improve_expect(m)
        if verdict is not None and (not e["gate"] or L["results"].get("dry_run")
                                    or verdict.attrs["data-verdict"] != ("yes" if e["improved"] else "no")):
            bad.append(f"{PATH}: {m['setup']}: verdict {verdict.attrs['data-verdict']!r} not what the data gives")
        if verdict is None and e["gate"] and not L["results"].get("dry_run"):
            bad.append(f"{PATH}: {m['setup']}: complete past the gate, but no verdict")
        cells = {c.attrs["data-cell"]: " ".join(ordered_text(c).split()) for c in walk(n) if c.attrs.get("data-cell")}

        def f(v, signed=False):
            return fmt(v, 1, signed=signed) if v is not None else NA
        expect = {"rf": f"{f(e['before']['risks_found'])} → {f(e['after']['risks_found'])}",
                  "rf-change": f(e["change"]["risks_found"], True), "range": f(e["range"]),
                  "threshold": f(e["threshold"]),
                  "er": f"{f(e['before']['error_rate'])} → {f(e['after']['error_rate'])}"}
        for k, v in expect.items():
            if cells.get(k) != v:
                bad.append(f"{PATH}: {m['setup']}: cell {k} is {cells.get(k)!r}, the data gives {v!r}")
    no_results = L.get("results") is None and not L.get("validation")
    try:
        strings = _test_set_strings(test_set or TEST_SET)
    except (OSError, ValueError, KeyError) as e:
        if not no_results:
            bad.append(f"{PATH}: results present but the test set is missing or unreadable ({type(e).__name__}): "
                       "the leakage check cannot run")
        return bad
    texts = {PATH: html.unescape(page.read_text()), DATA: data.read_text()}
    for s in strings:
        hit = re.compile(r"(?<![\w-])" + re.escape(s) + r"(?!\w)")
        bad += [f"{name}: test position {s[:24]!r}\u2026" for name, t in texts.items() if hit.search(t)]
    return bad


def run(S: dict, out: Path) -> list[str]:
    failures = []
    nums = allowed_numbers(out, S)
    # The per-league, per-phase views load as fragments into the Leagues page (the home page's until Ümit #2938):
    # checked as part of it.
    pages = [(p, p) for p in sorted(out.rglob("index.html"))] + [(p, out / "leagues/index.html")
                                                                 for p in sorted((out / "fragments").glob("*.html"))]
    for page, base in pages:
        rel = page.relative_to(out)
        tree = Tree()
        tree.feed(without_suite_bar(page.read_text()))
        # archive/: the page that was live before the switch, frozen with its own data file; results/<id>/: fixed
        # snapshots of earlier results (cited elsewhere), frozen with their own data/. Only their links and the
        # private-data scan apply (their numbers trace to their own data files, not to the current data/).
        if rel.parts[0] not in ("archive", "results"):
            failures += check_numbers(rel, tree.root, nums)
            failures += check_mixing(rel, tree.root, S)
        failures += [f.replace(str(base), str(rel)) for f in check_links(base, tree.root, out, anchors=page == base)]
    failures += check_counts(S)
    for p in out.rglob("*"):
        if not p.is_file() or p.suffix == ".png":
            continue
        m = scan_file(p)
        if m:
            failures.append(f"{p.relative_to(out)}: banned string {m.group(0)!r}")
    failures += findings.failures(out)
    failures += check_learning(out)
    failures += check_improve(out)
    failures += check_palette()
    return failures


def check_palette() -> list[str]:
    """content/maker_palette.json is the three sites' shared palette unchanged: its sha256 is the one
    maker_colors.json records (Ümit #3635; logic #3668)."""
    want = json.loads((CONTENT / "maker_colors.json").read_text())["palette_sha256"]
    got = hashlib.sha256((CONTENT / "maker_palette.json").read_bytes()).hexdigest()
    return [] if got == want else [f"content/maker_palette.json: sha256 {got}, not the shared palette's {want}"]
