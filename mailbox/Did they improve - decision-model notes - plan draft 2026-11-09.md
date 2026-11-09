# Did they improve? Decision models (Part 3): plan draft (2026-11-09, revision 2)

**Draft, not the pre-registration.** Nothing was called, bought, started or stopped to write it; the running lanes, the live plan (`mailbox/Did they improve - plan 2026-11-08.md`, sha256 85a970d0…8542) and the live page are untouched. The pre-registration will be a separate addendum, committed and shown on the page (rule, writer, arms) before the first call.

Sources: Ümit #3632 (the part) and #3660 (the second arm), Zeki #3638 (writer, label, preflight, context check, ledger), #3662 (second-arm rules), #3664/#3665 (publication) and #3678 (review of revision 1, sha256 c9aa6db9…00d3), the live plan, `v3.db` (read-only), the improve run files, the server and client code named below, and the makers' docs (read 2026-11-09).

**Changed from revision 1 (Zeki #3678):**
- Delivery evidence is now split into API contract + accounting (hosted) and final-render evidence (local). Anything unresolved is "delivery unverified", never a pass (§6).
- Every actual request is gated at run time. The historical-maximum figures are sizing evidence only (§2, §6).
- Publication follows #3664/#3665 (§8.7).
- The cohort is reconciled to 23 setups (§3).
- No Celeris successor and no hosted/local substitution (§3).
- Money keeps the $110 total, the $5 reserve and the existing provider subcaps, with both empty-run schedules shown separately (§7).
- One model per GPU (§3).
- Effect of the stricter delivery standard: Mercury, Liquid, SubQ Snap Preview and GPT-6 Luna become "not tested: delivery unverified", because their docs do not say that oversize input is refused or that billed input is what the model reads.
- D3, D4, D9 and D10 are decided here; D1, D2, D5–D8 remain for Ümit.

## 1. What this part asks

Per decision model on the leaderboard, at its leaderboard setting: does it take risks better on the pilot's 200-position test after 10 games against GNUbg weak with a block of text about its own earlier games in its prompt, than with no block? Two arms, each judged on its own:

- **Arm N, helper-written notes → decision player.** After each game a fixed helper model (the writer) reads the decision model's graded game record and writes notes with the pilot's lesson prompt and limits. The page says: *helper-written notes, not self-written learning* (Zeki #3638).
- **Arm W, worst mistakes (no writer).** After each game a fixed script puts the 5 costliest decisions of this series so far (GNUbg grades) into the prompt as solved examples (Ümit #3660).

Same as the chat models: 5 series × 10 games against GNUbg weak (GNU Backgammon 1.08 Beginner), the pilot's dice s01–s05 (mirrored pairs), the same 200 test positions (test-set sha256 6c92e741…18e6), 3 empty runs, T10 after each series, and the rule unchanged: **Improved** = risks found (mean of 5 T10) − risks found (mean of 3 empty runs) > max(range of the 3 empty runs, 5 points), and right safety change ≥ −5 points. Verdicts are reported **per arm**, under the same rule; neither arm is picked as "the" result (Zeki #3662).

Each arm has its **own games**: same dice schedules, never the other arm's games, decisions or trajectories (Zeki #3662). Notes and examples reset at the start of every series. Games count nowhere (no league, no leaderboard).

## 2. Delivery: what is known

A decision request is System One JSON: `state` (free text: the league rules text, then this turn's score, board and dice, then the question), one `choice` question with `instructions` (free text) and `criteria` (option → description); OpenAI's Decisions API takes `input` instead of `state` (`src/players/decision.rs` `body()`). Free text can therefore go into the request on every route. Whether each service puts it into the model's input complete and unchanged is the question §6 settles per route.

**Finding 1, our own runner (all routes):** `prompt_note` / `prompt_note_file` exist only for chat players. `llm::play_system` appends them to the chat system prompt (`jevgammon-improve/src/players/llm.rs:332-342`). The decision branch of `Player::build` builds `DecisionClient::new(http, service, model, base_url)` and never sees them (`src/players/mod.rs:491-497`), and `DecisionClient` builds the body from `state(req)` and `instructions(req)` alone. **A note set on a decision player is dropped without an error today.** This is why "Cygnet's layer never sees the lessons" (live plan §3): the cause is the runner, not Cygnet's shim. The shim copies `state` into the model's user turn (`cygnet/shim/decision_server.py:221`, `cygnet_shim.py:162-170`).

**Finding 2, the improve branch lacks the late-entry routes.** `jevgammon-improve` (`19921b4`) has the 15 older services. `baselabs`, `nace`, `drex-max`, `drex-local` and `reax`, and the decision-service budget ledger (`jevgammon-drex` `e58fc6c`), live in the late-entry branches (`jevgammon-reax` `acfd89c`).

**Finding 3, notes size (sizing evidence only).** On the 17 completed chat-model series, the notes context after game 10 measured **mean 1,473 and max 1,838 tokens** (Qwen3 tokenizer; max 9,535 bytes and 1,460 words). The pilot's cut rule caps it at about 1,560 words with headers. The sizing below uses **2,000 tokens for Arm N**.

**Finding 4, the worst-mistakes block (sizing evidence only):** **at most 249 tokens per example** (Qwen3 count). That is the league's own position block, measured over 11,265 distinct stored League 1 boards (min 108, median 145, p99 164, max 174 tokens), plus two plays and the loss line. With headers, 5 examples come to **≤ 1,300 tokens**; the sizing uses **1,350 tokens for Arm W**.

These figures and the historical largest requests (§3) decide only whether a model is **worth preparing**. They do not bound future requests. The binding check is the **per-request gate** (§6.2) on every request actually rendered at the pinned settings.

**Placement (decided, an implementation choice):** the block goes at the **start of `state`** (OpenAI: start of `input`), before the rules text. `instructions`, the option descriptions and the rest of the state stay byte-identical to the league's, apart from escaping a route declares. Header and delimiters for Arm N: the live plan's `=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===` … `=== END OF NOTES ===`, with the intro line **"Notes a helper wrote from your earlier games in this series, oldest first:"**. That replaces `improve.py:85`'s "Lessons you wrote for yourself", which would be false here. Placement says nothing about whether the model uses the notes.

**"State is data."** Decider v1.1/v1.2/Flash, Drex Max v1, Winnow and both REAX parts have a fixed system or ask prompt that says the state is data, not instructions (e.g. `autojev/model.py:107-108`, `pplx_decider/protocol.py:36-38`, `drex_max/model.py:111-116`, `winnow/native/protocol.h:56-57`, `reax knowline_server.py:66-67`). Notes can arrive intact and still be discounted by design. That is a property of the model and part of what the test measures, and the page says so. Delivery evidence is about arrival only.

## 3. Cohort and models

**Count reconciled.** The live plan names "the 22", i.e. 22 leaderboard names, one of which ("Drex 2.0 (and its local setting)") has two setups in `v3.db`: **Drex 2.0** (Nace hosted) and **Drex 2.0 (local)**. That gives **23 setups**, rows 1–23 below. **Cygnet (Gemma 4 12B)** is a further setup that #3111 excluded explicitly; it is listed only as an open scope question (D2). Fastino GLiDE (hosted) and Fastino GLiDE v1.2 (local) are separate leaderboard names, each run on its own route.

**Identity freeze (per setup, written into the addendum before any call).** The following are frozen from `v3.db` `players.settings`:
- setup name;
- route (service, URL path);
- model id sent;
- checkpoint and commit (local);
- request parameters;
- option cap (`max_choices` / group size);
- the allowed response aliases (as observed in the league).

There is no successor, alias or substitute beyond that list:
- **Celeris:** send `celeris-1-decision`, as the leaderboard row did. Its docs now name `celeris-1.1-decision`. If the service refuses the frozen id or answers with an id outside the frozen aliases, the model stops: "not tested: model id not served as on the leaderboard" (D7).
- **SubQ Snap Preview:** the same rule.
- **No hosted/local swap:** a hosted setup is never replaced by local weights, and the reverse.

A returned name alone does not prove the model behind it is unchanged; it is recorded, and a mismatch stops.

**Columns.**
- **Delivery evidence:** the class from §6.1. Hosted routes: contract + accounting (Hc), or unresolved. Local routes: final render (Lr), or pending its render check.
- **Sizing:** the historical largest league request of that model (the service's own reported input tokens, `v3.db` exchanges, valid matches) + the arm's sizing bound (N 2,000 / W 1,350) + output allowance (0 everywhere: every route reads probabilities and none generates text; Cygnet's vLLM call is 1 token), against the route's limit for one request, question or candidate.
- **Est. $:** **separate** empty runs (the default, D1), then **shared** empty runs; method in §7. "Arm N" is that arm with its own 3 empty runs.
- **GPU:** the single-model footprint measured in the league. One model per GPU (no co-residency is planned).

| # | Setup (v3.db) | Maker | Route (frozen) | Delivery evidence (§6.1) | Sizing N / W (historical max + bound vs limit) | Est. decisions / requests per arm (incl. its 3 empty runs) | Est. $ both arms: separate · shared (Arm N alone); billed unless noted | GPU (alone) | Status / blocker |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mercury Decide | Inception | OpenRouter `openrouter.ai/api/v1/systemone`, `inception/mercury-decide` | **unresolved**: docs say state is read as given (openrouter.ai/docs/guides/community/typesafe-sdk.md; docs.inceptionlabs.ai/capabilities/decisions.md, read 2026-11-09). Neither documents oversize handling, and the same OpenRouter page documents a **silent** cut for another provider ("reads roughly the first 2,000 tokens of text in `state` and drops the rest without an error") | 27,535 + 2,000 / + 1,350 ≤ 65,536 (openrouter.ai/inception/mercury-decide) | 2,600 / 2,600 | $0.46 · $0.42 ($0.23) on OpenRouter | — | **not tested: delivery unverified** (unless the maker documents refusal on oversize) |
| 2 | Drex Max 1.1 | Nace.AI | Nace `console.nace.ai/v1/systemone`, `drex-max-v1.1`, 25 options | **Hc**: "Drex passes it to the model as is"; too long → `422`, "A longer request is refused" (console.nace.ai/docs/drex/api-reference/systemone; …/reference/models) | 5,204 + 2,000 / + 1,350 ≤ 262,144 whole request | 2,600 / 3,350 | booked at list $0.06: $1.74 · $1.58 ($0.86); Nace bills $0.87 · $0.79 at its $0.03 launch price | — | Nace subcap (§7) |
| 3 | Liquid d1-ultra | Liquid AI | `api.liquid.ai/decisions/v1/systemone`, `d1-ultra` | **unresolved**: state "can be plain text" (docs.liquid.ai/lfm/models/d1.md); Liquid publishes no limit and no oversize behaviour | 20,603 + 2,000 / + 1,350 ≤ 32,768 (OpenRouter listing only) | 2,600 / 2,600 | $0.94 · $0.86 ($0.47) | — | **not tested: delivery unverified** |
| 4 | Celeris-1 Decision | Celeris | `inference.celeris.ai/celeris-1-decision/v1/systemone`, `celeris-1-decision` | **Hc**: "`input_tokens` covers everything the model reads for the request"; unknown field → `422`; context 131,072 (docs.celeris.ai/decisions, /models) | 28,163 + 2,000 / + 1,350 ≤ 131,072 | 2,600 / 2,600 | $0.96 · $0.87 ($0.48) at our recorded $0.04 (docs now $0.004) | — | D7 (id) |
| 5 | Fastino GLiDE | Fastino | `api.fastino.ai/v1/systemone`, `fastino/GLiDE` (answers `glide_v2`) | **Hc**: each question prompt "must fit within 65,536 tokens"; `400` "Prompt exceeds the context window"; extra field → `422` (docs.fastino.ai/inference/systemone.md) | 27,515 + 2,000 / + 1,350 ≤ 65,536 | 2,650 / 2,650 | $0.99 · $0.90 ($0.49) at $0.04 (docs; league recorded none) | — | — |
| 6 | SubQ Snap 1.1 | SubQ | `api.subq.ai/v1/systemone`, `subq-snap-1.1` | **Hc**: "`state`: the text, object, or array to evaluate"; "A request over the limit, or close to it, fails with `400`" (docs.subq.ai/endpoints/decisions-api) | 21,968 + 2,000 / + 1,350 ≤ 393,216 | 2,700 / 2,700 | $0.99 · $0.90 ($0.49) | — | — |
| 7 | Jev 1.13.0 | TypeSafe | `api.typesafe.ai/v1/systemone`, `jev-1.13.0` | **Hc**: "State is the content you ask a System One model to evaluate"; over the limit → `400 max_tokens_exceeded` (docs.typesafe.ai/concepts/state.md, api/errors.md) | 26,116 + 2,000 / + 1,350 ≤ 32k per question (docs.typesafe.ai/models.md; 32,000 or 32,768 not stated: the gate uses 32,000) | 2,600 / 2,600 | $1.05 · $0.96 ($0.52) | — | — |
| 8 | Jev 1.14.0 | TypeSafe | same, `jev-1.14.0` | **Hc**, as row 7 | 27,898 + 2,000 = 29,898 / 29,248 ≤ 32,000 (tightest hosted) | 2,650 / 2,650 | $1.08 · $0.98 ($0.53) | — | — |
| 9 | SubQ Snap Preview | SubQ | `api.subq.ai/v1/systemone`, `subq-snap-preview` | **unresolved**: no longer on docs.subq.ai/using-the-api/models (answered on 2026-11-07) | not published | 2,650 / 2,650 | $1.25 · $1.14 ($0.62) | — | **not tested: delivery unverified**; D7 |
| 10 | Drex 2.0 | Nace.AI | Nace, `drex-v2.0`, 25 options | **Hc**, as row 2 | 5,017 + 2,000 / + 1,350 ≤ 131,072 state / 262,144 state + question | 2,600 / 3,350 | $1.71 · $1.55 ($0.84) | — | Nace subcap; D8 |
| 11 | GPT-6 Luna | OpenAI | `api.openai.com/v1/decisions`, `gpt-6-luna` | **unresolved**: `input` is "Shared evidence for the questions: a text string…"; the API schema limits `input` to 10,485,760 characters, but the pages read (developers.openai.com/api/docs/guides/decisions; …/reference/resources/decisions/methods/create, 2026-11-09) neither say that over-long token input is refused rather than cut nor tie billed input to what the model reads | 24,150 + 2,000 / + 1,350 ≤ 922,000 max input (model page) | 2,600 / 2,600 | $2.17 · $1.97 ($1.07) | — | **not tested: delivery unverified** (unless OpenAI's docs settle (a)) |
| 12 | Decider Flash v1.2 | Perplexity | local `pplx_decider_server.py`, `decider-v1.2.sh flash`, 25 options | **pending R** (code: `protocol.py:176-189` "State:\n" + state; only `<|…|>` escaped, `:149-152`) | 5,162 + 2,000 / + 1,350 ≤ 262,144 (`model.py:35`, then 400) | 2,600 / 3,400 | $0 (list eq. $0.30 · $0.27) | ~13 GiB | GPU |
| 13 | Decider v1.2 27B | Perplexity | local `decider-v1.2.sh 27b` | **pending R**, as row 12 | 5,166 + 2,000 / + 1,350 ≤ 262,144 | 2,600 / 3,300 | $0 (list eq. $0.57 · $0.52) | ~53 GiB | GPU |
| 14 | Decider v1.1 27B | Perplexity | local `decider.sh` (`autojev`) | **pending R** (`autojev/model.py:98-103` "State:\n" + describe(state)) | 5,168 + 2,000 = 7,168 / 6,518 ≤ 8,192 per question (`model.py:264,284-285`, then 422) | 2,600 / 3,350 | $0 (list eq. $0.58 · $0.53) | ~49–52 GiB | GPU |
| 15 | Base Labs Elephant-1 | Base Labs | local `baselabs_server.py` (qev + `serve.patch`, image `baselabs-serve:81ce62f`), 120 options | **pending R** (state in the shared prefix, `serve.patch:226-238,252-254`; renderer `qev.prompt.state_block` only inside the image) | 14,777 + 2,000 = 16,777 / 16,127 vs trained 16,384 (card); engine refuses > 32,768 | 2,600 / 2,600 | $0 (list eq. $0.85 · $0.77) | ~22 GB | GPU; D5 (N past the trained length) |
| 16 | Base Labs Mammoth-1 | Base Labs | local, as row 15 | **pending R**, as row 15 | 15,212 + 2,000 = 17,212 / 16,562 vs 16,384 trained / 32,768 refused | 2,650 / 2,650 | $0 (list eq. $2.52 · $2.28) | ~57–59 GB | GPU; D5 (both arms past the trained length) |
| 17 | Drex Max v1 | Nace.AI | local `drex_max_server.py` (`drex_max` @ e206b27), 25 options | **pending R** (`drex_max/model.py:105-108`; `_text` returns strings unchanged) | 5,135 + 2,000 / + 1,350 ≤ 16,384 (`model.py:26-45`, then 400) | 2,650 / 3,450 | $0 (list eq. $1.79 · $1.63) | ~55 GB [inference: 27B bf16] | GPU |
| 18 | Drex 2.0 (local) | Nace.AI | local checkpoint `serve.py` (kev), 25 options | **pending R** (`kev/api.py:107-123` render returns strings unchanged; `kev/model.py:116-119` escapes only `<|name|>`) | 5,065 + 2,000 / + 1,350 ≤ 16,384 (`KEV_CONTEXT`, `ContextOverflow` → 400) | 2,500 / 3,250 | $0 (list eq. $1.64 · $1.49) | ~75 GB [inference: 70.2 GB weights] | GPU; D8 |
| 19 | Fastino GLiDE v1.2 (local) | Fastino | local `glide/server.py`, `glide-v12.sh` | **pending R** (`prompt.py:164-166` "Context:\n{state}") | 25,372 + 2,000 / + 1,350 ≤ 40,000 (`server.py:48`, then 422) | 2,600 / 2,600 | $0 | 53.6 GiB | GPU |
| 20 | REAX 1.3 | REAX Labs | local `reax13/serve.py` (Docker, reax-engine @ ff8f595) | **pending R** (G `knowline_server.py:132-133`, Q `d3_format.py:149-159`). Part G reads requests ≤ 3,000 tokens twice (`backend.py:42`, `knowline_layout.py:182-194`); with the block every request is longer, so short requests are read once | 57,867 + ~10,000 bytes ÷ 4 ≈ 17,000 proxy tokens ≤ 32,000 (`reax13_engine.py:21-24`) | 2,650 / 2,650 | $0 | ~62 GB | GPU; D5 (layout switch) |
| 21 | Open-Jev 27B v1.1 | (Open-Jev) | local `open-jev.sh`, one prompt per candidate | text would pass (`jev/api.py:83`), but each candidate prompt is limited to **4,096** tokens (`open-jev.sh:15`), refused with 422, "no silent truncation" (`jev/model.py:225-226`); state alone is ~2.4–2.9k | over on most or all requests in both arms | — | — | — | **not tested: context too short** (both arms) |
| 22 | Winnow-12B | EldanRing | local `winnow-inference:d4631fb`, 40 options | **pending R**: state, instructions and options are JSON-escaped (`protocol.h:28-35,66,133-137`); R must show notes, board and options survive that escaping | 6,807 + 2,000 = 8,807 > 8,192 (`winnow.sh:17-18`, then 400); W 8,157 by the Qwen bound, 35 tokens under | — / 2,900 if W qualifies | $0 | 14.6 GiB | **N: not tested: context too short.** W: only if R's exact Gemma-tokenizer sizing qualifies; any runtime refusal → incomplete. The 40-option cap stays (D5) |
| 23 | Clef | (Clef) | local `clef/server.py`, 110 options | text passes, but the state's tail is **cut silently** (`joint_schema_model.py:170` `state_ids[: max_length - fixed_length]`) | 15,194 + 2,000 / + 1,350 > 16,384 (`:547`): the cut removes the dice and the question | — | — | — | **not tested: context too short** (both arms; the route cuts silently, so no gate can protect it) |
| (D2) | Cygnet (Gemma 4 12B) | (Cygnet) | local shim `cygnet.sh` (vLLM gemma-4-12B-it), 26 options | **pending R** (shim copies `state`: `decision_server.py:221`, `cygnet_shim.py:162-170`; trailing whitespace stripped) | 9,953 + 2,000 / + 1,350 ≤ 16,384 (`cygnet.sh:20`, then 422) | 3,100 / 3,100 | $0 | ~32–42 GiB | excluded by #3111; **D2** |

**Cohort outcome before preflight:**
- **Hosted, eligible to prepare (Hc), 6:** rows 2, 4, 5, 6, 7, 8, plus row 10 if D8 keeps it.
- **Hosted, "not tested: delivery unverified", 4:** rows 1, 3, 9, 11.
- **Local, eligible to prepare (pending R), 9:** rows 12–20 (row 18 per D8; rows 15, 16, 20 per D5).
- **"Not tested: context too short":** rows 21 and 23 in both arms; row 22 in Arm N.
- **Row 22 Arm W** depends on its exact count.
- **Cygnet** per D2.

**GPU (one model per GPU).** Each local model ran alone on one RTX PRO 6000 (96 GB) in the league, which is the only capacity evidence. This plan puts **one model per GPU at a time** and no co-residency. Several local models have shared a card in the past, but that was not measured for this workload, so it is not planned. The local queue is ordered smallest footprint first: Decider Flash v1.2 → Elephant-1 → (Winnow-12B W, if eligible) → Cygnet (if D2) → Decider v1.1 27B → Decider v1.2 27B → GLiDE v1.2 → Drex Max v1 → Mammoth-1 → REAX 1.3 → Drex 2.0 (local).

**GPU state (from Main, 9 Nov):**
- GPU-1115ade0: our Gemma 4 31B player lane until about 11 Nov 05:00 UTC.
- GPU-e4f2a538: Qwen3.8-27B, then LFM2.5.
- GPU-7a85a208: logic's small models.
- GPU-bee4b5d4: Hilde and Can.

No card is free, and nothing here evicts, shares or starts anything; the current lanes stay untouched. A local model starts only on a card its owner releases, with the claim posted on the bus and the Xid watch of the live plan §10. Completion timing is not established.

## 4. The writer (Arm N only)

**Decided (Zeki #3638, Ümit's stated fallback): Qwen3.8 Flash (off) via OpenRouter for every decision model**, because Gemma 4 31B's GPU is busy. The Gemma server is not shared. The setup is pinned **once for the whole cohort; no swap mid-cohort**. It is the live plan's Qwen3.8 Flash (off) lesson call unchanged (`workspace/improve/runs/qwen3.8-flash-off/S1/lesson-player.json`):
- spec `openai-compatible/qwen/qwen3.8-flash`, `https://openrouter.ai/api/v1`;
- request `provider: {order: ["alibaba"], allow_fallbacks: false, require_parameters: true}`, `usage: {include: true}`, `reasoning: {enabled: false}`, temperature 1.0 (its league request);
- output limit `max_tokens` 32,768 (the live plan's exception for this model);
- `parallel` 1;
- route check: response `model` ∈ {`qwen/qwen3.8-flash`, `qwen/qwen3.8-flash-20260826`} and provider `Alibaba`; anything else stops the run.

**Prompt (decided):** the pilot's `lessons_system.txt` + `lessons_user.txt`, **byte-identical** (sha256 d7550015…), so the writer writes in the player's voice ("you played"). The attribution is made truthful on the reading side: the intro line in §2, and the page label "helper-written notes → decision player".

**Cut rule (the pilot's, not context truncation):** lines starting `- ` are lessons; at most 5 lessons and 150 words are kept; cuts are counted and shown. The writer's raw reply, the kept notes and the exact block delivered to each request (by hash) are all stored. After the cut rule, nothing in the delivered block is ever shortened (§6.2).

**Measured cost** on the 50 lesson calls of the Qwen3.8 Flash (off) chat run: mean 3,347 input and 173 output tokens, **$0.00058 per call** (max $0.00091), 5.1 s.
- A decision model's game record is the same length (same opponent, ~20 decisions a game): about **$0.03 per model**, 50 calls.
- Worst-case pre-send reservation per call: about $0.002 input + 32,768 × $0.47/M output, ≈ **$0.018**.
- Writer calls are booked in **the same ledger as the players** (Zeki #3638).

**What the writer reads:** the live plan's lesson record (`improve.py` `record_line`, `game_header`, `eligible`) for that decision model's game in Arm N, built from its private database and the GNUbg 1.08 2-ply scoring (`score_games.py`). Per game:
- the header: game number, won/lost, points, single/gammon/backgammon;
- per decision of the model, in turn order:
  - turn number and dice;
  - the board in the mover's numbering (own and opponent checkers, bar, off);
  - the play chosen;
  - GNUbg's best play;
  - the equity lost (3 decimals);
  - the error mark (best play / small error / doubtful ≥ 0.04 / bad ≥ 0.08 / very bad ≥ 0.16);
  - the risk-call label (missed risk, needless risk, wrong risk, right risk call, right safety call, no risk trade-off; margin 0.001).

**Left out:**
- forced and impossible moves;
- invalid answers (random fallback plays);
- unscored decisions;
- GNUbg's moves;
- the model's probabilities;
- any decision whose `board_key` is among the frozen 200 test positions. This exclusion is applied before the record is built, then counted and shown; 0 were excluded in all 17 chat series so far.

Test answers never enter.

## 5. Arm W: the worst-mistakes block (exact)

After game g of a series, a deterministic script (no model) builds the block for game g + 1 and, after game 10, for T10.

1. **Eligible decisions:** this arm's own games 1…g of the **current series** only. Each decision is model-decided (not forced, not fallback/invalid) and scored by GNUbg 2-ply. Its `board_key` (board from the mover's side, dice not included, the pilot's key) is **not** among the 200 frozen test positions. The exclusion runs **before** selection and is counted.
2. **Selection:** largest equity loss first, compared at full precision. **Tie-break:** earlier game, then lower turn number, then lower turn id. Losses that print as 0.000 at 3 decimals (best play) are not eligible. Take the first 5. If fewer than 5 are eligible, use those. If none are, there is no block: the request is the league request.
3. **Serialization (decided):** board, chosen play, best play and loss only. No option descriptions, probabilities, scores or other GNUbg equities. It is inserted at the start of `state` as in §2:

```
=== WORST MISTAKES FROM YOUR EARLIER GAMES IN THIS SERIES ===
Your costliest decisions so far in this series, by GNU Backgammon's 2-ply equity loss, largest first:

Example 1 (game 3, turn 17):
<the league prompt's position block for that decision, verbatim: "Position (your numbering; you move 24 -> 1):" … "Dice: a-b">
You played: <play>. GNUbg's best play: <play>. Equity lost: 0.352.

Example 2 (…)
=== END OF WORST MISTAKES ===
```

   Plays are in the league option notation (the `criteria` keys, mover's numbering).
4. **Reset** at the start of every series.
5. **Size:** sizing evidence ≤ 1,300 tokens (Finding 4). The per-request gate (§6.2) governs at run time.
6. **Private record:** selected decision ids (turn ids) per game, their `board_key`s, the scoring file, and the GNUbg version and ply. Only aggregates are published.

**Can a game decision equal a test position?** Yes in principle: the key is board-only, and the test positions come from League 2 games. That is why the frozen-set check runs before selection, as in Arm N.

## 6. Preflight and run-time gates (per model and arm)

### 6.1 Delivery evidence (decided; replaces revision 1's D10)

There are two kinds of evidence, recorded separately per route; neither is shown as "verified" unless it meets its standard.

**Local routes, final render (Lr).** The check renders, CPU only (no model, no GPU), with the server's own code at its pinned commit and settings, the **final inference input**: the text or token ids the model reads, after every template, declared escaping and option layout. It uses stored league requests with and without a block, including the largest stored request.

It passes only if all of these hold:
- (a) the block's content is present in full, after the route's **declared** transformations: Winnow JSON-escaping, `<|…|>` escaping in Decider v1.2 and kev, Cygnet's trailing-whitespace strip;
- (b) the original state, instructions and every option description are present in full, in the same declared form as without the block;
- (c) the server's limits (per question, per candidate, per read) are applied to that input and no cut path is taken. For example, Clef's `state_ids[: max_length - fixed_length]` would fail.

Exact byte equality is not required where escaping is declared, and token counts are not expected to add exactly. The tools are:
- `cygnet_shim.build_prompt`;
- `pplx_decider` / `autojev` encoders;
- `drex_max.model._prompt`;
- `kev.model.encode(strict=True)`;
- `glide prompt.py`;
- REAX `knowline_layout.render_request` + `d3_format`;
- Winnow's prompt builder and GGUF tokenizer;
- Base Labs `qev.prompt.state_block` read from the image with `docker run --rm --entrypoint python baselabs-serve:81ce62f …`, which starts no model.

A route whose final input cannot be rendered this way is **"delivery unverified"**.

**Hosted routes, API contract + accounting (Hc).** This is weaker than Lr and labelled so on the page: "delivery: API contract + accounting, not verified end to end". It needs both of these:
- (a) **Contract:** the maker's docs say the `state`/`input` text is what the model reads **and** either that oversize requests are **refused**, not cut, or that billed input covers everything the model reads (so an accounting delta is a reading delta by contract). Met for rows 2 and 10 (Nace: passed "as is", oversize refused), 4 (Celeris: billed input "covers everything the model reads"), 5 (Fastino: `400` over the limit), 6 (SubQ: `400` over the limit), 7 and 8 (TypeSafe: `400 max_tokens_exceeded`). Not met for rows 1, 3, 9, 11.
- (b) **Accounting, probe P1:** one stored 2-option request sent without and with the block (under $0.001 per route). The reported input tokens must rise. P1 is accounting evidence only: billing can come before a cut, so it does not show the original board and options survived.

A route without (a) is **"not tested: delivery unverified"**, and P1 is not sent to it.

**No canary.** A behavioural canary shows neither complete delivery nor anything the rule needs, so it is not part of the plan.

**Never a pass.** Anything unresolved is "delivery unverified". A model/arm with unverified delivery is not run; it is shown with that reason.

### 6.2 Context: sizing, then a gate on every request (decided)

- **Sizing (preflight):** the historical largest request plus the arm's sizing bound (§3) decides only whether a model is prepared. For local routes, the Lr render of the largest stored request with a worst-case block (Arm N: 10 × 5 lessons × 30 words; Arm W: the 5 largest stored position blocks and the longest plays) must fit in the model's own tokenizer.
- **Run-time gate (fail closed):** every request actually rendered at the pinned settings is checked against every limit that applies before it is sent: route, question, candidate, read layout, plus the output allowance.
  - **Local routes:** the server's own refusal path (400/422 on overflow) is the gate. Clef has none, which is one reason it is not tested.
  - **Hosted routes:** our client also refuses to send a request whose upper-bound size (request bytes counted as tokens) exceeds the documented limit. The service's documented refusal is the second gate.
- **On any gate failure or refusal:** that model/arm **stops and is marked "incomplete: context limit reached"**. Nothing is shortened: no notes cut beyond the pilot rule, no examples dropped, no options dropped, no different group size. No position or game is scored from only the requests that succeeded.

### 6.3 Identity

The response `model` (and OpenRouter `provider`) must be in the frozen alias list (§3). Local servers report the served name and checkpoint hash at start. Any mismatch stops the model.

## 7. Money

**Rules (unchanged by this part; estimates do not authorise anything):**
- **$110 total cap and $5 reserve** (live plan §9): before every billed step and every request, the remaining authorised funds minus the $5 reserve must cover the pre-send reservation.
- **The existing provider subcaps stay as they are** until Ümit allocates (D6). That includes Nace's $1.25 pre-send ledger shared by both hosted Drex setups and the experiment's OpenRouter share.
- With Nace's subcap unchanged, rows 2 and 10 cannot both finish: together they book about $3.45 with separate empty runs ($3.13 shared) at list price (§7 booking rule), against $1.25. The second would stop at the cap and show "incomplete". So no Nace work starts before D6.
- **Booked:** player requests, writer calls, P1 probes, retries, and every in-flight reservation (the worst case per request: request bytes as input tokens plus the route's template margin, 4,096 tokens on decision routes, at list price; the writer's 32,768-token output allowance). A request with no response is booked at its worst case. Billed = max(provider-reported cost, tokens × list price).
- **Cost check after E1 + S1 per arm** (live plan rule a): projected > 1.5 × the per-model estimate in §3 → that model stops and is reported.
- **Cross-provider accounting (D6):** OpenRouter is checked against its live balance. TypeSafe, Celeris, Fastino, SubQ, OpenAI and Nace bill their own accounts. Whether they count against the $110, and with what allocation, is D6. No paid hosted work starts before it.

**Estimates, rows that can be run (Hc rows 2, 4–8, 10), booked** (= max(reported, list price), the rule's amount; for Drex Max 1.1 that is the $0.06 list price, about twice what Nace bills at its $0.03 launch price):

| Schedule | Hosted players | Writer (OpenRouter) | P1 probes | Total |
|---|---:|---:|---:|---:|
| **Separate empty runs (default, D1)** | $8.51 | $0.49 (≈ 17 Arm N models × 50 × $0.00058) | < $0.02 | **≈ $9.0** |
| Shared empty runs | $7.73 | $0.49 | < $0.02 | ≈ $8.2 |

- Per provider, separate empty runs: Nace $3.45 (Drex Max 1.1 $1.74 + Drex 2.0 $1.71); TypeSafe $2.13; Fastino $0.99; SubQ $0.99; Celeris $0.96 (about $0.10 at the docs' $0.004).
- The not-tested hosted rows (1, 3, 9, 11) add nothing; Mercury was the only OpenRouter player. If OpenAI's docs settle row 11's contract, Luna adds $2.17 separate / $1.97 shared.
- Reservation peak in flight is small: about $0.018 per writer call, and under $0.01 per decision request at worst case.
- This experiment's OpenRouter billed total so far: $20.72 of $110 (`workspace/improve/out/improve.json`). The total-cap question #3631 is open; nothing here assumes a higher cap.

**Order (API first, cheapest first, booked).** The order is the same under both schedules except that Fastino and SubQ swap places; the default is separate.
- **Separate:** Celeris ($0.96) → SubQ Snap 1.1 ($0.99) → Fastino GLiDE ($0.99) → Jev 1.13.0 ($1.05) → Jev 1.14.0 ($1.08) → Drex 2.0 ($1.71) → Drex Max 1.1 ($1.74).
- **Shared:** Celeris ($0.87) → Fastino ($0.90) → SubQ 1.1 ($0.90) → Jev 1.13.0 ($0.96) → Jev 1.14.0 ($0.98) → Drex 2.0 ($1.55) → Drex Max 1.1 ($1.58).

Nace (Drex) rows wait for D6 in either order.

**Local:** $0 billed; GPU queue in §3.

**Method.** From `v3.db` valid League 1 / late-entry matches, per model:
- model decisions per game: 19.6–21.5;
- requests per decision: 1.0 for 255-option routes, 1.25–1.31 for 25-option routes, 1.19 for Cygnet;
- mean service-reported input tokens per request: 3,336–4,020.

Per arm: 50 games ≈ 1,000–1,075 decisions, 5 T10 = 1,000 and 3 empty runs = 600. Added tokens per request: Arm N mean 660 over the games and 1,470 at T10; Arm W ≈ 1,100 and 1,250. The league's own cost per decision matches this method's per-decision figure (e.g. Luna $0.000334, Mercury $0.000072). Test positions are assumed to cost the same as an average league decision [inference: their option counts are not measured here].

## 8. Harness work (estimate)

1. **Runner (Rust), blocks into decision requests:**
   - `DecisionClient` takes `prompt_note` / `prompt_note_file`, re-read per request, and inserts the block at the start of `state` (System One) or `input` (OpenAI);
   - a decision player with a note on a route without support **fails at start**;
   - the hosted pre-send size gate (§6.2);
   - the stored request is the exact body sent.
   - Tests for both formats. About half a day.
2. **Late-entry routes into `improve`:** `baselabs`, `nace`, `drex-max`, `drex-local`, `reax` services and the decision-service budget ledger (`jevgammon-drex` `e58fc6c`, Nace's unbilled statuses). About 2–3 h plus a dry run.
3. **`improve.py`, decision lane:**
   - frozen setups (§3);
   - a writer call separate from the player (§4 setup, its own route check and ledger entries), storing raw, kept and delivered texts;
   - the Arm W selector and serializer (§5) with private provenance;
   - per-arm run keys and directories (`<model>-notes`, `<model>-worst`);
   - the empty-run schedule (D1);
   - the new intro line;
   - stop/incomplete on gate failure;
   - "not tested" reasons as states.
   - About 1 day with tests (`test_improve.py`).
4. **Preflight tools:**
   - Lr render checks per local route (each server's own venv, CPU only);
   - Hc contract records and P1 per eligible hosted route;
   - identity checks;
   - results stored per model/arm, with their evidence class.
   - About 1 day.
5. **Money:** all booked items of §7 go into the step ledgers; provider ledgers with the existing subcaps; the $5 reserve check. About 2 h.
6. **Plan binding:** a new addendum file (this part's pre-registration) whose sha256 `improve.py` checks next to the live plan's (`PLAN` constant), and the page shows it.
7. **Page and validator (#3664/#3665)** (`improve_page.py`, `improve_validate.py`, `checks.check_improve`, `selftest_improve.py`):
   - extend the **existing** improve table, not a new section, with a **Chat / Decision filter**;
   - **two rows per decision model** ("<model> · helper-written notes" and "<model> · worst mistakes");
   - **not-tested rows stay visible with their reason** ("context too short", "delivery unverified", "model id not served as on the leaderboard", "excluded (#3111)" for Cygnet unless D2 changes it);
   - per row: the delivery evidence class, and "incomplete" states;
   - the rule, the writer (Qwen3.8 Flash (off), pinned) and the label "helper-written notes → decision player" stated above the table before the first call;
   - the plan text "not tested: cannot write lessons" (in `REQUIRED` and `others()`) is replaced by the decision rows, and the validator's required phrases change with it.
   - About half a day.
8. **Ops:** existing server scripts with `*_GPU` set to the released card's UUID, one model per card, claims on the bus, the Xid watch. The current lanes are untouched.

## 9. Decided in this revision

- **D3 placement:** start of `state` / `input` (§2).
- **D4 wording:** the pilot prompt stays byte-identical; the intro line is "Notes a helper wrote from your earlier games in this series, oldest first:" (§2, §4).
- **D9 Arm W content:** board, chosen play, best play, loss; no descriptions (§5).
- **D10 delivery evidence:** Lr / Hc / "delivery unverified", no canary (§6.1).

## 10. Open decisions for Ümit

- **D1 Empty runs:** one set per arm (the default) or shared by both arms. Sharing saves 600 decisions per model (~$0.8 booked over the runnable hosted rows) but makes both verdicts use the same baseline, and needs one schedule interleaving both arms' series.
- **D2 Cygnet:** keep it excluded (#3111) or add it (its earlier reason was our runner; sizing fits).
- **D5 Edge settings:** with settings unchanged, are these eligible or "not tested"?
  - Base Labs past the trained 16,384 tokens (Elephant: N; Mammoth: both arms);
  - REAX's read-twice → read-once switch.
  - Winnow and Clef keep their option caps in either case.
- **D6 Money allocation:**
  - do the non-OpenRouter providers count against the $110 total, and with what per-provider allocation?
  - Nace's $1.25 subcap is below the ~$3.45 booked (~$2.58 billed by Nace) that both hosted Drex setups need with separate empty runs (~$3.13 / $2.34 shared).
  - No paid hosted work starts before this.
- **D7 Identity:** Celeris's docs now name `celeris-1.1-decision`, while the row used `celeris-1-decision`; SubQ Snap Preview has left SubQ's docs. If the frozen id is not served as on the leaderboard, is "not tested: model id not served as on the leaderboard" right?
- **D8 Drex 2.0 settings:** test the hosted setup only (the row's), or both it and Drex 2.0 (local)?
