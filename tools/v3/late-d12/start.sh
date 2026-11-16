#!/usr/bin/env bash
# Late entry of Liquid AI's d1.2 or d1.2-ultra (KEY d12 | d12-ultra; player-KEY.json: provider liquid, the runner's
# Liquid decisions client) v the original League 1 table (Ümit via Zeki #10928/#10931, 16 Nov 2026), stage 1: the 3
# programs and the paid API setups less GPT-6 Luna and Mercury Decide (not required): 9 pairs. The 8 local setups
# follow later with locals.sh on a bariton GPU booked by Main. As tools/v3/late-gemini-decision/start.sh.
# Status: mailbox/Late entry <name> - status.md (main checkout); state workspace/late-KEY/state.
#   systemd-run --user --unit=late-KEY --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
#     /home/cbasaran/code/jevgammon-late-d12ultra/tools/v3/late-d12/start.sh KEY
# (waiter.sh KEY starts it once Liquid answers the model.)
# Before anything: one probe decision (liquid12.py probe: raw reply, usage and served model kept in state/probes)
# must be answered. Once: v3.db backup (VACUUM INTO and zstd, both on ~/T9/jevgammon-league-backups, not /; zstd -t),
# first match id, the late_entry_stage trigger, the league config. Then starts the league unit late-KEY-league and
# guards it every 60 s; it stops the league unit (matches resume later from their last turn):
#   - when OpenRouter's balance (paid opponents bill there) is under $FLOOR ($40), or cannot be read 3 times in a row;
#   - when the entry's cost from the first match (the entrant plus the paid opponents) reaches $CAP ($5);
#   - when the 9 pairs are played (done), every open pair is blocked (e.g. Liquid 404s the model), or after 12 h.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
KEY=${1:?KEY: d12 or d12-ultra}
[[ $KEY == d12 || $KEY == d12-ultra ]] || { echo "KEY must be d12 or d12-ultra" >&2; exit 1; }
export LATE_KEY=$KEY
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-$KEY
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/gemini-decision/release/jevgammon
BACKUPS=/home/cbasaran/T9/jevgammon-league-backups
FLOOR=40
CAP=5
UNIT=late-$KEY-league
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/player-$KEY.json")
STATUS="mailbox/Late entry $NAME - status.md"
export PATH=$HOME/.local/bin:$PATH
liq() { python3 "$T/liquid12.py" "$@"; }
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard, waiter and locals logs, probes, first match id) and league config of the $NAME late entry" \
  "reason: Ümit via Zeki #10928/#10931; scripts in ~/code/jevgammon-late-d12ultra/tools/v3/late-d12 (branch late-d12ultra)" \
  "delete when: after the entry is complete and published (the matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ)" > $W/METADATA
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/guard.log; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { liq billed "$(cat $ST/first)"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }
if [[ ! -e $ST/qualified ]]; then
  p=$(liq probe) || { echo "Liquid probe: $p" >&2; exit 1; }
  echo "$(date -u +%FT%TZ) $p" > $ST/qualified
fi

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written.
if [[ ! -e $ST/first ]]; then
  raw=$BACKUPS/v3-before-$KEY.db
  bak=$BACKUPS/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-$KEY.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  sqlite3 v3.db "VACUUM INTO '$raw'" || fail "v3.db backup (VACUUM INTO) to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  liq trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  liq configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entry %s - status\n\nGo: Ümit via Zeki #10928/#10931 (16 Nov). First match id: #%s.\n\n## Log\n' \
  "$NAME" "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME (liquid, $(cat $ST/qualified)); OpenRouter \$$bal; floor \$$FLOOR; entry cap \$$CAP (entrant + paid opponents) from #$(cat $ST/first); 9 opponents, one match at a time (GPT-6 Luna, Mercury Decide not required; 8 local setups later)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(liq pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 9 first-stage pairs played; entry \$$(spent); OpenRouter \$$(balance); locals next (Main books a GPU)"; exit 0
  fi
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then
      stop_league; log "STOPPED: OpenRouter balance \$$bal under \$$FLOOR; entry \$$(spent)"; exit 1
    fi
  else
    unread=$((unread + 1))
    if (( unread >= 3 )); then
      stop_league; log "STOPPED: OpenRouter balance unreadable 3 times in a row; entry \$$(spent)"; exit 1
    fi
  fi
  s=$(spent)
  if ! lt "$s" "$CAP"; then
    stop_league; log "STOPPED: entry \$$s (entrant + paid opponents) reached the \$$CAP cap"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(liq inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      log "in flight, first decisions: $first20"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(liq scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(liq scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$KEY" "$BIN"
  fi
  (( SECONDS - t0 > 43200 )) && { stop_league; log "STOPPED: pairs still open after 12 h"; exit 1; }
  sleep 60
done
