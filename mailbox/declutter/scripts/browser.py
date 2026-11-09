"""declutter browser checks (Ümit via Zeki #3521), Chromium (Playwright), renders served over HTTP. Reads only.

usage: browser.py URL_ROOT BASE_NAME NEW_NAME OUT_DIR
Every top-level backgammon page plus two model pages, at 375 / 390 / 1280 px, light and dark, both renders:
 - no sideways overflow (document scrollWidth - innerWidth <= 0), no script error;
 - heading sizes: h1 as --h1, every visible h2 <= h1 and every h3 <= h2 (largest of each), the h1's line count;
 - About: the moved board drawn in the board colours (felt not black); front page: no hero buttons, the leaderboard's top and its first row's bottom against the first screen.
Fails (exit 1) only on the candidate. Writes OUT_DIR/browser.md, browser.csv and the screenshots (for-umit/,
screenshots/)."""
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root, base_name, new_name, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], Path(sys.argv[4])
for d in ("for-umit", "screenshots"):
    (out / d).mkdir(parents=True, exist_ok=True)
PAGES = ["", "leagues/", "decisions/", "highlights/", "experiments/", "about/", "method/", "data/", "matches/",
         "nackgammon/", "clear-risk/", "learning/", "improve/", "new-models/", "models/", "compare/", "phases/",
         "disagreements/", "archive/2026-10-23/"]
models = sorted(p.parent.relative_to(Path("/tmp") / new_name).as_posix() + "/"
                for p in (Path("/tmp") / new_name / "models").glob("*/*/index.html"))
PAGES += [models[0], models[-1]]
MEASURE = """() => {
  const vis = e => e.offsetParent !== null && e.getBoundingClientRect().height > 1 && e.getBoundingClientRect().width > 1;
  const fs = e => parseFloat(getComputedStyle(e).fontSize);
  const h1 = document.querySelector('main h1');
  const max = sel => Math.max(0, ...[...document.querySelectorAll(sel)].filter(vis).map(fs));
  const lb = document.getElementById('leaderboard');
  const row = document.querySelector('#headline-table tbody tr');
  return {theme: document.documentElement.dataset.theme || '', over: document.documentElement.scrollWidth - innerWidth,
    h1: h1 ? fs(h1) : null,
    h1lines: h1 ? Math.round(h1.getBoundingClientRect().height / parseFloat(getComputedStyle(h1).lineHeight)) : null,
    h2max: max('main h2'), h3max: max('main h3'), body: fs(document.body),
    boardFill: (b => b ? getComputedStyle(b).fill : null)(document.querySelector('.hero-bd .bd-felt')),
    heroButtons: document.querySelectorAll('.hero-card .hero-links').length,
    lbTop: lb ? Math.round(lb.getBoundingClientRect().top + scrollY) : null,
    row1Bottom: row ? Math.round(row.getBoundingClientRect().bottom + scrollY) : null, screen: innerHeight}; }"""
SHORT = "Do models take the right risks, and do they learn from their games?"
rows, fail = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in (base_name, new_name):
        cand = name == new_name
        tag = "after" if cand else "before"
        for width in (375, 390, 1280):
            phone = width < 600
            for theme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": width, "height": 844 if phone else 900}, color_scheme=theme,
                                    has_touch=phone, is_mobile=phone)
                for page in PAGES:
                    pg = ctx.new_page()
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)))
                    pg.goto(root + name + "/" + page)
                    pg.wait_for_timeout(250)
                    m = pg.evaluate(MEASURE)
                    m["errors"] = errs
                    ok = m["over"] <= 0 and not errs and (m["theme"] == theme or page.startswith("archive/"))
                    if cand and not page.startswith("archive/"):  # the archive page has its own inline styles
                        ok &= m["h2max"] <= (m["h1"] or 99) and m["h3max"] <= max(m["h2max"], m["body"])
                        if page == "about/":
                            ok &= m["boardFill"] not in (None, "rgb(0, 0, 0)")
                        if page == "":
                            ok &= m["heroButtons"] == 0 and m["row1Bottom"] <= m["screen"] and (
                                m["h1lines"] <= (2 if width == 1280 else 3))
                    rows.append((tag, width, theme, page or "/", json.dumps(m), "yes" if ok else "NO"))
                    if cand and not ok:
                        fail.append(f"{width} {theme} {page or '/'}: {m}")
                    if page == "" and theme == "light" and width in (375, 1280):
                        pg.screenshot(path=str(out / "for-umit" / f"{tag}-front-{width}px-light.png"))
                        pg.screenshot(path=str(out / "screenshots" / f"{tag}-front-{width}px-light-full.png"), full_page=True)
                        if cand and width == 375:
                            pg.evaluate(f"() => document.querySelector('main h1').textContent = {json.dumps(SHORT)}")
                            pg.screenshot(path=str(out / "for-umit" / "option-short-title-front-375px-light.png"))
                    if cand and page == "" and theme == "dark" and width in (375, 1280):
                        pg.screenshot(path=str(out / "screenshots" / f"after-front-{width}px-dark.png"))
                    if cand and page == "about/" and theme == "light" and width in (375, 1280):
                        pg.goto(root + name + "/about/#front-page")
                        pg.wait_for_timeout(250)
                        pg.screenshot(path=str(out / "screenshots" / f"after-about-front-page-{width}px-light.png"))
                    pg.close()
                ctx.close()
    b.close()
with (out / "browser.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["render", "width", "theme", "page", "measured", "ok"])
    w.writerows(rows)
cand_rows = [r for r in rows if r[0] == "after"]
ok_n = sum(r[5] == "yes" for r in cand_rows)
fr = {(r[0], r[1], r[2]): json.loads(r[4]) for r in rows if r[3] == "/"}
summary = "".join(
    f"| {w} | {t} | {fr[('before', w, t)]['h1']} px, {fr[('before', w, t)]['h1lines']} lines | "
    f"{fr[('after', w, t)]['h1']} px, {fr[('after', w, t)]['h1lines']} lines | {fr[('before', w, t)]['h2max']} | "
    f"{fr[('after', w, t)]['h2max']} | {fr[('before', w, t)]['lbTop']} / {fr[('before', w, t)]['row1Bottom']} | "
    f"{fr[('after', w, t)]['lbTop']} / {fr[('after', w, t)]['row1Bottom']} | {fr[('after', w, t)]['screen']} |\n"
    for w in (375, 390, 1280) for t in ("light", "dark"))
(out / "browser.md").write_text(
    f"# Browser checks\n\nCandidate: **{ok_n}/{len(cand_rows)} page loads ok** ({len(PAGES)} pages x 3 widths x 2 themes): "
    "no sideways overflow, no script error, theme as asked (the frozen 23 Oct archive page has its own inline styles and no theme: overflow and errors only), largest h2 <= h1 and largest h3 <= max(h2, body); front "
    "page: no hero buttons, title <= 2 lines at 1280 (3 accepted at 375/390, Main), first leaderboard row inside the first "
    "screen. origin/main measured the same way for reference (no pass/fail).\n\n"
    "## Front page\n| px | theme | title before | title after | largest h2 before (px) | after | leaderboard top / "
    "row 1 bottom before (px) | after | screen height |\n|---|---|---|---|---|---|---|---|---|\n" + summary
    + "\n## Every load\n| render | px | theme | page | measured | ok |\n|---|---|---|---|---|---|\n"
    + "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | {r[5]} |\n" for r in rows)
    + (f"\n## Failures\n" + "".join(f"- {f}\n" for f in fail) if fail else ""))
print(f"browser: {ok_n}/{len(cand_rows)} candidate loads ok")
for f_ in fail[:30]:
    print(" FAIL", f_[:400])
sys.exit(1 if fail else 0)
