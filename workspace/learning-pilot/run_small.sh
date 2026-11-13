#!/usr/bin/env bash
# Learning pilot protocol for one small chat model (Ümit #6225): the shared T0, then series FIRST-LAST of all four arms,
# then the summary, as run_smoke.sh / run_main.sh ran Gemma 4 31B (off). Smoke: 1-3; after a clean smoke: 4-10.
#   workspace/learning-pilot/run_small.sh KEY FIRST-LAST      # KEY: configs/KEY.json (lfm3-1.7b-on, minicpm5-2b-on)
# The model's server must already answer at the config's base_url with its served name (logic's small_models.py serve,
# on a card booked on the bus); this script never starts or stops a server. The private evaluation set
# (test_set.json, test_positions.jsonl) must be next to pilot.py; pilot.py refuses another set (test_set_sha256).
set -euo pipefail
KEY=${1:?usage: run_small.sh KEY FIRST-LAST}
SERIES=${2:?usage: run_small.sh KEY FIRST-LAST}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../.."
[[ -f $HERE/configs/$KEY.json ]] || { echo "no config $HERE/configs/$KEY.json" >&2; exit 1; }
export PILOT_CONFIG=configs/$KEY.json
export PATH=$PATH:/usr/games  # gnubg (score_games.py)
# The interpreter with tokenizers (the units' default python3 lacked it at the pilot's first smoke start).
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
URL=$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["players"][0]["base_url"])' "$HERE/configs/$KEY.json")
SERVED=$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["served_model"])' "$HERE/configs/$KEY.json")
curl -fsS -m 10 "$URL/models" |
  $PY -c 'import json,sys; sys.exit(sys.argv[1] not in [m["id"] for m in json.load(sys.stdin)["data"]])' \
  "$SERVED" || { echo "$URL does not serve $SERVED" >&2; exit 1; }
echo "start $KEY $SERIES $(date -u +%FT%TZ)"
$PY workspace/learning-pilot/pilot.py t0   # once per model: returns at once when done
echo "t0 done $(date -u +%FT%TZ)"
$PY workspace/learning-pilot/pilot.py run --series "$SERIES"
echo "series $SERIES done $(date -u +%FT%TZ)"
$PY workspace/learning-pilot/pilot.py summary
