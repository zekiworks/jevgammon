# deepseek-fix: DeepSeek V4.1 Flash's parameter line in the card's own terms (Zeki #3510, #3529)

Branch `deepseek-fix`, **9d3bd27**, one commit on origin/main 5e29f80 (small-models merged). **Not merged.** Narrow fix
ahead of params-align: two files, `tools/site/pages.py` (+6 −2: a `terms` field shown verbatim, linked) and
`tools/site/content/model_params.json` (two entries + the about line).

## What changed (render: only index.html; 3 leaderboard rows' box line)
| Row | origin/main | deepseek-fix |
|---|---|---|
| DeepSeek V4.1 Flash (main row #6 and its 'off' row) | `Parameters: 552B total / 16B active` | `Parameters: 552B backbone + 196B conditional memory; active 8B (prefill) / 16B (decode)` |
| Cygnet (Gemma 4 12B) (#29) | `11.95B` → google/gemma-4-12B-it (current) | `11.95B` → Google's card at the recipe's pinned revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7; the recipe (github.com/blockbrain-ai/cygnet-recipe) in its quote/note |

DeepSeek: `total_b` null and `terms` set: no total is stated or computed, so it is never a Small model (it was not one
before either; the ≤15B set is unchanged: Elephant-1, Cygnet, Decider Flash v1.2). The quote has the card's words at
README revision 314113f8a7dadb388215396ba5fbee2c610a04d6: '552B backbone parameters'; 'activate only 8B parameters per
token during prefill and 16B during decode'; 'Engram conditional memory (196B parameters, sparsely accessed via
token-based lookup)'; table '# Backbone Params 552B', '# Activated Params 8B / 16B'. DeepSeek V4.1 Flash 1017 (an
other-settings row) is unchanged ('not disclosed by maker'); it belongs to params-align's open list.
The Small models threshold (15B) stays the shared provisional one, not a human decision.

## What ran
- Frozen copy of the live state `/tmp/pa-state` (copied 2026-11-09 12:02:44Z under the update lock; data as of
  11:50Z, results 7acf91cb); the candidate built on `/tmp/ds-state`, a byte copy of it.
- `/usr/bin/python3 tools/site/build.py --state … --no-image`: origin/main 5e29f80 `build-main.log` **exit 0**;
  deepseek-fix 9d3bd27 `build-candidate.log` **exit 0** (checks.run 0 failures).

## Results
| Check | Result |
|---|---|
| Files (`compare.md`, manifests) | 2,552 each; only `index.html` differs. |
| Rows (`numbers.csv`, `params.csv`) | 63 rows (54 model + 9 program, 39 distinct models): all equal to origin/main outside the Parameters line; 0 number changes; 3 rows' line changed as above; every line = model_params.json; data-hl-small unchanged. compare exit 0. |
| Browser (`browser.md`) | **42/42, exit 0** at 375/390/1280 light+dark: filter states = data, the line on all 63 rows (hover/tap), no overflow. `deepseek-box.txt`: the DeepSeek box at 1280 and 375, overflow 0. |

## Files
`source.patch`, `render-narrow.diff` (the leaderboard section, 3 lines), `for-umit/deepseek-box-{1280,375}px-light.png`
(the open box), the rest of `for-umit/` and `screenshots/` as small-models' checks make them. `scripts/`: compare.py,
browser.py (small-models', adapted), shot_row.py.
