#!/usr/bin/env bash
# gemma-4-31B-it, plain OpenAI-compatible vLLM on GPU 3 (wave A), next to Qwen's TP4 shard.
#   tools/v3/servers/gemma4-31b.sh start|stop|status
# Model flags as ~/code/gemma4-31b/compose.yaml (bf16 checkpoint, online FP8 weights, FP8 KV
# cache); a smaller memory share, no image/video inputs, and its own port.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

NAME=v3-gemma4-31b
PORT=8894
URL=http://127.0.0.1:$PORT/v1/models

case ${1:-} in
  start)
    docker_up "$NAME" "$PORT" --runtime nvidia --gpus '"device=3"' --ipc host \
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
      --max-num-seqs 8 \
      --gpu-memory-utilization 0.46 \
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
