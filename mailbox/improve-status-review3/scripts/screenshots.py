"""Screenshots of the "Models and status" table (Ümit #3219): Playwright Chromium on file:// renders, light theme,
1280 and 375 wide; element shots with the sticky top bar made static. No HTTP server.

    ~/.pyenv/shims/python3 mailbox/improve-status-review3/scripts/screenshots.py SITE SELFTEST

SITE: the full build.py --no-image render of the frozen live state (REAL). SELFTEST: selftest_improve.py --keep DIR;
its pages/status-<state> are the default build (pre-registration only) on SYNTHETIC states, laid over a hard-link copy
of SITE (improve/ and data/v3/improve.json replaced) so links and styles resolve.
"""
import datetime
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE, SELF = Path(sys.argv[1]), Path(sys.argv[2])
I = SELF.parent / "status-shots"
D = Path(__file__).resolve().parent.parent / "screenshots"
D.mkdir(exist_ok=True)
for old in D.glob("*.png"):
    old.unlink()

SHOTS = [("REAL-frozen-page", SITE / "improve/index.html", None),
         ("REAL-frozen-status", SITE / "improve/index.html", "#improve-status")]
for state in ("none", "running-1", "paused", "complete-yes"):
    site = I / state
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(SITE, site, copy_function=lambda s, d: Path(d).hardlink_to(s))
    for rel in ("improve/index.html", "data/v3/improve.json"):
        (site / rel).unlink()
        shutil.copy(SELF / "pages" / f"status-{state}" / rel, site / rel)
    name = "done" if state == "complete-yes" else state
    SHOTS.append((f"SYNTHETIC-{name}-status", site / "improve/index.html", "#improve-status"))

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, page, sel in SHOTS:
        for w in (1280, 375):
            ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme="light")
            pg = ctx.new_page()
            url = page.as_uri()
            pg.goto(url, wait_until="load")
            out = D / f"improve-{name}-{w}.png"
            if sel:
                pg.evaluate("""() => { for (const e of document.querySelectorAll('*')) {
                    const p = getComputedStyle(e).position;
                    if (p === 'sticky' || p === 'fixed') e.style.setProperty('position', 'static', 'important'); } }""")
                pg.locator(sel).first.screenshot(path=str(out))
            else:
                h = min(pg.evaluate("document.documentElement.scrollHeight"), 3000)
                pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h}, full_page=True)
            over = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            print(f"{datetime.datetime.now(datetime.UTC):%F %T} UTC  {out.name}  <- {url}{' ' + sel if sel else ''}"
                  f"{'  [page wider than the viewport]' if over else ''}")
            ctx.close()
    b.close()
