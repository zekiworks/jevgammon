#!/usr/bin/env bash
# Offline checks of a bariton-served late entry (Ümit #6225: d1-2b, strands-decider-2b, metask-jev-4b; #7649: d1-omni-2b) before its first
# start, without a GPU, a model server or v3.db:
#   1. pins.sh healthy() passes against stub_server.py KIND (the server's own /health shape) and fails with no server;
#   2. pins.sh pinned() against a stand-in process table (a `ps` first on PATH listing a sleeping process that has the
#      pinned server's environment and working directory): passes for the pinned command line (pins.sh SERVE), fails
#      for that line with one more argument and for the right line without the environment;
#   3. a one-round league of KEY v Random through the runner BIN in a scratch database, the player's base_url pointed at
#      the stub (which refuses lists over the client's cap): every entrant decision a valid model answer, nothing
#      refused, no request over the client's option cap (longer lists split into groups).
# Scratch (stub log, config, database) under ~/.cache/late-tiny8-dry/KEY; nothing under the main checkout.
#   dry_run.sh KEY KIND BIN     e.g. dry_run.sh strands-decider-2b strands <target>/debug/jevgammon
set -uo pipefail
KEY=${1:?usage: dry_run.sh KEY KIND BIN}
KIND=${2:?usage: dry_run.sh KEY KIND BIN}
BIN=${3:?usage: dry_run.sh KEY KIND BIN}
T=$(dirname "$(readlink -f "$0")")
[[ -f $T/models/$KEY/player.json && -f $T/models/$KEY/pins.sh ]] || { echo "unknown model $KEY" >&2; exit 1; }
[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
OUT=$HOME/.cache/late-tiny8-dry/$KEY
rm -rf "$OUT" && mkdir -p "$OUT/bin"
failed=0
check() { if "${@:2}"; then echo "ok   $1"; else echo "FAIL $1"; failed=1; fi; }
not() { ! "$@"; }
STUB_PORT=$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
python3 "$T/stub_server.py" "$KIND" "$STUB_PORT" > "$OUT/stub.log" 2>&1 &
STUB=$!
SLEEPER=
trap 'kill $STUB ${SLEEPER:-} 2>/dev/null' EXIT
for _ in $(seq 50); do curl -s -o /dev/null "http://127.0.0.1:$STUB_PORT/stats" && break; sleep 0.1; done

# 1, 2: pins.sh as start.sh sources it (URL, PORT from player.json; the stub's address for healthy()).
URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$T/models/$KEY/player.json")
export PORT=${URL##*:}
. "$T/models/$KEY/pins.sh"
URL=http://127.0.0.1:$STUB_PORT
check "healthy() against the $KIND stub" healthy
URL=http://127.0.0.1:1
check "healthy() fails with no server" not healthy 2>/dev/null
# A sleeping process with the pinned server's environment and working directory stands in for the server; the fake ps
# lists it under the command line given.
fake_ps() { printf '#!/bin/sh\necho "%s %s"\n' "$SLEEPER" "$1" > "$OUT/bin/ps"; chmod +x "$OUT/bin/ps"; }
sleeper() { (cd "${DIR:-/}" && exec env "$@" sleep 300) & SLEEPER=$!; sleep 0.2; }
sleeper HF_HUB_OFFLINE=1 HF_HUB_CACHE="${HF_CACHE:-}"
fake_ps "$SERVE"
check "pinned() with the pinned command line" env PATH="$OUT/bin:$PATH" bash -c ". '$T/models/$KEY/pins.sh'; pinned"
fake_ps "$SERVE --extra"
check "pinned() fails for another command line" not env PATH="$OUT/bin:$PATH" bash -c ". '$T/models/$KEY/pins.sh'; pinned"
kill "$SLEEPER"
sleeper OTHER=1
fake_ps "$SERVE"
check "pinned() fails without the server's environment" not env PATH="$OUT/bin:$PATH" \
  bash -c ". '$T/models/$KEY/pins.sh'; pinned"
kill "$SLEEPER"; SLEEPER=

# 3: the runner's client v Random against the stub.
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/models/$KEY/player.json")
python3 - "$T/models/$KEY/player.json" "http://127.0.0.1:$STUB_PORT" "$OUT/league.json" <<'EOF'
import json, sys
player = json.load(open(sys.argv[1]))
player["base_url"] = sys.argv[2]
cfg = {"note": "late-tiny8 stub dry run (offline)", "seed": 7, "order_seed": 11, "rounds": 1, "max_turns": 300,
       "mirror_concurrent": True, "players": [player, {"name": "Random", "spec": "random", "provider": "local"}]}
json.dump(cfg, open(sys.argv[3], "w"), indent=1)
EOF
(cd "$OUT" && timeout 900 "$BIN" league --config "$OUT/league.json" --db "$OUT/dry.db" > "$OUT/league.log" 2>&1)
check "league v Random finished" grep -q "Final ranking" "$OUT/league.log"
read -r decisions invalid other split < <(sqlite3 -separator ' ' "$OUT/dry.db" "SELECT
    SUM(t.decided_by = 'model'), SUM(COALESCE(t.invalid, 0)), SUM(t.decided_by NOT IN ('model', 'forced', 'no_move')),
    SUM(t.group_size IS NOT NULL)
  FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
  JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END WHERE p.name = '$NAME'")
stats=$(curl -s "http://127.0.0.1:$STUB_PORT/stats")
echo "$NAME: $decisions model decisions, $invalid invalid, $other by fallback or timeout, $split split into groups; stub $stats"
check "every entrant decision a valid model answer" test "${decisions:-0}" -gt 0 -a "${invalid:-1}" = 0 -a "${other:-1}" = 0
check "nothing refused, no request over the cap" python3 -c 'import json,sys; s=json.loads(sys.argv[1])
sys.exit(not (s["refused"] == 0 and s["requests"] > 0 and s["most_options"] <= s["cap"]))' "$stats"
exit $failed
