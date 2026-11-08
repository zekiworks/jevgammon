"""Hover sweep (HoverCheck's finding on live, Main): the box of a row must always be the box of the row under the mouse.
Chromium and WebKit (Playwright), 1280 and 1440 px, light and dark, a rendered home page served over HTTP. Reads only.

    python3 sweep.py URL OUT_DIR LABEL

Sweeps (the mouse moved in 6 steps between row centres, the check made 60 ms after each arrival, i.e. within one row
move):
- down the name column (x on the names), rows 1 to the last (ranked rows, then the programs Random / GNUbg weak /
  Safest), the window and the table's own scroll box scrolled in segments (a fresh move after each scroll);
- up the name column, the same rows;
- down the score column (x on the scores);
- from the right: for each row, from 30 px right of the table leftwards onto its name;
- resting 3 s on rows 5, 15 and the last row, in the name column.
Each check: an open box exists, it is the box of the row whose centre the mouse is on, and only one box is open.
Plus, at each size: a mouse click on a row's empty space still opens its decisions (as on live); keyboard focus on row 1
keeps its box while the mouse rests on row 3 (Zeki #2918).
Writes OUT_DIR/sweep-LABEL.md, sweep-LABEL.csv; exits 1 on any failed check."""
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

url, out, label = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
out.mkdir(parents=True, exist_ok=True)
ROWS = "#headline-table tbody tr[data-box]:not([hidden])"
results, fail = [], []
STATE = """([x, y]) => {
  const open = [...document.querySelectorAll('.hl-box.open')].map(b => b.id);
  const under = document.elementFromPoint(x, y)?.closest('tr[data-box]');
  return {open, under: under ? under.dataset.box : null};
}"""


def run(engine, browser, width, theme):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=theme)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_timeout(500)
    rows = pg.locator(ROWS)
    n = rows.count()
    ids = [rows.nth(i).get_attribute("data-box") for i in range(n)]
    checks, bad = 0, []
    pos = {"x": 0, "y": 0}

    def move(x, y, steps=6):
        pg.mouse.move(x, y, steps=steps)
        pos.update(x=x, y=y)

    def verify(i, how, wait=60):
        nonlocal checks
        pg.wait_for_timeout(wait)
        s = pg.evaluate(STATE, [pos["x"], pos["y"]])
        checks += 1
        if s["open"] != [ids[i]] or s["under"] != ids[i]:
            bad.append({"how": how, "row": i + 1, "expected": ids[i], **s})

    def centre(i, part):
        tr = rows.nth(i)
        el = tr.locator(".model-name") if part == "name" else tr.locator(".hl-val").first if part == "score" else tr
        bb = el.bounding_box()
        return bb["x"] + min(bb["width"] / 2, 30) if part == "name" else bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2

    # The leaderboard scrolls inside its own box (fit to the window): a row counts as reachable when its centre is
    # inside that box (below its sticky head) and inside the window.
    WRAP = """tr => { let e = tr.parentElement;
      while (e && e !== document.body) { const s = getComputedStyle(e);
        if (/(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight) return e; e = e.parentElement; }
      return null; }"""

    def reachable(i):
        return rows.nth(i).evaluate(f"""tr => {{ const wrap = ({WRAP})(tr), r = tr.getBoundingClientRect(), c = (r.top + r.bottom) / 2;
          const w = wrap ? wrap.getBoundingClientRect() : {{top: 0, bottom: innerHeight}};
          const head = tr.closest('table').querySelector('thead').getBoundingClientRect().height;
          return c > Math.max(w.top + head + 10, 100) && c < Math.min(w.bottom - 10, innerHeight - 20); }}""")

    def bring(i):
        """Scroll the window to the table's box and the box so row i is its first row (the mouse moved off first)."""
        move(2, 2, steps=1)
        pg.wait_for_timeout(30)
        rows.nth(i).evaluate(f"""tr => {{ const wrap = ({WRAP})(tr);
          const head = tr.closest('table').querySelector('thead').getBoundingClientRect().height;
          if (wrap) {{ scrollTo(0, wrap.getBoundingClientRect().top + scrollY - 100);
                      wrap.scrollTop += tr.getBoundingClientRect().top - wrap.getBoundingClientRect().top - head; }}
          else scrollTo(0, tr.getBoundingClientRect().top + scrollY - 140); }}""")
        pg.wait_for_timeout(80)

    def sweep(order, part, how):
        for i in order:
            if not reachable(i):
                bring(i)
                x, y = centre(i, part)
                move(x, y, steps=1)
            else:
                x, y = centre(i, part)
                move(x, y)
            verify(i, how)

    sweep(range(n), "name", "down the name column")
    sweep(range(n - 1, -1, -1), "name", "up the name column")
    sweep(range(n), "score", "down the score column")
    for i in range(n):
        if not reachable(i):
            bring(i)
        tb = pg.locator("#headline-table").bounding_box()
        x, y = centre(i, "name")
        move(min(tb["x"] + tb["width"] + 30, width - 2), y, steps=1)
        pg.wait_for_timeout(30)
        move(x, y, steps=10)
        verify(i, "from the right onto the name")
    for i in (4, 14, n - 1):
        bring(i)
        x, y = centre(i, "name")
        move(x, y, steps=1)
        verify(i, "resting 3 s on the name", wait=3000)
    # A mouse click on a row's empty space opens its decisions, as before.
    bring(1)
    cell = rows.nth(1).locator("td.model").bounding_box()
    href = rows.nth(1).locator("a.model-name").get_attribute("href")
    nb = rows.nth(1).locator("a.model-name").bounding_box()
    move(cell["x"] + cell["width"] - 6, nb["y"] + nb["height"] / 2, steps=1)  # right of the name, clear of the expander
    pg.mouse.click(pos["x"], pos["y"])
    pg.wait_for_timeout(600)
    click = {"url": pg.url, "expected": href}
    click_ok = bool(href) and (url.rsplit("/", 1)[0] + "/" + href) in pg.url
    pg.go_back()
    pg.wait_for_timeout(500)
    # Focus beats pointer (Zeki #2918).
    bring(0)
    pg.evaluate("() => document.activeElement && document.activeElement.blur()")
    rows.nth(0).locator(".model-name").focus()
    pg.keyboard.press("Shift+Tab")
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(60)
    x, y = centre(2, "score")
    move(x, y)
    pg.wait_for_timeout(100)
    focus_open = pg.evaluate("() => [...document.querySelectorAll('.hl-box.open')].map(b => b.id)")
    focus_ok = focus_open == [ids[0]]
    ctx.close()
    for what, ok, m in ((f"every sweep check: box = row under the mouse ({checks} checks, {n} rows)", not bad, bad[:6]),
                        ("mouse click on a row's empty space opens its decisions (unchanged)", click_ok, click),
                        ("keyboard focus on row 1 keeps its box with the mouse on row 3", focus_ok, focus_open),
                        ("no script error", not errs, errs)):
        results.append((engine, width, theme, what, json.dumps(m)[:600], "yes" if ok else "NO"))
        if not ok:
            fail.append(f"{engine} {width} {theme}: {what}: {json.dumps(m)[:600]}")


with sync_playwright() as p:
    for engine in ("chromium", "webkit"):
        br = getattr(p, engine).launch()
        for width in (1280, 1440):
            for theme in ("light", "dark"):
                run(engine, br, width, theme)
        br.close()

with (out / f"sweep-{label}.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["engine", "width", "theme", "check", "measured", "ok"])
    w.writerows(results)
ok = sum(r[5] == "yes" for r in results)
(out / f"sweep-{label}.md").write_text(
    f"# Hover sweep: {label}\n\n`{url}`; Chromium and WebKit, 1280 and 1440 px (900 high), light and dark.\n\n**{ok} of {len(results)} ok.**\n\n"
    "| Engine | Width | Theme | Check | Measured (first failures) | OK |\n|---|---:|---|---|---|---|\n"
    + "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | {r[5]} |\n" for r in results))
print(f"sweep {label}: {ok}/{len(results)} ok")
for f_ in fail:
    print(" FAIL", f_)
sys.exit(1 if fail else 0)
