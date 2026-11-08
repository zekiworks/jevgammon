#!/usr/bin/env bash
# Learning pilot smoke: shared T0, then series 1-3 of all four arms (Main's go, 2026-11-07).
set -euo pipefail
# The interpreter with tokenizers and numpy (the unit's default python3 has neither).
cd /home/cbasaran/code/jevgammon
echo "start $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py t0   # already done: returns at once
echo "t0 done $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py run --series 1-3
echo "smoke done $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py summary
