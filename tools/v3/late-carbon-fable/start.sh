#!/usr/bin/env bash
# Late entry of ENTRANT (carbon: Gemini 4 Carbon (high) on OpenRouter pinned to Google AI Studio, paid; fable: Claude
# Fable 5.2 (max) on the Claude subscription) v the original League 1 table (Ümit via Zeki #4676), stage 1: the 3 programs and the paid
# API setups (GPT-6 Luna deferred while OpenAI is out of credit), as tools/v3/late-knowline4b/start.sh. Stage 2 (the 8
# local setups, one opponent server at a time on a GPU Main hands over) is locals.sh. Status: mailbox/Late entries
# <name> - status.md (main checkout); state workspace/late-carbon-fable/<ENTRANT>/state.
#   systemd-run --user --unit=late-carbon --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
#     /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/start.sh carbon
#   (fable: --unit=late-fable ... start.sh fable; only once the Claude lane improve-subs-claude has ended)
# Before anything: the runner tree is clean; no run of this entrant is going (its units inactive, no runner process);
# fable: the subscription's other user here is not running (the "Did they improve?" Claude lane improve-subs-claude and
# its probe improve-claude-wait): it keeps priority.
# Once: v3.db backup (VACUUM INTO, one snapshot; zstd, verified), first match id, the late_entry_stage trigger, the
# league config. Then starts the league unit late-<ENTRANT>-league and guards it every 60 s; it stops the league unit
# (matches resume later from their last turn):
#   - when the entrant's route is at its limit (its latest aborted match ended on a 429 / usage or rate limit /
#     RESOURCE_EXHAUSTED naming its model): logged, exit 3, no retry loop; start again once the limit has reset;
#   - fable: when the Claude lane above starts (it has priority): exit 3, start again after it;
#   - carbon: when its own list-price cost from the first match reaches $OWN_CAP (default $250: 1.3 x the $193
#     estimate for 19 opponents; stage 1 alone is about $100);
#   - when OpenRouter's balance (shared with other lanes; paid opponents bill there) is under $FLOOR ($40), or cannot
#     be read 3 times in a row (fail closed);
#   - when the paid opponents' cost from the first match reaches $CAP ($5);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 48 h.
# One match at a time from the first match on: player-<ENTRANT>.json has max_matches 1.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
ENTRANT=${1:-}
T=$(dirname "$(readlink -f "$0")")
case $ENTRANT in
  carbon) NAME="Gemini 4 Carbon (high)"; CFG=gemini-4-carbon-high; LANES=(); OWN_CAP=${OWN_CAP:-250} ;;
  fable) NAME="Claude Fable 5.2 (max)"; CFG=claude-fable-5\.2-max; LANES=(improve-subs-claude improve-claude-wait)
         OWN_CAP= ;;
  *) echo "usage: start.sh carbon|fable" >&2; exit 2 ;;
esac
W=workspace/late-carbon-fable/$ENTRANT
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/carbon-fable/release/jevgammon
STATUS="mailbox/Late entries $NAME - status.md"
FLOOR=40
CAP=5
UNIT=late-$ENTRANT-league
L() { python3 "$T/late.py" "$ENTRANT" "$@"; }
export PATH=$HOME/.local/bin:$PATH
mkdir -p "$ST"
[[ -e $W/../METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id) and league configs of the Gemini 4 Carbon (high) and Claude Fable 5.2 (max) late entries (carbon/, fable/), and the route smoke answers (smoke.db)" \
  "reason: Ümit via Zeki #4676; scripts in ~/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable (branch late-carbon-fable)" \
  "delete when: after both entries are complete and reported (the matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ) (Can #3774)" > "$W/../METADATA"
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$ST/guard.log"; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { L billed "$(cat "$ST/first")"; }
lane_up() { local u; for u in "${LANES[@]}"; do systemctl --user is-active -q "$u" && { echo "$u"; return 0; }; done; return 1; }
# Nothing plays this entrant's league: its units inactive (or not loaded), no runner process for it.
idle() {
  local u s id
  for u in "$UNIT" "late-$ENTRANT-locals"; do
    s=$(systemctl --user is-active "$u" 2>/dev/null)
    [[ $s == inactive || $s == failed || $s == unknown || -z $s ]] || { echo "$u is $s"; return 1; }
  done
  id=$(L league-id)
  pgrep -f -- "late-carbon-fable/run_league\.sh $ENTRANT|league --config [^ ]*$CFG\.json${id:+|league --resume $id --db}" \
    >/dev/null 2>&1
  case $? in 1) return 0 ;; 0) echo "a runner for $NAME's league is running"; return 1 ;;
    *) echo "pgrep failed"; return 1 ;; esac
}
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
why=$(idle) || { echo "not idle: $why" >&2; exit 1; }
lane=$(lane_up) && { echo "$lane is running: it keeps the subscription; start $NAME after it" >&2; exit 3; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (/tmp is a smaller tmpfs) and the .zst is verified with
# zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-$ENTRANT.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-$ENTRANT.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  # VACUUM INTO: one read snapshot, not restarted by other runs' writes (sqlite3 .backup restarted endlessly under the
  # live lanes' writes on 11 Nov and never finished).
  sqlite3 v3.db "VACUUM INTO '$raw'" || fail "v3.db backup (VACUUM INTO) to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  L trigger >> "$ST/guard.log" 2>&1 || fail "trigger failed"
  L configs >> "$ST/guard.log" 2>&1 || fail "configs failed"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat "$ST/first")" >> "$ST/guard.log"
fi
[[ -e $STATUS ]] || printf '# Late entries %s - status\n\nGo: Ümit via Zeki #4676. First match id: #%s.\n\n## Log\n' \
  "$NAME" "$(cat "$ST/first")" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME; OpenRouter \$$bal; floor \$$FLOOR; paid-opponent cap \$$CAP from #$(cat "$ST/first"); 10 opponents, one match at a time (GPT-6 Luna deferred: no OpenAI credit; 8 local setups by locals.sh)"

stop_league() { systemctl --user stop "$UNIT" 2>/dev/null; }
restarts=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(L pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 10 pairs played; paid opponents \$$(spent); $NAME: $(L own "$(cat "$ST/first")"); OpenRouter \$$(balance)"; exit 0
  fi
  if lane=$(lane_up); then
    stop_league; log "PAUSED: $lane started (it keeps the subscription); start $NAME again after it; paid opponents \$$(spent)"; exit 3
  fi
  if hit=$(L limited "$(cat "$ST/first")") && [[ -n $hit ]]; then
    stop_league; log "PAUSED: $NAME's route at its limit ($hit); start again once it has reset; paid opponents \$$(spent)"; exit 3
  fi
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then
      stop_league; log "STOPPED: OpenRouter balance \$$bal under \$$FLOOR; paid opponents \$$(spent)"; exit 1
    fi
  else
    unread=$((unread + 1))
    if (( unread >= 3 )); then
      stop_league; log "STOPPED: OpenRouter balance unreadable 3 times in a row; paid opponents \$$(spent)"; exit 1
    fi
  fi
  s=$(spent)
  if ! lt "$s" "$CAP"; then
    stop_league; log "STOPPED: paid opponents \$$s reached the \$$CAP cap"; exit 1
  fi
  if [[ -n $OWN_CAP ]] && ! lt "$(L owncost "$(cat "$ST/first")")" "$OWN_CAP"; then
    stop_league; log "STOPPED: $NAME's own cost reached the \$$OWN_CAP cap: $(L own "$(cat "$ST/first")")"; exit 1
  fi
  if ! systemctl --user is-active -q "$UNIT"; then
    read -r opened blocked < <(L scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(L scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed "$UNIT" >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit="$UNIT" --working-directory="$PWD" "$T/run_league.sh" "$ENTRANT" "$BIN"
  fi
  (( SECONDS - t0 > 172800 )) && { stop_league; log "STOPPED: pairs still open after 48 h"; exit 1; }
  sleep 60
done
