#!/usr/bin/env bash
# Scores every legal play of the league decisions not yet scored, at 2-ply (tools/site/score_plays.py),
# into STATE_PLAYS_DIR/s{0..31}.db: 32 shards, at most 8 gnubg processes at nice 19 / idle I/O class.
# Per-shard logs: STATE_PLAYS_DIR/s{N}.log. Prints the total of newly scored decisions.
#   tools/site/score.sh SNAP STATE_PLAYS_DIR
set -euo pipefail

[ $# -eq 2 ] || { echo "usage: $0 SNAP STATE_PLAYS_DIR" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SNAP=$(realpath "$1")
OUT=$2
SHARDS=32
JOBS=8

mkdir -p "$OUT"
OUT=$(realpath "$OUT")
cd "$ROOT"
seq 0 $((SHARDS - 1)) | xargs -P "$JOBS" -I{} sh -c \
  'SCORE_PLAYS_ARGS="$1 $2 $3 $4" nice -n 19 ionice -c 3 gnubg -t -q -p tools/site/score_plays.py > "$2/s$3.log" 2>&1' \
  _ "$SNAP" "$OUT" {} "$SHARDS" || true
for i in $(seq 0 $((SHARDS - 1))); do
  grep -q 'decisions scored$' "$OUT/s$i.log" || { echo "shard $i failed, see $OUT/s$i.log" >&2; exit 1; }
done
awk '/decisions scored$/ { n += $(NF-2) } END { print n + 0 " decisions newly scored" }' "$OUT"/s*.log
