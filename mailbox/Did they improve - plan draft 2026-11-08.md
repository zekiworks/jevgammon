# Did they improve? Plan draft (2026-11-08, revision 2)

**DRAFT. Not the pre-registration yet.** It becomes one only after Ümit settles section 8, and it is committed and published (rule, lesson prompt, model list, and "Results will be published whichever way they go.") before the first model call.

The brief is Ümit's (bus #2954), consolidated in #2955, which wins where they differ. This draft follows the learning pilot's plan (`mailbox/Learning pilot - plan 2026-11-07.md`) and its results (`mailbox/Learning pilot - results 2026-11-07.md`).

**Revision 2** follows Zeki's review (#2967):
- spread with no floor;
- the Gemma pilot row with its original verdict;
- sampling checked per route against the providers' docs;
- concurrency, completion and failed/invalid policies;
- Cygnet and DeepSeek;
- spending approval and GPU schedule.

How the draft was made: no model call, no spend, no GPU, no service claim. The inputs were:
- read-only queries of `v3.db`;
- the live leaderboard (8 Nov 2026, 08:20 UTC data);
- the pilot's own files;
- read-only checks: OpenRouter `/api/v1/credits` and `/api/v1/models/<id>/endpoints`, spark2's `docker ps` and `/v1/models`, and bariton's `nvidia-smi`;
- provider documentation, read 2026-11-08 (§4).

**Order (#2955):** Part 2 (this experiment) starts only after Part 1 is done. Part 1 is the retest-noise and sampling-settings check that LearningPilot is running on spark3.

## 1. Question

Does each chat model on the leaderboard take risks better on the 200-position test after writing lessons from 5 series of 10 games against GNU Backgammon Beginner, compared with no memory?

## 2. Models

**Rule:** every chat model on the live leaderboard, with one row per model at its leaderboard setting. That is the highest reasoning setting, with late entries included (the site's row rule).

**Count:** 16 chat models. Gemma 4 31B (off) also gets a row from the pilot, labelled "pilot (different design)".

**Decision models are not tested.** There are 22 of them:
- Liquid d1-ultra, Base Labs Mammoth-1, Base Labs Elephant-1;
- Drex Max v1, Drex Max 1.1, Drex 2.0 (and its local setting), REAX 1.3;
- Fastino GLiDE, Fastino GLiDE v1.2;
- Jev 1.13.0, Jev 1.14.0, Open-Jev 27B v1.1;
- Decider v1.2 27B, Decider v1.1 27B, Decider Flash v1.2;
- Celeris-1 Decision, Clef, SubQ Snap 1.1, SubQ Snap Preview, GPT-6 Luna, Winnow-12B, Mercury Decide.

They return probabilities over the options and cannot write lessons. The page lists them as "not tested: cannot write lessons".

| # | Model (v3.db setup) | Maker | Setting | Route in the league | Access now (8 Nov) |
|---|---|---|---|---|---|
| 1 | GPT-6 Astra (high), late entry | OpenAI | high | ChatGPT Pro subscription (Codex backend) | **Blocked.** At the weekly limit until **2026-11-13 11:38 UTC**. Paid API is on hold (Zeki/Can), so this runs on the subscription only, after the reset. The Astra (high) re-ask needs the same allowance. |
| 2 | Gemini 4 Argon (on) | Google | high | Antigravity subscription | Credentials present. Quota per the 10-28 probe: about $1,800 API-equivalent per week and $450 per 5 h. Not probed now. |
| 3 | Claude Fable 5.1 (on) | Anthropic | high | Claude Code subscription | Credentials present. Quota unknown. Probably shared with our own Claude Code agents [INFERENCE]. |
| 4 | GPT-6.1 Sol (high) | OpenAI | high | ChatGPT Pro subscription (Codex) | **Blocked** until 2026-11-13 11:38 UTC (same weekly limit). |
| 5 | Claude Opus 5.5 (on) | Anthropic | high | Claude Code subscription | Same as Fable. |
| 6 | DeepSeek V4.1 Flash (on) | DeepSeek | low | Until 2026-10-20 20:09 UTC: OpenRouter → Fireworks. After that: our own SGLang, V4.1-Flash-1017 checkpoint, TP4 on all 4 bariton GPUs | Only the OpenRouter → Fireworks route is possible; it is billed. Bariton TP4 is impossible: GPU 3 (GPU-e4f2a538) is faulty and never used. spark2's `deepseek-v4-flash-dspark` (DeepSeek-V4-Flash-Vision-Exp) is a different checkpoint and **is never used as a substitute**. |
| 7 | Grok 4.7 (on) | xAI | high | xAI subscription (OMP `xai-oauth`, `api.x.ai`) | Credentials present. Quota unknown. |
| 8 | Claude Sonnet 5.5 (high) | Anthropic | high | Claude Code subscription | Same as Fable. |
| 9 | Gemini 3.8 Flash (high) | Google | high | Antigravity subscription | Same as Argon. |
| 10 | Kimi K3.1 Pro (off) | Moonshot | off | OpenRouter → moonshotai/mxfp4 | OpenRouter credit: **$13.42** on 8 Nov ($155.00 total − $141.58 used). It is shared with logic/turkce's new Flash runs, so it is re-checked at go time. |
| 11 | Gemma 4 31B (on) | Google | on | local vLLM (bariton RTX PRO 6000; GB10 for a while) | Needs a GPU (§7). The pilot was Gemma (**off**); the leaderboard setting is (on). |
| 12 | Qwen3.8-27B (on) | Alibaba (Qwen) | low | local vLLM (bariton) | Needs a GPU (§7). |
| 13 | GLM-5.3 (on) | Z.ai | low | OpenRouter → Fireworks | OpenRouter credit (as Kimi). |
| 14 | Qwen3.8 Flash (off) | Alibaba (Qwen) | off | OpenRouter → Alibaba | OpenRouter credit (as Kimi). |
| 15 | Cygnet (Gemma 4 12B) | Google | – | local: the Cygnet shim (one-token letter readout, decision-service route) over vLLM | Needs a GPU. **Not run until a verified change exists (§6 item 3, §8.9).** |
| 16 | LFM2.5-24B-A2B (on) | Liquid AI | on | local vLLM (bariton) | Needs a GPU (§7). |
| – | Gemma 4 31B (off): **pilot (different design)** | Google | off | spark3 vLLM | Done (pilot). No new calls. |

## 3. Design (from #2954/#2955)

**Conditions, per model:**
- **lessons:** 5 series × 10 games against GNUbg weak (Beginner), with the pilot's lesson prompt, unchanged (sha256 `d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e`). Limits: at most 5 lessons and 150 words per game.
  - Every series starts with no lessons.
  - After each game there is one lesson call. It sees that game's record with GNUbg's 2-ply evaluation of each decision, and nothing else.
  - The context is every lesson so far in the series, in the system prompt between the pilot's delimiters.
- **no memory:** the 200-position test, run 3 times with an empty context. That is exactly the league request.

**Test:**
- The pilot's 200 positions (100 Risk wins, 100 Safety wins; sha256 `6c92e741…18e6`).
- In the lessons condition, the test runs after game 10 of every series (T10), with that series' lessons.
- There is no test after game 5.

**Dice:** the same 5 schedules for every model. **Proposed:** the pilot's series seeds s01–s05 (`learning-pilot 2026-11-07 series k`). Games 2k−1 and 2k are a mirrored pair.

**Isolation:**
- Test answers never enter lessons.
- Test positions never appear in a lesson record (the pilot's leakage rule).
- Nothing goes into `v3.db`, the leagues or the leaderboard.

**Score per model:**
- **before** = the mean of the 3 no-memory runs;
- **after** = the mean of the 5 T10 tests;
- **change** = after − before, for risks found, right safety and error rate (PR).

**Own retest spread** = the observed max − min of risks found over the model's 3 no-memory runs, in percentage points.

**Improved (Ümit's rule, as written; to publish before the first call):** both of these must hold:
- risks found change > the model's own retest spread;
- right safety change ≥ −5 points.

Error rate is shown, but it is not part of the rule.

**What the rule is not.** The spread is a descriptive yardstick: how far the model's own answers moved when the same empty test was asked 3 times. "Improved" means the lessons mean rose by more than that observed range. It is not a significance test, and the page says so.

**Completion and verdict.** A model gets a verdict (yes/no) only when all of these are complete under the §5 policies:
- all 5 series (10 games each, 10 lesson calls each);
- all 5 T10 tests;
- all 3 no-memory tests.

Until then, its row shows live numbers and "running, n of 5 series", with no verdict text. A model that cannot complete gets "incomplete" and the reason; it never gets a verdict from partial data.

**Page "Did they improve?" (under Experiments):**
- One row per model: maker, setting, risks found before → after, change, right safety before → after, error rate before → after, the model's own retest spread, and yes/no.
- Rows are sorted by the change in risks found.
- Tapping a row shows its lessons.
- Decision models are listed as "not tested: cannot write lessons".
- Numbers go live as each model finishes.
- Before the first call, the page shows the rule, the lesson prompt, the model list and "Results will be published whichever way they go."

**The Gemma pilot row.** Label: "pilot (different design)".
- It shows the pilot's **original pre-registered verdict** (plan §8: T10 − T0 ≥ +10 points risks found and ≥ −5 right safety, lessons arm): **not met**.
  - Risks found 25.0 → 33.3 (+8.3).
  - Right safety 96.0 → 97.1 (+1.1).
  - Error rate 55.6 → 46.4.
  - This is T0 (one shared run) against the mean of 10 lessons series at T10.
- In the new rule's column it reads **"not comparable (different design)"**. The differences: reasoning off; 10 series; one T0 run instead of 3 no-memory runs; T5 tests; different in-flight counts.
- Any exploratory comparison is shown separately and only if Ümit confirms (§8.6). An example is the pilot's lessons T10 against its 20 empty-context budget tests.

**Order:**
1. Part 1 settles the sampling settings.
2. Local models when GPUs are free (§7).
3. API and subscription models, cheapest first.
4. For each API model: 1 series as a cost check, then report $ and time, and continue only with **Ümit's approval for the spend**. Zeki's review is not spending approval.

## 4. Sampling settings: what each route accepts (docs read 2026-11-08)

Ümit's brief asks for the same sampling settings for every model. The table records what each provider documents for these models, and what our league requests send today (`src/players/llm.rs` `constrained_request`, branch `learning-pilot`).

An unsent parameter does not prove the API rejects it. Only documented behaviour is listed, with its source.

| Route (models) | League request sends | temperature | top_p | seed | Source (read 2026-11-08) |
|---|---|---|---|---|---|
| OpenAI public API (GPT-6 Astra, GPT-6.1 Sol; effort high) | none of the three | **not accepted** when reasoning effort is not `none` (Astra and Sol do not support `none`) | **not accepted** | **no seed parameter** in Responses `create` | https://developers.openai.com/api/docs/guides/latest-model ("When reasoning effort is not `none`, remove `temperature`, `top_p`, and `top_logprobs`"); https://developers.openai.com/api/reference/resources/responses/methods/create (no `seed`) |
| Anthropic Messages (Fable 5.1, Opus 5.5, Sonnet 5.5) | none | **default (1.0) only**: non-default values return 400 on Claude 4.7 and later in API version 2023-06-01 (the version our route sends); removed entirely in 2026-10-21 | default only | **no seed parameter** | https://platform.claude.com/docs/en/about-claude/model-deprecations (API parameter deprecations); https://platform.claude.com/docs/en/api/migration-2026-10-21#sampling-parameters |
| Gemini API (Argon, Gemini 3.8 Flash) | `temperature: 1.0`, `thinkingLevel` | accepted | accepted (`topP`) | **accepted** (`seed`; random when unset) | https://ai.google.dev/api/generate-content (GenerationConfig) |
| xAI Responses (Grok 4.7) | none | accepted, 0–2, sampled at most at 1 | accepted, sampled at most at 0.95 | **no seed field** | https://docs.x.ai/developers/rest-api-reference/inference/responses ; https://docs.x.ai/developers/model-capabilities/text/reasoning |
| OpenRouter → Fireworks (DeepSeek V4.1 Flash, GLM-5.3) | `temperature: 1.0`; `require_parameters: true`, no fallback | accepted | accepted | **not supported by the Fireworks endpoint**. Because of `require_parameters`, sending one would fail routing. | `GET https://openrouter.ai/api/v1/models/<id>/endpoints` (`supported_parameters`, read 2026-11-08); https://openrouter.ai/docs/api/api-reference/models/get-models |
| OpenRouter → moonshotai/mxfp4 (Kimi K3.1 Pro) | `temperature: 1.0` | accepted | accepted | **not supported** | same endpoints listing |
| OpenRouter → Alibaba (Qwen3.8 Flash) | `temperature: 1.0` | accepted | accepted | accepted | same endpoints listing |
| local vLLM (Gemma 4 31B, Qwen3.8-27B, LFM2.5, Cygnet's vLLM) | `temperature: 1.0` | accepted | accepted | accepted per request. Batch-invariant results need `VLLM_BATCH_INVARIANT=1` (beta). | https://docs.vllm.ai/en/stable/api/vllm/sampling_params/ ; https://docs.vllm.ai/en/latest/features/batch_invariance/ |

**Caveat on subscription routes.** The rows above document the public APIs. Our league routes use other backends:
- OpenAI: `chatgpt.com/backend-api/codex/responses`;
- Claude: the Claude Code OAuth login on `api.anthropic.com`;
- Google: Antigravity `cloudcode-pa …/v1internal:generateContent`;
- xAI: `api.x.ai` with OMP's login.

Their parameter handling is not documented. Whether they accept or honour a parameter (for example, a seed on Antigravity) could only be checked with a model call. None was made.

**Consequence: one common setting for all 16 is not possible on the documented APIs.**
- **Seed:** possible only on Gemini (public API; Antigravity unverified), OpenRouter → Alibaba and local vLLM. It is impossible on OpenAI, Anthropic, xAI, Fireworks and Moonshot.
- **Temperature:** cannot be set on OpenAI (Astra, Sol). Anthropic accepts only its default, 1.0. Every other route accepts 1.0 (xAI caps at 1).
- **Closest common setting:**
  - temperature 1.0 wherever a value can be sent;
  - Anthropic at its default, which is 1.0;
  - OpenAI with no temperature (its internal sampling, undocumented);
  - top_p at each provider's default;
  - no seed.

This is a scope decision for Ümit (§8.1), not something to adopt silently.

## 5. Load and concurrency, completion, failed and invalid answers

**Concurrency policy (proposed; A or B in §8.5):**
- **A (proposed):** within a model, one thing runs at a time.
  - The series run one after another.
  - Games and lesson calls run with 1 request in flight.
  - Every test, whether no-memory or T10, runs **alone** for that model, with **4 requests in flight**.
  - So the "before" and "after" tests run under the same policy.
  - Cost: the longest wall times (§6).
- **B:** the 5 series run in parallel. The tests then overlap other series' games, so the in-flight count differs between tests. Faster, but before and after are no longer under the same load.

**Recorded load, for every request:**
- the number of this experiment's requests in flight to the same server or route when it was sent;
- for local servers, the server's running and waiting request counts (vLLM `/metrics`) at the start and end of each test;
- the wall time of each test.

The provider-side load on API and subscription routes is not observable, and the page says so.

**Interleaving:** the 3 no-memory tests are run one before series 2, one after series 3 and one after series 5. Series 1 is the cost check. Drift during a model's run then appears in its spread.

**Failed requests** (no reply: transport or HTTP error, quota 429, timeout):
- The runner retries as in the leagues.
- A test position still unanswered is re-asked later with the same prompt and context, after quota waits if needed. A test counts as complete only with **200 of 200** positions answered.
- A game interrupted part-way: the series is replayed from game 1 with the same dice (the pilot rule). The aborted attempt's lessons are archived and not used.
- A lesson call that fails is retried until it returns.

**Invalid answers** (a reply that names no option: empty after thinking, cut at the output limit, or a non-letter):
- **In tests:**
  - not re-asked (re-asking would select answers);
  - counted per test and shown in the row;
  - left out of risks found, right safety and error rate, as on the site (shares over valid answers);
  - Ümit to confirm, or choose an alternative (§8.7).
- **In games:** a random legal play, as in the leagues; counted.
- **In lesson calls:** a reply with no line starting `- ` gives an empty lesson set for that game. It is kept, not re-asked, counted and shown.

## 6. Harness: what the pilot supports and what must change

**Already supported** (runner branch `learning-pilot`, e18ff59):
- Games: the match runner with `--model1-config`, `--fixed-rounds` and `--after-game`.
- The test: `jevgammon ask`, which uses the same `Player` as the leagues.
- Both work for every league chat route (Codex, Claude Code, Antigravity, xAI, OpenRouter, local vLLM), with subscription logins, pacers and retries.

**How chat models answer** (unchanged from the leagues; prompt `bg-v2`, League 2's option-order seed):
- **Subscription routes:** a provider-constrained single letter (JSON schema, or Gemini's enum).
- **OpenAI-compatible routes:** reasoning first, then the most probable letter (`answer` or `prefill` readout).
- Positions with more than 26 legal plays are asked in groups (32 of the 200).

**Where the lessons go:** the runner appends `prompt_note` / `prompt_note_file` to the play call's system prompt for every LLM route (`llm::play_system`), as in the pilot.

**Changes needed:**
1. **The lesson call for every route.** `pilot.py` `chat()` posts only to spark3's vLLM, with a Gemma-only body. Add a runner subcommand that sends one free-text request (no answer schema) through the player's own route, login and reasoning setting, and returns text, usage and time.
2. **Output cap for lessons.** For reasoning models, 400 output tokens would be used up by thinking. Proposed: the route's league cap, plus the pilot's cut rule (5 lessons, 150 words), with every cut counted (§8.8).
3. **Cygnet.** It plays through the decision-service shim (`/v1/systemone`), which ignores `prompt_note`. **No lessons result for Cygnet until it is verified that the lessons reach its decision request.** The check: the stored request to the underlying vLLM contains the note, and the empty-note request is byte-identical to the league's. Two different changes are possible:
   - (a) a note field in the shim; the setup stays "Cygnet" only if the empty-note request is unchanged;
   - (b) a different local adapter (Gemma 4 12B via `local/`). **This is a changed setup, not the leaderboard's Cygnet row**, so it would be a new, separately labelled row.

   The lesson call goes to the underlying Gemma 4 12B chat endpoint. Decision §8.9.
4. **Make `pilot.py` model-generic, as a new script.**
   - The player config comes from `v3.db` `players.settings` of the leaderboard setup, unchanged except `name`, `parallel` and `prompt_note_file`.
   - Remove the hard-coded Gemma name, server, `CONTEXT_LIMIT` and tokenizer.
   - Arms: lessons only. `CHECKPOINTS = (10,)`. `SERIES = 5`.
5. **The no-memory runs.** `ask --repeats 3` (or three setup names). `eval_answers` currently reads only `repeat = 1`.
6. **Policies:** the §5 concurrency policy, load recording, re-asking of failed positions, completion checks and the verdict gate.
7. **Cost.**
   - Record `cost_usd` from the runner plus the lesson calls (the pilot hard-codes $0).
   - Per-model cap.
   - OpenRouter `/credits` check before every series.
   - A hard stop after series 1 that waits for Ümit's approval.
8. **Aggregates and page:**
   - per model: before, after, change, spread, invalid/failed counts, load record, completion state and yes/no;
   - the new page "Did they improve?" under Experiments (`tools/site`);
   - the pilot row as in §3.
9. **Separate databases** (`smoke/improve*.db`). The pilot's leakage rule and `score_games.py` stay unchanged.

## 7. Workload, cost and time per model

**Workload per model:**
- games: 50 games × the model's own decisions per game against GNUbg weak in valid league matches (`v3.db`, 18–30);
- tests: 1,600 answers (5 T10 × 200 + 3 no-memory × 200);
- lessons: 50 calls.

Answers come to 2,500–3,100 per model, plus 50 lesson calls, consistent with Ümit's "about 2,800". HTTP requests are 3,000–7,300: more because of groups, two-step local reasoning models, and retries.

**Cost:** tokens per decision × price from `v3.db` (these reproduce the site's $ per 1,000 decisions), plus the pilot-measured extra input:
- test prompts ×1.17;
- lessons in games +690 tokens per request;
- lessons at T10 +1,600 per request;
- each lesson call about 3,600 input tokens plus (200 + the model's reasoning tokens) output.

Billed: OpenRouter only. Subscriptions are $0 billed and use quota, shown as API-equivalent. Local runs are $0 API spend; local compute is not estimated.

**Time:** league mean seconds per request. The league measured these under load: up to 24 sequences on local servers. So the local times are likely upper bounds under policy A [INFERENCE]. Each series includes about 0.35 h of scoring and engine overhead.

| Order | Model | Setting | Route | Blocker | Answers (+50 lesson calls) | HTTP requests | $ billed / API-equivalent | 1-series check $ (list) | 1 series | Wall, policy A (serial) | Wall, policy B (parallel) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| L1 | Cygnet (Gemma 4 12B) | – | local GPU (shim) | GPU; verified change first | 2,500 | 3,025 | $0 / – | – | 0.5 h | 2.3 h | 0.5 h |
| L2 | Gemma 4 31B | on | local GPU | GPU | 2,715 | 7,218 | $0 / – | – | 16 h | 87 h | 24 h |
| L3 | Qwen3.8-27B | low | local GPU | GPU | 2,665 | 6,846 | $0 / – | – | 21 h | 119 h | 33 h |
| L4 | LFM2.5-24B-A2B | on | local GPU | GPU | 2,865 | 7,298 | $0 / – | – | 34 h | 186 h | 50 h |
| A1 | Qwen3.8 Flash | off | OpenRouter | credit | 2,625 | 3,305 | $2.30 / $2.30 | $0.35 | 0.7 h | 3.5 h | 0.8 h |
| A2 | GLM-5.3 | low | OpenRouter | credit | 2,615 | 3,345 | $22 / $22 | $3.35 | 0.6 h | 3.3 h | 0.8 h |
| A3 | Kimi K3.1 Pro | off | OpenRouter | credit | 2,840 | 3,770 | $35 / $35 | $5.34 | 0.7 h | 3.5 h | 0.8 h |
| A4 | DeepSeek V4.1 Flash | low | OpenRouter (Fireworks) | credit | 2,735 | 3,742 | $44 / $44 | $6.96 | 6.6 h | 37 h | 9.9 h |
| A5 | GPT-6.1 Sol | high | ChatGPT subscription | weekly limit until 11-13 11:38 UTC | 2,940 | 4,313 | $0 / $52 | $8.23 | 2.1 h | 12 h | 3.0 h |
| A6 | Gemini 3.8 Flash | high | Antigravity subscription | none (fits the quota) | 2,650 | 3,495 | $0 / $65 | $10.03 | 1.8 h | 10 h | 2.5 h |
| A7 | Claude Sonnet 5.5 | high | Claude Code subscription | quota unknown | 2,740 | 3,639 | $0 / $65 | $10.10 | 1.1 h | 6 h | 1.4 h |
| A8 | Claude Opus 5.5 | high | Claude Code subscription | quota unknown | 2,965 | 3,964 | $0 / $129 | $20.25 | 1.2 h | 6.5 h | 1.6 h |
| A9 | Gemini 4 Argon | high | Antigravity subscription | none (fits the quota) | 2,770 | 3,900 | $0 / $202 | $31.59 | 6.4 h | 35 h | 9.5 h |
| A10 | GPT-6 Astra | high | ChatGPT subscription only | weekly limit until 11-13 11:38 UTC; paid API on hold | 3,100 | 4,576 | $0 / $239 | $37.85 | 2.3 h | 12 h | 3.1 h |
| A11 | Grok 4.7 | high | xAI subscription | quota unknown | 2,550 | 3,620 | $0 / $310 | $47.60 | 16.6 h | 93 h | 26 h |
| A12 | Claude Fable 5.1 | high | Claude Code subscription | quota unknown | 2,865 | 4,118 | $0 / $436 | $68.41 | 2.2 h | 12 h | 3.0 h |
| – | Gemma 4 31B (off), pilot | off | – | done | – | 0 | $0 | – | – | – | – |
| | **Total (16 models)** | | | | **44,140 (+800)** | **≈ 70,200** | **≈ $103 billed / ≈ $1,601 API-equivalent** | **$16 billed + $234 API-equivalent** | | **local ≈ 393 GPU-h; API ≈ 232 h** | **local ≈ 107 h; API ≈ 61 h** |

**Money and quota:**
- **OpenRouter:**
  - About $103 is needed against $13.42 on 8 Nov, which is shared with logic/turkce's Flash runs.
  - The four 1-series checks need $16.00.
  - The balance is re-checked at each go.
  - A top-up (Can) is needed before the full OpenRouter runs.
- **Subscriptions, API-equivalent:**
  - Claude about $630 (Fable $436, Opus $129, Sonnet $65);
  - xAI about $310;
  - OpenAI about $291 (only after the 11-13 reset);
  - Google about $266, inside the probed Antigravity weekly quota of about $1,800.

**GPU schedule (8 Nov):**
- The compactor holds bariton GPUs 1 and 2 for about 1 day (#2958).
- GPU 0 is claimed this evening.
- GPU 3 is never used.
- spark3 is LearningPilot's until Part 1 ends.
- **No local GPU is free for Part 2 now.**
- Earliest local start: when the compactor releases GPUs 1–2 (about 9 Nov) or when spark3 is free after Part 1, through the bus claim with the owner.
- Under policy A, the four local models take about 393 GPU-hours, or about 8 days on two GPUs. Under policy B, about 107 h (about 2–3 days on two GPUs).

**Cost check:**
- Series 1 of each API model: 10 games, 10 lesson calls and its T10 test.
- Afterwards, the measured $, tokens and time go to Ümit.
- Series 2–5 and the 3 no-memory tests run only after **Ümit's approval**.

**Proposed order** (local first, then cheapest API-equivalent; blocked models wait):
1. Gemma 4 31B (on), Qwen3.8-27B, LFM2.5, plus Cygnet only after its verified change. They wait for GPUs.
2. Qwen3.8 Flash, GLM-5.3, Kimi K3.1 Pro, DeepSeek V4.1 Flash.
3. Gemini 3.8 Flash, Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, Grok 4.7, Claude Fable 5.1.
4. GPT-6.1 Sol and GPT-6 Astra (high), after 2026-11-13 11:38 UTC.

If no GPU is free when Part 1 ends, Ümit decides whether the API phase may start before the local one (§8.11).

## 8. Open decisions for Ümit before pre-registration

1. **Sampling (scope or exception).**
   - A common seed is impossible on OpenAI, Anthropic, xAI, Fireworks and Moonshot.
   - Temperature cannot be set for Astra and Sol.
   - Anthropic accepts only 1.0.
   - Choose:
     - (a) the closest common setting: temperature 1.0 where it can be sent, provider defaults otherwise, no seed. Stated on the page as an exception to "same settings".
     - (b) the same plus a seed where accepted. Not the same for all.
     - (c) narrow the scope to routes that accept the chosen setting.
   - Part 1's result informs this choice.
2. **Spread** = the observed max − min of the 3 no-memory runs (risks found, points), with no floor. **Open option, not proposed:** a minimum spread (for example 2 points), so a model with a 0 spread cannot pass on a one-position change. This would add a condition to the rule and is Ümit's call.
3. **"after"** = the mean of the 5 T10 tests. **"before"** = the mean of the 3 no-memory tests, interleaved as in §5. Confirm.
4. **Lessons-condition games count nowhere:** not in the leagues, the leaderboard or the rule. They appear only as the source of the lessons, with error rate and wins as descriptive notes.
5. **Concurrency policy:** A (serial, tests alone at 4 in flight; proposed, slower) or B (parallel series; the load differs between tests, recorded but not equal).
6. **Gemma pilot row:**
   - the original pre-registered verdict (not met) plus "not comparable (different design)" in the new rule's column (proposed);
   - whether any exploratory comparison appears separately at all.
7. **Invalid answers in tests:**
   - (i) left out of the shares, as on the site, and counted (proposed);
   - or (ii) kept in the denominators as not-right calls;
   - optionally withhold a verdict above an invalid share that Ümit sets.
   - Failed requests are always re-asked until 200 of 200 (§5).
8. **Lesson call settings:** the model's leaderboard reasoning setting; the route's league output cap instead of 400 tokens for reasoning models; the pilot's cut rule.
9. **Cygnet:**
   - (a) a shim note, which keeps the row only if the empty-note request is unchanged and verified;
   - (b) a new local adapter, which is a new labelled row, not Cygnet's;
   - (c) leave it out, with the reason on the page.
10. **DeepSeek V4.1 Flash:** OpenRouter → Fireworks ($44 billed), or leave it out. The Vision-Exp checkpoint on spark2 is never substituted.
11. **Order:** if GPUs are not free when Part 1 ends, may the API phase start first?
12. **Astra:** subscription only, after the reset on 2026-11-13 11:38 UTC; the paid-API hold stands. Which goes first on the ChatGPT allowance: the Astra (high) re-ask or this experiment?
13. **Spending approvals:**
    - an OpenRouter top-up (Can), re-checked at go time;
    - Ümit's approval after each API model's 1-series check;
    - Claude and xAI quota headroom is unknown, and the checks measure it.
