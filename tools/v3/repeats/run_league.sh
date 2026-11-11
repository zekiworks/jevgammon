#!/usr/bin/env bash
# A repeat's league (tools/v3/repeats), as tools/v3/late-knowline/run_league.sh: starts it from its config, or resumes it
# once v3.db has it (league --resume ID, which also plays pairs added by league-add). repeats.py league-id never names a
# recorded attempt's league (REAX 1.3's #24), so after an attempt the config starts a new league. Started by run.sh as
# the user unit repeat-ID-league with the checked runner build, run.sh's database and the admitted-settings record of
# run.sh's check (workspace/repeats/ID/admitted.json); log repeat-ID.log in its working directory. Before the league
# starts, `repeats.py bound` compares that record with what the league will read (the config file's sha256, the config
# players' and pinned opponents' v3.db settings, read write-ahead-log-aware): any difference and no league starts.
set -euo pipefail
RID=$1 BIN=$2 ADMITTED=${4:?usage: run_league.sh ID BIN DB ADMITTED}
export JEVGAMMON_DB=$3
T=$(dirname "$(readlink -f "$0")")
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
ID=$(python3 "$T/repeats.py" league-id "$RID")
exec >> "repeat-$RID.log" 2>&1
python3 "$T/repeats.py" bound "$RID" "$ADMITTED" || exit 1
if [[ -n $ID ]]; then
  exec "$BIN" league --resume "$ID" --db "$JEVGAMMON_DB"
fi
exec "$BIN" league --config "$T/leagues/$RID.json" --db "$JEVGAMMON_DB"
