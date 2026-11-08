# "Did they improve?" page candidate: review (ImprovePage, 2026-11-08)

**Candidate:** branch `improve-page`, commit **c7fa237**, on origin/main eb8d8c0 (plan `mailbox/Did they improve - plan
2026-11-08.md` at 0799b46, sha256 `1edda547494e4fa85d678ba36d2619b2e1a77de6f9554d404f16eff59c4d4864`). Pushed, not
merged. `improve_page.PREREGISTRATION_ONLY = True` is the default: the live build never reads `improve.json`; the
results view is rendered here with the review flag `--with-results` only. Render-only: no `build.py`/`update.sh`, no
server, timer, deploy or model call. Rerun: `bash mailbox/improve-page-review/scripts/run_review.sh` (main checkout).

## Files (branch, against origin/main)

| File | What |
|---|---|
| `tools/site/improve_page.py` | data builder + page (`improve/`, data file `data/v3/improve.json`), the learning page's structure and helpers (redaction of private strings, overlay, status line, `--check`) |
| `tools/site/improve_validate.py` | closed-schema validator of `improve.json` (learning_validate's `check`, `untrusted` and public/private problems reused) |
| `tools/site/checks.py` | check 8, `check_improve` (also in `checks.run`) |
| `tools/site/snapshot.py`, `update.sh` | `snapshot_improve`: `workspace/improve/out/improve.json` and `out/prompt/` (→ `STATE/improve/harness-prompt/`), the plan's lesson prompt (`workspace/learning-pilot/lessons_*.txt` → `STATE/improve/prompt/`); key `"improve"` in the summary and `improve:$IMPROVE` in the change key, so each new `improve.json` rebuilds the site live |
| `tools/site/build.py`, `pages.py` | `S["improve"]`, the data file, the page, the Experiments card (`#improve`; status "Pre-registration"), `improve/` under the Experiments tab |
| `tools/site/assets/bg.css` | 3 lines: room for the long cells of the models table |
| `tools/site/selftest_improve.py` | SYNTHETIC states, 29 injected faults in `improve.json`, 12 injected page faults |

Note: `content/experiments.json` holds the Method page's method-experiment numbers, not the Experiments cards; the
cards are `pages.experiments_page`'s list (where the learning page's card is), so the card was added there.

## What the page shows

**Pre-registration view (the default build; also what a refused file falls back to):** the heading "Did they improve?
(pre-registered)", the commitment line "Results will be published whichever way they go." at the top, the plan file
and its sha256; then
1. **The rule**: plan §2 verbatim (with "This is an operational threshold, not a statistical test and not statistical
   evidence.");
2. **Models and status**: the line **no shared seed; same settings as the leaderboard** (plan §4); the 15 chat models
   from plan §3's table (setup, its label: DeepSeek's "tested checkpoint: original V4.1 Flash", GPT-6 Astra's "late
   entry"; maker; setting; route, DeepSeek's "Fireworks" with its API setup behind "API setup"; the plan's status;
   "no result yet"); the plan's two notes ("Games played with lessons count nowhere …", "Provider-side load is not
   observable, and the page says so."); a second table: decision models ("not tested: cannot write lessons", the 22
   names as the plan writes them), Cygnet ("not tested", the plan's #3111 paragraph), the Gemma pilot row ("pilot
   (different design)", its own verdict **not met**, 25.0 → 33.3 (+8.3), right safety 96.0 → 97.1 (+1.1), error rate
   55.6 → 46.4; "not comparable (different design)" in this rule's column) and the plan's pilot paragraph;
3. **Lesson prompt and test set**: the prompt's sha256 `d7550015…` (render fails unless the files hash to the plan's),
   both prompt files verbatim, the test set's sha256 `6c92e741…` ("200 positions (never published)");
4. every other plan section verbatim (§1, §3–§11: routes and settings table, design, money stop rules with the $110
   cap, the $55 share and the pause rules, schedule, outputs). Private strings in the plan (3 occurrences: the GPU
   host's name, `base_url`) are replaced by "[withheld: private address]" by the learning page's redaction, as the
   site's private-strings rule requires.

**Results view (`--with-results`; shown only when improve_validate accepts the file):** a status line ("N of 15 models
with a verdict · running · paused · incomplete or stopped", last update), billed so far against $110; the models table
with, per model: risks found before → after, change, own range, threshold, right safety before → after (change), error
rate before → after, answers before/after (valid of expected, risk-pays and safety-pays denominators, invalid, failed,
answer rate), cost (billed and OpenRouter-reported; subscriptions "$0 billed (subscription quota)" with the
API-list-price equivalent; local "$0 API spend; local compute cost not estimated."), and Yes/No or the status
("running, n of 5 series", "paused: reason", "stopped: reason", "incomplete: reason"); sorted by the change in risks
found, rows without a change after (plan order). Tapping a model's name opens its block under "Lessons and every
test": every test (E1–E3, each series' T10) and every series' lessons per game (empty lesson sets shown as such).
Before/after/change/range/threshold/verdict are computed by the site (improve_validate.scores), never read from the
file; checks.check_improve recomputes them independently from the data file and compares every cell.

**Refused file:** the pre-registration view plus "Data refused." with the failed fields; names taken from the file
(unknown keys, a setup outside the plan) are "[name withheld]" on the page and in full on stderr only.

## States and results

| State | Source | Result |
|---|---|---|
| default-preregistration | the branch's whole-site render (default build), STATE/improve with prompt/ only | Pre-registration view; reads only `prompt/` (02, audit hook) |
| none | no improve.json, `--with-results` | Pre-registration view, status "Not started" |
| running-1 | SYNTHETIC: Qwen3.8 Flash (off), E1 + S1 done | live numbers, "running, 1 of 5 series", no Yes/No |
| complete-yes | SYNTHETIC: Qwen complete, +6.0 > threshold 5.0, safety −1.4 | Yes |
| complete-no | SYNTHETIC: GLM-5.3 complete, +5.1 vs own range 6.0 | No |
| mixed | SYNTHETIC: Qwen Yes, GLM No, Kimi paused, DeepSeek running mid-series, Gemini stopped | order and every status |
| refused | complete-yes with a test position's board in a lesson | refused; pre-registration view + note |
| REAL-dry-run-asis | the harness's own `workspace/improve/out-dry/improve.json` (dry run, no model call), as written | refused: `protocol.plan_sha256` is the earlier plan's (309adc7a…) |
| REAL-dry-run-rehashed | the same with `plan_sha256` set to the current plan's (the only change) | accepted: "running, 2 of 5 series" |

| File | What | Result |
|---|---|---|
| `00-states.txt` | STATE/improve as snapshot_improve writes it | prompt/ only (no improve.json on disk yet) |
| `01-site-renders-and-checks-run.txt` | whole-site renders of origin/main and the branch (same state), `checks.run` on the branch's, `diff -rq` | 0 failures; only `data/index.html`, `data/manifest.json`, `experiments/index.html` differ, `improve/` and `data/v3/improve.json` added |
| `02-page-checks.txt` | `improve_page.py --check` in all 9 states (numbers trace, links/ids, private strings, check_improve with the leak scan); audit-hook proof that the default build opens no improve.json; leak scan of the whole built site | 0 failures in every state; default build opens only `prompt/lessons_*.txt`; leak scan: 600 strings (200 positions × id, board key, board) over 2,552 files, 0 hits |
| `03-selftest-faults.txt` | `selftest_improve.py`: 5 states, 29 injected `improve.json` faults (bad plan/prompt/test-set hash, counts that do not add up, denominators, answer rate, share range, unknown keys with canaries, setup outside the plan, verdict gate: 4 series / 199 of 200 / 9 lessons / 2 empty runs, steps order, test position (board, board key) in a lesson, cut rule, billing, $110, missing reason, removed `cumulative_cap_usd`, duplicate setup, not JSON) + the harness prompt missing; 12 page faults | 52/52 as expected (exit 0) |
| `05-screenshots-log.txt`, `screenshots/` | Playwright Chromium, light, 1280 and 375 wide (the learning reviews' method) | 44 PNGs (22 shots × 1280/375), no page wider than the viewport |

## Not rendered / open

- The plan's §3 status cells are rendered as written; Improve's note that the local models' status is "waiting: GPU 3
  (bariton)" is not in the plan's table (it says "waiting for a GPU"), and "bariton" is a private string the site
  withholds anyway.
- Every number in the results states is SYNTHETIC; no real run exists yet. The REAL dry-run file is the harness's dry
  run (placeholder lessons, no model call).
- The page checks rely on the private `workspace/learning-pilot/test_set.json` (as the learning page's): with
  `improve.json` present and the test set missing, the build fails (learning_page.TestSetRequired).
