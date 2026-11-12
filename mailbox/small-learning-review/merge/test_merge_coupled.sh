#!/usr/bin/env bash
# merge_coupled.sh on throwaway clones (git clone --shared of the two checkouts, under ~/.cache; the real checkouts are
# only read). Cases: dry run, pre-check refusals (not a fast-forward; target pin != target chat file), a failed second
# merge (first reset at once), a full merge, the rollback. Exit 0 when every case is as expected.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d "$HOME/.cache/merge-coupled-test.XXXXXX")
trap 'rm -rf "$T"' EXIT
git clone -q --shared "$HOME/code/jevgammon-improve" "$T/chat"
git clone -q --shared "$HOME/code/jevgammon-improve-decision" "$T/dec"
git -C "$T/chat" checkout -q -B improve a76fdc9
git -C "$T/dec" checkout -q -B improve-decision d9c3cbd
export CHAT_REPO=$T/chat DEC_REPO=$T/dec CHAT_TARGET=origin/improve-small-2 DEC_TARGET=origin/improve-decision-small
M="$HERE/merge_coupled.sh --no-fetch"
fail=0
heads() { echo "$(git -C "$T/chat" rev-parse --short HEAD) $(git -C "$T/dec" rev-parse --short HEAD)"; }
expect() {  # name, wanted exit, wanted heads ("" = any), command...
  local name=$1 want=$2 wh=$3; shift 3
  "$@" > "$T/out" 2>&1; local got=$?
  local h; h=$(heads)
  if [[ $got == "$want" && ( -z $wh || $h == "$wh" ) ]]; then echo "PASS  $name (exit $got, heads $h)"
  else echo "FAIL  $name: exit $got (want $want), heads $h (want $wh)"; cat "$T/out"; fail=1; fi
}
OLD="$(heads)"
NEW="$(git -C "$T/chat" rev-parse --short "$CHAT_TARGET") $(git -C "$T/dec" rev-parse --short "$DEC_TARGET")"
expect "dry run: plan only" 0 "$OLD" $M --dry-run
expect "target pin != target chat file: refused before any merge" 2 "$OLD" \
  env DEC_TARGET=origin/improve-decision-small~1 $M
git -C "$T/chat" commit -q --allow-empty -m "diverged"
expect "chat not a fast-forward: refused before any merge" 2 "$(heads)" $M
git -C "$T/chat" reset -q --hard a76fdc9
expect "second merge fails: decision reset at once" 3 "$OLD" env MC_FAIL_SECOND=1 $M
expect "full merge: both advanced, fence agrees" 0 "$NEW" $M
grep -q "fence pin 564312da" "$T/out" || { echo "FAIL  full merge: fence line"; fail=1; }
expect "rollback to the old heads" 0 "$OLD" $M --rollback a76fdc9 d9c3cbd
echo "tracked tree clean after all: $(git -C "$T/chat" status --porcelain -uno | wc -l) $(git -C "$T/dec" status --porcelain -uno | wc -l)"
exit $fail
