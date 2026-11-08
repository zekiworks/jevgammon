#!/usr/bin/env bash
# Nackgammon paired test, a late entry under Method §10.14(i) (2026-11-07): its 400 main positions, its first look,
# and the 600 reserve positions only when the frozen stopping rule extends it. Own roster and answers database
# (leagues/nack-paired-late.json, smoke/nack-paired-late.db); the 28 published setups' files are not touched.
# Binary: the late entries' league binary (target/drex/release, branch late-drex; prompts as the 2026-10-27 run).
#   tools/v3/nack_paired_late.sh "SETUP" [--max-cost USD] >> smoke/nack-paired-late-LOG.log 2>&1
S=${1:?usage: $0 SETUP [ask options]}
shift
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
export NACK_DB=smoke/nack-paired-late.db NACK_ROSTER=leagues/nack-paired-late.json
A=(ask --config "$NACK_ROSTER" --out "$NACK_DB" --time-limit 600 --setup "$S" "$@")
B=target/drex/release/jevgammon
echo "$(date -u +%FT%TZ) $S: main 400"
"$B" "${A[@]}" --positions positions/nack-paired/main.jsonl 2>&1 | grep "answered\|blocked\|rror\|CAP" | cut -c1-300
echo "$(date -u +%FT%TZ) $S: first look"
FL=$(/usr/bin/python3 tools/v3/nack_paired_score.py first-look | /usr/bin/python3 -c '
import sys; s = sys.argv[1]
print("".join(l for l in sys.stdin if l[:32].rstrip() == s and l[32:].lstrip().startswith("std")), end="")' "$S")
echo "$FL"
if grep -q "extend=True" <<<"$FL"; then
  echo "$(date -u +%FT%TZ) $S: extended, reserve 600"
  "$B" "${A[@]}" --positions positions/nack-paired/reserve.jsonl 2>&1 | grep "answered\|blocked\|rror\|CAP" | cut -c1-300
fi
echo "$(date -u +%FT%TZ) $S: done"
