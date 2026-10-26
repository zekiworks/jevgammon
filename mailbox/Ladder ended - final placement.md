# Ladder ended: final swap (round 6)

Oct 26, 2026 15:45 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

**Approved by Can (Oct 26), under his rule of 2026-10-26 for the end of the ladder** (which replaces the original-league placement of the earlier version of this file): the last swap is made one final time, and everyone stays where it puts them. Clef goes to League 2, Celeris-1 Decision to League 1, Gemini 4 Argon (off) to League 3, Gemini 3.8 Flash (low) to League 2; sizes stay 19/19/12. No match is needed.

## Ladder ended

Round 6's moves would create no new pairing (every pair they make is already stored), so the ladder ends (rule of 2026-10-26): round 6's swap is made one final time (reason: final swap (ladder ended)) and every setup stays where it puts it. Setups added later start the next season, and the ladder continues from there.

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. GNUbg weak (program): 51 pts, games 57-21, error rate 25.5; 2. Clef: 43 pts, games 56-36, error rate 37.0; 3. Cygnet (Gemma 4 12B): 37 pts, games 60-38, error rate 38.0 … last: 19. Random (program): 0 pts, games 6-56, error rate 119.4; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 31-65, error rate 59.9
- **League 2 (workhorses)** (19 setups): 1. Gemini 4 Argon (off): 40 pts, games 60-46, error rate 15.9; 2. Claude Sonnet 5.5 (low): 39 pts, games 66-40, error rate 19.8; 3. DeepSeek V4.1 Flash 1017 (on): 39 pts, games 63-43, error rate 16.5 … last: 19. Celeris-1 Decision: 9 pts, games 34-66, error rate 33.1
- **League 3 (frontier models)** (12 setups): 1. GPT-6.1 Sol (low): 27 pts, games 41-25, error rate 11.5; 2. GPT-6 Astra (on): 24 pts, games 35-27, error rate 11.5; 3. GPT-6.1 Sol (high): 21 pts, games 38-24, error rate 10.7 … last: 12. GNUbg weak (program): 8 pts, games 23-39, error rate 25.5; last setup that can move: 11. Gemini 3.8 Flash (low): 12 pts, games 25-33, error rate 17.4

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 6 | Clef | League 1 | League 2 | final swap (ladder ended) |
| 6 | Celeris-1 Decision | League 2 | League 1 | final swap (ladder ended) |
| 6 | Gemini 4 Argon (off) | League 2 | League 3 | final swap (ladder ended) |
| 6 | Gemini 3.8 Flash (low) | League 3 | League 2 | final swap (ladder ended) |

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
- round 4: Clef, League 1 to League 2, promoted
- round 4: DeepSeek V4.1 Flash (off), League 2 to League 1, relegated
- round 4: Gemini 4 Argon (off), League 2 to League 3, promoted
- round 4: Gemini 3.8 Flash (low), League 3 to League 2, relegated
- round 5: Celeris-1 Decision, League 1 to League 2, promoted
- round 5: Clef, League 2 to League 1, relegated
- round 5: Gemini 3.8 Flash (low), League 2 to League 3, promoted
- round 5: Gemini 4 Argon (off), League 3 to League 2, relegated

## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Clef | 37.0 (95% interval 34.7-39.3; 3,970 decisions) | Celeris-1 Decision | 33.1 (95% interval 30.8-35.4; 4,044 decisions) | **flagged: worse than the setup it replaces** |
| League 2-League 3 | Gemini 4 Argon (off) | 15.9 (95% interval 14.2-17.6; 3,698 decisions) | Gemini 3.8 Flash (low) | 17.4 (95% interval 16.0-18.9; 3,620 decisions) | no |

## Lineups after the round

- **League 1** (19 setups): joins Celeris-1 Decision; leaves Clef.
- **League 2** (19 setups): joins Clef, Gemini 3.8 Flash (low); leaves Celeris-1 Decision, Gemini 4 Argon (off).
- **League 3** (12 setups): joins Gemini 4 Argon (off); leaves Gemini 3.8 Flash (low).

## New pairings (0)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Reused pairings (64)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Clef v Gemini 3.8 Flash (high) | #705 (2026-10-26) | League 2 | Clef 2-4 Gemini 3.8 Flash (high) |
| League 2 | Clef v Claude Sonnet 5.5 (low) | #707 (2026-10-26) | League 2 | Clef 2-6 Claude Sonnet 5.5 (low) |
| League 2 | Clef v Claude Sonnet 5.5 (high) | #704 (2026-10-26) | League 2 | Claude Sonnet 5.5 (high) 5-1 Clef |
| League 2 | Clef v DeepSeek V4.1 Flash (on) | #709 (2026-10-26) | League 2 | Clef 0-6 DeepSeek V4.1 Flash (on) |
| League 2 | Clef v GLM-5.3 (on) | #715 (2026-10-26) | League 2 | GLM-5.3 (on) 2-5 Clef |
| League 2 | Clef v GNUbg weak | #78 (2026-10-16) | League 1 | Clef 2-5 GNUbg weak |
| League 2 | Clef v Qwen3.8 Flash (off) | #716 (2026-10-26) | League 2 | Qwen3.8 Flash (off) 4-5 Clef |
| League 2 | Clef v Gemma 4 31B (on) | #717 (2026-10-26) | League 2 | Clef 4-6 Gemma 4 31B (on) |
| League 2 | Clef v Gemma 4 31B (off) | #718 (2026-10-26) | League 2 | Clef 0-5 Gemma 4 31B (off) |
| League 2 | Clef v Qwen3.8-27B (on) | #719 (2026-10-26) | League 2 | Qwen3.8-27B (on) 5-1 Clef |
| League 2 | Clef v Liquid d1-ultra | #180 (2026-10-19) | League 1 | Clef 1-5 Liquid d1-ultra |
| League 2 | Clef v Claude Fable 5.1 (off) | #721 (2026-10-26) | League 2 | Claude Fable 5.1 (off) 7-2 Clef |
| League 2 | Clef v Fastino GLiDE | #359 (2026-10-20) | League 1 | Fastino GLiDE 6-1 Clef |
| League 2 | Clef v Grok 4.7 (off) | #722 (2026-10-26) | League 2 | Grok 4.7 (off) 7-1 Clef |
| League 2 | Clef v DeepSeek V4.1 Flash 1017 (off) | #723 (2026-10-26) | League 2 | Clef 4-6 DeepSeek V4.1 Flash 1017 (off) |
| League 2 | Clef v DeepSeek V4.1 Flash 1017 (on) | #724 (2026-10-26) | League 2 | Clef 0-8 DeepSeek V4.1 Flash 1017 (on) |
| League 2 | Clef v Jev 1.14.0 | #245 (2026-10-19) | League 1 | Clef 3-4 Jev 1.14.0 |
| League 2 | Clef v Gemini 3.8 Flash (low) | #727 (2026-10-26) | League 2 | Clef 2-5 Gemini 3.8 Flash (low) |
| League 1 | Celeris-1 Decision v Decider v1.1 27B | #299 (2026-10-19) | League 1 | Celeris-1 Decision 3-4 Decider v1.1 27B |
| League 1 | Celeris-1 Decision v SubQ Snap Preview | #243 (2026-10-19) | League 1 | SubQ Snap Preview 4-4 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v Open-Jev 27B v1.1 | #242 (2026-10-19) | League 1 | Open-Jev 27B v1.1 1-5 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v Cygnet (Gemma 4 12B) | #271 (2026-10-19) | League 1 | Celeris-1 Decision 2-5 Cygnet (Gemma 4 12B) |
| League 1 | Celeris-1 Decision v Random | #259 (2026-10-19) | League 1 | Celeris-1 Decision 7-0 Random |
| League 1 | Celeris-1 Decision v Safest | #261 (2026-10-19) | League 1 | Safest 2-4 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v GNUbg weak | #262 (2026-10-19) | League 1 | GNUbg weak 3-5 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v Jev 1.13.0 | #288 (2026-10-19) | League 1 | Jev 1.13.0 2-5 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v GPT-6 Luna | #296 (2026-10-19) | League 1 | Celeris-1 Decision 6-3 GPT-6 Luna |
| League 1 | Celeris-1 Decision v Decider Flash v1.2 | #285 (2026-10-19) | League 1 | Celeris-1 Decision 5-3 Decider Flash v1.2 |
| League 1 | Celeris-1 Decision v Winnow-12B | #291 (2026-10-19) | League 1 | Celeris-1 Decision 5-3 Winnow-12B |
| League 1 | Celeris-1 Decision v Mercury Decide | #369 (2026-10-20) | League 1 | Celeris-1 Decision 5-5 Mercury Decide |
| League 1 | Celeris-1 Decision v Decider v1.2 27B | #417 (2026-10-20) | League 1 | Decider v1.2 27B 6-2 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v Fastino GLiDE v1.2 (local) | #493 (2026-10-22) | League 1 | Celeris-1 Decision 1-5 Fastino GLiDE v1.2 (local) |
| League 1 | Celeris-1 Decision v LFM2.5-24B-A2B (off) | #536 (2026-10-23) | League 1 | LFM2.5-24B-A2B (off) 1-5 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v LFM2.5-24B-A2B (on) | #593 (2026-10-24) | League 1 | LFM2.5-24B-A2B (on) 2-4 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v Qwen3.8-27B (off) | #690 (2026-10-25) | League 1 | Qwen3.8-27B (off) 0-5 Celeris-1 Decision |
| League 1 | Celeris-1 Decision v DeepSeek V4.1 Flash (off) | #725 (2026-10-26) | League 1 | Celeris-1 Decision 5-3 DeepSeek V4.1 Flash (off) |
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
| League 2 | Gemini 3.8 Flash (low) v Jev 1.14.0 | #711 (2026-10-26) | League 2 | Gemini 3.8 Flash (low) 5-0 Jev 1.14.0 |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.


## Totals

- New pairings: **0**; reused: 64.
- Money (API price): **$0.00**.
- API-equivalent of the subscription matches (not billed): $0.00.
- Match time: under 1 min in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 6`: records the moves (league-remove with "ladder round 6: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. No match is played: every pair of the final lineups is stored. The ladder is over; the Hype Cup can be prepared from the final tables.

