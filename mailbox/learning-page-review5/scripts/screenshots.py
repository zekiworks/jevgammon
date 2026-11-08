"""Review 5 screenshots: Playwright Chromium on file:// renders from run_review5.sh (no HTTP server). The theme is the
prefers-color-scheme the page's own head script reads. Full pages are capped at 6000 px; sections are element shots (with the sticky top bar made static, so it is not stitched over them).

    ~/.pyenv/shims/python3 mailbox/learning-page-review5/scripts/screenshots.py [SCRATCH]   (default /tmp/inv5)

default-preregistration is the branch's whole-site render (the default build, PREREGISTRATION_ONLY on). For every other
state, <state>-site is a hard-link copy of that render with learning/ and data/v3/learning-pilot.json from page-<state>,
rendered with --with-results (review only): real-complete (the REAL results), SYNTHETIC-running,
SYNTHETIC-smoke-running, SYNTHETIC-not-started (SYNTHETIC: subsets of the real series, never results) and none.
"""
import datetime
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

I = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/inv5")
D = Path(__file__).resolve().parent.parent / "screenshots"
D.mkdir(exist_ok=True)
for old in D.glob("*.png"):
    old.unlink()

STATES = ("real-complete", "SYNTHETIC-running", "SYNTHETIC-smoke-running", "SYNTHETIC-not-started", "none")
for state in STATES:
    site = I / f"{state}-site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(I / "out-branch", site, copy_function=lambda s, d: Path(d).hardlink_to(s))
    for rel in ("learning/index.html", "data/v3/learning-pilot.json"):
        (site / rel).unlink()
        shutil.copy(I / f"page-{state}" / rel, site / rel)

HEAD, RES, VERD, LESS = "header.page-head", "#learning-results", "#learning-verdict-section", "#learning-lessons"
# name, page, element selector (None: the page from the top, capped)
SHOTS = [("default-preregistration-page", "out-branch/learning/index.html", None)]
SHOTS += [(f"real-complete-{n}", "real-complete-site/learning/index.html", s) for n, s in
          (("status-line", HEAD), ("charts-and-tables", RES), ("verdict-and-lift", VERD), ("lessons", LESS),
           ("page", None))]
SHOTS += [(f"SYNTHETIC-running-{n}", "SYNTHETIC-running-site/learning/index.html", s) for n, s in
          (("status-line", HEAD), ("charts-and-tables", RES), ("verdict-pending", VERD), ("lessons", LESS))]
SHOTS += [(f"SYNTHETIC-smoke-running-{n}", "SYNTHETIC-smoke-running-site/learning/index.html", s) for n, s in
          (("status-line", HEAD), ("charts-and-tables", RES), ("verdict-pending", VERD))]
SHOTS += [(f"SYNTHETIC-not-started-{n}", "SYNTHETIC-not-started-site/learning/index.html", s) for n, s in
          (("status-line", HEAD), ("results-empty", RES))]
SHOTS += [("none-status-line", "none-site/learning/index.html", HEAD)]

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, page, sel in SHOTS:
        for w in (1280, 390):
            for theme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme=theme)
                pg = ctx.new_page()
                url = (I / page).as_uri()
                pg.goto(url, wait_until="load")
                out = D / f"learning-{name}-{w}-{theme}.png"
                if sel:
                    # Element shots scroll the page; the site's sticky top bar would be stitched over the element, so
                    # sticky and fixed elements are made static for these shots only (the page is otherwise as built).
                    pg.evaluate("""() => { for (const e of document.querySelectorAll('*')) {
                        const p = getComputedStyle(e).position;
                        if (p === 'sticky' || p === 'fixed') e.style.setProperty('position', 'static', 'important'); } }""")
                    pg.locator(sel).first.screenshot(path=str(out))
                else:
                    h = min(pg.evaluate("document.documentElement.scrollHeight"), 6000)
                    pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h}, full_page=True)
                over = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                print(f"{datetime.datetime.now(datetime.UTC):%F %T} UTC  {out.name}  <- "
                      f"{url.replace(str(I), '$SCRATCH')}{' ' + sel if sel else ''}"
                      f"{'  [page wider than the viewport]' if over else ''}")
                ctx.close()
    b.close()
