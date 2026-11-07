#!/usr/bin/env bash
# leaderboard-ct review 2 (Zeki #2790): everything from RETAINED fixtures, no statistics or model run.
#   - /tmp/lct/S.pkl: build.compute() of 7 Nov 19:18 UTC (compute_retained.py; results 7b40b30e), rendered with the
#     branch HEAD's tools/site by render_retained.py, then checks.run;
#   - /tmp/lct/out-main and /tmp/lct/out-branch: review 1's full renders of origin/main a25b75e and of 5ca56de;
#   - /tmp/lct/live: the live mirror as of 19:35Z (results 7b40b30e).
# Every step's output and exit status go to review2/runs.txt; the script exits 1 if any step that must pass fails.
#   bash mailbox/leaderboard-ct/scripts/run_review2.sh WORKTREE
set -uo pipefail
WT=${1:?leaderboard-ct worktree}
PY=${PY:-$HOME/.pyenv/shims/python3}
R=/home/cbasaran/code/jevgammon
D=$R/mailbox/leaderboard-ct
O=$D/review2
I=/tmp/lct
HASH=7b40b30e
mkdir -p "$O"
rm -rf "$I/src-r2"; mkdir -p "$I/src-r2/tools"
shopt -s dotglob
for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-r2/" ;; esac; done
for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-r2/tools/"; done
shopt -u dotglob
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-r2"
status=0
step() {  # step NAME EXPECTED_EXIT CMD...: run, log, record the exit status against the expected one
  local name=$1 want=$2; shift 2
  echo; echo "## $name"; echo "\$ $*"
  "$@" 2>&1 | grep -v -e RuntimeWarning -e 'np.where'
  local rc=${PIPESTATUS[0]}
  echo "exit status: $rc (expected $want)"
  [ "$rc" -eq "$want" ] || status=1
}
{
  echo "# leaderboard-ct review 2, $(date -u '+%F %T UTC'); branch $(git -C "$WT" rev-parse --short HEAD), retained fixtures"
  rm -rf "$I/out-r2" "$I/out-late2"
  step "render the branch from the retained S, checks.run" 0 \
    bash -c "cd $I/src-r2 && $PY $D/scripts/render_retained.py $I/src-r2 $I/state $I/out-r2 $HASH $I/S.pkl --checks"
  step "late-entry preview render (LATE_ROWS on; screenshots only)" 0 \
    bash -c "cd $I/src-r2 && LATE=1 $PY $D/scripts/render_retained.py $I/src-r2 $I/state $I/out-late2 $HASH $I/S.pkl"
  step "the retained S gives the 5ca56de render's data files, byte for byte (manifest aside; the render time stamp normalised)" 0 \
    $PY -c "
import re, sys
from pathlib import Path
a, b = Path('$I/out-branch/data'), Path('$I/out-r2/data')
stamp = lambda s: re.sub(rb'updated \d+ \w+ \d{4}, \d\d:\d\d UTC', b'updated STAMP', s)
fa = {p.relative_to(a) for p in a.rglob('*') if p.is_file() and p.name != 'manifest.json'}
fb = {p.relative_to(b) for p in b.rglob('*') if p.is_file() and p.name != 'manifest.json'}
diff = sorted(str(p) for p in fa & fb if stamp((a / p).read_bytes()) != stamp((b / p).read_bytes()))
print(f'{len(fa)} / {len(fb)} files; only in one: {sorted(map(str, fa ^ fb))}; differing: {diff}')
sys.exit(0 if fa == fb and not diff else 1)"
  step "selection rule regression tests" 0 \
    bash -c "cd $I/src-r2/tools/site && $PY $D/scripts/test_rules.py . $I/S.pkl"
  step "LATE_ROWS on adds a separate late group and leaves the ranked rows as they are (Astra stays medium)" 0 \
    $PY -c "
import sys
from bs4 import BeautifulSoup
def rows(d):
    t = BeautifulSoup(open(d + '/index.html').read(), 'html.parser').select_one('#headline-table')
    trs = t.tbody.find_all('tr', recursive=False)
    ranked = [(r['data-dataset'], r['data-setup']) for r in trs if r.get('data-setup') and not set(r.get('class') or []) & {'hl-sub', 'reference', 'late'}]
    late = [(r['data-dataset'], r['data-setup']) for r in trs if 'late' in (r.get('class') or []) and 'hl-sub' not in (r.get('class') or [])]
    return ranked, late
a, la = rows('$I/out-r2'); b, lb = rows('$I/out-late2')
print('ranked rows off/on:', len(a), len(b), 'identical:', a == b)
print('GPT-6 Astra ranked row:', [x for x in b if x[1].startswith('gpt-6-astra')])
print('late group off/on:', len(la), len(lb), lb)
sys.exit(0 if a == b and not la and lb else 1)"
  step "evidence: re-derived choice and per-parent families against the branch render" 0 \
    $PY "$D/scripts/evidence.py" "$WT" "$I/out-r2" "$O/evidence" "$I/out-branch"
  step "negative control: the same evidence against the 5ca56de render must fail (no score-free rule text there)" 1 \
    $PY "$D/scripts/evidence.py" "$WT" "$I/out-branch" "$I/evidence-5ca56de"
  step "review: numbers, links, browser tests (file:// and the phase control), screenshots" 0 \
    $PY "$D/scripts/review.py" "$WT" "$I/live" "$I/out-main" "$I/out-r2" "$I/out-late2" "$O" "$O/evidence/expected-families.json"
  step "first screen at #leaderboard, 5ca56de against the branch" 0 \
    $PY "$D/scripts/first_screen.py" "5ca56de=$I/out-branch" "branch=$I/out-r2"
  echo; echo "# overall exit status: $status"
  exit "$status"
} 2>&1 | tee "$O/runs.txt"
exit "${PIPESTATUS[0]}"
