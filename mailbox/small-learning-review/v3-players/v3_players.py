"""Path (b), Zeki #5699/#5705: the frozen settings of small chat setups as v3.db `players` rows, WITHOUT play. Additive
only: no existing row changes, no turns, replies, matches or league rows, no ranking baseline. Not run on production.

    python3 v3_players.py check    --db DB [--rows rows.json]                    # what insert would do; writes nothing
    python3 v3_players.py insert   --db DB --manifest M.json [--rows rows.json]  # idempotent; records what it inserted
    python3 v3_players.py rollback --db DB --manifest M.json                     # only the ids the manifest records

rows.json: {"rows": [{"key", "source", "settings"}]}; each `settings` is the prepared late-entry player.json.

insert (one transaction, all or nothing):
- name absent: INSERT with the columns the runner fills (spec, provider, quantization, device, price from the
  settings; settings = compact JSON in the file's key order, as the runner stores it; created_at now);
- name present with equal settings (parsed JSON): nothing; it is NOT recorded (this script did not insert it);
- name present with other settings: refuse, nothing written.
Every row this run inserted is appended to the manifest (provenance): {id, name, settings_sha256, inserted_at} with
the database path and rows.json's sha256. The manifest is written only after the commit.

rollback: for each id in the manifest only (never a row this script did not insert, so never a pre-existing
identical row): the row must still have the recorded name and settings (else refused: nothing deleted); a row that
any match (player1/player2) or league_players row references is KEPT; the others are deleted in one transaction and
removed from the manifest. Exit status 1, naming every kept row, when any is kept.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_rows(path):
    rows = json.loads(Path(path).read_text())["rows"]
    names = [r["settings"]["name"] for r in rows]
    if len(names) != len(set(names)):
        raise SystemExit("rows.json: duplicate names")
    return rows


def compact(settings):
    return json.dumps(settings, separators=(",", ":"), ensure_ascii=False)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


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


def read_manifest(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


def write_manifest(path, doc):
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(p)


def insert(db, rows, manifest, db_path, rows_sha):
    actions = plan(db, rows)
    bad = [a for a in actions if a[0] == "conflict"]
    if bad:
        raise SystemExit("refused, nothing written: a player of this name has other settings: "
                         + ", ".join(f"{n} (id {i})" for _, n, i in bad))
    doc = read_manifest(manifest) or dict(db=str(db_path), inserted=[])
    if doc["db"] != str(db_path):
        raise SystemExit(f"refused: the manifest belongs to {doc['db']}, not {db_path}")
    at, new = now(), []
    with db:
        for r, (act, name, _) in zip(rows, actions):
            if act != "insert":
                continue
            s = r["settings"]
            price = s.get("price")
            cur = db.execute("INSERT INTO players (name, spec, provider, quantization, device, price, settings, "
                             "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (name, s["spec"], s.get("provider"), s.get("quantization"), s.get("device"),
                              json.dumps(price) if price is not None else None, compact(s), at))
            new.append(dict(id=cur.lastrowid, name=name, settings_sha256=sha(compact(s)), inserted_at=at,
                            rows_sha256=rows_sha))
    if new:
        doc["inserted"] += new
        write_manifest(manifest, doc)
    return actions, new


def rollback(db, manifest, db_path):
    doc = read_manifest(manifest)
    if not doc or not doc["inserted"]:
        return [], []
    if doc["db"] != str(db_path):
        raise SystemExit(f"refused: the manifest belongs to {doc['db']}, not {db_path}")
    for e in doc["inserted"]:
        hit = db.execute("SELECT name, settings FROM players WHERE id = ?", (e["id"],)).fetchone()
        if hit is None or hit[0] != e["name"] or sha(hit[1]) != e["settings_sha256"]:
            raise SystemExit(f"refused, nothing deleted: id {e['id']} is no longer the row this script inserted "
                             f"({e['name']})")
    kept, gone = [], []
    for e in doc["inserted"]:
        m = db.execute("SELECT count(*) FROM matches WHERE player1 = ? OR player2 = ?", (e["id"], e["id"])).fetchone()[0]
        lp = db.execute("SELECT count(*) FROM league_players WHERE player_id = ?", (e["id"],)).fetchone()[0]
        (kept if m or lp else gone).append(dict(e, matches=m, league_rows=lp))
    with db:
        for e in gone:
            db.execute("DELETE FROM players WHERE id = ?", (e["id"],))
    doc["inserted"] = [e for e in doc["inserted"] if e["id"] in {k["id"] for k in kept}]
    write_manifest(manifest, doc)
    return gone, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "insert", "rollback"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--rows", default=str(HERE / "rows.json"))
    ap.add_argument("--manifest", help="provenance file of the ids this script inserted (insert, rollback)")
    a = ap.parse_args()
    db_path = Path(a.db).resolve()
    db = sqlite3.connect(str(db_path), timeout=60)
    if a.cmd == "check":
        for act, name, i in plan(db, load_rows(a.rows)):
            print(f"{act:8} {name}" + (f" (id {i})" if i else ""))
        return 0
    if not a.manifest:
        raise SystemExit("--manifest is required for insert and rollback")
    if a.cmd == "insert":
        rows_sha = hashlib.sha256(Path(a.rows).read_bytes()).hexdigest()
        actions, new = insert(db, load_rows(a.rows), a.manifest, db_path, rows_sha)
        ids = {e["name"]: e["id"] for e in new}
        for act, name, i in actions:
            print(f"{'inserted' if act == 'insert' else 'present, not recorded':8} {name} (id {ids.get(name, i)})")
        return 0
    gone, kept = rollback(db, a.manifest, db_path)
    for e in gone:
        print(f"deleted  {e['name']} (id {e['id']})")
    for e in kept:
        print(f"KEPT     {e['name']} (id {e['id']}): referenced by {e['matches']} matches, {e['league_rows']} league "
              "rows; not deleted", file=sys.stderr)
    return 1 if kept else 0


if __name__ == "__main__":
    sys.exit(main())
