"""v3 league results for the public report: a JSON of the numbers and the generated tables of
analysis/backgammon/index.html, from a snapshot of the league database and GNUbg's scores.

    sqlite3 v3.db ".backup /tmp/v3-snap.db"
    GNUBG_EVAL_ARGS="/tmp/v3-snap.db /tmp/v3-gnubg/sN.db N 32 1 2" gnubg -t -q -p tools/gnubg_eval.py   # N = 0..31
    python3 tools/v3/page_v3.py /tmp/v3-snap.db "/tmp/v3-gnubg/s*.db" \
        analysis/backgammon/v3-results.json analysis/backgammon/index.html

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

The HTML file is patched between `<!-- v3:NAME -->` and `<!-- /v3:NAME -->` markers: asof (data
time), scored (decisions scored), progress1/progress2 (matches finished), league1/league2 (tables).
The prose around them is written by hand and has to be checked against the new numbers after a
refresh. Standard library only.
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

RUNS_ON = {
    # League 1
    "Liquid d1-ultra": "Liquid AI decisions API",
    "GNUbg weak": "GNU Backgammon 1.08, Beginner level (0-ply, noise 0.060)",
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
    "Gemma 4 31B (on)": "our GPU, fp8 (vLLM); DGX Spark 19 Oct 19:40-22:26 UTC",
    "Gemma 4 31B (off)": "our GPU, fp8 (vLLM); DGX Spark 19 Oct 19:40-22:26 UTC",
    "Qwen3.8-27B (on)": "our GPU, fp16 (vLLM); first decisions on Cerebras via OpenRouter",
    "Qwen3.8-27B (off)": "our GPU, fp16 (vLLM); first decisions on Cerebras via OpenRouter",
    "DeepSeek V4.1 Flash (off)": "Fireworks via OpenRouter, quantization not published",
    "DeepSeek V4.1 Flash (on)": "Fireworks via OpenRouter, quantization not published",
    "Qwen3.8 Flash (off)": "Alibaba via OpenRouter, quantization not published",
    "GLM-5.3 (on)": "Fireworks via OpenRouter, quantization not published",
    "LFM2.5-24B-A2B (on)": "our GPU, bf16 (vLLM)",
    "LFM2.5-24B-A2B (off)": "our GPU, bf16 (vLLM)",
}

READOUT = {"decision": "option probabilities", "logprobs": "letter probabilities", "choice_only": "one letter"}


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


def league(conn: sqlite3.Connection, lid: int, scored: dict, rng: random.Random) -> dict:
    row = conn.execute("SELECT * FROM leagues WHERE id = ?", (lid,)).fetchone()
    roster = json.loads(row["models"])
    names = [m["name"] for m in roster]
    fixtures, games_won = league_fixtures(conn, lid)
    fixtures = [f for f in fixtures if f["stage"] == "league"]
    table = league_table(names, fixtures, games_won)
    left = {n: 0 for n in names}
    for f in fixtures:
        if f["status"] != "finished":
            left[f["model1"]] += 1
            left[f["model2"]] += 1

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
                   runs_on=RUNS_ON.get(name), decisions=0)
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
    return dict(id=lid, matches=len(fixtures), finished=finished, games=games, models=models)


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
        rows.append("<tr>" + "".join([
            cell(str(m["place"])), cell(name, "l"), cell(str(m["played"])), cell(str(m["won"])),
            cell(str(m["drawn"]), "zero" if not m["drawn"] else ""), cell(str(m["lost"])),
            cell(f"<strong>{m['points']}</strong>"), cell(f"{m['games_won']}-{m['games_lost']}"),
            cell(str(left), "zero" if not left else ""), cell(er), cell(pct(m.get("best_share"))),
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
    return f"""<div class="table-wrap">
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
    as_of = conn.execute("SELECT MAX(created_at) FROM turns").fetchone()[0]
    as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
    rng = random.Random(1)
    result = dict(
        data_as_of=as_of.strftime("%Y-%m-%dT%H:%MZ"),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        gnubg=dict(scored=len(scored), skipped=skipped, method="GNU Backgammon 1.08: 0-ply on every play, 2-ply on the five best and the chosen one"),
        leagues=[league(conn, lid, scored, rng) for lid in (1, 2)],
    )
    Path(json_out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

    text = Path(html_path).read_text()
    text = patch(text, "asof", as_of.strftime("%-d %B %Y, %H:%M UTC"))
    text = patch(text, "scored", f"{len(scored):,}")
    for lg in result["leagues"]:
        text = patch(text, f"league{lg['id']}", "\n      " + tables(lg) + "\n      ")
        text = patch(text, f"progress{lg['id']}",
                     f"{lg['finished']} of {lg['matches']} matches finished, {lg['games']:,} games")
    Path(html_path).write_text(text)


if __name__ == "__main__":
    main()
