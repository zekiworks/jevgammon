# Part B website: v6 delivery

Oct 22, 2026 · Part B of `mailbox/backgammon-site-brief.md` (v6). It replaces the v3-based first delivery.

**Preview:** https://zekiworks.github.io/analysis/backgammon-preview/
- It is not linked from anywhere, and every page carries `noindex`.
- The live page `/analysis/backgammon/` was not touched.
- Deployed by the update loop (results `1042247b`, data as of 22 Oct 14:08 UTC).
- Code: jevgammon `f964514` (`tools/site/`).
- Note: an earlier commit, `1feffa4` ("takeover: SKIP_SMOKE=1…"), also swept up part of this work while it was in progress. The 14:05 loop run deployed that half-state (`aae4be33`). The 14:08 run replaced it with the full v6 build.

## What changed from v3 to v6 (brief diff) and what was done

| v6 requirement | Done |
| --- | --- |
| B0 framing: five threads; every home section and tab belongs to one; leagues, runner history, anchor and hardware go to Leagues or Method; no decision-models mention; English only | The home page runs in this order: **Hero → Findings → Leaderboard → Is the risk worth it? → What the input adds → Confidence → Cost and reasoning → Learning from experience → links**. Each section and tab carries a "Thread N" label. The home league table and the Game phases section are gone (now on Leagues and Phases). "Changes during the leagues" and "About the anchor" moved from Leagues to Method (`#v3-changes`, `#v3-anchor`). The check bans the string "decision-models" in every file. |
| Title, subtitle with N from the build, intro ending "Every decision is public." | Title: "Can a model tell when a risk is worth taking?". Subtitle: "… across 41 model setups." N is computed (league setups, programs left out). Intro: 3 sentences ending "Every decision is public." |
| Downloads from the hero and from Data; Method link | Hero buttons: Results (JSON) (`data/results.json`, new: every league's results per setup, one league per key), Decisions (JSON) (`decisions/index.json`), Every decision, Method. The same downloads are on Data and in every footer. |
| Stats strip: decisions scored · leagues · setups · models; "Results <hash>, updated <date>" | 77,044 decisions scored · 3 leagues · 41 setups · 29 models. Line: "Results 1042247b, updated 22 October 2026, 14:08 UTC." |
| Findings: 4 bullets, one per thread, the first answering the core question. From findings-draft.md after approval, each stored with a machine check; rerun before every deploy; a failure stops the deploy and is reported | Until approval the page shows "Findings will be written when the current leagues finish." plus the four thread questions as links. The store is `tools/site/content/findings.json` (empty). `tools/site/findings.py` holds the check types: `bound`; `lower` (unpaired, intervals don't overlap); `paired` (interval excludes zero). `checks.py` reruns every check before each deploy. A failing finding stops the deploy and is written to `mailbox/Backgammon site - findings to re-check.md`. The draft (`workspace/findings-draft.md`) is now one section per thread. |
| Leaderboard: Table/Charts; league as selector, never merged; "Shared positions" view showing its status; filters league, model type, weights, runs on, reasoning; tabs Quality · Risk · Confidence · Reasoning · Cost · Stability | Done. The selector offers League 1/2/3, Shared positions (Analysis pending) and Earlier version: v1 set. It opens on the latest finished league (League 3), and `?league=` makes a view linkable. Routing moved to Cost and reasoning. |
| Risk 2×2 as second signature, glanceable, works as an image on X | Each setup gets a tile wall: rows Risk pays / Safety pays, columns took a risk / played safe. Each cell shows the share of its row large, with count / row total and mean equity lost under it. Green marks good calls, red costly ones, and the fill grows with the share. The same wall is in Charts. The build also writes a 1200×675 PNG per league (`share/risk-league-N-<hash>.png`), linked under the wall. |
| B6 rewritten: minimum risk, best safe play, one rule, No hit-risk trade-off counted and left out; cells with raw count, share of row, mean; headline numbers with count and denominator; Safest program as reference; empty cell shows 0 and no mean, never "Too few"; limit next to the 2×2 and every risk chart | `analysis.risk_class` implements the one rule. Shares are now per row (they were per total). "Too few" is gone from risk cells and headlines; every share shows n / denominator. Safest is pinned first in League 1 as "reference: never takes a risk". Leagues 2 and 3 link to it. The limit line sits under the wall, the Risk tab, the Charts card and Every decision. Method was rewritten to match. |
| What the input adds (thread 2): v1 prompt history table with error after each step; the computed-consequences finding prominent; Earlier version | Done. The lead finding is "about two thirds: from 120 in league #6 to 38.5 in league #7". Both numbers are parsed from the archived table, not typed. The v3 ablation shows Analysis pending. |
| Confidence (thread 3); Cost and reasoning (thread 4, with routing and teams) | Done, each per league. Confidence holds the tail table and "confident and badly wrong". Cost and reasoning holds the unpaired reasoning table described under B9 below, plus routing and teams (pending). |
| Every decision: Risk pays / Safety pays / No hit-risk trade-off, took a risk; both filterable | Each card has a mark. Two new filters, Decision kind and The model, use per-setup `risk.json.gz` indexes, so no page has to be loaded to filter. A pre-deploy check confirms the marks equal the 2×2 counts. Example: `decisions/?d=league-3&s=gpt-6-astra-on&r=risk&t=safe`. |
| Board as visual signature in hero, social preview, Every decision | A server-side SVG board (`tools/site/board.py`) uses the same geometry as Every decision. The hero shows a real Risk pays decision with the engine's best play drawn as arrows (League 3, Gemini 4 Argon (off) played safe), linked to the decision. The social preview puts the board beside the question and the stats. |
| Accent colour | Felt green/teal (#0f766e light, #2dd4bf dark). Dark/light modes, sortable and clickable tables, and the text-second layout are kept (Can's request). |
| Leagues: notes generated from table data | Each league's Notes list is generated: winner or leader, lowest error rate in league play with the setups not clearly different, each model's reasoning reading, the "not paired" line, and the anchor/runner-changes link. The kept hand-written notes block is removed. |
| New models: minimum-sample rule doesn't apply; Fable/Grok | Rows show count / interval / n. A note says the minimum rule does not apply. Claude Fable 5.1 and Grok 4.7 keep their rows, marked "also in League 3". The Gemini 3.8 Flash Antigravity row is marked "also in League 2". |
| Method: anchor note, runner changes, league comparisons not paired, minimum sample for averages only, shares with count/denominator | Done. The verdict "No clear benefit" now reads: never "the same", "level" or "gains nothing". The archived v1 report's two "level" phrasings were changed to "no clear difference" and "close to". |
| B9 league (unpaired) wording | League reasoning reads "lower/higher error rate in league play" only when the two 95% intervals don't overlap; otherwise "no clear difference in league play". No verdict label. |
| B11 cost label "list-price estimate; runs on our GPUs" | Relabelled for the Deciders (4 entries) and defined in Method → Cost. |
| B7 publishing rule; pre-deploy scan of every published file | The scan in `common.BANNED` now also catches private IP ranges, localhost, URLs with ports, `/root/`, `/mnt/`, key/token/header patterns and the hostnames. It covers every file, including the decompressed decision files. The loop's own weaker grep was removed. |
| Reasoning-setting filter: no "Shuffled" | The Argon replay's `setting` is now null. A `play_order` flag shows in its row ("shuffled play order") and on its model page. |
| B1 loop: every 15 min; survives restarts; reports its own failures | The timer runs at `*:5/15` with `Persistent=true` (the user manager lingers). Any crash, kill or timeout writes `mailbox/Backgammon site preview - update loop failed.md`, through the ERR trap and through `OnFailure=bg-site-preview-failed.service` (`tools/site/report_failure.sh`). The next good run removes it. A failed check is still written to `… - check failed.md` and blocks the deploy. |
| B3 design note before building; licence check before reusing decision-models code | Written first: `mailbox/Backgammon site - design note.md`. The licence check (LicenceCheck) found nothing from decision-bench in decision-models beyond boilerplate (decision-bench is MIT). No new decision-models code was copied. |
| Part A (background) | See the Part A section below. |

## Verification (exercised)

- **Build and checks:** the full build plus pre-deploy checks passed locally and in the loop. The checks cover numbers tracing to data, counts, mixing, links/ids/anchors, the private-data scan, published findings, and B6 marks vs counts.
- **Headless Chromium** (Playwright), at 1280 and 390 px, dark and light, on a local copy of the deployed build:
  - **Pages:** home, home `?league=league-1`, Leagues, New models, Method, Data, Phases, Compare, Where models disagree, Models, Every decision (League 3, League 3 filtered Risk pays × played safe, v1 set).
  - **Results:** 52 page loads. No console errors. No element wider than the screen outside the scrolling tables and nav.
  - **Selector:** exactly one league view shows (League 3 by default, League 1 with `?league=league-1`). 10 and 16 tiles respectively.
  - **Filter:** the filtered Every decision gives 4 pages for 186 decisions, which matches the 2×2 cell 186 / 422.
- **Public URL:** GitHub Pages served `1042247b` about 7 minutes after the push. The same 52-load headless Chromium run against https://zekiworks.github.io/analysis/backgammon-preview/ found 0 console errors and 0 overflow. The selector showed one league view in every width and theme.

## B13 list (v6)

1. **Design note, then snapshot + build script + update loop with its pre-deploy checks.** The design note is in mailbox/. Snapshot, scoring, build and checks are as in the first delivery, plus the findings check and the B7 scan. The loop runs every 15 minutes and reports its own failures.
2. **Home page with hero, leaderboard (league selector), and "Is the risk worth it?".** The risk analysis is computed for League 1 and League 3 (finished, Published) and League 2 (Provisional: league still running, "Stopped (paused; 132 / 136 matches)").
3. **Every decision and Method, filled with the data that exists.**
   - Every decision: 76,836 league decisions plus 17,000 v1-set answers (count as of the first delivery; the counts have not been re-checked since), each with board, prompt, plays, equities, choice, and the new risk mark and filters.
   - Method: v6 B6 definitions, statistics with the league/unpaired rule, cost labels, anchor, runner changes.
4. **Every other section in place, showing its status:**

   | Section | Status |
   | --- | --- |
   | Shared positions view | Analysis pending |
   | What the input adds (v3 ablation) | Analysis pending (v1 history: Earlier version) |
   | Stability | Not measured (leagues) / Analysis pending (shared) |
   | Routing and teams | Analysis pending |
   | Charts | 2×2: per league · other five charts: Analysis pending |
   | Learning from experience | Not measured |
   | Phases, Compare, Where models disagree | per league / Earlier version, as before |
   | New models | Smoke test |

5. **Analyses → status, data file, waits for leagues?** Unchanged from the first delivery except for the rows below. The table is on the Data page and in `tools/site/content/analysis_status.json`.
   - **Is the risk worth it? (B6)**
     - Status: league decisions per league, Published (L1, L3) · Provisional (L2). v1: Earlier version. Shared positions: Analysis pending.
     - Data: `data/v3/league-N.json` (risk, with counts and denominators), `data/results.json`, `decisions/<league>/<setup>/risk.json.gz`.
     - Waits for the running league: the league part does.
   - **A2 What the input adds**
     - v1 history: Earlier version (`content/archive/v1-why.html`).
     - v3 ablation: Analysis pending, no data yet.
     - Waits for the leagues: no.
   - **A3 reasoning**
     - Shared positions: Analysis pending.
     - Per league: unpaired "in league play" readings, in `data/v3/league-N.json` (reasoning).
     - v1: Earlier version.
6. **Setups with missing B7 metadata** (from `content/setups.json`; each model page lists its own):

   | Dataset | Missing | Setups |
   | --- | --- | --- |
   | League 1 | price date | Decider v1.1 27B, SubQ Snap Preview |
   | League 1 | weights | SubQ Snap Preview, Liquid d1-ultra, Jev 1.14.0, Jev 1.13.0, Celeris-1 Decision, GPT-6 Luna, Mercury Decide, Fastino GLiDE |
   | League 1 | price | Fastino GLiDE |
   | League 1 | sampling | Cygnet (Gemma 4 12B) |
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

## Part A (background)

- **Fable 5.1 and Grok 4.7:** skipped, as Can asked. Their already-run smoke rows stay and are marked "also in League 3".
- **d3-turbo and Nemotron 3.5 Bolt (off, on):** ran in the midnight takeover and are on New models.
- **GPU needs:** no v6 item needs a GPU any more, so nothing was posted to compactor. The optional Nemotron BF16 two-GPU alternative failed then and is not required by the brief.
- **API models:** v6 adds none. It adds limits (a $50 cap, 2 transport retries, a 600 s timeout). The runs already in `mailbox/Part A smoke tests - results.md` used the 600 s limit.

## Points for you

- **The hero example is an extreme position.** The best safe play gives away 1.494 equity, so it is a gammon-scale swing. The rule picks "the clearest Risk pays decision where the model played safe" (`decisions_export.mark_risk`). If you prefer a typical one, say so and I'll switch the rule to the median gap.
- **League 2 is paused** at 132 / 136 matches, so its numbers stay Provisional.
- **Not done (needs your approval):** switching the live URL (B2).
