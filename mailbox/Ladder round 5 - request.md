# Ladder round 5: request

Oct 26, 2026 15:25 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

**Pre-approved by Can (Oct 26), provided the moves match the trial plan** (they do: Celeris-1 Decision L1→L2, Clef L2→L1, Gemini 3.8 Flash (low) L2→L3, Gemini 4 Argon (off) L3→L2). Celeris-1 Decision's League 2 matches were pre-played as an early start for round 5 (approved by Can) in hidden league #5, Oct 26 10:40-15:25 UTC: 13 matches (#733-745), reused below, not played again. Can skipped Celeris v Gemini 3.8 Flash (low) in that early start; after this round that pair is in different leagues. Rules of 2026-10-26 (no lock; end check).

## End check

Round 5's moves create 2 new pairing(s), so the ladder goes on (it ends at the first round whose moves would create no new pairing).

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. GNUbg weak (program): 48 pts, games 54-22, error rate 25.5; 2. Celeris-1 Decision: 38 pts, games 57-39, error rate 33.0; 3. SubQ Snap Preview: 37 pts, games 66-38, error rate 43.9 … last: 19. Random (program): 0 pts, games 6-58, error rate 119.4; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 33-65, error rate 59.9
- **League 2 (workhorses)** (19 setups): 1. Gemini 3.8 Flash (low): 44 pts, games 63-39, error rate 17.4; 2. Claude Sonnet 5.5 (low): 40 pts, games 65-41, error rate 19.8; 3. Gemma 4 31B (on): 39 pts, games 62-42, error rate 19.3 … last: 19. Clef: 6 pts, games 27-67, error rate 37.3
- **League 3 (frontier models)** (12 setups): 1. GPT-6.1 Sol (low): 27 pts, games 41-25, error rate 11.5; 2. GPT-6 Astra (on): 24 pts, games 36-26, error rate 11.5; 3. GPT-6.1 Sol (high): 21 pts, games 38-26, error rate 10.7 … last: 12. GNUbg weak (program): 8 pts, games 26-38, error rate 25.5; last setup that can move: 11. Gemini 4 Argon (off): 10 pts, games 27-43, error rate 15.8

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 5 | Celeris-1 Decision | League 1 | League 2 | promoted |
| 5 | Clef | League 2 | League 1 | relegated |
| 5 | Gemini 3.8 Flash (low) | League 2 | League 3 | promoted |
| 5 | Gemini 4 Argon (off) | League 3 | League 2 | relegated |

- League 1: GNUbg weak ranks above Celeris-1 Decision but is a program and never moves; the next setup is taken.
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
- round 3: Jev 1.14.0, League 1 to League 2, promoted
- round 3: Qwen3.8-27B (off), League 2 to League 1, relegated
- round 3: Gemini 3.8 Flash (low), League 2 to League 3, promoted
- round 3: Gemini 4 Argon (off), League 3 to League 2, relegated
- round 4: Clef, League 1 to League 2, promoted
- round 4: DeepSeek V4.1 Flash (off), League 2 to League 1, relegated
- round 4: Gemini 4 Argon (off), League 2 to League 3, promoted
- round 4: Gemini 3.8 Flash (low), League 3 to League 2, relegated

## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Celeris-1 Decision | 33.0 (95% interval 30.6-35.5; 3,937 decisions) | Clef | 37.3 (95% interval 34.7-39.7; 3,794 decisions) | no |
| League 2-League 3 | Gemini 3.8 Flash (low) | 17.4 (95% interval 16.0-18.9; 3,620 decisions) | Gemini 4 Argon (off) | 15.8 (95% interval 14.2-17.6; 3,575 decisions) | **flagged: worse than the setup it replaces** |

## Lineups after the round

- **League 1** (19 setups): joins Clef; leaves Celeris-1 Decision.
- **League 2** (19 setups): joins Celeris-1 Decision, Gemini 4 Argon (off); leaves Clef, Gemini 3.8 Flash (low).
- **League 3** (12 setups): joins Gemini 3.8 Flash (low); leaves Gemini 4 Argon (off).

## New pairings (2)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | League 2 | Celeris-1 Decision v Gemini 4 Argon (off) | $0.02 | $1.21 | 7 min | none | antigravity-subscription, celeris |
| 2 | League 1 | Clef v DeepSeek V4.1 Flash (off) | $0.05 | $0.00 | 20 min | local server at 127.0.0.1:18091 | openrouter:fireworks |

## Reused pairings (62)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Celeris-1 Decision v Gemini 3.8 Flash (high) | #739 (2026-10-26) | early start, hidden league #5 | Gemini 3.8 Flash (high) 5-1 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Claude Sonnet 5.5 (low) | #735 (2026-10-26) | early start, hidden league #5 | Celeris-1 Decision 1-5 Claude Sonnet 5.5 (low) |
| League 2 | Celeris-1 Decision v Claude Sonnet 5.5 (high) | #738 (2026-10-26) | early start, hidden league #5 | Claude Sonnet 5.5 (high) 4-3 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v DeepSeek V4.1 Flash (on) | #736 (2026-10-26) | early start, hidden league #5 | DeepSeek V4.1 Flash (on) 6-0 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v GLM-5.3 (on) | #734 (2026-10-26) | early start, hidden league #5 | GLM-5.3 (on) 6-1 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v GNUbg weak | #262 (2026-10-19) | League 1 | GNUbg weak 3-5 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Qwen3.8 Flash (off) | #737 (2026-10-26) | early start, hidden league #5 | Qwen3.8 Flash (off) 5-3 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Gemma 4 31B (on) | #743 (2026-10-26) | early start, hidden league #5 | Celeris-1 Decision 3-4 Gemma 4 31B (on) |
| League 2 | Celeris-1 Decision v Gemma 4 31B (off) | #742 (2026-10-26) | early start, hidden league #5 | Celeris-1 Decision 1-6 Gemma 4 31B (off) |
| League 2 | Celeris-1 Decision v Qwen3.8-27B (on) | #745 (2026-10-26) | early start, hidden league #5 | Qwen3.8-27B (on) 6-4 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Liquid d1-ultra | #264 (2026-10-19) | League 1 | Liquid d1-ultra 6-5 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Claude Fable 5.1 (off) | #741 (2026-10-26) | early start, hidden league #5 | Claude Fable 5.1 (off) 5-0 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Fastino GLiDE | #379 (2026-10-20) | League 1 | Fastino GLiDE 2-4 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Grok 4.7 (off) | #740 (2026-10-26) | early start, hidden league #5 | Grok 4.7 (off) 5-2 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v DeepSeek V4.1 Flash 1017 (off) | #733 (2026-10-26) | early start, hidden league #5 | Celeris-1 Decision 6-3 DeepSeek V4.1 Flash 1017 (off) |
| League 2 | Celeris-1 Decision v DeepSeek V4.1 Flash 1017 (on) | #744 (2026-10-26) | early start, hidden league #5 | DeepSeek V4.1 Flash 1017 (on) 8-0 Celeris-1 Decision |
| League 2 | Celeris-1 Decision v Jev 1.14.0 | #266 (2026-10-19) | League 1 | Celeris-1 Decision 2-5 Jev 1.14.0 |
| League 1 | Clef v Decider v1.1 27B | #56 (2026-10-15) | League 1 | Decider v1.1 27B 6-0 Clef |
| League 1 | Clef v SubQ Snap Preview | #22 (2026-10-15) | League 1 | Clef 5-3 SubQ Snap Preview |
| League 1 | Clef v Open-Jev 27B v1.1 | #65 (2026-10-15) | League 1 | Clef 5-5 Open-Jev 27B v1.1 |
| League 1 | Clef v Cygnet (Gemma 4 12B) | #55 (2026-10-15) | League 1 | Cygnet (Gemma 4 12B) 5-0 Clef |
| League 1 | Clef v Random | #10 (2026-10-15) | League 1 | Random 0-6 Clef |
| League 1 | Clef v Safest | #18 (2026-10-15) | League 1 | Clef 6-0 Safest |
| League 1 | Clef v GNUbg weak | #78 (2026-10-16) | League 1 | Clef 2-5 GNUbg weak |
| League 1 | Clef v Jev 1.13.0 | #250 (2026-10-19) | League 1 | Jev 1.13.0 2-6 Clef |
| League 1 | Clef v GPT-6 Luna | #248 (2026-10-19) | League 1 | GPT-6 Luna 3-4 Clef |
| League 1 | Clef v Decider Flash v1.2 | #298 (2026-10-19) | League 1 | Decider Flash v1.2 0-7 Clef |
| League 1 | Clef v Winnow-12B | #301 (2026-10-19) | League 1 | Clef 4-2 Winnow-12B |
| League 1 | Clef v Mercury Decide | #354 (2026-10-20) | League 1 | Mercury Decide 1-5 Clef |
| League 1 | Clef v Decider v1.2 27B | #392 (2026-10-20) | League 1 | Clef 5-1 Decider v1.2 27B |
| League 1 | Clef v Fastino GLiDE v1.2 (local) | #484 (2026-10-22) | League 1 | Fastino GLiDE v1.2 (local) 1-5 Clef |
| League 1 | Clef v LFM2.5-24B-A2B (off) | #533 (2026-10-23) | League 1 | LFM2.5-24B-A2B (off) 2-9 Clef |
| League 1 | Clef v LFM2.5-24B-A2B (on) | #596 (2026-10-24) | League 1 | LFM2.5-24B-A2B (on) 3-5 Clef |
| League 1 | Clef v Qwen3.8-27B (off) | #681 (2026-10-25) | League 1 | Qwen3.8-27B (off) 2-6 Clef |
| League 3 | Gemini 3.8 Flash (low) v GPT-6 Astra (off) | #669 (2026-10-25) | League 3 | GPT-6 Astra (off) 3-4 Gemini 3.8 Flash (low) |
| League 3 | Gemini 3.8 Flash (low) v GPT-6 Astra (on) | #671 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 1-5 GPT-6 Astra (on) |
| League 3 | Gemini 3.8 Flash (low) v Claude Opus 5.5 (off) | #670 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 0-6 Claude Opus 5.5 (off) |
| League 3 | Gemini 3.8 Flash (low) v Claude Opus 5.5 (on) | #668 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 4-3 Claude Opus 5.5 (on) |
| League 3 | Gemini 3.8 Flash (low) v Claude Fable 5.1 (on) | #677 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 3-4 Claude Fable 5.1 (on) |
| League 3 | Gemini 3.8 Flash (low) v Gemini 4 Argon (on) | #678 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 1-5 Gemini 4 Argon (on) |
| League 3 | Gemini 3.8 Flash (low) v Grok 4.7 (on) | #695 (2026-10-25) | League 3 | Grok 4.7 (on) 3-4 Gemini 3.8 Flash (low) |
| League 3 | Gemini 3.8 Flash (low) v GNUbg weak | #129 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 8-0 GNUbg weak |
| League 3 | Gemini 3.8 Flash (low) v GPT-6.1 Sol (low) | #130 (2026-10-19) | League 2 | GPT-6.1 Sol (low) 5-2 Gemini 3.8 Flash (low) |
| League 3 | Gemini 3.8 Flash (low) v GPT-6.1 Sol (high) | #135 (2026-10-19) | League 2 | Gemini 3.8 Flash (low) 0-5 GPT-6.1 Sol (high) |
| League 3 | Gemini 3.8 Flash (low) v Kimi K3.1 Pro (off) | #699 (2026-10-25) | League 3 | Gemini 3.8 Flash (low) 3-5 Kimi K3.1 Pro (off) |
| League 2 | Gemini 4 Argon (off) v Gemini 3.8 Flash (high) | #658 (2026-10-25) | early start, hidden league #4 | Gemini 3.8 Flash (high) 4-3 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Claude Sonnet 5.5 (low) | #652 (2026-10-25) | early start, hidden league #4 | Claude Sonnet 5.5 (low) 3-4 Gemini 4 Argon (off) |
| League 2 | Gemini 4 Argon (off) v Claude Sonnet 5.5 (high) | #657 (2026-10-25) | early start, hidden league #4 | Claude Sonnet 5.5 (high) 2-4 Gemini 4 Argon (off) |
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
| League 2 | Gemini 4 Argon (off) v Jev 1.14.0 | #659 (2026-10-25) | early start, hidden league #4 | Jev 1.14.0 1-6 Gemini 4 Argon (off) |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.

1. **API and subscription (no GPU)**: pairings 1-1 (1); needs no GPU; 7 min of match time, about 7 min wall time (Celeris-1 Decision).
2. **League 1 GPU block**: pairings 2-2 (1); needs 1 bariton GPU(s); local server at 127.0.0.1:18091; 20 min of match time, about 20 min wall time (Clef).

## Totals

- New pairings: **2**; reused: 62.
- Money (API price): **$0.07**.
- API-equivalent of the subscription matches (not billed): $1.21.
- Match time: 26 min in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):
  - local server at 127.0.0.1:18091: 20 min

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 5`: records the moves (league-remove with "ladder round 5: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. Block 1 (API and subscription): resume the leagues that hold those pairings (`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also holds GPU pairings starts them too: while their server is down they fail the warm-up and back off (2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are all GPU pairings is resumed with its first GPU block.
3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers (`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the servers and release the GPUs.
4. When every pairing is played, the next `tools/ladder.py plan` writes round 6's request (or the ladder's end and final placement).

