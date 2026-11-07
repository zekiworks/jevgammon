# Learning page status before the bariton reboot (from LearningPage, 2026-11-07 about 16:28 UTC)

`origin/learning-page` is at **97aaa78**. This is a work-in-progress commit on origin/main 7719e1a, with plan sha256 1e9bc932…e8f6.

## Done in 97aaa78

- **Earlier items (from 587e57f):** the Part-row tabs (TAB_RISK and TAB_LEARNING), the new TITLE, `home.HERO_LINKS`, `home.how_numbers` and `RANK_NOTE` (Zeki's #2578 wording). Whole-site `checks.run` gave 0 failures at 587e57f.
- **Learning page:**
  - records dropped, tokens and latency, and the "API spend" wording;
  - the plan rendered through `method.spec_markdown`, including code fences and blockquotes;
  - the Learning tab card: no leader until the run is complete, then the plan §9 order (arms that meet the signal rule first, then by lift against control), with the plan bullet quoted;
  - the checkpoint chart;
  - the budget arm's per-point table, with the plan §11 "Interpretation, fixed now" bullet quoted.
- **`learning_validate.py`:**
  - a closed, typed schema;
  - the site's own copy of the protocol;
  - the lesson prompt hash from the plan;
  - the test-set hash taken at build time;
  - completeness recomputed from the aggregates: series 1–10, games 1–10, T5 and T10 answered 200/200, and lesson-file hashes matched against the inventory;
  - lift, lift against control, and signal recomputed;
  - lessons reconciled.
- **Check 7** now includes `#learning-leaders`.
- **Snapshot** copies `runs/t0/aggregate.json`.
- **Page checks** are clean in the no-results and dry states.

## Not yet verified

Whole-site `checks.run` on 97aaa78.

## Remaining

1. Full renders of main and the branch, plus `checks.run`, into file 01. The current `01-full-checks-run.txt` is OBSOLETE: it is a partial output from a cancelled run.
2. Page checks in the no-results, running and complete states, into file 02. The complete state needs a SYNTHETIC fixture built from the dry aggregates.
3. Injected faults, including schema faults, into file 03.
4. The invariance CSV and summary, into file 04. The rules are ready in `scripts/invariance.py`.
5. Screenshots of home, the Learning tab and the protocol section, at 1280 and 390 wide, light and dark.
6. A README with the commands, timestamps, the Method sections quoted, and the 4 plan hashes. Then copy to the mailbox, commit and push.

## Addendum (LearningPage, just before the reboot)

`origin/learning-page` is now at **47d96f5** (work in progress). It adds two scripts under review3:

- `scripts/make_fixture.py` builds a SYNTHETIC complete or running fixture from the dry aggregates. The validator accepts it as complete.
- `scripts/injected_source_faults.py` handled 17 of 17 source faults:
  - **8 make the validator refuse the file:**
    - the string "true" instead of a boolean;
    - an unknown key;
    - a 5th arm;
    - planned set to 2;
    - a wrong prompt hash;
    - a wrong test-set hash;
    - a wrong inventory hash;
    - `t0_done` set to 1.
  - **9 make the validator refuse "complete":**
    - `dry_run`;
    - budget series 10 missing;
    - a tampered vs_control value;
    - a wrong signal flag;
    - T10 answered 199 of 200;
    - a wrong games 8–10 rate;
    - an edited lesson file;
    - the T0 aggregate missing;
    - a wrong type for `budget_points`.

That output was not saved to a review file; it has to be rerun after the reboot.
