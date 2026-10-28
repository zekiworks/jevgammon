# Nackgammon: GPT-6.1 Terra (high), cost and time estimate (2026-10-28)

Can's ask: add GPT-6.1 Terra at reasoning effort **high** to the Nackgammon paired test, **exploratory** (added after the paired results were known; not a primary comparison; M stays 5). **Before any model call.** Nothing below has been run; no model was called. Databases read read-only.

**Everything here is an estimate: Terra (high) has no logs.** It is built from Terra (low)'s real logs times an effort multiplier measured on other models.

## Setup to run

Terra (low)'s stored entry (`leagues/nack-paired.json`, "GPT-6.1 Terra") with `reasoning: "high"` and its own name, e.g. "GPT-6.1 Terra (high)": `openai-compatible/openai/gpt-6.1-terra` via OpenRouter, pinned to OpenAI (`order: [openai]`, fallbacks off, `require_parameters`), `usage.include`, `temperature`/`logprobs`/`top_logprobs` null, letter readout `answer`, `max_tokens` 8000, `parallel` 4, `rpm` 18, prompt and option-order seed as in the paired run, own budget ledger.

OpenRouter metadata today (`/api/v1/models`, no key): `openai/gpt-6.1-terra` has `reasoning_effort` among its supported parameters and `supported_efforts` = max, xhigh, **high**, medium, low, none (default medium). Price unchanged: prompt $1/M, **cache write $1.25/M** (what OpenRouter bills every Terra prompt as), cache read $0.05/M, output $5/M (prompts under 272k tokens).

## Terra (low): real logs

| Source | Decisions | Input tok/dec | Output tok/dec (reasoning) | Max output | $ per decision (billed) | Mean / max latency | Wall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Smoke, `smoke/terra-smoke.db` | 50 | 3,087 | 79 (65) | 446 | $0.00425 ($0.213 total) | 2.5 / 6.8 s | 2.8 min |
| Paired, `smoke/nack-paired.db` (main + reserve) | 1,000 (0 errors) | 2,603 | 91 (78) | 556 | $0.00371 ($3.71 total; ledger c: 400 for $1.49) | 2.7 / 10.1 s | 56 min (19:06–20:02 UTC): set by the 18 rpm limit |

Per paired decision: input $0.00325 (2,603 × $1.25/M, 88% of the cost), output $0.00046. The effort level changes only the output part.

## Effort multiplier (high vs low)

| Model, source | Output tok/dec low → high | × output | Mean latency low → high | × latency |
| --- | --- | --- | --- | --- |
| GPT-6.1 Sol, this paired run (1,000 each) | 80 → 285 (reasoning 64 → 268); max 363 → 2,744 | **3.6** | 5.6 → 13.2 s | 2.3 |
| GPT-6.1 Sol, `v3.db` league decisions | 113 → 463 | 4.1 | 6.6 → 21.2 s | 3.2 |
| Claude Sonnet 5.5, `v3.db` | 230 → 838 | 3.6 | 3.5 → 8.8 s | 2.5 |
| Claude Opus 5.5 (off → on), `v3.db` | 266 → 646 | 2.4 | 5.3 → 9.8 s | 1.9 |
| Grok 4.7 (off → on), `v3.db` | 3,408 → 17,090 | 5.0 | 61 → 234 s | 3.8 |
| Gemini 3.8 Flash, `v3.db` | 240 → 5,151 | 21 (outlier) | 3.9 → 20.4 s | 5.3 |

Fields: Sol runs on the ChatGPT subscription, but the stored rows have input, output and reasoning tokens and latency for every decision (1,000/1,000 in the paired run; all `v3.db` model decisions of these setups); its `cost_usd` is only the list-price equivalent, not billed. `v3.db` turns have no setup at low/high effort with OpenRouter-billed cost.

**Used:** output × **4** central (range 2.4–5 from the same-family and other low/high pairs); **× 8 worst case** (Sol's max output rose 7.6×; Gemini Flash's 21× is kept as the outlier that a hard cap guards against). Latency × 2.3–3.2 (worst 5.3). +5% retries on the worst case (Terra (low) had 0 failures).

Per paired decision: central $0.00325 + 365 × $5/M = **$0.0051**; worst ($0.00325 + 730 × $5/M) × 1.05 = **$0.0073**. Smoke (3,087 input): central $0.0054, worst $0.0074.

## The three rows (kept separate)

| Row | What | Decisions | OpenRouter $ central | OpenRouter $ worst | Wall time |
| --- | --- | --- | --- | --- | --- |
| a | Smoke test, Terra (low)'s procedure: the 50 positions of `positions/smoke.jsonl`, bg-v2, the leagues' option-order seed, plus the reference comparisons (Δ vs GPT-6.1 Sol (low) and Gemini 3.8 Flash (low), and here vs Terra (low): stored answers, no calls) | 50 | **$0.27** | **$0.37** | about 3–4 min |
| b | Paired start: main 200 pairs, both sides | 400 | **$2.03** | **$2.90** | about 22–30 min |
| c | Worst-case extension to 1,000 (+600 reserve) | +600 | **$3.05** | **$4.35** | about 33–45 min |

a + b + c: $5.35 central, $7.62 worst. Time: at parallel 4 and 6–9 s per decision Terra (high) still makes 27–37 requests a minute, so the **18 rpm limit** sets the pace as for Terra (low) (400 → 22 min, 1,000 → 56 min); the upper ends allow for latency × 5.3 (then about 17 a minute) and the slow tail. `max_tokens` 8000 means the ledger reserves up to $0.044 per attempt in flight, so each row's cap needs about $0.20 headroom over its worst case.

## Credit and what fits, in order

OpenRouter `/api/v1/credits` today: $120.00 total − $112.77 used = **$7.23 left**. Can is adding about **$2** (≈ $9.23). Queued against the same credit first: the **4 DeepSeek V4.1 Flash 1017 (on) gap matches, est. $2.39, worst $3.60**.

| Step | Central (cumulative left of $9.23) | Worst (left of $9.23) | Worst, without the $2 (left of $7.23) |
| --- | --- | --- | --- |
| DeepSeek 1017 (on) gap matches | $2.39 → $6.84 | $3.60 → $5.63 | $3.60 → $3.63 |
| a. Terra (high) smoke | $0.27 → $6.57 | $0.37 → $5.26 | $0.37 → $3.26 |
| b. Paired start (400) | $2.03 → $4.54 | $2.90 → $2.36 | $2.90 → $0.36 |
| c. Extension (+600) | $3.05 → **$1.49 left: fits** | $4.35 → **short by $1.99** | $4.35 → **short by $3.99** |

So with the $2 added: the DeepSeek matches, a and b fit even at their worst; c fits at the central estimate but not at the worst case (cap it at what is left, about $2.3, and report Terra (high) with what it answered). Without the $2, a and b only just fit after DeepSeek at the worst case; c does not. Row b's real cost per decision, known after a, will tighten c.

Waiting for Can's go.
