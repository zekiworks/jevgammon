# no-subline: nothing under the model name (Ümit #3039), plus the hover-box fix (HoverCheck)

Branch `no-subline`, HEAD 99cca67, one commit on origin/main 5607f2f. The tools/site tree is the same as at ac60201.
**Candidate only. Not merged or deployed.** Diff: `source.patch` (4 files, +38 −28).

## Change
- **Leaderboard rows:** the line under the model name ('maker · chat model / decision model · setting', or a
  program's reference label) is gone. The row keeps the rank, maker dot, family icon, model name, the 'late entry' /
  'late entry · provisional' tag (small, grey, after the name on the same line), the expander, the bar with its whisker,
  the score, and the wide-screen columns.
- **Details box, first line:** `<model> · <maker> · <chat model / decision model> · <setting>`. A part that is not on
  record is left out ('Maker not recorded' is not shown; a decision model with no setting has no setting). A program
  shows `<name> · <reference label>`, the label that used to sit under the name; its other-league rows show the same
  label. The setting moved from the old 'Setting X · League N' line, which is now just 'League N'. The other lines are
  unchanged.
- **Hover fix (HoverCheck, live bug):** the box is fixed under its row and covers the name cells of the rows below.
  With the pointer on the box it still counted as on the passed row, so on live, resting on Kimi K3.1 Pro's name
  showed Grok 4.7's box. Now a box opened by hover lets the pointer through (`hl-hover` → `pointer-events: none`), so
  the row under the mouse, not the box, decides which box shows. Unchanged: keyboard focus beats the pointer (Zeki
  #2918; a focused row's box takes the pointer, so its links work), the tap behaviour, and placement with short-screen
  capping. A mouse click on a row still opens its decisions, as on live.
- **Tap fix (found while testing):** on live, tapping a row's bar or score did not open the box. bg.js does call
  `preventDefault`, but tables.js's row-link handler then followed the row's first link and opened the decisions page.
  Only a tap on the name opened the box. tables.js now leaves a prevented click alone (one line). This makes the
  documented tap behaviour ("a tap opens the box") hold for the whole row.

## What ran
- `tools/site/build.py --no-image` (full production compute + render + **checks.run**) on a **frozen copy of the live
  state** (`/tmp/nosub-state`, copied 8 Nov, data as of 14:50Z, results 8f38dd91). It ran twice: once with
  origin/main's tools/site and once with the branch's. **Both exit 0, checks.run 0 failures.** No retained computed
  state was used: the only one, `/tmp/lct/S.pkl` from 7 Nov, is older than later main changes. The live state itself
  was only read.
- Not run: update.sh, deploy, scorers, model calls.

## Results
| Check | Result |
|---|---|
| Numbers / files (`compare.md`) | 2,550 files each. Only `index.html`, `bg.css`, `bg.js` and `tables.js` differ; all data and decision files are byte-identical. The numbers in all 63 leaderboard rows (row + box) are equal. The home text outside the leaderboard is identical. **0 number changes.** |
| Box first line (`compare.md`) | **63/63** rows: the expected first line is origin/main's first line plus its old sub-line (the setting for other-setting rows); late tags unchanged; no sub-line left. |
| Browser 375/390/1280, light + dark (`browser.md`) | **42/42**. No sub-line; late tags small on the name's line; no sideways overflow; the box opens with the right first line on **every ranked row (38)**: at 1280 on hover over the name, bar, score and empty space; at 375/390 on a tap on the name, bar and score, with a second tap closing it and no navigation. Focus beats pointer. Filter All / Chat / Decision (only that type plus programs, the box opens on filtered rows). No script error. |
| 375 px, two screens (844 px) | Row 3 ends at **1430** (origin/main: 1552), ≤ 1688. 6 rows within two screens (was 4). At 390 px: 1422 (was 1523). |
| Hover sweep, candidate (`sweep-candidate.md`) | **32/32**. Chromium + WebKit, 1280 + 1440, light + dark. 167 checks over all 41 rows (38 ranked + Random, GNUbg weak, Safest): down the name column, up the name column, down the score column, from the right onto each name, and resting 3 s on rows 5, 15 and the last. The open box was always the box of the row under the mouse, checked within one row move. Mouse click still opens the decisions; focus beats pointer; no script error. |
| Hover sweep, origin/main (`sweep-main.md`) | 24/32: the sweep check **fails in all 8 combinations**, the box of a passed row stays open (e.g. resting on row 3 shows row 2's box). `screenshots/hover-down-to-kimi-1280-main.png` shows Grok 4.7's box while the mouse is on Kimi K3.1 Pro; the candidate shows Kimi's. |

## Screenshots
- `for-umit/front-page-1280px-light.png`, `for-umit/front-page-375px-light-two-screens.png` (candidate);
  `for-umit/before-live-375px-light-two-screens.png` (origin/main, same state);
  `for-umit/375px-row1-tapped-box.png`; `for-umit/1280px-mouse-down-names-to-kimi.png`.
- `screenshots/`: hover at 1280 (rows 1 and 38), tap at 375 light/dark, two screens at 375 dark, before/after.

## For Ümit / Main to decide
- With a mouse, a box opened by hover can no longer be entered: the pointer passes through it to the row below. Its
  links ('Open its decisions' = the row click; 'Model page'; the 'Released' source) are reachable by Tab (focus holds
  the box) and on a phone by tap, but not by mouse. If mouse access to those links matters, one option is a click on
  the row that pins the box. That would replace the current click-opens-decisions.
- A program's other-league rows now show the reference label on their box's first line, the same as the main row.

## Scripts (`scripts/`)
`compare.py BASE NEW OUT`, `browser.py URL BASE NEW OUT`, `sweep.py URL OUT LABEL`, `shots.py URL PNG` (Playwright,
renders served by `python3 -m http.server` over /tmp).
