"""Ladder rules of 2026-10-26 (tools/ladder.py): moves without a lock, the pairs a round creates, and
the end check with its final swap.

    python3 tools/test_ladder.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ladder  # noqa: E402

PEOPLE = {n: dict(spec="gnubg-weak" if n == "GNU" else "model") for n in
          ("A", "B", "C", "D", "E", "F", "G", "H", "GNU")}


def league(*names):
    return dict(names=list(names), table=[dict(name=n) for n in names])


def current():
    # Tables in rank order: League 1 A, B, GNU; League 2 GNU, C, D, E; League 3 F, G, H.
    return {1: league("GNU", "A", "B"), 2: league("C", "D", "E", "GNU"), 3: league("F", "G", "H")}


def test_moves_skip_programs_and_have_no_lock():
    moves, notes, swaps = ladder.round_moves(current(), PEOPLE, 7)
    assert [(m["setup"], m["source"], m["target"], m["reason"]) for m in moves] == [
        ("A", 1, 2, "promoted"), ("E", 2, 1, "relegated"),
        ("C", 2, 3, "promoted"), ("H", 3, 2, "relegated")]
    assert len(swaps) == 2 and len(notes) == 2  # GNU skipped at the top of League 1 and the bottom of League 2


def test_pairs_and_end_check():
    cur = current()
    moves, _, _ = ladder.round_moves(cur, PEOPLE, 7)
    after = ladder.lineups_after({lid: cur[lid]["names"] for lid in ladder.LADDER}, moves)
    assert sorted(after[2]) == ["A", "D", "GNU", "H"]
    pairs = {frozenset((p["a"], p["b"])) for p in ladder.mover_pairs(moves, after)}
    # A meets D, GNU and H (the two newcomers of League 2 play each other once); E, C and H meet theirs.
    assert pairs == {frozenset(p) for p in [("A", "D"), ("A", "GNU"), ("A", "H"), ("E", "GNU"), ("E", "B"),
                                            ("C", "F"), ("C", "G"), ("H", "D"), ("H", "GNU")]}


def test_final_swap():
    moves = [dict(round=9, setup="A", source=1, target=2, reason="promoted"),
             dict(round=9, setup="E", source=2, target=1, reason="relegated")]
    pairs = [dict(league=2, a="A", b="D"), dict(league=1, a="E", b="B")]
    ended, out = ladder.end_check(moves, pairs, {frozenset(("A", "D")): {}})
    assert not ended and out == moves  # E v B is not stored: the ladder goes on
    ended, out = ladder.end_check(moves, pairs, {frozenset(("A", "D")): {}, frozenset(("E", "B")): {}})
    assert ended
    assert [(m["setup"], m["source"], m["target"], m["reason"]) for m in out] == [
        ("A", 1, 2, "final swap (ladder ended)"), ("E", 2, 1, "final swap (ladder ended)")]


def test_move_note_reasons():
    for reason in ("promoted", "relegated", "final swap (ladder ended)"):
        m = ladder.MOVE_NOTE.search(f"ladder round 5: {reason} to league 2")
        assert m and m.group(2) == reason
    assert not ladder.MOVE_NOTE.search("ladder round 5: frozen boundary to league 2")
    assert not ladder.MOVE_NOTE.search("ladder round 5: final placement to league 2")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
