#!/usr/bin/env bash
# StartLux-Decision v1.1 2B (StartLux-Decision-v1.1-2B-Instant) late entry v the original League 1 table (Main, 11 Nov),
# stage 1: the 3 programs and the paid API setups (GPT-6 Luna deferred while OpenAI is out of credit), as
# tools/v3/late-knowline4b (KnowLine 4B Gen5.5). The model runs on its own server, its package's `startlux-decide serve
# --launch-vllm` on spark2 (player.json base_url), never started from here.
# Status: mailbox/Late entries StartLux 2B - status.md (main checkout); state workspace/late-startlux2b/state.
#   systemd-run --user --unit=late-startlux2b --working-directory=/home/cbasaran/code/jevgammon \
#     /home/cbasaran/code/jevgammon-startlux2b/tools/v3/late-startlux2b/start.sh
# Before anything: the server answers /health as the pinned snapshot's Instant server (vLLM 0.31.0, bidirectional
# prompt attention, context 131,072, no thinking) and, read over ssh ($STARTLUX_SSH, default spark2), runs the pinned
# package (StartLux-Decision @ a99977d, clean, its vLLM plugin by sha256) as `startlux-decide serve --model <snapshot>
# --launch-vllm` on PORT with serve's defaults (none_check on, allow_none off), and a vLLM on the snapshot in BF16 (no
# --quantization) with --max-model-len 131072. Once: v3.db backup, first match id, the late_entry_stage trigger, the
# league config. Then starts the league unit late-startlux2b-league and guards it
# every 60 s; it stops the league unit (matches resume later from their last turn):
#   - when OpenRouter's balance (shared with other lanes; Mercury Decide bills there) is under $FLOOR ($40), or cannot
#     be read 3 times in a row (fail closed: the floor is never left unchecked);
#   - when the paid opponents' cost from the first match reaches $CAP ($5; StartLux itself costs nothing);
#   - when the StartLux server fails 3 health checks in a row (fail closed: no match runs against a missing server);
#   - when the 10 pairs are played (done), every open pair is blocked, or after 12 h.
# One match at a time from the first match on (Zeki #4561): player.json has max_matches 1 and parallel 1, so the
# server gets one request at a time. After the first 20 StartLux decisions, their measured in-flight peak (turn
# intervals) and vLLM's own stats log for that window are logged once.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-startlux2b
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/startlux2b/release/jevgammon
STATUS="mailbox/Late entries StartLux 2B - status.md"
FLOOR=40
CAP=5
UNIT=late-startlux2b-league
SNAPSHOT=/home/cbasaran/decision-models/StartLux-Decision-v1.1-2B-Instant@f1e6cd147dda82c9ffa3e8e725d5c1f175566fb1
REPO=/home/cbasaran/decision-src/StartLux-Decision
REPO_COMMIT=a99977d9332decc9fb27a2488b4a83b533b6cd5f
PLUGIN_SHA=d80d120266b915f0d7ef1de09483b09eaf4ef79641f8847f6c696f9d8ac20a66
SSH_HOST=${STARTLUX_SSH:-spark2}
URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$T/player.json")
PORT=${URL##*:}
export PATH=$HOME/.local/bin:$PATH
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id, server log) and league config of the StartLux-Decision v1.1 2B late entry" \
  "reason: Main's brief (11 Nov); scripts in ~/code/jevgammon-startlux2b/tools/v3/late-startlux2b (branch late-startlux2b)" \
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
spent() { python3 $T/startlux.py billed "$(cat $ST/first)"; }
# The pinned snapshot's Instant server, as /health reports it.
healthy() {
  curl -fsS -m 10 "$URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); e=d["engine"]
sys.exit(not (d["status"] == "ok" and d["model"] == "StartLux-Decision-v1.1-2B-Instant@f1e6cd147dda82c9ffa3e8e725d5c1f175566fb1"
              and d["kind"] == "instant" and d["prompt_attention"] == "bidirectional" and e["name"] == "vllm"
              and e["vllm_versions"] == ["0.31.0"] and d["context_length"] == 131072
              and d["defaults"]["think_mode"] == "never"))'
}
# The pinned package (commit, clean tree, installed editable from it, plugin by sha256) serving the snapshot on PORT
# with serve's defaults (no --allow-none, no --no-none-check), and its vLLM on the snapshot in BF16 (no --quantization)
# at the 131,072-token context (read-only ssh).
pinned() {
  local procs
  procs=$(timeout 30 ssh -o BatchMode=yes "$SSH_HOST" "ps -eo args; echo @@; git -C $REPO rev-parse HEAD;
    git -C $REPO status --porcelain --untracked-files=no | wc -l; sha256sum $REPO/startlux_decide/vllm_plugin.py;
    cat ~/envs/startlux/lib/python3.12/site-packages/startlux_decide-1.1.0.dist-info/direct_url.json" 2>/dev/null) ||
    return 1
  grep -qxF "$REPO_COMMIT" <<<"$procs" && grep -qxF 0 <<<"$procs" &&
  grep -qF "$PLUGIN_SHA  $REPO/startlux_decide/vllm_plugin.py" <<<"$procs" &&
  grep -qF "\"url\": \"file://$REPO\"" <<<"$procs" &&
  grep -F "startlux-decide serve --model $SNAPSHOT --launch-vllm " <<<"$procs" | grep -F -- "--port $PORT" |
    grep -vF -- "--allow-none" | grep -qvF -- "--no-none-check" &&
  grep -F "vllm.entrypoints.openai.api_server --model $SNAPSHOT " <<<"$procs" | grep -F -- "--max-model-len 131072" |
    grep -vqF -- "--quantization"
}
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "Mercury Decide" "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
healthy || { echo "StartLux server $URL: no /health of the pinned Instant snapshot" >&2; exit 1; }
pinned || { echo "StartLux server on $SSH_HOST: not the pinned package's serve of the snapshot on port $PORT" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written (so the block
# runs again next time). The backup goes to v3.db's own disk (/tmp is a smaller tmpfs) and the .zst is verified with
# zstd -t before anything writes v3.db.
if [[ ! -e $ST/first ]]; then
  raw=$PWD/v3-before-startlux2b.db
  bak=$PWD/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-startlux2b.zst
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
  python3 $T/startlux.py trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  python3 $T/startlux.py configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entries StartLux 2B - status\n\nGo: Main (11 Nov). First match id: #%s.\n\n## Log\n' "$(cat $ST/first)" > "$STATUS"
log "guard up: runner $(git -C "$T" rev-parse --short HEAD) clean; StartLux $URL pinned ($SSH_HOST); OpenRouter \$$bal; floor \$$FLOOR; paid-opponent cap \$$CAP from #$(cat $ST/first); 10 opponents, one match at a time (GPT-6 Luna deferred: no OpenAI credit; 8 local setups queued for a GPU)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
down=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(python3 $T/startlux.py pending "${OPPS[@]}") == 0 ]]; then
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
    stop_league; log "STOPPED: StartLux server $URL failed 3 health checks in a row; paid opponents \$$s"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(python3 $T/startlux.py inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      until_utc=$(sqlite3 -readonly v3.db "SELECT strftime('%Y-%m-%d %H:%M:%S', MAX(created_at), '+1 second') FROM turns")
      server=$(python3 $T/startlux.py server-inflight "$(cat $ST/since)" "$until_utc" 2>&1)
      log "in flight, first decisions: $first20; server: $server"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(python3 $T/startlux.py scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(python3 $T/startlux.py scope | tail -n +2 | tr '\n' ' ')"; exit 1
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
