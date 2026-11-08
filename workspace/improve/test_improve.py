"""Unit tests for workspace/improve/improve.py (no model call, no runner, no network):

    python3 -m unittest workspace/improve/test_improve.py -v
"""

import hashlib
import json
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
        saved = (I.check_inputs, I.ensure_runner_db, I.run_empty, I.run_series, I.summary, I.response_ids)
        rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
        poor = lambda: dict(balance=5.50, total_credits=5.5, total_usage=0.0, at="t")  # noqa: E731

        def fake_step(key, step, gate):
            calls.append((step, gate["binding"], round(gate["cap"], 4)))
            make_ledger(I.mdir(key) / "ledgers" / f"{step}-a1.db", settled={"E1": 0.15, "S1": 0.70}[step])
            self.done(key, step)

        try:
            I.check_inputs = I.ensure_runner_db = lambda *a: None
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
            (I.check_inputs, I.ensure_runner_db, I.run_empty, I.run_series, I.summary, I.response_ids) = saved

    def test_share_limit_pauses(self):
        rich = lambda: dict(balance=500.0, total_credits=600.0, total_usage=100.0, at="t")  # noqa: E731
        I.write_atomic(I.RUNS / "share_cap.json", json.dumps(dict(usd=55.0, note="t", at="t")))
        make_ledger(I.mdir("glm-5.3-on") / "ledgers" / "S1-a1.db", settled=54.80)
        with self.assertRaises(I.Pause):
            I.money_gate(KEY, "S1", rich)  # 54.80 + 0.35 > 55
        gate = I.money_gate(KEY, "E1", rich)  # 54.80 + 0.18 <= 55
        self.assertEqual(gate["binding"], "share")
        self.assertAlmostEqual(gate["cap"], 0.20)

    def test_route_check(self):
        self.assertIsNone(I.route_check("deepseek-v4.1-flash-on", [("deepseek/deepseek-v4.1-flash", "Fireworks")]))
        self.assertIn("route check", I.route_check("deepseek-v4.1-flash-on",
                                                   [("deepseek/deepseek-v4.1-flash-1017", "Fireworks")]))
        self.assertIn("route check", I.route_check("deepseek-v4.1-flash-on",
                                                   [("deepseek/deepseek-v4.1-flash", "Alibaba")]))
        self.assertIsNone(I.route_check("claude-opus-5.5-on", [("x", "y")]))  # not billed: no check


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
