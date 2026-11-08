# Learning page, review 5 (LearningPage5, 2026-11-08): Ümit's page spec (#2925) and Zeki's four fixes (#2931)

**Candidate:** branch `learning-page`, commit **34ef85e**, rebased on origin/main **dc00eca** (nav-ct merged). Pushed,
not merged. `PREREGISTRATION_ONLY = True` stays the production default (no GO yet); the results view is rendered here
with the review flag `--with-results` only.

| Commit | Change |
|---|---|
| 003f7e7 | ad2fb4d (review 4's candidate, Zeki #2676), rebased unchanged |
| e65ce73 | #2925: status line, the two charts with their tables, verdict/lift only when validated complete (wording #2929), lessons beside their games; `checks.check_learning` checks all of these against the data file; a real T0 aggregate (no `dry` key) is accepted |
| 9f37745 | #2931: the four validator fixes (below) |
| 34ef85e | verdict wording: "For records and lessons, ..." |

Files changed against origin/main: `tools/site/learning_page.py`, `learning_validate.py`, `checks.py`,
`assets/bg.css`. Everything here was render-only: no `build.py`/`update.sh`, no server, timer, service or deploy, no
model call. Note (as Zeki says): the whole-site renders call `build.compute` and the complete state's validation runs
the bootstrap (10,000 resamples), so "render-only" is not "compute-free".

## What the page does now (results view, behind `--with-results` until the GO)

1. **Status line** at the top of the page (`learning_page.status`, and independently re-derived by `checks.py`),
   exactly one of: `Not started` / `Smoke running: N of 3 series per arm` / `Running: N of 10 series per arm` /
   `Done`, with `Last update: <UTC time>`. Derivation, from the validated state only:
   - N = the series finished in **every** arm: the minimum over the arms of learning_validate's finished series.
   - `Done` only when learning_validate accepts the results as complete.
   - `Not started`: no accepted results file, or one with no finished series in any arm and no shared T0 run.
   - `Smoke running`: N < 3. Plan §5 runs 3 series per arm first (the smoke), then continues, so the run is in its
     smoke phase exactly until every arm has finished 3.
   - `Running`: N ≥ 3 and not accepted as complete (this includes 10 of 10 if, e.g., T0 is not answered in full).
   - Last update: the latest `finished_at` of the validated aggregates behind the page (shared T0 and finished series),
     shown in UTC; "none yet" before the first.
   - A refused results file shows `Not started` (nothing validated) plus "The latest results file was not accepted".
2. **Results** (empty until the first finished series), in the site's SVG chart style (`chart-svg`, the earlier
   checkpoint chart's helpers generalised as `line_chart`), arm colours fixed in one map (`ARM_COLOUR`: control
   `--text-2`, records `--reading`, lessons `--good`, budget `--wrong`, set as `--lp` on every line, dot and swatch):
   - (a) risks found on the 200 evaluation positions before game 1 (T0) / after game 5 / after game 10, one line per
     arm; control is a flat dashed line at its T0 value (it has T0 only); table arm × checkpoint under it;
   - (b) error rate per game 1–10, averaged over each arm's finished series (mean of the series' game error rates),
     one line per arm; table arm × game under it.
   - Every number is in the data file (`game_error_rate`, `table`); the tables pass checks.py's number check.
3. **Verdict and learning lift** only when learning_validate accepts complete; otherwise "N of 10 series done in every
   arm" (and the numbers above). The verdict: the plan §8 threshold per non-control arm with the changes and their
   intervals; the T0 caveat (T10−T0 intervals conditional on the single T0; not the game-lift intervals); the budget
   arm's plan §11 reading ("with this budget, record memory could not be provided", shown only because its context
   was empty at all 100 of 100 points); "All observed game-lift differences are below control" (derived from the
   data's signs); which intervals include zero; for budget, the interval excluding zero with Zeki's #2929 wording ("The
   source of this unexpected difference and the calibration of the intervals were not determined in this pilot").
   No "no effect", no non-determinism claim, no vs-budget comparison. The Learning tab order (plan §9) only when
   complete (unchanged).
4. **Lessons**: every lesson of the lessons arm next to its game (series, game, result), one box per series, text
   escaped, from the validated lesson files only (hash-bound to their aggregates).

The default build (pre-registration only) is unchanged: its page and data file are byte-identical to origin/main's
(02, last section; 04).

## Zeki #2931: the four fixes, each with a regression test (03a)

`scripts/zeki2931_regressions.py`, run on the tree before the fixes (003f7e7 = ad2fb4d rebased) and on 34ef85e:

| Fix | Cases | Before (003f7e7) | After (34ef85e) |
|---|---|---|---|
| 1 malformed T0 ({} / list) refused before its fields are read; a real T0 without `dry` accepted | 3 | 3 crash (KeyError, TypeError, KeyError) | 3 PASS |
| 2 no untrusted name (unknown key, map key, arm/series directory) in the public page or data file: `[name withheld]`, full text on stderr only | 5 canaries | 5 leak into the page | 5 PASS |
| 3 budget points one per game 1..n in order, agreeing with the context records; empty list = points with no game shown | 3 | 3 accepted | 3 PASS |
| 4 evaluation counts: valid + invalid + failed = answered, calls = valid (T0 and every checkpoint) | 2 + 1 control | 2 accepted; control passes | 3 PASS |

Before: 1/14 (the control case: consistent failures stay accepted, as they must); after: 14/14. Exit codes saved.

## Results (all saved with their commands)

| File | What | Result |
|---|---|---|
| `00-states.txt` | the states (real, none, SYNTHETIC subsets) | see "SYNTHETIC" |
| `01-site-renders-and-checks-run.txt` | whole-site renders of origin/main and the branch (default build), `checks.run` on the branch's | 0 failures |
| `02-page-checks.txt` | `learning_page.py --check` in 6 states: default (pre-registration), none, SYNTHETIC not started / smoke running / running, REAL complete (`--with-results`) | 0 failures in every state; status lines as derived; verdict/lift/signal only in the REAL complete; the REAL results file accepted complete by learning_validate |
| `03a-zeki2931-fix-regressions.txt` | the four fixes' tests, before and after | 1/14 before (control), 14/14 after |
| `03-faults.txt` (c1) | 38 faults injected into the rendered page or its data file | 38/38 detected |
| `03-faults.txt` (c2) | Zeki's `synthetic_checks.py`, as delivered | stops at extraction (it imports `read_lessons`, removed in 97aaa78; as in review 4, not a product result) |
| `03-faults.txt` (c3) | Zeki's 8 synthetic cases ported to this candidate (11 checks) | 11/11 end as fixed (refused or build failed; nothing published) |
| `03-faults.txt` (c4) | review 4's saved regression cases, now on the REAL complete state and the SYNTHETIC running subset | 58/58 |
| `04-invariance-*` | origin/main's render against the branch's, file by file | 2,548 identical, 1 explained (bg.css's Learning block), **0 unexplained** |
| `05-screenshots-log.txt`, `screenshots/` | 16 shots × 1280/390 × light/dark | 64 PNGs |

The injected faults (c1) include: the status line lying (N, "Done" while running, "Smoke running" after the smoke,
wrong time, removed, the data file's own line); chart numbers not in the data (risks and games dots, a dropped dot);
table numbers not in the data (a cell changed to another value; a number absent from every data file); control's line
not dashed, not flat; another arm dashed; an arm not in its fixed colour; a chart removed; the verdict/lift block or
lift/signal keys before complete; a wrong "N of 10 series done"; the data's complete flag disagreeing with the
validation; on the REAL complete render, a verdict contradicting the signal, the budget reading removed, the verdict
removed; lessons without their game (data and page), of an unknown series, dropped, edited, unescaped; evaluation-set
id, board key and board strings in the page and the data file. Evaluation-set strings are redacted (`[REDACTED]`) in
every saved output.

## SYNTHETIC

Only the real complete state is real. `scripts/make_states.py` builds every state in snapshot.py's STATE/learning
layout by copying the pilot's published inputs exactly as `snapshot_learning` does (read-only reads):
- `real`: the real files, unchanged (complete);
- `none`: the lesson prompt files only (no results file);
- **SYNTHETIC** subsets of the real series (series removed, nothing else edited, the summary rewritten as pilot.py's
  summary would be for the kept aggregates, `updated_at` = latest kept `finished_at`):
  - `SYNTHETIC-not-started`: no T0, no series;
  - `SYNTHETIC-smoke-running`: T0 + control 1–3, records 1–2, lessons 1–3, budget 1–2 → "Smoke running: 2 of 3";
  - `SYNTHETIC-running`: T0 + control 1–7, records 1–6, lessons 1–6, budget 1–5, plus budget s06 cut after game 4
    (unfinished: validated, not published) → "Running: 5 of 10".

Every SYNTHETIC screenshot and render is named `SYNTHETIC-…`. Faults and regression cases are test inputs, never
results.

## Screenshots (`screenshots/`, each at 1280 and 390, light and dark)

`learning-default-preregistration-page` (production default, PREREGISTRATION_ONLY on, the whole-site render);
`learning-real-complete-{status-line,charts-and-tables,verdict-and-lift,lessons,page}` (REAL, review flag);
`learning-SYNTHETIC-running-{status-line,charts-and-tables,verdict-pending,lessons}`;
`learning-SYNTHETIC-smoke-running-{status-line,charts-and-tables,verdict-pending}`;
`learning-SYNTHETIC-not-started-{status-line,results-empty}`; `learning-none-status-line`. Element shots are taken
with the site's sticky top bar made static, so it is not stitched over them. No page was wider than the viewport.

## Commands (from the learning-page worktree)

    PATH=/usr/bin:$PATH bash mailbox/learning-page-review5/scripts/run_review5.sh      # 00-04 (scratch: /tmp/inv5)
    ~/.pyenv/shims/python3 mailbox/learning-page-review5/scripts/screenshots.py /tmp/inv5   # 05 + screenshots/

The site state is review 3's copy (`/tmp/inv/state`, read only); both whole-site renders use it and the fixed results
hash 1279974c, so 04 compares like with like. Timestamps (UTC, also in each file's header and footer): 01 08:01:58-08:03:53, 02 08:03:53-08:04:00, 03a 08:04:00-08:04:04, 03 08:04:04-08:05:20, 04 at 08:05:20, screenshots 08:05:21-08:05:32, all on 2026-11-08, at 34ef85e on origin/main dc00eca.

## Housekeeping

Before the rebase, the worktree's uncommitted review-3 script edits and its untracked review-3/review-4 packet copies
(older than the packets committed in main) were stashed (`git stash list` in the worktree: "review3/review4 WIP
packet files …") and also copied to `/home/cbasaran/code/jevgammon-learning-page-wip-backup-20261108/`. Nothing was
lost; they are not part of this packet.

## Not done / open

- `PREREGISTRATION_ONLY` stays True: switching it off needs Zeki's GO on this candidate.
- In pre-registration-only mode the page has no status line (the build reads nothing of the run, so it has no status
  to state); the status line appears with the results view.
