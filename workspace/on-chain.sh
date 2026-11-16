#!/usr/bin/env bash
# Thinking-on backgammon first stages, one model at a time on bariton GPU 2 under the booking RES (jevgammon, 15 Nov).
# Per pair SERVE_KEY:ENTRY_KEY: serve with logic's small_models.py (published setup), one free test request, the
# late-smallchat-on first stage, the stage watcher (stops the units at 9 required pairs), stop the server, log.
# Stops the whole chain at the first failed serve or test (nothing started for that model).
#   bash workspace/on-chain.sh minicpm5-2b:minicpm5-2b-on lfm3-1.7b-vllm:lfm3-1.7b-on ...
set -u
J=/home/cbasaran/code/jevgammon
# The late-smallchat runner tree and its runner (CHAIN_TREE / CHAIN_BIN override the live ones): both must carry the run
# guard (smallchat.py guard; runner guard-ledger, admit/league --guard), else the chain stops before any entry.
W=${CHAIN_TREE:-$HOME/.cache/jevgammon-wt/late-smallchat-on}; B=${CHAIN_BIN:-$HOME/.cache/jevgammon-wt/target-late-smallchat-on/release/jevgammon}
G=${GPU:-2}   # bariton GPU index; GPU 3 carries ~1 GB of desktop processes, hence the 2 GB "empty" threshold below
L=$HOME/code/benchmark/logic; U=$(nvidia-smi -i "$G" --query-gpu=uuid --format=csv,noheader | tr -d ' ')
# Batch spending bound (Ümit's rule #9719, Zeki #9937/#10006/#10062): BATCH_CAP_USD = the approved ceiling for the whole
# batch, enforced per request by the runner's run guard. The batch's guard file is written once (smallchat.py guard) into
# BATCH_GUARD_DIR (default workspace/late-smallchat/batch-guard-<UTC start>; name an earlier batch's directory to go on
# under its ledger): every paid opponent of every entry metered at its list price under one ledger (BATCH_GUARD_DIR/
# ledger.db) and the cap. Every request attempt reserves its worst case ((request bytes + 4,096) x input price) before it
# is sent and is refused when spent + reserved + it would pass the cap; a participant neither metered nor local is
# refused at admission; a refusal stops the league and writes BATCH_GUARD_DIR/latch, which keeps every entry from
# starting until a person removes it. start.sh gets the file as GUARD_FILE. Entries run strictly one at a time. Second
# line, read-only: before each entry the latch must be absent and billed so far (paid opponents' turns in this batch's
# entries' late-entry matches, v3.db; Fastino GLiDE, which records no cost, at its $0.15/M list price) under
# BATCH_CAP_USD, else the chain stops and starts nothing more. No cap, no paid dispatch.
CAP=${BATCH_CAP_USD:?set BATCH_CAP_USD to the approved batch ceiling}
(($#)) || { echo "usage: on-chain.sh SERVE_KEY:ENTRY_KEY ..."; exit 2; }
D=${BATCH_GUARD_DIR:-$J/workspace/late-smallchat/batch-guard-$(date -u +%Y%m%dT%H%M%SZ)}; GF=$D/guard.json
mkdir -p "$D"
[[ -e $D/METADATA ]] || printf '%s\n' "owner: jevgammon (agent; Can's backgammon project ~/code/jevgammon)" \
  "created: $(date -u +%F)" "what: run guard of one on-chain.sh batch (guard.json, ledger.db, latch when stopped)" \
  "reason: Zeki #10062: the batch cap BATCH_CAP_USD=\$$CAP enforced per request by the runner" \
  "delete when: after the batch is reported (keep the ledger with the report)" > "$D/METADATA"
if [[ ! -e $GF ]]; then
  python3 "$W/tools/v3/late-smallchat/smallchat.py" "${1#*:}" guard "$CAP" "$D/ledger.db" "$D/latch" > "$GF.new" &&
    mv "$GF.new" "$GF" || { rm -f "$GF.new"; echo "$(date -u +%FT%TZ) batch guard not written; chain stopped"; exit 2; }
fi
python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["cap_usd"] != float(sys.argv[2]))' "$GF" "$CAP" ||
  { echo "$(date -u +%FT%TZ) $GF has another cap than BATCH_CAP_USD \$$CAP; chain stopped"; exit 2; }
"$B" guard-ledger --guard "$GF" || { echo "$(date -u +%FT%TZ) batch guard $GF refused (latched?); chain stopped"; exit 2; }
echo "$(date -u +%FT%TZ) batch guard $GF (sha256 $(sha256sum "$GF" | cut -c1-16)…), cap \$$CAP"
names=()
billed() {  # USD billed so far by the opponents (not the entrants) in the late-entry matches of "${names[@]}"
  ((${#names[@]})) || { echo 0; return; }
  python3 - "$J/v3.db" "${names[@]}" <<'E'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); ns = sys.argv[2:]; q = ",".join("?" * len(ns))
print(db.execute(f"""SELECT coalesce(sum(coalesce(t.cost_usd,
    CASE p.name WHEN 'Fastino GLiDE' THEN t.input_tokens * 0.15 / 1e6 END)), 0)
  FROM turns t JOIN games g ON g.id=t.game_id JOIN matches m ON m.id=g.match_id
  JOIN players a ON a.id=m.player1 JOIN players b ON b.id=m.player2
  JOIN players p ON p.id=(CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END)
  WHERE m.stage='late-entry' AND (a.name IN ({q}) OR b.name IN ({q})) AND p.name NOT IN ({q})""", ns * 3).fetchone()[0])
E
}
for p in "$@"; do
  s=${p%%:*}; k=${p#*:}
  echo "$(date -u +%FT%TZ) == $k (serve $s)"
  [[ ! -e $D/latch ]] || { echo "$(date -u +%FT%TZ) batch guard latched ($D/latch: $(tail -1 "$D/latch" | cut -c1-200)); chain stopped before $k"; exit 2; }
  spent=$(billed)
  if ! python3 -c "import sys; sys.exit(0 if $spent < $CAP else 1)"; then
    echo "$(date -u +%FT%TZ) batch cap: billed \$$spent reached \$$CAP; chain stopped before $k"; exit 2
  fi
  names+=("$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$W/tools/v3/late-smallchat/models/$k/player.json")")
  until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$G")" -lt 2000 ]; do sleep 10; done
  (cd "$L" && timeout 1800 python3 work/small_models.py serve "$s" "$U") 2>&1 | tail -1
  if ! (cd "$J" && SMALLCHAT_BIN=$B timeout 1800 bash "$W/tools/v3/late-smallchat/test.sh" "$k") 2>&1 | tail -1 | tee /dev/stderr | grep -q "test decision valid"; then
    echo "$(date -u +%FT%TZ) $k: test failed; chain stopped (server left up for a look)"; exit 1
  fi
  (cd "$J" && systemd-run --user --unit="late-smallchat-$k" --working-directory="$J" -E SMALLCHAT_BIN="$B" -E GUARD_FILE="$GF" \
     -E ENTRY_CAP_USD="${ENTRY_CAP_USD:-$CAP}" -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/games \
     "$W/tools/v3/late-smallchat/start.sh" "$k")
  until systemctl --user is-active -q "late-smallchat-$k-league" || ! systemctl --user is-active -q "late-smallchat-$k"; do sleep 20; done
  if ! systemctl --user is-active -q "late-smallchat-$k-league"; then
    echo "$(date -u +%FT%TZ) $k: start.sh ended before its league ran (guard, admission or a check refused: workspace/late-smallchat/$k/state/guard.log, journalctl --user -u late-smallchat-$k); chain stopped (server left up for a look)"; exit 1
  fi
  sleep 60
  (cd "$J" && bash workspace/stage-done-watch.sh)
  (cd "$L" && python3 work/small_models.py stop "$s") 2>&1 | tail -1
  if [[ -e $D/latch ]]; then
    echo "$(date -u +%FT%TZ) $k: batch guard latched ($D/latch: $(tail -1 "$D/latch" | cut -c1-200)); server stopped; chain stopped"; exit 2
  fi
  f=$(ls "$J"/mailbox/*"$k"* 2>/dev/null | head -1)
  if [[ -n $f ]]; then
    echo "- $(date -u +%FT%TZ) first stage done (watcher); units stopped; server stopped" >> "$f"
    (cd "$J" && git add "$f" && git commit -qm "mailbox: $k first stage done" && git pull -q --rebase --autostash && git push -q origin main)
  fi
done
echo "$(date -u +%FT%TZ) chain done"
