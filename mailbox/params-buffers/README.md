# params-buffers: parameters only, buffers out — the turkce #3592 reconciliation (follow-up to params-align)

Branch `params-buffers`: **one site commit 254a300 on origin/main f255bec** (params-align 6fb9b43 merged, Zeki GO
#3596). **Not merged.** One file changes: `tools/site/content/model_params.json`, with four entries and the about line.

## The definition (one, for every entry)
**A count includes only parameters.** A tensor that the model class registers as `nn.Buffer` is not a parameter and
is left out. The buffers are identified from the shard headers (`buffers.txt`, read with the fail-closed
`scripts/small_tensors.py`) and from huggingface/transformers @ b25568817a6cb458f6d8b180a32698c2ab11fd26:
- **Gemma 4** (`models/gemma4/modeling_gemma4.py`): `layer_scalar` at line 1351, `std_bias` and `std_scale` at lines
  2066–2067, all `nn.Buffer`.
- **LFM2.5** (`models/lfm2_moe/modeling_lfm2_moe.py`): `expert_bias` at line 205, `nn.Buffer`.
- **Qwen3.5** (`models/qwen3_5/modeling_qwen3_5.py`): `A_log` and `dt_bias` (lines 518, 522) are `nn.Parameter`, so
  they stay counted.

## The four reconciliations (exact counts now equal turkce's)
| Model | All tensor elements (old exact) | Buffers taken out | Parameters (new exact) | Shown: main → branch |
|---|---:|---|---:|---|
| Gemma 4 31B (@842da379) | 31,273,088,876 | model.vision_tower.std_bias 1,152 + std_scale 1,152 + 60 × layer_scalar 1 = 2,364 | **31,273,086,512** | 31.27B incl. its vision encoder (unchanged) |
| REAX 1.3 (@fa4bf7ee) | 57,359,724,636 | the same 2,364 in part G, a Gemma 4 31B checkpoint | **57,359,722,272** | part G 31.27B + part Q 26.09B (…) + decision head 1.3M (unchanged) |
| Winnow-12B (GGUF @0b5b7f98) | 11,907,350,576 (we had 11,907,350,320) | rope_freqs 256 + 48 × blk.N.layer_output_scale 1 (the GGUF name of layer_scalar) = 304 | **11,907,350,272** | 11.91B (unchanged) |
| Cygnet = google/gemma-4-12B-it (@707f0a3b) | 11,959,730,224 | 48 × layer_scalar 1 | **11,959,730,176** | **11.95B → "11.96B incl. its vision encoder; card: 11.95B"** |

- **Why ours differed:** we had excluded only Winnow's rope_freqs. We had not treated Gemma 4's per-layer
  `layer_scalar`, or the vision tower's `std_bias` and `std_scale`, as buffers.
- **Cygnet:** now follows the checkpoint rule like every other entry, with the card's figure beside the count (Main
  #3592 relay). It stays a Small model.
- **LFM2.5-24B-A2B:** its quote now names the 2,432 F32 elements left out as the 38 `expert_bias` buffers. Its
  figure (23,971,585,280 → 23.97B) is unchanged.
- **Other entries:** no other count changes. The Qwen3.8-27B listing shows no buffer.
- **Small models** (15B, provisional): unchanged, #27, #29, #34, #37.

## What ran
- **Frozen state:** a fresh copy of the live state, `/tmp/pb-state`, taken 2026-11-09 13:09:18Z under the update lock.
- **Builds:** `/usr/bin/python3 tools/site/build.py --state /tmp/pb-state --no-image`.
  - origin/main f255bec (git archive): `build-main.log`.
  - params-buffers 254a300: `build-candidate.log`.
  - Exit codes and checks.run are in the logs and under Results.
- **Compare and browser:** `scripts/compare.py` and `scripts/browser.py` (params-align's), run on the two renders.

## Results
## 1. Files
2552 files in origin/main's render, 2552 in the candidate's; only in one: none; different: ['index.html']

## 2. Rows and numbers
Leaderboard rows with a details box: origin/main 63, candidate 63.

Rows differing from origin/main beyond the Parameters line and data-hl-small: 0. Rows whose numbers (row + box, Parameters line out) differ: 0.

Home page outside the leaderboard table: text identical.

- **Builds:** both exit 0, so checks.run had 0 failures (data as of 13:05Z, results 6b6c89a6).
- **Rendered suite-bar.css:** sha256 7c686c6d…bca in both renders, unchanged.
- **Rows:** 63 = 54 model + 9 program rows, 39 distinct models. 0 number changes outside the Parameters lines.
- **Displayed change:** one Parameters line, Cygnet (#29): `11.95B` → `11.96B incl. its vision encoder; card: 11.95B`,
  now linked to the checkpoint tree at 707f0a3b (`render-narrow.diff`). Every line matches model_params.json, and
  Small flags are unchanged (`params.csv`). compare exit 0.
- **Browser:** **42/42, exit 0** (`browser.md`), at 375/390/1280 px in light and dark.
  - The filter states match the data; Small models shows #27, #29, #34 and #37.
  - The Parameters line is on all 63 rows, by hover and by tap.
  - No overflow and no script errors.

## Files
- **Diffs:** `source.patch`, `render-narrow.diff`.
- **Comparison:** `compare.md`, `numbers.csv`, `params.csv`, `manifest-*.tsv`.
- **Browser:** `browser.md`, `browser.csv`, `for-umit/`, `screenshots/`.
- **Count receipts:** `buffers.txt`, `winnow-gguf-count.txt`, `reax-headers.txt`.
- **Logs and scripts:** `build-*.log`, `scripts/`.
