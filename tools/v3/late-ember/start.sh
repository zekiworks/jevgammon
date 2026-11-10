#!/usr/bin/env bash
# Muse Ember (max) late entry v the original League 1 table: the stage without GPUs (the 3 programs and the 7 paid API
# setups; GPT-6 Luna deferred, OpenAI out of credit), as the REAX/Drex late entries. Go: Can, bus #4144.
# Status: mailbox/Late entries Muse Ember - status 2026-11-10.md (main checkout); state workspace/late-ember/state.
#   systemd-run --user --unit=late-ember --working-directory=/home/cbasaran/code/jevgammon \
#     /home/cbasaran/code/jevgammon-ember/tools/v3/late-ember/start.sh
# Once: v3.db backup, first match id, the late_entry_stage trigger, the league config. Then starts the league unit
# late-ember-league and guards it every 60 s; it stops the league unit (matches resume later from their last turn):
#   - when OpenRouter's balance (shared with other lanes) is under $FLOOR ($40 kept, $1 margin for requests in flight
#     and the credits endpoint's lag);
#   - when Ember's ledger (spent + open reservations; hard pre-send cap 19.5 in player.json) plus the paid opponents'
#     cost from the first match reaches $CAP (the run's $20 with margin: a reservation books 32,768 output tokens,
#     Meta's reasoning can pass that, smoke max 83,103);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 16 h.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-ember
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/ember/release/jevgammon
STATUS="mailbox/Late entries Muse Ember - status 2026-11-10.md"
FLOOR=41
CAP=19.75
UNIT=late-ember-league
mkdir -p $ST
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/guard.log; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { python3 -c 'import sys; print(f"{float(sys.argv[1]) + float(sys.argv[2]):.4f}")' \
  "$(python3 $T/ember.py ledger)" "$(python3 $T/ember.py billed "$(cat $ST/first)")"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$(python3 -c "print($FLOOR + $CAP)")" && { echo "OpenRouter balance \$$bal: under \$$FLOOR + the \$$CAP run" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (34 GB; /tmp is a smaller tmpfs) and the .zst is
# verified with zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-ember.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-ember.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  sqlite3 v3.db ".backup '$raw'" || fail "v3.db backup to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  python3 $T/ember.py trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  python3 $T/ember.py configs >> $ST/guard.log 2>&1 || fail "configs failed"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entries Muse Ember - status 2026-11-10\n\nGo: Can, bus #4144. First match id: #%s.\n\n## Log\n' "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; OpenRouter \$$bal; floor \$$FLOOR; run cap \$$CAP (Ember ledger + paid opponents from #$(cat $ST/first)); 10 opponents (GPT-6 Luna deferred: no OpenAI credit; 8 local setups queued for a GPU)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
t0=$SECONDS
while true; do
  if [[ $(python3 $T/ember.py pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 10 pairs played; run spent \$$(spent) (Ember ledger \$$(python3 $T/ember.py ledger)); OpenRouter \$$(balance)"; exit 0
  fi
  if bal=$(balance) && lt "$bal" "$FLOOR"; then
    stop_league; log "STOPPED: OpenRouter balance \$$bal under \$$FLOOR; run spent \$$(spent)"; exit 1
  fi
  s=$(spent)
  if ! lt "$s" "$CAP"; then
    stop_league; log "STOPPED: run spent \$$s reached the \$$CAP cap"; exit 1
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(python3 $T/ember.py scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(python3 $T/ember.py scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
  fi
  (( SECONDS - t0 > 57600 )) && { stop_league; log "STOPPED: pairs still open after 16 h"; exit 1; }
  sleep 60
done
