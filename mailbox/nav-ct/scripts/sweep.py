"""bg.css is shared by every page: at 390 px, every page (decision and fragment files excepted) of the BEFORE and AFTER
renders, page overflow (scrollWidth - clientWidth) and hbar rows whose parts stick out. Prints the pages whose result
differs between the renders and exits 1 if AFTER is worse anywhere.
(nav-ct: mobile-fix's sweep.py; a page that is new in AFTER (about/, experiments/, highlights/) is measured against
zero overflow.)
    sweep.py BEFORE_RENDER AFTER_RENDER"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
before, after = Path(sys.argv[1]), Path(sys.argv[2])
pages = sorted(p.relative_to(after) for p in after.rglob("*.html")
               if not {"decisions", "fragments"} & set(p.relative_to(after).parts) and not str(p.relative_to(after)).startswith("archive"))
JS = """() => { const vw = document.documentElement.clientWidth; let bad = 0;
  for (const li of document.querySelectorAll('.hbars > li.hbar')) { if (!li.getClientRects().length) continue;
    const lb = li.getBoundingClientRect();
    for (const k of li.children) { const b = k.getBoundingClientRect(); if (b.width && (b.right > Math.min(lb.right, vw) + .5 || k.scrollWidth > k.clientWidth + 1)) bad++; } }
  return [document.documentElement.scrollWidth - vw, bad]; }"""
worse = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    tot = {"before": [0, 0], "after": [0, 0]}
    for rel in pages:
        res = {}
        for name, root in (("before", before), ("after", after)):
            if not (root / rel).is_file():  # a new page: measured against no overflow
                res[name] = [0, 0]
                print(rel, "new in AFTER")
                continue
            pg.goto((root / rel).resolve().as_uri()); pg.wait_for_timeout(150)
            res[name] = pg.evaluate(JS)
            tot[name][0] += res[name][0] > 0; tot[name][1] += res[name][1] > 0
        if res["before"] != res["after"]:
            print(rel, "overflow px, bad hbar parts: before", res["before"], "after", res["after"])
        if res["after"][0] > res["before"][0] or res["after"][1] > res["before"][1]:
            worse += 1
    print(f"{len(pages)} pages; pages with page overflow: before {tot['before'][0]}, after {tot['after'][0]}; "
          f"pages with hbar parts sticking out: before {tot['before'][1]}, after {tot['after'][1]}; pages worse after: {worse}")
    b.close()
sys.exit(1 if worse else 0)
