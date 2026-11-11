#!/usr/bin/env bash
# A repeat's league (tools/v3/repeats), as tools/v3/late-knowline/run_league.sh: starts it from its config, or resumes it
# once v3.db has it (league --resume ID, which also plays pairs added by league-add). Started by run.sh as the user unit
# repeat-ID-league with the checked runner build and run.sh's database; log repeat-ID.log in its working directory.
set -euo pipefail
RID=$1 BIN=$2
export JEVGAMMON_DB=$3
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
ID=$(python3 "$T/repeats.py" league-id "$RID")
exec >> "repeat-$RID.log" 2>&1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db "$JEVGAMMON_DB"
fi
exec "$BIN" league --config "$T/leagues/$RID.json" --db "$JEVGAMMON_DB"
