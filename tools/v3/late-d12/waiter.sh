#!/usr/bin/env bash
# Waits for Liquid to serve the entrant's model (KEY d12 | d12-ultra), then starts its first stage (start.sh KEY as the
# unit late-KEY). Liquid answered d1.2 and d1.2-ultra with 404 "model does not exist" on 16 Nov (turkce #10929; the ids
# are Liquid's own, liquid.ai/blog/d1-2), while /decisions/v1/models did not list them. One probe decision
# (liquid12.py probe, raw reply kept in state/probes) every 10 min, at most 6 h (37 probes): answered -> start.sh;
# 404 "does not exist" -> wait; anything else -> stop, logged.
#   systemd-run --user --unit=late-KEY-waiter --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
#     /home/cbasaran/code/jevgammon-late-d12ultra/tools/v3/late-d12/waiter.sh KEY
set -uo pipefail
cd /home/cbasaran/code/jevgammon
KEY=${1:?KEY: d12 or d12-ultra}
[[ $KEY == d12 || $KEY == d12-ultra ]] || { echo "KEY must be d12 or d12-ultra" >&2; exit 1; }
export LATE_KEY=$KEY
T=$(dirname "$(readlink -f "$0")")
ST=workspace/late-$KEY/state
mkdir -p $ST
set -a; . ~/.keys; set +a
log() { echo "$(date -u +%FT%TZ) $*" >> $ST/waiter.log; }
for ((n = 1; n <= 37; n++)); do
  out=$(python3 "$T/liquid12.py" probe); rc=$?
  log "probe $n: $out"
  case $rc in
    0) echo "$(date -u +%FT%TZ) $out" > $ST/qualified
       systemctl --user reset-failed late-$KEY >/dev/null 2>&1 || true
       systemd-run --user --quiet --unit=late-$KEY --working-directory="$PWD" \
         -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin "$T/start.sh" "$KEY" &&
         { log "started unit late-$KEY"; exit 0; }
       log "STOPPED: systemd-run of late-$KEY failed"; exit 1 ;;
    2) (( n < 37 )) && sleep 600 ;;
    *) log "STOPPED: probe answered otherwise"; exit 1 ;;
  esac
done
log "STOPPED: model still absent after 6 h"
exit 1
