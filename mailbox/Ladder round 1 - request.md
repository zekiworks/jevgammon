# Ladder round 1: request

Oct 23, 2026 20:45 UTC · computed by `tools/ladder.py plan` from `v3.db` (read-only). Nothing has started. Nothing runs until Can approves this round.

## Tables used

Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, decisions with two or more legal plays, invalid answers left out, as on the site). Programs never move.

- **League 1 (decision models)** (19 setups): 1. Liquid d1-ultra: 48 pts, games 67-35, error rate 30.0; 2. GNUbg weak (program): 48 pts, games 55-27, error rate 24.8; 3. Fastino GLiDE: 37 pts, games 57-41, error rate 37.1 … last: 19. Random (program): 0 pts, games 6-58, error rate 118.5; last setup that can move: 18. Decider Flash v1.2: 6 pts, games 28-64, error rate 58.2
- **League 2 (workhorses)** (17 setups): 1. GPT-6.1 Sol (low): 45 pts, games 61-27, error rate 10.8; 2. Gemma 4 31B (on): 36 pts, games 58-34, error rate 19.2; 3. GPT-6.1 Sol (high): 36 pts, games 52-30, error rate 11.1 … last: 17. LFM2.5-24B-A2B (off): 0 pts, games 10-52, error rate 63.0
- **League 3 (frontier models)** (11 setups): 1. GPT-6 Astra (on): 24 pts, games 33-23, error rate 12.5; 2. Claude Fable 5.1 (on): 21 pts, games 33-23, error rate 12.8; 3. Claude Opus 5.5 (on): 18 pts, games 37-27, error rate 14.3 … last: 11. Claude Fable 5.1 (off): 7 pts, games 32-36, error rate 17.8

## Moves

| Round | Setup | From | To | Reason |
| --- | --- | --- | --- | --- |
| 1 | Liquid d1-ultra | League 1 | League 2 | promoted |
| 1 | LFM2.5-24B-A2B (off) | League 2 | League 1 | relegated |
| 1 | GPT-6.1 Sol (low) | League 2 | League 3 | promoted |
| 1 | Claude Fable 5.1 (off) | League 3 | League 2 | relegated |


## Error-rate flag

A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site method, 2,000 resamples).

| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |
| --- | --- | --- | --- | --- | --- |
| League 1-League 2 | Liquid d1-ultra | 30.0 (95% interval 27.3-32.8; 2,143 decisions) | LFM2.5-24B-A2B (off) | 63.0 (95% interval 57.1-69.3; 1,302 decisions) | no |
| League 2-League 3 | GPT-6.1 Sol (low) | 10.8 (95% interval 9.3-12.4; 1,787 decisions) | Claude Fable 5.1 (off) | 17.8 (95% interval 15.5-20.2; 1,457 decisions) | no |

## Lineups after the round

- **League 1** (19 setups): joins LFM2.5-24B-A2B (off); leaves Liquid d1-ultra.
- **League 2** (17 setups): joins Liquid d1-ultra, Claude Fable 5.1 (off); leaves GPT-6.1 Sol (low), LFM2.5-24B-A2B (off).
- **League 3** (11 setups): joins GPT-6.1 Sol (low); leaves Claude Fable 5.1 (off).

## New pairings (55)

Each mover plays every setup of its new league it has not played anywhere (two newcomers of one league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); League 1's earlier matches stay as played (in sequence), as the page says.

Estimates from each setup's stored valid matches: decisions per match (the mean of the two setups), its mean seconds per decision, its cost per decision at its configured price. Duration = decisions x (seconds of both) x 0.56 (measured: wall time of a match with both games at once over its summed decision time, median of the stored matches). Money labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** (list price of the tokens, not billed), **own hardware** (no money; GPU time).

| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | League 2 | Claude Fable 5.1 (off) v Claude Sonnet 5.5 (high) | $0.00 | $11.66 | 16 min | none | claude-subscription |
| 2 | League 2 | Claude Fable 5.1 (off) v Claude Sonnet 5.5 (low) | $0.00 | $10.30 | 9 min | none | claude-subscription |
| 3 | League 2 | Claude Fable 5.1 (off) v DeepSeek V4.1 Flash (off) | $0.08 | $8.59 | 18 min | none | claude-subscription, openrouter:fireworks |
| 4 | League 2 | Claude Fable 5.1 (off) v DeepSeek V4.1 Flash (on) | $1.65 | $8.88 | 2.2 h | none | claude-subscription, openrouter:fireworks |
| 5 | League 2 | Claude Fable 5.1 (off) v GLM-5.3 (on) | $0.43 | $8.32 | 20 min | none | claude-subscription, openrouter:fireworks |
| 6 | League 2 | Claude Fable 5.1 (off) v GPT-6.1 Sol (high) | $0.00 | $10.25 | 24 min | none | chatgpt-subscription, claude-subscription |
| 7 | League 2 | Claude Fable 5.1 (off) v Gemini 3.8 Flash (high) | $0.00 | $12.20 | 34 min | none | antigravity-subscription, claude-subscription |
| 8 | League 2 | Claude Fable 5.1 (off) v Gemini 3.8 Flash (low) | $0.00 | $8.88 | 10 min | none | antigravity-subscription, claude-subscription |
| 9 | League 2 | Claude Fable 5.1 (off) v Qwen3.8 Flash (off) | $0.04 | $8.60 | 24 min | none | claude-subscription, openrouter:alibaba |
| 10 | League 2 | Liquid d1-ultra v Claude Fable 5.1 (off) | $0.02 | $8.80 | 5 min | none | claude-subscription, liquid |
| 11 | League 2 | Liquid d1-ultra v Claude Sonnet 5.5 (high) | $0.02 | $2.43 | 11 min | none | claude-subscription, liquid |
| 12 | League 2 | Liquid d1-ultra v Claude Sonnet 5.5 (low) | $0.02 | $1.56 | 4 min | none | claude-subscription, liquid |
| 13 | League 2 | Liquid d1-ultra v DeepSeek V4.1 Flash (off) | $0.09 | $0.00 | 13 min | none | liquid, openrouter:fireworks |
| 14 | League 2 | Liquid d1-ultra v DeepSeek V4.1 Flash (on) | $1.50 | $0.00 | 1.9 h | none | liquid, openrouter:fireworks |
| 15 | League 2 | Liquid d1-ultra v GLM-5.3 (on) | $0.40 | $0.00 | 14 min | none | liquid, openrouter:fireworks |
| 16 | League 2 | Liquid d1-ultra v GPT-6.1 Sol (high) | $0.02 | $1.57 | 18 min | none | chatgpt-subscription, liquid |
| 17 | League 2 | Liquid d1-ultra v Gemini 3.8 Flash (high) | $0.02 | $2.83 | 27 min | none | antigravity-subscription, liquid |
| 18 | League 2 | Liquid d1-ultra v Gemini 3.8 Flash (low) | $0.02 | $0.46 | 5 min | none | antigravity-subscription, liquid |
| 19 | League 2 | Liquid d1-ultra v Qwen3.8 Flash (off) | $0.05 | $0.00 | 18 min | none | liquid, openrouter:alibaba |
| 20 | League 3 | GPT-6.1 Sol (low) v Claude Fable 5.1 (on) | $0.00 | $15.98 | 29 min | none | chatgpt-subscription, claude-subscription |
| 21 | League 3 | GPT-6.1 Sol (low) v Claude Opus 5.5 (off) | $0.00 | $4.54 | 13 min | none | chatgpt-subscription, claude-subscription |
| 22 | League 3 | GPT-6.1 Sol (low) v Claude Opus 5.5 (on) | $0.00 | $5.80 | 19 min | none | chatgpt-subscription, claude-subscription |
| 23 | League 3 | GPT-6.1 Sol (low) v GPT-6 Astra (off) | $0.00 | $7.33 | 15 min | none | chatgpt-subscription |
| 24 | League 3 | GPT-6.1 Sol (low) v GPT-6 Astra (on) | $0.00 | $7.22 | 15 min | none | chatgpt-subscription |
| 25 | League 3 | GPT-6.1 Sol (low) v Gemini 4 Argon (off) | $0.00 | $2.55 | 15 min | none | antigravity-subscription, chatgpt-subscription |
| 26 | League 3 | GPT-6.1 Sol (low) v Gemini 4 Argon (on) | $0.00 | $6.19 | 1.1 h | none | antigravity-subscription, chatgpt-subscription |
| 27 | League 3 | GPT-6.1 Sol (low) v Grok 4.7 (off) | $0.00 | $4.91 | 1.3 h | none | chatgpt-subscription, xai-subscription |
| 28 | League 3 | GPT-6.1 Sol (low) v Grok 4.7 (on) | $0.00 | $14.53 | 4.3 h | none | chatgpt-subscription, xai-subscription |
| 29 | League 1 | LFM2.5-24B-A2B (off) v Clef | $0.00 | $0.00 | 10 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); clef.sh on the DGX Spark at 192.168.1.127 | none |
| 30 | League 1 | LFM2.5-24B-A2B (off) v Cygnet (Gemma 4 12B) | $0.00 | $0.00 | 2 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); cygnet.sh on the DGX Spark at 192.168.1.127 | none |
| 31 | League 1 | LFM2.5-24B-A2B (off) v Decider Flash v1.2 | $0.00 | $0.00 | 2 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 32 | League 1 | LFM2.5-24B-A2B (off) v Decider v1.2 27B | $0.00 | $0.00 | 3 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 33 | League 1 | LFM2.5-24B-A2B (off) v Winnow-12B | $0.00 | $0.00 | 3 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU) | none |
| 34 | League 1 | LFM2.5-24B-A2B (off) v Decider v1.1 27B | $0.00 | $0.00 | 8 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); decider.sh: Decider v1.1 27B (bariton) | none |
| 35 | League 1 | LFM2.5-24B-A2B (off) v Fastino GLiDE v1.2 (local) | $0.00 | $0.00 | 2 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton) | none |
| 36 | League 1 | LFM2.5-24B-A2B (off) v Celeris-1 Decision | $0.01 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | celeris |
| 37 | League 1 | LFM2.5-24B-A2B (off) v Fastino GLiDE | $0.00 + unknown (Fastino GLiDE: no price recorded) | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | fastino |
| 38 | League 1 | LFM2.5-24B-A2B (off) v GPT-6 Luna | $0.03 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | openai-decisions |
| 39 | League 1 | LFM2.5-24B-A2B (off) v Jev 1.13.0 | $0.02 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | jev |
| 40 | League 1 | LFM2.5-24B-A2B (off) v Jev 1.14.0 | $0.02 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | jev |
| 41 | League 1 | LFM2.5-24B-A2B (off) v Mercury Decide | $0.01 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | openrouter (inception) |
| 42 | League 1 | LFM2.5-24B-A2B (off) v Random | $0.00 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | none |
| 43 | League 1 | LFM2.5-24B-A2B (off) v Safest | $0.00 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | none |
| 44 | League 1 | LFM2.5-24B-A2B (off) v SubQ Snap Preview | $0.02 | $0.00 | under 1 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | subq |
| 45 | League 1 | LFM2.5-24B-A2B (off) v Open-Jev 27B v1.1 | $0.00 | $0.00 | 4 min | lfm25-24b.sh: LFM2.5-24B-A2B (bariton); open-jev.sh: Open-Jev 27B v1.1 (bariton) | none |
| 46 | League 2 | Claude Fable 5.1 (off) v Gemma 4 31B (off) | $0.00 | $8.12 | 9 min | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | claude-subscription |
| 47 | League 2 | Claude Fable 5.1 (off) v Gemma 4 31B (on) | $0.00 | $8.83 | 5.2 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | claude-subscription |
| 48 | League 2 | Liquid d1-ultra v Gemma 4 31B (off) | $0.02 | $0.00 | 5 min | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | liquid |
| 49 | League 2 | Liquid d1-ultra v Gemma 4 31B (on) | $0.02 | $0.00 | 4.6 h | gemma4-31b-replicas.sh: Gemma 4 31B (bariton) | liquid |
| 50 | League 2 | Claude Fable 5.1 (off) v LFM2.5-24B-A2B (on) | $0.00 | $8.37 | 10.0 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | claude-subscription |
| 51 | League 2 | Liquid d1-ultra v LFM2.5-24B-A2B (on) | $0.02 | $0.00 | 8.9 h | lfm25-24b.sh: LFM2.5-24B-A2B (bariton) | liquid |
| 52 | League 2 | Claude Fable 5.1 (off) v Qwen3.8-27B (off) | $0.00 | $8.27 | 7 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | claude-subscription |
| 53 | League 2 | Claude Fable 5.1 (off) v Qwen3.8-27B (on) | $0.00 | $8.38 | 7.2 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | claude-subscription |
| 54 | League 2 | Liquid d1-ultra v Qwen3.8-27B (off) | $0.02 | $0.00 | 3 min | qwen38-27b.sh: Qwen3.8-27B (bariton) | liquid |
| 55 | League 2 | Liquid d1-ultra v Qwen3.8-27B (on) | $0.02 | $0.00 | 6.4 h | qwen38-27b.sh: Qwen3.8-27B (bariton) | liquid |

## Reused pairings (4)

Already played (valid match), so not played again; the stored result counts in the new league's table.

| League | Pairing | Stored match | Played in | Result |
| --- | --- | --- | --- | --- |
| League 2 | Liquid d1-ultra v GNUbg weak | #192 (2026-10-19) | League 1 | Liquid d1-ultra 5-6 GNUbg weak |
| League 1 | LFM2.5-24B-A2B (off) v GNUbg weak | #338 (2026-10-19) | League 2 | LFM2.5-24B-A2B (off) 0-5 GNUbg weak |
| League 3 | GPT-6.1 Sol (low) v GNUbg weak | #110 (2026-10-19) | League 2 | GPT-6.1 Sol (low) 5-4 GNUbg weak |
| League 2 | Claude Fable 5.1 (off) v GNUbg weak | #453 (2026-10-20) | League 3 | Claude Fable 5.1 (off) 3-6 GNUbg weak |

## Scheduling order

API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one set of servers (at most 4 bariton GPUs), so GPU time can be arranged with compactor block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless set) and is rough: the slowest match of a block sets its end.

1. **API and subscription (no GPU)**: pairings 1-28 (28); needs no GPU; 17.1 h of match time, about 4.3 h wall time (Claude Fable 5.1 (off), GPT-6.1 Sol (low), Liquid d1-ultra).
2. **League 1 GPU block 1**: pairings 29-44 (16); needs 4 bariton GPU(s); clef.sh on the DGX Spark at 192.168.1.127; cygnet.sh on the DGX Spark at 192.168.1.127; decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU); decider.sh: Decider v1.1 27B (bariton); glide-v12.sh: Fastino GLiDE v1.2 (bariton); lfm25-24b.sh: LFM2.5-24B-A2B (bariton); 34 min of match time, about 10 min wall time (LFM2.5-24B-A2B (off)).
3. **League 1 GPU block 2**: pairings 45-45 (1); needs 2 bariton GPU(s); lfm25-24b.sh: LFM2.5-24B-A2B (bariton); open-jev.sh: Open-Jev 27B v1.1 (bariton); 4 min of match time, about 4 min wall time (LFM2.5-24B-A2B (off)).
4. **League 2 GPU block**: pairings 46-55 (10); needs 3 bariton GPU(s); gemma4-31b-replicas.sh: Gemma 4 31B (bariton); lfm25-24b.sh: LFM2.5-24B-A2B (bariton); qwen38-27b.sh: Qwen3.8-27B (bariton); 42.8 h of match time, about 10.0 h wall time (Claude Fable 5.1 (off), Liquid d1-ultra).

## Totals

- New pairings: **55**; reused: 4.
- Money (API price): **$4.53**, plus Fastino GLiDE (no price recorded).
- API-equivalent of the subscription matches (not billed): $216.34.
- Match time: 60.6 h in total.
- Own hardware, match time per server (summed over its matches; matches of one server overlap):
  - clef.sh on the DGX Spark at 192.168.1.127: 10 min
  - cygnet.sh on the DGX Spark at 192.168.1.127: 2 min
  - decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU): 8 min
  - decider.sh: Decider v1.1 27B (bariton): 8 min
  - gemma4-31b-replicas.sh: Gemma 4 31B (bariton): 10.1 h
  - glide-v12.sh: Fastino GLiDE v1.2 (bariton): 2 min
  - lfm25-24b.sh: LFM2.5-24B-A2B (bariton): 19.6 h
  - open-jev.sh: Open-Jev 27B v1.1 (bariton): 4 min
  - qwen38-27b.sh: Qwen3.8-27B (bariton): 13.8 h

## On approval

1. `python3 tools/ladder.py apply --db v3.db --round 1`: records the moves (league-remove with "ladder round 1: <reason> to league M", then league-add with the setup's stored settings) and sets the leagues that receive a mover to play both games of a round at the same time.
2. Block 1 (API and subscription): resume the leagues that hold those pairings (`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also holds GPU pairings starts them too: while their server is down they fail the warm-up and back off (2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are all GPU pairings is resumed with its first GPU block.
3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers (`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the servers and release the GPUs.
4. When every pairing is played, the next `tools/ladder.py plan` writes round 2's request (or the steady state).

## Notes

- **What to approve:** the 4 moves and the 55 new pairings above: $4.53 in API money, plus Fastino GLiDE, whose config records no price, so its cost is unknown. The subscription matches cost no money; their list-price equivalent is $216.34. The GPU blocks start only after compactor releases bariton's GPUs; Block 1 needs no GPU.
- **No error-rate flags.** Both promoted setups have a clearly lower error rate than the setup they replace: 30.0 against 63.0, and 10.8 against 17.8. In both swaps the two intervals do not overlap.
- **League 1's winner.** Liquid d1-ultra and GNUbg weak both have 48 points. Liquid d1-ultra ranks first on games won (67 against 55), so the error rate (24.8 for GNUbg weak) does not decide this place. Our reply was wrong about this; see `Participants migration - check.md`. GNUbg weak is a program and would not move anyway.
- **Reused results.** All 4 reused pairings are against GNUbg weak, which plays in all three leagues. Each counts once, in the mover's new league.
- **League 1 format.** `apply` switches League 1 to both games of a round at the same time for its new matches (LFM2.5-24B-A2B (off)'s 17). Its 171 earlier matches stay as they were played, one game after the other.
- **Estimates.** These are averages from each setup's stored matches. Reasoning-on setups that we host ourselves, such as Gemma 4 31B (on), LFM2.5-24B-A2B (on) and Qwen3.8-27B (on), take hours per match, and they dominate GPU time: the League 2 block is about 10 hours. Durations assume the servers run as they did in League 2. They are not a schedule.
- **Hype Cup ties (decided with Can after our reply).** A level Cup match, stored or new, goes to the setup with the lower error rate in that match. No extra rounds are played. This replaces "decisive mode" in our reply (`tools/ladder.py cup-winner`).
