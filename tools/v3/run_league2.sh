#!/usr/bin/env bash
# Starts League 2 into v3.db (log: league2.log), or resumes it once it exists:
#   setsid nohup tools/v3/run_league2.sh >> league2.log 2>&1 < /dev/null &
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
# Keys kept in their own files, read when the environment has none (as run_league1.sh; the ladder
# moves League 1 setups such as Celeris-1 Decision into League 2).
[ -n "${JEV_API_KEY:-}" ] || { JEV_API_KEY="$(cat ~/code/jev/key)"; export JEV_API_KEY; }
[ -n "${FASTINO_API_KEY:-}" ] || { FASTINO_API_KEY="$(cat ~/.config/fastino/key)"; export FASTINO_API_KEY; }
[ -n "${CELERIS_API_KEY:-}" ] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
if sqlite3 v3.db "SELECT 1 FROM leagues WHERE id = 2" 2>/dev/null | grep -q 1; then
  exec ./target/release/jevgammon league --resume 2 --db v3.db
fi
exec ./target/release/jevgammon league --config leagues/league2-start.json --db v3.db
