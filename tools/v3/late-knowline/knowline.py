#!/usr/bin/env python3
"""Late entry KnowLine 31B Gen1.5 into the original League 1 table (Ümit #4325), as the Muse Ember / Base Labs late
entries (tools/v3/late-ember/ember.py, mailbox/Late entries 3 - plan 2026-11-02.md). Runs against the main checkout's
v3.db; the league web helpers are this tree's.

  knowline.py configs              league config: the entrant v the 3 programs and the paid API setups (GPT-6 Luna
                                   left out while OpenAI is out of credit, as REAX/Ember); the 8 local setups join later
                                   by league-add; read-only on v3.db
  knowline.py trigger              adds the entrant to v3.db's late_entry_stage trigger (writes v3.db)
  knowline.py league-id            the entrant's late-entry league id (read-only)
  knowline.py pending NAME...      opponents among NAME... without a finished valid late-entry match (count; read-only)
  knowline.py open                 open pairs of the entrant's late-entry league (read-only)
  knowline.py billed FIRST         paid opponents' dollars in late-entry matches from match FIRST on (read-only)
  knowline.py scope                open and blocked pairs: "OPEN BLOCKED", then one line per blocked pair (read-only)
  knowline.py estimate             decisions and server hours expected, from earlier late entries (read-only)
  knowline.py settings             records player.json in v3.db's players row when only max_matches and the note
                                   changed (one match at a time, Zeki #4561); refuses any other change (writes v3.db)
  knowline.py parallel-valid       the parallel-window matches (PARALLEL) still valid, one id per line (read-only)
  knowline.py parallel-record      markdown for the status file: the excluded window's matches, turn ids and times
  knowline.py inflight FIRST N     the first N KnowLine decisions in valid late-entry matches from match FIRST on:
                                   most requests in flight (request start = created_at - request_ms) and most
                                   KnowLine matches running at once (read-only)
  knowline.py server-inflight SINCE UNTIL   SGLang's own batch log on the server host (ssh, read-only; UTC times
                                   'YYYY-MM-DD HH:MM:SS'): most requests in the server (new + running + queued) per
                                   logged batch; other clients of the same server are counted too
"""
import argparse
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path("/home/cbasaran/code/jevgammon")
DB = ROOT / "v3.db"
HERE = Path(__file__).resolve().parent
OUT = ROOT / "workspace" / "late-knowline" / "leagues"
CONFIG = OUT / "knowline-31b-gen1.5.json"
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
# Decider v1.1 27B (a dense 27B decision model) while it ran on a DGX Spark GB10, its only GB10 stretch.
GB10 = ("Decider v1.1 27B", "2026-10-16T11:04", "2026-10-22T19:34")


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
        "note": (f"Late entry (Ümit #4325): {NAME} plays the original League 1 table once (all 19 setups; the "
                 "programs and the paid API setups first, GPT-6 Luna deferred while OpenAI is out of credit, the setups "
                 "on our GPUs by league-add when their servers run). Hidden league (not on the site, the dashboard or "
                 "the ladder tools); only its pairs are played; League 1's rules (seed, pair-v1 dice, bg-v2, "
                 "option-order seed, mirror_concurrent, 3 rounds, no clock, delay 30 s, 300 turns). Opponent settings "
                 "unchanged (v3.db players.settings). Not eligible for the Hype Cup. "
                 "mailbox/Late entries KnowLine - status.md"),
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
    """Paid opponents' recorded cost_usd (Fastino GLiDE records none: $0.04 per million input tokens, as before).
    KnowLine itself runs on our GPU and costs nothing."""
    rows = ro().execute(
        """SELECT p.name, SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens) FROM turns t JOIN games g ON g.id = t.game_id
           JOIN matches m ON m.id = g.match_id
           JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
           WHERE m.stage = 'late-entry' AND m.id >= ? AND p.name <> ? GROUP BY p.name""", (args.first, NAME)).fetchall()
    total = 0.0
    for name, cost, tokens in rows:
        if name == "Fastino GLiDE":
            total += (tokens or 0) * 0.04 / 1e6
        elif name in API:
            total += cost
    print(f"{total:.4f}")


# An aborted match whose last error is one of these is blocked: retrying does not cure it (out of credit, key or model
# not available, a request KnowLine's server refuses). It stays in the league and is reported as missing, never dropped.
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
    """Expected KnowLine decisions (earlier entrants' model decisions per late-entry match x 19 opponents), paid
    opponents' dollars per match, and GB10 hours at the GB10 Decider's mean seconds per decision."""
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
    name, lo, hi = GB10
    ms = [r[0] for r in conn.execute(
        f"""SELECT t.request_ms FROM turns t {side} WHERE p.name = ? AND t.decided_by = 'model' AND m.valid = 1
            AND t.created_at >= ? AND t.created_at < ? AND t.request_ms IS NOT NULL""", (name, lo, hi))]
    paid = {}
    for opp in API:
        cost, tokens, n = conn.execute(
            f"""SELECT SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens), COUNT(DISTINCT m.id) FROM turns t {side}
                WHERE {ok} AND o.name IN ({marks}) AND p.name = ?""", EARLIER + [opp]).fetchone()
        if n:
            paid[opp] = ((tokens or 0) * 0.04 / 1e6 if opp == "Fastino GLiDE" else cost) / n
    mean_s = statistics.mean(ms) / 1000
    total = per_match * len(FIELD)
    print(f"decisions per match {per_match:.1f} ({dec} over {matches} late-entry matches of {', '.join(EARLIER)})")
    print(f"expected KnowLine decisions: {total:.0f} (19 opponents); now (programs + API less Luna): "
          f"{per_match * len(NOW):.0f}; locals: {per_match * len(LOCAL):.0f}")
    print(f"decisions over 255 options in bg-v2: {over[1]} of {over[0]} -> {total * over[1] / over[0]:.1f} expected")
    print(f"GB10 reference {name} {lo}..{hi}: {len(ms)} decisions, median {statistics.median(ms) / 1000:.2f} s, "
          f"mean {mean_s:.2f} s -> KnowLine at that mean: {total * mean_s / 3600:.1f} h of server time")
    print("paid opponents per match: " + ", ".join(f"{k} ${v:.4f}" for k, v in paid.items())
          + f"; all {len(paid)}: ${sum(paid.values()):.3f}; now: ${sum(v for k, v in paid.items() if k in NOW):.3f}")


# The first run (2026-11-10 20:22-20:30 UTC, league #21, harness 9df24a8) played these 4 matches at once, so the
# server got up to 5 requests at a time (SGLang's batch log; turn intervals show 1 decision at a time, the rest were
# warm-ups). Rule (Zeki #4564): void (the league's own `jevgammon void`: valid 0, rows kept) and replayed from the
# start, one match at a time.
PARALLEL = [933, 934, 935, 936]
PARALLEL_REASON = ("KnowLine 31B Gen1.5's first run played 4 matches at once (#933-#936), up to 5 requests at once "
                   "on a server handed over for one at a time; excluded and replayed from the start, one match at a "
                   "time (Zeki #4561, #4564)")
SSH_HOST = "spark2"
SNAPSHOT = "/home/cbasaran/decision-models/KnowLine-31B-Gen1.5@8e56aa1b236a6dd1064dcfd22ba1e5e360e4c140"


def settings(_args) -> None:
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT id, settings FROM players WHERE name = ?", (NAME,)).fetchone()
    if not row:
        conn.rollback()
        sys.exit(f"{NAME} is not in v3.db")
    stored = json.loads(row[1])
    if stored == PLAYER:
        conn.rollback()
        print(f"players #{row[0]}: settings already as player.json")
        return
    changed = {k for k in stored.keys() | PLAYER.keys() if stored.get(k) != PLAYER.get(k)}
    if not changed <= {"max_matches", "note"}:
        conn.rollback()
        sys.exit(f"players #{row[0]}: settings differ in {sorted(changed)}, not only max_matches/note")
    conn.execute("UPDATE players SET settings = ? WHERE id = ?", (json.dumps(PLAYER, ensure_ascii=False), row[0]))
    conn.commit()
    print(f"players #{row[0]}: settings updated ({', '.join(sorted(changed))}): max_matches {PLAYER.get('max_matches')}")


def parallel_valid(_args) -> None:
    conn = ro()
    for mid in PARALLEL:
        if conn.execute("SELECT valid FROM matches WHERE id = ?", (mid,)).fetchone()[0] == 1:
            print(mid)


def knowline_turns(conn, where: str, params: tuple):
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


def parallel_record(_args) -> None:
    conn = ro()
    marks = ",".join("?" * len(PARALLEL))
    turns = knowline_turns(conn, f"m.id IN ({marks})", tuple(PARALLEL))
    model = [t for t in turns if t["decided_by"] in ("model", "fallback")]
    print(f"- Excluded (Zeki #4564): matches {', '.join(f'#{m}' for m in PARALLEL)}, played at once in the first run; "
          f"void with `jevgammon void` (valid 0, every row kept), pairs replayed from the start one match at a time.")
    for mid in PARALLEL:
        r = conn.execute("""SELECT m.status, m.valid, m.voided_at, m.started_at, a.name, b.name FROM matches m
                            JOIN players a ON a.id = m.player1 JOIN players b ON b.id = m.player2 WHERE m.id = ?""",
                         (mid,)).fetchone()
        n = sum(t["match_id"] == mid for t in model)
        print(f"  - #{mid} {r[4]} v {r[5]}: {r[0]}, valid {r[1]}{f', voided {r[2]}' if r[2] else ''}; started "
              f"{r[3]}; {n} KnowLine decisions")
    print(f"  - KnowLine turns: {len(turns)} ({len(model)} decisions with a request), turn ids {turns[0]['id']}-"
          f"{turns[-1]['id']}, stored {turns[0]['created_at']} to {turns[-1]['created_at']}")
    print(f"  - decision turn ids: {' '.join(str(t['id']) for t in model)}")
    iv = [(ts(t["created_at"]) - t["request_ms"] / 1000, ts(t["created_at"])) for t in model if t["request_ms"]]
    print(f"  - in flight: decisions at most {peak(iv)} at once (turn intervals, created_at - request_ms); warm-ups "
          "(not stored) at each start and resume of the 4 matches: SGLang's batch log shows up to 5 requests at once")


def inflight(args) -> None:
    conn = ro()
    turns = knowline_turns(conn, "m.id >= ? AND m.valid = 1 AND m.stage = 'late-entry' AND t.decided_by IN "
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
          f"{turns[-1]['created_at']}): at most {peak(iv)} in flight; at most {peak(spans.values())} KnowLine "
          f"matches deciding at once (matches {', '.join(f'#{m}' for m in spans)})")


def server_inflight(args) -> None:
    import subprocess
    cmd = (f"pid=$(pgrep -f 'sglang.launch_server --model-path {SNAPSHOT}' | head -1); "
           "unit=$(sed -n 's#.*/\\([^/]*\\.service\\)$#\\1#p' /proc/$pid/cgroup); "
           f"journalctl --user -u \"$unit\" --since '{args.since} UTC' --until '{args.until} UTC' -o cat --no-pager")
    out = subprocess.run(["timeout", "60", "ssh", "-o", "BatchMode=yes", SSH_HOST, cmd], capture_output=True,
                         text=True, check=True).stdout
    most, batches = 0, 0
    for line in out.splitlines():
        if " batch, " not in line:
            continue
        d = dict((k, int(v)) for k, v in re.findall(r"#([a-z-]+): (\d+)", line))
        batches += 1
        most = max(most, d.get("new-seq", 0) + d.get("running-req", 0) + d.get("queue-req", 0))
    print(f"SGLang batch log {args.since} to {args.until} UTC: {batches} batches, at most {most} requests in the "
          "server (new + running + queued; other clients included)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("configs", "trigger", "league-id", "open", "scope", "estimate"):
        sub.add_parser(cmd)
    p = sub.add_parser("pending")
    p.add_argument("opponents", nargs="+")
    b = sub.add_parser("billed")
    b.add_argument("first", type=int)
    for cmd in ("settings", "parallel-valid", "parallel-record"):
        sub.add_parser(cmd)
    i = sub.add_parser("inflight")
    i.add_argument("first", type=int)
    i.add_argument("n", type=int)
    s = sub.add_parser("server-inflight")
    s.add_argument("since")
    s.add_argument("until")
    args = ap.parse_args()
    {"configs": configs, "trigger": trigger, "pending": pending, "open": open_pairs, "billed": billed,
     "scope": scope, "estimate": estimate, "league-id": lambda a: print(league_id() or ""), "settings": settings,
     "parallel-valid": parallel_valid, "parallel-record": parallel_record, "inflight": inflight,
     "server-inflight": server_inflight}[args.cmd](args)


if __name__ == "__main__":
    main()
