"""front-story review packet (Ümit #2570): numbers, links and deep links, screenshots, from the branch render and the
live mirror; reads only. Method of mailbox/pws-style/packet_build.py, adapted (data-league-pick keys All/1/2/3, the new
headline table and finding sections).
Usage: review.py WORKTREE LIVE_DIR BRANCH_RENDER_DIR OUT_DIR
Writes OUT_DIR/{source.patch, numbers.csv, numbers.md, links.csv, links.md, screenshots/}.
No HTTP server: the browser loads the pages through Playwright's request routing from the directories."""
import csv
import difflib
import json
import mimetypes
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

work, live, cand, pk = (Path(a) for a in sys.argv[1:5])
pk.mkdir(parents=True, exist_ok=True)

# --- 1. Source diff -----------------------------------------------------------------------------------------------
(pk / "source.patch").write_text(subprocess.run(
    ["git", "-C", str(work), "diff", "origin/learning-page...front-story", "--", "tools/site"],
    check=True, capture_output=True, text=True).stdout)


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


L, C = soup(live), soup(cand)
rows_csv, summary = [], []

# 2a. Every table cell of the live home page against the branch (the new headline table aside; its All setups panel is
# the live All leagues risk table and is compared here, keyed by its id-less position like every other table).
lt, ct = table_cells(L), table_cells(C, skip=("headline-table",))
diff_t = [k for k in lt if ct.get(k) != lt[k]]
for k in sorted(lt, key=str):
    (tid, ds, margin, cap, _), (rds, setup, name, _), col = k
    rows_csv.append(["home table cell", tid or cap[:60], rds or ds, setup or name, col, lt[k], ct.get(k, "MISSING"),
                     "equal" if ct.get(k) == lt[k] else "DIFF"])
extra = [k for k in ct if k not in lt]
for k in extra:
    rows_csv.append(["home table cell (branch only)", k[0][0] or k[0][3][:60], k[1][0], k[1][1] or k[1][2], k[2], "",
                     ct[k], "new"])
summary.append(("Home page: every live table cell (Risk, Quality, Confidence, Reasoning, Cost tabs, both margins, All "
                "leagues and each league; Leagues block; Close choices; Nackgammon) against the branch", len(lt),
                len(diff_t), len(extra)))


# 2b. Headline table: every cell against the live table cell of the same setup.
def live_col(pred, col):
    out = {}
    for (tkey, rkey, head), v in lt.items():
        if pred(tkey) and head == col:
            out.setdefault((rkey[0] or tkey[1], rkey[1]), v)
    return out


risk_all = lambda col: live_col(lambda t: t[0] == "panel-risk" and t[1] == "all" and t[2] == "0.001", col)
qual = lambda col: live_col(lambda t: t[0] == "panel-quality", col)
SRC = {"Risk judgement (95% interval)": (risk_all("Risk judgement"), 3), "Risks found": (risk_all("Risks found"), 9),
       "Right safety": (risk_all("Right safety"), 9), "Error rate (PR)": (qual("Error rate (PR), 95% interval"), 3),
       "$ per 1,000 decisions $ per 1M decisions": (qual("$ per 1,000 decisions"), 1)}
hl = C.select_one("#headline-table")
head = [norm(th.get_text(" ")) for th in hl.thead.find_all("th")]
hl_n = hl_d = 0
for tr in hl.tbody.find_all("tr", recursive=False):
    cells = tr.find_all(["td", "th"], recursive=False)
    k = (tr["data-dataset"], tr["data-setup"])
    for h, c in zip(head, cells):
        if h not in SRC:
            continue
        table, n = SRC[h]
        text = norm((c.select_one(".cost-1k") or c).get_text(" "))
        exp = table.get(k)
        ok = exp is not None and nums(text)[:n] == nums(exp)[:n] and (nums(text) or norm(text) in exp)
        hl_n += 1
        hl_d += not ok
        rows_csv.append(["headline cell (new)", h, k[0], k[1], h, exp if exp is not None else "MISSING IN LIVE", text,
                         "equal" if ok else "DIFF"])
summary.append(("Headline table (new): risk judgement and interval, risks found, right safety (All leagues Risk table, "
                "margin 0.001), error rate and interval, $ per 1,000 decisions (the league's Quality table) against the "
                "live cell of the same setup", hl_n, hl_d, 0))

# 2c. Finding sections: every value beside a bar against the clear-risk data file.
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
    lab = norm(li.select_one(".hbar-label").get_text(" "))
    name, lg = re.match(r"(.+) · League (\d)$", lab).groups()
    text = norm(li.select_one(".hbar-value").get_text(" "))
    exp = exp_scan.get((name, lg))
    ok = exp is not None and norm(exp) == text
    f_n += 1
    f_d += not ok
    rows_csv.append(["finding: Models are too cautious", "scan bias", f"league-{lg}", name, "bias", exp, text,
                     "equal" if ok else "DIFF"])
for li in C.select("#finding-flinch li.hbar"):
    name = norm(li.select_one(".hbar-label").get_text(" "))
    text = norm(li.select_one(".hbar-value").get_text(" "))
    e = exp_q1.get(name, {})
    exp = f'{e.get("with numbers")} | {e.get("board only")}' if e else None
    ok = exp is not None and norm(exp) == text
    f_n += 1
    f_d += not ok
    rows_csv.append(["finding: numbers on screen", "Q1 bias with numbers | board only", "", name, "bias", exp, text,
                     "equal" if ok else "DIFF"])
# Numbers in the finding sentences: each must be a value of the data file.
allv = {norm(v) for v in exp_scan.values()} | {norm(v) for d in exp_q1.values() for v in d.values()}
kept = re.search(r"Kept: ([\d,]+) of", " ".join(next(s for s in CR["sections"] if s["id"] == "clear-risk-scan")["notes"])).group(1)
for fid in ("finding-cautious", "finding-flinch"):
    txt = norm(C.select_one(f"#{fid} .finding-text").get_text(" "))
    for v in re.findall(r"[+\u2212-]?\d[\d.,]*\s?pp|[\d,]{5,}", txt):
        ok = norm(v) in allv or v == kept
        f_n += 1
        f_d += not ok
        rows_csv.append([f"finding sentence: {fid}", "number in the text", "", "", "value", "in clear-risk.json" if ok
                         else "NOT FOUND", v, "equal" if ok else "DIFF"])
summary.append(("Finding sections (new): every value beside a bar, and every number in the sentences, against "
                "data/v3/clear-risk.json (scan per-setup bias; Part 2 Q1 bias with numbers and board only)", f_n, f_d, 0))

# 2d. Every other page: the main content, byte for byte; 2e data files.
o_n = o_d = 0
cut = lambda s: s[s.index('<main id="main"'):s.index("</main>")] if '<main id="main"' in s else s
# The render's own time stamp ("updated 7 November 2026, 17:07 UTC") is the render time, not data: normalised.
stamp = lambda s: re.sub(r"updated \d+ \w+ \d{4}, \d\d:\d\d UTC", "updated STAMP", s)
frozen = 0
page_diffs = []
for f in sorted(live.rglob("index.html")):
    rel = f.relative_to(live)
    if str(rel) == "index.html":
        continue
    b = cand / rel
    if not b.is_file() and rel.parts[0] in ("archive", "results"):
        frozen += 1  # frozen snapshots: copied as they are at deploy, not rendered
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
        if f.name == "manifest.json":  # data_as_of is the render time; every live file entry must be the branch's
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
extra_d = [g for g in (cand / "data").rglob("*") if g.is_file() and g.suffix != ".html"
           and not (live / g.relative_to(cand)).is_file()]
for g in extra_d:
    rows_csv.append(["data file (branch only)", str(g.relative_to(cand)), "", "", "bytes", "", "branch", "new"])
summary.append(("Data files under data/, byte for byte (manifest.json without its generated time)", d_n, d_d, len(extra_d)))
(pk / "page-diffs.md").write_text("# Other pages: live against branch, where the main content differs\n\n" +
                                  ("\n".join(page_diffs) or "None.\n"))

with (pk / "numbers.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["what", "where", "dataset", "setup", "metric", "live", "branch", "result"])
    w.writerows(rows_csv)
lines = ["# Numbers: front-story render against live", "",
         f"Live: the deployed site's mirror ({live}); branch: the render of front-story "
         f"({subprocess.run(['git', '-C', str(work), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()})"
         " from a copy of the live state, the same results hash. numbers.csv has one line per compared value.", "",
         "| Compared | Values | Differences | New in branch, not in live |", "|---|---:|---:|---:|"]
lines += [f"| {w} | {n:,} | {d:,} | {e:,} |" for w, n, d, e in summary]
(pk / "numbers.md").write_text("\n".join(lines) + "\n")
print("numbers:", summary)


# --- 3. Links and deep links --------------------------------------------------------------------------------------
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


def context(browser, root, width, theme):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844})
    ctx.add_init_script(f"localStorage.setItem('theme','{theme}')")
    ctx.route("http://site.test/**", router(root))
    return ctx


BASE = "http://site.test/"
results = []

# 3a. Every link on the branch home page: the file exists in the render, and its #fragment is an id of that page. The
# same href is resolved on the live mirror too: a link that does not resolve in either tree statically (an absolute
# path into the sibling site; a #d… anchor that Every decision's script makes) is the same as live, not a break.
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


live_hrefs = {a["href"] for a in L.find_all("a", href=True)}
for a in C.find_all("a", href=True):
    h = a["href"]
    if re.match(r"^(https?:|mailto:)", h):
        results.append(["any", "home link (external, not fetched)", h, "", "", "", "", "external"])
        continue
    ok, why = resolve_link(cand, h)
    lok, lwhy = resolve_link(live, h)
    res = "ok" if ok else ("same as live (unresolved statically in both)" if not lok and (h in live_hrefs or h.startswith("/"))
                           else "BROKEN")
    results.append(["any", "home link", h, "", "", lwhy, why, res])

# 3b. Deep links in the browser at 1280 and 390, live against branch where the address exists on live; the new anchors
# on the branch only.
home_ids = sorted({t["id"] for t in L.find_all(id=re.compile(r"^lg-"))})
URLS = ["", "?league=league-1", "?league=league-2", "?league=league-3", "?league=shared", "?league=all",
        "?type=decision", "?type=chat", "?type=program", "?league=league-1&type=decision",
        "?tab=risk", "?tab=quality", "?tab=confidence", "?tab=reasoning", "?tab=cost", "?tab=stability",
        "?league=league-2&type=chat&tab=cost#board", "?league=league-3&tab=quality#board", "#board", "#board-panel",
        "#filters", "#close-choices-stage-b", "#nackgammon-paired", "#downloads", "#leagues-tabs", "#v3", "#v3-l1",
        "#allstar"] + [f"#{i}" for i in home_ids]
NEW = ["#leaderboard", "#finding-cautious", "#finding-flinch", "#risk-judgement", "#error-rate", "#cost", "#time",
       "?league=league-2#leaderboard", "?tab=risk#leaderboard", "?type=chat#risk-judgement",
       "decisions/?r=risk&c=rr", "method/", "decisions/", "method/#limits", "method/#statistics", "clear-risk/"]
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
LEAGUE_LABEL = {"All leagues": "All", "League 1": "1", "League 2": "2", "League 3": "3", "Shared positions": "Shared",
                "All types": "All"}  # the compact filter row's shorter key labels
lab = lambda s: "|".join(LEAGUE_LABEL.get(x, x) for x in s.split("|")) if s else s
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
            # The headline table's All setups toggle and back.
            if name == "branch":
                page.goto(BASE + "#leaderboard")
                page.wait_for_timeout(250)
                vis = lambda: page.evaluate("[...document.querySelectorAll('[data-headline-panel]')].filter(p => !p.hidden).map(p => p.dataset.headlinePanel).join('|')")
                seq = [vis()]
                for k in ("all", "best"):
                    page.click(f'[data-headline-view="{k}"]')
                    page.wait_for_timeout(150)
                    seq.append(vis())
                ok = seq == ["best", "all", "best"]
                results.append([width, "headline toggle", "All setups, then Best setting", "", "", "", " → ".join(seq),
                                "ok" if ok else "WRONG"])
                # Nackgammon Decision / Chat / All (Ümit #2647, Zeki #2656): the Unclear and additions note visible
                # in every state; rows of the summary table shown per state.
                page.goto(BASE + "#nackgammon-paired")
                page.wait_for_timeout(250)
                for pick in ("decision", "chat", "all", "decision"):
                    page.click(f'[data-nack-kind-pick="{pick}"]')
                    page.wait_for_timeout(120)
                    st = page.evaluate("""() => {
                      const n = document.querySelector('#nackgammon-paired .nack-always');
                      const vis = e => !!e && !!(e.offsetParent || e.getClientRects().length) && getComputedStyle(e).visibility !== 'hidden';
                      const rows = [...document.querySelectorAll('#nack-summary tbody tr')];
                      return { note: vis(n) ? n.textContent.trim() : 'NOT VISIBLE',
                               shown: rows.filter(r => !r.hidden).map(r => r.dataset.row),
                               points: [...document.querySelectorAll('#chart-nack g[data-setup]')].filter(g => g.style.display !== 'none').length,
                               pressed: [...document.querySelectorAll('[data-nack-kind-pick]')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.nackKindPick).join('|') };
                    }""")
                    ok = (st["note"].startswith("Unclear means the test can\u2019t tell, not that the scores are equal.")
                          and "were added after the results were read; the primary results are shown with and without them" in st["note"]
                          and st["pressed"] == pick and "Random" in st["shown"] and "GNUbg weak" in st["shown"])
                    results.append([width, "nackgammon type keys", f"click {pick}", "", "", "",
                                    f"pressed={st['pressed']}; rows shown={len(st['shown'])} ({', '.join(st['shown'])}); "
                                    f"chart points={st['points']}; note visible={st['note'] != 'NOT VISIBLE'}",
                                    "ok" if ok else "WRONG"])
            out[name] = (states, errors)
            ctx.close()
        for u, a, c in zip(URLS, out["live"][0], out["branch"][0]):
            a = dict(a, league=lab(a["league"]), type=lab(a["type"]))
            c = dict(c, league=lab(c["league"]), type=lab(c["type"]))
            same = all(a[k] == c[k] for k in KEYS) and a["path"] == c["path"]
            results.append([width, "address, live vs branch", u, a["path"], c["path"],
                            "; ".join(f"{k}={a[k]}" for k in KEYS), "; ".join(f"{k}={c[k]}" for k in KEYS),
                            "same" if same else "DIFFERENT"])
        for u, c in zip(NEW, out["branch"][0][len(URLS):]):
            ok = c["target"] in ("", "in view") and c["status"] == "loaded" and not c["overflow"]
            results.append([width, "address, branch only", u, "", c["path"], "",
                            "; ".join(f"{k}={c[k]}" for k in KEYS + ("overflow",)), "ok" if ok else "CHECK"])
        results.append([width, "script errors", "", "", "", "; ".join(out["live"][1]) or "none",
                        "; ".join(out["branch"][1]) or "none", "ok" if not out["branch"][1] else "ERRORS"])
    b.close()
with (pk / "links.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["width", "check", "address or action", "live address after load", "branch address after load",
                "live state", "branch state", "result"])
    w.writerows(results)
cnt = Counter(r[-1] for r in results)
by = Counter((r[1], r[-1]) for r in results)
(pk / "links.md").write_text(
    "# Links and deep links: front-story render\n\n"
    f"{len(results)} checks: " + ", ".join(f"{v} {k}" for k, v in sorted(cnt.items())) + ". links.csv has every one.\n\n"
    "| Check | Result | Count |\n|---|---|---:|\n" + "".join(f"| {k} | {r} | {v} |\n" for (k, r), v in sorted(by.items())) +
    "\nHome links: every href of the branch home page, the file in the render and its #fragment an id of the target "
    "page (external links listed, not fetched). Addresses: opened at 1280 px and 390 px (Playwright, request routing, no "
    "server) on the live mirror and the branch; compared: the address after the page's script ran, the selected tabs, "
    "the League (keys now All/1/2/3, mapped from the live labels) and Model type filters, the rows shown in the open "
    "Every number tab, and for an #anchor whether its element exists and is at the top of the window below a sticky "
    "bar. Branch-only addresses (new anchors, hero buttons' targets): loaded, target in view, no horizontal overflow.\n")
print("links:", dict(cnt))

# --- 4. Screenshots -----------------------------------------------------------------------------------------------
shots = pk / "screenshots"
shots.mkdir(exist_ok=True)
SHOTS = [("home-top", None), ("leaderboard", "#leaderboard"), ("finding-cautious", "#finding-cautious"),
         ("finding-flinch", "#finding-flinch"), ("risk-judgement", "#risk-judgement"), ("every-number", "#board-panel"),
         ("nackgammon-all", "#nackgammon-paired")]
with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (1280, 390):
        for theme in ("light", "dark"):
            ctx = context(b, cand, width, theme)
            page = ctx.new_page()
            for name, target in SHOTS:
                page.goto(BASE + (target or ""))
                page.wait_for_timeout(400)
                page.screenshot(path=str(shots / f"{name}-{width}-{theme}.png"))
            for pick in ("decision", "chat"):
                page.click(f'[data-nack-kind-pick="{pick}"]')
                page.wait_for_timeout(150)
                page.evaluate("document.getElementById('nackgammon-paired').scrollIntoView()")
                page.screenshot(path=str(shots / f"nackgammon-{pick}-{width}-{theme}.png"))
            page.goto(BASE)
            page.wait_for_timeout(400)
            page.screenshot(path=str(shots / f"home-full-{width}-{theme}.png"), full_page=True)
            ctx.close()
    b.close()
print("screenshots:", len(list(shots.glob("*.png"))))
