#!/usr/bin/env bash
# Starts League 3 into v3.db (log: league3.log), or resumes it once it exists:
#   systemd-run --user --unit=league3 --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_league3.sh >> league3.log 2>&1'
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
# The Grok setups have OMP refresh its xai-oauth login (`omp token`).
export PATH=$HOME/.local/bin:$PATH
if sqlite3 v3.db "SELECT 1 FROM leagues WHERE id = 3" 2>/dev/null | grep -q 1; then
  exec ./target/release/jevgammon league --resume 3 --db v3.db
fi
exec ./target/release/jevgammon league --config leagues/league3.json --db v3.db
