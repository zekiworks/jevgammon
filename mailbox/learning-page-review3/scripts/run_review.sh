#!/usr/bin/env bash
# Review 3 of the learning page (Zeki #2531): every output teed into this directory. Render-only: nothing here runs
# build.py, update.sh, a server or a deploy; the live state and site are only read (copied to /tmp/inv first).
#   bash mailbox/learning-page-review3/scripts/run_review.sh            (from the learning-page worktree)
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
R=/home/cbasaran/code/jevgammon                       # main checkout: read only (v3.db, replay.db, workspace, mailbox)
D=$WT/mailbox/learning-page-review3
S=$D/scripts
I=/tmp/inv                                           # scratch: state copy, source mirrors, renders
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon                       # the live build, read only (links resolve against it)
TS=$R/workspace/learning-pilot/test_set.json         # private, read only
HASH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["results"])' "$SITE/data/manifest.json")
stamp() { date -u '+%F %T UTC'; }

# Sources: update.sh's layout, tools/site from origin/main and from this worktree's HEAD.
for v in main branch; do
  rm -rf "$I/src-$v"; mkdir -p "$I/src-$v/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$v/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$v/tools/"; done
  shopt -u dotglob
done
git -C "$R" archive --prefix=tools/site/ origin/main:tools/site | tar -x -C "$I/src-main"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-branch"
# The branch's plan (mailbox/ of the mirrors is main's; both carry origin/main's committed plan).
# State: a copy of the live state; STATE/learning as snapshot.py writes it from the real workspace (no results yet).
mkdir -p "$I/state"
for f in snap.db plays knockout.db shared prompts.db; do rm -rf "$I/state/$f"; cp -r "$LIVE/$f" "$I/state/"; done
(cd "$I/src-branch/tools/site" && python3 -c "import snapshot, sys; print('learning key', snapshot.snapshot_learning(sys.argv[1], sys.argv[2]))" "$R" "$I/state")

# (a) Whole-site renders, main vs branch, no-results state, full checks.run on both.
{
  echo "# (a) checks.run on whole-site renders (no-results state). Started $(stamp)"
  echo "# main: $(git -C "$R" rev-parse --short origin/main)  branch: $(git -C "$WT" rev-parse --short HEAD)  results hash fixed: $HASH"
  for v in main branch; do
    echo; echo "## $v: python3 render_site.py $I/src-$v $I/state $I/out-$v $HASH --checks"
    rm -rf "$I/out-$v"
    (cd "$I/src-$v" && nice python3 "$S/render_site.py" "$I/src-$v" "$I/state" "$I/out-$v" "$HASH" --checks 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where')
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/01-full-checks-run.txt"

# (b) The learning page alone in three states, page checks (numbers, mixing, links, private strings, check 7).
{
  echo "# (b) learning_page.py --check in three states. Started $(stamp)"
  for c in none:/tmp/lp-state running:/tmp/lp-state-dryrun complete:/tmp/lp-state-dry; do
    n=${c%%:*}; src=${c#*:}
    echo; echo "## $n: python3 tools/site/learning_page.py --out /tmp/lp-out-$n --src $src/learning --check $SITE --test-set $TS"
    rm -rf "/tmp/lp-out-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "/tmp/lp-out-$n" --src "$src/learning" --check "$SITE" --test-set "$TS" 2>&1)
    python3 -c 'import json,sys; L=json.load(open(sys.argv[1])); r=L["results"]; print("results:", None if r is None else {k: r.get(k) for k in ("complete","series_done","planned_series_per_arm")}, "| lift/signal in data:", sorted(k for k in ("learning_lift","signal","paired_series") if k in (r or {})))' "/tmp/lp-out-$n/data/v3/learning-pilot.json"
    echo "lift/signal blocks in page: $(grep -o 'id="learning-\(lift\|signal\)"' "/tmp/lp-out-$n/learning/index.html" | tr '\n' ' ')"
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (c) Injected faults on the running-state render.
{
  echo "# (c) injected faults. Started $(stamp)"
  echo "# python3 injected_faults.py $WT/tools/site /tmp/lp-out-running $SITE <test_set.json>"
  python3 "$S/injected_faults.py" "$WT/tools/site" /tmp/lp-out-running "$SITE" "$TS" 2>&1
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-injected-faults.txt"

# (d) File-level invariance inventory of the two whole-site renders.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt"
