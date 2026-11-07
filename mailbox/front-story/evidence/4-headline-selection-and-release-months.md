# Headline table: one row per model, its setting with the highest stored risk judgement

Source: the live site's published data files (results f45081f6, data as of 2026-11-07T17:50Z): data/v3/league-N.json (risk.main.judgement per setup) and data/setups.json (model). Read-only; every number below is copied from those files as printed.

Each row is ONE named setup, the model's setting with the highest stored risk judgement (Zeki #2578): every cell of the row (risk judgement and interval, risks found, right safety, error rate, cost) is that setup's own; the model's other settings are under All setups. A selection for display, not a separate run.

| Model | Shown setup (league) | Its risk judgement | Other settings: risk judgement |
|---|---|---:|---|
| GPT-6 Astra | GPT-6 Astra (low) (L3) | 75.8 | GPT-6 Astra (medium) (L3) 74.7 |
| Gemini 4 Argon | Gemini 4 Argon (high) (L3) | 74.1 | Gemini 4 Argon (low) (L3) 69.2 |
| GPT-6.1 Sol (low) | GPT-6.1 Sol (low) (L3) | 72.7 | — |
| Claude Fable 5.1 | Claude Fable 5.1 (high) (L3) | 72.3 | — |
| GPT-6.1 Sol (high) | GPT-6.1 Sol (high) (L3) | 72.2 | — |
| Claude Opus 5.5 | Claude Opus 5.5 (high) (L3) | 70.0 | Claude Opus 5.5 (low) (L3) 66.9 |
| DeepSeek V4.1 Flash | DeepSeek V4.1 Flash (low) (L2) | 69.0 | — |
| Grok 4.7 | Grok 4.7 (high) (L3) | 68.5 | — |
| DeepSeek V4.1 Flash 1017 | DeepSeek V4.1 Flash 1017 (low) (L2) | 68.5 | DeepSeek V4.1 Flash 1017 (off) (L2) 58.5 |
| Claude Sonnet 5.5 | Claude Sonnet 5.5 (high) (L2) | 68.2 | Claude Sonnet 5.5 (low) (L2) 63.5 |
| Claude Fable 5.1 (low) | Claude Fable 5.1 (low) (L2) | 67.8 | — |
| Grok 4.7 (low) | Grok 4.7 (low) (L2) | 67.7 | — |
| Gemini 3.8 Flash | Gemini 3.8 Flash (high) (L2) | 66.9 | Gemini 3.8 Flash (low) (L2) 65.1 |
| Kimi K3.1 Pro | Kimi K3.1 Pro (off) (L3) | 65.9 | — |
| Gemma 4 31B | Gemma 4 31B (on) (L2) | 64.5 | Gemma 4 31B (off) (L2) 62.6 |
| Liquid d1-ultra | Liquid d1-ultra (L2) | 64.0 | — |
| Qwen3.8-27B | Qwen3.8-27B (low) (L2) | 62.0 | — |
| GLM-5.3 | GLM-5.3 (low) (L2) | 61.7 | — |
| Fastino GLiDE | Fastino GLiDE (L2) | 60.4 | — |
| Jev 1.13.0 | Jev 1.13.0 (L1) | 59.5 | — |
| Qwen3.8 Flash | Qwen3.8 Flash (off) (L2) | 59.5 | — |
| DeepSeek V4.1 Flash (off) | DeepSeek V4.1 Flash (off) (L1) | 59.3 | — |
| Jev 1.14.0 | Jev 1.14.0 (L2) | 59.3 | — |
| Fastino GLiDE v1.2 | Fastino GLiDE v1.2 (local) (L1) | 58.8 | — |
| Decider v1.2 27B | Decider v1.2 27B (L1) | 57.9 | — |
| Celeris-1 Decision | Celeris-1 Decision (L1) | 57.8 | — |
| Qwen3.8-27B (off) | Qwen3.8-27B (off) (L1) | 57.6 | — |
| Clef | Clef (L2) | 57.5 | — |
| Cygnet (Gemma 4 12B) | Cygnet (Gemma 4 12B) (L1) | 57.1 | — |
| Decider v1.1 27B | Decider v1.1 27B (L1) | 56.9 | — |
| SubQ Snap Preview | SubQ Snap Preview (L1) | 56.5 | — |
| GPT-6 Luna | GPT-6 Luna (L1) | 55.7 | — |
| Winnow-12B | Winnow-12B (L1) | 55.2 | — |
| Mercury Decide | Mercury Decide (L1) | 53.4 | — |
| LFM2.5-24B-A2B (on) | LFM2.5-24B-A2B (on) (L1) | 52.4 | — |
| Decider Flash v1.2 | Decider Flash v1.2 (L1) | 49.1 | — |
| Open-Jev 27B v1.1 | Open-Jev 27B v1.1 (L1) | 48.5 | — |
| LFM2.5-24B-A2B (off) | LFM2.5-24B-A2B (off) (L1) | 45.7 | — |

## Release months (column Released)

From the maker's own page, read on 2026-11-07, quote copied verbatim (tools/site/content/release_months.json). — where no official dated statement for the exact model name was found:

| Model | Month | Source |
|---|---|---|
| Celeris-1 Decision | 2026-10 | https://celeris.ai/celeris-1-decision |
| Claude Fable 5.1 | 2026-09 | https://www.anthropic.com/claude-fable-and-mythos-5-1 |
| Claude Fable 5.1 (low) | — | no entry |
| Claude Opus 5.5 | 2026-09 | https://www.anthropic.com/claude-opus-5-5 |
| Claude Sonnet 5.5 | 2026-09 | https://www.anthropic.com/claude-sonnet-5-5 |
| Clef | 2026-10 | https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/ |
| Cygnet (Gemma 4 12B) | — | Cygnet's own repo (https://github.com/blockbrain-ai/cygnet-recipe) was read; it states no release date (only 'retrieved 2026-09-30' for benchmark data). Gemma 4 12B dates not used per instructions. |
| Decider Flash v1.2 | 2026-10 | https://docs.perplexity.ai/changelog |
| Decider v1.1 27B | 2026-10 | https://docs.perplexity.ai/changelog |
| Decider v1.2 27B | 2026-10 | https://docs.perplexity.ai/changelog |
| DeepSeek V4.1 Flash | 2026-09 | https://api-docs.deepseek.com/updates/ |
| DeepSeek V4.1 Flash (off) | — | no entry |
| DeepSeek V4.1 Flash 1017 | 2026-10 | https://api-docs.deepseek.com/updates/ |
| Fastino GLiDE | 2026-09 | https://fastino.ai/blog/introducing-glide-the-first-thinking-decision-model |
| Fastino GLiDE v1.2 | 2026-10 | https://fastino.ai/blog/training-glide-sota-decision-model |
| GLM-5.3 | 2026-08 | https://docs.z.ai/release-notes/new-released |
| GPT-6 Astra | 2026-09 | https://openai.com/index/introducing-gpt-6-1-sol/ |
| GPT-6 Luna | 2026-09 | https://openai.com/index/gpt-6-astra/ |
| GPT-6.1 Sol (high) | — | no entry |
| GPT-6.1 Sol (low) | — | no entry |
| Gemini 3.8 Flash | 2026-09 | https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/ |
| Gemini 4 Argon | 2026-10 | https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-4-argon/ |
| Gemma 4 31B | 2026-04 | https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ |
| Grok 4.7 | 2026-09 | https://x.ai/news/grok-4-7 |
| Grok 4.7 (low) | — | no entry |
| Jev 1.13.0 | — | No official page found stating when jev-1.13.0 was released; typesafe.ai/blog/introducing-system-one-models-and-jev (Sep 15, 2026) and docs.typesafe.ai/models, /changelog were read and do not date 1.13.0. |
| Jev 1.14.0 | 2026-10 | https://docs.typesafe.ai/models |
| Kimi K3.1 Pro | 2026-10 | https://forum.moonshot.ai/t/kimi-k3-1-pro-has-launched-start-exploring-now/629 |
| LFM2.5-24B-A2B (off) | — | no entry |
| LFM2.5-24B-A2B (on) | — | no entry |
| Liquid d1-ultra | 2026-10 | https://www.liquid.ai/blog/d1-ultra |
| Mercury Decide | 2026-10 | https://www.inceptionlabs.ai/blog/introducing-mercury-3 |
| Open-Jev 27B v1.1 | — | HF card ZefanCai/Open-Jev-27B-v1.1 read; it states no release date (commit dates not counted). |
| Qwen3.8 Flash | — | Not used: the page does not name this exact model (Alibaba Cloud Model Studio new-models page; assumes our 'Qwen3.8 Flash' is the API model qwen3.8-flash (open-weight Qwen3.8-Flash-Next also dated 2026-08-26 on its GitHub).); a month shown must be stated for the exact model name (Ümit #2570: never guess). Was 2026-08 from https://www.alibabacloud.com/help/en/model-studio/newly-released-models. |
| Qwen3.8-27B | 2026-08 | https://github.com/QwenLM/Qwen3.8 |
| Qwen3.8-27B (off) | — | no entry |
| SubQ Snap Preview | — | Not used: the page does not name this exact model (Post dated October 12, 2026. Doubt: page names the model 'SubQ Snap' and its status 'Public Preview', not literally 'SubQ Snap Preview'.); a month shown must be stated for the exact model name (Ümit #2570: never guess). Was 2026-10 from https://subq.ai/introducing-subq-snap. |
| Winnow-12B | — | HF card EldanRing/Winnow-12B read; it states no release date. |
