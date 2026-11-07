# leaderboard-ct: the leaderboard as Ümit specified it (bus #2745)

Branch `leaderboard-ct`, HEAD 5ca56de, on origin/main a25b75e. That base already has CostLabels' cost-label fix: cost labels are looked up through `pages.origin_meta`. This is a **candidate**. It is not merged and not deployed.

## What ran

`scripts/run_render.sh` renders the whole site twice from one copy of the live state (results 7b40b30e): once with origin/main's `tools/site` and once with the branch's. Both renders go through `scripts/render_site.py` (the same file as in mailbox/front-story).

- render_site.py calls `build.compute()` and then the page writers. `build.compute()` reads every published aggregate and runs the site's own offline computations, including the bootstrap loops in `offline.py`. So the render is **not statistics-free**.
- What did not run: `build.py main`, `update.sh`, deploy, model calls, scorers and rescoring.
- `checks.run` gives **0 failures on both renders** (`checks-run.txt`).

Then:
- `scripts/evidence.py` re-derives the per-model choice from the branch render's data files. It does this independently of story.py and checks the result against the rendered table: 7 PASS, 0 FAIL (`evidence/checks.txt`).
- `scripts/review.py` compares numbers and links, runs the browser tests and takes the screenshots.

## What changed (tools/site)

| # | Ümit's item | Done |
|---|---|---|
| 1 | One row per model, at a fixed rule | **Rule:** each model's row is its highest reasoning setting played, never its best score. The effort sent is ordered none = off < minimal < low < medium < high < xhigh < max. `on` is used for a model with no levels and ranks above off; a model with both `on` and a level fails the build. A decision model has its single setup.<br>**Version names** are separate models.<br>**Dated checkpoints:** a dated checkpoint (`<model> MMDD`, where the base name is a model in the standings) shares its original's row. That row is named and release-dated by the original, and at the top setting the original's setup is taken.<br>**Ties:** two setups at the same top setting go to `home.best_per_model`'s rule (highest stored judgement; on an exact tie, first in league order). best_per_model gained a `group` argument for this; it is called, not copied.<br>**Result:** 31 rows. Main's table had 32, because it counted DeepSeek V4.1 Flash 1017 as its own model. Two rows changed setup compared with the best-score rule: GPT-6 Astra (low → **medium**) and GPT-6.1 Sol (low → **high**). See `evidence/1-setting-choice.md`. |
| 2 | Columns | # · Model (maker dot, family icon, name; under it: Released month, model page, expander) · Setting · League · Risk judgement (bar to the score, the 95% interval as a whisker, the 50 mark, the number) · Risks found n/N · Right safety n/N · Error rate · $ per 1,000 with its price label · Decisions. Sorting is off in this table (`data-nosort`), so the other-setting rows stay under their row. |
| 3 | Note under the table | "Bars run to each score; the whisker is its 95% interval. Ranks show observed scores; small gaps need not be meaningful. Leagues played different positions." **Flag:** the overlap sentence from #2745 is replaced by Zeki's accepted sentence (#2578), because overlap is not a difference test. The page has no "not reliably ordered" text (checked). |
| 4 | Tap a model → its decisions | The name opens Every decision filtered to that setup: `decisions/?d=<league>&s=<slug>`. The **model page** link is kept beside it, and the Decisions count links to the same view. Each row has an "N other settings" expander. It shows the model's remaining setups as rows with the same columns, including the checkpoint's setups under DeepSeek V4.1 Flash. Without JavaScript those rows are always shown. |
| 5 | Programs | GNUbg weak, Safest and Random: grey, unranked rows (–) under the heading "Programs: reference rows, never ranked". Each row is the program's played League 1 setup (the best_per_model rule over the played setups). An expander lists the program's other leagues, including the computed Random and Safest rows. |
| 6 | "Too safe" chart | Under the table. Each table row gets two bars: right safety (solid) and risks found (hatched), in the maker's colour. GNUbg weak is the grey reference pair. The bars are horizontal so that 31 pairs read at 390 px. |
| 7 | Maker colours | One file, `content/maker_colors.json` (Main #2749). It holds the 7 given colours, every other maker in grey `#8f9399`, and every setup → maker. Each grey maker records the sibling site's family colour beside it, so switching is a one-file edit. Gemma (and Cygnet) are Google; LFM2.5 is Liquid AI. **Every chart** now takes its colour from this file: the 4 measure charts, both finding charts and Too safe. `families.json` keeps icons only. The chart legends now list makers. A setup without a maker fails the build. See `evidence/2-maker-colours.md`. |
| + | Late entries | Behind `story.LATE_ROWS = False`. When set to True they form a separate grey group, "Late entries (not ranked)", under the programs. They use the same rule over their own setups and are never ranked. Preview screenshots: `review/screenshots/leaderboard-late-on-*.png`. |

Other changes:
- The "One row per model / All setups" keys stay; the All setups panel is the unchanged All leagues risk table.
- The Released month moved into the model cell. Its column is not in Ümit's list, and the links are kept.
- The Nackgammon per-model note said its rule is "the leaderboard's rule", which is no longer true. That claim is removed, and the Nackgammon rule itself is unchanged.

## Results

`review/numbers.md`: the branch render was compared with the live mirror (data as of 19:35Z, results 7b40b30e) and with origin/main's render.

| Compared | Values | Differences |
|---|---:|---:|
| Every live home-page table cell, the All setups panel included (vs live, and separately vs origin/main) | 17,377 | 0 / 0 |
| Leaderboard: every cell of every row, including other-setting and program rows | 432 | 0 |
| Too safe values against the live Risk table | 32 | 0 |
| Finding values against clear-risk.json | 58 | 0 |
| Measure-chart values, live against branch | 398 | 0 |
| Other pages, main content byte for byte | 111 | 0 |
| Data files, byte for byte | 105 | 0 |

- **Leaderboard cell sources:** judgement, found and right safety come from the live All leagues Risk table; error rate is compared on every number; cost is compared as the whole cell **with its price label**; decisions are checked against the live Cost tab and Every decision's index; setting against setups.json.
- **Links** (`review/links.md`, 3,604 checks, no broken or lost link):
  - Every live home link is still on the branch page, except the 3 `share/risk-card-*.png` previews. build.py main makes those, so they are absent from origin/main's render too.
  - 867 decision links point to a dataset and setup that are in Every decision's index.
  - 68 taps (34 rows × 1280/390) open Every decision with that setup and show decision cards. These used routed http, because Every decision fetches JSON and file:// cannot.
  - 206 addresses behave the same on live and branch.
  - 823 are unresolved statically in both, as before.
- **Browser** (`review/browser.md`, 44/44 ok): from file:// at 1280 and 390, light and dark.
  - Under 9 filter states (address and clicked keys), all 34 rows stay shown and all 20 other-setting rows stay hidden.
  - Each of the 15 expanders opens exactly its own rows and closes them again.
  - All setups and back keeps an open expander.
  - No script errors.
- **Screenshots** (`review/screenshots/`, 44):
  - Leaderboard top, table, an expanded row, programs, and the chat filter.
  - Too safe, Risk judgement, Error rate and both finding charts.
  - The late-entries preview.
  - Each at 1280 and 390, light and dark.
- `review/source.patch` = `git diff origin/main...leaderboard-ct -- tools/site`.

## Open questions for Ümit

1. **Late entries:** should they appear in the table? The default is no, and the constant is ready. If they counted for the rule, GPT-6 Astra's highest setting would be **high** (a late entry) instead of medium. See `evidence/3-late-entries-question.md`.
2. **The note:** your overlap sentence was replaced by Zeki's accepted rank sentence (#2578). Please confirm.
3. **Other makers' colours:** grey on every site, or the sibling site's family colours? Each sibling colour is recorded in the file, so the switch is one edit. These makers are grey now: Perplexity, SubQ, TypeSafe (Jev, named from its API), Celeris, Inception, Fastino, Z.ai, Alibaba (Qwen), Base Labs, Nace.AI, REAX Labs, and "maker not recorded" (Clef, Open-Jev 27B v1.1, Winnow-12B). Two of these are judgement calls: Cygnet counts as **Google**, because it is gemma-4-12B-it unchanged behind our server, and Winnow is not counted as Google. This also turns Qwen, GLM, Fastino, Jev and the others grey on the existing charts.
4. **Nackgammon "one setting per model"** still uses the best-score rule. Should it switch to the highest-setting rule?
5. **Too safe layout:** the bars are horizontal pairs, one per model, rather than vertical columns, so they read on phones. Is that acceptable?
6. **Table width:** the table is wider than the 1280 card and scrolls sideways (live: 1,366 px; branch: 1,252 px in a 1,056 px card).

## Files

- `scripts/`: `run_render.sh`, `render_site.py`, `evidence.py`, `review.py`.
- `checks-run.txt`.
- `evidence/`: 1–3 and `checks.txt`.
- `review/`: numbers, links, browser, page-diffs, source.patch, screenshots.
