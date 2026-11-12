#!/usr/bin/env bash
# "Did they improve?" decision models, local setups (Main, after Zeki #5434): one model at a time on one empty card
# GPU under the agent-bus reservation RES, strictly sequential, as the systemd user unit improve-decision-local:
#   systemd-run --user --unit=improve-decision-local --working-directory=$HOME/code/jevgammon-improve-decision \
#     -E GPU=<n> -E RES=<reservation> workspace/improve/run_decision_local.sh
# Per setup, in order (Elephant-1 worst; Decider v1.2 27B notes, worst; GLiDE v1.2 notes, worst): the arms that
# `decision.py arm-state` says have steps to run (none: no server); the card must be empty (at most EMPTY MiB in use,
# else the script refuses and exits 1, starting nothing); its pinned server is started with the league's own script
# under `agent-bus run RES`; the server's own probe must answer with the served model id (P1 is the hosted
# accounting probe and does not apply to local rows, addendum §6.1); then each arm `decision.py run` until done
# (0 done; 3 log + sleep + retry; 2 next arm; other: skip the setup); then the server is stopped. A stop or exit of
# the unit stops the server it started. It never touches the hosted unit improve-decision or its queue.
# DECISION_PY / DECISION_SLEEP / DECISION_SETUPS / DECISION_SERVERS / DECISION_BASELABS / DECISION_BUS /
# DECISION_SMI / DECISION_EMPTY_MIB / DECISION_FREE_WAIT override the script, wait, setups, server scripts, bus,
# nvidia-smi, empty threshold and the wait for the card to empty after a stop (tests only).
set -uo pipefail
cd "$(dirname "$0")/../.."
: "${GPU:?set GPU to the booked card}" "${RES:?set RES to its agent-bus reservation}"
[[ -n ${DECISION_PY:-} ]] || . "$HOME/.keys"
export IMPROVE_BIN=${IMPROVE_BIN:-$HOME/code/jevgammon-improve-decision/target/release/jevgammon-bb74f07}
export IMPROVE_LANE=decision
PY=${DECISION_PY:-workspace/improve/decision.py}
SLEEP=${DECISION_SLEEP:-300}
S=${DECISION_SERVERS:-/home/cbasaran/code/jevgammon/tools/v3/servers}
BL=${DECISION_BASELABS:-/home/cbasaran/code/jevgammon/workspace/late3/baselabs.sh}
BUS=${DECISION_BUS:-agent-bus}
SMI=${DECISION_SMI:-nvidia-smi}
EMPTY=${DECISION_EMPTY_MIB:-1024}
FREE_WAIT=${DECISION_FREE_WAIT:-180}
log() { echo "$(date -u +%FT%TZ) $*"; }
used() { "$SMI" -i "$GPU" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' '; }

# slug|arms|start (GPU in $GPU)|stop|probe|served model id
SETUPS=(
  "baselabs-elephant-1|worst|ELEPHANT_GPU=$GPU $BL elephant start|$BL elephant stop|$BL elephant probe|baselabs/elephant-1"
  "decider-v1.2-27b|notes worst|DECIDER_V12_GPU=$GPU $S/decider-v1.2.sh 27b start|$S/decider-v1.2.sh 27b stop|$S/decider-v1.2.sh 27b probe|pplx-decider-v1.2"
  "glide-v1.2-local|notes worst|GLIDE_GPU=$GPU $S/glide-v12.sh start|$S/glide-v12.sh stop|$S/glide-v12.sh probe|glide-v1.2"
)
running=""
stop_server() { [[ -n $running ]] && { bash -c "$running"; log "server stopped ($running)"; running=""; }; }
trap 'stop_server' EXIT
trap 'exit 143' TERM INT

for row in "${SETUPS[@]}"; do
  IFS='|' read -r slug arms start stop probe model <<<"$row"
  [[ " ${DECISION_SETUPS:-$slug} " == *" $slug "* ]] || continue
  todo=()
  for arm in $arms; do
    python3 "$PY" arm-state --arm "decision/$slug-$arm"; rc=$?
    if [[ $rc -eq 0 ]]; then todo+=("$arm"); else log "$slug-$arm: nothing to run (arm-state exit $rc)"; fi
  done
  (( ${#todo[@]} )) || { log "$slug: no arm to run, no server"; continue; }
  t0=$SECONDS
  until mib=$(used) && (( mib <= EMPTY )) || (( SECONDS - t0 >= FREE_WAIT )); do sleep 10; done
  if ! mib=$(used) || (( mib > EMPTY )); then
    log "REFUSED: GPU $GPU is not empty (${mib:-unreadable} MiB in use, limit $EMPTY); nothing started"; exit 1
  fi
  log "$slug: starting its server on GPU $GPU ($mib MiB in use) under reservation $RES"
  running=$stop
  if ! "$BUS" run "$RES" -- bash -c "$start"; then
    log "$slug: server did not start, skipping setup"; stop_server; continue
  fi
  reply=$(bash -c "$probe" 2>&1)
  if [[ $reply != *'"answers"'* || $reply != *"\"$model\""* ]]; then
    log "$slug: server probe failed (${reply:0:300}), skipping setup"; stop_server; continue
  fi
  log "$slug: server answers as $model"
  for arm in "${todo[@]}"; do
    while :; do
      python3 "$PY" run --arm "decision/$slug-$arm"; rc=$?
      case $rc in
        0) log "$slug-$arm: done"; break ;;
        3) log "$slug-$arm: paused (exit 3), retry in ${SLEEP}s"; sleep "$SLEEP" ;;
        2) log "$slug-$arm: stopped (exit 2), next arm"; break ;;
        *) log "$slug-$arm: exit $rc, skipping setup"; break 2 ;;
      esac
    done
  done
  stop_server
done
log "all local setups processed"
