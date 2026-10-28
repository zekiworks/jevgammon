"""Nackgammon paired test: the Markdown results report, assembled from the saved results by data key (no scoring).

    python3 tools/v3/nack_paired_report.py accounting   # positions/nack-paired/results/accounting.json from the ledgers
    python3 tools/v3/nack_paired_report.py render       # mailbox/Nackgammon paired test - results.md
    python3 tools/v3/nack_paired_report.py verify       # every table cell of the report against the saved JSON
    python3 tools/v3/nack_paired_report.py mapping      # section -> table -> data keys

Inputs: positions/nack-paired/results/results.json (frozen scorer output; read, never recomputed here) and
accounting.json (OpenRouter spend, read-only from the budget ledgers and the answers' recorded costs; no request).
Every table is declared once in TABLES: its section, its rows and, per column, the data-key paths and the format.
`render` prints from those declarations; `verify` re-reads the written report, finds each table under its declared
section heading by its header line, and checks every cell against the values at its declared paths.
"""

import json
import re
import sqlite3
import sys

RES = "positions/nack-paired/results/results.json"
ACC = "positions/nack-paired/results/accounting.json"
MD = "mailbox/Nackgammon paired test - results.md"
GROUP_ORDER = ["decision models", "workhorses", "frontier", "no group (exploratory)", "yardstick"]
PHASES = ("opening", "contact", "holding", "race", "bear-off")
RULES = [("random", "Primary rule: an invalid or missing answer scores the position's Random error"),
         ("worst", "Sensitivity (i): an invalid or missing answer scores the worst legal play's loss"),
         ("drop", "Sensitivity (ii): the setup's pairs with an invalid or missing answer left out")]


def get(d, path):
    for k in path:
        d = d[k]
    return d


def ci(path, f="+.1f"):
    """Two placeholders for an interval stored as [lo, hi] at path."""
    return [(path + (0,), f), (path + (1,), f)]


# --- table declarations ------------------------------------------------------------------------------------------
# A column: (header, template, [(path, format)]). Paths may contain "@" (the row key). Template has "{}" placeholders,
# filled in order; a format of "s" is text, "yn" is yes/no from a bool.

def setup_rows(R):
    S = R["setups"]
    return sorted(S, key=lambda s: (GROUP_ORDER.index(S[s]["group"]), S[s]["first_look"]["standard_pr"], s))


def model_rows(R):
    return [s for s in setup_rows(R) if s != "Random"]


TABLES = []


def table(section, name, rows, cols, intro=""):
    TABLES.append(dict(section=section, name=name, rows=rows, cols=cols, intro=intro))


F, L = ("setups", "@", "first_look"), ("setups", "@", "final_look")
RF, RL = ("setups", "Random", "first_look", "drop"), ("setups", "Random", "final_look", "drop")
table("Per setup", "per-setup", setup_rows, [
    ("Setup", "{}", [((), "row")]),
    ("Group", "{}", [(("setups", "@", "group"), "s")]),
    ("Standard PR (200)", "{}", [(F + ("standard_pr",), ".2f")]),
    ("Nackgammon PR (200)", "{}", [(F + ("nackgammon_pr",), ".2f")]),
    ("Drop [97.5%] (200)", "{} [{}, {}]", [(F + ("drop",), "+.2f")] + ci(F + ("drop_975",))),
    ("Random's drop (200)", "{}", [(RF, "+.2f")]),
    ("Standard / Nackgammon PR (500)", "{} / {}", [(L + ("standard_pr",), ".2f"), (L + ("nackgammon_pr",), ".2f")]),
    ("Drop [97.5%] (500)", "{} [{}, {}]", [(L + ("drop",), "+.2f")] + ci(L + ("drop_975",))),
    ("Random's drop (500)", "{}", [(RL, "+.2f")]),
    ("Asked the reserve under the rule", "{}", [(("setups", "@", "extended"), "yn")]),
    ("Label (final)", "{}", [(("setups", "@", "label"), "s")]),
])
table("Invalid or missing answers and sensitivity", "sensitivity", setup_rows, [
    ("Setup", "{}", [((), "row")]),
    ("Invalid or missing, Nackgammon / standard (200 pairs)", "{} / {}",
     [(F + ("invalid", "nackgammon"), "d"), (F + ("invalid", "standard"), "d")]),
    ("Same (500 pairs)", "{} / {}", [(L + ("invalid", "nackgammon"), "d"), (L + ("invalid", "standard"), "d")]),
    ("Primary drop [97.5%] (200)", "{} [{}, {}]", [(F + ("drop",), "+.2f")] + ci(F + ("drop_975",))),
    ("(i) worst play: drop [97.5%]", "{} [{}, {}]",
     [(("setups", "@", "sensitivity_first", "worst", "drop"), "+.2f")]
     + ci(("setups", "@", "sensitivity_first", "worst", "drop_975"))),
    ("(ii) pairs left out: pairs, drop [97.5%]", "{}, {} [{}, {}]",
     [(("setups", "@", "sensitivity_first", "drop", "pairs"), "d"),
      (("setups", "@", "sensitivity_first", "drop", "drop"), "+.2f")]
     + ci(("setups", "@", "sensitivity_first", "drop", "drop_975"))),
])
table("By phase", "phases", setup_rows, [("Setup", "{}", [((), "row")])] + [
    (ph, "{} [{}, {}]", [(("setups", "@", "phases", ph, "drop"), "+.1f")] + ci(("setups", "@", "phases", ph, "drop_95")))
    for ph in PHASES] + [
    ("opening − other phases [95%]", "{} [{}, {}]",
     [(("setups", "@", "phases", "opening minus other phases", "diff"), "+.1f")]
     + ci(("setups", "@", "phases", "opening minus other phases", "ci_95")))])
table("By phase", "cost", model_rows, [
    ("Setup", "{}", [((), "row")]),
    ("Positions recorded (all)", "{}", [(("setups", "@", "cost_all", "decisions"), "d")]),
    ("Recorded cost $ per decision (provider-reported; Mercury Decide: list price)", "{}", [(("setups", "@", "cost_all", "billed_usd_per_decision"), ".5f")]),
    ("API-equivalent $ per decision", "{}", [(("setups", "@", "cost_all", "api_eq_usd_per_decision"), ".5f")]),
], intro="Cost per recorded position over all 1,000 (recorded cost and API-equivalent are never added; 0 = none of "
         "that kind; setups on our GPUs have no list price). Recorded cost is the cost stored with each answer: the "
         "provider's reported cost per response where the route reports one, otherwise the runner's list-price "
         "computation (Mercury Decide; its provider-billed amount is unknown). No invoice was checked.")


def side(k):
    return [((k + ("standard_pr",)), ".2f"), ((k + ("nackgammon_pr",)), ".2f"), ((k + ("drop",)), "+.2f")]


for rule, cap in RULES:
    P = ("primary", rule, "@")
    table("Primary comparisons", f"primary-{rule}", (lambda R, rule=rule: list(range(len(R["primary"][rule])))), [
        ("Comparison", "{}", [(P + ("comparison",), "s")]),
        ("A: standard / Nackgammon / drop", "{} / {} / {}", side(P + ("A",))),
        ("B: standard / Nackgammon / drop", "{} / {} / {}", side(P + ("B",))),
        ("A − B [99%]", "{} [{}, {}]", [(P + ("diff",), "+.2f")] + ci(P + ("ci_99",), "+.2f")),
        ("Random's drop (200)", "{}", [(RF, "+.2f")]),
    ], intro=f"**{cap}.**")
for key, cap in (("kept_advantage", "Main 200 pairs"), ("kept_advantage_all_500", "All 500 pairs")):
    K = (key, "@")
    table("Secondary 1: kept advantage over random play", key,
          (lambda R, key=key: [s for s in setup_rows(R) if s in R.get(key, {})]), [
              ("Setup", "{}", [((), "row")]),
              ("K [95%]", "{} [{}, {}]", [(K + ("K",), ".2f")] + ci(K + ("ci_95",), ".2f")),
              ("Standard advantage over Random (PR) [95%]", "{} [{}, {}]",
               [(K + ("standard_advantage",), ".1f")] + ci(K + ("advantage_95",), ".1f")),
              ("Unstable", "{}", [(K + ("unstable",), "yn")]),
          ], intro=f"**{cap}.**")
table("Secondary 2: ranking", "spearman", lambda R: [0], [
    ("Model setups", "{}", [(("spearman", "setups"), "d")]),
    ("Spearman ρ [95%]", "{} [{}, {}]", [(("spearman", "rho"), ".2f")] + ci(("spearman", "ci_95"), ".2f")),
])
table("Secondary 2: ranking", "rank-changes", lambda R: list(range(len(R["spearman"]["largest_rank_changes"]))), [
    ("Setup", "{}", [(("spearman", "largest_rank_changes", "@", "setup"), "s")]),
    ("Standard rank", "{}", [(("spearman", "largest_rank_changes", "@", "standard_rank"), "d")]),
    ("Nackgammon rank", "{}", [(("spearman", "largest_rank_changes", "@", "nackgammon_rank"), "d")]),
    ("Change", "{}", [(("spearman", "largest_rank_changes", "@", "change"), "+d")]),
], intro="Five largest rank changes (1 = lowest error rate; ties by name).")
RK = ("setups", "@", "risk_main")
table("Secondary 3: risk", "risk", setup_rows, [
    ("Setup", "{}", [((), "row")]),
    ("Risk pays / Safety pays positions, Nackgammon; standard", "{} / {}; {} / {}",
     [(RK + ("nackgammon", "risk_pays"), "d"), (RK + ("nackgammon", "safety_pays"), "d"),
      (RK + ("standard", "risk_pays"), "d"), (RK + ("standard", "safety_pays"), "d")]),
    ("d′ standard", "{}", [(RK + ("standard", "d_prime"), ".2f")]),
    ("d′ Nackgammon", "{}", [(RK + ("nackgammon", "d_prime"), ".2f")]),
    ("Δd′ [95%]", "{} [{}, {}]", [(RK + ("change", "d_prime"), "+.2f")] + ci(RK + ("change", "d_prime_95"), "+.2f")),
    ("c standard", "{}", [(RK + ("standard", "caution"), ".2f")]),
    ("c Nackgammon", "{}", [(RK + ("nackgammon", "caution"), ".2f")]),
    ("Δc [95%]", "{} [{}, {}]", [(RK + ("change", "caution"), "+.2f")] + ci(RK + ("change", "caution_95"), "+.2f")),
    ("Thin", "{}", [(RK + ("thin",), "yn")]),
])
E = ("engine_check", "primary", "@")
table("Engine check", "engine-primary", lambda R: list(range(len(R["engine_check"]["primary"]))), [
    ("Comparison (40 pairs)", "{}", [(E + ("comparison",), "s")]),
    ("2-ply A − B [99%]", "{} [{}, {}]", [(E + ("2ply",), "+.2f")] + ci(E + ("2ply_ci_99",), "+.2f")),
    ("Rollout A − B [99%]", "{} [{}, {}]", [(E + ("rollout",), "+.2f")] + ci(E + ("rollout_ci_99",), "+.2f")),
    ("Direction changed", "{}", [(E + ("direction_changed",), "yn")]),
])
EP = ("engine_check", "per_setup", "@")
table("Engine check", "engine-setups", setup_rows, [
    ("Setup", "{}", [((), "row")]),
    ("2-ply standard / Nackgammon / drop", "{} / {} / {}", side(EP + ("2ply",))),
    ("Rollout standard / Nackgammon / drop", "{} / {} / {}", side(EP + ("rollout",))),
])
A = ("accounting", "rows", "@")
table("OpenRouter accounting", "accounting", lambda R: list(range(len(R["accounting"]["rows"]))), [
    ("Run", "{}", [(A + ("run",), "s")]),
    ("Row", "{}", [(A + ("row",), "s")]),
    ("Ledger attempts (Mercury Decide: final answer records, no attempt ledger)", "{}", [(A + ("attempts",), "d")]),
    ("Ledger-accounted $ (booked: max of list price and provider-reported)", "{}", [(A + ("ledger_usd",), "$8")]),
    ("Provider-reported $", "{}", [(A + ("provider_usd",), "$8")]),
    ("Source", "{}", [(A + ("source",), "s")]),
])


# --- rendering ---------------------------------------------------------------------------------------------------

def fmt_one(v, f):
    if f == "row" or f == "s":
        return str(v)
    if f == "yn":
        return "yes" if v else "no"
    if f == "d":
        return f"{int(v)}"
    if f == "+d":
        return f"{int(v):+d}"
    if f == "$8":
        return "unknown" if v is None else f"${v:.8f}"
    return format(v, f)


def resolve(path, row):
    return tuple(row if k == "@" else k for k in path)


def cells(R, t, row):
    out = []
    for _, tmpl, specs in t["cols"]:
        vals = [fmt_one(row if f == "row" else get(R, resolve(p, row)), f) for p, f in specs]
        out.append(tmpl.format(*vals))
    return out


def md_table(R, t):
    head = [c[0] for c in t["cols"]]
    lines = ([t["intro"], ""] if t["intro"] else []) + [
        "| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for row in t["rows"](R):
        lines.append("| " + " | ".join(cells(R, t, row)) + " |")
    return "\n".join(lines)


def tables_in(R, section):
    return "\n\n".join(md_table(R, t) for t in TABLES if t["section"] == section)


def load():
    R = json.load(open(RES))
    R["accounting"] = json.load(open(ACC))
    return R


def render():
    import hashlib
    R = load()
    acc = R["accounting"]
    h = hashlib.sha256(open(RES, "rb").read()).hexdigest()
    S = R["setups"]
    lfm = S["LFM2.5-24B-A2B (on)"]
    lfm_main = lfm["first_look"]["invalid"]
    lfm_all = lfm["final_look"]["invalid"]
    ec = R["engine_check"]
    doc = f"""# Nackgammon paired test: results

2026-10-28 · Method §10 (`tools/site/content/method-spec-2026-10-24.md`, with the addenda of 2026-10-27, §10.14 and its
dated correction (f) of 2026-10-28). Brief: `mailbox/Nackgammon and Terra - brief 2026-10-27.md`. Saved scores:
`positions/nack-paired/results/results.json` (sha256 `{h}`; the scorer's output of 2026-10-28 with one text field,
`groups_rule`, corrected by a string edit on 2026-10-28; every number unchanged). This report is assembled from that
file by data key (`tools/v3/nack_paired_report.py`; `verify` checks every table cell against it).

**Scope:** {R['scope_note']} {R['frontier_note']}

**Groups and disclosure:** {R['groups_rule']}

What this measures: how much a new starting setup (same rules) changes each setup's (model, settings and prompt)
decision quality. A larger drop is consistent with relying on familiar positions but is not proof, because Nackgammon
positions also differ in structure. "Kept" is a valid result. The paired test's standard prompt (`bg-v3-std-notable`)
differs from the league prompt (no opening table; the setup sentence on its own line), so the standard error rates
here are not compared directly with league error rates. **Random is slightly better on Nackgammon** on these pairs: its
own drop is shown next to every result.

## What ran

- 24 asked setups: 12 decision models, 9 workhorses, 1 frontier setup (original leagues, §10.14), GPT-6.1 Terra (no
  group, exploratory; passed its smoke test, 50/50 valid, 9.8 PR) and GNUbg weak (yardstick). **Random** (yardstick)
  is computed exactly from GNUbg's 2-ply values (mean loss over all legal plays): it was never asked and is not
  subject to the stopping rule; it is reported on the main 200 pairs and on all 500.
- Every asked setup was asked the main 400 positions (200 pairs). Every first look was "unclear" (97.5% intervals
  about ±4 to ±18 PR), so the frozen rule sent every asked setup the 300 reserve pairs (600 positions). **Each asked
  setup has 1,000 recorded positions.** For 23 setups all 1,000 hold a valid answer. **LFM2.5-24B-A2B (on)** has 107
  records without a choice (timed out at the 600 s limit: 38 of the main 400, 69 of the reserve 600; scored split
  {lfm_all['nackgammon']} Nackgammon / {lfm_all['standard']} standard positions over all 500 pairs, {lfm_main['nackgammon']} / {lfm_main['standard']} on the main 200). These are never dropped: they score the
  position's Random error (primary rule), with both sensitivity checks below. Usual retries only, no re-asks.
- Raw answers, logs and the per-attempt ledgers are kept privately; a release bundle is prepared locally and not published.

## Per setup

Standard, Nackgammon and the drop together; not a ranking (rows by group, then standard PR). Drop = Nackgammon PR −
standard PR on the same pairs (positive = worse on Nackgammon). First look on the main 200 pairs, final look on all 500.
Label from the final 97.5% interval. Bootstrap intervals are approximate.

{tables_in(R, "Per setup")}

**Labels:** every asked setup and GNUbg weak is **"unclear"** at the final look (Random too, reported for reference):
every 97.5% interval contains 0 and reaches past ±5 PR. "Unclear" means the interval is too wide to decide; it is
**not** evidence of equivalence ("kept" would need the whole interval within ±5 PR). No setup is "kept", "worse" or
"better" on this evidence.

## Invalid or missing answers and sensitivity

{tables_in(R, "Invalid or missing answers and sensitivity")}

## By phase

Main 200 pairs, descriptive, 95% intervals.

{tables_in(R, "By phase")}

By game-plan tag: PR per tag and set in `results.json` (`setups.<name>.tags`; descriptive, tags are not matched; the
back-game row is too thin to read, 10 Nackgammon against 2 standard, and partly reflects Nackgammon's starting anchors).

## Primary comparisons

Main 200 pairs, M = 5, each interval at 99%.

{R['groups_rule']}

{R['frontier_note']} {R['scope_note']}

{tables_in(R, "Primary comparisons")}

No primary interval excludes 0, under the primary rule or either sensitivity rule.

## Secondary 1: kept advantage over random play

Labelled secondary. K = (Random's Nackgammon PR − setup's Nackgammon PR) ÷ (Random's standard PR − setup's standard
PR); 1 = keeps its whole advantage over random play.

{tables_in(R, "Secondary 1: kept advantage over random play")}

## Secondary 2: ranking

Labelled secondary. Model setups only (yardsticks left out).

{tables_in(R, "Secondary 2: ranking")}

## Secondary 3: risk

Labelled secondary. Main 200 pairs; invalid or missing answers with Random's weights; d′ ability, c caution (§2 rules).

{tables_in(R, "Secondary 3: risk")}

Exploratory (not tested): GPT-6.1 Terra against GPT-6.1 Sol (low) appears in the tables above; no comparison is drawn.

## Engine check

40 frozen pairs (80 positions). Rollouts: {ec['settings']}. {ec['counts']['rolled_out_plays']} plays rolled out;
a play without a rollout used its 2-ply value plus the position's mean shift ({ec['counts']['adjusted_plays_used']}
uses, mostly Random's all-plays mean). No comparison changes direction.

{tables_in(R, "Engine check")}

## OpenRouter accounting

From the retained budget ledgers and the answers' recorded costs only (no request). "Ledger-accounted" is what the
ledger booked against the caps: per attempt the larger of the list-price cost and the provider-reported cost.
"Provider-reported" is OpenRouter's `usage.cost` per response. Mercury Decide is on no ledger (its route allows none):
its recorded cost is the runner's list-price computation; its provider-billed amount was not retained (unknown).

{tables_in(R, "OpenRouter accounting")}

{chr(10).join('- ' + x for x in acc['notes'])}
"""
    open(MD, "w").write(doc)
    print(f"wrote {MD}")


# --- verify ------------------------------------------------------------------------------------------------------

NUM = re.compile(r"[+\-−]?\$?\d+(?:\.\d+)?")


def sections_of(text):
    out, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def verify():
    R = load()
    text = open(MD).read()
    secs = sections_of(text)
    bad, n_cells, n_numbers = [], 0, 0
    for t in TABLES:
        lines = secs.get(t["section"])
        if lines is None:
            bad.append(f"{t['name']}: section {t['section']!r} missing")
            continue
        head = "| " + " | ".join(c[0] for c in t["cols"]) + " |"
        idx = [i for i, ln in enumerate(lines) if ln == head
               and (not t["intro"] or (i >= 2 and lines[i - 2] == t["intro"]))]
        if len(idx) != 1:
            bad.append(f"{t['name']}: header found {len(idx)} times in section {t['section']!r}")
            continue
        body = []
        for ln in lines[idx[0] + 2:]:
            if not ln.startswith("|"):
                break
            body.append([c.strip() for c in ln.strip().strip("|").split("|")])
        rows = t["rows"](R)
        if len(body) != len(rows):
            bad.append(f"{t['name']}: {len(body)} rows, data has {len(rows)}")
            continue
        for row, got in zip(rows, body):
            for (h, tmpl, specs), cell in zip(t["cols"], got):
                n_cells += 1
                # Independent of the printed text: each value from its path, compared to the cell's tokens.
                vals = [(row if f == "row" else get(R, resolve(p, row)), f) for p, f in specs]
                if all(f in ("row", "s", "yn") for _, f in vals):
                    if cell != tmpl.format(*[fmt_one(v, f) for v, f in vals]):
                        bad.append(f"{t['name']} [{row}] {h}: {cell!r}")
                    continue
                toks = NUM.findall(cell.replace("unknown", ""))
                want = [(v, f) for v, f in vals if f not in ("row", "s", "yn") and v is not None]
                if len(toks) != len(want):
                    bad.append(f"{t['name']} [{row}] {h}: {cell!r} has {len(toks)} numbers, data {len(want)}")
                    continue
                for tok, (v, f) in zip(toks, want):
                    x = float(tok.replace("−", "-").replace("$", ""))
                    d = 8 if f == "$8" else (int(f.split(".")[1][0]) if "." in f else 0)
                    n_numbers += 1
                    if x != round(float(v), d) and abs(x - float(v)) > 0.5 * 10 ** -d + 1e-12:
                        bad.append(f"{t['name']} [{row}] {h}: {tok} for {v!r}")
    for k in ("groups_rule", "frontier_note", "scope_note"):
        if R[k] not in text:
            bad.append(f"{k} not verbatim in the report")
    for word in ("memori", "trained on", "answered 1,000", "Nothing was published."):
        if word in text:
            bad.append(f"forbidden wording {word!r}")
    print(f"{len(TABLES)} tables, {n_cells} cells, {n_numbers} numbers checked; "
          + ("OK" if not bad else f"{len(bad)} MISMATCH"))
    for b in bad[:40]:
        print("MISMATCH", b)
    sys.exit(1 if bad else 0)


def mapping():
    for t in TABLES:
        keys = sorted({"/".join(str(k) for k in p) for c in t["cols"] for p, f in c[2] if f != "row"})
        print(f"## {t['section']} :: {t['name']}\n  " + "\n  ".join(keys))


# --- accounting (read-only) ----------------------------------------------------------------------------------------

def ledger(path, setup):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    n, led, rep, nulls, open_ = con.execute(
        "SELECT COUNT(*), SUM(cost_usd), SUM(reported_cost_usd), SUM(reported_cost_usd IS NULL AND cost_usd > 0), "
        "SUM(status != 'settled') FROM attempts WHERE setup = ?", (setup,)).fetchone()
    return n, led, rep, nulls, open_


def answers_cost(db, setup, pset):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return con.execute("SELECT COUNT(*), SUM(cost_usd) FROM answers WHERE setup = ? AND position_set = ?",
                       (setup, pset)).fetchone()


def accounting():
    rows, opened = [], 0
    for run, row, path, setup in (
            ("GPT-6.1 Terra smoke (50 positions)", "a", "smoke/nack-paired-budget-abc.db", "GPT-6.1 Terra"),
            ("DeepSeek V4.1 Flash (off), main 400", "b", "smoke/nack-paired-budget-abc.db", "DeepSeek V4.1 Flash (off)"),
            ("GPT-6.1 Terra, main 400", "c", "smoke/nack-paired-budget-c.db", "GPT-6.1 Terra"),
            ("DeepSeek V4.1 Flash (off), reserve 600", "d", "smoke/nack-paired-budget-d.db", "DeepSeek V4.1 Flash (off)"),
            ("GPT-6.1 Terra, reserve 600", "d", "smoke/nack-paired-budget-d.db", "GPT-6.1 Terra")):
        n, led, rep, nulls, op = ledger(path, setup)
        opened += op or 0
        rows.append(dict(run=run, row=row, attempts=n, ledger_usd=round(led, 8), provider_usd=round(rep, 8),
                         source="budget ledger"))
    for pset, row in (("nack-paired-main", "b"), ("nack-paired-reserve", "d")):
        n, c = answers_cost("smoke/nack-paired.db", "Mercury Decide", pset)
        rows.append(dict(run=f"Mercury Decide, {'main 400' if row == 'b' else 'reserve 600'}", row=row, attempts=n,
                         ledger_usd=round(c, 8), provider_usd=None,
                         source="answers' recorded cost (runner list price; no ledger)"))

    def tot(sel, k):
        vals = [r[k] for r in rows if sel(r)]
        return None if any(v is None for v in vals) else round(sum(vals), 8)

    d_led = tot(lambda r: r["row"] == "d" and r["source"] == "budget ledger", "ledger_usd")
    d_rep = tot(lambda r: r["row"] == "d" and r["source"] == "budget ledger", "provider_usd")
    d_merc = tot(lambda r: r["row"] == "d" and r["source"] != "budget ledger", "ledger_usd")
    all_led = tot(lambda r: True, "ledger_usd")
    known_rep = tot(lambda r: r["source"] == "budget ledger", "provider_usd")
    merc = tot(lambda r: r["source"] != "budget ledger", "ledger_usd")
    notes = [
        f"Open or lost reservations in the three ledgers: {opened} (every attempt settled).",
        f"Row d, ledger setups only: ledger-accounted ${d_led:.8f}, provider-reported ${d_rep:.8f}. Adding Mercury "
        f"Decide's recorded reserve cost (${d_merc:.8f}, list price) gives ${d_led + d_merc:.8f}: the \"$2.489\" quoted "
        f"earlier was this ledger-accounted figure including Mercury, against the $2.55 cap (ledger cap $2.51 + Mercury "
        f"limit $0.035). Provider-reported row d including Mercury is unknown (Mercury's billed amount was not retained); "
        f"with Mercury at its list-price record it would be ${d_rep + d_merc:.8f}.",
        f"Rows a–d: ledger-accounted ${all_led:.8f} (incl. Mercury at list price; the \"$4.39\" quoted earlier); "
        f"provider-reported ${known_rep:.8f} for the ledger runs plus Mercury unknown (list-price record ${merc:.8f}).",
        "DeepSeek V4.1 Flash (off) books above its provider-reported cost because the ledger's list price ($0.30/$1.20 "
        "per M) exceeds what OpenRouter reported; GPT-6.1 Terra books at its provider-reported cost, which exceeds list "
        "price because OpenRouter billed each prompt as a cache write ($1.25 per M).",
        "Not on any ledger: before the smoke test, direct probe requests to openai/gpt-6.1-terra outside the runner; one "
        "answered probe reported $0.000033, one answered probe's cost was not retained (unknown); the rest were refused "
        "by routing (404): none has a reported cost and none was booked; the billed amount is unknown. The smoke test's first attempt (50 requests) was refused by routing (404) and "
        "booked at $0 (no reported cost; the billed amount is unknown).",
        "The OpenRouter account's usage rose by $4.99 between 18:05 UTC on 2026-10-27 and about 01:00 UTC on "
        "2026-10-28; the difference from the figures above is not attributable from retained data (other runs on the "
        "same account in that window): unknown.",
    ]
    json.dump(dict(rows=rows, notes=notes, d_ledger_usd=d_led, d_provider_usd=d_rep, d_mercury_list_usd=d_merc,
                   total_ledger_usd=all_led, total_provider_known_usd=known_rep, mercury_list_usd=merc,
                   open_reservations=opened), open(ACC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in json.load(open(ACC)).items() if k not in ("rows", "notes")}))


if __name__ == "__main__":
    {"render": render, "verify": verify, "mapping": mapping, "accounting": accounting}[sys.argv[1]]()
