#!/usr/bin/env python3
"""Independent recomputation of the "Did they improve?" verdicts from improve.json (plan sections 2, 6, 7).

    python3 mailbox/improve_recompute.py IMPROVE_JSON OUT_CSV
"""
import csv
import json
import sys

d = json.load(open(sys.argv[1]))
rows = []
for m in d["models"]:
    E = m["empty"]
    T = [s["t10"] for s in m["series"] if s.get("finished") and s.get("t10")]
    full = lambda t: t and t["answered"] == t["expected"] == 200 and not t["failed"]
    gate = len(E) == 3 and all(map(full, E)) and len(m["series"]) == 5 and all(
        s.get("finished") and s.get("games") == 10 for s in m["series"]) and len(T) == 5 and all(map(full, T))
    mean = lambda xs, k: sum(x[k] for x in xs) / len(xs) if xs else None
    r = dict(setup=m["setup"], state=m["state"], empty_runs=len(E), t10_done=len(T))
    for k in ("risks_found", "right_safety", "error_rate"):
        b, a = mean(E, k), mean(T, k)
        r[f"{k}_before"], r[f"{k}_after"] = b, a
        r[f"{k}_change"] = None if a is None or b is None else a - b
    r["invalid_empty"] = sum(e["invalid"] for e in E)
    r["invalid_t10"] = sum(t["invalid"] for t in T)
    r["threshold"] = max(max(e["risks_found"] for e in E) - min(e["risks_found"] for e in E), 5) if len(E) == 3 else None
    r["verdict"] = (("Yes" if r["risks_found_change"] > r["threshold"] and r["right_safety_change"] >= -5 else "No")
                    if gate else "")
    rows.append(r)
with open(sys.argv[2], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
for r in rows:
    if r["t10_done"] or r["empty_runs"]:
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
