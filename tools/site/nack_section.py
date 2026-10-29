"""Nackgammon paired test (Method spec 2026-10-24 §10): the home page section, from content/nack_paired_results.json.

Every value cell carries data-k (paths into the data file, "|"-separated; "@Name/..." is setup Name's record) and every
row data-row (its key under the table's data-src); nack_paired_verify.py reads them back and checks each printed number
against the data file. Rows are in the data file's fixed order (group, then standard PR); no header can be sorted.
"""

import math

import pages as P
from common import NACK_SCOPE_NOTE, count, esc, fmt

SECTION_ID = "nackgammon-paired"
TITLE = "Nackgammon paired test"
READING = ("A larger drop is consistent with relying on familiar positions but is not proof: Nackgammon positions also "
           "differ in structure. \u201cKept\u201d is a valid result.")
PROMPT_NOTE = ("The paired test's standard-side prompt differs from the league prompt (no opening table; the starting "
               "setup on its own line), so the standard error rates here are not compared with league error rates.")
LABELS = {"kept": "kept", "worse": "worse", "better": "better", "unclear": "unclear"}
RULES = [("random", "Primary rule: an invalid or missing answer scores the position's Random error"),
         ("worst", "Sensitivity (i): an invalid or missing answer scores the worst legal play's loss"),
         ("drop", "Sensitivity (ii): the pair is left out for that setup"),
         ("cutoff", "Sensitivity (iii): a pair with an answer cut off at the output limit is left out for that setup")]
PHASES = ("opening", "contact", "holding", "race", "bear-off")
DASH = "\u2013"
ADDED = "added under \u00a710.14(g), after the results were read"
ENGINE_ADDED = ("The additions' chosen plays that had no rollout yet were rolled out later with the same settings, alone "
                "rather than alongside the other candidates of their positions; the earlier rollouts are unchanged.")
# Chart classes per group (not the group names: one of them is a banned string in published files).
GROUP_CLASS = {"decision models": "nack-dm", "workhorses": "nack-wh", "frontier": "nack-fr",
               "no group (exploratory)": "nack-ng"}


def resolve(data: dict, rec, path: str):
    """The value at path ("a/b/0") inside rec; "@Name/..." starts at data["setups"][Name]."""
    if path.startswith("@"):
        name, _, path = path[1:].partition("/")
        rec = data["setups"][name]
    for k in path.split("/") if path else []:
        rec = rec[int(k)] if isinstance(rec, list) else rec[k]
    return rec


def show(v, digits=2, signed=False) -> str:
    if v is None:
        return DASH
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        return f"[{show(v[0], digits, signed)}, {show(v[1], digits, signed)}]"
    if isinstance(v, int):
        return count(v)
    if isinstance(v, float):
        return fmt(v, digits, signed)
    return str(v)


def td(data, rec, paths, digits=2, signed=False, sep=" ", text=False) -> str:
    vals = [resolve(data, rec, p) for p in paths]
    shown = sep.join(show(v, digits, signed) for v in vals if v is not None) or DASH
    cls = "" if text else " class=num"
    return f'<td{cls} data-k="{esc("|".join(paths))}">{esc(shown)}</td>'


def table(src, head, rows, caption, tid) -> str:
    head = [(h, " data-nosort") for h in head]
    return P.SWIPE + P.table(head, rows, esc(caption), cls="board list", attrs=f' id="{tid}" data-src="{esc(src)}"')


def row(key, label, cells) -> str:
    return f'<tr data-row="{esc(key)}"><th scope="row">{label}</th>{"".join(cells)}</tr>'


def _setup_label(name, rec) -> str:
    added = f" \u00b7 {ADDED}" if rec.get("added") else ""
    return f'{esc(name)}<span class="small">{esc(rec["group"])}{esc(added)}</span>'


def no_group_note(N) -> str:
    """Who is in no group and why: a setup new to the leagues (§10.14(b)), or one added by decision (the scorer's
    exploratory notes, §10.14(h))."""
    new = [s for s, r in N["setups"].items() if r["group"] == "no group (exploratory)" and s not in N["exploratory"]]
    parts = [f"{s} (a setup that had played in no league before this test, \u00a710.14(b))" for s in new]
    parts += list(N["exploratory"].values())
    return "No group (exploratory), in no group comparison: " + "; ".join(parts) + "."


def random_ref(N, pairs) -> str:
    """Random's drop on the same pair set as the row's final look: chosen by the number of pairs shown, never by the
    paid-model extension flag (Random is computed, not extended)."""
    rnd = N["setups"]["Random"]
    for look in ("final", "first"):
        if rnd[look]["pairs"] == pairs:
            return f"@Random/{look}/drop"
    raise ValueError(f"no Random look on {pairs} pairs")


def main_table(N) -> str:
    rows = []
    for s, r in N["setups"].items():
        rnd = random_ref(N, r["final"]["pairs"])
        rows.append(row(s, _setup_label(s, r), [
            td(N, r, ["first/standard_pr"]), td(N, r, ["first/nackgammon_pr"]), td(N, r, ["first/drop"], signed=True),
            td(N, r, ["first/drop_975"], signed=True), td(N, r, ["@Random/first/drop"], signed=True),
            td(N, r, ["extended", "extension_incomplete"], sep="; ", text=True),
            td(N, r, ["final/pairs"]), td(N, r, ["final/standard_pr"]), td(N, r, ["final/nackgammon_pr"]),
            td(N, r, ["final/drop"], signed=True), td(N, r, ["final/drop_975"], signed=True),
            td(N, r, [rnd], signed=True), td(N, r, ["label"], text=True),
            td(N, r, ["invalid/first/standard", "invalid/first/nackgammon"], sep=" / "),
            td(N, r, ["invalid/final/standard", "invalid/final/nackgammon"], sep=" / ")]))
    head = ["Setup (group)", "Standard PR, main 200 pairs", "Nackgammon PR, main 200 pairs", "Drop, main 200 pairs",
            "First look 97.5% interval", "Random's drop, main 200 pairs", "Extended to 500 pairs",
            "Pairs, final look", "Standard PR, final", "Nackgammon PR, final", "Drop, final", "Final 97.5% interval",
            "Random's drop, same pairs as the final look", "Label (final interval)",
            "Positions without a valid choice, main 200 pairs (standard / Nackgammon)",
            "Positions without a valid choice, final pairs (standard / Nackgammon)"]
    return table("setups", head, rows, "Per setup: standard PR, Nackgammon PR and the drop (Nackgammon \u2212 standard; "
                                       "positive = worse on Nackgammon)", "nack-table")


def _limit_cells(N, r) -> list:
    """Output-limit counts (§10.14(h)), main 200 pairs and all recorded positions; Random is never asked."""
    if not r["cut_off"]:
        return [f"<td>{DASH}</td>"] * 4
    return [td(N, r, [f"{k}/{w}/standard", f"{k}/{w}/nackgammon"], sep=" / ")
            for k in ("cut_off", "past_32768_no_limit_sent") for w in ("main", "all")]


def sensitivity_table(N) -> str:
    rows = [row(s, _setup_label(s, r), [
        td(N, r, ["invalid/first/standard", "invalid/first/nackgammon"], sep=" / "),
        td(N, r, ["first/drop"], signed=True), td(N, r, ["first/drop_975"], signed=True),
        td(N, r, ["sensitivity/worst/drop"], signed=True), td(N, r, ["sensitivity/worst/drop_975"], signed=True),
        td(N, r, ["sensitivity/drop/pairs"]), td(N, r, ["sensitivity/drop/drop"], signed=True),
        td(N, r, ["sensitivity/drop/drop_975"], signed=True),
        td(N, r, ["sensitivity/cutoff/pairs"]), td(N, r, ["sensitivity/cutoff/drop"], signed=True),
        td(N, r, ["sensitivity/cutoff/drop_975"], signed=True)] + _limit_cells(N, r))
        for s, r in N["setups"].items()]
    head = ["Setup (group)", "Invalid answers, standard / Nackgammon (main 200 pairs)", "Drop, primary rule",
            "97.5% interval", "Drop, invalid = worst play", "97.5% interval", "Pairs, invalid pairs left out",
            "Drop, invalid pairs left out", "97.5% interval", "Pairs, cut-off pairs left out",
            "Drop, cut-off pairs left out", "97.5% interval",
            "Cut off at the output limit, main 200 pairs (standard / Nackgammon)",
            "Cut off at the output limit, all recorded positions (standard / Nackgammon)",
            "Past 32,768 output tokens, no limit sent, main 200 pairs (standard / Nackgammon)",
            "Past 32,768 output tokens, no limit sent, all recorded positions (standard / Nackgammon)"]
    return (table("setups", head, rows, "Invalid answers, output-limit flags and the three sensitivity checks, main "
                                        "200 pairs", "nack-sensitivity")
            + f'<p class="table-note nack-limit-note">{esc(N["limit_note"])}</p>')


def phase_table(N) -> str:
    rows = []
    for s, r in N["setups"].items():
        cells = [td(N, r, [f"phases/{p}/standard_pr", f"phases/{p}/nackgammon_pr"], sep=" / ")
                 + td(N, r, [f"phases/{p}/drop", f"phases/{p}/drop_95"], signed=True) for p in PHASES]
        cells.append(td(N, r, ["opening_vs_rest/diff", "opening_vs_rest/ci_95"], signed=True))
        rows.append(row(s, _setup_label(s, r), cells))
    head = ["Setup (group)"] + [h for p in PHASES for h in (f"{p}: standard / Nackgammon PR", f"{p}: drop [95%]")] + [
        "Opening drop \u2212 other phases' drop [95%]"]
    return table("setups", head, rows, "By phase, main 200 pairs (descriptive, 95% intervals); Random's row is in the "
                                       "table", "nack-phases")


def tag_table(N) -> str:
    tags = sorted({t for r in N["setups"].values() for t in r["tags"]})
    rows = []
    for s, r in N["setups"].items():
        cells = []
        for t in tags:
            if t in r["tags"]:
                cells.append(td(N, r, [f"tags/{t}/standard/pr", f"tags/{t}/standard/n",
                                       f"tags/{t}/nackgammon/pr", f"tags/{t}/nackgammon/n"], sep=" \u00b7 "))
            else:
                cells.append(f"<td>{DASH}</td>")
        rows.append(row(s, _setup_label(s, r), cells))
    head = ["Setup (group)"] + [f"{t}: standard PR \u00b7 n \u00b7 Nackgammon PR \u00b7 n" for t in tags]
    return table("setups", head, rows, "By game-plan tag, main 200 pairs (descriptive; the back-game row is too thin to "
                                       "read)", "nack-tags")


def cost_table(N) -> str:
    rows = [row(s, _setup_label(s, r), [td(N, r, [f"cost/{w}/{k}"], digits=3)
                                        for w in ("main", "all") for k in ("decisions", "billed_usd_per_1000",
                                                                           "api_eq_usd_per_1000")])
            for s, r in N["setups"].items() if r["cost"]]
    head = ["Setup (group)", "Decisions, main", "Recorded cost, USD per 1,000 decisions, main",
            "API-equivalent USD per 1,000 decisions, main", "Positions recorded, all (incl. timed out)",
            "Recorded cost, USD per 1,000, all",
            "API-equivalent USD per 1,000, all"]
    return (table("setups", head, rows, "Cost per decision of the run (recorded cost and API-equivalent never added; "
                                        "0 = nothing recorded of that kind)", "nack-cost")
            + f'<p class="table-note nack-cost-note">{esc(N["cost_note"])}</p>')


def risk_table(N, which) -> str:
    rows = []
    for s, r in N["setups"].items():
        if not r["risk"][which]:
            continue
        b = f"risk/{which}"
        rows.append(row(s, _setup_label(s, r), [
            td(N, r, [f"{b}/standard/risk_pays", f"{b}/standard/safety_pays"], sep=" / "),
            td(N, r, [f"{b}/nackgammon/risk_pays", f"{b}/nackgammon/safety_pays"], sep=" / "),
            td(N, r, [f"{b}/standard/d_prime"]), td(N, r, [f"{b}/nackgammon/d_prime"]),
            td(N, r, [f"{b}/change/d_prime", f"{b}/change/d_prime_95"], signed=True),
            td(N, r, [f"{b}/standard/caution"]), td(N, r, [f"{b}/nackgammon/caution"]),
            td(N, r, [f"{b}/change/caution", f"{b}/change/caution_95"], signed=True),
            td(N, r, [f"{b}/thin"], text=True)]))
    head = ["Setup (group)", "Risk pays / Safety pays, standard", "Risk pays / Safety pays, Nackgammon",
            "Ability d\u2032, standard", "d\u2032, Nackgammon", "Change in d\u2032 [95%]", "Caution c, standard",
            "c, Nackgammon", "Change in c [95%]", "Thin (a class under 50 positions)"]
    what = "main 200 pairs" if which == "main" else "all 500 pairs, extended setups"
    return table("setups", head, rows, f"Secondary: risk calls, {what}", f"nack-risk-{which}")


def group_notes(N, orig=False) -> str:
    """\u00a710.14: the groups rule (what had been opened before it) and the frontier note, verbatim from the scorer;
    after a table of the original members only, the frontier note of that roster."""
    fr = N["frontier_note_original_members"] if orig else N["frontier_note"]
    return (f'<p class="table-note nack-groups-rule">{esc(N["groups_rule"])}</p>'
            f'<p class="table-note nack-frontier-note">{esc(fr)}</p>')


def scope_notes(N) -> str:
    """Wherever group results or the frontier group appear: the scope note and the frontier note."""
    return (f'<p class="note"><strong>Scope.</strong> {esc(NACK_SCOPE_NOTE)}</p>'
            f'<p class="table-note nack-frontier-note">{esc(N["frontier_note"])}</p>')


def primary_table(N, rule, caption, key="primary") -> str:
    """One rule's primary comparisons: with the §10.14(g) additions (key "primary", the primary result) or with the
    original members only (key "primary_original_members")."""
    rows = []
    for i, c in enumerate(N[key][rule]):
        label = esc(c["comparison"])
        if c.get("missing"):
            rows.append(f'<tr data-row="{i}"><th scope="row">{label}</th><td colspan="9">Not yet available: one side '
                        f'has no setup in the run yet.</td></tr>')
            continue
        rows.append(row(i, label, [
            td(N, c, ["A/standard_pr"]), td(N, c, ["A/nackgammon_pr"]), td(N, c, ["A/drop"], signed=True),
            td(N, c, ["B/standard_pr"]), td(N, c, ["B/nackgammon_pr"]), td(N, c, ["B/drop"], signed=True),
            td(N, c, ["diff"], signed=True), td(N, c, ["ci_99"], signed=True),
            td(N, c, ["@Random/first/drop"], signed=True)]))
    head = ["Comparison (A \u2212 B)", "A: standard PR", "A: Nackgammon PR", "A: drop", "B: standard PR",
            "B: Nackgammon PR", "B: drop", "Difference of drops", "99% interval", "Random's drop, same pairs"]
    orig = key == "primary_original_members"
    tid = f"nack-primary-{'orig-' if orig else ''}{rule}"
    return table(f"{key}/{rule}", head, rows, caption, tid) + group_notes(N, orig)


def kept_table(N, key, caption) -> str:
    K = N["secondary"][key]
    rows = [row(s, _setup_label(s, N["setups"][s]), [td(N, k, ["K"]), td(N, k, ["ci_95"]), td(N, k, ["standard_advantage"]),
                            td(N, k, ["advantage_95"]), td(N, k, ["unstable"], text=True)]) for s, k in K.items()]
    head = ["Setup (group)", "Kept advantage K", "95% interval", "Standard advantage over Random (PR)", "95% interval",
            "Unstable"]
    return table(f"secondary/{key}", head, rows, caption, f"nack-{key.replace('_', '-')}")


def spearman_tables(N) -> str:
    sp = N["secondary"]["spearman"]
    one = table("secondary", ["Analysis", "Model setups", "Spearman correlation", "95% interval"],
                [row("spearman", "Standard against Nackgammon PR, main 200 pairs",
                     [td(N, sp, ["setups"]), td(N, sp, ["rho"]), td(N, sp, ["ci_95"])])],
                "Secondary: ranking, yardsticks left out", "nack-spearman")
    rows = [row(i, esc(c["setup"]), [td(N, c, ["standard_rank"]), td(N, c, ["nackgammon_rank"]),
                                     td(N, c, ["change"], signed=True)])
            for i, c in enumerate(sp["largest_rank_changes"])]
    two = table("secondary/spearman/largest_rank_changes", ["Setup", "Rank, standard", "Rank, Nackgammon", "Change"],
                rows, "Secondary: the five largest rank changes (rank 1 = lowest PR; ties by name)", "nack-rank-changes")
    return one + two


def engine_tables(N) -> str:
    E = N["engine_check"]
    if not E:
        return ('<p class="table-note">Engine check (\u00a710.12, GNUbg rollouts on 40 of the main pairs): not run yet; '
                'shown here once it is.</p>')
    rows = [row(s, _setup_label(s, N["setups"][s]), [td(N, v, [f"{e}/{k}"], signed=k == "drop") for e in ("2ply", "rollout")
                            for k in ("standard_pr", "nackgammon_pr", "drop")]) for s, v in E["per_setup"].items()]
    per = table("engine_check/per_setup", ["Setup (group)", "2-ply: standard PR", "2-ply: Nackgammon PR", "2-ply: drop",
                                           "Rollout: standard PR", "Rollout: Nackgammon PR", "Rollout: drop"],
                rows, "Engine check: 2-ply against rollout values on the subset", "nack-engine")
    prims = ""
    for key, what in (("primary", "with the \u00a710.14(g) additions (primary)"),
                      ("primary_original_members", "original members only")):
        if key not in E:
            continue
        rows = [row(i, esc(c["comparison"]), [td(N, c, ["2ply"], signed=True), td(N, c, ["2ply_ci_99"], signed=True),
                                              td(N, c, ["rollout"], signed=True),
                                              td(N, c, ["rollout_ci_99"], signed=True),
                                              td(N, c, ["direction_changed"], text=True)])
                for i, c in enumerate(E[key])]
        orig = key == "primary_original_members"
        prims += table(f"engine_check/{key}", ["Comparison", "2-ply difference", "99% interval", "Rollout difference",
                                                "99% interval", "Direction changed"],
                       rows, f"Engine check: the primary comparisons with both engines, {what}",
                       "nack-engine-primary" + ("-orig" if orig else "")) + group_notes(N, orig)
    counts = table("", ["Subset", "Pairs", "Plays rolled out", "Unrolled plays used (2-ply + shift)"],
                   [row("engine_check", "Engine-check subset", [td(N, E, ["pairs"]),
                                                          td(N, E, ["counts/rolled_out_plays"]),
                                                          td(N, E, ["counts/adjusted_plays_used"])])],
                   "Engine check: counts", "nack-engine-counts")
    changed = [c["comparison"] for key in ("primary", "primary_original_members") for c in E.get(key, [])
               if c["direction_changed"]]
    return (per + prims + counts + f'<p class="table-note">Settings: {esc(E["settings"])}. {esc(ENGINE_ADDED)}</p>'
            + f'<p class="table-note">{"Direction changed: " + esc("; ".join(changed)) if changed else "No primary comparison changes direction between 2-ply and rollout values, either way."} '
              "GNUbg's network learned standard play, so its values for early Nackgammon positions are likely less "
              "accurate; the check bounds that, it does not remove it.</p>")


def chart(N) -> str:
    pts = N["chart"]
    W, H, L, B, T, R = 640, 520, 56, 46, 14, 16
    top = max([max(p["standard_pr"], p["nackgammon_pr"]) for p in pts] or [10])
    mx = math.ceil(top * 1.05 / 10) * 10
    x = lambda v: L + (W - L - R) * v / mx  # noqa: E731
    y = lambda v: H - B - (H - B - T) * v / mx  # noqa: E731
    step = 10 if mx <= 100 else 20
    parts = []
    for v in range(0, mx + 1, step):
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{T}" y2="{H - B}"/>'
                     f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="muted" x="{x(v):.1f}" y="{H - B + 14}" text-anchor="middle">{v}</text>'
                     f'<text class="muted" x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    parts.append(f'<line class="rm-diag" x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(mx):.1f}" y2="{y(mx):.1f}"/>'
                 f'<text x="{(L + W - R) / 2}" y="{H - 8}" text-anchor="middle">Standard PR, main 200 pairs</text>'
                 f'<text x="14" y="{(T + H - B) / 2}" transform="rotate(-90 14 {(T + H - B) / 2})" '
                 f'text-anchor="middle">Nackgammon PR, main 200 pairs</text>')
    for p in pts:
        cx, cy = x(p["standard_pr"]), y(p["nackgammon_pr"])
        tip = (f'{p["setup"]} ({p["group"]}): standard PR {fmt(p["standard_pr"], 2)}, Nackgammon PR '
               f'{fmt(p["nackgammon_pr"], 2)}')
        mark = (f'<rect class="nack-yard" x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10"/>'
                f'<text x="{cx + 8:.1f}" y="{cy + 4:.1f}">{esc(p["setup"])}</text>' if p["group"] == "yardstick"
                else f'<circle class="nack-dot {GROUP_CLASS[p["group"]]}" cx="{cx:.1f}" cy="{cy:.1f}" r="4.5"/>')
        parts.append(f'<g class="pt" data-setup="{esc(p["setup"])}" data-x="{p["standard_pr"]}" '
                     f'data-y="{p["nackgammon_pr"]}"><title>{esc(tip)}</title>{mark}</g>')
    note = (f"{TITLE}: standard PR (x) against Nackgammon PR (y), main 200 pairs; dashed diagonal = no change; above it "
            f"= worse on Nackgammon. Colour = group by original league (no group = exploratory). Squares: GNUbg weak and "
            f"Random. {NACK_SCOPE_NOTE} {N['frontier_note']}")
    return (f'<svg class="chart-svg" data-chart="nack" data-note="{esc(note)}" viewBox="0 0 {W} {H}" width="{W}" '
            f'height="{H}" role="img" aria-label="{esc(TITLE)}: standard against Nackgammon error rate">'
            + "".join(parts) + "</svg>")


def section(N) -> str:
    rnd = N["setups"]["Random"]
    rd1, rdf = rnd["first"]["drop"], rnd["final"]["drop"]
    rnd_text = (f"Random's own drop: {fmt(rd1, 2, True)} PR on the main 200 pairs, {fmt(rdf, 2, True)} on all 500 "
                f"(Random scores {'slightly better' if rdf < 0 else 'worse'} on the Nackgammon positions). It is shown "
                "next to every result. Random is computed exactly from GNUbg's 2-ply values (mean loss over all legal "
                "plays): it is never asked and is not extended by the stopping rule; it is reported on the main 200 "
                "pairs and on all 500.")
    status = ('<p class="note"><strong>Partial results.</strong> The run is still in progress: some setups have not '
              'answered yet or not finished their extension. The numbers will change.</p>' if N["in_progress"] else "")
    rule_tables = "".join(primary_table(N, rule, "With the \u00a710.14(g) additions (primary result). " + cap
                                        + (", 99% intervals (M = 5)" if rule == "random" else ""))
                          for rule, cap in RULES)
    orig_tables = "".join(primary_table(N, rule, "Original members only. " + cap
                                        + (", 99% intervals (M = 5)" if rule == "random" else ""),
                                        "primary_original_members")
                          for rule, cap in RULES)
    kept = kept_table(N, "kept_advantage", "Secondary: kept advantage over random play, main 200 pairs")
    if N["secondary"]["kept_advantage_all_500"]:
        kept += kept_table(N, "kept_advantage_all_500", "Secondary: kept advantage, all 500 pairs (extended setups)")
    risk = risk_table(N, "main") + (risk_table(N, "all") if any(r["risk"]["all"] for r in N["setups"].values()) else "")
    scope = scope_notes(N)
    return (f'<section class="card" id="{SECTION_ID}"><div class="section-head"><h2>{esc(TITLE)}</h2></div>'
            f'<p class="section-label">{esc(N["method"])}</p>{status}{scope}'
            f'<p class="note nack-additions-note"><strong>Additions.</strong> {esc(N["additions_note"])}</p>'
            "<p>Nackgammon has the rules of backgammon; only the starting position differs. Each setup was asked 200 "
            "Nackgammon positions and 200 standard positions matched to them by phase, position class, number of legal "
            "plays and the gap between the two best plays. Error rate (PR) = 500 \u00d7 mean GNUbg 2-ply equity loss. "
            "Drop = Nackgammon PR \u2212 standard PR on the same pairs; positive = worse on Nackgammon. A setup whose "
            "first-look 97.5% interval was wide and contained 0 was asked the 300 reserve pairs too (500 pairs). Every "
            "recorded position is scored: an invalid, timed-out or missing answer scores the position's Random error, "
            "with the sensitivity checks below. Label from the final 97.5% "
            "interval: kept (within \u00b15 PR), worse, better or unclear. \u201cUnclear\u201d means the interval is "
            "too wide to decide; it is not evidence of equivalence.</p>"
            f'<p class="note">{esc(READING)}</p><p class="table-note">{esc(PROMPT_NOTE)}</p>'
            f'<p class="table-note">{esc(rnd_text)}</p>'
            f'<p class="table-note nack-no-group-note">{esc(no_group_note(N))}</p>'
            '<p class="table-note">Not a ranking: rows are in fixed order (group, then standard PR) and no table can be '
            'sorted.</p>'
            + main_table(N)
            + f'<p class="table-note nack-missing-note">{esc(N["missing_note"])}</p>'
            + '<figure class="chart-card" data-static-chart id="chart-nack"><div class="chart-head">'
              '<h3>Standard against Nackgammon error rate</h3>'
              '<button type="button" class="key" data-download-static>Download PNG</button></div>' + chart(N)
            + '<p class="chart-legend"><span><i class="swatch nack-dot nack-dm"></i>decision models</span> '
              '<span><i class="swatch nack-dot nack-wh"></i>workhorses</span> '
              '<span><i class="swatch nack-dot nack-fr"></i>frontier</span> '
              '<span><i class="swatch nack-dot nack-ng"></i>no group (exploratory)</span> '
              '<span><i class="swatch nack-yard"></i>GNUbg weak, Random</span> '
              '<span>Above the dashed diagonal: higher error on Nackgammon.</span></p></figure>'
            + f'<h3>Primary comparisons</h3>{scope}'
              '<p>Each difference is A\'s drop \u2212 B\'s drop (a group\'s drop = the mean of its setups\' drops), main 200 '
              'pairs, paired bootstrap. Five comparisons, so each interval is at 99% (Bonferroni, 1 \u2212 0.05/5). Both '
              'sides\' standard and Nackgammon PR are shown next to every difference. Shown both ways: with the '
              '\u00a710.14(g) additions (the primary result) and with the original members only.</p>' + rule_tables
            + f'<h4>Original members only</h4>{scope}' + orig_tables
            + '<h3>Invalid answers, output limit and sensitivity</h3>' + scope + sensitivity_table(N)
            + '<details><summary>By phase (descriptive)</summary>' + scope + phase_table(N) + '</details>'
            + '<details><summary>By game-plan tag (descriptive)</summary>' + scope + tag_table(N) + '</details>'
            + '<details><summary>Cost per decision</summary>' + scope + cost_table(N) + '</details>'
            + f'<h3>Secondary analyses</h3>{scope}'
              '<p class="table-note">Secondary, as fixed in \u00a710.11. K = (Random\'s Nackgammon PR \u2212 setup\'s '
              'Nackgammon PR) \u00f7 (Random\'s standard PR \u2212 setup\'s standard PR): 1 = keeps its whole advantage '
              'over random play, 0 = falls to random. Unstable: standard advantage under 20 PR or its interval reaches '
              '0. Risk: a class with fewer than 50 positions is thin and not read into.</p>'
            + kept + spearman_tables(N) + risk
            + '<h3>Engine check</h3>' + scope + engine_tables(N)
            + f'<p class="table-note">Data: <a href="data/v3/nack-paired.json" download="nack-paired.json">'
              f'nack-paired.json</a> \u00b7 <a href="method/#nackgammon-paired">Method</a> ({esc(N["method"])})</p>'
              '</section>')
