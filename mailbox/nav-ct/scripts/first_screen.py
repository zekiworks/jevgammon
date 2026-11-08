"""First screen at #leaderboard (390 x 844 as a phone, and 1280 x 900): the sticky header's height, where the table
starts, and how many ranked rows show all four parts (rank, model name, bar, score) fully inside the window below the
header. Exits 1 if no ranked row shows all four parts at either width, or the page is wider than the window.
    first_screen.py NAME=RENDER_DIR ..."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

JS = """() => {
  const head = document.querySelector('.site-header').getBoundingClientRect().bottom, vh = innerHeight, vw = document.documentElement.clientWidth;
  const inside = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.top >= head - 0.5 && r.bottom <= vh + 0.5 && r.left >= -0.5 && r.right <= vw + 0.5; };
  const rows = [...document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub):not(.reference)')];
  const full = rows.filter(r => inside(r.cells[0]) && inside(r.querySelector('.model-name')) && inside(r.querySelector('.hl-bar')) && inside(r.querySelector('.hl-val')));
  const t = document.getElementById('headline-table').getBoundingClientRect();
  return { header: Math.round(head), table_top: Math.round(t.top), rows_with_all_four_parts: full.length,
           page_wider_than_window: document.documentElement.scrollWidth - vw };
}"""
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for arg in sys.argv[1:]:
        name, root = arg.split("=", 1)
        for w, h, mobile in ((390, 844, True), (1280, 900, False)):
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
            pg = ctx.new_page()
            pg.goto((Path(root) / "index.html").resolve().as_uri() + "#leaderboard")
            pg.wait_for_timeout(500)
            r = pg.evaluate(JS)
            print(json.dumps({"render": name, "width": w, "height": h, **r}))
            bad += r["rows_with_all_four_parts"] == 0 or r["page_wider_than_window"] > 0
            ctx.close()
    b.close()
sys.exit(1 if bad else 0)
