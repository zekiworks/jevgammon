#!/usr/bin/env bash
# Cygnet (wave B): frozen google/gemma-4-12B-it on vLLM (port 8892, GPU 0) behind Cygnet's
# decision server ~/code/cygnet/shim/decision_server.py (port 18093), as in v1.
#   tools/v3/servers/cygnet.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

NAME=v3-cygnet-vllm
VLLM_PORT=8892
UNIT=v3-cygnet
PORT=18093

case ${1:-} in
  start)
    docker_up "$NAME" "$VLLM_PORT" --runtime nvidia --gpus '"device=0"' --ipc host --network host \
      -v "$HF_HUB:/root/.cache/huggingface/hub:ro" -e HF_HUB_OFFLINE=1 \
      --entrypoint vllm vllm/vllm-openai:v0.30.0 \
      serve google/gemma-4-12B-it --revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 \
      --served-model-name cygnet --host 127.0.0.1 --port "$VLLM_PORT" \
      --max-model-len 16384 --gpu-memory-utilization 0.45
    docker_wait "$NAME" "http://127.0.0.1:$VLLM_PORT/v1/models" 900
    unit_up "$UNIT" "$PORT" /home/cbasaran/code/cygnet \
      -E "SHIM_VLLM=http://127.0.0.1:$VLLM_PORT/v1/chat/completions" -E SHIM_MODEL=cygnet \
      -E SHIM_TEMPERATURE=3.4 -E "CYGNET_PORT=$PORT" \
      -- /usr/bin/python3 shim/decision_server.py
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/v1/models" 60
    ;;
  stop)
    unit_down "$UNIT"
    docker_down "$NAME"
    ;;
  status)
    docker_status "$NAME" "http://127.0.0.1:$VLLM_PORT/v1/models"
    unit_status "$UNIT" "http://127.0.0.1:$PORT/v1/models"
    ;;
  *) die "usage: $0 start|stop|status" ;;
esac
