#!/usr/bin/env python3
"""Original-league tables and the Hype Cup roster built from them (mailbox/backgammon-ladder-cup.md,
Part 2, amendments of 2026-10-27 and 2026-10-28, Can). Read-only on the database.

    python3 tools/original_league.py tables [--db v3.db] [--scores DIR]   # tables, tiebreaks
    python3 tools/original_league.py cup    [--db v3.db] [--scores DIR]   # roster, draw, stored pairings

Rules:
- Each setup is counted in its original league (`league_web.league_origins`: its league before any
  ladder move); GNUbg weak, the anchor, is in all three. Only valid matches between setups of the
  same original league count (any league, ladder round or hidden league they were played in; legacy
  playoffs left out, as `tools/ladder.py`): 3 points for a win, 1 for a draw, 0 for a loss.
- Ranking (Can, 2026-10-28): points, then head-to-head, then the lower error rate. Two setups level
  on points: the winner of their match ranks higher; a drawn match goes to the lower error rate.
  Three or more: a mini-table of the matches among them only (3/1/0); setups still level on it are
  ranked by the lower error rate (no further head-to-head step).
- Error rate: the site's (brief B11): 500 x mean GNUbg 1.08 2-ply equity loss of the setup's
  decisions with two or more legal plays, invalid answers (`decided_by = 'fallback'`) left out,
  over the matches counted in that original-league table only, from the site's score shards
  (`tools/site/score.sh`). Decisions not scored yet are reported as pending.
- Cup (Part 2): the top 2 models of each original-league table (programs skipped) and the two
  3rd-placed models with the lowest error rates (each 3rd place's rate in its own table); seeds
  L3 #1, L3 #2, L2 #1, L2 #2, L1 #1, L1 #2, better 3rd, other 3rd; seeds 1-4 pick in that order the
  lowest-seeded remaining team from a different league (a forced same-league last pick swaps
  opponents with the previous pick); semi-final A = winners of QF seed 1 and seed 4, B = seed 2 and
  seed 3. A Cup pairing already played (any valid match) stands.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import league_web as lw  # noqa: E402
from ladder import PROGRAM_SPECS, pair_matches, played_in  # noqa: E402

LEAGUES = [1, 2, 3]
ANCHOR = "GNUbg weak"


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def members(conn) -> dict[int, list[str]]:
    """Every original league's setups (GNUbg weak in all three)."""
    groups = {lid: set() for lid in LEAGUES}
    for lid in LEAGUES:
        for name, origin in lw.league_origins(conn, lid).items():
            groups[origin].add(name)
    for lid in LEAGUES:
        groups[lid].add(ANCHOR)
    return {lid: sorted(g) for lid, g in groups.items()}


def counted_matches(conn, names: list[str]) -> tuple[dict[frozenset, dict], list[dict]]:
    """The finished valid matches between the setups `names`, by pair, and the unfinished ones."""
    wanted = set(names)
    done, running = {}, []
    for r in conn.execute(
            """SELECT m.id, m.status, m.score1, m.score2, p1.name AS a, p2.name AS b
               FROM matches m JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
               WHERE m.valid = 1 AND m.stage IS NOT NULL AND m.stage <> 'playoff' ORDER BY m.id"""):
        if r["a"] not in wanted or r["b"] not in wanted:
            continue
        key = frozenset((r["a"], r["b"]))
        if r["status"] != "finished":
            running.append(dict(r))
        elif key in done:
            raise SystemExit(f"two valid finished matches for {r['a']} v {r['b']}: #{done[key]['id']}, #{r['id']}")
        else:
            done[key] = dict(r)
    return done, running


def load_losses(scores: Path) -> tuple[dict[int, float], set[int]]:
    loss: dict[int, float] = {}
    skipped: set[int] = set()
    for path in sorted(scores.glob("s*.db")):
        shard = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            loss.update(shard.execute("SELECT turn_id, loss FROM plays"))
            skipped.update(t for (t,) in shard.execute("SELECT turn_id FROM skipped"))
        finally:
            shard.close()
    return loss, skipped


def error_rates(conn, match_ids: list[int], losses) -> dict[str, dict]:
    """Per setup: the site's error rate over the decisions of `match_ids` only."""
    loss, skipped = losses
    out: dict[str, dict] = {}
    marks = ",".join("?" * len(match_ids)) or "NULL"
    for turn, name in conn.execute(
            f"""SELECT t.id, p.name FROM turns t JOIN games g ON g.id = t.game_id
                JOIN matches m ON m.id = g.match_id
                JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
                WHERE m.id IN ({marks}) AND t.decided_by = 'model' AND t.legal_count >= 2""", match_ids):
        r = out.setdefault(name, dict(loss=0.0, scored=0, skipped=0, pending=0))
        if turn in loss:
            r["loss"] += loss[turn]
            r["scored"] += 1
        elif turn in skipped:
            r["skipped"] += 1
        else:
            r["pending"] += 1
    for r in out.values():
        r["rate"] = lw.ERROR_SCALE * r["loss"] / r["scored"] if r["scored"] else None
    return out


def score_of(match: dict, name: str) -> tuple[int, int]:
    """(for, against) of `name` in `match`."""
    return (match["score1"], match["score2"]) if match["a"] == name else (match["score2"], match["score1"])


def rate_key(rates: dict, name: str) -> float:
    rate = rates.get(name, {}).get("rate")
    return float("inf") if rate is None else rate


def break_tie(group: list[str], done: dict, rates: dict) -> tuple[list[str], dict]:
    """Ranks setups level on points (Can, 2026-10-28) and says how."""
    if len(group) == 2:
        a, b = group
        match = done.get(frozenset(group))
        note = dict(kind="head-to-head", setups=group, match=match)
        if match is None:
            note["decided_by"] = "no match between them yet: lower error rate"
            order = sorted(group, key=lambda n: rate_key(rates, n))
        else:
            fa, fb = score_of(match, a)
            if fa != fb:
                order = [a, b] if fa > fb else [b, a]
                note["decided_by"] = "head-to-head"
            else:
                order = sorted(group, key=lambda n: rate_key(rates, n))
                note["decided_by"] = "drawn match: lower error rate"
        note["level_rates"] = rate_key(rates, order[0]) == rate_key(rates, order[1])
        return order, note
    mini = {n: dict(pts=0, p=0, w=0, d=0, l=0, f=0, a=0) for n in group}
    missing = []
    for i, a in enumerate(group):
        for b in group[i + 1:]:
            match = done.get(frozenset((a, b)))
            if match is None:
                missing.append((a, b))
                continue
            for x, y in ((a, b), (b, a)):
                f, ag = score_of(match, x)
                r = mini[x]
                r["p"] += 1
                r["f"] += f
                r["a"] += ag
                if f > ag:
                    r["w"] += 1
                    r["pts"] += 3
                elif f == ag:
                    r["d"] += 1
                    r["pts"] += 1
                else:
                    r["l"] += 1
    order = sorted(group, key=lambda n: (-mini[n]["pts"], rate_key(rates, n)))
    still = [n for n in group if sum(mini[m]["pts"] == mini[n]["pts"] for m in group) > 1]
    pairs = [(a, b, done[frozenset((a, b))]) for i, a in enumerate(group) for b in group[i + 1:]
             if frozenset((a, b)) in done]
    return order, dict(kind="mini-table", setups=group, mini=mini, pairs=pairs, missing=missing,
                       by_error_rate=still)


def league_table(conn, lid: int, losses) -> dict:
    names = members(conn)[lid]
    done, running = counted_matches(conn, names)
    rates = error_rates(conn, [m["id"] for m in done.values()], losses)
    rows = {n: dict(name=n, pts=0, p=0, w=0, d=0, l=0, f=0, a=0) for n in names}
    for match in done.values():
        for x in (match["a"], match["b"]):
            f, ag = score_of(match, x)
            r = rows[x]
            r["p"] += 1
            r["f"] += f
            r["a"] += ag
            if f > ag:
                r["w"] += 1
                r["pts"] += 3
            elif f == ag:
                r["d"] += 1
                r["pts"] += 1
            else:
                r["l"] += 1
    by_points: dict[int, list[str]] = {}
    for n in names:
        by_points.setdefault(rows[n]["pts"], []).append(n)
    order, ties = [], []
    for pts in sorted(by_points, reverse=True):
        group = by_points[pts]
        if len(group) == 1:
            order += group
            continue
        ranked, note = break_tie(group, done, rates)
        note["points"] = pts
        order += ranked
        ties.append(note)
    missing = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if frozenset((a, b)) not in done]
    programs = {r["name"] for r in conn.execute("SELECT name, spec FROM players") if r["spec"] in PROGRAM_SPECS}
    return dict(lid=lid, names=names, rows=[rows[n] for n in order], rates=rates, ties=ties, done=done,
                running=running, missing=missing, programs=programs)


def fmt_rate(rates: dict, name: str) -> str:
    r = rates.get(name)
    if not r or r["rate"] is None:
        return "–"
    return f"{r['rate']:.2f}" + (f" ({r['pending']} pending)" if r["pending"] else "")


def result(match: dict) -> str:
    if match["score1"] == match["score2"]:
        return f"{match['a']} {match['score1']}–{match['score2']} {match['b']} (draw, #{match['id']})"
    w, l, fw, fl = ((match["a"], match["b"], match["score1"], match["score2"]) if match["score1"] > match["score2"]
                    else (match["b"], match["a"], match["score2"], match["score1"]))
    return f"{w} beat {l} {fw}–{fl} (#{match['id']})"


def render_tables(tables: list[dict]) -> str:
    out = []
    for t in tables:
        n = len(t["names"])
        need = n * (n - 1) // 2
        state = "complete" if not t["missing"] else f"{len(t['missing'])} pairings missing, provisional"
        out.append(f"## League {t['lid']}: {n} setups, {len(t['done'])} of {need} pairings played ({state})\n")
        if t["missing"]:
            out.append("Missing: " + "; ".join(f"{a} v {b}" for a, b in t["missing"]) + ".\n")
        out.append("| # | Setup | Pts | P | W-D-L | For | Against | Error rate |")
        out.append("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(t["rows"], 1):
            tag = " (program)" if r["name"] in t["programs"] else ""
            out.append(f"| {i} | {r['name']}{tag} | {r['pts']} | {r['p']} | {r['w']}-{r['d']}-{r['l']} | "
                       f"{r['f']} | {r['a']} | {fmt_rate(t['rates'], r['name'])} |")
        out.append("")
        if t["ties"]:
            out.append(f"Ties on points in League {t['lid']}:\n")
        for note in t["ties"]:
            rates = t["rates"]
            if note["kind"] == "head-to-head":
                m = note["match"]
                how = note["decided_by"]
                line = f"- {note['points']} points: {' and '.join(note['setups'])}: "
                line += (result(m) if m else "no match") + f"; decided by {how}"
                if how != "head-to-head":
                    line += " (" + ", ".join(f"{s} {fmt_rate(rates, s)}" for s in note["setups"]) + ")"
                out.append(line + ".")
            else:
                out.append(f"- {note['points']} points: {', '.join(note['setups'])}: mini-table of the matches "
                           "among them:\n")
                for a, b, m in note["pairs"]:
                    out.append(f"  - {result(m)}")
                for a, b in note["missing"]:
                    out.append(f"  - {a} v {b}: not played yet")
                out.append("")
                out.append("  | Setup | Mini Pts | P | W-D-L | For | Against | Error rate |")
                out.append("  |---|---|---|---|---|---|---|")
                ranked = sorted(note["setups"], key=lambda s: (-note["mini"][s]["pts"], rate_key(rates, s)))
                for s in ranked:
                    r = note["mini"][s]
                    out.append(f"  | {s} | {r['pts']} | {r['p']} | {r['w']}-{r['d']}-{r['l']} | {r['f']} | {r['a']} | "
                               f"{fmt_rate(rates, s)} |")
                out.append("")
                if note["by_error_rate"]:
                    out.append("  Still level on the mini-table, ranked by the lower error rate: "
                               + ", ".join(f"{s} ({fmt_rate(rates, s)})" for s in
                                           sorted(note["by_error_rate"], key=lambda s: rate_key(rates, s))) + ".")
                else:
                    out.append("  The mini-table separates them; no error rate needed.")
            out.append("")
        if t["running"]:
            out.append("Running: " + "; ".join(f"#{m['id']} {m['a']} v {m['b']}" for m in t["running"]) + ".\n")
    return "\n".join(out)


def cup(tables: list[dict], conn) -> dict:
    """Roster, seeds, quarter-final draw and the stored results of every possible Cup pairing."""
    by = {t["lid"]: t for t in tables}
    models = {lid: [r["name"] for r in by[lid]["rows"] if r["name"] not in by[lid]["programs"]] for lid in LEAGUES}
    thirds = sorted(((models[lid][2], lid) for lid in LEAGUES), key=lambda x: rate_key(by[x[1]]["rates"], x[0]))
    seeds = [(models[3][0], 3, "League 3 #1"), (models[3][1], 3, "League 3 #2"),
             (models[2][0], 2, "League 2 #1"), (models[2][1], 2, "League 2 #2"),
             (models[1][0], 1, "League 1 #1 model"), (models[1][1], 1, "League 1 #2 model"),
             (thirds[0][0], thirds[0][1], f"League {thirds[0][1]} 3rd model, better 3rd place"),
             (thirds[1][0], thirds[1][1], f"League {thirds[1][1]} 3rd model, other 3rd place")]
    remaining = list(range(4, 8))
    picks, steps = [], []
    for s in range(4):
        options = [k for k in sorted(remaining, reverse=True) if seeds[k][1] != seeds[s][1]]
        if options:
            k = options[0]
            skipped = [j for j in sorted(remaining, reverse=True) if j > k]
            steps.append((s, k, skipped))
        else:
            k = remaining[0]
            steps.append((s, k, "forced"))
        remaining.remove(k)
        picks.append([s, k])
    swap = None
    if seeds[picks[3][0]][1] == seeds[picks[3][1]][1]:
        picks[2][1], picks[3][1] = picks[3][1], picks[2][1]
        swap = (picks[2], picks[3])
    stored = pair_matches(conn)
    qf = {s: k for s, k in picks}
    names = [s[0] for s in seeds]

    def pairing(a: int, b: int) -> dict:
        m = stored.get(frozenset((names[a], names[b])))
        return dict(a=a, b=b, match=m, where=played_in(conn, m) if m else [])

    rounds = dict(qf=[pairing(s, qf[s]) for s in range(4)])
    sf = []
    for x, y in ((0, 3), (1, 2)):
        for a in (x, qf[x]):
            for b in (y, qf[y]):
                sf.append(pairing(a, b))
    rounds["sf"] = sf
    final = []
    for a in (0, 3, qf[0], qf[3]):
        for b in (1, 2, qf[1], qf[2]):
            final.append(pairing(a, b))
    rounds["final"] = final
    return dict(seeds=seeds, thirds=thirds, steps=steps, swap=swap, picks=picks, rounds=rounds, by=by)


def render_cup(c: dict) -> str:
    seeds, by = c["seeds"], c["by"]
    out = ["## The 8 teams and their seeds\n", "| Seed | Team | From | Error rate (in its original-league table) |",
           "|---|---|---|---|"]
    for i, (name, lid, why) in enumerate(seeds, 1):
        out.append(f"| {i} | {name} | {why} | {fmt_rate(by[lid]['rates'], name)} |")
    out.append("\n3rd-placed models: " + "; ".join(
        f"League {lid} {name} {fmt_rate(by[lid]['rates'], name)}" for name, lid in c["thirds"]) + ".\n")
    out.append("## Quarter-final draw\n")
    for s, k, skipped in c["steps"]:
        note = ("the one left" if skipped == "forced" else
                "lower seeds skipped (same league): " + ", ".join(f"seed {j + 1}" for j in skipped) if skipped else
                "the lowest-seeded remaining team, from a different league")
        out.append(f"{s + 1}. Seed {s + 1}, {seeds[s][0]} (League {seeds[s][1]}) takes seed {k + 1}, "
                   f"{seeds[k][0]} (League {seeds[k][1]}): {note}.")
    out.append("\n" + ("Swap rule used: the last pick would pair two setups of one league, so it swapped "
                       "opponents with the previous pick." if c["swap"] else
                       "No quarter-final pairs two setups of one league, so the swap rule is not needed.") + "\n")

    def label(p: dict) -> str:
        return f"{seeds[p['a']][0]} ({p['a'] + 1}) v {seeds[p['b']][0]} ({p['b'] + 1})"

    def stored(p: dict) -> str:
        m = p["match"]
        if m is None:
            return "none | new match needed"
        if m["status"] != "finished":
            return f"#{m['id']} ({m['status']}) | not finished"
        return f"#{m['id']}, {', '.join(p['where']) or 'no league'} | {result(m)}"

    out.append("## Bracket\n")
    for i, p in enumerate(c["rounds"]["qf"], 1):
        out.append(f"- **QF{i}:** {label(p)}")
    out.append("- **Semi-final A:** winner QF1 v winner QF4")
    out.append("- **Semi-final B:** winner QF2 v winner QF3")
    out.append("- **Final:** winner SF A v winner SF B\n")
    out.append("## Stored results (a pairing already played stands)\n")
    out.append("| Round | Pairing | Stored | Result |\n|---|---|---|---|")
    for rnd, title in (("qf", "QF"), ("sf", "SF"), ("final", "Final")):
        for p in c["rounds"][rnd]:
            out.append(f"| {title} | {label(p)} | {stored(p)} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["tables", "cup"])
    ap.add_argument("--db", type=Path, default=ROOT / "v3.db")
    ap.add_argument("--scores", type=Path, default=lw.default_scores())
    args = ap.parse_args()
    conn = connect(args.db)
    losses = load_losses(args.scores)
    tables = [league_table(conn, lid, losses) for lid in LEAGUES]
    if args.command == "tables":
        print(render_tables(tables))
    else:
        if any(t["missing"] for t in tables):
            print("Warning: an original league is not a complete round robin; the roster is provisional.\n")
        print(render_cup(cup(tables, conn)))


if __name__ == "__main__":
    main()
