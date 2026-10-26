# Ladder round 5: log

Pre-approved by Can (moves had to match the trial plan, and they did); run as in `Ladder round 5 - request.md`, rules of 2026-10-26. **Status (Oct 26, 15:40 UTC): round 5 is finished**: 2 new pairings played (#746, #747), 62 reused (incl. Celeris-1 Decision's 13 early-start matches #733-745). **The ladder has ended**: round 6 would need no new matches. The final placement is in `Ladder ended - final placement.md`, not applied (waiting for Can).

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

## End of the ladder (not applied)

- Round 6 would swap Clef (League 1's top) with Celeris-1 Decision (League 2's last), and Gemini 4 Argon (off) (League 2's top) with Gemini 3.8 Flash (low) (League 3's last); every pair is stored.
- Final placement by original league:
  - Clef stays in League 1.
  - Celeris-1 Decision goes to League 1.
  - Argon (off) goes to League 3.
  - Flash (low) goes to League 2.
- League 1 would have 20 setups, League 2 18, League 3 12. No match is needed.
- Next (after Can approves the placement): `apply --round 6`, then the Cup roster and the league rename (not started).
