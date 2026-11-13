#!/usr/bin/env python3
"""Export the stored exchanges of one original's matches from v3.db (read-only) for the replay stub.

  export.py NAME MATCH_ID... > exchanges.json

Writes {"entrant": NAME, "matches": [...], "exchanges": [{"turn": id, "attempt": n, "player": name,
"match": id, "request": text, "response": text, "error": text}]} in exchange id order."""
import json
import sqlite3
import sys

name, ids = sys.argv[1], [int(x) for x in sys.argv[2:]]
conn = sqlite3.connect("file:/home/cbasaran/code/jevgammon/v3.db?mode=ro", uri=True)
rows = conn.execute(
    f"""SELECT e.id, t.id, e.attempt, p.name, g.match_id, e.request, e.response, e.error
        FROM exchanges e JOIN turns t ON t.id = e.turn_id JOIN games g ON g.id = t.game_id
        JOIN matches m ON m.id = g.match_id
        JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
        WHERE g.match_id IN ({",".join("?" * len(ids))}) ORDER BY e.id""", ids).fetchall()
json.dump(dict(entrant=name, matches=ids, exchanges=[
    dict(id=r[0], turn=r[1], attempt=r[2], player=r[3], match=r[4], request=r[5], response=r[6], error=r[7])
    for r in rows]), sys.stdout)
