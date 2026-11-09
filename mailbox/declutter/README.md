# declutter review: smaller headings, a shorter front page (Ümit, relayed by Zeki #3521)

Ümit: 'webden gereksiz büyük fontları değiştirin, sonra gereksiz yazıları çıkartın' (shrink the needlessly big fonts,
then take out the needless text). Branch `declutter`, site commit **239e158**, one commit on origin/main 7b35e40.
**Candidate only. Not merged or deployed.** Presentation only: bg.css, home.py, story.py, pages.py.

## What changed
**1. Fonts (bg.css, every backgammon page; body text unchanged).**
- h1 / the front-page title: `clamp(1.05rem, 1.6vw, 1.35rem)` (was 1.6rem, 1.45rem below 720 px; the sibling-site
  rule 2.25rem was overridden already). Measured: 20.5 px at 1280 (was 25.6), 16.8 px at 375 / 390 (was 25.6).
- h2: `clamp(1rem, 1.3vw, 1.12rem)` (was 1.15rem on cards, 1.25rem on the finding sections, 1.05rem in chart heads):
  16.6 px at 1280, 16 px at 375. h3: .95rem (was 1rem; Leagues' table titles were the browser's 18.7 px).
- The result-card label (.result-card h2, .9rem) keeps its size. The frozen 23 Oct 2026 archive page has its own inline
  styles and is not touched.

**2. Front page.**
- Hero: the title and the counts line only. Title text unchanged (see 'Option for Ümit').
- Every removed or moved block (also `moved.csv`, with the full text):

| Block (front page before) | Now |
|---|---|
| Hero buttons Every decision / Highlights / Read the method | Removed: the top bar's Decisions and Highlights tabs and the footer's Method link go to the same pages. |
| Hero description 'Models play backgammon, and an engine scores every move they make. We measure… Every decision is public.' | About › From the front page › What this is (`about/#front-intro`) |
| Hero board and caption (League 3, dice 3-2, Claude Opus 5.5 (high) … a right risk; Open this decision) | About › From the front page › An example risk call (`about/#front-example`); same SVG, link one level up; About now loads decisions.css so the board has its colours. |
| a. Models are too cautious: paragraph above the chart | About (`about/#text-finding-cautious`) |
| b. Risk judgement by release date: paragraph above the chart | About (`about/#text-finding-release`) |
| c. With the numbers on screen…: paragraph above the chart | About (`about/#text-finding-flinch`) |
| d. More thinking…: paragraph above the chart | About (`about/#text-finding-reasoning`) |
| e. A new starting position: 'Each model was asked…' and 'Random play's own drop is −4.6 PR…' | About (`about/#text-finding-nackgammon`, whole paragraph); the front page keeps the between-group sentence, the late-entry sentence ('Outside the groups, the late entry Base Labs Elephant-1 dropped…') and 'Unclear means the test can't tell, not that the scores are equal.' |
| f. Does the model learn from its games?: 'Status: Done. No arm reached the pre-registered signal threshold (plan section 8).' | Kept in full (status and verdict). |

- Kept as they were: the leaderboard (heading, keys, 'Risk judgement: 100 = every call right, 50 = always safe; higher
  is better.', the table, the row line 'One row per model at its highest reasoning setting, never its best score; late
  entries included. Leagues played different positions; close scores across leagues need not mean a real
  difference.', 'Ranks show observed scores; small gaps need not be meaningful.' under All setups), every chart, legend
  and each section's one caveat, 'How the scores work', the footer.
- About gets a new last section **From the front page** (`#front-page`, in its 'On this page' bar) with the above
  under h3 headings, each finding linking back to its chart (`../#finding-…`). Nothing else on About changed.

## Option for Ümit (title at 375 px)
At the agreed minimum (1.05rem, not below body text) the title is **1 line at 1280, 3 lines at 375 / 390**. Two lines at
375 would need the text shortened. Option, front-page h1 only (the page `<title>`, previews and PNG headers keep the
full title): **'Do models take the right risks, and do they learn from their games?'** (the top bar already says
'Backgammon bench'). Screenshots: `for-umit/after-front-375px-light.png` (as built, 3 lines) and
`for-umit/option-short-title-front-375px-light.png` (the option, 2 lines; text swapped in the browser, not built).

## What ran (logs with exit status in the files)
- New frozen copy of the live state: `/tmp/decl-state` (copied 2026-11-09T12:04:33Z under the update lock
  `~/.local/state/bg-site/lock`; data as of 11:50Z, results 7acf91cb), plus frozen copies of the untracked build inputs
  (replay.db, smoke/part-a.json, workspace/learning-pilot). The live state was only read. Each build used its own copy.
- Full `build.py --state … --no-image` (compute, render and checks.run, which exits 2 on any failure), `/usr/bin/python3`:
  - origin/main 7b35e40: `build-main.log`, **exit status 0**.
  - candidate 239e158 (the committed tree, checked equal to the build's source): `build-candidate.log`, **exit status 0**,
    so **checks.run 0 failures** (links, anchors, unique ids, number traceability, findings).
- `scripts/compare.py` (render vs render), `scripts/narrow.py` (diffs), `scripts/browser.py` (Playwright, Chromium,
  renders served by `python3 -m http.server` over /tmp). Not run: update.sh, deploy, scorers, model calls.

## Results
| Check | Result |
|---|---|
| Files (`compare.md`, manifests) | 2,552 files each, none only in one; different: `index.html`, `about/index.html`, `bg.css` only. |
| Front page text | origin/main's page with the moved blocks taken out (and the kept Nackgammon sentences put in) has **identical text** to the candidate's; all 14 required lines on the page verbatim (list in `compare.md`). |
| About | Text identical to origin/main's once the new section and its nav link are taken out; every moved block in it verbatim; the board's SVG markup identical. |
| Numbers | Front page before = after − kept sentences + moved blocks (multiset of 6,403 numbers; 93 in moved blocks); About after = before + its new section. **0 number changes.** |
| Anchors | Every id of the old front page is still on it or in its moved-anchors map, except the board's two SVG marker ids (`bd-arrow`, `bd-arrow-alt`, not link targets), which are on About; every old About id still there; checks.run's link and anchor check passed site-wide. |
| Browser (`browser.md`, `browser.csv`) | **126/126** candidate loads (21 pages: every top-level page, two model pages and the archive × 375 / 390 / 1280 × light / dark): no sideways overflow, no script error, largest h2 ≤ h1, largest h3 ≤ h2 or body; About's board in colour. |

### First screen (front page, light; dark the same)
| px | title before | after | leaderboard top / row 1 bottom before | after | screen |
|---|---|---|---|---|---|
| 1280 | 25.6 px, 2 lines | 20.5 px, 1 line | 609 / 879 | 219 / 489 | 900 |
| 390 | 25.6 px, 4 lines | 16.8 px, 3 lines | 921 / 1308 | 269 / 655 | 844 |
| 375 | 25.6 px, 4 lines | 16.8 px, 3 lines | 930 / 1333 | 270 / 672 | 844 |

At 1280 the tabs, title, counts line and the leaderboard's first six rows are on the first screen; at 375 the tabs,
title, leaderboard keys and its first three rows (row 1 ends at 672 px of 844) (before: the leaderboard began below the first screen).

## Diffs
- `source.patch`: the branch against origin/main (`tools/site`).
- `render-front.diff`: the front page's hero card and finding sections, before/after, one tag per line.
- `render-about.diff`: About's nav bar and the new section. `render-bg.css.diff`: the stylesheet.

## Screenshots
- `for-umit/before-front-{1280,375}px-light.png`, `for-umit/after-front-{1280,375}px-light.png` (first screen),
  `for-umit/option-short-title-front-375px-light.png`.
- `screenshots/`: full-page before/after at 1280 and 375, after in dark, About's new section at 1280 and 375.

## Not done / for Main
- 'How the scores work' (five bullets at the bottom of the front page) is still there: it is not above a chart or table,
  and these five bullets appear only there (checked: none of them is on About). Moving them to About is a small change
  if wanted.
- The leaderboard table's caption ('One row per model at its highest reasoning setting; all leagues, all phases')
  repeats the row line under the table; kept (table caption).
