# Did they improve? Pre-registration (2026-11-08)

**This is the pre-registration.** It is committed and pushed before the first model call of this experiment, and the page "Did they improve?" shows its rule, lesson prompt, model list and commitment line before that call.

**Results will be published whichever way they go.**

Sources: Ümit's brief (#2954, #2955), the plan draft (`mailbox/Did they improve - plan draft 2026-11-08.md`, 0567bb2), the proposal (`mailbox/Did they improve - proposal 2026-11-08.md`, 3f23da6), Zeki's 13 points (#3052) and clarifications (#3057, #3066, #3077), Ümit's decisions #3060, #3065 and #3084, Can's top-up note #3078. Where they differ, the later decision wins; this file states the result. The learning pilot (`mailbox/Learning pilot - plan 2026-11-07.md`, `mailbox/Learning pilot - results 2026-11-07.md`) supplies the lesson prompt, the test set, the dice and the harness rules reused here.

## 1. Question

Does each chat model on the leaderboard take risks better on the pilot's 200-position test after writing its own lessons over 10 games against GNU Backgammon Beginner (GNUbg weak), compared with answering the same test with no memory?

## 2. The rule (verbatim; decided by Ümit, #3060 and #3065)

**Improved** = both of these hold:

1. risks found with lessons (the mean of the 5 tests after game 10) minus risks found with no memory (the mean of the 3 empty runs) is **more than max(range of the model's own 3 empty runs, 5 points)**;
2. right safety with lessons minus right safety with no memory is **≥ −5 points** (right safety drops by no more than 5 points).

- Range = max − min of risks found over the model's 3 empty runs, in percentage points.
- The 5-point floor = 5 of the 100 positions where the risk pays. The Gemma pilot showed about 3 points of drift from re-asking alone.
- **This is an operational threshold, not a statistical test and not statistical evidence.** The page says so.
- Error rate (PR) is shown before and after; it is not part of the rule.

Examples (from #3057, with the 5-point floor): empty runs 28, 28, 28 (range 0) → threshold 5; with lessons +4 → **No**; +5.5 → **Yes** if right safety fell by at most 5. Empty runs 24, 27, 30 (range 6) → threshold 6; +5 → **No**; +7 → **Yes**.

## 3. Models

**Rule:** every chat model on the live leaderboard, one row per model, at its leaderboard setting (the setup that names the row: highest reasoning setting, late entries included). Each runs with its `v3.db` `players.settings` unchanged except `name`, `parallel`, `prompt_note_file` and, for local servers, `base_url`.

**15 chat models (in scope):**

| # | Model (v3.db setup) | Maker | Setting | Route | Status (8 Nov) |
|---|---|---|---|---|---|
| 1 | Qwen3.8 Flash (off) | Alibaba (Qwen) | off | OpenRouter → Alibaba, fallbacks off | waiting: first in order |
| 2 | GLM-5.3 (on) | Z.ai | low | OpenRouter → Fireworks, fallbacks off | waiting |
| 3 | Kimi K3.1 Pro (off) | Moonshot | off (`reasoning_effort: none`) | OpenRouter → moonshotai/mxfp4, fallbacks off | waiting: needs the money cap raised (§9) |
| 4 | DeepSeek V4.1 Flash — **tested checkpoint: 1017** (the leaderboard row is the original V4.1 Flash; separate checkpoints) | DeepSeek | low | **API setup: OpenRouter id `deepseek/deepseek-v4.1-flash-1017`** (canonical slug `deepseek/deepseek-v4.1-flash-20261017`, Hugging Face `deepseek-ai/DeepSeek-V4.1-Flash-1017`; Fireworks `accounts/fireworks/models/deepseek-v4p1-flash-1017`), **pinned to provider tag `fireworks`, fallbacks off, `require_parameters: true`**, $0.30/$1.20 per 1M (read 2026-11-08). Settings: the league settings of the setup "DeepSeek V4.1 Flash 1017 (on)" (reasoning effort low, letter read from the answer's logprobs, top_logprobs 5, `response_format` not sent), only the provider pin changed (DeepSeek → Fireworks). Every response's `model` and `provider` fields are recorded; the run stops if they do not name the 1017 checkpoint on Fireworks (no substitution). Not the league's local route (bariton 4-GPU, impossible: GPU 3 faulty); spark2 is not used. Decided by Ümit (#3084, #3089) and Main. | waiting: needs the money cap raised (§9) |
| 5 | Gemini 3.8 Flash (high) | Google | high | Antigravity subscription | waiting |
| 6 | Claude Sonnet 5.5 (high) | Anthropic | high | Claude Code subscription | waiting |
| 7 | Claude Opus 5.5 (on) | Anthropic | high | Claude Code subscription | waiting |
| 8 | Gemini 4 Argon (on) | Google | high | Antigravity subscription | waiting |
| 9 | Grok 4.7 (on) | xAI | high | xAI subscription (`api.x.ai`) | waiting |
| 10 | Claude Fable 5.1 (on) | Anthropic | high | Claude Code subscription | waiting |
| 11 | Gemma 4 31B (on) | Google | on (thinking) | local vLLM, same image, checkpoint and arguments as the league | waiting for a GPU |
| 12 | Qwen3.8-27B (on) | Alibaba (Qwen) | low | local vLLM (`tools/v3/servers/qwen38-27b.sh`) | waiting for a GPU |
| 13 | LFM2.5-24B-A2B (on) | Liquid AI | on | local vLLM (`tools/v3/servers/lfm25-24b.sh`) | waiting for a GPU |
| 14 | GPT-6.1 Sol (high) | OpenAI | high | ChatGPT Pro subscription (Codex backend) | blocked until the weekly reset 2026-11-13 11:38 UTC |
| 15 | GPT-6 Astra (high), late entry | OpenAI | high | ChatGPT Pro subscription only (paid API on hold) | blocked until 2026-11-13 11:38 UTC; the Astra (high) re-ask is cancelled, so this experiment uses the allowance |

**Cygnet (Gemma 4 12B): UNRESOLVED.** "Cygnet: in scope or not is pending Ümit's decision; its route does not currently pass lessons to the model." (Zeki #3066.) It is not run and not replaced by another model. If Ümit puts it in scope, a verified change is needed first (the stored request to the underlying vLLM contains the note, and the empty-note request is byte-identical to the league's); that change and its check are then added to this file as a dated amendment before any Cygnet call.

**Decision models: not tested: cannot write lessons.** They return probabilities over the options and cannot write text. The 22: Liquid d1-ultra, Base Labs Mammoth-1, Base Labs Elephant-1, Drex Max v1, Drex Max 1.1, Drex 2.0 (and its local setting), REAX 1.3, Fastino GLiDE, Fastino GLiDE v1.2, Jev 1.13.0, Jev 1.14.0, Open-Jev 27B v1.1, Decider v1.2 27B, Decider v1.1 27B, Decider Flash v1.2, Celeris-1 Decision, Clef, SubQ Snap 1.1, SubQ Snap Preview, GPT-6 Luna, Winnow-12B, Mercury Decide.

**The Gemma pilot row: "pilot (different design)".** Gemma 4 31B (off), from the learning pilot; no new calls.
- It shows the pilot's own pre-registered verdict (pilot plan §8: T10 − T0 ≥ +10 risks found and ≥ −5 right safety, lessons arm): **not met**. Risks found 25.0 → 33.3 (+8.3), right safety 96.0 → 97.1 (+1.1), error rate 55.6 → 46.4: T0 (one run) against the mean of 10 lessons series at T10.
- In this rule's column: **"not comparable (different design)"** (reasoning off; 10 series; one T0 run, not 3 empty runs; T5 tests; different in-flight counts).
- No exploratory comparison is shown.

## 4. Sampling and settings: what each route accepts

**Ümit's decision (#3060): each model at its league settings, unchanged; no forced temperature.** The page says: **"no shared seed; same settings as the leaderboard"**. No route is sent a seed (none is sent in the league).

| Route (models) | League request (and this experiment's) sends | temperature | seed | Source (read 2026-11-08) |
|---|---|---|---|---|
| ChatGPT subscription, Codex Responses (Sol, Astra) | `reasoning.effort: high`; no temperature, no top_p, no seed, no output cap | not accepted when effort ≠ `none` | no seed parameter | https://developers.openai.com/api/docs/guides/latest-model ; https://developers.openai.com/api/reference/resources/responses/methods/create |
| Claude Code subscription, Messages API (Fable, Opus, Sonnet) | `output_config.effort: high`, `max_tokens: 32000`; no temperature | default (1.0) only on Claude 4.7 and later | no seed parameter | https://platform.claude.com/docs/en/about-claude/model-deprecations ; https://platform.claude.com/docs/en/api/migration-2026-10-21#sampling-parameters |
| Antigravity subscription, generateContent (Argon, Gemini 3.8 Flash) | `temperature: 1.0`, `thinkingConfig.thinkingLevel: high` | accepted | accepted on the public API (random when unset); not sent | https://ai.google.dev/api/generate-content |
| xAI subscription, Responses (Grok 4.7) | `reasoning.effort: high`; no temperature | accepted (0–2) | no seed field | https://docs.x.ai/developers/rest-api-reference/inference/responses ; https://docs.x.ai/developers/model-capabilities/text/reasoning |
| OpenRouter → Fireworks (GLM-5.3, DeepSeek V4.1 Flash) | `temperature: 1.0`, `reasoning_effort: low`, provider pinned, `require_parameters: true`, `allow_fallbacks: false`, `usage.include` | accepted | not supported by the endpoint | `GET https://openrouter.ai/api/v1/models/<id>/endpoints` (`supported_parameters`) ; https://openrouter.ai/docs/api/api-reference/models/get-models |
| OpenRouter → moonshotai/mxfp4 (Kimi K3.1 Pro) | `temperature: 1.0`, `reasoning_effort: none`, provider pinned, fallbacks off | accepted | not supported | same listing |
| OpenRouter → Alibaba (Qwen3.8 Flash) | `temperature: 1.0`, `reasoning.enabled: false`, provider pinned, fallbacks off | accepted | accepted; not sent | same listing |
| local vLLM (Gemma 4 31B, Qwen3.8-27B, LFM2.5) | `temperature: 1.0`, the setup's template switches and `max_tokens` | accepted | accepted; not sent | https://docs.vllm.ai/en/stable/api/vllm/sampling_params/ |

The subscription routes use backends whose parameter handling is not documented (ChatGPT `backend-api/codex`, Claude Code OAuth, Antigravity `v1internal`, xAI with OMP's login); they get exactly the league's request.

## 5. Design

**Per model, the lessons condition only:**
- **5 series** of 10 games against GNUbg weak (GNU Backgammon 1.08 Beginner), **one series at a time**.
- Every series starts with no lessons. After each game there is **one lesson call**: it sees that game's record with GNUbg's 2-ply evaluation of each decision, and nothing else. The context of the next games is every lesson so far in the series, in the play call's system prompt between the pilot's delimiters (`=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===` … `=== END OF NOTES ===`).
- **Test after game 10 (T10)** of every series, with that series' lessons. No test after game 5.
- **No memory:** the same 200-position test, run **3 times with an empty context** (exactly the league request), **interleaved through the run**: E1 before series 1, E2 after series 2, E3 after series 4.

**Order of one model's steps:** E1 → S1 (+ its T10) → *cost check (§9)* → S2 → E2 → S3 → S4 → E3 → S5.

**Lesson call (Ümit #3060).**
- Prompt: the pilot's, unchanged — `workspace/learning-pilot/lessons_system.txt` + `lessons_user.txt`, **sha256 `d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e`** (sha256 of the two files' bytes concatenated).
- Sent as one free-text request (no answer format) through the model's **own route and login, at its leaderboard reasoning setting, with the route's league output limit**:
  - Codex, xAI, Antigravity: no output cap (the league sends none);
  - Claude Code: `max_tokens` 32,000 (the league's);
  - OpenRouter and local: the setup's `max_tokens`, else the route's default 32,768 (Gemma 4 31B (on) 24,000; LFM2.5 32,000). **Exception noted:** Qwen3.8 Flash (off) answers its league play call with `max_tokens: 16` (one letter, no reasoning); 16 tokens cannot hold lessons, so its lesson call uses the route's 32,768.
  - Temperature and reasoning fields exactly as in the route's league request (§4); the setup's extra request fields (provider pinning, template switches) are merged in as in the league.
- **Cut rule (the pilot's):** lines starting `- ` are lessons; at most 5 lessons and 150 words are kept (extra lessons, then extra words, cut). Every cut is counted and shown. A reply with no line at all gives an empty lesson set for that game: kept, not re-asked, counted and shown.

**Test:** the pilot's 200 positions (100 where the risk pays, 100 where safety pays), **test-set sha256 `6c92e7416745125ca3ea09c9e41e450a52716f8ad018772278b07f992f7318e6`** (`test_set.json`; positions file `test_positions.jsonl` sha256 `ff509ea102b4fcd2faca3402d585b05ba6d7dc0014a7c5f9dabbe48b13a3467f`). Asked with `jevgammon ask` (the league `Player`, prompt `bg-v2`, League 2's option-order seed 1190975713392774006). Test positions are never published.

**Dice:** the pilot's series seeds s01–s05 (`learning-pilot 2026-11-07 series k`, sha256-derived), the same for every model; games 2k−1 and 2k are a mirrored pair (`--fixed-rounds`).

**Isolation:**
- Test answers never enter lessons; test positions never appear in a lesson record (the pilot's leakage rule: a game decision whose board is a test position is left out of the record, counted).
- Nothing goes into `v3.db`, the leagues or the leaderboard. **Games played with lessons count nowhere** (no league, no leaderboard, not in the rule); each model has its own private database and output directory.

**Concurrency (recorded per request):** games and lesson calls run with 1 request in flight; each test (empty or T10) runs alone for that model with 4 decisions in flight; one model's steps run one at a time. Every stored request records how many of this experiment's decisions were in flight for that model when it was sent. Provider-side load is not observable, and the page says so.

## 6. Scores per model

- **before** = mean of the 3 empty runs; **after** = mean of the 5 T10 tests; **change** = after − before, for risks found, right safety and error rate (PR).
- Shares are over valid answers. Each row shows, before and after: the denominators (risk-pays and safety-pays positions answered validly), the invalid answers left out, and the answer rate.
- Rows are sorted by the change in risks found; tapping a row shows its lessons.

## 7. Completion and verdict gate

A model gets **yes/no** only when all of these are complete:
- all 5 series (10 games each, 10 lesson files each);
- all 5 T10 tests, each with **200 of 200** positions answered (valid or invalid; no failed request left);
- all 3 empty runs, each 200 of 200.

Until then its row shows live numbers and "running, n of 5 series", with no verdict text. A model that cannot complete is shown "incomplete" with the reason, and never gets a verdict from partial data.

## 8. Failed and invalid answers

- **Invalid answers (same rule as the leaderboard; Ümit #3060):** a reply that names no option (empty after thinking, cut at the output limit, a non-letter). In tests: not re-asked, left out of the shares (risks found, right safety, error rate), and **the count is shown**. In games: a random legal play, as in the leagues; counted.
- **Failed requests** (no reply: transport or HTTP error, quota 429, timeout): retried as in the leagues; a test position still unanswered is asked again later with the same prompt and context (after quota waits if needed) until 200 of 200.
- **A series interrupted part-way** is played again from game 1 with the same dice (the pilot rule); the failed attempt's files are archived (`attempt-N/`), its lessons are not used, and its spend counts.
- A lesson call that fails is retried until it returns.

## 9. Money (verbatim rules; Ümit #3065, Can #3078, Main's interim instruction)

Billed money: OpenRouter only (Qwen3.8 Flash, GLM-5.3, Kimi K3.1 Pro, DeepSeek V4.1 Flash). Subscriptions are $0 billed (quota, shown as API-list-price equivalent); local runs are $0 API spend.

**Stop rules (Ümit #3065, verbatim):**
1. "Spending approved up to $110 billed total from the shared OpenRouter balance (cap, not target). Logic/turkce are not part of it."
2. "NO per-model approvals. Cheapest first. After each model's 1-series cost check, continue automatically UNLESS (a) its projected full cost > 1.5× its estimate (use the per-model estimates in the plan draft table), or (b) the running billed total would pass $110. If either fires, stop that model and report why."

**Interim cap (Can #3078, Main):** until the balance is confirmed after the next top-up, this experiment's cumulative billed total is capped at **$25** (enough for Qwen3.8 Flash then GLM-5.3; Kimi and DeepSeek wait). The cap is a runner setting; it is raised to $110 only on Main's word, recorded in the run log.

**Balance check:** before every billed step the runner reads OpenRouter's live balance (`GET /api/v1/credits`: total credits − total usage). If **balance − $5 reserve** does not cover the step's expected cost, it stops and reports. A top-up instruction is not money; only the read balance counts.

**Per-model estimates (plan draft §7) and the stop limits derived from them:**

| Model | Estimate (full run) | 1.5× (rule a) | 1-series step S (estimate) | Empty-run step E (estimate) |
|---|---:|---:|---:|---:|
| Qwen3.8 Flash (off) | $2.30 | $3.45 | $0.35 | $0.18 |
| GLM-5.3 (on) | $22.00 | $33.00 | $3.35 | $1.75 |
| Kimi K3.1 Pro (off) | $35.00 | $52.50 | $5.34 | $2.77 |
| DeepSeek V4.1 Flash 1017, via Fireworks | $44.00 | $66.00 | $6.96 | $3.07 |

E = (full − 5 × S) / 3, the draft's estimate split over its steps.

**How the rules are applied (hard stops, logged):**
- **Cost check** = after E1 and S1 (with its T10). **Projected full cost = 5 × (billed cost of S1) + 3 × (billed cost of E1).** If it is more than 1.5× the model's estimate → rule (a): that model stops; the reason is logged and reported.
- **Before every billed step:** expected step cost = the table's S or E until the model's cost check, then its measured S1 or E1. If billed total so far + expected step cost would pass the cumulative cap ($25 interim, then $110) → rule (b): stop and report. The same if the live balance − $5 does not cover it.
- **Before every request (Zeki #3085): caps are enforced before a request starts, never discovered after crossing.** Every OpenRouter request (game, lesson call, test) first reserves its worst case in a hard ledger (the runner's `budget` ledger): every byte of the request body counted as an input token plus the request's whole output allowance (its `max_tokens`) at the list price — far above a typical request, so it is the safety margin. It is sent only if billed so far + the reservations of every request already in flight + its own reservation stay within the ledger's cap = min(1.5 × the model's estimate − that model's billed so far, cumulative cap ($25 interim, then $110) − billed total so far). Otherwise it is refused unsent, the step stops at the boundary, and the stop is logged and reported.
- **Billed cost (booked)** = per request, the larger of OpenRouter's reported `usage.cost` and the tokens at the list price; a request with no response is booked at its worst case. All stop rules use this booked amount (conservative). OpenRouter's reported cost is recorded beside it, and the account usage before and after each step is also recorded (the account is shared, so that delta is a cross-check only). Note: for DeepSeek the draft's $44 is OpenRouter's reported cost of the row's league decisions, which was 0.78× their list price; at list price the same workload is about $56 (still under its $66 limit).

## 10. Schedule

- **Publish first:** this file, then the page in pre-registration mode; the first model call only after the page is live.
- Then, one model at a time: **Qwen3.8 Flash → GLM-5.3 → Kimi K3.1 Pro → DeepSeek V4.1 Flash** (OpenRouter, within the money rules); **Gemini 3.8 Flash → Claude Sonnet 5.5 → Claude Opus 5.5 → Gemini 4 Argon → Grok 4.7 → Claude Fable 5.1** (subscriptions); **local models** (Gemma 4 31B (on), Qwen3.8-27B, LFM2.5) when a bariton GPU is free (the compactor holds them until about 08:00 UTC 9 Nov), claimed on the bus; **GPT-6.1 Sol and GPT-6 Astra (high)** after the ChatGPT reset 2026-11-13 11:38 UTC.
- Local and API models may run at the same time (different servers); one model's own steps never overlap.

## 11. Outputs

Private (never committed): `smoke/improve/<model>.db` (games, test answers, every request), `smoke/improve/<model>-plays.db`, `workspace/improve/runs/<model>/` (lessons, contexts, logs, ledgers). Public via the page: per-model aggregates, lesson texts, the rule, the lesson prompt and its hash, and the money record. Test positions and per-position answers are never published.

**Results will be published whichever way they go.**
