#!/usr/bin/env python3
"""Billable input tokens per request body byte of the paid opponents (Zeki #10299), read-only on v3.db: the bound behind
the run guard's input_bytes_factor (smallchat.py guard). The guard reserves every request against its own body, so the
ratio that matters is per request: usage.input_tokens of each answered exchange / length of its request body. The
per-turn ratio (turns.input_tokens, which adds up every request of a split decision, / the turn's last request body) is
printed beside it to show why it is not a per-request bound (a split decision's last request is its small final round).

  input_ratio.py [--db V3DB] [--from-turn ID] [NAME ...]   (default: the paid opponents of the small chat configs)
"""
import argparse
import sqlite3

PAID = ["Celeris-1 Decision", "Fastino GLiDE", "Jev 1.13.0", "Jev 1.14.0", "Liquid d1-ultra", "Mercury Decide",
        "SubQ Snap Preview"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="/home/cbasaran/code/jevgammon/v3.db")
    ap.add_argument("--from-turn", type=int, default=360000)
    ap.add_argument("names", nargs="*", default=PAID)
    args = ap.parse_args()
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=60)
    q = ",".join("?" * len(args.names))
    rows = {r[0]: r[1:] for r in conn.execute(f"""
        WITH tt AS (
          SELECT t.id, t.input_tokens, p.name FROM turns t JOIN games g ON g.id = t.game_id
          JOIN matches m ON m.id = g.match_id
          JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
          WHERE t.id >= ? AND m.stage = 'late-entry' AND p.name IN ({q})),
        ex AS (
          SELECT e.turn_id, length(e.request) AS bytes, json_extract(e.response, '$.usage.input_tokens') AS tokens,
                 ROW_NUMBER() OVER (PARTITION BY e.turn_id ORDER BY e.attempt DESC, e.id DESC) AS last
          FROM exchanges e WHERE e.turn_id IN (SELECT id FROM tt))
        SELECT tt.name, COUNT(DISTINCT tt.id), COUNT(ex.tokens), MAX(1.0 * ex.tokens / ex.bytes),
               MAX(CASE ex.last WHEN 1 THEN 1.0 * tt.input_tokens / ex.bytes END)
        FROM tt JOIN ex ON ex.turn_id = tt.id GROUP BY tt.name""", [args.from_turn, *args.names])}
    print(f"late-entry turns from id {args.from_turn} ({args.db}, read-only)")
    print(f"{'setup':<20} {'turns':>6} {'requests':>9} {'max tokens/byte per request':>28} {'per turn (not a bound)':>23}")
    for name in args.names:
        if name not in rows:
            print(f"{name:<20} {'0':>6} {'0':>9} {'no data':>28} {'-':>23}")
            continue
        turns, requests, per_request, per_turn = rows[name]
        print(f"{name:<20} {turns:>6} {requests:>9} {per_request or 0:>28.3f} {per_turn or 0:>23.3f}")


if __name__ == "__main__":
    main()
