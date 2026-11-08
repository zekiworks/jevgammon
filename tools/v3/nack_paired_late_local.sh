#!/usr/bin/env bash
# Nackgammon paired test, the local late entries (Method §10.14(i)), one at a time on ONE GPU named by UUID.
# Waits until REAX's league container (reax13-late) is gone and the card has room, then per setup: start its server
# (the league launchers), run tools/v3/nack_paired_late.sh, stop the server. Never index 3 (GPU-e4f2a538).
# systemd launchers take the UUID (CUDA_VISIBLE_DEVICES). Docker here cannot resolve UUIDs as CDI devices, so the
# Base Labs containers get the index that nvidia-smi maps to the UUID right before the start, and the container's
# own nvidia-smi must report that UUID, else the server is stopped and the setup skipped.
#   NACK_GPU=GPU-xxxx tools/v3/nack_paired_late_local.sh [SETUP ...] >> smoke/nack-paired-late-local.log 2>&1
set -u
G=${NACK_GPU:?set NACK_GPU to a GPU UUID}
[[ $G == GPU-* ]] || { echo "NACK_GPU must be a UUID"; exit 1; }
[[ $G == GPU-e4f2a538* ]] && { echo "refusing GPU-e4f2a538 (index 3)"; exit 1; }
cd /home/cbasaran/code/jevgammon
free_mib() { nvidia-smi --id="$G" --query-gpu=memory.free --format=csv,noheader,nounits | tr -d ' '; }
gpu_index() { nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -F', ' -v u="$G" '$2 == u {print $1}'; }
while docker ps --format '{{.Names}}' | grep -qx reax13-late || (( $(free_mib) < 90000 )); do
  echo "$(date -u +%FT%TZ) waiting: reax13-late up or $(free_mib) MiB free"; sleep 120
done
baselabs_start() {  # elephant|mammoth CONTAINER
  local i; i=$(gpu_index)
  [[ -n $i && $i != 3 ]] || { echo "UUID $G maps to index '${i}'; not starting"; return 1; }
  echo "host: index $i = $G"
  ELEPHANT_GPU=$i MAMMOTH_GPU=$i workspace/late3/baselabs.sh "$1" start || return 1
  local seen; seen=$(docker exec "$2" nvidia-smi --query-gpu=uuid --format=csv,noheader 2>&1)
  echo "container $2 sees: $seen"
  [[ $seen == "$G" ]]
}
run() {  # NAME START STOP
  echo "$(date -u +%FT%TZ) $1: starting server on $G ($(free_mib) MiB free)"
  if eval "$2"; then
    tools/v3/nack_paired_late.sh "$1"
  else
    echo "$(date -u +%FT%TZ) $1: server failed to start or is on the wrong GPU; skipped"
  fi
  eval "$3"
  echo "$(date -u +%FT%TZ) $1: server stopped ($(free_mib) MiB free)"
}
want() { (( ${#SETUPS[@]} == 0 )) || printf '%s\n' "${SETUPS[@]}" | grep -qxF "$1"; }
SETUPS=("$@")
want "Base Labs Elephant-1" && run "Base Labs Elephant-1" "baselabs_start elephant v3-baselabs-elephant" \
    "workspace/late3/baselabs.sh elephant stop"
want "Base Labs Mammoth-1" && run "Base Labs Mammoth-1" "baselabs_start mammoth v3-baselabs-mammoth" \
    "workspace/late3/baselabs.sh mammoth stop"
want "Drex Max v1" && run "Drex Max v1" "DREX_MAX_GPU=$G workspace/drex/drexmax.sh start" \
    "DREX_MAX_GPU=$G workspace/drex/drexmax.sh stop"
want "Drex 2.0 (local)" && run "Drex 2.0 (local)" "DREX_V2_GPU=$G workspace/drex/drexv2.sh start" \
    "DREX_V2_GPU=$G workspace/drex/drexv2.sh stop"
echo "$(date -u +%FT%TZ) local late entries done; GPU $G free of us ($(free_mib) MiB free)"
