#!/usr/bin/env bash
# Late entry of Gemini 4 Carbon (high) (player.json: openai-compatible/gemini-4-carbon on Can's Antigravity subscription
# bridge, agbench, http://192.168.1.129:8899/v1; thinking level high, choice only, as Gemini 4 Argon (on) in League 1)
# v the original League 1 table, stage 1: the 3 programs and the paid API setups less GPT-6 Luna and Mercury Decide
# (not required, as the Liquid d1.2 entries): 9 pairs. The 8 local setups follow later with locals.sh on a bariton GPU
# booked by Main. As tools/v3/late-d12/start.sh, without a waiter. The paid opponents (~$0.10) need Ümit's OK (#9719):
# APPROVAL is that message's id, logged; nothing starts without it.
# Status: mailbox/Late entry Gemini 4 Carbon (high) - status.md (main checkout); state workspace/late-carbon/state.
# Not before the bridge's weekly reset (carbon.py quota-reset; 2026-11-20T22:51:48Z as read 17 Nov): the quota left
# before 80% this week is Answer Check's Carbon pass (compactor #11583).
#   systemd-run --user --unit=late-carbon --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E FLOOR_USD=0 [-E QUOTA_STOP=80] \
#     /home/cbasaran/code/jevgammon-late-carbon/tools/v3/late-carbon/start.sh '#NNNN'
# Before anything: the bridge's /health answers status ok, Antigravity connected, circuit breaker off, and its weekly
# quota use is under $QUOTA_STOP. Once: v3.db backup (VACUUM INTO and zstd, both on
# ~/T9/jevgammon-league-backups, not /; zstd -t), first match id, the late_entry_stage trigger, the league config. Then
# starts the league unit late-carbon-league and guards it every 60 s; it stops the league unit (matches resume later
# from their last turn):
#   - when the bridge's weekly quota use reaches $QUOTA_STOP (QUOTA_STOP, default 80%, under the bridge's own 85%
#     reserve, past which it answers 429), or cannot be read 3 times in a row (fail closed). The gauge is the one
#     compactor's grading_bench.py stops on: GET /quota, parsed.weekly_used_percent (carbon.py quota);
#   - when OpenRouter's balance is under $FLOOR ($40; FLOOR_USD overrides it), or cannot be read 3 times in a row.
#     None of this entry's 9 opponents bills through OpenRouter (Celeris, Fastino, Jev, Liquid and SubQ use their own
#     keys; Mercury Decide is skipped) and the entrant bills nothing, so the floor only guards the shared balance for
#     others: run with FLOOR_USD=0, as late-d12;
#   - when the paid opponents' cost from the first match reaches $CAP ($5; the entrant's cost_usd is a list-price
#     equivalent, $0 billed, and does not count);
#   - when the 9 pairs are played (done), every open pair is blocked, or after 24 h.
# Up to 2 matches at once (player.json max_matches 2, mirror_concurrent: 2 games each), at most 4 requests in flight
# (parallel 4, the bridge's 4 lanes). After the first 20 decisions, their measured in-flight peak is logged once.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
APPROVAL=${1:-}
[[ $APPROVAL =~ ^#[0-9]+$ ]] || { echo "usage: start.sh '#NNNN' (Ümit's go for the paid opponents, rule #9719)" >&2; exit 1; }
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-carbon
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/gemini-decision/release/jevgammon
BACKUPS=/home/cbasaran/T9/jevgammon-league-backups
FLOOR=${FLOOR_USD:-40}
CAP=5
QUOTA_STOP=${QUOTA_STOP:-80}
[[ $QUOTA_STOP =~ ^[0-9]+(\.[0-9]+)?$ ]] && python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < 85)' "$QUOTA_STOP" ||
  { echo "QUOTA_STOP must be a percent under the bridge's 85% reserve, not '$QUOTA_STOP'" >&2; exit 1; }
UNIT=late-carbon-league
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/player.json")
STATUS="mailbox/Late entry $NAME - status.md"
export PATH=$HOME/.local/bin:$PATH
car() { python3 "$T/carbon.py" "$@"; }
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id) and league config of the $NAME late entry (Antigravity bridge)" \
  "reason: offered #11570, go $APPROVAL; scripts in ~/code/jevgammon-late-carbon/tools/v3/late-carbon (branch late-carbon)" \
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
spent() { car billed "$(cat $ST/first)"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
h=$(car health) || { echo "bridge not ready: $h" >&2; exit 1; }
q=$(car quota) || { echo "bridge quota unreadable" >&2; exit 1; }
lt "$q" "$QUOTA_STOP" || { echo "bridge weekly quota $q% used: not under $QUOTA_STOP%" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written.
if [[ ! -e $ST/first ]]; then
  raw=$BACKUPS/v3-before-carbon.db
  bak=$BACKUPS/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-carbon.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  sqlite3 v3.db "VACUUM INTO '$raw'" || fail "v3.db backup (VACUUM INTO) to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  car trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  car configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entry %s - status\n\nGo: %s (offered #11570; bridge #11571). First match id: #%s.\n\n## Log\n' \
  "$NAME" "$APPROVAL" "$(cat $ST/first)" > "$STATUS"
log "guard up (go $APPROVAL): runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME via the Antigravity bridge ($h); weekly quota $q% used, stop at $QUOTA_STOP%; OpenRouter \$$bal; floor \$$FLOOR; paid-opponent cap \$$CAP from #$(cat $ST/first); 9 opponents, up to 2 matches at once (GPT-6 Luna, Mercury Decide not required; 8 local setups later)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
unread=0
qunread=0
t0=$SECONDS
while true; do
  if [[ $(car pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 9 first-stage pairs played; paid opponents \$$(spent); weekly quota $(car quota)% used; locals next (Main books a GPU)"; exit 0
  fi
  if q=$(car quota); then
    qunread=0
    if ! lt "$q" "$QUOTA_STOP"; then
      stop_league; log "STOPPED: bridge weekly quota $q% used, reached $QUOTA_STOP%; paid opponents \$$(spent)"; exit 1
    fi
  else
    qunread=$((qunread + 1))
    if (( qunread >= 3 )); then
      stop_league; log "STOPPED: bridge weekly quota unreadable 3 times in a row; paid opponents \$$(spent)"; exit 1
    fi
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
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(car inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      log "in flight, first decisions: $first20; weekly quota $q% used"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(car scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(car scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN"
  fi
  (( SECONDS - t0 > 86400 )) && { stop_league; log "STOPPED: pairs still open after 24 h"; exit 1; }
  sleep 60
done
