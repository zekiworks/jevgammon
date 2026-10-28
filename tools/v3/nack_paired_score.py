"""Nackgammon paired test (Method spec 2026-10-24 §10): scoring of the answers. Plays no model.

    python3 tools/v3/nack_paired_score.py first-look              # §10.8 first look (main 200 pairs)
    python3 tools/v3/nack_paired_score.py report [--rollouts DB]  # everything, into positions/nack-paired/results/
    python3 tools/v3/nack_paired_score.py engine-candidates OUT.db CHOSEN.json   # §10.12 rollout candidates

Inputs: positions/nack-paired/{main,reserve,pairs,scores-2ply}.jsonl, the answers in smoke/nack-paired.db
(`jevgammon ask`), the roster leagues/nack-paired.json and freeze/nack-paired.json (engine-check pairs).

Rules (§10.8): PR = 500 × mean 2-ply loss. An invalid, failed, timed-out or never-stored answer scores the
position's Random error (mean loss over its legal plays; risk calls with weight 1/n per legal play); sensitivity:
(i) the worst legal play's loss, (ii) the pair left out for that setup. Intervals: paired bootstrap over pairs,
10,000 resamples, percentile, indices shared by every setup (numpy default_rng, seed = first 8 bytes of
h("bootstrap:<look>")). Bootstrap intervals are approximate.
"""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
from statistics import NormalDist

import numpy as np

SEED = "nack-paired-2026-10-27"
DIR = "positions/nack-paired"
DB = "smoke/nack-paired.db"
ROSTER = "leagues/nack-paired.json"
OUT = os.path.join(DIR, "results")
B = 10000
MARGIN = 0.001
PHASES = ("opening", "contact", "holding", "race", "bear-off")
YARDSTICKS = ["GNUbg weak", "Random"]
GROUP_OF_LEAGUE = {1: "decision models", 2: "workhorses", 3: "frontier"}
NOTE_E = ("Groups by original league (Method §10.14, amendment of 2026-10-27). It was written after the per-setup first "
          "looks and after six full-report calls on partial data had computed group results under the earlier group "
          "definitions; one returned those results into an agent's context. Whether a person saw them is not "
          "established. Nothing was published. See §10.14(e) and its correction (f) of 2026-10-28.")


def original_league_groups(names, db="v3.db"):
    """§10.14: group = the setup's original league (tools/league_web.py league_origins, read-only); none = no group."""
    sys.path.insert(0, "tools")
    import league_web
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    origin = {}
    for (lid,) in con.execute("SELECT id FROM leagues WHERE id IN (1, 2, 3)"):
        origin.update(league_web.league_origins(con, lid))
    groups = {g: [] for g in GROUP_OF_LEAGUE.values()}
    for n in names:
        if n in origin and origin[n] in GROUP_OF_LEAGUE:
            groups[GROUP_OF_LEAGUE[origin[n]]].append(n)
    return groups


GROUPS = {}  # §10.14: filled by Data from the original leagues
PRIMARY = [("group", "decision models", "workhorses"), ("group", "decision models", "frontier"),
           ("group", "workhorses", "frontier"),
           ("setup", "LFM2.5-24B-A2B (on)", "LFM2.5-24B-A2B (off)"),
           ("setup", "GPT-6.1 Sol (high)", "GPT-6.1 Sol (low)")]
M = 5


def h(text):
    return hashlib.sha256(f"{SEED}:{text}".encode()).hexdigest()


def rng_for(look):
    return np.random.default_rng(int(h("bootstrap:" + look)[:16], 16))


def jl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def play_call(shots, losses, i, margin=MARGIN):
    """analysis.play_call (as tools/v3/nack_paired.py)."""
    least = min(shots)
    if least == max(shots):
        return "none", None
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call


class Data:
    def __init__(self, db=DB, roster=ROSTER):
        self.rows = {r["id"]: r for r in jl(f"{DIR}/main.jsonl") + jl(f"{DIR}/reserve.jsonl")}
        self.pairs = jl(f"{DIR}/pairs.jsonl")
        self.main = [p for p in self.pairs if p["set"] == "main"]
        self.reserve = [p for p in self.pairs if p["set"] == "reserve"]
        self.scores = {}
        for s in jl(f"{DIR}/scores-2ply.jsonl"):
            plays = s["plays"]
            losses = [p["loss"] for p in plays]
            shots = [p["hitting_rolls"] for p in plays]
            n = len(plays)
            self.scores[s["id"]] = {
                "plays": {p["play"]: i for i, p in enumerate(plays)}, "loss": losses, "shots": shots,
                "equity": [p["equity"] for p in plays], "random": sum(losses) / n, "worst": max(losses),
                "calls": [play_call(shots, losses, i)[1] for i in range(n)]}
        with open(roster) as f:
            self.players = {p["name"]: p for p in json.load(f)["players"]}
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        self.answers = {}
        for r in con.execute("SELECT * FROM answers WHERE repeat = 1"):
            self.answers.setdefault(r["setup"], {})[r["position_id"]] = r
        self.setups = [s for s in self.players if s in self.answers]
        if not GROUPS:
            GROUPS.update(original_league_groups([s for s in self.setups if s not in YARDSTICKS]))

    def answered(self, setup, pairs):
        a = self.answers.get(setup, {})
        return all(p["nackgammon"] in a and p["standard"] in a for p in pairs)

    def outcome(self, setup, pid):
        """(loss, valid, call weights {call: w}) of a setup's answer at a position."""
        sc = self.scores[pid]
        if setup == "Random":
            n = len(sc["loss"])
            w = {}
            for c in sc["calls"]:
                w[c] = w.get(c, 0) + 1 / n
            return sc["random"], True, w
        r = self.answers.get(setup, {}).get(pid)
        if r is not None and r["error"] is None and not r["invalid"] and r["move"] in sc["plays"]:
            i = sc["plays"][r["move"]]
            return sc["loss"][i], True, {sc["calls"][i]: 1.0}
        n = len(sc["loss"])
        w = {}
        for c in sc["calls"]:
            w[c] = w.get(c, 0) + 1 / n
        return None, False, w

    def vectors(self, setup, pairs, rule="random"):
        """Per pair: nack loss, std loss (×500), mask (both valid, for rule 'drop'), invalid counts."""
        nk, st, ok = [], [], []
        bad = {"nackgammon": 0, "standard": 0}
        for p in pairs:
            vals = []
            good = True
            for side in ("nackgammon", "standard"):
                pid = p[side]
                loss, valid, _ = self.outcome(setup, pid)
                if not valid:
                    bad[side] += 1
                    good = False
                    loss = self.scores[pid]["worst"] if rule == "worst" else self.scores[pid]["random"]
                vals.append(500 * loss)
            nk.append(vals[0])
            st.append(vals[1])
            ok.append(good or rule != "drop")
        return np.array(nk), np.array(st), np.array(ok, dtype=float), bad


def boot_means(x, mask, idx):
    xs, ms = (x * mask)[idx].sum(axis=1), mask[idx].sum(axis=1)
    return xs / np.maximum(ms, 1e-12)


def q(a, level):
    lo, hi = np.quantile(a, [(1 - level) / 2, 1 - (1 - level) / 2])
    return [round(float(lo), 2), round(float(hi), 2)]


def r2(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 2)


def label(ci):
    lo, hi = ci
    if -5 <= lo and hi <= 5:
        return "kept"
    if lo > 0:
        return "worse"
    if hi < 0:
        return "better"
    return "unclear"


def extend(ci):
    lo, hi = ci
    return lo <= 0 <= hi and (lo <= -5 or hi >= 5)


def setup_look(d, setup, pairs, look, rule="random"):
    nk, st, m, bad = d.vectors(setup, pairs, rule)
    idx = rng_for(look).integers(0, len(pairs), size=(B, len(pairs)))
    dn, ds = boot_means(nk, m, idx), boot_means(st, m, idx)
    w = m.sum()
    sp, npr = float((st * m).sum() / w), float((nk * m).sum() / w)
    return {"pairs": int(w), "standard_pr": r2(sp), "nackgammon_pr": r2(npr), "drop": r2(npr - sp),
            "drop_975": q(dn - ds, 0.975), "drop_95": q(dn - ds, 0.95), "invalid": bad}, dn - ds, dn, ds


def first_look(d):
    out = {}
    for s in d.setups + ["Random"]:
        if s != "Random" and not d.answered(s, d.main):
            continue
        res, *_ = setup_look(d, s, d.main, "first")
        res["label_first"] = label(res["drop_975"])
        res["extend"] = extend(res["drop_975"]) and s != "Random"
        out[s] = res
    return out


def cost(d, setup, pids):
    """Mean cost per decision: billed (cost_usd), else API-equivalent at the roster price, else None."""
    a = d.answers.get(setup, {})
    price = (d.players.get(setup) or {}).get("price")
    billed, eq, n, secs, tin, tout = 0.0, 0.0, 0, [], [], []
    for pid in pids:
        r = a.get(pid)
        if r is None:
            continue
        n += 1
        if r["cost_usd"]:
            billed += r["cost_usd"]
        elif price:
            eq += ((r["input_tokens"] or 0) * price["input_per_mtok"] + (r["output_tokens"] or 0)
                   * price["output_per_mtok"]) / 1e6
        if r["request_ms"]:
            secs.append(r["request_ms"] / 1000)
        tin.append(r["input_tokens"] or 0)
        tout.append(r["output_tokens"] or 0)
    if not n:
        return {}
    return {"decisions": n, "billed_usd_per_decision": billed / n if billed else 0.0,
            "api_eq_usd_per_decision": eq / n if eq else 0.0, "billed_usd_total": round(billed, 4),
            "median_request_s": float(np.median(secs)) if secs else None,
            "tokens_in": float(np.mean(tin)), "tokens_out": float(np.mean(tout))}


def phase_table(d, setup, rule="random"):
    out = {}
    for ph in PHASES:
        pairs = [p for p in d.main if p["phase"] == ph]
        res, *_ = setup_look(d, setup, pairs, f"first:phase:{ph}", rule)
        out[ph] = {k: res[k] for k in ("pairs", "standard_pr", "nackgammon_pr", "drop", "drop_95")}
    nk, st, m, _ = d.vectors(setup, d.main, rule)
    op = np.array([p["phase"] == "opening" for p in d.main], dtype=float)
    idx = rng_for("first:opening-vs-rest").integers(0, len(d.main), size=(B, len(d.main)))
    a = boot_means(nk, m * op, idx) - boot_means(st, m * op, idx)
    b = boot_means(nk, m * (1 - op), idx) - boot_means(st, m * (1 - op), idx)
    w1, w0 = (m * op).sum(), (m * (1 - op)).sum()
    point = ((nk * m * op).sum() - (st * m * op).sum()) / w1 - ((nk * m * (1 - op)).sum() - (st * m * (1 - op)).sum()) / w0
    out["opening minus other phases"] = {"diff": r2(point), "ci_95": q(a - b, 0.95)}
    return out


def tag_table(d, setup):
    """Descriptive: PR per game-plan tag and set (tags are not matched; not a paired drop)."""
    out = {}
    for side in ("nackgammon", "standard"):
        for p in d.main:
            pid = p[side]
            tag = d.rows[pid]["tag"] or f"(none: {p['phase']})"
            loss, valid, _ = d.outcome(setup, pid)
            if not valid:
                loss = d.scores[pid]["random"]
            cell = out.setdefault(tag, {}).setdefault(side, [])
            cell.append(500 * loss)
    return {t: {s: {"n": len(v), "pr": r2(np.mean(v))} for s, v in sides.items()} for t, sides in sorted(out.items())}


# --- risk (§10.11.3) --------------------------------------------------------------------------------

def risk_counts(d, setup, pairs):
    """Per pair and side: R, S, T (risks taken in Risk pays), N (needless risks)."""
    arr = np.zeros((len(pairs), 2, 4))
    for k, p in enumerate(pairs):
        for j, side in enumerate(("nackgammon", "standard")):
            pid = p[side]
            cls = d.rows[pid]["class"]
            _, _, w = d.outcome(setup, pid)
            if cls == "risk":
                arr[k, j, 0] = 1
                arr[k, j, 2] = w.get("right_risk", 0) + w.get("wrong_risk", 0)
            elif cls == "safety":
                arr[k, j, 1] = 1
                arr[k, j, 3] = w.get("needless", 0)
    return arr


Z = NormalDist().inv_cdf


def sdt(R, S, T, N):
    if R == 0 or S == 0:
        return None, None
    zh, zf = Z((T + 0.5) / (R + 1)), Z((N + 0.5) / (S + 1))
    return zh - zf, -(zh + zf) / 2


def risk_table(d, setup, pairs, look):
    arr = risk_counts(d, setup, pairs)
    idx = rng_for(look + ":risk").integers(0, len(pairs), size=(2000, len(pairs)))
    out = {}
    tot = arr.sum(axis=0)
    for j, side in enumerate(("nackgammon", "standard")):
        R, S, T, N = tot[j]
        dp, c = sdt(R, S, T, N)
        out[side] = {"risk_pays": int(R), "safety_pays": int(S), "risks_taken": r2(T), "needless": r2(N),
                     "d_prime": r2(dp), "caution": r2(c)}
    bs = arr[idx].sum(axis=1)  # (B, 2, 4)
    dd, dc = [], []
    for b in bs:
        n1, s1 = sdt(*b[0]), sdt(*b[1])
        if None in n1 or None in s1:
            continue
        dd.append(n1[0] - s1[0])
        dc.append(n1[1] - s1[1])
    pn, ps = out["nackgammon"], out["standard"]
    out["change"] = {
        "d_prime": r2(pn["d_prime"] - ps["d_prime"]) if None not in (pn["d_prime"], ps["d_prime"]) else None,
        "d_prime_95": q(np.array(dd), 0.95) if dd else None,
        "caution": r2(pn["caution"] - ps["caution"]) if None not in (pn["caution"], ps["caution"]) else None,
        "caution_95": q(np.array(dc), 0.95) if dc else None}
    out["thin"] = any(out[s][k] < 50 for s in ("nackgammon", "standard") for k in ("risk_pays", "safety_pays"))
    return out


# --- report -------------------------------------------------------------------------------------------

def drops_matrix(d, setups, pairs, look, rule="random", loss_fn=None):
    """(B,) resampled drop per setup, with points (std, nack, drop)."""
    idx = rng_for(look).integers(0, len(pairs), size=(B, len(pairs)))
    res = {}
    for s in setups:
        if loss_fn:
            nk, st = loss_fn(s, pairs)
            m = np.ones(len(pairs))
        else:
            nk, st, m, _ = d.vectors(s, pairs, rule)
        dn, ds = boot_means(nk, m, idx), boot_means(st, m, idx)
        w = m.sum()
        res[s] = (float((st * m).sum() / w), float((nk * m).sum() / w), dn - ds, dn, ds)
    return res


def primary(d, res, level=1 - 0.05 / M):
    out = []
    for kind, a, b in PRIMARY:
        def side(x):
            names = [s for s in (GROUPS[x] if kind == "group" else [x]) if s in res]
            if not names:
                return None
            return {"members": names, "standard_pr": r2(np.mean([res[s][0] for s in names])),
                    "nackgammon_pr": r2(np.mean([res[s][1] for s in names])),
                    "drop": r2(np.mean([res[s][1] - res[s][0] for s in names])),
                    "boot": np.mean([res[s][2] for s in names], axis=0)}
        A, Bs = side(a), side(b)
        if A is None or Bs is None:
            out.append({"comparison": f"{a} − {b}", "missing": True})
            continue
        diff = A["drop"] - Bs["drop"]
        out.append({"comparison": f"{a} − {b}", "kind": kind, "diff": r2(diff),
                    f"ci_{level * 100:.0f}": q(A["boot"] - Bs["boot"], level),
                    "A": {k: v for k, v in A.items() if k != "boot"}, "B": {k: v for k, v in Bs.items() if k != "boot"}})
    return out


def kept_advantage(d, res, setups):
    rn, rs = res["Random"][3], res["Random"][4]
    rnp, rsp = res["Random"][1], res["Random"][0]
    out = {}
    for s in setups:
        sp, npr, _, dn, ds = res[s]
        adv = rsp - sp
        k = (rnp - npr) / adv if adv else float("nan")
        with np.errstate(divide="ignore", invalid="ignore"):
            kb = (rn - dn) / (rs - ds)
        kb = kb[np.isfinite(kb)]
        adv_ci = q(rs - ds, 0.95)
        out[s] = {"K": r2(k), "ci_95": q(kb, 0.95), "standard_advantage": r2(adv), "advantage_95": adv_ci,
                  "unstable": bool(adv < 20 or adv_ci[0] <= 0)}
    return out


def ranks(v):
    order = np.argsort(np.argsort(v, axis=-1, kind="stable"), axis=-1)
    return order.astype(float)


def spearman(d, res, setups):
    S = np.array([res[s][0] for s in setups])
    N = np.array([res[s][1] for s in setups])
    rho = float(np.corrcoef(ranks(S), ranks(N))[0, 1])
    Sb = np.stack([res[s][4] for s in setups], axis=1)
    Nb = np.stack([res[s][3] for s in setups], axis=1)
    rs, rn = ranks(Sb), ranks(Nb)
    rs -= rs.mean(axis=1, keepdims=True)
    rn -= rn.mean(axis=1, keepdims=True)
    rb = (rs * rn).sum(axis=1) / np.sqrt((rs ** 2).sum(axis=1) * (rn ** 2).sum(axis=1))
    rk_s, rk_n = ranks(S) + 1, ranks(N) + 1
    changes = sorted(((int(rk_n[i] - rk_s[i]), s, int(rk_s[i]), int(rk_n[i])) for i, s in enumerate(setups)),
                     key=lambda x: (-abs(x[0]), x[1]))[:5]
    return {"setups": len(setups), "rho": r2(rho), "ci_95": q(rb, 0.95),
            "largest_rank_changes": [{"setup": s, "standard_rank": a, "nackgammon_rank": b, "change": c}
                                     for c, s, a, b in changes]}


def engine_check(d, setups, rollout_db):
    with open("freeze/nack-paired.json") as f:
        ec = json.load(f)["engine_check"]["pairs"]
    pairs = [p for p in d.main if p["pair"] in set(ec)]
    con = sqlite3.connect(f"file:{rollout_db}?mode=ro", uri=True)
    ro = {}
    for pid, play, eq in con.execute("SELECT position, play, equity FROM rollouts"):
        ro.setdefault(pid, {})[play] = eq
    adj = {}
    counts = {"rolled_out_plays": 0, "adjusted_plays_used": 0}
    for p in pairs:
        for side in ("nackgammon", "standard"):
            pid = p[side]
            sc = d.scores[pid]
            r = ro.get(pid, {})
            names = list(sc["plays"])
            shift = np.mean([r[n] - sc["equity"][sc["plays"][n]] for n in r]) if r else 0.0
            eqs = [r.get(n, sc["equity"][i] + shift) for i, n in enumerate(names)]
            best = max(r.values()) if r else max(eqs)
            adj[pid] = {"loss": [max(0.0, best - e) for e in eqs], "rolled": [n in r for n in names]}
            counts["rolled_out_plays"] += len(r)

    def rollout_losses(s, prs):
        nk, st = [], []
        for p in prs:
            vals = []
            for side in ("nackgammon", "standard"):
                pid = p[side]
                sc, a = d.scores[pid], adj[pid]
                if s == "Random":
                    loss = float(np.mean(a["loss"]))
                    counts["adjusted_plays_used"] += sum(1 for x in a["rolled"] if not x)
                else:
                    _, valid, _ = d.outcome(s, pid)
                    r = d.answers[s][pid]
                    if valid:
                        i = sc["plays"][r["move"]]
                        loss = a["loss"][i]
                        if not a["rolled"][i]:
                            counts["adjusted_plays_used"] += 1
                    else:
                        loss = float(np.mean(a["loss"]))
                vals.append(500 * loss)
            nk.append(vals[0])
            st.append(vals[1])
        return np.array(nk), np.array(st)

    two = drops_matrix(d, setups + ["Random"], pairs, "engine")
    rol = drops_matrix(d, setups + ["Random"], pairs, "engine", loss_fn=rollout_losses)
    per = {s: {"2ply": {"standard_pr": r2(two[s][0]), "nackgammon_pr": r2(two[s][1]), "drop": r2(two[s][1] - two[s][0])},
               "rollout": {"standard_pr": r2(rol[s][0]), "nackgammon_pr": r2(rol[s][1]), "drop": r2(rol[s][1] - rol[s][0])}}
           for s in setups + ["Random"]}
    p2, pr = primary(d, two), primary(d, rol)
    comps = []
    for a, b in zip(p2, pr):
        if a.get("missing") or b.get("missing"):
            continue
        comps.append({"comparison": a["comparison"], "2ply": a["diff"], "rollout": b["diff"],
                      "2ply_ci_99": a["ci_99"], "rollout_ci_99": b["ci_99"],
                      "direction_changed": bool(np.sign(a["diff"]) != np.sign(b["diff"]))})
    return {"pairs": len(pairs), "counts": counts, "per_setup": per, "primary": comps,
            "settings": "GNUbg 1.08.003 rollout: 1,296 trials per play, cubeless, variance reduction on, "
                        "quasi-random dice, no truncation, no late evaluation, chequer play 1-ply, seed 1, 8 threads, "
                        "nice 19; candidates: top 5 at 2-ply plus every play any setup chose"}


def svg_chart(rows, path):
    """Standard PR (x) against Nackgammon PR (y), diagonal drawn, yardsticks marked."""
    W, Hh, pad = 640, 640, 60
    mx = max(max(r[1], r[2]) for r in rows) * 1.05
    sx = lambda v: pad + v / mx * (W - 2 * pad)  # noqa: E731
    sy = lambda v: Hh - pad - v / mx * (Hh - 2 * pad)  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" font-family="sans-serif" font-size="10">',
           f'<rect width="{W}" height="{Hh}" fill="white"/>',
           f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(mx)}" y2="{sy(mx)}" stroke="#bbb" stroke-dasharray="4"/>',
           f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(mx)}" y2="{sy(0)}" stroke="black"/>',
           f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(0)}" y2="{sy(mx)}" stroke="black"/>',
           f'<text x="{W / 2}" y="{Hh - 20}" text-anchor="middle">Standard error rate (PR), main 200 pairs</text>',
           f'<text x="18" y="{Hh / 2}" transform="rotate(-90 18 {Hh / 2})" text-anchor="middle">Nackgammon error rate (PR)</text>']
    step = 10 if mx < 120 else 20
    for v in range(0, int(mx) + 1, step):
        out.append(f'<text x="{sx(v)}" y="{sy(0) + 14}" text-anchor="middle">{v}</text>')
        out.append(f'<text x="{sx(0) - 6}" y="{sy(v) + 3}" text-anchor="end">{v}</text>')
    colors = {"decision models": "#1f77b4", "workhorses": "#2ca02c", "frontier": "#d62728",
              "no group (exploratory)": "#9467bd", "yardstick": "#000"}
    for name, x, y, group in rows:
        c = colors[group]
        shape = (f'<rect x="{sx(x) - 4}" y="{sy(y) - 4}" width="8" height="8" fill="{c}"/>' if group == "yardstick"
                 else f'<circle cx="{sx(x)}" cy="{sy(y)}" r="4" fill="{c}"/>')
        out.append(shape)
        out.append(f'<text x="{sx(x) + 6}" y="{sy(y) - 4}">{name}</text>')
    for i, (g, c) in enumerate(colors.items()):
        out.append(f'<circle cx="{W - 170}" cy="{pad + 14 * i}" r="4" fill="{c}"/>'
                   f'<text x="{W - 160}" y="{pad + 14 * i + 3}">{g}</text>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))


def group_of(s):
    for g, names in GROUPS.items():
        if s in names:
            return g
    return "yardstick" if s in YARDSTICKS else "no group (exploratory)"


def report(args):
    d = Data()
    os.makedirs(OUT, exist_ok=True)
    fl = first_look(d)
    setups = [s for s in d.setups if s in fl]
    res = {}
    # Per setup: first look, final look (extended: all 500 pairs), label, sensitivity, phases, tags, risk, cost.
    for s in setups + ["Random"]:
        r = {"group": group_of(s), "first_look": fl[s]}
        if s == "Random" or (fl[s]["extend"] and d.answered(s, d.reserve)):
            fin, *_ = setup_look(d, s, d.pairs, "final")
            r["final_look"] = fin
            r["extended"] = s != "Random"
        else:
            r["final_look"] = fl[s]
            r["extended"] = False
        if s != "Random" and fl[s]["extend"] and not d.answered(s, d.reserve):
            n = sum(1 for p in d.reserve for side in ("nackgammon", "standard")
                    if p[side] in d.answers.get(s, {}))
            r["extension_incomplete"] = f"{n} of 600 reserve positions answered"
        r["label"] = label(r["final_look"]["drop_975"])
        r["sensitivity_first"] = {}
        for rule in ("worst", "drop"):
            x, *_ = setup_look(d, s, d.main, "first", rule)
            r["sensitivity_first"][rule] = {k: x[k] for k in ("pairs", "standard_pr", "nackgammon_pr", "drop", "drop_975")}
        r["phases"] = phase_table(d, s)
        r["tags"] = tag_table(d, s)
        r["risk_main"] = risk_table(d, s, d.main, "first")
        if r["extended"]:
            r["risk_all"] = risk_table(d, s, d.pairs, "final")
        if s != "Random":
            r["cost_main"] = cost(d, s, [p[x] for p in d.main for x in ("nackgammon", "standard")])
            r["cost_all"] = cost(d, s, list(d.rows))
        res[s] = r
    mat = drops_matrix(d, setups + ["Random"], d.main, "first")
    frontier = GROUPS.get("frontier", [])
    out = {"groups_rule": NOTE_E,
           "frontier_note": (f"The frontier group currently has {len(frontier)} setup"
                             f"{'' if len(frontier) == 1 else 's'} ({', '.join(frontier)}); comparisons 2 and 3 rest on "
                             f"{'it' if len(frontier) == 1 else 'them'}."),
           "scope_note": "These results hold for these rosters only; each group is the setups in the run from that "
                         "original league.",
           "first_look": fl, "setups": res,
           "primary": {rule: primary(d, drops_matrix(d, setups + ["Random"], d.main, "first", rule))
                       for rule in ("random", "worst", "drop")},
           "groups": {g: [s for s in names if s in setups] for g, names in GROUPS.items()},
           "kept_advantage": kept_advantage(d, mat, setups),
           "spearman": spearman(d, mat, [s for s in setups if s not in YARDSTICKS])}
    ext = [s for s in setups if res[s]["extended"]]
    if ext:
        mat5 = drops_matrix(d, ext + ["Random"], d.pairs, "final")
        out["kept_advantage_all_500"] = kept_advantage(d, mat5, ext)
    if args.rollouts:
        out["engine_check"] = engine_check(d, setups, args.rollouts)
    rows = [(s, mat[s][0], mat[s][1], group_of(s)) for s in setups + ["Random"]]
    svg_chart(rows, os.path.join(OUT, "standard-vs-nackgammon.svg"))
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({"first_look": {s: {k: fl[s][k] for k in ("standard_pr", "nackgammon_pr", "drop", "drop_975",
                                                                  "label_first", "extend", "invalid")} for s in fl}},
                     indent=1, ensure_ascii=False))


def engine_candidates(args):
    """§10.12: rollout candidates of the 80 engine-check positions into OUT.db (score.py's near_ties table),
    the top 5 at 2-ply plus every play any setup chose; CHOSEN.json maps position id -> chosen plays."""
    d = Data()
    with open("freeze/nack-paired.json") as f:
        ec = set(json.load(f)["engine_check"]["pairs"])
    con = sqlite3.connect(args[0])
    con.executescript("CREATE TABLE IF NOT EXISTS near_ties (position TEXT PRIMARY KEY, gap REAL, candidates TEXT);")
    chosen = {}
    n = 0
    for p in d.main:
        if p["pair"] not in ec:
            continue
        for side in ("nackgammon", "standard"):
            pid = p[side]
            sc = d.scores[pid]
            names = list(sc["plays"])
            top = [names[i] for i in sorted(range(len(names)), key=lambda i: -sc["equity"][i])[:5]]
            picks = sorted({r["move"] for s, a in d.answers.items() if (r := a.get(pid)) is not None
                            and r["error"] is None and not r["invalid"] and r["move"] in sc["plays"]})
            chosen[pid] = picks
            cands = [x for x in names if x in set(top) | set(picks)]
            eq = sorted(sc["equity"], reverse=True)
            con.execute("INSERT OR REPLACE INTO near_ties VALUES (?,?,?)", (pid, eq[0] - eq[1], json.dumps(cands)))
            n += len(cands)
    con.commit()
    with open(args[1], "w") as f:
        json.dump(chosen, f, indent=1)
    print(f"engine check: 80 positions, {n} plays to roll out")


def main():
    if sys.argv[1:2] == ["first-look"]:
        fl = first_look(Data())
        for s, r in fl.items():
            print(f"{s:32s} std {r['standard_pr']:7.2f}  nack {r['nackgammon_pr']:7.2f}  drop {r['drop']:+7.2f}  "
                  f"97.5% [{r['drop_975'][0]:+.2f}, {r['drop_975'][1]:+.2f}]  {r['label_first']:8s} "
                  f"extend={r['extend']}  invalid n/s={r['invalid']['nackgammon']}/{r['invalid']['standard']}")
    elif sys.argv[1:2] == ["engine-candidates"]:
        engine_candidates(sys.argv[2:])
    elif sys.argv[1:2] == ["report"]:
        p = argparse.ArgumentParser()
        p.add_argument("--rollouts")
        report(p.parse_args(sys.argv[2:]))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
