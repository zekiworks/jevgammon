#!/usr/bin/env bash
# Review 3 of the learning-page candidate: every output teed into mailbox/learning-page-review3/. Render-only: nothing
# here runs build.py, update.sh, a server, a timer or a deploy; the live state and site are only read (copied to
# $I first). Run from the learning-page worktree:
#   bash mailbox/learning-page-review3/scripts/run_review.sh
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
R=/home/cbasaran/code/jevgammon                       # main checkout: read only (v3.db, replay.db, workspace, mailbox)
D=$WT/mailbox/learning-page-review3
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/inv}                        # scratch: state copy, source mirrors, renders, fixtures
LIVE=$HOME/.local/state/bg-site
SITE=$LIVE/analysis/backgammon                       # the live build, read only (links resolve against it)
TS=$R/workspace/learning-pilot/test_set.json         # private, read only; never written to these files
HASH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["results"])' "$SITE/data/manifest.json")
TOOLS=$WT/tools/site
stamp() { date -u '+%F %T UTC'; }
mkdir -p "$I"

# Sources: update.sh's layout; tools/site from origin/main and from this worktree's HEAD (committed trees only).
for v in main branch; do
  rm -rf "$I/src-$v"; mkdir -p "$I/src-$v/tools"
  shopt -s dotglob
  for e in "$R"/*; do case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$I/src-$v/" ;; esac; done
  for e in "$R"/tools/*; do [ "${e##*/}" = site ] || ln -s "$e" "$I/src-$v/tools/"; done
  shopt -u dotglob
done
git -C "$R" archive --prefix=tools/site/ origin/main:tools/site | tar -x -C "$I/src-main"
git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/src-branch"
# State: a copy of the live state; STATE/learning as snapshot.py writes it from the real workspace (no results yet).
mkdir -p "$I/state"
for f in snap.db plays knockout.db shared prompts.db; do rm -rf "$I/state/$f"; cp -r "$LIVE/$f" "$I/state/"; done
(cd "$I/src-branch/tools/site" && python3 -c "import snapshot, sys; print('learning key', snapshot.snapshot_learning(sys.argv[1], sys.argv[2]))" "$R" "$I/state")
# Page states: none (the real workspace: no results), dry (the dry run's files, accepted, running), and the SYNTHETIC
# running / complete fixtures (make_fixture.py; test data, never results).
rm -rf "$I/dryroot" && mkdir -p "$I/dryroot/workspace/learning-pilot" "$I/dryroot/mailbox"
W=$R/workspace/learning-pilot
ln -s "$W/out-dry" "$I/dryroot/workspace/learning-pilot/out"; ln -s "$W/runs-dry" "$I/dryroot/workspace/learning-pilot/runs"
ln -s "$W/lessons_system.txt" "$W/lessons_user.txt" "$I/dryroot/workspace/learning-pilot/"
for st in none dry; do rm -rf "$I/state-$st"; mkdir -p "$I/state-$st"; done
(cd "$TOOLS" && python3 -c "import snapshot, sys; snapshot.snapshot_learning(sys.argv[1], sys.argv[2]); snapshot.snapshot_learning(sys.argv[3], sys.argv[4])" "$R" "$I/state-none" "$I/dryroot" "$I/state-dry")
python3 "$S/make_fixture.py" "$TOOLS" "$I/state-dry/learning" "$I/fix-complete" "$I/fix-running" "$TS"

# (a) Whole-site renders, main vs branch, no-results state, full checks.run on both.
{
  echo "# (a) checks.run on whole-site renders (no-results state). Started $(stamp)"
  echo "# main: $(git -C "$R" rev-parse --short origin/main)  branch: $(git -C "$WT" rev-parse --short HEAD)  results hash fixed: $HASH"
  for v in main branch; do
    echo; echo "## $v: python3 scripts/render_site.py $I/src-$v $I/state $I/out-$v $HASH --checks"
    rm -rf "$I/out-$v"
    (cd "$I/src-$v" && nice python3 "$S/render_site.py" "$I/src-$v" "$I/state" "$I/out-$v" "$HASH" --checks 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where')
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/01-full-checks-run.txt"

# (b) The learning page alone in four states, page checks (numbers, mixing, links, private strings, check 7).
{
  echo "# (b) learning_page.py --check in four states. Started $(stamp)"
  for c in none:$I/state-none/learning dry-running:$I/state-dry/learning synthetic-running:$I/fix-running synthetic-complete:$I/fix-complete; do
    n=${c%%:*}; src=${c#*:}
    echo; echo "## $n: python3 tools/site/learning_page.py --out $I/page-$n --src $src --check $SITE --test-set <test_set.json>"
    rm -rf "$I/page-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "$I/page-$n" --src "$src" --check "$SITE" --test-set "$TS" 2>&1)
    python3 -c 'import json,sys; L=json.load(open(sys.argv[1])); r=L["results"]; print("validation:", L["validation"]); print("results:", None if r is None else {k: r.get(k) for k in ("complete","series_total_done","series_total_planned")}, "| lift/signal in data:", sorted(k for k in ("learning_lift","signal","paired_series") if k in (r or {})))' "$I/page-$n/data/v3/learning-pilot.json"
    echo "complete-only blocks in page: $(grep -o 'id="learning-\(lift\|signal\|leaders\)"' "$I/page-$n/learning/index.html" | tr '\n' ' ')"
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (c) Injected faults: in the rendered page (running state) and in the pilot's files (synthetic complete fixture).
{
  echo "# (c1) injected page faults. Started $(stamp)"
  python3 "$S/injected_faults.py" "$TOOLS" "$I/page-synthetic-running" "$SITE" "$TS" 2>&1
  echo; echo "# (c2) injected source faults. $(stamp)"
  python3 "$S/injected_source_faults.py" "$TOOLS" "$I/fix-complete" "$TS" 2>&1
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-injected-faults.txt"

# (d) File-level invariance inventory of the two whole-site renders.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt"
