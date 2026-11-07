#!/usr/bin/env bash
# Review 3, partial rerun after the top-label fix: 02 (page checks, 4 states) and 04 (invariance) only, reusing
# run_review.sh's scratch ($I: state copy, fixtures, out-main). The branch render is redone from HEAD's tools/site
# (no checks.run: 01 is not rerun). Render-only, as run_review.sh. Run from the learning-page worktree:
#   PATH=/usr/bin:$PATH bash mailbox/learning-page-review3/scripts/rerun_02_04.sh
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
R=/home/cbasaran/code/jevgammon
D=$WT/mailbox/learning-page-review3
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/inv}
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon
TS=$R/workspace/learning-pilot/test_set.json
# The results hash of 01's renders (out-main and the state copy are 01's), not the live one, which moves on republish.
HASH=$(grep -o 'results hash fixed: [0-9a-f]*' "$D/01-full-checks-run.txt" | cut -d' ' -f4)
stamp() { date -u '+%F %T UTC'; }

rm -rf "$I/src-branch/tools/site"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-branch"
rm -rf "$I/out-branch"
(cd "$I/src-branch" && nice python3 "$S/render_site.py" "$I/src-branch" "$I/state" "$I/out-branch" "$HASH" 2>&1 \
  | grep -v -e RuntimeWarning -e 'np.where')

# (b) as in run_review.sh.
{
  echo "# (b) learning_page.py --check in four states, at $(git -C "$WT" rev-parse --short HEAD). Started $(stamp)"
  for c in none:$I/state-none/learning dry-running:$I/state-dry/learning synthetic-running:$I/fix-running synthetic-complete:$I/fix-complete; do
    n=${c%%:*}; src=${c#*:}
    echo; echo "## $n: python3 tools/site/learning_page.py --out $I/page-$n --src $src --check $SITE --test-set <test_set.json>"
    rm -rf "$I/page-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "$I/page-$n" --src "$src" --check "$SITE" --test-set "$TS" 2>&1)
    python3 -c 'import json,sys; L=json.load(open(sys.argv[1])); r=L["results"]; print("validation:", L["validation"]); print("results:", None if r is None else {k: r.get(k) for k in ("complete","series_total_done","series_total_planned")}, "| lift/signal in data:", sorted(k for k in ("learning_lift","signal","paired_series") if k in (r or {})))' "$I/page-$n/data/v3/learning-pilot.json"
    echo "complete-only blocks in page: $(grep -o 'id="learning-\(lift\|signal\|leaders\)"' "$I/page-$n/learning/index.html" | tr '\n' ' ')"
    echo "top label: $(grep -o '<p class="eyebrow">[^<]*' "$I/page-$n/learning/index.html" | sed 's/.*>//')"
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (d) as in run_review.sh.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt"
