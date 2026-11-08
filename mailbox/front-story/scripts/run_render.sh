#!/usr/bin/env bash
# front-story review renders (Ümit #2570): the whole site rendered twice from one copy of the live state, with
# tools/site of origin/main and of the front-story worktree's HEAD, each followed by checks.run (the full pre-deploy
# checks). Render-only: no build.py main, no update.sh, no server, no deploy; the live state is only read (copied).
# The same method as mailbox/learning-page-review3 (render_site.py copied from there).
#   bash mailbox/front-story/scripts/run_render.sh FRONT_WORKTREE
set -uo pipefail
WT=${1:?front-story worktree}
R=/home/cbasaran/code/jevgammon
D=$R/mailbox/front-story
I=/tmp/fs
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon
HASH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["results"])' "$SITE/data/manifest.json")
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
(cd "$I/src-branch/tools/site" && python3 -c "import snapshot, sys; print('learning key', snapshot.snapshot_learning(sys.argv[1], sys.argv[2]))" "$R" "$I/state")
{
  echo "# checks.run on whole-site renders. Started $(stamp)"
  echo "# main: $(git -C "$R" rev-parse --short origin/main)  front-story: $(git -C "$WT" rev-parse --short HEAD)  results hash fixed: $HASH"
  echo "# live mirror: $(git -C "$LIVE/analysis" rev-parse --short HEAD), data as of $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["data_as_of"])' "$SITE/data/manifest.json")"
  for v in main branch; do
    echo; echo "## $v: python3 render_site.py $I/src-$v $I/state $I/out-$v $HASH --checks"
    rm -rf "$I/out-$v"
    (cd "$I/src-$v" && nice python3 "$D/scripts/render_site.py" "$I/src-$v" "$I/state" "$I/out-$v" "$HASH" --checks 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where')
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/checks-run.txt"
