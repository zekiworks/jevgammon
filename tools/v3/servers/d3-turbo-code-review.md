# vllm-sr/d3-turbo remote code review

Revision `a0f3e9e59ebd1202fe1d4de1c4c0f9a986758cbb` (Hugging Face API `sha` on 2026-10-21,
`lastModified` 2026-10-20T15:49:39Z). Every file below was read from
`https://huggingface.co/vllm-sr/d3-turbo/raw/<sha>/<file>`, and the SHA-256 of each `.py`,
`chat_template.jinja`, `config.json`, `decision_config.json`, `requirements.txt` and
`tokenizer_config.json` matches the package's own `MODEL_MANIFEST.json`, which `d3_server.py
--verify fast` checks again at load (files up to 64 MiB hashed, weight shards size-checked).

Checked for: network calls, subprocess / `os.system`, `eval` / `exec`, pickle or `torch.load`,
downloads of further code (Hub, pip), file writes outside the cache, environment variables,
telemetry. Found: no subprocess, `eval`/`exec`, pickle, `torch.load` or pip anywhere; weights
load only through safetensors; no telemetry; no file writes except a deleted video temp file and
Triton's kernel cache.

| file | what it does | findings |
|---|---|---|
| `config.json` | Qwen3.5 config (`model_type: qwen3_5`, bf16), `auto_map: AutoModel -> modeling_d3.D3Model`, custom pipeline `decision -> pipeline_d3.D3Pipeline` | remote code only through `trust_remote_code`; the tokenizer and processors are stock classes (`Qwen2Tokenizer`, `Qwen3VLProcessor`), no `auto_map` |
| `decision_config.json` | readout contract `d3-code-readout-v1`: 255 answer codes (A..Z, AA..JT) and their token ids, `attention_mode: prefix_bidir`, temperature 1.0, fp32 readout, `validated_length` 32,768, Box/track calibration | data only |
| `MODEL_MANIFEST.json` | SHA-256 and byte size of every file, model name `d3-turbo` | data only |
| `chat_template.jinja` | Qwen3.5 chat template (thinking switch, tools) | none; the runtime always renders with `enable_thinking=False` (`<think>\n\n</think>` prefilled) |
| `d3_format.py` | prompt text (`State: / Question: / Options:` with one code per option) and the answer-code check against the tokenizer | none (pure) |
| `d3_compose.py` | prompts for images inside questions/options, Box/track windows and box confidence | none (pure; numpy) |
| `d3_runtime.py` | the runtime `D3`: snapshot resolve, manifest check, tokenizer, `Qwen3_5Model.from_pretrained` (bf16, SDPA), `readout.safetensors` via `safetensors.load_file`, state-once forward pass, softmax over the shown codes, System One answers | `resolve_dir` calls `huggingface_hub.snapshot_download` when given a Hub id (not used: the script passes the local snapshot dir and the unit sets `HF_HUB_OFFLINE=1`). `load_image`/`load_video` fetch http(s) URLs (`urllib.request`, 30 s, 64 MiB cap) and open local paths **only in process**; the server calls them with `strict=True`, which accepts base64 data URLs only. Encoded videos are written to a `tempfile.NamedTemporaryFile` and deleted. Env reads: `D3_STATE_ONCE`, `D3_FUSED`, `D3_CUDNN_SDPA` (performance switches). `load_file_module` imports `d3_fast.py` from the snapshot dir by path (same verified package). Seeds torch with 20260919 at load. |
| `d3_fast.py` | ROCm-only fast path (HIP graphs, fused layers) | inactive on our NVIDIA GPUs (`enabled()` returns "not a ROCm GPU"); reads `D3_FAST`, `D3_GRAPH_TOKENS`, `D3_GRAPH_BUCKET`, `OMP_NUM_THREADS`, `/sys/fs/cgroup/cpu.max`; imports `d3_kernels.py` by path |
| `d3_kernels.py` | Triton kernels for the fused path (gfx942 only) | none; never imported on CUDA. Triton (via flash-linear-attention) caches compiled kernels in `~/.triton` |
| `d3_server.py` | stdlib `ThreadingHTTPServer`: `GET /health`, `GET /v1/models`, `POST /v1/systemone`; one model call at a time under a lock; optional bearer key from `DECISION_API_KEY` | binds 127.0.0.1 by default and serves without a key unless that variable is set (our script binds `BIND_HOST`, 127.0.0.1 by default); refuses fields other than `state`, `questions`, `images`, `videos`, `model` (422); never opens paths or URLs for a client |
| `modeling_d3.py` | `AutoModel` entry: if `decision_config.json` exists (`hf_hub_download` of that one file for a Hub id) loads `D3`, else the stock `Qwen3_5Model` | Hub download of `decision_config.json` only (data); `save_pretrained`/`push_to_hub` raise |
| `pipeline_d3.py` | `pipeline("decision")` wrapper around `system_one` | none |
| `d3_engine.py` | adapter for the Jev Decision Index kit (`decision_index.engines`, not installed) | not imported by the server; sets `TRITON_CACHE_AUTOTUNING=1` when imported |
| `README.md`, `requirements.txt`, `.eval_results/*.yaml`, `NOTICE` | card, pinned requirements (`transformers==5.17.0`, `flash-linear-attention==0.5.2`, torch >= 2.8, ...), self-reported scores | the card's `vllm-sr` install line (`curl ... install.sh | bash`) is not used here |

Verdict: safe to run as `tools/v3/servers/d3-turbo.sh` does (local snapshot, offline, data-URL-only
server on localhost). The only outbound network paths are Hub downloads when given a repo id
and in-process image/video URL fetching, neither reachable through the server.
