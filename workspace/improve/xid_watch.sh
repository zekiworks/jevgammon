#!/usr/bin/env bash
# Watches the kernel log while the local lane runs (plan §10) and stops the lane only for errors of OUR GPU, given by
# UUID (argument 1): its PCI device and root port are read from nvidia-smi and /sys at start.
#   - NVIDIA Xid lines naming our GPU's bus, or "fallen off the bus" for it;
#   - AER/PCIe errors reported for our root port or our device that are Uncorrectable (Non-Fatal or Fatal);
# Correctable AER errors on our port or device are logged and the lane continues. Every other GPU/PCIe/AER line
# (other GPUs, other ports) is logged only.
#   systemd-run --user --unit improve-xid-watch workspace/improve/xid_watch.sh GPU-UUID
set -uo pipefail
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
[[ "${XID_DRY:-}" == 1 ]] && RUNS=$(mktemp -d)
UUID=${1:?GPU UUID}
BUS=$(nvidia-smi -i "$UUID" --query-gpu=pci.bus_id --format=csv,noheader | tr 'A-F' 'a-f' | sed 's/^0000//')  # 0000:11:00.0
DEV=${BUS%.*}                                                                                  # 0000:11:00
PORT=$(basename "$(dirname "$(readlink -f "/sys/bus/pci/devices/$BUS")")")                      # 0000:10:01.1
[[ -n "$DEV" && -n "$PORT" ]] || { echo "cannot find the PCI path of $UUID" >&2; exit 1; }
OURS="${PORT//./\.}|${DEV//./\.}\.[0-9]|PCI:${DEV}"
echo "$(date -u +%FT%TZ) watching $UUID: device $BUS, root port $PORT" | tee -a "$RUNS/XID.txt"
# XID_DRY=1: read lines from stdin and only print the decisions (a check of the rules, nothing is stopped).
source_lines() { if [[ "${XID_DRY:-}" == 1 ]]; then cat; else journalctl -k -f -n0 --no-pager; fi; }
source_lines | while IFS= read -r line; do
  echo "$line" | grep -qiE 'NVRM: Xid|AER:|PCIe Bus Error|pcieport|fallen off the bus' || continue
  at=$(date -u +%FT%TZ)
  if echo "$line" | grep -qE "$OURS"; then
    if echo "$line" | grep -qiE 'NVRM: Xid|fallen off the bus|Uncorrect|Fatal'; then
      echo "$at STOP (our GPU) $line" | tee -a "$RUNS/XID.txt"
      [[ "${XID_DRY:-}" == 1 ]] && continue
      systemctl --user stop improve-local
      for c in v3-gemma4-31b v3-qwen38-27b v3-lfm25-24b; do docker stop "$c" >/dev/null 2>&1; done
      exit 0
    fi
    echo "$at LOG (our GPU, correctable: continue) $line" | tee -a "$RUNS/XID.txt"
  else
    echo "$at LOG (not our GPU) $line" | tee -a "$RUNS/XID.txt"
  fi
done
