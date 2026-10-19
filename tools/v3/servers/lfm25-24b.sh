#!/usr/bin/env bash
# LFM2.5-24B-A2B for League 2 (off and on) on bariton, one GPU (GPU 2 by default, LFM_GPU), from
# 2026-10-19 overnight; it played through Liquid AI's API before, whose answers were read from
# the reasoning text (voided).
#   [LFM_GPU=N] [LFM_UTIL=share] tools/v3/servers/lfm25-24b.sh start|stop|status|probe
# vLLM (image vllm/vllm-openai:v0.30.0) with Liquid AI's bf16 checkpoint LiquidAI/LFM2.5-24B-A2B
# @ 1769516a (45 GiB), bf16 KV cache, memory share 0.90 (the GPU is its own), 32 sequences (16
# (on) matches at a time, with (off) never waiting behind their reasoning),
# 65,536-token context, top-20 logprobs (raw, vLLM's default), sampling defaults from
# generation_config.json (top_k 50, repetition_penalty 1.05; the league sets temperature 1).
# LFM2.5 always reasons: its chat template opens <think> for every answer and has no switch or
# effort knob, so League 2's (off) reads the letter after a prefilled "<think></think>Answer:"
# (no reasoning) and (on) after its reasoning (letter_readout "prefill"); the reasoning parser
# files the text up to </think> under reasoning. 20 stored League 2 (off) requests with that
# prefill: same top letter as Liquid's API 14/20 in bf16 (Liquid's FP8 checkpoint f54bf395
# here: 12/20; Liquid against itself 19/20; bf16 against FP8 here 15/20, most of them near-ties).
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

NAME=v3-lfm25-24b
PORT=8898
SNAPSHOT=models--LiquidAI--LFM2.5-24B-A2B/snapshots/1769516ac588c4c558089c94f27d96b0dc67b183
URL=http://127.0.0.1:$PORT/v1/models

case ${1:-} in
  start)
    # shellcheck disable=SC2046
    docker_up "$NAME" "$PORT" $(docker_gpu "${LFM_GPU:-2}") --ipc host \
      -p "$BIND_HOST:$PORT:$PORT" \
      -e HF_HUB_OFFLINE=1 \
      -v "$HF_HUB:/hub:ro" \
      vllm/vllm-openai:v0.30.0 \
      "/hub/$SNAPSHOT" \
      --served-model-name lfm2.5-24b-a2b \
      --host 0.0.0.0 --port "$PORT" \
      --dtype bfloat16 \
      --gpu-memory-utilization "${LFM_UTIL:-0.90}" \
      --max-model-len 65536 \
      --max-num-seqs 32 \
      --enable-chunked-prefill \
      --enable-prefix-caching \
      --generation-config auto \
      --reasoning-parser deepseek_r1 \
      --max-logprobs 20
    docker_wait "$NAME" "$URL" 1200
    ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "$URL" ;;
  probe) python3 "$DIR/probe_chat.py" "http://127.0.0.1:$PORT/v1" lfm2.5-24b-a2b ;;
  *) die "usage: $0 start|stop|status|probe" ;;
esac
