#!/usr/bin/env bash
# After an Anthropic overload (529) or usage limit (429) ended the Claude lane: one probe request through Claude Fable
# 5.1's league route every INTERVAL seconds (argument 1; default 600; 1800 for a usage limit, to save quota; pinned
# runner, `jevgammon lesson`, a one-line prompt); on the first success, the Claude lane is
# restarted with its committed start command (Fable -> Opus -> Sonnet, Ümit #3465). The match itself is never looped.
#   systemd-run --user --unit improve-claude-wait workspace/improve/claude_wait_restart.sh [INTERVAL]
set -uo pipefail
INTERVAL=${1:-600}
cd "$(dirname "$0")/../.."
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
BIN=$PWD/target/improve-bin/jevgammon-1270c04
LOG=/home/cbasaran/code/jevgammon/workspace/improve/runs/claude-fable-5.1-on/log.jsonl
P=$(mktemp -d)
"$PY" -c "
import sys,json; sys.path.insert(0,'workspace/improve'); import improve as I
p=I.league_settings('Claude Fable 5.1 (on)'); p.update(name='Claude Fable 5.1 (on) | improve | probe', parallel=1); p.pop('max_matches',None)
json.dump(p, open('$P/player.json','w'))"
echo "Reply with the single word: ok" > "$P/user.txt"; echo "You are a test." > "$P/system.txt"
for i in $(seq 1 $(( 43200 / INTERVAL ))); do
  if "$BIN" lesson --player "$P/player.json" --system "$P/system.txt" --user "$P/user.txt" --out "$P/out.json" 2> "$P/err.txt"; then
    model=$("$PY" -c "import json; print(json.loads(json.load(open('$P/out.json'))['exchanges'][0]['response']).get('model'))")
    printf '{"at": "%s", "event": "provider_probe", "result": "ok", "model": "%s"}\n' "$(date -u +%FT%T+00:00)" "$model" >> "$LOG"
    echo "$(date -u +%FT%TZ) probe ok ($model): restarting the Claude lane"
    exec workspace/improve/run_lane.sh improve-subs-claude claude-fable-5.1-on claude-opus-5.5-on claude-sonnet-5.5-high
  fi
  err=$(tr -d '"\\' < "$P/err.txt" | tail -c 300)
  printf '{"at": "%s", "event": "provider_probe", "result": "failed", "error": "%s"}\n' "$(date -u +%FT%T+00:00)" "$err" >> "$LOG"
  echo "$(date -u +%FT%TZ) probe failed: $err"
  sleep "$INTERVAL"
done
echo "gave up after 12 h of probes"; exit 1
