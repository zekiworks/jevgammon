# Small models on the backgammon bench: plan (Ümit #6225, 2026-11-13)

For Ümit via Main. JSON twin: `small-backgammon-bench-2026-11-13.json`. **Nothing has been started**: no model run, GPU job, league unit or v3.db write. All numbers are from v3.db (read-only), the site's own state (read-only) or CPU tokenizers; estimates are marked [INFERENCE] with their basis.

Models (16 setups): chat LFM3-1.7B (on), MiniCPM5-2B (on) (thinking on); decision Liquid d1-2B, GLiDE 2B, GLiDE 0.8B, GLiDE 0.4B, KnowLine 4B Gen5.5, KnowLine-2B-Gen1, KnowLine-0.8B-Gen1, StartLux-Decision v1.1 2B (Instant), StartLux-Decision-v1.1-0.8B-Instant, OneJev1.6-0.8B, Strands Decider 2B, Metask-Jev-4B, GLiClass v4 Edge; Decider Flash v1.2 (already in League 1).

## 0. Summary table

| Model (setup) | League play now (league; first stage / local) | Late entry prepared | Part 2 runnable | Learning arms | Invalid share so far |
|---|---|---|---|---|---|
| LFM3-1.7B (on) | none | yes: `late-smallchat-on` a083fb4 (repinned to logic's vLLM nightly; read-out fix) | yes | all four: fit (61,245 of 69,632 tokens) | not played; (off) none either |
| MiniCPM5-2B (on) | none; (off) proxy L39 9/9, 0/8 | yes after a runner fix: `late-smallchat-on` 7170908 | yes | all four: fit (61,139 of 69,632), with the same runner fix | not played; (off) 0 / 976 |
| Liquid d1-2B | none | yes: `late-tiny8-small3` 8ebad40 (new provider d1-local) | yes | no-memory + full records: fit (29,766 of 128,000) | not played |
| Strands Decider 2B | none | yes: `late-tiny8-small3` (provider strands, 13 options/request) | yes | **skip**: 4,096-token window < record + request | not played |
| Metask-Jev-4B | none | yes: `late-tiny8-small3` (provider metask, 11 options/request) | yes | **skip**: 4,096-token limit | not played |
| GLiDE 2B | L41 9/9, 0/8 | done (late-tiny8) | yes | fit (34,603 of 39,992) | 0 / 818 |
| GLiDE 0.8B | L42 9/9, 0/8 | done | yes | fit (31,650 of 39,992) | 0 / 983 |
| GLiDE 0.4B | L43 9/9, 0/8 | done | yes | **skip**: 7,999-token limit; 348 of 840 requests over with the largest record | 0 / 765 |
| KnowLine 4B Gen5.5 | L22 9/9, 0/8 | done (late-knowline4b) | yes | fit (32,706 of 262,138); caveat: read-twice switches off past 3,000 tokens | 0 / 1,146 |
| KnowLine-2B-Gen1 | L40 9/9, 0/8 | done | yes | fit (29,262); same caveat | 0 / 1,004 |
| KnowLine-0.8B-Gen1 | L25 9/9, 0/8 | done | yes | fit (27,916); same caveat | 0 / 868 |
| StartLux-Decision v1.1 2B | L23 9/9, 0/8 | done (late-startlux2b) | yes | fit (29,886 of 131,072) | 0 / 846 |
| StartLux-Decision-v1.1-0.8B-Instant | L27 9/9, 0/8 | done | yes | fit (30,870 of 131,072) | 0 / 880 |
| OneJev1.6-0.8B | L30 9/9, 0/8 | done | yes | partial: 1 of 977 requests over 32,768 with the largest record | 0 / 977 |
| GLiClass v4 Edge | L36 9/9, 0/8 | done | yes | partial: 12 of 744 over 16,384 with the largest record | 0 / 725 |
| Decider Flash v1.2 | League 1 original, 18/18 | — | yes (added: 'all of them') | no-memory + full records: fit (11,099 of 262,144) | 0 / 2,309 |

## 1. League play

### 1.1 Status (v3.db, read-only, ~15:15Z)
Each late entry has its own hidden league (`leagues.only_pairs_of`) that plays the original League 1 field (19 setups). First stage = the 3 programs + 6 paid API setups (9 required; Mercury Decide not required, Ümit #5220; GPT-6 Luna deferred). Local stage = the 8 setups on our GPUs (`locals.sh`).

| Setup | player | league | first stage | local | finished match ids | open |
|---|---|---|---|---|---|---|
| KnowLine 4B Gen5.5 | 63 | 22 | 9/9 | 0/8 | 957–965 | #966 Mercury (aborted, not required) |
| StartLux-Decision v1.1 2B | 64 | 23 | 9/9 | 0/8 | 970–978 | #979 Mercury |
| KnowLine-0.8B-Gen1 | 66 | 25 | 9/9 | 0/8 | 983–991 | #992 Mercury |
| StartLux-Decision-v1.1-0.8B-Instant | 68 | 27 | 9/9 | 0/8 | 1000, 1001, 1003, 1006, 1007, 1009, 1010, 1012, 1014 | #1015 Mercury |
| OneJev1.6-0.8B | 71 | 30 | 9/9 | 0/8 | 1041–1049 | #1050 Mercury |
| GLiClass v4 Edge | 76 | 36 | 9/9 | 0/8 | 1141–1144, 1165–1169 | #1170 Mercury |
| KnowLine-2B-Gen1 | 80 | 40 | 9/9 | 0/8 | 1181–1189 | #1190 Mercury |
| GLiDE 2B | 81 | 41 | 9/9 | 0/8 | 1191–1199 | #1200 Mercury |
| GLiDE 0.8B | 82 | 42 | 9/9 | 0/8 | 1201–1209 | #1210 Mercury |
| GLiDE 0.4B | 83 | 43 | 9/9 | 0/8 | 1211–1219 | #1220 Mercury |
| Decider Flash v1.2 | 33 | 1 | original member, 18/18 | — | League 1 | — |
| MiniCPM5-2B (off) (proxy, not on Ümit's list) | 79 | 39 | 9/9 | 0/8 | 1171, 1173–1180 | #1172 Mercury |
| LFM3-1.7B (on), MiniCPM5-2B (on), Liquid d1-2B, Strands Decider 2B, Metask-Jev-4B | — | — | none | none | — | — |

All ten small decision entrants and both chat entrants are held off the site (`tools/site/content/held_setups.json`) until complete. "Publish live whichever way": the existing `running` list in the same file (Ümit via Zeki #5001) shows a held entry as an unranked 'Running · n of N' row while it plays; moving a name from `held` to `running` at its start is a one-line content change.

### 1.2 Entries still to prepare: done, on branches (nothing started)
- **LFM3-1.7B (on) and (off)** — branch `late-smallchat-on` a083fb4 (Main's priority, 13 Nov: logic serves LFM3-1.7B on bariton GPU 1 from ≈21:00Z). Pinned to logic's `lfm3-1.7b-vllm-rerun` (work/lfm3_rerun.sh): vLLM 0.34.0rc1.dev302+gbe47189f3, image `vllm/vllm-openai@sha256:7f0618da…`, LiquidAI/LFM3-1.7B@0dc4268 BF16 safetensors, served `lfm3-1.7b`, port 18634, `--max-model-len 69632`, 32 sequences, `--generation-config auto` (so vLLM's server defaults top_k 50 and repetition penalty 1.1 apply beside our temperature 1.0), `--reasoning-parser qwen3`; (off) = `enable_thinking: false` on the same server; the twin key `lfm3-1.7b-vllm` (:18605, otherwise identical) is accepted via `SMALLCHAT_URL`; pins.sh also checks the image digest. **Second blocker found and fixed:** vLLM hands LFM3's template its content as a list of parts (vLLM's own detection code run on the pinned template), which turned the (on) read-out into `<think></think><think>R</think>Answer:` silently (no error); new optional runner key `reasoning_field` (lfm3-1.7b-on only) carries the reasoning in the message's reasoning field so the template renders `<think>R</think>Answer:`. Without the key every request is byte-identical (unit test; lfm3-1.7b-off identical from old and new runner). Longest League 1 prompt as vLLM renders it: 4,375 (on) / 4,376 (off) + 32,768 output = 37,143 ≤ 69,632: no request can reach the limit. Options: groups of ≤ 26 (as every smallchat setup). `cargo test` 75 passed; stub `test.sh` (transformers 5.22.2 as in the image, messages given as vLLM gives them): old runner passes lfm3-1.7b-off and refuses lfm3-1.7b-on/minicpm5-2b-on (kept as regressions), new runner passes all three. Real `test.sh` only once the server is up. Site: hold + params (1.73B) in main; the params note 'played from the BF16 GGUF on llama.cpp' is corrected on branch `smallchat-lfm3-vllm-site` d8ca1da (scratch build with checks exit 0). **Open for Main:** the server is logic's rerun's until it finishes; League 1's rule (and test.sh) expect it to be ours alone.
- **MiniCPM5-2B (on)** — **blocker found and fixed on a branch**: the (on) read-out sends `<think>R</think>Answer:` with continue_final_message; MiniCPM5's template re-renders it as `<think>\nR\n</think>\n\nAnswer:`, so vLLM 0.30.0 answers 400 on every decision (shown statically from the template and the vLLM image's transformers code, reproduced by a template-exact stub; nothing run). Fix: branch `late-smallchat-on` 7170908 adds an optional player key `reasoning_prefill`, set only for minicpm5-2b-on to `<think>\n{reasoning}\n</think>\n\nAnswer:`; without the key the request is byte-identical (checked for lfm3-1.7b-on/off and against 200 stored Gemma 4 E4B (on) read-outs). `cargo test` 74 passed; stub `test.sh` passes for minicpm5-2b-on with the new runner and still reproduces the 400 with the old one. Scripts refuse a setup with `reasoning_prefill` unless `SMALLCHAT_BIN` names the new runner. Prompt: 4,336 + 32,768 = 37,104 ≤ 69,632. vLLM @42433e90, port 18614. Site hold + params (2.52B) already in main. **Needs review** (runner change).
- **Liquid d1-2B, Strands Decider 2B, Metask-Jev-4B** — branch `late-tiny8-small3` 8ebad40 (base late-tiny8 a72223d) + site branch `small3-site` e118111. All three run on **one bariton card** (no snapshot/env on spark2):

| | Liquid d1-2B | Strands Decider 2B | Metask-Jev-4B |
|---|---|---|---|
| repo @ rev | LiquidAI/d1-2B @ 10e7671d (HF main 652f920 changes README only) | StrandsAgents/strands-decider-2B-hobson-v21 @ 2b52a623 on Qwen/Qwen3.5-2B-Base @ b1485b2f | wayfind/metask-jev-4b-policy-mix @ ea20fe85 |
| licence | LFM Open License v1.0 | Apache-2.0 | Apache-2.0 |
| params (#3508 rule) | 1.92B | 2.29B (base + LoRA + head) | 4.54B |
| server | logic's d1_server.py (env ~/code/d1-2b/.venv), 127.0.0.1:19260 | the package's `strands-decider serve --strict-window`, :19270 (logic's servers.sh omits the flag and **cuts the state**; not used) | logic's ~/code/metask-jev/server.py, :19250 |
| limit / behaviour | 128,000 context; 400, never cuts | 4,096-token window; 422 | 4,096 tokens or > 26 options; 400 |
| options per request | 255 (league rule) | 13 | 11 |
| League 1 stored requests (31,798), own tokenizer | longest 20,759; 0 over | as stored 6,496 over 4,096; at 13 per request worst group 4,025 → 0 over | as stored 8,799 over; at 11 per request worst group 4,008 → 0 over |
| requests per decision | 1 | 1.87 | 2.09 |

  Runner providers `d1-local`, `strands`, `metask`; `pins.sh` checks the local process table (exact command, env, file and weight hashes); `start.sh`/`locals.sh` take `TINY_BIN` (default unchanged); `dry_run.sh` (stub server, scratch DB, one round v Random): d1 138 decisions, Strands 68, Metask 60, 0 invalid, 0 refused. `cargo test` 83 passed. Site: holds, params, Strands/Metask families + icons; CPU content checks and `selftest_suite_bar` pass.
- **KnowLine 4B, StartLux 2B** — already prepared and first-staged on late-knowline4b 3427947 / late-startlux2b 2a27d5d; their `locals.sh` are in ~/code/jevgammon-knowline4b and ~/code/jevgammon-startlux2b.

### 1.3 Scoring against the Random of the field's league
**Now:** the All benches feed (tools/site/bench_scores.py) scores every row as 100 × (1 − PR / Random's PR "in that league"); for a late entry that is League 1's played Random, 121.11 (1,337 decisions on League 1's positions), while the entrant's PR is on its own late-entry positions. So the comparison exists but is on different positions. The site's league pages also have a computed Random (B6.4, `analysis.references`: every legal play equally likely) for leagues where Random did not play; late entries have none.

**Proposal (smallest change):** score a late entry against Random **computed on its own scored positions** (the same B6.4 computed Random, main margin) — same positions as its PR, nothing new to play, no change for league rows. Branch `late-random-same-positions` c7ddcf9 (base main 6fa83cb, not merged): `build.late_entry_summaries` stores `random_same_positions` {error_rate, positions}; `bench_scores.random_of()` uses it in build() and problems(); notes and the zero text say so. Test: `tools/site/selftest_late_random.py` (synthetic check + offline preview through the site's own `decision()`/`references()`); a full scratch build (state symlinked, `--no-image`) passes every site check: the 11 shown late entries move, the 30 league rows are identical.

Offline numbers (site code, snapshot 15:20Z; not published):

| Late entry | decisions | PR | score now (League 1 Random 121.11) | Random on its own positions | proposed score [95% game bootstrap] |
|---|---:|---:|---:|---:|---|
| KnowLine 31B Gen1.5 (shown) | 1,928 | 26.22 | 78.35 | 118.85 | 77.94 [75.1, 80.7] |
| REAX 1.3 (shown) | 1,998 | 27.77 | 77.07 | 119.57 | 76.77 [74.2, 79.3] |
| Gemini Decision 1 (shown) | 1,704 | 27.97 | 76.91 | 120.00 | 76.69 [73.7, 79.4] |
| GLiClass v4 Edge (held, first stage) | 725 | 138.41 | −14.29 | 136.45 | −1.44 [−6.4, 3.9] |
| GLiDE 0.8B (held, first stage) | 983 | 85.41 | 29.47 | 134.45 | 36.47 [29.9, 42.8] |
| GLiDE 2B (held) | 818 | 66.69 | 44.93 | 110.41 | 39.60 [33.2, 45.6] |
| StartLux v1.1 2B (held) | 846 | 49.22 | 59.35 | 110.58 | 55.49 [50.1, 60.5] |

Other shown entries in the scratch feed: GPT-6 Astra 92.50 → 93.01, Muse Ember 83.40 → 84.01, Mammoth-1 76.43 → 77.41, Drex Max 74.90 → 74.98, Drex Max v1.1 74.45 → 74.47, Drex 2.0 68.26 → 68.03, SubQ Snap 1.1 66.81 → 66.63, Elephant-1 63.20 → 64.63. For the big models the change is < 1.5 points; for the small first-stage entries it is up to 13 points (their positions, mostly v programs and API setups, are easier or harder for Random than League 1's). Game-level check, each entrant's own match v Random in its field: GLiClass lost 1–5 (#1144), OneJev lost 4–5 (#1044), every other small entrant won.

**Decision for Ümit/Main:** merge `late-random-same-positions` (changes 11 published late-entry scores, listed above) or keep League 1's played Random.

## 2. Invalid answers (site rule: `turns.decided_by = 'fallback'`; finished valid matches)
0 for every played setup: KnowLine 4B 0/1,146; StartLux 2B 0/846; KnowLine-0.8B 0/868; StartLux 0.8B 0/880; OneJev 0/977; GLiClass 0/725; KnowLine-2B 0/1,004; GLiDE 2B 0/818; GLiDE 0.8B 0/983; GLiDE 0.4B 0/765; Decider Flash v1.2 0/2,309 (League 1); MiniCPM5-2B (off) 0/976; Gemma 4 E4B (on) 0/924 (the one thinking-on small chat reference). No exchange of theirs stored an error; exchanges with attempt > 1 are option-group splits, not retries. New entries: the share is reported from each first stage's matches before anything is published (rule from #6225). Part 2: `crp2.py score` prints the invalid share per model (its stub test shows 62 of 438 = 14% for a stub that answers prose every 7th question).

## 3. Clear risk Part 2 (Q1, Q2; with numbers and board only)
Source: runner `jevgammon quiz` (commit a52da92, branch `quiz-command`; main's uncommitted `src/quiz.rs` is identical, untouched), config `smoke/clearrisk-config.json`, items `workspace/clearrisk-scratch/items_chat.jsonl` (sha256 672cf015…, 816 lines) / `items_decision.jsonl` (c752c58c…, 1,782), scoring `p2rep.py` (frozen), answers `smoke/clearrisk-q.db`. Q1: 189 positions × (with numbers, board only); Q2: 60, **board only** (no 'with numbers' version exists). Decision form: options are the plays (Q1: 2; Q2: 4 features); with numbers = each option's computed consequences in its description; so every decision model can answer (2–4 options, longest prompt 2,361–2,669 tokens with real tokenizers). Chat form: JSON answer (`response_format` json_schema), as Kimi and GLM were asked.

Branch `small-clearrisk-p2` f6b623b (main + quiz-command + the decision clients of late-tiny8 a72223d and late-tiny8-small3 8ebad40 and late-smallchat-on a083fb4's two runner keys, src only; `tools/v3/clearrisk-small/`: pinned `items_q1q2.jsonl` (438 lines, sha256 1344aa4a…), `crp2.py` plan/score, `run.sh`, stubs, tests; chat keys pinned to the a083fb4 player.json files). Tests: 5 passed; Rust 88 passed; **2,190 requests byte-identical** to the stored ones (Celeris, Jev 1.14.0, d1-ultra, Kimi, GLM × 438); `crp2.py score` reproduces `p2rep.json`'s Q1/Q2 numbers for all 8 current models; dry run of all 16 models × 438 against stubs, one request per question, no errors; Decider Flash's settings checked byte-exact against v3.db players 33. A Part 2 chat request has no assistant turn, so the read-out keys never apply; all 438 questions rendered through LFM3's pinned template (plain and list-of-parts) end in one open `<think>` (longest 2,527 + 32,768 = 35,295 ≤ 69,632).

Requests: 438 per model (189 × 2 + 60), one per question; 16 models → 7,008 (`crp2.py plan` lists them).

| Model | runnable | est. GPU minutes [INFERENCE] | server |
|---|---|---:|---|
| LFM3-1.7B (on) | yes | 10–140 | bariton GPU 1 (logic's vLLM nightly), :18634 |
| MiniCPM5-2B (on) | yes (JSON answer, no read-out prefill: the §1.2 blocker does not apply) | 10–140 | bariton card, :18614 |
| GLiDE 2B / 0.8B / 0.4B | yes | 1.9 / 1.2 / 0.6 | spark2 :19330 / :19340 / :19350 |
| KnowLine 4B / 2B / 0.8B | yes | 3.0 / 1.6 / 1.0 | spark2 :19400 / :19490 / :19450 |
| StartLux 2B / 0.8B | yes | 1.2 / 0.7 | spark2 :19440 / :19460 |
| OneJev1.6-0.8B | yes | 0.5 | spark2 :19420 |
| GLiClass v4 Edge | yes | 5.5 | spark2 :19480 |
| Liquid d1-2B / Strands Decider 2B / Metask-Jev-4B | yes (≤ 4 options; longest Q1/Q2 prompt 2,595 tokens with their own tokenizers, under Strands'/Metask's 4,096) | 1.9 each (438 × GLiDE 2B's 261 ms; no league record) | bariton card, :19260 / :19270 / :19250 |
| Decider Flash v1.2 | yes (settings = v3.db players 33, provider pplx-local) | 3.3 (438 × 446 ms, its own median, n = 896) | bariton card, `tools/v3/servers/decider-v1.2.sh flash start` (:18098) |

Basis: decision = 438 × the model's v3.db median request time on ≤ 4-option decisions (the same statistic matches Celeris/Jev/d1-ultra's actual Part 2 times); chat = 438/16 × Gemma 4 E4B (on) 22.6 s (low) to LFM2.5-24B-A2B (on) 303 s (high). Server start/handover not included. Chat risk [INFERENCE]: with `--reasoning-parser qwen3`, vLLM's structured output should constrain only the text after `</think>` (not verified on these builds); a reply cut at 32,768 inside the reasoning has no JSON and counts invalid under the frozen scoring. So each chat run starts with `run.sh KEY --smoke` and a check that `quiz_exchanges.response` holds the reasoning plus a `{"choice": …}` answer.

Publishing: `clear_risk_publish.py` expects Q3 and 816/1,782 requests; the small models need their own list (Q3 'not asked', 438 expected, the invalid-share table, 'Preliminary / partial'). That site change is not made yet.

## 4. Learning from experience
Runner: the Gemma 4 31B pilot's own `workspace/learning-pilot/pilot.py` (sha256 454092f7…, identical to main's copy). Plan recorded: four arms (no memory; full records of every earlier game with GNUbg 2-ply, oldest dropped past the limit; own lessons after each game; budget = newest whole records fitting the lessons arm's size); 10 series × 10 games per arm v GNUbg Beginner; tests = 200 positions at T0 (shared) and after games 5 and 10 for the three memory arms (12,200 answers). Gemma measured: no memory 3.21 h, records 10.89 h, lessons 12.26 h, budget 7.49 h; whole run 13.5 h. Branch `small-learning-pilot` 0c3d01b (base learning-pilot e18ff59): `PILOT_CONFIG` per model (own DB/runs/out, served name, tokenizer, context, output allowance), chat configs lfm3-1.7b-on (a083fb4 player.json) and minicpm5-2b-on (7170908 player.json), decision mode (`"arms": ["control","records"]`) with 11 decision configs and `configs/decision_skipped.json`, `run_small.sh KEY FIRST-LAST`, `context_fit.py`. Runner branch `small-learning-runner` b01eca2 = late-tiny8-small3 8ebad40 (all small decision clients) + improve-decision-small 0333578 (records block at the start of `state`) + `reasoning_prefill` + `reasoning_field` + a new gate `context_gate: server_invalid` (a refusal counts as an invalid answer and the series continues; before, a refusal stopped the series); `cargo test` 112 passed; pinned binary `~/.cache/jevgammon-wt/target-small-learning-runner/jevgammon-b01eca2`. Tests: 13 of 13 pass, incl. all four arms end to end for both chat models against a stub that enforces vLLM's continue-final-message rule, and decision end-to-end runs (GLiDE 2B, d1-2B, GLiClass); Gemma's constants unchanged.

### 4.1 Chat
| | LFM3-1.7B (on) | MiniCPM5-2B (on) |
|---|---|---|
| tokenizer | LiquidAI/LFM3-1.7B@0dc4268b | openbmb/MiniCPM5-2B@42433e90 |
| served context | 69,632 | 69,632 |
| longest stored pilot request + 32,768 reasoning | 28,477 + 32,768 = 61,245: fits | 28,371 + 32,768 = 61,139: fits |
| largest records context (Gemma's 26,830) | 24,302 | 24,206 |
| arms | all four runnable (stub) | all four runnable (stub), with the §1.2 runner fix |

**Decision needed:** the plan's lesson call is 'reasoning off, 400 tokens'; the configs run it with thinking on and 32,768 tokens to match the (on) setting (5 lessons / 150 words cut unchanged). Approve one or the other.

**GPU time is the real cost here [INFERENCE]:** the pilot keeps one request in flight per arm, so the run is bound by its serial chain (lessons arm + last budget series ≈ 9,700 requests by Gemma's counts). At an assumed 150 tok/s per sequence: ~50 h per model if it reasons like Gemma 4 E4B (on) (2,765 tokens/decision), ~144–148 h at its own Logic & Math mean (8,027 / 8,216 tokens), ~387 h at LFM2.5-24B-A2B (on)'s 21,557. Each is one bariton card. The smoke (series 1–3) gives the real figure before the rest is started; allowing more requests in flight per arm would cut it but changes the protocol.

### 4.2 Decision models: does one full game record fit?
Delivery as on improve-decision-small: the record goes at the start of `state` + a blank line. Measured: the 100 single-game records of Gemma's records arm (largest 10,998 chars, median 6,007) + each model's own largest/median League 1 request, own tokenizer (GLiDE 2B/0.8B through their own renderer; cross-checks within 1–2% of the player notes' renderer counts).

| Model | tokenizer | largest request + largest record | median + median | limit | verdict |
|---|---|---:|---:|---:|---|
| Liquid d1-2B | LiquidAI/d1-2B@10e7671d | 29,766 | 6,032 | 128,000 | fit |
| GLiDE 2B | fastino/GLiDE-2B@00f122c1 | 34,603 | 6,556 | 39,992 | fit |
| GLiDE 0.8B | fastino/GLiDE-0.8B@9eacdeec | 31,650 | 6,744 | 39,992 | fit |
| GLiDE 0.4B | fastino/GLiDE-0.4B@6bda7ab9 | 12,136 | 5,696 | 7,999 | **skip**: 88 of 840 requests over with the median record, 348 with the largest |
| KnowLine 4B Gen5.5 | PelaAI/KnowLine-4B-Gen5.5@779944d2 | 32,706 | 6,594 | 262,138 | fit; caveat: read-twice applies only ≤ 3,000 tokens, so every decision with a record is read once (a readout change, like REAX's open question) |
| KnowLine-2B-Gen1 | PelaAI/KnowLine-2B-Gen1@53245d47 | 29,262 | 6,620 | 262,138 | fit; same caveat |
| KnowLine-0.8B-Gen1 | PelaAI/KnowLine-0.8B-Gen1@6b27831f | 27,916 | 6,514 | 262,138 | fit; same caveat |
| StartLux v1.1 2B | startlux-models/…-2B-Instant@f1e6cd14 | 29,886 | 6,594 | 131,072 | fit |
| StartLux v1.1 0.8B | startlux-models/…-0.8B-Instant@6496ae64 | 30,870 | 6,681 | 131,072 | fit |
| OneJev1.6-0.8B | OmniJev/OneJev1.6-0.8B@bcd88a38 | 33,772 | 6,598 | 32,768 | partial: 0 of 977 over with the median record, 1 with the largest (refused, counted invalid) |
| GLiClass v4 Edge | knowledgator/gliclass-v4-edge@885af1af | 19,882 | 5,732 | 16,384 per pass | partial: 4 of 744 over with the median record, 12 with the largest |
| Strands Decider 2B | StrandsAgents/…-hobson-v21@2b52a623 | record alone 6,139 / 3,276 | — | 4,096 | **skip**: a record does not fit its window |
| Metask-Jev-4B | metask-ai/metask-jev@ea20fe85 | record alone 6,139 / 3,276 | — | 4,096 | **skip**: same |
| Decider Flash v1.2 | its own (HF snapshot) | 11,099 | — | 262,144 | fit |

Skipped on the page with the reason (`configs/decision_skipped.json`): GLiDE 0.4B, Strands Decider 2B, Metask-Jev-4B (median record + median request 6,598 > 4,096).

Decision configs (no-memory + full records only; room for records = the model's limit − its largest League 1 request (median for OneJev and GLiClass) − 1,500, own tokenizer; oldest games dropped past it; requests per model ≈ 2,592 no memory + 6,283 full records incl. tests, by Gemma's counts):

| Config | host | room for records (tokens) | median request (ms) | GPU-h [INFERENCE] |
|---|---|---:|---:|---:|
| d1-2b | bariton :19260 | 102,172 | no league record | not estimable before its first stage |
| glide-2b | spark2 :19330 | 10,029 | 321 | ~2.1 |
| glide-0.8b | spark2 :19340 | 12,982 | 227 | ~1.8 |
| knowline-4b (read-once caveat) | spark2 :19400 | 234,072 | 285 | ~3.5 |
| knowline-2b (caveat) | spark2 :19490 | 237,516 | 152 | ~1.9 |
| knowline-0.8b (caveat) | spark2 :19450 | 238,862 | 109 | ~1.3 |
| startlux-2b | spark2 :19440 | 105,826 | 206 | ~2.5 |
| startlux-0.8b | spark2 :19460 | 104,842 | 131 | ~1.6 |
| onejev1.6-0.8b (partial) | spark2 :19420 | 27,947 | 96 | ~1.2 |
| gliclass-v4-edge (partial) | spark2 :19480 | 11,670 | 1,403 | ~10.8 |
| decider-flash-v1.2 | bariton :18098 | 255,685 | 531 | ~6.5 |

Estimate: 2,592 × median s + 6,283 × median s × f, with f the slowdown from longer input (6.6 where the room does not bind: Gemma's records arm sent 22,848 vs 4,355 input tokens per decision; 3.4–4 under GLiDE's and GLiClass's limits); one request at a time per server, so wall ≈ GPU-h; server start extra. Total ≈ 33 h (+ d1-2B), of which ≈ 27 h on spark2.

## 5. Costs and GPUs

**Cash (OpenRouter; guards keep the shared balance ≥ $40):**
| Item | Expected | Ceiling (enforced) |
|---|---:|---:|
| First stages: LFM3-1.7B (on), MiniCPM5-2B (on), d1-2B, Strands, Metask (paid opponents; measured on the earlier small entries $0.084–0.122 each) | ≈ $0.50 | 5 × $5.00 = $25.00 (start.sh/locals.sh stop at $5 paid-opponent $ per entry) |
| Local stages (8 locals, our GPUs) | $0 | — |
| Clear risk Part 2 (local models only) | $0 | — |
| Learning (chat models write their own lessons; decision arms are no-memory and full records: no writer) | $0 | — |
| **Total** | **≈ $0.50** | **$25.00 < $30** |

**GPU (rental-equivalent at $2.49/h, kept apart from cash):**
| Part | Where | Hours [INFERENCE unless measured] |
|---|---|---|
| First stages, 2 chat (on) | 1 bariton card each | ~0.4 h each (MiniCPM5 (off) 48 s wall × Gemma E4B on/off ratio 31); up to 3–5 h if every decision reasons to the cap |
| First stages, d1-2B / Strands / Metask | 1 bariton card each | busy < 0.1 h; card held 0.1–1.8 h (tiny8 measured) |
| Local stages, 15 entrants | entrant: spark2 (10) or its bariton card (5); opponents: 1 bariton card | ~0.5 h of matches (sum of the 8 locals' median match walls, v3.db) + server starts ≈ 0.7 h each → ~10.5 h of a bariton card, plus ~7 h of spark2 handoffs |
| Clear risk Part 2 | spark2 (10), bariton (chat + 4) | ~18 GPU-min on spark2 for the 10; ~9 min for d1/Strands/Metask/Decider Flash; chat 10–140 min each; handover not included |
| Learning, chat (on) ×2 | 1 bariton card each | 50–387 h each, central ~145 h (§4.1) |
| Learning, decision (no memory + full records) | spark2 (9) / bariton (d1-2B, Decider Flash) | ≈ 33 h total, ≈ 27 h of it on spark2 (§4.2); d1-2B not estimable before its first stage |

## 6. Order (smallest first, ready first) and exact start commands
Cards: all four bariton cards are in use now (83–97 GB used); my queued GPU 2 booking r_16666a6987bd starts after the compactor. spark2 is logic's: it serves one decision model at a time (Turion Jev 31B's first stage now); every spark2 step below waits for logic's handoff of that model's server.

1. **Part 2 for the 10 spark2 models** (≈ 18 GPU-min in total; each in its server's window, e.g. right after that model's local stage):
   `cd ~/.cache/jevgammon-wt/small-clearrisk-p2 && tools/v3/clearrisk-small/run.sh KEY` (KEY: glide-2b glide-0.8b glide-0.4b knowline-4b knowline-2b knowline-0.8b startlux-2b startlux-0.8b onejev1.6-0.8b gliclass-v4-edge; pins checked with late-tiny8 `models/KEY/pins.sh`), then `tools/v3/clearrisk-small/crp2.py score ~/code/jevgammon/smoke/clearrisk-small-q.db`.
2. **LFM3-1.7B (on)** on logic's server on bariton GPU 1 (from ≈21:00Z, after logic's rerun/turkce, Main's slot):
   ```
   B=$HOME/.cache/jevgammon-wt/target-late-smallchat-on/release/jevgammon   # built from late-smallchat-on a083fb4
   T=$HOME/.cache/jevgammon-wt/late-smallchat-on/tools/v3/late-smallchat
   # server: logic's lfm3-1.7b-vllm-rerun on GPU 1 (work/lfm3_rerun.sh), started by logic; we never start it
   SMALLCHAT_BIN=$B $T/test.sh lfm3-1.7b-off && SMALLCHAT_BIN=$B $T/test.sh lfm3-1.7b-on
   systemd-run --user --unit=late-smallchat-lfm3-1.7b-on --working-directory=/home/cbasaran/code/jevgammon \
     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/games -E SMALLCHAT_BIN=$B $T/start.sh lfm3-1.7b-on
   cd ~/.cache/jevgammon-wt/small-clearrisk-p2 && tools/v3/clearrisk-small/run.sh lfm3-1.7b-on --smoke && tools/v3/clearrisk-small/run.sh lfm3-1.7b-on
   SMALLCHAT_BIN=$B OPP_GPU=N RES=RES $T/locals.sh lfm3-1.7b-on
   cp /home/cbasaran/code/jevgammon/workspace/learning-pilot/test_{set.json,positions.jsonl} ~/.cache/jevgammon-wt/small-learning-pilot/workspace/learning-pilot/
   systemd-run --user --unit=learning-small-lfm3-1.7b-on --working-directory=$HOME/.cache/jevgammon-wt/small-learning-pilot \
     workspace/learning-pilot/run_small.sh lfm3-1.7b-on 1-3        # then 4-10 after the smoke's numbers
   ```
   LFM3-1.7B (off) (Main's first-stage slot ≈1 h after turkce) uses the same `start.sh lfm3-1.7b-off`; it is not on Ümit's list but shares the server.
3. **MiniCPM5-2B (on)**, on logic's GPU 1 after LFM3 (Main: logic serves MiniCPM5-2B next; served `minicpm5-2b`, vLLM v0.30.0 @42433e90, :18614, as pinned), with the fixed runner (`SMALLCHAT_BIN=$HOME/.cache/jevgammon-wt/target-late-smallchat-on/release/jevgammon`, scripts from `~/.cache/jevgammon-wt/late-smallchat-on/tools/v3/late-smallchat/`): `test.sh minicpm5-2b-on`, `start.sh minicpm5-2b-on` (with `-E SMALLCHAT_BIN=…`), Part 2 `run.sh minicpm5-2b-on --smoke` then full, `locals.sh minicpm5-2b-on`, `run_small.sh minicpm5-2b-on 1-3`. If we must serve it ourselves: `systemd-run --user --unit=smallchat-serve-minicpm5-2b -p RemainAfterExit=yes --working-directory=$HOME/code/benchmark/logic -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin agent-bus run RES -- python3 work/small_models.py serve minicpm5-2b GPU_UUID`.
4. **Liquid d1-2B, Metask-Jev-4B, Strands Decider 2B**, one bariton card, one at a time (start.sh refuses while any other `late-tiny8-*` unit runs, e.g. Turion's):
   ```
   cd ~/.cache/jevgammon-wt/late-tiny8-small3 && CARGO_TARGET_DIR=/home/cbasaran/code/jevgammon/target/small3 cargo build --release
   BIN=/home/cbasaran/code/jevgammon/target/small3/release/jevgammon
   tools/v3/late-tiny8/dry_run.sh d1-2b d1 $BIN          # metask-jev-4b metask / strands-decider-2b strands
   ~/code/benchmark/decision/servers.sh start d1-2b G   # metask: servers.sh start metask G; strands: see below
   systemd-run --user --unit=late-small3-strands -E CUDA_VISIBLE_DEVICES=G -E HF_HUB_CACHE=/home/cbasaran/code/strands-decider/hf-cache -E HF_HUB_OFFLINE=1 \
     /home/cbasaran/code/strands-decider/.venv/bin/strands-decider serve /home/cbasaran/code/strands-decider/model --host 127.0.0.1 --port 19270 \
     --device cuda --model-name strands-decider-2b --strict-window
   systemd-run --user --unit=late-tiny8-KEY --working-directory=/home/cbasaran/code/jevgammon -E TINY_BIN=$BIN \
     ~/.cache/jevgammon-wt/late-tiny8-small3/tools/v3/late-tiny8/start.sh KEY
   systemd-run --user --unit=late-tiny8-KEY-locals --working-directory=/home/cbasaran/code/jevgammon \
     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E OPP_GPU=<n> -E RES=<reservation> -E TINY_BIN=$BIN \
     ~/.cache/jevgammon-wt/late-tiny8-small3/tools/v3/late-tiny8/locals.sh KEY
   ```
   Merge `small3-site` before (holds) and the late-tiny8-small3 tool changes into late-tiny8 once Turion's entry is over.
   Part 2 for these three and Decider Flash v1.2 while each server is up: `cd ~/.cache/jevgammon-wt/small-clearrisk-p2 && tools/v3/clearrisk-small/run.sh d1-2b` (`strands-decider-2b`, `metask-jev-4b`; Decider Flash: `tools/v3/servers/decider-v1.2.sh flash start` on a card, then `run.sh decider-flash-v1.2`).
5. **Local stages of the 10 spark2 entrants** (spark2 handoff + one bariton card for opponents): `systemd-run --user --unit=late-tiny8-KEY-locals … ~/code/jevgammon-tiny8/tools/v3/late-tiny8/locals.sh KEY` (8 tiny8 keys); `~/code/jevgammon-knowline4b/tools/v3/late-knowline4b/locals.sh`; `~/code/jevgammon-startlux2b/tools/v3/late-startlux2b/locals.sh` (each with `-E OPP_GPU=<n> -E RES=<reservation>`).
6. **Learning, decision arms** (one server at a time, in its window; spark2 after logic's handoff, `pins.sh` check first): `cp /home/cbasaran/code/jevgammon/workspace/learning-pilot/test_{set.json,positions.jsonl} ~/.cache/jevgammon-wt/small-learning-pilot/workspace/learning-pilot/` once, then `systemd-run --user --unit=learning-small-KEY --working-directory=$HOME/.cache/jevgammon-wt/small-learning-pilot workspace/learning-pilot/run_small.sh KEY 1-3` and later `4-10` (KEY: glide-2b glide-0.8b knowline-4b knowline-2b knowline-0.8b startlux-2b startlux-0.8b onejev1.6-0.8b gliclass-v4-edge d1-2b decider-flash-v1.2; Decider Flash server: `DECIDER_V12_GPU=<n> tools/v3/servers/decider-v1.2.sh flash start`).
7. **Learning, chat full runs** (series 4–10): last, after the smoke gives real hours.

Before publishing anything: the invalid share per model from its own matches/answers (§2), then the site's 'Preliminary / partial' labels.

## 7. Branches (all pushed, none merged)
| Branch | Commit | Base | What |
|---|---|---|---|
| late-random-same-positions | c7ddcf9 | main 6fa83cb | Random computed on a late entry's own positions (§1.3) |
| late-smallchat-on | a083fb4 | late-smallchat 171698f | MiniCPM5-2B (on) read-out prefill; LFM3-1.7B (off/on) repinned to logic's vLLM nightly + read-out fix (§1.2) |
| smallchat-lfm3-vllm-site | d8ca1da | main | LFM3-1.7B params note: vLLM, not llama.cpp |
| late-tiny8-small3 | 8ebad40 | late-tiny8 a72223d | d1-2B, Strands, Metask entries (§1.2) |
| small3-site | e118111 | main 6fa83cb | their site holds, params, families |
| small-clearrisk-p2 | f6b623b | main + quiz-command + late-tiny8/-small3 clients + late-smallchat-on keys | Part 2 runner for the 16 models (§3) |
| small-learning-pilot | 0c3d01b | learning-pilot e18ff59 | pilot configs (2 chat, 11 decision, skip list), context fit (§4) |
| small-learning-runner | b01eca2 | late-tiny8-small3 + improve-decision-small 0333578 + late-smallchat-on keys | the pilot's runner for the small models (`server_invalid` gate) |

## 8. Blockers and decisions
- **Cards:** no bariton card is free now; spark2 steps need logic's handoffs (one server at a time).
- **MiniCPM5-2B (on), LFM3-1.7B (on):** need review of the two runner keys on late-smallchat-on (`reasoning_prefill`, `reasoning_field`) before their first stages; their Part 2 runs ask JSON answers (no read-out prefill).
- **Learning chat:** approve the lesson-call setting (thinking on 32,768 vs the plan's off/400); GPU time 50–387 h per model under the pilot's one-request-per-arm rule.
- **KnowLine full-records arm:** the record switches its readout from read-twice to read-once (a question for Ümit, like REAX's).
- **Random scoring:** merging late-random-same-positions changes 11 published scores.
- **Part 2 page:** the small models need their own publish list (no Q3); not built yet.
- **Incidents (fixed):** (1) for ~10 min a subagent's site edits (held_setups.json, families.json, model_params.json, additions only) sat in the main checkout before being moved to small3-site and reverted; the 15:35Z live build's deployed data contains none of the three names (checked). (2) A subagent briefly wrote scratch files under /tmp (one file deleted at once; test temp folders moved to ~/.cache/jevgammon-wt/small-learning-tmp).
