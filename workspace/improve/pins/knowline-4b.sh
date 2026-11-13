# Sourced by decision.py server_pin_check (URL, PORT and SSH_HOST set there): KnowLine 4B Gen5.5's snapshot, its /health
# as the pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only). Copied
# from tools/v3/late-knowline4b/start.sh (branch late-knowline4b), the league entry's own checks.
SNAPSHOT=/home/cbasaran/decision-models/KnowLine-4B-Gen5.5@779944d2cc8ffa19cef386aee83c83bcb967ade2
LABEL=KnowLine
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); l=d["layout"]
sys.exit(not (d["status"] == "ok" and d["model"] == "m" and d["temperature"] == 1.0 and l["read_twice"]
              and l["twice_max_tokens"] == 3000 and not l["header"]))'
}
# The pinned snapshot's front end on PORT (serve_knowline.sh's arguments, no temperatures file), behind an SGLang with
# FP8 at load that never truncates (read-only ssh).
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" 'ps -eo args' 2>/dev/null) || return 1
  grep -F "$SNAPSHOT/knowline_server.py --model $SNAPSHOT --backend sglang" <<<"$procs" |
    grep -F -- "--temperature 1 --workers 16 " | grep -F -- "--port $PORT" | grep -vF -- "--temperatures" |
    grep -vF -- "--no-read-twice" | grep -qvF -- "--header" &&
  grep -F "sglang.launch_server --model-path $SNAPSHOT " <<<"$procs" | grep -F -- "--quantization fp8" |
    grep -F -- "--enable-fp32-lm-head" | grep -vqF -- "--allow-auto-truncate"
}
