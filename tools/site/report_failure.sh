#!/usr/bin/env bash
# The update loop reports its own failures (brief v6 B1): writes why the last run stopped to
#   mailbox/Backgammon site preview - update loop failed.md
# Called by update.sh's ERR trap (with the reason) and by systemd's OnFailure= unit (bg-site-preview-failed.service),
# which also catches what the trap cannot: a killed run, a timeout, a crash before the trap is set.
# A later successful run removes the file (update.sh).
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE=${XDG_STATE_HOME:-$HOME/.local/state}/bg-site
OUT="$ROOT/mailbox/Backgammon site preview - update loop failed.md"
REASON=${1:-"systemd marked bg-site-preview.service as failed"}
{
  echo "# Backgammon site preview: the update loop failed"
  echo
  echo "$(date -u '+%F %H:%M UTC'). Reason: $REASON."
  echo "The preview keeps its last good build. The timer (bg-site-preview.timer) still fires every 15 minutes and the"
  echo "next run retries; this file goes away after the next successful run."
  echo
  echo "Last lines of the loop's log:"
  echo
  echo '```'
  tail -25 "$STATE/update.log" 2>/dev/null
  echo '```'
  if command -v systemctl >/dev/null; then
    echo
    echo "Service status:"
    echo
    echo '```'
    systemctl --user status bg-site-preview.service --no-pager 2>&1 | head -15
    echo '```'
  fi
} > "$OUT"
