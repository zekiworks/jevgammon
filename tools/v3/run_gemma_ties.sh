#!/usr/bin/env bash
# Gemma 4 31B (on)'s two remaining ties (Can's go 2026-10-28), one ChatGPT job at a time, on bariton GPU 3 shared
# with Can's ComfyUI (never stopped or restarted): waits until no late-entry match of hidden league #9 runs (the
# ChatGPT subscription is then free), starts the Gemma server at GEMMA_UTIL (default 0.6, the single server's default; fp8 weights), plays Hype Cup QF1
# (leagues/cup-2026-10-28-qf1.json, v3.db) and then the Nackgammon knockout QF1 (knockout-nack.db), stops the server.
# A watchdog stops Gemma at once when GPU 3's free memory falls below MIN_FREE_MIB (ComfyUI growing) and writes
# mailbox/Gemma on GPU 3 - stopped.md.
#   systemd-run --user --unit=gemma-ties --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_gemma_ties.sh >> gemma-ties.log 2>&1'
set -uo pipefail
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
export PATH=$HOME/.local/bin:$PATH
UTIL=${GEMMA_UTIL:-0.6}
MIN_FREE_MIB=${MIN_FREE_MIB:-2048}
log() { echo "$(date -u +%FT%TZ) $*"; }
gemma() { GEMMA_GPUS=3 GEMMA_UTIL=$UTIL tools/v3/servers/gemma4-31b-replicas.sh "$1"; }
free_mib() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i 3; }

while [ "$(sqlite3 -readonly v3.db "SELECT COUNT(*) FROM matches WHERE stage = 'late-entry' AND status = 'running'")" != 0 ]; do
  sleep 60
done
log "ChatGPT free (no late-entry match running); GPU 3 free $(free_mib) MiB; starting Gemma at $UTIL"
gemma start || { log "Gemma failed to start"; gemma stop; exit 1; }
log "Gemma up; GPU 3 free $(free_mib) MiB"

( while sleep 30; do
    f=$(free_mib)
    if [ "$f" -lt "$MIN_FREE_MIB" ]; then
      log "GPU 3 free memory $f MiB < $MIN_FREE_MIB: stopping Gemma (ComfyUI keeps running)"
      gemma stop
      printf '# Gemma on GPU 3: stopped\n\n%s UTC: GPU 3 free memory fell to %s MiB (Can'"'"'s ComfyUI shares it); the Gemma server was stopped at once. ComfyUI untouched. The running tie resumes from its last stored turn when Gemma is up again.\n' "$(date -u '+%F %H:%M')" "$f" > "mailbox/Gemma on GPU 3 - stopped.md"
      pkill -f "jevgammon league --config leagues/cup-2026-10-28-qf1.json" ; pkill -f "knockout-nack/QF1.json"
      exit 0
    fi
  done ) &
WATCH=$!

ID=$(sqlite3 -readonly v3.db "SELECT id FROM leagues WHERE note LIKE 'Hype Cup 2026-10-28, quarter-final 1 %' ORDER BY id DESC LIMIT 1")
if [ -z "$ID" ]; then
  log "Cup QF1 starts"
  ./target/knockout/release/jevgammon league --config leagues/cup-2026-10-28-qf1.json --db v3.db >> cup-2026-10-28.log 2>&1
else
  log "Cup QF1 resumes (league #$ID)"
  ./target/knockout/release/jevgammon league --resume "$ID" --db v3.db >> cup-2026-10-28.log 2>&1
fi
log "Cup QF1 ended (exit $?)"
tools/v3/run_knockout_nack.sh --only QF1 >> knockout-nack.log 2>&1
log "knockout QF1 ended (exit $?)"
kill "$WATCH" 2>/dev/null
gemma stop
log "Gemma stopped; GPU 3 free $(free_mib) MiB"
