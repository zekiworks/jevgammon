#!/bin/bash
# Restarts the small-model Learning lane on GPU 3 whenever it stops early because a model's port is taken (Logic's
# Science loads use the same small_models.py keys/ports on GPU 1). Finished models are skipped by the lane itself.
set -u
M="minicpm5-2b-on qwen3.5-2b-on lfm2.5-24b-a2b-off gemma-4-e2b-on raon-1-nano-on smollm3-3b-off smollm3-3b-on"
cd /home/cbasaran/code/jevgammon-improve
while :; do
  left=0
  status_failed=0
  for model in $M; do
    status=$(timeout 180 python3 workspace/improve/improve.py status --model "$model" 2>/dev/null) ||
      { status_failed=1; break; }
    grep -Eq ': complete|operator hold|stopped' <<<"$status" || left=$((left + 1))
  done
  if [ "$status_failed" = 1 ]; then sleep 60; continue; fi
  [ "$left" = 0 ] && { echo "all done $(date -u +%T)"; break; }
  if ! systemctl --user is-active -q improve-local-small; then
    systemctl --user reset-failed improve-local-small improve-xid-watch-small 2>/dev/null
    systemctl --user stop improve-xid-watch-small 2>/dev/null
    systemctl --user set-environment SMALL_SHARE_GPU=0.72 LFM_UTIL=0.85 AGENT_BUS_RESERVATION=r_4c565858ef75
    IMPROVE_PIN=c32fedb workspace/improve/run_local_start.sh GPU-e4f2a538-a3dc-e777-a1b6-e083f08514aa improve-local-small improve-xid-watch-small $M
    sleep 5
    systemctl --user unset-environment SMALL_SHARE_GPU LFM_UTIL AGENT_BUS_RESERVATION
  fi
  sleep 600
done
