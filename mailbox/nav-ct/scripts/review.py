"""nav-ct review packet (Ümit #2901, #2904, #2907): numbers, old URLs and anchors, browser tests, screenshots, from the
nav-ct render, the leaderboard-ct (base) render of the same state and the live mirror; reads only.
Method of mailbox/leaderboard-ct/scripts/review.py, adapted to the new header, pages, details box and type filter.
Usage: review.py WORKTREE BASE_COMMIT LIVE_DIR BASE_RENDER_DIR NAV_RENDER_DIR OUT_DIR
Exits 1 if any number differs or any check is not in an accepted state.
Writes OUT_DIR/{source.patch, numbers.csv, numbers.md, page-diffs.md, urls.csv, urls.md, browser.csv, browser.md,
header-heights.md, screenshots/}. No HTTP server: file:// for most browser tests; Playwright request routing where a
page's script fetches (Every decision; the old-address comparison, as in leaderboard-ct's review)."""
import csv
import difflib
import json
import mimetypes
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

work, base_commit = Path(sys.argv[1]), sys.argv[2]
live, baser, nav, pk = (Path(a) for a in sys.argv[3:7])
pk.mkdir(parents=True, exist_ok=True)
git = lambda *a: subprocess.run(["git", "-C", str(work), *a], check=True, capture_output=True, text=True).stdout
CONTENT = work / "tools/site/content"

# --- 1. Source diff -----------------------------------------------------------------------------------------------
# The tree against the base (two dots): this change, plus the mobile fix's bg.css hunk that the rebase onto main kept.
(pk / "source.patch").write_text(git("diff", base_commit, "HEAD", "--", "tools/site"))


# --- 2. Numbers ---------------------------------------------------------------------------------------------------
def soup(root: Path, path=""):
    return BeautifulSoup((root / path / "index.html").read_text(), "html.parser")


NUM = re.compile(r"[\u2212-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: [x.replace(",", "").replace("\u2212", "-") for x in NUM.findall(t)]
norm = lambda t: " ".join(t.split())


def table_cells(s, skip=()) -> dict:
    """Every table cell, keyed by its table (nearest id, dataset, margin, caption), its row (dataset, setup, first cell)
    and its column header: a value is compared only with the value under the same labels."""
    out, seen = {}, Counter()
    for t in s.find_all("table"):
        if t.get("id") in skip:
            continue
        anc = [a.get("id") for a in t.parents if getattr(a, "get", None) and a.get("id")]
        cap = norm(t.caption.get_text(" ")) if t.caption else ""
        tkey = (anc[0] if anc else "", t.get("data-dataset", ""), t.get("data-margin", ""), cap)
        seen[tkey] += 1
        tkey += (seen[tkey],)
        head = [norm(th.get_text(" ")) for th in (t.thead.find_all("th") if t.thead else [])]
        rows = Counter()
        for tr in (t.tbody.find_all("tr", recursive=False) if t.tbody else []):
            cells = tr.find_all(["td", "th"], recursive=False)
            rk = (tr.get("data-dataset", ""), tr.get("data-setup", ""), norm(cells[0].get_text(" ")) if cells else "")
            rows[rk] += 1
            for i, c in enumerate(cells):
                out[(tkey, rk + (rows[rk],), head[i] if i < len(head) else str(i))] = norm(c.get_text(" "))
    return out


L, B, N = soup(live), soup(baser), soup(nav)
rows_csv, summary = [], []

# 2a. Every table cell of the live home page and of the base render against nav-ct; the headline table in 2b.
lt, bt, nt = (table_cells(x, skip=("headline-table",)) for x in (L, B, N))
for name, ref in (("live", lt), ("leaderboard-ct render", bt)):
    diff_t = [k for k in ref if nt.get(k) != ref[k]]
    extra = [k for k in nt if k not in ref]
    for k in sorted(ref, key=str):
        (tid, ds, margin, cap, _), (rds, setup, nm_, _), col = k
        if nt.get(k) != ref[k] or name == "live":
            rows_csv.append([f"home table cell vs {name}", tid or cap[:60], rds or ds, setup or nm_, col, ref[k],
                             nt.get(k, "MISSING"), "equal" if nt.get(k) == ref[k] else "DIFF"])
    for k in extra:
        rows_csv.append([f"home table cell (nav-ct only) vs {name}", k[0][0] or k[0][3][:60], k[1][0], k[1][1] or k[1][2],
                         k[2], "", nt[k], "new"])
    summary.append((f"Home page: every {name} table cell, by table, row and column (every tab, both margins, All "
                    "leagues and each league, the All setups panel, Leagues block, Close choices, Nackgammon; the "
                    "leaderboard in the next rows)", len(ref), len(diff_t), len(extra)))

# 2b. The leaderboard: every row's bar score and interval against the live All leagues Risk table (same setup, same
# label), and every value of every details box against the data files (independently of story.py).
def live_col(pred, col):
    out = {}
    for (tkey, rkey, head), v in lt.items():
        if pred(tkey) and head == col:
            out.setdefault((rkey[0] or tkey[1], rkey[1]), v)
    return out


risk_all = lambda col: live_col(lambda t: t[0] == "panel-risk" and t[1] == "all" and t[2] == "0.001", col)
LIVE_J = risk_all("Risk judgement")
hl = N.select_one("#headline-table")
data = nav / "data"
setups_meta = json.loads((data / "setups.json").read_text())["setups"]
makers = json.loads((CONTENT / "maker_colors.json").read_text())["setups"]
releases = json.loads((CONTENT / "release_months.json").read_text())["models"]
identity = json.loads((CONTENT / "model_identity.json").read_text())["same_model"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
leagues = {f"league-{i}": json.loads((data / "v3" / f"league-{i}.json").read_text()) for i in (1, 2, 3)}


def setup_file(ds, slug):
    f = data / "v3" / ds / f"{slug}.json"
    return json.loads(f.read_text()) if f.is_file() else None


def meta_of(ds, slug):
    m = [x for x in setups_meta if x["slug"] == slug and x["dataset"] == ds] or \
        [x for x in setups_meta if x["slug"] == slug and x["dataset"].startswith("league-")]
    return m[0] if m else None


def r1(x, d=1):
    return f"{x:,.{d}f}"


def pc(share):
    return f"{share * 100:.1f}%"


def cnt(x):
    return f"{int(round(x)):,}" if abs(x - round(x)) < 1e-6 else f"{x:,.1f}"


def expected_box(ds, slug, sub, parent_name):
    """The lines a setup's details box must show, from data/ (the setup's file, its league's standings, setups.json)
    and content/ (makers, release months): each line or part left out where the data has no value."""
    d = setup_file(ds, slug)
    if d is None:  # a computed reference row (Random / Safest computed): its row in the league file's references
        d = next(v for v in leagues[ds]["references"].values() if v.get("slug") == slug)
    m = meta_of(ds, slug) or {}
    r, q = d["risk"]["main"], d.get("quality")
    name = d["name"]
    j = lambda parts: " · ".join(p for p in parts if p)
    st = next((s for s in leagues[ds]["standings"] if s["name"] == name), None)
    er = (f"Error rate {r1(q['error_rate'])} (95%: {r1(q['error_lo'])}–{r1(q['error_hi'])})"
          if q and q.get("error_rate") is not None and not q.get("too_few") else None)
    cost = None
    if q and q.get("usd_per_1000") is not None:
        lab = (m.get("price") or {}).get("label")
        cost = f"${q['usd_per_1000']:,.3f} per 1,000 decisions" + (f" ({lab})" if lab else "")
    f, s = r["found"], r["right_safety"]
    prog = m.get("model_type") == "program" or d.get("slug") in ("random-computed", "safest-computed") or name in ("GNUbg weak", "Random", "Safest") or name.endswith("(computed)")
    lines = [j([name, None if prog else makers.get(name)]),
             j([f"Setting {m['setting']}" if m.get("setting") else None, f"League {ds.split('-')[1]}"]),
             f"Risk judgement {r1(r['judgement'])} (95%: {r1(r['judgement_lo'])}–{r1(r['judgement_hi'])})" if r.get("judgement") is not None else None,
             j([f"Risks found {pc(f['share'])}" if f["den"] else None, f"safe right {pc(s['share'])}" if s["den"] else None]),
             j([f"Took {cnt(f['n'])} of {cnt(f['den'])} risks that paid" if f["den"] else None,
                f"played safe in {cnt(s['n'])} of {cnt(s['den'])} positions where safe paid" if s["den"] else None]),
             j([er, f"record {st['won']}–{st['drawn']}–{st['lost']}" if st else None]),
             j([cost, f"{q['decisions']:,} decisions" if q else None])]
    if not sub and not prog:
        e = releases.get(parent_name) or {}
        if e.get("month"):
            y, mo = e["month"].split("-")
            lines.append(f"Released {MONTHS[int(mo) - 1]} {y}")
        ck = sorted({x for x, base in identity.items() if base == parent_name})
        if ck:
            lines.append("With its dated checkpoint " + ", ".join(ck) + " (under the expander)")
    links = j(["Open its decisions →" if q else None, "Model page" if q else None])
    lines.append(links)
    return [x for x in lines if x]


def shown_box(box):
    b2 = BeautifulSoup(str(box), "html.parser")
    for x in b2.select(".cost-1m"):
        x.decompose()
    return [norm(p.get_text(" ").replace(" ·", " ·")) for p in b2.select("p")]


bx_n = bx_d = j_n = j_d = 0
box_rows = []
parent = None
for tr in hl.tbody.find_all("tr", recursive=False):
    if not tr.get("data-setup"):
        continue
    ds, slug = tr["data-dataset"], tr["data-setup"]
    sub = "hl-sub" in (tr.get("class") or [])
    if not sub:
        parent = norm(tr.select_one(".model-name").get_text(" "))
    box = tr.select_one(".hl-box")
    got = [re.sub(r"\s+·", " ·", x) for x in shown_box(box)]
    want = expected_box(ds, slug, sub, parent)
    for i in range(max(len(got), len(want))):
        g, w = (got[i] if i < len(got) else "MISSING"), (want[i] if i < len(want) else "EXTRA")
        ok = g == w
        bx_n += 1
        bx_d += not ok
        rows_csv.append(["details box line" + (" (other setting)" if sub else ""), f"line {i + 1}", ds, slug, "text", w, g,
                         "equal" if ok else "DIFF"])
    # The row's own bar value (score and 95% interval) against the live All leagues Risk table, same setup.
    cell = norm(tr.select_one("td.hl-judgement, td.num:last-child").get_text(" "))
    exp = LIVE_J.get((ds, slug))
    ok = exp is not None and nums(cell) == nums(exp)
    j_n += 1
    j_d += not ok
    rows_csv.append(["leaderboard row: risk judgement (95% interval)", "row", ds, slug, "Risk judgement", exp, cell,
                     "equal" if ok else "DIFF"])
    box_rows.append((ds, slug, sub))
summary.append(("Leaderboard rows (ranked, other settings, programs): the risk judgement and its 95% interval against "
                "the live All leagues Risk table, same setup and label", j_n, j_d, 0))
summary.append(("Details boxes: every line of every row's box (setup and maker, setting and league, risk judgement and "
                "interval, risks found and safe right, took n of N and played safe m of M, error rate and interval, "
                "record, cost with its price label and decisions, release month, links) against the data files "
                "(data/v3/<league>/<setup>.json, data/v3/<league>.json standings, data/setups.json, content makers and "
                "release months), text equal", bx_n, bx_d, 0))

# 2c. The same box values, label by label, against the live page's own tables (the live All leagues Risk table for the
# risk numbers; the live Quality tab for error rate and cost; the live Cost tab for decisions).
qual = lambda col: live_col(lambda t: t[0] == "panel-quality", col)
LIVE_SRC = {"Risks found": risk_all("Risks found"), "Right safety": risk_all("Right safety"),
            "Error rate": qual("Error rate (PR), 95% interval"), "Cost": qual("$ per 1,000 decisions"),
            "Decisions": live_col(lambda t: t[0] == "panel-cost", "Decisions")}
lv_n = lv_d = 0
for tr in hl.tbody.find_all("tr", recursive=False):
    if not tr.get("data-setup"):
        continue
    k = (tr["data-dataset"], tr["data-setup"])
    text = " | ".join(shown_box(tr.select_one(".hl-box")))
    found = re.search(r"Risks found ([\d.]+)%", text)
    safe = re.search(r"safe right ([\d.]+)%", text)
    took = re.search(r"Took ([\d,.]+) of ([\d,.]+) risks", text)
    played = re.search(r"played safe in ([\d,.]+) of ([\d,.]+) positions", text)
    er = re.search(r"Error rate ([\d.]+) \(95%: ([\d.]+)–([\d.]+)\)", text)
    cost = re.search(r"\$([\d,.]+) per 1,000 decisions(?: \(([^)]*\)?)\))?", text)
    dec = re.search(r"([\d,]+) decisions(?: \||$)", text)
    checks = []
    if k in LIVE_SRC["Risks found"]:
        lf = nums(LIVE_SRC["Risks found"][k])
        checks.append(("Risks found share, n / N", [found.group(1), *took.groups()] if found and took else None, lf[:3]))
        ls = nums(LIVE_SRC["Right safety"][k])
        checks.append(("Right safety share, n / N", [safe.group(1), *played.groups()] if safe and played else None, ls[:3]))
    if k in LIVE_SRC["Error rate"]:
        le = nums(LIVE_SRC["Error rate"][k])
        checks.append(("Error rate and interval", list(er.groups()) if er else (None if le else []), le[:3]))
    if k in LIVE_SRC["Cost"]:
        lc = LIVE_SRC["Cost"][k]
        if re.match(r"\s*[\d,.]+", lc):  # a cost: its value and price label
            checks.append(("$ per 1,000 decisions and price label",
                           [cost.group(1).replace(",", ""), norm(cost.group(2) or "")] if cost else None,
                           [nums(lc)[0], norm(re.sub(r"^\s*[\d,.]+\s*", "", lc))]))
        else:  # no cost on record (e.g. "Priced for 0% of decisions"): the box leaves the cost out
            checks.append((f"no $ per 1,000 decisions (live: {norm(lc)})", [] if cost is None else [cost.group(0)], []))
    if k in LIVE_SRC["Decisions"]:
        checks.append(("Decisions", [dec.group(1).replace(",", "")] if dec else None, nums(LIVE_SRC["Decisions"][k])[:1]))
    for label, got, want in checks:
        got = [g.replace(",", "") if isinstance(g, str) else g for g in got] if got is not None else None
        want = [w.replace(",", "") for w in want]
        ok = got == want
        lv_n += 1
        lv_d += not ok
        rows_csv.append(["details box vs live table", label, k[0], k[1], label, " ".join(want), " ".join(map(str, got or [])),
                         "equal" if ok else "DIFF"])
summary.append(("Details boxes against the live page's own tables, label by label (risks found and right safety: share, "
                "n and N, live All leagues Risk table; error rate and interval and $ per 1,000 with its price label, live "
                "Quality tab; decisions, live Cost tab)", lv_n, lv_d, 0))

# 2d. Too safe, the findings and the measure charts: every value, live (and base) against nav-ct, by setup.
def chart_vals(s, sel):
    out = Counter()
    for li in s.select(sel):
        out[(li.find_parent(["section", "figure"]).get("id"), li.get("data-dataset"), li.get("data-setup"),
             norm(li.get_text(" ")))] += 1
    return out


for label, sel, ref, refname in (
        ("Measure charts (Risk judgement, Error rate, Cost, Time): every bar, label and value", "section.measure li.hbar", L, "live"),
        ("Finding sections: every bar, label and value", "section.finding li.hbar", L, "live"),
        ("Too safe chart: every bar, label and value", "#too-safe li.hbar", B, "leaderboard-ct render")):
    a, c = chart_vals(ref, sel), chart_vals(N, sel)
    summary.append((f"{label}, {refname} against nav-ct", sum(a.values()), sum((a - c).values()), sum((c - a).values())))
    for k in (a - c):
        rows_csv.append(["chart value", k[0], k[1], k[2], "bar", k[3], "MISSING", "DIFF"])

# 2e. Every other page: the main content, byte for byte (live and base against nav-ct); data files.
cut = lambda s: s[s.index('<main id="main"'):s.index("</main>")] if '<main id="main"' in s else s
stamp = lambda s: re.sub(r"updated \d+ \w+ \d{4}, \d\d:\d\d UTC", "updated STAMP", s)
page_diffs = []
for name, ref in (("live", live), ("leaderboard-ct render", baser)):
    o_n = o_d = frozen = 0
    for f in sorted(ref.rglob("index.html")):
        rel = f.relative_to(ref)
        if str(rel) == "index.html":
            continue
        b = nav / rel
        if not b.is_file() and rel.parts[0] in ("archive", "results"):
            frozen += 1
            continue
        a_t, b_t = (stamp(cut(f.read_text())), stamp(cut(b.read_text()))) if b.is_file() else (None, None)
        ok = b.is_file() and a_t == b_t
        o_n += 1
        o_d += not ok
        if not ok:
            rows_csv.append([f"other page vs {name}", str(rel), "", "", "main content", name, "nav-ct", "DIFF"])
            if b_t is not None:
                page_diffs.append(f"## {rel} ({name} against nav-ct)\n\n```diff\n" + "\n".join(difflib.unified_diff(
                    a_t.replace(">", ">\n").splitlines(), b_t.replace(">", ">\n").splitlines(), name, "nav-ct",
                    lineterm="", n=1)) + "\n```\n")
    summary.append((f"Every other page ({name}): the main content, byte for byte after the render time stamp "
                    f"({frozen} frozen snapshots under results/ and archive/ are copied at deploy, not rendered, and left "
                    "out)", o_n, o_d, 0))
for name, ref in (("live", live), ("leaderboard-ct render", baser)):
    d_n = d_d = 0
    for f in sorted((ref / "data").rglob("*")):
        if f.is_file() and f.suffix != ".html":
            d_n += 1
            g = nav / f.relative_to(ref)
            if f.name == "manifest.json":
                ma, mb = json.loads(f.read_text()), json.loads(g.read_text())
                fb = {e["path"]: e for e in mb.get("files", [])}
                bad = ({k: v for k, v in ma.items() if k not in ("data_as_of", "files", "built_at")} !=
                       {k: v for k, v in mb.items() if k not in ("data_as_of", "files", "built_at")}
                       or any(fb.get(e["path"]) != e for e in ma.get("files", [])))
            else:
                bad = not g.is_file() or f.read_bytes() != g.read_bytes()
            d_d += bad
            if bad:
                rows_csv.append([f"data file vs {name}", str(f.relative_to(ref)), "", "", "bytes", name, "nav-ct", "DIFF"])
    summary.append((f"Data files under data/ ({name}), byte for byte (manifest.json: every file entry and every field "
                    "but its generated time)", d_n, d_d, 0))
(pk / "page-diffs.md").write_text("# Other pages: where the main content differs from nav-ct\n\n" +
                                  ("\n".join(page_diffs) or "None.\n"))
with (pk / "numbers.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["what", "where", "dataset", "setup", "label", "reference", "nav-ct", "result"])
    w.writerows(rows_csv)
lines = ["# Numbers: nav-ct render against live and leaderboard-ct", "",
         f"Live: the deployed site's mirror; nav-ct: the render of {git('rev-parse', '--short', 'HEAD').strip()}; "
         f"leaderboard-ct: the render of {base_commit} from the same copy of the live state and results hash. Every "
         "comparison is label-aware: a value is compared with the value of the same setup under the same label (table, "
         "row and column; box line; chart bar). numbers.csv has one line per compared value.", "",
         "| Compared | Values | Differences | New in nav-ct |", "|---|---:|---:|---:|"]
lines += [f"| {w} | {n:,} | {d:,} | {e:,} |" for w, n, d, e in summary]
(pk / "numbers.md").write_text("\n".join(lines) + "\n")
print("numbers:", [(w[:40], n, d, e) for w, n, d, e in summary])


# --- 3. Old URLs and anchors ------------------------------------------------------------------------------------------
def router(root: Path):
    def serve(route):
        path = unquote(urlparse(route.request.url).path).lstrip("/")
        f = root / path
        if f.is_dir():
            f = f / "index.html"
        if not f.is_file():
            return route.fulfill(status=404, body="not found")
        route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or "application/octet-stream")
    return serve


def context(browser, root, width, theme, routed=True, touch=False):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844}, has_touch=touch,
                              is_mobile=touch)
    ctx.add_init_script(f"try {{ localStorage.setItem('theme','{theme}'); }} catch (e) {{}}")  # about:blank has no storage
    if routed:
        ctx.route("http://site.test/**", router(root))
    return ctx


SITE = "http://site.test/"
urls = []
ids = lambda f: {t["id"] for t in BeautifulSoup(f.read_text(), "html.parser").find_all(id=True)}


def header_ids(f):
    """The ids inside the old page header itself (its Part row's label), not part of any page's content."""
    s = BeautifulSoup(f.read_text(), "html.parser")
    return {t["id"] for h in s.select(".site-header, .topbar") for t in h.find_all(id=True)}
# 3a. Every page of live and of the base render is a page of nav-ct, and every id (anchor) on it is still there.
for name, ref in (("live", live), ("leaderboard-ct render", baser)):
    pages_n = anchors_n = 0
    for f in sorted(ref.rglob("index.html")):
        rel = f.relative_to(ref)
        g = nav / rel
        if not g.is_file() and rel.parts[0] in ("archive", "results"):
            continue
        pages_n += 1
        if not g.is_file():
            urls.append(["static", f"page of {name}", str(rel.parent) + "/", "", "MISSING"])
            continue
        old, new, chrome = ids(f), ids(g), header_ids(f)
        lost = sorted(old - new - chrome)
        gone = sorted((old - new) & chrome)
        anchors_n += len(old)
        urls.append(["static", f"page of {name}: the page and every one of its {len(old - chrome)} content ids",
                     str(rel.parent) + "/", (f"lost: {lost[:12]}" if lost else "all kept")
                     + (f"; the old header's own id {gone} went with the old header (a link to it opens the page at "
                        "its top)" if gone else ""), "ok" if not lost else "LOST"])
    print(f"{name}: {pages_n} pages, {anchors_n} anchors checked")
# 3b. The old navigation (the leaderboard-ct pages row and Part row) and the home page's face links, in the browser at
# 1280 and 390: each address loads, its #anchor exists and lands below the sticky header.
old_nav = sorted({a["href"] for a in B.select(".topbar a[href], .site-header a[href]") if not a["href"].startswith("/")} |
                 {a["href"] for a in B.select(".face-nav a[href], .hero-links a[href]")})
deep = ["#leaderboard", "#too-safe", "#finding-cautious", "#finding-flinch", "#how-numbers", "#findings", "#board-panel",
        "#leagues-tabs", "#filters", "#close-choices-stage-b", "#nackgammon-paired", "#downloads", "#risk-judgement",
        "#error-rate", "#cost", "#time", "method/#limits", "method/#prompt", "method/#nackgammon-paired",
        "leagues/#late-entries", "leagues/#nack-knockout", "leagues/#hype-cup", "matches/#stage-knockout",
        "matches/#stage-cup", "data/#recompute", "data/#status", "learning/#learning-prompt", "clear-risk/",
        "?league=league-2#leaderboard", "?type=chat#board", "decisions/?d=league-3&s=gpt-6-astra-off"]
TARGET = """() => {
  const id = decodeURIComponent(location.hash.slice(1));
  const t = id && document.getElementById(id);
  const head = document.querySelector('.site-header').getBoundingClientRect().bottom;
  const box = t && t.getBoundingClientRect();
  return { path: location.pathname + location.search + location.hash, title: document.title,
           target: id ? (t ? ((t.offsetParent || t.getClientRects().length) ? (box.top >= head - 2 && box.top < innerHeight ? 'below the header, in view' : `exists, top ${Math.round(box.top)} vs header ${Math.round(head)}`) : 'hidden') : 'missing') : '',
           tab: [...document.querySelectorAll('.site-tabs a[aria-current]')].map(a => a.textContent).join('|') };
}"""
TAB_OF = {"": "Leaderboard", "decisions/": "Decisions", "highlights/": "Highlights", "experiments/": "Experiments",
          "about/": "About", "clear-risk/": "Experiments", "learning/": "Experiments", "method/": "About", "data/": "About"}
with sync_playwright() as p:
    br = p.chromium.launch()
    for width in (1280, 390):
        ctx = context(br, nav, width, "light")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        for u in old_nav + deep:
            page.goto("about:blank")  # a full load each time (a #-only change would not reload the page)
            resp = page.goto(SITE + u)
            page.wait_for_timeout(250)
            st = page.evaluate(TARGET)
            path = urlparse(u).path
            want_tab = next((v for k, v in TAB_OF.items() if k and path.startswith(k)), "Leaderboard")
            ok = resp.status == 200 and st["target"] in ("", "below the header, in view") and st["tab"] == want_tab
            urls.append([width, "old address in the browser", u, f"{resp.status}; {st['target'] or 'no anchor'}; tab {st['tab']} "
                         f"(expected {want_tab})", "ok" if ok else "WRONG"])
        urls.append([width, "script errors on these addresses", "", "; ".join(errs) or "none", "ok" if not errs else "ERRORS"])
        ctx.close()
    br.close()
with (pk / "urls.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["width", "check", "address", "observed", "result"])
    w.writerows(urls)
uc = Counter(r[-1] for r in urls)
(pk / "urls.md").write_text(
    "# Old URLs and anchors\n\n"
    f"{len(urls)} checks: " + ", ".join(f"{v} {k}" for k, v in sorted(uc.items())) + ". urls.csv has every one.\n\n"
    "Static: every page of the live mirror and of the leaderboard-ct render (frozen archive/ and results/ snapshots "
    "aside, which deploy copies) is a page of nav-ct at the same path, and every id on it (every #anchor) is still on "
    "the nav-ct page. checks.run (checks-run.txt) also resolves every relative link and #anchor of every nav-ct page.\n\n"
    "Browser (1280 and 390 px, request routing, no server): every link of the old navigation (leaderboard-ct's "
    "pages row and Part row) and the home page's part links, and the deep links listed in review.py, opened on nav-ct: "
    "status 200, the #anchor's element exists and its top is below the sticky header, and the tab marked in the header "
    "is the page's tab.\n")
print("urls:", dict(uc))

# --- 4. Browser tests ------------------------------------------------------------------------------------------------
browser_rows = []
heights = []
HEADER = """() => {
  const h = document.querySelector('.site-header'), r = h.getBoundingClientRect();
  const ul = document.querySelector('.site-tabs ul');
  const tabs = [...ul.querySelectorAll('a')];
  const cur = tabs.filter(a => a.hasAttribute('aria-current'));
  const link = getComputedStyle(document.documentElement).getPropertyValue('--link').trim();
  const probe = document.createElement('span'); probe.style.color = link; document.body.append(probe);
  const linkRgb = getComputedStyle(probe).color; probe.remove();
  const style = a => getComputedStyle(a);
  return { top: Math.round(r.top), height: Math.round(r.height), suite: !!h.querySelector('.suite-bar'),
           title: h.querySelector('.site-title').textContent.trim(), leaf: h.querySelector('.site-leaf').naturalWidth > 0,
           tabs: tabs.map(a => a.textContent.trim()), current: cur.map(a => a.textContent.trim()),
           underline: cur.map(a => [style(a).borderBottomColor, style(a).borderBottomWidth, style(a).borderBottomStyle].join(' ')),
           others: tabs.filter(a => !a.hasAttribute('aria-current')).map(a => style(a).borderBottomColor).filter(c => c !== 'rgba(0, 0, 0, 0)').length,
           linkRgb, sticky: style(h).position, scrollW: ul.scrollWidth, clientW: ul.clientWidth, overflowX: style(ul).overflowX,
           curInView: cur.length ? (() => { const a = cur[0].getBoundingClientRect(), b = ul.getBoundingClientRect(); return a.left >= b.left - 1 && a.right <= b.right + 1; })() : null,
           headerRight: Math.round(Math.max(...[...h.querySelectorAll('*')].filter(e => e.closest('.site-tabs ul') === null).map(e => e.getBoundingClientRect().right))),
           vw: document.documentElement.clientWidth };
}"""
PAGES = [("", "Leaderboard"), ("decisions/", "Decisions"), ("highlights/", "Highlights"), ("experiments/", "Experiments"),
         ("about/", "About"), ("method/", "About"), ("data/", "About"), ("clear-risk/", "Experiments"),
         ("learning/", "Experiments"), ("matches/", "Leaderboard"), ("leagues/", "Leaderboard"), ("phases/", "Leaderboard"),
         ("compare/", "Leaderboard"), ("disagreements/", "Leaderboard"), ("models/", "Leaderboard")]
EXPECT_TABS = ["Leaderboard", "Decisions", "Highlights", "Experiments", "About"]

# The type of each ranked row, from data/setups.json (model_type of the row's setup), not from the page.
def kind_of(ds, slug):
    m = meta_of(ds, slug)
    t = (m or {}).get("model_type") or ""
    return "program" if t == "program" else "decision" if t.startswith("decision") else "chat" if t else "unknown"


rows_all = [(tr["data-dataset"], tr["data-setup"]) for tr in hl.tbody.find_all("tr", recursive=False)
            if tr.get("data-setup") and "hl-sub" not in (tr.get("class") or [])]
programs = {k for k in rows_all if "reference" in (hl.find("tr", attrs={"data-dataset": k[0], "data-setup": k[1]}).get("class") or [])}
ranked = [k for k in rows_all if k not in programs]
want_rows = {"all": set(rows_all), "chat": {k for k in ranked if kind_of(*k) == "chat"} | programs,
             "decision": {k for k in ranked if kind_of(*k) == "decision"} | programs}
# Each parent's other-setting rows in the leaderboard-ct render (the approved table): the expander must show them.
fam_base = {}
cur = None
for tr in B.select_one("#headline-table").tbody.find_all("tr", recursive=False):
    if not tr.get("data-setup"):
        continue
    if "hl-sub" in (tr.get("class") or []):
        fam_base[cur].append(f"{tr['data-dataset']}/{tr['data-setup']}")
    else:
        cur = f"{tr['data-dataset']}/{tr['data-setup']}"
        fam_base[cur] = []
VIS = """sel => [...document.querySelectorAll(sel)].filter(e => !!(e.offsetParent || e.getClientRects().length)).map(r => `${r.dataset.dataset}/${r.dataset.setup}`).sort()"""
BOX = """tr => { const b = document.getElementById(tr.dataset.box); const r = b.getBoundingClientRect();
  return { open: getComputedStyle(b).display !== 'none', left: r.left, right: r.right, top: r.top, bottom: r.bottom,
           vw: document.documentElement.clientWidth, vh: innerHeight, text: b.innerText.replace(/\\s+/g, ' ').trim(),
           scrollW: b.scrollWidth, clientW: b.clientWidth }; }"""
static_box = {(tr["data-dataset"], tr["data-setup"], "hl-sub" in (tr.get("class") or [])): " | ".join(shown_box(tr.select_one(".hl-box")))
              for tr in hl.tbody.find_all("tr", recursive=False) if tr.get("data-setup")}
# The box as the reader sees it (innerText: the chosen cost unit only) against the page's box text, spacing aside.
same_text = lambda a, b: re.sub(r"[\s|]", "", a) == re.sub(r"[\s|]", "", b)
with sync_playwright() as p:
    br = p.chromium.launch()
    for width in (1280, 390):
        touch = width < 600
        for theme in ("light", "dark"):
            ctx = context(br, nav, width, theme, routed=True, touch=touch)
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            # 4a. Header on every kind of page: suite strip, leaf, name, the five tabs, the page's tab underlined in the
            # link colour (3 px solid), no other tab underlined, sticky.
            for path, tab in PAGES:
                page.goto(SITE + path)
                page.wait_for_timeout(300)
                h = page.evaluate(HEADER)
                ok = (h["suite"] and h["leaf"] and h["title"] == "Backgammon bench" and h["tabs"] == EXPECT_TABS
                      and h["current"] == [tab] and h["underline"] == [f"{h['linkRgb']} 3px solid"] and h["others"] == 0
                      and h["sticky"] == "sticky" and h["top"] == 0 and h["curInView"] and h["headerRight"] <= h["vw"] + 1)
                browser_rows.append([width, theme, f"header on {path or '(home)'}",
                                     f"tabs {h['tabs']}; marked {h['current']} (expected {tab}); underline {h['underline']} "
                                     f"(link colour {h['linkRgb']}); other tabs underlined {h['others']}; height {h['height']} px; "
                                     f"position {h['sticky']}; marked tab in view {h['curInView']}; header right edge "
                                     f"{h['headerRight']} of {h['vw']} px", "ok" if ok else "WRONG"])
                if path in ("", "about/", "decisions/") and theme == "light":
                    heights.append((width, path or "(home)", h["height"]))
            # 4b. Sticky while scrolling: at the end of the long home and About pages the header is still at the top.
            for path in ("", "about/", "method/"):
                page.goto(SITE + path)
                page.wait_for_timeout(250)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(250)
                h = page.evaluate(HEADER)
                y = page.evaluate("scrollY")
                ok = h["top"] == 0 and y > 1000
                browser_rows.append([width, theme, f"sticky header after scrolling {path or '(home)'} to the end",
                                     f"scrolled {y} px; header top {h['top']} px, height {h['height']} px", "ok" if ok else "WRONG"])
            # 4c. The tab row scrolls sideways on a phone (and fits on one line at 1280), the page itself does not.
            page.goto(SITE + "about/")
            page.wait_for_timeout(300)
            h = page.evaluate(HEADER)
            before = page.eval_on_selector(".site-tabs ul", "u => u.scrollLeft")
            page.eval_on_selector(".site-tabs ul", "u => u.scrollBy(-1000, 0)")
            page.wait_for_timeout(100)
            start = page.eval_on_selector(".site-tabs ul", "u => u.scrollLeft")
            if touch:
                box = page.locator(".site-tabs ul").bounding_box()
                page.mouse.move(box["x"] + box["width"] - 10, box["y"] + box["height"] / 2)
                page.mouse.wheel(400, 0)
                page.wait_for_timeout(200)
            end = page.eval_on_selector(".site-tabs ul", "u => u.scrollLeft")
            overflow = page.evaluate("document.querySelector('.site-header').scrollWidth > document.documentElement.clientWidth + 1")
            ok = (h["overflowX"] == "auto" and not overflow and
                  ((h["scrollW"] > h["clientW"] and before > 0 and end > start) if touch else h["scrollW"] <= h["clientW"]))
            browser_rows.append([width, theme, "tab row: sideways scroll",
                                 f"tab row {h['scrollW']} px of content in {h['clientW']} px, overflow-x {h['overflowX']}; "
                                 f"on About the marked tab was scrolled into view (scrollLeft {before}); scrolled back to "
                                 f"{start}, wheel/swipe to {end}; header wider than the window: {overflow}",
                                 "ok" if ok else "WRONG"])
            # 4d. Leaderboard filter (local): each state's rows = the data's rows of that type, programs in every state.
            page.goto(SITE)
            page.wait_for_timeout(400)
            seen = set()
            for state in ("chat", "decision", "all"):
                page.click(f'[data-hl-filter="{state}"]')
                page.wait_for_timeout(120)
                shown = {tuple(x.split("/")) for x in page.evaluate(VIS, "#headline-table tbody tr[data-setup]:not(.hl-sub)")}
                seen |= shown
                pressed = page.eval_on_selector_all("[data-hl-filter]", "ks => ks.filter(k => k.getAttribute('aria-pressed') === 'true').map(k => k.dataset.hlFilter)")
                ranks = page.evaluate("""() => [...document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub):not(.reference)')].filter(e => e.offsetParent).map(r => [r.dataset.dataset + '/' + r.dataset.setup, r.cells[0].textContent.trim()])""")
                base_rank = {f"{d}/{s}": str(i) for i, (d, s) in enumerate(ranked, 1)}
                ranks_ok = all(base_rank.get(k) == v for k, v in ranks)
                ok = shown == want_rows[state] and pressed == [state] and ranks_ok and programs <= shown
                browser_rows.append([width, theme, f"leaderboard filter: {state}",
                                     f"rows shown {len(shown)} = the data's {state} rows {len(want_rows[state])} "
                                     f"(programs {len(programs & shown)}/{len(programs)}): {shown == want_rows[state]}; key "
                                     f"pressed {pressed}; ranks unchanged (rank among all models) {ranks_ok}",
                                     "ok" if ok else "WRONG"])
                if state != "all":
                    # Expanders in the filtered view: each shown parent's expander shows exactly its rows.
                    bad = []
                    for key in sorted(shown):
                        k = "/".join(key)
                        btn = page.locator(f'#headline-table tr[data-dataset="{key[0]}"][data-setup="{key[1]}"]:not(.hl-sub) .hl-more')
                        if not btn.count():
                            if fam_base.get(k):
                                bad.append(f"{k}: no expander")
                            continue
                        btn.evaluate("b => b.click()")
                        open_ = page.evaluate(VIS, "#headline-table tr.hl-sub")
                        btn.evaluate("b => b.click()")
                        closed = page.evaluate(VIS, "#headline-table tr.hl-sub")
                        if open_ != sorted(fam_base.get(k, [])) or closed:
                            bad.append(f"{k}: shown {open_}")
                    browser_rows.append([width, theme, f"leaderboard filter: {state}: every expander",
                                         "each shown row's expander shows exactly its other settings (as in the "
                                         "leaderboard-ct table) and hides them again" + (f"; WRONG: {bad}" if bad else ""),
                                         "ok" if not bad else "WRONG"])
            ok = seen == set(rows_all)
            browser_rows.append([width, theme, "leaderboard filter: no row lost",
                                 f"rows seen over the three states {len(seen)} = all rows {len(rows_all)}: {ok}", "ok" if ok else "WRONG"])
            # 4e. Details box: every row (ranked and programs; other-setting rows opened through their expander).
            page.goto(SITE)
            page.wait_for_timeout(400)
            bad, n = [], 0
            for tr_key in rows_all:
                sel = f'#headline-table tr[data-dataset="{tr_key[0]}"][data-setup="{tr_key[1]}"]:not(.hl-sub)'
                row = page.locator(sel)
                name = row.locator(".model-name")
                name.scroll_into_view_if_needed()
                if touch:
                    name.tap()
                else:
                    name.hover()
                page.wait_for_timeout(60)
                st = row.evaluate(BOX)
                n += 1
                inside = st["left"] >= 0 and st["right"] <= st["vw"] + 0.5 and st["scrollW"] <= st["clientW"] + 1
                same = same_text(st["text"], static_box[(tr_key[0], tr_key[1], False)])
                if not (st["open"] and inside and same):
                    bad.append(f"{tr_key}: open {st['open']}, {round(st['left'])}–{round(st['right'])} of {st['vw']}, text equal {same}")
                if touch:
                    name.tap()  # a second tap closes it
                    page.wait_for_timeout(60)
                    if row.evaluate(BOX)["open"]:
                        bad.append(f"{tr_key}: second tap left it open")
                else:
                    page.mouse.move(2, 400)
                    page.wait_for_timeout(60)
                    if row.evaluate(BOX)["open"]:
                        bad.append(f"{tr_key}: still open after the pointer left")
            browser_rows.append([width, theme, f"details box: {'tap' if touch else 'hover'} on every row ({n})",
                                 ("opens; inside the window's width, no overflow; text equal to the page's box for that "
                                  "setup (checked against the data files in numbers.md); "
                                  + ("closes on a second tap" if touch else "closes when the pointer leaves"))
                                 + (f"; WRONG: {bad}" if bad else ""), "ok" if not bad else "WRONG"])
            # Other-setting rows: open the expander, then the sub row's box.
            bad = []
            for parent_key, subs in fam_base.items():
                if not subs:
                    continue
                pd, ps = parent_key.split("/")
                page.locator(f'#headline-table tr[data-dataset="{pd}"][data-setup="{ps}"]:not(.hl-sub) .hl-more').evaluate("b => b.click()")
                for sk in subs:
                    sd, ss = sk.split("/")
                    row = page.locator(f'#headline-table tr.hl-sub[data-dataset="{sd}"][data-setup="{ss}"]')
                    nm_ = row.locator(".model-name")
                    nm_.scroll_into_view_if_needed()
                    nm_.tap() if touch else nm_.hover()
                    page.wait_for_timeout(50)
                    st = row.evaluate(BOX)
                    if not (st["open"] and st["left"] >= 0 and st["right"] <= st["vw"] + 0.5 and same_text(st["text"], static_box[(sd, ss, True)])):
                        bad.append(sk)
                    if touch:
                        nm_.tap()
                    else:
                        page.mouse.move(2, 400)
                page.locator(f'#headline-table tr[data-dataset="{pd}"][data-setup="{ps}"]:not(.hl-sub) .hl-more').evaluate("b => b.click()")
            browser_rows.append([width, theme, "details box: every other-setting row (through its expander)",
                                 f"{sum(len(v) for v in fam_base.values())} rows: opens inside the window with its own setup's "
                                 "text" + (f"; WRONG: {bad}" if bad else ""), "ok" if not bad else "WRONG"])
            # Tap / click outside closes; Escape closes; keyboard focus opens; filter hides an open box's row.
            first = page.locator('#headline-table tbody tr[data-box]:not(.hl-sub)').first
            fname = first.locator(".model-name")
            fname.scroll_into_view_if_needed()
            if touch:
                fname.tap()
                page.wait_for_timeout(60)
                o1 = first.evaluate(BOX)["open"]
                page.tap("#leaderboard-title")
                page.wait_for_timeout(60)
                o2 = first.evaluate(BOX)["open"]
                ok = o1 and not o2
                browser_rows.append([width, theme, "details box: a tap outside closes it", f"open {o1} → after a tap outside {o2}",
                                     "ok" if ok else "WRONG"])
                # The box's own link opens Every decision filtered to that setup.
                fname.tap()
                page.wait_for_timeout(60)
                link = first.locator(".hl-box a", has_text="Open its decisions")
                href = link.get_attribute("href")
                link.tap()
                page.wait_for_url(re.compile(r".*/decisions/.*"))
                page.wait_for_timeout(800)
                q = parse_qs(urlparse(page.url).query)
                want = parse_qs(urlparse(href.replace("&amp;", "&")).query)
                ok = q.get("d") == want.get("d") and q.get("s") == want.get("s") and page.locator(".dec-card").count() > 0
                browser_rows.append([width, theme, "details box: Open its decisions → (tap)",
                                     f"{page.url}: decision cards {page.locator('.dec-card').count()}", "ok" if ok else "WRONG"])
                page.goto(SITE)
                page.wait_for_timeout(300)
            else:
                page.mouse.move(2, 400)
                page.focus('#headline-table tbody tr[data-box]:not(.hl-sub) .model-name')
                page.wait_for_timeout(60)
                o1 = first.evaluate(BOX)["open"]
                inbox = False
                for _ in range(3):  # past the row's expander, into the box: its first link
                    page.keyboard.press("Tab")
                    page.wait_for_timeout(40)
                    inbox = page.evaluate("() => !!document.activeElement.closest('.hl-box')")
                    if inbox:
                        break
                o2 = first.evaluate(BOX)["open"]
                page.keyboard.press("Escape")
                page.wait_for_timeout(60)
                o3 = first.evaluate(BOX)["open"]
                back = page.evaluate("() => document.activeElement.classList.contains('model-name')")
                ok = o1 and inbox and o2 and not o3 and back
                browser_rows.append([width, theme, "details box: keyboard",
                                     f"focus on the name opens it {o1}; Tab moves into the box {inbox} (still open {o2}); "
                                     f"Escape closes it {not o3} and returns the focus to the name {back}",
                                     "ok" if ok else "WRONG"])
            bad_err = [e for e in errs if "fetch" not in e.lower()]
            browser_rows.append([width, theme, "script errors", "; ".join(errs) or "none", "ok" if not bad_err else "ERRORS"])
            ctx.close()
    br.close()
with (pk / "browser.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["width", "theme", "check", "observed", "result"])
    w.writerows(browser_rows)
bc = Counter(r[-1] for r in browser_rows)
(pk / "browser.md").write_text(
    "# Browser tests (1280 and 390 px, light and dark)\n\n"
    f"{len(browser_rows)} checks: " + ", ".join(f"{v} {k}" for k, v in sorted(bc.items())) + ". browser.csv has every one.\n\n"
    "Chromium through Playwright, the nav-ct render served by request routing (no server); at 390 px as a phone (touch, "
    "mobile viewport). Header: on 15 pages the suite strip, the leaf, the name, the five tabs, exactly the page's tab "
    "underlined (3 px solid, the computed link colour), sticky at the top, nothing wider than the window. Sticky: "
    "scrolled to the end of the home, About and Method pages, the header is still at the top. Tabs: at 390 px the row "
    "scrolls sideways (wheel/swipe) and the marked tab is scrolled into view; at 1280 px it fits. Filter: each state's "
    "rows equal the rows of that type in data/setups.json, programs in every state, the ranks unchanged (rank among all "
    "models), no row lost; every expander works in the filtered views. Details box: every row (and every other-setting "
    "row through its expander), by hover at 1280 and by tap at 390: it opens inside the window's width with that "
    "setup's text, and closes (pointer leaves / second tap); a tap outside closes it; at 1280 the keyboard: focus opens "
    "it, Tab enters it, Escape closes it and returns the focus; at 390 its Open its decisions link opens Every decision "
    "filtered to the setup.\n")
print("browser:", dict(bc))
(pk / "header-heights.md").write_text(
    "# Sticky header height (suite strip + name + tabs), light theme\n\n| Width | Page | Height |\n|---:|---|---:|\n"
    + "".join(f"| {w} | {pg} | {h} px |\n" for w, pg, h in heights))

# --- 5. Screenshots -----------------------------------------------------------------------------------------------
shots = pk / "screenshots"
shots.mkdir(exist_ok=True)
with sync_playwright() as p:
    br = p.chromium.launch()
    for width in (1280, 390):
        touch = width < 600
        for theme in ("light", "dark"):
            ctx = context(br, nav, width, theme, routed=True, touch=touch)
            page = ctx.new_page()
            sfx = f"{width}-{theme}"
            for path, name in (("", "leaderboard"), ("decisions/", "decisions"), ("highlights/", "highlights"),
                               ("experiments/", "experiments"), ("about/", "about"), ("method/", "method")):
                page.goto(SITE + path)
                page.wait_for_timeout(700 if path == "decisions/" else 350)
                page.screenshot(path=str(shots / f"{name}-{sfx}.png"))
            page.goto(SITE)
            page.wait_for_timeout(300)
            page.evaluate("window.scrollTo(0, 2600)")
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / f"sticky-scrolled-{sfx}.png"))
            if touch:
                page.goto(SITE + "about/")
                page.wait_for_timeout(300)
                page.eval_on_selector(".site-tabs ul", "u => u.scrollTo(0, 0)")
                page.wait_for_timeout(100)
                page.screenshot(path=str(shots / f"tabs-scrolled-start-{sfx}.png"), clip={"x": 0, "y": 0, "width": width, "height": 140})
                page.eval_on_selector(".site-tabs ul", "u => u.scrollTo(u.scrollWidth, 0)")
                page.wait_for_timeout(100)
                page.screenshot(path=str(shots / f"tabs-scrolled-end-{sfx}.png"), clip={"x": 0, "y": 0, "width": width, "height": 140})
            page.goto("about:blank")
            page.goto(SITE + "#headline-table")
            page.wait_for_timeout(350)
            page.screenshot(path=str(shots / f"leaderboard-table-{sfx}.png"))
            row = page.locator('#headline-table tbody tr[data-box]:not(.hl-sub)').nth(2)
            row.locator(".model-name").scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -260)")
            if touch:
                row.locator(".model-name").tap()
            else:
                row.locator(".model-name").hover()
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / f"details-{'tap' if touch else 'hover'}-{sfx}.png"))
            page.mouse.move(2, 300)
            page.goto("about:blank")
            page.goto(SITE + "#headline-table")
            page.wait_for_timeout(300)
            for state in ("chat", "decision"):
                page.click(f'[data-hl-filter="{state}"]')
                page.wait_for_timeout(150)
                page.evaluate("document.querySelector('.hl-filter').scrollIntoView({block: 'start'}); window.scrollBy(0, -110)")
                page.wait_for_timeout(100)
                page.screenshot(path=str(shots / f"filter-{state}-{sfx}.png"))
            ctx.close()
    br.close()
print("screenshots:", len(list(shots.glob("*.png"))))

# --- Exit status: non-zero when any compared number differs or any check is not in an accepted state.
bad_numbers = sum(d for _, _, d, _ in summary)
bad_urls = [r for r in urls if r[-1] != "ok"]
bad_browser = [r for r in browser_rows if r[-1] != "ok"]
print(f"review: {bad_numbers} number difference(s), {len(bad_urls)} URL check(s) and {len(bad_browser)} browser "
      "check(s) not accepted")
sys.exit(1 if bad_numbers or bad_urls or bad_browser else 0)
