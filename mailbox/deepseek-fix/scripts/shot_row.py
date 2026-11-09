"""Screenshot of one leaderboard row's open box (hover at 1280, tap at 375), light; prints the box's Parameters line
and the page's sideways overflow. Reads only.

    python3 shot_row.py URL BOX_ID OUT_PREFIX"""
import sys

from playwright.sync_api import sync_playwright

url, box, prefix = sys.argv[1:4]
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1280, 375):
        phone = w < 600
        pg = b.new_context(viewport={"width": w, "height": 844 if phone else 900}, has_touch=phone, is_mobile=phone).new_page()
        pg.goto(url)
        pg.wait_for_timeout(400)
        tr = pg.locator(f'tr[data-box="{box}"]')
        tr.scroll_into_view_if_needed()
        pg.evaluate("tr => scrollBy(0, tr.getBoundingClientRect().top - 120)", tr.element_handle())
        (tr.locator(".hl-bar").tap() if phone else tr.locator(".model-name").hover())
        pg.wait_for_timeout(200)
        line = pg.evaluate(f"""() => [...document.getElementById('{box}').querySelectorAll('p')].map(p => p.textContent.trim())
            .find(t => t.startsWith('Parameters:'))""")
        print(w, repr(line), "overflow", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth"))
        pg.screenshot(path=f"{prefix}-{w}px-light.png")
    b.close()
