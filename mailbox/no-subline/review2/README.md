# no-subline review2: box links usable with the mouse (Zeki #3146, #3147)

Branch `no-subline`, HEAD **ed85086**, one commit on 99cca67, which sits on origin/main 5607f2f. **Candidate only. Not
merged or deployed.**
- `delta-vs-99cca67.patch`: the rework only (bg.js +43 −17, bg.css +2 −2).
- `source.patch`: the whole branch against origin/main (story.py, bg.css, bg.js, tables.js).

## What changed since 99cca67
- **Removed:** `pointer-events: none` on hover-opened boxes (class `hl-hover`). The box takes the pointer normally and
  its links work with the mouse. A row click is not a pin; a mouse click still opens the row's decisions.
- **Geometry:** where the window has room, the box stands **beside its row**, right of the score column (if that has
  no room, right of the name column). It starts at the row's top. Near the window's foot it ends at the row's bottom
  instead, and it is capped to the window under the header, scrolling inside. So it never covers another row's name,
  and at 1280/1440 it never covers a score either: moving down the name or score column always hits a row. On phones
  (no room beside) placement is unchanged: under the row, above it near the bottom, same capping.
- **Intent:** leaving the row and its box (the box is inside the row) closes it after **150 ms**. Coming back to the row
  or the box cancels the close. Entering another row shows that row's box at once.
- **Kept:** focus beats the pointer (Zeki #2918), the tap behaviour, Escape, the short-screen capping, the sub-line
  removal and box first line (unchanged from 99cca67), and the tables.js tap fix.

## What ran (logs and exit codes in the files)
- The frozen copy of round 1 had been deleted. I made a **new frozen copy of the live state**, `/tmp/nosub-state2`
  (copied 8 Nov, data as of 15:05Z, results 8f38dd91; the live state was only read).
- `build.py --no-image` ran on it twice. That is the full production compute, render and checks.run; build.py exits 2
  on any checks.run failure.
  - origin/main eb8d8c0 (tools/site the same as 5607f2f): `build-main.log`, **exit status 0**.
  - Candidate ed85086: `build-candidate.log`, **exit status 0**.
  - So **checks.run had 0 failures on both**.
- Not run: update.sh, deploy, scorers, model calls.

## Results (each script's exit code is in its `*-run.txt`)
| Check | Result |
|---|---|
| Files (`compare.md`, `manifest-main.tsv`, `manifest-candidate.tsv`: path, sha256, bytes for every file of both renders) | 2,550 files each, none only in one. Different: `index.html`, `bg.css`, `bg.js`, `tables.js` only; every data and decision file is byte-identical. compare exit 0. |
| Numbers (`numbers.csv`: per row, the sorted number multiset of both renders) | **63/63 rows equal** (row + box, without the old sub-line and the box's first line, which is checked word for word below). Home text outside the leaderboard is identical. **0 number changes.** |
| Box first line (`compare.md` §3) | 63/63. |
| Hover sweep (`sweep-candidate.md`) | **32/32, exit 0.** Chromium + WebKit, 1280 + 1440, light + dark. 167 checks over all 41 rows: down and up the names, down the scores, from the right onto each name, and resting 3 s on rows 5, 15 and the last. Also: mouse click opens the decisions; focus on row 1 holds its box with the mouse on row 3; no script error. |
| Hover sweep, origin/main (`sweep-main.md`) | 24/32, exit 1: the wrong-box bug in all 8 combinations, as reported. |
| **Mouse into the box, click links** (`links.md`) | **36/36, exit 0.** Chromium + WebKit, 1280 + 1440. For rows 1, 10, the last ranked row (38) and the last row (41, Safest, a program), the mouse goes onto the name, along the row into the box, down to each link, and clicks. The box stayed open, the link was under the mouse, and the page landed on the link's own URL. 'Released' was clicked on rows 1 and 10 (row 38 and the program have no release month); 'Model page' on rows 10, 38 and 41 (row 1 is a late entry, which has 'Its late-entry page' instead, also clicked); 'Open its decisions' on rows 10, 38 and 41. External pages were answered locally, not fetched. |
| Browser 375/390/1280, light + dark (`browser.md`) | **42/42, exit 0**, the same checks as round 1. |
| 375 px, two screens (844 px) | Row 3 ends at **1430** (origin/main 1552), within 1688. Six rows within two screens (was 4). At 390 px: 1422 (was 1523). |

## Screenshots
- `for-zeki/1280px-mouse-down-names-to-kimi.png`: mouse moved down the names to Kimi K3.1 Pro; Kimi's box shows,
  beside the row. `screenshots/hover-down-to-kimi-1280-main.png` shows the same move on origin/main, with Grok 4.7's box.
- `for-zeki/front-page-1280px-light.png`, `for-zeki/front-page-375px-light-two-screens.png`; `screenshots/` has the
  rest (hover at 1280 on rows 1 and 38, tap at 375 light and dark, before/after).

## Scripts (`scripts/`)
`compare.py BASE NEW OUT`, `browser.py URL BASE NEW OUT`, `sweep.py URL OUT LABEL`, `links.py URL OUT`,
`shots.py URL PNG` (Playwright; the renders served with `python3 -m http.server` over /tmp).
