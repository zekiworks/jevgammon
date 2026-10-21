# Part B website: first delivery

Oct 21, 2026 · Part B of `workspace/backgammon-site-brief.md`, B13 items 1–5.

**Preview:** https://zekiworks.github.io/analysis/backgammon-preview/
- It is not linked from anywhere, and every page carries `noindex`.
- The live page `/analysis/backgammon/` is unchanged. Its own 15-minute timer still runs.
- The update loop commits only `backgammon-preview/` in the analysis repository, and it refuses to deploy if a build touches anything else.

**What the data allows right now.** No model has answered the v3 shared positions. The only shared-set answers are the v1 set's: 1,000 positions, 17 setups, the old prompt with plays in generation order. No new model requests were made (B12). So:
- Every shared-position section shows **Analysis pending**. None shows a number.
- v1-set numbers appear only as **Earlier version**, in their own blocks with the play-order note, never in a v3 table or chart.
- League numbers appear only league by league. League 1 and League 3 are **Published**. League 2 is **Provisional: league still running**, with status "Stopped (paused; 131 / 136 matches)".

## 1. Snapshot, build script, skeleton, home page, main table, Every decision, Method

Scripts are in `tools/site/` (jevgammon). Every page and every number is generated from data files; no number is typed into the HTML.

| Step | Script | What it does |
| --- | --- | --- |
| Snapshot | `snapshot.py` | Copies every v3.db table except `exchanges` in one read transaction (0.2 s). It also extracts, incrementally, exactly what each model was sent into `STATE/prompts.db` (68,724 decisions, 2 rules-text variants). A full re-read of all 68,724 decisions against the original requests found 0 mismatches. |
| Scoring | `score_plays.py`, `describe.py`, `score.sh` | GNUbg 1.08 evaluates **every legal play at 2-ply** (1,151,536 plays, 76,836 league decisions, 0 skipped) at nice 19 with at most 8 processes. `describe.py` reproduces the runner's option text byte for byte: 9,439/9,439 v1 options match. That gives the hitting rolls each model was shown, which B6 needs. |
| Analyses | `analysis.py`, `stats.py` | Error rate with a game bootstrap for league decisions and a position bootstrap for v1/shared positions (2,000 resamples, fixed seed); best-play share, blunder rate, P95 loss, worst-5% mean, confident-and-badly-wrong, AUROC/ECE/Brier (v1), time median/P90, retry time, $ per 1,000 with cost coverage, B6 2×2, breakdowns by phase/tag/options/gap, paired comparisons with the B9 verdicts, disagreements. |
| Pages | `build.py`, `pages.py`, `method.py`, `decisions_export.py`, `assets/` | The design system, components and page structure reused from the existing benchmark site. It is not named or linked anywhere. |
| Checks | `checks.py` | See item 5. |

Pages:
- **Home:**
  - title, subtitle, readouts, and "Results <hash>, data as of <date, time>";
  - "Findings will be written when the current leagues finish.";
  - filters for model type, weights, runs on and reasoning setting;
  - the main table with Table/Charts and the tabs Quality · Risk · Reasoning · Confidence · Routing · Stability · Cost (anchors `?tab=…#board`).
  - In every tab the shared-position table shows its columns and **Analysis pending**. The Earlier-version v1 table sits below it.
  - Under the table: how the shared positions were drawn, 2,000 standard positions, 2–25 legal plays.
  - Then the sections Is the risk worth it?, Reasoning, Risk and confidence, Game phases, Routing and teams, Learning from experience (Not measured, with the required line), Leagues, and Method and data.
- **Every decision** (`decisions/`):
  - 76,836 league decisions and 17,000 v1-set answers, 50 to a page, loaded on demand as gzip JSON split by dataset and setup. That is 1,906 files, 62 MB in total, and each page file is at most about 60 KB.
  - Each decision has an SVG board that fits 360 px, the turn text exactly as the model saw it (the shared rules text behind a toggle), the dice, and every legal play in the order shown with its consequences.
  - Each play also shows GNUbg's 2-ply equity, the equity it loses and the model's probability. The model's choice and the engine's best play are marked, with group splits and invalid answers.
- **Method:** setup, shared positions, the prompt and its history (with "Why it looks like this"), error rate, human scale (approximate), the B6 definitions and their limit, statistics and verdicts, the fixed thresholds, status labels, versions and the play-order note, confidence, cost, time, limits, and the two method experiments labelled "Method finding, not a model result".
- **Leagues:** one table per league with standings, decision quality, time and cost, plus the kept v3 notes and the earlier report's league and team sections (Earlier version).

The thresholds were fixed in `tools/site/content/thresholds.json` and committed (c7d1523) before any site number was computed:

| Threshold | Value |
| --- | --- |
| Blunder | loss > 0.08 |
| Badly wrong | loss > 0.08 |
| Very confident | p ≥ 0.9 |
| Time budget | 30 s |
| Minimum cell | 200 decisions |
| Near tie | gap < 0.02 |
| Safety pays | loss < 0.001 |

## 2. Every other section in place, with its status

| Page or section | Shows now | Status |
| --- | --- | --- |
| Where models disagree | v1 set: how many different plays the setups chose (all 17 agreed on 76 of 1,000 positions), and the 150 most-contested positions linked to Every decision | Shared: Analysis pending · v1: Earlier version |
| Phases | Error rate by phase, strategy tag, number of legal plays and top-two gap, per league and for the v1 set; cells under 200 show "Too few decisions" | Shared: Analysis pending · leagues: Published / Provisional · v1: Earlier version |
| Compare | Any two v1 setups, paired on the same positions, with interval and reading. League setups cannot be paired, and the page says so. | Shared: Analysis pending · v1: Earlier version |
| Models | One page per setup: 46 league, 17 v1, 19 smoke. Each has the B7 metadata, its results and a link to its decisions. | per dataset |
| New models: first look | One row per smoke setup, sorted by name, with the required top line. It feeds nothing else. | Smoke test (d3-turbo and Nemotron rows still waiting for a GPU) |
| Data | Every data file with its size and sha256, versions, how to recompute, and the analysis status table | — |
| Home charts | 6 v3 charts, each **Analysis pending**, plus one v1 dot plot (Earlier version) | |
| Routing and teams | Status, oracle note, link to the earlier team results | Analysis pending |
| Learning from experience | The one line | Not measured |

## 3. Analyses: status, data file, and whether it waits for the leagues

"Leagues" below means: League 1 and League 3 Published, League 2 Provisional. League numbers are never pooled. The same table, generated from `tools/site/content/analysis_status.json`, is on the Data page.

| Analysis | Status | Data file | Waits for running leagues? |
| --- | --- | --- | --- |
| A1 Decision quality | Shared: **Analysis pending** · per league: Published/Provisional · v1: Earlier version | `data/v3/shared.json`; `data/v3/league-N.json`, `data/v3/league-N/<setup>.json`; `data/v1/v1-set.json` | league part: yes (L2) |
| A2 Information given to the model | **Analysis pending** (no ablation answers) | none yet | no |
| A3 Return on reasoning | Shared: **Analysis pending** (league games are not paired) · v1: Earlier version, DeepSeek V4.1 Flash off vs thinking | `data/v1/v1-set.json` (reasoning), `data/v1/compare.json` | no |
| A4 Where models fail | Shared: pending · per league · v1 | `data/v3/league-N/<setup>.json` (phases, tags, options, gaps); `data/v1/v1-set/<setup>.json` | league part: yes |
| A5 Confidence | Shared: **Analysis pending** · v1: Earlier version (AUROC, ECE, Brier) · risk–coverage and letter-position bias: **Analysis pending** | `data/v1/v1-set/<setup>.json` | no |
| A6 Routing | **Analysis pending** | none yet | no |
| A7 Teams | **Analysis pending** · earlier report's teams: Earlier version (archived) | `tools/site/content/archive/` | yes |
| A8 Repeatability | **Analysis pending** (no repeat answers) | none yet | no |
| A9 Time and cost | Shared: pending · per league · v1 (time and tokens; cost Not measured) | `data/v3/league-N.json`; `data/v1/v1-set.json` | league part: yes |
| A10 League results (standings, W-D-L, games, gammons, safest-play behaviour) | Published / Provisional | `data/v3/league-N.json` | yes |
| A11 Cube | **Not measured** | none | no |
| A12 Opening knowledge / Nackgammon | **Analysis pending** (set sizes only) | `data/v3/shared.json` | no |
| A13 Fixed positions vs league results | **Analysis pending** | none yet | yes (and needs shared answers) |
| High hurts: fixes vs breaks | Shared: pending · v1: Earlier version (fixed/broken counts and equity) | `data/v1/compare.json` | no |
| High hurts: tail risk (P95, worst 5%, blunders) | Shared: pending · per league · v1 | `data/v3/league-N.json`; `data/v1/v1-set.json` | league part: yes |
| High hurts: confident and badly wrong | Shared: pending · per league (setups with probabilities; N/A otherwise) · v1 | same | league part: yes |
| High hurts: time budget | per league: share of request times over 30 s. The leagues had no clock, so losing on time was not measured, and the site says so. | `data/v3/league-N.json` | yes |
| High hurts: high only when needed | **Analysis pending** | none yet | no |
| Is the risk worth it? (B6) | Shared: pending · per league (2×2, headline numbers, by phase, confidence per cell) · v1: Earlier version | `data/v3/league-N.json`, `data/v3/league-N/<setup>.json`; `data/v1/v1-set.json` | league part: yes |

How B6 was settled:
- It runs on recorded decisions only, per league and labelled by league. No GNUbg run beyond scoring was needed: every play already has a 2-ply value, the safest included.
- The hitting rolls are the numbers the model was shown.
- A decision where every play leaves the same number of hitting rolls offers no risk choice. These are left out and counted.
- Where a risky best play and a safe play are within 0.001, the decision counts as **Safety pays**.
- Each 2×2 cell with fewer than 200 decisions shows "Too few decisions".

## 4. Setups with missing B7 metadata

Source: `tools/site/content/setups.json`, 82 entries. Each model page lists its own missing fields.
- **League 1:**
  - **price date:** Decider v1.1 27B, SubQ Snap Preview.
  - **weights:** SubQ Snap Preview, Liquid d1-ultra, Jev 1.14.0, Jev 1.13.0, Celeris-1 Decision, GPT-6 Luna, Mercury Decide, Fastino GLiDE.
  - **price:** Fastino GLiDE.
  - **sampling:** Cygnet (the letter-reading server's calibration temperature).
  - **No price, labelled own hardware:** Clef, Cygnet, Open-Jev and Winnow-12B. No source gives a price for them.
- **League 2:**
  - **price date:** all 11 priced setups (Gemini 3.8 Flash low/high, Claude Sonnet 5.5 low/high, GPT-6.1 Sol low/high, DeepSeek V4.1 Flash off/on, GLM-5.3 (on), Qwen3.8 Flash (off)).
  - **weights:** Qwen3.8 Flash (off).
- **League 3:**
  - **price date:** all 10 setups (GPT-6 Astra, Claude Opus 5.5, Claude Fable 5.1, Gemini 4 Argon, Grok 4.7; each off/on).
- **v1 set:**
  - **date run:** all 17.
  - **option groups:** Jev 1.13.0, GPT-6 Luna, DeepSeek V4.1 Flash, Qwen3.8 Flash Next, GLM-4.7-Flash, Gemini 3.8 Flash, GPT-6 Astra, Claude Opus 5.5, DeepSeek V4.1 Flash (thinking), Gemini 4 Argon, Gemini 4 Argon (shuffled).
  - **weights:** Jev 1.13.0, GPT-6 Luna.
  - **reasoning:** DeepSeek V4.1 Flash, Qwen3.8 Flash Next, GLM-4.7-Flash.
  - **sampling:** Cygnet, Gemma 4 31B.
  - **price date:** Decider v1.1 27B, GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon (both runs).
  - **GLM-5.3-Flash NVFP4:** model ID, provider, weights, runs on, reasoning, option groups, sampling and price. It exists only in replay.db.
- **Smoke tests:** nothing missing.

The "open" weights of the checkpoints we serve ourselves (Clef, the Deciders, Winnow, LFM, Gemma, Qwen3.8-27B, DeepSeek) are inferred from the fact that we serve them; no source states it.

## 5. Update loop with pre-deploy checks (running)

- **Units:** the systemd user units `bg-site-preview.service` and `.timer` (`tools/site/systemd/`) run `tools/site/update.sh` at :05 and :35 each hour.
- **What one run does:**
  - takes a snapshot and computes a change key from the league fingerprint, the site code, the smoke rows and the v1 set;
  - stops if the key has not changed;
  - otherwise scores the new decisions (8 processes at nice 19, never at the same time as the live page's scoring: it waits for the live page's lock);
  - builds in its own clone of the analysis repository, runs the checks, commits `backgammon-preview/` only, pushes (rebasing on a race), and refreshes `workspace/findings-draft.md`.
- **First deploy:** today at 18:52 UTC, results `b58c69ba`.
- **Checks (`tools/site/checks.py`, before every deploy):**
  1. Every number on every page appears in a data or content file (dates are taken out first).
  2. Counts add up:
     - snapshot = setups = league decisions;
     - played = 2 × finished matches;
     - invalid + valid = decisions;
     - risk cells and phase/option cells sum to the scored decisions;
     - v1 = 17 × 1,000;
     - exported decisions = scored decisions.
  3. No mixing:
     - no table holds rows of two datasets;
     - v1 rows sit only inside Earlier-version blocks;
     - every block of an unfinished league carries "Provisional: league still running".
  4. No hostnames, IPs, local paths, keys or the other benchmark's name, in any file including the decompressed decision files.
  5. Every relative link resolves, ids are unique, and every #anchor exists.
- **On a failure:** nothing is deployed, and the failures go to `mailbox/Backgammon site preview - check failed.md`.
- **Browser check:** headless Chromium at 1280 and 390 px on the home page, Leagues, Phases, Compare, Disagreements, Every decision (a league and the v1 set), New models, Models, Data, Method and model pages. No console errors. Nothing wider than the screen except the scrolling nav and the sideways-scrolling tables. The board is 330 px at 390 px and 300 px at 360 px.

## Differences from the current page, and points for you

- **Scoring:** the new site scores every legal play at 2-ply. The live page re-scores only the five best at 0-ply plus the chosen play. 99.7% of losses are identical; the largest difference is 0.004.
- **Invalid answers** are left out of error rates and shown separately (B11). The live page counted the runner's random play.
- **The play-order note** is computed by the build: Gemini 4 Argon shuffled minus unshuffled is **+1.9 (95% interval −0.2 to +4.2)** with this site's bootstrap. The brief quotes −0.3 to 4.1 from an earlier run. I kept the computed one, because every site number must come from a script.
- **Failed requests:** a request that fails after its retries leaves no decision, so the site cannot count failures per decision. The Quality tab says so. Retry and wait time is shown.
- **Confidence metrics** (AUROC/ECE/Brier) are shown only for the v1 set. The design restricts A5 to shared positions, so the leagues show only "confident and badly wrong".
- **v1 prompts for chat models:** Every decision rebuilds them with `tools/replay.py letter_prompt()`, which needs `~/code/cygnet/shim` on the build machine.
- **Size:** the preview adds 62 MB of decision files to the analysis repository. Later updates rewrite only the pages that changed.
- **Findings draft:** `workspace/findings-draft.md`, refreshed after every update. The site shows none.
- **Re-checking published findings:** once a set is approved, add it to `tools/site/content/findings.json` with the value each finding rests on. The loop then lists any finding the new data no longer supports in `mailbox/Backgammon site - findings to re-check.md`.
- **Not done (needs your approval):** switching the live URL (B2).
