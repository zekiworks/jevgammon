#!/usr/bin/env bash
# KnowLine 31B Gen1.5 v the 8 local League 1 opponents, one opponent server at a time on OPP_GPU under the bus
# reservation RES (only once Main hands over a free card), as tools/v3/late-ember/locals.sh. KnowLine itself stays on
# its own server (player.json base_url). For each opponent whose pair is unplayed: stops the league unit and confirms
# nothing plays league #ID (quiesce; any failure aborts the run before league-add and server launch, logged),
# league-adds it to KnowLine's league, checks the guard, waits until
# OPP_GPU has room for it (+2 GB; a GPU held by someone else is waited for, never freed), starts its server with
# `agent-bus run RES -- ...`, (re)starts the league unit, waits until the pair is played, stops the server. A server
# that does not start leaves its pair in the league, unplayed and reported missing (the league's warm-up fails against
# it, unbilled). It keeps start.sh's guard (OpenRouter balance >= $40 and readable, paid opponents < $5, KnowLine
# server healthy) itself, so the unit late-knowline (start.sh) must have exited first. The one exception (Zeki #4621,
# review #4626): the balance check is skipped while `knowline.py local-only` proves from the recorded settings that
# KnowLine's league #21 exists, KnowLine and the current opponent are active members, and KnowLine, the opponent and
# every other open pair are on their exact known routes (KnowLine on spark2 as player.json; each of the 8 opponents on
# its own server script's loopback port on bariton); anything else keeps the check (the open Mercury Decide pair too).
#   systemd-run --user --unit=late-knowline-locals --working-directory=/home/cbasaran/code/jevgammon \
#     -E OPP_GPU=<n> -E RES=<reservation> /home/cbasaran/code/jevgammon-knowline/tools/v3/late-knowline/locals.sh
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-knowline
ST=$W/state
S=tools/v3/servers
BIN=/home/cbasaran/code/jevgammon/target/knowline/release/jevgammon
STATUS="mailbox/Late entries KnowLine - status.md"
UNIT=late-knowline-league
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
spent() { python3 $T/knowline.py billed "$(cat $ST/first)"; }
healthy() { curl -fsS -m 10 -o /dev/null "$URL/health"; }
# Guard; returns 1 (and logs) when the run must stop. `current`: the opponent whose pair is being played.
down=0
unread=0
current=
exempt_for=
guard() {
  local bal s why
  if [[ -n $current ]] && why=$(python3 $T/knowline.py local-only "$current" 2>&1); then
    if [[ $exempt_for != "$current" ]]; then
      log "locals: OpenRouter balance check skipped for KnowLine v $current, our hardware only (Zeki #4621): $(tr '\n' ' ' <<<"$why")"
      exempt_for=$current
    fi
    unread=0
  else
    exempt_for=
    if bal=$(balance); then
      unread=0
      if lt "$bal" "$FLOOR"; then log "locals STOPPED: OpenRouter balance \$$bal under \$$FLOOR"; return 1; fi
    else
      unread=$((unread + 1))
      (( unread < 3 )) || { log "locals STOPPED: OpenRouter balance unreadable 3 times in a row"; return 1; }
    fi
  fi
  s=$(spent)
  lt "$s" "$CAP" || { log "locals STOPPED: paid opponents \$$s reached the \$$CAP cap"; return 1; }
  if healthy; then down=0; else down=$((down + 1)); fi
  (( down < 3 )) || { log "locals STOPPED: KnowLine server $URL failed 3 health checks in a row"; return 1; }
}
ensure_league() {
  systemctl --user is-active -q $UNIT && return 0
  systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
  systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
}
# Stops the league unit and confirms nothing can play league #ID (Zeki #4628): the stop succeeded (or the unit is not
# loaded at all: systemd then refuses the stop, exit 5, LoadState not-found); systemctl reports the unit inactive or
# failed; and pgrep finds no league runner for it (run_league.sh, `league --resume ID --db`, `league --config` of
# KnowLine's config; pgrep exit 1 = none, 0 = found, anything else = unknown). Returns 1, logged, otherwise.
quiesce() {
  local load state found
  if ! systemctl --user stop $UNIT 2>/dev/null; then
    load=$(systemctl --user show -p LoadState --value $UNIT 2>/dev/null)
    [[ $load == not-found ]] || { log "locals: stopping $UNIT failed (LoadState ${load:-unknown})"; return 1; }
  fi
  state=$(systemctl --user is-active $UNIT 2>/dev/null)
  [[ $state == inactive || $state == failed ]] || { log "locals: $UNIT is ${state:-of unknown state} after the stop"; return 1; }
  pgrep -f -- "late-knowline/run_league\.sh|league --resume $ID --db|league --config [^ ]*knowline-31b-gen1\.5\.json" \
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
systemctl --user is-active -q late-knowline && { echo "stop the unit late-knowline first" >&2; exit 1; }
ID=$(python3 $T/knowline.py league-id)
[[ -n $ID ]] || { log "locals: KnowLine's league is not in v3.db"; exit 1; }
finish() { systemctl --user stop $UNIT 2>/dev/null; log "locals: $1; paid opponents \$$(spent); GPU $OPP_GPU free of us ($(gpus))"; }
log "locals up: opponents one at a time on GPU $OPP_GPU (reservation $RES); KnowLine at $URL"
missing=()
for o in "${OPPS[@]}"; do
  IFS='|' read -r name need start stop <<<"$o"
  current=$name
  [[ $(python3 $T/knowline.py pending "$name") == 0 ]] && continue
  quiesce || { finish "aborted before adding $name: league #$ID not confirmed stopped"; exit 1; }
  if ! sqlite3 -readonly v3.db "SELECT 1 FROM league_players lp JOIN players p ON p.id = lp.player_id
       WHERE lp.league_id = $ID AND lp.left_at IS NULL AND p.name = '$name'" | grep -q 1; then
    entry=$(sqlite3 -readonly v3.db "SELECT settings FROM players WHERE name = '$name'")
    "$BIN" league-add --db v3.db --league "$ID" --entry "$entry" >> late-knowline.log 2>&1 ||
      { log "locals: league-add of $name failed"; missing+=("$name"); continue; }
    log "locals: $name added to league #$ID"
  fi
  guard || { finish "stopped by the guard"; exit 1; }
  until (( $(room "$OPP_GPU") >= need + 2000 )); do sleep 60; done
  if ! agent-bus run "$RES" -- bash -c "g=$OPP_GPU; $start" >> $ST/servers.log 2>&1; then
    bash -c "$stop" >> $ST/servers.log 2>&1
    log "locals: $name did not start on GPU $OPP_GPU (state/servers.log); its pair stays missing"
    missing+=("$name"); continue
  fi
  log "locals: started $name on GPU $OPP_GPU ($(gpus))"
  # Played, or given up after 4 h with the pair still open (an aborted match is retried by the league runner).
  t0=$SECONDS
  until [[ $(python3 $T/knowline.py pending "$name") == 0 ]] || (( SECONDS - t0 > 14400 )); do
    guard || { bash -c "$stop" >> $ST/servers.log 2>&1; finish "stopped by the guard during $name"; exit 1; }
    ensure_league; sleep 60
  done
  bash -c "$stop" >> $ST/servers.log 2>&1
  if [[ $(python3 $T/knowline.py pending "$name") == 0 ]]; then
    log "locals: $name played; its server stopped"
  else
    log "locals: $name not played within 4 h; its server stopped, pair missing"; missing+=("$name")
  fi
done
finish "done${missing:+; missing: ${missing[*]}}"
