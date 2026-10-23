"""Every number of the backgammon site, computed from the data files.

Inputs: the league snapshot (STATE/snap.db), GNUbg's play-by-play scores (STATE/plays/s*.db,
tools/site/score_plays.py), the earlier-version v1 set (replay.db + positions/v1.jsonl), the shared
position files (positions/*.jsonl, positions/build-log.json), the smoke-test rows (smoke/part-a.json)
and the fixed thresholds (content/thresholds.json). Output: plain dicts that build.py writes as the
site's data files and renders as pages; nothing else produces a number on the site.

Rules applied here (brief B1, B8, B9, B11):
- League numbers stay inside their league. A league that has not finished is Provisional.
- v1-set numbers are Earlier version and never share a table or chart with v3 numbers.
- Invalid answers (decided_by = 'fallback', or a v1 answer with an error) are counted and shown, and
  left out of every quality number: the runner's random play is not the model's choice.
- Error rate = 500 x mean 2-ply equity loss; every legal play evaluated at 2-ply.
- Intervals: bootstrap by game for league decisions, by position for v1/shared positions.
- A cell with fewer than min_decisions_per_cell decisions shows "Too few decisions".
"""

import glob
import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stats
from common import EARLIER, PROVISIONAL, PUBLISHED, ROOT, THRESHOLDS as T, slug
from decisions_export import PAGE_SIZE as DECISION_PAGE

sys.path.insert(0, str(ROOT / "tools"))
from league_web import last_activity, league_fixtures, league_state, league_table  # noqa: E402

SCALE = T["equity_scale"]
PHASES = ["opening", "contact", "holding", "race", "bear-off"]
TAGS = ["blitz", "back game", "holding", "priming", "low-anchor", "other"]
REAL_PROBS = {"decision", "logprobs"}
SHOTS = re.compile(r"the opponent hits with (\d+) of 36 rolls")


def utc(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def boot(seed_text: str) -> int:
    """A fixed seed per interval: the thresholds' seed plus a stable hash of what is resampled."""
    h = 0
    for ch in seed_text:
        h = (h * 131 + ord(ch)) % 2**31
    return T["bootstrap_seed"] + h


# --- Loading --------------------------------------------------------------------------------------

def load_plays(plays_dir: Path) -> dict[int, dict]:
    out = {}
    for path in sorted(glob.glob(str(plays_dir / "s*.db"))):
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            for tid, n, chosen, best, loss, phase, tag, data in db.execute(
                    "SELECT turn_id, n, chosen, best, loss, phase, tag, data FROM plays"):
                out[tid] = dict(n=n, chosen=chosen, best=best, loss=loss, phase=phase, tag=tag, data=data)
        except sqlite3.OperationalError:
            pass
        db.close()
    return out


def decision_from_plays(p: dict) -> dict:
    """Per-play arrays of a scored decision: losses, hitting rolls, gap between the two best plays."""
    data = json.loads(p["data"])
    eq = [d[1] for d in data]
    best = max(eq)
    top = sorted(eq, reverse=True)
    return dict(losses=[best - e for e in eq], shots=[d[2] for d in data],
                gap=(top[0] - top[1]) if len(top) > 1 else None)


def load_leagues(snap: Path, plays_dir: Path) -> dict:
    conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    plays = load_plays(plays_dir)
    leagues = []
    for row in conn.execute("SELECT * FROM leagues ORDER BY id").fetchall():
        lid = row["id"]
        roster = json.loads(row["models"])
        names = [m["name"] for m in roster]
        fixtures, games_won = league_fixtures(conn, lid)
        fixtures = [f for f in fixtures if f["stage"] == "league"]
        table = league_table(names, fixtures, games_won)
        done = sum(f["status"] == "finished" for f in fixtures)
        state = league_state(row, last_activity(conn, lid))
        if state == "finished":
            label = "Finished"
        elif state == "live":
            label = f"Running ({done} / {len(fixtures)} matches)"
        else:
            label = f"Stopped (paused; {done} / {len(fixtures)} matches)"
        left = Counter()
        for f in fixtures:
            if f["status"] != "finished":
                left[f["model1"]] += 1
                left[f["model2"]] += 1
        decisions = []
        for r in conn.execute(
            """SELECT t.id, g.id AS game_id, g.match_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name,
                      t.decided_by, t.legal_count, t.probability_source, t.probabilities, t.chosen_position,
                      t.request_ms, t.latency_ms, t.retry_ms, t.cost_usd, t.group_size, t.created_at,
                      t.input_tokens, t.output_tokens, t.reasoning_tokens
               FROM turns t JOIN games g ON g.id = t.game_id JOIN league_matches lm ON lm.match_id = g.match_id
               WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')""", (lid,)):
            p = plays.get(r["id"])
            prob = None
            if r["probability_source"] in REAL_PROBS and r["probabilities"] and r["chosen_position"] is not None:
                probs = json.loads(r["probabilities"])
                if r["chosen_position"] < len(probs):
                    prob = probs[r["chosen_position"]]
            d = dict(id=r["id"], setup=r["name"], cluster=r["game_id"], match=r["match_id"], invalid=r["decided_by"] == "fallback",
                     scored=p is not None, n=r["legal_count"], source=r["probability_source"], p=prob,
                     req_s=(r["request_ms"] if r["request_ms"] is not None else r["latency_ms"]) / 1000,
                     retry_s=(r["retry_ms"] or 0) / 1000, cost=r["cost_usd"], group=r["group_size"],
                     at=r["created_at"], tin=r["input_tokens"], tout=r["output_tokens"], treason=r["reasoning_tokens"])
            if p is not None:
                d.update(loss=p["loss"], phase=p["phase"], tag=p["tag"], **decision_from_plays(p))
                d["chosen"] = p["chosen"]
            decisions.append(d)
        # Where each match's decisions sit in Every decision: per setup, scored decisions in turn order, 50 a page.
        order = defaultdict(list)
        for d in decisions:
            if d["scored"]:
                order[d["setup"]].append(d["id"])
        first = {}
        for ids in order.values():
            ids.sort()
        by_match = {}
        for d in decisions:
            if d["scored"]:
                k = (d["match"], d["setup"])
                if k not in by_match or d["id"] < by_match[k]:
                    by_match[k] = d["id"]
        position = {setup: {tid: i for i, tid in enumerate(ids)} for setup, ids in order.items()}
        for (mid, setup), tid in by_match.items():
            first[(mid, setup)] = dict(id=tid, slug=slug(setup), page=position[setup][tid] // DECISION_PAGE + 1)
        matches_list = []
        for f in fixtures:
            gw = games_won.get(f["match_id"], [0, 0]) if f["match_id"] else [0, 0]
            matches_list.append(dict(
                matchday=f["matchday"], model1=f["model1"], model2=f["model2"], match_id=f["match_id"],
                status=f["status"], score1=f["score1"] or 0, score2=f["score2"] or 0, games=sum(gw),
                model1_first=first.get((f["match_id"], f["model1"])), model2_first=first.get((f["match_id"], f["model2"]))))
        leagues.append(dict(
            matches_list=matches_list,
            id=lid, dataset=f"league-{lid}", roster=roster, names=names, table=table,
            fixtures=len(fixtures), done=done, state=state, status_label=label,
            metric_status=PUBLISHED if state == "finished" else PROVISIONAL,
            started=row["started_at"], finished=row["finished_at"], left=dict(left),
            games=conn.execute("""SELECT COUNT(*) FROM games g JOIN league_matches lm ON lm.match_id = g.match_id
                                  WHERE lm.league_id = ? AND g.winner_player IS NOT NULL""", (lid,)).fetchone()[0],
            gammons=dict(conn.execute(
                """SELECT CASE g.winner_player WHEN 1 THEN lm.model1 ELSE lm.model2 END, COUNT(*)
                   FROM games g JOIN matches m ON m.id = g.match_id JOIN league_matches lm ON lm.match_id = g.match_id
                   WHERE lm.league_id = ? AND lm.stage = 'league' AND m.status = 'finished'
                     AND g.result IN ('gammon', 'backgammon') GROUP BY 1""", (lid,)).fetchall()),
            decisions=decisions))
    turns_total = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    last = conn.execute("SELECT MAX(created_at) FROM turns").fetchone()[0]
    conn.close()
    return dict(leagues=leagues, plays=len(plays), turns_total=turns_total, last_move=last)


def load_v1(replay_db: Path, v1_positions: Path) -> dict:
    """The earlier-version v1 set: 1,000 positions, 17 setups, every play's 2-ply equity."""
    meta = {}
    for line in v1_positions.read_text().splitlines():
        r = json.loads(line)
        meta[r["replay_position_id"]] = r
    db = sqlite3.connect(f"file:{replay_db}?mode=ro", uri=True)
    eq = defaultdict(dict)
    for pid, play, e in db.execute("SELECT position_id, play, equity FROM equities"):
        eq[pid][play] = e
    positions = {}
    for pid, options in db.execute("SELECT id, options FROM positions"):
        opts = json.loads(options)
        plays = list(opts)
        e = [eq[pid][p] for p in plays]
        best = max(e)
        top = sorted(e, reverse=True)
        shots = [int(SHOTS.search(opts[p]).group(1)) for p in plays]
        positions[pid] = dict(plays=plays, losses=[best - x for x in e], shots=shots,
                              gap=(top[0] - top[1]) if len(top) > 1 else None,
                              phase=meta[pid]["phase"], tag=meta[pid]["tag"], key=meta[pid]["id"])
    decisions = []
    for pid, model, choice, probs, ms, error, tin, tout in db.execute(
            "SELECT position_id, model, choice, probabilities, latency_ms, error, input_tokens, output_tokens "
            "FROM answers ORDER BY model, position_id"):
        pos = positions[pid]
        invalid = error is not None or choice is None or choice not in pos["plays"]
        d = dict(id=pos["key"], setup=model, cluster=pid, invalid=invalid, scored=not invalid, n=len(pos["plays"]),
                 req_s=ms / 1000 if ms is not None else None, retry_s=None, cost=None, group=None,
                 tin=tin, tout=tout, phase=pos["phase"], tag=pos["tag"])
        if not invalid:
            i = pos["plays"].index(choice)
            pr = json.loads(probs) if probs else None
            d.update(chosen=i, loss=pos["losses"][i], losses=pos["losses"], shots=pos["shots"], gap=pos["gap"],
                     p=pr.get(choice) if pr else None)
        decisions.append(d)
    setups = sorted({d["setup"] for d in decisions})
    # A setup whose every answer is one play at probability 1 returns only a choice (B11): no confidence.
    choice_only = {s for s in setups if all(d.get("p") == 1.0 for d in decisions if d["setup"] == s and not d["invalid"])}
    for d in decisions:
        d["source"] = "choice_only" if d["setup"] in choice_only else "probabilities"
        if d["setup"] in choice_only:
            d["p"] = None
    db.close()
    return dict(dataset="v1-set", positions=positions, decisions=decisions, setups=setups, choice_only=choice_only)


def shared_sets(root: Path) -> dict:
    """How the v3 shared positions were drawn: counts and option ranges from the frozen files."""
    log = json.loads((root / "positions/build-log.json").read_text())
    for entry in log.values():
        if "games_used" in entry:
            entry["games"] = entry["games_used"][1] - entry["games_used"][0]
    parts = {}
    for name in ["v1", "new", "nackgammon", "opening-control", "extension"]:
        rows = [json.loads(x) for x in (root / f"positions/{name}.jsonl").read_text().splitlines()]
        n = [len(r["legal_plays"]) for r in rows]
        parts[name] = dict(positions=len(rows), min_plays=min(n), max_plays=max(n),
                           phases=dict(Counter(r["phase"] for r in rows)))
    standard = parts["v1"]["positions"] + parts["new"]["positions"]
    return dict(parts=parts, standard=standard, build_log=log,
                min_plays=min(parts[p]["min_plays"] for p in ("v1", "new")),
                max_plays=max(parts[p]["max_plays"] for p in ("v1", "new")))


# --- Measures -------------------------------------------------------------------------------------

def too_few(n: int) -> bool:
    return n < T["min_decisions_per_cell"]


def calibration(p: list[float], right: list[bool]) -> dict:
    """AUROC (probability of the chosen play vs 'right' = engine's best play), ECE with 10 bins, Brier score."""
    pos = [x for x, r in zip(p, right) if r]
    neg = [x for x, r in zip(p, right) if not r]
    out = dict(brier=sum((x - r) ** 2 for x, r in zip(p, right)) / len(p))
    bins = defaultdict(list)
    for x, r in zip(p, right):
        bins[min(int(x * 10), 9)].append((x, r))
    out["ece"] = sum(len(b) / len(p) * abs(sum(x for x, _ in b) / len(b) - sum(r for _, r in b) / len(b))
                     for b in bins.values())
    if pos and neg:
        ranked = sorted([(x, 1) for x in pos] + [(x, 0) for x in neg])
        i, rank_sum = 0, 0.0
        while i < len(ranked):
            j = i
            while j < len(ranked) and ranked[j][0] == ranked[i][0]:
                j += 1
            rank_sum += (i + j + 1) / 2 * sum(1 for k in range(i, j) if ranked[k][1])
            i = j
        out["auroc"] = (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return out


def quality(decs: list[dict], key: str) -> dict:
    """Quality, tail risk, time and cost of one setup's decisions in one dataset."""
    valid = [d for d in decs if not d["invalid"]]
    scored = [d for d in valid if d["scored"]]
    out = dict(decisions=len(decs), invalid=len(decs) - len(valid), scored=len(scored),
               engine_scored=sum(1 for d in decs if d["scored"]))
    if scored:
        loss = [d["loss"] for d in scored]
        clusters = defaultdict(lambda: [0.0, 0])
        for d in scored:
            c = clusters[d["cluster"]]
            c[0] += d["loss"]
            c[1] += 1
        sums, counts = zip(*clusters.values())
        er = SCALE * sum(loss) / len(loss)
        lo, hi = stats.ratio_interval(sums, counts, SCALE, T["bootstrap_resamples"], boot(key), T["interval"])
        out.update(
            too_few=too_few(len(scored)), error_rate=er, error_lo=lo, error_hi=hi, clusters=len(clusters),
            best_share=sum(x < T["best_play_loss_below"] for x in loss) / len(loss),
            blunder_share=sum(x > T["blunder_loss_above"] for x in loss) / len(loss),
            p95_loss=stats.quantile(loss, T["tail_quantile"]),
            worst_mean=stats.worst_mean(loss, T["worst_share"]),
        )
        # Confidence only for setups that return probabilities; group-split decisions are left out (design A5).
        withp = [d for d in scored if d.get("p") is not None and not d.get("group")]
        if withp:
            cbw = [d for d in withp if d["p"] >= T["very_confident_probability_at_least"]
                   and d["loss"] > T["badly_wrong_loss_above"]]
            vc = [d for d in withp if d["p"] >= T["very_confident_probability_at_least"]]
            out.update(confidence_n=len(withp), confident_badly_wrong=len(cbw) / len(withp),
                       very_confident=len(vc) / len(withp), mean_confidence=sum(d["p"] for d in withp) / len(withp),
                       **calibration([d["p"] for d in withp], [d["loss"] < T["best_play_loss_below"] for d in withp]))
    times = [d["req_s"] for d in valid if d["req_s"] is not None]
    if times:
        out.update(time_median=stats.median(times), time_p90=stats.quantile(times, 0.9),
                   over_budget=sum(t > T["time_budget_seconds"] for t in times) / len(times))
    retry = [d["retry_s"] for d in decs if d.get("retry_s") is not None]
    if retry:
        out["retry_mean"] = sum(retry) / len(retry)
    priced = [d for d in decs if d.get("cost") is not None]
    out["cost_coverage"] = len(priced) / len(decs) if decs else 0
    if decs and len(priced) == len(decs):
        out["usd_per_1000"] = 1000 * sum(d["cost"] for d in priced) / len(decs)
    tin = [d["tin"] for d in decs if d.get("tin")]
    if tin:
        out["tokens_in"] = sum(tin) / len(tin)
        out["tokens_out"] = sum(d["tout"] or 0 for d in decs if d.get("tin")) / len(tin)
    groups = sorted({d["group"] for d in decs if d.get("group")})
    out["group_sizes"] = groups
    out["grouped"] = sum(1 for d in decs if d.get("group"))
    sources = Counter(d.get("source") for d in decs if d.get("source"))
    out["probability_source"] = sources.most_common(1)[0][0] if sources else None
    dates = sorted(d["at"][:10] for d in decs if d.get("at"))
    if dates:
        out["first_date"], out["last_date"] = dates[0], dates[-1]
    return out


MARGINS = {"main": T["risk_margin"], "robust": T["risk_margin_robust"]}
CALLS = ["right_risk", "wrong_risk", "needless", "missed", "right_safety"]
BANDS = ["small", "medium", "big"]


def band(x: float, edges=None) -> str:
    """small below the first edge, medium up to and including the second, big above it (B6.3)."""
    a, b = edges or T["stake_bands"]
    return "small" if x < a else ("medium" if x <= b else "big")


def play_call(shots: list, losses: list, i: int, margin: float) -> tuple:
    """B6.1 for play i of one position: (position class, risk call, stake, extra hitting rolls over the minimum).
    Hitting rolls are the numbers the model was shown; stake = the best safe play's equity loss against the engine's
    best play; class 'none' (No trade-off) when every legal play leaves the same number of hitting rolls."""
    least = min(shots)
    if least == max(shots):
        return "none", None, None, 0
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call, stake, shots[i] - least


def risk_class(d: dict, margin: float | None = None) -> tuple[str | None, str | None, float | None]:
    """One decision: (position class, risk call, stake); (None, None, None) for invalid or unscored decisions."""
    if d["invalid"] or not d["scored"]:
        return None, None, None
    cls, call, stake, _ = play_call(d["shots"], d["losses"], d["chosen"], T["risk_margin"] if margin is None else margin)
    return cls, call, stake


def _items(d: dict, margin: float, who: str | None) -> list[tuple]:
    """What one decision adds to a setup's risk metrics: (weight, class, call, stake, loss, extra rolls, p). A real
    setup has one item of weight 1; the computed reference rows spread a position over what they would play: Safest
    the best safe play, Random every legal play with equal weight."""
    shots, losses = d["shots"], d["losses"]
    if who is None:
        cls, call, stake, extra = play_call(shots, losses, d["chosen"], margin)
        p = d.get("p") if not d.get("group") else None
        return [(1.0, cls, call, stake, d["loss"], extra, p)]
    if who == "Safest":
        least = min(shots)
        i = min((j for j, s in enumerate(shots) if s == least), key=lambda j: losses[j])
        cls, call, stake, extra = play_call(shots, losses, i, margin)
        return [(1.0, cls, call, stake, losses[i], extra, None)]
    w = 1.0 / len(shots)
    out = []
    for i in range(len(shots)):
        cls, call, stake, extra = play_call(shots, losses, i, margin)
        out.append((w, cls, call, stake, losses[i], extra, None))
    return out


def _share(n: float, den: float) -> dict:
    return dict(n=n, den=den, share=n / den if den else None)


def risk_metrics(decs: list[dict], key: str, margin: float, who: str | None = None, phases: bool = True) -> dict:
    """B6.2 and B6.3 for one setup at one margin. Every share carries its count and denominator; averages below the
    minimum sample show Too few (B9). who='Safest' or 'Random' computes that reference row on these positions."""
    valid = [d for d in decs if not d["invalid"] and d["scored"]]
    calls = {c: 0.0 for c in CALLS}
    loss_by = {c: 0.0 for c in CALLS + ["none"]}
    classes = {"none": 0.0, "risk": 0.0, "safety": 0.0}
    stake = {b: dict(risk_pays=0.0, right_risk=0.0, missed=0.0, wrong_risk=0.0) for b in BANDS}
    needless_by_loss = {b: 0.0 for b in BANDS}
    size = {"right": [0.0, 0.0], "bad": [0.0, 0.0]}
    conf_taken, conf_missed = [], []
    clusters = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # right risks, Risk pays, right safety, Safety pays
    for d in valid:
        for w, cls, call, st, loss, extra, p in _items(d, margin, who):
            classes[cls] += w
            if cls == "none":
                loss_by["none"] += w * loss
                continue
            calls[call] += w
            loss_by[call] += w * loss
            c = clusters[d["cluster"]]
            if cls == "risk":
                b = band(st)
                stake[b]["risk_pays"] += w
                if call in stake[b]:
                    stake[b][call] += w
                c[1] += w
                c[0] += w * (call == "right_risk")
            else:
                c[3] += w
                c[2] += w * (call == "right_safety")
                if call == "needless":
                    needless_by_loss[band(loss, T["needless_loss_bands"])] += w
            if call == "right_risk":
                size["right"][0] += w * extra
                size["right"][1] += w
            elif call in ("wrong_risk", "needless"):
                size["bad"][0] += w * extra
                size["bad"][1] += w
            if p is not None and call in ("right_risk", "wrong_risk", "needless"):
                conf_taken.append((p, call == "right_risk"))
            if p is not None and call == "missed":
                conf_missed.append(p)
    # Position classes are whole positions; the reference rows' play weights sum to 1 per position.
    classes = {k: round(v, 6) for k, v in classes.items()}
    for v in stake.values():
        v["risk_pays"] = round(v["risk_pays"], 6)
    rp, sp = classes["risk"], classes["safety"]
    out = dict(margin=margin, scored=len(valid), trade_off=rp + sp, no_trade_off=classes["none"],
               risk_pays=rp, safety_pays=sp, calls=calls, reference=who)
    if rp and sp:
        cl = list(clusters.values())
        lo, hi = stats.judgement_interval([c[0] for c in cl], [c[1] for c in cl], [c[2] for c in cl],
                                          [c[3] for c in cl], T["bootstrap_resamples"], boot(f"{key}/j"), T["interval"])
        out.update(judgement=50 * (calls["right_risk"] / rp + calls["right_safety"] / sp), judgement_lo=lo,
                   judgement_hi=hi, judgement_na=None)
    else:
        out.update(judgement=None, judgement_na="N/A: no " + ("Risk pays" if not rp else "Safety pays") + " decisions")
    taken = calls["right_risk"] + calls["wrong_risk"] + calls["needless"]
    out.update(found=_share(calls["right_risk"], rp), right_safety=_share(calls["right_safety"], sp),
               good=_share(calls["right_risk"], taken), missed=_share(calls["missed"], rp),
               needless=_share(calls["needless"], sp), wrong=_share(calls["wrong_risk"], rp))
    # B6.2 item 8: the error rate by risk-call category; the six parts sum to the error rate.
    n = len(valid)
    out["by_call"] = {k: SCALE * v / n if n else None for k, v in loss_by.items()}
    out["error_rate"] = SCALE * sum(loss_by.values()) / n if n else None
    out["stake"] = {b: dict(risk_pays=v["risk_pays"], found=_share(v["right_risk"], v["risk_pays"]),
                            missed=_share(v["missed"], v["risk_pays"]), wrong=_share(v["wrong_risk"], v["risk_pays"]))
                    for b, v in stake.items()}
    out["needless_by_loss"] = {b: _share(v, sp) for b, v in needless_by_loss.items()}
    out["size"] = {k: dict(n=v[1], too_few=too_few(v[1]), mean=v[0] / v[1] if v[1] else None) for k, v in size.items()}
    # B6.3 confidence on the call: ranking score only (the probability is for the chosen play, not for the risk).
    conf = dict(taken_n=len(conf_taken), missed_n=len(conf_missed), auroc_right_risk=None, missed_mean_p=None)
    if conf_taken and not too_few(len(conf_taken)):
        conf["auroc_right_risk"] = calibration([p for p, _ in conf_taken], [r for _, r in conf_taken]).get("auroc")
    if conf_missed and not too_few(len(conf_missed)):
        conf["missed_mean_p"] = sum(conf_missed) / len(conf_missed)
    out["confidence"] = conf if (conf_taken or conf_missed) else None
    # B6.5 risk map: x = Risk pays without the right risk, y = needless risks; colour = wrong among x.
    out["map"] = None
    if rp and sp:
        bad = calls["missed"] + calls["wrong_risk"]
        out["map"] = dict(x=bad / rp, y=calls["needless"] / sp, wrong_share=calls["wrong_risk"] / bad if bad else None)
    if phases:
        out["phases"] = {ph: risk_metrics([d for d in valid if d["phase"] == ph], key + "/" + ph, margin, who, False)
                         for ph in PHASES}
    return out


def risk(decs: list[dict], key: str, who: str | None = None) -> dict:
    """Every risk metric at the main margin and at the robustness margin (B6.6)."""
    return {m: risk_metrics(decs, f"{key}/{m}", v, who) for m, v in MARGINS.items()}


def confidence(decs: list[dict], key: str) -> dict | None:
    """The Confidence tab (B4) for a setup that returns probabilities; None otherwise (N/A). Group-split decisions
    are left out. Averages below the minimum sample show Too few (B9)."""
    withp = [d for d in decs if not d["invalid"] and d["scored"] and d.get("p") is not None and not d.get("group")]
    if not withp:
        return None
    blunder = T["blunder_loss_above"]
    out = dict(n=len(withp), too_few=too_few(len(withp)), cutoffs={})
    for c in T["confidence_cutoffs"]:
        kept = [d for d in withp if d["p"] >= c]
        nb = sum(d["loss"] > blunder for d in kept)
        out["cutoffs"][str(c)] = dict(kept=_share(len(kept), len(withp)), blunders=_share(nb, len(kept)),
                                      too_few=too_few(len(kept)),
                                      mean_loss=sum(d["loss"] for d in kept) / len(kept) if kept else None)
    ps = sorted((d["p"] for d in withp), reverse=True)
    cut = ps[math.ceil(T["surest_share"] * len(ps)) - 1]
    sure = [d for d in withp if d["p"] >= cut]
    out["surest"] = dict(n=len(sure), too_few=too_few(len(sure)), cut=cut,
                         error_rate=SCALE * sum(d["loss"] for d in sure) / len(sure))
    best = calibration([d["p"] for d in withp], [d["loss"] < T["best_play_loss_below"] for d in withp])
    warn = calibration([d["p"] for d in withp], [d["loss"] <= blunder for d in withp])
    out.update(auroc_best=best.get("auroc"), auroc_blunder=warn.get("auroc"), ece=best["ece"],
               confident_badly_wrong=_share(sum(d["p"] >= T["very_confident_probability_at_least"]
                                                and d["loss"] > T["badly_wrong_loss_above"] for d in withp), len(withp)))
    out["held_out"] = held_out_cutoff(withp, key)
    return out


def held_out_cutoff(withp: list[dict], key: str) -> dict:
    """content/thresholds.json cutoff_split_rule: chosen on half of the games, scored on the other half."""
    import random
    games = defaultdict(list)
    for i, d in enumerate(withp):
        games[d["cluster"]].append(i)
    units = list(games.values())
    p = [d["p"] for d in withp]
    bl = [d["loss"] > T["blunder_loss_above"] for d in withp]
    rng = random.Random(boot(key + "/split"))
    kept_sum = blunder_sum = 0.0
    none = 0
    runs = T["cutoff_split_runs"]
    for _ in range(runs):
        order = list(range(len(units)))
        rng.shuffle(order)
        half = len(units) // 2
        first = [i for u in order[:half] for i in units[u]]
        test = [i for u in order[half:] for i in units[u]]
        worst = max((p[i] for i in first if bl[i]), default=None)
        above = [p[i] for i in first if worst is None or p[i] > worst]
        if not above or not test:
            none += 1
            continue
        cutoff = min(above)
        kept = [i for i in test if p[i] >= cutoff]
        kept_sum += len(kept) / len(test)
        blunder_sum += (sum(bl[i] for i in kept) / len(kept)) if kept else 0.0
    done = runs - none
    return dict(runs=runs, no_cutoff=none, kept=kept_sum / done if done else None,
                blunders=blunder_sum / done if done else None)


def breakdown(decs: list[dict], field: str, labels: list) -> dict:
    """Error rate per label of one field (phase, tag, options bucket, gap bucket); n < min shows Too few."""
    groups = defaultdict(list)
    for d in decs:
        if d["invalid"] or not d["scored"]:
            continue
        groups[d[field]].append(d["loss"])
    out = {}
    for lab in labels:
        v = groups.get(lab, [])
        out[str(lab)] = dict(n=len(v), too_few=too_few(len(v)), error_rate=SCALE * sum(v) / len(v) if v else None)
    return out


def option_bucket(n: int) -> str:
    for lo, hi in T["option_buckets"]:
        if n >= lo and (hi is None or n <= hi):
            return f"{lo}\u2013{hi}" if hi else f"{lo}+"
    return "1"


def gap_bucket(g) -> str:
    a, b = T["gap_buckets"]
    if g is None:
        return "n/a"
    return f"under {a}" if g < a else (f"{a} to {b}" if g <= b else f"over {b}")


OPTION_LABELS = [f"{lo}\u2013{hi}" if hi else f"{lo}+" for lo, hi in T["option_buckets"]]
GAP_LABELS = [f"under {T['gap_buckets'][0]}", f"{T['gap_buckets'][0]} to {T['gap_buckets'][1]}",
              f"over {T['gap_buckets'][1]}"]


def annotate(decs: list[dict]) -> None:
    for d in decs:
        d["options"] = option_bucket(d["n"])
        d["gapb"] = gap_bucket(d.get("gap"))


def dataset_summary(dataset: str, decisions: list[dict], setups: list[str]) -> dict:
    annotate(decisions)
    per = defaultdict(list)
    for d in decisions:
        per[d["setup"]].append(d)
    out = {}
    for name in setups:
        decs = per.get(name, [])
        key = f"{dataset}/{name}"
        out[name] = dict(
            name=name, slug=slug(name), quality=quality(decs, key), risk=risk(decs, key),
            confidence=confidence(decs, key),
            phases=breakdown(decs, "phase", PHASES), tags=breakdown(decs, "tag", TAGS),
            options=breakdown(decs, "options", OPTION_LABELS), gaps=breakdown(decs, "gapb", GAP_LABELS),
            quality_phases={ph: quality([d for d in decs if d.get("phase") == ph], f"{key}/{ph}") for ph in PHASES})
    return out


REFERENCE_LABEL = {"Safest": "computed: always the best safe play", "Random": "computed: every legal play equally likely"}


def references(dataset: str, decisions: list[dict], setups: list[str]) -> dict:
    """B6.4 reference rows for a league where the Safest or Random program did not play: computed on the positions
    of this league's scored decisions (every setup's), never ranked and never champions."""
    return {f"{who} (computed)": dict(name=f"{who} (computed)", slug=slug(f"{who} computed"), reference=who,
                                      label=REFERENCE_LABEL[who], positions=sum(1 for d in decisions if not d["invalid"] and d["scored"]),
                                      risk=risk(decisions, f"{dataset}/ref/{who}", who))
            for who in ("Safest", "Random") if who not in setups}


def paired(decs_a: list[dict], decs_b: list[dict], key: str) -> dict:
    """b minus a on the positions both answered validly (v1 set / shared positions only)."""
    a = {d["id"]: d for d in decs_a if not d["invalid"] and d["scored"]}
    b = {d["id"]: d for d in decs_b if not d["invalid"] and d["scored"]}
    common = sorted(set(a) & set(b))
    if not common:
        return dict(positions=0)
    diffs = [b[i]["loss"] - a[i]["loss"] for i in common]
    diff = SCALE * sum(diffs) / len(diffs)
    lo, hi = stats.paired_interval(diffs, SCALE, T["bootstrap_resamples"], boot(key), T["interval"])
    phases = {}
    for ph in PHASES:
        sub = [b[i]["loss"] - a[i]["loss"] for i in common if a[i]["phase"] == ph]
        if too_few(len(sub)):
            phases[ph] = dict(n=len(sub), too_few=True)
        else:
            plo, phi = stats.paired_interval(sub, SCALE, T["bootstrap_resamples"], boot(key + ph), T["interval"])
            phases[ph] = dict(n=len(sub), too_few=False, diff=SCALE * sum(sub) / len(sub), lo=plo, hi=phi,
                              verdict=stats.verdict(plo, phi))
    fixed = sum(1 for i in common if a[i]["loss"] > T["blunder_loss_above"] >= b[i]["loss"])
    broken = sum(1 for i in common if b[i]["loss"] > T["blunder_loss_above"] >= a[i]["loss"])
    # B9: phase-level effects pointing in different directions, each excluding zero (phase verdicts are exploratory).
    signs = {(p["hi"] < 0) - (p["lo"] > 0) for p in phases.values() if not p["too_few"] and (p["hi"] < 0 or p["lo"] > 0)}
    overall = "Depends on the position" if signs == {1, -1} else stats.verdict(lo, hi)
    return dict(positions=len(common), diff=diff, lo=lo, hi=hi, verdict=overall, phases=phases,
                fixed=fixed, broken=broken,
                fixed_loss=sum(a[i]["loss"] - b[i]["loss"] for i in common if b[i]["loss"] < a[i]["loss"]),
                broken_loss=sum(b[i]["loss"] - a[i]["loss"] for i in common if b[i]["loss"] > a[i]["loss"]))


def disagreements(v1: dict) -> dict:
    """Positions of the v1 set where the setups chose different plays."""
    by_pos = defaultdict(dict)
    for d in v1["decisions"]:
        if not d["invalid"]:
            by_pos[d["cluster"]][d["setup"]] = d["chosen"]
    rows = []
    for pid, picks in by_pos.items():
        pos = v1["positions"][pid]
        c = Counter(picks.values())
        best = min(range(len(pos["losses"])), key=lambda i: pos["losses"][i])
        common, k = c.most_common(1)[0]
        rows.append(dict(id=pos["key"], pid=pid, phase=pos["phase"], plays=len(pos["plays"]), setups=len(picks),
                         distinct=len(c), best_share=c.get(best, 0) / len(picks),
                         common=pos["plays"][common], common_share=k / len(picks),
                         common_loss=pos["losses"][common], best=pos["plays"][best]))
    rows.sort(key=lambda r: (-r["distinct"], r["best_share"], r["id"]))
    dist = Counter(r["distinct"] for r in rows)
    return dict(positions=len(rows), all_agree=dist.get(1, 0), distribution=dict(sorted(dist.items())), rows=rows)
