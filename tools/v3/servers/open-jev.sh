#!/usr/bin/env bash
# Open-Jev 27B v1.1 decision server (wave B): jev.server on GPU 2 (OPEN_JEV_GPU), port 8791,
# with the v1 league settings (batch 8, request-local prefix cache).
#   [OPEN_JEV_GPU=N] [BIND_HOST=0.0.0.0] tools/v3/servers/open-jev.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

UNIT=v3-open-jev
PORT=8791

case ${1:-} in
  start)
    unit_up "$UNIT" "$PORT" /home/cbasaran/code/Open-Jev -E "CUDA_VISIBLE_DEVICES=${OPEN_JEV_GPU:-2}" \
      -E TOKENIZERS_PARALLELISM=false \
      -- /home/cbasaran/code/Open-Jev/.venv/bin/python -m jev.server \
      --checkpoint /home/cbasaran/code/Open-Jev/checkpoints/open-jev-27b-v1.1/package/checkpoint \
      --device cuda:0 --max-length 4096 --batch-size 8 --prefix-cache \
      --host "$BIND_HOST" --port "$PORT"
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/health" 900
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "http://127.0.0.1:$PORT/health" ;;
  *) die "usage: $0 start|stop|status" ;;
esac
