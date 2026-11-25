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


class SmallModels(unittest.TestCase):
    """The amendments (Ümit native 1570509348072063026 via Zeki #5674/#5689; Ümit #13295): the Tiny and Small chat
    models of Logic & Math and the models of 2B or less, local rows under the same plan, each with its served name."""

    SMALL = {"gemma-4-e4b-on": "gemma-4-e4b-it", "minicpm5-2b-on": "minicpm5-2b", "lfm2.5-2.6b-on": "lfm2.5-2.6b",
             "lfm2.5-8b-a1b-on": "lfm2.5-8b-a1b", "lfm3-1.7b-on": "lfm3-1.7b", "gemma-4-e2b-on": "gemma-4-e2b-it",
             "gemma-4-12b-on": "gemma-4-12b-it", "erk-14b-on": "erk-14b", "qwen3-14b-on": "qwen3-14b",
             "lfm3-1.7b-off": "lfm3-1.7b", "qwen3.5-2b-on": "qwen3.5-2b", "raon-1-nano-on": "raon-1-nano",
             "smollm2-1.7b": "smollm2-1.7b", "smollm2-360m": "smollm2-360m",
             "smollm3-3b-off": "smollm3-3b", "smollm3-3b-on": "smollm3-3b"}
    GATED = {"lfm3-1.7b-on", "lfm3-1.7b-off", "minicpm5-2b-on", "qwen3.5-2b-on", "gemma-4-e2b-on", "raon-1-nano-on",
             "smollm2-1.7b", "smollm2-360m", "smollm3-3b-on"}

    def test_every_small_chat_row_is_local_unbilled_with_its_served_name_and_in_the_amendment(self):
        for key, served in self.SMALL.items():
            m = I.MODELS[key]
            self.assertEqual((m["lane"], m["expect"]), ("local", dict(models=[served])), key)
            self.assertFalse(m.get("billed"), key)
            mode = key.rsplit("-", 1)[1]
            if mode in ("on", "off"):
                self.assertTrue(m["setup"].endswith(f" ({mode})"), key)
        self.assertEqual(I.MODELS["gemma-4-e4b-on"]["setup"], "Gemma 4 E4B (on)")
        self.assertEqual((I.MODELS["smollm2-1.7b"]["setup"], I.MODELS["smollm2-360m"]["setup"]),
                         ("SmolLM2-1.7B-Instruct", "SmolLM2-360M-Instruct"))
        a, b, c = I.AMENDMENTS[:3]
        self.assertEqual(sorted(a["added"] + b["added"] + c["added"]), sorted(self.SMALL))
        self.assertIn("1570509348072063026", a["source"])
        self.assertIn("#13295", b["source"])
        self.assertIn("#13462", c["source"])
        self.assertEqual(I.VALIDITY_GATED,
                         self.GATED | {"lfm2.5-24b-a2b-off", "inkling-2-mini-on", "inkling-2-mini-e05",
                                       "inkling-2-mini-e02"})
        self.assertEqual(c["check_only"], [k for k, m in I.MODELS.items() if m.get("check_only")])
        keys = list(I.MODELS)  # Ümit #13489: SmolLM3-3B last in the small lane, (off) before (on)
        self.assertEqual(keys[keys.index("smollm2-360m") + 1:keys.index("smollm2-360m") + 3],
                         ["smollm3-3b-off", "smollm3-3b-on"])

    def test_logic_routes_match_small_models_names_and_take_its_ports(self):
        import importlib.util
        import re
        import subprocess
        path = Path("/home/cbasaran/code/benchmark/logic/work/small_models.py")
        if not path.exists():
            self.skipTest(f"no {path}")
        spec = importlib.util.spec_from_file_location("small_models", path)
        sm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sm)
        script = (Path(__file__).resolve().parent / "run_local.sh").read_text()
        routes = re.findall(r'^\s*([\w.|-]+)\) echo "logic:(\S+) (\S+) - -"', script, re.M)
        self.assertEqual({k for keys, *_ in routes for k in keys.split("|")},
                         set(self.SMALL) - {"erk-14b-on", "qwen3-14b-on"})
        # The port: small_models.py's own, read when the model starts (its ports move with its SETUPS order).
        port = script[script.index("logic_port() {"):].split("\n}\n", 1)[0] + "\n}"
        for keys, logic, name in routes:
            s = sm.SETUPS[logic]
            got = subprocess.run(["bash", "-c", f'PY={sys.executable}; SMALL_MODELS={path}\n{port}\nlogic_port {logic}'],
                                 capture_output=True, text=True, check=True).stdout
            self.assertEqual(got, f"{s['port']}\n", logic)
            process = "venv" in s or s["server"] == "llama.cpp"
            self.assertEqual(name, "-" if process else f"logic-small-{logic}", logic)
            for key in keys.split("|"):
                self.assertEqual(I.MODELS[key]["expect"]["models"], [sm.model_name(logic)], key)
        # SmolLM3-3B: logic's Logic & Math load (its :18710 server), pinned, vLLM v0.30.0, qwen3 reasoning parser.
        s = sm.SETUPS["smollm3-3b"]
        self.assertEqual((s["port"], s["repo"], s["rev"], s["image"], s["max_model_len"], s["vllm_args"]),
                         (18710, "HuggingFaceTB/SmolLM3-3B", "a07cc9a04f16550a088caea529712d1d335b0ac1", sm.VLLM_DIGEST,
                          65536, ["--reasoning-parser", "qwen3"]))

    def test_a_row_without_settings_exports_but_cannot_run(self):
        saved = I.has_setup
        I.has_setup = lambda setup: setup != "Erk-14B (on)" and saved(setup)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runs, out = I.RUNS, I.OUT
                I.RUNS, I.OUT = Path(tmp) / "runs", Path(tmp) / "out"
                try:
                    self.assertEqual(I.model_summary("erk-14b-on")["route"], "local")
                    self.assertEqual(I.summary()["amendments"], I.AMENDMENTS)
                finally:
                    I.RUNS, I.OUT = runs, out
        finally:
            I.has_setup = saved
        with self.assertRaises(SystemExit):
            I.league_settings("Erk-14B (on)")  # `run` builds its player from this: no settings, no run

    def test_export_off_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = I.OUT
            I.OUT = Path(tmp) / "out"
            os.environ["IMPROVE_EXPORT"] = "0"
            try:
                self.assertIsNone(I.summary())
                self.assertFalse(I.OUT.exists())
            finally:
                os.environ.pop("IMPROVE_EXPORT")
                I.OUT = out

    def test_the_local_lane_serves_it_with_logics_command_on_the_lanes_card(self):
        import subprocess
        here = Path(__file__).resolve().parent
        script = (here / "run_local.sh").read_text()
        funcs = "\n".join(script[script.index(f"{name}() {{"):].split("\n}\n", 1)[0] + "\n}"
                          for name in ("server", "start_server", "stop_server"))
        stub = (f'UUID=GPU-x; SERVERS=/srv; SMALL_MODELS=/logic/small_models.py\n{funcs}\n'
                'python3() { echo "python3 $*"; }; env() { echo "env $*"; }\n'
                'read -r script name port var < <(server gemma-4-e4b-on); echo "$name $port"\n'
                'start_server "$script" "$var" 3; stop_server "$script"\n'
                'read -r script name port var < <(server qwen3.8-27b-on); start_server "$script" "$var" 3\n')
        out = subprocess.run(["bash", "-c", stub], capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertEqual(out, ["logic-small-gemma-4-e4b-it -",
                               "python3 /logic/small_models.py serve gemma-4-e4b-it GPU-x",
                               "python3 /logic/small_models.py stop gemma-4-e4b-it",
                               "env QWEN27_GPU=3 /srv/qwen38-27b.sh start"])
        start = (here / "run_local_start.sh").read_text()
        container = start[start.index("container() {"):].split("esac; }", 1)[0] + "esac; }"
        for key in self.SMALL:  # the watcher's container is the lane's server container (none for a process server)
            got = subprocess.run(["bash", "-c", f"{funcs}\n{container}\nread -r s name p v < <(server {key}) || exit 9\n"
                                  f'echo "$name|$(container {key})"'], capture_output=True, text=True).stdout.strip()
            if key in ("erk-14b-on", "qwen3-14b-on"):  # no bariton route yet (logic serves them on spark2)
                self.assertEqual(got, "", key)
                continue
            name, watched = got.split("|")
            self.assertEqual(watched, "" if name == "-" else name, key)
        # Inkling 2 Mini: logic's shared load, never started, stopped or watched by the lane
        for key in ("inkling-2-mini-on", "inkling-2-mini-e05", "inkling-2-mini-e02"):
            got = subprocess.run(["bash", "-c", f"{funcs}\n{container}\nread -r s name p v < <(server {key})\n"
                                  f'echo "$s $name $p $v|$(container {key})"; stop_server "$s"; echo "rc $?"'],
                                 capture_output=True, text=True, check=True).stdout.splitlines()
            self.assertEqual(got, ["external:inkling-2-mini logic-small-inkling-2-mini 18712 -|", "rc 0"], key)


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
        self.assertEqual(len(rows), 39)
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
        n = sum(I.has_setup(m["setup"]) for m in I.MODELS.values())  # exported: the rows whose settings exist
        self.assertTrue(15 <= n < len(I.MODELS))
        self.assertEqual([m["key"] for m in first["models"]], [k for k in I.MODELS if I.has_setup(I.MODELS[k]["setup"])])
        I.write_atomic(I.mdir(KEY) / "paused.json", json.dumps(dict(at="t", reason="an unforeseen pause")))
        out = I.summary()
        kept = [m for m in out["models"] if m["key"] == KEY]
        self.assertEqual(kept, [m for m in first["models"] if m["key"] == KEY])  # the last exported entry, not invented
        self.assertEqual(len(out["models"]), n)
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

    def test_response_ids_uses_the_runners_checked_codex_identity(self):
        key, step = "gpt-6.2-astra-high", "E1"
        path = I.db_path(key)
        path.parent.mkdir(parents=True)
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE answers (id INTEGER PRIMARY KEY, setup TEXT)")
        db.execute("CREATE TABLE answer_exchanges (answer_id INTEGER, response TEXT, identity TEXT)")
        db.execute("INSERT INTO answers (id, setup) VALUES (1, ?)", (I.test_name(key, step),))
        checked = json.dumps({"result": "exact",
                              "fields": {"model": "gpt-6.2-astra", "provider": None}})
        db.execute("INSERT INTO answer_exchanges VALUES (1, ?, ?)", ("B", checked))
        db.commit()
        db.close()
        self.assertEqual(I.response_ids(key, step), [("gpt-6.2-astra", None)])

    def test_response_ids_excludes_archived_series_attempts(self):
        key, step = "gpt-6.2-astra-high", "S1"
        d = I.step_dir(key, step)
        archived = d / "attempt-1"
        archived.mkdir(parents=True)
        missing = {"exchanges": [{"response": "old answer"}]}
        checked = {"exchanges": [{"response": "new answer", "identity": json.dumps({
            "result": "accepted", "fields": {"model": "gpt-6.2-astra", "provider": None},
        })}]}
        (archived / "lessons-g01.call.json").write_text(json.dumps(missing))
        (d / "lessons-g01.call.json").write_text(json.dumps(checked))
        self.assertEqual(I.response_ids(key, step), [("gpt-6.2-astra", None)])

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
        old_rows = [{k: v for k, v in r.items() if k != "in_flight"} for r in rows]
        self.assertEqual(I.metrics_from(old_rows, positions)["in_flight_max"], 0)
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


class ValidityGate(Isolated):
    """Ümit #13295: a gated model's E1 is the validity check (more than 10% invalid: no series); a setup that sets a
    key the pinned runner drops is refused before any file is written."""

    def test_boundary_is_more_than_twenty_of_two_hundred(self):
        self.assertIsNone(I.validity(dict(invalid=20)))
        why = I.validity(dict(invalid=21))
        self.assertTrue(why.startswith("E1: validity check: 21 of 200 answers invalid (10.5%)"), why)
        self.assertRegex(I.public_reason(why), r"^[^<>&\x00-\x1f]{1,200}$")

    def test_run_stops_a_gated_model_after_e1_and_leaves_others_alone(self):
        names = ("check_inputs", "settings_check", "ensure_runner_db", "bind_plan", "fit_check", "run_empty",
                 "run_series", "summary", "response_ids")
        saved = {n: getattr(I, n) for n in names}
        calls = []

        def step(invalid):
            def run_step(key, s, gate):
                calls.append((key, s))
                I.write_atomic(I.step_dir(key, s) / "aggregate.json", json.dumps(dict(test=dict(invalid=invalid))))
            return run_step
        try:
            I.check_inputs = I.settings_check = I.ensure_runner_db = I.bind_plan = I.fit_check = lambda *a: None
            I.summary = lambda *a, **k: None
            I.response_ids = lambda key, s: [(I.MODELS[key]["expect"]["models"][0], None)]
            I.run_empty = I.run_series = step(21)
            self.assertEqual(I.run("smollm2-360m"), I.STOP)
            self.assertEqual(calls, [("smollm2-360m", "E1")])
            self.assertIn("validity check", json.loads((I.mdir("smollm2-360m") / "stopped.json").read_text())["reason"])
            self.assertEqual(I.run("smollm2-360m"), I.STOP)  # stays stopped
            self.assertEqual(I.run("gemma-4-e4b-on", until="S1"), 0)  # not gated
            self.assertFalse((I.mdir("gemma-4-e4b-on") / "validity.json").exists())
            I.run_empty = I.run_series = step(20)
            self.assertEqual(I.run("lfm3-1.7b-off", until="S1"), 0)
            self.assertEqual(json.loads((I.mdir("lfm3-1.7b-off") / "validity.json").read_text())["fired"], None)
            self.assertEqual(calls[-2:], [("lfm3-1.7b-off", "E1"), ("lfm3-1.7b-off", "S1")])
        finally:
            for n, f in saved.items():
                setattr(I, n, f)

    def test_settings_the_pinned_runner_drops_are_refused(self):
        saved = I.league_settings
        try:
            I.league_settings = lambda setup: dict(name=setup, spec="openai-compatible/m", reasoning_field="reasoning")
            with self.assertRaises(SystemExit) as e:
                I.settings_check("qwen3.5-2b-on")
            self.assertIn("reasoning_field", str(e.exception))
            I.league_settings = lambda setup: dict(name=setup, spec="openai-compatible/m", letter_readout="prefill")
            I.settings_check("lfm3-1.7b-off")
        finally:
            I.league_settings = saved

    def test_a_pin_that_reads_them_runs_them_after_its_parity_pass(self):
        """PIN_READS: jevgammon-c32fedb reads reasoning_prefill/reasoning_field, but only with a recorded parity PASS
        for that very binary (Ümit #13349); jevgammon-e417a0c still refuses them."""
        saved = I.league_settings, I.BIN
        try:
            I.league_settings = lambda setup: dict(name=setup, spec="openai-compatible/m", reasoning_field="reasoning",
                                                   reasoning_prefill="<think>\n{reasoning}\n</think>\n\nAnswer:")
            for commit in ("e417a0c", "c32fedb"):
                (Path(self.tmp.name) / f"jevgammon-{commit}").write_bytes(commit.encode())
            I.BIN = Path(self.tmp.name) / "jevgammon-e417a0c"
            with self.assertRaises(SystemExit) as e:
                I.settings_check("minicpm5-2b-on")
            self.assertIn("reasoning_field, reasoning_prefill", str(e.exception))
            I.BIN = Path(self.tmp.name) / "jevgammon-c32fedb"
            with self.assertRaises(SystemExit) as e:
                I.settings_check("minicpm5-2b-on")
            self.assertIn("parity", str(e.exception))
            record = dict(result="PASS", pin=dict(commit="c32fedb", sha256=I.sha256_file(I.BIN)))
            I.write_atomic(I.parity_path("c32fedb"), json.dumps(dict(record, result="FAIL")))
            with self.assertRaises(SystemExit):
                I.settings_check("minicpm5-2b-on")
            I.write_atomic(I.parity_path("c32fedb"), json.dumps(dict(record, pin=dict(sha256="0" * 64))))
            with self.assertRaises(SystemExit):  # another binary under the same name
                I.settings_check("minicpm5-2b-on")
            I.write_atomic(I.parity_path("c32fedb"), json.dumps(record))
            I.settings_check("minicpm5-2b-on")
        finally:
            I.league_settings, I.BIN = saved

    def test_the_export_names_each_rows_runner_pins(self):
        """Each exported row lists the pins its steps ran on (step_start's binary), once each, in order of first use."""
        self.assertEqual(I.model_summary("lfm3-1.7b-off")["runner"], [])
        old, new = dict(commit="e417a0c", sha256="a" * 64), dict(commit="c32fedb", sha256="b" * 64)
        for step, b in (("E1", new), ("S1", new), ("S2", old)):
            I.log("lfm3-1.7b-off", "step_start", step=step, gate=None, binary=dict(b, path="x", pinned=True))
        self.assertEqual(I.model_summary("lfm3-1.7b-off")["runner"], [new, old])


class SmolLM3(Isolated):
    """Ümit #13462: SmolLM3-3B with thinking on; with thinking off, the format check only."""

    def test_the_thinking_off_row_stops_after_its_format_check(self):
        names = ("check_inputs", "settings_check", "ensure_runner_db", "bind_plan", "fit_check", "run_empty",
                 "run_series", "summary", "response_ids")
        saved = {n: getattr(I, n) for n in names}
        calls = []

        def run_step(key, s, gate):
            calls.append((key, s))
            I.write_atomic(I.step_dir(key, s) / "aggregate.json", json.dumps(dict(test=dict(invalid=7))))
        try:
            I.check_inputs = I.settings_check = I.ensure_runner_db = I.bind_plan = I.fit_check = lambda *a: None
            I.summary = lambda *a, **k: None
            I.response_ids = lambda key, s: [("smollm3-3b", None)]
            I.run_empty = I.run_series = run_step
            self.assertEqual(I.run("smollm3-3b-off"), I.STOP)
            self.assertEqual(calls, [("smollm3-3b-off", "E1")])
            reason = json.loads((I.mdir("smollm3-3b-off") / "stopped.json").read_text())["reason"]
            self.assertEqual(reason, "E1: format check only: 7 of 200 answers invalid (3.5%); no series")
            self.assertEqual(I.public_reason(reason), reason)
            v = json.loads((I.mdir("smollm3-3b-off") / "validity.json").read_text())
            self.assertEqual((v["invalid"], v["fired"], v["check_only"]), (7, None, True))
            self.assertEqual(I.run("smollm3-3b-off"), I.STOP)  # stays stopped
            self.assertEqual(I.run("smollm3-3b-on", until="S1"), 0)  # (on) plays on
            self.assertEqual(calls[1:], [("smollm3-3b-on", "E1"), ("smollm3-3b-on", "S1")])
        finally:
            for n, f in saved.items():
                setattr(I, n, f)


class LFM25Off(unittest.TestCase):
    """Ümit's 23 Nov decision: the existing thinking-off league setup runs locally after Qwen3.5-2B."""

    KEY = "lfm2.5-24b-a2b-off"

    def test_it_uses_the_existing_off_setup_and_is_validity_gated(self):
        m = I.MODELS[self.KEY]
        self.assertEqual((m["lane"], m["expect"], m.get("billed")),
                         ("local", {"models": ["lfm2.5-24b-a2b"]}, None))
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == [self.KEY])
        self.assertEqual(amendment["gated"], [self.KEY])
        self.assertIn("immediately after Qwen3.5-2B", amendment["note"])
        s = I.league_settings("LFM2.5-24B-A2B (off)")
        self.assertEqual((s["spec"], s["base_url"], s["request"], s["max_tokens"], s["letter_readout"],
                          s["answer_prefix"]),
                         ("openai-compatible/lfm2.5-24b-a2b", "http://127.0.0.1:8898/v1", {}, 32000,
                          "prefill", "<think></think>Answer:"))


class SubscriptionSuccessors(unittest.TestCase):
    """Ümit #15926: current successors use the shared subscriptions before any new paid API route."""

    EXPECTED = {
        "gemini-4-neon-high": ("Gemini 4 Neon (high)", "antigravity-subscription",
                               "antigravity/gemini-4-neon", "high", None),
        "gpt-6.2-astra-high": ("GPT-6.2 Astra (high)", "chatgpt-subscription",
                               "openai/gpt-6.2-astra", "high", None),
        "gpt-6.2-sol-high": ("GPT-6.2 Sol (high)", "chatgpt-subscription",
                             "openai/gpt-6.2-sol", "high", None),
        "claude-fable-5.2-high": ("Claude Fable 5.2 (high)", "claude-subscription",
                                  "anthropic/claude-fable-5-2", "high", 32768),
    }

    def test_current_successors_use_the_preregistered_settings(self):
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == list(self.EXPECTED))
        self.assertIn("Claude Opus 5.5 is not rerun", amendment["note"])
        for key, (setup, provider, spec, reasoning, max_tokens) in self.EXPECTED.items():
            model = I.MODELS[key]
            settings = I.league_settings(setup)
            self.assertEqual(model["lane"], "subscription")
            self.assertEqual((settings["provider"], settings["spec"], settings["reasoning"],
                              settings.get("max_tokens"), settings["parallel"]),
                             (provider, spec, reasoning, max_tokens, 4))

    def test_carbon_uses_the_verified_antigravity_route_after_neon(self):
        key = "gemini-4-carbon-high"
        model = I.MODELS[key]
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == [key])
        self.assertIn("after Gemini 4 Neon", amendment["note"])
        self.assertEqual(model["expect"],
                         {"models": ["gemini-4-carbon"], "model_pointer": "/response/modelVersion"})
        settings = I.model_settings(key)
        self.assertEqual((settings["provider"], settings["spec"], settings["reasoning"], settings["parallel"]),
                         ("antigravity-subscription", "antigravity/gemini-4-carbon", "high", 4))

    def test_kimi_uses_the_verified_omp_subscription(self):
        key = "kimi-k3.1-pro-high"
        model = I.MODELS[key]
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == [key])
        self.assertIn("exact model identity k3.1-pro", amendment["note"])
        self.assertEqual(model["expect"], {"models": ["k3.1-pro"]})
        settings = I.model_settings(key)
        self.assertEqual(
            (model["lane"], settings["provider"], settings["spec"], settings["reasoning"],
             settings["request"], settings["parallel"]),
            ("subscription", "kimi-code-subscription", "kimi-code/k3.1-pro", "high",
             {"top_p": 0.95}, 4),
        )





class Qwen4Max(unittest.TestCase):
    """Ümit #16378/#16380/#16384: run Qwen4 Max High E1 alone, then report actual cost before S1."""

    def test_high_e1_uses_the_preregistered_alibaba_route(self):
        key = "qwen4-max-high"
        m = I.MODELS[key]
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == [key])
        self.assertIn("Stop after S1", amendment["note"])
        self.assertEqual((m["lane"], m["estimate"], m["S"], m["E"], m["price"], m["expect"]),
                         ("openrouter", 134.66, 17.88, 10.0, (1.425, 0.07125, 4.275),
                          {"models": ["qwen/qwen4-max", "qwen/qwen4-max-20261115"],
                           "provider": "Alibaba"}))
        settings = I.model_settings(key)
        self.assertEqual((settings["spec"], settings["provider"], settings["reasoning"], settings["parallel"]),
                         ("openai-compatible/qwen/qwen4-max", "openrouter:alibaba", "high", 4))
        self.assertEqual(settings["request"]["provider"],
                         {"order": ["alibaba"], "allow_fallbacks": False, "require_parameters": True})
        settings["reasoning"] = "changed"
        self.assertEqual(I.model_settings(key)["reasoning"], "high")
class Inkling(Isolated):
    """Ümit #13780/#13810/#13811: Inkling 2 Mini on logic's shared load, which the lane neither starts, stops nor
    claims; before every step (and when a step's requests fail) the server must be the pinned load, else a pause."""

    KEY = "inkling-2-mini-on"
    X = I.MODELS[KEY]["external"]
    ARGV = ["serve", X["repo"], "--revision", X["rev"], "--tokenizer-revision", X["rev"], "--served-model-name",
            "inkling-2-mini", "inkling-2-mini-tools", "--port", "18712", "--max-model-len", "65536",
            "--reasoning-parser", "inkling"]

    def setUp(self):
        super().setUp()
        self.receipt = Path(self.tmp.name) / "receipt.json"
        self.write_receipt()
        self.saved = dict(self.saved, MODELS=I.MODELS)
        I.MODELS = dict(I.MODELS, **{self.KEY: dict(I.MODELS[self.KEY], external=dict(self.X, receipt=str(self.receipt)))})
        I.write_atomic(I.mdir(self.KEY) / "base_url.txt", "http://127.0.0.1:18712/v1")

    def write_receipt(self, **kw):
        self.receipt.write_text(json.dumps(dict(dict(
            owner="@logic", reservation="r_x", repository=self.X["repo"], revision=self.X["rev"],
            image_id=self.X["image_id"], served_models=["inkling-2-mini", "inkling-2-mini-tools"], argv=self.ARGV), **kw)))

    def models(self, *cards):
        return lambda url: json.dumps(dict(data=list(cards)))

    CARD = dict(id="inkling-2-mini", root="thinkingmachines/Inkling-2-Mini", max_model_len=65536)

    def container(self, args=None, image=None, running=True):
        return lambda name: json.dumps([dict(Args=self.ARGV if args is None else args, Image=image or self.X["image_id"],
                                             State=dict(Running=running, StartedAt="2026-11-21T06:49:28Z"),
                                             Config=dict(Image="vllm/vllm-openai@sha256:c2dc"),
                                             HostConfig=dict(DeviceRequests=[dict(DeviceIDs=["0"])]))])

    def test_the_row_is_logics_load_greedy_at_effort_09_read_from_its_answer(self):
        m = self.saved["MODELS"][self.KEY]
        self.assertEqual((m["lane"], m["expect"], m.get("billed")), ("local", dict(models=["inkling-2-mini"]), None))
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == [self.KEY])
        self.assertIn("#13810", amendment["source"])
        s = I.league_settings("Inkling 2 Mini (on)")  # v3.db player 112
        self.assertEqual((s["spec"], s["base_url"], s["max_tokens"], s["letter_readout"], s["top_logprobs"]),
                         ("openai-compatible/inkling-2-mini", "http://127.0.0.1:18712/v1", 32768, "answer", 20))
        self.assertEqual(s["request"], {"chat_template_kwargs": {"reasoning_effort": 0.9}, "reasoning_effort": None,
                                        "temperature": 0, "seed": 0})
        self.assertFalse(set(s) & set(I.RUNNER_UNREAD))  # a prefill read-out cannot follow its reasoning block
        real = Path(m["external"]["receipt"])
        if real.exists():  # the owner's receipt names this very load
            r = json.loads(real.read_text())
            self.assertEqual((r["repository"], r["revision"], r["image_id"]), (m["external"]["repo"],
                             m["external"]["rev"], m["external"]["image_id"]))
            self.assertIn("inkling-2-mini", r["served_models"])
            self.assertEqual(r["argv"][r["argv"].index("--port") + 1], "18712")

    def test_effort_05_is_the_same_row_at_effort_05(self):
        """Ümit #14049/#14136: at 0.9 most E1 answers ran out of room; the rerun differs from 112 in its effort only."""
        on, e05 = self.saved["MODELS"][self.KEY], self.saved["MODELS"]["inkling-2-mini-e05"]
        self.assertEqual({k: v for k, v in e05.items() if k != "setup"}, {k: v for k, v in on.items() if k != "setup"})
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == ["inkling-2-mini-e05"])
        self.assertEqual(amendment["gated"], ["inkling-2-mini-e05"])
        self.assertNotRegex(amendment["note"], r"#\d")
        a, b = I.league_settings("Inkling 2 Mini (on)"), I.league_settings("Inkling 2 Mini (on, effort 0.5)")
        self.assertEqual(b["request"], dict(a["request"], chat_template_kwargs={"reasoning_effort": 0.5}))
        self.assertEqual((b["name"], b["reasoning"]), ("Inkling 2 Mini (on, effort 0.5)", "0.5"))
        same = lambda s: {k: v for k, v in s.items() if k not in ("name", "reasoning", "request", "note")}  # noqa: E731
        self.assertEqual(same(b), same(a))
        self.assertIn("effort 0.5 (chat_template_kwargs reasoning_effort 0.5", b["note"])

    def test_effort_02_is_the_first_retry_and_uses_learnings_compatible_load(self):
        """Ümit #15121/#15388: effort 0.2 is first; after Logic's load went away, Learning loaded one compatible copy."""
        on, e02 = self.saved["MODELS"][self.KEY], self.saved["MODELS"]["inkling-2-mini-e02"]
        self.assertEqual({k: v for k, v in e02.items() if k not in ("setup", "external")},
                         {k: v for k, v in on.items() if k not in ("setup", "external")})
        self.assertEqual(e02["external"], I.INKLING_2_MINI_E02_LOAD)
        self.assertEqual(e02["external"]["receipt"],
                         "/home/cbasaran/.cache/learn-inkling/admit-e02/inkling-2-mini-e02-receipt.json")
        amendment = next(a for a in I.AMENDMENTS if a.get("added") == ["inkling-2-mini-e02"])
        self.assertEqual(amendment["gated"], ["inkling-2-mini-e02"])
        self.assertNotRegex(amendment["note"], r"#\d")
        self.assertIn("Learning loaded one compatible copy", amendment["note"])
        a, b = I.league_settings("Inkling 2 Mini (on)"), I.league_settings("Inkling 2 Mini (on, effort 0.2)")
        self.assertEqual(b["request"], dict(a["request"], chat_template_kwargs={"reasoning_effort": 0.2}))
        self.assertEqual((b["name"], b["reasoning"]), ("Inkling 2 Mini (on, effort 0.2)", "0.2"))
        same = lambda s: {k: v for k, v in s.items() if k not in ("name", "reasoning", "request", "note")}  # noqa: E731
        self.assertEqual(same(b), same(a))
        self.assertIn("effort 0.2 (chat_template_kwargs reasoning_effort 0.2", b["note"])

    def test_the_server_must_be_the_receipts_pinned_load(self):
        self.assertEqual(I.external_state(self.KEY, self.models(self.CARD), self.container())[0], None)

        def down(url):
            raise OSError("connection refused")
        away = [(self.models(self.CARD), self.container(running=False)),
                (self.models(dict(self.CARD, id="inkling-2-mini-tools")), self.container()),
                (self.models(dict(self.CARD, max_model_len=32768)), self.container()),
                (self.models(dict(self.CARD, root="other/repo")), self.container()),
                (self.models(self.CARD), self.container(args=self.ARGV[:-1])),
                (self.models(self.CARD), self.container(image="sha256:other")),
                (self.models(self.CARD), lambda name: ""),
                (down, self.container())]
        for fetch, inspect in away:
            self.assertIsNotNone(I.external_state(self.KEY, fetch, inspect)[0])
        self.write_receipt(revision="main")
        self.assertIn("receipt", I.external_state(self.KEY, self.models(self.CARD), self.container())[0])
        self.write_receipt()
        I.external_gate(self.KEY, "E1", self.models(self.CARD), self.container())
        rec = json.loads((I.mdir(self.KEY) / "server.json").read_text())
        self.assertEqual((rec["server"], rec["args"], rec["gpus"]), ("external", self.ARGV, [dict(DeviceIDs=["0"])]))
        with self.assertRaises(I.Pause) as e:
            I.external_gate(self.KEY, "S2", down, self.container())
        self.assertTrue(str(e.exception).startswith("S2: waiting for a GPU: the shared server"), e.exception)
        self.assertEqual(I.progress_reason(str(e.exception)), I.GPU_WAIT_TEXT)
        self.assertRegex(I.public_reason(str(e.exception)), r"^[^<>&\x00-\x1f]{1,200}$")
        self.assertEqual([x["ok"] for x in I.events(self.KEY) if x["event"] == "external_server"], [True, False])
        I.external_gate("gemma-4-e4b-on", "E1", down, self.container())  # other models: no external server, no check

    def test_run_pauses_while_the_server_is_away_and_plays_when_it_is_back(self):
        names = ("check_inputs", "settings_check", "ensure_runner_db", "bind_plan", "fit_check", "run_empty",
                 "run_series", "summary", "response_ids", "external_state")
        saved = {n: getattr(I, n) for n in names}
        calls, state = [], ["down"]

        def run_step(key, s, gate):
            calls.append((key, s))
            I.write_atomic(I.step_dir(key, s) / "aggregate.json", json.dumps(dict(test=dict(invalid=3))))
        try:
            I.check_inputs = I.settings_check = I.ensure_runner_db = I.bind_plan = lambda *a: None
            I.fit_check = lambda key: calls.append((key, "fit"))
            I.summary = lambda *a, **k: None
            I.response_ids = lambda key, s: [("inkling-2-mini", None)]
            I.external_state = lambda key, *a: (("http://127.0.0.1:18712/v1 does not answer", {}) if state[0] == "down"
                                                else (None, dict(server="external")))
            I.run_empty = I.run_series = run_step
            self.assertEqual(I.run(self.KEY), I.PAUSE)
            self.assertEqual(calls, [])  # no fit check, no request
            reason = json.loads((I.mdir(self.KEY) / "paused.json").read_text())["reason"]
            self.assertTrue(reason.startswith("E1: waiting for a GPU"), reason)
            state[0] = "up"
            self.assertEqual(I.run(self.KEY, until="S1"), 0)
            self.assertEqual(calls, [(self.KEY, "fit"), (self.KEY, "E1"), (self.KEY, "S1")])
            self.assertEqual(json.loads((I.mdir(self.KEY) / "validity.json").read_text())["fired"], None)  # gated
        finally:
            for n, f in saved.items():
                setattr(I, n, f)

    def test_a_test_whose_server_goes_away_pauses_at_once(self):
        names = ("ask_watched", "test_metrics", "answer_error", "vllm_load", "player_config", "external_state")
        saved = {n: getattr(I, n) for n in names}
        asked = []
        try:
            I.ask_watched = lambda *a, **k: asked.append(1) or I.Asked(1, "", "connection refused", None)
            I.test_metrics = lambda key, name: dict(answered=200, failed=150)
            I.answer_error = lambda *a: None
            I.vllm_load = lambda key: None
            I.player_config = lambda *a, **k: {}
            I.external_state = lambda key, *a: ("http://127.0.0.1:18712/v1 does not answer", {})
            with self.assertRaises(I.Pause) as e:
                I.run_test(self.KEY, "E1", "Inkling 2 Mini (on) | improve | E1", "", I.step_dir(self.KEY, "E1"))
            self.assertEqual(len(asked), 1)  # no waiting rounds
            self.assertIn("E1: waiting for a GPU", str(e.exception))
        finally:
            for n, f in saved.items():
                setattr(I, n, f)


class ContextFit(Isolated):
    """Ümit #13462 item 3: the runner never cuts the note and vLLM refuses (never truncates) a prompt that does not
    fit, so each lesson call and note is measured on the model's server first; a misfit stops the model."""

    def setUp(self):
        super().setUp()
        self.saved = dict(self.saved, league_settings=I.league_settings)
        self.settings = {"SmolLM2-360M-Instruct": dict(spec="openai-compatible/smollm2-360m", max_tokens=1024,
                                                       request=dict(temperature=0)),
                         "SmolLM3-3B (on)": dict(spec="openai-compatible/smollm3-3b", reasoning="template default",
                                                 max_tokens=32768,
                                                 request=dict(chat_template_kwargs=dict(enable_thinking=True)))}
        I.league_settings = self.settings.__getitem__
        for key, port in (("smollm2-360m", 18707), ("smollm3-3b-on", 18710)):
            I.write_atomic(I.mdir(key) / "base_url.txt", f"http://127.0.0.1:{port}/v1")

    def server(self, count, ctx):
        self.bodies = []

        def fetch(url, body):
            self.bodies.append((url, body))
            return json.dumps(dict(count=count, max_model_len=ctx, tokens=[]))
        return fetch

    def test_a_lesson_call_must_leave_its_max_tokens(self):
        msgs = [dict(role="system", content="s"), dict(role="user", content="u")]
        self.assertIsNone(I.context_fit("smollm2-360m", "the lesson call after game 1", msgs, False,
                                        self.server(7168, 8192)))
        url, body = self.bodies[0]
        self.assertEqual((url, body["model"], body["add_generation_prompt"]),
                         ("http://127.0.0.1:18707/tokenize", "smollm2-360m", True))
        why = I.context_fit("smollm2-360m", "the lesson call after game 1", msgs, False, self.server(7169, 8192))
        self.assertEqual(why, "lessons don't fit: the lesson call after game 1: 7169 prompt tokens + 1024 for the "
                              "reply > max-model-len 8192")
        self.assertEqual(I.public_reason(f"S2: {why}"), "S2: lessons don't fit the model's context")  # not '529'
        self.assertEqual([e["fits"] for e in I.events("smollm2-360m") if e["event"] == "context_fit"], [True, False])

    def test_a_play_call_with_its_note(self):
        msgs = [dict(role="system", content="s"), dict(role="user", content="u")]
        # reasoning off: the read-out after the prefilled answer, 1 token, plus the position margin
        self.assertIsNone(I.context_fit("smollm2-360m", "note", msgs, True, self.server(8192 - 257, 8192)))
        self.assertEqual((self.bodies[0][1]["messages"][-1], self.bodies[0][1]["continue_final_message"]),
                         (dict(role="assistant", content="Answer:"), True))
        self.assertIsNotNone(I.context_fit("smollm2-360m", "note", msgs, True, self.server(8192 - 256, 8192)))
        # reasoning on: max_tokens and the read-out margin, the template's thinking switch sent along
        room = 65536 - 32768 - I.READOUT_MARGIN - I.POSITION_MARGIN
        self.assertIsNone(I.context_fit("smollm3-3b-on", "note", msgs, True, self.server(room, 65536)))
        self.assertEqual(self.bodies[0][1]["chat_template_kwargs"], dict(enable_thinking=True))
        self.assertIsNotNone(I.context_fit("smollm3-3b-on", "note", msgs, True, self.server(room + 1, 65536)))

        def down(url, body):
            raise OSError("no /tokenize")
        self.assertIsNone(I.context_fit("smollm3-3b-on", "note", msgs, True, down))  # unmeasured: logged, goes ahead
        self.assertEqual(I.events("smollm3-3b-on")[-1]["event"], "context_fit_unmeasured")

    def test_the_position_is_the_longest_stored_one_without_its_note(self):
        self.assertIsNone(I.position_messages("smollm2-360m"))
        I.SMOKE.mkdir(parents=True)
        db = sqlite3.connect(I.db_path("smollm2-360m"))
        for table in ("exchanges", "answer_exchanges"):
            db.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, request TEXT)")
        req = lambda user, note="": json.dumps(dict(messages=[  # noqa: E731
            dict(role="system", content="SYS" + (f"\n\n{I.OPEN}\n{note}\n{I.CLOSE}" if note else "")),
            dict(role="user", content=user)] + ([dict(role="assistant", content="x" * 500)] if note else [])))
        db.executemany("INSERT INTO answer_exchanges (request) VALUES (?)", [(req("a" * 10),), (req("b" * 20),)])
        db.executemany("INSERT INTO exchanges (request) VALUES (?)", [(req("c" * 30, "old lessons"),), (req("d"),)])
        db.commit()
        db.close()
        self.assertEqual(I.position_messages("smollm2-360m"),
                         [dict(role="system", content="SYS"), dict(role="user", content="c" * 30)])


if __name__ == "__main__":
    unittest.main()
