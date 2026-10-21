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
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stats
from common import EARLIER, PROVISIONAL, PUBLISHED, ROOT, THRESHOLDS as T, slug

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
            label = f"Stopped ({done} / {len(fixtures)} matches)"
        left = Counter()
        for f in fixtures:
            if f["status"] != "finished":
                left[f["model1"]] += 1
                left[f["model2"]] += 1
        decisions = []
        for r in conn.execute(
            """SELECT t.id, g.id AS game_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END AS name,
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
            d = dict(id=r["id"], setup=r["name"], cluster=r["game_id"], invalid=r["decided_by"] == "fallback",
                     scored=p is not None, n=r["legal_count"], source=r["probability_source"], p=prob,
                     req_s=(r["request_ms"] if r["request_ms"] is not None else r["latency_ms"]) / 1000,
                     retry_s=(r["retry_ms"] or 0) / 1000, cost=r["cost_usd"], group=r["group_size"],
                     at=r["created_at"], tin=r["input_tokens"], tout=r["output_tokens"], treason=r["reasoning_tokens"])
            if p is not None:
                d.update(loss=p["loss"], phase=p["phase"], tag=p["tag"], **decision_from_plays(p))
                d["chosen"] = p["chosen"]
            decisions.append(d)
        leagues.append(dict(
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


def risk(decs: list[dict], key: str) -> dict:
    """Is the risk worth it? (B6) for one setup: the 2x2 of decision kind x what the model did."""
    cells = {k: [] for k in ("risk_took", "risk_safe", "safety_took", "safety_safe")}
    by_phase = defaultdict(lambda: {k: [] for k in cells})
    skipped = 0
    for d in decs:
        if d["invalid"] or not d["scored"]:
            continue
        shots, losses = d["shots"], d["losses"]
        least = min(shots)
        if least == max(shots):
            skipped += 1  # every play leaves the same number of hitting rolls: no risk choice
            continue
        safest = [i for i, s in enumerate(shots) if s == least]
        best = min(range(len(losses)), key=lambda i: losses[i])
        safety_pays = shots[best] == least or min(losses[i] for i in safest) < T["safety_pays_loss_below"]
        took = shots[d["chosen"]] > least
        k = ("safety_" if safety_pays else "risk_") + ("took" if took else "safe")
        cells[k].append(d)
        by_phase[d["phase"]][k].append(d)
    total = sum(len(v) for v in cells.values())

    def cell(v):
        withp = [d["p"] for d in v if d.get("p") is not None]
        return dict(n=len(v), share=len(v) / total if total else None,
                    mean_loss=sum(d["loss"] for d in v) / len(v) if v else None,
                    confidence=sum(withp) / len(withp) if withp and len(withp) == len(v) else None)

    def heads(c):
        rp = len(c["risk_took"]) + len(c["risk_safe"])
        sp = len(c["safety_took"]) + len(c["safety_safe"])
        return dict(risk_pays=rp, safety_pays=sp,
                    takes_risk=len(c["risk_took"]) / rp if rp else None,
                    needless_risk=len(c["safety_took"]) / sp if sp else None,
                    risk_too_few=too_few(rp), safety_too_few=too_few(sp))

    return dict(decisions=total, no_risk_choice=skipped, too_few=too_few(total),
                cells={k: cell(v) for k, v in cells.items()}, **heads(cells),
                phases={ph: heads(c) for ph, c in by_phase.items()})


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
            phases=breakdown(decs, "phase", PHASES), tags=breakdown(decs, "tag", TAGS),
            options=breakdown(decs, "options", OPTION_LABELS), gaps=breakdown(decs, "gapb", GAP_LABELS))
    return out


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
