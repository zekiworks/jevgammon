"""The learning-explore review's screenshots: Playwright Chromium on file:// renders from run_review.sh (no HTTP server).
The theme is the prefers-color-scheme the page's own head script reads. Element shots are taken with the site's sticky
top bar made static, so it is not stitched over them; full pages are capped at 20,000 px.

    ~/.pyenv/shims/python3 mailbox/learning-explore-review/scripts/screenshots.py [SCRATCH]   (default /tmp/inv6)

explore: the branch's production-mode whole-site render (STATE/learning = the REAL pilot and the REAL exploratory
file). malformed-explore and no-explore: hard-link copies of it with learning/ and its data file from
page-malformed-explore (SYNTHETIC malformed exploratory file) and page-no-explore.
"""
import datetime
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

I = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/inv6")
D = Path(__file__).resolve().parent.parent / "screenshots"
D.mkdir(exist_ok=True)
for old in D.glob("*.png"):
    old.unlink()
for state in ("malformed-explore", "no-explore"):
    site = I / f"{state}-site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(I / "out-branch", site, copy_function=lambda s, d: Path(d).hardlink_to(s))
    for rel in ("learning/index.html", "data/v3/learning-pilot.json"):
        (site / rel).unlink()
        shutil.copy(I / f"page-{state}" / rel, site / rel)

PAGE = "out-branch/learning/index.html"
SHOTS = [("explore-top-line", PAGE, "#learning-run-line"), ("explore-charts-and-tables", PAGE, "#learning-results"),
         ("explore-verdict", PAGE, "#learning-verdict-section"), ("explore-exploratory-block", PAGE, "#learning-explore"),
         ("explore-full-page", PAGE, None),
         ("SYNTHETIC-malformed-explore-exploratory-block", "malformed-explore-site/learning/index.html",
          "#learning-explore"),
         ("no-explore-full-page", "no-explore-site/learning/index.html", None)]
UNSTICK = """() => { for (const e of document.querySelectorAll('*')) {
    const p = getComputedStyle(e).position;
    if (p === 'sticky' || p === 'fixed') e.style.setProperty('position', 'static', 'important'); } }"""
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
                    pg.evaluate(UNSTICK)
                    pg.locator(sel).first.screenshot(path=str(out))
                else:
                    h = min(pg.evaluate("document.documentElement.scrollHeight"), 20000)
                    pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h}, full_page=True)
                over = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                print(f"{datetime.datetime.now(datetime.UTC):%F %T} UTC  {out.name}  <- "
                      f"{url.replace(str(I), '$SCRATCH')}{' ' + sel if sel else ''}"
                      f"{'  [page wider than the viewport]' if over else ''}")
                ctx.close()
    b.close()
