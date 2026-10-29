#!/usr/bin/env bash
# Update loop of the backgammon site (brief v12 B1, B2): https://zekiworks.github.io/analysis/backgammon/
# Since the live switch (23 Oct 2026, Ümit's approval) it deploys data updates to the live site by itself; the old
# preview path, analysis/backgammon-preview/, holds one redirect per page to the same page on the live address.
# New sections, layout changes and findings text still need Ümit's approval before they are committed here.
# Run by the systemd user timer bg-site-preview.timer (its name predates the switch; every 15 minutes; Persistent,
# so a run missed while the machine was off happens at boot; the user manager lingers, so it runs without a login).
# Install:
#   systemctl --user link tools/site/systemd/bg-site-preview{,-failed}.service tools/site/systemd/bg-site-preview.timer
#   systemctl --user enable --now bg-site-preview.timer
#
#   1. snapshot (tools/site/snapshot.py): league tables copied in one read transaction, plus the prompts of new
#      decisions and the Nackgammon knockout's matches (knockout-nack.db, read-only, to STATE/knockout.db); its
#      fingerprint (the knockout's included), the smoke-test rows, the v1 set and the site code make the change key;
#      if the key equals the last deployed one, stop: nothing changed;
#   2. GNUbg scores every legal play of the new decisions (tools/site/score.sh: 8 processes, nice 19, idle I/O);
#   3. tools/site/build.py builds the site into this job's own clone of the analysis repository and runs the
#      pre-deploy checks (numbers trace, counts add up, no mixing, every published finding still holds, no private
#      address or credential in any file); if a check fails nothing is deployed and the failures go to
#      mailbox/Backgammon site preview - check failed.md (a failed finding also to
#      mailbox/Backgammon site - findings to re-check.md);
#   4. commit backgammon/ and the redirects in backgammon-preview/ only, and push, rebasing on a race;
#   5. tools/site/findings_draft.py refreshes workspace/findings-draft.md from the deployed data.
# The loop reports its own failures: any other failure (a crash, a push that keeps failing, a kill or timeout)
# writes mailbox/Backgammon site preview - update loop failed.md (tools/site/report_failure.sh, from the ERR trap and
# from systemd's OnFailure=); the next successful run removes it.
# Only committed site code is published: every step runs from STATE/src, a mirror of the repository (one symlink per
# top-level entry and per entry of tools/) whose tools/site is HEAD's tree, extracted with git archive; uncommitted
# edits under tools/site never reach the site (a run that finds some logs that it ignored them).
# Runs never overlap (flock). Log: STATE/update.log.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE=${XDG_STATE_HOME:-$HOME/.local/state}/bg-site
CLONE=$STATE/analysis
OUT=$CLONE/backgammon
PREVIEW=$CLONE/backgammon-preview
REMOTE=git@github-zekiworks:zekiworks/analysis
FAILED="$ROOT/mailbox/Backgammon site preview - check failed.md"
FINDINGS="$ROOT/mailbox/Backgammon site - findings to re-check.md"
LOOP_FAILED="$ROOT/mailbox/Backgammon site preview - update loop failed.md"

mkdir -p "$STATE"
exec >>"$STATE/update.log" 2>&1
log() { echo "$(date -u +%FT%TZ) $*"; }
exec 9>"$STATE/lock"
if ! flock -n 9; then
  log "previous run still going; skipped"
  exit 0
fi
renice -n 19 $$ >/dev/null
ionice -c 3 -p $$ 2>/dev/null || true
trap 'log "failed (line $LINENO)"; "$ROOT/tools/site/report_failure.sh" "update.sh stopped at line $LINENO"' ERR
log "start"

# 0. The committed site code (the tree the change key names) in a mirror of the repository.
CODE=$(git -C "$ROOT" rev-parse HEAD:tools/site)
SRC=$STATE/src
rm -rf "$SRC"
mkdir -p "$SRC/tools"
shopt -s nullglob dotglob
for e in "$ROOT"/*; do
  case ${e##*/} in tools|.git) ;; *) ln -s "$e" "$SRC/" ;; esac
done
for e in "$ROOT"/tools/*; do
  [ "${e##*/}" = site ] || ln -s "$e" "$SRC/tools/"
done
shopt -u nullglob dotglob
git -C "$ROOT" archive --prefix=tools/site/ "$CODE" | tar -x -C "$SRC"
if [ -n "$(git -C "$ROOT" status --porcelain -- tools/site)" ]; then
  log "tools/site has uncommitted changes; ignored: building the committed tree $CODE"
fi
cd "$SRC"

# 1. Snapshot and change key.
SUMMARY=$(python3 tools/site/snapshot.py "$ROOT/v3.db" "$STATE" | tail -1)
FP=$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["fingerprint"])' "$SUMMARY")
KEY="$FP code:$CODE smoke:$(sha256sum "$ROOT/smoke/part-a.json" | cut -c1-12) v1:$(stat -c %Y "$ROOT/replay.db")"
if [ "${1:-}" != "--force" ] && [ -f "$STATE/deployed.key" ] && [ "$(cat "$STATE/deployed.key")" = "$KEY" ]; then
  log "no change ($FP)"
  rm -f "$LOOP_FAILED"
  exit 0
fi
log "snapshot: $SUMMARY"

# 2. Score new decisions.
log "scored: $(tools/site/score.sh "$STATE/snap.db" "$STATE/plays" | tail -1)"

# 3. Build and check in the job's own clone, on top of the published site.
[ -d "$CLONE/.git" ] || git clone -q "$REMOTE" "$CLONE"
git -C "$CLONE" fetch -q origin main
git -C "$CLONE" checkout -q main
git -C "$CLONE" reset -q --hard origin/main
set +e
python3 tools/site/build.py --state "$STATE" --out "$OUT" --preview-redirects "$PREVIEW" > "$STATE/build.out" 2> "$STATE/build.err"
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
  {
    echo "# Backgammon site: pre-deploy check failed"
    echo
    echo "$(date -u '+%F %H:%M UTC'). The update loop (tools/site/update.sh) built the site but did not deploy it."
    echo "Exit status $STATUS. The live site keeps its last good build."
    echo
    echo '```'
    if [ -f "$STATE/site-check-failures.json" ] && [ $STATUS -eq 2 ]; then
      python3 -c 'import json, sys; [print(f) for f in json.load(open(sys.argv[1]))["failures"][:200]]' "$STATE/site-check-failures.json"
    else
      tail -40 "$STATE/build.err"
    fi
    echo '```'
  } > "$FAILED"
  # B4: a published finding that no longer holds also gets its own note; Ümit decides the new wording.
  if [ $STATUS -eq 2 ] && python3 -c 'import json, sys; sys.exit(0 if any(f.startswith("Finding ") for f in json.load(open(sys.argv[1]))["failures"]) else 1)' "$STATE/site-check-failures.json"; then
    {
      echo "# Published findings the new data no longer supports"
      echo
      echo "$(date -u '+%F %H:%M UTC'). The deploy was stopped. Each line: the finding, then what the data now shows."
      echo
      python3 -c 'import json, sys; [print("- " + f) for f in json.load(open(sys.argv[1]))["failures"] if f.startswith("Finding ")]' "$STATE/site-check-failures.json"
    } > "$FINDINGS"
  fi
  log "build or checks failed (status $STATUS); not deployed; see mailbox"
  git -C "$CLONE" reset -q --hard origin/main
  git -C "$CLONE" clean -qfd -- backgammon backgammon-preview
  # A failed check is the loop working as intended (reported above); a crashed build is a loop failure.
  [ $STATUS -eq 2 ] && { rm -f "$LOOP_FAILED"; exit 0; }
  exit 1
fi
rm -f "$FAILED" "$FINDINGS"
if git -C "$CLONE" diff --name-only HEAD -- . ':!backgammon' ':!backgammon-preview' | grep -q .; then
  log "build touched files outside backgammon/ and backgammon-preview/; not deployed"
  git -C "$CLONE" reset -q --hard origin/main
  exit 1
fi

# 4. Publish when the build changed anything.
AS_OF=$(python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["data_as_of"], d["results"])' "$OUT/data/manifest.json")
git -C "$CLONE" add -A -- backgammon backgammon-preview
if git -C "$CLONE" diff --cached --quiet; then
  log "no change in the built site ($AS_OF)"
else
  git -C "$CLONE" commit -q -m "backgammon: data as of $AS_OF"
  for attempt in 1 2 3; do
    if git -C "$CLONE" push -q origin main; then
      log "pushed, data as of $AS_OF"
      break
    fi
    [ "$attempt" = 3 ] && { log "push failed 3 times; next run retries"; exit 1; }
    git -C "$CLONE" pull -q --rebase origin main || { git -C "$CLONE" rebase --abort; log "rebase conflict; next run rebuilds"; exit 1; }
  done
fi
echo "$KEY" > "$STATE/deployed.key"

# 5. Findings draft (never published by itself).
python3 tools/site/findings_draft.py "$OUT" "$ROOT/workspace/findings-draft.md" || log "findings draft failed"
rm -f "$LOOP_FAILED"
log "done"
