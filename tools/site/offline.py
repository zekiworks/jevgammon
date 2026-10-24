"""Offline analyses of the reviewed brief of 24 Oct 2026, by the Method specification fixed before computing
(content/method-spec-2026-10-24.md, values in content/analysis_2026-10-24.json):

    §1  probability support per setup (content/probability_audit.json.gz, written by prob_audit.py)
    §3  5A re-read risk call: "re-read from the model's probabilities, not played"
    §4  5B calibration as shipped and after a cross-fitted Platt refit (two events, kept apart)
    §5  5C minimum bar, then cheapest
    §6  5D confidence distributions
    §7  the Safest program of League 1

Every split, fold and resample uses the league's block map: a block is a (match, round), the two games with seats
swapped and the same dice (analysis.load_leagues sets d["block"]).
"""

import gzip
import json
import math
from collections import Counter, defaultdict

import numpy as np

import analysis as A
from common import CONTENT, SPEC, THRESHOLDS as T

AUDIT_FILE = CONTENT / "probability_audit.json.gz"
REREAD_LABEL = "re-read from the model's probabilities, not played"
STATUSES = ["complete", "sparse", "unverified", "no_raw", "grouped", "no_probabilities", "invalid", "not_audited"]
MAIN = T["risk_margin"]
_Z = np.vectorize(A._Z, otypes=[float])


def load_audit() -> dict[int, str]:
    if not AUDIT_FILE.exists():
        return {}
    return {int(k): v for k, v in json.loads(gzip.decompress(AUDIT_FILE.read_bytes()))["statuses"].items()}


def rng_for(label: str) -> np.random.Generator:
    return np.random.default_rng(A.boot(label))


# --- Thresholds -----------------------------------------------------------------------------------------------

THRESHOLDS = [math.inf if t == "always safe" else float(t) for t in SPEC["reread_thresholds"]]
LABELS = ["always safe" if math.isinf(t) else f"{t:.2f}" for t in THRESHOLDS]
# The tie rule: nearest 0.5, then the smaller t; "always safe" is farthest from 0.5.
PREFERENCE = sorted(range(len(THRESHOLDS)), key=lambda k: (abs(THRESHOLDS[k] - 0.5), THRESHOLDS[k]))


def pick(J: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """Per split (rows of J: splits × thresholds), the chosen threshold index; -1 where the split has no fit."""
    best = np.where(ok, J.max(axis=1), -np.inf)
    out = np.full(len(J), -1)
    for k in PREFERENCE[::-1]:  # the last assignment wins: the most preferred among the ties
        hit = ok & (J[:, k] >= best - SPEC["reread_tie_tolerance"])
        out[hit] = k
    return out


# --- Per-decision arrays ----------------------------------------------------------------------------------------

def eligible(d: dict, audit: dict) -> str:
    if d["invalid"]:
        return "invalid"
    if d["id"] not in audit:
        return "not_audited"
    s = audit[d["id"]]
    if s == "complete" and (not d["scored"] or d.get("pvec") is None or any(x is None for x in d["pvec"])):
        return "not_scored"
    return s


def reread_row(d: dict) -> dict:
    """What the re-read needs from one complete record (main margin)."""
    shots, losses, ch = d["shots"], d["losses"], d["chosen"]
    cls, call, _, _ = A.play_call(shots, losses, ch, MAIN)
    p = d["pvec"]
    total = sum(p)
    row = dict(block=d["block"], cls=cls, right_ap=call in ("right_risk", "right_safety"), loss_ap=d["loss"],
               call_ap=call, p=d["p"], best=d["loss"] < T["best_play_loss_below"])
    if cls == "none":
        return row
    least = min(shots)
    key = lambda j: (p[j], -d["rank"][j])
    risky = max((j for j, s in enumerate(shots) if s > least), key=key)
    safe = max((j for j, s in enumerate(shots) if s == least), key=key)
    row.update(prisk=sum(p[j] for j, s in enumerate(shots) if s > least) / total if total > 0 else 0.0,
               right_r=A.play_call(shots, losses, risky, MAIN)[1] == "right_risk", loss_r=losses[risky],
               right_s=A.play_call(shots, losses, safe, MAIN)[1] == "right_safety", loss_s=losses[safe])
    return row


class Blocks:
    """The league's block index and its 300 fixed splits (one map for every setup of the league)."""

    def __init__(self, dataset: str, decisions: list[dict]):
        self.ids = sorted({d["block"] for d in decisions})
        self.index = {b: i for i, b in enumerate(self.ids)}
        B = len(self.ids)
        rng = rng_for(f"offline/{dataset}/splits")
        self.train = np.zeros((SPEC["splits"], B))
        for s in range(SPEC["splits"]):
            self.train[s, rng.permutation(B)[: B // 2]] = 1.0
        self.test = 1.0 - self.train
        self.dataset = dataset

    def replicate(self, r: int) -> tuple[np.ndarray, np.ndarray]:
        """Bootstrap replicate r: the block weights and its splits (train and test weights, splits × blocks)."""
        rng = rng_for(f"offline/{self.dataset}/boot/{r}")
        B = len(self.ids)
        w = np.bincount(rng.integers(0, B, B), minlength=B).astype(float)
        drawn = np.flatnonzero(w)
        n = SPEC["bootstrap_splits_per_replicate"]
        tr = np.zeros((n, B))
        for s in range(n):
            tr[s, drawn[rng.permutation(len(drawn))[: len(drawn) // 2]]] = 1.0
        return tr * w, (1.0 - tr) * w

    def sums(self, blocks: list[str], values: np.ndarray) -> np.ndarray:
        """Per-block sums of per-record values (records × columns) → blocks × columns."""
        out = np.zeros((len(self.ids),) + values.shape[1:])
        np.add.at(out, np.array([self.index[b] for b in blocks], dtype=int), values)
        return out


def judge(rr, rp, rs, sp):
    """Risk judgement with N/A (nan) where a class is absent."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((rp > 0) & (sp > 0), 50 * (rr / rp + rs / sp), np.nan)


# --- 5A ------------------------------------------------------------------------------------------------------

def reread_arrays(rows: list[dict], blocks: Blocks) -> dict:
    """Per-block sums for every threshold: right risks / Risk pays / right safety / Safety pays and losses."""
    K = len(THRESHOLDS)
    th = np.array(THRESHOLDS)
    n = len(rows)
    cls = np.array([r["cls"] for r in rows])
    isR, isS = (cls == "risk").astype(float), (cls == "safety").astype(float)
    prisk = np.array([r.get("prisk", 0.0) for r in rows])
    risky = prisk[:, None] >= th[None, :]
    trade = cls != "none"
    get = lambda k, dflt: np.array([r.get(k, dflt) for r in rows], dtype=float)
    right = np.where(risky, get("right_r", 0)[:, None], get("right_s", 0)[:, None]) * trade[:, None]
    loss = np.where(trade[:, None], np.where(risky, get("loss_r", 0)[:, None], get("loss_s", 0)[:, None]),
                    get("loss_ap", 0)[:, None])
    rap = get("right_ap", 0) * trade
    values = np.concatenate([right * isR[:, None], right * isS[:, None], loss,
                             np.stack([isR, isS, rap * isR, rap * isS, get("loss_ap", 0), np.ones(n)], axis=1)], axis=1)
    S = blocks.sums([r["block"] for r in rows], values)
    return dict(RR=S[:, :K], SR=S[:, K:2 * K], L=S[:, 2 * K:3 * K], R=S[:, 3 * K], Sf=S[:, 3 * K + 1],
                RRap=S[:, 3 * K + 2], SRap=S[:, 3 * K + 3], Lap=S[:, 3 * K + 4], n=S[:, 3 * K + 5])


def reread_run(a: dict, train: np.ndarray, test: np.ndarray) -> dict:
    """One set of splits: the chosen threshold per split and the test-half results (nan where N/A)."""
    J = judge(train @ a["RR"], (train @ a["R"])[:, None], train @ a["SR"], (train @ a["Sf"])[:, None])
    ok = ~np.isnan(J).any(axis=1)
    k = pick(np.nan_to_num(J, nan=-np.inf), ok)
    s = np.arange(len(k))
    kk = np.where(k >= 0, k, 0)
    tR, tS, tn = test @ a["R"], test @ a["Sf"], test @ a["n"]
    j_rr = judge((test @ a["RR"])[s, kk], tR, (test @ a["SR"])[s, kk], tS)
    j_ap = judge(test @ a["RRap"], tR, test @ a["SRap"], tS)
    with np.errstate(divide="ignore", invalid="ignore"):
        pr_rr = np.where(tn > 0, T["equity_scale"] * (test @ a["L"])[s, kk] / tn, np.nan)
        pr_ap = np.where(tn > 0, T["equity_scale"] * (test @ a["Lap"]) / tn, np.nan)
    fit = k >= 0
    return dict(k=k, fit=fit, j_rr=np.where(fit, j_rr, np.nan), j_ap=np.where(fit, j_ap, np.nan),
                pr_rr=np.where(fit, pr_rr, np.nan), pr_ap=np.where(fit, pr_ap, np.nan), test_n=tn)


def _mean(x) -> float | None:
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(x.mean()) if len(x) else None


def _pct(x, q) -> float | None:
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(np.percentile(x, q)) if len(x) else None


# Hypothesis predictor, from the training half's decisions (all valid scored decisions of the setup).

def predictor_arrays(decs: list[dict], blocks: Blocks) -> np.ndarray:
    rows, keys = [], []
    for d in decs:
        if d["invalid"] or not d["scored"]:
            continue
        cls, call, _, _ = A.play_call(d["shots"], d["losses"], d["chosen"], MAIN)
        if cls == "none":
            continue
        rows.append([call in ("right_risk", "wrong_risk"), cls == "risk", call == "needless", cls == "safety",
                     call == "missed", d["loss"] * (call == "needless"), d["loss"] * (call == "missed")])
        keys.append(d["block"])
    return blocks.sums(keys, np.array(rows, float).reshape(-1, 7))


def predictor(P: np.ndarray, train: np.ndarray) -> np.ndarray:
    """X = d′ × (c − c*) per split; nan where c* is undefined (rules 1-4) or d′ is below the split near-zero bound."""
    t, R, N, S, M, LN, LM = (train @ P).T
    a, b = SPEC["loglinear_add"]
    with np.errstate(divide="ignore", invalid="ignore"):
        zh, zf = _Z(np.clip((t + a) / (R + b), 1e-12, 1 - 1e-12)), _Z(np.clip((N + a) / (S + b), 1e-12, 1 - 1e-12))
        d, c = zh - zf, -(zh + zf) / 2
        beta = (S / R) * ((LN / N) / (LM / M))
        cs = np.log(beta) / d
    ok = (R > 0) & (S > 0) & (N > 0) & (M > 0) & (LN > 0) & (LM > 0) & np.isfinite(beta) & (beta > 0) \
        & (d >= SPEC["split_dprime_near_zero_below"])
    return np.where(ok, d * (c - cs), np.nan)


def spearman(x, y) -> float | None:
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = ~(np.isnan(x) | np.isnan(y))
    x, y = x[keep], y[keep]
    if len(x) < 3:
        return None

    def avg_rank(v):
        order = np.argsort(v, kind="stable")
        r = np.empty(len(v))
        sv = v[order]
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and sv[j + 1] == sv[i]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = avg_rank(x), avg_rank(y)
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


# --- 5B ------------------------------------------------------------------------------------------------------

def platt_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    """Logistic regression of y on x (Newton–Raphson); None for one class only or no convergence."""
    if y.min() == y.max():
        return None
    a = b = 0.0
    X = np.stack([np.ones_like(x), x], axis=1)
    for _ in range(SPEC["platt_max_steps"]):
        q = 1 / (1 + np.exp(-(a + b * x)))
        g = X.T @ (y - q)
        H = (X * (q * (1 - q))[:, None]).T @ X
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return None
        a, b = a + step[0], b + step[1]
        if not (math.isfinite(a) and math.isfinite(b)):
            return None
        if np.abs(step).max() < SPEC["platt_tolerance"]:
            return a, b
    return None


def logit(p: np.ndarray) -> np.ndarray:
    c = SPEC["platt_clip"]
    p = np.clip(p, c, 1 - c)
    return np.log(p / (1 - p))


def reliability(p: np.ndarray, y: np.ndarray) -> list[dict]:
    nb = SPEC["reliability_bins"]
    idx = np.minimum((p * nb).astype(int), nb - 1)
    out = []
    for i in range(nb):
        m = idx == i
        out.append(dict(lo=i / nb, hi=(i + 1) / nb, n=int(m.sum()), mean_p=float(p[m].mean()) if m.any() else None,
                        observed=float(y[m].mean()) if m.any() else None))
    return out


def calibrate(p: np.ndarray, y: np.ndarray, blocks: list[str], folds: dict[str, int]) -> dict:
    """Before and after a Platt refit cross-fitted over the league's block folds, on the same records."""
    f = np.array([folds[b] for b in blocks])
    q = np.full(len(p), np.nan)
    failed = 0
    for k in range(SPEC["platt_folds"]):
        held = f == k
        if not held.any():
            continue
        fit = platt_fit(logit(p[~held]), y[~held])
        if fit is None:
            failed += 1
            continue
        q[held] = 1 / (1 + np.exp(-(fit[0] + fit[1] * logit(p[held]))))
    keep = ~np.isnan(q)
    out = dict(records=int(len(p)), paired=int(keep.sum()), left_out=int((~keep).sum()), failed_folds=failed,
               too_few=bool(keep.sum() < T["min_decisions_per_cell"]), event_rate=float(y.mean()) if len(y) else None)
    if keep.any():
        pk, qk, yk = p[keep], q[keep], y[keep]
        out.update(brier_before=float(((pk - yk) ** 2).mean()), brier_after=float(((qk - yk) ** 2).mean()),
                   bins_before=reliability(pk, yk), bins_after=reliability(qk, yk))
    return out


# --- 5D ------------------------------------------------------------------------------------------------------

def histogram(p: list[float]) -> dict:
    nb = SPEC["reliability_bins"]
    a = np.asarray(p, float)
    counts = np.bincount(np.minimum((a * nb).astype(int), nb - 1), minlength=nb) if len(a) else np.zeros(nb, int)
    return dict(n=len(a), too_few=len(a) < T["min_decisions_per_cell"], counts=[int(c) for c in counts],
                median=float(np.median(a)) if len(a) else None, mean=float(a.mean()) if len(a) else None)


# --- The league ------------------------------------------------------------------------------------------------

def league(lg: dict, meta: dict, audit: dict) -> dict:
    """All offline analyses of one league (lg = analysis.load_leagues entry; meta = setups.json by name)."""
    ds = lg["dataset"]
    decs = lg["decisions"]
    blocks = Blocks(ds, decs)
    by = defaultdict(list)
    for d in decs:
        by[d["setup"]].append(d)
    support, rows = {}, {}
    for n, ds_ in by.items():
        c = Counter(eligible(d, audit) for d in ds_)
        support[n] = {s: c.get(s, 0) for s in STATUSES + ["not_scored"] if c.get(s, 0) or s in STATUSES}
        rows[n] = [reread_row(d) for d in ds_ if eligible(d, audit) == "complete"]
    out = dict(spec_fixed_on=SPEC["fixed_on"], blocks=len(blocks.ids), splits=SPEC["splits"], label=REREAD_LABEL,
               support=support, thresholds=LABELS)
    # 5A, with the hypothesis predictor.
    reread, X, Y, boot_xy = {}, {}, {}, defaultdict(dict)
    arrays = {n: reread_arrays(r, blocks) for n, r in rows.items() if len(r) >= T["min_decisions_per_cell"]}
    preds = {n: predictor_arrays(by[n], blocks) for n in arrays}
    for n, a in arrays.items():
        r = reread_run(a, blocks.train, blocks.test)
        dj, dp = r["j_rr"] - r["j_ap"], r["pr_rr"] - r["pr_ap"]
        chosen = Counter(LABELS[k] for k in r["k"] if k >= 0)
        x = predictor(preds[n], blocks.train)
        defined = int((~np.isnan(x)).sum())
        X[n] = _mean(x) if defined >= SPEC["hypothesis_min_defined_splits"] else None
        Y[n] = _mean(dj)
        trade = sum(1 for z in rows[n] if z["cls"] != "none")
        reread[n] = dict(records=len(rows[n]), trade_off=trade, no_fit=int((~r["fit"]).sum()),
                         test_judgement_na=int((r["fit"] & np.isnan(r["j_ap"])).sum()),
                         judgement_played=_mean(r["j_ap"]), judgement_reread=_mean(r["j_rr"]), judgement_diff=_mean(dj),
                         judgement_diff_p5=_pct(dj, SPEC["stability_percentiles"][0]),
                         judgement_diff_p95=_pct(dj, SPEC["stability_percentiles"][1]),
                         pr_played=_mean(r["pr_ap"]), pr_reread=_mean(r["pr_rr"]), pr_diff=_mean(dp),
                         pr_diff_p5=_pct(dp, SPEC["stability_percentiles"][0]),
                         pr_diff_p95=_pct(dp, SPEC["stability_percentiles"][1]),
                         test_records_mean=_mean(np.where(r["fit"], r["test_n"], np.nan)),
                         chosen=dict(sorted(chosen.items(), key=lambda kv: -kv[1])),
                         always_safe=chosen.get("always safe", 0), always_risky=chosen.get("0.00", 0),
                         predictor=X[n], predictor_splits=defined)
    for rep in range(SPEC["bootstrap_replicates"]):
        tr, te = blocks.replicate(rep)
        for n, a in arrays.items():
            r = reread_run(a, tr, te)
            x = predictor(preds[n], tr)
            boot_xy[n][rep] = (_mean(r["j_rr"] - r["j_ap"]), _mean(r["pr_rr"] - r["pr_ap"]),
                               _mean(x) if (~np.isnan(x)).sum() >= len(x) / 2 else None)
    q = [(1 - T["interval"]) / 2 * 100, (1 + T["interval"]) / 2 * 100]
    for n in arrays:
        dj = [v[0] for v in boot_xy[n].values() if v[0] is not None]
        dp = [v[1] for v in boot_xy[n].values() if v[1] is not None]
        reread[n].update(judgement_diff_lo=_pct(dj, q[0]), judgement_diff_hi=_pct(dj, q[1]),
                         pr_diff_lo=_pct(dp, q[0]), pr_diff_hi=_pct(dp, q[1]), replicates=len(dj))
    out["reread"] = reread
    out["reread_too_few"] = {n: len(r) for n, r in rows.items() if 0 < len(r) < T["min_decisions_per_cell"]}
    out["hypothesis"] = dict(X=X, Y=Y)
    # Per replicate (Y, X) for the pooled Spearman interval in build.py; not written to the data files.
    out["_boot"] = {n: {k: (v[0], v[2]) for k, v in b.items()} for n, b in boot_xy.items()}
    # 5B: block folds for the league.
    rng = rng_for(f"offline/{ds}/folds")
    perm = rng.permutation(len(blocks.ids))
    folds = {blocks.ids[i]: j % SPEC["platt_folds"] for j, i in enumerate(perm)}
    calib = {}
    for n, r in rows.items():
        if not r:
            continue
        p1 = np.array([z["p"] for z in r], float)
        y1 = np.array([z["best"] for z in r], float)
        tr_ = [z for z in r if z["cls"] != "none"]
        calib[n] = dict(chosen=calibrate(p1, y1, [z["block"] for z in r], folds))
        if tr_:
            calib[n]["risk_class"] = calibrate(np.array([z["prisk"] for z in tr_], float),
                                               np.array([z["cls"] == "risk" for z in tr_], float),
                                               [z["block"] for z in tr_], folds)
    out["calibration"] = calib
    # 5D.
    dist = {}
    for n, r in rows.items():
        if not r:
            continue
        taken = [z for z in r if z["call_ap"] in ("right_risk", "wrong_risk", "needless")]
        dist[n] = dict(right=histogram([z["p"] for z in r if z["best"]]),
                       wrong=histogram([z["p"] for z in r if not z["best"]]),
                       right_risk=histogram([z["p"] for z in taken if z["call_ap"] == "right_risk"]),
                       bad_risk=histogram([z["p"] for z in taken if z["call_ap"] != "right_risk"]))
    out["distributions"] = dist
    out["cheapest"] = cheapest(lg, by, meta, blocks)
    if "Safest" in by:
        out["safest"] = safest(by["Safest"])
    return out


def hypothesis(leagues: list[tuple[str, dict]], boots: dict) -> dict:
    """The recorded hypothesis (spec §3): Spearman ρ between X (training d′ × (c − c*)) and Y (held-out change in risk
    judgement) across setups, all leagues pooled; 95% interval from the same bootstrap replicates."""
    xs, ys, used, left = [], [], [], []
    per = {}
    for ds, off in leagues:
        h = off["hypothesis"]
        lx, ly = [], []
        for n in sorted(h["X"]):
            if h["X"][n] is None or h["Y"][n] is None:
                left.append(f"{n} ({ds})")
                continue
            xs.append(h["X"][n]), ys.append(h["Y"][n]), used.append((ds, n))
            lx.append(h["X"][n]), ly.append(h["Y"][n])
        per[ds] = dict(setups=len(lx), rho=spearman(lx, ly))
    rho = spearman(xs, ys)
    reps = []
    for r in range(SPEC["bootstrap_replicates"]):
        bx, by_ = [], []
        for ds, n in used:
            y, x = boots[ds][n][r]
            if x is not None and y is not None:
                bx.append(x), by_.append(y)
        reps.append(spearman(bx, by_))
    reps = [v for v in reps if v is not None]
    q = [(1 - T["interval"]) / 2 * 100, (1 + T["interval"]) / 2 * 100]
    lo, hi = (_pct(reps, q[0]), _pct(reps, q[1])) if reps else (None, None)
    if rho is None:
        verdict = "not testable: fewer than 3 setups with a defined predictor"
    elif rho > 0 and lo is not None and lo > 0:
        verdict = "supported"
    elif rho > 0:
        verdict = "inconclusive"
    else:
        verdict = "not supported"
    return dict(text="Gains will be largest for setups with high ability whose caution is well above the cost-derived "
                     "SDT reference.", setups=len(used), left_out=left, rho=rho, rho_lo=lo, rho_hi=hi,
                replicates=len(reps), verdict=verdict, per_league=per,
                points=[dict(dataset=ds, setup=n, x=x, y=y) for (ds, n), x, y in zip(used, xs, ys)])


# --- 5C ------------------------------------------------------------------------------------------------------

def cheapest(lg: dict, by: dict, meta: dict, blocks: Blocks) -> dict:
    names = sorted(n for n in by if (meta.get(n) or {}).get("model_type") != "program")
    cols = {}
    for n in names:
        vals, keys = [], []
        for d in by[n]:
            v = [0.0] * 9  # rr, rp, rs, sp, loss, scored, cost, priced, all
            v[8] = 1
            if d.get("cost") is not None:
                v[6], v[7] = d["cost"], 1
            if not d["invalid"] and d["scored"]:
                cls, call, _, _ = A.play_call(d["shots"], d["losses"], d["chosen"], MAIN)
                v[0], v[1] = call == "right_risk", cls == "risk"
                v[2], v[3] = call == "right_safety", cls == "safety"
                v[4], v[5] = d["loss"], 1
            vals.append(v)
            keys.append(d["block"])
        cols[n] = blocks.sums(keys, np.array(vals, float))
    jbar, pbar = SPEC["bar_judgement_at_least"], SPEC["bar_error_rate_at_most"]

    def measures(m, w):
        s = w @ m
        with np.errstate(divide="ignore", invalid="ignore"):
            j = judge(s[:, 0], s[:, 1], s[:, 2], s[:, 3])
            pr = np.where(s[:, 5] > 0, T["equity_scale"] * s[:, 4] / s[:, 5], np.nan)
            price = np.where((s[:, 8] > 0) & (s[:, 7] == s[:, 8]), 1000 * s[:, 6] / s[:, 8], np.nan)
        return j, pr, price

    train = {n: measures(cols[n], blocks.train) for n in names}
    test = {n: measures(cols[n], blocks.test) for n in names}
    per = {n: dict(qualified=0, qualified_unpriced=0, chosen=0, cleared=0, test_na=0) for n in names}
    none_q = none_priced = 0
    for s in range(SPEC["splits"]):
        q = [n for n in names if train[n][0][s] >= jbar and train[n][1][s] <= pbar]
        for n in q:
            per[n]["qualified"] += 1
            if np.isnan(train[n][2][s]):
                per[n]["qualified_unpriced"] += 1
        priced = [n for n in q if not np.isnan(train[n][2][s])]
        if not q:
            none_q += 1
            continue
        if not priced:
            none_priced += 1
            continue
        c = min(priced, key=lambda n: (train[n][2][s], train[n][1][s], n))
        per[c]["chosen"] += 1
        j, pr = test[c][0][s], test[c][1][s]
        if np.isnan(j):
            per[c]["test_na"] += 1
        elif j >= jbar and pr <= pbar:
            per[c]["cleared"] += 1
    cov = {}
    for n in names:
        a = len(by[n])
        cov[n] = dict(decisions=a, priced=sum(1 for d in by[n] if d.get("cost") is not None))
    return dict(bar_judgement=jbar, bar_error_rate=pbar, splits=SPEC["splits"], no_qualifier=none_q,
                no_priced_qualifier=none_priced, setups=per, coverage=cov,
                chosen_splits=sum(v["chosen"] for v in per.values()),
                cleared_splits=sum(v["cleared"] for v in per.values()))


# --- §7 ------------------------------------------------------------------------------------------------------

def safest(decs: list[dict]) -> dict:
    v = [d for d in decs if not d["invalid"] and d["scored"]]
    mins = best_safe = rs = 0
    rs_loss = 0.0
    for d in v:
        least = min(d["shots"])
        safe = [j for j, s in enumerate(d["shots"]) if s == least]
        mins += d["shots"][d["chosen"]] == least
        best_safe += d["losses"][d["chosen"]] <= min(d["losses"][j] for j in safe) + 1e-12
        if A.play_call(d["shots"], d["losses"], d["chosen"], MAIN)[1] == "right_safety":
            rs += 1
            rs_loss += d["loss"]
    n = len(v)
    return dict(decisions=n, minimum_hitting_rolls=mins, best_safe_play=best_safe, right_safety=rs,
                right_safety_contribution=T["equity_scale"] * rs_loss / n if n else None,
                right_safety_conditional=T["equity_scale"] * rs_loss / rs if rs else None)
