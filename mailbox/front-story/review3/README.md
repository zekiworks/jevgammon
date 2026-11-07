# review3 (Zeki #2737): two narrow fixes on front-story

Branch `front-story` is at 8f84e36. `delta-vs-ef3ed0e.patch` is `git diff ef3ed0e HEAD -- tools/site`: 3 files, +51/−25.

## The fixes

1. **Nackgammon model types now fail the build if missing or unknown** (`home.nack_views`).
   - The resolved `model_type` must be exactly one of `NACK_KINDS`:
     - the four types in setups.json: `decision model`, `chat model, answer-letter probabilities`, `chat model, one letter`, `program`;
     - `chat model`, which is Terra's unchanged record in `content/nack_setup_types.json`.
   - A missing metadata object, a missing `model_type` or any other string raises `ValueError`. `kind()` is no longer used here; before, it filed any unknown non-empty type under Chat.
2. **One selection rule**: `home.best_per_model(S, eligible=None)`.
   - Each model's setup with the highest stored All-leagues risk judgement, scored per (league, setup).
   - On an exact tie, the first in league order (all_rows' order) wins, via a strict `>`.
   - `story.best_settings` (the leaderboard) and `nack_views` (the Nackgammon per-model view) both call it. The Nackgammon view restricts the candidates to the settings this test asked.
   - The name-keyed dict, which let a later league's score overwrite an earlier one, and the tie-break by alphabetically last name are both removed.
   - The note under the Nackgammon table now states the tie rule.

## Tests (saved output: `test_selection.txt`; script: `../scripts/test_selection.py`)

The tests import the branch's `tools/site` modules (home, story) and rebuild S from the last branch render's published data files: `data/v3/league-N.json` and `data/setups.json` from `/tmp/fs/out-branch`, plus the content file `nack_paired_results.json`. These are the inputs `nack_views` and `best_settings` read.

There was **no build, no `compute()`, no full re-render, and no model or statistics run.** A re-render was not needed: test (c) shows the fixed rule gives the same per-model selection as the rendered page, so the page HTML does not change. `data-nack-chosen` in the render matches the new `chosen` exactly.
- **(c) PASS, 26 models:** each per-model setup is checked by identity (model, setup and league).
  - 19 equal the leaderboard's selected setup.
  - GPT-6.1 Terra has no leaderboard row, because it played in no league.
  - 6 models' leaderboard setting was not asked in the Nackgammon test: Claude Sonnet 5.5, DeepSeek V4.1 Flash, GPT-6 Astra, Gemini 3.8 Flash, Gemini 4 Argon, Qwen3.8-27B (each leaderboard-selected at a setting the test did not ask). For each, the per-model view equals the same rule run over the asked settings.
- **(d) PASS, synthetic:** model M with A (League 1, 70), C (League 1, 75; League 2, 50) and B (League 2, 70).
  - Both views pick C at League 1. The old name-keyed rule picked B, because C's League 2 row overwrote its League 1 score.
  - With C in League 1 lowered to 60, A and B tie at 70. Both views pick A (first in league order); the old rule picked B (alphabetically last).
