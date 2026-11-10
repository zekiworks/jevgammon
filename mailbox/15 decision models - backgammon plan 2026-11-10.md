# 15 decision models on backgammon: plan (2026-11-10)

For Ümit's handoff (bus #4057): 15 open decision models on backgammon (error rate; league entry) and on "Did they improve?", plus the combined score page (owner Turkce, #4062). Planning only: nothing was run, downloaded or started. Sources: `v3.db` and the site's GNUbg score shards (`~/.local/state/bg-site/plays/s*.db`), read-only; `tools/site/content/setups.json`; `tools/ladder.py`; `src/players/decision.rs`; `tools/v3/servers/`; the mailbox files named below; Hugging Face API metadata and model-card text (no weights fetched, 10 Nov). Logic's #4059 facts (7 new repos public, not gated, sizes) are used as given; Main's #4062/#4063 decisions (spark2 servers shared in turn; latency from Reading's spark2 pass; ECE definition) are followed. Unchecked statements are marked [INFERENCE].

## 1. The 15 models

"On backgammon" = a setup with valid matches in `v3.db`. Decisions = the setup's own model-decided turns. Sizes: HF safetensors totals; bf16 memory ≈ weights + KV/activations.

| # | Model (HF repo @ main sha, 10 Nov) | On backgammon? | Server route | Option limit / context | Size, bf16 | Fits 96 GB card / GB10 (121 GB usable) |
|---|---|---|---|---|---|---|
| 1 | REAX 1.3 (`decisionmodels/REAX-1.3` @ fa4bf7ee) | **Yes, same commit**: late entry `REAX 1.3`, 18 matches (Luna not played), 1,998 decisions, PR 27.8 | exists: `workspace/reax/reax.sh` (Docker, reax-engine @ ff8f595), service `reax` on branch `late-reax` | 255 options; refuses > 32,000 proxy tokens (chars/4), never truncates | two parts, 114.7 GB on disk; card: both parts FP8 on one RTX PRO 6000, peak ≈ 88.5 GiB; we ran ≈ 62 GB loaded | 96 GB: **only in FP8** (bf16 ≈ 115 GB does not fit). GB10: card requires SM120 RTX PRO 6000, x86 Docker image and FP8 kernels → [INFERENCE] not runnable on spark2 without a rebuild; keep on bariton |
| 2 | GLiDE 27B (`fastino/GLiDE-27B` @ 4d32743a) | **No, different checkpoint.** `Fastino GLiDE v1.2 (local)` is `fastino/GLiDE` @ a7e45896; the repo was renamed (`fastino/GLiDE` → 307 to `GLiDE-27B`) and 4d32743a is "GLiDE 27B: new main (previous version kept at tag glide-v1.2)", 5 Nov. Hosted `Fastino GLiDE` (glide_v2) is a third thing | `glide/server.py` in the repo (same package as `glide-v12.sh`, new snapshot); runner: existing `fastino` service with `base_url` | 255; 40,000 tokens per question by default (then 422) | 26.1 B, 52.2 GB; 56.4 GB peak (card) | yes / yes |
| 3 | KnowLine 31B Gen1.5 (`PelaAI/KnowLine-31B-Gen1.5` @ 8e56aa1b) | No | `serve_knowline.sh` = SGLang bf16 + `knowline_server.py` `/v1/systemone` (new script) | 255 options, 64 questions; reads requests ≤ 3,000 tokens twice; question header up to 32,768 tokens; card: over the limit "reported as" unsupported | 31.3 B, 62.5 GB; SGLang reserves 0.85 of the card (≈ 82 GB) | yes (card tested 96 GB H20 only) / yes, one 31B at a time |
| 4 | Sieve 31B v3 (`sthanika-ai/Sieve-31B-v3` @ 8fcee858) | No | `sieve-serve` from `github.com/sthanika-ai/Sieve` (pip package, not in the HF repo); its HTTP API shape not read [INFERENCE: System One, to check] | 255 (more refused); "no token limit declared", never truncates, OOM fails | 31.3 B, 62.5 GB; peak 81.4 GiB on their longest request | yes / yes |
| 5 | Turion Jev 31B (`turion-ai/turion-jev-31b` @ 866c0fc6) | No | `python -m turion_jev.serve` (TypeSafe-compatible `/v1/systemone`, vLLM in-process) | 255; prompts > 65,536 tokens refused | 31.3 B, 62.5 GB bf16; card's reported run **FP8** (online); bf16 untested by maker | yes / yes |
| 6 | vLLM-SR d3-ultra (`vllm-sr/d3-ultra` @ ccdcfa61) | No (addendum: "no backgammon route yet") | `d3_server.py` in the repo; our `d3-turbo.sh` + service `d3` (200 options sent) adapt with a new snapshot | 131,072 tokens per question; 255 codes [INFERENCE from d3-turbo] | 26.1 B, 52.2 GB | yes / yes |
| 7 | GLiDE 9B (`fastino/GLiDE-9B` @ ab54df5a) | No | `glide/server.py` | 255; context not read [INFERENCE: as 27B] | 7.9 B, 15.9 GB | yes / yes |
| 8 | Base Labs Elephant-1 (`baselabs/elephant-1` @ b3f8a934) | **Yes, same commit**: late entry, 19 matches, 2,044 decisions, PR 44.6 | exists: `baselabs_server.py` (image `baselabs-serve:81ce62f`), branch-only runner service | 120 options per request (our setting); engine refuses > 32,768, trained 16,384 | 9.4 B, 18.8 GB | yes / yes |
| 9 | Cerno 9B v1.2 (`apertixai/cerno-9b-v1.2` @ f02a632f) | No | **no HTTP server shipped**: Python `CernoEngine` (transformers, bf16) → needs our wrapper server, as `baselabs_server.py` | 255; read twice ≤ 3,000 tokens; trained 16k; vLLM engine `max_model_len` default 20,480, longer rows "unsupported", not truncated | 9.0 B, 17.9 GB | yes / yes |
| 10 | KnowLine 4B Gen5.5 (`PelaAI/KnowLine-4B-Gen5.5` @ 779944d2) | No | as #3 (SGLang **FP8 at load** in the card's setting) | 255 / 64 questions; read twice ≤ 3,000 | 4.7 B, 9.3 GB | yes / yes |
| 11 | StartLux-Decision v1.1 4B (`startlux-models/StartLux-Decision-v1.1-4B-Instant` @ 416088f7; cc-by-nc-4.0) | No | `startlux-decide serve --launch-vllm` (`/v1/systemone`) | 26 options per pass; server groups wider choices itself (`wide_choice` group 25, keep 3); prompts > 65,536 need vLLM 0.31 | 4.7 B, 9.3 GB | yes / yes |
| 12 | Perplexity Decider Flash v1.2 (`perplexity-ai/pplx-decider-flash-v1.2`, main 9ff7cf98) | **Yes**: League 1 `Decider Flash v1.2`, 22 league matches, 2,309 decisions, PR 59.9. Our setting records the local checkpoint dir, not a commit; HF history: 6d771ad7 (weights, 16 Oct) then 9ff7cf98 (tag only) → [INFERENCE] same weights | exists: `decider-v1.2.sh flash`, service `pplx-local` (25 options) | 25 (our cap); 262,144 | 4.5 B, 9.1 GB | yes / yes |
| 13 | GLiDE 0.8B (`fastino/GLiDE-0.8B` @ 9eacdeec) | No | `glide/server.py` | 255 | 0.75 B, 1.5 GB | yes / yes |
| 14 | GLiDE 0.4B (`fastino/GLiDE-0.4B` @ 6bda7ab9) | No | `glide/server.py` (encoder backbone) | 255; **`max_len` 7,999, `trunc_head` 1,024: longer prompts are shortened silently** | 0.39 B, 0.8 GB | yes / yes |
| 15 | OneJev1.6-0.8B (`OmniJev/OneJev1.6-0.8B` @ c89933c2) | No | `flide serve` (github.com/OmniJev/Flide, System One + `media`); not read | not documented on the card [unchecked] | 0.85 B, 1.7 GB | yes / yes |
| ref | Jev 1.14 hosted | **Yes**: League 1 `Jev 1.14.0`, 36 matches, 3,812 decisions, PR 34.5 (TypeSafe API, key in use) | `jev` service | 255; 32k | closed | — |

**Request size against the limits.** League requests (one per decision unless the list is split): median ≈ 3,300 tokens, max 45,247 (GLiDE v1.2 tokenizer, 3,493 decisions); 61 kB the largest stored body; up to 600 legal plays in a position (89 model turns above 255). Share of GLiDE v1.2's league requests above: 7,999 tokens **3.3 %**, 16,384 0.5 %, 20,480 0.3 %, 32,000 0.06 %, 40,000 0.03 % (Decider Flash's 25-option requests are larger per option: 11.9 % above 7,999).

Consequences:
- **GLiDE 0.4B**: about 3 % of league requests exceed 7,999 tokens and would be cut, not refused [INFERENCE: its encoder tokenizer differs, so the exact share needs its own count]. **Our context guard (addendum §6.1/6.2) would refuse this route** — a silent cut fails the local render check, as Clef did. For the league it needs a decision: run with a smaller option cap so each request stays under 7,999 (the runner's existing group split; e.g. cap ≈ 60 options), or "not tested: context too short".
- **Cerno 9B**: 0.3 % over its default 20,480 → refused rows; the runner treats a refusal as an error, so the cap (group split) must keep requests below it, or raise `max_model_len` (card: "trained 16k").
- **StartLux 4B**: 26 options per pass; set our cap to 25 (as `pplx-local`) so our split, not the server's internal grouping, decides; or accept its server grouping (D-item).
- KnowLine, Cerno, REAX read short requests (≤ 3,000 tokens) twice: a league-normal layout; relevant only for "Did they improve?" (§4).
- All others (255 options, ≥ 40,000 tokens) take league requests as they are, with the runner's existing split above 255.

**Runner adapters** (`src/players/decision.rs` has one static `Service` per provider: `max_choices`, path, model field). Every new server speaks `POST /v1/systemone` with `model`/`state`/`questions` [INFERENCE for Sieve and OneJev, cards not fully read]. Needed: a `Service` entry (or reuse with `base_url`) per route with its option cap: GLiDE ×4 → reuse `fastino` with `base_url` (as `glide-v1.2`); d3-ultra → `d3` with 255/200; KnowLine ×2, Turion, Sieve, StartLux, OneJev → new entries (no key); Cerno → our wrapper server + entry. The `reax`/`baselabs` services exist on branches `late-reax`/`late-drex`, not on main [INFERENCE from main's `SERVICES` list]. Each: unit test of the body, 20-request smoke on stored League 1 requests (as REAX).

## 2. League entry

**What the rules are.** The inter-league ladder (`tools/ladder.py`, `mailbox/backgammon-ladder-cup.md`): each round, at every boundary, the lower league's winner swaps with the upper league's last; programs never move; one stored result per pair. It **ended** at round 6 (Can, 26 Oct: "final swap (ladder ended)"; `mailbox/Ladder ended - final placement.md`), with the rule "new setups added later start the next season, and the ladder continues from there". Since then every new setup (SubQ Snap 1.1, Elephant-1, Mammoth-1, the four Drex, REAX 1.3; GPT-6 Astra (high) in League 3) entered by the **late-entry protocol**: a hidden late-entry league that plays the 19 setups of the original League 1 table once (3 rounds, 2 games each), stage `late-entry` (trigger `late_entry_stage`), out of every standings table, Cup and other setup's numbers, never moved league, shown on the Late entries tab ranked by nothing ("late entries are never ranked"; the main metric is risk judgement). Measured: 18–19 matches, 1,993–2,148 own decisions per entry.

**Two ways:**
- **A. Late-entry protocol (proposed).** Same field (19, of which GPT-6 Luna is still out of credit → 18), same match count, same prompt/seed rules as the seven precedents. Nothing in the leagues moves; the new rows are comparable with the existing late entries. Least disruptive and fair against the same opponents.
- **B. "Next season" under the ladder.** New setups would join a league and the ladder would resume: swaps change the published tables, every mover plays all new pairs of its new league, and 12 entrants (which league? the rules do not say where a newcomer starts) would require new League 1 rounds of ~19+ pairs each plus swap rounds. Many more matches, all leagues' tables change, and decision models would occupy the bottom league [INFERENCE: on error rate, none of them would be promoted past League 2's chat models]. Needs Can/Ümit to define the entry league.

Recommendation: A for the 12 new entrants; the 3 already on backgammon keep their rows (REAX, Elephant-1 late; Decider Flash League 1). If Ümit's "usual inter-league swap rules" means B, that is Decision D1 (§6).

**Size and cost per entrant (A).** ≈ 19 matches, ≈ 2,000 own decisions; 8 local opponents (Cygnet, Winnow, Decider Flash v1.2, Decider v1.2 27B, GLiDE v1.2 local, Clef, Open-Jev, Decider v1.1 27B) need their servers up: REAX's run played them one at a time on one bariton card in 37 min (+ startup), 7 paid opponents billed $0.128 (cap $1), 3 programs free.

Own model time from comparable late entries on RTX PRO 6000 (mean request time): 27–31B dense ≈ 0.9–1.0 s (Mammoth-1 0.87 s, Drex Max v1 0.95 s) → ≈ 0.5 h for 2,000 decisions; GLiDE v1.2 27B 1.8–2.7 s → ≈ 1–1.5 h; 9B ≈ 0.36 s (Elephant) → 0.2 h; REAX 1.9 s. On **GB10** the same 27B decision models ran **≈ 3.9× slower** (Decider v1.1 27B 0.92 s on bariton → 3.58 s mean from 16 Oct on DGX Spark; Clef 1.16 → 3.29 s; Cygnet 0.33 → 1.27 s, mixed periods).

| Entrant group | spark2 (GB10) model time per entrant [INFERENCE: ×3.9] | wall per entrant on spark2 incl. opponents | bariton card instead |
|---|---|---|---|
| 31B dense ×3 (KnowLine, Sieve, Turion) | ≈ 2 h | ≈ 3–4 h | ≈ 1–1.5 h |
| GLiDE 27B, d3-ultra | ≈ 4–6 h (GLiDE v1.2 1.8–2.7 s × 3.9) | ≈ 5–7 h | ≈ 1.5–2 h |
| 9B ×2, 4B ×2, 0.8B ×2, 0.4B | ≈ 0.3–1 h each | all 7 fit together (≈ 57 GB) → one session ≈ 4–6 h | ≈ 2–3 h total |

Plus local opponents on a bariton card: ≈ 0.75 GPU-h per entrant, ≈ 9 h for 12 (≈ 4 h if the small entrants share one opponent cycle). Paid opponents ≈ $0.13 per entrant, **≈ $1.6** for 12 (Luna excluded).

**spark2 total for league entries ≈ 25–35 h** [INFERENCE], against **minutes per model** for Logic & Math / Reading on the same servers. That is the scheduling problem: one backgammon 31B entry holds the shared server for an afternoon. Option: run backgammon entries on a bariton card (≈ 4× faster) and use spark2 only for the shared latency pass; or run backgammon on spark2 during the night slots when L&M/Reading do not need the model in memory.

**Cross-machine:** entrant on spark2, local opponents on bariton; the runner takes `base_url` per player, so this works if bariton can reach spark2's port [INFERENCE: not checked].

## 3. Backgammon 0–100 score (Ümit's definition)

score = 100 × (1 − PR / PR_Random), PR = 500 × mean GNUbg 1.08 2-ply equity loss over decisions with ≥ 2 legal plays, invalid answers left out (`league_web.error_rates`).

**Random's error rate: 119.4** (1,580 scored decisions, all its valid non-late-entry matches, 22 matches; `league_web.error_rates` method over the 32 shards, 10 Nov). The League 1 page shows 118.5 (League 1 matches only); in late-entry matches Random scored 104.7 (538 decisions). Proposal: fix 119.4 (all its counted matches) as `zero`, recorded with its date and decision count, refreshed by the generator.

Current rows (league = all valid non-late-entry matches; late = own decisions in late-entry matches; all decisions scored, 0 pending):

| Setup | Where | Decisions | PR | Score |
|---|---|---:|---:|---:|
| GPT-6.1 Sol (high) | league | 3,362 | 10.6 | 91.1 |
| GPT-6 Astra (on) | league | 1,848 | 11.1 | 90.7 |
| GPT-6 Astra (off) | league | 1,694 | 11.3 | 90.6 |
| GPT-6.1 Sol (low) | league | 3,174 | 11.4 | 90.5 |
| Gemini 4 Argon (on) | league | 1,699 | 11.7 | 90.2 |
| Claude Fable 5.1 (on) | league | 1,760 | 13.9 | 88.4 |
| Claude Opus 5.5 (on) | league | 1,909 | 13.9 | 88.4 |
| Gemini 3.8 Flash (high) | league | 3,118 | 14.4 | 87.9 |
| Claude Sonnet 5.5 (high) | league | 3,065 | 15.4 | 87.1 |
| Claude Opus 5.5 (off) | league | 1,760 | 15.6 | 87.0 |
| Gemini 4 Argon (off) | league | 3,698 | 15.9 | 86.7 |
| DeepSeek V4.1 Flash 1017 (on) | league | 3,163 | 17.1 | 85.6 |
| Gemini 3.8 Flash (low) | league | 3,620 | 17.4 | 85.4 |
| Grok 4.7 (on) | league | 1,763 | 17.7 | 85.1 |
| Claude Fable 5.1 (off) | league | 3,842 | 17.9 | 85.0 |
| DeepSeek V4.1 Flash (on) | league | 3,114 | 18.4 | 84.6 |
| Gemma 4 31B (on) | league | 3,190 | 19.0 | 84.1 |
| Grok 4.7 (off) | league | 3,559 | 19.1 | 84.0 |
| Claude Sonnet 5.5 (low) | league | 2,972 | 19.8 | 83.4 |
| Gemma 4 31B (off) | league | 2,665 | 22.4 | 81.2 |
| GNUbg weak (program) | league | 5,359 | 25.5 | 78.7 |
| Kimi K3.1 Pro (off) | league | 1,462 | 26.8 | 77.5 |
| REAX 1.3 | late | 1,998 | 27.8 | 76.7 |
| Base Labs Mammoth-1 | late | 2,021 | 28.5 | 76.1 |
| Qwen3.8-27B (on) | league | 2,923 | 29.1 | 75.7 |
| Liquid d1-ultra | league | 4,287 | 30.1 | 74.8 |
| GLM-5.3 (on) | league | 2,756 | 30.3 | 74.6 |
| Drex Max v1 | late | 2,148 | 30.4 | 74.5 |
| Drex Max 1.1 | late | 2,154 | 30.9 | 74.1 |
| Celeris-1 Decision | league | 4,044 | 33.1 | 72.3 |
| DeepSeek V4.1 Flash (off) | league | 4,186 | 33.7 | 71.8 |
| Qwen3.8 Flash (off) | league | 2,916 | 33.8 | 71.7 |
| DeepSeek V4.1 Flash 1017 (off) | league | 2,958 | 34.1 | 71.4 |
| Jev 1.13.0 | league | 2,268 | 34.4 | 71.2 |
| Jev 1.14.0 | league | 3,812 | 34.5 | 71.1 |
| Fastino GLiDE (hosted) | league | 4,316 | 34.5 | 71.1 |
| Fastino GLiDE v1.2 (local) | league | 2,452 | 35.5 | 70.3 |
| Decider v1.2 27B | league | 2,412 | 36.5 | 69.4 |
| Clef | league | 3,970 | 37.0 | 69.0 |
| Cygnet (Gemma 4 12B) | league | 2,511 | 38.0 | 68.2 |
| Decider v1.1 27B | league | 2,423 | 38.2 | 68.0 |
| Drex 2.0 (hosted) | late | 1,937 | 38.4 | 67.8 |
| SubQ Snap 1.1 | late | 2,326 | 40.2 | 66.3 |
| Qwen3.8-27B (off) | league | 4,067 | 41.5 | 65.3 |
| GPT-6 Luna | league | 2,422 | 41.7 | 65.1 |
| Drex 2.0 (local) | late | 1,993 | 42.9 | 64.0 |
| SubQ Snap Preview | league | 2,642 | 43.9 | 63.3 |
| Base Labs Elephant-1 | late | 2,044 | 44.6 | 62.7 |
| Mercury Decide | league | 2,277 | 46.5 | 61.0 |
| LFM2.5-24B-A2B (on) | league | 4,025 | 47.4 | 60.3 |
| Winnow-12B | league | 2,474 | 48.6 | 59.3 |
| Safest (program) | league | 2,517 | 51.0 | 57.3 |
| Decider Flash v1.2 | league | 2,309 | 59.9 | 49.8 |
| LFM2.5-24B-A2B (off) | league | 3,440 | 60.3 | 49.5 |
| Open-Jev 27B v1.1 | league | 2,511 | 65.0 | 45.6 |
| Random (program) | league | 1,580 | 119.4 | 0.0 |

Caveats for the page: leagues and late entries played different positions and opponents, so close scores are not a ranking (site rule); a 0–100 on PR is linear in PR, so it inherits PR's intervals (×100/119.4); our main metric stays risk judgement — this score is the one Ümit asked for on the combined page.

## 4. "Did they improve?" (Part 3, addendum 2026-11-09)

The addendum's cohort is closed (Ümit #3744/#3746/#3758; "every decision model outside this list is out of scope"), and the harness refuses to run unless the addendum has its bound sha256. Adding models therefore needs **an amendment as a new file** (e.g. "addendum 2, cohort extension", its own hash, committed before its first call), leaving running arms' hash untouched.

Volume per model (addendum §8, draft §7): per arm 50 games ≈ 1,000–1,075 decisions + 5 × T10 (1,000) + 3 empty runs (600) ≈ 2,600; both arms with separate empty runs (D1 default) ≈ 5,200 decisions; blocks add ≈ 660–1,470 tokens per request (≈ +20–45 % on a 3,300-token median). Writer (Qwen3.8 Flash on OpenRouter) ≈ $0.03 per model (Arm N); GNUbg is CPU.

| Model | In cohort now? | Can run under the addendum (after amendment) | Est. GPU-h, RTX PRO 6000 / GB10 [INFERENCE: ×1.3 for blocks] |
|---|---|---|---|
| REAX 1.3 | yes | pending D5 (read-twice → read-once with a block), Lr render check; bariton only | ≈ 3.5 / — |
| Elephant-1 | yes | pending D5 for Arm N (past trained 16,384), Lr | ≈ 0.7 / 2.5 |
| Decider Flash v1.2 | no | yes: 25 options, 262,144 limit; Lr pending (protocol.py renders "State:\n"+state) | ≈ 1.3 / 5 |
| GLiDE 27B | no (v1.2 local is; not the same checkpoint, D7: no successor) | yes: 40,000 limit then 422; Lr on the new snapshot | ≈ 3.5 / 13 |
| KnowLine 31B Gen1.5 | no | edge: read twice ≤ 3,000 tokens → with a block, read once (same D5 issue as REAX); header ≤ 32,768 | ≈ 1.8 / 7 |
| Sieve 31B v3 | no | yes if `sieve-serve` refuses rather than cuts (card: never truncates) | ≈ 1.8 / 7 |
| Turion Jev 31B | no | yes: refuses > 65,536; FP8 vs bf16 setting must match its league row | ≈ 1.8 / 7 |
| d3-ultra | yes (no route) | yes after route + league row; 131,072 | ≈ 3.5 / 13 |
| GLiDE 9B, GLiDE 0.8B | no | yes (as GLiDE 27B) [INFERENCE: same 40,000 default] | ≈ 0.7 / 2.5 each |
| Cerno 9B v1.2 | no | edge: read twice ≤ 3,000 (D5), 20,480 limit refuses, trained 16k | ≈ 0.7 / 2.5 |
| KnowLine 4B Gen5.5 | no | edge: read twice (D5); FP8 at load in the card | ≈ 0.5 / 2 |
| StartLux 4B | no | yes at 25 options; licence cc-by-nc-4.0 (non-commercial; a benchmark run is [INFERENCE] fine, Can to confirm) | ≈ 0.5 / 2 |
| GLiDE 0.4B | no | **no as served: 7,999 tokens, silent head-keeping cut → fails Lr; "not tested: route cuts silently"** (Arm N's notes block alone is up to ≈ 5,000 tokens) | — |
| OneJev1.6-0.8B | no | unknown limits (Flide); Lr needs Flide's code | ≈ 0.5 / 2 |
| Jev 1.14 (ref) | yes | **not tested: conservative context guard** (addendum §6.2: refuses 1.3 % with no block) | — |

Total ≈ 25 GPU-h on RTX PRO 6000 cards, or ≈ 70–80 h on GB10 [INFERENCE] — on spark2 that would crowd out L&M/Reading for days; the decision arms should run on bariton cards. Conflicts: each model needs its league row first (D7 freezes the leaderboard setting: no league row = nothing to freeze), so §2 precedes §4 for the 12 new ones; one model per GPU (§8); the $110 cap is unaffected beyond ≈ $0.4 writer + P1s (all routes local).

## 5. Latency

Per Main (#4062): the combined page takes latency from Reading's pinned spark2 pass only, so backgammon runs **no** latency pass. Backgammon's own league latencies (different machines: bariton, three DGX Sparks, APIs; recorded per setup in `players.device`) stay on the backgammon pages as they are and are not used on the combined page.

## 6. Combined page feed: `…/backgammon/bench-scores.json`

Schema: Turkce's (#4062). Values for backgammon:
- `bench` `"backgammon"`, `title`, `url` (site root), `updated` (data as of), `score` `{"zero": 119.4 (Random's PR, with source), "hundred": 0}`.
- per model: `repo` / `commit` (HF id and the commit recorded in `players.settings`; `null` for hosted), `name` (setups.json label), `maker`, `kind` (`decision model` / `chat model` / `program`), `params_total`, `params_active`, `quantization` (`players.quantization`), `score_0_100`, `raw` `{"metric": "PR (500 × mean GNUbg 1.08 2-ply equity loss)", "value": PR, "questions": scored decisions, "options": mean legal plays}`, `calibration_error`, `improvement_points` (Part 3 verdict delta: risks found with lessons − no memory, per arm, null until published), `runs` (league / late-entry ids and match counts), `notes` (late entry; positions differ).

**calibration_error (as logic #4063):** ECE, 10 equal-width bins, on the chosen play's probability, "correct" = the chosen play is the engine's best play (loss < 0.001, the site's `best_play_loss_below`); exactly `analysis.calibration(...)["ece"]` already computed for the Confidence tab. `null` for chat models and programs. Flag for Ümit: (a) "best play" at 0.001 makes near-ties count as wrong though they cost nothing; an alternative "correct = not a blunder (loss ≤ 0.08)" is also computed on the site (`auroc_blunder`); (b) for split lists the stored probability is the one from the request that chose the play (group or final), not a full-list probability.

**Rows that would appear (only those with an HF repo id in `players.settings`):**

| Setup | repo @ commit | score | ECE (computed now) |
|---|---|---:|---:|
| REAX 1.3 | decisionmodels/REAX-1.3 @ fa4bf7ee | 76.7 | 0.037 |
| Base Labs Mammoth-1 | baselabs/mammoth-1 @ 61cec44c | 76.1 | 0.104 |
| Drex Max v1 | nace-ai/drex-max-v1 @ cac65e19 | 74.5 | 0.137 |
| Fastino GLiDE v1.2 (local) | fastino/GLiDE (now GLiDE-27B, tag glide-v1.2) @ a7e45896 | 70.3 | 0.026 |
| Drex 2.0 (local) | nace-ai/drex-v2.0 @ e6466744 | 64.0 | 0.157 |
| Base Labs Elephant-1 | baselabs/elephant-1 @ b3f8a934 | 62.7 | 0.036 |

(ECE over all valid scored decisions with a probability, league and late-entry; 1,993–3,493 each.) Not shown until a repo id/commit is recorded: Decider Flash v1.2 (repo known, commit not recorded), Decider v1.1/v1.2 27B, Winnow-12B, Clef, Cygnet, Open-Jev, Gemma 4 31B, Qwen3.8-27B, LFM2.5 — a `content/hf_repos.json` map (setup → repo, commit, source) would add them; Decision D6.

**Generator design (not built).** `tools/site/bench_scores.py`, called by `build.py` (step 3 of `update.sh`, so it writes inside `backgammon/` and goes through `checks.py` and the "touched files outside backgammon/" guard). Inputs: the snapshot `snap.db`, the score shards, `setups.json`, `hf_repos.json`. It reuses `league_web.error_rates` (plus the late-entry pass) and `analysis.calibration`; refuses (build check fails, no deploy) if any counted decision is pending, if Random has no rate, or if a row's repo/commit disagrees with `players.settings`. Output sorted by name, no timestamps besides `updated`, so the publish step's "no change" test keeps working. `checks.py` validates the schema and recomputes 3 rows.

## 7. Totals, schedule, decisions

**GPU time [INFERENCE, from the timings above]:**
- League entries (12): spark2 ≈ 25–35 h, or bariton ≈ 12–18 card-h; plus ≈ 4–9 card-h bariton for the 8 local opponents; ≈ $1.6 paid opponents.
- "Did they improve?" (14 runnable at most): ≈ 25 card-h bariton (≈ 70–80 h if on GB10).
- Latency: 0 (Reading's pass).
- **Total ≈ 45–55 bariton card-h, or ≈ 30 h spark2 + ≈ 35 card-h bariton.**

**Claims (as given):** bariton GPU 0 ours (Gemma) until ≈ 11 Nov 05:00 UTC; GPU 3 ours (Qwen3.8-27B, then LFM2.5); GPUs 1–2 compactor RL ≈ 2 days (≈ 12 Nov); spark2 logic until ≈ 22:00 UTC today, then shared in turn.

**Proposed schedule:**
1. Now (no GPU): adapters + smoke harness per route; Cerno wrapper; HF downloads to bariton/spark2 caches (≈ 260 GB in total); amendment draft; generator.
2. 10 Nov 22:00 → 11 Nov: spark2 small-entrant session (7 models together) after L&M/Reading have used each server; opponents on bariton GPU 0 from 05:00.
3. 11 Nov 05:00 →: bariton GPU 0: the five 26–31B entrants, one at a time (≈ 1.5–2 h each with opponents on GPU 3 when free), or on spark2 overnight slots if Can prefers bariton for "Did they improve?".
4. ≈ 12 Nov (GPUs 1–2 back): "Did they improve?" arms, one model per card, after the amendment is approved.
5. bench-scores.json live once the new rows are scored.

**Decisions for Ümit / Can:**
- D1 Entry: late-entry protocol (A, proposed) or a new season of the ladder (B; needs the newcomers' starting league).
- D2 Machine: backgammon league entries on spark2 (≈ 25–35 h of the shared server) or on a bariton card (≈ 4× faster).
- D3 GLiDE 0.4B: league with a smaller option cap so requests stay under 7,999 tokens, or "not tested: context too short" (and in Part 3: not tested, silent cut).
- D4 Settings per model: StartLux at 25 options (our split) vs its server's grouping; Cerno `max_model_len`; Turion FP8 (card) vs bf16; KnowLine 4B FP8 (card).
- D5 Part 3 amendment: which of the 15 join, and the read-once/past-trained-length edge settings (REAX, KnowLine ×2, Cerno, Elephant).
- D6 Combined page: Random's 119.4 as `zero`; ECE "correct" = best play (0.001) or not-a-blunder; add `hf_repos.json` for the locally served rows without a recorded commit.
- D7 StartLux cc-by-nc-4.0 for a benchmark run (Can).
- D8 GPT-6 Luna still out of credit: entrants play 18 of 19 as the Drex/REAX precedent, or top up.
