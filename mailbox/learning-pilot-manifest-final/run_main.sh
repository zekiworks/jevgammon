#!/usr/bin/env bash
# Learning pilot series 4-10 (Main's go after the clean smoke, 2026-11-07).
set -euo pipefail
# The interpreter with tokenizers and numpy (the unit's default python3 has neither).
cd /home/cbasaran/code/jevgammon
echo "start $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py t0   # already done: returns at once
echo "t0 done $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py run --series 4-10
echo "series 4-10 done $(date -u +%FT%TZ)"
/home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/pilot.py summary
