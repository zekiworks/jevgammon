#!/usr/bin/env bash
# Schedule after GPT-6 Astra (high)'s Grok matches (Can's go 2026-10-28; one job per subscription at a time):
#  1. when no late-entry match runs: xAI is free -> the xAI effort sweep (workspace/sweep_run.sh xai);
#  2. when both the xAI sweep and tools/v3/run_gemma_ties.sh (unit gemma-ties, ChatGPT) have ended: the Nackgammon
#     knockout QF3 (ChatGPT + xAI), then the full knockout run (semi-finals and final; Claude ties wait for the
#     Claude sweep, unit sweep-claude, to end).
#   systemd-run --user --unit=after-grok --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_after_grok_2026-10-28.sh >> after-grok.log 2>&1'
set -uo pipefail
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
export PATH=$HOME/.local/bin:$PATH
log() { echo "$(date -u +%FT%TZ) $*"; }
active() { systemctl --user is-active -q "$1"; }

while [ "$(sqlite3 -readonly v3.db "SELECT COUNT(*) FROM matches WHERE stage = 'late-entry' AND status = 'running'")" != 0 ]; do
  sleep 60
done
log "xAI free: effort sweep xai starts"
workspace/sweep_run.sh xai
log "effort sweep xai ended (exit $?)"
while active gemma-ties; do sleep 60; done
log "ChatGPT free (gemma-ties ended): knockout QF3"
tools/v3/run_knockout_nack.sh --only QF3 >> knockout-nack.log 2>&1
log "knockout QF3 ended (exit $?)"
while active sweep-claude; do sleep 60; done
log "Claude free: knockout semi-finals and final"
tools/v3/run_knockout_nack.sh >> knockout-nack.log 2>&1
log "knockout ended (exit $?)"
