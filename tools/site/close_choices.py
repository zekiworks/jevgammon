"""Close choices (Method specification 2026-10-24, section 9; values in content/close_choices_2026-10-24.json).

"A decision is a close choice when the second most likely play has at least half the probability of the first
(internally: split)." Probabilities over plays, not sampled reasoning.

    league(lg, audit, plays_dir) -> {"setups": {name: summary}, "records": {turn id: record}}

Eligible: probability audit status `complete` (offline.eligible) with an engine value for every legal play. For every
eligible decision: p1, p2, p1 + p2, the two candidate plays (ties by the shown option order), the features that differ
between them (from the option text the model was shown), their 2-ply values and losses, and at both margins the
position class, stake band and risk call of the play made. Per setup: shares with count and denominator, ties, the
risk close choices, close choices by stake band (Risk pays only) and the missed-risk comparison of §9.7 with a
bootstrap by match.

Run as a script to print the per-league tables for the mailbox:
    python3 tools/site/close_choices.py STATE [LEAGUE ...]
"""

import json
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import analysis as A
import offline as O
from common import CONTENT, THRESHOLDS as T

CC = json.loads((CONTENT / "close_choices_2026-10-24.json").read_text())
LABEL = CC["label"]
DEFINITION = CC["definition"]
FEATURES = CC["features"]
FEATURE_LABEL = {"hitting": "hitting risk (the opponent's hitting rolls)", "points": "newly made points",
                 "race": "pip counts", "prime": "longest prime"}
MARGIN_KEYS = {"main": T["risk_margin"], "robust": T["risk_margin_robust"]}
assert sorted(MARGIN_KEYS.values()) == sorted(CC["margins"])
EXCLUSIONS = ["invalid", "grouped", "sparse", "unverified", "no_raw", "not_audited", "not_scored", "no_probabilities"]
EXCLUSION_LABEL = {"invalid": "invalid answer", "grouped": "asked in groups of options",
                   "sparse": "incomplete distribution (an option without its own probability)",
                   "unverified": "stored probabilities not reproduced from the raw response",
                   "no_raw": "no raw response", "not_audited": "not audited",
                   "not_scored": "no engine value", "no_probabilities": "one letter only, or a program"}
POINTS = re.compile(r"makes (?:no new point|the ([\d, ]+) points?);")
PIPS = re.compile(r"pips: you (\d+), opponent (\d+)")
PRIME = re.compile(r"longest prime (\d+)")
SMALL = CC["small_group_below"]


def features_of(desc: str) -> dict:
    """The four measured features of one option text (describe.py)."""
    m = POINTS.search(desc)
    pts = frozenset(int(x) for x in m.group(1).split(", ")) if m and m.group(1) else frozenset()
    p = PIPS.search(desc)
    return dict(points=pts, race=(int(p.group(1)), int(p.group(2))), prime=int(PRIME.search(desc).group(1)))


def top_two(pvec: list[float], rank: list[int]) -> dict:
    """Candidates 1 and 2 by probability, equal probabilities by the shown option order; the ties of §9.4."""
    total = sum(pvec)
    p = [x / total for x in pvec]
    order = sorted(range(len(p)), key=lambda j: (-p[j], rank[j]))
    c1, c2 = order[0], order[1]
    p1, p2 = p[c1], p[c2]
    tie_order = p1 == p2
    tie_member = len(order) > 2 and p[order[2]] == p2
    return dict(c1=c1, c2=c2, p1=p1, p2=p2, close=p2 >= CC["close_ratio"] * p1,
                tie=tie_order or tie_member, tie_zero=(tie_order or tie_member) and p2 == 0,
                tie_order=tie_order, tie_member=tie_member)


def fetch_texts(plays_dir: Path, wanted: dict[int, tuple[int, int]]) -> dict[int, tuple]:
    """(equity, hitting rolls, description) of both candidates, read from the GNUbg scores store."""
    shards = sorted(plays_dir.glob("s*.db"), key=lambda p: int(p.stem[1:]))
    out = {}
    by = defaultdict(list)
    for tid in wanted:
        by[tid % len(shards)].append(tid)
    for k, ids in by.items():
        db = sqlite3.connect(f"file:{shards[k]}?mode=ro", uri=True)
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            for tid, data in db.execute(f"SELECT turn_id, data FROM plays WHERE turn_id IN ({','.join('?' * len(chunk))})",
                                        chunk):
                rows = json.loads(data)
                a, b = wanted[tid]
                out[tid] = (rows[a], rows[b])
        db.close()
    return out


def _share(n, den) -> dict:
    return dict(n=n, den=den, share=n / den if den else None, small=0 < den < SMALL)


def _stats(xs: list[float]) -> dict:
    return dict(n=len(xs), mean=sum(xs) / len(xs) if xs else None, median=statistics.median(xs) if xs else None)


def describe_group(recs: list[dict]) -> dict:
    """§9.5 summaries of one group (close choices, or the other eligible decisions)."""
    n = len(recs)
    by_k = Counter(len(r["differ"]) for r in recs)
    return dict(n=n, differ={f: _share(sum(f in r["differ"] for r in recs), n) for f in FEATURES},
                by_count=[by_k.get(k, 0) for k in range(len(FEATURES) + 1)],
                gap=_stats([r["gap"] for r in recs]), loss1=_stats([r["loss1"] for r in recs]),
                loss2=_stats([r["loss2"] for r in recs]), p1=_stats([r["p1"] for r in recs]),
                p2=_stats([r["p2"] for r in recs]), psum=_stats([r["p1"] + r["p2"] for r in recs]),
                psum_bins=[sum(1 for r in recs if min(int((r["p1"] + r["p2"]) * 10), 9) == b) for b in range(10)])


def _rates(nC, mC, nO, mO):
    """Crude and adjusted (§9.7) differences for count arrays (... × strata); nan where undefined."""
    with np.errstate(divide="ignore", invalid="ignore"):
        tC, tO = nC.sum(-1), nO.sum(-1)
        rc, ro = mC.sum(-1) / tC, mO.sum(-1) / tO
        crude = np.where((tC > 0) & (tO > 0), rc - ro, np.nan)
        both = (nC > 0) & (nO > 0)
        w = np.where(both, nC, 0).sum(-1)
        ac = np.where(both, mC, 0).sum(-1) / w
        ao = np.where(both, nC * np.where(nO > 0, mO / np.where(nO > 0, nO, 1), 0), 0).sum(-1) / w
        adj = np.where(w > 0, ac - ao, np.nan)
    return dict(rate_c=rc, rate_o=ro, crude=crude, adj_c=np.where(w > 0, ac, np.nan),
                adj_o=np.where(w > 0, ao, np.nan), adjusted=adj, covered=w)


def missed_risks(recs: list[dict], matches: list, mk: str, label: str) -> dict:
    """§9.7 at one margin: group G (Risk pays, the candidates a risk pair), close choices vs the other decisions."""
    G = [r for r in recs if r["m"][mk]["cls"] == "risk" and r["risk_pair"]]
    C = [r for r in G if r["close"]]
    Oth = [r for r in G if not r["close"]]
    out = dict(group=len(G), close=_share(sum(r["m"][mk]["call"] == "missed" for r in C), len(C)),
               other=_share(sum(r["m"][mk]["call"] == "missed" for r in Oth), len(Oth)))
    if not C or not Oth:
        out.update(na="N/A: " + ("no close choices" if not C else "no other decisions") + " in this group")
        return out
    strata = sorted({r["stratum"] for r in G})
    si = {s: i for i, s in enumerate(strata)}
    mi = {m: i for i, m in enumerate(matches)}
    X = np.zeros((len(matches), 4, len(strata)))
    for r in G:
        X[mi[r["match"]], 0 if r["close"] else 2, si[r["stratum"]]] += 1
        X[mi[r["match"]], 1 if r["close"] else 3, si[r["stratum"]]] += r["m"][mk]["call"] == "missed"
    tot = X.sum(0)
    point = _rates(*tot)
    out.update(na=None, crude=float(point["crude"]), adjusted=None if np.isnan(point["adjusted"]) else float(point["adjusted"]),
               adj_close=None if np.isnan(point["adj_c"]) else float(point["adj_c"]),
               adj_other=None if np.isnan(point["adj_o"]) else float(point["adj_o"]),
               covered=_share(int(point["covered"]), len(C)), strata=len(strata),
               strata_both=int(((tot[0] > 0) & (tot[2] > 0)).sum()))
    if out["adjusted"] is None:
        out["adjusted_na"] = "N/A: no stratum holds both close choices and other decisions"
    rng = np.random.default_rng(A.boot(label))
    M, R = len(matches), CC["bootstrap_resamples"]
    W = np.stack([np.bincount(rng.integers(0, M, M), minlength=M) for _ in range(R)]).astype(float)
    S = np.einsum("rm,mks->rks", W, X)
    b = _rates(S[:, 0], S[:, 1], S[:, 2], S[:, 3])
    for k in ("crude", "adjusted"):
        v = b[k][~np.isnan(b[k])]
        out[f"{k}_lo"], out[f"{k}_hi"] = ((float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v)
                                         else (None, None))
        out[f"{k}_left_out"] = int(R - len(v))
    out["resamples"], out["matches"] = R, M
    return out


def setup_summary(ds: str, name: str, decs: list[dict], recs: list[dict], status: Counter) -> dict:
    total = len(decs)
    excl = {k: status.get(k, 0) for k in EXCLUSIONS if status.get(k, 0)}
    out = dict(decisions=total, eligible=len(recs), exclusions=excl, definition=DEFINITION, label=LABEL)
    if not recs:
        out.update(na="N/A: no full probability distribution")
        return out
    close = [r for r in recs if r["close"]]
    other = [r for r in recs if not r["close"]]
    ties = [r for r in recs if r["tie"]]
    out.update(na=None, close=_share(len(close), len(recs)),
               ties=dict(top_two=len(ties), positive=sum(not r["tie_zero"] for r in ties),
                         zero=sum(r["tie_zero"] for r in ties), order=sum(r["tie_order"] for r in ties),
                         member=sum(r["tie_member"] for r in ties),
                         close=sum(r["close"] for r in ties)),
               groups=dict(close=describe_group(close), other=describe_group(other)))
    rc = sum(r["risk_pair"] for r in close)
    out["risk_close"] = _share(rc, len(close))
    out["risk_close_of_eligible"] = _share(rc, len(recs))
    out["risk_pair_other"] = _share(sum(r["risk_pair"] for r in other), len(other))
    matches = sorted({r["match"] for r in recs})
    out["margins"] = {}
    for mk, mv in MARGIN_KEYS.items():
        classes = {}
        for cls in ("risk", "safety", "none"):
            rs = [r for r in recs if r["m"][mk]["cls"] == cls]
            cl = [r for r in rs if r["close"]]
            classes[cls] = dict(eligible=len(rs), close=_share(len(cl), len(rs)),
                                risk_close=_share(sum(r["risk_pair"] for r in cl), len(cl)))
        stake = {}
        for b in A.BANDS:
            rs = [r for r in recs if r["m"][mk]["cls"] == "risk" and r["m"][mk]["band"] == b]
            stake[b] = _share(sum(r["close"] for r in rs), len(rs))
        out["margins"][mk] = dict(margin=mv, classes=classes, stake=stake,
                                  missed=missed_risks(recs, matches, mk, f"close/{ds}/{name}/{mk}"))
    return out


def league(lg: dict, audit: dict, plays_dir: Path) -> dict:
    """Every close-choice number of one league (lg = analysis.load_leagues entry)."""
    ds = lg["dataset"]
    by = defaultdict(list)
    for d in lg["decisions"]:
        by[d["setup"]].append(d)
    status, cand = {}, {}
    for d in lg["decisions"]:
        s = O.eligible(d, audit)
        status[d["id"]] = s
        if s == "complete":
            cand[d["id"]] = top_two(d["pvec"], d["rank"])
    texts = fetch_texts(plays_dir, {tid: (c["c1"], c["c2"]) for tid, c in cand.items()})
    missing_values = sum(1 for d in lg["decisions"] if status[d["id"]] == "not_scored")
    records, setups = {}, {}
    for name, decs in by.items():
        recs = []
        for d in decs:
            c = cand.get(d["id"])
            if c is None:
                continue
            (n1, e1, h1, t1), (n2, e2, h2, t2) = texts[d["id"]]
            f1, f2 = features_of(t1), features_of(t2)
            differ = [f for f, a, b in (("hitting", h1, h2), ("points", f1["points"], f2["points"]),
                                        ("race", f1["race"], f2["race"]), ("prime", f1["prime"], f2["prime"])) if a != b]
            least = min(d["shots"])
            sh1, sh2 = d["shots"][c["c1"]], d["shots"][c["c2"]]
            r = dict(id=d["id"], match=d["match"], close=c["close"], p1=c["p1"], p2=c["p2"], c1=c["c1"], c2=c["c2"],
                     tie=c["tie"], tie_zero=c["tie_zero"], tie_order=c["tie_order"], tie_member=c["tie_member"],
                     differ=differ, e1=e1, e2=e2, gap=abs(e1 - e2), loss1=d["losses"][c["c1"]],
                     loss2=d["losses"][c["c2"]], risk_pair=(sh1 == least) != (sh2 == least),
                     stratum=(d["phase"], A.option_bucket(d["n"]), A.gap_bucket(d.get("gap"))), m={})
            for mk, mv in MARGIN_KEYS.items():
                cls, call, stake, _ = A.play_call(d["shots"], d["losses"], d["chosen"], mv)
                r["m"][mk] = dict(cls=cls, call=call, band=A.band(stake) if cls == "risk" else None)
            recs.append(r)
            records[d["id"]] = r
        setups[name] = setup_summary(ds, name, decs, recs, Counter(status[d["id"]] for d in decs))
    return dict(setups=setups, records=records, missing_engine_values=missing_values,
                spec_fixed_on=CC["fixed_on"], label=LABEL, definition=DEFINITION)


# --- Mailbox tables ---------------------------------------------------------------------------------------------

def _p(s: dict) -> str:
    if not s["den"]:
        return "N/A (0 / 0)"
    return f"{100 * s['share']:.1f}% ({s['n']:,} / {s['den']:,}){'†' if s['small'] else ''}"


def _ci(m: dict, k: str) -> str:
    v = m.get(k)
    if v is None:
        return m.get(f"{k}_na") or m.get("na") or "N/A"
    lo, hi = m.get(f"{k}_lo"), m.get(f"{k}_hi")
    return f"{100 * v:+.1f} pts [{100 * lo:+.1f}, {100 * hi:+.1f}]" if lo is not None else f"{100 * v:+.1f} pts"


def _rate(x) -> str:
    return "N/A" if x is None else f"{100 * x:.1f}%"


def markdown(lg_id: int, res: dict) -> str:
    S = res["setups"]
    names = sorted(S, key=str.lower)
    L = []
    w = L.append
    w(f"### League {lg_id}\n")
    w(f"Missing engine values among probability-complete decisions: {res['missing_engine_values']}.\n")
    w("#### Eligibility and close choices\n")
    w("| Setup | decisions | eligible | excluded by reason | close choices ÷ eligible | ties affecting the top two "
      "(positive / at 0; order / membership) | risk close choices ÷ close choices | risk close ÷ eligible |")
    w("|---|---|---|---|---|---|---|---|")
    for n in names:
        s = S[n]
        ex = "; ".join(f"{EXCLUSION_LABEL[k]} {v:,}" for k, v in s["exclusions"].items()) or "none"
        if s["na"]:
            w(f"| {n} | {s['decisions']:,} | 0 | {ex} | {s['na']} | — | — | — |")
            continue
        t = s["ties"]
        w(f"| {n} | {s['decisions']:,} | {s['eligible']:,} | {ex} | {_p(s['close'])} | {t['top_two']:,} "
          f"({t['positive']:,} / {t['zero']:,}; {t['order']:,} / {t['member']:,}) | {_p(s['risk_close'])} | "
          f"{_p(s['risk_close_of_eligible'])} |")
    ok = [n for n in names if not S[n]["na"]]
    if not ok:
        w("\nNo setup in this league has an eligible decision: every column below is N/A.\n")
        return "\n".join(L) + "\n"
    w("\n#### p1, p2 and p1 + p2 (means; medians in brackets)\n")
    w("| Setup | close: p1 | close: p2 | close: p1 + p2 | other: p1 | other: p2 | other: p1 + p2 |")
    w("|---|---|---|---|---|---|---|")
    for n in ok:
        g = S[n]["groups"]
        c = lambda grp, k: "—" if not g[grp]["n"] else f"{g[grp][k]['mean']:.3f} [{g[grp][k]['median']:.3f}]"
        w(f"| {n} | {c('close', 'p1')} | {c('close', 'p2')} | {c('close', 'psum')} | {c('other', 'p1')} | "
          f"{c('other', 'p2')} | {c('other', 'psum')} |")
    w("\n#### Features that differ between the two candidates (share of the group; several can differ)\n")
    w("| Setup | group | n | hitting rolls | newly made points | pip counts | longest prime | none / 1 / 2 / 3 / 4 differ |")
    w("|---|---|---|---|---|---|---|---|")
    for n in ok:
        for grp, lab in (("close", "close choices"), ("other", "other decisions")):
            g = S[n]["groups"][grp]
            w(f"| {n} | {lab} | {g['n']:,} | " + " | ".join(_p(g["differ"][f]) for f in FEATURES)
              + f" | {' / '.join(f'{x:,}' for x in g['by_count'])} |")
    w("\n#### Engine values (GNUbg 2-ply, equity): gap between the candidates and each one's loss against the engine's best play (mean [median])\n")
    w("| Setup | group | n | gap |e1 − e2| | candidate 1 loss | candidate 2 loss |")
    w("|---|---|---|---|---|---|")
    for n in ok:
        for grp, lab in (("close", "close choices"), ("other", "other decisions")):
            g = S[n]["groups"][grp]
            f = lambda k: "—" if not g["n"] else f"{g[k]['mean']:.4f} [{g[k]['median']:.4f}]"
            w(f"| {n} | {lab} | {g['n']:,} | {f('gap')} | {f('loss1')} | {f('loss2')} |")
    for mk, lab in (("main", "0.001"), ("robust", "0.02")):
        w(f"\n#### Margin {lab}: close choices by position class and by stake band (Risk pays only)\n")
        w("| Setup | Risk pays: close ÷ eligible | Safety pays: close ÷ eligible | No trade-off: close ÷ eligible | "
          "Risk pays: risk close ÷ close | Safety pays: risk close ÷ close | small stake | medium stake | big stake |")
        w("|---|---|---|---|---|---|---|---|---|")
        for n in ok:
            m = S[n]["margins"][mk]
            c = m["classes"]
            w(f"| {n} | {_p(c['risk']['close'])} | {_p(c['safety']['close'])} | {_p(c['none']['close'])} | "
              f"{_p(c['risk']['risk_close'])} | {_p(c['safety']['risk_close'])} | "
              + " | ".join(_p(m["stake"][b]) for b in A.BANDS) + " |")
        w(f"\n#### Margin {lab}: missed risks in Risk pays positions whose candidates are a safe play and a riskier one\n")
        w("| Setup | group | close choices: missed ÷ n | other: missed ÷ n | crude difference [95%] | "
          "adjusted: close | adjusted: other (standardised) | adjusted difference [95%] | close choices covered | resamples left out (crude / adjusted) |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for n in ok:
            m = S[n]["margins"][mk]["missed"]
            if m.get("na"):
                w(f"| {n} | {m['group']:,} | {_p(m['close'])} | {_p(m['other'])} | {m['na']} | N/A | N/A | N/A | — | — |")
                continue
            w(f"| {n} | {m['group']:,} | {_p(m['close'])} | {_p(m['other'])} | {_ci(m, 'crude')} | "
              f"{_rate(m['adj_close'])} | {_rate(m['adj_other'])} | {_ci(m, 'adjusted')} | "
              f"{_p(m['covered'])} | {m['crude_left_out']} / {m['adjusted_left_out']} |")
    return "\n".join(L) + "\n"


def main():
    state = Path(sys.argv[1]).expanduser()
    wanted = {int(x) for x in sys.argv[2:]}
    L = A.load_leagues(state / "snap.db", state / "plays")
    audit = O.load_audit()
    dump = {}
    for lg in L["leagues"]:
        if wanted and lg["id"] not in wanted:
            continue
        res = league(lg, audit, state / "plays")
        dump[lg["dataset"]] = res["setups"]
        print(markdown(lg["id"], res))
    out = state.parent / "close_choices.json"
    out.write_text(json.dumps(dump, indent=1, default=list))
    print(f"(JSON: {out})", file=sys.stderr)


if __name__ == "__main__":
    main()
