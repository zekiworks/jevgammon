# Sourced by start.sh and locals.sh (KEY, T, URL, PORT and SERVED set there): healthy() and pinned() for the setup's
# server, whoever runs it (logic's small_models.py server on bariton GPU 1 #5080, or ours from serve.sh), read-only.
#   healthy: GET URL/models answers and lists the served model name the setup sends (SERVED).
#   pinned:  the process serving PORT runs the pinned checkpoint: a docker container (vLLM) whose arguments carry
#            --port PORT, the pinned repo with --revision REV (or its snapshot path), BF16, --max-model-len of at least
#            38,000 (the longest League 1 request, at most ~4,750 tokens through the 11 templates, + 32,768 output: never
#            refused for length, never truncated); or, for llama.cpp
#            (LFM3-1.7B), a llama-server on PORT with the pinned GGUF and the pinned repo's chat template.
MODEL=${KEY%-on}
MODEL=${MODEL%-off}
eval "$(python3 - "$T/models.json" "$MODEL" <<'EOF'
import json, shlex, sys
m = json.load(open(sys.argv[1]))[sys.argv[2]]
g = (m["own"].get("gguf") or ["", "", ""])
print(f"PIN_REPO={shlex.quote(m['repo'])} PIN_REV={m['rev']} PIN_GGUF_REV={g[1]} PIN_GGUF_FILE={shlex.quote(g[2])}")
EOF
)"
LABEL="$MODEL ($PIN_REPO@${PIN_REV:0:8})"
MIN_CONTEXT=38000
healthy() {
  curl -fsS -m 10 "$URL/models" 2>/dev/null | python3 -c 'import json,sys; ids=[m["id"] for m in json.load(sys.stdin)["data"]]
sys.exit(sys.argv[1] not in ids)' "$SERVED" 2>/dev/null
}
pinned() {
  local c args
  for c in $(docker ps -q 2>/dev/null); do
    args=$(docker inspect --format '{{join .Args " "}}' "$c" 2>/dev/null) || continue
    [[ " $args " == *" --port $PORT "* ]] || continue
    { [[ " $args " == *" $PIN_REPO "* && " $args " == *" --revision $PIN_REV "* ]] ||
      [[ $args == *"snapshots/$PIN_REV"* ]]; } || return 1
    [[ " $args " == *" --dtype bfloat16 "* ]] || return 1
    python3 -c 'import re,sys; m=re.search(r"--max-model-len[ =](\d+)", sys.argv[1]); sys.exit(not (m and int(m.group(1)) >= int(sys.argv[2])))' \
      "$args" "$MIN_CONTEXT" || return 1
    return 0
  done
  [[ -n $PIN_GGUF_REV ]] || return 1
  pgrep -af llama-server 2>/dev/null | grep -F -- "--port $PORT " | grep -F -- "snapshots/$PIN_GGUF_REV/$PIN_GGUF_FILE" |
    grep -qF -- "snapshots/$PIN_REV/chat_template.jinja"
}
