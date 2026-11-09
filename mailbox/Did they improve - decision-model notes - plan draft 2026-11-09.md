# Did they improve? Decision models (Part 3): plan draft (2026-11-09)

**Draft, not the pre-registration.** Nothing was called, bought, started or stopped to write it; the running lanes, the live plan (`mailbox/Did they improve - plan 2026-11-08.md`, sha256 85a970d0…8542) and the live page are untouched. The pre-registration will be a separate addendum, committed and shown on the page (rule, writer, arms) before the first call.

Sources: Ümit #3632 (the part) and #3660 (the second arm), Zeki #3638 (writer, label, preflight, context check, ledger) and #3662 (second-arm rules), the live plan, `v3.db` (read-only), the improve run files, the server and client code named below, and the makers' docs (read 2026-11-09).

## 1. What this part asks

Per decision model on the leaderboard, at its leaderboard setting: does it take risks better on the pilot's 200-position test after 10 games against GNUbg weak with a block of text about its own earlier games in its prompt, than with no block? Two arms, each judged on its own:

- **Arm N, helper-written notes → decision player.** After each game a fixed helper model (the writer) reads the decision model's graded game record and writes notes with the pilot's lesson prompt and limits. The page says: *helper-written notes, not self-written learning* (Zeki #3638).
- **Arm W, worst mistakes (no writer).** After each game a fixed script puts the 5 costliest decisions of this series so far (GNUbg grades) into the prompt as solved examples (Ümit #3660).

Same as the chat models: 5 series × 10 games against GNUbg weak (GNU Backgammon 1.08 Beginner), the pilot's dice s01–s05 (mirrored pairs), the same 200 test positions (test-set sha256 6c92e741…18e6), 3 empty runs, T10 after each series, and the rule unchanged: **Improved** = risks found (mean of 5 T10) − risks found (mean of 3 empty runs) > max(range of the 3 empty runs, 5 points), and right safety change ≥ −5 points. Verdicts are reported **per arm**, under the same rule; neither arm is picked as "the" result (Zeki #3662).

Each arm has its **own games**: same dice schedules, never the other arm's games, decisions or trajectories (Zeki #3662). Notes and examples reset at the start of every series. Games count nowhere (no league, no leaderboard).

## 2. The crux: do the notes reach the model?

A decision request is System One JSON: `state` (free text: the league rules text, then this turn's score, board and dice, then the question), one `choice` question with `instructions` (free text) and `criteria` (option → description); OpenAI's Decisions API takes `input` instead of `state` (`src/players/decision.rs` `body()`). Free text can therefore go into the request on every route. What remained open was whether each service puts it into the model's tokens unchanged and uncut.

**Finding 1, our own runner (all routes):** `prompt_note` / `prompt_note_file` exist only for chat players. `llm::play_system` appends them to the chat system prompt (`jevgammon-improve/src/players/llm.rs:332-342`). The decision branch of `Player::build` builds `DecisionClient::new(http, service, model, base_url)` and never sees them (`src/players/mod.rs:491-497`), and `DecisionClient` builds the body from `state(req)` and `instructions(req)` alone. **A note set on a decision player is dropped without an error today.** This is why "Cygnet's layer never sees the lessons" (live plan §3): the cause is the runner, not Cygnet's shim. The shim copies `state` verbatim into the model's user turn (`cygnet/shim/decision_server.py:221`, `cygnet_shim.py:162-170`).

**Finding 2, the improve branch lacks the late-entry routes.** `jevgammon-improve` (`19921b4`) has the 15 older services. `baselabs`, `nace`, `drex-max`, `drex-local` and `reax`, and the decision-service budget ledger (`jevgammon-drex` `e58fc6c`), live in the late-entry branches (`jevgammon-reax` `acfd89c`).

**Finding 3, notes size.** Ümit's ~1,300 tokens is about the mean, not the worst case. On the 17 completed chat-model series, the notes context after game 10 measured **mean 1,473 and max 1,838 tokens** (Qwen3 tokenizer; max 9,535 bytes and 1,460 words). The cut rule bounds it at 10 × 150 words plus headers, about 1,560 words. The context check below uses a **2,000-token bound for Arm N**.

**Finding 4, the worst-mistakes block** (format in §5) measures **at most 249 tokens per example**. That is the league's own position block, measured over 11,265 distinct stored League 1 boards (min 108, median 145, p99 164, max 174 tokens), plus two plays and the loss line. With headers, 5 examples come to **≤ 1,300 tokens**; the context check uses a **1,350-token bound for Arm W**. Both bounds are Qwen3 counts. Each model's preflight (§6) replaces them with the exact serialized payload in that model's own tokenizer or usage count; nothing reuses another arm's figure (Zeki #3662).

**Proposed placement (open decision D3):** the block goes at the **start of `state`** (OpenAI: start of `input`), before the rules text. This is the decision-request equivalent of the chat arm's system-prompt placement. It stays away from the state's tail, where the dice and the question are. `instructions` and the options stay byte-identical to the league's. Header and delimiters for Arm N: the live plan's `=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===` … `=== END OF NOTES ===`. The intro line changes, because "Lessons you wrote for yourself" (`improve.py:85`) would be false here (D4).

**What "state is data" means for the result.** Decider v1.1/v1.2/Flash, Drex Max v1, Winnow and both REAX parts have a fixed system or ask prompt that says the state is data, not instructions (e.g. `autojev/model.py:107-108`, `pplx_decider/protocol.py:36-38`, `drex_max/model.py:111-116`, `winnow/native/protocol.h:56-57`, `reax knowline_server.py:66-67`). Notes can arrive intact and still be discounted by design. That is a property of the model, and part of what the test measures. The preflight proves **delivery** only; it need not prove use (Zeki #3638).

## 3. Models

Every decision row of the live leaderboard (the live plan's 22, late entries included), plus Cygnet (Ümit #3111 excluded it on a reason that Finding 1 shows was ours; D2). "Fits?" = largest league request of that model (the service's own reported input tokens, `v3.db` exchanges, valid matches) + the arm's bound (N 2,000 / W 1,350) + output allowance (0 for every route here: all read probabilities, none generates text; Cygnet's vLLM call is 1 token) ≤ the route's limit for one request or question.

Calls and money per model (§7 method): **N** = Arm N with its own 3 empty runs. **N+W** = both arms sharing one set of 3 empty runs (D1); separate empty runs add the "E" figure once more. Prices are $/1M input tokens; output is free on every route. Writer calls are not included here (§4: about $0.03 per model).

| # | Model (v3.db setup) | Maker | Route | Notes reach model? (evidence) | Fits? N / W (max league request + bound vs limit) | Est. decisions / requests (N; W adds ~2,000 decisions) | Est. $ N · N+W · E (list; billed where different) | GPU | Blocker |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mercury Decide | Inception | OpenRouter System One `openrouter.ai/api/v1/systemone`, `inception/mercury-decide` | **passes text (docs)**: OpenRouter TypeSafe-SDK guide, "implements TypeSafe's request and response shapes"; Inception: state/instructions "can be strings, JSON objects, or arrays" (openrouter.ai/docs/guides/community/typesafe-sdk.md, read 2026-11-09). Overflow behaviour not documented → **probe P1** | 27,535 + 2,000 / + 1,350 ≤ 65,536 (openrouter.ai/inception/mercury-decide): **fits / fits** | 2,600 / 2,600 | $0.23 · $0.42 · $0.04 at $0.02 (billed **on OpenRouter**: counts in the $110 / share ledger) | — | needs P1; budget ledger for this route (Finding 2) |
| 2 | Drex Max 1.1 | Nace.AI | Nace hosted `console.nace.ai/v1/systemone`, `drex-max-v1.1`, 25 options per request | **passes text (docs, explicit)**: "Drex passes it to the model as is"; unknown keys ignored; too long → `422` (console.nace.ai/docs/drex/api-reference/systemone, read 2026-11-09) | 5,204 + 2,000 / + 1,350 ≤ 262,144 (whole request, same page): **fits / fits** | 2,600 / 3,350 (1.27 requests per decision) | list $0.86 · $1.58 · $0.16; **billed $0.43 · $0.79 · $0.08** at the $0.03 launch price | — | Nace pre-send ledger is capped at $1.25 for both hosted Drex setups (league setting): both together need about $2.35 billed (D6) |
| 3 | Liquid d1-ultra | Liquid AI | `api.liquid.ai/decisions/v1/systemone` | **passes text (docs)**: "State: the context the model should evaluate. This can be plain text…" (docs.liquid.ai/lfm/models/d1.md, read 2026-11-09); overflow behaviour not documented → **P1** | 20,603 + 2,000 / + 1,350 ≤ 32,768 (OpenRouter listing; Liquid publishes none): **fits / fits** | 2,600 / 2,600 | $0.47 · $0.86 · $0.09 at $0.042 | — | needs P1 |
| 4 | Celeris-1 Decision | Celeris | `inference.celeris.ai/celeris-1-decision/v1/systemone` | **passes text (docs)**: "`state` can be a string or any other JSON value"; unknown field → `422` (docs.celeris.ai/decisions, read 2026-11-09) | 28,163 + 2,000 / + 1,350 ≤ 131,072 (docs.celeris.ai/models): **fits / fits** | 2,600 / 2,600 | $0.48 · $0.87 · $0.09 at our recorded $0.04 (docs now show $0.004: then a tenth) | — | identity: docs name `celeris-1.1-decision`; we send `celeris-1-decision` (answered 2026-11-07). The preflight must record the response's model field (D7) |
| 5 | Fastino GLiDE | Fastino | `api.fastino.ai/v1/systemone` (answers as `glide_v2`) | **passes text (docs)**: "Each rendered question prompt (`state` plus that question) must fit within 65,536 tokens"; over → `400`; extra field → `422` (docs.fastino.ai/inference/systemone.md, read 2026-11-09) | 27,515 + 2,000 / + 1,350 ≤ 65,536: **fits / fits** | 2,650 / 2,650 | $0.49 · $0.90 · $0.09 at $0.04 (docs; the league recorded no price) | — | — |
| 6 | SubQ Snap 1.1 | SubQ | `api.subq.ai/v1/systemone` | **passes text (docs)**: "`state`: the text, object, or array to evaluate"; over the limit → `400` (docs.subq.ai/endpoints/decisions-api, read 2026-11-09) | 21,968 + 2,000 / + 1,350 ≤ 393,216: **fits / fits** | 2,700 / 2,700 | $0.49 · $0.90 · $0.09 at $0.04 | — | — |
| 7 | Jev 1.13.0 | TypeSafe | `api.typesafe.ai/v1/systemone` | **passes text (docs)**: "State is the content you ask a System One model to evaluate"; over the limit → `400 max_tokens_exceeded` (docs.typesafe.ai/concepts/state.md, api/errors.md, read 2026-11-09). TypeSafe warns that "Accuracy falls as the state grows with content unrelated to the decision" | 26,116 + 2,000 / + 1,350 ≤ 32k per question (docs.typesafe.ai/models.md; 32,000 or 32,768 not stated): **fits / fits** | 2,600 / 2,600 | $0.52 · $0.96 · $0.10 at $0.042 | — | — |
| 8 | Jev 1.14.0 | TypeSafe | same | same | 27,898 + 2,000 = 29,898 / 29,248 ≤ 32k: **fits / fits** (tightest hosted) | 2,650 / 2,650 | $0.53 · $0.98 · $0.10 at $0.042 | — | — |
| 9 | SubQ Snap Preview | SubQ | `api.subq.ai/v1/systemone`, `subq-snap-preview` | **unknown**: no longer on docs.subq.ai/using-the-api/models (read 2026-11-09), though it answered on 2026-11-07 → **P1** | limit not published (1.1's is 393,216) | 2,650 / 2,650 | $0.62 · $1.14 · $0.12 at $0.05 | — | may be retired: if P1 fails, "not tested: route no longer served" |
| 10 | Drex 2.0 | Nace.AI | Nace hosted, `drex-v2.0`, 25 options per request | **passes text (docs, explicit)**, as row 2 | 5,017 + 2,000 / + 1,350 ≤ 131,072 state / 262,144 state + question: **fits / fits** | 2,600 / 3,350 | $0.84 · $1.55 · $0.16 at $0.06 billed | — | Nace ledger cap (D6) |
| 11 | GPT-6 Luna | OpenAI | Decisions API `api.openai.com/v1/decisions` (`input` + `questions`) | **passes text (docs)**: `input` is "Shared evidence for the questions: a text string…" (developers.openai.com/api/docs/guides/decisions, read 2026-11-09) | 24,150 + 2,000 / + 1,350 ≤ 922,000 max input (model page): **fits / fits** | 2,600 / 2,600 | $1.07 · $1.97 · $0.20 at $0.10 | — | — |
| 12 | Decider Flash v1.2 | Perplexity | local `pplx_decider_server.py` (`decider-v1.2.sh flash`), 25 options | **passes text (code)**: `protocol.py:176-189` "State:\n" + state; only `<|…|>` is escaped (`:149-152`) | 5,162 + 2,000 / + 1,350 ≤ 262,144 (`model.py:35`): **fits / fits** | 2,600 / 3,400 | $0 billed (list-price equivalent $0.15 · $0.27 · $0.03) | ~13 GiB | GPU |
| 13 | Decider v1.2 27B | Perplexity | local `decider-v1.2.sh 27b` | **passes text (code)**, as row 12 | 5,166 + 2,000 / + 1,350 ≤ 262,144: **fits / fits** | 2,600 / 3,300 | $0 (list eq. $0.28 · $0.52 · $0.05) | ~53 GiB | GPU |
| 14 | Decider v1.1 27B | Perplexity | local `decider.sh` (`autojev`) | **passes text (code)**: `autojev/model.py:98-103` "State:\n" + describe(state) | 5,168 + 2,000 = 7,168 / 6,518 ≤ 8,192 per question (`model.py:264,284-285`, then 422): **fits / fits** (1,024 tokens to spare) | 2,600 / 3,350 | $0 (list eq. $0.29 · $0.53 · $0.05) | ~49–52 GiB | GPU |
| 15 | Base Labs Elephant-1 | Base Labs | local `baselabs_server.py` (qev DecisionEngine + `serve.patch`, image `baselabs-serve:81ce62f`), 120 options | **passes text (code, high confidence)**: the state goes in the shared prefix (`serve.patch:226-238,252-254`). The renderer `qev.prompt.state_block` exists only inside the image → **zero-cost render check R** | 14,777 + 2,000 = 16,777 / 16,127 vs trained 16,384 (card) and engine refusal at 32,768: **N past the trained length, not refused; W fits** | 2,600 / 2,600 | $0 (list eq. $0.42 · $0.77 · $0.08 at Baseten's $0.035) | ~22 GB | GPU; D5 |
| 16 | Base Labs Mammoth-1 | Base Labs | local, as row 15 | as row 15 | 15,212 + 2,000 = 17,212 / 16,562 vs 16,384 trained / 32,768 refused: **past the trained length in both arms** | 2,650 / 2,650 | $0 (list eq. $1.25 · $2.28 · $0.23 at $0.10) | ~57–59 GB | GPU; D5 |
| 17 | Drex Max v1 | Nace.AI | local `drex_max_server.py` (Nace's `drex_max` @ e206b27), 25 options | **passes text (code)**: `drex_max/model.py:105-108`; `_text` returns strings unchanged | 5,135 + 2,000 / + 1,350 ≤ 16,384 (`model.py:26-45`, then 400): **fits / fits** | 2,650 / 3,450 | $0 (list eq. $0.89 · $1.63 · $0.16) | ~55 GB [inference: 27B bf16] | GPU |
| 18 | Drex 2.0 (local) | Nace.AI | local checkpoint `serve.py` (kev), 25 options | **passes text (code)**: `kev/api.py:107-123` render returns strings unchanged; `kev/model.py:116-119` rewrites only `<|name|>` | 5,065 + 2,000 / + 1,350 ≤ 16,384 (`KEV_CONTEXT`, `ContextOverflow` → 400): **fits / fits** | 2,500 / 3,250 | $0 (list eq. $0.81 · $1.49 · $0.15) | ~75 GB [inference: 70.2 GB weights] | GPU; whether it runs beside Drex 2.0 (D8) |
| 19 | Fastino GLiDE v1.2 (local) | Fastino | local `glide/server.py` (`glide-v12.sh`) | **passes text (code)**: `prompt.py:164-166` "Context:\n{state}"; no system prompt | 25,372 + 2,000 / + 1,350 ≤ 40,000 (`server.py:48`, then 422): **fits / fits** | 2,600 / 2,600 | $0 (no list price) | 53.6 GiB | GPU |
| 20 | REAX 1.3 | REAX Labs | local `reax13/serve.py` (Docker, reax-engine @ ff8f595) | **passes text (code)**: G `knowline_server.py:132-133`, Q `d3_format.py:149-159`. **Caveat:** part G reads requests of ≤ 3,000 tokens twice (`backend.py:42`, `knowline_layout.py:182-194`); with the block every request is over 3,000, so short requests switch from read-twice to read-once | 57,867 + ~10,000 bytes ÷ 4 ≈ 17,000 proxy tokens ≤ 32,000 (`reax13_engine.py:21-24`): **fits / fits** | 2,650 / 2,650 | $0 (no list price) | ~62 GB | GPU; D5 (layout switch); the server's EPERM / no-new-privileges history (REAX status 2026-11-07) |
| 21 | Open-Jev 27B v1.1 | (Open-Jev) | local `open-jev.sh`, one prompt per candidate | text would pass verbatim (`jev/api.py:83` "Context:\n{state}"), but **no silent truncation: 422** (`jev/model.py:225-226`) | state up to ~2.4–2.9k tokens + question + option per candidate prompt, limit **4,096** (`open-jev.sh:15` `--max-length 4096`, checkpoint `model.json`). +2,000 / +1,350 → over on most or all requests | — | — | — | **not tested: context too short** (both arms) |
| 22 | Winnow-12B | EldanRing | local `winnow-inference:d4631fb`, 40 options | **passes text (code), JSON-escaped**: `protocol.h:66` "State:\n" + `safe_data(state)` | 6,807 + 2,000 = 8,807 > 8,192 (`winnow.sh:17-18`, then 400); W 6,807 + 1,350 = 8,157: 35 tokens under the limit by the Qwen bound, so the exact Gemma-tokenizer count decides | — / 2,900 if W fits | $0 | 14.6 GiB | **N: not tested: context too short.** W: decided by the exact count in the preflight (else the same reason). A smaller option cap (~28) would be a changed setting (D5) |
| 23 | Clef | (Clef) | local `clef/server.py`, 110 options | text passes, but **the tail of the state is cut silently**: `joint_schema_model.py:170` `state_ids[: max_length - fixed_length]` | 15,194 + 2,000 = 17,194 / 16,544 > 16,384 (`:547`): the cut removes the dice and the question | — | — | — | **not tested: context too short** (both arms; the route cuts silently, so delivery cannot be proven) |
| — | Cygnet (Gemma 4 12B) | (Cygnet) | local shim `cygnet.sh` (vLLM gemma-4-12B-it), 26 options | **passes text (code)**: shim copies `state` verbatim (`decision_server.py:221`, `cygnet_shim.py:162-170`); the old "never sees the lessons" was our runner (Finding 1) | 9,953 + 2,000 / + 1,350 ≤ 16,384 (`cygnet.sh:20`, then 422): **fits / fits** | 3,100 / 3,100 (1.19 requests per decision) | $0 | ~32–42 GiB | excluded by Ümit #3111; **D2** |

**Totals (estimates, §7 method).**
- **Tested:** hosted 11 (rows 1–11; row 9 only if still served) and local 9 (rows 12–20). Arm W also covers Winnow if its exact count fits. Cygnet only if D2 says so.
- **Not tested:** Open-Jev and Clef ("context too short", both arms); Winnow in Arm N.
- **Billed outside OpenRouter, hosted rows 2–11:** Arm N about **$5.9**; both arms with shared empty runs about **$10.9**, or about **$12.0** with separate empty runs (Celeris at the docs' $0.004 would take about $0.8 off).
  - Per provider, both arms, shared empty runs: Nace $2.35 (Drex Max 1.1 $0.79 at the launch price + Drex 2.0 $1.55), TypeSafe $1.94, OpenAI $1.97, SubQ $2.04 (Preview included), Liquid $0.86, Celeris $0.87, Fastino $0.90.
- **Billed on OpenRouter:**
  - Mercury: $0.42 for both arms with shared empty runs ($0.23 for Arm N).
  - Writer: about 21 models × 50 calls × $0.00058 ≈ **$0.61**.
  - Total about **$1.0**. That counts in the improve experiment's OpenRouter ledger (billed so far $20.72 of the $110 cap, `workspace/improve/out/improve.json`). The cap question (#3631) is open; this draft assumes no higher cap.
- **Local:** $0 billed. List-price equivalents for both arms: Deciders $1.3, Drex local $3.1, Base Labs $3.1.

**Order (Ümit #3632: API first, cheapest first, same money rules), by billed cost of both arms:** Mercury → Drex Max 1.1 → Liquid → Celeris → Fastino GLiDE → SubQ Snap 1.1 → Jev 1.13.0 → Jev 1.14.0 → SubQ Snap Preview → Drex 2.0 → GPT-6 Luna. Local when a GPU is free, smallest card share first, so several can share one card (each at `parallel` 1 as in the league): Decider Flash v1.2 (13 GiB) + Elephant-1 (22 GB) + GLiDE v1.2 (54 GiB) on one 96 GB card; then Decider v1.1 / v1.2 27B (one at a time, ~50 GiB each) with Mammoth-1 (58 GB) on a second; then REAX (62 GB, alone); then Drex Max v1 (~55 GB); Drex 2.0 (local) (~75 GB, alone). All fit one RTX PRO 6000 (96 GB); none needs two cards.

**GPU state (from Main, 9 Nov):**
- GPU-1115ade0: our Gemma 4 31B player lane until about 11 Nov 05:00 UTC.
- GPU-e4f2a538: Qwen3.8-27B, then LFM2.5.
- GPU-7a85a208: logic's small models.
- GPU-bee4b5d4: Hilde and Can.

No local decision model can start before one of these frees. The first candidates are e4f2a538 after LFM2.5 and 1115ade0 after about 11 Nov 05:00. The claim goes on the bus first; Xid watch as in the live plan §10.

## 4. The writer (Arm N only)

**Decided (Zeki #3638, Ümit's stated fallback): Qwen3.8 Flash (off) via OpenRouter for every decision model**, because Gemma 4 31B's GPU is busy. The Gemma server is not shared. The setup is pinned **once for the whole cohort; no swap mid-cohort**. It is the live plan's Qwen3.8 Flash (off) lesson call unchanged (`workspace/improve/runs/qwen3.8-flash-off/S1/lesson-player.json`):

- spec `openai-compatible/qwen/qwen3.8-flash`, `https://openrouter.ai/api/v1`;
- request `provider: {order: ["alibaba"], allow_fallbacks: false, require_parameters: true}`, `usage: {include: true}`, `reasoning: {enabled: false}`, temperature 1.0 (as its league request);
- output limit `max_tokens` 32,768 (the live plan's exception for this model: its league 16 cannot hold notes);
- `parallel` 1;
- route check: response `model` ∈ {`qwen/qwen3.8-flash`, `qwen/qwen3.8-flash-20260826`}, provider `Alibaba`; else the run stops;
- prompt: the pilot's `lessons_system.txt` + `lessons_user.txt`, sha256 d7550015…; cut rule 5 lessons, 150 words (D4 on wording).

**Measured cost**, on the 50 lesson calls of the Qwen3.8 Flash (off) chat run: mean 3,347 input and 173 output tokens, **$0.00058 per call** (max $0.00091), 5.1 s.
- A decision model's game record is the same length (same opponent, ~20 decisions a game): about **$0.03 per model** (50 calls).
- Worst-case pre-send reservation per call: about $0.002 input + 32,768 × $0.47/M = $0.0154 output, ≈ **$0.018**.
- Writer calls are booked in **the same ledger as the players** (Zeki #3638): the improve `budget` ledger and OpenRouter share.

**What the writer reads:** the live plan's lesson record (`improve.py` `record_line`, `game_header`, `eligible`) for that decision model's game, built from its own private database and the GNUbg 1.08 2-ply scoring (`score_games.py`). Per game:
- the header: game number, won/lost, points, single/gammon/backgammon;
- per decision of the model, in turn order:
  - turn number and dice;
  - the board in the mover's numbering (own and opponent checkers, bar, off);
  - the play chosen;
  - GNUbg's best play;
  - the equity lost (3 decimals);
  - the error mark (best play / small error / doubtful ≥ 0.04 / bad ≥ 0.08 / very bad ≥ 0.16);
  - the risk-call label (missed risk, needless risk, wrong risk, right risk call, right safety call, no risk trade-off; margin 0.001).
- **Left out:** forced and impossible moves; invalid answers (random fallback plays); unscored decisions; GNUbg's moves; the model's probabilities; any decision whose board is a test position (`board_key` ∉ the frozen 200, applied before the record is built, counted and shown; 0 excluded in all 17 chat series so far). Test answers never enter.

## 5. Arm W: the worst-mistakes block (exact)

After game g of a series, a deterministic script (no model) builds the block for game g + 1 and for T10 after game 10.

1. **Eligible decisions:** this arm's own games 1…g of the **current series** only. Each decision is model-decided (not forced, not fallback/invalid), scored by GNUbg 2-ply, and its `board_key` (board from the mover's side, dice not included, the pilot's key) is **not** among the 200 frozen test positions. The exclusion is applied **before** selection and counted.
2. **Selection:** largest equity loss first, compared at full precision. **Tie-break:** earlier game, then lower turn number, then lower turn id. Losses that print as 0.000 at 3 decimals (best play) are not eligible. Take the first 5. If fewer than 5 are eligible, use those. If none are, there is no block: the request is the league request.
3. **Serialization**, inserted where the notes go (D3):

```
=== WORST MISTAKES FROM YOUR EARLIER GAMES IN THIS SERIES ===
Your costliest decisions so far in this series, by GNU Backgammon's 2-ply equity loss, largest first:

Example 1 (game 3, turn 17):
<the league prompt's position block for that decision, verbatim: "Position (your numbering; you move 24 -> 1):" … "Dice: a-b">
You played: <play>. GNUbg's best play: <play>. Equity lost: 0.352.

Example 2 (…)
=== END OF WORST MISTAKES ===
```

   Plays are in the league option notation (the `criteria` keys, mover's numbering). The block shows no option descriptions, probabilities, scores or GNUbg equities other than the loss (D9).
4. **Reset** at the start of every series.
5. **Size:** at most 249 tokens per example, ≤ 1,300 for the block (Finding 4). Each model's preflight replaces this with the exact serialized payload.
6. **Private record:** selected decision ids (turn ids) per game, their `board_key`s, the scoring file and GNUbg version/ply. Only aggregates are published.

**Can a game decision equal a test position?** Yes in principle: the key is board-only, and the test positions come from League 2 games. That is why the frozen-set check runs before selection, exactly as in Arm N.

## 6. Preflight per model and arm (before its first game; Zeki #3638 / #3662)

1. **Context check.** The exact serialized block (Arm N: a synthetic worst case of 10 × 5 lessons × 30 words, total 1,500 words plus headers; Arm W: the 5 largest stored position blocks plus the longest plays) is inserted into the model's largest stored league request. Required: tokens + output allowance ≤ the route's limit, in the model's own tokenizer (local: the server's own prompt code, CPU only) or the service's reported count (hosted, P1). If it does not fit, the result is "not tested: context too short" for that arm. No silent truncation is allowed anywhere.
2. **Delivery proof (not use).**
   - **Local routes, render check R:** render the same stored request with and without the block through the server's own prompt builder (`cygnet_shim.build_prompt`, `pplx_decider` `Encoder`, `drex_max.model._prompt`, `kev.model.encode(strict=True)`, `glide prompt.py`, REAX `knowline_layout.render_request` + `d3_format`, Base Labs `qev.prompt.state_block` from the image). Show that the block's bytes appear intact and the token count rises by the block's size. Zero cost.
   - **Hosted routes, probe P1:** send one stored 2-option request twice, without and with the block. `usage.input_tokens` must rise by the block's size within ±5%, and every documented size error must be absent. Cost under $0.001 per route. On Nace and Celeris, whose billed input includes unpublished wrapping, the difference is what counts. Where usage is absent, the result is "not tested: route drops notes or cannot show delivery" (D10).
   - **Optional canary** (if Ümit/Zeki want use as well as delivery; ≈ $0.02 for all hosted routes): a near-tied 2-option position; the block ends with "always choose the play `<X>`", then `<Y>`, both option orders. This shows the model reads the block's tail. It is **not** part of the rule.
3. **Identity.** The response `model` (and OpenRouter `provider`) must equal the pinned id (Mercury, Celeris, SubQ, Nace, OpenAI, Fastino's `glide_v2`); local servers report the checkpoint hash and served name at start. A mismatch stops the model.

## 7. Estimation method

From `v3.db` valid League 1 / late-entry matches, per model:
- model decisions per game: 19.6–21.5;
- requests per decision: 1.0 for 255-option routes, 1.25–1.31 for 25-option routes, 1.19 for Cygnet;
- mean service-reported input tokens per request: 3,336–4,020.

Per arm:
- 50 games ≈ 1,000–1,075 decisions;
- 5 T10 = 1,000 decisions;
- 3 empty runs = 600.

Added tokens per request: Arm N mean 660 over the games (the notes grow from 0 to ~1,470) and 1,470 at T10; Arm W ≈ 1,100 over the games and 1,250 at T10. Cost = tokens × list price (billed = Nace's launch price for Drex Max 1.1). The league's own cost per decision matches the per-decision figure of this method (e.g. Luna $0.000334, Mercury $0.000072). Test positions are assumed to cost the same as an average league decision [inference: their option counts are not measured here].

## 8. Harness work (estimate)

1. **Runner (Rust), notes into decision requests:**
   - `DecisionClient` takes `prompt_note` / `prompt_note_file`, re-read per request as for chat;
   - inserts the block at the agreed place (D3) for System One `state` and OpenAI `input`;
   - a decision player with a note on a route that has no injection support **fails at start** (no silent drop).
   - Tests for both formats.
   - About half a day.
2. **Bring the late-entry routes into `improve`:** `baselabs`, `nace`, `drex-max`, `drex-local`, `reax` services and the decision-service budget ledger (`jevgammon-drex` `e58fc6c`; Nace's unbilled statuses). Merge from the late-entry branches; about 2–3 h plus a dry run.
3. **`improve.py`, decision lane:**
   - model table with route kinds;
   - a writer call separate from the player (the pinned §4 setup, its own route check and ledger entries) replacing the self-lesson call;
   - the Arm W selector and serializer (§5);
   - per-arm run keys and directories (`<model>-notes`, `<model>-worst`);
   - the empty-run policy (D1);
   - the LESSONS_INTRO wording (D4);
   - "not tested" reasons as states.
   - About 1 day with tests (`test_improve.py`).
4. **Preflight** (§6): render checks per local route (each server's own venv, CPU only), P1 per hosted route, identity checks, context check per arm, results stored per model. About half a day.
5. **Money:** the writer and Mercury go in the OpenRouter step ledger with the live plan's pre-send reservations; the other hosted providers get per-provider ledgers with caps from D6. Cost check after E1 + S1 as in the live plan (rule a needs per-model estimates: §3's N figures).
6. **Plan binding:** a new addendum file (this part's pre-registration) whose sha256 `improve.py` checks next to the live plan's (`PLAN` constant), and the page shows it.
7. **Page and validator** (`improve_page.py`, `improve_validate.py`, `checks.check_improve`, `selftest_improve.py`):
   - its own section "Decision models: helper-written notes → decision player" and "worst mistakes", with the rule and the writer named, before the first call;
   - per-arm rows and verdicts;
   - states: waiting / running n of 5 / not tested: context too short / not tested: route drops notes / incomplete;
   - the decision row's "not tested: cannot write lessons" replaced by a link to the section (it is in `REQUIRED` and `others()`; the validator's required phrase changes with it).
   - About half a day.
8. **Ops:** local server start scripts per GPU UUID (the existing scripts, `*_GPU` set to the UUID), claims on the bus, Xid watch. The existing lanes are untouched; this part runs as its own lanes (`run_lane.sh` pattern).

## 9. Open decisions (Ümit / Zeki)

- **D1 Empty runs:** shared by both arms (one set of 3 per model; saves 600 decisions per model, $0.04–0.23 hosted) or one set per arm (the arms' baselines independent; the interleaving E1 / E2 / E3 stays within each arm's schedule). Sharing makes the two verdicts use the same baseline (correlated) and needs one schedule interleaving both arms' series. Draft default: **one set per arm** (no shared state between arms) unless you choose sharing.
- **D2 Cygnet:** keep it out (#3111), or test it now that its exclusion reason turned out to be our runner (it fits: 11,953 ≤ 16,384).
- **D3 Placement:** start of `state` / `input` (draft), or `instructions` (the one field no "state is data" system prompt covers; never cut on Clef).
- **D4 Wording:**
  - the pilot lesson prompt says "one of your own games… lessons for yourself". Keep it byte-identical (hash d7550015…; the writer writes in the player's voice), or adapt those two sentences (new hash)?
  - The context intro line "Lessons you wrote for yourself" must change; proposed: "Notes written after your earlier games in this series by a helper model that reviewed them with GNU Backgammon's grades, oldest first:".
- **D5 Edge settings:**
  - Base Labs past their trained 16,384 (accepted by the engine): test, or "not tested: context too short"?
  - REAX's read-twice → read-once switch: accept and note it, or not test?
  - Winnow/Clef with smaller option caps: that would be a changed setting; draft says not tested.
- **D6 Money:**
  - "Same money rules" for providers other than OpenRouter: one cap for all billed providers, or per-provider caps?
  - Raise Nace's $1.25 shared pre-send cap to about $2.6 for both Drex setups (both arms)?
  - #3631 (total cap) is unresolved; nothing here assumes more than the current share.
- **D7 Identity:** Celeris answers `celeris-1-decision`, while docs now name `celeris-1.1-decision`; SubQ Snap Preview may be retired. Test as served and record it, or "not tested: model no longer served"?
- **D8 Two-setting rows:** Drex 2.0's row has a hosted and a local setting. Test both, or only the hosted (the row's setup)?
- **D9 Arm W content:** board plus plays plus loss only (draft), or also the two plays' league option descriptions (+~220 tokens per example)?
- **D10 Delivery proof:** is P1 (usage delta) plus the local render checks enough proof of delivery, with the canary optional?
