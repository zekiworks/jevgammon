# 1. Setting choice per model (Ümit #2745 item 1; Zeki #2790)

Re-derived by `scripts/evidence.py` from the render's data files (data/setups.json `setting`, the sent effort, and the league of each setup's entry; data/v3/league-N.json) and content/model_identity.json, independently of story.py, and compared with the rendered table: **all checks pass**.

## The rule

- Order of the sent effort: none = off < minimal < low < medium < high < xhigh < max.
- `on`: the setting of a model with no levels (thinking on/off only: LFM2.5-24B-A2B, Gemma 4 31B); above off. A model with both `on` and a level fails the build (none has).
- Decision models send no setting: their single setup.
- Version names are separate models (Jev 1.13.0 / Jev 1.14.0; Decider v1.1 / v1.2; Fastino GLiDE / GLiDE v1.2).
- One model under two names only by the approved list `content/model_identity.json`: DeepSeek V4.1 Flash 1017 → DeepSeek V4.1 Flash, nothing else; any other name, a dated suffix included, is its own model. The row is named and dated by the original.
- Several setups at the model's highest setting: the **first in league order** (the league of its setups.json entry), **then by setup name**. **No score** anywhere in the choice. The same for programs (their first played setup: League 1) and, with LATE_ROWS, late entries (their field league, then name).
- Ranked by the chosen setup's stored risk judgement (exact tie: name).

## Per model

| # | Row (model) | Setups played (setting · league · judgement) | Chosen | Why | Best-score setup (for comparison) |
|---:|---|---|---|---|---|
| 1 | GPT-6 Astra | GPT-6 Astra (low) (low · L3 · 75.8); GPT-6 Astra (medium) (medium · L3 · 74.7) | GPT-6 Astra (medium) · L3 | highest setting played: medium | GPT-6 Astra (low) |
| 2 | Gemini 4 Argon | Gemini 4 Argon (high) (high · L3 · 74.1); Gemini 4 Argon (low) (low · L3 · 69.2) | Gemini 4 Argon (high) · L3 | highest setting played: high | Gemini 4 Argon (high) (same) |
| 3 | Claude Fable 5.1 | Claude Fable 5.1 (low) (low · L2 · 67.8); Claude Fable 5.1 (high) (high · L3 · 72.3) | Claude Fable 5.1 (high) · L3 | highest setting played: high | Claude Fable 5.1 (high) (same) |
| 4 | GPT-6.1 Sol | GPT-6.1 Sol (high) (high · L3 · 72.2); GPT-6.1 Sol (low) (low · L3 · 72.7) | GPT-6.1 Sol (high) · L3 | highest setting played: high | GPT-6.1 Sol (low) |
| 5 | Claude Opus 5.5 | Claude Opus 5.5 (high) (high · L3 · 70.0); Claude Opus 5.5 (low) (low · L3 · 66.9) | Claude Opus 5.5 (high) · L3 | highest setting played: high | Claude Opus 5.5 (high) (same) |
| 6 | DeepSeek V4.1 Flash | DeepSeek V4.1 Flash (off) (off · L1 · 59.3); DeepSeek V4.1 Flash (low) (low · L2 · 69.0); DeepSeek V4.1 Flash 1017 (low) (low · L2 · 68.5); DeepSeek V4.1 Flash 1017 (off) (off · L2 · 58.5) | DeepSeek V4.1 Flash (low) · L2 | highest setting played: low; 2 setups at it (DeepSeek V4.1 Flash (low) L2, DeepSeek V4.1 Flash 1017 (low) L2): the first in league order, then by name | DeepSeek V4.1 Flash (low) (same) |
| 7 | Grok 4.7 | Grok 4.7 (low) (low · L2 · 67.7); Grok 4.7 (high) (high · L3 · 68.5) | Grok 4.7 (high) · L3 | highest setting played: high | Grok 4.7 (high) (same) |
| 8 | Claude Sonnet 5.5 | Claude Sonnet 5.5 (high) (high · L2 · 68.2); Claude Sonnet 5.5 (low) (low · L2 · 63.5) | Claude Sonnet 5.5 (high) · L2 | highest setting played: high | Claude Sonnet 5.5 (high) (same) |
| 9 | Gemini 3.8 Flash | Gemini 3.8 Flash (high) (high · L2 · 66.9); Gemini 3.8 Flash (low) (low · L2 · 65.1) | Gemini 3.8 Flash (high) · L2 | highest setting played: high | Gemini 3.8 Flash (high) (same) |
| 10 | Kimi K3.1 Pro | Kimi K3.1 Pro (off) (off · L3 · 65.9) | Kimi K3.1 Pro (off) · L3 | single setup | Kimi K3.1 Pro (off) (same) |
| 11 | Gemma 4 31B | Gemma 4 31B (off) (off · L2 · 62.6); Gemma 4 31B (on) (on · L2 · 64.5) | Gemma 4 31B (on) · L2 | highest setting played: on | Gemma 4 31B (on) (same) |
| 12 | Liquid d1-ultra | Liquid d1-ultra (— · L2 · 64.0) | Liquid d1-ultra · L2 | single setup | Liquid d1-ultra (same) |
| 13 | Qwen3.8-27B | Qwen3.8-27B (off) (off · L1 · 57.6); Qwen3.8-27B (low) (low · L2 · 62.0) | Qwen3.8-27B (low) · L2 | highest setting played: low | Qwen3.8-27B (low) (same) |
| 14 | GLM-5.3 | GLM-5.3 (low) (low · L2 · 61.7) | GLM-5.3 (low) · L2 | single setup | GLM-5.3 (low) (same) |
| 15 | Fastino GLiDE | Fastino GLiDE (— · L2 · 60.4) | Fastino GLiDE · L2 | single setup | Fastino GLiDE (same) |
| 16 | Jev 1.13.0 | Jev 1.13.0 (— · L1 · 59.5) | Jev 1.13.0 · L1 | single setup | Jev 1.13.0 (same) |
| 17 | Qwen3.8 Flash | Qwen3.8 Flash (off) (off · L2 · 59.5) | Qwen3.8 Flash (off) · L2 | single setup | Qwen3.8 Flash (off) (same) |
| 18 | Jev 1.14.0 | Jev 1.14.0 (— · L2 · 59.3) | Jev 1.14.0 · L2 | single setup | Jev 1.14.0 (same) |
| 19 | Fastino GLiDE v1.2 | Fastino GLiDE v1.2 (local) (— · L1 · 58.8) | Fastino GLiDE v1.2 (local) · L1 | single setup | Fastino GLiDE v1.2 (local) (same) |
| 20 | Decider v1.2 27B | Decider v1.2 27B (— · L1 · 57.9) | Decider v1.2 27B · L1 | single setup | Decider v1.2 27B (same) |
| 21 | Celeris-1 Decision | Celeris-1 Decision (— · L1 · 57.8) | Celeris-1 Decision · L1 | single setup | Celeris-1 Decision (same) |
| 22 | Clef | Clef (— · L2 · 57.5) | Clef · L2 | single setup | Clef (same) |
| 23 | Cygnet (Gemma 4 12B) | Cygnet (Gemma 4 12B) (— · L1 · 57.1) | Cygnet (Gemma 4 12B) · L1 | single setup | Cygnet (Gemma 4 12B) (same) |
| 24 | Decider v1.1 27B | Decider v1.1 27B (— · L1 · 56.9) | Decider v1.1 27B · L1 | single setup | Decider v1.1 27B (same) |
| 25 | SubQ Snap Preview | SubQ Snap Preview (— · L1 · 56.5) | SubQ Snap Preview · L1 | single setup | SubQ Snap Preview (same) |
| 26 | GPT-6 Luna | GPT-6 Luna (— · L1 · 55.7) | GPT-6 Luna · L1 | single setup | GPT-6 Luna (same) |
| 27 | Winnow-12B | Winnow-12B (— · L1 · 55.2) | Winnow-12B · L1 | single setup | Winnow-12B (same) |
| 28 | Mercury Decide | Mercury Decide (— · L1 · 53.4) | Mercury Decide · L1 | single setup | Mercury Decide (same) |
| 29 | LFM2.5-24B-A2B | LFM2.5-24B-A2B (off) (off · L1 · 45.7); LFM2.5-24B-A2B (on) (on · L1 · 52.4) | LFM2.5-24B-A2B (on) · L1 | highest setting played: on | LFM2.5-24B-A2B (on) (same) |
| 30 | Decider Flash v1.2 | Decider Flash v1.2 (— · L1 · 49.1) | Decider Flash v1.2 · L1 | single setup | Decider Flash v1.2 (same) |
| 31 | Open-Jev 27B v1.1 | Open-Jev 27B v1.1 (— · L1 · 48.5) | Open-Jev 27B v1.1 · L1 | single setup | Open-Jev 27B v1.1 (same) |

Rows whose setup differs from the best-score rule (2): GPT-6 Astra: GPT-6 Astra (low) → GPT-6 Astra (medium); GPT-6.1 Sol: GPT-6.1 Sol (low) → GPT-6.1 Sol (high).

Rows: 31 models (main's table has 32: it counted DeepSeek V4.1 Flash 1017 as its own model, a row that now sits under DeepSeek V4.1 Flash's expander).

Against the 5ca56de render (score used within the top setting): ranked rows changed: **none** (31 rows then, 31 now, the same setups in the same order).

