# Sourced by start.sh and locals.sh (URL and PORT set there): the model's snapshot, its /health as the pinned server
# answers it, and pinned(): the pinned server process on PORT. The server runs on this host (bariton), not on spark2:
# pinned() reads the local process table and files, so SSH_HOST only names the host in messages (TINY_SSH unused).
SSH_HOST="bariton (local)"
SNAPSHOT=/home/cbasaran/.cache/huggingface/hub/models--LiquidAI--d1-2B/snapshots/10e7671d44e4b37700020b1eed3f594c5f2af0b4
LABEL="Liquid d1-2B"
ENV=/home/cbasaran/code/d1-2b/.venv
SERVER=/home/cbasaran/code/benchmark/decision/runner/servers/d1_server.py
SERVER_SHA=ab105fbdf501c6bb7dd1a3b250af184a45577583cb39ca9bfe4b1a2e49710533
# The snapshot's weights: Hugging Face's blob, named by its sha256.
WEIGHTS_BLOB=b5e573687315e82ea80f4f7dd8d76b5cec3b6ee97e3509fd0493cfebb203719f
# d1_server.py's /health: the model it answers for.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d == {"status": "ok", "model": "LiquidAI/d1-2B"}))'
}
# The pinned server: exactly logic's servers.sh d1-2b command on PORT (the pinned revision, BF16 as the server loads it)
# from ENV, offline (HF_HUB_OFFLINE=1 in its environment), the pinned server file, torch 2.15.0 (+cu132) and
# transformers 5.22.1, and the snapshot's weights as released.
SERVE="$ENV/bin/python -B $SERVER --model LiquidAI/d1-2B --revision ${SNAPSHOT##*/} --device cuda:0 --host 127.0.0.1 --port $PORT"
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
