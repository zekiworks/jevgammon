#!/usr/bin/env bash
# "Did they improve?" Phase 2, OpenRouter lane (plan §10): one model at a time, cheapest first. Each model runs to
# completion under the money rules built into improve.py. Exit codes of `improve.py run`: 0 complete, 2 stopped
# (rule a, rule b, route check: the next model goes on), 3 paused (balance or share: the queue stops here and
# resumes from the same step when started again), anything else: an error (the queue stops for a look).
#   systemd-run --user --unit improve-openrouter workspace/improve/run_queue.sh qwen3.8-flash-off glm-5.3-on ...
set -uo pipefail
cd "$(dirname "$0")/../.."
# OPENROUTER_API_KEY (and the other provider keys) as the leagues read them.
. "$HOME/.keys"
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
echo "queue start $(date -u +%FT%TZ): $*"
for model in "$@"; do
  echo "== $model start $(date -u +%FT%TZ)"
  "$PY" workspace/improve/improve.py run --model "$model"
  code=$?
  echo "== $model exit $code $(date -u +%FT%TZ)"
  "$PY" workspace/improve/improve.py status --model "$model"
  case $code in
    0|2) continue ;;
    3) echo "queue paused at $model"; exit 3 ;;
    *) echo "queue stopped: $model failed"; exit "$code" ;;
  esac
done
echo "queue done $(date -u +%FT%TZ)"
