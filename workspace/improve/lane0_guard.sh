#!/usr/bin/env bash
# One-off guard for the GPU-0 local lane started 2026-11-09 01:52 UTC with the pre-claim run_local.sh (its queue still
# lists Qwen3.8-27B and LFM2.5, now owned by lane improve-local3 on another GPU). It ends that lane before its loop can
# touch another model's server: as soon as Gemma's run process exits (normally, paused or stopped), or as soon as the
# lane's shell starts anything for Qwen3.8-27B or LFM2.5, it stops the unit improve-local and the container
# v3-gemma4-31b, and nothing else. Gemma's run itself is never touched.
#   systemd-run --user --unit improve-lane0-guard workspace/improve/lane0_guard.sh GEMMA_RUN_PID LANE_SHELL_PID
set -uo pipefail
RUN=${1:?Gemma run pid}; SHELL_PID=${2:?lane shell pid}
LOG=/home/cbasaran/code/jevgammon/workspace/improve/runs/gemma-4-31b-on/log.jsonl
note() { echo "$(date -u +%FT%TZ) $*"; }
cmd() { tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null; }  # cmdline arguments are NUL-separated
cmd "$RUN" | grep -q "improve.py run --model gemma-4-31b-on" || { note "pid $RUN is not Gemma's run"; exit 1; }
cmd "$SHELL_PID" | grep -q "run_local.sh" || { note "pid $SHELL_PID is not the lane shell"; exit 1; }
GATE=/home/cbasaran/code/jevgammon/workspace/improve/runs/server_gate.txt
# Zeki #3397: while the lane shell is alive, the server gate file must exist and list improve-local.service (the gate
# allows every caller when the file is absent). Checked at start and once a minute; restored and logged if not.
check_gate() {
  [[ -d /proc/$SHELL_PID ]] || return 0
  if ! grep -qxF improve-local.service "$GATE" 2>/dev/null; then
    echo improve-local.service >> "$GATE"
    note "server gate restored: $GATE did not list improve-local.service"
    printf '{"at": "%s", "event": "server_gate_restored", "file": "%s"}\n' "$(date -u +%FT%T+00:00)" "$GATE" >> "$LOG"
  fi
}
check_gate
note "guarding: Gemma run $RUN, lane shell $SHELL_PID; stop action: improve-local + v3-gemma4-31b only; gate file checked each minute"
printf '{"at": "%s", "event": "lane0_guard_start", "gemma_run_pid": %s, "lane_shell_pid": %s, "stop_action": "systemctl --user stop improve-local; docker stop v3-gemma4-31b"}\n' "$(date -u +%FT%T+00:00)" "$RUN" "$SHELL_PID" >> "$LOG"
tick=0
while true; do
  why=""
  if [[ ! -d /proc/$RUN ]]; then why="Gemma's run exited"; fi
  if [[ -z "$why" ]]; then
    for c in $(pgrep -P "$SHELL_PID"); do
      [[ "$c" == "$RUN" ]] && continue
      if cmd "$c" | grep -qE 'qwen38-27b|lfm25-24b|qwen3\.8-27b-on|lfm2\.5-24b-a2b-on'; then
        why="the lane shell started: $(cmd "$c" | cut -c1-200)"
      fi
    done
  fi
  if [[ -n "$why" ]]; then
    note "firing: $why"
    systemctl --user stop improve-local
    docker stop v3-gemma4-31b >/dev/null 2>&1
    printf '{"at": "%s", "event": "lane0_guard_fired", "why": "%s", "action": "improve-local stopped, v3-gemma4-31b stopped"}\n' "$(date -u +%FT%T+00:00)" "${why//\"/\'}" >> "$LOG"
    exit 0
  fi
  systemctl --user is-active -q improve-local || { note "improve-local is no longer active: guard ends"; exit 0; }
  (( ++tick % 60 == 0 )) && check_gate
  sleep 1
done
