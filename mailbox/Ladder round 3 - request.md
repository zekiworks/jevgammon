# Ladder round 3: request

Oct 25, 2026 19:01 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

**Provisional, not applied.** Round 2 had late entries (Kimi K3.1 Pro (off), DeepSeek V4.1 Flash 1017 (off)/(on)), so this round is provisional until Can approves it. Pairings of Gemini 3.8 Flash (low) and Qwen3.8-27B (off) are listed but not played: skipped by Can (23 of 37; marked in the table). Gemini 4 Argon (off)'s League 2 matches were pre-played as an early start (approved by Can) in hidden league #4, 2026-10-25 12:17-16:45 UTC; they are reused below, not played again. Without the skipped pairings: 14 new pairings (1-11, 35-37), money (API price) $2.72, API-equivalent $17.65, match time 15.0 h; the totals below are the tool's, over all 37.

Error rates and tables leave out matches held only by the hidden league (the plan's error-rate query now skips them, as the site's scoring does).

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. GNUbg weak (program): 48 pts, games 54-24, error rate 25.5; 2. Jev 1.14.0: 42 pts, games 57-35, error rate 36.8; 3. Jev 1.13.0: 39 pts, games 56-34, error rate 34.4 … last: 19. Random (program): 0 pts, games 6-58, error rate 118.2; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 30-64, error rate 58.7
- **League 2 (workhorses)** (19 setups): 1. Gemini 3.8 Flash (low): 44 pts, games 65-39, error rate 16.7; 2. Claude Sonnet 5.5 (low): 40 pts, games 66-42, error rate 20.3; 3. DeepSeek V4.1 Flash 1017 (on): 40 pts, games 62-46, error rate 16.3 … last: 19. Qwen3.8-27B (off): 6 pts, games 30-70, error rate 41.1
- **League 3 (frontier models)** (12 setups): 1. GPT-6.1 Sol (low): 27 pts, games 41-25, error rate 11.5; 2. GPT-6 Astra (on): 24 pts, games 36-26, error rate 11.7; 3. GPT-6.1 Sol (high): 21 pts, games 38-26, error rate 10.7 … last: 12. GNUbg weak (program): 8 pts, games 26-38, error rate 25.5; last setup that can move: 11. Gemini 4 Argon (off): 10 pts, games 27-43, error rate 16.5

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 3 | Jev 1.14.0 | League 1 | League 2 | promoted |
| 3 | Qwen3.8-27B (off) | League 2 | League 1 | relegated |
| 3 | Gemini 3.8 Flash (low) | League 2 | League 3 | promoted |
| 3 | Gemini 4 Argon (off) | League 3 | League 2 | relegated |

- League 1: GNUbg weak ranks above Jev 1.14.0 but is a program and never moves; the next setup is taken.
- League 3: GNUbg weak ranks below Gemini 4 Argon (off) but is a program and never moves; the next setup is taken.

Earlier rounds:

- round 1: Liquid d1-ultra, League 1 to League 2, promoted
- round 1: LFM2.5-24B-A2B (off), League 2 to League 1, relegated
- round 1: GPT-6.1 Sol (low), League 2 to League 3, promoted
- round 1: Claude Fable 5.1 (off), League 3 to League 2, relegated
- round 2: Fastino GLiDE, League 1 to League 2, promoted
- round 2: LFM2.5-24B-A2B (on), League 2 to League 1, relegated
- round 2: GPT-6.1 Sol (high), League 2 to League 3, promoted
- round 2: Grok 4.7 (off), League 3 to League 2, relegated

## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Jev 1.14.0 | 36.8 (95% interval 32.9-41.1; 1,897 decisions) | Qwen3.8-27B (off) | 41.1 (95% interval 37.4-44.8; 2,320 decisions) | no |
| League 2-League 3 | Gemini 3.8 Flash (low) | 16.7 (95% interval 15.0-18.4; 2,468 decisions) | Gemini 4 Argon (off) | 16.5 (95% interval 13.7-19.4; 1,484 decisions) | **flagged: worse than the setup it replaces** |

## Lineups after the round

- **League 1** (19 setups): joins Qwen3.8-27B (off); leaves Jev 1.14.0.
- **League 2** (19 setups): joins Jev 1.14.0, Gemini 4 Argon (off); leaves Gemini 3.8 Flash (low), Qwen3.8-27B (off).
- **League 3** (12 setups): joins Gemini 3.8 Flash (low); leaves Gemini 4 Argon (off).

## New pairings (37)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | League 2 | Jev 1.14.0 v Claude Fable 5.1 (off) | $0.02 | $7.47 | 4 min | none | claude-subscription, jev |  |
| 2 | League 2 | Jev 1.14.0 v Claude Sonnet 5.5 (high) | $0.02 | $2.30 | 10 min | none | claude-subscription, jev |  |
| 3 | League 2 | Jev 1.14.0 v Claude Sonnet 5.5 (low) | $0.02 | $1.50 | 4 min | none | claude-subscription, jev |  |
| 4 | League 2 | Jev 1.14.0 v DeepSeek V4.1 Flash (off) | $0.08 | $0.00 | 11 min | none | jev, openrouter:fireworks |  |
| 5 | League 2 | Jev 1.14.0 v DeepSeek V4.1 Flash (on) | $1.48 | $0.00 | 1.6 h | none | jev, openrouter:fireworks |  |
| 6 | League 2 | Jev 1.14.0 v DeepSeek V4.1 Flash 1017 (off) | $0.04 | $0.00 | 27 min | none | jev, openrouter:deepseek |  |
| 7 | League 2 | Jev 1.14.0 v DeepSeek V4.1 Flash 1017 (on) | $0.56 | $0.00 | 1.1 h | none | jev, openrouter:deepseek |  |
| 8 | League 2 | Jev 1.14.0 v GLM-5.3 (on) | $0.35 | $0.00 | 11 min | none | jev, openrouter:fireworks |  |
| 9 | League 2 | Jev 1.14.0 v Gemini 3.8 Flash (high) | $0.02 | $2.65 | 23 min | none | antigravity-subscription, jev |  |
| 10 | League 2 | Jev 1.14.0 v Grok 4.7 (off) | $0.02 | $3.73 | 1.1 h | none | jev, xai-subscription |  |
| 11 | League 2 | Jev 1.14.0 v Qwen3.8 Flash (off) | $0.05 | $0.00 | 14 min | none | jev, openrouter:alibaba |  |
| 12 | League 3 | Gemini 3.8 Flash (low) v Claude Fable 5.1 (on) | $0.00 | $15.72 | 27 min | none | antigravity-subscription, claude-subscription | **not played: skipped by Can** |
| 13 | League 3 | Gemini 3.8 Flash (low) v Claude Opus 5.5 (off) | $0.00 | $3.95 | 10 min | none | antigravity-subscription, claude-subscription | **not played: skipped by Can** |
| 14 | League 3 | Gemini 3.8 Flash (low) v Claude Opus 5.5 (on) | $0.00 | $5.05 | 16 min | none | antigravity-subscription, claude-subscription | **not played: skipped by Can** |
| 15 | League 3 | Gemini 3.8 Flash (low) v GPT-6 Astra (off) | $0.00 | $6.28 | 11 min | none | antigravity-subscription, chatgpt-subscription | **not played: skipped by Can** |
| 16 | League 3 | Gemini 3.8 Flash (low) v GPT-6 Astra (on) | $0.00 | $6.45 | 13 min | none | antigravity-subscription, chatgpt-subscription | **not played: skipped by Can** |
| 17 | League 3 | Gemini 3.8 Flash (low) v Gemini 4 Argon (on) | $0.00 | $7.59 | 1.4 h | none | antigravity-subscription | **not played: skipped by Can** |
| 18 | League 3 | Gemini 3.8 Flash (low) v Grok 4.7 (on) | $0.00 | $14.26 | 4.4 h | none | antigravity-subscription, xai-subscription | **not played: skipped by Can** |
| 19 | League 3 | Gemini 3.8 Flash (low) v Kimi K3.1 Pro (off) | $0.43 | $0.45 | 7 min | none | antigravity-subscription, openrouter:moonshotai/mxfp4 | **not played: skipped by Can** |
| 20 | League 1 | Qwen3.8-27B (off) v Decider Flash v1.2 | $0.00 | $0.00 | 3 min | qwen38-27b.sh: Qwen3.8-27B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none | **not played: skipped by Can** |
| 21 | League 1 | Qwen3.8-27B (off) v Decider v1.2 27B | $0.00 | $0.00 | 5 min | qwen38-27b.sh: Qwen3.8-27B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none | **not played: skipped by Can** |
| 22 | League 1 | Qwen3.8-27B (off) v Winnow-12B | $0.00 | $0.00 | 5 min | qwen38-27b.sh: Qwen3.8-27B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none | **not played: skipped by Can** |
| 23 | League 1 | Qwen3.8-27B (off) v Decider v1.1 27B | $0.00 | $0.00 | 10 min | qwen38-27b.sh: Qwen3.8-27B (bariton); decider.sh: Decider v1.1 27B (bariton) | none | **not played: skipped by Can** |
| 24 | League 1 | Qwen3.8-27B (off) v Fastino GLiDE v1.2 (local) | $0.00 | $0.00 | 4 min | qwen38-27b.sh: Qwen3.8-27B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton) | none | **not played: skipped by Can** |
| 25 | League 1 | Qwen3.8-27B (off) v Clef | $0.00 | $0.00 | 12 min | qwen38-27b.sh: Qwen3.8-27B (bariton); local server at 127.0.0.1:18091 | none | **not played: skipped by Can** |
| 26 | League 1 | Qwen3.8-27B (off) v Cygnet (Gemma 4 12B) | $0.00 | $0.00 | 3 min | qwen38-27b.sh: Qwen3.8-27B (bariton); local server at 127.0.0.1:18093 | none | **not played: skipped by Can** |
| 27 | League 1 | Qwen3.8-27B (off) v Open-Jev 27B v1.1 | $0.00 | $0.00 | 6 min | qwen38-27b.sh: Qwen3.8-27B (bariton); open-jev.sh: Open-Jev 27B v1.1 (bariton) | none | **not played: skipped by Can** |
| 28 | League 1 | Qwen3.8-27B (off) v Celeris-1 Decision | $0.02 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | celeris | **not played: skipped by Can** |
| 29 | League 1 | Qwen3.8-27B (off) v GPT-6 Luna | $0.04 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | openai-decisions | **not played: skipped by Can** |
| 30 | League 1 | Qwen3.8-27B (off) v Jev 1.13.0 | $0.02 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | jev | **not played: skipped by Can** |
| 31 | League 1 | Qwen3.8-27B (off) v Mercury Decide | $0.01 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | openrouter (inception) | **not played: skipped by Can** |
| 32 | League 1 | Qwen3.8-27B (off) v Random | $0.00 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | none | **not played: skipped by Can** |
| 33 | League 1 | Qwen3.8-27B (off) v Safest | $0.00 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | none | **not played: skipped by Can** |
| 34 | League 1 | Qwen3.8-27B (off) v SubQ Snap Preview | $0.02 | $0.00 | 2 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | subq | **not played: skipped by Can** |
| 35 | League 2 | Jev 1.14.0 v Gemma 4 31B (off) | $0.02 | $0.00 | 3 min | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | jev |  |
| 36 | League 2 | Jev 1.14.0 v Gemma 4 31B (on) | $0.02 | $0.00 | 3.9 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | jev |  |
| 37 | League 2 | Jev 1.14.0 v Qwen3.8-27B (on) | $0.02 | $0.00 | 5.5 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | jev |  |

## Reused pairings (27)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Jev 1.14.0 v GNUbg weak | #263 (2026-10-19) | League 1 | GNUbg weak 7-2 Jev 1.14.0 |
| League 2 | Jev 1.14.0 v Liquid d1-ultra | #265 (2026-10-19) | League 1 | Liquid d1-ultra 4-2 Jev 1.14.0 |
| League 2 | Jev 1.14.0 v Fastino GLiDE | #377 (2026-10-20) | League 1 | Fastino GLiDE 5-3 Jev 1.14.0 |
| League 2 | Jev 1.14.0 v Gemini 4 Argon (off) | #659 (2026-10-25) | early start, hidden league #4 | Jev 1.14.0 1-6 Gemini 4 Argon (off) |
| League 1 | Qwen3.8-27B (off) v GNUbg weak | #404 (2026-10-20) | League 2 | GNUbg weak 5-0 Qwen3.8-27B (off) |
| League 1 | Qwen3.8-27B (off) v LFM2.5-24B-A2B (off) | #407 (2026-10-20) | League 2 | Qwen3.8-27B (off) 4-3 LFM2.5-24B-A2B (off) |
| League 1 | Qwen3.8-27B (off) v LFM2.5-24B-A2B (on) | #402 (2026-10-20) | League 2 | LFM2.5-24B-A2B (on) 1-5 Qwen3.8-27B (off) |
| League 3 | Gemini 3.8 Flash (low) v GNUbg weak | #129 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 8-0 GNUbg weak |
| League 3 | Gemini 3.8 Flash (low) v GPT-6.1 Sol (low) | #130 (2026-10-19) | League 2 | GPT-6.1 Sol (low) 5-2 Gemini 3.8 Flash (low) |
| League 3 | Gemini 3.8 Flash (low) v GPT-6.1 Sol (high) | #135 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 0-5 GPT-6.1 Sol (high) |
| League 2 | Gemini 4 Argon (off) v Gemini 3.8 Flash (high) | #658 (2026-10-25) | early start, hidden league #4 | Gemini 3.8 Flash (high) 4-3 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Claude Sonnet 5.5 (low) | #652 (2026-10-25) | early start, hidden league #4 | Claude Sonnet 5.5 (low) 3-4 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Claude Sonnet 5.5 (high) | #657 (2026-10-25) | early start, hidden league #4 | Claude Sonnet 5.5 (high) 2-4 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v DeepSeek V4.1 Flash (off) | #655 (2026-10-25) | early start, hidden league #4 | DeepSeek V4.1 Flash (off) 0-7 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v DeepSeek V4.1 Flash (on) | #656 (2026-10-25) | early start, hidden league #4 | DeepSeek V4.1 Flash (on) 3-6 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v GLM-5.3 (on) | #654 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 6-0 GLM-5.3 (on) |
| League 2 | Gemini 4 Argon (off) v GNUbg weak | #437 (2026-10-20) | League 3 | GNUbg weak 3-4 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Qwen3.8 Flash (off) | #663 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 3-5 Qwen3.8 Flash (off) |
| League 2 | Gemini 4 Argon (off) v Gemma 4 31B (on) | #662 (2026-10-25) | early start, hidden league #4 | Gemma 4 31B (on) 5-2 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Gemma 4 31B (off) | #665 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 5-4 Gemma 4 31B (off) |
| League 2 | Gemini 4 Argon (off) v Qwen3.8-27B (on) | #666 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 5-2 Qwen3.8-27B (on) |
| League 2 | Gemini 4 Argon (off) v Liquid d1-ultra | #661 (2026-10-25) | early start, hidden league #4 | Liquid d1-ultra 4-4 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Claude Fable 5.1 (off) | #452 (2026-10-20) | League 3 | Claude Fable 5.1 (off) 3-7 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Fastino GLiDE | #660 (2026-10-25) | early start, hidden league #4 | Fastino GLiDE 2-5 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Grok 4.7 (off) | #468 (2026-10-21) | League 3 | Gemini 4 Argon (off) 4-3 Grok 4.7 (off) |
| League 2 | Gemini 4 Argon (off) v DeepSeek V4.1 Flash 1017 (off) | #664 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 5-2 DeepSeek V4.1 Flash 1017 (off) |
| League 2 | Gemini 4 Argon (off) v DeepSeek V4.1 Flash 1017 (on) | #653 (2026-10-25) | early start, hidden league #4 | Gemini 4 Argon (off) 1-6 DeepSeek V4.1 Flash 1017 (on) |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.

1. **API and subscription (no GPU)**: pairings 1-19 (19); needs no GPU; 12.7 h of match time, about 4.4 h wall time (Gemini 3.8 Flash (low), Jev 1.14.0).
2. **League 1 GPU block 1**: pairings 20-24 (5); needs 4 bariton GPU(s); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU); decider.sh: Decider v1.1 27B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton); qwen38-27b.sh: Qwen3.8-27B (bariton); 28 min of match time, about 10 min wall time (Qwen3.8-27B (off)).
3. **League 1 GPU block 2**: pairings 25-34 (10); needs 4 bariton GPU(s); local server at 127.0.0.1:18091; local server at 127.0.0.1:18093; open-jev.sh: Open-Jev 27B v1.1 (bariton); qwen38-27b.sh: Qwen3.8-27B (bariton); 37 min of match time, about 12 min wall time (Qwen3.8-27B (off)).
4. **League 2 GPU block**: pairings 35-37 (3); needs 2 bariton GPU(s); gemma4-31b-replicas.sh: Gemma 4 31B (bariton); qwen38-27b.sh: Qwen3.8-27B (bariton); 9.5 h of match time, about 5.5 h wall time (Jev 1.14.0).

## Totals

- New pairings: **37**; reused: 27.
- Money (API price): **$3.25**.
- API-equivalent of the subscription matches (not billed): $77.41.
- Match time: 23.3 h in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):
  - decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU): 14 min
  - decider.sh: Decider v1.1 27B (bariton): 10 min
  - gemma4-31b-replicas.sh: Gemma 4 31B (bariton): 4.0 h
  - glide-v12.sh: Fastino GLiDE v1.2 (bariton): 4 min
  - local server at 127.0.0.1:18091: 12 min
  - local server at 127.0.0.1:18093: 3 min
  - open-jev.sh: Open-Jev 27B v1.1 (bariton): 6 min
  - qwen38-27b.sh: Qwen3.8-27B (bariton): 6.6 h

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 3`: records the moves (league-remove with "ladder round 3: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. Block 1 (API and subscription): resume the leagues that hold those pairings (`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also holds GPU pairings starts them too: while their server is down they fail the warm-up and back off (2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are all GPU pairings is resumed with its first GPU block.
3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers (`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the servers and release the GPUs.
4. When every pairing is played, the next `tools/ladder.py plan` writes round 4's request (or the steady state).

