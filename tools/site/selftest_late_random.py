#!/usr/bin/env python3
"""Self-test and offline preview of a late entry's All benches score against Random on its own positions
(build.late_entry_summaries' random_same_positions, bench_scores.random_of; Ümit #6225).

    python3 tools/site/selftest_late_random.py                      # synthetic check only
    python3 tools/site/selftest_late_random.py --state STATE NAME…  # also the preview for late entrants NAME…

Synthetic: analysis.references' computed Random error rate equals 500 x the mean, over the valid scored positions, of
the mean loss of every legal play (invalid and unscored decisions left out), and random_of picks it for a late row and
the league's Random row otherwise. Preview (read-only: STATE/snap.db and STATE/plays/s*.db, the site's own inputs):
per entrant, its error rate, the score today (League N's played Random) and the score against Random computed on its
own positions, with the site's own decision() and references(). Exit 0 when the synthetic check passes. Writes nothing.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as A  # noqa: E402
import bench_scores as B  # noqa: E402
from common import LATE_ENTRY  # noqa: E402


def synthetic() -> list[str]:
    bad = []
    decs = []
    for i, (losses, invalid, scored) in enumerate([([0.0, 0.1, 0.2], False, True), ([0.0, 0.4], False, True),
                                                   ([0.0, 0.9, 0.9, 0.9], True, True), ([0.0, 0.3], False, False)]):
        decs.append(dict(id=i, setup="X", cluster=i, block=f"{i}/1", invalid=invalid, scored=scored, n=len(losses),
                         losses=losses, shots=[0] * len(losses), chosen=0, loss=0.0, gap=losses[1], phase="contact",
                         tag=None, p=None, group=None))
    want = A.SCALE * ((0.1 + 0.2) / 3 + 0.4 / 2) / 2
    ref = A.references(LATE_ENTRY, decs, [])["Random (computed)"]
    got = ref["risk"]["main"]["error_rate"]
    if abs(got - want) > 1e-9 or ref["positions"] != 2:
        bad.append(f"references: Random (computed) {got} on {ref['positions']} positions, want {want} on 2")
    late = dict(late=dict(field_league=1, random_same_positions=dict(error_rate=got, positions=2)))
    if B.random_of(late, {1: 121.1}) != got:
        bad.append("random_of: a late row is not scored against Random on its own positions")
    if B.random_of(dict(late=None, lg=dict(id=2)), {1: 121.1, 2: 117.9}) != 117.9:
        bad.append("random_of: a league row is not scored against its league's Random")
    return bad


def preview(state: Path, names: list[str]) -> None:
    conn = sqlite3.connect(f"file:{state / 'snap.db'}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    plays = A.load_plays(state / "plays")
    rows = conn.execute(
        f"""SELECT {A.DECISION_COLUMNS}, ? AS name FROM turns t JOIN games g ON g.id = t.game_id
            JOIN matches m ON m.id = g.match_id JOIN players p ON p.name = ?
            WHERE m.valid = 1 AND m.stage = 'league' AND m.id IN (SELECT match_id FROM league_match_view WHERE league_id = 1)
              AND ((m.player1 = p.id AND t.player = 1) OR (m.player2 = p.id AND t.player = 2))
              AND t.decided_by IN ('model', 'fallback')""", ("Random", "Random")).fetchall()
    league1 = A.quality([A.decision(r, plays) for r in rows], "League 1/Random").get("error_rate")
    print(f"League 1 Random, played: error rate {league1:.2f} ({len(rows)} decisions)")
    print("entrant | decisions | error rate | score today (League 1 Random) | Random on own positions | proposed score")
    for name in names:
        rows = conn.execute(
            f"""SELECT {A.DECISION_COLUMNS}, ? AS name FROM turns t JOIN games g ON g.id = t.game_id
                JOIN matches m ON m.id = g.match_id JOIN players p ON p.name = ?
                WHERE m.valid = 1 AND m.stage = 'late-entry'
                  AND ((m.player1 = p.id AND t.player = 1) OR (m.player2 = p.id AND t.player = 2))
                  AND t.decided_by IN ('model', 'fallback') ORDER BY t.id""", (name, name)).fetchall()
        decs = [A.decision(r, plays) for r in rows]
        er = A.quality(decs, f"{LATE_ENTRY}/{name}").get("error_rate")
        ref = A.references(LATE_ENTRY, decs, [])["Random (computed)"]
        own = ref["risk"]["main"]["error_rate"]
        print(f"{name} | {len(decs)} | {er:.2f} | {B.score(er, league1)} | {own:.2f} on {ref['positions']} | "
              f"{B.score(er, own)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", type=Path)
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()
    bad = synthetic()
    print("synthetic:", "ok" if not bad else "; ".join(bad))
    if args.state and args.names:
        preview(args.state, args.names)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
