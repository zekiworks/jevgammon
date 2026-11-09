# small-models review: parameter counts in the details box, Small models filter (Ümit #3465, threshold Ümit #3475)

Branch `small-models`, **27d5db2**, one commit on origin/main 27c04f9. **Candidate only. Not merged or deployed.**
Presentation only: story.py, pages.py (the parameter helpers and the one constant), bg.js, new
`tools/site/content/model_params.json`. Model pages unchanged (Main: details box and filter only).

## What changed
- **Details box, every model row** (38 main rows + 16 other-settings rows): one line after the cost line,
  `Parameters: 30.7B` (dense), `Parameters: 24B total / 2.45B active` (MoE), `Parameters: 753.33B total; active not
  disclosed by maker` (GLM-5.3: MoE per its config.json, no active count from the maker), the figure linked to its
  source as Released is; `Parameters: not disclosed by maker` (no link) where the maker gives none. 'X effective (Y
  total)' is supported, but no row has an effective figure. Programs: no line. No size next to the name.
- **Filter:** All · Chat models · Decision models · **Small models**. Small models = rows whose model's disclosed
  TOTAL is at most `pages.SMALL_MAX_B = 15` (billions; MoE by total; **15B, Ümit #3475**); undisclosed sizes are
  not included; the programs stay as reference rows (as in every view); ranks stay overall (27, 29, 37). While
  pressed, under the keys: 'Small models: 15B parameters or fewer (total), as disclosed by the maker; models with
  undisclosed size are not included.' An other-settings row goes with its main row. The About page's leaderboard
  section names the key and repeats the definition plus a sentence on where the counts come from.
- `content/model_params.json`: per model `total_b`, `active_b`, `effective_b` (billions as shown), `moe`, `source`,
  `quote` (verbatim or what was searched), `checked` (URLs), `read` (2026-11-09), `note`. Figures are stored in
  billions so the page's numbers are traceable for checks.run (an exact repository count is rounded to two decimals;
  the exact count is in `quote`/`note`).

## Source rule (as applied)
Maker's own text first (model card, official announcement/changelog/docs). Where the maker states no figure in text,
the safetensors total Hugging Face shows for the maker's own repo (Decider v1.1 27B, Fastino GLiDE v1.2, GLM-5.3).
Where both exist and differ, the maker's text (both recorded in `note`). Nothing from names, base models
(Winnow-12B, Open-Jev 27B v1.1, DeepSeek V4.1 Flash 1017 stay 'not disclosed') or third parties. Closed API models:
launch post, API model docs and system/model card checked for a count (URLs in `checked`).

## Which rows are Small models
At **15B** (live): 3 ranked rows
| Rank | Model | Parameters |
|---:|---|---|
| 27 | Base Labs Elephant-1 | 9B |
| 29 | Cygnet (Gemma 4 12B) | 11.95B |
| 37 | Decider Flash v1.2 | 4B |

At **32B** (for comparison): 12 ranked rows
| Rank | Model | Parameters |
|---:|---|---|
| 11 | Gemma 4 31B | 30.7B |
| 13 | Base Labs Mammoth-1 | 27B |
| 14 | Drex Max v1 | 27B |
| 15 | Qwen3.8-27B | 27B |
| 23 | Fastino GLiDE v1.2 | 26.09B |
| 25 | Decider v1.2 27B | 27B |
| 27 | Base Labs Elephant-1 | 9B |
| 28 | Clef | 27B |
| 29 | Cygnet (Gemma 4 12B) | 11.95B |
| 30 | Decider v1.1 27B | 26.09B |
| 36 | LFM2.5-24B-A2B | 24B total / 2.45B active |
| 37 | Decider Flash v1.2 | 4B |

Drex 2.0 (35B total / 3B active) would be out at 32B; all undisclosed models are out at any threshold.

## Parameter table (all 39 models on the leaderboard, incl. other-settings rows' models)
| Model | Parameters shown | Source (read 2026-11-09) | Note |
|---|---|---|---|
| Base Labs Elephant-1 | 9B | https://huggingface.co/baselabs/elephant-1/blob/b3f8a93462fb1051a9de031e94a7ff380e254072/README.md | Dense. HF safetensors total at the pinned sha b3f8a934: 9,409,813,744 (BF16); card's rounded 9B used. |
| Base Labs Mammoth-1 | 27B | https://huggingface.co/baselabs/mammoth-1/blob/61cec44c281c693992e3d6ebeb44dd3402dfa186/README.md | Dense. HF safetensors total for the maker's repo at the pinned sha 61cec44c: 27,356,728,560 (BF16); card's rounded 27B used. |
| Celeris-1 Decision | not disclosed by maker | checked: https://celeris.ai/celeris-1-decision | Closed API. |
| Claude Fable 5.1 | not disclosed by maker | checked: https://www.anthropic.com/claude-fable-and-mythos-5-1, https://docs.claude.com/en/docs/about-claude/models/overview, https://www.anthropic.com/system-cards, https://assets.claude.com/0339e6a7c5c7b87f5c07798616dc32c215d14235.pdf | System card PDF (Fable 5.1 / Mythos 5.1) searched in full text. |
| Claude Opus 5.5 | not disclosed by maker | checked: https://www.anthropic.com/claude-opus-5-5, https://docs.claude.com/en/docs/about-claude/models/overview, https://www.anthropic.com/system-cards, https://assets.claude.com/fc1b44717c85dc068bc6ba5024219938094694bd.pdf | System card PDF searched in full text. |
| Claude Sonnet 5.5 | not disclosed by maker | checked: https://www.anthropic.com/claude-sonnet-5-5, https://docs.claude.com/en/docs/about-claude/models/overview, https://www.anthropic.com/system-cards, https://assets.claude.com/870c8f525702625d2c62fc6dd04c857e3250bec1.pdf | System card PDF searched in full text. |
| Clef | 27B | https://huggingface.co/cloudflare/clef | Model card and Cloudflare changelog ('@cf/cloudflare/clef 27B') say 27B; HF safetensors total for cloudflare/clef is 27356728560 (sha cfddda043dd190ef3b01cff449d5ee8cff1e8ec6). Card figure chosen per rule. Maker: Cloudflare. |
| Cygnet (Gemma 4 12B) | 11.95B | https://huggingface.co/google/gemma-4-12B-it | Cygnet is blockbrain-ai's recipe (github.com/blockbrain-ai/cygnet-recipe): Google's gemma-4-12B-it, 'no fine-tuning', served by vLLM at --revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7; so the weights' maker card is Google's. Figure read from the current ma… |
| Decider Flash v1.2 | 4B | https://docs.perplexity.ai/changelog | Maker's own stated figure (changelog) used over Hugging Face's exact safetensors total for perplexity-ai/pplx-decider-flash-v1.2 @ 9ff7cf98: 4,539,265,536. Model card states no count. Dense. |
| Decider v1.1 27B | 26.09B | https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1.1-27b | Model card states no explicit count (only the name '27b' and backbone Qwen3.8-27B); the figure is the safetensors total HF shows for Perplexity's own repo. Dense. |
| Decider v1.2 27B | 27B | https://docs.perplexity.ai/changelog | Maker's own stated figure (changelog) used over Hugging Face's exact safetensors total for perplexity-ai/pplx-decider-v1.2 @ cce0f3f8: 26,085,330,160. Model card text states no count. Dense. |
| DeepSeek V4.1 Flash | 552B total / 16B active | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash | Card table: '# Backbone Params 552B', '# Activated Params 8B / 16B' (prefill/decode); active recorded as the 16B decode figure. Card also lists 'Engram conditional memory (196B parameters, sparsely accessed)' separately from the 552B backbone; total kept at th… |
| DeepSeek V4.1 Flash 1017 | not disclosed by maker | checked: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017, https://huggingface.co/api/models/deepseek-ai/DeepSeek-V4.1-Flash-1017, https://api-docs.deepseek.com/updates/ | Not filled from the V4.1-Flash card (lineage). HF safetensors total 763,205,315,794 is identical to V4.1-Flash's and inflated by packed FP4 (I8) storage, so not a parameter count. If Main accepts 'minor update' as same architecture, V4.1-Flash's 552B / 8B-16B … |
| Drex 2.0 | 35B total / 3B active | https://huggingface.co/nace-ai/drex-v2.0/blob/e646674476744e3826caf62b834054151e2aba51/README.md | Active is 'about 3B' on the card; Nace docs: 'drex-v2.0 is a mixture of experts with 3B active parameters'. HF safetensors total at pinned sha e6466744: 35,107,181,936 (includes the vision tower, which the card says is dropped on load). Applies to both hosted … |
| Drex Max 1.1 | not disclosed by maker | checked: https://console.nace.ai/docs/drex/reference/models, https://console.nace.ai/docs/drex/guides/drex-max, https://www.nace.ai/blog/introducing-drex-max, https://www.nace.ai/developers | Not inferred from Drex Max v1 (27B). |
| Drex Max v1 | 27B | https://huggingface.co/nace-ai/drex-max-v1/blob/cac65e1982a0237e996419ba559004522d9a33ac/README.md | Card says 27B; HF safetensors total at pinned sha cac65e19 is 26,085,330,160 (BF16, ~26.1B). Disagreement recorded; card figure used per rule. Repo main has moved on (sha 81cb1111), same safetensors total. |
| Fastino GLiDE | not disclosed by maker | checked: https://fastino.ai/blog/introducing-glide-the-first-thinking-decision-model, https://fastino.ai/blog/training-glide-sota-decision-model, https://huggingface.co/api/models/fastino/GLiDE | Hosted glide_v2 is not documented as the same checkpoint as the HF fastino/GLiDE weights, so the HF safetensors total is not applied. |
| Fastino GLiDE v1.2 | 26.09B | https://huggingface.co/api/models/fastino/GLiDE/revision/a7e45896 | Model card text states no count; Fastino blog says only '27B-class'. HF-shown safetensors total for the maker's own repo at the pin used. |
| GLM-5.3 | 753.33B total; active not disclosed by maker | https://huggingface.co/api/models/zai-org/GLM-5.3 | Neither the model card, blog nor docs state a parameter count (blog: 'uses the same base model as GLM-5.2'). Total is the HF safetensors figure; active not stated anywhere checked (MoE active unknown). Repo may include MTP layers in the count. Mixture of exper… |
| GPT-6 Astra | not disclosed by maker | checked: https://openai.com/index/gpt-6-astra/, https://developers.openai.com/api/docs/models/gpt-6-astra, https://platform.openai.com/docs/models/gpt-6-astra, https://deploymentsafety.openai.com/gpt-6-astra (+1 more) | Closed API model; system card not checked separately. openai.com system-card URL returned HTTP 403 (Cloudflare); the same card on deploymentsafety.openai.com was read instead. |
| GPT-6 Luna | not disclosed by maker | checked: https://openai.com/index/introducing-gpt-6-sol-and-luna/, https://openai.com/index/gpt-6-astra/, https://developers.openai.com/api/docs/models/gpt-6-luna, https://platform.openai.com/docs/models/gpt-6-luna (+3 more) | Only 'billions' appears, referring to requests, not parameters. No Luna system card was found: the two openai.com and deploymentsafety guesses returned 403 or failed to fetch. The model docs and the launch post state no count. |
| GPT-6.1 Sol | not disclosed by maker | checked: https://openai.com/index/introducing-gpt-6-1-sol/, https://openai.com/index/gpt-6-astra/, https://developers.openai.com/api/docs/models/gpt-6.1-sol, https://platform.openai.com/docs/models/gpt-6.1-sol (+2 more) | openai.com system-card URL returned HTTP 403; card read on deploymentsafety.openai.com. |
| Gemini 3.8 Flash | not disclosed by maker | checked: https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/, https://ai.google.dev/gemini-api/docs/models, https://deepmind.google/models/model-cards/, https://deepmind.google/models/model-cards/gemini-3-8-flash/ |  |
| Gemini 4 Argon | not disclosed by maker | checked: https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-4-argon/, https://ai.google.dev/gemini-api/docs/models, https://deepmind.google/models/model-cards/, https://deepmind.google/models/model-cards/gemini-4-argon/ |  |
| Gemma 4 31B | 30.7B | https://huggingface.co/google/gemma-4-31B-it | Dense. Card says 30.7B; HF safetensors total for the repo is 31,273,088,876 (includes ~550M vision encoder). Chose the card figure per rule. |
| Grok 4.7 | not disclosed by maker | checked: https://x.ai/news/grok-4-7, https://docs.x.ai/docs/models, https://docs.x.ai/docs/models/grok-4.7, https://x.ai/news | x.ai/news mentions Grok-1's 314B, not Grok 4.7. |
| Jev 1.13.0 | not disclosed by maker | checked: https://docs.typesafe.ai/models, https://typesafe.ai/blog/jev-1-14 | Closed API; TypeSafe states no size. |
| Jev 1.14.0 | not disclosed by maker | checked: https://docs.typesafe.ai/models, https://typesafe.ai/blog/jev-1-14 | Closed API; TypeSafe states no size. |
| Kimi K3.1 Pro | 2.8T total / 104B active | https://huggingface.co/moonshotai/Kimi-K3.1-Pro/blob/main/README.md | Open weights, MoE (repo sha d9e99b0792a5e93b78ea9bea62a68167e36ddd9e). HF safetensors total shows 2,780,110,363,392 but 2.72T of that is U8-packed MXFP4 storage, so it is not a true param count; card figure 2.8T used. Card also states vision encoder ~401M sepa… |
| LFM2.5-24B-A2B | 24B total / 2.45B active | https://huggingface.co/LiquidAI/LFM2.5-24B-A2B | Card intro and blog say '24B-parameter ... with only 2B active'; spec list says 24.0B / 2.45B — used the precise spec figures. HF safetensors total 23,971,587,712 (BF16 23,971,585,280 + F32 2,432). |
| Liquid d1-ultra | not disclosed by maker | checked: https://www.liquid.ai/blog/d1-ultra, https://www.liquid.ai/models, https://huggingface.co/LiquidAI/d1-ultra (401, not public) | API-only decision model. |
| Mercury Decide | not disclosed by maker | checked: https://docs.inceptionlabs.ai/capabilities/decisions, https://www.inceptionlabs.ai/models, https://www.inceptionlabs.ai/blog/introducing-mercury-3 |  |
| Open-Jev 27B v1.1 | not disclosed by maker | checked: https://huggingface.co/ZefanCai/Open-Jev-27B-v1.1, https://huggingface.co/api/models/ZefanCai/Open-Jev-27B-v1.1 | Maker: Zefan Cai (HF ZefanCai, github Zefan-Cai/Open-Jev; sha 28cf73067d5b337860bbef3c85b8b82ba8730956). Card states only the adapter+head count (15,471,617 trainable); it gives no total for the combined model and HF shows no safetensors total. Total would req… |
| Qwen3.8 Flash | not disclosed by maker | checked: https://www.alibabacloud.com/help/en/model-studio/newly-released-models, https://www.alibabacloud.com/help/en/model-studio/models | Closed API model. Not the open-weight Qwen3.8-Flash-Next; its numbers not used. |
| Qwen3.8-27B | 27B | https://huggingface.co/Qwen/Qwen3.8-27B | Card says 27B; HF safetensors total 27,781,427,952 (BF16, likely includes vision tower). Chose card figure. |
| REAX 1.3 | not disclosed by maker | checked: https://huggingface.co/decisionmodels/REAX-1.3/blob/fa4bf7ee3bb56a8bc421dad090631be1c5845c2d/README.md, https://huggingface.co/api/models/decisionmodels/REAX-1.3, https://huggingface.co/decisionmodels/REAX-1.3/blob/fa4bf7ee3bb56a8bc421dad090631be1c5845c2d/engine/reax13.json | Component sizes in names (31B/27B) are lineage, not a stated total for REAX; not summed. |
| SubQ Snap 1.1 | not disclosed by maker | checked: https://subq.ai/subq-snap-1-1, https://docs.subq.ai/using-the-api/models/, https://docs.subq.ai/endpoints/decisions-api/ | Closed API. |
| SubQ Snap Preview | not disclosed by maker | checked: https://subq.ai/introducing-subq-snap, https://docs.subq.ai/using-the-api/models/ | Closed API. |
| Winnow-12B | not disclosed by maker | checked: https://huggingface.co/EldanRing/Winnow-12B, https://huggingface.co/api/models/EldanRing/Winnow-12B?expand[]=gguf | GGUF repo, no safetensors total. HF's gguf total (422,857,220, architecture gemma4-assistant) is for the MTP assistant file, not Winnow. Base Gemma 4 12B's 11.95B not used (lineage). |

## Points for Zeki / Ümit to look at
- **Logic's per-model file:** not received during this run, so these figures were not cross-checked against it.
  Models both sites have (Gemma, Qwen, DeepSeek, GLM, Kimi, LFM and the closed APIs) should be compared when it is.
- **Decider v1.1 27B 26.09B vs Decider v1.2 27B 27B:** v1.1 has no text figure (safetensors total for the maker's
  repo); v1.2's changelog calls it 'the 27B decision model' (its repo total is also 26,085,330,160). Same for Fastino
  GLiDE v1.2 (26.09B; the blog says only '27B-class'). Neither matters at 15B or 32B.
- **Decider Flash v1.2 4B:** changelog 'a new 4B decision model'; repo total 4,539,265,536. Small either way.
- **Cygnet (Gemma 4 12B):** Cygnet is Google's gemma-4-12B-it unchanged (blockbrain-ai recipe, 'no fine-tuning'), so
  the count is from Google's card (11.95B); it was read from the current card, not the recipe's pinned revision
  (the repository total, 11.96B, agrees).
- **Winnow-12B:** its card states no count (GGUF repo, no safetensors total), so 'not disclosed by maker' and it is
  not a Small model, though built on Gemma 4 12B. The rule forbids taking the base model's count.
- **DeepSeek V4.1 Flash:** active recorded as 16B, the decode figure; the card gives 8B for prefill and 16B for decode.
- **GPT-6 Luna:** its system card could not be loaded; 'not disclosed' rests on its launch post and API docs.

## What ran (logs and exit codes in the files)
- New frozen copy of the live state: `/tmp/small-state` (copied 2026-11-09 11:42:24Z under the update lock, data as of
  11:35Z, results 67a1d058), plus frozen copies of the repo's untracked build inputs (replay.db, smoke/part-a.json,
  workspace/learning-pilot). The live state was only read.
- Full `build.py --state /tmp/small-state --no-image` (production compute, render and checks.run, which exits 2 on any
  failure), `/usr/bin/python3`:
  - origin/main 27c04f9: `build-main.log`, **exit status 0**.
  - candidate (the committed tree): `build-candidate.log`, **exit status 0**, so **checks.run 0 failures**. (The
    first candidate build failed checks.run on '753.33' not being traceable to a data file; the figures are now stored
    in billions as shown, and the rebuild passed.)
- Not run: update.sh, deploy, scorers, model calls.

## Results
| Check | Result |
|---|---|
| Files (`compare.md`; manifests) | 2,552 files each, none only in one; different: `index.html`, `about/index.html`, `bg.js` only. |
| Numbers (`numbers.csv`) | **63/63 rows**: each row's HTML equal to origin/main's once the Parameters line and `data-hl-small` are taken out; numbers equal. Home text outside the leaderboard equal (new key and note out). About: equal but for the added sentences. **0 number changes.** |
| Parameters line vs file (`params.csv`) | **63/63**: every model row one line = model_params.json (text and link); programs none; `data-hl-small` exactly on the 15B rows (main + their other-settings rows). |
| Browser 375/390/1280 light+dark (`browser.md`) | **42/42, exit 0.** Per size/theme: each filter state (expanders closed and all open) shows exactly the data's rows for that key, ranks overall, the note only under Small models, no sideways overflow; no row lost; the Parameters line on all 63 rows as data (hover at 1280, tap + second tap at 375/390), box inside the window, no overflow with a box open at 375/390; no script error. |

## Diffs
- `source.patch`: the branch against origin/main (`git diff origin/main -- tools/site`).
- `render-narrow.diff`: the leaderboard section of index.html, origin/main vs candidate (one tag per line).
- `render-about.diff`, `render-bg.js.diff`: the other two changed files.

## Screenshots
- `for-umit/small-models-1280px-light-box.png` (Small models pressed, a box open), `for-umit/small-models-1280px-light.png`,
  `for-umit/small-models-375px-light.png` (two screens), `for-umit/all-*.png` (All), `for-umit/before-main-*.png`
  (origin/main). `screenshots/`: row 1 hover at 1280, row 1 tap at 375 light/dark, 375 dark and 390 Small models.

## Scripts (`scripts/`)
`compare.py REPO BASE NEW OUT`, `browser.py URL BASE NEW OUT` (Playwright; renders served with
`python3 -m http.server` over /tmp).
