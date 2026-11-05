# Late entries Drex - plan 2026-11-05

Nov 5, 2026 · for Can and Ümit (Ümit's request, bus #1159). **Prepared only.**

- **Nothing run:** no match, no model request, no server, no GPU use, no spend. v3.db was only read.
- **HTTP reads, all free:** Nace's docs and pricing pages, Hugging Face metadata (no weights downloaded), the Decision Models page, and OpenRouter `/api/v1/credits`.
- **Format:** the 2 Nov late entries 3, plan B: each entrant plays all 19 setups of the original League 1 table once.

## Decision needed (Can)

Can's decisions are reserved: rosters, model servers and money. The source is his in-session instruction; there is no written mailbox rule. Precedents: `mailbox/League 3 - GPT-6 Astra (high) estimate 2026-10-28.md:122` ("Waiting for Can's approval.") and Can's go for plan B on 2 Nov.

| | (a) API stage: `start_api.sh` | (b) GPU stage: `start_gpu.sh` |
|---|---|---|
| What | Drex Max 1.1 and Drex 2.0 (Nace API) v the 8 API setups and 3 programs | Drex Max v1 (our GPU) v all 19; the 8 local setups v Drex Max 1.1 and Drex 2.0 |
| Matches | **22** | **35**. With the optional Drex 2.0 (local): 54 |
| Billed (est.) | **≈ $0.68** | **≈ $0.43**. With Drex 2.0 (local): ≈ $0.58 |
| Time | **≈ 30–40 min**; no GPU | **≈ 1.5 h** once the GPUs are free (≈ 2.5 h with Drex 2.0 (local)) |
| Needs | Can's go | Can's go, plus GPUs 1–3 freed by their holders (see GPUs) |

- **Both stages:** 57 matches, ≈ $1.11 billed (≈ $1.26 with Drex 2.0 (local)). The scripts stop everything above **$2** billed.
- **Not billed:** Drex Max v1 at list-price equivalent ≈ $0.49, and Drex 2.0 (local) ≈ $0.41.

**Budget facts:**
- **OpenRouter** (Mercury Decide only): **$0.46** free (read 06:42Z). Mercury needs ≈ $0.02 here.
- **Nace account:** balance and tier (free 120 RPM / 8 in flight, or paid 600 / 16) are **unknown** without a call or the dashboard. The key is in `~/.keys` as `NACEAI_API_KEY`.
  - Nace refuses requests (402) at zero balance unless auto-pay is on.
  - The Nace share is ≈ $0.65 of the total.
- **No top-up of any account without Can.**

## 1. Runner: services added (branch `late-drex`, not main)

- **Branch and build:**
  - Branch `late-drex`, commit `ec18e90`, pushed. It is `late3-baselabs` (104103a, unmerged) with `origin/main` merged in, plus the new services.
  - Clean worktree: `/home/cbasaran/code/jevgammon-drex`. The harness commit is read from it at run time, so it must stay.
  - Binary: `target/drex/release/jevgammon`.
- **Unit tests:** `cargo test --release --bin jevgammon players::` gives 33 passed, including the 2 new tests. `rustfmt` was run on `decision.rs`. README provider rows were added.
- **Client semantics:** taken over from the Turkish runner (`benchmark_ollama.py` `SYSTEM_ONE`), with the same System One body and answer parsing as every other decision service.

| provider | for | endpoint | auth (names only) | max options per request |
|---|---|---|---|---|
| `nace` | Drex Max 1.1 (`nace/drex-max-v1.1`), Drex 2.0 (`nace/drex-v2.0`) | `https://console.nace.ai/v1/systemone` (`NACE_BASE_URL`) | `NACE_API_KEY` (Turkish runner's name), else `NACEAI_API_KEY` (the name in `~/.keys`) | **255**: Nace's limit for both (Limits; docs/request-format.md) |
| `drex-max` | Drex Max v1 (`drex-max/drex-max-v1`) | `http://127.0.0.1:18104` | none | **110** |
| `drex-local` | optional Drex 2.0 (local) (`drex-local/drex-v2.0`) | `http://127.0.0.1:18105` | none | **110** |

- **Model ids** come from the Turkish results db (`runs.model`, provider `nace`):
  - `drex-max-v1.1` (runs 325–332, …);
  - `drex-v2.0` (runs 333–338, 563–586).
  - The stored responses name the same model.
- **Why 110 for the loaders.** Both Nace loaders refuse a request over their default 16,384 tokens with an error; we keep the default, as the Turkish Drex Max v1 runs did. That refusal is a failed request, not an invalid answer, so a match would stall.
  - I tokenized the 40 largest stored League 1 requests with Drex Max v1's tokenizer and prompt (`drex_max.model._prompt`, CPU only).
  - At 110 options the largest is **14,527 tokens**; at 120 it is 15,610; at 128 it is **16,486**, over the limit. Clef uses the same 110 against a 16,384-token limit.
  - Drex 2.0's `kev` prompt is not measured, because its tokenizer would have had to be downloaded. Its smoke test (below) sends 3 requests at the cap.
- **Ports.** 18104 and 18105. The Turkish default for `drex_max_server.py` is 18099, which is Decider v1.2 27B's stored `base_url`.

## 2. Option-count rule: what the runner actually does

**Ümit's rule does not match the runner exactly.** His rule: at most 25 options per request; larger sets split into equal groups; a winner per group, then a final among the winners; every play's probability stored.

What the runner does (`Player::decide`, `src/players/mod.rs`, unchanged since League 1):
- **Cap per service, not one global 25.** Each decision service has its own `max_choices` (`src/players/decision.rs`). In League 1:

  | cap | models |
  |---|---|
  | **25** | Decider v1.1, v1.2 and Flash v1.2 (pplx-local) |
  | 26 | Cygnet |
  | 40 | Winnow |
  | 110 | Clef |
  | 255 | Open-Jev and every hosted API (Jev, Fastino, OpenAI, Liquid, SubQ, Celeris, OpenRouter) |
  | 120 | late entries 3: Base Labs |
  | 255 | late entries 3: SubQ Snap 1.1 |

  v3.db confirms this. The largest unsplit list is 25 for the Deciders, 26 for Cygnet, 40 for Winnow, 110 for Clef, and 219–251 for the APIs.
- **Groups.** With n options over the cap, the runner makes `ceil(n/cap)` groups of `ceil(n/groups)` in the seeded shown order. They are equal except the last, which can be smaller. A one-play group passes straight through.
- **Final.** The group winners, in group order, play another round. Rounds repeat until one play is left, so it is a final whenever there are 2 or more winners. `turns.group_size` records the group size.
- **Storage:** **not every play's probability.**
  - `turns.probabilities` holds only the **last request's** probabilities, aligned with `option_order`, with `null` for every option outside that request.
  - Every request and response, each group's included, is in `exchanges`, so the group-round probabilities can be recovered from the raw responses only.
  - Example: turn 219740 (Decider v1.2, 69 options) made 3 groups of 23 plus a final of 3. That is 4 exchanges, and its stored row has 3 values and 66 nulls.
- **Protocol unchanged.** The Drex entrants get their service's own cap, as every League 1 decision model did: 255 hosted, 110 local. A uniform 25 would change the League 1 protocol (and the late entries 3 protocol); that is Ümit's call, not made here.

## 3. Setups and prices (read 2026-11-05)

| setup | route | weights / loader | price in config ($/M input; output free) | billed |
|---|---|---|---|---|
| **Drex Max 1.1** | `nace/drex-max-v1.1`, Nace API | no open weights | **0.06** list (nace.ai/drex) | **$0.03** launch price (console.nace.ai/docs/drex/reference/pricing: drex-max-v1.1 30 nUSD per token) |
| **Drex 2.0** | `nace/drex-v2.0`, Nace API | — | **0.06** (console pricing: drex-v2.0 60 nUSD per token) | $0.06 |
| **Drex Max v1** | `drex-max/drex-max-v1`, our GPU | `nace-ai/drex-max-v1` @ **cac65e1982a0237e996419ba559004522d9a33ac**; the HF cache has exactly this snapshot (49 GB, bf16). Nace's `drex_max` at e206b27 (`~/code/drex-decision-models`, clean; `.venv-drex-max`: torch 2.15.0, transformers 5.17.0) behind `servers/drex_max_server.py` | **0.06**, "list price for the hosted model, not billed", as on the Decision Models page (results.json `prices`: drex-max-v1 $0.06, source nace.ai/drex) | $0 |
| **Drex 2.0 (local)**, optional 4th | `drex-local/drex-v2.0`, our GPU | see below | 0.06, list price for the hosted model, not billed | $0 |

- **Config fields.** `workspace/drex/players.json` uses the same fields as the late-3 entries (price, `parallel`, `base_url`, `device`, note).
- **`parallel`.** Each Nace setup has `parallel` 2, so at most 4 requests are in flight against Nace's free-tier 8.
- **Probabilities.** Stored as returned. Drex 2.0 rounds them to 4 decimals, both hosted and through its `serve.py`. The runner does not check sums (as checked for late entries 3).
- **Cost cap.** `drex.py billed` counts Drex Max 1.1 at the $0.03 it is billed. `turns.cost_usd` keeps the $0.06 list price, as for the other setups.

### Drex 2.0 (local), from Hugging Face metadata only

- **Repository:** `nace-ai/drex-v2.0` is public, revision **e646674476744e3826caf62b834054151e2aba51** (as Zeki read it), last modified 2026-10-30.
  - 16 safetensors shards, **70.2 GB** in total (70,241,939,617 bytes in the repository). Disk has 2.0 TB free.
  - Base model `Qwen/Qwen3.6-35B-A3B`: `Qwen3_5MoeForConditionalGeneration`, 40 layers, 256 experts, 8 active, bf16.
- **Not the Drex Max v1 loader.** Drex Max v1 is a dense `Qwen3_5Model` with `readout.safetensors`, scored by `drex_max`. Drex 2.0 ships its own `serve.py` with Nace's `kev` loader and a pointer head, `head.pt`.
  - `serve.py` takes the same System One request at `POST /v1/systemone` and returns `{model, answers, usage}`.
  - It does not check the `model` field.
  - It refuses with 400 over its default 16,384 tokens (`KEV_CONTEXT`) and over 1 MB of body.
  - So it gets its own runner service, `drex-local`.
- **Requirements:** `torch>=2.6,<2.9`, `transformers>=5.17,<6`. This needs a new venv, `.venv-drex-v2`; the Drex Max venv has torch 2.15.
- **GPU:** ≈ 72 GB of weights, so one RTX PRO 6000 of its own (job need set at 82 GB).
- **Scripts:** `drexv2.sh download` (70.2 GB; refuses without `CAN_GO=yes`), `setup`, then `start`.

## 4. Opponents and GPUs

Each entrant plays the same 19 setups as plan B.

**Without a GPU (stage a):**

| opponent | route | key present (non-empty) |
|---|---|---|
| Celeris-1 Decision | `celeris/celeris-1-decision` | `~/.config/celeris/key` |
| Fastino GLiDE | `fastino` | `FASTINO_API_KEY` |
| GPT-6 Luna | `openai-decisions/gpt-6-luna` | `OPENAI_API_KEY` |
| Jev 1.13.0, Jev 1.14.0 | `jev/…` | `JEV_API_KEY` |
| Liquid d1-ultra | `liquid/d1-ultra` | `LIQUIDAI_API_KEY` |
| Mercury Decide | `openrouter-decisions/inception/mercury-decide` | `OPENROUTER_API_KEY`; checked at go, dropped below $0.10 free |
| SubQ Snap Preview | `subq/subq-snap-preview` | `SUBQ_API_KEY`; still listed by SubQ on 2 Nov; checked at go, dropped if gone |
| GNUbg weak, Random, Safest | CPU | — |

**On GPUs (stage b), the same scripts and settings as plan B on 2 Nov:**
- Decider v1.2 27B + Decider Flash v1.2 + Winnow-12B (73.5 GiB together)
- Clef (55.5)
- Cygnet (`CYGNET_UTIL=0.34`, 32.5)
- Fastino GLiDE v1.2 (local) (53.6)
- Open-Jev 27B v1.1 (52.8)
- Decider v1.1 27B (51.6)
- the entrant Drex Max v1 (48.6 GiB loaded per its card; job need 60 GB)

**GPUs now (`nvidia-smi`, read only, 06:42Z):**
- All four are held by `deepseek-v41-flash-4x-rtx-pro-6000-deepseek-1`: Turkce's DeepSeek V4.1 Flash 1017 repeat runs, sglang TP4, ≈ 86 GB each, expected to end about 07:43 UTC (an estimate).
- **GPU 0 is claimed by compactor for ≈ 30 h (bus #1038).**
- Our scripts touch neither and never stop anyone else's process.
- GPU start is coordinated with @turkce and compactor by Main.

**Plan for stage b on GPUs 1–3 (`DREX_GPUS`, default "1 2 3").** `drex-orch-gpu` starts each server only on a GPU whose free memory covers its need plus 2 GB, so a held GPU is waited for. Expected layout once GPUs 1–3 are free:

| wave | GPU 1 | GPU 2 | GPU 3 |
|---|---|---|---|
| 1 | Drex Max v1 (entrant, first) + Cygnet | Decider v1.2 27B + Flash + Winnow | Clef |
| 2 (as wave-1 servers finish) | Drex Max v1 | GLiDE v1.2 (local), then Decider v1.1 | Open-Jev |

- **Stopping.** Each opponent server stops once it has played every entrant, and Drex Max v1 once it has played all 19. The release text goes to the status file at the end.
- **Drex 2.0 (local).** With `DREX_LOCAL=yes`, it needs a whole free GPU before the opponent servers start. That delays wave 1 until one of GPUs 1–3 has 84 GB free.

## 5. Estimates

**Basis:**
- **Decisions and tokens.** 115 decisions per entrant per match (late entries 3 averaged 107–122). The tokens per decision come from SubQ Snap 1.1's 3,743 in late entries 3, scaled by the Turkish runs' tokens per question against SubQ's 385:

  | setup | tokens per question (Turkish runs) | tokens per decision |
  |---|---|---|
  | Drex Max 1.1 | 385 | 3,743 |
  | Drex 2.0 | 319 | ≈ 3,100 |
  | Drex Max v1 | 388 | ≈ 3,770 |

- **Opponents' billed cost.** These are late entries 3's actual costs per entrant, $0.151 for the 8 API setups:

  | opponent | $ per entrant |
  |---|---|
  | Luna | 0.028 |
  | Preview | 0.025 |
  | Jev 1.14 | 0.020 |
  | Celeris | 0.019 |
  | Liquid | 0.019 |
  | Fastino | ≈ 0.017 |
  | Jev 1.13 | 0.015 |
  | Mercury | 0.008 |

| | matches | entrants' billed | opponents' billed | total billed |
|---|---|---|---|---|
| (a) API stage | 22 | Drex Max 1.1 $0.14 (at $0.03) + Drex 2.0 $0.24 | $0.30 (OpenRouter $0.016) | **$0.68** |
| (b) GPU stage | 35 | Drex Max 1.1 v 8 local $0.10 + Drex 2.0 v 8 local $0.17 | Drex Max v1's 8 API opponents $0.15 | **$0.43** |
| (b) + Drex 2.0 (local) | +19 | $0 | +$0.15 | **$0.58** |

- **Speed.** In the Turkish runs, the hosted Drex took 0.31–0.32 s per question (median) and Drex Max v1 on our GPU 0.08 s. Backgammon prompts are about 10× longer [INFERENCE: ≈ 0.3–0.6 s hosted, ≈ 0.5–1 s local].
- **Time.** Late entries 3 played its 45 API/program/GPU-1 matches in 25 min and its last 12 in 26 min after GPU 2 came free. Hence ≈ 30–40 min for (a), and ≈ 1.5 h for (b) after GPUs are free, server starts (≈ 2–5 min each) included.

## 6. Launch (not run)

Files in `workspace/drex/` (not committed):

| file | what |
|---|---|
| `players.json` | the four configs |
| `drex.py` | `configs` (read-only: entrant v the API setups and programs, from v3.db's stored settings), `trigger` (adds the entrant to `late_entry_stage`), `smoke`, `pending`, `open`, `league-id`, `billed` |
| `drexmax.sh` | Drex Max v1 server: unit `v3-drex-max`, `DREX_MAX_GPU`, :18104 |
| `drexv2.sh` | `download` / `setup` / `start` for Drex 2.0 (local), :18105 |
| `run_league.sh` | one league as a user unit: start, or `--resume` |
| `orchestrate.sh` | the unit `drex-orch-api` / `drex-orch-gpu`: every 5 min it keeps the leagues running, starts servers when a GPU has room, adds opponents by `league-add`, stops servers when done, stops everything above $2 billed, and writes the release text |
| `start_api.sh` | stage (a) |
| `start_gpu.sh` | stage (b), with `DREX_GPUS`, optional `DREX_LOCAL=yes` |

Both start scripts refuse without `CAN_GO=yes` (checked).

1. **`CAN_GO=yes workspace/drex/start_api.sh`**
   - Free checks (GETs only):
     - Nace `/v1/models` must list `drex-max-v1.1` and `drex-v2.0`, or it stops;
     - SubQ Snap Preview is dropped if SubQ no longer lists it;
     - Mercury Decide is dropped below $0.10 OpenRouter credit.
   - Backs up v3.db (`v3.db.bak-<ts>-before-drex.zst`), records the first match id and creates `mailbox/Late entries Drex - status 2026-11-05.md`.
   - Starts `drex-orch-api`.
2. **`CAN_GO=yes workspace/drex/start_gpu.sh`** can run alongside step 1.
   - It runs step 1's checks first if step 1 has not run, then starts `drex-orch-gpu`.
   - That unit waits for GPU room, starts Drex Max v1 and creates its league when the server answers, then starts the opponent servers and adds them to every entrant league.
   - Before Drex Max v1's league starts, it is worth running a smoke test: `drex.py smoke http://127.0.0.1:18104 drex-max-v1` (20 stored requests, 3 of them at 110 options). The orchestrator does not run it.
3. **Stage rules:** stage `late-entry` through the trigger, League 1's rules, one hidden league per entrant (`only_pairs_of`), and $2 billed cap.

## Blockers

1. **Can's go** for (a), (b), or both; the roster with or without Drex 2.0 (local); and the money (≈ $0.68 + $0.43). The 70.2 GB download for Drex 2.0 (local) also needs his go.
2. **GPUs for (b):** Turkce's DeepSeek server holds all four (until about 07:43 UTC, estimated), and GPU 0 is compactor's claim. Main coordinates with @turkce and compactor; the scripts only wait.
3. **Nace balance and tier are unknown** without a call or the dashboard. If the balance is short (402), a top-up needs Can.
4. **Ümit's 25-option rule differs from the runner.** The runner uses per-service caps and stores only the deciding request's probabilities. The plan keeps the League 1 protocol; changing it is Ümit's or Can's decision, for all decision models alike.
