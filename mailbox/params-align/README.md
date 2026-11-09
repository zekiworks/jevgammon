# params-align review (reissued for Zeki #3574): parameter figures by the three sites' rule

Branch `params-align` = **one commit, 6fb9b4313661302a48de188e07c957ca5987e72d, on origin/main
98effa3af62f76aeaf92fb9e21de84f0ccd782e8**. That main already has the deepseek-fix (merge 7b35e40) and the shared
suite-bar.css (6d9d06d via 8eec5da). **Not merged.** This replaces the earlier params-align packets: a482971 and dda60ed,
built on 5e29f80/9d3bd27, are **historical**. That base is why their source patch appeared to revert suite-bar.css.

## Scope (source.patch, source-stat.txt: `git diff origin/main..params-align -- tools/site`)
- **Three files only.** `tools/site/content/model_params.json`, plus one comment line each in `pages.py` and
  `story.py`. The comments say 15B is the three sites' shared **provisional** threshold (#3471/#3473), not a human
  decision. No layout, CSS or feature change.
- **Rendered suite-bar.css is unchanged.** It is byte-identical in both renders and equal to the shared file: sha256
  `7c686c6d5be33c47b1069436067c20da491bfe9863e43e56fb348eb70ed11bca`, 3,365 bytes (both manifests).

## Rule applied (logic #3508/#3550, Main #3506, turkce #3552 wording, Zeki #3529/#3574)
- **What is counted:** the released checkpoint, or the release composition, at the stated revision. The count is
  logical: the sum of tensor shapes. Never counted: packed storage elements, quantization scales, buffers, or an
  adapter or assistant file on its own. The scope is written out.
- **Run identity:** an actual-run identity is claimed only where it is evidenced. None of these figures claims to be
  the model as loaded in our runs.
- **Display:**
  - Named parts are shown: "incl. its vision encoder", or "backbone X + decision head Y".
  - The maker's own text figure stands beside a count where it differs ("card: 27B").
  - A card that gives parts but no whole-model total is shown in its own terms (DeepSeek V4.1 Flash).

## Changed figures (pinned base main 98effa3 → params-align 6fb9b43, same frozen state)
Live is reported as 9d3bd27 (Main / Zeki #3557). I did not inspect production. `git diff 9d3bd27 98effa3` is empty for
model_params.json, pages.py and story.py, so this table is also the change against the reported live state. Nineteen rows change; DeepSeek V4.1 Flash and Cygnet are already in main and do not change here.

| Row | Model | main 98effa3 (= live after deepseek-fix) | params-align 6fb9b43 | Small (≤15B) main → new |
|---|---|---|---|---|
| hl-11-box (main) | Gemma 4 31B | 30.7B | 31.27B incl. its vision encoder | – → – |
| hl-11-1-box (other) | Gemma 4 31B | 30.7B | 31.27B incl. its vision encoder | – → – |
| hl-13-box (main) | Base Labs Mammoth-1 | 27B | 27.36B incl. its vision encoder; card: 27B | – → – |
| hl-14-box (main) | Drex Max v1 | 27B | backbone 26.09B incl. its vision encoder + decision head 1.3M; card: 27B | – → – |
| hl-15-box (main) | Qwen3.8-27B | 27B | 27.78B incl. its vision encoder; card: 27B | – → – |
| hl-15-1-box (other) | Qwen3.8-27B | 27B | 27.78B incl. its vision encoder; card: 27B | – → – |
| hl-17-box (main) | REAX 1.3 | not disclosed by maker | part G 31.27B + part Q 26.09B (each incl. its vision encoder) + decision head 1.3M | – → – |
| hl-23-box (main) | Fastino GLiDE v1.2 | 26.09B | backbone 26.09B incl. its vision encoder + decision head 1.3M | – → – |
| hl-24-box (main) | Drex 2.0 | 35B total / 3B active | 35.11B incl. a vision tower the card says is dropped on load; card: 35B; 3B active | – → – |
| hl-24-1-box (other) | Drex 2.0 | 35B total / 3B active | 35.11B incl. a vision tower the card says is dropped on load; card: 35B; 3B active | – → – |
| hl-25-box (main) | Decider v1.2 27B | 27B | backbone 26.09B incl. its vision encoder + decision head 1.3M; changelog: 27B | – → – |
| hl-27-box (main) | Base Labs Elephant-1 | 9B | 9.41B incl. its vision encoder; card: 9B | yes → yes |
| hl-28-box (main) | Clef | 27B | backbone 27.36B incl. its vision encoder + joint head 128.1M; card: 27B | – → – |
| hl-30-box (main) | Decider v1.1 27B | 26.09B | backbone 26.09B incl. its vision encoder + decision head 1.3M | – → – |
| hl-34-box (main) | Winnow-12B | not disclosed by maker | 11.91B | – → yes |
| hl-36-box (main) | LFM2.5-24B-A2B | 24B total / 2.45B active | 23.97B total / 2.45B active | – → – |
| hl-36-1-box (other) | LFM2.5-24B-A2B | 24B total / 2.45B active | 23.97B total / 2.45B active | – → – |
| hl-37-box (main) | Decider Flash v1.2 | 4B | backbone 4.54B incl. its vision encoder + decision head 0.7M; changelog: 4B | yes → yes |
| hl-38-box (main) | Open-Jev 27B v1.1 | not disclosed by maker | 27.80B: Qwen3.8-27B base 27.78B + adapter and head 15.47M (the repo holds only the adapter and head) | – → – |

## Evidence for each figure
Each entry's `quote` in model_params.json gives the repo, the files, the revision, how it was counted and the maker's
own text. `note` says why.

**Elephant-1, Mammoth-1, Gemma 4 31B, Qwen3.8-27B: single checkpoints with a vision encoder**
- **Count:** Hugging Face's safetensors total for the maker's repo at the stated revision.
- **Vision part:** Elephant-1's is 456,010,480 of 9,409,813,744, from the file header (`elephant-vision.txt`). The
  other three checkpoints' indexes list 333–356 vision tensors.
- **Revisions:** Gemma and Qwen were read at the repo's current revision; the run's revision is not recorded.

**Decider v1.1, Decider v1.2, Decider Flash v1.2, Drex Max v1, GLiDE v1.2 and Clef: backbone plus a separate head**
- **Backbone:** the shards in model.safetensors.index.json, vision encoder included.
- **Head:** read from its file header (`head-files.txt`): readout.safetensors (1,305,600; Flash 652,800) or Clef's
  joint_head.safetensors (128,056,324).
- **Decider v1.2:** its index is byte-identical at cce0f3f8 and 225c913d (`receipts/`, same sha256), and the head is
  the same at both revisions.
- **GLiDE v1.2:** model-visual.safetensors (460,730,096) is already in the backbone index, so it is not counted twice.

**REAX 1.3 = 57,359,724,636**
- part-g: 31,273,088,876, the sum of its 13 shard headers (`reax-headers.txt`).
- part-q: 26,085,330,160, the `total_parameters` in its index (`receipts/reax-part-q-index.json`).
- part-q/readout.safetensors: 1,305,600.
- This is a sum of the named released components.

**Drex 2.0 = 35,107,181,936 at e6466744**
- Total from `receipts/drex-v2.0-e6466744-index.json`. The vision tower is 446,571,248: 333 tensors in shard 16
  (`drex2-vision.txt`).
- This is a **checkpoint-scope count** that includes a tower the card says is dropped on load. It is not a verified
  count of the model as loaded in our hosted or local runs. No subtracted runtime figure is published.

**Open-Jev 27B v1.1 = 27,796,899,569 (27.80B)**
- This is the **release composition**: base + adapter and head.
- **Adapter repo:** ZefanCai/Open-Jev-27B-v1.1 @ 28cf73067d5b337860bbef3c85b8b82ba8730956.
  - release-manifest.json: sha256 19a4f2ad…0a1f5, in `receipts/`. The local checkout's copy has the same bytes.
  - adapter_model.safetensors: sha256 1c857224…8a81.
  - head.pt: sha256 76e382f1…96b4.
  - The card states the 15,471,617 trained parameters.
- **Base:** Qwen/Qwen3.8-27B @ 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0, 27,781,427,952. This is the whole released
  checkpoint, vision encoder included. The adapter targets the text backbone.
- **Where the base pin comes from:** the release manifest. The local Open-Jev checkout's download script fetches the
  same revision. It does **not** come from our league run's record, which does not name a revision.

**Winnow-12B = 11,907,350,320 parameters (11.91B)**
- **File:** the maker's gguf/Winnow-12B-Q8_0.gguf @ 0b5b7f98, LFS sha256 b710efc4…18ea. It is the same file the
  winnow-inference repo pins at d4631fb (logic #3534).
- **What was read:** the header only, from a 206 range response, plus the whole local copy with the same sha256
  (`winnow-gguf-count.txt`).
- **Counted:** 667 tensors, text model only. The 256-element rope_freqs buffer is excluded; all tensor elements come
  to 11,907,350,576. Q8_0 storage blocks and scales are not counted.

**LFM2.5-24B-A2B**
- BF16 23,971,585,280 at 3dc4cd09, with 2,432 F32 buffer elements left out.
- 2.45B active, from the card.

**Unchanged entries**
- DeepSeek V4.1 Flash (the card's own terms) and Cygnet (11.95B, pinned card) are as in main.
- DeepSeek V4.1 Flash 1017 stays "not disclosed by maker".
- Kimi K3.1 Pro 2.8T / 104B is the card's figure; the experts are stored packed.
- GLM-5.3 753.33B is the repository total. Its 19,456 F32 elements may be scales or buffers, which would not change
  the rounded figure.
- The closed API models stay "not disclosed by maker".

## Small models (threshold 15B, provisional)
- **main:** #27 Elephant-1, #29 Cygnet, #37 Decider Flash v1.2.
- **params-align:** **#27, #29, #34 Winnow-12B, #37.** Winnow joins.

## What ran
- **Frozen state:** a fresh copy of the live state, `/tmp/pa2-state`, taken 2026-11-09 12:43:41Z under the update lock
  (data as of 12:35Z, results 41349961).
- **Builds:** `/usr/bin/python3 tools/site/build.py --state /tmp/pa2-state --no-image`, on the same state.
  - main 98effa3 (git archive): `build-main.log`, **exit 0**.
  - params-align 6fb9b43: `build-candidate.log`, **exit 0**. So checks.run had 0 failures.
- **Receipts:** fetched with `scripts/st_header_count.py`. It now fails closed: it requires HTTP 206 and an exact
  Content-Range, makes bounded reads, and caps the header size at 64 MiB. Small index and manifest files were saved
  whole under `receipts/` (`receipts/SOURCES.txt` lists them with their sha256). `scripts/gguf_count.py` reports all
  tensor elements and the parameter-only total separately.

## Results (all regenerated from the pinned base)
## 1. Files
2552 files in origin/main's render, 2552 in the candidate's; only in one: none; different: ['index.html']

## 2. Rows and numbers
Leaderboard rows with a details box: origin/main 63, candidate 63.

Rows differing from origin/main beyond the Parameters line and data-hl-small: 0. Rows whose numbers (row + box, Parameters line out) differ: 0.

Home page outside the leaderboard table: text identical.

- **Rows:** 63 = 54 model + 9 program rows; 39 distinct models.
- **Numbers:** 0 number changes outside the Parameters lines (`numbers.csv`).
- **Parameters lines:** every line matches model_params.json, and data-hl-small sits exactly on the ≤15B rows
  (`params.csv`). compare exit 0.
- **Narrow diff:** `render-narrow.diff` shows 19 Parameters lines and 1 row attribute (Winnow's data-hl-small).
- **Browser:** **42/42, exit 0** (`browser.md`), run by the owner at 375/390/1280 px in light and dark on the pinned renders.
  - Each filter state shows exactly the rows the data says; Small models shows #27, #29, #34 and #37.
  - The Parameters line is on all 63 rows, by hover and by tap.
  - The box stays inside the window, nothing overflows sideways, and there are no script errors.

## Files
- **Diffs:** `source.patch`, `source-stat.txt`, `render-narrow.diff`.
- **Comparison:** `compare.md`, `numbers.csv`, `params.csv`, `manifest-main.tsv`, `manifest-candidate.tsv`.
- **Browser:** `browser.md`, `browser.csv`, `for-umit/`, `screenshots/`.
- **Count receipts:** `head-files.txt`, `reax-headers.txt`, `drex2-vision.txt`, `elephant-vision.txt`,
  `winnow-gguf-count.txt`, `receipts/`.
- **Logs and scripts:** `build-*.log`, `scripts/` (compare.py, browser.py, st_header_count.py, gguf_count.py).

## Parameter table (all 39 models)
| Model | Shown | Source | How counted, revision, maker's text (quote) | Why (note) |
|---|---|---|---|---|
| Base Labs Elephant-1 | 9.41B incl. its vision encoder; card: 9B | https://huggingface.co/baselabs/elephant-1/tree/b3f8a93462fb1051a9de031e94a7ff380e254072 | baselabs/elephant-1 @ b3f8a93462fb1051a9de031e94a7ff380e254072, model.safetensors (one file, no separate head file): 9,409,813,744 logical parameters (Hugging Face's safetensors total; language model 8,953,803,264 + vision encoder 456,010,480 per logic). Maker's text: 'a 9B parameter decision model'. | Checkpoint total at the pinned revision (#3508 rule); same as logic's model_sizes.json 'Elephant-1'. |
| Base Labs Mammoth-1 | 27.36B incl. its vision encoder; card: 27B | https://huggingface.co/baselabs/mammoth-1/tree/61cec44c281c693992e3d6ebeb44dd3402dfa186 | baselabs/mammoth-1 @ 61cec44c281c693992e3d6ebeb44dd3402dfa186, model.safetensors.index.json shards (no separate head file): 27,356,728,560 logical parameters (Hugging Face's safetensors total; language model 26,895,998,464 + vision encoder 460,730,096 per logic). Maker's text: 'a 27B parameter decision model'. | Checkpoint total at the pinned revision (#3508 rule); same as logic's model_sizes.json 'Mammoth-1'. |
| Celeris-1 Decision | not disclosed by maker | https://celeris.ai/celeris-1-decision | Launch post gives benchmarks, latency, price; no parameter count | Closed API. |
| Claude Fable 5.1 | not disclosed by maker | https://www.anthropic.com/claude-fable-and-mythos-5-1 | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | System card PDF (Fable 5.1 / Mythos 5.1) searched in full text. |
| Claude Opus 5.5 | not disclosed by maker | https://www.anthropic.com/claude-opus-5-5 | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | System card PDF searched in full text. |
| Claude Sonnet 5.5 | not disclosed by maker | https://www.anthropic.com/claude-sonnet-5-5 | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | System card PDF searched in full text. |
| Clef | backbone 27.36B incl. its vision encoder + joint head 128.1M; card: 27B | https://huggingface.co/Cloudflare/clef/tree/cfddda043dd190ef3b01cff449d5ee8cff1e8ec6 | Cloudflare/clef @ cfddda043dd190ef3b01cff449d5ee8cff1e8ec6: backbone 27,356,728,560 logical parameters (model.safetensors.index.json shards, language model and vision encoder; Hugging Face's safetensors total) + joint head 128,056,324 (joint_head.safetensors, 122 tensors, its header's tensor shapes) = 27,484,784,884. Maker's text: the card: 'Clef is a 27B multimodal model…'; Cloudflare changelog '27B'. | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. Revision: the repo's current one (the run's revision is not recorded). |
| Cygnet (Gemma 4 12B) | 11.95B | https://huggingface.co/google/gemma-4-12B-it/blob/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7/README.md | Card at the pinned revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7, '12B Unified' column: '/ **Total Parameters** / ... / 11.95B /'. Recipe: https://github.com/blockbrain-ai/cygnet-recipe (Google's gemma-4-12B-it, 'no fine-tuning', vLLM --revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7). | Kept at the maker card's 11.95B at the recipe's pinned revision 707f0a3b (Zeki #3510); recipe https://github.com/blockbrain-ai/cygnet-recipe. Not an E-series model, no effective figure. |
| Decider Flash v1.2 | backbone 4.54B incl. its vision encoder + decision head 0.7M; changelog: 4B | https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.2/tree/9ff7cf9838e59df461c276b7699d56b244d2af58 | perplexity-ai/pplx-decider-flash-v1.2 @ 9ff7cf9838e59df461c276b7699d56b244d2af58: backbone 4,539,265,536 logical parameters (model.safetensors.index.json shards, language model and vision encoder; Hugging Face's safetensors total) + decision head 652,800 (readout.safetensors, its header's tensor shapes) = 4,539,918,336. Maker's text: changelog: '`pplx-decider-flash-v1.2` is a new 4B decision model at \$0.01 per million input tokens.' | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. |
| Decider v1.1 27B | backbone 26.09B incl. its vision encoder + decision head 1.3M | https://huggingface.co/perplexity-ai/pplx-decider-v1.1-27b/tree/14c9d90137962d300f3de95633f7b6535e80c5ce | perplexity-ai/pplx-decider-v1.1-27b @ 14c9d90137962d300f3de95633f7b6535e80c5ce: backbone 26,085,330,160 logical parameters (model.safetensors.index.json shards, language model and vision encoder, 333 vision tensors in the index; Hugging Face's safetensors total) + decision head 1,305,600 (readout.safetensors, its header's tensor shapes) = 26,086,635,760. Maker's text: the card states no count. | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. |
| Decider v1.2 27B | backbone 26.09B incl. its vision encoder + decision head 1.3M; changelog: 27B | https://huggingface.co/perplexity-ai/pplx-decider-v1.2/tree/cce0f3f80033e9d89d80831d5281fd72124aacce | perplexity-ai/pplx-decider-v1.2 @ cce0f3f80033e9d89d80831d5281fd72124aacce (same counts at 225c913ddc8761a8264f04f64548e1f97e443eb3): backbone 26,085,330,160 logical parameters (model.safetensors.index.json shards, language model and vision encoder; Hugging Face's safetensors total) + decision head 1,305,600 (readout.safetensors, its header's tensor shapes) = 26,086,635,760. Maker's text: changelog: '`pplx-decider-v1.2` replaces `pplx-decider-v1.1-27b` as the 27B decision model'. | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. |
| DeepSeek V4.1 Flash | 552B backbone + 196B conditional memory; active 8B (prefill) / 16B (decode) | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash | README at revision 314113f8a7dadb388215396ba5fbee2c610a04d6: 'a multimodal Mixture-of-Experts (MoE) model with 552B backbone parameters'; 'activate only **8B parameters per token during prefill** and **16B during decode**'; 'Engram conditional memory (196B parameters, sparsely accessed via token-based lookup)'; table '# Backbone Params 552B', '# Activated Params 8B / 16B'. | The card's own terms (Zeki #3510): no whole-model total is stated, none is computed, so not a Small model. The checkpoint's safetensors total (763,205,315,794) counts packed FP4 experts as I8 elements, not parameters. |
| DeepSeek V4.1 Flash 1017 | not disclosed by maker | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017 | Card states only: 'DeepSeek-V4.1-Flash-1017 is a minor update to DeepSeek-V4.1-Flash'; no parameter count on the 1017 card. | Not filled from the V4.1-Flash card (lineage). HF safetensors total 763,205,315,794 is identical to V4.1-Flash's and inflated by packed FP4 (I8) storage, so not a parameter count. If Main accepts 'minor update' as same architecture, V4.1-Flash's 552B / 8B-16B applies. |
| Drex 2.0 | 35.11B incl. a vision tower the card says is dropped on load; card: 35B; 3B active | https://huggingface.co/nace-ai/drex-v2.0/tree/e646674476744e3826caf62b834054151e2aba51 | nace-ai/drex-v2.0 @ e646674476744e3826caf62b834054151e2aba51, model.safetensors.index.json (16 shards; 'total_parameters': 35,107,181,936, = Hugging Face's safetensors total, BF16); the vision tower is 333 tensors in model-00016-of-00016.safetensors, 446,571,248 logical parameters from that shard's header (drex2-vision.txt). Maker's text: 'mixture-of-experts ... 40 layers, 256 experts and 8 active per token: 35B parameters in total, about 3B active per token'; the card says the vision tower is dropped on load (text use). | Released-checkpoint count at the stated revision, scope written out (logic #3550, turkce #3552, Zeki #3574): the checkpoint total incl. the vision tower, which the card says is dropped on load (text use); not a verified count of the model as loaded in our hosted or local runs. 3B active from the card. Applies to the hosted and local rows. |
| Drex Max 1.1 | not disclosed by maker |  | Maker's model reference, Drex Max guide and developer page list API id drex-max-v1.1, limits and pricing, but no parameter count; no open weights. | Not inferred from Drex Max v1 (27B). |
| Drex Max v1 | backbone 26.09B incl. its vision encoder + decision head 1.3M; card: 27B | https://huggingface.co/nace-ai/drex-max-v1/tree/cac65e1982a0237e996419ba559004522d9a33ac | nace-ai/drex-max-v1 @ cac65e1982a0237e996419ba559004522d9a33ac: backbone 26,085,330,160 logical parameters (model.safetensors.index.json shards, language model and vision encoder; Hugging Face's safetensors total) + decision head 1,305,600 (readout.safetensors, its header's tensor shapes) = 26,086,635,760. Maker's text: the card: 'a dense 27B-parameter model'. | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. |
| Fastino GLiDE | not disclosed by maker |  | Hosted API (responses name glide_v2); the launch post and v1.2 post give no parameter count for the hosted model; the v1.2 post only says post-trained from 'an open weight 27B-class hybrid language model'. | Hosted glide_v2 is not documented as the same checkpoint as the HF fastino/GLiDE weights, so the HF safetensors total is not applied. |
| Fastino GLiDE v1.2 | backbone 26.09B incl. its vision encoder + decision head 1.3M | https://huggingface.co/fastino/GLiDE-27B/tree/a7e45896be7c96ba3354891da790c5ec99c30b6c | fastino/GLiDE (now fastino/GLiDE-27B) @ a7e45896be7c96ba3354891da790c5ec99c30b6c: backbone 26,085,330,160 logical parameters (model.safetensors.index.json shards, language model in 5 shards and vision encoder model-visual.safetensors 460,730,096, both in the index; Hugging Face's safetensors total) + decision head 1,305,600 (readout.safetensors, its header's tensor shapes) = 26,086,635,760. Maker's text: the card states no count; Fastino's blog: '27B-class'. | Checkpoint total of the maker's released repo at the pinned revision (logic #3508 rule, Main #3506; Zeki #3529: component scope shown). Same figure as logic's model_sizes.json where it has the model. |
| GLM-5.3 | 753.33B total; active not disclosed by maker | https://huggingface.co/api/models/zai-org/GLM-5.3 | safetensors.total: 753329940480 (BF16 2,103,729,152 + F8_E4M3 751,226,191,872 + F32 19,456), maker's own repo zai-org/GLM-5.3 @ ba32f8c19c8738e2c57c71798c601d477a7bf844 | Neither the model card, blog nor docs state a parameter count (blog: 'uses the same base model as GLM-5.2'). Total is the HF safetensors figure; active not stated anywhere checked (MoE active unknown). Repo may include MTP layers in the count. Mixture of experts per the maker's Hugging Face config.json (architectures: GlmMoeDsaForCausalLM; first_k_dense_replace 3), so shown as total with active not disclosed. |
| GPT-6 Astra | not disclosed by maker | https://openai.com/index/gpt-6-astra/ | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | Closed API model; system card not checked separately. openai.com system-card URL returned HTTP 403 (Cloudflare); the same card on deploymentsafety.openai.com was read instead. |
| GPT-6 Luna | not disclosed by maker | https://openai.com/index/introducing-gpt-6-sol-and-luna/ | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | Only 'billions' appears, referring to requests, not parameters. No Luna system card was found: the two openai.com and deploymentsafety guesses returned 403 or failed to fetch. The model docs and the launch post state no count. |
| GPT-6.1 Sol | not disclosed by maker | https://openai.com/index/introducing-gpt-6-1-sol/ | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | openai.com system-card URL returned HTTP 403; card read on deploymentsafety.openai.com. |
| Gemini 3.8 Flash | not disclosed by maker | https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/ | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). |  |
| Gemini 4 Argon | not disclosed by maker | https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-4-argon/ | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). |  |
| Gemma 4 31B | 31.27B incl. its vision encoder | https://huggingface.co/google/gemma-4-31B-it/tree/842da3794eaa0b77d5f08bae87a17459d91ff475 | google/gemma-4-31B-it @ 842da3794eaa0b77d5f08bae87a17459d91ff475, model.safetensors.index.json shards: 31,273,088,876 logical parameters, BF16 (Hugging Face's safetensors total; language model and vision encoder). Maker's text: the card's table gives 30.7B plus a vision encoder. | Checkpoint total (#3508 rule); same as logic's model_sizes.json. Revision: the repo's current one (the run's revision is not recorded). |
| Grok 4.7 | not disclosed by maker | https://x.ai/news/grok-4-7 | Searched the launch post, the API model docs page and the system/model card for 'parameter', 'billion', 'trillion' and figures like 'NB'/'NT'. No explicit parameter count was found (all cards fetched as full text unless noted). | x.ai/news mentions Grok-1's 314B, not Grok 4.7. |
| Jev 1.13.0 | not disclosed by maker | https://docs.typesafe.ai/models | Models page lists model ID jev-1.13.0, price, context; no parameter count | Closed API; TypeSafe states no size. |
| Jev 1.14.0 | not disclosed by maker | https://docs.typesafe.ai/models | Models page lists model ID jev-1.14.0, price, context, release; no parameter count; launch blog has no count either | Closed API; TypeSafe states no size. |
| Kimi K3.1 Pro | 2.8T total / 104B active | https://huggingface.co/moonshotai/Kimi-K3.1-Pro/blob/main/README.md | Total Parameters / 2.8T ; Activated Parameters / 104B | Open weights, MoE (repo sha d9e99b0792a5e93b78ea9bea62a68167e36ddd9e). HF safetensors total shows 2,780,110,363,392 but 2.72T of that is U8-packed MXFP4 storage, so it is not a true param count; card figure 2.8T used. Card also states vision encoder ~401M separately. |
| LFM2.5-24B-A2B | 23.97B total / 2.45B active | https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/tree/3dc4cd09c9a2a99e1e819693e79d3aba5e9bb4f2 | LiquidAI/LFM2.5-24B-A2B @ 3dc4cd09c9a2a99e1e819693e79d3aba5e9bb4f2, model.safetensors.index.json shards: BF16 23,971,585,280 logical parameters (Hugging Face's safetensors total; plus F32 2,432 buffer elements, not counted). Maker's text (card): 24B total, 2.45B active. | Checkpoint total (#3508 rule; backgammon only); active 2.45B from the card (a checkpoint has no active count). Revision: the repo's current one. |
| Liquid d1-ultra | not disclosed by maker | https://www.liquid.ai/blog/d1-ultra | Launch post ('Today, we release d1-ultra, our new multimodal decision model') states no parameter count. | API-only decision model. |
| Mercury Decide | not disclosed by maker |  | Inception's decisions docs, models page and Mercury 3 post describe the API (model id mercury-decide) but give no parameter count. |  |
| Open-Jev 27B v1.1 | 27.80B: Qwen3.8-27B base 27.78B + adapter and head 15.47M (the repo holds only the adapter and head) | https://huggingface.co/ZefanCai/Open-Jev-27B-v1.1/tree/28cf73067d5b337860bbef3c85b8b82ba8730956 | ZefanCai/Open-Jev-27B-v1.1 @ 28cf73067d5b337860bbef3c85b8b82ba8730956: release-manifest.json (sha256 19a4f2ad3eb48e3b6335519549baac279fa95af82dca21bb892aa033ebf0a1f5, the same bytes as the local checkout's copy) gives artifact_type 'qwen_lora_adapter_plus_scalar_decision_head', base_model 'Qwen/Qwen3.8-27B', base_revision '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0', base_weights_included false; package/checkpoint/adapter/adapter_model.safetensors (sha256 1c857224bd3609c6a71eacf7f71dd021115fcc0f791936b1fc332e915b548a81, 61,907,944 bytes) and package/checkpoint/head.pt (sha256 76e382f122abfa4e0c467d860a8d142d2fb6d2a98dc0ef9e19870bfc6eb296b4, 22,221 bytes). Card: 'A trained LoRA adapter and scalar decision head for the text backbone of Qwen/Qwen3.8-27B ... It contains 15,471,617 trained parameters; upstream base-model weights are obtained separately.' Base: Qwen/Qwen3.8-27B @ 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0, 27,781,427,952 logical parameters (Hugging Face's safetensors total for the whole released checkpoint, incl. its vision encoder). Release composition: 27,781,427,952 + 15,471,617 = 27,796,899,569. | Released composition at the stated revisions, scope written out (logic #3550, turkce #3552, Zeki #3574): the repo holds only the adapter and head; the total is the base the release manifest pins plus the adapter and head. The base revision comes from the release manifest (the local Open-Jev checkout's scripts/download_models.py downloads the same revision), not from our league run's record, which does not name it. Same as logic's 27.80B. |
| Qwen3.8 Flash | not disclosed by maker | https://www.alibabacloud.com/help/en/model-studio/newly-released-models | qwen3.8-flash entries (2026-08-26 etc.) describe 'a multimodal model from the Qwen family ... million-token context window' with no parameter count. | Closed API model. Not the open-weight Qwen3.8-Flash-Next; its numbers not used. |
| Qwen3.8-27B | 27.78B incl. its vision encoder; card: 27B | https://huggingface.co/Qwen/Qwen3.8-27B/tree/37561816e66b5b9153b1b64c10968c18c1e6f4a0 | Qwen/Qwen3.8-27B @ 37561816e66b5b9153b1b64c10968c18c1e6f4a0, model.safetensors.index.json shards: 27,781,427,952 logical parameters, BF16 (Hugging Face's safetensors total; language model and vision encoder). Maker's text: 'Number of Parameters: 27B'. | Checkpoint total (#3508 rule); same as logic's model_sizes.json. Revision: the repo's current one (the run's revision is not recorded). |
| REAX 1.3 | part G 31.27B + part Q 26.09B (each incl. its vision encoder) + decision head 1.3M | https://huggingface.co/decisionmodels/REAX-1.3/tree/fa4bf7ee3bb56a8bc421dad090631be1c5845c2d | decisionmodels/REAX-1.3 @ fa4bf7ee3bb56a8bc421dad090631be1c5845c2d, the two parts of the blend: part-g, 13 shards model-000NN-of-00013.safetensors, 31,273,088,876 logical parameters (BF16; summed from each shard's header, scripts/st_header_count.py, reax-headers.txt); part-q, 11 shards, 26,085,330,160 (its model.safetensors.index.json 'total_parameters') + part-q/readout.safetensors 1,305,600 (F32, header) = 57,359,724,636. Weights stored in BF16 (served in FP8 on our GPU); no scale tensors counted. Maker's text: the card describes the two parts but states no count. | Checkpoint total of the maker's released repo at the pinned revision (#3508 rule), component scope shown; same as logic's model_sizes.json 'REAX 1.3' 57.36B, verified here from the shard headers. |
| SubQ Snap 1.1 | not disclosed by maker | https://subq.ai/subq-snap-1-1 | Announcement covers training, calibration, benchmarks; no parameter count | Closed API. |
| SubQ Snap Preview | not disclosed by maker | https://subq.ai/introducing-subq-snap | Launch post gives benchmarks, price ($0.05/M input), Public Preview status; no parameter count | Closed API. |
| Winnow-12B | 11.91B | https://huggingface.co/EldanRing/Winnow-12B/blob/0b5b7f98e718cf0faffd0acea3093b86ebf00b56/gguf/Winnow-12B-Q8_0.gguf | EldanRing/Winnow-12B @ 0b5b7f98e718cf0faffd0acea3093b86ebf00b56, gguf/Winnow-12B-Q8_0.gguf (LFS sha256 b710efc4c0d048ee61eed92c5fef5ce323a4d17e7c51f9f0533cc72ae50818ea, the file the winnow-inference repo pins at d4631fb, logic #3534): 667 tensors, text model only (mmproj-Winnow-12B.gguf and the assistant GGUF not counted); from the GGUF header's tensor shapes: 11,907,350,320 logical parameters (token_embd 1,006,632,960 + blocks 10,900,713,520 + output_norm 3,840), excluding the 256-element rope_freqs buffer (all tensor elements: 11,907,350,576); shapes, not Q8_0 storage blocks or scales. Counted here (scripts/gguf_count.py) from the maker's file at that revision (header read) and from the local copy (same sha256). Maker's text: no count. | Checkpoint total (#3508 rule); same as logic's model_sizes.json 'Winnow-12B' (logic #3534 receipt). |

