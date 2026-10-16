#!/usr/bin/env bash
# Pause or resume League 1 together with the servers it uses on this machine's GPUs; the
# dashboard's Pause / Resume button runs this (tools/league_web.py --control).
#   tools/v3/league_control.sh pause|resume|status
#
# pause:  SIGINT the league1 unit (the runner stops; unfinished matches resume from their last
#         stored turn), wait until it is inactive, then stop the Gemma 4 31B replicas and proxy
#         (GPUs 0, 1, 3) and Open-Jev (GPU 2). The decision servers on the Sparks keep running.
# resume: start those servers (each start waits until it answers; the replicas take about
#         2 min), check Gemma answers a chat request, then start league1 (run_league1.sh
#         resumes League 1).
# Both are idempotent, hold league_control.lock so only one runs at a time, and log to
# league_control.log. status prints one JSON line: unit, state (running | pausing | paused |
# resuming | error), since (UTC) and the last message.

set -uo pipefail
REPO=$(readlink -f "$(dirname "$(readlink -f "$0")")/../..")
SERVERS=$REPO/tools/v3/servers
UNIT=league1
LOG=$REPO/league_control.log
STATE=$REPO/league_control.state
LOCK=$REPO/league_control.lock
# How long pause waits for the runner to stop before giving up (servers are then left up).
PAUSE_WAIT=${PAUSE_WAIT:-900}
export PATH=$HOME/.local/bin:$PATH

now() { date -u +%FT%TZ; }

# live: what the league1 unit is doing, as a control state.
live() {
  case $(systemctl --user is-active "$UNIT" 2>/dev/null) in
    active|reloading) echo running ;;
    activating) echo resuming ;;
    deactivating) echo pausing ;;
    *) echo paused ;;
  esac
}

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

pause() {
  local start=$SECONDS waited
  enter pausing "pausing: stopping $UNIT"
  if [[ $(live) != paused ]]; then
    systemctl --user kill -s INT "$UNIT" || fail "could not signal $UNIT"
    until [[ $(live) == paused ]]; do
      (( SECONDS - start < PAUSE_WAIT )) || fail "$UNIT still running after ${PAUSE_WAIT}s; servers left running"
      sleep 2
    done
    say "$UNIT stopped after $((SECONDS - start))s; stopping the Gemma replicas and Open-Jev"
  else
    say "$UNIT was not running; stopping the Gemma replicas and Open-Jev"
  fi
  "$SERVERS/gemma4-31b-replicas.sh" stop || fail "stopping the Gemma replicas"
  "$SERVERS/open-jev.sh" stop || fail "stopping Open-Jev"
  enter paused "paused in $((SECONDS - start))s; $(gpu_memory)"
}

resume() {
  local start=$SECONDS gemma open_jev bad=()
  enter resuming "resuming: starting the Gemma replicas and Open-Jev"
  "$SERVERS/gemma4-31b-replicas.sh" start & gemma=$!
  "$SERVERS/open-jev.sh" start & open_jev=$!
  wait "$gemma" || bad+=("the Gemma replicas")
  wait "$open_jev" || bad+=("Open-Jev")
  (( ${#bad[@]} == 0 )) || fail "${bad[*]} did not start (servers that did are left running)"
  say "servers ready after $((SECONDS - start))s; checking Gemma answers"
  curl -fsS -m 300 -o /dev/null http://127.0.0.1:8894/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma-4-31B-it","messages":[{"role":"user","content":"Say OK."}],"max_tokens":1}' ||
    fail "Gemma did not answer a chat request"
  if [[ $(live) == running ]]; then
    say "$UNIT was already running"
  else
    systemctl --user reset-failed "$UNIT" >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit="$UNIT" --working-directory="$REPO" \
      bash -c 'tools/v3/run_league1.sh >> league1.log 2>&1' || fail "could not start $UNIT"
    sleep 10
    [[ $(live) == running ]] || fail "$UNIT exited at once (see league1.log)"
  fi
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
    '{unit: $unit, state: $state, since: $since, message: $message}'
}

case ${1:-} in
  pause|resume)
    if [[ -t 1 ]]; then exec > >(tee -a "$LOG") 2>&1; else exec >>"$LOG" 2>&1; fi
    exec 9>>"$LOCK"
    # A few seconds' grace for a status probe; a pause or resume holds it for minutes.
    if ! flock -w 5 9; then
      echo "$(now) $1: another pause or resume is running; nothing done"
      exit 75
    fi
    "$1"
    ;;
  status) status ;;
  *) echo "usage: $0 pause|resume|status" >&2; exit 2 ;;
esac
