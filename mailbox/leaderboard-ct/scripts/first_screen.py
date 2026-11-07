"""How much of the leaderboard the first screen shows, opened at #leaderboard from file:// (Zeki #2790 item 6): the
table's top, the ranked rows fully in view, and the rows whose risk-judgement number (the score text itself) is fully
inside the window and the table's scroll box. Exits 1 unless the last render named shows at least 3 scores at 390 px.
    first_screen.py NAME=RENDER_DIR [NAME=RENDER_DIR ...]"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright
JS = """() => {
  const H = innerHeight, W = innerWidth;
  const rows = [...document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub)')];
  const inView = r => { const b = r.getBoundingClientRect(); return b.top >= 0 && b.bottom <= H; };
  const wrapR = document.querySelector('#headline-table').closest('.table-wrap').getBoundingClientRect().right;
  const valIn = r => { const v = r.querySelector('.hl-val'); if (!v) return false; const g = document.createRange(); g.selectNodeContents(v.firstChild);
    const b = g.getBoundingClientRect(); return b.top >= 0 && b.bottom <= H && b.left >= 0 && b.right <= Math.min(W, wrapR); };
  const anyVal = r => { const v = r.querySelector('.hl-val'); if (!v) return false; const b = v.getBoundingClientRect(); return b.top >= 0 && b.bottom <= H && b.left < W && b.right > 0; };
  const t = document.querySelector('#headline-table').getBoundingClientRect();
  return { table_top: Math.round(t.top), rows_fully_in_view: rows.filter(inView).length,
           score_number_fully_visible: rows.filter(valIn).length, judgement_cell_partly_visible: rows.filter(anyVal).length };
}"""
last = None
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, root in [(a.split('=')[0], Path(a.split('=')[1])) for a in sys.argv[1:]]:
        for w, h in ((390, 844), (1280, 900)):
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            pg.goto((root / "index.html").resolve().as_uri() + "#leaderboard"); pg.wait_for_timeout(500)
            r = pg.evaluate(JS)
            print(json.dumps({"render": name, "width": w, "height": h, **r}))
            if w == 390:
                last = r
            ctx.close()
sys.exit(0 if last and last["score_number_fully_visible"] >= 3 else 1)
