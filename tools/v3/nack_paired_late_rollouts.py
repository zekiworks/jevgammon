"""Nackgammon paired test, late entries (Method §10.14(i)): the §10.12 engine check's missing rollouts.

    NACK_DB=smoke/nack-paired-late.db NACK_ROSTER=leagues/nack-paired-late.json \
        python3 tools/v3/nack_paired_late_rollouts.py prepare   # todo db + chosen.json of plays with no rollout
    V3_ARGS="rollout out=smoke/nack-engine-check-late-todo.db positions=positions/nack-paired/main.jsonl \
        chosen=smoke/nack-engine-check-late-chosen.json trials=1296 plies=1 threads=8 seed=1" \
        nice -n 19 gnubg -t -q -p tools/v3/score.py
    python3 tools/v3/nack_paired_late_rollouts.py merge     # todo rollouts into smoke/nack-engine-check-late.db

smoke/nack-engine-check-late.db starts as a copy of smoke/nack-engine-check-g.db (442 plays, unchanged); only the
late entries' chosen plays on the 40 frozen engine-check pairs that have no rollout yet are rolled out, alone (as
the 2026-10-28 additions' 6 plays were).
"""

import json
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import nack_paired_score as nps  # noqa: E402

BASE = "smoke/nack-engine-check-g.db"
LATE = "smoke/nack-engine-check-late.db"
TODO = "smoke/nack-engine-check-late-todo.db"
CHOSEN = "smoke/nack-engine-check-late-chosen.json"


def prepare():
    if not os.path.exists(LATE):
        shutil.copyfile(BASE, LATE)
    d = nps.Data()
    with open("freeze/nack-paired.json") as f:
        ec = set(json.load(f)["engine_check"]["pairs"])
    have = {(p, m) for p, m in sqlite3.connect(LATE).execute("SELECT position, play FROM rollouts")}
    todo = {}
    for p in d.main:
        if p["pair"] not in ec:
            continue
        for side in ("nackgammon", "standard"):
            pid = p[side]
            for s, a in d.answers.items():
                r = a.get(pid)
                if r is not None and r["error"] is None and not r["invalid"] and r["move"] in d.scores[pid]["plays"] \
                        and (pid, r["move"]) not in have:
                    todo.setdefault(pid, set()).add(r["move"])
    if os.path.exists(TODO):
        os.remove(TODO)
    con = sqlite3.connect(TODO)
    con.executescript("CREATE TABLE near_ties (position TEXT PRIMARY KEY, gap REAL, candidates TEXT);")
    for pid, plays in todo.items():
        con.execute("INSERT INTO near_ties VALUES (?,?,?)", (pid, None, json.dumps(sorted(plays))))
    con.commit()
    with open(CHOSEN, "w") as f:
        json.dump({p: sorted(m) for p, m in todo.items()}, f, indent=1)
    print(f"{sum(map(len, todo.values()))} plays on {len(todo)} positions to roll out")


def merge():
    con = sqlite3.connect(LATE)
    con.execute(f"ATTACH '{TODO}' AS t")
    n = con.execute("INSERT OR IGNORE INTO rollouts SELECT * FROM t.rollouts").rowcount
    con.commit()
    total = con.execute("SELECT count(*) FROM rollouts").fetchone()[0]
    print(f"merged {n} rollouts; {LATE} now holds {total} plays")


if __name__ == "__main__":
    {"prepare": prepare, "merge": merge}[sys.argv[1]]()
