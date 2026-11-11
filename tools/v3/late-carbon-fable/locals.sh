#!/usr/bin/env bash
# Stage 2 of ENTRANT's late entry (carbon | fable): the 8 local League 1 opponents, one opponent server at a time on
# OPP_GPU under the bus reservation RES (only once Main hands over a free card), as tools/v3/late-knowline4b/locals.sh.
# For each opponent whose pair is unplayed: waits until OPP_GPU has room for it (+2 GB; a GPU held by someone else is
# waited for, never freed), starts its server with `agent-bus run RES -- ...`, league-adds it to the entrant's league,
# waits until the pair is played, stops the server. It keeps start.sh's guard (OpenRouter balance >= $40 and readable,
# paid opponents < $5, carbon: own cost < $OWN_CAP; fable: the Claude lane not running; the entrant's route not at its limit)
# itself, so the unit late-<ENTRANT> (start.sh) must have exited first. Before each opponent's server starts and before
# its league-add, quiesce() confirms nothing plays the entrant's league; any failure aborts the run there, logged.
#   systemd-run --user --unit=late-carbon-locals --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E OPP_GPU=<n> -E RES=<reservation> \
#     /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/locals.sh carbon
set -uo pipefail
cd /home/cbasaran/code/jevgammon
export PATH=$HOME/.local/bin:$PATH  # agent-bus
ENTRANT=${1:-}
T=$(dirname "$(readlink -f "$0")")
case $ENTRANT in
  carbon) NAME="Gemini 4 Carbon (high)"; CFG=gemini-4-carbon-high; LANES=(); OWN_CAP=${OWN_CAP:-250} ;;
  fable) NAME="Claude Fable 5.2 (max)"; CFG=claude-fable-5\.2-max; LANES=(improve-subs-claude improve-claude-wait)
         OWN_CAP= ;;
  *) echo "usage: locals.sh carbon|fable" >&2; exit 2 ;;
esac
W=workspace/late-carbon-fable/$ENTRANT
ST=$W/state
S=tools/v3/servers
BIN=/home/cbasaran/code/jevgammon/target/carbon-fable/release/jevgammon
STATUS="mailbox/Late entries $NAME - status.md"
UNIT=late-$ENTRANT-league
FLOOR=40
CAP=5
: "${OPP_GPU:?}" "${RES:?}"
L() { python3 "$T/late.py" "$ENTRANT" "$@"; }
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$ST/locals.log"; echo "- $line" >> "$STATUS"; }
room() { nvidia-smi -i "$1" --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print $1-$2}'; }
gpus() { nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { L billed "$(cat "$ST/first")"; }
lane_up() { local u; for u in "${LANES[@]}"; do systemctl --user is-active -q "$u" && { echo "$u"; return 0; }; done; return 1; }
# Guard; returns 1 (and logs) when the run must stop.
unread=0
guard() {
  local bal s lane hit
  if lane=$(lane_up); then log "locals PAUSED: $lane started (it keeps the subscription)"; return 1; fi
  if hit=$(L limited "$(cat "$ST/first")") && [[ -n $hit ]]; then
    log "locals PAUSED: $NAME's route at its limit ($hit)"; return 1
  fi
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then log "locals STOPPED: OpenRouter balance \$$bal under \$$FLOOR"; return 1; fi
  else
    unread=$((unread + 1))
    (( unread < 3 )) || { log "locals STOPPED: OpenRouter balance unreadable 3 times in a row"; return 1; }
  fi
  s=$(spent)
  lt "$s" "$CAP" || { log "locals STOPPED: paid opponents \$$s reached the \$$CAP cap"; return 1; }
  if [[ -n $OWN_CAP ]] && ! lt "$(L owncost "$(cat "$ST/first")")" "$OWN_CAP"; then
    log "locals STOPPED: $NAME's own cost reached the \$$OWN_CAP cap: $(L own "$(cat "$ST/first")")"; return 1
  fi
}
ensure_league() {
  systemctl --user is-active -q "$UNIT" && return 0
  systemctl --user reset-failed "$UNIT" >/dev/null 2>&1 || true
  systemd-run --user --quiet --unit="$UNIT" --working-directory="$PWD" "$T/run_league.sh" "$ENTRANT" "$BIN"
}
# Stops the league unit and confirms nothing can play league #ID (as late-knowline4b/locals.sh quiesce): the stop
# succeeded (or the unit is not loaded: LoadState not-found); the unit is inactive or failed; pgrep finds no league
# runner for it (pgrep exit 1 = none, 0 = found, anything else = unknown). Returns 1, logged, otherwise.
quiesce() {
  local load state found
  if ! systemctl --user stop "$UNIT" 2>/dev/null; then
    load=$(systemctl --user show -p LoadState --value "$UNIT" 2>/dev/null)
    [[ $load == not-found ]] || { log "locals: stopping $UNIT failed (LoadState ${load:-unknown})"; return 1; }
  fi
  state=$(systemctl --user is-active "$UNIT" 2>/dev/null)
  [[ $state == inactive || $state == failed ]] || { log "locals: $UNIT is ${state:-of unknown state} after the stop"; return 1; }
  pgrep -f -- "late-carbon-fable/run_league\.sh $ENTRANT|league --resume $ID --db|league --config [^ ]*$CFG\.json" \
    >/dev/null 2>&1
  found=$?
  (( found == 1 )) || { log "locals: a league runner for league #$ID may still run (pgrep exit $found)"; return 1; }
}
# name|MiB|start (GPU in $g)|stop   (sizes as tools/v3/late-knowline4b/locals.sh)
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
systemctl --user is-active -q "late-$ENTRANT" && { echo "stop the unit late-$ENTRANT first" >&2; exit 1; }
[[ -e $ST/first ]] || { echo "start.sh $ENTRANT has not run yet (no $ST/first)" >&2; exit 1; }
ID=$(L league-id)
[[ -n $ID ]] || { log "locals: $NAME's league is not in v3.db"; exit 1; }
finish() { systemctl --user stop "$UNIT" 2>/dev/null; log "locals: $1; paid opponents \$$(spent); GPU $OPP_GPU free of us ($(gpus))"; }
log "locals up: opponents one at a time on GPU $OPP_GPU (reservation $RES); $NAME"
missing=()
for o in "${OPPS[@]}"; do
  IFS='|' read -r name need start stop <<<"$o"
  [[ $(L pending "$name") == 0 ]] && continue
  guard || { finish "stopped by the guard"; exit 1; }
  quiesce || { finish "aborted before starting $name: league #$ID not confirmed stopped"; exit 1; }
  until (( $(room "$OPP_GPU") >= need + 2000 )); do sleep 60; done
  if ! agent-bus run "$RES" -- bash -c "g=$OPP_GPU; $start" >> "$ST/servers.log" 2>&1; then
    bash -c "$stop" >> "$ST/servers.log" 2>&1
    log "locals: $name did not start on GPU $OPP_GPU (state/servers.log); its pair stays missing"
    missing+=("$name"); continue
  fi
  log "locals: started $name on GPU $OPP_GPU ($(gpus))"
  if ! sqlite3 -readonly v3.db "SELECT 1 FROM league_players lp JOIN players p ON p.id = lp.player_id
       WHERE lp.league_id = $ID AND lp.left_at IS NULL AND p.name = '$name'" | grep -q 1; then
    entry=$(sqlite3 -readonly v3.db "SELECT settings FROM players WHERE name = '$name'")
    quiesce || { bash -c "$stop" >> "$ST/servers.log" 2>&1; finish "aborted before adding $name: league #$ID not confirmed stopped"; exit 1; }
    "$BIN" league-add --db v3.db --league "$ID" --entry "$entry" >> "late-$ENTRANT.log" 2>&1 ||
      { log "locals: league-add of $name failed"; bash -c "$stop" >> "$ST/servers.log" 2>&1; missing+=("$name"); continue; }
    log "locals: $name added to league #$ID"
  fi
  # Played, or given up after 8 h with the pair still open (an aborted match is retried by the league runner).
  t0=$SECONDS
  until [[ $(L pending "$name") == 0 ]] || (( SECONDS - t0 > 28800 )); do
    guard || { bash -c "$stop" >> "$ST/servers.log" 2>&1; finish "stopped by the guard during $name"; exit 1; }
    ensure_league; sleep 60
  done
  bash -c "$stop" >> "$ST/servers.log" 2>&1
  if [[ $(L pending "$name") == 0 ]]; then
    log "locals: $name played; its server stopped"
  else
    log "locals: $name not played within 8 h; its server stopped, pair missing"; missing+=("$name")
  fi
done
finish "done${missing:+; missing: ${missing[*]}}"
