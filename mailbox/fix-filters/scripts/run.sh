#!/usr/bin/env bash
# fix-filters checks (Main, after Zeki #2790): origin/main and fix-filters rendered from the same RETAINED computed
# state (/tmp/lct/S.pkl, build.compute() of 7 Nov 19:18 UTC; no statistics or model run), checks.run on both, every
# output file compared byte for byte, then the filter-row browser test. Output and exit statuses: ../runs.txt.
#   bash mailbox/fix-filters/scripts/run.sh FIX_WORKTREE
set -uo pipefail
WT=${1:?fix-filters worktree}
PY=${PY:-$HOME/.pyenv/shims/python3}
R=/home/cbasaran/code/jevgammon
D=$R/mailbox/fix-filters
I=/tmp/lct
HASH=7b40b30e
status=0
step() {
  local name=$1 want=$2; shift 2
  echo; echo "## $name"; echo "\$ $*"
  "$@" 2>&1 | grep -v -e RuntimeWarning -e 'np.where'
  local rc=${PIPESTATUS[0]}
  echo "exit status: $rc (expected $want)"
  [ "$rc" -eq "$want" ] || status=1
}
for v in main ff; do
  rm -rf "$I/src-$v-r"; mkdir -p "$I/src-$v-r/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$v-r/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$v-r/tools/"; done
  shopt -u dotglob
done
git -C "$R" archive --prefix=tools/site/ origin/main:tools/site | tar -x -C "$I/src-main-r"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-ff-r"
{
  echo "# fix-filters, $(date -u '+%F %T UTC'); origin/main $(git -C "$R" rev-parse --short origin/main), fix-filters $(git -C "$WT" rev-parse --short HEAD)"
  for v in main ff; do
    rm -rf "$I/out-$v-r"
    step "render $v from the retained S, checks.run" 0 \
      bash -c "cd $I/src-$v-r && $PY $D/scripts/render_retained.py $I/src-$v-r $I/state $I/out-$v-r $HASH $I/S.pkl --checks"
  done
  step "every rendered file byte for byte, origin/main against fix-filters (only bg.css may differ)" 0 \
    bash -c "d=\$(diff -rq $I/out-main-r $I/out-ff-r); echo \"\$d\"; [ \"\$d\" = \"Files $I/out-main-r/bg.css and $I/out-ff-r/bg.css differ\" ]"
  step "the CSS change" 0 bash -c "diff $I/out-main-r/bg.css $I/out-ff-r/bg.css; true"
  step "filter row in the browser (file://; the phase's effect over routed http), before and after" 0 \
    $PY "$D/scripts/test_filters.py" "$I/out-main-r" "$I/out-ff-r" "$D"
  echo; echo "# overall exit status: $status"
  exit "$status"
} 2>&1 | tee "$D/runs.txt"
exit "${PIPESTATUS[0]}"
