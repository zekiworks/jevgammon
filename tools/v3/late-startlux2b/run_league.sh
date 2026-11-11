#!/usr/bin/env bash
# StartLux-Decision v1.1 2B's late-entry league, as tools/v3/late-ember/run_league.sh: starts it from its config, or
# resumes it once v3.db has it (league --resume ID, which also plays pairs added by league-add). Started by start.sh as
# the user unit late-startlux2b-league; log late-startlux2b.log in the main checkout.
set -euo pipefail
cd /home/cbasaran/code/jevgammon
BIN=$1
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
CONFIG=workspace/late-startlux2b/leagues/startlux-decision-v1.1-2b.json
ID=$(python3 "$T/startlux.py" league-id)
exec >> late-startlux2b.log 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
