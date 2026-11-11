#!/usr/bin/env bash
# Late entry of Google's Gemini Decision 1 (player.json: OpenRouter's System One route, model google/gemini-decision-1,
# provider pinned to Google AI Studio, fallbacks off) v the original League 1 table (Main, 11 Nov; Ümit, Can #4966),
# stage 1: the 3 programs and the paid API setups (GPT-6 Luna deferred while OpenAI is out of credit), as
# tools/v3/late-tiny8. The 8 local setups follow later with locals.sh (bariton GPU 2, reservation r_82bfcd93782c).
# Status: mailbox/Late entry Gemini Decision 1 - status.md (main checkout); state workspace/late-gemini-decision/state.
#   systemd-run --user --unit=late-gemini-decision --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
#     /home/cbasaran/code/jevgammon-gemini-decision/tools/v3/late-gemini-decision/start.sh
# Before anything: OpenRouter lists google/gemini-decision-1 as pinned (listed(): its one endpoint is Google AI Studio,
# up, at $0.10 per million input tokens and $0 output). Once: v3.db backup (VACUUM INTO, zstd -t), first match id, the
# late_entry_stage trigger, the league config. Then starts the league unit late-gemini-decision-league and guards it
# every 60 s; it stops the league unit (matches resume later from their last turn):
#   - when OpenRouter's balance (shared with other lanes; the entrant and Mercury Decide bill there) is under $FLOOR
#     ($40), or cannot be read 3 times in a row (fail closed: the floor is never left unchecked);
#   - when the entry's cost from the first match (the entrant plus the paid opponents) reaches $CAP ($5);
#   - when the listing check fails 3 times in a row (fail closed);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 12 h.
# One match at a time from the first match on: player.json has max_matches 1 and parallel 1. After the first 20
# decisions, their measured in-flight peak is logged once.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-gemini-decision
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/gemini-decision/release/jevgammon
STATUS="mailbox/Late entry Gemini Decision 1 - status.md"
FLOOR=40
CAP=5
UNIT=late-gemini-decision-league
MODEL=google/gemini-decision-1
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/player.json")
export PATH=$HOME/.local/bin:$PATH
gem() { python3 "$T/gemini.py" "$@"; }
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id), league config and smoke receipts of the $NAME late entry" \
  "reason: Ümit wants it asap (Can #4966); scripts in ~/code/jevgammon-gemini-decision/tools/v3/late-gemini-decision (branch late-gemini-decision)" \
  "delete when: after the entry is complete and reported (the matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ) (Can #4966)" > $W/METADATA
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/guard.log; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
# OpenRouter still serves the model as pinned: exactly one endpoint, Google AI Studio, up (status 0), at the list price.
listed() {
  curl -fsS -m 20 "https://openrouter.ai/api/v1/models/$MODEL/endpoints" | python3 -c 'import json,sys
e=json.load(sys.stdin)["data"]["endpoints"]
sys.exit(not (len(e) == 1 and e[0]["tag"] == "google-ai-studio" and e[0]["status"] == 0
              and float(e[0]["pricing"]["prompt"]) == 1e-7 and float(e[0]["pricing"]["completion"]) == 0))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { gem billed "$(cat $ST/first)"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
listed || { echo "OpenRouter: $MODEL not listed as pinned (one Google AI Studio endpoint, up, \$0.10/\$0)" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (/tmp is a smaller tmpfs) and the .zst is verified with
# zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-gemini-decision.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-gemini-decision.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  # VACUUM INTO: one read snapshot, not restarted by other runs' writes (sqlite3 .backup restarted endlessly
  # under the live lanes' writes on 11 Nov and never finished).
  sqlite3 v3.db "VACUUM INTO '$raw'" || fail "v3.db backup (VACUUM INTO) to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  gem trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  gem configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entry Gemini Decision 1 - status\n\nGo: Main (11 Nov; Can #4966). First match id: #%s.\n\n## Log\n' \
  "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME via OpenRouter ($MODEL, Google AI Studio only, fallbacks off) listed as pinned; OpenRouter \$$bal; floor \$$FLOOR; entry cap \$$CAP (entrant + paid opponents) from #$(cat $ST/first); 10 opponents, one match at a time (GPT-6 Luna deferred: no OpenAI credit; 8 local setups later on bariton GPU 2)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
down=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(gem pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 10 pairs played; entry \$$(spent); OpenRouter \$$(balance)"; exit 0
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
  if listed; then down=0; else down=$((down + 1)); fi
  if (( down >= 3 )); then
    stop_league; log "STOPPED: OpenRouter did not list $MODEL as pinned 3 checks in a row; entry \$$s"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(gem inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      log "in flight, first decisions: $first20"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(gem scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(gem scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
  fi
  (( SECONDS - t0 > 43200 )) && { stop_league; log "STOPPED: pairs still open after 12 h"; exit 1; }
  sleep 60
done
