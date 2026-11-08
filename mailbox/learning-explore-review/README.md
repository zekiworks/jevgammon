# Learning page: plain names and the exploratory block (Ümit #2950/#2952; Zeki #2964; LearningPilot)

**Branch** `learning-explore` (new; worktree `/home/cbasaran/code/jevgammon-learning-explore`), commit **bbcd644**, on
origin/main **4e9b06e** (learning-page merged, `PREREGISTRATION_ONLY = False`; ct-brief merged). Pushed, not merged.
Render-only: no `build.py`/`update.sh`, no server, timer, service or deploy, no model call. The pilot's files, the
exploratory file and the site state were only read (copies under the scratch directory). The whole-site renders call
`build.compute`, and validating the complete state runs the bootstrap, so "render-only" here does not mean "no compute".

| Commit | Change |
|---|---|
| 466aad6 | A: plain arm names (one map, `ARM_LABEL`), the line at the top of Results, "Gemma 4 31B" in every chart title; B: the exploratory block, `snapshot.py` copy, `learning_validate.validate_explore`, `checks.check_learning` |
| 3e41596 | Zeki #2964 wording: pairing, two sampling lists (sent; server's effective defaults), argmax fact, "cause ... not verified" |
| 9d5b0aa | exploratory tables: shorter heads, runs grouped (not sortable), spread with groups as columns, budget rows in order |
| f73a422 | final explore.json: `agreement` (validator, block, checks) |
| bbcd644 | line lengths |

Files: `tools/site/learning_page.py`, `learning_validate.py`, `checks.py`, `snapshot.py`, `assets/bg.css`. The results
file `mailbox/Learning pilot - results 2026-11-07.md` was not touched.

## A. Presentation

- **Top line of Results**, exactly: "One model: Gemma 4 31B (reasoning off, our GPUs) · opponent: GNUbg weak · 4 kinds
  of memory (one of them is no memory) · 10 series of 10 games each." (`learning_page.RUN_LINE`; checked).
- **Chart titles**: "Gemma 4 31B: risks found, % (higher is better)", "Gemma 4 31B: error rate per game (PR, lower is
  better)" (checked). The risks chart is shared with the home page's finding f, which therefore shows the same names
  and title (04 explains it).
- **Arm names** on the page (legends, chart tables, all tables, verdict lines and sentences, budget section, tab
  card): control → "no memory", records → "full records", lessons → "own lessons", budget → "budget (empty: no game
  fit)" (`learning_page.ARM_LABEL`, one map). Data-file keys and internal keys unchanged. The plan's own text (its
  sections, quoted as written) keeps the plan's names. Checks: every legend entry, chart-table row and verdict line
  must carry its arm's name.
- **Verdict**: unchanged apart from the display names (e.g. "All observed game-lift differences are below the no
  memory arm.").

## B. Exploratory block ("Exploratory, after the results")

Placed right after the verdict, in its own card (dashed frame), labelled "Exploratory, after the results. Not part of
the pre-registered verdict above." Contents (all numbers from the validated file, traced by checks.py):

1. **Each arm minus budget (empty: no game fit), paired by series** (same series id and dice seed; the games differ
   once plays differ): full records and own lessons at T5 and T10, risks found, right safety, error rate, risk
   judgement: mean over 10 series [95% interval]. Text: budget's context was empty at every point, so its evaluations
   are empty-context retests of the T0 prompts (the noise baseline); the calibration of the intervals was not
   determined; not part of the pre-registered verdict.
2. **Empty-context runs**: T0, retests r1–r5 (4 requests in flight), the 20 budget evaluations (1 in flight), with
   answered/valid/invalid/failed and the five rates; the spread (mean, min–max, SD) per group. "The cause of the
   differences between empty-context runs was not verified; any sampling or numerical explanation is a hypothesis
   only."
3. **Do the empty-context runs choose the same plays?** The agreement summary (positions of 200 where two runs chose
   different plays) per group of pairs, and the facts that follow from the counts and rows only: retests differ from
   each other on 0–3 positions, T0 from each retest on 8–11; every retest has risks found 28.0 and right safety 97.0
   against T0's 25.0 and 96.0; "T0 differs from the later empty-context runs; the cause was not verified" (shown only
   when every T0-vs-retest count exceeds every retest-vs-retest count; checked); positions not unanimous across the 5
   retests.
4. **How the evaluation requests were made**: *Sent* (temperature 1.0; max_tokens 1; logprobs with top_logprobs 20;
   prefilled "Answer:" with continue_final_message; enable_thinking false; no top_p, top_k or seed sent) and *the
   server's effective defaults* (vLLM's log: overridden by the model's generation_config.json, temperature 1.0, top_k
   64, top_p 0.95; that file identical on the server and in our copy; no seed sent, the server's seed behaviour not
   checked). "The answer is the argmax over the option-letter logprobs, so temperature, top_k and top_p cannot change
   which option is chosen." Positions with more than 26 options (32 of 200) are asked in groups. These facts are fixed
   text from LearningPilot's checks (`learning_page.SAMPLING`, also in the data file so the numbers trace).
5. **Next version (not run)**: budget-match the records at the decision level.

**Plumbing.** `snapshot.py` copies `workspace/learning-retest/out/explore.json` (read-only) to
`STATE/learning/explore/explore.json` with the pilot's files; the copy is in the learning key (00: the key is
959a469f0d60 without the file and changes with it). A missing file: no block, no `explore` key in the data file.

**Validator** (`learning_validate.validate_explore`, run only after the pilot validates complete):
closed schema (keys, types, ranges; run names from a fixed pattern); counts valid + invalid + failed = answered = 200
for every run; arm minus budget (per series, mean, interval with the pilot's bootstrap) recomputed from the validated
aggregates; the T0 and the 20 budget rows equal to the validated aggregates; retest rows exactly the retests with 200
answers; the spread recomputed from the rows; the evaluation set's hash; budget's context empty at every point;
`agreement`: counts 0–200, run names exactly the rows' runs, `pairwise` symmetric and complete, `summary` recomputed
from `pairwise`, the not-unanimous count within what `pairwise` allows (at least the largest retest-vs-retest count, at
most r1's counts against the other retests summed). A refused file publishes only fixed codes
(`EXPLORE_CODES`; details on stderr), and the page shows "Exploratory file not accepted" and no number of it.

## Results

| File | What | Result |
|---|---|---|
| `00-states.txt` | states (with the branch's own `snapshot_learning`) | see "States" |
| `01-site-renders-and-checks-run.txt` | whole-site renders, production mode (`PREREGISTRATION_ONLY = False` on both), origin/main and branch, same state (with the exploratory file) and results hash; `checks.run` on the branch | 0 failures |
| `02-page-checks.txt` | `learning_page.py --check` (production mode): no exploratory file, exploratory file, malformed exploratory file, SYNTHETIC running | 0 failures in all 4; block present only with the file, refused file shows only its codes |
| `03a-explore-validator-regressions.txt` | the validator's regression tests (27 cases: 2 controls, schema, test set, counts, arm minus budget, rows, retests, agreement, spread, unreadable), before (origin/main: no exploratory validation, the file is ignored) and after | before 1/27 (only the "no exploratory file" control), after 27/27 |
| `03-faults.txt` (c1) | injected faults: review 5's 38 (names updated) + 17 new (top line, chart title, names in legend/table/verdict, exploratory cells, agreement, placement, label, block vs data, refused file) | 55/55 detected |
| `03-faults.txt` (c2) | reviews 4/5's saved regression cases | 58/58 |
| `04-invariance-*` | origin/main's production render against the branch's, file by file | 2,544 identical, 4 explained (bg.css, data page row, manifest entry, home finding f chart), 2 subject (learning page and its data file), **0 unexplained** |
| `05-screenshots-log.txt`, `screenshots/` | 7 shots × 1280/390 × light/dark | 28 PNGs |

## States

- `explore`: the REAL complete pilot and the REAL, final exploratory file (sha256 in 00; all 5 retests 200/200), as
  `snapshot_learning` copies them. This is also the whole-site renders' STATE/learning.
- `no-explore`: the REAL pilot, no exploratory file.
- `malformed-explore`: **SYNTHETIC**: the explore state's file with an unknown top-level key (refused).
- `SYNTHETIC-running` (review 5's subset of the real series; only for the running-state faults).

## Screenshots (`screenshots/`, each 1280 and 390, light and dark)

`learning-explore-top-line`, `learning-explore-charts-and-tables`, `learning-explore-verdict`,
`learning-explore-exploratory-block`, `learning-explore-full-page` (production render, real data);
`learning-SYNTHETIC-malformed-explore-exploratory-block` (the refusal); `learning-no-explore-full-page`.

## Commands (from the worktree)

    PATH=/usr/bin:$PATH bash mailbox/learning-explore-review/scripts/run_review.sh            # 00-04 (scratch /tmp/inv6)
    ~/.pyenv/shims/python3 mailbox/learning-explore-review/scripts/screenshots.py /tmp/inv6  # 05 + screenshots/

Timestamps (UTC) are in each file's header and footer.

Run on 2026-11-08 at bbcd644 on origin/main 4e9b06e: 00 11:09:25, 01 11:09:26-11:12:00, 02 11:12:00-11:12:09, 03a
11:12:09-11:13:56, 03 11:13:56-11:15:44, 04 at 11:15:44, screenshots 11:15:45-11:15:54 (UTC).
