#!/usr/bin/env bash
# Clef decision server (wave B): ~/code/clef/server.py on GPU 1 (CLEF_GPU), port 18091.
#   [CLEF_GPU=N] [BIND_HOST=0.0.0.0] tools/v3/servers/clef.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

UNIT=v3-clef
PORT=18091

case ${1:-} in
  start)
    unit_up "$UNIT" "$PORT" /home/cbasaran/code/clef -E "CUDA_VISIBLE_DEVICES=${CLEF_GPU:-1}" \
      -- /home/cbasaran/code/clef/.venv/bin/python server.py --device cuda:0 \
      --host "$BIND_HOST" --port "$PORT"
    unit_wait_port "$UNIT" "$PORT" 900
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "port:$PORT" ;;
  *) die "usage: $0 start|stop|status" ;;
esac
