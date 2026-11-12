#!/usr/bin/env bash
# QC 2026-11-12 Run 2 (Ümit via Zeki #5264/#5276): improve.py from this worktree, writing only to the separate Run 2
# root (IMPROVE_RUN2); the original runs, v3.db and the live lanes' improve.py are only read. Pinned runner
# jevgammon-8b6f9a1 (1270c04 + the 200-error-reply fix). IMPROVE_DRY=1 passes through (dry run: the safest program,
# canned lessons, nothing billed, *-dry paths).
#   systemd-run --user --unit qc-run2-deepseek --property=WorkingDirectory=$PWD workspace/improve/run2.sh deepseek-v4.1-flash-on
#   systemd-run --user --unit qc-run2-argon --property=WorkingDirectory=$PWD workspace/improve/run2.sh gemini-4-argon-on
set -uo pipefail
cd "$(dirname "$0")/../.."
MODEL=${1:?model}
. "$HOME/.keys"
export IMPROVE_ROOT=/home/cbasaran/code/jevgammon
export IMPROVE_RUN2=/home/cbasaran/code/jevgammon/smoke/improve-run2
export IMPROVE_BIN=/home/cbasaran/code/jevgammon-improve/target/improve-bin/jevgammon-8b6f9a1
export TMPDIR=/home/cbasaran/.cache/tmp
mkdir -p "$TMPDIR" "$IMPROVE_RUN2"
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
I=workspace/improve/improve.py
echo "run2 $MODEL start $(date -u +%FT%TZ) dry=${IMPROVE_DRY:-0} bin $(sha256sum "$IMPROVE_BIN")"
case $MODEL in
  deepseek-v4.1-flash-on)
    # S5-T10: the 4 answers lost to HTTP-200 provider errors, with S5's stored test config; then S1 whole.
    "$PY" $I refill --model "$MODEL" --step S5 --answers 1465,1466,1491,1492 || { echo "refill failed: $?"; exit 1; }
    export IMPROVE_RUN2_STEPS=S1
    ;;
  gemini-4-argon-on)
    # E1, S1 and the whole S2; only gemini-4-argon accepted (a -d reply fails the route check and stops the run).
    export IMPROVE_RUN2_STEPS=E1,S1,S2
    export IMPROVE_RUN2_EXPECT='{"gemini-4-argon-on": ["gemini-4-argon"]}'
    ;;
  *) echo "no Run 2 for $MODEL"; exit 1 ;;
esac
"$PY" $I run --model "$MODEL"
code=$?
echo "run2 $MODEL run exit $code $(date -u +%FT%TZ)"
"$PY" $I run2-report --model "$MODEL"
exit $code
