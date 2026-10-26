# Ladder round 5: log

Pre-approved by Can (moves had to match the trial plan, and they did); run as in `Ladder round 5 - request.md`, rules of 2026-10-26. **Status (Oct 26, 15:47 UTC): round 5 is finished**: 2 new pairings played (#746, #747), 62 reused (incl. Celeris-1 Decision's 13 early-start matches #733-745). **The ladder has ended**: round 6 needed no new matches, and its swap was applied as the final swap (Can's rule; `Ladder ended - final placement.md`).

## Timeline (UTC, Oct 26)

- 15:25: plan = trial (Celeris-1 Decision L1→L2, Clef L2→L1, Gemini 3.8 Flash (low) L2→L3, Gemini 4 Argon (off) L3→L2); end check: 2 new pairings, so not ended.
- 15:25:56: `apply --db v3.db --round 5`. The 4 league-removes ran, then the first league-add (Celeris-1 Decision) failed: `CELERIS_API_KEY` was not in the environment (as `FASTINO_API_KEY` in round 2). I ran the 4 league-adds by hand with the key files loaded (same entries and freeze logs). Fixes:
  - `ladder.py apply` now reads the Jev/Fastino/Celeris key files when the environment has none.
  - `tools/v3/run_league2.sh` does the same (League 2's runner could not build Celeris's client either; `league2` restarted at ~15:28).
- 15:26: Clef on GPU 2 (free since 14:04; posted on the bus). #746 Clef 5-3 DeepSeek V4.1 Flash (off) (League 1), 15:26-15:37. Clef stopped and GPU 2 released at 15:38.
- 15:28-15:38: #747 Gemini 4 Argon (off) 5-1 Celeris-1 Decision (League 2).
- 15:39: `score.sh v3.db ~/.local/state/bg-site/plays` (no copy): 152 decisions newly scored. `ladder.py plan`: ladder ended (round 6, 0 new pairings).

## Spend

- List price: DeepSeek V4.1 Flash (off) $0.07 (OpenRouter), Celeris $0.02, Gemini 4 Argon (off) $1.25 (subscription, not billed). OpenRouter counter $107.66 to $107.73.

## End of the ladder: final swap (applied)

- Round 6 swaps Clef (League 1's top) with Celeris-1 Decision (League 2's last), and Gemini 4 Argon (off) (League 2's top) with Gemini 3.8 Flash (low) (League 3's last). Every pair those swaps make is stored.
- My first version placed the oscillating setups by original league; that would have kept Clef in League 1 and made the sizes 20/18/12. Can replaced that rule on Oct 26: the last swap is made one final time, and everyone stays where it puts them; setups added later start the next season. `tools/ladder.py`, its tests, the README and the amendment in `backgammon-ladder-cup.md` follow (the placement text kept, marked superseded).
- 15:46: `apply --db v3.db --round 6` (reason "final swap (ladder ended)"). Clef → League 2, Celeris-1 Decision → League 1, Argon (off) → League 3, Flash (low) → League 2; each join and leave reported 0 matches to play. The three runners were resumed once to close the leagues: no match created (none after #747); all three finished 15:46:30 with full fixtures (171/171, 171/171, 66/66) and new rankings. Sizes 19/19/12.
- Final tables (points, games, error rate):
  - League 1: 1. GNUbg weak (program) 48, 54-22, 25.5; 2. Celeris-1 Decision 38, 57-39, 33.1; 3. SubQ Snap Preview 37, 66-38, 43.9 … 17. Open-Jev 27B v1.1 7; 18. Decider Flash v1.2 6; 19. Random (program) 0.
  - League 2: 1. Gemini 3.8 Flash (low) 44, 63-39, 17.4; 2. Claude Sonnet 5.5 (low) 40, 65-41, 19.8; 3. Gemma 4 31B (on) 39, 62-42, 19.3 … 17. Jev 1.14.0 15; 18. Qwen3.8 Flash (off) 6; 19. Clef 6.
  - League 3: 1. GPT-6.1 Sol (low) 27, 41-25, 11.5; 2. GPT-6 Astra (on) 24, 36-26, 11.5; 3. GPT-6.1 Sol (high) 21, 38-26, 10.7 … 10. Kimi K3.1 Pro (off) 12; 11. Gemini 4 Argon (off) 10; 12. GNUbg weak (program) 8.
- Dashboard (`/api/state`): the four show in their new leagues, with their origin leagues for the # colours: Celeris 1 (in League 1); Clef 1 and Flash (low) 2 (in League 2); Argon (off) 3 (in League 3).
- Next: the Cup roster and the league rename, each with its own approval (not started).
