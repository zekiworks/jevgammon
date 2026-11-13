#!/usr/bin/env python3
"""Byte-identity replay of an original late entry's matches (read-only on v3.db; everything else in OUT).

  replay.py NAME MATCH,... BIN MODE OUT BASEPORT

MODE repeat:   the entrant as '<NAME> [repeat 1]' with the league config's pinned_pairs (each opponent pinned to its
               original match's seed and seating), as the repeat's league config pins them (new runner).
MODE original: the entrant under its own name and no pins (the original runners derive each pair's seed and seating
               from the two names and the rules, as the original league did).
Every player that requests (the entrant and the six API opponents) gets base_url = its own port of stub.py, which
answers each request with the stored response of the byte-identical stored request (400 for any other). The league
(scratch database OUT/replay.db, the original league's seed, option-order seed, prompt, rounds, turns and mirror rule)
plays the original's 9 pairs; then every stored exchange of each player is matched (as a multiset) against the bodies
its port received, and the replayed turns against the original turns (dice, position, option order, chosen play)."""
import collections
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

NAME, IDS, BIN, MODE, OUT, BASE = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3], sys.argv[4], \
    Path(sys.argv[5]), int(sys.argv[6])
HERE = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
v3 = sqlite3.connect("file:/home/cbasaran/code/jevgammon/v3.db?mode=ro", uri=True)
v3.row_factory = sqlite3.Row
me = v3.execute("SELECT id FROM players WHERE name = ?", (NAME,)).fetchone()[0]
matches = [dict(v3.execute("SELECT * FROM matches WHERE id = ?", (i,)).fetchone()) for i in IDS]
league = dict(v3.execute("SELECT * FROM leagues WHERE id = (SELECT league_id FROM league_players lp JOIN players p "
                         "ON p.id = lp.player_id WHERE p.name = ? ORDER BY lp.id DESC LIMIT 1)", (NAME,)).fetchone())
names = {r[0]: r[1] for r in v3.execute("SELECT id, name FROM players")}
settings = lambda n: json.loads(v3.execute("SELECT settings FROM players WHERE name = ?", (n,)).fetchone()[0])
entrant = NAME + " [repeat 1]" if MODE == "repeat" else NAME
opps = [names[m["player2"] if m["player1"] == me else m["player1"]] for m in matches]
requesting = [NAME] + [o for o in opps if o not in ("GNUbg weak", "Random", "Safest")]
ports = {n: BASE + i for i, n in enumerate(requesting)}
players = []
for n in [NAME] + opps:
    s = settings(n)
    if n in ports:
        url = f"http://127.0.0.1:{ports[n]}"
        s["base_url"] = url + "/v1" if s.get("base_url", "").endswith("/v1") else url
    if n == NAME:
        s["name"] = entrant
        s |= json.loads(os.environ.get("REPLAY_MUTATE", "{}"))  # negative control: a changed request setting
    players.append(s)
cfg = dict(note=f"byte-identity replay of {NAME} ({MODE})", prompt_version=league["prompt_version"],
           seed=league["seed"], order_seed=league["order_seed"], rounds=league["rounds"], clock=0, delay=30,
           max_turns=league["max_turns"], mirror_concurrent=bool(league["mirror_concurrent"]), only_pairs_of=entrant,
           hidden=True, players=players)
if MODE == "repeat":
    cfg["pinned_pairs"] = {o: dict(seed=m["seed"] & (2**64 - 1), seat_first=m["player1"] == me)
                           for o, m in zip(opps, matches)}
(OUT / "league.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
subprocess.run([sys.executable, str(HERE / "export.py"), NAME, *map(str, IDS)],
               stdout=open(OUT / "exchanges.json", "w"), check=True)
log = OUT / "stub.jsonl"
log.unlink(missing_ok=True)
stub = subprocess.Popen([sys.executable, str(HERE / "stub.py"), str(OUT / "exchanges.json"), str(log),
                         *(f"{n}={p}" for n, p in ports.items())], stdout=open(OUT / "stub.out", "w"),
                        stderr=subprocess.STDOUT)
time.sleep(2)
db = OUT / "replay.db"
for suffix in ("", "-wal", "-shm"):
    Path(f"{db}{suffix}").unlink(missing_ok=True)
env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
env |= {k: "replay-dummy" for k in ("TYPESAFE_API_KEY", "FASTINO_API_KEY", "LIQUID_API_KEY", "SUBQ_API_KEY",
                                     "CELERIS_API_KEY", "OPENROUTER_API_KEY")}
env["JEVGAMMON_DB"] = str(db)
t0 = time.time()
try:  # REPLAY_LEAGUE_TIMEOUT (seconds) bounds a negative control, whose refused requests back off for minutes
    league_exit = subprocess.run([BIN, "league", "--config", str(OUT / "league.json"), "--db", str(db)], cwd=OUT,
                                 env=env, stdout=open(OUT / "league.log", "w"), stderr=subprocess.STDOUT,
                                 timeout=int(os.environ.get("REPLAY_LEAGUE_TIMEOUT", 3600))).returncode
except subprocess.TimeoutExpired:
    league_exit = "stopped at REPLAY_LEAGUE_TIMEOUT"
took = time.time() - t0
stub.send_signal(signal.SIGTERM)
stub.wait()

# Exchanges: every stored request of each player against the bodies its port received (multiset, byte for byte).
data = json.load(open(OUT / "exchanges.json"))
got = collections.defaultdict(collections.Counter)
unmatched = collections.Counter()
warm = collections.Counter()
paths = collections.defaultdict(collections.Counter)
import hashlib
for line in open(log):
    r = json.loads(line)
    if r.get("warm_up"):
        warm[r["player"]] += 1
        continue
    got[r["player"]][r["sha256"]] += 1
    paths[r["player"]][r.get("path")] += 1
    if not r["matched"]:
        unmatched[r["player"]] += 1
per = {}
for n in ports:
    stored = collections.Counter(hashlib.sha256(e["request"].encode()).hexdigest()
                                 for e in data["exchanges"] if e["player"] == n)
    identical = sum(min(c, got[n][h]) for h, c in stored.items())
    per[n] = dict(stored=sum(stored.values()), received=sum(got[n].values()), identical=identical,
                  received_not_stored=unmatched[n], warm_ups=warm[n], paths=dict(paths[n]))

# Turns: the replayed matches' turns against the original's (dice, position, side, option order, chosen play).
rdb = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
rnames = {r[0]: r[1] for r in rdb.execute("SELECT id, name FROM players")}
turn_cols = "g.round_no, g.leg, t.turn_no, t.side, t.die1, t.die2, t.position, t.option_order, t.chosen_index, t.move"
def turns(conn, mid):
    return [tuple(r) for r in conn.execute(
        f"SELECT {turn_cols} FROM turns t JOIN games g ON g.id = t.game_id WHERE g.match_id = ? "
        "ORDER BY g.round_no, g.leg, t.turn_no", (mid,))]
pairs = []
for o, m in zip(opps, matches):
    row = rdb.execute("SELECT m.id, m.status, m.player1, m.player2, m.seed, m.score1, m.score2 FROM matches m JOIN "
                      "players a ON a.id = m.player1 JOIN players b ON b.id = m.player2 WHERE ? IN (a.name, b.name)",
                      (o,)).fetchone()
    if row is None:
        pairs.append(dict(opponent=o, original=m["id"], replay=None))
        continue
    a, b = turns(v3, m["id"]), turns(rdb, row[0])
    first = rnames[row[2]] == entrant
    pairs.append(dict(opponent=o, original=m["id"], replay=row[0], status=row[1],
                      seed_same=(row[4] & (2**64 - 1)) == (m["seed"] & (2**64 - 1)),
                      seat_same=first == (m["player1"] == me),
                      score_same=(row[5], row[6]) == (m["score1"], m["score2"]),
                      turns=(len(a), len(b)), turns_identical=a == b))
summary = dict(entrant=NAME, mode=MODE, binary=BIN, binary_sha256=hashlib.sha256(open(BIN, "rb").read()).hexdigest(),
               league_exit=league_exit, seconds=round(took, 1), exchanges=per, pairs=pairs)
(OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
print(json.dumps(summary, indent=1))
