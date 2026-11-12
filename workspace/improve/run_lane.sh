#!/usr/bin/env bash
# "Did they improve?" Phase 2: starts an API/subscription lane (no local server) as the systemd user unit LANE-UNIT
# (transient, so a reboot loses it: run this again), one model at a time through run_queue.sh, with the pinned runner
# binary jevgammon-e417a0c (1270c04 + the 200-error-reply fix + native_finish_reason, QC 2026-11-12; jevgammon-1270c04,
# then jevgammon-8b6f9a1 before). The Codex lane pins its own build: IMPROVE_PIN=66bbcd6 (938c842 + the same fixes). The lane's models are claimed for
# it (runs/<model>/lane.json); improve.py refuses a model
# claimed by another lane, so a model runs in exactly one lane.
#   workspace/improve/run_lane.sh improve-subs-xai grok-4.7-on
#   workspace/improve/run_lane.sh improve-subs-claude claude-sonnet-5.5-high claude-opus-5.5-on claude-fable-5.1-on
set -euo pipefail
cd "$(dirname "$0")/../.."
LANE=${1:?lane unit}; shift
[[ $# -gt 0 ]] || { echo "no models" >&2; exit 1; }
BIN=$PWD/target/improve-bin/jevgammon-${IMPROVE_PIN:-e417a0c}
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
[[ -x "$BIN" ]] || { echo "missing pinned binary $BIN" >&2; exit 1; }
for m in "$@"; do
  claim=$RUNS/$m/lane.json
  if [[ -f $claim ]] && ! grep -q "\"$LANE\"" "$claim"; then echo "$m is claimed by another lane: $(cat "$claim")" >&2; exit 1; fi
done
if systemctl --user is-active -q "$LANE"; then echo "$LANE is already running" >&2; exit 1; fi
systemctl --user reset-failed "$LANE" 2>/dev/null || true
for m in "$@"; do
  mkdir -p "$RUNS/$m"
  printf '{"lane": "%s", "at": "%s"}\n' "$LANE" "$(date -u +%FT%TZ)" > "$RUNS/$m/lane.json"
done
systemd-run --user --unit "$LANE" --description "Did they improve? lane $LANE" \
  --setenv=PATH=/usr/games:/usr/local/bin:/usr/bin:/bin --setenv=IMPROVE_BIN="$BIN" --setenv=IMPROVE_LANE="$LANE" \
  --property=WorkingDirectory="$PWD" \
  workspace/improve/run_queue.sh "$@"
