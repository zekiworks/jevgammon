# Reasoning sweep: plan and estimate (2026-10-28)

**Estimates only. No sweep row has run.** The sweep would put each model's missing effort settings on the 500 frozen standard positions of the Nackgammon paired test (standard side, prompt `bg-v3-std-notable`, same option-order seed and frozen rules). The only calls made so far are the effort probe in §1: OpenRouter part done with Can's go; the subscription part runs when Season2 frees each subscription.

Sources:
- Logged tokens, latency and cost: `v3.db` turns (valid matches, model + fallback decisions), `smoke/nack-paired.db` (standard positions `nps-*`), `smoke/terra-codex-smoke.db`, `smoke/astra-high-smoke.db`, `smoke/argon-on-smoke.db`, `smoke/answers.db`, and "Reviewed brief 2026-10-24 - status" (Kimi max smoke).
- Prices: OpenRouter `/api/v1/models/<id>/endpoints` for the pinned endpoints, fetched today, and the roster list prices.

**Scaling rules used throughout (stated once):**
- **Paired prompt vs league prompt.** Paired/league output-token ratio from setups logged in both: OpenAI **0.65** (Sol low 0.70, Sol high 0.65, Astra 0.64); Claude **0.6** (Sonnet low 0.63, Fable high 0.55); Gemini Flash **1.0** (1.04); Grok **0.53**; OpenRouter models 0.65 (OpenAI figure, assumed). Paired input tokens per route, logged: OpenAI 2,599, Claude 3,672, Gemini 2,671 (Argon ≈ 2,690), Grok 3,868, DeepSeek 2,639, Qwen 2,697. Kimi ≈ 2,980 and GLM ≈ 2,690, both scaled from league × 0.68 (the DeepSeek ratio).
- **Latency, paired vs league:** OpenAI 0.78, Claude 0.6, Gemini 0.71, Grok 0.57.
- **Effort multiplier per step** = √(logged low→high output ratio), because low→high is two steps. Logged league pairs: Sol 115→465 (4.0×), Sonnet 234→852 (3.6×), Opus 266→646 (2.4×), Fable 116→1,362 (11.7×), Grok 3,408→17,090 (5.0×), Astra medium→high 110→264 (2.4×, one step). Result: central **2.0 per step**, range **1.5–3.4**. No published effort ratios are used.
- **Time** = latency × 500 / effective concurrency. Concurrency is busy/wall as observed in the paired runs: Codex 3, Claude 2.5 (Fable 4), Antigravity 2, xAI 7.5, OpenRouter 8 with ≤ 18 rpm.
- **Money.** Subscriptions: API-equivalent at list price, which is **not money**. OpenRouter: billed.

## 1. Effort probe per route

**What the probe is.** One tiny request per effort value per model, nothing scored.
- Prompt: system "Answer with the number only.", user "How many positive divisors does 7560 have?" (answer 64).
- Values: effort absent, `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Claude also gets `thinking: disabled`; DeepSeek 1017 also gets `reasoning.enabled: false`.
- Each request is the same route request the harness sends (`src/players/llm.rs`: endpoint, headers, effort field), with the play's JSON schema left out. Limits: `max_tokens` 512 on OpenRouter (cost cap) and 4,096 on subscriptions where the route takes a limit.
- Recorded per value: HTTP status, accepted or rejected (with the error), reasoning/output tokens, and what the response echoes (Codex/xAI `reasoning.effort`, Antigravity `modelVersion`, OpenRouter `provider`/`model`).
- Raw exchanges: `smoke/effort-probe.db` (tables `probes`, `ledger`). Script: `workspace/effort_probe.py` (not committed).
- Subscription tokens are read read-only and never refreshed by the probe; refresh stays with the running jobs.

**Cost and time:**
- About 8–10 requests per model.
- OpenRouter: 33 requests, **$0.0145 billed** (ledger, cap $0.10), 97 s. Credit was $1.7396 before. Afterwards it is about $1.725, which leaves ≥ $0.61 for Astra (high)'s Kimi match (worst case).
- Subscriptions: about 80 requests, $0, about 1–5 min per subscription (Grok xhigh longer).

### 1a. OpenRouter (done 16:03–16:05 UTC, Can's go)

OpenRouter does not echo the effort it applied, so a silent mapping cannot be seen in the response. Values outside a model's `supported_efforts` list were still accepted (with `require_parameters: true`), so OpenRouter presumably maps them to a listed value [INFERENCE]. Tokens on a prompt this small are too few to tell levels apart; the "reasoning" column is a one-sample count.

| Model (pinned endpoint) · listed efforts (default) | absent | none | minimal | low | medium | high | xhigh | max | other |
|---|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash 1017 (DeepSeek) · none/low/high/max (high) | ✓ 108 | ✓ **0** | ✓ 104 (not listed) | ✓ 135 | ✓ 158 (not listed) | ✓ 141 | ✓ 149 (not listed) | ✓ 108 | `reasoning.enabled:false` ✓ **0** |
| GLM-5.3 (Fireworks) · low/high/max (max) | ✓ 76 | **✗ 400 "Reasoning is mandatory for this endpoint and cannot be disabled."** | ✓ 11 (not listed; = low) | ✓ 11 | ✓ 11 (not listed; = low) | ✓ 32 | ✓ 26 (not listed) | ✓ 64 | |
| GPT-6.1 Terra (OpenAI) · none/low/medium/high/xhigh/max (medium) | ✓ 53 | ✓ **0** | ✓ 61 (not listed) | ✓ 55 | ✓ 56 | ✓ 54 | ✓ 51 | ✓ 97 | |
| Kimi K3.1 Pro (Moonshot mxfp4) · none/low/high/max (max) | ✓ 123 | ✓ **0** | ✓ 69 (not listed) | ✓ 73 | ✓ 60 (not listed) | ✓ 96 | ✓ 105 (not listed) | ✓ 119 | |

✓ = 200 accepted; the number is the reasoning tokens reported. Every answer was "64". Rows: `smoke/effort-probe.db` probes ids 2–34.

**No-reasoning setting available:**
- DeepSeek 1017: `none` or `reasoning.enabled:false`. This is the existing (off).
- Kimi: `none`. This is the existing (off).
- Terra (OpenRouter): `none`, new.
- GLM: none.
- Top value confirmed on the list and accepted: `max` for all four; mapping not detectable.

### 1b. Our vLLM Qwen3.8-27B template

The server (127.0.0.1:8897) was **not up** at 16:03 (connection refused). Probe **pending**: no server started, no GPU taken.

### 1c. Subscriptions

Season2 owns the running jobs. Each probe runs only when Season2 says that subscription is free, and the subscription is held until "done".

**Claude (done 18:13–18:14 UTC; Season2 held the subscription).** 30 requests, `smoke/effort-probe.db` rows with route `claude`. Request: `output_config.effort` as the harness sends it, `max_tokens` 4,096. Anthropic echoes no effort, so mapping is judged from the thinking tokens reported (`usage.output_tokens_details.thinking_tokens`) and whether a thinking block is present.

| Model | absent | none | minimal | low | medium | high | xhigh | max | `thinking: disabled` | `thinking: between_tools` |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 | ✓ 0 | ✗ 400 | ✗ 400 | ✓ 0 | ✓ 0 | ✓ 0 | ✓ **112** (thinking block) | ✓ **101** (thinking block) | ✗ 400 "not supported for this model. Use thinking.type.adaptive and output_config.effort" | ✗ 400 "not supported for this model" |
| Claude Opus 5.5 | ✓ 53 | ✗ 400 | ✗ 400 | ✓ 57 | ✓ 53 | ✓ 53 | ✓ 61 | ✓ **114** | ✗ 400 (same) | ✗ 400 "not supported for this model" |
| Claude Sonnet 5.5 | ✓ 0 | ✗ 400 | ✗ 400 | ✓ 0 | ✓ 0 | ✓ 0 | ✓ **59** (thinking block) | ✓ **200** (thinking block) | ✗ 400 "To turn thinking off on this model, send "thinking": {"type": "between_tools"} instead of {"type": "disabled"}" | ✓ **0 thinking tokens**, no thinking block (75 output tokens) |

✓ = 200, followed by the thinking tokens reported. The 400 text for `none`/`minimal` is: "output_config.effort: Input should be 'low', 'medium', 'high', 'xhigh' or 'max'".
- **Probed top: `max`, accepted on all three, not mapped down as far as the response shows.** Max used more thinking than high in every case: Fable 101 vs 0, Opus 114 vs 53, Sonnet 200 vs 0. `xhigh` is accepted too.
- On this tiny prompt, low, medium and high cannot be told apart (Fable and Sonnet did not think at all). This is a single sample.
- No response came near the limit: the largest was 203 output tokens, against `max_tokens` 4,096.
- **No-reasoning setting:** only **Claude Sonnet 5.5**, through `thinking: {"type": "between_tools"}` (0 thinking tokens). Fable and Opus have none: adaptive thinking only, with low as the lowest effort.

**ChatGPT (Codex), Antigravity, xAI:** pending. Season2 will free them (ChatGPT and Antigravity after the Astra (high) v Argon (on) match; xAI after Grok's paired run).

## 2. Sweep rows (b): missing partners on the 500 standard positions (estimates)

Each row is one setup, with **500 decisions**. Subscription rows: $0 billed, and the API-equivalent is not money.

| Setup (route) | Basis for output tok/dec | Input tok/dec | Output incl. reasoning tok/dec | Total tokens in / out | API-equivalent (not money) | Time |
|---|---|---|---|---|---|---|
| GPT-6 Astra (low) (Codex) | league low 101 × 0.65 | 2,599 | 66 | 1.30 M / 0.03 M | $14.6 | 15 min |
| GPT-6.1 Terra (low) (Codex) | Codex smoke low 16 | 2,599 | 16 | 1.30 M / 0.01 M | $1.3 | 7 min |
| GPT-6.1 Terra (high) (Codex) | Codex smoke high 209 | 2,599 | 209 | 1.30 M / 0.10 M | $1.8 | 14 min |
| Claude Fable 5.1 (low) | league low 116 × 0.6 | 3,672 | 70 | 1.84 M / 0.04 M | $20.1 | 7 min |
| Claude Opus 5.5 (low) | league low 266 × 0.6 | 3,672 | 160 | 1.84 M / 0.08 M | $8.9 | 10 min |
| Claude Opus 5.5 (high) | league high 646 × 0.6 | 3,672 | 390 | 1.84 M / 0.20 M | $11.2 | 19 min |
| Claude Sonnet 5.5 (high) | league high 852 × 0.6 | 3,672 | 510 | 1.84 M / 0.26 M | $6.2 | 18 min |
| Gemini 4 Argon (low) (Antigravity) | league low 26 (0 reasoning) | 2,690 | 26 | 1.35 M / 0.01 M | $2.8 | 17 min |
| Gemini 3.8 Flash (high) (Antigravity) | league high 5,209 × 1.0 | 2,671 | 5,210 | 1.34 M / 2.61 M | $10.8 | 55 min |
| Grok 4.7 (low) (xAI) | league low 3,408 × 0.53 | 3,868 | 1,810 | 1.93 M / 0.91 M | $9.3 | 29 min |
| Qwen3.8-27B (low) (our GPU) | league low 5,542 × 0.65 | ≈ 9,000 (the prefill readout resends the reasoning: 2 × 2,697 + 3,600) | 3,600 | 4.5 M / 1.8 M | $0 (GPU) | **≈ 2.3 GPU-h** at 8 streams × 27 tok/s (range 1.5–4 h), plus about 10 min server start. **Needs a compactor claim** (1 GPU, bariton) |

Not needed:
- Fable (high) and Grok (high) are already running in the paired test as Fable (on) / Grok (on).
- Argon (high) comes from the Nackgammon run (Argon (on)).
- Terra on OpenRouter (low, 500 answered) becomes the route check for Terra (low) on Codex.

**"If available" no-reasoning rows:**
- **Terra (none), OpenRouter:** accepted. About $1.6 billed for 500, based on the logged (low) run of $1.853 minus the output it saves.
- **Claude Sonnet 5.5 (off), via `thinking: between_tools`:** available (probe). Per decision: input 3,672, output ≈ 11 (the answer only; logged non-thinking replies). For 500 decisions: about $3.7 API-equivalent (not money) and about 5 min. Fable and Opus have no off.
- **Other subscriptions:** waiting for the probe. Notes already say Astra rejects none/minimal and Grok rejects none. For Gemini 3.8 Flash, Antigravity listed `minimal`; an estimate for it would be about the (low) cost.

**Sum of (b):** API-equivalent about $87 (not money). Per subscription, serial: ChatGPT ≈ 0.6 h, Claude ≈ 0.9 h, Antigravity ≈ 1.2 h, xAI ≈ 0.5 h, GPU ≈ 2.3 h.

## 3. OpenRouter models (c): estimate only, not planned now

Can: only after a top-up; skip for now.

| Setup | Basis | In / out tok/dec | Billed for 500 |
|---|---|---|---|
| DeepSeek V4.1 Flash 1017 (off/none) | non-1017 (off) paired billed $0.132 | 2,639 / 1 | ≈ $0.13 |
| DeepSeek V4.1 Flash 1017 (low) | league $4.69 / 1,000 × 0.65 | 2,639 / 4,570 | ≈ $1.5 |
| DeepSeek V4.1 Flash 1017 (max) | low × 4 (2 steps) | 2,639 / 18,300 [10,300–52,800] | ≈ $5.7 [3.3–16.0] |
| GLM-5.3 (low) | league $2.95 / 1,000 × 0.68 | 2,690 / 100 | ≈ $1.0 |
| GLM-5.3 (max) | low × 4 | 2,690 / 400 [230–1,160] | ≈ $2.8 [2.4–4.4] at list (logged billing ≈ half of list: caching) |
| Kimi K3.1 Pro (max) | logged max smoke: 9,810 out, 154 s, 13/50 timeouts | 2,980 / 9,810 | ≈ $52; **skipped (Can)** |

Credit: about $1.725 left, shared with the Turkish benchmark. After reserving $0.61 for Astra (high)'s Kimi match, about $1.11 is usable. That covers only DeepSeek 1017 (none) plus GLM (low).

## 4. Top-effort rows (Can, 2026-10-28): plan only, wait for Can's go before any starts

- **Output limit: 32,768 tokens on every top-effort row.** A cut-off answer is invalid under the frozen rule (it scores the position's Random error).
- **Cut-off rate column:** share of answers stopped at the limit (`stop_reason`/`finish_reason` = length/max_tokens, or Codex `response.incomplete`). It is reported with the invalid count.
- **Planned once the probe confirms the value:**
  - GPT-6 Astra, GPT-6.1 Sol and GPT-6.1 Terra (Codex) at `max`
  - Claude Opus 5.5, Sonnet 5.5 and Fable 5.1 at `max`
  - Grok 4.7 at `xhigh`
- Qwen3.8-27B (xhigh) when its server is up. DeepSeek 1017 / GLM max only after a top-up. Kimi max skipped. Geminis: high is the top, already run.
- Base = the model's highest logged setting, scaled as above. Steps high→max = 2, high→xhigh = 1.

| Row | Expected top (AA) | Probed top | Planned | Base (paired) | Input tok/dec | Output incl. reasoning tok/dec (central [range]) | Total tokens out (M) | API-eq. / billed for 500 | Time | Cut-off risk at 32,768 |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Astra (max), Codex | max | pending | if confirmed | high 172 | 2,599 | 690 [390–1,990] | 0.34 [0.19–1.0] | $30 [23–63] | 2.0 h [1.1–5.8] | low |
| GPT-6.1 Sol (max), Codex | max | pending | if confirmed | high 302 | 2,599 | 1,210 [680–3,490] | 0.60 [0.34–1.7] | $8.6 [6.0–20] | 2.6 h [1.4–7.4] | low |
| GPT-6.1 Terra (max), Codex | max | pending (OpenRouter: `max` accepted, listed) | if confirmed | high 209 | 2,599 | 840 [470–2,420] | 0.42 [0.24–1.2] | $3.4 [2.5–7.3] | 0.9 h [0.5–2.7] | low |
| Claude Opus 5.5 (max) | max | **max accepted**; not mapped down (thinking 114 vs 53 at high) | **yes** (wait for Can's go) | high 390 | 3,672 | 1,560 [880–4,510] | 0.78 [0.44–2.3] | $23 [16–52] | 1.2 h [0.7–3.6] | low (probe responses ≤ 203 tokens) |
| Claude Sonnet 5.5 (max) | max | **max accepted**; not mapped down (200 vs 0 at high) | **yes** (wait for Can's go) | high 510 | 3,672 | 2,040 [1,150–5,900] | 1.0 [0.57–2.9] | $14 [9–33] | 1.2 h [0.7–3.4] | low |
| Claude Fable 5.1 (max) | max | **max accepted**; not mapped down (101 vs 0 at high) | **yes** (wait for Can's go) | high 754 | 3,672 | 3,020 [1,700–8,720] | 1.5 [0.85–4.4] | $94 [61–236] | 1.6 h [0.9–4.7] | low–moderate (tail) |
| Grok 4.7 (xhigh), xAI | xhigh | pending | if confirmed | high 9,107 | 3,868 | 18,200 [13,700–31,000] | 9.1 [6.8–15.5] | $58 [45–97] | 4.9 h [3.7–8.3] | **high**: the mean is already more than half the limit, and Grok (on)'s league tail reaches far beyond it |
| Qwen3.8-27B (xhigh), our GPU | xhigh | pending (server down) | when the server is up | low 3,600 | ≈ 19,800 | 14,400 [8,100–41,600] | 7.2 [4.1–20.8] | $0 (≈ 9.3 GPU-h [5.2–27]) | ≈ 9.3 h | **high**: the upper range is above the limit |
| DeepSeek 1017 (max), OpenRouter | max | **max accepted, listed** | after top-up | low 4,570 | 2,639 | 18,300 [10,300–52,800] | 9.1 [5.1–26] | billed $5.7 [3.3–16] | 2.0 h [1.1–5.8] | **high** |
| GLM-5.3 (max), OpenRouter | max | **max accepted, listed** | after top-up | low 100 | 2,690 | 400 [230–1,160] | 0.2 [0.1–0.6] | billed $2.8 [2.4–4.4] | 0.5 h | low |
| Gemini 4 Argon / 3.8 Flash | high | (high is the top) | no row | — | — | — | — | — | — | — |

**Totals of the 7 subscription top rows (if all are confirmed):** 3,500 decisions. Output ≈ 13.8 M tokens [9.9–30.9 M]. API-equivalent ≈ $231 [162–509], not money. Time, serial per subscription: ChatGPT 5.5 h [3.0–15.9], Claude 4.0 h [2.3–11.7], xAI 4.9 h [3.7–8.3].

## 5. Time per subscription (d): one job at a time per subscription, subscriptions in parallel

Queue order per subscription (b rows first, then top rows), after Season2's current jobs:
- **ChatGPT (Codex):** Astra (low) 0.25 h → Terra (low) 0.1 h → Terra (high) 0.25 h → Astra (max) 2.0 h → Sol (max) 2.6 h → Terra (max) 0.9 h. **≈ 6.1 h** [3.6–16.5].
- **Claude:** Fable (low) 0.1 h → Opus (low) 0.2 h → Opus (high) 0.3 h → Sonnet (high) 0.3 h → Opus (max) 1.2 h → Sonnet (max) 1.2 h → Fable (max) 1.6 h. **≈ 4.9 h** [3.2–12.6]. It starts after Fable (on)'s paired run.
- **Antigravity:** Argon (low) 0.3 h → Gemini 3.8 Flash (high) 0.9 h. **≈ 1.2 h**, but queued behind Argon (on)'s paired run, which takes many hours (its smoke ran at 195 s per decision and 16,450 reasoning tokens).
- **xAI:** Grok (low) 0.5 h → Grok (xhigh) 4.9 h. **≈ 5.4 h** [4.2–8.8]. It starts after Grok (on)'s paired run.
- **Our GPU:** Qwen3.8-27B (low) ≈ 2.3 GPU-h, plus (xhigh) ≈ 9.3 GPU-h when approved. Needs a compactor claim.
- **OpenRouter:** after a top-up only.

**Wall time with subscriptions in parallel:** about 6 h once all four subscriptions are free, set by ChatGPT; up to about 17 h at the upper ranges. The GPU queue runs in parallel (≈ 2.3 h, or ≈ 12 h with xhigh).

Waiting for Can's go.
