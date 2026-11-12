#!/usr/bin/env bash
# Our own server for one small chat model (MODEL: a key of models.json) on bariton GPU GPU, the fallback when logic's
# server (#5080) is not used, and the only route for Gemma 4 E4B and LFM2.5-8B-A1B (not in logic's list). Never started
# by start.sh; serves on logic's port and served name for the model (models.json), so the setup's settings are the
# same on either route, and so never next to logic's server for the same model; one model per card; the card must be empty (refused otherwise, never freed).
#   tools/v3/late-smallchat/serve.sh MODEL GPU start|stop|status        (UTIL=share, default 0.85)
# vLLM: as logic's small_models.py serve (vLLM v0.30.0 BF16 from the pinned repo/revision, served name MODEL, context
# 69,632 = 65,536 + 4,096, 16 sequences, chunked prefill, prefix caching, --generation-config auto, the model's reasoning
# parser): the same arguments as logic's container logic-small-MODEL (read with docker inspect on 12 Nov for
# lfm2.5-2.6b), here bound to 127.0.0.1:PORT; top-20 logprobs are vLLM's default limit.
# llama.cpp (LFM3-1.7B, Spark-X2.6-4B: not in vLLM v0.30.0): logic's build and arguments (official BF16 GGUF, the
# pinned repo's chat_template.jinja, --reasoning-format deepseek), 16 slots of 69,632 tokens.
# Spark-X2.6-4B: llama.cpp too (vLLM v0.30.0 has no Spark2_5ForCausalLM), with the official GGUF logic serves (#5091).
source "$(dirname "$(readlink -f "$0")")/../servers/_lib.sh"
T=$(dirname "$(readlink -f "$0")")
MODEL=${1:?usage: serve.sh MODEL GPU start|stop|status}
GPU=${2:?usage: serve.sh MODEL GPU start|stop|status}
CMD=${3:?usage: serve.sh MODEL GPU start|stop|status}
CONTEXT=69632
IMAGE=vllm/vllm-openai:v0.30.0
LLAMA_SERVER=/home/cbasaran/code/llama.cpp/build-cuda/bin/llama-server
eval "$(python3 - "$T/models.json" "$MODEL" <<'EOF'
import json, shlex, sys
m = json.load(open(sys.argv[1])).get(sys.argv[2]) or sys.exit(f"echo 'unknown model {sys.argv[2]}' >&2; exit 1")
own = m["own"]
print(f"REPO={shlex.quote(m['repo'])} REV={m['rev']} SERVER={own['server']} PORT={own['port']}")
print("ARGS=(" + " ".join(shlex.quote(a) for a in own.get("args", [])) + ")")
print(f"BLOCKER={shlex.quote(own.get('blocker', ''))}")
g = own.get("gguf") or ["", "", ""]
print(f"GGUF_REPO={shlex.quote(g[0])} GGUF_REV={g[1]} GGUF_FILE={shlex.quote(g[2])}")
EOF
)"
NAME=v3-smallchat-$MODEL
SNAP=$HF_HUB/models--${REPO//\//--}/snapshots/$REV
URL=http://127.0.0.1:$PORT/v1/models
[[ $SERVER == none ]] && die "$MODEL: no server route: $BLOCKER"
[[ -d $SNAP ]] || die "$REPO@$REV is not in the HF cache ($SNAP)"

empty_gpu() {
  local used apps
  used=$(nvidia-smi -i "$GPU" --query-gpu=memory.used --format=csv,noheader,nounits) || die "GPU $GPU unreadable"
  apps=$(nvidia-smi -i "$GPU" --query-compute-apps=pid --format=csv,noheader | grep -c .)
  (( used < 1024 && apps == 0 )) || die "GPU $GPU is not empty ($used MiB, $apps processes): one model per card, never freed"
}

case $CMD in
  start)
    empty_gpu
    if [[ $SERVER == vllm ]]; then
      # shellcheck disable=SC2046
      docker_up "$NAME" "$PORT" $(docker_gpu "$GPU") --ipc host -p "127.0.0.1:$PORT:$PORT" \
        -e HF_HOME=/root/.cache/huggingface -e HF_HUB_OFFLINE=1 \
        -v "$(dirname "$HF_HUB"):/root/.cache/huggingface:ro" \
        --entrypoint vllm "$IMAGE" serve "$REPO" --revision "$REV" --tokenizer-revision "$REV" \
        --served-model-name "$MODEL" --host 0.0.0.0 --port "$PORT" --dtype bfloat16 --max-model-len $CONTEXT \
        --max-num-seqs 16 --gpu-memory-utilization "${UTIL:-0.85}" --tensor-parallel-size 1 \
        --enable-chunked-prefill --enable-prefix-caching --generation-config auto "${ARGS[@]}"
      docker_wait "$NAME" "$URL" 1800
    else
      GGUF=$HF_HUB/models--${GGUF_REPO//\//--}/snapshots/$GGUF_REV/$GGUF_FILE
      [[ -f $GGUF ]] || die "$GGUF missing"
      unit_up "$NAME" "$PORT" "$T" -E CUDA_VISIBLE_DEVICES="$GPU" -- \
        "$LLAMA_SERVER" -m "$GGUF" --alias "$MODEL" --host 127.0.0.1 --port "$PORT" -ngl 999 -fa on -np 16 \
        -c $((CONTEXT * 16)) --jinja --chat-template-file "$SNAP/chat_template.jinja" --reasoning-format deepseek --no-webui
      unit_wait "$NAME" "$URL" 600
    fi
    ;;
  stop)
    if [[ $SERVER == vllm ]]; then docker_down "$NAME"; else systemctl --user stop "$NAME" 2>/dev/null; echo "$NAME: stopped"; fi
    ;;
  status)
    if [[ $SERVER == vllm ]]; then docker_status "$NAME" "$URL"; else
      printf '%-28s %-26s %s\n' "$NAME" "$(systemctl --user is-active "$NAME")" "$(http_reach "$URL")"; fi
    ;;
  *) die "usage: serve.sh MODEL GPU start|stop|status" ;;
esac
