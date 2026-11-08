#!/usr/bin/env bash
# Review 5 of the learning page (Ümit #2925 spec; wording Zeki #2929), every output teed into
# mailbox/learning-page-review5/. Render-only: no build.py/update.sh, no server, no timer, no deploy, no model call; the
# pilot's files and the site state are only read (copies under $I). tools/site must be committed (renders use HEAD).
# From the learning-page worktree:
#   PATH=/usr/bin:$PATH bash mailbox/learning-page-review5/scripts/run_review5.sh
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
git -C "$WT" diff --quiet HEAD -- tools/site || { echo "tools/site has uncommitted changes"; exit 2; }
R=/home/cbasaran/code/jevgammon
D=$WT/mailbox/learning-page-review5
S=$D/scripts
I=${REVIEW_SCRATCH:-/tmp/inv5}
STATE=/tmp/inv/state                 # review 3's copy of the site state (read-only here), reused by reviews 4 and 5
HASH=1279974c                        # results hash fixed (review 3's), so the two renders compare file by file
PILOT=$R/workspace/learning-pilot
TS=$PILOT/test_set.json
TOOLS=$WT/tools/site
HEAD_SHORT=$(git -C "$WT" rev-parse --short HEAD)
BEFORE=${BEFORE:-003f7e7}               # the branch's commit before review 5 (ad2fb4d rebased onto origin/main)
MAIN_SHORT=$(git -C "$WT" rev-parse --short origin/main)
stamp() { date -u '+%F %T UTC'; }
mkdir -p "$I"

# States: the REAL complete state and the no-results state; SYNTHETIC subsets of the real series (make_states.py).
python3 "$S/make_states.py" "$TOOLS" "$PILOT" "$TS" "$I/states" 2>&1 | tee "$D/00-states.txt"

# (a) Whole-site renders (default build, PREREGISTRATION_ONLY on) of origin/main and of the branch, same state and
# results hash; checks.run on the branch's.
{
  echo "# (a) whole-site renders, default build. origin/main $MAIN_SHORT and branch $HEAD_SHORT. Started $(stamp)"
  for side in main:origin/main branch:HEAD; do
    IFS=: read -r n ref <<<"$side"
    # A read-only mirror of the main checkout (symlinks; review 4's layout) whose tools/site is the tree under test.
    rm -rf "$I/src-$n" "$I/out-$n" && mkdir -p "$I/src-$n/tools"
    for e in "$R"/* "$R"/.[!.]*; do [ "$(basename "$e")" = tools ] || ln -s "$e" "$I/src-$n/"; done
    for e in "$R"/tools/*; do [ "$(basename "$e")" = site ] || ln -s "$e" "$I/src-$n/tools/"; done
    git -C "$WT" archive --prefix=tools/site/ "$ref:tools/site" | tar -x -C "$I/src-$n"
    flag=""; [ "$n" = branch ] && flag=--checks
    (cd "$I/src-$n" && nice python3 "$S/render_site.py" "$I/src-$n" "$STATE" "$I/out-$n" "$HASH" $flag 2>&1 \
      | grep -v -e RuntimeWarning -e 'np.where')
  done
  echo "# Finished $(stamp)"
} 2>&1 | tee "$D/01-site-renders-and-checks-run.txt"

# (b) The learning page alone, learning_page.py --check, in every state.
{
  echo "# (b) learning_page.py --check at $HEAD_SHORT (links against the branch's whole-site render). Started $(stamp)"
  for c in default-preregistration:real: none:none:--with-results \
           SYNTHETIC-not-started:SYNTHETIC-not-started:--with-results \
           SYNTHETIC-smoke-running:SYNTHETIC-smoke-running:--with-results \
           SYNTHETIC-running:SYNTHETIC-running:--with-results real-complete:real:--with-results; do
    IFS=: read -r n st flag <<<"$c"
    echo; echo "## $n: python3 tools/site/learning_page.py --out $I/page-$n --src $I/states/$st/learning --check $I/out-branch --test-set <test_set.json> $flag"
    rm -rf "$I/page-$n"
    (cd "$WT" && python3 tools/site/learning_page.py --out "$I/page-$n" --src "$I/states/$st/learning" \
      --check "$I/out-branch" --test-set "$TS" $flag 2>&1 | sed "s#$I#\$SCRATCH#g")
    python3 - "$I/page-$n" <<'EOF'
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1])
L = json.loads((out / "data/v3/learning-pilot.json").read_text())
page = (out / "learning/index.html").read_text()
r = L["results"]
print("preregistration_only:", L["preregistration_only"], "| validation:",
      None if L["validation"] is None else {k: L["validation"][k] for k in ("accepted", "complete")})
print("status (data file):", L.get("status"))
m = re.search(r'id="learning-status-line"><strong[^>]*>([^<]*)</strong>.*?Last update: (?:<time[^>]*>)?([^<]*)', page)
print("status line (page):", m and f"{m.group(1)} · Last update: {m.group(2)}")
print("results:", None if r is None else {k: r.get(k) for k in ("complete", "series_total_done", "last_update")},
      "| lift/signal in data:", sorted(k for k in ("learning_lift", "signal", "paired_series") if k in (r or {})),
      "| lessons:", len(L["lessons"]), "| budget series:", len(L["budget"]))
print("charts:", re.findall(r'data-chart="(learning-[a-z]+)"', page),
      "| chart dots:", len(re.findall(r'<circle class="lp-dot"', page)),
      "| control dashed lines:", len(re.findall(r'data-arm="control" style="[^"]*" stroke-dasharray', page)))
print("blocks:", re.findall(r'id="(learning-verdict[a-z-]*|learning-lift|learning-signal|learning-leaders)"', page))
m = re.search(r'id="learning-verdict-pending">(.*?)</p>', page)
print("verdict pending text:", m and re.sub("<[^>]+>", "", m.group(1)))
print("top label:", re.search(r'<p class="eyebrow">([^<]*)', page).group(1), "| heading:",
      re.search(r"<h1>([^<]*)", page).group(1))
EOF
  done
  echo; echo "## the default build reads no results: files opened under the source or the test set while building"
  (cd "$TOOLS" && python3 -c '
import sys
from pathlib import Path
opened = []
sys.addaudithook(lambda e, a: opened.append(str(a[0])) if e == "open" else None)
import learning_page as LP
LP.data(LP.PLAN, Path(sys.argv[1]), Path(sys.argv[2]))
print([o.replace(sys.argv[1], "<src>") for o in opened if o.startswith(sys.argv[1]) or o == sys.argv[2]])' \
    "$I/states/real/learning" "$TS")
  echo; echo "## the default page equals origin/main's default page (learning/ and its data file)"
  for f in learning/index.html data/v3/learning-pilot.json; do
    cmp -s "$I/out-main/$f" "$I/out-branch/$f" && echo "identical: $f" || echo "DIFFERS: $f"
  done
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/02-page-checks.txt"

# (c) Faults: page/data faults, Zeki's synthetic_checks.py as delivered and ported, the saved regression cases.
{
  echo "# (c0) Zeki #2931: one regression test per fix (zeki2931_regressions.py), on the tree before the fixes"
  echo "# ($BEFORE = ad2fb4d rebased) and on $HEAD_SHORT. Started $(stamp)"
  B=$I/src-before
  rm -rf "$B" && mkdir -p "$B/tools"
  for e in "$R"/* "$R"/.[!.]*; do [ "$(basename "$e")" = tools ] || ln -s "$e" "$B/"; done
  for e in "$R"/tools/*; do [ "$(basename "$e")" = site ] || ln -s "$e" "$B/tools/"; done
  git -C "$WT" archive --prefix=tools/site/ "$BEFORE:tools/site" | tar -x -C "$B"
  echo; echo "## before the fixes: $BEFORE:tools/site (expected: every case FAILs except the control case of fix 4)"
  python3 "$S/zeki2931_regressions.py" "$B/tools/site" "$I/states/real/learning" "$TS" 2>&1 | sed "s#$I#\$SCRATCH#g"
  echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "## after the fixes: $HEAD_SHORT:tools/site (expected: every case PASSes)"
  python3 "$S/zeki2931_regressions.py" "$TOOLS" "$I/states/real/learning" "$TS" 2>&1 | sed "s#$I#\$SCRATCH#g"
  echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03a-zeki2931-fix-regressions.txt"

{
  echo "# (c1) injected faults (injected_faults.py) at $HEAD_SHORT. Started $(stamp)"
  python3 "$S/injected_faults.py" "$TOOLS" "$I/page-SYNTHETIC-running" "$I/page-real-complete" "$I/out-branch" "$TS" \
    2>&1 | sed "s#$I#\$SCRATCH#g"; echo "exit code: ${PIPESTATUS[0]}"
  Z=/home/cbasaran/.agent-bus/received/jevgammon/f_7f2d02645d854171985de0ea21a21889-synthetic_checks.py
  echo; echo "# (c2) Zeki's synthetic_checks.py as delivered (sha256 $(sha256sum "$Z" | cut -c1-64)) on $HEAD_SHORT:tools/site. $(stamp)"
  rm -rf "$I/zeki" && mkdir -p "$I/zeki" && cp "$Z" "$I/zeki/synthetic_checks.py"
  git -C "$WT" archive --prefix=tools/site/ HEAD:tools/site | tar -x -C "$I/zeki"
  (cd "$I/zeki" && python3 synthetic_checks.py 2>&1 | sed "s#$I#\$SCRATCH#g"); echo "exit code: ${PIPESTATUS[0]}"
  echo; echo "# (c3) Zeki's synthetic cases ported to this candidate (zeki_synthetic_ported.py). $(stamp)"
  python3 "$S/zeki_synthetic_ported.py" "$TOOLS" "$I/states/real/learning" "$I/states/SYNTHETIC-smoke-running/learning" \
    "$TS" 2>&1; echo "exit code: $?"
  echo; echo "# (c4) review 4's saved regression cases (regression_cases.py), on the REAL complete state and the SYNTHETIC running subset. $(stamp)"
  python3 "$S/regression_cases.py" "$TOOLS" "$I/states/real/learning" "$I/states/SYNTHETIC-running/learning" "$TS" 2>&1
  echo "exit code: $?"
  echo; echo "# Finished $(stamp)"
} 2>&1 | tee "$D/03-faults.txt"

# (d) File-level invariance inventory: origin/main's render against the branch's.
python3 "$S/invariance.py" "$I/out-main" "$I/out-branch" "$D/04-invariance-inventory.csv" "$D/04-invariance-summary.txt"
