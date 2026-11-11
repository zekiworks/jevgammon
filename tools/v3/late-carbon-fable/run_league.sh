#!/usr/bin/env bash
# The late-entry league of ENTRANT (carbon | fable), as tools/v3/late-knowline4b/run_league.sh: starts it from its
# config, or resumes it once v3.db has it (league --resume ID, which also plays pairs added by league-add). Started by
# start.sh as the user unit late-<ENTRANT>-league; log late-<ENTRANT>.log in the main checkout.
set -euo pipefail
cd /home/cbasaran/code/jevgammon
ENTRANT=$1
BIN=$2
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
case $ENTRANT in
  carbon) CONFIG=workspace/late-carbon-fable/carbon/leagues/gemini-4-carbon-high.json ;;
  fable) CONFIG=workspace/late-carbon-fable/fable/leagues/claude-fable-5.2-max.json ;;
  *) echo "ENTRANT: carbon or fable" >&2; exit 2 ;;
esac
ID=$(python3 "$T/late.py" "$ENTRANT" league-id)
exec >> "late-$ENTRANT.log" 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
