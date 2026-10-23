"""The Method page (brief B5, B6 limit, B8, B9, B10, B11) and the archived sections of the earlier live page.

body(ctx) returns the inner HTML of <main> for method/index.html. archive_v1() and archive_v3_notes() return the
sections kept from the earlier live page (content/archive/*.html, verbatim copies at analysis commit 3eca8e4) for
the Leagues page.

No result number is typed here: thresholds come from content/thresholds.json, the human scale from
content/human_scale.json, the two method experiments from content/experiments.json, shared-set counts from
positions/build-log.json and the play-order re-run from replay.db (both through ctx).
"""

import json
import re

from common import CONTENT, EARLIER, EARLIER_NOTE, NA, NOT_MEASURED, PENDING, PROVISIONAL, PUBLISHED, TOO_FEW, esc, fmt, status_badge

ARCHIVE = CONTENT / "archive"
# The play-order note (B8) without its "Earlier version:" prefix, which the status badge next to it already shows.
_note = EARLIER_NOTE.split(": ", 1)[-1]
ORDER_NOTE = _note[:1].upper() + _note[1:]
LEAGUES = "../leagues/"
DECISIONS = "../decisions/"
PHASES = ("opening", "contact", "holding", "race", "bear-off")  # display order, as tools/v3/classify.py PHASES

# Verdict labels (B9) and status words (B10), with what each means.
VERDICTS = [
    ("High helps", "The paired 95% interval of the error difference (high minus low, or B minus A) lies entirely below zero."),
    ("High hurts", "The interval lies entirely above zero."),
    ("No clear benefit", "The interval includes zero. Never read as \"the same\", \"level\" or \"gains nothing\"."),
    ("Depends on the position", "Phase-level effects point in different directions, each with an interval that excludes zero."),
]
STATUSES = [
    (PUBLISHED, "Computed from finished leagues or complete shared-position runs."),
    (PROVISIONAL, "From a league that is still running. The numbers will change. They appear only in that league's own tables "
                  "and enter no cross-league ranking, chart or finding until the league finishes."),
    (EARLIER, "From an earlier version of the benchmark. Never ranked or charted together with current numbers."),
    (PENDING, "The data exists, but the analysis has not been run on it yet."),
    (NOT_MEASURED, "This was not measured."),
    (NA, "Does not apply to this setup, for example confidence metrics for a setup that returns only a choice."),
]
LEAGUE_STATUSES = [
    ("Running (done / total)", "Matches are still being played; the numbers are provisional."),
    ("Finished", "Every match has been played."),
    ("Stopped", "The league was ended before all its matches were played; its finished matches are kept."),
]

# What each fixed threshold means (thresholds.json keys). Keys not listed here are still shown, under their own name.
THRESHOLDS = {
    "equity_scale": ("Error-rate scale", "Error rate = this number × mean equity lost per decision."),
    "best_play_loss_below": ("Engine's best play", "The chosen play lost less than this much equity."),
    "blunder_loss_above": ("Blunder", "The chosen play lost more than this much equity."),
    "badly_wrong_loss_above": ("Badly wrong", "The chosen play lost more than this much equity (used in \"confident and badly wrong\")."),
    "very_confident_probability_at_least": ("Very confident", "The setup gave its chosen play at least this probability."),
    "time_budget_seconds": ("Time budget", "Seconds of request time per decision; slower decisions count as over the budget."),
    "min_decisions_per_cell": ("Minimum sample", f"Fewer decisions than this in a cell: \"{TOO_FEW}\" instead of a value."),
    "near_tie_gap_below": ("Near-tie", "The two best plays are closer than this in equity."),
    "gap_buckets": ("Gap groups", "Limits of the groups by equity gap between the two best plays."),
    "option_buckets": ("Option groups", "Groups by number of legal plays."),
    "risk_margin": ("Risk margin", "B6.1: stake below it is Safety pays, at or above it Risk pays; a taken risk is right when the chosen play is at least this much better than the best safe play."),
    "risk_margin_robust": ("Robustness margin", "B6.6: every risk metric computed again with this margin in place of the risk margin."),
    "risk_thresholds_fixed_on": ("Risk thresholds fixed on", "Date the risk thresholds were fixed, before any risk number was computed."),
    "stake_bands": ("Stake bands", "Risk pays decisions by stake: small below the first value, medium up to the second, big above it."),
    "needless_loss_bands": ("Needless-risk bands", "Needless risks by the equity the chosen play lost: small, medium, big."),
    "confidence_cutoffs": ("Confidence cutoffs", "Confidence tab: decisions kept at or above each probability."),
    "cutoff_split_runs": ("Held-out splits", "Random halves of the games for the cutoff chosen on one half and tested on the other."),
    "cutoff_split_rule": ("Held-out cutoff rule", "How that cutoff is chosen."),
    "surest_share": ("Surest share", "Share of a setup's decisions with the highest confidence, for the error rate in the surest quarter."),
    "risk_map_diagonals": ("Risk map diagonals", "Risk judgement values drawn as faint diagonals on the risk map."),
    "hero_stake_range": ("Hero board stake", "The home page board shows a Risk pays decision with a stake in this range: the one closest to the median stake of those decisions in the latest finished league."),
    "tail_quantile": ("Tail error", "Quantile of the loss per decision reported as tail error."),
    "worst_share": ("Worst decisions", "Share of a setup's decisions, the ones with the largest loss, whose mean loss is reported."),
    "bootstrap_resamples": ("Bootstrap resamples", "Resamples for every interval."),
    "bootstrap_seed": ("Bootstrap seed", "Fixed random seed for every interval."),
    "interval": ("Interval level", "Coverage of every interval."),
}

# Shared position sets (positions/build-log.json keys), in the order shown.
SETS = {
    "v1": ("v1 set", "Recorded positions from the earlier version's leagues, the same positions the earlier report used. "
                     "Their plays are reshuffled with the option-order seed."),
    "new": ("New set", "GNU Backgammon self-play at expert level, the same number per phase."),
    "nackgammon": ("Nackgammon", "GNU Backgammon self-play from the Nackgammon starting position (an unfamiliar start, "
                                 "same rules). Its prompt drops the opening table."),
    "opening-control": ("Opening control", "The new set's opening positions, asked again with the opening table removed "
                                           "from the prompt."),
    "extension": ("League 1 extension", "More expert self-play positions with the same phase mix, for League 1 setups only."),
}


def _load(name: str):
    return json.loads((CONTENT / name).read_text())


def _value(x) -> str:
    """A threshold value as written in thresholds.json."""
    if isinstance(x, list):
        return ", ".join(_value(v) for v in x)
    return esc(x)


def _section(sid: str, title: str, inner: str) -> str:
    return (f'<section class="card" id="{sid}" aria-labelledby="{sid}-title">\n<h2 id="{sid}-title">{title}</h2>\n'
            f"{inner}\n</section>\n")


def _h3(sid: str, title: str) -> str:
    return f'<h3 id="{sid}">{title}</h3>'


def _table(head: list[str], rows: list[list[str]], num_cols: tuple = ()) -> str:
    def cls(i):
        return ' class="num"' if i in num_cols else ""
    th = "".join(f'<th scope="col"{cls(i)}>{h}</th>' for i, h in enumerate(head))
    body = "\n".join("<tr>" + "".join(f"<td{cls(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return (f'<div class="table-wrap">\n<table class="board">\n<thead><tr>{th}</tr></thead>\n<tbody>\n{body}\n</tbody>\n'
            "</table>\n</div>")


def _earlier(html: str) -> str:
    """Label every archived section 'Earlier version', with the play-order note under its title."""
    label = f'\n<p class="note">{status_badge(EARLIER)} {esc(ORDER_NOTE)}</p>'
    return re.sub(r"(<h2 [^>]*>.*?</h2>)", lambda m: m.group(1) + label, html, flags=re.S)


def _archive(name: str) -> str:
    return (ARCHIVE / name).read_text()


# ---------------------------------------------------------------- sections

def _toc() -> str:
    items = [("setup", "Setup"), ("shared-positions", "Shared positions"), ("prompt", "The prompt"),
             ("v1-why", "Why it looks like this"), ("error-rate", "Error rate"), ("human-scale", "Human scale"),
             ("risk", "Was it the right risk?"), ("statistics", "Statistics and verdicts"), ("thresholds", "Fixed thresholds"),
             ("status", "Status labels"), ("versions", "Versions and play order"), ("confidence", "Confidence"),
             ("cost", "Cost"), ("time", "Time"), ("limits", "Limits"), ("input", "What the input adds"),
             ("learning", "Learning from experience"), ("routing", "Routing and teams"), ("tail", "Tail risk"),
             ("v3-changes", "Runner changes during the leagues"),
             ("v3-anchor", "The anchor"), ("experiments", "Method experiments")]
    lis = "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in items)
    return f'<nav class="toc" aria-label="On this page"><ul>{lis}</ul></nav>'


def _intro() -> str:
    return ('<section class="card" id="method" aria-labelledby="method-title">\n<h1 id="method-title">Method</h1>\n'
            '<p>How the games are played, what the models are shown, how every decision is scored, and the rules for '
            'intervals and verdicts. The thresholds below were fixed before any number on this site was computed.</p>\n'
            "</section>\n")


def _setup() -> str:
    return _section("setup", "Setup", f"""
<p>The question is which model, at which reasoning setting, makes better decisions in which positions. Two kinds of data
  answer it: league games and shared positions. A <strong>setup</strong> is one model with one set of settings: a model
  with reasoning off and the same model with reasoning on are two setups.</p>
{_h3("setup-leagues", "Leagues")}
<p>Setups play each other in leagues: each league is a single round robin. League tables compare players inside one
  league only, and leagues are never merged into one overall score. See <a href="{LEAGUES}">Leagues</a>.</p>
<ul>
  <li><strong>League 1:</strong> decision models, plus two programs: Random (a random legal play) and Safest (the play
    that the fewest opponent rolls hit).</li>
  <li><strong>League 2:</strong> workhorse chat models, closed and open, each in two settings (reasoning low and high,
    or off and on).</li>
  <li><strong>League 3:</strong> frontier chat models played through their subscriptions, each with reasoning off and
    on.</li>
  <li><strong>Anchor:</strong> GNU Backgammon at its weak Beginner level plays in all three leagues as a fixed
    reference player (see <a href="#exp-anchor">the reference-player checks</a>).</li>
</ul>
{_h3("setup-match", "Match rules")}
<ul>
  <li>A match is played in rounds of two games with the same dice: in the second game the players swap seats and the
    same rolls are repeated, so both face the same luck.</li>
  <li>Three rounds, or fewer: the first player to 5 points after a full round wins if ahead. A tie gets one extra round,
    then counts as a draw. A game still running after 300 turns goes to the lower pip count for 1 point.</li>
  <li>Games score 1 point, 2 for a gammon and 3 for a backgammon. There is no doubling cube.</li>
  <li>League table: 3 points for a match win, 1 for a draw; ties broken by more games won, then fewer games lost.</li>
  <li>Dice seeds are fixed per league and published. Each match has its own dice (see
    <a href="#exp-dice">the dice-sharing test</a>).</li>
  <li>The v3 leagues play without a clock (see <a href="#time">Time</a>).</li>
</ul>
{_h3("setup-protocol", "How a decision is asked")}
<ul>
  <li><strong>Legal plays only.</strong> The program generates every legal play and the model chooses one of them, so a
    model can never make an illegal move. A roll with only one legal play is played automatically and is not a
    decision.</li>
  <li><strong>Shuffled order.</strong> The legal plays appear in a fixed random order per position, drawn from a
    published seed. The order never comes from an engine's ranking.</li>
  <li><strong>Reading the answer.</strong> Decision models give a probability for each option. Open chat models give
    probabilities for each answer letter, read after their reasoning when it is on. Models without probabilities
    answer one letter.</li>
  <li><strong>Long play lists.</strong> When a position has more legal plays than a model accepts, the plays are split
    into equal groups. The model picks a winner in each group, then chooses among the winners. The decision page shows
    when this happened.</li>
  <li><strong>Invalid answers.</strong> An answer that names no option is not retried. The runner plays a random legal
    play and marks the decision invalid. That play is never counted as the model's choice: it is shown as invalid and
    left out of every error rate.</li>
  <li><strong>Retries.</strong> Network and server errors are retried. Retry and wait time is kept apart from request
    time.</li>
  <li><strong>Memory.</strong> Every decision is a separate request. Models are not told how earlier games went.</li>
</ul>""")


def _shared(sets: dict) -> str:
    rows = []
    for key in list(SETS) + [k for k in sets if k not in SETS]:
        s = sets.get(key)
        if s is None:
            continue
        name, how = SETS.get(key, (key, ""))
        phases = s.get("per_phase", {})
        n = s.get("positions") or sum(phases.values()) or s.get("turns_1_to_6", 0) + s.get("later_turns", 0)
        order = list(PHASES) + [p for p in phases if p not in PHASES]
        mix = " · ".join(f"{esc(p)} {phases[p]:,}" for p in order if p in phases)
        extra = []
        if "games" in s:
            extra.append(f"from {s['games']:,} recorded games")
        if "games_used" in s:
            lo, hi = s["games_used"]
            extra.append(f"from {hi - lo:,} self-play games")
        if "turns_1_to_6" in s:
            extra.append(f"{s['turns_1_to_6']:,} from turns 1 to 6, {s.get('later_turns', 0):,} from later turns")
        if s.get("first_roll_positions"):
            extra.append(f"{s['first_roll_positions']:,} first-roll positions")
        for roll, plays in (s.get("first_rolls_excluded") or {}).items():
            extra.append(f"first roll {esc(roll)} left out ({plays:,} legal plays)")
        if s.get("duplicates_skipped"):
            extra.append(f"{s['duplicates_skipped']:,} duplicates skipped")
        detail = esc(how) + (f'<span class="small">{"; ".join(extra)}</span>' if extra else "")
        rows.append([esc(name), f"{n:,}", detail, mix or "–"])
    table = _table(["Set", "Positions", "How drawn", "By phase"], rows, num_cols=(1,))
    return _section("shared-positions", "Shared positions", f"""
<p>Every setup answers the same fixed positions with the same prompt. These positions, not the league tables, compare
  setups across leagues, and the main ranking uses them only. Each position is a board, the dice and the side to move.</p>
{table}
<p class="table-note">Counts from the position build log. Sampling rules: every position has 2 to 25 legal plays, so
  no model needs its plays split into groups; each self-play game gives at most one position per phase; within a game
  and phase the turn is drawn at random from a fixed seed; duplicates are skipped. If a phase cannot be filled, all
  distinct positions are used and the shortfall is logged.</p>
{_h3("shared-phases", "Game phases")}
<p>Each position gets the first phase that matches:</p>
<ol>
  <li><strong>Opening:</strong> turns 1 to 6, each side's first three moves.</li>
  <li><strong>Bear-off:</strong> any of GNU Backgammon's bear-off classes.</li>
  <li><strong>Race:</strong> GNU Backgammon's race class.</li>
  <li><strong>Holding:</strong> a contact position after turn 6 where one side has escaped all its back checkers and
    the other keeps one high anchor (2 or more checkers on the opponent's bar, 5- or 4-point, and no other checkers in
    the opponent's home board or on its bar point). This follows
    <a href="https://thegammonpress.com/backgammon-lesson-9-holding-games/">The Gammon Press's definition of a holding game</a>.</li>
  <li><strong>Contact:</strong> every other position.</li>
</ol>
{_h3("shared-tags", "Game-plan tags")}
<p>For analysis only, each contact position after the opening gets the first tag that matches: <strong>blitz</strong>
  (a checker on the bar against a home board with 3 or more made points), <strong>back game</strong> (2 or more anchors
  in the opponent's home board), <strong>holding</strong> (the rule above), <strong>low anchor</strong> (the only anchor
  is on the opponent's 3-, 2- or ace-point), <strong>priming</strong> (4 or more made points in a row), or
  <strong>other</strong>.</p>""")


def _prompt() -> str:
    return _section("prompt", "The prompt", f"""
<p>The current version is <strong>bg-v2</strong>. Every player gets it, and it did not change after the first match.
  It is the format of the earlier version's league #8. Every decision sends these parts in this order:</p>
<ol>
  <li><strong>Rules and strategy:</strong> the rules of backgammon, strategy principles (blots and points,
    distribution, exposure, blocking, hitting, anchors), the best opening plays from computer rollouts, and the match
    rules. Decision models get a short version; chat models get a longer one with a glossary, game plans and a worked
    example. Each setup's page says which it got.</li>
  <li><strong>Score</strong> and where the match stands.</li>
  <li><strong>Position</strong> from the mover's side: checkers on every point, bar, borne off, pip counts.</li>
  <li><strong>Race:</strong> the pip lead and whether the two sides are still in contact.</li>
  <li><strong>Dice</strong>, then the question: which move makes a point in front of the opponent's checkers, reduces
    your single pieces, or gets you closer to home.</li>
  <li><strong>The legal plays</strong> in the shuffled order, each followed by what the position looks like after it,
    computed by the program: hits, points made, blots left and how many of the opponent's 36 rolls hit them, points
    held, longest prime, pips. Chat models see each play under a letter.</li>
</ol>
<p>There is no move history: in the earlier version, adding the last 10 moves made no measurable difference. The
  <a href="{DECISIONS}">Every decision</a> page shows the exact text each model was sent.</p>
{_h3("prompt-history", "History")}
<p>The prompt was built one step at a time in the earlier version's leagues; the next section shows each step and what
  it changed. bg-v2 keeps that format and changes how the models are asked: the plays are shuffled, an invalid answer
  is not retried, and every setup gets the same rules and question. The earlier version re-asked up to three times and
  then played the first legal play, which its order favoured.</p>
""") + _earlier(_archive("v1-why.html")) + _earlier(_archive("v1-prompt.html"))


def _error_rate(t: dict) -> str:
    return _section("error-rate", "Error rate", f"""
<p>Wins and losses depend heavily on the dice. A backgammon engine can instead judge every decision directly. GNU
  Backgammon 1.08 evaluates every legal play at 2-ply, in cubeless money equity (expected points per game, match score
  ignored). The loss of a decision is the equity of the best play minus the equity of the play made. A play that ends
  the game scores its points exactly.</p>
<dl class="facts">
  <dt>Error rate</dt><dd>{_value(t["equity_scale"])} × mean 2-ply equity loss per decision. Lower is better. This is the
    checker-play performance rating (PR) that backgammon players use.</dd>
  <dt>Decision</dt><dd>A roll with 2 or more legal plays. Forced moves count in no rate.</dd>
  <dt>Invalid answers</dt><dd>Left out of the error rate and shown separately, with their count and share.</dd>
  <dt>Engine's best play</dt><dd>Share of decisions where the play made lost less than {_value(t["best_play_loss_below"])} equity.</dd>
  <dt>Blunder rate</dt><dd>Share of decisions where the play made lost more than {_value(t["blunder_loss_above"])} equity.</dd>
  <dt>Tail error</dt><dd>The {_value(t["tail_quantile"])} quantile of the loss per decision, and the mean loss of the worst
    {_value(t["worst_share"])} of decisions.</dd>
  <dt>Near-tie</dt><dd>The two best plays are within {_value(t["near_tie_gap_below"])} equity. Close plays are not rolled
    out; the gap groups on the Phases page show how much of a setup's error comes from them.</dd>
</dl>""")


def _human_scale() -> str:
    hs = _load("human_scale.json")
    rows, lo = [], None
    for b in hs["bands"]:
        hi = b["below"]
        rng = (f"under {_value(hi)}" if lo is None else f"{_value(lo)} or more" if hi is None
               else f"{_value(lo)} to {_value(hi)}")
        rows.append([esc(b["label"]), rng])
        lo = hi
    return _section("human-scale", "Human scale (approximate)", f"""
<p>Error rates are shown next to {esc(hs["source"])}'s bands for human players:</p>
{_table(["Band", "Error rate"], rows, num_cols=(1,))}
<p>The comparison is approximate. Human ratings also count doubling-cube decisions; these games have no cube, so the
  error rate covers checker plays only. The scale also comes from eXtreme Gammon's own evaluation, not GNU Backgammon
  at 2-ply. Read a band as a rough guide, not as a measured human level.</p>""")


def _risk(t: dict, extra: dict) -> str:
    m, r = _value(t["risk_margin"]), _value(t["risk_margin_robust"])
    a, b = t["stake_bands"]
    return _section("risk", "Was it the right risk? Definitions", f"""
<p>The core question: when a model takes a risk, is it the right risk? And when it plays safe, was safe right? The
  thresholds below ({m}, {r}, the stake bands {_value(a)} and {_value(b)}) were fixed on
  {esc(t["risk_thresholds_fixed_on"])}, before any of these numbers was computed.</p>
<dl class="facts">
  <dt>Hitting rolls</dt><dd>For each legal play, how many of the opponent's 36 rolls hit, read from the numbers the
    model was shown next to that play.</dd>
  <dt>Minimum risk</dt><dd>The fewest hitting rolls any legal play leaves in that position.</dd>
  <dt>Best safe play</dt><dd>Among the plays that leave the minimum risk, the one the engine rates best.</dd>
  <dt>Stake</dt><dd>The equity difference between the engine's best play and the best safe play: how much the risk call
    is worth in that position.</dd>
  <dt>Position class</dt><dd><strong>No trade-off</strong>: every legal play leaves the same number of hitting rolls;
    counted and left out of every risk metric. <strong>Safety pays</strong>: stake below {m}. <strong>Risk pays</strong>:
    stake {m} or more.</dd>
  <dt>Took a risk</dt><dd>The chosen play leaves more hitting rolls than the minimum. Otherwise the model played safe.</dd>
  <dt>Risk call</dt><dd><strong>Right risk</strong>: took a risk, and the chosen play is at least {m} better than the
    best safe play. <strong>Wrong risk</strong>: took a risk in a Risk pays position, but not one at least {m} better
    than the best safe play. <strong>Needless risk</strong>: took a risk in a Safety pays position. <strong>Missed
    risk</strong>: played safe in a Risk pays position. <strong>Right safety</strong>: played safe in a Safety pays
    position. Every decision with a trade-off gets exactly one risk call.</dd>
</dl>
{_h3("risk-metrics", "Metrics per setup (the Risk tab, in this order)")}
<ol>
  <li><strong>Risk judgement</strong>: the average of risks found and right safety, × 100. It does not depend on how many
    positions of each class a setup met. With both classes present, the Safest program scores exactly 50, the "always
    safe" line. If a setup has no Risk pays or no Safety pays decisions, it shows "N/A: no &lt;class&gt; decisions";
    an empty class is never read as 0 or 100. 95% interval: bootstrap by game.</li>
  <li><strong>Risks found</strong>: right risks ÷ Risk pays decisions.</li>
  <li><strong>Right safety</strong>: right safety ÷ Safety pays decisions.</li>
  <li><strong>Good risks</strong>: right risks ÷ all risks taken.</li>
  <li><strong>Missed risks</strong>: missed risks ÷ Risk pays decisions (too cautious).</li>
  <li><strong>Needless risks</strong>: needless risks ÷ Safety pays decisions (too bold).</li>
  <li><strong>Wrong risks</strong>: wrong risks ÷ Risk pays decisions.</li>
  <li><strong>Error rate by risk-call category</strong>: each part is 500 × the equity lost in that category ÷ all scored
    decisions of the setup, the same denominator for all six parts (needless risks, missed risks, wrong risks, right
    risks, right safety, No trade-off), so they add up exactly to the error rate. A right risk or right safety can still
    lose equity: the chosen play need not be the engine's best. It says where losses happened, not what caused
    them.</li>
  <li><strong>Decisions with a trade-off</strong>, and the counts per class.</li>
</ol>
<p>Every share shows its count and denominator. Every metric is computed per league; league comparisons are not paired.
  Setups met different positions, and risk judgement is not adjusted for how hard they were; paired comparisons wait for
  the shared positions.</p>
{_h3("risk-breakdowns", "Breakdowns")}
<ul>
  <li><strong>By stake</strong> (Risk pays only): small (below {_value(a)}), medium ({_value(a)} to {_value(b)}), big
    (above {_value(b)}); risks found, missed risks and wrong risks per band, and "big risks found" on its own.</li>
  <li><strong>Needless risks</strong> have no stake band (their stake is below the margin by definition); they are
    banded by the equity the chosen play lost, with the same limits, and "big needless risks" are those that lost more
    than {_value(b)}.</li>
  <li><strong>Risk size</strong>: extra hitting rolls over the minimum, averaged for right risks and for wrong and
    needless risks. An average over fewer than {_value(t["min_decisions_per_cell"])} decisions shows "{esc(TOO_FEW)}".</li>
  <li><strong>By phase</strong>: risk judgement per phase, on the <a href="../phases/">Phases</a> page and through the
    home page's Phase filter.</li>
  <li><strong>Confidence on the call</strong> (setups with probabilities only): among risks taken, the ranking score
    (AUROC) of confidence for "right risk", and the average confidence on missed risks. The confidence is the probability
    a model gave its chosen play, not the probability that the risk beats the best safe play, so no calibration gap is
    reported for risk calls. The calibration gap is reported only for the event the confidence stands for, the chosen
    play being the engine's best (Confidence tab).</li>
</ul>
{_h3("risk-references", "Reference rows")}
<p>Shown, never ranked, never champions. <strong>Safest</strong> always plays the best safe play; <strong>Random</strong>
  plays a random legal play; <strong>GNUbg weak</strong> is the x86-64 build: its noise is shifted, so it overplays
  gammons (see <a href="#v3-anchor">The anchor</a>). Safest and Random played League 1 only; in the other leagues they are
  computed on that league's positions (every scored decision of the league): Safest from the best safe play, Random as
  the expectation over all legal plays, so its counts can have decimals. A cell with no decisions shows its count, 0, and
  no average.</p>
{_h3("risk-charts", "Charts")}
<p><strong>Risk map</strong>: across, the Risk pays decisions without the right risk (missed + wrong risks) as a share
  of Risk pays decisions; up, needless risks as a share of Safety pays decisions. Risk judgement = 100 − (across + up) /
  2, so the corner (0, 0) is risk judgement 100; the faint diagonals mark {_value(t["risk_map_diagonals"])}. A point's
  colour is its share of wrong risks among the Risk pays decisions without the right risk. <strong>Error rate by risk-call
  category</strong>: the six parts as a stacked bar. <strong>Stake chart</strong>: risks found, wrong and missed risks per
  stake band, and big needless risks. <strong>Risk call card</strong>: one image per league winner. A downloaded PNG
  carries the league, the margin, the number of decisions, the results version and the site address, and lists the active
  filters; it keeps the theme in view.</p>
{_h3("risk-robust", "Robustness: the 0.02 margin")}
<p>At 2-ply the engine can misjudge close plays by more than {m}. Every risk metric is therefore computed a second time
  with {r} in every place where {m} appears above. The {r} results are on the Risk tab under the main table, and here:</p>
{extra["robust"]}
{_h3("risk-evaluations", "Plays without a 2-ply evaluation")}
<p>{extra["unscored"]}</p>
<p class="note">Limit: this measures one kind of risk, being hit. Gammon risk and priming are not in it.</p>""")


def _statistics(t: dict) -> str:
    rows = [[f"<strong>{esc(v)}</strong>", esc(d)] for v, d in VERDICTS]
    return _section("statistics", "Statistics and verdicts", f"""
<ul>
  <li><strong>Intervals</strong> are {_value(t["interval"])} bootstrap intervals with {_value(t["bootstrap_resamples"])}
    resamples and a fixed seed ({_value(t["bootstrap_seed"])}).</li>
  <li><strong>League decisions</strong> resample whole games, because moves within a game are not independent.</li>
  <li><strong>Shared positions</strong> resample positions.</li>
  <li><strong>Comparisons</strong> of two setups on the same positions are always paired: the interval is of the
    per-position difference in loss.</li>
  <li><strong>League comparisons are not paired.</strong> League games give each setup different positions. Between
    league setups we write only "no clear difference in league play" or "lower/higher error rate in league play",
    never a verdict label.</li>
  <li><strong>Minimum sample:</strong> an average (error rate, mean equity lost, a calibration metric) over fewer than
    {_value(t["min_decisions_per_cell"])} decisions shows "{esc(TOO_FEW)}" instead of a value. Raw counts are always
    shown, and a share is always shown with its count and denominator. Exception: the 50-position error rates on New
    models: first look are shown with their intervals.</li>
  <li><strong>League placings</strong> are descriptive. Middle places move between leagues with the dice.</li>
</ul>
{_h3("verdicts", "Verdicts")}
<p>For reasoning (low against high, off against on) and any comparison of A against B on the same positions:</p>
{_table(["Verdict", "Rule"], rows)}
<p>Every phase-level verdict is exploratory. "Worse moves" and "more time or cost with no shown gain" are kept as two
  separate findings and never merged into "high is bad".</p>""")


def _thresholds(t: dict) -> str:
    rows = []
    for key, val in t.items():
        if key.startswith("_") or key == "fixed_on":
            continue
        label, meaning = THRESHOLDS.get(key, (key, ""))
        if key == "option_buckets":
            shown = ", ".join(f"{lo}–{hi}" if hi is not None else f"{lo} or more" for lo, hi in val)
        else:
            shown = _value(val)
        rows.append([esc(label), shown, esc(meaning)])
    return _section("thresholds", "Fixed thresholds", f"""
<p>These values were fixed on {esc(t["fixed_on"])}, before any number on this site was computed, and are not changed
  after seeing results. Equity values are in points per game.</p>
{_table(["Threshold", "Value", "Meaning"], rows, num_cols=(1,))}""")


def _status() -> str:
    rows = [[status_badge(s), esc(d)] for s, d in STATUSES]
    lrows = [[f"<strong>{esc(s)}</strong>", esc(d)] for s, d in LEAGUE_STATUSES]
    return _section("status", "Status labels", f"""
<p>Every section and every metric shows one status. Where the data does not exist, the status is shown, never a
  placeholder number.</p>
{_table(["Status", "Meaning"], rows)}
{_h3("status-leagues", "League status")}
{_table(["League", "Meaning"], lrows)}
<p>An average below the minimum sample shows "{esc(TOO_FEW)}".</p>""")


def _versions(po: dict) -> str:
    diff, lo, hi = po["diff"], po["lo"], po["hi"]
    if lo > 0:
        reading = "so the runner's order helped it"
    elif hi < 0:
        reading = "so the runner's order hurt it"
    else:
        reading = "so a help from the order is possible but not proven"
    return _section("versions", "Versions and play order", f"""
<p>Numbers from different benchmark versions or prompt formats are never put in one ranking or chart. Every number
  carries its version.</p>
<p>{status_badge(EARLIER)} {esc(ORDER_NOTE)} Re-asked with the same plays in a random order on {po["positions"]:,}
  positions, {esc(po["setup"])}'s error rate changed by {fmt(diff, 1, signed=True)} (95% interval {fmt(lo, 1)} to
  {fmt(hi, 1)}), {reading}. The current version shuffles the plays for every setup.</p>
<p>The earlier version also scored differently: every legal play at 0-ply, then the five best and the chosen play again
  at 2-ply. The current version evaluates every legal play at 2-ply.</p>""")


def _confidence(t: dict, extra: dict) -> str:
    c = " and ".join(_value(x) for x in t["confidence_cutoffs"])
    return _section("confidence", "Confidence", f"""
<ul>
  <li><strong>Sources.</strong> A setup's confidence is its probability for the play it chose. It comes from one of
    three sources: decision-model probability, letter probability, or none.</li>
  <li><strong>{esc(NA)} for choice-only setups.</strong> Confidence metrics (AUROC, ECE, Brier score, risk–coverage) are
    {esc(NA)} for setups that return only a choice. A recorded 1.0 from those setups is not 100% confidence.</li>
  <li><strong>Same source only.</strong> Confidence is compared only between setups with the same confidence source.</li>
  <li><strong>Group splits.</strong> Decisions whose plays were split into groups are left out of the confidence
    analyses: the probability then belongs to a smaller choice.</li>
  <li><strong>Cutoffs</strong> {c}, fixed before computing: decisions kept (probability at or above the cutoff), blunders
    among them and their mean equity lost. <strong>Surest quarter</strong>: the error rate of the
    {_value(t["surest_share"])} share of decisions with the highest probability.</li>
  <li><strong>Ranking scores (AUROC)</strong>: for the engine's best play (does a higher probability go with the best
    play?) and for warning before a blunder (does a lower probability go with a blunder?). <strong>Calibration gap
    (ECE)</strong>: for the event "the chosen play is the engine's best", in 10 bins, in points.</li>
  <li><strong>Confident and badly wrong:</strong> the setup gave its play at least
    {_value(t["very_confident_probability_at_least"])} and the play lost more than {_value(t["badly_wrong_loss_above"])}
    equity.</li>
</ul>
{_h3("confidence-held-out", "A cutoff chosen on half of the games")}
<p>{esc(t["cutoff_split_rule"])} {_value(t["cutoff_split_runs"])} splits, by game.</p>
{extra["held_out"]}""")


def _cost() -> str:
    return _section("cost", "Cost", """
<p>Cost per 1,000 decisions carries one of three labels. They are never mixed in one figure or ranking.</p>
<dl class="facts">
  <dt>API price estimate</dt><dd>The provider's list price, on a stated date, × the tokens its API reported. The bill
    itself was not checked.</dd>
  <dt>API-equivalent (subscription)</dt><dd>A setup played through a subscription, which is not billed per token,
    priced at the API list price × the tokens reported. Not money paid.</dd>
  <dt>Own hardware</dt><dd>A setup run on our own GPUs. It has no per-request price; no dollar figure is shown.</dd>
  <dt>List-price estimate; runs on our GPUs</dt><dd>A model that runs on our GPUs but has a maker's list price,
    priced at that list price × the tokens reported. Not money paid.</dd>
</dl>
<p>Every view shows how many of its decisions have a cost (cost coverage).</p>""")


def _time(t: dict) -> str:
    return _section("time", "Time", f"""
<ul>
  <li><strong>Request time</strong> runs from sending a request to receiving the answer. Time spent on retries and on
    waiting after provider errors is kept separate and is not part of it.</li>
  <li>Several requests can be in flight at once, so on our own hardware the time depends on the load.</li>
  <li>Time per decision is shown as the median and the 90th percentile.</li>
  <li><strong>Time budget:</strong> the share of decisions slower than {_value(t["time_budget_seconds"])} seconds.</li>
  <li>The v3 leagues had no clock, so no game could be lost on time. The risk of going over a time budget in play was
    therefore not measured; the share above only shows how often a setup needed more time.</li>
</ul>""")


def _limits() -> str:
    return _section("limits", "Limits", """
<ul>
  <li><strong>One kind of risk.</strong> The risk calls measure one kind of risk, being hit. Gammon risk and priming are
    not in it.</li>
  <li><strong>Different positions.</strong> Setups played different positions; league comparisons are not paired, and
    risk judgement is not adjusted for how hard the positions were.</li>
  <li><strong>Checker plays only.</strong> The games have no doubling cube, so the error rate leaves out cube decisions.
    The human scale is a rough guide.</li>
  <li><strong>The engine evaluation is not the strongest available.</strong> Plays are judged at 2-ply with GNU
    Backgammon, not by rollouts, in cubeless money equity with match score ignored. Small differences between close
    plays can be wrong. GNU Backgammon learned standard play, so its scores for early Nackgammon positions are likely
    less accurate.</li>
  <li><strong>The prompt steers.</strong> The strategy text and the question say what a good move looks like. The
    results measure how well models follow that guidance with the numbers in front of them, as much as how well they
    play.</li>
  <li><strong>Strategy text is in training data.</strong> Rules, opening tables and strategy articles are online.
    Backgammon is not an unfamiliar task.</li>
  <li><strong>Setups get different inputs.</strong> Rules text length and option groups differ between setups; rankings
    mark rows that got different inputs. The shared positions avoid group splits.</li>
  <li><strong>Providers vary.</strong> A hosted model can change without notice, and providers differ in quantization.
    We log them; we cannot control them.</li>
  <li><strong>Models only play each other</strong> and the anchor. Their strength against human players is not
    measured.</li>
</ul>""")


def _home_extras(extra: dict) -> str:
    """What B4 moves off the home page: what the input adds, learning from experience, routing and teams, tail risk."""
    return (_section("input", f"What the input adds {status_badge(EARLIER)}", extra["input"])
            + _section("learning", f"Learning from experience {status_badge(NOT_MEASURED)}",
                       "<p>Every decision is a separate request; models are not told how earlier games went.</p>")
            + _section("routing", f"Routing and teams {status_badge(PENDING)}",
                       "<p>Which decisions a cheap model can handle before handing over to a strong one, and whether a team "
                       "picks better plays than its best member, wait for the shared-position answers. A team \"oracle\", "
                       "the best answer any member gave, is an upper bound and never a working system; the earlier "
                       "version's team results are on <a href=\"../leagues/#earlier\">Leagues</a>.</p>")
            + _section("tail", "Tail risk", "<p>The 95th percentile of the equity lost per decision and the mean loss of "
                       "the worst 5% of decisions, per league.</p>" + extra["tail"]))


def _experiments() -> str:
    ex = _load("experiments.json")
    d = {k: esc(v["value"]) for k, v in ex["roll_schedule"]["numbers"].items()}
    a = {k: esc(v["value"]) for k, v in ex["anchor_checks"]["numbers"].items()}
    label = "Method finding, not a model result"
    dice = f"""
{_h3("exp-dice", "Sharing dice across matches")}
<p class="eyebrow">{label}</p>
<p>Each match has its own dice. We tested whether giving round <em>r</em> of every match the same roll schedule would
  make a league table less a matter of luck. The test used {d["players"]} GNU Backgammon players of known strength and no
  model, and replayed a round robin {d["replays_per_scheme"]} times under each scheme. The players' order was checked in a
  separate long run of {d["long_run_matches"]} matches: in all {d["long_run_pairs"]} pairs the stronger player scored more
  league points per match.</p>
<ul>
  <li><strong>Shared schedules made the table noisier.</strong> League points scattered more: standard deviation
    ×{d["sd_ratio"]} (95% interval {d["sd_ratio_lo"]} to {d["sd_ratio_hi"]}); variance ×{d["variance_ratio"]}
    ({d["variance_ratio_lo"]} to {d["variance_ratio_hi"]}).</li>
  <li><strong>The order got slightly worse.</strong> Rank correlation with the true order fell from {d["rho_a"]} to
    {d["rho_b"]} (difference {d["rho_diff"]}, 95% interval {d["rho_diff_lo"]} to {d["rho_diff_hi"]}). The stronger of two
    neighbours finished above the weaker in about {d["neighbour_above_pct"]}% of replays under both schemes.</li>
  <li><strong>Why.</strong> Mirrored games already cancel most of the dice luck within a match. Sharing schedules across
    matches cancels nothing more, and it puts all of a player's matches on the same dice, so their luck adds up: two
    matches of the same player correlated {d["match_corr_b"]} with shared schedules against {d["match_corr_a"]} without.</li>
</ul>
<p>So the leagues keep separate dice per match. The test players are not language models, whose play varies more from
  match to match.</p>"""
    anchor = f"""
{_h3("exp-anchor", "Checks of the reference player")}
<p class="eyebrow">{label}</p>
<p>The anchor is GNU Backgammon 1.08 at its Beginner level (0-ply, deterministic noise). We checked whether it is the
  same player on every machine.</p>
<ul>
  <li><strong>It is reproducible on x86-64.</strong> Replaying all {a["replayed"]} recorded anchor decisions on the x86-64
    build gives the recorded play in {a["replayed_same"]}; on an ARM build of the same package, in {a["arm_match_pct"]}%.</li>
  <li><strong>Another build plays differently.</strong> On the {a["positions"]} v1 positions, the x86-64 and ARM builds
    choose different plays in {a["differ_noise"]}. With the noise off, they differ in {a["differ_no_noise"]}, all exact
    ties, so the engine's own scoring does not depend on the build. Error rate {a["pr_x86"]} on x86-64 against
    {a["pr_arm"]} on ARM.</li>
  <li><strong>Why.</strong> The noise code sums hash bytes as <code>char</code>, which is signed on x86-64, but subtracts
    the mean of unsigned bytes. On x86-64 every noise draw is shifted by about {a["noise_shift_sd"]} standard deviations:
    the anchor understates its own winning chances and plays for gammons.</li>
  <li><strong>Gammons in self-play</strong> ({a["selfplay_games"]} games each): {a["gammons_x86_pct"]}% of games end in a
    gammon or backgammon on x86-64, {a["gammons_arm_pct"]}% on ARM, {a["gammons_no_noise_pct"]}% without noise.</li>
</ul>
<p>So the v3 anchor is "GNU Backgammon 1.08 Beginner, x86-64 build". It is a fixed reference, not GNU Backgammon's
  Beginner as published elsewhere. See also <a href="#v3-anchor">The anchor</a>.</p>"""
    return _section("experiments", "Method experiments", f"""
<p>Two experiments with GNU Backgammon players only, run to choose how the leagues work. They are method findings, not
  results about any model.</p>{dice}{anchor}""")


# ---------------------------------------------------------------- interface

def body(ctx: dict) -> str:
    """Inner HTML of <main> for method/index.html."""
    t, extra = ctx["thresholds"], ctx["extra"]
    return "\n".join([
        _intro(), _toc(), _setup(), _shared(ctx["shared_sets"]), _prompt(), _error_rate(t), _human_scale(),
        _risk(t, extra), _statistics(t), _thresholds(t), _status(), _versions(ctx["play_order"]),
        _confidence(t, extra), _cost(), _time(t), _limits(), _home_extras(extra), _archive("v3-notes.html"),
        _experiments(),
    ])


def archive_v1() -> str:
    """The earlier version's report sections (setup, models, error rate, results, teams, speed and cost, limits),
    each labelled 'Earlier version'. The prompt and 'Why it looks like this' are on the Method page."""
    intro = (f'<p class="note">{status_badge(EARLIER)} The sections below are kept from the earlier report, unchanged. '
             f'Their numbers come from the earlier version and are never ranked with current numbers. The prompt and '
             f'how it was built are on the <a href="../method/#prompt">Method</a> page.</p>\n')
    return intro + _earlier(_archive("v1-report.html"))


