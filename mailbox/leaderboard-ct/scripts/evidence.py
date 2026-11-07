"""leaderboard-ct evidence (Ümit #2745): the per-model setting choice, re-derived here from the branch render's published
data files (data/setups.json, data/v3/league-N.json, data/v3/late-entries.json) by an implementation independent of
story.py, then compared with the rendered table; the maker colours. Reads only.
    evidence.py WORKTREE BRANCH_RENDER_DIR OUT_DIR
Writes OUT_DIR/1-setting-choice.md, 2-maker-colours.md, 3-late-entries-question.md and prints PASS/FAIL lines."""
import json
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

work, render, out = (Path(a) for a in sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
data = render / "data"
meta = json.loads((data / "setups.json").read_text())["setups"]
leagues = [json.loads((data / "v3" / f"league-{i}.json").read_text()) for i in (1, 2, 3)]
late = json.loads((data / "v3" / "late-entries.json").read_text())
ORDER = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]
RANK = {"none": 0, **{s: i for i, s in enumerate(ORDER)}}
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")


def entry(ds, name):
    m = [x for x in meta if x["name"] == name and x["dataset"] == ds]
    return m[0] if m else next(x for x in meta if x["name"] == name and x["dataset"].startswith("league-"))


# Every league setup with its stored judgement, in the All leagues order: judgement descending, ties kept in league
# order and each league's own order (judgement descending, then name).
rows = []
for lg in leagues:
    own = sorted(((n, s) for n, s in lg["setups"].items()), key=lambda x: (x[1]["risk"]["main"]["judgement"] is None,
                                                                            -(x[1]["risk"]["main"]["judgement"] or 0), x[0]))
    for n, s in own:
        m = entry(lg["dataset"], n)
        if m["model_type"] == "program":
            continue
        rows.append(dict(ds=lg["dataset"], lid=lg["id"], name=n, slug=s["slug"], model=m["model"], setting=m["setting"],
                         j=s["risk"]["main"]["judgement"]))
rows.sort(key=lambda x: (x["j"] is None, -(x["j"] or 0)))
models = {x["model"] for x in rows}


def base(m):
    c = re.match(r"^(.+) (\d{4})$", m)
    return c.group(1) if c and c.group(1) in models else m


def rank(s, levelled):
    if s is None:
        return 0
    if s == "on":
        assert not levelled, "on with levels"
        return 1
    return RANK[s]


groups = {}
for x in rows:
    groups.setdefault(base(x["model"]), []).append(x)
chosen, lines = {}, []
for b, g in groups.items():
    levelled = any(x["setting"] not in (None, "on", "off", "none") for x in g)
    top = max(rank(x["setting"], levelled) for x in g)
    cands = [x for x in g if rank(x["setting"], levelled) == top]
    cands = [x for x in cands if x["model"] == b] or cands
    pick = cands[0]
    for x in cands[1:]:
        if x["j"] is not None and (pick["j"] is None or x["j"] > pick["j"]):
            pick = x
    chosen[b] = pick
    best = max(g, key=lambda x: x["j"] or -1)
    at_top = [x for x in g if rank(x["setting"], levelled) == top]
    why = ("single setup" if len(g) == 1 else
           "decision model, no setting sent" if pick["setting"] is None and len(cands) == 1 else
           f"highest setting played: {pick['setting']}"
           + (f"; at it also {', '.join(x['name'] for x in at_top if x is not pick)} (dated checkpoint): the original's setup"
              if any(x["model"] != b for x in at_top) else "")
           + (f"; {len(cands)} setups at it: the higher stored judgement" if len(cands) > 1 else ""))
    lines.append((b, g, pick, why, best))

# The rendered table: its ranked rows in order, against the re-derived choice ranked by judgement (then name).
html = BeautifulSoup((render / "index.html").read_text(), "html.parser")
table = html.select_one("#headline-table")
shown = [(tr["data-dataset"], tr["data-setup"]) for tr in table.tbody.find_all("tr", recursive=False)
         if tr.get("data-setup") and not set(tr.get("class") or []) & {"hl-sub", "reference", "late"}]
expect = [(x["ds"], x["slug"]) for x in sorted(chosen.values(), key=lambda x: (x["j"] is None, -(x["j"] or 0),
                                                                                next(b for b in chosen if chosen[b] is x)))]
check("ranked rows = re-derived choice, in rank order", shown == expect, f"{len(shown)} rows shown, {len(expect)} expected")
subs = [(tr["data-dataset"], tr["data-setup"]) for tr in table.select("tr.hl-sub") if "reference" not in (tr.get("class") or [])
        and "late" not in (tr.get("class") or [])]
check("every other league setup of a model is under its row's expander, once",
      sorted(subs + shown) == sorted((x["ds"], x["slug"]) for x in rows), f"{len(subs)} other-setting rows")
progs = [(tr["data-dataset"], tr["data-setup"]) for tr in table.select("tr.reference:not(.hl-sub)")]
check("programs: one grey unranked row each (GNUbg weak, Safest, Random), League 1 (the played setup; best_per_model's "
      "rule over the played setups)", [p[1] for p in progs] == ["gnubg-weak", "safest", "random"]
      and all(p[0] == "league-1" for p in progs), str(progs))
check("no late-entry row (LATE_ROWS off)", not table.select('tr[data-dataset="late-entry"]'))
note = html.select_one("#leaderboard [data-headline-panel=model] .section-caveat").get_text(" ")
check("note under the table", note.startswith("Bars run to each score; the whisker is its 95% interval. Ranks show "
                                                "observed scores; small gaps need not be meaningful. Leagues played "
                                                "different positions."), note)
check("no whisker-overlap sentence anywhere on the page", "not reliably ordered" not in html.get_text(" "))

md = ["# 1. Setting choice per model (Ümit #2745 item 1)", "",
      "Re-derived by `scripts/evidence.py` from the branch render's data files (data/setups.json `setting`, the sent "
      "effort; data/v3/league-N.json stored risk judgements), independently of story.py, and compared with the "
      "rendered table: " + ("**all checks pass**." if not fails else f"**{fails} check(s) fail**."), "",
      "## The rule", "",
      "- Order of the sent effort: none = off < minimal < low < medium < high < xhigh < max.",
      "- `on`: the setting of a model with no levels (thinking on/off only: LFM2.5-24B-A2B, Gemma 4 31B); above off. "
      "A model with both `on` and a level fails the build (none has).",
      "- Decision models send no setting: their single setup.",
      "- Version names are separate models (Jev 1.13.0 / Jev 1.14.0; Decider v1.1 / v1.2; Fastino GLiDE / GLiDE v1.2).",
      "- A dated checkpoint (`<model> MMDD`, the base name a model in the standings) is the same model: DeepSeek V4.1 "
      "Flash 1017 → DeepSeek V4.1 Flash. The row is named and dated by the original; at the top setting the "
      "original's setup is taken when it has one there.",
      "- Same top setting in two places: `home.best_per_model`'s rule (highest stored risk judgement; exact tie, first "
      "in league order). No model in the data has such a tie except via the checkpoint (resolved by the original "
      "rule above); Drex 2.0 / Drex 2.0 (local) would be one among the late entries (off).",
      "- Ranked by the chosen setup's stored risk judgement (exact tie: name).", "",
      "## Per model", "",
      "| # | Row (model) | Setups played (setting · league · judgement) | Chosen | Why | Best-score setup (the old rule) |",
      "|---:|---|---|---|---|---|"]
order = sorted(lines, key=lambda t: (t[2]["j"] is None, -(t[2]["j"] or 0), t[0]))
changed = []
for i, (b, g, pick, why, best) in enumerate(order, 1):
    played = "; ".join(f"{x['name']} ({x['setting'] or '—'} · L{x['lid']} · {x['j']:.1f})" for x in g)
    old = best["name"] + (" (same)" if best is pick else "")
    if best is not pick:
        changed.append(f"{b}: {best['name']} → {pick['name']}")
    md.append(f"| {i} | {b} | {played} | {pick['name']} · L{pick['lid']} | {why} | {old} |")
md += ["", f"Rows whose setup differs from the best-score rule ({len(changed)}): " + ("; ".join(changed) or "none") + ".",
       "", "Rows: 31 models (main's table has 32: it counted DeepSeek V4.1 Flash 1017 as its own model, a row that "
       "now sits under DeepSeek V4.1 Flash's expander).", ""]
(out / "1-setting-choice.md").write_text("\n".join(md) + "\n")

# 2. Maker colours.
mk = json.loads((work / "tools/site/content/maker_colors.json").read_text())
fam_old = json.loads(subprocess.run(["git", "-C", str(work), "show", "origin/main:tools/site/content/families.json"],
                                    capture_output=True, text=True, check=True).stdout)["families"]
given = ["OpenAI", "Google", "Anthropic", "xAI", "DeepSeek", "Moonshot", "Liquid AI"]
shown_names = {x["name"] for x in rows} | {e["name"] for e in late["entries"]}
missing = sorted(n for n in shown_names if n not in mk["setups"])
check("every league and late-entry setup has a maker", not missing, ", ".join(missing))
md = ["# 2. Maker colours (Ümit #2745 item 7; Main #2749)", "",
      "One file: `tools/site/content/maker_colors.json` holds the makers, their colours and every setup's maker. Every "
      "chart of the home page (Risk judgement, Error rate, Cost, Time, the two finding charts, Too safe) and the "
      "leaderboard take a setup's colour from it; `families.json` keeps only the icons (its colours are removed). "
      "Switching the other makers from grey to the Decision models site's family colours is an edit of that file "
      "(each grey maker records its sibling colour beside it).", "",
      "| Maker | Colour | Setups |", "|---|---|---|"]
by = {}
for n, m in mk["setups"].items():
    by.setdefault(m, []).append(n)
for m, v in mk["makers"].items():
    md.append(f"| {m}{'' if m in given else ' (grey for now)'} | `{v['colour']}`"
              + (f" (sibling: `{v['sibling_family_colour']}` {v['sibling_family']})" if v.get("sibling_family_colour") else "")
              + f" | {', '.join(by.get(m, []))} |")
md += ["", "## Existing charts: family colour before → maker colour now", "", "| Family | Before | Maker | Now |", "|---|---|---|---|"]
for f in fam_old:
    hit = [n for n in mk["setups"] if re.match(f["match"], n)]
    makers_ = sorted({mk["setups"][n] for n in hit})
    md.append(f"| {f['name']} | `{f['colour']}` | {', '.join(makers_) or '(no setup)'} | "
              + ", ".join(f"`{mk['makers'][x]['colour']}`" for x in makers_) + " |")
md += ["", "Setups with no family (no icon) now take their maker's colour as well: Liquid d1-ultra (Liquid AI) was "
       "the neutral grey before.", "",
       "For Ümit: the other makers and their grey: " + ", ".join(m for m in mk["makers"] if m not in given) + ". "
       "Judgement calls recorded in the file: Cygnet is Google's gemma-4-12B-it unchanged behind our letter-reading "
       "server, so Google; Winnow-12B (a Gemma fine-tune by its author), Clef and Open-Jev 27B v1.1 have no maker on "
       "record; Jev's maker is taken from its API (TypeSafe); the other names come from setups.json's provider, "
       "model id or notes (the `source` field per maker)."]
(out / "2-maker-colours.md").write_text("\n".join(md) + "\n")

# 3. Late entries: the open question.
ents = late["entries"]
md = ["# 3. Late entries in the leaderboard: open question for Ümit", "",
      "Default: **not shown** (they are in no standings table). `story.LATE_ROWS = False`; set to True they appear as a "
      "separate grey group, **Late entries (not ranked)**, under the programs, one row per model by the same "
      "highest-setting rule over their own late-entry setups, never in the ranking; the name links to the late "
      "entry's page (Every decision does not hold late entries). Screenshots of that state: "
      "`review/screenshots/leaderboard-late-on-*.png` (a render of the same data with the constant set, not the candidate).", "",
      "| Late entry | Model | Setting | Risk judgement |", "|---|---|---|---|"]
for e in ents:
    m = next((x for x in meta if x["dataset"] == "late-entry" and x["name"] == e["name"]), {})
    j = e.get("risk", {}).get("main", {}).get("judgement") if isinstance(e.get("risk"), dict) else None
    md.append(f"| {e['name']} | {m.get('model', '?')} | {m.get('setting') or '—'} | {'' if j is None else f'{j:.1f}'} |")
md += ["", "Note: GPT-6 Astra (high) is a late entry. If late entries counted for the rule, Astra's highest setting "
       "would be high (a late entry) instead of medium (League 3)."]
(out / "3-late-entries-question.md").write_text("\n".join(md) + "\n")
print("evidence:", "OK" if not fails else f"{fails} FAIL")
sys.exit(1 if fails else 0)
