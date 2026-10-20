#!/usr/bin/env python3
"""Analysis of the roll-schedule experiment (system Python with numpy and scipy).

    python3 analyze.py DATA_DIR [LONG_DIR]

DATA_DIR holds sim.py `rr` output (rr.*.jsonl) and pr.py output in DATA_DIR/../pr; LONG_DIR,
if given, sim.py `long` output. Prints markdown tables.
"""

import collections
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NAMES = ["1-ply", "Advanced", "n0.030", "Intermediate", "Casual", "n0.055", "Beginner", "n0.100"]
PR_NAME = {"1-ply": "1p n0.000", "Advanced": "0p n0.015", "n0.030": "0p n0.030",
           "Intermediate": "0p n0.040", "Casual": "0p n0.050", "n0.055": "0p n0.055",
           "Beginner": "0p n0.060", "n0.100": "0p n0.100"}
PAIR = ("Casual", "n0.055")
BOOT = 4000
rng = np.random.default_rng(1)
P = len(NAMES)
IDX = {n: i for i, n in enumerate(NAMES)}


def load(pattern):
    rows = [json.loads(line) for f in sorted(glob.glob(pattern)) for line in open(f)]
    return rows


def table(matches):
    """Per player: points, games won, games lost; ranks (1 = top) by the league key, ties
    sharing the average rank."""
    pts, gw, gl = np.zeros(P), np.zeros(P), np.zeros(P)
    for m in matches:
        a, b = IDX[m["m1"]], IDX[m["m2"]]
        if m["winner"] is None:
            pts[a] += 1
            pts[b] += 1
        else:
            pts[a if m["winner"] == 1 else b] += 3
        gw[a] += m["games_won"][0]
        gw[b] += m["games_won"][1]
        gl[a] += m["games_won"][1]
        gl[b] += m["games_won"][0]
    key = pts * 1e6 + gw * 1e3 - gl  # points, then games won, then fewer games lost
    rank = rankdata(-key, method="average")
    return pts, key, rank


def ci(samples, lo=2.5, hi=97.5):
    return np.percentile(samples, lo), np.percentile(samples, hi)


def fmt_ci(x, s, d=3):
    lo, hi = ci(s)
    return f"{x:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


data_dir = sys.argv[1]
long_dir = sys.argv[2] if len(sys.argv) > 2 else None
rows = load(os.path.join(data_dir, "rr.*.jsonl"))
by = {"A": {}, "B": {}}
for r in rows:
    by[r["job"][1]][r["job"][2]] = r
for s in "AB":
    by[s] = [by[s][i] for i in sorted(by[s])]
n_rep = {s: len(by[s]) for s in "AB"}
print(f"replays: A {n_rep['A']}, B {n_rep['B']}\n")

# --- True strength --------------------------------------------------------------------------
pr = {}
for f in glob.glob(os.path.join(data_dir, "..", "pr", "*.json")):
    pr.update(json.load(open(f)))
print("## True strength (v1 set, PR = 500 x mean 2-ply loss, 1,000 positions)\n")
print("| player | gnubg context | PR | gap to next (paired SE) |")
print("|---|---|---:|---|")
for i, n in enumerate(NAMES):
    c = pr[PR_NAME[n]]
    gap = ""
    if i + 1 < P:
        d = 500 * (np.array(pr[PR_NAME[NAMES[i + 1]]]["losses"]) - np.array(c["losses"]))
        gap = f"{d.mean():.2f} ({d.std(ddof=1) / np.sqrt(len(d)):.2f})"
    ctx = c["context"]
    print(f"| {n} | {ctx['plies']}-ply, noise {ctx['noise']:.3f}, det | {c['pr']:.2f} | {gap} |")
print()

tabs = {s: [table(r["matches"]) for r in by[s]] for s in "AB"}
points = {s: np.array([t[0] for t in tabs[s]]) for s in "AB"}   # replays x players
ranks = {s: np.array([t[2] for t in tabs[s]]) for s in "AB"}
keys = {s: np.array([t[1] for t in tabs[s]]) for s in "AB"}
true_rank = np.arange(1, P + 1)


def boot_idx(n):
    return rng.integers(0, n, size=(BOOT, n))


bi = {s: boot_idx(n_rep[s]) for s in "AB"}

# --- (1) Scatter of league points ------------------------------------------------------------
print("## (1) League points per player across replays\n")
print("| player | mean A | mean B | SD A | SD B | SD B/A |")
print("|---|---:|---:|---:|---:|---:|")
sd = {s: points[s].std(axis=0, ddof=1) for s in "AB"}
for i, n in enumerate(NAMES):
    print(f"| {n} | {points['A'][:, i].mean():.2f} | {points['B'][:, i].mean():.2f} | "
          f"{sd['A'][i]:.2f} | {sd['B'][i]:.2f} | {sd['B'][i] / sd['A'][i]:.2f} |")
msd = {s: sd[s].mean() for s in "AB"}
bsd = {s: np.array([points[s][ix].std(axis=0, ddof=1).mean() for ix in bi[s]]) for s in "AB"}
print(f"\nMean SD over players: A {fmt_ci(msd['A'], bsd['A'], 2)}, B {fmt_ci(msd['B'], bsd['B'], 2)}; "
      f"ratio B/A {fmt_ci(msd['B'] / msd['A'], bsd['B'] / bsd['A'])} (bootstrap over replays, "
      f"{BOOT} resamples, 95% percentile CI)")
var_ratio = (sd["B"] ** 2).mean() / (sd["A"] ** 2).mean()
bvar = np.array([(points['B'][ib].std(axis=0, ddof=1) ** 2).mean() / (points['A'][ia].std(axis=0, ddof=1) ** 2).mean()
                 for ia, ib in zip(bi["A"], bi["B"])])
print(f"Mean variance ratio B/A: {fmt_ci(var_ratio, bvar)}")
rsd = {s: ranks[s].std(axis=0, ddof=1).mean() for s in "AB"}
print(f"Mean SD of finishing place: A {rsd['A']:.2f}, B {rsd['B']:.2f}\n")

# Why: a player's matches in one replay. Match league points (3/1/0) per (replay, player,
# opponent), centred on the pair's mean over replays; correlation between two matches of the
# same player in the same replay, averaged over players and opponent pairs.
print("Correlation between two matches of the same player in the same replay (match league "
      "points, centred per pairing), mean over players and opponent pairs:")
for s in "AB":
    mp = np.zeros((n_rep[s], P, P))
    for ri, r in enumerate(by[s]):
        for m in r["matches"]:
            a, b = IDX[m["m1"]], IDX[m["m2"]]
            pa = 1 if m["winner"] is None else (3 if m["winner"] == 1 else 0)
            pb = 1 if m["winner"] is None else (3 if m["winner"] == 2 else 0)
            mp[ri, a, b], mp[ri, b, a] = pa, pb
    mp -= mp.mean(axis=0)
    cs = []
    for x in range(P):
        opp = [o for o in range(P) if o != x]
        for u in range(len(opp)):
            for v in range(u + 1, len(opp)):
                c = np.corrcoef(mp[:, x, opp[u]], mp[:, x, opp[v]])[0, 1]
                if np.isfinite(c):
                    cs.append(c)
    print(f"- {s}: {np.mean(cs):+.3f} (SD over pairs {np.std(cs):.3f}, {len(cs)} pairs)")
print()
print("SD of the league-points difference of neighbouring players (stronger - weaker) across "
      "replays:\n")
print("| pair | mean diff A | mean diff B | SD A | SD B | SD B/A [95% CI] |")
print("|---|---:|---:|---:|---:|---|")
for i in range(P - 1):
    d = {s: points[s][:, i] - points[s][:, i + 1] for s in "AB"}
    bs = d["B"][bi["B"]].std(axis=1, ddof=1) / d["A"][bi["A"]].std(axis=1, ddof=1)
    print(f"| {NAMES[i]} v {NAMES[i + 1]} | {d['A'].mean():.2f} | {d['B'].mean():.2f} | "
          f"{d['A'].std(ddof=1):.2f} | {d['B'].std(ddof=1):.2f} | "
          f"{fmt_ci(d['B'].std(ddof=1) / d['A'].std(ddof=1), bs, 2)} |")
print()

# --- (2) Spearman ---------------------------------------------------------------------------
print("## (2) Spearman correlation of standings with the true order\n")
rho = {s: np.array([spearmanr(-true_rank, -r)[0] for r in ranks[s]]) for s in "AB"}
brho = {s: rho[s][bi[s]].mean(axis=1) for s in "AB"}
for s in "AB":
    exact = np.mean([np.array_equal(r, true_rank) for r in ranks[s]])
    print(f"- {s}: mean rho {fmt_ci(rho[s].mean(), brho[s])}, median {np.median(rho[s]):.3f}, "
          f"exact true order {100 * exact:.1f}% of replays, top place right "
          f"{100 * np.mean(ranks[s][:, 0] == 1):.1f}%")
print(f"- B - A: {fmt_ci(rho['B'].mean() - rho['A'].mean(), brho['B'] - brho['A'])}\n")

# --- (3) Pairs ------------------------------------------------------------------------------
print("## (3) Does the stronger player finish above the weaker one? (league key: points, games "
      "won, fewer games lost; ties = level on all three, before playoffs)\n")


def pair_stats(s, i, j):
    k = keys[s]
    above, tie = k[:, i] > k[:, j], k[:, i] == k[:, j]
    return above, tie


print("| pair (stronger v weaker) | dPR | A above / tie / below | B above / tie / below | B - A above [95% CI] |")
print("|---|---:|---|---|---|")
pairs = [(i, i + 1) for i in range(P - 1)]
for i, j in pairs:
    out = []
    for s in "AB":
        above, tie = pair_stats(s, i, j)
        out.append((above.mean(), tie.mean(), 1 - above.mean() - tie.mean(), above))
    diff = out[1][3][bi["B"]].mean(axis=1) - out[0][3][bi["A"]].mean(axis=1)
    dpr = pr[PR_NAME[NAMES[j]]]["pr"] - pr[PR_NAME[NAMES[i]]]["pr"]
    tag = " (near-equal pair)" if (NAMES[i], NAMES[j]) == PAIR else ""
    print(f"| {NAMES[i]} v {NAMES[j]}{tag} | {dpr:.1f} | "
          + " | ".join(f"{100 * a:.1f} / {100 * t:.1f} / {100 * w:.1f}%" for a, t, w, _ in out)
          + f" | {fmt_ci(100 * (out[1][0] - out[0][0]), 100 * diff, 1)} |")
for label, sel in (("all 7 neighbouring pairs", pairs),
                   ("all 28 pairs", [(i, j) for i in range(P) for j in range(i + 1, P)])):
    res = []
    for s in "AB":
        a = np.mean([pair_stats(s, i, j)[0].mean() for i, j in sel])
        t = np.mean([pair_stats(s, i, j)[1].mean() for i, j in sel])
        res.append(f"{s} {100 * a:.1f} / {100 * t:.1f} / {100 * (1 - a - t):.1f}%")
    print(f"| {label}, mean | | " + " | ".join(r[2:] for r in res) + " | |")
print()
print("Points only (ties on league points, ignoring the games tiebreaks):\n")
print("| pair | A above / tie / below | B above / tie / below |")
print("|---|---|---|")
for i, j in pairs:
    cells = []
    for s in "AB":
        p = points[s]
        a, t = (p[:, i] > p[:, j]).mean(), (p[:, i] == p[:, j]).mean()
        cells.append(f"{100 * a:.1f} / {100 * t:.1f} / {100 * (1 - a - t):.1f}%")
    print(f"| {NAMES[i]} v {NAMES[j]} | " + " | ".join(cells) + " |")
print()

# --- Head-to-head and game statistics ------------------------------------------------------
print("## Head to head in the round robins (per scheme; same expectation under both)\n")
print("| pair (stronger v weaker) | A: W / D / L % | B: W / D / L % | A+B ppg diff (SE) |")
print("|---|---|---|---|")
h2h = collections.defaultdict(lambda: {"A": [], "B": []})
ppg = collections.defaultdict(list)
for s in "AB":
    for r in by[s]:
        for m in r["matches"]:
            a, b = IDX[m["m1"]], IDX[m["m2"]]
            res = 0 if m["winner"] is None else (1 if (m["winner"] == 1) == (a < b) else -1)
            key = (min(a, b), max(a, b))
            h2h[key][s].append(res)
            sa, sb = m["score"] if a < b else m["score"][::-1]
            ppg[key].append((sa - sb, len(m["games"])))
for i, j in pairs:
    cells = []
    for s in "AB":
        v = np.array(h2h[(i, j)][s])
        cells.append(f"{100 * (v == 1).mean():.1f} / {100 * (v == 0).mean():.1f} / {100 * (v == -1).mean():.1f}")
    d = np.array(ppg[(i, j)], dtype=float)
    per_match = d[:, 0] / d[:, 1]
    print(f"| {NAMES[i]} v {NAMES[j]} | " + " | ".join(cells)
          + f" | {d[:, 0].sum() / d[:, 1].sum():+.3f} ({per_match.std(ddof=1) / np.sqrt(len(d)):.3f}) |")
print()


def tie_break(m):
    """Whether the match needed the extra round (src/runner.rs rounds_after): regular play ends
    after round 3 or the first round ending with someone on 5+; any later round is the
    tie-break."""
    s = [0, 0]
    for k in range(0, len(m["games"]), 2):
        for g in m["games"][k:k + 2]:
            s[g[2] - 1] += g[4]
        rnd = m["games"][k][0]
        if rnd >= 3 or max(s) >= 5:
            return len(m["games"]) > k + 2
    return False


print("## Games\n")
print("| | A | B |")
print("|---|---:|---:|")
stats = {}
for s in "AB":
    games = [g for r in by[s] for m in r["matches"] for g in m["games"]]
    kinds = collections.Counter(g[3] for g in games)
    ms = [m for r in by[s] for m in r["matches"]]
    stats[s] = {
        "games": len(games),
        "games per match": np.mean([len(m["games"]) for m in ms]),
        "matches drawn %": 100 * np.mean([m["winner"] is None for m in ms]),
        "matches with a tie-break round %": 100 * np.mean([tie_break(m) for m in ms]),
        "gammon or backgammon %": 100 * (kinds["gammon"] + kinds["backgammon"]) / len(games),
        "backgammon %": 100 * kinds["backgammon"] / len(games),
        "turn limit %": 100 * kinds["turn_limit"] / len(games),
        "turns per game (mean)": np.mean([g[5] for g in games]),
        "turns per game (max)": max(g[5] for g in games),
        "gnubg decisions per game": np.mean([g[6] for g in games]),
        "split rounds (1-1, equal points) %": 100 * np.mean([
            m["games"][k][2] != m["games"][k + 1][2] and m["games"][k][4] == m["games"][k + 1][4]
            for m in ms for k in range(0, len(m["games"]), 2)]),
    }
for k in stats["A"]:
    a, b = stats["A"][k], stats["B"][k]
    f = (lambda x: f"{x:.0f}") if isinstance(a, (int, np.integer)) else (lambda x: f"{x:.2f}")
    print(f"| {k} | {f(a)} | {f(b)} |")
print()


# --- (4) Per-schedule effects --------------------------------------------------------------
def rounds_of(s):
    """(group, net points for the stronger player in the round, total points, upset, split,
    round) for rounds 1-3 of every match; group = (replay, round): in B the schedule id."""
    out = []
    for r in by[s]:
        for m in r["matches"]:
            a, b = IDX[m["m1"]], IDX[m["m2"]]
            strong = 1 if a < b else 2
            gs = m["games"]
            for k in range(0, len(gs), 2):
                rnd = gs[k][0]
                if rnd > 3:
                    continue
                net = sum((g[4] if g[2] == strong else -g[4]) for g in gs[k:k + 2])
                tot = gs[k][4] + gs[k + 1][4]
                split = gs[k][2] != gs[k + 1][2] and gs[k][4] == gs[k + 1][4]
                out.append((r["job"][2] * 10 + rnd, net, tot, net < 0, split, rnd))
    return np.array(out, dtype=float)


def eta2(groups, y):
    """Share of the variance of y explained by group means, and its chance level."""
    u, inv = np.unique(groups, return_inverse=True)
    means = np.bincount(inv, y) / np.bincount(inv)
    ss_b = (np.bincount(inv) * (means - y.mean()) ** 2).sum()
    ss_t = ((y - y.mean()) ** 2).sum()
    return ss_b / ss_t, (len(u) - 1) / (len(y) - 1)


print("## (4) Per-schedule effects: rounds 1-3 grouped by (replay, round) = the shared "
      "schedule in B; in A the same grouping is a null (independent dice per match)\n")
print("| measure (per match-round) | A: eta^2 (chance) | B: eta^2 (chance) |")
print("|---|---|---|")
rd = {s: rounds_of(s) for s in "AB"}
for col, label in ((1, "net points for the stronger player"), (2, "total points (gammons)"),
                   (3, "upset (weaker player ahead in the round)"), (4, "split round")):
    cells = []
    for s in "AB":
        e, c = eta2(rd[s][:, 0], rd[s][:, col])
        cells.append(f"{e:.3f} ({c:.3f})")
    print(f"| {label} | " + " | ".join(cells) + " |")
print()
for s in "AB":
    d = rd[s]
    u, inv = np.unique(d[:, 0], return_inverse=True)
    cnt = np.bincount(inv)
    full = cnt >= 20
    up = (np.bincount(inv, d[:, 3]) / cnt)[full]
    net = (np.bincount(inv, d[:, 1]) / cnt)[full]
    tot = (np.bincount(inv, d[:, 2]) / cnt)[full]
    spl = (np.bincount(inv, d[:, 4]) / cnt)[full]
    print(f"- {s}: per-(replay, round) groups with >= 20 matches: {full.sum()}; upset rate mean "
          f"{up.mean():.3f}, SD {up.std(ddof=1):.3f}, range {up.min():.2f}-{up.max():.2f}; mean net "
          f"for stronger SD {net.std(ddof=1):.3f} (range {net.min():+.2f} to {net.max():+.2f}); "
          f"split share range {spl.min():.2f}-{spl.max():.2f}; mean round points range "
          f"{tot.min():.2f}-{tot.max():.2f}")
print()

# Which round decides a replay's table in B: correlation of each round's points with the table.
print("Share of each player's league-points variance that follows a single schedule (B) vs the "
      "same round in A: correlation of the player's net round points (rounds 1, 2, 3) with its "
      "league points, averaged over players\n")
for s in "AB":
    cors = []
    for rnd in (1, 2, 3):
        per = np.zeros((n_rep[s], P))
        for ri, r in enumerate(by[s]):
            for m in r["matches"]:
                a, b = IDX[m["m1"]], IDX[m["m2"]]
                for g in m["games"]:
                    if g[0] == rnd:
                        w, l = (a, b) if g[2] == 1 else (b, a)
                        per[ri, w] += g[4]
                        per[ri, l] -= g[4]
        cors.append(np.nanmean([np.corrcoef(per[:, i], points[s][:, i])[0, 1] for i in range(P)]))
    print(f"- {s}: round 1 {cors[0]:.3f}, round 2 {cors[1]:.3f}, round 3 {cors[2]:.3f}")
print()

# --- Runtime --------------------------------------------------------------------------------
wall = sum(r["wall"] for r in rows)
cpu = sum(r["cpu"] for r in rows)
print(f"## Runtime\n\nSum over jobs: wall {wall / 3600:.2f} process-hours, CPU {cpu / 3600:.2f} "
      f"CPU-hours; per replay: wall {wall / len(rows):.1f} s, CPU {cpu / len(rows):.1f} s\n")

# --- Long-run check -------------------------------------------------------------------------
if long_dir:
    lr = load(os.path.join(long_dir, "long.*.jsonl"))
    print(f"## Long-run pairwise check ({len(lr)} independent matches)\n")
    agg = collections.defaultdict(list)
    for m in lr:
        a, b = IDX[m["m1"]], IDX[m["m2"]]
        res = 0 if m["winner"] is None else (1 if (m["winner"] == 1) == (a < b) else -1)
        sa, sb = m["score"] if a < b else m["score"][::-1]
        agg[(min(a, b), max(a, b))].append((res, sa - sb, len(m["games"])))
    print("| pair (stronger by PR v weaker) | matches | W / D / L % | league pts per match "
          "stronger - weaker (SE) | ppg diff (SE) |")
    print("|---|---:|---|---|---|")
    disagree = []
    for i in range(P):
        for j in range(i + 1, P):
            v = np.array(agg[(i, j)], dtype=float)
            res = v[:, 0]
            lp = np.where(res == 1, 3, np.where(res == 0, 0, -3))  # 3-0, 1-1, 0-3
            se = lp.std(ddof=1) / np.sqrt(len(lp))
            pg = v[:, 1] / v[:, 2]
            if lp.mean() <= 0:
                disagree.append(f"{NAMES[i]} v {NAMES[j]}")
            if j == i + 1 or (NAMES[i], NAMES[j]) == PAIR:
                print(f"| {NAMES[i]} v {NAMES[j]} | {len(v)} | {100 * (res == 1).mean():.1f} / "
                      f"{100 * (res == 0).mean():.1f} / {100 * (res == -1).mean():.1f} | "
                      f"{lp.mean():+.3f} ({se:.3f}) | {v[:, 1].sum() / v[:, 2].sum():+.3f} "
                      f"({pg.std(ddof=1) / np.sqrt(len(pg)):.3f}) |")
    print(f"\nPairs (of 28) where the PR-stronger player does not score more league points per "
          f"match: {', '.join(disagree) or 'none'}")
