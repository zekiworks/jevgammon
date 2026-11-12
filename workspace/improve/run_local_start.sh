#!/usr/bin/env bash
# "Did they improve?" Phase 2, a local lane: starts its Xid/AER watcher and the lane as systemd user units
# (transient, so a reboot loses them: run this again). One GPU by UUID; the lane's models are claimed for it
# (runs/<model>/lane.json), so no other lane runs them. Pinned runner binary jevgammon-e417a0c (1270c04 + the
# 200-error-reply fix + native_finish_reason, QC 2026-11-12; jevgammon-1270c04, then jevgammon-8b6f9a1 before).
#   workspace/improve/run_local_start.sh GPU-UUID LANE-UNIT WATCH-UNIT MODEL...
#   e.g. run_local_start.sh GPU-1115ade0-3068-1856-5889-5855079d97f7 improve-local improve-xid-watch gemma-4-31b-on
#        run_local_start.sh GPU-e4f2a538-a3dc-e777-a1b6-e083f08514aa improve-local3 improve-xid-watch3 qwen3.8-27b-on lfm2.5-24b-a2b-on
set -euo pipefail
cd "$(dirname "$0")/../.."
UUID=${1:?GPU UUID}; LANE=${2:?lane unit}; WATCH=${3:?watcher unit}; shift 3
[[ $# -gt 0 ]] || { echo "no models" >&2; exit 1; }
BIN=$PWD/target/improve-bin/jevgammon-e417a0c
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
[[ -x "$BIN" ]] || { echo "missing pinned binary $BIN" >&2; exit 1; }
container() { case $1 in gemma-4-31b-on) echo v3-gemma4-31b ;; qwen3.8-27b-on) echo v3-qwen38-27b ;; lfm2.5-24b-a2b-on) echo v3-lfm25-24b ;;
  gemma-4-e4b-on|gemma-4-e2b-on|gemma-4-12b-on|minicpm5-2b-on|lfm2.5-2.6b-on|lfm2.5-8b-a1b-on)
    k=${1%-on}; [[ $k == gemma-* ]] && k=$k-it; echo "logic-small-$k" ;;
  esac; }
containers=()
for m in "$@"; do
  claim=$RUNS/$m/lane.json
  if [[ -f $claim ]] && ! grep -q "\"$LANE\"" "$claim"; then echo "$m is claimed by another lane: $(cat "$claim")" >&2; exit 1; fi
  containers+=("$(container "$m")")
done
for u in "$LANE" "$WATCH"; do
  if systemctl --user is-active -q "$u"; then echo "$u is already running" >&2; exit 1; fi
  systemctl --user reset-failed "$u" 2>/dev/null || true
done
for m in "$@"; do
  mkdir -p "$RUNS/$m"
  printf '{"lane": "%s", "gpu": "%s", "at": "%s"}\n' "$LANE" "$UUID" "$(date -u +%FT%TZ)" > "$RUNS/$m/lane.json"
done
systemd-run --user --unit "$WATCH" --description "Did they improve? Xid/PCIe watch ($LANE, $UUID)" \
  "$PWD/workspace/improve/xid_watch.sh" "$UUID" "$LANE" "${containers[@]}"
systemd-run --user --unit "$LANE" --description "Did they improve? local lane $LANE ($UUID)" \
  --setenv=PATH=/usr/games:/usr/local/bin:/usr/bin:/bin --setenv=IMPROVE_BIN="$BIN" --setenv=IMPROVE_LANE="$LANE" \
  --property=WorkingDirectory="$PWD" \
  workspace/improve/run_local.sh "$UUID" "$@"
