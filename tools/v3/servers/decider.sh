#!/usr/bin/env bash
# Decider v1.1 27B (wave B): ~/code/pplx-decider/server.py on GPU 3 (DECIDER_GPU), port 18097.
# It answers one request at a time (others get 529 with Retry-After).
#   [DECIDER_GPU=N] [BIND_HOST=0.0.0.0] tools/v3/servers/decider.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

UNIT=v3-decider
PORT=18097

case ${1:-} in
  start)
    # --gpus sets CUDA_VISIBLE_DEVICES itself; the model goes on that GPU alone.
    unit_up "$UNIT" "$PORT" /home/cbasaran/code/pplx-decider \
      -- /home/cbasaran/code/pplx-decider/.venv/bin/python -u server.py --gpus "${DECIDER_GPU:-3}" \
      --host "$BIND_HOST" --port "$PORT"
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/health" 900
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "http://127.0.0.1:$PORT/health" ;;
  *) die "usage: $0 start|stop|status" ;;
esac
