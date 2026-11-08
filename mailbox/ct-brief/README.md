# ct-brief: the backgammon site as Clocktower Bench (Ümit #2938, About text #2939)

Branch `ct-brief`, HEAD ace14d5, one commit on origin/main e70840e. **Candidate: not merged, not deployed.**
Diff: `source.patch` (tools/site only: 9 files, +777 −202). What the brief asks against what was live: `GAP.md`.

## What ran
- `scripts/run_retained.sh`: origin/main and HEAD rendered from the **retained computed state** `/tmp/lct/S.pkl`
  (build.compute() of the live state, 7 Nov, results 7b40b30e; **no compute ran**); the learning page's data read from a
  copy of the live state's `learning/`; results label a8708ed6 and data-as-of label set to live's. checks.run on both:
  **0 failures** (`review-render-run.txt`). Not run: build.py main, update.sh, deploy, scorers, model calls.
- `scripts/review.py`: numbers vs the live mirror, old anchors, links, browser, screenshots (`review/`, `review-run.txt`).

## Results
| Check | Result |
|---|---|
| checks.run (HEAD render) | 0 failures |
| Numbers vs live, label-aware (`review/numbers.md`) | 17,377 home table cells where each table now is: 0 diff; 63 leaderboard rows + details boxes + wide cells: 0; Too safe / bias / numbers-on-screen bars: 0; 114 other pages' main text identical; 2,403 data and decision files byte-identical, no new data file. 4 block-level differences, all explained: `#leagues-tabs` (the old wrapper held the sections; it now names the Leagues tab bar, the sections compare equal under their own ids) and `#board-panel`/`#charts`/`#chart-risk` (the "Risk call card" PNG line, written only by build.py's image step, absent from every retained render incl. origin/main's). review.py exits 1 on these by design. |
| Old home anchors (`review/anchors.md`) | 313/313 live home ids at 1280 (+32 at 390): 0 missing; land on home 123, leagues/ 162, nackgammon/ 28 |
| Links (`review/links.md`) | 19/19 internal tab, hero, Decisions, Experiments, About and footer links 200 (GitHub not fetched) |
| Browser 375/390/1280 light+dark (`review/browser.md`) | 78/78: one tab row on 7 pages, no chip row on home, no sideways overflow, no script error; row 1 GPT-6 Astra (high) 74.4 late entry; no DeepSeek 1017 row; wide columns only ≥900 px; white tick |
| 375 px first screens | screen 844; hero ends 914, row 1 ends 1312, row 3 ends 1503 ≤ 1688 (two screens) |
| Screenshots for Ümit | `for-umit/front-page-1280px-light.png`, `for-umit/front-page-375px-light-two-screens.png`; 42 more in `review/screenshots/` |

## Finding headings (evidence/a.md … f.md; each heading decided in code by the stated rule)
| | Heading | |
|---|---|---|
| a | Models are too cautious. | kept: 38/38 ranked models risks found < safe right (18.7–53.3% vs 59.8–97.6%); GNUbg weak grey 66.6/67.6 |
| b | Risk judgement by release date | **neutral**: 24/38 dated; Google rises, Fastino falls (60.4 → 58.8) |
| c | With the numbers on screen, every model asked played safer | kept as live ("asked": 8 models), Clear risk preliminary |
| d | What thinking adds | **neutral**: 9 models; lower error at highest setting 9/9, but higher risk judgement 7/9. Astra 75.8/74.7/74.4, 11.8/11.1/8.8 match the brief |
| e | A new starting position | **neutral** (Zeki #2961): the data hold only between-group drop differences (all 99% intervals include 0: groups not shown to differ), no per-group drop interval; late entry Base Labs Elephant-1 dropped (+8.66, 97.5% +0.42 to +16.02), said in the section |
| f | Does the model learn from its games? | question; status "Done" + the published verdict sentence, risks-found chart |

## Highlights fact check (evidence/highlight-108669.md)
Decision 108669 (League 3, GPT-6 Astra (low), dice 4-3): model 7/3 7/4, 0 of 36 hitting rolls ✓; engine best 6/2 24/21,
36 of 36 ✓ (two blots, not one); difference 0.2238 ✓. Built from the export; content/highlights.json's stated facts are
compared at build. **Brief mismatch:** its sample details box says Astra (high) "Risks found 57% · Took 267 of 465";
the data say 53.3%, 248 of 465 (live shows the same). Not changed.

## Missing inputs / decisions for Ümit
- Highlight stories (all slots "Story coming"); slots 2–6 are candidates only.
- `CHECK-LINES.md`: the [check] lines fixed, two other claims fixed (late entries, cost), the two rank sentences
  replaced by Zeki's accepted one (**flagged deviations**), note on "never merged".
- Judgement calls: filters kept on Leagues (they drive Every number); Risk pays vs safety pays and Close choices stage B
  moved to Leagues (not named in the brief); old clear-risk bias chart now under Clear risk; old About sections kept under
  Ümit's four.

## Checks to run before merge
Full `build.py` (image step, results hash will be unchanged: no data file changed), checks.run, and a look at the
risk-call-card line on Leagues.

## Update: Zeki #2961 (branch HEAD 2c41357)
Finding (e) heading is now the neutral **"A new starting position"**: the data hold only between-group drop differences
(99% intervals, all including 0 = the groups are not shown to differ), no interval for a group's own drop. The sentence
says that; Random's drop, the Elephant-1 exception and the "unclear" note are kept (`evidence/e.md`, correction).
Re-rendered from the retained state: checks.run 0 (`review-render-run-2961.txt`). `review/delta-2961.txt`: against the
ace14d5 render every file is identical except `index.html`, and the home page is identical outside
`#finding-nackgammon`; the section has no new number (only the interval level, 99%, now named; it is nack-paired.json's
`primary_level`). The other review results above are for ace14d5 and still hold for everything outside that section.

## Review 2: Zeki #2963 (branch HEAD 0ed9029 = 2c41357 + one commit)
Delta vs ace14d5: `delta-vs-ace14d5.patch` (bg.css, content/about.md, story.py; +26 −15). Full diff vs main: `source.patch`.
- **Fix 1 (#2961, 2c41357):** finding (e) heading "A new starting position" (see the update above).
- **Fix 2:** under each model name "maker · chat model / decision model · setting" (parts on record only: "Maker not
  recorded" and a decision model's absent setting are left out), late / provisional tag kept. E.g. "OpenAI · chat model ·
  high · late entry".
- **Fix 3:** About "Risks found" = a worthwhile risky play, at least 0.001 better than the best safe play (a lesser risky
  play is a wrong risk); box bullet 2 and finding (a) text and axis likewise. Listed for Ümit in CHECK-LINES.md section D
  (the details box's "Took N of M risks that paid" is Ümit's own example wording: flagged, unchanged).
- Also from the review notes: finding (b) "That is not a consistent increase across the makers shown."; a wide-screen
  note that $ per 1,000 is at each setup's price basis named in its details, not a bill paid.

Renders: retained state, no compute; checks.run 0 (`review-render-run-2963.txt`). `review2/` (`review2-run.txt`):
- **review.py exit status 1, by design, on 4 differences, all explained, 0 unexplained** (`review2/numbers.md`):
  `#leagues-tabs` (the old wrapper; its sections compare equal under their own ids) and `#board-panel`, `#charts`,
  `#chart-risk` (the Risk call card line, written only by build.py's image step; the release check below shows it).
- 17,377 old home table cells: 0 differences; 63 leaderboard rows and boxes: 0; 114 pages compared: 107 equal, 7
  expected changes, 0 unexpected; 2,403 data/decision files equal after gunzip, data/manifest.json excluded, no new file.
- Anchors: 313 at 1280 + 32 at 390, 0 missing; 344/345 in view or hidden by design. The one: `#f-kind` at 390 → leagues/,
  the filter row's "Models" label, which is visually hidden (1 px, clipped) at phone width; re-opened with a longer wait
  it is at y 114 inside its filter row (y 65–189) of an 844 px screen.
- Links 19/19 internal 200; browser 78/78 at 375/390/1280 light and dark.
- 375 px after the longer sub-line: hero ends 914, row 1 ends 1329, row 3 ends 1552 ≤ 1688 (two screens of 844).
- Screenshots for Ümit (replaced): `for-umit/front-page-1280px-light.png`, `for-umit/front-page-375px-light-two-screens.png`.

## Release check: production path (`prod-build.txt`)
`build.py` (the real build, image step included) on ct-brief 0ed9029, on a scratch copy of the state
(/tmp/ctb/scratch-state; not the live state), out /tmp/ctb/out-prod; no deploy, no timer, no redirects:
**exit status 0**, with checks.run inside it (exit 2 on any failure): 0 failures. Leagues shows the Risk call card line
with its three PNG links, all present, where live has it on its home page. Data: 2,403 files equal to live after gunzip
(manifest excluded); results label 2b432cfb vs live a8708ed6 only because the copy's snapshot time is 10:35Z. Nothing
shared was written.
