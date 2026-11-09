"""Unit tests for workspace/improve/improve.py (no model call, no runner, no network):

    python3 -m unittest workspace/improve/test_improve.py -v
"""

import hashlib
import json
import os
import time
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import improve as I  # noqa: E402

KEY = "qwen3.8-flash-off"  # estimate $2.30, S $0.35, E $0.18


def make_ledger(path: Path, settled=0.0, lost=0.0, open_=0.0, reported=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, status TEXT, reserved_usd REAL, "
               "cost_usd REAL, reported_cost_usd REAL)")
    if settled:
        db.execute("INSERT INTO attempts (status, reserved_usd, cost_usd, reported_cost_usd) VALUES "
                   "('settled', 1.0, ?, ?)", (settled, reported))
    if lost:
        db.execute("INSERT INTO attempts (status, reserved_usd) VALUES ('lost', ?)", (lost,))
    if open_:
        db.execute("INSERT INTO attempts (status, reserved_usd) VALUES ('open', ?)", (open_,))
    db.commit()
    db.close()


class Isolated(unittest.TestCase):
    """Every path the harness writes points into a temporary directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = {k: getattr(I, k) for k in ("RUNS", "OUT", "SMOKE")}
        I.RUNS, I.OUT, I.SMOKE = root / "runs", root / "out", root / "smoke"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(I, k, v)
        self.tmp.cleanup()

    def done(self, key, *steps):
        for s in steps:
            I.write_atomic(I.step_dir(key, s) / "aggregate.json", "{}")


class Lessons(unittest.TestCase):
    def test_cut_rule_keeps_five_lessons_and_150_words(self):
        text = "\n".join(f"- lesson {k} " + "w " * 40 for k in range(7))
        kept, cut = I.limit_lessons(text)
        lines = kept.splitlines()
        self.assertEqual(cut["lessons_written"], 7)
        self.assertTrue(cut["cut"])
        self.assertLessEqual(len(lines), 5)
        self.assertEqual(sum(len(x[2:].split()) for x in lines), 150)
        self.assertTrue(all(x.startswith("- ") for x in lines))

    def test_cut_rule_without_dash_lines_and_empty(self):
        kept, cut = I.limit_lessons("1. Hit when it pays.\n\n* Keep the bar closed.")
        self.assertEqual(kept, "- Hit when it pays.\n- Keep the bar closed.")
        self.assertFalse(cut["cut"])
        self.assertEqual(I.limit_lessons("")[0], "")

    def test_context_is_the_pilots(self):
        self.assertEqual(I.lessons_context([(1, ""), (2, "")]), "")
        ctx = I.lessons_context([(1, "- a"), (2, ""), (3, "- b")])
        self.assertTrue(ctx.startswith(I.OPEN) and ctx.endswith(I.CLOSE))
        self.assertLess(ctx.index("After game 1:\n- a"), ctx.index("After game 3:\n- b"))
        self.assertNotIn("After game 2", ctx)

    def test_lesson_prompt_and_seeds_are_the_pilots(self):
        self.assertEqual(I.lesson_prompt_sha256(), I.LESSON_PROMPT_SHA256)
        seed = int(hashlib.sha256(b"learning-pilot 2026-11-07 series 3").hexdigest()[:16], 16) & (2**63 - 1)
        self.assertEqual(I.series_seed(3), seed)


class Schedule(Isolated):
    def test_step_order_and_next_step(self):
        self.assertEqual(I.STEPS, ["E1", "S1", "S2", "E2", "S3", "S4", "E3", "S5"])
        self.assertEqual(I.next_step(KEY), "E1")
        self.done(KEY, "E1", "S1", "S2")
        self.assertEqual(I.next_step(KEY), "E2")
        self.done(KEY, *I.STEPS)
        self.assertIsNone(I.next_step(KEY))

    def test_every_plan_model_has_a_progress_object(self):
        I.write_atomic(I.mdir("glm-5.3-on") / "hold.json", json.dumps(dict(reason="paused: shared-balance priority, Ümit #3215")))
        self.done(KEY, "E1", "S1")
        I.log(KEY, "step_start", step="S2")
        saved_active = I.run_active
        I.run_active = lambda key: key == KEY
        try:
            rows = {k: I.progress(k, *I.model_state(k)) for k in I.MODELS}
        finally:
            I.run_active = saved_active
        self.assertEqual(len(rows), 15)
        self.assertEqual((rows[KEY]["status"], rows[KEY]["reason"], rows[KEY]["series_done"]), ("running", None, 1))
        self.assertEqual((rows["glm-5.3-on"]["status"], rows["glm-5.3-on"]["reason"]), ("paused", "shared-balance priority"))
        self.assertEqual(rows["claude-opus-5.5-on"]["reason"], "waiting for its turn")
        self.assertIn(rows["gpt-6.1-sol-high"]["reason"], ("waiting for the ChatGPT reset 13 Nov", "waiting for its turn"))
        self.assertTrue(all(r["reason"] in (None,) + I.PROGRESS_REASONS for r in rows.values()))
        self.done(KEY, *I.STEPS)
        self.assertEqual(I.progress(KEY, *I.model_state(KEY)), dict(status="done", reason=None, series_done=5,
                                                                    updated_at=I.events(KEY)[-1]["at"]))
        self.assertEqual(I.progress_reason("S1: usage limit (429) on the subscription: QUOTA: 429"), "usage limit")
        with self.assertRaises(ValueError):  # a pause the page has no text for is not hidden
            I.progress_reason("something else")

    def test_export_keeps_writing_when_a_pause_has_no_page_text(self):
        first = I.summary()
        self.assertEqual(len(first["models"]), 15)
        I.write_atomic(I.mdir(KEY) / "paused.json", json.dumps(dict(at="t", reason="an unforeseen pause")))
        out = I.summary()
        kept = [m for m in out["models"] if m["key"] == KEY]
        self.assertEqual(kept, [m for m in first["models"] if m["key"] == KEY])  # the last exported entry, not invented
        self.assertEqual(len(out["models"]), 15)
        self.assertIn("unforeseen", (I.RUNS / "export-errors.log").read_text())
        written = json.loads((I.OUT / "improve.json").read_text())
        self.assertEqual(written["updated_at"], out["updated_at"])
        self.assertFalse(list(I.OUT.glob("*.tmp")))  # atomic: no temp file left

    def test_a_model_claimed_by_another_lane_is_refused(self):
        I.write_atomic(I.mdir("qwen3.8-27b-on") / "lane.json", json.dumps(dict(lane="improve-local3")))
        os.environ.pop("IMPROVE_LANE", None)
        with self.assertRaises(SystemExit):
            I.run("qwen3.8-27b-on")
        os.environ["IMPROVE_LANE"] = "improve-local"
        try:
            with self.assertRaises(SystemExit):
                I.run("qwen3.8-27b-on")
        finally:
            os.environ.pop("IMPROVE_LANE", None)

    def test_a_started_model_without_a_run_process_is_waiting_for_its_turn(self):
        """Main (Ümit #3465): a model whose lane was reordered mid-E1 is waiting, not running; kept answers stay."""
        I.log(KEY, "step_start", step="E1")
        saved = I.run_active
        try:
            I.run_active = lambda key: False
            self.assertEqual(I.model_state(KEY), ("paused", I.TURN))
            self.assertEqual(I.progress(KEY, *I.model_state(KEY))["reason"], "waiting for its turn")
            I.run_active = lambda key: True
            self.assertEqual(I.model_state(KEY), ("running", None))
        finally:
            I.run_active = saved

    def test_run_active_finds_a_run_process(self):
        import subprocess
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "x/improve.py", "run", "--model",
                              "zz-test-model"])
        try:
            for _ in range(50):
                if I.run_active("zz-test-model"):
                    break
                time.sleep(0.02)
            self.assertTrue(I.run_active("zz-test-model"))
            self.assertFalse(I.run_active("zz-other"))
        finally:
            p.kill()
            p.wait()

    def test_every_exported_reason_passes_the_site_text_pattern(self):
        """Main: models[].reason must match the site's TEXT pattern (improve_validate: [^<>&\\x00-\\x1f]{1,400})."""
        import re as _re
        TEXT = _re.compile(r"[^<>&\x00-\x1f]{1,400}")
        raw = [
            'S2: usage limit (429) on the subscription: jevgammon: player 1: claude-fable-5-1 request failed: QUOTA: 429 '
            'Too Many Requests: {"type":"error","error":{"type":"rate_limit_error","message":"This request would '
            'exceed your account\'s rate limit. Please try again later."},"request_id":"req_011CgsgwYUvRLWnfUvDKdyBx"}\n',
            "S2: jevgammon: player 1: claude-fable-5-1 request failed: gave up after 4 attempts: 529 <unknown status "
            'code>: {"type":"error","error":{"type":"overloaded_error"}}',
            "S4: paused: shared-balance priority (provider account limit: HTTP 403 key limit / 402 credits): 403 Forbidden",
            "S1: route check: responses named [('x', 'y')] <bad> & more",
            "rule (a): projected full cost $3.95 (5 x S1 $0.70 + 3 x E1 $0.15) > 1.5 x estimate $2.30 = $3.45",
            "paused: shared-balance priority, Ümit #3215",
            "line one\nline two\twith a tab " + "x" * 600,
            "\x07\n",
        ]
        for r in raw:
            out = I.public_reason(r)
            self.assertTrue(TEXT.fullmatch(out), repr(out))
            self.assertLessEqual(len(out), 200)
        self.assertEqual(I.public_reason(raw[0]), "S2: usage limit (429 rate_limit_error)")
        self.assertEqual(I.public_reason(raw[1]), "S2: provider overloaded (529)")
        self.assertIsNone(I.public_reason(None))
        # The live export: every model's reason passes.
        out = I.summary()
        for m in out["models"]:
            if m["reason"] is not None:
                self.assertTrue(TEXT.fullmatch(m["reason"]), (m["key"], m["reason"]))

    def test_restarted_series_is_archived_with_new_names(self):
        d = I.step_dir(KEY, "S2")
        d.mkdir(parents=True)
        (d / "lessons-g01.txt").write_text("- x\n")
        (d / "failed").write_text("boom")
        self.assertEqual(I.game_name(KEY, 2, I.attempt_of(KEY, "S2")), "Qwen3.8 Flash (off) | improve | s02 | a1")
        I.archive_attempt(KEY, "S2", "boom")
        self.assertTrue((d / "attempt-1" / "lessons-g01.txt").exists())
        self.assertFalse((d / "lessons-g01.txt").exists())
        self.assertEqual(I.attempt_of(KEY, "S2"), 2)
        self.assertEqual(I.test_name(KEY, "S2", 2), "Qwen3.8 Flash (off) | improve | s02 | a2 | T10")
        self.assertEqual(I.test_name(KEY, "E2"), "Qwen3.8 Flash (off) | improve | E2")


class Money(Isolated):
    def test_rule_a_projection_at_the_boundary(self):
        # 1.5 x $2.30 = $3.45; 5 x 0.60 + 3 x 0.15 = 3.45 exactly: not more than the limit.
        self.assertIsNone(I.rule_a(KEY, 0.60, 0.15))
        self.assertIn("rule (a)", I.rule_a(KEY, 0.61, 0.15))
        self.assertAlmostEqual(I.projected_full(1.0, 0.5), 6.5)

    def test_rule_b_and_balance(self):
        self.assertIsNone(I.rule_b(100.0, 10.0))
        self.assertIn("rule (b)", I.rule_b(100.0, 10.01))
        self.assertIsNone(I.balance_shortfall(10.0, 5.0))
        self.assertIn("reserve", I.balance_shortfall(10.0, 5.01))

    def test_ledger_cap_takes_the_binding_limit(self):
        cap, binding, limits = I.ledger_cap(KEY, balance=100.0, model_billed=1.0, total=50.0)
        self.assertEqual(binding, "rule (a) limit")
        self.assertAlmostEqual(cap, 3.45 - 1.0)
        cap, binding, _ = I.ledger_cap(KEY, balance=6.0, model_billed=0.0, total=0.0)
        self.assertEqual((binding, round(cap, 6)), ("balance", 1.0))
        cap, binding, _ = I.ledger_cap(KEY, balance=500.0, model_billed=0.0, total=108.0)
        self.assertEqual((binding, round(cap, 6)), ("rule (b) limit", 2.0))

    def test_billed_counts_settled_lost_and_in_flight(self):
        d = I.mdir(KEY) / "ledgers"
        make_ledger(d / "E1-a1.db", settled=0.10, lost=0.02, reported=0.08)
        make_ledger(d / "S1-a1.db", settled=0.30, open_=0.05)
        self.assertAlmostEqual(I.billed(KEY, "E1"), 0.12)
        self.assertAlmostEqual(I.billed(KEY, "S1"), 0.35)
        self.assertAlmostEqual(I.billed(KEY), 0.47)
        self.assertAlmostEqual(I.reported(KEY), 0.08)

    def test_step_estimate_switches_to_measured_after_the_cost_check(self):
        self.assertEqual(I.step_estimate(KEY, "S2"), 0.35)
        self.assertEqual(I.step_estimate(KEY, "E2"), 0.18)
        d = I.mdir(KEY) / "ledgers"
        make_ledger(d / "E1-a1.db", settled=0.2)
        make_ledger(d / "S1-a1.db", settled=0.5)
        I.write_atomic(I.mdir(KEY) / "cost_check.json", "{}")
        self.assertAlmostEqual(I.step_estimate(KEY, "S2"), 0.5)
        self.assertAlmostEqual(I.step_estimate(KEY, "E2"), 0.2)

    def test_money_gate_stops_pauses_or_caps(self):
        rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
        gate = I.money_gate(KEY, "E1", rich)
        self.assertEqual(gate["binding"], "rule (a) limit")
        self.assertAlmostEqual(gate["cap"], 3.45)
        poor = lambda: dict(balance=5.10, total_credits=5.10, total_usage=0.0, at="t")  # noqa: E731
        with self.assertRaises(I.Pause):
            I.money_gate(KEY, "S1", poor)  # 5.10 - 5 < 0.35
        # Another model has booked $109.90: S1's expected $0.35 would pass $110.
        make_ledger(I.mdir("glm-5.3-on") / "ledgers" / "S1-a1.db", settled=109.90)
        with self.assertRaises(I.Stop):
            I.money_gate(KEY, "S1", rich)

    def test_run_stops_or_pauses_by_the_binding_limit_and_applies_rule_a(self):
        calls = []
        saved = (I.check_inputs, I.ensure_runner_db, I.run_empty, I.run_series, I.summary, I.response_ids,
                 I.bind_plan)
        rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
        poor = lambda: dict(balance=5.50, total_credits=5.5, total_usage=0.0, at="t")  # noqa: E731

        def fake_step(key, step, gate):
            calls.append((step, gate["binding"], round(gate["cap"], 4)))
            make_ledger(I.mdir(key) / "ledgers" / f"{step}-a1.db", settled={"E1": 0.15, "S1": 0.70}[step])
            self.done(key, step)

        try:
            I.check_inputs = I.ensure_runner_db = I.bind_plan = lambda *a: None
            I.summary = lambda: None
            I.response_ids = lambda key, step: [("qwen/qwen3.8-flash", "Alibaba")]
            I.run_empty = I.run_series = fake_step
            # E1 then S1, then the cost check: 5 x 0.70 + 3 x 0.15 = 3.95 > 3.45: rule (a) stops the model.
            self.assertEqual(I.run(KEY, balance_reader=rich), I.STOP)
            self.assertEqual([c[0] for c in calls], ["E1", "S1"])
            self.assertIn("rule (a)", json.loads((I.mdir(KEY) / "stopped.json").read_text())["reason"])
            self.assertEqual(I.run(KEY, balance_reader=rich), I.STOP)  # stays stopped
            # A refused reservation: a pause when the balance limit binds, a stop otherwise.
            other = "glm-5.3-on"

            def refused(key, step, gate):
                raise I.BudgetRefused("BUDGET CAP: refused")
            I.run_empty = refused
            self.assertEqual(I.run(other, balance_reader=poor), I.PAUSE)  # cap = 0.50: the balance binds
            self.assertTrue((I.mdir(other) / "paused.json").exists())
            self.assertEqual(I.run(other, balance_reader=rich), I.STOP)  # rule (a) limit binds
        finally:
            (I.check_inputs, I.ensure_runner_db, I.run_empty, I.run_series, I.summary, I.response_ids,
             I.bind_plan) = saved

    def test_share_limit_pauses(self):
        rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
        I.write_atomic(I.RUNS / "share_cap.json", json.dumps(dict(usd=55.0, note="t", at="t")))
        make_ledger(I.mdir("glm-5.3-on") / "ledgers" / "S1-a1.db", settled=54.80)
        with self.assertRaises(I.Pause):
            I.money_gate(KEY, "S1", rich)  # 54.80 + 0.35 > 55
        gate = I.money_gate(KEY, "E1", rich)  # 54.80 + 0.18 <= 55
        self.assertEqual(gate["binding"], "share")
        self.assertAlmostEqual(gate["cap"], 0.20)

    def test_plan_identity_is_stored_and_resume_refuses_a_changed_plan(self):
        plan = Path(self.tmp.name) / "plan.md"
        plan.write_text("published plan")
        saved = (I.PLAN, I.PLAN_SHA256)
        try:
            I.PLAN, I.PLAN_SHA256 = plan, I.sha256_file(plan)
            I.SMOKE.mkdir(parents=True)
            bound = I.bind_plan(KEY)
            self.assertEqual(bound, I.PLAN_SHA256)
            db = sqlite3.connect(I.db_path(KEY))
            self.assertEqual(db.execute("SELECT value FROM improve_identity").fetchone()[0], bound)
            db.close()
            self.assertEqual(I.bind_plan(KEY), bound)  # resume with the same plan
            plan.write_text("edited plan")
            with self.assertRaises(SystemExit):
                I.bind_plan(KEY)  # resume refused
            self.assertEqual(I.bound_plan([KEY]), bound)  # summaries keep the stored identity
            self.assertEqual(I.summary()["protocol"]["plan_sha256"], bound)
            # A model that has not started cannot start under a plan that is not the published one.
            with self.assertRaises(SystemExit):
                I.bind_plan("glm-5.3-on")
        finally:
            I.PLAN, I.PLAN_SHA256 = saved

    def test_route_check(self):
        self.assertIsNone(I.route_check("deepseek-v4.1-flash-on", [("deepseek/deepseek-v4.1-flash", "Fireworks")]))
        self.assertIn("route check", I.route_check("deepseek-v4.1-flash-on",
                                                   [("deepseek/deepseek-v4.1-flash-1017", "Fireworks")]))
        self.assertIn("route check", I.route_check("deepseek-v4.1-flash-on",
                                                   [("deepseek/deepseek-v4.1-flash", "Alibaba")]))
        self.assertIsNone(I.route_check("claude-opus-5.5-on", [("claude-opus-5-5", None)]))
        self.assertIn("route check", I.route_check("claude-opus-5.5-on", [("claude-sonnet-5-5", None)]))
        self.assertIn("fails closed", I.route_check("deepseek-v4.1-flash-on", []))  # no evidence
        self.assertIn("route check", I.route_check("deepseek-v4.1-flash-on", [(None, None)]))

    def test_billed_players_carry_the_route_guard(self):
        p = I.player_config("deepseek-v4.1-flash-on", "n", 1)
        self.assertEqual(p["expect_route"]["models"][0], "deepseek/deepseek-v4.1-flash")
        self.assertEqual(p["expect_route"]["provider"], "Fireworks")
        self.assertTrue(p["expect_route"]["reject_log"].endswith("route-rejections.jsonl"))
        p = I.player_config("claude-opus-5.5-on", "n", 1)
        self.assertEqual((p["expect_route"]["models"], p["quota_pause"]), (["claude-opus-5-5"], True))
        self.assertNotIn("provider", p["expect_route"])
        p = I.player_config("gemini-3.8-flash-high", "n", 1)
        self.assertEqual(p["expect_route"]["model_pointer"], "/response/modelVersion")
        self.assertNotIn("quota_pause", p)

    def test_a_rejected_route_stops_before_any_step(self):
        I.write_atomic(I.mdir(KEY) / "route-rejections.jsonl", '{"reason": "wrong model"}\n')
        saved = (I.check_inputs, I.ensure_runner_db, I.bind_plan, I.summary, I.run_empty)
        try:
            I.check_inputs = I.ensure_runner_db = I.bind_plan = lambda *a: None
            I.summary = lambda: None
            I.run_empty = lambda *a: self.fail("a step ran after a route rejection")
            rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
            self.assertEqual(I.run(KEY, balance_reader=rich), I.STOP)
            self.assertIn("wrong model", json.loads((I.mdir(KEY) / "stopped.json").read_text())["reason"])
        finally:
            (I.check_inputs, I.ensure_runner_db, I.bind_plan, I.summary, I.run_empty) = saved


class Metrics(unittest.TestCase):
    def test_shares_over_valid_answers_with_counts(self):
        positions = {
            "r1": dict(shots=[0, 5], losses=[0.05, 0.0]),  # risk pays (taking the shot is best)
            "r2": dict(shots=[0, 5], losses=[0.05, 0.0]),
            "s1": dict(shots=[0, 5], losses=[0.0, 0.05]),  # safety pays
            "s2": dict(shots=[0, 5], losses=[0.0, 0.05]),
        }
        row = lambda pid, i, invalid=0, error=None: dict(position_id=pid, chosen_index=i, invalid=invalid,  # noqa
                                                          error=error, in_flight=3)
        rows = [row("r1", 1), row("r2", 0), row("s1", 0), row("s2", None, invalid=1)]
        m = I.metrics_from(rows, positions)
        self.assertEqual((m["answered"], m["valid"], m["invalid"], m["failed"]), (4, 3, 1, 0))
        self.assertEqual((m["risk_pays"], m["safety_pays"]), (2, 1))
        self.assertEqual((m["risks_found"], m["right_safety"]), (50.0, 100.0))
        self.assertAlmostEqual(m["error_rate"], 500 * 0.05 / 3)
        self.assertEqual(m["answer_rate"], 1.5)  # 3 valid of 200
        self.assertEqual(m["in_flight_max"], 3)
        m = I.metrics_from(rows + [row("s1", None, error="HTTP 500")], positions)
        self.assertEqual(m["failed"], 1)
        self.assertFalse(I.test_complete(m))


class KeyLimit(Isolated):
    """Zeki/Main: a provider account limit (403 key limit, 402 credits) pauses the model at once; other 403s do not."""

    def setUp(self):
        super().setUp()
        root = Path(self.tmp.name)
        self.saved_bin = I.BIN
        fake = root / "jevgammon"
        fake.write_text(f"#!/bin/sh\nexec {sys.executable} {Path(I.__file__).with_name('fake_ask.py')} \"$@\"\n")
        fake.chmod(0o755)
        I.BIN = fake
        I.SMOKE.mkdir(parents=True)
        self.ledger = root / "ledger.db"
        db = sqlite3.connect(self.ledger)
        db.execute("CREATE TABLE attempts (id INTEGER PRIMARY KEY, status TEXT, pid INTEGER, reserved_usd REAL, "
                   "cost_usd REAL, reported_cost_usd REAL)")
        db.commit()
        db.close()
        self.dispatch = root / "dispatch.log"
        os.environ.update(FAKE_LEDGER=str(self.ledger), FAKE_DISPATCH_LOG=str(self.dispatch))

    def tearDown(self):
        I.BIN = self.saved_bin
        for k in ("FAKE_MODE", "FAKE_LEDGER", "FAKE_DISPATCH_LOG"):
            os.environ.pop(k, None)
        super().tearDown()

    def ask(self, mode, rounds=1):
        os.environ["FAKE_MODE"] = mode
        d = I.step_dir(KEY, "E1")
        return I.run_test(KEY, "E1", I.test_name(KEY, "E1"), "", d, ledger=dict(path=str(self.ledger), cap=1.0),
                          rounds=rounds)

    def dispatched(self):
        return self.dispatch.read_text().split() if self.dispatch.exists() else []

    def test_key_limit_pauses_at_once_and_resume_reasks_only_failed_positions(self):
        with self.assertRaises(I.Pause):
            self.ask("keylimit", rounds=30)
        sent = self.dispatched()
        # 3 answered, then the first refusal; dispatch stops soon after (no retry loop, no sweep of 200). The bound
        # holds for this serial test double's timing only; it is not a proved bound for the real runner.
        self.assertLessEqual(len(sent), 3 + 1 + 4, sent)
        hold = json.loads((I.mdir(KEY) / "hold.json").read_text())
        self.assertIn("shared-balance priority", hold["reason"])
        event = [e for e in I.events(KEY) if e["event"] == "key_limit"][0]
        self.assertIn("Key limit exceeded", event["provider_text"])
        db = sqlite3.connect(I.db_path(KEY))
        failed = {r[0] for r in db.execute("SELECT position_id FROM answers WHERE error IS NOT NULL")}
        db.close()
        self.assertTrue(failed)  # failed positions are kept for the re-ask
        led = sqlite3.connect(self.ledger)
        self.assertEqual(led.execute("SELECT COUNT(*) FROM attempts WHERE status = 'open'").fetchone()[0], 0)
        self.assertEqual(led.execute("SELECT SUM(cost_usd) FROM attempts WHERE cost_usd = 0").fetchone()[0] or 0, 0)
        led.close()
        # While held, nothing is dispatched.
        with self.assertRaises(I.Pause):
            self.ask("resume")
        self.assertEqual(len(self.dispatched()), len(sent))
        # Hold lifted: only the failed and unasked positions are asked; the answered ones are not asked again.
        (I.mdir(KEY) / "hold.json").unlink()
        answered = set(sent[:3])
        m = self.ask("resume")
        again = self.dispatched()[len(sent):]
        self.assertFalse(answered & set(again))
        self.assertTrue(failed <= set(again))
        self.assertEqual((m["answered"], m["failed"]), (200, 0))

    def seed(self, failed_error):
        """199 answered positions, then the last one failed with the highest row id (as after an earlier run)."""
        ids = [json.loads(line)["id"] for line in open(I.TEST_POSITIONS)]
        db = sqlite3.connect(I.db_path(KEY))
        db.execute("CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY, setup TEXT, position_id TEXT, "
                   "repeat INTEGER, chosen_index INTEGER, invalid INTEGER, error TEXT, in_flight INTEGER, "
                   "cost_usd REAL, created_at TEXT)")
        name = I.test_name(KEY, "E1")
        for k, pid in enumerate(ids):
            failed = k == len(ids) - 1
            db.execute("INSERT INTO answers (setup, position_id, repeat, chosen_index, invalid, error, in_flight, "
                       "created_at) VALUES (?, ?, 1, ?, 0, ?, 1, '1.0')",
                       (name, pid, None if failed else 0, failed_error if failed else None))
        db.commit()
        top = db.execute("SELECT id, position_id FROM answers ORDER BY id DESC LIMIT 1").fetchone()
        db.close()
        return top

    STALE = ('credential rejected: 403 Forbidden: {"error":{"message":"Key limit exceeded (total limit)"}}')

    def test_a_fresh_key_limit_on_the_highest_id_retry_pauses(self):
        """Zeki #3285: the re-asked position reuses the highest row id; its fresh failure is still this asking's."""
        top = self.seed(self.STALE)
        with self.assertRaises(I.Pause):
            self.ask("retry-keylimit", rounds=30)
        db = sqlite3.connect(I.db_path(KEY))
        again = db.execute("SELECT id FROM answers WHERE position_id = ?", (top[1],)).fetchone()
        db.close()
        self.assertEqual(again[0], top[0])  # the same id, reused
        self.assertEqual(self.dispatched(), [top[1]])
        self.assertTrue((I.mdir(KEY) / "hold.json").exists())

    def test_a_successful_resume_ignores_stale_failures(self):
        top = self.seed(self.STALE)
        m = self.ask("resume")
        self.assertEqual((m["answered"], m["failed"]), (200, 0))
        self.assertEqual(self.dispatched(), [top[1]])
        self.assertFalse((I.mdir(KEY) / "hold.json").exists())

    def test_a_key_limit_printed_on_stdout_only_is_detected(self):
        with self.assertRaises(I.Pause):
            self.ask("stdout-keylimit", rounds=30)
        self.assertLessEqual(len(self.dispatched()), 1 + 4)  # the serial double's timing, not a runner bound
        self.assertTrue((I.mdir(KEY) / "hold.json").exists())

    def test_an_ordinary_403_is_a_failed_request_as_before(self):
        m = self.ask("plain403")
        self.assertEqual((m["answered"], m["failed"]), (200, 200))
        self.assertFalse((I.mdir(KEY) / "hold.json").exists())
        self.assertFalse([e for e in I.events(KEY) if e["event"] == "key_limit"])

    def test_key_limit_texts(self):
        self.assertIsNotNone(I.key_limit_text('credential rejected: 403 Forbidden: {"error":{"message":"Key limit exceeded (total limit)"}}'))
        self.assertIsNotNone(I.key_limit_text("request failed: 402 Payment Required: Insufficient credits"))
        self.assertIsNone(I.key_limit_text('credential rejected: 403 Forbidden: {"error":{"message":"Invalid API key"}}'))
        self.assertIsNone(I.key_limit_text("429 Too Many Requests: rate limit exceeded"))


class FitCheck(Isolated):
    def test_kv_capacity_must_hold_four_full_sequences(self):
        I.write_atomic(I.mdir("qwen3.8-27b-on") / "base_url.txt", "http://h:1/v1")

        def server(blocks):
            def fetch(url):
                if url.endswith("/models"):
                    return json.dumps(dict(data=[dict(id="m", max_model_len=65536)]))
                return ('# HELP\nvllm:cache_config_info{block_size="16",num_gpu_blocks="%d",x="y"} 1.0\n' % blocks)
            return fetch
        rec = I.fit_check("qwen3.8-27b-on", server(16384))  # 262,144 tokens = 4 sequences
        self.assertEqual(rec["sequences"], 4.0)
        with self.assertRaises(SystemExit):
            I.fit_check("qwen3.8-27b-on", server(16383))


if __name__ == "__main__":
    unittest.main()
