"""ct-brief review (Ümit #2938): numbers against live (label-aware), old URLs and anchors, links, browser checks and
screenshots, from the ct-brief render, the origin/main render (same retained state) and the live mirror. Reads only.

    python3 review.py LIVE_DIR BASE_RENDER NEW_RENDER OUT_DIR HTTP_ROOT_URL

HTTP_ROOT_URL serves the parent of NEW_RENDER (http.server), e.g. http://127.0.0.1:8765/ with NEW_RENDER = /tmp/ctb/out-head.
Writes OUT_DIR/{numbers.md, numbers.csv, anchors.md, anchors.csv, links.md, browser.md, browser.csv, pages.md,
screenshots/} and the two screenshots for Ümit into OUT_DIR/../for-umit/. Exits 1 on any number difference or failed
check."""
import csv
import gzip
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

live, base, new, out = (Path(a) for a in sys.argv[1:5])
root_url = sys.argv[5].rstrip("/") + "/" + new.name + "/"
out.mkdir(parents=True, exist_ok=True)
(out / "screenshots").mkdir(exist_ok=True)
umit = out.parent / "for-umit"
umit.mkdir(exist_ok=True)
fail = []
NUM = re.compile(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: Counter(x.replace(",", "").replace("\u2212", "-").lstrip("+") for x in NUM.findall(t))  # noqa: E731
norm = lambda t: re.sub(r"\s+", " ", t).strip()  # noqa: E731


def soup(root: Path, path=""):
    return BeautifulSoup((root / path / "index.html").read_text(), "html.parser")


def text(el) -> str:
    return norm(el.get_text(" ")) if el else ""


L_HOME, N_HOME = soup(live), soup(new)
MOVED = json.loads(N_HOME.find(id="moved-anchors").string)
pages_new = {}


def new_page(path):
    if path not in pages_new:
        pages_new[path] = soup(new, path)
    return pages_new[path]


def where(i):
    """(page path, id) where the live home id lives in the new render."""
    if N_HOME.find(id=i):
        return "", i
    if i in MOVED:
        p, _, h = MOVED[i].partition("#")
        return p, h or None
    return None, None


# --- 1. Numbers ------------------------------------------------------------------------------------------------------
rows = []
summary = []

# 1a. Every table of the live home page, cell by cell, against the same table (its block's id and caption) where it
# is now. The leaderboard (#headline-table) is 1c.
def tables(s):
    out_ = {}
    for t in s.find_all("table"):
        anc = next((a.get("id") for a in t.parents if a.get("id") and a.name != "html"), "")
        cap = text(t.find("caption"))
        key = (anc, cap, t.get("id") or "")
        k = 0
        while key + (k,) in out_:
            k += 1
        out_[key + (k,)] = t
    return out_


def cells(t):
    head = [text(th) for th in t.find("thead").find_all("th")] if t.find("thead") else []
    got = {}
    for r, tr in enumerate(t.find("tbody").find_all("tr", recursive=False) if t.find("tbody") else []):
        tds = tr.find_all(["td", "th"], recursive=False)
        label = text(tds[0]) if tds else str(r)
        for c, td in enumerate(tds):
            got[(r, label, head[c] if c < len(head) else str(c))] = text(td)
    return got


lt = tables(L_HOME)
n_cells = n_diff = n_tables = 0
for key, t in lt.items():
    anc, cap, tid, k = key
    if tid == "headline-table":
        continue
    p, h = where(anc) if anc else ("", None)
    if p is None:
        fail.append(f"table {key}: its block #{anc} is nowhere in the new render")
        continue
    nt = tables(new_page(p)).get((h or anc, cap, tid, k))
    if nt is None:
        fail.append(f"table {key}: not found on {p or 'home'}")
        continue
    a, b = cells(t), cells(nt)
    n_tables += 1
    for c, v in a.items():
        n_cells += 1
        if b.get(c) != v:
            n_diff += 1
            rows.append(["home table cell", anc, cap, str(c), v, b.get(c)])
summary.append(("Live home tables, cell by cell (header and row label), where each now is", n_tables, n_cells, n_diff))

# 1b. Every id'd block of the live home page: its numbers (multiset) against the same id where it now is. Blocks that
# stayed on the home page and were reshaped (the leaderboard, the hero, the old finding sections) are 1c / 1d.
RESHAPED = {"leaderboard", "finding-cautious", "finding-flinch", "findings", "how-numbers", "headline-table",
            "too-safe", "main"}
n_blocks = n_bdiff = 0
for el in L_HOME.find("main").find_all(id=True):
    i = el["id"]
    if i in RESHAPED or any(a.get("id") in RESHAPED - {"main"} for a in el.parents) or i.startswith("hl-"):
        continue
    p, h = where(i)
    if p is None:
        fail.append(f"#{i}: not on the new home page and not in the moved-anchors map")
        continue
    ne = new_page(p).find(id=h) if h else new_page(p).find("main")
    if ne is None:
        fail.append(f"#{i}: maps to {p}#{h}, which does not exist")
        continue
    n_blocks += 1
    if nums(text(el)) != nums(text(ne)):
        n_bdiff += 1
        rows.append(["home block numbers", i, f"{p}#{h}", "", text(el)[:300], text(ne)[:300]])
summary.append(("Live home id'd blocks (every id, nested ones too): numbers as a multiset where each now is",
                n_blocks, n_blocks, n_bdiff))

# 1c. The leaderboard: every row (rank, model, risk judgement cell) against live; each details box's numbers against
# the live box (same numbers, lines reordered, "late entry" added); each wide cell's value in the row's box.
def lb(s):
    t = s.find(id="headline-table")
    out_ = []
    for tr in t.find("tbody").find_all("tr", recursive=False):
        if "hl-group" in (tr.get("class") or []):
            continue
        tds = tr.find_all("td", recursive=False)
        box = tr.find(class_="hl-box")
        name = text(tr.find(class_="model-name"))
        out_.append(dict(key=(tr.get("data-dataset"), tr.get("data-setup")), sub="hl-sub" in (tr.get("class") or []),
                         rank=text(tds[0]), name=name, judgement=text(tr.find("td", class_="hl-judgement")),
                         box=text(box), wide=[text(td) for td in tr.find_all("td", class_="hl-wide")],
                         type=text(tr.find(class_="hl-type"))))
    return out_


lrows, nrows = lb(L_HOME), lb(N_HOME)
lby = {r["key"]: r for r in lrows}
n_lb = n_lbd = 0
for r in nrows:
    l = lby.get(r["key"])
    n_lb += 1
    if not l:
        n_lbd += 1
        rows.append(["leaderboard row", str(r["key"]), "", "", "", "not in live"])
        continue
    for f in ("rank", "name", "judgement"):
        if l[f] != r[f]:
            n_lbd += 1
            rows.append(["leaderboard row", str(r["key"]), f, "", l[f], r[f]])
    lb_n = nums(l["box"])
    nb_n = nums(r["box"])
    if lb_n != nb_n:
        n_lbd += 1
        rows.append(["details box numbers", str(r["key"]), "", "", str(sorted((lb_n - nb_n).elements())),
                     str(sorted((nb_n - lb_n).elements()))])
    for v in r["wide"]:
        for x in nums(v):
            if x not in nums(r["box"]):
                n_lbd += 1
                rows.append(["wide cell not in its box", str(r["key"]), "", "", v, r["box"][:200]])
if {r["key"] for r in lrows} != {r["key"] for r in nrows}:
    n_lbd += 1
    rows.append(["leaderboard rows", "", "", "", str(sorted(map(str, {r["key"] for r in lrows} - {r["key"] for r in nrows}))),
                 str(sorted(map(str, {r["key"] for r in nrows} - {r["key"] for r in lrows})))])
summary.append(("Leaderboard rows (rank, model, risk judgement), details-box numbers, wide cells within their box",
                n_lb, n_lb, n_lbd))

# 1d. The old Too safe chart (under finding a, in a details) and the old clear-risk bias chart (Clear risk page):
# every bar label and value against live.
def bars(s, sel):
    return {text(li.find(class_="hbar-label")): text(li.find(class_="hbar-value")) for li in s.select(sel)}


for name, a, b in (("Too safe bars", bars(L_HOME, "#too-safe li.hbar"), bars(N_HOME, "#too-safe li.hbar")),
                   ("Clear-risk bias bars (home -> Clear risk page)", bars(L_HOME, "#finding-cautious li.hbar"),
                    bars(new_page("clear-risk/"), "#clear-risk-bias li.hbar")),
                   ("Numbers on screen bars (finding c)", bars(L_HOME, "#finding-flinch li.hbar"),
                    bars(N_HOME, "#finding-flinch li.hbar"))):
    d = sum(1 for k in a if b.get(k) != a[k]) + len(set(b) - set(a))
    for k in a:
        if b.get(k) != a[k]:
            rows.append([name, k, "", "", a[k], b.get(k)])
    summary.append((name, len(a), len(a), d))
    n_bdiff += d

# 1e. Every other page: the main content's text, live against the new render; data files and decision pages byte for
# byte (gz decompressed).
changed_ok = {"", "leagues/", "about/", "experiments/", "highlights/", "decisions/", "clear-risk/"}
pg_rows = []
n_same = 0
for p in sorted(live.rglob("index.html")):
    rel = str(p.parent.relative_to(live)) + "/" if p.parent != live else ""
    if rel.startswith(("archive/", "results/")):
        continue
    q = new / rel / "index.html"
    if not q.exists():
        fail.append(f"page {rel}: missing in the new render")
        continue
    a, b = text(soup(live, rel).find("main")), text(soup(new, rel).find("main"))
    if a == b:
        n_same += 1
    else:
        pg_rows.append((rel, rel in changed_ok, nums(a) == nums(b) or rel in changed_ok))
        if rel not in changed_ok:
            fail.append(f"page {rel}: main content differs from live and the page is not one this change touches")
summary.append(("Other pages: main content text identical to live", n_same + len(pg_rows), n_same + len(pg_rows),
                len([r for r in pg_rows if not r[1]])))
n_files = n_fd = 0
for p in sorted(live.rglob("*")):
    rel = p.relative_to(live)
    if not p.is_file() or rel.parts[0] not in ("data", "decisions") or p.suffix == ".html":
        continue
    n_files += 1
    q = new / rel
    x = p.read_bytes()
    y = q.read_bytes() if q.exists() else b""
    if p.suffix == ".gz":
        x, y = gzip.decompress(x), gzip.decompress(y) if y else b""
    if x != y and str(rel) != "data/manifest.json":
        n_fd += 1
        rows.append(["data file", str(rel), "", "", "differs", ""])
extra = sorted(str(q.relative_to(new)) for q in new.rglob("*") if q.is_file() and q.relative_to(new).parts[0] in ("data", "decisions")
               and not (live / q.relative_to(new)).exists())
summary.append((f"Data files and decision pages, byte for byte (gz decompressed; manifest.json's time stamps aside); new "
                f"files: {extra or 'none'}", n_files, n_files, n_fd + len(extra)))

with open(out / "numbers.csv", "w", newline="") as f:
    csv.writer(f).writerows([["what", "where", "label", "cell", "live", "new"]] + rows)
total = sum(s[3] for s in summary)
md = ["# Numbers: the ct-brief render against live", "",
      "Live: the mirror of https://zekiworks.github.io/analysis/backgammon/ (results a8708ed6). The new render is "
      "rendered from the retained computed state (no compute), data-as-of label set to live's.", "",
      "| Check | Items | Values | Differences |", "|---|---:|---:|---:|"]
md += [f"| {a} | {b:,} | {c:,} | {d} |" for a, b, c, d in summary]
md += ["", f"**Total differences: {total}.** Every difference is in `numbers.csv`.", "",
       "Pages whose main content changed (expected: the pages this change touches):", ""]
md += [f"- `{r[0] or 'home'}`" for r in pg_rows]
(out / "numbers.md").write_text("\n".join(md) + "\n")
if total:
    fail.append(f"numbers: {total} differences")

# --- 2. Links: every tab and page link answers 200 --------------------------------------------------------------------
link_rows = []
targets = {}
for path in ("", "decisions/", "highlights/", "experiments/", "about/", "leagues/", "nackgammon/"):
    s = new_page(path)
    sel = ("nav.site-tabs a, .hero-links a, .decisions-links a, .experiment-card a, .about-links a, .footer-links a, "
           "nav.more-pages a")
    for a in s.select(sel):
        href = a.get("href")
        if href.startswith("http"):
            targets.setdefault(href, (path, text(a)))
            continue
        u = (root_url + path) if path else root_url
        from urllib.parse import urljoin
        targets.setdefault(urljoin(u, href.split("#")[0]), (path, text(a)))
n_ok = 0
for u, (path, label) in sorted(targets.items()):
    if not u.startswith(root_url):
        link_rows.append((label, u, "external, not fetched"))
        continue
    try:
        code = urllib.request.urlopen(u).status
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", str(e))
    link_rows.append((label, u.replace(root_url, ""), code))
    n_ok += code == 200
    if code != 200:
        fail.append(f"link {u}: {code}")
tabs = [a.get("href") for a in N_HOME.select("nav.site-tabs a")]
(out / "links.md").write_text("# Links\n\nEvery link of the header tabs, the hero buttons, the Decisions, Experiments and "
                              "About link rows and the footer, on the five tab pages, Leagues and Nackgammon, "
                              f"fetched from the render over HTTP: **{n_ok} of {len([r for r in link_rows if r[2] != 'external, not fetched'])} "
                              "answer 200**.\n\n| Label | Address | Status |\n|---|---|---|\n"
                              + "".join(f"| {a} | `{b}` | {c} |\n" for a, b, c in link_rows))

# --- 3 and 4. Browser: old anchors, tab rows, the first screen, the leaderboard's first row, screenshots ---------------
an_rows, br_rows = [], []
live_ids = [el["id"] for el in L_HOME.find_all(id=True)]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    # 3. Every id of the live home page, opened on the new home page at 1280 (and every 10th at 390).
    for width in (1280, 390):
        ctx = b.new_context(viewport={"width": width, "height": 900 if width > 600 else 844})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        ids = live_ids if width == 1280 else live_ids[::10]
        for i in ids:
            pg.goto(root_url + "#" + i)
            pg.wait_for_timeout(250)
            final = pg.url.replace(root_url, "")
            h = final.split("#", 1)[1] if "#" in final else ""
            st = pg.evaluate("""h => { const el = h && document.getElementById(decodeURIComponent(h));
                if (!el) return {exists: false};
                const r = el.getBoundingClientRect(); const vis = !!(el.offsetParent || el.getClientRects().length);
                return {exists: true, visible: vis, inview: vis && r.bottom > 0 && r.top < innerHeight}; }""", h)
            kind = ("details box (opens on tap / hover)" if i.endswith("-box") and i.startswith("hl-") else
                    "other-settings row (opens with its expander)" if re.match(r"hl-(p-)?\d+-\d+$", i) else "")
            ok = st["exists"] and (st["inview"] or kind or not st["visible"])
            an_rows.append((width, i, final, st["exists"], st.get("visible"), st.get("inview"), kind))
            if not st["exists"]:
                fail.append(f"anchor #{i} at {width}: lands on {final}, element missing")
        ctx.close()
    # 4. Tab rows, overflow, the first screen, row 1, screenshots.
    for width in (375, 390, 1280):
        for theme in ("light", "dark"):
            ctx = b.new_context(viewport={"width": width, "height": 844 if width < 600 else 900}, color_scheme=theme,
                                has_touch=width < 600)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            for path in ("", "decisions/", "highlights/", "experiments/", "about/", "leagues/", "nackgammon/"):
                pg.goto(root_url + path)
                pg.wait_for_timeout(400)
                r = pg.evaluate("""() => ({
                    tabRows: document.querySelectorAll('nav.site-tabs').length,
                    chipRows: document.querySelectorAll('main .part-links, main nav.face-nav[aria-label="On this page"], body.home main nav.face-nav, body.home main #filters').length,
                    overflow: document.documentElement.scrollWidth - innerWidth,
                    current: [...document.querySelectorAll('nav.site-tabs a[aria-current]')].map(a => a.textContent.trim()).join(',')})""")
                ok = r["tabRows"] == 1 and r["overflow"] <= 0 and (path != "" or r["chipRows"] == 0)
                br_rows.append((width, theme, path or "home", "one tab row, no chip row on home, no sideways overflow",
                                json.dumps(r), ok))
                if not ok:
                    fail.append(f"browser {width} {theme} {path or 'home'}: {r}")
                pg.screenshot(path=str(out / "screenshots" / f"{(path or 'home').strip('/')}-{width}-{theme}.png"))
            pg.goto(root_url)
            pg.wait_for_timeout(400)
            m = pg.evaluate("""() => {
                const rows = [...document.querySelectorAll('#headline-table tbody tr:not(.hl-sub):not(.hl-group)')];
                const hero = document.querySelector('.hero-card').getBoundingClientRect();
                const r = i => rows[i].getBoundingClientRect().bottom + scrollY;
                const first = rows[0];
                return {screen: innerHeight, heroBottom: hero.bottom + scrollY, row1Bottom: r(0), row3Bottom: r(2),
                        row1: first.querySelector('.model-name').textContent.trim(),
                        row1Box: first.querySelector('.hl-box').textContent,
                        row1Score: first.querySelector('.hl-val').firstChild.textContent.trim(),
                        row1Tag: (first.querySelector('.hl-tag') || {}).textContent || '',
                        deepseek1017Row: rows.some(tr => /1017/.test(tr.querySelector('.model-name').textContent)),
                        wideShown: getComputedStyle(first.querySelector('td.hl-wide')).display !== 'none',
                        tick: getComputedStyle(first.querySelector('.hl-safe')).backgroundColor};
            }""")
            within = m["row3Bottom"] <= 2 * m["screen"]
            row1 = "GPT-6 Astra (high)" in m["row1Box"] and m["row1Score"] == "74.4" and "late entry" in m["row1Tag"]
            wide_ok = m["wideShown"] == (width >= 900)
            for what, ok in (("hero + first 3 leaderboard rows within two screen heights", within),
                             ("row 1: GPT-6 Astra (high) 74.4, late entry", row1),
                             ("no own DeepSeek V4.1 Flash 1017 row", not m["deepseek1017Row"]),
                             ("wide columns only at >= 900 px", wide_ok),
                             ("white tick at 50", m["tick"] == "rgb(255, 255, 255)"),
                             ("no script error", not errs)):
                br_rows.append((width, theme, "home", what, json.dumps({k: v for k, v in m.items() if k != "row1Box"}) if what.startswith("hero") else "", ok))
                if not ok:
                    fail.append(f"browser {width} {theme}: {what} ({m if what.startswith('hero') else errs})")
            if theme == "light" and width in (375, 1280):
                h = 2 * m["screen"]
                pg.set_viewport_size({"width": width, "height": h})
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(umit / f"front-page-{width}px-light{'-two-screens' if width < 600 else ''}.png"))
                pg.set_viewport_size({"width": width, "height": m["screen"]})
            if width == 375 and theme == "light":
                pg.locator("#headline-table tbody tr:not(.hl-sub):not(.hl-group) .model-name").first.tap()
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(out / "screenshots" / "home-375-light-row1-box.png"))
            ctx.close()
    b.close()

with open(out / "anchors.csv", "w", newline="") as f:
    csv.writer(f).writerows([["width", "old home id", "lands on", "exists", "visible", "in view", "note"]] + an_rows)
lands = Counter("home" if not r[2].split("#")[0] else r[2].split("#")[0] for r in an_rows if r[0] == 1280)
(out / "anchors.md").write_text(
    "# Old home anchors\n\n"
    f"Every id of the live home page ({len(live_ids)}) opened as `#id` on the new home page in a browser at 1280 px, "
    f"every 10th also at 390 px ({len([r for r in an_rows if r[0] == 390])}). The page the anchor lands on, and whether "
    "the element exists there, is shown and is in view (details boxes and other-settings rows exist and open on tap / "
    "hover or with their expander, as on live).\n\n"
    f"- Missing: {sum(1 for r in an_rows if not r[3])}\n"
    f"- In view, or by design hidden until opened: {sum(1 for r in an_rows if r[3] and (r[5] or r[6] or not r[4]))} of {len(an_rows)}\n\n"
    "Where they land (1280 px): " + ", ".join(f"{k}: {v}" for k, v in sorted(lands.items())) + "\n\n"
    "Every row: `anchors.csv`.\n")
with open(out / "browser.csv", "w", newline="") as f:
    csv.writer(f).writerows([["width", "theme", "page", "check", "measured", "ok"]] + br_rows)
(out / "browser.md").write_text(
    "# Browser checks\n\n375, 390 and 1280 px, light and dark, Chromium (Playwright), served over HTTP.\n\n"
    f"**{sum(1 for r in br_rows if r[5])} of {len(br_rows)} ok.**\n\n| Width | Theme | Page | Check | Measured | OK |\n"
    "|---:|---|---|---|---|---|\n" + "".join(f"| {a} | {b_} | {c} | {d} | `{e[:160]}` | {'yes' if g else '**no**'} |\n"
                                              for a, b_, c, d, e, g in br_rows))
print("\n".join(fail) if fail else "review: 0 failures")
sys.exit(1 if fail else 0)
