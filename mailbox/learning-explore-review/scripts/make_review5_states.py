"""The learning page's review states, in snapshot.py's STATE/learning layout (read-only reads of the pilot's files).

    python3 make_states.py SITE_TOOLS PILOT_DIR TEST_SET OUT_DIR

- OUT_DIR/real/learning: the REAL complete state, copied exactly as snapshot.py's snapshot_learning copies it
  (LEARNING_FILES: out/learning-pilot.json, every runs/*/s*/aggregate.json, runs/t0/aggregate.json, the lessons arm's
  lessons-gKK.txt and the lesson prompt files). Nothing is changed.
- OUT_DIR/none/learning: no results file and no aggregate (the lesson prompt files only): the state before the run.
- OUT_DIR/SYNTHETIC-<state>/learning: SYNTHETIC fixtures, never results. Each is the real state with series REMOVED
  (subsetting only: no aggregate, lesson file or number is edited) and learning-pilot.json rewritten as the summary
  pilot.py would write for the kept aggregates (learning_validate.summary, the site's copy of pilot.py summary()), its
  updated_at the latest finished_at of the kept aggregates:
  - not-started: no T0 aggregate, no series;
  - smoke-running: T0 and series 1-3 control, 1-2 records, 1-3 lessons, 1-2 budget (2 of 3 series in every arm);
  - running: T0 and series 1-7 control, 1-6 records, 1-6 lessons, 1-5 budget, plus budget s06 cut after game 4 (an
    UNFINISHED series: its games list truncated to 4, its T5/T10 evaluations kept; validated, not published).
"""
import glob
import json
import os
import shutil
import sys
from pathlib import Path

tools, pilot, test_set, out = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(tools))
import learning_validate as V  # noqa: E402
import snapshot  # noqa: E402

test_sha = V.sha256(test_set)


def copy_real(dest: Path):
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for pattern, rel_of in snapshot.LEARNING_FILES:
        for p in sorted(glob.glob(str(pilot / pattern))):
            rel = rel_of(os.path.relpath(p, pilot))
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest / rel)


def subset(name: str, keep: dict, t0: bool, partial: dict | None = None):
    dest = out / name / "learning"
    copy_real(dest)
    runs = dest / "runs"
    if not t0:
        shutil.rmtree(runs / "t0")
    aggs = {arm: {} for arm in V.ARMS}
    for arm in V.ARMS:
        for d in sorted((runs / arm).glob("s*")):
            s = int(d.name[1:])
            if s > keep[arm] and not (partial and partial.get(arm) == s):
                shutil.rmtree(d)
                continue
            A = json.loads((d / "aggregate.json").read_text())
            if partial and partial.get(arm) == s:  # an unfinished series: the first 4 games only
                A["games"] = A["games"][:4]
                A["games_error_rate_8_10"] = None
                A["games_error_rate_1_3"] = V.pooled(A["games"], 1, 3)
                A["budget_points"] = A["budget_points"][:4]
                A["budget_context_empty_after_game"] = [g for g in A["budget_context_empty_after_game"] if g <= 4]
                A["context_tokens_after_game"] = {k: v for k, v in A["context_tokens_after_game"].items()
                                                  if int(k) <= 4}
                A["records_dropped_after_game"] = {k: v for k, v in A["records_dropped_after_game"].items()
                                                   if int(k) <= 4}
                (d / "aggregate.json").write_text(json.dumps(A))
            aggs[arm][s] = A
    R = json.loads((dest / "learning-pilot.json").read_text())
    T0 = json.loads((runs / "t0" / "aggregate.json").read_text()) if t0 else None
    times = [T0["finished_at"]] if T0 else []
    times += [A["finished_at"] for arm in V.ARMS for A in aggs[arm].values()]
    updated = max(times) if times else R["updated_at"]
    S = dict(updated_at=updated) | V.summary(T0, aggs, R["protocol"], test_sha, R["protocol"]["lesson_prompt_sha256"])
    (dest / "learning-pilot.json").write_text(json.dumps(S, indent=1))
    fin = {a: len(v) for a, v in S["series_finished"].items()}
    print(f"{name}: SYNTHETIC (subset of the real series); T0 {'kept' if t0 else 'removed'}; finished series {fin}; "
          f"complete={S['complete']}; updated_at {updated}")


copy_real(out / "real" / "learning")
R = json.loads((out / "real/learning/learning-pilot.json").read_text())
print(f"real: copied as snapshot.py does; complete={R['complete']}; updated_at {R['updated_at']}")
none = out / "none" / "learning"
shutil.rmtree(none, ignore_errors=True)
none.mkdir(parents=True)
for f in ("lessons_system.txt", "lessons_user.txt"):
    shutil.copyfile(pilot / f, none / f)
print("none: the lesson prompt files only")
subset("SYNTHETIC-not-started", dict(control=0, records=0, lessons=0, budget=0), t0=False)
subset("SYNTHETIC-smoke-running", dict(control=3, records=2, lessons=3, budget=2), t0=True)
subset("SYNTHETIC-running", dict(control=7, records=6, lessons=6, budget=5), t0=True, partial=dict(budget=6))
