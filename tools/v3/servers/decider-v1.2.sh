#!/usr/bin/env bash
# Perplexity Decider v1.2 checkpoints (League 1, from 2026-10-19), as the Turkish benchmark served
# them: pplx_decider_server.py (turkce-benchmark runner/servers at febf46c, copied to
# ~/code/pplx-decider) runs the pplx_decider package each checkpoint ships on its reference path,
# one request at a time, in .venv-v1.2 (only the checkpoint's requirements.txt, on uv's
# Python 3.12.13). The request's model field must name the loaded checkpoint.
#   flash: pplx-decider-flash-v1.2 (~/code/pplx-decider/checkpoint-flash-v1.2), port 18098
#   27b:   pplx-decider-v1.2 (Hugging Face snapshot 225c913), port 18099
# GPU 3 (DECIDER_V12_GPU), on BIND_HOST.
#   [DECIDER_V12_GPU=N] [BIND_HOST=0.0.0.0] tools/v3/servers/decider-v1.2.sh flash|27b start|stop|status|probe
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

DIR=/home/cbasaran/code/pplx-decider
case ${1:-} in
  flash) UNIT=v3-decider-flash-v12 PORT=18098 MODEL=pplx-decider-flash-v1.2
    CHECKPOINT=$DIR/checkpoint-flash-v1.2 ;;
  27b) UNIT=v3-decider-v12 PORT=18099 MODEL=pplx-decider-v1.2
    CHECKPOINT=$HF_HUB/models--perplexity-ai--pplx-decider-v1.2/snapshots/225c913ddc8761a8264f04f64548e1f97e443eb3 ;;
  *) die "usage: $0 flash|27b start|stop|status|probe" ;;
esac

case ${2:-} in
  start)
    unit_up "$UNIT" "$PORT" "$DIR" -E "CUDA_VISIBLE_DEVICES=${DECIDER_V12_GPU:-3}" \
      -- "$DIR/.venv-v1.2/bin/python" -u pplx_decider_server.py --checkpoint "$CHECKPOINT" \
      --device cuda:0 --host "$BIND_HOST" --port "$PORT"
    unit_wait_port "$UNIT" "$PORT" 900
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "port:$PORT" ;;
  probe) systemone_probe "http://127.0.0.1:$PORT" "$MODEL" ;;
  *) die "usage: $0 flash|27b start|stop|status|probe" ;;
esac
