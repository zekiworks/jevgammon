# Late entries Drex - plan 2026-11-05

Nov 5, 2026 · for Can and Ümit (Ümit's request, bus #1159; Zeki's review of 7f8f38e, bus #1167, applied). **Prepared only.**

- **Nothing run:** no match, no model request, no server, no GPU use, no download, no spend. v3.db was only read.
- **HTTP reads, all free:** Nace's docs and pricing pages, Hugging Face metadata (no weights), the Decision Models page, and one read of an account's free credit.
- **Format:** the 2 Nov late entries 3, plan B: each entrant plays all 19 setups of the original League 1 table once.

## Decision needed (Can)

Can's decisions are reserved: rosters, model servers and money. The source is his in-session instruction; there is no written mailbox rule. Precedents: `mailbox/League 3 - GPT-6 Astra (high) estimate 2026-10-28.md:122` ("Waiting for Can's approval.") and Can's go for plan B on 2 Nov.

| | (a) API stage: `start_api.sh` | (b) GPU stage: `start_gpu.sh` |
|---|---|---|
| What | Drex Max 1.1 and Drex 2.0 (Nace API) v the 8 API setups and 3 programs | Drex Max v1 (our GPU) v all 19; the 8 local setups v Drex Max 1.1 and Drex 2.0 |
| Matches | **22** | **35**. With the optional Drex 2.0 (local): 54 |
| Billed (est.) | **≈ $0.76** | **≈ $0.48**. With Drex 2.0 (local): ≈ $0.63 |
| Time | **≈ 35–45 min**; no GPU | **≈ 1.5–1.75 h** once GPUs are free (≈ 2.5–3 h with Drex 2.0 (local)) |
| Needs | Can's go | Can's go, plus GPUs freed by their holders (see GPUs) |

- **Both stages:** 57 matches, ≈ $1.24 billed (≈ $1.39 with Drex 2.0 (local)).
- **Not billed:** Drex Max v1 at list-price equivalent ≈ $0.60; Drex 2.0 (local) ≈ $0.49.

**Budget facts:**
- **OpenRouter** is used only by the opponent Mercury Decide, which needs ≈ $0.02 here. The free credit read today covers it.
- **Nace account:** balance, limits and tier are **unknown** without a call or the dashboard. Nace refuses requests (402) at zero balance unless auto-pay is on.
- **No top-up of any account without Can.**

## 1. Runner (branch `late-drex`, not main)

- **Commits.** Branch `late-drex` is pushed at `eea4de5`: `late3-baselabs` (unmerged) with `origin/main` merged in, then `ec18e90` (services) and `eea4de5` (review fixes).
- **Worktree and binary.** Clean worktree `/home/cbasaran/code/jevgammon-drex`; the harness commit is read from it at run time. Binary `target/drex/release/jevgammon`.
- **Tests.** `cargo test --release --bin jevgammon`: **77 passed**, including 3 new tests in `players::decision`.
- **Clients.** All three use the System One request and answer parsing of every other decision service. The hosted endpoint is Nace's, as the Turkish runner uses it.

| provider | for | endpoint | options per request |
|---|---|---|---|
| `nace` | Drex Max 1.1 (`nace/drex-max-v1.1`), Drex 2.0 (`nace/drex-v2.0`) | `https://console.nace.ai/v1/systemone` | **25** |
| `drex-max` | Drex Max v1 (`drex-max/drex-max-v1`) | `http://127.0.0.1:18104` | **25** |
| `drex-local` | optional Drex 2.0 (local) (`drex-local/drex-v2.0`) | `http://127.0.0.1:18105` | **25** |

- **Model ids** come from the Turkish results db: `drex-max-v1.1` and `drex-v2.0`; the stored responses name the same model.
- **Ports.** 18104 and 18105. The Turkish default for `drex_max_server.py` is 18099, which is Decider v1.2 27B's stored `base_url`.

## 2. Options per request: 25, as Ümit specified

- **The Drex rule.** The four Drex setups get **at most 25 options per request** (Ümit, #1159), the same as the Deciders.
  - A longer list is split into equal groups of at most 25.
  - Each group gets one request and a winner; the winners then play a final. Further rounds follow only if there are more than 25 winners, which never happens in League 1.
- **Only these setups change.** The cap is the service's `max_choices` (`nace`, `drex-max`, `drex-local`), used only by these players. Every earlier setup and result is untouched.
  - The other League 1 decision models keep their own caps:

    | cap | models |
    |---|---|
    | 25 | Deciders |
    | 26 | Cygnet |
    | 40 | Winnow |
    | 110 | Clef |
    | 255 | Open-Jev and every hosted API |
    | 120 | Base Labs (late entries 3) |
    | 255 | SubQ Snap 1.1 (late entries 3) |

  - v3.db confirms these caps from the largest unsplit lists.
- **How groups are cut** (`Player::decide`, unchanged). With n options, the runner makes `ceil(n/25)` groups of `ceil(n/groups)` in the seeded shown order. They are equal except the last, which can be smaller. A one-play group passes straight through. `turns.group_size` records the size.
- **Effect at cap 25.** Over League 1's **36,995 decisions** (v3.db, model or fallback, two or more legal plays):
  - **10.9%** are split.
  - A decision takes **1.293 requests on average** (1.0004 at cap 255), and at most 20.
  - Input tokens rise by **×1.206** per decision (4,474 against 3,710). Each extra request repeats the state, about 2,529 tokens, plus about 84 per option.

## 3. Probabilities: every group's and the final's are recoverable

**Check (v3.db, read-only, all of it).** Every decision-service turn with stored probabilities (`probability_source = 'decision'`, two or more plays) was rebuilt from its `exchanges` rows alone:
- the runner's grouping was replayed over `turns.option_order`;
- each request's option list (`criteria` keys, or `choices` values for OpenAI's format) was matched to its group;
- the response's probabilities had to cover exactly those options;
- each group's choice was followed through to the final;
- the final's winner had to equal `turns.chosen_index`.

| | turns | requests (exchanges) | probabilities recovered | failures |
|---|---|---|---|---|
| all | **62,510** | 66,054 | **887,491** | **0** |
| of them split into groups | 1,384 | | | 0 |

- **Play ids.** In every request, the option names are the plays' notations, and there are exactly as many as the group's plays. No notation collides, so each notation maps to one play.
- **Position.** The k-th option of group g is `option_order[g × group_size + k]`, so a play's id (its index in `turns.option_order`) is recovered without recomputing the legal plays.
- **Coverage.** Every returned probability, in every group and in the final, is in `exchanges.response` as returned.

**Worked example, turn 219740** (Decider v1.1 27B, 69 legal plays, `group_size` 23):

| request | options | first option = play | probabilities sum | group winner (p) |
|---|---|---|---|---|
| 1 | 23 | `16/15 15/14 4/3 3/2` = `option_order[0]` | 1.000000 | `6/5 6/5 4/3 4/3` (0.4106) |
| 2 | 23 | `16/15 15/14 8/7 4/3` = `option_order[23]` | 1.000000 | `16/15 16/15 8/7 8/7` (0.4167) |
| 3 | 23 | `8/7 4/3 4/3 3/2` = `option_order[46]` | 1.000000 | `6/5 6/5 4/3 3/2` (0.2603) |
| final | 3 | the three winners | 1.000000 | `6/5 6/5 4/3 4/3` (0.7953) = `chosen_index` 63 |

- **`turns.probabilities` keeps only the final's three values**, with 66 nulls, by design.
- **No global distribution is ever built from the groups.** Readers take each request's probabilities from `exchanges`.
- **No storage addition is needed.** The protocol and the tables are unchanged.
- **Limit.** A failed HTTP attempt that was retried has no row: only the answered attempt's request and response are stored, and the retry time is in `turns.retry_ms`. That loses no probability.

## 4. Setups and prices (read 2026-11-05)

| setup | route | weights / loader | price in config ($/M input; output free) | billed |
|---|---|---|---|---|
| **Drex Max 1.1** | Nace API | no open weights | **0.06** list (nace.ai/drex) | **$0.03** launch price (console.nace.ai/docs/drex/reference/pricing) |
| **Drex 2.0** | Nace API | — | **0.06** (console pricing) | $0.06 |
| **Drex Max v1** | our GPU | `nace-ai/drex-max-v1` @ **cac65e1982a0237e996419ba559004522d9a33ac** (the cached snapshot: 49 GB, bf16), with Nace's `drex_max` at e206b27 behind the decision-models runner's `servers/drex_max_server.py`, as the Turkish runs served it | **0.06**, "list price for the hosted model, not billed", as on the Decision Models page (source nace.ai/drex) | $0 |
| **Drex 2.0 (local)**, optional | our GPU | see below | 0.06, list price for the hosted model, not billed | $0 |

- **Probabilities.** Stored as returned. Drex 2.0 rounds them to 4 decimals, hosted and local; the runner checks no sums.
- **Drex 2.0 (local), from Hugging Face metadata only:**
  - `nace-ai/drex-v2.0` @ **e646674476744e3826caf62b834054151e2aba51**: 16 shards, **70.2 GB**; `Qwen3_5MoeForConditionalGeneration` (40 layers, 256 experts, 8 active, bf16).
  - It is **not** the Drex Max v1 loader. It ships its own `serve.py` with Nace's `kev` loader and pointer head, takes the same System One request and returns `{model, answers, usage}`. That is why it has its own service, `drex-local`.
  - It needs torch <2.9, so a new Python environment. GPU: one RTX PRO 6000 of its own (≈ 72 GB of weights).
  - `drexv2.sh download` refuses without `CAN_GO=yes`.

## 5. Opponents and GPUs

Each entrant plays the same 19 setups as plan B.

**No opponent is left out.** If an opponent cannot be reached at go (out of credit, model withdrawn):
- it stays in the league and its pairs stay **blocked**;
- once nothing else can be played, the run ends as **INCOMPLETE SCOPE**, listing every missing pair (`drex.py scope`);
- the same scripts play those pairs once they are unblocked.

**Without a GPU (stage a):**

| opponents | route |
|---|---|
| Celeris-1 Decision, Fastino GLiDE, GPT-6 Luna, Jev 1.13.0, Jev 1.14.0, Liquid d1-ultra | their stored API routes |
| Mercury Decide | OpenRouter |
| SubQ Snap Preview | SubQ API |
| GNUbg weak, Random, Safest | CPU |

**On GPUs (stage b), the same scripts and settings as plan B:**
- Decider v1.2 27B + Decider Flash v1.2 + Winnow-12B (73.5 GiB together)
- Clef (55.5)
- Cygnet (32.5)
- Fastino GLiDE v1.2 (local) (53.6)
- Open-Jev 27B v1.1 (52.8)
- Decider v1.1 27B (51.6)
- the entrant Drex Max v1 (48.6 GiB loaded per its card; job need 60 GB)

**GPUs now (read only, 06:42Z):**
- All four are held by Turkce's DeepSeek V4.1 Flash 1017 repeat runs (sglang TP4, ≈ 86 GB each), expected to end about 07:43 UTC (an estimate).
- **GPU 0 is claimed by compactor for ≈ 30 h (bus #1038).**
- Main coordinates the GPU start with @turkce and compactor.

**How stage b uses GPUs.** `drex-orch-gpu` only uses `DREX_GPUS` (default "1 2 3"). It starts a server only on a GPU whose free memory covers its need plus 2 GB, so it waits for actually free GPUs and never stops anyone else's process. Expected layout:

| wave | GPU 1 | GPU 2 | GPU 3 |
|---|---|---|---|
| 1 | Drex Max v1 (first) + Cygnet | Decider v1.2 27B + Flash + Winnow | Clef |
| 2 (as wave-1 servers finish) | Drex Max v1 | GLiDE v1.2 (local), then Decider v1.1 | Open-Jev |

- **Stopping.** Each opponent server stops once it has played every entrant, and Drex Max v1 once it has played all 19. The release text goes to the status file.
- **Drex 2.0 (local)** (`DREX_LOCAL=yes`) needs a whole free GPU first.

## 6. Spend cap: what is hard and what is soft

- **Hard pre-send cap on the Drex entrants' Nace requests.**
  - Drex Max 1.1 and Drex 2.0 carry a `budget` in their configs: one ledger shared by both, **cap $1.25**, at the billed prices.
  - The runner's existing budget ledger (`src/budget.rs`, until now for openai-compatible chat servers) now also meters decision services.
  - **Before each attempt, retries included**, it reserves the worst case: every request byte counted as an input token, and as many output tokens. It refuses the call when spent + reserved + the new reservation would pass the cap; nothing is sent.
  - An answered attempt is booked at its reported `usage`. One with no response or unreadable usage keeps its worst case, so failed and retried calls are counted conservatively.
  - Test: `budget_refuses_a_request_before_sending_it_past_the_cap`, a local test server. The first request goes out and is booked at its usage; the second is refused with "BUDGET CAP" and the server sees no second request; a second process on the same ledger sees the same spend.
  - $1.25 covers the estimated Nace spend (≈ $0.79) with margin and leaves room within $2 for the opponents.
- **Opponents' spend: soft stop only.** The 8 API opponents are not metered before sending: their stored settings must stay unchanged, and a `budget` would change them.
  - Their spend, ≈ $0.45–0.60 estimated, is covered by a **periodic soft stop**. Every 5 minutes, `drex.py billed` totals the billed cost of every late-entry match since the first one, entrants and opponents.
  - Above $2, our leagues and servers stop. Spend between two checks is not prevented.
  - **The $2 total is therefore a soft stop, not a hard cap.** Only the Nace part ($1.25) is hard.

## 7. Estimates

**Basis:**
- **Decisions.** 115 decisions per entrant per match (late entries 3: 107–122).
- **Tokens at cap 255.** From SubQ Snap 1.1's 3,743 per decision in late entries 3, scaled by the Turkish runs' tokens per question against SubQ's 385:

  | setup | tokens per question | tokens per decision at cap 255 |
  |---|---|---|
  | Drex Max 1.1 | 385 | 3,743 |
  | Drex 2.0 | 319 | 3,100 |
  | Drex Max v1 | 388 | 3,770 |

- **At cap 25,** tokens per decision go ×1.206 (section 2): **4,514**, **3,739** and **4,547**.
- **Opponents' billed cost.** Late entries 3's actual $0.151 per entrant for the 8 API setups.

| | matches | Drex requests (est.) | entrants' billed | opponents' billed | total billed |
|---|---|---|---|---|---|
| (a) API stage | 22 | ≈ 3,270 | Drex Max 1.1 $0.17 (at $0.03) + Drex 2.0 $0.28 | $0.30 | **$0.76** |
| (b) GPU stage | 35 | ≈ 5,200 (Nace ≈ 2,380) | Drex Max 1.1 v 8 local $0.12 + Drex 2.0 v 8 local $0.21 | Drex Max v1's 8 API opponents $0.15 | **$0.48** |
| (b) + Drex 2.0 (local) | +19 | +≈ 2,830 (local) | $0 | +$0.15 | **$0.63** |

- **Time.** Late entries 3 played its first 45 matches in 25 min and its last 12 in 26 min. Requests per decision rise ×1.29 at cap 25, so the Drex side's request time grows by about 29%.
  - The hosted Drex took 0.31–0.32 s per question in the Turkish runs. Backgammon prompts are longer [INFERENCE: ≈ 0.3–0.6 s per request hosted].
  - Hence ≈ 35–45 min for (a), and ≈ 1.5–1.75 h for (b) after GPUs are free, server starts included.
- **Rate.** Two hosted entrants make about 100 Nace requests per minute at peak [INFERENCE from late entries 3's ≈ 40 decisions per minute per entrant × 1.29]. That is near Nace's lowest published request rate. A 429 is retried with backoff, so it slows play but does not lose decisions.

## 8. Launch (not run)

Files in `workspace/drex/` (not committed): `players.json`, `drex.py`, `drexmax.sh`, `drexv2.sh`, `run_league.sh`, `orchestrate.sh`, `start_api.sh`, `start_gpu.sh`. Both start scripts refuse without `CAN_GO=yes` (checked).

1. **`CAN_GO=yes workspace/drex/start_api.sh`**
   - Free checks (GETs only): Nace must list both model ids, or nothing starts. Opponent availability is only noted (privately), never acted on.
   - v3.db backup, first match id, status file `mailbox/Late entries Drex - status 2026-11-05.md`, then `drex-orch-api`.
2. **`CAN_GO=yes workspace/drex/start_gpu.sh`** can run alongside step 1.
   - `drex-orch-gpu` waits for GPU room, starts Drex Max v1 and its league, then the opponent servers, adding them by `league-add`.
   - Worth running first: the local smoke test `drex.py smoke http://127.0.0.1:18104 drex-max-v1` (20 stored requests up to 25 options, on our own server, free).
3. **Stage rules:** stage `late-entry` through the trigger, League 1's rules, one hidden league per entrant (`only_pairs_of`).

## Blockers

1. **Can's go** for (a), (b), or both; the roster with or without Drex 2.0 (local) and its 70.2 GB download; and the money (≈ $0.76 + $0.48).
2. **GPUs for (b):** Turkce's DeepSeek runs hold all four (until about 07:43 UTC, estimated), and GPU 0 is compactor's claim. Main coordinates; the scripts only wait.
3. **Nace account state is unknown** without a call or the dashboard. A 402 blocks the Drex pairs (reported as INCOMPLETE SCOPE); a top-up needs Can.
