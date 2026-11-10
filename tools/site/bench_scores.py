"""The backgammon feed of the combined score page (https://zekiworks.github.io/analysis/decision-models/all-benches/):
bench-scores.json at the site's root, in the three benches' shared schema (turkce #4062; logic's conventions #4065).

One row per model row of the leaderboard (story.leaderboard_rows: the model's leaderboard setup, late entries
included); the programs (GNUbg weak, Safest, Random) are left out. Every number is the setup's stored error rate
(analysis.quality, the leaderboard's own): score_0_100 = 100 x (1 - error rate / Random's error rate in the same
league), Random's being the leaderboard's Random row of that league (played, or computed on its positions; a late
entry: the league whose field it played); no floor (turkce #4076: below 0 = worse than a random legal play).
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
ROW_KEYS = {"repo", "commit", "name", "model_key", "maker", "kind", "params_total", "params_active", "quantization",
            "score_0_100", "raw", "calibration_error", "improvement_points", "runs", "notes"}
RAW_KEYS = {"metric", "value", "questions", "options"}
# A locally served open-weights setup's recorded checkpoint in setups.json model_id: "<owner>/<repo> @ <commit>".
CHECKPOINT = re.compile(r"^([\w.-]+/[\w.-]+) @ ([0-9a-f]{7,40})\b")
QUANT = re.compile(r"\b(FP8|NVFP4|BF16)\b", re.I)
# The cross-site join key (bus #4243, turkce #4251): the model's name without its setting, route or a parenthesised
# note ('(open)' etc.), lower case, spaces to '-', dots kept: 'gpt-6-astra', 'claude-fable-5.1', 'reax-1.3', 'cygnet'.
# All benches joins on repo where both rows have one, else on this key. Settings never split a key.
KEY_OK = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
# The other benches' names for our leaderboard rows (Ümit #4270): All benches joins rows on the name, so a model's row
# here carries the name the Logic & Math and Reading feeds give the same model and route; the key follows from it.
# Our setup on a different route than their row: their name with the route suffix in their style, and the route in
# `notes`; a setting their name leaves out goes there too. Leaderboard name -> (feed name, note or None, (repo, commit)
# of the served checkpoint where our records name it and setups.json does not, else None). problems() fails on an
# entry no leaderboard row uses.
FEED_NAMES = {
    # Reading 'Perplexity Decider 27B v1.2 (local GPU)' (perplexity-ai/pplx-decider-v1.2, self-hosted); Logic & Math
    # has only the API row 'Perplexity Decider 27B v1.2 API'.
    # Served from snapshot 225c913 (tools/v3/servers/decider-v1.2.sh), Reading's commit.
    "Decider v1.2 27B": ("Perplexity Decider 27B v1.2 (local GPU)", None,
                         ("perplexity-ai/pplx-decider-v1.2", "225c913ddc8761a8264f04f64548e1f97e443eb3")),
    # Logic & Math, Reading 'Perplexity Decider Flash v1.2' (perplexity-ai/pplx-decider-flash-v1.2, self-hosted).
    "Decider Flash v1.2": ("Perplexity Decider Flash v1.2", None, None),
    # Reading 'Perplexity Decider 27B v1.1' is the Perplexity Decisions API; ours ran on our GPUs.
    "Decider v1.1 27B": ("Perplexity Decider 27B v1.1 (local GPU)",
                         "route: our GPUs (released checkpoint); the other benches' row is the Perplexity Decisions API",
                         None),
    # Logic & Math, Reading 'Inception Mercury Decide' (OpenRouter System One API; ours: OpenRouter, Inception).
    "Mercury Decide": ("Inception Mercury Decide", None, None),
    # Reading 'GPT-6 Luna (Decisions API)' (OpenAI Decisions API); not 'GPT-6 Luna (chat API)'.
    "GPT-6 Luna": ("GPT-6 Luna (Decisions API)", None, None),
    # Reading 'GPT-6 Astra', 'GPT-6.1 Sol' (Codex CLI, ChatGPT subscription; ours: ChatGPT subscription).
    "GPT-6 Astra (high)": ("GPT-6 Astra", "setting: high", None),
    "GPT-6.1 Sol (high)": ("GPT-6.1 Sol", "setting: high", None),
    # Reading 'Gemini 4 Argon', 'Gemini 3.8 Flash' (Gemini API; ours: Google Antigravity subscription).
    "Gemini 4 Argon (high)": ("Gemini 4 Argon", "setting: high; route: Google Antigravity subscription", None),
    "Gemini 3.8 Flash (high)": ("Gemini 3.8 Flash", "setting: high; route: Google Antigravity subscription", None),
    # Reading 'Claude Fable 5.1', 'Claude Opus 5.5', 'Claude Sonnet 5.5' (Claude Code CLI, Claude subscription).
    "Claude Fable 5.1 (high)": ("Claude Fable 5.1", "setting: high", None),
    "Claude Opus 5.5 (high)": ("Claude Opus 5.5", "setting: high", None),
    "Claude Sonnet 5.5 (high)": ("Claude Sonnet 5.5", "setting: high", None),
    # Reading 'Grok 4.7' (xAI Responses API, SuperGrok subscription; ours: SuperGrok subscription).
    "Grok 4.7 (high)": ("Grok 4.7", "setting: high", None),
    # Reading 'Kimi K3.1 Pro' (OpenRouter, Moonshot AI's endpoint, mxfp4; ours the same endpoint).
    "Kimi K3.1 Pro (off)": ("Kimi K3.1 Pro", "setting: off", None),
    # Reading 'GLM-5.3' (OpenRouter, Fireworks endpoint; ours: Fireworks via OpenRouter).
    "GLM-5.3 (low)": ("GLM-5.3", "setting: low", None),
    # Logic & Math, Reading 'Gemma 4 31B' (google/gemma-4-31B-it, self-hosted, FP8).
    "Gemma 4 31B (on)": ("Gemma 4 31B", "setting: on", None),
    # Logic & Math, Reading 'Qwen3.8-27B' (Qwen/Qwen3.8-27B, self-hosted).
    "Qwen3.8-27B (low)": ("Qwen3.8-27B", "setting: low", None),
    # Logic & Math, Reading 'Mammoth-1', 'Elephant-1' (baselabs/*, self-hosted through the model card's loader).
    "Base Labs Mammoth-1": ("Mammoth-1", None, None),
    "Base Labs Elephant-1": ("Elephant-1", None, None),
    # Logic & Math, Reading 'Fastino GLiDE v1.2' (fastino/GLiDE, self-hosted, Fastino's server).
    "Fastino GLiDE v1.2 (local)": ("Fastino GLiDE v1.2", None, None),
    # Logic & Math, Reading 'Cygnet' (Cygnet decision server on vLLM, self-hosted).
    "Cygnet (Gemma 4 12B)": ("Cygnet", None, None),
}


def model_key(model: str) -> str:
    return re.sub(r"\s+", "-", re.sub(r"\s*\([^)]*\)", "", model).strip().lower())


def score(error_rate: float | None, random: float) -> float | None:
    """100 x (1 - error rate / Random's in the same league), 2 decimals; no floor."""
    return None if error_rate is None else round(100 * (1 - error_rate / random), 2)


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


def randoms(prog_rows) -> dict[int, float]:
    """{league id: Random's error rate on that league's positions}: the leaderboard's Random rows, played (League 1) or
    computed over the league's positions where Random did not play."""
    out = {}
    for x in next(g for _, _, name, g in prog_rows if name == "Random"):
        er = x["q"]["error_rate"] if x["q"] is not None else x["r"]["error_rate"]
        if not er:
            raise ValueError(f"bench-scores: Random has no error rate in League {x['lg']['id']}")
        out[x["lg"]["id"]] = er
    return out


def league_of(x) -> int:
    """The league whose positions the row's error rate is on; a late entry: the league whose field it played."""
    return x["late"]["field_league"] if x["late"] else x["lg"]["id"]


def build(S) -> dict:
    model_rows, prog_rows = ST.leaderboard_rows(S)
    rnd = randoms(prog_rows)
    rows = []
    for x, _, _, group in model_rows:
        m = _meta(S, x)
        q = x["q"] or {}
        p = P.PARAMS[x["model"]]
        repo, commit, quant = _checkpoint(m)
        imp = _improvement(S, group)
        lg = league_of(x)
        notes = [f"League {lg}", CALIBRATION_NOTE]
        if x["late"]:
            notes.append(f"late entry: its own decisions in late-entry matches against League {lg}'s field "
                         f"(different positions from the league's); scored against League {lg}'s Random")
        notes.append("run on our GPUs" if m.get("runs_on") == "our GPUs" else "hosted (API or subscription)")
        name, route, ckpt = FEED_NAMES.get(x["name"], (x["name"], None, None))
        if route:
            notes.append(route)
        if ckpt and repo is None:
            repo, commit = ckpt
        if imp is not None:
            imp = round(imp, 2)
            notes.append("improvement_points: change in risks found, percentage points of risk-pays decisions "
                         "(with lessons minus no memory)")
        rows.append(dict(
            repo=repo, commit=commit, name=name, model_key=model_key(name if x["name"] in FEED_NAMES else x["model"]),
            maker=H.maker(x["name"])[0],
            kind=ST.model_type(S, x),
            params_total=p["total_b"], params_active=p["active_b"] if p["moe"] else p["total_b"], quantization=quant,
            score_0_100=score(q.get("error_rate"), rnd[lg]),
            raw=dict(metric=METRIC, value=q.get("error_rate"), questions=q.get("scored"), options=None),
            calibration_error=None, improvement_points=imp, runs=[f"backgammon:{m['slug']}"], notes="; ".join(notes)))
    rows.sort(key=lambda r: (r["score_0_100"] is None, -(r["score_0_100"] or 0), r["name"]))
    per = ", ".join(f"League {k}: {v:.1f}" for k, v in sorted(rnd.items()))
    return dict(
        bench="backgammon", title="Backgammon", url=S["base"], updated=S["as_of"],
        score=dict(zero=f"0 = a random legal play's error rate in the same league ({per}; late entries: the league "
                        "whose field they played); below 0 = worse than a random legal play. score = 100 × (1 − "
                        "error rate / Random's error rate in that league); error rate (PR) = 500 × mean GNUbg equity "
                        "loss per decision",
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
    model_rows, prog_rows = ST.leaderboard_rows(S)
    rnd = randoms(prog_rows)
    expect = {FEED_NAMES.get(x["name"], (x["name"],))[0]: ((x["q"] or {}).get("error_rate"), league_of(x))
              for x, *_ in model_rows}
    unused = sorted(set(FEED_NAMES) - {x["name"] for x, *_ in model_rows})
    if unused:
        out.append(f"{PATH}: FEED_NAMES entries for no leaderboard model row: {unused}")
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    opt = lambda v, t: v is None or t(v)
    for r in doc["models"]:
        name = r.get("name") if isinstance(r, dict) else None
        if not isinstance(r, dict) or set(r) != ROW_KEYS or not isinstance(r["raw"], dict) or set(r["raw"]) != RAW_KEYS:
            out.append(f"{PATH}: row {name!r}: keys are not the schema's")
            continue
        raw = r["raw"]
        types = [isinstance(name, str), isinstance(r["model_key"], str) and bool(KEY_OK.match(r["model_key"])),
                 isinstance(r["maker"], str), r["kind"] in ("chat", "decision"),
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
        if name not in expect:
            continue
        er, lg = expect[name]
        want = score(er, rnd[lg])
        if raw["value"] != er or not r["notes"].startswith(f"League {lg};") or (want is None) != (
                r["score_0_100"] is None) or (want is not None and want != r["score_0_100"]):
            out.append(f"{PATH}: row {name!r}: score {r['score_0_100']} / error rate {raw['value']}, the leaderboard's "
                       f"error rate {er} against League {lg}'s Random gives {want}")
        if r["improvement_points"] is not None and r["improvement_points"] != round(r["improvement_points"], 2):
            out.append(f"{PATH}: row {name!r}: improvement_points not rounded to 2 decimals")
    names = sorted(r.get("name") for r in doc["models"] if isinstance(r, dict))
    want = sorted(expect)
    if names != want:
        out.append(f"{PATH}: rows {names} are not the leaderboard's model rows {want}")
    return out