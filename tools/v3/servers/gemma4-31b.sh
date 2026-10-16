#!/usr/bin/env bash
# gemma-4-31B-it, plain OpenAI-compatible vLLM on GPU 3 (wave A, next to Qwen's TP4 shard) or
# GPU 0 (League 1 layout, next to Cygnet): GEMMA_GPU=0. gemma4-31b-replicas.sh runs one
# replica per GPU with this script (GEMMA_NAME, GEMMA_PORT, GEMMA_UTIL per replica).
#   [GEMMA_GPU=N] [GEMMA_UTIL=share] tools/v3/servers/gemma4-31b.sh start|stop|status
# Model flags as ~/code/gemma4-31b/compose.yaml (bf16 checkpoint, online FP8 weights, FP8 KV
# cache); a smaller memory share, no image/video inputs, and its own port.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

NAME=${GEMMA_NAME:-v3-gemma4-31b}
PORT=${GEMMA_PORT:-8894}
URL=http://127.0.0.1:$PORT/v1/models

case ${1:-} in
  start)
    # shellcheck disable=SC2046
    docker_up "$NAME" "$PORT" $(docker_gpu "${GEMMA_GPU:-3}") --ipc host \
      -p "127.0.0.1:$PORT:$PORT" \
      -v /home/cbasaran/code/models/gemma-4-31B-it:/model:ro \
      vllm/vllm-openai:v0.30.0 \
      /model \
      --served-model-name gemma-4-31B-it \
      --host 0.0.0.0 --port "$PORT" \
      --dtype bfloat16 \
      --quantization fp8 \
      --kv-cache-dtype fp8 \
      --max-model-len 32768 \
      --max-num-seqs 16 \
      --gpu-memory-utilization "${GEMMA_UTIL:-0.6}" \
      --limit-mm-per-prompt '{"image":0,"video":0,"audio":0}' \
      --enable-chunked-prefill \
      --enable-prefix-caching \
      --generation-config auto \
      --reasoning-parser gemma4 \
      --max-logprobs 20
    docker_wait "$NAME" "$URL" 900
    ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "$URL" ;;
  *) die "usage: $0 start|stop|status" ;;
esac
