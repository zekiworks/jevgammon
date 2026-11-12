#!/usr/bin/env bash
# Coupled fast-forward merge of the chat and decision "Did they improve?" branches (Zeki #5705): the decision lane's
# chat fence (decision.py CHAT_IMPROVE_SHA256) must always equal the sha256 of the chat checkout's improve.py; a
# mismatch pauses every decision arm. Never leaves one side merged:
#   1. both checkouts on their branch, no tracked change; targets fetched;
#   2. BEFORE either merge: both fast-forwards possible (git merge-base --is-ancestor HEAD target) and the targets
#      agree (target decision.py's pin == sha256 of target chat improve.py); else nothing is touched (exit 2);
#   3. decision merge, then chat merge; if the chat merge fails, the decision checkout is restored to its old head at
#      once (exit 3);
#   4. verify the working files agree (pin == chat improve.py); else both are restored to their old heads (exit 4);
#   5. print the rollback command (both old heads). Every failure ends with one STATE line (both heads, agree or not).
# --dry-run: steps 1-2 and the plan, nothing changed. --rollback OLD_CHAT OLD_DEC (Zeki #5763: the same paired-update
# safety): BEFORE either reset, both targets must be commits of their repository and must agree (target pin == target
# chat improve.py), else nothing is reset (exit 2); decision reset, then chat reset; if the chat reset fails, the
# decision checkout is restored to the head it had before the rollback (exit 3); post-check as step 4, both restored
# on a mismatch (exit 4). Pushes nothing. Run it right after a step_start of the running GPU 2 arm.
#   merge_coupled.sh [--dry-run|--no-fetch] [--rollback OLD_CHAT OLD_DEC]
# Defaults (override for tests): CHAT_REPO=~/code/jevgammon-improve CHAT_BRANCH=improve CHAT_TARGET=origin/improve-small-2
#   DEC_REPO=~/code/jevgammon-improve-decision DEC_BRANCH=improve-decision DEC_TARGET=origin/improve-decision-small
#   Tests only: MC_FAIL_SECOND=1 fails the second update (merge or reset); MC_BREAK_AFTER=1 changes the chat file after
#   both updates (a pin mismatch for the post-check).
set -uo pipefail
CHAT_REPO=${CHAT_REPO:-$HOME/code/jevgammon-improve}; CHAT_BRANCH=${CHAT_BRANCH:-improve}
CHAT_TARGET=${CHAT_TARGET:-origin/improve-small-2}
DEC_REPO=${DEC_REPO:-$HOME/code/jevgammon-improve-decision}; DEC_BRANCH=${DEC_BRANCH:-improve-decision}
DEC_TARGET=${DEC_TARGET:-origin/improve-decision-small}
CHAT_FILE=workspace/improve/improve.py; DEC_FILE=workspace/improve/decision.py
DRY=0; FETCH=1; ROLLBACK=()
while (( $# )); do
  case $1 in
    --dry-run) DRY=1 ;;
    --no-fetch) FETCH=0 ;;
    --rollback) ROLLBACK=("$2" "$3"); shift 2 ;;
    *) echo "usage: $0 [--dry-run|--no-fetch] [--rollback OLD_CHAT OLD_DEC]" >&2; exit 64 ;;
  esac
  shift
done
log() { echo "$(date -u +%FT%TZ) $*"; }
pin_of() { sed -n 's/^CHAT_IMPROVE_SHA256 = "\([0-9a-f]\{64\}\)".*/\1/p' "$1"; }
pin_at() { git -C "$DEC_REPO" show "$1:$DEC_FILE" | sed -n 's/^CHAT_IMPROVE_SHA256 = "\([0-9a-f]\{64\}\)".*/\1/p'; }
sha_at() { git -C "$CHAT_REPO" show "$1:$CHAT_FILE" | sha256sum | cut -d' ' -f1; }
agree() {  # the working files: pin == chat improve.py
  local pin sha
  pin=$(pin_of "$DEC_REPO/$DEC_FILE"); sha=$(sha256sum "$CHAT_REPO/$CHAT_FILE" | cut -d' ' -f1)
  log "fence pin $pin, chat improve.py $sha"
  [[ -n $pin && $pin == "$sha" ]]
}
for r in "$CHAT_REPO:$CHAT_BRANCH" "$DEC_REPO:$DEC_BRANCH"; do
  repo=${r%%:*} br=${r##*:}
  [[ $(git -C "$repo" symbolic-ref --short HEAD 2>/dev/null) == "$br" ]] || { log "REFUSED: $repo is not on $br"; exit 2; }
  git -C "$repo" diff --quiet HEAD -- || { log "REFUSED: $repo has tracked changes"; exit 2; }
done
OLD_CHAT=$(git -C "$CHAT_REPO" rev-parse HEAD); OLD_DEC=$(git -C "$DEC_REPO" rev-parse HEAD)
state() {  # the clear end state, whatever happened
  local s="MISMATCH: the decision arms pause at their next billed step; fix before anything else"
  agree && s="fence and chat file agree"
  log "STATE: chat $(git -C "$CHAT_REPO" rev-parse --short HEAD), decision $(git -C "$DEC_REPO" rev-parse --short HEAD); $s"
}
restore() {  # both checkouts back to the heads they had when this run started
  git -C "$DEC_REPO" reset -q --hard "$OLD_DEC"; local a=$?
  git -C "$CHAT_REPO" reset -q --hard "$OLD_CHAT"; local b=$?
  (( a == 0 && b == 0 )) || log "RESTORE FAILED (decision $a, chat $b)"
}
# Test hooks only: MC_FAIL_SECOND=1 fails the second update (merge or reset); MC_BREAK_AFTER=1 changes the chat file
# after both updates, so the post-check sees a pin mismatch.
second_fails() { [[ ${MC_FAIL_SECOND:-0} == 1 ]]; }
break_after() { [[ ${MC_BREAK_AFTER:-0} == 1 ]] && echo "# test hook" >> "$CHAT_REPO/$CHAT_FILE"; return 0; }

if (( ${#ROLLBACK[@]} )); then
  # Same paired-update safety as the merge: both targets must be commits of their repository and must agree (the
  # target decision.py pin == the target chat improve.py) BEFORE either reset.
  TO_CHAT=$(git -C "$CHAT_REPO" rev-parse -q --verify "${ROLLBACK[0]}^{commit}") ||
    { log "REFUSED: chat ${ROLLBACK[0]} is not a commit here; nothing reset"; exit 2; }
  TO_DEC=$(git -C "$DEC_REPO" rev-parse -q --verify "${ROLLBACK[1]}^{commit}") ||
    { log "REFUSED: decision ${ROLLBACK[1]} is not a commit here; nothing reset"; exit 2; }
  want=$(pin_at "$TO_DEC"); have=$(sha_at "$TO_CHAT")
  [[ -n $want && $want == "$have" ]] ||
    { log "REFUSED: rollback target pin ${want:-none} != target chat improve.py $have; nothing reset"; exit 2; }
  log "rollback plan: decision $OLD_DEC -> $TO_DEC, chat $OLD_CHAT -> $TO_CHAT (fence pin $want)"
  (( DRY )) && { log "dry run: nothing reset"; exit 0; }
  git -C "$DEC_REPO" reset -q --hard "$TO_DEC" || { log "FAILED: decision reset"; restore; state; exit 3; }
  if second_fails || ! git -C "$CHAT_REPO" reset -q --hard "$TO_CHAT"; then
    log "FAILED: chat reset; restoring the decision checkout to $OLD_DEC"; restore; state; exit 3
  fi
  break_after
  if ! agree; then log "MISMATCH after rollback: both restored to the heads before it"; restore; state; exit 4; fi
  log "rolled back; fence and chat file agree"; exit 0
fi

if (( FETCH )); then git -C "$CHAT_REPO" fetch -q && git -C "$DEC_REPO" fetch -q || { log "REFUSED: fetch failed"; exit 2; }; fi
NEW_CHAT=$(git -C "$CHAT_REPO" rev-parse "$CHAT_TARGET") && NEW_DEC=$(git -C "$DEC_REPO" rev-parse "$DEC_TARGET") ||
  { log "REFUSED: a target does not resolve"; exit 2; }
git -C "$CHAT_REPO" merge-base --is-ancestor HEAD "$NEW_CHAT" || { log "REFUSED: chat $CHAT_TARGET is not a fast-forward of HEAD; nothing merged"; exit 2; }
git -C "$DEC_REPO" merge-base --is-ancestor HEAD "$NEW_DEC" || { log "REFUSED: decision $DEC_TARGET is not a fast-forward of HEAD; nothing merged"; exit 2; }
want=$(pin_at "$NEW_DEC"); have=$(sha_at "$NEW_CHAT")
[[ -n $want && $want == "$have" ]] || { log "REFUSED: target pin $want != target chat improve.py $have; nothing merged"; exit 2; }
log "plan: decision $OLD_DEC -> $NEW_DEC, chat $OLD_CHAT -> $NEW_CHAT (fence pin $want)"
(( DRY )) && { log "dry run: nothing merged"; exit 0; }

git -C "$DEC_REPO" merge -q --ff-only "$NEW_DEC" || { log "FAILED: decision merge; nothing changed"; state; exit 3; }
if second_fails || ! git -C "$CHAT_REPO" merge -q --ff-only "$NEW_CHAT"; then
  log "FAILED: chat merge; decision reset to $OLD_DEC"; restore; state; exit 3
fi
break_after
if ! agree; then log "MISMATCH after merge: both reset to their old heads"; restore; state; exit 4; fi
log "merged; fence and chat file agree. Rollback: $0 --rollback $OLD_CHAT $OLD_DEC"
