# Late entries 3 - plan 2026-11-02

Nov 2, 2026 · for Can. **Prepared only.** No match, model request, GPU start or server start has run. Nothing was spent and the site is unchanged. v3.db was only read. The one exception is that a Docker container of `baselabs-serve:81ce62f` was created and removed, without being started, to read qev's source. Can approves the roster, the GPUs and any spend.

**Update (later on Nov 2): Ümit chose Plan B.**
- The `baselabs` runner service is now implemented on branch `late3-baselabs`, not on main (see "Plan B: status" at the end).
- Can's approval is still missing, so still nothing has run.

Entrants: **Base Labs Elephant-1** and **Base Labs Mammoth-1** (local, Docker), and **SubQ Snap 1.1** (API). They come in as late entries to the **original League 1 table** (the Decision group), in the same way as GPT-6 Astra (high) joined League 3 (hidden league #9, `matches.stage = 'late-entry'`; `mailbox/Late entries on the site - proposal 2026-10-28.md`).

Files, in `workspace/late3/` (not committed; this file is the only commit):

| file | what |
|---|---|
| `players.json` | the three player configs |
| `late3.py` | `configs` (read-only: league configs from v3.db's stored opponent settings), `trigger` (adds the three names to v3.db's `late_entry_stage` trigger), `smoke` (replays stored League 1 requests to a local Base Labs server), `pending`, `league-id` |
| `baselabs.sh` | `elephant\|mammoth start\|stop\|status\|probe` (docker, as `baselabs_server.py`'s docstring) |
| `run_league.sh` | one league as a user unit: `league --config`, or `--resume` once it exists |
| `start_A.sh`, `start_B.sh` | the two plans; both refuse to run without `CAN_GO=yes` |
| `leagues/*-{A,B}.json` | league configs generated today by `late3.py configs` (the start scripts generate them again at go) |

## 1. Player configs

They use the same fields as the stored decision-model players: SubQ Snap 1.1 has SubQ Snap Preview's fields (spec, provider, price) plus a note, and the Base Labs pair use the local Decider v1.2 27B layout.

| name | spec | provider | price ($/M in, out) | parallel | base_url | device |
|---|---|---|---|---|---|---|
| Base Labs Elephant-1 | `baselabs/baselabs/elephant-1` | `local (baselabs_server.py)` | 0.035, 0 (Baseten list, 2026-11-01) | 1 | `http://127.0.0.1:18102` | bariton GPU 3 |
| Base Labs Mammoth-1 | `baselabs/baselabs/mammoth-1` | `local (baselabs_server.py)` | 0.10, 0 (Baseten list, 2026-11-01) | 1 | `http://127.0.0.1:18103` | bariton GPU 0 |
| SubQ Snap 1.1 | `subq/subq-snap-1.1` | `subq` | 0.04, 0 (docs.subq.ai, read today) | (none, as Preview) | (default `https://api.subq.ai`) | API |

- **Base Labs spec.** The model part must be `baselabs/elephant-1`, because the server refuses any other `model` and the runner splits the spec at its first `/`. That gives `baselabs/baselabs/…`, the same shape as `openrouter-decisions/inception/mercury-decide`. The servers start with `--name baselabs/elephant-1` and `--name baselabs/mammoth-1`, as in the Turkish runs.
- **Ports.** 18102 and 18103. The server's default, 18101, is Fastino GLiDE v1.2 (local)'s stored `base_url`.
- **Price and quantization.** Price is Baseten's list price for the same model, as the Turkish runner's `PRICES` has it. It is recorded as API-equivalent, as with Decider's Perplexity price; nothing is billed. Quantization is `bf16`.

### Code change for Base Labs (now made on branch `late3-baselabs`; see "Plan B: status")

**The runner has no decision service that matches Base Labs today** (`src/players/decision.rs` `SERVICES`). The spec `baselabs/…` fails at start with "unknown provider". There are two ways to run it:

1. **Recommended: add a service.** Insert this entry after `d3` in `SERVICES`:
   ```rust
   // Base Labs' elephant-1 / mammoth-1 behind the decision-models runner's servers/baselabs_server.py (qev's own
   // app; the model field must name the loaded checkpoint, e.g. baselabs/elephant-1). The card's trained length is
   // 16,384 tokens: state about 2,400 tokens, a described option at most about 110, so 120 options stay within it.
   Service {
       provider: "baselabs",
       label: "Base Labs (local)",
       base_url: "http://127.0.0.1:18102",
       url_var: "BASELABS_BASE_URL",
       path: "/v1/systemone",
       key_vars: &[],
       key_required: false,
       default_model: Some("baselabs/elephant-1"),
       openai_format: false,
       max_choices: 120,
   },
   ```
   - **Build from a clean worktree.** The main checkout has someone else's uncommitted work in `src/{ask,main}.rs` and `src/players/{decision,llm,mod}.rs`. Build from a worktree at HEAD plus only this entry, committed on a branch: `git worktree add /tmp/late3-build HEAD`, add the entry, commit, then `CARGO_TARGET_DIR=…/jevgammon/target/late3 cargo build --release`.
   - **Binary.** The result is `target/late3/release/jevgammon`. The start scripts check that this binary contains "Base Labs (local)".
2. **No rebuild: `BASELABS_ROUTE=d3`.** This uses the existing `d3` service, which also has no key and sends the spec's model. The spec becomes `d3/baselabs/elephant-1`, and requests carry at most 200 options. Requests can then reach about 24.4k tokens: under the engine's refusal limit, but over the card's trained 16,384. The spec also names the wrong service for good.

The choice is final once the setup is stored. `upsert_player` refuses different settings under a known name.

### Probability tolerance

- **The runner does not check sums.** In `src/players/decision.rs`, `ask` takes the answer when `choice` names an option. `probabilities` reads every value as `f64` and stores it as returned (`turns.probabilities`, `probability_source = 'decision'`). There is no sum check and no renormalization, so 6-decimal and float32 values pass unchanged. Celeris-1 Decision's 2-decimal probabilities ran the same way in League 1.
- **Downstream readers do not check sums either.** `tools/league_web.py` and the site only display the values or count whether they exist. **No code change is needed.**
- **Where the tolerances do live.** The checks are in the Turkish runner (`benchmark_ollama.py --check-probabilities`):
  - `ROUNDED_PROBABILITIES` covers Elephant-1 and Mammoth-1: to 1 within 6-decimal rounding.
  - `FLOAT32_PROBABILITIES` covers SubQ Snap 1.1: within one 2^-23 per option when every value is an exact float32. This is "an experimental 32-bit rule of ours" (run 346).
- **The plan reuses the Base Labs rule.** `late3.py smoke` applies the 6-decimal rule to the Base Labs smoke answers before any league starts.

## 2. Option counts (max_choices)

- **Backgammon option counts.** Over v3.db's 165,639 model/fallback decisions, the number of legal plays reaches **600**:
  - more than 25: 12.4% of decisions;
  - more than 110: 0.96%;
  - more than 120: 0.78%;
  - more than 200: 0.15%;
  - more than 255: 0.05% (80 decisions).
- **League 1 average.** The mean is 14.4 legal plays.
- **Long lists are split.** Every decision service splits a list longer than its `max_choices` into groups. The group winners then meet (`Player::decide`, `src/players/mod.rs`; `turns.group_size`). So the question is how many options **one request** can carry.

| model | documented limit | runner | verdict |
|---|---|---|---|
| SubQ Snap 1.1 | docs.subq.ai Decisions API (read today): a choice takes **2–255 options**; the request must fit 393,216 tokens (`400` above) | `subq` service, `max_choices` 255 (as SubQ Snap Preview) | **Yes.** One request for 99.95% of decisions; above 255 it splits, as Preview did. |
| Elephant-1 / Mammoth-1 | Card: no option cap; "Max sequence length: 16,384 tokens"; "Requests longer than the trained length limits are refused, not truncated". Engine (qev in `baselabs-serve:81ce62f`; `serve.patch` does not change the limits): 256 slot labels (`MAX_SLOTS`, `readout.json` `n_slots` 256); refuses with `ValueError` → **HTTP 422** when state + question exceeds **32,768 tokens** (`max_branch_tokens`) or the request exceeds 65,536 | none yet (code change above: 120; d3 route: 200) | **Yes, with a cap.** 255 fits the engine but runs about 2× past the trained length; **120** keeps every request inside 16,384. |

- **Request sizes, measured with the checkpoint's own `tokenizer.json`.** I took 3,000 stored League 1 System One requests (SubQ Snap Preview's, the same body).
  - State: at most **2,387 tokens** (median 2,357).
  - Instructions: 82 tokens.
  - A described option: at most **120 tokens** (mean 84; worst per-request mean 110).
  - Worst request at 120 options: about **15.7k tokens**. At 200: about 24.4k. At 255: about 30.5k.
- **Effect of a cap of 120.** It splits 0.78% of decisions.
- **Why the cap matters.** A 422 is not an invalid answer: the runner treats it as a request failure, and the match fails and is deferred again and again. A cap at or below the engine's limit is therefore required, not optional.
- **The Turkish runs did not test this.** Their questions have at most 5 options, so long lists were never exercised. The smoke step sends the 3 largest stored requests within the cap (118 options) before any league starts.

## 3. Opponents

The original League 1 table (`league_web.league_origins`, as `tools/original_league.py`) has **19 setups**. Each entrant plays each opponent once, in its own hidden late-entry league:

- `only_pairs_of` = the entrant;
- League 1's seed 2567889193785291627 with pair-v1 dice, so the pairs get the dice of that table;
- `bg-v2` prompt, option-order seed 1190975713392774006;
- `mirror_concurrent`, 3 rounds, no clock, delay 30 s, 300 turns.

Opponent settings are copied byte-for-byte from `players.settings`.

### Plan A: the API setups of League 1 (8 opponents, 24 matches)

"Reachable per config" means the key or login the config needs is present, plus the last stored use. No calls were made.

| opponent | route (spec · key) | key present | last valid match | reachable? |
|---|---|---|---|---|
| Celeris-1 Decision | `celeris/celeris-1-decision` · `CELERIS_API_KEY` from `~/.config/celeris/key` (not in `~/.keys`; the scripts load it) | yes | 2026-10-26 | yes per config |
| Fastino GLiDE | `fastino` · `FASTINO_API_KEY` | yes | 2026-10-28 (Hype Cup QF2) | yes per config; no price in its settings (cost not recorded) |
| GPT-6 Luna | `openai-decisions/gpt-6-luna` · `OPENAI_API_KEY` | yes | 2026-10-26 | yes per config |
| Jev 1.13.0 | `jev/jev-1.13.0` · `JEV_API_KEY` | yes | 2026-10-26 | yes per config |
| Jev 1.14.0 | `jev/jev-1.14.0` · `JEV_API_KEY` | yes | 2026-10-26 | yes per config |
| Liquid d1-ultra | `liquid/d1-ultra` · `LIQUIDAI_API_KEY` | yes | 2026-10-25 | yes per config (one 502 "all upstream backends failed" on 10-24, retried) |
| Mercury Decide | `openrouter-decisions/inception/mercury-decide` · `OPENROUTER_API_KEY` | yes | 2026-10-26 | **depends on OpenRouter credit** (402 history; $5.47 left on 10-28, before Kimi and DeepSeek). The script checks `/api/v1/credits` and drops it below $0.10 |
| SubQ Snap Preview | `subq/subq-snap-preview` · `SUBQ_API_KEY` | yes | 2026-10-26 | **probably not.** The SubQ models page (read today) lists only `subq-snap-1.1` ("replaced Snap Preview") and the chat model `subq-preview`. The script checks `GET /v1/models` and drops Preview if it is not listed |

**Site consequence of Plan A.** The Late entries card counts the **whole field** as a late entry's total (`analysis.late_entries`: total = the field without the entrant = 19). Under Plan A each entrant would show "8 of 19" (or 7) and keep the badge "Provisional: late entry still playing" for good. Making Plan A show as complete would need a site change, for example a stored per-entrant total (described, not made).

### Plan B: the whole original League 1 table (19 opponents, 57 matches)

These are Plan A's 8, plus 3 engines (GNUbg weak, Random, Safest: CPU, no server), plus 8 local servers. All four of bariton's GPUs are needed.

| local opponent | server script (stored base_url) | memory (README / roster) | plan B GPU |
|---|---|---|---|
| Decider v1.2 27B | `DECIDER_V12_GPU=1 decider-v1.2.sh 27b` (18099) | trio on one GPU: 73.5 GiB | 1 (wave 1) |
| Decider Flash v1.2 | `DECIDER_V12_GPU=1 decider-v1.2.sh flash` (18098) | (in the trio) | 1 (wave 1) |
| Winnow-12B | `WINNOW_GPU=1 winnow.sh` (8091) | (in the trio) | 1 (wave 1) |
| Clef | `CLEF_GPU=2 clef.sh` (18091) | 55.5 GiB | 2 (wave 1) |
| Cygnet (Gemma 4 12B) | `CYGNET_GPU=2 CYGNET_UTIL=0.34 cygnet.sh` (18093) | 32.5 GiB | 2 (wave 1) |
| Fastino GLiDE v1.2 (local) | `GLIDE_GPU=3 glide-v12.sh` (18101) | 53.6 GiB | 3 (wave 1) |
| Open-Jev 27B v1.1 | `OPEN_JEV_GPU=2 open-jev.sh` (8791) | 52.8 GiB | 2 (wave 2) |
| Decider v1.1 27B | `DECIDER_GPU=3 decider.sh` (18097) | 51.6 GiB | 3 (wave 2) |
| *Mammoth-1 (entrant)* | `baselabs.sh mammoth` (18103) | 54.7 GB weights, about 60+ GB in use [INFERENCE, unmeasured] | 0 (both waves) |
| *Elephant-1 (entrant)* | `baselabs.sh elephant` (18102) | 18.8 GB weights, about 25 GB [INFERENCE] | 3 (both waves, next to lfm3-audio's 6.4 GB) |

**The servers do not all fit at once.** They need about 405 GiB, plus lfm3-audio's 6.4, against 4 × 95.6 = 382 GiB. So there are two waves:

- **Wave 1.** Open-Jev and Decider v1.1 join only after Clef, Cygnet and GLiDE v1.2 have played all three entrants.
- **Wave 2.** The unit `late3-wave2` then stops those three servers, starts Open-Jev and Decider v1.1, adds both with `league-add` (the Astra/Kimi pattern), and resumes any league that already finished.

**GPUs today (nvidia-smi, read only):**

| GPU | in use | by |
|---|---|---|
| 0 | free | — |
| 1 | 94.6 GB | pplx `decider_server.py --port 8960`, up 3 days; docker vLLM `cmp-qwen25-14b`, up 21 h |
| 2 | 79.7 GB | ComfyUI (`main.py --listen`, 51.5 GB); ai-toolkit (28.3 GB) |
| 3 | 6.6 GB | lfm3-audio llama-server |

**Plan B needs GPUs 1 and 2 released by their owners.** `start_B.sh` refuses to start otherwise. **Plan A needs only GPU 0 and GPU 3, which are free enough now.**

## 4. Estimates (from v3.db League 1 averages)

**Basis.** These are the 171 valid finished matches between League 1 table members, late entries excluded.

- **Decisions.** A model side averages **110.4 decisions per match** (5.3 games).
- **Cost per opponent match (billed):**

  | opponent | $ per match |
  |---|---|
  | Celeris | 0.0178 |
  | Fastino GLiDE | ≈0.018 at $0.04/M; its settings have no price |
  | GPT-6 Luna | 0.0366 |
  | Jev 1.13.0 | 0.0168 |
  | Jev 1.14.0 | 0.0187 |
  | Liquid | 0.0169 |
  | Mercury Decide | 0.0072 (OpenRouter) |
  | SubQ Snap Preview | 0.0228 |

- **Entrants.**
  - SubQ Snap 1.1: 110.4 × 3,847 tokens (Preview's count on the same API) × $0.04/M = **$0.017 per match**.
  - Base Labs: about 3,780 tokens per decision with the Qwen3.5 tokenizer at a 120-option cap. At Baseten list prices that is $0.0146 per match for Elephant and $0.0417 for Mammoth. These are API-equivalent figures only; **$0 is billed**.

| | Plan A | Plan B |
|---|---|---|
| Matches | **24** (8 × 3); 21 if Preview is gone, 18 if Mercury is also dropped | **57** (19 × 3); 54 / 51 likewise |
| Entrants' decisions | ≈ 2,650 | ≈ 6,290 |
| Billed, opponents | ≈ **$0.47** (Luna $0.11, Jev $0.11, Preview $0.07, Fastino $0.05, Celeris $0.05, Liquid $0.05, OpenRouter $0.02) | ≈ **$0.47** (the same 8; local and engine opponents $0) |
| Billed, SubQ Snap 1.1 | ≈ **$0.14** | ≈ **$0.32** |
| **Billed total** | **≈ $0.60** | **≈ $0.79** |
| API-equivalent, not billed | Elephant $0.12, Mammoth $0.33 | Elephant $0.28, Mammoth $0.79, Decider opponents $0.07 |
| GPUs | 0 and 3 | all four (1 and 2 freed first) |
| Wall time | **≈ 45–60 min**: server start and smoke tests ≈ 10–15 min, then the three leagues at once; Mammoth bounds it at ≈ 883 own decisions × ≈ 1.2 s, served one at a time ≈ 18 min, plus opponents' turns ≈ 25–35 min. Elephant ≈ 15–20 min; SubQ ≈ 10 min | **≈ 2.5–3 h**: wave 1 start ≈ 20 min (8 servers in turn), wave 1 ≈ 1.5 h (Mammoth's own ≈ 42 min, served one at a time; Clef 3 × 107 × 4.6 s ≈ 25 min; Winnow ≈ 17 min), swap ≈ 10 min, wave 2 ≈ 30 min (Decider v1.1 3 × 112 × 4.3 s ≈ 24 min) |

**Speed basis [INFERENCE].** Base Labs speed in backgammon is unmeasured. Mammoth-1 is assumed to match Decider v1.2 27B (same Qwen3.5-27B backbone and GPU type; 1.24 s per decision in League 1). Elephant-1 (9B) is assumed at ≈ 0.6 s. The smoke step logs real request times and memory before any league starts.

## 5. Launch (not run)

- **Plan A:**
  ```sh
  CAN_GO=yes [BASELABS_ROUTE=d3] workspace/late3/start_A.sh
  ```
  1. Free checks (GETs only): SubQ must list `subq-snap-1.1` (otherwise stop); Preview and Mercury are dropped if unavailable.
  2. Start Mammoth-1 on GPU 0 and Elephant-1 on GPU 3.
  3. Smoke-test both (20 stored requests each: valid choice, probabilities sum to 1 within 6-decimal rounding).
  4. Log `nvidia-smi`.
  5. Back up v3.db to `v3.db.bak-<ts>-before-late3-A.zst`.
  6. Generate the configs and add the three names to the `late_entry_stage` trigger. Without that, the runner's matches get `stage = 'league'`.
  7. Start three user units `late3-<slug>`, logging to `late3-<slug>.log`.
- **Plan B:**
  ```sh
  CAN_GO=yes [BASELABS_ROUTE=d3] workspace/late3/start_B.sh
  ```
  It does the same after a GPU-free check, with wave 1's 8 servers. It then starts the `late3-wave2` unit.
- **Stopping.** Stop commands are printed at the end. The servers do not stop by themselves.

### Bus GPU claim (to post at go)

**Plan A:**

> Claim (jevgammon, Can's go): bariton **GPU 0** (Base Labs Mammoth-1, ≈ 60 GB) and **GPU 3** (Base Labs Elephant-1, ≈ 25 GB, next to lfm3-audio's 6.4 GB, which stays). Docker `v3-baselabs-mammoth` :18103 and `v3-baselabs-elephant` :18102 on 127.0.0.1. From now for ≈ 1 h (late-entry matches v League 1's API setups). Please keep both GPUs free of new jobs until I post the release.

**Plan B:**

> Claim (jevgammon, Can's go): **all four bariton GPUs** for ≈ 3 h (late entries v the whole original League 1 table). GPU 0 Mammoth-1; GPU 1 Decider v1.2 27B + Flash v1.2 + Winnow-12B; GPU 2 Clef + Cygnet, later Open-Jev; GPU 3 Elephant-1 + GLiDE v1.2, later Decider v1.1 (lfm3-audio's 6.4 GB stays). **Needs GPU 1 freed (pplx decider_server :8960, vLLM cmp-qwen25-14b) and GPU 2 freed (ComfyUI, ai-toolkit) by their owners first.** I post the release when the servers stop.

## Plan B: status (Nov 2, after Ümit's choice)

### Runner: `baselabs` service built (branch, not main)

- **Branch.** `late3-baselabs` (pushed; `origin/main` f32636a + 2 commits):
  - 6d66b04 adds the `baselabs` service to `src/players/decision.rs` as described above (cap 120), with a unit test, plus a README provider row;
  - 104103a is rustfmt only.
- **Worktree.** `/home/cbasaran/code/jevgammon-late3`, made clean from `origin/main` and not from the dirty main checkout.
  - The runner records its harness commit from this directory, so it must stay.
  - It records 104103a, clean.
- **Binary.** `target/late3/release/jevgammon`. It contains "Base Labs (local)", which is what `start_B.sh` checks.
- **Tests.**
  - `cargo test --release --bin jevgammon players::`: 31 passed, including the new `decision::tests::baselabs_sends_the_checkpoint_name_to_the_configured_server` (URL from `base_url`, `model` = `baselabs/mammoth-1`, cap 120, no key).
  - `rustfmt --check` on `decision.rs` is clean.
- **Route.** `BASELABS_ROUTE=d3` is no longer needed. Plan B uses `spec baselabs/baselabs/{elephant,mammoth}-1`.

### Opponent check (read-only, no calls, Nov 2)

All 19 setups of the original League 1 table are ready per their stored settings:
- every API key is set (non-empty);
- every local server's script, venv, checkpoint and Docker image is on disk;
- every port is free (nothing listening on 18091, 18093, 8892, 18097, 18098, 18099, 8091, 18101, 8791, 18102 or 18103);
- `/usr/games/gnubg` is present.

| # | opponent | route (stored spec) | ready without a call | server / port / GPU in plan B |
|---|---|---|---|---|
| 1 | Celeris-1 Decision | `celeris/celeris-1-decision` | key in `~/.config/celeris/key` | API |
| 2 | Fastino GLiDE | `fastino` (model `fastino/GLiDE`) | `FASTINO_API_KEY` set | API |
| 3 | GPT-6 Luna | `openai-decisions/gpt-6-luna` | `OPENAI_API_KEY` set | API |
| 4 | Jev 1.13.0 | `jev/jev-1.13.0` | `JEV_API_KEY` set | API |
| 5 | Jev 1.14.0 | `jev/jev-1.14.0` | `JEV_API_KEY` set | API |
| 6 | Liquid d1-ultra | `liquid/d1-ultra` | `LIQUIDAI_API_KEY` set | API |
| 7 | Mercury Decide | `openrouter-decisions/inception/mercury-decide` | `OPENROUTER_API_KEY` set; **credit checked at go** (dropped below $0.10) | API |
| 8 | SubQ Snap Preview | `subq/subq-snap-preview` | `SUBQ_API_KEY` set; **model probably retired** (SubQ's models page); `/v1/models` checked at go, dropped if absent | API |
| 9 | GNUbg weak | `gnubg-weak` | `/usr/games/gnubg` | CPU |
| 10 | Random | `random` | built in | CPU |
| 11 | Safest | `safest` | built in | CPU |
| 12 | Decider v1.2 27B | `pplx-local/pplx-decider-v1.2` | `.venv-v1.2`, HF snapshot 225c913 | `DECIDER_V12_GPU=1 decider-v1.2.sh 27b`, :18099, **GPU 1**, wave 1 |
| 13 | Decider Flash v1.2 | `pplx-local/pplx-decider-flash-v1.2` | `.venv-v1.2`, `checkpoint-flash-v1.2` | `DECIDER_V12_GPU=1 decider-v1.2.sh flash`, :18098, **GPU 1**, wave 1 |
| 14 | Winnow-12B | `winnow/winnow-12b` | image `winnow-inference:d4631fb`, `~/code/winnow/models` | `WINNOW_GPU=1 winnow.sh`, :8091, **GPU 1**, wave 1 |
| 15 | Clef | `clef` | `~/code/clef/.venv`, `~/code/clef/model` | `CLEF_GPU=2 clef.sh`, :18091, **GPU 2**, wave 1 |
| 16 | Cygnet (Gemma 4 12B) | `cygnet` | image `vllm/vllm-openai:v0.30.0`, gemma-4-12B-it @ 707f0a3b, shim | `CYGNET_GPU=2 CYGNET_UTIL=0.34 cygnet.sh`, :18093 (+ vLLM :8892), **GPU 2**, wave 1 |
| 17 | Fastino GLiDE v1.2 (local) | `fastino/glide-v1.2` (base_url :18101) | `~/code/glide/.venv`, HF fastino/GLiDE @ a7e45896 | `GLIDE_GPU=3 glide-v12.sh`, :18101, **GPU 3**, wave 1 |
| 18 | Open-Jev 27B v1.1 | `open-jev` | `~/code/Open-Jev/.venv`, checkpoint, Qwen3.8-27B @ 1d4bf0f2 | `OPEN_JEV_GPU=2 open-jev.sh`, :8791, **GPU 2**, wave 2 |
| 19 | Decider v1.1 27B | `pplx-local` (base_url :18097) | `~/code/pplx-decider/.venv`, `checkpoint` | `DECIDER_GPU=3 decider.sh`, :18097, **GPU 3**, wave 2 |

The entrants are ready too:
- Mammoth-1 on **GPU 0** (`baselabs.sh mammoth`, :18103) and Elephant-1 on **GPU 3** (`baselabs.sh elephant`, :18102), both waves;
- image `baselabs-serve:81ce62f` and both snapshots are present;
- SubQ Snap 1.1 runs through the API with `SUBQ_API_KEY`.

### GPUs now (`nvidia-smi`, read only, Nov 2) and what plan B needs

| GPU | held now by | plan B wave 1 | plan B wave 2 |
|---|---|---|---|
| 0 | free (41 MiB) | Mammoth-1 | Mammoth-1 |
| 1 | **compactor**: pplx-decider venv `decider_server.py --port 8960` (pid 146742, cwd `~/code/compactor/exp-grpo`, 60.6 GB, up 3 days) and docker vLLM `cmp-qwen25-14b` (33.9 GB, up 22 h); 94.6 GB, idle (0%) | Decider v1.2 27B + Decider Flash v1.2 + Winnow-12B (73.5 GiB) | the same three, until the leagues end |
| 2 | **ComfyUI** (`main.py --listen`, 51.5 GB, up 1 d 19 h) and **ai-toolkit** training job `output/nsfw_perreal` (25.9 GB, running 3 h 47 min, 100% busy); 78.5 GB | Clef + Cygnet (≈ 88 GiB) | Open-Jev (52.8 GiB) |
| 3 | **lfm3-audio** llama-server (`lfm3-audio-llama.service`, 6.6 GB) | Elephant-1 (≈ 25 GB [INFERENCE]) + GLiDE v1.2 (53.6 GiB) next to lfm3-audio | Elephant-1 + Decider v1.1 (51.6 GiB) next to lfm3-audio |

`start_B.sh` refuses to start unless GPUs 0, 1 and 2 have at most 2 GB in use and GPU 3 at most 8 GB.

### Remaining blockers (each needs Can or another owner)

1. **Can's approval** of three things:
   - the roster: the three entrants against the 19-setup original League 1 table, 57 matches;
   - the GPUs: all four of bariton's for ≈ 2.5–3 h;
   - the spend: ≈ $0.79 billed, across OpenAI, TypeSafe, SubQ, Celeris, Liquid, Fastino and OpenRouter.
2. **GPU 1 freed by compactor's owner.** That means stopping `decider_server.py --port 8960` (pid 146742) and the `cmp-qwen25-14b` container.
3. **GPU 2 freed by Can.** That means stopping or moving ComfyUI and the running ai-toolkit `nsfw_perreal` training job.
4. **GPU 3:** lfm3-audio's owner keeps its 6.6 GB but adds nothing more there for the duration. No stop is needed.

Not blockers, handled at go by `start_B.sh`, but for Can to know:
- SubQ Snap Preview is dropped if SubQ no longer lists it, which makes 18 opponents.
- Mercury Decide is dropped if OpenRouter has less than $0.10 free; a top-up is Can's choice.
- Base Labs memory and speed are measured by the smoke step before any league starts.
- Merging `late3-baselabs` into main is not needed for the run.
