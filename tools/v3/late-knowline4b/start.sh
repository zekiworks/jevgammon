#!/usr/bin/env bash
# KnowLine 4B Gen5.5 late entry v the original League 1 table (Ümit #4325), stage 1: the 3 programs and the paid API
# setups (GPT-6 Luna deferred while OpenAI is out of credit), as tools/v3/late-knowline (KnowLine 31B Gen1.5). The
# model runs on its own server, PelaAI's serve_knowline.sh on spark2 (player.json base_url), never started from here.
# Status: mailbox/Late entries KnowLine 4B - status.md (main checkout); state workspace/late-knowline4b/state.
#   systemd-run --user --unit=late-knowline4b --working-directory=/home/cbasaran/code/jevgammon \
#     /home/cbasaran/code/jevgammon-knowline4b/tools/v3/late-knowline4b/start.sh
# Before anything: the server answers /health with the card's layout (read twice up to 3,000 tokens, no header) and,
# read over ssh ($KNOWLINE_SSH, default spark2), runs the pinned snapshot's knowline_server.py and an SGLang with FP8 at
# load and without --allow-auto-truncate (serve_knowline.sh's own command lines). Once: v3.db backup, first match id,
# the late_entry_stage trigger, the league config. Then starts the league unit late-knowline4b-league and guards it
# every 60 s; it stops the league unit (matches resume later from their last turn):
#   - when OpenRouter's balance (shared with other lanes; Mercury Decide bills there) is under $FLOOR ($40), or cannot
#     be read 3 times in a row (fail closed: the floor is never left unchecked);
#   - when the paid opponents' cost from the first match reaches $CAP ($5; KnowLine itself costs nothing);
#   - when the KnowLine server fails 3 health checks in a row (fail closed: no match runs against a missing server);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 12 h.
# One match at a time from the first match on (Zeki #4561): player.json has max_matches 1 and parallel 1, so the
# server gets one request at a time. After the first 20 KnowLine decisions, their measured in-flight peak (turn
# intervals) and SGLang's own batch log for that window are logged once.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-knowline4b
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/knowline/release/jevgammon
STATUS="mailbox/Late entries KnowLine 4B - status.md"
FLOOR=40
CAP=5
UNIT=late-knowline4b-league
SNAPSHOT=/home/cbasaran/decision-models/KnowLine-4B-Gen5.5@779944d2cc8ffa19cef386aee83c83bcb967ade2
SSH_HOST=${KNOWLINE_SSH:-spark2}
URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$T/player.json")
PORT=${URL##*:}
export PATH=$HOME/.local/bin:$PATH
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id, server log) and league config of the KnowLine 4B Gen5.5 late entry" \
  "reason: Ümit #4325; scripts in ~/code/jevgammon-knowline4b/tools/v3/late-knowline4b (branch late-knowline4b)" \
  "delete when: after the entry is complete and reported (the matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ) (Can #3774)" > $W/METADATA
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/guard.log; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { python3 $T/knowline.py billed "$(cat $ST/first)"; }
# The card's serving, as /health reports it (serve_knowline.sh: read twice up to 3,000 tokens, no header).
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); l=d["layout"]
sys.exit(not (d["status"] == "ok" and d["model"] == "m" and d["temperature"] == 1.0 and l["read_twice"]
              and l["twice_max_tokens"] == 3000 and not l["header"]))'
}
# The pinned snapshot's front end on PORT (serve_knowline.sh's arguments, no temperatures file), behind an SGLang with
# FP8 at load that never truncates (read-only ssh).
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" 'ps -eo args' 2>/dev/null) || return 1
  grep -F "$SNAPSHOT/knowline_server.py --model $SNAPSHOT --backend sglang" <<<"$procs" |
    grep -F -- "--temperature 1 --workers 16 " | grep -F -- "--port $PORT" | grep -vF -- "--temperatures" |
    grep -vF -- "--no-read-twice" | grep -qvF -- "--header" &&
  grep -F "sglang.launch_server --model-path $SNAPSHOT " <<<"$procs" | grep -F -- "--quantization fp8" |
    grep -F -- "--enable-fp32-lm-head" | grep -vqF -- "--allow-auto-truncate"
}
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
healthy || { echo "KnowLine server $URL: no /health with the card's layout" >&2; exit 1; }
pinned || { echo "KnowLine server on $SSH_HOST: not the pinned snapshot's serve_knowline.sh on port $PORT" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (/tmp is a smaller tmpfs) and the .zst is verified with
# zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-knowline4b.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-knowline4b.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  sqlite3 v3.db ".backup '$raw'" || fail "v3.db backup to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  python3 $T/knowline.py trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  python3 $T/knowline.py configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entries KnowLine 4B - status\n\nGo: Ümit #4325. First match id: #%s.\n\n## Log\n' "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; KnowLine $URL pinned ($SSH_HOST); OpenRouter \$$bal; floor \$$FLOOR; paid-opponent cap \$$CAP from #$(cat $ST/first); 10 opponents, one match at a time (GPT-6 Luna deferred: no OpenAI credit; 8 local setups queued for a GPU)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
down=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(python3 $T/knowline.py pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 10 pairs played; paid opponents \$$(spent); OpenRouter \$$(balance)"; exit 0
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
  if healthy; then down=0; else down=$((down + 1)); fi
  if (( down >= 3 )); then
    stop_league; log "STOPPED: KnowLine server $URL failed 3 health checks in a row; paid opponents \$$s"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(python3 $T/knowline.py inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      until_utc=$(sqlite3 -readonly v3.db "SELECT strftime('%Y-%m-%d %H:%M:%S', MAX(created_at), '+1 second') FROM turns")
      server=$(python3 $T/knowline.py server-inflight "$(cat $ST/since)" "$until_utc" 2>&1)
      log "in flight, first decisions: $first20; server: $server"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(python3 $T/knowline.py scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(python3 $T/knowline.py scope | tail -n +2 | tr '\n' ' ')"; exit 1
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
