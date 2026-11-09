#!/usr/bin/env bash
# Watches the kernel log while a local lane runs (plan §10) and stops THAT lane only for errors of its GPU, given by
# UUID (argument 1); argument 2 is the lane's unit, the rest are the lane's container names (only those are stopped).
# The GPU's PCI device and root port are read from nvidia-smi and /sys at start.
#   - NVIDIA Xid lines naming the GPU's bus, or "fallen off the bus" for it;
#   - AER/PCIe errors reported for its root port or device that are Uncorrectable (Non-Fatal or Fatal);
# Correctable AER errors on its port or device are logged and the lane continues. Every other GPU/PCIe/AER line is
# logged only.
#   systemd-run --user --unit improve-xid-watch3 workspace/improve/xid_watch.sh GPU-UUID improve-local3 v3-qwen38-27b v3-lfm25-24b
set -uo pipefail
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
[[ "${XID_DRY:-}" == 1 ]] && RUNS=$(mktemp -d)
UUID=${1:?GPU UUID}; LANE=${2:?lane unit}; shift 2; CONTAINERS=("$@")
BUS=$(nvidia-smi -i "$UUID" --query-gpu=pci.bus_id --format=csv,noheader | tr 'A-F' 'a-f' | sed 's/^0000//')
DEV=${BUS%.*}
PORT=$(basename "$(dirname "$(readlink -f "/sys/bus/pci/devices/$BUS")")")
[[ -n "$DEV" && -n "$PORT" ]] || { echo "cannot find the PCI path of $UUID" >&2; exit 1; }
OURS="${PORT//./\\.}|${DEV//./\\.}\\.[0-9]|PCI:${DEV}"
echo "$(date -u +%FT%TZ) $LANE: watching $UUID: device $BUS, root port $PORT; containers ${CONTAINERS[*]}" | tee -a "$RUNS/XID.txt"
# XID_DRY=1: read lines from stdin and only print the decisions (a check of the rules, nothing is stopped).
source_lines() { if [[ "${XID_DRY:-}" == 1 ]]; then cat; else journalctl -k -f -n0 --no-pager; fi; }
source_lines | while IFS= read -r line; do
  echo "$line" | grep -qiE 'NVRM: Xid|AER:|PCIe Bus Error|pcieport|fallen off the bus|DPC:' || continue
  at=$(date -u +%FT%TZ)
  if echo "$line" | grep -qE "$OURS"; then
    if echo "$line" | grep -qiE 'NVRM: Xid|fallen off the bus|Uncorrect|Fatal'; then
      echo "$at STOP $LANE (its GPU) $line" | tee -a "$RUNS/XID.txt"
      [[ "${XID_DRY:-}" == 1 ]] && continue
      systemctl --user stop "$LANE"
      for c in "${CONTAINERS[@]}"; do docker stop "$c" >/dev/null 2>&1; done
      exit 0
    fi
    echo "$at LOG $LANE (its GPU, correctable: continue) $line" | tee -a "$RUNS/XID.txt"
  else
    echo "$at LOG $LANE (not its GPU) $line" | tee -a "$RUNS/XID.txt"
  fi
done
