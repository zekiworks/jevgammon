#!/usr/bin/env bash
# Wait (up to 2 h) until all four bariton GPUs are empty, then run League 2's resume (steps 2-3).
for i in $(seq 1 240); do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1>1000' | wc -l)
  [ "$used" -eq 0 ] && break
  sleep 30
done
echo "$(date -u +%FT%TZ) GPUs in use: $used" >> /home/cbasaran/code/jevgammon/midnight-takeover.log
[ "$used" -eq 0 ] || { echo "GPUs not free after 2 h; not starting" >> /home/cbasaran/code/jevgammon/midnight-takeover.log; exit 1; }
cd /home/cbasaran/code/jevgammon && SKIP_SMOKE=1 exec tools/v3/midnight_takeover.sh
