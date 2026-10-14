# Backgammon v3: smoke test

Oct 14, 2026 · run order step 1 of the v3 design

Every setup of the three v3 rosters (`leagues/league1.json`, `league2.json`, `league3.json`) answered the same 50 positions through the league runner (`jevgammon ask`): same prompt (bg-v2), same seeded option order, same fallbacks as in the leagues. The positions come from expert GNUbg self-play games 11000–11050, which no shared set uses: 10 per phase (opening, contact, holding, race, bear-off), `positions/smoke.jsonl`. GNUbg 1.08 scored every legal play at 2-ply (`tools/v3/score.py`); 29 of the 50 positions are near-ties (the two best plays within 0.02), and nothing was rolled out. With 50 positions an error rate moves by several points from one position, so the error column is a sanity check, not a ranking.

Spend: about **$6.70** in real money (OpenRouter $3.84, Gemini API $2.77, SubQ $0.01, test requests about $0.10), under the $40 limit. Subscription setups (Claude, ChatGPT) cost nothing in money; their dollars below are API list-price equivalents.

## Table

Probabilities: "yes" = answer-letter or decision-model probabilities for the options; "choice only" = one constrained letter, left out of the confidence analyses. Seconds exclude retries. Invalid = no option named, so a random legal play was made (all invalid answers here were reasoning that ran past the output-token cap). Tokens are means per decision; reasoning tokens as the provider reports them (n/a = not reported). $ per 1,000 decisions: provider-reported cost (OpenRouter) or list price. Error rate = mean 2-ply equity loss × 500, invalid answers scored by the random play made. Best play = loss under 0.001; blunders = loss over 0.08.

| League | Setup | Reasoning | Answers | Failed | Probabilities | p50 s | p90 s | Invalid | Tokens in / out / reasoning | $ per 1,000 | Error rate | Best play | Blunders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Jev 1.13.0 | – | 0 | – | blocked: no key in the environment; TypeSafe account out of credit (402) | | | | | | | | |
| 1 | GPT-6 Luna | – | 0 | – | blocked: no OPENAI_API_KEY | | | | | | | | |
| 1 | Decider v1.1 27B | – | 50 | 0 | yes | 0.7 | 0.9 | 0% | 3489 / 0 / n/a | 0.07* | 28.7 | 58% | 22% |
| 1 | SubQ Snap Preview | – | 50 | 0 | yes | 0.3 | 0.3 | 0% | 3489 / 0 / n/a | 0.17 | 29.4 | 50% | 26% |
| 1 | Fastino GLiDE | – | 0 | – | blocked: no key | | | | | | | | |
| 1 | Celeris-1 Decision | – | 0 | – | blocked: no key | | | | | | | | |
| 1 | Clef | – | 50 | 0 | yes | 0.9 | 1.2 | 0% | 3596 / 0 / n/a | – | 30.2 | 58% | 28% |
| 1 | Open-Jev 27B v1.1 | – | 50 | 0 | yes | 1.3 | 1.8 | 0% | 27849 / 0 / n/a | – | 48.8 | 52% | 22% |
| 1 | Cygnet (Gemma 4 12B) | – | 50 | 0 | yes | 0.4 | 0.6 | 0% | 3844 / 1 / n/a | – | 19.7 | 56% | 18% |
| 1 | Gemma 4 31B (off) | off | 50 | 0 | yes | 0.9 | 1.2 | 0% | 3402 / 1 / 0 | – | 15.9 | 68% | 14% |
| 1 | Gemma 4 31B (on) | template default | 50 | 0 | yes | 177.9 | 329.9 | 0% | 10217 / 3421 / 3408 | – | 14.1 | 68% | 12% |
| 1 | Qwen3.8-27B (off) | off | 50 | 0 | yes | 0.6 | 3.8 | 0% | 3410 / 2 / 0 | 3.38 | 20.5 | 56% | 18% |
| 1 | Qwen3.8-27B (on) | low | 50 | 0 | yes | 2.9 | 7.6 | 0% | 3434 / 3797 / 3794 | 9.06 | 22.3 | 60% | 18% |
| 1 | Random | – | 50 | 0 | none | 0.0 | 0.0 | 0% | – | – | 91.2 | 32% | 44% |
| 1 | Safest | – | 50 | 0 | none | 0.0 | 0.0 | 0% | – | – | 22.1 | 44% | 24% |
| 1 | GNUbg weak | – | 50 | 0 | none | 0.0 | 0.0 | 0% | – | – | 20.1 | 52% | 20% |
| 2 | Gemini 3.8 Flash (low) | low | 50 | 0 | choice only | 1.6 | 5.6 | 0% | 3386 / 195 / 194 | 3.27 | 8.5 | 74% | 8% |
| 2 | Gemini 3.8 Flash (high) | high | 50 | 0 | choice only | 21.6 | 72.7 | 0% | 3386 / 4161 / 4160 | 18.14 | 8.5 | 72% | 8% |
| 2 | Claude Sonnet 5.5 (low) | low | 50 | 0 | choice only | 2.3 | 5.8 | 0% | 4448 / 190 / 179 | 10.80 | 10.8 | 68% | 10% |
| 2 | Claude Sonnet 5.5 (high) | high | 50 | 0 | choice only | 4.9 | 10.2 | 0% | 4448 / 542 / 531 | 14.31 | 6.5 | 74% | 4% |
| 2 | GPT-6.1 Sol (low) | low | 50 | 0 | choice only | 3.7 | 8.6 | 0% | 3225 / 90 / 73 | 7.35 | 5.8 | 74% | 6% |
| 2 | GPT-6.1 Sol (high) | high | 50 | 0 | choice only | 8.6 | 25.6 | 0% | 3225 / 325 / 308 | 9.70 | 6.0 | 76% | 6% |
| 2 | DeepSeek V4.1 Flash (off) | off | 50 | 0 | yes | 1.0 | 1.8 | 0% | 3265 / 7 / 0 | 0.66 | 19.1 | 56% | 20% |
| 2 | DeepSeek V4.1 Flash (on) | low | 50 | 0 | yes | 76.4 | 161.7 | 2% | 3290 / 11779 / 8660 | 14.73 | 7.9 | 74% | 6% |
| 2 | Qwen3.8 Flash Next (off) | off | 50 | 0 | yes | 2.1 | 3.0 | 0% | 3412 / 1 / 0 | – | 17.6 | 54% | 16% |
| 2 | Qwen3.8 Flash Next (on) | template default | 50 | 0 | yes | 355.9 | 405.6 | 0% | 26166 / 19273 / 19269 | – | 13.1 | 68% | 14% |
| 2 | GLM-5.3 (on) | low | 50 | 0 | yes | 2.0 | 8.3 | 0% | 3180 / 133 / 90 | 3.17 | 16.5 | 62% | 16% |
| 3 | GPT-6 Astra (low) | low | 50 | 0 | choice only | 3.1 | 7.6 | 0% | 3225 / 69 / 53 | 35.70 | 5.7 | 74% | 6% |
| 3 | GPT-6 Astra (high) | high | 28 | 0 | choice only | 8.2 | 16.3 | 0% | 3351 / 164 / 147 | 41.69 | 9.4 | 68% | 11% |
| 3 | Claude Opus 5.5 (low) | low | 50 | 0 | choice only | 2.9 | 5.8 | 0% | 4448 / 172 / 161 | 21.22 | 11.2 | 74% | 8% |
| 3 | Claude Opus 5.5 (high) | high | 40 | 0 | choice only | 4.8 | 13.0 | 0% | 4532 / 457 / 446 | 27.27 | 6.0 | 75% | 8% |
| 3 | Gemini 4 Argon (low) | low | 50 | 0 | choice only | 2.7 | 4.5 | 0% | 3464 / 5 / 0 | 6.98 | 13.1 | 68% | 10% |
| 3 | Gemini 4 Argon (high) | high | 30 | 0 | choice only | 24.3 | 122.3 | 0% | 3624 / 3744 / 3739 | 44.69 | 13.7 | 57% | 13% |
| 3 | DeepSeek V4 Pro (off) | off | 50 | 0 | yes | 1.4 | 2.0 | 0% | 3176 / 1 / 0 | 3.05 | 22.6 | 48% | 22% |
| 3 | DeepSeek V4 Pro (on) | low | 27 | 3 | yes | 144.1 | 270.6 | 22% | 3384 / 17533 / 17531 | 59.72 | 56.0 | 52% | 19% |
| 3 | Qwen3.8-Max (on) | low | 50 | 0 | choice only | 4.7 | 6.0 | 0% | 3434 / 13 / 0 | 6.95 | 19.8 | 50% | 18% |

\* Decider runs on our GPUs; its dollars are Perplexity's list price. Local models have no price.

**Stopped early by the $1-per-50 rule:** GPT-6 Astra high (28), Claude Opus high (40), Gemini 4 Argon high (30), DeepSeek V4 Pro on (27 answers, 3 failed requests). Astra low also passed $1 per 50 at API-equivalent prices, but it is a low setup on a subscription, so it was finished. Opus low ($1.06 per 50) finished.

## Findings

1. **Probabilities.** Every decision model, every local model and every open model on OpenRouter returned letter probabilities, except Qwen3.8-Max on Together, which returns no logprobs (choice only). All closed models are choice only, as expected.
   - Fireworks (DeepSeek V4.1 Flash, GLM-5.3), Novita (DeepSeek V4 Pro) and Together do not continue a prefilled "Answer:": they start a new assistant turn. On these the runner reads the letter's probabilities from the answer token of the ordinary response, after the reasoning when on (`letter_readout: "answer"`). This is the same quantity (the letter's probability after the reasoning); the local vLLM servers continue the prefill as designed.
   - Fireworks allows at most 5 top logprobs, so letters outside the top 5 get probability 0 there.
   - Novita and Cerebras accept no JSON schema, so DeepSeek V4 Pro and Qwen3.8-27B answer with an unconstrained letter. No invalid answers came from that.
2. **Clock: by the design's rule, all three leagues play without a clock.** The 90th-percentile time is above 30 s for Gemma 4 31B on (330 s) in League 1; for DeepSeek V4.1 Flash on (162 s), Qwen3.8 Flash Next on (406 s) and Gemini 3.8 Flash high (73 s) in League 2; and for Gemini 4 Argon high (122 s) and DeepSeek V4 Pro on (271 s) in League 3. The local times are inflated, because Gemma on and Qwen on ran at the same time with 8 requests each on shared GPUs, but they are far above 30 s either way.
3. **Reasoning levels are not similar across models.** Mean reasoning tokens per decision:
   - Open models' "on" at their lowest effort: Qwen3.8 Flash Next 19,269 (template default, no knob), DeepSeek V4 Pro 17,531, DeepSeek V4.1 Flash 8,660, Qwen3.8-27B 3,794, Gemma 4 31B 3,408 (template default), GLM-5.3 90.
   - Qwen3.8-Max reports 0 reasoning tokens (Together returns no reasoning text either), though OpenRouter lists its reasoning as mandatory.
   - Closed "low": Gemini 3.8 Flash 194, Claude Sonnet 179, Claude Opus 161, GPT-6.1 Sol 73, GPT-6 Astra 53, Gemini 4 Argon 0 (effectively off). Closed "high": 147 (Astra) to 4,160 (Gemini Flash).
   - So an open model's lowest "on" thinks 20 to 100 times longer than a closed model's "low", and often longer than its "high". "Similar level" holds only for GLM-5.3 on and the closed lows. If the levels should match, the open models need a token budget (e.g. max_tokens or a reasoning budget near 200–500) instead of the lowest effort; that is a decision for the freeze.
4. **Invalid answers are rare, and all come from the output cap.**
   - DeepSeek V4 Pro on: 6 of 27 answers reasoned past 32,768 tokens with no answer (22%), at $0.06 per decision.
   - DeepSeek V4.1 Flash on: 1 of 50.
   - A first Claude run at high effort had 8–12% invalid answers, because the old Anthropic output limit of 1,024 tokens was used up by thinking. The limit is now 32,000, and the table shows the rerun with 0%.
5. **Error rates (descriptive, 50 positions).**
   - The closed models at low effort and the reasoning-on open models are around 6–14 (expert to advanced range).
   - The decision models are around 20–30; Open-Jev is at 49. Note that Open-Jev's input tokens (27,849) count each option scored separately.
   - Safest and GNUbg weak are at 22 and 20; Random is at 91.
   - DeepSeek V4 Pro on (56) is dominated by its invalid random plays.
6. **Rate limits.**
   - OpenRouter limits new accounts to 20 requests per minute per model, so the OpenRouter setups now carry `rpm: 18` for `jevgammon ask`, and the shared positions will take about 2 hours per setup there.
   - Cerebras (Qwen3.8-27B) and Together (Qwen3.8-Max) also return upstream 429s from shared pools.
   - Failed requests are asked again on a rerun. League matches send one request at a time per model, well under these limits.

## Setups, counts and call budget (updated)

Following the user's addition, every model that can reason has an "on" setup, and Qwen3.8-27B "on" joins League 1. GLM-5.3 and Qwen3.8-Max have only "on", because their endpoints make reasoning mandatory.

| League | Players | Model setups | Matches |
| --- | --- | --- | --- |
| 1 | 16 (13 model setups + random, safest, GNUbg weak) | 13, of which Jev, Luna, Fastino and Celeris are blocked today | 120 |
| 2 | 12 (11 + GNUbg weak) | 11 | 66 |
| 3 | 10 (9 + GNUbg weak; Qwen3.8-Max needs confirmed open weights) | 9 | 45 |
| Total | 38 | 33 | 231 |

The call budget uses the design's basis, with 33 model setups, 13 of them in League 1. It is about 243,800 calls (design: 233,700):

| Run | Calls |
| --- | --- |
| League 1 | 22,400 (78 model pairs × 2 + 39 model–baseline × 1, × 115) |
| League 2 | 13,900 (55 × 2 + 11, × 115) |
| League 3 | 9,300 (36 × 2 + 9, × 115) |
| Shared positions | 66,000 |
| Nackgammon | 16,500 |
| Repeats | 33,000 |
| Opening control | 6,600 |
| Ablation | 24,000 |
| League 1 extension | 52,000 |

Reasoning-on setups on our servers send two requests per decision (reasoning, then the prefilled letter).

## Rosters and providers

- **Pinned through OpenRouter** (`provider.order` = one endpoint, `allow_fallbacks: false`, `require_parameters: true`):

  | Setups | Endpoint | Quantization | $ per 1M in / out |
  | --- | --- | --- | --- |
  | DeepSeek V4.1 Flash | `fireworks` | not published | 0.30 / 1.20 |
  | GLM-5.3 | `fireworks` | not published | 1.40 / 4.40 |
  | DeepSeek V4 Pro | `novita/fp8` | fp8 | 1.60 / 3.20 |
  | Qwen3.8-27B | `cerebras/fp16` | fp16 | 0.99 / 1.49 |
  | Qwen3.8-Max | `together` | not published | 2 / 6 |

  Reasoning off is `reasoning: {"enabled": false}`; on is `reasoning_effort: "low"`.
- **Our GPUs** (`tools/v3/servers/`):
  - Qwen3.8 Flash Next: fp8 checkpoint, vLLM TP4.
  - Gemma 4 31B: bf16 checkpoint quantized to fp8 by vLLM at load, fp8 KV cache.
  - Cygnet, Clef, Open-Jev 27B and Decider v1.1 27B: bf16.
  - Thinking on/off: `chat_template_kwargs.enable_thinking`.
  - The two reasoning models need different GPU waves from the four decision servers: `tools/v3/servers/wave.sh A|B start|stop`. Wave B is running now. The DeepSeek SGLang server is stopped but still enabled at boot.
- **Closed:**
  - Gemini API, with `thinkingLevel` low/high.
  - Claude and ChatGPT subscriptions, with effort low/high.
  - Prices are the API list prices of the Turkish benchmark's price table, plus Gemini 4 Argon at $2 / $10 (introductory, until Nov 30).
- Every decision logs prompt version, harness commit, provider, quantization, option order, letter, probabilities, request and retry time, tokens, reasoning tokens and cost.

## Blocked or open

- Jev (TypeSafe out of credit, and no key in the environment), GPT-6 Luna (no OPENAI_API_KEY), Fastino and Celeris (no keys): no smoke answers.
- Qwen3.8-Max joins League 3 only if its open weights are confirmed.
- Reasoning levels (finding 3) and the clock (finding 2) need a decision before the freeze.
- The live view stays on league.db until League 1's first match starts (Main's instruction); the v3 database is `v3.db` in the repo root.

Reproduce: `python3 tools/v3/smoke_positions.py`; `V3_ARGS="evaluate out=smoke/score.db positions=positions/smoke.jsonl" gnubg -t -q -p tools/v3/score.py`; `jevgammon ask --config <roster> --positions positions/smoke.jsonl --out smoke/answers.db --max-cost 1.0`; `python3 tools/v3/smoke_report.py smoke/answers.db smoke/score.db`.
