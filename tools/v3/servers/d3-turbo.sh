#!/usr/bin/env bash
# vllm-sr/d3-turbo (Part A smoke test): the System One server its Hugging Face package ships
# (d3_server.py, standard-library HTTP; reviewed in d3-turbo-code-review.md), run from the pinned
# snapshot in ~/.cache/huggingface/hub with the package's own runtime (d3_runtime.D3): bf16
# backbone, fp32 readout, one request at a time, model field accepted and ignored. Port 18100
# on BIND_HOST, unit v3-d3-turbo. D3_GPU is required (no default: our GPUs are shared).
#
# Python: D3_PYTHON, default ~/code/pplx-decider/.venv (transformers 5.17.0, flash-linear-attention
# 0.5.2, torch 2.14.0 CUDA 13.0, as the package's requirements.txt pins; no OpenCV, which only
# video inputs need). `setup` builds a separate ~/code/d3-turbo/.venv from that requirements.txt
# instead (then D3_PYTHON=~/code/d3-turbo/.venv/bin/python).
#
#   tools/v3/servers/d3-turbo.sh download                  # 52 GB, nice/ionice; before start
#   tools/v3/servers/d3-turbo.sh setup                     # optional, see above
#   D3_GPU=N [D3_PYTHON=...] [BIND_HOST=0.0.0.0] tools/v3/servers/d3-turbo.sh start
#   tools/v3/servers/d3-turbo.sh stop|status|probe
source "$(dirname "$(readlink -f "$0")")/_lib.sh"

REPO=vllm-sr/d3-turbo
REVISION=a0f3e9e59ebd1202fe1d4de1c4c0f9a986758cbb
SNAPSHOT=$HF_HUB/models--vllm-sr--d3-turbo/snapshots/$REVISION
UNIT=v3-d3-turbo
PORT=18100
MODEL=d3-turbo
PYTHON=${D3_PYTHON:-/home/cbasaran/code/pplx-decider/.venv/bin/python}
VENV=/home/cbasaran/code/d3-turbo/.venv
# 48.6 GiB of bf16 weights plus CUDA context, warm-up and activations.
MIN_FREE_MIB=${D3_MIN_FREE_MIB:-56000}

case ${1:-} in
  download)
    # Everything but the model card's images and video (the runtime never reads assets/).
    nice -n 19 ionice -c3 "$PYTHON" -c '
import sys
from huggingface_hub import snapshot_download
print(snapshot_download(sys.argv[1], revision=sys.argv[2], ignore_patterns=["assets/*"]))
' "$REPO" "$REVISION"
    ;;
  setup)
    [[ -f $SNAPSHOT/requirements.txt ]] || die "run '$0 download' first"
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -r "$SNAPSHOT/requirements.txt"
    echo "then: D3_PYTHON=$VENV/bin/python $0 start"
    ;;
  start)
    [[ -n ${D3_GPU:-} ]] || die "set D3_GPU to the GPU to load d3-turbo on (needs ${MIN_FREE_MIB} MiB free)"
    [[ -f $SNAPSHOT/d3_server.py ]] || die "snapshot $REVISION missing: run '$0 download' first"
    free=$(nvidia-smi -i "$D3_GPU" --query-gpu=memory.free --format=csv,noheader,nounits)
    (( free >= MIN_FREE_MIB )) || die "GPU $D3_GPU has $free MiB free, d3-turbo needs $MIN_FREE_MIB (D3_MIN_FREE_MIB)"
    # The snapshot's .py files are links into blobs/; d3_server.py imports its neighbours by path.
    unit_up "$UNIT" "$PORT" "$SNAPSHOT" -E "CUDA_VISIBLE_DEVICES=$D3_GPU" \
      -- "$PYTHON" -u "$SNAPSHOT/d3_server.py" --model "$SNAPSHOT" --device cuda:0 \
      --verify fast --name "$MODEL" --host "$BIND_HOST" --port "$PORT"
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/health" 1200
    ;;
  stop) unit_down "$UNIT" ;;
  status) unit_status "$UNIT" "http://127.0.0.1:$PORT/health" ;;
  probe) systemone_probe "http://127.0.0.1:$PORT" "$MODEL" ;;
  *) die "usage: [D3_GPU=N] $0 download|setup|start|stop|status|probe" ;;
esac
