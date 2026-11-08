"""Mouse into the box and click its links (Zeki #3146): for rows 1, 10, the last ranked row and the last row (a
program), the mouse goes onto the row's name, along the row into its box, down to each link of the box ('Open its
decisions' / 'Its late-entry page', 'Model page', 'Released'), and clicks it; the page must land on the link's own URL
(external pages answered locally, never fetched). Chromium and WebKit, 1280 and 1440 px, light. Reads only.

    python3 links.py URL OUT_DIR

Writes OUT_DIR/links.md, links.csv; exits 1 on any failure."""
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
ROWS = "#headline-table tbody tr[data-box]:not([hidden])"
RANKED = ROWS + ":not(.reference)"
results, fail = [], []


def bring(pg, tr):
    pg.mouse.move(2, 2)
    pg.wait_for_timeout(200)
    tr.evaluate("""tr => { const wrap = tr.closest('.table-wrap'), head = tr.closest('table').querySelector('thead').offsetHeight;
      scrollTo(0, wrap.getBoundingClientRect().top + scrollY - 100);
      wrap.scrollTop += tr.getBoundingClientRect().top - wrap.getBoundingClientRect().top - head - 80; }""")
    pg.wait_for_timeout(100)


with sync_playwright() as p:
    for engine in ("chromium", "webkit"):
        br = getattr(p, engine).launch()
        for width in (1280, 1440):
            ctx = br.new_context(viewport={"width": width, "height": 900})
            ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1")
                      else route.fulfill(status=200, content_type="text/html", body="<p>external</p>"))
            pg = ctx.new_page()
            pg.goto(url)
            pg.wait_for_timeout(400)
            n_ranked, n_all = pg.locator(RANKED).count(), pg.locator(ROWS).count()
            targets = [("row 1", RANKED, 0), ("row 10", RANKED, 9), (f"last ranked row ({n_ranked})", RANKED, n_ranked - 1),
                       (f"last row ({n_all}, program)", ROWS, n_all - 1)]
            for label, sel, i in targets:
                tr = pg.locator(sel).nth(i)
                box_id = tr.get_attribute("data-box")
                links = pg.evaluate("""id => [...document.querySelectorAll('#' + id + ' a')].map((a, k) => ({k, text: a.textContent.trim(),
                    line: a.closest('p').textContent.trim().split(' ')[0], href: a.href}))""", box_id)
                for link in links:
                    what = "Released" if link["line"] == "Released" else link["text"].rstrip(" →")
                    bring(pg, tr)
                    nb = tr.locator(".model-name").bounding_box()
                    pg.mouse.move(nb["x"] + 10, nb["y"] + nb["height"] / 2, steps=4)
                    pg.wait_for_timeout(80)
                    bb = pg.locator(f"#{box_id}").bounding_box()
                    row = tr.bounding_box()
                    y = min(max(row["y"] + row["height"] / 2, bb["y"] + 10), bb["y"] + bb["height"] - 10)
                    pg.mouse.move(nb["x"] + 10, y, steps=3)  # within the row, level with the box
                    pg.mouse.move(bb["x"] + 24, y, steps=12)  # along the row into the box
                    a = pg.locator(f"#{box_id} a").nth(link["k"])
                    lb = a.bounding_box()
                    pg.mouse.move(lb["x"] + min(lb["width"] / 2, 20), lb["y"] + lb["height"] / 2, steps=12)  # down to the link
                    pg.wait_for_timeout(300)
                    state = pg.evaluate("""([id, x, y]) => ({open: [...document.querySelectorAll('.hl-box.open')].map(b => b.id),
                        atLink: document.elementFromPoint(x, y)?.closest('a')?.href || null})""",
                                        [box_id, lb["x"] + min(lb["width"] / 2, 20), lb["y"] + lb["height"] / 2])
                    pg.mouse.click(lb["x"] + min(lb["width"] / 2, 20), lb["y"] + lb["height"] / 2)
                    try:
                        pg.wait_for_url(lambda u: u != url, timeout=5000)
                    except Exception:
                        pass
                    landed = pg.url
                    ok = state["open"] == [box_id] and state["atLink"] == link["href"] and landed == link["href"]
                    m = {"box": box_id, "openWhileOnLink": state["open"], "linkUnderMouse": state["atLink"], "href": link["href"], "landed": landed}
                    results.append((engine, width, label, what, json.dumps(m), "yes" if ok else "NO"))
                    if not ok:
                        fail.append(f"{engine} {width} {label} {what}: {m}")
                    pg.goto(url)
                    pg.wait_for_timeout(400)
            ctx.close()
        br.close()

with (out / "links.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["engine", "width", "row", "link", "measured", "ok"])
    w.writerows(results)
ok = sum(r[5] == "yes" for r in results)
(out / "links.md").write_text(
    f"# Mouse into the box, click its links\n\n`{url}`; Chromium and WebKit, 1280 and 1440 px (900 high), light. The mouse goes "
    "onto the row's name, along the row into its box, down to the link, clicks; external pages answered locally.\n\n"
    f"**{ok} of {len(results)} ok.**\n\n| Engine | Width | Row | Link | Measured | OK |\n|---|---:|---|---|---|---|\n"
    + "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | {r[5]} |\n" for r in results))
print(f"links: {ok}/{len(results)} ok")
for f_ in fail:
    print(" FAIL", f_)
sys.exit(1 if fail else 0)
