#!/usr/bin/env python3
"""Close choices, stage B: the site's data file from the scorer's output (Method spec 2026-10-24 §9.9-9.13).

    python3 tools/site/close_choices_b_publish.py SCORE_JSON [OUT_JSON]

SCORE_JSON is the output of close_choices_b_score.py; OUT_JSON defaults to tools/site/content/close_choices_b_results.json.
Teams are the players of the stage B configs (leagues/close-choices-b*.json) except NOT_REPORTED (Gemma 4 31B (on), stopped
before its run was complete: no entry at all). Only aggregates are kept (no per-position sets). Every published team must
be complete (scored, no call left unasked), else the script stops. Setting and temperature come from Method §9.12's team
table, parsed from the spec.
"""

import argparse
import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent.parent
CONTENT = SITE / "content"
SPEC = CONTENT / "method-spec-2026-10-24.md"
CONFIGS = [ROOT / "leagues/close-choices-b.json", ROOT / "leagues/close-choices-b-gemma.json"]
CC = json.loads((CONTENT / "close_choices_2026-10-24.json").read_text())["stage_b"]

# Ümit, 2026-10-25: Gemma 4 31B (on) was stopped before its run was complete; it is not reported (no entry here).
NOT_REPORTED = {"Gemma 4 31B (on)"}
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def spec_settings() -> dict:
    """Team -> (setting, temperature text) from the table of Method §9.12."""
    text = SPEC.read_text()
    sec = text[text.index("### 9.12"):text.index("### 9.13")]
    out = {}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0] not in ("Team", "---") and not set(cells[0]) <= {"-", " "}:
            out[cells[0]] = (cells[5], cells[6])
    return out


def temperature(text: str) -> dict:
    if "not disclosed" in text:
        return dict(known=False, value=None, text=text)
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        raise SystemExit(f"temperature not readable: {text!r}")
    return dict(known=True, value=m.group(0), text=text)


def vs_baseline(s: dict) -> str:
    """Where the observed mean sits against the baseline's 2.5-97.5 percentile range."""
    if s["observed"] > s["baseline_hi"]:
        return "above"
    if s["observed"] < s["baseline_lo"]:
        return "below"
    return "within"


def score(s: dict) -> dict:
    return dict(observed=s["observed"], baseline_mean=s["baseline_mean"], baseline_lo=s["baseline_lo"],
                baseline_hi=s["baseline_hi"], p=s["share_baseline_at_least_observed"], vs_baseline=vs_baseline(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("score")
    ap.add_argument("out", nargs="?", default=str(CONTENT / "close_choices_b_results.json"))
    args = ap.parse_args()
    scores = json.loads(Path(args.score).read_text())
    players = {p["name"]: p for cfg in CONFIGS for p in json.loads(cfg.read_text())["players"]}
    settings = spec_settings()
    unknown = set(scores) - set(players)
    if unknown:
        raise SystemExit(f"not a stage B team: {sorted(unknown)}")
    complete = []
    for team in sorted(set(players) - NOT_REPORTED):
        s = scores.get(team)
        if s is None or not s["scored"] or "primary_exact" not in s or any("not asked" in r for r in s["excluded"]):
            raise SystemExit(f"{team}: run not complete in {args.score}; not publishable")
        setting, temp = settings[team]
        complete.append(dict(
            team=team, setting=setting, temperature=temperature(temp),
            positions=s["positions"], scored=s["scored"], exact_n=s["exact_n"],
            excluded={k: v["n"] for k, v in s["excluded"].items()}, excluded_positions=s["excluded_positions"],
            primary_exact=score(s["primary_exact"]), secondary_overlap=score(s["secondary_overlap"]),
            same_play=s["same_play"], changed_same_features=s["changed_same_features"],
            observed_nonempty=s["observed_nonempty"], predicted_size_mean=s["predicted_size_mean"],
            deterministic=s["deterministic"]))
    out = dict(
        title=f"Stage B: {WORDS[len(complete)]} teams" if len(complete) < len(WORDS) else f"Stage B: {len(complete):,} teams",
        method="Method spec 2026-10-24 §9.9-9.13", score_file=Path(args.score).name,
        positions=CC["positions"], repeats=CC["repeats"], baseline_shuffles=CC["baseline_shuffles"],
        complete=complete)
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{args.out}: {len(complete)} teams ({', '.join(t['team'] for t in complete)}); "
          f"not reported: {', '.join(sorted(NOT_REPORTED))}")


if __name__ == "__main__":
    main()
