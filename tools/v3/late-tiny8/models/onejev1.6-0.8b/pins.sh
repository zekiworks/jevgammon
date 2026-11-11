# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/OneJev1.6-0.8B@bcd88a382f314b26cb7b1b7f369c1ed3502ee7a0
LABEL=OneJev
# Flide 0.1.11's /health for the card's name.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin)
sys.exit(not (d["status"] == "ok" and d["model"] == "OmniJev/OneJev1.6-0.8B" and d["engine"] == "flide"
              and d["version"] == "0.1.11"))'
}
# flide serve of the snapshot under the card's name on PORT, from ~/envs/onejev16 (flide 0.1.11).
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" 'ps -eo args; echo @@;
    ~/envs/onejev16/bin/python -c "import flide; print(\"flide\", flide.__version__)"' 2>/dev/null) || return 1
  grep -qxF "flide 0.1.11" <<<"$procs" &&
  grep -F "flide serve --model $SNAPSHOT --name OmniJev/OneJev1.6-0.8B " <<<"$procs" | grep -qF -- "--port $PORT"
}
