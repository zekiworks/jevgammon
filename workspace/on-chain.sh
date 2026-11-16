#!/usr/bin/env bash
# Thinking-on backgammon first stages, one model at a time on bariton GPU 2 under the booking RES (jevgammon, 15 Nov).
# Per pair SERVE_KEY:ENTRY_KEY: serve with logic's small_models.py (published setup), one free test request, the
# late-smallchat-on first stage, the stage watcher (stops the units at 9 required pairs), stop the server, log.
# Stops the whole chain at the first failed serve or test (nothing started for that model).
#   bash workspace/on-chain.sh minicpm5-2b:minicpm5-2b-on lfm3-1.7b-vllm:lfm3-1.7b-on ...
set -u
J=/home/cbasaran/code/jevgammon; W=$HOME/.cache/jevgammon-wt/late-smallchat-on; B=$HOME/.cache/jevgammon-wt/target-late-smallchat-on/release/jevgammon
G=${GPU:-2}   # bariton GPU index; GPU 3 carries ~1 GB of desktop processes, hence the 2 GB "empty" threshold below
L=$HOME/code/benchmark/logic; U=$(nvidia-smi -i "$G" --query-gpu=uuid --format=csv,noheader | tr -d ' ')
# Batch spending bound (Ümit's rule #9719, Zeki #9937/#10006): BATCH_CAP_USD = the approved ceiling for the whole batch.
# Entries run strictly one at a time. Each entry reserves ENTRY_CAP_USD (passed to start.sh's guard) + OVERSHOOT_USD: the guard
# checks every 60 s, so an entry can pass its cap by at most one minute of paid calls already sent. Measured on every small
# chat entry so far (12, v3.db): paid opponents' cost per entry <= $0.071, per minute <= $0.037; OVERSHOOT_USD defaults to
# $0.10. That margin is empirical, not a proof: a hard bound needs pre-send reservations in the runner. Before each entry:
# billed so far (paid opponents' turns only, in this batch's entries' late-entry matches, from v3.db) + ENTRY_CAP_USD +
# OVERSHOOT_USD must stay within BATCH_CAP_USD, else the chain stops and starts nothing more. No cap, no paid dispatch.
CAP=${BATCH_CAP_USD:?set BATCH_CAP_USD to the approved batch ceiling}; ECAP=${ENTRY_CAP_USD:-5}; OVER=${OVERSHOOT_USD:-0.10}
names=()
billed() {  # USD billed so far by the opponents (not the entrants) in the late-entry matches of "${names[@]}"
  ((${#names[@]})) || { echo 0; return; }
  python3 - "$J/v3.db" "${names[@]}" <<'E'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); ns = sys.argv[2:]; q = ",".join("?" * len(ns))
print(db.execute(f"""SELECT coalesce(sum(t.cost_usd),0) FROM turns t JOIN games g ON g.id=t.game_id JOIN matches m ON m.id=g.match_id
  JOIN players a ON a.id=m.player1 JOIN players b ON b.id=m.player2
  JOIN players p ON p.id=(CASE t.side WHEN 1 THEN m.player1 ELSE m.player2 END)
  WHERE m.stage='late-entry' AND (a.name IN ({q}) OR b.name IN ({q})) AND p.name NOT IN ({q})""", ns * 3).fetchone()[0])
E
}
for p in "$@"; do
  s=${p%%:*}; k=${p#*:}
  echo "$(date -u +%FT%TZ) == $k (serve $s)"
  spent=$(billed)
  if ! python3 -c "import sys; sys.exit(0 if $spent + $ECAP + $OVER <= $CAP else 1)"; then
    echo "$(date -u +%FT%TZ) batch cap: billed \$$spent + entry cap \$$ECAP + overshoot \$$OVER > \$$CAP; chain stopped before $k"; exit 2
  fi
  names+=("$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$W/tools/v3/late-smallchat/models/$k/player.json")")
  until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$G")" -lt 2000 ]; do sleep 10; done
  (cd "$L" && timeout 1800 python3 work/small_models.py serve "$s" "$U") 2>&1 | tail -1
  if ! (cd "$J" && SMALLCHAT_BIN=$B timeout 1800 bash "$W/tools/v3/late-smallchat/test.sh" "$k") 2>&1 | tail -1 | tee /dev/stderr | grep -q "test decision valid"; then
    echo "$(date -u +%FT%TZ) $k: test failed; chain stopped (server left up for a look)"; exit 1
  fi
  (cd "$J" && systemd-run --user --unit="late-smallchat-$k" --working-directory="$J" -E SMALLCHAT_BIN="$B" -E ENTRY_CAP_USD="$ECAP" \
     -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/games "$W/tools/v3/late-smallchat/start.sh" "$k")
  until systemctl --user is-active -q "late-smallchat-$k-league" || ! systemctl --user is-active -q "late-smallchat-$k"; do sleep 20; done
  sleep 60
  (cd "$J" && bash workspace/stage-done-watch.sh)
  (cd "$L" && python3 work/small_models.py stop "$s") 2>&1 | tail -1
  f=$(ls "$J"/mailbox/*"$k"* 2>/dev/null | head -1)
  if [[ -n $f ]]; then
    echo "- $(date -u +%FT%TZ) first stage done (watcher); units stopped; server stopped" >> "$f"
    (cd "$J" && git add "$f" && git commit -qm "mailbox: $k first stage done" && git pull -q --rebase --autostash && git push -q origin main)
  fi
done
echo "$(date -u +%FT%TZ) chain done"
