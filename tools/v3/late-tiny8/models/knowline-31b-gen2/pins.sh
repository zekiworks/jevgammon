# Sourced by start.sh and locals.sh (URL and PORT set there): the model's snapshot, its /health as the pinned server
# answers it, and pinned(): the pinned server on PORT. The server runs on this host (bariton), on compactor's card, in
# compactor's docker container (runs/gpu0-serve-15nov.sh serve knowline-31b-gen2), not on spark2: pinned() reads the
# local process table, docker's record of the container and the snapshot's files, so SSH_HOST only names the host in
# messages (TINY_SSH unused). The container's processes run as root: their environment is read from docker, not /proc.
SSH_HOST="bariton (local)"
SNAPSHOT=/home/cbasaran/.cache/huggingface/hub/models--PelaAI--KnowLine-31B-Gen2/snapshots/fd99a9ed2255d8a67dd47a44cc429e638f611593
LABEL=KnowLine-31B-Gen2
HUB=${SNAPSHOT%/models--*}
# The snapshot's own SHA256SUMS (29 files): the code, configs and tokenizer are checked against it, the 13 weight shards
# by their blob names (Hugging Face names an LFS blob by its sha256).
SUMS_SHA=cb9e2bded680a19946782e4242975ae0239e2db33180fb2f1c21d003dc0320a0
# lmsysorg/sglang:latest as compactor runs it: v0.5.23 (label org.opencontainers.image.version, commit 297e54f).
IMAGE=sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f
CONTAINER=cmp-knowline-31b-gen2
SGL_PORT=$((PORT + 1000))
# knowline_server.py's /health (Gen2): served name m, temperature 1, read twice up to 3,000 tokens (no header, no
# referenced fields), the box settings serve_knowline.sh gives (gemma prompt, yxyx, no calibration), no URL assets.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d == {"status": "ok", "model": "m", "temperature": 1.0,
                    "layout": {"header": False, "header_min_questions": 1, "read_twice": True, "twice_max_tokens": 3000,
                               "referenced_fields": False},
                    "box": {"backend": True, "prompt": "gemma", "template": None, "coords": "yxyx", "calibration": None},
                    "url_assets": False}))'
}
# The pinned server: exactly serve_knowline.sh's two processes for the snapshot on PORT (SGLang in BF16 at MEM 0.85,
# no --quantization, no --allow-auto-truncate; the front end with the card's flags; no box calibration file in the
# snapshot), in the container CONTAINER as compactor starts it: the pinned image, `bash <snapshot>/serve_knowline.sh
# <snapshot> 0 PORT`, published on 127.0.0.1:PORT only, the hub mounted read-only, HF_HUB_OFFLINE=1 and HOST=0.0.0.0
# in its environment and no MEM override; and the snapshot's files as released.
SERVE="python $SNAPSHOT/knowline_server.py --model $SNAPSHOT --backend sglang --url http://127.0.0.1:$SGL_PORT --served-model-name m --temperature 1 --workers 16 --host 0.0.0.0 --port $PORT --temperatures $SNAPSHOT/temperatures.json --box-prompt gemma --box-coords yxyx"
SERVE_ALSO="python -m sglang.launch_server --model-path $SNAPSHOT --served-model-name m --tp 1 --mem-fraction-static 0.85 --enable-fp32-lm-head --port $SGL_PORT"
CONTAINER_FMT='{{.Image}}|{{.State.Running}}|{{json .Config.Entrypoint}}|{{json .Config.Cmd}}|{{json .HostConfig.PortBindings}}|{{range .Mounts}}{{.Source}}:{{.Destination}}:{{.RW}};{{end}}'
CONTAINER_WANT="$IMAGE|true|[\"bash\"]|[\"$SNAPSHOT/serve_knowline.sh\",\"$SNAPSHOT\",\"0\",\"$PORT\"]|{\"$PORT/tcp\":[{\"HostIp\":\"127.0.0.1\",\"HostPort\":\"$PORT\"}]}|$HUB:$HUB:false;"
pinned() {
  local procs env
  procs=$(ps -eo pid=,args= 2>/dev/null | sed 's/^ *[0-9]* //')
  grep -qxF -- "$SERVE" <<<"$procs" && grep -qxF -- "$SERVE_ALSO" <<<"$procs" || return 1
  [[ $(docker inspect -f "$CONTAINER_FMT" "$CONTAINER" 2>/dev/null) == "$CONTAINER_WANT" ]] || return 1
  env=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" 2>/dev/null) || return 1
  grep -qxF HF_HUB_OFFLINE=1 <<<"$env" && grep -qxF HOST=0.0.0.0 <<<"$env" && ! grep -q '^MEM=' <<<"$env" || return 1
  [[ ! -e $SNAPSHOT/box_calibration.json ]] || return 1
  [[ $(sha256sum < "$SNAPSHOT/SHA256SUMS") == "$SUMS_SHA  -" ]] || return 1
  (cd "$SNAPSHOT" && grep -v '\.safetensors$' SHA256SUMS | sha256sum -c --quiet >/dev/null 2>&1) || return 1
  local sum file n=0
  while read -r sum file; do
    [[ $(basename "$(readlink "$SNAPSHOT/$file")") == "$sum" ]] || return 1
    n=$((n + 1))
  done < <(grep '\.safetensors$' "$SNAPSHOT/SHA256SUMS")
  (( n == 13 ))
}
