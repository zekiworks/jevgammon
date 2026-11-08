#!/usr/bin/env python3
"""Test double for `jevgammon ask` (test_improve.py only): writes answers like the runner (one row per position,
replacing an earlier row of the same setup and position), one simulated request at a time, with a ledger
reservation per request. FAKE_MODE: keylimit (3 answers, then every request refused 403 key limit), plain403 (every
request refused 403 invalid key), resume (asks only positions without an answer or with a failed one)."""
import json
import os
import sqlite3
import sys
import time

args = dict(zip(sys.argv[2::2], sys.argv[3::2]))
db = sqlite3.connect(args["--out"])
db.execute("CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY, setup TEXT, position_id TEXT, repeat INTEGER, "
           "chosen_index INTEGER, invalid INTEGER, error TEXT, in_flight INTEGER, cost_usd REAL)")
ids = [json.loads(line)["id"] for line in open(args["--positions"])]
setup, mode = args["--setup"], os.environ["FAKE_MODE"]
ledger = os.environ.get("FAKE_LEDGER")
log = open(os.environ["FAKE_DISPATCH_LOG"], "a")
if mode == "resume":
    done = {r[0] for r in db.execute("SELECT position_id FROM answers WHERE setup = ? AND error IS NULL", (setup,))}
    ids = [p for p in ids if p not in done]
KEY = ('qwen/qwen3.8-flash request failed: credential rejected: 403 Forbidden: {"error":{"message":"Key limit '
       'exceeded (total limit). Manage it using https://openrouter.ai/settings/keys","code":403}}')
BAD = 'qwen/qwen3.8-flash request failed: credential rejected: 403 Forbidden: {"error":{"message":"Invalid API key"}}'
for k, pid in enumerate(ids):
    log.write(pid + "\n")
    log.flush()
    if ledger:
        lg = sqlite3.connect(ledger)
        cur = lg.execute("INSERT INTO attempts (status, pid, reserved_usd) VALUES ('open', ?, 0.001)", (os.getpid(),))
        lg.commit()
    time.sleep(0.03)
    error = {"keylimit": KEY if k >= 3 else None, "plain403": BAD, "resume": None}[mode]
    if ledger:
        lg.execute("UPDATE attempts SET status = 'settled', cost_usd = ? WHERE id = ?",
                   (0.0 if error else 0.0005, cur.lastrowid))
        lg.commit()
        lg.close()
    db.execute("DELETE FROM answers WHERE setup = ? AND position_id = ?", (setup, pid))
    db.execute("INSERT INTO answers (setup, position_id, repeat, chosen_index, invalid, error, in_flight) "
               "VALUES (?, ?, 1, ?, 0, ?, 1)", (setup, pid, None if error else 0, error))
    db.commit()
    time.sleep(0.02)
