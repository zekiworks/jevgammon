"""Simulation worker, one shard per gnubg process:

    RS_DIR=<this folder> RS_SIM_ARGS="MODE OUT.jsonl SHARD SHARDS N [FIRST]" \
        nice -n 19 gnubg -t -q -p sim.py

MODE `rr`: replays FIRST..FIRST+N-1 of the round robin of common.PLAYERS under both schemes;
replay i's league seed is derive_seed(BASE, "replay i").
- Scheme A (the runner): match seed = derive_seed(league seed, "matchday D: M1 v M2"), round r
  rolls from round_seed(match seed, r).
- Scheme B (shared): round r of every match rolls from schedule r, round_seed(derive_seed(league
  seed, "shared schedule"), r); both games of the round use it with seats swapped, as in A. The
  stream is unbounded, so no game runs out of rolls.
Both schemes of replay i share the fixture (who is model1); the fixture does not affect results
beyond seat order.

MODE `long`: N independent matches for every pair of PLAYERS (k = FIRST..FIRST+N-1), match seed
derive_seed(BASE, "long A v B k"), model1 alternating with k: the long-run pairwise check.

One JSON line per job, appended and flushed, so a stopped run resumes by skipping done jobs.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.environ["RS_DIR"])

from common import PLAYERS, derive_seed, draw_fixture, play_match, round_seed  # noqa: E402

BASE = 20261020
CONTEXT = dict(PLAYERS)
NAMES = [n for n, _ in PLAYERS]

mode, out_path, shard, shards, n, *rest = os.environ["RS_SIM_ARGS"].split()
shard, shards, n = int(shard), int(shards), int(n)
first = int(rest[0]) if rest else 0

if mode == "rr":
    jobs = [("rr", s, i) for i in range(first, first + n) for s in "AB"]
else:
    pairs = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:]]
    jobs = [("long", a, b, k) for k in range(first, first + n) for a, b in pairs]
jobs = jobs[shard::shards]

done = set()
if os.path.exists(out_path):
    done = {tuple(json.loads(line)["job"]) for line in open(out_path)}
out = open(out_path, "a")


def run_rr(scheme, i):
    league = derive_seed(BASE, f"replay {i}")
    shared = derive_seed(league, "shared schedule")
    matches = []
    for day, m1, m2 in draw_fixture(NAMES, league):
        if scheme == "A":
            seed = derive_seed(league, f"matchday {day}: {m1} v {m2}")
            seed_of_round = lambda r, s=seed: round_seed(s, r)  # noqa: E731
        else:
            seed_of_round = lambda r: round_seed(shared, r)  # noqa: E731
        score, games_won, winner, games = play_match(CONTEXT[m1], CONTEXT[m2], seed_of_round)
        matches.append({"day": day, "m1": m1, "m2": m2, "score": score, "games_won": games_won,
                        "winner": winner, "games": games})
    return {"matches": matches}


def run_long(a, b, k):
    m1, m2 = (a, b) if k % 2 == 0 else (b, a)
    seed = derive_seed(BASE, f"long {a} v {b} {k}")
    score, games_won, winner, games = play_match(CONTEXT[m1], CONTEXT[m2],
                                                 lambda r: round_seed(seed, r))
    return {"m1": m1, "m2": m2, "score": score, "games_won": games_won, "winner": winner,
            "games": games}


for job in jobs:
    if tuple(job) in done:
        continue
    wall, cpu = time.time(), time.process_time()
    result = run_rr(*job[1:]) if job[0] == "rr" else run_long(*job[1:])
    result.update(job=list(job), wall=time.time() - wall, cpu=time.process_time() - cpu)
    out.write(json.dumps(result) + "\n")
    out.flush()
print(f"shard {shard}/{shards} done", flush=True)
