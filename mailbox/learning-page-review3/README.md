# Learning page, review 3 (Review3, 2026-11-07, after the 17:00 UTC bariton reboot)

**Candidate:** branch `learning-page`, commit **9d8c29b** (678b225 + the top-label fix below; on origin/main 7719e1a;
origin/main has since gained mailbox notes only: `tools/site` is identical in 7719e1a and current main). Not merged.

### 9d8c29b: what changed, why, and what was rerun

- **Change** (`tools/site/learning_page.py`, `body`): the Learning page's top label follows the validated status:
  "Complete" when `learning_validate` accepts complete (`validation.complete`), otherwise "Preliminary · running".
- **Why:** review 3 at 678b225 found the label fixed at "Preliminary · running" even in the SYNTHETIC complete state
  (Main's instruction).
- **Rerun at 9d8c29b:** 02 (all 4 states; each now also prints the top label: "Preliminary · running" in none, dry
  run and SYNTHETIC running, "Complete" in SYNTHETIC complete; 0 failures in all 4), 04 (branch render redone from
  9d8c29b with 01's state copy and results hash 1279974c, against 01's main render: 0 unexplained), and the four
  `learning-tab-SYNTHETIC-complete-*` screenshots. Command: `PATH=/usr/bin:$PATH bash
  mailbox/learning-page-review3/scripts/rerun_02_04.sh` (17:23 UTC), then `screenshots.py /tmp/inv
  learning-tab-SYNTHETIC-complete` (17:24 UTC).
- **Not rerun, still from 678b225:** 01, 03 and the other 24 screenshots. The fix changes only the label of a
  complete page, which none of those shows (01 and the screenshots render the no-results state; 03's page faults use
  the running state).
- A first rerun at 17:21 hit the live site's own timer republish: 3 link failures (`../decisions/`, `../data/` not
  resolving while the live directories were replaced) and, because the live results hash had moved, hundreds of
  unexplained files in 04. `rerun_02_04.sh` now pins 01's hash; the final rerun above is clean. Those outputs were
  overwritten.

Render-only: no `build.py`/`update.sh` on the live site, no HTTP server, no timer/service action, no model call. The
live state and the live site (`~/.local/state/bg-site`) were only read; renders, fixtures and the state copy are
scratch in `/tmp/inv`. Every output below is a file in this folder.

## Results

| File | What | Result |
|---|---|---|
| `01-full-checks-run.txt` | whole-site render, main (origin/main d62ec9e tools/site) vs branch (678b225), same state copy, results hash 1279974c, full `checks.run` | main 0 failures; branch 0 failures |
| `02-page-checks.txt` (**9d8c29b**) | `learning_page.py --check` in 4 states: none (real workspace, no results), dry run (running), SYNTHETIC running, SYNTHETIC complete | 0 failures in all 4; validator accepts all; lift/signal/leaders blocks and keys only in the complete state; top label "Complete" only in the complete state |
| `03-injected-faults.txt` (c1) | 7 faults injected into the rendered page (SYNTHETIC running) | 7/7 detected |
| `03-injected-faults.txt` (c2) | 17 faults injected into the pilot's files (SYNTHETIC complete fixture) | 17/17 handled (8 file refused, 9 "complete" refused); baseline accepted |
| `03-injected-faults.txt` (c3) | Zeki's `synthetic_checks.py` (sha256 80760a6b…8811) on 678b225's `tools/site` | **did not run: AssertionError at extraction.** It extracts `read_lessons` from `learning_page.py`; that function was removed in 97aaa78 (lessons now come from `learning_validate.py`'s reconciliation with the inventory). Every other function and constant it extracts is present. Zeki's script was not modified. Needs an updated script from Zeki, or his call that the removed path is covered by c2. |
| `04-invariance-inventory.csv`, `04-invariance-summary.txt` (**9d8c29b**) | file-by-file inventory of the two whole-site renders | 2,544 vs 2,542 files: 2,429 identical, 2 added (learning page + its data), 113 explained, **0 unexplained** |
| `05-screenshots-log.txt`, `screenshots/` | 7 views × 1280/390 × light/dark = 28 PNGs | all written |

### The Method change (Main, 678b225), classified

`method/index.html` is explained by the rule "method: 'Learning from experience' status 'Running (preliminary)'
linking to learning/, was 'Not measured' (Main, commit 678b225; expected)", together with the site-wide rules (title,
Part row, view-bar label, Analyses nav link). The rule undoes exactly these two lines; nothing else in the file differs:

```
main:   <h2 id="learning-title">Learning from experience <span class="status status-not-measured">Not measured</span></h2>
        <p>Every decision is a separate request; models are not told how earlier games went.</p>
branch: <h2 id="learning-title">Learning from experience <span class="status status-running">Running (preliminary)</span></h2>
        <p>Running (preliminary): see <a href="../learning/">Learning across games</a>.</p>
```

No results text. The "Memory" limit in Method is unchanged. Screenshot: `screenshots/method-learning-row-*.png`.

## SYNTHETIC

The "synthetic running" and "synthetic complete" states, the c2 faults and every `*SYNTHETIC*` screenshot use
fixtures made by `scripts/make_fixture.py` from the dry run's aggregates. They are **SYNTHETIC test data, not
results**: no model call has been made and no series has run. Zeki's `synthetic_checks.py` uses in-memory SYNTHETIC
data only.

## Plan hash chain (`mailbox/Learning pilot - plan 2026-11-07.md`, recomputed from git at each commit)

| Commit | sha256 |
|---|---|
| 5af8842 | 3839eae1c1411ef82e20fe9ef18fdf4818192a7e44c034a07fea1e6bbfaa0861 |
| e9475b3 | fc29d8ff6f70a137bfbc78aaa3a076156c162f5fdc12a7d1ce59611162220caf |
| 09bcbc4 | 39156727711cb991599ca54312511eb7957555248cd0c1ecdd27d07885a65fbc |
| 7719e1a | 1e9bc932e0f6e72605868582510e4c8026885f19153a562cf1ed493a046ce8f6 (current; same in 678b225 and on main) |

Lesson prompt sha256 (from the plan): d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e.
Private evaluation set: test_set.json sha256 6c92e741…18e6 (read only, never copied here).

## "How the numbers work" (home, branch render), quoted from Method

- Who scores. GNU Backgammon 1.08 evaluates every legal play at 2-ply, in cubeless money equity (expected points per game, match score ignored). The loss of a decision is the equity of the best play minus the equity of the play made. *Method: Error rate*
- Error rate. 500 × mean 2-ply equity loss per decision. Lower is better. This is the checker-play performance rating (PR) that backgammon players use. *Method: Error rate*
- Risk judgement. The average of risks found and right safety, × 100. It does not depend on how many positions of each class a setup met. With both classes present, the Safest program scores exactly 50, the "always safe" line. *Method: Was it the right risk?*
- Intervals. Intervals are 0.95 bootstrap intervals with 2000 resamples and a fixed seed (20261021). League decisions resample whole games, because moves within a game are not independent. *Method: Statistics and verdicts*
- Different positions. Setups played different positions; league comparisons are not paired, and risk judgement is not adjusted for how hard the positions were. *Method: Limits*

## Provenance and commands

From the worktree `/home/cbasaran/code/jevgammon-learning-page` at 678b225, with `/usr/bin/python3` first on PATH
(the systemd service's Python; the login shell's miniconda Python lacks numpy, so the first attempt at 17:07 failed
on import and was rerun):

```
PATH=/usr/bin:$PATH bash mailbox/learning-page-review3/scripts/run_review.sh          # 17:12:29-17:16:47 UTC: 01-04
~/.pyenv/shims/python3 mailbox/learning-page-review3/scripts/screenshots.py           # 17:18 UTC: screenshots/, 05
```

| Output | Written by | Inputs |
|---|---|---|
| 01 | run_review.sh (a) → `scripts/render_site.py` | origin/main and HEAD `tools/site` (git archive), copy of live state, live results hash |
| 02 | run_review.sh (b) → `tools/site/learning_page.py --check` | `snapshot.snapshot_learning` of the real workspace and of the dry run; `make_fixture.py` fixtures |
| 03 c1 | `scripts/injected_faults.py` | page-synthetic-running render |
| 03 c2 | `scripts/injected_source_faults.py` | fix-complete (SYNTHETIC) |
| 03 c3 | Zeki's `synthetic_checks.py` (copied unchanged next to a git archive of HEAD `tools/site`) | in-memory SYNTHETIC data |
| 04 | `scripts/invariance.py` | out-main and out-branch renders from 01 |
| screenshots, 05 | `scripts/screenshots.py` (Playwright Chromium, file:// URLs, prefers-color-scheme light/dark) | out-branch; SYNTHETIC complete = out-branch with page-synthetic-complete's learning page and data file |

Changes to the review scripts in this session: `invariance.py` gained the Method rule; `run_review.sh` gained c3;
`screenshots.py` is new (optional name prefix to retake some shots); `rerun_02_04.sh` is new. The obsolete partial 01
from before the reboot is not included.

## Observations (not changed; for the page owner / Zeki)

- Fixed in 9d8c29b: the top label. Still fixed text in every state: the page title and `<h1>` "Learning from
  experience (preliminary, running)" and the site-wide nav link of the same wording
  (`screenshots/learning-tab-SYNTHETIC-complete-*.png`).
