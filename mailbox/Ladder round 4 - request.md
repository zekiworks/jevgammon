# Ladder round 4: request

Oct 26, 2026 08:59 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

**Approved by Can (Oct 26), under the ladder rules of 2026-10-26** (`backgammon-ladder-cup.md`, amendment): no lock (models move every round, repeats allowed); the ladder ends at the first round that would need no new matches, and a setup still oscillating then is placed in whichever of its two leagues is closer to its original league. The moves are the same as under the old rules (no round-4 mover was locked). The lock-rule check of the earlier version of this request no longer applies. With no lock, Gemini 4 Argon (off) and Gemini 3.8 Flash (low) can keep swapping between League 2 and League 3. Once every pair such a swap creates is stored, the ladder ends and the placement rule settles them.

## End check

Round 4's moves create 29 new pairing(s), so the ladder goes on (it ends at the first round whose moves would create no new pairing).

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. GNUbg weak (program): 48 pts, games 55-23, error rate 25.5; 2. Clef: 41 pts, games 55-37, error rate 38.1; 3. SubQ Snap Preview: 37 pts, games 67-37, error rate 44.2 … last: 19. Random (program): 0 pts, games 6-58, error rate 118.9; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 32-66, error rate 59.6
- **League 2 (workhorses)** (19 setups): 1. Gemini 4 Argon (off): 40 pts, games 59-45, error rate 15.8; 2. Claude Sonnet 5.5 (low): 39 pts, games 66-40, error rate 19.8; 3. Gemma 4 31B (on): 39 pts, games 64-42, error rate 19.3 … last: 19. DeepSeek V4.1 Flash (off): 10 pts, games 38-68, error rate 32.5
- **League 3 (frontier models)** (12 setups): 1. GPT-6.1 Sol (low): 27 pts, games 41-25, error rate 11.5; 2. GPT-6 Astra (on): 24 pts, games 35-27, error rate 11.5; 3. GPT-6.1 Sol (high): 21 pts, games 38-24, error rate 10.7 … last: 12. GNUbg weak (program): 8 pts, games 23-39, error rate 25.5; last setup that can move: 11. Gemini 3.8 Flash (low): 12 pts, games 25-33, error rate 17.4

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 4 | Clef | League 1 | League 2 | promoted |
| 4 | DeepSeek V4.1 Flash (off) | League 2 | League 1 | relegated |
| 4 | Gemini 4 Argon (off) | League 2 | League 3 | promoted |
| 4 | Gemini 3.8 Flash (low) | League 3 | League 2 | relegated |

- League 1: GNUbg weak ranks above Clef but is a program and never moves; the next setup is taken.
- League 3: GNUbg weak ranks below Gemini 3.8 Flash (low) but is a program and never moves; the next setup is taken.

Earlier rounds:

- round 1: Liquid d1-ultra, League 1 to League 2, promoted
- round 1: LFM2.5-24B-A2B (off), League 2 to League 1, relegated
- round 1: GPT-6.1 Sol (low), League 2 to League 3, promoted
- round 1: Claude Fable 5.1 (off), League 3 to League 2, relegated
- round 2: Fastino GLiDE, League 1 to League 2, promoted
- round 2: LFM2.5-24B-A2B (on), League 2 to League 1, relegated
- round 2: GPT-6.1 Sol (high), League 2 to League 3, promoted
- round 2: Grok 4.7 (off), League 3 to League 2, relegated
- round 3: Jev 1.14.0, League 1 to League 2, promoted
- round 3: Qwen3.8-27B (off), League 2 to League 1, relegated
- round 3: Gemini 3.8 Flash (low), League 2 to League 3, promoted
- round 3: Gemini 4 Argon (off), League 3 to League 2, relegated

## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Clef | 38.1 (95% interval 34.8-41.5; 2,328 decisions) | DeepSeek V4.1 Flash (off) | 32.5 (95% interval 30.2-35.2; 2,666 decisions) | **flagged: worse than the setup it replaces** |
| League 2-League 3 | Gemini 4 Argon (off) | 15.8 (95% interval 14.2-17.6; 3,575 decisions) | Gemini 3.8 Flash (low) | 17.4 (95% interval 15.8-19.0; 3,397 decisions) | no |

## Lineups after the round

- **League 1** (19 setups): joins DeepSeek V4.1 Flash (off); leaves Clef.
- **League 2** (19 setups): joins Clef, Gemini 3.8 Flash (low); leaves DeepSeek V4.1 Flash (off), Gemini 4 Argon (off).
- **League 3** (12 setups): joins Gemini 4 Argon (off); leaves Gemini 3.8 Flash (low).

## New pairings (29)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | League 1 | DeepSeek V4.1 Flash (off) v Celeris-1 Decision | $0.08 | $0.00 | 11 min | none | celeris, openrouter:fireworks |
| 2 | League 1 | DeepSeek V4.1 Flash (off) v GPT-6 Luna | $0.10 | $0.00 | 11 min | none | openai-decisions, openrouter:fireworks |
| 3 | League 1 | DeepSeek V4.1 Flash (off) v Jev 1.13.0 | $0.08 | $0.00 | 10 min | none | jev, openrouter:fireworks |
| 4 | League 1 | DeepSeek V4.1 Flash (off) v Mercury Decide | $0.07 | $0.00 | 11 min | none | openrouter (inception), openrouter:fireworks |
| 5 | League 1 | DeepSeek V4.1 Flash (off) v Random | $0.05 | $0.00 | 9 min | none | openrouter:fireworks |
| 6 | League 1 | DeepSeek V4.1 Flash (off) v Safest | $0.06 | $0.00 | 11 min | none | openrouter:fireworks |
| 7 | League 1 | DeepSeek V4.1 Flash (off) v SubQ Snap Preview | $0.09 | $0.00 | 11 min | none | openrouter:fireworks, subq |
| 8 | League 2 | Gemini 3.8 Flash (low) v Jev 1.14.0 | $0.02 | $0.45 | 4 min | none | antigravity-subscription, jev |
| 9 | League 1 | DeepSeek V4.1 Flash (off) v Decider Flash v1.2 | $0.06 | $0.00 | 12 min | decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | openrouter:fireworks |
| 10 | League 1 | DeepSeek V4.1 Flash (off) v Decider v1.2 27B | $0.06 | $0.00 | 14 min | decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | openrouter:fireworks |
| 11 | League 1 | DeepSeek V4.1 Flash (off) v Winnow-12B | $0.06 | $0.00 | 13 min | decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | openrouter:fireworks |
| 12 | League 1 | DeepSeek V4.1 Flash (off) v Decider v1.1 27B | $0.06 | $0.00 | 19 min | decider.sh: Decider v1.1 27B (bariton) | openrouter:fireworks |
| 13 | League 1 | DeepSeek V4.1 Flash (off) v Fastino GLiDE v1.2 (local) | $0.06 | $0.00 | 12 min | glide-v12.sh: Fastino GLiDE v1.2 (bariton) | openrouter:fireworks |
| 14 | League 1 | DeepSeek V4.1 Flash (off) v Cygnet (Gemma 4 12B) | $0.06 | $0.00 | 12 min | local server at 127.0.0.1:18093 | openrouter:fireworks |
| 15 | League 1 | DeepSeek V4.1 Flash (off) v Open-Jev 27B v1.1 | $0.06 | $0.00 | 15 min | open-jev.sh: Open-Jev 27B v1.1 (bariton) | openrouter:fireworks |
| 16 | League 2 | Clef v Gemma 4 31B (off) | $0.00 | $0.00 | 13 min | local server at 127.0.0.1:18091; gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | none |
| 17 | League 2 | Clef v Gemma 4 31B (on) | $0.00 | $0.00 | 4.1 h | local server at 127.0.0.1:18091; gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | none |
| 18 | League 2 | Clef v Claude Fable 5.1 (off) | $0.00 | $7.46 | 15 min | local server at 127.0.0.1:18091 | claude-subscription |
| 19 | League 2 | Clef v Claude Sonnet 5.5 (high) | $0.00 | $2.30 | 20 min | local server at 127.0.0.1:18091 | claude-subscription |
| 20 | League 2 | Clef v Claude Sonnet 5.5 (low) | $0.00 | $1.52 | 14 min | local server at 127.0.0.1:18091 | claude-subscription |
| 21 | League 2 | Clef v DeepSeek V4.1 Flash (on) | $1.49 | $0.00 | 1.7 h | local server at 127.0.0.1:18091 | openrouter:fireworks |
| 22 | League 2 | Clef v DeepSeek V4.1 Flash 1017 (off) | $0.03 | $0.00 | 36 min | local server at 127.0.0.1:18091 | openrouter:deepseek |
| 23 | League 2 | Clef v DeepSeek V4.1 Flash 1017 (on) | $0.56 | $0.00 | 1.2 h | local server at 127.0.0.1:18091 | openrouter:deepseek |
| 24 | League 2 | Clef v GLM-5.3 (on) | $0.33 | $0.00 | 21 min | local server at 127.0.0.1:18091 | openrouter:fireworks |
| 25 | League 2 | Clef v Gemini 3.8 Flash (high) | $0.00 | $2.65 | 33 min | local server at 127.0.0.1:18091 | antigravity-subscription |
| 26 | League 2 | Clef v Gemini 3.8 Flash (low) | $0.00 | $0.46 | 14 min | local server at 127.0.0.1:18091 | antigravity-subscription |
| 27 | League 2 | Clef v Grok 4.7 (off) | $0.00 | $3.74 | 1.3 h | local server at 127.0.0.1:18091 | xai-subscription |
| 28 | League 2 | Clef v Qwen3.8 Flash (off) | $0.03 | $0.00 | 24 min | local server at 127.0.0.1:18091 | openrouter:alibaba |
| 29 | League 2 | Clef v Qwen3.8-27B (on) | $0.00 | $0.00 | 5.7 h | local server at 127.0.0.1:18091; qwen38-27b.sh: Qwen3.8-27B (bariton) | none |

## Reused pairings (35)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Clef v GNUbg weak | #78 (2026-10-16) | League 1 | Clef 2-5 GNUbg weak |
| League 2 | Clef v Liquid d1-ultra | #180 (2026-10-19) | League 1 | Clef 1-5 Liquid d1-ultra |
| League 2 | Clef v Fastino GLiDE | #359 (2026-10-20) | League 1 | Fastino GLiDE 6-1 Clef |
| League 2 | Clef v Jev 1.14.0 | #245 (2026-10-19) | League 1 | Clef 3-4 Jev 1.14.0 |
| League 1 | DeepSeek V4.1 Flash (off) v GNUbg weak | #100 (2026-10-19) | League 2 | DeepSeek V4.1 Flash (off) 1-5 GNUbg weak |
| League 1 | DeepSeek V4.1 Flash (off) v LFM2.5-24B-A2B (off) | #310 (2026-10-19) | League 2 | LFM2.5-24B-A2B (off) 0-6 DeepSeek V4.1 Flash (off) |
| League 1 | DeepSeek V4.1 Flash (off) v LFM2.5-24B-A2B (on) | #311 (2026-10-19) | League 2 | DeepSeek V4.1 Flash (off) 2-6 LFM2.5-24B-A2B (on) |
| League 1 | DeepSeek V4.1 Flash (off) v Qwen3.8-27B (off) | #400 (2026-10-20) | League 2 | DeepSeek V4.1 Flash (off) 8-0 Qwen3.8-27B (off) |
| League 3 | Gemini 4 Argon (off) v GPT-6 Astra (off) | #425 (2026-10-20) | League 3 | Gemini 4 Argon (off) 5-5 GPT-6 Astra (off) |
| League 3 | Gemini 4 Argon (off) v GPT-6 Astra (on) | #445 (2026-10-20) | League 3 | Gemini 4 Argon (off) 0-5 GPT-6 Astra (on) |
| League 3 | Gemini 4 Argon (off) v Claude Opus 5.5 (off) | #450 (2026-10-20) | League 3 | Claude Opus 5.5 (off) 4-2 Gemini 4 Argon (off) |
| League 3 | Gemini 4 Argon (off) v Claude Opus 5.5 (on) | #454 (2026-10-20) | League 3 | Claude Opus 5.5 (on) 3-5 Gemini 4 Argon (off) |
| League 3 | Gemini 4 Argon (off) v Claude Fable 5.1 (on) | #434 (2026-10-20) | League 3 | Claude Fable 5.1 (on) 5-6 Gemini 4 Argon (off) |
| League 3 | Gemini 4 Argon (off) v Gemini 4 Argon (on) | #432 (2026-10-20) | League 3 | Gemini 4 Argon (off) 2-4 Gemini 4 Argon (on) |
| League 3 | Gemini 4 Argon (off) v Grok 4.7 (on) | #478 (2026-10-21) | League 3 | Gemini 4 Argon (off) 1-5 Grok 4.7 (on) |
| League 3 | Gemini 4 Argon (off) v GNUbg weak | #437 (2026-10-20) | League 3 | GNUbg weak 3-4 Gemini 4 Argon (off) |
| League 3 | Gemini 4 Argon (off) v GPT-6.1 Sol (low) | #526 (2026-10-23) | League 3 | GPT-6.1 Sol (low) 4-3 Gemini 4 Argon (off) |
| League 3 | Gemini 4 Argon (off) v GPT-6.1 Sol (high) | #578 (2026-10-24) | League 3 | Gemini 4 Argon (off) 2-5 GPT-6.1 Sol (high) |
| League 3 | Gemini 4 Argon (off) v Kimi K3.1 Pro (off) | #615 (2026-10-24) | League 3 | Kimi K3.1 Pro (off) 5-2 Gemini 4 Argon (off) |
| League 2 | Gemini 3.8 Flash (low) v Gemini 3.8 Flash (high) | #137 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 2-4 Gemini 3.8 Flash (high) |
| League 2 | Gemini 3.8 Flash (low) v Claude Sonnet 5.5 (low) | #128 (2026-10-19) | League 2 | Claude Sonnet 5.5 (low) 4-4 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Claude Sonnet 5.5 (high) | #123 (2026-10-19) | League 2 | Claude Sonnet 5.5 (high) 2-5 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v DeepSeek V4.1 Flash (on) | #120 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 6-2 DeepSeek V4.1 Flash (on) |
| League 2 | Gemini 3.8 Flash (low) v GLM-5.3 (on) | #125 (2026-10-19) | League 2 | GLM-5.3 (on) 1-5 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v GNUbg weak | #129 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 8-0 GNUbg weak |
| League 2 | Gemini 3.8 Flash (low) v Qwen3.8 Flash (off) | #315 (2026-10-19) | League 2 | Qwen3.8 Flash (off) 1-6 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Gemma 4 31B (on) | #214 (2026-10-19) | League 2 | Gemma 4 31B (on) 5-1 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Gemma 4 31B (off) | #203 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 7-3 Gemma 4 31B (off) |
| League 2 | Gemini 3.8 Flash (low) v Qwen3.8-27B (on) | #220 (2026-10-19) | League 2 | Qwen3.8-27B (on) 3-5 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Liquid d1-ultra | #503 (2026-10-23) | League 2 | Gemini 3.8 Flash (low) 5-2 Liquid d1-ultra |
| League 2 | Gemini 3.8 Flash (low) v Claude Fable 5.1 (off) | #504 (2026-10-23) | League 2 | Claude Fable 5.1 (off) 1-5 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Fastino GLiDE | #560 (2026-10-24) | League 2 | Fastino GLiDE 3-5 Gemini 3.8 Flash (low) |
| League 2 | Gemini 3.8 Flash (low) v Grok 4.7 (off) | #559 (2026-10-24) | League 2 | Gemini 3.8 Flash (low) 5-2 Grok 4.7 (off) |
| League 2 | Gemini 3.8 Flash (low) v DeepSeek V4.1 Flash 1017 (off) | #608 (2026-10-24) | League 2 | Gemini 3.8 Flash (low) 5-3 DeepSeek V4.1 Flash 1017 (off) |
| League 2 | Gemini 3.8 Flash (low) v DeepSeek V4.1 Flash 1017 (on) | #611 (2026-10-24) | League 2 | Gemini 3.8 Flash (low) 5-5 DeepSeek V4.1 Flash 1017 (on) |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.

1. **API and subscription (no GPU)**: pairings 1-8 (8); needs no GPU; 1.3 h of match time, about 11 min wall time (DeepSeek V4.1 Flash (off), Gemini 3.8 Flash (low)).
2. **League 1 GPU block 1**: pairings 9-14 (6); needs 4 bariton GPU(s); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU); decider.sh: Decider v1.1 27B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton); local server at 127.0.0.1:18093; 1.4 h of match time, about 20 min wall time (DeepSeek V4.1 Flash (off)).
3. **League 1 GPU block 2**: pairings 15-15 (1); needs 1 bariton GPU(s); open-jev.sh: Open-Jev 27B v1.1 (bariton); 15 min of match time, about 15 min wall time (DeepSeek V4.1 Flash (off)).
4. **League 2 GPU block**: pairings 16-29 (14); needs 3 bariton GPU(s); gemma4-31b-replicas.sh: Gemma 4 31B (bariton); local server at 127.0.0.1:18091; qwen38-27b.sh: Qwen3.8-27B (bariton); 17.1 h of match time, about 5.7 h wall time (Clef).

## Totals

- New pairings: **29**; reused: 35.
- Money (API price): **$3.43**.
- API-equivalent of the subscription matches (not billed): $18.57.
- Match time: 20.0 h in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):
  - decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU): 39 min
  - decider.sh: Decider v1.1 27B (bariton): 19 min
  - gemma4-31b-replicas.sh: Gemma 4 31B (bariton): 4.3 h
  - glide-v12.sh: Fastino GLiDE v1.2 (bariton): 12 min
  - local server at 127.0.0.1:18091: 17.1 h
  - local server at 127.0.0.1:18093: 12 min
  - open-jev.sh: Open-Jev 27B v1.1 (bariton): 15 min
  - qwen38-27b.sh: Qwen3.8-27B (bariton): 5.7 h

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 4`: records the moves (league-remove with "ladder round 4: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. Block 1 (API and subscription): resume the leagues that hold those pairings (`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also holds GPU pairings starts them too: while their server is down they fail the warm-up and back off (2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are all GPU pairings is resumed with its first GPU block.
3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers (`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the servers and release the GPUs.
4. When every pairing is played, the next `tools/ladder.py plan` writes round 5's request (or the ladder's end and final placement).

