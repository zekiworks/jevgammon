"""The home page as a story (Ümit, bus #2570): one headline table, one row per model at its highest reasoning setting, and
sections whose headings state what the published numbers show, each with one chart, two sentences and one caveat. Every number is a
stored value as the site's tables print it: risk judgement, risks found, right safety, error rate and cost from the
league results; the bias of the clear-risk scan and of its Part 2 question Q1 from the published clear-risk data
(data/v3/clear-risk.json). A third heading asked for, on reasoning, is not shown: the Reasoning tab's comparison is not
paired and shows no effect of the setting (its own note). The check of each heading against these
numbers is mailbox/front-story/evidence (made by evidence.py there), not code here: a heading that the data stops
supporting must be reworded by hand."""

import json
import math
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


# --- The headline table (Ümit, bus #2745; late entries ranked, #2921) --------------------------------------------------
# One row per model at its highest reasoning setting played, late-entry setups included: a fixed rule, never the best
# score. The settings in order,
# as the requests sent them (setups.json "setting"; "none" is off). "on" is the setting of a model without levels
# (thinking on or off only): above off, and a model with "on" and a level fails the build. A decision model sends no
# setting: its single setup. Version names are separate models (Jev 1.13.0, Jev 1.14.0). Several setups at that
# setting: the first in league order, then the setup name; no score (Zeki #2790). A late entry stands in the league
# order of the league whose field it played (Ümit #2921 (b): late entries join the ranking, each tagged).
LEVELS = {"off": 0, "none": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
ON = "on"
# Models that are one row (content/model_identity.json: an approved list, nothing inferred from names): a dated
# checkpoint under its original, which names and dates the row.
SAME_MODEL = json.loads((CONTENT / "model_identity.json").read_text())["same_model"]
# Beside the table until Ümit #2938 item 3; on About since (Zeki #2578's accepted rank sentence in place of the
# whisker-overlap one).
NOTE = ("Bars run to each score; the whisker is its 95% interval. Ranks show observed scores; small gaps need not be "
        "meaningful. Leagues played different positions.")
# The full row rule (Ümit #2921 items 1 and 5); the table's own line is ROW_LINE.
RULE = ("Row rule: each model's highest reasoning setting (off < minimal < low < medium < high < xhigh < max), late "
        "entries included; a model with one setup uses it; several setups at that setting: the first in league order, "
        "then by setup name, never by score.")


def about_text(S, rel: str) -> str:
    """How the leaderboard is built, for the About page: the text that stood above and under the table before
    Ümit #2921 item 5, and the notes that stood beside it before #2938 item 3 (bars and ranks, the row rule, Released),
    unchanged but for where the filters and Every number now are (Leagues)."""
    n_models = len(leaderboard_rows(S)[0])
    missing = headline_rows(S)[1]
    released = (f'<p>Released (in a row\'s details): the month of the maker\'s own dated statement that this exact model '
                f'was released or became available to the public (an announcement before public availability does not '
                f'count), linked; left out where no such statement is on record ({count(len(missing))} of '
                f'{count(n_models)} models).</p>' if missing else "")
    return ('<p><strong>A fixed table:</strong> the filters on the Leagues page do not change it. Tap a model (or '
            'point at it) for its details and its decisions.</p>'
            '<p># is the rank among all models, in every view of the table\'s All · Chat models · Decision models · '
            'Small models filter; the programs are reference rows in every view.</p>'
            f'<p>{esc(SMALL_NOTE)} Parameters (in a row\'s details): the count its maker documents (model card, '
            'Hugging Face repository or announcement), linked; a mixture of experts as total / active; "not disclosed '
            'by maker" where the maker gives none.</p>'
            f'<p>{esc(NOTE)}</p><p>{esc(RULE)}</p>'
            '<p>Each model\'s row is its highest reasoning setting played, by the effort the requests sent (off &lt; '
            'minimal &lt; low &lt; medium &lt; high &lt; xhigh &lt; max; on above off for a model without levels; a '
            'decision model\'s single setup), never its best score; late-entry setups count as the model\'s setups '
            '(a late entry stands in the league order of the league whose field it played). Several setups at that '
            'setting: the first in league order, then by setup name (no score). Every value of a row and of its details '
            'is that setup\'s own; its other settings are under the row\'s expander and under All setups. Version names '
            'are separate models; ' + "; ".join(f"{esc(k)} is under {esc(v)}" for k, v in SAME_MODEL.items()) + ' (a '
            f'dated checkpoint under its original). Every column of every setup: <a href="{rel}leagues/#board-panel">Every '
            'number</a>.</p>' + released)


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
                model=H.model_of(S, ds, n), setting=setting_of(S, ds, n), late=None,
                origin=int(P.origin_meta(S, ds, n).get("dataset", ds).rsplit("-", 1)[1]))


def _first(entries: list) -> dict:
    """The representative among setups of equal standing: the first in league order (the league of its setups.json
    entry), then by setup name. No score."""
    return min(entries, key=lambda x: (x["origin"], x["name"]))


def _top(group: list) -> list:
    """The setups of a row at the model's highest reasoning setting."""
    levelled = any(level(x["setting"], False) > 0 for x in group if x["setting"] != ON)
    top = max(level(x["setting"], levelled) for x in group)
    return [x for x in group if level(x["setting"], levelled) == top]


def _late_entry(S, e) -> dict:
    m = S["setups_meta"].get((LATE_ENTRY, e["name"])) or {}
    return dict(lg=None, ds=LATE_ENTRY, name=e["name"], r=e["risk"]["main"], q=e["quality"],
                model=m.get("model") or e["name"], setting=m.get("setting"), late=e, origin=e["field_league"])


def leaderboard_rows(S) -> tuple[list, list]:
    """(model rows, program rows): each a (chosen setup, the row's other setups, row name, settings played) tuple.
    Model rows, late-entry setups among their model's setups, ranked by the chosen setup's stored risk judgement;
    programs (GNUbg weak, Safest, Random) one row each, their first played setup in league order (computed reference
    rows under it)."""
    groups, progs = {}, {}
    for lg, n, r, ref in H.all_rows(S):
        x = _entry(S, lg, n, r)
        if ref:
            progs.setdefault(n.removesuffix(" (computed)"), []).append(x)
            continue
        groups.setdefault(SAME_MODEL.get(x["model"], x["model"]), []).append(x)
    for e in S["late_entries"]:
        x = _late_entry(S, e)
        groups.setdefault(SAME_MODEL.get(x["model"], x["model"]), []).append(x)
    out = []
    for base, g in groups.items():
        chosen = _first(_top(g))
        out.append((chosen, [x for x in g if x is not chosen], base, g))
    out.sort(key=lambda t: (t[0]["r"]["judgement"] is None, -(t[0]["r"]["judgement"] or 0), t[2]))
    prog_rows = []
    for name in ("GNUbg weak", "Safest", "Random"):  # Ümit's order (#2745 item 5)
        g = progs.get(name, [])
        if g:
            chosen = _first([x for x in g if x["q"] is not None] or g)
            prog_rows.append((chosen, [x for x in g if x is not chosen], name, g))
    return out, prog_rows


def late_tag(x) -> str | None:
    """"late entry", or "late entry · provisional" while a pair of its field is not played."""
    e = x["late"]
    if not e:
        return None
    return "late entry \u00b7 provisional" if e["status"] == P.PROVISIONAL else "late entry"


def chip_text(S, x, kind: str, league: bool = False) -> str:
    """The one small grey chip after a row's name (Ümit #3193): '<setting> · <chat|decision>' (the setting left out
    where the setup has none), then its late-entry tag; a program 'program' (an other-league row of a program: its
    league first)."""
    if kind == "program":
        parts = [f'League {x["lg"]["id"]}' if league and x["lg"] else None, "program"]
    else:
        typ = model_type(S, x)
        parts = [x["setting"], typ if typ in TYPE_LABEL else None]
    return " \u00b7 ".join(p for p in parts + [late_tag(x)] if p)


def row_name(text: str, setting: str | None) -> str:
    """The name a row shows: without a trailing '(<setting>)', which its chip carries (data and links keep the name)."""
    return text.removesuffix(f" ({setting})") if setting else text


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


# The row's details box (Ümit #2904, as Clocktower Bench's): opened by a tap on a phone, by hover or the keyboard focus on
# a desktop (bg.js), each line filled only from the setup's stored values, a line or part left out where the data has
# none (never "n/a"). The row itself shows the rank, the model (maker dot, the name, one chip after it: setting · type,
# a late entry's tag) and the risk judgement; every other value of the setup is in its box, its maker, type and setting
# on the first line (Ümit #3039: nothing under the name; #3193: the chip).
TYPE_LABEL = {"chat": "chat model", "decision": "decision model"}


def model_type(S, x) -> str:
    """"chat", "decision", "program" or "unknown" (home.kind of the setup's setups.json entry)."""
    return H.kind((S["setups_meta"].get((LATE_ENTRY, x["name"])) or {}) if x["late"] else P.origin_meta(S, x["ds"], x["name"]))


def record(x) -> dict | None:
    """The setup's won, drawn and lost matches: its league standing, or its late-entry record."""
    if x["late"]:
        return x["late"].get("record")
    return next((s for s in x["lg"]["standings"] if s["name"] == x["name"]), None)


def cost_text(S, x) -> str | None:
    q = x["q"]
    if q is None or q.get("usd_per_1000") is None:
        return None
    label = ((x["late"].get("price") or {}) if x["late"] else (P.origin_meta(S, x["ds"], x["name"]).get("price") or {})).get("label")
    return (f'<span class="cost-1k">${fmt(q["usd_per_1000"], 3)} per 1,000 decisions</span><span class="cost-1m" '
            f'data-usd="{q["usd_per_1000"]!r}">${fmt(q["usd_per_1000"], 3)}</span><span class="cost-1m"> per 1M decisions</span>'
            + (f' ({esc(label)})' if label else ""))


def details_box(S, x, kind: str, bid: str, extra: list, ref: str | None = None) -> str:
    """The lines of one setup's details box; extra: lines about the row's model (release month, checkpoint); ref: a
    program's reference label (home.ref_label of its row), on the first line in place of maker, type and setting."""
    r, q, e = x["r"], x["q"], x["late"]
    found, safe = r["found"], r["right_safety"]
    join = lambda parts: " \u00b7 ".join(p for p in parts if p)
    rec = record(x)
    er = (f'Error rate {fmt(q["error_rate"])} (95%: {fmt(q["error_lo"])}\u2013{fmt(q["error_hi"])})'
          if q and q.get("error_rate") is not None and not q.get("too_few") else None)
    # The lines in the order of Ümit's example (#2938 item 3): name · maker · type · setting (#3039: no longer under
    # the name; each part only where it is on record) / risk judgement / both halves / the raw counts / error rate ·
    # record · late entry; then the setup's other stored facts; then the links.
    mk = H.maker(x["name"])[0] if kind != "program" else None
    lines = [
        join([f'<strong>{esc(x["name"])}</strong>'] + ([esc(ref) if ref else None] if kind == "program" else
             [esc(p) for p in (mk, TYPE_LABEL.get(model_type(S, x)), x["setting"]) if p])),
        (f'Risk judgement {fmt(r["judgement"])} (95%: {fmt(r["judgement_lo"])}\u2013{fmt(r["judgement_hi"])})'
         if r["judgement"] is not None else None),
        join([f'Risks found {pct(found["share"])}' if found["den"] else None,
              f'safe right {pct(safe["share"])}' if safe["den"] else None]),
        join([f'Took {H.n_(found["n"])} of {H.n_(found["den"])} risks that paid' if found["den"] else None,
              f'played safe in {H.n_(safe["n"])} of {H.n_(safe["den"])} positions where safe paid' if safe["den"] else None]),
        join([er, f'record {count(rec["won"])}\u2013{count(rec["drawn"])}\u2013{count(rec["lost"])}' if rec else None,
              esc(late_tag(x)) if e else None]),
        (None if e else f'League {x["lg"]["id"]}'),
        (f'Played the original League {e["field_league"]} field after the league finished (late entry)' if e else None),
        (join([f'Provisional: {count(e["played"])} of {count(e["total"])} matches'] + [
            f'not played: {esc(g["opponent"])} ({esc(g["reason"])})' for g in e.get("not_played") or []])
         if e and e["status"] == P.PROVISIONAL else None),
        (esc(P.SUBQ_SELF) if e and x["name"] == P.SUBQ_11 else None),
        join([cost_text(S, x), f'{count(q["decisions"])} decisions' if q else None]),
        (f'Parameters: {P.params_html(x["model"])}' if kind != "program" else None),
        *extra,
        links_line(S, x)]
    return box_html(bid, x["name"], lines)


def links_line(S, x, rel: str = "") -> str:
    """The box's last line: the setup's decisions (a late entry: its own page) and its model page, where it has them;
    rel: the page's way to the site root."""
    href, page = decisions_href(S, x), page_href(S, x)
    return " \u00b7 ".join(p for p in (
        f'<a href="{rel}{href}">{"Its late-entry page" if x["late"] else "Open its decisions"} \u2192</a>' if href else None,
        f'<a href="{rel}{page}">Model page</a>' if page else None) if p)


def box_html(bid: str, name: str, lines: list) -> str:
    """A row's details box (bg.js headlineDetails): one paragraph per line, a line without data left out."""
    return (f'<div class="hl-box" id="{bid}" role="group" aria-label="{esc(name)}: details">'
            + "".join(f"<p>{line}</p>" for line in lines if line) + "</div>")


def name_link(S, x, text, bid) -> str:
    href = decisions_href(S, x)
    return (f'<a class="model-name" href="{href}" aria-describedby="{bid}">{esc(text)}</a>' if href else
            f'<span class="model-name" tabindex="0" aria-describedby="{bid}">{esc(text)}</span>')


def tr_attrs(S, x, kind, typ, small: bool = False) -> str:
    """small: the row's model is in the Small models view (its other-settings rows go with it)."""
    hl = f' data-hl-type="{typ}"' + (' data-hl-small="yes"' if small else "")
    if x["late"]:
        return f' data-dataset="{LATE_ENTRY}" data-setup="{esc(x["late"]["slug"])}" data-kind="late"{hl}'
    return H.attrs(S, x["ds"], H.slug_name(x["name"]), kind == "program") + hl


def headline_rows(S) -> tuple[list, list, list]:
    """The table rows (each followed by its hidden other-settings rows) and the models without a release month."""
    ranked, progs = leaderboard_rows(S)
    body, missing, chart = [], [], []
    for kind, rows in (("model", ranked), ("program", progs)):
        if kind == "program" and rows:
            body.append(f'<tr class="hl-group"><th scope="rowgroup" colspan="{len(HEADLINE_HEAD)}">Programs: reference rows, '
                        f'never ranked</th></tr>')
        for i, (x, others, name, group) in enumerate(rows, 1):
            mk, colour = H.maker(x["name"]) if kind == "model" else (None, None)
            fam = H.family(x["name"]) if kind != "program" else None
            icon = f'<svg class="fam-icon" aria-hidden="true" focusable="false"><use href="#{fam["icon"]}"/></svg>' if fam else ""
            dot = f'<i class="swatch hl-dot" style="background:{colour}" title="{esc(mk)}"></i>' if colour else \
                '<i class="swatch hl-dot swatch-program"></i>'
            typ = "program" if kind == "program" else model_type(S, x)
            small = kind == "model" and P.is_small(x["model"])
            # Nothing under the name (Ümit #3039); after it one small grey chip (Ümit #3193): setting · type, a late
            # entry's tag in it (a caveat on its rank); the maker only in the dot and the box.
            tag = f'<span class="hl-tag">{esc(chip_text(S, x, kind))}</span>'
            ref = H.ref_label(S, x["ds"], x["name"]) if kind == "program" else None
            extra = []
            if kind == "model":
                month, url = release(name)
                if url:
                    extra.append(f'Released <a href="{esc(url)}">{month}</a>')
                else:
                    missing.append(name)
                ckpt = sorted({y["model"] for y in group if y["model"] != name})
                if ckpt:
                    extra.append("With its dated checkpoint " + ", ".join(esc(c) for c in ckpt) + " (under the expander)")
            rid = f'hl-{"p-" if kind == "program" else ""}{i}'
            sub_ids = [f"{rid}-{k}" for k in range(1, len(others) + 1)]
            what = "league" if kind == "program" else "setting"
            more = (f'<button type="button" class="hl-more needs-js" aria-expanded="false" aria-controls="{" ".join(sub_ids)}">'
                    f'{count(len(others))} other {what}{"s" if len(others) > 1 else ""}</button>' if others else "")
            rank = f'<td class="num">{i}</td>' if kind == "model" else '<td class="num"><span class="muted" title="never ranked">\u2013</span></td>'
            cls = ' class="reference"' if kind == "program" else ""
            label = x["name"] if kind == "program" else name
            bid = f"{rid}-box"
            body.append(f'<tr{cls}{tr_attrs(S, x, kind, typ, small)} data-box="{bid}">{rank}<td class="model">{dot}{icon}'
                        f'{name_link(S, x, row_name(label, x["setting"]), bid)}{tag}{more}'
                        f'{details_box(S, x, kind, bid, extra, ref)}</td>{judgement_cell(x["r"], colour)}{wide_cells(x)}</tr>')
            for sid, y in zip(sub_ids, others):
                ycol = H.maker(y["name"])[1] if kind == "model" else None
                ybid = f"{sid}-box"
                ytag = f'<span class="hl-tag">{esc(chip_text(S, y, kind, league=True))}</span>'
                body.append(f'<tr class="hl-sub{"" if kind == "model" else " reference"}" '
                            f'id="{sid}" hidden{tr_attrs(S, y, kind, typ, small)} data-box="{ybid}"><td class="num"></td><td class="model">'
                            f'{name_link(S, y, row_name(y["name"], y["setting"]), ybid)}{ytag}'
                            f'{details_box(S, y, kind, ybid, [], ref)}</td>{judgement_cell(y["r"], ycol)}{wide_cells(y)}</tr>')
            if kind != "program" or x["name"] == "GNUbg weak":
                chart.append((kind, label, x, colour))
    return body, missing, chart


# Wide screens add four columns (Ümit #2938 item 3): risks found, safe right, error rate, $ per 1,000 decisions; bg.css
# hides the hl-wide cells below 900 px, where the details box holds the same values.
WIDE_HEAD = ["Risks found", "Safe right", "Error rate (PR)",
             '<span class="cost-1k">$ per 1,000</span><span class="cost-1m">$ per 1M</span>']
HEADLINE_HEAD = ([(h, " data-nosort") for h in ("#", "Model", "Risk judgement (95% interval)")]
                 + [(h, " data-nosort data-wide") for h in WIDE_HEAD])


def wide_cells(x) -> str:
    """The four wide-screen cells of a row, each the setup's stored value as its details box prints it; a dash where
    the data has none."""
    r, q = x["r"], x["q"]
    dash = '<span class="muted">\u2013</span>'
    share = lambda s: pct(s["share"]) if s["den"] else dash  # noqa: E731
    er = fmt(q["error_rate"]) if q and q.get("error_rate") is not None and not q.get("too_few") else dash
    usd = q.get("usd_per_1000") if q else None
    cost = (f'<span class="cost-1k">${fmt(usd, 3)}</span><span class="cost-1m" data-usd="{usd!r}">${fmt(usd, 3)}</span>'
            if usd is not None else dash)
    return "".join(f'<td class="num hl-wide">{v}</td>' for v in (share(r["found"]), share(r["right_safety"]), er, cost))


def too_safe(S, chart: list) -> str:
    """"Too safe" (Ümit #2745 item 6): per row of the table, right safety (played safe when safe was right) and risks
    found (took the risk when it paid), the stored shares; GNUbg weak as the grey reference pair."""
    bars = []
    legend_makers = H.maker_legend(x["name"] for kind, label, x, colour in chart if kind == "model")
    for kind, label, x, colour in chart:
        rs, rf = x["r"]["right_safety"], x["r"]["found"]
        grey = kind != "model"
        slug = x["late"]["slug"] if x["late"] else P.meta(S, x["ds"], x["name"])["slug"]
        val = lambda s: s["share"] * 100 if s["den"] else 0
        text = lambda s: pct(s["share"]) if s["den"] else nm(NA)
        where = (f' · League {x["lg"]["id"]}' if x["lg"] else " · late entry")
        bars.append((f'{esc(label)}<span class="hbar-where">{esc(where)}</span>',
                     [(val(rs), "ts-safety" + (" ts-grey" if grey else ""), None if grey else colour),
                      (val(rf), "ts-found" + (" ts-grey" if grey else ""), None if grey else colour)],
                     f'{text(rs)} | {text(rf)}', f' data-dataset="{esc(x["ds"])}" data-setup="{esc(slug)}"'
                     + (' data-program="yes"' if kind == "program" else "")))
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


# The two lines around the table (Ümit #2938 item 3): the score's meaning above it, the row rule (with the All leagues
# note the merged table carries) under it. The longer notes (bars and whisker, ranks, Released, the full rule) are on
# About (about_text).
MEANING = "Risk judgement: 100 = every call right, 50 = always safe; higher is better."
ROW_LINE = "One row per model at its highest reasoning setting, never its best score; late entries included."
SMALL_NOTE = (f"Small models: {P.billions(P.SMALL_MAX_B)} parameters or fewer (total), as disclosed by the maker; models "
              "with undisclosed size are not included.")


def headline(S) -> str:
    """One row per model at its highest reasoning setting (a fixed rule, not the best score), its other settings
    behind a per-row expander, the programs as grey unranked rows; the All setups key shows the full All leagues risk
    table (every setup, programs as reference rows) in its place."""
    rows = headline_rows(S)[0]
    table = P.table(HEADLINE_HEAD, rows, "One row per model at its highest reasoning setting; all leagues, all phases",
                    cls="board headline",
                    attrs=' data-dataset="all" id="headline-table"')
    keys = ('<span class="keys needs-js" role="group" aria-label="Rows"><button type="button" class="key" '
            'data-headline-view="model" aria-pressed="true">One row per model</button><button type="button" '
            'class="key" data-headline-view="all" aria-pressed="false">All setups</button></span>')
    # The table's own filter (Ümit #2907): local to this table, never the page's filters; programs stay in every view.
    # Small models (Ümit #3465; 15B provisional): rows whose model's disclosed total parameters are at most P.SMALL_MAX_B.
    types = ('<div class="keys hl-filter needs-js" role="group" aria-label="Model type">'
             + "".join(f'<button type="button" class="key" data-hl-filter="{k}" aria-pressed="{str(k == "all").lower()}">'
                       f'{l}</button>' for k, l in (("all", "All"), ("chat", "Chat models"), ("decision", "Decision models"),
                                                    ("small", "Small models")))
             + f'</div><p class="table-note hl-small-note" hidden>{esc(SMALL_NOTE)}</p>')
    return (f'<section class="card headline" id="leaderboard" data-dataset="all" aria-labelledby="leaderboard-title">'
            f'<div class="chart-head"><h2 id="leaderboard-title">Risk calls leaderboard</h2>{keys}'
            f'<p class="chart-sub">{esc(MEANING)}</p></div>'
            f'<div data-headline-panel="model">{types}{table}</div>'
            f'<div data-headline-panel="all" hidden>{H.all_risk_table(S)}{caveat(H.RANK_NOTE, "statistics")}</div>'
            f'<p class="table-note headline-rule">{esc(ROW_LINE)} {esc(ALL_NOTE)} '
            '<a href="about/#leaderboard">How rows are chosen</a><span class="hl-wide-note"> $ per 1,000 decisions: at '
            'each setup\'s price basis, which its details name (a list price, or API-equivalent for a subscription); '
            'not a bill paid.</span></p></section>')


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


def finding(fid: str, heading: str, sentences: str, chart: str, legend: str, warn: str, link: tuple[str, str]) -> str:
    """A finding section (Ümit #2938 item 2): the heading states the finding, one chart, two or three sentences and one
    link (href relative to the site's root, label)."""
    return (f'<section class="card finding" id="{fid}" aria-labelledby="{fid}-title"><h2 id="{fid}-title">{esc(heading)}</h2>'
            f'<p class="finding-text">{sentences}</p><figure class="chart-card chart-wide finding-chart">{chart}'
            + (f'<p class="chart-legend">{legend}</p>' if legend else "") + '</figure>'
            f'<p class="table-note section-caveat">{esc(warn)} <a href="{link[0]}">{esc(link[1])}</a></p></section>')


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
    return finding("clear-risk-bias", "Models are too cautious: the clear-risk scan", text, chart, legend,
                   "Not paired: setups met different positions, so the rows compare only loosely.",
                   ("method/#clear-risk", "More caveats: Method"))


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
    return finding("finding-flinch", heading, text, chart, legend, "Preliminary: two plays shown, not league play.",
                   ("clear-risk/", "Clear risk (preliminary)"))


# --- The front page's finding sections a-f (Ümit #2938 item 2). Every heading is decided from the same stored values
# the section shows (the rule beside each); where the rule fails the section keeps a neutral heading. The check of each
# rule against the data, with its numbers, is mailbox/ct-brief/evidence/a.md ... f.md. --------------------------------

def _svg(label: str, w: int, h: int, body: str) -> str:
    """A finding's SVG in the site's chart style. Its points carry no dataset (they come from several leagues, like the
    leaderboard's rows, and the section says so)."""
    return f'<svg class="chart-svg finding-svg" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">{body}</svg>'


def _rows_chart(S) -> list:
    """The leaderboard's model rows and GNUbg weak: (kind, row name, chosen setup, maker colour)."""
    return headline_rows(S)[2]


def two_skill(S) -> str:
    """a. Risks found (x) against safe right (y), one dot per leaderboard row in its maker's colour, GNUbg weak the grey
    reference. Heading rule: most ranked models found a smaller share of the risks that paid than they played safe
    right where safety paid."""
    rows = _rows_chart(S)
    models = [(label, x, c) for kind, label, x, c in rows if kind == "model"
              and x["r"]["found"]["den"] and x["r"]["right_safety"]["den"]]
    gnu = next((x for kind, label, x, c in rows if kind == "program"), None)
    below = [m for m in models if m[1]["r"]["found"]["share"] < m[1]["r"]["right_safety"]["share"]]
    heading = "Models are too cautious." if 2 * len(below) > len(models) else "Risks found and safe right"
    f = sorted(m[1]["r"]["found"]["share"] for m in models)
    s = sorted(m[1]["r"]["right_safety"]["share"] for m in models)
    who = f"Every one of the {count(len(models))}" if len(below) == len(models) else \
        f"{count(len(below))} of the {count(len(models))}"
    text = (f'{who} ranked models found a worthwhile risk (a risky play at least 0.001 better than the best safe play) '
            f'in a smaller share of the risk-pays positions than the share of safety-pays positions they played safe: '
            f'risks found runs from {pct(f[0])} to {pct(f[-1])}, safe right from {pct(s[0])} to {pct(s[-1])}.')
    if gnu:
        g = gnu["r"]
        text += (f' GNUbg weak, a weak setting of the engine (grey square), is close to even: {pct(g["right_safety"]["share"])} '
                 f'safe right, {pct(g["found"]["share"])} risks found.')
    text += (' Above the diagonal, a model succeeds more often when safety pays than when risk pays; the chart compares '
             'these two success rates, not how often a model plays risky at all.')
    W, Hh, L, B, T, R = 520, 420, 52, 44, 12, 14
    x = lambda v: L + (W - L - R) * v  # noqa: E731
    y = lambda v: Hh - B - (Hh - B - T) * v  # noqa: E731
    parts = []
    for t in range(0, 101, 25):
        v = t / 100
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{T}" y2="{Hh - B}"/>'
                     f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="muted" x="{x(v):.1f}" y="{Hh - B + 14}" text-anchor="middle">{t}%</text>'
                     f'<text class="muted" x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{t}%</text>')
    parts.append(f'<line class="rm-diag" x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}"/>'
                 f'<text x="{(L + W - R) / 2}" y="{Hh - 8}" text-anchor="middle">Risks found: a worthwhile risk when risk paid</text>'
                 f'<text x="14" y="{(T + Hh - B) / 2}" transform="rotate(-90 14 {(T + Hh - B) / 2})" text-anchor="middle">'
                 'Safe right: played safe when safe paid</text>')
    for label, xr, c in models:
        fx, sy = xr["r"]["found"]["share"], xr["r"]["right_safety"]["share"]
        parts.append(f'<circle class="sk-dot" cx="{x(fx):.1f}" cy="{y(sy):.1f}" r="5" style="fill:{c}">'
                     f'<title>{esc(label)}: risks found {pct(fx)}, safe right {pct(sy)}</title></circle>')
    if gnu:
        g = gnu["r"]
        cx, cy = x(g["found"]["share"]), y(g["right_safety"]["share"])
        parts.append(f'<rect class="sk-ref" x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10">'
                     f'<title>GNUbg weak: risks found {pct(g["found"]["share"])}, safe right '
                     f'{pct(g["right_safety"]["share"])}</title></rect>'
                     f'<text class="sk-label" x="{cx + 9:.1f}" y="{cy + 4:.1f}">GNUbg weak</text>')
    chart = _svg("Risks found against safe right, one dot per model", W, Hh, "".join(parts))
    chart += ('<details class="more" id="too-safe-values"><summary>Every model\'s two values</summary>'
              f'{too_safe(S, rows)}</details>')
    legend = (H.maker_legend(xr["name"] for _, xr, _ in models)
              + ' <span><i class="swatch swatch-ts-grey"></i>GNUbg weak (program, reference)</span>'
              ' <span>Dashed diagonal: as often right on both</span>')
    return finding("finding-cautious", heading, text, chart, legend,
                   "Not paired: models met different positions in different leagues.",
                   ("method/#risk-metrics", "How risks found and safe right are counted"))


def release_chart(S) -> str:
    """b. Risk judgement against release month, one line per maker, documented months only (content/release_months.json).
    Heading rule: "Newer models judge risk better" only if every maker with models in two or more months scores higher
    with each later month, and at least two makers do; else the neutral heading."""
    rows = [(label, x, c) for kind, label, x, c in _rows_chart(S) if kind == "model" and x["r"]["judgement"] is not None]
    dated = [(RELEASES[label]["month"], label, x["r"]["judgement"], H.maker(x["name"])[0], c)
             for label, x, c in rows if (RELEASES.get(label) or {}).get("month")]
    by = {}
    for m, label, j, mk, c in sorted(dated):
        by.setdefault(mk, []).append((m, label, j, c))
    # A line joins a maker's models only where they span two or more months.
    spread = {mk: pts for mk, pts in by.items() if len({p[0] for p in pts}) > 1}

    def rising(pts):
        months = sorted({p[0] for p in pts})
        return all(min(p[2] for p in pts if p[0] == b) > max(p[2] for p in pts if p[0] == a)
                   for a, b in zip(months, months[1:]))
    ok = len(spread) >= 2 and all(rising(p) for p in spread.values())
    heading = "Newer models judge risk better" if ok else "Risk judgement by release date"
    lines = "; ".join(f'{esc(mk)} {", ".join(fmt(p[2]) for p in pts)}' for mk, pts in spread.items())
    text = (f'A release month is documented for {count(len(dated))} of the {count(len(rows))} ranked models; only those '
            'are shown, each at the month of its maker\'s own dated statement.')
    if spread:
        text += (f' Makers with models in different months, earliest first: {lines}.'
                 + ("" if ok else " That is not a consistent increase across the makers shown."))
    months = sorted({d[0] for d in dated})
    if not months:
        return ""
    W, Hh, L, B, T, R = 560, 340, 44, 40, 12, 120
    js = [d[2] for d in dated]
    lo, hi = math.floor(min(js) / 5) * 5, math.ceil(max(js) / 5) * 5
    idx = lambda m: (int(m[:4]) * 12 + int(m[5:7]))  # noqa: E731
    m0, m1 = idx(months[0]), idx(months[-1])
    x = lambda m: L + (W - L - R) * ((idx(m) - m0) / ((m1 - m0) or 1))  # noqa: E731
    y = lambda v: Hh - B - (Hh - B - T) * (v - lo) / ((hi - lo) or 1)  # noqa: E731
    parts = []
    for v in range(lo, hi + 1, 5):
        parts.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="muted" x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for k in range(m0, m1 + 1):
        m = f"{(k - 1) // 12}-{(k - 1) % 12 + 1:02d}"
        parts.append(f'<text class="muted" x="{x(m):.1f}" y="{Hh - B + 14}" text-anchor="middle">{MONTHS[int(m[5:]) - 1]}</text>')
    parts.append(f'<text class="muted" x="{L}" y="{Hh - B + 30}">{months[0][:4]}</text>'
                 f'<text x="14" y="{(T + Hh - B) / 2}" transform="rotate(-90 14 {(T + Hh - B) / 2})" text-anchor="middle">'
                 'Risk judgement</text>')
    for mk, pts in by.items():
        c = pts[0][3]
        if mk in spread:
            parts.append(f'<polyline class="rd-line" style="stroke:{c}" points="'
                         + " ".join(f"{x(p[0]):.1f},{y(p[2]):.1f}" for p in pts) + '"/>')
        for m, label, j, _ in pts:
            parts.append(f'<circle class="sk-dot" cx="{x(m):.1f}" cy="{y(j):.1f}" r="4.5" style="fill:{c}">'
                         f'<title>{esc(label)} ({esc(mk)}), released {MONTHS[int(m[5:]) - 1]} {m[:4]}: risk judgement '
                         f'{fmt(j)}</title></circle>')
        last = pts[-1]
        parts.append(f'<text class="sk-label" x="{W - R + 8}" y="{y(last[2]) + 4:.1f}" style="fill:{c}">{esc(mk)}</text>'
                     if mk in spread else "")
    chart = _svg("Risk judgement against release month, one line per maker", W, Hh, "".join(parts))
    legend = H.maker_legend(x["name"] for label, x, _ in rows if (RELEASES.get(label) or {}).get("month"))
    return finding("finding-release", heading, text, chart, legend,
                   "Models without a documented release month are left out.",
                   ("about/#leaderboard", "How release months are dated"))


def reasoning_groups(S) -> list:
    """Every model with two or more reasoning settings in the same league (late entries in the league whose field they
    played): (model, league id, [setups from lowest to highest setting])."""
    groups = {}
    for lg, n, r, ref in H.all_rows(S):
        if not ref:
            x = _entry(S, lg, n, r)
            groups.setdefault((x["model"], lg["id"]), []).append(x)
    for e in S["late_entries"]:
        x = _late_entry(S, e)
        groups.setdefault((x["model"], e["field_league"]), []).append(x)
    out = []
    for (model, lid), g in groups.items():
        levelled = any(level(x["setting"], False) > 0 for x in g if x["setting"] != ON)
        by_level = {}
        for x in g:
            by_level.setdefault(level(x["setting"], levelled), []).append(x)
        if len(by_level) > 1:
            out.append((model, lid, [_first(by_level[k]) for k in sorted(by_level)]))
    return sorted(out, key=lambda t: (t[1], t[0]))


def _er(x):
    q = x["q"]
    return q["error_rate"] if q and q.get("error_rate") is not None and not q.get("too_few") else None


def reasoning(S) -> str:
    """d. The same model at different reasoning settings, in one league. Heading rule: "More thinking: better moves, not
    better risk calls" only if most such models have a lower error rate at their highest setting and most do not have a
    higher risk judgement there; else "What thinking adds"."""
    groups = [(m, lid, xs) for m, lid, xs in reasoning_groups(S)
              if _er(xs[0]) is not None and _er(xs[-1]) is not None and xs[0]["r"]["judgement"] is not None
              and xs[-1]["r"]["judgement"] is not None]
    if not groups:
        return ""
    n = len(groups)
    er_lower = sum(_er(xs[-1]) < _er(xs[0]) for _, _, xs in groups)
    rj_higher = sum(xs[-1]["r"]["judgement"] > xs[0]["r"]["judgement"] for _, _, xs in groups)
    ok = 2 * er_lower > n and 2 * rj_higher <= n
    heading = "More thinking: better moves, not better risk calls" if ok else "What thinking adds"
    ex = max(groups, key=lambda t: (len(t[2]), -t[1]))
    text = (f'{count(n)} models played two or more reasoning settings in the same league. At the highest setting, '
            f'{count(er_lower)} of the {count(n)} had a lower error rate than at the lowest, and {count(rj_higher)} of '
            f'the {count(n)} a higher risk judgement. {esc(ex[0])}, {esc(ex[2][0]["setting"] or "")} to '
            f'{esc(ex[2][-1]["setting"] or "")}: risk judgement {", ".join(fmt(x["r"]["judgement"]) for x in ex[2])}; '
            f'error rate {", ".join(fmt(_er(x)) for x in ex[2])}.')
    rj = [x["r"]["judgement"] for _, _, xs in groups for x in xs]
    er = [_er(x) for _, _, xs in groups for x in xs]
    W, RH, L, T, B, GAP = 640, 26, 200, 30, 26, 24
    PW = (W - L - GAP - 10) / 2
    Hh = T + RH * n + B
    rlo, rhi = math.floor(min(rj) / 10) * 10, math.ceil(max(rj) / 10) * 10
    ehi = math.ceil(max(er) / 10) * 10
    xr = lambda v: L + PW * (v - rlo) / ((rhi - rlo) or 1)  # noqa: E731
    xe = lambda v: L + PW + GAP + PW * v / (ehi or 1)  # noqa: E731
    parts = [f'<text class="sk-head" x="{L}" y="{T - 14}">Risk judgement (higher is better)</text>'
             f'<text class="sk-head" x="{L + PW + GAP}" y="{T - 14}">Error rate, PR (lower is better)</text>']
    for v in range(rlo, rhi + 1, 10):
        parts.append(f'<line class="grid" x1="{xr(v):.1f}" x2="{xr(v):.1f}" y1="{T - 6}" y2="{Hh - B}"/>'
                     f'<text class="muted" x="{xr(v):.1f}" y="{Hh - B + 14}" text-anchor="middle">{v}</text>')
    step = 10 if ehi <= 60 else 20
    for v in range(0, ehi + 1, step):
        parts.append(f'<line class="grid" x1="{xe(v):.1f}" x2="{xe(v):.1f}" y1="{T - 6}" y2="{Hh - B}"/>'
                     f'<text class="muted" x="{xe(v):.1f}" y="{Hh - B + 14}" text-anchor="middle">{v}</text>')
    for i, (m, lid, xs) in enumerate(groups):
        cy = T + RH * i + RH / 2
        c = H.maker(xs[-1]["name"])[1]
        parts.append(f'<text class="sk-row" x="{L - 8}" y="{cy + 4:.1f}" text-anchor="end">{esc(m)} · L{lid}</text>')
        for xf, val in ((xr, lambda x: x["r"]["judgement"]), (xe, _er)):
            pts = [(xf(val(x)), x) for x in xs]
            parts.append(f'<line class="th-line" x1="{pts[0][0]:.1f}" x2="{pts[-1][0]:.1f}" y1="{cy:.1f}" y2="{cy:.1f}" '
                         f'style="stroke:{c}"/>')
            for k, (px, x) in enumerate(pts):
                top = k == len(pts) - 1
                parts.append(f'<circle class="th-dot{" th-top" if top else ""}" cx="{px:.1f}" cy="{cy:.1f}" r="4.5" '
                             f'style="stroke:{c};fill:{c if top else "var(--panel)"}"><title>{esc(x["name"])}: '
                             f'{fmt(val(x))}</title></circle>')
    chart = _svg("The same model at its reasoning settings: risk judgement and error rate", W, Hh, "".join(parts))
    legend = ('<span>One row per model and league; hollow dots: its lower settings, filled dot: its highest setting.</span> '
              + H.maker_legend(xs[-1]["name"] for _, _, xs in groups))
    return finding("finding-reasoning", heading, text, chart, legend,
                   "Not paired: each setting played its own games; these are observed differences.",
                   ("leagues/?tab=reasoning#board", "Every setting, league by league"))


def nack_finding(S) -> str:
    """e. Nackgammon: standard against Nackgammon error rate per setup and group, Random as the reference (the paired
    test's own chart). Heading: always the neutral "A new starting position" (Zeki #2961). The data hold no interval for
    a group's own drop, only the 99% intervals of BETWEEN-group drop differences (primary, primary_original_members);
    those can say whether groups differ, not whether a group dropped. The sentence reports that comparison as such."""
    import nack_section as NS
    N, Lt = S["nack"], S["nack_late"]
    comps = [c for key in ("primary", "primary_original_members") for rule in (N.get(key) or {}).values()
             for c in rule if c.get("kind") == "group"]
    clear = bool(comps) and all(c["ci_99"][0] <= 0 <= c["ci_99"][1] for c in comps)
    heading = "A new starting position"
    rd1 = N["setups"]["Random"]["first"]["drop"]
    worse = [(s, r) for s, r in ((Lt or {}).get("setups") or {}).items() if r.get("label") == "worse"]
    text = ("Each model was asked Nackgammon positions and standard positions matched to them. "
            + ("Compared group against group (one group's drop minus another's: decision models, workhorses, "
               "frontier), every 99% interval includes 0, so the test does not show the groups' drops to differ. "
               if clear else "Compared group against group (one group's drop minus another's), not every 99% "
               "interval includes 0. ")
            + f"Random play's own drop is {fmt(rd1, 1, True)} PR on the main 200 pairs: the Nackgammon positions were "
            f"{'slightly easier' if rd1 < 0 else 'harder'} for random play.")
    if worse:
        text += " Outside the groups, " + "; ".join(
            f'the late entry {esc(s)} dropped ({fmt(r["final"]["drop"], 2, True)} PR, 97.5% interval '
            f'{fmt(r["final"]["drop_975"][0], 2, True)} to {fmt(r["final"]["drop_975"][1], 2, True)})' for s, r in worse) + "."
    text += f" <strong>{esc(NS.UNCLEAR_NOTE)}</strong>"
    legend = ('<span><i class="swatch nack-dot nack-dm"></i>decision models</span> '
              '<span><i class="swatch nack-dot nack-wh"></i>workhorses</span> '
              '<span><i class="swatch nack-dot nack-fr"></i>frontier</span> '
              '<span><i class="swatch nack-dot nack-ng"></i>no group (exploratory)</span> '
              '<span><i class="swatch nack-yard"></i>GNUbg weak, Random</span> '
              '<span>Above the dashed diagonal: higher error on Nackgammon.</span>')
    return finding("finding-nackgammon", heading, text, NS.chart(N), legend,
                   "Paired positions, not league play; a drop mixes the new start with how hard the positions are.",
                   ("nackgammon/", "The Nackgammon test"))


def learning_finding(S) -> str:
    """f. Learning from experience: the page's status line, its verdict's first sentence (published wording only) and
    its risks-found chart. A question, not a claim."""
    import learning_page as LP
    L = S["learning"]
    R = L.get("results")
    if L.get("preregistration_only"):
        return ""
    st = L["status"]
    text = f'Status: {esc(st["line"])}.'
    if R and R["complete"] and LP.is_complete(L):
        text += f' {esc(LP.verdict_head(R))}'
    chart = (LP.risks_figure(R, "finding-learning-chart") if R and R.get("series_total_done") else "") or \
        '<p class="note">No finished series yet.</p>'
    return finding("finding-learning", "Does the model learn from its games?", text, chart, "",
                   "One model, a small pilot; the plan, every number and the lessons are on its page.",
                   (LP.PATH, "Learning from experience"))


def findings(S) -> str:
    """The finding sections a-f, in Ümit's order (#2938 item 2); the wrapper keeps the old #findings anchor."""
    return ('<div class="findings" id="findings">' + two_skill(S) + release_chart(S) + flinch(S) + reasoning(S)
            + nack_finding(S) + learning_finding(S) + '</div>')
