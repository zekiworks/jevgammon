"""QC 2026-11-12 Run 2 planning: an arm's stored verdict (site rule, improve_validate.scores) and how far it is from
flipping. Read-only. Usage: python3 verdict_margin.py MODEL-KEY [S5-answer-ids...]
For the given answer ids (stored invalid by a transport error), every outcome of their re-ask is enumerated by class
(each position: its best play and its worst play for the share it falls in), and the verdict range is reported."""
import itertools, json, sqlite3, sys
from statistics import mean

sys.path.insert(0, "/home/cbasaran/code/jevgammon-improve/workspace/improve")
import improve as I  # noqa: E402

key = sys.argv[1]
ids = [int(x) for x in sys.argv[2:]]
R = I.mdir(key)
E = {e: json.loads((R / e / "aggregate.json").read_text())["test"] for e in ("E1", "E2", "E3")}
T = {s: json.loads((R / f"S{s}" / "aggregate.json").read_text())["t10"] for s in range(1, 6)}


def verdict(E, T):
    b_rf, b_rs = mean(E[e]["risks_found"] for e in E), mean(E[e]["right_safety"] for e in E)
    a_rf, a_rs = mean(T[s]["risks_found"] for s in T), mean(T[s]["right_safety"] for s in T)
    rf = [E[e]["risks_found"] for e in E]
    thr = max(max(rf) - min(rf), I.FLOOR_POINTS)
    d_rf, d_rs = a_rf - b_rf, a_rs - b_rs
    return dict(before_rf=b_rf, before_rs=b_rs, after_rf=a_rf, after_rs=a_rs, change_rf=d_rf, change_rs=d_rs,
                threshold=thr, improved=round(d_rf, 9) > round(thr, 9) and round(d_rs, 9) >= -I.SAFETY_DROP)


out = dict(model=key, stored=verdict(E, T), per_test={k: {x: v[x] for x in ("valid", "invalid", "failed", "risk_pays",
           "safety_pays", "risks_found", "right_safety")} for k, v in {**E, **{f"S{s}-T10": T[s] for s in T}}.items()})
v = out["stored"]
# margin: how much the mean of T10 risks found may drop, and right safety may drop, before the verdict flips
out["margin"] = dict(after_rf_mean_slack=v["change_rf"] - v["threshold"], after_rs_mean_slack=v["change_rs"] + I.SAFETY_DROP,
                     one_t10_rf_slack=5 * (v["change_rf"] - v["threshold"]),
                     one_t10_rs_slack=5 * (v["change_rs"] + I.SAFETY_DROP))
if ids:
    db = sqlite3.connect(f"file:{I.db_path(key)}?mode=ro", uri=True)
    pos = {p["id"]: p for p in I.test_set()["positions"]}
    rows = [dict(zip(("id", "setup", "position_id"), r)) for r in
            db.execute(f"SELECT id, setup, position_id FROM answers WHERE id IN ({','.join('?' * len(ids))})", ids)]
    setups = {r["setup"] for r in rows}
    assert len(setups) == 1, setups
    setup = setups.pop()
    s = int(setup.split("| s")[1][:2])
    base = I.test_answers(key, setup)
    outcomes = []
    for r in rows:
        p = pos[r["position_id"]]
        outcomes.append([(r["position_id"], i, *I.play_call(p["shots"], p["losses"], i)) for i in range(len(p["losses"]))])
        # distinct (class, call) outcomes suffice
        seen, keep = set(), []
        for o in outcomes[-1]:
            if o[2:] not in seen:
                seen.add(o[2:])
                keep.append(o)
        outcomes[-1] = keep
    res = set()
    detail = []
    for combo in itertools.product(*outcomes):
        pick = {pid: i for pid, i, _, _ in combo}
        new = []
        for a in base:
            a = dict(a)
            if a["position_id"] in pick:
                a.update(invalid=0, error=None, chosen_index=pick[a["position_id"]])
            new.append(a)
        m = I.metrics_from(new, pos)
        T2 = dict(T)
        T2[s] = m
        vv = verdict(E, T2)
        res.add(vv["improved"])
        detail.append((tuple(c[3] for c in combo), round(m["risks_found"], 3), round(m["right_safety"], 3),
                       round(vv["change_rf"], 3), round(vv["change_rs"], 3), vv["improved"]))
    out["refill"] = dict(setup=setup, positions=[(r["id"], r["position_id"], sorted({o[2] for o in oc})) for r, oc in
                                                  zip(rows, outcomes)],
                         outcomes=len(detail), verdicts_possible=sorted(res),
                         range_rf=[min(d[1] for d in detail), max(d[1] for d in detail)],
                         range_rs=[min(d[2] for d in detail), max(d[2] for d in detail)])
print(json.dumps(out, indent=1, default=str))
