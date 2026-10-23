# Part B website: v12 delivery

Oct 23, 2026 · Part B of `mailbox/backgammon-site-brief.md` (brief v12). It replaces the v6 delivery and its follow-ups.

**Preview:** https://zekiworks.github.io/analysis/backgammon-preview/
- Deployed by the update loop: results `ce40d3b0`, data as of 23 Oct 15:50 UTC. Analysis repo commit `aea8d61b`.
- Code: jevgammon `21dca52` (`tools/site/`). The risk thresholds were committed before any v10–v12 number was computed: `1b689bc` and `e032ba0`.
- The live page `/analysis/backgammon/` was not touched. The live URL was not switched: that needs Ümit's approval.
- The update timer (`bg-site-preview.timer`) was stopped while I worked, so no half-built state could deploy. It is running again.

**Design (B3, v11 first rule).** The preview keeps its approved look. I made no restyle and no re-layout: `site.css` is unchanged, and the existing components are reused. The only CSS added (in `bg.css`) is for elements the preview did not have yet:
- the risk map;
- the stacked bars;
- the risk call card;
- the champions row;
- the phase heatmap.

These new elements use the preview's own colour variables. I also removed the dead 2×2-wall CSS.

## v6 → v12: what changed in the brief, and what was done

| Changed requirement (v10 / v11 / v12) | Done |
| --- | --- |
| **B3** v10 said "look exactly like decision-models". v11 replaced that with "keep the current preview look; decision-models is the reference only for new elements". The design note is gone. Less text: intro ≤3 sentences, findings, one-line captions, footnote marks; no "About this table" and no thread headings on the home page. 8 screenshots. | The look is kept. The home page has no about-blocks, thread labels or prose sections any more. The screenshots are listed below. |
| **B3** Board: engine's best play as arrows, **best safe play dashed**. | The hero, the social preview and the risk call card show it this way. Before, the dashed line was the model's play. |
| **B4.0** Nav: Every decision · Where models disagree · Phases · Compare · Leagues · Method · Data. Model pages open from table rows. New models is linked from Data. | Done. "Models" and "New models" left the nav. Data links both. |
| **B4.1** Hero: title; intro ending "Every decision is public."; stats strip; results line "…; scored by GNU Backgammon 1.08, 2-ply."; typical Risk pays board (stake 0.05–0.15) whose callout explains one model's risk call; no hero buttons; champions row "League winners · match results". | Done. **Hero rule** (`thresholds.hero_stake_range`, `build.showcase`): take the most recent finished league's model Risk pays decisions with a stake of 0.05–0.15; pick the one whose stake is closest to the pool's median. The result is League 3, Gemini 4 Argon (off), dice 3-4, stake 0.088, a missed risk (pool 1,511). **Winners** come from the final standings: L1 Liquid d1-ultra, L2 GPT-6.1 Sol (low), L3 GPT-6 Astra (on). Each links to its model page. Every page's version line now names GNUbg 1.08, 2-ply. |
| **B4.2** Findings in decision-models form. The lead-in is itself a checked, approved finding (v11). Until approval: "Findings will be published after review." | The waiting line is shown. `content/findings.json` now has `lead_in` (null) plus `findings` (empty). `findings.py` adds the check types `higher_judgement` (unpaired, intervals don't overlap) and `no_leader` (for "None led on every measure": the leaders differ between measures). Every deploy reruns all checks, the lead-in's included. The draft (`workspace/findings-draft.md`) now covers, per league and at both margins: the best risk judgement with its interval, the setups with no clear difference from it, and the risk-call pattern. |
| **B4.3** Filters: League (1 · 2 · 3 · Shared positions), Model type (All · Decision · Chat · Program), Phase, Reasoning, Runs on, Weights; the setup counter; Reset with "Nothing to reset: the filters show the defaults."; default League 1; one league at a time; Shared positions shows its status. | Done. The default is now **League 1** (it was League 3). **Phase** loads that phase's Risk tables, Quality table and Risk charts from `fragments/<league>-<phase>.html`, so the page stays small. Tabs that don't change with phase (Confidence, Reasoning, Cost, Stability) say so. |
| **B4.4** Leaderboard: tabs **Risk** · Quality · Confidence · Reasoning · Cost · Stability, Risk first; one table; model cell with one settings line; value with its 95% interval under it; one caption plus footnote marks (§ · † · Not measured); limit lines under the table. | Done. The limit lines appear under the Risk table: "Hit risk only: …" and, from v12, "Setups met different positions; risk judgement is not adjusted for how hard they were. Paired comparisons wait for the shared positions." Under every tab: "Setups played different positions; league comparisons are not paired." **Confidence tab** (new): confidence source; decisions kept, blunders among kept and mean equity lost among kept, at 0.90 and at 0.99; error rate in the surest quarter; AUROC for the best play and for warning before a blunder; ECE (best-play event only); confident and badly wrong. N/A for setups without probabilities. |
| **B4.5** Chart panels with small tabs, Download PNG, "Show all": Risk (risk map · error split · stake chart), "Error rate, time and cost" (3 tabs), Trade-off (cost · time). | Done. Charts are server-side SVG and follow the filters. Without "Show all" they show the first 8 model setups plus the reference rows. The Risk panel has margin keys (0.001 / 0.02). **PNG download**: the chart in the current theme. In small type it adds the league, the margin, the decisions behind the visible rows, the active filters, the results version and the site URL. |
| **B4.6** "Risk pays vs safety pays": one sentence per league, then one chart. | Done: risks found against right safety, per setup. The sentences give the range across model setups. |
| **B4.7** Downloads line "Download: results.json · decisions.json". Everything else moves off the home page. | Done. What the input adds (Earlier version), learning from experience (Not measured), routing and teams (Analysis pending) and tail risk are now Method sections `#input`, `#learning`, `#routing`, `#tail`. |
| **B5** Every decision: position class, stake, risk call; all three filterable (v12 example: missed risk with a big stake, or a needless risk that lost a lot of equity); best safe play next to the chosen play. | Done. The filters are Position class, Risk call and "Stake, or equity lost by a needless risk" (small / medium / big). Each card shows the best safe play, the stake band and the call at 0.02 when it differs. Example: `decisions/?d=league-3&s=gpt-6-astra-on&r=risk&c=mr&b=b` → 71 decisions. |
| **B6.1** Definitions: stake; position classes; the five risk calls. | `analysis.play_call` and `risk_class`. Every trade-off decision gets exactly one call. The pre-deploy check ties them to the counts. |
| **B6.2** Risk tab columns, in order: risk judgement (interval, games resampled); risks found and right safety next to it with counts; good, missed, needless and wrong risks; error rate by risk-call category (**six parts**, each 500 × equity lost in that category ÷ all scored decisions, summing exactly to PR; v11/v12); trade-off counts per class. "N/A: no <class> decisions" when a class is empty (v11). | Done. The pre-deploy check fails if the six parts don't sum to the error rate (1e-9) or if the call counts don't sum to the trade-off decisions. |
| **B6.3** Stake bands for Risk pays only (risks found, missed, wrong; "big risks found"). Needless risks banded by equity lost ("big needless risks"). Risk size. Risk judgement per phase (heatmap). Confidence on the call: AUROC for right risk plus mean confidence on missed risks, **no calibration gap**, with the reason stated under the metric (v11). | Done: Risk-tab columns, the stake chart, and the Phases page heatmap. The reason line is under the Risk table and in Method. |
| **B6.4** Reference rows: Safest, Random, GNUbg weak, with its label. Never ranked, never champions. | GNUbg weak is in every league. Safest and Random played only League 1, so for Leagues 2 and 3 they are **computed on that league's positions**: Safest = the best safe play; Random = the expectation over all legal plays, so its counts have decimals. This is labelled and explained in Method. Computed Safest = 50.0 in both leagues; computed Random = 27.1 (L2) and 27.2 (L3). |
| **B6.5** Risk map (v11): x = (missed + wrong) ÷ Risk pays, y = needless ÷ Safety pays; faint diagonals at 50–90; colour = wrong ÷ (missed + wrong); reference points. Error split (six parts). Risk call card per setup. Stake chart. PNG rules. | Done. A risk call card PNG (1200×675) is made for each **league winner** (`share/risk-card-league-N-*.png`, linked under the Risk panel). Every model page has the card in HTML. |
| **B6.6** Every risk metric at 0.001 and at 0.02, shown on the Risk tab and in Method. | Done. On the Risk tab, a robustness table sits directly under the main one. Method `#risk-robust` has both margins side by side, per league. The charts have the margin key. |
| **B6.7** Missing 2-ply plays evaluated on CPU. Thresholds fixed before computing. | All 81,386 league decisions have every legal play at 2-ply, so no CPU evaluation was needed. Method states this, computed at build time. New thresholds were committed first: `risk_margin` 0.001, `risk_margin_robust` 0.02, `stake_bands` and `needless_loss_bands` 0.02/0.08, `confidence_cutoffs` 0.90/0.99, `cutoff_split_runs` 300 with its rule, `surest_share` 0.25, `risk_map_diagonals`, `hero_stake_range`. I removed `safety_pays_loss_below`; `risk_margin` replaces it. |
| **B7** Publishing rule on pages and JSON downloads; the pre-deploy scan blocks. | The scan (`common.BANNED`) covers every published file, including the gzip decision files and the new fragments. It caught one comment of mine in `bg.css` during the build, which I fixed. |
| **B9** Unpaired league wording; fixed risk thresholds. | Unchanged wording: "no clear difference in league play" / "lower/higher error rate in league play". The risk thresholds are fixed as listed above. |
| **B13.2** Every B6 metric for all three finished leagues, both margins, risk map, error split, one card per league champion, 8 screenshots. | Done; see below. |
| **Part A** limits ($50 cap, stop at $40, ≤2 transport retries, 600 s timeout). | Unchanged since v6. Nothing new was run (see Part A below). |

## Verification (exercised)

**Build and checks.** Full build plus pre-deploy checks passed, locally and in the loop. The checks cover:
- numbers trace to data files, the fragments included;
- counts, including the new B6 sums;
- mixing;
- links and anchors;
- the B7 scan;
- findings.

`selftest_mixing.py` passes: 0 failures on the clean build, and on the deliberately mixed build all four mixing kinds are caught, the new chart case included.

**Headless Chromium on the deployed preview** (1280 and 390 px, dark and light): 64 page loads, 0 console errors, 0 elements wider than the screen. The pages:
- home, `?tab=quality`, `?tab=confidence`, `?league=league-2`, `?league=league-3&tab=reasoning`;
- Leagues, Phases, Compare, Where models disagree, Method, Data, New models, Models;
- a model page;
- two filtered Every decision views.

**Home page behaviour checked:**
- it opens on League 1, Risk tab, "19 of 19 setups";
- the Phase filter set to Race swaps in the Race tables;
- Model type = Decision gives "15 of 19 setups" (model setups plus the reference rows);
- the Risk chart's PNG download works.

## B13 list

1. **Snapshot, build script, update loop with pre-deploy checks.**
   - Runs every 15 minutes and reports its own failures (as in v6).
   - The checks now also cover the B6 sums, the fragments and the lead-in finding.
   - The 23 Oct 15:50 run (forced, because the code changed) deployed `ce40d3b0`.
2. **Home page in the v12 order, Risk tab first.**
   - Every B6 metric is computed for Leagues 1–3 (all Finished, Published), at 0.001 and at 0.02.
   - Risk map, error split and stake chart for each league.
   - One risk call card per league winner. Risk judgement of the winners, 0.001 / 0.02 margin:

     | League | Winner | 0.001 | 0.02 |
     | --- | --- | --- | --- |
     | L1 | Liquid d1-ultra | 62.1 | 62.0 |
     | L2 | GPT-6.1 Sol (low) | 71.4 | 73.7 |
     | L3 | GPT-6 Astra (on) | 73.9 | 74.6 |

   - These are descriptive only, not findings.
   - The screenshots are in `mailbox/v12-screenshots/` (see "Screenshots" below).
3. **Every decision and Method.**
   - Every decision: all 81,386 league decisions plus the v1 set, each with position class, stake, risk call (both margins) and best safe play. All three marks can be filtered.
   - Method:
     - B6.1–B6.7 in full, with the 0.02 tables per league and the held-out cutoff table (300 game splits);
     - the Confidence definitions;
     - What the input adds, Learning from experience, Routing and teams, Tail risk;
     - limits, thresholds and statistics.
4. **Every other section in place, with its status:**
   - Shared positions (filter view, every tab, every chart panel): Analysis pending.
   - Stability: Not measured (league games never repeat a position).
   - Routing and teams: Analysis pending (Method).
   - Learning from experience: Not measured (Method).
   - What the input adds: Earlier version (v1 history), v3 ablation Analysis pending.
   - Compare and Where models disagree: v1 set (Earlier version), shared positions Analysis pending.
   - New models: smoke test.
5. **Analyses → status → data file → waits for the leagues?**
   - All three leagues have finished, so **nothing waits for a running league**. What still waits is the shared-position answers.
   - The full table is on the Data page (`#status`), from `tools/site/content/analysis_status.json`.

   | Analysis | League decisions | Shared positions | v1 set | Data file |
   | --- | --- | --- | --- | --- |
   | A1 decision quality | Published (L1–3) | Analysis pending | Earlier version | `data/v3/league-N.json` |
   | A2 what the input adds | — | Analysis pending (ablation answers) | Earlier version | archive `v1-why.html` |
   | A3 reasoning (paired) | Unpaired "in league play" readings | Analysis pending | Earlier version | `data/v3/league-N.json` (reasoning), `data/v1/compare.json` |
   | A4 where models fail | Published | Analysis pending | Earlier version | `data/v3/league-N/<setup>.json` |
   | A5 confidence | **Published** (Confidence tab, held-out cutoff) | Analysis pending | Earlier version | `data/v3/league-N.json` (confidence) |
   | A6 routing | — | Analysis pending | — | none yet |
   | A7 teams | — | Analysis pending | Earlier version | archive |
   | A8 repeatability | Not measured | Analysis pending | — | none yet |
   | A9 time and cost | Published | Analysis pending | Earlier version | `data/v3/league-N.json` |
   | A10 standings and risk calls in play | Published | — | — | `data/v3/league-N.json` |
   | A11 cube | Not measured | | | |
   | A12 opening knowledge / Nackgammon | — | Analysis pending | — | `data/v3/shared.json` (sizes) |
   | A13 shared score vs league results | — | Analysis pending (shared answers) | — | none yet |
   | High 1–5 (fixed and broken, tail, confident and badly wrong, time budget, switching rule) | Published where league data allows (High 2–4) | Analysis pending | Earlier version (High 1–3) | as before |
   | **B6 risk metrics** (both margins, charts, cards, Every decision marks) | **Published** (L1–3) | Analysis pending | Earlier version | `data/v3/league-N.json` (`risk.main`, `risk.robust`, `references`), `data/v3/league-N/<setup>.json` (`risk.*.phases`), `decisions/<league>/<setup>/risk.json.gz` |
   | Learning from experience | Not measured | | | |

6. **Setups with missing B7 metadata** (from `content/setups.json`; each model page lists its own):

   | Dataset | Missing | Setups |
   | --- | --- | --- |
   | League 1 | price | Fastino GLiDE, Fastino GLiDE v1.2 (local) |
   | League 1 | price date | Decider v1.1 27B, SubQ Snap Preview |
   | League 1 | sampling | Cygnet (Gemma 4 12B) |
   | League 1 | weights | SubQ Snap Preview, Liquid d1-ultra, Jev 1.14.0, Jev 1.13.0, Celeris-1 Decision, GPT-6 Luna, Mercury Decide, Fastino GLiDE |
   | League 2 | price date | all 10 priced setups |
   | League 2 | weights | Qwen3.8 Flash (off) |
   | League 3 | price date | all 10 setups |
   | v1 set | date run | all 17 |
   | v1 set | option groups | 13 |
   | v1 set | price date | 5 |
   | v1 set | sampling | Cygnet, Gemma 4 31B, GLM-5.3-Flash NVFP4 |
   | v1 set | reasoning | DeepSeek V4.1 Flash, Qwen3.8 Flash Next, GLM-4.7-Flash, GLM-5.3-Flash NVFP4 |
   | v1 set | weights | Jev 1.13.0, GPT-6 Luna, GLM-5.3-Flash NVFP4 |
   | v1 set | model ID, provider, runs on, price | GLM-5.3-Flash NVFP4 |
   | Smoke tests | — | nothing missing |

7. **Preview URL:** https://zekiworks.github.io/analysis/backgammon-preview/

## Screenshots (`mailbox/v12-screenshots/`)

They were taken from both live URLs after the deploy. Desktop is 1280×1800; phone is 390×2400.

| File | Content |
| --- | --- |
| `side-by-side-desktop-dark.png` | decision-models home (left) and backgammon preview home (right), desktop, dark |
| `side-by-side-desktop-light.png` | the same, desktop, light |
| `side-by-side-phone-dark.png` | the same, phone, dark |
| `side-by-side-phone-light.png` | the same, phone, light |
| `decision-models-desktop-dark.png` and the other 7 single files | the 8 individual screenshots behind the four pairs (2 sites × 2 widths × 2 themes) |

## Part A

- **Nothing new was run.** v10–v12 list no model that hasn't already been smoke-tested. Mistral Large 4: weights not out, so no test, as asked.
- **Claude Fable 5.1 and Grok 4.7** were skipped, as Can asked. Their earlier smoke rows stay, marked "also in League 3".
- **Spend so far** (from `mailbox/Part A smoke tests - results.md`):
  - **$2.03** on OpenRouter;
  - **$0** on subscriptions (API-equivalent $10.48).
  - That is far below the $40 stop and the $50 cap.
- All runs used the 600 s limit, with retries for transport errors only.

## Judgement calls to confirm

- **Computed reference rows in Leagues 2 and 3** (Safest, Random). B6.4 asks for these rows and the risk map needs their points, but the programs played only League 1. They are labelled "computed". If you'd rather show only rows that actually played, they can be dropped.
- **Hero rule:** median stake within 0.05–0.15, latest finished league. If you want a different league (for example League 1, the default view), it's a one-line change.
- **Phase filter scope:** it applies to the Risk and Quality tables and to the Risk chart panel. The other panels and tabs say they cover all phases.
- **Risk map labels** can overlap where many setups sit close together; every point has a tooltip. Reference points are squares.
- **Nav:** "Models" and "New models" left the top bar (B4.0). Both are linked from Data.

## Not done (needs approval or data)

- **Switching the live URL (B2):** needs Ümit's approval.
- **Publishing findings and the lead-in (B4.2):** needs Ümit's approval. The draft is refreshed after each deploy.
- **Shared-position analyses:** wait for those answers.
