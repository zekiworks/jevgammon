"""Pages of the backgammon site. Every number comes from S (build.compute), the same dicts that build.py
writes to data/; nothing here holds a result number. Status words follow brief B10."""

import json
import re
from pathlib import Path

import analysis as A
import own_cost
from common import (EARLIER, EARLIER_NOTE, LATE_ENTRY, LATE_ENTRY_LABEL, LATE_ENTRY_NOTE, NA, NAME_NOTES, NOT_MEASURED,
                    OUT_OF_SCOPE, OUT_OF_SCOPE_OPPONENTS, PENDING, PROVISIONAL, PROVISIONAL_NOTE, PUBLISHED,
                    REASONING_NOTES, ROOT, SUITE_BAR, TOO_FEW, aliases, count, esc, fmt, nm, pct, relabel, setup_slug,
                    shown_names_html, slug, status_badge, unplayed_text)
from common import SHARED_NAMES, effort_aliases, model_key, name_and_tag, name_html, name_text, tag_html, tag_text

# The site's top bar (Ümit #2901, as Clocktower Bench's): the Hilde leaf and the site's name, then one row of tabs. Each
# tab is a page; every other page sits under one tab (SECTION), which is marked while it is in view. The pages that are
# not tabs (Matches, Phases, Compare, Where models disagree, Leagues, Models, Data, Method) are linked from the
# Leaderboard (the Text tab) and the About page (MORE_PAGES). Vision is a short page: no vision runs yet.
TABS = [("", "Text"), ("vision/", "Vision"), ("improve/", "Learning"), ("decisions/", "Decisions"),
        ("highlights/", "Highlights"), ("experiments/", "Experiments"), ("about/", "About")]
# Learning (Ümit #4178): "Did they improve?" (improve/), with the learning pilot (learning/) under it.
SECTION = {"clear-risk/": "experiments/", "learning/": "improve/", "nackgammon/": "experiments/", "method/": "about/",
           "data/": "about/"}
MORE_PAGES = [("matches/", "Matches"), ("phases/", "Phases"), ("compare/", "Compare"),
              ("disagreements/", "Where models disagree"), ("leagues/", "Leagues"), ("models/", "Every model setup"),
              ("method/", "Method"), ("data/", "Data")]
SITE_NAME = "Backgammon bench"
# The Hilde leaf: Hilde Reader's bare copper leaf (hilde repository, assets/reader-leaf.svg), copied byte for byte.
LEAF = "hilde-leaf.svg"
TITLE = "Backgammon: do models take the right risks, and do they learn from their games?"
# The learning pilot's tab name inside its page (Ümit #2553/#2557) and its address.
TAB_LEARNING = "Learning across games"
TAB_LEARNING_PATH = "learning/"
# Reviewed brief of 24 Oct 2026, item 2: the subtitle, used with the title in the hero, the meta description, the social
# preview and the PNG headers (png.js, bg.js read both from the body's data attributes).
SUBTITLE = "And when does playing safe cost more?"
# TEMPORARY (Can, 23 Oct 2026): the "Export page as PNG" key in the top bar (assets/png.js); False removes it.
EXPORT_PAGE_PNG = True


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
    return f"Results {S['hash']}, updated {as_of(S)}; scored by GNU Backgammon 1.08, 2-ply."


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


def table(head: list, rows: list[str], caption: str, cls="board", attrs="") -> str:
    """head: header texts; a (text, extra attributes) pair adds attributes to that header (e.g. data-nosort)."""
    th = "".join(f'<th scope="col"{" class=num" if i else ""}{h[1] if isinstance(h, tuple) else ""}>'
                 f'{h[0] if isinstance(h, tuple) else h}</th>' for i, h in enumerate(head))
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
    return dict(dataset=dataset, name=name, slug=setup_slug(dataset, name), model=name, setting=None, model_type=None,
                weights=None, runs_on=None, confidence_source=None, missing=["every B7 field"], sources=[],
                aliases=aliases(name) if dataset.startswith("league-") else [])


def origin_meta(S, dataset, name) -> dict:
    """The setup's setups.json entry for its model facts (model type, confidence source, price); a setup that came into
    this league by a ladder move is listed under the league it came from."""
    m = S["setups_meta"].get((dataset, name))
    if m:
        return m
    return next((m for (d, n), m in S["setups_meta"].items() if n == name and d.startswith("league-")),
                meta(S, dataset, name))


def model_href(rel, dataset, name, S) -> str:
    return f"{rel}models/{dataset}/{meta(S, dataset, name)['slug']}/"


def row_attrs(S, dataset, name) -> str:
    m = meta(S, dataset, name)
    return (f' data-dataset="{esc(dataset)}" data-type="{esc(m.get("model_type") or "unknown")}"'
            f' data-weights="{esc(m.get("weights") or "unknown")}" data-runs="{esc(m.get("runs_on") or "unknown")}"'
            f' data-setting="{esc(m.get("setting") or "none")}"')


def model_cell(S, rel, dataset, name) -> str:
    """The setup's cell: its official name and tag (setting · route · snapshot), how it was called under it."""
    m = meta(S, dataset, name)
    shown, parts = name_and_tag(name, dataset)
    bits = [x for x in (m.get("model_type"), m.get("runs_on"), m.get("play_order") and "shuffled play order") if x]
    return (f'<td class="model"><a class="model-name" href="{model_href(rel, dataset, name, S)}">{esc(shown)}</a>'
            f'{tag_html(tag_text(parts))}<span class="small">{esc(" · ".join(bits))}</span></td>')


def tr(S, dataset, name, cells: str, rel: str) -> str:
    return f"<tr{row_attrs(S, dataset, name)}>{model_cell(S, rel, dataset, name)}{cells}</tr>"


def by_error(setups: dict) -> list[str]:
    def key(n):
        q = setups[n]["quality"]
        return (q.get("error_rate") is None or q.get("too_few", False), q.get("error_rate") or 0, n)
    return sorted(setups, key=key)


def own_cost_hint(q, text: str) -> str:
    """text with the cost explanation as a tooltip (site.css .hint: hover, keyboard focus and tap; Ümit #4450): the
    estimate in dollars per 1,000 decisions and how it was counted (own_cost.tooltip, the gaps as a count); text
    alone for a recorded cost."""
    if not q or not q.get("own_cost"):
        return text
    return (f'<span class="hint" tabindex="0" data-tip="{esc(own_cost.tooltip(q["own_cost"], every_gap=False))}">'
            f'{text}</span>')


def own_cost_sort(q) -> str:
    """data-v for an own-machine cost cell: its estimate, so the column sorts by cost (tables.js) whatever the cell's
    second line; no estimate, no data-v (the machine's name sorts after every number)."""
    return f' data-v="{q["usd_per_1000"]:.3f}"' if own_machine(q) and q.get("usd_per_1000") is not None else ""


def own_machine(q) -> str | None:
    """Where a setup on our machines ran (own_cost.basis: the machine it used most, '+ API' for a mixed route); None
    for any other setup."""
    return own_cost.basis(q["own_cost"]) if q and q.get("own_cost") else None


def own_cost_text(q, amount: str) -> str:
    """An own-machine cost as every cost cell shows it (Ümit #4665 item 4, as logic #4685): the amount first, as an API
    cell rounds it, then a small second line 'estimate · DGX Spark' (mixed route: '… + API'); how it was counted on
    hover, focus and tap. No estimate yet (a rate pending): the machine's name alone."""
    if q.get("usd_per_1000") is None:
        return own_cost_hint(q, esc(own_machine(q)))
    return own_cost_hint(q, amount) + f'<span class="small">estimate \u00b7 {esc(own_machine(q))}</span>'


def cost_cell(S, dataset, name, q) -> str:
    label = (origin_meta(S, dataset, name).get("price") or {}).get("label")
    if own_machine(q):
        return f'<td class="num"{own_cost_sort(q)}>{own_cost_text(q, fmt(q.get("usd_per_1000"), 3))}</td>'
    if q.get("usd_per_1000") is None:
        why = NOT_MEASURED if q.get("cost_coverage", 0) == 0 else f"Priced for {pct(q['cost_coverage'], 0)} of decisions"
        return f'<td class="num">{nm(why)}</td>'
    return (f'<td class="num">{own_cost_hint(q, fmt(q["usd_per_1000"], 3))}'
            f'<span class="small">{esc(label or "label missing")}</span></td>')


# --- Shared blocks ----------------------------------------------------------------------------------------

def league_status_text(lg) -> str:
    s = status_badge(lg["status"])
    if lg["metric_status"] == PROVISIONAL:
        s += status_badge(PROVISIONAL_NOTE)
    else:
        s += status_badge(PUBLISHED)
    return s


def play_order_shuffled(S) -> str:
    """The shuffled-order check behind EARLIER_NOTE (play_order_note without its first sentence)."""
    p = S["v1"]["play_order"]
    return (f"When {p['setup']} answered the same {count(p['positions'])} positions with the plays "
            f"shuffled, its error rate changed by {fmt(p['diff'], 1, True)} (95% interval {fmt(p['lo'], 1, True)} to "
            f"{fmt(p['hi'], 1, True)}), so the effect is not proven.")


def play_order_note(S) -> str:
    return f"{EARLIER_NOTE} {play_order_shuffled(S)}"


def star_note(line: str, more: str, cls: str = "note") -> str:
    """One short line in front and its longer explanation under a '*' (Ümit via Zeki #4649, as Logic & Math's #4611,
    #4650): line and more are HTML; more is one or more block elements."""
    return (f'<details class="{cls} star-note"><summary>{line} <span class="star">*</span></summary>{more}</details>')


def about(inner: str, label: str = "About this table") -> str:
    """Explanatory prose, collapsed: the tables lead and the text is one click away."""
    return f'<details class="about"><summary>{esc(label)}</summary>{inner}</details>'



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


# --- Layout -------------------------------------------------------------------------------------------------

# The one sticky header of every page (Ümit #2901; the suite's shared component, Zeki #2270, #2290): the suite strip
# (common.SUITE_BAR, the shared snippet with Backgammon marked; its look is suite-bar.css, copied verbatim), then the
# site's bar: the Hilde leaf and the site's name (the Leaderboard's link) with the colour theme and More options, and
# under them the tabs (TABS), one row that scrolls sideways on a phone, the tab of the page in view underlined.
def tab_of(path: str) -> str:
    """The tab a page sits under: its own, its SECTION's, else the Leaderboard's."""
    for prefix, tab in SECTION.items():
        if path.startswith(prefix):
            return tab
    return next((href for href, _ in TABS if href and path.startswith(href)), "")


# The tab row keeps the id of the old Part row (view-part), so an old link to #view-part still lands on the site's parts.
def site_header(rel: str, path: str, controls: str) -> str:
    here = tab_of(path)
    tabs = "".join(f'<li><a href="{rel}{href or ("" if rel else "./")}"'
                   f'{(" aria-current=page" if href == path else " aria-current=true") if href == here else ""}>'
                   f'{esc(label)}</a></li>' for href, label in TABS)
    return (f'<div class="site-header">\n  {SUITE_BAR}\n  <header class="site-bar"><div class="site-bar-in">'
            f'<div class="site-title-row"><a class="site-title" href="{rel or "./"}"><img class="site-leaf" '
            f'src="{rel}{LEAF}" width="18" height="21" alt="">{esc(SITE_NAME)}</a>{controls}</div>'
            f'<nav class="site-tabs" id="view-part" aria-label="Sections"><ul>{tabs}</ul></nav></div></header>\n  </div>')


# The first script of every page, before the stylesheets apply (Zeki, bus #2310): the theme is always named on <html>
# (data-theme "light" or "dark"; the suite strip, suite-bar.css, follows it, and without it the reader's system), first
# from the system's setting (dark when it asks for dark, else light), then from the reader's stored choice where storage
# can be read; a browser that refuses storage keeps the first. The cost unit: ?cost-unit=, else the stored choice.
HEAD_SCRIPT = ('<script>(function () { var d = document.documentElement; d.classList.add("js"); '
               'd.dataset.theme = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; '
               'var u = new URLSearchParams(location.search).get("cost-unit"); '
               'try { var t = localStorage.getItem("theme"); if (t === "light" || t === "dark") d.dataset.theme = t; '
               'if (!u) u = localStorage.getItem("costUnit"); } catch (e) {} '
               'if (u === "1m") d.dataset.costUnit = "1m"; })();</script>')


def layout(S, base, path: str, title: str, body: str, description: str | None = None, main_class: str = "",
           scripts=(), styles=(), body_class: str = "", dataset: str | None = None) -> str:
    """dataset: the dataset of the page's setups where it is not the leagues' (their routes in the names' tags)."""
    depth = path.count("/")
    rel = "../" * depth
    desc = description or S["description"]
    full = f"{title} · Hilde" if title != TITLE else f"{TITLE} · Hilde"
    social = full if title != TITLE else f"{TITLE} {SUBTITLE} · Hilde"
    image = f'{base}{S["image"]}' if S.get("image") else None
    og = (f'<meta property="og:image" content="{image}"><meta property="og:image:width" content="1200">'
          f'<meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">'
          f'<meta name="twitter:image" content="{image}">') if image else ""
    css = "".join(f'<link rel="stylesheet" href="{rel}{s}">' for s in ("suite-bar.css", "site.css", "bg.css") + tuple(styles))
    js = "".join(f'<script src="{rel}{s}" defer></script>' for s in ("site.js", "tables.js", "png.js") + tuple(scripts))
    # The Dark / Light switch sits in the site's bar beside its name, as on the Decision models site (Ümit, 31 Oct 2026);
    # More options keeps the page export ("More" on a phone, its name unchanged).
    theme = ('<div class="theme-switch" role="group" aria-label="Colour theme" hidden><button type="button" class="key" '
             'data-theme-choice="dark" aria-pressed="true" aria-label="Dark background"><span class="lamp" aria-hidden="true">'
             '</span>Dark<span class="long"> background</span></button><button type="button" class="key" '
             'data-theme-choice="light" aria-pressed="false" aria-label="Light background"><span class="lamp" '
             'aria-hidden="true"></span>Light<span class="long"> background</span></button></div>')
    more = ('<div class="more-menu needs-js"><button type="button" class="key more-toggle" data-more-toggle aria-expanded="false" '
            'aria-controls="more-options" aria-label="More options">More<span class="more-long"> options</span><span '
            'class="chevron" aria-hidden="true"></span></button>'
            '<div class="more-pop" id="more-options" hidden><p class="more-label">Share</p><button type="button" class="key '
            'page-png" data-page-png hidden>Export page as PNG</button></div></div>' if EXPORT_PAGE_PNG else "")
    # Old model names in any text become the model's display name, every shown name the maker's official name and its
    # tag (common.shown_names_html, Ümit #4282 item 4, #4445); data-names: the page's setups' dataset, for checks.py.
    return shown_names_html(f"""<!doctype html>
<html lang="en"{f' data-names="{dataset}"' if dataset else ""}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full)}</title>
  <link rel="canonical" href="{base}{path}">
  <meta name="description" content="{esc(desc)}">
  <meta property="og:title" content="{esc(social)}"><meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website"><meta property="og:url" content="{base}{path}">
  <meta name="twitter:title" content="{esc(social)}"><meta name="twitter:description" content="{esc(desc)}">
  {og}
  <meta name="color-scheme" content="dark light">
  {HEAD_SCRIPT}
  {css}
  {js}
</head>
<body class="v3 {body_class}" data-site-title="{esc(TITLE)}" data-site-subtitle="{esc(SUBTITLE)}">
  <a class="skip" href="#main">Skip to content</a>
  {site_header(rel, path, f'<div class="site-controls">{theme}{more}</div>')}
  <main id="main"{f' class="{main_class}"' if main_class else ''}>
{body}
  </main>
  <footer class="footer">
    <nav class="footer-links" aria-label="Site"><a href="{rel}about/">About</a> · <a href="{rel}method/">Method</a> · <a href="{rel}data/">Data</a> · <a href="{GITHUB}">GitHub</a></nav>
    <p{' id="downloads"' if not path else ""}>Download: <a href="{rel}data/results.json" download="results.json">results.json</a> · <a href="{rel}decisions/index.json" download="decisions.json">decisions.json</a> · <a href="{rel}data/">every data file</a></p>
    <p>{esc(version_line(S))}</p>
  </footer>
</body>
</html>
""", dataset)


def page_head(S, eyebrow: str, title: str, intro: str = "", more: str = "") -> str:
    """A page's first card, as the sibling site's: the eyebrow, the title, the intro and the results version. more (HTML,
    optional): the intro's longer explanation, under a '*' after the intro."""
    lead = (star_note(intro, f"<p>{more}</p>", "intro") if more else f"<p class=intro>{intro}</p>") if intro else ""
    return (f'<header class="card hero page-head"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1>'
            f'{lead}<p class="version">{esc(version_line(S))}</p></header>')


# --- Home ---------------------------------------------------------------------------------------------------

def league_reasoning_table(S, lg) -> str:
    """Reasoning inside one league: every model with both settings in this league's games. Not paired, so no verdict
    label (B9). Risk judgement and error rate are separate measures, read separately."""
    def judgement(r):
        if r["judgement"] is None:
            return f'<td class="num">{nm(r["judgement_na"])}</td>'
        return (f'<td class="num">{fmt(r["judgement"])}<span class="small">{fmt(r["judgement_lo"])} to '
                f'{fmt(r["judgement_hi"])}</span></td>')
    rows, notes = [], []
    for r in lg["reasoning"]:
        lo, hi = lg["setups"][r["low"]], lg["setups"][r["high"]]
        qa, qb = lo["quality"], hi["quality"]
        reading = esc(r["reading"]) if r["reading"] else nm(TOO_FEW)
        if r["risk"] is None:
            change = overlap = f'<td class="num">{nm(NA)}</td>'
        else:
            change = f'<td class="num">{fmt(r["risk"]["change"], 1, True)}</td>'
            overlap = f'<td>{"yes" if r["risk"]["overlap"] else "no"}</td>'
        rows.append(f'<tr data-dataset="{lg["dataset"]}"><td class="model"><span class="model-name">{esc(r["model"])}</span>'
                    f'<span class="small">{esc(r["low_setting"])} \u2192 {esc(r["high_setting"])}</span></td>'
                    + judgement(lo["risk"]["main"]) + judgement(hi["risk"]["main"]) + change + overlap
                    + er_cell(qa) + er_cell(qb)
                    + f'<td>{reading}</td>'
                    + f'<td class="num">{secs(qa.get("time_median"))} \u2192 {secs(qb.get("time_median"))}</td>'
                    + f'<td class="num">{fmt(r["extra_time_median"], 1, True) if r["extra_time_median"] is not None else nm(NOT_MEASURED)}</td>'
                    + f'<td class="num">{fmt(r["extra_cost"], 3, True) if r["extra_cost"] is not None else nm(NOT_MEASURED)}</td></tr>')
        if REASONING_NOTES.get(r["model"]):
            notes.append(f'<strong>{esc(r["model"])}</strong>: {esc(REASONING_NOTES[r["model"]])}')
    if not rows:
        return f'<p>{nm(NA)}: no model plays this league at two reasoning settings.</p>'
    head = ["Model", "Risk judgement, lower setting", "Risk judgement, higher setting", "Risk judgement change",
            "Risk judgement intervals overlap", "Error rate (PR), lower setting", "Error rate (PR), higher setting",
            "Error rate, in league play", "Median s per decision", "Extra median s per decision",
            "Extra $ per 1,000 decisions"]
    return (SWIPE + table(head, rows, "The same model at a lower and a higher reasoning setting in this league's games",
                          attrs=f' data-dataset="{lg["dataset"]}"')
            + '<p class="table-note">Every model with both settings in this league\'s games is listed. Risk judgement '
              '(margin 0.001, 95% intervals from resampling whole games) and error rate are two separate measures: the '
              '"Error rate, in league play" column is about error rate only and says nothing about risk judgement. The '
              'risk judgement change is the higher setting minus the lower, from unrounded values. Whether two intervals '
              'overlap describes them; it is not a test of a difference.</p>'
            + '<p class="table-note">League games are not the same positions, so this comparison is not paired and shows '
              'no effect of the setting: a higher or lower value at the higher setting is not evidence that reasoning '
              'caused it. For error rate it reads "lower/higher error rate in league play" only when the two 95% '
              'intervals do not overlap, and "no clear difference in league play" otherwise. The paired verdict waits '
              'for the shared positions.</p>'
            + "".join(f'<p class="table-note">{n}</p>' for n in notes))


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



def hero_numbers(dec: dict, label: str, who: str, slug_: str, page: int) -> dict:
    """The numbers of one decision for the hero board, from an exported decision: its B6.1 marks (computed by
    decisions_export.mark_risk with analysis.risk_class), the engine's best play, the best safe play, the play made."""
    plays, r = dec["plays"], dec["risk"]
    pick = lambda i: dict(notation=plays[i]["notation"], hitting_rolls=plays[i]["hitting_rolls"], loss=plays[i]["loss"])
    return dict(dataset=dec["dataset"], label=label, who=who, id=dec["id"], slug=slug_, page=page,
                dice=dec["dice"], board=dec["board"], pips=dec["pips"], phase=dec["phase"], kind=r["class"],
                call=r["call"], stake=dec["stake"], best=pick(dec["best"]), best_safe=pick(r["best_safe"]),
                chosen=pick(dec["chosen"]))





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
            f'<a href="#v1-why">Why it looks like this</a>.</p>')




CONTENT_DIR = Path(__file__).resolve().parent / "content"


# --- Leagues ------------------------------------------------------------------------------------------------

def standings(S, lg, rel) -> str:
    """A league's standings as published, each row with its starting group and its recorded league moves."""
    import starting_groups as SG
    rows = []
    for t in lg["standings"]:
        cells = (f'<td class="num">{t["place"]}</td><td class="num">{t["played"]}</td>'
                 f'<td class="num">{t["won"]}-{t["drawn"]}-{t["lost"]}</td>'
                 f'<td class="num">{t["points"]}</td><td class="num">{t["games_won"]}-{t["games_lost"]}</td>'
                 f'<td class="num">{t["gammons_won"]}</td><td class="num">{t["to_play"]}</td>'
                 + SG.standing_cells(S, t["name"]))
        rows.append(tr(S, lg["dataset"], t["name"], cells, rel))
    head = ["Model and setting", "Place", "Played", "Won-drawn-lost", "Points", "Games won-lost", "Gammons won", "To play",
            "Starting group", ("League moves", " data-nosort")]
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


def league_sections(S) -> str:
    """The Leagues page's tab bar and its sections (Starting groups, After league moves, Cups, Late entries), written for
    the Leagues page (links relative to leagues/)."""
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
                      f'{matches_table(S, lg, rel)}<p class="table-note">This league table\'s matches. Every match of every '
                      f'stage (ladder rounds, gap matches, late entries, the Hype Cup, the Nackgammon knockout) and the '
                      f'voided ones: <a href="../matches/">Matches</a>.</p></details></section>')
    import starting_groups as SG
    leagues = [(f'league-{lg["id"]}', f'League {lg["id"]}', f'sub-panel-league-{lg["id"]}') for lg in S["leagues"]]
    after_head, after_note = SG.after_moves_intro(S)
    after = (after_head + link_tabs(leagues, "sub", "Leagues after the moves", "modes sub-tabs")
             + "".join(tab_panel(pid, f"sub-tab-{key}", b, "sub-panel") for (key, _, pid), b in zip(leagues, blocks))
             + after_note)
    late = late_entries_section(S, rel)
    cups_head, cups_note = SG.cups_intro()
    return league_tabs({"starting-groups": SG.section(S), "after-league-moves": after,
                        "cups": cups_head + cup_card(S) + cups_note, **({"late-entries": late} if late else {})})


# The home page's league block had every id prefixed "lg-" (#lg-starting-groups, #lg-hype-cup …) until Ümit #2938; its
# old anchors land on the same section of the Leagues page (moved_anchors).
HOME_PREFIX = "lg-"


def rebase(html: str, rel: str, local_ids: set | None = None) -> str:
    """HTML written relative to the site's root, moved to a page `rel` deep (rel "../"): every relative href and src
    gets rel in front; a same-page anchor (#id) does too unless the id is in local_ids (None: anchors stay)."""
    def fix(m):
        attr, v = m.group(1), m.group(2)
        if v.startswith(("http:", "https:", "mailto:", "data:", "/", "?", "../", "javascript:")):
            return m.group(0)
        if v.startswith("#") and (local_ids is None or v[1:] in local_ids):
            return m.group(0)
        return f'{attr}"{rel}{v}"'
    return re.sub(r'(\s(?:href|src)=)"([^"]*)"', fix, html)


def ids_of(html: str) -> set:
    return set(re.findall(r'\sid="([^"]+)"', html))


def moved_anchors(moved: dict, league_ids: set) -> dict:
    """{old home id: new address}: every id of each block that left the home page (moved: {page path: ids of the block
    now on that page}), and the old home league block's lg- ids, each to the same id on the Leagues page."""
    out = {i: f"{path}#{i}" for path, ids in moved.items() for i in sorted(ids)}
    out.update({HOME_PREFIX + i: f"leagues/#{i}" for i in sorted(league_ids)})
    out["leagues-tabs"] = "leagues/#leagues-tabs"  # the old home block's wrapper: the Leagues page's tab bar
    return out


def leagues_page(S, archive_v1: str) -> tuple[str, set, set]:
    """(page, ids of the blocks moved here from the home page, ids of the league sections). The moved blocks (Ümit
    #2938 item 2; home.leagues_moved) frame the league sections: the overview first, then the sections, then the
    filters, the measure sections and Every number."""
    import home
    top, bottom = home.leagues_moved(S)
    sections = league_sections(S)
    intro = about("<p>One table per league. League tables compare only the players inside one league; they are never "
                  "merged into one overall score. A running league's numbers are Provisional and change as matches finish. "
                  "Click a row to open the setup, or a match to open its decisions.</p>", "About these tables")
    earlier = (f'<section class="card" id="earlier"><details class="more"><summary>Earlier version: v1 leagues and teams '
               f'{status_badge(EARLIER)}</summary><p class="note">{esc(play_order_note(S))}</p>{archive_v1}</details>'
               f'<p class="table-note" id="pre-switch">The page as it was before this site went live, with its final league '
               f'data: <a href="../archive/2026-10-23/">archive, 23 October 2026</a>.</p></section>')
    head = page_head(S, "Leagues", "Leagues")
    local = ids_of(head + top + sections + bottom + intro + earlier)
    page = head + rebase(top, "../", local) + sections + rebase(bottom, "../", local) + intro + earlier
    return page, ids_of(top) | ids_of(bottom), ids_of(sections)


# --- Leagues page tabs (Can, 31 Oct 2026): the home page's tab keys as links, one section at a time (bg.js), with a
# smaller second level (the starting groups, the leagues after the moves); the URL hash picks the tabs; without the
# script every section shows and the tabs are plain jump links. ---------------------------------------------------

LEAGUE_TABS = [("starting-groups", "Starting groups", "league-panel-starting-groups"),
               ("after-league-moves", "After league moves", "league-panel-after-league-moves"),
               ("hype-cup", "Hype Cup", "league-panel-cups"), ("nack-knockout", "Nackgammon knockout", "league-panel-cups"),
               ("late-entries", "Late entries", "league-panel-late-entries")]


def link_tabs(items: list[tuple[str, str, str]], kind: str, label: str, cls: str = "modes") -> str:
    """A tablist of links drawn as the home page's tab keys: (target id, label, panel id); the first is selected."""
    return (f'<div class="{cls}" role="tablist" aria-label="{esc(label)}">'
            + "".join(f'<a class="mode" role="tab" id="{kind}-tab-{key}" href="#{key}" aria-selected="{str(i == 0).lower()}" '
                      f'aria-controls="{pid}" data-tab="{key}"><span class="lamp" aria-hidden="true"></span>{esc(text)}</a>'
                      for i, (key, text, pid) in enumerate(items))
            + '</div>')


def tab_panel(pid: str, tab_id: str, html: str, cls: str) -> str:
    return f'<div class="tabpanel {cls}" role="tabpanel" id="{pid}" aria-labelledby="{tab_id}">{html}</div>'


def league_tabs(panels: dict[str, str]) -> str:
    """The Leagues page's tab bar (Every match links to the Matches page) and its sections, one tabpanel each; a tab
    whose section has nothing to show (no late entry) is left out."""
    tabs = [t for t in LEAGUE_TABS if t[2][len("league-panel-"):] in panels]
    first = {}
    for key, _, pid in tabs:
        first.setdefault(pid, key)
    nav = (f'<nav class="league-tabs" id="leagues-tabs" aria-label="Leagues sections" data-league-tabs>'
           f'{link_tabs(tabs, "league", "Leagues sections")}'
           f'<a class="mode" href="../matches/"><span class="lamp" aria-hidden="true"></span>Every match</a></nav>')
    return nav + "".join(tab_panel(f"league-panel-{key}", f"league-tab-{first[f'league-panel-{key}']}", html, "league-panel")
                         for key, html in panels.items())


# --- Hype Cup and Nackgammon knockout (Can, 29 Oct 2026) ------------------------------------------------------

TIE_STATE = {"played": "Played", "stored": "Stored", "to play": "To play", "waits": "To play", "playing": "Playing now"}
ROUND_OF = {"QF": "Quarter-finals", "SF": "Semi-finals", "FI": "Final"}


def match_anchor(source: str, match_id: int) -> str:
    return f'{"k" if source == "knockout" else "m"}{match_id}'


def match_ref(source: str, match_id: int) -> str:
    return f'{"knockout match" if source == "knockout" else "match"} #{match_id}'


def tie_box(t: dict, source: str, prefix: str, rel: str, labels: dict) -> str:
    """One tie of a bracket: its two setups (seed, name, score), the winner marked, and how its result came about."""
    sides = []
    for k in ("1", "2"):
        name = t["model" + k]
        if name is None:
            src = t["from_ties"][int(k) - 1]
            sides.append(f'<li class="side tbd"><span class="seed"></span><span class="name">Winner of {esc(labels[src])}</span>'
                         f'<span class="score"></span></li>')
            continue
        win = t.get("winner") == name
        score = t.get("score" + k)
        sides.append(f'<li class="side{" win" if win else ""}"><span class="seed">{t["seed" + k]}</span>'
                     f'<span class="name">{esc(name)}{"<span class=visually-hidden> (winner)</span>" if win else ""}</span>'
                     f'<span class="score">{score if score is not None else ""}</span></li>')
    state = t.get("state")
    head = f'<span class="tie-state state-{slug(state)}">{TIE_STATE[state]}</span>'
    foot = ""
    if t.get("match") is not None and state in ("played", "stored"):
        link = f'<a href="{rel}matches/#{match_anchor(source, t["match"])}">{match_ref(source, t["match"])}</a>'
        when = t["finished"][:10]
        if state == "stored":
            foot = f'Played in {esc(t["where"])}, {when}: {link}'
        else:
            foot = f'{when}: {link}'
        if t.get("level"):
            foot += (f'. Level; {esc(t["winner"])} goes through on the lower error rate in the match'
                     if t.get("winner") else ". Level; the error rate in the match decides, not yet scored")
    elif state == "playing":
        foot = "In progress"
    elif state == "waits":
        foot = "Waits for " + " and ".join(esc(labels[x]) for x in t["from_ties"])
    return (f'<li class="tie tie-{slug(state)}" id="{prefix}-{t["tie"].lower()}"><p class="tie-head">'
            f'<span class="tie-name">{esc(t["label"])}</span>{head}</p><ol class="tie-sides">{"".join(sides)}</ol>'
            f'{f"<p class=tie-foot>{foot}</p>" if foot else ""}</li>')


def bracket(ties: list[dict], source: str, prefix: str, rel: str, caption: str) -> str:
    rounds, labels = {}, {t["tie"]: t["label"] for t in ties}
    for t in ties:
        rounds.setdefault(ROUND_OF[t["tie"][:2]], []).append(t)
    cols = "".join(f'<div class="bracket-round"><h4>{esc(name)}</h4><ol class="ties">'
                   f'{"".join(tie_box(t, source, prefix, rel, labels) for t in ts)}</ol></div>' for name, ts in rounds.items())
    return f'<div class="bracket" role="group" aria-label="{esc(caption)}">{cols}</div>'


def cup_card(S, rel: str = "../") -> str:
    """The Hype Cup and the Nackgammon knockout: each heading, then its bracket (the winner marked in it), then its
    notes (Ümit via Zeki #4666: no champion line or text above a bracket)."""
    c, k = S["cup"], S["knockout"]
    k_left = ('' if k["state"] == "finished" else
              f'<p class="table-note">{count(k["played"])} of {count(k["matches_total"])} matches played; the rest to play.</p>')
    return (f'<section class="card cup-card" id="hype-cup"><div data-tab-part="hype-cup"><div class="section-head"><h2>Hype Cup</h2>'
            f'{status_badge("Finished" if c["state"] == "finished" else "In progress")}</div>'
            + bracket(c["ties"], "v3", "cup", rel, "Hype Cup bracket")
            + f'<p class="table-note"><strong>Played</strong> ({count(c["new_matches"])}): a new Cup match. '
              f'<strong>Stored</strong> ({count(c["stored_matches"])}): {esc(c["stored_rule"])} {esc(c["level_rule"])}</p>'
              f'<p class="table-note"><strong>Roster.</strong> {esc(c["roster_rule"])}</p></div>'
              f'<div data-tab-part="nack-knockout"><div class="section-head cup-sub"><h3 id="nack-knockout">{esc(k["name"])}</h3>'
              f'{status_badge("Finished" if k["state"] == "finished" else "In progress")}</div>'
            + bracket(k["ties"], "knockout", "nack", rel, "Nackgammon knockout bracket")
            + f'<p class="note"><strong>{esc(k["label"])}.</strong> {esc(k["about"])}</p>{k_left}'
            + f'</div><p class="table-note">Every match of both, with the leagues\' matches: <a href="{rel}matches/">Matches</a>. '
              f'{esc(c["honesty"])}</p></section>')


# --- Matches ------------------------------------------------------------------------------------------------

def match_row(m: dict, rel: str) -> str:
    links = []
    for side in ("model1", "model2"):
        first = (m.get("decisions") or {}).get(side)
        if first:
            links.append(f'<a href="{rel}decisions/?d={first["dataset"]}&amp;s={first["slug"]}&amp;p={first["page"]}'
                         f'#d{first["id"]}">{esc(m[side])}</a>')
    stage = esc(m["stage_label"]) + (f'<span class="small">{esc(m["note"])}</span>' if m.get("note") else "")
    winner = esc(m["winner"]) if m["winner"] else "Draw"
    num = f'K{m["id"]}' if m["source"] == "knockout" else str(m["id"])
    return (f'<tr id="{match_anchor(m["source"], m["id"])}"{" class=late-entry" if m["stage"] == "late-entry" else ""}>'
            f'<td class="model"><span class="model-name">{esc(m["model1"])} v {esc(m["model2"])}</span></td>'
            f'<td class="num">{num}</td><td class="date">{m["finished"][:10]}</td><td>{stage}</td>'
            f'<td class="num">{m["score1"]}\u2013{m["score2"]}</td><td>{winner}</td>'
            f'<td>{" · ".join(links) if links else nm("not on the site")}</td></tr>')


MATCH_HEAD = ["Match", "#", "Finished", "Stage", "Score", "Winner", "Decisions of each player"]


def matches_page(S) -> str:
    rel = "../"
    M = S["matches"]
    by = {}
    for m in M["matches"]:
        by.setdefault(m["stage"], []).append(m)
    nav = "".join(f'<li><a href="#stage-{s["stage"]}">{esc(s["label"])}</a> ({count(s["matches"])})</li>' for s in M["stages"])
    nav += f'<li><a href="#voided">Voided</a> ({count(M["voided_total"])})</li>'
    blocks = []
    for s in M["stages"]:
        rows = by.get(s["stage"], [])
        if s["stage"] == "season":
            parts = {}
            for m in rows:
                parts.setdefault(f'League {m["league"]}', []).append(m)
        elif s["stage"] == "ladder":
            parts = {}
            for m in sorted(rows, key=lambda m: (m["round"], m["id"])):
                parts.setdefault(f'Ladder round {m["round"]}', []).append(m)
        else:
            parts = {"": rows}
        inner = []
        for title, ms in parts.items():
            sid = f'stage-{s["stage"]}-{slug(title)}' if title else ""
            inner.append((f'<h3 id="{sid}">{esc(title)} ({count(len(ms))})</h3>' if title else "")
                         + SWIPE + table(MATCH_HEAD, [match_row(m, rel) for m in ms],
                                         f'{s["label"]}{": " + title if title else ""}; in the order the matches started',
                                         cls="board list"))
        note = {"ladder": "Matches a ladder move made: the mover against the setups of its new league it had not met. "
                          "Early starts of a round are in it.",
                "gap": "Pairs missing from a league's round robin, played later under that league's rules.",
                "late-entry": "Late entry, not in standings: these matches count in no table and in no other setup's "
                              "numbers; only the results are shown here.",
                "cup": 'New Hype Cup matches; the Cup\'s stored results are listed where they were played. Bracket: '
                       '<a href="../leagues/#hype-cup">Leagues</a>.',
                "knockout": 'From the Nackgammon start (its own database). Bracket: '
                            '<a href="../leagues/#nack-knockout">Leagues</a>.'}.get(s["stage"], "")
        blocks.append(f'<section class="card" id="stage-{s["stage"]}"><div class="section-head"><h2>{esc(s["label"])}</h2>'
                      f'<span class="small">{count(s["matches"])} matches</span></div>'
                      f'{f"<p class=note>{note}</p>" if note else ""}'
                      + ("".join(inner) if rows else f'<p class="note">{nm("None yet")}</p>') + '</section>')
    void_rows = [f'<tr><td class="model"><span class="model-name">{esc(m["model1"])} v {esc(m["model2"])}</span></td>'
                 f'<td class="num">{m["id"]}</td><td class="date">{m["finished"][:10]}</td>'
                 f'<td class="num">{m["score1"]}\u2013{m["score2"]}</td><td>{esc(m["reason"] or "")}</td></tr>'
                 for m in M["voided"]]
    blocks.append(f'<section class="card" id="voided"><details class="more"><summary>Voided matches '
                  f'({count(M["voided_total"])}): finished, then voided; they count nowhere</summary>'
                  + SWIPE + table(["Match", "#", "Finished", "Score", "Why voided"], void_rows,
                                  "Voided matches, with the reason recorded when they were voided", cls="board list")
                  + '</details></section>')
    intro = (f'Every finished match: {count(M["total"])}, by stage. Results only: the standings and error rates are on '
             '<a href="../leagues/">Leagues</a>. A match is listed once, where it was played; the setups carry their '
             'current names.')
    return (page_head(S, "Matches", "Every match")
            + f'<nav class="card stage-nav" aria-label="Stages"><ul class="subnav">{nav}</ul></nav>' + "".join(blocks)
            + f'<p class="table-note page-note">{intro}</p>')


# --- Late entries (Can's go of 28 Oct 2026, live after GPT-6 Astra (high)'s 12th late-entry match): a tab of the
# Leagues block after the Nackgammon knockout; their own rows, never in a standings table. ------------------------

LATE_ABOUT = ("A late entry joins an original league table after it was played and plays every setup of that table "
              "once, in matches of its own. Its games count in no standings table, no league table, no Hype Cup input "
              "and no other setup's numbers. The numbers here come from its own late-entry games only, computed as for "
              "a setup in a league.")
# On About and Leagues only (Zeki #2930, explaining Ümit #2921).
LATE_RANKED = ("Late entries are ranked on the risk leaderboard; they do not change league match-points standings, "
               "Cups, or other setups' results.")
LATE_METHOD = ("Error rate and risk judgement: 95% intervals, whole games resampled. Ability d\u2032 and caution c at "
               "the 0.001 margin: rates corrected by adding 0.5 to the counts and 1 to the totals; 95% intervals, blocks "
               "of two seat-swapped games resampled. Cut off: answers that stopped at an output limit the request sent "
               "(finish reason length, stop reason max_tokens, finishReason MAX_TOKENS, incomplete max_output_tokens), "
               "in the stored response or error. Effort: the reasoning effort the requests sent. Engine's best play: "
               "the share of its scored decisions that chose the engine's best play (equity loss under the best-play "
               "threshold). Time: median request seconds per decision (waits between retries not included). Cost per "
               "1,000 decisions: the recorded tokens at the price shown, as labelled there (list or billed price; for a "
               "setup on our GPUs the hosted model's list price, not billed).")


def late_status(e) -> str:
    """Published when every pair of its field was played or is outside the requested scope (build.late_entry_summaries);
    a pair not played for a recorded reason (content/late_entries.json) is named as such, never as a loss; otherwise
    still playing."""
    if e["status"] != PROVISIONAL:
        return status_badge(PUBLISHED)
    gone = e.get("not_played") or []
    left = [g for g in gone if not g.get("out_of_scope")]
    if left and not e["running"] and e["played"] + len(gone) == e["total"]:
        return status_badge(f"{PROVISIONAL}: {count(len(left))} {'pair' if len(left) == 1 else 'pairs'} not played")
    return status_badge(LATE_ENTRY_NOTE)


def late_cost(e) -> str:
    """$ per 1,000 decisions at the price its setups.json entry records (label, source, date read), and, where it was
    billed at another price, the billed figure (build.late_entry_summaries) beside it."""
    q, p = e["quality"], e.get("price") or {}
    if own_machine(q):  # on our machines (Ümit #4665 item 4): the estimate, its machine under it
        return own_cost_text(q, fmt(q.get("usd_per_1000"), 3))
    if p and p.get("input_per_mtok") is None:
        src = (f'; {esc(p["source"])}' if p.get("source") else "") + (f', read {esc(p["date"])}' if p.get("date") else "")
        return f'{nm("No price")}<span class="small">{esc(p["label"])}{src}</span>'
    if q.get("usd_per_1000") is None or not p:
        return cost_cell({"setups_meta": {}}, LATE_ENTRY, e["name"], q)[16:-5]
    tokens = f'${p["input_per_mtok"]} per million input tokens' + (
        f', ${p["output_per_mtok"]} per million output tokens' if p.get("output_per_mtok") else "")
    src = (f'; {esc(p["source"])}' if p.get("source") else "") + (f', read {esc(p["date"])}' if p.get("date") else "")
    billed = (f'<span class="small">{esc(p["billed_label"])}, ${p["billed_input_per_mtok"]} per million input tokens: '
              f'{fmt(e["usd_per_1000_billed"], 3)}</span>' if e.get("usd_per_1000_billed") is not None else "")
    return f'{fmt(q["usd_per_1000"], 3)}<span class="small">{esc(p["label"])}, {tokens}{src}</span>{billed}'


def late_cells(e) -> dict:
    """The late-entry numbers as cell contents, shared by the Leagues table and the setup's page."""
    import home
    q, r, x, route = e["quality"], e["risk"]["main"], e["exchanges"], e["route"]
    td = lambda cell: cell[16:-5]  # the contents of a <td class="num"> cell
    effort = "; ".join(f"{esc(k)} in {count(v)} of {count(x['with_exchanges'])} decisions" for k, v in x["efforts"].items())
    gone = e.get("not_played") or []
    return dict(
        entry=f'{esc(e["entry"][:10])}<span class="small">first match {esc(e["entry"][11:16])} UTC</span>',
        field=f'League {e["field_league"]} (original table)<span class="small">{count(e["total"])} setups</span>',
        played=(f'{count(e["played"])} / {count(e["total"])}'
                + (f'<span class="small">{count(e["running"])} running</span>' if e["running"] else "")
                + "".join(f'<span class="small">{esc(unplayed_text(g))}</span>' for g in gone)),
        record=(f'{count(e["record"]["won"])}\u2013{count(e["record"]["drawn"])}\u2013{count(e["record"]["lost"])}'
                f'<span class="small">won\u2013drawn\u2013lost</span>'),
        error=td(er_cell(q)), judgement=td(home.judgement_td(r)), ability=td(home.ability_td(r)),
        caution=td(home.caution_td(r)),
        best=pct(q["best_share"]) if q.get("best_share") is not None and not q.get("too_few") else nm(NA),
        time=secs(q.get("time_median")), cost=late_cost(e),
        invalid=f'{count(q["invalid"])}<span class="small">of {count(q["decisions"])} decisions</span>',
        cut=(f'{count(x["cut_off"])}<span class="small">{count(x["limit_sent"])} of {count(x["with_exchanges"])} '
             f'decisions sent an output limit; {count(x["past_limit_no_limit_sent"])} over '
             f'{count(x["output_limit"])} output tokens without one</span>'),
        route=(f'{esc(route["provider"] or NOT_MEASURED)}<span class="small">{esc(route["spec"] or "")} · effort '
               f'{effort or nm("not in the requests")}</span>'))


LATE_HEAD = ["Setup", "Entry date", "League field played", "Matches played", "Record (W\u2013D\u2013L)",
             "Error rate (PR), 95% interval", "Risk judgement, margin 0.001", "Ability d\u2032",
             "Caution c (+ cautious, \u2212 bold)", "Engine's best play", "Median s per decision",
             "$ per 1,000 decisions", "Invalid answers", "Cut off at the output limit", "Route and effort sent"]


LATE_RESULT = {1: "Won", 0: "Draw", -1: "Lost"}


def late_href(rel, e) -> str:
    return f"{rel}models/{LATE_ENTRY}/{e['slug']}/"


SUBQ_PREVIEW, SUBQ_11 = "SubQ Snap Preview", "SubQ Snap 1.1"
SUBQ_SELF = ("This pair may be SubQ Snap 1.1 against itself: under the 'subq-snap-preview' name the API returned answers "
             "identical to SubQ Snap 1.1 (1,000 identical paired positions: letters and probabilities).")
SUBQ_OTHER = ("The opponent was requested as SubQ Snap Preview; under that name the API returned answers identical to "
              "SubQ Snap 1.1 on 1,000 paired positions, so the opponent's model identity is not verified.")


def subq_note(entrant, opponent=None, tag="span") -> str:
    """Presentation only, no result changes. SubQ Snap 1.1's row and page, and its pair against SubQ Snap Preview: the
    pair may be 1.1 against itself; every other late-entry pair against SubQ Snap Preview: the opponent's model
    identity is not verified."""
    if (opponent is None or opponent == SUBQ_PREVIEW) and entrant == SUBQ_11:
        text = SUBQ_SELF
    elif opponent == SUBQ_PREVIEW:
        text = SUBQ_OTHER
    else:
        return ""
    return f'<{tag} class="small">{esc(text)}</{tag}>'


def late_results(e, rel) -> str:
    """A late entry's matches, one row per opponent in the order they started: score (its own first), result, match.
    A pair not played for a recorded reason (its stopped match, if any, included) shows the reason, no score."""
    gone = {g["opponent"]: g["reason"] for g in e.get("not_played") or []}
    rows = []
    for m in e["matches"]:
        done = m["status"] == "finished"
        if not done and m["opponent"] in gone:
            continue
        res = LATE_RESULT[(m["score_for"] > m["score_against"]) - (m["score_for"] < m["score_against"])] if done else None
        rows.append(f'<tr data-dataset="{LATE_ENTRY}"><td class="model"><span class="model-name">{esc(m["opponent"])}</span>'
                    f'{subq_note(e["name"], m["opponent"])}</td>'
                    f'<td class="num">{m["score_for"]}\u2013{m["score_against"]}</td>'
                    f'<td>{res or esc(MATCH_STATE.get(m["status"], m["status"]))}</td>'
                    f'<td class="num">' + (f'<a href="{rel}matches/#{match_anchor("v3", m["id"])}">{m["id"]}</a>' if done
                                           else str(m["id"])) + '</td>'
                    f'<td class="date">{(m["finished"] or "")[:10]}</td></tr>')
    for g in e.get("not_played") or []:
        why = (f'{esc(OUT_OF_SCOPE[0].upper() + OUT_OF_SCOPE[1:])}; not played ({esc(g["reason"])})' if g.get("out_of_scope")
               else f'Not played ({esc(g["reason"])})')
        rows.append(f'<tr data-dataset="{LATE_ENTRY}"><td class="model"><span class="model-name">{esc(g["opponent"])}</span></td>'
                    f'<td class="num">{nm("No score")}</td><td>{why}</td><td class="num">{nm(NA)}</td>'
                    f'<td class="date"></td></tr>')
    r = e["record"]
    scope = sum(bool(g.get("out_of_scope")) for g in e.get("not_played") or [])
    unplayed = "".join([f"; {count(scope)} {esc(OUT_OF_SCOPE)}, not played" if scope else "",
                        f"; {count(len(gone) - scope)} not played" if len(gone) > scope else ""])
    unplayed += ", not a loss" if gone else ""
    return (SWIPE + table(["Opponent", "Score", "Result", "#", "Finished"], rows,
                          f"{esc(e['name'])} against each opponent, its score first: {count(r['won'])} won, "
                          f"{count(r['drawn'])} drawn, {count(r['lost'])} lost{unplayed}; none counts in a standings table",
                          cls="board list", attrs=f' data-dataset="{LATE_ENTRY}"'))


def late_entries_section(S, rel) -> str:
    """The Late entries tab: every late entry in its own table, then each one's results per opponent; outside every
    league table and standings."""
    if not S["late_entries"]:
        return ""
    rows, results = [], []
    for e in S["late_entries"]:
        c = late_cells(e)
        rows.append(f'<tr data-dataset="{LATE_ENTRY}"><td class="model"><a class="model-name" href="{late_href(rel, e)}">'
                    f'{esc(e["name"])}</a><span class="small">{late_status(e)}</span>{subq_note(e["name"])}</td>'
                    f'<td class="date">{c["entry"]}</td>'
                    f'<td>{c["field"]}</td>'
                    + "".join(f'<td class="num"{own_cost_sort(e["quality"]) if k == "cost" else ""}>{c[k]}</td>'
                              for k in ("played", "record", "error", "judgement", "ability",
                                        "caution", "best", "time", "cost", "invalid", "cut"))
                    + f'<td>{c["route"]}</td></tr>')
        results.append(f'<h3 id="late-{e["slug"]}">{esc(e["name"])}: results per opponent</h3>' + late_results(e, rel))
    return (f'<section class="card" id="late-entries" data-dataset="{LATE_ENTRY}"><div class="section-head">'
            f'<h2>Late entries (not in standings)</h2></div>'
            + SWIPE + table(LATE_HEAD, rows, "Late entries: each one's own late-entry games; never ranked",
                            attrs=f' data-dataset="{LATE_ENTRY}"')
            + f'<p class="note">{esc(LATE_ABOUT)} {esc(LATE_RANKED)}</p>'
            + "".join(results)
            + f'<p class="table-note">{esc(LATE_METHOD)} Every match of every stage: <a href="{rel}matches/">Matches</a>.</p>'
              f'</section>')


def late_entry_page(S, e) -> str:
    """The page of a late entry: what it is, the same numbers as its Leagues row, and its matches."""
    rel = "../../../"
    c = late_cells(e)
    q = e["quality"]
    items = [("Late entry", f'{esc(LATE_ENTRY_LABEL)}: its games count in no standings table, no league table, no Hype '
                            f'Cup input and no other setup\'s numbers'),
             ("Entry date", c["entry"]), ("League field played", c["field"]), ("Matches played", c["played"]),
             ("Record", c["record"]), ("Error rate (PR), 95% interval", c["error"]),
             ("Decisions", f'{count(q["decisions"])} ({count(q["scored"])} scored)'),
             ("Risk judgement, margin 0.001", c["judgement"]), ("Ability d\u2032", c["ability"]),
             ("Caution c (+ cautious, \u2212 bold)", c["caution"]), ("Engine's best play", c["best"]),
             ("Median s per decision", c["time"]), ("$ per 1,000 decisions", c["cost"]),
             ("Invalid answers", c["invalid"]),
             ("Cut off at the output limit", c["cut"]), ("Route and effort sent", c["route"])]
    m = S["setups_meta"].get((LATE_ENTRY, e["name"]))
    setup = (f'<section class="card" id="setup"><h2>How we called it</h2>{facts(m, q)}</section>' if m else "")
    return (f'<section class="card"><p class="eyebrow">{esc(LATE_ENTRY_LABEL)} · League {e["field_league"]} field</p>'
            f'<h1>{esc(e["name"])}</h1><p class="subtitle">{late_status(e)}</p>{subq_note(e["name"], tag="p")}'
            f'<p class="version">{esc(version_line(S))}</p></section>'
            f'<section class="card" id="late-entry" data-dataset="{LATE_ENTRY}"><h2>{esc(LATE_ENTRY_LABEL)}</h2>'
            f'<dl class="facts">'
            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items)
            + f'</dl><p class="note">{esc(LATE_ABOUT)}</p><p class="table-note">{esc(LATE_METHOD)}</p>'
            f'<p><a href="{rel}leagues/#late-entries">Late entries on the Leagues page</a> · '
            f'<a href="{rel}data/v3/late-entries/{e["slug"]}.json">JSON</a></p></section>' + setup
            + f'<section class="card" id="late-entry-matches"><h2>Matches</h2>' + late_results(e, rel) + "</section>")


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
        risk_ph = ""
        if lg:
            rows = []
            for n in by_error(setups):
                cells = ""
                for p in A.PHASES:
                    r = setups[n]["risk"]["main"]["phases"][p]
                    v = r["judgement"]
                    cells += (f'<td class="num heat" style="--heat:{(v or 0) / 100:.2f}">{fmt(v) if v is not None else nm(NA)}'
                              f'<span class="small">{fmt(r["trade_off"], 0)} with a trade-off</span></td>')
                rows.append(tr(S, ds, n, cells, rel))
            risk_ph = (f'<h3 id="{ds}-risk-phase">Risk judgement per phase</h3>' + SWIPE
                       + table(["Model and setting"] + [PHASE_LABEL[p] for p in A.PHASES], rows,
                               "Risk judgement (margin 0.001) per game phase; N/A where a phase has no Risk pays or no "
                               "Safety pays decisions", attrs=f' data-dataset="{ds}" data-margin="0.001"')
                       + f'<p class="table-note">{esc(RISK_LIMIT)}</p>')
        badge = league_status_text(lg) if lg else status_badge(EARLIER)
        body = (risk_ph + f'<h3 id="{ds}-phase">Game phase</h3>' + phase_table(S, rel, ds, setups)
                + f'<h3 id="{ds}-tag">Strategy tag (contact and holding positions after the opening)</h3>'
                + phase_table(S, rel, ds, setups, "tags", A.TAGS, "Error rate (PR) per strategy tag")
                + f'<h3 id="{ds}-options">Number of legal plays</h3>'
                + phase_table(S, rel, ds, setups, "options", A.OPTION_LABELS, "Error rate (PR) by number of legal plays")
                + f'<h3 id="{ds}-gap">Equity gap between the two best plays</h3>'
                + phase_table(S, rel, ds, setups, "gaps", A.GAP_LABELS, "Error rate (PR) by the gap between the two best plays"))
        note = f'<p class="table-note">{esc(play_order_note(S))}</p>' if not lg else ""
        version = "" if lg else ' data-version="v1"'
        out.append(f'<section class="card" id="{ds}" data-dataset="{ds}"{version}><div class="section-head"><h2>{esc(title)}</h2>'
                   f'{badge}</div>{body}{note}</section>')
    out.append(about("<p>Error rate by game phase, strategy tag, number of legal plays and the equity gap between the "
                     "two best plays. Each league on its own; the shared-position version waits for the answers. A cell "
                     "with fewer decisions than the minimum shows the status instead of a value.</p>", "About these tables"))
    return "".join(out)


# --- Models -------------------------------------------------------------------------------------------------

# Parameter counts (Ümit #3465): only as the maker documents them (content/model_params.json: total, active for a
# mixture of experts, effective where the maker gives one, in billions as shown, the source URL and read date); never
# an estimate.
# Keyed by the shown model name (common.relabel, labels.json "models"), as the rendered state names models.
PARAMS = relabel(json.loads((CONTENT_DIR / "model_params.json").read_text())["models"])
# List prices (Ümit #4217, #4238, #4245): for every model whose maker states no total parameter count (closed models,
# and open models without a maker's total), the maker's standard price per 1M input tokens, its URL and read date
# (content/model_prices.json); never an estimate.
PRICES = relabel(json.loads((CONTENT_DIR / "model_prices.json").read_text())["models"])
# Model classes (Ümit #4245, #4259; one scale for the three sites): (key, label). Undisclosed: neither the maker's size
# nor a per-token list price (a chat model always has one, so never; a decision model with a per-request price or
# none). Programs are in no class.
CLASSES = (("tiny", "Tiny"), ("small", "Small"), ("medium", "Medium"), ("large", "Large"),
           ("efficient", "Efficient"), ("workhorse", "Workhorse"), ("flagship", "Flagship"),
           ("undisclosed", "Undisclosed"))
CLASS_LABEL = dict(CLASSES)
# The rule shown under the Class row and on About, word for word (Ümit #4245).
CLASS_RULE = ("Size by total parameters, as disclosed by the maker (for MoE models the label also shows active "
              "parameters): Tiny under 6B · Small 6B–15B · Medium over 15B up to 40B · Large over 40B. Models of "
              "undisclosed size, by standard list price per 1M input tokens: Efficient up to $0.50 · Workhorse up to "
              "$3 · Flagship over $3.")


def billions(b: float) -> str:
    """A count in billions as shown: 31 -> '31B', 30.7 -> '30.7B', 2800 -> '2.8T'."""
    return f"{b / 1000:g}T" if b >= 1000 else f"{b:g}B"


def params_html(model: str) -> str:
    """The box's parameter count: '31B dense', '24B MoE · 2.45B active', '753.33B MoE; active not disclosed by maker' (a
    mixture of experts whose maker gives no active count), '4B effective (8B total)', or the maker card's own terms
    where it gives parts but no whole-model total ('terms'; total_b null, so never a Small model); a disclosed count
    linked to its source (as the box's Released month is); else 'not disclosed by maker'. A model the file does not
    list: KeyError."""
    p = PARAMS[model]
    total = p["total_b"]
    if p.get("terms"):
        kind = "MoE" if p["moe"] else "dense"
        return f'<a href="{esc(p["source"])}">{esc(p["terms"])}</a> · {kind}'
    if total is None:
        return "not disclosed by maker"
    if p["effective_b"] is not None:
        text = f'{billions(total)} {"MoE" if p["moe"] else "dense"} · {billions(p["effective_b"])} effective'
    elif p["active_b"] is not None:
        text = f'{billions(total)} MoE · {billions(p["active_b"])} active'
    elif p["moe"]:
        text = f'{billions(total)} MoE; active not disclosed by maker'
    else:
        text = f'{billions(total)} dense'  # dense or MoE stated for every disclosed size (Ümit via Zeki #4183)
    return f'<a href="{esc(p["source"])}">{esc(text)}</a>'


def _by_total(b: float) -> str:
    return "tiny" if b < 6 else "small" if b <= 15 else "medium" if b <= 40 else "large"


def model_class(model: str) -> str | None:
    """The model's class key (CLASSES; Ümit #4245): by the total the MAKER states (card_total_b: tiny < 6B, small 6B to
    15B, medium over 15B to 40B, large over 40B; not our checkpoint count total_b); REAX 1.3, two models run together
    whose card states no total (card_parts_b), by its total in all (total_b, 57.36B, the figure logic's live site uses,
    #4253); any other model by its standard list price (PRICES: efficient <= $0.50, workhorse over $0.50 to $3,
    flagship over $3); undisclosed where it has neither a maker's size nor a per-token list price (#4259); an open model
    whose card states no total but whose released files are counted (class_from_files, GLM-5.3: turkce #4406, Zeki
    #4409/#4412) by that count (total_b). A model the parameter file does not list: KeyError."""
    p = PARAMS[model]
    if p["card_total_b"] is not None:
        return _by_total(p["card_total_b"])
    if p.get("card_parts_b") or p.get("class_from_files"):
        return _by_total(p["total_b"])
    price = PRICES[model]["input_per_mtok"]
    if price is None:
        return "undisclosed"  # Ümit #4259: neither size nor a per-token list price
    return "efficient" if price <= 0.5 else "workhorse" if price <= 3 else "flagship"


def _short(b: float) -> str:
    """A count in billions for the label after a name (turkce #4231, #4237, the three sites' format): trillions to one
    decimal from 1,000B ('2.8T'), whole from 10B ('26B', '276B'), one decimal under 10B ('7.9B', '9.0B', '4.0B'; logic
    #4361, as on Reading)."""
    return f"{b / 1000:.1f}T" if b >= 1000 else f"{round(b)}B" if b >= 10 else f"{b:.1f}B"


# Each model's weights as setups.json records them (shown model name -> the set of its setups' "weights" values).
_SETUP_WEIGHTS: dict[str, set] = {}
for _s in relabel(json.loads((CONTENT_DIR / "setups.json").read_text())["setups"]):
    _SETUP_WEIGHTS.setdefault(_s["model"], set()).add(_s.get("weights"))


def weights(model: str) -> str | None:
    """'open' or 'closed' (Ümit #4445: the class label starts with it): the shared names file's "open" (by model key),
    else the price file's "weights", else the one value every setups.json entry of the model records; None where none
    of them says (never guessed: Zeki #4448)."""
    e = SHARED_NAMES.get(model_key(model))
    if e and isinstance(e.get("open"), bool):
        return "open" if e["open"] else "closed"
    if model in PRICES and PRICES[model].get("weights") in ("open", "closed"):
        return PRICES[model]["weights"]
    rec = _SETUP_WEIGHTS.get(model, set())
    return next(iter(rec)) if len(rec) == 1 and rec <= {"open", "closed"} else None


def class_label(model: str) -> str:
    """The short plain-text label after a row's name (Ümit #4245, #4254, #4269, #4445; turkce #4263/#4266/#4268): Open
    or Closed (weights; left out where no source says), then the maker's total, a dense model the number only
    ('Open · 31B'), a mixture of experts with its active count ('Open · 309B MoE · 15B active'; '753B MoE' without one);
    REAX 1.3 its total only ('Open · 57B'; its two parts are explained in the details box); a model of undisclosed size
    its price class: 'Closed · Workhorse', 'Open · Workhorse' (open weights, no stated size), '(provisional)' on an
    introductory-only price. The details box gives the exact counts and the price."""
    p = PARAMS[model]
    if p["card_total_b"] is not None:
        active = f' \u00b7 {_short(p["card_active_b"])} active' if p["moe"] and p["card_active_b"] is not None else ""
        body = f'{_short(p["card_total_b"])}{" MoE" if p["moe"] else ""}{active}'
    elif p.get("card_parts_b"):
        body = _short(p["total_b"])
    elif p.get("class_from_files"):  # an open model whose card states no total: sized by its released files (#4406)
        body = f'{_short(p["total_b"])} MoE' if p["moe"] else _short(p["total_b"])
    else:
        body = CLASS_LABEL[model_class(model)] + (" (provisional)" if PRICES[model]["provisional"] else "")
    head = {"open": "Open", "closed": "Closed"}.get(weights(model))
    return f"{head} \u00b7 {body}" if head else body


def class_note(model: str) -> str | None:
    """The details box's line on the model's size or price class (Ümit #4229, #4245), plain text: the maker's figure
    the class uses and our checkpoint count ('Mixture of experts: 35B total, about 3B active per step (the maker's
    figures); our checkpoint count 35.11B.'); REAX 1.3 its two parts (model card and reax-engine @ ff8f595
    reax13/probabilities.py: every request to both parts, per-option probabilities 0.5*G + 0.5*Q); an open model whose
    maker states no count, that; an introductory-only price, why its class is provisional (#4238); else None."""
    p = PARAMS[model]
    ours = (f'; our checkpoint count {billions(p["total_b"])}'
            if p["total_b"] is not None and p["total_b"] != p["card_total_b"] else "")
    if p["card_total_b"] is not None:
        if p["moe"]:
            split = f', {p["card_active_terms"]}' if p.get("card_active_terms") else ""
            active = (f'about {billions(p["card_active_b"])} active per step{split}' if p["card_active_b"] is not None
                      else "active count not disclosed by the maker")
            return f'Mixture of experts: {billions(p["card_total_b"])} total, {active} (the maker\'s figures){ours}.'
        return f'Size class by the maker\'s figure, {billions(p["card_total_b"])}{ours}.'
    if p.get("class_from_files"):
        return p["class_from_files"]
    if p.get("card_parts_b"):
        return (f'Two models run together, option probabilities averaged 50/50: {billions(p["total_b"])} in all, all '
                'used on every question.')
    if model in PRICES:
        head = "Closed" if PRICES[model]["weights"] == "closed" else "Open, size not stated by the maker"
        kind = "introductory price, the only one published" if PRICES[model]["provisional"] else "standard list price"
        price = f'${PRICES[model]["input_per_mtok"]:g} per 1M input tokens, {kind}'
        prov = (f'; class provisional: {PRICES[model]["provisional_reason"].rstrip(".")}'
                if PRICES[model]["provisional"] else "")
        return f'{head} · {CLASS_LABEL[model_class(model)]} ({price}){prov}{ours}.'
    return None


def class_keys(cls: str) -> str:
    """The Class row under a table's type keys (Ümit #4217, #4245): All · Tiny · Small · Medium · Large · Efficient ·
    Workhorse · Flagship (data-class-key; the page's script hides a key with no model in the type in view), and the
    rule (CLASS_RULE) under it; cls: the row's classes."""
    return (f'<div class="keys class-keys needs-js {cls}" role="group" aria-label="Class"><span class="class-keys-label">'
            'Class:</span>' + "".join(f'<button type="button" class="key" data-class-key="{k}" aria-pressed='
                                      f'"{str(k == "all").lower()}">{l}</button>'
                                      for k, l in (("all", "All"),) + CLASSES)
            + '</div>' + star_note("Class: by the maker's total parameters, or by list price when the size is "
                                   "undisclosed", f'<p>{esc(CLASS_RULE)}</p>', "table-note class-note"))


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
            v = (f"{tokens}; {v['label']}" + (f"; source {v['source']}" if v.get("source") else "")
                 + f"; price date {v.get('date') or 'not recorded'}"
                 + (f"; {v['billed_label']}: ${v['billed_input_per_mtok']} per million input tokens"
                    if v.get("billed_input_per_mtok") is not None else ""))
        if k == "date_run" and not v and q and q.get("first_date"):
            v = q["first_date"] if q["first_date"] == q["last_date"] else f"{q['first_date']} to {q['last_date']}"
        if k == "option_groups" and q is not None:
            seen = (f"; in this data {count(q['grouped'])} decisions were split into groups of "
                    f"{', '.join(str(g) for g in q['group_sizes'])}" if q.get("grouped") else "; no decision in this data was split")
            v = (v or "not recorded") + seen
        out.append(f"<dt>{label}</dt><dd>{esc(v) if v else nm('Missing')}</dd>")
    if m.get("play_order"):
        out.append(f"<dt>Play order</dt><dd>{esc(m['play_order'])}</dd>")
    if m.get("aliases") and effort_aliases(m["name"]):
        out.append(f"<dt>Earlier name</dt><dd>{esc(', '.join(effort_aliases(m['name'])))} (renamed on 28 Oct 2026 to the reasoning "
                   f"effort its requests sent)</dd>")
    if m.get("dataset", "").startswith("league-") and NAME_NOTES.get(m.get("name")):
        out.append(f"<dt>Reasoning, from the logs</dt><dd>{esc(NAME_NOTES[m['name']])}</dd>")
    return f'<dl class="facts">{"".join(out)}</dl>'


# --- Close choices (Method spec 2026-10-24 §9), shared by the Confidence tab and the model pages -------------

CC_MARGIN = {"main": "0.001", "robust": "0.02"}
CC_NA = "no full probability distribution"
SMALL_MARK = ", under 200 decisions"
# Probability audit (2026-10-24): League 2's complete letter-readout records are mostly positions with few options.
SUBSET_DATASETS = {"league-2"}
SUBSET_NOTE = "League 2: complete letter-readout records are mostly few-option positions, a selected subset."


def subset_note(dataset: str) -> str:
    """The selected-subset caveat beside every result built on League 2's complete probability records."""
    return f'<p class="note subset-note"><strong>{esc(SUBSET_NOTE)}</strong></p>' if dataset in SUBSET_DATASETS else ""


def cc_text(s: dict) -> str:
    """A share as text: 'x% (n / den)', marked when the denominator is under the site's minimum."""
    if not s["den"]:
        return f"{NA} (0 / 0)"
    return f'{pct(s["share"])} ({count(s["n"])} / {count(s["den"])}){SMALL_MARK if s["small"] else ""}'


def cc_td(s: dict) -> str:
    if not s["den"]:
        return f'<td class="num">{nm(NA)}<span class="small">0 / 0</span></td>'
    return (f'<td class="num">{pct(s["share"])}<span class="small">{count(s["n"])} / {count(s["den"])}'
            f'{SMALL_MARK if s["small"] else ""}</span></td>')


def cc_rate(x) -> str:
    return nm(NA) if x is None else pct(x)


def cc_diff(m: dict, k: str) -> str:
    v = m.get(k)
    if v is None:
        return nm(m.get(f"{k}_na") or NA)
    out = f"{fmt(100 * v, 1, True)} points"
    if m.get(f"{k}_lo") is not None:
        out += f'<span class="small">95% interval {fmt(100 * m[k + "_lo"], 1, True)} to {fmt(100 * m[k + "_hi"], 1, True)}</span>'
    return out


def close_engine_table(c: dict) -> str:
    rows = []
    for g, lab in (("close", "Close choices"), ("other", "Other decisions")):
        x = c["groups"][g]
        v = lambda k: (nm(NA) if not x["n"] else f'{eq(x[k]["mean"])}<span class="small">median {eq(x[k]["median"])}</span>')
        rows.append(f'<tr><th scope="row">{lab}</th><td class="num">{count(x["n"])}</td><td class="num">{v("gap")}</td>'
                    f'<td class="num">{v("loss1")}</td><td class="num">{v("loss2")}</td></tr>')
    return table(["Decisions", "Number", "Gap between the two plays' values", "Most likely play: behind the engine's best",
                    "Second most likely play: behind the engine's best"], rows,
                   "Engine values (GNUbg 2-ply, equity), mean with median", cls="board list")


def close_missed_table(c: dict) -> str:
    rows = []
    for mk in ("main", "robust"):
        m = c["margins"][mk]["missed"]
        lab = f'<th scope="row">margin {CC_MARGIN[mk]}<span class="small">{count(m["group"])} decisions</span></th>'
        if m.get("na"):
            rows.append(f'<tr>{lab}<td class="num">{cc_rate(None)}<span class="small">{esc(cc_text(m["close"]))}</span></td>'
                        f'<td class="num">{cc_rate(m["other"]["share"])}<span class="small">{esc(cc_text(m["other"]))}</span></td>'
                        f'<td class="num">{nm(m["na"])}</td><td class="num">{nm(NA)}</td></tr>')
            continue
        rows.append(f'<tr>{lab}<td class="num">{cc_rate(m["adj_close"])}<span class="small">crude {esc(cc_text(m["close"]))}</span></td>'
                    f'<td class="num">{cc_rate(m["adj_other"])}<span class="small">crude {esc(cc_text(m["other"]))}</span></td>'
                    f'<td class="num">{cc_diff(m, "adjusted")}</td><td class="num">{cc_diff(m, "crude")}</td></tr>')
    return table(["Margin", "Close choices: missed risks", "Other decisions: missed risks (weighted to the close choices' mix)",
                    "Difference, close minus other", "Crude difference"], rows,
                   "Missed risks where the risk is worth taking, close choices vs other decisions", cls="board list")


def close_risk_table(c: dict) -> str:
    rows = []
    for mk in ("main", "robust"):
        k = c["margins"][mk]["classes"]
        rows.append(f'<tr><th scope="row">margin {CC_MARGIN[mk]}</th>' + cc_td(k["risk"]["risk_close"])
                    + cc_td(k["safety"]["risk_close"]) + "</tr>")
    return table(["Margin", "In Risk pays positions", "In Safety pays positions"], rows,
                   "Close choices between a safe play and a riskier one, by position class", cls="board list")


CC_EXCLUSION = {"invalid": "invalid answers", "grouped": "asked in groups of options",
                "sparse": "incomplete distribution (an option without its own probability)",
                "unverified": "stored probabilities not reproduced from the raw response", "no_raw": "no raw response",
                "not_audited": "not audited", "not_scored": "no engine value",
                "no_probabilities": "one letter only, or a program"}
CC_FEATURES = [("hitting", "Hitting rolls"), ("points", "Newly made points"), ("race", "Pip counts"),
               ("prime", "Longest prime")]


def close_section(S, dataset: str, name: str, c: dict, rel: str) -> str:
    """The model page's full close-choice breakdown (Method spec 2026-10-24 §9)."""
    spec = S["close_spec"]
    ex = "; ".join(f"{CC_EXCLUSION[k]} {count(v)}" for k, v in c["exclusions"].items()) or "none"
    head = (f'<section class="card" id="close-choices"><h2>Close choices</h2><p>{esc(spec["definition"])}</p>'
            f'<p class="table-note">{esc(spec["label"])} <a href="{rel}method/#close-choices">Method</a></p>'
            + subset_note(dataset))
    facts_ = [("Decisions", count(c["decisions"])), ("Eligible (full probability distribution)", count(c["eligible"])),
              ("Left out, by reason", esc(ex))]
    if c["na"]:
        facts_.append(("Close choices", nm(NA) + " " + esc(CC_NA)))
        return head + '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts_) + "</dl></section>"
    t = c["ties"]
    facts_ += [("Close choices", esc(cc_text(c["close"]))),
               ("Ties in the top two", f'{count(t["top_two"])} decisions ({count(t["positive"])} at a positive probability, '
                                       f'{count(t["zero"])} at 0; the two most likely plays tied: {count(t["order"])}, the '
                                       f'second tied with the third: {count(t["member"])}); {count(t["close"])} of them '
                                       f'close choices. Ties are broken by the order the plays were shown, never by the engine.'),
               ("Between a safe play and a riskier one", esc(cc_text(c["risk_close"])) + " of the close choices; "
                + esc(cc_text(c["risk_close_of_eligible"])) + " of all eligible decisions")]
    out = [head, '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts_) + "</dl>"]
    G = c["groups"]
    st = lambda x, k: (nm(NA) if not x["n"] else f'{fmt(x[k]["mean"], 3)}<span class="small">median {fmt(x[k]["median"], 3)}</span>')
    rows = [f'<tr><th scope="row">{lab}</th><td class="num">{count(G[g]["n"])}</td><td class="num">{st(G[g], "p1")}</td>'
            f'<td class="num">{st(G[g], "p2")}</td><td class="num">{st(G[g], "psum")}</td></tr>'
            for g, lab in (("close", "Close choices"), ("other", "Other decisions"))]
    out.append(table(["Decisions", "Number", "p1 (most likely play)", "p2 (second)", "p1 + p2"], rows,
                     "Probabilities of the two most likely plays, mean with median", cls="board list"))
    bins = [f"{b / 10:.1f}\u2013{(b + 1) / 10:.1f}" for b in range(10)]
    rows = [f'<tr><th scope="row">{lab}</th>' + "".join(f'<td class="num">{count(v)}</td>' for v in G[g]["psum_bins"]) + "</tr>"
            for g, lab in (("close", "Close choices"), ("other", "Other decisions"))]
    out.append(table(["p1 + p2"] + bins, rows, "How much probability the two plays hold together: decisions per bin",
                     cls="board list"))
    rows = [f'<tr><th scope="row">{lab}</th><td class="num">{count(G[g]["n"])}</td>'
            + "".join(cc_td(G[g]["differ"][f]) for f, _ in CC_FEATURES)
            + f'<td class="num">{" / ".join(count(x) for x in G[g]["by_count"])}</td></tr>'
            for g, lab in (("close", "Close choices"), ("other", "Other decisions"))]
    out.append(table(["Decisions", "Number"] + [l for _, l in CC_FEATURES] + ["None / 1 / 2 / 3 / 4 differ"], rows,
                     "What differs between the two most likely plays (several can differ; none is picked as the cause)",
                     cls="board list"))
    out.append(close_engine_table(c))
    out.append(close_risk_table(c))
    rows = []
    for mk in ("main", "robust"):
        m = c["margins"][mk]
        k = m["classes"]
        rows.append(f'<tr><th scope="row">margin {CC_MARGIN[mk]}</th>' + cc_td(k["risk"]["close"]) + cc_td(k["safety"]["close"])
                    + cc_td(k["none"]["close"]) + "".join(cc_td(m["stake"][b]) for b in A.BANDS) + "</tr>")
    out.append(table(["Margin", "Risk pays", "Safety pays", "No trade-off", "Risk pays, small stake",
                      "Risk pays, medium stake", "Risk pays, big stake"], rows,
                     "Close choices among eligible decisions, by position class and stake band", cls="board list"))
    out.append('<p class="table-note">At the 0.02 margin a Risk pays position has a stake of at least 0.02, so the small '
               'band is empty. A big stake means playing safe costs more by the engine\'s value, not that the decision '
               'was harder.</p>')
    out.append(close_missed_table(c))
    out.append(f'<p class="table-note">{esc(spec["label"])} <a href="{rel}decisions/?d={dataset}&amp;s={meta(S, dataset, name)["slug"]}'
               f'&amp;k=close">Every close choice of this setup</a></p></section>')
    return "".join(out)


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
        for mk, label in (("main", "0.001"), ("robust", "0.02")):
            r = entry["risk"][mk]
            share = lambda s: f"{pct(s['share'])} ({fmt(s['n'], 0)} / {fmt(s['den'], 0)})" if s["den"] else "0 / 0"
            j = (f"{fmt(r['judgement'])} (95% interval {fmt(r['judgement_lo'])} to {fmt(r['judgement_hi'])})"
                 if r["judgement"] is not None else r["judgement_na"])
            cells += (f"<dt>Risk judgement, margin {label}</dt><dd>{esc(j)}; risks found {share(r['found'])}, right safety "
                      f"{share(r['right_safety'])}</dd>")
        r = entry["risk"]["main"]
        cells += f"<dt>No trade-off</dt><dd>{count(int(r['no_trade_off']))} (left out of every risk metric)</dd>"
        note = f'<p class="note">{esc(play_order_note(S))}</p>' if dataset == "v1-set" else ""
        parts.append(f'<section class="card" id="results"><h2>Results in {esc(where)}</h2>{note}<dl class="facts">{cells}</dl>'
                     f'<p><a href="{rel}decisions/?d={dataset}&amp;s={m["slug"] if dataset != "v1-set" else slug(name)}">Every decision of this setup</a> · '
                     f'<a href="{rel}data/{"v1/v1-set" if dataset == "v1-set" else "v3/" + dataset}/{setup_slug(dataset, name)}.json">JSON</a></p></section>')
        if r["trade_off"]:
            top = max(r["calls"].values()) or 1
            bars = "".join(f'<div class="cc-row"><span class="cc-l">{esc(lab)}</span><span class="cc-bar {cls}" '
                           f'style="width:{60 * r["calls"][k] / top:.1f}%"></span><span class="cc-n">{fmt(r["calls"][k], 0)}</span></div>'
                           for k, lab, cls in (("right_risk", "right risks", "sp-right"), ("wrong_risk", "wrong risks", "sp-wrong"),
                                               ("needless", "needless risks", "sp-needless"), ("missed", "missed risks", "sp-missed"),
                                               ("right_safety", "right safety", "sp-safety")))
            big = esc(fmt(r["judgement"]) if r["judgement"] is not None else r["judgement_na"])
            parts.append(f'<section class="card risk-card" id="risk-calls"><h2>Risk call card</h2><p class="cc-big">{big}'
                         f'<span class="small">risk judgement, margin 0.001</span></p>{bars}'
                         f'<p class="table-note">{esc(RISK_LIMIT)}</p></section>')
        if entry.get("close") is not None:
            parts.append(close_section(S, dataset, name, entry["close"], rel))
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
              + star_note(esc(EARLIER_NOTE), f'<p>{esc(play_order_shuffled(S))}</p>') +
              f'<div class="compare-pick needs-js"><label>First <select data-compare="a">{opts}</select></label>'
              f'<label>Second <select data-compare="b">{opts}</select></label></div>'
              f'<div data-compare-out aria-live="polite"></div>'
              f'<noscript><p>The comparison needs JavaScript; the numbers are in <a href="../data/v1/compare.json">compare.json</a>.</p></noscript>'
              f'</section>')


def vision_page(S) -> str:
    return (page_head(S, "Vision", "Vision")
            + '<section class="card" id="vision"><p>No vision runs yet: every model here reads the board as text '
              '(points, dice and legal plays), never a picture of the board.</p>'
              '<p><a href="../">See the text results \u2192</a></p></section>')


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
            + '<section class="card" id="smoke">' + SWIPE
            + table(head, rows, "Smoke tests: the same 50 positions for every setup, with the v3 prompt and shuffled plays")
            + '<p class="note"><strong>50 positions each, outside the shared sets. Error rates are rough '
              '(about \u00b110 to \u00b125): enough to spot a clearly weak model, not to rank models.</strong> This page feeds no '
              'ranking, chart or finding. Sorted by name. '
              'Every value is shown with its count and interval: the minimum-sample rule of the other pages '
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


# The Data page's downloads and how-to-recompute text, also on the About page (both pages are one level down, so the
# links are the same).
DOWNLOADS = ('<p class="hero-links"><a class="key" href="../data/results.json" download="results.json">results.json</a> '
             '<a class="key" href="../decisions/index.json" download="decisions.json">decisions.json</a> '
             '<a class="key" href="../new-models/">New models: first look</a> <a class="key" href="../models/">Every model setup</a></p>'
             '<p>results.json: every league\'s results per setup, one league per key, every risk metric at both margins. '
             'decisions.json: the index of every decision file, one gzip JSON file per setup and page of 50 decisions, '
             'with the board, the plays as shown, the engine\'s equities, the model\'s choice and its position class, '
             'stake and risk call.</p>')


def recompute(thresholds_href: str) -> str:
    return ('<ol>'
            '<li>Snapshot the league database: <code>python3 tools/site/snapshot.py v3.db STATE</code> (one read transaction; the prompts each model was sent go to <code>STATE/prompts.db</code>; the Nackgammon knockout\'s matches, from <code>knockout-nack.db</code> next to it, to <code>STATE/knockout.db</code>).</li>'
            '<li>Score every legal play of every decision with GNUbg 1.08 at 2-ply: <code>tools/site/score.sh STATE/snap.db STATE/plays</code>.</li>'
            '<li>Build and check the site: <code>python3 tools/site/build.py --state STATE --out OUT</code>. The build fails, and nothing is deployed, if a number does not trace to a data file, counts do not add up, leagues or versions mix, a published finding no longer holds, or a file contains a private address or credential.</li>'
            f'</ol><p>The scripts are in the jevgammon repository under <code>tools/site/</code>; the fixed thresholds are in <a href="{thresholds_href}">thresholds.json</a>.</p>')


def data_page(S, out: Path) -> str:
    man = json.loads((out / "data/manifest.json").read_text())
    rows = "".join(f'<tr><td><a href="../{esc(f["path"])}">{esc(f["path"])}</a></td><td class="num">{count(f["bytes"])}</td>'
                   f'<td><code>{f["sha256"][:12]}</code></td></tr>' for f in man["files"])
    return (page_head(S, "Data", "Data, versions and how to recompute")
            + f'<section class="card" id="downloads"><h2>Downloads</h2>{DOWNLOADS}'
              + SWIPE + table(["File", "Bytes", "sha256"], [rows], "Data files of this build", cls="board list")
              + f'<p class="table-note">Data files are split per version, league and model, '
              f'so each loads on a phone. Every number on the site is in one of them. The decision files behind '
              f'<a href="../decisions/">Every decision</a> are under <code>decisions/</code> ({count(S["decision_files"])} files, gzip-compressed JSON).</p></section>'
            + f'<section class="card" id="status"><h2>Analysis status</h2>{status_list(S)}</section>'
            + '<section class="card" id="versions"><h2>Versions</h2><dl class="facts">'
              '<dt>v3</dt><dd>Prompt bg-v2, plays in a seeded random order, invalid answers not retried. Leagues 1 to 3 and the shared positions.</dd>'
              f'<dt>v1</dt><dd>{status_badge(EARLIER)} Earlier prompt; plays listed in the runner\'s order. The v1 set of 1,000 positions answered by the v1 setups. Never in a v3 table or chart.</dd>'
              '<dt>Smoke tests</dt><dd>50 positions outside the shared sets, v3 prompt; only on New models: first look.</dd></dl></section>'
            + f'<section class="card" id="recompute"><h2>How to recompute</h2>{recompute("thresholds.json")}</section>')


def more_pages(rel: str, label: str = "More pages") -> str:
    """The pages that are not tabs (MORE_PAGES), as the in-page link keys: linked from the Leaderboard and About."""
    return (f'<nav class="face-nav more-pages" aria-label="{esc(label)}"><span class="view-label">{esc(label)}</span>'
            + "".join(f'<a href="{rel}{href}">{esc(text)}</a>' for href, text in MORE_PAGES) + '</nav>')


# --- Highlights, Experiments, About (Ümit #2901) --------------------------------------------------------------------

# Highlights (Ümit #2938 item 4): decision slots, each one decision (board, the model's play, the engine's play) and its
# short story; content/highlights.json names them. A slot's decision is read from the Every decision export and its
# stated facts (content/highlights.json "facts") must be the exported decision's, or the build fails; its story comes
# from Ümit / Claude, until then it is marked Story coming. Under the slots, four finding cards (highlight_cards.py,
# Ümit #4178), each number checked against the built site.
HIGHLIGHTS = json.loads((CONTENT_DIR / "highlights.json").read_text())["slots"]
STORY_COMING = "Story coming"


def exported_decision(out: Path, dataset: str, slug: str, did: int) -> tuple[dict, int]:
    """(the decision as exported, its page number) from decisions/<dataset>/<slug>/<page>.json.gz."""
    import gzip
    files = [p for p in (out / "decisions" / dataset / slug).glob("*.json.gz") if re.fullmatch(r"\d+\.json\.gz", p.name)]
    for p in sorted(files, key=lambda p: int(p.name.split(".")[0])):
        for d in json.loads(gzip.decompress(p.read_bytes()))["decisions"]:
            if d["id"] == did:
                return d, int(p.name.split(".")[0])
    raise ValueError(f"content/highlights.json: decision {did} is not in the {dataset}/{slug} export")


def highlight_slot(S, out: Path, i: int, h: dict) -> str:
    head = f'<section class="card highlight-slot" id="highlight-{i}"'
    coming = f'<p class="note">{status_badge(STORY_COMING)} The story will be added here.</p>'
    from board import board_svg
    d, page = exported_decision(out, h["dataset"], h["setup"], h["decision"])
    me, best = d["plays"][d["chosen"]], d["plays"][d["best"]]
    f = h["facts"]
    shown = dict(model_play=me["notation"], model_hitting_rolls=me["hitting_rolls"], best_play=best["notation"],
                 best_hitting_rolls=best["hitting_rolls"], equity_difference=round(best["equity"] - me["equity"], 4))
    if shown != f:
        raise ValueError(f"content/highlights.json slot {i}: stated facts {f} are not the exported decision's {shown}")
    svg = board_svg(d["board"], d["dice"], d["pips"], play=best["notation"], alt=me["notation"], cls="bd hl-board",
                    label_extra=f"Solid arrows: the engine's best play, {best['notation']}. Dashed: the model's play, "
                                f"{me['notation']}.")
    href = f'../decisions/?d={h["dataset"]}&amp;s={h["setup"]}&amp;p={page}#d{h["decision"]}'
    shot = lambda n: f"the opponent hits with {count(n)} of 36 rolls"  # noqa: E731  (Every decision's wording)
    facts = (f'<dl class="facts"><dt>Dice</dt><dd>{d["dice"][0]}-{d["dice"][1]}</dd>'
             f'<dt>The model played</dt><dd><code>{esc(me["notation"])}</code>: {shot(me["hitting_rolls"])}</dd>'
             f'<dt>The engine\'s best play</dt><dd><code>{esc(best["notation"])}</code>: {shot(best["hitting_rolls"])}, '
             f'worth {fmt(f["equity_difference"], 3)} more in equity (GNU Backgammon 2-ply)</dd></dl>')
    return (f'{head} data-slot="filled"><h2>{esc(h["title"])}</h2><div class="highlight-body">'
            f'<figure class="hero-board">{svg}</figure><div>{facts}{coming}'
            f'<p><a href="{href}">This decision</a></p></div></div></section>')


def highlights_page(S, out: Path) -> str:
    import highlight_cards as HC
    slots = "".join(highlight_slot(S, out, i, h) for i, h in enumerate(HIGHLIGHTS, 1))
    slots += "".join(HC.card_html(c, status_badge) for c in HC.cards(S))
    return (page_head(S, "Highlights", "Highlights", "A single decision with the board, the model's play and the "
                      "engine's play, then findings the site already shows, each with its numbers and the page it "
                      'comes from. Every decision is on <a href="../decisions/">Decisions</a>.')
            + f'<div class="highlight-slots">{slots}</div>')


def experiments_page(S) -> str:
    """One compact card per experiment (Ümit #4388, #4390). Status words: 'Completed', 'In progress' or 'Paused', from
    the data. 'Learning' is the every-model study (/improve/), its status and counts from the same validated data as
    that page (the build fails without it); the finished one-model pilot (/learning/) is its own small card."""
    import improve_page
    import learning_page
    I = S.get("improve")
    if not I or not I.get("plan"):
        raise SystemExit("experiments page: improve data missing")
    st = improve_page.status(I)
    istatus = ("Completed" if st["phase"] == "done" else "Not started" if st["phase"] == "not-started"
               else "Paused" if st["paused"] and not st["running"] else "In progress")
    counts = " · ".join([f'{st["verdicts"]}/{st["models"]} verdicts', f'{st["running"]} running']
                        + ([f'{st["paused"]} paused'] if st["paused"] else [])
                        + ([f'{st["stopped"]} stopped'] if st["stopped"] else []))
    L = S["learning"]
    lphase = "pre" if L.get("preregistration_only") else L["status"]["phase"]
    lstatus = "Completed" if lphase == "done" else "Not started" if lphase in ("pre", "not-started") else "In progress"
    cards = [
        ("improve", "Learning", istatus, counts,
         "Do models take better risks after notes from their own games? Every model, five series each.",
         [(f"../{improve_page.PATH}", "Results")]),
        ("learning", "Pilot", lstatus, None, "One model, finished.", [(f"../{learning_page.PATH}", "The pilot")]),
        ("clear-risk", "Clear risk", "In progress", None,
         "Decisions where a risk or safety is clearly better, per setup.", [("../clear-risk/", "Clear risk")]),
        ("nackgammon", "Nackgammon", "Completed", None,
         "Does a model still play well from a different starting position?",
         [("../nackgammon/", "Nackgammon"), ("../leagues/#nack-knockout", "The knockout"),
          ("../matches/#stage-knockout", "Its matches")])]
    out = "".join(
        f'<section class="card experiment-card{" experiment-small" if cid == "learning" else ""}" id="{cid}">'
        f'<h2>{esc(title)}</h2><p class="experiment-status">{status_badge(status)}'
        + (f'<span class="experiment-counts">{esc(sub)}</span>' if sub else "") + f'</p><p>{text}</p>'
        '<p class="hero-links">' + "".join(f'<a href="{href}">{esc(label)}</a>' for href, label in links)
        + '</p></section>'
        for cid, title, status, sub, text, links in cards)
    return page_head(S, "Experiments", "Experiments", "Tests beside the leagues.") + repeat_checks(S) + \
        f'<div class="experiment-cards">{out}</div>'


# Repeat checks (Ümit via Zeki #4663, #4667, #4671; state from the snapshot, Zeki #5032): the reproducibility repeats'
# manifest (tools/v3/repeats) and each repeat's state and numbers from the snapshot of v3.db (build: _repeat_originals);
# once a repeat is complete, Run 1 (its original) and Run 2 on exactly the pairs it finished. The section's numbers are
# published in data/v3/repeat-checks.json (repeat_data).
REPEAT_MANIFEST = ROOT / "mailbox/repeats/manifest-2026-11-11.json"
REPEAT_STATUS = {"queued": "Queued", "running": "Running", "complete": "Complete", "stopped": "Stopped"}
# Changed setting fields in words (a page never names the server-address field).
REPEAT_FIELDS = {"name": "name", "note": "note", "max_matches": "one match at a time",
                 "base_url": "server address (logic's REAX server)", "device": "device note"}


def repeat_data(S) -> list[dict]:
    """One record per repeat, everything the Repeat checks section shows: from the manifest and the build's numbers from
    the snapshot (state, matches finished of the pairs playable today; risk judgement at margin 0.001, error rate,
    decisions, invalid decisions and billed cost). Run 2's numbers only once the repeat is complete and every decision
    of the matched pairs is scored (else scoring_pending); Run 1's on the same pairs."""
    from common import label

    def measures(s, billed):
        q, r = s["quality"], s["risk"]["main"]
        return dict(judgement=r.get("judgement"), judgement_lo=r.get("judgement_lo"), judgement_hi=r.get("judgement_hi"),
                    judgement_na=r.get("judgement_na"), error_rate=q.get("error_rate"), error_lo=q.get("error_lo"),
                    error_hi=q.get("error_hi"), too_few=bool(q.get("too_few")), decisions=q["decisions"],
                    invalid=q["invalid"], billed_usd=round(billed, 4))

    out = []
    for m in json.loads(REPEAT_MANIFEST.read_text())["repeats"]:
        o = S["_repeat_originals"][m["id"]]
        cov, today, cost, rules = m["coverage_original"], m["coverage_repeat_today"], m["cost_basis"], m["rules"]
        played_then = {p["opponent"] for p in m["pairs"] if p["status"] == "finished"}
        sr = m["settings_repeat"]
        complete = o["state"] == "complete"
        out.append(dict(
            id=m["id"], run_id=m["run_id"], model=m["display"], status=o["state"], league=o["league"],
            scoring_pending=complete and o["scoring_pending"],
            original_in=("late entry" if m["original_stage"] == "late-entry" else f'League {m["original_league"]}'),
            original_matches=o["matches"], original=measures(o, o["billed_usd"]),
            repeat=(measures(o["repeat"], o["repeat_billed_usd"])
                    if complete and o["repeat"] and not o["scoring_pending"] else None),
            repeat_matches=o["repeat_matches"], played=o["played"], running_matches=o["running"],
            playable=o["playable"], field=today["of"], original_played=cov["played"], original_field=cov["of"],
            original_dates=[min(p["started"] for p in m["pairs"])[:10],
                            max(p["finished"] or p["started"] for p in m["pairs"])[:10]],
            not_played=[dict(opponent=label(g["opponent"]), reason=g["reason"],
                             out_of_scope=g["opponent"] in OUT_OF_SCOPE_OPPONENTS) for g in cov["not_played"]],
            blocked_today=[dict(opponent=label(b["opponent"]), played_in_original=b["opponent"] in played_then,
                                out_of_scope=b["opponent"] in OUT_OF_SCOPE_OPPONENTS) for b in today["blocked"]],
            setup=(f'its own players row: {sr["spec"]} · {sr.get("provider") or NOT_MEASURED} · '
                   f'{sr.get("quantization") or "hosted"}'),
            settings=(f'as the original\'s, changed: {", ".join(REPEAT_FIELDS[k] for k in m["settings_changed"])}; '
                      f'League 1 rules (prompt {rules["prompt_version"]}, {rules["rounds"]} rounds, {rules["max_turns"]} '
                      f'turns, the original\'s option-order seed, mirror games {"on" if rules["mirror_concurrent"] else "off"}); '
                      "each pair with its original match's seed and seats; one match at a time"),
            dates=dict(prepared=m["prepared"], started=o["started"], finished=o["finished"]),
            cost=dict(estimate_usd=round(cost["estimate_usd"], 2), entrant_usd=round(cost["entrant_usd"], 2),
                      cap_usd=cost["cap_usd"]),
            differences=repeat_differences(m, played_then)))
    return run2_order(out)


REPLAY_LINE = "Not replayable today, though played in the original: "


def repeat_differences(m: dict, played_then: set) -> list[str]:
    """The manifest's differences, as written, except its line on the pairs not replayable today when every one of those
    is outside the requested scope (Ümit #5220): then it says so, without implying they are still to be replayed."""
    gone = [b for b in m["coverage_repeat_today"]["blocked"] if b["opponent"] in played_then]
    if not gone or not all(b["opponent"] in OUT_OF_SCOPE_OPPONENTS for b in gone):
        return m["differences"]
    from common import label
    # The manifest's reason starts with its short form before the first colon ('no credit', 'no OpenRouter endpoint').
    why = ", ".join(f'{label(b["opponent"])} ({b["reason"].split(":", 1)[0]})' for b in gone)
    line = (f"Not replayed, though played in the original: {why}: {OUT_OF_SCOPE}, and blocked today as well; their seed "
            "pins are kept.")
    return [line if x.startswith(REPLAY_LINE) else x for x in m["differences"]]


def run2_order(rows: list[dict]) -> list[dict]:
    """The Run 2 view (Zeki #4838): the repeats with a risk judgement from a complete, scored run first, by that judgement
    (higher first; ties by model name), ranked 1..n consecutively over those only; every other repeat (queued, running,
    stopped, scoring pending, complete without a judgement) below, unranked (rank None), in the manifest's fixed order.
    Each model has one repeat: nothing is picked from several repeats or averaged."""
    done = [d for d in rows if d["repeat"] and d["repeat"]["judgement"] is not None]
    done.sort(key=lambda d: (-d["repeat"]["judgement"], d["model"]))
    rest = [d for d in rows if d not in done]
    return [dict(d, rank=i) for i, d in enumerate(done, 1)] + [dict(d, rank=None) for d in rest]


def repeat_measures(x: dict) -> str:
    """Risk judgement / error rate / decisions, as one cell; below 640 px only the risk judgement (bg.css .rc-more),
    the rest in the row's details."""
    return (f'<span class="rc-m">{repeat_judgement(x)}</span><span class="rc-more"> / <span class="rc-m">'
            f'{repeat_error(x)}</span> / {count(x["decisions"])}</span>')


def repeat_judgement(x: dict) -> str:
    return (f'{fmt(x["judgement"])}<span class="small">{fmt(x["judgement_lo"])} to {fmt(x["judgement_hi"])}</span>'
            if x["judgement"] is not None else nm(x["judgement_na"] or NA))


def repeat_error(x: dict) -> str:
    return (f'{fmt(x["error_rate"])}<span class="small">{fmt(x["error_lo"])} to {fmt(x["error_hi"])}</span>'
            if x["error_rate"] is not None and not x["too_few"] else nm(TOO_FEW if x["too_few"] else NA))


def repeat_state(d: dict) -> tuple[str, str]:
    """(badge, counts) of a repeat: 'Queued', 'Running', 'Stopped' or 'Complete' with 'n of N matches' (N: the pairs
    playable today), or 'Matches complete' with 'scoring pending'."""
    if d["scoring_pending"]:
        return "Matches complete", "scoring pending"
    return REPEAT_STATUS[d["status"]], f'{count(d["played"])} of {count(d["playable"])} matches'


def utc_time(iso: str | None) -> str:
    """'2026-11-11 15:25 UTC' from a stored ISO time; 'not yet' without one."""
    return f'{iso[:10]} {iso[11:16]} UTC' if iso else "not yet"


# The one area of the backgammon repeats: every repeat replays its original's League 1 field (Ümit via Zeki #4831).
REPEAT_AREA = "League play vs League 1's field"
# The Run 2 view (Zeki #4838): rank, model, the repeat (Run 2), its first run beside it, pairs, status; the build's order
# only (no header sorts: ranks hold for completed repeats only, the rest stay in their fixed order below).
REPEAT_HEAD = [(h, " data-nosort") for h in (
    "Rank", "Model", 'Run 2<span class="rc-more">: risk judgement / error rate (PR) / decisions</span>',
    'First run<span class="rc-more">, same pairs</span>', "Pairs", "Status")]
RUN2_NOTE = ("Run 2: the completed repeats ranked by their own risk judgement, Rank 1 to n; queued, running and "
             "stopped repeats below them, unranked, in a fixed order. Each repeat is one run of its model, shown beside "
             "that model's first run on exactly the same pairs, seeds and dice (the pairs the repeat finished, of those "
             "playable today); nothing is picked from several runs or averaged, and the main leaderboard is unchanged.")


def repeat_compare(d: dict) -> str:
    """Run 1 and Run 2 side by side on the matched pairs: risk judgement, error rate, decisions, invalid decisions and
    billed cost; no conclusion drawn."""
    runs = [("Run 1 (first run)", d["original"]), ("Run 2 (repeat)", d["repeat"])]
    rows = [("Risk judgement", repeat_judgement), ("Error rate (PR)", repeat_error),
            ("Decisions", lambda x: count(x["decisions"])), ("Invalid decisions", lambda x: count(x["invalid"])),
            ("Billed cost", lambda x: f'${x["billed_usd"]:.3f}')]
    return ('<table class="rc-compare"><thead><tr><th></th>' + "".join(f"<th>{k}</th>" for k, _ in runs)
            + "</tr></thead><tbody>" + "".join(
                f'<tr><th>{k}</th>' + "".join(f'<td class="num">{f(x)}</td>' for _, x in runs) + "</tr>"
                for k, f in rows) + "</tbody></table>")


def repeat_checks(S) -> str:
    """Repeat checks at the top of Experiments (Ümit via Zeki #4831; Run 2 view, Zeki #4838; state from the snapshot,
    Zeki #5032): one compact table per area, a row per repeat in run2_order: its Run 2 rank (completed repeats only), the
    model (maker dot, family icon, official name and tag, as on the home leaderboard), the repeat's risk judgement /
    error rate / decisions (or its state in words), the first run's on the same pairs, matches finished of the pairs
    playable today and status; Run 1 and Run 2 side by side on the matched pairs (with invalid decisions and billed
    cost), the run id, settings, dates, cost basis and differences in the row's details. Below 640 px: rank, model, both
    risk judgements and status; the rest in the details."""
    import home as H
    # The setup's shown name (maker, family, official name), beside the published record.
    setup = {m["id"]: m["original"] for m in json.loads(REPEAT_MANIFEST.read_text())["repeats"]}
    rows = []
    for d in repeat_data(S):
        state, counts = repeat_state(d)
        mk, colour = H.maker(setup[d["id"]])
        icon = f'<svg class="fam-icon" aria-hidden="true" focusable="false"><use href="#{H.family(setup[d["id"]])["icon"]}"/></svg>'
        dot = f'<i class="swatch hl-dot" style="background:{colour}" title="{esc(mk)}"></i>'
        repeat = repeat_measures(d["repeat"]) if d["repeat"] else nm(f"{state.lower()} · {counts}")
        pairs = f'{count(d["played"])} of {count(d["playable"])}'
        gone = "".join(f"; {esc(unplayed_text(g))}" for g in d["not_played"])
        blocked = "; ".join(
            f'{esc(b["opponent"])} ('
            + ("played in the first run, blocked only today" if b["played_in_original"]
               else "not played in the first run either") + ")"
            for b in d["blocked_today"] if not b["out_of_scope"])
        scope = [b for b in d["blocked_today"] if b["out_of_scope"]]
        scope = (f'; {esc(OUT_OF_SCOPE)}: ' + ", ".join(
            f'{esc(b["opponent"])} (' + ("played in the first run" if b["played_in_original"]
                                        else "not played in the first run either") + "; blocked today as well)"
            for b in scope)) if scope else ""
        cost = d["cost"]
        same = (f'the {count(len(d["original_matches"]))} pairs the repeat finished' if d["status"] == "complete"
                else f'the {count(len(d["original_matches"]))} pairs playable today')
        items = [
            ("Run 2", repeat),
            ("First run", f'{repeat_measures(d["original"])} (risk judgement / error rate (PR) / decisions)'),
            *([("Run 1 and Run 2, same pairs", repeat_compare(d))] if d["repeat"] else []),
            ("Status", f'{esc(state)} · {esc(counts)}' + (f' (league #{d["league"]})' if d["league"] else "")
                       + (f'; {count(d["running_matches"])} in progress' if d["running_matches"] else "")),
            ("Run id", esc(d["run_id"])),
            ("Setup", f'{esc(d["setup"])}; held: in no standings, table or other setup\'s numbers'),
            ("Settings", esc(d["settings"])),
            ("First run's pairs", f'{esc(d["original_in"])}: {count(d["original_played"])} of '
                                  f'{count(d["original_field"])} pairs played, '
                                  f'{esc(" to ".join(dict.fromkeys(d["original_dates"])))}{gone}; its numbers here: its '
                                  f'own decisions in {same} (matches '
                                  f'{esc(", ".join(f"#{i}" for i in d["original_matches"]))})'),
            ("Dates", f'prepared {esc(d["dates"]["prepared"])}; started {esc(utc_time(d["dates"]["started"]))}; '
                      f'finished {esc(utc_time(d["dates"]["finished"]))}'),
            ("Pairs today", f'{count(d["playable"])} of {count(d["field"])} playable (first run: '
                            f'{count(d["original_played"])} of {count(d["original_field"])} played)'
                            + (f'; blocked today: {blocked}' if blocked else "") + scope),
            ("Cost basis", f'${cost["estimate_usd"]:.2f} estimated (the original\'s billed paid-opponent costs'
                           + (f', with its own ${cost["entrant_usd"]:.2f}' if cost["entrant_usd"] else "")
                           + f'); cap ${cost["cap_usd"]:.0f} per repeat'),
            ("Differences from the original protocol",
             "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in d["differences"]) + "</ul>")]
        details = (f'<details class="more rc-details" id="repeat-{d["id"]}"><summary>Details</summary>'
                   '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl></details>")
        rank = (count(d["rank"]) if d["rank"] else
                '<span class="nm"><span class="rc-more">unranked</span><span class="rc-short" title="unranked">–</span></span>')
        rows.append(f'<tr class="rc-row"><td class="num rc-rank">{rank}</td><td class="model">{dot}{icon}'
                    f'<span class="model-name">{name_html(setup[d["id"]])}</span></td><td class="num">{repeat}</td>'
                    f'<td class="num">{repeat_measures(d["original"])}</td>'
                    f'<td class="num rc-pairs">{pairs}</td><td class="rc-status">{status_badge(state)}'
                    f'<span class="small"> · {esc(counts)}</span></td></tr>'
                    f'<tr class="rc-detail-row"><td colspan="{len(REPEAT_HEAD)}">{details}</td></tr>')
    return (f'<section class="card" id="repeat-checks">{H.FAMILY_ICONS}<div class="section-head"><h2>Repeat checks</h2>'
            f'</div><h3>{esc(REPEAT_AREA)}</h3><p class="table-note rc-view">{esc(RUN2_NOTE)}</p>'
            + table(REPEAT_HEAD, rows, f"Repeat checks, {esc(REPEAT_AREA)}, Run 2: each repeat ranked when complete, "
                    "beside its first run on the same pairs", cls="board repeat-table")
            + "</section>")


def nackgammon_page(S) -> str:
    """The Nackgammon paired test on its own page (Ümit #2938 item 5): the home page's section as it was (its per-setup
    tables, chart and method text, from nack-paired.json), moved here."""
    import home
    import nack_section
    sec = nack_section.section(S["nack"], *home.nack_views(S), S["nack_late"])
    return (page_head(S, "Experiments", "Nackgammon") + rebase(sec, "../", ids_of(sec))
            + '<p class="table-note page-note">Finished. The knockout: <a href="../leagues/#nack-knockout">Leagues</a>.</p>')


def rules_text() -> str:
    """The rules of backgammon as every player is given them: the Rules part of the current prompt (bg-v2), verbatim."""
    md = (ROOT / "prompts/bg-v2.md").read_text()
    md = md[md.index("## Rules\n") + len("## Rules\n"):md.index("## Strategy principles")]
    import method
    return method.spec_markdown(md)


def method_sections(method_html: str) -> list[tuple[str, str]]:
    """(id, heading) of the Method page's sections, in order."""
    return re.findall(r'<section class="card" id="([\w-]+)"[^>]*>\s*<h2 id="[\w-]+-title">(.*?)</h2>', method_html)


# About's text (Ümit, bus #2939): content/about.md, four sections in order, then the "Leaderboard box" section that the
# home page shows as "How the scores work". Each section's id: the old About anchors keep landing (#leaderboard is the
# leaderboard rules, with the longer leaderboard notes under them).
ABOUT_IDS = {"Backgammon in one page": "backgammon", "How the benchmark works": "how-it-works",
             "How the scores work": "scores", "Leaderboard rules": "leaderboard", "Leaderboard box": "short"}
GITHUB = "https://github.com/zekiworks/jevgammon"


def about_sections() -> list[tuple[str, str, str]]:
    """(id, heading, markdown) of content/about.md's sections, in order; the "1. " numbering of a heading is dropped."""
    md = re.sub(r"<!--.*?-->", "", (CONTENT_DIR / "about.md").read_text(), flags=re.S)
    out = []
    for block in re.split(r"^## ", md, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        head = re.sub(r"^\d+\.\s*", "", head.strip())
        out.append((ABOUT_IDS[head], head, body.strip()))
    return out


def about_links(rel: str) -> str:
    """About's links (Ümit #2938 item 6): Method, Data, Leagues, Matches, GitHub."""
    items = [(f"{rel}method/", "Method"), (f"{rel}data/", "Data"), (f"{rel}leagues/", "Leagues"),
             (f"{rel}matches/", "Matches"), (GITHUB, "GitHub")]
    return ('<nav class="face-nav about-links" aria-label="About links">'
            + "".join(f'<a href="{h}">{esc(t)}</a>' for h, t in items) + '</nav>')


def about_page(S, method_html: str) -> str:
    import home
    import method
    import story
    ours = [(i, h, method.spec_markdown(md)) for i, h, md in about_sections() if i != "short"]
    more = [("rules", "Rules of backgammon, as the prompt states them"), ("method", "Method"), ("data", "Data"),
            ("how-to-run", "How to run it"), ("late-entries", "Late entries"), ("open-questions", "Open questions"),
            ("pages", "More pages")]
    method_links = "".join(f'<li><a href="../method/#{i}">{h}</a></li>' for i, h in method_sections(method_html))
    parts = {
        "rules": f'<p class="note">The rules as every player reads them in the prompt (bg-v2, the current version: '
                 f'<a href="../method/#prompt">Method: The prompt</a>), quoted unchanged.</p>{rules_text()}',
        "method": f'<p>Every definition, threshold and caveat is on the <a href="../method/">Method</a> page:</p>'
                  f'<ul class="columns">{method_links}</ul>',
        "data": f'{DOWNLOADS}<p>Every data file, with its size and hash: <a href="../data/">Data</a>.</p>',
        "how-to-run": recompute("../data/thresholds.json"),
        "late-entries": f'<p>{esc(LATE_ABOUT)} {esc(LATE_RANKED)}</p><p>{esc(LATE_METHOD)}</p><p>Every late entry, its numbers and its '
                        f'matches: <a href="../leagues/#late-entries">Leagues: Late entries</a>.</p>',
        "open-questions": f'<p>What is not settled yet: every analysis in the plan with its status, and the limits on '
                          f'the <a href="../method/#limits">Method page</a>.</p>{status_list(S)}',
        "pages": more_pages("../")}
    extra = {"scores": home.how_numbers(S, "../"),
             "leaderboard": '<h3 id="leaderboard-notes">How the leaderboard is built</h3>' + story.about_text(S, "../")}
    nav = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t, _ in ours) + "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in more)
    return (page_head(S, "About", "About the benchmark", "Backgammon in one page, how the benchmark works, how the "
                      "scores work and the leaderboard rules; then the method, the data and how to run it.")
            + about_links("../")
            + f'<nav class="face-nav" aria-label="On this page">{nav}</nav>'
            + "".join(f'<section class="card about-text" id="{i}"><h2>{esc(t)}</h2>{body}{extra.get(i, "")}</section>'
                      for i, t, body in ours)
            + "".join(f'<section class="card" id="{i}"><h2>{esc(t)}</h2>{parts[i]}</section>' for i, t in more))


# The Decisions tab's other pages (Ümit #2938 item 1): linked under its first card.
DECISION_PAGES = [("disagreements/", "Where models disagree"), ("phases/", "Phases"), ("compare/", "Compare")]


def decisions_page(S, body: str) -> str:
    links = ('<nav class="face-nav decisions-links" aria-label="More on decisions">'
             + "".join(f'<a href="../{h}">{esc(t)}</a>' for h, t in DECISION_PAGES) + '</nav>')
    head_end = body.index("</section>") + len("</section>")
    # Each setup as the site shows it (official name and tag, Ümit #4445), by dataset and the name decisions/index.json
    # keys it by (that file is part of the results hash and keeps the name): decisions.js shows these.
    shown = {ds: {n: name_text(n, ds) for n in setups} for ds, setups in S["decisions_export"].items()}
    labels = (f'<script type="application/json" id="setup-labels">'
              f'{json.dumps(shown, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")}</script>')
    return (body[:head_end] + links + body[head_end:] + labels
            + f'<p class="version version-line">{esc(version_line(S))}</p>')


def share_card(S) -> str:
    """The link preview card (1200 x 630), drawn from the current results: the board beside the question."""
    from board import board_svg
    sc = S.get("showcase")
    c = S["counts"]
    css = (SITE_CSS_DIR / "decisions.css").read_text()
    board = board_svg(sc["board"], sc["dice"], sc["pips"], play=sc["best"]["notation"],
                      alt=sc["best_safe"]["notation"]) if sc else ""
    cap = (f'{esc(sc["label"])}, stake {eq(sc["stake"])}: the engine\'s best play {esc(sc["best"]["notation"])} (arrows) '
           f'leaves {sc["best"]["hitting_rolls"]} hitting rolls; the best safe play (dashed) '
           f'leaves {sc["best_safe"]["hitting_rolls"]}.') if sc else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{css}
:root{{--text:#e2e8f0;--text-2:#94a3b8;--sans:system-ui,sans-serif;--bd-frame:#3d3226;--bd-felt:#1e293b;--bd-a:#6b5a43;--bd-b:#2f6f63;--bd-tray:#162032;--bd-num:#94a3b8;--bd-me:#ebe9e4;--bd-me-edge:#0e0e0d;--bd-opp:#9a3b2e;--bd-opp-edge:#f0b8ad;--bd-die:#ebe9e4;--bd-die-edge:#0e0e0d;--bd-pip:#1a1a18}}
body{{margin:0;width:1200px;height:630px;background:#0f172a;color:#e2e8f0;font-family:system-ui,sans-serif;display:flex;gap:44px;align-items:center;padding:0 56px;box-sizing:border-box}}
.l{{flex:0 0 520px}} .l svg{{width:520px;height:auto;display:block}} .l p{{font-size:17px;color:#94a3b8;margin:12px 0 0;line-height:1.35}}
.r{{flex:1}} h1{{font-size:50px;margin:0 0 18px;line-height:1.08}} .s{{font-size:23px;color:#cbd5e1;margin:0 0 26px;line-height:1.3}}
ul{{list-style:none;padding:0;margin:0;display:flex;gap:28px}} li b{{display:block;font-size:40px;color:#2dd4bf}} li{{font-size:18px;color:#94a3b8}}
.f{{position:absolute;bottom:26px;right:56px;font-size:17px;color:#64748b}}</style></head><body>
<div class="l">{board}<p>{cap}</p></div>
<div class="r"><h1>{esc(TITLE)}</h1><p class="s">{esc(SUBTITLE)}</p>
<ul><li><b>{count(c["decisions_scored"])}</b>decisions</li><li><b>{c["leagues"]}</b>leagues</li><li><b>{c["model_setups"]}</b>setups</li><li><b>{c["models"]}</b>models</li></ul></div>
<div class="f">Hilde · every decision is public</div></body></html>"""


def description(S) -> str:
    c = S["counts"]
    return (f"{TITLE} {SUBTITLE} Models play backgammon, and GNU Backgammon scores every move they make: {count(c['decisions_scored'])} "
            f"decisions, {count(c['model_setups'])} setups, {count(c['leagues'])} leagues. We measure whether each risk a "
            f"model takes is the right one, and what that costs. Every decision is public.")


# --- Write ----------------------------------------------------------------------------------------------------

def write_all(S, out: Path, base: str) -> None:
    import decisions_export
    import home
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
    import story
    leagues, moved_ids, league_ids = leagues_page(S, method.archive_v1())
    nack = nackgammon_page(S)
    # The old home anchors (#risk-judgement, #lg-hype-cup, #board-panel, #nackgammon-paired …): bg.js sends each to
    # the same id on its new page; ids that stayed on the home page are not in the map.
    home_html = home.home(S)
    moved = moved_anchors({"leagues/": moved_ids, "nackgammon/": ids_of(nack)}, league_ids)
    moved = {k: v for k, v in moved.items() if k not in ids_of(home_html)}
    home_html += f'<script type="application/json" id="moved-anchors">{json.dumps(moved, sort_keys=True)}</script>'
    put("", TITLE, home_html, scripts=("bg.js",), styles=("decisions.css",), body_class="home")
    home.fragments(S, out)
    put("leagues/", "Leagues", leagues, scripts=("bg.js",), styles=("decisions.css",))
    put("nackgammon/", "Nackgammon", nack, scripts=("bg.js",), dataset="nackgammon",
        description="The Nackgammon paired test of the backgammon benchmark (finished): does a model still play well "
                    "when the starting position changes? Per-setup tables, the chart and the method.")
    put("matches/", "Matches", matches_page(S), scripts=("bg.js",),
        description="Every match of the backgammon benchmark: the leagues, the ladder rounds, gap matches, late "
                    "entries, the Hype Cup and the Nackgammon knockout, with scores, winners and links to the decisions.")
    put("phases/", "Phases", phases_page(S), scripts=("bg.js",))
    put("vision/", "Vision", vision_page(S))
    put("compare/", "Compare", compare_page(S), scripts=("bg.js",), dataset="v1-set")
    put("disagreements/", "Where models disagree", disagreements_page(S), scripts=("bg.js",), dataset="v1-set")
    put("new-models/", "New models: first look", new_models_page(S), scripts=("bg.js",))
    put("models/", "Models", models_index(S))
    for lg in S["leagues"]:
        for n, e in lg["setups"].items():
            put(f"models/{lg['dataset']}/{meta(S, lg['dataset'], n)['slug']}/", n, model_page(S, lg["dataset"], n, e, None))
    for n, e in S["v1"]["setups"].items():
        put(f"models/v1-set/{meta(S, 'v1-set', n)['slug']}/", f"{n} (v1)", model_page(S, "v1-set", n, e, None),
            dataset="v1-set")
    for e in S["late_entries"]:
        put(late_href("", e), f"{e['name']} (late entry)", late_entry_page(S, e))
    for r in S["smoke"]:
        put(f"models/smoke-part-a/{meta(S, 'smoke-part-a', r['setup'])['slug']}/", r["setup"],
            model_page(S, "smoke-part-a", r["setup"], None, r), dataset="smoke-part-a")
    ctx = dict(thresholds=S["thresholds"], play_order=S["v1"]["play_order"], shared_sets=S["shared"]["build_log"],
               data_as_of=as_of(S), extra=home.method_extras(S))
    method_html = method.body(ctx)
    put("method/", "Method", method_html, main_class="method-page")
    import clear_risk_section
    # The clear-risk scan's bias chart, a finding section of the home page until Ümit #2938, sits under the scan.
    bias = story.cautious(S)
    put("clear-risk/", "Clear risk (preliminary)", clear_risk_section.body(S) + rebase(bias, "../", ids_of(bias)),
        description="Clear-risk scan of the backgammon benchmark (preliminary / partial): decisions where a risk or "
                    "safety is clearly better, per setup, checks, a rollout check and a partial model quiz.")
    import learning_page
    # The Learning and "Did they improve?" runs are their own (the improve page has its own Route column): the tags there
    # carry the setting and snapshot, never a league setup's route.
    put(learning_page.PATH, learning_page.title(S["learning"]), learning_page.body(S["learning"]),
        description=learning_page.DESCRIPTION, dataset="learning")
    import improve_page
    put(improve_page.PATH, improve_page.title(S["improve"]), improve_page.body(S["improve"], S),
        description=improve_page.DESCRIPTION, scripts=("bg.js",), dataset="improve")
    for path, title, body in improve_page.registration_pages(S["improve"]):
        put(path, title, body, dataset="improve")
    put("data/", "Data", data_page(S, out))
    put("decisions/", "Every decision", decisions_page(S, decisions_export.body()),
        scripts=("decisions.js",), styles=("decisions.css",))
    put("highlights/", "Highlights", highlights_page(S, out), styles=("decisions.css",),
        description="Highlights of the backgammon benchmark: a single decision with the board, the model's play and "
                    "the engine's play, then findings the site already shows, each with its numbers.")
    put("experiments/", "Experiments", experiments_page(S),
        description="Experiments of the backgammon benchmark: Clear risk, Nackgammon and Learning from experience.")
    put("about/", "About", about_page(S, method_html),
        description="About the backgammon benchmark: backgammon in one page, how the benchmark works, how the scores "
                    "work, the leaderboard rules, the method, the data, how to run it, late entries and open questions.")
