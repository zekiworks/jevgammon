#!/usr/bin/env python3
"""Late entry of Google's Gemini Decision 1 (hosted, through OpenRouter pinned to Google AI Studio) into the original
League 1 table (Main, 11 Nov; Ümit, Can #4966), as tools/v3/late-tiny8, one match at a time from the first match on.
player.json holds its v3.db settings. Runs against the main checkout's v3.db; the league web helpers are this tree's.

  gemini.py configs              league config: the entrant v the 3 programs and the paid API setups (GPT-6 Luna
                                 left out while OpenAI is out of credit, as REAX/Ember); the 8 local setups join later
                                 by league-add; read-only on v3.db
  gemini.py trigger              adds the entrant to v3.db's late_entry_stage trigger (writes v3.db)
  gemini.py league-id            the entrant's late-entry league id (read-only)
  gemini.py pending NAME...      opponents among NAME... without a finished valid late-entry match (count; read-only)
  gemini.py open                 open pairs of the entrant's late-entry league (read-only)
  gemini.py billed FIRST         dollars of the entry from match FIRST on: the entrant plus the paid opponents
                                 (read-only)
  gemini.py scope                open and blocked pairs: "OPEN BLOCKED", then one line per blocked pair (read-only)
  gemini.py estimate             decisions, entrant tokens and dollars expected, from earlier late entries (read-only)
  gemini.py inflight FIRST N     the entrant's first N decisions in valid late-entry matches from match FIRST on:
                                 most requests in flight (request start = created_at - request_ms) and most of
                                 its matches running at once (read-only)
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/home/cbasaran/code/jevgammon")
DB = ROOT / "v3.db"
HERE = Path(__file__).resolve().parent
OUT = ROOT / "workspace" / "late-gemini-decision" / "leagues"
CONFIG = OUT / "gemini-decision-1.json"
sys.path.insert(0, str(HERE.parents[1]))
from league_web import league_origins  # noqa: E402

PLAYER = json.loads((HERE / "player.json").read_text())
NAME = PLAYER["name"]
# Original League 1 table (league_web.league_origins, as tools/original_league.py), 19 setups.
API = ["Celeris-1 Decision", "Fastino GLiDE", "GPT-6 Luna", "Jev 1.13.0", "Jev 1.14.0", "Liquid d1-ultra",
       "Mercury Decide", "SubQ Snap Preview"]
ENGINES = ["GNUbg weak", "Random", "Safest"]
LOCAL = ["Clef", "Cygnet (Gemma 4 12B)", "Decider Flash v1.2", "Decider v1.1 27B", "Decider v1.2 27B",
         "Fastino GLiDE v1.2 (local)", "Open-Jev 27B v1.1", "Winnow-12B"]
FIELD = sorted(API + ENGINES + LOCAL)
SKIPPED = ["GPT-6 Luna"]  # OpenAI out of credit: deferred, never dropped (as REAX 1.3, Muse Ember)
NOW = ENGINES + [n for n in API if n not in SKIPPED]
TRIGGER = re.compile(r"p\.name IN \((.*?)\)\)", re.S)
# Earlier decision-model late entries against the same table, for the estimate.
EARLIER = ["Base Labs Elephant-1", "Base Labs Mammoth-1", "Drex 2.0 (local)", "REAX 1.3", "Muse Ember (max)"]
# Gemini input tokens per byte of a stored System One request, the highest of the smoke test's three (11 Nov:
# 2,801 / 9,074, 4,053 / 12,162, 26,133 / 58,077 bytes), for the estimate.
TOKENS_PER_BYTE = 0.45
# A System One decision request of the original League 1 table, as the entrant sends it (same body; model and the
# provider pin aside).
REFERENCE = "Mercury Decide"


def ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def configs(_args) -> None:
    conn = ro()
    field = set()
    for lid in (1, 2, 3):
        field |= {n for n, o in league_origins(conn, lid).items() if o == 1}
    if sorted(field) != FIELD:
        sys.exit(f"original League 1 table changed: {sorted(field ^ set(FIELD))}")
    row = conn.execute("SELECT settings FROM players WHERE name = ?", (NAME,)).fetchone()
    if row and json.loads(row["settings"]) != PLAYER:
        sys.exit(f"{NAME} is already in v3.db with other settings: {row['settings']}")
    l1 = conn.execute("SELECT seed, order_seed, rounds, max_turns, prompt_version FROM leagues WHERE id = 1").fetchone()
    base = json.loads((HERE.parents[2] / "leagues" / "league1.json").read_text())
    players = [PLAYER] + [json.loads(conn.execute("SELECT settings FROM players WHERE name = ?", (n,)).fetchone()[0])
                          for n in NOW]
    cfg = {
        "note": (f"Late entry (Main, 11 Nov; Ümit, Can #4966): {NAME} plays the original League 1 table once (all 19 "
                 "setups; the programs and the paid API setups first, GPT-6 Luna deferred while OpenAI is out of "
                 "credit, the setups on our GPUs by league-add when their servers run). Hidden league (not on the "
                 "site, the dashboard or the ladder tools); only its pairs are played; League 1's rules (seed, pair-v1 "
                 "dice, bg-v2, option-order seed, mirror_concurrent, 3 rounds, no clock, delay 30 s, 300 turns). "
                 "Opponent settings unchanged (v3.db players.settings). Not eligible for the Hype Cup. "
                 "mailbox/Late entry Gemini Decision 1 - status.md"),
        "prompt_version": l1["prompt_version"],
        "seed": l1["seed"],
        "order_seed": l1["order_seed"],
        "rounds": l1["rounds"],
        "clock": base["clock"],
        "delay": base["delay"],
        "max_turns": l1["max_turns"],
        "mirror_concurrent": True,
        "only_pairs_of": NAME,
        "hidden": True,
        "players": players,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"{CONFIG}: {NAME} v {len(NOW)}: {', '.join(NOW)}")


def trigger(_args) -> None:
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("BEGIN IMMEDIATE")
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'late_entry_stage'").fetchone()
    if not sql:
        sys.exit("v3.db has no late_entry_stage trigger")
    names = [n.replace("''", "'") for n in re.findall(r"'((?:[^']|'')*)'", TRIGGER.search(sql[0]).group(1))]
    if NAME in names:
        print("trigger already names", NAME)
        conn.rollback()
        return
    listed = ", ".join("'" + n.replace("'", "''") + "'" for n in names + [NAME])
    conn.execute("DROP TRIGGER late_entry_stage")
    conn.execute(f"""CREATE TRIGGER late_entry_stage AFTER INSERT ON matches
WHEN EXISTS (SELECT 1 FROM players p WHERE p.id IN (NEW.player1, NEW.player2)
             AND p.name IN ({listed}))
BEGIN
  UPDATE matches SET stage = 'late-entry' WHERE id = NEW.id;
END""")
    conn.commit()
    print("late_entry_stage now names:", listed)


def league_id():
    row = ro().execute("SELECT id FROM leagues WHERE only_pairs_of = ? ORDER BY id DESC LIMIT 1", (NAME,)).fetchone()
    return row[0] if row else None


def played(conn, opp) -> bool:
    return bool(conn.execute(
        """SELECT COUNT(*) FROM matches m JOIN players a ON a.id = m.player1 JOIN players b ON b.id = m.player2
           WHERE m.valid = 1 AND m.status = 'finished' AND m.stage = 'late-entry'
             AND ((a.name = ?1 AND b.name = ?2) OR (a.name = ?2 AND b.name = ?1))""", (NAME, opp)).fetchone()[0])


def members(conn) -> list[str]:
    lid = league_id()
    if lid is None:
        return []
    return [r[0] for r in conn.execute(
        """SELECT p.name FROM league_players lp JOIN players p ON p.id = lp.player_id
           WHERE lp.league_id = ? AND lp.left_at IS NULL AND p.name <> ?""", (lid, NAME))]


def pending(args) -> None:
    conn = ro()
    print(sum(not played(conn, o) for o in args.opponents))


def open_pairs(_args) -> None:
    conn = ro()
    print(sum(not played(conn, o) for o in members(conn)))


def billed(args) -> None:
    """The entrant's and the paid opponents' recorded cost_usd (Fastino GLiDE records none: $0.04 per million input
    tokens, as before)."""
    rows = ro().execute(
        """SELECT p.name, SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens) FROM turns t JOIN games g ON g.id = t.game_id
           JOIN matches m ON m.id = g.match_id
           JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
           WHERE m.stage = 'late-entry' AND m.id >= ? GROUP BY p.name""", (args.first,)).fetchall()
    total = 0.0
    for name, cost, tokens in rows:
        if name == "Fastino GLiDE":
            total += (tokens or 0) * 0.04 / 1e6
        elif name in API or name == NAME:
            total += cost
    print(f"{total:.4f}")


# An aborted match whose last error is one of these is blocked: retrying does not cure it (out of credit, key or model
# not available, a request the entrant's server refuses). It stays in the league and is reported as missing, never dropped.
BLOCKING = re.compile(r"refused|\b40[0-4]\b|\b422\b|budget|insufficient|Payment Required|not available", re.I)


def scope(_args) -> None:
    conn = ro()
    blocked = []
    opened = 0
    for opp in members(conn):
        if played(conn, opp):
            continue
        opened += 1
        last = conn.execute(
            """SELECT m.id, m.status, m.error FROM matches m JOIN players a ON a.id = m.player1
               JOIN players b ON b.id = m.player2
               WHERE m.valid = 1 AND m.stage = 'late-entry'
                 AND ((a.name = ?1 AND b.name = ?2) OR (a.name = ?2 AND b.name = ?1))
               ORDER BY m.id DESC LIMIT 1""", (NAME, opp)).fetchone()
        if last and last["status"] == "aborted" and last["error"] and BLOCKING.search(last["error"]):
            blocked.append(f"{NAME} v {opp} (match #{last['id']}): {last['error'][:200]}")
    print(opened, len(blocked))
    for line in blocked:
        print(line)


def estimate(_args) -> None:
    """Expected entrant decisions (earlier entrants' model decisions per late-entry match x 19 opponents), the
    entrant's tokens and dollars (League 1's stored System One request bytes per decision x TOKENS_PER_BYTE at its list
    price), and paid opponents' dollars per match."""
    conn = ro()
    side = """JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
              JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
              JOIN players o ON o.id = CASE t.player WHEN 1 THEN m.player2 ELSE m.player1 END"""
    ok = "m.valid = 1 AND m.status = 'finished' AND m.stage = 'late-entry'"
    marks = ",".join("?" * len(EARLIER))
    dec, matches = conn.execute(
        f"""SELECT SUM(t.decided_by IN ('model', 'fallback')), COUNT(DISTINCT m.id) FROM turns t {side}
            WHERE {ok} AND p.name IN ({marks})""", EARLIER).fetchone()
    per_match = dec / matches
    over = conn.execute("""SELECT COUNT(*), SUM(legal_count > 255) FROM turns WHERE decided_by IN ('model', 'fallback')
                           AND prompt_version = 'bg-v2'""").fetchone()
    price = PLAYER["price"]["input_per_mtok"]
    # Bytes of the answered System One requests per decision of the reference setup, over its valid matches.
    ref_bytes, ref_dec = conn.execute(
        f"""SELECT SUM(LENGTH(CAST(e.request AS BLOB))), COUNT(DISTINCT t.id) FROM exchanges e
            JOIN turns t ON t.id = e.turn_id {side}
            WHERE p.name = ? AND m.valid = 1 AND e.error IS NULL AND t.decided_by IN ('model', 'fallback')""",
        (REFERENCE,)).fetchone()
    per_dec = ref_bytes / ref_dec * TOKENS_PER_BYTE
    paid = {}
    for opp in API:
        cost, tokens, n = conn.execute(
            f"""SELECT SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens), COUNT(DISTINCT m.id) FROM turns t {side}
                WHERE {ok} AND o.name IN ({marks}) AND p.name = ?""", EARLIER + [opp]).fetchone()
        if n:
            paid[opp] = ((tokens or 0) * 0.04 / 1e6 if opp == "Fastino GLiDE" else cost) / n
    total = per_match * len(FIELD)
    print(f"decisions per match {per_match:.1f} ({dec} over {matches} late-entry matches of {', '.join(EARLIER)})")
    print(f"expected {NAME} decisions: {total:.0f} (19 opponents); now (programs + API less Luna): "
          f"{per_match * len(NOW):.0f}; locals: {per_match * len(LOCAL):.0f}")
    print(f"decisions over 255 options in bg-v2: {over[1]} of {over[0]} -> {total * over[1] / over[0]:.1f} expected")
    print(f"entrant tokens per decision ~{per_dec:,.0f} ({REFERENCE}'s {ref_bytes / ref_dec:,.0f} request bytes per "
          f"decision over {ref_dec} decisions x {TOKENS_PER_BYTE}) -> ${per_dec * price / 1e6:.5f} per decision; "
          f"all {total:.0f}: ${total * per_dec * price / 1e6:.2f}; "
          f"now: ${per_match * len(NOW) * per_dec * price / 1e6:.2f}")
    print("paid opponents per match: " + ", ".join(f"{k} ${v:.4f}" for k, v in paid.items())
          + f"; all {len(paid)}: ${sum(paid.values()):.3f}; now: ${sum(v for k, v in paid.items() if k in NOW):.3f}")


def entrant_turns(conn, where: str, params: tuple):
    return conn.execute(
        f"""SELECT t.id, m.id AS match_id, t.created_at, t.request_ms, t.decided_by FROM turns t
            JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
            JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
            WHERE p.name = ? AND {where} ORDER BY t.created_at, t.id""", (NAME,) + params).fetchall()


def ts(s: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def peak(intervals) -> int:
    events = sorted([(s, 1) for s, _ in intervals] + [(e, -1) for _, e in intervals])
    cur = most = 0
    for _, d in events:
        cur += d
        most = max(most, cur)
    return most


def inflight(args) -> None:
    conn = ro()
    turns = entrant_turns(conn, "m.id >= ? AND m.valid = 1 AND m.stage = 'late-entry' AND t.decided_by IN "
                                 "('model', 'fallback') AND t.request_ms IS NOT NULL", (args.first,))[:args.n]
    if not turns:
        print("0 decisions")
        return
    iv = [(ts(t["created_at"]) - t["request_ms"] / 1000, ts(t["created_at"])) for t in turns]
    spans = {}
    for t, (s, e) in zip(turns, iv):
        lo, hi = spans.get(t["match_id"], (s, e))
        spans[t["match_id"]] = (min(lo, s), max(hi, e))
    print(f"{len(turns)} decisions (turn ids {turns[0]['id']}-{turns[-1]['id']}, {turns[0]['created_at']} to "
          f"{turns[-1]['created_at']}): at most {peak(iv)} in flight; at most {peak(spans.values())} {NAME} "
          f"matches deciding at once (matches {', '.join(f'#{m}' for m in spans)})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("configs", "trigger", "league-id", "open", "scope", "estimate"):
        sub.add_parser(cmd)
    p = sub.add_parser("pending")
    p.add_argument("opponents", nargs="+")
    b = sub.add_parser("billed")
    b.add_argument("first", type=int)
    i = sub.add_parser("inflight")
    i.add_argument("first", type=int)
    i.add_argument("n", type=int)
    args = ap.parse_args()
    {"configs": configs, "trigger": trigger, "pending": pending, "open": open_pairs, "billed": billed,
     "scope": scope, "estimate": estimate, "league-id": lambda a: print(league_id() or ""),
     "inflight": inflight}[args.cmd](args)


if __name__ == "__main__":
    main()
