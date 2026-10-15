#!/usr/bin/env bash
cd /home/cbasaran/code/jevgammon
set -a; . ~/.keys; set +a
exec ./target/release/jevgammon league --config leagues/league1.json --db v3.db
