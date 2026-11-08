# a. Models are too cautious

Source rows: the 38 ranked models of the live home leaderboard (/tmp/ctb/live/index.html #headline-table, one row per model at its highest reasoning setting, late entries included) and the Too safe chart (#too-safe, built by tools/site/story.py:313-339). Values: `risk.main.right_safety.share` (safe right) and `risk.main.found.share` (risks found) from data/results.json `leagues.<lg>.setups.<setup>` or data/v3/late-entries.json `entries[slug]`; each matches the chart label on the live page.

Criterion: KEEP if most ranked models have risks found well below safe right (count and median gap reported).

Result: 38 of 38 models have risks found < safe right. Gap (safe right − risks found): median 48.5 points, smallest 22.5, largest 69.4. Median safe right 87.5%, median risks found 35.0%.
Grey reference GNUbg weak (League 1, data/results.json leagues.league-1.setups["GNUbg weak"].risk.main): safe right 67.6%, risks found 66.6% (gap 1.1).
Live wording to reuse: chart legend 'right safety: played safe when safe was right' / 'risks found: took the risk when it paid' / 'GNUbg weak, a program: the grey reference pair' (story.py:333-335). The live 'Models are too cautious' section (story.py:429-454) uses the Clear risk scan bias instead: every one of 45 model setups has bias +30.0 to +80.6 pp; GNUbg weak −11.2/−14.1/−3.9 pp, Random −41.9 pp, Safest +100.0 pp (live index.html #finding-cautious; clear_risk_results.json sections[clear-risk-setups]).

Verdict: **KEEP** — heading: **Models are too cautious.**

| # | Model (setup) | Where | Safe right % | Risks found % | Gap | Source |
|---|---|---|---|---|---|---|
| 1 | GPT-6 Astra (GPT-6 Astra (high)) | late-entry | 95.5 | 53.3 | 42.2 | data/v3/late-entries.json entries[slug=gpt-6-astra-high].risk.main |
| 2 | Gemini 4 Argon (Gemini 4 Argon (high)) | league-3 | 97.4 | 50.8 | 46.6 | data/results.json leagues.league-3.setups["Gemini 4 Argon (high)"].risk.main |
| 3 | Claude Fable 5.1 (Claude Fable 5.1 (high)) | league-3 | 94.0 | 50.7 | 43.3 | data/results.json leagues.league-3.setups["Claude Fable 5.1 (high)"].risk.main |
| 4 | GPT-6.1 Sol (GPT-6.1 Sol (high)) | league-3 | 93.7 | 50.6 | 43.1 | data/results.json leagues.league-3.setups["GPT-6.1 Sol (high)"].risk.main |
| 5 | Claude Opus 5.5 (Claude Opus 5.5 (high)) | league-3 | 96.6 | 43.4 | 53.2 | data/results.json leagues.league-3.setups["Claude Opus 5.5 (high)"].risk.main |
| 6 | DeepSeek V4.1 Flash (DeepSeek V4.1 Flash (low)) | league-2 | 93.0 | 45.0 | 48.0 | data/results.json leagues.league-2.setups["DeepSeek V4.1 Flash (low)"].risk.main |
| 7 | Grok 4.7 (Grok 4.7 (high)) | league-3 | 93.0 | 44.0 | 49.1 | data/results.json leagues.league-3.setups["Grok 4.7 (high)"].risk.main |
| 8 | Claude Sonnet 5.5 (Claude Sonnet 5.5 (high)) | league-2 | 94.6 | 41.8 | 52.8 | data/results.json leagues.league-2.setups["Claude Sonnet 5.5 (high)"].risk.main |
| 9 | Gemini 3.8 Flash (Gemini 3.8 Flash (high)) | league-2 | 97.6 | 36.1 | 61.5 | data/results.json leagues.league-2.setups["Gemini 3.8 Flash (high)"].risk.main |
| 10 | Kimi K3.1 Pro (Kimi K3.1 Pro (off)) | league-3 | 89.5 | 42.4 | 47.1 | data/results.json leagues.league-3.setups["Kimi K3.1 Pro (off)"].risk.main |
| 11 | Gemma 4 31B (Gemma 4 31B (on)) | league-2 | 97.1 | 31.9 | 65.3 | data/results.json leagues.league-2.setups["Gemma 4 31B (on)"].risk.main |
| 12 | Liquid d1-ultra (Liquid d1-ultra) | league-2 | 86.0 | 42.0 | 44.0 | data/results.json leagues.league-2.setups["Liquid d1-ultra"].risk.main |
| 13 | Base Labs Mammoth-1 (Base Labs Mammoth-1) | late-entry | 86.4 | 40.0 | 46.4 | data/v3/late-entries.json entries[slug=base-labs-mammoth-1].risk.main |
| 14 | Drex Max v1 (Drex Max v1) | late-entry | 86.5 | 39.3 | 47.2 | data/v3/late-entries.json entries[slug=drex-max-v1].risk.main |
| 15 | Qwen3.8-27B (Qwen3.8-27B (low)) | league-2 | 90.2 | 33.8 | 56.3 | data/results.json leagues.league-2.setups["Qwen3.8-27B (low)"].risk.main |
| 16 | GLM-5.3 (GLM-5.3 (low)) | league-2 | 92.7 | 30.7 | 62.0 | data/results.json leagues.league-2.setups["GLM-5.3 (low)"].risk.main |
| 17 | REAX 1.3 (REAX 1.3) | late-entry | 89.4 | 31.7 | 57.7 | data/v3/late-entries.json entries[slug=reax-1-3].risk.main |
| 18 | Fastino GLiDE (Fastino GLiDE) | league-2 | 84.0 | 36.9 | 47.1 | data/results.json leagues.league-2.setups["Fastino GLiDE"].risk.main |
| 19 | Jev 1.13.0 (Jev 1.13.0) | league-1 | 92.1 | 27.0 | 65.1 | data/results.json leagues.league-1.setups["Jev 1.13.0"].risk.main |
| 20 | Qwen3.8 Flash (Qwen3.8 Flash (off)) | league-2 | 84.6 | 34.4 | 50.1 | data/results.json leagues.league-2.setups["Qwen3.8 Flash (off)"].risk.main |
| 21 | Jev 1.14.0 (Jev 1.14.0) | league-2 | 89.4 | 29.1 | 60.3 | data/results.json leagues.league-2.setups["Jev 1.14.0"].risk.main |
| 22 | Drex Max 1.1 (Drex Max 1.1) | late-entry | 82.5 | 35.6 | 46.9 | data/v3/late-entries.json entries[slug=drex-max-1-1].risk.main |
| 23 | Fastino GLiDE v1.2 (Fastino GLiDE v1.2 (local)) | league-1 | 84.6 | 33.0 | 51.6 | data/results.json leagues.league-1.setups["Fastino GLiDE v1.2 (local)"].risk.main |
| 24 | Drex 2.0 (Drex 2.0) | late-entry | 84.8 | 31.5 | 53.3 | data/v3/late-entries.json entries[slug=drex-2-0].risk.main |
| 25 | Decider v1.2 27B (Decider v1.2 27B) | league-1 | 82.5 | 33.4 | 49.1 | data/results.json leagues.league-1.setups["Decider v1.2 27B"].risk.main |
| 26 | Celeris-1 Decision (Celeris-1 Decision) | league-1 | 91.7 | 23.9 | 67.8 | data/results.json leagues.league-1.setups["Celeris-1 Decision"].risk.main |
| 27 | Base Labs Elephant-1 (Base Labs Elephant-1) | late-entry | 87.0 | 28.4 | 58.5 | data/v3/late-entries.json entries[slug=base-labs-elephant-1].risk.main |
| 28 | Clef (Clef) | league-2 | 75.6 | 39.5 | 36.1 | data/results.json leagues.league-2.setups["Clef"].risk.main |
| 29 | Cygnet (Gemma 4 12B) (Cygnet (Gemma 4 12B)) | league-1 | 86.8 | 27.3 | 59.5 | data/results.json leagues.league-1.setups["Cygnet (Gemma 4 12B)"].risk.main |
| 30 | Decider v1.1 27B (Decider v1.1 27B) | league-1 | 80.7 | 33.1 | 47.6 | data/results.json leagues.league-1.setups["Decider v1.1 27B"].risk.main |
| 31 | SubQ Snap 1.1 (SubQ Snap 1.1) | late-entry | 74.8 | 38.6 | 36.2 | data/v3/late-entries.json entries[slug=subq-snap-1-1].risk.main |
| 32 | SubQ Snap Preview (SubQ Snap Preview) | league-1 | 75.1 | 37.9 | 37.2 | data/results.json leagues.league-1.setups["SubQ Snap Preview"].risk.main |
| 33 | GPT-6 Luna (GPT-6 Luna) | league-1 | 89.7 | 21.6 | 68.1 | data/results.json leagues.league-1.setups["GPT-6 Luna"].risk.main |
| 34 | Winnow-12B (Winnow-12B) | league-1 | 76.6 | 33.7 | 42.9 | data/results.json leagues.league-1.setups["Winnow-12B"].risk.main |
| 35 | Mercury Decide (Mercury Decide) | league-1 | 88.1 | 18.7 | 69.4 | data/results.json leagues.league-1.setups["Mercury Decide"].risk.main |
| 36 | LFM2.5-24B-A2B (LFM2.5-24B-A2B (on)) | league-1 | 73.4 | 31.5 | 41.9 | data/results.json leagues.league-1.setups["LFM2.5-24B-A2B (on)"].risk.main |
| 37 | Decider Flash v1.2 (Decider Flash v1.2) | league-1 | 66.9 | 31.3 | 35.6 | data/results.json leagues.league-1.setups["Decider Flash v1.2"].risk.main |
| 38 | Open-Jev 27B v1.1 (Open-Jev 27B v1.1) | league-1 | 59.8 | 37.3 | 22.5 | data/results.json leagues.league-1.setups["Open-Jev 27B v1.1"].risk.main |
| – | GNUbg weak (reference) | league-1 | 67.6 | 66.6 | 1.1 | data/results.json leagues.league-1.setups["GNUbg weak"].risk.main |

**Wording (Zeki #2963):** risks found = right risks ÷ Risk pays decisions (a risky play at least 0.001 better than the
best safe play), so the section and the axis now say "found a worthwhile risk"; the chart compares the two success rates,
not how often a model plays risky at all. Numbers unchanged.
