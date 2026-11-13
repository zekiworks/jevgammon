#!/usr/bin/env bash
# Clear-risk Part 2 (Q1 with numbers + board only, Q2 board only) for one small model KEY of models.json, at its league
# settings, through `jevgammon quiz` (Part 2's runner). One model at a time, while its server is up (decision models:
# logic's server on spark2, handed over; chat models: logic's small_models.py server or late-smallchat serve.sh on
# bariton). A rerun asks only the missing or failed items of KEY (quiz's rule); nothing else is retried.
#   tools/v3/clearrisk-small/run.sh KEY            the 438 questions, answers in $OUT
#   tools/v3/clearrisk-small/run.sh KEY --smoke    the first question only, answers in ~/.cache/clearrisk-small/smoke
# Env: BIN (runner built from this branch; default ~/.cache/clearrisk-small/target/release/jevgammon), OUT (default
# ~/code/jevgammon/smoke/clearrisk-small-q.db, a new file: never the 30 Oct smoke/clearrisk-q.db), CRP2_BASE_URL
# (stub tests only: replaces the player's base_url).
set -uo pipefail
T=$(dirname "$(readlink -f "$0")")
KEY=${1:?usage: run.sh KEY [--smoke]}
MODE=${2:-}
BIN=${BIN:-$HOME/.cache/clearrisk-small/target/release/jevgammon}
OUT=${OUT:-/home/cbasaran/code/jevgammon/smoke/clearrisk-small-q.db}
CACHE=${CRP2_CACHE:-$HOME/.cache/clearrisk-small}
ITEMS=$T/items_q1q2.jsonl
[[ $OUT == */smoke/clearrisk-q.db ]] && { echo "refusing the frozen Part 2 DB $OUT" >&2; exit 1; }
[[ -x $BIN ]] || { echo "no runner $BIN (build: CARGO_TARGET_DIR=$HOME/.cache/clearrisk-small/target cargo build --release)" >&2; exit 1; }
CFG=$CACHE/configs/$KEY.json
python3 "$T/crp2.py" config "$KEY" "$CFG" ${CRP2_BASE_URL:+--base-url "$CRP2_BASE_URL"} || exit 1
IFS=$'\t' read -r NAME URL SERVED FORM < <(python3 - "$CFG" "$KEY" "$T" <<'EOF'
import json, sys
sys.path.insert(0, sys.argv[3]); import crp2
p = json.load(open(sys.argv[1]))["players"][0]
print("\t".join([p["name"], p["base_url"], p["spec"].split("/", 1)[-1], crp2.models()[sys.argv[2]]["kind"]]))
EOF
)
[[ -n ${FORM:-} ]] || { echo "settings of $KEY unreadable" >&2; exit 1; }
LIMIT=$(python3 "$T/crp2.py" field "$KEY" time_limit) || exit 1
# Server up: a chat server lists the served model; a decision server answers HTTP at all (routes differ per server).
if [[ $FORM == chat ]]; then
  curl -sf --max-time 10 "$URL/models" | grep -q "\"$SERVED\"" || { echo "$NAME: $URL does not serve $SERVED" >&2; exit 1; }
else
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$URL/health")
  [[ $code != 000 ]] || { echo "$NAME: no server at $URL" >&2; exit 1; }
fi
if [[ $MODE == --smoke ]]; then
  mkdir -p "$CACHE/smoke"
  head -n 1 "$ITEMS" > "$CACHE/smoke/$KEY.jsonl"
  ITEMS=$CACHE/smoke/$KEY.jsonl
  OUT=$CACHE/smoke/$KEY.db
elif [[ -n $MODE ]]; then
  echo "unknown option $MODE" >&2; exit 1
fi
mkdir -p "$(dirname "$OUT")"
echo "$(date -u +%FT%TZ) $NAME ($KEY) starts: $ITEMS -> $OUT" >> "${OUT%.db}.log"
"$BIN" quiz --config "$CFG" --items "$ITEMS" --out "$OUT" --setup "$NAME" --time-limit "$LIMIT" 2>&1 | tee -a "${OUT%.db}.log"
status=${PIPESTATUS[0]}
echo "$(date -u +%FT%TZ) $NAME ($KEY) ended (exit $status)" >> "${OUT%.db}.log"
sqlite3 -readonly "$OUT" "SELECT COUNT(*), SUM(error IS NOT NULL) FROM quiz_answers WHERE setup = '${NAME//\'/\'\'}'" |
  { IFS='|' read -r n failed; echo "$NAME: $n answer rows, ${failed:-0} with a request error (of $(wc -l < "$ITEMS"))"; }
exit "$status"
