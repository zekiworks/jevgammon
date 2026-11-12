#!/usr/bin/env bash
# After a provider overload or usage limit ended a subscription lane: one probe request through MODEL's league route
# (its v3.db setup, the pinned runner, `jevgammon lesson`, a one-line prompt) every INTERVAL seconds for up to 12 h;
# on the first success the lane is restarted with its committed start command (run_lane.sh LANE MODELS...). The
# match itself is never looped. Each probe is logged as a provider_probe event in MODEL's run log.
#   systemd-run --user --unit improve-xai-wait workspace/improve/provider_wait_restart.sh 600 grok-4.7-on \
#     improve-subs-xai grok-4.7-on
set -uo pipefail
cd "$(dirname "$0")/../.."
INTERVAL=${1:?interval seconds}; MODEL=${2:?model key to probe}; LANE=${3:?lane unit}; shift 3
[[ $# -gt 0 ]] || { echo "no lane models" >&2; exit 1; }
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
BIN=$PWD/target/improve-bin/jevgammon-8b6f9a1
LOG=/home/cbasaran/code/jevgammon/workspace/improve/runs/$MODEL/log.jsonl
P=$(mktemp -d)
"$PY" - "$MODEL" "$P/player.json" <<'EOF'
import json, sys
sys.path.insert(0, "workspace/improve")
import improve as I
key, out = sys.argv[1], sys.argv[2]
setup = I.MODELS[key]["setup"]
p = I.league_settings(setup)
p.update(name=f"{setup} | improve | probe", parallel=1)
p.pop("max_matches", None)
json.dump(p, open(out, "w"))
EOF
echo "Reply with the single word: ok" > "$P/user.txt"; echo "You are a test." > "$P/system.txt"
for i in $(seq 1 $(( 43200 / INTERVAL ))); do
  if "$BIN" lesson --player "$P/player.json" --system "$P/system.txt" --user "$P/user.txt" --out "$P/out.json" 2> "$P/err.txt"; then
    served=$("$PY" -c "import json; print(json.loads(json.load(open('$P/out.json'))['exchanges'][0]['response']).get('model'))")
    printf '{"at": "%s", "event": "provider_probe", "result": "ok", "model": "%s"}\n' "$(date -u +%FT%T+00:00)" "$served" >> "$LOG"
    echo "$(date -u +%FT%TZ) probe ok ($served): restarting $LANE"
    exec workspace/improve/run_lane.sh "$LANE" "$@"
  fi
  err=$(tr -d '"\\' < "$P/err.txt" | tr '\n' ' ' | tail -c 300)
  printf '{"at": "%s", "event": "provider_probe", "result": "failed", "error": "%s"}\n' "$(date -u +%FT%T+00:00)" "$err" >> "$LOG"
  echo "$(date -u +%FT%TZ) probe failed: $err"
  sleep "$INTERVAL"
done
echo "gave up after 12 h of probes"; exit 1
