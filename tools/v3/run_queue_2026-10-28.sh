#!/usr/bin/env bash
# Season2's remaining queue (Can's go 2026-10-28; one job per subscription at a time). Replaces
# run_after_grok_2026-10-28.sh. Each step writes a one-line status to "mailbox/Season2 queue - status.md".
#   1. Wait until no late-entry match runs (Astra (high) v Grok (low)/(high)); then the xAI effort sweep starts in the
#      background (xAI only).
#   2. Wait for gemma-ties (ChatGPT + GPU 3: Cup QF1, knockout QF1) and the xAI sweep; knockout QF3 (ChatGPT + xAI).
#   3. Wait for the Claude sweep; knockout semi-finals and final (ChatGPT, Claude, maybe xAI/Gemma). If Gemma 4 31B (on)
#      is still in, its server is started on GPU 3 (fraction 0.6, shared with Can's ComfyUI) for these ties only.
#   4. GPU 3 release posted on the agent bus once no Gemma tie is left.
#   5. Codex (ChatGPT) effort sweep.
#   6. Kimi K3.1 Pro (off) v GPT-6 Astra (high), last: only if OpenRouter /api/v1/credits shows >= $0.61 free (Kimi
#      keeps its budget ledger cap); otherwise mailbox/Kimi match - waiting for credit.md and stop.
#   systemd-run --user --unit=season2-queue --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_queue_2026-10-28.sh >> season2-queue.log 2>&1'
set -uo pipefail
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
export PATH=$HOME/.local/bin:$PATH
STATUS="mailbox/Season2 queue - status.md"
[ -f "$STATUS" ] || printf '# Season2 queue: status (one line per step start and end, UTC)\n\n' > "$STATUS"
log() { echo "$(date -u +%FT%TZ) $*"; echo "- $(date -u '+%F %H:%M') $*" >> "$STATUS"; }
active() { systemctl --user is-active -q "$1"; }
late_running() { sqlite3 -readonly v3.db "SELECT COUNT(*) FROM matches WHERE stage = 'late-entry' AND status = 'running'"; }
gemma() { GEMMA_GPUS=3 GEMMA_UTIL=0.6 tools/v3/servers/gemma4-31b-replicas.sh "$1"; }

# 1. xAI sweep after the Grok matches.
while [ "$(late_running)" != 0 ]; do sleep 60; done
log "Grok matches ended; xAI effort sweep starts (log smoke/effort-sweep-xai.log)"
( workspace/sweep_run.sh xai >/dev/null 2>&1; log "xAI effort sweep ended (exit $?)" ) &
XAI=$!

# 2. Knockout QF3 after the Gemma ties and the xAI sweep.
while active gemma-ties; do sleep 60; done
wait "$XAI"
log "knockout QF3 starts (ChatGPT + xAI; log knockout-nack/QF3.log)"
tools/v3/run_knockout_nack.sh --only QF3 >> knockout-nack.log 2>&1
log "knockout QF3 ended (exit $?)"

# 3. Semi-finals and final after the Claude sweep.
while active sweep-claude; do sleep 60; done
GEMMA_IN=$(python3 - <<'PY'
import sqlite3
c = sqlite3.connect("file:knockout-nack.db?mode=ro", uri=True)
r = c.execute("""SELECT m.winner, v.model1, v.model2 FROM league_match_view v JOIN matches m ON m.id = v.match_id
                 JOIN leagues l ON l.id = v.league_id WHERE l.note LIKE 'Nackgammon knockout QF1:%'""").fetchone()
print(1 if r and r[0] and r[r[0]] == "Gemma 4 31B (on)" else 0)
PY
)
if [ "$GEMMA_IN" = 1 ]; then
  log "Gemma 4 31B (on) won knockout QF1: Gemma server starts on GPU 3 for the semi-final (free $(nvidia-smi --query-gpu=memory.free --format=csv,noheader -i 3))"
  gemma start || log "Gemma failed to start"
fi
log "knockout semi-finals and final start (log knockout-nack.log)"
tools/v3/run_knockout_nack.sh >> knockout-nack.log 2>&1
log "knockout ended (exit $?): $(tail -1 knockout-nack.log)"
[ "$GEMMA_IN" = 1 ] && gemma stop

# 4. GPU 3 release.
~/agent-bus/bus send --as jevgammon compactor "jevgammon: bariton GPU 3 released (Gemma 4 31B server stopped; Hype Cup and Nackgammon knockout ties done). Can's ComfyUI on it untouched. Nothing of ours on any GPU." >/dev/null 2>&1
log "GPU 3 release posted on the agent bus"

# 5. Codex sweep.
log "Codex effort sweep starts (log smoke/effort-sweep-codex.log)"
workspace/sweep_run.sh codex >/dev/null 2>&1
log "Codex effort sweep ended (exit $?)"

# 6. Kimi v Astra (high), last, after a credit check.
FREE=$(curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
       python3 -c 'import json, sys; d = json.load(sys.stdin)["data"]; print(round(d["total_credits"] - d["total_usage"], 4))')
if python3 -c "import sys; sys.exit(0 if float('${FREE:-0}') >= 0.61 else 1)"; then
  log "OpenRouter credit \$$FREE free (>= \$0.61): Kimi K3.1 Pro (off) v GPT-6 Astra (high) starts (league #9)"
  E=$(sqlite3 -readonly v3.db "SELECT settings FROM players WHERE name = 'Kimi K3.1 Pro (off)'")
  ./target/knockout/release/jevgammon league-add --db v3.db --league 9 --entry "$E" >> league3-astra-high.log 2>&1
  ./target/knockout/release/jevgammon league --resume 9 --db v3.db >> league3-astra-high.log 2>&1
  log "Kimi match ended (exit $?); OpenRouter credit now \$$(curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" | python3 -c 'import json, sys; d = json.load(sys.stdin)["data"]; print(round(d["total_credits"] - d["total_usage"], 4))')"
else
  printf '# Kimi match: waiting for credit\n\n%s UTC: OpenRouter shows $%s free, below the $0.61 worst case of Kimi K3.1 Pro (off) v GPT-6 Astra (high). The match was not started. Start it with tools/v3/run_queue_2026-10-28.sh step 6 after a top-up.\n' "$(date -u '+%F %H:%M')" "$FREE" > "mailbox/Kimi match - waiting for credit.md"
  log "Kimi match NOT started: OpenRouter credit \$$FREE < \$0.61 (mailbox/Kimi match - waiting for credit.md)"
fi
log "queue done"
