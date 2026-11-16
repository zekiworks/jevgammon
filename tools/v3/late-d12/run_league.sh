#!/usr/bin/env bash
# Liquid d1.2 / d1.2-ultra late-entry league (KEY d12 | d12-ultra), as tools/v3/late-gemini-decision/run_league.sh:
# starts it from its config, or resumes it once v3.db has it (league --resume ID, which also plays pairs added by
# league-add). Started by start.sh (and locals.sh) as the user unit late-KEY-league; log late-KEY.log in the main checkout.
#   run_league.sh KEY BIN
set -euo pipefail
cd /home/cbasaran/code/jevgammon
KEY=$1
BIN=$2
export LATE_KEY=$KEY
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
CONFIG=workspace/late-$KEY/leagues/liquid-$KEY.json
ID=$(python3 "$T/liquid12.py" league-id)
exec >> late-$KEY.log 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
