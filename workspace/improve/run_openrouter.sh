#!/usr/bin/env bash
# "Did they improve?" Phase 2, OpenRouter lane: starts it as the systemd user unit improve-openrouter (transient, so a
# reboot loses it: run this again). One model at a time through run_queue.sh, cheapest first: Qwen3.8 Flash,
# GLM-5.3, then by leaderboard rank (Ümit #3465): DeepSeek V4.1 Flash, Kimi K3.1 Pro, under the plan's money rules (live balance - $5, the share, $110,
# 1.5x per model) and the key/credit-limit pause. Pinned runner binary jevgammon-8b6f9a1 (1270c04 + the 200-error-reply
# fix, QC 2026-11-12; was jevgammon-1270c04 until then). A model with an operator hold
# (runs/<key>/hold.json) pauses before its next step; the queue stops there.
#   workspace/improve/run_openrouter.sh      # start (refuses if the unit is already running)
set -euo pipefail
cd "$(dirname "$0")/../.."
BIN=$PWD/target/improve-bin/jevgammon-8b6f9a1
[[ -x "$BIN" ]] || { echo "missing pinned binary $BIN" >&2; exit 1; }
if systemctl --user is-active -q improve-openrouter; then echo "improve-openrouter is already running" >&2; exit 1; fi
systemctl --user reset-failed improve-openrouter 2>/dev/null || true
systemd-run --user --unit improve-openrouter --description "Did they improve? OpenRouter lane" \
  --setenv=PATH=/usr/games:/usr/local/bin:/usr/bin:/bin --setenv=IMPROVE_BIN="$BIN" \
  --property=WorkingDirectory="$PWD" \
  workspace/improve/run_queue.sh qwen3.8-flash-off glm-5.3-on deepseek-v4.1-flash-on kimi-k3.1-pro-off
