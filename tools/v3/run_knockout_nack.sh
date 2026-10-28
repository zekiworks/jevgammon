#!/usr/bin/env bash
# Nackgammon knockout (leagues/knockout-nack.json; Can's brief of 2026-10-27, point 3): plays the
# Hype Cup bracket with every game from the Nackgammon start, into knockout-nack.db only (never
# v3.db), one two-player league per tie (as the ladder's early starts play one setup's pairs in a
# league of their own). Can's go for the 2026-10-28 roster (Hype Cup roster 2026-10-28):
#   systemd-run --user --unit=knockout-nack --working-directory=/home/cbasaran/code/jevgammon \
#     bash -c 'tools/v3/run_knockout_nack.sh >> knockout-nack.log 2>&1'
# `--check` validates the database, the config and the binary, writes the quarter-final configs and
# prints the bracket, without a model call or a match. `--only QF1,QF4` plays (or resumes) only those
# quarter-finals and stops, so ties on a busy subscription can wait (one job per subscription at a
# time); a later full run reads the finished ties from the database.
# Bracket (Hype Cup draw, players in seed order in the config): QF1 1 v 8, QF2 2 v 6, QF3 3 v 7,
# QF4 4 v 5; SF A winner QF1 v winner QF4, SF B winner QF2 v winner QF3; final. The ties of a stage
# play at once (logs knockout-nack/<TIE>.log). Running it again continues: a finished tie is read
# from the database, an unfinished one resumes from its last stored turn. A level match stops the
# run: the Cup rule (lower error rate in the match) needs this database's own GNUbg scores.
# Gemma 4 31B (on) (QF1) needs its vLLM server up (http://127.0.0.1:8894/v1).
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
# Keys kept in their own files, read when the environment has none (as run_league1.sh).
[ -n "${CELERIS_API_KEY:-}" ] || { CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }
set -euo pipefail
DB=knockout-nack.db
CONFIG=leagues/knockout-nack.json
BIN=./target/knockout/release/jevgammon
# Error-rate shards of this database (none yet); never the site's v3 shards, whose turn ids differ.
SCORES=knockout-nack-scores
TIES=knockout-nack

ONLY=""
case "${1:-}" in
  "") CHECK=0 ;;
  --check) CHECK=1 ;;
  --only) CHECK=0; ONLY=${2:?usage: $0 --only QF1,QF4} ;;
  *) echo "usage: $0 [--check | --only QF1,QF4] (the database is always $DB)" >&2; exit 2 ;;
esac

# Bracket bookkeeping: reads knockout-nack.db read-only, writes only the tie configs.
kn() {
  python3 - "$@" <<'PY'
import json, os, sqlite3, sys

DB, CONFIG, TIES = "knockout-nack.db", "leagues/knockout-nack.json", "knockout-nack"
cmd, *args = sys.argv[1:]
config = json.load(open(CONFIG))
seeds = [p["name"] for p in config["players"]]


def conn():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)


def tag(tie):
    return f"Nackgammon knockout {tie}:"


def league(tie):
    t = tag(tie)
    return conn().execute(
        "SELECT id, status FROM leagues WHERE substr(note, 1, length(?1)) = ?1 ORDER BY id DESC LIMIT 1",
        (t,)).fetchone()


if cmd == "check":
    assert config["start_position"] == "nackgammon" and config["prompt_version"] == "bg-v3-nack", CONFIG
    assert len(seeds) == 8 == len(set(seeds)), "8 distinct teams"
    if not os.path.isfile(DB):
        sys.exit(f"{DB} is missing: `target/knockout/release/jevgammon rank --db {DB}` creates the schema "
                 "(then says `no such league`)")
    c = conn()
    columns = {r[1] for r in c.execute("PRAGMA table_info(leagues)")}
    if "start_position" not in columns:
        sys.exit(f"{DB} has no leagues.start_position: not a knockout database of this runner")
    other = c.execute("""SELECT COUNT(*) FROM leagues WHERE start_position IS NOT 'nackgammon'
                         OR prompt_version IS NOT 'bg-v3-nack'""").fetchone()[0]
    other += c.execute("SELECT COUNT(*) FROM matches WHERE start_position IS NOT 'nackgammon'").fetchone()[0]
    if other:
        sys.exit(f"{DB} holds {other} leagues or matches not under the Nackgammon start: refusing")
elif cmd == "seed":
    print(seeds[int(args[0]) - 1])
elif cmd == "config":
    tie, a, b = args
    players = {p["name"]: p for p in config["players"]}
    out = dict(config, players=[players[a], players[b]],
               note=f"{tag(tie)} {a} v {b}. Nackgammon start, prompt bg-v3-nack, league match rules; "
                    f"bracket and teams: {CONFIG}.")
    os.makedirs(TIES, exist_ok=True)
    path = f"{TIES}/{tie}.json"
    with open(path, "w") as f:
        f.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(path)
elif cmd == "league":
    row = league(args[0])
    print(f"{row[0]} {row[1]}" if row else "")
elif cmd == "winner":
    tie = args[0]
    row = league(tie)
    if row is None or row[1] != "finished":
        sys.exit(f"{tie} has not finished")
    m = conn().execute(
        """SELECT v.match_id, v.model1, v.model2, m.status, m.winner, m.score1, m.score2, m.start_position
           FROM league_match_view v JOIN matches m ON m.id = v.match_id WHERE v.league_id = ?""",
        (row[0],)).fetchall()
    if len(m) != 1 or m[0][3] != "finished" or m[0][7] != "nackgammon":
        sys.exit(f"{tie}: league #{row[0]} does not hold one finished Nackgammon match: {m}")
    match_id, a, b, _, winner, s1, s2, _ = m[0]
    if winner is None:
        sys.exit(f"{tie}: match #{match_id} {a} v {b} is level {s1}-{s2}; the Cup rule (lower error rate "
                 f"in the match) needs {DB}'s own GNUbg scores; decide it before running on")
    print(a if winner == 1 else b)
    print(f"{tie}: match #{match_id} {a} {s1}-{s2} {b}, winner {a if winner == 1 else b}", file=sys.stderr)
else:
    sys.exit(f"unknown command {cmd}")
PY
}

if [ "$(realpath -m "$DB")" = "$(realpath -m v3.db)" ] || [ "$DB" -ef v3.db ]; then
  echo "$DB is v3.db: refusing" >&2
  exit 1
fi
[[ "$("$BIN" league --help)" == *--start-position* ]] \
  || { echo "$BIN has no Nackgammon start: build it with CARGO_TARGET_DIR=target/knockout cargo build --release" >&2; exit 1; }
kn check

# play TIE A B: one tie, as a two-player league; resumed or skipped once it exists.
play() {
  local tie=$1 row
  row=$(kn league "$tie")
  if [ -z "$row" ]; then
    "$BIN" league --config "$(kn config "$tie" "$2" "$3")" --db "$DB" --scores "$SCORES"
  elif [ "${row#* }" != finished ]; then
    "$BIN" league --resume "${row%% *}" --db "$DB" --scores "$SCORES"
  fi
}

# stage TIE A B [TIE A B ...]: the ties at once; fails when one fails.
stage() {
  local pids=() ties=() failed=0 i
  mkdir -p "$TIES"
  while [ "$#" -gt 0 ]; do
    echo "$(date -u +%FT%TZ) $1: $2 v $3 (log $TIES/$1.log)"
    play "$1" "$2" "$3" >> "$TIES/$1.log" 2>&1 &
    pids+=("$!")
    ties+=("$1")
    shift 3
  done
  for i in "${!pids[@]}"; do
    wait "${pids[$i]}" || { echo "${ties[$i]} failed (see $TIES/${ties[$i]}.log)" >&2; failed=1; }
  done
  return "$failed"
}

S=()
for n in 1 2 3 4 5 6 7 8; do S[n]=$(kn seed "$n"); done
if [ "$CHECK" = 1 ]; then
  for t in "QF1 1 8" "QF2 2 6" "QF3 3 7" "QF4 4 5"; do
    set -- $t
    echo "$1: ${S[$2]} ($2) v ${S[$3]} ($3): $(kn config "$1" "${S[$2]}" "${S[$3]}")"
  done
  echo "SF A: winner QF1 v winner QF4; SF B: winner QF2 v winner QF3; final: the semi-final winners"
  echo "check passed: no match was started"
  exit 0
fi

if [ -n "$ONLY" ]; then
  ARGS=()
  for t in "QF1 1 8" "QF2 2 6" "QF3 3 7" "QF4 4 5"; do
    set -- $t
    [[ ",$ONLY," == *",$1,"* ]] && ARGS+=("$1" "${S[$2]}" "${S[$3]}")
  done
  [ "${#ARGS[@]}" -gt 0 ] || { echo "--only: no quarter-final in '$ONLY'" >&2; exit 2; }
  stage "${ARGS[@]}"
  echo "$(date -u +%FT%TZ) --only $ONLY: done"
  exit 0
fi
stage QF1 "${S[1]}" "${S[8]}" QF2 "${S[2]}" "${S[6]}" QF3 "${S[3]}" "${S[7]}" QF4 "${S[4]}" "${S[5]}"
W1=$(kn winner QF1); W2=$(kn winner QF2); W3=$(kn winner QF3); W4=$(kn winner QF4)
stage SFA "$W1" "$W4" SFB "$W2" "$W3"
WA=$(kn winner SFA); WB=$(kn winner SFB)
stage FINAL "$WA" "$WB"
echo "$(date -u +%FT%TZ) Nackgammon knockout champion: $(kn winner FINAL)"
