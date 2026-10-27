# Original-league tables (2026-10-27)

**Provisional.** League 2 is not complete yet: DeepSeek V4.1 Flash 1017 (off) v LFM2.5-24B-A2B (on) (#752) is still being played, and the 4 DeepSeek V4.1 Flash 1017 (on) matches (vs GPT-6.1 Sol (low), Sol (high), LFM2.5-24B-A2B (on) and (off)) wait for OpenRouter credit (Can's decision after the Nackgammon test's extension spend is known). Leagues 1 and 3 are complete.

Rule (Can): each setup in its original league (`league_web.league_origins`), GNUbg weak in all three; only matches between setups of the same original league count, 3 points for a win, 1 for a draw, 0 for a loss. Rows are ordered by points only, then name. **No tiebreak is applied** (still to be confirmed by Can: head-to-head, then error rate). Rosters unchanged. Points for/against are match points (game points, gammons 2, backgammons 3). Error rate = 500 × mean 2-ply equity loss over all the setup's valid matches (the dashboard's tiebreak figure, from the site's GNUbg score shards; decisions of the new matches are counted once scored).

## The new matches

Played in two hidden leagues (league 7: League 2's rules and seed, only DeepSeek V4.1 Flash 1017 (off)'s pairs, `leagues/league2-1017off-gap.json`; league 6: League 3's rules and seed, only Kimi K3.1 Pro (off)'s pairs, `leagues/league3-kimi-gap.json`), started by `tools/v3/run_league2_early.sh`. Prompt bg-v2, games of a round at once, 3 rounds, turn limit 300, no clock. Stored as normal valid matches. LFM2.5-24B-A2B ran on NackRun's GPU 3 server (same script and arguments as the league), shared.

| # | Match | Result | Status |
|---|---|---|---|
| 748 | DeepSeek V4.1 Flash 1017 (off) v GPT-6.1 Sol (high) | 1–6 (GPT-6.1 Sol (high) wins) | finished |
| 749 | DeepSeek V4.1 Flash 1017 (off) v GPT-6.1 Sol (low) | 1–5 (GPT-6.1 Sol (low) wins) | finished |
| 750 | Kimi K3.1 Pro (off) v Grok 4.7 (off) | 0–5 (Grok 4.7 (off) wins) | finished |
| 751 | Kimi K3.1 Pro (off) v Claude Fable 5.1 (off) | 5–1 (Kimi K3.1 Pro (off) wins) | finished |
| 752 | DeepSeek V4.1 Flash 1017 (off) v LFM2.5-24B-A2B (on) | 0–0 | running, 1 game finished |
| 753 | DeepSeek V4.1 Flash 1017 (off) v LFM2.5-24B-A2B (off) | 6–1 (DeepSeek V4.1 Flash 1017 (off) wins) | finished |

Not played yet (waiting for credit): DeepSeek V4.1 Flash 1017 (on) v GPT-6.1 Sol (low), v GPT-6.1 Sol (high), v LFM2.5-24B-A2B (on), v LFM2.5-24B-A2B (off).

## Spend

OpenRouter: $0.77 for these matches (cap $1.20; estimate before starting $0.97: 1017 (off) $0.027 and Kimi K3.1 Pro (off) $0.43 per match on average in their logged matches). openrouter:deepseek: $0.088, openrouter:moonshotai/mxfp4: $0.677. Credits at the start: $6.79 left ($115.00 total, $108.21 used). GPT-6.1 Sol, Claude Fable and Grok on subscriptions; LFM2.5 on our GPU.

## League 1: 19 setups, 171 of 171 pairings played (complete)

| Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|
| GNUbg weak | 48 | 18 | 16-0-2 | 101 | 36 | 25.5 |
| Liquid d1-ultra | 48 | 18 | 16-0-2 | 90 | 43 | 30.1 |
| Fastino GLiDE | 37 | 18 | 12-1-5 | 77 | 49 | 34.5 |
| Decider v1.2 27B | 36 | 18 | 12-0-6 | 84 | 46 | 36.5 |
| Jev 1.13.0 | 36 | 18 | 12-0-6 | 81 | 47 | 34.4 |
| Jev 1.14.0 | 36 | 18 | 12-0-6 | 77 | 52 | 34.5 |
| Cygnet (Gemma 4 12B) | 34 | 18 | 11-1-6 | 75 | 59 | 38.0 |
| Clef | 32 | 18 | 10-2-6 | 69 | 53 | 37.0 |
| Celeris-1 Decision | 30 | 18 | 9-3-6 | 74 | 63 | 33.1 |
| Fastino GLiDE v1.2 (local) | 30 | 18 | 10-0-8 | 69 | 55 | 35.5 |
| SubQ Snap Preview | 28 | 18 | 9-1-8 | 76 | 58 | 43.9 |
| Decider v1.1 27B | 27 | 18 | 9-0-9 | 69 | 60 | 38.2 |
| GPT-6 Luna | 27 | 18 | 9-0-9 | 62 | 65 | 41.7 |
| Mercury Decide | 19 | 18 | 6-1-11 | 51 | 78 | 46.5 |
| Safest | 12 | 18 | 3-3-12 | 50 | 83 | 51.0 |
| Winnow-12B | 12 | 18 | 4-0-14 | 51 | 77 | 48.6 |
| Open-Jev 27B v1.1 | 8 | 18 | 2-2-14 | 38 | 96 | 65.0 |
| Decider Flash v1.2 | 6 | 18 | 2-0-16 | 36 | 97 | 59.9 |
| Random | 0 | 18 | 0-0-18 | 6 | 119 | 119.4 |

## League 2: 19 setups, 166 of 171 pairings played (5 pairings missing)

Missing: DeepSeek V4.1 Flash 1017 (off) v LFM2.5-24B-A2B (on); DeepSeek V4.1 Flash 1017 (on) v GPT-6.1 Sol (high); DeepSeek V4.1 Flash 1017 (on) v GPT-6.1 Sol (low); DeepSeek V4.1 Flash 1017 (on) v LFM2.5-24B-A2B (off); DeepSeek V4.1 Flash 1017 (on) v LFM2.5-24B-A2B (on).

| Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|
| GPT-6.1 Sol (low) | 48 | 17 | 16-0-1 | 88 | 32 | 11.5 |
| Claude Sonnet 5.5 (high) | 39 | 18 | 13-0-5 | 82 | 46 | 15.4 |
| GPT-6.1 Sol (high) | 39 | 17 | 13-0-4 | 74 | 39 | 10.5 |
| Gemma 4 31B (on) | 39 | 18 | 13-0-5 | 79 | 54 | 19.3 |
| Gemini 3.8 Flash (low) | 38 | 18 | 12-2-4 | 84 | 47 | 17.4 |
| Claude Sonnet 5.5 (low) | 37 | 18 | 12-1-5 | 82 | 48 | 19.8 |
| Gemini 3.8 Flash (high) | 36 | 18 | 12-0-6 | 77 | 48 | 14.4 |
| DeepSeek V4.1 Flash (on) | 33 | 18 | 11-0-7 | 77 | 55 | 18.4 |
| DeepSeek V4.1 Flash 1017 (on) | 28 | 14 | 9-1-4 | 67 | 43 | 16.5 |
| Qwen3.8-27B (on) | 27 | 18 | 9-0-9 | 58 | 61 | 29.1 |
| Gemma 4 31B (off) | 25 | 18 | 8-1-9 | 63 | 59 | 22.4 |
| GNUbg weak | 24 | 18 | 8-0-10 | 67 | 66 | 25.5 |
| GLM-5.3 (on) | 21 | 18 | 7-0-11 | 56 | 78 | 30.3 |
| DeepSeek V4.1 Flash 1017 (off) | 15 | 17 | 5-0-12 | 53 | 77 | 34.1 |
| Qwen3.8 Flash (off) | 15 | 18 | 5-0-13 | 50 | 86 | 33.8 |
| DeepSeek V4.1 Flash (off) | 13 | 18 | 4-1-13 | 56 | 83 | 33.7 |
| Qwen3.8-27B (off) | 12 | 18 | 4-0-14 | 37 | 91 | 41.5 |
| LFM2.5-24B-A2B (on) | 6 | 16 | 2-0-14 | 33 | 88 | 47.4 |
| LFM2.5-24B-A2B (off) | 0 | 17 | 0-0-17 | 13 | 95 | 60.2 |

## League 3: 12 setups, 66 of 66 pairings played (complete)

| Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|
| GPT-6 Astra (on) | 27 | 11 | 9-0-2 | 49 | 30 | 11.5 |
| Claude Fable 5.1 (on) | 24 | 11 | 8-0-3 | 51 | 31 | 13.6 |
| Grok 4.7 (on) | 19 | 11 | 6-1-4 | 39 | 40 | 17.7 |
| Claude Opus 5.5 (on) | 18 | 11 | 6-0-5 | 48 | 37 | 13.9 |
| GPT-6 Astra (off) | 17 | 11 | 5-2-4 | 44 | 33 | 11.3 |
| Gemini 4 Argon (off) | 16 | 11 | 5-1-5 | 38 | 45 | 15.9 |
| Gemini 4 Argon (on) | 16 | 11 | 5-1-5 | 36 | 43 | 11.7 |
| Claude Opus 5.5 (off) | 15 | 11 | 5-0-6 | 38 | 42 | 15.6 |
| Kimi K3.1 Pro (off) | 15 | 11 | 5-0-6 | 38 | 38 | 26.8 |
| Grok 4.7 (off) | 12 | 11 | 4-0-7 | 33 | 40 | 19.1 |
| GNUbg weak | 8 | 11 | 2-2-7 | 32 | 54 | 25.5 |
| Claude Fable 5.1 (off) | 7 | 11 | 2-1-8 | 37 | 50 | 17.9 |
