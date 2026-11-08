# Did they improve? Plan draft (2026-11-08)

**DRAFT. Not the pre-registration yet.** It becomes one only after Ümit/Zeki settle section 7, and it is committed and published (rule, lesson prompt, model list, and "Results will be published whichever way they go.") before the first model call.

The brief is Ümit's (bus #2954), consolidated in #2955, which wins where they differ. This draft follows the learning pilot's plan (`mailbox/Learning pilot - plan 2026-11-07.md`) and its results (`mailbox/Learning pilot - results 2026-11-07.md`).

How the draft was made: no model call, no spend, no GPU, no service claim. The inputs were:
- read-only queries of `v3.db`;
- the live leaderboard (8 Nov 2026, 08:20 UTC data);
- the pilot's own files;
- read-only checks: OpenRouter `/api/v1/credits`, spark2's `docker ps` and `/v1/models`, and bariton's `nvidia-smi`.

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
| 6 | DeepSeek V4.1 Flash (on) | DeepSeek | low | Until 2026-10-20 20:09 UTC: OpenRouter → Fireworks. After that: our own SGLang, V4.1-Flash-1017 checkpoint, TP4 on all 4 bariton GPUs | **Route decision needed (§7.9).** Bariton TP4 is impossible: GPU 3 (GPU-e4f2a538) is faulty and never used. spark2 serves `deepseek-v4-flash-dspark` (DeepSeek-V4-Flash-Vision-Exp: vLLM TP2, nvfp4 KV), a **different checkpoint**. OpenRouter Fireworks works but is billed. |
| 7 | Grok 4.7 (on) | xAI | high | xAI subscription (OMP `xai-oauth`) | Credentials present. Quota unknown. |
| 8 | Claude Sonnet 5.5 (high) | Anthropic | high | Claude Code subscription | Same as Fable. |
| 9 | Gemini 3.8 Flash (high) | Google | high | Antigravity subscription | Same as Argon. |
| 10 | Kimi K3.1 Pro (off) | Moonshot | off | OpenRouter → moonshotai/mxfp4 | **OpenRouter credit is $13.42** ($155.00 total − $141.58 used). |
| 11 | Gemma 4 31B (on) | Google | on | local vLLM (bariton RTX PRO 6000; GB10 for a while) | Needs a GPU claim. The pilot was Gemma (**off**); the leaderboard setting is (on). spark3 is LearningPilot's until Part 1 ends. |
| 12 | Qwen3.8-27B (on) | Alibaba (Qwen) | low | local vLLM (bariton) | Needs a GPU claim. |
| 13 | GLM-5.3 (on) | Z.ai | low | OpenRouter → Fireworks | OpenRouter credit (as Kimi). |
| 14 | Qwen3.8 Flash (off) | Alibaba (Qwen) | off | OpenRouter → Alibaba | OpenRouter credit (as Kimi). |
| 15 | Cygnet (Gemma 4 12B) | Google | – | local: the Cygnet shim (one-token letter readout) over vLLM | Needs a GPU claim. Its decisions go through a **decision-service route**, so the harness needs a change (§5). |
| 16 | LFM2.5-24B-A2B (on) | Liquid AI | on | local vLLM (bariton) | Needs a GPU claim. |
| – | Gemma 4 31B (off): **pilot (different design)** | Google | off | spark3 vLLM | Done (pilot). No new calls. |

**Bariton now:**
- GPUs 0 and 2 are empty.
- GPU 1 holds someone's vLLM (34.7 GB).
- GPU 3 is never used.

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

**Improved (to publish before the first call):** both of these must hold:
- risks found change > the model's own retest spread (§7.2);
- right safety change ≥ −5 points.

Error rate is shown, but it is not part of the rule.

**Page "Did they improve?" (under Experiments):**
- One row per model: maker, setting, risks found before → after, change, right safety before → after, error rate before → after, the model's own retest spread, and yes/no.
- Rows are sorted by the change in risks found.
- Tapping a row shows its lessons.
- Gemma pilot row: "pilot (different design)".
- Decision models are listed as "not tested: cannot write lessons".
- Numbers go live as each model finishes. A model gets no verdict text until all 5 of its series are done.
- Before the first call, the page shows the rule, the lesson prompt, the model list and "Results will be published whichever way they go."

**Order:**
1. Part 1 settles the sampling settings.
2. Local models (§6).
3. API and subscription models, cheapest first.
4. For each API model: 1 series as a cost check, then report $ and time before running the rest.

## 4. How chat models are asked (the league format, unchanged)

Chat models answer through the runner's players exactly as in the leagues (`src/players/llm.rs` `constrained_request`, prompt `bg-v2`, League 2's option-order seed). The answer is a letter, mapped to a play through the seeded option order:

| Route | How the letter is read | Requests per decision |
|---|---|---|
| Codex / xAI (Responses API) | `text.format` JSON schema with one letter; reasoning effort set | – |
| Claude Code | `output_config` JSON schema; effort set | – |
| Antigravity | `responseMimeType text/x.enum` over the letters; thinkingLevel set | – |
| OpenAI-compatible (OpenRouter, local vLLM) | Reasoning first, then the most probable letter: `answer` readout from the answer's logprobs, or `prefill` | 2 |

- **Groups:** positions with more than 26 legal plays are asked in groups (32 of the 200 test positions).
- **Requests per decision in `v3.db`** (attempts included): 1.2–1.5 for API and subscription routes, and 2.5–2.6 for local reasoning models (two-step).
- **Invalid answers** (no option named): in games, a random legal play is made; in tests, the answer is left out of the shares and counted.

**Where the lessons go:**
- The runner appends `prompt_note` / `prompt_note_file` to the play call's system prompt after a blank line (`llm::play_system`). This holds for every LLM route, including the two-step compatible call.
- For Claude Code, it follows the required Claude Code identity block.
- This is the same placement as in the pilot.

## 5. Harness: what the pilot supports and what must change

**Already supported** (runner branch `learning-pilot`, e18ff59):
- Games: the match runner with `--model1-config`, `--fixed-rounds` and `--after-game`.
- The test: `jevgammon ask`, which uses the same `Player` as the leagues.
- Both work for every league chat route (Codex, Claude Code, Antigravity, xAI, OpenRouter, local vLLM), with subscription logins, pacers and retries.

**Changes needed:**
1. **The lesson call for every route.** `pilot.py` `chat()` posts straight to spark3's vLLM with a Gemma-only body (`enable_thinking: false`, temperature 1.0, `max_tokens` 400). Add a runner subcommand that sends one free-text request (no answer schema) through the player's own route, login and reasoning setting, and returns text, usage and time. Subscription logins live only in the runner (Rust), so Python cannot reach them.
2. **Output cap for lessons.** For reasoning models, 400 output tokens would be used up by thinking: Anthropic `max_tokens` and OpenAI output limits include reasoning. Proposed: the route's league cap (none for Codex and Antigravity, 32,000 for Claude, the configured value for local). The 5-lesson / 150-word limit is enforced by the pilot's cut rule, and every cut is logged. Decision §7.6.
3. **Cygnet.** It plays through the decision-service shim (`/v1/systemone`, one-token readout), which ignores `prompt_note`. Two parts:
   - the shim needs a system-note field, or Cygnet is played through its vLLM as `local/` (but that changes its setup);
   - the lesson call goes to the underlying Gemma 4 12B vLLM chat endpoint.

   Decision §7.10.
4. **Make `pilot.py` model-generic, as a new script.**
   - The player config comes from `v3.db` `players.settings` of the leaderboard setup, unchanged except `name`, `parallel` and `prompt_note_file`.
   - Remove the hard-coded Gemma name, server, `CONTEXT_LIMIT` and tokenizer. The Gemma tokenizer was only needed for records/budget; report provider-counted tokens instead.
   - Arms: lessons only. `CHECKPOINTS = (10,)`. `SERIES = 5`.
5. **The no-memory runs.** `ask --repeats 3` (or three setup names). `eval_answers` currently reads only `repeat = 1`.
6. **Cost.**
   - Record `cost_usd` from the runner (turns/answers) plus the lesson calls. The pilot hard-codes $0.
   - Add a per-model cap and an OpenRouter credit check before each series (as in the late entries).
   - Subscription runs log API-equivalent cost.
7. **Concurrency** must be fixed and the same for every test of a model (§7.5). The pilot's T0 ran with 4 requests in flight and its later tests with 1, and that difference was never measured.
8. **Aggregates and page.**
   - New aggregates: before, after, change, spread, invalid/failed counts and yes/no, per model.
   - A new page "Did they improve?" under Experiments (`tools/site`).
   - Live per-model numbers, the verdict only after 5 series, and the lessons beside their games.
9. **Separate databases** (`smoke/improve*.db`). The pilot's leakage rule and `score_games.py` stay unchanged.

## 6. Workload, cost and time per model

**Workload per model:**
- games: 50 games × decisions per game. Taken from `v3.db`: the model's own decisions per game against GNUbg weak in valid league matches (18–30). The pilot measured about 24 for Gemma (off) against Beginner.
- tests: 1,600 answers (5 T10 × 200 + 3 no-memory × 200);
- lessons: 50 calls.

**Answers per model** (decisions + test answers) are 2,500–3,100, plus 50 lesson calls. That is consistent with Ümit's "about 2,800 calls per model". HTTP requests are 3,000–7,300: more than answers because of the groups, the two-step local reasoning models, and retries.

**Cost, from each model's `v3.db` league averages:**
- Base: input and output tokens per decision × its configured price. These reproduce the site's $ per 1,000 decisions; for example, Astra (high) gives $59.36.
- Extra input, from the pilot:
  - the test prompts are ×1.17 the league's;
  - lessons in the games add about 690 tokens per request;
  - lessons at T10 add about 1,600 per request;
  - each lesson call is about 3,600 input tokens plus (200 + the model's reasoning tokens per decision) output.
- **Billed:** OpenRouter only. Subscriptions are $0 billed and use quota, shown as API-equivalent. Local runs are $0 API spend; local compute is not estimated.

**Time:**
- Seconds per request: the league mean of `request_ms`, measured under league load.
- One series = 10 games + 10 lesson calls + one T10 test with 4 requests in flight + about 0.35 h of scoring and engine overhead (pilot: about 1 h per series for Gemma off).
- Wall time assumes the 5 series of a model run in parallel, plus the 3 no-memory runs with 4 in flight.
- The local reasoning models' times come from heavily loaded league servers (24 sequences), so they are rough [INFERENCE].

| Order | Model | Setting | Route | Blocker | Decisions | Answers (+50 lesson calls) | HTTP requests | $ billed / API-equivalent (list) | 1-series check $ (list) | 1 series | Wall (5 series in parallel + 3 no-memory runs) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| L1 | Cygnet (Gemma 4 12B) | – | local GPU (shim) | GPU claim; shim note change | 900 | 2,500 | 3,025 | $0 / – | – | 0.5 h | 0.5 h |
| L2 | Gemma 4 31B | on | local GPU | GPU claim (or spark3 after Part 1) | 1,115 | 2,715 | 7,218 | $0 / – | – | 16 h | 24 h |
| L3 | Qwen3.8-27B | low | local GPU | GPU claim | 1,065 | 2,665 | 6,846 | $0 / – | – | 21 h | 33 h |
| L4 | LFM2.5-24B-A2B | on | local GPU | GPU claim | 1,265 | 2,865 | 7,298 | $0 / – | – | 34 h | 50 h |
| A1 | Qwen3.8 Flash | off | OpenRouter | credit | 1,025 | 2,625 | 3,305 | $2.30 / $2.30 | $0.35 | 0.7 h | 0.8 h |
| A2 | GLM-5.3 | low | OpenRouter | credit | 1,015 | 2,615 | 3,345 | $22 / $22 | $3.35 | 0.6 h | 0.8 h |
| A3 | Kimi K3.1 Pro | off | OpenRouter | credit | 1,240 | 2,840 | 3,770 | $35 / $35 | $5.34 | 0.7 h | 0.8 h |
| A4 | DeepSeek V4.1 Flash | low | OpenRouter (Fireworks) | credit; route decision §7.9 | 1,135 | 2,735 | 3,742 | $44 / $44 | $6.96 | 6.6 h | 9.9 h |
| A5 | GPT-6.1 Sol | high | ChatGPT subscription | weekly limit until 11-13 11:38 UTC | 1,340 | 2,940 | 4,313 | $0 / $52 | $8.23 | 2.1 h | 3.0 h |
| A6 | Gemini 3.8 Flash | high | Antigravity subscription | quota (fits) | 1,050 | 2,650 | 3,495 | $0 / $65 | $10.03 | 1.8 h | 2.5 h |
| A7 | Claude Sonnet 5.5 | high | Claude Code subscription | quota unknown | 1,140 | 2,740 | 3,639 | $0 / $65 | $10.10 | 1.1 h | 1.4 h |
| A8 | Claude Opus 5.5 | high | Claude Code subscription | quota unknown | 1,365 | 2,965 | 3,964 | $0 / $129 | $20.25 | 1.2 h | 1.6 h |
| A9 | Gemini 4 Argon | high | Antigravity subscription | quota (fits) | 1,170 | 2,770 | 3,900 | $0 / $202 | $31.59 | 6.4 h | 9.5 h |
| A10 | GPT-6 Astra | high | ChatGPT subscription only | weekly limit until 11-13 11:38 UTC; paid API on hold | 1,500 | 3,100 | 4,576 | $0 / $239 | $37.85 | 2.3 h | 3.1 h |
| A11 | Grok 4.7 | high | xAI subscription | quota unknown | 950 | 2,550 | 3,620 | $0 / $310 | $47.60 | 16.6 h | 26.3 h |
| A12 | Claude Fable 5.1 | high | Claude Code subscription | quota unknown | 1,265 | 2,865 | 4,118 | $0 / $436 | $68.41 | 2.2 h | 3.0 h |
| – | Gemma 4 31B (off), pilot | off | – | done | – | – | 0 | $0 | – | – | – |
| | **Total (16 models)** | | | | **18,540** | **44,140 (+800)** | **≈ 70,200** | **≈ $103 billed / ≈ $1,601 API-equivalent** | **$16 billed + $234 API-equivalent** | | |

**Money and quota:**
- **OpenRouter:** about $103 is needed against **$13.42 left**.
  - Even the four 1-series checks ($16.00) do not fit.
  - Qwen3.8 Flash + GLM + Kimi checks ($9.04) fit.
  - Can needs to top up about $90–110 before the full OpenRouter runs.
- **Subscriptions, API-equivalent:**
  - Claude about $630 (Fable $436, Opus $129, Sonnet $65);
  - xAI about $310;
  - OpenAI about $291 (Astra $239, Sol $52; only after the 11-13 reset);
  - Google about $266, inside the probed Antigravity weekly quota of about $1,800.

**Time:**
- **Local:** about 107 GPU-hours in sequence. On the two free bariton GPUs that is about 3 days. Gemma (on) could use spark3 after Part 1.
- **API and subscriptions:** most models take 1–3 h of wall time. DeepSeek and Argon take about 10 h each, and Grok about 26 h, because their reasoning is slow (mean 79 s, 74 s and 233 s per request).

**Cost check:** series 1 of each API model, which is 10 games, 10 lesson calls and its T10 test. After it, send the measured $ and time, and wait for a go before series 2–5 and the 3 no-memory runs.

**Proposed order** (local first, then cheapest API-equivalent; blocked models skipped until free):
1. Cygnet, Gemma 4 31B (on), Qwen3.8-27B, LFM2.5 (two GPUs in parallel);
2. Qwen3.8 Flash, GLM-5.3, Kimi K3.1 Pro, DeepSeek V4.1 Flash;
3. Gemini 3.8 Flash, Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, Grok 4.7, Claude Fable 5.1;
4. GPT-6.1 Sol and GPT-6 Astra (high), after 2026-11-13 11:38 UTC.

## 7. Open decisions before pre-registration (Ümit/Zeki)

1. **Sampling settings (from Part 1).** What each route lets us control, from the request bodies in `llm.rs`:

   | Route | Temperature | Seed |
   |---|---|---|
   | Codex, Claude Code, xAI | none sent (provider default) | none |
   | Antigravity | 1.0 | none |
   | OpenRouter and local vLLM | 1.0 | none |

   - Reasoning endpoints on the subscriptions generally do not take temperature or seed [INFERENCE; unverified per route]. With Claude's thinking on, the temperature is fixed at 1.
   - So "same sampling settings for all" can only mean **each model at its league request settings**: temperature 1.0 where the route takes one, the provider default elsewhere, no seed.
   - Unless Part 1 finds that a seed or a lower temperature matters: that could only be applied on local and OpenRouter routes, and it would change those setups away from the leaderboard's.
   - The one-token-readout models (Cygnet; the pilot's Gemma off) pick the argmax, so temperature does not change their choice.
2. **"Own retest spread."**
   - **Proposed:** the range (max − min) of the model's 3 no-memory runs' risks found, in points.
   - Alternatives: the SD of the 3 runs, or a 95% interval (both unstable with 3 runs).
   - Also decide a **floor**. A model with near-deterministic answers can have a spread of 0, and then +1 point (one position) would count. Proposed: change > max(spread, 2 points).
3. **"after"** = the mean over the 5 series' T10. **"before"** = the mean of the 3 no-memory runs. **Proposed:** run the no-memory runs **interleaved**: one before series 2, one after series 3, one after series 5 (series 1 is the cost check). That way, provider drift during the run shows up in the spread.
4. **Games in the lessons condition count nowhere.** They are not in the leagues, the leaderboard, `v3.db` or the rule. They are shown only as the source of each lesson, with error rate and wins as descriptive notes per model.
5. **Concurrency:** every test of a model at the same number of requests in flight. **Proposed:** 4 for the no-memory runs and the T10 tests alike, and the 5 series in parallel.
6. **Lesson call settings:**
   - the model's leaderboard reasoning setting;
   - no 400-token cap for reasoning models (the route's league cap instead; §5 item 2);
   - the pilot's cut rule for more than 5 lessons or 150 words, with every cut counted and shown.
7. **Gemma pilot row ("pilot (different design)").** Proposed mapping:
   - after = the lessons arm's T10 mean over its **10** series: risks found 33.3, right safety 97.1, PR 46.4;
   - before = the mean of its **21** empty-context runs: the shared T0 (4 in flight) plus the budget arm's 20 tests (T5 and T10; the budget context was empty at all 100 points, 1 in flight). That gives 28.1, 96.8 and 54.4;
   - change = **+5.2** risks found, **+0.3** right safety, **−8.0** PR.

   Spread:
   - The range over the 21 runs is **6.0** points (24–30; SD 1.4 over the 20 budget runs). Under the range rule the row is **No**.
   - A 3-run-equivalent range (about 1.7 SD ≈ 2.4 points) would make it **Yes**.

   Decide which, and show the pilot's own pre-registered verdict (+8.3 vs T0 against a ≥ +10 rule: not met) next to it. The +8.3 and the +5.2 differ only in the baseline: one T0 run vs 21 runs. Alternative: use LearningPilot's Part 1 retests of Gemma (off) as the pilot row's "before".
8. **Gemma 4 31B (on)** is the leaderboard setting and gets a full new run. The pilot row is Gemma (off) and stays as a separate row.
9. **DeepSeek V4.1 Flash (on): which route?**
   - (a) OpenRouter → Fireworks, as in its first league days ($44 billed). **Proposed.**
   - (b) spark2's `deepseek-v4-flash-dspark`. It is a different checkpoint (V4-Flash-Vision-Exp), so it would be another model's row. It also needs the owner's OK.
   - (c) Bariton SGLang TP4: not possible (GPU 3).
10. **Cygnet:** either add a system note to the shim and send its lessons to the underlying vLLM, or run Gemma 4 12B via `local/`, which changes its setup. Or leave it out with a reason on the page.
11. **GPT-6 Astra (high):** subscription only, after the ChatGPT reset on 2026-11-13 11:38 UTC. Zeki/Can's paid-API hold stands. The ChatGPT allowance is also needed for the Astra (high) re-ask (about $63 API-equivalent). Who goes first?
12. **Invalid answers:** left out of the shares as on the site, and counted per run. Argon had 98 invalid answers in 1,762 league decisions (5.6%). Proposed: flag a row whose test runs have more than 5% invalid.
13. **Not applicable here:** the pilot's decision-line vs whole-game budget question. There is no records or budget arm.
14. **Money:** an OpenRouter top-up of about $90–110 (Can), and Claude/xAI quota headroom (unknown; the 1-series checks measure it). Who approves each model's go after its cost check?
