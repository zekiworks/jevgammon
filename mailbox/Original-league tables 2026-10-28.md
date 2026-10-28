# Original-league tables, tiebreak applied (2026-10-28)

Under Can's tiebreak of 2026-10-28 (`mailbox/backgammon-ladder-cup.md`, Part 2, amendment of 2026-10-28): points, then head-to-head, then the lower error rate. Two tied setups: the winner of their match ranks higher (a drawn match: lower error rate). Three or more: a mini-table of the matches among them only; setups still level on it are ranked by the lower error rate. The rule was set after the ties were known.

**League 1 and League 3 are final. League 2 is provisional** until DeepSeek V4.1 Flash 1017 (on)'s 4 remaining matches (v GPT-6.1 Sol (low), Sol (high), LFM2.5-24B-A2B (on), (off)) are played; they wait for OpenRouter credit.

How it was computed: `python3 tools/original_league.py tables` (read-only on `v3.db`). Each setup in its original league (`league_web.league_origins`), GNUbg weak in all three; only valid matches between setups of the same original league count, 3/1/0. Error rate = 500 × mean GNUbg 1.08 2-ply equity loss over the setup's decisions with two or more legal plays, invalid answers (`fallback`) left out, **over the matches of that original-league table only** (so these rates differ slightly from the site's, which use all valid matches). Every one of these decisions is already scored in the site's shards (League 1: 37,110, League 2: 37,204, League 3: 16,724 decisions; none pending, none skipped), so `tools/site/score.sh` had nothing to add. Points for/against are match points.

## The ties Can asked about

- **League 1, Cygnet (Gemma 4 12B) v SubQ Snap Preview:** no tie in the original-league table. Their 37 points each were in the final *ladder* table. In the original-league table, Cygnet has 34 points (7th) and SubQ Snap Preview 28 (11th). Cygnet also won their match 7–3 (#36). No tiebreak is needed. League 1's ties that matter for the Cup:
  - 48 points, GNUbg weak and Liquid d1-ultra: GNUbg weak won their match 6–5 (#192). GNUbg weak is a program, so either way Liquid d1-ultra is League 1's #1 model.
  - 36 points, Jev 1.13.0, Jev 1.14.0 and Decider v1.2 27B (League 1's 3rd model place): the mini-table separates them, so no error rate is used. Jev 1.13.0 is 1st with 6 points, Jev 1.14.0 2nd with 3 and Decider v1.2 27B 3rd with 0.
- **League 2, the three setups on 39** (GPT-6.1 Sol (high), Claude Sonnet 5.5 (high), Gemma 4 31B (on); places 2–4, so this decides League 2's #2 and its 3rd place):
  - Head-to-head is a circle: Claude Sonnet 5.5 (high) beat GPT-6.1 Sol (high) 5–1 (#127). Gemma 4 31B (on) beat Claude Sonnet 5.5 (high) 4–2 (#202). GPT-6.1 Sol (high) beat Gemma 4 31B (on) 5–2 (#210).
  - Mini-table: 3 points each (1-0-1), so all three are still level and go to the error rate.
  - Error rates, over League 2's original-league matches: **GPT-6.1 Sol (high) 10.72**, Claude Sonnet 5.5 (high) 15.20, Gemma 4 31B (on) 18.92.
  - Order: 2. GPT-6.1 Sol (high), 3. Claude Sonnet 5.5 (high), 4. Gemma 4 31B (on).
  - **This can still change.** GPT-6.1 Sol (high) plays DeepSeek V4.1 Flash 1017 (on) in one of the 4 remaining matches. A win gives it 42 points, a clear 2nd. DeepSeek V4.1 Flash 1017 (on) has 28 points and can reach at most 40, which would put it 2nd only if it wins all four, and that includes beating Sol (high).

## Tables

## League 1: 19 setups, 171 of 171 pairings played (complete)

| # | Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|---|
| 1 | GNUbg weak (program) | 48 | 18 | 16-0-2 | 101 | 36 | 23.43 |
| 2 | Liquid d1-ultra | 48 | 18 | 16-0-2 | 90 | 43 | 29.98 |
| 3 | Fastino GLiDE | 37 | 18 | 12-1-5 | 77 | 49 | 37.12 |
| 4 | Jev 1.13.0 | 36 | 18 | 12-0-6 | 81 | 47 | 34.83 |
| 5 | Jev 1.14.0 | 36 | 18 | 12-0-6 | 77 | 52 | 35.24 |
| 6 | Decider v1.2 27B | 36 | 18 | 12-0-6 | 84 | 46 | 36.99 |
| 7 | Cygnet (Gemma 4 12B) | 34 | 18 | 11-1-6 | 75 | 59 | 39.08 |
| 8 | Clef | 32 | 18 | 10-2-6 | 69 | 53 | 37.29 |
| 9 | Fastino GLiDE v1.2 (local) | 30 | 18 | 10-0-8 | 69 | 55 | 35.62 |
| 10 | Celeris-1 Decision | 30 | 18 | 9-3-6 | 74 | 63 | 32.46 |
| 11 | SubQ Snap Preview | 28 | 18 | 9-1-8 | 76 | 58 | 46.65 |
| 12 | GPT-6 Luna | 27 | 18 | 9-0-9 | 62 | 65 | 41.92 |
| 13 | Decider v1.1 27B | 27 | 18 | 9-0-9 | 69 | 60 | 37.75 |
| 14 | Mercury Decide | 19 | 18 | 6-1-11 | 51 | 78 | 47.10 |
| 15 | Winnow-12B | 12 | 18 | 4-0-14 | 51 | 77 | 48.38 |
| 16 | Safest (program) | 12 | 18 | 3-3-12 | 50 | 83 | 51.17 |
| 17 | Open-Jev 27B v1.1 | 8 | 18 | 2-2-14 | 38 | 96 | 64.67 |
| 18 | Decider Flash v1.2 | 6 | 18 | 2-0-16 | 36 | 97 | 58.19 |
| 19 | Random (program) | 0 | 18 | 0-0-18 | 6 | 119 | 118.50 |

Ties on points in League 1:

- 48 points: GNUbg weak and Liquid d1-ultra: GNUbg weak beat Liquid d1-ultra 6–5 (#192); decided by head-to-head.

- 36 points: Decider v1.2 27B, Jev 1.13.0, Jev 1.14.0: mini-table of the matches among them:

  - Jev 1.13.0 beat Decider v1.2 27B 7–0 (#416)
  - Jev 1.14.0 beat Decider v1.2 27B 4–3 (#415)
  - Jev 1.13.0 beat Jev 1.14.0 5–1 (#287)

  | Setup | Mini Pts | P | W-D-L | For | Against | Error rate |
  |---|---|---|---|---|---|---|
  | Jev 1.13.0 | 6 | 2 | 2-0-0 | 12 | 1 | 34.83 |
  | Jev 1.14.0 | 3 | 2 | 1-0-1 | 5 | 8 | 35.24 |
  | Decider v1.2 27B | 0 | 2 | 0-0-2 | 3 | 11 | 36.99 |

  The mini-table separates them; no error rate needed.

- 30 points: Celeris-1 Decision and Fastino GLiDE v1.2 (local): Fastino GLiDE v1.2 (local) beat Celeris-1 Decision 5–1 (#493); decided by head-to-head.

- 27 points: Decider v1.1 27B and GPT-6 Luna: GPT-6 Luna beat Decider v1.1 27B 4–2 (#254); decided by head-to-head.

- 12 points: Safest and Winnow-12B: Winnow-12B beat Safest 5–3 (#238); decided by head-to-head.

## League 2: 19 setups, 167 of 171 pairings played (4 pairings missing, provisional)

Missing: DeepSeek V4.1 Flash 1017 (on) v GPT-6.1 Sol (high); DeepSeek V4.1 Flash 1017 (on) v GPT-6.1 Sol (low); DeepSeek V4.1 Flash 1017 (on) v LFM2.5-24B-A2B (off); DeepSeek V4.1 Flash 1017 (on) v LFM2.5-24B-A2B (on).

| # | Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|---|
| 1 | GPT-6.1 Sol (low) | 48 | 17 | 16-0-1 | 88 | 32 | 10.84 |
| 2 | GPT-6.1 Sol (high) | 39 | 17 | 13-0-4 | 74 | 39 | 10.72 |
| 3 | Claude Sonnet 5.5 (high) | 39 | 18 | 13-0-5 | 82 | 46 | 15.20 |
| 4 | Gemma 4 31B (on) | 39 | 18 | 13-0-5 | 79 | 54 | 18.92 |
| 5 | Gemini 3.8 Flash (low) | 38 | 18 | 12-2-4 | 84 | 47 | 16.59 |
| 6 | Claude Sonnet 5.5 (low) | 37 | 18 | 12-1-5 | 82 | 48 | 20.04 |
| 7 | Gemini 3.8 Flash (high) | 36 | 18 | 12-0-6 | 77 | 48 | 14.46 |
| 8 | DeepSeek V4.1 Flash (on) | 33 | 18 | 11-0-7 | 77 | 55 | 17.63 |
| 9 | DeepSeek V4.1 Flash 1017 (on) | 28 | 14 | 9-1-4 | 67 | 43 | 15.78 |
| 10 | Qwen3.8-27B (on) | 27 | 18 | 9-0-9 | 58 | 61 | 30.30 |
| 11 | Gemma 4 31B (off) | 25 | 18 | 8-1-9 | 63 | 59 | 22.06 |
| 12 | GNUbg weak (program) | 24 | 18 | 8-0-10 | 67 | 66 | 25.03 |
| 13 | GLM-5.3 (on) | 21 | 18 | 7-0-11 | 56 | 78 | 29.65 |
| 14 | DeepSeek V4.1 Flash 1017 (off) | 15 | 18 | 5-0-13 | 56 | 82 | 34.90 |
| 15 | Qwen3.8 Flash (off) | 15 | 18 | 5-0-13 | 50 | 86 | 33.67 |
| 16 | DeepSeek V4.1 Flash (off) | 13 | 18 | 4-1-13 | 56 | 83 | 31.90 |
| 17 | Qwen3.8-27B (off) | 12 | 18 | 4-0-14 | 37 | 91 | 40.51 |
| 18 | LFM2.5-24B-A2B (on) | 9 | 17 | 3-0-14 | 38 | 91 | 46.10 |
| 19 | LFM2.5-24B-A2B (off) | 0 | 17 | 0-0-17 | 13 | 95 | 62.19 |

Ties on points in League 2:

- 39 points: Claude Sonnet 5.5 (high), GPT-6.1 Sol (high), Gemma 4 31B (on): mini-table of the matches among them:

  - Claude Sonnet 5.5 (high) beat GPT-6.1 Sol (high) 5–1 (#127)
  - Gemma 4 31B (on) beat Claude Sonnet 5.5 (high) 4–2 (#202)
  - GPT-6.1 Sol (high) beat Gemma 4 31B (on) 5–2 (#210)

  | Setup | Mini Pts | P | W-D-L | For | Against | Error rate |
  |---|---|---|---|---|---|---|
  | GPT-6.1 Sol (high) | 3 | 2 | 1-0-1 | 6 | 7 | 10.72 |
  | Claude Sonnet 5.5 (high) | 3 | 2 | 1-0-1 | 7 | 5 | 15.20 |
  | Gemma 4 31B (on) | 3 | 2 | 1-0-1 | 6 | 7 | 18.92 |

  Still level on the mini-table, ranked by the lower error rate: GPT-6.1 Sol (high) (10.72), Claude Sonnet 5.5 (high) (15.20), Gemma 4 31B (on) (18.92).

- 15 points: DeepSeek V4.1 Flash 1017 (off) and Qwen3.8 Flash (off): DeepSeek V4.1 Flash 1017 (off) beat Qwen3.8 Flash (off) 6–1 (#629); decided by head-to-head.

## League 3: 12 setups, 66 of 66 pairings played (complete)

| # | Setup | Pts | P | W-D-L | For | Against | Error rate |
|---|---|---|---|---|---|---|---|
| 1 | GPT-6 Astra (on) | 27 | 11 | 9-0-2 | 49 | 30 | 12.24 |
| 2 | Claude Fable 5.1 (on) | 24 | 11 | 8-0-3 | 51 | 31 | 13.07 |
| 3 | Grok 4.7 (on) | 19 | 11 | 6-1-4 | 39 | 40 | 16.29 |
| 4 | Claude Opus 5.5 (on) | 18 | 11 | 6-0-5 | 48 | 37 | 14.50 |
| 5 | GPT-6 Astra (off) | 17 | 11 | 5-2-4 | 44 | 33 | 11.25 |
| 6 | Gemini 4 Argon (on) | 16 | 11 | 5-1-5 | 36 | 43 | 12.20 |
| 7 | Gemini 4 Argon (off) | 16 | 11 | 5-1-5 | 38 | 45 | 16.65 |
| 8 | Claude Opus 5.5 (off) | 15 | 11 | 5-0-6 | 38 | 42 | 16.14 |
| 9 | Kimi K3.1 Pro (off) | 15 | 11 | 5-0-6 | 38 | 38 | 28.57 |
| 10 | Grok 4.7 (off) | 12 | 11 | 4-0-7 | 33 | 40 | 19.75 |
| 11 | GNUbg weak (program) | 8 | 11 | 2-2-7 | 32 | 54 | 28.56 |
| 12 | Claude Fable 5.1 (off) | 7 | 11 | 2-1-8 | 37 | 50 | 18.13 |

Ties on points in League 3:

- 16 points: Gemini 4 Argon (off) and Gemini 4 Argon (on): Gemini 4 Argon (on) beat Gemini 4 Argon (off) 4–2 (#432); decided by head-to-head.

- 15 points: Claude Opus 5.5 (off) and Kimi K3.1 Pro (off): Claude Opus 5.5 (off) beat Kimi K3.1 Pro (off) 5–4 (#603); decided by head-to-head.

