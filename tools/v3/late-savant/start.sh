#!/usr/bin/env bash
# Late entry of SubQ Savant 1.4 (player.json: openai-compatible/subq-savant-1.4 on SubQ's Chat Completions API,
# https://api.subq.ai/v1, key SUBQ_API_KEY; always reasons, reasoning_effort high (SubQ's default), temperature 1, choice
# only: SubQ refuses logprobs for this model) v the original League 1 table, stage 1: the 3 programs and the paid API
# setups less GPT-6 Luna and Mercury Decide (not required, as the Liquid d1.2 entries): 9 pairs. The 8 local setups
# follow later with locals.sh on a bariton GPU booked by Main. As tools/v3/late-carbon/start.sh. Go: Can #11963
# (APPROVAL, logged; nothing starts without it).
# Status: mailbox/Late entry SubQ Savant 1.4 - status.md (main checkout); state workspace/late-savant/state.
#   systemd-run --user --unit=late-savant --working-directory=/home/cbasaran/code/jevgammon \
#     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/games -E FLOOR_USD=0 [-E ENTRY_CAP_USD=10] \
#     /home/cbasaran/code/jevgammon-late-savant/tools/v3/late-savant/start.sh '#11963'
# Before anything: SubQ's GET /v1/models lists subq-savant-1.4 for our key. Once: v3.db backup (VACUUM INTO and zstd,
# both on ~/T9/jevgammon-league-backups, not /; zstd -t), first match id, the late_entry_stage trigger, the league
# config. Then starts the league unit late-savant-league and guards it every 60 s; it stops the league unit (matches
# resume later from their last turn):
#   - when the entry's spend reaches $CAP (ENTRY_CAP_USD, default $10): the entrant's budget ledger (settled costs at
#     list price, open and lost reservations at their worst case; the runner itself refuses any request past the
#     ledger's cap_usd 9.75, player.json) plus the paid opponents' cost from the first match;
#   - when OpenRouter's balance is under $FLOOR ($40; FLOOR_USD overrides it), or cannot be read 3 times in a row.
#     None of this entry's 9 opponents bills through OpenRouter (Celeris, Fastino, Jev, Liquid and SubQ use their own
#     keys; Mercury Decide is skipped) and the entrant bills SubQ, so the floor only guards the shared balance for
#     others: run with FLOOR_USD=0, as late-d12 and late-carbon;
#   - when the 9 pairs are played (done), every open pair is blocked, or after 24 h.
# Up to 2 matches at once (player.json max_matches 2, mirror_concurrent: 2 games each), at most 4 requests in flight
# (parallel 4). After the first 20 decisions, their measured in-flight peak is logged once.
set -uo pipefail
cd /home/cbasaran/code/jevgammon
APPROVAL=${1:-}
[[ $APPROVAL =~ ^#[0-9]+$ ]] || { echo "usage: start.sh '#NNNN' (the go for this entry and its paid opponents)" >&2; exit 1; }
T=$(dirname "$(readlink -f "$0")")
W=workspace/late-savant
ST=$W/state
BIN=/home/cbasaran/code/jevgammon/target/gemini-decision/release/jevgammon
BACKUPS=/home/cbasaran/T9/jevgammon-league-backups
FLOOR=${FLOOR_USD:-40}
CAP=${ENTRY_CAP_USD:-10}
[[ $CAP =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "ENTRY_CAP_USD must be a number, not '$CAP'" >&2; exit 1; }
UNIT=late-savant-league
NAME=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/player.json")
MODEL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"].split("/", 1)[1])' "$T/player.json")
STATUS="mailbox/Late entry $NAME - status.md"
export PATH=$HOME/.local/bin:$PATH:/usr/games
sav() { python3 "$T/savant.py" "$@"; }
mkdir -p $ST
[[ -e $W/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" \
  "what: state (guard and locals logs, first match id, the entrant's budget ledger savant-budget.db) and league config of the $NAME late entry (SubQ Chat Completions API)" \
  "reason: Can $APPROVAL; scripts in ~/code/jevgammon-late-savant/tools/v3/late-savant (branch late-savant)" \
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
spent() { python3 -c 'import sys; print(f"{float(sys.argv[1]) + float(sys.argv[2]):.4f}")' \
  "$(sav ledger)" "$(sav billed "$(cat $ST/first)")"; }
OPPS=("GNUbg weak" "Random" "Safest" "Celeris-1 Decision" "Fastino GLiDE" "Jev 1.13.0" "Jev 1.14.0" "Liquid d1-ultra"
      "SubQ Snap Preview")

[[ -x $BIN ]] || { echo "no runner $BIN" >&2; exit 1; }
[[ -z $(git -C "$T" status --porcelain --untracked-files=no) ]] || { echo "runner tree $T is dirty" >&2; exit 1; }
[[ -n ${SUBQ_API_KEY:-} ]] || { echo "SUBQ_API_KEY not set (~/.keys)" >&2; exit 1; }
curl -fsS -m 20 https://api.subq.ai/v1/models -H "Authorization: Bearer $SUBQ_API_KEY" |
  python3 -c 'import json,sys; sys.exit(sys.argv[1] not in [m["id"] for m in json.load(sys.stdin)["data"]])' "$MODEL" ||
  { echo "SubQ's /v1/models does not list $MODEL for our key" >&2; exit 1; }
bal=$(balance) || { echo "OpenRouter credits unreadable" >&2; exit 1; }
lt "$bal" "$FLOOR" && { echo "OpenRouter balance \$$bal: under \$$FLOOR" >&2; exit 1; }

# Once, fail closed: every step must succeed, else nothing after it runs and state/first is not written.
if [[ ! -e $ST/first ]]; then
  raw=$BACKUPS/v3-before-savant.db
  bak=$BACKUPS/v3.db.bak-$(date -u +%Y%m%dT%H%M%S)-before-savant.zst
  fail() { echo "$1" >&2; rm -f "$raw" "$ST/first.new"; exit 1; }
  rm -f "$raw"
  [[ ! -e $bak ]] || fail "$bak already exists"
  sqlite3 v3.db "VACUUM INTO '$raw'" || fail "v3.db backup (VACUUM INTO) to $raw failed"
  zstd -q -T0 "$raw" -o "$bak" || { rm -f "$bak"; fail "zstd of $raw failed"; }
  zstd -q -t "$bak" || { rm -f "$bak"; fail "zstd -t: $bak does not verify"; }
  rm -f "$raw"
  sqlite3 -readonly v3.db "SELECT COALESCE(MAX(id), 0) + 1 FROM matches" > "$ST/first.new" && [[ -s $ST/first.new ]] ||
    fail "first match id unreadable"
  sav trigger >> $ST/guard.log 2>&1 || fail "trigger failed"
  sav configs >> $ST/guard.log 2>&1 || fail "configs failed"
  date -u '+%F %T' > $ST/since || fail "state/since not written"
  mv "$ST/first.new" "$ST/first" || fail "state/first not written"
  echo "$(date -u +%FT%TZ) backup $bak verified (zstd -t); first match #$(cat $ST/first)" >> $ST/guard.log
fi
[[ -e $STATUS ]] || printf '# Late entry %s - status\n\nGo: Can %s. First match id: #%s.\n\n## Log\n' \
  "$NAME" "$APPROVAL" "$(cat $ST/first)" > "$STATUS"
log "guard up (go $APPROVAL): runner $(git -C "$T" rev-parse --short HEAD) clean; $NAME on SubQ ($MODEL listed); OpenRouter \$$bal; floor \$$FLOOR; entry cap \$$CAP (ledger \$$(sav ledger) + paid opponents from #$(cat $ST/first)); 9 opponents, up to 2 matches at once (GPT-6 Luna, Mercury Decide not required; 8 local setups later)"

stop_league() { systemctl --user stop $UNIT 2>/dev/null; }
restarts=0
unread=0
t0=$SECONDS
while true; do
  if [[ $(sav pending "${OPPS[@]}") == 0 ]]; then
    stop_league; log "done: all 9 first-stage pairs played; spent \$$(spent) (ledger \$$(sav ledger)); $(sav projection "$(cat $ST/first)" | tail -1); locals next (Main books a GPU)"; exit 0
  fi
  if bal=$(balance); then
    unread=0
    if lt "$bal" "$FLOOR"; then
      stop_league; log "STOPPED: OpenRouter balance \$$bal under \$$FLOOR; spent \$$(spent)"; exit 1
    fi
  else
    unread=$((unread + 1))
    if (( unread >= 3 )); then
      stop_league; log "STOPPED: OpenRouter balance unreadable 3 times in a row; spent \$$(spent)"; exit 1
    fi
  fi
  s=$(spent)
  if ! lt "$s" "$CAP"; then
    stop_league; log "STOPPED: entry spend \$$s (ledger + paid opponents) reached the \$$CAP cap"; exit 1
  fi
  if [[ ! -e $ST/inflight-logged ]]; then
    first20=$(sav inflight "$(cat $ST/first)" 20 2>&1)
    if [[ $first20 == "20 decisions"* ]]; then
      log "in flight, first decisions: $first20; spent \$$s"
      touch $ST/inflight-logged
    fi
  fi
  if ! systemctl --user is-active -q $UNIT; then
    read -r opened blocked < <(sav scope | head -1)
    if [[ -n ${opened:-} && $opened -gt 0 && $opened == "$blocked" ]]; then
      log "STOPPED: every open pair is blocked: $(sav scope | tail -n +2 | tr '\n' ' ')"; exit 1
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
