#!/usr/bin/env bash
# Early start of one setup's League 2 pairs for a coming ladder round (approved by Can), in a hidden
# league that plays only that setup's pairs (CONFIG sets only_pairs_of and hidden). Starts it into
# v3.db, or resumes it once it exists:
#   systemd-run --user --unit=league2early --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_league2_early.sh "SETUP" CONFIG >> league2-early.log 2>&1'
# Early starts so far: round 3, Gemini 4 Argon (off), leagues/league2-argon-early.json (2026-10-25);
# round 5, Celeris-1 Decision, leagues/league2-celeris-early.json (2026-10-26).
SETUP=${1:?usage: $0 SETUP CONFIG}
CONFIG=${2:?usage: $0 SETUP CONFIG}
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
# Keys kept in their own files, read when the environment has none (as run_league1.sh).
[ -n "${JEV_API_KEY:-}" ] || { JEV_API_KEY="$(cat ~/code/jev/key)"; export JEV_API_KEY; }
[ -n "${FASTINO_API_KEY:-}" ] || { FASTINO_API_KEY="$(cat ~/.config/fastino/key)"; export FASTINO_API_KEY; }
[ -n "${CELERIS_API_KEY:-}" ] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
# The Grok setups have OMP refresh its xai-oauth login (`omp token`).
export PATH=$HOME/.local/bin:$PATH
BIN=./target/early/release/jevgammon
ID=$(sqlite3 v3.db "SELECT id FROM leagues WHERE hidden = 1 AND only_pairs_of = '${SETUP//\'/\'\'}' AND status <> 'finished'" 2>/dev/null)
if [ -n "$ID" ]; then
  exec "$BIN" league --resume "$ID" --db v3.db
fi
exec "$BIN" league --config "$CONFIG" --db v3.db
