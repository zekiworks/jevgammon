# GLiDE v1.2 (local) vs hosted Fastino GLiDE – preparation

[ZEKI-BG-GLIDE-COMPARE-1564076956268634166]

Status: **blocked before the v1.2 run.** The local server is not running, and Can starts servers.
Everything that can be done offline is done:
- the positions are extracted;
- the hosted answers are graded;
- the replay requests are checked byte for byte;
- the reasoning question is answered from the server code.

No league table, page, `v3.db` row or model server was touched. The hosted API was not called.
`v3.db` was opened read-only.

## Positions

The set is every decision by the hosted **"Fastino GLiDE"** (player 30) in a valid, staged match since it joined League 2 on 2026-10-24 15:38 UTC. It counts model decisions only; forced moves and no-move turns are left out.

| | Matches | Games | Decisions |
|---|---:|---:|---:|
| League 2, ladder round 2 (matchdays 15–18) | 16 | 94 | 1,892 |
| League 2 pair of ladder round 3, played early (match 660 v Gemini 4 Argon (off), matchday 13). It held only by the hidden early-start league 4 and used League 2's rules and dice. | 1 | 6 | 130 |
| **Total** | **17** | **100** | **2,022** |

Notes on the set:
- There are 1,996 distinct position+dice pairs. Some positions repeat, such as openings.
- None of the decisions were invalid or fallbacks. All were prompt `bg-v2` and provider `fastino`, and every response names the model `glide_v2`.
- One decision (turn 145747, 263 legal plays) went in groups of 132, as in the league (3 requests). Every other decision was a single request.
- The two round-2 opponents Gemini 3.8 Flash (low) and Qwen3.8-27B (off) left League 2 at ladder round 3. Their matches with GLiDE stay in the set, and the site's scores give them league 2.

## Hosted GLiDE results (GNUbg, as on the site)

Grading uses the site's existing 2-ply scores (`~/.local/state/bg-site/plays`). All 2,022 decisions were already scored, so nothing was scored again.
- Error rate is 500 × mean equity loss, with a 95% interval from resampling games (2,000 resamples, seed 20261021).
- A best move is a loss below 0.001.

| Set | Decisions | Error rate | 95% interval | Best move |
|---|---:|---:|---:|---:|
| All 2,022 (main set) | 2,022 | **32.1** | 29.1–35.2 | **48.3%** (977) |
| Round 2 only | 1,892 | 32.0 | 28.8–35.4 | 48.6% (920) |

The paired comparison needs v1.2's answers, so it is not done yet. `compare.py` (below) prints it:
- the share of positions where both chose the same play;
- the positions where only v1.2, only the hosted model, both or neither found the best move;
- the paired error difference with a 95% interval from resampling positions.

## Replay requests: the same prompt and settings as League 1

- **Config** (`smoke/glide-compare/config.json`): League 1's top-level settings (`bg-v2`, order seed 1190975713392774006, 3 rounds, no clock, 300 max turns). It has one player, the unchanged `leagues/league1.json` roster entry "Fastino GLiDE v1.2 (local)":
  - spec `fastino/glide-v1.2`, `base_url` `http://127.0.0.1:18101`, `parallel` 4, bf16;
  - this matches `players.settings` in `v3.db` except the device history note.
- **Positions** (`smoke/glide-compare/positions.jsonl`): one row per hosted decision, holding:
  - the board and dice;
  - the stored legal plays and option order (`jevgammon` checks both);
  - the match context the model saw: score, round, rounds, leg, turn, turn limit and clock.

  For mirror-concurrent matches the score counts only earlier rounds. In an extra round the "rounds" shown is the round number.
- **Exact bodies** (`smoke/glide-compare/replay-requests.jsonl.gz`): the request for each of the 2,021 single-request decisions, with model `glide-v1.2`.
- **Checks of the requests:**
  - `jevgammon render` on these rows reproduces **all 2,307 stored single-request League 1 v1.2 requests byte for byte**. It also reproduces all 2,021 stored hosted League 2 requests, with `fastino/GLiDE` in place of `glide-v1.2` and nothing else changed. So both models get the same prompt.
  - `jevgammon ask` with this config was pointed at a throwaway request-capturing stub on port 18199, not a model, for 31 positions including the grouped one. It sent the 30 expected bodies exactly. It also sent both group requests of the 263-play turn identically to the hosted ones, model name aside. The final group request depends on the group winners, so it can differ.

## Reasoning setting of the local GLiDE v1.2 server

**There is no reasoning to switch on.** The evidence is in `glide/` of snapshot `a7e45896`, `glide-v12.sh` and the unit's start line.
- **How it answers:** it runs one forward pass per question. The hidden state of the last token goes through a 255-way readout, and a softmax gives the option probabilities (model card: "Nothing is generated"). `usage.output_tokens` is always 0.
- **The thinking setting:** the only one is a module constant, `REASONING_EFFORT = "medium"` in `glide/prompt.py`. With it, the chat template is rendered with `enable_thinking=True`, but the server then closes the think block itself, so the prompt ends `<think>\n\n</think>\n\nAnswer: (`.
  - At "medium" the template adds no reasoning instruction; only xhigh and low add text.
  - The prompt body ends "Think it through briefly, then answer with the option letter only.", but no tokens are generated.
- **Server-level settings:** the environment variables (`GLIDE_MODEL`, `_MODEL_NAME`, `_DEVICE`, `_MAX_LEN` 40000, `_TOKEN_BUDGET`, `_MAX_BATCH`, `_BATCH_WAIT_MS`, `_MAX_QUEUE`, `_REQUEST_TIMEOUT_S`, `_THREADS`, `_API_KEY`, pixel bounds) include no thinking or reasoning option.
- **Our start line:**
  ```
  CUDA_VISIBLE_DEVICES=$GLIDE_GPU GLIDE_MODEL=<snapshot> GLIDE_MODEL_NAME=glide-v1.2 GLIDE_DEVICE=cuda:0 GLIDE_MAX_BATCH=1 TRITON_CACHE_DIR=~/code/glide/triton-cache PYTHONPATH=<snapshot> .venv/bin/python -m uvicorn glide.server:app --host 127.0.0.1 --port 18101 --workers 1
  ```
  The journal shows the same command for the last start (2026-10-25 20:43 UTC).
- **Per request:** there is no setting. The handler passes only `state` and `questions` to the model and ignores any other field.
- **Decoding:** sampling is not used (`generation_config.json` sampling settings are never read). The softmax temperature is 1.0 from `decision_config.json`.

So the "reasoning on" run in item 3 cannot be done, and it was not prepared.

**The output tokens of the hosted run:** the request says the hosted run logged output tokens, but `v3.db` does not show that.
- Every hosted response, 2,024 of 2,024 in League 2, and League 1's as well, has `usage.output_tokens: 0`, and `turns.output_tokens` is 0.
- The hosted responses carry an extra `token_usage` field. It is 63–5,927 (median 228) above `input_tokens` and grows with the number of options (r = 0.95, about 34 + 22 per option). That looks like the option and readout scaffolding counted on Fastino's side, not generated text [INFERENCE].

## The run, once Can has started the server

**GPU:** one GPU with at least 62,000 MiB free (`glide-v12.sh` checks this). It uses 53.6 GiB after loading, and the card gives a 60.2 GB peak at 39k tokens. On bariton that is one RTX PRO 6000; League 1 used GPU 0. It loads in about 20 s.

Start (Can): `GLIDE_GPU=<N> tools/v3/servers/glide-v12.sh start`, then `tools/v3/servers/glide-v12.sh probe`.

Then, from the repo root:

```bash
FASTINO_API_KEY="$(cat ~/.config/fastino/key)" ./target/release/jevgammon ask \
  --config smoke/glide-compare/config.json \
  --positions smoke/glide-compare/positions.jsonl \
  --out smoke/glide-compare/v12.db \
  --setup "Fastino GLiDE v1.2 (local)"
python3 smoke/glide-compare/compare.py smoke/glide-compare/v12.db
```

- **The key:** it is set exactly as `run_league1.sh` does for League 1. The fastino client needs a key, but the request goes only to the `base_url` 127.0.0.1:18101. That server has no `GLIDE_API_KEY` and ignores the key. Nothing is sent to Fastino's API.
- **Re-runs:** a re-run asks only what is missing or failed.
- **Time:** League 1's v1.2 decisions took a median of 1.6 s each, 73 min in total for 2,313. So 2,022 decisions take about 1 h; with `GLIDE_MAX_BATCH=1` they run one at a time.
- **Grading:** it needs no new GNUbg run, because every legal play's 2-ply equity is already in `hosted-decisions.jsonl`.
- **Cost:** none. It uses no API.

## Files (`smoke/glide-compare/`)

- `hosted-decisions.jsonl`: one row per decision, with:
  - turn, match, game, round, leg, turn number, dice, legal plays and option order;
  - the hosted choice and its probabilities;
  - the 2-ply equity of every legal play, the hosted loss, and whether it was a best move.
- `positions.jsonl`: the `jevgammon ask` input.
- `config.json`: the ask config.
- `replay-requests.jsonl.gz`: the exact request bodies.
- `compare.py`: the grading and paired comparison.
