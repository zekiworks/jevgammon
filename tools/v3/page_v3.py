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
matches linked from league_matches; voided and removed matches are not linked.

Per setup: error rate = 500 x mean 2-ply equity loss over scored decisions (every decision has two
or more legal plays), with a 95% bootstrap interval resampling games; best-play share (loss <
0.001); blunder share (loss > 0.08); invalid share; mean request seconds per decision (retries
excluded); dollars per 1,000 decisions where every decision has a price (provider-reported or list
price; subscriptions at API-list-price equivalent); and where the setup runs (RUNS_ON, written for
the public page: no hostnames).

The HTML file is patched between `<!-- v3:NAME -->` and `<!-- /v3:NAME -->` markers: live (data
time), status (matches to play), scored (decisions scored), progressN (matches finished), leagueN
(tables), N = 1..3. Matches not finished are listed per league: playing (a move within the last
hour), paused (started, no recent move) or to play. The prose around the markers is written by
hand and carries the time it was last checked. Standard library only.
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
from league_web import league_fixtures, league_table  # noqa: E402

BOOTSTRAP = 2000
BEST, BLUNDER = 0.001, 0.08
PLAYING = 3600  # a started match counts as playing when its last move is at most this many seconds old

RUNS_ON = {
    # League 1
    "Liquid d1-ultra": "Liquid AI decisions API",
    "GNUbg weak": "GNU Backgammon 1.08, Beginner level (0-ply, noise 0.060), x86-64 build (see About the anchor)",
    "Jev 1.14.0": "TypeSafe API",
    "Jev 1.13.0": "TypeSafe API",
    "Fastino GLiDE": "Fastino API",
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


def league(conn: sqlite3.Connection, lid: int, scored: dict, rng: random.Random, as_of: datetime) -> dict:
    row = conn.execute("SELECT * FROM leagues WHERE id = ?", (lid,)).fetchone()
    roster = json.loads(row["models"])
    names = [m["name"] for m in roster]
    fixtures, games_won = league_fixtures(conn, lid)
    fixtures = [f for f in fixtures if f["stage"] == "league"]
    table = league_table(names, fixtures, games_won)
    left = {n: 0 for n in names}
    playing = {n: 0 for n in names}
    open_ = [f for f in fixtures if f["status"] != "finished"]
    last = dict(conn.execute(
        f"""SELECT g.match_id, MAX(t.created_at) FROM turns t JOIN games g ON g.id = t.game_id
            WHERE g.match_id IN ({','.join('?' * len(open_)) or 'NULL'}) GROUP BY 1""",
        [f["match_id"] for f in open_],
    ).fetchall())
    pending = []
    for f in open_:
        left[f["model1"]] += 1
        left[f["model2"]] += 1
        moved = last.get(f["match_id"])
        if moved is None:
            state = "to play"
        elif (as_of - utc(moved)).total_seconds() <= PLAYING:
            state = "playing"
        else:
            state = "paused"
        if state == "playing":
            playing[f["model1"]] += 1
            playing[f["model2"]] += 1
        pending.append(dict(
            model1=f["model1"], model2=f["model2"], state=state,
            rounds_played=f["rounds_played"] or 0, rounds_planned=f["rounds_planned"],
            score1=f["score1"] or 0, score2=f["score2"] or 0,
            last_move=utc(moved).strftime("%Y-%m-%dT%H:%MZ") if moved else None,
        ))
    pending.sort(key=lambda p: ("playing", "paused", "to play").index(p["state"]))  # stable: matchday order within

    per: dict[str, dict] = {}
    for r in conn.execute(
        """SELECT t.id, g.id AS game_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name,
                  t.decided_by, t.legal_count, t.probability_source, COALESCE(t.request_ms, t.latency_ms) AS ms,
                  t.cost_usd
           FROM turns t JOIN games g ON g.id = t.game_id JOIN league_matches lm ON lm.match_id = g.match_id
           WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')""",
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
                   playing=playing[name], runs_on=RUNS_ON.get(name), decisions=0)
        if m:
            games = list(m["games"].values())
            n = sum(g[1] for g in games)
            out.update(
                decisions=m["decisions"],
                scored=n,
                coverage=round(n / m["decisions"], 4),
                invalid_share=round(m["invalid"] / m["decisions"], 4),
                s_per_decision=round(m["ms"] / m["decisions"] / 1000, 2),
                usd_per_1000=round(1000 * m["cost"] / m["decisions"], 3) if m["priced"] == m["decisions"] else None,
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
        """SELECT COUNT(*) FROM games g JOIN league_matches lm ON lm.match_id = g.match_id AND lm.league_id = ?
           WHERE g.winner_player IS NOT NULL""",
        (lid,),
    ).fetchone()[0]
    return dict(id=lid, status="finished" if row["status"] == "finished" else "running", matches=len(fixtures),
                finished=finished, games=games, pending=pending, models=models)


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
        to_play = str(left) + (f' <span class="live">({m["playing"]} playing)</span>' if m["playing"] else "")
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
            cell("–" if cost is None else f"${cost:.2f}"),
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
    """Matches not finished: playing (a move in the last hour), paused (started, no recent move), to play."""
    if not lg["pending"]:
        return ""
    rows = []
    for p in lg["pending"]:
        state = '<span class="live">playing</span>' if p["state"] == "playing" else p["state"]
        started = p["state"] != "to play"
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


def status(result: dict) -> str:
    parts = []
    for lg in result["leagues"]:
        if lg["status"] == "finished":
            parts.append(f"League {lg['id']} has finished")
            continue
        playing = sum(p["state"] == "playing" for p in lg["pending"])
        parts.append(f"League {lg['id']} has {len(lg['pending'])} of {lg['matches']} matches to play"
                     + (f" ({playing} playing)" if playing else ""))
    return "; ".join(parts) + "."


def progress(lg: dict) -> str:
    return f"{lg['finished']} of {lg['matches']} matches finished, {lg['games']:,} games"


def patch(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- v3:{name} -->).*?(<!-- /v3:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker v3:{name} not found")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main():
    db_path, score_glob, json_out, html_path = sys.argv[1:5]
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    scored, skipped = scores(sorted(glob.glob(score_glob)))
    as_of = utc(conn.execute("SELECT MAX(created_at) FROM turns").fetchone()[0])
    rng = random.Random(1)
    result = dict(
        data_as_of=as_of.strftime("%Y-%m-%dT%H:%MZ"),
        gnubg=dict(scored=len(scored), skipped=skipped, method="GNU Backgammon 1.08: 0-ply on every play, 2-ply on the five best and the chosen one"),
        leagues=[league(conn, lid, scored, rng, as_of) for lid in (1, 2, 3)],
    )
    result["scored"] = sum(m.get("scored", 0) for lg in result["leagues"] for m in lg["models"])
    Path(json_out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

    text = Path(html_path).read_text()
    text = patch(text, "live", live(result))
    text = patch(text, "status", status(result))
    text = patch(text, "scored", f"{result['scored']:,}")
    for lg in result["leagues"]:
        text = patch(text, f"league{lg['id']}", "\n      " + tables(lg) + "\n      ")
        text = patch(text, f"progress{lg['id']}", progress(lg))
    Path(html_path).write_text(text)


if __name__ == "__main__":
    main()
