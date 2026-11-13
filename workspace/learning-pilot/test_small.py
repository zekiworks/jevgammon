"""Tests of the learning pilot for the small models (Ümit #6225): the model configs, context_fit.py, and the whole
protocol end to end against a stub OpenAI server (no model, no GPU) and in the pilot's dry run.

    python3 workspace/learning-pilot/test_small.py            # from the repo root; needs target/release/jevgammon,
                                                             # gnubg, tokenizers/transformers, test_set.json (private)

The end-to-end tests write only files of a throwaway key (stubtest-*: smoke/learning-pilot-stubtest-*.db,
runs-stubtest-*/, out-stubtest-*/) and remove them.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import context_fit as F  # noqa: E402

SMALL = ["lfm3-1.7b-on", "minicpm5-2b-on"]
# The player settings: late-smallchat-on a083fb4 (LFM3 repinned to logic's vLLM rerun with reasoning_field; MiniCPM5's
# reasoning_prefill from 7170908, unchanged there)
PLAYER_SOURCE = {"lfm3-1.7b-on": "a083fb4", "minicpm5-2b-on": "a083fb4"}
MAIN = Path("/home/cbasaran/code/jevgammon")
RUNNER = Path("/home/cbasaran/.cache/jevgammon-wt/target-small-learning-runner/jevgammon-b01eca2")
DECISION = ["d1-2b", "glide-2b", "glide-0.8b", "knowline-4b", "knowline-2b", "knowline-0.8b", "startlux-2b",
            "startlux-0.8b", "onejev1.6-0.8b", "gliclass-v4-edge", "decider-flash-v1.2"]
# tools/v3/late-tiny8/stub_server.py kind per decision config (Decider Flash: startlux, no model rule)
KIND = {"d1-2b": "d1", "glide-2b": "glide", "glide-0.8b": "glide", "knowline-4b": "knowline", "knowline-2b": "knowline",
        "knowline-0.8b": "knowline", "startlux-2b": "startlux", "startlux-0.8b": "startlux", "onejev1.6-0.8b": "onejev",
        "gliclass-v4-edge": "gliclass", "decider-flash-v1.2": "startlux"}
SCRATCH = Path.home() / ".cache/jevgammon-wt/small-learning-tmp"  # never /tmp
SCRATCH.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(SCRATCH)


def pilot(config, **env):
    """pilot.py's module namespace for a config, without running its main()."""
    src = (HERE / "pilot.py").read_text().rstrip()
    assert src.endswith("\nmain()")
    old = dict(os.environ)
    os.environ.update(PILOT_CONFIG=str(config), **env)
    try:
        ns = {"__file__": str(HERE / "pilot.py"), "__name__": "pilot_under_test"}
        exec(compile(src[:-len("main()")], str(HERE / "pilot.py"), "exec"), ns)
        return ns
    finally:
        os.environ.clear()
        os.environ.update(old)


# --- Configs -----------------------------------------------------------------------------------------------------

def test_gemma_unchanged():
    p = pilot("configs/base.json")
    assert p["NOTE_BUDGET"] == 26879 and p["CONTEXT_LIMIT"] == 32768 and p["PROMPT_MAX"] == 4389
    assert p["DB"] == ROOT / "smoke/learning-pilot.db" and p["RUNS"] == HERE / "runs" and p["OUTPUTS"] == HERE / "out"
    assert p["T0_NAME"] == "Gemma 4 31B (off) | T0 shared" and p["player_name"]("records", 5) == \
        "Gemma 4 31B (off) | records | s05"
    assert p["MODEL"] == "gemma-4-31B-it" and p["LESSONS_MAX_TOKENS"] == 400
    assert p["LESSONS_REQUEST"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert p["BIN"] == ROOT.parent / "jevgammon-learning-pilot/target/release/jevgammon"
    assert p["TOKENIZER"] == "/home/cbasaran/code/models/gemma-4-31B-it/tokenizer.json"
    assert set(p["BASE"]) <= set(p["RUNNER_FIELDS"])  # run_eval's config for Gemma stays the whole base.json
    assert "model" not in p["protocol"]()
    assert pilot("configs/base.json", PILOT_DRY="1")["DB"] == ROOT / "smoke/learning-pilot-dry.db"


def test_small_configs():
    for key in SMALL:
        cfg = json.loads((HERE / f"configs/{key}.json").read_text())
        p = pilot(f"configs/{key}.json")
        assert p["KEY"] == key and p["DB"] == ROOT / f"smoke/learning-pilot-{key}.db"
        assert p["RUNS"] == HERE / f"runs-{key}" and p["OUTPUTS"] == HERE / f"out-{key}"
        assert p["NOTE_BUDGET"] == 69632 - 32768 - cfg["prompt_max"] - 1500
        assert p["MODEL"] == cfg["players"][0]["spec"].split("/", 1)[1]
        assert p["LESSONS_REQUEST"] == {"chat_template_kwargs": cfg["players"][0]["request"]["chat_template_kwargs"]}
        assert p["LESSONS_REQUEST"] == {"chat_template_kwargs": {"enable_thinking": True}}
        assert p["LESSONS_MAX_TOKENS"] == cfg["players"][0]["max_tokens"] == 32768
        assert Path(p["TOKENIZER"]).exists()
        assert p["BIN"] == RUNNER
        assert p["T0_NAME"] == f"{cfg['players'][0]['name']} | T0 shared"
        assert p["ORDER_SEED"] == pilot("configs/base.json")["ORDER_SEED"]
        assert p["TEST_SET_SHA256"] == "6c92e7416745125ca3ea09c9e41e450a52716f8ad018772278b07f992f7318e6"
        # the player is the late entry's, byte for byte as JSON
        own = subprocess.run(["git", "-C", str(MAIN), "show",
                              f"{PLAYER_SOURCE[key]}:tools/v3/late-smallchat/models/{key}/player.json"],
                             capture_output=True, text=True, check=True).stdout
        assert cfg["players"][0] == json.loads(own)
    assert "reasoning_prefill" in json.loads((HERE / "configs/minicpm5-2b-on.json").read_text())["players"][0]


def test_decision_configs():
    v3 = sqlite3.connect("file:/home/cbasaran/code/jevgammon/v3.db?mode=ro", uri=True)
    fit = {m["key"]: m for m in json.loads((HERE / "context_fit_decision.json").read_text())["models"]}
    for key in DECISION:
        cfg = json.loads((HERE / f"configs/{key}.json").read_text())
        p = pilot(f"configs/{key}.json")
        assert p["ARMS"] == ["control", "records"] and p["BIN"] == RUNNER and RUNNER.exists()
        assert p["NOTE_BUDGET"] == cfg["context_limit"] - cfg["prompt_max"] - 1500 > 0
        assert Path(p["TOKENIZER"]).exists() and fit[key]["verdict"] in ("fit", "partial")
        player = dict(cfg["players"][0])
        assert player.pop("context_gate") == {"kind": "server_invalid"}
        row = v3.execute("SELECT settings FROM players WHERE name = ?", (F.DECISION[[m["key"] for m in F.DECISION]
                                                                                 .index(key)]["setup"],)).fetchone()
        if row:  # a league setup: its frozen settings, unchanged
            assert player == json.loads(row[0]), key
    skipped = json.loads((HERE / "configs/decision_skipped.json").read_text())["skipped"]
    assert sorted(s["key"] for s in skipped) == ["glide-0.4b", "metask", "strands"]
    assert not any((HERE / f"configs/{s['key']}.json").exists() for s in skipped)


# --- context_fit -------------------------------------------------------------------------------------------------

def records_fixture(tmp):
    """A records-arm context of two games in the pilot's own format (records_text), and the single-game texts."""
    p = pilot("configs/base.json")
    lines = {1: ["- Turn 1, dice 3-1; a. You played 8/5 6/5.", "- Turn 3, dice 6-6; b. You played x."],
             2: ["- Turn 2, dice 2-1; c. You played 13/11 6/5."]}
    results = {1: dict(won=True, result="single", points=1), 2: dict(won=False, result="gammon", points=2)}
    d = Path(tmp) / "records/s01/contexts"
    d.mkdir(parents=True)
    (d / "after-g02.txt").write_text(p["records_text"](lines, results))
    (d / "after-g01.txt").write_text(p["records_text"]({1: lines[1]}, results))
    return {g: p["records_text"]({g: lines[g]}, results) for g in lines}


def test_game_records():
    with tempfile.TemporaryDirectory() as tmp:
        single = records_fixture(tmp)
        F.RECORDS = Path(tmp) / "records"
        got = F.game_records()
        assert sorted(got.values()) == sorted(single.values()) and len(got) == 2
        pick = F.largest_and_median(got)
        assert pick["largest"][1] == single[1] and pick["median"][1] == single[2]


def test_block_placement_and_plain_text():
    body = {"state": "S", "questions": {"play": {"type": "choice", "instructions": "I",
                                                 "criteria": {"8/5": "8/5: d1", "6/5": "6/5: d2"}}}}
    assert F.with_block(body, "B\n")["state"] == "B\n\nS"  # decision.rs state_with_block: trim_end + blank line
    assert F.with_block(body, "")["state"] == "S"
    assert F.plain_text(body) == "S\n\nI\n8/5: 8/5: d1\n6/5: 6/5: d2"
    assert F.plain_text(body, "description") == "S\n\nI\n8/5: d1\n6/5: d2"


def test_decision_verdicts():
    words = lambda path, text, special=False: len(text.split())  # noqa: E731
    old = F.count
    F.count = words
    try:
        req = lambda n: dict(exchange=1, bytes=n, body={"state": " ".join(["s"] * n), "questions": {}})  # noqa: E731
        records = dict(median=(("s01", "g"), " ".join(["r"] * 10)), largest=(("s01", "h"), " ".join(["r"] * 30)))
        base = dict(key="k", name="K", source="r@1", tok="t", method="plain", limit_basis="b")
        fit = F.decision_fit(dict(base, limit=100), records, dict(largest=req(60), median=req(20)))
        assert fit["verdict"] == "fit" and fit["tokens"]["largest+largest"] == 90
        assert fit["block_tokens"]["median"] == 10
        part = F.decision_fit(dict(base, limit=80), records, dict(largest=req(60), median=req(20)))
        assert part["verdict"] == "partial" and "refused" in part["why"]
        cut = F.decision_fit(dict(base, limit=80, capped=True), records, dict(largest=req(60), median=req(20)))
        assert cut["verdict"] == "skip" and "cut" in cut["why"]
        skip = F.decision_fit(dict(base, limit=25), records, dict(largest=req(60), median=req(20)))
        assert skip["verdict"] == "skip"
        twice = F.decision_fit(dict(base, limit=100, twice=3000), records, dict(largest=req(60), median=req(20)))
        assert "read once" in twice["notes"][0]
    finally:
        F.count = old


def test_chat_fit_counts_with_own_tokenizer():
    cfg = json.loads((HERE / "configs/lfm3-1.7b-on.json").read_text()) | dict(path="lfm3-1.7b-on.json")
    msgs = lambda n: [{"role": "system", "content": "x " * n}, {"role": "user", "content": "u"}]  # noqa: E731
    out = F.chat_fit(cfg, requests=[("t0", 1, "T0", msgs(10)), ("game", 2, "records", msgs(1000))], contexts=[])
    assert out["prompt_max_t0"]["id"] == 1 and out["longest_stored_request"]["id"] == 2
    assert out["longest_needs"] == out["longest_stored_request"]["tokens"] + 32768 and out["longest_fits"]
    assert out["note_budget"] == 69632 - 32768 - out["prompt_max_t0"]["tokens"] - 1500
    snap = Path(cfg["tokenizer_file"]).parent
    text = F.render_chat(snap, msgs(10), {"enable_thinking": True})
    assert text.endswith("<|im_start|>assistant\n<think>")  # LFM3's template opens the reasoning


# --- End to end: stub OpenAI server --------------------------------------------------------------------------

class Stub(BaseHTTPRequestHandler):
    """chat/completions for the runner's (on) readout and the lesson call: a reasoning request (response_format) gets
    reasoning + a constrained letter; a prefill request (continue_final_message) gets the top-20 letter logprobs; any
    other request (the lesson call) gets reasoning + five lessons."""
    seen = []
    lock = threading.Lock()

    def do_GET(self):  # noqa: N802
        self.reply({"object": "list", "data": [{"id": self.server.served}]})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.lock:
            self.seen.append(body)
        if body.get("model") != self.server.served:
            return self.reply({"error": {"message": "unknown model"}}, 404)
        if body.get("continue_final_message"):
            # vLLM's rule (transformers): the prefilled final message must appear verbatim in the rendered prompt
            if self.server.template and body["messages"][-1]["content"] not in self.server.render(body["messages"]):
                return self.reply({"error": {"message": "continue_final_message is set but the final message does "
                                             "not appear in the chat after applying the chat template!"}}, 400)
            top = [{"token": c, "logprob": -0.1 - i} for i, c in enumerate("ABCDEFGHIJKLMNOPQRST")]
            msg = {"role": "assistant", "content": "A"}
            choice = {"message": msg, "finish_reason": "length",
                      "logprobs": {"content": [{"token": "A", "logprob": -0.1, "top_logprobs": top}]}}
        elif "response_format" in body:
            msg = {"role": "assistant", "content": '{"choice": "A"}', "reasoning_content": "\nstub reasoning\n"}
            choice = {"message": msg, "finish_reason": "stop"}
        else:
            lessons = "\n".join(f"- stub lesson {k}: keep the blots safe" for k in range(1, 6))
            msg = {"role": "assistant", "content": lessons, "reasoning_content": "stub reasoning"}
            choice = {"message": msg, "finish_reason": "stop"}
        self.reply({"id": "x", "model": self.server.served, "choices": [dict(choice, index=0)],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3}})

    def reply(self, obj, status=200):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def throwaway(key, tmp, url):
    cfg = json.loads((HERE / f"configs/{key}.json").read_text())
    cfg["key"] = f"stubtest-{key}"
    cfg["players"][0]["base_url"] = url
    path = Path(tmp) / f"{cfg['key']}.json"
    path.write_text(json.dumps(cfg))
    return path, cfg


def clean(key):
    for p in [ROOT / f"smoke/learning-pilot{s}" for s in (f"-{key}.db", f"-plays-{key}.db", f"-{key}-dry.db",
                                                         f"-plays-{key}-dry.db")]:
        for q in (p, Path(f"{p}-wal"), Path(f"{p}-shm")):
            q.unlink(missing_ok=True)
    for d in (f"runs-{key}", f"out-{key}", f"runs-{key}-dry", f"out-{key}-dry"):
        shutil.rmtree(HERE / d, ignore_errors=True)


def run_pilot(config, *args, **env):
    r = subprocess.run([sys.executable, str(HERE / "pilot.py"), *args], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, PILOT_CONFIG=str(config), **env), timeout=3600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-3000:]
    return r


def render_final(snapshot):
    """The prompt as transformers renders a conversation whose last (assistant) message is continued."""
    from transformers.utils.chat_template_utils import render_jinja_template
    tc = json.loads((snapshot / "tokenizer_config.json").read_text())
    tpl = (snapshot / "chat_template.jinja").read_text()

    def render(messages):
        # vLLM hands a message's `reasoning` to the template as both `reasoning` and `reasoning_content`
        messages = [dict(m, reasoning_content=m["reasoning"]) if "reasoning" in m else m for m in messages]
        out, _ = render_jinja_template(conversations=[messages], chat_template=tpl, add_generation_prompt=False,
                                       bos_token=tc.get("bos_token") or "", eos_token=tc.get("eos_token"),
                                       enable_thinking=True)
        return out[0]
    return render


def test_template_rule_of_the_stub():
    """The stub refuses MiniCPM5's old (on) prefill and accepts the reasoning_prefill layout, as vLLM did/does."""
    cfg = json.loads((HERE / "configs/minicpm5-2b-on.json").read_text())
    render = render_final(Path(cfg["tokenizer_file"]).parent)
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    old = "<think>\nstub reasoning\n</think>Answer:"
    new = cfg["players"][0]["reasoning_prefill"].replace("{reasoning}", "stub reasoning")
    assert old not in render(msgs + [{"role": "assistant", "content": old}])
    assert new in render(msgs + [{"role": "assistant", "content": new}])


def chat_end_to_end(key):
    cfg0 = json.loads((HERE / f"configs/{key}.json").read_text())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    server.served = cfg0["served_model"]
    server.template = True
    server.render = render_final(Path(cfg0["tokenizer_file"]).parent)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    Stub.seen.clear()
    with tempfile.TemporaryDirectory() as tmp:
        config, cfg = throwaway(key, tmp, f"http://127.0.0.1:{server.server_address[1]}/v1")
        clean(cfg["key"])
        try:
            run_pilot(config, "t0")
            run_pilot(config, "run", "--series", "1-1")
            p = pilot(config)
            out = json.loads((p["OUTPUTS"] / "learning-pilot.json").read_text())
            assert out["series_finished"] == {arm: [1] for arm in p["ARMS"]}, out["series_finished"]
            assert out["t0_done"] and out["protocol"]["model"] == cfg0["players"][0]["name"]
            assert out["protocol"]["note_budget"] == p["NOTE_BUDGET"]
            t0 = json.loads((p["RUNS"] / "t0/aggregate.json").read_text())["metrics"]
            assert t0["answered"] == 200 and t0["invalid"] == 0 and t0["failed"] == 0
            db = sqlite3.connect(f"file:{p['DB']}?mode=ro", uri=True)
            src = {r[0] for r in db.execute("SELECT DISTINCT probability_source FROM answers")}
            setups = {r[0] for r in db.execute("SELECT DISTINCT setup FROM answers")}
            db.close()
            assert src == {"logprobs"} and f"{p['LABEL']} | lessons | s01 | T10" in setups
            for arm in ("records", "lessons", "budget"):
                a = json.loads((p["RUNS"] / arm / "s01/aggregate.json").read_text())
                assert all(a["evaluations"][t]["answered"] == 200 and a["evaluations"][t]["invalid"] == 0
                           for t in ("T5", "T10"))
            les = json.loads((p["RUNS"] / "lessons/s01/aggregate.json").read_text())
            assert len(les["lessons_calls"]) == 10 and not any(c["cut"] for c in les["lessons_calls"])
            assert (p["RUNS"] / "lessons/s01/lessons-g01.txt").read_text().startswith("- stub lesson 1")
            rec = json.loads((p["RUNS"] / "records/s01/aggregate.json").read_text())
            assert rec["context_tokens_after_game"]["9"] > 0
            # requests: the served name; the (on) readout's reasoning request carries the late entry's switches and
            # 32,768 output tokens; the lesson call is the model's (on) request with its output limit, never Gemma's
            reasoning = [b for b in Stub.seen if "response_format" in b]
            lesson = [b for b in Stub.seen if "response_format" not in b and not b.get("continue_final_message")]
            assert {b["model"] for b in Stub.seen} == {server.served}
            assert all(b["max_tokens"] == 32768 and b["chat_template_kwargs"] == {"enable_thinking": True}
                       for b in reasoning)
            assert len(lesson) == 10 and all(b["max_tokens"] == 32768 and b["temperature"] == 1.0 and
                                             b["chat_template_kwargs"] == {"enable_thinking": True} for b in lesson)
            # the records arm's notes reach the system prompt once a game is played
            noted = [b for b in reasoning if p["OPEN"] in b["messages"][0]["content"]]
            assert noted and all(p["CLOSE"] in b["messages"][0]["content"] for b in noted)
            finals = [b["messages"][-1] for b in Stub.seen if b.get("continue_final_message")]
            player = cfg0["players"][0]
            if player.get("reasoning_field"):  # LFM3 under vLLM: Answer: as content, the reasoning in its field
                want = {"role": "assistant", "content": "Answer:", player["reasoning_field"]: "\nstub reasoning\n"}
            else:
                layout = player.get("reasoning_prefill")
                want = {"role": "assistant", "content": layout.replace("{reasoning}", "stub reasoning") if layout
                        else "<think>\nstub reasoning\n</think>Answer:"}
            assert finals and all(m == want for m in finals), finals[:1]
        finally:
            server.shutdown()
            clean(cfg["key"])


def test_end_to_end_stub_lfm3():
    chat_end_to_end("lfm3-1.7b-on")


def test_end_to_end_stub_minicpm5():
    chat_end_to_end("minicpm5-2b-on")


def stub_server(kind, port):
    """tools/v3/late-tiny8/stub_server.py as on late-tiny8-small3 8ebad40, from git (read-only)."""
    src = subprocess.run(["git", "-C", str(MAIN), "show", "8ebad40:tools/v3/late-tiny8/stub_server.py"],
                         capture_output=True, text=True, check=True).stdout
    path = SCRATCH / "stub_server.py"
    path.write_text(src)
    return subprocess.Popen([sys.executable, str(path), kind, str(port)])


def free_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def decision_end_to_end(key):
    import time
    import urllib.request
    port = free_port()
    proc = stub_server(KIND[key], port)
    with tempfile.TemporaryDirectory() as tmp:
        config, cfg = throwaway(key, tmp, f"http://127.0.0.1:{port}")
        clean(cfg["key"])
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/stats", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.1)
            run_pilot(config, "t0")
            run_pilot(config, "run", "--series", "1-1")
            p = pilot(config)
            out = json.loads((p["OUTPUTS"] / "learning-pilot.json").read_text())
            assert out["series_finished"] == {"control": [1], "records": [1]}, out["series_finished"]
            t0 = json.loads((p["RUNS"] / "t0/aggregate.json").read_text())["metrics"]
            assert t0["answered"] == 200 and t0["invalid"] == 0 and t0["failed"] == 0
            rec = json.loads((p["RUNS"] / "records/s01/aggregate.json").read_text())
            assert all(rec["evaluations"][t]["answered"] == 200 for t in ("T5", "T10"))
            assert rec["context_tokens_after_game"]["9"] > 0
            db = sqlite3.connect(f"file:{p['DB']}?mode=ro", uri=True)
            states = [json.loads(r[0])["state"] for r in db.execute(
                "SELECT ae.request FROM answer_exchanges ae JOIN answers a ON a.id = ae.answer_id "
                "WHERE a.setup LIKE '% | records | s01 | T10'")]
            plain = [json.loads(r[0])["state"] for r in db.execute(
                "SELECT ae.request FROM answer_exchanges ae JOIN answers a ON a.id = ae.answer_id "
                "WHERE a.setup LIKE '% | T0 shared'")]
            db.close()
            note = (p["RUNS"] / "records/s01/contexts/after-g10.txt").read_text()
            # the records block at the start of state + a blank line (decision.rs state_with_block); T0 has none
            assert states and all(s.startswith(note.rstrip() + "\n\n") for s in states)
            assert plain and not any(s.startswith(p["OPEN"]) for s in plain)
            return rec["context_tokens_after_game"]
        finally:
            proc.terminate()
            clean(cfg["key"])


def test_decision_end_to_end_stub():
    for key in os.environ.get("DECISION_KEYS", ",".join(DECISION)).split(","):
        ctx = decision_end_to_end(key)
        print(f"  {key}: records context tokens after game 10 = {ctx['10']}", flush=True)


def test_dry_run():
    """The pilot's own dry run (PILOT_DRY=1: Safest in the model's seat, no call) with a small model's config."""
    key = "minicpm5-2b-on"
    with tempfile.TemporaryDirectory() as tmp:
        config, cfg = throwaway(key, tmp, "http://127.0.0.1:9/v1")
        clean(cfg["key"])
        try:
            run_pilot(config, "t0", PILOT_DRY="1")
            run_pilot(config, "run", "--series", "1-1", PILOT_DRY="1")
            p = pilot(config, PILOT_DRY="1")
            assert p["RUNS"] == HERE / f"runs-{cfg['key']}-dry"
            out = json.loads((p["OUTPUTS"] / "learning-pilot.json").read_text())
            # dry: evaluations are skipped, so only the control series counts as finished (pilot.series_finished)
            assert out["series_done"] == {arm: 1 for arm in p["ARMS"]} and out["protocol"]["dry_run"]
            assert out["series_finished"] == dict(control=[1], records=[], lessons=[], budget=[])
            budget = json.loads((p["RUNS"] / "budget/s01/aggregate.json").read_text())
            assert len(budget["budget_points"]) == 10
        finally:
            clean(cfg["key"])


def test_run_small_refuses():
    """run_small.sh never starts a server: an unknown key, or a server that does not answer with the served name,
    stops it before pilot.py runs."""
    sh = HERE / "run_small.sh"
    r = subprocess.run([str(sh), "no-such-model", "1-1"], capture_output=True, text=True)
    assert r.returncode == 1 and "no config" in r.stderr
    with tempfile.TemporaryDirectory() as tmp:
        _, cfg = throwaway("lfm3-1.7b-on", tmp, "http://127.0.0.1:9/v1")  # nothing listens on port 9
        path = HERE / f"configs/{cfg['key']}.json"
        path.write_text(json.dumps(cfg))
        try:
            r = subprocess.run([str(sh), cfg["key"], "1-1"], capture_output=True, text=True)
            assert r.returncode == 1 and "does not serve lfm3-1.7b" in r.stderr and "start" not in r.stdout
            assert not (HERE / f"runs-{cfg['key']}").exists()
        finally:
            path.unlink()


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    only = sys.argv[1:]
    for t in tests:
        if only and t.__name__ not in only:
            continue
        t()
        print(f"ok {t.__name__}", flush=True)
    print(f"{len(only) or len(tests)} passed")
