#!/usr/bin/env bash
# Pause or resume the leagues together with the model servers they use on this machine's GPUs;
# the dashboard's Pause / Resume button runs pause and resume (tools/league_web.py --control).
#   tools/v3/league_control.sh pause [all]|free|resume|status
#
# This machine's servers (from 2026-10-19 overnight):
#   GPU 0: Gemma 4 31B replica + proxy (League 2), gemma4-31b-replicas.sh (GEMMA_GPUS, default 0)
#   GPU 1: Qwen3.8-27B (League 2), qwen38-27b.sh; once Qwen's League 2 matches are played,
#          Decider v1.2 27B (League 1) instead, decider-v1.2.sh 27b (tools/v3/swap_qwen_decider.sh)
#   GPU 2: LFM2.5-24B-A2B (League 2), lfm25-24b.sh
#   GPU 3: Open-Jev, Winnow-12B, Decider Flash v1.2 (League 1): open-jev.sh, winnow.sh,
#          decider-v1.2.sh flash
#
# pause:  SIGINT the league1 and league2 units (the runners stop; unfinished matches resume from
#         their last stored turn), wait until both are inactive, stop the overnight
#         v3-swap-qwen-decider watcher if it runs, then stop the GPU 0-2 servers, noting which
#         were up in league_control.servers. GPU 3's servers keep running unless `pause all`.
# free:   pause (GPU 0-2 servers only), then start league1 and league2 again, so both play on
#         with what is left (GPU 3, the DGX Sparks, the APIs); matches of the stopped local
#         models are deferred and retried with back-off until resume.
# resume: start the GPU 3 servers that are down, then the GPU 0-2 servers the last pause noted
#         (without a note: Gemma, Qwen3.8-27B and LFM2.5); each start waits until it answers
#         (the Gemma replica takes about 3 minutes). Then check Gemma answers a chat request and
#         start league1 and league2 (run_league1.sh / run_league2.sh resume them).
# All three are idempotent, hold league_control.lock so only one runs at a time, and log to
# league_control.log. status prints one JSON line for the dashboard: unit (league1), state
# (running | pausing | paused | resuming | error), since (UTC), the last message, and league2's
# unit state.

set -uo pipefail
REPO=$(readlink -f "$(dirname "$(readlink -f "$0")")/../..")
SERVERS=$REPO/tools/v3/servers
UNIT=league1
UNITS=(league1 league2)
LOG=$REPO/league_control.log
STATE=$REPO/league_control.state
LOCK=$REPO/league_control.lock
# GPU 0-2 servers that were up when the last pause stopped them (names, one per line).
NOTED=$REPO/league_control.servers
# How long pause waits for the runners to stop before giving up (servers are then left up).
PAUSE_WAIT=${PAUSE_WAIT:-900}
export PATH=$HOME/.local/bin:$PATH
# The Gemma replica as League 2 runs it: GPU 0, 24 sequences (16 thinking matches + (off)).
export GEMMA_GPUS=${GEMMA_GPUS:-0} GEMMA_MAX_SEQS=${GEMMA_MAX_SEQS:-24}

now() { date -u +%FT%TZ; }

# unit_live UNIT: what a runner unit is doing, as a control state.
unit_live() {
  case $(systemctl --user is-active "$1" 2>/dev/null) in
    active|reloading) echo running ;;
    activating) echo resuming ;;
    deactivating) echo pausing ;;
    *) echo paused ;;
  esac
}
live() { unit_live "$UNIT"; }

# State file, one tab-separated line: state, since, live state when written, message.
st='' since='' msg=''
write_state() {
  printf '%s\t%s\t%s\t%s\n' "$st" "$since" "$(live)" "$msg" >"$STATE.tmp" && mv -f "$STATE.tmp" "$STATE"
}
say() { msg=$*; echo "$(now) $msg"; write_state; }
enter() { st=$1 since=$(now); say "$2"; }
fail() { st=error since=$(now); say "failed: $*"; exit 1; }

gpu_memory() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader 2>/dev/null |
    awk -F', ' '{printf "%sGPU %s %s", (NR > 1 ? ", " : ""), $1, $2}'
}

# The servers on GPUs 0-2 and on GPU 3, as "name|probe|command" (probe: a URL that answers, or
# port:N that listens, while it is up; the command takes start|stop). Starts go in this order.
GPU012=(
  "Gemma 4 31B|http://127.0.0.1:8894/v1/models|$SERVERS/gemma4-31b-replicas.sh"
  "Qwen3.8-27B|http://127.0.0.1:8897/v1/models|$SERVERS/qwen38-27b.sh"
  "Decider v1.2 27B|port:18099|env DECIDER_V12_GPU=1 $SERVERS/decider-v1.2.sh 27b"
  "LFM2.5-24B-A2B|http://127.0.0.1:8898/v1/models|$SERVERS/lfm25-24b.sh"
)
GPU012_DEFAULT=("Gemma 4 31B" "Qwen3.8-27B" "LFM2.5-24B-A2B")
GPU3=(
  "Open-Jev|http://127.0.0.1:8791/health|env OPEN_JEV_GPU=3 $SERVERS/open-jev.sh"
  "Winnow-12B|http://127.0.0.1:8091/health|$SERVERS/winnow.sh"
  "Decider Flash v1.2|port:18098|$SERVERS/decider-v1.2.sh flash"
)

name_of() { echo "${1%%|*}"; }

# is_up ENTRY: whether the entry's server answers.
is_up() {
  local rest=${1#*|} probe
  probe=${rest%%|*}
  if [[ $probe == port:* ]]; then
    ss -ltnH "sport = :${probe#port:}" | grep -q .
  else
    curl -fsS -m 5 -o /dev/null "$probe" 2>/dev/null
  fi
}

# servers ACTION ENTRY...: run each entry's command with ACTION, in order; fail on the first error.
servers() {
  local action=$1 entry rest; shift
  for entry in "$@"; do
    rest=${entry#*|}
    ${rest#*|} "$action" || fail "${action}ing $(name_of "$entry")"
  done
}

# noted_entries: the GPU 0-2 entries the last pause noted as up, or the default set.
noted_entries() {
  local entry names=()
  if [[ -s $NOTED ]]; then
    mapfile -t names <"$NOTED"
  else
    names=("${GPU012_DEFAULT[@]}")
  fi
  for entry in "${GPU012[@]}"; do
    printf '%s\n' "${names[@]}" | grep -qxF "$(name_of "$entry")" && printf '%s\n' "$entry"
  done
}

stop_runners() {
  local start=$SECONDS u running=()
  for u in "${UNITS[@]}"; do
    [[ $(unit_live "$u") != paused ]] || continue
    systemctl --user kill -s INT "$u" || fail "could not signal $u"
    running+=("$u")
  done
  for u in "${running[@]}"; do
    until [[ $(unit_live "$u") == paused ]]; do
      (( SECONDS - start < PAUSE_WAIT )) || fail "$u still running after ${PAUSE_WAIT}s; servers left running"
      sleep 2
    done
  done
  say "runners stopped after $((SECONDS - start))s (${running[*]:-none were running})"
}

start_runners() {
  local u
  for u in "${UNITS[@]}"; do
    [[ $(unit_live "$u") == running ]] && { say "$u was already running"; continue; }
    systemctl --user reset-failed "$u" >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit="$u" --working-directory="$REPO" \
      bash -c "tools/v3/run_$u.sh >> $u.log 2>&1" || fail "could not start $u"
  done
  sleep 10
  for u in "${UNITS[@]}"; do
    [[ $(unit_live "$u") == running ]] || fail "$u exited at once (see $u.log)"
  done
}

pause() {
  local start=$SECONDS scope=${1:-} entry up=()
  enter pausing "pausing: stopping ${UNITS[*]}"
  stop_runners
  # The overnight Qwen -> Decider swap must not start a server on a freed GPU.
  if systemctl --user is-active -q v3-swap-qwen-decider; then
    systemctl --user stop v3-swap-qwen-decider && say "stopped the v3-swap-qwen-decider watcher"
  fi
  for entry in "${GPU012[@]}"; do
    is_up "$entry" && up+=("$(name_of "$entry")")
  done
  # A second pause finds nothing up and keeps the first one's note.
  (( ${#up[@]} == 0 )) || printf '%s\n' "${up[@]}" >"$NOTED"
  say "stopping the GPU 0-2 servers (up: ${up[*]:-none})"
  servers stop "${GPU012[@]}"
  if [[ $scope == all ]]; then
    say "stopping the GPU 3 servers"
    servers stop "${GPU3[@]}"
  fi
  enter paused "paused in $((SECONDS - start))s; $(gpu_memory)"
}

free() {
  local start=$SECONDS
  pause
  enter resuming "GPUs 0-2 free; starting ${UNITS[*]} on the remaining servers"
  start_runners
  enter running "running without the GPU 0-2 servers (freed in $((SECONDS - start))s); $(gpu_memory)"
}

resume() {
  local start=$SECONDS entries
  mapfile -t entries < <(noted_entries)
  enter resuming "resuming: starting the GPU 3 servers, then $(printf '%s\n' "${entries[@]}" | cut -d'|' -f1 | paste -sd, -)"
  servers start "${GPU3[@]}"
  servers start "${entries[@]}"
  say "servers ready after $((SECONDS - start))s"
  if printf '%s\n' "${entries[@]}" | grep -q '^Gemma 4 31B|'; then
    curl -fsS -m 300 -o /dev/null http://127.0.0.1:8894/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d '{"model":"gemma-4-31B-it","messages":[{"role":"user","content":"Say OK."}],"max_tokens":1}' ||
      fail "Gemma did not answer a chat request"
  fi
  start_runners
  enter running "running; resumed in $((SECONDS - start))s"
}

status() {
  local fst='' fsince='' flive='' fmsg='' cur state since busy=0
  [[ -f $STATE ]] && IFS=$'\t' read -r fst fsince flive fmsg <"$STATE"
  # Probe the lock and let go at once, so an action starting now is not kept waiting.
  exec 9>>"$LOCK"
  flock -n 9 || busy=1
  exec 9>&-
  cur=$(live)
  if (( busy )) && [[ $fst == pausing || $fst == resuming ]]; then
    state=$fst since=$fsince
  elif [[ $fst == error && $flive == "$cur" ]] || [[ $fst == "$cur" ]]; then
    state=$fst since=$fsince
  else
    # Changed outside this script (or never run): the unit's own timestamps.
    state=$cur since=''
    local prop=InactiveEnterTimestamp
    [[ $cur == running ]] && prop=ActiveEnterTimestamp
    local t
    t=$(systemctl --user show -p "$prop" --value "$UNIT" 2>/dev/null)
    [[ -n $t ]] && since=$(date -u -d "$t" +%FT%TZ 2>/dev/null)
    fmsg=${fmsg:+"last action: $fmsg"}
  fi
  jq -cn --arg unit "$UNIT" --arg state "$state" --arg since "$since" --arg message "$fmsg" \
    --arg league2 "$(unit_live league2)" \
    '{unit: $unit, state: $state, since: $since, message: $message, league2: $league2}'
}

case ${1:-} in
  pause|free|resume)
    if [[ -t 1 ]]; then exec > >(tee -a "$LOG") 2>&1; else exec >>"$LOG" 2>&1; fi
    exec 9>>"$LOCK"
    # A few seconds' grace for a status probe; a pause or resume holds it for minutes.
    if ! flock -w 5 9; then
      echo "$(now) $1: another pause, free or resume is running; nothing done"
      exit 75
    fi
    [[ $1 == pause && -n ${2:-} && $2 != all ]] && { echo "usage: $0 pause [all]" >&2; exit 2; }
    "$1" "${2:-}"
    ;;
  status) status ;;
  *) echo "usage: $0 pause [all]|free|resume|status" >&2; exit 2 ;;
esac
