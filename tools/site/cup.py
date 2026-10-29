"""Every match, the Hype Cup and the Nackgammon knockout (Can, 29 Oct 2026), from the snapshots: STATE/snap.db (v3.db)
and STATE/knockout.db (knockout-nack.db, tools/site/snapshot.py). Only match results: nothing here changes a standing,
an error rate or any other number of the leagues.

Where a v3 match was played: the leagues both players were members of when it started (as tools/ladder.py
played_in), a hidden league counting only for the pairs of its `only_pairs_of` setup when it names one.
- a hidden league, by the start of its note: "Early start for round N" (ladder round N), "Gap matches", "Late entry",
  "Hype Cup" (its note names the quarter-final); late-entry matches (matches.stage 'late-entry') are always late entries;
- else the shown league (1-3): a ladder-round match when one player came into that league by a ladder move (the note
  "ladder round N: ..." on the membership it left), round N (the later one if both did), else the league's season.
The Hype Cup bracket comes from content/hype_cup.json (the roster of 28 Oct 2026) and the stored pairings: each tie's
result is the pair's one valid finished match (any stage, late entries left out), "played" when a Cup league played
it and "stored" otherwise. A level match goes to the lower error rate in that match (tools/ladder.py cup_winner).
The knockout's ties are its leagues, named by their note ("Nackgammon knockout QF1: ..."), as run_knockout_nack.sh.
"""

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from common import CONTENT

CUP = json.loads((CONTENT / "hype_cup.json").read_text())
ERROR_SCALE = 500
MOVE = re.compile(r"ladder round (\d+): ")
QUARTER = re.compile(r"quarter-final (\d)")
LEAGUE_IN_NOTE = re.compile(r"League (\d)")
KNOCKOUT_TAG = re.compile(r"^Nackgammon knockout (\w+):")

STAGES = [("season", "League seasons"), ("ladder", "Ladder"), ("gap", "Gap matches"), ("cup", "Hype Cup"),
          ("knockout", "Nackgammon knockout"), ("late-entry", "Late entry, not in standings")]
LATE_NOTE = "not in standings"


def ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _hidden_kind(note: str) -> tuple[str, int | None]:
    m = re.match(r"Early start for round (\d+)", note)
    if m:
        return "ladder", int(m.group(1))
    for prefix, kind in (("Gap matches", "gap"), ("Late entry", "late-entry"), ("Hype Cup", "cup")):
        if note.startswith(prefix):
            return kind, None
    raise RuntimeError(f"hidden league with an unknown note: {note[:60]!r}")


def classify(conn) -> tuple[list[dict], list[dict]]:
    """(every valid finished v3 match with where it was played, every voided finished match with its reason)."""
    leagues = {r["id"]: dict(r) for r in conn.execute("SELECT id, hidden, only_pairs_of, note FROM leagues")}
    member = defaultdict(list)
    for r in conn.execute("""SELECT lp.league_id, lp.joined_at, lp.left_at, lp.note, p.name FROM league_players lp
                             JOIN players p ON p.id = lp.player_id ORDER BY lp.joined_at, lp.id"""):
        member[r["name"]].append(dict(r))

    def at(name, t):
        return {m["league_id"]: m for m in member[name] if m["joined_at"] <= t and (m["left_at"] is None or m["left_at"] > t)}

    def moved_in(name, m):
        """The ladder round that brought `name` into the league of membership `m`, if a ladder move did."""
        before = [x for x in member[name] if x["left_at"] and x["left_at"] <= m["joined_at"]]
        rounds = MOVE.findall(before[-1]["note"] or "") if before else []
        return int(rounds[-1]) if rounds else None

    games = dict(conn.execute("SELECT match_id, COUNT(*) FROM games WHERE winner_player IS NOT NULL GROUP BY 1"))
    out, voided = [], []
    for m in conn.execute("""SELECT m.id, m.started_at, m.finished_at, m.stage, m.score1, m.score2, m.winner, m.valid,
                                    m.void_reason, p1.name AS a, p2.name AS b
                             FROM matches m JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
                             WHERE m.status = 'finished' AND m.stage IS NOT NULL ORDER BY m.id"""):
        row = dict(id=m["id"], source="v3", finished=m["finished_at"], model1=m["a"], model2=m["b"],
                   score1=m["score1"], score2=m["score2"],
                   winner={1: m["a"], 2: m["b"]}.get(m["winner"]), games=games.get(m["id"], 0))
        if not m["valid"]:
            voided.append(dict(row, reason=m["void_reason"]))
            continue
        a, b = at(m["a"], m["started_at"]), at(m["b"], m["started_at"])
        both = [lid for lid in sorted(set(a) & set(b))
                if not leagues[lid]["only_pairs_of"] or leagues[lid]["only_pairs_of"] in (m["a"], m["b"])]
        hidden = [lid for lid in both if leagues[lid]["hidden"]]
        league = rnd = tie = None
        if hidden:
            note = leagues[hidden[0]]["note"] or ""
            kind, rnd = _hidden_kind(note)
            found = LEAGUE_IN_NOTE.search(note)
            league = int(found.group(1)) if found and kind != "cup" else None
            if kind == "cup":
                q = QUARTER.search(note)
                tie = f"QF{q.group(1)}" if q else None
        elif len(both) == 1:
            league = both[0]
            rounds = [r for r in (moved_in(m["a"], a[league]), moved_in(m["b"], b[league])) if r]
            kind, rnd = ("ladder", max(rounds)) if rounds else ("season", None)
        else:
            raise RuntimeError(f"match #{m['id']} {m['a']} v {m['b']}: played in leagues {both}, expected one")
        if m["stage"] == "late-entry":
            kind = "late-entry"
        out.append(dict(row, stage=kind, league=league, round=rnd, tie=tie, note=LATE_NOTE if kind == "late-entry" else None))
    return out, voided


def stage_label(m: dict) -> str:
    """The stage as one short phrase (the Matches page and the Cup's stored results)."""
    k = m["stage"]
    if k == "season":
        return f"League {m['league']} season"
    if k == "ladder":
        return f"Ladder round {m['round']}, League {m['league']}"
    if k == "gap":
        return f"Gap match, League {m['league']}"
    if k == "late-entry":
        return f"Late entry, League {m['league']}"
    if k == "cup":
        return f"Hype Cup {m['tie']}" if m.get("tie") else "Hype Cup"
    return f"Nackgammon knockout {m['tie']}"


def _match_rates(conn, plays: Path, match_id: int) -> dict[int, float | None]:
    """Error rate of each side in one match (tools/ladder.py match_error_rates): None while a decision is unscored."""
    turns = conn.execute("""SELECT t.id, t.player FROM turns t JOIN games g ON g.id = t.game_id
                            WHERE g.match_id = ? AND t.decided_by = 'model' AND t.legal_count >= 2""", (match_id,)).fetchall()
    marks = ",".join("?" * len(turns)) or "NULL"
    loss = {}
    for path in sorted(plays.glob("s*.db")):
        shard = ro(path)
        loss.update(shard.execute(f"SELECT turn_id, loss FROM plays WHERE turn_id IN ({marks})", [t for t, _ in turns]))
        shard.close()
    out = {}
    for side in (1, 2):
        mine = [t for t, s in turns if s == side]
        out[side] = (ERROR_SCALE * sum(loss[t] for t in mine) / len(mine)) if mine and all(t in loss for t in mine) else None
    return out


def _seed_of(seeds: dict, name: str) -> int:
    return next(s for s, n in seeds.items() if n == name)


def _bracket(seeds: dict, result_of) -> tuple[list[dict], str | None]:
    """The ties in content order, each with its two setups once known, and the champion (None until the final is
    decided). result_of(tie, a, b) -> dict(match fields, winner) or None while it is not played."""
    ties, winners = [], {}
    for t in CUP["ties"]:
        if "seeds" in t:
            a, b = (seeds[s] for s in t["seeds"])
        else:
            a, b = (winners.get(w) for w in t["winners_of"])
        tie = dict(tie=t["tie"], label=t["label"], model1=a, model2=b,
                   seed1=_seed_of(seeds, a) if a else None, seed2=_seed_of(seeds, b) if b else None,
                   from_ties=t.get("winners_of"))
        if a and b:
            tie.update(result_of(t["tie"], a, b))
        else:
            tie["state"] = "waits"
        if tie.get("winner"):
            winners[t["tie"]] = tie["winner"]
        ties.append(tie)
    return ties, winners.get(CUP["ties"][-1]["tie"])


def hype_cup(conn, plays: Path, matches: list[dict]) -> dict:
    seeds = {s["seed"]: s["name"] for s in CUP["seeds"]}
    pairs = {}
    for m in matches:
        if m["stage"] != "late-entry":
            pairs.setdefault(frozenset((m["model1"], m["model2"])), m)

    def result(tie, a, b):
        m = pairs.get(frozenset((a, b)))
        if m is None:
            return dict(state="to play")
        flip = m["model1"] != a
        out = dict(state="played" if m["stage"] == "cup" else "stored", match=m["id"],
                   score1=m["score2"] if flip else m["score1"], score2=m["score1"] if flip else m["score2"],
                   finished=m["finished"], where=stage_label(m), winner=m["winner"], level=m["winner"] is None)
        if m["winner"] is None:
            rates = _match_rates(conn, plays, m["id"])
            r1, r2 = (rates[2], rates[1]) if flip else (rates[1], rates[2])
            out.update(rate1=r1, rate2=r2)
            if r1 is not None and r2 is not None and r1 != r2:
                out["winner"] = a if r1 < r2 else b
        return out

    ties, champion = _bracket(seeds, result)
    return dict(name=CUP["name"], seeds=CUP["seeds"], ties=ties, champion=champion,
                state="finished" if champion else "in progress", roster_rule=CUP["roster_rule"],
                honesty=CUP["honesty"], stored_rule=CUP["stored_rule"], level_rule=CUP["level_rule"],
                new_matches=sum(t.get("state") == "played" for t in ties),
                stored_matches=sum(t.get("state") == "stored" for t in ties))


def knockout(path: Path) -> tuple[dict, list[dict]]:
    """The knockout bracket from STATE/knockout.db, and its finished matches for the Matches page."""
    seeds = {s["seed"]: s["name"] for s in CUP["seeds"]}
    by_tie, matches = {}, []
    if path.exists():
        conn = ro(path)
        for lg in conn.execute("SELECT id, note FROM leagues ORDER BY id"):
            tag = KNOCKOUT_TAG.match(lg["note"] or "")
            if not tag:
                continue
            rows = conn.execute(
                """SELECT m.id, m.started_at, m.finished_at, m.status, m.score1, m.score2, m.winner, p1.name AS a, p2.name AS b
                   FROM matches m JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
                   JOIN league_players x ON x.league_id = ? AND x.player_id = m.player1
                   JOIN league_players y ON y.league_id = ? AND y.player_id = m.player2
                   WHERE m.valid = 1 AND m.started_at >= (SELECT started_at FROM leagues WHERE id = ?)
                   ORDER BY m.id DESC""", (lg["id"], lg["id"], lg["id"])).fetchall()
            if rows:
                by_tie[tag.group(1)] = dict(rows[0])
        conn.close()
    for tie, m in sorted(by_tie.items(), key=lambda kv: kv[1]["id"]):
        if m["status"] == "finished":
            matches.append(dict(id=m["id"], source="knockout", finished=m["finished_at"], model1=m["a"], model2=m["b"],
                                score1=m["score1"], score2=m["score2"], winner={1: m["a"], 2: m["b"]}.get(m["winner"]),
                                stage="knockout", league=None, round=None, tie=tie, note=None))

    def result(tie, a, b):
        m = by_tie.get(tie)
        if m is None or {m["a"], m["b"]} != {a, b}:
            return dict(state="to play")
        if m["status"] != "finished":
            return dict(state="playing", match=m["id"])
        flip = m["a"] != a
        winner = {1: m["a"], 2: m["b"]}.get(m["winner"])
        return dict(state="played", match=m["id"], score1=m["score2"] if flip else m["score1"],
                    score2=m["score1"] if flip else m["score2"], finished=m["finished_at"], winner=winner,
                    level=winner is None)

    ties, champion = _bracket(seeds, result)
    return (dict(name=CUP["knockout"]["name"], label=CUP["knockout"]["label"], about=CUP["knockout"]["about"],
                 ties=ties, champion=champion, state="finished" if champion else "in progress",
                 played=sum(t.get("state") == "played" for t in ties), matches_total=len(ties)), matches)


def compute(state: Path, leagues: list[dict]) -> dict:
    """Matches (every valid finished match: v3 and the knockout), voided matches, the Cup and the knockout.
    `leagues` (build.compute's) give each match's decision links where the site has them."""
    conn = ro(state / "snap.db")
    matches, voided = classify(conn)
    cup = hype_cup(conn, state / "plays", matches)
    conn.close()
    ko, ko_matches = knockout(state / "knockout.db")
    links = {}
    for lg in leagues:
        for m in lg["matches_list"]:
            if m["match_id"] and m["status"] == "finished":
                links[m["match_id"]] = dict(dataset=lg["dataset"], model1=m["model1_first"], model2=m["model2_first"],
                                            names=(m["model1"], m["model2"]))
    for m in matches:
        got = links.get(m["id"])
        firsts = {}
        if got:
            for side, name in zip(("model1", "model2"), got["names"]):
                if got[side]:
                    firsts[name] = dict(got[side], dataset=got["dataset"])
        m["decisions"] = {side: firsts.get(m[side]) for side in ("model1", "model2")} if firsts else None
    for m in ko_matches:
        m["decisions"] = None
    every = matches + ko_matches
    for m in every:
        m["stage_label"] = stage_label(m)
    counts, parts = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for m in every:
        counts[m["stage"]] += 1
        if m["stage"] == "season":
            parts[m["stage"]][f"League {m['league']}"] += 1
        elif m["stage"] == "ladder":
            parts[m["stage"]][f"Ladder round {m['round']}"] += 1
    stages = [dict(stage=k, label=label, matches=counts[k],
                   parts=[dict(label=p, matches=n) for p, n in sorted(parts[k].items())]) for k, label in STAGES]
    return dict(matches=every, voided=voided, stages=stages, total=len(every), voided_total=len(voided),
                cup=cup, knockout=ko)
