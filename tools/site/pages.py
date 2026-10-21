"""Pages of the backgammon site. Every number comes from S (build.compute), the same dicts that build.py
writes to data/; nothing here holds a result number. Status words follow brief B10."""

import json
from pathlib import Path

import analysis as A
from common import (EARLIER, EARLIER_NOTE, NA, NOT_MEASURED, PENDING, PROVISIONAL, PROVISIONAL_NOTE, PUBLISHED,
                    TOO_FEW, count, esc, fmt, nm, pct, slug, status_badge)

NAV = [("decisions/", "Every decision"), ("disagreements/", "Where models disagree"), ("phases/", "Phases"),
       ("compare/", "Compare"), ("models/", "Models"), ("leagues/", "Leagues"), ("new-models/", "New models"),
       ("method/", "Method"), ("data/", "Data")]
TABS = [("quality", "Quality"), ("risk", "Risk"), ("reasoning", "Reasoning"), ("confidence", "Confidence"),
        ("routing", "Routing"), ("stability", "Stability"), ("cost", "Cost")]
TITLE = "How well do models decide under risk?"
SUBTITLE = "We compare move quality, reasoning, confidence and cost using engine-scored backgammon decisions."
SWIPE = '<p class="swipe-hint" data-swipe-hint>Swipe for more columns \u2192</p>'
PHASE_LABEL = {"opening": "Opening", "contact": "Contact", "holding": "Holding game", "race": "Race",
               "bear-off": "Bear-off"}


# --- Formatting ---------------------------------------------------------------------------------------

def as_of(S) -> str:
    from datetime import datetime
    t = datetime.strptime(S["as_of"], "%Y-%m-%dT%H:%MZ")
    return t.strftime("%-d %B %Y, %H:%M UTC")


def version_line(S) -> str:
    return f"Results {S['hash']}, data as of {as_of(S)}."


def band(S, er) -> str:
    for b in S["human_scale"]["bands"]:
        if b["below"] is None or er < b["below"]:
            return b["label"]
    return ""


def secs(x) -> str:
    if x is None:
        return nm(NOT_MEASURED)
    return fmt(x, 2 if x < 10 else 1)


def eq(x) -> str:
    return fmt(x, 3)


def er_cell(q) -> str:
    if q.get("error_rate") is None:
        return f'<td class="num">{nm("Not scored yet")}</td>'
    if q.get("too_few"):
        return f'<td class="num">{nm(TOO_FEW)}</td>'
    return (f'<td class="num">{fmt(q["error_rate"])}<span class="small">{fmt(q["error_lo"])} to '
            f'{fmt(q["error_hi"])}</span></td>')


def val(q, key, f, too_few_key="too_few") -> str:
    """A value cell: the value, 'Too few decisions' below the minimum, or the status when there is no value."""
    if q.get(too_few_key):
        return f'<td class="num">{nm(TOO_FEW)}</td>'
    v = q.get(key)
    return f'<td class="num">{f(v) if v is not None else nm(NA)}</td>'


def table(head: list[str], rows: list[str], caption: str, cls="board", attrs="") -> str:
    th = "".join(f'<th scope="col"{" class=num" if i else ""}>{h}</th>' for i, h in enumerate(head))
    return (f'<div class="table-wrap"><table class="{cls}"{attrs}><caption>{caption}</caption><thead><tr>{th}</tr>'
            f'</thead><tbody>{"".join(rows)}</tbody></table></div>')


def pending_table(head: list[str], caption: str, what: str) -> str:
    th = "".join(f'<th scope="col">{h}</th>' for h in head)
    return (f'<div class="table-wrap"><table class="board"><caption>{caption}</caption><thead><tr>{th}</tr></thead>'
            f'<tbody><tr><td colspan="{len(head)}">{status_badge(PENDING)} {esc(what)}</td></tr></tbody></table></div>')


# --- Setups ---------------------------------------------------------------------------------------------

def meta(S, dataset, name) -> dict:
    m = S["setups_meta"].get((dataset, name))
    if m:
        return m
    return dict(dataset=dataset, name=name, slug=slug(name), model=name, setting=None, model_type=None,
                weights=None, runs_on=None, confidence_source=None, missing=["every B7 field"], sources=[])


def model_href(rel, dataset, name, S) -> str:
    return f"{rel}models/{dataset}/{meta(S, dataset, name)['slug']}/"


def row_attrs(S, dataset, name) -> str:
    m = meta(S, dataset, name)
    return (f' data-dataset="{esc(dataset)}" data-type="{esc(m.get("model_type") or "unknown")}"'
            f' data-weights="{esc(m.get("weights") or "unknown")}" data-runs="{esc(m.get("runs_on") or "unknown")}"'
            f' data-setting="{esc(m.get("setting") or "none")}"')


def model_cell(S, rel, dataset, name) -> str:
    m = meta(S, dataset, name)
    bits = [x for x in (m.get("setting") and f"{m['setting']}", m.get("model_type"), m.get("runs_on")) if x]
    return (f'<td class="model"><a class="model-name" href="{model_href(rel, dataset, name, S)}">{esc(name)}</a>'
            f'<span class="small">{esc(" · ".join(bits))}</span></td>')


def tr(S, dataset, name, cells: str, rel: str) -> str:
    return f"<tr{row_attrs(S, dataset, name)}>{model_cell(S, rel, dataset, name)}{cells}</tr>"


def by_error(setups: dict) -> list[str]:
    def key(n):
        q = setups[n]["quality"]
        return (q.get("error_rate") is None or q.get("too_few", False), q.get("error_rate") or 0, n)
    return sorted(setups, key=key)


def cost_cell(S, dataset, name, q) -> str:
    m = meta(S, dataset, name)
    label = (m.get("price") or {}).get("label")
    if q.get("usd_per_1000") is None:
        why = NOT_MEASURED if q.get("cost_coverage", 0) == 0 else f"Priced for {pct(q['cost_coverage'], 0)} of decisions"
        return f'<td class="num">{nm(why)}</td>'
    return f'<td class="num">{fmt(q["usd_per_1000"], 3)}<span class="small">{esc(label or "label missing")}</span></td>'


# --- Shared blocks ----------------------------------------------------------------------------------------

def league_status_text(lg) -> str:
    s = status_badge(lg["status"])
    if lg["metric_status"] == PROVISIONAL:
        s += status_badge(PROVISIONAL_NOTE)
    else:
        s += status_badge(PUBLISHED)
    return s


def play_order_note(S) -> str:
    p = S["v1"]["play_order"]
    return (f"{EARLIER_NOTE} When {p['setup']} answered the same {count(p['positions'])} positions with the plays "
            f"shuffled, its error rate changed by {fmt(p['diff'], 1, True)} (95% interval {fmt(p['lo'], 1, True)} to "
            f"{fmt(p['hi'], 1, True)}), so the effect is not proven.")


def earlier_block(S, inner: str, title: str) -> str:
    return (f'<div class="block" data-version="v1"><div class="section-head"><h3>{esc(title)}</h3>'
            f'{status_badge(EARLIER)}</div><p class="note">{esc(play_order_note(S))} v1 used an earlier prompt; '
            f'these numbers never share a table or chart with v3 numbers.</p>{inner}</div>')


def quality_rows(S, rel, dataset, setups) -> list[str]:
    rows = []
    for n in by_error(setups):
        q = setups[n]["quality"]
        b = band(S, q["error_rate"]) if q.get("error_rate") is not None and not q.get("too_few") else None
        cells = (er_cell(q) + f'<td class="num">{esc(b) + " (approx.)" if b else nm(NA)}</td>'
                 + val(q, "best_share", pct) + val(q, "blunder_share", pct)
                 + f'<td class="num">{secs(q.get("time_median"))} / {secs(q.get("time_p90"))}</td>'
                 + cost_cell(S, dataset, n, q)
                 + f'<td class="num">{count(q["scored"])}'
                 + (f'<span class="mark" title="Some decisions had their plays split into groups">\u2020</span>'
                    f'<span class="small">{count(q["grouped"])} split into groups</span>' if q.get("grouped") else "")
                 + f'</td><td class="num">{count(q["invalid"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    return rows


QUALITY_HEAD = ["Model and setting", "Error rate (PR), 95% interval", "Band on the human scale",
                "Engine's best play", "Blunder rate", "Median / P90 s per decision", "$ per 1,000 decisions",
                "Decisions scored", "Invalid answers"]


def risk_rows(S, rel, dataset, setups) -> list[str]:
    rows = []
    for n in by_error(setups):
        r, q = setups[n]["risk"], setups[n]["quality"]
        cells = (val(r, "takes_risk", pct, "risk_too_few") + val(r, "needless_risk", pct, "safety_too_few")
                 + val(q, "p95_loss", eq) + val(q, "worst_mean", eq) + val(q, "blunder_share", pct)
                 + f'<td class="num">{count(r["risk_pays"])} / {count(r["safety_pays"])}</td>'
                 + f'<td class="num">{count(q["invalid"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    return rows


RISK_HEAD = ["Model and setting", "Takes the risk when it pays", "Takes a needless risk", "P95 equity loss",
             "Mean loss, worst 5%", "Blunder rate", "Decisions: risk pays / safety pays", "Invalid answers"]


def confidence_rows(S, rel, dataset, setups) -> list[str]:
    rows = []
    for n in by_error(setups):
        q = setups[n]["quality"]
        src = meta(S, dataset, n).get("confidence_source") or "unknown"
        if q.get("confidence_n") is None:
            cells = f'<td>{esc(src)}</td>' + "".join(f'<td class="num">{nm(NA)}</td>' for _ in range(5))
        else:
            tf = A.too_few(q["confidence_n"])
            g = (lambda k, f: f'<td class="num">{nm(TOO_FEW) if tf else (f(q[k]) if q.get(k) is not None else nm(NA))}</td>')
            cells = (f'<td>{esc(src)}</td>' + g("auroc", lambda v: fmt(v, 2)) + g("ece", lambda v: fmt(v, 3))
                     + g("brier", lambda v: fmt(v, 3)) + g("confident_badly_wrong", pct)
                     + f'<td class="num">{count(q["confidence_n"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    return rows


CONF_HEAD = ["Model and setting", "Confidence source", "AUROC", "ECE", "Brier score", "Confident and badly wrong",
             "Decisions with probabilities"]


def cost_rows(S, rel, dataset, setups) -> list[str]:
    rows = []
    for n in by_error(setups):
        q = setups[n]["quality"]
        cells = (cost_cell(S, dataset, n, q)
                 + f'<td class="num">{secs(q.get("time_median"))} / {secs(q.get("time_p90"))}</td>'
                 + f'<td class="num">{secs(q.get("retry_mean")) if q.get("retry_mean") is not None else nm(NOT_MEASURED)}</td>'
                 + val(q, "over_budget", pct)
                 + f'<td class="num">{fmt(q["tokens_in"], 0) + " / " + fmt(q["tokens_out"], 0) if q.get("tokens_in") else nm(NOT_MEASURED)}</td>'
                 + f'<td class="num">{pct(q.get("cost_coverage", 0), 0)}</td><td class="num">{count(q["decisions"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    return rows


COST_HEAD = ["Model and setting", "$ per 1,000 decisions", "Median / P90 s per decision", "Mean retry/wait s",
             "Over the time budget", "Tokens in / out per decision", "Cost coverage", "Decisions"]


def reasoning_rows(S, items) -> list[str]:
    rows = []
    for r in items:
        phases = " · ".join(
            f'{PHASE_LABEL[p]}: {TOO_FEW if v["too_few"] else fmt(v["diff"], 1, True) + " (" + v["verdict"] + ")"}'
            for p, v in r["phases"].items())
        rows.append(f'<tr data-dataset="v1-set"><td class="model"><span class="model-name">{esc(r["model"])}</span>'
                    f'<span class="small">{esc(r["low"])} \u2192 {esc(r["high"])}</span></td>'
                    f'<td class="num">{fmt(r["diff"], 1, True)}<span class="small">{fmt(r["lo"], 1, True)} to {fmt(r["hi"], 1, True)}</span></td>'
                    f'<td class="verdict">{esc(r["verdict"])}<span class="small">By phase (exploratory): {esc(phases)}</span></td>'
                    f'<td class="num">{count(r["fixed"])} / {count(r["broken"])}</td>'
                    f'<td class="num">{eq(r["fixed_loss"])} / {eq(r["broken_loss"])}</td>'
                    f'<td class="num">{fmt(r["extra_time_median"], 1, True)}</td>'
                    f'<td class="num">{fmt(r["extra_cost"], 3, True) if r.get("extra_cost") is not None else nm(NOT_MEASURED)}</td>'
                    f'<td class="num">{count(r["positions"])}</td></tr>')
    return rows


REASON_HEAD = ["Model", "Paired error difference (higher minus lower setting), 95% interval", "Verdict",
               "Blunders fixed / broken", "Equity regained / lost in total", "Extra median s per decision",
               "Extra $ per 1,000 decisions", "Positions"]


# --- Layout -------------------------------------------------------------------------------------------------

def layout(S, base, path: str, title: str, body: str, description: str | None = None, main_class: str = "",
           scripts=(), styles=(), body_class: str = "") -> str:
    depth = path.count("/")
    rel = "../" * depth
    desc = description or S["description"]
    full = f"{title} · Zeki Works" if title != TITLE else f"{TITLE} · Zeki Works"
    image = f'{base}{S["image"]}' if S.get("image") else None
    og = (f'<meta property="og:image" content="{image}"><meta property="og:image:width" content="1200">'
          f'<meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">'
          f'<meta name="twitter:image" content="{image}">') if image else ""
    nav = "".join(f'<li><a href="{rel}{href}"{" aria-current=page" if path.startswith(href) else ""}>{esc(label)}</a></li>'
                  for href, label in NAV)
    css = "".join(f'<link rel="stylesheet" href="{rel}{s}">' for s in ("site.css", "bg.css") + tuple(styles))
    js = "".join(f'<script src="{rel}{s}" defer></script>' for s in ("site.js",) + tuple(scripts))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>{esc(full)}</title>
  <link rel="canonical" href="{base}{path}">
  <meta name="description" content="{esc(desc)}">
  <meta property="og:title" content="{esc(full)}"><meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website"><meta property="og:url" content="{base}{path}">
  <meta name="twitter:title" content="{esc(full)}"><meta name="twitter:description" content="{esc(desc)}">
  {og}
  <script>document.documentElement.classList.add("js"); try {{ if (localStorage.getItem("theme") === "light") document.documentElement.dataset.theme = "light"; }} catch (e) {{}}</script>
  {css}
  {js}
</head>
<body class="v3 {body_class}">
  <a class="skip" href="#main">Skip to content</a>
  <header class="topbar">
    <a class="brand" href="{rel or './'}">Zeki Works · Backgammon benchmark · v3 preview</a>
    <nav class="nav" aria-label="Pages"><ul>{nav}</ul></nav>
    <div class="theme-switch" role="group" aria-label="Colour theme" hidden><button type="button" class="key" data-theme-choice="dark" aria-pressed="true" aria-label="Dark background"><span class="lamp" aria-hidden="true"></span>Dark<span class="long"> background</span></button><button type="button" class="key" data-theme-choice="light" aria-pressed="false" aria-label="Light background"><span class="lamp" aria-hidden="true"></span>Light<span class="long"> background</span></button></div>
  </header>
  <main id="main"{f' class="{main_class}"' if main_class else ''}>
{body}
  </main>
  <footer class="footer">
    <p>Download: <a href="{rel}data/">data files</a> · <a href="{rel}data/manifest.json">manifest.json</a></p>
    <p>{esc(version_line(S))}</p>
  </footer>
</body>
</html>
"""


def page_head(S, eyebrow: str, title: str, intro: str = "") -> str:
    return (f'<header class="hero"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1>'
            f'{f"<p class=intro>{intro}</p>" if intro else ""}<p class="version">{esc(version_line(S))}</p></header>')


# --- Home ---------------------------------------------------------------------------------------------------

def shared_note(S) -> str:
    sh = S["shared"]
    p = sh["parts"]
    return (f'<p class="tab-notes" id="shared-positions">The shared positions: {count(sh["standard"])} standard positions '
            f'({count(p["v1"]["positions"])} from the earlier v1 league games and {count(p["new"]["positions"])} from GNUbg '
            f'self-play at expert level, {count(p["new"]["positions"] // 5)} per game phase), plus '
            f'{count(p["nackgammon"]["positions"])} Nackgammon positions and a {count(p["opening-control"]["positions"])}-position '
            f'opening control. Every standard position has {sh["min_plays"]} to {sh["max_plays"]} legal plays, so no '
            f'play list is split into groups. Every setup answers the same positions; this set, not the league tables, '
            f'compares setups across leagues. <a href="method/#shared-positions">How they were drawn</a>.</p>')


def readouts(S) -> str:
    scored = sum(lg["scored"] for lg in S["leagues"])
    setups = sum(len(lg["setups"]) for lg in S["leagues"])
    items = [(count(scored), "league decisions engine-scored"), (count(len(S["leagues"])), "leagues"),
             (count(setups), "league setups"), (count(S["shared"]["standard"]), "shared positions")]
    return "".join(f'<li class="readout"><span class="readout-value">{v}</span> <span class="readout-label">{l}</span></li>'
                   for v, l in items)


def filters(S) -> str:
    def group(key, label, values):
        keys = "".join(f'<button type="button" class="key" data-filter-{key}="{esc(v)}" aria-pressed="{str(v == "all").lower()}">'
                       f'<span class="lamp" aria-hidden="true"></span>{esc(v.capitalize() if v != "all" else "All")}</button>'
                       for v in ["all"] + values)
        return (f'<div class="group" role="group" aria-labelledby="f-{key}"><span class="group-label" id="f-{key}">{label}</span>'
                f'<span class="keys" data-control="{key}">{keys}</span></div>')
    ms = list(S["setups_meta"].values())
    types = sorted({m["model_type"] for m in ms if m.get("model_type")})
    weights = sorted({m["weights"] for m in ms if m.get("weights")})
    runs = sorted({m["runs_on"] for m in ms if m.get("runs_on")})
    settings = sorted({m["setting"] for m in ms if m.get("setting")})
    return f"""<section class="panel filters needs-js" id="filters" aria-label="Filters">
      <div class="filters-bar">
        <button type="button" class="key toggle" data-control="filters" aria-expanded="false" aria-controls="filters-body"><span class="chevron" aria-hidden="true"></span>Filters</button>
        <p class="filters-summary" data-summary aria-live="polite">All setups</p>
        <button type="button" class="key reset" data-control="reset">Reset</button>
      </div>
      <div class="filters-body" id="filters-body">
        {group("type", "Model type", types)}{group("weights", "Weights", weights)}{group("runs", "Runs on", runs)}{group("setting", "Reasoning setting", settings)}
      </div>
    </section>"""


def tab_panel(S, key: str) -> str:
    rel = ""
    v1 = S["v1"]["setups"]
    cap = "Earlier version: v1 set, {n} positions, {k} setups".format(n=count(S["v1"]["positions"]), k=count(len(v1)))
    if key == "quality":
        main = pending_table(QUALITY_HEAD, "Shared positions (v3): error rate per setup",
                             "No setup has answered the shared positions yet; this table fills in when they do.")
        earlier = earlier_block(S, SWIPE + table(QUALITY_HEAD, quality_rows(S, rel, "v1-set", v1), cap, attrs=' data-version="v1"'),
                                "Earlier version: the v1 set")
        note = ('<p class="tab-notes">Error rate (PR): 500 \u00d7 the mean equity a setup gives away per decision, '
                'against GNUbg 2-ply; lower is better. The band is approximate: human ratings include doubling-cube '
                'decisions and these games have none. Invalid answers are counted, never scored as the model\'s choice. '
                'Failed requests: a request that fails after retries leaves no decision, so they are not counted here.</p>')
        return main + shared_note(S) + note + earlier
    if key == "risk":
        main = pending_table(RISK_HEAD, "Shared positions (v3): risk per setup", "Waits for the shared-position answers.")
        earlier = earlier_block(S, SWIPE + table(RISK_HEAD, risk_rows(S, rel, "v1-set", v1), cap, attrs=' data-version="v1"'),
                                "Earlier version: the v1 set")
        return (main + '<p class="tab-notes">League decisions, per league: <a href="#risk-worth">Is the risk worth it?</a> '
                'and <a href="#risk-confidence">Risk and confidence</a>.</p>' + earlier)
    if key == "reasoning":
        main = pending_table(REASON_HEAD, "Shared positions (v3): the same model at two settings, paired",
                             "Waits for the shared-position answers. League games give each setting different positions, so they cannot be paired.")
        earlier = earlier_block(S, SWIPE + table(REASON_HEAD, reasoning_rows(S, S["v1"]["reasoning"]),
                                                 "Earlier version: v1 set, paired on the same positions", attrs=' data-version="v1"'),
                                "Earlier version: the v1 set")
        return main + earlier
    if key == "confidence":
        main = pending_table(CONF_HEAD, "Shared positions (v3): confidence per setup", "Waits for the shared-position answers.")
        earlier = earlier_block(S, SWIPE + table(CONF_HEAD, confidence_rows(S, rel, "v1-set", v1), cap, attrs=' data-version="v1"'),
                                "Earlier version: the v1 set")
        note = ('<p class="tab-notes">Confidence metrics are N/A for setups that return only a choice: their recorded 1.0 '
                'is not 100% confidence. Compare confidence only between setups with the same confidence source. '
                '"Right" means the engine\'s best play.</p>')
        return main + note + earlier
    if key == "routing":
        return (pending_table(["First model", "Second model", "Error rate", "$ per 1,000 decisions", "Share handed on", "Cutoff"],
                              "Shared positions (v3): a cheap model first, a strong model on the rest",
                              "Waits for the shared-position answers.")
                + '<p class="tab-notes">The team results of the earlier version are on the <a href="leagues/#earlier">Leagues page</a> (Earlier version). '
                  'A team "oracle" (the best answer any member gave) is only an upper bound, never a working system.</p>')
    if key == "stability":
        return (pending_table(["Model and setting", "Positions asked 5 times", "Share where the play changed"],
                              "Shared positions (v3): the same position asked again", "Waits for the repeat answers.")
                + f'<p class="tab-notes">Earlier version: {nm(NOT_MEASURED)} (v1 asked every position once).</p>')
    if key == "cost":
        main = pending_table(COST_HEAD, "Shared positions (v3): time and cost per setup", "Waits for the shared-position answers.")
        earlier = earlier_block(S, SWIPE + table(COST_HEAD, cost_rows(S, rel, "v1-set", v1), cap, attrs=' data-version="v1"'),
                                "Earlier version: the v1 set")
        note = ('<p class="tab-notes">Three cost labels never mix: API price estimate, API-equivalent (subscription runs) '
                'and own hardware. Request time is shown apart from retry and wait time. The v3 leagues had no clock, '
                'so the risk of running over a time budget was not measured; "Over the time budget" is the share of '
                'request times above it. League time and cost: <a href="leagues/">Leagues</a>.</p>')
        return main + note + earlier
    raise KeyError(key)


DEFINITIONS = {
    "quality": "Move quality on the shared positions: error rate with its 95% interval, the share of engine-best plays and of blunders.",
    "risk": "The decisions that averages hide: tail losses, blunders, and whether risks were taken when they paid.",
    "reasoning": "The same model at two reasoning settings, paired on the same positions, with the verdict rule from Method.",
    "confidence": "Whether a model's probability for its play shows when the play is right.",
    "routing": "Whether a cheap model can answer first and hand the hard positions to a strong one.",
    "stability": "Whether a setup repeats its play when asked the same position again.",
    "cost": "Dollars per 1,000 decisions and seconds per decision.",
}

CHARTS = [("error-cost", "Error vs cost (log cost axis, line through the best-value setups)"),
          ("error-time", "Error vs median time per decision"),
          ("paired", "Paired low \u2192 high, per model"),
          ("risk-coverage", "Risk\u2013coverage curves"),
          ("phase-heatmap", "Game phase \u00d7 model"),
          ("risk-2x2", "Is the risk worth it? 2 \u00d7 2")]


def v1_chart(S) -> str:
    """Earlier version only: v1-set error rates with 95% intervals, as an SVG dot plot."""
    setups = S["v1"]["setups"]
    names = by_error(setups)
    hi = max(setups[n]["quality"]["error_hi"] for n in names)
    top = (int(hi / 10) + 1) * 10
    w, left, row = 640, 200, 22
    h = 30 + row * len(names)
    x = lambda v: left + (w - left - 20) * v / top
    parts = [f'<svg class="chart-svg" viewBox="0 0 {w} {h}" role="img" aria-label="v1 set error rates with 95% intervals">']
    for t in range(0, top + 1, 10):
        parts.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="10" y2="{h - 20}"/>'
                     f'<text x="{x(t):.1f}" y="{h - 5}" text-anchor="middle" class="muted">{t}</text>')
    for i, n in enumerate(names):
        q = setups[n]["quality"]
        y = 22 + i * row
        parts.append(f'<text x="{left - 8}" y="{y + 4}" text-anchor="end">{esc(n)}</text>'
                     f'<line class="whisker" x1="{x(q["error_lo"]):.1f}" x2="{x(q["error_hi"]):.1f}" y1="{y}" y2="{y}" stroke-width="2"/>'
                     f'<circle class="dot" cx="{x(q["error_rate"]):.1f}" cy="{y}" r="4"><title>{esc(n)}: {fmt(q["error_rate"])}</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


def charts(S) -> str:
    cards = "".join(f'<figure class="panel chart-card" id="chart-{k}"><div class="chart-head"><h2>{esc(t)}</h2></div>'
                    f'<p class="chart-status">{status_badge(PENDING)} Shared positions (v3): waits for the shared-position answers.</p></figure>'
                    for k, t in CHARTS)
    v1 = (f'<figure class="panel chart-card" id="chart-v1-error" data-version="v1"><div class="chart-head"><h2>Error rate (PR) with 95% interval, v1 set</h2>'
          f'{status_badge(EARLIER)}</div><p class="note">{esc(play_order_note(S))}</p>{v1_chart(S)}</figure>')
    return f'<section class="charts" id="charts" aria-label="Charts" tabindex="-1">{cards}{v1}</section>'


def risk_table(S, rel, dataset, setups) -> str:
    rows = []
    for n in by_error(setups):
        r = setups[n]["risk"]
        c = r["cells"]
        cell = (lambda k: f'<td class="num">{nm(TOO_FEW)}<span class="small">{count(c[k]["n"])}</span></td>'
                if A.too_few(c[k]["n"]) else
                f'<td class="num">{pct(c[k]["share"])}<span class="small">'
                f'{eq(c[k]["mean_loss"]) if c[k]["mean_loss"] is not None else "\u2013"}'
                f'{" · conf. " + fmt(c[k]["confidence"], 2) if c[k]["confidence"] is not None else ""}</span></td>')
        if r["decisions"] == 0:
            cells = f'<td class="num" colspan="7">{nm("Not scored yet" if not setups[n]["quality"]["scored"] else NA)}</td>'
        else:
            cells = (val(r, "takes_risk", pct, "risk_too_few") + val(r, "needless_risk", pct, "safety_too_few")
                     + cell("risk_took") + cell("risk_safe") + cell("safety_took") + cell("safety_safe")
                     + f'<td class="num">{count(r["decisions"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    head = ["Model and setting", "Takes the risk when it pays", "Takes a needless risk",
            "Risk pays: took the risk", "Risk pays: played safe", "Safety pays: took a needless risk",
            "Safety pays: played safe", "Risk decisions"]
    return SWIPE + table(head, rows, "Share of risk decisions in each cell, with the mean equity lost "
                                     "(and, for setups that give probabilities, the mean confidence)",
                         attrs=f' data-dataset="{dataset}"')


def risk_phase_table(S, rel, dataset, setups) -> str:
    rows = []
    for n in by_error(setups):
        ph = setups[n]["risk"]["phases"]
        cells = ""
        for p in A.PHASES:
            h = ph.get(p)
            if not h:
                cells += f'<td class="num">{nm(TOO_FEW)}</td>'
                continue
            a = nm(TOO_FEW) if h["risk_too_few"] else pct(h["takes_risk"], 0)
            b = nm(TOO_FEW) if h["safety_too_few"] else pct(h["needless_risk"], 0)
            cells += f'<td class="num">{a} / {b}</td>'
        rows.append(tr(S, dataset, n, cells, rel))
    head = ["Model and setting"] + [PHASE_LABEL[p] for p in A.PHASES]
    return SWIPE + table(head, rows, "Per phase: takes the risk when it pays / takes a needless risk",
                         attrs=f' data-dataset="{dataset}"')


def tail_table(S, rel, dataset, setups) -> str:
    rows = []
    for n in by_error(setups):
        q = setups[n]["quality"]
        cbw = (f'<td class="num">{pct(q["confident_badly_wrong"])}</td>' if q.get("confidence_n")
               else f'<td class="num">{nm(NA)}</td>')
        cells = (er_cell(q) + val(q, "p95_loss", eq) + val(q, "worst_mean", eq) + val(q, "blunder_share", pct) + cbw
                 + f'<td class="num">{count(q["scored"])}</td><td class="num">{count(q["invalid"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    head = ["Model and setting", "Error rate (PR), 95% interval", "P95 equity loss", "Mean loss, worst 5%",
            "Blunder rate", "Confident and badly wrong", "Decisions scored", "Invalid answers"]
    return SWIPE + table(head, rows, "League decisions; intervals resample whole games", attrs=f' data-dataset="{dataset}"')


def phase_table(S, rel, dataset, setups, field="phases", labels=None, title="Error rate (PR) per game phase") -> str:
    labels = labels or A.PHASES
    rows = []
    for n in by_error(setups):
        b = setups[n][field]
        cells = "".join(f'<td class="num">{nm(TOO_FEW) if b[str(l)]["too_few"] else fmt(b[str(l)]["error_rate"])}'
                        f'<span class="small">{count(b[str(l)]["n"])}</span></td>' for l in labels)
        rows.append(tr(S, dataset, n, cells, rel))
    head = ["Model and setting"] + [PHASE_LABEL.get(str(l), str(l).capitalize()) for l in labels]
    return SWIPE + table(head, rows, f"{title}; the small number is the decisions in the cell",
                         attrs=f' data-dataset="{dataset}"')


def league_section(S, lg, inner: str, title: str, anchor: str) -> str:
    return (f'<div class="block" id="{anchor}" data-dataset="{lg["dataset"]}"><div class="section-head"><h3>{esc(title)}</h3>'
            f'{league_status_text(lg)}</div>{inner}</div>')


def home(S) -> str:
    rel = ""
    tabs = "".join(f'<button type="button" role="tab" id="tab-{k}" class="mode" aria-controls="board" '
                   f'aria-selected="{str(i == 0).lower()}" data-tab="{k}"><span class="lamp" aria-hidden="true"></span>{l}</button>'
                   for i, (k, l) in enumerate(TABS))
    panels = "".join(f'<div class="tabpanel" id="panel-{k}" data-panel="{k}"{" hidden" if i else ""}>'
                     f'<p class="definition">{esc(DEFINITIONS[k])}</p>{tab_panel(S, k)}</div>'
                     for i, (k, _) in enumerate(TABS))
    L = S["leagues"]
    risk_blocks = "".join(league_section(S, lg, risk_table(S, rel, lg["dataset"], lg["setups"])
                                         + '<details class="more"><summary>By game phase</summary>'
                                         + risk_phase_table(S, rel, lg["dataset"], lg["setups"]) + "</details>",
                                         f"League {lg['id']}", f"risk-league-{lg['id']}") for lg in L)
    risk_v1 = earlier_block(S, risk_table(S, rel, "v1-set", S["v1"]["setups"]), "Earlier version: the v1 set")
    tail_blocks = "".join(league_section(S, lg, tail_table(S, rel, lg["dataset"], lg["setups"]),
                                         f"League {lg['id']}", f"tail-league-{lg['id']}") for lg in L)
    phase_blocks = "".join(league_section(S, lg, phase_table(S, rel, lg["dataset"], lg["setups"]),
                                          f"League {lg['id']}", f"phases-league-{lg['id']}") for lg in L)
    league_list = "".join(
        f'<li><a href="leagues/#league-{lg["id"]}">League {lg["id"]}</a> {league_status_text(lg)} '
        f'{count(lg["matches_done"])} of {count(lg["matches"])} matches, {count(lg["games"])} games, '
        f'{count(lg["scored"])} of {count(lg["decisions"])} decisions engine-scored.</li>' for lg in L)
    th = S["thresholds"]
    reasoning_v1 = table(REASON_HEAD, reasoning_rows(S, S["v1"]["reasoning"]),
                         "Earlier version: v1 set, paired on the same positions", attrs=' data-version="v1"')
    return f"""
    <header class="hero">
      <h1>{TITLE}</h1>
      <p class="intro">{SUBTITLE}</p>
      <div class="readout-row">
        <ul class="readouts">{readouts(S)}</ul>
        <p class="version">{esc(version_line(S))}</p>
      </div>
      <div class="summary" id="findings">
        <p class="summary-lead findings-wait">Findings will be written when the current leagues finish.</p>
        <p class="summary-lead">They will answer four questions:</p>
        <ul class="summary-list">
          <li><a href="?tab=quality#board" data-goto-tab="quality">Which setup has the lowest move error?</a></li>
          <li><a href="#risk-worth">Can models tell when a risk is worth taking?</a></li>
          <li><a href="?tab=reasoning#board" data-goto-tab="reasoning">Where does high reasoning help?</a></li>
          <li><a href="?tab=cost#board" data-goto-tab="cost">Which cheaper setup keeps the quality?</a></li>
        </ul>
      </div>
    </header>
    {filters(S)}
    <section class="panel board-panel" id="board-panel" aria-labelledby="board-title">
      <h2 id="board-title" class="visually-hidden">Main table: shared positions</h2>
      <div class="modebar">
        <div class="keys view-switch needs-js" role="group" aria-label="Show the results as"><button type="button" class="key" data-view="table" aria-pressed="true"><span class="lamp" aria-hidden="true"></span>Table</button><button type="button" class="key" data-view="charts" aria-pressed="false"><span class="lamp" aria-hidden="true"></span>Charts</button></div>
        <div class="modes" role="tablist" aria-label="Main table">{tabs}</div>
        <span class="in-view">{status_badge(PENDING)}</span>
        <a class="charts-link" href="#charts">Charts</a>
      </div>
      <div id="board" role="tabpanel">{panels}</div>
      {charts(S)}
    </section>

    <section class="card" id="risk-worth">
      <div class="section-head"><h2>Is the risk worth it?</h2>{status_badge(PENDING)} <span class="small inline">shared positions</span></div>
      <p>The main research question: can a model tell when a risk is worth taking? For each decision we find the
      safest play, the legal play that leaves the opponent the fewest hitting rolls, as shown to the model. In
      <strong>Risk pays</strong> decisions, the engine's best play leaves more hitting rolls than the safest play. In
      <strong>Safety pays</strong> decisions, a safest play is the engine's best play or loses less than
      {th['safety_pays_loss_below']} equity. Decisions where every play leaves the same number of hitting rolls offer
      no such choice and are left out. This measures one kind of risk, being hit; gammon risk and priming are not in it.</p>
      <p>The shared-position version waits for the answers. Below: league decisions, each league on its own, and the earlier v1 set.</p>
      {risk_blocks}
      {risk_v1}
    </section>

    <section class="card" id="reasoning">
      <div class="section-head"><h2>Reasoning: does a higher setting help?</h2>{status_badge(PENDING)} <span class="small inline">shared positions</span></div>
      <p>The same model at low and high, or off and on, compared on the same positions: the paired error
      difference, the gain per game phase, the extra time and cost, and a verdict (High helps · No clear benefit ·
      High hurts · Depends on the position). Worse moves and more time or cost with no shown gain are reported
      apart. League games give each setting different positions, so the leagues cannot answer this; it waits for the
      shared-position answers.</p>
      {earlier_block(S, SWIPE + reasoning_v1, "Earlier version: the v1 set")}
    </section>

    <section class="card" id="risk-confidence">
      <div class="section-head"><h2>Risk and confidence</h2>{status_badge(PENDING)} <span class="small inline">shared positions</span></div>
      <p>Tail risk: the 95th percentile of the equity lost per decision, the mean loss of the worst
      {pct(th['worst_share'], 0)} of decisions and the blunder rate (a loss over {th['blunder_loss_above']}).
      "Confident and badly wrong": the share of decisions where the model gave its play a probability of at least
      {th['very_confident_probability_at_least']} and lost more than {th['badly_wrong_loss_above']} equity; N/A for
      setups that return only a choice. League decisions, each league on its own:</p>
      {tail_blocks}
    </section>

    <section class="card" id="phases">
      <div class="section-head"><h2>Game phases</h2>{status_badge(PENDING)} <span class="small inline">shared positions</span></div>
      <p>Opening, contact, holding game, race and bear-off. A cell with fewer than {th['min_decisions_per_cell']}
      decisions shows "{TOO_FEW}". Strategy tags, number of options and the gap between the two best plays:
      <a href="phases/">Phases</a>. League decisions, each league on its own:</p>
      {phase_blocks}
    </section>

    <section class="card" id="routing">
      <div class="section-head"><h2>Routing and teams</h2>{status_badge(PENDING)}</div>
      <p>Which decisions can a cheap model handle, and when should it hand over to a strong one? Can a team pick
      better plays than its best member? Both wait for the shared-position answers. The team "oracle", the best
      answer any member gave, is an upper bound and never a working system. The earlier version's team results are
      on the <a href="leagues/#earlier">Leagues page</a>.</p>
    </section>

    <section class="card" id="learning">
      <div class="section-head"><h2>Learning from experience</h2>{status_badge(NOT_MEASURED)}</div>
      <p>Every decision is a separate request; models are not told how earlier games went.</p>
    </section>

    <section class="card" id="leagues">
      <div class="section-head"><h2>Leagues</h2></div>
      <p>Round-robin leagues, kept apart from the quality ranking: each league's table compares only the players in
      it, and no league numbers are merged into one overall score.</p>
      <ul>{league_list}</ul>
    </section>

    <section class="card" id="more">
      <h2>Method and data</h2>
      <p><a href="method/">Method</a>: setup, prompt, error rate, human scale, statistics, fixed thresholds, limits.
      <a href="data/">Data</a>: downloads, versions and how to recompute.</p>
    </section>"""


# --- Leagues ------------------------------------------------------------------------------------------------

def standings(S, lg, rel) -> str:
    rows = []
    for t in lg["standings"]:
        cells = (f'<td class="num">{t["played"]}</td><td class="num">{t["won"]}-{t["drawn"]}-{t["lost"]}</td>'
                 f'<td class="num">{t["points"]}</td><td class="num">{t["games_won"]}-{t["games_lost"]}</td>'
                 f'<td class="num">{t["gammons_won"]}</td><td class="num">{t["to_play"]}</td>')
        rows.append(f"<tr{row_attrs(S, lg['dataset'], t['name'])}><td class=num>{t['place']}</td>"
                    f"{model_cell(S, rel, lg['dataset'], t['name'])}{cells}</tr>")
    head = ["Place", "Model and setting", "Played", "Won-drawn-lost", "Points", "Games won-lost", "Gammons won", "To play"]
    th = "".join(f'<th scope="col"{" class=num" if i != 1 else ""}>{h}</th>' for i, h in enumerate(head))
    return (SWIPE + f'<div class="table-wrap"><table class="board" data-dataset="{lg["dataset"]}"><caption>Standings: '
            f'3 points a win, 1 a draw; only finished league-stage matches count</caption><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def leagues_page(S, archive_v1: str, archive_notes: str) -> str:
    rel = "../"
    blocks = []
    for lg in S["leagues"]:
        q = (SWIPE + table(QUALITY_HEAD, quality_rows(S, rel, lg["dataset"], lg["setups"]),
                           "Decision quality in this league's games; intervals resample whole games",
                           attrs=f' data-dataset="{lg["dataset"]}"')
             + '<p class="table-note">\u2020 Setups got different inputs: when a position had more legal plays than a '
               'setup takes in one request, its plays were split into groups and the group winners compared. The '
               'rows marked \u2020 had such decisions; the others saw every play at once. Every setup got the same '
               'long rules text.</p>')
        c = (SWIPE + table(COST_HEAD, cost_rows(S, rel, lg["dataset"], lg["setups"]), "Time and cost in this league",
                           attrs=f' data-dataset="{lg["dataset"]}"'))
        dates = f'started {lg["started"][:10]}' + (f', finished {lg["finished"][:10]}' if lg["finished"] else "")
        blocks.append(f'<section class="card" id="league-{lg["id"]}" data-dataset="{lg["dataset"]}"><div class="section-head">'
                      f'<h2>League {lg["id"]}</h2>{league_status_text(lg)}</div>'
                      f'<p>{count(lg["matches_done"])} of {count(lg["matches"])} matches finished, {count(lg["games"])} games; '
                      f'{esc(dates)}. {count(lg["scored"])} of {count(lg["decisions"])} decisions engine-scored so far.</p>'
                      f'{standings(S, lg, rel)}<h3 id="league-{lg["id"]}-quality">Decision quality</h3>{q}'
                      f'<h3 id="league-{lg["id"]}-cost">Time and cost</h3>{c}</section>')
    return (page_head(S, "Leagues", "Leagues", "One table per league. League tables compare only the players inside "
                      "one league; they are never merged into one overall score. A running league's numbers are "
                      "Provisional and change as matches finish.")
            + "".join(blocks)
            + f'<section class="card" id="notes"><h2>Notes kept from the earlier page</h2>{archive_notes}</section>'
            + f'<section class="card" id="earlier"><div class="section-head"><h2>Earlier version: v1 leagues and teams</h2>'
              f'{status_badge(EARLIER)}</div><p class="note">{esc(play_order_note(S))}</p>{archive_v1}</section>')


# --- Phases -------------------------------------------------------------------------------------------------

def phases_page(S) -> str:
    rel = "../"
    out = [page_head(S, "Phases", "Where do models fail?",
                     "Error rate by game phase, strategy tag, number of legal plays and the equity gap between the two "
                     "best plays. Each league on its own; the shared-position version waits for the answers.")]
    out.append(f'<section class="card" id="shared"><div class="section-head"><h2>Shared positions</h2>{status_badge(PENDING)}</div>'
               f'<p>Waits for the shared-position answers.</p></section>')
    sets = [(lg["dataset"], f"League {lg['id']}", lg["setups"], lg) for lg in S["leagues"]]
    sets.append(("v1-set", "Earlier version: the v1 set", S["v1"]["setups"], None))
    for ds, title, setups, lg in sets:
        badge = league_status_text(lg) if lg else status_badge(EARLIER)
        body = (f'<h3 id="{ds}-phase">Game phase</h3>' + phase_table(S, rel, ds, setups)
                + f'<h3 id="{ds}-tag">Strategy tag (contact and holding positions after the opening)</h3>'
                + phase_table(S, rel, ds, setups, "tags", A.TAGS, "Error rate (PR) per strategy tag")
                + f'<h3 id="{ds}-options">Number of legal plays</h3>'
                + phase_table(S, rel, ds, setups, "options", A.OPTION_LABELS, "Error rate (PR) by number of legal plays")
                + f'<h3 id="{ds}-gap">Equity gap between the two best plays</h3>'
                + phase_table(S, rel, ds, setups, "gaps", A.GAP_LABELS, "Error rate (PR) by the gap between the two best plays"))
        note = f'<p class="note">{esc(play_order_note(S))}</p>' if not lg else ""
        out.append(f'<section class="card" id="{ds}" data-dataset="{ds}"><div class="section-head"><h2>{esc(title)}</h2>'
                   f'{badge}</div>{note}{body}</section>')
    return "".join(out)


# --- Models -------------------------------------------------------------------------------------------------

B7 = [("model_id", "Model ID"), ("provider", "Provider or endpoint"), ("date_run", "Date run"), ("price", "Price"),
      ("model_type", "Model type"), ("weights", "Weights"), ("runs_on", "Runs on"), ("reasoning", "Reasoning setting"),
      ("confidence_source", "Confidence source"), ("rules_text", "Rules text"), ("option_groups", "Option groups"),
      ("sampling", "Sampling settings"), ("notes", "Notes")]


def facts(m: dict, q: dict | None) -> str:
    out = []
    for k, label in B7:
        v = m.get(k)
        if k == "price" and v:
            tokens = (f"${v['input_per_mtok']} / ${v['output_per_mtok']} per million tokens in / out"
                      if v.get("input_per_mtok") is not None else "no price per token")
            v = f"{tokens}; {v['label']}; price date {v.get('date') or 'not recorded'}"
        if k == "date_run" and not v and q and q.get("first_date"):
            v = q["first_date"] if q["first_date"] == q["last_date"] else f"{q['first_date']} to {q['last_date']}"
        if k == "option_groups" and q is not None:
            seen = (f"; in this data {count(q['grouped'])} decisions were split into groups of "
                    f"{', '.join(str(g) for g in q['group_sizes'])}" if q.get("grouped") else "; no decision in this data was split")
            v = (v or "not recorded") + seen
        out.append(f"<dt>{label}</dt><dd>{esc(v) if v else nm('Missing')}</dd>")
    return f'<dl class="facts">{"".join(out)}</dl>'


def model_page(S, dataset: str, name: str, entry: dict | None, smoke_row: dict | None) -> str:
    m = meta(S, dataset, name)
    rel = "../../../"
    q = entry["quality"] if entry else None
    if dataset.startswith("league-"):
        lg = next(l for l in S["leagues"] if l["dataset"] == dataset)
        badge, where = league_status_text(lg), f'League {lg["id"]}'
    elif dataset == "v1-set":
        lg, badge, where = None, status_badge(EARLIER), "v1 set (earlier version)"
    else:
        lg, badge, where = None, status_badge("Smoke test"), "New models: first look (50 smoke positions)"
    parts = [f'<section class="card"><p class="eyebrow">{esc(m.get("model_type") or "Setup")} · {esc(where)}</p>'
             f'<h1>{esc(name)}</h1><p class="subtitle">{badge}</p><p class="version">{esc(version_line(S))}</p></section>',
             f'<section class="card" id="setup"><h2>How we called it</h2>{facts(m, q)}'
             f'{"<p class=note>Missing B7 fields: " + esc(", ".join(m["missing"])) + "</p>" if m.get("missing") else ""}</section>']
    if entry:
        cells = (f"<dt>Error rate (PR)</dt><dd>{er_cell(q)[16:-5]}</dd>"
                 f"<dt>Decisions</dt><dd>{count(q['decisions'])} ({count(q['scored'])} scored, {count(q['invalid'])} invalid)</dd>")
        if q.get("error_rate") is not None and not q.get("too_few"):
            cells += (f"<dt>Engine's best play</dt><dd>{pct(q['best_share'])}</dd><dt>Blunder rate</dt><dd>{pct(q['blunder_share'])}</dd>"
                      f"<dt>P95 equity loss</dt><dd>{eq(q['p95_loss'])}</dd><dt>Mean loss, worst 5%</dt><dd>{eq(q['worst_mean'])}</dd>")
        cells += (f"<dt>Median / P90 s per decision</dt><dd>{secs(q.get('time_median'))} / {secs(q.get('time_p90'))}</dd>"
                  f"<dt>$ per 1,000 decisions</dt><dd>{cost_cell(S, dataset, name, q)[16:-5]}</dd>")
        r = entry["risk"]
        if r["decisions"]:
            cells += (f"<dt>Takes the risk when it pays</dt><dd>{nm(TOO_FEW) if r['risk_too_few'] else pct(r['takes_risk'])}</dd>"
                      f"<dt>Takes a needless risk</dt><dd>{nm(TOO_FEW) if r['safety_too_few'] else pct(r['needless_risk'])}</dd>")
        note = f'<p class="note">{esc(play_order_note(S))}</p>' if dataset == "v1-set" else ""
        parts.append(f'<section class="card" id="results"><h2>Results in {esc(where)}</h2>{note}<dl class="facts">{cells}</dl>'
                     f'<p><a href="{rel}decisions/?d={dataset}&amp;s={m["slug"] if dataset != "v1-set" else slug(name)}">Every decision of this setup</a> · '
                     f'<a href="{rel}data/{"v1/v1-set" if dataset == "v1-set" else "v3/" + dataset}/{slug(name)}.json">JSON</a></p></section>')
        b = entry["phases"]
        rows = "".join(f'<tr><th scope="row">{PHASE_LABEL[p]}</th><td class="num">{nm(TOO_FEW) if b[p]["too_few"] else fmt(b[p]["error_rate"])}</td>'
                       f'<td class="num">{count(b[p]["n"])}</td></tr>' for p in A.PHASES)
        parts.append(f'<section class="card" id="phases"><h2>By game phase</h2><div class="table-wrap"><table class="board list">'
                     f'<thead><tr><th scope="col">Phase</th><th scope="col" class="num">Error rate (PR)</th><th scope="col" class="num">Decisions</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></div></section>')
    if smoke_row:
        parts.append(f'<section class="card" id="smoke"><h2>Smoke test</h2>{smoke_facts(smoke_row)}</section>')
    return "".join(parts)


def smoke_facts(r: dict) -> str:
    ci = r.get("error_ci") or [None, None]
    rows = [("Positions answered", f"{r['answered']} of {r['asked']} ({r['failed']} failed, {r['timed_out']} timed out)"),
            ("Invalid answers", f"{r['invalid']}"),
            ("Error rate (PR)", f"{fmt(r['error_rate'])} (95% interval {fmt(ci[0])} to {fmt(ci[1])})" if r.get("error_rate") is not None else None),
            ("Median / P90 request s", f"{fmt(r['request_s_p50'], 1)} / {fmt(r['request_s_p90'], 1)}" if r.get("request_s_p50") is not None else None),
            ("$ per 1,000 decisions", fmt(r["usd_per_1000"], 2) if r.get("usd_per_1000") is not None else None)]
    return '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{esc(v) if v is not None else nm(NOT_MEASURED)}</dd>" for k, v in rows) + "</dl>"


def models_index(S) -> str:
    groups = []
    for lg in S["leagues"]:
        items = "".join(f'<li><a href="{lg["dataset"]}/{meta(S, lg["dataset"], n)["slug"]}/">{esc(n)}</a></li>' for n in lg["setups"])
        groups.append(f'<section class="card" id="{lg["dataset"]}"><div class="section-head"><h2>League {lg["id"]}</h2>'
                      f'{league_status_text(lg)}</div><ul>{items}</ul></section>')
    items = "".join(f'<li><a href="v1-set/{meta(S, "v1-set", n)["slug"]}/">{esc(n)}</a></li>' for n in S["v1"]["setups"])
    groups.append(f'<section class="card" id="v1-set"><div class="section-head"><h2>v1 set</h2>{status_badge(EARLIER)}</div><ul>{items}</ul></section>')
    items = "".join(f'<li><a href="smoke-part-a/{meta(S, "smoke-part-a", r["setup"])["slug"]}/">{esc(r["setup"])}</a></li>'
                    for r in sorted(S["smoke"], key=lambda r: r["setup"]))
    groups.append(f'<section class="card" id="smoke-part-a"><h2>New models: first look (smoke tests)</h2><ul>{items}</ul></section>')
    return page_head(S, "Models", "Model setups", "One page per setup, with how it was called. Setups are not "
                     "identical: they differ in model type, where they run, reasoning setting, confidence source and "
                     "option groups.") + "".join(groups)


# --- Compare, disagreements, new models, data ------------------------------------------------------------------

def compare_page(S) -> str:
    names = S["v1"]["setups"]
    opts = "".join(f'<option value="{esc(n)}">{esc(n)}</option>' for n in names)
    return (page_head(S, "Compare", "Compare two setups", "Two models, or one model at two reasoning settings, side "
                      "by side, paired on the same positions.")
            + f'<section class="card" id="shared"><div class="section-head"><h2>Shared positions</h2>{status_badge(PENDING)}</div>'
              f'<p>Waits for the shared-position answers. League games give each setup different positions, so league '
              f'setups cannot be paired; see each league\'s own tables on the <a href="../leagues/">Leagues page</a>.</p></section>'
            + f'<section class="card" id="v1" data-version="v1"><div class="section-head"><h2>Earlier version: the v1 set</h2>{status_badge(EARLIER)}</div>'
              f'<p class="note">{esc(play_order_note(S))}</p>'
              f'<div class="compare-pick needs-js"><label>First <select data-compare="a">{opts}</select></label>'
              f'<label>Second <select data-compare="b">{opts}</select></label></div>'
              f'<div data-compare-out aria-live="polite"></div>'
              f'<noscript><p>The comparison needs JavaScript; the numbers are in <a href="../data/v1/compare.json">compare.json</a>.</p></noscript>'
              f'</section>')


def disagreements_page(S) -> str:
    d = S["v1"]["disagreements"]
    dist = "".join(f'<tr><td class="num">{k}</td><td class="num">{count(v)}</td></tr>' for k, v in d["distribution"].items())
    rows = []
    for r in d["rows"][:150]:
        first = slug(next(iter(S["v1"]["setups"])))
        rows.append(f'<tr data-dataset="v1-set"><td><a href="../decisions/?d=v1-set&amp;s={first}&amp;p={(r["pid"] - 1) // 50 + 1}#d{esc(r["id"])}">{esc(r["id"])}</a></td>'
                    f'<td>{esc(PHASE_LABEL.get(r["phase"], r["phase"]))}</td><td class="num">{r["plays"]}</td>'
                    f'<td class="num">{r["distinct"]}</td><td class="num">{pct(r["best_share"], 0)}</td>'
                    f'<td>{esc(r["common"])}<span class="small">{pct(r["common_share"], 0)} of setups, loses {eq(r["common_loss"])}</span></td>'
                    f'<td>{esc(r["best"])}</td></tr>')
    head = ["Position", "Phase", "Legal plays", "Different plays chosen", "Setups choosing the engine's best",
            "Most common play", "Engine's best play"]
    return (page_head(S, "Where models disagree", "Where do models disagree?", "Positions where setups pick different plays.")
            + f'<section class="card" id="shared"><div class="section-head"><h2>Shared positions</h2>{status_badge(PENDING)}</div>'
              f'<p>Waits for the shared-position answers.</p></section>'
            + f'<section class="card" id="v1" data-version="v1"><div class="section-head"><h2>Earlier version: the v1 set</h2>{status_badge(EARLIER)}</div>'
              f'<p class="note">{esc(play_order_note(S))}</p>'
              f'<p>{count(d["positions"])} positions, {count(len(S["v1"]["setups"]))} setups. All setups chose the same play in '
              f'{count(d["all_agree"])} positions.</p>'
              + table(["Different plays chosen", "Positions"], [dist], "How many different plays the setups chose", cls="board list")
              + SWIPE + table(head, rows, "The 150 positions with the most different plays (then the fewest engine-best choices)",
                              attrs=' data-version="v1"') + "</section>")


def new_models_page(S) -> str:
    rows = []
    for r in sorted(S["smoke"], key=lambda r: r["setup"].lower()):
        m = meta(S, "smoke-part-a", r["setup"])
        ci = r.get("error_ci") or [None, None]
        pairs = "".join(f'<span class="small">vs {esc(p["reference"])}: {fmt(p["diff"], 1, True)} ({fmt(p["ci"][0], 1, True)} to {fmt(p["ci"][1], 1, True)}), n = {p["positions"]}</span>'
                        for p in r.get("paired", []) if p["reference"] != r["setup"])
        price = m.get("price") or {}
        rows.append(
            f'<tr data-dataset="smoke-part-a"><td class="model"><a class="model-name" href="../models/smoke-part-a/{m["slug"]}/">{esc(r["setup"])}</a>'
            f'<span class="small">{esc(m.get("provider") or "")}</span></td>'
            f'<td>{esc(r["probabilities"])}</td><td>{esc(m.get("reasoning") or "")}</td>'
            f'<td class="num">{fmt(r["request_s_p50"], 1)} / {fmt(r["request_s_p90"], 1)}</td>'
            f'<td class="num">{fmt(r["usd_per_1000"], 2) if r.get("usd_per_1000") is not None else nm(NOT_MEASURED)}'
            f'<span class="small">{esc(price.get("label", ""))}</span></td>'
            f'<td class="num">{pct(r["invalid"] / r["asked"], 0)}<span class="small">{r["failed"]} failed, {r["timed_out"]} timed out</span></td>'
            f'<td class="num">{fmt(r["error_rate"])}<span class="small">{fmt(ci[0])} to {fmt(ci[1])}</span></td>'
            f'<td class="num">{pairs}</td></tr>')
    head = ["Setup", "Probabilities", "Reasoning setting", "Median / P90 request s", "$ per 1,000 decisions",
            "Invalid share", "Error rate (PR), 95% interval", "Paired difference from the reference setups"]
    return (page_head(S, "New models: first look", "New models: first look")
            + '<section class="card" id="smoke"><p><strong>50 positions each, outside the shared sets. Error rates are rough '
              '(about \u00b110 to \u00b125): enough to spot a clearly weak model, not to rank models.</strong> This page feeds no '
              'ranking, chart or finding. Sorted by name.</p>' + SWIPE
            + table(head, rows, "Smoke tests: the same 50 positions for every setup, with the v3 prompt and shuffled plays")
            + '<p class="note">Setups that wait for a free GPU (d3-turbo, Nemotron 3.5 Bolt) join this table when they have run.</p></section>')


def status_list(S) -> str:
    rows = []
    for a in S["status"]["analyses"]:
        for p in a["parts"]:
            st = p["status"]
            if st.startswith("Published (Leagues"):
                st = " · ".join(f"League {lg['id']}: {lg['metric_status']}" for lg in S["leagues"])
            rows.append(f'<tr><td>{esc(a["id"])}</td><td>{esc(a["name"])}<span class="small">{esc(p["scope"])}</span></td>'
                        f'<td>{esc(st)}</td><td><code>{esc(p["data"])}</code></td><td>{"yes" if p["waits_for_leagues"] else "no"}</td></tr>')
    return SWIPE + table(["Analysis", "What", "Status", "Data file", "Waits for the running leagues"], rows,
                         "Every analysis in the plan, with its status and data file", cls="board list")


def data_page(S, out: Path) -> str:
    man = json.loads((out / "data/manifest.json").read_text())
    rows = "".join(f'<tr><td><a href="../{esc(f["path"])}">{esc(f["path"])}</a></td><td class="num">{count(f["bytes"])}</td>'
                   f'<td><code>{f["sha256"][:12]}</code></td></tr>' for f in man["files"])
    return (page_head(S, "Data", "Data, versions and how to recompute")
            + f'<section class="card" id="downloads"><h2>Downloads</h2><p>Data files are split per version, league and model, '
              f'so each loads on a phone. Every number on the site is in one of them. The decision files behind '
              f'<a href="../decisions/">Every decision</a> are under <code>decisions/</code> ({count(S["decision_files"])} files, gzip-compressed JSON).</p>'
              + SWIPE + table(["File", "Bytes", "sha256"], [rows], "Data files of this build", cls="board list") + "</section>"
            + '<section class="card" id="versions"><h2>Versions</h2><dl class="facts">'
              '<dt>v3</dt><dd>Prompt bg-v2, plays in a seeded random order, invalid answers not retried. Leagues 1 to 3 and the shared positions.</dd>'
              f'<dt>v1</dt><dd>{status_badge(EARLIER)} Earlier prompt; plays listed in the runner\'s order. The v1 set of 1,000 positions answered by the v1 setups. Never in a v3 table or chart.</dd>'
              '<dt>Smoke tests</dt><dd>50 positions outside the shared sets, v3 prompt; only on New models: first look.</dd></dl></section>'
            + '<section class="card" id="recompute"><h2>How to recompute</h2><ol>'
              '<li>Snapshot the league database: <code>python3 tools/site/snapshot.py v3.db STATE</code> (one read transaction; the prompts each model was sent go to <code>STATE/prompts.db</code>).</li>'
              '<li>Score every legal play of every decision with GNUbg 1.08 at 2-ply: <code>tools/site/score.sh STATE/snap.db STATE/plays</code>.</li>'
              '<li>Build and check the site: <code>python3 tools/site/build.py --state STATE --out OUT</code>. The build fails, and nothing is deployed, if a number does not trace to a data file, counts do not add up, or leagues or versions mix.</li>'
              '</ol><p>The scripts are in the jevgammon repository under <code>tools/site/</code>; the fixed thresholds are in <a href="thresholds.json">thresholds.json</a>.</p></section>'
            + f'<section class="card" id="status"><h2>Analysis status</h2>{status_list(S)}</section>')


def decisions_page(S, body: str) -> str:
    return body + f'<p class="version version-line">{esc(version_line(S))}</p>'


def share_card(S) -> str:
    """The link preview card (1200 x 630), drawn from the current results."""
    leagues = "".join(f'<li><b>League {lg["id"]}</b> {esc(lg["status"])} · {count(lg["scored"])} decisions scored</li>'
                      for lg in S["leagues"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;width:1200px;height:630px;background:#0e0e0d;color:#ebe9e4;font-family:system-ui,sans-serif;display:flex;flex-direction:column;justify-content:center;padding:0 80px;box-sizing:border-box}}
h1{{font-size:64px;margin:0 0 20px;line-height:1.05}} p{{font-size:28px;color:#b8b5ad;margin:0 0 28px}} ul{{list-style:none;padding:0;margin:0;font-size:28px}} li{{margin:8px 0}} b{{color:#ff5b4f}}
.f{{position:absolute;bottom:40px;left:80px;font-size:22px;color:#8a877f}}</style></head><body>
<h1>{TITLE}</h1><p>{SUBTITLE}</p><ul>{leagues}<li><b>Shared positions</b> {count(S["shared"]["standard"])} · analysis pending</li></ul>
<div class="f">Zeki Works · backgammon benchmark · engine-scored decisions, GNUbg 2-ply</div></body></html>"""


def description(S) -> str:
    scored = sum(lg["scored"] for lg in S["leagues"])
    st = "; ".join(f"League {lg['id']} {lg['status'].lower()}" for lg in S["leagues"])
    return (f"{SUBTITLE} {count(scored)} league decisions scored by GNUbg so far ({st}). "
            f"Shared-position results: analysis pending.")


# --- Write ----------------------------------------------------------------------------------------------------

def write_all(S, out: Path, base: str) -> None:
    import decisions_export
    import method
    S["description"] = description(S)

    def put(path: str, title: str, body: str, **kw):
        target = out / path / "index.html" if path else out / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(layout(S, base, path, title, body, **kw))

    for stale in ("models",):
        import shutil
        if (out / stale).exists():
            shutil.rmtree(out / stale)
    put("", TITLE, home(S), scripts=("bg.js",), body_class="home")
    put("leagues/", "Leagues", leagues_page(S, method.archive_v1(), method.archive_v3_notes()), scripts=("bg.js",))
    put("phases/", "Phases", phases_page(S), scripts=("bg.js",))
    put("compare/", "Compare", compare_page(S), scripts=("bg.js",))
    put("disagreements/", "Where models disagree", disagreements_page(S), scripts=("bg.js",))
    put("new-models/", "New models: first look", new_models_page(S), scripts=("bg.js",))
    put("models/", "Models", models_index(S))
    for lg in S["leagues"]:
        for n, e in lg["setups"].items():
            put(f"models/{lg['dataset']}/{meta(S, lg['dataset'], n)['slug']}/", n, model_page(S, lg["dataset"], n, e, None))
    for n, e in S["v1"]["setups"].items():
        put(f"models/v1-set/{meta(S, 'v1-set', n)['slug']}/", f"{n} (v1)", model_page(S, "v1-set", n, e, None))
    for r in S["smoke"]:
        put(f"models/smoke-part-a/{meta(S, 'smoke-part-a', r['setup'])['slug']}/", r["setup"],
            model_page(S, "smoke-part-a", r["setup"], None, r))
    ctx = dict(thresholds=S["thresholds"], play_order=S["v1"]["play_order"], shared_sets=S["shared"]["build_log"],
               data_as_of=as_of(S))
    put("method/", "Method", method.body(ctx), main_class="method-page")
    put("data/", "Data", data_page(S, out))
    put("decisions/", "Every decision", decisions_page(S, decisions_export.body()),
        scripts=("decisions.js",), styles=("decisions.css",))
