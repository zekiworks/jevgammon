#!/usr/bin/env bash
# Runs the experiment under nice with at most 24 gnubg processes, then the analysis:
#   ./run.sh pr          # v1-set PR of the candidate configurations (pr.py)
#   ./run.sh rr N        # N replays of the round robin per scheme into data/main
#   ./run.sh long N      # N independent matches per pair into data/long
#   ./run.sh report      # analyze.py on data/main and data/long
# Output folders resume: done jobs are skipped. Wall and CPU (user + sys of the gnubg
# processes) go to data/runtime.txt.
set -euo pipefail
cd "$(dirname "$0")"
export RS_DIR=$PWD
SHARDS=24
TIMEFORMAT="%R s wall, %U s user, %S s sys"

run_shards() {  # MODE DIR N
    mkdir -p "data/$2"
    for s in $(seq 0 $((SHARDS - 1))); do
        RS_SIM_ARGS="$1 data/$2/$1.$s.jsonl $s $SHARDS $3" nice -n 19 gnubg -t -q -p sim.py \
            > "data/$2/$1.$s.log" 2>&1 &
    done
    wait
}

case "$1" in
pr)
    mkdir -p data/pr
    names=("0p n0.000" "0p n0.005" "0p n0.010" "0p n0.015" "0p n0.020" "0p n0.025" "0p n0.030"
           "0p n0.035" "0p n0.040" "0p n0.045" "0p n0.050" "0p n0.055" "0p n0.060" "0p n0.070"
           "0p n0.080" "0p n0.100" "0p n0.120" "1p n0.000" "1p prune n0.000" "1p n0.020"
           "0p n0.030 nondet" "0p n0.060 nondet")
    { time {
        for i in "${!names[@]}"; do
            RS_PR_ARGS="data/pr/$i.json|${names[$i]}" nice -n 19 gnubg -t -q -p pr.py \
                > "data/pr/$i.log" 2>&1 &
        done
        wait
    } ; } 2>> data/runtime.txt.tmp
    echo "pr: $(tail -n 1 data/runtime.txt.tmp)" >> data/runtime.txt
    ;;
rr | long)
    dir=$([ "$1" = rr ] && echo main || echo long)
    { time run_shards "$1" "$dir" "$2" ; } 2>> data/runtime.txt.tmp
    echo "$1 $2: $(tail -n 1 data/runtime.txt.tmp)" >> data/runtime.txt
    ;;
report)
    python3 analyze.py data/main data/long
    ;;
esac
