#!/usr/bin/env bash
# Muse Ember (max) v the 8 local League 1 opponents, one server at a time on OPP_GPU under the bus reservation RES
# (Main: bariton GPU 0, reservation r_57d739c4cd53, only once Main says the card is free), as workspace/reax/locals.sh.
# For each opponent whose pair is unplayed: waits until OPP_GPU has room for it (+2 GB; a GPU held by someone else is
# waited for, never freed), starts its server with `agent-bus run RES -- ...`, league-adds it to Ember's league, waits
# until the pair is played, stops the server. It keeps start.sh's money guard (OpenRouter balance >= $41, run cap
# $19.75; a balance unreadable 3 times in a row also stops it) itself, so the unit late-ember (start.sh) must have exited first.
#   systemd-run --user --unit=late-ember-locals --working-directory=/home/cbasaran/code/jevgammon \
#     -E OPP_GPU=0 -E RES=r_57d739c4cd53 /home/cbasaran/code/jevgammon-ember/tools/v3/late-ember/locals.sh
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-ember
ST=$W/state
S=tools/v3/servers
BIN=/home/cbasaran/code/jevgammon/target/ember/release/jevgammon
STATUS="mailbox/Late entries Muse Ember - status 2026-11-10.md"
UNIT=late-ember-league
FLOOR=41
CAP=19.75
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
spent() { python3 -c 'import sys; print(f"{float(sys.argv[1]) + float(sys.argv[2]):.4f}")' \
  "$(python3 $T/ember.py ledger)" "$(python3 $T/ember.py billed "$(cat $ST/first)")"; }
# Money guard; returns 1 (and logs) when the run must stop.
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
  lt "$s" "$CAP" || { log "locals STOPPED: run spent \$$s reached the \$$CAP cap"; return 1; }
}
ensure_league() {
  systemctl --user is-active -q $UNIT && return 0
  systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
  systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
}
# name|MiB|start (GPU in $g)|stop   (sizes as workspace/reax/locals.sh; measured on 7 Nov: 32.6, 13.4, 9.4, 50.4,
# 52.8, 53.1, 53.1, 50.4 GB)
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
systemctl --user is-active -q late-ember && { echo "stop the unit late-ember first" >&2; exit 1; }
ID=$(python3 $T/ember.py league-id)
[[ -n $ID ]] || { log "locals: Ember's league is not in v3.db"; exit 1; }
finish() { systemctl --user stop $UNIT 2>/dev/null; log "locals: $1; run spent \$$(spent); GPU $OPP_GPU free of us ($(gpus))"; }
log "locals up: opponents one at a time on GPU $OPP_GPU (reservation $RES)"
missing=()
for o in "${OPPS[@]}"; do
  IFS='|' read -r name need start stop <<<"$o"
  [[ $(python3 $T/ember.py pending "$name") == 0 ]] && continue
  guard || { finish "stopped by the money guard"; exit 1; }
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
    "$BIN" league-add --db v3.db --league "$ID" --entry "$entry" >> late-ember.log 2>&1 ||
      { log "locals: league-add of $name failed"; bash -c "$stop" >> $ST/servers.log 2>&1; missing+=("$name"); continue; }
    log "locals: $name added to league #$ID"
  fi
  # Played, or given up after 4 h with the pair still open (an aborted match is retried by the league runner).
  t0=$SECONDS
  until [[ $(python3 $T/ember.py pending "$name") == 0 ]] || (( SECONDS - t0 > 14400 )); do
    guard || { bash -c "$stop" >> $ST/servers.log 2>&1; finish "stopped by the money guard during $name"; exit 1; }
    ensure_league; sleep 60
  done
  bash -c "$stop" >> $ST/servers.log 2>&1
  if [[ $(python3 $T/ember.py pending "$name") == 0 ]]; then
    log "locals: $name played; its server stopped"
  else
    log "locals: $name not played within 4 h; its server stopped, pair missing"; missing+=("$name")
  fi
done
finish "done${missing:+; missing: ${missing[*]}}"
