"""Pre-deploy checks of a built site (brief B1). run() returns a list of failures; empty means deployable.

1. Numbers trace to data files: every number in the text of every page appears, as printed, among the values
   of the data files under data/ or the content files (tools/site/content/: thresholds, setups metadata,
   human scale, method experiments, archived earlier-page sections), allowing the formats the pages use
   (decimals, percentages, thousands separators, signs). Dates and times are taken out first.
2. Counts add up: per league, setup decisions sum to the league's decisions and match the snapshot; invalid +
   valid = decisions; risk cells and phase cells sum to the scored decisions; standings played = 2 x matches
   finished; the v1 set is setups x positions; exported decisions match the engine-scored decisions; the B6 marks
   on Every decision match the 2x2 counts.
3. No mixing: no table holds rows of two datasets; v1 rows only inside an Earlier-version block; every block
   of a league that has not finished says "Provisional: league still running".
4. No private addresses or credentials (B7): hostnames, IPs, ports, server paths, keys, tokens, request headers,
   the other benchmark's name, in any output file including the decompressed decision files.
5. Every relative link resolves; ids are unique per page and every #anchor exists.
6. Every published finding still holds (B4): findings.py reruns each finding's machine check on the built data.
"""

import gzip
import json
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path

import findings
from common import BANNED, CONTENT, PROVISIONAL, PROVISIONAL_NOTE

NUM = re.compile(r"(?<![\w.\u2212+-])([\u2212+-]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)?|\b\d{1,2}:\d{2}\b|"
                  r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December)"
                  r"(?: \d{4})?|\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}"
                  r"|\b\d{1,2} (?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.text = tag, dict(attrs), parent, [], []


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


def walk(n):
    yield n
    for c in n.children:
        yield from walk(c)


def text_of(n) -> str:
    return "".join(t for x in walk(n) if x.tag not in ("script", "style") for t in x.text)


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
                            JOIN league_matches lm ON lm.match_id = g.match_id
                            WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')""", (lg["id"],)).fetchone()[0]
        su = sum(s["quality"]["decisions"] for s in lg["setups"].values())
        if not (n == su == lg["decisions"]):
            bad.append(f"league {lg['id']}: snapshot {n}, setups sum {su}, league {lg['decisions']} decisions")
        if sum(s["quality"]["engine_scored"] for s in lg["setups"].values()) != lg["scored"]:
            bad.append(f"league {lg['id']}: engine-scored decisions do not add up")
        played = sum(t["played"] for t in lg["standings"])
        if played != 2 * lg["matches_done"]:
            bad.append(f"league {lg['id']}: standings played {played} != 2 x {lg['matches_done']} finished matches")
    snap.close()
    sets = [(lg["dataset"], lg["setups"]) for lg in S["leagues"]] + [("v1-set", S["v1"]["setups"])]
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
        if len(ds) > 1:
            bad.append(f"{page}: {what} mixes datasets {sorted(ds)}")
        if in_v1 and ds - {"v1-set"}:
            bad.append(f"{page}: {what} in an Earlier-version block holds v3 rows {sorted(ds - {'v1-set'})}")
        if "v1-set" in ds and not in_v1:
            bad.append(f"{page}: v1 rows outside an Earlier-version block")
        for r in ds & running:
            if not any(PROVISIONAL_NOTE in text_of(a) for a in ancestors(t) if a.attrs.get("data-dataset") == r
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


def run(S: dict, out: Path) -> list[str]:
    failures = []
    nums = allowed_numbers(out, S)
    # The home page's per-league, per-phase views load as fragments into the home page: checked as part of it.
    pages = [(p, p) for p in sorted(out.rglob("index.html"))] + [(p, out / "index.html")
                                                                 for p in sorted((out / "fragments").glob("*.html"))]
    for page, base in pages:
        rel = page.relative_to(out)
        tree = Tree()
        tree.feed(page.read_text())
        # archive/: the page that was live before the switch, frozen with its own data file; only its links and the
        # private-data scan apply (its numbers are that day's and trace to its v3-results.json, not to data/).
        if rel.parts[0] != "archive":
            failures += check_numbers(rel, tree.root, nums)
            failures += check_mixing(rel, tree.root, S)
        failures += [f.replace(str(base), str(rel)) for f in check_links(base, tree.root, out, anchors=page == base)]
    failures += check_counts(S)
    for p in out.rglob("*"):
        if not p.is_file() or p.suffix == ".png":
            continue
        data = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
        m = BANNED.search(data.decode("utf-8", "replace"))
        if m:
            failures.append(f"{p.relative_to(out)}: banned string {m.group(0)!r}")
    failures += findings.failures(out)
    return failures
