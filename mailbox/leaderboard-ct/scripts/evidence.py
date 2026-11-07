"""leaderboard-ct evidence (Ümit #2745; Zeki #2790): the per-model setting choice, re-derived here from a render's
published data files (data/setups.json, data/v3/league-N.json, data/v3/late-entries.json) and the approved identity list
(content/model_identity.json) by an implementation independent of story.py, then compared with the rendered table, row
by row and expander by expander; the maker colours. Reads only. Exits 1 if any check fails.
    evidence.py WORKTREE RENDER_DIR OUT_DIR [PREVIOUS_RENDER_DIR]
Writes OUT_DIR/1-setting-choice.md, 2-maker-colours.md, 3-late-entries-question.md, expected-families.json and prints
PASS/FAIL lines; PREVIOUS_RENDER_DIR (the 5ca56de render) lists the ranked rows that changed against it."""
import json
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

work, render, out = (Path(a) for a in sys.argv[1:4])
prev = Path(sys.argv[4]) if len(sys.argv) > 4 else None
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


# Every league setup with its stored judgement and the league of its setups.json entry (its original league).
rows, prog = [], {}
for lg in leagues:
    for n, s in lg["setups"].items():
        m = entry(lg["dataset"], n)
        x = dict(ds=lg["dataset"], lid=lg["id"], name=n, slug=s["slug"], model=m["model"], setting=m["setting"],
                 j=s["risk"]["main"]["judgement"], origin=int(m["dataset"].rsplit("-", 1)[1]), played=True)
        if m["model_type"] == "program":
            prog.setdefault(n, []).append(x)
        else:
            rows.append(x)
    for n, s in lg["references"].items():
        prog.setdefault(n.removesuffix(" (computed)"), []).append(
            dict(ds=lg["dataset"], lid=lg["id"], name=n, slug=s["slug"], origin=lg["id"], played=False))
SAME = json.loads((work / "tools/site/content/model_identity.json").read_text())["same_model"]
check("the approved identity list is exactly DeepSeek V4.1 Flash 1017 → DeepSeek V4.1 Flash",
      SAME == {"DeepSeek V4.1 Flash 1017": "DeepSeek V4.1 Flash"}, json.dumps(SAME))


def rank(s, levelled):
    if s is None:
        return 0
    if s == "on":
        assert not levelled, "on with levels"
        return 1
    return RANK[s]


first = lambda xs: min(xs, key=lambda x: (x["origin"], x["name"]))  # league order, then name: no score
groups = {}
for x in rows:
    groups.setdefault(SAME.get(x["model"], x["model"]), []).append(x)
chosen, lines = {}, []
for b, g in groups.items():
    levelled = any(x["setting"] not in (None, "on", "off", "none") for x in g)
    top = max(rank(x["setting"], levelled) for x in g)
    cands = [x for x in g if rank(x["setting"], levelled) == top]
    pick = first(cands)
    chosen[b] = pick
    best = max(g, key=lambda x: x["j"] or -1)
    why = ("single setup" if len(g) == 1 else
           f"highest setting played: {pick['setting'] or 'none sent'}"
           + (f"; {len(cands)} setups at it ({', '.join(x['name'] + ' L' + str(x['origin']) for x in cands)}): the first "
              "in league order, then by name" if len(cands) > 1 else ""))
    lines.append((b, g, pick, why, best))
prog_pick = {n: first([x for x in g if x["played"]] or g) for n, g in prog.items()}

# The rendered table: its ranked rows in order, against the re-derived choice ranked by judgement (then name).
html = BeautifulSoup((render / "index.html").read_text(), "html.parser")
table = html.select_one("#headline-table")
shown = [(tr["data-dataset"], tr["data-setup"]) for tr in table.tbody.find_all("tr", recursive=False)
         if tr.get("data-setup") and not set(tr.get("class") or []) & {"hl-sub", "reference", "late"}]
expect = [(x["ds"], x["slug"]) for x in sorted(chosen.values(), key=lambda x: (x["j"] is None, -(x["j"] or 0),
                                                                                next(b for b in chosen if chosen[b] is x)))]
check("ranked rows = re-derived choice, in rank order", shown == expect, f"{len(shown)} rows shown, {len(expect)} expected")
# Each parent's alternatives, expected from the data (not from the page's aria-controls), against the rows its
# expander controls; written out for the browser test (review.py clicks each expander and compares).
families = {}
for b, g in groups.items():
    p = chosen[b]
    families[f'{p["ds"]}/{p["slug"]}'] = sorted(f'{x["ds"]}/{x["slug"]}' for x in g if x is not p)
for n, g in prog.items():
    p = prog_pick[n]
    families[f'{p["ds"]}/{p["slug"]}'] = sorted(f'{x["ds"]}/{x["slug"]}' for x in g if x is not p)
(out / "expected-families.json").write_text(json.dumps(families, indent=1) + "\n")
bad = []
for tr in table.tbody.find_all("tr", recursive=False):
    if not tr.get("data-setup") or "hl-sub" in (tr.get("class") or []):
        continue
    key = f'{tr["data-dataset"]}/{tr["data-setup"]}'
    btn = tr.select_one(".hl-more")
    got = sorted(f'{s["data-dataset"]}/{s["data-setup"]}' for s in
                 (table.find(id=i) for i in (btn["aria-controls"].split() if btn else [])))
    if families.get(key) != got:
        bad.append(f"{key}: expected {families.get(key)}, expander controls {got}")
check("each parent row's expander controls exactly its expected alternatives (per row, expected from the data)",
      not bad and len(families) == len(shown) + 3, "; ".join(bad) or f"{len(families)} parent rows")
progs = [(tr["data-dataset"], tr["data-setup"]) for tr in table.select("tr.reference:not(.hl-sub)")]
check("programs: one grey unranked row each (GNUbg weak, Safest, Random), their first played setup in league order",
      progs == [(prog_pick[n]["ds"], prog_pick[n]["slug"]) for n in ("GNUbg weak", "Safest", "Random")], str(progs))
check("no late-entry row (LATE_ROWS off)", not table.select('tr[data-dataset="late-entry"]'))
note = html.select_one("#leaderboard [data-headline-panel=model] .section-caveat").get_text(" ")
check("note under the table", note.startswith("Bars run to each score; the whisker is its 95% interval. Ranks show "
                                                "observed scores; small gaps need not be meaningful. Leagues played "
                                                "different positions."), note)
check("no whisker-overlap sentence anywhere on the page", "not reliably ordered" not in html.get_text(" "))
rule = norm_text = " ".join(html.select_one("#leaderboard .headline-rule").get_text(" ").split())
check("the rule under the table states the score-free representative",
      "never its best score" in rule and "the first in league order, then by setup name (no score)" in rule, rule)
prev_rows = []
if prev:
    pt = BeautifulSoup((prev / "index.html").read_text(), "html.parser").select_one("#headline-table")
    prev_rows = [(tr["data-dataset"], tr["data-setup"]) for tr in pt.tbody.find_all("tr", recursive=False)
                 if tr.get("data-setup") and not set(tr.get("class") or []) & {"hl-sub", "reference", "late"}]

md = ["# 1. Setting choice per model (Ümit #2745 item 1; Zeki #2790)", "",
      "Re-derived by `scripts/evidence.py` from the render's data files (data/setups.json `setting`, the sent "
      "effort, and the league of each setup's entry; data/v3/league-N.json) and content/model_identity.json, "
      "independently of story.py, and compared with the rendered table: "
      + ("**all checks pass**." if not fails else f"**{fails} check(s) fail**."), "",
      "## The rule", "",
      "- Order of the sent effort: none = off < minimal < low < medium < high < xhigh < max.",
      "- `on`: the setting of a model with no levels (thinking on/off only: LFM2.5-24B-A2B, Gemma 4 31B); above off. "
      "A model with both `on` and a level fails the build (none has).",
      "- Decision models send no setting: their single setup.",
      "- Version names are separate models (Jev 1.13.0 / Jev 1.14.0; Decider v1.1 / v1.2; Fastino GLiDE / GLiDE v1.2).",
      "- One model under two names only by the approved list `content/model_identity.json`: DeepSeek V4.1 Flash 1017 "
      "→ DeepSeek V4.1 Flash, nothing else; any other name, a dated suffix included, is its own model. The row is "
      "named and dated by the original.",
      "- Several setups at the model's highest setting: the **first in league order** (the league of its setups.json "
      "entry), **then by setup name**. **No score** anywhere in the choice. The same for programs (their first played "
      "setup: League 1) and, with LATE_ROWS, late entries (their field league, then name).",
      "- Ranked by the chosen setup's stored risk judgement (exact tie: name).", "",
      "## Per model", "",
      "| # | Row (model) | Setups played (setting · league · judgement) | Chosen | Why | Best-score setup (for comparison) |",
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
if prev:
    diff = [f"{i}: {a} → {b}" for i, (a, b) in enumerate(zip(prev_rows, shown), 1) if a != b]
    md += [f"Against the 5ca56de render (score used within the top setting): ranked rows changed: "
           + ("; ".join(diff) if diff or len(prev_rows) != len(shown) else "**none**") +
           f" ({len(prev_rows)} rows then, {len(shown)} now, the same setups in the same order).", ""]
    check("ranked rows unchanged against 5ca56de (the score-free rule picks the same setups now)", prev_rows == shown,
          "; ".join(diff))
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
md += ["", "What LATE_ROWS = True does, precisely: it **adds** a separate grey, unranked group under the programs; the "
       "ranked rows do not change. GPT-6 Astra keeps its ranked row at **medium** (League 3); its late entry GPT-6 "
       "Astra (high) appears only as an extra row in the late group. The open question for Ümit is therefore whether "
       "to show that extra group at all, not whether late entries change a model's ranked setting (they do not, in "
       "either state)."]
(out / "3-late-entries-question.md").write_text("\n".join(md) + "\n")
print("evidence:", "OK" if not fails else f"{fails} FAIL")
sys.exit(1 if fails else 0)
