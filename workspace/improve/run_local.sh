#!/usr/bin/env bash
# "Did they improve?" Phase 2, local lane (plan §10): one model at a time on ONE GPU, given by UUID, each with its
# league server script and arguments (only the GPU differs). Several lanes may run on different GPUs (Can #3383);
# each model belongs to exactly one lane: runs/<model>/lane.json names the lane's unit (IMPROVE_LANE), and a lane
# skips a model claimed by another lane before touching any server. Before each start: the UUID's index on the host
# and the GPU the container sees are checked; the container's model path and image are recorded. A stop (exit 2)
# moves on to the next model; a pause (3) or an error stops the lane (the server is stopped).
#   IMPROVE_LANE=improve-local3 [IMPROVE_PIN=c32fedb] workspace/improve/run_local.sh GPU-UUID qwen3.8-27b-on lfm2.5-24b-a2b-on
# An external lane (UUID `external`) runs models on a shared server its owner runs (server() `external:`, MODELS
# `external`): no GPU, no start, no stop; improve.py checks and records that server before every step and pauses the
# model while it is not the pinned load (Inkling 2 Mini on logic's load, Ümit #13810).
#   IMPROVE_LANE=improve-local-ink IMPROVE_PIN=c32fedb workspace/improve/run_local.sh external inkling-2-mini-e05
# The runner pin: IMPROVE_BIN (run_local_start.sh sets it), else target/improve-bin/jevgammon-${IMPROVE_PIN:-e417a0c}.
set -uo pipefail
cd "$(dirname "$0")/../.."
UUID=$1; shift
LANE=${IMPROVE_LANE:?IMPROVE_LANE: the lane unit name}
export IMPROVE_BIN=${IMPROVE_BIN:-$PWD/target/improve-bin/jevgammon-${IMPROVE_PIN:-e417a0c}}
PY=/home/cbasaran/.pyenv/versions/3.12.13/bin/python3
SERVERS=/home/cbasaran/code/jevgammon/tools/v3/servers
# Small chat models: the league's (on) route, logic's own serve command on our card (#5119); `logic:KEY` below. Its port
# is read from small_models.py SETUPS when the model starts (logic_port): SETUPS numbers ports by position (18600 +
# index), so a setup inserted there moves the later ones (20 Nov: LFM3-1.7B rerun 18645 -> 18654).
SMALL_MODELS=${IMPROVE_SMALL_MODELS:-/home/cbasaran/code/benchmark/logic/work/small_models.py}
RUNS=/home/cbasaran/code/jevgammon/workspace/improve/runs
server() {  # model key -> "script name port gpu-variable" (script logic:KEY: small_models.py KEY, by UUID)
  case $1 in
    gemma-4-31b-on) echo "gemma4-31b.sh v3-gemma4-31b 8894 GEMMA_GPU" ;;
    qwen3.8-27b-on) echo "qwen38-27b.sh v3-qwen38-27b 8897 QWEN27_GPU" ;;
    lfm2.5-24b-a2b-on) echo "lfm25-24b.sh v3-lfm25-24b 8898 LFM_GPU" ;;
    gemma-4-e4b-on) echo "logic:gemma-4-e4b-it logic-small-gemma-4-e4b-it - -" ;;
    gemma-4-e2b-on) echo "logic:gemma-4-e2b-it logic-small-gemma-4-e2b-it - -" ;;
    gemma-4-12b-on) echo "logic:gemma-4-12b-it logic-small-gemma-4-12b-it - -" ;;
    minicpm5-2b-on) echo "logic:minicpm5-2b logic-small-minicpm5-2b - -" ;;
    lfm2.5-2.6b-on) echo "logic:lfm2.5-2.6b logic-small-lfm2.5-2.6b - -" ;;
    lfm2.5-8b-a1b-on) echo "logic:lfm2.5-8b-a1b logic-small-lfm2.5-8b-a1b - -" ;;
    # LFM3-1.7B (on) and (off): the server of the published LFM3-1.7B (off) row (vLLM nightly; LFM3-1.7B (on)'s twin
    # lfm3-1.7b-vllm has the same arguments); thinking is set per request by the setup.
    lfm3-1.7b-on|lfm3-1.7b-off) echo "logic:lfm3-1.7b-vllm-rerun logic-small-lfm3-1.7b-vllm-rerun - -" ;;
    qwen3.5-2b-on) echo "logic:qwen3.5-2b logic-small-qwen3.5-2b - -" ;;
    raon-1-nano-on) echo "logic:raon-1-nano - - -" ;;  # KRAFTON's vLLM fork (~/envs/raon-vllm): a process
    smollm2-1.7b) echo "logic:smollm2-1.7b logic-small-smollm2-1.7b - -" ;;
    smollm2-360m) echo "logic:smollm2-360m logic-small-smollm2-360m - -" ;;
    smollm3-3b-off|smollm3-3b-on) echo "logic:smollm3-3b logic-small-smollm3-3b - -" ;;  # thinking per request
    # logic's shared Inkling load (owner receipt in MODELS external): never started or stopped here
    inkling-2-mini-on|inkling-2-mini-e05|inkling-2-mini-e02) echo "external:inkling-2-mini logic-small-inkling-2-mini 18712 -" ;;
    *) return 1 ;;
  esac
}
logic_port() {  # small_models.py SETUPS[KEY]["port"]
  "$PY" -c 'import importlib.util as u, sys; s = u.spec_from_file_location("small_models", sys.argv[1]); m = u.module_from_spec(s); s.loader.exec_module(m); print(m.SETUPS[sys.argv[2]]["port"])' "$SMALL_MODELS" "$1"
}
start_server() {  # script gpu-variable index
  if [[ $1 == logic:* ]]; then python3 "$SMALL_MODELS" serve "${1#logic:}" "$UUID"
  else env "$2=$3" "$SERVERS/$1" start; fi
}
stop_server() {
  if [[ $1 == external:* ]]; then return 0; fi  # its owner's
  if [[ $1 == logic:* ]]; then python3 "$SMALL_MODELS" stop "${1#logic:}"; else "$SERVERS/$1" stop; fi
}
echo "local lane $LANE start $(date -u +%FT%TZ) on $UUID: $*"
for model in "$@"; do
  claim=$RUNS/$model/lane.json
  owner=$([[ -f $claim ]] && "$PY" -c "import json,sys; print(json.load(open(sys.argv[1]))['lane'])" "$claim" || echo "")
  if [[ -n "$owner" && "$owner" != "$LANE" ]]; then echo "== $model: owned by $owner, skipped"; continue; fi
  # Its setup can run now (settings in v3.db, none the pinned runner drops), else no server is started for it.
  "$PY" workspace/improve/improve.py check --model "$model" || { echo "== $model: cannot run now, skipped"; continue; }
  read -r script name port var < <(server "$model") || { echo "unknown local model $model"; exit 1; }
  if [[ $script == logic:* ]]; then
    port=$(logic_port "${script#logic:}") || { echo "$model: no port for ${script#logic:} in $SMALL_MODELS"; exit 1; }
  fi
  if [[ $UUID == external && $script != external:* || $UUID != external && $script == external:* ]]; then
    echo "$model: an external lane (UUID external) runs exactly the models on external servers"; exit 1
  fi
  if [[ $script == external:* ]]; then
    echo "== $model start $(date -u +%FT%TZ) on its owner's server $name :$port (not started or stopped here)"
  else
    index=$(nvidia-smi -i "$UUID" --query-gpu=index,uuid --format=csv,noheader) || { echo "no GPU $UUID"; exit 1; }
    echo "== $model: host GPU $index"
    # Docker's CDI names GPUs by index here, not by UUID: the index the host gives this UUID now, and the
    # container must then report this UUID (checked below).
    start_server "$script" "$var" "${index%%,*}" || { echo "$model: server did not start"; exit 1; }
    if [[ $name == - ]]; then  # a process server: a process of the port's listener's session must hold this GPU
      pid=$(ss -ltnpH "sport = :$port" | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
      # vLLM's GPU process is its engine core, a child of the listener; llama.cpp's is the listener itself
      sid=$([[ -n $pid ]] && ps -o sid= -p "$pid" | tr -d ' ')
      if [[ -n $sid ]] && nvidia-smi -i "$UUID" --query-compute-apps=pid --format=csv,noheader |
          grep -qxF -f <(ps -e -o pid=,sid= | awk -v s="$sid" '$2 == s {print $1}'); then
        seen=$UUID; else seen="pid ${pid:-none} on another GPU"; fi
    else
      seen=$(docker exec "$name" nvidia-smi --query-gpu=uuid --format=csv,noheader | tr -d ' ')
    fi
    if [[ "$seen" != "$UUID" ]]; then
      echo "$model: the server sees '$seen', not $UUID: stopped"; stop_server "$script"; exit 1
    fi
    mkdir -p "$RUNS/$model"
    if [[ $name == - ]]; then
      "$PY" -c 'import json,sys; print(json.dumps(dict(server="process", pid=int(sys.argv[1]), cmdline=open(f"/proc/{sys.argv[1]}/cmdline").read().split("\0")[:-1])))' "$pid" \
        > "$RUNS/$model/server.json"
    else
      docker inspect "$name" --format '{"image": "{{.Config.Image}}", "image_id": "{{.Image}}", "args": {{json .Args}}, "gpus": {{json .HostConfig.DeviceRequests}}}' \
        > "$RUNS/$model/server.json"
    fi
    echo "== $model start $(date -u +%FT%TZ) (container sees $seen)"
  fi
  "$PY" workspace/improve/improve.py run --model "$model" --base-url "http://127.0.0.1:$port/v1"
  code=$?
  echo "== $model exit $code $(date -u +%FT%TZ)"
  "$PY" workspace/improve/improve.py status --model "$model"
  stop_server "$script"
  case $code in
    0|2) continue ;;
    3) echo "local lane paused at $model"; exit 3 ;;
    *) echo "local lane stopped: $model failed"; exit "$code" ;;
  esac
done
echo "local lane $LANE done $(date -u +%FT%TZ)"
