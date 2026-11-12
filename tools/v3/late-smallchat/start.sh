#!/usr/bin/env bash
# Late entry of one small chat setup (KEY: models/KEY/player.json, KEY = MODEL-on or MODEL-off) v the original League 1
# table (Zeki #5064/#5071/#5073; manifest small-chat-full-suite-1570238769422934048), stage 1: the 3 programs and the
# paid API setups (GPT-6 Luna deferred while OpenAI is out of credit), as tools/v3/late-tiny8. The model runs on a server
# on bariton started elsewhere, never from here: logic's server on its GPU 1 for an (off) entry's first stage, else
# (#5119: every (on) entry and every local-opponent stage) the same command on our card, under our reservation RES:
#   systemd-run --user --unit=smallchat-serve-MODEL -p RemainAfterExit=yes --working-directory=$HOME/code/benchmark/logic \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
#     agent-bus run RES -- python3 work/small_models.py serve LOGIC_KEY GPU_UUID
#   (stop: python3 ~/code/benchmark/logic/work/small_models.py stop LOGIC_KEY; systemctl --user stop smallchat-serve-MODEL)
# It uses models.json's logic key, port and served name (player.json's), so no SMALLCHAT_URL/SMALLCHAT_MODEL is needed;
# RemainAfterExit keeps a llama.cpp server (LFM3-1.7B, Spark-X2.6-4B: a child process, unlike vLLM's container) alive
# after the serve command returns. serve.sh MODEL GPU start is the fallback copy. One setup at a time: start.sh refuses
# while another smallchat unit runs.
# Status: mailbox/Late entries smallchat - KEY - status.md (main checkout); state workspace/late-smallchat/KEY/state.
#   systemd-run --user --unit=late-smallchat-KEY --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/games [-E SMALLCHAT_URL=... -E SMALLCHAT_MODEL=...] \
#     /home/cbasaran/code/jevgammon-smallchat/tools/v3/late-smallchat/start.sh KEY
# Before anything: the server answers /v1/models with the setup's served name (pins.sh healthy) and the process on its
# port runs the pinned repo@revision in BF16 with a context of at least 38,000 tokens (pins.sh pinned). Once: v3.db
# backup (VACUUM INTO, zstd -t), first match id, the late_entry_stage trigger, the league config. Then starts the league
# unit late-smallchat-KEY-league and guards it every 60 s; it stops the league unit (matches resume later from their
# last turn):
#   - when OpenRouter's balance (shared with other lanes; Mercury Decide bills there) is under $FLOOR ($40), or cannot
#     be read 3 times in a row (fail closed: the floor is never left unchecked);
#   - when the paid opponents' cost from the first match reaches $CAP ($5; the entrant itself costs nothing);
#   - when the entrant's server fails 3 health checks in a row (fail closed);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 36 h (Granite-4.2-30B (on): ~25 h).
# Up to 16 matches and 16 requests at once (player.json max_matches 16, parallel 16), League 1's rule for its local chat
# setups (Main, 12 Nov): the server is ours alone after turkce's 'done KEY'. Before the first start of a setup, test.sh
# KEY sends it one test decision through the real client; a setup whose test fails is reported, not started.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
KEY=${1:?usage: start.sh KEY}
T=$(dirname "$(readlink -f "$0")")
[[ -f $T/models/$KEY/player.json ]] || { echo "unknown setup $KEY" >&2; exit 1; }
W=workspace/late-smallchat/$KEY
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/smallchat/release/jevgammon
STATUS="mailbox/Late entries smallchat - $KEY - status.md"
FLOOR=40
CAP=5
UNIT=late-smallchat-$KEY-league
PLAYER=$(python3 "$T/smallchat.py" "$KEY" player) || { echo "settings of $KEY unreadable" >&2; exit 1; }
field() { python3 -c 'import json,sys; print(eval(sys.argv[2], {}, {"p": json.loads(sys.argv[1])}))' "$PLAYER" "$1"; }
URL=$(field 'p["base_url"]')
NAME=$(field 'p["name"]')
SERVED=$(field 'p["spec"].split("/", 1)[1]')
PORT=${URL%/v1}
PORT=${PORT##*:}
. "$T/pins.sh"
export PATH=$HOME/.local/bin:$PATH:/usr/games
tiny() { python3 "$T/smallchat.py" "$KEY" "$@"; }
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id) and league config of the $NAME late entry" \
  "reason: Zeki #5064/#5071/#5073 (small chat cohort); scripts in ~/code/jevgammon-smallchat/tools/v3/late-smallchat (branch late-smallchat), KEY $KEY" \
  "delete when: after the entry is complete and reported (the matches stay in v3.db)" \
  "written: $(date -u +%FT%TZ)" > $W/METADATA
set -a; . ~/.keys; set +a
[[ -n ${CELERIS_API_KEY:-} ]] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
log() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> $ST/guard.log; echo "- $line" >> "$STATUS"; }
balance() {
  curl -fsS -m 20 https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY" |
    python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(round(d["total_credits"]-d["total_usage"],4))'
}
lt() { python3 -c 'import sys; sys.exit(not float(sys.argv[1]) < float(sys.argv[2]))' "$1" "$2"; }
spent() { tiny billed "$(cat $ST/first)"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
others=$(systemctl --user list-units --state=active --plain --no-legend 'late-smallchat-*' 2>/dev/null |
  awk '{print $1}' | grep -vxF -e "late-smallchat-$KEY.service" -e "$UNIT.service")
# One setup at a time unless ALLOW_CONCURRENT=1. With it, another running entry's paid opponents also count in this
# entry's spent() (smallchat.py billed sums every late-entry match from $ST/first on, any entrant but this one), so
# concurrency only makes the $5 cap stop earlier, never later.
[[ -z $others || ${ALLOW_CONCURRENT:-0} == 1 ]] || { echo "another smallchat entry runs: $others (one setup at a time)" >&2; exit 1; }
[[ -z $others ]] || echo "concurrent with: $others (ALLOW_CONCURRENT=1)" >&2
healthy || { echo "$LABEL server $URL: does not serve $SERVED" >&2; exit 1; }
pinned || { echo "$LABEL: the process on port $PORT is not the pinned $PIN_REPO@$PIN_REV (BF16, context >= $MIN_CONTEXT)" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (/tmp is a smaller tmpfs) and the .zst is verified with
# zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-smallchat-$KEY.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-smallchat-$KEY.zst
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
  tiny trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  tiny configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entries smallchat - %s (%s) - status\n\nGo: Zeki #5064/#5071/#5073. First match id: #%s.\n\n## Log\n' \
  "$KEY" "$NAME" "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME at $URL ($SERVED) pinned $PIN_REPO@${PIN_REV:0:8}; OpenRouter \$$bal; floor \$$FLOOR; paid-opponent cap \$$CAP from #$(cat $ST/first); 10 opponents, up to 16 matches at once (GPT-6 Luna deferred: no OpenAI credit; 8 local setups queued for a GPU)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
down=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(tiny pending "${OPPS[@]}") == 0 ]]; then
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
    stop_league; log "STOPPED: $LABEL server $URL failed 3 health checks in a row; paid opponents \$$s"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(tiny inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      log "in flight, first decisions: $first20"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(tiny scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(tiny scope | tail -n +2 | tr '\n' ' ')"; exit 1
    fi
    (( restarts > 6 )) && { log "STOPPED: league unit ended 7 times with pairs open"; exit 1; }
    (( restarts > 0 )) && log "league unit not running with pairs open: restart $restarts"
    restarts=$((restarts + 1))
    systemctl --user reset-failed $UNIT >/dev/null 2>&1 || true
    systemd-run --user --quiet --unit=$UNIT --working-directory="$PWD" "$T/run_league.sh" "$BIN" "$KEY"
  fi
  (( SECONDS - t0 > 129600 )) && { stop_league; log "STOPPED: pairs still open after 36 h"; exit 1; }
  sleep 60
done
