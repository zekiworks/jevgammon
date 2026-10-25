#!/usr/bin/env bash
# Early start for ladder round 3 (approved by Can, 2026-10-25): Gemini 4 Argon (off)'s League 2 pairs
# in a hidden league that plays only its pairs (leagues/league2-argon-early.json). Starts it into
# v3.db (log: league2-early.log), or resumes it once it exists:
#   systemd-run --user --unit=league2early --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_league2_early.sh >> league2-early.log 2>&1'
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
# The Grok setups have OMP refresh its xai-oauth login (`omp token`).
export PATH=$HOME/.local/bin:$PATH
BIN=./target/early/release/jevgammon
ID=$(sqlite3 v3.db "SELECT id FROM leagues WHERE hidden = 1 AND only_pairs_of = 'Gemini 4 Argon (off)'" 2>/dev/null)
if [ -n "$ID" ]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config leagues/league2-argon-early.json --db v3.db
