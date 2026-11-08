# leaderboard-ct review 2: the fixes for Zeki #2790

Branch `leaderboard-ct` is now HEAD a99a1ce. It was rebased onto `fix-filters` (e3dc886: the hidden home filter row, a separate change in mailbox/fix-filters). 5ca56de, the reviewed candidate, became 3094aa5 in the rebase. `delta-vs-5ca56de.patch` is `git diff 3094aa5 HEAD -- tools/site`, which is only this review's change; it touches 4 files (bg.css, model_identity.json, home.py, story.py). This is a candidate: not merged, not deployed.

**No model or statistics run.** Everything here comes from **retained fixtures**:
- `/tmp/lct/S.pkl`: the output of `build.compute()` at 19:18 UTC on the copy of the live state (results 7b40b30e; `scripts/compute_retained.py`, run once). `scripts/render_retained.py` renders from it. It re-reads only the learning page's data, which is a file read from the 19:35 state.
- Review 1's full renders of origin/main and 5ca56de.
- The live mirror as of 19:35Z.

`runs.txt` has every step with its output and **exit status**, and the expected status. The overall exit status is in its last line.

## The fixes

| # | Zeki #2790 / Main | Fix | Evidence |
|---|---|---|---|
| 1 | The representative at the top effort was chosen by best score | **Score-free:** among the setups at the model's highest effort, take the first in league order (the league of the setup's setups.json entry), then by setup name. `home.best_per_model` is back to its Nackgammon-only signature and no longer used by the leaderboard. The rule is stated under the table ("never its best score … Several setups at that setting: the first in league order, then by setup name (no score)") and in `evidence/1-setting-choice.md`. Programs and late entries use the same score-free rule. | **No ranked row changes against 5ca56de** (31 rows, same setups, same order): `evidence/checks.txt`, check "ranked rows unchanged against 5ca56de". `scripts/test_rules.py` (a) builds a tie on a copy of S: Gemma 4 31B (off) marked "on", so two setups share the top setting. The first by name is chosen (62.6) over the higher score (64.5). (b) Raising the 1017 checkpoint's judgement to 99 does not move the DeepSeek row. |
| 2 | Checkpoint merging by any 4-digit suffix | The name pattern is removed. `content/model_identity.json` holds the approved list, exactly `"DeepSeek V4.1 Flash 1017" → "DeepSeek V4.1 Flash"`. Any other name is its own model. | `test_rules.py` (c): a model renamed "Grok 4.7 1101" stays its own row. (d): the list is exactly that pair, and the DeepSeek row holds its 4 setups. The evidence check confirms the same list. |
| 3 | The phase test never changed the phase | The phase test now uses the **real visible control** (fix-filters made the filter row visible): More filters, then `select_option` on the Phase select, for each of the 5 phases and back to All phases, at 1280 and 390. Each time it checks: the select's value; every phase slot (rows and every cell) against that phase's `fragments/<league>-<phase>.html`; the leaderboard and Too safe text unchanged; the open DeepSeek expander still open; no dialog; no script error (none excluded). This runs over routed http, because bg.js fetches the fragments and file:// refuses that. There is **no phase address parameter** (bg.js reads `?league=` and `?type=` only). `?phase=race` is checked to leave All phases with every slot as loaded. | `browser.csv` rows "Phase via the control: …" and "Phase via the address" (14 rows, all ok). |
| 4 | Expander → parent tested only globally; no failing exit status | `evidence.py` derives each parent's expected alternatives from the data files (`evidence/expected-families.json`, 34 parents) and checks every parent's expander against them. The browser test clicks every parent's expander and compares the rows shown with that file, not with the page's aria-controls. Exit status: render_retained/render_site, evidence, review, test_rules and first_screen all **exit 1 on any failure**, and `run_review2.sh` records each step's status. **Negative control:** evidence.py against the 5ca56de render must exit 1 (its rule text is not score-free), and it does. | `runs.txt`. `evidence/checks.txt` (10 PASS, exit 0). `browser.csv`. |
| 5 | Links wording | `links.md` now opens with "No new errors among the checked links". It notes that 823 hrefs are unresolvable statically in both live and branch, that the 21 external links were not fetched, and that 3 share images are build.py-only (absent from origin/main's render too). | `links.md` |
| 6 | Mobile: no score on the first screen | **Above the table:** a one-line subtitle and one "fixed table" sentence. The rule and the All leagues note moved under the table. The caption is short.<br>**At ≤640 px:** the model, not the rank, is the sticky first column (115 px), the Setting and League headers lose their minimum width, and the bar column is narrower. | `first_screen.py`, opened at `#leaderboard`, 390×844 (see the table below). Screenshots: `screenshots/leaderboard-390-*.png`. |
| 7 | Late-entry wording | Stated precisely below and in `evidence/3-late-entries-question.md`. The pipeline checks it on the `LATE_ROWS = True` preview render: the 31 ranked rows are identical, GPT-6 Astra's ranked row stays medium, and 8 late rows are added. | `runs.txt` step "LATE_ROWS on adds …". |

First screen at `#leaderboard`, from `first_screen.py`:

| Render | Width | Table top | Rows fully in view | Score numbers fully visible |
|---|---:|---:|---:|---:|
| 5ca56de | 390 | 553 px | 2 | 0 |
| Branch | 390 | 308 px | 3 | 4 |
| 5ca56de | 1280 | 309 px | 5 | 6 |
| Branch | 1280 | 203 px | 7 | 7 |

## Results

- `checks.run` on the retained-S render: 0 failures, exit 0.
- **Fixture check:** the retained S gives exactly the 5ca56de full render's data files, 105 of 105, with the render time stamp normalised.
- **Numbers** (`numbers.md`): 0 differences.
  - 17,377 live home table cells; the same against origin/main's render.
  - 432 leaderboard cells.
  - 32 Too safe values.
  - 58 finding values.
  - 398 measure-chart values.
  - 111 other pages.
  - 105 data files.
- **Links:** no new errors among the checked links (3,604 checks).
- **Browser:** 54 of 54 ok (`browser.md`).
- **Screenshots:** 44, the changed views at 1280 and 390, light and dark (`screenshots/`). They include the shorter text above the table, the rule under the table, and the late-on preview.

## Open questions for Ümit (unchanged except 1)

1. **Late entries:** should the table show a separate "Late entries (not ranked)" group? The default is no.
   - Setting `LATE_ROWS = True` **adds** that grey group under the programs and changes **no ranked row**.
   - GPT-6 Astra stays ranked at **medium** (League 3); its late entry GPT-6 Astra (high) appears only as an extra row in the late group.
   - So the question is whether to show the group, not whether late entries change a ranked setting.
2. **The note:** Zeki's rank sentence replaces the overlap sentence. Please confirm.
3. **Other makers' colours:** grey, or the sibling site's family colours? The same list and judgement calls as in review 1 (Cygnet counted as Google).
4. **Nackgammon "one setting per model"** still uses best score. Should it switch to the highest-setting rule?
5. **Layout:** horizontal Too safe bars; the table scrolls sideways at 1280.
