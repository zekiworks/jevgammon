# Learning pilot: final run manifest (all 10 series)

This manifest covers the whole run: series 1–10 of each arm, plus the shared T0, from 2026-11-07 17:57Z to 2026-11-08 07:28Z.

- **How it was made:** generated read-only by `manifest.py 1-10 mailbox/learning-pilot-manifest-final`. That script is the smoke-manifest script (Zeki #2841 and #2843) extended to a series range. A copy is in this folder.
- **Data:** in `manifest.json`.
- **What it contains:** counts, hashes, times and token sizes only. There are no outcome numbers (no error rate, risks found, right safety, risk judgement, risk appetite or lift), no positions, no contexts and no lesson text, only lesson-file hashes. A check found 0 metric keys, and none of the 200 evaluation-set ids or board keys.
- **Results:** the aggregates and the verdict are in `mailbox/Learning pilot - results 2026-11-07.md`.

## Contents of `manifest.json`

- **`hashes`:**
  - plan `1e9bc932…e8f6`;
  - lesson prompt `d7550015…550e`;
  - evaluation set `6c92e741…18e6`;
  - evaluation prompt file, base config, runner binary;
  - `pilot.py` at each harness commit.
- **`harness`:** which commit ran which part.
  - ba8b011: the first smoke start (T0, control s1–s3).
  - e18ff59: the smoke restart, then series 4–10.
  - What changed between the two commits: `harness-ba8b011-e18ff59.patch`. It is the same patch and hunk list as in the smoke manifest.
- **`t0`:** 200 answers, 0 failed, 0 invalid, with times and hashes.
- **`series[]`:** 40 entries, one per arm and series. Each gives:
  - dice seed, match id and status;
  - start and end times;
  - games 1–10 with their ids, turns and times;
  - decisions per game, and invalid and unscored counts;
  - T5 and T10 answer counts, with failed and invalid counts and times;
  - lesson-file hashes, the number of lesson calls, and cuts;
  - context tokens and records dropped after each game;
  - budget points;
  - evaluation positions excluded;
  - restarts;
  - the test-set and prompt hashes recorded in each aggregate;
  - aggregate, log and match-log hashes.

  In total: 12,200 evaluation answers, 0 failed, 0 invalid.
- **`replays[]`:** the 2 smoke replays. Records s1 aborted match 3 was replaced by match 7. Lessons s1 aborted match 2 was replaced by match 6. Seeds, game-1 dice seed, opening roll and all 63 rolls were compared: `same_dice` is true for both. Archive paths and file hashes are included.
- **`records_context_limit_events`:** 40 drop steps at 22 points over 10 series. Each step dropped the oldest whole game and measured the context again, until it fit the 26,879-token budget. Nothing was trimmed, skipped or refused.

  Format: tokens before each drop → whole game dropped, then tokens after.

  | Series | After game | Drops | Tokens after |
  |---|---|---|---|
  | 1 | 9 | 29,525 → g1 | 25,902 |
  | 1 | 10 | 32,552 → g1; 28,929 → g2 | 25,572 |
  | 2 | 9 | 28,858 → g1 | 26,090 |
  | 2 | 10 | 32,563 → g1; 29,795 → g2 | 26,399 |
  | 3 | 10 | 29,204 → g1 | 25,143 |
  | 4 | 8 | 28,150 → g1 | 24,774 |
  | 4 | 9 | 30,765 → g1; 27,389 → g2 | 24,440 |
  | 4 | 10 | 33,786 → g1; 30,410 → g2; 27,461 → g3 | 23,735 |
  | 5 | 10 | 30,786 → g1 | 26,593 |
  | 6 | 10 | 28,537 → g1 | 26,059 |
  | 7 | 8 | 27,281 → g1 | 24,303 |
  | 7 | 9 | 30,862 → g1; 27,884 → g2 | 25,006 |
  | 7 | 10 | 33,564 → g1; 30,586 → g2; 27,708 → g3 | 22,884 |
  | 8 | 9 | 29,387 → g1 | 25,813 |
  | 8 | 10 | 33,385 → g1; 29,811 → g2; 27,864 → g3 | 21,931 |
  | 9 | 7 | 28,302 → g1 | 22,375 |
  | 9 | 8 | 31,636 → g1 | 25,709 |
  | 9 | 9 | 34,837 → g1; 28,910 → g2 | 24,849 |
  | 9 | 10 | 38,407 → g1; 32,480 → g2; 28,419 → g3 | 24,436 |
  | 10 | 8 | 29,847 → g1 | 26,459 |
  | 10 | 9 | 33,565 → g1; 30,177 → g2; 28,412 → g3 | 25,971 |
  | 10 | 10 | 37,203 → g1; 33,815 → g2; 32,050 → g3; 29,609 → g4 | 26,115 |

- **Budget arm:** the context was empty at 100 of 100 points. No whole game ever fit within the lessons arm's token count. See `series[].budget_points`.

## Other files

- `run_smoke.sh` runs the smoke restart, series 1–3.
- `run_main.sh` runs series 4–10.
- Both are systemd user-unit scripts with the explicit interpreter.
