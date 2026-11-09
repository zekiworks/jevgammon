# Render comparison

## 1. Files
2552 files in origin/main's render, 2552 in the candidate's; only in one: none; different: ['index.html']

## 2. Rows and numbers
Leaderboard rows with a details box: origin/main 63, candidate 63.

Rows differing from origin/main beyond the Parameters line and data-hl-small: 0. Rows whose numbers (row + box, Parameters line out) differ: 0.

Home page outside the leaderboard table: text identical.

## 3-4. Parameters line and Small models flag vs model_params.json (threshold 15B)
63 of 63 rows ok; 3 rows changed.

| Box | Row | Setup | Model | origin/main | small (main) | candidate | Link | small | Change | OK |
|---|---|---|---|---|---|---|---|---|---|---|
| hl-1-box | model/main | GPT-6 Astra (high) | GPT-6 Astra | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-1-1-box | model/other | GPT-6 Astra (low) | GPT-6 Astra | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-1-2-box | model/other | GPT-6 Astra (medium) | GPT-6 Astra | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-2-box | model/main | Gemini 4 Argon (high) | Gemini 4 Argon | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-2-1-box | model/other | Gemini 4 Argon (low) | Gemini 4 Argon | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-3-box | model/main | Claude Fable 5.1 (high) | Claude Fable 5.1 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-3-1-box | model/other | Claude Fable 5.1 (low) | Claude Fable 5.1 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-4-box | model/main | GPT-6.1 Sol (high) | GPT-6.1 Sol | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-4-1-box | model/other | GPT-6.1 Sol (low) | GPT-6.1 Sol | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-5-box | model/main | Claude Opus 5.5 (high) | Claude Opus 5.5 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-5-1-box | model/other | Claude Opus 5.5 (low) | Claude Opus 5.5 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-6-box | model/main | DeepSeek V4.1 Flash (low) | DeepSeek V4.1 Flash | 552B total / 16B active |  | 552B backbone + 196B conditional memory; active 8B (prefill) / 16B (decode) | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash |  | CHANGED | yes |
| hl-6-1-box | model/other | DeepSeek V4.1 Flash 1017 (low) | DeepSeek V4.1 Flash 1017 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-6-2-box | model/other | DeepSeek V4.1 Flash (off) | DeepSeek V4.1 Flash | 552B total / 16B active |  | 552B backbone + 196B conditional memory; active 8B (prefill) / 16B (decode) | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash |  | CHANGED | yes |
| hl-6-3-box | model/other | DeepSeek V4.1 Flash 1017 (off) | DeepSeek V4.1 Flash 1017 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-7-box | model/main | Grok 4.7 (high) | Grok 4.7 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-7-1-box | model/other | Grok 4.7 (low) | Grok 4.7 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-8-box | model/main | Claude Sonnet 5.5 (high) | Claude Sonnet 5.5 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-8-1-box | model/other | Claude Sonnet 5.5 (low) | Claude Sonnet 5.5 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-9-box | model/main | Gemini 3.8 Flash (high) | Gemini 3.8 Flash | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-9-1-box | model/other | Gemini 3.8 Flash (low) | Gemini 3.8 Flash | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-10-box | model/main | Kimi K3.1 Pro (off) | Kimi K3.1 Pro | 2.8T total / 104B active |  | 2.8T total / 104B active | https://huggingface.co/moonshotai/Kimi-K3.1-Pro/blob/main/README.md |  | same | yes |
| hl-11-box | model/main | Gemma 4 31B (on) | Gemma 4 31B | 30.7B |  | 30.7B | https://huggingface.co/google/gemma-4-31B-it |  | same | yes |
| hl-11-1-box | model/other | Gemma 4 31B (off) | Gemma 4 31B | 30.7B |  | 30.7B | https://huggingface.co/google/gemma-4-31B-it |  | same | yes |
| hl-12-box | model/main | Liquid d1-ultra | Liquid d1-ultra | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-13-box | model/main | Base Labs Mammoth-1 | Base Labs Mammoth-1 | 27B |  | 27B | https://huggingface.co/baselabs/mammoth-1/blob/61cec44c281c693992e3d6ebeb44dd3402dfa186/README.md |  | same | yes |
| hl-14-box | model/main | Drex Max v1 | Drex Max v1 | 27B |  | 27B | https://huggingface.co/nace-ai/drex-max-v1/blob/cac65e1982a0237e996419ba559004522d9a33ac/README.md |  | same | yes |
| hl-15-box | model/main | Qwen3.8-27B (low) | Qwen3.8-27B | 27B |  | 27B | https://huggingface.co/Qwen/Qwen3.8-27B |  | same | yes |
| hl-15-1-box | model/other | Qwen3.8-27B (off) | Qwen3.8-27B | 27B |  | 27B | https://huggingface.co/Qwen/Qwen3.8-27B |  | same | yes |
| hl-16-box | model/main | GLM-5.3 (low) | GLM-5.3 | 753.33B total; active not disclosed by maker |  | 753.33B total; active not disclosed by maker | https://huggingface.co/api/models/zai-org/GLM-5.3 |  | same | yes |
| hl-17-box | model/main | REAX 1.3 | REAX 1.3 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-18-box | model/main | Fastino GLiDE | Fastino GLiDE | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-19-box | model/main | Jev 1.13.0 | Jev 1.13.0 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-20-box | model/main | Qwen3.8 Flash (off) | Qwen3.8 Flash | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-21-box | model/main | Jev 1.14.0 | Jev 1.14.0 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-22-box | model/main | Drex Max 1.1 | Drex Max 1.1 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-23-box | model/main | Fastino GLiDE v1.2 (local) | Fastino GLiDE v1.2 | 26.09B |  | 26.09B | https://huggingface.co/api/models/fastino/GLiDE/revision/a7e45896 |  | same | yes |
| hl-24-box | model/main | Drex 2.0 | Drex 2.0 | 35B total / 3B active |  | 35B total / 3B active | https://huggingface.co/nace-ai/drex-v2.0/blob/e646674476744e3826caf62b834054151e2aba51/README.md |  | same | yes |
| hl-24-1-box | model/other | Drex 2.0 (local) | Drex 2.0 | 35B total / 3B active |  | 35B total / 3B active | https://huggingface.co/nace-ai/drex-v2.0/blob/e646674476744e3826caf62b834054151e2aba51/README.md |  | same | yes |
| hl-25-box | model/main | Decider v1.2 27B | Decider v1.2 27B | 27B |  | 27B | https://docs.perplexity.ai/changelog |  | same | yes |
| hl-26-box | model/main | Celeris-1 Decision | Celeris-1 Decision | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-27-box | model/main | Base Labs Elephant-1 | Base Labs Elephant-1 | 9B | yes | 9B | https://huggingface.co/baselabs/elephant-1/blob/b3f8a93462fb1051a9de031e94a7ff380e254072/README.md | yes | same | yes |
| hl-28-box | model/main | Clef | Clef | 27B |  | 27B | https://huggingface.co/cloudflare/clef |  | same | yes |
| hl-29-box | model/main | Cygnet (Gemma 4 12B) | Cygnet (Gemma 4 12B) | 11.95B | yes | 11.95B | https://huggingface.co/google/gemma-4-12B-it/blob/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7/README.md | yes | CHANGED | yes |
| hl-30-box | model/main | Decider v1.1 27B | Decider v1.1 27B | 26.09B |  | 26.09B | https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1.1-27b |  | same | yes |
| hl-31-box | model/main | SubQ Snap 1.1 | SubQ Snap 1.1 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-32-box | model/main | SubQ Snap Preview | SubQ Snap Preview | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-33-box | model/main | GPT-6 Luna | GPT-6 Luna | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-34-box | model/main | Winnow-12B | Winnow-12B | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-35-box | model/main | Mercury Decide | Mercury Decide | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-36-box | model/main | LFM2.5-24B-A2B (on) | LFM2.5-24B-A2B | 24B total / 2.45B active |  | 24B total / 2.45B active | https://huggingface.co/LiquidAI/LFM2.5-24B-A2B |  | same | yes |
| hl-36-1-box | model/other | LFM2.5-24B-A2B (off) | LFM2.5-24B-A2B | 24B total / 2.45B active |  | 24B total / 2.45B active | https://huggingface.co/LiquidAI/LFM2.5-24B-A2B |  | same | yes |
| hl-37-box | model/main | Decider Flash v1.2 | Decider Flash v1.2 | 4B | yes | 4B | https://docs.perplexity.ai/changelog | yes | same | yes |
| hl-38-box | model/main | Open-Jev 27B v1.1 | Open-Jev 27B v1.1 | not disclosed by maker |  | not disclosed by maker |  |  | same | yes |
| hl-p-1-box | program/main | GNUbg weak |  |  |  |  |  |  | same | yes |
| hl-p-1-1-box | program/other | GNUbg weak |  |  |  |  |  |  | same | yes |
| hl-p-1-2-box | program/other | GNUbg weak |  |  |  |  |  |  | same | yes |
| hl-p-2-box | program/main | Safest |  |  |  |  |  |  | same | yes |
| hl-p-2-1-box | program/other | Safest (computed) |  |  |  |  |  |  | same | yes |
| hl-p-2-2-box | program/other | Safest (computed) |  |  |  |  |  |  | same | yes |
| hl-p-3-box | program/main | Random |  |  |  |  |  |  | same | yes |
| hl-p-3-1-box | program/other | Random (computed) |  |  |  |  |  |  | same | yes |
| hl-p-3-2-box | program/other | Random (computed) |  |  |  |  |  |  | same | yes |

**Failures: 0**
