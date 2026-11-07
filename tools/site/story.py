"""The home page as a story (Ümit, bus #2570): one headline table, one row per model at its best-scoring setting, and
sections whose headings state what the published numbers show, each with one chart, two sentences and one caveat. Every number is a
stored value as the site's tables print it: risk judgement, risks found, right safety, error rate and cost from the
league results; the bias of the clear-risk scan and of its Part 2 question Q1 from the published clear-risk data
(data/v3/clear-risk.json). A third heading asked for, on reasoning, is not shown: the Reasoning tab's comparison is not
paired and shows no effect of the setting (its own note). The check of each heading against these
numbers is mailbox/front-story/evidence (made by evidence.py there), not code here: a heading that the data stops
supporting must be reworded by hand."""

import json
import re

import home as H
import pages as P
from common import ALL_NOTE, CONTENT, NA, count, esc, fmt, nm, pct

RELEASES = json.loads((CONTENT / "release_months.json").read_text())["models"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PROGRAMS = ("GNUbg weak", "Random", "Safest")


def caveat(text: str, anchor: str = "limits") -> str:
    """The one caveat of a section (Ümit, bus #2570 item 4); the others are on the Method page."""
    return (f'<p class="table-note section-caveat">{esc(text)} <a href="method/#{anchor}">More caveats: Method</a></p>')


# --- The headline table ------------------------------------------------------------------------------------------

def model_of(S, lg, n) -> str:
    return H.model_of(S, lg["dataset"], n)


def best_settings(S) -> list:
    """(league, setup name, risk metrics) of each model's setup with the highest stored risk judgement (H.best_per_model,
    the rule shared with the Nackgammon per-model view), best first. Programs are not models; a setup without a risk
    judgement is left out (Too few decisions)."""
    return sorted(H.best_per_model(S).values(), key=lambda x: (-x[2]["judgement"], x[1]))


def release(model: str) -> tuple[str, str | None]:
    """The model's release month as its maker's page states it (content/release_months.json), else a dash."""
    e = RELEASES.get(model) or {}
    if not e.get("month"):
        return "\u2014", None
    y, m = e["month"].split("-")
    return f"{MONTHS[int(m) - 1]} {y}", e["url"]


def share(s: dict) -> str:
    if not s["den"]:
        return f'<td class="num">{nm(NA)}<span class="small">0 / 0</span></td>'
    return f'<td class="num">{pct(s["share"])}<span class="small">{H.n_(s["n"])} / {H.n_(s["den"])}</span></td>'


def judgement_cell(r: dict, colour: str | None) -> str:
    """The risk judgement as a bar on 0 to 100 with its 95% interval and the line at 50 (always safe)."""
    j, lo, hi = r["judgement"], r["judgement_lo"], r["judgement_hi"]
    fill = f' style="width:{j:.2f}%;background-color:{colour}"' if colour else f' style="width:{j:.2f}%"'
    return (f'<td class="hl-judgement" data-v="{j}"><span class="hl-bar" aria-hidden="true"><span class="hl-fill'
            f'{"" if colour else " other"}"{fill}></span><span class="hl-int" style="left:{lo:.2f}%;width:{hi - lo:.2f}%">'
            f'</span><span class="hl-safe"></span></span><span class="hl-val">{fmt(j)}<span class="small">{fmt(lo)} to '
            f'{fmt(hi)}</span></span></td>')


def headline_rows(S) -> tuple[list, list]:
    rows, missing = [], []
    settings = {}
    for lg, n, r, ref in H.all_rows(S):
        if not ref:
            settings[model_of(S, lg, n)] = settings.get(model_of(S, lg, n), 0) + 1
    for rank, (lg, n, r) in enumerate(best_settings(S), 1):
        ds, model = lg["dataset"], model_of(S, lg, n)
        fam = H.family(n)
        icon = f'<svg class="fam-icon" aria-hidden="true" focusable="false"><use href="#{fam["icon"]}"/></svg>' if fam else ""
        swatch = f'<i class="swatch" style="background:{fam["colour"]}" title="{esc(fam["name"])}"></i>' if fam else ""
        month, url = release(model)
        if not url:
            missing.append(model)
        q = lg["setups"][n]["quality"]
        er = (f'<td class="num">{fmt(q["error_rate"])}<span class="small">{fmt(q["error_lo"])} to {fmt(q["error_hi"])}'
              f'</span></td>' if q.get("error_rate") is not None and not q.get("too_few") else f'<td class="num">{nm(NA)}</td>')
        label = (P.origin_meta(S, ds, n).get("price") or {}).get("label")
        cost = (f'<td class="num"><span class="cost-1k">${fmt(q["usd_per_1000"], 3)}</span><span class="cost-1m" '
                f'data-usd="{q["usd_per_1000"]!r}">${fmt(q["usd_per_1000"], 3)}</span>'
                f'<span class="small">{esc(label or "label missing")}</span></td>'
                if q.get("usd_per_1000") is not None else P.cost_cell(S, ds, n, q))
        when = (f'<td class="hl-release"><a href="{esc(url)}">{month}</a></td>' if url else
                f'<td class="hl-release"><span class="muted" title="No release date from the maker on record">{month}</span></td>')
        others = settings[model] - 1
        rows.append(f'<tr{H.attrs(S, ds, n)}><td class="num">{rank}</td><td class="model">{swatch}{icon}'
                    f'<a class="model-name" href="{P.model_href("", ds, n, S)}">{esc(n)}</a><span class="small">League '
                    f'{lg["id"]} · {"its setting with the highest risk judgement; " + count(others) + " other setting" + ("s" if others > 1 else "") + " under All setups" if others else "its only setting"}'
                    f'</span></td>{when}'
                    f'{judgement_cell(r, fam["colour"] if fam else None)}{share(r["found"])}{share(r["right_safety"])}{er}{cost}</tr>')
    return rows, missing


HEADLINE_HEAD = ["Rank", "Model: its setting with the highest risk judgement", ("Released", " data-nosort"), "Risk judgement (95% interval)", "Risks found",
                 "Right safety", "Error rate (PR)",
                 '<span class="cost-1k">$ per 1,000 decisions</span><span class="cost-1m">$ per 1M decisions</span>']


def headline(S) -> str:
    """One row per model at its setting with the highest stored risk judgement; the All setups key shows the full
    All leagues risk table (every setup, programs as reference rows) in its place."""
    rows, missing = headline_rows(S)
    table = P.table(HEADLINE_HEAD, rows, "One row per model: one named setup, the model's setting with the highest stored "
                    "risk judgement (a selection for display; every cell of a row is that setup's own; all setups under All "
                    "setups). All leagues, all phases.", cls="board headline",
                    attrs=' data-dataset="all" id="headline-table"')
    note = (f'<p class="table-note">Released: the month of the maker\'s own dated statement that this exact model was '
            f'released or became available to the public (an announcement before public availability does not count), '
            f'linked; \u2014 where no such statement is on record ({count(len(missing))} of {count(len(rows))} models).</p>'
            if missing else "")
    keys = ('<span class="keys needs-js" role="group" aria-label="Rows"><button type="button" class="key" '
            'data-headline-view="best" aria-pressed="true">Best setting per model</button><button type="button" '
            'class="key" data-headline-view="all" aria-pressed="false">All setups</button></span>')
    return (f'<section class="card headline" id="leaderboard" data-dataset="all" aria-labelledby="leaderboard-title">'
            f'<div class="chart-head"><h2 id="leaderboard-title">Risk calls leaderboard</h2>{keys}<p class="chart-sub">'
            f'Risk judgement: 100 = every call right, 50 = always safe; the line on each bar is its 95% interval, the mark '
            f'at 50 the always-safe line · higher is better</p></div>'
            f'<p class="table-note">{esc(ALL_NOTE)}</p>'
            '<p class="table-note headline-scope"><strong>A fixed table:</strong> all leagues, all phases, every model; '
            'the filter row below does not change it. A model with several settings shows the one with the highest '
            'stored risk judgement (on an exact tie, the first in league order).</p>'
            f'<div data-headline-panel="best">{P.SWIPE}{table}{note}</div>'
            f'<div data-headline-panel="all" hidden>{H.all_risk_table(S)}</div>'
            f'{caveat(H.RANK_NOTE, "statistics")}</section>')


# --- Finding sections ----------------------------------------------------------------------------------------------

def _num(s: str) -> float:
    return float(s.replace("\u2212", "-").replace("pp", "").replace("+", "").strip())


def scan_bias(S) -> list:
    """(league id, setup, bias text, bias) of the clear-risk scan's per-setup tables (kept decisions only); the
    league's reference rows (Safest program, Random legal play expected) left out."""
    sec = next(s for s in S["clear_risk"]["sections"] if s["id"] == "clear-risk-setups")
    out = []
    for t in sec["tables"]:
        m = re.match(r"League (\d)", t["caption"])
        i = t["head"].index("bias = missed \u2212 needless")
        for row in t["rows"]:
            if "(reference)" in row[0] or "(expected)" in row[0]:
                continue
            out.append((int(m.group(1)), row[0], row[i], _num(row[i])))
    return out


def q1_bias(S) -> list:
    """(model, bias with numbers text, value, bias board only text, value) of Clear risk Part 2, question Q1."""
    sec = next(s for s in S["clear_risk"]["sections"] if s["id"] == "clear-risk-part2")
    t = next(t for t in sec["tables"] if t["caption"].startswith("Q1"))
    i = t["head"].index("bias")
    by = {}
    for row in t["rows"]:
        by.setdefault(row[0], {})[row[1]] = row[i]
    return [(m, v["with numbers"], _num(v["with numbers"]), v["board only"], _num(v["board only"])) for m, v in by.items()]


def _bars(rows: list, lo: float, hi: float, ticks: list, head: str, zero: bool = True) -> str:
    """Bars from zero on a lo..hi axis (the sibling site's HTML bars): rows are (label html, [(value, class, colour)],
    value text, attrs)."""
    pos = lambda v: 100 * (v - lo) / (hi - lo)
    z = pos(0)
    out = []
    for label, bars, text, attrs in rows:
        fills = "".join(f'<span class="hbar-fill {cls}" style="margin-left:{min(pos(v), z):.2f}%;width:{abs(pos(v) - z):.2f}%'
                        f'{";background-color:" + colour if colour else ""}"></span>' for v, cls, colour in bars)
        mark = f'<span class="hbar-marker" style="left:{z:.2f}%"></span>' if zero else ""
        out.append(f'<li class="hbar"{attrs}><span class="hbar-label">{label}</span><span class="hbar-track">{fills}{mark}'
                   f'</span><span class="hbar-value">{text}</span></li>')
    axis = "".join(f'<span class="hbar-tick" style="left:{pos(t):.2f}%">{esc(lab)}</span>' for t, lab in ticks)
    return (f'<div class="hbar hbar-axis headed" aria-hidden="true"><span></span><span class="hbar-track">{axis}</span>'
            f'<span class="hbar-head">{head}</span></div><ol class="hbars headed">{"".join(out)}</ol>')


def finding(fid: str, heading: str, sentences: str, chart: str, legend: str, warn: str, anchor: str) -> str:
    return (f'<section class="card finding" id="{fid}" aria-labelledby="{fid}-title"><h2 id="{fid}-title">{esc(heading)}</h2>'
            f'<p class="finding-text">{sentences}</p><figure class="chart-card chart-wide finding-chart">{chart}'
            f'<p class="chart-legend">{legend}</p></figure>{caveat(warn, anchor)}</section>')


def cautious(S) -> str:
    rows = scan_bias(S)
    models = sorted((x for x in rows if x[1] not in PROGRAMS), key=lambda x: -x[3])
    progs = sorted((x for x in rows if x[1] in PROGRAMS), key=lambda x: -x[3])
    lo_m, hi_m = models[-1], models[0]
    gnu = [x for x in progs if x[1] == "GNUbg weak"]
    rnd = next(x for x in progs if x[1] == "Random")
    scanned = next(s for s in S["clear_risk"]["sections"] if s["id"] == "clear-risk-scan")
    kept = re.search(r"Kept: ([\d,]+) of", " ".join(scanned["notes"])).group(1)
    text = (f'In the clear-risk scan ({kept} league decisions where the engine\'s call is clear and stable), every one of '
            f'the {count(len(models))} model setups missed more risks than it took needlessly: its bias (missed minus '
            f'needless) runs from {esc(lo_m[2])} ({esc(lo_m[1])}, League {lo_m[0]}) to {esc(hi_m[2])} ({esc(hi_m[1])}, '
            f'League {hi_m[0]}). The programs are not like that: GNUbg weak\'s bias is negative in all three leagues '
            f'({", ".join(esc(x[2]) for x in sorted(gnu, key=lambda x: x[0]))}), and so is Random\'s ({esc(rnd[2])}); '
            f'Safest, which never takes a risk, is {esc(next(x[2] for x in progs if x[1] == "Safest"))} by construction.')
    bars = []
    for lg, n, t, v in models + progs:
        fam = None if n in PROGRAMS else H.family(n)
        cls = "program" if n in PROGRAMS else ("" if fam else "other")
        bars.append((f'{esc(n)}<span class="hbar-where"> · League {lg}</span>', [(v, cls, fam["colour"] if fam else None)],
                     esc(t), f' data-program="{"yes" if n in PROGRAMS else "no"}"'))
    chart = _bars(bars, -50, 100, [(-50, "\u221250"), (0, "0"), (50, "+50"), (100, "+100 pp")], "Bias (pp)")
    legend = ('<span>Bias = missed risks (a clear Risk win played safe) minus needless risks (a clear Safety win played '
              'unsafe), in percentage points; right of 0 = too cautious</span> <span><i class="swatch swatch-program">'
              '</i>program (reference row)</span>')
    return finding("finding-cautious", "Models are too cautious", text, chart, legend,
                   "Not paired: setups met different positions, so the rows compare only loosely.", "clear-risk")


def flinch(S) -> str:
    rows = q1_bias(S)
    safer = [r for r in rows if r[2] > r[4]]
    neg = [r for r in rows if r[4] < 0]
    all_ = len(safer) == len(rows)
    # Observed, not tested (Zeki, bus #2578: no new statistics): the heading says what the two versions showed.
    heading = ("With the numbers on screen, every model asked played safer" if all_ else
               f"With the numbers on screen, {count(len(safer))} of {count(len(rows))} models asked played safer")
    big = max(rows, key=lambda r: r[2] - r[4])
    small = min(rows, key=lambda r: r[2] - r[4])
    text = (f'Asked which of two plays is better on the same rollout-confirmed positions, '
            f'{"all " + count(len(rows)) if all_ else count(len(safer)) + " of " + count(len(rows))} models chose the safe '
            f'play more often when the prompt showed each play\'s computed numbers than from the board alone: the bias '
            f'(missed minus needless) moves from {esc(big[3])} to {esc(big[1])} for {esc(big[0])} and from {esc(small[3])} '
            f'to {esc(small[1])} for {esc(small[0])}. From the board alone, {count(len(neg))} of them '
            f'({", ".join(esc(r[0]) for r in neg)}) took more needless risks than they missed.')
    bars = []
    for m, tn, vn, tb, vb in sorted(rows, key=lambda r: -r[2]):
        fam = H.family(m)
        bars.append((esc(m), [(vn, "q1-numbers", fam["colour"] if fam else None), (vb, "q1-board", None)],
                     f'{esc(tn)} | {esc(tb)}', ""))
    chart = _bars(bars, -50, 100, [(-50, "\u221250"), (0, "0"), (50, "+50"), (100, "+100 pp")],
                  '<span class="head-long">With numbers | board only (pp)</span><span class="head-short">Numbers | board</span>')
    legend = ('<span><i class="swatch" style="background:var(--text-2)"></i>with numbers (the league prompt, each play\'s '
              'computed consequences)</span> <span><i class="swatch swatch-q1-board"></i>board only (notation, no computed '
              'number)</span> <span>Bias: missed minus needless, Q1 of Clear risk Part 2</span>')
    return finding("finding-flinch", heading, text, chart, legend, "Two plays shown, not league play.", "clear-risk")


def findings(S) -> str:
    return cautious(S) + flinch(S)
