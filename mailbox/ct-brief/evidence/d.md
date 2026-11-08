# d. Reasoning settings

Scope: every model with ≥2 reasoning settings in the SAME league (data/results.json `leagues.<lg>.setups`, plus data/v3/late-entries.json GPT-6 Astra (high), `field_league` 3). Excluded (settings in different leagues): Claude Fable 5.1 (low L2 / high L3), Grok 4.7 (low L2 / high L3), DeepSeek V4.1 Flash (off L1 / low L2), Qwen3.8-27B (off L1 / low L2). DeepSeek V4.1 Flash 1017 is a separate checkpoint (model_identity.json `same_model`), compared within itself. Values: `quality.error_rate` [error_lo, error_hi], `risk.main.judgement` [judgement_lo, judgement_hi].

Criterion: heading 'More thinking: better moves, not better risk calls' only if most models have a lower error rate at the highest setting AND most do NOT have higher risk judgement at the highest setting; else 'What thinking adds'.

| League | Model | Low setting | High setting | Error low → high | Lower? | Risk low → high | Higher? |
|---|---|---|---|---|---|---|---|
| 1 | LFM2.5-24B-A2B | LFM2.5-24B-A2B (off) | LFM2.5-24B-A2B (on) | 61.5 [56.3–66.8] → 47.7 [44.1–51.2] | yes (intervals apart) | 45.7 [43.2–48.1] → 52.4 [50.3–54.5] | yes (intervals apart) |
| 2 | Claude Sonnet 5.5 | Claude Sonnet 5.5 (low) | Claude Sonnet 5.5 (high) | 20.1 [17.8–22.4] → 16.7 [14.9–18.7] | yes | 63.5 [61.6–65.4] → 68.2 [66.3–70.0] | yes (intervals apart) |
| 2 | DeepSeek V4.1 Flash 1017 | DeepSeek V4.1 Flash 1017 (off) | DeepSeek V4.1 Flash 1017 (low) | 35.2 [31.8–38.8] → 17.1 [15.1–19.2] | yes (intervals apart) | 58.5 [56.6–60.5] → 68.5 [66.4–70.6] | yes (intervals apart) |
| 2 | Gemini 3.8 Flash | Gemini 3.8 Flash (low) | Gemini 3.8 Flash (high) | 16.3 [14.5–18.2] → 14.9 [12.9–17.0] | yes | 65.1 [63.5–66.8] → 66.9 [65.2–68.5] | yes |
| 2 | Gemma 4 31B | Gemma 4 31B (off) | Gemma 4 31B (on) | 22.5 [19.9–25.3] → 19.6 [17.5–21.7] | yes | 62.6 [60.4–65.0] → 64.5 [62.9–66.2] | yes |
| 3 | Claude Opus 5.5 | Claude Opus 5.5 (low) | Claude Opus 5.5 (high) | 15.4 [13.1–18.0] → 14.4 [12.1–17.0] | yes | 66.9 [64.7–69.2] → 70.0 [67.3–72.6] | yes |
| 3 | GPT-6 Astra | GPT-6 Astra (low) | GPT-6 Astra (high) (late entry) | 11.8 [9.5–14.2] → 8.8 [7.4–10.3] | yes | 75.8 [73.1–78.5] → 74.4 [71.8–77.0] | no |
| 3 | GPT-6.1 Sol | GPT-6.1 Sol (low) | GPT-6.1 Sol (high) | 12.1 [10.5–13.7] → 9.9 [8.6–11.3] | yes | 72.7 [69.9–75.5] → 72.2 [69.5–74.9] | no |
| 3 | Gemini 4 Argon | Gemini 4 Argon (low) | Gemini 4 Argon (high) | 16.5 [13.7–19.5] → 12.6 [10.5–14.8] | yes | 69.2 [66.2–72.3] → 74.1 [72.0–76.1] | yes |

Result: error rate lower at the highest setting for 9 of 9 (intervals apart for 2 of 9). Risk judgement higher at the highest setting for 7 of 9 (intervals apart for 3 of 9); not higher for 2 (GPT-6 Astra, GPT-6.1 Sol). The second condition (most do NOT have higher risk judgement) fails.
GPT-6 Astra low/medium/high: risk 75.8/74.7/74.4, error 11.8/11.1/8.8 — matches the brief (75.8/74.7/74.4, 11.8/11.1/8.8); no mismatch. Sources: results.json leagues.league-3.setups["GPT-6 Astra (low)"|"GPT-6 Astra (medium)"]; late-entries.json entries[slug=gpt-6-astra-high].
Site's own reading: results.json `leagues.<lg>.reasoning[]` reads 'lower error rate in league play' for LFM2.5-24B-A2B and DeepSeek V4.1 Flash 1017, 'no clear difference in league play' for the other 7 (it compares lowest vs medium for Astra; the late Astra (high) is not in that list).

Verdict: **NEUTRAL** — heading: **What thinking adds**.

**Used on the site (CTBrief):** the rule in code (story.reasoning): heading "More thinking: better moves, not better
risk calls" only if more than half of these models have a lower error rate at their highest setting AND at most half a
higher risk judgement there; 9/9 and 7/9 → "What thinking adds". The site finds the same 9 models (render:
mailbox/ct-brief/review).
