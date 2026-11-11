#!/usr/bin/env python3
"""Late entries Gemini 4 Carbon (high) and Claude Fable 5.2 (max) into the original League 1 table (Ümit via Zeki
#4676), as tools/v3/late-knowline4b (KnowLine 4B Gen5.5), one match at a time from the first match on. ENTRANT is
carbon or fable (player-carbon.json, player-fable.json). Runs against the main checkout's v3.db; the league web helpers
are this tree's.

  late.py ENTRANT configs          league config: the entrant v the 3 programs and the paid API setups (GPT-6 Luna left
                                   out while OpenAI is out of credit, as KnowLine 4B); the 8 local setups join later by
                                   league-add (locals.sh); read-only on v3.db
  late.py ENTRANT trigger          adds the entrant to v3.db's late_entry_stage trigger (writes v3.db)
  late.py ENTRANT league-id        the entrant's late-entry league id (read-only)
  late.py ENTRANT pending NAME...  opponents among NAME... without a finished valid late-entry match (count; read-only)
  late.py ENTRANT open             open pairs of the entrant's late-entry league (read-only)
  late.py ENTRANT billed FIRST     paid opponents' dollars in the entrant's late-entry matches from match FIRST on
                                   (read-only)
  late.py ENTRANT own FIRST        the entrant's own list-price dollars, tokens and decisions from match FIRST on
                                   (Claude subscription: $0 billed; OpenRouter: billed)
  late.py ENTRANT owncost FIRST    the entrant's own list-price dollars from match FIRST on (a number; the guard's cap)
  late.py ENTRANT scope            open and blocked pairs: "OPEN BLOCKED", then one line per blocked pair (read-only)
  late.py ENTRANT limited FIRST    the entrant's subscription limit, if its latest aborted match from FIRST on ended on
                                   one (429 / usage or rate limit / RESOURCE_EXHAUSTED): prints that error, else nothing
  late.py ENTRANT estimate         decisions per match (earlier late entries) and the family's league record at its
                                   highest setting: tokens and API-list-price dollars per decision (read-only)
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
sys.path.insert(0, str(HERE.parents[1]))
from league_web import league_origins  # noqa: E402

# entrant -> (player file, league config name, the family's league setup at its highest stored setting)
ENTRANTS = {
    "carbon": ("player-carbon.json", "gemini-4-carbon-high.json", "Gemini 4 Argon (on)"),
    "fable": ("player-fable.json", "claude-fable-5.2-max.json", "Claude Fable 5.1 (on)"),
}
# Original League 1 table (league_web.league_origins, as tools/original_league.py), 19 setups.
API = ["Celeris-1 Decision", "Fastino GLiDE", "GPT-6 Luna", "Jev 1.13.0", "Jev 1.14.0", "Liquid d1-ultra",
       "Mercury Decide", "SubQ Snap Preview"]
ENGINES = ["GNUbg weak", "Random", "Safest"]
LOCAL = ["Clef", "Cygnet (Gemma 4 12B)", "Decider Flash v1.2", "Decider v1.1 27B", "Decider v1.2 27B",
         "Fastino GLiDE v1.2 (local)", "Open-Jev 27B v1.1", "Winnow-12B"]
FIELD = sorted(API + ENGINES + LOCAL)
SKIPPED = ["GPT-6 Luna"]  # OpenAI out of credit: deferred, never dropped (as REAX 1.3, Muse Ember, KnowLine)
NOW = ENGINES + [n for n in API if n not in SKIPPED]
TRIGGER = re.compile(r"p\.name IN \((.*?)\)\)", re.S)
EARLIER = ["Base Labs Elephant-1", "Base Labs Mammoth-1", "Drex 2.0 (local)", "REAX 1.3", "Muse Ember (max)",
           "KnowLine 31B Gen1.5"]
# A subscription at its limit: the run stops (resumable), never loops on it.
LIMITED = re.compile(r"\b429\b|rate_limit|usage limit|RESOURCE_EXHAUSTED|quota", re.I)
# An aborted match whose last error is one of these is blocked: retrying does not cure it (out of credit, key or model
# not available, a request refused). It stays in the league and is reported as missing, never dropped.
BLOCKING = re.compile(r"refused|\b40[0-4]\b|\b422\b|budget|insufficient|Payment Required|not available", re.I)

ENTRANT: str = ""
PLAYER: dict = {}
NAME: str = ""
CONFIG: Path = Path()


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
        "note": (f"Late entry (Ümit via Zeki #4676): {NAME} plays the original League 1 table once (all 19 setups; "
                 "the programs and the paid API setups first, GPT-6 Luna deferred while OpenAI is out of credit, the "
                 "setups on our GPUs by league-add when their servers run), one match at a time. Hidden league (not on "
                 "the site, the dashboard or the ladder tools; the site holds the setup until the entry is complete); "
                 "only its pairs are played; League 1's rules (seed, pair-v1 dice, bg-v2, option-order seed, "
                 "mirror_concurrent, 3 rounds, no clock, delay 30 s, 300 turns). Opponent settings unchanged (v3.db "
                 f"players.settings). Not eligible for the Hype Cup. mailbox/Late entries {NAME} - status.md"),
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
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
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


SIDE = """JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
          JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
          JOIN players o ON o.id = CASE t.player WHEN 1 THEN m.player2 ELSE m.player1 END"""


def billed(args) -> None:
    """Paid opponents' recorded cost_usd in the entrant's late-entry matches (Fastino GLiDE records none: $0.04 per
    million input tokens, as before). The entrant's own cost: own / owncost."""
    rows = ro().execute(
        f"""SELECT p.name, SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens) FROM turns t {SIDE}
            WHERE m.stage = 'late-entry' AND m.id >= ? AND o.name = ? GROUP BY p.name""",
        (args.first, NAME)).fetchall()
    total = 0.0
    for name, cost, tokens in rows:
        if name == "Fastino GLiDE":
            total += (tokens or 0) * 0.04 / 1e6
        elif name in API:
            total += cost
    print(f"{total:.4f}")


def own_row(first: int):
    return ro().execute(
        f"""SELECT SUM(t.decided_by IN ('model', 'fallback')), SUM(COALESCE(t.cost_usd, 0)), SUM(t.input_tokens),
                   SUM(t.output_tokens) FROM turns t {SIDE}
            WHERE m.stage = 'late-entry' AND m.id >= ? AND p.name = ?""", (first, NAME)).fetchone()


def own(args) -> None:
    dec, cost, tin, tout = own_row(args.first)
    billing = "subscription: $0 billed" if PLAYER["provider"].endswith("-subscription") else "billed on OpenRouter"
    print(f"{dec or 0} decisions, {tin or 0} input + {tout or 0} output tokens, list price ${cost or 0:.2f} ({billing})")


def owncost(args) -> None:
    """The entrant's own recorded cost_usd from match FIRST on, valid or voided (every request is paid)."""
    print(f"{own_row(args.first)[1] or 0:.4f}")


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
        if last and last["status"] == "aborted" and last["error"] and BLOCKING.search(last["error"]) \
                and not LIMITED.search(last["error"]):
            blocked.append(f"{NAME} v {opp} (match #{last['id']}): {last['error'][:200]}")
    print(opened, len(blocked))
    for line in blocked:
        print(line)


def limited(args) -> None:
    last = ro().execute(
        """SELECT m.id, m.error FROM matches m JOIN players a ON a.id = m.player1 JOIN players b ON b.id = m.player2
           WHERE m.stage = 'late-entry' AND m.id >= ? AND m.status = 'aborted' AND ? IN (a.name, b.name)
           ORDER BY m.id DESC LIMIT 1""", (args.first, NAME)).fetchone()
    # The entrant's own limit only: the error names the failing player's model id (an opponent's 429 does not count).
    if last and last["error"] and LIMITED.search(last["error"]) \
            and PLAYER["spec"].split("/", 1)[1] in last["error"]:
        print(f"match #{last['id']}: {last['error'][:400]}")


def estimate(_args) -> None:
    conn = ro()
    ok = "m.valid = 1 AND m.status = 'finished'"
    marks = ",".join("?" * len(EARLIER))
    dec, matches = conn.execute(
        f"""SELECT SUM(t.decided_by IN ('model', 'fallback')), COUNT(DISTINCT m.id) FROM turns t {SIDE}
            WHERE {ok} AND m.stage = 'late-entry' AND p.name IN ({marks})""", EARLIER).fetchone()
    per_match = dec / matches
    family = ENTRANTS[ENTRANT][2]
    fdec, fin, fout, frsn, fcost, fms = conn.execute(
        f"""SELECT SUM(t.decided_by IN ('model', 'fallback')), AVG(t.input_tokens), AVG(t.output_tokens),
                   AVG(t.reasoning_tokens), SUM(t.cost_usd), AVG(t.request_ms)
            FROM turns t {SIDE} WHERE {ok} AND p.name = ? AND t.decided_by IN ('model', 'fallback')""",
        (family,)).fetchone()
    price = PLAYER["price"]
    per_dec = (fin * price["input_per_mtok"] + fout * price["output_per_mtok"]) / 1e6
    total = per_match * len(FIELD)
    print(f"decisions per match {per_match:.1f} ({dec} over {matches} late-entry matches of {', '.join(EARLIER)}); "
          f"19 opponents: {total:.0f}")
    print(f"{family}: {fdec} league decisions, mean {fin:.0f} input + {fout:.0f} output tokens ({frsn or 0:.0f} "
          f"reasoning), {fms / 1000:.1f} s per decision; recorded ${fcost / fdec:.4f} per decision")
    print(f"{NAME} at those tokens and its price ${price['input_per_mtok']}/${price['output_per_mtok']}: "
          f"${per_dec:.4f} per decision, ${per_dec * total:.0f} for {total:.0f} decisions (x2 output tokens: "
          f"${(fin * price['input_per_mtok'] + 2 * fout * price['output_per_mtok']) / 1e6 * total:.0f})")


def main() -> None:
    global ENTRANT, PLAYER, NAME, CONFIG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrant", choices=sorted(ENTRANTS))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("configs", "trigger", "league-id", "open", "scope", "estimate"):
        sub.add_parser(cmd)
    p = sub.add_parser("pending")
    p.add_argument("opponents", nargs="+")
    for cmd in ("billed", "own", "owncost", "limited"):
        sub.add_parser(cmd).add_argument("first", type=int)
    args = ap.parse_args()
    ENTRANT = args.entrant
    pfile, cname, _ = ENTRANTS[ENTRANT]
    PLAYER = json.loads((HERE / pfile).read_text())
    NAME = PLAYER["name"]
    CONFIG = ROOT / "workspace" / "late-carbon-fable" / ENTRANT / "leagues" / cname
    {"configs": configs, "trigger": trigger, "pending": pending, "open": open_pairs, "billed": billed, "own": own,
     "owncost": owncost,
     "scope": scope, "limited": limited, "estimate": estimate,
     "league-id": lambda a: print(league_id() or "")}[args.cmd](args)


if __name__ == "__main__":
    main()
