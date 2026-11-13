"""Learning pilot: the results tables (markdown) from out/learning-pilot.json, aggregates only. The learning lift and
the signal rule appear only when every planned series is done (plan section 9).

    python3 workspace/learning-pilot/report.py [path/to/learning-pilot.json]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["control", "records", "lessons", "budget"]
KEYS = [("error_rate", "Error rate (PR)"), ("risk_judgement", "Risk judgement"), ("risks_found", "Risks found %"),
        ("right_safety", "Right safety %"), ("risk_appetite", "Risk appetite %")]


def f(x, d=1):
    return "–" if x is None else f"{x:.{d}f}"


def ci(c, d=1):
    return "" if not c else f" [{c[0]:.{d}f}, {c[1]:.{d}f}]"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out/learning-pilot.json"
    s = json.loads(path.read_text())
    t = s["table"]
    out = ["Series done: " + ", ".join(f"{a} {s['series_done'][a]}/{s['planned_series_per_arm']}" for a in ARMS)
           + f"; shared T0 {'done' if s['t0_done'] else 'not run'}.", ""]
    out.append("| Arm | Evaluation | Series | " + " | ".join(k[1] for k in KEYS)
               + " | Invalid | Failed | Input tokens / decision | Request time (s) | Cost |")
    out.append("|" + " --- |" * (len(KEYS) + 8))
    for a in ARMS:
        for cp in ["T0", "T5", "T10"]:
            r = t[a].get(cp)
            if r is None:
                continue
            series = "shared" if r.get("shared") else r["series"]
            out.append(f"| {a} | {cp} | {series} | " + " | ".join(f(r[k]) for k, _ in KEYS)
                       + f" | {r['invalid']} | {r['failed']} | {f(r.get('input_tokens_per_decision'), 0)} | "
                         f"{r['request_seconds']:.0f} | $0 |")
    out += ["", "Change from the shared T0 (percentage points; error rate in PR):", ""]
    out.append("| Arm | Evaluation | " + " | ".join(k[1] for k in KEYS) + " |")
    out.append("|" + " --- |" * (len(KEYS) + 2))
    for a in ARMS[1:]:
        for cp in ["T5", "T10"]:
            r, z = t[a].get(cp), t[a].get("T0")
            if not r or not z or not r["series"]:
                continue
            out.append(f"| {a} | {cp} | " + " | ".join(
                f(r[k] - z[k]) if r[k] is not None and z[k] is not None else "–" for k, _ in KEYS) + " |")
    out += ["", "Games against GNUbg Beginner (all series so far):", "",
            "| Arm | Series | Games | Decisions | Invalid | Error rate (PR) | Wins | Input tokens / decision | "
            "Median decision latency (s) | Records dropped | Cost |", "|" + " --- |" * 11]
    for a in ARMS:
        g = s["games"][a]
        out.append(f"| {a} | {g['series']} | {g['games']} | {g['decisions']} | {g['invalid']} | {f(g['error_rate'])} | "
                   f"{g['wins']} | {f(g['input_tokens_per_decision'], 0)} | {f(g['latency_median_s'], 2)} | "
                   f"{g['records_dropped']} | $0 |")
    if s.get("complete"):
        out += ["", f"Signal rule (T10 − T0, mean over {len(s['paired_series'])} series, 95% bootstrap over series):", "",
                "| Arm | Risks found change (pp) | Right safety change (pp) | Signal |", "| --- | --- | --- | --- |"]
        for a in ARMS[1:]:
            x = s["signal"][a]
            out.append(f"| {a} | {f(x['risks_found_change'])}{ci(x['risks_found_ci'])} | "
                       f"{f(x['right_safety_change'])}{ci(x['right_safety_ci'])} | {'–' if x['signal'] is None else ('yes' if x['signal'] else 'no')} |")
        out += ["", "A17 learning lift (error rate games 1–3 minus games 8–10; positive = better later), paired by series:",
                "", "| Arm | Lift (PR) | Lift − control's lift (PR) |", "| --- | --- | --- |"]
        for a in ARMS:
            x = s["learning_lift"][a]
            vs = f"{f(x['vs_control'], 2)}{ci(x['vs_control_ci'], 2)}" if a != "control" else "–"
            out.append(f"| {a} | {f(x['lift'], 2)}{ci(x['lift_ci'], 2)} | {vs} |")
    else:
        out += ["", "Signal rule and learning lift: not shown until every planned series of every arm is done."]
    print("\n".join(out))


main()
