# Shared positions: review and estimates (before any request)

Oct 24, 2026 · for Ümit, relayed by Zeki · brief `ZEKI-BG-SHARED-1563492796520861757` (`reviewed-request.md`, SHA256 `c9c6dd046e216f84ff1606e8dee73329e199c8d6ef7c1cff97dd3f79b4cd815a`, verified before reading; `original-request.txt` read too)

**No new model requests were made for this report: none paid, free or local, no smoke, probe, pilot or preflight call.** Here is everything I did:

- read `v3.db` read-only (`mode=ro`) and the smoke-answer files;
- rendered the shared-position requests offline with the existing binary (`jevgammon render`, which makes no network calls);
- computed the ladder tables read-only (`tools/ladder.py` functions with a read-only connection);
- fetched public price pages and OpenRouter's public model list.

No server, unit, site file or match was touched, and no batch is scheduled. The private Method draft is `mailbox/Method amendment draft - A12 matched 2026-10-24 v1.md`. The unrelated follow-up `ZEKI-BG-FOLLOWUP-1563491593900658812` was neither rebuilt nor run.

## 1. Already done

### At the plan and template level (not a measurement)

- **Nackgammon drops the standard opening table.** The Method page says so (`tools/site/method.py`, sets list: "Its prompt drops the opening table"), and so does the v3 design (design final, line 128).
- `prompts/nack-v2.md` (sha256 `fa7397be…a8`) matches `freeze.json` and `freeze/league1.json`, `league2.json` and `league3.json`. It has no "Opening rolls" section: it is `bg-v2.md` minus exactly that block (1,291 characters).
- `tools/v3/build.py` gives `nack-v2` to all 500 Nackgammon rows (line 218) and all 200 opening-control rows (line 291). The row files agree: 500 and 200 rows have `prompt: nack-v2`, and the 1,000 new-set rows have `bg-v2`.
- `src/players/prompt.rs` asserts the missing table in a unit test (lines 647–653: no "## Opening rolls", no "| 6-5 |", and the state equals bg-v2 minus the table block).
- One stale hash: root `freeze.json` (harness `32bab18`, Oct 14) lists `src/players/prompt.rs` as `db5fb888…`. The current file and all three league freezes have `67934a35…`. The position and prompt hashes match everywhere.

### The actual request path, checked offline today

- **The runner honours each row's prompt.** `jevgammon ask` (`src/ask.rs`, lines 434–436) picks the version in this order: `--prompt-version` flag, then the row's `prompt`, then the config's version (`bg-v2`). Both routes build their text from that version:
  - decision models: `decision.rs` line 435, `state(req)`;
  - chat models: `llm.rs` line 260, `letter_user(req, …)`.

  `render` uses the same precedence and the same match context as the league configs (3 rounds, 300-turn limit, no clock), so the rendered text is what `ask` would send. **Risk:** passing `--prompt-version bg-v2` to `ask` would silently put the table back on these rows. The Method draft forbids that flag for these files.
- **Rendered with each row's own prompt** (binary `target/release/jevgammon`, sha256 `20c5f0d8…c161`, built from `91b6016`; option-order seed `1190975713392774006`):

  | Set | Version | Table in state / letter prompt | Rules-block sha256 | Decision-route sha256 (all rows) | Chat-route sha256 (all rows) |
  | --- | --- | --- | --- | --- | --- |
  | Nackgammon (500) | nack-v2 × 500 | 0 / 0 | `9e73f933…4c0f` | `3e6d0fff7289423e2513e289744a00bb440ecf71ac7e1deadb6025dbcbccb92c` | `6b2a30e463c15b21f7ef3629d9caebf2a4f246cef4126e89e02ec8c66a2ca725` |
  | Opening control (200) | nack-v2 × 200 | 0 / 0 | `9e73f933…4c0f` | `5ad27cb54eea61521003425899bc11bb592812e3c598c213869aafe53e5b9587` | `b65d4d0a74af996e2e74f99737392291a4b879f646211e4db048ea10ac83258b` |
  | Same files with a forced `bg-v2` (negative check) | bg-v2 | 500 / 500 and 200 / 200 | `2c527d71…f550` | — | — |

  Every option order matches the stored `option_order`.
  - Decision-route hash: per row, sha256 of {state, instructions, options}, then sha256 over the lines.
  - Chat-route hash: per row, sha256 of {system, letter prompt}, then the same.
- **The opening control pairs exactly.** All 200 `ctl-*` rows match their `paired_with` `new-*` rows on board, dice, side, position key, turn, phase, option order and option texts. Each control state equals its standard state with only the table block removed. The control holds all 15 standard first rolls.
- **Wording mismatch, reported, not fixed.** `nack-v2` keeps the standard Setup sentence ("two on the 24-point, five on the 13-point, three on the 8-point, and five on the 6-point"). All 14 turn-1 Nackgammon requests show the real start below it: "your checkers: 24:2 23:2 13:4 8:3 6:4". The word Nackgammon appears nowhere in the prompt. The sentence is true for the control rows. Changing it would change a frozen prompt, so it waits for Ümit (decision D4).
- **Frozen counts confirmed.**
  - Nackgammon: 300 positions from turns 1–6 and 200 later. 14 eligible first rolls; 3-2 (27 legal plays) was excluded by the 2-to-25 rule.
  - Standard control: 15 first rolls.
  - Legal plays: 2–25 in every set, so no setup's option limit (the smallest is 25) splits a request. Any position costs one request, or two for the setups with a two-step reasoning readout.
- **Reusable records: none.**
  - No setup has answered any shared position (`tools/site/content/analysis_status.json` says the same).
  - The 50 smoke positions share no position key with any shared set (checked).
  - `replay.db` and `argon.db` hold v1 answers on the 1,000 v1 positions, but with v1's stored state text and generation-order options. That is a different prompt and order, so they are not reusable.

### Not done yet

- Matching Nackgammon to standard positions by difficulty: the plan had no rule for it and no frozen pair map.
- The old A12 "unfamiliar-start effect" (early Nackgammon minus control) compares different, unmatched positions. It is not a matched experiment.

## 2. Proposed Method changes (staged privately, dated, versioned)

The full text is in `mailbox/Method amendment draft - A12 matched 2026-10-24 v1.md`. In short:

1. **Counts:** 14 Nackgammon first rolls, not 15. 3-2 stays excluded, and the freeze stays as it is. First-roll comparisons use the 14 common rolls and stay descriptive.
2. **Table on/off stays its own contrast:** the 200 controls against their exact standard IDs, never merged with the Nackgammon contrast.
3. **New matched contrast:** ΔPR(setup, stratum) = PR(Nackgammon) − PR(matched standard, **no table**). Positive means worse on Nackgammon; no drop is assumed. Early (turns 1–6) and later (turn 7 or later) are reported separately.
   - **Exact strata:** turn (and roll at turn 1), GNUbg class group, and legal-play band.
   - **Distance features:** top-two 2-ply gap (weight 2), share of plays within 0.02, share of plays losing more than 0.08, mean loss over legal plays, log of the play count, and pip lead (later stratum).
   - **Calipers:** |Δgap| ≤ 0.25 SD and total distance ≤ 1.0.
   - **Assignment:** optimal 1:1 without replacement, with a seeded tie rule.
   - **Exclusions:** the v1 set as donors, and failed evaluations.
   - **Freeze:** mapping, seed and hashes go into a new `freeze/a12-match-v1.json`.
   - **Reported:** coverage and balance, with unmatched counts kept.
   - **Uncertainty:** paired cluster bootstrap over Nackgammon source games.
   - **Limits printed next to it:** matched *different* positions, no causal memorisation claim, and GNUbg's weaker Nackgammon evaluation.
4. **Donors:** early donors are the 200 controls plus the extension's 800 opening positions. Later donors are the new set's and the extension's non-opening positions.
   - **Extra matched no-table calls:** 300–500 per setup if coverage is full (early 100–300, later up to 200), counted and priced separately below.
   - The extension's own `bg-v2` run stays excluded.
5. **Runner rules:** no `--prompt-version` flag; a separate answers file (not `v3.db`); reuse only with identical settings JSON; re-check the render hashes before each set.

## 3. Exact missing decisions

- **D1. League 1 cohort membership** (roster read from `v3.db` at about 10:30 UTC, Oct 24):
  - Base proposal: the 15 current League 1 decision-model setups (Table A).
  - Liquid d1-ultra (a decision model, League 1's winner, moved to League 2 by ladder round 1): include it? It costs about $0.33.
  - LFM2.5-24B-A2B (off) (in League 1 now, but a chat model reading letter log-probabilities): include it? It needs about 1 GPU-minute.
  - Liquid d1.1: only after its own gate in the queued brief (smoke test first). Its model ID, price and tokens are unknown.
- **D2. Cup cohort: nine or eight?** See section 4.2. Which nine setups, or does Ümit mean the 8-team Hype Cup? And should we wait for the ladder's steady state (the Cup roster isn't fixed yet) or price a dated snapshot?
- **D3. The matching design (Method draft v1):** approve or change it. It needs a GNUbg CPU pass over the 500 Nackgammon positions and up to 5,000 donors. That pass makes no model requests, but it is computation, so it waits for this approval. Its CPU time isn't measured. [INFERENCE] It is small next to the roughly 116,000 league decisions the same scorer has already scored.
- **D4. `nack-v2` wording:**
  - (a) keep it and document the standard-layout sentence; or
  - (b) freeze a new version whose only change is a truthful setup sentence for Nackgammon rows.
- **D5. Extra matched calls:** approve 300–500 extra no-table decisions per setup. The exact number is known when the mapping is frozen, before any request.
- **D6. Routes for setups whose route changed:**
  - DeepSeek V4.1 Flash: OpenRouter → Fireworks (latest league turns) or our own SGLang server.
  - Qwen3.8-27B and LFM2.5: our own GPU (latest) and not their earlier hosted routes.

  Proposal: the route of each setup's latest league turns.
- **D7. Identity and price drift.** Checking any of these with a call would count as a model request, so none was made:
  - docs.celeris.ai/pricing lists `celeris-1.1-decision` but not our `celeris-1-decision`;
  - subq.ai lists $0.04/M against our roster's $0.05/M;
  - the hosted Fastino GLiDE model version isn't recorded.
- **D8. Spend caps and credit:**
  - League 1 cohort: billed $3.15–3.46.
  - OpenRouter: $11.00 left on Oct 23 (ladder log). That covers Mercury Decide. It doesn't cover DeepSeek V4.1 Flash (on) if it is ever chosen ($38–51), and this brief allows no credit purchase.
- **D9. GPUs and order.** No bariton GPU is free (nvidia-smi at 10:33 UTC):
  - GPUs 0 and 1: League 2's last two ladder matches, #525 and #554, still running;
  - GPU 2: other jobs;
  - GPU 3: in use by another job.

  Can schedules GPUs. The queued BG brief (Liquid d1.1, Kimi) is also waiting. Who goes first?
- **D10. Optional items, not in the base and not requested:** repeats (200 × 5), the 4,000-position extension (`bg-v2`), the A2 harness ablation, Kimi K3.1 Pro. Kimi stays under its existing $30 TOTAL cap and 200-first-look limit and is not enrolled here. OpenRouter lists `moonshotai/kimi-k3.1-pro` at $2/M in, $10/M out ($0.20/M cache read), Oct 24.

## 4. Cost and time estimates

### How the numbers are built

- **Base per setup:** 2,700 decisions (2,000 standard + 500 Nackgammon + 200 control).
- **Extra matched no-table calls:** 300–500, separate.
- **Reusable:** 0 everywhere.
- **Tokens and latency** come from each setup's own League decisions with 2–25 legal plays, on its latest route (`v3.db` `turns` joined through `matches.player1/2` to `players`), checked against smoke answers on the same route. Input tokens are scaled by 0.976 for the base mix and 0.935 for the no-table extras. That is the rendered length of these sets against the league-like smoke positions; it reflects the shorter `nack-v2`.
- **Output tokens include reasoning tokens.** For reasoning setups the range runs from the lower of league and smoke up to the higher of the two plus 20%.
- **No cache discount:** our records show no measured cached tokens.
- **Attempts** add an allowance for failed requests that `ask` asks again on a rerun: +2% for decision and off setups, +5% for reasoning setups. Invalid answers are never retried.
- **Provider calls** = attempts × calls per decision, as measured in `exchanges`: 2.0 for the two-step reasoning readout on our GPUs. Decision services add one warm-up call per `ask` run (5 runs).
- **Network retries** (HTTP 408/429/5xx, up to 3) aren't separable in our records, because pacing waits are logged in the same field.
- **Time:** the low end uses p50 latency, the high end mean latency × 1.2, each divided by the setup's configured parallel requests. Our single-slot GPU servers use smoke-test latency (league latency there includes queueing behind other matches). The 18 rpm OpenRouter pacing applies where set. It is shared by setups of one model: DeepSeek (off) and (on) share it.
- **Money:**
  - **Billed:** API keys.
  - **API-equivalent:** subscriptions and our own GPUs at list price, never billed.
  - **GPU hours:** server time, no dollar figure.
  - **Unknown:** shown as n/a, not $0.

**Price sources, fetched Oct 24, 2026, about 10:31–10:40 UTC:**

- OpenRouter: [models API](https://openrouter.ai/api/v1/models) and per-endpoint API (`/api/v1/models/<id>/endpoints`). Pinned endpoints: Fireworks DeepSeek V4.1 Flash $0.30/$1.20, Fireworks GLM-5.3 $1.40/$4.40, Alibaba Qwen3.8 Flash $0.15/$0.47, Inception Mercury Decide $0.02/$0. All equal our roster prices.
- [docs.typesafe.ai/models](https://docs.typesafe.ai/models): Jev 1.13.0 and 1.14.0, $0.042/M.
- [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions): gpt-6-luna, $0.10/M uncached input, no output charge.
- [docs.celeris.ai/pricing](https://docs.celeris.ai/pricing): $0.04/M for the 1.1 decision model.
- [docs.fastino.ai/pricing](https://docs.fastino.ai/pricing): GLiDE $0.04/M in, $0 out.
- [subq.ai/pricing](https://subq.ai/pricing): $0.04/M.
- [liquid.ai/blog/d1-ultra](https://liquid.ai/blog/d1-ultra): $0.042/M.
- Decider API-equivalent: Perplexity list price in our roster (Oct 18; not re-checked).
- Subscription API-equivalents: OpenRouter list prices. One differs from our roster: Gemini 3.8 Flash at $0.825/$4.125 against the roster's $0.75/$3.75.

### 4.1 League 1 decision-model cohort (first)

**Roster reconciliation.**

- **Frozen design (Oct 13):** Jev 1.13.0, GPT-6 Luna, Decider v1.1 27B, SubQ Snap Preview, Fastino GLiDE, Celeris-1 Decision, Clef, Open-Jev 27B v1.1, Cygnet, Gemma 4 31B (off/on), Qwen3.8-27B (off), Random, Safest, GNUbg weak.
- **League start (Oct 15):** Jev 1.13.0, Fastino GLiDE and Celeris were blocked (no key or credit), and GPT-6 Luna played through the ChatGPT subscription as a chat model.
- **Oct 19 reshape to decision models only:**
  - The Gemma 4 31B and Qwen3.8-27B setups moved to League 2, and Luna's subscription entry left.
  - Added Oct 19: Liquid d1-ultra, Jev 1.14.0, Jev 1.13.0, Celeris-1 Decision, GPT-6 Luna (Decisions API), Decider Flash v1.2, Winnow-12B, Mercury Decide.
  - Added Oct 20: Fastino GLiDE, Decider v1.2 27B.
  - Added Oct 22: Fastino GLiDE v1.2 (local).
- **Ladder round 1 (Oct 23, 20:49 UTC):** Liquid d1-ultra moved up to League 2; LFM2.5-24B-A2B (off) came down.
- **Proposed, queued, not started:** Liquid d1.1.
- **Today:** 19 participants = 15 decision-model setups + LFM2.5 (off) (a chat model) + Random, Safest and GNUbg weak. The three programs make no model requests and are not counted.

**Table A1: identity and measured inputs** (settings as stored in `players.settings`; probabilities come from the decision service for all 15)

| Setup | players.id | spec | Route | parallel | League decisions used (dates) | Input tok/decision | Output tok/decision | Latency p50 / mean, s | Smoke n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Celeris-1 Decision | 44 | `celeris/celeris-1-decision` | Celeris API | 2 | 1,983 (10-19–10-23) | 3,274 | 0 | 0.17 / 0.17 | 10 |
| Clef | 14 | `clef` | own GPU | 1 | 2,432 (10-15–10-23) | 3,416 | 0 | 1.88 / 7.98 | 50 |
| Cygnet (Gemma 4 12B) | 2 | `cygnet` | own GPU | 4 | 2,441 (10-15–10-23) | 3,456 | 1 | 0.42 / 0.91 | 50 |
| Decider Flash v1.2 | 33 | `pplx-local/pplx-decider-flash-v1.2` | own GPU | 1 | 1,784 (10-19–10-23) | 3,312 | 0 | 0.73 / 1.31 | 10 |
| Decider v1.1 27B | 16 | `pplx-local` | own GPU | 1 | 2,390 (10-15–10-23) | 3,291 | 0 | 0.89 / 6.05 | 50 |
| Decider v1.2 27B | 11 | `pplx-local/pplx-decider-v1.2` | own GPU | 1 | 1,826 (10-20–10-23) | 3,273 | 0 | 2.93 / 3.23 | 10 |
| Fastino GLiDE | 30 | `fastino` | Fastino hosted API | 4 | 1,894 (10-20–10-23) | 3,301 | 0 | 0.42 / 0.47 | 50 |
| Fastino GLiDE v1.2 (local) | 41 | `fastino/glide-v1.2` | own GPU | 4 | 1,793 (10-22–10-23) | 3,288 | 0 | 1.64 / 1.81 | 50 |
| GPT-6 Luna | 36 | `openai-decisions/gpt-6-luna` | OpenAI Decisions API | 2 | 1,881 (10-19–10-23) | 3,050 | 0 | 0.23 / 0.21 | 10 |
| Jev 1.13.0 | 8 | `jev/jev-1.13.0` | TypeSafe API | 2 | 1,774 (10-19–10-23) | 3,539 | 166 | 0.22 / 0.23 | 10 |
| Jev 1.14.0 | 38 | `jev/jev-1.14.0` | TypeSafe API | 2 | 1,871 (10-19–10-23) | 3,539 | 167 | 0.22 / 0.24 | 10 |
| Mercury Decide | 28 | `openrouter-decisions/inception/mercury-decide` | OpenRouter, Inception | 2 | 1,779 (10-20–10-23) | 3,204 | 1 | 0.47 / 0.52 | — |
| Open-Jev 27B v1.1 | 4 | `open-jev` | own GPU | 1 | 2,483 (10-15–10-23) | 24,563 (one pass per option) | 0 | 1.55 / 3.48 | 50 |
| SubQ Snap Preview | 32 | `subq/subq-snap-preview` | SubQ API | 4 | 2,465 (10-15–10-23) | 3,305 | 0 | 0.23 / 0.25 | 50 |
| Winnow-12B | 40 | `winnow/winnow-12b` | own GPU | 4 | 1,895 (10-19–10-23) | 3,369 | 0 | 2.74 / 2.61 | 10 |
| *Option: Liquid d1-ultra* | 27 | `liquid/d1-ultra` | Liquid API | 2 | 3,624 (10-19–10-24) | 2,963 | 0 | 0.23 / 0.32 | 10 |
| *Option: LFM2.5-24B-A2B (off)* | 10 | `openai-compatible/lfm2.5-24b-a2b` | own GPU (vLLM) | 16 | 3,011 (10-19–10-23) | 3,028 | 1 | 0.12 / 0.18 | — |
| *Proposed: Liquid d1.1* | — | not verified | Liquid API | — | none | unknown | unknown | unknown | none |

**Table A2: counts, money and time per setup**

| Setup | Base decisions | Attempts | Provider calls | Extra matched calls | Reusable | Price (Oct 24) | Base 2,700 | Extra 300–500 | Time base | Time extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Celeris-1 Decision | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.04/M in | $0.35 billed | $0.04–0.06 | 4–6 min | ≤1 min |
| Clef | 2,700 | 2,754 | 2,759 | 306–510 | 0 | none published | n/a | n/a | 42 min–1.4 h | 5–16 min |
| Cygnet (Gemma 4 12B) | 2,700 | 2,754 | 2,759 | 306–510 | 0 | none published | n/a | n/a | 4–12 min | ≤2 min |
| Decider Flash v1.2 | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.01/M in (Perplexity) | $0.09 API-eq. only | $0.01–0.02 | 20–34 min | 2–6 min |
| Decider v1.1 27B | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.02/M in (Perplexity) | $0.18 API-eq. only | $0.02–0.03 | 31–48 min | 3–9 min |
| Decider v1.2 27B | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.02/M in (Perplexity) | $0.18 API-eq. only | $0.02–0.03 | 43 min–2.2 h | 5–25 min |
| Fastino GLiDE | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.04/M in | $0.35 billed | $0.04–0.06 | 5–9 min | 1–2 min |
| Fastino GLiDE v1.2 (local) | 2,700 | 2,754 | 2,759 | 306–510 | 0 | none published | n/a | n/a | 19–56 min | 2–10 min |
| GPT-6 Luna | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.10/M in | $0.82 billed | $0.09–0.15 | 5–55 min | 1–10 min |
| Jev 1.13.0 | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.042/M in | $0.40 billed | $0.04–0.07 | 5–6 min | ≤1 min |
| Jev 1.14.0 | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.042/M in | $0.40 billed | $0.04–0.07 | 5–6 min | ≤1 min |
| Mercury Decide | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.02/M in | $0.17 billed | $0.02–0.03 | 11–14 min | 1–3 min |
| Open-Jev 27B v1.1 | 2,700 | 2,754 | 2,759 | 306–510 | 0 | none published | n/a | n/a | 58 min–1.5 h | 6–17 min |
| SubQ Snap Preview | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.04/M in (roster $0.05) | $0.36–0.44 billed | $0.04–0.07 | 3–5 min | ≤1 min |
| Winnow-12B | 2,700 | 2,754 | 2,759 | 306–510 | 0 | none published | n/a | n/a | 25–36 min | 3–7 min |
| *Option: Liquid d1-ultra* | 2,700 | 2,754 | 2,759 | 306–510 | 0 | $0.042/M in | $0.33 billed | $0.04–0.06 | 5–10 min | 1–2 min |
| *Option: LFM2.5-24B-A2B (off)* | 2,700 | 2,754 | 2,754 | 306–510 | 0 | (OpenRouter Liquid $0.05/$0.70) | $0.41 API-eq. only | $0.04–0.07 | ≤1 min | ≤1 min |
| *Proposed: Liquid d1.1* | 2,700 | unknown | unknown | 300–500 | 0 | unknown | unknown | unknown | unknown | unknown |

**Cohort totals (15 setups, without the options):**

- **Decisions:** 40,500 base, 41,310 attempts, 41,385 provider calls. The extra matched calls add 4,590–7,650.
- **Billed:** $2.85–2.94 base and $0.30–0.51 extra, so **$3.15–3.46 in all**. The warm-up calls cost under $0.01.
- **API-equivalent, not billed** (our-GPU Deciders at Perplexity's price): $0.44 base and $0.05–0.08 extra. Clef, Cygnet, GLiDE v1.2, Open-Jev and Winnow have no published price, so theirs is n/a.
- **Subscription quota:** none.
- **API time:** 0.6–1.7 h if run one after another. The vendors run side by side, so wall time is under 1 h; the longest is GPT-6 Luna, up to 55 min.
- **Own-GPU server time:** 4.0–8.3 h for the base and 0.45–1.5 h for the extras.
  - [INFERENCE] On 3 GPUs, laid out as in ladder round 1 (GLiDE v1.2 + Cygnet, then Clef, on one GPU; Decider v1.2 27B, Decider Flash v1.2 and Winnow on one; Decider v1.1, then Open-Jev, on one), that is about 2–4 h of wall time.
  - Add about 10 min per server start, as in the round-1 log.
- **Uncertainty:** low for money. Decision services bill input only, and the token counts are stable (smoke and league agree within about 15%). The risk is in the price and identity checks (D7) and in GPU availability (D9). Own-GPU times are ±50%, depending on GPU sharing.

### 4.2 Cup cohort (second): 9 against 8 is unresolved

- **The conflict:**
  - Ümit wrote "9 Cup teams".
  - `mailbox/backgammon-ladder-cup.md` line 7 replaces "the 9-team format", and its "Teams (8)" section defines eight. Our reply of Oct 23 (`backgammon-ladder-cup - response.md`) confirms that format.
  - I searched `mailbox/`, `workspace/`, the README, the handoff folders and the full git history (every commit). **I found no documented nine-setup list or shortlist.** The only trace is the line saying the nine-team format was replaced.
- **Please clarify:** does Ümit mean the 8-team Hype Cup, or a separate nine-setup evaluation list she will name? I haven't added a ninth entrant or changed the Cup format.
- **The Cup roster isn't fixed yet.** The ladder hasn't reached a steady state:
  - Round 1 still has #525 and #554 running.
  - Round 2 isn't requested. A read-only preview of today's tables would move Fastino GLiDE up to League 2, LFM2.5 (on) down, GPT-6.1 Sol (high) up and Grok 4.7 (off) down.

**Labelled scenario only: eight teams, from today's provisional tables (Oct 24, about 10:30 UTC). This is not a roster and not a replacement for the nine.**

1. League 3 #1, GPT-6.1 Sol (low)
2. League 3 #2, GPT-6 Astra (on)
3. League 2 #1, GPT-6.1 Sol (high)
4. League 2 #2, Gemini 3.8 Flash (low)
5. League 1 #1, Fastino GLiDE (GNUbg weak ranks first but is a program)
6. League 1 #2, Jev 1.14.0
7. Lowest-PR third place: Claude Opus 5.5 (on), PR 14.0
8. Next lowest third place: Gemma 4 31B (on), PR 19.2. The third third place, Jev 1.13.0 (PR 34.5), drops out.

**Exact overlaps with the League 1 cohort:** Fastino GLiDE and Jev 1.14.0 are the same setup row, settings, prompt versions, positions and seed. They are reused at $0 and 0 calls. Nothing else overlaps.

**Incremental cost of the scenario (6 setups):**

| Setup | Billing | Attempts / provider calls | Base 2,700 | Extra 300–500 | Time base |
| --- | --- | --- | --- | --- | --- |
| GPT-6.1 Sol (low) | ChatGPT subscription | 2,835 / 2,835 | $19.15–20.06 API-eq. | $2.05–3.58 | 43 min–1.1 h |
| GPT-6 Astra (on) | ChatGPT subscription | 2,835 / 2,835 | $96.15–101.54 API-eq. | $10.29–18.15 | 46 min–1.2 h |
| GPT-6.1 Sol (high) | ChatGPT subscription | 2,835 / 2,835 | $25.20–28.09 API-eq. | $2.72–5.07 | 1.5–3.0 h |
| Gemini 3.8 Flash (low) | Antigravity subscription | 2,835 / 2,835 | $9.50–9.93 API-eq. | $1.02–1.78 | 24–48 min |
| Claude Opus 5.5 (on) | Claude subscription | 2,835 / 2,835 | $71.56–84.67 API-eq. | $7.74–15.32 | 1.2–1.9 h |
| Gemma 4 31B (on) | own GPU (2 calls per decision) | 2,835 / 5,670 | GPU 3.4–7.5 h (API-eq. $9.59–10.98, hypothetical) | GPU 0.4–1.4 h | 3.4–7.5 h |

- **Billed money:** $0.
- **Subscription API-equivalent:** $221.6–244.3 base and $23.8–43.9 extra.
  - ChatGPT: $140.5–149.7.
  - Claude: $71.6–84.7.
  - Antigravity: $9.5–9.9.
- **Calls:** 19,845 base provider calls (17,010 attempts) and 2,205–3,675 extra.
- **Wall time:** about 3.4–7.5 h if the providers run side by side and a GPU is free. The bound is Gemma 4 31B (on) on one GPU at 24 sequences. The three ChatGPT setups take 2.9–5.3 h if run one after another.
- **Quota:** the usage limits are unknown. As a reference, ladder round 1 used about $185 API-equivalent of subscription capacity in one night without a reported stop (ladder log).

**Table C: unit costs for every League 2 and 3 model setup**, so any nine (or eight) named can be priced. A League 1 decision setup in the Cup costs $0 extra (Table A2 already pays for it).

| League | Setup | id | Route | Reasoning | parallel | In tok/dec. | Out tok/dec. | Calls/dec. | Attempts / calls | Price $/M in/out | Base 2,700 | Extra 300–500 | Time base | Time extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L3 | GPT-6.1 Sol (low) | 23 | ChatGPT subscription | low | 4 | 3,076 | 75 | 1.0 | 2,835 / 2,835 | $2 / $10 | $19.15–20.06 API-eq. | $2.05–3.58 | 43 min–1.1 h | 5–12 min |
| L3 | GPT-6 Astra (on) | 47 | ChatGPT subscription | medium | 4 | 3,094 | 75 | 1.0 | 2,835 / 2,835 | $10 / $50 | $96.15–101.54 API-eq. | $10.29–18.15 | 46 min–1.2 h | 5–13 min |
| L3 | Claude Opus 5.5 (on) | 34 | Claude subscription | high | 4 | 4,203 | 442 | 1.0 | 2,835 / 2,835 | $4 / $20 | $71.56–84.67 API-eq. | $7.74–15.32 | 1.2–1.9 h | 8–21 min |
| L3 | Claude Fable 5.1 (on) | 6 | Claude subscription | high | 4 | 4,231 | 790 | 1.0 | 2,835 / 2,835 | $10 / $50 | $228.99–314.02 API-eq. | $24.90–57.25 | 2.0–4.6 h | 13–51 min |
| L3 | Gemini 4 Argon (on) | 13 | Antigravity subscription | high | 4 | 3,392 | 2,063 | 1.0 | 2,835 / 2,835 | $2 / $10 | $77.24–102.60 API-eq. | $8.50–18.86 | 5.9–9.1 h | 40 min–1.7 h |
| L3 | GPT-6 Astra (off) | 3 | ChatGPT subscription | low | 4 | 3,081 | 64 | 1.0 | 2,754 / 2,754 | $10 / $50 | $91.63 API-eq. | $9.80–16.33 | 42 min–1.2 h | 5–13 min |
| L3 | Grok 4.7 (on) | 48 | xAI subscription | high | 8 | 4,342 | 11,237 | 1.0 | 2,835 / 2,835 | $2 / $6 | $215.15–366.20 API-eq. | $23.79–67.63 | 9.0–25.1 h | 1.0–4.6 h |
| L3 | Gemini 4 Argon (off) | 21 | Antigravity subscription | low | 4 | 3,421 | 19 | 1.0 | 2,754 / 2,754 | $2 / $10 | $18.91 API-eq. | $2.02–3.36 | 41 min–1.0 h | 5–11 min |
| L3 | Claude Opus 5.5 (off) | 46 | Claude subscription | low | 4 | 4,232 | 181 | 1.0 | 2,835 / 2,835 | $4 / $20 | $55.94–59.14 API-eq. | $6.00–10.59 | 39–58 min | 4–11 min |
| L3 | Grok 4.7 (off) | 22 | xAI subscription | low | 4 | 4,335 | 2,362 | 1.0 | 2,835 / 2,835 | $2 / $6 | $50.29–72.19 API-eq. | $5.48–13.18 | 2.7–12.6 h | 18 min–2.3 h |
| L2 | GPT-6.1 Sol (high) | 45 | ChatGPT subscription | high | 4 | 3,080 | 288 | 1.0 | 2,835 / 2,835 | $2 / $10 | $25.20–28.09 API-eq. | $2.72–5.07 | 1.5–3.0 h | 10–33 min |
| L2 | Gemini 3.8 Flash (low) | 17 | Antigravity subscription | low | 4 | 3,217 | 185 | 1.0 | 2,835 / 2,835 | $0.825 / $4.125 | $9.50–9.93 API-eq. | $1.02–1.78 | 24–48 min | 3–9 min |
| L2 | Gemma 4 31B (on) | 1 | own GPU (vLLM) | template default | 24 | 10,320 | 3,874 | 2.0 | 2,835 / 5,670 | $0.20 / $0.40 | $9.59–10.98 API-eq. | $1.04–1.99 | 3.4–7.5 h | 23 min–1.4 h |
| L2 | DeepSeek V4.1 Flash (on) | 15 | OpenRouter → Fireworks | low | 8, 18 rpm | 3,134 | 10,304 | 1.0 | 2,835 / 2,835 | $0.30 / $1.20 | **$37.65–50.69 billed** | $4.17–9.37 | 6.3–10.4 h | 42 min–1.9 h |
| L2 | Claude Sonnet 5.5 (high) | 9 | Claude subscription | high | 4 | 4,228 | 595 | 1.0 | 2,835 / 2,835 | $2 / $10 | $38.75–43.61 API-eq. | $4.20–7.90 | 58 min–1.5 h | 6–17 min |
| L2 | Gemini 3.8 Flash (high) | 18 | Antigravity subscription | high | 4 | 3,202 | 3,856 | 1.0 | 2,835 / 2,835 | $0.825 / $4.125 | $52.39–61.41 API-eq. | $5.79–11.32 | 2.1–4.0 h | 14–45 min |
| L2 | Claude Sonnet 5.5 (low) | 37 | Claude subscription | low | 4 | 4,185 | 145 | 1.0 | 2,835 / 2,835 | $2 / $10 | $27.25–29.63 API-eq. | $2.92–5.31 | 17–41 min | 2–8 min |
| L2 | Claude Fable 5.1 (off) | 24 | Claude subscription | low | 4 | 4,195 | 64 | 1.0 | 2,835 / 2,835 | $10 / $50 | $125.11–128.52 API-eq. | $13.37–22.91 | 18 min–1.2 h | 2–14 min |
| L2 | Gemma 4 31B (off) | 12 | own GPU (vLLM) | — | 4 | 3,217 | 1 | 1.0 | 2,754 / 2,754 | $0.20 / $0.40 | $1.73 API-eq. | $0.18–0.31 | 3–30 min | ≤6 min |
| L2 | GLM-5.3 (on) | 26 | OpenRouter → Fireworks | low | 8, 18 rpm | 3,004 | 113 | 1.0 | 2,835 / 2,835 | $1.40 / $4.40 | **$13.04–13.62 billed** | $1.39–2.43 | 2.6 h | 18–29 min |
| L2 | Qwen3.8-27B (on) | 20 | own GPU (vLLM) | low | 16 | 10,642 | 4,127 | 2.0 | 2,835 / 5,670 | $0.20 / $2.50 | $35.14–40.99 API-eq. | $3.88–7.55 | 9.5–16.1 h | 1.1–3.0 h |
| L2 | Qwen3.8 Flash (off) | 25 | OpenRouter → Alibaba | — | 8, 18 rpm | 3,213 | 8 | 1.0 | 2,754 / 2,754 | $0.15 / $0.47 | **$1.31 billed** | $0.14–0.23 | 2.5 h | 17–28 min |
| L2 | DeepSeek V4.1 Flash (off) | 31 | OpenRouter → Fireworks | — | 8, 18 rpm (shared with (on)) | 3,057 | 7 | 1.0 | 2,754 / 2,754 | $0.30 / $1.20 | **$2.49 billed** | $0.26–0.44 | 2.5 h | 17–28 min |
| L2 | Qwen3.8-27B (off) | 5 | own GPU (vLLM) | — | 8 | 3,189 | 2 | 1.0 | 2,754 / 2,754 | $0.20 / $2.50 | $1.73 API-eq. | $0.18–0.31 | 5–11 min | 1–2 min |
| L2 | LFM2.5-24B-A2B (on) | 19 | own GPU (vLLM) | low | 16 | 22,300 | 16,952 | 2.0 | 2,835 / 5,670 | $0.05 / $0.70 | $36.72 API-eq. (no current-route smoke: range not estimated) | $4.07–6.78 | 17.1–23.2 h | 1.9–4.3 h |
| L2 | Liquid d1-ultra | 27 | Liquid API | — | 2 | 2,963 | 0 | 1.0 | 2,754 / 2,759 | $0.042 / $0 | **$0.33 billed** | $0.04–0.06 | 5–10 min | 1–2 min |

Inputs in Table C are as measured. The money columns apply the 0.976 and 0.935 size factors.

### Uncertainty and what could move the numbers

- **Reasoning output** is the main driver for reasoning setups. The ranges span league against smoke plus 20%. The shared sets hold more opening positions than league play, so reasoning length there isn't measured. Grok 4.7 (on), Gemini 4 Argon (on) and Fable (on) could fall outside their ranges.
- **Subscription quotas and rate limits** are unknown. A quota stop changes wall time, not money. API-equivalent figures are not spending.
- **GPU availability** (D9): every own-GPU figure assumes a free RTX PRO 6000. None is free right now.
- **Prices** can drift: SubQ, Gemini 3.8 Flash and the Celeris model ID (D7) already have. Our records show no cache discount, so none is assumed.
- **Matched extras:** 300–500 per setup is a bound for full coverage. The exact count is known only after the frozen matching (D3, D5), which needs no model request.
- **Unknown, not zero:** Liquid d1.1 (tokens, price, identity); the hosted Fastino GLiDE model version; GNUbg CPU time for the matching features; Kimi K3.1 Pro (not enrolled).

Waiting for Ümit's go.
