#!/usr/bin/env bash
# Fastino GLiDE v1.2 (League 1 late joiner, 2026-10-22): the HTTP server the Hugging Face repo
# fastino/GLiDE ships (glide/server.py, System One `POST /v1/systemone`, `GET /health`), run from
# the pinned snapshot in ~/.cache/huggingface/hub with the repo's own `glide` package: bf16, PyTorch
# SDPA, flash-linear-attention kernels. Served model name glide-v1.2 (GLIDE_MODEL_NAME; the
# request's model field is ignored). Port 18101 on BIND_HOST, unit v3-glide-v12.
# GLIDE_GPU is required (no default: our GPUs are shared). GLIDE_MAX_BATCH=1, so an answer never
# depends on other traffic (the card: batching moves probabilities by up to 0.039).
#
# Python: ~/code/glide/.venv, built by `setup` from the snapshot's requirements.txt (Python 3.12,
# torch 2.14.0, transformers 5.17.0, flash-linear-attention 0.5.2). Triton's compiled kernels and
# autotuning results persist in ~/code/glide/triton-cache (TRITON_CACHE_DIR).
#
#   tools/v3/servers/glide-v12.sh download                 # 52 GB, nice/ionice; needs HF_TOKEN
#   tools/v3/servers/glide-v12.sh setup                    # the venv, once
#   GLIDE_GPU=N [BIND_HOST=0.0.0.0] tools/v3/servers/glide-v12.sh start
#   tools/v3/servers/glide-v12.sh stop|status|probe
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

REPO=fastino/GLiDE
REVISION=a7e45896be7c96ba3354891da790c5ec99c30b6c
SNAPSHOT=$HF_HUB/models--fastino--GLiDE/snapshots/$REVISION
UNIT=v3-glide-v12
PORT=18101
MODEL=glide-v1.2
DIR=/home/cbasaran/code/glide
VENV=$DIR/.venv
# 52.2 GB of bf16 weights; the card measures a 60.2 GB peak for a 39k-token question.
MIN_FREE_MIB=${GLIDE_MIN_FREE_MIB:-62000}

case ${1:-} in
  download)
    # Everything but the model card's banner.
    nice -n 19 ionice -c3 uv run --no-project --python 3.12 --with huggingface_hub==1.33.0 python -c '
import sys
from huggingface_hub import snapshot_download
print(snapshot_download(sys.argv[1], revision=sys.argv[2], ignore_patterns=["assets/*"]))
' "$REPO" "$REVISION"
    ;;
  setup)
    [[ -f $SNAPSHOT/requirements.txt ]] || die "run '$0 download' first"
    mkdir -p "$DIR/triton-cache"
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -r "$SNAPSHOT/requirements.txt"
    ;;
  start)
    [[ -n ${GLIDE_GPU:-} ]] || die "set GLIDE_GPU to the GPU to load GLiDE on (needs ${MIN_FREE_MIB} MiB free)"
    [[ -f $SNAPSHOT/glide/server.py ]] || die "snapshot $REVISION missing: run '$0 download' first"
    [[ -x $VENV/bin/python ]] || die "run '$0 setup' first"
    free=$(nvidia-smi -i "$GLIDE_GPU" --query-gpu=memory.free --format=csv,noheader,nounits)
    (( free >= MIN_FREE_MIB )) || die "GPU $GLIDE_GPU has $free MiB free, GLiDE needs $MIN_FREE_MIB (GLIDE_MIN_FREE_MIB)"
    unit_up "$UNIT" "$PORT" "$SNAPSHOT" -E "CUDA_VISIBLE_DEVICES=$GLIDE_GPU" \
      -E "GLIDE_MODEL=$SNAPSHOT" -E "GLIDE_MODEL_NAME=$MODEL" -E GLIDE_DEVICE=cuda:0 \
      -E GLIDE_MAX_BATCH=1 -E "TRITON_CACHE_DIR=$DIR/triton-cache" -E "PYTHONPATH=$SNAPSHOT" \
      -- "$VENV/bin/python" -m uvicorn glide.server:app --host "$BIND_HOST" --port "$PORT" --workers 1
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/health" 900
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "http://127.0.0.1:$PORT/health" ;;
  probe) systemone_probe "http://127.0.0.1:$PORT" "$MODEL" ;;
  *) die "usage: [GLIDE_GPU=N] $0 download|setup|start|stop|status|probe" ;;
esac
