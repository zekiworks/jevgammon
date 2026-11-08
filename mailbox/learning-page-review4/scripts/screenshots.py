"""Review 4 screenshots of the changed states: Playwright Chromium on file:// renders from run_review4.sh (no HTTP
server). The theme is the prefers-color-scheme the page's own head script reads. Full pages are capped at 6000 px;
sections are element shots.

    ~/.pyenv/shims/python3 mailbox/learning-page-review4/scripts/screenshots.py [SCRATCH]   (default /tmp/inv)

learning-tab-default-preregistration is the branch's whole-site render (the default build, PREREGISTRATION_ONLY on).
synthetic-<state>-site is a hard-link copy of it with learning/ and data/v3/learning-pilot.json from
page-synthetic-<state>, rendered with --with-results (review only): complete, running and rejected (the complete
fixture with an unknown top-level key). SYNTHETIC fixtures: test data, never results.
"""
import datetime
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

I = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/inv")
ONLY = sys.argv[2] if len(sys.argv) > 2 else ""  # optional: retake only the shots whose name starts with this
D = Path(__file__).resolve().parent.parent / "screenshots"
D.mkdir(exist_ok=True)
for old in D.glob(f"{ONLY}*.png"):
    old.unlink()

for state in ("complete", "running", "rejected"):
    if not (I / f"page-synthetic-{state}").exists():
        continue
    site = I / f"synthetic-{state}-site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(I / "out-branch", site, copy_function=lambda s, d: Path(d).hardlink_to(s))
    for rel in ("learning/index.html", "data/v3/learning-pilot.json"):
        (site / rel).unlink()
        shutil.copy(I / f"page-synthetic-{state}" / rel, site / rel)

# name, page, element selector (None: the page from the top)
SHOTS = [
    ("learning-tab-default-preregistration", "out-branch/learning/index.html", None),
    ("learning-tab-SYNTHETIC-complete", "synthetic-complete-site/learning/index.html", None),
    ("learning-tab-SYNTHETIC-complete-charts", "synthetic-complete-site/learning/index.html", "#learning-chart"),
    ("learning-tab-SYNTHETIC-complete-budget", "synthetic-complete-site/learning/index.html", "#learning-budget"),
    ("learning-tab-SYNTHETIC-running", "synthetic-running-site/learning/index.html", None),
    ("learning-tab-SYNTHETIC-rejected", "synthetic-rejected-site/learning/index.html", None),
]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, page, sel in (s for s in SHOTS if s[0].startswith(ONLY)):
        for w in (1280, 390):
            for theme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme=theme)
                pg = ctx.new_page()
                url = (I / page).as_uri()
                pg.goto(url, wait_until="load")
                out = D / f"{name}-{w}-{theme}.png"
                if sel:
                    pg.locator(sel).first.screenshot(path=str(out))
                else:
                    h = min(pg.evaluate("document.documentElement.scrollHeight"), 6000)
                    pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h}, full_page=True)
                print(f"{datetime.datetime.now(datetime.UTC):%F %T} UTC  {out.name}  <- {url}{' ' + sel if sel else ''}")
                ctx.close()
    b.close()
