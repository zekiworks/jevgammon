#!/usr/bin/env bash
# One test decision of a small chat setup (KEY: models/KEY) through the real chat client against the real server, before
# its first start (Main, 12 Nov): llama.cpp's handling of the prefilled answer (LFM3-1.7B, Spark-X2.6-4B) and the
# templates predicted to refuse the (on) prefill (Qwen3.5, MiniCPM5, Gemma 4 E4B) are checked here, and only here.
# Run only when the server is ours alone (after turkce's 'done KEY'); it costs nothing (no paid player is asked).
#   tools/v3/late-smallchat/test.sh KEY        [SMALLCHAT_URL / SMALLCHAT_MODEL as for start.sh]
# What it does: the server is the pinned one (pins.sh), the setup's League 1 config is written to
# ~/.cache/smallchat/test/KEY (never workspace/ or v3.db), and `jevgammon ask` puts the first smoke position
# (positions/smoke.jsonl) to the setup once, answers in ~/.cache/smallchat/test/KEY/answers.db. Exit 0 only when that
# answer is valid with the letter probabilities read from logprobs (probability_source 'logprobs'), as every decision of
# League 1's local chat setups was; otherwise exit 1 and the setup is reported, not started.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
KEY=${1:?usage: test.sh KEY}
T=$(dirname "$(readlink -f "$0")")
[[ -f $T/models/$KEY/player.json ]] || { echo "unknown setup $KEY" >&2; exit 1; }
BIN=${SMALLCHAT_BIN:-/home/cbasaran/code/jevgammon/target/smallchat/release/jevgammon}
OUT=$HOME/.cache/smallchat/test/$KEY
PLAYER=$(python3 "$T/smallchat.py" "$KEY" player) || { echo "settings of $KEY unreadable" >&2; exit 1; }
field() { python3 -c 'import json,sys; print(eval(sys.argv[2], {}, {"p": json.loads(sys.argv[1])}))' "$PLAYER" "$1"; }
[[ $(field '"reasoning_prefill" in p') == False || -n ${SMALLCHAT_BIN:-} ]] ||
  { echo "$KEY sets reasoning_prefill: SMALLCHAT_BIN must name a runner built with it" >&2; exit 1; }
URL=$(field 'p["base_url"]')
NAME=$(field 'p["name"]')
SERVED=$(field 'p["spec"].split("/", 1)[1]')
PORT=${URL%/v1}
PORT=${PORT##*:}
. "$T/pins.sh"
[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
healthy || { echo "$LABEL server $URL: does not serve $SERVED" >&2; exit 1; }
pinned || { echo "$LABEL: the process on port $PORT is not the pinned $PIN_REPO@$PIN_REV" >&2; exit 1; }
mkdir -p "$OUT"
SMALLCHAT_OUT=$OUT python3 "$T/smallchat.py" "$KEY" configs || { echo "config of $KEY not written" >&2; exit 1; }
"$BIN" ask --config "$OUT/$KEY.json" --positions positions/smoke.jsonl --limit 1 --setup "$NAME" --once \
  --out "$OUT/answers.db" 2>&1 | tee "$OUT/ask.log" | tail -5
sqlite3 -readonly "$OUT/answers.db" "SELECT invalid, probability_source, letter, output_tokens, request_ms FROM answers
  WHERE setup = '$NAME'" | tee "$OUT/result.txt"
row=$(cat "$OUT/result.txt")
if [[ $row == 0\|logprobs\|* ]]; then
  echo "$KEY: test decision valid, letter probabilities from logprobs ($row)"
else
  echo "$KEY: TEST FAILED (${row:-no answer stored}); see $OUT/ask.log and answer_exchanges in $OUT/answers.db" >&2
  exit 1
fi
