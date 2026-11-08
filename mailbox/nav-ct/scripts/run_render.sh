#!/usr/bin/env bash
# nav-ct renders (Ümit #2901, #2904, #2907): the whole site rendered twice from one copy of the live state, with the
# tools/site of leaderboard-ct (the base, a99a1ce) and of nav-ct's HEAD, each followed by checks.run (the full pre-deploy
# checks). Render-only: no build.py main, no update.sh, no server, no deploy; the live state is only read (copied).
# render_site.py runs build.compute(), which reads the published aggregates and runs the site's offline computations,
# the bootstrap loops of offline.py included: NOT statistics-free, but no model call, no scorer, no rescoring.
#   bash mailbox/nav-ct/scripts/run_render.sh NAV_WORKTREE BASE_COMMIT
set -uo pipefail
WT=${1:?nav-ct worktree}
BASE=${2:?base commit}
PY=${PY:-$HOME/.pyenv/shims/python3}
R=/home/cbasaran/code/jevgammon
D=$R/mailbox/nav-ct
I=/tmp/nav
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon
mkdir -p "$I"
# The live mirror as rendered now, kept beside the renders for the comparisons (it can move on during the run).
rm -rf "$I/live" && cp -r "$SITE" "$I/live"
HASH=$($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["results"])' "$I/live/data/manifest.json")
stamp() { date -u '+%F %T UTC'; }
for v in base nav; do
  rm -rf "$I/src-$v"; mkdir -p "$I/src-$v/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$v/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$v/tools/"; done
  shopt -u dotglob
done
git -C "$WT" archive --prefix=tools/site/ "$BASE:tools/site" | tar -x -C "$I/src-base"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-nav"
mkdir -p "$I/state"
for f in snap.db plays knockout.db shared prompts.db; do rm -rf "$I/state/$f"; cp -r "$LIVE/$f" "$I/state/"; done
(cd "$I/src-nav/tools/site" && $PY -c "import snapshot, sys; print('learning key', snapshot.snapshot_learning(sys.argv[1], sys.argv[2]))" "$R" "$I/state")
{
  echo "# checks.run on whole-site renders. Started $(stamp)"
  echo "# base (leaderboard-ct): $(git -C "$WT" rev-parse --short "$BASE")  nav-ct: $(git -C "$WT" rev-parse --short HEAD)  results hash fixed: $HASH"
  echo "# live mirror: $(git -C "$LIVE/analysis" rev-parse --short HEAD), data as of $($PY -c 'import json,sys; print(json.load(open(sys.argv[1]))["data_as_of"])' "$I/live/data/manifest.json")"
  status=0
  for v in base nav; do
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
} 2>&1 | tee "$D/checks-run.txt"
exit "${PIPESTATUS[0]}"
