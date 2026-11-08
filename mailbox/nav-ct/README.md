# nav-ct: the site's navigation as Clocktower Bench's (Ümit #2901, with #2904 and #2907)

Branch `nav-ct`, HEAD d345323. It is a **candidate**: not merged, not deployed. It holds leaderboard-ct (approved, not merged) and this change, **rebased onto origin/main ff652d8** (the mobile fix, MobileFix). See "Conflicts" below.

## What ran

`scripts/run_render.sh` copies the live state and the live mirror once, then renders the whole site twice from that copy with `scripts/render_site.py`: once with leaderboard-ct's `tools/site` (a99a1ce, the base) and once with nav-ct's. Both renders use the same results hash.

- **Not statistics-free.** render_site.py calls `build.compute()`, which reads every published aggregate and runs the site's offline computations, including the bootstrap loops in `offline.py`.
- **What did not run:** `build.py main`, `update.sh`, deploy, model calls, scorers and rescoring.
- **checks.run:** 0 failures on both renders, exit 0 (`checks-run.txt`).

Then `scripts/review.py` compares the numbers, checks the old URLs and anchors, runs the browser tests and takes the screenshots. It exits 1 on any difference or failed check. It exited 0 (`review-run.txt`).

## What changed (tools/site)

| # | Ümit's item | Done |
|---|---|---|
| 1 | Top bar | One sticky header on every page, made of three rows: the shared Hilde suite strip (`content/suite-bar.html` and `assets/suite-bar.css`, unchanged), then the Hilde leaf and **Backgammon bench** with the Dark/Light keys and More options on the right, then the tabs **Leaderboard · Decisions · Highlights · Experiments · About**. The tab of the page in view has a 3 px underline in the link colour.<br>**The leaf:** Hilde Reader's bare copper leaf (hilde repo `assets/reader-leaf.svg`), copied byte for byte as `assets/hilde-leaf.svg` (sha256 a476cc18…). No new logo.<br>**Removed:** the old Home/Part bar ("Risk calls · Learning across games") and the "Pages" row. |
| 2 | Leaderboard = front page | The home page with its existing content: question, 3 buttons, the table, findings, How the scoring works, and the other sections. |
| 3 | Decisions | The tab opens Every decision (`decisions/`, same address). |
| 4 | Highlights | New page `highlights/` with 6 slots, each marked **Story coming**. Slots 1–4 name only the candidates Can and Ümit listed: Astra 36/36 rolls, Sol board-only vs with numbers, one good risk, one blunder. Each is marked "not chosen yet". No position is picked, no decision is linked and no story text is written. Slots 5–6 read "No decision chosen yet". |
| 5 | Experiments | New page `experiments/` with three cards:<br>• **Clear risk**: Preliminary / partial; opens `clear-risk/`.<br>• **Nackgammon**: opens the paired test (`./#nackgammon-paired`), the knockout (`leagues/#nack-knockout`) and its matches (`matches/#stage-knockout`).<br>• **Learning from experience**: opens `learning/`. Its status label is read from the state by the same function that sets the learning page's own label (`learning_page.status_label`): Pre-registration / Preliminary · running / Complete. It shows **Pre-registration** now. No results are shown. |
| 6 | About | New page `about/` with six sections, each built from existing text:<br>• **Rules of backgammon**: the Rules part of the current prompt `prompts/bg-v2.md`, quoted unchanged and labelled as such. The Method page does not contain the rules.<br>• **Method**: links to every section of the Method page, by its heading.<br>• **Data**: the Data page's downloads text.<br>• **How to run it**: the Data page's "How to recompute" steps.<br>• **Late entries**: the Leagues page's late-entry text, with a link to it.<br>• **Open questions**: the analysis-status table, with a link to Method: Limits.<br>Then More pages. No new claims. |
| 7 | Other pages reachable; old URLs | **More pages** (Matches, Phases, Compare, Where models disagree, Leagues, Every model setup, Method, Data) is a row on the Leaderboard's first card and a section of About.<br>**Every old path is unchanged.** No page moved, so no redirects are needed. Every page of the live site and of the base is still a page of nav-ct, and every content id on it is still there (`urls.md`). The one id that went is `view-part`, the label of the old Part row in the removed header.<br>Method, Data, Clear risk and Learning sit under the About / Experiments tabs. The other pages sit under Leaderboard. |
| 8 | Phone | The tab row is one line that scrolls sideways, and the marked tab is scrolled into view. The whole header is one sticky block (suite strip, name and tabs). On a phone it is compacted: smaller name and leaf, "More" for More options (its accessible name unchanged), 36 px theme keys. **Heights:** see the table below. |
| #2904 | Details box | Each leaderboard row now shows only: rank · model (maker dot, family icon, its type under the name) · risk judgement bar with whisker · score. Everything else is in the row's **details box**.<br>**Opening and closing:** a tap opens it on a phone; a second tap or a tap outside closes it. On a desktop it opens on hover and on keyboard focus; Tab goes into it and Escape closes it.<br>**Lines,** each filled only from the setup's stored values; a line or part is left out where the data has none (never "n/a"):<br>• setup · maker<br>• Setting · League<br>• Risk judgement x (95%: lo–hi)<br>• Risks found p% · safe right q%<br>• Took n of N risks that paid · played safe in m of M positions where safe paid<br>• Error rate (95%) · record W–D–L · late entry<br>• $ per 1,000 (price label) · decisions<br>• Released month<br>• Open its decisions → · Model page<br>The box fits the window's width (at most 380 px, 8 px margins). Without JavaScript every box is shown in its row.<br>**Change from #2745, as Main instructed:** setting, league, risks found, right safety, PR, $ and decisions are no longer columns. They are in the box. The full multi-column numbers stay on the page under All setups (risk columns) and Every number (every column, All columns key); the rule under the table links Every number. The "N other settings" expander is kept. |
| #2907 | Type filter | **All · Chat models · Decision models** above the table, default All. It belongs to this table only; the page's filters still never change it. Programs stay as grey reference rows in every view. The type is shown under each name ("chat model" / "decision model"; for programs, their reference label).<br>**Ranks:** each row keeps its overall rank. A legend says "# is the rank among all models, in every view". |

## Results

| Check | Result |
|---|---|
| checks.run (both renders) | 0 failures, exit 0 |
| Numbers vs live (label-aware) | 0 differences. 17,377 home-table cells; 111 other pages' main content; 105 data files; 398 measure-chart values; 58 finding values |
| Numbers vs the leaderboard-ct render | 0 differences. The same sets, plus 32 Too safe values |
| Leaderboard bar scores vs the live All leagues Risk table | 54 rows, 0 differences |
| Details boxes vs the data files | 445 lines, 0 differences |
| Details boxes vs the live tables | 208 values, 0 differences |
| Old URLs and anchors (`urls.md`) | 328/328 ok. 112 pages × every content id, static; the old navigation links and deep links, in a browser at 1280 and 390 |
| Browser (`browser.md`) | 118/118 ok, at 1280 and 390, light and dark. Covers: the header on 15 pages, active underline, sticky header, sideways tab scroll, the filter (3 states, expanders, no row lost), the box on all 34 rows + 20 other-setting rows, tap outside, keyboard, and Open its decisions |
| Phone sweep (`phone-checks.txt`; MobileFix's sweep.py) | 113 pages at 390 px: 0 pages wider than the window (base: 1, the home page, 46 px), 0 worse |
| First screen at #leaderboard (390 × 844) | 4 ranked rows with all four parts in view, no overflow. Base: 0 rows |
| Screenshots | 48 in `review/screenshots/`, at 1280 and 390, light and dark: every tab's page, Method, sticky while scrolled, the tab row at its start and end, the table, desktop hover, phone tap, and the Chat / Decision filter |

Header height (sticky: suite strip, name and tabs), light theme:

| Width | Height |
|---:|---:|
| 1280 | 92 px |
| 390 | 98 px |

The old header was 63 px at 1280 and 83 px at 390, but the old pages row and title strip scrolled away underneath it.

## Conflicts

**With leaderboard-ct.** None in the code: nav-ct is leaderboard-ct plus this change. What this branch changes in leaderboard-ct's design:
- The table's columns (#2904, as above).
- Released and the dated-checkpoint note moved into the box.
- The note under the table now says Released is "left out" where there is no maker statement, where the table used to show a dash.
- The swipe hint above the three-column table is gone.
- The phone CSS no longer makes the model a sticky column, because the three columns fit 390 px.

**With the mobile fix (origin/main ff652d8).** The rebase conflicted in `story.py`, `bg.js` and `bg.css`. Main's mobile fix restyles main's own 8-column headline table, which leaderboard-ct replaces:
- **Taken from leaderboard-ct / nav-ct:** `story.py` and `bg.js` whole, and the headline block of `bg.css`. Main's "+N" link to All setups, its head-long/head-short headers and its flex-row phone layout of the headline are dropped, because they style columns that no longer exist.
- **Kept from main:** the phone rules for the charts' bars in two lines, and the filter row's part links scrolling inside the row (this also fixes a 436 px page width at 390 px, which the base render still has). In the same block, main drops the base's `.hbar-where { display: block }`, and the rebase follows main.
- `git diff` of the tree before and after the rebase is exactly that bg.css hunk.

## Open questions for Ümit

1. **Highlights:** slots 1–4 show the candidates exactly as listed ("Astra 36/36 rolls", "Sol board-only vs with numbers", "one good risk", "one blunder"). Should these labels show publicly before the stories exist, or should every slot read only "Story coming"? How many slots: 6 now; 8 is a one-line change (`pages.HIGHLIGHT_SLOTS`).
2. **About, Rules:** the rules are quoted from the prompt, so they are addressed to a player ("your home board"). Keep the quotation as is?
3. **About, Open questions:** this section is the analysis-status table plus a link to Method: Limits. Is that what you meant, or is there a list of open questions to put there?
4. **Which tab marks which page:** Method and Data → About; Clear risk and Learning → Experiments; Matches, Leagues, Phases, Compare, Where models disagree and model pages → Leaderboard.

## Files

- `scripts/`: `run_render.sh`, `render_site.py`, `review.py`.
- `checks-run.txt`.
- `review/`: `numbers.md`/`.csv`, `urls.md`/`.csv`, `browser.md`/`.csv`, `header-heights.md`, `page-diffs.md`, `source.patch` (`git diff a99a1ce nav-ct -- tools/site`: this change and the kept bg.css hunk of the mobile fix), `screenshots/`.
