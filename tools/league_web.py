#!/usr/bin/env python3
"""League dashboard: serves one page and JSON snapshots read from the league database.

    python3 tools/league_web.py --db league.db --port 8095 [--control tools/v3/league_control.sh]

Standard library only. The database is opened read-only per request, so it can run beside a
league in progress. The page shows the latest league (or ?league=N), the history of every
league in the database with what each one tested (`leagues.note`), and links to the working
copy of the published report (`--report`, served at /report/). The table follows `src/league.rs`: 3 points for a win, 1 for
a draw, ties broken by more games won, then fewer games lost; only finished matches count.

--control SCRIPT adds a Pause / Resume button: GET /api/control runs `SCRIPT status` (one JSON
line: unit, state, since, message) and POST /api/control {"action": "pause"|"resume"} starts
`SCRIPT pause|resume` in its own systemd user unit (league-control) and returns at once. POSTs
are taken only from CONTROL_NETWORKS and with the X-League-Control header the page sends.
"""

import argparse
import ipaddress
import json
import sqlite3
import subprocess
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

WIN_POINTS, DRAW_POINTS = 3, 1
CACHE_SECONDS = 2.0
# A league that is not finished counts as live while it moved within this many seconds.
LIVE_SECONDS = 600
# A gap between two turns of a match longer than this (seconds) counts as a pause, not play.
PAUSE_GAP = 1800
# Clients allowed to pause or resume: this machine and the LAN.
CONTROL_NETWORKS = (ipaddress.ip_network("127.0.0.1/32"), ipaddress.ip_network("192.168.1.0/24"))
# Header the page sends with control POSTs; a cross-site form or fetch cannot set it unasked.
CONTROL_HEADER = "X-League-Control"
CONTROL_UNIT = "league-control"


def control_allowed(host: str) -> bool:
    """Whether a client at `host` may pause or resume."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in net for net in CONTROL_NETWORKS)


def control_status(script: Path) -> dict:
    """`SCRIPT status` as a dict, with enabled: true."""
    try:
        out = subprocess.run([str(script), "status"], capture_output=True, text=True, timeout=20, check=True)
        return {"enabled": True, **json.loads(out.stdout)}
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return {"enabled": True, "state": "error", "unit": "", "since": "", "message": f"status failed: {error}"}


def control_start(script: Path, action: str) -> str | None:
    """Start `SCRIPT action` in a transient systemd user unit; an error message, or None."""
    out = subprocess.run(
        ["systemd-run", "--user", "--collect", "--quiet", f"--unit={CONTROL_UNIT}",
         f"--working-directory={script.parent}", str(script), action],
        capture_output=True, text=True, timeout=20,
    )
    return None if out.returncode == 0 else (out.stderr.strip() or f"systemd-run exited {out.returncode}")


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Column names of `table`; older databases lack the per-decision v3 columns."""
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def unsigned(value: int | None) -> str | None:
    """A seed stored as SQLite's signed 64-bit integer, as the runner's u64 (a string for JS)."""
    return None if value is None else str(value & (2**64 - 1))



def league_fixtures(conn: sqlite3.Connection, lid: int) -> tuple[list[dict], dict[int, list[int]]]:
    """The league's fixtures with their latest match, and games won per match."""
    # A deferred match failed and is retried later (databases since resumable matches).
    deferred = (
        "lm.error AS deferred_error, lm.failed_at AS deferred_at"
        if {"error", "failed_at"} <= columns(conn, "league_matches")
        else "NULL AS deferred_error, NULL AS deferred_at"
    )
    fixtures = [dict(r) for r in conn.execute(
        f"""SELECT lm.id, lm.stage, lm.label, lm.matchday, lm.model1, lm.model2, lm.match_id,
                  m.status, m.score1, m.score2, m.winner, m.rounds_played, m.rounds_planned,
                  m.error, m.started_at, m.finished_at, {deferred}
           FROM league_matches lm LEFT JOIN matches m ON m.id = lm.match_id
           WHERE lm.league_id = ? ORDER BY lm.stage != 'league', lm.stage, lm.matchday, lm.id""",
        (lid,),
    )]
    match_ids = [f["match_id"] for f in fixtures if f["match_id"]]
    marks = ",".join("?" * len(match_ids)) or "NULL"
    games_won: dict[int, list[int]] = {}
    for r in conn.execute(
        f"""SELECT match_id, winner_player, COUNT(*) AS n FROM games
            WHERE match_id IN ({marks}) AND winner_player IS NOT NULL GROUP BY 1, 2""",
        match_ids,
    ):
        games_won.setdefault(r["match_id"], [0, 0])[r["winner_player"] - 1] = r["n"]
    # Playing time per match, in minutes: the span of its turns with pauses taken out
    # (gaps over PAUSE_GAP between consecutive turns, e.g. a stopped runner, count as zero).
    times: dict[int, list[float]] = {}
    for r in conn.execute(
        f"""SELECT g.match_id, t.created_at FROM turns t JOIN games g ON g.id = t.game_id
            WHERE g.match_id IN ({marks}) ORDER BY g.match_id, t.created_at""",
        match_ids,
    ):
        times.setdefault(r["match_id"], []).append(datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).timestamp())
    for f in fixtures:
        ts = times.get(f["match_id"], [])
        f["minutes"] = round(sum(min(b - a, PAUSE_GAP) for a, b in zip(ts, ts[1:])) / 60, 1) if len(ts) > 1 else None
    return fixtures, games_won


def league_table(names: list[str], fixtures: list[dict], games_won: dict[int, list[int]]) -> list[dict]:
    """League-stage table from finished matches, ordered as `src/league.rs` ranks it."""
    rows = {n: dict(name=n, played=0, won=0, drawn=0, lost=0, points=0, gw=0, gl=0, pf=0, pa=0) for n in names}
    for f in fixtures:
        if f["stage"] != "league" or f["status"] != "finished":
            continue
        gw = games_won.get(f["match_id"], [0, 0])
        for side, name in enumerate((f["model1"], f["model2"])):
            row, other = rows[name], 1 - side
            row["played"] += 1
            row["gw"] += gw[side]
            row["gl"] += gw[other]
            row["pf"] += (f["score1"], f["score2"])[side]
            row["pa"] += (f["score1"], f["score2"])[other]
            if f["winner"] is None:
                row["drawn"] += 1
                row["points"] += DRAW_POINTS
            elif f["winner"] == side + 1:
                row["won"] += 1
                row["points"] += WIN_POINTS
            else:
                row["lost"] += 1
    order = {n: i for i, n in enumerate(names)}
    return sorted(rows.values(), key=lambda r: (-r["points"], -r["gw"], r["gl"], order[r["name"]]))


def last_activity(conn: sqlite3.Connection, lid: int) -> str | None:
    """Newest move or match start in the league."""
    return conn.execute(
        """SELECT MAX(t) FROM (
               SELECT MAX(t.created_at) AS t FROM turns t JOIN games g ON g.id = t.game_id
               JOIN league_matches lm ON lm.match_id = g.match_id WHERE lm.league_id = ?1
               UNION ALL
               SELECT MAX(m.started_at) FROM matches m
               JOIN league_matches lm ON lm.match_id = m.id WHERE lm.league_id = ?1)""",
        (lid,),
    ).fetchone()[0]


def league_state(league: sqlite3.Row, last: str | None) -> str:
    """finished, live (activity in the last LIVE_SECONDS), or stopped part-way."""
    if league["status"] == "finished":
        return "finished"
    if last and time.time() - datetime.fromisoformat(last).timestamp() < LIVE_SECONDS:
        return "live"
    return "stopped"


GAME_TOTALS = """SELECT COUNT(*) AS games, AVG(g.turns) AS avg_turns,
                        SUM(g.result = 'turn_limit') AS turn_limit, SUM(g.result = 'timeout') AS timeouts,
                        SUM(g.result IN ('gammon', 'backgammon')) AS gammons
                 FROM games g JOIN league_matches lm ON lm.match_id = g.match_id AND lm.league_id = ?
                 WHERE g.winner_player IS NOT NULL"""


def live_game(conn: sqlite3.Connection, fixture: dict, game: sqlite3.Row) -> dict:
    """One game of a running match at its newest roll, as the live card shows it."""
    turn = conn.execute(
        "SELECT * FROM turns WHERE game_id = ? ORDER BY turn_no DESC LIMIT 1", (game["id"],)
    ).fetchone()
    names = (fixture["model1"], fixture["model2"])
    return {
        "turn_id": turn["id"] if turn else None,
        "round": game["round_no"],
        "leg": game["leg"],
        "white": names[game["white_player"] - 1],
        "black": names[2 - game["white_player"]],
        "turn": turn["turn_no"] if turn else 0,
        "mover": names[turn["player"] - 1] if turn else None,
        "dice": [turn["die1"], turn["die2"]] if turn else None,
        "move": turn["move"] if turn else None,
        "decided_by": turn["decided_by"] if turn else None,
        "latency_ms": turn["latency_ms"] if turn else None,
        "legal": turn["legal_count"] if turn else None,
        # Position before that move, white's perspective.
        "position": json.loads(turn["position"]) if turn else None,
        "at": turn["created_at"] if turn else game["started_at"],
        "game_over": game["finished_at"] is not None,
    }


def snapshot(db: Path, league_id: int | None) -> dict:
    with connect(db) as conn:
        league = conn.execute(
            "SELECT * FROM leagues WHERE id = ?" if league_id else "SELECT * FROM leagues ORDER BY id DESC LIMIT 1",
            (league_id,) if league_id else (),
        ).fetchone()
        if league is None:
            return {"error": "no league in this database"}
        lid = league["id"]
        names = [m["name"] for m in json.loads(league["models"])]
        fixtures, games_won = league_fixtures(conn, lid)
        state = league_state(league, last_activity(conn, lid))

        # The game in progress (or the last one) of every running match: with both games of
        # a round played at once (mirror_concurrent), the one that moved last, plus `games`:
        # both games of that round, each at its own newest roll. A stopped league's
        # interrupted matches are not live.
        concurrent = bool(league["mirror_concurrent"]) if "mirror_concurrent" in league.keys() else False
        live = {}
        for f in fixtures:
            if state != "live" or f["status"] != "running":
                continue
            game = conn.execute(
                """SELECT * FROM games g WHERE match_id = ?
                   ORDER BY finished_at IS NULL DESC,
                            (SELECT MAX(t.id) FROM turns t WHERE t.game_id = g.id) DESC, id DESC
                   LIMIT 1""",
                (f["match_id"],),
            ).fetchone()
            if game is None:
                continue
            live[f["match_id"]] = live_game(conn, f, game)
            if concurrent:
                live[f["match_id"]]["games"] = [live_game(conn, f, g) for g in conn.execute(
                    "SELECT * FROM games WHERE match_id = ? AND round_no = ? ORDER BY leg, id",
                    (f["match_id"], game["round_no"]),
                ).fetchall()]

        def model(player_col: str) -> str:
            """League name of the player in `player_col` (1 = model1, 2 = model2)."""
            return f"CASE {player_col} WHEN 1 THEN lm.model1 ELSE lm.model2 END"

        # 'fallback': the answer named no legal play, so a random legal play was made.
        # The v3 per-decision columns, only when this database has them.
        v3 = (
            """, SUM(t.decided_by IN ('model', 'fallback') AND t.probability_source IS NOT NULL) AS with_probs,
                 AVG(CASE WHEN t.decided_by IN ('model', 'fallback') THEN t.request_ms END) AS avg_request_ms,
                 SUM(t.cost_usd) AS cost_usd"""
            if {"probability_source", "request_ms", "cost_usd"} <= columns(conn, "turns") else ""
        )
        decisions = {r["name"]: dict(r) for r in conn.execute(
            f"""SELECT {model('t.player')} AS name,
                       SUM(t.decided_by IN ('model', 'fallback', 'timeout')) AS decisions,
                       AVG(CASE WHEN t.decided_by IN ('model', 'fallback') THEN t.latency_ms END) AS avg_ms,
                       MAX(CASE WHEN t.decided_by IN ('model', 'fallback') THEN t.latency_ms END) AS max_ms,
                       SUM(t.decided_by = 'fallback') AS invalid,
                       SUM(t.decided_by = 'timeout') AS timeouts,
                       SUM(t.move LIKE '%*%' AND t.decided_by IN ('model', 'fallback')) AS hits,
                       SUM(t.input_tokens) AS input_tokens{v3}
                FROM turns t JOIN games g ON g.id = t.game_id
                JOIN league_matches lm ON lm.match_id = g.match_id AND lm.league_id = ?
                GROUP BY 1""",
            (lid,),
        )}
        outcomes: dict[str, dict] = {}
        for r in conn.execute(
            f"""SELECT {model('g.winner_player')} AS name, g.result, COUNT(*) AS n
                FROM games g JOIN league_matches lm ON lm.match_id = g.match_id AND lm.league_id = ?
                WHERE g.winner_player IS NOT NULL GROUP BY 1, 2""",
            (lid,),
        ):
            outcomes.setdefault(r["name"], {})[r["result"]] = r["n"]
        game_totals = conn.execute(GAME_TOTALS, (lid,)).fetchone()
        recent = [dict(r) for r in conn.execute(
            f"""SELECT lm.label, g.round_no, g.leg, g.result, g.points, g.turns, g.finished_at,
                       {model('g.winner_player')} AS winner
                FROM games g JOIN league_matches lm ON lm.match_id = g.match_id AND lm.league_id = ?
                WHERE g.winner_player IS NOT NULL ORDER BY g.finished_at DESC LIMIT 25""",
            (lid,),
        )]
        # Mean seconds per decision in each match, per player and for both together.
        timing = {}
        ids = [f["match_id"] for f in fixtures if f["match_id"]]
        if ids:
            for r in conn.execute(
                f"""SELECT g.match_id, t.player, COUNT(*) AS n, SUM(t.latency_ms) AS ms
                    FROM turns t JOIN games g ON g.id = t.game_id
                    WHERE g.match_id IN ({','.join('?' * len(ids))})
                      AND t.decided_by IN ('model', 'fallback', 'timeout')
                    GROUP BY 1, 2""",
                ids,
            ):
                timing.setdefault(r["match_id"], {})[r["player"]] = (r["n"], r["ms"] or 0)

    table = league_table(names, fixtures, games_won)

    for f in fixtures:
        f["games_won"] = games_won.get(f["match_id"], [0, 0])
        f["live"] = live.get(f["match_id"])
        per = timing.get(f["match_id"], {})
        f["s_move"] = [round(per[p][1] / per[p][0] / 1000, 2) if p in per and per[p][0] else None for p in (1, 2)]
        n = sum(v[0] for v in per.values())
        f["s_turn"] = round(sum(v[1] for v in per.values()) / n / 1000, 2) if n else None

    return {
        "league": {
            "id": lid,
            "status": state,
            "note": league["note"],
            "seed": unsigned(league["seed"]),
            # v3 leagues only.
            "prompt_version": league["prompt_version"] if "prompt_version" in league.keys() else None,
            "order_seed": unsigned(league["order_seed"]) if "order_seed" in league.keys() else None,
            "rounds": league["rounds"],
            "clock_seconds": league["clock_seconds"],
            "delay_seconds": league["delay_seconds"],
            "max_turns": league["max_turns"],
            "started_at": league["started_at"],
            "finished_at": league["finished_at"],
            "ranking": json.loads(league["ranking"]) if league["ranking"] else None,
            "models": json.loads(league["models"]),
        },
        "table": table,
        "fixtures": fixtures,
        "models": [
            {"name": n, **decisions.get(n, {}), "outcomes": outcomes.get(n, {})} for n in names
        ],
        "v3": bool(v3),
        "games": dict(game_totals),
        "recent": recent,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def history(db: Path) -> dict:
    """Every league, newest first: what it tested, how far it got, its table and game totals."""
    leagues = []
    with connect(db) as conn:
        for league in conn.execute("SELECT * FROM leagues ORDER BY id DESC").fetchall():
            lid = league["id"]
            names = [m["name"] for m in json.loads(league["models"])]
            fixtures, games_won = league_fixtures(conn, lid)
            last = last_activity(conn, lid)
            leagues.append({
                "id": lid,
                "status": league_state(league, last),
                "note": league["note"],
                "started_at": league["started_at"],
                "finished_at": league["finished_at"],
                "last_activity": last,
                "rounds": league["rounds"],
                "models": json.loads(league["models"]),
                "matches_done": sum(f["status"] == "finished" for f in fixtures),
                "matches_total": len(fixtures),
                "games": dict(conn.execute(GAME_TOTALS, (lid,)).fetchone()),
                "ranking": json.loads(league["ranking"]) if league["ranking"] else None,
                "table": league_table(names, fixtures, games_won),
            })
    return {"leagues": leagues, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def round_turns(db: Path, match_id: int, round_no: int) -> dict:
    """Every roll of one round (both games), oldest first, in the shape of a live game."""
    with connect(db) as conn:
        fixture = conn.execute(
            "SELECT model1, model2 FROM league_matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if fixture is None:
            return {"error": f"no league match #{match_id}"}
        names = (fixture["model1"], fixture["model2"])
        turns = [
            {
                "turn_id": r["id"],
                "round": round_no,
                "leg": r["leg"],
                "white": names[r["white_player"] - 1],
                "black": names[2 - r["white_player"]],
                "turn": r["turn_no"],
                "mover": names[r["player"] - 1],
                "dice": [r["die1"], r["die2"]],
                "move": r["move"],
                "decided_by": r["decided_by"],
                "latency_ms": r["latency_ms"],
                "legal": r["legal_count"],
                # Position before the move, white's perspective.
                "position": json.loads(r["position"]),
                "at": r["created_at"],
                # The game has ended, so this list of its rolls is complete.
                "game_over": r["finished_at"] is not None,
            }
            for r in conn.execute(
                """SELECT t.id, g.leg, g.white_player, t.turn_no, t.player, t.die1, t.die2, t.move,
                          t.decided_by, t.latency_ms, t.legal_count, t.position, t.created_at, g.finished_at
                   FROM turns t JOIN games g ON g.id = t.game_id
                   WHERE g.match_id = ? AND g.round_no = ? ORDER BY g.leg, t.turn_no""",
                (match_id, round_no),
            )
        ]
    return {"match_id": match_id, "round": round_no, "turns": turns}


def turn_context(db: Path, turn_id: int) -> dict:
    """What was sent to the model for one roll and what it answered: one entry per request
    (play lists above a service's option limit are split into several)."""
    with connect(db) as conn:
        # The v3 per-decision fields the dialog shows, when this database has them.
        extra = [c for c in ("letter", "probability_source", "request_ms", "cost_usd", "provider",
                             "quantization", "prompt_version") if c in columns(conn, "turns")]
        turn = conn.execute(
            f"SELECT {', '.join(['turn_no', 'die1', 'die2', 'move', 'decided_by', *extra])} FROM turns WHERE id = ?",
            (turn_id,),
        ).fetchone()
        if turn is None:
            return {"error": f"no turn #{turn_id}"}
        exchanges = []
        for r in conn.execute(
            "SELECT request, response, error, latency_ms FROM exchanges WHERE turn_id = ? ORDER BY id",
            (turn_id,),
        ):
            try:
                request = json.loads(r["request"])
            except ValueError:
                request = {}
            # System One: `state` + `questions.play.criteria`; OpenAI Decisions: `input` +
            # `questions[0].choices`; LLMs: chat messages.
            questions = request.get("questions")
            # The option text the model read: the description (older requests repeat the play).
            if isinstance(questions, dict):
                options = [str(v) for v in next(iter(questions.values()), {}).get("criteria", {}).values()]
            elif isinstance(questions, list) and questions:
                options = [c.get("description") or c.get("value") for c in questions[0].get("choices", [])]
            else:
                options = []
            context = request.get("state", request.get("input"))
            if context is None and "messages" in request:
                context = "\n\n".join(str(m.get("content")) for m in request["messages"])
            if not isinstance(context, str):
                context = json.dumps(context, indent=2)
            exchanges.append({
                "model": request.get("model"),
                "context": context,
                "options": options,
                "response": r["response"],
                "error": r["error"],
                "latency_ms": r["latency_ms"],
            })
    return {"turn": dict(turn), "exchanges": exchanges}


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>jevgammon league</title>
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#2a2f3a;--fg:#e6e8ec;--mute:#8a91a0;--acc:#6aa9ff;--win:#4cc38a;--draw:#d9b44a;--loss:#e5636b;--wc:#d5dae3;--bc:#d9534f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline}
h1{font-size:18px;margin:0}h2{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:0 0 10px}
.meta{color:var(--mute)}main{display:grid;gap:16px;padding:16px 20px;grid-template-columns:repeat(auto-fit,minmax(420px,1fr))}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}
.wide{grid-column:1/-1}table{border-collapse:collapse;width:100%}th,td{padding:5px 8px;text-align:right;white-space:nowrap}
th{color:var(--mute);font-weight:500;border-bottom:1px solid var(--line)}td:first-child,th:first-child,td.l,th.l{text-align:left}
tbody tr+tr td{border-top:1px solid #20242d}.pts{font-weight:700;color:var(--acc)}.top td{background:#1b2230}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px;background:#232836;color:var(--mute)}
.running{background:#16324f;color:#9cc7ff}.finished{background:#1c3327;color:#8fe0b3}.aborted{background:#3d1d22;color:#ff9aa1}.deferred{background:#3d331d;color:#ffd27a}
.w{color:var(--win);font-weight:600}.live{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.card{border:1px solid var(--line);border-radius:8px;padding:10px}.card h3{margin:0 0 4px;font-size:14px}
/* Both games of a round played at once: the card spans the row, one board per game. */
.card.duo{grid-column:1/-1}.games{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));margin-top:4px}
.board{display:grid;grid-template-columns:repeat(13,1fr);gap:2px;margin:8px 0;font-size:11px;text-align:center}
.pt{background:#20242d;border-radius:3px;min-height:22px;padding:2px 0}
/* Checker colours: one per side, shared by board cells, legend discs and names. */
.pt.wc{background:var(--wc);color:#12151b;font-weight:700}.pt.wc .num{color:#5a6070}
.pt.bc{background:var(--bc);color:#fff;font-weight:700}.pt.bc .num{color:#ffd3d1}
.pt.bar{background:#111;color:var(--mute)}.num{color:#555b68;font-size:10px}
.disc{display:inline-block;width:.75em;height:.75em;border-radius:50%;vertical-align:-.05em;margin-right:1px}
.disc.dw{background:var(--wc)}.disc.db{background:var(--bc)}
.cw{color:var(--wc);font-weight:600}.cb{color:var(--bc);font-weight:600}
/* Home-board labels: points 19-24 (black) above the top right, 1-6 (white) below the bottom right. */
.home{grid-column:8/14;font-size:11px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.home.top{border-bottom:2px solid var(--bc)}.home.bottom{border-top:2px solid var(--wc)}.homegap{grid-column:1/8}
.nav{display:flex;gap:6px;align-items:center;margin-top:8px}.nav button{background:#232836;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:2px 10px;font:inherit;cursor:pointer}
.nav button:disabled{opacity:.35;cursor:default}.nav button:not(:disabled):hover{border-color:var(--acc)}
.mute{color:var(--mute)}.days{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.day h3{margin:0 0 6px;font-size:13px;color:var(--mute)}.fx{display:flex;justify-content:space-between;gap:8px;padding:3px 0}
.fx .s{font-variant-numeric:tabular-nums;min-width:52px;text-align:center}footer{padding:0 20px 20px;color:var(--mute);font-size:12px}
dialog{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:8px;width:min(1000px,94vw);max-height:90vh;padding:14px}
dialog::backdrop{background:#000a}dialog pre{white-space:pre-wrap;word-break:break-word;background:#0b0d11;border:1px solid var(--line);border-radius:6px;padding:10px;font:12px/1.4 ui-monospace,monospace;max-height:55vh;overflow:auto}
dialog .head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}dialog h3{margin:0}
/* History: one row per league; the league on view is highlighted. */
#history tbody tr{cursor:pointer}#history tbody tr:hover td{background:#1d2230}#history tr.sel td{background:#1b2a40}
#history td.note{white-space:normal;text-align:left;min-width:280px;max-width:520px;color:var(--mute);font-size:13px}
.note details{margin-top:2px}.note summary{cursor:pointer;color:var(--acc);font-size:12px}.note ul{margin:4px 0 0;padding-left:18px}.note li{margin:2px 0}
#note.note{max-width:900px}
a.mlink{color:inherit;text-decoration:none;border-bottom:1px dotted var(--mute)}a.mlink:hover{color:var(--acc)}
.mtable{width:100%}.mtable td{padding:4px 8px}.m-win td{background:#4cc38a26}.m-win td:nth-child(4){color:var(--win);font-weight:600}
.m-loss td{background:#e5636b26}.m-loss td:nth-child(4){color:var(--loss);font-weight:600}.m-draw td{background:#d9b44a26}.m-draw td:nth-child(4){color:var(--draw);font-weight:600}
.m-open td{color:var(--mute)}
h2 .seasons{float:right;text-transform:none;letter-spacing:0;display:flex;gap:6px;align-items:center}
.seasons button{background:#232836;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:0 9px;font:inherit;cursor:pointer}
.seasons button:disabled{opacity:.35;cursor:default}
#note{flex-basis:100%;color:var(--mute);font-size:13px}header a{color:var(--acc)}
/* Pause / Resume (--control): the league runner and the GPU servers it uses. */
#control{margin-left:auto;display:flex;flex-wrap:wrap;gap:8px;align-items:center}#control[hidden]{display:none}
#control button{background:#232836;color:var(--fg);border:1px solid var(--acc);border-radius:6px;padding:5px 14px;font:inherit;font-weight:600;cursor:pointer}
#control button[data-action=pause]{border-color:var(--draw);color:#ffd27a}#control button[data-action=resume]{border-color:var(--win);color:#8fe0b3}
#control button:disabled{opacity:.7;cursor:default;border-color:var(--line);color:var(--mute)}#control button:not(:disabled):hover{background:#2b3142}
#ctlStatus.error{color:var(--loss)}
.spin{display:inline-block;width:.8em;height:.8em;border:2px solid var(--mute);border-top-color:transparent;border-radius:50%;vertical-align:-.1em;margin-right:4px;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style></head><body>
<dialog id="ctx"><div class="head"><h3 id="ctxTitle"></h3><button onclick="$('ctx').close()">close</button></div><div id="ctxBody"></div></dialog>
<header><h1>jevgammon league <span id="lid"></span></h1><span id="status"></span><span class="meta" id="rules"></span><span class="meta" id="updated"></span><a href="report/" target="_blank" id="report" hidden>report (working copy)</a><a href="#" id="latest" hidden>back to the latest league</a><div id="control" hidden><span id="ctlButtons"></span><span class="meta" id="ctlStatus"></span></div><div id="note" class="note"></div></header>
<main>
<section class="wide"><h2>History</h2><table id="history"></table><div class="mute" style="margin-top:8px">Click a league to view it. Live: moved in the last 10 minutes; stopped: ended before its last match, so only its finished matches count.</div></section>
<section><h2>Table <span class="seasons"><button id="prevSeason" title="previous league">&lsaquo;</button><span id="season"></span><button id="nextSeason" title="next league">&rsaquo;</button></span></h2><table id="table"></table><div class="mute" style="margin-top:8px">3 points per win, 1 per draw; ties: more games won, then fewer games lost. PF/PA are backgammon points. The arrows step through finished leagues and the live one.</div></section>
<section><h2>Models</h2><table id="models"></table><div class="mute" style="margin-top:8px" id="totals"></div></section>
<section class="wide"><h2>Live</h2><div class="live" id="live"></div></section>
<section class="wide"><h2>Fixture</h2><div class="days" id="fixture"></div></section>
<section class="wide"><h2>Recent games</h2><table id="recent"></table></section>
</main>
<footer>Refreshes every 5 s · <span id="ranking"></span></footer>
<script>
const $=id=>document.getElementById(id);
// Side markers in the same colours as the board's checkers.
const W='<span class="disc dw"></span>',B='<span class="disc db"></span>';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const clock=s=>s==null?'off':`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
const ago=t=>{if(!t)return'';const s=Math.max(0,(Date.now()-Date.parse(t))/1000);return s<60?`${s|0}s ago`:s<3600?`${(s/60)|0}m ago`:`${(s/3600).toFixed(1)}h ago`};
const pct=(a,b)=>b?`${(100*a/b).toFixed(0)}%`:'–';
function board(p,white,black){ if(!p)return'';
  // White's perspective: points[i] is white's point i+1 (+ white, - black). Top row 13..24, bottom 12..1.
  const cell=(i)=>{const v=p.points[i];const c=v>0?'wc':v<0?'bc':'';return `<div class="pt ${c}">${v?Math.abs(v):''}<div class="num">${i+1}</div></div>`};
  let top='',bot='';
  for(let i=12;i<24;i++){top+=cell(i);if(i===17)top+=`<div class="pt bar">${p.bar.black?B+p.bar.black:''}</div>`}
  for(let i=11;i>=0;i--){bot+=cell(i);if(i===6)bot+=`<div class="pt bar">${p.bar.white?W+p.bar.white:''}</div>`}
  const label=(cls,side,name)=>`<div class="homegap"></div><div class="home ${cls} ${side}">${esc(name)} home</div>`;
  return `<div class="board">${label('top','cb',black)}${top}${bot}${label('bottom','cw',white)}</div><div class="mute">off: ${W} ${p.off.white} · ${B} ${p.off.black}</div>`;
}
function render(d){
  if(d.error){$('status').textContent=d.error;return}
  const L=d.league;
  $('lid').textContent='#'+L.id;
  $('status').innerHTML=pill(L.status);
  $('note').innerHTML=noteHtml(L.note,'head');
  $('latest').hidden=selected==null;
  $('rules').textContent=`${L.rounds} rounds per match · clock ${clock(L.delay_seconds)} delay + ${clock(L.clock_seconds)} bank · turn limit ${L.max_turns??'off'} · seed ${L.seed}`+
    (L.order_seed!=null?` · option order seed ${L.order_seed}`:'')+(L.prompt_version?` · prompt ${L.prompt_version}`:'');
  $('updated').textContent='updated '+new Date(d.generated_at).toLocaleTimeString();
  $('table').innerHTML='<thead><tr><th>#</th><th class="l">Model</th><th>P</th><th>W</th><th>D</th><th>L</th><th>Pts</th><th>GW</th><th>GL</th><th>PF</th><th>PA</th></tr></thead><tbody>'+
    d.table.map((r,i)=>`<tr class="${i<3?'top':''}"><td>${i+1}</td><td class="l"><a href="#" class="mlink" data-model="${esc(r.name)}" title="show this model's matches">${esc(r.name)}</a></td><td>${r.played}</td><td>${r.won}</td><td>${r.drawn}</td><td>${r.lost}</td><td class="pts">${r.points}</td><td>${r.gw}</td><td>${r.gl}</td><td>${r.pf}</td><td>${r.pa}</td></tr>`).join('')+'</tbody>';
  // Player config per name: spec plus provider / quantization / device when the league recorded them.
  const player=n=>{const c=(L.models||[]).find(x=>x.name===n)||{};return [c.spec,c.provider,c.quantization,c.device].filter(Boolean).join(' · ')};
  const sec=ms=>ms!=null?(ms/1000).toFixed(2)+'s':'–';
  $('models').innerHTML='<thead><tr><th class="l">Model</th><th>Decisions</th><th>Avg</th><th>Max</th><th>Hit %</th><th title="the answer named no legal play; a random legal play was made">Invalid</th><th>Timeout</th>'+
    (d.v3?'<th title="decisions with option probabilities">Probs %</th><th title="mean request time, retries excluded">Request</th><th>Cost</th>':'')+'<th>G/BG won</th></tr></thead><tbody>'+
    d.models.map(m=>{const o=m.outcomes||{},n=m.decisions||0;return `<tr><td class="l">${esc(m.name)} <span class="mute">${esc(player(m.name))}</span></td><td>${n}</td><td>${sec(m.avg_ms)}</td><td>${m.max_ms!=null?(m.max_ms/1000).toFixed(1)+'s':'–'}</td><td>${pct(m.hits||0,n)}</td><td>${m.invalid??0} <span class="mute">(${pct(m.invalid||0,n)})</span></td><td>${m.timeouts??0}</td>`+
      (d.v3?`<td>${pct(m.with_probs||0,n)}</td><td>${sec(m.avg_request_ms)}</td><td>${m.cost_usd!=null?'$'+m.cost_usd.toFixed(4):'–'}</td>`:'')+`<td>${(o.gammon||0)}/${(o.backgammon||0)}</td></tr>`}).join('')+'</tbody>';
  const g=d.games;
  $('totals').textContent=g.games?`${g.games} games · avg ${Math.round(g.avg_turns)} turns · ${g.turn_limit} at the turn limit (${pct(g.turn_limit,g.games)}) · ${g.gammons} gammons/backgammons · ${g.timeouts} lost on time`:'no finished games yet';
  const running=d.fixtures.filter(f=>f.live);
  $('live').innerHTML=running.length?running.map(f=>{
    const gs=slots(f);
    // One game: its newest roll (live) or the roll being browsed, with its own navigation.
    const game=(lv,k)=>{
      const s=view[f.match_id+':'+k], v=s?s.turns[s.i]:lv, at=`data-id="${f.match_id}" data-slot="${k}"`;
      const last=s&&s.i===s.turns.length-1&&s.turns[s.i].game_over;
      const nav=`<div class="nav"><button ${at} data-step="start" title="first roll of round ${v.round} game ${v.leg}">&#9198; round start</button><button ${at} data-step="prev" ${s&&s.i===0?'disabled':''}>&laquo;</button><button ${at} data-step="next" ${s&&!last?'':'disabled'}>&raquo;</button><button ${at} data-step="live" ${s?'':'disabled'}>live</button><button data-ctx="${v.turn_id??''}" ${v.turn_id&&v.decided_by!=='forced'&&v.decided_by!=='no_move'?'':'disabled'} title="what was sent to the model for this roll">context</button>${s?`<span class="pill">roll ${s.i+1} of ${s.turns.length} · round ${s.round} game ${s.leg}</span>`:''}</div>`;
      return `<div class="mute">round ${v.round} game ${v.leg} · ${W} <span class="cw">${esc(v.white)}</span> v ${B} <span class="cb">${esc(v.black)}</span> · turn ${v.turn}${L.max_turns?' / '+L.max_turns:''}${!s&&lv.game_over?' · game over':''}</div>
    ${board(v.position,v.white,v.black)}
    <div>${v.mover?`<span class="${v.mover===v.white?'cw':'cb'}">${esc(v.mover)}</span> rolled ${v.dice.join('-')}: <b>${esc(v.move||'(no move)')}</b> <span class="mute">${how(v.decided_by)}${v.decided_by==='model'||v.decided_by==='fallback'?`, ${(v.latency_ms/1000).toFixed(1)}s of ${v.legal} plays`:''} · ${ago(v.at)}</span>`:'<span class="mute">starting</span>'}</div>${nav}`};
    return `<div class="card${gs.length>1?' duo':''}"><h3>${esc(f.label)}</h3>
    <div><b>${esc(f.model1)}</b> <span class="pts">${f.score1} – ${f.score2}</span> <b>${esc(f.model2)}</b> <span class="mute">(games ${f.games_won[0]}–${f.games_won[1]})</span></div>
    ${gs.length>1?`<div class="games">${gs.map((lv,k)=>`<div>${game(lv,k)}</div>`).join('')}</div>`:game(gs[0],0)}</div>`}).join(''):`<div class="mute">${L.status==='live'?'no match running':`league #${L.id} is ${L.status}`}</div>`;
  const days={};for(const f of d.fixtures){const k=f.stage==='playoff'?'Playoffs':f.stage==='playoff-stale'?'Playoffs (stale: players added after them)':'Matchday '+f.matchday;(days[k]=days[k]||[]).push(f)}
  $('fixture').innerHTML=Object.entries(days).map(([k,fs])=>`<div class="day"><h3>${k}</h3>`+fs.map(f=>{
    // Deferred: failed, waiting for the failing model's backoff; resumes from its last turn.
    const st=f.status!=='finished'&&f.status!=='running'&&f.deferred_error?'deferred':f.status||'pending';const w1=f.winner===1,w2=f.winner===2;
    const score=f.status?`${f.score1} – ${f.score2}`:'v';
    const tip=st==='deferred'?` title="${esc('failed '+new Date(f.deferred_at).toLocaleString()+': '+f.deferred_error)}"`:'';
    return `<div class="fx"><span class="${w1?'w':''}">${esc(f.model1)}</span><span class="s">${score}</span><span class="${w2?'w':''}">${esc(f.model2)}</span><span class="pill ${st}"${tip}>${st==='finished'&&f.winner==null?'draw':st}</span></div>`}).join('')+'</div>').join('');
  $('recent').innerHTML='<thead><tr><th class="l">When</th><th class="l">Match</th><th>Game</th><th class="l">Winner</th><th class="l">Result</th><th>Pts</th><th>Turns</th></tr></thead><tbody>'+
    d.recent.map(r=>`<tr><td class="l mute">${ago(r.finished_at)}</td><td class="l">${esc(r.label)}</td><td>${r.round_no}.${r.leg}</td><td class="l">${esc(r.winner)}</td><td class="l">${esc(r.result.replace('_',' '))}</td><td>${r.points}</td><td>${r.turns}</td></tr>`).join('')+'</tbody>';
  $('ranking').textContent=L.ranking?'Final ranking: '+L.ranking.join(' · '):'';
}
// turns.decided_by as shown: 'fallback' = the answer named no legal play.
const how=s=>s==='fallback'?'invalid answer, random legal play':s;
const pill=s=>`<span class="pill ${{finished:'finished',live:'running',stopped:'aborted'}[s]||''}">${esc(s)}</span>`;
const span=(a,b)=>{if(!a||!b)return'–';const m=Math.round((Date.parse(b)-Date.parse(a))/60000);return m<60?`${m} min`:`${Math.floor(m/60)} h ${m%60} min`};
// League notes grow with every change; show the first sentence and fold the rest into a list.
const openNotes=new Set();
function noteHtml(note,key){
  const parts=String(note||'').split(/(?<=\.)\s+(?=[A-Z0-9])/).filter(Boolean);
  if(parts.length<=1)return esc(parts[0]||'');
  return `${esc(parts[0])}<details data-note="${key}" ${openNotes.has(key)?'open':''}><summary>${parts.length-1} more</summary><ul>${parts.slice(1).map(p=>`<li>${esc(p)}</li>`).join('')}</ul></details>`;
}
document.addEventListener('toggle',e=>{const k=e.target.dataset&&e.target.dataset.note;if(k){if(e.target.open)openNotes.add(k);else openNotes.delete(k)}},true);
function renderHistory(h){
  const Ls=h.leagues||[];const shown=lastData&&lastData.league?lastData.league.id:null;
  $('history').innerHTML='<thead><tr><th>#</th><th class="l">Status</th><th class="l">Started</th><th>Duration</th><th>Models</th><th>Rounds</th><th>Matches</th><th>Games</th><th>Turn limit</th><th class="l">Leader</th><th class="l">What it tested</th></tr></thead><tbody>'+
    Ls.map(l=>{const g=l.games,leader=l.ranking?l.ranking[0]:(l.matches_done?l.table[0].name:'–');
      return `<tr data-league="${l.id}" class="${l.id===shown?'sel':''}"><td>${l.id}</td><td class="l">${pill(l.status)}</td><td class="l">${new Date(l.started_at).toLocaleString()}</td><td>${span(l.started_at,l.finished_at||l.last_activity)}</td><td>${l.models.length}</td><td>${l.rounds}</td><td>${l.matches_done} / ${l.matches_total}</td><td>${g.games}</td><td>${pct(g.turn_limit||0,g.games)}</td><td class="l">${esc(leader)}${l.ranking?'':l.matches_done?' <span class="mute">(so far)</span>':''}</td><td class="note">${noteHtml(l.note,'h'+l.id)}</td></tr>`}).join('')+'</tbody>';
  // Season arrows: finished leagues plus the live one, oldest to newest.
  const seasons=Ls.filter(l=>l.status!=='stopped').map(l=>l.id).sort((a,b)=>a-b);
  const at=seasons.indexOf(shown);
  $('season').textContent=shown!=null?`#${shown}`:'';
  $('prevSeason').disabled=at<=0;$('nextSeason').disabled=at<0||at>=seasons.length-1;
  $('prevSeason').onclick=()=>at>0&&choose(seasons[at-1]);
  $('nextSeason').onclick=()=>at>=0&&at<seasons.length-1&&choose(seasons[at+1]);
}
// Rolls being browsed per game on a live card: "match_id:slot" -> {round, leg, turn_id, i, turns}
// (turns: that game's rolls). Absent = live. Slot k is the k-th game the card shows.
const view={};let lastData=null,lastHistory=null;
// The games a running match's card shows: both games of the round when they are played at once.
const slots=f=>f.live.games&&f.live.games.length?f.live.games:[f.live];
// League on view: null = the latest one; ?league=N in the address selects one.
let selected=new URLSearchParams(location.search).get('league');selected=selected?+selected:null;
function choose(id){selected=id;for(const k in view)delete view[k];history.replaceState(null,'',id==null?location.pathname:`?league=${id}`);tick()}
$('history').addEventListener('click',e=>{if(e.target.closest('details'))return;const r=e.target.closest('tr[data-league]');if(r)choose(+r.dataset.league)});
$('latest').addEventListener('click',e=>{e.preventDefault();choose(null)});
// Steps run one after another, so quick clicks each start from where the previous one ended.
let stepping=Promise.resolve();
const step=(id,k,dir)=>stepping=stepping.then(()=>stepGame(id,k,dir)).catch(()=>{});
async function stepGame(id,k,dir){
  const f=lastData&&lastData.fixtures.find(x=>x.match_id===id);if(!f||!f.live)return;
  const key=id+':'+k,lv=slots(f)[k];if(!lv)return;
  if(dir==='live'){delete view[key];render(lastData);return}
  const s=view[key],round=s?s.round:lv.round,leg=s?s.leg:lv.leg;
  const r=await fetch(`api/round?match=${id}&round=${round}`,{cache:'no-store'});
  const turns=((await r.json()).turns||[]).filter(t=>t.leg===leg);
  if(!turns.length)return;
  // The game grows while it is browsed: find the shown roll again by its id. Live shows the
  // newest roll, so stepping back from live starts one before it.
  let i=turns.findIndex(t=>t.turn_id===(s?s.turn_id:lv.turn_id));
  if(i<0)i=s?Math.min(s.i,turns.length-1):turns.length;
  i=dir==='start'?0:dir==='prev'?Math.max(0,i-1):i+1;
  // Past the newest stored roll of a running game: back to live once the live view has caught
  // up with it (else it would step back); a finished game stays at its end.
  const newest=turns[turns.length-1];
  if(i>=turns.length&&!newest.game_over&&lv.round===round&&lv.leg===leg&&lv.turn>=newest.turn){delete view[key];render(lastData);return}
  i=Math.min(i,turns.length-1);
  view[key]={round,leg,turn_id:turns[i].turn_id,i,turns};
  render(lastData);
}
// A model's matches in the league on view: green win, red loss, yellow draw, grey not finished.
function showMatches(name){
  const fs=(lastData&&lastData.fixtures||[]).filter(f=>f.model1===name||f.model2===name);
  const rows=fs.map(f=>{const me=f.model1===name?1:2,opp=me===1?f.model2:f.model1;
    const done=f.status==='finished',my=me===1?f.score1:f.score2,their=me===1?f.score2:f.score1;
    const res=!done?'open':f.winner==null?'draw':f.winner===me?'win':'loss';
    const st=done?{win:'won',loss:'lost',draw:'draw'}[res]:(f.status&&f.status!=='running'&&f.deferred_error?'deferred':f.status||'pending');
    const when=f.stage==='playoff'?'playoff':f.stage==='playoff-stale'?'playoff (stale)':'matchday '+f.matchday;
    const sm=f.s_move||[],t=v=>v!=null?v.toFixed(2):'–';
    return {res,html:`<tr class="m-${res}"><td class="l mute">${esc(when)}</td><td class="l">${esc(opp)}</td><td>${f.status?`${my??0} – ${their??0}`:'–'}</td><td class="l">${esc(st)}</td><td>${t(sm[me-1])}</td><td>${t(sm[2-me])}</td><td>${t(f.s_turn)}</td><td>${f.minutes!=null?f.minutes.toFixed(1):'–'}</td></tr>`}});
  const n=k=>rows.filter(r=>r.res===k).length;
  $('ctxTitle').textContent=`${name}: ${n('win')} won · ${n('draw')} drawn · ${n('loss')} lost${n('open')?` · ${n('open')} to play`:''}`;
  $('ctxBody').innerHTML=`<table class="mtable"><thead><tr><th class="l">When</th><th class="l">Opponent</th><th>Score</th><th class="l">Result</th><th title="mean seconds per decision of ${esc(name)} in this match">s/move</th><th title="mean seconds per decision of the opponent">opp. s/move</th><th title="mean seconds per decision over both players' turns">s/turn</th><th title="playing time from first to last move; gaps over 30 min (paused runner) left out">min</th></tr></thead><tbody>${rows.map(r=>r.html).join('')}</tbody></table>`;
  $('ctx').showModal();
}
document.addEventListener('click',e=>{const a=e.target.closest('a.mlink');if(a){e.preventDefault();showMatches(a.dataset.model)}});
// A click on the backdrop (outside the dialog box) closes it; clicks inside the box land on its children.
$('ctx').addEventListener('click',e=>{if(e.target!==$('ctx'))return;const r=$('ctx').getBoundingClientRect();
  if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('ctx').close()});
async function showContext(turnId){
  const d=await (await fetch(`api/context?turn=${turnId}`,{cache:'no-store'})).json();
  if(d.error){$('ctxTitle').textContent=d.error;$('ctxBody').innerHTML='';$('ctx').showModal();return}
  const t=d.turn;
  $('ctxTitle').textContent=`Turn ${t.turn_no} · rolled ${t.die1}-${t.die2} · played ${t.move||'(no move)'} · ${how(t.decided_by)}`;
  // v3 decision fields, when recorded.
  const facts=[t.letter&&(t.decided_by==='fallback'?'random play ':'answer ')+t.letter,t.probability_source&&'probabilities: '+t.probability_source,t.request_ms!=null&&'request '+(t.request_ms/1000).toFixed(2)+'s',
    t.cost_usd!=null&&'$'+t.cost_usd.toFixed(5),t.provider,t.quantization,t.prompt_version&&'prompt '+t.prompt_version].filter(Boolean);
  $('ctxBody').innerHTML=(facts.length?`<p class="mute">${esc(facts.join(' · '))}</p>`:'')+(d.exchanges.length?d.exchanges.map((x,k)=>`
    <p class="mute">request ${k+1} of ${d.exchanges.length}${x.model?' · model '+esc(x.model):''} · ${x.context.length} chars · ${(x.latency_ms/1000).toFixed(2)}s${x.error?' · <span style="color:var(--loss)">'+esc(x.error)+'</span>':''}</p>
    <b>Context sent</b><pre>${esc(x.context)}</pre>
    ${x.options.length?`<b>Options (${x.options.length})</b><pre>${esc(x.options.join('\n'))}</pre>`:''}
    <b>Response</b><pre>${esc(x.response??'(none)')}</pre>`).join(''):`<p class="mute">${t.decided_by==='forced'||t.decided_by==='no_move'?'No request was sent for this roll (forced or no legal move).':'No request was recorded for this roll: this player decides locally (baseline or engine).'}</p>`);
  $('ctx').showModal();
}
$('live').addEventListener('click',e=>{const c=e.target.closest('button[data-ctx]');if(c&&!c.disabled){showContext(+c.dataset.ctx);return}
  const b=e.target.closest('button[data-step]');if(b&&!b.disabled)step(+b.dataset.id,+b.dataset.slot,b.dataset.step)});
// Pause / Resume, when the server runs with --control: GET api/control is the runner's state.
let control=null;
function renderControl(c){
  control=c;$('control').hidden=!c||!c.enabled;if($('control').hidden)return;
  const busy=c.state==='pausing'||c.state==='resuming';
  const btn=(a,label)=>`<button data-action="${a}">${label}</button>`;
  $('ctlButtons').innerHTML=busy?`<button disabled><span class="spin"></span>${c.state==='pausing'?'Pausing… (stopping the league, then the GPU servers)':'Resuming… (loading the GPU servers, about 3 min)'}</button>`:
    c.state==='running'?btn('pause','Pause (frees GPUs)'):c.state==='paused'?btn('resume','Resume'):btn('pause','Pause (frees GPUs)')+' '+btn('resume','Resume');
  $('ctlStatus').className=c.state==='error'?'meta error':'meta';
  $('ctlStatus').textContent=`${c.unit||'league'}: ${c.state}`+(c.since?` since ${new Date(c.since).toLocaleString()} (${ago(c.since)})`:'')+(c.message?` · ${c.message}`:'');
}
const CONFIRM={pause:'Pause the league?\n\nThe league runner stops (unfinished matches resume from their last turn), then the Gemma and Open-Jev servers stop and free the GPUs. Takes about a minute.',
  resume:'Resume the league?\n\nThe Gemma and Open-Jev servers start on the GPUs (about 3 minutes), then the league runner continues where it stopped.'};
$('ctlButtons').addEventListener('click',async e=>{
  const b=e.target.closest('button[data-action]');if(!b||b.disabled)return;
  const a=b.dataset.action;if(!confirm(CONFIRM[a]))return;
  renderControl({...control,state:a==='pause'?'pausing':'resuming',since:new Date().toISOString(),message:'starting'});
  try{const r=await fetch('api/control',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-League-Control':'1'},body:JSON.stringify({action:a})});
    const d=await r.json();if(!r.ok)alert(`Could not ${a}: ${d.error}`);
  }catch(err){alert(`Could not ${a}: ${err}`)}
  refreshControl();
});
function refreshControl(){fetch('api/control',{cache:'no-store'}).then(r=>r.json()).then(renderControl).catch(()=>{})}
async function tick(){refreshControl();try{
  const [s,h]=await Promise.all([fetch(selected==null?'api/state':`api/state?league=${selected}`,{cache:'no-store'}),fetch('api/history',{cache:'no-store'})]);
  lastData=await s.json();lastHistory=await h.json();render(lastData);renderHistory(lastHistory);
}catch(e){$('updated').textContent='update failed: '+e}}
tick();setInterval(tick,5000);
fetch('report/',{method:'HEAD',cache:'no-store'}).then(r=>{if(r.ok)$('report').hidden=false}).catch(()=>{});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    db: Path
    league_id: int | None
    # --control script, or None (no Pause / Resume button).
    control: Path | None = None
    # --report: the working copy of the published report page, served at /report/.
    report: Path | None = None
    # Rendered JSON per key ("state:<league>", "history"), with the time it was built.
    cache: dict[str, tuple[float, bytes]] = {}

    def cached(self, key: str, build) -> bytes:
        now = time.monotonic()
        hit = self.cache.get(key)
        if hit is None or now - hit[0] > CACHE_SECONDS:
            try:
                body = json.dumps(build()).encode()
            except sqlite3.Error as error:
                body = json.dumps({"error": f"database: {error}"}).encode()
            hit = self.cache[key] = (now, body)
        return hit[1]

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.reply(200, "text/html; charset=utf-8", PAGE.encode())
        elif path in ("/report", "/report/"):
            if not self.report or not self.report.is_file():
                self.reply(404, "text/plain", b"no report page (--report)")
                return
            self.reply(200, "text/html; charset=utf-8", self.report.read_bytes())
        elif path == "/api/context":
            query = parse_qs(urlparse(self.path).query)
            try:
                turn_id = int(query["turn"][0])
            except (KeyError, ValueError):
                self.reply(400, "text/plain", b"need integer turn")
                return
            try:
                body = json.dumps(turn_context(self.db, turn_id)).encode()
            except sqlite3.Error as error:
                body = json.dumps({"error": f"database: {error}"}).encode()
            self.reply(200, "application/json", body)
        elif path == "/api/round":
            query = parse_qs(urlparse(self.path).query)
            try:
                match_id, round_no = int(query["match"][0]), int(query["round"][0])
            except (KeyError, ValueError):
                self.reply(400, "text/plain", b"need integer match and round")
                return
            try:
                body = json.dumps(round_turns(self.db, match_id, round_no)).encode()
            except sqlite3.Error as error:
                body = json.dumps({"error": f"database: {error}"}).encode()
            self.reply(200, "application/json", body)
        elif path == "/api/state":
            query = parse_qs(urlparse(self.path).query)
            try:
                league_id = int(query["league"][0]) if "league" in query else self.league_id
            except ValueError:
                self.reply(400, "text/plain", b"league must be an integer")
                return
            body = self.cached(f"state:{league_id}", lambda: snapshot(self.db, league_id))
            self.reply(200, "application/json", body)
        elif path == "/api/history":
            self.reply(200, "application/json", self.cached("history", lambda: history(self.db)))
        elif path == "/api/control":
            status = control_status(self.control) if self.control else {"enabled": False}
            self.reply(200, "application/json", json.dumps(status).encode())
        else:
            self.reply(404, "text/plain", b"not found")

    def do_HEAD(self):
        ok = self.path.split("?", 1)[0] in ("/report", "/report/") and self.report and self.report.is_file()
        self.send_response(200 if ok else 404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        """POST /api/control {"action": "pause"|"resume"}: start the control script, return its
        status once it has picked the action up (or after 5 s)."""
        if self.path.split("?", 1)[0] != "/api/control" or not self.control:
            self.reply_json(404, {"error": "not found"})
            return
        if not control_allowed(self.client_address[0]):
            self.reply_json(403, {"error": "pause and resume are allowed from this machine and the LAN only"})
            return
        if self.headers.get(CONTROL_HEADER) != "1":
            self.reply_json(403, {"error": f"missing {CONTROL_HEADER} header"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            action = json.loads(self.rfile.read(min(length, 4096)))["action"] if 0 < length <= 4096 else None
        except (ValueError, KeyError, TypeError):
            action = None
        if action not in ("pause", "resume"):
            self.reply_json(400, {"error": 'body must be {"action": "pause"} or {"action": "resume"}'})
            return
        before = control_status(self.control)
        if before.get("state") in ("pausing", "resuming"):
            self.reply_json(409, {"error": f"already {before['state']}", **before})
            return
        error = control_start(self.control, action)
        if error:
            self.reply_json(409, {"error": error, **before})
            return
        deadline, status = time.monotonic() + 5, before
        while status.get("state") == before.get("state") and time.monotonic() < deadline:
            time.sleep(0.25)
            status = control_status(self.control)
        self.reply_json(202, status)

    def reply_json(self, status: int, body: dict):
        self.reply(status, "application/json", json.dumps(body).encode())

    def reply(self, status: int, kind: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=Path("league.db"))
    parser.add_argument("--league", type=int, help="league id (default: the latest)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8095)
    parser.add_argument("--control", type=Path, metavar="SCRIPT",
                        help="pause/resume script (pause|resume|status); adds the Pause / Resume button")
    parser.add_argument("--report", type=Path, metavar="HTML",
                        default=Path(__file__).resolve().parent.parent / "analysis" / "backgammon" / "index.html",
                        help="working copy of the published report, served at /report/ (default: analysis/backgammon/index.html)")
    args = parser.parse_args()
    if not args.db.exists():
        parser.error(f"{args.db} does not exist")
    Handler.db, Handler.league_id = args.db.resolve(), args.league
    if args.control:
        if not args.control.is_file():
            parser.error(f"{args.control} does not exist")
        Handler.control = args.control.resolve()
    Handler.report = args.report.resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"serving {args.db} on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
