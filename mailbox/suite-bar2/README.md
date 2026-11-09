# suite-bar2 review: turkce's roomier top tabs (Ümit #3501/#3507/#3532, turkce #3535)

Branch `suite-bar2`, one commit on origin/main 7b35e40. **Candidate only. Not merged or deployed.**

## Change
- `tools/site/assets/suite-bar.css` replaced by `/home/cbasaran/code/tb-next/suite-bar.css`, byte-identical:
  sha256 7c686c6d5be33c47b1069436067c20da491bfe9863e43e56fb348eb70ed11bca (was 0ebf1077…8590).
- `tools/site/content/suite-bar.html` unchanged: sha256 87fc5320…aa1b, the same as turkce's.
- No hash pins to update: no check or selftest pins the CSS hash. The scoped-ban exception (checks.without_suite_bar)
  matches the strip's HTML (common.SUITE_BAR), which did not change.

## What ran
- Frozen copy of the live state: `/tmp/sb2-state` (copied 9 Nov 12:06Z, data as of 12:05Z, results 3000c912; the live
  state was only read).
- `build.py --no-image` on it (full compute, render and checks.run; exit 2 on any checks.run failure):
  origin/main 7b35e40 `build-main.log` exit 0; candidate `build-candidate.log` exit 0. So checks.run 0 failures on both.
  (Also ran once on the previous main 5e29f80 before rebasing: same result.)
- `selftest_suite_bar.py`: all cases as expected, exit 0 (`selftest-suite-bar.txt`).
- Compare (`compare.txt`, `manifest-*.tsv`: sha256 of every file): 2,552 files each; the only different file is
  `suite-bar.css`. Every page, data and decision file is byte-identical, so every number is equal.
- Browser (`scripts/browser.py`, `browser.md`/`browser.csv`): Chromium, 375/390/1280, light + dark, home (= the
  leaderboard, index.html), improve, learning, about, both renders. 520 checks, 0 failed.
- Not run: update.sh, deploy, scorers, model calls.

## Measured (light; dark the same)
| | main | candidate |
|---|---:|---:|
| Sticky header, 1280 | 92 px | 116 px (+24) |
| Sticky header, 375/390 | 98 px | 118 px (+20) |
| Suite strip, 1280 / 375 | 27 / 27 px | 51 / 47 px |
| Strip's own sideways scroll, 375 | 12 px | 76 px |
| Strip's own sideways scroll, 390 | 5 px | 61 px |
| Strip's own sideways scroll, 1280 | 0 | 0 |
| Page overflow (scrollWidth − clientWidth), all widths/pages | 0 | 0 |
| Ranked leaderboard rows within two screens, 375 | 4 | 4 |

- 375: the third link (English & Turkish Reading) sits at x 335–451 of 375, so about 40 of its 116 px show until the
  strip is scrolled (main: fully visible minus 12 px).
- Anchors: 4 in-page anchors per page, every width/theme; each lands with its top below the sticky header's bottom
  (`--view-bar-h` follows the header's height on every page).
- Details box (home, rows 1 and 5; hover at 1280, tap at 375/390): inside the window and below the header in every case.

## Screenshots for Ümit
`screenshots/{main,cand}-{home,improve,learning,about}-{1280,375}-light.png` (viewport, top of the page).
