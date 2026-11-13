# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/KnowLine-2B-Gen1@53245d470a4ce316e32fd0d18c24e142c697f40b
LABEL=KnowLine
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); l=d["layout"]
sys.exit(not (d["status"] == "ok" and d["model"] == "m" and d["temperature"] == 1.0 and l["read_twice"]
              and l["twice_max_tokens"] == 3000 and not l["header"]))'
}
# serve_knowline.sh's front end on PORT with the card's temperatures file, behind an SGLang in BF16 (no
# --quantization) that never truncates (no --allow-auto-truncate).
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" 'ps -eo args' 2>/dev/null) || return 1
  grep -F "$SNAPSHOT/knowline_server.py --model $SNAPSHOT --backend sglang" <<<"$procs" |
    grep -F -- "--temperature 1 --workers 16 " | grep -F -- "--port $PORT " |
    grep -F -- "--temperatures $SNAPSHOT/temperatures.json" | grep -vF -- "--no-read-twice" | grep -qvF -- "--header" &&
  grep -F "sglang.launch_server --model-path $SNAPSHOT " <<<"$procs" | grep -F -- "--enable-fp32-lm-head" |
    grep -vF -- "--quantization" | grep -vqF -- "--allow-auto-truncate"
}
