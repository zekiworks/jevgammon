"""The home page of the backgammon site (brief v12 B4), in the approved look: hero, findings, filters, the
leaderboard (Risk first), the chart panels, "Risk pays vs safety pays" and the downloads line. Every number comes
from S (build.compute); the per-phase views of a league are written as fragments (fragments/<league>-<phase>.html)
that the page loads when the Phase filter changes, so the page itself stays small."""

import json
import math

import analysis as A
import pages as P
from common import NA, NOT_MEASURED, PENDING, PROVISIONAL, PROVISIONAL_NOTE, TOO_FEW, count, esc, fmt, nm, pct, status_badge

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
    return (f'<td class="num">{esc(a)}<span class="small">{count(c["taken_n"])} risks taken; mean confidence on missed '
            f'risks {esc(b)} ({count(c["missed_n"])})</span></td>')


RISK_HEAD = ["Model and setting", "Risk judgement", "Risks found", "Right safety", "Good risks", "Missed risks",
             "Needless risks", "Wrong risks", "Error rate by risk-call category (PR)", "Decisions with a trade-off",
             "Big risks found", "Big needless risks", "Extra hitting rolls: right / wrong and needless",
             "Confidence on the call: ranking score for right risk"]
ROBUST_HEAD = ["Model and setting", "Risk judgement", "Risks found", "Right safety", "Good risks", "Missed risks",
               "Needless risks", "Wrong risks"]


def risk_table(S, lg, phase="all") -> str:
    ds = lg["dataset"]
    body = []
    for n, r, _, ref in rows_of(S, lg, phase):
        cls = ' class="reference"' if ref else ""
        body.append(f'<tr{cls}{attrs(S, ds, slug_name(n), bool(ref))}>{cell_model(S, ds, n, ref if n in lg["references"] else None)}'
                    + judgement_td(r) + share_td(r["found"]) + share_td(r["right_safety"]) + share_td(r["good"])
                    + share_td(r["missed"]) + share_td(r["needless"]) + share_td(r["wrong"]) + split_td(r)
                    + classes_td(r) + share_td(r["stake"]["big"]["found"]) + share_td(r["needless_by_loss"]["big"])
                    + size_td(r) + conf_call_td(r) + "</tr>")
    where = "all phases" if phase == "all" else P.PHASE_LABEL[phase]
    return (P.SWIPE + P.table(RISK_HEAD, body, f"Risk calls at the 0.001 margin, {esc(where)}; shares with count / "
                              "denominator, risk judgement with its 95% interval (games resampled)",
                              attrs=f' data-dataset="{ds}" data-margin="0.001"')
            + f'<p class="table-note">{esc(LIMIT_HIT)}</p><p class="table-note">{esc(LIMIT_HARD)}</p>'
            + '<p class="table-note">Big: above 0.08 · confidence on the call: ranking score only, no calibration gap '
              '(the probability is for the chosen play, not the risk) · <a href="method/#risk">Definitions</a></p>')


def robust_table(S, lg, phase="all") -> str:
    ds = lg["dataset"]
    body = []
    for n, r, _, ref in rows_of(S, lg, phase, "robust"):
        cls = ' class="reference"' if ref else ""
        body.append(f'<tr{cls}{attrs(S, ds, slug_name(n), bool(ref))}>{cell_model(S, ds, n, ref if n in lg["references"] else None)}'
                    + judgement_td(r) + share_td(r["found"]) + share_td(r["right_safety"]) + share_td(r["good"])
                    + share_td(r["missed"]) + share_td(r["needless"]) + share_td(r["wrong"]) + "</tr>")
    return (f'<h3 class="table-title" id="risk-robust-{ds}{"" if phase == "all" else "-" + phase}">The same at the 0.02 margin (robustness)</h3>'
            + P.SWIPE + P.table(ROBUST_HEAD, body, "Every 0.001 in the definitions replaced by 0.02",
                                attrs=f' data-dataset="{ds}" data-margin="0.02"'))


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
            cells = f"<td>{esc(src)}</td>" + "".join(f'<td class="num">{nm(NA)}</td>' for _ in range(9))
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
        rows.append(f"<tr{attrs(S, ds, n)}>{cell_model(S, ds, n)}{cells}</tr>")
    head = ["Model and setting", "Confidence source", "Kept at 0.90", "Blunders among kept, 0.90",
            "Mean equity lost among kept, 0.90", "Kept at 0.99", "Blunders among kept, 0.99",
            "Mean equity lost among kept, 0.99", "Error rate in the surest quarter (PR)",
            "Ranking score (AUROC) for the engine's best play", "Calibration gap (ECE, points)",
            "Confident and badly wrong"]
    return (P.SWIPE + P.table(head, rows, "Confidence: the probability a setup gave its chosen play; N/A for setups "
                              "without probabilities", attrs=f' data-dataset="{ds}"')
            + '<p class="table-note">The cutoff chosen on half of the games and tested on the other half: '
              '<a href="method/#confidence">Method</a>.</p>')


def cost_table(S, lg) -> str:
    return P.SWIPE + P.table(P.COST_HEAD, P.cost_rows(S, "", lg["dataset"], lg["setups"]), "Time and cost in this league",
                             attrs=f' data-dataset="{lg["dataset"]}"')


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


def risk_panel_body(S, lg, phase="all") -> str:
    out = []
    for m in ("main", "robust"):
        out.append(f'<div class="chart-view" data-view-chart="riskmap" data-view-margin="{m}">{risk_map(S, lg, m, phase)}'
                   '<p class="chart-legend"><span><i class="swatch rm-cautious"></i>missed risks</span> '
                   '<span><i class="swatch rm-wrong"></i>wrong risks</span> <span>colour: share of wrong risks among the '
                   'Risk pays decisions without the right risk · squares: reference rows · diagonals: risk judgement</span></p></div>')
        out.append(f'<div class="chart-view" data-view-chart="split" data-view-margin="{m}">{split_chart(S, lg, m, phase)}</div>')
        out.append(f'<div class="chart-view" data-view-chart="stake" data-view-margin="{m}">{stake_chart(S, lg, m, phase)}</div>')
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
        elif key == "quality":
            inner = slot(lg, "quality", quality_table(S, lg)) + f'<p class="table-note">{esc(LIMIT_PAIRED)}</p>'
        elif key == "confidence":
            inner = confidence_table(S, lg)
        elif key == "reasoning":
            inner = P.league_reasoning_table(S, lg)
        elif key == "cost":
            inner = cost_table(S, lg)
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
        "reasoning": "The same model at two reasoning settings.",
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
    return f"""<section class="panel filters is-open needs-js" id="filters" aria-labelledby="filters-title">
      <h2 id="filters-title" class="filters-title">Filters</h2>
      <div class="filters-body" id="filters-body">
        <div class="group league-pick" role="group" aria-labelledby="f-league"><span class="group-label" id="f-league">League</span><span class="keys">{leagues}</span></div>
        {group("kind", "Model type", [("all", "All"), ("decision", "Decision"), ("chat", "Chat"), ("program", "Program")])}
        <label class="group"><span class="group-label">Phase</span> <select data-control="phase"><option value="all">All phases</option>{phases}</select></label>
        {group("setting", "Reasoning", settings)}{group("runs", "Runs on", runs)}{group("weights", "Weights", weights)}
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
    return ('<section class="charts" id="charts" aria-label="Charts" tabindex="-1">'
            + chart_panel("chart-risk", "Risk", [("riskmap", "Risk map"), ("split", "Error rate by risk-call category"),
                                                 ("stake", "Stake chart")], risk, True, risk_note)
            + chart_panel("chart-measures", "Error rate, time and cost", [("error", "Error rate"), ("time", "Time"),
                                                                           ("cost", "Cost")], measures, False, paired)
            + chart_panel("chart-tradeoff", "Trade-off", [("tradeoff-cost", "Cost"), ("tradeoff-time", "Time")], trade,
                          False, paired)
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
h1{{font-size:34px;margin:0 0 4px}} .sub{{font-size:19px;color:var(--text-2);margin:0 0 18px}}
.big{{font-size:120px;font-weight:700;line-height:1;margin:0}} .big small{{font-size:24px;font-weight:400;color:var(--text-2);margin-left:14px}}
.parts{{font-size:20px;color:var(--text-2);margin:6px 0 22px}}
.cc-row{{display:flex;align-items:center;gap:14px;margin:7px 0;font-size:20px}} .cc-l{{width:170px;text-align:right}} .cc-bar{{height:24px;border-radius:3px;display:inline-block}}
.f{{position:absolute;bottom:24px;left:56px;right:56px;font-size:15px;color:var(--text-2)}}
</style></head><body><h1>{esc(w)}: risk judgement</h1>
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
                tail="".join(tail), input=P.input_history(), unscored=unscored)
