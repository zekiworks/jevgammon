# Did they improve? Deterministic gate for the GPU-0 lane's next launch (Zeki #3392)

## Ordering evidence
The GPU-0 lane (`improve-local`, shell pid 806805, started 2026-11-09 01:52 UTC) runs the script it loaded then. The file was later replaced by rename; the running copy was read from `/proc/806805/fd/255`. The relevant lines:

```
40	  "$PY" workspace/improve/improve.py run --model "$model" --base-url "http://127.0.0.1:$port/v1"   # Gemma's run (pid 812671)
41	  code=$?
42	  echo "== $model exit $code $(date -u +%FT%TZ)"
43	  "$PY" workspace/improve/improve.py status --model "$model"     # external, fresh; exit ignored
44	  "$SERVERS/$script" stop                                          # gemma4-31b.sh stop; exit ignored
45	  case $code in
46	    0|2) continue ;;                                               # next model: qwen3.8-27b-on
47	    3) echo "local lane paused at $model"; exit 3 ;;
48	    *) echo "local lane stopped: $model failed"; exit "$code" ;;
...
25	  read -r script name port var < <(server "$model") || ...        # in-memory function
26	  index=$(nvidia-smi -i "$UUID" --query-gpu=index,uuid --format=csv,noheader) || ...
27	  echo "== $model: host GPU $index"
28	  case $UUID in GPU-e4f2a538*) ... exit 1 ;; esac                  # not taken (UUID GPU-1115ade0)
31	  env "$var=${index%%,*}" "$SERVERS/$script" start || { echo "$model: server did not start"; exit 1; }   # <- GATE
32	  seen=$(docker exec "$name" nvidia-smi ...)
33	  if [[ "$seen" != "$UUID" ]]; then
34	    echo ...; "$SERVERS/$script" stop; exit 1                      # only reached after a successful start
```

- After Gemma's run exits, the only external files the loop executes fresh are `improve.py status` (line 43) and `gemma4-31b.sh stop` (line 44). Their exit codes are ignored, and both are Gemma's own.
- The loop then runs `nvidia-smi` and executes `tools/v3/servers/qwen38-27b.sh start` (line 31). A non-zero exit there runs `exit 1` with no `stop` call. Lines 32-34, including line 34's `stop`, are reached only after a successful start.
- So the first external file whose result decides the next launch is the league server script at line 31. The gate sits at its top, before `_lib.sh` is sourced, before any docker call.

## The gate
- `tools/v3/servers/qwen38-27b.sh` and `lfm25-24b.sh` (the two models the GPU-0 loop still lists) check, before anything else, the caller's systemd unit (`/proc/$$/cgroup`, inherited from the lane's unit). If that unit is listed in the gate file `workspace/improve/runs/server_gate.txt`, the script prints a refusal and exits 3 with no side effect. The gate file currently holds one line: `improve-local.service`. The gate applies to every action (`start`, `stop`, `status`, `probe`).
- Live cgroups: the GPU-0 lane's shell is `…/app.slice/improve-local.service`; lane 3 is `…/app.slice/improve-local3.service` (not listed). League use from a shell or other units is not listed and is unaffected.
- Outcome for the GPU-0 lane: after Gemma's run it stops Gemma's server (line 44), tries `qwen38-27b.sh start`, is refused, prints "server did not start" and exits 1. It never touches `v3-qwen38-27b` or `v3-lfm25-24b`.
- The guard (`improve-lane0-guard`) stays as a second layer.

## Tests (no GPU, no model; `test-output.txt`)
- **T1:** the old loop's lines 15-34 verbatim (UUID GPU-1115ade0, models qwen3.8-27b-on, lfm2.5-24b-a2b-on) run in a transient unit `improve-gatetest-local`, listed in a test gate file. Result: `qwen38-27b.sh start: refused…`, "server did not start", exit 1. Lane 3's running container `v3-qwen38-27b` is unchanged (same Id and StartedAt before and after, still running).
- **T1b/c:** in that unit, `lfm25-24b.sh start`, `qwen38-27b.sh stop` and `lfm25-24b.sh stop` are each refused (exit 3); the lane-3 container is unchanged.
- **T2:** a unit not in the gate file (`improve-gatetest-lane3`) runs `qwen38-27b.sh status` → allowed (exit 0).
- **T3:** a plain shell (league use) with the real gate file runs `qwen38-27b.sh status` → allowed (exit 0).

### test-output.txt
```
### T1: old-loop sequence in unit improve-gatetest-local (listed in the gate file)
== qwen3.8-27b-on: host GPU 0, GPU-1115ade0-3068-1856-5889-5855079d97f7
qwen38-27b.sh start: refused for improve-gatetest-local.service (lane gate /tmp/gatetest/gate.txt)
qwen3.8-27b-on: server did not start
exit 1
lane-3 container after: true 2026-11-09T07:44:25.59814031Z 01b4e0e1a93e220ef0f5203bb8a6c032a00fcf16664eb37a29b16b9bc7af75a6
lane-3 container untouched: yes
### T1b/c: lfm25-24b.sh start in unit improve-gatetest-local (listed)
lfm25-24b.sh start: refused for improve-gatetest-local.service (lane gate /tmp/gatetest/gate.txt)
exit 3
### T1b/c: qwen38-27b.sh stop in unit improve-gatetest-local (listed)
qwen38-27b.sh stop: refused for improve-gatetest-local.service (lane gate /tmp/gatetest/gate.txt)
exit 3
### T1b/c: lfm25-24b.sh stop in unit improve-gatetest-local (listed)
lfm25-24b.sh stop: refused for improve-gatetest-local.service (lane gate /tmp/gatetest/gate.txt)
exit 3
lane-3 container now: true 2026-11-09T07:44:25.59814031Z
### T2: unit improve-gatetest-lane3 (not listed), same gate file: qwen38-27b.sh status (read-only)
v3-qwen38-27b                Up 8 minutes               http 200
exit 0
### T3: plain shell (leagues), real gate file (lists improve-local.service): qwen38-27b.sh status
v3-qwen38-27b                Up 8 minutes               http 200
exit 0
### T4: the live lane units' cgroups
improve-local (pid 806805): 0::/user.slice/user-1000.slice/user@1000.service/app.slice/improve-local.service
improve-local3: 0::/user.slice/user-1000.slice/user@1000.service/app.slice/improve-local3.service
```

### oldloop_step.sh (the simulation)
```bash
#!/usr/bin/env bash
# Lines 15-34 of the GPU-0 lane's in-memory run_local.sh (pid 806805), for the step after Gemma: model qwen3.8-27b-on.
set -uo pipefail
UUID=GPU-1115ade0-3068-1856-5889-5855079d97f7
SERVERS=/home/cbasaran/code/jevgammon/tools/v3/servers
server() {  # model key -> "script name port gpu-variable"
  case $1 in
    gemma-4-31b-on) echo "gemma4-31b.sh v3-gemma4-31b 8894 GEMMA_GPU" ;;
    qwen3.8-27b-on) echo "qwen38-27b.sh v3-qwen38-27b 8897 QWEN27_GPU" ;;
    lfm2.5-24b-a2b-on) echo "lfm25-24b.sh v3-lfm25-24b 8898 LFM_GPU" ;;
    *) return 1 ;;
  esac
}
for model in "$@"; do
  read -r script name port var < <(server "$model") || { echo "unknown local model $model"; exit 1; }
  index=$(nvidia-smi -i "$UUID" --query-gpu=index,uuid --format=csv,noheader) || { echo "no GPU $UUID"; exit 1; }
  echo "== $model: host GPU $index"
  case $UUID in GPU-e4f2a538*) echo "refused: GPU-e4f2a538 is off limits (hardware failure 2026-11-08)"; exit 1 ;; esac
  env "$var=${index%%,*}" "$SERVERS/$script" start || { echo "$model: server did not start"; exit 1; }
  seen=$(docker exec "$name" nvidia-smi --query-gpu=uuid --format=csv,noheader | tr -d ' ')
  if [[ "$seen" != "$UUID" ]]; then
    echo "$model: the container sees '$seen', not $UUID: stopped"; "$SERVERS/$script" stop; exit 1
  fi
  echo "UNEXPECTED: reached past the start"
done
```
