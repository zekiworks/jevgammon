"""The home page of the backgammon site (brief v12 B4), in the approved look: hero, findings, filters, the
leaderboard (Risk first), the chart panels, "Risk pays vs safety pays" and the downloads line. Every number comes
from S (build.compute); the per-phase views of a league are written as fragments (fragments/<league>-<phase>.html)
that the page loads when the Phase filter changes, so the page itself stays small."""

import json
import math
import textwrap

import analysis as A
import pages as P
from common import CLOSE_B_SCOPE_NOTE, NA, NOT_MEASURED, PENDING, PROVISIONAL, PROVISIONAL_NOTE, TOO_FEW, count, esc, fmt, nm, pct, status_badge

TABS = [("risk", "Risk"), ("quality", "Quality"), ("confidence", "Confidence"), ("reasoning", "Reasoning"),
        ("cost", "Cost"), ("stability", "Stability")]
INTRO = ("Models play backgammon, and an engine scores every move they make. We measure whether each risk a model "
         "takes is the right one, and what that costs. Every decision is public.")
LIMIT_PAIRED = "Setups played different positions; league comparisons are not paired."
LIMIT_HIT = "Hit risk only: being hit. Gammon risk and priming are not in it."
LIMIT_HARD = ("Setups met different positions; risk judgement is not adjusted for how hard they were. Paired "
              "comparisons wait for the shared positions.")
GNUBG_WEAK = "x86-64 build: its noise is shifted, so it overplays gammons"
CALL_LABEL = {"needless": "needless risks", "missed": "missed risks", "wrong_risk": "wrong risks",
              "right_risk": "right risks", "right_safety": "right safety", "none": "No trade-off"}
SPLIT_ORDER = ["needless", "missed", "wrong_risk", "right_risk", "right_safety", "none"]
PHASES = ["all"] + A.PHASES
TOP_N = 8
MARGIN_LABEL = {"main": "0.001", "robust": "0.02"}


# --- Setups -------------------------------------------------------------------------------------------------

def kind(m: dict) -> str:
    t = m.get("model_type") or ""
    return "program" if t == "program" else "decision" if t.startswith("decision") else "chat" if t else "unknown"


def settings_line(m: dict) -> str:
    """One settings line under a setup's name (B4): reasoning, kind of answer, where it runs."""
    t = m.get("model_type") or ""
    what = {"decision model": "decision model", "chat model, answer-letter probabilities": "letter probabilities",
            "chat model, one letter": "one letter", "program": "program"}.get(t, t)
    bits = [f"reasoning {m['setting']}" if m.get("setting") else None, what, m.get("runs_on"),
            "shuffled play order" if m.get("play_order") else None]
    return " · ".join(b for b in bits if b)


def attrs(S, ds, name, ref=False) -> str:
    m = P.meta(S, ds, name)
    return (f' data-dataset="{esc(ds)}" data-setup="{esc(m["slug"])}" data-kind="{"reference" if ref else kind(m)}"'
            f' data-weights="{esc(m.get("weights") or "unknown")}" data-runs="{esc(m.get("runs_on") or "unknown")}"'
            f' data-setting="{esc(m.get("setting") or "none")}"')


def cell_model(S, ds, name, ref=None) -> str:
    if ref:
        return (f'<td class="model"><span class="model-name">{esc(name)}</span>'
                f'<span class="small">reference row, never ranked · {esc(ref)}</span></td>')
    m = P.meta(S, ds, name)
    extra = f" · {GNUBG_WEAK}" if name == "GNUbg weak" else ""
    return (f'<td class="model"><a class="model-name" href="{P.model_href("", ds, name, S)}">{esc(name)}</a>'
            f'<span class="small">{esc(settings_line(m) + extra)}</span></td>')


def is_reference(S, ds, name) -> bool:
    return name in ("Safest", "Random", "GNUbg weak") and kind(P.meta(S, ds, name)) == "program"


def ref_label(S, ds, name) -> str | None:
    return {"Safest": "always plays safe", "Random": "a random legal play", "GNUbg weak": GNUBG_WEAK}.get(name) \
        if is_reference(S, ds, name) else None


def rows_of(S, lg, phase="all", margin="main"):
    """(name, risk metrics, quality, reference label) for every setup of the league, model setups first by risk
    judgement, then the reference rows (Safest, Random, GNUbg weak; computed where the program did not play)."""
    ds = lg["dataset"]
    out = []
    for n, s in lg["setups"].items():
        r = s["risk"][margin]
        q = s["quality"]
        if phase != "all":
            r, q = r["phases"][phase], s["quality_phases"][phase]
        out.append((n, r, q, ref_label(S, ds, n)))
    for n, ref in lg["references"].items():
        r = ref["risk"][margin]
        if phase != "all":
            r = r["phases"][phase]
        out.append((n, r, None, ref["label"]))
    model = sorted((x for x in out if not x[3]), key=lambda x: (x[1]["judgement"] is None, -(x[1]["judgement"] or 0), x[0]))
    refs = sorted((x for x in out if x[3]), key=lambda x: x[0])
    return model + refs


# --- Cells --------------------------------------------------------------------------------------------------

def n_(x) -> str:
    """A count; the computed Random row's counts are expectations, shown with one decimal."""
    return count(int(round(x))) if abs(x - round(x)) < 1e-6 else fmt(x, 1)


def share_td(s: dict) -> str:
    if not s["den"]:
        return f'<td class="num">{nm(NA)}<span class="small">0 / 0</span></td>'
    return f'<td class="num">{pct(s["share"])}<span class="small">{n_(s["n"])} / {n_(s["den"])}</span></td>'


def judgement_td(r: dict) -> str:
    if r["judgement"] is None:
        return f'<td class="num">{nm(r["judgement_na"])}</td>'
    return (f'<td class="num"><strong>{fmt(r["judgement"])}</strong><span class="small">{fmt(r["judgement_lo"])} to '
            f'{fmt(r["judgement_hi"])}</span></td>')


def split_td(r: dict) -> str:
    if r["error_rate"] is None:
        return f'<td class="num">{nm(NA)}</td>'
    parts = " · ".join(f"{CALL_LABEL[k]} {fmt(r['by_call'][k], 2)}" for k in SPLIT_ORDER)
    return f'<td class="num">{fmt(r["error_rate"])}<span class="small">{esc(parts)}</span></td>'


def classes_td(r: dict) -> str:
    return (f'<td class="num">{n_(r["trade_off"])}<span class="small">Risk pays {n_(r["risk_pays"])} · Safety pays '
            f'{n_(r["safety_pays"])} · No trade-off {n_(r["no_trade_off"])}</span></td>')


def size_td(r: dict) -> str:
    f = lambda s: nm(TOO_FEW) if s["too_few"] and s["n"] else (fmt(s["mean"]) if s["mean"] is not None else "0")
    return (f'<td class="num">{f(r["size"]["right"])} / {f(r["size"]["bad"])}<span class="small">'
            f'{n_(r["size"]["right"]["n"])} / {n_(r["size"]["bad"]["n"])} decisions</span></td>')


def conf_call_td(r: dict) -> str:
    c = r.get("confidence")
    if not c:
        return f'<td class="num">{nm(NA)}</td>'
    a = fmt(c["auroc_right_risk"], 2) if c["auroc_right_risk"] is not None else TOO_FEW
    b = pct(c["missed_mean_p"]) if c["missed_mean_p"] is not None else TOO_FEW
    left = "".join(f"; {count(c[k])} {what} left out" for k, what in (("taken_grouped", "split into groups"),
                                                                    ("taken_other", "without a probability for another reason"))
                   if c.get(k))
    return (f'<td class="num">{esc(a)}<span class="small">{count(c["taken_n"])} risks with a probability\u2021{esc(left)}; '
            f'mean confidence on missed risks {esc(b)} ({count(c["missed_n"])})</span></td>')


# Reviewed brief of 24 Oct 2026, item 4: ability and caution (Method spec 2026-10-24 §2).
SDT_LIMIT = "A simple model of the risk call (equal-variance signal detection); setups met different positions."
SDT_COSTS = ("The cost-derived SDT reference uses the setup's own mean equity lost per needless and per missed risk; those "
             "costs depend on the setup's own play, so it is a reference under that model, not the best caution, and a "
             "correctly classified call can still lose equity.")


def ability_td(r: dict) -> str:
    s = r["sdt"]
    if s["na"]:
        return f'<td class="num">{nm(s["na"])}</td>'
    iv = f'{fmt(s["dprime_lo"], 2)} to {fmt(s["dprime_hi"], 2)} · ' if s["dprime_lo"] is not None else ""
    return (f'<td class="num">{fmt(s["dprime"], 2)}<span class="small">{iv}risks taken {n_(s["hit"]["n"])} / '
            f'{n_(s["hit"]["den"])} Risk pays · needless {n_(s["false_alarm"]["n"])} / {n_(s["false_alarm"]["den"])} '
            f'Safety pays</span></td>')


def caution_td(r: dict) -> str:
    s = r["sdt"]
    if s["na"]:
        return f'<td class="num">{nm(s["na"])}</td>'
    word = "cautious" if s["caution"] > 0 else "bold" if s["caution"] < 0 else "neutral"
    iv = f'{fmt(s["caution_lo"], 2, True)} to {fmt(s["caution_hi"], 2, True)} · ' if s["caution_lo"] is not None else ""
    return f'<td class="num">{fmt(s["caution"], 2, True)}<span class="small">{iv}{word}</span></td>'


def cstar_td(r: dict) -> str:
    s = r["sdt"]
    costs = (f'needless risks lost {P.eq(s["needless_loss"]) if s["needless_loss"] is not None else nm(NA)} on average '
             f'({n_(s["needless_n"])}) · missed risks {P.eq(s["missed_loss"]) if s["missed_loss"] is not None else nm(NA)} '
             f'({n_(s["missed_n"])})')
    if s["cstar"] is None:
        return f'<td class="num">{nm(s["cstar_note"])}<span class="small">{costs}</span></td>'
    label = "" if s["cstar_status"] == "valid" else f'{nm(s["cstar_note"])} '
    return (f'<td class="num">{label}{fmt(s["cstar"], 2, True)}<span class="small">\u03b2 {fmt(s["beta"], 2)} · '
            f'{costs}</span></td>')


def sdt_cells(r: dict) -> str:
    return ability_td(r) + caution_td(r) + share_td(r["sdt"]["aim"]) + cstar_td(r)


SDT_HEAD = ["Ability d\u2032", "Caution c (+ cautious, \u2212 bold)", "Aim: right ÷ (right + wrong risks)",
            "Cost-derived SDT reference c*"]
RISK_HEAD = ["Model and setting", "Risk judgement", "Risks found", "Right safety", "Good risks", "Missed risks",
             "Needless risks", "Wrong risks", "Error rate by risk-call category (PR)", "Decisions with a trade-off",
             "Big risks found", "Big needless risks", "Extra hitting rolls: right / wrong and needless",
             "Confidence on the call: ranking score for right risk"] + SDT_HEAD
ROBUST_HEAD = ["Model and setting", "Risk judgement", "Risks found", "Right safety", "Good risks", "Missed risks",
               "Needless risks", "Wrong risks"] + SDT_HEAD
BIG_NOTE = "Big risks found: stake above 0.08. Big needless risks: the chosen play lost more than 0.08."
CONF_NOTE = ("\u2021 Risks with a probability: decisions whose plays were split into groups have no single probability "
             "and are left out; their count is shown per row. Setups that return no probabilities show N/A.")


def sdt_notes() -> str:
    return (f'<p class="table-note">Ability, caution and the SDT reference: {esc(SDT_LIMIT)} {esc(SDT_COSTS)} Rates '
            'corrected by adding 0.5 to the counts and 1 to the totals; a setup without Risk pays or Safety pays decisions '
            'shows N/A. Intervals: 95%, blocks of two seat-swapped games resampled. <a href="method/#risk-ability">Definitions</a></p>')


def risk_table(S, lg, phase="all") -> str:
    ds = lg["dataset"]
    body = []
    for n, r, _, ref in rows_of(S, lg, phase):
        cls = ' class="reference"' if ref else ""
        body.append(f'<tr{cls}{attrs(S, ds, slug_name(n), bool(ref))}>{cell_model(S, ds, n, ref if n in lg["references"] else None)}'
                    + judgement_td(r) + share_td(r["found"]) + share_td(r["right_safety"]) + share_td(r["good"])
                    + share_td(r["missed"]) + share_td(r["needless"]) + share_td(r["wrong"]) + split_td(r)
                    + classes_td(r) + share_td(r["stake"]["big"]["found"]) + share_td(r["needless_by_loss"]["big"])
                    + size_td(r) + conf_call_td(r) + sdt_cells(r) + "</tr>")
    where = "all phases" if phase == "all" else P.PHASE_LABEL[phase]
    return (P.SWIPE + P.table(RISK_HEAD, body, f"Risk calls at the 0.001 margin, {esc(where)}; shares with count / "
                              "denominator, risk judgement with its 95% interval (games resampled)",
                              attrs=f' data-dataset="{ds}" data-margin="0.001"')
            + f'<p class="table-note">{esc(LIMIT_HIT)}</p><p class="table-note">{esc(LIMIT_HARD)}</p>'
            + f'<p class="table-note">{esc(BIG_NOTE)}</p><p class="table-note">{esc(CONF_NOTE)} Confidence on the call: '
              'ranking score only, no calibration gap (the probability is for the chosen play, not the risk). '
              '<a href="method/#risk">Definitions</a></p>' + sdt_notes())


def robust_table(S, lg, phase="all") -> str:
    ds = lg["dataset"]
    body = []
    for n, r, _, ref in rows_of(S, lg, phase, "robust"):
        cls = ' class="reference"' if ref else ""
        body.append(f'<tr{cls}{attrs(S, ds, slug_name(n), bool(ref))}>{cell_model(S, ds, n, ref if n in lg["references"] else None)}'
                    + judgement_td(r) + share_td(r["found"]) + share_td(r["right_safety"]) + share_td(r["good"])
                    + share_td(r["missed"]) + share_td(r["needless"]) + share_td(r["wrong"]) + sdt_cells(r) + "</tr>")
    return (f'<h3 class="table-title" id="risk-robust-{ds}{"" if phase == "all" else "-" + phase}">The same at the 0.02 margin (robustness)</h3>'
            + P.SWIPE + P.table(ROBUST_HEAD, body, "Every 0.001 in the definitions replaced by 0.02",
                                attrs=f' data-dataset="{ds}" data-margin="0.02"'))


def reasoning_sdt_table(S, lg) -> str:
    """Item 4: ability and caution of one model at its two reasoning settings in this league (every model with both
    settings in the league's games), with the change and the time and tokens it costs. Different positions: UNPAIRED."""
    if not lg["reasoning"]:
        return ""
    rows = []
    for r in lg["reasoning"]:
        lo, hi = lg["setups"][r["low"]], lg["setups"][r["high"]]
        cells = []
        for m in ("main", "robust"):
            a, b = lo["risk"][m]["sdt"], hi["risk"][m]["sdt"]
            for k in ("dprime", "caution"):
                if r["sdt"][m] is None:
                    cells.append(f'<td class="num">{nm(a["na"] or b["na"])}</td>')
                else:
                    cells.append(f'<td class="num">{fmt(a[k], 2, k == "caution")} \u2192 {fmt(b[k], 2, k == "caution")}'
                                 f'<span class="small">change {fmt(r["sdt"][m][k + "_change"], 2, True)}</span></td>')
        qa, qb = lo["quality"], hi["quality"]
        t = (f'{P.secs(qa.get("time_median"))} \u2192 {P.secs(qb.get("time_median"))}<span class="small">'
             + (f'{fmt(r["extra_time_median"], 1, True)} s' if r["extra_time_median"] is not None else nm(NOT_MEASURED))
             + '</span>')
        tok = lambda q: fmt(q["tokens_out"], 0) if q.get("tokens_out") is not None else nm(NOT_MEASURED)
        rows.append(f'<tr data-dataset="{lg["dataset"]}"><td class="model"><span class="model-name">{esc(r["model"])}</span>'
                    f'<span class="small">{esc(r["low_setting"])} \u2192 {esc(r["high_setting"])} · UNPAIRED</span></td>'
                    + "".join(cells) + f'<td class="num">{t}</td><td class="num">{tok(qa)} \u2192 {tok(qb)}</td></tr>')
    head = ["Model", "Ability d\u2032, 0.001", "Caution c, 0.001", "Ability d\u2032, 0.02", "Caution c, 0.02",
            "Median s per decision", "Output tokens per decision (mean)"]
    return (f'<h3 class="table-title" id="risk-reasoning-{lg["dataset"]}">Ability and caution by reasoning setting '
            '(UNPAIRED)</h3>' + P.SWIPE
            + P.table(head, rows, "The same model at its lower and higher setting in this league's games: UNPAIRED, the "
                      "two settings met different positions", attrs=f' data-dataset="{lg["dataset"]}"')
            + '<p class="table-note">UNPAIRED: league games are not the same positions, so a change here is not a paired '
              'effect of the setting. Output tokens include reasoning tokens where the provider counts them there.</p>')


def slug_name(n: str) -> str:
    return n


def quality_table(S, lg, phase="all") -> str:
    ds = lg["dataset"]
    setups = lg["setups"] if phase == "all" else {n: dict(s, quality=s["quality_phases"][phase]) for n, s in lg["setups"].items()}
    rows = []
    for n in P.by_error(setups):
        q = setups[n]["quality"]
        b = P.band(S, q["error_rate"]) if q.get("error_rate") is not None and not q.get("too_few") else None
        cells = (P.er_cell(q) + f'<td class="num">{esc(b) + " (approx.)" if b else nm(NA)}</td>'
                 + P.val(q, "best_share", pct) + P.val(q, "blunder_share", pct)
                 + f'<td class="num">{P.secs(q.get("time_median"))} / {P.secs(q.get("time_p90"))}</td>'
                 + P.cost_cell(S, ds, n, q)
                 + f'<td class="num">{count(q["scored"])}'
                 + (f'<span class="mark">\u2020</span><span class="small">{count(q["grouped"])} split into groups</span>'
                    if q.get("grouped") else "")
                 + f'</td><td class="num">{count(q["invalid"])}</td>')
        rows.append(f"<tr{attrs(S, ds, n)}>{cell_model(S, ds, n)}{cells}</tr>")
    where = "all phases" if phase == "all" else P.PHASE_LABEL[phase]
    head = ["Model and setting", "Error rate (PR), 95% interval", "Band on the human scale (approx.)",
            "Engine's best play", "Blunder rate", "Median / P90 s per decision", "$ per 1,000 decisions",
            "Decisions scored", "Invalid answers"]
    return P.SWIPE + P.table(head, rows, f"Decision quality, {esc(where)}: equity given away against GNUbg 2-ply",
                             attrs=f' data-dataset="{ds}"')


def confidence_table(S, lg) -> str:
    ds = lg["dataset"]
    rows = []
    th = S["thresholds"]
    for n in P.by_error(lg["setups"]):
        s = lg["setups"][n]
        src = P.meta(S, ds, n).get("confidence_source") or "none"
        c = s.get("confidence")
        if not c:
            cells = f"<td>{esc(src)}</td>" + "".join(f'<td class="num">{nm(NA)}</td>' for _ in range(10))
        else:
            cut = []
            for k in (str(x) for x in th["confidence_cutoffs"]):
                x = c["cutoffs"][k]
                mean = nm(TOO_FEW) if x["too_few"] else (P.eq(x["mean_loss"]) if x["mean_loss"] is not None else "0")
                cut.append(f'<td class="num">{count(x["kept"]["n"])}<span class="small">{pct(x["kept"]["share"])} of '
                           f'{count(x["kept"]["den"])}</span></td>' + share_td(x["blunders"])
                           + f'<td class="num">{mean}</td>')
            tf = c["too_few"]
            g = lambda v, f: nm(TOO_FEW) if tf else (f(v) if v is not None else nm(NA))
            sure = nm(TOO_FEW) if c["surest"]["too_few"] else fmt(c["surest"]["error_rate"])
            cells = (f"<td>{esc(src)}</td>" + "".join(cut)
                     + f'<td class="num">{sure}<span class="small">{count(c["surest"]["n"])} decisions</span></td>'
                     + f'<td class="num">{g(c["auroc_best"], lambda v: fmt(v, 2))}<span class="small">warning before a blunder '
                       f'{g(c["auroc_blunder"], lambda v: fmt(v, 2))}</span></td>'
                     + f'<td class="num">{g(c["ece"], lambda v: fmt(100 * v, 1))}</td>'
                     + share_td(c["confident_badly_wrong"]))
        cells += close_td(S, ds, n, s.get("close"))
        rows.append(f"<tr{attrs(S, ds, n)}>{cell_model(S, ds, n)}{cells}</tr>")
    head = ["Model and setting", "Confidence source", "Kept at 0.90", "Blunders among kept, 0.90",
            "Mean equity lost among kept, 0.90", "Kept at 0.99", "Blunders among kept, 0.99",
            "Mean equity lost among kept, 0.99", "Error rate in the surest quarter (PR)",
            "Ranking score (AUROC) for the engine's best play", "Calibration gap (ECE, points)",
            "Confident and badly wrong",
            (f'Close choices<span class="small th-note">{esc(CC_HEAD_NOTE)}</span>',
             ' data-nosort title="Not sortable: setups are never ranked by close choices"')]
    return (P.SWIPE + P.table(head, rows, "Confidence: the probability a setup gave its chosen play; N/A for setups "
                              "without probabilities", attrs=f' data-dataset="{ds}"')
            + '<p class="table-note">The cutoff chosen on half of the games and tested on the other half: '
              '<a href="method/#confidence">Method</a>.</p>'
            + f'<p class="table-note cc-label">Close choices: {esc(S["close_spec"]["label"])} Click a value for its '
              f'details; this column cannot be sorted. <a href="method/#close-choices">Method</a></p>'
            + P.subset_note(ds))


def cost_table(S, lg) -> str:
    return P.SWIPE + P.table(P.COST_HEAD, P.cost_rows(S, "", lg["dataset"], lg["setups"]), "Time and cost in this league",
                             attrs=f' data-dataset="{lg["dataset"]}"')


# --- Close choices (Method spec 2026-10-24 §9) ------------------------------------------------------------------

CC_HEAD_NOTE = "The second most likely play has at least half the probability of the first."
CC_PNG_NOTE = ("Bars per setup, top to bottom: small, medium, big stake (Risk pays only). | Each bar: close choices "
               "among the eligible decisions in that band. | ")
def cc_id(S, ds, n) -> str:
    return f'cc-{ds}-{P.meta(S, ds, n)["slug"]}'


def close_td(S, ds, n, c) -> str:
    """The Confidence tab's Close choices cell: the value opens the setup's details (an anchor; never sorted)."""
    if not c or c["na"]:
        return f'<td class="num">{nm(NA)}<span class="small">{esc(P.CC_NA)}</span></td>'
    s = c["close"]
    return (f'<td class="num"><a class="cc-open" href="#{cc_id(S, ds, n)}" title="Details: {esc(n)}">{pct(s["share"])}</a>'
            f'<span class="small">{count(s["n"])} / {count(s["den"])}{P.SMALL_MARK if s["small"] else ""}</span></td>')


def close_details(S, lg) -> str:
    """Per setup, opened from the Close choices column: risk, engine values, missed risks, both margins."""
    ds = lg["dataset"]
    label = S["close_spec"]["label"]
    out, na = [], []
    for n in P.by_error(lg["setups"]):
        c = lg["setups"][n].get("close")
        if not c or c["na"]:
            na.append(n)
            continue
        href = P.model_href("", ds, n, S) + "#close-choices"
        out.append(
            f'<details class="cc-details" id="{cc_id(S, ds, n)}"><summary><strong>{esc(n)}</strong>: close choices '
            f'{esc(P.cc_text(c["close"]))}</summary><div class="cc-body">'
            f'<h4>1. Risk</h4><p>Close choices between a safe play (the fewest hitting rolls of all legal plays) and a '
            f'riskier one: <strong>{esc(P.cc_text(c["risk_close"]))}</strong> of the close choices.</p>{P.close_risk_table(c)}'
            f'<h4>2. Engine values</h4>{P.close_engine_table(c)}'
            f'<h4>3. Missed risks</h4><p>In Risk pays positions whose two most likely plays are a safe one and a riskier '
            f'one: is the play made more often a missed risk in close choices than in other decisions?</p>{P.close_missed_table(c)}'
            f'<p class="table-note">{esc(label)} <a href="{href}">Full breakdown</a></p>'
            f'</div></details>')
    note = (f'<p class="table-note">{esc(NA)} ({esc(P.CC_NA)}): {esc(", ".join(na))}.</p>' if na else "")
    if not out:
        return (f'<h3 class="table-title" id="close-{ds}">Close choices: details</h3>'
                f'<p class="table-note">{esc(NA)}: no setup in this league has a full probability distribution. {esc(label)}</p>')
    return (f'<h3 class="table-title" id="close-{ds}">Close choices: details per setup</h3>'
            f'<p class="table-note">{esc(S["close_spec"]["definition"])} {esc(label)}</p>' + P.subset_note(ds)
            + f'<div class="cc-list">{"".join(out)}</div>{note}')


# --- Offline analyses (reviewed brief of 24 Oct 2026, item 5; Method spec 2026-10-24) --------------------------

SUPPORT_LABEL = [("complete", "Complete"), ("sparse", "Sparse: an option without its own probability"),
                 ("unverified", "Stored vector not reproduced from the response"), ("no_raw", "No raw response"),
                 ("grouped", "Plays split into groups"), ("not_audited", "Not audited (after the audit)")]
REREAD_NOTE = ("Re-read from the model's probabilities, not played: the recorded positions scored again with the play "
               "the setup's own probabilities point to; not a league result, and no new win rates.")


def mini_bins(bins: list, other: list | None = None) -> str:
    """A small reliability diagram (10 fixed bins): observed share against mean probability; dashed: after the refit."""
    W = H = 64
    pt = lambda b: f'{4 + (W - 8) * b["mean_p"]:.1f},{H - 4 - (H - 8) * b["observed"]:.1f}'
    line = lambda bs, cls: (f'<polyline class="{cls}" points="{" ".join(pt(b) for b in bs if b["n"])}"/>'
                            if any(b["n"] for b in bs) else "")
    return (f'<svg class="mini-rel" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Reliability '
            f'diagram"><line class="rel-diag" x1="4" y1="{H - 4}" x2="{W - 4}" y2="4"/>{line(bins, "rel-before")}'
            f'{line(other, "rel-after") if other else ""}</svg>')


def mini_hist(h: dict) -> str:
    W, H = 100, 28
    top = max(h["counts"]) or 1
    bars = "".join(f'<rect class="hist-bar" x="{i * W / 10 + 1:.1f}" y="{H - (H - 2) * c / top:.1f}" width="{W / 10 - 2:.1f}" '
                   f'height="{(H - 2) * c / top:.1f}"/>' for i, c in enumerate(h["counts"]))
    return f'<svg class="mini-hist" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Histogram">{bars}</svg>'


def support_table(S, lg) -> str:
    off = lg["offline"]
    rows = []
    for n in sorted(off["support"], key=str.lower):
        c = off["support"][n]
        if not sum(c.get(k, 0) for k, _ in SUPPORT_LABEL):
            continue
        rows.append(f'<tr{attrs(S, lg["dataset"], n)}>{cell_model(S, lg["dataset"], n)}'
                    + "".join(f'<td class="num">{count(c.get(k, 0))}</td>' for k, _ in SUPPORT_LABEL) + "</tr>")
    if not rows:
        return f'<p>{nm(NA)}: no setup in this league returns option probabilities.</p>'
    return (P.SWIPE + P.table(["Model and setting"] + [l for _, l in SUPPORT_LABEL], rows,
                              "Probability support of each decision, checked against the raw responses",
                              attrs=f' data-dataset="{lg["dataset"]}"')
            + '<p class="table-note">Only Complete decisions enter the re-read, the refit and the distributions below. '
              'Sparse: a letter missing from the returned top log-probabilities was filled with 0 and the rest '
              'renormalised, so its probability is unknown. <a href="method/#offline">Method</a></p>')


def reread_table(S, lg) -> str:
    off = lg["offline"]
    rows = []
    for n in sorted(off["reread"], key=str.lower):
        r = off["reread"][n]
        iv = lambda a, b: f'95% interval {fmt(r[a], 2, True)} to {fmt(r[b], 2, True)}' if r[a] is not None else ""
        common = max(r["chosen"].items(), key=lambda kv: kv[1]) if r["chosen"] else None
        rows.append(
            f'<tr{attrs(S, lg["dataset"], n)}>{cell_model(S, lg["dataset"], n)}'
            f'<td class="num">{count(r["records"])}<span class="small">{count(r["trade_off"])} with a trade-off</span></td>'
            f'<td class="num">{fmt(r["judgement_played"])} \u2192 {fmt(r["judgement_reread"])}</td>'
            f'<td class="num">{fmt(r["judgement_diff"], 1, True)}<span class="small">{iv("judgement_diff_lo", "judgement_diff_hi")}'
            f' · stability {fmt(r["judgement_diff_p5"], 1, True)} to {fmt(r["judgement_diff_p95"], 1, True)}</span></td>'
            f'<td class="num">{fmt(r["pr_played"])} \u2192 {fmt(r["pr_reread"])}</td>'
            f'<td class="num">{fmt(r["pr_diff"], 1, True)}<span class="small">{iv("pr_diff_lo", "pr_diff_hi")}'
            f' · stability {fmt(r["pr_diff_p5"], 1, True)} to {fmt(r["pr_diff_p95"], 1, True)}</span></td>'
            f'<td class="num">{esc(common[0]) if common else nm(NA)}<span class="small">'
            + (f'{count(common[1])} of {count(off["splits"])} splits · ' if common else "")
            + f'always safe {count(r["always_safe"])} · always risky {count(r["always_risky"])}</span></td>'
            f'<td class="num">{count(r["no_fit"])} / {count(r["test_judgement_na"])}</td></tr>')
    few = off["reread_too_few"]
    note = ("".join(f" {esc(n)}: {count(k)} complete decisions." for n, k in sorted(few.items()))
            if few else "")
    if not rows:
        body = (f'<p>{nm(NA)}: no setup in this league has {count(S["thresholds"]["min_decisions_per_cell"])} complete '
                f'decisions.{note}</p>')
    else:
        head = ["Model and setting", "Complete decisions", "Risk judgement: as played \u2192 re-read",
                "Change in risk judgement", "Error rate (PR): as played \u2192 re-read", "Change in error rate",
                "Threshold chosen most often", "Splits without a fit / test half without a class"]
        body = (P.SWIPE + P.table(head, rows, f"Re-read risk call, {esc(off['label'])}: means over {count(off['splits'])} "
                                  "splits of the games, each tested on its held-out half",
                                  attrs=f' data-dataset="{lg["dataset"]}" data-margin="0.001"')
                + (f'<p class="table-note">{esc(TOO_FEW)}:{note}</p>' if note else ""))
    return (f'<h3 class="table-title" id="reread-{lg["dataset"]}">Re-read risk call ({esc(off["label"])})</h3>' + body
            + f'<p class="table-note">{esc(REREAD_NOTE)} Same held-out decisions for both columns. Stability: the 5th to '
              '95th percentile over the splits, not an interval; 95% interval: blocks of two seat-swapped games resampled, '
              'the whole procedure repeated. <a href="method/#offline">Method</a></p>')


def calibration_tables(S, lg) -> str:
    off = lg["offline"]
    out = []
    for ev, title, what in (("chosen", "Chosen play", "the probability of the chosen play against \"the chosen play is "
                             "the engine's best\""),
                            ("risk_class", "Risk class", "P(risk), the probability mass on risky plays, against \"the "
                             "position is Risk pays\"")):
        rows = []
        for n in sorted(off["calibration"], key=str.lower):
            c = off["calibration"][n].get(ev)
            if not c:
                continue
            if c["too_few"] or c.get("brier_before") is None:
                cells = f'<td class="num">{nm(TOO_FEW)}</td><td class="num">{nm(TOO_FEW)}</td><td></td>'
            else:
                cells = (f'<td class="num">{fmt(c["brier_before"], 3)}</td><td class="num">{fmt(c["brier_after"], 3)}</td>'
                         f'<td>{mini_bins(c["bins_before"], c["bins_after"])}</td>')
            rows.append(f'<tr{attrs(S, lg["dataset"], n)}>{cell_model(S, lg["dataset"], n)}'
                        f'<td class="num">{count(c["paired"])}<span class="small">of {count(c["records"])}; '
                        f'{count(c["failed_folds"])} folds without a fit</span></td>{cells}</tr>')
        if rows:
            out.append(f'<h4>{esc(title)}: {esc(what)}</h4>' + P.SWIPE + P.table(
                ["Model and setting", "Decisions (before and after)", "Brier score as shipped", "Brier score after the refit",
                 "Reliability: as shipped (solid), after (dashed)"], rows,
                f"{esc(title)} calibration as shipped and after a Platt refit cross-fitted by blocks of games",
                attrs=f' data-dataset="{lg["dataset"]}"'))
    if not out:
        return ""
    return (f'<h3 class="table-title" id="calibration-{lg["dataset"]}">Calibration as shipped and after a refit</h3>'
            + "".join(out) + '<p class="table-note">Two different events, kept apart: the chosen play\'s probability is '
            'not the probability that a risk pays. 10 fixed bins; the refit of a decision never saw its own block of '
            'games. <a href="method/#offline">Method</a></p>')


def distribution_tables(S, lg) -> str:
    off = lg["offline"]
    rows = []
    for n in sorted(off["distributions"], key=str.lower):
        d = off["distributions"][n]
        for a, b, label in (("right", "wrong", "Engine's best play vs not"),
                            ("right_risk", "bad_risk", "Right risks vs wrong and needless risks")):
            cell = lambda h: (f'<td class="num">{nm(TOO_FEW) if h["too_few"] else fmt(h["median"], 2)}'
                              f'<span class="small">{count(h["n"])} decisions</span>{mini_hist(h) if h["n"] else ""}</td>')
            rows.append(f'<tr{attrs(S, lg["dataset"], n)}>{cell_model(S, lg["dataset"], n)}<td>{esc(label)}</td>'
                        + cell(d[a]) + cell(d[b]) + "</tr>")
    if not rows:
        return ""
    return (f'<h3 class="table-title" id="distributions-{lg["dataset"]}">Confidence on right and wrong decisions</h3>'
            + P.SWIPE + P.table(["Model and setting", "Groups", "First group: median confidence",
                                 "Second group: median confidence"], rows,
                                "The chosen play's probability, Complete decisions only; 10 fixed bins from 0 to 1",
                                attrs=f' data-dataset="{lg["dataset"]}" data-margin="0.001"')
            + '<p class="table-note">The probability here is the chosen play\'s, never P(risk). Risks: risks taken at the '
              '0.001 margin. <a href="method/#offline">Method</a></p>')


def offline_confidence(S, lg) -> str:
    if not lg.get("offline"):
        return ""
    return (f'<h3 class="table-title" id="support-{lg["dataset"]}">Which probabilities are complete</h3>'
            + P.subset_note(lg["dataset"])
            + support_table(S, lg) + reread_table(S, lg) + calibration_tables(S, lg) + distribution_tables(S, lg))


def cheapest_section(S, lg) -> str:
    off = lg.get("offline")
    if not off:
        return ""
    c = off["cheapest"]
    rows = []
    for n in sorted(c["setups"], key=str.lower):
        v, cov = c["setups"][n], c["coverage"][n]
        rows.append(f'<tr{attrs(S, lg["dataset"], n)}>{cell_model(S, lg["dataset"], n)}'
                    f'<td class="num">{count(v["qualified"])}<span class="small">{count(v["qualified_unpriced"])} of them '
                    f'unpriced</span></td><td class="num">{count(v["chosen"])}</td>'
                    f'<td class="num">{count(v["cleared"]) if v["chosen"] else nm(NA)}'
                    f'<span class="small">of {count(v["chosen"])} chosen</span></td>'
                    f'<td class="num">{count(cov["priced"])} / {count(cov["decisions"])}</td></tr>')
    head = ["Model and setting", f"Splits clearing the bar on training (of {count(c['splits'])})", "Chosen as cheapest",
            "Bar cleared on the held-out half", "Decisions with a price"]
    return (f'<h3 class="table-title" id="cheapest-{lg["dataset"]}">Minimum bar, then cheapest</h3>'
            f'<p>Bar: risk judgement at least {fmt(c["bar_judgement"], 0)} and error rate at most {fmt(c["bar_error_rate"], 0)} '
            f'PR (equity lost, not a share of mistakes). In each of {count(c["splits"])} splits the cheapest priced setup '
            f'that clears the bar on one half of the games is chosen and checked on the other half. No setup cleared the '
            f'bar in {count(c["no_qualifier"])} splits; only unpriced setups did in {count(c["no_priced_qualifier"])}.</p>'
            + P.SWIPE + P.table(head, rows, "Minimum bar on training, cheapest priced setup, checked on the held-out half",
                                attrs=f' data-dataset="{lg["dataset"]}" data-margin="0.001"')
            + '<p class="table-note">An unpriced setup can clear the bar but is never called cheapest. Programs are left out. '
              '<a href="method/#offline">Method</a></p>')


# --- Charts -------------------------------------------------------------------------------------------------

def _svg(kind_: str, ds: str, margin: str, width: int, height: int, body: str, label: str, rows: int, top: int,
         row_h: int, decisions: float) -> str:
    return (f'<svg class="chart-svg" data-chart="{kind_}" data-dataset="{ds}" data-margin="{margin}" '
            f'data-top="{top}" data-row-h="{row_h}" data-rows="{rows}" data-decisions="{decisions:.0f}" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc(label)}">{body}</svg>')


def _row(S, ds, name, y, inner, n, rank, ref=False) -> str:
    return (f'<g class="row" transform="translate(0 {y})" data-n="{n:.0f}" data-rank="{rank}"'
            f'{attrs(S, ds, name, ref)}>{inner}</g>')


def _label(name, detail, w=200) -> str:
    return (f'<text x="{w - 8}" y="13" text-anchor="end">{esc(name)}</text>'
            f'<text class="muted" x="{w - 8}" y="26" text-anchor="end">{esc(detail)}</text>')


def risk_map(S, lg, margin, phase="all") -> str:
    """B6.5: x = missed + wrong risks / Risk pays, y = needless risks / Safety pays; diagonals of equal risk
    judgement; colour = share of wrong risks among the Risk pays decisions without the right risk."""
    ds = lg["dataset"]
    W, H, L, T, R, B = 640, 470, 56, 16, 20, 46
    x = lambda v: L + (W - L - R) * v
    y = lambda v: H - B - (H - T - B) * v
    parts = []
    for t in range(0, 101, 20):
        parts.append(f'<line class="grid" x1="{x(t / 100):.1f}" x2="{x(t / 100):.1f}" y1="{T}" y2="{H - B}"/>'
                     f'<text class="muted" x="{x(t / 100):.1f}" y="{H - B + 14}" text-anchor="middle">{t}%</text>'
                     f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(t / 100):.1f}" y2="{y(t / 100):.1f}"/>'
                     f'<text class="muted" x="{L - 6}" y="{y(t / 100) + 4:.1f}" text-anchor="end">{t}%</text>')
    for j in S["thresholds"]["risk_map_diagonals"]:
        s = 2 * (1 - j / 100)
        x0, y0 = (s, 0) if s <= 1 else (1, s - 1)
        x1, y1 = (0, s) if s <= 1 else (s - 1, 1)
        parts.append(f'<line class="rm-diag" x1="{x(x0):.1f}" y1="{y(y0):.1f}" x2="{x(x1):.1f}" y2="{y(y1):.1f}"/>'
                     f'<text class="rm-diag-label" x="{x((x0 + x1) / 2) + 3:.1f}" y="{y((y0 + y1) / 2) - 3:.1f}">{j}</text>')
    parts.append(f'<text x="{(L + W - R) / 2}" y="{H - 10}" text-anchor="middle">Risk pays without the right risk '
                 f'(missed + wrong risks): too cautious or wrong play \u2192</text>'
                 f'<text transform="translate(14 {(T + H - B) / 2}) rotate(-90)" text-anchor="middle">Needless risks: too bold \u2192</text>')
    total = 0.0
    for rank, (n, r, _, ref) in enumerate(rows_of(S, lg, phase, margin)):
        mp = r.get("map")
        if not mp:
            continue
        total += r["trade_off"]
        cx, cy = x(mp["x"]), y(mp["y"])
        ws = mp["wrong_share"] or 0
        tip = (f'{n}: risk judgement {fmt(r["judgement"])}; missed + wrong {pct(mp["x"])}, needless {pct(mp["y"])}; '
               f'wrong among them {pct(ws)}')
        mark = (f'<rect class="rm-ref" x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10"/>' if ref else
                f'<circle class="rm-dot" cx="{cx:.1f}" cy="{cy:.1f}" r="5.5" style="fill: color-mix(in srgb, var(--wrong) {100 * ws:.0f}%, var(--reading))"/>')
        anchor = "end" if mp["x"] > .7 else "start"
        dx = -8 if anchor == "end" else 8
        parts.append(f'<g class="pt"{attrs(S, ds, n, bool(ref))} data-n="{r["trade_off"]:.0f}" data-rank="{rank}">'
                     f'<title>{esc(tip)}</title>{mark}<text class="rm-name" x="{cx + dx:.1f}" y="{cy + 4:.1f}" '
                     f'text-anchor="{anchor}">{esc(n)}</text></g>')
    return _svg("riskmap", ds, margin, W, H, "".join(parts), f"Risk map of League {lg['id']} at the {MARGIN_LABEL[margin]} margin",
                0, 0, 0, total)


SPLIT_CLASS = {"needless": "sp-needless", "missed": "sp-missed", "wrong_risk": "sp-wrong", "right_risk": "sp-right",
               "right_safety": "sp-safety", "none": "sp-none"}


def bars_chart(S, lg, kind_, margin, rows, value, draw, label, axis_max, axis_fmt, legend="") -> str:
    """A horizontal bar chart, one row per setup; rows carry the filter attributes, and the page's script stacks the
    visible rows (default: the first TOP_N model setups by the chart's order plus the reference rows; Show all)."""
    ds = lg["dataset"]
    W, LW, TOP, RH = 640, 210, 22, 34
    x = lambda v: LW + (W - LW - 70) * v / axis_max
    ticks = [axis_max * k / 4 for k in range(5)]
    head = "".join(f'<line class="grid vfull" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{TOP - 4}" y2="{TOP + len(rows) * RH}"/>'
                   f'<text class="muted" x="{x(t):.1f}" y="12" text-anchor="middle">{axis_fmt(t)}</text>' for t in ticks)
    out, total = [], 0.0
    for rank, (n, r, q, ref, detail) in enumerate(rows):
        v = value(r, q)
        total += r["trade_off"] if r else 0
        inner = _label(n, detail, LW) + (draw(x, r, q) if v is not None else
                                         f'<text class="muted" x="{LW}" y="20">{esc(NA)}</text>')
        out.append(_row(S, ds, n, TOP + rank * RH, inner, r["trade_off"] if r else 0, rank, bool(ref)))
    H = TOP + len(rows) * RH + 6
    return _svg(kind_, ds, margin, W, H, head + "".join(out), label, len(rows), TOP, RH, total) + legend


def detail_of(S, lg, n, ref) -> str:
    if n in lg["references"]:
        return "reference, computed"
    if ref:
        return "reference"
    return settings_line(P.meta(S, lg["dataset"], n))


def split_chart(S, lg, margin, phase="all") -> str:
    rows = [(n, r, q, ref, detail_of(S, lg, n, ref)) for n, r, q, ref in rows_of(S, lg, phase, margin)]
    top = max((r["error_rate"] or 0) for _, r, *_ in rows) or 1
    axis = math.ceil(top / 10) * 10

    def draw(x, r, q):
        s, x0 = [], x(0)
        for k in SPLIT_ORDER:
            w = x(r["by_call"][k]) - x(0)
            s.append(f'<rect class="{SPLIT_CLASS[k]}" x="{x0:.1f}" y="8" width="{max(w, 0):.1f}" height="16">'
                     f'<title>{esc(CALL_LABEL[k])}: {fmt(r["by_call"][k], 2)}</title></rect>')
            x0 += w
        return "".join(s) + f'<text x="{x0 + 6:.1f}" y="20">{fmt(r["error_rate"])}</text>'
    legend = ('<p class="chart-legend">' + " ".join(f'<span><i class="swatch {SPLIT_CLASS[k]}"></i>{esc(CALL_LABEL[k])}</span>'
                                                     for k in SPLIT_ORDER) + "</p>")
    return bars_chart(S, lg, "split", margin, rows, lambda r, q: r["error_rate"], draw,
                      f"Error rate by risk-call category, League {lg['id']}", axis, lambda t: fmt(t, 0), legend)


def stake_chart(S, lg, margin, phase="all") -> str:
    rows = [(n, r, q, ref, f'big needless risks: {n_(r["needless_by_loss"]["big"]["n"])} of {n_(r["safety_pays"])}')
            for n, r, q, ref in rows_of(S, lg, phase, margin)]

    def draw(x, r, q):
        s = []
        for i, b in enumerate(A.BANDS):
            st = r["stake"][b]
            y0, x0 = 2 + i * 10, x(0)
            for k, cls in (("found", "sp-right"), ("wrong", "sp-wrong"), ("missed", "sp-missed")):
                v = st[k]["share"] or 0
                w = x(v) - x(0)
                s.append(f'<rect class="{cls}" x="{x0:.1f}" y="{y0}" width="{w:.1f}" height="8"><title>{esc(b)} stake: '
                         f'{k} {pct(st[k]["share"]) if st[k]["den"] else "0 / 0"} ({n_(st[k]["n"])} / {n_(st[k]["den"])})</title></rect>')
                x0 += w
        return "".join(s)
    legend = ('<p class="chart-legend"><span>Three bars per setup: small, medium, big stake (Risk pays only).</span> '
              '<span><i class="swatch sp-right"></i>risks found</span> <span><i class="swatch sp-wrong"></i>wrong risks</span> '
              '<span><i class="swatch sp-missed"></i>missed risks</span> <span>Under each name: needless risks that lost more than 0.08.</span></p>')
    return bars_chart(S, lg, "stake", margin, rows, lambda r, q: r["risk_pays"] or None, draw,
                      f"Risk calls by stake, League {lg['id']}", 1, lambda t: pct(t, 0), legend)


def close_chart(S, lg, margin) -> str:
    """Close choices by stake band, Risk pays only (Method spec 2026-10-24 §9.6): the Confidence table's order, never
    ranked by the share; N/A for setups without a full probability distribution."""
    rows = []
    for n in P.by_error(lg["setups"]):
        c = lg["setups"][n].get("close")
        ref = ref_label(S, lg["dataset"], n)
        if not c or c["na"]:
            rows.append((n, dict(trade_off=0, stake=None), None, ref, P.CC_NA))
            continue
        st = c["margins"][margin]["stake"]
        rp = c["margins"][margin]["classes"]["risk"]["eligible"]
        rows.append((n, dict(trade_off=rp, stake=st), None, ref, f"Risk pays: {count(rp)} eligible decisions"))

    def draw(x, r, q):
        s = []
        for i, b in enumerate(A.BANDS):
            v = r["stake"][b]
            y0 = 2 + i * 10
            if not v["den"]:
                s.append(f'<text class="muted" x="{x(0) + 2:.1f}" y="{y0 + 8}" font-size="8">{esc(b)}: {esc(NA)}</text>')
                continue
            s.append(f'<rect class="ccs-{b}" x="{x(0):.1f}" y="{y0}" width="{x(v["share"]) - x(0):.1f}" height="8">'
                     f'<title>{esc(b)} stake: {esc(P.cc_text(v))}</title></rect>')
        return "".join(s)
    legend = ('<p class="chart-legend"><span>Three bars per setup: small, medium, big stake (Risk pays only); each bar is '
              'the share of eligible decisions in that band that are close choices.</span> <span><i class="swatch ccs-small">'
              '</i>small</span> <span><i class="swatch ccs-medium"></i>medium</span> <span><i class="swatch ccs-big"></i>big</span> '
              '<span>Rows in the Confidence table\'s order, not ranked by this share. A big stake means playing safe costs more '
              'by the engine\'s value, not that the decision was harder.</span></p>')
    svg = bars_chart(S, lg, "closestake", margin, rows, lambda r, q: r["stake"], draw,
                     f"Close choices by stake band, League {lg['id']}", 1, lambda t: pct(t, 0), legend)
    note = CC_PNG_NOTE + S["close_spec"]["label"] + (" | " + P.SUBSET_NOTE if lg["dataset"] in P.SUBSET_DATASETS else "")
    return svg.replace('<svg class="chart-svg"', f'<svg class="chart-svg" data-note="{esc(note)}"', 1)


def pays_chart(S, lg) -> str:
    """Risk pays vs safety pays: risks found and right safety per setup, as two bars on one 0-100% axis."""
    rows = [(n, r, q, ref, detail_of(S, lg, n, ref)) for n, r, q, ref in rows_of(S, lg)]

    def draw(x, r, q):
        a, b = r["found"]["share"] or 0, r["right_safety"]["share"] or 0
        return (f'<rect class="sp-right" x="{x(0):.1f}" y="5" width="{x(a) - x(0):.1f}" height="11"><title>risks found '
                f'{pct(a)}</title></rect><text x="{x(a) + 4:.1f}" y="14">{pct(a, 0)}</text>'
                f'<rect class="sp-pays-safe" x="{x(0):.1f}" y="18" width="{x(b) - x(0):.1f}" height="11"><title>right safety '
                f'{pct(b)}</title></rect><text x="{x(b) + 4:.1f}" y="27">{pct(b, 0)}</text>')
    legend = ('<p class="chart-legend"><span><i class="swatch sp-right"></i>Risks found (Risk pays)</span> '
              '<span><i class="swatch sp-pays-safe"></i>Right safety (Safety pays)</span></p>')
    return bars_chart(S, lg, "pays", "main", rows, lambda r, q: r["judgement"], draw,
                      f"Risk pays vs safety pays, League {lg['id']}", 1, lambda t: pct(t, 0), legend)


def measure_chart(S, lg, which) -> str:
    ds = lg["dataset"]
    rows = []
    for n in P.by_error(lg["setups"]):
        q = lg["setups"][n]["quality"]
        r = lg["setups"][n]["risk"]["main"]
        ref = ref_label(S, ds, n)
        rows.append((n, r, q, ref, detail_of(S, lg, n, ref)))
    if which == "error":
        val = lambda r, q: q.get("error_rate") if not q.get("too_few") else None
        top = max((val(r, q) or 0) for _, r, q, *_ in rows)
        axis = math.ceil((max((q.get("error_hi") or 0) for _, r, q, *_ in rows) or 1) / 10) * 10

        def draw(x, r, q):
            return (f'<line class="whisker" x1="{x(q["error_lo"]):.1f}" x2="{x(q["error_hi"]):.1f}" y1="16" y2="16" stroke-width="2"/>'
                    f'<circle class="dot" cx="{x(q["error_rate"]):.1f}" cy="16" r="4"/>'
                    f'<text x="{x(q["error_hi"]) + 6:.1f}" y="20">{fmt(q["error_rate"])}</text>')
        return bars_chart(S, lg, "error", "main", rows, val, draw, f"Error rate (PR), League {lg['id']}", axis,
                          lambda t: fmt(t, 0))
    key, unit = ("time_median", "s") if which == "time" else ("usd_per_1000", "$")
    val = lambda r, q: q.get(key)
    top = max((q.get(key) or 0) for _, r, q, *_ in rows) or 1

    def draw(x, r, q):
        v = q[key]
        return (f'<rect class="sp-bar" x="{x(0):.1f}" y="9" width="{x(v) - x(0):.1f}" height="14"/>'
                f'<text x="{x(v) + 6:.1f}" y="20">{fmt(v, 2 if which == "time" else 3)}</text>')
    return bars_chart(S, lg, which, "main", rows, val, draw,
                      f"{'Median s per decision' if which == 'time' else '$ per 1,000 decisions'}, League {lg['id']}",
                      top * 1.15, lambda t: fmt(t, 1 if which == "time" else 2))


def tradeoff_chart(S, lg, which) -> str:
    """Error rate against cost or median time, log scale across."""
    ds = lg["dataset"]
    key = "usd_per_1000" if which == "cost" else "time_median"
    pts = [(n, s["quality"]) for n, s in lg["setups"].items()
           if s["quality"].get(key) and s["quality"].get("error_rate") is not None and not s["quality"].get("too_few")]
    W, H, L, T, R, B = 640, 360, 52, 14, 20, 44
    if not pts:
        return f'<p class="chart-status">{nm(NOT_MEASURED)} No setup in this league has a {esc("cost" if which == "cost" else "time")}.</p>'
    xs = [q[key] for _, q in pts]
    lo, hi = math.log10(min(xs) / 1.6), math.log10(max(xs) * 1.6)
    ymax = math.ceil(max(q["error_rate"] for _, q in pts) / 10 + .5) * 10
    x = lambda v: L + (W - L - R) * (math.log10(v) - lo) / (hi - lo)
    y = lambda v: H - B - (H - T - B) * v / ymax
    parts = []
    for p in range(math.floor(lo), math.ceil(hi) + 1):
        v = 10 ** p
        if lo <= p <= hi:
            parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{T}" y2="{H - B}"/>'
                         f'<text class="muted" x="{x(v):.1f}" y="{H - B + 14}" text-anchor="middle">{v:g}</text>')
    for t in range(0, ymax + 1, 10):
        parts.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                     f'<text class="muted" x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{t}</text>')
    parts.append(f'<text x="{(L + W - R) / 2}" y="{H - 8}" text-anchor="middle">'
                 f'{"$ per 1,000 decisions" if which == "cost" else "Median s per decision"}, log scale</text>'
                 f'<text transform="translate(13 {(T + H - B) / 2}) rotate(-90)" text-anchor="middle">Error rate (PR)</text>')
    for rank, (n, q) in enumerate(sorted(pts, key=lambda p: p[1]["error_rate"])):
        parts.append(f'<g class="pt"{attrs(S, ds, n)} data-n="{q["scored"]}" data-rank="{rank}"><title>{esc(n)}: '
                     f'{fmt(q["error_rate"])}</title><circle class="dot" cx="{x(q[key]):.1f}" cy="{y(q["error_rate"]):.1f}" r="4.5"/>'
                     f'<text class="rm-name" x="{x(q[key]) + 7:.1f}" y="{y(q["error_rate"]) + 4:.1f}">{esc(n)}</text></g>')
    return _svg(f"tradeoff-{which}", ds, "main", W, H, "".join(parts),
                f"Error rate against {which}, League {lg['id']}", 0, 0, 0, sum(q["scored"] for _, q in pts))


def sdt_chart(S, lg, margin, phase="all") -> str:
    """Item 4: ability d′ across, caution c up; programs and computed rows as squares; a short bar at c* only where the
    cost-derived SDT reference is valid (Method spec 2026-10-24 §2, rule 7)."""
    ds = lg["dataset"]
    pts = [(n, r, ref) for n, r, _, ref in rows_of(S, lg, phase, margin) if not r["sdt"]["na"]]
    if not pts:
        return f'<p class="chart-status">{nm(NA)}: no setup has both Risk pays and Safety pays decisions here.</p>'
    W, H, L, T, R, B = 640, 470, 56, 16, 20, 46
    xs = [r["sdt"]["dprime"] for _, r, _ in pts]
    ys = [r["sdt"]["caution"] for _, r, _ in pts] + [r["sdt"]["cstar"] for _, r, _ in pts if r["sdt"]["cstar_status"] == "valid"]
    x0, x1 = min(-0.5, math.floor(min(xs) * 2) / 2), max(2.0, math.ceil(max(xs) * 2) / 2)
    y0, y1 = min(-1.0, math.floor(min(ys) * 2) / 2), max(1.0, math.ceil(max(ys) * 2) / 2)
    x = lambda v: L + (W - L - R) * (v - x0) / (x1 - x0)
    y = lambda v: H - B - (H - T - B) * (v - y0) / (y1 - y0)
    parts = []
    for k in range(int(round(x0 * 2)), int(round(x1 * 2)) + 1):
        v = k / 2
        parts.append(f'<line class="grid{" axis0" if v == 0 else ""}" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{T}" y2="{H - B}"/>'
                     f'<text class="muted" x="{x(v):.1f}" y="{H - B + 14}" text-anchor="middle">{v:g}</text>')
    for k in range(int(round(y0 * 2)), int(round(y1 * 2)) + 1):
        v = k / 2
        parts.append(f'<line class="grid{" axis0" if v == 0 else ""}" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="muted" x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:+g}</text>')
    parts.append(f'<text x="{(L + W - R) / 2}" y="{H - 10}" text-anchor="middle">Ability d\u2032: tells Risk pays from '
                 f'Safety pays \u2192</text><text transform="translate(14 {(T + H - B) / 2}) rotate(-90)" '
                 f'text-anchor="middle">Caution c: + cautious, \u2212 bold</text>')
    total = 0.0
    for rank, (n, r, ref) in enumerate(pts):
        s = r["sdt"]
        total += r["trade_off"]
        cx, cy = x(s["dprime"]), y(s["caution"])
        tip = f'{n}: ability {fmt(s["dprime"], 2)}, caution {fmt(s["caution"], 2, True)}; SDT reference: ' + (
            fmt(s["cstar"], 2, True) if s["cstar_status"] == "valid" else (s["cstar_note"] or NA))
        mark = (f'<rect class="rm-ref" x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10"/>' if ref else
                f'<circle class="rm-dot" cx="{cx:.1f}" cy="{cy:.1f}" r="5.5"/>')
        if s["cstar_status"] == "valid":
            mark += (f'<line class="sdt-link" x1="{cx:.1f}" x2="{cx:.1f}" y1="{cy:.1f}" y2="{y(s["cstar"]):.1f}"/>'
                     f'<line class="sdt-ref" x1="{cx - 9:.1f}" x2="{cx + 9:.1f}" y1="{y(s["cstar"]):.1f}" y2="{y(s["cstar"]):.1f}"/>')
        anchor = "end" if cx > (L + W - R) * .7 else "start"
        dx = -8 if anchor == "end" else 8
        parts.append(f'<g class="pt"{attrs(S, ds, n, bool(ref))} data-n="{r["trade_off"]:.0f}" data-rank="{rank}">'
                     f'<title>{esc(tip)}</title>{mark}<text class="rm-name" x="{cx + dx:.1f}" y="{cy + 4:.1f}" '
                     f'text-anchor="{anchor}">{esc(n)}</text></g>')
    return _svg("sdt", ds, margin, W, H, "".join(parts),
                f"Ability and caution of League {lg['id']} at the {MARGIN_LABEL[margin]} margin", 0, 0, 0, total)


def risk_panel_body(S, lg, phase="all") -> str:
    out = []
    for m in ("main", "robust"):
        out.append(f'<div class="chart-view" data-view-chart="riskmap" data-view-margin="{m}">{risk_map(S, lg, m, phase)}'
                   '<p class="chart-legend"><span><i class="swatch rm-cautious"></i>missed risks</span> '
                   '<span><i class="swatch rm-wrong"></i>wrong risks</span> <span>colour: share of wrong risks among the '
                   'Risk pays decisions without the right risk · squares: reference rows · diagonals: risk judgement</span></p></div>')
        out.append(f'<div class="chart-view" data-view-chart="split" data-view-margin="{m}">{split_chart(S, lg, m, phase)}</div>')
        out.append(f'<div class="chart-view" data-view-chart="stake" data-view-margin="{m}">{stake_chart(S, lg, m, phase)}</div>')
        out.append(f'<div class="chart-view" data-view-chart="sdt" data-view-margin="{m}">{sdt_chart(S, lg, m, phase)}'
                   '<p class="chart-legend"><span>circles: model setups · squares: programs and computed reference rows · '
                   '<i class="swatch sdt-swatch"></i>short bar: the cost-derived SDT reference c*, drawn only where it is '
                   f'valid</span></p><p class="chart-legend">{esc(SDT_LIMIT)} {esc(SDT_COSTS)}</p></div>')
    return "".join(out)


# --- Views (one per league; phase fragments) -------------------------------------------------------------

def league_badge(lg) -> str:
    return P.league_status_text(lg)


def phase_slots(S, lg, phase) -> dict:
    return {"risk": risk_table(S, lg, phase) + robust_table(S, lg, phase), "quality": quality_table(S, lg, phase),
            "chart-risk": risk_panel_body(S, lg, phase)}


def slot(lg, name, html) -> str:
    return f'<div class="phase-slot" data-slot="{name}" data-dataset="{lg["dataset"]}">{html}</div>'


def fragments(S, out) -> None:
    """fragments/<league>-<phase>.html: the phase-dependent parts of a league view, loaded by the Phase filter."""
    folder = out / "fragments"
    if folder.exists():
        for old in folder.glob("*.html"):
            old.unlink()
    folder.mkdir(exist_ok=True)
    for lg in S["leagues"]:
        for ph in A.PHASES:
            parts = "".join(slot(lg, k, v) for k, v in phase_slots(S, lg, ph).items())
            (folder / f"{lg['dataset']}-{ph}.html").write_text(
                f'<div data-league-view="{lg["dataset"]}" data-dataset="{lg["dataset"]}">{prov_note(lg)}{parts}</div>\n')


def prov_note(lg) -> str:
    """The Provisional label every block of a running league carries (brief B10)."""
    return f'<p class="table-note">{esc(PROVISIONAL_NOTE)}</p>' if lg["metric_status"] == PROVISIONAL else ""


def league_block(lg, inner: str) -> str:
    """One league's block outside the league switcher (Method page): its dataset plus the Provisional label if running."""
    return f'<div data-dataset="{lg["dataset"]}">{prov_note(lg)}{inner}</div>'


def view(S, lg, inner: str) -> str:
    off = "" if lg["dataset"] == default_league(S) else " data-off"
    prov = prov_note(lg)
    return f'<div class="league-view" data-league-view="{lg["dataset"]}" data-dataset="{lg["dataset"]}"{off}>{prov}{inner}</div>'


def shared_view(S, what: str) -> str:
    return (f'<div class="league-view" data-league-view="shared" data-off><p class="pending">{status_badge(PENDING)} '
            f'Shared positions: {esc(what)}</p></div>')


def default_league(S) -> str:
    return S["leagues"][0]["dataset"]


def tab_body(S, key: str) -> str:
    out = []
    for lg in S["leagues"]:
        if key == "risk":
            inner = slot(lg, "risk", risk_table(S, lg) + robust_table(S, lg))
            extra = reasoning_sdt_table(S, lg)
            if extra:
                inner += extra + '<p class="table-note">The Phase filter does not apply to this table: all phases.</p>'
        elif key == "quality":
            inner = slot(lg, "quality", quality_table(S, lg)) + f'<p class="table-note">{esc(LIMIT_PAIRED)}</p>'
        elif key == "confidence":
            inner = confidence_table(S, lg) + close_details(S, lg) + offline_confidence(S, lg)
        elif key == "reasoning":
            inner = P.league_reasoning_table(S, lg)
        elif key == "cost":
            inner = cost_table(S, lg) + cheapest_section(S, lg)
        else:
            inner = f'<p class="pending">{status_badge(NOT_MEASURED)} League games never repeat a position.</p>'
        if key in ("confidence", "reasoning", "cost", "stability"):
            inner += '<p class="table-note phase-all" hidden>The Phase filter does not apply to this tab: all phases.</p>'
        out.append(view(S, lg, inner))
    out.append(shared_view(S, "Analysis pending; no setup has answered them yet."))
    caption = {
        "risk": "Risk calls per setup: was each risk the right one, and was safe right when it played safe?",
        "quality": "How much equity each move gives away, judged by the engine, not by wins.",
        "confidence": "Does a setup's probability show when its play is likely wrong?",
        "reasoning": "The same model at a lower and a higher reasoning setting, each named by the effort its requests sent.",
        "cost": "Dollars per 1,000 decisions and seconds per decision.",
        "stability": "Does a setup repeat its play on the same position?"}[key]
    marks = ('<p class="table-note">\u00a7 list-price estimate; runs on our GPUs · \u2020 plays split into groups · '
             f'{esc(NOT_MEASURED)}: no value recorded. <a href="method/#{key}">Method</a></p>')
    return f'<p class="version-line">{esc(caption)}</p>' + "".join(out) + marks + f'<p class="table-note">{esc(LIMIT_PAIRED)}</p>'


# --- Hero, findings, filters -------------------------------------------------------------------------------

def version_line(S) -> str:
    return P.version_line(S)


def champions(S) -> str:
    items = []
    for lg in S["leagues"]:
        w = lg.get("winner")
        val = (f'<a href="{P.model_href("", lg["dataset"], w, S)}">{esc(w)}</a>' if w else nm(lg["status"]))
        items.append(f'<li class="readout"><span class="readout-label">League {lg["id"]}:</span> <span class="readout-value champ">{val}</span></li>')
    # The Hype Cup champion: the cross-league champion (an event, not a ranking: the Cup card says so).
    c = S["cup"]
    val = f'<a href="leagues/#hype-cup">{esc(c["champion"])}</a>' if c["champion"] else nm("To play")
    items.append(f'<li class="readout"><span class="readout-label">Hype Cup:</span> <span class="readout-value champ">{val}</span></li>')
    return (f'<div class="readout-row champions"><span class="readout-label">League winners · match results</span>'
            f'<ul class="readouts">{"".join(items)}</ul></div>')


CALL_WORDS = {"right_risk": "a right risk", "wrong_risk": "a wrong risk", "missed": "a missed risk",
              "needless": "a needless risk", "right_safety": "right safety"}


def hero_board(S) -> str:
    sc = S.get("showcase")
    if not sc:
        return ""
    from board import board_svg
    b, s, c = sc["best"], sc["best_safe"], sc["chosen"]
    svg = board_svg(sc["board"], sc["dice"], sc["pips"], play=b["notation"], alt=s["notation"], cls="bd hero-bd",
                    label_extra=f"Solid arrows: the engine's best play, {b['notation']}. Dashed: the best safe play, {s['notation']}.")
    code = lambda p: f'<code>{esc(p["notation"])}</code>'
    text = (f'{esc(sc["label"])}, dice {sc["dice"][0]}-{sc["dice"][1]}, stake {P.eq(sc["stake"])}: the engine\'s best play '
            f'{code(b)} leaves {count(b["hitting_rolls"])} hitting rolls, the best safe play {code(s)} (dashed) '
            f'leaves {count(s["hitting_rolls"])}. {esc(sc["who"])} played {code(c)}: {esc(CALL_WORDS[sc["call"]])}.')
    href = f'decisions/?d={sc["dataset"]}&amp;s={sc["slug"]}&amp;p={sc["page"]}#d{sc["id"]}'
    return f'<figure class="hero-board">{svg}<figcaption>{text} <a href="{href}">Open this decision</a></figcaption></figure>'


def findings_block(S) -> str:
    import findings as F
    approved = F.published()
    lead = F.lead_in()
    if not approved or not lead:
        return '<div class="summary" id="findings"><p class="summary-lead findings-wait">Findings will be published after review.</p></div>'
    items = "".join(f'<li><a href="?tab={esc(f["tab"])}#board" data-goto-tab="{esc(f["tab"])}">{esc(f["label"])}</a>: '
                    f'{esc(f["text"])}</li>' for f in approved)
    return (f'<div class="summary" id="findings"><p class="summary-lead">{esc(lead["text"])}</p>'
            f'<ul class="summary-list">{items}</ul></div>')


def filters(S) -> str:
    def keys(name, values, current="all"):
        return "".join(f'<button type="button" class="key" data-filter-{name}="{esc(v)}" aria-pressed="{str(v == current).lower()}">'
                       f'<span class="lamp" aria-hidden="true"></span>{esc(l)}</button>' for v, l in values)

    def group(name, label, values):
        return (f'<div class="group" role="group" aria-labelledby="f-{name}"><span class="group-label" id="f-{name}">{label}</span>'
                f'<span class="keys" data-control="{name}">{keys(name, values)}</span></div>')
    ms = [P.meta(S, lg["dataset"], n) for lg in S["leagues"] for n in lg["setups"]]
    cap = lambda v: v[:1].upper() + v[1:]
    settings = [("all", "All")] + [(v, cap(v)) for v in sorted({m["setting"] for m in ms if m.get("setting")})] + [("none", "None")]
    runs = [("all", "All")] + [(v, cap(v)) for v in sorted({m["runs_on"] for m in ms if m.get("runs_on")})]
    weights = [("all", "All")] + [(v, cap(v)) for v in sorted({m["weights"] for m in ms if m.get("weights")})]
    leagues = "".join(f'<button type="button" class="key" data-league-pick="{lg["dataset"]}" aria-pressed="'
                      f'{str(lg["dataset"] == default_league(S)).lower()}"><span class="lamp" aria-hidden="true"></span>League {lg["id"]}</button>'
                      for lg in S["leagues"])
    leagues += ('<button type="button" class="key" data-league-pick="shared" aria-pressed="false"><span class="lamp" '
                f'aria-hidden="true"></span>Shared positions</button>')
    phases = "".join(f'<option value="{p}">{esc(P.PHASE_LABEL[p])}</option>' for p in A.PHASES)
    totals = {lg["dataset"]: len(lg["setups"]) for lg in S["leagues"]}
    # The league and the model type stay in view; phase, reasoning, runs on and weights fold behind "More filters", whose
    # key names the active ones while it is closed (bg.js).
    return f"""<section class="panel filters is-open needs-js" id="filters" aria-labelledby="filters-title">
      <h2 id="filters-title" class="filters-title">Filters</h2>
      <div class="filters-body" id="filters-body">
        <div class="group league-pick" role="group" aria-labelledby="f-league"><span class="group-label" id="f-league">League</span><span class="keys">{leagues}</span></div>
        {group("kind", "Model type", [("all", "All"), ("decision", "Decision"), ("chat", "Chat"), ("program", "Program")])}
        <div class="group more-filters"><button type="button" class="key fold-toggle" data-more-filters aria-expanded="false" aria-controls="filters-more"><span class="chevron" aria-hidden="true"></span>More filters<span class="fold-summary" data-more-summary> · phase, reasoning, runs on, weights</span></button></div>
        <div class="filters-more" id="filters-more" hidden>
          <label class="group"><span class="group-label">Phase</span> <select data-control="phase"><option value="all">All phases</option>{phases}</select></label>
          {group("setting", "Reasoning", settings)}{group("runs", "Runs on", runs)}{group("weights", "Weights", weights)}
        </div>
        <div class="group"><span class="setup-count" data-setups data-totals='{esc(json.dumps(totals))}' aria-live="polite">{count(totals[default_league(S)])} of {count(totals[default_league(S)])} setups</span>
        <button type="button" class="key reset" data-control="reset" aria-disabled="true" data-tip="Nothing to reset: the filters show the defaults.">Reset</button>
        <span class="small reset-why" data-reset-why>Nothing to reset: the filters show the defaults.</span></div>
      </div>
    </section>"""


# --- Chart panels ----------------------------------------------------------------------------------------------

def chart_panel(pid: str, title: str, tabs: list[tuple[str, str]], body: str, margins=False, note: str = "") -> str:
    keys = "".join(f'<button type="button" class="key" data-chart-tab="{k}" aria-pressed="{str(i == 0).lower()}">'
                   f'<span class="lamp" aria-hidden="true"></span>{esc(l)}</button>' for i, (k, l) in enumerate(tabs))
    mk = ("".join(f'<button type="button" class="key" data-chart-margin="{m}" aria-pressed="{str(m == "main").lower()}">'
                  f'<span class="lamp" aria-hidden="true"></span>margin {MARGIN_LABEL[m]}</button>' for m in ("main", "robust"))
          if margins else "")
    return (f'<figure class="panel chart-card" id="{pid}" data-chart-panel><div class="chart-head"><h2>{esc(title)}</h2>'
            f'<span class="keys">{keys}</span>{f"<span class=keys>{mk}</span>" if mk else ""}'
            f'<button type="button" class="key" data-download>Download PNG</button></div>{body}{note}'
            f'<p class="chart-more"><button type="button" class="key" data-show-all aria-pressed="false"><span class="lamp" '
            f'aria-hidden="true"></span><span data-show-all-label>Show all</span></button></p></figure>')


def charts(S) -> str:
    risk = "".join(view(S, lg, slot(lg, "chart-risk", risk_panel_body(S, lg))) for lg in S["leagues"])
    risk += shared_view(S, "Analysis pending.")
    cards = " · ".join(f'<a href="{S["risk_cards"][lg["dataset"]]}">League {lg["id"]}: {esc(lg["winner"])}</a>'
                       for lg in S["leagues"] if S.get("risk_cards", {}).get(lg["dataset"]))
    risk_note = (f'<p class="table-note">{esc(LIMIT_HIT)}</p>'
                 + (f'<p class="table-note">Risk call card of each league winner (PNG, 1200\u00d7675): {cards}</p>' if cards else ""))
    measures = "".join(view(S, lg, "".join(f'<div class="chart-view" data-view-chart="{k}" data-view-margin="main">{measure_chart(S, lg, k)}</div>'
                                           for k in ("error", "time", "cost"))) for lg in S["leagues"]) + shared_view(S, "Analysis pending.")
    trade = "".join(view(S, lg, "".join(f'<div class="chart-view" data-view-chart="tradeoff-{k}" data-view-margin="main">{tradeoff_chart(S, lg, k)}</div>'
                                        for k in ("cost", "time"))) for lg in S["leagues"]) + shared_view(S, "Analysis pending.")
    paired = f'<p class="table-note">{esc(LIMIT_PAIRED)} Charts cover all phases except the Risk panel.</p>'
    conf = "".join(view(S, lg, P.subset_note(lg["dataset"]) + "".join(
        f'<div class="chart-view" data-view-chart="closestake" data-view-margin="{m}">{close_chart(S, lg, m)}</div>'
        for m in ("main", "robust")))
                   for lg in S["leagues"]) + shared_view(S, "Analysis pending.")
    conf_note = (f'<p class="table-note cc-label">{esc(S["close_spec"]["label"])} {esc(S["close_spec"]["definition"])} '
                 f'{esc(NA)} for setups without a full probability distribution. <a href="method/#close-choices">Method</a></p>')
    return ('<section class="charts" id="charts" aria-label="Charts" tabindex="-1">'
            + chart_panel("chart-risk", "Risk", [("riskmap", "Risk map"), ("split", "Error rate by risk-call category"),
                                                 ("stake", "Stake chart"), ("sdt", "Ability and caution")], risk, True,
                          risk_note)
            + chart_panel("chart-measures", "Error rate, time and cost", [("error", "Error rate"), ("time", "Time"),
                                                                           ("cost", "Cost")], measures, False, paired)
            + chart_panel("chart-tradeoff", "Trade-off", [("tradeoff-cost", "Cost"), ("tradeoff-time", "Time")], trade,
                          False, paired)
            + chart_panel("chart-confidence", "Confidence", [("closestake", "Close choices by stake band")], conf, True,
                          conf_note)
            + "</section>")


def pays_section(S) -> str:
    lines = []
    for lg in S["leagues"]:
        rows = [(n, s["risk"]["main"]) for n, s in lg["setups"].items() if not ref_label(S, lg["dataset"], n)
                and kind(P.meta(S, lg["dataset"], n)) != "program" and s["risk"]["main"]["judgement"] is not None]
        if not rows:
            continue
        f = [r["found"]["share"] for _, r in rows]
        s = [r["right_safety"]["share"] for _, r in rows]
        lines.append(f'<li>League {lg["id"]}: model setups found {pct(min(f), 0)} to {pct(max(f), 0)} of the risks that paid, '
                     f'and played safe in {pct(min(s), 0)} to {pct(max(s), 0)} of the positions where safety paid.</li>')
    chart = "".join(view(S, lg, pays_chart(S, lg)) for lg in S["leagues"])
    return (f'<section class="card" id="risk-pays-vs-safety-pays"><div class="section-head"><h2>Risk pays vs safety pays</h2></div>'
            f'<ul class="league-notes">{"".join(lines)}</ul>'
            f'<figure class="chart-card" data-chart-panel>{chart}<p class="table-note">{esc(LIMIT_HIT)} {esc(LIMIT_PAIRED)}</p></figure></section>')


# --- Close choices, stage B (Method spec 2026-10-24 §9.9-9.13): repeated answers, its own section --------------------

CCB_VS = {"above": "above the baseline range", "within": "inside the baseline range: not clearly above it",
          "below": "below the baseline range"}
CCB_SHORT = {"above": "above", "within": "inside", "below": "below"}
CCB_TITLE = "Can a model predict where it will waver?"
CCB_SUBTITLE = "Close choices: does a setup know where it hesitates?"
CCB_RANKING = ("Not a ranking: each team is compared with its own shuffled baseline, never with another team. Rows are in "
               "fixed alphabetical order and the table cannot be sorted.")


def ccb_cells(B) -> dict:
    """The published value of every cell of a team's row, keyed as in the table (close_choices_b_verify.py reads these
    keys back from the page)."""
    out = {}
    for t in B["complete"]:
        e, o = t["primary_exact"], t["secondary_overlap"]
        out[t["team"]] = dict(
            scored=count(t["scored"]), exact=fmt(e["observed"], 2),
            exact_baseline=f'{fmt(e["baseline_mean"], 3)} [{fmt(e["baseline_lo"], 2)}, {fmt(e["baseline_hi"], 2)}]',
            exact_p=fmt(e["p"], 3), exact_vs=CCB_VS[e["vs_baseline"]], overlap=fmt(o["observed"], 3),
            overlap_baseline=f'{fmt(o["baseline_mean"], 3)} [{fmt(o["baseline_lo"], 3)}, {fmt(o["baseline_hi"], 3)}]',
            overlap_p=fmt(o["p"], 3), overlap_vs=CCB_VS[o["vs_baseline"]], same_play=count(t["same_play"]),
            changed_same_features=count(t["changed_same_features"]), observed_nonempty=count(t["observed_nonempty"]),
            predicted_size_mean=fmt(t["predicted_size_mean"], 2),
            excluded="; ".join(f"{r}: {count(n)}" for r, n in t["excluded"].items()) or "none")
    return out


CCB_COLS = [("scored", "Positions scored"), ("exact", "Exact agreement (primary score)"),
            ("exact_baseline", "Shuffled baseline, mean [2.5\u201397.5%]"), ("exact_p", "p"),
            ("exact_vs", "Exact agreement against its baseline"), ("overlap", "Partial overlap (secondary score)"),
            ("overlap_baseline", "Shuffled baseline, mean [2.5\u201397.5%]"), ("overlap_p", "p"),
            ("overlap_vs", "Partial overlap against its baseline"), ("same_play", "Same play in all 5 answers"),
            ("changed_same_features", "Play changed, features identical"),
            ("observed_nonempty", "Positions where a feature changed"),
            ("predicted_size_mean", "Features predicted per position, mean"), ("excluded", "Left out, by reason")]


CCB_TEXT = {"exact_vs", "overlap_vs", "excluded"}


def close_b_chart(B) -> str:
    """Per team: exact agreement (dot) against its own shuffled baseline (band 2.5-97.5%, tick at the mean); rows in the
    table's fixed alphabetical order."""
    W, LW, TOP, RH = 640, 210, 22, 34
    rows = B["complete"]
    cells = ccb_cells(B)
    top = max([max(t["primary_exact"]["baseline_hi"], t["primary_exact"]["observed"]) for t in rows] or [0.1])
    axis = math.ceil(top * 10 + 1e-9) / 10
    x = lambda v: LW + (W - LW - 70) * v / axis
    ticks = [axis * k / 4 for k in range(5)]
    parts = [f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{TOP - 4}" y2="{TOP + len(rows) * RH}"/>'
             f'<text class="muted" x="{x(t):.1f}" y="12" text-anchor="middle">{fmt(t, 2)}</text>' for t in ticks]
    for i, t in enumerate(rows):
        e, c = t["primary_exact"], cells[t["team"]]
        tip = f'{t["team"]}: exact agreement {c["exact"]}; shuffled baseline {c["exact_baseline"]}; p {c["exact_p"]}; {c["exact_vs"]}'
        parts.append(
            f'<g class="ccb-row" transform="translate(0 {TOP + i * RH})" data-team="{esc(t["team"])}" data-observed="{e["observed"]}" '
            f'data-baseline-mean="{e["baseline_mean"]}" data-baseline-lo="{e["baseline_lo"]}" data-baseline-hi="{e["baseline_hi"]}">'
            f'<title>{esc(tip)}</title>' + _label(t["team"], f'p {c["exact_p"]}, {CCB_SHORT[e["vs_baseline"]]} the range', LW)
            + f'<rect class="ccb-band" x="{x(e["baseline_lo"]):.1f}" y="9" width="{max(x(e["baseline_hi"]) - x(e["baseline_lo"]), 1):.1f}" height="14"/>'
            f'<line class="ccb-mean" x1="{x(e["baseline_mean"]):.1f}" x2="{x(e["baseline_mean"]):.1f}" y1="6" y2="26"/>'
            f'<circle class="ccb-dot ccb-{e["vs_baseline"]}" cx="{x(e["observed"]):.1f}" cy="16" r="5.5"/>'
            f'<text x="{x(max(e["observed"], e["baseline_hi"])) + 9:.1f}" y="20">{c["exact"]}</text></g>')
    H = TOP + len(rows) * RH + 6
    note = " | ".join(" | ".join(textwrap.wrap(s, 110)) for s in (
        f'{B["title"]}. {CCB_SUBTITLE}',
        "Exact agreement (primary score) per team: dot = share of positions where the predicted feature set equals the "
        "observed one; band = the team's own predictions shuffled within phase, 2.5\u201397.5%; tick = baseline mean.",
        "Filled dot: above the band. Hollow dot: inside it, not clearly above the baseline (which does not make it equal "
        "to the baseline).", CCB_RANKING, CLOSE_B_SCOPE_NOTE))
    return (f'<svg class="chart-svg" data-chart="closeb" data-note="{esc(note)}" viewBox="0 0 {W} {H}" width="{W}" '
            f'height="{H}" role="img" aria-label="{esc(B["title"])}: exact agreement against the shuffled baseline">'
            + "".join(parts) + "</svg>")


def close_b_section(S) -> str:
    B = S["close_b"]
    done = B["complete"]
    head = [("Team and setting", " data-nosort"), ("Temperature", " data-nosort")] + [(l, " data-nosort") for _, l in CCB_COLS]
    cells = ccb_cells(B)
    rows = []
    for t in done:
        tp = t["temperature"]
        temp = (f'known: {esc(tp["value"])}' if tp["known"] else "not disclosed") + f'<span class="small">{esc(tp["text"])}</span>'
        rows.append(f'<tr data-team="{esc(t["team"])}"><th scope="row">{esc(t["team"])}<span class="small">{esc(t["setting"])}</span></th>'
                    f'<td data-k="temperature">{temp}</td>'
                    + "".join(f'<td{"" if k in CCB_TEXT else " class=num"} data-k="{k}">{esc(cells[t["team"]][k])}</td>'
                              for k, _ in CCB_COLS) + "</tr>")
    notes = [CCB_RANKING,
             "A change, or no change, across five answers doesn't measure the model's whole behaviour.",
             "Against its baseline: above the range = the observed mean is above the baseline's 97.5% point. Inside the "
             "range = not clearly above the baseline; a result that is not significant is not evidence that the team "
             "equals its baseline."]
    if done and all(2 * t["observed_nonempty"] < t["scored"] for t in done):
        lo, hi = min(t["same_play"] for t in done), max(t["same_play"] for t in done)
        notes.append(f"Most positions have no changed feature: the five answers chose the same play ({count(lo)}\u2013"
                     f"{count(hi)} positions per team), or changed play without changing a feature. So much of each score "
                     "comes from predicting \u201cnone\u201d where the team does not hesitate.")
    det = [t["team"] for t in done if t["deterministic"]]
    notes.append(f'Deterministic on these positions (the same play in all five answers everywhere): {", ".join(det)}.' if det
                 else "No team gave the same play in all five answers on every scored position.")
    notes.append("Every team kept its league settings. Temperature: the value sent or the provider's documented default "
                 "where known, otherwise not disclosed.")
    return (f'<section class="card" id="close-choices-stage-b"><div class="section-head"><h2>{esc(CCB_TITLE)}</h2></div>'
            f'<p class="section-label">{esc(B["title"])}</p>'
            f'<p class="subtitle-line"><strong>{esc(CCB_SUBTITLE)}</strong></p>'
            f'<p class="note"><strong>Scope.</strong> {esc(CLOSE_B_SCOPE_NOTE)}</p>'
            f'<p>Each team answered the same {count(B["positions"])} positions {count(B["repeats"])} times, and once more in '
            f'a separate call naming the features it expects to differ between the plays it might choose (hitting risk, '
            f'making a point, the race, the prime). Observed set: the features that differ between any of the '
            f'{count(B["repeats"])} chosen plays. <strong>Primary score</strong>: exact agreement of the predicted set with '
            f'the observed set. <strong>Secondary score</strong>, declared secondary: partial overlap of the two sets. '
            f'Baseline: the team\'s own predictions shuffled within phase, {count(B["baseline_shuffles"])} seeded shuffles; '
            f'p = the share of shuffles scoring at least the observed mean. Stage B asks again and looks at repeated '
            f'answers; it is separate from stage A (Confidence tab), which reads recorded league decisions.</p>'
            + P.SWIPE + P.table(head, rows, f'{esc(B["title"])}: per team, against its own shuffled baseline',
                                cls="board list", attrs=' id="close-b-table"')
            + "".join(f'<p class="table-note">{esc(n)}</p>' for n in notes)
            + '<figure class="chart-card" data-static-chart id="chart-close-b"><div class="chart-head">'
              '<h3>Exact agreement against the shuffled baseline</h3>'
              '<button type="button" class="key" data-download-static>Download PNG</button></div>'
            + close_b_chart(B)
            + '<p class="chart-legend"><span><i class="swatch ccb-band"></i>shuffled baseline, 2.5\u201397.5%</span> '
              '<span><i class="swatch ccb-mean"></i>baseline mean</span> <span><i class="swatch ccb-dot ccb-above"></i>'
              'exact agreement, above the range</span> <span><i class="swatch ccb-dot ccb-within"></i>inside the range: not '
              'clearly above</span> <span>Each team against its own baseline; not a ranking.</span></p></figure>'
            + f'<p class="table-note">Data: <a href="data/v3/close-choices-b.json" download="close-choices-b.json">'
              f'close-choices-b.json</a> · <a href="method/#close-choices-b">Method</a> ({esc(B["method"])})</p></section>')


def home(S) -> str:
    tabs = "".join(f'<button type="button" role="tab" id="tab-{k}" class="mode" aria-controls="board" '
                   f'aria-selected="{str(i == 0).lower()}" data-tab="{k}"><span class="lamp" aria-hidden="true"></span>{l}</button>'
                   for i, (k, l) in enumerate(TABS))
    panels = "".join(f'<div class="tabpanel" id="panel-{k}" data-panel="{k}"{" hidden" if i else ""}>{tab_body(S, k)}</div>'
                     for i, (k, _) in enumerate(TABS))
    return f"""
    <header class="hero hero-split">
      <div class="hero-text">
        <h1>{esc(P.TITLE)}</h1>
        <p class="subtitle">{esc(P.SUBTITLE)}</p>
        <p class="intro">{esc(INTRO)}</p>
        <div class="readout-row">
          <ul class="readouts">{P.readouts(S)}</ul>
          <p class="version">{esc(version_line(S))}</p>
        </div>
        {champions(S)}
      </div>
      {hero_board(S)}
    </header>
    {findings_block(S)}
    {filters(S)}
    <section class="panel board-panel" id="board-panel" aria-labelledby="board-title">
      <div class="section-head"><h2 id="board-title">Leaderboard</h2></div>
      <div class="modebar">
        <div class="keys view-switch needs-js" role="group" aria-label="Show the results as"><button type="button" class="key" data-view="table" aria-pressed="true"><span class="lamp" aria-hidden="true"></span>Table</button><button type="button" class="key" data-view="charts" aria-pressed="false"><span class="lamp" aria-hidden="true"></span>Charts</button></div>
        <div class="modes" role="tablist" aria-label="Leaderboard">{tabs}</div>
      </div>
      <div id="board" role="tabpanel">{panels}</div>
      {charts(S)}
    </section>
    {pays_section(S)}
    {close_b_section(S)}
    <p class="downloads" id="downloads">Download: <a href="data/results.json" download="results.json">results.json</a> · <a href="decisions/index.json" download="decisions.json">decisions.json</a></p>"""


# --- Risk call card (B6.5): one image per league winner, made to post on X ---------------------------------------

def risk_call_card(S, lg, css: str) -> str | None:
    w = lg.get("winner")
    if not w:
        return None
    r = lg["setups"][w]["risk"]["main"]
    if r["judgement"] is None:
        return None
    top = max(r["calls"].values()) or 1
    bars = "".join(
        f'<div class="cc-row"><span class="cc-l">{esc(CALL_LABEL[k] if k != "right_safety" else "right safety")}</span>'
        f'<span class="cc-bar {SPLIT_CLASS[k]}" style="width:{560 * r["calls"][k] / top:.0f}px"></span>'
        f'<span class="cc-n">{n_(r["calls"][k])}</span></div>'
        for k in ("right_risk", "wrong_risk", "needless", "missed", "right_safety"))
    return f"""<!doctype html><html data-theme="dark"><head><meta charset="utf-8"><style>
{css}
body{{margin:0;width:1200px;height:675px;background:var(--bg);color:var(--text);font-family:var(--sans);padding:40px 56px;box-sizing:border-box;position:relative}}
h1{{font-size:34px;margin:0 0 4px}} .sub{{font-size:19px;color:var(--text-2);margin:0 0 18px}} .site{{font-size:17px;font-weight:700;color:var(--text-2);margin:0 0 8px}}
.big{{font-size:120px;font-weight:700;line-height:1;margin:0}} .big small{{font-size:24px;font-weight:400;color:var(--text-2);margin-left:14px}}
.parts{{font-size:20px;color:var(--text-2);margin:6px 0 22px}}
.cc-row{{display:flex;align-items:center;gap:14px;margin:7px 0;font-size:20px}} .cc-l{{width:170px;text-align:right}} .cc-bar{{height:24px;border-radius:3px;display:inline-block}}
.f{{position:absolute;bottom:24px;left:56px;right:56px;font-size:15px;color:var(--text-2)}}
</style></head><body><p class="site">{esc(P.TITLE)} {esc(P.SUBTITLE)}</p><h1>{esc(w)}: risk judgement</h1>
<p class="sub">League {lg["id"]} winner (match results) · {n_(r["trade_off"])} decisions with a trade-off · margin 0.001</p>
<p class="big">{fmt(r["judgement"])}<small>95% interval {fmt(r["judgement_lo"])} to {fmt(r["judgement_hi"])} · 100 = every call right, 50 = always safe</small></p>
<p class="parts">Risks found {pct(r["found"]["share"])} ({n_(r["found"]["n"])} / {n_(r["found"]["den"])}) · right safety {pct(r["right_safety"]["share"])} ({n_(r["right_safety"]["n"])} / {n_(r["right_safety"]["den"])})</p>
{bars}
<div class="f">{esc(LIMIT_HIT)}<br>Results {esc(S["hash"])}, {esc(P.as_of(S))} · GNU Backgammon 1.08, 2-ply · {esc(S["base"])}</div></body></html>"""


# --- Method sections fed from the results (B4 moves them off the home page; B6.6 robustness; B6.7) -------------

def method_extras(S) -> dict:
    rel = "../"
    robust, held, tail = [], [], []
    for lg in S["leagues"]:
        ds = lg["dataset"]
        rows = []
        for n, r, _, ref in rows_of(S, lg):
            rr = (lg["setups"][n] if n in lg["setups"] else lg["references"][n])["risk"]["robust"]
            two = lambda a, b: (f'<td class="num">{a}<span class="small">0.02: {b}</span></td>')
            j = lambda x: fmt(x["judgement"]) if x["judgement"] is not None else x["judgement_na"]
            s = lambda x: pct(x["share"]) if x["den"] else "0 / 0"
            name = (f'<td class="model"><span class="model-name">{esc(n)}</span><span class="small">reference</span></td>'
                    if n in lg["references"] else P.model_cell(S, rel, ds, n))
            rows.append(f'<tr{attrs(S, ds, n, bool(ref))}>{name}' + two(esc(j(r)), esc(j(rr)))
                        + "".join(two(s(r[k]), s(rr[k])) for k in ("found", "right_safety", "missed", "needless", "wrong"))
                        + "</tr>")
        robust.append(f'<h4 id="robust-{ds}">League {lg["id"]}</h4>' + league_block(lg, P.SWIPE + P.table(
            ["Model and setting", "Risk judgement", "Risks found", "Right safety", "Missed risks", "Needless risks",
             "Wrong risks"], rows, "Margin 0.001 (large) and 0.02 (small)", attrs=f' data-dataset="{ds}" data-margin="0.001 and 0.02"')))
        hrows = []
        for n in P.by_error(lg["setups"]):
            c = lg["setups"][n].get("confidence")
            if not c:
                continue
            h = c["held_out"]
            cells = (f'<td class="num">{pct(h["kept"]) if h["kept"] is not None else nm(NA)}</td>'
                     f'<td class="num">{pct(h["blunders"]) if h["blunders"] is not None else nm(NA)}</td>'
                     f'<td class="num">{count(h["no_cutoff"])} of {count(h["runs"])}</td><td class="num">{count(c["n"])}</td>')
            hrows.append(P.tr(S, ds, n, cells, rel))
        if hrows:
            held.append(f'<h4 id="held-out-{ds}">League {lg["id"]}</h4>' + league_block(lg, P.SWIPE + P.table(
                ["Model and setting", "Share kept on the other half", "Blunders among kept", "Splits with no cutoff",
                 "Decisions with probabilities"], hrows, "Means over the splits of the held-out half",
                attrs=f' data-dataset="{ds}"')))
        tail.append(f'<h4 id="tail-{ds}">League {lg["id"]}</h4>' + league_block(lg, P.tail_table(S, rel, ds, lg["setups"])))
    total = sum(lg["decisions"] for lg in S["leagues"])
    scored = sum(lg["scored"] for lg in S["leagues"])
    unscored = (f"All {count(scored)} of the {count(total)} league decisions have a 2-ply evaluation of every legal play, "
                f"so no play needed a CPU evaluation." if scored == total else
                f"{count(total - scored)} of {count(total)} league decisions have plays without a 2-ply evaluation; they "
                f"are evaluated with GNU Backgammon on CPU, at low priority, by the update loop.")
    return dict(robust="".join(robust), held_out="".join(held) or f"<p>{nm(NA)}: no setup returns probabilities.</p>",
                tail="".join(tail), input=P.input_history(), unscored=unscored, safest=safest_text(S),
                hypothesis=hypothesis_text(S))


def safest_text(S) -> str:
    """Item 6 of the reviewed brief: the played program (League 1) against the computed reference (Leagues 2, 3)."""
    played = [(lg, lg["offline"]["safest"]) for lg in S["leagues"] if lg.get("offline", {}).get("safest")]
    out = []
    for lg, s in played:
        out.append(
            f'In League {lg["id"]}, Safest is the program that actually played the matches: among the plays that leave '
            f'the fewest hitting rolls it takes the one with the fewest blots, then the largest pip lead, then the play shown '
            f'first; it never asks the engine. It played a fewest-hitting-rolls play in {count(s["minimum_hitting_rolls"])} '
            f'of its {count(s["decisions"])} scored decisions and the engine\'s best safe play in '
            f'{count(s["best_safe_play"])} of them. Its right-safety part of the error rate, '
            f'{fmt(s["right_safety_contribution"], 2)} PR, is the equity lost on its {count(s["right_safety"])} '
            f'right-safety decisions × {count(S["thresholds"]["equity_scale"])} ÷ all {count(s["decisions"])} of its scored '
            f'decisions: a share of its error rate, not the average loss of a right-safety decision, which is '
            f'{fmt(s["right_safety_conditional"], 2)} PR.')
    computed = [lg["id"] for lg in S["leagues"] if "Safest (computed)" in lg["references"]]
    if computed:
        out.append(f'In League {" and League ".join(str(i) for i in computed)}, <em>Safest (computed)</em> is a computed '
                   'reference: the engine\'s best safe play on every scored decision of that league. Its numbers are not '
                   'directly comparable with League 1\'s played program.')
    return " ".join(out)


def hypothesis_text(S) -> str:
    h = S["hypothesis"]
    if h["rho"] is None:
        return f'Result: {esc(h["verdict"])}.'
    iv = (f' (95% interval {fmt(h["rho_lo"], 2, True)} to {fmt(h["rho_hi"], 2, True)}, {count(h["replicates"])} '
          f'resamples)' if h["rho_lo"] is not None else "")
    left = f' Left out (predictor undefined): {esc(", ".join(h["left_out"]))}.' if h["left_out"] else ""
    return (f'Result: ρ = {fmt(h["rho"], 2, True)}{iv} over {count(h["setups"])} setups: <strong>{esc(h["verdict"])}'
            f'</strong>.{left}')
