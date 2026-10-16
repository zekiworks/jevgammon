# v3 model servers

Start/stop scripts for the self-hosted models of the v3 benchmark, on this machine's four
RTX PRO 6000 (96 GB) GPUs. Each script takes `start` (launch, then wait until it answers),
`stop` or `status`:

```sh
tools/v3/servers/qwen38-flash-next.sh start|stop|status
tools/v3/servers/wave.sh A|B|L1 start|stop|status|probe
tools/v3/servers/spark.sh start|stop|status|probe              # League 1 from 2026-10-16
tools/v3/servers/gemma4-31b-replicas.sh start|stop|status      # League 1 from 2026-10-16
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
