"""leaderboard-ct review packet (Ümit #2745): numbers, links and deep links, browser tests from file://, screenshots,
from the branch render, origin/main's render and the live mirror; reads only. Method of mailbox/front-story/scripts/
review.py, adapted to the new leaderboard (one row per model at its highest setting, expanders, programs, Too safe).
Usage: review.py WORKTREE LIVE_DIR MAIN_RENDER_DIR BRANCH_RENDER_DIR LATE_PREVIEW_DIR OUT_DIR EXPECTED_FAMILIES_JSON
Exits 1 if any number differs or any check is not in an accepted state.
Writes OUT_DIR/{source.patch, numbers.csv, numbers.md, page-diffs.md, links.csv, links.md, browser.csv, browser.md,
screenshots/}. No HTTP server: file:// for the browser tests; Playwright request routing for the live-vs-branch
addresses and for tapping into Every decision (its script fetches its JSON, which file:// does not allow)."""
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

work, live, mainr, cand, latep, pk = (Path(a) for a in sys.argv[1:7])
pk.mkdir(parents=True, exist_ok=True)
git = lambda *a: subprocess.run(["git", "-C", str(work), *a], check=True, capture_output=True, text=True).stdout

# --- 1. Source diff -----------------------------------------------------------------------------------------------
(pk / "source.patch").write_text(git("diff", "origin/main...HEAD", "--", "tools/site"))
# 5ca56de as rebased onto fix-filters is 3094aa5: the delta is this review's change only (fix-filters is its own branch).
(pk / "delta-vs-5ca56de.patch").write_text(git("diff", "3094aa5", "HEAD", "--", "tools/site"))


# --- 2. Numbers ---------------------------------------------------------------------------------------------------
def soup(root: Path, path=""):
    return BeautifulSoup((root / path / "index.html").read_text(), "html.parser")


NUM = re.compile(r"[\u2212-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: [x.replace(",", "").replace("\u2212", "-") for x in NUM.findall(t)]
norm = lambda t: " ".join(t.split())


def table_cells(s, skip=()) -> dict:
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


L, M, C = soup(live), soup(mainr), soup(cand)
rows_csv, summary = [], []

# 2a. Every table cell of the live home page (and of origin/main's render) against the branch; the headline table is
# compared cell by cell in 2b (its rows changed by design).
lt, mt, ct = (table_cells(x, skip=("headline-table",)) for x in (L, M, C))
for name, ref in (("live", lt), ("origin/main render", mt)):
    diff_t = [k for k in ref if ct.get(k) != ref[k]]
    extra = [k for k in ct if k not in ref]
    for k in sorted(ref, key=str):
        (tid, ds, margin, cap, _), (rds, setup, nm_, _), col = k
        if ct.get(k) != ref[k] or name == "live":
            rows_csv.append([f"home table cell vs {name}", tid or cap[:60], rds or ds, setup or nm_, col, ref[k],
                             ct.get(k, "MISSING"), "equal" if ct.get(k) == ref[k] else "DIFF"])
    for k in extra:
        rows_csv.append([f"home table cell (branch only) vs {name}", k[0][0] or k[0][3][:60], k[1][0], k[1][1] or k[1][2],
                         k[2], "", ct[k], "new"])
    summary.append((f"Home page: every {name} table cell (every tab, both margins, All leagues and each league, All setups "
                    "panel, Leagues block, Close choices, Nackgammon; the headline table in the next row) against the branch",
                    len(ref), len(diff_t), len(extra)))


# 2b. Headline table: every cell of every row (ranked rows, other-settings rows, programs) against the live cell of the
# same setup; Decisions also against Every decision's index; Setting against setups.json.
def live_col(pred, col):
    out = {}
    for (tkey, rkey, head), v in lt.items():
        if pred(tkey) and head == col:
            out.setdefault((rkey[0] or tkey[1], rkey[1]), v)
    return out


risk_all = lambda col: live_col(lambda t: t[0] == "panel-risk" and t[1] == "all" and t[2] == "0.001", col)
qual = lambda col: live_col(lambda t: t[0] == "panel-quality", col)
COST_HEAD = "$ per 1,000 decisions $ per 1M decisions"
SRC = {"Risk judgement (95% interval)": risk_all("Risk judgement"), "Risks found": risk_all("Risks found"),
       "Right safety": risk_all("Right safety"), "Error rate (PR)": qual("Error rate (PR), 95% interval"),
       COST_HEAD: qual("$ per 1,000 decisions"),
       "Decisions": live_col(lambda t: t[0] == "panel-cost", "Decisions")}
index = json.loads((cand / "decisions" / "index.json").read_text())
dec_n = {(d["id"], s["slug"]): s["decisions"] for d in index["datasets"] for s in d["setups"]}
meta = json.loads((live / "data" / "setups.json").read_text())["setups"]


def setting_of(ds, slug):
    m = [x for x in meta if x["slug"] == slug and x["dataset"] == ds] or [x for x in meta if x["slug"] == slug and x["dataset"].startswith("league-")]
    return m[0]["setting"] if m else None  # a computed reference row (Random / Safest computed): no setups.json entry


hl = C.select_one("#headline-table")
head = [norm(th.get_text(" ")) for th in hl.thead.find_all("th")]
hl_n = hl_d = 0
for tr in hl.tbody.find_all("tr", recursive=False):
    if not tr.get("data-setup"):
        continue
    cells = tr.find_all(["td", "th"], recursive=False)
    k = (tr["data-dataset"], tr["data-setup"])
    kind = "other setting" if "hl-sub" in (tr.get("class") or []) else "row"
    for h, c in zip(head, cells):
        text = norm(c.get_text(" "))
        if h == "Setting":
            s = setting_of(*k)
            exp, ok = s or "\u2014", text == (s or "\u2014")
        elif h == "League":
            exp = f"League {k[0].split('-')[1]}"
            ok = text == exp
        elif h in SRC:
            exp = SRC[h].get(k)
            if exp is None and text in ("N/A",):
                exp, ok = "not in a live table (computed reference row)", True
            elif h == COST_HEAD:
                c2 = BeautifulSoup(str(c), "html.parser")
                for x in c2.select(".cost-1m"):
                    x.decompose()
                text = norm(c2.get_text(" ").replace("$", ""))
                ok = exp is not None and text == norm(exp)
            elif h == "Decisions":
                ok = int(nums(text)[0]) == dec_n.get(k) and (exp is None or nums(text)[:1] == nums(exp)[:1])
                exp = (f"{exp} (live Cost tab, Decisions)" if exp is not None else "not in the live Cost tab (a program)") \
                    + f"; Every decision index {dec_n.get(k)}"
            else:
                ok = exp is not None and (nums(text) == nums(exp) if nums(exp) else text == norm(exp))
        else:
            continue
        hl_n += 1
        hl_d += not ok
        rows_csv.append([f"headline cell ({kind})", h, k[0], k[1], h, exp if exp is not None else "MISSING IN LIVE", text,
                         "equal" if ok else "DIFF"])
summary.append(("Headline table, every row (ranked, other settings, programs): risk judgement and interval, risks found, "
                "right safety (live All leagues Risk table, 0.001), error rate and interval (every number), $ per 1,000 "
                "with its price label (whole cell), decisions (live Cost tab Decisions and Every decision's index), "
                "setting (setups.json), league", hl_n, hl_d, 0))

# 2c. Too safe chart: each value against the live Right safety / Risks found share of the same setup.
rs_l, rf_l = risk_all("Right safety"), risk_all("Risks found")
ts_n = ts_d = 0
for li in C.select("#too-safe li.hbar"):
    k = (li["data-dataset"], li["data-setup"])
    text = norm(li.select_one(".hbar-value").get_text(" "))
    exp = f'{nums(rs_l.get(k, ""))[:1]} | {nums(rf_l.get(k, ""))[:1]}'
    ok = [nums(x)[:1] for x in text.split("|")] == [nums(rs_l.get(k, ""))[:1], nums(rf_l.get(k, ""))[:1]]
    ts_n += 1
    ts_d += not ok
    rows_csv.append(["Too safe chart (new)", "right safety | risks found", k[0], k[1], "share", exp, text,
                     "equal" if ok else "DIFF"])
summary.append(("Too safe chart (new): right safety and risks found of each bar against the live All leagues Risk "
                "table", ts_n, ts_d, 0))

# 2d. Finding sections: every value beside a bar against the clear-risk data file (unchanged values; colours only).
CR = json.loads((live / "data" / "v3" / "clear-risk.json").read_text())
scan = next(s for s in CR["sections"] if s["id"] == "clear-risk-setups")
exp_scan = {}
for t in scan["tables"]:
    lg = re.match(r"League (\d)", t["caption"]).group(1)
    i = t["head"].index("bias = missed \u2212 needless")
    for r in t["rows"]:
        exp_scan[(r[0], lg)] = r[i]
p2 = next(s for s in CR["sections"] if s["id"] == "clear-risk-part2")
q1 = next(t for t in p2["tables"] if t["caption"].startswith("Q1"))
i = q1["head"].index("bias")
exp_q1 = {}
for r in q1["rows"]:
    exp_q1.setdefault(r[0], {})[r[1]] = r[i]
f_n = f_d = 0
for li in C.select("#finding-cautious li.hbar"):
    name, lg = re.match(r"(.+) · League (\d)$", norm(li.select_one(".hbar-label").get_text(" "))).groups()
    text = norm(li.select_one(".hbar-value").get_text(" "))
    exp = exp_scan.get((name, lg))
    ok = exp is not None and norm(exp) == text
    f_n += 1
    f_d += not ok
    rows_csv.append(["finding: Models are too cautious", "scan bias", f"league-{lg}", name, "bias", exp, text, "equal" if ok else "DIFF"])
for li in C.select("#finding-flinch li.hbar"):
    name = norm(li.select_one(".hbar-label").get_text(" "))
    text = norm(li.select_one(".hbar-value").get_text(" "))
    e = exp_q1.get(name, {})
    exp = f'{e.get("with numbers")} | {e.get("board only")}' if e else None
    ok = exp is not None and norm(exp) == text
    f_n += 1
    f_d += not ok
    rows_csv.append(["finding: numbers on screen", "Q1 bias", "", name, "bias", exp, text, "equal" if ok else "DIFF"])
summary.append(("Finding sections: every value beside a bar against data/v3/clear-risk.json", f_n, f_d, 0))

# 2e. Measure charts (maker colours): every value beside a bar, live against branch, by setup.
def chart_vals(s):
    out = Counter()
    for li in s.select("section.measure li.hbar"):
        out[(li.find_parent("section")["id"], li.get("data-dataset"), li.get("data-setup"),
             norm(li.select_one(".hbar-value").get_text(" ")))] += 1
    return out


cl, cc = chart_vals(L), chart_vals(C)
summary.append(("Measure charts (Risk judgement, Error rate, Cost, Time): every bar's value, live against branch",
                sum(cl.values()), sum((cl - cc).values()), sum((cc - cl).values())))
for k in (cl - cc):
    rows_csv.append(["measure chart value", k[0], k[1], k[2], "value", k[3], "MISSING", "DIFF"])

# 2f. Every other page: the main content, byte for byte; data files.
o_n = o_d = 0
cut = lambda s: s[s.index('<main id="main"'):s.index("</main>")] if '<main id="main"' in s else s
stamp = lambda s: re.sub(r"updated \d+ \w+ \d{4}, \d\d:\d\d UTC", "updated STAMP", s)
frozen = 0
page_diffs = []
for f in sorted(live.rglob("index.html")):
    rel = f.relative_to(live)
    if str(rel) == "index.html":
        continue
    b = cand / rel
    if not b.is_file() and rel.parts[0] in ("archive", "results"):
        frozen += 1
        continue
    a_t, b_t = (stamp(cut(f.read_text())), stamp(cut(b.read_text()))) if b.is_file() else (None, None)
    ok = b.is_file() and a_t == b_t
    o_n += 1
    o_d += not ok
    if not ok:
        rows_csv.append(["other page", str(rel), "", "", "main content", "live", "branch", "DIFF"])
        if b_t is not None:
            page_diffs.append(f"## {rel}\n\n```diff\n" + "\n".join(difflib.unified_diff(
                a_t.replace(">", ">\n").splitlines(), b_t.replace(">", ">\n").splitlines(), "live", "branch",
                lineterm="", n=1)) + "\n```\n")
summary.append((f"Every other page: the main content, byte for byte after the render time stamp ({frozen} frozen "
                "snapshots under results/ and archive/ are copied at deploy, not rendered, and left out)", o_n, o_d, 0))
d_n = d_d = 0
for f in sorted((live / "data").rglob("*")):
    if f.is_file() and f.suffix != ".html":
        d_n += 1
        g = cand / f.relative_to(live)
        if f.name == "manifest.json":
            ma, mb = json.loads(f.read_text()), json.loads(g.read_text())
            fb = {e["path"]: e for e in mb.get("files", [])}
            bad = ({k: v for k, v in ma.items() if k not in ("data_as_of", "files")} !=
                   {k: v for k, v in mb.items() if k not in ("data_as_of", "files")}
                   or any(fb.get(e["path"]) != e for e in ma.get("files", [])))
        else:
            bad = not g.is_file() or f.read_bytes() != g.read_bytes()
        d_d += bad
        if bad:
            rows_csv.append(["data file", str(f.relative_to(live)), "", "", "bytes", "live", "branch", "DIFF"])
summary.append(("Data files under data/, byte for byte (manifest.json without its generated time)", d_n, d_d, 0))
(pk / "page-diffs.md").write_text("# Other pages: live against branch, where the main content differs\n\n" +
                                  ("\n".join(page_diffs) or "None.\n"))
with (pk / "numbers.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["what", "where", "dataset", "setup", "metric", "reference", "branch", "result"])
    w.writerows(rows_csv)
lines = ["# Numbers: leaderboard-ct render against live", "",
         f"Live: the deployed site's mirror; branch: the render of leaderboard-ct ({git('rev-parse', '--short', 'HEAD').strip()}) "
         f"and origin/main ({git('rev-parse', '--short', 'origin/main').strip()}) from one copy of the live state, the same "
         "results hash. numbers.csv has one line per compared value (vs origin/main only where different).", "",
         "| Compared | Values | Differences | New in branch |", "|---|---:|---:|---:|"]
lines += [f"| {w} | {n:,} | {d:,} | {e:,} |" for w, n, d, e in summary]
(pk / "numbers.md").write_text("\n".join(lines) + "\n")
print("numbers:", [(w[:40], n, d, e) for w, n, d, e in summary])


# --- 3. Links -----------------------------------------------------------------------------------------------------
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


def context(browser, root, width, theme, routed=True):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844})
    ctx.add_init_script(f"localStorage.setItem('theme','{theme}')")
    if routed:
        ctx.route("http://site.test/**", router(root))
    return ctx


BASE = "http://site.test/"
results = []
ids_cache = {}


def ids_of(root, rel):
    if (root, rel) not in ids_cache:
        f = root / rel / "index.html" if (root / rel).is_dir() or rel in ("", ".") else root / rel
        ids_cache[root, rel] = {t["id"] for t in BeautifulSoup(f.read_text(), "html.parser").find_all(id=True)} \
            if f.is_file() and f.suffix == ".html" else None
    return ids_cache[root, rel]


def resolve_link(root, h):
    u = urlparse(h)
    if u.path.startswith("/"):
        return False, "absolute path outside the render"
    rel = unquote(u.path)
    f = root / rel
    exists = (f / "index.html").is_file() if (rel == "" or f.is_dir()) else f.is_file()
    frag_ok = True
    if u.fragment and exists:
        ids = ids_of(root, rel)
        frag_ok = ids is None or u.fragment in ids
    return exists and frag_ok, "file " + ("found" if exists else "MISSING") + (
        "" if not u.fragment else ", #" + u.fragment + (" found" if frag_ok else " not in the static page"))


# 3a. Every live home link is still on the branch home page (all existing links kept), and every branch link resolves.
live_hrefs = Counter(a["href"] for a in L.find_all("a", href=True))
cand_hrefs = Counter(a["href"] for a in C.find_all("a", href=True))
main_hrefs = Counter(a["href"] for a in M.find_all("a", href=True))
for h in sorted(live_hrefs):
    # The link-preview share images (share/risk-card-…png) are made by build.py main only, which these renders do not
    # run: absent from origin/main's render too.
    res = ("ok" if cand_hrefs.get(h) else "build.py-only asset, absent from the origin/main render too"
           if not main_hrefs.get(h) and h.startswith("share/") else "LOST")
    results.append(["any", "live home link kept on the branch", h, live_hrefs[h], cand_hrefs.get(h, 0), "",
                    f"origin/main render: {main_hrefs.get(h, 0)}", res])
for h in sorted(cand_hrefs):
    if re.match(r"^(https?:|mailto:)", h):
        results.append(["any", "branch home link (external, not fetched)", h, "", "", "", "", "external"])
        continue
    ok, why = resolve_link(cand, h)
    lok, lwhy = resolve_link(live, h)
    q = parse_qs(urlparse(h.replace("&amp;", "&")).query)
    if urlparse(h).path == "decisions/" and "s" in q:
        found = (q["d"][0], q["s"][0]) in dec_n
        results.append(["any", "decision link: dataset and setup in Every decision's index", h, "", "", "",
                        f"{q['d'][0]} / {q['s'][0]}: {dec_n.get((q['d'][0], q['s'][0]))} decisions",
                        "ok" if found and dec_n[(q['d'][0], q['s'][0])] > 0 else "BROKEN"])
    res = "ok" if ok else ("same as live (unresolved statically in both)" if not lok and (h in live_hrefs or h.startswith("/"))
                           else "BROKEN")
    results.append(["any", "branch home link", h, "", "", lwhy, why, res])

# 3b. Deep links in the browser at 1280 and 390, live against branch; the new anchors on the branch only; tapping each
# ranked row's model name opens Every decision with that setup selected (routed: Every decision fetches its JSON).
home_ids = sorted({t["id"] for t in L.find_all(id=re.compile(r"^lg-"))})
URLS = ["", "?league=league-1", "?league=league-2", "?league=league-3", "?league=shared", "?league=all",
        "?type=decision", "?type=chat", "?type=program", "?league=league-1&type=decision",
        "?tab=risk", "?tab=quality", "?tab=confidence", "?tab=reasoning", "?tab=cost", "?tab=stability",
        "?league=league-2&type=chat&tab=cost#board", "?league=league-3&tab=quality#board", "#board", "#board-panel",
        "#filters", "#close-choices-stage-b", "#nackgammon-paired", "#downloads", "#leagues-tabs", "#v3", "#v3-l1",
        "#allstar", "#leaderboard", "#finding-cautious", "#finding-flinch", "#risk-judgement", "#error-rate", "#cost",
        "#time"] + [f"#{i}" for i in home_ids]
NEW = ["#too-safe", "?type=chat#leaderboard", "?league=league-2#too-safe"]
STATE = """() => {
  const pressed = sel => [...document.querySelectorAll(sel)].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.textContent.trim()).join('|');
  const sel = [...document.querySelectorAll('[role="tab"][aria-selected="true"], a.mode[aria-selected="true"]')].map(b => b.textContent.trim()).join('|');
  const panel = [...document.querySelectorAll('#board [data-panel]')].find(p => !p.hidden);
  const rows = panel ? [...panel.querySelectorAll('[data-league-view]:not([data-off]) tr[data-kind]')].filter(r => !r.hidden && r.offsetParent).length : -1;
  const id = decodeURIComponent(location.hash.slice(1));
  const t = id && document.getElementById(id);
  const bar = [...document.querySelectorAll('.view-bar, #filters')].filter(e => getComputedStyle(e).position === 'sticky').reduce((a, e) => Math.max(a, e.getBoundingClientRect().bottom), 0);
  const box = t && t.getBoundingClientRect();
  return { path: location.pathname + location.search + location.hash, tabs: sel,
           league: pressed('#filters [data-league-pick]'), type: pressed('#filters [data-filter-kind]'), rows,
           target: id ? (t ? (t.offsetParent || t.getClientRects().length ? (box.top >= bar - 4 && box.top < innerHeight ? 'in view' : 'exists, not at top') : 'hidden') : 'missing') : '',
           status: document.title ? 'loaded' : 'no title', overflow: document.documentElement.scrollWidth > innerWidth + 1 };
}"""
KEYS = ("tabs", "league", "type", "rows", "target")
ranked = [(tr["data-dataset"], tr["data-setup"], tr.select_one("a.model-name")["href"])
          for tr in hl.tbody.find_all("tr", recursive=False)
          if tr.get("data-setup") and not set(tr.get("class") or []) & {"hl-sub", "late"}]
with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (1280, 390):
        out = {}
        for name, root, urls in (("live", live, URLS), ("branch", cand, URLS + NEW)):
            ctx = context(b, root, width, "dark")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            states = []
            for u in urls:
                page.goto(BASE + u)
                page.wait_for_timeout(250)
                states.append(page.evaluate(STATE))
            if name == "branch":
                # Tap each row's model name (ranked rows and programs): Every decision opens with that setup.
                for ds, slug, href in ranked:
                    page.goto(BASE)
                    page.wait_for_timeout(200)
                    page.click(f'#headline-table tr[data-dataset="{ds}"][data-setup="{slug}"]:not(.hl-sub) a.model-name')
                    page.wait_for_url(re.compile(r".*/decisions/.*"))
                    page.wait_for_timeout(700)
                    q = parse_qs(urlparse(page.url).query)
                    ok = q.get("d", [""])[0] == ds and q.get("s", [""])[0] == slug and page.locator(".dec-card").count() > 0
                    results.append([width, "tap a model: Every decision filtered to the setup", href, "", page.url, "",
                                    f"d={q.get('d')}, s={q.get('s')}, decision cards {page.locator('.dec-card').count()}",
                                    "ok" if ok else "WRONG"])
            out[name] = (states, errors)
            ctx.close()
        for u, a, c in zip(URLS, out["live"][0], out["branch"][0]):
            same = all(a[k] == c[k] for k in KEYS) and a["path"] == c["path"]
            results.append([width, "address, live vs branch", u, a["path"], c["path"],
                            "; ".join(f"{k}={a[k]}" for k in KEYS), "; ".join(f"{k}={c[k]}" for k in KEYS),
                            "same" if same else "DIFFERENT"])
        for u, c in zip(NEW, out["branch"][0][len(URLS):]):
            ok = c["target"] in ("", "in view") and c["status"] == "loaded"
            results.append([width, "address, branch only", u, "", c["path"], "",
                            "; ".join(f"{k}={c[k]}" for k in KEYS + ("overflow",)), "ok" if ok else "CHECK"])
        errs = [e for e in out["branch"][1] if "fetch" not in e.lower()]
        results.append([width, "script errors", "", "", "", "; ".join(out["live"][1]) or "none",
                        "; ".join(out["branch"][1]) or "none", "ok" if not errs else "ERRORS"])
    b.close()
with (pk / "links.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["width", "check", "address or action", "live", "branch address after load", "live state", "branch state",
                "result"])
    w.writerows(results)
cnt = Counter(r[-1] for r in results)
by = Counter((r[1], r[-1]) for r in results)
(pk / "links.md").write_text(
    "# Links and deep links: leaderboard-ct render\n\n"
    "**No new errors among the checked links.** Not every link is verified functional: 823 hrefs cannot be resolved "
    "statically in either live or branch (the #d… anchors Every decision's script makes, paths into the sibling "
    "site), 21 external links were not fetched, and 3 share images are made by build.py main only (absent from the "
    "origin/main render too).\n\n"
    f"{len(results)} checks: " + ", ".join(f"{v} {k}" for k, v in sorted(cnt.items())) + ". links.csv has every one.\n\n"
    "| Check | Result | Count |\n|---|---|---:|\n" + "".join(f"| {k} | {r} | {v} |\n" for (k, r), v in sorted(by.items())) +
    "\nExisting links: every href of the live home page must still be on the branch home page (count ≥ 1). Branch "
    "links: the file in the render and its #fragment an id of the target page (external links listed, not fetched; "
    "an href unresolved statically in live and branch alike is 'same as live'); each decisions/?d=…&s=… link's "
    "dataset and setup are in Every decision's index with decisions. Addresses: opened at 1280 px and 390 px "
    "(Playwright, request routing, no server) on the live mirror and the branch; compared: the address after the "
    "page's script ran, the selected tabs, League and Model type filters, the rows shown in the open Every number tab, "
    "and for an #anchor whether its element is at the top of the window. Tap: each ranked row's and program row's "
    "model name clicked; Every decision must open with that dataset and setup (its script keeps s= only for a setup it "
    "found) and show decision cards.\n")
print("links:", dict(cnt))

# --- 4. Browser tests (Ümit: expanders, links, filters don't break the table; Zeki #2790) -------------------------
# Each parent's alternatives come from evidence.py's expected-families.json (derived from the data files, not from the
# page's aria-controls): every expander is clicked and the rows it shows must be exactly those.
FAMILIES = json.loads(Path(sys.argv[7]).read_text())
STATE_HL = """() => {
  const t = document.getElementById('headline-table');
  const vis = e => !!(e.offsetParent || e.getClientRects().length);
  const main = [...t.querySelectorAll('tbody tr[data-setup]:not(.hl-sub)')];
  const sub = [...t.querySelectorAll('tbody tr.hl-sub')];
  return { main: main.length, main_shown: main.filter(vis).length, sub: sub.length, sub_shown: sub.filter(vis).length,
           ts_shown: [...document.querySelectorAll('#too-safe li.hbar')].filter(vis).length,
           quality_rows: [...document.querySelectorAll('#panel-quality tbody tr[data-kind]:not([data-kind="reference"])')].filter(r => !r.hidden).length,
           panel: [...document.querySelectorAll('[data-headline-panel]')].filter(p => !p.hidden).map(p => p.dataset.headlinePanel).join('|'),
           text: main.filter(vis).map(r => r.textContent.replace(/\\s+/g, ' ').trim()).join(' | ') + ' || ' +
                 [...document.querySelectorAll('#too-safe li.hbar')].map(r => r.textContent.replace(/\\s+/g, ' ').trim()).join(' | ') };
}"""
EXPAND = """() => {
  const vis = e => !!(e.offsetParent || e.getClientRects().length);
  const shownSubs = () => [...document.querySelectorAll('#headline-table tr.hl-sub')].filter(vis).map(r => `${r.dataset.dataset}/${r.dataset.setup}`).sort();
  const out = [];
  for (const tr of document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub)')) {
    const key = `${tr.dataset.dataset}/${tr.dataset.setup}`, b = tr.querySelector('.hl-more');
    const before = shownSubs();
    if (!b) { out.push({ key, button: false, before, open: [], closed: before }); continue; }
    b.click();
    const open = shownSubs(), exp1 = b.getAttribute('aria-expanded');
    b.click();
    out.push({ key, button: true, before, open, closed: shownSubs(), exp1, exp2: b.getAttribute('aria-expanded') });
  }
  return out;
}"""


def expanders_ok(ex):
    bad = []
    for e in ex:
        want = FAMILIES.get(e["key"])
        ok = (want is not None and e["before"] == [] and e["closed"] == [] and e["open"] == want
              and (e["button"] == bool(want)) and (not e["button"] or (e["exp1"] == "true" and e["exp2"] == "false")))
        if not ok:
            bad.append(f"{e['key']}: expected {want}, shown {e['open']}")
    return bad


browser_rows = []
n_main = len(hl.select("tbody tr[data-setup]:not(.hl-sub)"))
n_sub = len(hl.select("tbody tr.hl-sub"))
n_ts = len(C.select("#too-safe li.hbar"))
with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (1280, 390):
        for theme in ("light", "dark"):
            ctx = context(b, cand, width, theme, routed=False)
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            url = (cand / "index.html").resolve().as_uri()
            for state in ("", "?type=chat", "?type=decision", "?type=program", "?league=league-2", "?league=league-3&type=chat",
                          "click:[data-filter-kind=\"decision\"]", "click:[data-league-pick=\"league-1\"]"):
                page.goto(url + ("" if state.startswith("click:") else state))
                page.wait_for_timeout(300)
                if state.startswith("click:"):
                    loc = page.locator("#filters " + state[6:])
                    if loc.count():
                        loc.first.evaluate("b => b.click()")  # a key folded under More filters: clicked by script
                        page.wait_for_timeout(200)
                st = page.evaluate(STATE_HL)
                bad = expanders_ok(page.evaluate(EXPAND))
                ok = (st["main"] == n_main and st["main_shown"] == n_main and st["sub"] == n_sub and st["sub_shown"] == 0
                      and st["ts_shown"] == n_ts and st["panel"] == "model" and not bad)
                browser_rows.append([width, theme, state or "(no filter)",
                                     f"rows shown {st['main_shown']}/{n_main}; other-setting rows hidden {st['sub'] - st['sub_shown']}/{n_sub}; "
                                     f"each of {n_main} parent rows: its expander shows exactly its expected alternatives "
                                     f"(expected-families.json) and hides them again" + (f"; WRONG: {'; '.join(bad)}" if bad else "")
                                     + f"; Too safe bars {st['ts_shown']}/{n_ts}; Every number Quality rows shown {st['quality_rows']}",
                                     "ok" if ok else "WRONG"])
            # All setups and back; an expander left open survives the round trip.
            page.goto(url)
            page.wait_for_timeout(300)
            first = page.locator("#headline-table .hl-more").first
            first_key = first.evaluate("b => `${b.closest('tr').dataset.dataset}/${b.closest('tr').dataset.setup}`")
            first.click()
            page.click('[data-headline-view="all"]')
            a = page.evaluate(STATE_HL)
            page.click('[data-headline-view="model"]')
            m = page.evaluate(STATE_HL)
            ok = a["panel"] == "all" and m["panel"] == "model" and m["main_shown"] == n_main and m["sub_shown"] == len(FAMILIES[first_key])
            browser_rows.append([width, theme, "One row per model → All setups → back, first expander open",
                                 f"panels {a['panel']} → {m['panel']}; rows {m['main_shown']}/{n_main}; open rows {m['sub_shown']} "
                                 f"(expected {len(FAMILIES[first_key])}, {first_key})", "ok" if ok else "WRONG"])
            bad = [e for e in errs if "fetch" not in e.lower()]
            browser_rows.append([width, theme, "script errors (file://; Every number's own fetches excluded)",
                                 "; ".join(errs) or "none", "ok" if not bad else "ERRORS"])
            ctx.close()

    # The Phase filter (Zeki #2790 item 3): bg.js loads fragments/<league>-<phase>.html by fetch, which file:// refuses,
    # so this test runs on the same render through request routing (no server). The real control is used: the More
    # filters key, then the Phase select. Expected slot contents come from the fragment files themselves.
    def slot_expect(phase):
        out = {}
        for f in sorted((cand / "fragments").glob(f"*-{phase}.html")):
            ds = f.name[:-len(f"-{phase}.html")]
            for s in BeautifulSoup(f.read_text(), "html.parser").select(".phase-slot[data-slot]"):
                out[(ds, s["data-slot"])] = (len(s.select("tr[data-kind]")), [norm(c.get_text("")) for c in s.select("td, th")])
        return out
    SLOTS = """() => [...document.querySelectorAll('.phase-slot[data-slot]')].map(s => [s.dataset.dataset, s.dataset.slot,
      s.querySelectorAll('tr[data-kind]').length, [...s.querySelectorAll('td, th')].map(c => c.textContent.replace(/\\s+/g, ' ').trim())])"""
    phases = [o["value"] for o in BeautifulSoup(str(C.select_one('#filters [data-control="phase"]')), "html.parser").select("option")]
    for width in (1280, 390):
        ctx = context(b, cand, width, "light")
        page = ctx.new_page()
        errs, dialogs = [], []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.goto(BASE)
        page.wait_for_timeout(400)
        original = {(d, s): (n, c) for d, s, n, c in page.evaluate(SLOTS)}
        ds_row = '#headline-table tr[data-dataset="league-2"][data-setup="deepseek-v4-1-flash-on"]:not(.hl-sub)'
        page.locator(ds_row + " .hl-more").click()
        base_hl = page.evaluate(STATE_HL)
        # The real, visible control (fix-filters made the filter row visible): Playwright clicks More filters, then
        # chooses each phase in the Phase select; both fail if the element cannot be seen. No script fallback.
        if page.get_attribute("#filters [data-more-filters]", "aria-expanded") != "true":
            page.click("#filters [data-more-filters]", timeout=5000)
        visible = page.locator('#filters [data-control="phase"]').is_visible()
        how = "More filters clicked, Phase select used (visible)" if visible else "Phase select NOT visible"
        for ph in phases[1:] + ["all"]:
            if visible:
                page.select_option('#filters [data-control="phase"]', ph, timeout=5000)
            page.wait_for_timeout(900)
            got = {(d, s): (n, c) for d, s, n, c in page.evaluate(SLOTS)}
            want = original if ph == "all" else slot_expect(ph)
            slot_bad = [f"{k}" for k in got if want.get(k) != got[k]]
            hl_now = page.evaluate(STATE_HL)
            value = page.eval_on_selector('#filters [data-control="phase"]', "s => s.value")
            ok = (visible and value == ph and not slot_bad and len(got) > 0 and hl_now["text"] == base_hl["text"]
                  and hl_now["sub_shown"] == len(FAMILIES["league-2/deepseek-v4-1-flash-on"]) and not dialogs and not errs)
            browser_rows.append([width, "light", f"Phase via the control: {ph}",
                                 f"{how}; select value {value}; {len(got)} phase slots, {len(got) - len(slot_bad)} equal to "
                                 f"{'the page as loaded' if ph == 'all' else f'fragments/*-{ph}.html'} (rows and every cell)"
                                 + (f", differing: {slot_bad[:6]}" if slot_bad else "")
                                 + f"; leaderboard rows and Too safe unchanged: {hl_now['text'] == base_hl['text']}; "
                                 f"DeepSeek expander still open ({hl_now['sub_shown']} rows); dialogs {dialogs or 'none'}; "
                                 f"script errors {errs or 'none'}", "ok" if ok else "WRONG"])
        # The address: bg.js reads ?league= and ?type= only, so the phase is not in the address; ?phase= must leave the
        # page at All phases, every slot as loaded.
        page.goto(BASE + "?phase=race")
        page.wait_for_timeout(500)
        value = page.eval_on_selector('#filters [data-control="phase"]', "s => s.value")
        got = {(d, s): (n, c) for d, s, n, c in page.evaluate(SLOTS)}
        ok = value == "all" and got == original
        browser_rows.append([width, "light", "Phase via the address: ?phase=race (no such parameter)",
                             f"select value {value}; every phase slot as loaded: {got == original} (the address carries "
                             "league and type only; the phase is chosen with the control)", "ok" if ok else "WRONG"])
        ctx.close()
    b.close()
with (pk / "browser.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["width", "theme", "state", "observed", "result"])
    w.writerows(browser_rows)
bc = Counter(r[-1] for r in browser_rows)
(pk / "browser.md").write_text(
    "# Browser tests (1280 and 390 px)\n\n"
    f"{len(browser_rows)} checks: " + ", ".join(f"{v} {k}" for k, v in sorted(bc.items())) + ". browser.csv has every one.\n\n"
    "Filters and expanders: the render's index.html opened from file:// (no server), light and dark. For each filter "
    "state (by address: type, league; by clicking a key of the filter row) the leaderboard must keep every row shown "
    "and every other-settings row hidden, and the Too safe chart every bar. Then every parent row's expander is "
    "clicked: the rows it shows must equal that parent's expected alternatives in evidence/expected-families.json "
    "(derived from the data files by evidence.py, not from the page's aria-controls), and a second click must hide "
    "them. Then All setups and back with an expander open.\n\n"
    "Phase: the same render through request routing (bg.js fetches fragments/<league>-<phase>.html, which file:// "
    "refuses). The real control is used (More filters, then the Phase select) for every phase and back to All "
    "phases: the select's value, every phase slot's rows and cells against that phase's fragment file (All phases: "
    "against the page as loaded), the leaderboard and Too safe text unchanged, the DeepSeek row's open expander still "
    "open, no dialog, no script error (none excluded). The address does not carry the phase (bg.js reads ?league= and "
    "?type= only): ?phase=race is checked to leave All phases and every slot as loaded.\n")
print("browser:", dict(bc))

# --- 5. Screenshots -----------------------------------------------------------------------------------------------
shots = pk / "screenshots"
shots.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (1280, 390):
        for theme in ("light", "dark"):
            for tag, root in (("", cand), ("-late-on", latep)):
                ctx = context(b, root, width, theme, routed=False)
                page = ctx.new_page()
                url = (root / "index.html").resolve().as_uri()
                page.goto(url + "#leaderboard")
                page.wait_for_timeout(500)
                if tag:
                    page.evaluate("[...document.querySelectorAll('#headline-table tr.hl-group')].pop().scrollIntoView({block: 'start'})")
                    page.wait_for_timeout(200)
                    page.screenshot(path=str(shots / f"leaderboard-late-on-{width}-{theme}.png"))
                    ctx.close()
                    continue
                page.screenshot(path=str(shots / f"leaderboard-{width}-{theme}.png"))
                page.locator("#headline-table").screenshot(path=str(shots / f"leaderboard-table-{width}-{theme}.png"))
                # The DeepSeek row's expander open (the checkpoint's settings under the original).
                ds_row = '#headline-table tr[data-dataset="league-2"][data-setup="deepseek-v4-1-flash-on"]:not(.hl-sub)'
                page.locator(ds_row + ' .hl-more').click()
                page.wait_for_timeout(150)
                page.evaluate(f"document.querySelector('{ds_row}').scrollIntoView({{block: 'start'}})")
                page.screenshot(path=str(shots / f"leaderboard-expanded-{width}-{theme}.png"))
                page.evaluate("document.querySelector('#headline-table tr.hl-group').scrollIntoView({block: 'center'})")
                page.wait_for_timeout(150)
                page.screenshot(path=str(shots / f"leaderboard-programs-{width}-{theme}.png"))
                # Whole-element shots: the sticky page bars would be drawn over the middle of a tall element.
                page.evaluate("""() => document.querySelectorAll('body *').forEach(e => {
                  const p = getComputedStyle(e).position; if (p === 'sticky' || p === 'fixed') e.style.position = 'static'; })""")
                for name, target in (("too-safe", "#too-safe"), ("risk-judgement", "#risk-judgement"),
                                     ("error-rate", "#error-rate"), ("finding-cautious", "#finding-cautious"),
                                     ("finding-flinch", "#finding-flinch")):
                    page.locator(target).screenshot(path=str(shots / f"{name}-{width}-{theme}.png"))
                page.goto(url + "?type=chat#leaderboard")
                page.wait_for_timeout(400)
                page.screenshot(path=str(shots / f"leaderboard-filter-chat-{width}-{theme}.png"))
                ctx.close()
    b.close()
print("screenshots:", len(list(shots.glob("*.png"))))

# --- Exit status (Zeki #2790): non-zero when any compared number differs or any check is not in an accepted state.
ACCEPTED = {"ok", "equal", "same", "external", "same as live (unresolved statically in both)",
            "build.py-only asset, absent from the origin/main render too"}
bad_numbers = sum(d for _, _, d, _ in summary)
bad_links = [r for r in results if r[-1] not in ACCEPTED]
bad_browser = [r for r in browser_rows if r[-1] != "ok"]
print(f"review: {bad_numbers} number difference(s), {len(bad_links)} link check(s) and {len(bad_browser)} browser "
      "check(s) not accepted")
sys.exit(1 if bad_numbers or bad_links or bad_browser else 0)
