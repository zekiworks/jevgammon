# v3 model servers

Start/stop scripts for the self-hosted models of the v3 benchmark, on this machine's four
RTX PRO 6000 (96 GB) GPUs. Each script takes `start` (launch, then wait until it answers),
`stop` or `status`:

```sh
tools/v3/servers/qwen38-flash-next.sh start|stop|status
tools/v3/servers/wave.sh A|B|L1 start|stop|status|probe
tools/v3/servers/spark.sh start|stop|status|probe              # League 1 from 2026-10-16 (+ Gemma on spark3 2026-10-19 18:36-22:26)
GEMMA_GPUS=0 tools/v3/servers/gemma4-31b-replicas.sh start|stop|status   # League 1 2026-10-16 to 2026-10-19 (GPUs 0 1 3); League 2 from 2026-10-19 22:26 (GPU 0)
tools/v3/servers/spark3-flashnext.sh start|stop|status|probe   # League 2 Flash Next, 2026-10-19 (withdrawn, stopped)
tools/v3/servers/decider-v1.2.sh flash|27b start|stop|status|probe   # League 1 from 2026-10-19 (flash on GPU 3; 27b on GPU 1 once Qwen3.8-27B is done)
tools/v3/servers/winnow.sh start|stop|status|probe          # League 1 from 2026-10-19 (GPU 3)
tools/v3/servers/qwen38-27b.sh start|stop|status|probe      # League 2 from 2026-10-19 22:26 (GPU 1; GPU 3 2026-10-20 20:16-21:10; then spark, see the end)
tools/v3/servers/lfm25-24b.sh start|stop|status|probe       # League 2 from 2026-10-19 22:26 (GPU 2; spark3 from 2026-10-20 21:10)
D3_GPU=N tools/v3/servers/d3-turbo.sh download|setup|start|stop|status|probe   # Part A smoke test (vllm-sr/d3-turbo), see the end
NEMOTRON_GPUS=N[,M] [NEMOTRON_CHECKPOINT=24gb|bf16] tools/v3/servers/nemotron35-bolt.sh fetch|start|stop|status|probe   # Part A smoke test (Nemotron 3.5 Bolt), see the end
```

vLLM servers run as docker containers (`docker logs -f <name>`); the Python decision servers
run as transient systemd user units (`journalctl --user -u <unit> -f`). Neither restarts on
its own or comes back after a reboot. ComfyUI (`python main.py --listen`, about 8-24 GB on
GPU 0 and 0.5 GB on the others) stays up; the memory shares below leave room for it.

## Servers

| script | URL | served model name | checkpoint | weights as served | GPU | wave |
|---|---|---|---|---|---|---|
| `qwen38-flash-next.sh` | `http://127.0.0.1:8896/v1` (OpenAI-compatible) | `qwen3.8-flash-next` | `Qwen/Qwen3.8-Flash-Next-FP8` @ `236dfdf2`, `~/.cache/huggingface/hub` | `fp8` (checkpoint `quant_method: fp8`, 128×128 block scales, dynamic activations) | 0-3, TP4, 0.50 each | A |
| `gemma4-31b.sh` | `http://127.0.0.1:8894/v1` (OpenAI-compatible) | `gemma-4-31B-it` | `~/code/models/gemma-4-31B-it` (bf16 checkpoint) | `fp8` (vLLM `--quantization fp8`: quantized at load), FP8 KV cache | 3, 0.46 | A |
| `cygnet.sh` | `http://127.0.0.1:18093/v1/systemone` (vLLM `cygnet` on 8892) | `cygnet` | `google/gemma-4-12B-it` @ `707f0a3b`, `~/.cache/huggingface/hub` | `bf16` | 0, 0.45 | B |
| `clef.sh` | `http://127.0.0.1:18091/v1/systemone` | `clef` | `~/code/clef/model` (Qwen3.5 backbone + joint head) | `bf16` | 1 | B |
| `open-jev.sh` | `http://127.0.0.1:8791/v1/systemone` | (takes no model name) | `~/code/Open-Jev/checkpoints/open-jev-27b-v1.1` (LoRA rank 8 + head) on `Qwen/Qwen3.8-27B` @ `1d4bf0f2` | `bf16` | 2 | B |
| `decider.sh` | `http://127.0.0.1:18097/v1/systemone` | `pplx-decider-v1.1-27b` | `~/code/pplx-decider/checkpoint` | `bf16` | 3 | B |
| `d3-turbo.sh` | `http://127.0.0.1:18100/v1/systemone` (unit `v3-d3-turbo`) | `d3-turbo` (accepted, not checked) | `vllm-sr/d3-turbo` @ `a0f3e9e5`, `~/.cache/huggingface/hub` | `bf16` (fp32 readout) | `D3_GPU`, about 52 GiB | Part A |
| `nemotron35-bolt.sh` | `http://127.0.0.1:8893/v1` (OpenAI-compatible; container `v3-nemotron35-bolt`) | `nemotron-3.5-bolt` | `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB` @ `cf2effc5` + drafter `…-24GB-LiLiCorr` @ `449d2414`, `~/.cache/huggingface/hub` | IQ2_XXS routed experts (2.06 bits, QAD), Q8_0 / W4A16 NVFP4 elsewhere; FP8 KV cache | `NEMOTRON_GPUS` (one), 0.50 (two GPUs: BF16 @ `56702103`, TP2, 0.92 each) | Part A |

The "weights as served" column is what goes into a player config's `quantization` (and so
`turns.quantization`).

- **Qwen3.8 Flash Next**: image `vllm/vllm-openai:qwen38-flash-next` with the v1 model flags
  (`--reasoning-parser qwen3`, `--attention-config.indexer_kv_dtype fp8`, `--max-logprobs 20`).
  Memory changes against v1: `--gpu-memory-utilization 0.50`, `--max-num-seqs 16`,
  `--max-num-batched-tokens 2048`, no image/video inputs, and the classic inductor compile path
  (see the comment in the script; the standalone path needs about 81 GiB per GPU while it
  compiles, which GPU 0 does not have next to ComfyUI). `NCCL_P2P_DISABLE=1`, because direct
  GPU-to-GPU copies on this machine arrive corrupted. KV cache: 220k tokens.
- **Gemma 4 31B**: image `vllm/vllm-openai:v0.30.0` with the flags of
  `~/code/gemma4-31b/compose.yaml` (`--reasoning-parser gemma4`), minus tool calling, plus
  `--max-logprobs 20` and no image/video/audio inputs. KV cache: 41k tokens (1.26 sequences
  of the 32,768-token limit).
- **Cygnet**: `shim/decision_server.py` with `SHIM_TEMPERATURE=3.4`, as in v1.
- **Open-Jev**: `--batch-size 8 --prefix-cache --max-length 4096`, as in v1.
- **Decider**: answers one request at a time; others get 529 with `Retry-After`.

## Thinking on and off

Both OpenAI-compatible servers switch reasoning with the chat template's `enable_thinking`,
passed in the request body (a player config's `request`):

| model | thinking on | thinking off |
|---|---|---|
| `qwen3.8-flash-next` | `{"chat_template_kwargs": {"enable_thinking": true}}` (also the template default) | `{"chat_template_kwargs": {"enable_thinking": false}}` |
| `gemma-4-31B-it` | `{"chat_template_kwargs": {"enable_thinking": true}}` | `{"chat_template_kwargs": {"enable_thinking": false}}` (also the template default) |

The reasoning comes back in `choices[0].message.reasoning` (vLLM's reasoning parsers), not in
`content`. Both accept `logprobs: true` with `top_logprobs: 20`, and an assistant prefill with
`continue_final_message: true` (plus `add_generation_prompt: false`).
`probe_chat.py` checks all of this:

```sh
tools/v3/servers/wave.sh A probe     # or: python3 tools/v3/servers/probe_chat.py http://127.0.0.1:8894/v1 gemma-4-31B-it
```

## Waves

The two 27B decision servers, Clef and Cygnet do not fit next to Qwen's TP4 shards, so the
servers come in two waves that are never up together:

| | GPU 0 | GPU 1 | GPU 2 | GPU 3 |
|---|---|---|---|---|
| wave A | Qwen 48.6 + ComfyUI (8-24) | Qwen 48.6 | Qwen 48.6 | Qwen 48.6 + Gemma 41.5 |
| wave B | Cygnet 42.2 + ComfyUI (8-24) | Clef 51.9 | Open-Jev 51.8 | Decider 49.2 |
| wave L1 | Cygnet 32.5 (share 0.34) + Gemma 42.5 + ComfyUI | Clef 55.5 | Open-Jev 52.8 | Decider 51.6 |

(GiB in use per process, measured with `nvidia-smi` on 2026-10-14; each card has 95.6 GiB.)

```sh
tools/v3/servers/wave.sh A start                                      # about 5 min (Qwen, then Gemma)
tools/v3/servers/wave.sh A stop && tools/v3/servers/wave.sh B start   # A -> B, about 3 min
tools/v3/servers/wave.sh B stop && tools/v3/servers/wave.sh A start   # B -> A, about 5 min
tools/v3/servers/wave.sh A status; tools/v3/servers/wave.sh B status
tools/v3/servers/wave.sh B probe     # a 2-option Choice to each decision server
```

The DeepSeek V4.1 Flash server (`deepseek-v41.service`, all four GPUs, port 8010) must be
stopped for either wave: `systemctl --user stop deepseek-v41.service`. It is enabled at boot.

## League 1 layout (wave L1)

League 1 needs Gemma 4 31B next to the four decision servers. Wave L1 is wave B with Cygnet's
vLLM at a 0.34 memory share (`CYGNET_UTIL`; 0.32 leaves too little KV cache for its 16,384-token
context) and Gemma on GPU 0 (`GEMMA_GPU=0`), which leaves about 20 GiB on GPU 0 for ComfyUI.
Qwen3.8 Flash Next (wave A) cannot run at the same time; it plays in League 2.

    tools/v3/servers/wave.sh L1 start|stop|status|probe

## League 1 on the DGX Sparks (from 2026-10-16)

From 2026-10-16 11:04 UTC, Clef, Cygnet and Decider served League 1 from two DGX Sparks
(NVIDIA GB10, 121 GiB unified memory, aarch64) with the same checkpoints, code, package
versions and server arguments, so that Gemma 4 31B (on), the slowest player, could run on
three of this machine's GPUs at once. Open-Jev stayed here. Each player's `base_url` in the
roster points at its server, and its `device` field and note record the move.

| host | server | URL | memory in use (`nvidia-smi`, 2026-10-16) |
|---|---|---|---|
| `spark` (spark-002e, 192.168.1.127) | Cygnet: vLLM share 0.28 (34 GiB; 0.34 of a 95.6 GiB card here) + shim | `http://192.168.1.127:18093` | 31.8 GiB |
| `spark` | Clef | `http://192.168.1.127:18091` | 51.4 GiB |
| `spark3` (spark-194d, 192.168.1.139) | Decider v1.1 27B | `http://192.168.1.139:18097` | 48.8 GiB |
| this machine, GPU 2 | Open-Jev 27B v1.1 (`open-jev.sh`) | `http://127.0.0.1:8791` | 52.9 GiB |
| this machine, GPUs 0, 1, 3 | Gemma 4 31B, one replica each (share 0.85, 195k-token KV cache each) behind `gemma_proxy.py` | `http://127.0.0.1:8894/v1` | 78.6 GiB each |

```sh
tools/v3/servers/spark.sh start|stop|status|probe     # ssh to the Sparks; about 10 min to load
tools/v3/servers/gemma4-31b-replicas.sh start|stop|status
curl -s http://127.0.0.1:8894/proxy/status            # requests in flight per replica
```

`spark.sh` copies `_lib.sh` and the server scripts to `~/code/v3-servers` on each Spark and
runs them there with `BIND_HOST=0.0.0.0` (the servers listen on the LAN; Cygnet's shim then
needs `CYGNET_ALLOW_NO_KEY=1`, which `cygnet.sh` sets) and GPU 0. What each Spark needed:

- The projects at the same paths (`~/code/clef`, `~/code/cygnet`, `~/code/pplx-decider`,
  `~/code/Open-Jev`), their checkpoints and the Hugging Face snapshots
  (`google/gemma-4-12B-it` @ `707f0a3b`, whose two large files live in `hub/blobs/??/`, and
  `Qwen/Qwen3.8-27B` @ `1d4bf0f2`), copied with `rsync` from here.
- aarch64 virtualenvs with the same packages: `uv venv --python 3.12.13`, then
  `uv pip install -r` the `uv pip freeze` of this machine's venv (PyPI's aarch64 torch wheels
  are CUDA 13.0 builds; Open-Jev also `uv pip install --no-deps -e .`). Docker images: the
  aarch64 `vllm/vllm-openai:v0.30.0`. Docker on the Sparks has no `nvidia` runtime
  registered; `docker_gpu` then passes `--gpus` alone. `spark3` needed
  `loginctl enable-linger` so the systemd user units outlive the ssh session.
- Free memory: on a GB10, CUDA reports `MemFree` as free GPU memory, so page cache left by
  loading checkpoints counts as used and vLLM's and Decider's start-up checks fail.
  `free_page_cache` (`_lib.sh`) touches anonymous memory up to `MemAvailable` before each
  start so the kernel drops that cache. Open-Jev peaks near 108 GiB while it loads the whole
  Qwen3.8-27B checkpoint, so it cannot load next to Decider on one Spark.

Equivalence check before the switch: 20 League 1 requests per player, taken at random from
the last 400 stored exchanges, sent to both servers (this machine's servers reproduced the
stored answers exactly):

| player | same play | max \|Δp\| | median latency here | median latency on the Spark |
|---|---|---|---|---|
| Clef | 20/20 | 0.007 | 0.92 s | 5.40 s |
| Cygnet | 20/20 | 0.042 | 0.29 s | 0.62 s |
| Decider v1.1 27B | 20/20 | 0.029 | 0.58 s | 3.49 s |
| Open-Jev 27B v1.1 | 18/20 (not moved) | 0.0045 | 1.56 s | 8.48 s |

Open-Jev's two other plays were near-ties (top two 0.00003 and 0.004 apart), but more than
one in 20 differing kept it here.

`gemma_proxy.py` (aiohttp, run with `uv run --script`) sends each request to the replica with
the fewest in flight, passes method, path, headers and body through unchanged and streams the
response back as it arrives; a replica that refuses the connection is skipped.

Measured on 2026-10-16 with Gemma 4 31B (on) in 9 matches at once: 342 generated tokens/s
over the three replicas, 3 requests running on each (about 38 tokens/s per request; one
GPU next to Cygnet gave about 154 tokens/s over 4 matches). A thinking decision still takes
about 130 s; what grew is the number of matches played at once.

## League 1 late joiner: Gemma 4 31B on spark3 (from 2026-10-19)

Liquid d1-ultra joined the finished League 1 on 2026-10-19 (`league-add`, 13 matches) when
bariton's GPUs were no longer available. From 18:36 UTC both Gemma 4 31B setups play from one
server on spark3 next to Decider (`spark.sh` starts it after Decider; `BIND_HOST=0.0.0.0`):
same `gemma4-31b.sh` arguments, image `vllm/vllm-openai:v0.30.0` (aarch64, pulled by the
digest spark has), checkpoint `~/code/models/gemma-4-31B-it` copied from here, memory share
0.45 (55.3 GiB in use next to Decider's 50.0 GiB; 233,725-token FP8 KV cache). URL
`http://192.168.1.139:8894/v1`, in the roster's `base_url`, `device` and the league note.

Equivalence check: 20 Gemma 4 31B (off) requests taken at random from the last 400 stored
League 1 exchanges, replayed on spark3: same play 19/20 (the other: stored Q 0.94 / A 0.06,
spark3 A 0.80 / Q 0.20), max |Δp| 0.67, median |Δp| under 0.0001, median latency 0.87 s. That is
within the one-in-20 rule used for the 2026-10-16 moves; there was no alternative host.
(on) is sampled at temperature 1, so it was only checked to answer with letter probabilities.

Open-Jev 27B v1.1 failed the same check on a GB10 (18/20) and its GPU on bariton is not
available, so its match against Liquid d1-ultra stays deferred until `open-jev.sh` runs again.

At 19:31 UTC League 1 became decision models only and both Gemma 4 31B setups moved to League 2
(`leagues/league2-l1chat.json`, `league-add`), on the same spark3 server. For League 2's thinking
matches the server runs 24 sequences at once (`GEMMA_MAX_SEQS=24` in `spark.sh`, was 16; same
memory share and KV cache): with 16 running it generated about 84 tokens/s in total (5.3 per
request) with the KV cache a third full. Restarting it does not touch Decider. From 2026-10-19
22:26 UTC both setups play on bariton GPU 0 again (below); spark3's Gemma server is stopped
(`ssh spark3 'cd ~/code/v3-servers && ./gemma4-31b.sh stop'`, Decider untouched).

## League 1 late joiners on bariton GPU 3 (from 2026-10-19)

Only GPU 3 is available on bariton (GPUs 0-2 hold other work), and Open-Jev 27B v1.1
(`open-jev.sh`, 54.0 GiB) runs there again. Two local decision models joining League 1 late
run next to it, both started with the arguments the Turkish benchmark used:

| script | URL | served model name | checkpoint | weights as served | GPU memory |
|---|---|---|---|---|---|
| `decider-v1.2.sh flash` | `http://127.0.0.1:18098/v1/systemone` (unit `v3-decider-flash-v12`) | `pplx-decider-flash-v1.2` | `~/code/pplx-decider/checkpoint-flash-v1.2` (rsync from spark3) | `bf16` | 9.3 GiB idle, about 13 GiB under load |
| `winnow.sh` | `http://127.0.0.1:8091/v1/systemone` (container `v3-winnow`) | `winnow-12b` | `~/code/winnow/models/gguf/Winnow-12B-Q8_0.gguf` | Q8_0 GGUF, Q8_0 KV cache | 14.6 GiB |

- **Decider Flash v1.2**: `~/code/pplx-decider/pplx_decider_server.py` (from turkce-benchmark
  `runner/servers` at `febf46c`) in `.venv-v1.2`, which holds only the checkpoint's
  `requirements.txt` on uv's Python 3.12.13 (Triton needs the headers). Reference path, one
  request at a time; the request's model must name the loaded checkpoint. It plays through
  the `pplx-local` service (25 options per request at most, as Decider v1.1).
- **Winnow-12B**: image `winnow-inference:d4631fb`, 8,192-token context, 4 decision slots,
  selected head, optimized pipeline, text only. A stored 110-option League 1 request cut to
  48 options took 7,679 input tokens, so the `winnow` service sends at most 40.
- **Decider v1.2 27B** (`decider-v1.2.sh 27b`, port 18099) did not fit here: 49 GB of bf16
  weights against 44 GiB free on GPU 3, 20 GiB available on spark and 5 GiB on spark3. It
  waits for bariton GPU 1 overnight (next section).

## League 2 overnight on bariton GPUs 0-2 (from 2026-10-19 22:26 UTC)

bariton's GPUs 0-2 were free overnight. From 22:26 UTC (league2 restart) they serve League 2's
self-hosted players, one server per GPU; GPU 3 keeps League 1's Open-Jev, Winnow-12B and
Decider Flash v1.2. `tools/v3/league_control.sh` stops and starts all of them (see the repo
README); `free` gives GPUs 0-2 back and lets both leagues play on without them.

| GPU | script | URL | served model name | checkpoint, weights as served | memory |
|---|---|---|---|---|---|
| 0 | `GEMMA_GPUS=0 GEMMA_MAX_SEQS=24 gemma4-31b-replicas.sh` | `http://127.0.0.1:8894/v1` (proxy) -> `:8900` | `gemma-4-31B-it` | as before: bf16 checkpoint, online FP8, FP8 KV cache; share 0.85, 24 sequences, 194,617-token KV cache | 80.7 GiB |
| 1 | `qwen38-27b.sh` | `http://127.0.0.1:8897/v1` (container `v3-qwen38-27b`) | `qwen3.8-27b` | `Qwen/Qwen3.8-27B` @ `1d4bf0f2` (bf16) served in fp16; share 0.90, 32 sequences, 65,536-token context | 85.7 GiB |
| 2 | `lfm25-24b.sh` | `http://127.0.0.1:8898/v1` (container `v3-lfm25-24b`) | `lfm2.5-24b-a2b` | `LiquidAI/LFM2.5-24B-A2B` @ `1769516a`, bf16; share 0.90, 32 sequences, 2.07M-token KV cache | 86.5 GiB |

All three run `vllm/vllm-openai:v0.30.0` with raw top-20 logprobs and the checkpoints'
sampling defaults (the league sets temperature 1). Equivalence check before the switch: 20
stored League 2 (off) requests per model, replayed with the stored messages:

| player | stored on | same top letter | max \|Δp\| | median \|Δp\| | median latency |
|---|---|---|---|---|---|
| Gemma 4 31B (off) | spark3 (GB10) | 20/20 | 0.08 | 0.00002 | 0.66 s |
| Qwen3.8-27B (off), fp16 | Cerebras fp16 (OpenRouter) | 18/20 | 0.15 | 0.034 | 1.4 s |
| Qwen3.8-27B (off), bf16 (not used) | | 17/20 | 0.16 | 0.042 | 0.4 s |
| LFM2.5-24B-A2B (off), bf16, `<think></think>Answer:` prefill | Liquid AI's API, same prefill (LocalQwenLfm's baseline) | 14/20 | 0.21 | 0.098 | 0.13 s |
| LFM2.5-24B-A2B (off), FP8 `f54bf395` (not used) | | 12/20 | 0.22 | 0.13 | 0.11 s |

Qwen's differing letters were near-ties (stored top two 0.004-0.055 apart). For LFM, Liquid's
API against its own baseline gave 19/20, local bf16 against local FP8 15/20; the (off)
distributions are flat (7 of the 20 have Liquid's top two within 0.06). Both (on) setups were
smoke-tested through the runner (`jevgammon ask`, 5 positions each): all answered with
probabilities; Qwen (on) 484-10,211 reasoning tokens at about 27 tokens/s per request, LFM (on)
14,221-24,016 output tokens at about 70 tokens/s per request (5 at once).

Throughput in the first minutes of play (vLLM metrics over 60 s): Gemma 676 generated tokens/s
with 24 requests running (about 28 per request, about 2 minutes per thinking decision; spark3
gave about 5 per request); LFM2.5 about 800 tokens/s with 16 thinking matches (about 50 per
request, about 10 minutes per (on) decision at its 29k tokens); Qwen mostly prefill (about
5,000 prompt tokens/s from the (off) matches against fast opponents).

Decider v1.2 27B (53 GiB under load, measured on GPU 2 before LFM2.5 took it) fits next to none
of these. `tools/v3/swap_qwen_decider.sh` (unit `v3-swap-qwen-decider`) waits until
Qwen3.8-27B has no League 2 fixture left to play (except against OpenRouter players, out of
credit since 22:26), then stops Qwen, starts Decider v1.2 27B on GPU 1 and adds it to League 1
(`league-add`, entry in `leagues/league1.json`; smoke test on 2026-10-19: 10/10 answered with
probabilities, 10 s for all 10).

## League 2 Flash Next on DGX Spark spark3 (2026-10-19, withdrawn)

Withdrawn later on 2026-10-19 (7-20 minutes per thinking decision); the spark3 server is
stopped and spark3 serves League 1 again (Decider and Gemma 4 31B, see above).

bariton's GPUs are taken, so both Qwen3.8 Flash Next setups of League 2 joined late
(`leagues/league2-flashnext.json`, `league-add`) against one server on spark3 (GB10,
`http://192.168.1.139:8896/v1`, served name `qwen3.8-flash-next`): the MiaAI-Lab single-Spark
recipe (`~/code/Qwen3.8-Flash-Next-Single-DGX-Spark`, `.env` as on spark2), image
`vllm/vllm-openai:qwen38-flash-next`, checkpoint `Mia-AiLab/Qwen3.8-Flash-Next-NVFP4` (99 GB:
MXFP8 attention, NVFP4 experts via Marlin, the 27 GiB n-gram table memory-mapped on the CPU),
all copied from spark2. Overrides: `--max-model-len 32768`, `--max-num-seqs 8`,
`--max-logprobs 20`, port 8896; MTP speculation (3 tokens), FP8 KV cache (611k tokens) and
`--reasoning-parser qwen3` as the recipe has them. Start-up takes about 13 minutes.

Smoke test (first 10 of `positions/smoke.jsonl`, `smoke/flashnext-spark3.db`) against the
bariton FP8 server (`smoke/answers.db`): letter probabilities from logprobs on every answer,
no invalid answers. Off: same top letter 9/10, median max |dp| 0.08; about 2 s per request
alone, but 444 s on average while 8 thinking requests held every slot, hence (on) 6 and (off)
2 requests in flight. On: same top letter 6/10; about 18,500 reasoning tokens per decision at
15 tokens/s per request with 8 running (bariton FP8: 54 tokens/s), about 20 minutes a decision.

## League 1's last matches and League 2's DeepSeek V4.1 Flash (2026-10-20)

From 20:09 UTC bariton's GPUs were free again for the leagues. League 1's last 16 matches (all
Decider v1.2 27B's) ran with Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B together on
GPU 1 (`DECIDER_V12_GPU=1`, `WINNOW_GPU=1`; 81 GB; Open-Jev was not needed) and Clef, Cygnet
and Decider v1.1 on the Sparks as before; League 1 finished at 20:41:52 UTC. League 2's
Gemma 4 31B (GPU 0), LFM2.5-24B-A2B (GPU 2) and Qwen3.8-27B (`QWEN27_GPU=3`) played on their
overnight servers until 21:10.

Then DeepSeek V4.1 Flash (off, on) moved from Fireworks (OpenRouter) to our own server, which
needs all four GPUs: `~/code/deepseek-v4.1-flash-4x-rtx-pro-6000`, started with
`BIND_ADDRESS=127.0.0.2 docker compose -f compose.yaml up -d` (launcher defaults; listening on
`127.0.0.2:8010` so the league could not reach it before the check; `deepseek-v41.service`
stays disabled), checkpoint `DeepSeek-V4.1-Flash-1017` @ `1bae0e10`. The other self-hosted
League 2 players moved to the Sparks, freed by League 1, with the same scripts:

| host | server | URL | memory share |
|---|---|---|---|
| `spark3` (spark-194d) | `gemma4-31b.sh` (`GEMMA_MAX_SEQS=24`), started first: it loads the bf16 checkpoint and quantizes, and was OOM-killed when started after LFM2.5 | `http://192.168.1.139:8894/v1` | 0.45 |
| `spark3` | `lfm25-24b.sh` (`LFM_GPU=0`) | `http://192.168.1.139:8898/v1` | 0.45 |
| `spark` (spark-002e) | `qwen38-27b.sh` (`QWEN27_GPU=0`) | `http://192.168.1.127:8897/v1` | 0.85 |

All with `BIND_HOST=0.0.0.0`, scripts copied to `~/code/v3-servers`, the LFM2.5 checkpoint
copied to spark3. Equivalence, 20 stored League 2 (off) requests each, reference = the stored
answers:

| player | stored on | replayed on | same top letter | max \|Δp\| | median \|Δp\| |
|---|---|---|---|---|---|
| Qwen3.8-27B (off) | bariton GPU 1 | bariton GPU 3 | 20/20 | 0.008 | 0.002 |
| Qwen3.8-27B (off) | bariton | spark | 20/20 | 0.005 | 0.002 |
| LFM2.5-24B-A2B (off) | bariton GPU 2 | bariton GPU 2 (same server) | 18/20 | 0.15 | 0.04 |
| LFM2.5-24B-A2B (off) | bariton | spark3 | 20/20 | 0.10 | 0.05 |
| Gemma 4 31B (off) | bariton | spark3 | 20/20 | 0.50 | 0.0000 |
| DeepSeek V4.1 Flash (off) | Fireworks | our server, two runs | 16/20, 17/20 | 0.49 | 0.09 |
| DeepSeek V4.1 Flash (off) | Fireworks | Fireworks again | 18/20 | 0.18 | 0.05 |

Our DeepSeek server is not deterministic (|Δp| about 0.1 between two runs of the same request);
Fireworks disagrees with its own stored answers about as often, so DeepSeek played on locally
(Main's call). Its answers end with `<｜end▁of▁sentence｜>` in the logprobs, as vLLM's end with
`<|im_end|>`; the runner skips such trailing special tokens since `afc7b41` (before it, all of
Qwen3.8-27B (off)'s vLLM decisions fell back to the sampled letter; its matches were replayed,
see `freeze/league2-changes.json`).

## Part A smoke test: vllm-sr/d3-turbo

`d3-turbo.sh` runs the System One server the Hugging Face package ships (`d3_server.py`, Python
standard library) from the pinned snapshot `a0f3e9e59ebd1202fe1d4de1c4c0f9a986758cbb`, with the
package's runtime (`d3_runtime.D3`; reviewed in `d3-turbo-code-review.md`). vLLM does not serve
it. Python: `~/code/pplx-decider/.venv` (`D3_PYTHON`), which has the versions the package's
`requirements.txt` pins (transformers 5.17.0, flash-linear-attention 0.5.2; torch 2.14.0, CUDA
13.0); `setup` builds a separate `~/code/d3-turbo/.venv` from that file instead.

- Model: Qwen3.5 backbone (26.09B, bf16) plus a 255-row readout over answer codes (A..Z, AA..):
  the options are listed under codes, the prompt is read once without generating text, and the
  probabilities are a softmax over the shown options' codes at temperature 1.0. No thinking
  (the template is rendered with `enable_thinking=False`), no permutation averaging.
- Limits: 255 options per question and 32,768 tokens per question prompt (the server has no
  `long_context` switch); the `d3` service sends at most 200 options, so the smoke positions
  (2-24 plays, about 3,500 + 120 tokens each) go in one request.
- One request at a time (a lock); others wait in the server, so players use `parallel: 1`.
- Memory: 48.6 GiB of weights; `start` refuses a GPU with less than 56,000 MiB free
  (`D3_MIN_FREE_MIB`). Not yet measured; record `nvidia-smi` after the run.
- Start-up: `--verify fast` (manifest hashes), then a kernel warm-up (text batches 1-8 and
  three image requests). `HF_HUB_OFFLINE=1`, so `download` must have run first.

```sh
tools/v3/servers/d3-turbo.sh download                 # once, 52 GB
D3_GPU=N tools/v3/servers/d3-turbo.sh start && tools/v3/servers/d3-turbo.sh probe
target/parta/release/jevgammon ask --config leagues/smoke-parta-d3.json \
  --positions positions/smoke.jsonl --out smoke/part-a.db --time-limit 600
tools/v3/servers/d3-turbo.sh stop
```

## Part A smoke test: Nemotron 3.5 Bolt 74B-A9B

`nemotron35-bolt.sh` serves NVIDIA's Nemotron 3.5 Bolt 74B-A9B (Mamba-2/attention hybrid
LatentMoE, 88 layers of which 8 attention, 2 KV heads; vision encoder unused) with NVIDIA's vLLM
recipe, minus tool calling and image/video inputs, plus `--max-logprobs 20`. Both setups,
(off) and (on), use the one server (`leagues/smoke-parta-nemotron.json`; BF16:
`leagues/smoke-parta-nemotron-bf16.json`, players "Nemotron 3.5 Bolt BF16 (off)/(on)").

- Checkpoint: `NEMOTRON_CHECKPOINT=24gb` (default with one GPU in `NEMOTRON_GPUS`) serves the
  24GB build (`cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f`; NVIDIA's inference checkpoint, 24.1 GB)
  with its LiLiCorr DFlash drafter (`449d24140160b8e51871bfc0f0a7338abf640aa1`, 7 speculative
  tokens, standard rejection sampling, so the target's distribution; `NEMOTRON_SPEC=0` drops it).
  `NEMOTRON_CHECKPOINT=bf16` (default with two GPUs, e.g. `NEMOTRON_GPUS=1,2`) serves the BF16
  release (`567021037ff88364143e24ea05e6abd0f72086ff`, 149.8 GB, about 75 GB of weights per GPU)
  with TP2 and `NCCL_P2P_DISABLE=1`, memory share 0.92 each, no drafter.
- Image: both model cards require vLLM nightly `77154ca6` (2026-10-14; `v0.30.0` is older).
  `fetch` builds `v3-vllm-nemotron35:77154ca6` from it with `b12x==1.5.1` (the SM120 kernels for
  the IQ2/Q8_0/NVFP4 layers, `vllm[b12x]` at that commit) and `vllm download-kernels`, and
  downloads the pinned snapshots at `nice 19`/idle I/O; `start` runs `fetch` when something is
  missing. Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER=1`), FlashInfer attention and Mamba
  kernels, `--mamba-cache-mode align`, bf16 Mamba states, `--trust-remote-code`.
- Thinking: `chat_template_kwargs.enable_thinking` (template default true; false ends the
  prompt with `<think></think>`, so (off) prefills `<think></think>Answer:`). The template has
  no effort level except `medium_effort: true`; (on) uses the default (full) and sends no
  `reasoning_effort`. NVIDIA's `ultra_v3` reasoning parser (`ultra_v3_reasoning_parser.py` in
  the snapshot, a `deepseek_r1` subclass) returns the reasoning under `reasoning`.
- Limits: 65,536-token context (the model takes 262,144), 16 sequences. A smoke prompt is
  about 3,500 + 120 tokens per option, under 7,000 for 24 options, so every position goes in
  one request (the runner splits only above 26 options); (on) has `max_tokens` 32,000.
- Memory: about 25 GB of weights; share 0.50 (48 GiB) leaves room for the FP8 KV cache
  (8 attention layers × 2 KV heads × 128: 4 KiB a token) and the Mamba states. Not yet
  measured; record `nvidia-smi` and the KV-cache size from `docker logs` after the run.
- Sampling: `generation_config.json` (top_p 0.95); the runner sets temperature 1.

```sh
NEMOTRON_GPUS=3 tools/v3/servers/nemotron35-bolt.sh fetch   # once: snapshots + image (about 10 GB pull)
NEMOTRON_GPUS=3 tools/v3/servers/nemotron35-bolt.sh start && tools/v3/servers/nemotron35-bolt.sh probe
target/parta/release/jevgammon ask --config leagues/smoke-parta-nemotron.json \
  --positions positions/smoke.jsonl --out smoke/part-a.db --time-limit 600
tools/v3/servers/nemotron35-bolt.sh stop
```

BF16 on two GPUs: `NEMOTRON_GPUS=1,2 tools/v3/smoke_parta.sh nemotron-bf16` (fetch downloads
150 GB; check `df` first).

## League 2's last matches back on bariton (2026-10-22)

League 2 paused 15:27:13 UTC (`systemctl --user kill -s SIGINT league2`; `resume-league2` stopped),
DeepSeek's server stopped 15:27:43 and DeepSeek V4.1 Flash (off, on) went back to Fireworks via
OpenRouter (provider pinned, fallbacks off; the roster entry as before 2026-10-20 21:56 UTC). On
bariton: `GEMMA_GPUS="0 1" GEMMA_MAX_SEQS=24 gemma4-31b-replicas.sh start`, `LFM_GPU=2 lfm25-24b.sh start`,
`QWEN27_GPU=3 qwen38-27b.sh start` (URLs `127.0.0.1:8894/8898/8897`; ComfyUI kept its share of GPUs 2
and 3). 20 stored League 2 (off) requests (`/tmp/equiv.py`): Gemma 20/20 (max |Δp| 0.044), LFM2.5 17/20
(max 0.15; not deterministic), Qwen 20/20 (max 0.007). Resumed 15:37:42; Spark copies stopped 15:40.
See `freeze/league2-changes.json`.
