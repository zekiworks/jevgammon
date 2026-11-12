#!/usr/bin/env bash
# One reproducibility repeat (tools/v3/repeats; manifest mailbox/repeats/manifest-2026-11-11.json), one match at a time,
# as the late entries' start.sh + locals.sh (tools/v3/late-knowline) in one loop:
#   systemd-run --user --unit=repeat-ID --working-directory=/home/cbasaran/code/jevgammon \
#     [-E GPU=<entrant card>] -E OPP_GPU=<card for opponent servers> -E RES=<agent-bus reservation> \
#     /home/cbasaran/code/jevgammon/tools/v3/repeats/run.sh ID
# run.sh ID --prepare-only: the checks and, when needed, the preparation below; nothing starts or plays.
# Every check comes first and writes nothing (repeats.py check): not held (REAX 1.3 never passes), the league config pins
# every opponent to its original match's seed and seating (the league holds the same pins once it exists), the settings
# as the manifest's, the name held in the main checkout's committed site code, the runner binary and every build input
# at the sha256 recorded for the runner build (repeats.py RUNNER: 0e66836, exact commit, clean tree), then client
# admission by that binary (`jevgammon admit` of the league config with the keys loaded as below: every config player's
# and pinned opponent's client built, only decision services and the local engines, v3.db and budget ledgers opened
# read-only and immutable, no request; any refused client fails the check) and the settings it admitted as v3.db holds
# them now (its admitted-settings record against an ordinary read-only read, which sees the write-ahead log: the league
# config's sha256, the config players' rows, each pinned opponent's row and settings sha256; any difference fails), a
# recorded attempt's league exactly as recorded (REAX 1.3's #24 on 4ca4f08, every column of its leagues and
# league_players rows: kept, never resumed; league-id skips it, so the league unit creates a new league for the repeat),
# the name in the late_entry_stage trigger.
# Only "trigger missing" with everything else passing (check exit 3) leads to the one write: a zstd backup of v3.db
# (VACUUM INTO, zstd -t), `repeats.py trigger ID` (itself refused on any other failure), then the complete check again.
# Any other failure exits before anything is written: no backup, no trigger, no state or status file.
# The final check's admitted-settings record is kept as workspace/repeats/ID/admitted.json: the league unit
# (run_league.sh) starts no league unless `repeats.py bound` finds the config and v3.db's settings as admitted, and
# league-add gets each pinned opponent's settings from `repeats.py entry` (the admitted text, else the run stops).
# REPEATS_HOME (default the main checkout: v3.db, workspace/repeats, the status file) and JEVGAMMON_DB (default
# REPEATS_HOME/v3.db) are for the scratch regression tests (tools/v3/repeats/test_launcher.sh).
# The entrant: Mammoth-1 and Drex Max v1 are started here on GPU under RES and smoke-tested as in their originals (and
# stopped at the end); REAX 1.3 must already answer on logic's server (unit logic-dm-reax13, image checked, smoke-tested;
# never started or stopped here); Liquid d1-ultra is hosted. Then each opponent of the plan in turn (programs, paid API,
# local servers smallest first): league-add after confirming nothing plays the league (quiesce), the opponent's server
# under RES on OPP_GPU when there is room beside everything else (a pair that cannot fit on one card with the entrant is
# left missing and reported), the league unit until the pair is played (4 h at most), the server stopped. Opponents
# blocked today (GPT-6 Luna, Mercury Decide) are skipped and reported unless RETRY_BLOCKED=1.
# Guard every minute, stopping the league (matches resume later from their last turn): billed spend of the repeat >= its
# cap ($5; a repeat with a run guard: its ledger's spent + reserved), OpenRouter balance under $40 or unreadable 3 times
# in a row, the entrant failing 3 health checks in a row, a run guard's latch file present.
# A repeat with a run guard (repeats.py GEMINI_GUARD; Zeki #5385) runs its league with `--guard` (run_league.sh): the
# runner reserves every request attempt of the entrant and the paid opponents before sending and refuses past the cap,
# checks every entrant reply's served identity, and on either stop latches (latch file) and ends the league; with the
# latch set the runner starts nothing, check refuses and this loop stops. The guard's ledger is created by the
# preparation (check exit 3 lists it with the trigger).
set -uo pipefail
cd "${REPEATS_HOME:-/home/cbasaran/code/jevgammon}" || exit 1
RID=${1:?usage: run.sh ID [--prepare-only]}
MODE=${2:-}
[[ -z $MODE || $MODE == --prepare-only ]] || { echo "usage: run.sh ID [--prepare-only]" >&2; exit 1; }
export JEVGAMMON_DB=${JEVGAMMON_DB:-$PWD/v3.db}
DB=$JEVGAMMON_DB
T=$(dirname "$(readlink -f "$0")")
R=(python3 "$T/repeats.py")
env_out=$("${R[@]}" env "$RID") || exit 1
eval "$env_out"
STATUS=$PWD/$STATUS
FLOOR=40
UNIT=repeat-$RID-league
W=workspace/repeats
ST=$W/$RID
if [[ -z $MODE ]]; then
  : "${OPP_GPU:?set OPP_GPU}" "${RES:?set RES (agent-bus reservation)}"
  [[ $KIND != ours || -n ${GPU:-} ]] || { echo "set GPU (the entrant's card)" >&2; exit 1; }
fi

# Every check before any write; only the missing trigger is prepared, then everything is checked again.
checked=$("${R[@]}" check "$RID" 2>&1)
rc=$?
prepared=
if (( rc == 3 )); then
  raw=${DB%.db}-before-$RID.db
  bak=$DB.bak-$(date -u +%Y%m%dT%H%M%S)-before-$RID.zst
  fail() { echo "$1" >&2; rm -f "$raw"; exit 1; }
  rm -f "$raw"
  sqlite3 "$DB" "VACUUM INTO '$raw'" || fail "VACUUM INTO $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  out=$("${R[@]}" trigger "$RID" 2>&1) || fail "trigger failed: $out"
  prepared="backup $bak verified; $out"
  checked=$("${R[@]}" check "$RID" 2>&1)
  rc=$?
  (( rc == 0 )) || fail "the check after the preparation fails (exit $rc): $checked"
elif (( rc != 0 )); then
  echo "check refused (exit $rc); nothing written: $checked" >&2
  exit 1
fi
# check's last line, the settings it admitted (repeats.py ADMITTED), is kept for the league unit and league-add.
admitted=$(sed -n 's/^admitted-settings //p' <<< "$checked")
checked=$(grep -v '^admitted-settings ' <<< "$checked")
[[ -n $admitted ]] || { echo "the check passed without an admitted-settings record: $checked" >&2; exit 1; }

mkdir -p "$ST" "$(dirname "$STATUS")"
rm -f "$ST/done"
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state of the reproducibility repeats (run, smoke and server logs, flags) per repeat id" \
  "reason: Ümit via Zeki #4663/#4666/#4667/#4671; scripts tools/v3/repeats, manifest mailbox/repeats/manifest-2026-11-11.json" \
  "delete when: after the repeats are reported (their matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ) (Can #3774)" > $W/METADATA
[[ -e $STATUS ]] || printf '# Repeat %s - status\n\n%s, run %s. Manifest: mailbox/repeats/manifest-2026-11-11.json.\n\n## Log\n' \
  "$RID" "$NAME" "$RUN_ID" > "$STATUS"
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$ST/run.log"; echo "- $line" >> "$STATUS"; }
[[ -z $prepared ]] || { log "$prepared"; touch "$ST/prepared"; }
log "check: $checked"
[[ -z $MODE ]] || exit 0
printf '%s\n' "$admitted" > "$ST/admitted.json"
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
export PATH=$HOME/.local/bin:$PATH
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { "${R[@]}" billed "$RID"; }
pending() { "${R[@]}" pending "$RID" "$@"; }
healthy() {
  [[ -z $HEALTH ]] && return 0
  if [[ $HEALTH_ANY == 1 ]]; then curl -sS -m 10 -o /dev/null "$HEALTH" 2>/dev/null; else curl -fsS -m 10 -o /dev/null "$HEALTH" 2>/dev/null; fi
}
room() { nvidia-smi -i "$1" --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print $1-$2}'; }
gpus() { nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '; }

ID=
quiesce() {
  local load state found
  if ! systemctl --user stop "$UNIT" 2>/dev/null; then
    load=$(systemctl --user show -p LoadState --value "$UNIT" 2>/dev/null)
    [[ $load == not-found ]] || { log "stopping $UNIT failed (LoadState ${load:-unknown})"; return 1; }
  fi
  state=$(systemctl --user is-active "$UNIT" 2>/dev/null)
  [[ $state == inactive || $state == failed ]] || { log "$UNIT is ${state:-of unknown state} after the stop"; return 1; }
  pgrep -f -- "repeats/run_league\.sh ${RID//./\\.} |league --resume ${ID:-none} --db|league --config [^ ]*repeats/leagues/${RID//./\\.}\.json" \
    >/dev/null 2>&1
  found=$?
  (( found == 1 )) || { log "a league runner for $RID may still run (pgrep exit $found)"; return 1; }
}
ensure_league() {
  systemctl --user is-active -q "$UNIT" && return 0
  systemctl --user reset-failed "$UNIT" >/dev/null 2>&1 || true
  systemd-run --user --quiet --unit="$UNIT" --working-directory="$PWD" "$T/run_league.sh" "$RID" "$BIN" "$DB" \
    "$PWD/$ST/admitted.json" "$GUARD"
}
down=0
unread=0
guard() {
  local bal s
  if [[ -n $GUARD_LATCH && -e $GUARD_LATCH ]]; then
    log "STOPPED: the run guard is latched ($GUARD_LATCH): $(head -c 600 "$GUARD_LATCH" | tr '\n' ' ')"; return 1
  fi
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then log "STOPPED: OpenRouter balance \$$bal under \$$FLOOR"; return 1; fi
  else
    unread=$((unread + 1))
    (( unread < 3 )) || { log "STOPPED: OpenRouter balance unreadable 3 times in a row"; return 1; }
  fi
  s=$(spent)
  lt "$s" "$CAP" || { log "STOPPED: billed \$$s reached the \$$CAP cap"; return 1; }
  if healthy; then down=0; else down=$((down + 1)); fi
  (( down < 3 )) || { log "STOPPED: $NAME's server $HEALTH failed 3 health checks in a row"; return 1; }
}
ours_up=0
finish() {
  systemctl --user stop "$UNIT" 2>/dev/null
  [[ -n ${opp_stop:-} ]] && bash -c "$opp_stop" >> "$ST/servers.log" 2>&1
  (( ours_up )) && bash -c "$STOP" >> "$ST/servers.log" 2>&1
  log "$1; billed \$$(spent); OpenRouter \$$(balance || echo unreadable); GPUs: $(gpus)"
}

bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }
case $KIND in
  ours)
    if ! healthy; then
      until (( $(room "$GPU") >= ENTRANT_MIB + 2000 )); do sleep 60; done
      agent-bus run "$RES" -- bash -c "g=$GPU; $START" >> "$ST/servers.log" 2>&1 ||
        { bash -c "$STOP" >> "$ST/servers.log" 2>&1; log "STOPPED: $NAME's server did not start on GPU $GPU"; exit 1; }
      ours_up=1
      log "started $NAME's server on GPU $GPU ($(gpus))"
    fi ;;
  logic)
    healthy || { log "STOPPED before any match: logic's REAX server $HEALTH does not answer"; exit 1; }
    img=$(docker inspect -f '{{.Image}}' logic-dm-reax13 2>/dev/null)
    want=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import repeats; print(repeats.LOGIC_REAX["image"])' "$T")
    [[ $img == "$want" ]] || { log "STOPPED before any match: logic-dm-reax13 runs image ${img:-none}, not $want"; exit 1; }
    log "REAX on logic's server $HEALTH, image $img" ;;
esac
if [[ -n $SMOKE ]]; then
  if bash -c "$SMOKE" >> "$ST/smoke.log" 2>&1; then
    log "smoke test passed ($(tail -1 "$ST/smoke.log"))"
  else
    finish "STOPPED: smoke test failed ($ST/smoke.log)"; exit 1
  fi
fi
log "repeat up: $NAME, runner $BIN; OpenRouter \$$bal (floor \$$FLOOR); cap \$$CAP; opponents on GPU $OPP_GPU (reservation $RES)"

missing=()
opp_stop=
while IFS='|' read -r -u 3 name kind mib start stop blocked; do
  [[ $(pending "$name") == 0 ]] && continue
  if [[ -n $blocked && ${RETRY_BLOCKED:-} != 1 ]]; then
    log "$name: skipped, blocked today (manifest blockers_today)"; missing+=("$name (blocked)"); continue
  fi
  if [[ $kind != program ]]; then
    ID=$("${R[@]}" league-id "$RID")
    if [[ -z $ID ]]; then
      ensure_league
      for _ in $(seq 60); do ID=$("${R[@]}" league-id "$RID"); [[ -n $ID ]] && break; sleep 10; done
      [[ -n $ID ]] || { finish "STOPPED: the league did not appear in v3.db"; exit 1; }
    fi
    quiesce || { finish "STOPPED before adding $name: league #$ID not confirmed stopped"; exit 1; }
    if ! sqlite3 -readonly "$DB" "SELECT 1 FROM league_players lp JOIN players p ON p.id = lp.player_id
         WHERE lp.league_id = $ID AND lp.left_at IS NULL AND p.name = '${name//\'/\'\'}'" | grep -q 1; then
      entry=$("${R[@]}" entry "$RID" "$name" "$ST/admitted.json" 2>&1) ||
        { finish "STOPPED before adding $name: $entry"; exit 1; }
      pin=$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["pinned_pairs"][sys.argv[2]]))' \
        "$T/leagues/$RID.json" "$name")
      "$BIN" league-add --db "$DB" --league "$ID" --entry "$entry" --pin "$pin" >> "repeat-$RID.log" 2>&1 ||
        { log "league-add of $name failed"; missing+=("$name (league-add failed)"); continue; }
      log "$name added to league #$ID"
    fi
  fi
  guard || { finish "stopped by the guard"; exit 1; }
  if [[ $kind == local ]]; then
    beside=0
    [[ $KIND == ours || $KIND == logic ]] && [[ $OPP_GPU == "${GPU:-}" ]] && beside=$ENTRANT_MIB
    if (( beside + mib + 2000 > 97887 )); then
      log "$name: does not fit on GPU $OPP_GPU beside $NAME ($beside + $mib MiB); its pair stays missing (needs a second card)"
      missing+=("$name (needs a second GPU)"); continue
    fi
    t0=$SECONDS
    until (( $(room "$OPP_GPU") >= mib + 2000 )) || (( SECONDS - t0 > 7200 )); do sleep 60; done
    if (( $(room "$OPP_GPU") < mib + 2000 )); then
      log "$name: no room on GPU $OPP_GPU after 2 h ($(gpus)); its pair stays missing"; missing+=("$name (no room)"); continue
    fi
    if ! agent-bus run "$RES" -- bash -c "g=$OPP_GPU; $start" >> "$ST/servers.log" 2>&1; then
      bash -c "$stop" >> "$ST/servers.log" 2>&1
      log "$name did not start on GPU $OPP_GPU ($ST/servers.log); its pair stays missing"; missing+=("$name (server)"); continue
    fi
    opp_stop=$stop
    log "started $name on GPU $OPP_GPU ($(gpus))"
  fi
  t0=$SECONDS
  until [[ $(pending "$name") == 0 ]] || (( SECONDS - t0 > 14400 )); do
    guard || { finish "stopped by the guard during $name"; exit 1; }
    ensure_league; sleep 60
  done
  if [[ -n $opp_stop ]]; then bash -c "$opp_stop" >> "$ST/servers.log" 2>&1; opp_stop=; fi
  if [[ $(pending "$name") == 0 ]]; then log "$name played"; else log "$name not played within 4 h; pair missing"; missing+=("$name (4 h)"); fi
done 3< <("${R[@]}" plan "$RID")
finish "done: $("${R[@]}" pending "$RID") of the original's played pairs still open${missing:+; missing: ${missing[*]}}"
touch "$ST/done"
