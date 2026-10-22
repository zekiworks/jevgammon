#!/usr/bin/env bash
# Refreshes the v3 section of the public report (zekiworks.github.io/analysis/backgammon/#v3) from v3.db.
# Run by the systemd user timer v3-page-refresh.timer every 15 minutes. Install and run by hand:
#   systemctl --user link tools/v3/systemd/v3-page-refresh.{service,timer}
#   systemctl --user enable --now v3-page-refresh.timer
#   systemctl --user start v3-page-refresh.service
#
#   1. snapshot: one read transaction copies every table but `exchanges` (the prompts and answers, most of
#      v3.db's size; nothing here reads them) to /tmp, so the leagues keep writing undisturbed;
#   2. GNUbg scores the decisions not yet scored (tools/gnubg_eval.py, 32 shards kept under $STATE, at most 8
#      processes at nice 19);
#   3. tools/v3/page_v3.py writes backgammon/v3-results.json and the HTML fallback in a clone of the analysis
#      repository kept for this job (so hand edits in other working copies are never picked up half-done);
#   4. if the JSON changed: commit it (and index.html if it changed) and push, rebasing on a race.
# Once leagues 2 and 3 have both finished and their final data is pushed, the timer disables itself.
# Runs never overlap (flock). Log: v3-page-refresh.log in the repository root.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE=${XDG_STATE_HOME:-$HOME/.local/state}/v3-page-refresh
CLONE=$STATE/analysis
SCORES=$STATE/gnubg
SNAP=/tmp/v3-page-snap.db
REMOTE=git@github-zekiworks:zekiworks/analysis
SHARDS=32
JOBS=8
BANNED='192\.168|/home/|bariton|spark-|\bsk-'

mkdir -p "$STATE" "$SCORES"
exec >>"$ROOT/v3-page-refresh.log" 2>&1
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

# 1. Snapshot.
rm -f "$SNAP.tmp"
python3 - "$ROOT/v3.db" "$SNAP.tmp" <<'EOF'
import sqlite3, sys
src, dst = sys.argv[1:3]
db = sqlite3.connect(dst, uri=True, isolation_level=None)
db.execute("ATTACH ? AS src", (f"file:{src}?mode=ro",))
db.execute("BEGIN")
tables = db.execute("SELECT name, sql FROM src.sqlite_master WHERE type = 'table' AND name != 'exchanges'"
                    " AND name NOT LIKE 'sqlite_%'").fetchall()
for name, sql in tables:
    db.execute(sql)
    db.execute(f'INSERT INTO main."{name}" SELECT * FROM src."{name}"')
for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
                         " AND tbl_name != 'exchanges'").fetchall():
    db.execute(sql)
db.execute("COMMIT")
db.execute("DETACH src")
EOF
mv "$SNAP.tmp" "$SNAP"
read -r L2 L3 < <(sqlite3 "$SNAP" "SELECT (SELECT status FROM leagues WHERE id = 2) || ' ' || (SELECT status FROM leagues WHERE id = 3)")
log "snapshot done (league 2 $L2, league 3 $L3)"

# 2. Incremental GNUbg scoring (gnubg_eval.py skips turns already in each shard database).
seq 0 $((SHARDS - 1)) | xargs -P "$JOBS" -I{} sh -c \
  'GNUBG_EVAL_ARGS="$1 $2/s$3.db $3 $4 1 2 3" nice -n 19 gnubg -t -q -p tools/gnubg_eval.py > "$2/s$3.log" 2>&1' \
  _ "$SNAP" "$SCORES" {} "$SHARDS"
log "scored: $(awk '/decisions scored$/ { n += $(NF-2) } END { print n + 0 }' "$SCORES"/s*.log) new decisions"

# 3. Generate in the job's own clone, on top of the latest published page.
[ -d "$CLONE/.git" ] || git clone -q "$REMOTE" "$CLONE"
git -C "$CLONE" fetch -q origin main
git -C "$CLONE" checkout -q main
git -C "$CLONE" reset -q --hard origin/main
python3 tools/v3/page_v3.py "$SNAP" "$SCORES/s*.db" "$CLONE/backgammon/v3-results.json" "$CLONE/backgammon/index.html"
if grep -qE "$BANNED" "$CLONE/backgammon/v3-results.json" ||
   git -C "$CLONE" diff -U0 -- backgammon/index.html | grep '^+' | grep -qE "$BANNED"; then
  log "banned string in the generated page; not published"
  git -C "$CLONE" reset -q --hard origin/main
  exit 1
fi

# 4. Publish when the data changed.
AS_OF=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["data_as_of"].replace("T", " ").replace("Z", " UTC"))' \
  "$CLONE/backgammon/v3-results.json")
if [ -n "$(git -C "$CLONE" status --porcelain -- backgammon/v3-results.json)" ]; then
  git -C "$CLONE" add backgammon/v3-results.json backgammon/index.html
  git -C "$CLONE" commit -q -m "backgammon: v3 live data $AS_OF"
  for attempt in 1 2 3; do
    if git -C "$CLONE" push -q origin main; then
      log "pushed data as of $AS_OF"
      echo "$(date -u +%s) $AS_OF" >"$STATE/last_push"
      break
    fi
    [ "$attempt" = 3 ] && { log "push failed 3 times; next run retries"; exit 1; }
    git -C "$CLONE" pull -q --rebase origin main || { git -C "$CLONE" rebase --abort; log "rebase conflict; next run regenerates"; exit 1; }
  done
else
  log "no change (data as of $AS_OF)"
fi

# 5. Public check: once GitHub Pages and its CDN (max-age 600 s) have had 15 minutes after a push,
# the public URL, fetched as a visitor gets it, must show the pushed "data as of". Otherwise
# report it in mailbox/ (once per pushed value).
PUBLIC_URL=https://zekiworks.github.io/analysis/backgammon/
if [ -s "$STATE/last_push" ]; then
  read -r PUSHED_AT PUSHED_ASOF <"$STATE/last_push"
  if (( $(date -u +%s) - PUSHED_AT >= 900 )); then
    PUBLIC=$(curl -s -m 30 "$PUBLIC_URL" | python3 -c '
import re, sys, datetime
m = re.search(r"(?:Live|Final): data as of (\d+ \w+ \d{4}), (\d\d:\d\d) UTC", sys.stdin.read())
print(datetime.datetime.strptime(m[1] + " " + m[2], "%d %B %Y %H:%M").strftime("%Y-%m-%d %H:%M UTC") if m else "not found")')
    if [ "$PUBLIC" = "$PUSHED_ASOF" ]; then
      log "public check ok: $PUBLIC_URL shows data as of $PUBLIC"
    elif [ ! -e "$STATE/reported-$PUSHED_AT" ]; then
      log "public check FAILED: $PUBLIC_URL shows '$PUBLIC', pushed '$PUSHED_ASOF'"
      {
        echo "# Live page: public URL does not show the pushed data"
        echo
        echo "$(date -u '+%F %H:%M UTC'): $PUBLIC_URL shows data as of **$PUBLIC**; the update loop pushed **$PUSHED_ASOF** at $(date -u -d "@$PUSHED_AT" '+%F %H:%M UTC') (at least 15 minutes ago)."
        echo "Check the GitHub Pages runs (https://github.com/zekiworks/analysis/actions) and the CDN; the loop's log is v3-page-refresh.log."
      } >"$HOME/code/jevgammon/mailbox/Live page - public URL check failed.md"
      touch "$STATE/reported-$PUSHED_AT"
    fi
  fi
fi

# Done: leagues 2 and 3 finished and their final data is published.
if [ "$L2" = finished ] && [ "$L3" = finished ]; then
  log "leagues 2 and 3 finished and published; disabling v3-page-refresh.timer"
  systemctl --user disable --now v3-page-refresh.timer || log "could not disable the timer"
fi
log "done"
