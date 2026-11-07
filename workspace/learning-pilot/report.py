"""Learning pilot: the results table (markdown) from learning-pilot.json, aggregates only.

    python3 workspace/learning-pilot/report.py > /tmp/table.md
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["control", "records", "lessons", "top10"]
KEYS = [("error_rate", "Error rate (PR)", 1), ("risk_judgement", "Risk judgement", 1), ("risks_found", "Risks found %", 1),
        ("right_safety", "Right safety %", 1), ("risk_appetite", "Risk appetite %", 1)]


def f(x, d=1):
    return "–" if x is None else f"{x:.{d}f}"


def main():
    s = json.loads((HERE / "learning-pilot.json").read_text())
    t = s["table"]
    out = [f"Series done: " + ", ".join(f"{a} {s['series_done'][a]}/{s['planned_series_per_arm']}" for a in ARMS), ""]
    out.append("| Arm | Test | Series | " + " | ".join(k[1] for k in KEYS) + " | Invalid | Failed | Request time (s) | Cost |")
    out.append("|" + " --- |" * (len(KEYS) + 7))
    for a in ARMS:
        for cp in ["T0", "T5", "T10"]:
            r = t[a][cp]
            out.append(f"| {a} | {cp} | {r['series']} | " + " | ".join(f(r[k], d) for k, _, d in KEYS)
                       + f" | {r['invalid']} | {r['failed']} | {r['request_seconds']:.0f} | $0 |")
    out += ["", "Difference from control (arm − control), same test round:", ""]
    out.append("| Arm | Test | " + " | ".join(k[1] for k in KEYS) + " |")
    out.append("|" + " --- |" * (len(KEYS) + 2))
    for a in ARMS[1:]:
        for cp in ["T0", "T5", "T10"]:
            cells = []
            for k, _, d in KEYS:
                x, c = t[a][cp][k], t["control"][cp][k]
                cells.append(f(x - c, d) if x is not None and c is not None else "–")
            out.append(f"| {a} | {cp} | " + " | ".join(cells) + " |")
    if s.get("complete") and s.get("learning_lift"):
        ll = s["learning_lift"]
        out += ["", "Learning lift (error rate games 1–3 minus games 8–10; positive = better later):", "",
                "| Arm | Lift | Lift − control's |", "| --- | --- | --- |"]
        for a in ARMS:
            out.append(f"| {a} | {f(ll['per_arm'][a], 2)} | {f(ll['vs_control'].get(a), 2) if a != 'control' else '–'} |")
    print("\n".join(out))


main()
