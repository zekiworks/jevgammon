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
from dataclasses import dataclass
from datetime import datetime

import home as H
import own_cost
import pages as P
from common import (ALL_NOTE, CONTENT, LATE_ENTRY, NA, QC_LABEL, QC_SETUPS, ROOT, count, esc, fmt, nm, pct, relabel,
                    tag_text, unplayed_text)
from common import label as shown_name
from common import base_model, name_and_tag
import zw_ui as ui

RELEASES = relabel(json.loads((CONTENT / "release_months.json").read_text())["models"])
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
SAME_MODEL = relabel(json.loads((CONTENT / "model_identity.json").read_text())["same_model"])
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
    missing = release_missing(S)
    released = (f'<p>Released (in a row\'s details): the month of the maker\'s own dated statement that this exact model '
                f'was released or became available to the public (an announcement before public availability does not '
                f'count), linked; left out where no such statement is on record ({count(len(missing))} of '
                f'{count(n_models)} models).</p>' if missing else "")
    return ('<p><strong>A fixed table:</strong> the filters on the Leagues page do not change it. Tap a model (or '
            'point at it) for its details and its decisions.</p>'
            '<p>Rank counts 1, 2, 3 down the rows shown, by the measure chosen (Risk judgement, Error rate (PR) or Cost '
            'per 1,000 decisions), among the rows of the table\'s filters (models: All · Chat · Decision; class: All · '
            'Tiny · Small · Medium · Large · Efficient · Workhorse · Flagship, combined with the models; a class with no '
            'model in view has no key; rows: one per model or all setups); the programs are reference rows in every view '
            'and in no class, never ranked. Rank has no tiers: a tier needs a paired exact test '
            '(McNemar, Holm) over one question set every model answered, and the leagues played different positions, so '
            'no pair of models in different leagues shares one. The tier in a row\'s details comes from the same 200 '
            'positions.</p>'
            f'<p>{esc(P.CLASS_RULE)} The maker\'s own figure (model card, announcement or model name), never our '
            'count; the standard price, never an introductory one, and "(provisional)" where the maker publishes only '
            'an introductory or launch price. Never estimated: Undisclosed is a model with neither (never a chat '
            'model, each has a per-token list price; a decision model with only a per-request price or none). The '
            'label after a '
            'model\'s name: its total (trillions to one decimal from 1,000B, whole from 10B, one decimal under 10B), '
            'a mixture of experts as "total MoE · active", or Closed and its price class; a row\'s details give the '
            'maker\'s figure the class uses and our checkpoint count. Parameters (in a row\'s details): the logical '
            'parameter count of the maker\'s released checkpoint, linked, with dense or MoE; a mixture of experts as '
            'total · active; "not disclosed by maker" where the maker gives none.</p>'
            f'<p>{esc(NOTE)}</p><p>{esc(RULE)}</p>'
            '<p>Each model\'s row is its highest reasoning setting played, by the effort the requests sent (off &lt; '
            'minimal &lt; low &lt; medium &lt; high &lt; xhigh &lt; max; on above off for a model without levels; a '
            'decision model\'s single setup), never its best score; late-entry setups count as the model\'s setups '
            '(a late entry stands in the league order of the league whose field it played). Several setups at that '
            'setting: the first in league order, then by setup name (no score). Every value of a row and of its details '
            'is that setup\'s own; its other settings are rows of their own under All setups. Version names '
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
    """The one small grey chip after a row's name (Ümit #3193, #4445): 'setting · route · snapshot · <chat|decision>'
    (common.name_and_tag; each part left out where the setup has none), then its late-entry tag, then 'QC-pending' for a
    setup under QC (content/qc_status.json; its note in the details box); a program 'program' (an other-league row of a
    program: its league first)."""
    if kind == "program":
        parts = [f'League {x["lg"]["id"]}' if league and x["lg"] else None, "program"]
    else:
        typ = model_type(S, x)
        parts = [*name_and_tag(x["name"], x["ds"])[1], typ if typ in TYPE_LABEL else None]
    return " \u00b7 ".join(p for p in parts + [late_tag(x), QC_LABEL if x["name"] in QC_SETUPS else None] if p)


def row_name(x, kind: str) -> str:
    """The name a row shows: a model's official name (its setting, route and snapshot are in its chip; data and links
    keep the setup's name), a program's as it is."""
    return x["name"] if kind == "program" else name_and_tag(x["name"], x["ds"])[0]


def decisions_href(S, x) -> str | None:
    """Every decision filtered to the setup (decisions/?d=…&s=…); a late entry, which Every decision does not hold, its
    own page; a computed reference row none. Unescaped: the kit escapes its links."""
    if x["late"]:
        return P.late_href("", x["late"])
    if x["q"] is None:
        return None
    return f'decisions/?d={x["ds"]}&s={P.meta(S, x["ds"], x["name"])["slug"]}'


def page_href(S, x) -> str | None:
    if x["late"]:
        return None
    return P.model_href("", x["ds"], x["name"], S) if x["q"] is not None else None


# The row's details box (Ümit #2904, as Clocktower Bench's; the kit's box since zw-ui): opened by a tap, a click, a mouse
# on the row or the keyboard (zw-ui.js), each line filled only from the setup's stored values, a line or part left out
# where the data has none (never "n/a"). The row itself shows the rank, the model (maker dot, the name, its class label,
# one chip after it: setting · type, a late entry's tag), the selected measure and two helper columns; every other value
# of the setup is in its box, its maker, type and setting on the first line (Ümit #3039, #3193).
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
        return f'On {esc(P.own_machine(q))}' if P.own_machine(q) else None
    if P.own_machine(q):  # on our machines (Ümit #4665 item 4): the estimate, then where it ran
        label = f"estimate \u00b7 {P.own_machine(q)}"
    else:
        label = ((x["late"].get("price") or {}) if x["late"] else
                 (P.origin_meta(S, x["ds"], x["name"]).get("price") or {})).get("label")
    return (f'<span class="cost-1k">${fmt(q["usd_per_1000"], 3)} per 1,000 decisions</span><span class="cost-1m" '
            f'data-usd="{q["usd_per_1000"]!r}">${fmt(q["usd_per_1000"], 3)}</span><span class="cost-1m"> per 1M decisions</span>'
            + (f' ({esc(label)})' if label else ""))


def details_lines(S, x, kind: str, extra: list, ref: str | None = None) -> list:
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
        join([f'<strong>{esc(row_name(x, kind))}</strong>'] + ([esc(ref) if ref else None] if kind == "program" else
             [esc(p) for p in (mk, TYPE_LABEL.get(model_type(S, x)), *name_and_tag(x["name"], x["ds"])[1]) if p])),
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
        (join([("Provisional: " if e["status"] == P.PROVISIONAL else "") + f'{count(e["played"])} of {count(e["total"])} '
               "matches"] + [esc(unplayed_text(g)) for g in e.get("not_played") or []])
         if e and (e["status"] == P.PROVISIONAL or e.get("not_played")) else None),
        (esc(P.SUBQ_SELF) if e and x["name"] == P.SUBQ_11 else None),
        (f'{QC_LABEL}: {esc(QC_SETUPS[x["name"]])}' if x["name"] in QC_SETUPS else None),
        join([cost_text(S, x), f'{count(q["decisions"])} decisions' if q else None]),
        (f'Cost: {esc(own_cost.tooltip(q["own_cost"], every_gap=False))}' if q and q.get("own_cost") else None),
        (f'Parameters: {P.params_html(x["model"])}' if kind != "program" else None),
        (esc(P.class_note(x["model"])) if kind != "program" and P.class_note(x["model"]) else None),
        (f'Base model: {esc(base_model(x["model"]))}' if kind != "program" and base_model(x["model"]) else None),
        # The Same positions tier (Ümit #4313), in the box: the table keeps five columns (Ümit #4862 item 4).
        (f'Tier (same positions) {esc(tier_text(x["name"]))}' if kind != "program" else None),
        *extra,
        links_line(S, x)]
    return [line for line in lines if line]


def links_line(S, x, rel: str = "") -> str:
    """The box's last line: the setup's decisions (a late entry: its own page) and its model page, where it has them;
    rel: the page's way to the site root."""
    href, page = decisions_href(S, x), page_href(S, x)
    return " \u00b7 ".join(p for p in (
        f'<a href="{rel}{esc(href)}">{"Its late-entry page" if x["late"] else "Its decisions"} \u2192</a>' if href else None,
        f'<a href="{rel}{page}">Model page</a>' if page else None) if p)


def release_missing(S) -> list:
    """The ranked models without a documented release month (About counts them)."""
    return [name for _, _, name, _ in leaderboard_rows(S)[0] if not release(name)[1]]


def model_extras(name: str, group: list, chosen: bool) -> list:
    """The box lines about a row's model: its release month; on its chosen row, the dated checkpoint shown with it."""
    month, url = release(name)
    out = [f'Released <a href="{esc(url)}">{month}</a>'] if url else []
    ckpt = sorted({y["model"] for y in group if y["model"] != name}) if chosen else []
    if ckpt:
        out.append("With its dated checkpoint " + ", ".join(esc(c) for c in ckpt) + " (its own rows under All setups)")
    return out


# --- Learning (Ümit #6068, #6069): the "Did they improve?" state of every leaderboard model, from its sources only ---
# The chat lane's plan models: improve.json through improve_page (verdicts, Run 2 where published, progress); the
# decision lane: its status file (one state and reason per arm); the Tiny / Small and decision plan of 12 Nov: each
# row's state and blocker; any other setup: not in the learning plan. Never a number the sources do not hold.
LEARN_DECISION = ROOT / "workspace/improve/out/improve-decision.json"
LEARN_PLAN = ROOT / "mailbox/learning-small-and-decision-plan-2026-11-12.json"
LANE_WORD = {"pending": "waiting", "complete": "complete", "stopped": "stopped", "not tested": "not tested",
             "not started": "not started", "running": "running"}
# The lanes' reasons are working notes (hosts, ledgers, message numbers): a page shows what each says in public words,
# matched on the note's own terms, in this order; a note none of them matches shows its state alone.
REASONS = [("D5", "Ümit's D5 decision"), ("cash", "cash approval"), ("subcap", "cash approval"),
           ("BUDGET CAP", "its budget cap was reached"), ("context guard", "conservative context guard"),
           ("frozen settings", "no frozen settings yet"), ("renderer", "a request renderer for its server"),
           ("render check", "its render check"), ("no backgammon route", "no backgammon route yet"),
           ("no league record", "no league record"), ("never sees the lessons", "its layer never sees the lessons"),
           ("merged", "the plan amendment's merge")]


def public_reason(*notes: str | None) -> str:
    text = " ".join(n for n in notes if n)
    seen = []
    for term, words in REASONS:
        if term in text and words not in seen:
            seen.append(words)
    return "; ".join(seen)


NOT_IN_PLAN = "not in the learning plan"


@dataclass(frozen=True)
class Learn:
    """One setup's learning state: setup (as its source names it), order (its place: improve_page.result_group's 0 Yes,
    1 No, 2 not finished, then minus the change in risks found), result (HTML: the Result cell), numbers (the four
    number cells of improve_page.NUMBER_COLUMNS, empty without a result), line (the details box's line)."""
    setup: str
    order: tuple
    result: str
    numbers: tuple
    line: str


NO_NUMBERS = ("", "", "", "")


def _chat_lane(S) -> dict:
    """The chat lane's plan models (with the dated roster amendments): /improve/'s own cells (improve_page.result_cells),
    or the state from the validated progress fields."""
    import improve_page as IP
    import improve_validate as V
    L = S["improve"]
    prog = {m["setup"]: m for m in (L["progress"] or {}).get("models", [])}
    by = {m["setup"]: m for m in (L["results"] or {}).get("models", [])} if IP.results_shown(L) else {}
    out = {}
    for pm in L["plan"]["models"]:
        s, p, m = pm["setup"], prog.get(pm["setup"]), by.get(pm["setup"])
        if m is not None:
            v = IP.shown(m)
            group = IP.result_group(m)
            result, numbers = IP.result_cells(m)
            rf = v["change"]["risks_found"]
            line = (f'Did they improve? {IP.qc_mark(m["key"])}{esc(v["status"])} · {fmt(rf, 1, signed=True)} pp · '
                    f'threshold {IP.num(v["threshold"])} pp' if group < 2 else "Did they improve? pending")
            out[s] = Learn(s, (group, -(rf or 0) if group < 2 else 0), result, numbers, line)
            continue
        state = (NA if L["progress_refused"] else "not started" if p is None else
                 f'{IP.progress_status(p)} · series {p["series_done"]} of {V.SERIES}')
        out[s] = Learn(s, (2, 0), IP.chip(esc(state), "state"), NO_NUMBERS, f"Did they improve? {esc(state)}")
    return out


def _decision_lane() -> dict:
    """The decision lane's arms (improve-decision.json): one state per setup, its arms' states and reasons joined."""
    import improve_page as IP
    rows = json.loads(LEARN_DECISION.read_text())["rows"]
    arms: dict[str, list] = {}
    for r in rows:
        arms.setdefault(relabel(r["setup"]), []).append(r)
    out = {}
    for s, rs in arms.items():
        def one(r):
            why = public_reason(r.get("reason"))
            return LANE_WORD.get(r["state"], r["state"]) + (f" ({why})" if why else "")
        texts = [one(r) for r in rs]
        state = texts[0] if len(set(texts)) == 1 else " · ".join(f'{r["arm"]}: {t}' for r, t in zip(rs, texts))
        out[s] = Learn(s, (2, 0), IP.chip(esc(state), "state"), NO_NUMBERS,
                       f"Did they improve? (decision models, two arms) {esc(state)}")
    return out


def _plan_rows() -> dict:
    """The Tiny / Small and decision plan of 12 Nov: each row's league setups with its state and blocker."""
    import improve_page as IP
    out = {}
    for r in json.loads(LEARN_PLAN.read_text())["rows"]:
        kind = ("queued" if r["state"].startswith("READY") else
                "not tested" if "not tested" in (r.get("blocker") or "") else
                "not started" if r["state"].startswith("not started") else "waiting")
        why = public_reason(r["state"], r.get("blocker"))
        state = kind + (f" ({why})" if why else "")
        for b in (r.get("baseline"), r.get("baseline_other")):
            if b and b.get("setup"):
                s = relabel(b["setup"])
                out.setdefault(s, Learn(s, (2, 0), IP.chip(esc(state), "state"), NO_NUMBERS,
                                        f"Did they improve? (learning plan, 12 Nov) {esc(state)}"))
    return out


def learning_states(S) -> dict:
    """{setup name (shown): Learn}: the chat lane first, then the decision lane, then the plan of 12 Nov."""
    out = _plan_rows()
    out.update(_decision_lane())
    out.update(_chat_lane(S))
    return out


def base_name(setup: str) -> str:
    return re.sub(r" \([^()]*\)$", "", setup)


def learning_of(states: dict, x, group: list | None) -> Learn | None:
    """A row's learning state: its own setup's; on a model's own row (group given), else the state of another setup of
    the model (the setting the test used); None: not in the learning plan."""
    own = states.get(x["name"])
    if own is not None or group is None:
        return own
    names = {y["name"] for y in group} | {y["model"] for y in group}
    return next((v for k, v in states.items() if k in names or base_name(k) in names), None)


def learning_cells(states: dict, x, group: list | None) -> tuple[Learn | None, str, tuple]:
    """(state, Result cell, the four number cells) of a row; a state from another setting of the model says which
    setting the test used."""
    import improve_page as IP
    v = learning_of(states, x, group)
    if v is None:
        return None, IP.chip(NOT_IN_PLAN, "none"), NO_NUMBERS
    other = "" if v.setup == x["name"] else f'<span class="zw-int">at {esc(tag_text(name_and_tag(v.setup)[1]) or v.setup)}</span>'
    return v, v.result + other, v.numbers


# The leaderboard on the bench kit (zw_ui, turkce's bench-ui; Zeki #4879), in Reading's form (Ümit #6068: Reading's
# home on the kit): Models · Class · Rows filters, the Measure keys Risk judgement · Learning · Error rate · Cost, each
# panel's Chart / Table views (the table first), the compact table (rank · model · the selected measure · two helper
# columns), every row in view (no Top 10 to fold back), one list per panel (each model's other settings as sub-rows;
# All setups is that list shown flat); every other value in each setup's details box. Rank counts 1, 2, 3 down the rows
# shown, by the selected measure (the risk judgement's order is the league order of leaderboard_rows; Learning: the
# models with a verdict, by the change in risks found); the programs (GNUbg weak, Safest, Random) are pinned reference
# rows: in every Models and Class view, never ranked, after the models.
HERO_TITLE = "Risk calls"  # the page's short title (Ümit #4862 item 5: no hero buttons; the nav carries the ways in)
MEASURE_KEYS = [ui.Key("risk", "Risk judgement"), ui.Key("learning", "Learning"), ui.Key("error", "Error rate (PR)"),
                ui.Key("cost", "Cost per 1,000 decisions")]
VALUED = ("risk", "error", "cost")  # the measures of every setup; Learning is its own (learning_cells)
COST_UNITS = dict(unit="per 1,000 decisions", unit_1m="per 1M decisions")  # the site's cost-unit switch (site.js)
MEASURE_COLUMN = {"risk": ui.Column("Risk judgement", "95% interval"),
                  "error": ui.Column("Error rate (PR)", "95% interval", num=True),
                  "cost": ui.Column("Cost", "$ per 1,000 decisions", num=True, sub_1m="$ per 1M decisions", **COST_UNITS),
}
HELPER_COLUMN = {"risk": ui.Column("Risk judgement", num=True), "error": ui.Column("Error rate (PR)", num=True),
                 "cost": ui.Column("Cost", "$ / 1,000", num=True, sub_1m="$ / 1M", **COST_UNITS)}
# Every measure side by side (Ümit via Zeki #6721): the chosen one first, the others, then the median request time per
# decision (analysis: turns.request_ms, as the Cost and time tables), a column only, never a measure key. No
# calibration column: its definition is pending (bench_scores.CALIBRATION_NOTE).
LATENCY_COLUMN = ui.Column("Latency", "median s", num=True, unit="s, median per decision")
# Each head's meaning opens from it (improve_page.head_tips: hover, keyboard focus, a tap), from the method's words.
HEAD_TIPS = {
    "Rank": "Counts 1, 2, 3 down the rows shown, by the measure chosen; no tiers.",
    "Model": "The model and its setting. Tap or point at a name for its details.",
    "Risk judgement": "100 = every call right, 50 = always safe; higher is better.",
    "Error rate (PR)": (f'{json.loads((CONTENT / "thresholds.json").read_text())["equity_scale"]} × mean 2-ply equity '
                        "loss per decision, the checker-play performance rating (PR) backgammon players use; lower is "
                        "better."),
    "Cost": ("Dollars per 1,000 decisions at each setup's price basis (a list price, or API-equivalent for a "
             "subscription); not a bill paid."),
    "Latency": "Median request seconds per decision (waits between retries not included).",
}
# The Learning tab's groups (Ümit via Zeki #6257): improve_page.result_group's, then the models outside the plan.
LEARN_GROUP = {0: "Improved: Yes", 1: "Improved: No", 2: "Not finished", None: "Not in the learning plan"}
PANEL_SUB = {"risk": "all leagues · 95% interval · higher is better",
             "error": "all leagues · 95% interval · lower is better",
             "cost": "all leagues · lower is better",
             "learning": None}  # Learning: improve_page.ORDER_LINE, the order above the table
PROGRAM_COLOUR = "var(--data-grey)"
SAFE_MARK = "50 = always safe"  # the reference mark on the risk judgement's bar
# The cost cell's one short tag (Ümit #4862 item 4); how it was counted opens from the tag, and the box names the basis.
COST_NOTE = "At each setup's price basis (a list price, or API-equivalent for a subscription); not a bill paid."


def price_label(S, x) -> str | None:
    """The setup's price basis as its setups.json (a late entry: its own) entry names it."""
    return ((x["late"].get("price") or {}) if x["late"] else
            (P.origin_meta(S, x["ds"], x["name"]).get("price") or {})).get("label")


def usd(x) -> float | None:
    return x["q"].get("usd_per_1000") if x["q"] else None


def per_million(v: float) -> str:
    """A cost per 1M decisions as site.js writes it from a cost per 1,000 (setupCostUnit perMillion; checks.py allows
    these 1,000-fold forms of every stored usd_per_1000)."""
    m = v * 1000
    return f"${m:,.0f}" if m >= 100 else f"${m:,.2f}"


def cost_cell(S, x) -> str:
    """'$x' (per 1,000 decisions, and per 1M for the site's cost-unit switch) and one tag opening its calculation: 'GPU
    estimate' on our machines (own_cost's account), 'Billed' for a billed API price, else 'List price' (the price
    basis); a dash where the data has none."""
    q, v = x["q"], usd(x)
    amount = ui.Cost(f"${fmt(v, 3)}", per_million(v)) if v is not None else "\u2013"
    if P.own_machine(q):
        return ui.cost_cell(amount, "GPU estimate", "estimate", own_cost.tooltip(q["own_cost"], every_gap=False))
    if v is None:
        return ui.value(amount)
    label = price_label(S, x)
    billed = bool(label) and "(billed)" in label
    return ui.cost_cell(amount, "Billed" if billed else "List price", "billed" if billed else "list",
                        f"{label}. {COST_NOTE}" if label else COST_NOTE)


def judgement_cell(x, colour: str, bar: bool) -> str:
    """The risk judgement: as the measure, a bar on 0 to 100 with its 95% interval as the whisker, the mark at 50
    (always safe) and beside it the number; as a helper, the number."""
    r = x["r"]
    j = r["judgement"]
    if j is None:
        return nm(r["judgement_na"] or NA)
    if not bar:
        return ui.value(fmt(j))
    lo, hi = r["judgement_lo"], r["judgement_hi"]
    return ui.bar(j / 100, lo / 100, hi / 100, colour, fmt(j), f"{fmt(lo)}\u2013{fmt(hi)}", ref=.5, ref_label=SAFE_MARK)


def family_icon(name: str) -> str:
    """The model's family icon (home.family; the page's FAMILY_ICONS sprite), '' without one."""
    fam = H.family(name)
    return f'<svg class="fam-icon" aria-hidden="true" focusable="false"><use href="#{fam["icon"]}"/></svg>' if fam else ""


def running_row(S, e, measure: str, states: dict) -> ui.Row:
    """A held late entry still playing (held_setups.json "running", analysis.running_entries; Ümit via Zeki #5001): one
    unranked row after the ranked models, every score cell empty (no score until its entry is complete), its finished
    matches of its field as its tag; the league, start, route, runner and the pairs still to play in its details box.
    In no data file. On Learning, its learning state."""
    name = e["name"]
    mk, colour = H.maker(name)
    status = f'Running \u00b7 {count(e["finished"])} of {count(e["total"])} matches'
    started = datetime.fromisoformat(e["started"].replace("Z", "+00:00"))
    lines = [
        " \u00b7 ".join(p for p in (f'<strong>{esc(name)}</strong>', esc(mk), TYPE_LABEL.get(e["type"])) if p),
        f'{esc(status)}: late entry still playing; no score or rank until its entry is complete',
        f'Late-entry league #{e["league"]}, started {started.day} {started:%B %Y}, {started:%H:%M} UTC',
        f'Route: {esc(e["route"])}, model {esc(e["model_id"])}',
        ("Runner: " + "; then ".join(esc(r["commit"]) + (f' ({esc(r["note"])})' if r["note"] else "")
                                     for r in e["runners"])) if e["runners"] else None,
        "Pending: " + "; ".join(esc(p) for p in e["pending"]),
        f'Parameters: {P.params_html(name)}']
    import improve_page as IP
    learn = states.get(name)
    if measure == "learning":
        cells = (learn.result, *learn.numbers) if learn else (IP.chip(NOT_IN_PLAN, "none"), *NO_NUMBERS)
        group = LEARN_GROUP[learn.order[0] if learn else None]
    else:
        cells, group = ("", "", "", ""), ""
    return ui.Row(model=ui.Model(name, colour, mk, P.class_label(name), tag=status, icon=family_icon(name)),
                  measure=cells[0], helpers=tuple(cells[1:]), details=[x for x in lines if x],
                  details_label=f"{name}: details", filters={"models": e["type"], "class": P.model_class(name) or "none"},
                  box_key=f"running/{name}", attrs={"data-kind": "running"}, group=group, untiered=True)


def error_cell(x, interval: bool) -> str:
    v = _er(x)
    if v is None:
        return ui.value("\u2013")
    q = x["q"]
    return ui.value(fmt(v), f'{fmt(q["error_lo"])}\u2013{fmt(q["error_hi"])}' if interval else "")


def risk_key(x) -> tuple:
    return (x["r"]["judgement"] is None, -(x["r"]["judgement"] or 0), x["name"])


class Leaderboard(ui.Bench):
    labels = ui.Labels(empty="No model of this kind on the leaderboard.")
    # Every row in view, as Reading's and Logic's live leaderboards: no Top 10 to fold back (Ümit #6070: closing the kit's
    # Show top 10 scrolled the page up by the folded rows).
    top = None
    default_view = "table"
    # One list per panel (kit v2.1, as Reading's home): one row per model with its other settings as sub-rows; All
    # setups is that list shown flat, in its own order and ranks (rows(..., "all")).
    one_list = True

    def __init__(self, S):
        self.S = S
        self.ranked, self.progs = leaderboard_rows(S)
        self.states = learning_states(S)
        # The chart axes span every row's value and interval, the programs' too (Random's error rate is the highest).
        setups = [y for _, _, _, g in self.ranked + self.progs for y in g]
        errors = [v for y in setups if _er(y) is not None for v in (_er(y), y["q"]["error_hi"])]
        self.er_top = math.ceil(max(errors) / 10) * 10
        costs = [v for v in map(usd, setups) if v]
        self.cost_range = (10 ** math.floor(math.log10(min(costs))), 10 ** math.ceil(math.log10(max(costs))))

    def title(self) -> str:
        return HERO_TITLE

    def scope(self, part) -> str:
        S = self.S
        return (f'{count(S["counts"]["decisions_scored"])} decisions scored in {len(S["leagues"])} leagues · GNU '
                'Backgammon 1.08, 2-ply')

    def filter_rows(self) -> list:
        return P.kit_filters() + [ui.KeyRow("setups", "Rows", [ui.Key("models", "One row per model", ""),
                                                               ui.Key("all", "All setups")])]

    def measure_keys(self):
        return ui.KeyRow("measure", "Measure", MEASURE_KEYS)

    def views(self, part, measure) -> tuple:
        """A chart beside every measure's table (the table first), as Reading's; Learning, a state per model, a table."""
        return ("table",) if measure == "learning" else ("chart", "table")

    def chart_rank(self, part, measure) -> bool:
        return True

    def axis(self, part, measure):
        if measure == "risk":
            return ui.Axis([(v / 100, str(v)) for v in (0, 25, 50, 75, 100)], "risk judgement")
        if measure == "error":
            step = 10 if self.er_top <= 60 else 20 if self.er_top <= 120 else 50
            return ui.Axis([(v / self.er_top, str(v)) for v in range(0, self.er_top + 1, step)], "error rate (PR)")
        if measure == "cost":
            return ui.log_axis(*self.cost_range, lambda v: f"${v:g}", "$ per 1,000 decisions, log scale")
        return None

    def panel_title(self, part, measure) -> tuple:
        import improve_page as IP
        return next(k.label for k in MEASURE_KEYS if k.value == measure), PANEL_SUB[measure] or IP.ORDER_LINE

    def columns(self, part, measure):
        if measure == "learning":
            # /improve/'s columns (Ümit via Zeki #6257), each value its own column; no rank: the rows are in the order
            # the line above the table states, in groups, never ranked.
            import improve_page as IP
            return ui.Columns("", "Model", IP.RESULT_COLUMN, IP.NUMBER_COLUMNS)
        others = [m for m in VALUED if m != measure]
        return ui.Columns("Rank", "Model", MEASURE_COLUMN[measure],
                          tuple(HELPER_COLUMN[m] for m in others) + (LATENCY_COLUMN,))

    def notes(self, part, measure) -> list:
        import improve_page as IP
        class_rule = ui.Note(P.class_rule_note(), raw=True)
        if measure == "learning":
            qc = IP.qc_footnote(self.S["improve"])
            return ['Every model on the leaderboard: its verdict after lessons where one is published (Run 2 where it '
                    'replaced the original), else its state in the learning lanes, as their status files give it. '
                    '<a href="improve/">Did they improve?</a>',
                    ui.Note(P.star_note("Result: Yes or No once every run is complete; the change, right safety change "
                                        "and threshold are in points (pp).", f'<p>{esc(IP.THRESHOLD_NOTE)}</p>'), raw=True),
                    class_rule] + ([ui.Note(qc, raw=True)] if qc else [])
        lead = f"{esc(MEANING)} " if measure == "risk" else ""
        return [f'{lead}{esc(ROW_LINE)} All setups: every setup of every model. '
                '<a href="about/#leaderboard">How rows are chosen</a>',
                ui.Note(P.star_note(esc(ALL_NOTE),
                                    f'<p>{esc(NO_TIERS)} {esc(TIER_NOTE)} {esc(H.RANK_NOTE)}</p><p>$ per 1,000 decisions: '
                                    f'{esc(COST_NOTE)} Each cost\'s tag opens how it was counted; each row\'s details name '
                                    'its price basis.</p><p><a href="about/#leaderboard">How rows are chosen</a></p>',
                                    cls="table-note headline-rule"), raw=True),
                class_rule]

    def sort_key(self, measure: str, x, group: list | None):
        if measure == "learning":
            v = learning_of(self.states, x, group)
            return v.order if v is not None else (3, 0)
        value = {"risk": None, "error": _er, "cost": usd}[measure]
        return (value(x) is None, value(x) or 0) if value else risk_key(x)

    def rows(self, part, measure, setups) -> list:
        if setups == "models":
            models = []
            for x, _, name, group in self.ranked:
                others = sorted((y for y in group if y is not x), key=lambda y: self.sort_key(measure, y, None))
                models.append((x, model_extras(name, group, True), group,
                               [self.row(y, "model", model_extras(name, group, False), measure, setups, None)
                                for y in others]))
            progs = [(x, [self.row(y, "program", [], measure, setups, None) for y in g if y is not x])
                     for x, _, _, g in self.progs]
            models.sort(key=lambda e: self.sort_key(measure, e[0], e[2]))
            out = [self.row(x, "model", extra, measure, setups, group, subs) for x, extra, group, subs in models]
        else:
            flat = sorted(((y, model_extras(name, group, y is x)) for x, _, name, group in self.ranked for y in group),
                          key=lambda e: risk_key(e[0]))
            flat.sort(key=lambda e: self.sort_key(measure, e[0], None))
            progs = [(y, []) for _, _, _, g in self.progs for y in g]
            out = [self.row(x, "model", extra, measure, setups, None) for x, extra in flat]
        out += [running_row(self.S, e, measure, self.states) for e in self.S["_running"]]
        return out + [self.row(x, "program", [], measure, setups, None, subs) for x, subs in progs]

    def row(self, x, kind: str, extra: list, measure: str, setups: str, group: list | None, others=()) -> ui.Row:
        """One setup's row; group: the model's setups on its own row of one row per model (Learning may then show the
        state of the setting the test used)."""
        S = self.S
        model = kind == "model"
        mk, colour = H.maker(x["name"]) if model else ("program", PROGRAM_COLOUR)
        ref = None if model else H.ref_label(S, x["ds"], x["name"])
        cells = {"risk": judgement_cell(x, colour, measure == "risk"), "error": error_cell(x, measure == "error"),
                 "cost": cost_cell(S, x)}
        if measure == "learning":
            import improve_page as IP
            learn, measure_html, helpers = (learning_cells(self.states, x, group) if model else
                                            (None, IP.chip(f"program · {NOT_IN_PLAN}", "none"), NO_NUMBERS))
            untiered, row_group = True, LEARN_GROUP[learn.order[0] if learn else None]
        else:
            value = {"risk": None, "error": _er, "cost": usd}[measure]
            measure_html = cells[measure]
            helpers = (*(cells[m] for m in VALUED if m != measure),
                       ui.value(P.secs((x["q"] or {}).get("time_median")))
                       if (x["q"] or {}).get("time_median") is not None else P.secs(None))
            untiered, row_group = value is not None and value(x) is None, ""
        own = learning_of(self.states, x, None) if model else None
        lines = details_lines(S, x, kind, extra, ref) + ([own.line] if own else
                                                         [f"Did they improve? {NOT_IN_PLAN}"] if model else [])
        return ui.Row(
            model=ui.Model(row_name(x, kind), colour, mk, P.class_label(x["model"]) if model else "",
                           decisions_href(S, x), tag=chip_text(S, x, kind, league=not model and setups == "all"),
                           icon=family_icon(x["name"]) if model else ""),
            measure=measure_html, helpers=helpers, details=lines, details_label=f'{x["name"]}: details',
            filters={"models": model_type(S, x), "class": P.model_class(x["model"]) or "none"} if model else {},
            chart=self.bar(x, measure, colour) if measure in VALUED else None, missing="No value",
            box_key=f'{x["ds"]}/{x["name"]}', others=list(others), group=row_group,
            # A model without a value of the measure shown is not ranked by it; a program is a pinned reference row.
            untiered=model and untiered, pinned=not model)

    def bar(self, x, measure: str, colour: str):
        if measure == "risk":
            r = x["r"]
            j = r["judgement"]
            return None if j is None else ui.Bar(j / 100, fmt(j), r["judgement_lo"] / 100, r["judgement_hi"] / 100,
                                                 ref=.5, ref_label=SAFE_MARK)
        if measure == "error":
            v = _er(x)
            q = x["q"]
            return None if v is None else ui.Bar(v / self.er_top, fmt(v), q["error_lo"] / self.er_top,
                                                 q["error_hi"] / self.er_top)
        v = usd(x)
        return None if not v else ui.Bar(ui.log_share(v, *self.cost_range), f"${fmt(v, 3)}")


def tier_text(name: str) -> str:
    """The row's Same positions tier; a model with some of the 200 answers stored, how many; else 'not run yet'."""
    if name in TIER:
        return str(TIER[name])
    return f'{PARTIAL[name]} of 200 so far' if name in PARTIAL else "not run yet"


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
# Under the table, next to the not-paired note (Ümit #4282 item 2): why # has no tiers, plainly.
NO_TIERS = ("Rank counts 1, 2, 3 down the rows shown, by the measure shown (with a filter on, among those rows only); "
            "it has no tiers: a tier needs a paired test (McNemar, Holm) over positions every "
            "model answered, and each league played its own positions, so models in different leagues never answered "
            "the same ones. The tier in each row's details and Same positions (preview) come from 200 positions every "
            "model there answered.")
TIER_NOTE = "Rank comes from league play; tier comes from the same 200 positions for every model."
# Same positions (preview, Zeki #4287): the stored E1 answers of 'Did they improve?' (content/same_positions_preview.json,
# tools/site/same_positions_publish.py), tiers by exact McNemar with Holm.
SAME = json.loads((CONTENT / "same_positions_preview.json").read_text())
SAME_KEY = "Same positions" if SAME["prompt_equals_league"] else "Same positions (learning-experiment prompt)"
# Shown leaderboard name -> its tier (models with all 200 answers only).
TIER = {shown_name(m["name"]): m["tier"] for m in SAME["models"] if m["tier"] is not None}
# Shown leaderboard name -> answers stored so far (models in the run without all 200).
PARTIAL = {shown_name(m["name"]): m["n"] for m in SAME["models"] if m["tier"] is None}


def same_positions() -> str:
    """The Same positions view: a tier table of the ranked models with all 200 stored E1 answers, then the ranked models
    not yet asked and what asking them would cost."""
    done = sorted((m for m in SAME["models"] if m["tier"] is not None), key=lambda m: (m["tier"], -m["correct"]))
    part = [m for m in SAME["models"] if m["tier"] is None]
    rows = [f'<tr><td>{m["tier"]}</td><th scope="row">{esc(shown_name(m["name"]))}</th>'
            f'<td class="num">{m["correct"]}</td><td class="num">{m["invalid"]}</td>'
            f'<td class="num">{m["rank"]}</td></tr>' for m in done]
    table = P.table(["Tier", "Model", "Engine's best play, of 200", "Invalid (counted wrong)", "League rank"], rows,
                    f"Same positions: {len(done)} models, 200 positions each, by tier", cls="board list",
                    attrs=' id="same-positions-table"')
    prompt = ("The prompt and setting are the league row's (checked request by request against the league prompts)."
              if SAME["prompt_equals_league"] else "The prompt is the learning experiment's, not the league's.")
    T = SAME["missing_totals"]
    late = "; ".join(f'{esc(shown_name(m["name"]))} ({m["n"]} of 200 stored, not in the tiers)' for m in part)
    gone = ", ".join(f'{esc(shown_name(m["name"]))} ({esc(m["unavailable"])})' for m in SAME["missing_ranked"]
                     if m["unavailable"])
    return (f'<p class="table-note">Preview. The stored answers of the "Did they improve?" test without lessons (E1): '
            f'200 positions every model below answered; Muse Ember\'s answers come from its own run of the same test '
            f'(12 Nov 2026, its league route and settings). {prompt} Engine\'s best play: the play loses under '
            f'0.001 against GNU Backgammon\'s best; an invalid answer counts as wrong. Tiers: an exact McNemar test on '
            f'every pair, Holm-adjusted at 0.05; tier 1 is the model with the most best plays and every model not '
            f'significantly different from it, then the same for the models left. Rank is the league rank.</p>'
            + table +
            f'<p class="table-note">Not asked yet: {T["models"]} ranked models ('
            + ", ".join(esc(shown_name(m["name"])) for m in SAME["missing_ranked"]) + ")"
            + (f"; {late}" if late else "") +
            f'. Asking them, one position per request: about ${T["usd_hosted"]} at list price on hosted APIs '
            f'(${T["usd_hosted_available"]} for those available now), {T["hours_sequential"]} hours one after another, '
            f'of which {T["gpu_hours"]} hours on our GPUs. Not available now: {gone}.</p>')


def leaderboard(S) -> str:
    """The home page's head and leaderboard (Ümit #4862; the bench kit, zw_ui.results): the short title, its scope,
    the Models · Class · Rows filters, the Measure keys and the compact table (Leaderboard) with its notes, then Same
    positions (preview). The block keeps the old #leaderboard anchor."""
    import improve_page as IP
    return (P.KIT_ALIASES + IP.head_tips(ui.results(Leaderboard(S), block_id="leaderboard", box_prefix="lb-box"),
                                         "leaderboard", HEAD_TIPS)
            + learning_section()
            + f'<section class="card same-positions" id="same-positions" aria-labelledby="same-positions-title">'
              f'<h2 id="same-positions-title">{esc(SAME_KEY)}</h2>{same_positions()}</section>')


def learning_section() -> str:
    """Under the leaderboard, in its own box (Ümit #6068): what the Learning tab shows and how a model is judged (the
    "Did they improve?" page's short method, word for word), and the way to that page."""
    import improve_page as IP
    return ('<section class="card learning-section" id="learning" aria-labelledby="learning-title">'
            '<h2 id="learning-title">Learning: did they improve?</h2>'
            '<p>The leaderboard\'s Learning tab shows, for every model, its verdict where one is published, else its '
            'state in the learning lanes: running, waiting (and why), not tested (and the rule), or not in the learning '
            'plan.</p>' + IP.summary().replace(' id="improve-summary"', '')
            + '<p><a href="improve/">Did they improve? Every result, test and lesson \u2192</a></p></section>')


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
    ranked, progs = leaderboard_rows(S)
    return ([("model", name, x, H.maker(x["name"])[1]) for x, _, name, _ in ranked]
            + [("program", x["name"], x, None) for x, _, _, _ in progs if x["name"] == "GNUbg weak"])


def two_skill_numbers(S) -> dict:
    """Finding a's numbers (two_skill; the Highlights card reads them too): the ranked models with both shares, those
    below the diagonal, GNUbg weak's row, the heading by its rule, and the rows at the ends of both ranges."""
    rows = _rows_chart(S)
    models = [(label, x, c) for kind, label, x, c in rows if kind == "model"
              and x["r"]["found"]["den"] and x["r"]["right_safety"]["den"]]
    gnu = next((x for kind, label, x, c in rows if kind == "program"), None)
    below = [m for m in models if m[1]["r"]["found"]["share"] < m[1]["r"]["right_safety"]["share"]]
    heading = "Models are too cautious." if 2 * len(below) > len(models) else "Risks found and safe right"
    ends = {k: (min(models, key=lambda m: m[1]["r"][k]["share"])[1], max(models, key=lambda m: m[1]["r"][k]["share"])[1])
            for k in ("found", "right_safety")}
    return dict(rows=rows, models=models, gnu=gnu, below=below, heading=heading, ends=ends)


def two_skill(S) -> str:
    """a. Risks found (x) against safe right (y), one dot per leaderboard row in its maker's colour, GNUbg weak the grey
    reference. Heading rule: most ranked models found a smaller share of the risks that paid than they played safe
    right where safety paid."""
    N = two_skill_numbers(S)
    rows, models, gnu, below, heading = N["rows"], N["models"], N["gnu"], N["below"], N["heading"]
    f = [x["r"]["found"]["share"] for x in N["ends"]["found"]]
    s = [x["r"]["right_safety"]["share"] for x in N["ends"]["right_safety"]]
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


def reasoning_numbers(S) -> dict | None:
    """Finding d's numbers (reasoning; the Highlights card reads them too): the models with two or more settings in one
    league, how many have a lower error rate / a higher risk judgement at the highest setting, the heading by its rule,
    the example model, and the finding's two count sentences as written. None when no model qualifies."""
    groups = [(m, lid, xs) for m, lid, xs in reasoning_groups(S)
              if _er(xs[0]) is not None and _er(xs[-1]) is not None and xs[0]["r"]["judgement"] is not None
              and xs[-1]["r"]["judgement"] is not None]
    if not groups:
        return None
    n = len(groups)
    er_lower = sum(_er(xs[-1]) < _er(xs[0]) for _, _, xs in groups)
    rj_higher = sum(xs[-1]["r"]["judgement"] > xs[0]["r"]["judgement"] for _, _, xs in groups)
    ok = 2 * er_lower > n and 2 * rj_higher <= n
    return dict(groups=groups, n=n, er_lower=er_lower, rj_higher=rj_higher,
                heading="More thinking: better moves, not better risk calls" if ok else "What thinking adds",
                ex=max(groups, key=lambda t: (len(t[2]), -t[1])),
                lead=f'{count(n)} models played two or more reasoning settings in the same league.',
                counts=(f'At the highest setting, {count(er_lower)} of the {count(n)} had a lower error rate than at the '
                        f'lowest, and {count(rj_higher)} of the {count(n)} a higher risk judgement.'))


def reasoning(S) -> str:
    """d. The same model at different reasoning settings, in one league. Heading rule: "More thinking: better moves, not
    better risk calls" only if most such models have a lower error rate at their highest setting and most do not have a
    higher risk judgement there; else "What thinking adds"."""
    N = reasoning_numbers(S)
    if N is None:
        return ""
    groups, n, heading, ex = N["groups"], N["n"], N["heading"], N["ex"]
    text = (f'{N["lead"]} {N["counts"]} {esc(ex[0])}, {esc(ex[2][0]["setting"] or "")} to '
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
            + ("Compared group against group (one group's drop minus another's; a group is the setups from one "
               "original league: League 1, 2, 3), every 99% interval includes 0, so the test does not show the groups' drops to differ. "
               if clear else "Compared group against group (one group's drop minus another's), not every 99% "
               "interval includes 0. ")
            + f"Random play's own drop is {fmt(rd1, 1, True)} PR on the main 200 pairs: the Nackgammon positions were "
            f"{'slightly easier' if rd1 < 0 else 'harder'} for random play.")
    if worse:
        text += " Outside the groups, " + "; ".join(
            f'the late entry {esc(s)} dropped ({fmt(r["final"]["drop"], 2, True)} PR, 97.5% interval '
            f'{fmt(r["final"]["drop_975"][0], 2, True)} to {fmt(r["final"]["drop_975"][1], 2, True)})' for s, r in worse) + "."
    text += f" <strong>{esc(NS.UNCLEAR_NOTE)}</strong>"
    legend = NS.chart_legend(N)
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
