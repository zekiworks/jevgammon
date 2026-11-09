#!/usr/bin/env bash
# "Did they improve?" Phase 2, local lane (plan §10): one model at a time on ONE GPU, given by UUID (Can #3121; since
# 2026-11-09 GPU-1115ade0, Main, after GPU-e4f2a538's hardware failure),
# each with its league server script and arguments (only the GPU differs). Before each start: the UUID's index on
# the host and the GPU the container sees are checked; the container's model path and image are recorded. The
# experiment's run then starts with the server's address; afterwards the server is stopped. A stop (exit 2) moves
# on to the next model; a pause (3) or an error stops the lane (the server is stopped).
#   systemd-run --user --unit improve-local workspace/improve/run_local.sh GPU-UUID gemma-4-31b-on qwen3.8-27b-on ...
set -uo pipefail
cd "$(dirname "$0")/../.."
UUID=$1; shift
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
SERVERS=/home/cbasaran/code/jevgammon/tools/v3/servers
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
server() {  # model key -> "script name port gpu-variable"
  case $1 in
    gemma-4-31b-on) echo "gemma4-31b.sh v3-gemma4-31b 8894 GEMMA_GPU" ;;
    qwen3.8-27b-on) echo "qwen38-27b.sh v3-qwen38-27b 8897 QWEN27_GPU" ;;
    lfm2.5-24b-a2b-on) echo "lfm25-24b.sh v3-lfm25-24b 8898 LFM_GPU" ;;
    *) return 1 ;;
  esac
}
echo "local lane start $(date -u +%FT%TZ) on $UUID: $*"
for model in "$@"; do
  read -r script name port var < <(server "$model") || { echo "unknown local model $model"; exit 1; }
  index=$(nvidia-smi -i "$UUID" --query-gpu=index,uuid --format=csv,noheader) || { echo "no GPU $UUID"; exit 1; }
  echo "== $model: host GPU $index"
  case $UUID in GPU-e4f2a538*) echo "refused: GPU-e4f2a538 is off limits (hardware failure 2026-11-08)"; exit 1 ;; esac
  # Docker's CDI names GPUs by index here, not by UUID: the index the host gives this UUID now, and the
  # container must then report this UUID (checked below).
  env "$var=${index%%,*}" "$SERVERS/$script" start || { echo "$model: server did not start"; exit 1; }
  seen=$(docker exec "$name" nvidia-smi --query-gpu=uuid --format=csv,noheader | tr -d ' ')
  if [[ "$seen" != "$UUID" ]]; then
    echo "$model: the container sees '$seen', not $UUID: stopped"; "$SERVERS/$script" stop; exit 1
  fi
  mkdir -p "$RUNS/$model"
  docker inspect "$name" --format '{"image": "{{.Config.Image}}", "image_id": "{{.Image}}", "args": {{json .Args}}, "gpus": {{json .HostConfig.DeviceRequests}}}' \
    > "$RUNS/$model/server.json"
  echo "== $model start $(date -u +%FT%TZ) (container sees $seen)"
  "$PY" workspace/improve/improve.py run --model "$model" --base-url "http://127.0.0.1:$port/v1"
  code=$?
  echo "== $model exit $code $(date -u +%FT%TZ)"
  "$PY" workspace/improve/improve.py status --model "$model"
  "$SERVERS/$script" stop
  case $code in
    0|2) continue ;;
    3) echo "local lane paused at $model"; exit 3 ;;
    *) echo "local lane stopped: $model failed"; exit "$code" ;;
  esac
done
echo "local lane done $(date -u +%FT%TZ)"
