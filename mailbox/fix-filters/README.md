# fix-filters: the home page's filter row was hidden

Branch `fix-filters` (e3dc886) on origin/main ddc0fad. It changes one rule in `tools/site/assets/bg.css` and nothing else. It is not merged and not deployed.

## The bug

On live (mirror of 19:35Z) and on origin/main, the filter row on the home page is an empty bar. That row holds:
- the League, Models and Measure links;
- More filters (phase, reasoning, runs on, weights);
- the setup count and Reset.

The cause is in the CSS. site.css's collapsible-panel rule `.filters:not(.is-open) .filters-body { display: none }` has specificity 0,3,0. It outranks bg.css's `.filter-row .filters-body { display: flex }` at 0,2,0. No script sets `is-open` on this row, so `#filters-body` computes to `display: none`.

## The fix

The rule is now `nav.filters.filter-row .filters-body { display: flex; … }`, with specificity 0,3,1. It is more specific than the collapse rule, so it wins regardless of file order. The collapse rule itself is untouched. No page of the site uses a collapsible `.filters` panel; the test checks the collapse rule on an injected panel.

## What ran (`runs.txt`, with every exit status)

Both renders come from the **retained** computed state `/tmp/lct/S.pkl`. That state was produced by `build.compute()` at 19:18 UTC on the copy of the live state (results 7b40b30e). No statistics or model calls ran again. The learning page's data, which is a file read, comes from the 19:35 state. The renderer is `scripts/render_retained.py`.

- **Renders:** origin/main and fix-filters, each followed by `checks.run`. Result: **0 failures on both**, exit status 0 for each.
- **Numbers unchanged:** every rendered file of the two trees was compared byte for byte, and the only difference is `bg.css`. So every page, data file and number is identical, exit status 0.
- **Browser** (`scripts/test_filters.py`, `browser.csv`): file:// at 1280 and 390 px, light and dark, on the render before and after the fix.
  - `#filters-body` display is not `none`.
  - League, Models, the Measure link, More filters and Reset are visible. Playwright's real clicks work: League 2 and Chat become pressed, More filters opens its fold, and Reset returns to the defaults.
  - The phase select is visible inside the open fold and can be operated. Under file://, bg.js's fetch of `fragments/` is refused, so the page alerts "Could not load this phase (Failed to fetch)"; this is recorded.
  - Over routed http (no server), choosing Race sets the select, replaces the phase slots, and raises no dialog or error.
  - The collapsible `.filters` panel stays hidden without `.is-open` and shows with it.
  - **Before** the fix (origin/main), every one of these checks fails, because the row cannot be seen.
  - Exit status: 0 for the fixed render (see `runs.txt`).
- **Screenshots:** `screenshots/filter-row-{1280,390}-{light,dark}.png`, taken from the fixed render at `#filters`.

## Files

- `scripts/`: `run.sh`, `render_retained.py`, `test_filters.py`.
- `runs.txt`, `browser.csv`, `screenshots/`.
