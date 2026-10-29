#!/usr/bin/env python3
"""Nackgammon paired test: the site's data file from the scorer's output (Method spec 2026-10-24 §10).

    python3 tools/site/nack_paired_publish.py [RESULTS_JSON] [OUT_JSON]

RESULTS_JSON defaults to positions/nack-paired/results-2026-10-28/results.json (tools/v3/nack_paired_score.py report,
with the §10.14(g) Cup-roster additions and the §10.14(h) exploratory setup); OUT_JSON to
tools/site/content/nack_paired_results.json. Only aggregates are kept: no per-position answers, no answer text, no
logs, no paths. Cost is per 1,000 decisions (recorded cost and API-equivalent kept apart). Setups carry their shown
names (content/labels.json), the databases' names as "aliases". build() is also what nack_paired_verify.py uses to
rederive the data file from results.json and from a fresh recomputation.
"""

import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent.parent
CONTENT = SITE / "content"
RESULTS = ROOT / "positions/nack-paired/results-2026-10-28/results.json"
OUT = CONTENT / "nack_paired_results.json"
sys.path.insert(0, str(SITE))

from common import RENAMED, aliases, relabel  # noqa: E402

GROUP_ORDER = ["decision models", "workhorses", "frontier", "no group (exploratory)", "yardstick"]
LOOK = ("pairs", "standard_pr", "nackgammon_pr", "drop", "drop_975", "drop_95")
RULES = ("random", "worst", "drop", "cutoff")
OUTPUT_LIMIT = 32768


def _cost(c: dict | None) -> dict | None:
    if not c:
        return None
    return dict(decisions=c["decisions"], billed_usd_per_1000=round(1000 * c["billed_usd_per_decision"], 3),
                api_eq_usd_per_1000=round(1000 * c["api_eq_usd_per_decision"], 3))


def _risk(r: dict | None) -> dict | None:
    if not r:
        return None
    return {k: r[k] for k in ("standard", "nackgammon", "change", "thin")}


COST_NOTE = ("Recorded cost (the field billed_usd_per_1000) is the cost stored with each answer: the provider's reported "
             "cost per response where the route reports one, otherwise the runner's list-price computation (Mercury "
             "Decide: list price; its provider-billed amount was not retained and is unknown). No invoice was checked. "
             "API-equivalent is a subscription setup priced at list price, not money paid. Setups on our GPUs have no "
             "list price.")


def _text(s: str) -> str:
    """A scorer sentence with the setups it names under their shown names (the scorer writes the databases' names).
    The §10.14(h) note shortens the dropped "Gemini 4 Argon (on)" to "Argon (on)"."""
    for old in sorted(RENAMED, key=len, reverse=True):
        s = s.replace(old, RENAMED[old])
    return s.replace("instead of Argon (on)", f"instead of {RENAMED['Gemini 4 Argon (on)']}")


def shown(R: dict) -> dict:
    """results.json under the shown names: exact names (keys, members, rank lists) and the notes that name setups."""
    R = relabel(R)
    R["frontier_note"] = _text(R["frontier_note"])
    R["exploratory"] = {s: _text(v) for s, v in R.get("exploratory", {}).items()}
    for key in ("primary", "primary_original_members"):
        for cs in R[key].values():
            for c in cs:
                c["comparison"] = _text(c["comparison"])
    for key in ("primary", "primary_original_members"):
        for c in (R.get("engine_check") or {}).get(key, []):
            c["comparison"] = _text(c["comparison"])
    return R


def _names(xs: list) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def missing_note(setups: dict) -> str:
    """The positions recorded without a valid choice, main versus final, from the saved counts (no rescoring)."""
    parts = []
    for s, v in setups.items():
        f, m = v["invalid"]["final"], v["invalid"]["first"]
        tot, main = f["standard"] + f["nackgammon"], m["standard"] + m["nackgammon"]
        if tot:
            parts.append(f"{s}: {tot:,} positions recorded without a valid choice (timeouts or missing choices), "
                         f"{main:,} in the main 200 pairs and {tot - main:,} in the reserve; on its final "
                         f"{v['final']['pairs']} pairs {f['standard']} standard / {f['nackgammon']} Nackgammon")
    if not parts:
        return "Every asked setup gave a valid choice on every recorded position."
    return ("; ".join(parts) + ". They are not answers: each is scored by the primary rule (the position's Random "
            "error), with both sensitivity checks below. Every other asked setup gave a valid choice on every recorded "
            "position.")


def limit_note(setups: dict) -> str:
    """Output-limit flags (§10.14(h)), from the saved counts: answers cut off at the limit, and answers past 32,768
    output tokens from runs that sent no limit."""
    cut, past = [], []
    for s, v in setups.items():
        for flag, into in (("cut_off", cut), ("past_32768_no_limit_sent", past)):
            c = v.get(flag)
            if c and c["all"]["standard"] + c["all"]["nackgammon"]:
                a, m = c["all"], c["main"]
                into.append(f"{s}, {a['standard'] + a['nackgammon']:,} of its recorded positions "
                            f"({a['standard']} standard / {a['nackgammon']} Nackgammon), {m['standard'] + m['nackgammon']:,}"
                            f" in the main 200 pairs")
    text = (f"Output limit (\u00a710.14(h)): an answer cut off at {OUTPUT_LIMIT:,} output tokens counts as invalid, "
            "with its own sensitivity check (cut-off pairs left out). ")
    text += ("Cut off at the limit: " + "; ".join(cut) + ". ") if cut else "No recorded answer was cut off at the limit. "
    if past:
        text += (f"Past {OUTPUT_LIMIT:,} output tokens from a run that sent no limit (flagged; the answers keep their "
                 "scores): " + "; ".join(past) + ".")
    return text.strip()


def build(R: dict) -> dict:
    """The published aggregates of a results.json (pure function of it)."""
    R = shown(R)
    orig = {s for m in R["groups_original_members"].values() for s in m}
    added = [s for g in GROUP_ORDER if g in R["groups"] for s in R["groups"][g] if s not in orig]
    names = sorted(R["setups"], key=lambda s: (GROUP_ORDER.index(R["setups"][s]["group"]),
                                               R["setups"][s]["first_look"]["standard_pr"], s))
    setups = {}
    for s in names:
        r = R["setups"][s]
        ph = r["phases"]
        setups[s] = dict(
            group=r["group"], aliases=aliases(s), added=s in added,
            first={k: r["first_look"][k] for k in LOOK},
            final={k: r["final_look"][k] for k in LOOK},
            extend_at_first_look=r["first_look"]["extend"], extended=r["extended"],
            extension_incomplete=r.get("extension_incomplete"), label=r["label"],
            invalid=dict(first=r["first_look"]["invalid"], final=r["final_look"]["invalid"]),
            cut_off=r.get("cut_off"), past_32768_no_limit_sent=r.get("past_32768_no_limit_sent"),
            sensitivity=r["sensitivity_first"], sensitivity_final_cutoff=r.get("sensitivity_final_cutoff"),
            phases={p: v for p, v in ph.items() if p != "opening minus other phases"},
            opening_vs_rest=ph["opening minus other phases"],
            tags=r["tags"],
            cost=dict(main=_cost(r.get("cost_main")), all=_cost(r.get("cost_all"))) if s != "Random" else None,
            risk=dict(main=_risk(r.get("risk_main")), all=_risk(r.get("risk_all"))))
    incomplete = any(v["extension_incomplete"] for v in setups.values()) or any(
        c.get("missing") for key in ("primary", "primary_original_members") for c in R[key]["random"])
    by_group = {g: [s for s in added if R["setups"][s]["group"] == g] for g in GROUP_ORDER}
    additions_note = (
        "Added under \u00a710.14(g) after this test's results had been computed and read: "
        + "; ".join(f"{_names(xs)} ({g})" for g, xs in by_group.items() if xs)
        + ". They follow the Cup roster, not the results. The primary comparisons are shown both ways: with the "
          "additions (the primary result, \u00a710.14(b)) and with the original members only "
          f"({len(orig)} setups, \u00a710.14(d)).")
    fr = R["groups_original_members"]["frontier"]
    out = dict(
        title="Nackgammon paired test", method="Method spec 2026-10-24 \u00a710 (groups: \u00a710.14)",
        scope_note=R["scope_note"], groups_rule=R["groups_rule"], frontier_note=R["frontier_note"],
        frontier_note_original_members=(f"Original members only: the frontier group has {len(fr)} "
                                        f"setup{'s' if len(fr) != 1 else ''} ({', '.join(fr)}); comparisons 2 and 3 "
                                        f"rest on {'them' if len(fr) != 1 else 'it'}."),
        in_progress=incomplete, primary_level=0.99, comparisons=5, intervals_first_final=0.975, interval_descriptive=0.95,
        groups=R["groups"], groups_original_members=R["groups_original_members"], additions=added,
        additions_note=additions_note, exploratory=R["exploratory"],
        setups=setups, cost_note=COST_NOTE, missing_note=missing_note(setups), limit_note=limit_note(setups),
        primary={rule: [dict(c) for c in R["primary"][rule]] for rule in RULES},
        primary_original_members={rule: [dict(c) for c in R["primary_original_members"][rule]] for rule in RULES},
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
