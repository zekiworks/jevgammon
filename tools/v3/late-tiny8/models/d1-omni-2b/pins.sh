# Sourced by start.sh and locals.sh (URL and PORT set there): the model's snapshot, its /health as the pinned server
# answers it, and pinned(): the pinned server process on PORT. The server runs on this host (bariton), not on spark2:
# pinned() reads the local process table and files, so SSH_HOST only names the host in messages (TINY_SSH unused).
SSH_HOST="bariton (local)"
SNAPSHOT=/home/cbasaran/.cache/huggingface/hub/models--LiquidAI--d1-Omni-2B/snapshots/81222dae8bf8bdd7f903643b5b2a8803bf2e3176
LABEL="Liquid d1-Omni-2B"
ENV=/home/cbasaran/code/d1-2b/.venv
SERVER=/home/cbasaran/code/benchmark/decision/runner/servers/d1_server.py
SERVER_SHA=ab105fbdf501c6bb7dd1a3b250af184a45577583cb39ca9bfe4b1a2e49710533
# The snapshot's weights: Hugging Face's blob, named by its sha256.
WEIGHTS_BLOB=1553fff04c54377ff527d2016fc479425ef60a0b3bc7a2e61d32f80a75c32aaf
# d1_server.py's /health: the model it answers for.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d == {"status": "ok", "model": "LiquidAI/d1-Omni-2B"}))'
}
# The pinned server: exactly logic's servers.sh d1-omni-2b command (d1-2B's server and env) on PORT (the pinned revision, BF16 as the server loads it)
# from ENV, offline (HF_HUB_OFFLINE=1 in its environment), the pinned server file, torch 2.15.0 (+cu132) and
# transformers 5.22.1, and the snapshot's weights as released.
SERVE="$ENV/bin/python -B $SERVER --model LiquidAI/d1-Omni-2B --revision ${SNAPSHOT##*/} --device cuda:0 --host 127.0.0.1 --port $PORT"
pinned() {
  local procs sp=$ENV/lib/python3.12/site-packages
  procs=$( { ps -eo pid=,args= | while read -r pid a; do
      [[ $a == "$SERVE" ]] && echo "server $(tr '\0' '\n' < /proc/$pid/environ | grep -cx 'HF_HUB_OFFLINE=1')"; done
    sha256sum "$SERVER"; ls -d "$sp/torch-2.15.0.dist-info" "$sp/transformers-5.22.1.dist-info"
    echo "weights $(basename "$(readlink "$SNAPSHOT/model.safetensors")")"; } 2>/dev/null)
  grep -qx "server 1" <<<"$procs" && grep -qxF "$SERVER_SHA  $SERVER" <<<"$procs" &&
  grep -qxF "$sp/torch-2.15.0.dist-info" <<<"$procs" && grep -qxF "$sp/transformers-5.22.1.dist-info" <<<"$procs" &&
  grep -qxF "weights $WEIGHTS_BLOB" <<<"$procs"
}
