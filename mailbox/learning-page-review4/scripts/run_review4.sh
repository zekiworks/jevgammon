#!/usr/bin/env bash
# Review 4 of the learning-page candidate (Zeki #2676 fixes), every output teed into mailbox/learning-page-review4/.
# Render-only: no build.py/update.sh, no server, no timer, no deploy; the live state is only read (review 3's copy in
# $I/state is reused, with review 3's main render $I/out-main and results hash, so 04 compares like with like).
# tools/site must be committed (the renders use HEAD). From the learning-page worktree:
#   PATH=/usr/bin:$PATH bash mailbox/learning-page-review4/scripts/run_review4.sh
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
git -C "$WT" diff --quiet HEAD -- tools/site || { echo "tools/site has uncommitted changes"; exit 2; }
R=/home/cbasaran/code/jevgammon
D=$WT/mailbox/learning-page-review4
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/inv}
SITE=$I/out-branch                      # links resolve against the branch's own whole-site render
TS=$R/workspace/learning-pilot/test_set.json
HASH=$(grep -o 'results hash fixed: [0-9a-f]*' "$WT/mailbox/learning-page-review3/01-full-checks-run.txt" | cut -d' ' -f4)
TOOLS=$WT/tools/site
HEAD_SHORT=$(git -C "$WT" rev-parse --short HEAD)
stamp() { date -u '+%F %T UTC'; }

# Fixtures (SYNTHETIC; real aggregate format) and the refused-file state.
python3 "$S/make_fixture.py" "$TOOLS" "$I/state-dry/learning" "$I/fix-complete" "$I/fix-running" "$TS"
rm -rf "$I/fix-rejected" && cp -r "$I/fix-complete" "$I/fix-rejected"
python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["verdict"]="learns"; json.dump(d, open(p, "w"))' \
  "$I/fix-rejected/learning-pilot.json"

# (a) The branch's whole-site render (pre-registration-only, the default build) with the full checks.run.
{
  echo "# (a) branch $HEAD_SHORT whole-site render, default build (PREREGISTRATION_ONLY on), checks.run. Started $(stamp)"
  rm -rf "$I/src-branch/tools/site" "$I/out-branch"
  git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-branch"
  (cd "$I/src-branch" && nice python3 "$S/render_site.py" "$I/src-branch" "$I/state" "$I/out-branch" "$HASH" --checks 2>&1 \
    | grep -v -e RuntimeWarning -e 'np.where')
  echo "# Finished $(stamp)"
} 2>&1 | tee "$D/01-branch-checks-run.txt"

# (b) The learning page alone: the default build, then (--with-results, review only) five states.
{
  echo "# (b) learning_page.py --check, at $HEAD_SHORT. Started $(stamp)"
  for c in preregistration-default:$I/fix-complete: none:$I/state-none/learning:--with-results \
           dry-running:$I/state-dry/learning:--with-results synthetic-running:$I/fix-running:--with-results \
           synthetic-complete:$I/fix-complete:--with-results synthetic-rejected:$I/fix-rejected:--with-results; do
    IFS=: read -r n src flag <<<"$c"
    echo; echo "## $n: python3 tools/site/learning_page.py --out $I/page-$n --src $src --check $SITE --test-set <test_set.json> $flag"
    rm -rf "$I/page-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "$I/page-$n" --src "$src" --check "$SITE" --test-set "$TS" $flag 2>&1)
    python3 -c 'import json,sys; L=json.load(open(sys.argv[1])); r=L["results"]; print("preregistration_only:", L["preregistration_only"], "| validation:", L["validation"]); print("results:", None if r is None else {k: r.get(k) for k in ("complete","series_total_done","series_total_planned")}, "| lift/signal in data:", sorted(k for k in ("learning_lift","signal","paired_series") if k in (r or {})), "| lessons:", len(L["lessons"]), "| budget series:", len(L["budget"]))' "$I/page-$n/data/v3/learning-pilot.json"
    echo "complete-only blocks in page: $(grep -o 'id="learning-\(lift\|signal\|leaders\)"' "$I/page-$n/learning/index.html" | tr '\n' ' ')"
    echo "top label: $(grep -o '<p class="eyebrow">[^<]*' "$I/page-$n/learning/index.html" | sed 's/.*>//') | heading: $(grep -o '<h1>[^<]*' "$I/page-$n/learning/index.html" | sed 's/<h1>//')"
  done
  echo; echo "## the default build reads no results: files opened under the source or the test set while building"
  (cd "$TOOLS" && python3 -c '
import sys
from pathlib import Path
opened = []
sys.addaudithook(lambda e, a: opened.append(str(a[0])) if e == "open" else None)
import learning_page as LP
LP.data(LP.PLAN, Path(sys.argv[1]), Path(sys.argv[2]))
print([o.replace(sys.argv[1], "<src>") for o in opened if o.startswith(sys.argv[1]) or o == sys.argv[2]])' "$I/fix-complete" "$TS")
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (c) Page faults, the saved regression cases (Zeki's included), Zeki's synthetic_checks.py.
{
  echo "# (c1) injected page faults, at $HEAD_SHORT. Started $(stamp)"
  python3 "$S/injected_faults.py" "$TOOLS" "$I/page-synthetic-running" "$SITE" "$TS" 2>&1
  echo; echo "# (c2) saved regression cases (regression_cases.py). $(stamp)"
  python3 "$S/regression_cases.py" "$TOOLS" "$I/fix-complete" "$I/fix-running" "$TS" 2>&1
  Z=/home/cbasaran/.agent-bus/received/jevgammon/f_7f2d02645d854171985de0ea21a21889-synthetic_checks.py
  echo; echo "# (c3) Zeki's synthetic_checks.py (sha256 $(sha256sum "$Z" | cut -c1-64)) on $HEAD_SHORT:tools/site. $(stamp)"
  rm -rf "$I/zeki" && mkdir -p "$I/zeki" && cp "$Z" "$I/zeki/synthetic_checks.py"
  git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/zeki"
  (cd "$I/zeki" && python3 synthetic_checks.py 2>&1); echo "exit code: $?"
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-faults-and-regressions.txt"

# (d) File-level invariance inventory: review 3's main render against this branch render.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt"
