"""fix-filters browser test (Main, after bus #2790): the home page's filter row, opened from file:// at 1280 and 390 px,
light and dark, on a render of origin/main (BEFORE) and of fix-filters (AFTER).
    test_filters.py BEFORE_RENDER AFTER_RENDER OUT_DIR
Per state: #filters-body's computed display; League, Models, Measure (part links), More filters, Phase and Reset
visible and clickable (Playwright clicks, which fail on an element that cannot be seen); clicking a League key and a
Models key changes their pressed state; More filters opens its fold; the phase select can be used (file:// refuses
bg.js's fetch of fragments/, so there it alerts and resets; recorded), and over routed http (no server) choosing Race
sets the select and replaces the page's phase slots; Reset returns to the defaults. The collapsible .filters panel rule is checked on an injected panel (no page of this site uses one): it
must stay hidden without .is-open and show with it. 4 screenshots of the filter row (AFTER). Exits 1 on any failure in
AFTER (BEFORE is expected to fail: the row was hidden)."""
import csv
import mimetypes
import sys
from urllib.parse import unquote, urlparse
from pathlib import Path

from playwright.sync_api import sync_playwright

before, after, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
(out / "screenshots").mkdir(parents=True, exist_ok=True)
rows = []
SLOTS = "() => [...document.querySelectorAll('.phase-slot[data-slot]')].map(s => s.textContent.replace(/\\s+/g, ' ').trim())"


def router(root):
    def serve(route):
        path = unquote(urlparse(route.request.url).path).lstrip("/")
        f = root / path
        if f.is_dir():
            f = f / "index.html"
        if not f.is_file():
            return route.fulfill(status=404, body="not found")
        route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or "application/octet-stream")
    return serve


CONTROLS = [("League key 'League 2'", '#filters [data-league-pick="league-2"]'),
            ("Models key 'Chat'", '#filters [data-filter-kind="chat"]'),
            ("Measure link 'Error rate'", '#filters .part-links a[href="#error-rate"]'),
            ("More filters", "#filters [data-more-filters]"),
            ("Reset", '#filters [data-control="reset"]')]
fails_after = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, root in (("before (origin/main)", before), ("after (fix-filters)", after)):
        for width in (1280, 390):
            for theme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": width, "height": 900 if width > 500 else 844})
                ctx.add_init_script(f"localStorage.setItem('theme','{theme}')")
                page = ctx.new_page()
                errs, dialogs = [], []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
                page.goto((root / "index.html").resolve().as_uri() + "#filters")
                page.wait_for_timeout(500)
                if name.startswith("after"):  # as the page loads, before any interaction
                    page.screenshot(path=str(out / "screenshots" / f"filter-row-{width}-{theme}.png"))
                res = []
                disp = page.eval_on_selector("#filters-body", "e => getComputedStyle(e).display")
                res.append(("#filters-body display", disp, disp != "none"))
                for label, sel in CONTROLS:
                    loc = page.locator(sel).first
                    vis = loc.count() > 0 and loc.is_visible()
                    res.append((f"{label} visible", vis, vis))
                # Clicks (real Playwright clicks; they need a visible, enabled element).
                def click(sel):
                    try:
                        page.locator(sel).first.click(timeout=2000)
                        return True
                    except Exception as e:  # noqa: BLE001 - recorded, not hidden
                        return f"not clickable: {str(e).splitlines()[0][:80]}"
                c = click('#filters [data-league-pick="league-2"]')
                pressed = page.get_attribute('#filters [data-league-pick="league-2"]', "aria-pressed")
                res.append(("League 2 clicked → pressed", f"{c}; aria-pressed={pressed}", c is True and pressed == "true"))
                c = click('#filters [data-filter-kind="chat"]')
                pressed = page.get_attribute('#filters [data-filter-kind="chat"]', "aria-pressed")
                res.append(("Models 'Chat' clicked → pressed", f"{c}; aria-pressed={pressed}", c is True and pressed == "true"))
                c = click("#filters [data-more-filters]")
                exp = page.get_attribute("#filters [data-more-filters]", "aria-expanded")
                fold = page.locator("#filters-more").is_visible()
                res.append(("More filters clicked → fold open", f"{c}; aria-expanded={exp}; fold visible={fold}",
                            c is True and exp == "true" and fold))
                vis = page.locator('#filters [data-control="phase"]').is_visible()
                res.append(("Phase select visible (in the More filters fold, once open)", vis, vis))
                try:
                    page.select_option('#filters [data-control="phase"]', "race", timeout=2000)
                    page.wait_for_timeout(600)
                    v = page.eval_on_selector('#filters [data-control="phase"]', "s => s.value")
                    # file:// refuses bg.js's fetch of fragments/: it alerts and puts the select back. The select itself
                    # was usable; its effect is checked over routed http below.
                    res.append(("Phase select usable (real select, file://)", f"value after: {v}; dialogs: {dialogs or 'none'}",
                                True))
                except Exception as e:  # noqa: BLE001
                    res.append(("Phase select usable (real select, file://)", f"not usable: {str(e).splitlines()[0][:80]}", False))
                c = click('#filters [data-control="reset"]')
                page.wait_for_timeout(300)
                st = page.evaluate("""() => ({ league: [...document.querySelectorAll('#filters [data-league-pick]')].find(b => b.getAttribute('aria-pressed') === 'true')?.dataset.leaguePick,
                  kind: [...document.querySelectorAll('#filters [data-filter-kind]')].find(b => b.getAttribute('aria-pressed') === 'true')?.dataset.filterKind,
                  phase: document.querySelector('#filters [data-control="phase"]').value })""")
                res.append(("Reset clicked → defaults", f"{c}; {st}", c is True and st["kind"] == "all" and st["phase"] == "all"))
                # The phase's effect, over routed http (no server): the real select, then the page's phase state.
                rctx = b.new_context(viewport={"width": width, "height": 900 if width > 500 else 844})
                rctx.add_init_script(f"localStorage.setItem('theme','{theme}')")
                rctx.route("http://site.test/**", router(root))
                rp = rctx.new_page()
                rerr, rdlg = [], []
                rp.on("pageerror", lambda e: rerr.append(str(e)))
                rp.on("dialog", lambda d: (rdlg.append(d.message), d.dismiss()))
                rp.goto("http://site.test/#filters")
                rp.wait_for_timeout(500)
                before_slots = rp.evaluate(SLOTS)
                try:
                    if rp.get_attribute("#filters [data-more-filters]", "aria-expanded") != "true":
                        rp.click("#filters [data-more-filters]", timeout=2000)
                    rp.select_option('#filters [data-control="phase"]', "race", timeout=2000)
                    rp.wait_for_timeout(900)
                    v = rp.eval_on_selector('#filters [data-control="phase"]', "s => s.value")
                    after_slots = rp.evaluate(SLOTS)
                    changed = sum(1 for a, c in zip(before_slots, after_slots) if a != c)
                    ok = v == "race" and changed > 0 and not rdlg and not rerr
                    res.append(("Phase select → Race changes the page (routed http)",
                                f"value {v}; {changed} of {len(after_slots)} phase slots replaced; dialogs {rdlg or 'none'}; "
                                f"errors {rerr or 'none'}", ok))
                except Exception as e:  # noqa: BLE001
                    res.append(("Phase select → Race changes the page (routed http)", f"not usable: {str(e).splitlines()[0][:80]}", False))
                rctx.close()
                # The collapsible panel rule elsewhere: an injected <nav class="filters"> must stay collapsed until .is-open.
                coll = page.evaluate("""() => { const n = document.createElement('nav'); n.className = 'panel filters';
                  n.innerHTML = '<div class="filters-body">x</div>'; document.querySelector('main').appendChild(n);
                  const b = n.querySelector('.filters-body'); const closed = getComputedStyle(b).display;
                  n.classList.add('is-open'); const open = getComputedStyle(b).display; n.remove(); return [closed, open]; }""")
                res.append(("collapsible .filters panel: closed / .is-open", f"{coll[0]} / {coll[1]}",
                            coll[0] == "none" and coll[1] != "none"))
                res.append(("script errors (fragment fetch refused by file:// listed)", "; ".join(errs) or "none",
                            all("fetch" in e.lower() or "fragments/" in e for e in errs)))
                for check, observed, ok in res:
                    rows.append([name, width, theme, check, observed, "ok" if ok else "FAIL"])
                    if name.startswith("after") and not ok:
                        fails_after += 1
                ctx.close()
    b.close()
with (out / "browser.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["render", "width", "theme", "check", "observed", "result"])
    w.writerows(rows)
for r in rows:
    print(" | ".join(str(x) for x in r))
print(f"test_filters: {fails_after} failure(s) on the fix-filters render")
sys.exit(1 if fails_after else 0)
