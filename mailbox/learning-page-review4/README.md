# Learning page, review 4 (Review3 agent, 2026-11-07): Zeki's final review of 9d8c29b (#2676)

**Candidate:** branch `learning-page`, commit **ad2fb4d**. It is on origin/main 7719e1a; `tools/site` is unchanged on
main since then. Pushed, not merged.

Commits since review 3's candidate 9d8c29b:

| Commit | Change |
|---|---|
| 3f6fc82 | #2671: typed rejected validation; the evaluation set required (first version); title follows the status; the two charts as separate SVGs that stack on phones |
| 50dcba1 | charts: right margin so "After game 10" is not clipped at 390 px |
| 89c0f01 | **pre-registration-only mode** (Main): `learning_page.PREREGISTRATION_ONLY = True`, default ON |
| ad2fb4d | #2676: the publication boundary rebuilt (below) |

Everything was render-only: no `build.py`/`update.sh`, no HTTP server, no timer or service action, no model call.

The live state was only read: review 3's copy of it and review 3's main render (`/tmp/inv/out-main`, results hash
1279974c) were reused, so 04 compares like with like.

## What ad2fb4d changes, against each finding

**Pre-registration-only mode (89c0f01, default ON).** With it on, `learning_page.data` reads none of these:
- the results file;
- any aggregate;
- any lesson file;
- the test set.

The page shows only the plan and the pre-registered lesson prompt:
- label "Pre-registration";
- title "Learning from experience (pre-registered)";
- the line "No results or lessons are published on this page yet: they are not read by the build."

Results and lessons are published only after a reviewed commit switches the constant off. `--with-results` exists for
review renders only.

Evidence in 02: an audit hook over the default build with a SYNTHETIC complete source opened only `lessons_system.txt`
and `lessons_user.txt`. The default build's page and data file carry no results, lessons or budget points.

**P1, missing private evaluation set.** The build fails (`TestSetRequired`) if the evaluation set is missing, unreadable
or does not match the results' stated hash, whenever any of these is present:
- a results file;
- any aggregate;
- any lesson file.

`checks.check_learning` likewise fails, rather than skips, when the set is missing and the page carries results,
validation or lessons. Only the no-results state builds without the set.

**P1, closed nested schema and escaping.** `learning_validate.check` applies a closed recursive schema to:
- every key, type and range of the T0 aggregate;
- every series aggregate, including each game, each evaluation (with `calls`), each budget point and each
  lesson-call record.

Details:
- `games_shown` must be a list of game numbers 1–10, distinct and not after the point; `games_dropped` must equal
  `after_game` minus the number of games shown.
- Results must be one of single, gammon or backgammon.
- Strings are limited to fixed patterns.
- NaN and infinities are refused.
- The page publishes an explicit projection, key by key: table rows by `METRICS`, games by `GAME_METRICS`, the lift and
  the signal by `LIFT_KEYS` and `SIGNAL_KEYS`, budget points by their five fields.
- Every interpolated value on the page is escaped (budget cells, series and game numbers, lesson text).

**P1, table and signal bound to the aggregates.** The site recomputes `pilot.py summary()` from the validated
aggregates. `learning_validate.summary` is a line-by-line copy of harness ba8b011, including the bootstrap intervals
with the same seed and the same count. The results file is refused unless every field agrees:
- table (the shared T0 in every arm included), games, series, inventory;
- finished series, `series_done`, `t0_done`, completion;
- once complete: the learning lift, the signal, their intervals, and the paired series.

Each aggregate must match:
- its directory, for the arm and the series;
- the series' dice seed, `series_seed(s)` from pilot.py's master seed;
- the lesson prompt files present at build time;
- the evaluation set present at build time.

Each game's error rate must follow from its losses, and games 1–3 and 8–10 must follow from the games.

The published numbers come from the site's own projection, not from the summary. That projection is rebuilt from the
finished series only, with `provenance`: the sha256 of the T0 aggregate and of each published series' aggregate, plus
the prompt and test-set hashes.

This is a file-consistency check, not proof that the runs were stochastically independent, as Zeki notes.

**P2, provenance of running series.** These requirements hold while running too:
- the lesson prompt files must be present, or the file is refused;
- every finished lessons series needs its aggregate, and every lesson file must match the aggregate's hash, or the file
  is refused;
- unfinished series are validated but not published.

**P2, a refused file rendering.** A refused validation always carries all four fields:
- `accepted`
- `producer_complete`
- `complete`
- `problems`

Labels and the title use `.get`. The regression suite renders the whole page for every refused case. It also renders
the body for Zeki's bare `{accepted, problems}` shape.

**Fidelity check against the real harness.** The real dry run's `learning-pilot.json`, written by `pilot.py` (ba8b011),
is accepted by the site's recomputation (02, dry-running state). The site's copy therefore agrees with the producer on
real files.

## Results

| File | What | Result |
|---|---|---|
| `01-branch-checks-run.txt` | the branch's whole-site render at ad2fb4d (default build), full `checks.run` | 0 failures |
| `02-page-checks.txt` | the page alone, in 6 states (see below) | 0 failures in all 6; lift/signal/leaders only in SYNTHETIC complete |
| `03-faults-and-regressions.txt` (c1) | 7 faults injected into the rendered page (SYNTHETIC running) | 7/7 detected |
| `03-faults-and-regressions.txt` (c2) | `scripts/regression_cases.py`: 57 saved cases, 14 of them Zeki's [Zeki] | **57/57** as expected |
| `03-faults-and-regressions.txt` (c3) | Zeki's earlier `synthetic_checks.py` | still stops at extraction: it imports `read_lessons`, removed in 97aaa78 (not a product defect, per Zeki's final review) |
| `04-invariance-*` | review 3's main render against the ad2fb4d render | 2,429 identical, 2 added, 113 explained, **0 unexplained** |
| `05-screenshots-log.txt`, `screenshots/` | 6 changed states × 1280/390 × light/dark | 24 PNGs |

The 6 states in 02:
- the default pre-registration build;
- with `--with-results` (review only): none, dry-run running, SYNTHETIC running, SYNTHETIC complete, SYNTHETIC refused.

In 03 (c2), every case is checked as follows:
- **"file refused" cases:** the full page renders without a crash, shows the "not accepted" note, publishes no
  results, lessons or budget points, has no complete-only block, and passes the leakage check.
- **Accepted cases:** the published table carries only the projection's keys.

Zeki's cases from his `results.json`, rebuilt on the fixture's real aggregate format:
- `string_complete` and `wrong_prompt`;
- `running_missing_test_and_prompt_orphan_aggregate`, split into three cases: no set leads to a build failure; no
  prompt files leads to a refusal; an inventory entry without its aggregate leads to a refusal;
- `missing_test_check_learning`;
- `nested_budget` and `budget_cell_exact_expression`: refused, and escaped in the body;
- `complete_wrong_run_identity`: another arm, another series, an unknown `run_id`;
- `complete_unbound_table_and_nested_extra`: the table and signal changes are refused, and so is the extra literal;
- the rejected-file `KeyError` probe.

Many cases also run with the summary recomputed by an honest producer (`resummarize`). Those show the aggregate-level
checks catch the fault on their own, not only the summary comparison.

## SYNTHETIC

The SYNTHETIC fixtures are test data, not results. No model call has been made.

`scripts/make_fixture.py` builds them in pilot.py's real aggregate format from the dry run:
- series 1–10 (complete) or 1–5 (running);
- each series with its own seed;
- made-up evaluation rates;
- the summary written by `learning_validate.summary`.

The "refused" fixture is the complete one with an unknown top-level key. Every `*SYNTHETIC*` screenshot uses these.

## Provenance and commands

Run from the worktree `/home/cbasaran/code/jevgammon-learning-page` at ad2fb4d, after the commit; the runner refuses a
dirty `tools/site`.

```
PATH=/usr/bin:$PATH bash mailbox/learning-page-review4/scripts/run_review4.sh   # 17:48-17:53 UTC: fixtures, 01-04
~/.pyenv/shims/python3 mailbox/learning-page-review4/scripts/screenshots.py      # 17:54 UTC: screenshots/, 05
```

| Output | Written by | Inputs |
|---|---|---|
| 01 | run_review4.sh (a) → `render_site.py --checks` | HEAD `tools/site` (git archive), review 3's state copy and results hash |
| 02 | run_review4.sh (b) → `tools/site/learning_page.py --check` (links against the branch render) | `make_fixture.py` fixtures; snapshots of the real workspace (no results) and of the dry run |
| 03 c1 | `injected_faults.py` | page-synthetic-running |
| 03 c2 | `regression_cases.py` | fix-complete, fix-running (SYNTHETIC), the private set (read only; values never printed) |
| 03 c3 | Zeki's `synthetic_checks.py`, unchanged | HEAD `tools/site` |
| 04 | `invariance.py` | review 3's out-main, this out-branch |
| screenshots, 05 | `screenshots.py` (Playwright Chromium, file://) | out-branch; per-state overlays of the page renders |

Script sha256:

| Script | sha256 |
|---|---|
| `injected_faults.py` | 27f6dbe8… |
| `invariance.py` | c86206b2… |
| `make_fixture.py` | a58c3457… |
| `regression_cases.py` | 7346bf89… |
| `render_site.py` | 5d8a7475… |
| `screenshots.py` | 7be97d6d… |
| `run_review4.sh` | 1edb6b9b… |

Plan sha256 (unchanged): 1e9bc932e0f6e72605868582510e4c8026885f19153a562cf1ed493a046ce8f6.
Lesson prompt sha256: d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e.

## Notes

- The #2671 outputs (3f6fc82/50dcba1) were produced in the worktree but never committed to the mailbox. ad2fb4d
  supersedes them, and this folder replaces them.
- In the refused state the label stays "Preliminary · running", and the page states "Results file not accepted" with
  the reasons.
- The nav link "Learning from experience (preliminary, running)" is fixed text on every page; it does not follow the
  mode.
