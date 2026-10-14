#!/usr/bin/env bash
# Start, stop, check or probe one wave of v3 model servers. The two waves do not fit on the
# four GPUs together: stop one before starting the other.
#   tools/v3/servers/wave.sh A|B start|stop|status|probe
#   wave A: qwen38-flash-next (GPUs 0-3) and gemma4-31b (GPU 3)
#   wave B: cygnet (GPU 0), clef (GPU 1), open-jev (GPU 2), decider (GPU 3)
source "$(dirname "$(readlink -f "$0")")/_lib.sh"
DIR=$(dirname "$(readlink -f "$0")")

case ${1:-} in
  A) SERVERS=(qwen38-flash-next gemma4-31b) ;;
  B) SERVERS=(cygnet clef open-jev decider) ;;
  *) die "usage: $0 A|B start|stop|status|probe" ;;
esac

case ${2:-} in
  start)
    if [[ $1 == A ]]; then
      # Sequential: Gemma shares GPU 3 with Qwen and sizes its memory after Qwen has loaded.
      for s in "${SERVERS[@]}"; do "$DIR/$s.sh" start; done
    else
      # One GPU each, so they load in parallel.
      pids=()
      for s in "${SERVERS[@]}"; do "$DIR/$s.sh" start & pids+=($!); done
      failed=0
      for p in "${pids[@]}"; do wait "$p" || failed=1; done
      (( failed == 0 )) || die "wave B: a server failed to start (see above)"
    fi
    ;;
  stop) for s in "${SERVERS[@]}"; do "$DIR/$s.sh" stop; done ;;
  status) for s in "${SERVERS[@]}"; do "$DIR/$s.sh" status; done ;;
  probe)
    if [[ $1 == A ]]; then
      python3 "$DIR/probe_chat.py" http://127.0.0.1:8896/v1 qwen3.8-flash-next
      python3 "$DIR/probe_chat.py" http://127.0.0.1:8894/v1 gemma-4-31B-it
    else
      for s in 18093:cygnet 18091:clef 8791: 18097:pplx-decider-v1.1-27b; do
        echo "== port ${s%%:*}"; systemone_probe "http://127.0.0.1:${s%%:*}" "${s#*:}"
      done
    fi
    ;;
  *) die "usage: $0 A|B start|stop|status|probe" ;;
esac
