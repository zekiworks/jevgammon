#!/usr/bin/env bash
# Gemini Decision 1's late-entry league, as tools/v3/late-tiny8/run_league.sh: starts it from its config, or resumes it
# once v3.db has it (league --resume ID, which also plays pairs added by league-add). Started by start.sh (and
# locals.sh) as the user unit late-gemini-decision-league; log late-gemini-decision.log in the main checkout.
#   run_league.sh BIN
set -euo pipefail
cd /home/cbasaran/code/jevgammon
BIN=$1
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
CONFIG=workspace/late-gemini-decision/leagues/gemini-decision-1.json
ID=$(python3 "$T/gemini.py" league-id)
exec >> late-gemini-decision.log 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
