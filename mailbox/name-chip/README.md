# name-chip review: one chip after the name (Ümit #3193)

Branch `name-chip`, HEAD **fc31b85**, two commits on origin/main 58cd3ac (9fc49fd the chip, fc31b85 the wide-window
column). **Candidate only. Not merged or deployed.** Presentation only: story.py and bg.css; the details box is unchanged
(its HTML byte-identical in all 63 rows), bg.js and tables.js unchanged.

## What changed
- The name line shows the model name, then **one small grey chip**: `<setting> · <chat|decision>`, the setting left out
  where the setup has none (`decision`). Examples from the render: `GPT-6 Astra` `high · chat · late entry`,
  `Liquid d1-ultra` `decision`, `Drex Max v1` `decision · late entry · provisional`, `Kimi K3.1 Pro` `off · chat`.
- The late-entry / provisional tag is **inside the same chip** (no second tag).
- Programs: chip `program`; their other-league rows `League 2 · program`, `League 3 · program`.
- Other-settings rows: the chip with their own setting (`low · chat`), in place of the old 'other setting of …' text.
- **GPT-6 Astra:** the main row's name was already `GPT-6 Astra` (no '(high)'); its chip says `high · chat · late entry`.
  Other-settings rows carried the setting in the name (`GPT-6 Astra (low)`): the trailing `(<setting>)` is left out
  of the **visible row name only** when it equals the chip's setting, so the setting is never shown twice. Data, links
  (href unchanged in 63/63) and the box's first line (`GPT-6 Astra (low) · OpenAI · chat model · low`) keep the full
  name. `DeepSeek V4.1 Flash 1017 (low)` shows `DeepSeek V4.1 Flash 1017` `low · chat`; `Drex 2.0 (local)` keeps its
  name (no setting on record, chip `decision · late entry · provisional`).
- Maker: only the colour dot (its title) and the box.
- Wide windows (≥ 1200 px): the model column is 22.5rem so every name and chip stand on one line (at 1280 the bar
  column goes from 373 to 253 px; without it 35 of 63 chips wrapped under the name). Below 1200 px a chip that does not
  fit wraps whole onto the next line (never inside itself).

## What ran (logs and exit codes in the files)
- New frozen copy of the live state: `/tmp/chip-state` (copied 2026-11-08 16:08Z, data as of 16:05Z, results
  5aaf6587; plus frozen copies of the repo's untracked build inputs replay.db, smoke/part-a.json,
  workspace/learning-pilot). The live state was only read.
- Full `build.py --state /tmp/chip-state --no-image` (production compute, render and checks.run; exits 2 on any
  checks.run failure), `/usr/bin/python3`:
  - origin/main 58cd3ac: `build-main.log`, **exit status 0**.
  - candidate fc31b85: `build-candidate.log`, **exit status 0**. So **checks.run 0 failures on both.**
- Not run: update.sh, deploy, scorers, model calls.

## Results
| Check | Result |
|---|---|
| Files (`compare.md`; `manifest-main.tsv`, `manifest-candidate.tsv`: path, sha256, bytes) | 2,552 files each, none only in one; different: `index.html`, `bg.css` only. compare exit 0. |
| Numbers (`numbers.csv`) | **63/63 rows equal** (row + box, chip and the old small line out); boxes 0 differ; home text outside the leaderboard identical. **0 number changes.** |
| Chip and name vs data (`chips.csv`, `compare.md` §3) | **63/63**: one chip, no other small line; chip = setting · type from the box's first line + origin/main's late tag; programs as above; name = origin/main's minus ' (<setting>)'; link unchanged. |
| Browser 375/390/1280 light+dark (`browser.md`, `chips-shown-*.json`) | **42/42, exit 0.** Per size/theme: all 63 chips as shown (expanders open) = data, one line, inside the cell; no sideways overflow (375: 0 px); at 1280 every chip on its name's line; at 375/390 28 of 63 on the name's line, the rest wrapped whole; boxes open on every ranked row (hover at 1280, tap + second tap at 375/390); focus beats pointer; filter. |
| 375 px, two screens (844 px) | Row 3 ends at **1442** (origin/main 1430), within 1688; 6 rows within two screens (same). 390 px: 1434 (was 1422). |
| Hover sweep (`sweep-candidate.md`) | **32/32, exit 0** (Chromium + WebKit, 1280 + 1440, light + dark). origin/main: 32/32 (`sweep-main.md`). |
| Mouse into the box, click links (`links.md`) | **36/36, exit 0** (Chromium + WebKit, 1280 + 1440). |

## Diffs
- `source.patch`: the branch against origin/main (story.py +26 −9, bg.css).
- `render-narrow.diff`: the leaderboard's model cells, origin/main vs candidate (box taken out; the boxes are identical).
- `render-bg.css.diff`: the rendered bg.css.

## Screenshots
- `for-umit/front-page-1280px-light.png`, `for-umit/front-page-375px-light-two-screens.png` (and origin/main's
  `before-live-*`). `screenshots/` has the rest (hover at 1280 rows 1/38, tap at 375 light/dark, 375 dark).

## Scripts (`scripts/`)
`compare.py BASE NEW OUT`, `browser.py URL BASE NEW OUT`, `sweep.py URL OUT LABEL`, `links.py URL OUT`,
`shots.py URL PNG` (Playwright; the renders served with `python3 -m http.server` over /tmp). sweep/links/shots are
no-subline review2's, unchanged.
