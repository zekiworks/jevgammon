"""Dry runs of Clear-risk Part 2 for the small models against stub servers (no GPU, no model, no paid call):

    BIN=~/.cache/clearrisk-small/target/release/jevgammon python3 tools/v3/clearrisk-small/test_crp2.py

- items: items_q1q2.jsonl is byte-identical to the Q1/Q2 lines of both Part 2 item files (189 + 189 + 60).
- frozen scoring: crp2.score() gives p2rep.json's Q1/Q2 counts for the 8 Part 2 models (smoke/clearrisk-q.db, read-only).
- prompt identity: this branch's runner, given Part 2's config (smoke/clearrisk-config.json; base_url to stubs, budget
  ledger and rpm pacing dropped), sends byte-for-byte the requests stored for Celeris-1 Decision, Jev 1.14.0, Liquid
  d1-ultra, Kimi K3.1 Pro (off) and GLM-5.3 (on) on all 438 Q1/Q2 items.
- every runnable small model, through run.sh at its pinned league settings against its stub kind (late-tiny8's
  stub_server.py @ a72223d; stub_chat.py): 438 answer rows, none failed, one request per question; decision requests
  equal Celeris's stored request but for the model field; chat requests carry the item's system/user (= Kimi's stored
  messages), the item's schema (= GLM's stored response_format), the player's switches; a rerun asks nothing; --smoke
  asks one question; the blocked models have no config; run.sh refuses without a server.
- invalid share: a chat stub answering prose every 7th request gives 62 invalid answers in crp2.score().
Scratch: ~/.cache/clearrisk-small/test (wiped first). Production files are only read.
"""
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crp2  # noqa: E402

MAIN = Path(os.environ.get("CRP2_MAIN", "/home/cbasaran/code/jevgammon"))
PART2_DB = MAIN / "smoke" / "clearrisk-q.db"
PART2_CONFIG = MAIN / "smoke" / "clearrisk-config.json"
SCRATCH = MAIN / "workspace" / "clearrisk-scratch"
BIN = os.environ.get("BIN", str(Path.home() / ".cache/clearrisk-small/target/release/jevgammon"))
TMP = Path.home() / ".cache" / "clearrisk-small" / "test"
STUB_COMMIT = "a72223d0ee08b1f4020ece622c89a70dca6065d3"
IDENTITY = ["Celeris-1 Decision", "Jev 1.14.0", "Liquid d1-ultra", "Kimi K3.1 Pro (off)", "GLM-5.3 (on)"]
EXPECTED_MODEL = {"knowline": "m", "onejev": "OmniJev/OneJev1.6-0.8B", "gliclass": "knowledgator/gliclass-v4-edge",
                  "startlux": None, "glide": None, "glide-0.4b": None}
ITEMS = crp2.items()
PROCS = []


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def stub(kind_or_model, chat=False, invalid=0):
    port = free_port()
    args = [HERE / "stub_chat.py", kind_or_model, port, invalid] if chat else [TMP / "stub_server.py", kind_or_model, port]
    p = subprocess.Popen([sys.executable, *map(str, args)])
    PROCS.append(p)
    for _ in range(200):
        try:
            socket.create_connection(("127.0.0.1", port), 0.1).close()
            return p, port
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"stub {args} did not start")


def exchanges(db, setup):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    n = c.execute("SELECT COUNT(*) FROM quiz_exchanges e JOIN quiz_answers a ON a.id = e.answer_id WHERE a.setup = ?",
                  (setup,)).fetchone()[0]
    c.close()
    return n


def health(port):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5))


def requests(db, setup):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute("SELECT a.item_id, e.request, a.choice, a.text, a.error FROM quiz_answers a JOIN quiz_exchanges e "
                     "ON e.answer_id = a.id WHERE a.setup = ? AND e.attempt = 1 AND a.item_id NOT LIKE '%:Q3:%'",
                     (setup,)).fetchall()
    c.close()
    return {r[0]: r[1:] for r in rows}


def run_sh(key, base_url, out, *extra, check=True):
    env = dict(os.environ, BIN=BIN, OUT=str(out), CRP2_CACHE=str(TMP / "cache"), CRP2_BASE_URL=base_url)
    r = subprocess.run(["bash", str(HERE / "run.sh"), key, *extra], env=env, capture_output=True, text=True)
    if check:
        assert r.returncode == 0, (key, r.stdout[-2000:], r.stderr[-2000:])
    return r


def test_items():
    crp2.check_items(SCRATCH)


def test_frozen_scoring_reproduces_part2():
    R, _ = crp2.score(PART2_DB, sorted(crp2.PART2_CHAT | {"Celeris-1 Decision", "Jev 1.14.0", "Liquid d1-ultra"}))
    frozen = json.loads((SCRATCH / "p2rep.json").read_text())
    checked = 0
    for (model, version), r in R.items():
        want = {k: v for k, v in frozen[f"{model}|{version}"].items() if k.startswith(("q1_", "q2_"))}
        got = {k: v for k, v in r.items() if v or k in want}
        assert got == want, (model, version, got, want)
        checked += 1
    assert checked == 16


def test_prompt_identity_with_part2_requests():
    config = json.loads(PART2_CONFIG.read_text())
    _, dport = stub("glide")
    _, cport = stub("*", chat=True)
    players = []
    for p in config["players"]:
        if p["name"] in IDENTITY:
            p = dict(p)
            chat = p["spec"].startswith("openai-compatible/")
            p["base_url"] = f"http://127.0.0.1:{cport}/v1" if chat else f"http://127.0.0.1:{dport}"
            p.pop("budget", None)
            p.pop("rpm", None)
            players.append(p)
    assert len(players) == len(IDENTITY)
    cfg = TMP / "identity.json"
    cfg.write_text(json.dumps({"players": players}))
    out = TMP / "identity.db"
    env = dict(os.environ, **{k: "stub" for k in ("CELERIS_API_KEY", "TYPESAFE_API_KEY", "LIQUID_API_KEY",
                                                  "OPENROUTER_API_KEY")})
    r = subprocess.run([BIN, "quiz", "--config", cfg, "--items", crp2.ITEMS, "--out", out, "--time-limit", "60"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    same = 0
    for setup in IDENTITY:
        new, old = requests(out, setup), requests(PART2_DB, setup)
        assert len(new) == len(old) == 438, (setup, len(new), len(old))
        for item_id, (request, *_rest) in new.items():
            assert request == old[item_id][0], (setup, item_id)
            same += 1
    assert same == 5 * 438
    print(f"prompt identity: {same} requests byte-identical to Part 2's stored requests")


def test_small_models_dry_run():
    out = TMP / "small.db"
    celeris = {k: json.loads(v[0]) for k, v in requests(PART2_DB, "Celeris-1 Decision").items()}
    kimi = {k: json.loads(v[0]) for k, v in requests(PART2_DB, "Kimi K3.1 Pro (off)").items()}
    glm = {k: json.loads(v[0]) for k, v in requests(PART2_DB, "GLM-5.3 (on)").items()}
    by_id = {i["id"]: i for i in ITEMS}
    runnable = {k: m for k, m in crp2.models().items() if "blocked" not in m}
    assert len(runnable) == 12
    for key, m in runnable.items():
        p = crp2.player(key)
        if m["kind"] == "decision":
            _, port = stub(m["stub"])
            run_sh(key, f"http://127.0.0.1:{port}", out)
            # One request per question, no split (gliclass_server.py has no GET route, so its stub has no /health).
            assert exchanges(out, p["name"]) == 438, key
            if m["stub"] != "gliclass":
                assert health(port)["requests"] == 438, key
            provider = p["spec"].split("/")[0]
            for item_id, (request, choice, text, error) in requests(out, p["name"]).items():
                body, want = json.loads(request), dict(celeris[item_id])
                assert body.pop("model", None) == EXPECTED_MODEL[provider], (key, item_id)
                want.pop("model")
                assert body == want and json.dumps(body, ensure_ascii=False) == json.dumps(want, ensure_ascii=False)
                assert error is None and choice == by_id[item_id]["options"][0][0], (key, item_id)
        else:
            served = p["spec"].split("/", 1)[1]
            _, port = stub(served, chat=True, invalid=7 if key == "minicpm5-2b-on" else 0)
            run_sh(key, f"http://127.0.0.1:{port}/v1", out)
            assert health(port)["requests"] == 438, key
            for item_id, (request, choice, text, error) in requests(out, p["name"]).items():
                body, item = json.loads(request), by_id[item_id]
                assert body["model"] == served and error is None
                assert body["messages"] == [{"role": "system", "content": item["system"]},
                                            {"role": "user", "content": item["user"]}] == kimi[item_id]["messages"]
                assert body["response_format"] == {"type": "json_schema", "json_schema": {
                    "name": item["schema_name"], "schema": item["schema"], "strict": True}} == glm[item_id]["response_format"]
                assert body["chat_template_kwargs"] == {"enable_thinking": True} and "reasoning_effort" not in body
                assert body["temperature"] == 1.0 and body["max_tokens"] == 32768
        rows = requests(out, p["name"])
        assert len(rows) == 438 and not any(r[3] for r in rows.values()), key
    # A rerun asks nothing (every item answered); --smoke asks one question into its own DB.
    key = "glide-0.4b"
    _, port = stub("glide-0.4b")
    r = run_sh(key, f"http://127.0.0.1:{port}", out)
    assert " 0 asked, 0 failed" in r.stdout and health(port)["requests"] == 0, r.stdout
    r = run_sh(key, f"http://127.0.0.1:{port}", out, "--smoke")
    assert health(port)["requests"] == 1 and "1 answer rows" in r.stdout, r.stdout
    # No server: refused before any question.
    r = run_sh("knowline-2b", f"http://127.0.0.1:{free_port()}", TMP / "none.db", check=False)
    assert r.returncode == 1 and "no server" in r.stderr and not (TMP / "none.db").exists()
    # Blocked models: no route, no config.
    for key in ("d1-2b", "strands-decider-2b", "metask-jev-4b"):
        try:
            crp2.player(key)
            raise AssertionError(key)
        except SystemExit as e:
            assert "late-tiny8" in str(e)
    # Scoring of the dry run: stubs pick the first shown option (A); MiniCPM's stub answered prose every 7th request.
    R, md = crp2.score(out)
    names = {crp2.models()[k]["name"] for k in runnable}
    assert set(n for n, _ in R) == names
    for name in names:
        bad = 62 if name == "MiniCPM5-2B (on)" else 0
        assert crp2.invalid[(name, "invalid")] == bad and crp2.ties[name] == 0, name
        answered = sum(R[(name, v)]["q1_answered"] for v in ("numbers", "board"))
        assert answered + R[(name, "board")]["q2_items"] - bad <= 438
        for v in ("numbers", "board"):
            assert R[(name, v)]["q1_A"] == R[(name, v)]["q1_answered"], (name, v)
        if not bad:
            assert answered == 378 and R[(name, "board")]["q2_items"] == 60
    assert "| MiniCPM5-2B (on) | 438 | 438 | 0 | 62 | 0 | 376 | 14% (62/438) | 14% (62/438) |" in md, md
    (TMP / "score.md").write_text(md)
    print(f"dry run: {len(runnable)} models × 438 requests against stubs, all stored; score in {TMP / 'score.md'}")


if __name__ == "__main__":
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    (TMP / "stub_server.py").write_bytes(subprocess.run(
        ["git", "-C", str(crp2.ROOT), "show", f"{STUB_COMMIT}:tools/v3/late-tiny8/stub_server.py"],
        check=True, capture_output=True).stdout)
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    try:
        for t in tests:
            try:
                t()
                print(f"ok   {t.__name__}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {t.__name__}: {type(e).__name__}: {str(e)[:3000]}")
    finally:
        for p in PROCS:
            p.terminate()
    print(f"{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
