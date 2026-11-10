"""The backgammon feed of the combined score page (https://zekiworks.github.io/analysis/decision-models/all-benches/):
bench-scores.json at the site's root, in the three benches' shared schema (turkce #4062; logic's conventions #4065).

One row per model row of the leaderboard (story.leaderboard_rows: the model's leaderboard setup, late entries
included); the programs (GNUbg weak, Safest, Random) are left out. Every number is the setup's stored error rate
(analysis.quality, the leaderboard's own): score_0_100 = 100 x (1 - error rate / Random's error rate), Random's
being the leaderboard's Random row; no floor (turkce #4076: below 0 = worse than a random legal play).
calibration_error stays null until Ümit decides its definition; improvement_points is "Did they improve?"'s change
in risks found for a model with a verdict."""

import math
import re

import home as H
import pages as P
import story as ST
from common import LATE_ENTRY

PATH = "bench-scores.json"
METRIC = "error rate (PR, lower is better)"
CALIBRATION_NOTE = "calibration definition pending Ümit"
# The schema's keys (turkce #4062): checks.py refuses any other.
TOP_KEYS = {"bench", "title", "url", "updated", "score", "models"}
ROW_KEYS = {"repo", "commit", "name", "maker", "kind", "params_total", "params_active", "quantization", "score_0_100",
            "raw", "calibration_error", "improvement_points", "runs", "notes"}
RAW_KEYS = {"metric", "value", "questions", "options"}
# A locally served open-weights setup's recorded checkpoint in setups.json model_id: "<owner>/<repo> @ <commit>".
CHECKPOINT = re.compile(r"^([\w.-]+/[\w.-]+) @ ([0-9a-f]{7,40})\b")
QUANT = re.compile(r"\b(FP8|NVFP4|BF16)\b", re.I)


def score(error_rate: float | None, random: float) -> float | None:
    return None if error_rate is None else 100 * (1 - error_rate / random)


def _meta(S, x) -> dict:
    return S["setups_meta"].get((LATE_ENTRY, x["name"])) or {} if x["late"] else P.origin_meta(S, x["ds"], x["name"])


def _checkpoint(m: dict) -> tuple[str | None, str | None, str | None]:
    """(repo, commit, quantization): only for open weights on our GPUs with a recorded commit (logic #4065)."""
    hit = CHECKPOINT.match(m.get("model_id") or "")
    if not hit or m.get("weights") != "open" or m.get("runs_on") != "our GPUs":
        return None, None, None
    q = QUANT.search(m["model_id"])
    return hit.group(1), hit.group(2), q.group(1).upper() if q else None


def _improvement(S, group: list) -> float | None:
    """The change in risks found (percentage points, lessons minus no memory) of the row's setup in "Did they
    improve?", once it has a verdict."""
    names = {x["name"] for x in group}
    done = [m for m in ((S["improve"].get("results") or {}).get("models") or [])
            if m["setup"] in names and m["verdict"] and m["change"]["risks_found"] is not None]
    if len(done) > 1:
        raise ValueError(f"bench-scores: several 'Did they improve?' verdicts for one row: {sorted(names)}")
    return done[0]["change"]["risks_found"] if done else None


def build(S) -> dict:
    model_rows, prog_rows = ST.leaderboard_rows(S)
    rnd = next(x for x, _, name, _ in prog_rows if name == "Random")
    random = rnd["q"]["error_rate"]
    if not random:
        raise ValueError("bench-scores: Random has no error rate")
    rows = []
    for x, _, _, group in model_rows:
        m = _meta(S, x)
        q = x["q"] or {}
        p = P.PARAMS[x["model"]]
        repo, commit, quant = _checkpoint(m)
        imp = _improvement(S, group)
        notes = [CALIBRATION_NOTE]
        if x["late"]:
            notes.append("late entry: its own decisions in late-entry matches (different positions and opponents "
                         "from the leagues)")
        else:
            notes.append(f"League {x['lg']['id']}")
        notes.append("run on our GPUs" if m.get("runs_on") == "our GPUs" else "hosted (API or subscription)")
        if imp is not None:
            notes.append("improvement_points: change in risks found, percentage points of risk-pays decisions "
                         "(with lessons minus no memory)")
        rows.append(dict(
            repo=repo, commit=commit, name=x["name"], maker=H.maker(x["name"])[0], kind=ST.model_type(S, x),
            params_total=p["total_b"], params_active=p["active_b"] if p["moe"] else p["total_b"], quantization=quant,
            score_0_100=score(q.get("error_rate"), random),
            raw=dict(metric=METRIC, value=q.get("error_rate"), questions=q.get("scored"), options=None),
            calibration_error=None, improvement_points=imp, runs=[f"backgammon:{m['slug']}"], notes="; ".join(notes)))
    rows.sort(key=lambda r: (r["score_0_100"] is None, -(r["score_0_100"] or 0), r["name"]))
    where = "late-entry matches" if rnd["late"] else f"League {rnd['lg']['id']}"
    return dict(
        bench="backgammon", title="Backgammon", url=S["base"], updated=S["as_of"],
        score=dict(zero=f"0 = Random's error rate ({random:.1f}, a random legal play; {rnd['q']['scored']:,} scored "
                        f"decisions, {where}); below 0 = worse than a random legal play. score = 100 × (1 − error "
                        f"rate / {random:.1f}); error rate (PR) = 500 × mean GNUbg equity loss per decision",
                   hundred="100 = error rate 0: the engine's best play on every decision"),
        models=rows)



def problems(S, doc) -> list[str]:
    """The file against the schema (closed keys, types), each score finite and at most 100 (no lower bound: below 0
    is worse than Random) and equal to its raw value's, one row per leaderboard model row."""
    out = []
    if set(doc) != TOP_KEYS:
        return [f"{PATH}: keys {sorted(doc)}, not {sorted(TOP_KEYS)}"]
    if not (all(isinstance(doc[k], str) for k in ("bench", "title", "url", "updated"))
            and isinstance(doc["score"], dict) and set(doc["score"]) == {"zero", "hundred"}
            and all(isinstance(v, str) for v in doc["score"].values()) and isinstance(doc["models"], list)):
        return [f"{PATH}: bench/title/url/updated/score/models of the wrong type"]
    random = next(x for x, _, n, _ in ST.leaderboard_rows(S)[1] if n == "Random")["q"]["error_rate"]
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    opt = lambda v, t: v is None or t(v)
    for r in doc["models"]:
        name = r.get("name") if isinstance(r, dict) else None
        if not isinstance(r, dict) or set(r) != ROW_KEYS or not isinstance(r["raw"], dict) or set(r["raw"]) != RAW_KEYS:
            out.append(f"{PATH}: row {name!r}: keys are not the schema's")
            continue
        raw = r["raw"]
        types = [isinstance(name, str), isinstance(r["maker"], str), r["kind"] in ("chat", "decision"),
                 opt(r["repo"], lambda v: isinstance(v, str)), opt(r["commit"], lambda v: isinstance(v, str)),
                 (r["repo"] is None) == (r["commit"] is None), opt(r["params_total"], num),
                 opt(r["params_active"], num), opt(r["quantization"], lambda v: isinstance(v, str)),
                 opt(r["score_0_100"], num), r["calibration_error"] is None, opt(r["improvement_points"], num),
                 isinstance(r["runs"], list) and len(r["runs"]) == 1 and isinstance(r["runs"][0], str)
                 and r["runs"][0].startswith("backgammon:"), isinstance(r["notes"], str),
                 raw["metric"] == METRIC, opt(raw["value"], num), opt(raw["questions"], lambda v: type(v) is int),
                 raw["options"] is None]
        if not all(types):
            out.append(f"{PATH}: row {name!r}: field {types.index(False)} of the wrong type or value")
            continue
        if r["score_0_100"] is not None and r["score_0_100"] > 100:
            out.append(f"{PATH}: row {name!r}: score {r['score_0_100']} above 100")
        want = score(raw["value"], random)
        if (want is None) != (r["score_0_100"] is None) or (want is not None and abs(want - r["score_0_100"]) > 1e-9):
            out.append(f"{PATH}: row {name!r}: score {r['score_0_100']}, its error rate gives {want}")
    names = sorted(r.get("name") for r in doc["models"] if isinstance(r, dict))
    want = sorted(x["name"] for x, *_ in ST.leaderboard_rows(S)[0])
    if names != want:
        out.append(f"{PATH}: rows {names} are not the leaderboard's model rows {want}")
    return out