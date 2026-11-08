"""Screenshots of the "Did they improve?" candidate (the learning-page reviews' method): Playwright Chromium on file://
renders from run_review.sh (no HTTP server), light theme, 1280 and 375 wide. Full pages are capped at 6000 px; sections
are element shots with the sticky top bar made static (so it is not stitched over them).

    ~/.pyenv/shims/python3 mailbox/improve-page-review/scripts/screenshots.py [SCRATCH]   (default /tmp/imp-review)

default-preregistration is the branch's whole-site render (the default build, PREREGISTRATION_ONLY on). For every other
state, <state>-site is a hard-link copy of that render with improve/ and data/v3/improve.json from page-<state>,
rendered with --with-results (review only). SYNTHETIC states come from selftest_improve.py; REAL-dry-run-* is the
harness's own dry-run file (no model call, placeholder lessons).
"""
import datetime
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

I = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/imp-review")
D = Path(__file__).resolve().parent.parent / "screenshots"
D.mkdir(exist_ok=True)
for old in D.glob("*.png"):
    old.unlink()

STATES = ("none", "running-1", "complete-yes", "complete-no", "mixed", "refused", "REAL-dry-run-rehashed",
          "REAL-dry-run-asis")
for state in STATES:
    site = I / f"{state}-site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(I / "out-branch", site, copy_function=lambda s, d: Path(d).hardlink_to(s))
    for rel in ("improve/index.html", "data/v3/improve.json"):
        (site / rel).unlink()
        shutil.copy(I / f"page-{state}" / rel, site / rel)

HEAD, MODELS, LESS = "header.page-head", "#improve-models", "#improve-lessons"
SHOTS = [("default-preregistration-page", "out-branch/improve/index.html", None),
         ("default-preregistration-models", "out-branch/improve/index.html", MODELS),
         ("experiments-card", "out-branch/experiments/index.html", "#improve")]
for st in ("SYNTHETIC-running-1", "SYNTHETIC-complete-yes", "SYNTHETIC-complete-no", "SYNTHETIC-mixed"):
    s = st.removeprefix("SYNTHETIC-")
    SHOTS += [(f"{st}-{n}", f"{s}-site/improve/index.html", sel) for n, sel in
              (("head", HEAD), ("models", MODELS), ("lessons", LESS))]
SHOTS += [("SYNTHETIC-complete-yes-page", "complete-yes-site/improve/index.html", None),
          ("none-head", "none-site/improve/index.html", HEAD),
          ("SYNTHETIC-refused-head", "refused-site/improve/index.html", HEAD)]
SHOTS += [(f"REAL-dry-run-rehashed-{n}", "REAL-dry-run-rehashed-site/improve/index.html", sel) for n, sel in
          (("head", HEAD), ("models", MODELS), ("lessons", LESS))]
SHOTS += [("REAL-dry-run-asis-head", "REAL-dry-run-asis-site/improve/index.html", HEAD)]

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, page, sel in SHOTS:
        for w in (1280, 375):
            ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme="light")
            pg = ctx.new_page()
            url = (I / page).as_uri()
            pg.goto(url, wait_until="load")
            out = D / f"improve-{name}-{w}.png"
            if sel:
                pg.evaluate("""() => { for (const e of document.querySelectorAll('*')) {
                    const p = getComputedStyle(e).position;
                    if (p === 'sticky' || p === 'fixed') e.style.setProperty('position', 'static', 'important'); } }""")
                if sel == LESS:  # open the first model's lessons and its first series, as a tap would
                    pg.evaluate("""() => { const m = document.querySelector('#improve-lessons details.improve-model');
                        if (m) { m.open = true; const s = m.querySelector('details.lp-series'); if (s) s.open = true; } }""")
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
