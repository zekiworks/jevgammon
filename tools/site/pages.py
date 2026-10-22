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
TABS = [("quality", "Quality"), ("risk", "Risk"), ("confidence", "Confidence"), ("reasoning", "Reasoning"),
        ("cost", "Cost"), ("stability", "Stability")]
TITLE = "Can a model tell when a risk is worth taking?"


def subtitle(S) -> str:
    return (f"We score every backgammon decision with an engine and compare decision quality, what the input adds, "
            f"confidence and cost across {count(S['counts']['model_setups'])} model setups.")


INTRO = ("Language models and decision models play backgammon leagues, and GNU Backgammon scores every legal play of "
         "every decision, so a move is judged by the equity it gives away, not by who won the game. The hardest "
         "choices trade safety against gain: leaving a blot can be the best play or a needless risk. "
         "Every decision is public.")
# B0: the five threads; every home section and tab belongs to one of them.
THREADS = {1: "Decision quality under risk", 2: "What the input adds", 3: "Confidence", 4: "Cost",
           5: "Learning from experience"}
TAB_THREAD = {"quality": 1, "risk": 1, "confidence": 3, "reasoning": 4, "cost": 4, "stability": 1}
RISK_LIMIT = "Hit risk only: being hit. Gammon risk and priming are not in it."
SWIPE = '<p class="swipe-hint" data-swipe-hint>Swipe for more columns \u2192</p>'
LEAGUE_KIND = {1: "decision models and models on our own hardware", 2: "workhorse chat models, closed and open",
               3: "frontier chat models on subscriptions"}
PHASE_LABEL = {"opening": "Opening", "contact": "Contact", "holding": "Holding game", "race": "Race",
               "bear-off": "Bear-off"}


# --- Formatting ---------------------------------------------------------------------------------------

def as_of(S) -> str:
    from datetime import datetime
    t = datetime.strptime(S["as_of"], "%Y-%m-%dT%H:%MZ")
    return t.strftime("%-d %B %Y, %H:%M UTC")


def version_line(S) -> str:
    return f"Results {S['hash']}, updated {as_of(S)}."


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
    bits = [x for x in (m.get("setting") and f"{m['setting']}", m.get("model_type"), m.get("runs_on"),
                        m.get("play_order") and "shuffled play order") if x]
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


def about(inner: str, label: str = "About this table") -> str:
    """Explanatory prose, collapsed: the tables lead and the text is one click away."""
    return f'<details class="about"><summary>{esc(label)}</summary>{inner}</details>'


def earlier_block(S, inner: str, title: str) -> str:
    return (f'<div class="block" data-version="v1"><div class="section-head"><h3>{esc(title)}</h3>'
            f'{status_badge(EARLIER)}</div>{inner}<p class="table-note">{esc(play_order_note(S))} v1 used an '
            f'earlier prompt; these numbers never share a table or chart with v3 numbers.</p></div>')


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


def share_cell(share, n, den, digits=1) -> str:
    """A share is always shown with its count and denominator (B9)."""
    if not den:
        return f'<td class="num">{nm(NA)}<span class="small">0 / 0</span></td>'
    return f'<td class="num">{pct(share, digits)}<span class="small">{count(n)} / {count(den)}</span></td>'


def risk_rows(S, rel, dataset, setups) -> list[str]:
    rows = []
    for n in by_error(setups):
        r, q = setups[n]["risk"], setups[n]["quality"]
        cells = (share_cell(r["takes_risk"], r["took_when_pays"], r["risk_pays"])
                 + share_cell(r["needless_risk"], r["took_needless"], r["safety_pays"])
                 + val(q, "p95_loss", eq) + val(q, "worst_mean", eq) + val(q, "blunder_share", pct)
                 + f'<td class="num">{count(r["no_risk_choice"])}</td>'
                 + f'<td class="num">{count(q["invalid"])}</td>')
        rows.append(tr(S, dataset, n, cells, rel))
    return rows


RISK_HEAD = ["Model and setting", "Risk pays: took a risk", "Safety pays: took a needless risk", "P95 equity loss",
             "Mean loss, worst 5%", "Blunder rate", "No hit-risk trade-off (left out)", "Invalid answers"]


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
    js = "".join(f'<script src="{rel}{s}" defer></script>' for s in ("site.js", "tables.js") + tuple(scripts))
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
  <meta name="color-scheme" content="dark light">
  <script>document.documentElement.classList.add("js"); try {{ var t = localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); if (t === "light") document.documentElement.dataset.theme = "light"; }} catch (e) {{}}</script>
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
    <p>Download: <a href="{rel}data/results.json">results (JSON)</a> · <a href="{rel}decisions/index.json">decisions (JSON index)</a> · <a href="{rel}data/">every data file</a> · <a href="{rel}data/manifest.json">manifest.json</a></p>
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
    return (f'<p id="shared-positions">The shared positions: {count(sh["standard"])} standard positions '
            f'({count(p["v1"]["positions"])} from the earlier v1 league games and {count(p["new"]["positions"])} from GNUbg '
            f'self-play at expert level, {count(p["new"]["positions"] // 5)} per game phase), plus '
            f'{count(p["nackgammon"]["positions"])} Nackgammon positions and a {count(p["opening-control"]["positions"])}-position '
            f'opening control. Every standard position has {sh["min_plays"]} to {sh["max_plays"]} legal plays, so no '
            f'play list is split into groups. Every setup answers the same positions; this set, not the league tables, '
            f'compares setups across leagues. <a href="method/#shared-positions">How they were drawn</a>.</p>')


def readouts(S) -> str:
    c = S["counts"]
    items = [(count(c["decisions_scored"]), "decisions scored"), (count(c["leagues"]), "leagues"),
             (count(c["model_setups"]), "setups"), (count(c["models"]), "models")]
    return "".join(f'<li class="readout"><span class="readout-value">{v}</span> <span class="readout-label">{l}</span></li>'
                   for v, l in items)


def default_league(S) -> str:
    """The league the leaderboard opens on: the most recent finished league, else the most recent one."""
    done = [lg for lg in S["leagues"] if lg["metric_status"] == PUBLISHED]
    return max(done or S["leagues"], key=lambda lg: lg["id"])["dataset"]


def league_views(S) -> list[tuple[str, str]]:
    """The leaderboard's league selector: one league at a time, never merged (B4); the shared positions show their
    status until answered; the v1 set is the earlier version."""
    return ([(lg["dataset"], f"League {lg['id']}") for lg in S["leagues"]]
            + [("shared", "Shared positions"), ("v1-set", "Earlier version: v1 set")])


def league_picker(S, label="League") -> str:
    cur = default_league(S)
    keys = "".join(f'<button type="button" class="key" data-league-pick="{k}" aria-pressed="{str(k == cur).lower()}">'
                   f'<span class="lamp" aria-hidden="true"></span>{esc(l)}</button>' for k, l in league_views(S))
    return (f'<div class="group league-pick" role="group" aria-label="{esc(label)}"><span class="group-label">{esc(label)}</span>'
            f'<span class="keys">{keys}</span></div>')


def view_block(S, key: str, inner: str) -> str:
    """One league's (or the shared set's, or v1's) part of a section; the league selector shows one at a time.
    Without JavaScript every block shows, each under its own heading."""
    return f'<div class="league-view" data-league-view="{key}"{"" if key == default_league(S) else " data-off"}>{inner}</div>'


def filters(S) -> str:
    def group(key, label, values):
        keys = "".join(f'<button type="button" class="key" data-filter-{key}="{esc(v)}" aria-pressed="{str(v == "all").lower()}">'
                       f'<span class="lamp" aria-hidden="true"></span>{esc(v[:1].upper() + v[1:] if v != "all" else "All")}</button>'
                       for v in ["all"] + values)
        return (f'<div class="group" role="group" aria-labelledby="f-{key}"><span class="group-label" id="f-{key}">{label}</span>'
                f'<span class="keys" data-control="{key}">{keys}</span></div>')
    ms = list(S["setups_meta"].values())
    types = sorted({m["model_type"] for m in ms if m.get("model_type")})
    weights = sorted({m["weights"] for m in ms if m.get("weights")})
    runs = sorted({m["runs_on"] for m in ms if m.get("runs_on")})
    # Reasoning settings only; the v1 replay with shuffled plays is a play-order flag, not a setting.
    settings = sorted({m["setting"] for m in ms if m.get("setting")})
    return f"""<section class="panel filters is-open needs-js" id="filters" aria-label="Filters">
      <div class="filters-body" id="filters-body">
        {league_picker(S)}
        {group("type", "Model type", types)}{group("weights", "Weights", weights)}{group("runs", "Runs on", runs)}{group("setting", "Reasoning setting", settings)}
        <div class="group"><p class="filters-summary" data-summary aria-live="polite">All setups</p><button type="button" class="key reset" data-control="reset">Reset</button></div>
      </div>
    </section>"""


def league_head(S, lg) -> str:
    return (f'<div class="section-head"><h3>League {lg["id"]}</h3>{league_status_text(lg)}'
            f'<span class="small inline">{esc(LEAGUE_KIND.get(lg["id"], ""))}; league decisions, intervals resample whole games</span></div>')


def per_view(S, league_html, shared_html: str, v1_html: str | None) -> str:
    """A tab or section: one block per league, the shared positions, and the v1 set (Earlier version)."""
    out = []
    for lg in S["leagues"]:
        out.append(view_block(S, lg["dataset"], f'<div class="block" data-dataset="{lg["dataset"]}">'
                              f'{league_head(S, lg)}{league_html(lg)}</div>'))
    out.append(view_block(S, "shared", f'<div class="block"><div class="section-head"><h3>Shared positions</h3>'
                                       f'{status_badge(PENDING)}</div>{shared_html}</div>'))
    out.append(view_block(S, "v1-set", v1_html if v1_html else
                          f'<div class="block" data-version="v1"><div class="section-head"><h3>Earlier version: the v1 set</h3>'
                          f'{status_badge(EARLIER)}</div><p>{nm(NOT_MEASURED)} in the earlier version.</p></div>'))
    return "".join(out)


def tab_panel(S, key: str) -> str:
    """The tab's tables first, league by league; what they mean in a collapsed note under them."""
    rel = ""
    v1 = S["v1"]["setups"]
    cap = "Earlier version: v1 set, {n} positions, {k} setups".format(n=count(S["v1"]["positions"]), k=count(len(v1)))
    definition = (f'<p><strong>Thread {TAB_THREAD[key]}: {esc(THREADS[TAB_THREAD[key]])}.</strong> '
                  f'{esc(DEFINITIONS[key])}</p>')
    lt = lambda head, rows_fn, caption: (lambda lg: SWIPE + table(head, rows_fn(S, rel, lg["dataset"], lg["setups"]), caption,
                                                                   attrs=f' data-dataset="{lg["dataset"]}"'))
    pending = lambda what: f'<p class="pending">{status_badge(PENDING)} {esc(what)}</p>'
    earlier = lambda head, rows: earlier_block(S, SWIPE + table(head, rows, cap, attrs=' data-version="v1"'),
                                               "Earlier version: the v1 set")
    if key == "quality":
        body = per_view(S, lt(QUALITY_HEAD, quality_rows, "Decision quality in this league's games"),
                        pending("No setup has answered the shared positions yet; this view fills in when they do."),
                        earlier(QUALITY_HEAD, quality_rows(S, rel, "v1-set", v1)))
        note = ('<p>Error rate (PR): 500 \u00d7 the mean equity a setup gives away per decision, '
                'against GNUbg 2-ply; lower is better. The band is approximate: human ratings include doubling-cube '
                'decisions and these games have none. Invalid answers are left out of the error rate and counted next to it. '
                'Failed requests: a request that fails after retries leaves no decision, so they are not counted here. '
                'League games are not the same positions for every setup, so league rows are not paired comparisons.</p>')
        return body + about(definition + shared_note(S) + note)
    if key == "risk":
        body = per_view(S, lt(RISK_HEAD, risk_rows, "Risk in this league's games: shares with count / denominator"),
                        pending("Waits for the shared-position answers."),
                        earlier(RISK_HEAD, risk_rows(S, rel, "v1-set", v1)))
        return body + f'<p class="table-note risk-limit">{esc(RISK_LIMIT)}</p>' + about(
            definition + '<p>The 2\u00d72 for each setup: <a href="#risk-worth">Is the risk worth it?</a></p>')
    if key == "reasoning":
        body = per_view(S, lambda lg: league_reasoning_table(S, lg),
                        pending("Waits for the shared-position answers: the only paired comparison of two settings."),
                        earlier_block(S, SWIPE + table(REASON_HEAD, reasoning_rows(S, S["v1"]["reasoning"]),
                                                       "Earlier version: v1 set, paired on the same positions",
                                                       attrs=' data-version="v1"'), "Earlier version: the v1 set"))
        return body + about(definition)
    if key == "confidence":
        body = per_view(S, lt(CONF_HEAD, confidence_rows, "Confidence in this league's games"),
                        pending("Waits for the shared-position answers."),
                        earlier(CONF_HEAD, confidence_rows(S, rel, "v1-set", v1)))
        note = ('<p>Confidence metrics are N/A for setups that return only a choice: their recorded 1.0 '
                'is not 100% confidence. Compare confidence only between setups with the same confidence source. '
                '"Right" means the engine\'s best play.</p>')
        return body + about(definition + note)
    if key == "cost":
        body = per_view(S, lt(COST_HEAD, cost_rows, "Time and cost in this league"),
                        pending("Waits for the shared-position answers."),
                        earlier(COST_HEAD, cost_rows(S, rel, "v1-set", v1)))
        note = ('<p>Cost labels never mix: API price estimate, API-equivalent (subscription runs), own hardware, and '
                '"list-price estimate; runs on our GPUs". Request time is shown apart from retry and wait time. The v3 '
                'leagues had no clock, so the risk of running over a time budget was not measured; "Over the time '
                'budget" is the share of request times above it.</p>')
        return body + about(definition + note)
    if key == "stability":
        return (per_view(S, lambda lg: f'<p class="pending">{status_badge(NOT_MEASURED)} League games never repeat a position.</p>',
                         pending("Waits for the repeat answers (positions asked 5 times)."), None)
                + about(definition))
    raise KeyError(key)


def league_reasoning_table(S, lg) -> str:
    """Reasoning inside one league: not paired, so no verdict label (B9)."""
    rows = []
    for r in lg["reasoning"]:
        qa, qb = lg["setups"][r["low"]]["quality"], lg["setups"][r["high"]]["quality"]
        reading = esc(r["reading"]) if r["reading"] else nm(TOO_FEW)
        rows.append(f'<tr data-dataset="{lg["dataset"]}"><td class="model"><span class="model-name">{esc(r["model"])}</span>'
                    f'<span class="small">{esc(r["low_setting"])} \u2192 {esc(r["high_setting"])}</span></td>'
                    + er_cell(qa) + er_cell(qb)
                    + f'<td>{reading}</td>'
                    + f'<td class="num">{fmt(r["extra_time_median"], 1, True) if r["extra_time_median"] is not None else nm(NOT_MEASURED)}</td>'
                    + f'<td class="num">{fmt(r["extra_cost"], 3, True) if r["extra_cost"] is not None else nm(NOT_MEASURED)}</td></tr>')
    if not rows:
        return f'<p>{nm(NA)}: no model plays this league at two reasoning settings.</p>'
    head = ["Model", "Error rate (PR), lower setting", "Error rate (PR), higher setting", "In league play",
            "Extra median s per decision", "Extra $ per 1,000 decisions"]
    return (SWIPE + table(head, rows, "The same model at two settings in this league's games",
                          attrs=f' data-dataset="{lg["dataset"]}"')
            + '<p class="table-note">League games are not the same positions, so this comparison is not paired: it reads '
              '"lower/higher error rate in league play" only when the two 95% intervals do not overlap, and "no clear '
              'difference in league play" otherwise. The paired verdict waits for the shared positions.</p>')


DEFINITIONS = {
    "quality": "How much equity each move gives away, judged by the engine, not by wins: error rate with its 95% interval, the share of engine-best plays and of blunders.",
    "risk": "Whether risks were taken when they paid, and the decisions that averages hide: tail losses and blunders.",
    "reasoning": "What more reasoning buys: the same model at two settings.",
    "confidence": "Whether a model's probability for its play shows when the play is likely wrong.",
    "cost": "Dollars per 1,000 decisions and seconds per decision.",
    "stability": "Whether a setup repeats its play when asked the same position again.",
}

CHARTS = [("error-cost", "Error vs cost (log cost axis, line through the best-value setups)"),
          ("error-time", "Error vs median time per decision"),
          ("paired", "Paired low \u2192 high, per model"),
          ("risk-coverage", "Risk\u2013coverage curves"),
          ("phase-heatmap", "Game phase \u00d7 model")]


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
    risk = per_view(S, lambda lg: risk_tiles(S, "", lg["dataset"], lg["setups"], image=S.get("risk_images", {}).get(lg["dataset"])),
                    f'<p class="chart-status">{status_badge(PENDING)} Waits for the shared-position answers.</p>',
                    earlier_block(S, risk_tiles(S, "", "v1-set", S["v1"]["setups"]), "Earlier version: the v1 set"))
    lead = (f'<figure class="panel chart-card" id="chart-risk-2x2"><div class="chart-head"><h2>Is the risk worth it? 2 \u00d7 2</h2></div>'
            f'{risk}<p class="table-note risk-limit">{esc(RISK_LIMIT)}</p></figure>')
    cards = "".join(f'<figure class="panel chart-card" id="chart-{k}"><div class="chart-head"><h2>{esc(t)}</h2></div>'
                    f'<p class="chart-status">{status_badge(PENDING)} Shared positions (v3): waits for the shared-position answers.</p></figure>'
                    for k, t in CHARTS)
    v1 = (f'<figure class="panel chart-card" id="chart-v1-error" data-version="v1"><div class="chart-head"><h2>Error rate (PR) with 95% interval, v1 set</h2>'
          f'{status_badge(EARLIER)}</div><p class="note">{esc(play_order_note(S))}</p>{v1_chart(S)}</figure>')
    return f'<section class="charts" id="charts" aria-label="Charts" tabindex="-1">{lead}{cards}{v1}</section>'


# --- Is the risk worth it? (B6): the 2x2, the site's second signature ------------------------------------------

R2_CELLS = [("risk", "took", "good"), ("risk", "safe", "bad"), ("safety", "took", "bad"), ("safety", "safe", "good")]


def r2_cell(c: dict, tone: str) -> str:
    """One cell: share of its row (big), count / row total, mean equity lost. An empty cell shows 0 and no mean."""
    share = c["share"]
    big = pct(share, 0) if share is not None else "\u2013"
    mean = f'<span class="r2-loss">loses {eq(c["mean_loss"])}</span>' if c["mean_loss"] is not None else '<span class="r2-loss">no mean</span>'
    return (f'<div class="r2-cell r2-{tone}" style="--share:{share or 0:.3f}"><b>{big}</b>'
            f'<span class="r2-n">{count(c["n"])} / {count(c["den"])}</span>{mean}</div>')


def r2_tile(S, rel, dataset, name, r, reference=False) -> str:
    c = r["cells"]
    m = meta(S, dataset, name)
    grid = ('<div class="r2-grid"><span></span><span class="r2-col">Took a risk</span><span class="r2-col">Played safe</span>'
            f'<span class="r2-row">Risk pays<small>{count(r["risk_pays"])}</small></span>'
            + r2_cell(c["risk_took"], "good") + r2_cell(c["risk_safe"], "bad")
            + f'<span class="r2-row">Safety pays<small>{count(r["safety_pays"])}</small></span>'
            + r2_cell(c["safety_took"], "bad") + r2_cell(c["safety_safe"], "good") + "</div>")
    tag = '<span class="r2-ref">reference: never takes a risk</span>' if reference else ""
    return (f'<figure class="r2"{row_attrs(S, dataset, name)}><figcaption><a href="{model_href(rel, dataset, name, S)}">'
            f'{esc(name)}</a>{tag}<span class="small">{count(r["no_risk_choice"])} with no hit-risk trade-off, left out</span>'
            f'</figcaption>{grid}</figure>')


def risk_order(S, dataset, setups) -> list[tuple[str, bool]]:
    """The Safest program first (the reference row: what pure caution costs), then the setups by error rate;
    other programs and setups without risk decisions are left out."""
    ref = [(n, True) for n in setups if n == "Safest" and setups[n]["risk"]["decisions"]]
    rest = [(n, False) for n in by_error(setups) if n != "Safest" and setups[n]["risk"]["decisions"]
            and meta(S, dataset, n).get("model_type") != "program"]
    return ref + rest


def risk_tiles(S, rel, dataset, setups, image: str | None = None) -> str:
    tiles = "".join(r2_tile(S, rel, dataset, n, setups[n]["risk"], ref) for n, ref in risk_order(S, dataset, setups))
    if not tiles:
        return f'<p>{nm("Not scored yet")}</p>'
    img = (f'<p class="r2-image"><a href="{rel}{image}">The 2\u00d72 of this league as an image (PNG, 1200\u00d7675)</a></p>'
           if image else "")
    return (f'<div class="r2-key" aria-hidden="true"><span class="r2-good">good call</span><span class="r2-bad">costly call</span>'
            f'<span>big number: share of its row; small: count / row total, mean equity lost</span></div>'
            f'<div class="r2-wall" data-dataset="{dataset}">{tiles}</div>{img}')


def risk_table(S, rel, dataset, setups) -> str:
    """The 2x2 as a sortable table: each cell's count, share of its row and mean equity lost."""
    rows = []
    for n, ref in risk_order(S, dataset, setups):
        r = setups[n]["risk"]
        c = r["cells"]
        cell = (lambda k: f'<td class="num">{count(c[k]["n"])}<span class="small">'
                f'{pct(c[k]["share"]) if c[k]["share"] is not None else "0 / 0"}'
                f'{" · loses " + eq(c[k]["mean_loss"]) if c[k]["mean_loss"] is not None else ""}</span></td>')
        cells = (share_cell(r["takes_risk"], r["took_when_pays"], r["risk_pays"])
                 + share_cell(r["needless_risk"], r["took_needless"], r["safety_pays"])
                 + cell("risk_took") + cell("risk_safe") + cell("safety_took") + cell("safety_safe")
                 + f'<td class="num">{count(r["no_risk_choice"])}</td>')
        row = tr(S, dataset, n, cells, rel)
        rows.append(row.replace("<tr", '<tr class="reference"', 1) if ref else row)
    head = ["Model and setting", "Risk pays: took a risk", "Safety pays: took a needless risk",
            "Risk pays \u00d7 took a risk", "Risk pays \u00d7 played safe", "Safety pays \u00d7 took a risk",
            "Safety pays \u00d7 played safe", "No hit-risk trade-off"]
    return SWIPE + table(head, rows, "Each cell: count, share of its row, mean equity lost",
                         attrs=f' data-dataset="{dataset}"')


def risk_phase_table(S, rel, dataset, setups) -> str:
    rows = []
    for n, _ in risk_order(S, dataset, setups):
        ph = setups[n]["risk"]["phases"]
        cells = ""
        for p in A.PHASES:
            h = ph.get(p) or dict(risk_pays=0, safety_pays=0, took_when_pays=0, took_needless=0, takes_risk=None,
                                  needless_risk=None)
            a = f'{pct(h["takes_risk"], 0)} ({count(h["took_when_pays"])}/{count(h["risk_pays"])})' if h["risk_pays"] else "0/0"
            b = f'{pct(h["needless_risk"], 0)} ({count(h["took_needless"])}/{count(h["safety_pays"])})' if h["safety_pays"] else "0/0"
            cells += f'<td class="num">{a}<span class="small">{b}</span></td>'
        rows.append(tr(S, dataset, n, cells, rel))
    head = ["Model and setting"] + [PHASE_LABEL[p] for p in A.PHASES]
    return SWIPE + table(head, rows, "Per phase: Risk pays, took a risk (large); Safety pays, took a needless risk (small); "
                                     "count / denominator in brackets", attrs=f' data-dataset="{dataset}"')


def risk_card(S, lg) -> str | None:
    """The league's 2x2 wall as a standalone 1200 x 675 image for X: the core question, the league, up to ten tiles."""
    order = risk_order(S, lg["dataset"], lg["setups"])[:10]
    if not order:
        return None
    tiles = "".join(r2_tile(S, "", lg["dataset"], n, lg["setups"][n]["risk"], ref) for n, ref in order)
    css = (SITE_CSS_DIR / "bg.css").read_text()
    status = "Provisional: league still running" if lg["metric_status"] == PROVISIONAL else "Finished league"
    return f"""<!doctype html><html data-theme="dark"><head><meta charset="utf-8"><style>
:root{{--bg:#0f172a;--panel:#1e293b;--text:#e2e8f0;--text-2:#94a3b8;--edge:#334155;--sans:system-ui,sans-serif}}
{css}
body{{margin:0;width:1200px;height:675px;background:var(--bg);color:var(--text);font-family:var(--sans);padding:34px 44px;box-sizing:border-box}}
h1{{font-size:38px;margin:0 0 6px;line-height:1.1}} .sub{{font-size:19px;color:var(--text-2);margin:0 0 18px}}
.r2-wall{{grid-template-columns:repeat(5,1fr);gap:12px}} .r2 figcaption .small{{display:none}} .r2 figcaption a{{color:var(--text);text-decoration:none}}
.f{{position:absolute;bottom:22px;left:44px;right:44px;font-size:15px;color:var(--text-2);display:flex;justify-content:space-between}}
</style></head><body><h1>{esc(TITLE)}</h1>
<p class="sub">League {lg["id"]} ({esc(status)}): in decisions where risk pays, did the model take it, and where safety pays, did it stay safe? Share of each row.</p>
<div class="r2-wall">{tiles}</div>
<div class="f"><span>{esc(RISK_LIMIT)} Engine: GNU Backgammon 2-ply.</span><span>Zeki Works · {esc(version_line(S))}</span></div></body></html>"""


SITE_CSS_DIR = Path(__file__).resolve().parent / "assets"


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


def hero_board(S) -> str:
    """The board, the site's visual signature: a real Risk pays decision in which the model played safe, with the
    engine's best play drawn as arrows."""
    sc = S.get("showcase")
    if not sc:
        return ""
    from board import board_svg
    svg = board_svg(sc["board"], sc["dice"], sc["pips"], play=sc["best"]["notation"], cls="bd hero-bd",
                    label_extra=f"Arrows: the engine's best play, {sc['best']['notation']}.")
    href = f'decisions/?d={sc["dataset"]}&amp;s={sc["slug"]}&amp;p={sc["page"]}#d{sc["id"]}'
    return (f'<figure class="hero-board">{svg}<figcaption><strong>Risk paid here.</strong> League {sc["league"]}, '
            f'dice {sc["dice"][0]}-{sc["dice"][1]}: the engine\'s best play <code>{esc(sc["best"]["notation"])}</code> '
            f'(arrows) leaves {count(sc["best"]["hitting_rolls"])} hitting rolls; the best safe play gives away '
            f'{eq(sc["best_safe_loss"])}. {esc(sc["setup"])} played safe with <code>{esc(sc["chosen"]["notation"])}</code>. '
            f'<a href="{href}">Open this decision</a></figcaption></figure>')


FINDING_QUESTIONS = [  # one per thread; the first answers the core question
    (1, "#risk-worth", "Can a model tell when a risk is worth taking?"),
    (2, "#input", "How much of a model's play comes from the information we compute for it?"),
    (3, "#confidence", "Does a model know when it is likely wrong?"),
    (4, "#cost-reasoning", "What does each level of quality cost, and what does more reasoning buy?"),
]


def findings_block(S) -> str:
    import findings as F
    approved = sorted(F.published(), key=lambda f: f["thread"])
    if approved:
        items = "".join(f'<li><a href="{esc("#" + f["anchor"])}">{esc(f["text"])}</a></li>' for f in approved)
        return f'<div class="summary" id="findings"><ul class="summary-list">{items}</ul></div>'
    items = "".join(f'<li><span class="thread">{esc(THREADS[t])}</span> <a href="{a}">{esc(q)}</a></li>'
                    for t, a, q in FINDING_QUESTIONS)
    return (f'<div class="summary" id="findings"><p class="summary-lead findings-wait">Findings will be written when the '
            f'current leagues finish.</p><ul class="summary-list">{items}</ul></div>')


def input_history() -> str:
    """Thread 2 from the earlier version: the v1 prompt history table and its strongest finding, read from the archived
    'Why it looks like this' section (numbers as published there)."""
    import re
    src = (CONTENT_DIR / "archive/v1-why.html").read_text()
    tbl = re.search(r'<div class="table-wrap">.*?</table>\s*</div>', src, re.S).group(0)
    tbl = tbl.replace('<table class="board">', '<table class="board list" data-version="v1">', 1)
    row = lambda league: re.search(rf'<td class="num">{league}</td>.*?<td class="num">([\d.]+)</td></tr>', src, re.S).group(1)
    before, after = row("#6"), row("#7")
    return (f'<p class="lead-finding"><strong>Computing each play\'s consequences in code cut the error rate by about two '
            f'thirds</strong>: from {before} in league #6 to {after} in league #7, the step that added what each play '
            f'leads to (hits, blots left, how many of the opponent\'s 36 rolls hit them, points made). This is the '
            f'strongest finding so far.</p>{SWIPE}{tbl}'
            f'<p class="table-note">Each league added one change to the prompt. Error rate: GNU Backgammon\'s, over all '
            f'model decisions of the league (earlier scoring), lower is better; grey rows did not finish. The full story: '
            f'<a href="method/#v1-why">Method, Why it looks like this</a>.</p>')


def home(S) -> str:
    rel = ""
    tabs = "".join(f'<button type="button" role="tab" id="tab-{k}" class="mode" aria-controls="board" '
                   f'aria-selected="{str(i == 0).lower()}" data-tab="{k}"><span class="lamp" aria-hidden="true"></span>{l}</button>'
                   for i, (k, l) in enumerate(TABS))
    panels = "".join(f'<div class="tabpanel" id="panel-{k}" data-panel="{k}"{" hidden" if i else ""}>'
                     f'{tab_panel(S, k)}</div>'
                     for i, (k, _) in enumerate(TABS))
    th = S["thresholds"]
    pending = lambda what: f'<p class="pending">{status_badge(PENDING)} {esc(what)}</p>'
    risk_views = per_view(
        S, lambda lg: (risk_tiles(S, rel, lg["dataset"], lg["setups"], image=S.get("risk_images", {}).get(lg["dataset"]))
                       + '<details class="more"><summary>The same as a table</summary>' + risk_table(S, rel, lg["dataset"], lg["setups"])
                       + "</details>" + '<details class="more"><summary>By game phase</summary>'
                       + risk_phase_table(S, rel, lg["dataset"], lg["setups"]) + "</details>"
                       + ("" if any(n == "Safest" for n in lg["setups"]) else
                          '<p class="table-note">Reference: the Safest program, which never takes a risk, plays in '
                          f'<a href="#risk-worth" data-league-goto="{S["leagues"][0]["dataset"]}">League {S["leagues"][0]["id"]}</a>.</p>')),
        pending("Waits for the shared-position answers."),
        earlier_block(S, risk_tiles(S, rel, "v1-set", S["v1"]["setups"]), "Earlier version: the v1 set"))
    conf_views = per_view(
        S, lambda lg: tail_table(S, rel, lg["dataset"], lg["setups"]),
        pending("Waits for the shared-position answers: confidence is compared on the same positions."),
        earlier_block(S, SWIPE + table(CONF_HEAD, confidence_rows(S, rel, "v1-set", S["v1"]["setups"]),
                                       "Earlier version: v1 set, confidence per setup", attrs=' data-version="v1"'),
                      "Earlier version: the v1 set"))
    reason_views = per_view(
        S, lambda lg: league_reasoning_table(S, lg),
        pending("Waits for the shared-position answers: the paired comparison with a verdict."),
        earlier_block(S, SWIPE + table(REASON_HEAD, reasoning_rows(S, S["v1"]["reasoning"]),
                                       "Earlier version: v1 set, paired on the same positions", attrs=' data-version="v1"'),
                      "Earlier version: the v1 set"))
    thread = lambda n: f'<span class="thread">Thread {n}: {esc(THREADS[n])}</span>'
    return f"""
    <header class="hero hero-split">
      <div class="hero-text">
        <h1>{TITLE}</h1>
        <p class="subtitle">{esc(subtitle(S))}</p>
        <p class="intro">{esc(INTRO)}</p>
        <p class="hero-links"><a class="key" href="data/results.json" download>Results (JSON)</a> <a class="key" href="decisions/index.json">Decisions (JSON)</a> <a class="key" href="decisions/">Every decision</a> <a class="key" href="method/">Method</a></p>
        <div class="readout-row">
          <ul class="readouts">{readouts(S)}</ul>
          <p class="version">{esc(version_line(S))}</p>
        </div>
      </div>
      {hero_board(S)}
    </header>
    {findings_block(S)}
    {filters(S)}
    <section class="panel board-panel" id="board-panel" aria-labelledby="board-title">
      <div class="section-head"><h2 id="board-title">Leaderboard</h2>{thread(1)}</div>
      <div class="modebar">
        <div class="keys view-switch needs-js" role="group" aria-label="Show the results as"><button type="button" class="key" data-view="table" aria-pressed="true"><span class="lamp" aria-hidden="true"></span>Table</button><button type="button" class="key" data-view="charts" aria-pressed="false"><span class="lamp" aria-hidden="true"></span>Charts</button></div>
        <div class="modes" role="tablist" aria-label="Leaderboard metric">{tabs}</div>
      </div>
      <p class="version-line">One league at a time; leagues are never merged. League games are not the same positions, so league rows are not paired. Shared positions: Analysis pending.</p>
      <div id="board" role="tabpanel">{panels}</div>
      {charts(S)}
    </section>

    <section class="card" id="risk-worth">
      <div class="section-head"><h2>Is the risk worth it?</h2>{thread(1)}</div>
      <p class="section-lead">For every scored decision: does the engine say the risk pays, or safety? And did the model take a risk or play safe? Good calls are green, costly calls red.</p>
      {league_picker(S, "Show")}
      {risk_views}
      <p class="table-note risk-limit">{esc(RISK_LIMIT)}</p>
      {about(f'''<p>Hitting rolls are the numbers the model was shown: for each legal play, how many of the opponent's 36
      rolls hit. Minimum risk: the fewest hitting rolls any legal play leaves. Best safe play: among the plays that leave
      the minimum, the one the engine rates best. <strong>Safety pays</strong>: the best safe play loses less than
      {th['safety_pays_loss_below']} equity against the engine's best play. <strong>Risk pays</strong>: it loses
      {th['safety_pays_loss_below']} or more. <strong>No hit-risk trade-off</strong>: every legal play leaves the same
      number of hitting rolls; these decisions are counted and left out of every share. The model took a risk if its play
      leaves more hitting rolls than the minimum. A share's denominator is its row's class. Full definitions:
      <a href="method/#risk">Method</a>.</p>''', "About this section")}
    </section>

    <section class="card" id="input">
      <div class="section-head"><h2>What the input adds</h2>{thread(2)}{status_badge(EARLIER)}</div>
      {input_history()}
      {pending("The same question on the current version (each piece of computed information switched off in turn) waits for the shared-position answers.")}
      <p class="table-note">{esc(play_order_note(S))}</p>
    </section>

    <section class="card" id="confidence">
      <div class="section-head"><h2>Confidence: does a model know when it is likely wrong?</h2>{thread(3)}</div>
      {league_picker(S, "Show")}
      {conf_views}
      {about(f'''<p>Does confidence track error, per confidence source (decision-model probability, letter probability;
      setups that name one play have none). "Confident and badly wrong": the model gave its play a probability of at
      least {th['very_confident_probability_at_least']} and lost more than {th['badly_wrong_loss_above']} equity. Tail
      risk: the 95th percentile of the equity lost per decision and the mean loss of the worst
      {pct(th['worst_share'], 0)} of decisions. Risk–coverage curves and calibration on the same positions wait for the
      shared-position answers.</p>''', "About this section")}
    </section>

    <section class="card" id="cost-reasoning">
      <div class="section-head"><h2>Cost and reasoning</h2>{thread(4)}</div>
      <p class="section-lead">What each level of quality costs in time and money, and what more reasoning buys. Time and cost per setup: the leaderboard's <a href="?tab=cost#board" data-goto-tab="cost">Cost</a> tab; the quality vs cost chart: <a href="#chart-error-cost" data-view-goto="charts">Charts</a> ({esc(PENDING)}).</p>
      <h3 id="reasoning">What more reasoning buys</h3>
      {league_picker(S, "Show")}
      {reason_views}
      <h3 id="routing">Routing and teams</h3>
      {pending("Which decisions a cheap model can handle before handing over to a strong one, and whether a team picks better plays than its best member, wait for the shared-position answers.")}
      <p class="table-note">A team "oracle", the best answer any member gave, is an upper bound and never a working system. The earlier version's team results: <a href="leagues/#earlier">Leagues</a> (Earlier version).</p>
    </section>

    <section class="card" id="learning">
      <div class="section-head"><h2>Learning from experience</h2>{thread(5)}{status_badge(NOT_MEASURED)}</div>
      <p>Every decision is a separate request; models are not told how earlier games went.</p>
    </section>

    <section class="card" id="more">
      <h2>Leagues, Method and Data</h2>
      <p><a href="leagues/">Leagues</a>: standings, matches and each league's notes, one table per league. <a href="method/">Method</a>: setup, prompt, rules,
      error rate, human scale, statistics, fixed thresholds, the anchor and the runner changes during the leagues.
      <a href="data/">Data</a>: every download, versions and how to recompute.</p>
    </section>"""


CONTENT_DIR = Path(__file__).resolve().parent / "content"


# --- Leagues ------------------------------------------------------------------------------------------------

def standings(S, lg, rel) -> str:
    rows = []
    for t in lg["standings"]:
        cells = (f'<td class="num">{t["place"]}</td><td class="num">{t["played"]}</td>'
                 f'<td class="num">{t["won"]}-{t["drawn"]}-{t["lost"]}</td>'
                 f'<td class="num">{t["points"]}</td><td class="num">{t["games_won"]}-{t["games_lost"]}</td>'
                 f'<td class="num">{t["gammons_won"]}</td><td class="num">{t["to_play"]}</td>')
        rows.append(tr(S, lg["dataset"], t["name"], cells, rel))
    head = ["Model and setting", "Place", "Played", "Won-drawn-lost", "Points", "Games won-lost", "Gammons won", "To play"]
    return SWIPE + table(head, rows, "Standings: 3 points a win, 1 a draw; only finished league-stage matches count",
                         attrs=f' data-dataset="{lg["dataset"]}"')


MATCH_STATE = {"finished": "Finished", "running": "Running", "aborted": "Stopped", None: "Not started"}


def matches_table(S, lg, rel) -> str:
    """Every league-stage match; a row opens the first decision of the first-named player in that match."""
    rows = []
    for m in lg["matches_list"]:
        links = []
        for side in ("model1", "model2"):
            first = m[side + "_first"]
            if first:
                links.append(f'<a href="{rel}decisions/?d={lg["dataset"]}&amp;s={first["slug"]}&amp;p={first["page"]}#d{first["id"]}">'
                             f'{esc(m[side])}</a>')
        href = links[0].split('"')[1].replace("&amp;", "&") if links else None
        score = f'{m["score1"]}\u2013{m["score2"]}' if m["status"] else ""
        rows.append(f'<tr data-dataset="{lg["dataset"]}"{f" data-href={chr(34)}{esc(href)}{chr(34)}" if href else ""}>'
                    f'<td class="model"><span class="model-name">{esc(m["model1"])} v {esc(m["model2"])}</span></td>'
                    f'<td class="num">{m["matchday"]}</td><td class="num">{score}</td>'
                    f'<td>{esc(MATCH_STATE.get(m["status"], m["status"]))}</td><td class="num">{m["games"]}</td>'
                    f'<td>{" · ".join(links) if links else nm(NA)}</td></tr>')
    head = ["Match", "Matchday", "Score", "Status", "Games", "Decisions of each player"]
    return SWIPE + table(head, rows, "Matches; a row opens the first-named player's decisions in that match",
                         attrs=f' data-dataset="{lg["dataset"]}"')


def league_notes(S, lg) -> str:
    """Notes generated from the same data as the league's tables (B5): nothing typed by hand."""
    notes = []
    if lg["standings"]:
        t = lg["standings"][0]
        notes.append(f'{"Leads" if lg["metric_status"] == PROVISIONAL else "Won"}: {esc(t["name"])}, {t["points"]} points '
                     f'from {t["won"]}-{t["drawn"]}-{t["lost"]} in {t["played"]} matches.')
    rows = [(n, s["quality"]) for n, s in lg["setups"].items() if meta(S, lg["dataset"], n).get("model_type") != "program"
            and s["quality"].get("error_rate") is not None and not s["quality"].get("too_few")]
    if rows:
        rows.sort(key=lambda r: r[1]["error_rate"])
        best, q = rows[0]
        close = [n for n, x in rows[1:] if x["error_lo"] <= q["error_hi"]]
        notes.append(f'Lowest error rate in league play: {esc(best)}, {fmt(q["error_rate"])} ({fmt(q["error_lo"])} to '
                     f'{fmt(q["error_hi"])}); no clear difference in league play from '
                     f'{esc(", ".join(close)) if close else "no other model setup"}.')
    for r in lg["reasoning"]:
        if r["reading"]:
            notes.append(f'{esc(r["model"])}, {esc(r["low_setting"])} \u2192 {esc(r["high_setting"])}: {esc(r["reading"])}.')
    notes.append("League comparisons are not paired: each setup met different positions. Paired comparisons come from "
                 "the shared positions.")
    notes.append('The anchor is GNU Backgammon 1.08 Beginner, x86-64 build; runner changes during the leagues are listed '
                 'in <a href="../method/#v3-changes">Method</a>.')
    return f'<ul class="league-notes">{"".join(f"<li>{n}</li>" for n in notes)}</ul>'


def leagues_page(S, archive_v1: str) -> str:
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
                      f'{standings(S, lg, rel)}'
                      f'<p class="table-note">{count(lg["matches_done"])} of {count(lg["matches"])} matches finished, {count(lg["games"])} games; '
                      f'{esc(dates)}. {count(lg["scored"])} of {count(lg["decisions"])} decisions engine-scored so far.</p>'
                      f'<h3 id="league-{lg["id"]}-notes">Notes</h3>{league_notes(S, lg)}'
                      f'<h3 id="league-{lg["id"]}-quality">Decision quality</h3>{q}'
                      f'<h3 id="league-{lg["id"]}-cost">Time and cost</h3>{c}'
                      f'<details class="more" id="league-{lg["id"]}-matches"><summary>Matches ({count(lg["matches"])})</summary>'
                      f'{matches_table(S, lg, rel)}</details></section>')
    intro = about("<p>One table per league. League tables compare only the players inside one league; they are never "
                  "merged into one overall score. A running league's numbers are Provisional and change as matches finish. "
                  "Click a row to open the setup, or a match to open its decisions.</p>", "About these tables")
    return (page_head(S, "Leagues", "Leagues")
            + "".join(blocks) + intro
            + f'<section class="card" id="earlier"><details class="more"><summary>Earlier version: v1 leagues and teams '
              f'{status_badge(EARLIER)}</summary><p class="note">{esc(play_order_note(S))}</p>{archive_v1}</details></section>')


# --- Phases -------------------------------------------------------------------------------------------------

def phases_page(S) -> str:
    rel = "../"
    out = [page_head(S, "Phases", "Where do models fail?")]
    out.append(f'<section class="card" id="shared"><div class="section-head"><h2>Shared positions</h2>{status_badge(PENDING)}'
               f'<span class="small inline">waits for the shared-position answers</span></div></section>')
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
        note = f'<p class="table-note">{esc(play_order_note(S))}</p>' if not lg else ""
        out.append(f'<section class="card" id="{ds}" data-dataset="{ds}"><div class="section-head"><h2>{esc(title)}</h2>'
                   f'{badge}</div>{body}{note}</section>')
    out.append(about("<p>Error rate by game phase, strategy tag, number of legal plays and the equity gap between the "
                     "two best plays. Each league on its own; the shared-position version waits for the answers. A cell "
                     "with fewer decisions than the minimum shows the status instead of a value.</p>", "About these tables"))
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
    if m.get("play_order"):
        out.append(f"<dt>Play order</dt><dd>{esc(m['play_order'])}</dd>")
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
            share = lambda s, n, d: f"{pct(s)} ({count(n)} / {count(d)})" if d else "0 / 0"
            cells += (f"<dt>Risk pays: took a risk</dt><dd>{share(r['takes_risk'], r['took_when_pays'], r['risk_pays'])}</dd>"
                      f"<dt>Safety pays: took a needless risk</dt><dd>{share(r['needless_risk'], r['took_needless'], r['safety_pays'])}</dd>"
                      f"<dt>No hit-risk trade-off</dt><dd>{count(r['no_risk_choice'])} (left out)</dd>")
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
    """One table per dataset: the B7 fields that differ between setups; a row opens the setup's page."""
    head = ["Setup", "Model type", "Weights", "Runs on", "Reasoning setting", "Confidence source", "Missing B7 fields"]

    def rows(dataset, names):
        out = []
        for n in names:
            m = meta(S, dataset, n)
            cells = "".join(f"<td>{esc(m.get(k)) if m.get(k) else nm('Missing')}</td>"
                            for k in ("model_type", "weights", "runs_on", "reasoning", "confidence_source"))
            cells += f'<td class="num">{count(len(m.get("missing") or []))}</td>'
            out.append(tr(S, dataset, n, cells, "../"))
        return out

    groups = []
    for lg in S["leagues"]:
        groups.append(f'<section class="card" id="{lg["dataset"]}"><div class="section-head"><h2>League {lg["id"]}</h2>'
                      f'{league_status_text(lg)}</div>{SWIPE}'
                      + table(head, rows(lg["dataset"], lg["setups"]), "Setups in this league", attrs=f' data-dataset="{lg["dataset"]}"')
                      + "</section>")
    groups.append(f'<section class="card" id="v1-set" data-version="v1"><div class="section-head"><h2>v1 set</h2>{status_badge(EARLIER)}</div>{SWIPE}'
                  + table(head, rows("v1-set", S["v1"]["setups"]), "Setups of the earlier version", attrs=' data-dataset="v1-set"')
                  + "</section>")
    groups.append(f'<section class="card" id="smoke-part-a"><h2>New models: first look (smoke tests)</h2>{SWIPE}'
                  + table(head, rows("smoke-part-a", sorted(r["setup"] for r in S["smoke"])), "Smoke-tested setups",
                          attrs=' data-dataset="smoke-part-a"') + "</section>")
    return (page_head(S, "Models", "Model setups") + "".join(groups)
            + about("<p>One page per setup, with how it was called. Setups are not identical: they differ in model "
                    "type, where they run, reasoning setting, confidence source and option groups.</p>", "About these tables"))


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
    return (page_head(S, "Where models disagree", "Where do models disagree?")
            + f'<section class="card" id="v1" data-version="v1"><div class="section-head"><h2>Earlier version: the v1 set</h2>{status_badge(EARLIER)}</div>'
              + SWIPE + table(head, rows, "The 150 positions with the most different plays (then the fewest engine-best choices); "
                              "a row opens the position in Every decision", attrs=' data-version="v1"')
              + f'<p class="table-note">{count(d["positions"])} positions, {count(len(S["v1"]["setups"]))} setups. All setups chose '
                f'the same play in {count(d["all_agree"])} positions. {esc(play_order_note(S))}</p>'
              + '<details class="more"><summary>How many different plays the setups chose</summary>'
              + table(["Different plays chosen", "Positions"], [dist], "Positions by the number of different plays chosen", cls="board list")
              + "</details></section>"
            + f'<section class="card" id="shared"><div class="section-head"><h2>Shared positions</h2>{status_badge(PENDING)}'
              f'<span class="small inline">waits for the shared-position answers</span></div></section>')


def new_models_page(S) -> str:
    # Models that also play a league (Part A ran them before or alongside it): their smoke rows stay, marked.
    in_league = {}
    for lg in S["leagues"]:
        for n in lg["setups"]:
            in_league.setdefault(meta(S, lg["dataset"], n).get("model"), lg["id"])
    rows = []
    for r in sorted(S["smoke"], key=lambda r: r["setup"].lower()):
        m = meta(S, "smoke-part-a", r["setup"])
        ci = r.get("error_ci") or [None, None]
        pairs = "".join(f'<span class="small">vs {esc(p["reference"])}: {fmt(p["diff"], 1, True)} ({fmt(p["ci"][0], 1, True)} to {fmt(p["ci"][1], 1, True)}), n = {p["positions"]}</span>'
                        for p in r.get("paired", []) if p["reference"] != r["setup"])
        price = m.get("price") or {}
        league = in_league.get(m.get("model"))
        also = (f'<span class="small also-league">also in <a href="../leagues/#league-{league}">League {league}</a></span>'
                if league else "")
        rows.append(
            f'<tr data-dataset="smoke-part-a"><td class="model"><a class="model-name" href="../models/smoke-part-a/{m["slug"]}/">{esc(r["setup"])}</a>'
            f'<span class="small">{esc(m.get("provider") or "")}</span>{also}</td>'
            f'<td>{esc(r["probabilities"])}</td><td>{esc(m.get("reasoning") or "")}</td>'
            f'<td class="num">{fmt(r["request_s_p50"], 1)} / {fmt(r["request_s_p90"], 1)}</td>'
            f'<td class="num">{fmt(r["usd_per_1000"], 2) if r.get("usd_per_1000") is not None else nm(NOT_MEASURED)}'
            f'<span class="small">{esc(price.get("label", ""))}</span></td>'
            f'<td class="num">{pct(r["invalid"] / r["asked"], 0)}<span class="small">{r["invalid"]} / {r["asked"]}; {r["failed"]} failed, {r["timed_out"]} timed out</span></td>'
            f'<td class="num">{fmt(r["error_rate"])}<span class="small">{fmt(ci[0])} to {fmt(ci[1])}; n = {r["answered"]}</span></td>'
            f'<td class="num">{pairs}</td></tr>')
    head = ["Setup", "Probabilities", "Reasoning setting", "Median / P90 request s", "$ per 1,000 decisions",
            "Invalid share", "Error rate (PR), 95% interval", "Paired difference from the reference setups"]
    return (page_head(S, "New models: first look", "New models: first look")
            + '<section class="card" id="smoke"><p><strong>50 positions each, outside the shared sets. Error rates are rough '
              '(about \u00b110 to \u00b125): enough to spot a clearly weak model, not to rank models.</strong> This page feeds no '
              'ranking, chart or finding. Sorted by name.</p>' + SWIPE
            + table(head, rows, "Smoke tests: the same 50 positions for every setup, with the v3 prompt and shuffled plays")
            + '<p class="note">Every value is shown with its count and interval: the minimum-sample rule of the other pages '
              'does not apply here. Rows marked "also in League N" are models that also play a league; their league '
              'results are on the Leagues page and are never compared with these 50 positions.</p></section>')


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
            + f'<section class="card" id="downloads"><h2>Downloads</h2>'
              f'<p class="hero-links"><a class="key" href="../data/results.json" download>Results (JSON)</a> '
              f'<a class="key" href="../decisions/index.json">Decisions (JSON index)</a></p>'
              f'<p>Results: every league\'s results per setup, one league per key. Decisions: the index of every decision '
              f'file, one gzip JSON file per setup and page of 50 decisions, with the board, the plays as shown, the '
              f'engine\'s equities, the model\'s choice and its "Is the risk worth it?" class.</p>'
              + SWIPE + table(["File", "Bytes", "sha256"], [rows], "Data files of this build", cls="board list")
              + f'<p class="table-note">Data files are split per version, league and model, '
              f'so each loads on a phone. Every number on the site is in one of them. The decision files behind '
              f'<a href="../decisions/">Every decision</a> are under <code>decisions/</code> ({count(S["decision_files"])} files, gzip-compressed JSON).</p></section>'
            + f'<section class="card" id="status"><h2>Analysis status</h2>{status_list(S)}</section>'
            + '<section class="card" id="versions"><h2>Versions</h2><dl class="facts">'
              '<dt>v3</dt><dd>Prompt bg-v2, plays in a seeded random order, invalid answers not retried. Leagues 1 to 3 and the shared positions.</dd>'
              f'<dt>v1</dt><dd>{status_badge(EARLIER)} Earlier prompt; plays listed in the runner\'s order. The v1 set of 1,000 positions answered by the v1 setups. Never in a v3 table or chart.</dd>'
              '<dt>Smoke tests</dt><dd>50 positions outside the shared sets, v3 prompt; only on New models: first look.</dd></dl></section>'
            + '<section class="card" id="recompute"><h2>How to recompute</h2><ol>'
              '<li>Snapshot the league database: <code>python3 tools/site/snapshot.py v3.db STATE</code> (one read transaction; the prompts each model was sent go to <code>STATE/prompts.db</code>).</li>'
              '<li>Score every legal play of every decision with GNUbg 1.08 at 2-ply: <code>tools/site/score.sh STATE/snap.db STATE/plays</code>.</li>'
              '<li>Build and check the site: <code>python3 tools/site/build.py --state STATE --out OUT</code>. The build fails, and nothing is deployed, if a number does not trace to a data file, counts do not add up, leagues or versions mix, a published finding no longer holds, or a file contains a private address or credential.</li>'
              '</ol><p>The scripts are in the jevgammon repository under <code>tools/site/</code>; the fixed thresholds are in <a href="thresholds.json">thresholds.json</a>.</p></section>')


def decisions_page(S, body: str) -> str:
    return body + f'<p class="version version-line">{esc(version_line(S))}</p>'


def share_card(S) -> str:
    """The link preview card (1200 x 630), drawn from the current results: the board beside the question."""
    from board import board_svg
    sc = S.get("showcase")
    c = S["counts"]
    css = (SITE_CSS_DIR / "decisions.css").read_text()
    board = board_svg(sc["board"], sc["dice"], sc["pips"], play=sc["best"]["notation"]) if sc else ""
    cap = (f'League {sc["league"]}: the engine\'s best play {esc(sc["best"]["notation"])} (arrows) leaves '
           f'{sc["best"]["hitting_rolls"]} hitting rolls; playing safe gave away {eq(sc["best_safe_loss"])}.') if sc else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{css}
:root{{--text:#e2e8f0;--sans:system-ui,sans-serif;--bd-frame:#3d3226;--bd-felt:#1e293b;--bd-a:#6b5a43;--bd-b:#2f6f63;--bd-tray:#162032;--bd-num:#94a3b8;--bd-me:#ebe9e4;--bd-me-edge:#0e0e0d;--bd-opp:#9a3b2e;--bd-opp-edge:#f0b8ad;--bd-die:#ebe9e4;--bd-die-edge:#0e0e0d;--bd-pip:#1a1a18}}
body{{margin:0;width:1200px;height:630px;background:#0f172a;color:#e2e8f0;font-family:system-ui,sans-serif;display:flex;gap:44px;align-items:center;padding:0 56px;box-sizing:border-box}}
.l{{flex:0 0 520px}} .l svg{{width:520px;height:auto;display:block}} .l p{{font-size:17px;color:#94a3b8;margin:12px 0 0;line-height:1.35}}
.r{{flex:1}} h1{{font-size:50px;margin:0 0 18px;line-height:1.08}} .s{{font-size:23px;color:#cbd5e1;margin:0 0 26px;line-height:1.3}}
ul{{list-style:none;padding:0;margin:0;display:flex;gap:28px}} li b{{display:block;font-size:40px;color:#2dd4bf}} li{{font-size:18px;color:#94a3b8}}
.f{{position:absolute;bottom:26px;right:56px;font-size:17px;color:#64748b}}</style></head><body>
<div class="l">{board}<p>{cap}</p></div>
<div class="r"><h1>{esc(TITLE)}</h1><p class="s">Every backgammon decision scored by an engine: decision quality, what the input adds, confidence and cost.</p>
<ul><li><b>{count(c["decisions_scored"])}</b>decisions</li><li><b>{c["leagues"]}</b>leagues</li><li><b>{c["model_setups"]}</b>setups</li><li><b>{c["models"]}</b>models</li></ul></div>
<div class="f">Zeki Works · every decision is public</div></body></html>"""


def description(S) -> str:
    st = "; ".join(f"League {lg['id']} {lg['status'].lower()}" for lg in S["leagues"])
    return (f"{subtitle(S)} {count(S['counts']['decisions_scored'])} decisions scored by GNU Backgammon so far ({st}). "
            f"Every decision is public.")


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
    put("", TITLE, home(S), scripts=("bg.js",), styles=("decisions.css",), body_class="home")
    put("leagues/", "Leagues", leagues_page(S, method.archive_v1()), scripts=("bg.js",))
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
