"""Path (b), Zeki #5699: the frozen settings of small chat setups as v3.db `players` rows, WITHOUT play. Additive only:
no existing row changes, no turns, replies, matches or league rows, no ranking baseline. Not run on production.

    python3 v3_players.py check    --db DB [--rows rows.json]   # what insert would do; writes nothing
    python3 v3_players.py insert   --db DB [--rows rows.json]   # idempotent
    python3 v3_players.py rollback --db DB [--rows rows.json]   # deletes exactly these rows, only if unreferenced

rows.json: {"rows": [{"key", "source", "settings"}]}; each `settings` is the prepared late-entry player.json
(late-smallchat models/KEY/player.json at the commit named in rows.json), byte-for-byte as parsed JSON.

insert, per row in one transaction (all or nothing):
- name absent: INSERT with the columns the runner fills for a local setup (spec, provider, quantization, device, price
  from the settings; settings = the compact JSON in the file's key order, as the runner stores it; created_at now).
- name present with equal settings (parsed JSON equality): nothing (idempotent).
- name present with other settings: refuse, nothing written.
rollback, per row in one transaction: refuse if any match (player1/player2) or league_players row references the id,
or if its settings are not the file's; else DELETE that id only.
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_rows(path):
    rows = json.loads(Path(path).read_text())["rows"]
    names = [r["settings"]["name"] for r in rows]
    if len(names) != len(set(names)):
        raise SystemExit("rows.json: duplicate names")
    return rows


def compact(settings):
    return json.dumps(settings, separators=(",", ":"), ensure_ascii=False)


def plan(db, rows):
    """[(action, name, id)]: insert | same | conflict."""
    out = []
    for r in rows:
        s = r["settings"]
        hit = db.execute("SELECT id, settings FROM players WHERE name = ?", (s["name"],)).fetchone()
        if hit is None:
            out.append(("insert", s["name"], None))
        elif json.loads(hit[1]) == s:
            out.append(("same", s["name"], hit[0]))
        else:
            out.append(("conflict", s["name"], hit[0]))
    return out


def insert(db, rows):
    actions = plan(db, rows)
    bad = [a for a in actions if a[0] == "conflict"]
    if bad:
        raise SystemExit("refused, nothing written: a player of this name has other settings: "
                         + ", ".join(f"{n} (id {i})" for _, n, i in bad))
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    with db:
        for r, (act, name, _) in zip(rows, actions):
            if act != "insert":
                continue
            s = r["settings"]
            price = s.get("price")
            db.execute("INSERT INTO players (name, spec, provider, quantization, device, price, settings, created_at) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (name, s["spec"], s.get("provider"), s.get("quantization"), s.get("device"),
                        json.dumps(price) if price is not None else None, compact(s), now))
    return plan(db, rows), actions


def rollback(db, rows):
    actions = plan(db, rows)
    bad = [a for a in actions if a[0] == "conflict"]
    if bad:
        raise SystemExit("refused, nothing deleted: settings differ from rows.json: " + ", ".join(n for _, n, _ in bad))
    ids = [(n, i) for a, n, i in actions if a == "same"]
    used = []
    for n, i in ids:
        m = db.execute("SELECT count(*) FROM matches WHERE player1 = ? OR player2 = ?", (i, i)).fetchone()[0]
        lp = db.execute("SELECT count(*) FROM league_players WHERE player_id = ?", (i,)).fetchone()[0]
        if m or lp:
            used.append(f"{n} (id {i}: {m} matches, {lp} league rows)")
    if used:
        raise SystemExit("refused, nothing deleted: referenced: " + "; ".join(used))
    with db:
        for _, i in ids:
            db.execute("DELETE FROM players WHERE id = ?", (i,))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "insert", "rollback"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--rows", default=str(HERE / "rows.json"))
    a = ap.parse_args()
    rows = load_rows(a.rows)
    db = sqlite3.connect(a.db, timeout=60)
    db.execute("PRAGMA foreign_keys = ON")
    if a.cmd == "check":
        for act, name, i in plan(db, rows):
            print(f"{act:8} {name}" + (f" (id {i})" if i else ""))
        return
    if a.cmd == "insert":
        after, before = insert(db, rows)
        for (b, name, _), (_, _, i) in zip(before, after):
            print(f"{'inserted' if b == 'insert' else 'present':8} {name} (id {i})")
        return
    for name, i in rollback(db, rows):
        print(f"deleted  {name} (id {i})")


if __name__ == "__main__":
    sys.exit(main())
