# Shared helpers for the v3 model-server scripts. Sourced, not run.
#
# vLLM servers run as docker containers (docker run -d, no restart policy); the Python
# decision servers run as transient systemd --user units (systemd-run), so they outlive the
# shell that started them and log to the journal: journalctl --user -u <unit>.

set -euo pipefail

HF_HUB=/home/cbasaran/.cache/huggingface/hub

# Address the decision servers listen on: this machine only, or 0.0.0.0 when they serve
# League 1 from the DGX Sparks (spark.sh).
BIND_HOST=${BIND_HOST:-127.0.0.1}

# docker_gpu N: docker options for GPU N. The nvidia runtime is registered here, not on the
# Sparks, where --gpus alone works.
docker_gpu() {
  if docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q '"nvidia"'; then
    echo --runtime nvidia --gpus "\"device=$1\""
  else
    echo --gpus "\"device=$1\""
  fi
}

# free_page_cache: on a DGX Spark (unified memory) CUDA reports MemFree as free GPU memory,
# so the page cache left by loading checkpoints counts as used, and vLLM's and Decider's
# start-up memory checks fail. Touching anonymous memory up to MemAvailable makes the kernel
# drop that cache (no root needed); the memory is returned when the process exits.
free_page_cache() {
  python3 - <<'EOF'
import mmap
GIB = 1 << 30
meminfo = {l.split(':')[0]: int(l.split()[1]) * 1024 for l in open('/proc/meminfo')}
chunks, block = [], b'\1' * GIB
for _ in range(max(0, (meminfo['MemAvailable'] - 6 * GIB) // GIB)):
    m = mmap.mmap(-1, GIB)
    m.write(block)
    chunks.append(m)
EOF
  echo "free memory: $(awk '/MemFree/ {printf "%.0f GiB", $2 / 1048576}' /proc/meminfo)"
}

die() { echo "$*" >&2; exit 1; }

port_busy() { ss -ltnH "sport = :$1" | grep -q .; }

# docker_up NAME PORT ARGS...: start a container (removing a stopped one of the same name).
docker_up() {
  local name=$1 port=$2; shift 2
  if [[ -n "$(docker ps -q -f "name=^${name}\$")" ]]; then
    echo "$name: already running"; return 0
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  port_busy "$port" && die "$name: port $port is in use by something else"
  docker run -d --name "$name" "$@" >/dev/null
  echo "$name: container started"
}

# docker_wait NAME URL SECONDS: wait for URL, failing early if the container exits.
docker_wait() {
  local name=$1 url=$2 timeout=$3 start=$SECONDS
  until curl -fsS -m 5 -o /dev/null "$url" 2>/dev/null; do
    if [[ -z "$(docker ps -q -f "name=^${name}\$")" ]]; then
      docker logs --tail 30 "$name" >&2 || true
      die "$name: container exited before it was ready"
    fi
    (( SECONDS - start < timeout )) || die "$name: not ready after ${timeout}s ($url)"
    sleep 10
  done
  echo "$name: ready after $((SECONDS - start))s ($url)"
}

docker_down() {
  local name=$1
  if docker inspect "$name" >/dev/null 2>&1; then
    docker stop -t 60 "$name" >/dev/null 2>&1 || true
    docker rm -f "$name" >/dev/null 2>&1 || true
    echo "$name: stopped"
  else
    echo "$name: not running"
  fi
}

# http_reach URL: "http <code>" or "not answering".
http_reach() {
  local code
  code=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null) || true
  [[ ${code:-000} == 000 ]] && echo 'not answering' || echo "http $code"
}

docker_status() {
  local name=$1 url=$2 state
  state=$(docker ps -a -f "name=^${name}\$" --format '{{.Status}}')
  printf '%-28s %-26s %s\n' "$name" "${state:-absent}" "$(http_reach "$url")"
}

# unit_up UNIT PORT WORKDIR [systemd-run -E/-p options...] -- COMMAND...
unit_up() {
  local unit=$1 port=$2 workdir=$3; shift 3
  if systemctl --user is-active -q "$unit"; then
    echo "$unit: already running"; return 0
  fi
  systemctl --user reset-failed "$unit" >/dev/null 2>&1 || true
  port_busy "$port" && die "$unit: port $port is in use by something else"
  local opts=()
  while [[ $1 != -- ]]; do opts+=("$1"); shift; done
  shift
  systemd-run --user --quiet --unit="$unit" --working-directory="$workdir" \
    -p KillMode=mixed -p TimeoutStopSec=60 -E PYTHONUNBUFFERED=1 -E HF_HUB_OFFLINE=1 \
    -E CUDA_DEVICE_ORDER=PCI_BUS_ID "${opts[@]}" "$@"
  echo "$unit: started (journalctl --user -u $unit)"
}

# unit_wait UNIT URL SECONDS: wait for URL, failing early if the unit dies.
unit_wait() {
  local unit=$1 url=$2 timeout=$3 start=$SECONDS
  until curl -fsS -m 5 -o /dev/null "$url" 2>/dev/null; do
    if ! systemctl --user is-active -q "$unit"; then
      journalctl --user -u "$unit" -n 30 --no-pager >&2 || true
      die "$unit: exited before it was ready"
    fi
    (( SECONDS - start < timeout )) || die "$unit: not ready after ${timeout}s ($url)"
    sleep 5
  done
  echo "$unit: ready after $((SECONDS - start))s ($url)"
}

# unit_wait_port UNIT PORT SECONDS: for servers without a GET endpoint (they bind the port
# only once the model is loaded).
unit_wait_port() {
  local unit=$1 port=$2 timeout=$3 start=$SECONDS
  until port_busy "$port"; do
    if ! systemctl --user is-active -q "$unit"; then
      journalctl --user -u "$unit" -n 30 --no-pager >&2 || true
      die "$unit: exited before it was ready"
    fi
    (( SECONDS - start < timeout )) || die "$unit: port $port not open after ${timeout}s"
    sleep 5
  done
  echo "$unit: listening after $((SECONDS - start))s (port $port)"
}

unit_down() {
  local unit=$1
  if systemctl --user is-active -q "$unit"; then
    systemctl --user stop "$unit"
    echo "$unit: stopped"
  else
    echo "$unit: not running"
  fi
  systemctl --user reset-failed "$unit" >/dev/null 2>&1 || true
}

# unit_status UNIT URL|port:N
unit_status() {
  local unit=$1 probe=$2 reach
  if [[ $probe == port:* ]]; then
    port_busy "${probe#port:}" && reach="listening on ${probe#port:}" || reach='not listening'
  else
    reach=$(http_reach "$probe")
  fi
  printf '%-28s %-26s %s\n' "$unit" "$(systemctl --user is-active "$unit" 2>/dev/null || true)" "$reach"
}

# systemone_probe URL MODEL: a 2-option Choice request; prints the answer.
systemone_probe() {
  local url=$1 model=$2 body
  body='{"state":"Probe: the answer is yes.","questions":{"play":{"type":"choice","instructions":"Pick the option that matches the state.","criteria":{"yes":"The answer is yes.","no":"The answer is no."}}}}'
  [[ -n $model ]] && body="{\"model\":\"$model\",${body#\{}"
  curl -fsS -m 300 "$url/v1/systemone" -H 'Content-Type: application/json' -d "$body"
  echo
}
