"""Classifier tests: phase rules and game-plan tags on textbook positions, and GNUbg's class numbers.

Concept positions come from transformer-backgammon's board.py
(https://github.com/wmhowell18/claude-code/blob/8bcf45d468afc36a3a48b324b1fce89ead7a96cb/transformer-backgammon/src/backgammon/core/board.py).
Its holding_game_position and back_game_position put both colours on the same points, so they are
not legal boards; the holding, back-game, low-anchor and priming positions below are our own,
built to the textbook definitions (The Gammon Press, lesson 9, for holding games and low anchors).

Runs inside gnubg's embedded Python from the repo root (it needs gnubg.classifypos):

    gnubg -t -q -p tools/v3/test_classify.py

Set GNUBG_EVAL_H to gnubg 1.08's eval.h to also compare the pinned enum with the source file
(gnubg-release-1.08.003-sources.tar.gz, sha256 6f7d969b13cfff786fba90ff8cc5e5d564b97f4f0aa69afe4f3838f18c445979,
eval.h lines 310-322). Exits with status 1 on any failure.
"""

import os
import re
import sys
import traceback

sys.path.insert(0, os.path.join(os.getcwd(), "tools", "v3"))  # gnubg runs scripts without __file__

import gnubg  # noqa: E402

import classify  # noqa: E402
import engine  # noqa: E402
from rules import CHECKERS, flip, start  # noqa: E402

# gnubg 1.08.003, eval.h lines 310-322, verbatim.
EVAL_H_ENUM = """typedef enum {
    CLASS_OVER = 0,             /* Game already finished */
    CLASS_HYPERGAMMON1,         /* hypergammon with 1 chequers */
    CLASS_HYPERGAMMON2,         /* hypergammon with 2 chequers */
    CLASS_HYPERGAMMON3,         /* hypergammon with 3 chequers */
    CLASS_BEAROFF2,             /* Two-sided bearoff database (in memory) */
    CLASS_BEAROFF_TS,           /* Two-sided bearoff database (on disk) */
    CLASS_BEAROFF1,             /* One-sided bearoff database (in memory) */
    CLASS_BEAROFF_OS,           /* One-sided bearoff database /on disk) */
    CLASS_RACE,                 /* Race neural network */
    CLASS_CRASHED,              /* Contact, one side has less than 7 active checkers */
    CLASS_CONTACT               /* Contact neural network */
} positionclass;"""


def source_classes():
    names = re.findall(r"^\s+(CLASS_\w+)", EVAL_H_ENUM, re.M)
    return {name: i for i, name in enumerate(names)}


def make(mine, theirs, bar=(0, 0)):
    """A position from the mover's side: `mine` and `theirs` map each side's own point numbers
    to checker counts; checkers not on the board or the bar are borne off."""
    pts = [0] * 24
    for p, n in mine.items():
        pts[p - 1] += n
    for p, n in theirs.items():
        assert pts[24 - p] == 0, f"point {25 - p} holds both colours"
        pts[24 - p] -= n
    off = [CHECKERS - sum(mine.values()) - bar[0], CHECKERS - sum(theirs.values()) - bar[1]]
    assert min(off) >= 0
    return pts, list(bar), off


def from_transformer(white, black):
    """transformer-backgammon's Board (white_checkers / black_checkers indexed 0 = bar, 1..24 =
    points in white's numbering, 25 = off; white to move) as a position with white the mover."""
    pts = [0] * 24
    for p, n in white.items():
        if 1 <= p <= 24:
            pts[p - 1] += n
    for p, n in black.items():
        if 1 <= p <= 24:
            if pts[p - 1] != 0:
                return None  # both colours on one point: not a legal board
            pts[p - 1] -= n
    bar = [white.get(0, 0), black.get(0, 0)]
    off = [CHECKERS - sum(n for p, n in white.items() if p <= 24), CHECKERS - sum(n for p, n in black.items() if p <= 24)]
    if min(off) < 0:
        return None
    return pts, bar, off


def label(pos, turn=20, variant="standard"):
    cls = engine.classify(pos, variant)
    ph = classify.phase(pos, cls, turn)
    return ph, classify.tag(pos, ph)


# --- transformer-backgammon concept positions (board.py at 8bcf45d4), verbatim -----------------

TB = {
    "initial_board": ({24: 2, 13: 5, 8: 3, 6: 5}, {1: 2, 12: 5, 17: 3, 19: 5}),
    "nackgammon_start": ({24: 2, 23: 2, 13: 4, 8: 3, 6: 4}, {1: 2, 2: 2, 12: 4, 17: 3, 19: 4}),
    "bearoff_practice": ({6: 3, 5: 3, 4: 3, 3: 3, 2: 2, 1: 1}, {19: 3, 20: 3, 21: 3, 22: 3, 23: 2, 24: 1}),
    "race_position": ({12: 2, 10: 3, 8: 3, 6: 4, 3: 3}, {13: 2, 15: 3, 17: 3, 19: 4, 22: 3}),
    "running_game_position": ({10: 2, 9: 2, 8: 3, 6: 3, 5: 2, 4: 2, 3: 1},
                              {14: 2, 13: 2, 12: 3, 19: 3, 20: 2, 21: 2, 22: 1}),
    "prime_building_position": ({7: 2, 6: 2, 5: 2, 4: 2, 24: 2, 23: 1, 13: 2, 8: 2},
                                {18: 2, 19: 2, 20: 2, 21: 2, 1: 2, 2: 1, 12: 2, 17: 2}),
    "blitz_position": ({6: 2, 5: 2, 4: 2, 3: 2, 2: 2, 13: 3, 8: 2}, {0: 2, 12: 4, 17: 3, 20: 3, 22: 2, 23: 1}),
    "holding_game_position": ({20: 2, 13: 3, 11: 2, 9: 2, 8: 2, 7: 2, 6: 2},
                              {8: 1, 7: 2, 6: 3, 5: 3, 4: 2, 3: 2, 2: 2}),
    "back_game_position": ({23: 2, 20: 2, 13: 3, 12: 2, 11: 2, 10: 2, 9: 2},
                           {10: 2, 9: 1, 6: 3, 5: 3, 4: 2, 3: 2, 2: 2}),
}


def test_gnubg_class_numbers_match_source():
    src = source_classes()
    assert src["CLASS_OVER"] == engine.CLASS_OVER == 0
    assert src["CLASS_BEAROFF2"] == engine.CLASS_BEAROFF2 == 4
    assert src["CLASS_BEAROFF_TS"] == engine.CLASS_BEAROFF_TS == 5
    assert src["CLASS_BEAROFF1"] == engine.CLASS_BEAROFF1 == 6
    assert src["CLASS_BEAROFF_OS"] == engine.CLASS_BEAROFF_OS == 7
    assert src["CLASS_RACE"] == engine.CLASS_RACE == classify.RACE_CLASS == 8
    assert src["CLASS_CRASHED"] == engine.CLASS_CRASHED == 9
    assert src["CLASS_CONTACT"] == engine.CLASS_CONTACT == 10
    assert classify.CONTACT_CLASSES == (src["CLASS_CRASHED"], src["CLASS_CONTACT"])
    assert set(classify.BEAROFF_CLASSES) == {v for k, v in src.items() if "BEAROFF" in k}
    path = os.environ.get("GNUBG_EVAL_H")
    if path:
        assert EVAL_H_ENUM in open(path).read(), "eval.h differs from the pinned enum"


def test_gnubg_classes_on_positions():
    assert engine.classify(start()) == engine.CLASS_CONTACT
    assert engine.classify(start("nackgammon"), "nackgammon") == engine.CLASS_CONTACT
    # One side down to 6 checkers in play while in contact: crashed.
    crashed = make({24: 2, 6: 2, 5: 2}, {13: 5, 8: 3, 6: 5, 2: 2})
    assert engine.classify(crashed) == engine.CLASS_CRASHED
    race = make({12: 2, 10: 3, 8: 3, 6: 4, 3: 3}, {12: 2, 10: 3, 8: 3, 6: 4, 3: 3})
    assert engine.classify(race) == engine.CLASS_RACE
    # Both sides in their home boards: GNUbg's bear-off databases (1.08 ships the in-memory ones).
    assert engine.classify(make({6: 3, 5: 3, 4: 3, 3: 3, 2: 2, 1: 1}, {6: 3, 5: 3, 4: 3, 3: 3, 2: 2, 1: 1})) \
        == engine.CLASS_BEAROFF1
    assert engine.classify(make({2: 1, 1: 1}, {3: 1, 1: 1})) == engine.CLASS_BEAROFF2


def test_transformer_concept_positions():
    expected = {
        "initial_board": (1, "standard", ("opening", None)),
        "nackgammon_start": (1, "nackgammon", ("opening", None)),
        "bearoff_practice": (40, "standard", ("bear-off", None)),
        "race_position": (30, "standard", ("race", None)),
        "running_game_position": (30, "standard", ("race", None)),
        "blitz_position": (12, "standard", ("contact", "blitz")),
        "prime_building_position": (20, "standard", ("contact", "priming")),
    }
    for name, (turn, variant, want) in expected.items():
        pos = from_transformer(*TB[name])
        assert pos is not None, name
        got = label(pos, turn, variant)
        assert got == want, f"{name}: {got}, textbook {want}"
    # These two put both colours on the same points (white and black on 6, 7, 8; on 9, 10), so
    # they are not legal boards; the textbook holding and back games below replace them.
    assert from_transformer(*TB["holding_game_position"]) is None
    assert from_transformer(*TB["back_game_position"]) is None


def test_opening():
    for d in range(1, 7):
        assert label(start(), turn=d) == ("opening", None)
    # The opening rule is by turn only: the same board at turn 7 is a contact position. Its only
    # anchors are the 24-points and neither side has a 4-prime, so it is tagged low-anchor.
    assert label(start(), turn=7) == ("contact", "low-anchor")


def test_holding_games():
    # Anchor on the opponent's 5-point (the mover's 20), opponent escaped: the classic holding game.
    five = make({20: 2, 13: 3, 8: 3, 6: 4, 5: 2, 4: 1}, {13: 4, 8: 3, 7: 2, 6: 4, 4: 2})
    assert label(five) == ("holding", "holding")
    # Bar-point (18) and 4-point (21) anchors.
    bar = make({18: 2, 13: 3, 8: 3, 6: 4, 5: 3}, {13: 4, 9: 3, 6: 4, 5: 2, 4: 2})
    assert label(bar) == ("holding", "holding")
    four = make({21: 3, 13: 2, 8: 4, 6: 4, 5: 2}, {13: 3, 9: 2, 8: 2, 6: 4, 5: 2, 3: 2})
    assert label(four) == ("holding", "holding")
    # The same with the opponent holding: the rule looks at both sides.
    assert label(flip(five)) == ("holding", "holding")
    # Race deficit: holder's pips minus the escaped side's.
    mine = 20 * 2 + 13 * 3 + 8 * 3 + 6 * 4 + 5 * 2 + 4
    theirs = 13 * 4 + 8 * 3 + 7 * 2 + 6 * 4 + 4 * 2
    assert classify.race_deficit(five) == mine - theirs
    assert classify.race_deficit(flip(five)) == mine - theirs


def test_not_holding():
    # A stray checker behind the anchor.
    stray = make({20: 2, 24: 1, 13: 3, 8: 3, 6: 4, 5: 2}, {13: 4, 8: 3, 7: 2, 6: 4, 4: 2})
    assert label(stray)[0] == "contact"
    # Anchor on the opponent's 3-point (22): a low anchor, not a holding game.
    low = make({22: 2, 13: 3, 8: 3, 6: 4, 5: 2, 4: 1}, {13: 4, 8: 3, 7: 2, 6: 4, 4: 2})
    assert label(low) == ("contact", "low-anchor")
    # The opponent still has a checker on its 14-point: not escaped.
    behind = make({20: 2, 13: 3, 8: 3, 6: 4, 5: 2, 4: 1}, {14: 1, 13: 3, 8: 3, 7: 2, 6: 4, 4: 2})
    assert label(behind)[0] == "contact"
    # A checker on the bar besides the anchor.
    entering = make({20: 2, 13: 3, 8: 3, 6: 4, 5: 2}, {13: 4, 8: 3, 7: 2, 6: 4, 4: 2}, bar=(1, 0))
    assert label(entering)[0] == "contact"


def test_blitz():
    # Two opponent checkers on the bar against a 4-point board, the mover attacking.
    pos = make({6: 3, 5: 2, 4: 2, 2: 2, 8: 2, 13: 3, 9: 1}, {24: 1, 13: 5, 8: 3, 6: 4}, bar=(0, 2))
    assert label(pos) == ("contact", "blitz")
    # On the bar against only 2 made points: no blitz.
    pos = make({6: 4, 5: 2, 4: 1, 3: 1, 8: 3, 13: 4}, {24: 1, 13: 5, 8: 3, 6: 4}, bar=(0, 2))
    assert label(pos)[1] != "blitz"


def test_back_game():
    # Anchors on the opponent's 2- and 4-points (the mover's 23 and 21).
    pos = make({23: 2, 21: 2, 13: 2, 11: 2, 9: 2, 8: 2, 6: 3}, {6: 4, 5: 4, 3: 3, 1: 2, 8: 2})
    assert label(pos) == ("contact", "back game")
    # A back game outranks a holding-looking structure and a prime.
    pos = make({24: 2, 20: 2, 9: 2, 8: 2, 7: 2, 6: 3, 5: 2}, {13: 5, 8: 3, 6: 3, 4: 2, 2: 2})
    assert label(pos) == ("contact", "back game")


def test_low_anchor():
    # Ace-point anchor (the mover's 24) only, and no 4-prime on either side.
    pos = make({24: 2, 13: 4, 8: 3, 6: 4, 5: 2}, {13: 5, 8: 3, 6: 4, 3: 2, 24: 1})
    assert label(pos) == ("contact", "low-anchor")
    # The same anchor against a 4-prime: priming outranks low-anchor (the agreed deviation from
    # the design's proposed order).
    pos = make({24: 2, 13: 4, 8: 3, 6: 4, 5: 2}, {13: 3, 8: 2, 7: 2, 6: 3, 5: 2, 3: 2, 24: 1})
    assert label(pos) == ("contact", "priming")


def test_priming():
    # A full prime from 4 to 9 with an opponent checker trapped on the mover's 2-point.
    pos = make({9: 2, 8: 2, 7: 2, 6: 3, 5: 2, 4: 2, 13: 2}, {23: 1, 13: 4, 8: 3, 6: 4, 5: 3})
    assert label(pos) == ("contact", "priming")
    # Four in a row is enough.
    pos = make({8: 2, 7: 2, 6: 3, 5: 2, 13: 4, 3: 2}, {24: 1, 23: 1, 13: 4, 8: 3, 6: 4, 5: 2})
    assert label(pos) == ("contact", "priming")


def test_other():
    pos = make({24: 1, 22: 1, 13: 4, 9: 1, 8: 3, 6: 4, 3: 1}, {24: 1, 21: 1, 13: 4, 8: 3, 6: 4, 4: 2})
    assert label(pos) == ("contact", "other")


def run():
    failed = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}", flush=True)
        except Exception:
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}", flush=True)
    print(f"{len(tests) - failed} passed, {failed} failed", flush=True)
    os._exit(1 if failed else 0)


run()
