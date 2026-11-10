# Class row preview: backgammon (Ümit JOB 2 FINAL, #4217)

Branch `class-preview`, HEAD **a65ee5c** (rebased onto origin/main 1858d9b, force-pushed: 914879b Class scheme on
a re-applied Size row, a063048 row label and card of Ümit #4229 / turkce #4231, a65ee5c trillions per turkce #4237
and standard list prices per Ümit #4238). **Preview only. Not merged, not deployed, nothing live changed.**

## Update 2 (turkce #4237, Ümit #4238)
- **Label numbers:** trillions to one decimal from 1,000B (Kimi K3.1 Pro `2.8T`<sup>MoE</sup>; card "2.8T total"),
  whole from 10B, one decimal under 10B.
- **Standard list price only.** Every model_prices.json entry rechecked on 2026-11-10 for introductory / launch /
  promotional / preview wording; each entry now has `provisional` (true/false) and `provisional_reason` (checks.run
  enforces both). Results:
  - **Mercury Decide: corrected to its standard $0.04** (docs.inceptionlabs.ai/get-started/models: "$0.02 per
    million tokens (50% off the regular $0.04 price)"). Still Efficient, not provisional.
  - **Drex Max 1.1: provisional.** $0.03 is its launch price (nace.ai/developers: "Drex Max v1.1 cost is at its 50%
    launch price"); no regular v1.1 price is printed. Label `Closed · Efficient (provisional)`; the card says why.
  - **Gemini 4 Argon:** Google writes "$2.00 through November 30, 2026. $4.00 starting December 1, 2026." and does
    not call $2.00 introductory or promotional (no such word on the page): standard today, Workhorse; Flagship from
    1 Dec. Gemini 3.8 Flash the same ("$0.75 through December 31, 2026. $1.50 starting January 1, 2027."): Workhorse.
  - **SubQ Snap Preview:** the model is in "Public Preview"; its launch post states $0.05 without calling it
    introductory or a preview discount: its own standard price, not provisional.
  - Celeris-1 Decision (launch post $0.04, no introductory wording), DeepSeek V4.1 Flash 1017 (peak = standard;
    off-peak is a discount), and the rest (Anthropic, OpenAI, xAI, Alibaba "standard prices", Liquid, TypeSafe,
    SubQ 1.1, Fastino, Meta): no introductory or promotional wording on the page; not provisional.
  - **Provisional list: Drex Max 1.1 only.**
- Rebuilt on the same frozen copy: branch exit 0; `data/` and `decisions/` byte-identical to origin/main's build
  (main's site code unchanged since 65a4ec6: only this mailbox file moved). Screenshots refreshed.

## Update 1 (Ümit #4229, aligned with turkce #4231)
- Builds again on a fresh frozen copy (`/tmp/class-state`, copied 16:04:18Z; the live state had not updated since
  15:52, so data as of 15:50Z, results a7130a46): origin/main 65a4ec6 **exit 0**, branch 405dd12 **exit 0**; `data/`
  and `decisions/` byte-identical; index.html and improve/index.html identical once the class markup is removed
  (number tokens 6,734 and 3,734 equal).
- **Label after the name:** total whole from 10B (`26B`, `57B`, `266B`, `2800B`), one decimal under 10B (`9.4B`,
  `4.5B`); superscript **MoE** after every mixture of experts (`35B`<sup>MoE</sup>, `24B`<sup>MoE</sup>,
  `753B`<sup>MoE</sup>); superscript **2×** after REAX 1.3 (`57B`<sup>2×</sup>); dense: no mark; open model without
  a whole-model total: empty (DeepSeek V4.1 Flash; its 1017 checkpoint too); closed: `Closed · <class>`.
- **Card line** (after Parameters), e.g. Drex 2.0: "Mixture of experts: 35.11B total, about 3B active per step. Size
  class uses 35.11B." (the total, per #4217). Same for LFM2.5-24B-A2B (23.97B / 2.45B), Inkling Small, MiniMax,
  Kimi (2.8T / 104B); GLM-5.3: "active count not disclosed by the maker"; DeepSeek V4.1 Flash: its 552B backbone +
  196B memory, 8B/16B active, "Size class uses the 552B backbone." REAX 1.3: "Two models run together, option
  probabilities averaged 50/50: 57.36B in all, all used on every question."
- **50/50 verified** three ways: the model card (decisionmodels/REAX-1.3 @ fa4bf7e README: "Every request goes to both
  parts; their per-option probabilities are averaged 50/50"); the engine code it pins (reax-engine @ ff8f595,
  `reax13/probabilities.py` `mix()`: `.5 * (px[k] + py[k])`, then renormalised for roundoff; `reax13_engine.py`:
  "'mix': '0.5*G probability + 0.5*Q probability'"); and our run (setups.json: our GPU through reax-engine @ ff8f595,
  reax13 mode; our local checkout's probabilities.py and reax13_engine.py are byte-identical to the card's `engine/`).
- **Taps:** the existing row tap opens the card; checked at 375 px with touch emulation: tap on Drex 2.0's MoE mark,
  REAX 1.3's 2× mark and Kimi K3.1 Pro's name each open the card (`tap-375-*.png`); mouse hover on the mark at 1280
  opens it (`hover-1280-Drex-20-mark.png`).

## What ran
- Frozen live state `/tmp/class-state` (copied 2026-11-10T15:52:54Z right after a finished update cycle; data as of
  2026-11-10T15:50Z, results a7130a46) plus the repo's untracked inputs (replay.db, smoke/part-a.json,
  workspace/learning-pilot). Live state only read.
- Full `build.py --state /tmp/class-state --no-image` (compute, render, checks.run):
  origin/main 6e765da **exit 0**; branch a48c05d **exit 0** (logs: `class-preview-backgammon/build-*.log`).
- **Numbers unchanged:** `data/` and `decisions/` byte-identical between the two builds; only index.html,
  improve/index.html, about/index.html, bg.css, bg.js, site.js differ. index.html is identical once the class
  labels/keys/attributes are taken out; the number tokens of index.html (6,734) and improve/index.html (3,734) are equal.

## Rules as built
- Open model with a disclosed total (model_params.json): Tiny < 6B, Small 6–15B, Medium > 15–40B, Large > 40B, by
  **total** (no min(total, active) any more). Gemma E-series by total with embeddings (none on these tables).
- Closed model, or open model whose total is undisclosed: list price per 1M input tokens, base rate, maker's page
  (new `tools/site/content/model_prices.json`, URL + quote + read date): Efficient ≤ $0.50, Workhorse > $0.50–$3,
  Flagship > $3. No price on the maker's page → no class (none such on the leaderboard).
- One Class row: All · Tiny · Small · Medium · Large · Efficient · Workhorse · Flagship, combined with the type row
  (All / Chat / Decision); a class key with no model in the type in view is hidden (a selected one falls back to All).
  Same on /improve/. Programs: no class, stay in every view. `?class=<key>` opens on a class; old
  `?models=small-chat|small-decision` still open on that type with Tiny + Small.
- Label after each name: `27B`, `35B MoE · 3B active`, `2.8T MoE · 104B active`, `753B MoE` (active undisclosed),
  `Closed · Workhorse`. checks.run: every undisclosed-total model has a price entry with weights/source/read; every
  leaderboard model row has a class.

## Facts table (read 2026-11-10)
Open models with a disclosed total (from model_params.json, unchanged; sources there):

| Model | Total | Active | Arch | Class |
|---|---|---|---|---|
| Decider Flash v1.2 | 4.54B | – | dense | Tiny |
| Base Labs Elephant-1 | 9.41B | – | dense | Small |
| Winnow-12B | 11.91B | – | dense | Small |
| Cygnet (Gemma 4 12B) | 11.96B | – | dense | Small |
| LFM2.5-24B-A2B | 23.97B | 2.45B | MoE | Medium |
| Decider v1.1 27B / v1.2 27B, Drex Max v1, Fastino GLiDE v1.2, vLLM-SR d3-ultra | 26.09B | – | dense | Medium |
| Base Labs Mammoth-1 | 27.36B | – | dense | Medium |
| Clef | 27.48B | – | dense | Medium |
| Qwen3.8-27B | 27.78B | – | dense | Medium |
| Open-Jev 27B v1.1 | 27.80B | – | dense | Medium |
| Gemma 4 31B | 31.27B | – | dense | Medium |
| Drex 2.0 | 35.11B | 3B | MoE | Medium |
| REAX 1.3 | 57.36B | – | dense (composite) | Large |
| Inkling Small | 265.96B | 12B | MoE | Large |
| MiniMax-M3.1-Flash | 428B | 23B | MoE | Large |
| GLM-5.3 | 753.33B | not disclosed | MoE | Large |
| Kimi K3.1 Pro | 2.8T | 104B | MoE | Large |
| DeepSeek V4.1 Flash | no whole-model total; card: 552B backbone + 196B memory | 8B prefill / 16B decode | MoE | Large (see decisions) |

Closed / open-undisclosed models, by list price (base rate per 1M input tokens):

| Model | Weights | $ / 1M in | Class | Maker's page |
|---|---|---|---|---|
| Claude Fable 5.1 | closed | 10 | Flagship | https://platform.claude.com/docs/en/about-claude/pricing |
| Claude Opus 5.5 | closed | 4 | Flagship | same |
| Claude Sonnet 5.5 | closed | 2 | Workhorse | same |
| GPT-6 Astra | closed | 10 | Flagship | https://developers.openai.com/api/docs/pricing (short context) |
| GPT-6.1 Sol | closed | 2 | Workhorse | same |
| GPT-6 Luna (OpenAI Decisions API) | closed | 0.10 | Efficient | https://developers.openai.com/api/docs/guides/decisions |
| Gemini 4 Argon | closed | 2.00 (→ 4.00 from 1 Dec 2026) | Workhorse (Flagship from 1 Dec) | https://ai.google.dev/gemini-api/docs/pricing |
| Gemini 3.8 Flash | closed | 0.75 (→ 1.50 from 1 Jan 2027) | Workhorse | same |
| Grok 4.7 | closed | 2.00 (< 200k prompt) | Workhorse | https://docs.x.ai/docs/models |
| Qwen3.8 Flash | closed | 0.15 (Singapore, standard) | Efficient | https://www.alibabacloud.com/help/en/model-studio/model-pricing |
| DeepSeek V4.1 Flash 1017 | open, size undisclosed | 0.30 (peak, cache miss; off-peak 0.15) | Efficient | https://api-docs.deepseek.com/quick_start/pricing |
| DeepSeek V4.1 Flash | open | unknown (API now serves 1017 for the old names) | – (classed Large by backbone) | same |
| Liquid d1-ultra | closed | 0.042 | Efficient | https://www.liquid.ai/pricing |
| Jev 1.13.0 / Jev 1.14.0 (TypeSafe) | closed | 0.042 | Efficient | https://docs.typesafe.ai/models |
| SubQ Snap 1.1 | closed | 0.04 | Efficient | https://subq.ai/pricing |
| SubQ Snap Preview | closed | 0.05 | Efficient | https://subq.ai/introducing-subq-snap (launch post; pricing page lists only 1.1) |
| Celeris-1 Decision | closed | 0.04 | Efficient | https://celeris.ai/celeris-1-decision (launch post; pricing page lists only Celeris-1.1 Decision at $0.004) |
| Fastino GLiDE (API) | closed (hosted glide_v2) | 0.04 | Efficient | https://docs.fastino.ai/pricing |
| Mercury Decide (Inception) | closed | 0.04 standard ("$0.02 ... 50% off the regular $0.04 price") | Efficient | https://docs.inceptionlabs.ai/get-started/models |
| Drex Max 1.1 (Nace) | closed | 0.03, its 50% launch price; no regular price printed | Efficient (provisional) | https://console.nace.ai/docs/drex/reference/models, https://www.nace.ai/developers |
| Muse Ember (held, not shown) | closed | 0.10 | Efficient | https://dev.meta.ai/models/muse-ember |

## Classes in each view (models with a class, programs excluded)
| Table / view | n | Tiny | Small | Medium | Large | Efficient | Workhorse | Flagship |
|---|---|---|---|---|---|---|---|---|
| Leaderboard All | 38 | **1** | 3 | 11 | 4 | 11 | 5 | 3 |
| Leaderboard Chat | 16 | **0** (hidden) | **1** | 3 | 3 | **1** | 5 | 3 |
| Leaderboard Decision | 22 | **1** | **2** | 8 | **1** | 10 | **0** (hidden) | **0** (hidden) |
| /improve/ All | 28 | **0** | **2** | 7 | 6 | 5 | 5 | 3 |
| /improve/ Chat | 17 | **0** | **0** | 3 | 5 | **1** | 5 | 3 |
| /improve/ Decision | 11 | **0** | **2** | 4 | **1** | 4 | **0** | **0** |

Bold: fewer than 3 models.

## Group changes vs today's Small chat / Small decision filters
- **LFM2.5-24B-A2B** (chat): old Small (2.45B active) → **Medium** (23.97B total). Leaderboard and /improve/.
- **Drex 2.0** (decision): old Small (3B active) → **Medium** (35.11B total).
- **Inkling Small** (/improve/ chat, Small by name): → **Large** (265.96B total).
- Stay small: Cygnet (Small), Base Labs Elephant-1 (Small), Winnow-12B (Small), Decider Flash v1.2 (Tiny).
- Old Small chat on the leaderboard was 2 models, now 1 (Cygnet); old Small decision was 4, now Tiny 1 + Small 2.

## Tiers: not built
The paired exact test (McNemar, Holm) needs every pair of models to answer the same questions. The leaderboard's
risk calls come from league play: each league's games produced their own positions, so models in different leagues
share no positions (the page already says "Leagues played different positions"). No test was invented; # stays the
rank, and the About text now says why. What a valid tier test here would need, for Ümit to decide:
1. One common position set every leaderboard row answers (e.g. a fixed set of risk-call positions sent to every
   setup at its leaderboard setting), scored right/wrong per position against GNUbg.
2. Then McNemar per pair on the shared positions, Holm across pairs, tiers as on the other sites.
3. Closest existing set: the Nackgammon paired test (positions/nack-paired), but it is nackgammon, not the risk-calls
   score; several setups ran at other settings than their leaderboard row (e.g. GPT-6 Astra medium vs high); and 7 of
   the 38 leaderboard models never ran it (Claude Opus 5.5, Kimi K3.1 Pro, GLM-5.3, REAX 1.3, Qwen3.8 Flash,
   Jev 1.14.0, Clef). So it cannot tier this table as is.

## 'with web' / 'sample' labels
None qualify: no backgammon setup uses web search (no web/search setting in setups.json, labels.json,
late_entries.json, held_setups.json) and no row is a sample setup. No label added.

## Decisions for Ümit
1. **DeepSeek V4.1 Flash** (leaderboard main row): open, but the site states no whole-model total (card: 552B
   backbone + 196B memory). Built as **Large** (its disclosed backbone alone is over 40B, so no estimate is needed);
   the price route gives no answer (DeepSeek's page now prices only V4.1-Flash-1017, $0.30). Alternatives: Efficient
   by the 1017 price, or no class.
2. **Gemini 4 Argon** turns Flagship on 1 Dec 2026 ($2 → $4 announced). Built at today's price (Workhorse).
3. **Drex Max 1.1** is Efficient (provisional) on its launch price; a regular price, once published, replaces it.
4. **DeepSeek V4.1 Flash 1017** is "Open, size undisclosed · Efficient" while its original is Large; it only shows
   under the original's expander, so its own class shows nowhere.

## Screenshots (Chromium, light; `mailbox/class-preview-backgammon/`, untracked)
- `leaderboard-class-1280-all.png`, `leaderboard-class-375-all.png`: Class row, nothing selected.
- `leaderboard-class-1280-medium.png`, `leaderboard-class-375-medium.png`: class Medium selected (11 rows).
- `leaderboard-class-1280-decision-efficient.png`, `leaderboard-class-375-decision-efficient.png`: Decision +
  Efficient (10 rows; Workhorse and Flagship keys hidden).
- `leaderboard-class-*-chat.png`: Chat (Tiny key hidden).
No sideways overflow at 375 or 1280 in any shot. Script: `shots.py`.
