# v3 model servers

Start/stop scripts for the self-hosted models of the v3 benchmark, on this machine's four
RTX PRO 6000 (96 GB) GPUs. Each script takes `start` (launch, then wait until it answers),
`stop` or `status`:

```sh
tools/v3/servers/qwen38-flash-next.sh start|stop|status
tools/v3/servers/wave.sh A|B start|stop|status|probe
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
