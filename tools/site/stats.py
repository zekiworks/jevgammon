"""Statistics for the backgammon site (brief B9): bootstrap intervals and verdicts.

League decisions resample whole games (moves inside a game are not independent); shared and v1-set
positions resample positions. Paired comparisons resample the positions both setups answered. Every
interval uses the resample count and seed fixed in content/thresholds.json.
"""

import numpy as np


def _quantiles(stats: np.ndarray, level: float) -> tuple[float, float]:
    lo, hi = np.quantile(stats, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def ratio_interval(sums: list[float], counts: list[int], scale: float, resamples: int, seed: int,
                   level: float) -> tuple[float, float]:
    """Interval of scale x sum(sums) / sum(counts), resampling clusters (games or positions)."""
    s, c = np.asarray(sums, float), np.asarray(counts, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(resamples, len(s)))
    stats = scale * s[idx].sum(axis=1) / np.maximum(c[idx].sum(axis=1), 1)
    return _quantiles(stats, level)


def judgement_interval(rr: list[float], rp: list[float], rs: list[float], sp: list[float], resamples: int,
                       seed: int, level: float) -> tuple[float, float]:
    """Interval of risk judgement = 50 x (right risks / Risk pays + right safety / Safety pays), resampling games;
    a resample without one of the two classes is left out."""
    a, b, c, d = (np.asarray(x, float) for x in (rr, rp, rs, sp))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(resamples, len(a)))
    B, D = b[idx].sum(axis=1), d[idx].sum(axis=1)
    ok = (B > 0) & (D > 0)
    j = 50 * (a[idx].sum(axis=1)[ok] / B[ok] + c[idx].sum(axis=1)[ok] / D[ok])
    return _quantiles(j, level)


def paired_interval(diffs: list[float], scale: float, resamples: int, seed: int, level: float) -> tuple[float, float]:
    """Interval of scale x mean per-position difference, resampling positions."""
    d = np.asarray(diffs, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(resamples, len(d)))
    return _quantiles(scale * d[idx].mean(axis=1), level)


def verdict(lo: float, hi: float) -> str:
    """B9 verdict for an error difference (second minus first): lower error is better."""
    if hi < 0:
        return "High helps"
    if lo > 0:
        return "High hurts"
    return "No clear benefit"


def quantile(values: list[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, float), q))


def worst_mean(values: list[float], share: float) -> float:
    """Mean of the worst `share` of values (at least one)."""
    v = np.sort(np.asarray(values, float))[::-1]
    k = max(1, int(round(share * len(v))))
    return float(v[:k].mean())


def median(values: list[float]) -> float:
    return float(np.median(np.asarray(values, float)))
