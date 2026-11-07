"""The home page as a story (Ümit, bus #2570): one headline table, one row per model at its highest reasoning setting, and
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
from common import ALL_NOTE, CONTENT, LATE_ENTRY, NA, count, esc, fmt, nm, pct

RELEASES = json.loads((CONTENT / "release_months.json").read_text())["models"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PROGRAMS = ("GNUbg weak", "Random", "Safest")


def caveat(text: str, anchor: str = "limits") -> str:
    """The one caveat of a section (Ümit, bus #2570 item 4); the others are on the Method page."""
    return (f'<p class="table-note section-caveat">{esc(text)} <a href="method/#{anchor}">More caveats: Method</a></p>')


# --- The headline table (Ümit, bus #2745) -----------------------------------------------------------------------------
# One row per model at its highest reasoning setting played: a fixed rule, never the best score. The settings in order,
# as the requests sent them (setups.json "setting"; "none" is off). "on" is the setting of a model without levels
# (thinking on or off only): above off, and a model with "on" and a level fails the build. A decision model sends no
# setting: its single setup. Version names are separate models (Jev 1.13.0, Jev 1.14.0).
LEVELS = {"off": 0, "none": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
ON = "on"
# A dated checkpoint ("DeepSeek V4.1 Flash 1017": the model name, a space, MMDD) is the same model as the name before
# the date when that is a model in the standings: one row, named and dated by the original (its first release).
CHECKPOINT = re.compile(r"^(.+) (\d{4})$")
# Late entries (not in standings) as a grey, unranked group under the ranked rows, never in the ranking: an open
# question to Ümit (bus #2745), off until he decides.
LATE_ROWS = False
# Under the table (Ümit #2745 item 3, with Zeki #2578's accepted rank sentence in place of the whisker-overlap one).
NOTE = ("Bars run to each score; the whisker is its 95% interval. Ranks show observed scores; small gaps need not be "
        "meaningful. Leagues played different positions.")


def level(setting: str | None, levelled: bool) -> int:
    """The setting's place in LEVELS (None, a decision model's: 0); levelled: the model has a setting above off."""
    if setting is None:
        return 0
    if setting == ON:
        if levelled:
            raise ValueError("a model with reasoning levels has an 'on' setup: the order of 'on' among levels is not defined")
        return 1
    if setting not in LEVELS:
        raise ValueError(f"reasoning setting {setting!r} is not one of {sorted(LEVELS)} or {ON!r}")
    return LEVELS[setting]


def release(model: str) -> tuple[str, str | None]:
    """The model's release month as its maker's page states it (content/release_months.json), else a dash."""
    e = RELEASES.get(model) or {}
    if not e.get("month"):
        return "\u2014", None
    y, m = e["month"].split("-")
    return f"{MONTHS[int(m) - 1]} {y}", e["url"]


def setting_of(S, ds, n) -> str | None:
    return P.origin_meta(S, ds, n).get("setting")


def _entry(S, lg, n, r) -> dict:
    ds = lg["dataset"]
    return dict(lg=lg, ds=ds, name=n, r=r, q=lg["setups"][n]["quality"] if n in lg["setups"] else None,
                model=H.model_of(S, ds, n), setting=setting_of(S, ds, n), late=None)


def _first_best(entries: list) -> dict:
    """best_per_model's rule for rows it does not take (programs, late entries): the highest stored risk judgement, on
    an exact tie the first in the given order."""
    best = None
    for x in entries:
        j = x["r"]["judgement"]
        if best is None or (j is not None and (best["r"]["judgement"] is None or j > best["r"]["judgement"])):
            best = x
    return best


def _top(group: list, base: str) -> list:
    """The setups of a row at the model's highest reasoning setting; the original's (not a dated checkpoint's) where it
    has one there."""
    levelled = any(level(x["setting"], False) > 0 for x in group if x["setting"] != ON)
    top = max(level(x["setting"], levelled) for x in group)
    cands = [x for x in group if level(x["setting"], levelled) == top]
    return [x for x in cands if x["model"] == base] or cands


def leaderboard_rows(S) -> tuple[list, list, list]:
    """(model rows, program rows, late-entry rows): each a (chosen setup, the row's other setups, row name, settings
    played) tuple. Model rows ranked by the chosen setup's stored risk judgement; programs (GNUbg weak, Safest, Random)
    one row each, their played setup by best_per_model's rule (computed reference rows under it); late entries (only
    with LATE_ROWS) by the same rule as the models over their own setups."""
    groups, progs = {}, {}
    rows = H.all_rows(S)
    models = {H.model_of(S, lg["dataset"], n) for lg, n, r, ref in rows if not ref}
    base_of = {}
    for lg, n, r, ref in rows:
        x = _entry(S, lg, n, r)
        if ref:
            progs.setdefault(n.removesuffix(" (computed)"), []).append(x)
            continue
        c = CHECKPOINT.match(x["model"])
        base = c.group(1) if c and c.group(1) in models else x["model"]
        base_of[(x["ds"], n)] = base
        groups.setdefault(base, []).append(x)
    top = {(x["ds"], x["name"]) for base, g in groups.items() for x in _top(g, base)}
    best = H.best_per_model(S, lambda lg, n: (lg["dataset"], n) in top, lambda lg, n: base_of[(lg["dataset"], n)])
    out = []
    for base, g in groups.items():
        cands = _top(g, base)
        chosen = next((x for x in cands if base in best and (x["ds"], x["name"]) == (best[base][0]["dataset"], best[base][1])),
                      cands[0])
        out.append((chosen, [x for x in g if x is not chosen], base, g))
    out.sort(key=lambda t: (t[0]["r"]["judgement"] is None, -(t[0]["r"]["judgement"] or 0), t[2]))
    prog_rows = []
    for name in PROGRAMS:
        g = progs.get(name, [])
        if g:
            chosen = _first_best([x for x in g if x["q"] is not None] or g)
            prog_rows.append((chosen, [x for x in g if x is not chosen], name, g))
    late = []
    if LATE_ROWS:
        lgroups = {}
        for e in S["late_entries"]:
            m = S["setups_meta"].get((LATE_ENTRY, e["name"])) or {}
            x = dict(lg=None, ds=LATE_ENTRY, name=e["name"], r=e["risk"]["main"], q=e["quality"],
                     model=m.get("model") or e["name"], setting=m.get("setting"), late=e)
            lgroups.setdefault(x["model"], []).append(x)
        for base, g in lgroups.items():
            chosen = _first_best(_top(g, base))
            late.append((chosen, [x for x in g if x is not chosen], base, g))
    return out, prog_rows, late


def share(s: dict) -> str:
    if not s["den"]:
        return f'<td class="num">{nm(NA)}<span class="small">0 / 0</span></td>'
    return f'<td class="num">{pct(s["share"])}<span class="small">{H.n_(s["n"])} / {H.n_(s["den"])}</span></td>'


def judgement_cell(r: dict, colour: str | None) -> str:
    """The risk judgement as a bar on 0 to 100 to the score, its 95% interval as the whisker, the line at 50 (always
    safe), and the number."""
    j, lo, hi = r["judgement"], r["judgement_lo"], r["judgement_hi"]
    if j is None:
        return f'<td class="num">{nm(r["judgement_na"] or NA)}</td>'
    fill = f' style="width:{j:.2f}%;background-color:{colour}"' if colour else f' style="width:{j:.2f}%"'
    return (f'<td class="hl-judgement" data-v="{j}"><span class="hl-bar" aria-hidden="true"><span class="hl-fill'
            f'{"" if colour else " other"}"{fill}></span><span class="hl-int" style="left:{lo:.2f}%;width:{hi - lo:.2f}%">'
            f'</span><span class="hl-safe"></span></span><span class="hl-val">{fmt(j)}<span class="small">{fmt(lo)} to '
            f'{fmt(hi)}</span></span></td>')


def decisions_href(S, x) -> str | None:
    """Every decision filtered to the setup (decisions/?d=…&s=…); a late entry, which Every decision does not hold, its
    own page; a computed reference row none."""
    if x["late"]:
        return P.late_href("", x["late"])
    if x["q"] is None:
        return None
    return f'decisions/?d={x["ds"]}&amp;s={P.meta(S, x["ds"], x["name"])["slug"]}'


def page_href(S, x) -> str | None:
    if x["late"]:
        return None
    return P.model_href("", x["ds"], x["name"], S) if x["q"] is not None else None


def setting_label(x) -> str:
    return esc(x["setting"]) if x["setting"] else '<span class="muted">\u2014</span>'


def cells(S, x, colour) -> str:
    """Setting, league and the numbers of one setup, as the league tables print them."""
    r, q, e = x["r"], x["q"], x["late"]
    league = (f'Late entry<span class="small">League {e["field_league"]} field</span>' if e else f'League {x["lg"]["id"]}')
    if q is None:
        er = cost = dec = f'<td class="num">{nm(NA)}</td>'
    else:
        er = (f'<td class="num">{fmt(q["error_rate"])}<span class="small">{fmt(q["error_lo"])} to {fmt(q["error_hi"])}'
              f'</span></td>' if q.get("error_rate") is not None and not q.get("too_few") else f'<td class="num">{nm(NA)}</td>')
        if e:
            cost = f'<td class="num">{P.late_cost(e)}</td>'
        elif q.get("usd_per_1000") is not None:
            label = (P.origin_meta(S, x["ds"], x["name"]).get("price") or {}).get("label")
            cost = (f'<td class="num"><span class="cost-1k">${fmt(q["usd_per_1000"], 3)}</span><span class="cost-1m" '
                    f'data-usd="{q["usd_per_1000"]!r}">${fmt(q["usd_per_1000"], 3)}</span>'
                    f'<span class="small">{esc(label or "label missing")}</span></td>')
        else:
            cost = P.cost_cell(S, x["ds"], x["name"], q)
        dec = f'<td class="num"><a href="{decisions_href(S, x)}">{count(q["decisions"])}</a></td>'
    return (f'<td class="hl-setting">{setting_label(x)}</td><td class="num" data-v="{x["lg"]["id"] if x["lg"] else 9}">'
            f'{league}</td>{judgement_cell(r, colour)}{share(r["found"])}{share(r["right_safety"])}{er}{cost}{dec}')


def name_link(S, x, text) -> str:
    href = decisions_href(S, x)
    return (f'<a class="model-name" href="{href}">{esc(text)}</a>' if href else f'<span class="model-name">{esc(text)}</span>')


def tr_attrs(S, x, kind) -> str:
    if x["late"]:
        return f' data-dataset="{LATE_ENTRY}" data-setup="{esc(x["late"]["slug"])}" data-kind="late"'
    return H.attrs(S, x["ds"], H.slug_name(x["name"]), kind == "program")


def headline_rows(S) -> tuple[list, list, list]:
    """The table rows (each followed by its hidden other-settings rows) and the models without a release month."""
    ranked, progs, late = leaderboard_rows(S)
    body, missing, chart = [], [], []
    for kind, rows in (("model", ranked), ("program", progs), ("late", late)):
        if kind == "program" and rows:
            body.append(f'<tr class="hl-group"><th scope="rowgroup" colspan="{len(HEADLINE_HEAD)}">Programs: reference rows, '
                        f'never ranked</th></tr>')
        if kind == "late" and rows:
            body.append(f'<tr class="hl-group"><th scope="rowgroup" colspan="{len(HEADLINE_HEAD)}">Late entries (not ranked): '
                        f'added after the standings, their own late-entry games, never in the ranking</th></tr>')
        for i, (x, others, name, group) in enumerate(rows, 1):
            mk, colour = H.maker(x["name"]) if kind == "model" else (None, None)
            fam = H.family(x["name"]) if kind != "program" else None
            icon = f'<svg class="fam-icon" aria-hidden="true" focusable="false"><use href="#{fam["icon"]}"/></svg>' if fam else ""
            dot = f'<i class="swatch hl-dot" style="background:{colour}" title="{esc(mk)}"></i>' if colour else \
                '<i class="swatch hl-dot swatch-program"></i>'
            bits = []
            if kind == "model":
                month, url = release(name)
                if not url:
                    missing.append(name)
                bits.append(f'Released <a href="{esc(url)}">{month}</a>' if url else
                            f'Released <span class="muted" title="No release date from the maker on record">{month}</span>')
                ckpt = sorted({y["model"] for y in group if y["model"] != name})
                if ckpt:
                    bits.append("with its dated checkpoint " + ", ".join(esc(c) for c in ckpt))
            elif kind == "program":
                bits.append(esc(H.ref_label(S, x["ds"], x["name"]) or ""))
            page = page_href(S, x)
            if page:
                bits.append(f'<a href="{page}">model page</a>')
            rid = f'hl-{"p-" if kind == "program" else "l-" if kind == "late" else ""}{i}'
            sub_ids = [f"{rid}-{k}" for k in range(1, len(others) + 1)]
            what = "league" if kind == "program" else "setting"
            more = (f'<button type="button" class="hl-more needs-js" aria-expanded="false" aria-controls="{" ".join(sub_ids)}">'
                    f'{count(len(others))} other {what}{"s" if len(others) > 1 else ""}</button>' if others else "")
            rank = f'<td class="num">{i}</td>' if kind == "model" else '<td class="num"><span class="muted" title="never ranked">\u2013</span></td>'
            cls = {"model": "", "program": ' class="reference"', "late": ' class="late"'}[kind]
            label = x["name"] if kind == "program" else name
            body.append(f'<tr{cls}{tr_attrs(S, x, kind)}>{rank}<td class="model">{dot}{icon}{name_link(S, x, label)}'
                        f'<span class="small">{" · ".join(b for b in bits if b)}</span>{more}</td>'
                        f'{cells(S, x, colour)}</tr>')
            for sid, y in zip(sub_ids, others):
                ycol = H.maker(y["name"])[1] if kind == "model" else None
                ypage = page_href(S, y)
                page_link = f' · <a href="{ypage}">model page</a>' if ypage else ""
                body.append(f'<tr class="hl-sub{"" if kind == "model" else " reference" if kind == "program" else " late"}" '
                            f'id="{sid}" hidden{tr_attrs(S, y, kind)}><td class="num"></td><td class="model">'
                            f'{name_link(S, y, y["name"])}<span class="small">other {what} of {esc(label)}'
                            f'{page_link}</span></td>{cells(S, y, ycol)}</tr>')
            if kind != "program" or x["name"] == "GNUbg weak":
                chart.append((kind, label, x, colour))
    return body, missing, chart


HEADLINE_HEAD = [(h, " data-nosort") for h in (
    "#", "Model", "Setting", "League", "Risk judgement (95% interval)", "Risks found", "Right safety", "Error rate (PR)",
    '<span class="cost-1k">$ per 1,000 decisions</span><span class="cost-1m">$ per 1M decisions</span>', "Decisions")]


def too_safe(chart: list) -> str:
    """"Too safe" (Ümit #2745 item 6): per row of the table, right safety (played safe when safe was right) and risks
    found (took the risk when it paid), the stored shares; GNUbg weak as the grey reference pair."""
    bars = []
    legend_makers = H.maker_legend(x["name"] for kind, label, x, colour in chart if kind == "model")
    for kind, label, x, colour in chart:
        rs, rf = x["r"]["right_safety"], x["r"]["found"]
        grey = kind != "model"
        val = lambda s: s["share"] * 100 if s["den"] else 0
        text = lambda s: pct(s["share"]) if s["den"] else nm(NA)
        where = (f' · League {x["lg"]["id"]}' if x["lg"] else " · late entry")
        bars.append((f'{esc(label)}<span class="hbar-where">{esc(where)}</span>',
                     [(val(rs), "ts-safety" + (" ts-grey" if grey else ""), None if grey else colour),
                      (val(rf), "ts-found" + (" ts-grey" if grey else ""), None if grey else colour)],
                     f'{text(rs)} | {text(rf)}', f' data-setup="{esc(x["name"])}"' + (' data-program="yes"' if kind == "program" else "")))
    chart_html = _bars(bars, 0, 100, [(0, "0%"), (25, "25%"), (50, "50%"), (75, "75%"), (100, "100%")],
                       '<span class="head-long">Right safety | risks found</span><span class="head-short">Safety | found</span>',
                       zero=False)
    legend = ('<span><i class="swatch swatch-ts-safety"></i>right safety: played safe when safe was right</span> '
              '<span><i class="swatch swatch-ts-found"></i>risks found: took the risk when it paid</span> '
              '<span><i class="swatch swatch-ts-grey"></i>GNUbg weak, a program: the grey reference pair</span> '
              f'<span>Bars in the maker\'s colour, the same rows as the table:</span> <span class="families">{legend_makers}</span>')
    return (f'<figure class="chart-card chart-wide finding-chart too-safe" id="too-safe"><div class="chart-head">'
            f'<h3>Too safe</h3><p class="chart-sub">Each model\'s row of the table: the share of its right-safety calls '
            f'and of the risks it found, as in the table</p></div>{chart_html}<p class="chart-legend">{legend}</p></figure>')


def headline(S) -> str:
    """One row per model at its highest reasoning setting (a fixed rule, not the best score), its other settings
    behind a per-row expander, the programs as grey unranked rows; the All setups key shows the full All leagues risk
    table (every setup, programs as reference rows) in its place. The Too safe chart under it."""
    rows, missing, chart = headline_rows(S)
    n_models = len(leaderboard_rows(S)[0])
    table = P.table(HEADLINE_HEAD, rows, "One row per model: the model's highest reasoning setting played (a fixed "
                    "rule, not its best score; every cell of a row is that setup's own); its other settings under the row's "
                    "expander and under All setups. All leagues, all phases.", cls="board headline",
                    attrs=' data-dataset="all" id="headline-table"')
    note = (f'<p class="table-note">Released: the month of the maker\'s own dated statement that this exact model was '
            f'released or became available to the public (an announcement before public availability does not count), '
            f'linked; \u2014 where no such statement is on record ({count(len(missing))} of {count(n_models)} models).</p>'
            if missing else "")
    keys = ('<span class="keys needs-js" role="group" aria-label="Rows"><button type="button" class="key" '
            'data-headline-view="model" aria-pressed="true">One row per model</button><button type="button" '
            'class="key" data-headline-view="all" aria-pressed="false">All setups</button></span>')
    return (f'<section class="card headline" id="leaderboard" data-dataset="all" aria-labelledby="leaderboard-title">'
            f'<div class="chart-head"><h2 id="leaderboard-title">Risk calls leaderboard</h2>{keys}<p class="chart-sub">'
            f'Risk judgement: 100 = every call right, 50 = always safe; the bar runs to the score, the whisker is its 95% '
            f'interval, the mark at 50 the always-safe line · higher is better</p></div>'
            f'<p class="table-note">{esc(ALL_NOTE)}</p>'
            '<p class="table-note headline-scope"><strong>A fixed table:</strong> all leagues, all phases, every model; '
            'the filter row below does not change it. Each model\'s row is its highest reasoning setting played, by the '
            'effort the requests sent (off &lt; minimal &lt; low &lt; medium &lt; high &lt; xhigh &lt; max; on above off for a model '
            'without levels; a decision model\'s single setup), not its best score; at the same setting in two places, '
            'the one with the higher stored risk judgement (on an exact tie, the first in league order). Version names '
            'are separate models; a dated checkpoint shares its model\'s row. Tap a model for its decisions.</p>'
            f'<div data-headline-panel="model">{P.SWIPE}{table}{caveat(NOTE, "statistics")}{note}{too_safe(chart)}</div>'
            f'<div data-headline-panel="all" hidden>{H.all_risk_table(S)}{caveat(H.RANK_NOTE, "statistics")}</div>'
            f'</section>')


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
        colour = None if n in PROGRAMS else H.maker(n)[1]
        bars.append((f'{esc(n)}<span class="hbar-where"> · League {lg}</span>', [(v, "program" if n in PROGRAMS else "", colour)],
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
        bars.append((esc(m), [(vn, "q1-numbers", H.maker(m)[1]), (vb, "q1-board", None)],
                     f'{esc(tn)} | {esc(tb)}', ""))
    chart = _bars(bars, -50, 100, [(-50, "\u221250"), (0, "0"), (50, "+50"), (100, "+100 pp")],
                  '<span class="head-long">With numbers | board only (pp)</span><span class="head-short">Numbers | board</span>')
    legend = ('<span><i class="swatch" style="background:var(--text-2)"></i>with numbers (the league prompt, each play\'s '
              'computed consequences)</span> <span><i class="swatch swatch-q1-board"></i>board only (notation, no computed '
              'number)</span> <span>Bias: missed minus needless, Q1 of Clear risk Part 2</span>')
    return finding("finding-flinch", heading, text, chart, legend, "Two plays shown, not league play.", "clear-risk")


def findings(S) -> str:
    return cautious(S) + flinch(S)
