#!/usr/bin/env bash
# leaderboard-ct review renders (Ümit #2745): the whole site rendered twice from one copy of the live state, with
# tools/site of origin/main and of the leaderboard-ct worktree's HEAD, each followed by checks.run (the full pre-deploy
# checks). Render-only: no build.py main, no update.sh, no server, no deploy; the live state is only read (copied).
# render_site.py (from mailbox/front-story) runs build.compute(), which reads the published aggregates and runs the
# site's offline computations, the bootstrap loops of offline.py included: not statistics-free, but no model call,
# no scorer, no rescoring.
#   bash mailbox/leaderboard-ct/scripts/run_render.sh WORKTREE
set -uo pipefail
WT=${1:?leaderboard-ct worktree}
PY=${PY:-$HOME/.pyenv/shims/python3}
R=/home/cbasaran/code/jevgammon
D=$R/mailbox/leaderboard-ct
I=/tmp/lct
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon
HASH=$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["results"])' "$SITE/data/manifest.json")
stamp() { date -u '+%F %T UTC'; }
for v in main branch; do
  rm -rf "$I/src-$v"; mkdir -p "$I/src-$v/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$v/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$v/tools/"; done
  shopt -u dotglob
done
git -C "$R" archive --prefix=tools/site/ origin/main:tools/site | tar -x -C "$I/src-main"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-branch"
mkdir -p "$I/state"
for f in snap.db plays knockout.db shared prompts.db; do rm -rf "$I/state/$f"; cp -r "$LIVE/$f" "$I/state/"; done
(cd "$I/src-branch/tools/site" && $PY -c "import snapshot, sys; print('learning key', snapshot.snapshot_learning(sys.argv[1], sys.argv[2]))" "$R" "$I/state")
{
  echo "# checks.run on whole-site renders. Started $(stamp)"
  echo "# main: $(git -C "$R" rev-parse --short origin/main)  leaderboard-ct: $(git -C "$WT" rev-parse --short HEAD)  results hash fixed: $HASH"
  echo "# live mirror: $(git -C "$LIVE/analysis" rev-parse --short HEAD), data as of $($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["data_as_of"])' "$SITE/data/manifest.json")"
  status=0
  for v in main branch; do
    echo; echo "## $v: render_site.py $I/src-$v $I/state $I/out-$v $HASH --checks"
    rm -rf "$I/out-$v"
    (cd "$I/src-$v" && nice $PY "$D/scripts/render_site.py" "$I/src-$v" "$I/state" "$I/out-$v" "$HASH" --checks 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where'; exit "${PIPESTATUS[0]}")
    rc=$?
    echo "exit status ($v): $rc"
    [ "$rc" -eq 0 ] || status=1
  done
  echo; echo "# Finished $(stamp); exit status: $status"
  exit "$status"
} 2>&1 | tee "${OUT:-$D/checks-run.txt}"
exit "${PIPESTATUS[0]}"
