#!/usr/bin/env bash
# Winnow-12B (League 1, from 2026-10-19): EldanRing's winnow-inference server (~/code/winnow at
# d4631fb, their patched llama.cpp, image winnow-inference:d4631fb) on the Q8_0 GGUF the release
# pins, with the configuration the author measured and the Turkish benchmark ran (8,192-token
# context, 4 decision slots, Q8_0 KV cache, selected head, optimized pipeline, text only).
# GPU 3 (WINNOW_GPU), port 8091 (on BIND_HOST).
#   [WINNOW_GPU=N] [BIND_HOST=0.0.0.0] tools/v3/servers/winnow.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

NAME=v3-winnow
PORT=8091

case ${1:-} in
  start)
    # shellcheck disable=SC2046
    docker_up "$NAME" "$PORT" $(docker_gpu "${WINNOW_GPU:-3}") -p "$BIND_HOST:$PORT:8091" \
      -v /home/cbasaran/code/winnow/models:/models:ro winnow-inference:d4631fb \
      --target q8 --text-only --context 8192 --decision-context 8192 --decision-parallel 4 \
      --chat-parallel 1 --cache q8_0 --head selected --pipeline optimized --memory auto \
      --alias winnow-12b
    docker_wait "$NAME" "http://127.0.0.1:$PORT/health" 900
    ;;
  stop) docker_down "$NAME" ;;
  status) docker_status "$NAME" "http://127.0.0.1:$PORT/health" ;;
  probe) systemone_probe "http://127.0.0.1:$PORT" winnow-12b ;;
  *) die "usage: $0 start|stop|status|probe" ;;
esac
