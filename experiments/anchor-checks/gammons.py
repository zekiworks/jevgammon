"""Check 2: how games end in the v3 leagues, and what gammons do for the anchor (GNUbg weak).

    python3 gammons.py            # v3.db opened read-only; prints markdown tables

Counted league matches only: games of matches linked from league_matches (the latest attempt of
each fixture; voided and removed matches are not linked), as tools/v3/page_v3.py counts them.
games.result is single | gammon | backgammon | timeout | turn_limit, games.points the points the
winner scored (1/2/3; a turn-limit game is worth 1) and games.winner_player the player number
(1 = matches.model1). A finished game has a winner; unfinished games are left out.

1-point rescoring of the anchor's won matches replays the runner's stopping rule (src/runner.rs
play_match / rounds_after, league fixtures: 3 planned rounds, first to 5, not decisive) on the
recorded games in order, with every game worth 1. If the rule asks for a round that was not
played (the recorded match stopped earlier), the rescored match is "undetermined" and the score
after the recorded games is reported.
"""

import os
import sqlite3
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ANCHOR = "GNUbg weak"
BASELINES = {"Random", "Safest"}
ROUNDS, FIRST_TO = 3, 5
KINDS = ("single", "gammon", "backgammon")


def rounds_after(round_no, rounds, score, tie_break, decisive=False):
    if round_no < rounds and all(s < FIRST_TO for s in score):
        return rounds, tie_break
    if score[0] == score[1] and (not tie_break or decisive):
        return round_no + 1, True
    return round_no, tie_break


def replay(games, points):
    """Stopping rule over the recorded games {(round, leg): (winner, result, points)}, each
    game scored by points(game). Returns (score, rounds_used, complete)."""
    score = [0, 0]
    rounds, tie_break, round_no = ROUNDS, False, 1
    while round_no <= rounds:
        for leg in (1, 2):
            g = games.get((round_no, leg))
            if g is None:
                return score, round_no - 1, False
            score[g[0] - 1] += points(g)
        rounds, tie_break = rounds_after(round_no, rounds, score, tie_break)
        round_no += 1
    return score, rounds, True


def outcomes(games, p1):
    """Result distribution (1 = player 1 wins, 2 = player 2, None = draw) at 1 pt/game: recorded
    games as played, every game the stopping rule needs beyond them won by player 1 with
    probability p1, independently. Probability-zero branches are kept out."""
    dist = Counter()

    def go(round_no, leg, score, rounds, tie_break, prob, invented):
        if round_no > rounds:
            w = None if score[0] == score[1] else (1 if score[0] > score[1] else 2)
            dist[w] += prob
            return
        g = games.get((round_no, leg)) if not invented else None
        branches = [(g[0], 1.0)] if g else [(1, p1), (2, 1 - p1)]
        for winner, q in branches:
            if q == 0:
                continue
            s = list(score)
            s[winner - 1] += 1
            if leg == 1:
                go(round_no, 2, s, rounds, tie_break, prob * q, invented or not g)
            else:
                r, t = rounds_after(round_no, rounds, s, tie_break)
                go(round_no + 1, 1, s, r, t, prob * q, invented or not g)

    go(1, 1, [0, 0], ROUNDS, False, 1.0, False)
    return dict(dist)


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "–"


conn = sqlite3.connect(f"file:{os.path.join(REPO, 'v3.db')}?mode=ro", uri=True)
rows = conn.execute("""
    SELECT lm.league_id, lm.model1, lm.model2, m.id, m.status, m.winner, m.score1, m.score2,
           g.round_no, g.leg, g.winner_player, g.result, g.points, g.turns
    FROM league_matches lm JOIN matches m ON m.id = lm.match_id
    JOIN games g ON g.match_id = m.id
    WHERE lm.stage = 'league'
    ORDER BY lm.league_id, m.id, g.round_no, g.leg""").fetchall()

matches = {}
for (lid, m1, m2, mid, status, winner, s1, s2, rnd, leg, wp, result, pts, turns) in rows:
    m = matches.setdefault(mid, {"league": lid, "names": (m1, m2), "status": status,
                                 "winner": winner, "score": (s1, s2), "games": {}})
    if wp is not None:
        m["games"][(rnd, leg)] = (wp, result, pts, turns)


def category(names):
    if ANCHOR in names:
        return "anchor"
    if BASELINES & set(names):
        return "Random/Safest"
    return "model v model"


# --- game endings per league and category ------------------------------------------------------
print("## Game endings (finished games in counted league matches)\n")
print("| league | games | single | gammon | backgammon | gammon+bg | turn limit / timeout |")
print("|---|---:|---:|---:|---:|---:|---:|")
cats = ("anchor", "Random/Safest", "model v model")
anchor_side = defaultdict(Counter)
for lid in (1, 2):
    for cat in cats + ("all",):
        c = Counter()
        for m in matches.values():
            if m["league"] != lid or (cat != "all" and category(m["names"]) != cat):
                continue
            for wp, result, pts, turns in m["games"].values():
                c[result] += 1
                if cat == "anchor" and result in KINDS:
                    anchor_won = m["names"][wp - 1] == ANCHOR
                    anchor_side[lid][(result, anchor_won)] += 1
        n = sum(c.values())
        other = n - sum(c[k] for k in KINDS)
        print(f"| L{lid} {cat} | {n} | {pct(c['single'], n)} ({c['single']}) | "
              f"{pct(c['gammon'], n)} ({c['gammon']}) | {pct(c['backgammon'], n)} "
              f"({c['backgammon']}) | {pct(c['gammon'] + c['backgammon'], n)} | {other} |")

print("\n## Anchor games by winner\n")
print("| league | anchor won: single / gammon / bg | anchor lost: single / gammon / bg |")
print("|---|---|---|")
for lid in (1, 2):
    a = anchor_side[lid]
    won = " / ".join(str(a[(k, True)]) for k in KINDS)
    lost = " / ".join(str(a[(k, False)]) for k in KINDS)
    print(f"| L{lid} | {won} | {lost} |")

# --- the anchor's matches ------------------------------------------------------------------------
# Missing games (the 1-pt stopping rule asks for more than was played) are filled in two ways:
# each won by the anchor with p = 0.5, or with p = the anchor's game-win share in that league.
p_anchor = {lid: sum(v for (k, won), v in anchor_side[lid].items() if won)
            / sum(anchor_side[lid].values()) for lid in (1, 2)}


def anchor_view(m, p):
    """(P(win), P(draw), P(loss)) for the anchor at 1 pt/game."""
    me = m["names"].index(ANCHOR) + 1
    d = outcomes(m["games"], p if me == 1 else 1 - p)
    return d.get(me, 0.0), d.get(None, 0.0), d.get(3 - me, 0.0)


print("\n## Anchor matches (finished)\n")
print(f"Anchor game-win share used for missing games: L1 {p_anchor[1]:.3f}, L2 {p_anchor[2]:.3f}.\n")
print("| league | finished | won | drawn | lost | wins with ≥1 anchor gammon/bg | wins certain "
      "at 1 pt/game | wins certainly lost/drawn at 1 pt | wins open | expected wins at 1 pt "
      "(p = 0.5) | (p = anchor share) | expected wins over all its matches (p = 0.5 / share) |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
details = []
for lid in (1, 2):
    c = Counter()
    for mid, m in matches.items():
        if m["league"] != lid or ANCHOR not in m["names"] or m["status"] != "finished":
            continue
        me = m["names"].index(ANCHOR) + 1
        half, share = anchor_view(m, 0.5), anchor_view(m, p_anchor[lid])
        c["finished"] += 1
        c["all_half"] += half[0]
        c["all_share"] += share[0]
        if m["winner"] != me:
            c["drawn" if m["winner"] is None else "lost"] += 1
            continue
        c["won"] += 1
        gammons = sum(1 for wp, res, _, _ in m["games"].values()
                      if wp == me and res in ("gammon", "backgammon"))
        c["won_g"] += gammons > 0
        c["certain"] += half[0] == 1.0
        c["gone"] += half[0] == 0.0
        c["open"] += 0.0 < half[0] < 1.0
        c["half"] += half[0]
        c["share"] += share[0]
        score, used, complete = replay(m["games"], lambda g: 1)
        details.append((lid, mid, m["names"][2 - me], m["score"], len(m["games"]), gammons,
                        score, used, complete, half, share))
    print(f"| L{lid} | {c['finished']} | {c['won']} | {c['drawn']} | {c['lost']} | {c['won_g']} | "
          f"{c['certain']} | {c['gone']} | {c['open']} | {c['half']:.2f} | {c['share']:.2f} | "
          f"{c['all_half']:.2f} / {c['all_share']:.2f} |")

print("\n### Anchor wins, rescored at 1 pt/game\n")
print("| league | match | opponent | recorded score (anchor first) | games | anchor gammons/bg "
      "| 1-pt score after the recorded games, rounds | more games needed | P(anchor wins) "
      "p = 0.5 | p = share | P(draw / loss), p = 0.5 |")
print("|---|---:|---|---|---:|---:|---|---|---:|---:|---|")
for lid, mid, opp, score, n, gammons, s1, used, complete, half, share in details:
    m = matches[mid]
    me = m["names"].index(ANCHOR)
    print(f"| L{lid} | {mid} | {opp} | {score[me]}–{score[1 - me]} | {n} | {gammons} | "
          f"{s1[me]}–{s1[1 - me]}, {used} | {'no' if complete else 'yes'} | {half[0]:.3f} | "
          f"{share[0]:.3f} | {half[1]:.3f} / {half[2]:.3f} |")

# --- every counted match: does 1-pt scoring change the result? ------------------------------
print("\n## All finished league matches at 1 pt/game (missing games at p = 0.5)\n")
print("| league | category | finished | needs more games | result certainly same | certainly "
      "different | open | expected share with the same result |")
print("|---|---|---:|---:|---:|---:|---:|---:|")
for lid in (1, 2):
    for cat in cats:
        c = Counter()
        for m in matches.values():
            if m["league"] != lid or m["status"] != "finished" or category(m["names"]) != cat:
                continue
            c["n"] += 1
            c["more"] += not replay(m["games"], lambda g: 1)[2]
            same = outcomes(m["games"], 0.5).get(m["winner"], 0.0)
            c["same"] += same == 1.0
            c["diff"] += same == 0.0
            c["open"] += 0.0 < same < 1.0
            c["exp"] += same
        print(f"| L{lid} | {cat} | {c['n']} | {c['more']} | {c['same']} | {c['diff']} | "
              f"{c['open']} | {pct(c['exp'], c['n'])} |")

# sanity: the replay with recorded points reproduces every finished match
bad = [mid for mid, m in matches.items() if m["status"] == "finished"
       and replay(m["games"], lambda g: g[2])[0] != list(m["score"])]
print(f"\nReplay with recorded points reproduces the recorded score: "
      f"{sum(m['status'] == 'finished' for m in matches.values()) - len(bad)} finished matches "
      f"(mismatches: {bad or 'none'}).")
