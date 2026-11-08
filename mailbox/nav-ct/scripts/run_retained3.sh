#!/usr/bin/env bash
# review3 renders (Ümit #2921): NO compute. Both 90cd56e and nav-ct's HEAD are rendered from the RETAINED computed state
# /tmp/lct/S.pkl (build.compute() of the copy of the live state, results 7b40b30e, made once on 7 Nov for leaderboard-ct
# review2; not re-run) with render_retained.py, each followed by checks.run. The learning page's data is a file read.
#   bash run_retained.sh NAV_WORKTREE
set -uo pipefail
WT=${1:?worktree}; PY=${PY:-$HOME/.pyenv/shims/python3}; R=/home/cbasaran/code/jevgammon; D=$R/mailbox/nav-ct; I=/tmp/nav
status=0
for v in 90cd56e HEAD; do
  n=$([ "$v" = HEAD ] && echo r3-head || echo r3-90cd56e)
  rm -rf "$I/src-$n"; mkdir -p "$I/src-$n/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$n/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$n/tools/"; done
  shopt -u dotglob
  git -C "$WT" archive --prefix=tools/site/ "$v:tools/site" | tar -x -C "$I/src-$n"
  echo "## $v ($(git -C "$WT" rev-parse --short "$v")): render_retained.py from /tmp/lct/S.pkl --checks"
  rm -rf "$I/out-$n"
  (cd "$I/src-$n" && $PY "$D/scripts/render_retained.py" "$I/src-$n" /tmp/lct/state "$I/out-$n" 7b40b30e /tmp/lct/S.pkl --checks 2>&1 \
    | grep -v -e RuntimeWarning -e 'np.where'; exit "${PIPESTATUS[0]}")
  rc=$?; echo "exit status: $rc"; [ "$rc" -eq 0 ] || status=1
done
echo "# overall exit status: $status"; exit $status
