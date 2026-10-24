# Ladder round 2: request

Oct 24, 2026 12:44 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. GNUbg weak (program): 48 pts, games 54-24, error rate 24.8; 2. Fastino GLiDE: 40 pts, games 58-38, error rate 36.7; 3. Jev 1.14.0: 39 pts, games 57-37, error rate 36.1 … last: 19. Random (program): 0 pts, games 7-59, error rate 118.0; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 28-64, error rate 58.9
- **League 2 (workhorses)** (17 setups): 1. GPT-6.1 Sol (high): 39 pts, games 56-28, error rate 11.5; 2. Gemini 3.8 Flash (low): 37 pts, games 54-32, error rate 16.8; 3. Gemma 4 31B (on): 36 pts, games 58-32, error rate 19.2 … last: 17. LFM2.5-24B-A2B (on): 3 pts, games 19-61, error rate 46.5
- **League 3 (frontier models)** (11 setups): 1. GPT-6.1 Sol (low): 24 pts, games 37-23, error rate 11.4; 2. GPT-6 Astra (on): 24 pts, games 34-22, error rate 12.2; 3. Claude Opus 5.5 (on): 18 pts, games 37-27, error rate 14.0 … last: 11. GNUbg weak (program): 5 pts, games 25-37, error rate 24.8; last setup that can move: 10. Grok 4.7 (off): 6 pts, games 23-35, error rate 19.0

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 2 | Fastino GLiDE | League 1 | League 2 | promoted |
| 2 | LFM2.5-24B-A2B (on) | League 2 | League 1 | relegated |
| 2 | GPT-6.1 Sol (high) | League 2 | League 3 | promoted |
| 2 | Grok 4.7 (off) | League 3 | League 2 | relegated |

- League 1: GNUbg weak ranks above Fastino GLiDE but is a program and never moves; the next setup is taken.
- League 3: GNUbg weak ranks below Grok 4.7 (off) but is a program and never moves; the next setup is taken.

Earlier rounds:

- round 1: Liquid d1-ultra, League 1 to League 2, promoted
- round 1: LFM2.5-24B-A2B (off), League 2 to League 1, relegated
- round 1: GPT-6.1 Sol (low), League 2 to League 3, promoted
- round 1: Claude Fable 5.1 (off), League 3 to League 2, relegated

## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Fastino GLiDE | 36.7 (95% interval 33.2-40.1; 2,193 decisions) | LFM2.5-24B-A2B (on) | 46.5 (95% interval 42.7-50.5; 1,893 decisions) | no |
| League 2-League 3 | GPT-6.1 Sol (high) | 11.5 (95% interval 10.1-12.9; 1,964 decisions) | Grok 4.7 (off) | 19.0 (95% interval 16.5-21.7; 1,320 decisions) | no |

## Lineups after the round

- **League 1** (19 setups): joins LFM2.5-24B-A2B (on); leaves Fastino GLiDE.
- **League 2** (17 setups): joins Fastino GLiDE, Grok 4.7 (off); leaves GPT-6.1 Sol (high), LFM2.5-24B-A2B (on).
- **League 3** (11 setups): joins GPT-6.1 Sol (high); leaves Grok 4.7 (off).

## New pairings (51)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | League 2 | Fastino GLiDE v Claude Fable 5.1 (off) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $7.83 | 5 min | none | claude-subscription, fastino |
| 2 | League 2 | Fastino GLiDE v Claude Sonnet 5.5 (high) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $2.38 | 10 min | none | claude-subscription, fastino |
| 3 | League 2 | Fastino GLiDE v Claude Sonnet 5.5 (low) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $1.52 | 4 min | none | claude-subscription, fastino |
| 4 | League 2 | Fastino GLiDE v DeepSeek V4.1 Flash (off) | $0.07 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 13 min | none | fastino, openrouter:fireworks |
| 5 | League 2 | Fastino GLiDE v DeepSeek V4.1 Flash (on) | $1.44 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 1.8 h | none | fastino, openrouter:fireworks |
| 6 | League 2 | Fastino GLiDE v GLM-5.3 (on) | $0.36 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 13 min | none | fastino, openrouter:fireworks |
| 7 | League 2 | Fastino GLiDE v Gemini 3.8 Flash (high) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $2.73 | 25 min | none | antigravity-subscription, fastino |
| 8 | League 2 | Fastino GLiDE v Gemini 3.8 Flash (low) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.46 | 5 min | none | antigravity-subscription, fastino |
| 9 | League 2 | Fastino GLiDE v Grok 4.7 (off) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $3.84 | 1.2 h | none | fastino, xai-subscription |
| 10 | League 2 | Fastino GLiDE v Qwen3.8 Flash (off) | $0.03 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 17 min | none | fastino, openrouter:alibaba |
| 11 | League 2 | Grok 4.7 (off) v Claude Sonnet 5.5 (high) | $0.00 | $6.38 | 1.4 h | none | claude-subscription, xai-subscription |
| 12 | League 2 | Grok 4.7 (off) v Claude Sonnet 5.5 (low) | $0.00 | $5.30 | 1.3 h | none | claude-subscription, xai-subscription |
| 13 | League 2 | Grok 4.7 (off) v DeepSeek V4.1 Flash (off) | $0.07 | $3.74 | 1.4 h | none | openrouter:fireworks, xai-subscription |
| 14 | League 2 | Grok 4.7 (off) v DeepSeek V4.1 Flash (on) | $1.47 | $3.91 | 3.1 h | none | openrouter:fireworks, xai-subscription |
| 15 | League 2 | Grok 4.7 (off) v GLM-5.3 (on) | $0.37 | $3.69 | 1.4 h | none | openrouter:fireworks, xai-subscription |
| 16 | League 2 | Grok 4.7 (off) v Gemini 3.8 Flash (high) | $0.00 | $6.75 | 1.7 h | none | antigravity-subscription, xai-subscription |
| 17 | League 2 | Grok 4.7 (off) v Gemini 3.8 Flash (low) | $0.00 | $4.20 | 1.3 h | none | antigravity-subscription, xai-subscription |
| 18 | League 2 | Grok 4.7 (off) v Liquid d1-ultra | $0.02 | $3.81 | 1.2 h | none | liquid, xai-subscription |
| 19 | League 2 | Grok 4.7 (off) v Qwen3.8 Flash (off) | $0.03 | $3.82 | 1.5 h | none | openrouter:alibaba, xai-subscription |
| 20 | League 3 | GPT-6.1 Sol (high) v Claude Fable 5.1 (on) | $0.00 | $16.24 | 39 min | none | chatgpt-subscription, claude-subscription |
| 21 | League 3 | GPT-6.1 Sol (high) v Claude Opus 5.5 (off) | $0.00 | $5.00 | 24 min | none | chatgpt-subscription, claude-subscription |
| 22 | League 3 | GPT-6.1 Sol (high) v Claude Opus 5.5 (on) | $0.00 | $6.22 | 30 min | none | chatgpt-subscription, claude-subscription |
| 23 | League 3 | GPT-6.1 Sol (high) v GPT-6 Astra (off) | $0.00 | $7.54 | 25 min | none | chatgpt-subscription |
| 24 | League 3 | GPT-6.1 Sol (high) v GPT-6 Astra (on) | $0.00 | $7.65 | 26 min | none | chatgpt-subscription |
| 25 | League 3 | GPT-6.1 Sol (high) v Gemini 4 Argon (off) | $0.00 | $2.96 | 26 min | none | antigravity-subscription, chatgpt-subscription |
| 26 | League 3 | GPT-6.1 Sol (high) v Gemini 4 Argon (on) | $0.00 | $6.55 | 1.3 h | none | antigravity-subscription, chatgpt-subscription |
| 27 | League 3 | GPT-6.1 Sol (high) v Grok 4.7 (on) | $0.00 | $14.82 | 4.5 h | none | chatgpt-subscription, xai-subscription |
| 28 | League 1 | LFM2.5-24B-A2B (on) v Decider Flash v1.2 | $0.00 | $0.00 | 7.8 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 29 | League 1 | LFM2.5-24B-A2B (on) v Decider v1.2 27B | $0.00 | $0.00 | 7.9 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 30 | League 1 | LFM2.5-24B-A2B (on) v Winnow-12B | $0.00 | $0.00 | 8.1 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 31 | League 1 | LFM2.5-24B-A2B (on) v Decider v1.1 27B | $0.00 | $0.00 | 8.1 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider.sh: Decider v1.1 27B (bariton) | none |
| 32 | League 1 | LFM2.5-24B-A2B (on) v Fastino GLiDE v1.2 (local) | $0.00 | $0.00 | 7.9 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton) | none |
| 33 | League 1 | LFM2.5-24B-A2B (on) v Celeris-1 Decision | $0.02 | $0.00 | 8.2 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | celeris |
| 34 | League 1 | LFM2.5-24B-A2B (on) v GPT-6 Luna | $0.04 | $0.00 | 7.9 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | openai-decisions |
| 35 | League 1 | LFM2.5-24B-A2B (on) v Jev 1.13.0 | $0.02 | $0.00 | 7.7 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | jev |
| 36 | League 1 | LFM2.5-24B-A2B (on) v Jev 1.14.0 | $0.02 | $0.00 | 8.0 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | jev |
| 37 | League 1 | LFM2.5-24B-A2B (on) v Mercury Decide | $0.01 | $0.00 | 7.6 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | openrouter (inception) |
| 38 | League 1 | LFM2.5-24B-A2B (on) v Random | $0.00 | $0.00 | 6.6 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | none |
| 39 | League 1 | LFM2.5-24B-A2B (on) v Safest | $0.00 | $0.00 | 8.2 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | none |
| 40 | League 1 | LFM2.5-24B-A2B (on) v SubQ Snap Preview | $0.02 | $0.00 | 8.3 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | subq |
| 41 | League 1 | LFM2.5-24B-A2B (on) v Clef | $0.00 | $0.00 | 8.1 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); local server at 127.0.0.1:18091 | none |
| 42 | League 1 | LFM2.5-24B-A2B (on) v Cygnet (Gemma 4 12B) | $0.00 | $0.00 | 8.0 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); local server at 127.0.0.1:18093 | none |
| 43 | League 1 | LFM2.5-24B-A2B (on) v Open-Jev 27B v1.1 | $0.00 | $0.00 | 8.2 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); open-jev.sh: Open-Jev 27B v1.1 (bariton) | none |
| 44 | League 2 | Fastino GLiDE v Gemma 4 31B (off) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 5 min | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | fastino |
| 45 | League 2 | Fastino GLiDE v Gemma 4 31B (on) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 4.3 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | fastino |
| 46 | League 2 | Grok 4.7 (off) v Gemma 4 31B (off) | $0.00 | $3.61 | 1.2 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | xai-subscription |
| 47 | League 2 | Grok 4.7 (off) v Gemma 4 31B (on) | $0.00 | $3.91 | 5.6 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | xai-subscription |
| 48 | League 2 | Fastino GLiDE v Qwen3.8-27B (off) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 3 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | fastino |
| 49 | League 2 | Fastino GLiDE v Qwen3.8-27B (on) | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.00 | 6.1 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | fastino |
| 50 | League 2 | Grok 4.7 (off) v Qwen3.8-27B (off) | $0.00 | $3.68 | 1.2 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | xai-subscription |
| 51 | League 2 | Grok 4.7 (off) v Qwen3.8-27B (on) | $0.00 | $3.76 | 7.4 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | xai-subscription |

## Reused pairings (8)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Fastino GLiDE v GNUbg weak | #374 (2026-10-20) | League 1 | GNUbg weak 5-1 Fastino GLiDE |
| League 2 | Fastino GLiDE v Liquid d1-ultra | #376 (2026-10-20) | League 1 | Liquid d1-ultra 5-3 Fastino GLiDE |
| League 1 | LFM2.5-24B-A2B (on) v GNUbg weak | #323 (2026-10-19) | League 2 | GNUbg weak 7-2 LFM2.5-24B-A2B (on) |
| League 1 | LFM2.5-24B-A2B (on) v LFM2.5-24B-A2B (off) | #324 (2026-10-19) | League 2 | LFM2.5-24B-A2B (on) 8-4 LFM2.5-24B-A2B (off) |
| League 3 | GPT-6.1 Sol (high) v GNUbg weak | #101 (2026-10-19) | League 2 | GNUbg weak 5-1 GPT-6.1 Sol (high) |
| League 3 | GPT-6.1 Sol (high) v GPT-6.1 Sol (low) | #126 (2026-10-19) | League 2 | GPT-6.1 Sol (low) 5-2 GPT-6.1 Sol (high) |
| League 2 | Grok 4.7 (off) v GNUbg weak | #444 (2026-10-20) | League 3 | GNUbg weak 2-5 Grok 4.7 (off) |
| League 2 | Grok 4.7 (off) v Claude Fable 5.1 (off) | #438 (2026-10-20) | League 3 | Claude Fable 5.1 (off) 2-4 Grok 4.7 (off) |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.

1. **API and subscription (no GPU)**: pairings 1-27 (27); needs no GPU; 27.3 h of match time, about 4.5 h wall time (Fastino GLiDE, GPT-6.1 Sol (high), Grok 4.7 (off)).
2. **League 1 GPU block 1**: pairings 28-40 (13); needs 4 bariton GPU(s); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU); decider.sh: Decider v1.1 27B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton); lfm25-24b.sh: LFM2.5-24B-A2B (bariton); 102.1 h of match time, about 8.3 h wall time (LFM2.5-24B-A2B (on)).
3. **League 1 GPU block 2**: pairings 41-43 (3); needs 4 bariton GPU(s); lfm25-24b.sh: LFM2.5-24B-A2B (bariton); local server at 127.0.0.1:18091; local server at 127.0.0.1:18093; open-jev.sh: Open-Jev 27B v1.1 (bariton); 24.3 h of match time, about 8.2 h wall time (LFM2.5-24B-A2B (on)).
4. **League 2 GPU block**: pairings 44-51 (8); needs 2 bariton GPU(s); gemma4-31b-replicas.sh: Gemma 4 31B (bariton); qwen38-27b.sh: Qwen3.8-27B (bariton); 26.0 h of match time, about 7.4 h wall time (Fastino GLiDE, Grok 4.7 (off)).

## Totals

- New pairings: **51**; reused: 8.
- Money (API price): **$3.99**, plus Fastino GLiDE (no price recorded).
- API-equivalent of the subscription matches (not billed): $142.28.
- Match time: 179.8 h in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):
  - decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU): 23.7 h
  - decider.sh: Decider v1.1 27B (bariton): 8.1 h
  - gemma4-31b-replicas.sh: Gemma 4 31B (bariton): 11.2 h
  - glide-v12.sh: Fastino GLiDE v1.2 (bariton): 7.9 h
  - lfm25-24b.sh: LFM2.5-24B-A2B (bariton): 126.5 h
  - local server at 127.0.0.1:18091: 8.1 h
  - local server at 127.0.0.1:18093: 8.0 h
  - open-jev.sh: Open-Jev 27B v1.1 (bariton): 8.2 h
  - qwen38-27b.sh: Qwen3.8-27B (bariton): 14.8 h

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 2`: records the moves (league-remove with "ladder round 2: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. Block 1 (API and subscription): resume the leagues that hold those pairings (`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also holds GPU pairings starts them too: while their server is down they fail the warm-up and back off (2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are all GPU pairings is resumed with its first GPU block.
3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers (`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the servers and release the GPUs.
4. When every pairing is played, the next `tools/ladder.py plan` writes round 3's request (or the steady state).

