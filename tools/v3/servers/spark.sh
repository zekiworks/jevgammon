#!/usr/bin/env bash
# League 1 decision servers on the two DGX Sparks (NVIDIA GB10, 121 GB unified memory each),
# run from this machine over ssh. Each Spark runs the same server scripts as here (copied to
# ~/code/v3-servers), with the same checkpoints, paths and server arguments, on its one GPU,
# listening on the LAN (BIND_HOST=0.0.0.0):
#   spark  (192.168.1.127): cygnet (vLLM 8892, shim 18093), clef (18091)
#   spark3 (192.168.1.139): decider (18097); from 2026-10-19 also Gemma 4 31B (vLLM 8894,
#     share 0.45), since bariton's GPUs are no longer available
# Open-Jev stays on this machine (open-jev.sh, GPU 2): on spark3 it chose another play than
# here in 2 of 20 League 1 requests (near-ties), over the 1-in-20 limit for moving a player.
#   tools/v3/servers/spark.sh start|stop|status|probe
# Each Spark needs the checkpoints and the projects' aarch64 virtualenvs at the paths used
# here (see README.md, "League 1 on the DGX Sparks").
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

HOSTS=(spark spark3)
declare -A ADDR=([spark]=192.168.1.127 [spark3]=192.168.1.139)
# vLLM checks free memory at start-up, so Cygnet starts before Clef.
declare -A SERVERS=([spark]="cygnet clef" [spark3]="decider gemma4-31b")
REMOTE=code/v3-servers
# Cygnet's vLLM share: 0.28 of 121.7 GiB is 34 GiB, about what 0.34 of a 95.6 GiB card gives.
# Gemma's 0.45 (55 GiB) leaves room for Decider (49 GiB) on spark3; it starts after Decider.
ENV="BIND_HOST=0.0.0.0 CYGNET_UTIL=0.28 CLEF_GPU=0 DECIDER_GPU=0 GEMMA_GPU=0 GEMMA_UTIL=0.45"

remote() { local host=$1; shift; ssh -o BatchMode=yes "$host" "cd ~/$REMOTE && $ENV $*"; }

start_host() {
  local host=$1 s
  ssh -o BatchMode=yes "$host" "mkdir -p ~/$REMOTE"
  rsync -a "$DIR/_lib.sh" "$DIR/cygnet.sh" "$DIR/clef.sh" "$DIR/open-jev.sh" "$DIR/decider.sh" \
    "$DIR/gemma4-31b.sh" "$host:$REMOTE/"
  for s in ${SERVERS[$host]}; do
    remote "$host" "bash -c 'source ./_lib.sh && free_page_cache'"
    remote "$host" "./$s.sh start"
  done
}

case ${1:-} in
  start)
    pids=()
    for h in "${HOSTS[@]}"; do start_host "$h" 2>&1 | sed "s/^/[$h] /" & pids+=($!); done
    failed=0
    for p in "${pids[@]}"; do wait "$p" || failed=1; done
    (( failed == 0 )) || die "spark: a server failed to start (see above)"
    ;;
  stop)
    for h in "${HOSTS[@]}"; do
      for s in ${SERVERS[$h]}; do remote "$h" "./$s.sh stop" | sed "s/^/[$h] /"; done
    done
    ;;
  status)
    for h in "${HOSTS[@]}"; do
      for s in ${SERVERS[$h]}; do remote "$h" "./$s.sh status" | sed "s/^/[$h] /"; done
    done
    ;;
  probe)
    for s in spark:18093:cygnet spark:18091:clef spark3:18097:pplx-decider-v1.1-27b; do
      IFS=: read -r h port model <<<"$s"
      echo "== $h:$port"; systemone_probe "http://${ADDR[$h]}:$port" "$model"
    done
    echo "== spark3:8894"; python3 "$DIR/probe_chat.py" "http://${ADDR[spark3]}:8894/v1" gemma-4-31B-it
    ;;
  *) die "usage: $0 start|stop|status|probe" ;;
esac
