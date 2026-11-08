#!/usr/bin/env bash
# Watches the kernel log while the local lane runs (plan §10) and stops the lane only for errors of OUR GPU:
#   - NVIDIA Xid lines naming our GPU's bus (PCI:0000:e1:00), or "fallen off the bus" for it;
#   - AER/PCIe errors reported for our root port (0000:e0:01.1) or our device (0000:e1:00.x) that are
#     Uncorrectable (Non-Fatal or Fatal);
# Correctable AER errors on our port or device are logged and the lane continues. Every other GPU/PCIe/AER line
# (other GPUs, other ports) is logged only. Topology: /sys/bus/pci/devices/0000:e1:00.0 ->
# pci0000:e0/0000:e0:01.1/0000:e1:00.0 (GPU index 3, GPU-e4f2a538-a3dc-e777-a1b6-e083f08514aa).
#   systemd-run --user --unit improve-xid-watch workspace/improve/xid_watch.sh
set -uo pipefail
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
OURS='0000:e0:01\.1|0000:e1:00\.[0-9]|PCI:0000:e1:00'
# XID_DRY=1: read lines from stdin and only print the decisions (a check of the rules, nothing is stopped).
source_lines() { if [[ "${XID_DRY:-}" == 1 ]]; then cat; else journalctl -k -f -n0 --no-pager; fi; }
[[ "${XID_DRY:-}" == 1 ]] && RUNS=$(mktemp -d)
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
