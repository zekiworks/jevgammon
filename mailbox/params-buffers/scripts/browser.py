"""params-align browser checks (small-models' checks, unchanged, on the params-align render), Chromium (Playwright), the renders served over HTTP. Reads only.

    python3 browser.py HTTP_ROOT_URL BASE_NAME NEW_NAME OUT_DIR   (OUT_DIR/params.csv from compare.py first)

At 375, 390 and 1280 px, light and dark, on the candidate's home page:
- the filter: for All, Chat models, Decision models and Small models the rows in view (expanders closed, then every
  expander opened) are exactly the data's rows for that key (type from the box's first line; Small models from
  model_params.json via params.csv, the model's disclosed total at most 15B; programs in every view); no row lost
  (each key's rows = the data's rows; All = every row); the Small models note shown only under Small models; ranks
  unchanged (the # of each shown row = its rank under All);
- the Parameters line on every model row (main and other-settings rows; programs none): at 1280 by hover on the
  name, at 375/390 by a tap (a second tap closes it); the line as shown equals params.csv; the box inside the window;
- no sideways overflow at any width with every expander open, in every filter state, and with a box open;
- no script error.
Screenshots: Small models at 1280 light with a box open, 375 light two screens; origin/main's for comparison.
Writes OUT_DIR/browser.md, browser.csv, screenshots/; exits 1 on any failed check."""
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root, base_name, new_name, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], Path(sys.argv[4])
(out / "screenshots").mkdir(parents=True, exist_ok=True)
(out / "for-umit").mkdir(parents=True, exist_ok=True)
rows_out, fail = [], []
DATA = {r["box"]: r for r in csv.DictReader((out / "params.csv").open())}
TYPE = {"chat model": "chat", "decision model": "decision"}


def check(width, theme, what, ok, measured=""):
    rows_out.append((width, theme, what, measured if isinstance(measured, str) else json.dumps(measured, ensure_ascii=False),
                     "yes" if ok else "NO"))
    if not ok:
        fail.append(f"{width} {theme}: {what}: {measured}")


ROWS = """() => [...document.querySelectorAll('#headline-table tbody tr[data-box]')].map(tr => ({
  box: tr.dataset.box, shown: !!tr.offsetParent, sub: tr.classList.contains('hl-sub'),
  prog: tr.classList.contains('reference'), rank: tr.querySelector('td.num').textContent.trim(),
  first: tr.querySelector('.hl-box p').textContent.replace(/\\s+/g, ' ').trim()}))"""
OPEN_ALL = "() => document.querySelectorAll('#headline-table .hl-more[aria-expanded=\"false\"]').forEach(b => b.click())"
CLOSE_ALL = "() => document.querySelectorAll('#headline-table .hl-more[aria-expanded=\"true\"]').forEach(b => b.click())"
OVER = "() => document.documentElement.scrollWidth - innerWidth"
BOX = """tr => { const box = document.getElementById(tr.dataset.box); const r = box.getBoundingClientRect();
  const p = [...box.querySelectorAll('p')].map(p => p.textContent.replace(/\\s+/g, ' ').trim());
  const line = [...box.querySelectorAll('p')].find(p => p.textContent.trim().startsWith('Parameters:'));
  return {open: box.classList.contains('open') && getComputedStyle(box).display !== 'none',
          inview: r.left >= 0 && r.right <= innerWidth + 1, params: p.filter(t => t.startsWith('Parameters:')),
          href: line && line.querySelector('a') ? line.querySelector('a').getAttribute('href') : ''}; }"""


def kind_of(r):
    if r["prog"]:
        return "program"
    return next((TYPE[p] for p in r["first"].split(" \u00b7 ") if p in TYPE), "unknown")


def expected_rows(all_rows, key, expanded):
    """The data's rows for a key: type from the box's first line (a sub row: its main row's), small from params.csv
    (the main row's model; its other-settings rows go with it); programs always; sub rows only when expanded."""
    out_, main = [], None
    for r in all_rows:
        if not r["sub"]:
            main = r
        k, prog = kind_of(main), main["prog"]
        small = DATA[main["box"]]["data-hl-small"] == "yes"
        keep = prog or key == "all" or (key == "small" and small) or k == key
        if keep and (expanded or not r["sub"]):
            out_.append(r["box"])
    return out_


with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (375, 390, 1280):
        phone = width < 600
        for theme in ("light", "dark"):
            ctx = b.new_context(viewport={"width": width, "height": 844 if phone else 900}, color_scheme=theme,
                                has_touch=phone, is_mobile=phone)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            home = root + new_name + "/"
            pg.goto(home)
            pg.wait_for_timeout(400)
            pg.evaluate(OPEN_ALL)
            all_rows = pg.evaluate(ROWS)
            pg.evaluate(CLOSE_ALL)
            ranks = {r["box"]: r["rank"] for r in all_rows}
            res, filt_ok = {}, True
            for key in ("chat", "decision", "small", "all"):
                pg.locator(f'[data-hl-filter="{key}"]').click()
                pg.wait_for_timeout(80)
                note = pg.evaluate("() => { const n = document.querySelector('.hl-small-note'); return n && n.offsetParent ? n.textContent : null; }")
                got_c = [r["box"] for r in pg.evaluate(ROWS) if r["shown"]]
                over_c = pg.evaluate(OVER)
                pg.evaluate(OPEN_ALL)
                pg.wait_for_timeout(50)
                shown_o = [r for r in pg.evaluate(ROWS) if r["shown"]]
                got_o = [r["box"] for r in shown_o]
                over_o = pg.evaluate(OVER)
                pg.evaluate(CLOSE_ALL)
                want_c, want_o = expected_rows(all_rows, key, False), expected_rows(all_rows, key, True)
                rank_ok = all(r["rank"] == ranks[r["box"]] for r in shown_o)
                note_ok = (note == "Small models: 15B parameters or fewer (total), as disclosed by the maker; models with "
                           "undisclosed size are not included.") if key == "small" else note is None
                ok = got_c == want_c and got_o == want_o and rank_ok and note_ok and over_c <= 0 and over_o <= 0
                filt_ok &= ok
                res[key] = {"rowsClosed": len(got_c), "rowsOpen": len(got_o), "match": got_c == want_c and got_o == want_o,
                            "ranks": rank_ok, "note": note_ok, "overflow": [over_c, over_o],
                            "ranked": [r["rank"] for r in shown_o if not r["sub"] and not r["prog"]] if key == "small" else None}
                check(width, theme, f"filter {key}: rows in view = data's rows (expanders closed and open), ranks overall, "
                      "note, no overflow", ok, res[key])
            n_models = sum(1 for r in all_rows if not r["prog"])
            check(width, theme, "no row lost: All = every row; Chat ∪ Decision ∪ programs = every row",
                  res["all"]["rowsOpen"] == len(all_rows) and
                  len(set(expected_rows(all_rows, "chat", True)) | set(expected_rows(all_rows, "decision", True))) == len(all_rows),
                  {"rows": len(all_rows), "modelRows": n_models})
            # The Parameters line on every row, by hover (1280) or tap (375/390), every expander open.
            pg.locator('[data-hl-filter="all"]').click()
            pg.evaluate(OPEN_ALL)
            pg.wait_for_timeout(80)
            trs = pg.locator("#headline-table tbody tr[data-box]")
            bad, n_ok = [], 0
            for i in range(trs.count()):
                tr = trs.nth(i)
                box = tr.get_attribute("data-box")
                d = DATA[box]
                name = tr.locator(".model-name")
                name.scroll_into_view_if_needed()
                if phone:
                    (tr.locator(".hl-bar") if tr.locator(".hl-bar").count() else name).tap()
                else:
                    pg.mouse.move(0, 0)
                    pg.wait_for_timeout(30)
                    name.hover()
                pg.wait_for_timeout(60)
                if pg.url != home:
                    bad.append({"box": box, "navigatedTo": pg.url})
                    pg.go_back()
                    pg.wait_for_timeout(400)
                    pg.evaluate(OPEN_ALL)
                    continue
                s = tr.evaluate(BOX)
                want = [] if d["kind"] == "program" else [f'Parameters: {d["parameters shown"]}']
                good = s["open"] and s["inview"] and s["params"] == want and (s["href"] or "") == d["link"]
                if good and phone:
                    over = pg.evaluate(OVER)
                    (tr.locator(".hl-bar") if tr.locator(".hl-bar").count() else name).tap()
                    pg.wait_for_timeout(60)
                    good = over <= 0 and not tr.evaluate(BOX)["open"]
                if good:
                    n_ok += 1
                else:
                    bad.append({"box": box, **s, "want": want})
                if not phone and theme == "light" and box == "hl-1-box":
                    pg.screenshot(path=str(out / "screenshots" / f"home-{width}-{theme}-row1-hover.png"))
                if phone and width == 375 and box == "hl-1-box":
                    tr.locator(".hl-bar").tap()
                    pg.wait_for_timeout(100)
                    pg.screenshot(path=str(out / "screenshots" / f"home-{width}-{theme}-row1-tap.png"))
                    tr.locator(".hl-bar").tap()
            pg.mouse.move(0, 0)
            how = "tap, second tap closes" if phone else "hover on the name"
            check(width, theme, f"Parameters line in the box on every row = data ({how}); box inside the window",
                  n_ok == trs.count(), {"rows": trs.count(), "ok": n_ok, "bad": bad[:5]})
            pg.evaluate(CLOSE_ALL)
            check(width, theme, "no script error", not errs, errs)
            # Screenshots: Small models.
            pg.locator('[data-hl-filter="small"]').click()
            pg.wait_for_timeout(100)
            pg.evaluate("() => document.getElementById('leaderboard').scrollIntoView()")
            if not phone and theme == "light":
                first = pg.locator("#headline-table tbody tr[data-hl-small]:not(.hl-sub)").first
                first.locator(".model-name").hover()
                pg.wait_for_timeout(150)
                pg.screenshot(path=str(out / "for-umit" / "small-models-1280px-light-box.png"))
                pg.mouse.move(0, 0)
                pg.wait_for_timeout(100)
            if theme == "light" or width == 375:
                pg.set_viewport_size({"width": width, "height": 2 * (844 if phone else 900)})
                pg.wait_for_timeout(300)
                pg.evaluate("() => document.getElementById('leaderboard').scrollIntoView()")
                pg.wait_for_timeout(100)
                tag = "for-umit" if theme == "light" and width in (375, 1280) else "screenshots"
                pg.screenshot(path=str(out / tag / f"small-models-{width}px-{theme}.png"))
                if theme == "light" and width in (375, 1280):
                    pg.locator('[data-hl-filter="all"]').click()
                    pg.wait_for_timeout(100)
                    pg.evaluate("() => document.getElementById('leaderboard').scrollIntoView()")
                    pg.screenshot(path=str(out / "for-umit" / f"all-{width}px-{theme}.png"))
                    pg.goto(root + base_name + "/")
                    pg.wait_for_timeout(400)
                    pg.evaluate("() => document.getElementById('leaderboard').scrollIntoView()")
                    pg.screenshot(path=str(out / "for-umit" / f"before-main-{width}px-{theme}.png"))
            ctx.close()
    b.close()

with (out / "browser.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["width", "theme", "check", "measured", "ok"])
    w.writerows(rows_out)
ok = sum(r[4] == "yes" for r in rows_out)
(out / "browser.md").write_text(
    "# Browser checks\n\n375, 390 and 1280 px, light and dark, Chromium (Playwright), served over HTTP; the candidate's "
    f"home page.\n\n**{ok} of {len(rows_out)} ok.**\n\n| Width | Theme | Check | Measured | OK |\n|---:|---|---|---|---|\n"
    + "".join(f"| {r[0]} | {r[1]} | {r[2]} | `{r[3][:500]}` | {r[4]} |\n" for r in rows_out))
print(f"browser: {ok}/{len(rows_out)} ok")
for f_ in fail:
    print(" FAIL", f_[:600])
sys.exit(1 if fail else 0)
