#!/usr/bin/env bash
# gemma-4-31B-it on several GPUs for the rest of League 1, once the decision servers moved to
# the DGX Sparks (spark.sh): one gemma4-31b.sh replica per GPU (container v3-gemma4-31b-gN on
# port 8900+N, memory share 0.85) behind gemma_proxy.py on port 8894, the single server's
# port, so player configs keep base_url http://127.0.0.1:8894/v1. The proxy sends each request
# to the replica with the fewest in flight; GET http://127.0.0.1:8894/proxy/status shows them.
# GPUs 0, 1 and 3 by default: GPU 2 keeps Open-Jev, which stayed on this machine.
#   [GEMMA_GPUS="0 1 3"] [GEMMA_UTIL=0.85] tools/v3/servers/gemma4-31b-replicas.sh start|stop|status
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

read -r -a GPUS <<<"${GEMMA_GPUS:-0 1 3}"
UNIT=v3-gemma-proxy
PORT=8894
UTIL=${GEMMA_UTIL:-0.85}

replica() { GEMMA_GPU=$1 GEMMA_NAME=v3-gemma4-31b-g$1 GEMMA_PORT=$((8900 + $1)) GEMMA_UTIL=$UTIL \
  "$DIR/gemma4-31b.sh" "$2"; }

case ${1:-} in
  start)
    pids=()
    for g in "${GPUS[@]}"; do replica "$g" start & pids+=($!); done
    failed=0
    for p in "${pids[@]}"; do wait "$p" || failed=1; done
    (( failed == 0 )) || die "gemma4-31b-replicas: a replica failed to start (see above)"
    backends=()
    for g in "${GPUS[@]}"; do backends+=(--backend "http://127.0.0.1:$((8900 + g))"); done
    unit_up "$UNIT" "$PORT" "$DIR" -- /home/cbasaran/.local/bin/uv run --script gemma_proxy.py \
      --host 127.0.0.1 --port "$PORT" "${backends[@]}"
    unit_wait "$UNIT" "http://127.0.0.1:$PORT/v1/models" 120
    ;;
  stop)
    unit_down "$UNIT"
    for g in "${GPUS[@]}"; do replica "$g" stop; done
    ;;
  status)
    unit_status "$UNIT" "http://127.0.0.1:$PORT/proxy/status"
    for g in "${GPUS[@]}"; do replica "$g" status; done
    ;;
  *) die "usage: $0 start|stop|status" ;;
esac
