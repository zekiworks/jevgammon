"""suite-bar2 (Ümit #3501/#3507/#3532, turkce #3535): origin/main's render against the candidate's, Chromium (Playwright),
both served over HTTP from the same frozen state. Reads only.

    python3 browser.py HTTP_ROOT_URL BASE_NAME NEW_NAME OUT_DIR

At 375, 390 and 1280 px, light and dark, on home (the leaderboard, index.html), improve/, learning/ and about/, both renders:
- the sticky header's height (.site-header) and the suite strip's own height;
- no sideways page overflow (scrollWidth == clientWidth); the strip's own scroll (its scrollWidth vs clientWidth);
- every in-page anchor (#id of an h2/h3/section) lands with its top below the sticky header's bottom;
- home: a leaderboard row's details box opened (hover at 1280, tap at 375/390) sits inside the window, under the header;
- home 375: ranked leaderboard rows whose bottom is within two screen heights (from the top of the page).
Writes OUT_DIR/browser.md, browser.csv, screenshots/; exits 1 on any failed check."""
import csv
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root, base_name, new_name, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], Path(sys.argv[4])
(out / "screenshots").mkdir(parents=True, exist_ok=True)
PAGES = [("home", ""), ("improve", "improve/"), ("learning", "learning/"), ("about", "about/")]
RANKED = "#headline-table tbody tr[data-box]:not(.hl-sub):not(.reference)"
rows, fail = [], []

GEOM = """() => { const h = document.querySelector('.site-header'), s = document.querySelector('.suite-bar'),
  ul = s && s.querySelector('ul'), sc = [s, ul].find(e => e && e.scrollWidth > e.clientWidth + 1),
  links = s ? [...s.querySelectorAll('a')].map(a => { const r = a.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; }) : [];
  return {header: h.offsetHeight, strip: s ? s.offsetHeight : 0, pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          stripScroll: sc ? sc.scrollWidth - sc.clientWidth : 0, links, viewBar: getComputedStyle(document.documentElement).getPropertyValue('--view-bar-h')}; }"""
ANCHORS = "() => [...document.querySelectorAll('main h2[id], main h3[id], main section[id]')].filter(e => e.offsetParent).map(e => e.id).slice(0, 4)"
LAND = """id => { const e = document.getElementById(id), h = document.querySelector('.site-header').getBoundingClientRect().bottom;
  const at = document.documentElement.scrollHeight - innerHeight - scrollY < 2;  // page end: cannot scroll further
  return {top: Math.round(e.getBoundingClientRect().top), header: Math.round(h), atEnd: at}; }"""
BOX = """tr => { const b = document.getElementById(tr.dataset.box), r = b.getBoundingClientRect(),
  h = document.querySelector('.site-header').getBoundingClientRect().bottom;
  return {open: b.classList.contains('open'), top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left),
          right: Math.round(r.right), header: Math.round(h), vw: document.documentElement.clientWidth, vh: innerHeight}; }"""
FIRST = """sel => { const lim = 2 * innerHeight; return [...document.querySelectorAll(sel)].filter(tr => tr.offsetParent
  && tr.getBoundingClientRect().bottom + scrollY <= lim).length; }"""


def rec(render, width, theme, page, what, measured, ok=True):
    rows.append((render, width, theme, page, what, measured, "yes" if ok else "NO"))
    if not ok:
        fail.append(f"{render} {width} {theme} {page}: {what}: {measured}")


with sync_playwright() as p:
    br = p.chromium.launch()
    for render in (base_name, new_name):
        for width in (375, 390, 1280):
            for theme in ("light", "dark"):
                touch = width < 600
                ctx = br.new_context(viewport={"width": width, "height": 812 if touch else 900}, has_touch=touch,
                                     is_mobile=touch, color_scheme=theme)
                pg = ctx.new_page()
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                for name, path in PAGES:
                    url = f"{root}{render}/{path}"
                    pg.goto(url)
                    pg.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
                    pg.wait_for_timeout(250)
                    g = pg.evaluate(GEOM)
                    rec(render, width, theme, name, "header px", g["header"])
                    rec(render, width, theme, name, "strip px", g["strip"])
                    rec(render, width, theme, name, "--view-bar-h", g["viewBar"], g["viewBar"] == f"{g['header']}px")
                    rec(render, width, theme, name, "page overflow px", g["pageOverflow"], g["pageOverflow"] == 0)
                    rec(render, width, theme, name, "strip own scroll px", g["stripScroll"])
                    rec(render, width, theme, name, "strip links x", str(g["links"]))
                    if theme == "light" and width in (375, 1280):
                        pg.screenshot(path=str(out / "screenshots" / f"{render}-{name}-{width}-light.png"))
                    for aid in pg.evaluate(ANCHORS):
                        pg.goto(f"{url}#{aid}")
                        pg.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
                        pg.wait_for_timeout(200)
                        l = pg.evaluate(LAND, aid)
                        rec(render, width, theme, name, f"anchor #{aid} top/header", f"{l['top']}/{l['header']}",
                            l["top"] >= l["header"] or l["atEnd"])
                    if name == "home":
                        pg.goto(url)
                        pg.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
                        pg.wait_for_timeout(250)
                        if width == 375:
                            rec(render, width, theme, name, "ranked rows within 2 screens", pg.evaluate(FIRST, RANKED))
                        for i in (0, 4):
                            tr = pg.locator(RANKED).nth(i)
                            tr.scroll_into_view_if_needed()
                            nm = tr.locator(".model-name")
                            if touch:
                                nm.tap()
                            else:
                                bb = nm.bounding_box()
                                pg.mouse.move(bb["x"] + 10, bb["y"] + bb["height"] / 2, steps=4)
                            pg.wait_for_timeout(200)
                            b = tr.evaluate(BOX)
                            ok = b["open"] and b["top"] >= b["header"] and b["bottom"] <= b["vh"] + 1 and b["left"] >= 0 \
                                and b["right"] <= b["vw"] + 1
                            rec(render, width, theme, name, f"row {i + 1} box top/bottom/left/right (header, vw x vh)",
                                f"{b['top']}/{b['bottom']}/{b['left']}/{b['right']} ({b['header']}, {b['vw']}x{b['vh']})", ok)
                            if touch:
                                nm.tap()
                            else:
                                pg.mouse.move(2, 600)
                            pg.wait_for_timeout(150)
                rec(render, width, theme, "all", "script errors", str(errors), not errors)
                ctx.close()
    br.close()

with open(out / "browser.csv", "w", newline="") as f:
    csv.writer(f).writerows([("render", "width", "theme", "page", "what", "measured", "ok"), *rows])
key = lambda r: (r[1], r[2], r[3], r[4])  # noqa: E731
base = {key(r): r[5] for r in rows if r[0] == base_name}
md = [f"# suite-bar2 browser: {base_name} vs {new_name}\n", f"{len(rows)} checks, {len(fail)} failed.\n",
      "| width | theme | page | what | main | candidate | ok |", "|---|---|---|---|---|---|---|"]
md += [f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} | {base.get(key(r), '')} | {r[5]} | {r[6]} |" for r in rows if r[0] == new_name]
if fail:
    md += ["", "## Failures", *[f"- {x}" for x in fail]]
(out / "browser.md").write_text("\n".join(md) + "\n")
print(f"{len(rows)} checks, {len(fail)} failed")
sys.exit(1 if fail else 0)
