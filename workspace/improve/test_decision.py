"""Unit tests for workspace/improve/decision.py (no model call, no network):

    python3 -m unittest workspace/improve/test_decision.py -v
"""

import hashlib
import json
import os
import random
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decision as D  # noqa: E402
import improve as I  # noqa: E402

HOSTED = "decision/jev-1.14.0-notes"
HOSTED_W = "decision/jev-1.14.0-worst"
LOCAL = "decision/decider-v1.2-27b-worst"
ZERO = {"jev": 0, "liquid": 0, "nace": 0, "subq": 0}


def dec(turn_id, game, turn_no, loss, board_key=None, scored=True, invalid=False):
    return dict(turn_id=turn_id, game=game, turn_no=turn_no, loss=loss, board_key=board_key or f"b{turn_id}",
                scored=scored, invalid=invalid, plays=["24/18", "13/7"], chosen=1, best=0, dice=(6, 6),
                position={}, side="white", call="none")


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = {k: getattr(I, k) for k in ("RUNS", "OUT", "SMOKE", "check_inputs")}
        self.saved_d = {k: getattr(D, k) for k in ("ADDENDUM", "ADDENDUM_SHA256", "COHORT_FILE")}
        I.RUNS, I.OUT, I.SMOKE = root / "runs", root / "out", root / "smoke"
        I.check_inputs = lambda: None  # the pinned-binary rule is for real runs; these tests start no process
        self.root = root

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(I, k, v)
        for k, v in self.saved_d.items():
            setattr(D, k, v)
        self.tmp.cleanup()

    def cohort(self, subcaps=None, **decisions):
        c = json.loads(self.saved_d["COHORT_FILE"].read_text())
        for k, v in decisions.items():
            c["decisions"][k]["value"] = v
        if subcaps is not None:
            c["provider_subcaps_usd"] = subcaps
        D.COHORT_FILE = self.root / "cohort.json"
        D.COHORT_FILE.write_text(json.dumps(c))

    def guard(self, slug, none=0, notes=0, worst=0):
        f = D.PREFLIGHT() / "guard.json"
        g = json.loads(f.read_text()) if f.exists() else dict(setups={})
        g["setups"][slug] = dict(refused=dict(none=none, notes=notes, worst=worst))
        I.write_atomic(f, json.dumps(g))


class Selector(unittest.TestCase):
    def test_largest_loss_first_with_the_tie_break(self):
        decs = [dec(1, 1, 5, 0.10), dec(2, 2, 3, 0.30), dec(3, 1, 9, 0.30), dec(4, 1, 9, 0.30), dec(5, 3, 1, 0.05),
                dec(6, 3, 2, 0.20), dec(7, 4, 4, 0.01)]
        chosen, excluded = D.select_worst(decs, set())
        # 0.30 x3: game 1 before game 2; in game 1 turn 9 twice: lower turn id first.
        self.assertEqual([d["turn_id"] for d in chosen], [3, 4, 2, 6, 1])
        self.assertEqual(excluded, [])

    def test_deterministic_over_input_order(self):
        decs = [dec(i, 1 + i % 10, i % 37, round(random.Random(i).random(), 2)) for i in range(200)]
        first = [d["turn_id"] for d in D.select_worst(decs, set())[0]]
        for seed in range(5):
            shuffled = decs[:]
            random.Random(seed).shuffle(shuffled)
            self.assertEqual([d["turn_id"] for d in D.select_worst(shuffled, set())[0]], first)

    def test_test_positions_are_removed_before_selection(self):
        decs = [dec(1, 1, 1, 0.90, board_key="TEST"), dec(2, 1, 2, 0.50), dec(3, 2, 1, 0.40)]
        chosen, excluded = D.select_worst(decs, {"TEST"}, n=1)
        self.assertEqual([d["turn_id"] for d in chosen], [2])  # not dropped after selection: the next one fills
        self.assertEqual([d["turn_id"] for d in excluded], [1])

    def test_best_plays_invalid_and_unscored_are_not_eligible(self):
        decs = [dec(1, 1, 1, 0.0004), dec(2, 1, 2, 0.0005), dec(3, 1, 3, 0.9, invalid=True),
                dec(4, 1, 4, 0.9, scored=False)]
        chosen, _ = D.select_worst(decs, set())
        self.assertEqual([d["turn_id"] for d in chosen], [2])  # 0.0005 prints as 0.001 (eligible), 0.0004 as 0.000
        self.assertEqual(D.select_worst([dec(1, 1, 1, 0.0)], set())[0], [])

    def test_block_format_and_empty(self):
        self.assertEqual(D.worst_block([], []), "")
        block = D.worst_block([dec(9, 3, 17, 0.3521)], ["Position (your numbering; you move 24 -> 1):\n  x\nDice: 6-6"])
        self.assertEqual(block.splitlines()[:4], [D.WORST_OPEN, D.WORST_INTRO, "", "Example 1 (game 3, turn 17):"])
        self.assertIn("You played: 13/7. GNUbg's best play: 24/18. Equity lost: 0.352.", block)
        self.assertTrue(block.endswith(D.WORST_CLOSE))

    def test_position_block_is_the_league_states_last(self):
        league = "Rules...\n\nPosition (your numbering; you move 24 -> 1):\n  your checkers: 6:5\nRace: x\nDice: 3-1\n\nWhich?"
        state = "=== WORST ===\nExample 1:\nPosition (your numbering; you move 24 -> 1):\n  old\nDice: 6-6\n\n" + league
        self.assertEqual(D.position_block(state),
                         "Position (your numbering; you move 24 -> 1):\n  your checkers: 6:5\nRace: x\nDice: 3-1")


class Writer(Isolated):
    def test_the_writer_never_reads_a_test_position(self):
        key = "decision/decider-v1.2-27b-notes"
        os.environ.update(MATCH_ID="1", GAME_ROUND="1", GAME_LEG="1")
        seen = {}
        saved = {k: getattr(I, k) for k in ("score_match", "test_board_keys", "game_decisions", "game_results",
                                             "board_text")}
        saved_w = D.write_notes
        try:
            I.score_match = lambda *a: None
            I.test_board_keys = lambda: {"TEST"}
            I.game_decisions = lambda *a: [dec(1, 1, 3, 0.2, board_key="TEST"), dec(2, 1, 5, 0.1)]
            I.game_results = lambda *a: {1: dict(won=True, result="single", points=1)}
            I.board_text = lambda position, side: "BOARD"
            def fake(key_, step, g, record):
                seen["record"] = record
                I.write_atomic(I.step_dir(key_, step) / f"notes-g{g:02d}.txt", "- a note\n")
                return "- a note", {}
            D.write_notes = fake
            D.after_game(key, 1)
        finally:
            for k, v in saved.items():
                setattr(I, k, v)
            D.write_notes = saved_w
        self.assertIn("Turn 5", seen["record"])
        self.assertNotIn("Turn 3", seen["record"])
        ev = [e for e in I.events(key) if e["event"] == "test_positions_excluded"]
        self.assertEqual(ev[0]["n"], 1)
        note = (I.step_dir(key, "S1") / "note.txt").read_text()
        self.assertEqual(note.splitlines()[:2], [I.OPEN, D.NOTES_INTRO])

    def test_the_pilot_prompt_is_unchanged(self):
        self.assertEqual(I.lesson_prompt_sha256(), I.LESSON_PROMPT_SHA256)

    def test_the_largest_notes_block_is_within_the_cut_rule(self):
        block = D.synthetic_notes_block()
        for game in block.split("After game ")[1:]:
            lessons = "\n".join(x for x in game.splitlines() if x.startswith("- "))
            kept, cut = I.limit_lessons(lessons)
            self.assertFalse(cut["cut"])
            self.assertEqual(kept, lessons)


def ledger(path, *rows):
    """A runner-schema ledger with (setup, status, reserved, cost) rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE attempts (id INTEGER PRIMARY KEY, setup TEXT, status TEXT, reserved_usd REAL, "
               "cost_usd REAL, reported_cost_usd REAL)")
    db.executemany("INSERT INTO attempts (setup, status, reserved_usd, cost_usd) VALUES (?, ?, ?, ?)", rows)
    db.commit()
    db.close()
    return path


class FakeAsk:
    """Stands in for `jevgammon ask` (no process, no network): records each call; `ok` writes one fresh answer with
    the given input tokens into the attempt's --out database; a failing call returns `code` and writes nothing."""

    def __init__(self, tokens=(100, 200), code=0, model="subq-snap-1.1"):
        self.tokens, self.code, self.model, self.calls = list(tokens), code, model, []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        a = dict(zip(argv[2::2], argv[3::2]))
        if self.code == 0:
            db = sqlite3.connect(a["--out"])
            db.execute("CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY, setup TEXT, error TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS answer_exchanges (id INTEGER PRIMARY KEY, answer_id INTEGER, "
                       "response TEXT)")
            cur = db.execute("INSERT INTO answers (setup, error) VALUES (?, NULL)", (a["--setup"],))
            db.execute("INSERT INTO answer_exchanges (answer_id, response) VALUES (?, ?)", (cur.lastrowid, json.dumps(
                {"model": self.model, "usage": {"input_tokens": self.tokens.pop(0)}})))
            db.commit()
            db.close()
        return type("R", (), dict(returncode=self.code, stdout="", stderr="" if self.code == 0 else "refused"))()


class Binding(Isolated):
    def test_an_arm_is_bound_to_the_published_addendum(self):
        D.ADDENDUM = self.root / "addendum.md"
        D.ADDENDUM.write_text("addendum v1\n")
        D.ADDENDUM_SHA256 = hashlib.sha256(b"addendum v1\n").hexdigest()
        D.check_addendum()
        self.assertEqual(D.bind_run(HOSTED)["addendum_sha256"], D.ADDENDUM_SHA256)
        D.ADDENDUM.write_text("addendum v2\n")
        with self.assertRaises(SystemExit):
            D.check_addendum()
        with self.assertRaises(SystemExit):
            D.bind_run(HOSTED)  # resume refused: bound to v1
        D.ADDENDUM_SHA256 = hashlib.sha256(b"addendum v2\n").hexdigest()
        with self.assertRaises(SystemExit):
            D.bind_run(HOSTED)  # even when the constant moves: the arm keeps its first binding

    def test_an_unpublished_addendum_binds_nothing(self):
        D.ADDENDUM = self.root / "addendum.md"
        D.ADDENDUM.write_text("draft\n")
        D.ADDENDUM_SHA256 = "0" * 64
        with self.assertRaises(SystemExit):
            D.bind_run(HOSTED)
        self.assertFalse((I.mdir(HOSTED) / "run.json").exists())

    def test_a_changed_cohort_refuses_the_resume_and_money_needs_an_amendment(self):
        self.cohort()
        bound = D.bind_run(HOSTED)
        c = json.loads(D.COHORT_FILE.read_text())
        jev = next(s for s in c["setups"] if s["slug"] == "jev-1.14.0")
        jev["estimate"]["notes"] = 0.99  # a run-defining setting
        D.COHORT_FILE.write_text(json.dumps(c))
        with self.assertRaises(SystemExit) as e:
            D.bind_run(HOSTED)
        self.assertIn("run-defining", str(e.exception))
        jev["estimate"]["notes"] = 0.56
        c["decision_lane_cap_usd"] = 4.0  # a money term without an amendment record
        D.COHORT_FILE.write_text(json.dumps(c))
        with self.assertRaises(SystemExit) as e:
            D.bind_run(HOSTED)
        self.assertIn("amendment", str(e.exception))
        c["amendments"] = [dict(path="decision_lane_cap_usd", **{"from": 3.0, "to": 4.0}, source="Ümit #test")]
        D.COHORT_FILE.write_text(json.dumps(c))
        self.assertEqual(D.bind_run(HOSTED)["identity_sha256"], bound["identity_sha256"])
        # The export shows the bound settings, not today's file.
        row = D.arm_summary("jev-1.14.0", "notes")
        self.assertEqual(row["bound_money"]["decision_lane_cap_usd"], 3.0)


class Money(Isolated):
    def test_a_zero_allowance_refuses_every_billed_hosted_step(self):
        self.cohort(D6_hosted_allowance_usd=ZERO)
        for key in (HOSTED, HOSTED_W):
            for step in ("E1", "S1"):
                with self.assertRaises(D.Refused) as e:
                    D.money_gate(key, step, balance_reader=lambda: dict(balance=100.0))
                self.assertTrue(e.exception.pause and "D6" in str(e.exception))

    def test_a_zero_allowance_keeps_the_arm_pending_and_calls_nothing(self):
        self.cohort(D6_hosted_allowance_usd=ZERO)
        self.guard("jev-1.14.0")
        D.register()
        self.assertEqual(D.arm_state("jev-1.14.0", "notes", dry=False)[0], "pending")
        self.assertIn("D6", D.arm_state("jev-1.14.0", "notes", dry=False)[1])
        self.assertEqual(D.run(HOSTED), I.PAUSE)
        self.assertFalse(I.mdir(HOSTED).exists())  # nothing started, nothing bound

    def test_an_exhausted_nace_subcap_refuses_even_a_mocked_probe(self):
        league = ledger(self.root / "nace-league.db", ("Drex Max 1.1", "settled", 1.0, 2.50))
        c = json.loads(self.saved_d["COHORT_FILE"].read_text())
        c["provider_ledgers"] = {"nace": [str(league)]}
        D.COHORT_FILE = self.root / "cohort.json"
        D.COHORT_FILE.write_text(json.dumps(c))
        fake = FakeAsk(model="drex-max-v1.1")
        with self.assertRaises(D.Refused) as e:
            D.probe_p1("drex-max-1.1", send=True, run=fake)
        self.assertIn("provider subcap", str(e.exception))
        self.assertEqual(fake.calls, [])
        with self.assertRaises(D.Refused):
            D.money_gate("decision/drex-max-1.1-worst", "E1")

    def test_p1_needs_fresh_successful_answers_and_never_reuses_an_earlier_attempt(self):
        self.cohort()
        good = D.probe_p1("subq-snap-1.1", send=True, run=FakeAsk(tokens=(100, 900)))
        self.assertTrue(good["passed"])
        failed = D.probe_p1("subq-snap-1.1", send=True, run=FakeAsk(code=1))
        self.assertFalse(failed["passed"])  # the earlier attempt's answers are in another database: not read
        self.assertEqual(failed["failures"]["plain"], "runner exit 1")
        self.assertFalse(D.evidence_record("p1", "subq-snap-1.1")["passed"])
        wrong = D.probe_p1("subq-snap-1.1", send=True, run=FakeAsk(model="subq-snap-preview"))
        self.assertFalse(wrong["passed"])
        flat = D.probe_p1("subq-snap-1.1", send=True, run=FakeAsk(tokens=(100, 100)))
        self.assertFalse(flat["passed"])
        # Each probe held, then released, an allocation in the one admission ledger.
        db = sqlite3.connect(I.RUNS / "decision" / "admission.db")
        self.assertEqual(db.execute("SELECT COUNT(*), SUM(status = 'closed') FROM allocations").fetchone(), (4, 4))
        db.close()

    def test_unreadable_accounting_refuses(self):
        self.cohort()
        bad = I.RUNS / "decision" / "subq-snap-1.1-worst" / "ledgers" / "E1-a1.db"
        bad.parent.mkdir(parents=True)
        bad.write_bytes(b"not a database" * 100)
        with self.assertRaises(D.AccountingError):
            D.booked_rows(bad)
        with self.assertRaises(D.AccountingError):
            D.money_gate(HOSTED_W, "E1")
        bad.unlink()
        ledger(bad, ("x", "settled", 1.0, None))  # a settled row without a cost
        with self.assertRaises(D.AccountingError):
            D.money_gate(HOSTED_W, "E1")
        self.assertEqual(D.booked_rows(self.root / "absent.db"), 0.0)  # a ledger never created holds nothing

    def test_concurrent_admissions_cannot_jointly_pass_the_lane_cap(self):
        import threading
        self.cohort()
        keys = [arm_key for arm_key in D.arm_keys() if D.I.entry(arm_key)["hosted"]] * 3
        granted, refused = [], []

        def one(k):
            try:
                granted.append(D.admit(k, "E1", D.next_ledger(k, f"E1-{threading.get_ident()}"), 0.05)["cap"])
            except D.Refused:
                refused.append(k)
        threads = [threading.Thread(target=one, args=(k,)) for k in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertLessEqual(sum(granted), 3.00 + 1e-9)
        self.assertTrue(refused)
        self.assertEqual(len(granted) + len(refused), len(keys))

    def test_every_decision_ledger_counts_in_the_110_and_a_chat_share_must_leave_room(self):
        self.cohort()
        ledger(I.RUNS / "decision" / "subq-snap-1.1-worst" / "ledgers" / "E1-a1.db",
               ("SubQ | E1", "settled", 1.0, 0.10), ("SubQ | s01" + D.WRITER_SUFFIX, "open", 0.05, None))
        self.assertAlmostEqual(I.billed_total(), 0.15)
        self.assertAlmostEqual(D.provider_spent("subq"), 0.15)
        I.write_atomic(I.RUNS / "share_cap.json", json.dumps(dict(usd=107.5)))
        with self.assertRaises(D.Refused):
            D.money_gate(HOSTED_W.replace("jev-1.14.0", "subq-snap-1.1"), "E1")

    def test_writer_steps_check_the_openrouter_balance(self):
        self.cohort()
        with self.assertRaises(D.Refused) as e:
            D.money_gate("decision/decider-v1.2-27b-notes", "S1", balance_reader=lambda: dict(balance=5.001))
        self.assertTrue(e.exception.pause)
        gate = D.money_gate("decision/decider-v1.2-27b-notes", "S1", balance_reader=lambda: dict(balance=50.0))
        self.assertEqual(gate["binding"], "rule (a) limit")  # 1.5 x $0.03
        self.assertFalse(D.needs_ledger(LOCAL, "S1"))  # a local worst arm bills nothing


class Configs(Isolated):
    def test_the_player_carries_gate_route_check_and_this_experiments_ledger(self):
        ledger = dict(path=self.root / "l.db", cap=0.123456789)
        p = D.player_config(HOSTED, "Jev 1.14.0 · helper-written notes | improve | s01 | a1", 4,
                            note_file=self.root / "note.txt", ledger=ledger)
        self.assertEqual(p["spec"], "jev/jev-1.14.0")
        self.assertEqual(p["parallel"], 2)  # never above the league's
        self.assertEqual(p["context_gate"], {"kind": "client", "limit_tokens": 32000})
        self.assertEqual(p["expect_route"]["models"], ["jev-1.14.0"])
        self.assertEqual(p["budget"]["ledger"], str(self.root / "l.db"))
        self.assertEqual(p["budget"]["cap_usd"], 0.123457)
        self.assertEqual(p["prompt_note_file"], str(self.root / "note.txt"))

    def test_the_writer_is_the_live_plans_lesson_call(self):
        ledger = dict(path=self.root / "l.db", cap=1.0)
        w = D.writer_config(HOSTED, "Jev | s01", ledger)
        live = I.player_config(D.WRITER_KEY, "Jev | s01" + D.WRITER_SUFFIX, 1, ledger=ledger)
        self.assertEqual({k: v for k, v in w.items() if k != "expect_route"},
                         {k: v for k, v in live.items() if k != "expect_route"})
        self.assertEqual(w["spec"], "openai-compatible/qwen/qwen3.8-flash")
        self.assertEqual(w["request"]["provider"], {"order": ["alibaba"], "allow_fallbacks": False,
                                                    "require_parameters": True})
        self.assertEqual(w["expect_route"]["provider"], "Alibaba")
        self.assertTrue(w["expect_route"]["reject_log"].endswith("writer-rejections.jsonl"))


class States(Isolated):
    def test_guard_refusals_make_arms_not_tested(self):
        self.cohort()
        self.assertEqual(D.arm_state("jev-1.14.0", "notes", dry=True)[0], "pending")  # no preflight yet
        self.guard("jev-1.14.0", notes=1)
        self.assertEqual(D.arm_state("jev-1.14.0", "notes", dry=True), ("not tested", "conservative context guard"))
        self.assertEqual(D.arm_state("jev-1.14.0", "worst", dry=True), ("eligible", None))
        self.guard("jev-1.14.0", none=1)
        self.assertEqual(D.arm_state("jev-1.14.0", "worst", dry=True)[0], "not tested")

    def test_rows_without_an_arm_stay_visible_with_their_reason(self):
        self.cohort()
        self.assertEqual(D.arm_state("d3-ultra", "worst")[0], "not started")
        self.assertEqual(D.arm_state("reax-1.3", "worst")[0], "pending")  # D5
        self.assertEqual(D.arm_state("baselabs-elephant-1", "notes")[0], "pending")  # D5: notes arm only
        self.assertNotIn("D5", D.arm_state("baselabs-elephant-1", "worst")[1])
        self.cohort(D5_edge_settings="not_tested")
        self.assertEqual(D.arm_state("reax-1.3", "worst"), ("not tested", "edge settings (D5)"))

    def test_liquid_runs_flagged_and_its_guard_fails_closed_without_a_documented_limit(self):
        self.cohort()
        out = D.guard_preflight(write=False, worst=D.worst_block([dec(1, 1, 1, 0.5)], ["Position\nDice: 1-1"]))
        row = out["setups"]["liquid-d1-ultra"]
        self.assertEqual(row["refused"]["none"], row["requests"])  # every request refused: fails closed
        rows = [r for r in D.summary()["rows"] if r["setup"] == "Liquid d1-ultra"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("delivery unverified (our evidence gap)" in r["delivery_flag"] for r in rows))
        self.assertTrue(all((r["state"], r["reason"]) == ("not tested", "native context limit unverified")
                            for r in rows))

    def test_a_spent_subcap_keeps_drex_max_pending(self):
        self.cohort(subcaps={"nace": 1.25}, D6_hosted_allowance_usd=dict(ZERO, nace=110))
        self.guard("drex-max-1.1")
        state, why = D.arm_state("drex-max-1.1", "notes", dry=False)
        self.assertEqual(state, "pending")
        self.assertIn("subcap", why)

    def test_an_incomplete_marker_from_the_runner_stops_the_arm(self):
        self.assertIsInstance(I.context_stop("Error: CONTEXT GATE: Jev request refused"), I.Incomplete)
        self.assertIn("conservative context guard", str(I.context_stop("CONTEXT GATE: x")))
        self.assertIsInstance(I.context_stop("CONTEXT REFUSAL: the service refused"), I.Incomplete)
        self.assertIsNone(I.context_stop("STOPPED: an earlier request failed a pre-send or reply check"))


if __name__ == "__main__":
    unittest.main()
