"""SYNTHETIC test fixture for the learning page's 'complete' and 'running' states: never published, never a result.
It takes a dry run's files in snapshot.py's STATE/learning layout (pilot.py's real aggregate format) and writes a copy
in which every arm has series 1-10 (series 1's games repeated, each series with its own dice seed), T0/T5/T10 answered
200/200 with made-up rates, dry_run false; learning-pilot.json is then the summary pilot.py would write for those
aggregates (learning_validate.summary, the site's line-by-line copy of pilot.py summary()).

    python3 make_fixture.py SITE_TOOLS DRY_SRC OUT_COMPLETE OUT_RUNNING TEST_SET

OUT_RUNNING has series 1-5 of every arm only.
"""
import json
import shutil
import sys
from pathlib import Path

tools, dry, out_c, out_r, test_set = (Path(a) for a in sys.argv[1:6])
sys.path.insert(0, str(tools))
import learning_validate as V  # noqa: E402

test_sha = V.sha256(test_set)
T0 = dict(error_rate=31.4, risks_found=41.2, right_safety=72.5)
SHIFT = {"records": (-1.6, 3.1), "lessons": (-2.4, 11.2), "budget": (-0.7, 1.4)}  # error rate, risks found at T10


def metrics(er, rf, rs=72.0):
    return dict(answered=200, expected=200, valid=200, invalid=0, failed=0, error_rate=er,
                risk_judgement=(rf + rs) / 2, risks_found=rf, right_safety=rs, risk_appetite=34.0, risk_pays=80,
                safety_pays=120, calls=dict(right_risk=round(0.8 * rf), wrong_risk=10, needless=5,
                                            missed=80 - round(0.8 * rf), right_safety=round(1.2 * rs), none=0),
                input_tokens_per_decision=4100.0, output_tokens_per_decision=12.0, request_seconds=80.0,
                latency_median_s=0.4, cost_usd=0.0)


def build(out: Path, n_series: int):
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(dry, out)
    R = json.loads((out / "learning-pilot.json").read_text())
    prompt_sha = R["protocol"]["lesson_prompt_sha256"]
    t0 = json.loads((out / "runs/t0/aggregate.json").read_text())
    t0.update(metrics=metrics(T0["error_rate"], T0["risks_found"], T0["right_safety"]), test_set_sha256=test_sha,
              dry=False)
    (out / "runs/t0/aggregate.json").write_text(json.dumps(t0))
    aggs = {}
    for arm in V.ARMS:
        base = json.loads((dry / "runs" / arm / "s01" / "aggregate.json").read_text())
        shutil.rmtree(out / "runs" / arm)
        aggs[arm] = {}
        for s in range(1, n_series + 1):
            d = out / "runs" / arm / f"s{s:02d}"
            d.mkdir(parents=True)
            A = dict(base, series=s, seed=V.series_seed(s), test_set_sha256=test_sha, lesson_prompt_sha256=prompt_sha)
            if arm != "control":
                de, dr = SHIFT[arm]
                A["evaluations"] = {"T5": metrics(T0["error_rate"] + de / 2, T0["risks_found"] + dr / 2),
                                    "T10": metrics(T0["error_rate"] + de, T0["risks_found"] + dr)}
            if arm == "lessons":
                for g in range(1, V.G + 1):
                    shutil.copyfile(dry / "runs/lessons/s01" / f"lessons-g{g:02d}.txt", d / f"lessons-g{g:02d}.txt")
            (d / "aggregate.json").write_text(json.dumps(A))
            aggs[arm][s] = A
    protocol = dict(R["protocol"], dry_run=False, test_set_sha256=test_sha)
    S = dict(updated_at="2026-11-07T17:00:00+00:00") | V.summary(t0, aggs, protocol, test_sha, prompt_sha)
    (out / "learning-pilot.json").write_text(json.dumps(S, indent=1))
    print(f"{out}: complete={S['complete']}, series finished per arm {n_series}")


build(out_c, V.N)
build(out_r, 5)
