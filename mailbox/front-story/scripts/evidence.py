"""Evidence for the front page's finding headings (Ümit, bus #2570 item 3; Zeki #2578): each heading checked against the
published data files of the live site, one Markdown file per heading, plus the headline table's selection and the
release months. Reads only; numbers are copied from the files, not recomputed.
Usage: evidence.py LIVE_SITE_DIR TOOLS_SITE_DIR OUT_DIR"""
import json
import re
import sys
from pathlib import Path

site, tools, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
data = site / "data"
manifest = json.loads((data / "manifest.json").read_text())
CR = json.loads((data / "v3" / "clear-risk.json").read_text())
LG = [json.loads((data / "v3" / f"league-{i}.json").read_text()) for i in (1, 2, 3)]
META = {(m["dataset"], m["name"]): m for m in json.loads((data / "setups.json").read_text())["setups"]}
REL = json.loads((tools / "content" / "release_months.json").read_text())["models"]
PROGRAMS = ("GNUbg weak", "Random", "Safest")
SRC = (f"Source: the live site's published data files (results {manifest['results']}, data as of {manifest['data_as_of']}): "
       "{files}. Read-only; every number below is copied from those files as printed.")
num = lambda s: float(s.replace("\u2212", "-").replace("pp", "").replace("+", "").strip())

# 1. Models are too cautious --------------------------------------------------------------------------------------
sec = next(s for s in CR["sections"] if s["id"] == "clear-risk-setups")
rows = []
for t in sec["tables"]:
    lg = re.match(r"League (\d)", t["caption"]).group(1)
    i = t["head"].index("bias = missed \u2212 needless")
    for r in t["rows"]:
        if "(reference)" in r[0] or "(expected)" in r[0]:
            continue
        rows.append((lg, r[0], r[2], r[5], r[i], num(r[i]), r[0] in PROGRAMS))
models = [r for r in rows if not r[6]]
progs = [r for r in rows if r[6]]
ok = all(r[5] > 0 for r in models)
neg = [r for r in progs if r[5] < 0]
L = ["# Heading: \"Models are too cautious\"", "",
     SRC.format(files="data/v3/clear-risk.json, section clear-risk-setups (\"Missed and needless risks per setup\", kept "
                      "decisions only)"), "",
     "Claim checked: in the clear-risk scan, bias = missed \u2212 needless is positive for every model setup, and not for "
     "the programs.", "",
     f"Result: **{'holds' if ok else 'does NOT hold'}**. {len(models)} model setups, all with a positive bias (lowest "
     f"{min(models, key=lambda r: r[5])[4]}, {min(models, key=lambda r: r[5])[1]}, League {min(models, key=lambda r: r[5])[0]}; "
     f"highest {max(models, key=lambda r: r[5])[4]}, {max(models, key=lambda r: r[5])[1]}, League "
     f"{max(models, key=lambda r: r[5])[0]}). Programs: {len(neg)} of {len(progs)} rows negative "
     f"({', '.join(f'{r[1]} L{r[0]} {r[4]}' for r in neg)}); Safest is +100 by construction (it never plays an unsafe "
     "play), which the page says.", "",
     "Scope: kept clear-risk decisions only (the scan's 2-ply/3-ply stability rule), not every league decision; setups "
     "met different positions (not paired). The page shows this as the section's one caveat.", "",
     "| League | Setup | Missed risks | Needless risks | Bias | Program |", "|---|---|---|---|---:|---|"]
L += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {'yes' if r[6] else ''} |" for r in sorted(rows, key=lambda r: (r[6], -r[5]))]
(out / "1-models-are-too-cautious.md").write_text("\n".join(L) + "\n")

# 2. Numbers on screen --------------------------------------------------------------------------------------------
sec = next(s for s in CR["sections"] if s["id"] == "clear-risk-part2")
t = next(t for t in sec["tables"] if t["caption"].startswith("Q1"))
h = t["head"]
by = {}
for r in t["rows"]:
    by.setdefault(r[0], {})[r[1]] = r
L = ["# Heading asked for: \"A number on screen makes models flinch\"", "",
     SRC.format(files="data/v3/clear-risk.json, section clear-risk-part2, table \"Q1: share right per group, missed and "
                      "needless, bias (two plays shown, not league play)\""), "",
     "Claim checked: on Q1 (best safe vs best unsafe play, the same 189 rollout-confirmed positions asked twice), each "
     "model's bias is higher (more cautious) with numbers than board only.", ""]
diffs = []
for m, v in by.items():
    a, b = v["with numbers"], v["board only"]
    diffs.append((m, a[h.index("missed (Risk wins \u2192 safe)")], b[h.index("missed (Risk wins \u2192 safe)")],
                  a[h.index("needless (Safety wins \u2192 unsafe)")], b[h.index("needless (Safety wins \u2192 unsafe)")],
                  a[h.index("bias")], b[h.index("bias")], num(a[h.index("bias")]) - num(b[h.index("bias")])))
all_ = all(d[7] > 0 for d in diffs)
L += [f"Result: direction **{'consistent' if all_ else 'NOT consistent'}**: {sum(d[7] > 0 for d in diffs)} of "
      f"{len(diffs)} models have a higher bias with numbers (differences {min(d[7] for d in diffs):+.0f} to "
      f"{max(d[7] for d in diffs):+.0f} pp, as the difference of the two printed biases). Board only, "
      f"{sum(num(d[6]) < 0 for d in diffs)} models have a negative bias.", "",
     "Wording on the page: \"With the numbers on screen, every model asked played safer\". It says what the two "
     "versions showed. The asked-for \"makes models flinch\" is causal; the comparison does hold the positions fixed "
     "(each model answered both versions of the same items), but no test of the difference is published and Zeki "
     "(bus #2578) asked for no new statistics, so the heading reports the observed direction only. 8 models, 189 "
     "positions, two plays shown (not league play): the section's caveat.", "",
     "| Model | Missed, with numbers | Missed, board only | Needless, with numbers | Needless, board only | Bias, with numbers | Bias, board only | Difference (pp) |",
     "|---|---|---|---|---|---:|---:|---:|"]
L += [f"| {d[0]} | {d[1]} | {d[2]} | {d[3]} | {d[4]} | {d[5]} | {d[6]} | {d[7]:+.0f} |" for d in diffs]
(out / "2-numbers-on-screen.md").write_text("\n".join(L) + "\n")

def weights_of(ds, name, model):
    """The setup's weights from setups.json: its own entry, else the same name in another league (a setup that moved by
    a ladder move is listed under the league it came from), else any entry of the same model."""
    m = META.get((ds, name)) or next((v for (d, n), v in META.items() if n == name), None) or next(
        (v for v in META.values() if v["model"] == model and v.get("weights")), None)
    return (m or {}).get("weights")


# 3. Thinking -----------------------------------------------------------------------------------------------------
pairs = []
for lg in LG:
    for r in lg["reasoning"]:
        w = weights_of(lg["dataset"], r["high"], r["model"])
        pairs.append((lg["id"], r["model"], w, r["low_setting"], r["high_setting"], r["reading"], r["risk"]["change"],
                      r["risk"]["overlap"]))
opn = [p for p in pairs if p[2] == "open"]
cls = [p for p in pairs if p[2] != "open"]
L = ["# Heading asked for: \"Thinking helps open models, not frontier ones\"", "",
     SRC.format(files="data/v3/league-1.json, league-2.json, league-3.json (\"reasoning\": every model with two "
                      "reasoning settings in that league's games) and data/setups.json (weights)"), "",
     f"Pairs: {len(pairs)} ({len(opn)} open weights, {len(cls)} closed). Error-rate reading as published on the "
     "Reasoning tab; risk-judgement change = higher setting minus lower; overlap of the two risk-judgement intervals as "
     "published.", "",
     "| League | Model | Weights | Settings | Error rate, in league play | Risk judgement change | Intervals overlap |",
     "|---|---|---|---|---|---:|---|"]
L += [f"| {p[0]} | {p[1]} | {p[2]} | {p[3]} \u2192 {p[4]} | {p[5]} | {p[6]:+.1f} | {'yes' if p[7] else 'no'} |" for p in pairs]
L += ["", "Result: **not shown on the page**.",
      f"- Open weights: {sum(p[5].startswith('lower') for p in opn)} of {len(opn)} read \"lower error rate in league "
      f"play\" ({', '.join(p[1] for p in opn if p[5].startswith('lower'))}); "
      f"{', '.join(p[1] for p in opn if not p[5].startswith('lower'))}: no clear difference.",
      f"- Closed weights: {sum(p[5].startswith('lower') for p in cls)} of {len(cls)} read lower error rate; in risk "
      f"judgement, {', '.join(p[1] for p in cls if not p[7]) or 'none'} has intervals that do not overlap.",
      "- \"Frontier\" (League 3, the frontier chat models): all four pairs no clear difference.",
      "- The pattern \"open models gain, frontier ones do not\" is in these rows only partly (one of three open models "
      "shows nothing; one closed non-frontier model moves in risk judgement), and the Reasoning tab itself says the "
      "comparison \"is not paired and shows no effect of the setting: a higher or lower value at the higher setting is "
      "not evidence that reasoning caused it\"; whether two intervals overlap \"describes them; it is not a test of a "
      "difference\" (Zeki #2578 likewise). A heading saying thinking helps (or does not help) would claim an effect the "
      "data cannot show. Dropped, as the brief allows (\"reword or drop\"); the Reasoning tab keeps the table."]
(out / "3-thinking-dropped.md").write_text("\n".join(L) + "\n")

# Headline table selection and release months ----------------------------------------------------------------------
by_model = {}
for lg in LG:
    for n, s in lg["setups"].items():
        m = (META.get((lg["dataset"], n)) or {}).get("model") or n
        if m in PROGRAMS or (META.get((lg["dataset"], n)) or {}).get("model_type") == "program":
            continue
        r = s["risk"]["main"]
        by_model.setdefault(m, []).append((r["judgement"], n, lg["id"]))
L = ["# Headline table: one row per model, its setting with the highest stored risk judgement", "",
     SRC.format(files="data/v3/league-N.json (risk.main.judgement per setup) and data/setups.json (model)"), "",
     "Each row is ONE named setup, the model's setting with the highest stored risk judgement (Zeki #2578): every cell "
     "of the row (risk judgement and interval, risks found, right safety, error rate, cost) is that setup's own; the "
     "model's other settings are under All setups. A selection for display, not a separate run.", "",
     "| Model | Shown setup (league) | Its risk judgement | Other settings: risk judgement |", "|---|---|---:|---|"]
for m, v in sorted(by_model.items(), key=lambda x: -max(j or -1 for j, _, _ in x[1])):
    v = sorted(v, key=lambda x: -(x[0] if x[0] is not None else -1))
    j, n, lid = v[0]
    L.append(f"| {m} | {n} (L{lid}) | {j:.1f} | {'; '.join(f'{nn} (L{ll}) {jj:.1f}' for jj, nn, ll in v[1:] if jj is not None) or '—'} |")
L += ["", "## Release months (column Released)", "",
      "From the maker's own page, read on 2026-11-07, quote copied verbatim (tools/site/content/release_months.json). "
      "\u2014 where no official dated statement for the exact model name was found:", "",
      "| Model | Month | Source |", "|---|---|---|"]
for m in sorted(by_model):
    e = REL.get(m) or {}
    L.append(f"| {m} | {e.get('month') or '\u2014'} | {e.get('url') or (e.get('note') or 'no entry')} |")
(out / "4-headline-selection-and-release-months.md").write_text("\n".join(L) + "\n")
print("written", sorted(p.name for p in out.iterdir()))
