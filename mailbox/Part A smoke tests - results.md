# Part A smoke tests: results

Oct 21, 2026 · Part A of `workspace/backgammon-site-brief.md`

Every API setup answered the usual 50 smoke positions (`positions/smoke.jsonl`: expert GNUbg self-play games 11000–11050, 10 per phase, outside every shared set; the same 50 as `mailbox/v3 smoke test.md`). They went through the league runner (`jevgammon ask`) with the leagues' bg-v2 prompt, the leagues' seeded shuffled option order (order_seed 1190975713392774006) and the leagues' fallbacks, so each model saw exactly what the leagues show. Each decision had a 600 s wall-clock limit (new `--time-limit` flag). A decision over the limit is counted as **timed out**, apart from failed and invalid. Scoring uses `smoke/score.db` (GNUbg 1.08, 2-ply, every legal play). The runs used runner commit 0a97729 plus the `--time-limit` change, committed with this report. No setup joined a league, and nothing touched the league runner, v3.db, the servers or the GPUs.

**Reference.** Gemini 3.8 Flash (low), run twice:
- today through the Antigravity subscription, the route League 2 uses;
- the stored answers of **Oct 14, 2026** (Gemini API, `smoke/answers.db`).

Every row gets a paired difference from both. The two references are the same model at the same setting, yet they differ by **+5.0 [−2.9, +15.1]**. That gap is the run-to-run noise of temperature-1 sampling on 50 positions. So read any difference under about 10 as noise, whatever its interval says.

**Spend.**
- OpenRouter: $56.63 used of $65.00 at the start, so $8.37 left (the brief said about $8.7). After the runs: $58.66 used, so **$2.03 spent** (about $0.25 of it on endpoint probes) and **$6.34 left**.
- Subscriptions: no money spent. Their API-equivalent is $10.48, mostly Claude Fable 5.1 ($6.28) and Grok 4.7 ($3.97).
- No paid setup was projected above $4 for 50 positions, so none needed the 20-position check first.

## Table

| Setup | Model ID · provider (pinned) · run | Weights | Reasoning settings available | Temp. | Probabilities | Context limit · plays split? | Rules text | Answers / failed / timed out | Invalid | Request s p50 / p90 · retry+wait s mean | Tokens in / out (reasoning) per decision | $ per 1,000 decisions · price in/out per M tokens, date, label | Error rate [95% CI] | Δ vs reference today [95% CI] | Δ vs reference Oct 14 [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Gemini 3.8 Flash (low) [antigravity]** | `gemini-3.8-flash` (Antigravity id `gemini-3.8-flash-low`) · Antigravity subscription · 2026-10-21 | closed | minimal / low / medium / high (default high); **run: low** | 1.0 | none (choice only) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 2.9 / 6.0 · 0.0 | 3244 / 276 (273) | 3.47 · $0.75 / $3.75 (OMP cache, 2026-10-21) · API-equivalent (subscription) | 13.6 [5.4, 24.3] | reference | +5.0 [-2.9, +15.1] (n=50) |
| **Gemini 3.8 Flash (low)** | `gemini-3.8-flash` · Gemini API · **2026-10-14** (stored answers, v3 smoke test) | closed | as above; **run: low** | 1.0 | none (choice only) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 1.6 / 5.6 · 0.0 | 3386 / 195 (194) | 3.27 · $0.75 / $3.75 (2026-10-14) · API price | 8.5 [2.8, 16.4] | -5.0 [-14.9, +2.9] (n=50) | reference |
| **Claude Haiku 5.5 (low)** | `claude-haiku-5-5` · Claude subscription · 2026-10-21 | closed | adaptive thinking; effort low / medium / high / xhigh / max; **run: low** | not sent (API default 1.0) | none (choice only) | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 1.4 / 1.6 · 0.0 | 4271 / 20 (9) | 0.44 · $0.10 / $0.50 (OMP cache + OpenRouter, 2026-10-21) · API-equivalent (subscription) | 18.0 [9.1, 28.0] | +4.4 [-7.1, +15.2] (n=50) | +9.5 [+2.7, +17.7] (n=50) |
| **Claude Haiku 5.5 (high)** | `claude-haiku-5-5` · Claude subscription · 2026-10-21 | closed | adaptive thinking; effort low / medium / high / xhigh / max; **run: high** | not sent (API default 1.0) | none (choice only) | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 3.2 / 6.2 · 0.0 | 4271 / 526 (515) | 0.69 · $0.10 / $0.50 (OMP cache + OpenRouter, 2026-10-21) · API-equivalent (subscription) | 21.1 [10.1, 33.9] | +7.5 [-0.6, +17.1] (n=50) | +12.5 [+3.0, +24.0] (n=50) |
| **Claude Fable 5.1 (low)** | `claude-fable-5-1` · Claude subscription (also in League 3 as (off)) · 2026-10-21 | closed | adaptive only (thinking off rejected); effort low / medium / high / xhigh / max; **run: low** | not sent (API default 1.0) | none (choice only) | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 1.7 / 2.5 · 0.0 | 4271 / 82 (71) | 46.83 · $10 / $50 (2026-10-21) · API-equivalent (subscription) | 11.7 [4.8, 20.5] | -1.9 [-12.7, +7.8] (n=50) | +3.2 [-0.7, +8.6] (n=50) |
| **Claude Fable 5.1 (high)** | `claude-fable-5-1` · Claude subscription (also in League 3 as (off)) · 2026-10-21 | closed | adaptive only (thinking off rejected); effort low / medium / high / xhigh / max; **run: high** | not sent (API default 1.0) | none (choice only) | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 6.7 / 30.8 · 0.0 | 4271 / 719 (708) | 78.66 · $10 / $50 (2026-10-21) · API-equivalent (subscription) | 9.0 [2.2, 18.5] | -4.5 [-9.2, -1.0] (n=50) | +0.5 [-6.6, +9.6] (n=50) |
| **Mercury 3 (off)** | `inception/mercury-3` · OpenRouter → `inception` (only endpoint; quantization not published) · 2026-10-21 | closed | off (`reasoning.enabled: false`) / minimal / low / medium / high; no setting = reasons (~14k hidden tokens); reasoning text never returned; **run: off** | 1.0 | none (choice only); unconstrained letter | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 2% | 0.5 / 1.5 · 0.0 | 2990 / 4 (0) | 0.29 · $0.10 / $0.35 (2026-10-21) · API price (OpenRouter-billed) | 22.9 [12.8, 34.3] | +9.0 [-3.5, +21.4] (n=49) | +14.2 [+6.5, +23.9] (n=49) |
| **Mercury 3 (low)** | `inception/mercury-3` · OpenRouter → `inception` (only endpoint; quantization not published) · 2026-10-21 | closed | off (`reasoning.enabled: false`) / minimal / low / medium / high; no setting = reasons (~14k hidden tokens); reasoning text never returned; **run: low** | 1.0 | none (choice only); unconstrained letter | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 10% | 23.0 / 78.7 · 0.0 | 2987 / 13524 (13519) | 4.85 · $0.10 / $0.35 (2026-10-21) · API price (OpenRouter-billed) | 23.6 [10.5, 39.0] | +12.2 [+2.0, +26.0] (n=45) | +17.8 [+5.5, +33.7] (n=45) |
| **MiMo V2.6 Pro (off)** | `xiaomi/mimo-v2.6-pro` · OpenRouter → `xiaomi/fp8` (Xiaomi's own) · 2026-10-21 | open (HF `XiaomiMiMo/MiMo-V2.6-Pro-RL`/`-MOPD`; which one the API serves is not published) | off / minimal / low / medium / high; no setting = reasons; **run: off** | 1.0 | none (choice only) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 2.2 / 3.4 · 0.0 | 3209 / 8 (0) | 0.64 · $0.435 / $0.87 (2026-10-21) · API price (OpenRouter-billed) | 25.9 [11.9, 42.9] | +12.3 [-2.6, +29.1] (n=50) | +17.4 [+5.8, +32.2] (n=50) |
| **MiMo V2.6 Pro (high)** | `xiaomi/mimo-v2.6-pro` · OpenRouter → `xiaomi/fp8` (Xiaomi's own) · 2026-10-21 | open (HF `XiaomiMiMo/MiMo-V2.6-Pro-RL`/`-MOPD`; which one the API serves is not published) | off / minimal / low / medium / high; no setting = reasons; **run: high** | 1.0 | none (choice only) | 1,048,576 · no (one request) | long (bg-v2 rules) | 42 / 0 / 8 | 0% | 23.6 / 346.1 · 0.0 | 3132 / 4333 (4324) | 4.05 · $0.435 / $0.87 (2026-10-21) · API price (OpenRouter-billed) | 7.2 [2.0, 14.0] | -1.7 [-13.3, +7.5] (n=42) | +2.7 [-1.5, +7.9] (n=42) |
| **Beam 1.0 (low)** | `reflection/beam-1.0-501b-a23b` · OpenRouter → `nebius/fp8` · 2026-10-21 | open (HF `reflection/Beam-1.0-501B-A23B`) | mandatory (off rejected); minimal / low / medium / high / xhigh; **run: low** | 1.0 | per answer letter (logprobs) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 7.7 / 16.2 · 0.0 | 3248 / 1548 (1539) | 1.99 · $0.25 / $1.00 (2026-10-21) · API price (OpenRouter-billed) | 15.1 [7.3, 24.2] | +1.6 [-9.0, +10.6] (n=50) | +6.6 [+1.0, +13.3] (n=50) |
| **Beam 1.0 (high)** | `reflection/beam-1.0-501b-a23b` · OpenRouter → `nebius/fp8` · 2026-10-21 | open (HF `reflection/Beam-1.0-501B-A23B`) | mandatory (off rejected); minimal / low / medium / high / xhigh; **run: high** | 1.0 | per answer letter (logprobs) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 34.5 / 72.9 · 0.0 | 3249 / 8227 (8218) | 8.67 · $0.25 / $1.00 (2026-10-21) · API price (OpenRouter-billed) | 15.0 [5.9, 26.7] | +1.4 [-8.9, +12.2] (n=50) | +6.5 [-3.8, +18.4] (n=50) |
| **MiMo V2.6 Flash (off)** | `xiaomi/mimo-v2.6-flash` · OpenRouter → `makora/fp8` · 2026-10-21 | open (HF `XiaomiMiMo/MiMo-V2.6-Flash-RL`/`-MOPD`) | off / minimal / low / medium / high; **run: off** | 1.0 | per answer letter (logprobs) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 10% | 0.9 / 2.7 · 0.0 | 3209 / 31 (0) | 0.14 · $0.13 / $0.28 (2026-10-21) · API price (OpenRouter-billed) | 12.5 [5.7, 20.6] | +0.8 [-10.8, +11.1] (n=45) | +6.4 [+0.6, +13.8] (n=45) |
| **MiMo V2.6 Flash (off, unconstrained)** | `xiaomi/mimo-v2.6-flash` · OpenRouter → `makora/fp8` · 2026-10-21 | open (HF `XiaomiMiMo/MiMo-V2.6-Flash-RL`/`-MOPD`) | off / minimal / low / medium / high; **run: off** | 1.0 | per answer letter (logprobs); unconstrained letter | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 4% | 0.8 / 1.6 · 0.0 | 3209 / 3 (0) | 0.02 · $0.13 / $0.28 (2026-10-21) · API price (OpenRouter-billed) | 15.9 [7.9, 25.7] | +5.3 [-7.2, +17.1] (n=48) | +10.1 [+3.0, +19.3] (n=48) |
| **MiMo V2.6 Flash (low)** | `xiaomi/mimo-v2.6-flash` · OpenRouter → `makora/fp8` · 2026-10-21 | open (HF `XiaomiMiMo/MiMo-V2.6-Flash-RL`/`-MOPD`) | off / minimal / low / medium / high; **run: low** | 1.0 | per answer letter (logprobs) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 28% | 39.5 / 332.7 · 0.0 | 3207 / 12660 (12653) | 3.62 · $0.13 / $0.28 (2026-10-21) · API price (OpenRouter-billed) | 7.7 [1.6, 15.4] | +4.4 [-0.2, +11.4] (n=36) | +3.9 [+0.1, +9.6] (n=36) |
| **Kimi K3 (low)** | `moonshotai/kimi-k3` · OpenRouter → `inference-net/fp4` · 2026-10-21 | open (HF `moonshotai/Kimi-K3`) | low / high / max, an effort is required (no off); default max; **run: low** | 1.0 | none (choice only) | 1,048,576 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 16.5 / 42.2 · 0.6 | 3232 / 723 (716) | 9.35 · $0.239 / $11.936 (2026-10-21) · API price (OpenRouter-billed) | 16.7 [7.2, 28.2] | +3.2 [-1.7, +9.9] (n=50) | +8.2 [+0.6, +18.4] (n=50) |
| **Hy4 Preview (off)** | `tencent/hy4-preview` · OpenRouter → `tencent/fp8` (Tencent's own) · 2026-10-21 | open (HF `tencent/Hy4-preview`) | off / low / medium / high; **run: off** | 1.0 | none (choice only) | 1,048,576 (max output 64,000) · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 2.7 / 4.0 · 0.0 | 3069 / 8 (0) | 1.71 · $0.834 / $2.501 (2026-10-21) · API price (OpenRouter-billed) | 20.9 [10.8, 33.5] | +7.3 [-5.0, +20.5] (n=50) | +12.4 [+4.1, +23.8] (n=50) |
| **MiniMax M3.1 Flash (low)** | `minimax/minimax-m3.1-flash:free` · OpenRouter → `minimax` (only listing: free) · 2026-10-21 | not on Hugging Face (MiniMaxAI's newest: M3, M3-MXFP8) → treat as closed | mandatory; low / medium / high / xhigh / max; **run: low** | 1.0 | none (choice only); unconstrained letter | 1,000,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 4.3 / 10.7 · 7.1 | 3225 / 393 (391) | 0.72 · $0.15 / $0.60 (MiniMax list, OMP cache, 2026-10-21) · API-equivalent (free endpoint) | 22.1 [9.4, 38.3] | +8.6 [-6.4, +25.9] (n=50) | +13.6 [+2.3, +29.0] (n=50) |
| **Grok 4.7 (low)** | `grok-4.7` · xAI subscription (OMP xai-oauth; also in League 3) · 2026-10-21 | closed | low / medium / high / xhigh (minimal served as low; none rejected); default high; **run: low** | not sent | none (choice only) | 500,000 · no (one request) | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 18.7 / 64.2 · 0.0 | 4354 / 2011 (2005) | 20.77 · $2 / $6 (2026-10-21) · API-equivalent (subscription) | 9.5 [2.8, 18.0] | -4.1 [-14.9, +5.0] (n=50) | +0.9 [-2.6, +5.9] (n=50) |
| **Grok 4.7 (high)** | `grok-4.7` · xAI subscription (OMP xai-oauth; also in League 3) · 2026-10-21 | closed | low / medium / high / xhigh (minimal served as low; none rejected); default high; **run: high** | not sent | none (choice only) | 500,000 · no (one request) | long (bg-v2 rules) | 46 / 0 / 4 | 0% | 69.2 / 264.6 · 0.0 | 4336 / 9178 (9172) | 63.74 · $2 / $6 (2026-10-21) · API-equivalent (subscription) | 6.5 [0.9, 14.7] | -6.9 [-17.6, +2.0] (n=46) | -1.4 [-4.1, +0.7] (n=46) |
| **d3-turbo** | `vllm-sr/d3-turbo` @ `a0f3e9e59ebd1202fe1d4de1c4c0f9a986758cbb` · our GPU, package's own `d3_server.py` (System One) on :18100, bf16 | open (Apache 2.0) | none (decision model, no text generated) | softmax T 1.0 | per option (decision model) | 32,768 tokens per question, up to 255 options (runner sends ≤ 200) · no | long (bg-v2 rules; the runner sends it to decision models too) | **waiting for a free GPU** (needs ~52–56 GB on one GPU) |  |  |  | own hardware |  |  |  |
| **Nemotron 3.5 Bolt (off)** | `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB` @ `cf2effc5` · our GPU, vLLM nightly `77154ca6` on :8893 (IQ2_XXS experts, NVFP4/Q8_0 elsewhere, fp8 KV) | open | thinking off / on (`enable_thinking`); only effort knob `medium_effort` | 1.0 | per answer letter (prefill logprobs, top 20) | 262,144 (served 65,536) · no | long (bg-v2 rules; the runner sends it to decision models too) | **waiting for a free GPU** (~50 GB on one GPU) |  |  |  | own hardware |  |  |  |
| **Nemotron 3.5 Bolt (on)** | as (off), thinking on (template default, full effort), max_tokens 32,000 | open | as above | 1.0 | per answer letter (after the reasoning) | as above | long (bg-v2 rules; the runner sends it to decision models too) | **waiting for a free GPU** |  |  |  | own hardware |  |  |  |
| **Nemotron 3.5 Bolt BF16 (off) / (on)** | `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16` @ `56702103` · two GPUs, TP2 (alternative to the 2-bit 24GB build) | open | as above | 1.0 | per answer letter | as above | long (bg-v2 rules; the runner sends it to decision models too) | **waiting for a free GPU** (two GPUs, ~88 GB each; 150 GB download) |  |  |  | own hardware |  |  |  |
| **Fastino GLiDE v1.2 (local)** | `fastino/GLiDE` @ `a7e45896be7c96ba3354891da790c5ec99c30b6c` (served name `glide-v1.2`) · our GPU (bariton GPU 0, RTX PRO 6000), the repo's own `glide/server.py` (System One) on :18101, bf16, `GLIDE_MAX_BATCH=1` · **2026-10-22** (`smoke/glide-v12.db`, `leagues/smoke-glide-v12.json`) | open (Fastino Community License; Qwen3.8-27B modification) | none (decision model, no text generated) | softmax T 1.0 (`decision_config.json`) | per option (decision model) | 40,000 tokens per question, up to 255 options · no | long (bg-v2 rules; the runner sends it to decision models too) | 50 / 0 / 0 | 0% | 2.7 / 9.1 · 0.0 (fresh process: Triton compiles kernels on first use of each shape; card: ~0.1 s warm) | 3317 / 0 (–) | own hardware | 22.5 [10.6, 37.5] | +9.0 [-5.1, +24.6] (n=50) | +14.0 [+4.1, +27.9] (n=50) |
| **Fastino GLiDE (API)** | `fastino/GLiDE` · Fastino's hosted API (responses name the model `glide_v2`), League 1's "Fastino GLiDE" · 2026-10-22 (same db and config) | closed (hosted) | none (decision model) | not sent | per option (decision model) | 255 options · no | long (bg-v2 rules) | 50 / 0 / 0 | 0% | 0.7 / 0.8 · 0.0 | 3317 / 0 (–) | no price recorded | 20.0 [8.9, 34.0] | +6.4 [-6.8, +21.2] (n=50) | +11.5 [+2.9, +24.5] (n=50) |
| **Hy4 Preview (on)** | `tencent/hy4-preview` · `tencent/fp8` | open | off / low / medium / high | 1.0 | none | 1,048,576 | long | **not run**: one low-effort probe took 321 s, 19,850 reasoning tokens, $0.053 → about $2.60 and ~35 min per 50 | | | | | | | |
| **Mistral Large 4** | `mistral-large-4-0` (Mistral API; OpenRouter `mistralai/mistral-large-4-0`, $1.36 / $4.18) | **weights not out**: no Mistral Large 4 repo on Hugging Face on 2026-10-21 (mistralai's newest Large is `Mistral-Large-3-675B-Instruct-2512`) | | | | | | no test (as asked) | | | | | | | |

**How to read the table**
- **Error rate:** mean 2-ply equity loss × 500, counting valid answers only. An invalid answer's random play is not the model's choice (brief B11), so it is left out here and shown in the Invalid column instead.
- **Interval:** 95% bootstrap over positions, 10,000 resamples.
- **Δ (paired difference):** setup minus reference, on the positions both answered validly (n), with a 95% bootstrap interval over those positions.
- **Time:** request seconds per decision, retries excluded. Retry and wait time (rate-limit pacing, backoff) is shown separately.
- **Tokens:** means per decision. Reasoning tokens are as the provider reports them.
- **$ per 1,000 decisions:**
  - OpenRouter rows: what OpenRouter billed, including prompt-cache discounts. So MiMo off and Mercury off cost less than tokens × list price.
  - Subscription rows and the free MiniMax endpoint: tokens × the listed price.
  - Timed-out requests carry no recorded cost, though OpenRouter may still bill them.
- **Rules text:** the runner has no short rules text. Every setup, decision models included, gets the long bg-v2 rules (`prompts/bg-v2.md`) in its state. So for v3 data the B7 field "rules text" is "long" for every setup.
- **Plays split into groups:** never. The smoke positions have 2–24 legal plays. Chat models take 26 letters, d3-turbo up to 200 options.
- **Sampling:** temperature 1.0 wherever the runner sends one. Anthropic and xAI requests send none, so their API defaults apply.

## What the runs showed

1. **Probabilities.**
   - **Per answer letter:**
     - Beam 1.0, through Nebius fp8. Its BaseTen and Together endpoints also list logprobs.
     - MiMo V2.6 Flash, through Makora fp8. Io Net also lists them; Xiaomi's own endpoint does not.
   - **None:**
     - **Mercury 3.** Its only OpenRouter endpoint (Inception) lists no logprobs. A pinned request asking for them is refused (404), and an unpinned one comes back with `logprobs: null`. Inception's own API was not tried: there is no key.
     - **MiMo V2.6 Pro.** None of its five endpoints offers logprobs.
     - **Kimi K3.** I used InferenceNet fp4. Morph fp8 lists logprobs but returned none on a probe, at $0.035 per decision.
     - **Hy4 Preview, MiniMax M3.1 Flash, the Claude models and Grok:** no logprobs.
   - **d3-turbo:** per-option probabilities (decision model), not yet run.
   - **Nemotron:** letter logprobs through vLLM, not yet run.
2. **Adapter quirks (all settings are in `leagues/smoke-parta.json`).**
   - **Mercury 3:**
     - With reasoning off, a JSON-schema (or json_object) request returns empty content on 2 of 3 probe positions.
     - With reasoning on, it returns a JSON array of prose ("API output protocol …") on 3 of 3.
     - Both Mercury setups therefore answer with an unconstrained letter, which is parsed from the reply.
   - **MiMo V2.6 Flash (off) on Makora:** the JSON-schema reply ran out in whitespace on 5 of 50 positions, even with a 256-token cap. Those are the 10% invalid. The **unconstrained** row is the same model reading the letter's logprobs without the schema: 2 of 50 replies began in prose (4% invalid). Use whichever adapter you prefer; the two error rates overlap.
   - **MiniMax M3.1 Flash:** its only OpenRouter listing is the free one. It has no structured outputs, so it answers with an unconstrained letter (0 invalid). Its pacing at 18 requests a minute is the retry+wait column.
   - **Beam 1.0:** reasoning is mandatory, and disabling it is rejected (400).
   - **Kimi K3:** requires an effort, so it has no off setting.
3. **Invalid answers come from the 32,768-token output cap.** Every invalid answer in the reasoning-on rows reasoned past the runner's 32,768-token default and stopped (`finish_reason: length`) without a letter:
   - Mercury 3 (low): 5 of 50.
   - MiMo V2.6 Flash (low): 14 of 50. Its mean was 12,653 reasoning tokens; its median time was 39.5 s and its P90 333 s.
4. **Timed out at 600 s:** MiMo V2.6 Pro (high) 8 of 50 (P90 346 s), and Grok 4.7 (high) 4 of 50 (P90 265 s). Nothing failed outright.
5. **Reasoning levels are again far apart.** Mean reasoning tokens per decision:
   - "low": Claude Haiku 9, Claude Fable 71, Gemini Flash 273, Kimi K3 716, Beam 1,539, Grok 2,005, Mercury 13,519, MiMo Flash 12,653.
   - "high": Claude Haiku 515, Claude Fable 708, MiMo Pro 4,324, Beam 8,218, Grok 9,172.
6. **Error rates (descriptive; 50 positions, outside the shared sets, no ranking).**
   - **Lowest point estimates:**
     - Grok 4.7 high: 6.5 [0.9, 14.7] (46 answered)
     - MiMo V2.6 Pro high: 7.2 [2.0, 14.0] (42 answered; its 8 timeouts are the long, likely hard decisions, so it is biased low)
     - MiMo V2.6 Flash low: 7.7 [1.6, 15.4] (36 valid)
     - Claude Fable 5.1 high: 9.0 [2.2, 18.5]
     - Grok 4.7 low: 9.5 [2.8, 18.0]
   - **Highest:**
     - MiMo V2.6 Pro off: 25.9 [11.9, 42.9]
     - Mercury 3 low: 23.6 [10.5, 39.0]
     - Mercury 3 off: 22.9 [12.8, 34.3]
     - MiniMax M3.1 Flash low: 22.1 [9.4, 38.3]
     - Claude Haiku 5.5 high: 21.1 [10.1, 33.9]
   - **Paired against today's reference**, two intervals exclude zero:
     - Claude Fable 5.1 (high): −4.5 [−9.2, −1.0].
     - Mercury 3 (low): +12.2 [+2.0, +26.0].
   - **Against the Oct 14 reference** (which scored 8.5), most setups land above zero. Given the +5.0 gap between the two reference runs, that mostly says the Oct 14 run had a good draw.
   - No setup is clearly weak in the way Random (91) or Open-Jev (49) were in the v3 smoke test. Mercury 3 and MiMo V2.6 Pro (off) sit at the level of the v3 decision models, about 20–30.
7. **Fable 5.1 and Grok 4.7** are also in League 3. These 50-position runs are smoke-test rows only, and their effort names follow the brief (low/high), not League 3's labels "(off)/(on)".
8. **Fastino GLiDE v1.2 (local), added 2026-10-22** (before it joined League 1; details in `mailbox/GLiDE v1.2 - log.md`). No earlier GLiDE smoke answers existed, so Fastino's API (League 1's "Fastino GLiDE") answered the same 50 positions the same day. Paired, local minus API: **+2.5 [−0.2, +7.9]** (n=50). The two chose the same play on 48 of 50 positions; the largest probability gap was 0.022 and the median 0.007 (per-position maximum). That is within what the model card gives for batching or a different GPU type (up to 0.039). Error rates: 22.5 local, 20.0 API.

## Waiting for a free GPU (prepared, not run)

Nothing was loaded on a GPU. When one frees up:

```sh
CARGO_TARGET_DIR=target/parta cargo build --release        # already built; the leagues' target/release is untouched
D3_GPU=3 tools/v3/smoke_parta.sh d3                        # d3-turbo: start, probe, ask the 50, stop  (~52–56 GB, one GPU)
NEMOTRON_GPUS=3 tools/v3/smoke_parta.sh nemotron           # Nemotron 3.5 Bolt 24GB build (off, on)  (~50 GB, one GPU; first run pulls/builds the vLLM nightly image, ~9 GB)
NEMOTRON_GPUS=1,2 tools/v3/smoke_parta.sh nemotron-bf16    # optional: full-precision BF16, TP2 (two GPUs; 150 GB download)
tools/v3/smoke_parta.sh report                             # the table above, with the new rows (+ smoke/part-a.json)
```

If a local model runs next to a league, mark its timing "measured while leagues ran" (brief, section 0).

- **d3-turbo:**
  - Pinned to `a0f3e9e59ebd1202fe1d4de1c4c0f9a986758cbb` (the HF API sha on 2026-10-21).
  - The remote code was read in full: `tools/v3/servers/d3-turbo-code-review.md`. It has no subprocess, eval/exec, pickle or telemetry. It fetches from the Hub or URLs only when handed a repo id or URL. The server takes base64 media only and runs with `HF_HUB_OFFLINE=1` from the pinned local snapshot.
  - The 52 GB of weights are downloaded and checked against the package manifest.
  - It runs on the package's own `d3_server.py`, which already speaks System One, as the systemd user unit `v3-d3-turbo` on port 18100 (18099 is Decider v1.2). It uses `~/code/pplx-decider/.venv`, which has the pinned transformers 5.17.0 and flash-linear-attention 0.5.2.
  - New runner service `d3`; config `leagues/smoke-parta-d3.json`.
  - It answers one request at a time.
  - Untested: real memory use and speed. The vendor tested on ROCm; on NVIDIA it takes the plain transformers path.
- **Nemotron 3.5 Bolt 74B-A9B:**
  - Default: NVIDIA's one-GPU "24GB" build @ `cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f`, already downloaded. It is heavily quantized: routed experts IQ2_XXS (about 2 bits), NVFP4/Q8_0 elsewhere, fp8 KV cache.
  - It uses the LiLiCorr speculative drafter @ `449d2414`; `NEMOTRON_SPEC=0` turns it off if logprobs misbehave.
  - Alternative: the BF16 build @ `567021037ff88364143e24ea05e6abd0f72086ff` on two GPUs. It is closer to the model as published; I'd prefer it if two GPUs are free tonight.
  - It needs the vLLM nightly `77154ca6` that the model card names: the local v0.30.0 is too old. `fetch` builds it, plus `b12x` kernels. That build is untested.
  - Thinking switch: `chat_template_kwargs.enable_thinking`. (off) prefills `<think></think>Answer:`.
  - Configs: `leagues/smoke-parta-nemotron.json` and `leagues/smoke-parta-nemotron-bf16.json`. Script: `tools/v3/servers/nemotron35-bolt.sh` (port 8893).

## Weights checks (Hugging Face, 2026-10-21)

- **Mistral Large 4: weights are not out.** Hugging Face has no Large 4 repository. mistralai's newest Large is `Mistral-Large-3-675B-Instruct-2512`. Large 4 is API-only: Mistral `mistral-large-4-0`, and OpenRouter `mistralai/mistral-large-4-0` at $1.36 / $4.18 per million tokens.
- **MiniMax M3.1 Flash: no open weights found.** MiniMaxAI's Hugging Face models end at MiniMax-M3 (plus M3-MXFP8, H3, Music3), and a search for "MiniMax-M3.1" finds nothing. Today it is served only through MiniMax's API and OpenRouter's free listing. Until a repository appears, treat it as closed.
- **Open:**
  - Beam 1.0 (`reflection/Beam-1.0-501B-A23B`, plus FP8/NVFP4)
  - MiMo V2.6 Pro and Flash (`XiaomiMiMo/MiMo-V2.6-*-RL` and `-MOPD`; which one the APIs serve is not published)
  - Kimi K3 (`moonshotai/Kimi-K3`)
  - Hy4 preview (`tencent/Hy4-preview`, plus FP8)
  - d3-turbo
  - Nemotron 3.5 Bolt
- **Closed:** Mercury 3, the Claude models, Gemini and Grok.

## Blockers and what was left out

- **Not run yet, waiting for a free GPU:** d3-turbo and Nemotron 3.5 Bolt. They are prepared as described above.
- **Mercury 3 through Inception's own API:** not tried, because there is no Inception key. Logprobs were checked through OpenRouter only.
- **MiMo V2.6 Pro through a Xiaomi token-plan subscription:** not possible. OMP has no Xiaomi login; its only logins are openai-codex, anthropic, google-antigravity, xai-oauth, vllm and lm-studio. So MiMo ran pay-per-token on Xiaomi's own OpenRouter endpoint.
- **Optional setups not run:**
  - Hy4 Preview (on): slow and about $2.60 per 50; see its row.
  - Kimi K3 (high) and (max): left out to save credit. (low) already took $0.47 per 50.
- **Claude Haiku 5.5 with thinking fully off:** not tried. The runner sends an effort only, and low is the lowest effort it sends.

## Files

- `leagues/smoke-parta.json`: the API setups, with pinning, reasoning, readout and price notes.
- `leagues/smoke-glide-v12.json`, `tools/v3/servers/glide-v12.sh`, answers in `smoke/glide-v12.db` (+ `smoke/glide-v12.json`): Fastino GLiDE v1.2 (local) and Fastino's API.
- `leagues/smoke-parta-d3.json`, `leagues/smoke-parta-nemotron.json` and `leagues/smoke-parta-nemotron-bf16.json`: the local setups.
- `tools/v3/smoke_parta.sh` (api | d3 | nemotron | nemotron-bf16 | report).
- `tools/v3/smoke_report.py paired`: the intervals and paired differences.
- `tools/v3/servers/d3-turbo.sh`, `tools/v3/servers/nemotron35-bolt.sh` and `tools/v3/servers/d3-turbo-code-review.md`.
- Runner: `jevgammon ask --time-limit` (`src/ask.rs`, `src/main.rs`) and the `d3` decision service (`src/players/decision.rs`).
- Answers: `smoke/part-a.db` (git-ignored, like the other smoke databases), with every request and response in `answer_exchanges`. Machine-readable rows: `smoke/part-a.json`.
