#!/usr/bin/env bash
# Update loop of the backgammon site preview (brief B1, B2): https://zekiworks.github.io/analysis/backgammon-preview/
# Run by the systemd user timer bg-site-preview.timer (every 30 minutes). Install:
#   systemctl --user link tools/site/systemd/bg-site-preview.{service,timer}
#   systemctl --user enable --now bg-site-preview.timer
#
#   1. snapshot (tools/site/snapshot.py): league tables copied in one read transaction, plus the prompts of new
#      decisions; its fingerprint, the smoke-test rows, the v1 set and the site code make the change key;
#      if the key equals the last deployed one, stop: nothing changed;
#   2. GNUbg scores every legal play of the new decisions (tools/site/score.sh: 8 processes, nice 19, idle I/O),
#      never at the same time as the live page's scoring (shares v3-page-refresh's lock while it scores);
#   3. tools/site/build.py builds the site into this job's own clone of the analysis repository and runs the
#      pre-deploy checks; if a check fails nothing is deployed and the failures go to
#      mailbox/Backgammon site preview - check failed.md;
#   4. commit backgammon-preview/ only (never the live page) and push, rebasing on a race;
#   5. tools/site/findings_draft.py refreshes workspace/findings-draft.md from the deployed data.
# Runs never overlap (flock). Log: STATE/update.log.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE=${XDG_STATE_HOME:-$HOME/.local/state}/bg-site
CLONE=$STATE/analysis
OUT=$CLONE/backgammon-preview
REMOTE=git@github-zekiworks:zekiworks/analysis
LIVE_LOCK=${XDG_STATE_HOME:-$HOME/.local/state}/v3-page-refresh/lock
FAILED="$ROOT/mailbox/Backgammon site preview - check failed.md"
BANNED='192\.168|127\.0\.0|/home/|bariton|spark-|\bsk-|base_url'

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
trap 'log "failed (line $LINENO)"' ERR
cd "$ROOT"
log "start"

# 1. Snapshot and change key.
SUMMARY=$(python3 tools/site/snapshot.py "$ROOT/v3.db" "$STATE" | tail -1)
FP=$(python3 -c 'import json, sys; print(json.loads(sys.argv[1])["fingerprint"])' "$SUMMARY")
CODE=$(git rev-parse HEAD:tools/site)
KEY="$FP code:$CODE smoke:$(sha256sum smoke/part-a.json | cut -c1-12) v1:$(stat -c %Y replay.db)"
if [ "${1:-}" != "--force" ] && [ -f "$STATE/deployed.key" ] && [ "$(cat "$STATE/deployed.key")" = "$KEY" ]; then
  log "no change ($FP)"
  exit 0
fi
log "snapshot: $SUMMARY"

# 2. Score new decisions, never alongside the live page's scoring.
exec 8>"$LIVE_LOCK"
flock -w 1800 8 || { log "live page scoring held its lock for 30 min; next run retries"; exit 0; }
log "scored: $(tools/site/score.sh "$STATE/snap.db" "$STATE/plays" | tail -1)"
flock -u 8

# 3. Build and check in the job's own clone, on top of the published site.
[ -d "$CLONE/.git" ] || git clone -q "$REMOTE" "$CLONE"
git -C "$CLONE" fetch -q origin main
git -C "$CLONE" checkout -q main
git -C "$CLONE" reset -q --hard origin/main
set +e
python3 tools/site/build.py --state "$STATE" --out "$OUT" > "$STATE/build.out" 2> "$STATE/build.err"
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
  {
    echo "# Backgammon site preview: pre-deploy check failed"
    echo
    echo "$(date -u '+%F %H:%M UTC'). The update loop (tools/site/update.sh) built the preview but did not deploy it."
    echo "Exit status $STATUS. The preview keeps its last good build."
    echo
    echo '```'
    if [ -f "$STATE/site-check-failures.json" ] && [ $STATUS -eq 2 ]; then
      python3 -c 'import json, sys; [print(f) for f in json.load(open(sys.argv[1]))["failures"][:200]]' "$STATE/site-check-failures.json"
    else
      tail -40 "$STATE/build.err"
    fi
    echo '```'
  } > "$FAILED"
  log "build or checks failed (status $STATUS); not deployed; see mailbox"
  git -C "$CLONE" reset -q --hard origin/main
  git -C "$CLONE" clean -qfd -- backgammon-preview
  exit 1
fi
rm -f "$FAILED"
if git -C "$CLONE" diff --name-only HEAD -- . ':!backgammon-preview' | grep -q .; then
  log "build touched files outside backgammon-preview/; not deployed"
  git -C "$CLONE" reset -q --hard origin/main
  exit 1
fi
if grep -rqE "$BANNED" "$OUT" --include='*.html' --include='*.json' --include='*.js' --include='*.css'; then
  log "banned string in the preview; not deployed"
  git -C "$CLONE" reset -q --hard origin/main
  git -C "$CLONE" clean -qfd -- backgammon-preview
  exit 1
fi

# 4. Publish when the build changed anything.
AS_OF=$(python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["data_as_of"], d["results"])' "$OUT/data/manifest.json")
git -C "$CLONE" add -A -- backgammon-preview
if git -C "$CLONE" diff --cached --quiet; then
  log "no change in the built site ($AS_OF)"
else
  git -C "$CLONE" commit -q -m "backgammon-preview: data as of $AS_OF"
  for attempt in 1 2 3; do
    if git -C "$CLONE" push -q origin main; then
      log "pushed preview, data as of $AS_OF"
      break
    fi
    [ "$attempt" = 3 ] && { log "push failed 3 times; next run retries"; exit 1; }
    git -C "$CLONE" pull -q --rebase origin main || { git -C "$CLONE" rebase --abort; log "rebase conflict; next run rebuilds"; exit 1; }
  done
fi
echo "$KEY" > "$STATE/deployed.key"

# 5. Findings draft (never published by itself).
python3 tools/site/findings_draft.py "$OUT" "$ROOT/workspace/findings-draft.md" || log "findings draft failed"
log "done"
