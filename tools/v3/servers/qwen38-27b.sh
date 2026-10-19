#!/usr/bin/env bash
# Qwen3.8-27B for League 2 (off and on) on bariton, one GPU (GPU 1 by default, QWEN27_GPU), from
# 2026-10-19 overnight (spark2, where spark2-qwen27b.sh was to serve it, hung).
#   [QWEN27_GPU=N] [QWEN27_UTIL=share] tools/v3/servers/qwen38-27b.sh start|stop|status|probe
# vLLM (image vllm/vllm-openai:v0.30.0, as Gemma) with the bf16 checkpoint Qwen/Qwen3.8-27B
# @ 1d4bf0f2 served in fp16, as League 2 had it on Cerebras (fp16 weights and KV cache, 16 bits
# like bf16 with three more mantissa bits; 20 stored League 2 (off) requests replayed: same
# letter 18/20 in fp16, 17/20 in bf16, the others near-ties either way), the checkpoint's fp32
# GDN states; no speculative decoding; memory share 0.90 (the GPU is its own), 32 requests at
# once (16 (on) matches, with (off) never waiting behind their reasoning), 65,536-token context,
# text only; top-20 logprobs (raw, vLLM's default); sampling
# defaults from generation_config.json (top_k 20, top_p 0.95; the league sets temperature 1).
# Thinking is switched per request with chat_template_kwargs.enable_thinking; --reasoning-parser
# qwen3 files the reasoning under reasoning.
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

NAME=v3-qwen38-27b
PORT=8897
SNAPSHOT=models--Qwen--Qwen3.8-27B/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0
URL=http://127.0.0.1:$PORT/v1/models

case ${1:-} in
  start)
    # shellcheck disable=SC2046
    docker_up "$NAME" "$PORT" $(docker_gpu "${QWEN27_GPU:-1}") --ipc host \
      -p "$BIND_HOST:$PORT:$PORT" \
      -e HF_HUB_OFFLINE=1 \
      -v "$HF_HUB:/hub:ro" \
      vllm/vllm-openai:v0.30.0 \
      "/hub/$SNAPSHOT" \
      --served-model-name qwen3.8-27b \
      --host 0.0.0.0 --port "$PORT" \
      --dtype float16 \
      --max-model-len 65536 \
      --max-num-seqs 32 \
      --gpu-memory-utilization "${QWEN27_UTIL:-0.90}" \
      --limit-mm-per-prompt '{"image":0,"video":0}' \
      --enable-chunked-prefill \
      --enable-prefix-caching \
      --generation-config auto \
      --reasoning-parser qwen3 \
      --max-logprobs 20
    docker_wait "$NAME" "$URL" 1200
    ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "$URL" ;;
  probe) python3 "$DIR/probe_chat.py" "http://127.0.0.1:$PORT/v1" qwen3.8-27b ;;
  *) die "usage: $0 start|stop|status|probe" ;;
esac
