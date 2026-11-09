#!/usr/bin/env bash
# "Did they improve?" decision models (Zeki #3790): the hosted setups one at a time, strictly sequential, as the
# systemd user unit improve-decision:
#   systemd-run --user --unit=improve-decision --working-directory=$HOME/code/jevgammon-improve-decision \
#     workspace/improve/run_decision.sh
# Per setup: `decision.py probe-p1 --send` until it passes (3 = refused for now: log, sleep, retry; 2/other = skip
# the setup), then each arm `decision.py run` until done (0 done; 3 log + sleep + retry; 2 next arm; other: skip
# the setup). DECISION_PY / DECISION_SLEEP / DECISION_SETUPS override the script, wait and setups (tests only).
set -uo pipefail
cd "$(dirname "$0")/../.."
[[ -n ${DECISION_PY:-} ]] || . "$HOME/.keys"
export IMPROVE_BIN=${IMPROVE_BIN:-$HOME/code/jevgammon-improve-decision/target/release/jevgammon-bb74f07}
export IMPROVE_LANE=decision
PY=${DECISION_PY:-workspace/improve/decision.py}
SLEEP=${DECISION_SLEEP:-300}
log() { echo "$(date -u +%FT%TZ) $*"; }

for slug in ${DECISION_SETUPS:-subq-snap-1.1 drex-max-1.1}; do
  while :; do
    python3 "$PY" probe-p1 --setup "$slug" --send; rc=$?
    [[ $rc -eq 0 ]] && { log "$slug: P1 passed"; break; }
    if [[ $rc -eq 3 ]]; then log "$slug: P1 waiting (exit 3), retry in ${SLEEP}s"; sleep "$SLEEP"; continue; fi
    log "$slug: P1 failed (exit $rc), skipping setup"; continue 2
  done
  for arm in notes worst; do
    while :; do
      python3 "$PY" run --arm "decision/$slug-$arm"; rc=$?
      case $rc in
        0) log "$slug-$arm: done"; break ;;
        3) log "$slug-$arm: paused (exit 3), retry in ${SLEEP}s"; sleep "$SLEEP" ;;
        2) log "$slug-$arm: stopped (exit 2), next arm"; break ;;
        *) log "$slug-$arm: exit $rc, skipping setup"; continue 3 ;;
      esac
    done
  done
done
log "all setups processed"
