#!/usr/bin/env bash
# One small chat setup's late-entry league (KEY: models/KEY), as tools/v3/late-tiny8/run_league.sh: starts it from its
# config, or resumes it once v3.db has it (league --resume ID, which also plays pairs added by league-add). Started by
# start.sh as the user unit late-smallchat-KEY-league; log late-smallchat-KEY.log in the main checkout.
#   run_league.sh BIN KEY
set -euo pipefail
cd /home/cbasaran/code/jevgammon
BIN=$1
KEY=$2
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH:/usr/games
CONFIG=workspace/late-smallchat/$KEY/leagues/$KEY.json
ID=$(python3 "$T/smallchat.py" "$KEY" league-id)
exec >> "late-smallchat-$KEY.log" 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
