#!/usr/bin/env bash
# Regression tests of run.sh's preflight (Zeki #4737, #4896, #4928), on scratch copies only: never the production v3.db,
# a production budget ledger, the main checkout's state or the runner tree. Each case gets its own copy of these scripts
# and the manifest (repo layout), a clone of the runner tree at the recorded commit, a copy of the recorded binary, and a
# scratch database (the runner's own schema, created by the copied binary, plus the originals' and programs' players
# rows from the manifest, the pinned opponents' rows (name and spec as each original played them; specs from the
# 2026-11-11 admission run, mailbox/pinned-late-review/admission.log) and a late_entry_stage trigger naming the originals
# only, so every repeat starts with "trigger missing"; and REAX 1.3's recorded attempt, league #24, exactly as recorded:
# every column of its leagues and league_players rows, the participants' players rows at their recorded ids).
# Drex Max 1.1's Nace ledger is a scratch ledger (the path replaced in the copies of the manifest, the league configs and
# repeats.py); the keys are a scratch HOME's ~/.keys and Celeris key file with placeholder values (no request is sent).
#   Recorded attempt: league-id skips league #24 (the league unit then starts a new league); a changed #24 refuses: a
#   heartbeat, and (#4928 L1) rounds, seed, hidden, a participant's joined_at, note, max_turns, the pins' stored text, a
#   participant's note or left_at, a column added, a participant added; and (#4954) a league_players column `name`
#   added and filled with the joined names, alone and with the joined players.name then renamed.
#   Admitted settings (#4928 S1): Clef's players row replaced by an UPDATE kept in the write-ahead log (clef ->
#   openai/review-placeholder): admission admits the checkpointed clef, check refuses on the difference alone, run.sh
#   writes nothing (database file and log byte-identical); after an admission, `repeats.py bound` and run_league.sh (a
#   stand-in binary) start no league and `repeats.py entry` gives no league-add text once the config or Clef's row
#   differs from the record, and do while nothing differs.
#   Refusals (a held repeat: REAX 1.3 marked held in the case's manifest copy, as before its release; bad pins, other
#   settings, another binary, a changed or missing build input, a changed src, a descendant commit, Drex Max 1.1's and
#   GLiDE v1.2's pins and budget, a repeat name not yet held in main's site; client admission: a pinned opponent's
#   players row with a subscription-login provider, a required key missing, Drex Max 1.1's ledger missing): run.sh ID
#   --prepare-only exits non-zero, the scratch database's sha256 is unchanged, no backup, no state or status file;
#   repeats.py check exits 1 (not 3) and repeats.py trigger refuses without a write. An admission refusal is the
#   check's only failure besides the missing trigger, and names the refused client; a missing ledger is not created.
#   Trigger missing only (each repeat not held): check exits 3, run.sh prepares (backup verified by zstd -t, trigger),
#   checks again and exits 0 with every client admitted; check then exits 0, and a second run.sh writes nothing more.
#   The scratch Nace ledger is byte-identical after every case, with no -wal or -shm beside it.
# Usage: tools/v3/repeats/test_launcher.sh   (TMPDIR defaults to ~/.cache/tmp; exit 0 when every case passes)
set -uo pipefail
HERE=$(dirname "$(readlink -f "$0")")
REPO=$(cd "$HERE/../../.." && pwd)
export TMPDIR=${TMPDIR:-$HOME/.cache/tmp}
S=$(mktemp -d "$TMPDIR/repeat-launcher-test.XXXXXX")
trap 'rm -rf "$S"' EXIT
MAN=$REPO/mailbox/repeats/manifest-2026-11-11.json
read -r RTREE RBIN RCOMMIT < <(python3 -c 'import json,sys; r=json.load(open(sys.argv[1]))["repeats"][0]["runner"]
print(r["tree"], r["binary"], r["commit_full"])' "$MAN")
echo "runner as recorded: tree $RTREE, binary $RBIN, commit $RCOMMIT"
echo "scratch: $S"

# Templates: the runner tree as a clone at the commit, the binary, the scripts and manifest with a scratch Nace ledger,
# the keys, the scratch database.
git clone -q --shared --no-checkout "$RTREE" "$S/tpl/runner" && git -C "$S/tpl/runner" checkout -q --detach "$RCOMMIT" ||
  { echo "cannot clone $RTREE at $RCOMMIT"; exit 1; }
mkdir -p "$S/tpl/bin" && cp "$RBIN" "$S/tpl/bin/jevgammon"
mkdir -p "$S/tpl/repo/tools/v3" "$S/tpl/repo/mailbox/repeats" "$S/ledger"
cp -r "$HERE" "$S/tpl/repo/tools/v3/repeats"
cp "$MAN" "$S/tpl/repo/mailbox/repeats/"
TMAN=$S/tpl/repo/mailbox/repeats/$(basename "$MAN")
LEDGER=$S/ledger/nace-budget.db
NACE=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import repeats; print(repeats.NACE_LEDGER)' "$HERE")
python3 - "$NACE" "$LEDGER" "$TMAN" "$S/tpl/repo/tools/v3/repeats" <<'EOF' || { echo "ledger fixture failed"; exit 1; }
import sqlite3, sys
from pathlib import Path
nace, ledger, man, rep = sys.argv[1:5]
for p in [Path(man), Path(rep) / "repeats.py", *sorted((Path(rep) / "leagues").glob("*.json"))]:
    p.write_text(p.read_text().replace(nace, ledger))
# The ledger as the runner's Ledger::open leaves it (budget.rs SCHEMA, WAL, the cap row), closed.
conn = sqlite3.connect(ledger)
conn.execute("PRAGMA journal_mode = WAL")
conn.executescript("""
CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK (id = 1), cap_usd REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY, setup TEXT NOT NULL, pid INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
    status TEXT NOT NULL, reserved_usd REAL NOT NULL, cost_usd REAL, list_cost_usd REAL, reported_cost_usd REAL,
    input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER, reasoning_tokens INTEGER, note TEXT);
INSERT INTO budget (id, cap_usd) VALUES (1, 1.25);
""")
conn.commit()
conn.close()
EOF
LEDGER_SHA=$(sha256sum < "$LEDGER")
ledger_intact() { [[ $(sha256sum < "$LEDGER") == "$LEDGER_SHA" && ! -e $LEDGER-wal && ! -e $LEDGER-shm ]]; }
ledger_intact || { echo "the scratch ledger did not close cleanly"; exit 1; }
# Every key the field's decision services require, placeholder values; Celeris' from its key file, as on the host.
keys_home() {  # dir [variable to leave out]
  mkdir -p "$1/.config/celeris"
  local v
  for v in TYPESAFE_API_KEY FASTINO_API_KEY OPENAI_API_KEY LIQUID_API_KEY SUBQ_API_KEY OPENROUTER_API_KEY NACE_API_KEY; do
    [[ $v == "${2:-}" ]] || echo "$v=placeholder-not-a-key"
  done > "$1/.keys"
  [[ ${2:-} == CELERIS_API_KEY ]] || echo placeholder-not-a-key > "$1/.config/celeris/key"
}
keys_home "$S/keys"
"$S/tpl/bin/jevgammon" void --db "$S/tpl/v3.db" --match 1 --reason schema >/dev/null 2>&1  # opens: creates the schema
python3 - "$S/tpl/v3.db" "$TMAN" "$S/tpl/repo/tools/v3/repeats/leagues" <<'EOF' || { echo "fixture failed"; exit 1; }
import json, sqlite3, sys
from pathlib import Path
db, man, leagues = sys.argv[1], json.load(open(sys.argv[2])), Path(sys.argv[3])
conn = sqlite3.connect(db)
if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'players'").fetchone():
    sys.exit("the runner did not create its schema")
rows = {r["original"]: r["settings_original"] for r in man["repeats"]}
for cfg in leagues.glob("*.json"):
    rows |= {p["name"]: p for p in json.loads(cfg.read_text())["players"][1:]}
# The pinned opponents (each original's field), as `jevgammon admit` built them on 2026-11-11 (admission.log): the
# name and spec of each players row; the originals among them keep their manifest settings.
OPPONENTS = {
    "Celeris-1 Decision": "celeris/celeris-1-decision", "Clef": "clef", "Cygnet (Gemma 4 12B)": "cygnet",
    "Decider Flash v1.2": "pplx-local/pplx-decider-flash-v1.2", "Decider v1.1 27B": "pplx-local",
    "Decider v1.2 27B": "pplx-local/pplx-decider-v1.2", "Fastino GLiDE": "fastino",
    "Fastino GLiDE v1.2 (local)": "fastino/glide-v1.2", "GPT-6 Luna": "openai-decisions/gpt-6-luna",
    "Jev 1.13.0": "jev/jev-1.13.0", "Jev 1.14.0": "jev/jev-1.14.0", "Liquid d1-ultra": "liquid/d1-ultra",
    "Mercury Decide": "openrouter-decisions/inception/mercury-decide", "Open-Jev 27B v1.1": "open-jev",
    "SubQ Snap Preview": "subq/subq-snap-preview", "Winnow-12B": "winnow/winnow-12b"}
for name, spec in OPPONENTS.items():
    rows.setdefault(name, dict(name=name, spec=spec))
pins = {o for r in man["repeats"] for o in json.loads((leagues / f"{r['id']}.json").read_text())["pinned_pairs"]}
if pins - set(rows):
    sys.exit(f"pinned opponents without a players row: {sorted(pins - set(rows))}")
# REAX 1.3's first attempt exactly as v3.db holds it (repeats.py REAX_ATTEMPT_1["record"]): league #24's leagues row
# and league_players rows, every column, the participants' players rows at their recorded ids (inserted first; the
# entrant's row as the attempt's league --config inserted it, from the repeat config), no match.
sys.path.insert(0, str(leagues.parent))
import repeats
a = repeats.REAX_ATTEMPT_1
cfg = json.loads((leagues / "reax-1.3-r1.json").read_text())
entrant = cfg["players"][0]
ids = {p["player_name"]: p["player_id"] for p in a["record"]["participants"]}
for name, s in sorted([*rows.items(), (entrant["name"], entrant)], key=lambda kv: kv[0] not in ids):
    conn.execute("INSERT INTO players (id, name, spec, settings, created_at) VALUES (?, ?, ?, ?, ?)",
                 (ids.get(name), name, s.get("spec") or "program", json.dumps(s),
                  a["record"]["league"]["started_at"] if name == entrant["name"] else "2026-11-11T00:00:00Z"))
listed = ", ".join("'" + r["original"].replace("'", "''") + "'" for r in man["repeats"])
conn.execute(f"""CREATE TRIGGER late_entry_stage AFTER INSERT ON matches
WHEN EXISTS (SELECT 1 FROM players p WHERE p.id IN (NEW.player1, NEW.player2)
             AND p.name IN ({listed}))
BEGIN
  UPDATE matches SET stage = 'late-entry' WHERE id = NEW.id;
END""")
league = a["record"]["league"]
columns = [r[1] for r in conn.execute("PRAGMA table_info(leagues)")]
if columns != list(league):
    sys.exit(f"the runner's leagues columns {columns} are not the recorded {list(league)}")
conn.execute(f"INSERT INTO leagues ({', '.join(league)}) VALUES ({', '.join('?' * len(league))})", list(league.values()))
for p in a["record"]["participants"]:
    cols = [k for k in p if k != "player_name"]
    conn.execute(f"INSERT INTO league_players ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                 [p[k] for k in cols])
conn.commit()
print(f"scratch database: runner schema, {len(rows) + 1} players rows, late_entry_stage naming {listed}, "
      f"attempt league #{a['league']} as recorded (every column of its leagues and league_players rows)")
EOF

fails=0
pass() { echo "ok   $C: $*"; }
failc() { echo "FAIL $C: $*"; fails=$((fails + 1)); }
# A case's own copies: D/repo (scripts, leagues, manifest pointing at D/runner and D/bin), D/home (state), D/home/v3.db.
# The keys: the scratch HOME $S/keys, or the case's own (CASE_HOME).
setup() {
  C=$1 D=$S/$1 CASE_HOME=
  mkdir -p "$D/repo/tools/v3" "$D/repo/mailbox/repeats" "$D/home"
  cp -r "$S/tpl/repo/tools/v3/repeats" "$D/repo/tools/v3/repeats"
  cp -a "$S/tpl/runner" "$D/runner"
  cp -a "$S/tpl/bin" "$D/bin"
  cp "$S/tpl/v3.db" "$D/home/v3.db"
  python3 - "$TMAN" "$D/repo/mailbox/repeats/$(basename "$MAN")" "$D" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1]))
for r in m["repeats"]:
    r["runner"] |= dict(tree=sys.argv[3] + "/runner", binary=sys.argv[3] + "/bin/jevgammon")
open(sys.argv[2], "w").write(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
EOF
}
in_case() { HOME=${CASE_HOME:-$S/keys} JEVGAMMON_DB=$D/home/v3.db REPEATS_HOME=$D/home "$@"; }
check_rc() { in_case python3 "$D/repo/tools/v3/repeats/repeats.py" check "$1" > "$D/check.out" 2>&1; echo $?; }
# An admission refusal is the check's only failure besides the missing trigger (problems() lists every other check
# before admission and only the trigger after it), and its text names the refusal.
admission_only() {  # rid expected-text
  if [[ $(wc -l < "$D/check.out") == 1 ]] &&
     grep -qE "^$1: client admission refused \(jevgammon admit exit 1\): .*$2.*; trigger missing: late_entry_stage does not name it$" "$D/check.out"; then
    pass "check's only failure (with the missing trigger) is the admission refusal: $(grep -oE "REFUSED[^|]*$2[^|]*" "$D/check.out" | head -1 | cut -c1-200)"
  else
    failc "check did not fail on the admission refusal alone: $(cut -c1-600 "$D/check.out")"
  fi
}

refuse() {  # case id: run after the case's mutation
  local rid=$1 before after rc crc trc
  before=$(sha256sum < "$D/home/v3.db")
  in_case bash "$D/repo/tools/v3/repeats/run.sh" "$rid" --prepare-only > "$D/run.out" 2>&1
  rc=$?
  after=$(sha256sum < "$D/home/v3.db")
  crc=$(check_rc "$rid")
  in_case python3 "$D/repo/tools/v3/repeats/repeats.py" trigger "$rid" > "$D/trigger.out" 2>&1
  trc=$?
  [[ $(sha256sum < "$D/home/v3.db") == "$before" ]] || after=changed-by-trigger
  echo "     run.sh: exit $rc: $(tr '\n' ' ' < "$D/run.out" | cut -c1-600)"
  echo "     check: exit $crc; trigger: exit $trc: $(tr '\n' ' ' < "$D/trigger.out" | cut -c1-200)"
  local bad=()
  (( rc != 0 )) || bad+=("run.sh exited 0")
  [[ $after == "$before" ]] || bad+=("database changed")
  compgen -G "$D/home/v3.db.bak-*" >/dev/null && bad+=("backup written")
  [[ -e $D/home/workspace || -e $D/home/mailbox ]] && bad+=("state or status written")
  (( crc == 1 )) || bad+=("check exit $crc, not 1")
  (( trc != 0 )) || bad+=("trigger did not refuse")
  if (( ${#bad[@]} )); then failc "${bad[*]}"; else pass "refused; scratch sha256 ${before%% *} unchanged; no backup, state or trigger write"; fi
}

setup held-reax
python3 - "$D/repo/mailbox/repeats/$(basename "$MAN")" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1]))
for r in m["repeats"]:
    if r["id"] == "reax-1.3-r1":
        r |= dict(status="held", hold="test: held as before its release (ac08899)")
open(sys.argv[1], "w").write(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
EOF
refuse reax-1.3-r1
setup bad-pins
python3 - "$D/repo/tools/v3/repeats/leagues/mammoth-1-r1.json" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1])); o = next(iter(c["pinned_pairs"])); c["pinned_pairs"][o]["seed"] ^= 1
open(sys.argv[1], "w").write(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
EOF
refuse mammoth-1-r1
setup bad-pin-seat
python3 - "$D/repo/tools/v3/repeats/leagues/drex-max-v1-r1.json" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1])); o = next(iter(c["pinned_pairs"])); c["pinned_pairs"][o]["seat_first"] ^= True
open(sys.argv[1], "w").write(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
EOF
refuse drex-max-v1-r1
setup bad-settings
python3 - "$D/repo/tools/v3/repeats/leagues/d1-ultra-r1.json" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1])); c["players"][0]["max_matches"] = 2
open(sys.argv[1], "w").write(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
EOF
refuse d1-ultra-r1
setup wrong-binary; printf '\0' >> "$D/bin/jevgammon"; refuse mammoth-1-r1
setup missing-binary; rm "$D/bin/jevgammon"; refuse mammoth-1-r1
setup changed-input; echo "changed" >> "$D/runner/prompts/bg-v2.md"; refuse mammoth-1-r1
setup missing-input; rm "$D/runner/tools/v3/order_vectors.json"; refuse mammoth-1-r1
setup changed-lock; echo "# changed" >> "$D/runner/Cargo.lock"; refuse drex-max-v1-r1
setup extra-src; echo "// new" > "$D/runner/src/extra.rs"; refuse mammoth-1-r1
setup descendant-commit
git -C "$D/runner" -c user.name=test -c user.email=test@localhost commit -q --allow-empty -m "plan-only descendant"
refuse mammoth-1-r1
setup bad-pins-glide
python3 - "$D/repo/tools/v3/repeats/leagues/glide-v1.2-r1.json" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1])); c["pinned_pairs"]["Clef"]["seed"] ^= 1
open(sys.argv[1], "w").write(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
EOF
refuse glide-v1.2-r1
setup bad-settings-drex11
python3 - "$D/repo/tools/v3/repeats/leagues/drex-max-1.1-r1.json" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1])); c["players"][0]["budget"]["cap_usd"] = 2.5
open(sys.argv[1], "w").write(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
EOF
refuse drex-max-1.1-r1

# Client admission (Zeki #4896): the bound runner's `jevgammon admit` refuses a client, so check exits 1 before any
# write. A pinned opponent's players row naming a subscription login (refused before its client is constructed):
setup admission-oauth-opponent
sqlite3 "$D/home/v3.db" "UPDATE players SET spec = 'openai/gpt-5.6', settings = json_set(settings, '$.spec', 'openai/gpt-5.6')
                         WHERE name = 'Jev 1.13.0'"
refuse mammoth-1-r1
admission_only mammoth-1-r1 "Jev 1.13.0 \(openai/gpt-5.6; players #[0-9]+\): provider .openai. of .openai/gpt-5.6. is outside the admission roster"
# A client that cannot be built: Celeris' required key missing (no CELERIS_API_KEY, no key file).
setup admission-key-missing
CASE_HOME=$D/keys; keys_home "$CASE_HOME" CELERIS_API_KEY
refuse reax-1.3-r1
admission_only reax-1.3-r1 "Celeris-1 Decision \(celeris/celeris-1-decision; players #[0-9]+\): .*needs an API key"
# Drex Max 1.1's budget ledger missing: refused, and not created (the writable Ledger::open would create it).
setup admission-ledger-missing
mv "$LEDGER" "$LEDGER.away"
refuse drex-max-1.1-r1
admission_only drex-max-1.1-r1 "Drex Max 1.1 \[repeat 1\] \(nace/drex-max-v1.1; league config\): budget ledger .* does not exist"
[[ ! -e $LEDGER && ! -e $LEDGER-wal && ! -e $LEDGER-shm ]] && pass "the missing ledger was not created" ||
  failc "admission created $LEDGER"
rm -f "$LEDGER" "$LEDGER-wal" "$LEDGER-shm"; mv "$LEDGER.away" "$LEDGER"

# The real runner as recorded (tree, binary, inputs; the unmodified manifest) against a scratch database: only the
# trigger is missing (exit 3); nothing is written.
C=recorded-runner D=$S/recorded-runner
mkdir -p "$D" && cp "$S/tpl/v3.db" "$D/v3.db"
before=$(sha256sum < "$D/v3.db")
out=$(HOME=$S/keys JEVGAMMON_DB=$D/v3.db python3 "$HERE/repeats.py" check mammoth-1-r1 2>&1); rc=$?
echo "     check (recorded runner $RTREE, $RBIN): exit $rc: $out"
if (( rc == 3 )) && [[ $(sha256sum < "$D/v3.db") == "$before" ]]; then pass "the recorded runner binds; only the trigger is missing"
else failc "check exit $rc or the database changed"; fi

# REAX 1.3's recorded attempt (league #24 on 4ca4f08, Zeki #4886): league-id never names it, so the league unit starts
# a new league; a changed attempt league (here: a heartbeat, as a resume would write) refuses like any other failure.
C=attempt-skipped D=$S/attempt-skipped
mkdir -p "$D" && cp "$S/tpl/v3.db" "$D/v3.db"
lid=$(JEVGAMMON_DB=$D/v3.db python3 "$HERE/repeats.py" league-id reax-1.3-r1)
n=$(sqlite3 "$D/v3.db" "SELECT count(*) FROM leagues WHERE id = 24 AND only_pairs_of = 'REAX 1.3 [repeat 1]'")
[[ -z $lid && $n == 1 ]] && pass "league #24 exists for the repeat name; league-id names no league (a new one is created)" ||
  failc "league-id printed '$lid' (league #24 rows: $n)"
setup attempt-resumed
sqlite3 "$D/home/v3.db" "UPDATE leagues SET heartbeat_at = '2026-11-11T17:00:00.000Z' WHERE id = 24"
refuse reax-1.3-r1
grep -q "attempt league #24 changed" "$D/check.out" && pass "the refusal names the changed attempt league" ||
  failc "check did not name the changed attempt league: $(cat "$D/check.out")"
# Zeki #4928 L1: league #24's historical rows are bound column by column, not only its times, status and participant
# names: the reviewer's changed rounds, seed, hidden flag and participant joined_at, and any other column (its note,
# max_turns, the same pins in other stored text, a participant's note or left_at, a column added, a participant
# added) refuse before any write.
for mutation in "rounds|UPDATE leagues SET rounds = 999 WHERE id = 24" \
                "seed|UPDATE leagues SET seed = 999 WHERE id = 24" \
                "hidden|UPDATE leagues SET hidden = 0 WHERE id = 24" \
                "joined_at|UPDATE league_players SET joined_at = 'changed' WHERE league_id = 24" \
                "note|UPDATE leagues SET note = note || ' ' WHERE id = 24" \
                "max_turns|UPDATE leagues SET max_turns = 301 WHERE id = 24" \
                "pinned_pairs|UPDATE leagues SET pinned_pairs = ' ' || pinned_pairs WHERE id = 24" \
                "league_players|UPDATE league_players SET note = 'x' WHERE id = 370" \
                "league_players|UPDATE league_players SET left_at = '2026-11-11T16:00:00.000Z' WHERE id = 372" \
                "extra|ALTER TABLE leagues ADD COLUMN extra TEXT" \
                "league_players|INSERT INTO league_players (league_id, player_id, joined_at) SELECT 24, id, 'x' FROM players WHERE name = 'Clef'"; do
  col=${mutation%%|*} sql=${mutation#*|}
  setup "attempt-$col-$(sha256sum <<< "$sql" | cut -c1-6)"
  sqlite3 "$D/home/v3.db" "$sql"
  echo "     $sql"
  refuse reax-1.3-r1
  grep -qE "attempt league #24 changed: (.* )?$col " "$D/check.out" && pass "the refusal names #24's changed $col" ||
    failc "check did not name #24's changed $col: $(cut -c1-600 "$D/check.out")"
done

# Zeki #4954 (L1 residual): a league_players column named `name` must not collapse into the joined players.name. The
# participants are read by an explicit projection (the recorded columns, the joined name as player_name), and any
# other league_players column set refuses. (1) league_players.name added and filled with the joined names; (2) the same,
# then the joined players.name renamed (the change the collision used to hide). Each refuses before any preparation
# write, on league #24 alone (besides the missing trigger).
attempt_only() {  # expected-text...: check's one line is league #24's change (and the missing trigger), naming each
  local t ok=1
  grep -qE "^reax-1\.3-r1: attempt league #24 changed: .*; trigger missing: late_entry_stage does not name it$" "$D/check.out" &&
    [[ $(wc -l < "$D/check.out") == 1 ]] || ok=0
  for t in "$@"; do grep -qF -- "$t" "$D/check.out" || ok=0; done
  if (( ok )); then pass "the refusal is league #24's change alone, naming: $*"
  else failc "check did not refuse on league #24's change alone ($*): $(cut -c1-800 "$D/check.out")"; fi
}
setup lp-name-added
sqlite3 "$D/home/v3.db" "ALTER TABLE league_players ADD COLUMN name TEXT;
  UPDATE league_players SET name = (SELECT p.name FROM players p WHERE p.id = league_players.player_id)"
echo "     league_players: $(sqlite3 "$D/home/v3.db" "SELECT group_concat(name, ', ') FROM pragma_table_info('league_players')")"
refuse reax-1.3-r1
attempt_only "league_players columns ['id', 'league_id', 'player_id', 'joined_at', 'left_at', 'note', 'name'] (recorded ['id', 'league_id', 'player_id', 'joined_at', 'left_at', 'note'])"
setup lp-name-added-joined-renamed
sqlite3 "$D/home/v3.db" "ALTER TABLE league_players ADD COLUMN name TEXT;
  UPDATE league_players SET name = (SELECT p.name FROM players p WHERE p.id = league_players.player_id);
  UPDATE players SET name = 'REAX 1.3 [repeat 1] (renamed)' WHERE id = 65"
refuse reax-1.3-r1
attempt_only "league_players columns ['id', 'league_id', 'player_id', 'joined_at', 'left_at', 'note', 'name']" \
  "league_players #369 player_name 'REAX 1.3 [repeat 1] (renamed)' (recorded 'REAX 1.3 [repeat 1]')"

# Zeki #4928 S1: admission reads v3.db immutably (its main file), the league reads the current rows. A writer that never
# checkpoints commits Clef's replacement (clef -> openai/review-placeholder, the reviewer's fixture) and keeps it in the
# write-ahead log until $D/release exists.
hold_wal() {  # db
  rm -f "$D/held" "$D/release"
  python3 - "$1" "$D" <<'EOF' &
import json, os, sqlite3, sys, time
db, d = sys.argv[1:3]
c = sqlite3.connect(db)
c.execute("PRAGMA wal_autocheckpoint = 0")
c.execute("UPDATE players SET spec = 'openai/review-placeholder', settings = ? WHERE name = 'Clef'",
          (json.dumps({"name": "Clef", "spec": "openai/review-placeholder"}),))
c.commit()
open(os.path.join(d, "held"), "w").close()
while not os.path.exists(os.path.join(d, "release")):
    time.sleep(0.1)
c.close()
EOF
  HOLDER=$!
  for _ in $(seq 100); do [[ -e $D/held ]] && return 0; sleep 0.1; done
  return 1
}
release_wal() { touch "$D/release"; wait "$HOLDER"; }
# Before any preparation: admission admits the checkpointed clef, check compares its admitted-settings record with an
# ordinary read-only read (which sees the log) and refuses on that alone (besides the missing trigger); run.sh writes
# nothing, the database file and its log byte-identical.
setup clef-in-log
hold_wal "$D/home/v3.db" || failc "the writer did not commit"
wal=$(sha256sum < "$D/home/v3.db-wal")
refuse reax-1.3-r1
[[ $(sha256sum < "$D/home/v3.db-wal") == "$wal" ]] && pass "the write-ahead log byte-identical (Clef's replacement only there)" ||
  failc "the write-ahead log changed"
if [[ $(wc -l < "$D/check.out") == 1 ]] && grep -qE "^reax-1\.3-r1: Clef: v3\.db's settings now \(players #[0-9]+, sha256 [0-9a-f]{16}…\) are not the ones admitted \(players #[0-9]+, sha256 [0-9a-f]{16}…\); trigger missing: late_entry_stage does not name it$" "$D/check.out"; then
  pass "every client admitted (Clef as clef, from the main file); the refusal is Clef's settings differing from the admitted ones: $(cut -c1-200 "$D/check.out")"
else
  failc "check did not refuse on Clef's settings alone: $(cut -c1-600 "$D/check.out")"
fi
release_wal
# After the admission: check passes and its record is kept (as run.sh keeps admitted.json); the league unit
# (run_league.sh, with a stand-in binary that records any start) starts only while the config and v3.db's settings are
# the admitted ones, and league-add's entry text is the admitted one: a changed config or Clef replaced in the log after
# the admission refuses both.
setup admitted-then-changed
in_case bash "$D/repo/tools/v3/repeats/run.sh" reax-1.3-r1 --prepare-only > "$D/run.out" 2>&1 || failc "prepare: $(cat "$D/run.out")"
crc=$(check_rc reax-1.3-r1)
sed -n 's/^admitted-settings //p' "$D/check.out" > "$D/admitted.json"
R=(python3 "$D/repo/tools/v3/repeats/repeats.py")
printf '#!/usr/bin/env bash\necho "$*" >> %q\n' "$D/started" > "$D/bin/stand-in" && chmod +x "$D/bin/stand-in"
league_unit() { (cd "$D/home" && in_case bash "$D/repo/tools/v3/repeats/run_league.sh" reax-1.3-r1 "$D/bin/stand-in" \
  "$D/home/v3.db" "$D/admitted.json"); }
stored=$(sqlite3 "$D/home/v3.db" "SELECT settings FROM players WHERE name = 'Clef'")
in_case "${R[@]}" bound reax-1.3-r1 "$D/admitted.json" > "$D/bound.out" 2>&1; brc=$?
e=$(in_case "${R[@]}" entry reax-1.3-r1 Clef "$D/admitted.json" 2>"$D/entry.err"); erc=$?
league_unit; lrc=$?
if (( crc == 0 && brc == 0 && erc == 0 && lrc == 0 )) && [[ -s $D/admitted.json && $e == "$stored" ]] &&
   grep -q "^league --config .*/leagues/reax-1.3-r1.json --db $D/home/v3.db$" "$D/started"; then
  pass "as admitted: check exit 0 with its record ($(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["clients"]))' "$D/admitted.json") clients), bound exit 0, entry prints Clef's stored text, the league unit starts the league"
else
  failc "as admitted: check $crc, bound $brc, entry $erc ('$e'), league unit $lrc, started: $(cat "$D/started" 2>/dev/null)"
fi
rm -f "$D/started"
cfg=$D/repo/tools/v3/repeats/leagues/reax-1.3-r1.json
cp "$cfg" "$D/config.kept" && echo >> "$cfg"
in_case "${R[@]}" bound reax-1.3-r1 "$D/admitted.json" > "$D/bound.out" 2>&1; brc=$?
league_unit; lrc=$?
if (( brc == 1 && lrc != 0 )) && [[ ! -e $D/started ]] && grep -q "reax-1.3-r1.json is not the one admitted" "$D/bound.out"; then
  pass "config changed after the admission: bound exit 1, no league started: $(cut -c1-160 "$D/bound.out")"
else
  failc "config changed: bound $brc, league unit $lrc, started: $(cat "$D/started" 2>/dev/null)"
fi
cp "$D/config.kept" "$cfg"
hold_wal "$D/home/v3.db" || failc "the writer did not commit"
before=$(sha256sum < "$D/home/v3.db")
in_case "${R[@]}" bound reax-1.3-r1 "$D/admitted.json" > "$D/bound.out" 2>&1; brc=$?
e=$(in_case "${R[@]}" entry reax-1.3-r1 Clef "$D/admitted.json" 2>"$D/entry.err"); erc=$?
league_unit; lrc=$?
after=$(sha256sum < "$D/home/v3.db")
release_wal
if (( brc == 1 && erc == 1 && lrc != 0 )) && [[ -z $e && ! -e $D/started && $after == "$before" ]] &&
   grep -q "Clef: v3.db's settings now" "$D/bound.out" && grep -q "Clef: v3.db's settings now" "$D/entry.err" &&
   grep -q "refused, not the admitted settings" "$D/home/repeat-reax-1.3-r1.log"; then
  pass "Clef replaced in the log after the admission: bound and entry exit 1 (no entry text), the league unit starts nothing, the database file unchanged: $(cut -c1-200 "$D/bound.out")"
else
  failc "Clef replaced after admission: bound $brc, entry $erc ('$e'), league unit $lrc, started: $(cat "$D/started" 2>/dev/null)"
fi


# A repeat whose held name is not yet in the main checkout's committed held_setups.json (the site branch adding it not
# merged) must refuse on that alone; once it is held, it takes the trigger-missing case below.
held_in_main() {
  git -C /home/cbasaran/code/jevgammon show HEAD:tools/site/content/held_setups.json 2>/dev/null | python3 -c '
import json, sys
name = next(r["name"] for r in json.load(open(sys.argv[2]))["repeats"] if r["id"] == sys.argv[1])
sys.exit(name not in json.load(sys.stdin).get("held", {}))' "$1" "$MAN"
}
prepare=(mammoth-1-r1 drex-max-v1-r1 reax-1.3-r1 d1-ultra-r1)
for rid in drex-max-1.1-r1 glide-v1.2-r1; do
  if held_in_main "$rid"; then prepare+=("$rid"); continue; fi
  setup "not-held-$rid"; refuse "$rid"
  grep -q "not held in the main checkout" "$D/check.out" && pass "the refusal names the missing held name" ||
    failc "check did not name the missing held name: $(cat "$D/check.out")"
done

for rid in "${prepare[@]}"; do
  setup "trigger-missing-$rid"
  before=$(sha256sum < "$D/home/v3.db")
  crc0=$(check_rc "$rid"); out0=$(cat "$D/check.out")
  in_case bash "$D/repo/tools/v3/repeats/run.sh" "$rid" --prepare-only > "$D/run.out" 2>&1
  rc=$?
  after=$(sha256sum < "$D/home/v3.db")
  crc1=$(check_rc "$rid"); out1=$(cat "$D/check.out")
  bak=$(compgen -G "$D/home/v3.db.bak-*-before-$rid.zst")
  in_case bash "$D/repo/tools/v3/repeats/run.sh" "$rid" --prepare-only > "$D/run2.out" 2>&1
  rc2=$?
  again=$(sha256sum < "$D/home/v3.db")
  echo "     check before: exit $crc0: $out0"
  echo "     run.sh: exit $rc; run.log: $(head -2 "$D/home/workspace/repeats/$rid/run.log" 2>/dev/null | tr '\n' ' ' | cut -c1-900)"
  echo "     check after: exit $crc1: $out1"
  bad=()
  (( crc0 == 3 )) || bad+=("check before exit $crc0, not 3")
  (( rc == 0 )) || bad+=("run.sh exit $rc: $(cat "$D/run.out")")
  [[ $after != "$before" ]] || bad+=("trigger not written")
  [[ -n $bak ]] && zstd -q -t "$bak" || bad+=("no verified backup")
  [[ -e $D/home/workspace/repeats/$rid/prepared ]] || bad+=("no prepared marker")
  (( crc1 == 0 )) || bad+=("check after exit $crc1")
  [[ $out1 == *"every client admitted (jevgammon admit)"* ]] || bad+=("check after: no admission")
  (( rc2 == 0 )) && [[ $again == "$after" ]] || bad+=("second run.sh: exit $rc2 or wrote")
  (( $(compgen -G "$D/home/v3.db.bak-*" | wc -l) == 1 )) || bad+=("more than one backup")
  if (( ${#bad[@]} )); then failc "${bad[*]}"; else
    pass "check exit 3, prepared ($(basename "$bak") verified, trigger added), check exit 0 with every client admitted; second run wrote nothing"
  fi
done

C=scratch-ledger
ledger_intact && pass "the scratch Nace ledger is byte-identical (sha256 ${LEDGER_SHA%% *}), no -wal or -shm beside it" ||
  failc "the scratch Nace ledger changed: $(sha256sum < "$LEDGER"); $(ls -la "$S/ledger")"

if (( fails )); then echo "FAILED: $fails case(s)"; else echo "ALL PASSED"; fi
exit $(( fails > 0 ))
