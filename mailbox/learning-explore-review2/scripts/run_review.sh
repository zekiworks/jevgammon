#!/usr/bin/env bash
# The learning-explore review 2 (Zeki #2991/#2993 on bbcd644), every output teed into mailbox/learning-explore-review2/.
# Render-only: no build.py/update.sh, no server, no timer, no deploy, no model call; the pilot's files, the exploratory
# file and the site state are only read (copies under $I). tools/site must be committed (renders use HEAD). From the
# worktree:   PATH=/usr/bin:$PATH bash mailbox/learning-explore-review2/scripts/run_review.sh
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
git -C "$WT" diff --quiet HEAD -- tools/site || { echo "tools/site has uncommitted changes"; exit 2; }
R=/home/cbasaran/code/jevgammon
D=$WT/mailbox/learning-explore-review2
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/inv6}
BASE_STATE=/tmp/inv/state             # review 3's copy of the site state (read only), as in reviews 4 and 5
HASH=1279974c                         # results hash fixed, so the two renders compare file by file
TS=$R/workspace/learning-pilot/test_set.json
TOOLS=$WT/tools/site
HEAD_SHORT=$(git -C "$WT" rev-parse --short HEAD)
MAIN_SHORT=$(git -C "$WT" rev-parse --short origin/main)
stamp() { date -u '+%F %T UTC'; }
mirror() {  # a read-only mirror of the main checkout (symlinks) whose tools/site is $2's
  rm -rf "$1" && mkdir -p "$1/tools"
  for e in "$R"/* "$R"/.[!.]*; do [ "$(basename "$e")" = tools ] || ln -s "$e" "$1/"; done
  for e in "$R"/tools/*; do [ "$(basename "$e")" = site ] || ln -s "$e" "$1/tools/"; done
  git -C "$WT" archive --prefix=tools/site/ "$2:tools/site" | tar -x -C "$1"
}
mkdir -p "$I"

# States: the REAL pilot without and with the REAL exploratory file, a SYNTHETIC malformed exploratory file (made with
# the branch's snapshot.snapshot_learning), and review 5's SYNTHETIC running subset (for the running-state faults).
{
  echo "# (00) states. $(stamp)"
  python3 "$S/make_states.py" "$TOOLS" "$R" "$I/states"
  python3 "$S/make_review5_states.py" "$TOOLS" "$R/workspace/learning-pilot" "$TS" "$I/states5" | grep -e "^real" -e "^SYNTHETIC-running"
  # The production-mode site state: review 3's state (hard links) with STATE/learning = the explore state.
  rm -rf "$I/state" && cp -al "$BASE_STATE" "$I/state" && rm -rf "$I/state/learning" \
    && cp -r "$I/states/explore/learning" "$I/state/learning" && echo "site state: $BASE_STATE with learning = explore"
} 2>&1 | sed "s#$I#\$SCRATCH#g" | tee "$D/00-states.txt"

# (a) Whole-site renders in production mode (PREREGISTRATION_ONLY = False on both sides), same state and results hash;
# checks.run on the branch's.
{
  echo "# (a) whole-site renders, production mode. origin/main $MAIN_SHORT and branch $HEAD_SHORT. Started $(stamp)"
  for side in main:origin/main branch:HEAD; do
    IFS=: read -r n ref <<<"$side"
    mirror "$I/src-$n" "$ref"
    grep -h "^PREREGISTRATION_ONLY" "$I/src-$n/tools/site/learning_page.py" | sed "s/^/$n: /"
    rm -rf "$I/out-$n"
    flag=""; [ "$n" = branch ] && flag=--checks
    (cd "$I/src-$n" && nice python3 "$S/render_site.py" "$I/src-$n" "$I/state" "$I/out-$n" "$HASH" $flag 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where' -e 'learning_validate.*(private)')
  done
  echo "# Finished $(stamp)"
} 2>&1 | sed "s#$I#\$SCRATCH#g" | tee "$D/01-site-renders-and-checks-run.txt"

# (b) The learning page alone, learning_page.py --check (production mode: no review flag), in every state.
{
  echo "# (b) learning_page.py --check at $HEAD_SHORT (links against the branch's whole-site render). Started $(stamp)"
  for c in no-explore:states/no-explore explore:states/explore malformed-explore:states/malformed-explore \
           SYNTHETIC-running:states5/SYNTHETIC-running; do
    IFS=: read -r n st <<<"$c"
    echo; echo "## $n: python3 tools/site/learning_page.py --out \$SCRATCH/page-$n --src \$SCRATCH/$st/learning --check \$SCRATCH/out-branch --test-set <test_set.json>"
    rm -rf "$I/page-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "$I/page-$n" --src "$I/$st/learning" \
      --check "$I/out-branch" --test-set "$TS" 2>&1 | sed "s#$I#\$SCRATCH#g")
    python3 - "$I/page-$n" <<'EOF'
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1])
L = json.loads((out / "data/v3/learning-pilot.json").read_text())
page = (out / "learning/index.html").read_text()
r, X = L["results"], L.get("explore")
print("preregistration_only:", L["preregistration_only"], "| validation:",
      None if L["validation"] is None else {k: L["validation"][k] for k in ("accepted", "complete")})
print("status line:", L["status"]["line"], "| top line:", bool(re.search(r'id="learning-run-line"', page)))
print("chart titles:", re.findall(r'class="lp-title">([^<]*)', page))
print("legend:", sorted(set(re.findall(r'lp-swatch[^>]*></i>([^<]*)', page))))
print("explore in data:", None if X is None else {k: (v if k in ("accepted", "problems") else "...") for k, v in X.items()})
print("explore block:", bool(re.search(r'id="learning-explore"', page)),
      "| after the verdict:", page.find('id="learning-explore"') > page.find('id="learning-verdict-section"'),
      "| explore cells:", len(re.findall(r'<td class="num" data-(?:arm="[a-z]+" data-cp|run|group)=', page)))
EOF
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (c) The exploratory validator's regression tests, before (origin/main: no exploratory validation) and after.
{
  echo "# (c0) explore_regressions.py on origin/main $MAIN_SHORT (before) and on $HEAD_SHORT (after). Started $(stamp)"
  mirror "$I/src-before" origin/main
  echo; echo "## before: origin/main $MAIN_SHORT:tools/site (expected: every fault case FAILs; the 2 control cases"
  echo "## differ: the real file is not shown before, so 'accepted' FAILs; 'no exploratory file' PASSes)"
  python3 "$S/explore_regressions.py" "$I/src-before/tools/site" "$I/states/explore/learning" \
    "$I/states/no-explore/learning" "$TS" 2>/dev/null | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "## before Zeki #2991's fixes: bbcd644:tools/site (the previous candidate). The regenerated file's 4th"
  echo "## spread group is unknown to it, so it refuses every file as schema: the controls and the two retests-spread"
  echo "## cases FAIL (no 'spread' code), as expected"
  mirror "$I/src-bbcd644" bbcd644
  python3 "$S/explore_regressions.py" "$I/src-bbcd644/tools/site" "$I/states/explore/learning" \
    "$I/states/no-explore/learning" "$TS" 2>/dev/null | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "## after: $HEAD_SHORT:tools/site (expected: every case PASSes)"
  python3 "$S/explore_regressions.py" "$TOOLS" "$I/states/explore/learning" "$I/states/no-explore/learning" "$TS" \
    2>/dev/null | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03a-explore-validator-regressions.txt"

{
  echo "# (c1) injected faults (injected_faults.py) at $HEAD_SHORT. Started $(stamp)"
  python3 "$S/injected_faults.py" "$TOOLS" "$I/page-SYNTHETIC-running" "$I/page-explore" "$I/page-malformed-explore" \
    "$I/out-branch" "$TS" 2>&1 | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "# (c2) review 4/5's saved regression cases (regression_cases.py) on the REAL state and the SYNTHETIC running subset. $(stamp)"
  python3 "$S/regression_cases.py" "$TOOLS" "$I/states5/real/learning" "$I/states5/SYNTHETIC-running/learning" "$TS" \
    2>/dev/null | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-faults.txt"

# (d) File-level invariance inventory: origin/main's production-mode render against the branch's.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt" \
  | sed "s#$I#\$SCRATCH#g"

# (e) The source delta (narrow, vs bbcd644; and whole, vs origin/main) and the public projection: the aggregate-only
# exploratory input, the page's data file and the page as rendered from the explore state (no question, board or
# answer is in any of them: the scan below uses checks._test_set_strings over every packet file).
mkdir -p "$D/source" "$D/public"
git -C "$WT" diff bbcd644 HEAD -- tools/site > "$D/source/delta-vs-bbcd644.patch"
git -C "$WT" diff origin/main HEAD -- tools/site > "$D/source/delta-vs-origin-main.patch"
git -C "$WT" diff --stat bbcd644 HEAD -- tools/site > "$D/source/delta-vs-bbcd644.stat"
cp "$I/states/explore/learning/explore/explore.json" "$D/public/explore.json"
cp "$I/page-explore/data/v3/learning-pilot.json" "$D/public/learning-pilot.json"
cp "$I/page-explore/learning/index.html" "$D/public/learning-index.html"
{
  echo "# (e) packet scan for evaluation-set strings (ids, board keys, boards). $(stamp)"
  (cd "$TOOLS" && python3 -c '
import sys, checks
from pathlib import Path
S = checks._test_set_strings(Path(sys.argv[1]))
files = [p for p in Path(sys.argv[2]).rglob("*") if p.is_file() and p.suffix != ".png"]
hits = [str(p) for p in files for s in S if s in p.read_text(errors="ignore")]
print(f"{len(S)} strings, {len(files)} files, hits: {len(hits)}")
sys.exit(1 if hits else 0)' "$TS" "$D"); echo "exit code: $?"
  sha256sum "$D/public/"* "$D/source/"* | sed "s#$D/##"
} 2>&1 | tee "$D/06-public-projection-and-scan.txt"
