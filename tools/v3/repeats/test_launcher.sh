#!/usr/bin/env bash
# Regression tests of run.sh's preflight (Zeki #4737, #4896), on scratch copies only: never the production v3.db, a
# production budget ledger, the main checkout's state or the runner tree. Each case gets its own copy of these scripts
# and the manifest (repo layout), a clone of the runner tree at the recorded commit, a copy of the recorded binary, and a
# scratch database (the runner's own schema, created by the copied binary, plus the originals' and programs' players
# rows from the manifest, the pinned opponents' rows (name and spec as each original played them; specs from the
# 2026-11-11 admission run, mailbox/pinned-late-review/admission.log) and a late_entry_stage trigger naming the originals
# only, so every repeat starts with "trigger missing"; and REAX 1.3's recorded attempt, league #24, as v3.db holds it).
# Drex Max 1.1's Nace ledger is a scratch ledger (the path replaced in the copies of the manifest, the league configs and
# repeats.py); the keys are a scratch HOME's ~/.keys and Celeris key file with placeholder values (no request is sent).
#   Recorded attempt: league-id skips league #24 (the league unit then starts a new league); a changed #24 refuses.
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
for name, s in rows.items():
    conn.execute("INSERT INTO players (name, spec, settings, created_at) VALUES (?, ?, ?, '2026-11-11T00:00:00Z')",
                 (name, s.get("spec") or "program", json.dumps(s)))
listed = ", ".join("'" + r["original"].replace("'", "''") + "'" for r in man["repeats"])
conn.execute(f"""CREATE TRIGGER late_entry_stage AFTER INSERT ON matches
WHEN EXISTS (SELECT 1 FROM players p WHERE p.id IN (NEW.player1, NEW.player2)
             AND p.name IN ({listed}))
BEGIN
  UPDATE matches SET stage = 'late-entry' WHERE id = NEW.id;
END""")
# REAX 1.3's first attempt as v3.db holds it (repeats.py REAX_ATTEMPT_1): league #24 playing only the repeat name's
# pairs, with its pins, the repeat name and the programs as participants, no match.
sys.path.insert(0, str(leagues.parent))
import repeats
a = repeats.REAX_ATTEMPT_1
cfg = json.loads((leagues / "reax-1.3-r1.json").read_text())
entrant = cfg["players"][0]
conn.execute("INSERT INTO players (name, spec, settings, created_at) VALUES (?, ?, ?, ?)",
             (entrant["name"], entrant["spec"], json.dumps(entrant), a["record"]["started_at"]))
conn.execute("""INSERT INTO leagues (id, started_at, finished_at, seed, rounds, status, heartbeat_at, only_pairs_of,
                                     hidden, pinned_pairs, prompt_version, order_seed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
             (a["league"], a["record"]["started_at"], a["record"]["finished_at"], cfg["seed"], cfg["rounds"],
              a["record"]["status"], a["record"]["heartbeat_at"], entrant["name"], json.dumps(cfg["pinned_pairs"]),
              cfg["prompt_version"], cfg["order_seed"]))
for name in a["record"]["participants"]:
    conn.execute("""INSERT INTO league_players (league_id, player_id, joined_at)
                    SELECT ?, id, ? FROM players WHERE name = ?""", (a["league"], a["record"]["started_at"], name))
conn.commit()
print(f"scratch database: runner schema, {len(rows)} players rows, late_entry_stage naming {listed}, "
      f"attempt league #{a['league']} as recorded")
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
