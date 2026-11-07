# Learning pilot and learning page: resume note (written 2026-11-07, before the bariton reboot at 16:33 UTC)

No model call has been made. No series and no evaluation have run.

## State

**Plan** (main, mailbox only): `mailbox/Learning pilot - plan 2026-11-07.md`

| Commit | Change | Plan sha256 |
|---|---|---|
| 5af8842 | original | 3839eae1c1411ef82e20fe9ef18fdf4818192a7e44c034a07fea1e6bbfaa0861 |
| e9475b3 | #2531: budget arm uses whole games; cost wording | fc29d8ff6f70a137bfbc78aaa3a076156c162f5fdc12a7d1ce59611162220caf |
| 09bcbc4 | Learning tab order | 39156727711cb991599ca54312511eb7957555248cd0c1ecdd27d07885a65fbc |
| 7719e1a | #2577: keep the whole-game unit; dry-run fact; interpretation wording | **1e9bc932e0f6e72605868582510e4c8026885f19153a562cf1ed493a046ce8f6** (current) |

The lesson prompt sha256 is unchanged: d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e.

**Harness:** branch `learning-pilot`, commit ba8b011, pushed. Worktree: `/home/cbasaran/code/jevgammon-learning-pilot`. The runner binary there is `target/release/jevgammon`. It survives the reboot; rebuild with `cargo build --release` only if it is missing.

- The working copies of the scripts are in `/home/cbasaran/code/jevgammon/workspace/learning-pilot/` (untracked). They are identical to the branch's copies at ba8b011.
- Private and untracked, on disk: `test_set.json` (sha256 6c92e741…18e6), `test_positions.jsonl`, `configs/base.json`, and the dry-run outputs in `runs-dry/` and `out-dry/`.
- The last dry run, started about 16:25 UTC to verify `budget_points` and the schema-init fix, may not have finished before the reboot. To rerun it (no model call):

  ```
  cd /home/cbasaran/code/jevgammon/workspace/learning-pilot
  rm -rf runs-dry out-dry ../../smoke/learning-pilot-dry.db* ../../smoke/learning-pilot-plays-dry.db*
  PILOT_DRY=1 python3 pilot.py t0 && PILOT_DRY=1 python3 pilot.py run --series 1-2
  ```

  Expected result: `complete` false; `series_finished` lists only control (non-control evaluations are stubbed); budget `budget_points` show empty contexts at every game.

**Page:** branch `learning-page`, worktree `/home/cbasaran/code/jevgammon-learning-page`. The LearningPage subagent was working on it; see "Page status" below.

- The last commit is 47d96f5 (work in progress; 97aaa78 before it), on origin/main 7719e1a. 587e57f already had the tabs, the home title, HERO_LINKS, how_numbers and RANK_NOTE (#2578 wording). It is NOT the review candidate.
- Still to do:
  - #2575 P1/P2: strict, typed, plan-bound completion; the leakage check must require the private test set (hash bound to the run); provenance hashes; a closed output schema; lessons reconciled with the inventory.
  - #2531: records dropped shown, cost wording, markdown rendering of the protocol.
  - #2577: show budget points and the interpretation wording.
  - #2564: hero links, Learning chart, "How the numbers work" box.
  - Review3 outputs saved to files: Zeki's `synthetic_checks.py` run against the candidate, regression cases, page checks, injected faults, the invariance CSV, screenshots.
- Zeki's review and tests: `/home/cbasaran/.agent-bus/received/jevgammon/f_d62d55a7977b40b79aa402c7d7e72c21-REVIEW.md` and `…/f_7f2d02645d854171985de0ea21a21889-synthetic_checks.py`.

## Page status (from LearningPage before the reboot)

See `PAGE-STATUS.md` in this folder, if it was written in time.

## Next steps, in order

1. Finish the learning-page candidate (the items above) and produce `mailbox/learning-page-review3/`. Zip it as `mailbox/learning-page-review3.zip` and send it to Main for Zeki.
2. After Zeki's go: Main merges and checks the live page, then posts the spark3 claim.
3. On Main's go, run from the repo root:

   ```
   python3 workspace/learning-pilot/pilot.py t0
   python3 workspace/learning-pilot/pilot.py run --series 1-3
   ```

   - The first command is the shared T0 evaluation: 200 positions, 4 in flight.
   - The second is the smoke: 4 arms in parallel, at most 4 requests in flight. The budget arm runs each series after the lessons arm finishes it.
   - Then `pilot.py summary` and `python3 workspace/learning-pilot/report.py`.
   - If the smoke is technically clean and the protocol is unchanged, continue with `--series 4-10`.
   - Results go to `mailbox/Learning pilot - results 2026-11-07.md`. The table is aggregates only.
