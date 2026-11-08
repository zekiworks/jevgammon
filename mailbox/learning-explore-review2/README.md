# Learning exploratory block, review 2: Zeki #2991 (P2-1, P2-2) and #2993's notes, on bbcd644

**Candidate:** branch `learning-explore`, **7e78dc6**, on origin/main **4e9b06e** (origin/main is now 59a5c16: mailbox commits only, `tools/` unchanged since 4e9b06e; the renders in 01/04 use origin/main 59a5c16). Pushed, not merged. The previous
candidate was bbcd644 (packet `mailbox/learning-explore-review/`, zip sha256 0428b73c…9789). Background, states and the
full method are in that packet's README; this one covers the delta only.

Render-only: no `build.py`/`update.sh`, no server, timer, service or deploy, no model call. The whole-site renders call
`build.compute` and validating the complete pilot runs the bootstrap: "render-only" is not "no compute".

## Delta vs bbcd644 (`source/delta-vs-bbcd644.patch`, `.stat`)

| Commit | Change |
|---|---|
| 320ae23 | **P2-1** the retests' own spread; **P2-2** the narrow settings text |
| 7e78dc6 | #2993 notes: missing retest key refused; comparison names; trust boundary of the pairwise counts |

Files: `tools/site/learning_page.py`, `learning_validate.py`, `checks.py` (no change to `snapshot.py` or `bg.css`).

**P2-1, the retests' own spread.** The regenerated explore.json (same path; sha256 in `06`) has a 4th `spread` group,
`"retests"`: r1–r5 only, n=5. The validator accepts it in the closed schema and recomputes it from the r1–r5 rows (T0
excluded). The page shows it as its own row under the retests in the runs table, "Retests r1-r5: min-max (SD)": risks
found 28.0-28.0 (SD 0.00), right safety 97.0-97.0 (SD 0.00), PR 54.4-54.7 (SD 0.11), so T0's difference is outside
the retests' own range. The spread table gains a "Retests r1-r5" column; the other groups stay. Each cell is checked
against the data file (`checks._learning_explore`, `data-rspread`). Equal aggregate rates are not presented as identical
plays: the agreement counts below show the retests differ on 0–3 positions.

**P2-2, the settings text.** Removed: "temperature, top_k and top_p cannot change which option is chosen". Now: "The
play is the argmax of the returned option-letter probabilities (several tokens per letter are summed). The cause of
differences between empty-context runs was not verified." Then what LearningPilot checked in the stored records of T0,
the 5 retests and the 20 budget evaluations: all 5,200 answers have probability_source "logprobs"; all 7,202 requests
are the prefill readout (max_tokens 1, continue_final_message), and none carries response_format, so the
constrained-letter fallback never fired; no request errors. "Whether vLLM returned raw or processed logprobs (before or
after temperature/top_k/top_p) cannot be shown from the stored records; it was not determined." The "sent" and
"server's effective defaults" lists are unchanged.

**#2993 notes.**
- Missing retest key: every one of r1–r5 must have an answer count; a missing key is refused (`explore.retests`),
  never dropped from "pending". Regression: r5 removed coherently (counts, row, agreement counts and summary and the
  spread recomputed) is refused.
- Comparison names: "own lessons − budget" and "full records − budget" (table rows, heading, caption), with "The no
  memory arm is not compared here: it has only the shared T0, no evaluations after games 5 and 10 of its own."
- Trust boundary, on the page under the agreement table: the pairwise counts, like the retests' rates and the
  not-unanimous count, come from the runs' private answers; the site checks them (range, symmetry, completeness) and
  recomputes only the summary.

## Trust boundaries (what the site recomputes and what it only checks)

- **Recomputed from the validated pilot aggregates** (refused on any mismatch): own lessons − budget and full records −
  budget (per series, mean, interval), the T0 and the 20 budget rows.
- **Recomputed from the file's own rows/counts:** the spread (all four groups), the agreement summary.
- **Checked only** (they come from private answers the site never reads): the retests' rates and counts (schema, 200
  answers each, valid + invalid + failed = answered), the pairwise agreement counts (0–200, the rows' run names,
  symmetric, complete), positions not unanimous across retests (within what the pairwise counts allow).
- **Owner-checked metadata, not inferred by the validator:** `learning_page.SAMPLING` (the sent settings, the server's
  effective defaults, 5,200 answers / 7,202 requests), fixed text from LearningPilot's read-only checks.

## Results (all rerun at 7e78dc6; exit codes in the files)

| File | What | Result |
|---|---|---|
| `00-states.txt` | states (the branch's `snapshot_learning`): explore (REAL, regenerated file), no-explore, SYNTHETIC malformed | — |
| `01-site-renders-and-checks-run.txt` | production-mode whole-site renders, origin/main and branch; `checks.run` on the branch | 0 failures |
| `02-page-checks.txt` | `learning_page.py --check`: no explore file, explore file, malformed file, SYNTHETIC running | 0 failures in all 4 |
| `03a-explore-validator-regressions.txt` | the validator's regression cases (30), on origin/main (no exploratory validation), on bbcd644 and on the candidate | origin/main 1/30 (the no-file control); bbcd644 9/30 (the no-file control and 8 cases whose expected code is schema or unreadable: bbcd644 refuses the regenerated file as schema, its 4th spread group being unknown, so every spread, retests and agreement case fails there); candidate 30/30 |
| `03-faults.txt` | injected faults (57, incl. the retests' range changed / dropped) and reviews 4/5's 58 saved cases | 57/57 detected; 58/58 |
| `04-invariance-*` | production renders, origin/main vs branch, file by file | 2,544 identical, 4 explained, 2 subject (the learning page and its data file), **0 unexplained** |
| `05-screenshots-log.txt`, `screenshots/` | the exploratory block (real) and the refused block (SYNTHETIC malformed), 1280/390, light/dark | 8 PNGs |
| `06-public-projection-and-scan.txt`, `public/`, `source/` | the aggregate-only input (`public/explore.json`), the page's public data file and page as rendered from it, the source deltas; a scan of every packet file for evaluation-set ids, board keys and boards | 0 hits (600 strings) |

The packet holds aggregates and the public projection only: no question, board, position id or answer.

## Commands (from the worktree)

    PATH=/usr/bin:$PATH bash mailbox/learning-explore-review2/scripts/run_review.sh                         # 00-04, 06
    ~/.pyenv/shims/python3 mailbox/learning-explore-review2/scripts/screenshots.py /tmp/inv6 exploratory-block  # 05

Run on 2026-11-08 (UTC): 00-01 11:39-11:41, 02 11:41:08-11:41:16, 03a 11:41:16-11:44:14, 03 11:44:14-11:46:07, 04 and 06
at 11:46, screenshots from 11:46:09.
