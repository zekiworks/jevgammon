# b. By release date

Criterion (stated before looking): use only ranked models with a documented release month (tools/site/content/release_months.json `models.<row>.month`, non-null). For each maker (maker_colors.json `setups.<setup>`) with ≥2 documented models, does risk judgement (`risk.main.judgement`) rise from the earliest-month to the latest-month model? KEEP 'Newer models judge risk better' only if this holds for every such maker AND the pooled Spearman rank correlation (month vs judgement, ties averaged) is clearly positive.

Documented: 24 of 38 ranked models. Undocumented (14): Base Labs Mammoth-1, Drex Max v1, REAX 1.3, Jev 1.13.0, Qwen3.8 Flash, Drex Max 1.1, Drex 2.0, Base Labs Elephant-1, Cygnet (Gemma 4 12B), SubQ Snap 1.1, SubQ Snap Preview, Winnow-12B, Mercury Decide, Open-Jev 27B v1.1. (Months null in release_months.json: Cygnet (Gemma 4 12B), Jev 1.13.0, Mercury Decide, Open-Jev 27B v1.1, Qwen3.8 Flash, SubQ Snap Preview, Winnow-12B; the 7 late entries Base Labs Mammoth-1, Base Labs Elephant-1, Drex Max v1, Drex Max 1.1, Drex 2.0, REAX 1.3, SubQ Snap 1.1 are not listed in the file.)

Per maker (month, model, risk judgement):
- Alibaba (Qwen): 2026-08 Qwen3.8-27B 62.0
- Anthropic: 2026-09 Claude Fable 5.1 72.3; 2026-09 Claude Opus 5.5 70.0; 2026-09 Claude Sonnet 5.5 68.2
- Celeris: 2026-10 Celeris-1 Decision 57.8
- DeepSeek: 2026-09 DeepSeek V4.1 Flash 69.0
- Fastino: 2026-09 Fastino GLiDE 60.4; 2026-10 Fastino GLiDE v1.2 58.8
- Google: 2026-04 Gemma 4 31B 64.5; 2026-09 Gemini 3.8 Flash 66.9; 2026-10 Gemini 4 Argon 74.1
- Liquid AI: 2026-10 LFM2.5-24B-A2B 52.4; 2026-10 Liquid d1-ultra 64.0
- Maker not recorded: 2026-10 Clef 57.5
- Moonshot: 2026-10 Kimi K3.1 Pro 65.9
- OpenAI: 2026-09 GPT-6 Astra 74.4; 2026-09 GPT-6 Luna 55.7; 2026-09 GPT-6.1 Sol 72.2
- Perplexity: 2026-10 Decider Flash v1.2 49.1; 2026-10 Decider v1.1 27B 56.9; 2026-10 Decider v1.2 27B 57.9
- TypeSafe: 2026-10 Jev 1.14.0 59.3
- Z.ai: 2026-08 GLM-5.3 61.7
- xAI: 2026-09 Grok 4.7 68.5

Makers with ≥2 documented models: Anthropic: untestable (all same month); Fastino: does not rise; Google: rises; Liquid AI: untestable (all same month); OpenAI: untestable (all same month); Perplexity: untestable (all same month).
Google: Gemma 4 31B (2026-04) 64.5 → Gemini 3.8 Flash (2026-09) 66.9 → Gemini 4 Argon (2026-10) 74.1: rises. Fastino: Fastino GLiDE (2026-09) 60.4 → Fastino GLiDE v1.2 (2026-10) 58.8: falls. Anthropic, OpenAI, Perplexity, Liquid AI: all documented models share one month, so earliest-to-latest cannot be read.
Pooled Spearman rank correlation (n=24): -0.44 (negative). Month counts: 2026-04 1, 2026-08 2, 2026-09 10, 2026-10 11 — month resolution is coarse.

Verdict: **NEUTRAL** (Fastino falls; pooled correlation negative). Heading: **Risk judgement by release date**. Note for the page: release month is documented for 24 of 38 models; within one month order is unknown; no trend is claimed.

**Used on the site (CTBrief):** the rule in code (story.release_chart) is the first half of the criterion above: every
maker with models in two or more documented months scores higher with each later month, and at least two makers do.
Fastino (60.4 → 58.8) fails it, so the heading is neutral; the pooled correlation is not computed on the site (no new
statistic). One line per maker only where its models span two or more months (Google, Fastino); "Maker not recorded"
is not a maker and gets no line.
Wording (Zeki #2963): "no clear trend" replaced by "That is not a consistent increase across the makers shown." (the rule
does not test every possible trend).
