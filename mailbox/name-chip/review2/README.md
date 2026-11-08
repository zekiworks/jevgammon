# name-chip review2: score and interval fully visible at 375/390 (Zeki #3240)

Branch `name-chip`, HEAD **1fbfb6d**, on fc31b85 (round 1), which sits on origin/main 58cd3ac. **Candidate only. Not
merged or deployed.**
- `delta-vs-fc31b85.patch`: this round's change only (bg.css, the phone block, +4 lines; 2 commits 651d81e, 1fbfb6d).
- `source.patch`: the whole branch against origin/main.
- `render-bg.css-vs-fc31b85.diff`: the rendered change vs round 1's render. Of the 2,552 rendered files, **only bg.css
  differs** from fc31b85's render (index.html byte-identical).

## The bug and the fix
At 375 px the chip's no-wrap width set the model column's minimum, the table grew to 370 px in a 328 px frame
(overflow-x: auto), and every row's upper interval end (and the score's right part) lay past the frame's visible edge:
round 1's render, measured with this round's check: 63 of 63 rows clipped at 375 (0 at 390). Phones only (≤ 640 px):
- the chip may wrap between its parts (`white-space: normal`, smaller radius), so it no longer sets a wide minimum;
- the bar column takes only what the model column leaves (`width: auto`, min 8rem, as before), so names are not
  squeezed into two lines by the freed width going to the bar.
Desktop unchanged (1280: every chip on its name's line, as round 1).

## What ran (logs and exit codes in the files)
- The same frozen state copy as round 1, `/tmp/chip-state` (data as of 2026-11-08 16:05Z, results 5aaf6587),
  still present; the live state was only read.
- Full `build.py --state /tmp/chip-state --no-image`, `/usr/bin/python3`: candidate 1fbfb6d `build-candidate.log`,
  **exit status 0** (checks.run 0 failures). origin/main 58cd3ac: round 1's render of the same state
  (`build-main.log`, exit status 0), reused unchanged.
- Not run: update.sh, deploy, scorers, model calls.

## Results
| Check | Result |
|---|---|
| Files (`compare.md`, manifests path+sha256+bytes) | 2,552 each, none only in one; vs origin/main only `index.html`, `bg.css` differ. compare exit 0. |
| Numbers (`numbers.csv`) | **63/63 rows equal**, boxes 0 differ, home text outside the leaderboard identical. **0 number changes.** |
| Chip and name vs data (`chips.csv`) | 63/63. |
| Browser 375/390/1280 light+dark (`browser.md`) | **46/46, exit 0**. New at 375/390: for every row (expanders open, 63 score cells) the score and both interval ends (a text Range per number, 189 numbers) lie inside the table frame's visible box (left .. left + clientWidth at scrollLeft 0), no ellipsis; **table not wider than its frame**: 375: table 327.8 px, frame 328 (scrollWidth 328, nothing to scroll); 390: 342.8 / 343. Rightmost number edge 299.8 px vs frame edge 351.6 (375). Page overflow 0. Chip = data 63/63 at every size. |
| 375 px two screens (844 px) | Row 3 ends at **1458** (origin/main 1430, round 1 1442), within 1688; 5 rows within two screens (main 6). 390: 1434 (main 1422), 6 rows. |
| Hover sweep (`sweep-candidate.md`) | **32/32, exit 0** (Chromium + WebKit, 1280/1440, light + dark). |
| Mouse into the box, click links (`links.md`) | **36/36, exit 0**. |

Note: origin/main itself is 9.6 px wider than its frame at 375 (table 337.6 in 328; numbers still inside, check 0
bad); the candidate fits.

## Screenshots
`for-umit/front-page-375px-light-two-screens.png`, `for-umit/front-page-1280px-light.png` (and origin/main's
`before-live-*`); `screenshots/` has the rest.

## Scripts
`scripts/browser.py` gained the clipping check (`CLIP`); the others as round 1.
