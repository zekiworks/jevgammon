# Sourced by start.sh and locals.sh (URL and PORT set there): the model's checkpoint, its server's answer as health, and
# pinned(): the pinned server process on PORT. The server runs on this host (bariton), not on spark2: pinned() reads the
# local process table and files, so SSH_HOST only names the host in messages (TINY_SSH unused).
SSH_HOST="bariton (local)"
# wayfind/metask-jev-4b-policy-mix @ ea20fe85b28733b1522721dec119bec50947a869 (Metask-Jev-4B), downloaded by logic.
SNAPSHOT=/home/cbasaran/code/metask-jev/model
LABEL="Metask-Jev-4B"
DIR=/home/cbasaran/code/metask-jev
ENV=$DIR/.venv
# logic's server.py (System One over the vendor's jev_scorer.score; 4,096-token and 26-choice refusals) and the vendor's
# jev_schema.py / jev_scorer.py beside it; the checkpoint's temperature.json; model.safetensors as Hugging Face's
# sha256 (its download metadata) gives it.
SERVER_SHA=d230778973683bf152942738b433d284ada40226b0025753c5e44da5fb16abe7
SCHEMA_SHA=a0a0f94d0f65e972bc20d088678ad3d595ff1c42b9c0d78f96034526303f63fc
SCORER_SHA=13e9d184ede675a92d4404591e55a8a1060db776a0f89fcf945d83ce2e784157
TEMPERATURE_SHA=40e69e5d6b55f1e2dfcf3dc8916e03b4018aecc96ef96769f990d174fcd685af
WEIGHTS_SHA=f4b40475d18e0a38638b985ed51816c012619e0d4138166704e2ea0aac7a12b3
# server.py has no GET route: any HTTP answer (its 501 for GET) means it is up; pinned() names the server.
healthy() {
  local code
  code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$URL/health")
  [[ -n $code && $code != 000 ]]
}
# The pinned server: exactly logic's servers.sh metask command on PORT from ENV in DIR (its working directory, where
# server.py imports jev_schema and jev_scorer from), offline (HF_HUB_OFFLINE=1), the pinned files, torch 2.11.0 and
# transformers 5.10.2, and the checkpoint's weights (hashed once, at start).
SERVE="$ENV/bin/python -B server.py --device cuda:0 --host 127.0.0.1 --port $PORT"
pinned() {
  local procs sp=$ENV/lib/python3.12/site-packages
  procs=$( { ps -eo pid=,args= | while read -r pid a; do
      [[ $a == "$SERVE" && $(readlink /proc/$pid/cwd) == "$DIR" ]] || continue
      echo "server $(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -cx 'HF_HUB_OFFLINE=1')"; done
    sha256sum "$DIR/server.py" "$DIR/jev_schema.py" "$DIR/jev_scorer.py" "$SNAPSHOT/temperature.json" \
      "$SNAPSHOT/model.safetensors"
    ls -d "$sp/torch-2.11.0.dist-info" "$sp/transformers-5.10.2.dist-info"; } 2>/dev/null)
  grep -qx "server 1" <<<"$procs" && grep -qxF "$SERVER_SHA  $DIR/server.py" <<<"$procs" &&
  grep -qxF "$SCHEMA_SHA  $DIR/jev_schema.py" <<<"$procs" && grep -qxF "$SCORER_SHA  $DIR/jev_scorer.py" <<<"$procs" &&
  grep -qxF "$TEMPERATURE_SHA  $SNAPSHOT/temperature.json" <<<"$procs" &&
  grep -qxF "$WEIGHTS_SHA  $SNAPSHOT/model.safetensors" <<<"$procs" &&
  grep -qxF "$sp/torch-2.11.0.dist-info" <<<"$procs" && grep -qxF "$sp/transformers-5.10.2.dist-info" <<<"$procs"
}
