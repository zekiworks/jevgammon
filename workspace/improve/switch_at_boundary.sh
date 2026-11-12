#!/usr/bin/env bash
# Switch a running lane to another pinned runner binary at its model's next step boundary, never inside a step
# (QC 2026-11-12). FROM and TO are pinned copies under target/improve-bin (environment SWITCH_FROM, SWITCH_TO, e.g.
# jevgammon-8b6f9a1 and jevgammon-e417a0c); SWITCH_WHY is the logged reason. A running improve.py keeps the binary it
# was started with (IMPROVE_BIN is read once), so the switch is a pause and a restart:
#  1. wait until MODEL's STEP is complete (runs/MODEL/STEP/aggregate.json: games, lessons and the full T10 done);
#  2. write the operator hold (runs/MODEL/hold.json). improve.py checks it before it dispatches anything of the next
#     step (held() before the next test is asked or the next match starts), pauses (exit 3) and the lane exits.
#     If the hold lands after that check (a race of a few seconds), the next step runs whole on the old binary and
#     the pause comes before the step after it: still at a step boundary;
#  3. when LANE has exited paused by this hold: remove the hold, log a binary_switch event in MODEL's run log, stop
#     the units in STOP_UNITS (e.g. a local lane's Xid watcher, restarted by run_local_start.sh), and restart the lane
#     with its committed start command (the remaining arguments), which must pin TO. Anything else (stopped,
#     failed): nothing is restarted and the hold stays, for a look.
#   systemd-run --user --unit improve-switch-xai --property=WorkingDirectory=$PWD \
#     --setenv=SWITCH_FROM=jevgammon-1270c04 --setenv=SWITCH_TO=jevgammon-e417a0c --setenv=SWITCH_WHY=... \
#     workspace/improve/switch_at_boundary.sh grok-4.7-on S4 improve-subs-xai workspace/improve/run_lane.sh improve-subs-xai grok-4.7-on
set -uo pipefail
cd "$(dirname "$0")/../.."
MODEL=${1:?model key}; STEP=${2:?step to finish first}; LANE=${3:?lane unit}; shift 3
[[ $# -gt 0 ]] || { echo "no restart command" >&2; exit 1; }
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
D=$RUNS/$MODEL
FROM=$PWD/target/improve-bin/${SWITCH_FROM:?SWITCH_FROM: the pinned binary the lane runs now}
TO=$PWD/target/improve-bin/${SWITCH_TO:?SWITCH_TO: the pinned binary to switch to}
WHY=${SWITCH_WHY:?SWITCH_WHY: the reason logged with the switch}
[[ -x $FROM && -x $TO ]] || { echo "missing pinned binary $FROM or $TO" >&2; exit 1; }
REASON="binary switch at the step boundary after $STEP: ${SWITCH_FROM} -> ${SWITCH_TO} (QC 2026-11-12)"
[[ -e $D/hold.json ]] && { echo "$MODEL already has a hold: $(cat "$D/hold.json")" >&2; exit 1; }
echo "$(date -u +%FT%TZ) waiting for $D/$STEP/aggregate.json"
until [[ -e $D/$STEP/aggregate.json ]]; do sleep 0.02; done
printf '{\n "reason": "%s",\n "at": "%s",\n "step": "%s"\n}\n' "$REASON" "$(date -u +%FT%T+00:00)" "$STEP" > "$D/hold.json.tmp"
mv "$D/hold.json.tmp" "$D/hold.json"
echo "$(date -u +%FT%TZ) $STEP complete; hold written"
while systemctl --user is-active -q "$LANE"; do sleep 5; done
if ! grep -q "binary switch at the step boundary" "$D/paused.json" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) $LANE exited, but not paused by this hold: nothing restarted, hold kept" >&2
  exit 1
fi
rm -f "$D/hold.json"
python3 - "$D/log.jsonl" "$STEP" "$FROM" "$TO" "$WHY" <<'PY'
import hashlib, json, sys
from datetime import datetime, timezone
log, step, src, dst, why = sys.argv[1:]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
with open(log, "a") as f:
    f.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec="seconds"), event="binary_switch",
                            after_step=step, **{"from": src}, from_sha256=sha(src), to=dst, to_sha256=sha(dst),
                            why=why)) + "\n")
PY
for u in ${STOP_UNITS:-}; do systemctl --user stop "$u"; done
echo "$(date -u +%FT%TZ) restarting: $*"
exec "$@"
