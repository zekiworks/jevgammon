"""Browser tests of the three Zeki #2918 fixes on a render (request routing, no server), light and dark; exits 1 on any
failure; screenshots of the changed cases into OUT/screenshots.
    test_fixes.py RENDER_DIR OUT_DIR
1. Mixed keyboard and mouse (1280 x 900): focus a model's name, Tab into its box; then the pointer leaves the row, then
   rests on another row: the focused box stays open and no other box opens; Escape closes it; a click outside closes a
   focused box too. Every ranked row.
2. Short windows (1280 x 500 desktop, 390 x 500 phone): every ranked row's box opens inside the window below the header
   (top >= header bottom, bottom <= window); when capped it scrolls inside; "Open its decisions →" is reachable: on the
   desktop by Tab (focused and inside the visible window), on the phone by scrolling the box, and tapping it opens
   Every decision filtered to the setup.
3. #view-part on the old addresses: the element exists, is visible, in the sticky header, and is the tab row."""
import csv
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import sync_playwright

root, out = Path(sys.argv[1]), Path(sys.argv[2])
shots = out / "screenshots"
shots.mkdir(parents=True, exist_ok=True)
SITE = "http://site.test/"


def serve(route):
    f = root / unquote(urlparse(route.request.url).path).lstrip("/")
    if f.is_dir():
        f = f / "index.html"
    if not f.is_file():
        return route.fulfill(status=404, body="not found")
    route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or "application/octet-stream")


def context(b, w, h, theme, touch):
    ctx = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    ctx.add_init_script(f"try {{ localStorage.setItem('theme','{theme}'); }} catch (e) {{}}")
    ctx.route("http://site.test/**", serve)
    return ctx


ROWS = "#headline-table tbody tr[data-box]:not(.hl-sub):not(.reference)"
OPEN = "() => [...document.querySelectorAll('.hl-box')].filter(b => getComputedStyle(b).display !== 'none').map(b => b.id)"
GEOM = """id => { const b = document.getElementById(id), r = b.getBoundingClientRect();
  const head = document.querySelector('.site-header').getBoundingClientRect().bottom;
  return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, head, vh: innerHeight, vw: document.documentElement.clientWidth,
           capped: b.scrollHeight > b.clientHeight + 1, maxh: b.style.maxHeight }; }"""
LINK_VISIBLE = """a => { const r = a.getBoundingClientRect(), b = a.closest('.hl-box').getBoundingClientRect();
  return r.top >= b.top - 0.5 && r.bottom <= b.bottom + 0.5 && r.top >= 0 && r.bottom <= innerHeight + 0.5; }"""
rows = []
with sync_playwright() as p:
    br = p.chromium.launch()
    for theme in ("light", "dark"):
        # 1. Mixed keyboard and mouse.
        ctx = context(br, 1280, 900, theme, False)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(SITE)
        pg.wait_for_timeout(400)
        n = pg.locator(ROWS).count()
        bad = []
        for i in range(n):
            row = pg.locator(ROWS).nth(i)
            bid = row.get_attribute("data-box")
            other = pg.locator(ROWS).nth((i + 2) % n)
            pg.mouse.move(2, 450)
            row.locator(".model-name").focus()
            for _ in range(3):
                pg.keyboard.press("Tab")
                if pg.evaluate("() => !!document.activeElement.closest('.hl-box')"):
                    break
            in_box = pg.evaluate("() => !!document.activeElement.closest('.hl-box')")
            pg.mouse.move(2, 450)  # the pointer leaves the row
            pg.wait_for_timeout(40)
            after_leave = pg.evaluate(OPEN)
            box = other.locator(".hl-box")
            nm = other.locator(".model-name")
            ob = other.bounding_box()
            if ob:
                pg.mouse.move(ob["x"] + ob["width"] - 30, ob["y"] + ob["height"] / 2)  # rests on another row
            pg.wait_for_timeout(40)
            after_other = pg.evaluate(OPEN)
            if i == 1 and theme == "light":
                pg.screenshot(path=str(shots / f"mixed-focus-then-pointer-on-another-row-1280-{theme}.png"))
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(40)
            after_esc = pg.evaluate(OPEN)
            ok = in_box and after_leave == [bid] and after_other == [bid] and after_esc == []
            if not ok:
                bad.append(f"row {i + 1}: focus in box {in_box}, open after leave {after_leave}, after another row {after_other}, after Escape {after_esc}")
        rows.append(["1280x900", theme, f"mixed keyboard + mouse, every ranked row ({n})",
                     "focus in the box; pointer leaves the row: still open; pointer on another row: still only that box; "
                     "Escape closes" + (f"; WRONG {bad}" if bad else ""), "ok" if not bad else "WRONG"])
        # Click outside closes a focused box; after that, hover works again.
        first = pg.locator(ROWS).first
        first.locator(".model-name").focus()
        pg.keyboard.press("Tab")
        pg.mouse.click(1250, 880)
        pg.wait_for_timeout(40)
        a = pg.evaluate(OPEN)
        third = pg.locator(ROWS).nth(2)
        third.locator(".model-name").hover()
        pg.wait_for_timeout(40)
        b = pg.evaluate(OPEN)
        ok = a == [] and b == [third.get_attribute("data-box")]
        rows.append(["1280x900", theme, "focused box, click outside, then hover another row",
                     f"open after the click {a}; after hover {b}", "ok" if ok else "WRONG"])
        rows.append(["1280x900", theme, "script errors", "; ".join(errs) or "none", "ok" if not errs else "ERRORS"])
        ctx.close()
        # 2. Short windows.
        for w, h, touch in ((1280, 500, False), (390, 500, True)):
            ctx = context(br, w, h, theme, touch)
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(SITE)
            pg.wait_for_timeout(400)
            n = pg.locator(ROWS).count()
            bad, capped = [], 0
            for i in range(n):
                row = pg.locator(ROWS).nth(i)
                bid = row.get_attribute("data-box")
                name = row.locator(".model-name")
                row.evaluate("r => r.scrollIntoView({block: 'center'})")  # not under the sticky header
                if touch:
                    name.tap()
                else:
                    pg.mouse.move(2, 5)
                    name.focus()
                pg.wait_for_timeout(50)
                g = pg.evaluate(GEOM, bid)
                capped += g["capped"]
                inside = g["top"] >= g["head"] - 0.5 and g["bottom"] <= g["vh"] + 0.5 and g["left"] >= 0 and g["right"] <= g["vw"] + 0.5
                link = pg.locator(f"#{bid} a", has_text="Open its decisions")
                if touch:
                    link.evaluate("a => a.closest('.hl-box').scrollTop = a.closest('.hl-box').scrollHeight")  # scroll the box
                    reach = link.evaluate(LINK_VISIBLE)
                else:
                    reach = False
                    for _ in range(4):
                        pg.keyboard.press("Tab")
                        pg.wait_for_timeout(20)
                        if link.evaluate("a => a === document.activeElement"):
                            reach = link.evaluate(LINK_VISIBLE)
                            break
                still = pg.evaluate(OPEN) == [bid]
                if not (inside and reach and still):
                    bad.append(f"row {i + 1}: inside {inside} ({round(g['top'])}–{round(g['bottom'])}, header {round(g['head'])}, window {g['vh']}), link reachable {reach}, open {still}")
                if i == 0:
                    pg.screenshot(path=str(shots / f"short-window-row1-{w}x{h}-{theme}.png"))
                if touch:
                    name.tap()
                else:
                    pg.keyboard.press("Escape")
                pg.wait_for_timeout(30)
            rows.append([f"{w}x{h}", theme, f"short window, every ranked row ({n})",
                         f"box inside the window below the header; {capped} boxes capped and scrolling; Open its decisions "
                         f"reachable ({'scrolling the box' if touch else 'Tab'})" + (f"; WRONG {bad}" if bad else ""),
                         "ok" if not bad else "WRONG"])
            # The decisions link actually opens Every decision with that setup (first row).
            row = pg.locator(ROWS).first
            name = row.locator(".model-name")
            row.evaluate("r => r.scrollIntoView({block: 'center'})")
            bid = row.get_attribute("data-box")
            link = pg.locator(f"#{bid} a", has_text="Open its decisions")
            href = link.get_attribute("href")
            if touch:
                name.tap()
                link.evaluate("a => a.closest('.hl-box').scrollTop = a.closest('.hl-box').scrollHeight")
                pg.wait_for_timeout(50)
                link.tap()
            else:
                name.focus()
                while not link.evaluate("a => a === document.activeElement"):
                    pg.keyboard.press("Tab")
                pg.keyboard.press("Enter")
            pg.wait_for_url(re.compile(r".*/decisions/.*"))
            pg.wait_for_timeout(800)
            q, want = parse_qs(urlparse(pg.url).query), parse_qs(urlparse(href).query)
            ok = q.get("d") == want.get("d") and q.get("s") == want.get("s") and pg.locator(".dec-card").count() > 0
            rows.append([f"{w}x{h}", theme, f"short window: Open its decisions → ({'tap' if touch else 'Enter'})",
                         f"{pg.url}: decision cards {pg.locator('.dec-card').count()}", "ok" if ok else "WRONG"])
            rows.append([f"{w}x{h}", theme, "script errors", "; ".join(errs) or "none", "ok" if not errs else "ERRORS"])
            ctx.close()
        # 3. #view-part.
        for w, touch in ((1280, False), (390, True)):
            ctx = context(br, w, 844, theme, touch)
            pg = ctx.new_page()
            for u in ("#view-part", "method/#view-part", "learning/#view-part", "decisions/#view-part"):
                pg.goto("about:blank")
                resp = pg.goto(SITE + u)
                pg.wait_for_timeout(300)
                st = pg.evaluate("""() => { const t = document.getElementById('view-part'), h = document.querySelector('.site-header');
                  if (!t) return 'missing'; const r = t.getBoundingClientRect();
                  return [t.matches('nav.site-tabs'), h.contains(t), r.top >= 0 && r.bottom <= h.getBoundingClientRect().bottom + 0.5 && r.width > 0,
                          document.querySelectorAll('#view-part').length].join(' '); }""")
                ok = resp.status == 200 and st == "true true true 1"
                rows.append([f"{w}", theme, f"old anchor {u}", f"status {resp.status}; tab row, in the header, in view, unique: {st}",
                             "ok" if ok else "WRONG"])
                if u == "#view-part" and theme == "light":
                    pg.screenshot(path=str(shots / f"view-part-{w}-{theme}.png"))
            ctx.close()
    br.close()
with (out / "fixes.csv").open("w", newline="") as fh:
    wr = csv.writer(fh)
    wr.writerow(["viewport", "theme", "check", "observed", "result"])
    wr.writerows(rows)
bad = [r for r in rows if r[-1] != "ok"]
for r in rows:
    print(r[-1], "|", r[0], r[1], "|", r[2], "|", r[3][:300])
print(f"test_fixes: {len(rows)} checks, {len(bad)} not ok")
sys.exit(1 if bad else 0)
