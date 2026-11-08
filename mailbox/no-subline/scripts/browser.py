"""no-subline browser checks (Ümit #3039), Chromium (Playwright), the renders served over HTTP. Reads only.

    python3 browser.py HTTP_ROOT_URL BASE_NAME NEW_NAME OUT_DIR

At 375, 390 and 1280 px, light and dark, on the candidate's home page:
- row layout: no sub-line under any name; a late tag on the name's line, small; no sideways overflow; no script error;
- every ranked row's box opens with its first line '<name> · <maker> · <type> · <setting>' (the line checked against
  the row's data-hl-type and the parts on record): at 1280 by hover on the name, the bar, the score and the row's empty
  space; at 375/390 by a tap (touch) on the row, and a second tap closes it;
- keyboard focus beats the pointer (Zeki #2918): a focused row's box stays while the mouse rests on another row (1280);
- the All / Chat / Decision filter: only rows of that type (and programs) shown, boxes open on the filtered rows;
- 375 px: hero + first 3 rows within two screen heights, origin/main against the candidate.
Writes OUT_DIR/browser.md, browser.csv, screenshots/; exits 1 on any failed check."""
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root, base_name, new_name, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], Path(sys.argv[4])
(out / "screenshots").mkdir(parents=True, exist_ok=True)
rows_out, fail = [], []
TYPE = {"chat": "chat model", "decision": "decision model"}


def check(width, theme, what, ok, measured=""):
    rows_out.append((width, theme, what, measured if isinstance(measured, str) else json.dumps(measured), "yes" if ok else "NO"))
    if not ok:
        fail.append(f"{width} {theme}: {what}: {measured}")


RANKED = "#headline-table tbody tr[data-box]:not(.hl-sub):not(.reference)"
LAYOUT = """() => {
  const rows = [...document.querySelectorAll('%s')];
  return {rows: rows.length, overflow: document.documentElement.scrollWidth - innerWidth,
    sublines: document.querySelectorAll('#headline-table td.model .hl-type, #headline-table tr:not(.hl-sub) td.model > span.small').length,
    tags: rows.filter(tr => tr.querySelector('.hl-tag')).map(tr => {
      const n = tr.querySelector('.model-name').getBoundingClientRect(), t = tr.querySelector('.hl-tag').getBoundingClientRect();
      return {name: tr.querySelector('.model-name').textContent, tag: tr.querySelector('.hl-tag').textContent,
              sameLine: Math.abs(t.bottom - n.bottom) < 4 || t.top < n.bottom, size: getComputedStyle(tr.querySelector('.hl-tag')).fontSize};
    }),
    maxRowHeight: Math.max(...rows.map(tr => tr.getBoundingClientRect().height))};
}""" % RANKED
STATE = """tr => { const box = document.getElementById(tr.dataset.box); const r = box.getBoundingClientRect();
  return {open: box.classList.contains('open') && getComputedStyle(box).display !== 'none',
          inview: r.top >= 0 && r.bottom <= innerHeight + 1 && r.left >= 0 && r.right <= innerWidth + 1,
          first: box.querySelector('p').textContent.replace(/\\s+/g, ' ').trim(), type: tr.dataset.hlType,
          setting: tr.dataset.setting || null}; }"""


def first_ok(s, name):
    """The first line starts with the row's setup name, has its type, and its setting when one is on record."""
    parts = s["first"].split(" \u00b7 ")
    t = TYPE.get(s["type"])
    return parts[0] == name and (t is None or t in parts) and (s["setting"] in (None, "none") or s["setting"] in parts) \
        and "Maker not recorded" not in parts and "Setting" not in s["first"]


with sync_playwright() as p:
    b = p.chromium.launch()
    two = {}
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
            m = pg.evaluate(LAYOUT)
            check(width, theme, "no sub-line under any name", m["sublines"] == 0, {"sublines": m["sublines"], "rankedRows": m["rows"]})
            check(width, theme, "late tags small on the name's line", all(t["sameLine"] for t in m["tags"]) and m["tags"] != [],
                  {"tags": m["tags"]})
            check(width, theme, "no sideways overflow", m["overflow"] <= 0, {"overflow": m["overflow"]})
            rows = pg.locator(RANKED)
            n = rows.count()
            names = [rows.nth(i).locator(".hl-box p strong").first.text_content() for i in range(n)]
            ok_rows, bad = 0, []
            for i in range(n):
                tr = rows.nth(i)
                tr.scroll_into_view_if_needed()
                if phone:
                    targets = [("name", tr.locator(".model-name")), ("bar", tr.locator(".hl-bar")), ("score", tr.locator(".hl-val"))]
                else:
                    targets = [("name", tr.locator(".model-name")), ("bar", tr.locator(".hl-bar")), ("score", tr.locator(".hl-val")),
                               ("empty", tr.locator("td.model"))]
                row_ok = True
                for part, loc in targets:
                    if part == "empty":
                        bb = loc.bounding_box()
                        pg.mouse.move(bb["x"] + bb["width"] - 4, bb["y"] + bb["height"] / 2)
                    elif phone:
                        loc.tap()
                    else:
                        pg.mouse.move(0, 0)
                        pg.wait_for_timeout(30)
                        loc.hover()
                    pg.wait_for_timeout(60)
                    if pg.url != home:
                        bad.append({"row": i + 1, "part": part, "navigatedTo": pg.url})
                        row_ok = False
                        pg.go_back()
                        pg.wait_for_timeout(400)
                        continue
                    s = tr.evaluate(STATE)
                    good = s["open"] and s["inview"] and first_ok(s, names[i])
                    if phone and good:
                        loc.tap()
                        pg.wait_for_timeout(60)
                        good = not tr.evaluate(STATE)["open"]
                    if not good:
                        row_ok = False
                        bad.append({"row": i + 1, "part": part, **s})
                    if part == "name" and not phone and i in (0, n - 1) and theme == "light":
                        pg.screenshot(path=str(out / "screenshots" / f"home-{width}-{theme}-row{i + 1}-hover.png"))
                    if phone and i == 0 and width == 375 and part == "bar":
                        loc.tap()
                        pg.wait_for_timeout(100)
                        pg.screenshot(path=str(out / "screenshots" / f"home-{width}-{theme}-row1-tap.png"))
                        loc.tap()
                ok_rows += row_ok
            pg.mouse.move(0, 0)
            how = "tap on name, bar and score; second tap closes; no navigation" if phone else "hover on name, bar, score and empty space"
            check(width, theme, f"box opens, first line name · maker · type · setting, every ranked row ({how})",
                  ok_rows == n, {"rows": n, "ok": ok_rows, "bad": bad[:5]})
            if not phone:
                # Zeki #2918: keyboard focus beats the pointer.
                pg.mouse.move(0, 0)
                pg.wait_for_timeout(50)
                pg.evaluate("() => document.body.focus()")
                rows.nth(0).locator(".model-name").focus()
                pg.keyboard.press("Shift+Tab")
                pg.keyboard.press("Tab")
                pg.wait_for_timeout(60)
                focused = rows.nth(0).evaluate(STATE)["open"]
                rows.nth(2).locator(".hl-bar").hover()
                pg.wait_for_timeout(80)
                held = rows.nth(0).evaluate(STATE)["open"] and not rows.nth(2).evaluate(STATE)["open"]
                check(width, theme, "keyboard focus beats the pointer (row 1 focused, mouse on row 3)", focused and held,
                      {"focusedOpens": focused, "heldWhileMouseOnRow3": held})
                pg.keyboard.press("Escape")
                pg.mouse.move(0, 0)
            # Filter.
            res = {}
            for key in ("chat", "decision", "all"):
                pg.locator(f'[data-hl-filter="{key}"]').click()
                pg.wait_for_timeout(80)
                vis = pg.evaluate("""() => [...document.querySelectorAll('#headline-table tbody tr[data-hl-type]')]
                    .filter(tr => tr.offsetParent).map(tr => tr.dataset.hlType)""")
                shown = pg.locator(RANKED + ":visible")
                box_ok = True
                if key != "all" and shown.count():
                    tr = shown.nth(min(1, shown.count() - 1))
                    tr.scroll_into_view_if_needed()
                    if phone:
                        tr.locator(".hl-bar").tap()
                    else:
                        tr.locator(".hl-bar").hover()
                    pg.wait_for_timeout(60)
                    s = tr.evaluate(STATE)
                    box_ok = s["open"] and TYPE[key] in s["first"].split(" \u00b7 ")
                    if phone:
                        tr.locator(".hl-bar").tap()
                    pg.mouse.move(0, 0)
                res[key] = {"shown": len(vis), "types": sorted(set(vis)), "boxOk": box_ok}
            filt_ok = (set(res["chat"]["types"]) <= {"chat", "program"} and set(res["decision"]["types"]) <= {"decision", "program"}
                       and res["chat"]["boxOk"] and res["decision"]["boxOk"] and res["all"]["shown"] > max(res["chat"]["shown"], res["decision"]["shown"]))
            check(width, theme, "filter All / Chat / Decision", filt_ok, res)
            check(width, theme, "no script error", not errs, errs)
            # Two screens at 375; screenshots.
            pg.evaluate("() => scrollTo(0, 0)")
            for name in (base_name, new_name):
                pg.goto(root + name + "/")
                pg.wait_for_timeout(400)
                two[(width, theme, name)] = pg.evaluate("""() => {
                    const rows = [...document.querySelectorAll('%s')];
                    const r = i => rows[i].getBoundingClientRect().bottom + scrollY;
                    return {screen: innerHeight, heroBottom: document.querySelector('.hero-card').getBoundingClientRect().bottom + scrollY,
                            row1Bottom: r(0), row3Bottom: r(2), rowsInTwoScreens: rows.filter(tr => tr.getBoundingClientRect().bottom + scrollY <= 2 * innerHeight).length};
                }""" % RANKED)
            if phone:
                o, c = two[(width, theme, base_name)], two[(width, theme, new_name)]
                check(width, theme, "hero + first 3 rows within two screens (origin/main → candidate)",
                      c["row3Bottom"] <= 2 * c["screen"] and c["row3Bottom"] <= o["row3Bottom"], {"main": o, "candidate": c})
            if theme == "light" and width in (375, 1280) or width == 375:
                pg.set_viewport_size({"width": width, "height": 2 * (844 if phone else 900)})
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(out / "screenshots" / f"home-{width}-{theme}{'-two-screens' if phone else ''}.png"))
                if theme == "light":
                    pg.goto(root + base_name + "/")
                    pg.wait_for_timeout(400)
                    pg.screenshot(path=str(out / "screenshots" / f"before-main-home-{width}-{theme}{'-two-screens' if phone else ''}.png"))
            ctx.close()
    b.close()

with (out / "browser.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["width", "theme", "check", "measured", "ok"])
    w.writerows(rows_out)
ok = sum(r[4] == "yes" for r in rows_out)
(out / "browser.md").write_text(
    "# Browser checks\n\n375, 390 and 1280 px, light and dark, Chromium (Playwright), served over HTTP; the candidate's home page "
    f"(the 375 px two-screen line also measures origin/main's render of the same state).\n\n**{ok} of {len(rows_out)} ok.**\n\n"
    "| Width | Theme | Check | Measured | OK |\n|---:|---|---|---|---|\n"
    + "".join(f"| {r[0]} | {r[1]} | {r[2]} | `{r[3][:400]}` | {r[4]} |\n" for r in rows_out))
print(f"browser: {ok}/{len(rows_out)} ok")
for f_ in fail:
    print(" FAIL", f_[:600])
sys.exit(1 if fail else 0)
