#!/usr/bin/env python3
"""Close choices, stage B: scoring by Method spec 2026-10-24 §9.9 (B4) with §9.12-9.13.

    python3 tools/site/close_choices_b_score.py RUN_DB POSITIONS OUT_JSON

RUN_DB holds `predictions` (jevgammon predict) and `answers` (jevgammon ask --repeats 5) of the stage B run; POSITIONS is
the frozen v2 file. Per setup and position:
- valid: the prediction is valid (a feature list, possibly empty) and all five play answers are valid (no error, not
  invalid); otherwise the position is excluded, with its reasons;
- observed set O: the features (hitting, points, race, prime; §9.5, read from the option text the model was shown) that
  differ between any two of the five chosen plays; predicted set P: the prediction's features;
- primary score: 1 if P = O; secondary: |P ∩ O| / |P ∪ O|, 1 when both are empty, 0 when exactly one is;
- baseline: the predictions shuffled across the setup's scored positions of the same phase, 1,000 seeded permutations
  (analysis.boot), scored the same way; reported: observed mean, baseline mean, its 2.5-97.5 percentiles and the share of
  shuffles scoring at least the observed mean;
- the two empty-O cases apart: (a) the same play in all five answers, (b) the play changed but the features are equal.
"""

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE.parent / "v3"))

import analysis as A  # noqa: E402
import close_choices as CC  # noqa: E402
from describe import describe_with_shots  # noqa: E402
from rules import from_json, legal_plays  # noqa: E402

FEATURES = ["hitting", "points", "race", "prime"]
REPEATS = 5


def play_features(row: dict) -> list[dict]:
    pos = from_json(row["position"], row["side"])
    plays = legal_plays(pos, *row["dice"])
    if [n for n, _ in plays] != row["legal_plays"]:
        raise SystemExit(f"{row['id']}: legal plays differ from the stored ones")
    out = []
    for play in plays:
        text, shots = describe_with_shots(pos, play)
        f = CC.features_of(text)
        out.append(dict(hitting=shots, points=f["points"], race=f["race"], prime=f["prime"]))
    return out


def scores(P: frozenset, O: frozenset) -> tuple[int, float]:
    exact = int(P == O)
    if not P and not O:
        return exact, 1.0
    if not P or not O:
        return exact, 0.0
    return exact, len(P & O) / len(P | O)


def main():
    run_db, positions_path, out_path = sys.argv[1:4]
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(positions_path)}
    feats = {pid: play_features(r) for pid, r in rows.items()}
    db = sqlite3.connect(f"file:{run_db}?mode=ro", uri=True)
    preds = defaultdict(dict)
    for setup, pid, features, invalid, reason, error in db.execute(
            "SELECT setup, position_id, features, invalid, invalid_reason, error FROM predictions"):
        preds[setup][pid] = dict(features=None if features is None else frozenset(json.loads(features)),
                                 invalid=invalid, reason=reason, error=error)
    plays = defaultdict(lambda: defaultdict(dict))
    for setup, pid, rep, chosen, invalid, error in db.execute(
            "SELECT setup, position_id, repeat, chosen_index, invalid, error FROM answers"):
        plays[setup][pid][rep] = dict(chosen=chosen, invalid=invalid, error=error)
    report = {}
    for setup in sorted(set(preds) | set(plays)):
        excluded, scored = defaultdict(list), []
        for pid, row in rows.items():
            pr = preds[setup].get(pid)
            reasons = []
            if pr is None:
                reasons.append("prediction not asked")
            elif pr["error"]:
                reasons.append("prediction failed")
            elif pr["invalid"]:
                reasons.append(f"prediction invalid ({pr['reason']})")
            answers = plays[setup].get(pid, {})
            for rep in range(1, REPEATS + 1):
                a = answers.get(rep)
                if a is None:
                    reasons.append(f"play {rep} not asked")
                elif a["error"]:
                    reasons.append("play failed")
                elif a["invalid"]:
                    reasons.append("play invalid")
            if reasons:
                for r in sorted(set(reasons)):
                    excluded[r].append(pid)
                continue
            chosen = [answers[r]["chosen"] for r in range(1, REPEATS + 1)]
            fs = [feats[pid][c] for c in chosen]
            O = frozenset(f for f in FEATURES if len({repr(x[f]) for x in fs}) > 1)
            P = pr["features"]
            ex, ov = scores(P, O)
            scored.append(dict(id=pid, phase=row["phase"], P=P, O=O, exact=ex, overlap=ov,
                               distinct_plays=len(set(chosen)), same_play=len(set(chosen)) == 1))
        n = len(scored)
        out = dict(positions=len(rows), scored=n,
                   excluded={k: dict(n=len(v), ids=sorted(v)) for k, v in sorted(excluded.items())},
                   excluded_positions=len({p for v in excluded.values() for p in v}))
        if n:
            exact = np.array([s["exact"] for s in scored], float)
            overlap = np.array([s["overlap"] for s in scored])
            by_phase = defaultdict(list)
            for i, s in enumerate(scored):
                by_phase[s["phase"]].append(i)
            R = CC.CC["stage_b"]["baseline_shuffles"]
            rng = np.random.default_rng(A.boot(f"close-choices-b/{setup}/baseline"))
            Ps = [s["P"] for s in scored]
            Os = [s["O"] for s in scored]
            base_e, base_o = np.zeros(R), np.zeros(R)
            for r in range(R):
                perm = list(range(n))
                for idx in by_phase.values():
                    shuffled = rng.permutation(idx)
                    for a, b in zip(idx, shuffled):
                        perm[a] = int(b)
                sc = [scores(Ps[perm[i]], Os[i]) for i in range(n)]
                base_e[r] = np.mean([e for e, _ in sc])
                base_o[r] = np.mean([o for _, o in sc])

            def summary(obs, base):
                return dict(observed=float(obs.mean()), baseline_mean=float(base.mean()),
                            baseline_lo=float(np.percentile(base, 2.5)), baseline_hi=float(np.percentile(base, 97.5)),
                            share_baseline_at_least_observed=float((base >= obs.mean() - 1e-12).mean()))
            empty_O = [s for s in scored if not s["O"]]
            out.update(
                primary_exact=summary(exact, base_e), secondary_overlap=summary(overlap, base_o),
                exact_n=int(exact.sum()),
                same_play=sum(s["same_play"] for s in scored),
                changed_same_features=sum(1 for s in empty_O if not s["same_play"]),
                observed_nonempty=n - len(empty_O),
                deterministic=all(s["same_play"] for s in scored),
                distinct_plays=dict(sorted(Counter(s["distinct_plays"] for s in scored).items())),
                predicted_sets=dict(Counter(",".join(sorted(s["P"])) or "none" for s in scored).most_common()),
                observed_sets=dict(Counter(",".join(sorted(s["O"])) or "none" for s in scored).most_common()),
                predicted_feature_share={f: sum(f in s["P"] for s in scored) / n for f in FEATURES},
                observed_feature_share={f: sum(f in s["O"] for s in scored) / n for f in FEATURES},
                predicted_size_mean=float(np.mean([len(s["P"]) for s in scored])),
                by_phase={ph: dict(scored=len(ix), exact=int(sum(scored[i]["exact"] for i in ix)),
                                   same_play=sum(scored[i]["same_play"] for i in ix)) for ph, ix in by_phase.items()},
                positions_scored=[dict(id=s["id"], phase=s["phase"], P=sorted(s["P"]), O=sorted(s["O"]),
                                       distinct_plays=s["distinct_plays"]) for s in scored])
        report[setup] = out
    Path(out_path).write_text(json.dumps(report, indent=1))
    for setup, o in report.items():
        print(setup, {k: o[k] for k in ("scored", "excluded_positions")},
              {k: (round(o[k]["observed"], 3), round(o[k]["baseline_mean"], 3)) for k in ("primary_exact", "secondary_overlap") if k in o})


if __name__ == "__main__":
    main()
