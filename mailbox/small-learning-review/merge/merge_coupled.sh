#!/usr/bin/env bash
# Coupled fast-forward merge of the chat and decision "Did they improve?" branches (Zeki #5705): the decision lane's
# chat fence (decision.py CHAT_IMPROVE_SHA256) must always equal the sha256 of the chat checkout's improve.py; a
# mismatch pauses every decision arm. Never leaves one side merged:
#   1. both checkouts on their branch, no tracked change; targets fetched;
#   2. BEFORE either merge: both fast-forwards possible (git merge-base --is-ancestor HEAD target) and the targets
#      agree (target decision.py's pin == sha256 of target chat improve.py); else nothing is touched (exit 2);
#   3. decision merge, then chat merge; if the chat merge fails, the decision checkout is reset to its old head at once
#      (exit 3);
#   4. verify the working files agree (pin == chat improve.py); else both are reset to their old heads (exit 4);
#   5. print the rollback command (both old heads).
# --dry-run: steps 1-2 and the plan, nothing merged. --rollback OLD_CHAT OLD_DEC: reset both to those heads (decision
# first), then step 4 (exit 4 on mismatch). Pushes nothing. Run it right after a step_start of the running GPU 2 arm.
#   merge_coupled.sh [--dry-run|--no-fetch] [--rollback OLD_CHAT OLD_DEC]
# Defaults (override for tests): CHAT_REPO=~/code/jevgammon-improve CHAT_BRANCH=improve CHAT_TARGET=origin/improve-small-2
#   DEC_REPO=~/code/jevgammon-improve-decision DEC_BRANCH=improve-decision DEC_TARGET=origin/improve-decision-small
#   MC_FAIL_SECOND=1 (tests only): make the second merge fail.
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

if (( ${#ROLLBACK[@]} )); then
  log "rollback: decision $OLD_DEC -> ${ROLLBACK[1]}, chat $OLD_CHAT -> ${ROLLBACK[0]}"
  (( DRY )) && { log "dry run: nothing reset"; exit 0; }
  git -C "$DEC_REPO" reset -q --hard "${ROLLBACK[1]}" && git -C "$CHAT_REPO" reset -q --hard "${ROLLBACK[0]}" ||
    { log "ROLLBACK FAILED: check both checkouts now"; exit 4; }
  agree || { log "MISMATCH after rollback: the decision arms will pause; fix before anything else"; exit 4; }
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

git -C "$DEC_REPO" merge -q --ff-only "$NEW_DEC" || { log "FAILED: decision merge; nothing changed"; exit 3; }
second() { [[ ${MC_FAIL_SECOND:-0} == 1 ]] && return 1; git -C "$CHAT_REPO" merge -q --ff-only "$NEW_CHAT"; }
if ! second; then
  git -C "$DEC_REPO" reset -q --hard "$OLD_DEC"
  log "FAILED: chat merge; decision reset to $OLD_DEC"; agree || log "MISMATCH: check both checkouts now"; exit 3
fi
if ! agree; then
  git -C "$DEC_REPO" reset -q --hard "$OLD_DEC"; git -C "$CHAT_REPO" reset -q --hard "$OLD_CHAT"
  log "MISMATCH after merge: both reset to their old heads"; exit 4
fi
log "merged; fence and chat file agree. Rollback: $0 --rollback $OLD_CHAT $OLD_DEC"
