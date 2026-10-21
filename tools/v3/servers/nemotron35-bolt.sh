#!/usr/bin/env bash
# NVIDIA Nemotron 3.5 Bolt 74B-A9B (Mamba-2/attention hybrid LatentMoE) for the Part A smoke test
# (workspace/backgammon-site-brief.md), thinking off and on from one server.
#   NEMOTRON_GPUS=N|N,M [NEMOTRON_CHECKPOINT=24gb|bf16] [NEMOTRON_UTIL=share] [NEMOTRON_SPEC=0] tools/v3/servers/nemotron35-bolt.sh fetch|start|stop|status|probe
# NEMOTRON_GPUS is required. NEMOTRON_CHECKPOINT picks the checkpoint (default: 24gb with one GPU,
# bf16 with two):
#   one GPU  -> nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB @ cf2effc5, NVIDIA's inference build
#               (routed experts IQ2_XXS 2.06 bits with quantization-aware distillation, 113 layers
#               Q8_0, 80 W4A16 NVFP4; 24.1 GB), with its LiLiCorr DFlash drafter
#               (…-24GB-LiLiCorr @ 449d2414, NVFP4, 7 speculative tokens; NEMOTRON_SPEC=0 drops it),
#               b12x linear/MoE kernels (SM120), FP8 KV cache, bf16 Mamba states, as in NVIDIA's
#               recipe; memory share 0.50 by default (about 48 GiB; fits next to other work).
#   two GPUs -> nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16 @ 56702103 (149.8 GB of bf16 weights),
#               TP2 with NCCL_P2P_DISABLE=1 (direct GPU-to-GPU copies arrive corrupted here),
#               bf16 KV cache, fp32 Mamba states, no drafter (NVIDIA's BF16 recipe has none);
#               memory share 0.92 of each GPU by default. Player configs:
#               leagues/smoke-parta-nemotron.json (24gb), leagues/smoke-parta-nemotron-bf16.json (bf16).
# Image: vllm/vllm-openai:nightly-77154ca6 (the version both model cards require; v0.30.0 is
# older) plus b12x 1.5.1 (vllm[b12x]) and `vllm download-kernels`, built once into
# v3-vllm-nemotron35:77154ca6 by `fetch`. Model Runner V2 (VLLM_USE_V2_MODEL_RUNNER=1, LiLiCorr
# needs it). 65,536-token context, 16 sequences, text only, top-20 logprobs (raw), sampling
# defaults from generation_config.json (top_p 0.95; the runner sets temperature 1).
# Thinking is switched per request with chat_template_kwargs.enable_thinking (template default
# true; off ends the prompt with <think></think>); NVIDIA's ultra_v3 reasoning parser (shipped in
# the checkpoint, a deepseek_r1 subclass) files the reasoning under reasoning.
# `fetch` downloads the pinned checkpoint(s) at nice 19 / idle I/O and builds the image; `start`
# runs it first when the checkpoint or image is missing.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

NAME=v3-nemotron35-bolt
PORT=8893
SERVED=nemotron-3.5-bolt
URL=http://127.0.0.1:$PORT/v1/models
BASE_IMAGE=vllm/vllm-openai:nightly-77154ca6116ae34cbfe314beef1016bde9b63989
IMAGE=v3-vllm-nemotron35:77154ca6
B12X=1.5.1

REPO_24GB=nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB
REV_24GB=cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f
REPO_DRAFT=nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-LiLiCorr
REV_DRAFT=449d24140160b8e51871bfc0f0a7338abf640aa1
REPO_BF16=nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16
REV_BF16=567021037ff88364143e24ea05e6abd0f72086ff

snapshot() { echo "models--${1//\//--}/snapshots/$2"; }

gpus() {
  [[ -n ${NEMOTRON_GPUS:-} ]] || die "set NEMOTRON_GPUS (one GPU: 24GB checkpoint; two, e.g. 1,2: BF16 TP2)"
  local list=${NEMOTRON_GPUS// /,}
  IFS=, read -ra GPU_LIST <<<"$list"
  case ${NEMOTRON_CHECKPOINT:-} in
    '') case ${#GPU_LIST[@]} in 1) VARIANT=24gb ;; 2) VARIANT=bf16 ;; *) VARIANT=? ;; esac ;;
    24gb | bf16) VARIANT=$NEMOTRON_CHECKPOINT ;;
    *) die "NEMOTRON_CHECKPOINT: 24gb or bf16, got '$NEMOTRON_CHECKPOINT'" ;;
  esac
  [[ $VARIANT == 24gb && ${#GPU_LIST[@]} == 1 ]] || [[ $VARIANT == bf16 && ${#GPU_LIST[@]} == 2 ]] \
    || die "NEMOTRON_GPUS: the 24gb checkpoint takes one GPU, bf16 two (TP2); got '$NEMOTRON_GPUS' for ${VARIANT}"
  GPU_DEVICES=$list
}

download() { nice -n 19 ionice -c3 hf download "$1" --revision "$2" >/dev/null; echo "$1 @ ${2:0:8}: downloaded"; }

fetch() {
  if [[ $VARIANT == 24gb ]]; then
    download "$REPO_24GB" "$REV_24GB"
    [[ ${NEMOTRON_SPEC:-1} == 0 ]] || download "$REPO_DRAFT" "$REV_DRAFT"
  else
    download "$REPO_BF16" "$REV_BF16"
  fi
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    # download-kernels only installs FlashInfer's precompiled kernels (faster start-up); without
    # them FlashInfer compiles at start.
    docker build -t "$IMAGE" - <<EOF
FROM $BASE_IMAGE
RUN pip install b12x==$B12X && (vllm download-kernels || echo 'vllm download-kernels failed: FlashInfer compiles at start')
EOF
    echo "$IMAGE: built"
  fi
}

start() {
  local snap args
  if [[ $VARIANT == 24gb ]]; then
    snap=$(snapshot "$REPO_24GB" "$REV_24GB")
  else
    snap=$(snapshot "$REPO_BF16" "$REV_BF16")
  fi
  if [[ ! -f $HF_HUB/$snap/model.safetensors.index.json ]] \
    || { [[ $VARIANT == 24gb && ${NEMOTRON_SPEC:-1} != 0 ]] && [[ ! -f $HF_HUB/$(snapshot "$REPO_DRAFT" "$REV_DRAFT")/model.safetensors ]]; } \
    || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    fetch
  fi
  args=(
    "/hub/$snap"
    --served-model-name "$SERVED"
    --host 0.0.0.0 --port "$PORT"
    --trust-remote-code
    --max-model-len 65536
    --max-num-seqs 16
    --limit-mm-per-prompt '{"image":0,"video":0}'
    --enable-chunked-prefill
    --enable-prefix-caching
    --attention-backend FLASHINFER
    --mamba-backend flashinfer
    --mamba-cache-mode align
    --generation-config auto
    --reasoning-parser-plugin "/hub/$snap/ultra_v3_reasoning_parser.py"
    --reasoning-parser ultra_v3
    --max-logprobs 20
  )
  if [[ $VARIANT == 24gb ]]; then
    args+=(
      --gpu-memory-utilization "${NEMOTRON_UTIL:-0.50}"
      --kv-cache-dtype fp8
      --linear-backend b12x
      --moe-backend b12x
      --mamba-ssm-cache-dtype bfloat16
      --mamba-cache-dtype bfloat16
    )
    [[ ${NEMOTRON_SPEC:-1} == 0 ]] || args+=(
      --speculative-config "{\"method\":\"dflash\",\"model\":\"/hub/$(snapshot "$REPO_DRAFT" "$REV_DRAFT")\",\"num_speculative_tokens\":7,\"rejection_sample_method\":\"standard\",\"attention_backend\":\"FLASHINFER\",\"draft_load_config\":{\"load_format\":\"auto\"}}"
    )
  else
    args+=(--tensor-parallel-size 2 --gpu-memory-utilization "${NEMOTRON_UTIL:-0.92}")
  fi
  # shellcheck disable=SC2046
  docker_up "$NAME" "$PORT" $(docker_gpu "$GPU_DEVICES") --ipc host \
    -p "$BIND_HOST:$PORT:$PORT" \
    -e HF_HUB_OFFLINE=1 -e VLLM_USE_V2_MODEL_RUNNER=1 -e NCCL_P2P_DISABLE=1 \
    -v "$HF_HUB:/hub:ro" \
    "$IMAGE" \
    "${args[@]}"
  docker_wait "$NAME" "$URL" 1800
}

case ${1:-} in
  fetch) gpus; fetch ;;
  start) gpus; start ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "$URL" ;;
  probe) python3 "$DIR/probe_chat.py" "http://127.0.0.1:$PORT/v1" "$SERVED" ;;
  *) die "usage: NEMOTRON_GPUS=N|N,M $0 fetch|start|stop|status|probe" ;;
esac
