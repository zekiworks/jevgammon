# Sourced by start.sh and locals.sh (URL and PORT set there): the model's checkpoint, its /health as the pinned server
# answers it, and pinned(): the pinned server process on PORT. The server runs on this host (bariton), not on spark2:
# pinned() reads the local process table and files, so SSH_HOST only names the host in messages (TINY_SSH unused).
SSH_HOST="bariton (local)"
# StrandsAgents/strands-decider-2B-hobson-v21 @ 2b52a6235c1b8306bbfa30b00b9d4b74b63a39f5 (LoRA adapter + pointer head),
# downloaded by logic; its base Qwen/Qwen3.5-2B-Base @ b1485b2 (provenance.json) is read offline from HF_CACHE.
SNAPSHOT=/home/cbasaran/code/strands-decider/model
HF_CACHE=/home/cbasaran/code/strands-decider/hf-cache
LABEL="Strands Decider 2B"
ENV=/home/cbasaran/code/strands-decider/.venv
# sha256 of "sha256sum" over the installed package's .py files (sorted, LC_ALL=C): strands_decider 0.0.1.dev11+g3e94e9d84.
TREE_SHA=1c68f578e75ed4e7999d6b19b29b4ecb5d57e3bd91dc0cc30199c96111fd14ee
# The checkpoint's files as provenance.json and MANIFEST.sha256 give them, and the base's weights (Hugging Face's blob,
# named by its sha256).
HEAD_SHA=0fc78684d7504d334082d6ac8e6cb7825b5eb0e230601181cd273757f9f6ebef
ADAPTER_SHA=59be987f5eb664a7f74f11ef69383a0de526fe30c684932102984eb9c11f4028
CONFIG_SHA=9b660cabb91ab9683dd62dee83e00a5ca30dff8657489e6ce473136f8d9eb529
BASE_SNAPSHOT=$HF_CACHE/models--Qwen--Qwen3.5-2B-Base/snapshots/b1485b2fa6dfa1287294f269f5fb618e03d52d7c
BASE_BLOB=928acbf11878c32185bbd863514d191769285065ab9ea14fbfe431303f5fdf2d
# strands_decider.server's /health: the served name, this checkpoint on its base, the 4,096-token window, text only.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d["status"] == "ok" and d["model"] == "strands-decider-2b" and d["checkpoint"] == sys.argv[1]
              and d["base_model"] == "Qwen/Qwen3.5-2B-Base" and d["max_length"] == 4096 and d["vision"] is False
              and d["device"] == "cuda"))' "$SNAPSHOT"
}
# The pinned server: exactly the package's own `strands-decider serve` on PORT with --strict-window (a prompt over the
# 4,096-token window is refused, 422; without it the server cuts the state), from ENV, offline (HF_HUB_OFFLINE=1,
# HF_HUB_CACHE the checkout's cache), the installed package's tree, torch 2.7.1+cu128, transformers 5.17.0, peft 0.21.0,
# and the pinned weights.
SERVE="$ENV/bin/python $ENV/bin/strands-decider serve $SNAPSHOT --host 127.0.0.1 --port $PORT --device cuda --model-name strands-decider-2b --strict-window"
pinned() {
  local procs sp=$ENV/lib/python3.12/site-packages
  procs=$( { ps -eo pid=,args= | while read -r pid a; do
      [[ $a == "$SERVE" ]] || continue
      e=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null)
      echo "server $(grep -cx 'HF_HUB_OFFLINE=1' <<<"$e") $(grep -cxF "HF_HUB_CACHE=$HF_CACHE" <<<"$e")"; done
    echo "tree $(cd "$sp" && find strands_decider -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)"
    ls -d "$sp/strands_decider-0.0.1.dev11+g3e94e9d84.dist-info" "$sp/torch-2.7.1+cu128.dist-info" \
      "$sp/transformers-5.17.0.dist-info" "$sp/peft-0.21.0.dist-info"
    sha256sum "$SNAPSHOT/head.safetensors" "$SNAPSHOT/lora/adapter_model.safetensors" "$SNAPSHOT/strands_decider_config.json"
    echo "base $(basename "$(readlink "$BASE_SNAPSHOT/model.safetensors-00001-of-00001.safetensors")")"; } 2>/dev/null)
  grep -qx "server 1 1" <<<"$procs" && grep -qxF "tree $TREE_SHA  -" <<<"$procs" &&
  grep -qxF "$sp/strands_decider-0.0.1.dev11+g3e94e9d84.dist-info" <<<"$procs" &&
  grep -qxF "$sp/torch-2.7.1+cu128.dist-info" <<<"$procs" && grep -qxF "$sp/transformers-5.17.0.dist-info" <<<"$procs" &&
  grep -qxF "$sp/peft-0.21.0.dist-info" <<<"$procs" && grep -qxF "$HEAD_SHA  $SNAPSHOT/head.safetensors" <<<"$procs" &&
  grep -qxF "$ADAPTER_SHA  $SNAPSHOT/lora/adapter_model.safetensors" <<<"$procs" &&
  grep -qxF "$CONFIG_SHA  $SNAPSHOT/strands_decider_config.json" <<<"$procs" && grep -qxF "base $BASE_BLOB" <<<"$procs"
}
