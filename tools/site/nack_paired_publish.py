#!/usr/bin/env python3
"""Nackgammon paired test: the site's data file from the scorer's output (Method spec 2026-10-24 §10).

    python3 tools/site/nack_paired_publish.py [RESULTS_JSON] [OUT_JSON]

RESULTS_JSON defaults to positions/nack-paired/results/results.json (tools/v3/nack_paired_score.py report);
OUT_JSON to tools/site/content/nack_paired_results.json. Only aggregates are kept: no per-position answers, no answer
text, no logs, no paths. Cost is per 1,000 decisions (billed and API-equivalent kept apart). build() is also what
nack_paired_verify.py uses to rederive the data file from results.json and from a fresh recomputation.
"""

import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent.parent
CONTENT = SITE / "content"
RESULTS = ROOT / "positions/nack-paired/results/results.json"
OUT = CONTENT / "nack_paired_results.json"

GROUP_ORDER = ["decision models", "workhorses", "frontier", "no group (exploratory)", "yardstick"]
LOOK = ("pairs", "standard_pr", "nackgammon_pr", "drop", "drop_975", "drop_95")


def _cost(c: dict | None) -> dict | None:
    if not c:
        return None
    return dict(decisions=c["decisions"], billed_usd_per_1000=round(1000 * c["billed_usd_per_decision"], 3),
                api_eq_usd_per_1000=round(1000 * c["api_eq_usd_per_decision"], 3))


def _risk(r: dict | None) -> dict | None:
    if not r:
        return None
    return {k: r[k] for k in ("standard", "nackgammon", "change", "thin")}


def build(R: dict) -> dict:
    """The published aggregates of a results.json (pure function of it)."""
    names = sorted(R["setups"], key=lambda s: (GROUP_ORDER.index(R["setups"][s]["group"]),
                                               R["setups"][s]["first_look"]["standard_pr"], s))
    setups = {}
    for s in names:
        r = R["setups"][s]
        ph = r["phases"]
        setups[s] = dict(
            group=r["group"],
            first={k: r["first_look"][k] for k in LOOK},
            final={k: r["final_look"][k] for k in LOOK},
            extend_at_first_look=r["first_look"]["extend"], extended=r["extended"],
            extension_incomplete=r.get("extension_incomplete"), label=r["label"],
            invalid=dict(first=r["first_look"]["invalid"], final=r["final_look"]["invalid"]),
            sensitivity=r["sensitivity_first"],
            phases={p: v for p, v in ph.items() if p != "opening minus other phases"},
            opening_vs_rest=ph["opening minus other phases"],
            tags=r["tags"],
            cost=dict(main=_cost(r.get("cost_main")), all=_cost(r.get("cost_all"))) if s != "Random" else None,
            risk=dict(main=_risk(r.get("risk_main")), all=_risk(r.get("risk_all"))))
    incomplete = any(v["extension_incomplete"] for v in setups.values()) or any(
        c.get("missing") for c in R["primary"]["random"])
    out = dict(
        title="Nackgammon paired test", method="Method spec 2026-10-24 §10 (groups: §10.14)",
        scope_note=R["scope_note"], groups_rule=R["groups_rule"], frontier_note=R["frontier_note"],
        in_progress=incomplete, primary_level=0.99, comparisons=5, intervals_first_final=0.975, interval_descriptive=0.95,
        groups=R["groups"], setups=setups,
        primary={rule: [{k: v for k, v in c.items()} for c in R["primary"][rule]] for rule in ("random", "worst", "drop")},
        secondary=dict(kept_advantage=R["kept_advantage"], kept_advantage_all_500=R.get("kept_advantage_all_500"),
                       spearman=R["spearman"]),
        engine_check=R.get("engine_check"),
        chart=[dict(setup=s, group=v["group"], standard_pr=v["first"]["standard_pr"],
                    nackgammon_pr=v["first"]["nackgammon_pr"]) for s, v in setups.items()])
    return out


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    out = build(json.loads(src.read_text()))
    dst.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{dst}: {len(out['setups'])} setups; {'in progress' if out['in_progress'] else 'complete'}; "
          f"engine check {'present' if out['engine_check'] else 'not yet'}")


if __name__ == "__main__":
    main()
