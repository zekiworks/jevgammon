#!/usr/bin/env bash
# Part A smoke tests (workspace/backgammon-site-brief.md): candidate models on the 50 smoke
# positions through `jevgammon ask`, then the paired table.
#
#   tools/v3/smoke_parta.sh api                  # every setup of leagues/smoke-parta.json
#   D3_GPU=N tools/v3/smoke_parta.sh d3          # d3-turbo: start server, ask, stop
#   NEMOTRON_GPUS=N tools/v3/smoke_parta.sh nemotron   # Nemotron 3.5 Bolt 24GB (off, on), one GPU
#   NEMOTRON_GPUS=N,M tools/v3/smoke_parta.sh nemotron-bf16   # Nemotron 3.5 Bolt BF16 (off, on), TP2
#   tools/v3/smoke_parta.sh report               # table (stdout) + smoke/part-a.json
#
# The runner is built apart from the leagues' binary (target/release stays untouched):
#   CARGO_TARGET_DIR=target/parta cargo build --release
# Answers go to smoke/part-a.db (a rerun asks only what is missing or failed). Each decision
# has a 600 s wall-clock limit; one over it is stored as timed out, not invalid.
set -euo pipefail
cd "$(dirname "$0")/../.."
BIN=target/parta/release/jevgammon
ASK=("$BIN" ask --positions positions/smoke.jsonl --out smoke/part-a.db --time-limit 600 --max-cost 4.0)
[[ -x $BIN ]] || { echo "build first: CARGO_TARGET_DIR=target/parta cargo build --release" >&2; exit 1; }

case "${1:-}" in
  api)
    set -a; . ~/.keys; set +a
    "${ASK[@]}" --config leagues/smoke-parta.json
    ;;
  d3)
    : "${D3_GPU:?set D3_GPU to a free GPU}"
    tools/v3/servers/d3-turbo.sh start
    tools/v3/servers/d3-turbo.sh probe
    "${ASK[@]}" --config leagues/smoke-parta-d3.json
    tools/v3/servers/d3-turbo.sh stop
    ;;
  nemotron | nemotron-bf16)
    : "${NEMOTRON_GPUS:?set NEMOTRON_GPUS to a free GPU (two for nemotron-bf16)}"
    if [[ $1 == nemotron ]]; then
      export NEMOTRON_CHECKPOINT=24gb; config=leagues/smoke-parta-nemotron.json
    else
      export NEMOTRON_CHECKPOINT=bf16; config=leagues/smoke-parta-nemotron-bf16.json
    fi
    tools/v3/servers/nemotron35-bolt.sh fetch
    tools/v3/servers/nemotron35-bolt.sh start
    tools/v3/servers/nemotron35-bolt.sh probe
    "${ASK[@]}" --config "$config"
    tools/v3/servers/nemotron35-bolt.sh stop
    ;;
  report)
    python3 tools/v3/smoke_report.py paired --score smoke/score.db \
      --setups leagues/smoke-parta.json=smoke/part-a.db \
      --setups leagues/smoke-parta-d3.json=smoke/part-a.db \
      --setups leagues/smoke-parta-nemotron.json=smoke/part-a.db \
      --setups leagues/smoke-parta-nemotron-bf16.json=smoke/part-a.db \
      --reference "Gemini 3.8 Flash (low) [antigravity]=smoke/part-a.db" \
      --reference "Gemini 3.8 Flash (low)=smoke/answers.db" \
      --json smoke/part-a.json
    ;;
  *)
    sed -n '2,14p' "$0"; exit 2 ;;
esac
