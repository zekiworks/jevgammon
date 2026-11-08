#!/usr/bin/env bash
# ct-brief renders (Ümit #2938): NO compute. origin/main and the ct-brief tree are rendered from the RETAINED computed
# state /tmp/lct/S.pkl (build.compute() of the copy of the live state, results 7b40b30e, 7 Nov; not re-run) with
# render_retained.py. The learning page's data is a file read (learning_page.from_state) from /tmp/ctb/state/learning,
# a copy of the live state's learning directory (8 Nov). Results hash a8708ed6 (the live manifest's), so labels compare.
#   bash run_retained.sh WORKTREE [REF...]     (default refs: origin/main HEAD)
set -uo pipefail
WT=${1:?worktree}; shift; REFS=${*:-origin/main HEAD}
export AS_OF=2026-11-08T08:20Z
PY=${PY:-$HOME/.pyenv/shims/python3}; R=/home/cbasaran/code/jevgammon; D=$R/mailbox/ct-brief; I=/tmp/ctb
status=0
for v in $REFS; do
  n=$(case $v in HEAD) echo head;; WORK) echo work;; *) echo base;; esac)
  rm -rf "$I/src-$n"; mkdir -p "$I/src-$n/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$n/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$n/tools/"; done
  shopt -u dotglob
  if [ "$v" = WORK ]; then cp -r "$WT/tools/site" "$I/src-$n/tools/site"   # the uncommitted tree (development only)
  else git -C "$WT" archive --prefix=tools/site/ "$v:tools/site" | tar -x -C "$I/src-$n"; fi
  echo "## $v ($(git -C "$WT" rev-parse --short "${v/WORK/HEAD}")): render_retained.py from /tmp/lct/S.pkl --checks"
  rm -rf "$I/out-$n"
  (cd "$I/src-$n" && $PY "$D/scripts/render_retained.py" "$I/src-$n" "$I/state" "$I/out-$n" a8708ed6 /tmp/lct/S.pkl --checks 2>&1 \
    | grep -v -e RuntimeWarning -e 'np.where'; exit "${PIPESTATUS[0]}")
  rc=$?; echo "exit status: $rc"; [ "$rc" -eq 0 ] || status=1
done
echo "# overall exit status: $status"; exit $status
