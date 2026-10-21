#!/usr/bin/env bash
# Takes bariton's four GPUs over at 00:00 UTC on 2026-10-22 (systemd user timer midnight-takeover.timer,
# tools/v3/systemd/) and runs, in order:
#   0. stop the user's GPU jobs: running GPU containers that are not ours -> `docker stop` (never rm);
#      GPU processes that are not ours -> SIGINT, 30 s, SIGTERM, 30 s; never SIGKILL. A survivor's GPUs
#      are skipped and logged. Ours: v3-* containers and units, the DeepSeek compose project, league2.
#   1. Part A local smoke tests (tools/v3/smoke_parta.sh), in parallel on different GPUs:
#      d3-turbo on one GPU; Nemotron 3.5 Bolt BF16 TP2 on two, falling back to the 24GB build on one.
#      Each run is timeboxed (SMOKE_TIMEBOX seconds, default 5400) and its server stopped afterwards;
#      a failure is logged and the script goes on. Then `smoke_parta.sh report`.
#   2. League 2's last matches: GPU check again (same procedure), DeepSeek V4.1 Flash on all four
#      GPUs (compose, 127.0.0.2:8010), 20-request check (tools/v3/ds_equiv.py), the thinking players'
#      Spark servers (started if down), then the league2 unit; a watcher polls v3.db read-only
#      until League 2 is finished (restarting the unit or DeepSeek a few times if they die).
#   3. Cleanup: DeepSeek stopped, the League 2 Spark servers stopped (spark3: Gemma 4 31B, LFM2.5;
#      spark: Qwen3.8-27B; spark2 is never touched), final v3-page-refresh and bg-site-preview runs,
#      the summary written to "mailbox/Midnight takeover - log.md" (committed and pushed).
#
#   tools/v3/midnight_takeover.sh --dry-run   # prints every action against the current state; changes nothing
#   tools/v3/midnight_takeover.sh             # the real run (log: midnight-takeover.log)
set -uo pipefail

ROOT=/home/cbasaran/code/jevgammon
cd "$ROOT" || exit 1
DRY=0
[[ ${1:-} == --dry-run ]] && DRY=1
LOG=$ROOT/midnight-takeover.log
MAILBOX="mailbox/Midnight takeover - log.md"
STATE=${XDG_STATE_HOME:-$HOME/.local/state}/midnight-takeover
SUMMARY=$STATE/summary.md
DS_DIR=$HOME/code/deepseek-v4.1-flash-4x-rtx-pro-6000
DS_PROJECT=deepseek-v41-flash-4x-rtx-pro-6000
DS_URL=http://127.0.0.2:8010/v1
DS_EQUIV_MIN=${DS_EQUIV_MIN:-14}        # same top letter out of 20 (earlier checks: 16, 17, 17, 17)
SMOKE_TIMEBOX=${SMOKE_TIMEBOX:-5400}
GPU_WAIT=${GPU_WAIT:-21600}             # how long step 2 waits for all four GPUs before giving up
POLL=${POLL:-300}
SPARK3=spark3                           # Gemma 4 31B :8894, LFM2.5-24B-A2B :8898
SPARK=spark                             # Qwen3.8-27B :8897
GEMMA_URL=http://192.168.1.139:8894/v1/models
LFM_URL=http://192.168.1.139:8898/v1/models
QWEN_URL=http://192.168.1.127:8897/v1/models
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15)

if (( ! DRY )); then
  mkdir -p "$STATE"
  : >"$SUMMARY"
  exec >>"$LOG" 2>&1
fi

log() { echo "$(date -u +%FT%TZ) $*"; }
# note: log line that also goes into the mailbox summary.
note() {
  log "$*"
  (( DRY )) || echo "- $(date -u +%H:%M) UTC: $*" >>"$SUMMARY"
}
# act CMD...: run (logged), or only print in dry-run mode.
act() {
  if (( DRY )); then
    echo "DRY-RUN would run: $*"
    return 0
  fi
  log "run: $*"
  "$@"
}
pause() { (( DRY )) || sleep "$1"; }

# ---------------------------------------------------------------- GPU inventory

declare -A GPU_OF_UUID
while IFS=', ' read -r idx uuid; do GPU_OF_UUID[$uuid]=$idx; done \
  < <(nvidia-smi --query-gpu=index,uuid --format=csv,noheader)
ALL_GPUS=$(printf '%s\n' "${GPU_OF_UUID[@]}" | sort -n | tr '\n' ' ')

# compute_apps: "PID GPU[,GPU...]" per compute process.
compute_apps() {
  nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv,noheader 2>/dev/null |
    while IFS=', ' read -r pid uuid; do echo "$pid ${GPU_OF_UUID[$uuid]:-?}"; done |
    awk '{ g[$1] = ($1 in g) ? g[$1] "," $2 : $2 } END { for (p in g) print p, g[p] }' | sort -n
}

container_of_pid() { grep -o 'docker-[0-9a-f]\{64\}' "/proc/$1/cgroup" 2>/dev/null | head -1 | cut -c8-; }

container_is_ours() {
  local name project
  name=$(docker inspect -f '{{.Name}}' "$1" 2>/dev/null) || return 1
  project=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$1" 2>/dev/null)
  [[ ${name#/} == v3-* || $project == "$DS_PROJECT" ]]
}

process_is_ours() {
  grep -qE '/(v3-[^/]*|league2|midnight-takeover)\.service' "/proc/$1/cgroup" 2>/dev/null
}

# Running containers with GPU access (nvidia runtime or a device request).
gpu_containers() {
  local ids
  ids=$(docker ps -q)
  [[ -n $ids ]] || return 0
  # shellcheck disable=SC2086
  docker inspect -f '{{.Id}} {{.HostConfig.Runtime}} {{if .HostConfig.DeviceRequests}}1{{else}}0{{end}}' $ids |
    awk '$2 == "nvidia" || $3 > 0 { print $1 }'
}

declare -A TRIED   # PIDs already signalled (never signalled twice)

wait_gone() { local i; for ((i = 0; i < $2; i++)); do kill -0 "$1" 2>/dev/null || return 0; sleep 1; done; ! kill -0 "$1" 2>/dev/null; }

stop_process() {
  local pid=$1
  if (( DRY )); then
    echo "DRY-RUN would run: kill -INT $pid; wait up to 30 s; if alive: kill -TERM $pid; wait up to 30 s; if alive: leave it (no SIGKILL), skip its GPU(s)"
    return 0
  fi
  TRIED[$pid]=1
  log "run: kill -INT $pid"
  kill -INT "$pid" 2>/dev/null
  wait_gone "$pid" 30 && { note "process $pid exited after SIGINT"; return 0; }
  log "run: kill -TERM $pid"
  kill -TERM "$pid" 2>/dev/null
  wait_gone "$pid" 30 && { note "process $pid exited after SIGTERM"; return 0; }
  note "process $pid survived SIGINT and SIGTERM; left running (no SIGKILL), its GPU(s) skipped"
  return 1
}

# clear_gpus PHASE: stop the user's GPU jobs; sets FREE (GPU indices with no foreign compute process).
clear_gpus() {
  local phase=$1 id name image pid gpus cid owner cmd stopped=0
  local -A blocked=()
  log "[$phase] GPU check; memory used per GPU: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '{ printf "%s:%s MiB  ", $1, $2 }')"
  for id in $(gpu_containers); do
    name=$(docker inspect -f '{{.Name}}' "$id"); name=${name#/}
    if container_is_ours "$id"; then
      log "[$phase] container $name: ours, kept"
      continue
    fi
    image=$(docker inspect -f '{{.Config.Image}}' "$id")
    note "[$phase] user GPU container $name (image $image, id ${id:0:12}): stopping (docker stop, not removed)"
    act docker stop -t 120 "$name" && stopped=1
  done
  (( stopped )) && pause 10
  while read -r pid gpus; do
    [[ -n $pid && -d /proc/$pid ]] || continue
    cmd=$(ps -o args= -p "$pid" 2>/dev/null | cut -c1-200)
    cid=$(container_of_pid "$pid")
    if [[ -n $cid ]]; then
      name=$(docker inspect -f '{{.Name}}' "$cid" 2>/dev/null); name=${name#/}
      if container_is_ours "$cid"; then
        log "[$phase] PID $pid on GPU $gpus in our container $name: kept"
      elif (( DRY )); then
        log "[$phase] PID $pid on GPU $gpus in container ${name:-${cid:0:12}} ($cmd): goes with the docker stop above"
      else
        note "[$phase] PID $pid on GPU $gpus still running in container ${name:-${cid:0:12}} after docker stop; GPU(s) $gpus skipped"
        IFS=, read -ra g <<<"$gpus"; for x in "${g[@]}"; do blocked[$x]=1; done
      fi
      continue
    fi
    if process_is_ours "$pid"; then
      log "[$phase] PID $pid on GPU $gpus is ours ($cmd): kept"
      continue
    fi
    owner=$(stat -c %U "/proc/$pid")
    note "[$phase] user GPU process PID $pid (user $owner, GPU $gpus): $cmd"
    if [[ $owner != "$USER" ]]; then
      note "[$phase] PID $pid belongs to $owner, not signalled; GPU(s) $gpus skipped"
      IFS=, read -ra g <<<"$gpus"; for x in "${g[@]}"; do blocked[$x]=1; done
    elif [[ -n ${TRIED[$pid]:-} ]]; then
      note "[$phase] PID $pid was already signalled earlier and is still there; GPU(s) $gpus skipped"
      IFS=, read -ra g <<<"$gpus"; for x in "${g[@]}"; do blocked[$x]=1; done
    elif ! stop_process "$pid"; then
      IFS=, read -ra g <<<"$gpus"; for x in "${g[@]}"; do blocked[$x]=1; done
    fi
  done < <(compute_apps)
  if (( ! DRY )); then
    # The truth is what is left on the GPUs now.
    sleep 5
    blocked=()
    while read -r pid gpus; do
      [[ -n $pid && -d /proc/$pid ]] || continue
      cid=$(container_of_pid "$pid")
      if [[ -n $cid ]]; then container_is_ours "$cid" && continue
      else process_is_ours "$pid" && continue; fi
      IFS=, read -ra g <<<"$gpus"; for x in "${g[@]}"; do blocked[$x]=1; done
    done < <(compute_apps)
  fi
  FREE=()
  for x in $ALL_GPUS; do [[ -n ${blocked[$x]:-} ]] || FREE+=("$x"); done
  note "[$phase] GPUs free for us: ${FREE[*]:-none}${blocked[*]:+ (held by a user job: ${!blocked[*]})}"
}

# ---------------------------------------------------------------- step 1: smoke tests

# timeboxed NAME CMD...: run with SMOKE_TIMEBOX (SIGINT, SIGKILL 5 min later: only our own processes),
# output to smoke/takeover-NAME.log.
timeboxed() {
  local name=$1 rc; shift
  if (( DRY )); then
    echo "DRY-RUN would run: timeout --signal=INT --kill-after=300 $SMOKE_TIMEBOX $* >> smoke/takeover-$name.log 2>&1"
    return 0
  fi
  log "run ($name, timebox ${SMOKE_TIMEBOX}s): $*"
  timeout --signal=INT --kill-after=300 "$SMOKE_TIMEBOX" "$@" >>"smoke/takeover-$name.log" 2>&1
  rc=$?
  (( rc == 124 )) && note "$name: timed out after ${SMOKE_TIMEBOX}s (answers so far stay in smoke/part-a.db)" ||
    { (( rc == 0 )) && note "$name: done" || note "$name: failed (exit $rc, see smoke/takeover-$name.log)"; }
  return "$rc"
}

smoke_d3() {
  log "d3-turbo smoke test on GPU $1"
  timeboxed d3 env D3_GPU="$1" tools/v3/smoke_parta.sh d3
  act tools/v3/servers/d3-turbo.sh stop
}

smoke_nemotron() {
  local gpus=$1 start=$SECONDS
  if systemctl --user is-active -q v3-nemotron-prefetch; then
    log "waiting for v3-nemotron-prefetch (checkpoint download + image build) to finish"
    (( DRY )) || while systemctl --user is-active -q v3-nemotron-prefetch && (( SECONDS - start < SMOKE_TIMEBOX )); do sleep 30; done
  fi
  if [[ $gpus == *,* ]]; then
    log "Nemotron 3.5 Bolt BF16 (TP2) smoke test on GPUs $gpus"
    timeboxed nemotron-bf16 env NEMOTRON_GPUS="$gpus" tools/v3/smoke_parta.sh nemotron-bf16 && { act tools/v3/servers/nemotron35-bolt.sh stop; return; }
    act tools/v3/servers/nemotron35-bolt.sh stop
    (( DRY )) && log "(only if the BF16 run fails:)"
    gpus=${gpus%%,*}
  fi
  log "Nemotron 3.5 Bolt 24GB smoke test on GPU $gpus"
  timeboxed nemotron env NEMOTRON_GPUS="$gpus" tools/v3/smoke_parta.sh nemotron
  act tools/v3/servers/nemotron35-bolt.sh stop
}

step1() {
  log "=== step 1: Part A local smoke tests"
  clear_gpus "00:00"
  local n=${#FREE[@]}
  if (( n >= 3 )); then
    note "smoke tests in parallel: d3-turbo on GPU ${FREE[0]}, Nemotron BF16 on GPUs ${FREE[n-2]},${FREE[n-1]} (24GB fallback on GPU ${FREE[n-2]})"
    if (( DRY )); then
      smoke_d3 "${FREE[0]}"; smoke_nemotron "${FREE[n-2]},${FREE[n-1]}"
    else
      smoke_d3 "${FREE[0]}" & local p1=$!
      smoke_nemotron "${FREE[n-2]},${FREE[n-1]}" & local p2=$!
      wait "$p1" "$p2"
    fi
  elif (( n == 2 )); then
    note "only 2 GPUs free: d3-turbo on GPU ${FREE[0]}, then Nemotron BF16 on GPUs ${FREE[0]},${FREE[1]}"
    smoke_d3 "${FREE[0]}"; smoke_nemotron "${FREE[0]},${FREE[1]}"
  elif (( n == 1 )); then
    note "only GPU ${FREE[0]} free: d3-turbo, then Nemotron 24GB, one after the other"
    smoke_d3 "${FREE[0]}"; smoke_nemotron "${FREE[0]}"
  else
    note "no GPU free: smoke tests skipped"
    return
  fi
  if (( DRY )); then
    echo "DRY-RUN would run: tools/v3/smoke_parta.sh report > smoke/takeover-report.txt"
  else
    tools/v3/smoke_parta.sh report >smoke/takeover-report.txt 2>>smoke/takeover-report.log &&
      note "smoke report: smoke/takeover-report.txt and smoke/part-a.json" || note "smoke report failed (smoke/takeover-report.log)"
  fi
}

# ---------------------------------------------------------------- step 2: League 2

ds_up() { curl -fsS -m 10 -o /dev/null "$DS_URL/models" 2>/dev/null; }
ds_running() {
  local id
  id=$(docker ps -q -f "label=com.docker.compose.project=$DS_PROJECT")
  [[ -n $id ]]
}
ds_start() {
  local start=$SECONDS
  act bash -c "cd '$DS_DIR' && BIND_ADDRESS=127.0.0.2 docker compose -f compose.yaml up -d"
  (( DRY )) && { echo "DRY-RUN would wait (up to 30 min) until $DS_URL/models answers"; return 0; }
  until ds_up; do
    ds_running || { note "DeepSeek container exited while loading"; docker logs --tail 30 "$(docker ps -aq -f "label=com.docker.compose.project=$DS_PROJECT" | head -1)"; return 1; }
    (( SECONDS - start < 1800 )) || { note "DeepSeek not ready after 30 min"; return 1; }
    sleep 15
  done
  note "DeepSeek V4.1 Flash ready after $((SECONDS - start)) s ($DS_URL)"
}
ds_stop() { act bash -c "cd '$DS_DIR' && docker compose -f compose.yaml stop"; }

up() { curl -fsS -m 10 -o /dev/null "$1" 2>/dev/null; }
wait_up() { local url=$1 start=$SECONDS; until up "$url"; do (( SECONDS - start < 1800 )) || return 1; sleep 20; done; }

# The thinking players' servers (AFTER_MORNING.md): Gemma before LFM2.5 on spark3 (LFM2.5 first gets
# Gemma OOM-killed), Qwen3.8-27B on spark.
ensure_thinkers() {
  local g=1 l=1 q=1
  up "$GEMMA_URL" || g=0; up "$LFM_URL" || l=0; up "$QWEN_URL" || q=0
  log "thinking players: Gemma 4 31B $( ((g)) && echo up || echo down), LFM2.5 $( ((l)) && echo up || echo down), Qwen3.8-27B $( ((q)) && echo up || echo down)"
  if (( ! g )); then
    note "Gemma 4 31B (spark3) down: restarting LFM2.5 after it"
    act "${SSH[@]}" "$SPARK3" 'cd ~/code/v3-servers && ./lfm25-24b.sh stop; BIND_HOST=0.0.0.0 GEMMA_MAX_SEQS=24 ./gemma4-31b.sh start'
    (( DRY )) || wait_up "$GEMMA_URL" || note "Gemma 4 31B still not answering after 30 min"
    l=0
  fi
  if (( ! l )); then
    (( g )) && note "LFM2.5 (spark3) down: starting it"
    act "${SSH[@]}" "$SPARK3" 'cd ~/code/v3-servers && BIND_HOST=0.0.0.0 LFM_GPU=0 ./lfm25-24b.sh start'
    (( DRY )) || wait_up "$LFM_URL" || note "LFM2.5 still not answering after 30 min"
  fi
  if (( ! q )); then
    note "Qwen3.8-27B (spark) down: starting it"
    act "${SSH[@]}" "$SPARK" 'cd ~/code/v3-servers && BIND_HOST=0.0.0.0 QWEN27_GPU=0 ./qwen38-27b.sh start'
    (( DRY )) || wait_up "$QWEN_URL" || note "Qwen3.8-27B still not answering after 30 min"
  fi
}

league2_status() { sqlite3 -readonly -cmd '.timeout 60000' v3.db "SELECT status FROM leagues WHERE id = 2"; }
league2_left() {
  sqlite3 -readonly -cmd '.timeout 60000' v3.db "SELECT count(*) FROM league_matches lm LEFT JOIN matches m ON m.id = lm.match_id
    WHERE lm.league_id = 2 AND coalesce(m.status, '') != 'finished'"
}
league2_start() {
  if systemctl --user is-active -q league2; then log "league2 already running"; return 0; fi
  act systemctl --user reset-failed league2
  act systemd-run --user --unit=league2 --working-directory="$ROOT" /usr/bin/bash -c 'tools/v3/run_league2.sh >> league2.log 2>&1'
}

step2() {
  log "=== step 2: League 2's last matches (DeepSeek V4.1 Flash on all four GPUs)"
  if [[ $(league2_status) == finished ]]; then note "League 2 already finished"; return 0; fi
  local start=$SECONDS
  while :; do
    clear_gpus "step 2"
    (( ${#FREE[@]} == 4 || DRY )) && break
    # DeepSeek is TP4 over all four GPUs: nothing smaller fits; wait (no stronger signals).
    (( SECONDS - start < GPU_WAIT )) || { note "GPUs ${FREE[*]:-none} free after $((GPU_WAIT / 3600)) h; DeepSeek needs all four: League 2 not resumed"; return 1; }
    note "DeepSeek needs all four GPUs, only ${FREE[*]:-none} free: checking again in 10 min"
    sleep 600
  done
  ds_start || { ds_stop; note "League 2 not resumed (DeepSeek did not start)"; return 1; }
  if (( DRY )); then
    echo "DRY-RUN would run: python3 tools/v3/ds_equiv.py ds-off $DS_URL  (league starts only if same top letter >= $DS_EQUIV_MIN/20; a check that cannot finish is logged and ignored)"
  else
    local out same
    out=$(python3 tools/v3/ds_equiv.py ds-off "$DS_URL" 2>&1)
    echo "$out" | tail -22
    same=$(grep -o 'same top letter [0-9]*/20' <<<"$out" | grep -o '[0-9]*/' | tr -d /)
    if [[ -z $same ]]; then
      note "20-request check could not finish (see log); going on"
    elif (( same < DS_EQUIV_MIN )); then
      note "20-request check: same top letter $same/20, below $DS_EQUIV_MIN: DeepSeek stopped, League 2 not resumed"
      ds_stop; return 1
    else
      note "20-request check: $(grep -o 'same top letter.*' <<<"$out")"
    fi
  fi
  ensure_thinkers
  league2_start
  (( DRY )) || note "league2 started: $(league2_left) of 136 matches left"
  watch_league2
}

watch_league2() {
  if (( DRY )); then
    echo "DRY-RUN would poll v3.db (read-only) every ${POLL}s until League 2 is finished (now: $(league2_status), $(league2_left) matches left);"
    echo "        if the league2 unit stops early: restart it (at most 3 times); if the DeepSeek container dies: compose up again (at most 3 times)"
    return 0
  fi
  local unit_restarts=0 ds_restarts=0 last_hour=-1 st
  while :; do
    sleep "$POLL"
    st=$(league2_status)
    [[ $st == finished ]] && { note "League 2 finished"; return 0; }
    if [[ $(date -u +%H) != "$last_hour" ]]; then
      last_hour=$(date -u +%H); log "League 2: $st, $(league2_left) matches left; DeepSeek $(ds_up && echo up || echo DOWN)"
    fi
    if ! ds_running && (( ds_restarts < 3 )); then
      ds_restarts=$((ds_restarts + 1))
      note "DeepSeek container not running: starting it again ($ds_restarts/3)"
      ds_start || true
    fi
    if ! systemctl --user is-active -q league2 && [[ $(league2_status) != finished ]]; then
      if (( unit_restarts >= 3 )); then
        note "league2 stopped a 4th time before finishing: not restarted; League 2 left unfinished"
        return 1
      fi
      unit_restarts=$((unit_restarts + 1))
      note "league2 unit stopped before League 2 finished ($(systemctl --user show -p Result --value league2)): restarting ($unit_restarts/3)"
      tail -5 league2.log
      sleep 60
      ensure_thinkers
      league2_start
    fi
  done
}

# ---------------------------------------------------------------- step 3: cleanup

run_oneshot() {
  local unit=$1
  if (( ! DRY )); then
    while systemctl --user is-active -q "$unit"; do log "$unit already running; waiting for it"; sleep 60; done
  fi
  act systemctl --user start "$unit" || { note "$unit: failed (journalctl --user -u $unit)"; return; }
  (( DRY )) || note "$unit: done"
}

step3() {
  log "=== step 3: cleanup and page refresh"
  local finished=0 i
  [[ $(league2_status) == finished ]] && finished=1
  if (( finished )) && (( ! DRY )); then
    for ((i = 0; i < 90; i++)); do systemctl --user is-active -q league2 || break; sleep 10; done
    systemctl --user is-active -q league2 && { note "league2 still running 15 min after finishing: SIGINT"; systemctl --user kill -s SIGINT league2; sleep 60; }
  fi
  (( DRY )) && log "(when League 2 has finished:)"
  ds_stop
  if (( finished || DRY )); then
    act "${SSH[@]}" "$SPARK3" 'cd ~/code/v3-servers && ./gemma4-31b.sh stop; ./lfm25-24b.sh stop'
    act "${SSH[@]}" "$SPARK" 'cd ~/code/v3-servers && ./qwen38-27b.sh stop'
    (( DRY )) || note "Spark servers stopped (spark3: Gemma 4 31B, LFM2.5; spark: Qwen3.8-27B)"
  else
    note "League 2 not finished: Spark servers left running"
  fi
  run_oneshot v3-page-refresh.service
  run_oneshot bg-site-preview.service
  log "v3-page-refresh.timer: $(systemctl --user is-enabled v3-page-refresh.timer 2>&1), $(systemctl --user is-active v3-page-refresh.timer 2>&1)"
  if (( ! DRY )); then
    [[ $(systemctl --user is-enabled v3-page-refresh.timer 2>&1) == enabled ]] &&
      note "v3-page-refresh.timer is still enabled (page_refresh.sh disables it once Leagues 2 and 3 are finished and pushed)" ||
      note "v3-page-refresh.timer disabled"
  fi
}

# ---------------------------------------------------------------- summary

WRITTEN=0
write_mailbox() {
  (( DRY || WRITTEN )) && return 0
  WRITTEN=1
  {
    echo "# Midnight takeover - log"
    echo
    echo "bariton's four GPUs, taken over at 00:00 UTC on 2026-10-22 by \`tools/v3/midnight_takeover.sh\`"
    echo "(timer \`midnight-takeover.timer\`). Full log: \`midnight-takeover.log\`; smoke test output:"
    echo "\`smoke/takeover-*.log\`, table \`smoke/takeover-report.txt\`."
    echo
    echo "## What happened"
    echo
    cat "$SUMMARY"
    echo
    echo "## Smoke test table"
    echo
    echo '```'
    cat smoke/takeover-report.txt 2>/dev/null || echo "(no report)"
    echo '```'
    echo
    echo "## End state ($(date -u '+%F %H:%M') UTC)"
    echo
    echo "- League 2: $(league2_status), $(league2_left) of 136 matches not finished"
    echo "- bariton GPUs: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ';')"
  } >"$MAILBOX"
  git add -- "$MAILBOX" && git commit -q -m "mailbox: midnight takeover log" -- "$MAILBOX" &&
    { git push -q origin HEAD 2>&1 || log "git push failed; commit left local"; }
  log "summary written to $MAILBOX"
}

if (( DRY )); then
  log "DRY RUN (nothing is stopped or started); state now: GPUs $ALL_GPUS"
else
  trap 'note "takeover script exiting early (signal or error)"; write_mailbox' EXIT
  log "midnight takeover start"
fi
step1
step2
step3
write_mailbox
trap - EXIT
log "midnight takeover done"
