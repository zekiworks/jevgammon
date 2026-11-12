"""Scratch-DB tests of v3_players.py (no production write): python3 -B -m unittest -v test_v3_players.py
Scratch DBs have v3.db's own schema (read-only from production), foreign keys ON as the script's own connections,
and live in memory or under ~/.cache (never /tmp); two scenarios copy today's players rows."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v3_players as P  # noqa: E402

V3 = "/home/cbasaran/code/jevgammon/v3.db"
CACHE = Path.home() / ".cache"


def scratch(copy_players=False, path=":memory:"):
    prod = sqlite3.connect(f"file:{V3}?mode=ro", uri=True, timeout=60)
    schema = [r[0] for r in prod.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL "
                                         "AND name NOT LIKE 'sqlite_%'")]
    players = prod.execute("SELECT * FROM players").fetchall() if copy_players else []
    prod.close()
    db = sqlite3.connect(str(path))
    for s in schema:
        db.execute(s)
    if players:
        db.executemany(f"INSERT INTO players VALUES ({','.join('?' * len(players[0]))})", players)
    db.execute("INSERT INTO leagues (id, started_at, seed, rounds, status) VALUES (1, 't', 1, 3, 'done')")
    db.commit()
    db.execute("PRAGMA foreign_keys = ON")
    return db


def count(db):
    return db.execute("SELECT count(*) FROM players").fetchone()[0]


def reference(db, pid):
    db.execute("INSERT INTO league_players (league_id, player_id, joined_at) VALUES (1, ?, 't')", (pid,))
    db.commit()


class Players(unittest.TestCase):
    def setUp(self):
        self.rows = P.load_rows(HERE / "rows.json")
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.manifest = Path(self.tmp.name) / "manifest.json"
        self.dbp = Path(self.tmp.name) / "scratch.db"  # the manifest's db field; the DB itself may be in memory

    def tearDown(self):
        self.tmp.cleanup()

    def test_insert_is_exact_idempotent_and_records_only_its_own_rows(self):
        db = scratch()
        actions, new = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        self.assertEqual([a for a, _, _ in actions], ["insert"] * len(self.rows))
        for r in self.rows:
            s = r["settings"]
            row = db.execute("SELECT spec, provider, quantization, device, price, settings FROM players WHERE name = ?",
                             (s["name"],)).fetchone()
            self.assertEqual(row[:5], (s["spec"], s.get("provider"), s.get("quantization"), s.get("device"), None))
            self.assertEqual(row[5], json.dumps(s, separators=(",", ":"), ensure_ascii=False))
        doc = json.loads(self.manifest.read_text())
        self.assertEqual([e["id"] for e in doc["inserted"]], [e["id"] for e in new])
        actions2, new2 = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        self.assertEqual(([a for a, _, _ in actions2], new2), (["same"] * len(self.rows), []))
        self.assertEqual(json.loads(self.manifest.read_text()), doc)
        self.assertEqual(count(db), len(self.rows))

    def test_a_name_with_other_settings_is_refused_and_nothing_is_written(self):
        db = scratch()
        s = dict(self.rows[1]["settings"], max_tokens=1)
        db.execute("INSERT INTO players (name, spec, settings, created_at) VALUES (?, ?, ?, 't')",
                   (s["name"], s["spec"], json.dumps(s)))
        db.commit()
        with self.assertRaises(SystemExit):
            P.insert(db, self.rows, self.manifest, self.dbp, "x")
        self.assertEqual(count(db), 1)
        self.assertFalse(db.in_transaction)
        self.assertFalse(self.manifest.exists())

    def test_a_pre_existing_identical_row_survives_rollback(self):
        db = scratch(copy_players=True)
        s = self.rows[0]["settings"]
        db.execute("INSERT INTO players (name, spec, settings, created_at) VALUES (?, ?, ?, 'earlier')",
                   (s["name"], s["spec"], P.compact(s)))
        db.commit()
        pre_id = db.execute("SELECT id FROM players WHERE name = ?", (s["name"],)).fetchone()[0]
        n0 = count(db)
        actions, new = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        self.assertEqual(actions[0], ("same", s["name"], pre_id))
        self.assertNotIn(pre_id, [e["id"] for e in new])
        gone, kept = P.rollback(db, self.manifest, self.dbp)
        self.assertEqual((len(gone), kept), (len(self.rows) - 1, []))
        self.assertEqual(count(db), n0)
        self.assertIsNotNone(db.execute("SELECT 1 FROM players WHERE id = ?", (pre_id,)).fetchone())

    def test_unreferenced_inserted_rows_go_referenced_ones_stay_and_the_cli_fails_loudly(self):
        db = scratch(copy_players=True, path=self.dbp)
        n0 = count(db)
        db.close()
        cli = [sys.executable, "-B", str(HERE / "v3_players.py")]
        r = subprocess.run(cli + ["insert", "--db", str(self.dbp), "--manifest", str(self.manifest)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        used = json.loads(self.manifest.read_text())["inserted"][0]
        db = P.connect(self.dbp)
        reference(db, used["id"])
        db.close()
        r = subprocess.run(cli + ["rollback", "--db", str(self.dbp), "--manifest", str(self.manifest)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"KEPT     {used['name']} (id {used['id']})", r.stderr)
        db = P.connect(self.dbp)
        self.assertEqual(count(db), n0 + 1)
        self.assertIsNotNone(db.execute("SELECT 1 FROM players WHERE id = ?", (used["id"],)).fetchone())
        self.assertEqual([e["id"] for e in json.loads(self.manifest.read_text())["inserted"]], [used["id"]])

    def test_rollback_refuses_when_a_recorded_row_was_changed(self):
        db = scratch()
        _, new = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        db.execute("UPDATE players SET settings = '{}' WHERE id = ?", (new[0]["id"],))
        db.commit()
        with self.assertRaises(SystemExit):
            P.rollback(db, self.manifest, self.dbp)
        self.assertEqual(count(db), len(self.rows))
        self.assertFalse(db.in_transaction)

    def test_foreign_keys_off_is_refused(self):
        db = scratch()
        P.insert(db, self.rows, self.manifest, self.dbp, "x")
        db.execute("PRAGMA foreign_keys = OFF")
        with self.assertRaises(SystemExit):
            P.rollback(db, self.manifest, self.dbp)
        with self.assertRaises(SystemExit):
            P.insert(db, self.rows, self.manifest, self.dbp, "x")
        self.assertEqual(count(db), len(self.rows))

    def test_nothing_can_reference_a_row_between_its_check_and_its_delete(self):
        """BEGIN IMMEDIATE holds the write lock from before the checks to the commit: another connection's attempt to
        reference a recorded row in that window fails (database is locked); after the commit the row is gone and a
        late reference is refused by the foreign key."""
        db = scratch(path=self.dbp)
        _, new = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        target = new[0]["id"]
        tried = []

        def other_writer():
            other = sqlite3.connect(str(self.dbp), timeout=0)
            other.execute("PRAGMA foreign_keys = ON")
            try:
                reference(other, target)
                tried.append("written")
            except sqlite3.OperationalError as e:
                tried.append(str(e))
            finally:
                other.close()
        gone, kept = P.rollback(db, self.manifest, self.dbp, _locked=other_writer)
        self.assertEqual(tried, ["database is locked"])
        self.assertEqual((len(gone), kept), (len(self.rows), []))
        other = P.connect(self.dbp)
        with self.assertRaises(sqlite3.IntegrityError):  # the deleted id cannot be referenced afterwards
            reference(other, target)

    def test_the_engine_also_refuses_deleting_a_referenced_row(self):
        db = scratch()
        _, new = P.insert(db, self.rows, self.manifest, self.dbp, "x")
        reference(db, new[0]["id"])
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("DELETE FROM players WHERE id = ?", (new[0]["id"],))

    def test_on_todays_players_insert_only_adds(self):
        db = scratch(copy_players=True)
        before = db.execute("SELECT * FROM players ORDER BY id").fetchall()
        self.assertEqual([a for a, _, _ in P.plan(db, self.rows)], ["insert"] * len(self.rows))
        P.insert(db, self.rows, self.manifest, self.dbp, "x")
        after = db.execute("SELECT * FROM players ORDER BY id").fetchall()
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(len(after), len(before) + len(self.rows))


if __name__ == "__main__":
    unittest.main()
