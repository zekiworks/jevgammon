# Ladder round 4: log

Approved by Can; run as in `Ladder round 4 - request.md`, under the ladder rules of 2026-10-26. **Status: round 4 is finished** (Oct 26, 14:04 UTC): all 29 new pairings played (#704-732), 35 reused. The early start for round 5 (Celeris-1 Decision) is finished too (hidden league #5, 15:25 UTC).

## Rule change (Can, 2026-10-26)

- The lock rule and its exception are dropped. The ladder ends at the first round that would need no new matches. A setup still oscillating then is placed in whichever of its two leagues is closer to its original league (its league before any ladder move); the rest stay. Programs never move.
- Recorded as a dated amendment in `backgammon-ladder-cup.md` (old text kept, marked superseded). Implemented in `tools/ladder.py` (commit 4a52ab0):
  - `round_moves`: no lock.
  - End check: every pair the moves create is already stored.
  - `final_placement`: origins from `league_web.league_origins`.
  - Reason "final placement" in the history and in `apply`.
  - Request sections "End check" / "Ladder ended".
- Tests: `tools/test_ladder.py`. The end branch was also exercised on the real state with every pair faked as stored. README updated.
- The round-4 plan re-run under the new rules gave the same moves: Clef L1→L2, DeepSeek V4.1 Flash (off) L2→L1, Gemini 4 Argon (off) L2→L3, Gemini 3.8 Flash (low) L3→L2.

## Timeline (UTC, Oct 26)

- 08:59: `apply --db v3.db --round 4`. Clef joined League 2 with 13 new matches, Flash (low) with 2, DeepSeek (off) League 1 with 14, Argon (off) League 3 with 0. `league1` and `league2` started (API pairings first). OpenRouter: $102.06 of $115 used.
- 09:00 (bus #105): GPU claim. Compactor held all four GPUs from 08:01; at 09:05 (bus #106) it released GPUs 0-2 and kept GPU 3.
- 09:07: Gemma 4 31B on GPU 0, Qwen3.8-27B on GPU 1, Clef on GPU 2; `league2` restarted.
- 09:10: Gemma and Qwen stopped again, so that League 1's GPU block could run on GPUs 0-1 without GPU 3. Clef was still playing its API opponents, so no Gemma or Qwen match was running yet.
  - GPU 0: Decider v1.2 27B + Flash and Winnow. GPU 1: Decider v1.1 and Cygnet.
  - Clef's Gemma and Qwen matches (#717-719) were deferred until 10:37 because of this.
- 10:17: those servers stopped; GLiDE v1.2 on GPU 0, Open-Jev on GPU 1.
- 10:33: League 1 finished; GLiDE and Open-Jev stopped. Gemma (GPU 0) and Qwen (GPU 1) back by 10:36; `league2` restarted at 10:37.
- 10:40-10:49: early start for round 5 (below). `league2` was paused 10:43-10:49: a runner refuses to resume a league while a match between its members has moved in the last 5 minutes, and #717/#719 are matches between members of league #5.
- 14:02: Gemma done; GPU 0 released on the bus.
- 14:04: League 2 finished (last: #719 Qwen3.8-27B (on) 5-1 Clef); Clef stopped, GPU 2 released.
- 15:25: league #5 finished; Qwen stopped, GPU 1 released. `score.sh v3.db ~/.local/state/bg-site/plays` (no copy): 5 decisions newly scored.
- No GPU fault this round. Disk: 49 GB free at 09:00; 610 GB free by 11:50 (cleanup by others).

## Early start for round 5, approved by Can

- Trial plan on the tables of 10:40 (League 1 finished, so certain): Celeris-1 Decision is League 1's top setup (38 pts; GNUbg weak, a program, ranks above) and moves up in round 5.
- Hidden league #5 (`only_pairs_of` = Celeris-1 Decision, `hidden`; League 2's seed, option-order seed and rules; config `leagues/league2-celeris-early.json`; unit `league2early`, `tools/v3/run_league2_early.sh "Celeris-1 Decision" leagues/league2-celeris-early.json`).
- Opponents: League 2's members of Oct 26, except Gemini 3.8 Flash (low) (skipped by Can). 5 pairs were stored and reused: GNUbg weak #262, Liquid d1-ultra #264, Fastino GLiDE #379, Jev 1.14.0 #266, Clef #253. 13 played (#733-745), 10:49-15:25 UTC. Celeris won 1 (#733 v DeepSeek V4.1 Flash 1017 (off) 6-3) and lost 12.
- Celeris v Gemini 4 Argon (off) was not in the early start (Argon was in League 3); round 5 plays it.
- The first start failed: `CELERIS_API_KEY` was not set. `run_league2_early.sh` now takes SETUP and CONFIG and reads the Jev/Fastino/Celeris key files as `run_league1.sh` does.

## Spend (turns.cost_usd at list price)

- Round 4 (#704-732): OpenRouter-billed about $3.56 (DeepSeek V4.1 Flash (on) $2.13, 1017 (on) $0.75, (off) $0.45, GLM-5.3 (on) $0.15, the rest cents); Jev, Luna, SubQ, Celeris, Mercury, Deciders a few cents. Subscriptions (API-equivalent, not billed): Claude Fable 5.1 (off) $8.53, Grok 4.7 (off) $2.60, Sonnet 5.5 (high) $2.18, Gemini 3.8 Flash (high) $2.12, the rest smaller.
- Early start (#733-745): OpenRouter-billed about $2.00 (DeepSeek V4.1 Flash (on) $1.19, 1017 (on) $0.60, the rest cents); Celeris $0.21. Subscriptions: Fable (off) $5.38, Flash (high) $2.96, Sonnet (high) $2.32, Grok (off) $2.12, Sonnet (low) $1.43.
- OpenRouter counter: $102.06 before, $107.66 after both (about $5.60, matching the list price).

## Next

- Round 5: `Ladder round 5 - request.md`, pre-approved by Can and run; see `Ladder round 5 - log.md`.
