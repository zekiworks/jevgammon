#!/usr/bin/env bash
# Nackgammon paired test, a setup added under Method §10.14(g) (2026-10-28): its 400 main positions,
# its first look, and the 600 reserve positions only when the frozen stopping rule extends it.
# Same runner binary, config, answers database and time limit as the original run (NackRun).
#   tools/v3/nack_paired_add.sh "SETUP" >> smoke/nack-paired-g-LOG.log 2>&1
S=${1:?usage: $0 SETUP}
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
[ -n "${FASTINO_API_KEY:-}" ] || { FASTINO_API_KEY="$(cat ~/.config/fastino/key)"; export FASTINO_API_KEY; }
export PATH=$HOME/.local/bin:$PATH   # Grok: OMP refreshes its xai-oauth login (`omp token`)
A=(ask --config leagues/nack-paired.json --out smoke/nack-paired.db --time-limit 600 --setup "$S")
B=target/nack/release/jevgammon
echo "$(date -u +%FT%TZ) $S: main 400"
"$B" "${A[@]}" --positions positions/nack-paired/main.jsonl 2>&1 | grep "answered\|blocked\|rror" | cut -c1-300
echo "$(date -u +%FT%TZ) $S: first look"
FL=$(python3 tools/v3/nack_paired_score.py first-look | python3 -c '
import sys; s = sys.argv[1]
print("".join(l for l in sys.stdin if l[:32].rstrip() == s and l[32:].lstrip().startswith("std")), end="")' "$S")
echo "$FL"
if grep -q "extend=True" <<<"$FL"; then
  echo "$(date -u +%FT%TZ) $S: extended, reserve 600"
  "$B" "${A[@]}" --positions positions/nack-paired/reserve.jsonl 2>&1 | grep "answered\|blocked\|rror" | cut -c1-300
fi
echo "$(date -u +%FT%TZ) $S: done"
