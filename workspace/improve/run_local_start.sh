#!/usr/bin/env bash
# "Did they improve?" Phase 2, local lane: starts the Xid/AER watcher for the lane's GPU and the lane itself as the
# systemd user units improve-xid-watch and improve-local (transient, so a reboot loses them: run this again). One GPU,
# given by UUID (default GPU-1115ade0, Main 2026-11-09); models Gemma 4 31B (on), Qwen3.8-27B (on), LFM2.5-24B-A2B (on),
# each with its league server script; pinned runner binary jevgammon-1270c04.
#   workspace/improve/run_local_start.sh [GPU-UUID]
set -euo pipefail
cd "$(dirname "$0")/../.."
UUID=${1:-GPU-1115ade0-3068-1856-5889-5855079d97f7}
BIN=$PWD/target/improve-bin/jevgammon-1270c04
[[ -x "$BIN" ]] || { echo "missing pinned binary $BIN" >&2; exit 1; }
for u in improve-local improve-xid-watch; do
  if systemctl --user is-active -q $u; then echo "$u is already running" >&2; exit 1; fi
  systemctl --user reset-failed $u 2>/dev/null || true
done
systemd-run --user --unit improve-xid-watch --description "Did they improve? Xid/PCIe watch ($UUID)" \
  "$PWD/workspace/improve/xid_watch.sh" "$UUID"
systemd-run --user --unit improve-local --description "Did they improve? local lane ($UUID)" \
  --setenv=PATH=/usr/games:/usr/local/bin:/usr/bin:/bin --setenv=IMPROVE_BIN="$BIN" \
  --property=WorkingDirectory="$PWD" \
  workspace/improve/run_local.sh "$UUID" gemma-4-31b-on qwen3.8-27b-on lfm2.5-24b-a2b-on
