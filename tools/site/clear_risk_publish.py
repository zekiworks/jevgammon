#!/usr/bin/env python3
"""Clear-risk scan and follow-up (preliminary): the site's data file from the saved, checked reports.

    python3 tools/site/clear_risk_publish.py P2_REPORT_MD [OUT_JSON]

Assembles existing aggregate outputs only, nothing is recomputed: the tables of the mailbox reports
(Clear-risk scan - steps 0-3 / results, Clear-risk follow-up - part 1 / rollouts) and the saved Part 2 score report
(P2_REPORT_MD: the report written 2026-10-30T06:25:50Z, after the Q3 random-baseline edit; Part 2 is partial, GPT-6.1
Sol (high) is pending and its rows are removed, never shown as 0). Left out: the hand-check position lists (position-to-
choice records stay private) and every local path. OUT_JSON defaults to tools/site/content/clear_risk_results.json.
"""

import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent.parent
MB = ROOT / "mailbox"
OUT = SITE / "content" / "clear_risk_results.json"
PENDING_MODEL = "GPT-6.1 Sol (high)"
LABEL = "Preliminary / partial. Two or four plays shown, not league play."


def section(md: str, heading: str) -> str:
    """The text under `heading` (a markdown heading line) up to the next heading of the same or a higher level."""
    lines = md.split("\n")
    i = next(k for k, l in enumerate(lines) if l.strip() == heading)
    level = len(heading) - len(heading.lstrip("#"))
    out = []
    for l in lines[i + 1:]:
        m = re.match(r"^(#+) ", l)
        if m and len(m.group(1)) <= level:
            break
        out.append(l)
    return "\n".join(out)


def clean(cell: str) -> str:
    c = cell.strip().replace("\\|", "|").replace("**", "")
    c = re.sub(r"^\*(.+)\*$", r"\1", c)
    return c.replace("`", "")


def tables(text: str) -> list[dict]:
    """Every markdown table in `text`: header and rows (cells as printed, markup removed)."""
    out, cur = [], None
    for l in text.split("\n"):
        if l.startswith("|"):
            cells = [clean(c) for c in re.split(r"(?<!\\)\|", l.strip())[1:-1]]
            if cur is None:
                cur = dict(head=cells, rows=[])
            elif not all(re.fullmatch(r":?-+:?", c.strip()) for c in cells):
                cur["rows"].append(cells)
        elif cur is not None:
            out.append(cur); cur = None
    if cur is not None:
        out.append(cur)
    return out


def one(text: str, caption: str, k: int = 0) -> dict:
    return dict(tables(text)[k], caption=caption)


def build(p2_md: Path) -> dict:
    s03 = (MB / "Clear-risk scan - steps 0-3 2026-10-29.md").read_text()
    res = (MB / "Clear-risk scan - results 2026-10-29.md").read_text()
    p1 = (MB / "Clear-risk follow-up - part 1 2026-10-29.md").read_text()
    ro = (MB / "Clear-risk follow-up - rollouts 2026-10-30.md").read_text()
    p2 = p2_md.read_text()
    sections = []

    sections.append(dict(id="clear-risk-scan", title="The scan: which decisions have a clear risk call", notes=[
        "A decision is scanned when the mover has both a safe play (0 hitting rolls for the opponent) and an unsafe "
        "play (12 or more hitting rolls), there is contact, and there are more than 2 legal plays. Invalid answers "
        "(fallback) are skipped.",
        "Gap = 2-ply cubeless equity of the best unsafe play minus that of the best safe play (GNU Backgammon). Risk "
        "wins: gap of +0.04 or more. Safety wins: gap of -0.04 or less. Both are 'flagged'.",
        "3-ply stability check (it replaced rollouts for the leagues): a flagged decision is kept only if the gap is "
        "0.04 or more at both 2-ply and 3-ply, has the same sign at both, and the two gaps differ by 0.02 or less. "
        "It is a stability signal, not a rollout.",
        "Kept: 25,199 of 32,840 flagged decisions (7,997 Risk wins, 17,202 Safety wins).",
        "The method was written down and committed before any computation; the 3-ply rule was committed before any "
        "3-ply value was computed."],
        tables=[one(section(s03, "## Steps 2–3: league decisions"), "Steps 2-3: league decisions, skipped by the "
                    "first reason that applies"),
                one(section(res, "## 3-ply pass on the 32,840 flagged decisions"),
                    "Step 4: kept and unstable decisions per league and group")]))

    per = []
    for lg in (1, 2, 3):
        per.append(one(section(res, f"### League {lg}"), f"League {lg}: per setup, kept decisions only"))
    sections.append(dict(id="clear-risk-setups", title="Missed and needless risks per setup", notes=[
        "Missed risks: Risk wins played safe (0 hitting rolls). Needless risks: Safety wins played unsafe (12 or "
        "more). In-between: 1 to 11 hitting rolls. Bias = missed minus needless, in percentage points; positive "
        "means too cautious. Each share is shown with its count; no group has under 30 positions.",
        "Reference rows use all of the league's kept decisions: the Safest program always plays a 0-roll play; "
        "Random legal play gives each decision's expected shares (fraction of legal plays in each bin).",
        "Not paired: setups met different positions, so the rows compare only loosely.",
        "Thread: risks found is a different, broader measure: the site's published Risks found at margin 0.001, from "
        "the deployed results a12573f2, computed on all of a setup's Risk pays decisions, a much larger set than the "
        "kept clear-risk positions. Risks found counts a right risk, missed risks here count playing safe."],
        tables=per))

    c4 = section(p1, "## Check 4: where the best play is (said first, as asked)")
    c2 = section(p1, "## Check 2: missed and needless risks per 3-ply gap band")
    c3 = section(p1, "## Check 3: equity lost per bin")
    sections.append(dict(id="clear-risk-checks", title="Checks on the scan", notes=[
        "The best legal play is in between (1 to 11 hitting rolls) in 22% of Risk wins and 16% of Safety wins: in "
        "about one decision in five or six, neither of the two plays the scan compares is the best play.",
        "Bands are the absolute 3-ply gap: 0.04-0.08, 0.08-0.15 and 0.15+ (lower edge included). Setups (pooled) = "
        "the 45 setups other than the three programs, Random, Safest and GNUbg weak; each decision counts once.",
        "Missed risks do not fall as the gap grows (59%, 65%, 55%); needless risks do (6.0%, 4.7%, 2.4%).",
        "Equity lost = 2-ply equity of the best legal play minus that of the chosen play, mean (count). Took the right "
        "risk: a Risk win played unsafe, within 0.02 of the best unsafe play.",
        "Not paired: the five Part-2 models played in different leagues."],
        tables=[one(c4, "Check 4: where the best legal play is (2-ply)"),
                one(c2, "Check 2: missed and needless per 3-ply gap band (setups pooled; random legal play in italics "
                        "in the source)", 0),
                one(c2, "Check 2: the five Part-2 models (missed n/N · needless n/N · bias)", 1),
                one(c3, "Check 3: equity lost per bin, and took the right risk")]
        + [one(_appendix(p1, "## Appendix A", lg),
               f"Check 2 per setup, League {lg} (missed · needless · bias per band)") for lg in (1, 2, 3)]
        + [one(_appendix(p1, "## Appendix B", lg), f"Check 3 per setup, League {lg} (mean equity lost (n); took the "
               "right risk)") for lg in (1, 2, 3)]))

    sections.append(dict(id="clear-risk-rollouts", title="Rollout check of a 200-position sample", notes=[
        "Sample: 200 kept positions drawn with a fixed seed, 100 Risk wins and 100 Safety wins, about a third per gap "
        "band; Bray position excluded. Oversample: 30 back-game and 30 prime-vs-prime kept positions not in the 200 "
        "(fixed seed), reported separately and not used in Part 2.",
        "Settings: GNU Backgammon 1.08.003, 1,296 games per play, variance reduction, quasi-random dice, same seed for "
        "both plays, no truncation, cubeless money play with gammons and backgammons counted (1/2/3 points), Jacoby "
        "off, 2-ply checker play (cubeless, prune, no noise). Each play is rolled out from the position after it, "
        "opponent on roll.",
        "Confirmed = same direction as the scan, rollout gap 0.04 or more, and more than 3 standard errors of the "
        "gap. The rule, the settings and the oversample were committed before the first rollout.",
        "189 of 200 confirmed (94.5%): 93 of 100 Risk wins, 96 of 100 Safety wins. No position flipped; all 11 "
        "misses are in the 0.04-0.08 band with a smaller gap in the same direction. Back game 39 of 40, prime-vs-prime "
        "40 of 40 (sample and oversample together); most of those are large-gap Safety wins already kept by the "
        "3-ply check, so this says nothing about the positions the check dropped."],
        tables=[one(section(ro, "## Agreement per group and gap band (the 200; band = |3-ply gap|)"),
                    "Agreement per group and band (the 200)"),
                one(section(ro, "## Back games and prime-vs-prime"), "Back game and prime-vs-prime")]))

    part2 = [t for t in tables(p2)]
    caps = ["Q1: share right per group, missed and needless, bias (two plays shown, not league play)",
            "Q2 (board only): share right vs random", "Q3: share of pairs in the right order (pairs 0.04 or more "
            "apart at 3-ply)", "Risk wins cross-table (counts)", "Answers, failures, tokens"]
    assert len(part2) == len(caps)
    for t, cap in zip(part2, caps):
        t["caption"] = cap
        t["rows"] = [r for r in t["rows"] if r[0] != PENDING_MODEL]
    usage = part2.pop()
    expected = {"Celeris-1 Decision": 1782, "Jev 1.14.0": 1782, "Liquid d1-ultra": 1782,
                "Claude Sonnet 5.5 (high)": 816}
    den_rows = []
    for r in usage["rows"]:
        name, stored, failed, invalid, ties = r[0], int(r[1]), int(r[2]), r[3], int(r[4])
        bad = sum(int(n) for n in re.findall(r"(?:^|· )(?:invalid|failed or missing) (\d+)", invalid))
        den_rows.append([name, f"{expected[name]:,}", f"{stored:,}", str(failed), f"{stored - failed - bad - ties:,}",
                         re.sub(r"Q3 two values on one play \(pairs\) (\d+)", r"\1 Q3 items with two values on one play",
                                invalid) if invalid != "0" else "0", str(ties), r[5], r[6], r[7], r[8]])
    den_rows.append([PENDING_MODEL, "816", "pending (not collected)", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA"])
    usage = dict(caption="Denominators, failures and tokens per model (list-price cost, not billed spending, for the "
                         "hosted models; API-equivalent for Sonnet, not money paid)",
                 head=["model", "expected requests", "recorded answer rows", "answer rows with a request error",
                       "usable answers", "item-level flags (see notes)", "exact ties at the top (no answer)",
                       "input tokens", "output tokens", "reasoning tokens", "cost"],
                 rows=den_rows)
    sections.append(dict(id="clear-risk-part2", title="Part 2: asking the models (partial)", notes=[
        LABEL,
        "Positions: the 189 rollout-confirmed sample positions (93 Risk wins, 96 Safety wins). Each question is its "
        "own request with no shared context. Not paired across models beyond these shared items, and the league "
        "comparison is unpaired (the models played in different leagues on different positions).",
        "Q1: best safe vs best unsafe play, 'Which play is better?'; half the right answers are A (fixed seed). Q2 "
        "(board only, 60 items where exactly one option is true of the unsafe play B and not of the safe play A): "
        "what does play B do that play A does not; random baseline 25%. Q3: 3 or 4 plays (best safe, best unsafe, "
        "best in-between if any, one clear blunder at least 0.10 below the others at 3-ply if any) and their 3-ply "
        "values (2 decimals, labelled W-Z); chat models match each value to a play (each play once), decision models "
        "get one question per value.",
        "Two versions: with numbers (the league prompt with the computed consequences of each play) and board only "
        "(notation only, no pip count or other computed number).",
        "Models at league settings; temperature not sent (provider default) for all. Decision models: the "
        "top-probability option is the answer; an exact tie at the top is no answer. Q3 scoring: only pairs 0.04 or "
        "more apart at 3-ply; a decision model that puts two values on one play gets the pairs of that play wrong; a "
        "chat answer that is not one-to-one counts every pair wrong.",
        "GPT-6.1 Sol (high): pending, not collected (its subscription was busy with other queued jobs). Its rows are "
        "NA, never 0%. This is separate from the Codex effort sweep, whose GPT-6.1 Sol (max) row is a different run.",
        "Q3 random baselines were added AFTER the first score output: first score 2026-10-30T06:25:29.387Z, baseline "
        "edit 2026-10-30T06:25:46.496Z, baseline output 2026-10-30T06:25:50.444Z. Not pre-registered and not exact: "
        "a simulation with seed 2026103005, 200 draws per item (4000 // 20), rounded to whole percent. Scoring was "
        "not changed.",
        "The cross-table's 'doesn't know the game' uses the board-only Q2 answer for both versions (Q2 was asked board "
        "only).",
        "Denominators: expected = items sent per model; recorded = answer rows stored; usable = recorded minus rows "
        "with a request error, invalid answers and exact ties. 'Item-level flags' for decision models count Q3 items "
        "(position and version) where two values went to one play, not pairs and not failed requests. Answer-row "
        "error counts are rows whose request failed after retries, not attempts.",
        "Cost: hosted decision models at list price (the cash cap was $3; the stored list-price total is about "
        "$0.59); Claude Sonnet 5.5 (high) on a subscription, shown as API-equivalent, not money paid."],
        tables=part2 + [usage]))
    return dict(label=LABEL, status="Preliminary / partial", sections=sections,
                pending=[dict(what="Part 2: GPT-6.1 Sol (high)", blocker="ChatGPT subscription busy with the "
                              "season-2 queue (Codex effort sweep); runs once it is free")],
                omitted=[dict(what="Hand-check position lists", why="position-to-choice records stay private")])


def _appendix(md: str, heading_prefix: str, lg: int) -> str:
    lines = md.split("\n")
    start = next(k for k, l in enumerate(lines) if l.startswith(heading_prefix))
    sub = "\n".join(lines[start:])
    return section(sub, f"### League {lg}")


def main():
    p2 = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    data = build(p2)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(out, sum(len(t["rows"]) for s in data["sections"] for t in s["tables"]), "rows")


if __name__ == "__main__":
    main()
