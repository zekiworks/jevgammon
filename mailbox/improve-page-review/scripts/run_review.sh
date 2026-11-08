#!/usr/bin/env bash
# Review of the "Did they improve?" page candidate (branch improve-page), every output teed into
# mailbox/improve-page-review/. Render-only: no build.py/update.sh, no server, timer, deploy or model call; the site
# state and the private files are only read (copies/links under $I). tools/site must be committed (renders use HEAD).
#   bash mailbox/improve-page-review/scripts/run_review.sh      (from the main checkout)
set -uo pipefail
R=/home/cbasaran/code/jevgammon                    # main checkout: untracked v3.db, workspace/, replay.db, ...
WT=/home/cbasaran/code/jevgammon-improve-page      # the candidate's worktree
D=$R/mailbox/improve-page-review
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/imp-review}
STATE0=/tmp/inv/state                              # the learning-page reviews' copy of the site state (read-only)
HASH=1279974c                                      # results hash fixed, so main's and the branch's renders compare
TS=$R/workspace/learning-pilot/test_set.json
PY=/usr/bin/python3                                # numpy; the screenshots use ~/.pyenv's (playwright)
git -C "$WT" diff --quiet HEAD -- tools/site || { echo "tools/site has uncommitted changes"; exit 2; }
HEAD_SHORT=$(git -C "$WT" rev-parse --short HEAD)
MAIN_SHORT=$(git -C "$WT" rev-parse --short origin/main)
stamp() { date -u '+%F %T UTC'; }
mkdir -p "$I"

# The state: the old copy's entries linked, plus STATE/improve as snapshot.py writes it (no improve.json yet: the
# harness has not written one; prompt/ is the plan's lesson prompt).
rm -rf "$I/state" && mkdir -p "$I/state"
for e in "$STATE0"/*; do ln -s "$e" "$I/state/"; done
(cd "$WT" && $PY -c 'import sys; sys.path.insert(0, "tools/site"); import snapshot; print("snapshot_improve key:", snapshot.snapshot_improve(sys.argv[1], sys.argv[2]))' "$R" "$I/state") \
  | tee "$D/00-states.txt"
echo "STATE/improve: $(cd "$I/state/improve" && find . -type f | sort | tr '\n' ' ')" | tee -a "$D/00-states.txt"

# A read-only mirror of the repository per side: tracked entries from the worktree (the committed plan), untracked
# ones (v3.db, workspace/, replay.db, ...) from the main checkout, tools/site from git archive of the side's ref.
mirror() {  # name ref
  local M=$I/src-$1
  rm -rf "$M" && mkdir -p "$M/tools"
  for e in "$R"/* "$R"/.[!.]*; do
    b=$(basename "$e"); [ "$b" = tools ] && continue
    if [ -e "$WT/$b" ]; then ln -s "$WT/$b" "$M/"; else ln -s "$e" "$M/"; fi
  done
  for e in "$WT"/tools/*; do [ "$(basename "$e")" = site ] || ln -s "$e" "$M/tools/"; done
  git -C "$WT" archive --prefix=tools/site/ "$2:tools/site" | tar -x -C "$M"
}

{
  echo "# (a) whole-site renders: origin/main $MAIN_SHORT and branch improve-page $HEAD_SHORT, same state, results hash"
  echo "# $HASH; checks.run (the full pre-deploy checks) on the branch's. Started $(stamp)"
  for side in main:origin/main branch:HEAD; do
    IFS=: read -r n ref <<<"$side"
    mirror "$n" "$ref"
    flag=""; [ "$n" = branch ] && flag=--checks
    (cd "$I/src-$n" && nice $PY "$S/render_site.py" "$I/src-$n" "$I/state" "$I/out-$n" "$HASH" $flag 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where' | sed "s#$I#\$SCRATCH#g")
  done
  echo; echo "## files that differ between the two renders (diff -rq; added files listed)"
  (cd "$I" && diff -rq out-main out-branch | sed "s#$I#\$SCRATCH#g")
  echo "# Finished $(stamp)"
} 2>&1 | tee "$D/01-site-renders-and-checks-run.txt"

{
  echo "# (b) selftest_improve.py at $HEAD_SHORT: SYNTHETIC states rendered with the results view, injected faults in"
  echo "# improve.json (refused) and in the rendered page (detected). Started $(stamp)"
  (cd "$I/src-branch" && $PY tools/site/selftest_improve.py --keep "$I/self" --workspace "$R/workspace" 2>"$I/self-stderr.txt" \
    | sed "s#$I#\$SCRATCH#g"); echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "## stderr: the private problem texts (names from the file in full; never on the page): first 12 lines"
  sed "s#$I#\$SCRATCH#g" "$I/self-stderr.txt" | head -12
  echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-selftest-faults.txt"

{
  echo "# (c) improve_page.py --check (numbers trace, links and ids against the branch's whole-site render, private-"
  echo "# strings scan, check_improve incl. the test-position leak scan) in every state, at $HEAD_SHORT. Started $(stamp)"
  # REAL dry-run: the harness's own dry-run file (branch improve, workspace/improve/out-dry: protocol.dry_run true,
  # placeholder lessons, no model call), in STATE/improve's layout; as written (made under an earlier plan hash) and
  # with protocol.plan_sha256 set to the current plan's (the only change).
  for v in asis rehashed; do
    rm -rf "$I/dry-$v" && mkdir -p "$I/dry-$v/improve/prompt" "$I/dry-$v/improve/harness-prompt"
    cp "$R"/workspace/learning-pilot/lessons_{system,user}.txt "$I/dry-$v/improve/prompt/"
    cp "$R"/workspace/improve/out-dry/prompt/lessons_{system,user}.txt "$I/dry-$v/improve/harness-prompt/"
    cp "$R/workspace/improve/out-dry/improve.json" "$I/dry-$v/improve/"
  done
  $PY - "$I/dry-rehashed/improve/improve.json" "$WT/mailbox/Did they improve - plan 2026-11-08.md" <<'EOF2'
import hashlib, json, sys
from pathlib import Path
p = Path(sys.argv[1]); d = json.loads(p.read_text())
print("REAL dry-run: plan_sha256 as written", d["protocol"]["plan_sha256"][:12], "-> current plan",
      hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()[:12])
d["protocol"]["plan_sha256"] = hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()
p.write_text(json.dumps(d))
EOF2
  for st in default-preregistration none running-1 complete-yes complete-no mixed refused REAL-dry-run-asis \
            REAL-dry-run-rehashed; do
    flag=--with-results; src=$I/self/states/$st/improve
    [ "$st" = default-preregistration ] && { flag=""; src=$I/state/improve; }
    [ "$st" = REAL-dry-run-asis ] && src=$I/dry-asis/improve
    [ "$st" = REAL-dry-run-rehashed ] && src=$I/dry-rehashed/improve
    if [ "$st" = refused ]; then  # one injected fault: a test position's board in a lesson
      rm -rf "$I/refused" && cp -r "$I/self/states/complete-yes" "$I/refused" && src=$I/refused/improve
      $PY - "$src/improve.json" "$TS" "$I/src-branch/tools/site" <<'EOF'
import json, sys
sys.path.insert(0, sys.argv[3])
import checks
from pathlib import Path
p = Path(sys.argv[1]); d = json.loads(p.read_text())
d["models"][0]["series"][0]["lessons"][2]["text"] = "- " + checks._test_set_strings(Path(sys.argv[2]))[2]
p.write_text(json.dumps(d))
EOF
    fi
    echo; echo "## $st: improve_page.py --out \$SCRATCH/page-$st --src <$st> --check \$SCRATCH/out-branch $flag"
    rm -rf "$I/page-$st"
    (cd "$I/src-branch" && $PY tools/site/improve_page.py --out "$I/page-$st" --src "$src" --check "$I/out-branch" \
      --test-set "$TS" $flag 2>&1 | grep -v "^improve_validate (private)" | sed "s#$I#\$SCRATCH#g")
    $PY - "$I/page-$st" <<'EOF'
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1])
L = json.loads((out / "data/v3/improve.json").read_text())
page = (out / "improve/index.html").read_text()
print("preregistration_only:", L["preregistration_only"], "| validation:", L["validation"] and
      {"accepted": L["validation"]["accepted"], "problems": len(L["validation"]["problems"])})
print("top label:", re.search(r'<p class="eyebrow">([^<]*)', page).group(1), "| heading:",
      re.search(r"<h1>([^<]*)", page).group(1), "| status line:", (L.get("status") or {}).get("line"))
print("rows (in page order):", [(s, v) for s, v in re.findall(
    r'<tr data-setup="([^"]*)".*?(?:data-verdict="([a-z]+)"|</tr>)', page, flags=re.S)][:6])
print("models with data:", [(m["setup"], m["status"]) for m in (L["results"] or {}).get("models", [])])
print("refused note:", 'id="improve-refused"' in page, "| lessons block:", 'id="improve-lessons"' in page)
EOF
  done
  echo; echo "## the default build reads no improve.json: files opened under the state or the test set while building"
  (cd "$I/src-branch/tools/site" && $PY -c '
import sys
from pathlib import Path
opened = []
sys.addaudithook(lambda e, a: opened.append(str(a[0])) if e == "open" else None)
import improve_page as IP
IP.data(IP.PLAN, Path(sys.argv[1]), Path(sys.argv[2]))
print(sorted(set(o.replace(sys.argv[1], "<src>") for o in opened if o.startswith(sys.argv[1]) or o == sys.argv[2])))' \
    "$I/self/states/complete-yes/improve" "$TS")
  echo; echo "## leak scan of the whole built site (branch): every test position (id, board key, board) in every file"
  $PY - "$I/out-branch" "$TS" "$I/src-branch/tools/site" <<'EOF'
import gzip, html, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import checks
strings = checks._test_set_strings(Path(sys.argv[2]))
pats = [re.compile(r"(?<![\w-])" + re.escape(s) + r"(?!\w)") for s in strings]
files = hits = 0
for p in Path(sys.argv[1]).rglob("*"):
    if not p.is_file() or p.suffix == ".png":
        continue
    b = p.read_bytes()
    t = html.unescape((gzip.decompress(b) if p.suffix == ".gz" else b).decode("utf-8", "replace"))
    files += 1
    for s, pat in zip(strings, pats):
        if s in t and pat.search(t):  # plain substring first (fast); the bounded match only on a hit
            hits += 1
            print("HIT", p, s[:30])
print(f"{len(strings)} strings (200 positions x id, board key, board) over {files} files: {hits} hit(s)")
EOF
  echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (d) Screenshots: 1280 and 375 wide, light, each state (screenshots.py).
~/.pyenv/shims/python3 "$S/screenshots.py" "$I" 2>&1 | tee "$D/05-screenshots-log.txt"
