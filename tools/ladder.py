#!/usr/bin/env python3
"""Inter-league ladder (mailbox/backgammon-ladder-cup.md): computes the next round from the current
tables, writes its approval request, and applies an approved round. It plays no match: the leagues'
runners play the new pairings (`jevgammon league --resume ID`) after `apply`.

    python3 tools/ladder.py plan  --db v3.db [--scores DIR] [--out FILE]   # read-only
    python3 tools/ladder.py apply --db v3.db --round N [--jevgammon BIN]   # only after Can's approval
    python3 tools/ladder.py cup-winner --db v3.db --match ID [--scores DIR]

Rules (setups move, not models; one result per pair):
- Leagues from bottom to top: LADDER. Each round, at every boundary at the same time, the lower
  league's winner swaps with the upper league's last. Programs (GNU Backgammon, Random, Safest) never
  move: when a rule picks a program, the next setup in the table is taken.
- Tables: points, games won, fewer games lost, then the lower error rate over all of a setup's valid
  matches (`league_web.error_rates`, the site's GNUbg scores). A pair's valid match counts in every
  league whatever league or rules it was played in, so a mover plays only the pairs it never played;
  every other pair of its new league is reused (order ignored).
- No lock (Can, 2026-10-26; the earlier lock rule is gone): setups move by these rules every round,
  as often as the tables say.
- End: the ladder ends at the first round whose moves would create no new pairing (every pair they
  create is already stored). That round is not played as a round; instead the final placement:
  each setup it would move is oscillating between its league and the move's target, and is placed
  in whichever of the two is closer to its original league (`league_web.league_origins`: the league
  before any ladder move); every other setup stays. The placement's moves have the reason "final
  placement" and are applied like a round's.
- Every move is recorded in `league_players.note` of the league left, by `apply`, as
  "ladder round N: <reason> to league M" (reasons: promoted, relegated, final placement); that is
  the ladder's history (`history`).

Hype Cup tie rule (for the Cup orchestrator): a Cup match that ends level (stored or new) goes to the
setup with the lower error rate in that match (`cup_winner`); no extra rounds are played.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "site"))
import league_web as lw  # noqa: E402

# Leagues from the bottom up, by id, with their names on the site.
LADDER = [1, 2, 3]
LEAGUE_NAMES = {1: "League 1 (decision models)", 2: "League 2 (workhorses)", 3: "League 3 (frontier models)"}
# Players that are programs: they never move and never enter the Cup.
PROGRAM_SPECS = {"random", "safest", "gnubg-weak"}
MOVE_NOTE = re.compile(r"ladder round (\d+): (promoted|relegated|final placement) to league (\d+)")


def short(lid: int) -> str:
    return f"League {lid}"


# --- Data ------------------------------------------------------------------------------------------

def connect(db: Path, write: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(db if write else f"file:{db}?mode=ro", uri=not write, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def players(conn) -> dict[str, dict]:
    """Every player by name: id, spec, provider, device, settings."""
    return {r["name"]: dict(id=r["id"], spec=r["spec"], provider=r["provider"] or "", device=r["device"] or "",
                            settings=json.loads(r["settings"]))
            for r in conn.execute("SELECT * FROM players")}


def is_program(player: dict) -> bool:
    return player["spec"] in PROGRAM_SPECS


def tables(conn, rates: dict[str, float]) -> dict[int, list[dict]]:
    """Every ladder league's current table, ranked with the error-rate tiebreak."""
    out = {}
    for lid in LADDER:
        league = conn.execute("SELECT * FROM leagues WHERE id = ?", (lid,)).fetchone()
        names = [p["name"] for p in lw.participants(conn, lid)]
        fixtures, games_won = lw.league_fixtures(conn, league)
        out[lid] = dict(league=league, names=names, fixtures=fixtures,
                        table=lw.league_table(names, fixtures, games_won, rates))
    return out


def pair_matches(conn) -> dict[frozenset, dict]:
    """Every pair's result: its valid match (any stage but legacy playoffs, any rules), by pair."""
    out = {}
    for r in conn.execute(
            """SELECT m.id, m.started_at, m.finished_at, m.status, m.score1, m.score2, m.winner, m.mirror_concurrent,
                      p1.name AS a, p2.name AS b
               FROM matches m JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'playoff' ORDER BY m.id"""):
        out[frozenset((r["a"], r["b"]))] = dict(r)
    return out


def played_in(conn, match: dict) -> list[str]:
    """The leagues a stored match was played in (both players were participants when it started), as
    labels; a hidden league (`leagues.hidden`) is an early start for a coming round."""
    hidden = "COALESCE(l.hidden, 0)" if "hidden" in {r[1] for r in conn.execute("PRAGMA table_info(leagues)")} else "0"
    return [f"early start, hidden league #{lid}" if is_hidden else short(lid) for lid, is_hidden in conn.execute(
        f"""SELECT a.league_id, {hidden} FROM league_players a JOIN players pa ON pa.id = a.player_id
           JOIN league_players b ON b.league_id = a.league_id JOIN players pb ON pb.id = b.player_id
           JOIN leagues l ON l.id = a.league_id
           WHERE pa.name = ? AND pb.name = ?
             AND a.joined_at <= ? AND (a.left_at IS NULL OR a.left_at > ?)
             AND b.joined_at <= ? AND (b.left_at IS NULL OR b.left_at > ?)
           ORDER BY a.league_id""",
        (match["a"], match["b"], *(match["started_at"],) * 4))]


def history(conn) -> list[dict]:
    """Moves of earlier rounds, from the notes `apply` leaves on the participation that ended."""
    out = []
    for r in conn.execute(
            """SELECT p.name, lp.league_id, lp.left_at, lp.note FROM league_players lp
               JOIN players p ON p.id = lp.player_id WHERE lp.left_at IS NOT NULL ORDER BY lp.left_at"""):
        for m in MOVE_NOTE.finditer(r["note"] or ""):
            out.append(dict(round=int(m.group(1)), setup=r["name"], source=r["league_id"],
                            target=int(m.group(3)), reason=m.group(2), at=r["left_at"]))
    return out


# --- The round -------------------------------------------------------------------------------------

def round_moves(current: dict, people: dict, number: int) -> tuple[list[dict], list[str], list[dict]]:
    """The round's moves at every boundary (the lower league's top setup swaps with the upper league's
    last; programs are skipped), with notes on skipped programs and the swaps for the error-rate flag."""
    moves, notes, swaps = [], [], []
    for lower, upper in zip(LADDER, LADDER[1:]):
        lower_table = [r for r in current[lower]["table"] if not is_program(people[r["name"]])]
        upper_table = [r for r in current[upper]["table"] if not is_program(people[r["name"]])]
        skipped_low = [r["name"] for r in current[lower]["table"][:current[lower]["table"].index(lower_table[0])]]
        skipped_up = [r["name"] for r in current[upper]["table"][current[upper]["table"].index(upper_table[-1]) + 1:]]
        winner, last = lower_table[0], upper_table[-1]
        if skipped_low:
            notes.append(f"{short(lower)}: {', '.join(skipped_low)} ranks above {winner['name']} but is a program "
                         "and never moves; the next setup is taken.")
        if skipped_up:
            notes.append(f"{short(upper)}: {', '.join(skipped_up)} ranks below {last['name']} but is a program "
                         "and never moves; the next setup is taken.")
        moves.append(dict(round=number, setup=winner["name"], source=lower, target=upper, reason="promoted"))
        moves.append(dict(round=number, setup=last["name"], source=upper, target=lower, reason="relegated"))
        swaps.append(dict(lower=lower, upper=upper, promoted=winner["name"], replaced=last["name"],
                          promoted_row=winner, replaced_row=last))
    return moves, notes, swaps


def lineups_after(names: dict[int, list[str]], moves: list[dict]) -> dict[int, list[str]]:
    """Every ladder league's members after `moves`."""
    after = {lid: list(names[lid]) for lid in LADDER}
    for m in moves:
        after[m["source"]].remove(m["setup"])
        after[m["target"]].append(m["setup"])
    return after


def mover_pairs(moves: list[dict], after: dict[int, list[str]]) -> list[dict]:
    """Each pair a mover meets in its new league (once per pair), as {league, a (the mover), b}."""
    out, seen = [], set()
    for m in moves:
        for other in after[m["target"]]:
            pair = frozenset((m["setup"], other))
            if other == m["setup"] or pair in seen:
                continue
            seen.add(pair)
            out.append(dict(league=m["target"], a=m["setup"], b=other))
    return out


def final_placement(moves: list[dict], origin: dict[str, int], number: int) -> tuple[list[dict], list[dict]]:
    """The end of the ladder: every setup the last round would move oscillates between its league and
    the move's target, and is placed in whichever is closer to its original league (`origin`). Returns
    the oscillating setups (setup, source, target, origin, placed) and the moves that placement makes."""
    oscillating, placed_moves = [], []
    for m in moves:
        home = origin[m["setup"]]
        placed = m["source"] if abs(home - m["source"]) <= abs(home - m["target"]) else m["target"]
        oscillating.append(dict(setup=m["setup"], source=m["source"], target=m["target"], origin=home,
                                placed=placed))
        if placed != m["source"]:
            placed_moves.append(dict(round=number, setup=m["setup"], source=m["source"], target=placed,
                                     reason="final placement"))
    return oscillating, placed_moves


def compute_round(conn, scores: Path) -> dict:
    people = players(conn)
    rates_full = lw.error_rates(conn, scores)
    rates = lw.tiebreak_rates(rates_full)
    current = tables(conn, rates)
    results = pair_matches(conn)
    moves_before = history(conn)
    number = 1 + max((m["round"] for m in moves_before), default=0)
    names = {lid: current[lid]["names"] for lid in LADDER}
    moves, notes, swaps = round_moves(current, people, number)
    after = lineups_after(names, moves)
    pairs = mover_pairs(moves, after)
    # End rule: a round whose moves create no new pairing is not played; the final placement instead.
    ended = all(frozenset((p["a"], p["b"])) in results for p in pairs)
    oscillating = []
    if ended:
        origin = {}
        for lid in LADDER:
            origin.update(lw.league_origins(conn, lid))
        oscillating, moves = final_placement(moves, origin, number)
        swaps = []
        after = lineups_after(names, moves)
        pairs = mover_pairs(moves, after)
    new, reused = [], []
    for p in pairs:
        match = results.get(frozenset((p["a"], p["b"])))
        if match:
            reused.append({**p, "match": match, "played_in": played_in(conn, match)})
        else:
            new.append(p)
    return dict(number=number, moves=moves, notes=notes, swaps=swaps, new=new, reused=reused, before=current,
                after=after, people=people, rates=rates_full, history=moves_before, ended=ended,
                oscillating=oscillating)


# --- Estimates -------------------------------------------------------------------------------------

def concurrent_factor(conn) -> float:
    """Median wall time of a match with both games of a round at once, over the summed decision time of
    both sides (pauses over league_web.PAUSE_GAP left out): measured on the stored valid matches."""
    ratios = []
    rows = conn.execute(
        """SELECT m.id, t.created_at, t.latency_ms, t.decided_by FROM turns t JOIN games g ON g.id = t.game_id
           JOIN matches m ON m.id = g.match_id
           WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.mirror_concurrent = 1 ORDER BY m.id, t.created_at""")
    by = defaultdict(list)
    for r in rows:
        by[r["id"]].append(r)
    for turns in by.values():
        stamps = [datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).timestamp() for t in turns]
        wall = sum(b - a for a, b in zip(stamps, stamps[1:]) if b - a <= lw.PAUSE_GAP)
        busy = sum(t["latency_ms"] for t in turns if t["decided_by"] in ("model", "fallback")) / 1000
        if busy > 60:
            ratios.append(wall / busy)
    return median(ratios)


def setup_stats(conn) -> dict[str, dict]:
    """Per setup over its valid matches: decisions per match (its own side), seconds per decision, and
    the cost per decision at its configured price (NULL prices count as unknown)."""
    out = {}
    for r in conn.execute(
            """SELECT p.name, COUNT(DISTINCT m.id) AS matches, COUNT(*) AS decisions,
                      AVG(t.latency_ms) / 1000.0 AS seconds, SUM(t.cost_usd) AS cost, COUNT(t.cost_usd) AS priced
               FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
               JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
               WHERE m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by IN ('model', 'fallback')
               GROUP BY p.name"""):
        out[r["name"]] = dict(per_match=r["decisions"] / r["matches"], seconds=r["seconds"],
                              cost=(r["cost"] / r["priced"]) if r["priced"] else None)
    return out


# Our model servers by address (tools/v3/servers/README.md, AFTER_MORNING.md): the server, and the
# bariton RTX PRO 6000 GPUs it takes (0: a DGX Spark). Servers named alike are one server (both
# settings of a model; Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B share one GPU).
SERVERS = {
    "127.0.0.1:8894": ("gemma4-31b-replicas.sh: Gemma 4 31B (bariton)", 1),
    "127.0.0.1:8897": ("qwen38-27b.sh: Qwen3.8-27B (bariton)", 1),
    "127.0.0.1:8898": ("lfm25-24b.sh: LFM2.5-24B-A2B (bariton)", 1),
    "127.0.0.1:18101": ("glide-v12.sh: Fastino GLiDE v1.2 (bariton)", 1),
    "127.0.0.1:18099": ("decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU)", 1),
    "127.0.0.1:18098": ("decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU)", 1),
    "127.0.0.1:8091": ("decider-v1.2.sh 27b + flash, winnow.sh (bariton, one GPU)", 1),
    "127.0.0.1:18097": ("decider.sh: Decider v1.1 27B (bariton)", 1),
    "127.0.0.1:8791": ("open-jev.sh: Open-Jev 27B v1.1 (bariton)", 1),
    "192.168.1.127:18091": ("clef.sh on the DGX Spark at 192.168.1.127", 0),
    "192.168.1.127:18093": ("cygnet.sh on the DGX Spark at 192.168.1.127", 0),
}
# Default addresses of local decision specs without a base_url (src/players/decision.rs).
DEFAULT_URLS = {"open-jev": "127.0.0.1:8791", "clef": "127.0.0.1:18091", "cygnet": "127.0.0.1:18093",
                "pplx-local": "127.0.0.1:18097", "winnow": "127.0.0.1:8091"}
BARITON_GPUS = 4


def hosting(player: dict) -> dict:
    """How a setup runs and what its matches cost: kind (program, subscription, own hardware, API),
    the cost label of the site's Method page, where it runs (server or API), and bariton GPUs."""
    s, provider = player["settings"], player["provider"]
    url = s.get("base_url") or ""
    address = re.sub(r"^https?://([^/]+).*$", r"\1", url) if url else DEFAULT_URLS.get(player["spec"].split("/")[0], "")
    if is_program(player):
        return dict(kind="program", label="no cost (program)", where="CPU (this machine)", gpus=0)
    if "subscription" in provider:
        return dict(kind="subscription", label="API-equivalent (subscription)", where=provider, gpus=0)
    if provider.startswith("local") or address.startswith(("127.0.0.1", "localhost", "192.168.")):
        where, gpus = SERVERS.get(address, (f"local server at {address or 'an unknown address'}", 1))
        return dict(kind="own hardware", label="own hardware", where=where, gpus=gpus)
    return dict(kind="API", label="API price", where=provider or url, gpus=0)


def estimate(conn, plan: dict) -> None:
    """Adds money, API-equivalent money, duration and hardware to every new pairing of `plan`."""
    stats = setup_stats(conn)
    factor = concurrent_factor(conn)
    plan["concurrent_factor"] = factor
    for p in plan["new"]:
        sides = [p["a"], p["b"]]
        decisions = sum(stats[n]["per_match"] for n in sides) / 2
        money, equivalent, unknown, servers, apis = 0.0, 0.0, [], {}, []
        for n in sides:
            h, st = hosting(plan["people"][n]), stats[n]
            if h["kind"] == "API":
                apis.append(h["where"])
                if st["cost"] is None:
                    unknown.append(n)
                else:
                    money += st["cost"] * decisions
            elif h["kind"] == "subscription":
                apis.append(h["where"])
                equivalent += (st["cost"] or 0.0) * decisions
            elif h["kind"] == "own hardware":
                servers[h["where"]] = h["gpus"]
        p.update(decisions=decisions, money=money, equivalent=equivalent, unknown=unknown, servers=servers,
                 apis=sorted(set(apis)), hours=decisions * sum(stats[n]["seconds"] for n in sides) * factor / 3600)


# --- Error rates with intervals --------------------------------------------------------------------

def interval(rate: dict, name: str) -> tuple[float, float]:
    """95% interval of a setup's all-matches error rate, resampling games as the site does."""
    import stats
    from analysis import boot
    from common import THRESHOLDS as T
    sums, counts = zip(*rate["games"].values())
    return stats.ratio_interval(sums, counts, T["equity_scale"], T["bootstrap_resamples"],
                                boot(f"all-matches/{name}"), T["interval"])


def fmt_rate(rates: dict, name: str) -> str:
    r = rates.get(name)
    if not r or r["rate"] is None:
        return "no scored decisions"
    lo, hi = interval(r, name)
    extra = f"; {r['pending']} decisions not scored yet" if r["pending"] else ""
    return f"{r['rate']:.1f} (95% interval {lo:.1f}-{hi:.1f}; {r['scored']:,} decisions{extra})"


# --- Cup tie rule ----------------------------------------------------------------------------------

def match_error_rates(conn, scores: Path, match_id: int) -> dict[int, dict]:
    """Error rate of each side (1, 2) in one match: 500 x mean loss of its scored decisions there
    (decisions with two or more legal plays, invalid answers left out), and how many are not scored."""
    decisions = conn.execute(
        """SELECT t.id, t.player FROM turns t JOIN games g ON g.id = t.game_id
           WHERE g.match_id = ? AND t.decided_by = 'model' AND t.legal_count >= 2""", (match_id,)).fetchall()
    marks = ",".join("?" * len(decisions)) or "NULL"
    loss = {}
    for path in sorted(scores.glob("s*.db")):
        shard = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        loss.update(shard.execute(f"SELECT turn_id, loss FROM plays WHERE turn_id IN ({marks})",
                                  [t for t, _ in decisions]))
        shard.close()
    out = {1: dict(loss=0.0, scored=0, pending=0), 2: dict(loss=0.0, scored=0, pending=0)}
    for turn, side in decisions:
        r = out[side]
        if turn in loss:
            r["loss"] += loss[turn]
            r["scored"] += 1
        else:
            r["pending"] += 1
    for r in out.values():
        r["rate"] = lw.ERROR_SCALE * r["loss"] / r["scored"] if r["scored"] else None
    return out


def cup_winner(conn, scores: Path, match_id: int) -> dict:
    """The winner of a Cup match: the match winner, or for a level match (stored or new) the setup with
    the lower error rate in that match. No extra rounds. Refuses while decisions are unscored."""
    m = conn.execute(
        """SELECT m.status, m.winner, m.score1, m.score2, p1.name AS a, p2.name AS b FROM matches m
           JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2 WHERE m.id = ?""",
        (match_id,)).fetchone()
    if m is None or m["status"] != "finished":
        raise SystemExit(f"match #{match_id} is not a finished match")
    names = {1: m["a"], 2: m["b"]}
    if m["winner"] is not None:
        return dict(winner=names[m["winner"]], how=f"won {max(m['score1'], m['score2'])}-{min(m['score1'], m['score2'])}")
    rates = match_error_rates(conn, scores, match_id)
    if any(r["pending"] or r["rate"] is None for r in rates.values()):
        raise SystemExit(f"match #{match_id} is level and not every decision is scored yet: run the site update first")
    if rates[1]["rate"] == rates[2]["rate"]:
        raise SystemExit(f"match #{match_id} is level on points and on error rate; no rule decides it")
    side = 1 if rates[1]["rate"] < rates[2]["rate"] else 2
    return dict(winner=names[side], how=f"level {m['score1']}-{m['score2']}; error rate in the match "
                                       f"{rates[side]['rate']:.1f} against {rates[3 - side]['rate']:.1f}")


# --- The request -----------------------------------------------------------------------------------

def usd(x: float) -> str:
    return f"${x:,.2f}"


def hours(x: float) -> str:
    if x < 1 / 60:
        return "under 1 min"
    return f"{x * 60:.0f} min" if x < 1 else f"{x:.1f} h"


def request(conn, plan: dict, db: Path) -> str:
    n, people, rates = plan["number"], plan["people"], plan["rates"]
    now = datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    title = f"# Ladder ended: final placement (round {n})" if plan["ended"] else f"# Ladder round {n}: request"
    out = [title, "",
           f"{now} · computed by `tools/ladder.py plan` from `{db.name}` (read-only). Nothing has started. "
           "Nothing runs until Can approves this round.", ""]
    if plan["ended"]:
        out += ["## Ladder ended", "",
                f"Round {n}'s moves would create no new pairing (every pair they make is already stored), so "
                "the ladder ends (rule of 2026-10-26). Each setup round " + str(n) + " would move is oscillating "
                "between its league and the move's target; it is placed in whichever of the two is closer to its "
                "original league (its league before any ladder move). Every other setup stays. The moves below "
                "are that placement (reason: final placement); the Hype Cup can be prepared once they are "
                "applied.", ""]
        if plan["oscillating"]:
            out += ["| Setup | Oscillates between | Original league | Placed in |", "| --- | --- | --- | --- |"]
            out += [f"| {o['setup']} | {short(o['source'])} and {short(o['target'])} | {short(o['origin'])} | "
                    f"{short(o['placed'])} |" for o in plan["oscillating"]]
        else:
            out.append("No setup would move: nobody oscillates.")
        out += [""]
    else:
        out += ["## End check", "",
                f"Round {n}'s moves create {len(plan['new'])} new pairing(s), so the ladder goes on (it ends at "
                "the first round whose moves would create no new pairing).", ""]
    out += ["## Tables used", "",
            "Ranking: points, then games won, then fewer games lost, then the lower error rate over all of a "
            "setup's valid matches (every league, ladder round and Cup; GNUbg 1.08 2-ply, 500 x mean equity loss, "
            "decisions with two or more legal plays, invalid answers left out, as on the site). Programs never "
            "move.", ""]
    for lid in LADDER:
        rows = plan["before"][lid]["table"]
        top = [r for r in rows if not is_program(people[r["name"]])]
        def line(r):
            err = f"{r['error_rate']:.1f}" if r["error_rate"] is not None else "-"
            prog = " (program)" if is_program(people[r["name"]]) else ""
            return f"{r['place']}. {r['name']}{prog}: {r['points']} pts, games {r['gw']}-{r['gl']}, error rate {err}"
        out.append(f"- **{LEAGUE_NAMES[lid]}** ({len(rows)} setups): " +
                   "; ".join(line(r) for r in rows[:3]) + " … last: " + line(rows[-1]) +
                   ("" if rows[-1]["name"] == top[-1]["name"] else f"; last setup that can move: {line(top[-1])}"))
    out += [""]
    out += ["## Moves", "", "| Round | Setup | From | To | Reason |", "| --- | --- | --- | --- | --- |"]
    for m in plan["moves"]:
        out.append(f"| {m['round']} | {m['setup']} | {short(m['source'])} | {short(m['target'])} | {m['reason']} |")
    out += [""] + [f"- {note}" for note in plan["notes"]]
    if plan["history"]:
        out += ["", "Earlier rounds:", ""] + [
            f"- round {m['round']}: {m['setup']}, {short(m['source'])} to {short(m['target'])}, {m['reason']}"
            for m in plan["history"]]
    out += ["", "## Error-rate flag", "",
            "A swap is flagged when the promoted setup's error rate is worse (higher) than the error rate of the "
            "setup it replaces. Error rates over all valid matches, 95% intervals by resampling games (site "
            "method, 2,000 resamples).", "",
            "| Boundary | Promoted | Error rate | Replaced | Error rate | Flag |", "| --- | --- | --- | --- | --- | --- |"]
    for s in plan["swaps"]:
        a, b = rates[s["promoted"]]["rate"], rates[s["replaced"]]["rate"]
        flag = "**flagged: worse than the setup it replaces**" if a is not None and b is not None and a > b else "no"
        out.append(f"| {short(s['lower'])}-{short(s['upper'])} | {s['promoted']} | {fmt_rate(rates, s['promoted'])} | "
                   f"{s['replaced']} | {fmt_rate(rates, s['replaced'])} | {flag} |")
    out += ["", "## Lineups after the round", ""]
    for lid in LADDER:
        joined = [n for n in plan["after"][lid] if n not in plan["before"][lid]["names"]]
        left = [n for n in plan["before"][lid]["names"] if n not in plan["after"][lid]]
        out.append(f"- **{short(lid)}** ({len(plan['after'][lid])} setups): joins {', '.join(joined) or 'nobody'}; "
                   f"leaves {', '.join(left) or 'nobody'}.")
    new, reused = plan["new"], plan["reused"]
    out += ["", f"## New pairings ({len(new)})", "",
            "Each mover plays every setup of its new league it has not played anywhere (two newcomers of one "
            "league play each other too). Format: the league match rules (3 rounds, turn limit 300, prompt "
            "bg-v2, the leagues' option-order seed), both games of a round at the same time (as Leagues 2 and 3); "
            "League 1's earlier matches stay as played (in sequence), as the page says.", "",
            "Estimates from each setup's stored valid matches: decisions per match (the mean of the two "
            "setups), its mean seconds per decision, its cost per decision at its configured price. Duration = "
            "decisions x (seconds of both) x " + f"{plan['concurrent_factor']:.2f}" + " (measured: wall time of a "
            "match with both games at once over its summed decision time, median of the stored matches). Money "
            "labels as on the site's Method page: **API price** (billed money), **API-equivalent (subscription)** "
            "(list price of the tokens, not billed), **own hardware** (no money; GPU time).", ""]
    blocks = schedule(new, people)
    order = [p for b in blocks for p in b["pairings"]]
    out += ["| # | League | Pairing | Money (API price) | API-equivalent (subscription) | Duration | Own hardware | APIs and subscriptions |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, p in enumerate(order, 1):
        p["order"] = i
        money = usd(p["money"]) + (f" + unknown ({', '.join(p['unknown'])}: no price recorded)" if p["unknown"] else "")
        servers = "; ".join(p["servers"]) or "none"
        out.append(f"| {i} | {short(p['league'])} | {p['a']} v {p['b']} | {money} | {usd(p['equivalent'])} | "
                   f"{hours(p['hours'])} | {servers} | {', '.join(p['apis']) or 'none'} |")
    out += ["", f"## Reused pairings ({len(reused)})", "",
            "Already played (valid match), so not played again; the stored result counts in the new league's table.", "",
            "| League | Pairing | Stored match | Played in | Result |", "| --- | --- | --- | --- | --- |"]
    for r in reused:
        m = r["match"]
        result = f"{m['a']} {m['score1']}-{m['score2']} {m['b']}"
        where = ", ".join(r["played_in"]) or "outside the leagues"
        out.append(f"| {short(r['league'])} | {r['a']} v {r['b']} | #{m['id']} ({m['started_at'][:10]}) | {where} | {result} |")
    out += ["", "## Scheduling order", "",
            "API and subscription pairings first (no GPU), then the GPU pairings in blocks: each block needs one "
            f"set of servers (at most {BARITON_GPUS} bariton GPUs), so GPU time can be arranged with compactor "
            "block by block. Wall time assumes the movers' usual limit of matches at once (max_matches, 4 unless "
            "set) and is rough: the slowest match of a block sets its end.", ""]
    for i, b in enumerate(blocks, 1):
        ps = b["pairings"]
        total = sum(p["hours"] for p in ps)
        movers = sorted({p["mover"] for p in ps})
        cap = min(len(ps), sum(people_max_matches(people[m]) for m in movers))
        wall = max(max(p["hours"] for p in ps), total / cap)
        need = ("no GPU" if not b["servers"] else
                f"{sum(b['servers'].values())} bariton GPU(s)" + "".join(
                    f"; {s}" for s in sorted(b["servers"])))
        out.append(f"{i}. **{b['name']}**: pairings {ps[0]['order']}-{ps[-1]['order']} ({len(ps)}); needs {need}; "
                   f"{hours(total)} of match time, about {hours(wall)} wall time ({', '.join(movers)}).")
    per_server = defaultdict(float)
    for p in order:
        for s in p["servers"]:
            per_server[s] += p["hours"]
    total_money = sum(p["money"] for p in new)
    total_eq = sum(p["equivalent"] for p in new)
    unknown = sorted({n for p in new for n in p["unknown"]})
    out += ["", "## Totals", "",
            f"- New pairings: **{len(new)}**; reused: {len(reused)}.",
            f"- Money (API price): **{usd(total_money)}**" +
            (f", plus {', '.join(unknown)} (no price recorded)" if unknown else "") + ".",
            f"- API-equivalent of the subscription matches (not billed): {usd(total_eq)}.",
            f"- Match time: {hours(sum(p['hours'] for p in new))} in total.",
            "- Own hardware, match time per server (summed over its matches; matches of one server overlap):"]
    out += [f"  - {s}: {hours(v)}" for s, v in sorted(per_server.items())]
    out += ["", "## On approval", "",
            f"1. `python3 tools/ladder.py apply --db v3.db --round {n}`: records the moves (league-remove with "
            f"\"ladder round {n}: <reason> to league M\", then league-add with the setup's stored settings) and "
            "sets the leagues that receive a mover to play both games of a round at the same time."]
    if plan["ended"] and not new:
        out += ["2. No match is played: every pair of the final lineups is stored. The ladder is over; the "
                "Hype Cup can be prepared from the final tables.", ""]
        return "\n".join(out) + "\n"
    out += ["2. Block 1 (API and subscription): resume the leagues that hold those pairings "
            "(`tools/v3/run_league<N>.sh` units); their runners play only the new pairings. A league that also "
            "holds GPU pairings starts them too: while their server is down they fail the warm-up and back off "
            "(2 minutes, doubling up to 1 hour) and resume once the server is up. A league whose pairings are "
            "all GPU pairings is resumed with its first GPU block.",
            "3. GPU blocks: claim the GPUs with compactor over the agent bus, start the block's servers "
            "(`tools/v3/servers/`; the scripts take the GPU index), let the runners play the block, stop the "
            "servers and release the GPUs.",
            ("4. When every pairing is played, the ladder is over; the Hype Cup can be prepared." if plan["ended"]
             else "4. When every pairing is played, the next `tools/ladder.py plan` writes round " + str(n + 1) +
             "'s request (or the ladder's end and final placement)."), ""]
    return "\n".join(out) + "\n"


def people_max_matches(player: dict) -> int:
    """Matches a setup plays at once in a league (`league.rs`: max_matches, 4 by default, engines any)."""
    if is_program(player):
        return 99
    return max(1, player["settings"].get("max_matches") or 4)


def schedule(new: list[dict], people: dict) -> list[dict]:
    """New pairings in blocks, in playing order: the pairings without own hardware first, then per league
    the GPU pairings, packed into blocks of at most BARITON_GPUS bariton GPUs (pairings needing the same
    servers next to each other)."""
    for p in new:
        p["mover"] = p["a"]
    blocks = [dict(name="API and subscription (no GPU)", servers={},
                   pairings=sorted([p for p in new if not p["servers"]],
                                   key=lambda p: (p["league"], p["a"], p["b"])))]
    for lid in LADDER:
        ps = sorted([p for p in new if p["servers"] and p["league"] == lid],
                    key=lambda p: (sorted(p["servers"]), p["a"], p["b"]))
        current = None
        for p in ps:
            union = {**(current["servers"] if current else {}), **p["servers"]}
            if current is None or sum(union.values()) > BARITON_GPUS:
                current = dict(name=f"{short(lid)} GPU block", servers=dict(p["servers"]), pairings=[])
                blocks.append(current)
            current["servers"].update(p["servers"])
            current["pairings"].append(p)
        same = [b for b in blocks if b["name"] == f"{short(lid)} GPU block"]
        if len(same) > 1:
            for k, b in enumerate(same, 1):
                b["name"] = f"{short(lid)} GPU block {k}"
    return [b for b in blocks if b["pairings"]]


# --- Apply -----------------------------------------------------------------------------------------

def apply(db: Path, scores: Path, number: int, binary: Path, freeze: Path) -> None:
    with connect(db) as conn:
        plan = compute_round(conn, scores)
    if plan["number"] != number:
        raise SystemExit(f"the next round is {plan['number']}, not {number}")
    moving = plan["moves"]
    if not moving:
        raise SystemExit("the ladder has ended and its final placement moves nobody: nothing to apply")
    receiving = sorted({m["target"] for m in moving})
    conn = connect(db, write=True)
    for lid in receiving:
        if not conn.execute("SELECT mirror_concurrent FROM leagues WHERE id = ?", (lid,)).fetchone()[0]:
            conn.execute(
                "UPDATE leagues SET mirror_concurrent = 1, note = TRIM(COALESCE(note, '') || ' ' || ?) WHERE id = ?",
                (f"From ladder round {number} on, new matches play both games of a round at the same time "
                 "(the ladder and Cup format); earlier matches were played in sequence.", lid))
    conn.commit()
    conn.close()
    for m in moving:
        run([binary, "league-remove", "--db", db, "--league", str(m["source"]), "--player", m["setup"],
             "--reason", f"ladder round {number}: {m['reason']} to league {m['target']}"])
    for m in moving:
        entry = json.dumps(plan["people"][m["setup"]]["settings"])
        run([binary, "league-add", "--db", db, "--league", str(m["target"]), "--entry", entry,
             "--freeze-log", freeze / f"league{m['target']}-additions.json"])
    print(f"round {number} applied: {len(moving)} moves; resume leagues {', '.join(map(str, receiving))} to play "
          f"{len(plan['new'])} new pairings")


# Keys kept in their own files, read when the environment has none (as tools/v3/run_league1.sh):
# `league-add` builds the setup's client, which needs its key.
KEY_FILES = {"JEV_API_KEY": "~/code/jev/key", "FASTINO_API_KEY": "~/.config/fastino/key",
             "CELERIS_API_KEY": "~/.config/celeris/key"}


def run(cmd: list) -> None:
    cmd = [str(c) for c in cmd]
    print("$", " ".join(cmd[:3]), "...", flush=True)
    env = dict(os.environ)
    for var, path in KEY_FILES.items():
        key = Path(path).expanduser()
        if not env.get(var) and key.is_file():
            env[var] = key.read_text().strip()
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


# --- Main ------------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply", "cup-winner"):
        p = sub.add_parser(name)
        p.add_argument("--db", type=Path, required=True)
        p.add_argument("--scores", type=Path, default=lw.default_scores())
        if name == "plan":
            p.add_argument("--out", type=Path, help="request file (default: print it)")
        if name == "apply":
            p.add_argument("--round", type=int, required=True)
            p.add_argument("--jevgammon", type=Path, default=ROOT / "target" / "release" / "jevgammon")
            p.add_argument("--freeze", type=Path, default=ROOT / "freeze",
                           help="directory of the additions freeze logs league<ID>-additions.json")
        if name == "cup-winner":
            p.add_argument("--match", type=int, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        with connect(args.db) as conn:
            plan = compute_round(conn, args.scores)
            unscored = {n: r["pending"] for n, r in plan["rates"].items() if r["pending"]}
            if unscored:
                raise SystemExit(f"decisions not scored yet (run the site update first): {unscored}")
            estimate(conn, plan)
            text = request(conn, plan, args.db)
        if args.out:
            args.out.write_text(text)
            print(f"wrote {args.out}: round {plan['number']}, {len(plan['new'])} new pairings, "
                  f"{len(plan['reused'])} reused")
        else:
            print(text)
    elif args.command == "apply":
        apply(args.db, args.scores, args.round, args.jevgammon, args.freeze)
    else:
        with connect(args.db) as conn:
            print(json.dumps(cup_winner(conn, args.scores, args.match)))


if __name__ == "__main__":
    main()
