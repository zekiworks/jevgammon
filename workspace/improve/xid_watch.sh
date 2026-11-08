#!/usr/bin/env bash
# Watches the kernel log for NVIDIA Xid and PCIe/AER errors while the local lane runs (plan §10). On the first
# match it stops the lane unit and the lane's servers and records the line in runs/XID.txt.
#   systemd-run --user --unit improve-xid-watch workspace/improve/xid_watch.sh
set -uo pipefail
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
line=$(journalctl -k -f -n0 --no-pager | grep -m1 -iE 'NVRM: Xid|PCIe Bus Error|AER:|pcieport.*error|GPU has fallen off')
echo "$(date -u +%FT%TZ) $line" | tee -a "$RUNS/XID.txt"
systemctl --user stop improve-local
for c in v3-gemma4-31b v3-qwen38-27b v3-lfm25-24b; do docker stop "$c" >/dev/null 2>&1; done
