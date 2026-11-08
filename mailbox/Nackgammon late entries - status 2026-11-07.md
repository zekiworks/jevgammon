# Nackgammon paired test: late entries, status (2026-11-07)

**Done for 7 of the 8 late entries.** REAX 1.3 was not run: it needs Can's OK to reuse its container exception. Results: `mailbox/Nackgammon paired test - results.md`, section "Update 2026-11-07: late entries". Not published.

Go: Ümit (bus #2646). Billed cap: $0.54 for the whole run (Zeki #2656). Estimate: `mailbox/Nackgammon late entries - estimate 2026-11-07.md`.

## Rules in force

- **Method §10.14(i)** was committed and pushed before any call (`6a64eb8`). The late entries are exploratory: no group, no primary comparison, M unchanged. They use the same rules and scoring, and they form their own group of setups, separate from the 2026-10-28 additions.
- **Separate files.**
  - Roster: `leagues/nack-paired-late.json`.
  - Answers: `smoke/nack-paired-late.db`.
  - Rollouts: `smoke/nack-engine-check-late.db` (a copy of `-g` plus 3 plays).
  - Results: `positions/nack-paired/results-late-2026-11-07/`.
  - The 28 published setups' files are untouched. A fresh report reproduces `results-2026-10-28/` byte for byte.
- **Binary:** `target/drex/release/jevgammon` (harness `e58fc6c`, the late entries' league binary). Request bytes match the 2026-10-27 run apart from the model id.
- **Tools:**
  - `tools/v3/nack_paired_late.sh` (one setup);
  - `tools/v3/nack_paired_late_local.sh` (local setups on one GPU UUID; Docker gets the index mapped from the UUID, checked on the host and inside the container);
  - `tools/v3/nack_paired_late_rollouts.py` (rollouts of missing plays);
  - `tools/v3/nack_paired_score.py` (`NACK_DB`/`NACK_ROSTER`, the `LATE` set, a late-only report).

## Runs

| Setup | Answered | Extended | Billed | When (UTC) |
|---|---|---|---|---|
| SubQ Snap 1.1 | 1,000, 0 failed | yes | $0.112 | 17:22–17:28 |
| Drex Max 1.1 | 1,000, 0 failed (early 429s were retried) | yes | $0.084 | 17:22–17:38 |
| Drex 2.0 | 1,000, 0 failed | yes | $0.163 | 17:38–17:48 |
| Drex Max v1 | 1,000, 0 failed | yes | $0 (local) | 17:44–17:54 |
| Drex 2.0 (local) | 1,000, 0 failed | yes | $0 (local) | 17:54–18:02 |
| Base Labs Elephant-1 | 1,000, 0 failed | yes | $0 (local) | 18:02–18:06 |
| Base Labs Mammoth-1 | 1,000, 0 failed | yes | $0 (local) | 18:06–18:17 |

- **Billed total: $0.359** of $0.54.
- **GPU:** GPU-7a85a208 (index 2) only, after `reax13-late` had gone. It has been free of us since 18:17:35 UTC.
- The first Base Labs attempt (17:44) failed before loading anything, because Docker here cannot take UUIDs. It was rerun with index 2, checked against the UUID.
- **Rollouts:** 3 plays, GNUbg nice 19, 4 threads (Main: shared CPU), 54 s.
