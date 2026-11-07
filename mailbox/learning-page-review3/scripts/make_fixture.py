"""SYNTHETIC test fixture for the learning page's 'complete' and 'running' states: never published, never a result.
It takes a dry run's files in snapshot.py's STATE/learning layout (each arm's series 1 finished) and writes a copy in
which every arm has series 1-10 (series 1's games repeated), T0/T5/T10 answered 200/200 with made-up rates, the
inventory, the learning lift and the signal recomputed the way the site checks them, dry_run false.

    python3 make_fixture.py SITE_TOOLS DRY_SRC OUT_COMPLETE OUT_RUNNING TEST_SET

OUT_RUNNING is the same with complete false and series 6-10 of every arm not finished.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

tools, dry, out_c, out_r, test_set = (Path(a) for a in sys.argv[1:6])
sys.path.insert(0, str(tools))
import learning_validate as V  # noqa: E402

P = V.PROTOCOL
N, G = P["planned_series_per_arm"], P["games_per_series"]
test_sha = V.sha256(test_set)
T0 = dict(error_rate=31.4, risk_judgement=56.9, risks_found=41.2, right_safety=72.5, risk_appetite=33.0)
SHIFT = {"records": (-1.6, 3.1), "lessons": (-2.4, 11.2), "budget": (-0.7, 1.4)}  # error rate, risks found at T10


def metrics(er, rf, rs=72.0):
    return dict(answered=200, expected=200, valid=200, invalid=0, failed=0, error_rate=er, risk_judgement=(rf + rs) / 2,
                risks_found=rf, right_safety=rs, risk_appetite=34.0, input_tokens_per_decision=4100.0,
                latency_median_s=0.4, request_seconds=80.0, cost_usd=0.0)


def build(out: Path, finished: int):
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(dry, out)
    R = json.loads((out / "learning-pilot.json").read_text())
    prompt_sha = R["protocol"]["lesson_prompt_sha256"]
    t0 = json.loads((out / "runs/t0/aggregate.json").read_text())
    t0.update(metrics=metrics(T0["error_rate"], T0["risks_found"], T0["right_safety"]), test_set_sha256=test_sha)
    (out / "runs/t0/aggregate.json").write_text(json.dumps(t0))
    inv, aggs = {}, {}
    for arm in P["arms"]:
        base = json.loads((dry / "runs" / arm / "s01" / "aggregate.json").read_text())
        inv[arm], aggs[arm] = {}, {}
        for s in range(1, finished + 1):
            d = out / "runs" / arm / f"s{s:02d}"
            d.mkdir(parents=True, exist_ok=True)
            A = dict(base, series=s, test_set_sha256=test_sha, lesson_prompt_sha256=prompt_sha)
            if arm != "control":
                de, dr = SHIFT[arm]
                A["evaluations"] = {"T5": metrics(T0["error_rate"] + de / 2, T0["risks_found"] + dr / 2),
                                    "T10": metrics(T0["error_rate"] + de, T0["risks_found"] + dr)}
            files = {}
            if arm == "lessons":
                for g in range(1, G + 1):
                    src = dry / "runs/lessons/s01" / f"lessons-g{g:02d}.txt"
                    shutil.copyfile(src, d / f"lessons-g{g:02d}.txt")
                    files[str(g)] = hashlib.sha256(src.read_bytes()).hexdigest()
            (d / "aggregate.json").write_text(json.dumps(A))
            aggs[arm][s] = A
            inv[arm][str(s)] = dict(games=list(range(1, G + 1)), lessons_files=files, test_set_sha256=test_sha,
                                    lesson_prompt_sha256=prompt_sha)
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    table = {}
    for arm in P["arms"]:
        table[arm] = {"T0": dict(metrics(T0["error_rate"], T0["risks_found"], T0["right_safety"]), shared=True)}
        if arm != "control":
            for cp in ("T5", "T10"):
                ms = [a["evaluations"][cp] for a in aggs[arm].values()]
                table[arm][cp] = {k: mean([m[k] for m in ms]) for k in ms[0]} | dict(series=len(ms))
    R.update(protocol=dict(R["protocol"], dry_run=False, test_set_sha256=test_sha), t0_done=True,
             series_finished={a: list(range(1, finished + 1)) for a in P["arms"]},
             series_done={a: finished for a in P["arms"]}, inventory=inv, table=table, complete=finished == N)
    for k in ("signal", "learning_lift", "paired_series"):
        R.pop(k, None)
    if finished == N:
        lift = {a: {s: V.pooled(A["games"], 1, 3) - V.pooled(A["games"], 8, 10) for s, A in aggs[a].items()}
                for a in P["arms"]}
        R["learning_lift"] = {a: dict(lift=mean(list(lift[a].values())), lift_ci=None) | (
            {} if a == "control" else dict(vs_control=mean([lift[a][s] - lift["control"][s] for s in lift[a]]),
                                           vs_control_ci=None)) for a in P["arms"]}
        R["signal"] = {}
        for a in P["arms"][1:]:
            rf = table[a]["T10"]["risks_found"] - table[a]["T0"]["risks_found"]
            rs = table[a]["T10"]["right_safety"] - table[a]["T0"]["right_safety"]
            R["signal"][a] = dict(risks_found_change=rf, risks_found_ci=None, right_safety_change=rs, right_safety_ci=None,
                                  signal=rf >= 10 and rs >= -5)
        R["paired_series"] = list(range(1, N + 1))
    (out / "learning-pilot.json").write_text(json.dumps(R, indent=1))
    print(f"{out}: complete={R['complete']}, series finished per arm {finished}")


build(out_c, N)
build(out_r, 5)
