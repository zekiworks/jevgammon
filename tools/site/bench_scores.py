"""The backgammon feed of the combined score page (https://zekiworks.github.io/analysis/decision-models/all-benches/):
bench-scores.json at the site's root, in the three benches' shared schema (turkce #4062; logic's conventions #4065).

One row per model row of the leaderboard (story.leaderboard_rows: the model's leaderboard setup, late entries
included); the programs (GNUbg weak, Safest, Random) are left out. Every number is the setup's stored error rate
(analysis.quality, the leaderboard's own): score_0_100 = 100 x (1 - error rate / Random's error rate on the same
positions), Random's being the leaderboard's Random row of that league (played, or computed on its positions); a late
entry: Random computed on the entrant's own scored positions in its late-entry matches against the league whose field
it played (Ümit #6225); no floor (turkce #4076: below 0 = worse than a random legal play).
calibration_error stays null until Ümit decides its definition; improvement_points is "Did they improve?"'s change
in risks found for a model with a verdict."""

import math
import re

import home as H
import pages as P
import story as ST
from common import (LATE_ENTRY, QC_IMPROVE, QC_LABEL, QC_SETUPS, RUN2, model_key, name_and_tag, tag_text,
                    unplayed_text)

PATH = "bench-scores.json"
METRIC = "error rate (PR, lower is better)"
CALIBRATION_NOTE = "calibration definition pending Ümit"
# The schema's keys (turkce #4062): checks.py refuses any other.
TOP_KEYS = {"bench", "title", "url", "updated", "score", "models"}
ROW_KEYS = {"repo", "commit", "name", "tag", "model_key", "maker", "kind", "params_total", "params_active", "quantization",
            "score_0_100", "raw", "calibration_error", "improvement_points", "runs", "notes"}
RAW_KEYS = {"metric", "value", "questions", "options"}
# A locally served open-weights setup's recorded checkpoint in setups.json model_id: "<owner>/<repo> @ <commit>".
CHECKPOINT = re.compile(r"^([\w.-]+/[\w.-]+) @ ([0-9a-f]{7,40})\b")
QUANT = re.compile(r"\b(FP8|NVFP4|BF16)\b", re.I)
# The cross-site join key (bus #4243, turkce #4251; common.model_key): the model's name without its setting, route or a
# parenthesised note, lower case, spaces to '-', dots kept: 'gpt-6-astra', 'claude-fable-5.1', 'reax-1.3', 'cygnet'.
# All benches joins on repo where both rows have one, else on this key. Settings never split a key.
KEY_OK = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
# Names (Ümit #4445, turkce #4449, Zeki #4448): `name` is the maker's official name (common.name_and_tag, the shared
# names file), `tag` how we ran the row's setup ('setting · route · snapshot', '' without one), as the site shows them.
# A name no longer tells routes or snapshots apart, so each row's model_key is frozen here, by the row's setup (the
# keys of 10 Nov 2026, before the names changed): two rows of one official name ('GLiDE', API and v1.2) keep their keys.
# A row not listed (a model added later) gets common.model_key of its shown model name, which keeps a route or
# snapshot ('fastino-glide-v1.2', 'deepseek-v4.1-flash-1017'). The note: where the row's setting or route differs from
# the other benches' row of the model (Ümit #4270), unchanged. CHECKPOINTS: the (repo, commit) of the served checkpoint
# where our records name it and setups.json does not. problems() fails on two rows with one key and on an entry no
# leaderboard row uses.
FEED_ROWS = {
    # Reading 'GPT-6 Astra', 'GPT-6.1 Sol' (Codex CLI, ChatGPT subscription; ours: ChatGPT subscription).
    "GPT-6 Astra (high)": ("gpt-6-astra", "setting: high"),
    "GPT-6.1 Sol (high)": ("gpt-6.1-sol", "setting: high"),
    # Reading 'Gemini 4 Argon', 'Gemini 3.8 Flash' (Gemini API; ours: Google Antigravity subscription).
    "Gemini 4 Argon (high)": ("gemini-4-argon", "setting: high; route: Google Antigravity subscription"),
    "Gemini 3.8 Flash (high)": ("gemini-3.8-flash", "setting: high; route: Google Antigravity subscription"),
    # Reading 'Claude Fable 5.1', 'Claude Opus 5.5', 'Claude Sonnet 5.5' (Claude Code CLI, Claude subscription).
    "Claude Fable 5.1 (high)": ("claude-fable-5.1", "setting: high"),
    "Claude Opus 5.5 (high)": ("claude-opus-5.5", "setting: high"),
    "Claude Sonnet 5.5 (high)": ("claude-sonnet-5.5", "setting: high"),
    # Reading 'Grok 4.7' (xAI Responses API, SuperGrok subscription; ours: SuperGrok subscription).
    "Grok 4.7 (high)": ("grok-4.7", "setting: high"),
    "DeepSeek-V4.1-Flash (low)": ("deepseek-v4.1-flash", None),
    # Logic & Math, Reading 'Gemma 4 31B' (google/gemma-4-31B-it, self-hosted, FP8).
    "Gemma 4 31B (on)": ("gemma-4-31b", "setting: on"),
    "REAX 1.3": ("reax-1.3", None),
    "Mammoth-1": ("mammoth-1", None),
    # Reading 'Kimi K3.1 Pro' (OpenRouter, Moonshot AI's endpoint, mxfp4; ours the same endpoint).
    "Kimi K3.1 Pro (off)": ("kimi-k3.1-pro", "setting: off"),
    # Logic & Math, Reading 'Qwen3.8-27B' (Qwen/Qwen3.8-27B, self-hosted).
    "Qwen3.8-27B (low)": ("qwen3.8-27b", "setting: low"),
    "Drex Max v1": ("drex-max-v1", None),
    "Drex Max 1.1": ("drex-max-1.1", None),
    "Liquid d1-ultra": ("liquid-d1-ultra", None),
    # Reading 'GLM-5.3' (OpenRouter, Fireworks endpoint; ours: Fireworks via OpenRouter).
    "GLM-5.3 (low)": ("glm-5.3", "setting: low"),
    "Jev 1.14.0": ("jev-1.14.0", None),
    "Fastino GLiDE": ("fastino-glide", None),
    "Jev 1.13.0": ("jev-1.13.0", None),
    "Qwen3.8 Flash (off)": ("qwen3.8-flash", None),
    "Fastino GLiDE v1.2": ("fastino-glide-v1.2", None),
    "Celeris-1 Decision": ("celeris-1-decision", None),
    "Perplexity Decider 27B v1.2 (local GPU)": ("perplexity-decider-27b-v1.2", None),
    "Clef": ("clef", None),
    "Drex 2.0": ("drex-2.0", None),
    "Cygnet": ("cygnet", None),
    # Reading 'Perplexity Decider 27B v1.1' is the Perplexity Decisions API; ours ran on our GPUs.
    "Perplexity Decider 27B v1.1 (local GPU)": (
        "perplexity-decider-27b-v1.1",
        "route: our GPUs (released checkpoint); the other benches' row is the Perplexity Decisions API"),
    "SubQ Snap 1.1": ("subq-snap-1.1", None),
    "GPT-6 Luna (Decisions API)": ("gpt-6-luna", None),
    "SubQ Snap Preview": ("subq-snap-preview", None),
    "Elephant-1": ("elephant-1", None),
    "LFM2.5-24B-A2B (on)": ("lfm2.5-24b-a2b", None),
    "Inception Mercury Decide": ("inception-mercury-decide", None),
    "Winnow-12B": ("winnow-12b", None),
    "Perplexity Decider Flash v1.2": ("perplexity-decider-flash-v1.2", None),
    "Open-Jev 27B v1.1": ("open-jev-27b-v1.1", None),
}
CHECKPOINTS = {
    # Served from snapshot 225c913 (tools/v3/servers/decider-v1.2.sh), Reading's commit.
    "Perplexity Decider 27B v1.2 (local GPU)": ("perplexity-ai/pplx-decider-v1.2",
                                                "225c913ddc8761a8264f04f64548e1f97e443eb3"),
}


def row_key(x) -> str:
    """The row's model_key: frozen in FEED_ROWS, else common.model_key of its shown model name."""
    return FEED_ROWS[x["name"]][0] if x["name"] in FEED_ROWS else model_key(x["model"])


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


def _improvement(S, group: list) -> tuple[float | None, str | None]:
    """(the change in risks found (percentage points, lessons minus no memory) of the row's setup in "Did they
    improve?", once it has a verdict; that model's key), or (None, None)."""
    names = {x["name"] for x in group}
    done = [m for m in ((S["improve"].get("results") or {}).get("models") or [])
            if m["setup"] in names and m["verdict"] and m["change"]["risks_found"] is not None]
    if len(done) > 1:
        raise ValueError(f"bench-scores: several 'Did they improve?' verdicts for one row: {sorted(names)}")
    return (done[0]["change"]["risks_found"], done[0]["key"]) if done else (None, None)


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


def random_of(x, rnd: dict[int, float]) -> float:
    """Random's error rate the row is scored against: its league's Random row; a late entry: Random computed on its own
    scored positions (build.late_entry_summaries, analysis.references), the positions of its own error rate."""
    return x["late"]["random_same_positions"]["error_rate"] if x["late"] else rnd[league_of(x)]


def build(S) -> dict:
    model_rows, prog_rows = ST.leaderboard_rows(S)
    rnd = randoms(prog_rows)
    rows = []
    for x, _, _, group in model_rows:
        m = _meta(S, x)
        q = x["q"] or {}
        p = P.PARAMS[x["model"]]
        repo, commit, quant = _checkpoint(m)
        imp, imp_key = _improvement(S, group)
        lg = league_of(x)
        notes = [f"League {lg}", CALIBRATION_NOTE]
        if x["late"]:
            e = x["late"]
            notes.append(f"late entry: its own decisions in late-entry matches against League {lg}'s field "
                         f"(different positions from the league's); scored against Random computed on those same "
                         f"positions (error rate {e['random_same_positions']['error_rate']:.1f} on "
                         f"{e['random_same_positions']['positions']} positions)")
            # Coverage carried to All benches so a partial entry never reads as complete (Zeki #4657); an entry whose
            # only unplayed pairs are outside the requested scope (Ümit #5220) is complete but keeps its count.
            gone = e.get("not_played") or []
            if e.get("status") == P.PROVISIONAL or gone:
                notes.append(("provisional: " if e.get("status") == P.PROVISIONAL else "")
                             + f"played {e['played']} of {e['total']} matches"
                             + "".join(f"; {unplayed_text(g)}" for g in gone))
            if m.get("notes"):
                notes.append(m["notes"])
        notes.append("run on our GPUs" if m.get("runs_on") == "our GPUs" else "hosted (API or subscription)")
        note = FEED_ROWS.get(x["name"], (None, None))[1]
        name, parts = name_and_tag(x["name"], x["ds"])
        ckpt = CHECKPOINTS.get(x["name"])
        if note:
            notes.append(note)
        if x["name"] in QC_SETUPS:
            notes.append(f"{QC_LABEL}: {QC_SETUPS[x['name']]}")
        if ckpt and repo is None:
            repo, commit = ckpt
        if imp is not None:
            notes.append("improvement_points: change in risks found, percentage points of risk-pays decisions "
                         "(with lessons minus no memory)")
            if imp_key in RUN2:
                notes.append(f"improvement_points from Run 2 after QC; original run {imp:+.2f}, superseded")
                imp = RUN2[imp_key]["run2"]["change"]["risks_found"]
            imp = round(imp, 2)
            if imp_key in QC_IMPROVE:
                notes.append(f"improvement_points {QC_LABEL}: {QC_IMPROVE[imp_key]}")
        rows.append(dict(
            repo=repo, commit=commit, name=name, tag=tag_text(parts), model_key=row_key(x),
            maker=H.maker(x["name"])[0],
            kind=ST.model_type(S, x),
            params_total=p["total_b"], params_active=p["active_b"] if p["moe"] else p["total_b"], quantization=quant,
            score_0_100=score(q.get("error_rate"), random_of(x, rnd)),
            raw=dict(metric=METRIC, value=q.get("error_rate"), questions=q.get("scored"), options=None),
            calibration_error=None, improvement_points=imp, runs=[f"backgammon:{m['slug']}"], notes="; ".join(notes)))
    rows.sort(key=lambda r: (r["score_0_100"] is None, -(r["score_0_100"] or 0), r["name"]))
    per = ", ".join(f"League {k}: {v:.1f}" for k, v in sorted(rnd.items()))
    return dict(
        bench="backgammon", title="Backgammon", url=S["base"], updated=S["as_of"],
        score=dict(zero=f"0 = a random legal play's error rate on the same positions ({per}; a late entry: Random "
                        "computed on its own positions against the field it played); below 0 = worse than a random "
                        "legal play. score = 100 × (1 − error rate / Random's error rate on those positions); error "
                        "rate (PR) = 500 × mean GNUbg equity "
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
    expect = {row_key(x): ((x["q"] or {}).get("error_rate"), league_of(x), name_and_tag(x["name"], x["ds"]),
                           random_of(x, rnd)) for x, *_ in model_rows}
    if len(expect) != len(model_rows):
        out.append(f"{PATH}: two leaderboard model rows with one model_key")
    unused = sorted((set(FEED_ROWS) | set(CHECKPOINTS)) - {x["name"] for x, *_ in model_rows})
    if unused:
        out.append(f"{PATH}: FEED_ROWS/CHECKPOINTS entries for no leaderboard model row: {unused}")
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    opt = lambda v, t: v is None or t(v)
    for r in doc["models"]:
        name = r.get("name") if isinstance(r, dict) else None
        if not isinstance(r, dict) or set(r) != ROW_KEYS or not isinstance(r["raw"], dict) or set(r["raw"]) != RAW_KEYS:
            out.append(f"{PATH}: row {name!r}: keys are not the schema's")
            continue
        raw = r["raw"]
        types = [isinstance(name, str), isinstance(r["tag"], str),
                 isinstance(r["model_key"], str) and bool(KEY_OK.match(r["model_key"])),
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
        key = r["model_key"]
        if key not in expect:
            continue
        er, lg, (want_name, parts), base = expect[key]
        if (name, r["tag"]) != (want_name, tag_text(parts)):
            out.append(f"{PATH}: row {key!r}: name and tag {name!r} / {r['tag']!r}, the site shows {want_name!r} / "
                       f"{tag_text(parts)!r}")
        want = score(er, base)
        if raw["value"] != er or not r["notes"].startswith(f"League {lg};") or (want is None) != (
                r["score_0_100"] is None) or (want is not None and want != r["score_0_100"]):
            out.append(f"{PATH}: row {key!r}: score {r['score_0_100']} / error rate {raw['value']}, the leaderboard's "
                       f"error rate {er} against its Random ({base}) gives {want}")
        if r["improvement_points"] is not None and r["improvement_points"] != round(r["improvement_points"], 2):
            out.append(f"{PATH}: row {key!r}: improvement_points not rounded to 2 decimals")
    keys = sorted(r.get("model_key") for r in doc["models"] if isinstance(r, dict))
    want = sorted(expect)
    if keys != want:
        out.append(f"{PATH}: rows {keys} are not the leaderboard's model rows {want}")
    return out