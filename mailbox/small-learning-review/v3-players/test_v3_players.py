"""Scratch-DB tests of v3_players.py (no production write): python3 -m unittest -v test_v3_players.py
The scratch schema is v3.db's own (read-only from sqlite_master); two scenarios also copy today's players rows."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v3_players as P  # noqa: E402

V3 = "/home/cbasaran/code/jevgammon/v3.db"


def scratch(copy_players=False):
    """An in-memory DB with v3.db's tables (schema read-only from production); nothing touches disk."""
    prod = sqlite3.connect(f"file:{V3}?mode=ro", uri=True, timeout=60)
    schema = [r[0] for r in prod.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL "
                                         "AND name NOT LIKE 'sqlite_%'")]
    players = prod.execute("SELECT * FROM players").fetchall() if copy_players else []
    prod.close()
    db = sqlite3.connect(":memory:")
    for s in schema:
        db.execute(s)
    if players:
        db.executemany(f"INSERT INTO players VALUES ({','.join('?' * len(players[0]))})", players)
    db.commit()
    return db


class Players(unittest.TestCase):
    def setUp(self):
        self.rows = P.load_rows(HERE / "rows.json")

    def test_insert_is_exact_and_idempotent(self):
        db = scratch()
        after, before = P.insert(db, self.rows)
        self.assertEqual([a for a, _, _ in before], ["insert"] * len(self.rows))
        for r in self.rows:
            s = r["settings"]
            row = db.execute("SELECT spec, provider, quantization, device, price, settings FROM players WHERE name = ?",
                             (s["name"],)).fetchone()
            self.assertEqual(row[:5], (s["spec"], s.get("provider"), s.get("quantization"), s.get("device"), None))
            self.assertEqual(row[5], json.dumps(s, separators=(",", ":"), ensure_ascii=False))
            self.assertEqual(json.loads(row[5]), s)
        ids = [i for _, _, i in after]
        again, _ = P.insert(db, self.rows)
        self.assertEqual([(a, i) for a, _, i in again], [("same", i) for i in ids])
        self.assertEqual(db.execute("SELECT count(*) FROM players").fetchone()[0], len(self.rows))

    def test_a_name_with_other_settings_is_refused_and_nothing_is_written(self):
        db = scratch()
        s = dict(self.rows[1]["settings"], max_tokens=1)
        db.execute("INSERT INTO players (name, spec, settings, created_at) VALUES (?, ?, ?, 't')",
                   (s["name"], s["spec"], json.dumps(s)))
        db.commit()
        with self.assertRaises(SystemExit):
            P.insert(db, self.rows)
        self.assertEqual(db.execute("SELECT count(*) FROM players").fetchone()[0], 1)

    def test_on_todays_players_it_only_adds_and_changes_no_row(self):
        db = scratch(copy_players=True)
        before = db.execute("SELECT * FROM players ORDER BY id").fetchall()
        self.assertEqual([a for a, _, _ in P.plan(db, self.rows)], ["insert"] * len(self.rows))
        P.insert(db, self.rows)
        after = db.execute("SELECT * FROM players ORDER BY id").fetchall()
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(len(after), len(before) + len(self.rows))

    def test_rollback_deletes_exactly_these_rows_and_refuses_when_referenced(self):
        db = scratch(copy_players=True)
        n0 = db.execute("SELECT count(*) FROM players").fetchone()[0]
        after, _ = P.insert(db, self.rows)
        used = after[0][2]
        db.execute("INSERT INTO league_players (league_id, player_id, joined_at) VALUES (1, ?, 't')", (used,))
        db.commit()
        with self.assertRaises(SystemExit):
            P.rollback(db, self.rows)
        self.assertEqual(db.execute("SELECT count(*) FROM players").fetchone()[0], n0 + len(self.rows))
        db.execute("DELETE FROM league_players WHERE player_id = ?", (used,))
        db.commit()
        self.assertEqual(len(P.rollback(db, self.rows)), len(self.rows))
        self.assertEqual(db.execute("SELECT count(*) FROM players").fetchone()[0], n0)


if __name__ == "__main__":
    unittest.main()
