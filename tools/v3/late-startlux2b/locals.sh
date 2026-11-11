#!/usr/bin/env bash
# StartLux-Decision v1.1 2B v the 8 local League 1 opponents, one opponent server at a time on OPP_GPU under the bus
# reservation RES (only once Main hands over a free card), as tools/v3/late-ember/locals.sh. StartLux itself stays on
# its own server (player.json base_url). For each opponent whose pair is unplayed: waits until OPP_GPU has room for it
# (+2 GB; a GPU held by someone else is waited for, never freed), starts its server with `agent-bus run RES -- ...`,
# league-adds it to StartLux's league, waits until the pair is played, stops the server. It keeps start.sh's guard
# (OpenRouter balance >= $40 and readable, paid opponents < $5, StartLux server healthy) itself, so the unit
# late-startlux2b (start.sh) must have exited first. Before each opponent's server starts and before its league-add,
# quiesce() confirms nothing plays league #ID; any failure aborts the run there, logged (Zeki #4628, as late-knowline).
#   systemd-run --user --unit=late-startlux2b-locals --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E OPP_GPU=<n> -E RES=<reservation> \
#     /home/cbasaran/code/jevgammon-startlux2b/tools/v3/late-startlux2b/locals.sh
set -uo pipefail
cd /home/cbasaran/code/jevgammon
export PATH=$HOME/.local/bin:$PATH  # agent-bus
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-startlux2b
ST=$W/state
S=tools/v3/servers
BIN=/home/cbasaran/code/jevgammon/target/startlux2b/release/jevgammon
STATUS="mailbox/Late entries StartLux 2B - status.md"
UNIT=late-startlux2b-league
FLOOR=40
CAP=5
URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$T/player.json")
: "${OPP_GPU:?}" "${RES:?}"
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/locals.log; echo "- $line" >> "$STATUS"; }
room() { nvidia-smi -i "$1" --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print $1-$2}'; }
gpus() { nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { python3 $T/startlux.py billed "$(cat $ST/first)"; }
healthy() { curl -fsS -m 10 -o /dev/null "$URL/health"; }
# Guard; returns 1 (and logs) when the run must stop.
down=0
unread=0
guard() {
  local bal s
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then log "locals STOPPED: OpenRouter balance \$$bal under \$$FLOOR"; return 1; fi
  else
    unread=$((unread + 1))
    (( unread < 3 )) || { log "locals STOPPED: OpenRouter balance unreadable 3 times in a row"; return 1; }
  fi
  s=$(spent)
  lt "$s" "$CAP" || { log "locals STOPPED: paid opponents \$$s reached the \$$CAP cap"; return 1; }
  if healthy; then down=0; else down=$((down + 1)); fi
  (( down < 3 )) || { log "locals STOPPED: StartLux server $URL failed 3 health checks in a row"; return 1; }
}
ensure_league() {
  systemctl --user is-active -q $UNIT && return 0
  systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
  systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
}
# Stops the league unit and confirms nothing can play league #ID (Zeki #4628, as tools/v3/late-knowline/locals.sh
# 4d7502f): the stop succeeded (or the unit is not loaded at all: systemd then refuses the stop, exit 5, LoadState
# not-found); systemctl reports the unit inactive or failed; and pgrep finds no league runner for it (run_league.sh,
# `league --resume ID --db`, `league --config` of StartLux 2B's config; pgrep exit 1 = none, 0 = found, anything else =
# unknown). Returns 1, logged, otherwise.
quiesce() {
  local load state found
  if ! systemctl --user stop $UNIT 2>/dev/null; then
    load=$(systemctl --user show -p LoadState --value $UNIT 2>/dev/null)
    [[ $load == not-found ]] || { log "locals: stopping $UNIT failed (LoadState ${load:-unknown})"; return 1; }
  fi
  state=$(systemctl --user is-active $UNIT 2>/dev/null)
  [[ $state == inactive || $state == failed ]] || { log "locals: $UNIT is ${state:-of unknown state} after the stop"; return 1; }
  pgrep -f -- "late-startlux2b/run_league\.sh|league --resume $ID --db|league --config [^ ]*startlux-decision-v1\.1-2b\.json" \
    >/dev/null 2>&1
  found=$?
  (( found == 1 )) || { log "locals: a league runner for league #$ID may still run (pgrep exit $found)"; return 1; }
}
# name|MiB|start (GPU in $g)|stop   (sizes as tools/v3/late-ember/locals.sh)
OPPS=(
  "Cygnet (Gemma 4 12B)|36000|CYGNET_GPU=\$g CYGNET_UTIL=0.34 $S/cygnet.sh start|$S/cygnet.sh stop"
  "Winnow-12B|30000|WINNOW_GPU=\$g $S/winnow.sh start|$S/winnow.sh stop"
  "Decider Flash v1.2|30000|DECIDER_V12_GPU=\$g $S/decider-v1.2.sh flash start|$S/decider-v1.2.sh flash stop"
  "Decider v1.2 27B|56000|DECIDER_V12_GPU=\$g $S/decider-v1.2.sh 27b start|$S/decider-v1.2.sh 27b stop"
  "Fastino GLiDE v1.2 (local)|56000|GLIDE_GPU=\$g $S/glide-v12.sh start|$S/glide-v12.sh stop"
  "Clef|57000|CLEF_GPU=\$g $S/clef.sh start|$S/clef.sh stop"
  "Open-Jev 27B v1.1|55000|OPEN_JEV_GPU=\$g $S/open-jev.sh start|$S/open-jev.sh stop"
  "Decider v1.1 27B|54000|DECIDER_GPU=\$g $S/decider.sh start|$S/decider.sh stop"
)
systemctl --user is-active -q late-startlux2b && { echo "stop the unit late-startlux2b first" >&2; exit 1; }
ID=$(python3 $T/startlux.py league-id)
[[ -n $ID ]] || { log "locals: StartLux's league is not in v3.db"; exit 1; }
finish() { systemctl --user stop $UNIT 2>/dev/null; log "locals: $1; paid opponents \$$(spent); GPU $OPP_GPU free of us ($(gpus))"; }
log "locals up: opponents one at a time on GPU $OPP_GPU (reservation $RES); StartLux at $URL"
missing=()
for o in "${OPPS[@]}"; do
  IFS='|' read -r name need start stop <<<"$o"
  [[ $(python3 $T/startlux.py pending "$name") == 0 ]] && continue
  guard || { finish "stopped by the guard"; exit 1; }
  quiesce || { finish "aborted before starting $name: league #$ID not confirmed stopped"; exit 1; }
  until (( $(room "$OPP_GPU") >= need + 2000 )); do sleep 60; done
  if ! agent-bus run "$RES" -- bash -c "g=$OPP_GPU; $start" >> $ST/servers.log 2>&1; then
    bash -c "$stop" >> $ST/servers.log 2>&1
    log "locals: $name did not start on GPU $OPP_GPU (state/servers.log); its pair stays missing"
    missing+=("$name"); continue
  fi
  log "locals: started $name on GPU $OPP_GPU ($(gpus))"
  if ! sqlite3 -readonly v3.db "SELECT 1 FROM league_players lp JOIN players p ON p.id = lp.player_id
       WHERE lp.league_id = $ID AND lp.left_at IS NULL AND p.name = '$name'" | grep -q 1; then
    entry=$(sqlite3 -readonly v3.db "SELECT settings FROM players WHERE name = '$name'")
    quiesce || { bash -c "$stop" >> $ST/servers.log 2>&1; finish "aborted before adding $name: league #$ID not confirmed stopped"; exit 1; }
    "$BIN" league-add --db v3.db --league "$ID" --entry "$entry" >> late-startlux2b.log 2>&1 ||
      { log "locals: league-add of $name failed"; bash -c "$stop" >> $ST/servers.log 2>&1; missing+=("$name"); continue; }
    log "locals: $name added to league #$ID"
  fi
  # Played, or given up after 4 h with the pair still open (an aborted match is retried by the league runner).
  t0=$SECONDS
  until [[ $(python3 $T/startlux.py pending "$name") == 0 ]] || (( SECONDS - t0 > 14400 )); do
    guard || { bash -c "$stop" >> $ST/servers.log 2>&1; finish "stopped by the guard during $name"; exit 1; }
    ensure_league; sleep 60
  done
  bash -c "$stop" >> $ST/servers.log 2>&1
  if [[ $(python3 $T/startlux.py pending "$name") == 0 ]]; then
    log "locals: $name played; its server stopped"
  else
    log "locals: $name not played within 4 h; its server stopped, pair missing"; missing+=("$name")
  fi
done
finish "done${missing:+; missing: ${missing[*]}}"
