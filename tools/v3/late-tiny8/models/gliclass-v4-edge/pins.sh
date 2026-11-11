# Sourced by start.sh and locals.sh (URL, PORT and SSH_HOST set there): the model's snapshot, its /health as the
# pinned server answers it, and pinned(): the pinned server process on PORT, read over ssh (read-only).
SNAPSHOT=/home/cbasaran/decision-models/gliclass-v4-edge@885af1af8a07edf4ed34df83ca0d995ed8201283
LABEL=GLiClass
SERVER=/home/cbasaran/decision-src/gliclass_server.py
SERVER_SHA=aa39e5f435c74f64b6ec905c2965d0ae5b76fa68b7bbf48f7c8a46bde52229e1
# gliclass_server.py has no GET route: any HTTP answer (its 501 for GET) means it is up; pinned() names the server.
healthy() {
  local code
  code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$URL/health")
  [[ -n $code && $code != 000 ]]
}
# The pinned server file (sha256) serving the snapshot on cuda:0 at PORT with its default 16,384-token limit.
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo args; echo @@; sha256sum $SERVER" 2>/dev/null) || return 1
  grep -qF "$SERVER_SHA  $SERVER" <<<"$procs" &&
  grep -F "$SERVER --model $SNAPSHOT --device cuda:0 " <<<"$procs" | grep -F -- "--port $PORT" |
    grep -vF -- "--max-length" | grep -qvF -- "--revision"
}
