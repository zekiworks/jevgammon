#!/usr/bin/env bash
# Regression tests of run.sh's preflight (Zeki #4737), on scratch copies only: never the production v3.db, the main
# checkout's state or the runner tree. Each case gets its own copy of these scripts and the manifest (repo layout), a
# clone of the runner tree at the recorded commit, a copy of the recorded binary, and a scratch database (the runner's
# own schema, created by the copied binary, plus the originals' and programs' players rows from the manifest and a
# late_entry_stage trigger naming the originals only, so every repeat starts with "trigger missing").
#   Refusals (a held repeat: REAX 1.3 marked held in the case's manifest copy, as before its release; bad pins, other
#   settings, another binary, a changed or missing build input, a changed src, a descendant commit, Drex Max 1.1's and
#   GLiDE v1.2's pins and budget, a repeat name not yet held in main's site): run.sh ID --prepare-only exits non-zero,
#   the scratch database's sha256 is unchanged, no backup,
#   no state or status file; repeats.py check exits 1 (not 3) and repeats.py trigger refuses without a write.
#   Trigger missing only (each repeat not held): check exits 3, run.sh prepares (backup verified by zstd -t, trigger),
#   checks again and exits 0; check then exits 0, and a second run.sh writes nothing more.
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

# Templates: the runner tree as a clone at the commit, the binary, the scratch database.
git clone -q --shared --no-checkout "$RTREE" "$S/tpl/runner" && git -C "$S/tpl/runner" checkout -q --detach "$RCOMMIT" ||
  { echo "cannot clone $RTREE at $RCOMMIT"; exit 1; }
mkdir -p "$S/tpl/bin" && cp "$RBIN" "$S/tpl/bin/jevgammon"
"$S/tpl/bin/jevgammon" void --db "$S/tpl/v3.db" --match 1 --reason schema >/dev/null 2>&1  # opens: creates the schema
python3 - "$S/tpl/v3.db" "$MAN" "$HERE/leagues" <<'EOF' || { echo "fixture failed"; exit 1; }
import json, sqlite3, sys
from pathlib import Path
db, man, leagues = sys.argv[1], json.load(open(sys.argv[2])), Path(sys.argv[3])
conn = sqlite3.connect(db)
if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'players'").fetchone():
    sys.exit("the runner did not create its schema")
rows = {r["original"]: r["settings_original"] for r in man["repeats"]}
for cfg in leagues.glob("*.json"):
    rows |= {p["name"]: p for p in json.loads(cfg.read_text())["players"][1:]}
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
conn.commit()
print(f"scratch database: runner schema, {len(rows)} players rows, late_entry_stage naming {listed}")
EOF

fails=0
pass() { echo "ok   $C: $*"; }
failc() { echo "FAIL $C: $*"; fails=$((fails + 1)); }
# A case's own copies: D/repo (scripts, leagues, manifest pointing at D/runner and D/bin), D/home (state), D/home/v3.db.
setup() {
  C=$1 D=$S/$1
  mkdir -p "$D/repo/tools/v3" "$D/repo/mailbox/repeats" "$D/home"
  cp -r "$HERE" "$D/repo/tools/v3/repeats"
  cp -a "$S/tpl/runner" "$D/runner"
  cp -a "$S/tpl/bin" "$D/bin"
  cp "$S/tpl/v3.db" "$D/home/v3.db"
  python3 - "$MAN" "$D/repo/mailbox/repeats/$(basename "$MAN")" "$D" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1]))
for r in m["repeats"]:
    r["runner"] |= dict(tree=sys.argv[3] + "/runner", binary=sys.argv[3] + "/bin/jevgammon")
open(sys.argv[2], "w").write(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
EOF
}
in_case() { JEVGAMMON_DB=$D/home/v3.db REPEATS_HOME=$D/home "$@"; }
check_rc() { in_case python3 "$D/repo/tools/v3/repeats/repeats.py" check "$1" > "$D/check.out" 2>&1; echo $?; }

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

# The real runner as recorded (tree, binary, inputs; the unmodified manifest) against a scratch database: only the
# trigger is missing (exit 3); nothing is written.
C=recorded-runner D=$S/recorded-runner
mkdir -p "$D" && cp "$S/tpl/v3.db" "$D/v3.db"
before=$(sha256sum < "$D/v3.db")
out=$(JEVGAMMON_DB=$D/v3.db python3 "$HERE/repeats.py" check mammoth-1-r1 2>&1); rc=$?
echo "     check (recorded runner $RTREE, $RBIN): exit $rc: $out"
if (( rc == 3 )) && [[ $(sha256sum < "$D/v3.db") == "$before" ]]; then pass "the recorded runner binds; only the trigger is missing"
else failc "check exit $rc or the database changed"; fi

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
  (( rc2 == 0 )) && [[ $again == "$after" ]] || bad+=("second run.sh: exit $rc2 or wrote")
  (( $(compgen -G "$D/home/v3.db.bak-*" | wc -l) == 1 )) || bad+=("more than one backup")
  if (( ${#bad[@]} )); then failc "${bad[*]}"; else
    pass "check exit 3, prepared ($(basename "$bak") verified, trigger added), check exit 0; second run wrote nothing"
  fi
done

if (( fails )); then echo "FAILED: $fails case(s)"; else echo "ALL PASSED"; fi
exit $(( fails > 0 ))
