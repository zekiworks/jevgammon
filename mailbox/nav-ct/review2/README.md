# nav-ct review 2: the fixes for Zeki #2918

Branch `nav-ct` is now HEAD 90cd56e: d345323 plus two commits (17ac0c7, 90cd56e). This is a candidate: not merged, not deployed. `delta-vs-d345323.patch` is `git diff d345323 90cd56e -- tools/site`: 3 files, 37 lines added and 6 removed (bg.js, bg.css, pages.py).

## What ran (no compute)

- **No `build.compute()`, no bootstrap, no statistics, no model calls.** `scripts/run_retained.sh` renders d345323 and 90cd56e with `scripts/render_retained.py` from the **retained computed state** `/tmp/lct/S.pkl`. That is `build.compute()` of the copy of the live state (results 7b40b30e), made once on 7 Nov for leaderboard-ct review 2 and not re-run. The learning page's data is a file read. Each render was followed by `checks.run`: 0 failures, exit 0 (`r2-runs.txt`).
- **Render diff** (`scripts/render_diff.py`, in `r2-runs.txt`, exit 0): of 2,549 files, 2,433 are identical. 114 HTML pages differ only by the tab row's `id="view-part"`. The only other changes are `bg.js` and `bg.css`.
- **Fix tests:** `scripts/test_fixes.py` on the 90cd56e render: 34/34 ok, exit 0 (`fx-run.txt`, `fixes.csv`).
- **Full review:** `scripts/review.py` (unchanged checks, except that the header-id exception is removed and #view-part is checked) on the 90cd56e render, against the live mirror and the leaderboard-ct render: exit 0 (`review2-run.txt`, `review/`).
  - 0 number differences, in the same 12 comparisons as review 1.
  - Old URLs and anchors: 334/334 ok, now with **no exception**. Every id of every page of live and of leaderboard-ct is on nav-ct, `view-part` included.
  - Browser: 118/118 ok.
  - 48 screenshots.

## The fixes

| # | Zeki #2918 | Fix (bg.js / bg.css / pages.py) | Test (`test_fixes.py`) |
|---|---|---|---|
| 1 | Keyboard-focused box hidden by the pointer | A box is **held** while keyboard focus is in its row (the name or the box). While held, the pointer leaving the row or entering another row neither hides it nor opens another box. It closes when the focus leaves the row, on Escape, or on a click or tap outside.<br>Focus given by a pointer press neither opens nor holds a box; the press decides. A tap still opens and a second tap closes. | 1280×900, light and dark, **every ranked row (31)**:<br>1. Focus the name, Tab into the box.<br>2. The pointer leaves the row: the box is still open.<br>3. The pointer rests on another row: still only that box.<br>4. Escape closes it.<br>Then: a focused box plus a click outside closes it, and hovering a row works again. |
| 2 | No vertical fit on short screens | 1. The box goes below the row if it fits, else above.<br>2. If it fits neither way, it is capped (`max-height`) to the larger side of the row and scrolls inside (`overflow: auto`). The row stays uncovered, so a second tap still reaches it.<br>3. Only when neither side has 120 px does it take the window under the header.<br>Its links stay reachable by scrolling it or with Tab. | **1280×500** (Tab to "Open its decisions →") and **390×500** (tap, then scroll the box), light and dark, every ranked row:<br>• the box is inside the window below the header;<br>• the link is reachable and visible inside the box and the window;<br>• the box stays open.<br>Then the link itself (Enter at 1280, tap at 390) opens Every decision filtered to the setup, with decision cards. |
| 3 | `#view-part` | The tab row (`nav.site-tabs`) carries the old Part row's id `view-part`, so the old fragment lands on the site's parts. The review's header-id exception is removed. | Static: every old id is kept (`review/urls.md`, 334/334).<br>Browser: `#view-part` on home, `method/`, `learning/` and `decisions/` at 1280 and 390, light and dark. The element exists once, is the tab row, sits in the sticky header and is in view; status 200. Also in `review.py`'s deep links (`#view-part`, `method/#view-part`, `about/#view-part`). |

**Found while testing fix 2:** before the fix, on a 390×500 phone, the box opened by focus covered the row being tapped. The tap then landed on a link in the box and navigated away. The second commit (90cd56e) fixes this: pointer focus no longer opens a box, and the box no longer covers its row.

## Screenshots of the changed cases (`fix-screenshots/`)

- `mixed-focus-then-pointer-on-another-row-1280-light.png`: focus in row 2's box, pointer on another row, row 2's box still open.
- `short-window-row1-1280x500-{light,dark}.png`: Tab has reached the link.
- `short-window-row1-390x500-{light,dark}.png`: the box above the row, capped and scrolled to its links.
- `view-part-{1280,390}-light.png`.

## Limits (as Zeki states)

- Tested in Chromium through Playwright only: emulated touch and mouse, file render with request routing. Safari/VoiceOver and a physical iPhone are untested.
- Enlarged text was not tested separately. The 500 px windows exercise the capped, scrolling case: 31 of 31 boxes at both 1280×500 and 390×500.
- The first-screen numbers in review 1 compare against a99a1ce, not against the phone-fixed live ff652d8.
