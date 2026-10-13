#!/usr/bin/env python3
"""Scores teams of decision models offline on replay.db (tools/replay.py + tools/gnubg_eval.py).

    python3 tools/teams.py [--db replay.db] [--folds 2] [--seed 1]

A team is a set of models that all answer the same position; a rule picks one play from their
answers, and the play is scored with GNU Backgammon's 2-ply equity loss for that position.
Rules:

  single      one model's own choice (the baseline).
  confidence  the member whose stated probability for its choice is highest.
  calibrated  the member whose choice is most likely correct, after mapping each model's
              stated probability to its observed accuracy (isotonic regression).
  exp-loss    the member whose choice has the lowest expected equity loss, mapped the same way.
  average     the play with the highest probability summed over the members.
  oracle      the member choice with the smallest loss: the ceiling for any rule.

Calibrated rules are cross-fitted: positions are split into folds, and each fold is scored with
mappings fitted on the other folds only. Error rate = mean loss x 500; correct = loss < 0.001.
Intervals are 95% bootstrap intervals over positions for the difference from the best single
model, paired on the same positions. Standard library only.
"""

import argparse
import itertools
import json
import random
import sqlite3
from collections import defaultdict

CORRECT = 0.001


def load(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    loss = defaultdict(dict)
    for pid, play, l in db.execute("SELECT position_id, play, loss FROM equities"):
        loss[pid][play] = l
    answers = defaultdict(dict)
    for pid, model, choice, probs in db.execute(
            "SELECT position_id, model, choice, probabilities FROM answers WHERE error IS NULL"):
        answers[pid][model] = (choice, json.loads(probs))
    models = sorted({m for a in answers.values() for m in a})
    # Only positions every model answered and the engine scored, so all teams are compared on
    # exactly the same positions.
    pids = sorted(p for p in answers if p in loss and len(answers[p]) == len(models))
    return models, pids, answers, loss


def isotonic(xs, ys, increasing=True):
    """Pool-adjacent-violators fit; returns a step function x -> fitted y."""
    pts = sorted(zip(xs, ys))
    blocks = []  # [sum_y, count, max_x]
    for x, y in pts:
        blocks.append([y, 1, x])
        while len(blocks) > 1:
            a, b = blocks[-2], blocks[-1]
            ma, mb = a[0] / a[1], b[0] / b[1]
            if (ma > mb) if increasing else (ma < mb):
                blocks[-2:] = [[a[0] + b[0], a[1] + b[1], b[2]]]
            else:
                break
    edges = [(b[2], b[0] / b[1]) for b in blocks]

    def f(x):
        for edge, value in edges:
            if x <= edge:
                return value
        return edges[-1][1]
    return f


def fit(models, pids, answers, loss):
    """Per model: p(choice) -> P(correct), and p(choice) -> expected loss."""
    maps = {}
    for m in models:
        ps = [answers[p][m][1][answers[p][m][0]] for p in pids]
        losses = [loss[p][answers[p][m][0]] for p in pids]
        maps[m] = (isotonic(ps, [l < CORRECT for l in losses], True),
                   isotonic(ps, losses, False))
    return maps


def pick(rule, team, pid, answers, maps):
    a = {m: answers[pid][m] for m in team}
    conf = {m: c[1][c[0]] for m, c in a.items()}
    if rule == "confidence":
        return a[max(team, key=lambda m: conf[m])][0]
    if rule == "calibrated":
        return a[max(team, key=lambda m: maps[m][0](conf[m]))][0]
    if rule == "exp-loss":
        return a[min(team, key=lambda m: maps[m][1](conf[m]))][0]
    if rule == "average":
        total = defaultdict(float)
        for _, probs in a.values():
            for play, p in probs.items():
                total[play] += p
        return max(total, key=total.get)
    raise ValueError(rule)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="replay.db")
    ap.add_argument("--folds", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--boot", type=int, default=2000)
    args = ap.parse_args()
    models, pids, answers, loss = load(args.db)
    print(f"{len(pids)} positions answered by all {len(models)} models\n")
    rng = random.Random(args.seed)
    order = pids[:]
    rng.shuffle(order)
    folds = [order[i::args.folds] for i in range(args.folds)]
    maps_for = {}
    for i, fold in enumerate(folds):
        train = [p for j, f in enumerate(folds) if j != i for p in f]
        m = fit(models, train, answers, loss)
        for p in fold:
            maps_for[p] = m

    def losses(rule, team):
        if rule == "single":
            return [loss[p][answers[p][team[0]][0]] for p in pids]
        if rule == "oracle":
            return [min(loss[p][answers[p][m][0]] for m in team) for p in pids]
        return [loss[p][pick(rule, team, p, answers, maps_for[p])] for p in pids]

    def summary(ls):
        return 500 * sum(ls) / len(ls), sum(l < CORRECT for l in ls) / len(ls)

    singles = {m: losses("single", [m]) for m in models}
    best_single = min(models, key=lambda m: sum(singles[m]))
    base = singles[best_single]

    def interval(ls):
        n = len(ls)
        diffs = []
        for _ in range(args.boot):
            idx = [rng.randrange(n) for _ in range(n)]
            diffs.append(500 * sum(ls[i] - base[i] for i in idx) / n)
        diffs.sort()
        return diffs[int(.025 * len(diffs))], diffs[int(.975 * len(diffs))]

    print(f"{'team / rule':58} {'error rate':>10} {'correct':>8}  vs {best_single} (95%)")
    for m in sorted(models, key=lambda m: sum(singles[m])):
        er, acc = summary(singles[m])
        print(f"{'single: ' + m:58} {er:10.1f} {acc:8.1%}")
    print()
    rules = ["confidence", "calibrated", "exp-loss", "average", "oracle"]
    for rule in rules:
        ls = losses(rule, models)
        er, acc = summary(ls)
        lo, hi = interval(ls)
        print(f"{f'all {len(models)}: ' + rule:58} {er:10.1f} {acc:8.1%}  {er - 500 * sum(base) / len(base):+6.1f} [{lo:+.1f}, {hi:+.1f}]")
    print("\nBest formations by rule (all subsets of 2 or more models):")
    for rule in ["calibrated", "exp-loss", "average"]:
        scored = []
        for k in range(2, len(models) + 1):
            for team in itertools.combinations(models, k):
                scored.append((sum(losses(rule, list(team))), team))
        scored.sort()
        for total, team in scored[:3]:
            ls = losses(rule, list(team))
            er, acc = summary(ls)
            lo, hi = interval(ls)
            print(f"  {rule:10} {er:6.1f} {acc:6.1%}  {er - 500 * sum(base) / len(base):+6.1f} [{lo:+.1f}, {hi:+.1f}]  "
                  + " + ".join(team))


if __name__ == "__main__":
    main()
