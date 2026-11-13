#!/usr/bin/env bash
# "Did they improve?" Phase 2, subscription lane: starts it as the systemd user unit improve-subs (transient, so a
# reboot loses it: run this again). One model at a time through run_queue.sh, in the order Main set: Antigravity
# (Gemini 3.8 Flash, Gemini 4 Argon), xAI (Grok 4.7), then Claude Code (Fable 5.1, Opus 5.5, Sonnet 5.5; Ümit #3465) last. Pinned
# runner binary jevgammon-1270c04. Claude: a 429 usage limit pauses the model ("usage limit"). Each model resumes
# from its stored state; an interrupted series is archived and replayed from game 1 with the same dice (plan §5).
#   workspace/improve/run_subs.sh            # start (refuses if the unit is already running)
set -euo pipefail
cd "$(dirname "$0")/../.."
BIN=$PWD/target/improve-bin/jevgammon-1270c04
[[ -x "$BIN" ]] || { echo "missing pinned binary $BIN" >&2; exit 1; }
if systemctl --user is-active -q improve-subs; then echo "improve-subs is already running" >&2; exit 1; fi
systemctl --user reset-failed improve-subs 2>/dev/null || true
systemd-run --user --unit improve-subs --description "Did they improve? subscription lane" \
  --setenv=PATH=/usr/games:/usr/local/bin:/usr/bin:/bin --setenv=IMPROVE_BIN="$BIN" \
  --property=WorkingDirectory="$PWD" \
  workspace/improve/run_queue.sh gemini-3.8-flash-high gemini-4-argon-on grok-4.7-on \
  claude-sonnet-5.5-high claude-opus-5.5-on claude-fable-5.1-on
