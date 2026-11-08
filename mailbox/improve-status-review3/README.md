# Improve page status table, review 3: fixed reason "waiting for a GPU" (ImproveStatus, 2026-11-08, Main)

**Candidate:** branch `improve-status` at **6522002** (pushed, not merged) = fix commit **0a1f5bb** on a59d633, then
origin/main (which already holds a59d633) merged in, so the branch differs from main by the fix only:
`03-diff-vs-main.patch` = `05-fix-vs-a59d633.patch`, 2 files, +21 −8 (`tools/site/improve_validate.py`,
`tools/site/selftest_improve.py`). No page, CSS, check, plan, snapshot, build or harness change.

## Change

- `improve_validate.PROGRESS_REASONS` gains a fifth fixed text, **`waiting for a GPU`** (a local model held for a GPU);
  `PAUSE_ONLY_REASONS` = (`usage limit`, `waiting for a GPU`): allowed with status `paused` only, refused with any
  other status. The rule sits in `progress_problems`, so it holds in the full validation and in the status-only read
  (`status_view`, the default pre-registration build) alike. The page renders it as `paused (waiting for a GPU)`.
- The text names no host or device. The producer (Improve, 36a3780) maps this hold to `waiting for its turn` today
  (GPU_WAIT_TEXT) and switches once the page accepts the new text; until then the live table shows the local models
  as `paused (waiting for its turn)` (below).

## What ran (exit codes)

- `selftest_improve.py` (`02-selftest.txt`): **exit 0, 97/97** (a59d633: 94). New: the `paused` state adds Qwen3.8-27B
  (on) `paused (waiting for a GPU)`; the default build's status table shows it (status view accepted, check_improve
  clean, no free text from the file); the full validation accepts the `paused` state (`usage limit` and
  `waiting for a GPU` when paused); fault "waiting for a GPU while not paused" (status `stopped`) refused by both the
  full validation and the status view, the page falls back to "Status unavailable".
- Full site (`01-build-and-checks.txt`): fresh `cp -a` of `~/.local/state/bg-site`, improve files refreshed with
  `snapshot.snapshot_improve` (byte-identical to the live `workspace/improve/out/improve.json`), then
  `build.py --state $STATE --out $SITE --no-image` with the branch's code (main + fix; `checks.run` inside): exit
  code, time and file as logged there. Then `improve_page.py --check $SITE` (page check), and a leak scan of the full
  build's `improve/index.html` and `data/v3/improve.json`: `check_improve` (test positions: id, board key, board;
  host and withheld marks), `checks.scan_file` (private strings), literal counts of `bariton`, `GPU-`, `withheld`,
  `SYNTHETIC`. The rendered real table is listed there.
- `06-gpu-reason-preview.txt`: a copy of the same REAL file with the three local holds' reason set to
  `waiting for a GPU` (what the exporter will write after the switch): status view accepted, check_improve clean,
  rows `paused (waiting for a GPU)`. Exit 0. (Done once on the 20:11 UTC copy.)
- Screenshots (`04-screenshots-log.txt`, `scripts/screenshots.py`), Playwright Chromium, light, 1280 and 375: REAL
  page top and status table from the full build (shown names: `common.relabel`, see review 1–2's README); SYNTHETIC
  none / running-1 / paused / done status tables (the selftest's standalone renders laid over the full build: raw
  setup ids, no relabel), the paused one with `paused (waiting for a GPU)`.

Rerun: `selftest_improve.py --workspace <main checkout>/workspace --keep $SELFTEST`; build as in 01; then
`~/.pyenv/shims/python3 mailbox/improve-status-review3/scripts/screenshots.py $SITE $SELFTEST`.
`MANIFEST.sha256` lists every file here.
