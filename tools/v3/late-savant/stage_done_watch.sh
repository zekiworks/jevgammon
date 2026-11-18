#!/usr/bin/env bash
# Stage-done watcher of the SubQ Savant 1.4 late entry, as workspace/stage-done-watch.sh for this entry's units: every
# 5 min, once the 9 required first-stage pairs are played (savant.py pending: the programs and the paid APIs, GPT-6
# Luna and Mercury Decide not required), stops late-savant-league and late-savant and exits, logged in the status file;
# also exits, logged, when late-savant is no longer active (start.sh finished or the guard stopped it).
#   systemd-run --user --unit=late-savant-watch --working-directory=/home/cbasaran/code/jevgammon \
#     /home/cbasaran/code/jevgammon-late-savant/tools/v3/late-savant/stage_done_watch.sh
cd /home/cbasaran/code/jevgammon || exit 1
T=$(dirname "$(readlink -f "$0")")
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/player.json")
STATUS="mailbox/Late entry $NAME - status.md"
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "SubQ Snap Preview")
log() { echo "- $(date -u +%FT%TZ) watch: $*" >> "$STATUS"; echo "$*"; }
while :; do
  n=$(python3 "$T/savant.py" pending "${OPPS[@]}")
  if [[ $n == 0 ]]; then
    systemctl --user stop late-savant-league late-savant
    log "STAGE DONE: all 9 required first-stage pairs of $NAME played; late-savant-league and late-savant stopped"; exit 0
  fi
  if ! systemctl --user is-active -q late-savant; then
    log "late-savant no longer active with ${n:-?} required first-stage pairs open: $(tail -1 "$STATUS" | cut -c1-200)"; exit 1
  fi
  sleep 300
done
