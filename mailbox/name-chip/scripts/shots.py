"""Screenshots of HoverCheck's case on each render: the mouse moved straight down the name column from row 7 (Grok 4.7)
to row 10 (Kimi K3.1 Pro), 1280 px light, Chromium; the open box's first line printed. Reads only.

    python3 shots.py URL OUT_PNG"""
import sys

from playwright.sync_api import sync_playwright

url, png = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(url)
    pg.wait_for_timeout(400)
    rows = pg.locator("#headline-table tbody tr[data-box]:not([hidden])")
    rows.nth(6).evaluate("""tr => { const wrap = tr.closest('table').parentElement, head = tr.closest('table').querySelector('thead').offsetHeight;
      scrollTo(0, wrap.getBoundingClientRect().top + scrollY - 100);
      wrap.scrollTop += tr.getBoundingClientRect().top - wrap.getBoundingClientRect().top - head; }""")
    pg.wait_for_timeout(100)
    for i in range(6, 10):
        bb = rows.nth(i).locator(".model-name").bounding_box()
        pg.mouse.move(bb["x"] + 20, bb["y"] + bb["height"] / 2, steps=6)
        pg.wait_for_timeout(80)
    first = pg.evaluate("() => [...document.querySelectorAll('.hl-box.open')].map(b => b.querySelector('p').textContent)")
    print(f"mouse on {rows.nth(9).locator('.model-name').text_content()!r}; open box: {first}")
    pg.screenshot(path=png)
    b.close()
