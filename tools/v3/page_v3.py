"""v3 league results for the public report: a JSON of the numbers and the generated tables of
analysis/backgammon/index.html, from a snapshot of the league database and GNUbg's scores.

tools/v3/page_refresh.sh runs the whole refresh every 15 minutes (systemd user timer
v3-page-refresh.timer): snapshot, incremental GNUbg scoring, this script, commit and push. By hand:

    python3 tools/v3/page_v3.py SNAPSHOT.db "SCORES/s*.db" \
        analysis/backgammon/v3-results.json analysis/backgammon/index.html

The page fetches v3-results.json on load and every 5 minutes and renders the same tables from it
(the script at the end of index.html mirrors tables(), pending(), live(), status() and progress());
the HTML written here is the no-JavaScript fallback. Change both together.

Standings come from tools/league_web.py (league_fixtures, league_table), so they match the
dashboard: only finished league-stage matches count. Decisions are turns decided by the model
('model', or 'fallback' when the answer named no option and a random legal play was made) in
valid staged matches of the league's current participants (league_match_view); voided matches are not listed.

Per setup: error rate = 500 x mean 2-ply equity loss over scored decisions (every decision has two
or more legal plays), with a 95% bootstrap interval resampling games; best-play share (loss <
0.001); blunder share (loss > 0.08); invalid share; mean request seconds per decision (retries
excluded); dollars per 1,000 decisions where every decision has a price (provider-reported or list
price; subscriptions at API-list-price equivalent); and where the setup runs (RUNS_ON, written for
the public page: no hostnames).

The HTML file is patched between `<!-- v3:NAME -->` and `<!-- /v3:NAME -->` markers: live (data
time), status (matches to play), scored (decisions scored), progressN (matches finished), leagueN
(tables), N = 1..3, and every piece of prose with a number or a date in it (texts(): updated,
title, toc, byline, summary, headN, notesN, anchor-stats), which is also stored in the JSON under
"text" so the page script shows prose and tables from the same data. Matches not finished are
listed per league: paused (stopped by an error: the runner stored a failure after the match's last
move and has not retried it yet, or the match was aborted), thinking (started, the league runner is
running, waiting on the next decision; with the minutes since the last move at build time),
stopped (started, no runner running, no error) or to play. The prose outside the markers carries
no league numbers. Standard library only.
"""

import glob
import html
import json
import random
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from league_web import league_fixtures, league_table, participants  # noqa: E402

BOOTSTRAP = 2000
BEST, BLUNDER = 0.001, 0.08
RUNNER_ALIVE = 300  # the league runner signs leagues.heartbeat_at every 30 s while it runs (src/league.rs RELOAD)
RETRY = 3600  # a deferred match is retried within this many seconds (src/league.rs MAX_BACKOFF)
STATES = ("thinking", "paused", "stopped", "to play")

RUNS_ON = {
    # League 1
    "Liquid d1-ultra": "Liquid AI decisions API",
    "GNUbg weak": "GNU Backgammon 1.08, Beginner level (0-ply, noise 0.060), x86-64 build (see About the anchor)",
    "Jev 1.14.0": "TypeSafe API",
    "Jev 1.13.0": "TypeSafe API",
    "Fastino GLiDE": "Fastino API (responses name the model glide_v2)",
    "Fastino GLiDE v1.2 (local)": "our GPU, bf16, Fastino's released weights and server",
    "Celeris-1 Decision": "Celeris API (probabilities rounded to 2 decimals)",
    "Cygnet (Gemma 4 12B)": "our GPUs, bf16; DGX Spark from 16 Oct",
    "Decider v1.1 27B": "our GPUs, bf16; DGX Spark from 16 Oct",
    "Clef": "our GPUs, bf16; DGX Spark from 16 Oct",
    "SubQ Snap Preview": "SubQ API",
    "GPT-6 Luna": "OpenAI Decisions API",
    "Mercury Decide": "OpenRouter (Inception)",
    "Winnow-12B": "our GPU, Q8_0 GGUF, author's server",
    "Safest": "program: fewest hitting rolls",
    "Open-Jev 27B v1.1": "our GPU, bf16",
    "Decider Flash v1.2": "our GPU, bf16",
    "Random": "program: random legal play",
    "Decider v1.2 27B": "our GPU, bf16",
    # League 2
    "GPT-6.1 Sol (low)": "ChatGPT subscription",
    "GPT-6.1 Sol (high)": "ChatGPT subscription",
    "Gemini 3.8 Flash (low)": "Google Antigravity subscription",
    "Gemini 3.8 Flash (high)": "Google Antigravity subscription",
    "Claude Sonnet 5.5 (low)": "Claude subscription",
    "Claude Sonnet 5.5 (high)": "Claude subscription",
    "Gemma 4 31B (on)": "our GPU, fp8 (vLLM); DGX Spark 19 Oct 18:36-22:26 UTC and from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    "Gemma 4 31B (off)": "our GPU, fp8 (vLLM); DGX Spark 19 Oct 18:36-22:26 UTC and from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    "Qwen3.8-27B (on)": "our GPU, fp16 (vLLM); first decisions on Cerebras via OpenRouter; DGX Spark from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    "Qwen3.8-27B (off)": "our GPU, fp16 (vLLM); first decisions on Cerebras via OpenRouter; DGX Spark from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    "DeepSeek V4.1 Flash (off)": "Fireworks via OpenRouter (quantization not published) until 20 Oct 21:56 UTC, then our four GPUs (SGLang, published FP4/FP8 weights, 17 Oct revision)",
    "DeepSeek V4.1 Flash (on)": "Fireworks via OpenRouter (quantization not published) until 20 Oct 21:56 UTC, then our four GPUs (SGLang, published FP4/FP8 weights, 17 Oct revision)",
    "Qwen3.8 Flash (off)": "Alibaba via OpenRouter, quantization not published",
    "GLM-5.3 (on)": "Fireworks via OpenRouter, quantization not published",
    "LFM2.5-24B-A2B (on)": "our GPU, bf16 (vLLM); first decisions on Liquid AI's API (voided); DGX Spark from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    "LFM2.5-24B-A2B (off)": "our GPU, bf16 (vLLM); DGX Spark from 20 Oct 21:10 UTC (back on our GPU 21 Oct 01:25-05:00)",
    # League 3
    "GPT-6 Astra (off)": "ChatGPT subscription",
    "GPT-6 Astra (on)": "ChatGPT subscription",
    "Claude Opus 5.5 (off)": "Claude subscription",
    "Claude Opus 5.5 (on)": "Claude subscription",
    "Claude Fable 5.1 (off)": "Claude subscription",
    "Claude Fable 5.1 (on)": "Claude subscription",
    "Gemini 4 Argon (off)": "Google Antigravity subscription",
    "Gemini 4 Argon (on)": "Google Antigravity subscription",
    "Grok 4.7 (off)": "xAI subscription (SuperGrok)",
    "Grok 4.7 (on)": "xAI subscription (SuperGrok)",
}

READOUT = {"decision": "option probabilities", "logprobs": "letter probabilities", "choice_only": "one letter"}

# Perplexity's Deciders run on our GPUs; their cost column is Perplexity's list price for the tokens, not money paid.
SELF_HOSTED_PRICED = {"Decider v1.1 27B", "Decider v1.2 27B", "Decider Flash v1.2"}
LIST_PRICE_ESTIMATE = "list-price estimate; runs on our GPUs"
ANCHOR = "GNUbg weak"
# v1 error rates of the v1 decision models (leagues #8, #11 and #12; the "By model" table of the report).
V1_ERROR = {"Jev 1.13.0": 35.7, "Clef": 35.8, "Decider v1.1 27B": 32.7, "Cygnet (Gemma 4 12B)": 43.2,
            "GPT-6 Luna": 39.4, "Open-Jev 27B v1.1": 59.6}
LEAGUE_TITLE = {1: "League 1: decision models", 2: "League 2: workhorse chat models, closed and open",
                3: "League 3: frontier chat models on subscriptions"}


def utc(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def scores(paths: list[str]) -> tuple[dict[int, tuple[int, float]], int]:
    """turn_id -> (plays, loss) from every shard database, and the number of skipped turns."""
    out, skipped = {}, 0
    for p in paths:
        db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        out.update({t: (n, loss) for t, n, loss in db.execute("SELECT turn_id, plays, loss FROM decisions")})
        skipped += db.execute("SELECT COUNT(*) FROM skipped").fetchone()[0]
        db.close()
    return out, skipped


def interval(games: list[tuple[float, int]], rng: random.Random) -> tuple[float, float]:
    """95% bootstrap interval of 500 x total loss / total decisions, resampling games."""
    stats = []
    for _ in range(BOOTSTRAP):
        draw = rng.choices(games, k=len(games))
        n = sum(c for _, c in draw)
        stats.append(500 * sum(s for s, _ in draw) / n if n else 0.0)
    stats.sort()
    return stats[int(0.025 * BOOTSTRAP)], stats[int(0.975 * BOOTSTRAP) - 1]


def league(conn: sqlite3.Connection, lid: int, scored: dict, rng: random.Random, now: datetime,
           taken: datetime) -> dict:
    """One league's standings and setups; `now` is the build time, `taken` when the snapshot was written."""
    row = conn.execute("SELECT * FROM leagues WHERE id = ?", (lid,)).fetchone()
    roster = [p["settings"] for p in participants(conn, lid)]
    names = [m["name"] for m in roster]
    fixtures, games_won = league_fixtures(conn, row)
    fixtures = [f for f in fixtures if f["stage"] == "league"]
    table = league_table(names, fixtures, games_won)
    left = {n: 0 for n in names}
    thinking = {n: 0 for n in names}
    open_ = [f for f in fixtures if f["status"] != "finished"]
    last = dict(conn.execute(
        f"""SELECT g.match_id, MAX(t.created_at) FROM turns t JOIN games g ON g.id = t.game_id
            WHERE g.match_id IN ({','.join('?' * len(open_)) or 'NULL'}) GROUP BY 1""",
        [f["match_id"] for f in open_],
    ).fetchall())
    beat = row["heartbeat_at"]
    runner = bool(beat) and (taken - utc(beat)).total_seconds() <= RUNNER_ALIVE
    pending = []
    for f in open_:
        left[f["model1"]] += 1
        left[f["model2"]] += 1
        moved = last.get(f["match_id"])
        failed = f["deferred_at"]
        # The runner keeps a failed match's error after it resumes; the failure stops the match only while it is
        # newer than the match's last move and its retry is still to come (a runner start retries every match).
        errored = f["status"] == "aborted" or bool(
            failed and (moved is None or utc(failed) > utc(moved))
            and (not runner or (now - utc(failed)).total_seconds() < RETRY))
        if errored:
            state = "paused"
        elif moved is None:
            state = "to play"
        elif runner:
            state = "thinking"
        else:
            state = "stopped"
        if state == "thinking":
            thinking[f["model1"]] += 1
            thinking[f["model2"]] += 1
        pending.append(dict(
            model1=f["model1"], model2=f["model2"], state=state,
            rounds_played=f["rounds_played"] or 0, rounds_planned=f["rounds_planned"],
            score1=f["score1"] or 0, score2=f["score2"] or 0,
            last_move=utc(moved).strftime("%Y-%m-%dT%H:%MZ") if moved else None,
            minutes_since_move=int((now - utc(moved)).total_seconds() // 60) if moved else None,
        ))
    pending.sort(key=lambda p: STATES.index(p["state"]))  # stable: matchday order within

    per: dict[str, dict] = {}
    for r in conn.execute(
        """SELECT t.id, g.id AS game_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name,
                  t.decided_by, t.legal_count, t.probability_source, COALESCE(t.request_ms, t.latency_ms) AS ms,
                  t.cost_usd
           FROM turns t JOIN games g ON g.id = t.game_id JOIN league_match_view lm ON lm.match_id = g.match_id
           WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')
           ORDER BY lm.label, g.id, t.turn_no""",
        (lid,),
    ):
        m = per.setdefault(r["name"], dict(decisions=0, invalid=0, ms=0, priced=0, cost=0.0, readout={}, games={}))
        m["decisions"] += 1
        m["invalid"] += r["decided_by"] == "fallback"
        m["ms"] += r["ms"] or 0
        if r["cost_usd"] is not None:
            m["priced"] += 1
            m["cost"] += r["cost_usd"]
        if r["probability_source"]:
            m["readout"][r["probability_source"]] = m["readout"].get(r["probability_source"], 0) + 1
        s = scored.get(r["id"])
        if s and s[0] >= 2:
            g = m["games"].setdefault(r["game_id"], [0.0, 0, 0, 0])  # loss sum, decisions, best, blunders
            g[0] += s[1]
            g[1] += 1
            g[2] += s[1] < BEST
            g[3] += s[1] > BLUNDER

    models = []
    for place, t in enumerate(table, 1):
        name = t["name"]
        m = per.get(name)
        out = dict(place=place, name=name, played=t["played"], won=t["won"], drawn=t["drawn"], lost=t["lost"],
                   points=t["points"], games_won=t["gw"], games_lost=t["gl"], to_play=left[name],
                   thinking=thinking[name], runs_on=RUNS_ON.get(name), decisions=0)
        if m:
            games = list(m["games"].values())
            n = sum(g[1] for g in games)
            out.update(
                decisions=m["decisions"],
                scored=n,
                coverage=round(n / m["decisions"], 4),
                invalid=m["invalid"],
                invalid_share=round(m["invalid"] / m["decisions"], 4),
                s_per_decision=round(m["ms"] / m["decisions"] / 1000, 2),
                usd_per_1000=round(1000 * m["cost"] / m["decisions"], 3) if m["priced"] == m["decisions"] else None,
                cost_note=LIST_PRICE_ESTIMATE if name in SELF_HOSTED_PRICED else None,
                readout=READOUT.get(max(m["readout"], key=m["readout"].get)) if m["readout"] else None,
            )
            if n:
                lo, hi = interval([(g[0], g[1]) for g in games], rng)
                out.update(
                    error_rate=round(500 * sum(g[0] for g in games) / n, 1),
                    error_rate_lo=round(lo, 1),
                    error_rate_hi=round(hi, 1),
                    best_share=round(sum(g[2] for g in games) / n, 4),
                    blunder_share=round(sum(g[3] for g in games) / n, 4),
                )
        models.append(out)
    finished = sum(f["status"] == "finished" for f in fixtures)
    games = conn.execute(
        """SELECT COUNT(*) FROM games g JOIN league_match_view lm ON lm.match_id = g.match_id AND lm.league_id = ?
           WHERE g.winner_player IS NOT NULL""",
        (lid,),
    ).fetchone()[0]
    return dict(id=lid, status="finished" if row["status"] == "finished" else "running", matches=len(fixtures),
                finished=finished, games=games, runner=runner, pending=pending, models=models)


# --- HTML ---------------------------------------------------------------------------------

def num(x, spec=",") -> str:
    return "–" if x is None else format(x, spec)


def pct(x, digits=0) -> str:
    return "–" if x is None else f"{100 * x:.{digits}f}%"


def cell(value: str, cls: str = "") -> str:
    return f'<td class="{cls}">{value}</td>' if cls else f"<td>{value}</td>"


def tables(lg: dict) -> str:
    rows, setup = [], []
    for m in lg["models"]:
        name = html.escape(m["name"])
        er = "–"
        if m.get("error_rate") is not None:
            er = f'<strong>{m["error_rate"]:.1f}</strong> <span class="muted">{m["error_rate_lo"]:.1f}–{m["error_rate_hi"]:.1f}</span>'
        left = m["to_play"]
        to_play = str(left) + (f' <span class="live">({m["thinking"]} thinking)</span>' if m["thinking"] else "")
        rows.append("<tr>" + "".join([
            cell(str(m["place"])), cell(name, "l"), cell(str(m["played"])), cell(str(m["won"])),
            cell(str(m["drawn"]), "zero" if not m["drawn"] else ""), cell(str(m["lost"])),
            cell(f"<strong>{m['points']}</strong>"), cell(f"{m['games_won']}-{m['games_lost']}"),
            cell(to_play, "zero" if not left else ""), cell(er), cell(pct(m.get("best_share"))),
            cell(pct(m.get("blunder_share"))),
        ]) + "</tr>")
        cost = m.get("usd_per_1000")
        setup.append("<tr>" + "".join([
            cell(name, "l"), cell(num(m["decisions"])),
            cell(html.escape(m.get("readout") or "–"), "l"),
            cell(pct(m.get("invalid_share"), 1), "zero" if not m.get("invalid_share") else ""),
            cell(num(m.get("s_per_decision"), ".2f") + (" s" if m.get("s_per_decision") is not None else "")),
            cell("–" if cost is None else f"${cost:.2f}"
                 + (f'<br><span class="muted">{m["cost_note"]}</span>' if m.get("cost_note") else "")),
            cell(html.escape(m["runs_on"] or "–"), "l wrap"),
        ]) + "</tr>")
    indent = "\n            "
    return pending(lg) + f"""<div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th class="l">Setup</th><th>P</th><th>W</th><th>D</th><th>L</th><th>Pts</th><th>Games</th><th>To play</th><th>Error rate (95%)</th><th>Engine's best play</th><th>Blunders</th></tr></thead>
          <tbody>
            {indent.join(rows)}
          </tbody>
        </table>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th class="l">Setup</th><th>Decisions</th><th class="l">Answer read as</th><th>Invalid</th><th>Time per<br>decision</th><th>$ per 1,000<br>decisions</th><th class="l">Runs on</th></tr></thead>
          <tbody>
            {indent.join(setup)}
          </tbody>
        </table>
      </div>"""


def pending(lg: dict) -> str:
    """Matches not finished: thinking, paused after an error, stopped or to play (see the module docstring)."""
    if not lg["pending"]:
        return ""
    rows = []
    for p in lg["pending"]:
        state = (f'<span class="live">thinking</span>, last move {p["minutes_since_move"]} min ago'
                 if p["state"] == "thinking" else STATE_TEXT[p["state"]])
        started = p["last_move"] is not None
        rows.append("<tr>" + "".join([
            cell(f"{html.escape(p['model1'])} v {html.escape(p['model2'])}", "l"), cell(state, "l"),
            cell(f"{p['rounds_played']} of {p['rounds_planned']}" if started else "–"),
            cell(f"{p['score1']}-{p['score2']}" if started else "–"),
            cell(utc(p["last_move"]).strftime("%-d %b %H:%M") if p["last_move"] else "–"),
        ]) + "</tr>")
    indent = "\n            "
    return f"""<div class="table-wrap">
        <table>
          <thead><tr><th class="l">Match not finished</th><th class="l">State</th><th>Rounds played</th><th>Score</th><th>Last move (UTC)</th></tr></thead>
          <tbody>
            {indent.join(rows)}
          </tbody>
        </table>
      </div>
      """


def live(result: dict) -> str:
    stamp = utc(result["data_as_of"]).strftime("%-d %B %Y, %H:%M UTC")
    if all(lg["status"] == "finished" for lg in result["leagues"]):
        return f"Final: data as of {stamp}"
    return f"Live: data as of {stamp} · updates every 15 minutes"


STATE_TEXT = {"thinking": "thinking", "paused": "paused after an error", "stopped": "stopped", "to play": "to play"}


def groups(lg: dict) -> list[str]:
    """The started matches not finished, by state: 'N thinking, last move M min ago', 'N paused after an error'..."""
    out = []
    for s in STATES[:-1]:
        ps = [p for p in lg["pending"] if p["state"] == s]
        if ps:
            out.append(f"{len(ps)} {STATE_TEXT[s]}" + (f", last move {min(p['minutes_since_move'] for p in ps)} min ago"
                                                        if s == "thinking" else ""))
    return out


def status(result: dict) -> str:
    parts = []
    for lg in result["leagues"]:
        if lg["status"] == "finished":
            parts.append(f"League {lg['id']} has finished")
            continue
        started = groups(lg)
        parts.append(f"League {lg['id']} has {len(lg['pending'])} of {lg['matches']} matches to play"
                     + (f" ({'; '.join(started)})" if started else ""))
    return "; ".join(parts) + "."


def progress(lg: dict) -> str:
    return f"{lg['finished']} of {lg['matches']} matches finished, {lg['games']:,} games"


# --- Generated text -------------------------------------------------------------------------
# Every number in the v3 prose comes from the result written to v3-results.json: main() stores the HTML of
# each text block in result["text"], patches it between the markers, and the page script sets it from the
# JSON with the tables, so the prose and the tables always show the same data.

def anchor_stats(conn: sqlite3.Connection) -> dict:
    """Gammons and match wins of the anchor in finished league-stage matches, per league."""
    out = {}
    for lid in (1, 2, 3):
        kinds = {k: [0, 0] for k in ("anchor", "models", "programs")}  # finished games, gammon or backgammon
        wins = gammon_wins = certain = 0
        programs = {p["name"] for p in participants(conn, lid) if p["name"] in ("Random", "Safest")}
        for lm in conn.execute(
            """SELECT lm.model1, lm.model2, m.id, m.winner, m.rounds_planned FROM league_match_view lm
               JOIN matches m ON m.id = lm.match_id
               WHERE lm.league_id = ? AND lm.stage = 'league' AND m.status = 'finished'""", (lid,)):
            pair = {lm["model1"], lm["model2"]}
            kind = "anchor" if ANCHOR in pair else "programs" if pair & programs else "models"
            games = conn.execute("SELECT winner_player, result FROM games WHERE match_id = ? AND winner_player IS NOT NULL",
                                 (lm["id"],)).fetchall()
            kinds[kind][0] += len(games)
            kinds[kind][1] += sum(g["result"] in ("gammon", "backgammon") for g in games)
            if kind != "anchor" or lm["winner"] is None:
                continue
            side = 1 if lm["model1"] == ANCHOR else 2
            if lm["winner"] != side:
                continue
            wins += 1
            gammon_wins += any(g["winner_player"] == side and g["result"] in ("gammon", "backgammon") for g in games)
            won = sum(g["winner_player"] == side for g in games)
            certain += won > len(games) - won + 2 * lm["rounds_planned"] - len(games)
        out[lid] = dict(gammon_share={k: round(v[1] / v[0], 3) if v[0] else None for k, v in kinds.items()},
                        anchor_wins=wins, anchor_wins_with_gammon=gammon_wins, anchor_wins_certain_at_1_point=certain)
    return out


def e(m: dict) -> str:
    return f"{m['error_rate']:.1f}"


def overlap(a: dict, b: dict) -> bool:
    return a["error_rate_lo"] <= b["error_rate_hi"] and b["error_rate_lo"] <= a["error_rate_hi"]


def compare(a: dict, b: dict) -> str:
    """How b's error rate stands against a's: a clear difference only when the intervals do not overlap."""
    if overlap(a, b):
        return "no clear difference in league play"
    return "lower, and the intervals do not overlap" if b["error_rate"] < a["error_rate"] else \
        "higher, and the intervals do not overlap"


def names(items: list[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def span(values: list[float], unit: str = "", money: bool = False) -> str:
    fmt = (lambda v: f"${v:,.0f}" if v >= 10 else f"${v:.2f}") if money else (lambda v: f"{v:.1f}{unit}")
    lo, hi = min(values), max(values)
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)} to {fmt(hi)}"


def pairs(models: list[dict]) -> list[tuple[str, dict, dict]]:
    """(base name, lower setting, higher setting) for every model played at two reasoning settings."""
    by = {}
    for m in models:
        found = re.fullmatch(r"(.*) \((off|on|low|high)\)", m["name"])
        if found and m.get("error_rate") is not None:
            by.setdefault(found.group(1), {})[found.group(2) in ("on", "high")] = m
    return [(base, s[False], s[True]) for base, s in by.items() if len(s) == 2]


def setting(m: dict) -> str:
    return re.fullmatch(r".* \((\w+)\)", m["name"]).group(1)


def reasoning(lg: dict) -> str:
    lines = []
    for base, lo, hi in pairs(lg["models"]):
        lines.append(f"{html.escape(base)} {e(lo)} ({setting(lo)}) and {e(hi)} ({setting(hi)}): {compare(lo, hi)}"
                     f"; {lo['s_per_decision']:.1f} s and {hi['s_per_decision']:.1f} s per decision")
    return ("<li><strong>Reasoning, lower and higher setting</strong> (error rate; a difference counts only when "
            "the 95% intervals do not overlap): " + "; ".join(lines) + ". League games are not the same positions, "
            "so these are not paired comparisons.</li>")


def still(lg: dict) -> str:
    if not lg["pending"]:
        return ""
    count = sum(p["state"] == "to play" for p in lg["pending"])
    parts = groups(lg) + ([f"{count} not started"] if count else [])
    return (f"<li><strong>Still to play</strong>: {len(lg['pending'])} of {lg['matches']} matches "
            f"({', '.join(parts)}; listed above the table).</li>")


def leader(lg: dict) -> str:
    top = lg["models"][0]
    word = "won" if lg["status"] == "finished" else "leads"
    return f"{html.escape(top['name'])} {word} with {top['won']} wins in {top['played']} matches"


def notes1(lg: dict) -> str:
    ms = lg["models"]
    by = {m["name"]: m for m in ms}
    programs = [m for m in ms if (m["runs_on"] or "").startswith("program:")]
    dm = sorted((m for m in ms if m["name"] != ANCHOR and m not in programs and m.get("error_rate") is not None),
                key=lambda m: m["error_rate"])
    out = []
    top = ", ".join(f"{m['place']}. {html.escape(m['name'])} ({m['points']} points)" for m in ms[:5])
    last = ms[-1]
    out.append(f"<li><strong>{'Final ranking' if lg['status'] == 'finished' else 'Standing'}</strong>: {top}; "
               f"{html.escape(last['name'])} last, with {last['won']} matches won.</li>")
    best = dm[0]
    close = [m for m in dm[1:] if m["error_rate"] <= best["error_rate_hi"]]
    rest = [m for m in dm[1:] if m not in close]
    text = f"<li><strong>{html.escape(best['name'])} has the lowest error rate of the decision models</strong>, {e(best)}."
    if close:
        text += f" {names(f'{html.escape(m['name'])} ({e(m)})' for m in close)} {'is' if len(close) == 1 else 'are'} within its interval;"
    if rest:
        text += f" every other decision model is at {e(rest[0])} or higher."
    out.append(text + "</li>")
    a = by.get(ANCHOR)
    if a and a.get("error_rate") is not None:
        worse = [m for m in dm if m["error_rate"] > a["error_rate"]]
        if len(worse) == len(dm):
            out.append(f"<li><strong>The weak GNU Backgammon anchor plays better than every decision model</strong> by "
                       f"error rate ({e(a)}); its match wins come with many gammons (see "
                       f'<a href="#v3-anchor">About the anchor</a>).</li>')
        else:
            out.append(f"<li><strong>The weak GNU Backgammon anchor</strong> ({e(a)}) has a lower error rate than "
                       f"{len(worse)} of the {len(dm)} decision models.</li>")
    safest, rnd = by.get("Safest"), by.get("Random")
    if safest and safest.get("error_rate") is not None:
        worse = [m for m in dm if m["error_rate"] > safest["error_rate"]]
        near = [m for m in dm if safest["error_rate_lo"] <= m["error_rate"] <= safest["error_rate"]]
        text = (f"<li><strong>{len(worse)} decision model{'s play' if len(worse) != 1 else ' plays'} worse than the "
                f"Safest program</strong> by error rate"
                + (f": {names(f'{html.escape(m['name'])} ({e(m)})' for m in worse)}, against {e(safest)}." if worse
                   else f" ({e(safest)})."))
        if near:
            text += f" {names(f'{html.escape(m['name'])} ({e(m)})' for m in near)} within Safest's interval."
        if rnd and rnd.get("error_rate") is not None:
            text += f" Random scores {e(rnd)}."
        out.append(text + "</li>")
    v1 = [(by[n], v) for n, v in V1_ERROR.items() if by.get(n, {}).get("error_rate") is not None]
    if v1:
        higher = sum(m["error_rate"] > v for m, v in v1)
        out.append(f"<li><strong>The {len(v1)} v1 decision models against their v1 error rates</strong>: {higher} higher, "
                   f"{len(v1) - higher} lower or equal: "
                   + ", ".join(f"{html.escape(m['name'])} {e(m)} (v1: {v:.1f})" for m, v in v1)
                   + ". The games, opponents and option order differ, so this is not a paired comparison.</li>")
    vs = [(by[x], by[y]) for x, y in (("Jev 1.13.0", "Jev 1.14.0"), ("Decider v1.1 27B", "Decider v1.2 27B"))
          if by.get(x, {}).get("error_rate") is not None and by.get(y, {}).get("error_rate") is not None]
    if vs:
        out.append("<li><strong>New versions</strong>: " + "; ".join(
            f"{html.escape(y['name'])} {e(y)} ({y['points']} points) against {html.escape(x['name'])} {e(x)} "
            f"({x['points']} points): {compare(x, y)}" for x, y in vs) + ".</li>")
    hosted = [m for m in dm if not (m["runs_on"] or "").startswith("our GPU")]
    priced = [m["usd_per_1000"] for m in hosted if m.get("usd_per_1000") is not None]
    if hosted:
        out.append(f"<li><strong>The hosted decision services</strong> ({len(hosted)}) take "
                   f"{span([m['s_per_decision'] for m in hosted], ' s')} per decision"
                   + (f"; the {len(priced)} with a price cost {span(priced, money=True)} per 1,000 decisions" if priced else "")
                   + ".</li>")
    return "\n        ".join(out)


def notes2(lg: dict) -> str:
    ms = [m for m in lg["models"] if m.get("error_rate") is not None]
    rated = sorted(ms, key=lambda m: m["error_rate"])
    closed = [m for m in rated if "subscription" in (m["runs_on"] or "")]
    open_ = [m for m in rated if m not in closed and m["name"] != ANCHOR]
    out = [f"<li><strong>{leader(lg)}</strong>. The lowest error rate is {html.escape(rated[0]['name'])}'s, "
           f"{e(rated[0])}.</li>", reasoning(lg)]
    if closed and open_:
        gap = open_[0]["error_rate"] - closed[0]["error_rate"]
        out.append(f"<li><strong>The best open setup is {gap:.1f} "
                   f"points behind the best closed one</strong>: {html.escape(open_[0]['name'])} at {e(open_[0])}, "
                   f"against {html.escape(closed[0]['name'])} at {e(closed[0])}.</li>")
    a = next((m for m in ms if m["name"] == ANCHOR), None)
    if a:
        below_closed = [m for m in closed if m["error_rate"] < a["error_rate"]]
        below_open = [m for m in open_ if m["error_rate"] < a["error_rate"]]
        out.append(f"<li><strong>The weak GNU Backgammon anchor</strong> ({e(a)}): {len(below_closed)} of "
                   f"{len(closed)} closed setups have a lower error rate; of the {len(open_)} open setups, "
                   + (names(f"{html.escape(m['name'])} ({e(m)})" for m in below_open) + " do" if below_open else "none")
                   + ".</li>")
    out.append(invalid(lg))
    out.append(still(lg))
    return "\n        ".join(x for x in out if x)


def invalid(lg: dict) -> str:
    bad = [m for m in lg["models"] if m.get("invalid")]
    if not bad:
        return "<li><strong>No invalid answers.</strong></li>"
    return ("<li><strong>Invalid answers</strong>: " + ", ".join(
        f"{m['invalid']} from {html.escape(m['name'])} ({pct(m['invalid_share'], 1)} of its decisions)" for m in bad)
        + "; none from any other setup.</li>")


def notes3(lg: dict) -> str:
    ms = [m for m in lg["models"] if m.get("error_rate") is not None]
    rated = sorted(ms, key=lambda m: m["error_rate"])
    best = rated[0]
    close = [m for m in rated[1:] if overlap(best, m) and m["name"] != ANCHOR][:3]
    out = [f"<li><strong>{leader(lg)}</strong>. Lowest error rates: "
           + ", ".join(f"{html.escape(m['name'])} {e(m)}" for m in [best] + close)
           + (", with overlapping intervals" if close else "") + ".</li>", reasoning(lg)]
    a = next((m for m in ms if m["name"] == ANCHOR), None)
    if a:
        better = [m for m in ms if m["name"] != ANCHOR and m["error_rate"] < a["error_rate"]]
        out.append(f"<li><strong>{len(better)} of the {len(ms) - 1} setups have a lower error rate than the weak "
                   f"GNU Backgammon anchor</strong> ({e(a)}).</li>")
    out.append(invalid(lg))
    for word in ("off", "on"):
        side = [m for m in ms if m["name"].endswith(f"({word})")]
        if side:
            slow = max(side, key=lambda m: m["s_per_decision"])
            out.append(f"<li><strong>Time per decision, reasoning {word}</strong>: "
                       f"{span([m['s_per_decision'] for m in side], ' s')}; slowest {html.escape(slow['name'])}.</li>")
    priced = [m["usd_per_1000"] for m in ms if m.get("usd_per_1000") is not None]
    if priced:
        out.append(f"<li><strong>Cost</strong> at API list prices: {span(priced, money=True)} per 1,000 decisions.</li>")
    out.append(still(lg))
    return "\n        ".join(x for x in out if x)


def phase(lg: dict) -> str:
    """'' when finished; else 'in progress, last move N min ago' (a match is thinking), 'in progress' (the runner
    runs), 'paused after an error' (a match stopped by an error, no runner) or 'stopped'."""
    if lg["status"] == "finished":
        return ""
    thinking = [p["minutes_since_move"] for p in lg["pending"] if p["state"] == "thinking"]
    if thinking:
        return f"in progress, last move {min(thinking)} min ago"
    if lg["runner"]:
        return "in progress"
    return "paused after an error" if any(p["state"] == "paused" for p in lg["pending"]) else "stopped"


def short(lg: dict) -> str:
    return phase(lg).split(",")[0]


def byline(result: dict) -> str:
    done = [str(lg["id"]) for lg in result["leagues"] if lg["status"] == "finished"]
    parts = [f"League{'s' if len(done) > 1 else ''} {names(done)} finished"] if done else []
    parts += [f"League {lg['id']}: {lg['finished']} of {lg['matches']} matches, {phase(lg)}"
              for lg in result["leagues"] if lg["status"] != "finished"]
    return "; ".join(parts)


def summary(result: dict) -> str:
    l1, l2, l3 = result["leagues"]
    best = lambda lg: min((m for m in lg["models"] if m.get("error_rate") is not None), key=lambda m: m["error_rate"])
    dm = [m for m in l1["models"] if m["name"] != ANCHOR and not (m["runs_on"] or "").startswith("program:")
          and m.get("error_rate") is not None]
    a1 = next((m for m in l1["models"] if m["name"] == ANCHOR and m.get("error_rate") is not None), None)
    word = lambda lg: "first" if lg["status"] == "finished" else "leads"
    state = lambda lg: "finished" if lg["status"] == "finished" else short(lg)
    b2 = best(l2)
    return (f"decision models ({state(l1)}: {html.escape(l1['models'][0]['name'])} {word(l1)}"
            + (", and the weak GNU Backgammon anchor plays better than every decision model"
               if a1 and all(m["error_rate"] > a1["error_rate"] for m in dm) else "")
            + f"), workhorse chat models closed and open ({state(l2)}: {html.escape(l2['models'][0]['name'])} "
            f"{word(l2)}; lowest error rate {html.escape(b2['name'])}, {e(b2)}), and frontier chat models on "
            f"subscriptions, each with reasoning off and on ({state(l3)}: {html.escape(l3['models'][0]['name'])} "
            f"{word(l3)})")


def anchor_notes(stats: dict) -> str:
    share = lambda x: "–" if x is None else f"{100 * x:.0f}%"
    s = {lid: v["gammon_share"] for lid, v in stats.items()}
    wins = sum(v["anchor_wins"] for v in stats.values())
    gammon = sum(v["anchor_wins_with_gammon"] for v in stats.values())
    certain = {lid: v["anchor_wins_certain_at_1_point"] for lid, v in stats.items()}
    return (f"<li><strong>Gammons in the leagues.</strong> Games with the anchor end in a gammon or backgammon in "
            + ", ".join(f"{share(s[l]['anchor'])} (League {l})" for l in s)
            + "; games between two models in " + ", ".join(f"{share(s[l]['models'])} (League {l})" for l in s)
            + f"; games with Random or Safest in {share(s[1]['programs'])}.</li>\n        "
            f"<li><strong>Match wins.</strong> {gammon} of the {wins} matches the anchor won included a gammon or "
            f"backgammon by it. Scored at 1 point per game, {sum(certain.values())} of those wins are certain ("
            + ", ".join(f"{n} in League {l}" for l, n in certain.items())
            + "); the rest would need games that were never played.</li>")


def texts(result: dict, stats: dict) -> dict:
    l1, l2, l3 = result["leagues"]
    phases = [short(lg) for lg in result["leagues"] if lg["status"] != "finished"]
    suffix = "in progress" if "in progress" in phases else phases[0] if phases else ""
    out = {"updated": utc(result["data_as_of"]).strftime("%-d %B %Y"),
           "title": "v3 leagues" + (f" ({suffix})" if suffix else ""), "byline": byline(result),
           "summary": summary(result), "anchor-stats": anchor_notes(stats),
           "notes1": notes1(l1), "notes2": notes2(l2), "notes3": notes3(l3)}
    out["toc"] = out["title"]
    for lg in result["leagues"]:
        out[f"head{lg['id']}"] = LEAGUE_TITLE[lg["id"]] + (f" ({phase(lg)})" if phase(lg) else "")
    return out


def patch(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- v3:{name} -->).*?(<!-- /v3:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker v3:{name} not found")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main():
    db_path, score_glob, json_out, html_path = sys.argv[1:5]
    taken = datetime.fromtimestamp(Path(db_path).stat().st_mtime, timezone.utc)  # when the snapshot was written
    now = datetime.now(timezone.utc)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    scored, skipped = scores(sorted(glob.glob(score_glob)))
    as_of = utc(conn.execute("SELECT MAX(created_at) FROM turns").fetchone()[0])
    rng = random.Random(1)
    result = dict(
        data_as_of=as_of.strftime("%Y-%m-%dT%H:%MZ"),
        gnubg=dict(scored=len(scored), skipped=skipped, method="GNU Backgammon 1.08: 0-ply on every play, 2-ply on the five best and the chosen one"),
        leagues=[league(conn, lid, scored, rng, now, taken) for lid in (1, 2, 3)],
    )
    result["scored"] = sum(m.get("scored", 0) for lg in result["leagues"] for m in lg["models"])
    result["anchor"] = anchor_stats(conn)
    result["text"] = texts(result, result["anchor"])
    Path(json_out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

    text = Path(html_path).read_text()
    text = patch(text, "live", live(result))
    text = patch(text, "status", status(result))
    text = patch(text, "scored", f"{result['scored']:,}")
    for lg in result["leagues"]:
        text = patch(text, f"league{lg['id']}", "\n      " + tables(lg) + "\n      ")
        text = patch(text, f"progress{lg['id']}", progress(lg))
    for name, body in result["text"].items():
        text = patch(text, name, body)
    Path(html_path).write_text(text)


if __name__ == "__main__":
    main()
