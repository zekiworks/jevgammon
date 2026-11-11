# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/glide-family/models/GLiDE-2B@00f122c120cdeed82284106cb77d9bab5a50ad16
LABEL=GLiDE
# glide.server's /health: one request at a time (GLIDE_MAX_BATCH=1), BF16 (no NVFP4), GLIDE_MAX_LEN 40000.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d["status"] == "ok" and d["max_len"] == 40000 and d["max_batch"] == 1 and d["quantization"] is None))'
}
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" 'ps -eo args' 2>/dev/null) || return 1
  grep -F -- "-m glide.server --model $SNAPSHOT " <<<"$procs" | grep -qF -- "--port $PORT"
}
