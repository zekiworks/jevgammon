# front-story review packet 2: the fix package for Zeki #2714 and #2718

Branch `front-story` HEAD (see `git -C ~/code/jevgammon-front log -1`) is rebased onto `origin/main` 76b39de, which adds the Nackgammon late entries. This is a candidate: it is not merged and not deployed.

## What ran

`scripts/run_render.sh` renders the whole site twice from one copy of the live state (results f45081f6): once with origin/main's `tools/site` and once with the branch's. It does this through `scripts/render_site.py` (render_site.py), which calls `build.compute()` and the page writers, followed by `checks.run`. `build.compute()` reads every published aggregate and runs the site's own offline computations, including the bootstrap loops in `offline.py`. So the render is not statistics-free.

What did not run: `build.py main`, `update.sh`, deploy, any model call, any scorer or rescoring, and any Nackgammon recomputation. `nack_paired_verify --saved-only` checks against the frozen results files only.

`checks.run` gives 0 failures on both renders (`../checks-run.txt`).

## The corrections

| # | Finding | Fix | Test |
|---|---|---|---|
| 1 | Headline cost lost its price basis | `story.py` prints the setup's price label (same `price.label` as `pages.cost_cell`) next to the number. The label stays when the unit switches to per 1M, because the switch only rewrites `.cost-1m`. Unpriced cells use `pages.cost_cell` ("Priced for N%" / "Not measured"). | `numbers.md` row 2: each headline cost cell is compared as **whole text with the label** against the live cell, after removing the `$` and the per-1M copy. The other columns are compared on every number in the cell, not a prefix. 160 cells, 0 differences. Example: Astra `49.737 API-equivalent (subscription)` = live. |
| 2 | Nackgammon showed every setting per model | The summary has two keys: **One setting per model** (default) and **All settings**. The rule, stated under the table: a model with several settings shows its setting with the highest stored All-leagues risk judgement. This is the leaderboard's rule, chosen from league play and never from this test. The detail tables, chart, primary comparisons with and without the additions, and the yardsticks stay complete. | `links.md` "nackgammon keys" (14 states at 1280 and 390, all OK): expected rows come from `setups.json` (`model`, `model_type`), not from the page. Chat with one setting per model gives 13 models, with no Sol or LFM pair; Chat with all settings gives 15. |
| 3 | Terra missing from Chat | `content/nack_setup_types.json` gives GPT-6.1 Terra's type (chat model) and model. Source: the §10 roster `openai/gpt-6.1-terra, effort low`, plus the route in `tools/v3/effort_sweep_score.py`. The build raises an error if any Nackgammon setup has no type. The note under the table explains that the group is the paired test's original league group and the type is the model type, so Cygnet is Chat while its group reads decision models. | Terra is shown under Chat (`links.csv`, `filter-scope.csv`). |
| 4 | Mercury's month came from a portfolio mention | All 32 entries were re-audited against maker pages; quotes were checked verbatim (`../evidence/release-audit.json`). Mercury Decide now shows —. GPT-6 Astra is now sourced to OpenAI's release index, which lists Astra's own launch post at Sep 3, 2026; the related-posts card is no longer used. DeepSeek V4.1 Flash 1017 now uses a quote that names the model. Qwen3.8 Flash and SubQ Snap Preview stay —, because the maker pages do not name those exact models. The rule is written in `release_months.json` and under the table: the maker's own dated release or public-availability statement for that exact model. | `../evidence/4-headline-selection-and-release-months.md` lists every month with its URL and quote. Its selection table now comes from the rendered headline table itself (32 rows, the production selection), not a separate resolver. |
| 5 | Headline only partly filtered | The leaderboard is a **fixed global table**. It now sits above the filter row, with a stated scope ("all leagues, all phases, every model; the filter row below does not change it") and the tie rule (first in league order). `bg.js` leaves out `#leaderboard`. | `filter-scope.md`: with global type set to program, decision or chat, all 32 headline rows stay shown and the All setups panel hides none, while Every number's rows follow the filter. |
| 6 | Global filters blanked the Nackgammon chart | `bg.js` exempts `#nackgammon-paired` from the global filters, so the section has one state: its own keys. Those keys govern only the summary table. The chart points and every detail-table row are always shown, and so are the yardsticks. | `filter-scope.md`: 34 checks, all OK, opened from **file://** at 1280 and 390 px. Each global type (all, program, decision, chat) is combined with Nackgammon keys (all/chat/decision × one setting/all settings). In every case the chart keeps every point, no detail row is hidden, the summary rows match the local keys, and the Unclear / additions note is visible. No script errors. |
| 7 | "dropped" vs the data's "worse" | The data value `worse` is displayed as **dropped**; the data is unchanged. A legend under each label table gives the Method §10 rule (c): "dropped = the data file's label 'worse': the interval lies above 0 (lower end > 0) and the setup is not kept". The sensitivity rule's "the pair is left out" wording is untouched. `nack_paired_verify` checks each label cell against the shown word. | Base Labs Elephant-1 (late entry) shows "dropped". `nack_paired_verify --saved-only` checks every Nackgammon cell, including the late table, and finds no Nackgammon mismatch. Its 111 remaining lines are the existing `private string 'decision-models'` hits (110 on main; +1 on learning/, which was already on main). |
| + | Late entries (Main, after #2656) | A separate **Late entries / exploratory** block. `data/v3/nack-paired-late.json` is published read-only by `nack_paired_publish.py --late` from `positions/nack-paired/results-late-2026-11-07/results.json`; the 28 Oct data file is unchanged (byte-identical republish). The block has its own note: "Added after the results were known; exploratory; not in any group comparison (§10.14(i))", separate from the "4 setups added" note. Its table has standard PR, Nackgammon PR, change, 97.5% interval and label, with Random as the grey row. The SubQ Snap 1.1 row notes that its answers equal SubQ Snap Preview's answers of 27 Oct on all 1,000 positions; that note is taken from the run's report, not the data file. A line says "REAX 1.3: not run (pending approval)". | `nack_paired_verify`: the site late file equals the content file, which equals `build_late(results-late)`. The late table is checked cell by cell and in row order. The values match the report's table. |

## Numbers and links

- **Numbers** (`numbers.md`): the branch render against the live mirror.

| Compared | Values | Differences |
|---|---:|---:|
| Every live home-page table cell | 16,085 | 0 |
| Headline cells, cost labels included | 160 | 0 |
| Finding values and the numbers in their sentences | 70 | 0 |
| Other pages | 111 | 1 |
| Data files | 104 | 0 |

  - The one page difference is the Data page listing the new `nack-paired-late.json` (`page-diffs.md`).
  - The new late data file is not on live yet; it is counted as new, not as a difference.
  - Other pages and data files are compared byte for byte (main content; the render time stamp is normalised). The per-file comparison lives in `numbers.csv` only for files that differ.
- **Links** (`links.md`): no new errors among the checked links.
  - 1,752 OK.
  - 192 addresses behave the same on live and branch.
  - 823 are unresolved statically in both live and branch (decision anchors made by the Every decision page's script, and paths into the sibling site).
  - 25 external links were not fetched.
  - So this is not a verification of every link.
- **Screenshots** (`screenshots/`, 68): 1280 and 390 px, light and dark, of the changed views.
  - Leaderboard, with its scope note and labelled costs.
  - Nackgammon at five key states, each as a viewport shot and a table shot.
  - Home top, findings, and the full page.
- **Patches**:
  - `source.patch` = `git diff origin/main...front-story -- tools/site`.
  - `delta-vs-5dd69fd.patch` = `git diff 5dd69fd HEAD -- tools/site`. It also includes main's 4476155 (late-entry SubQ wording), which came in through the rebase.
