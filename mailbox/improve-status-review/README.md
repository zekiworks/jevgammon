# "Models and status" table on the improve page: review (ImproveStatus, 2026-11-08, Ümit #3219)

**Candidate:** branch `improve-status`, commit **d2b9897** on origin/main 2456635 (pushed, not merged). Code-only diff
against main: 4 files, +280 −19 (`03-diff.patch`): `tools/site/improve_validate.py`, `improve_page.py`, `checks.py`,
`selftest_improve.py`. No CSS, plan, snapshot, build or harness change.

## What the page shows

A new first section **Models and status** (`#improve-status`), above the rule: one row per chat model of the plan's
section 3 (15, plan order; the decision models and Cygnet stay in their "not tested" table under **Models**, which is
renamed from "Models and status"; its plan column is now "Status in the plan (8 Nov)"). Columns:

| Column | Source |
|---|---|
| Model | plan setup name |
| Route | from the plan's route: billed → `OpenRouter`; "subscription" → `subscription`; `local …` → `our GPU` (build fails on anything else) |
| Status | `not started` / `running` / `paused (reason)` / `stopped (reason)` / `done`; reason one of the fixed texts `shared-balance priority`, `waiting for the ChatGPT reset 13 Nov`, `waiting for its turn` |
| Series done (of 5) | `n / 5` |
| Last update (UTC) | the model's `progress.updated_at` |

A plan model the file does not list: `not started`, `0 / 5`, N/A. No outcome number, no free text from the file.
The table is shown in the default build (PREREGISTRATION_ONLY stays on): there only the progress fields are read
(`improve_validate.status_view`; no test set, no results); with results on, from the fully validated file.
If the status fields are refused: every cell N/A and a "Status unavailable" note with the public problem names.

## Schema extension (closed; per model in `improve.json`)

```json
"progress": {"status": "paused", "reason": "shared-balance priority", "series_done": 1,
             "updated_at": "2026-11-08T16:26:08+00:00"}
```

- `status` ∈ {`not started`, `running`, `paused`, `stopped`, `done`}; `reason` null or one of the three texts; required
  when paused, refused when running or done; `series_done` int 0..5 (5 when done, 0 when not started); `updated_at`
  ISO (the site's ISO pattern). Missing, extra key, bad enum, 6, a string → refused.
- Full validation also: `series_done` = finished series in `steps_done`; status agrees with `state` (not started ↔
  running/paused with no step done; running ↔ running; paused ↔ paused; stopped ↔ stopped/incomplete; done ↔ complete).

**Producer change needed (not in this branch; harness branch `improve`, owner Improve):** `model_summary` must emit
`progress` (and list held models, e.g. from `hold.json`, if their rows should say `paused (shared-balance priority)`
rather than `not started`). Until then the live file is refused by the status view, as the frozen render below shows.

## What ran

- `selftest_improve.py` (`02-selftest.txt`): **84/84**. New: state `paused`; status table in the default build for
  none / running-1 / paused / complete-yes (done): 15 rows equal to the data, section before the rule, no outcome
  marker (`data-cell`, `data-verdict`, `#improve-lessons`) and no free-text reason from the file in page or data file,
  data rows exactly {setup, status, reason, series_done, updated_at}, check_improve clean; 11 progress faults (status
  outside the enum with canary, series_done 6, series_done "5", progress missing, series_done missing, updated_at not
  ISO, reason outside the list with canary, paused without reason, done with reason, done with 4, unknown key with
  canary) each refused by **both** the full validation and the status view, no canary on page/data; 3 page faults
  (wrong status, wrong series count, row removed) each caught by `check_improve`. The results-view loop skips the
  `paused` state: a model listed before its first empty run renders "N/A → N/A", which `check_improve`'s cell reader
  sees as "→ N/AN/A" (pre-existing in the results view, PREREGISTRATION_ONLY on; not changed here).
- Leak scan: `check_improve` (test positions: id, board key, board; host/withheld marks) and `checks.scan_file`
  (private strings) on every render above and on the frozen render.
- Full site: `build.py --no-image` on a frozen copy of live state (`01-build-and-checks.txt`): `cp -a` of
  `~/.local/state/bg-site` at 16:36 UTC, improve files refreshed with `snapshot.snapshot_improve` (copy identical to
  `workspace/improve/out/improve.json`, updated_at 16:26:08Z); `checks.run` inside, **exit 0**; then
  `improve_page.py --check`: **0 failures**. Built from 85ebd52, the same code as d2b9897 (rebased over mailbox-only
  commits). Result: the live file has no `progress` → "Status unavailable … models[0]: progress missing", all 15 rows
  N/A (screenshot `REAL-frozen`).
- Screenshots (`04-screenshots-log.txt`, `scripts/screenshots.py`), Playwright Chromium, light, 1280 and 375:
  REAL-frozen page top and status section; SYNTHETIC none / running-1 / paused / done status sections (the selftest's
  default-build pages laid over the frozen site). At 375 the table scrolls sideways (the site's "Swipe for more
  columns").

Rerun: `selftest_improve.py --workspace <main checkout>/workspace --keep $SELFTEST`; build as in 01; then
`~/.pyenv/shims/python3 mailbox/improve-status-review/scripts/screenshots.py $SITE $SELFTEST`.
`MANIFEST.sha256` lists every file here.
