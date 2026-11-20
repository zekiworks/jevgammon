"""Pin parity, GPU-free (Ümit #13349): before a small model plays on a new runner pin, the pin must reproduce an
already-published step. A stub OpenAI-compatible server replays one stored test step (E1, E2, E3 or a T10) of a
finished lane: every request the pin sends must be byte-identical to a stored request of that step, answered with the
stored response (attempts in order); a request not stored gets HTTP 400 (no retry) and fails the check. The pin asks
the same 200 positions with the step's own config (same setup, option-order seed, settings); only base_url and the
route reject log point elsewhere. PASS needs, per position, the stored answer exactly (chosen index, letter, move,
option order, legal count, invalid, error, probabilities and their source), the step's metrics (answered, valid,
invalid, failed, risk/safety pays, risks found, right safety, error rate) equal, and every stored request sent once.
No model call, no GPU, no money; nothing under runs/ or smoke/ is written, except with --record: a PASS is then also
written to runs/parity/<commit>.json, which improve.py requires before a PIN_READS pin runs (parity_check).

    python3 workspace/improve/parity.py --model gemma-4-e4b-on --step E1 \\
        --bin target/improve-bin/jevgammon-c32fedb [--out DIR] [--record]

Exit 0 on PASS, 1 on FAIL. The report (parity.json) and the replay database are written to --out (default a new
directory under /tmp).
"""

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import improve as I  # noqa: E402

ANSWER_FIELDS = ("chosen_index", "letter", "move", "option_order", "legal_count", "invalid", "error",
                 "probabilities", "probability_source")
METRIC_FIELDS = ("answered", "valid", "invalid", "failed", "risk_pays", "safety_pays", "risks_found",
                 "right_safety", "error_rate")


def stored_exchanges(db_path, setup):
    """The step's stored request bytes -> its responses in attempt order (an answer's re-sent request repeats)."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=60)
    rows = db.execute("SELECT x.request, x.response, x.error FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id "
                      "WHERE a.setup = ? AND a.repeat = 1 ORDER BY a.id, x.attempt", (setup,)).fetchall()
    db.close()
    replies = defaultdict(deque)
    for request, response, error in rows:
        replies[request].append((response, error))
    return replies, len(rows)


class Replay(BaseHTTPRequestHandler):
    replies, lock, sent, unmatched, other = None, threading.Lock(), 0, [], []

    def log_message(self, *args):
        pass

    def reply(self, status, body):
        data = body.encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        Replay.other.append(f"GET {self.path}")
        self.reply(404, '{"error": "parity stub: no such route"}')

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length") or 0)).decode()
        with Replay.lock:
            queue = Replay.replies.get(body)
            hit = queue.popleft() if queue else None
            if hit is None:
                Replay.unmatched.append(body)
            else:
                Replay.sent += 1
        if hit is None:
            self.reply(400, '{"error": "parity stub: request not byte-identical to a stored request of the step"}')
        elif hit[1] is not None or hit[0] is None:
            self.reply(500, json.dumps({"error": f"parity stub: stored failed attempt: {hit[1]}"}))
        else:
            self.reply(200, hit[0])


def answers(db_path, setup):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM answers WHERE setup = ? AND repeat = 1 ORDER BY id", (setup,)).fetchall()
    db.close()
    return {r["position_id"]: r for r in rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True, choices=sorted(I.MODELS))
    ap.add_argument("--step", default="E1", help="a finished test step of the model (E1, E2, E3)")
    ap.add_argument("--bin", required=True, help="the runner pin to check (target/improve-bin/jevgammon-<commit>)")
    ap.add_argument("--out", help="report directory (default: a new one under /tmp)")
    ap.add_argument("--record", action="store_true", help="on PASS, record it for improve.py (runs/parity/<commit>.json)")
    a = ap.parse_args()
    bin_path = Path(a.bin).resolve()
    out = Path(a.out or tempfile.mkdtemp(prefix=f"parity-{a.model}-{a.step}-"))
    out.mkdir(parents=True, exist_ok=True)
    source_db = I.db_path(a.model)
    config = json.loads((I.step_dir(a.model, a.step) / f"test-{a.step}.json").read_text())
    (player,) = config["players"]
    setup = player["name"]
    stored = answers(source_db, setup)
    if len(stored) != I.POSITIONS:
        raise SystemExit(f"{a.model} {a.step}: {len(stored)} stored answers, not {I.POSITIONS}: not a finished step")

    Replay.replies, total = stored_exchanges(source_db, setup)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Replay)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    player["base_url"] = f"http://127.0.0.1:{server.server_address[1]}/v1"
    if player.get("expect_route", {}).get("reject_log"):
        player["expect_route"]["reject_log"] = str(out / "route-rejections.jsonl")
    (out / "config.json").write_text(json.dumps(config, indent=1))
    replay_db = out / "replay.db"
    replay_db.unlink(missing_ok=True)
    r = subprocess.run([str(bin_path), "ask", "--config", str(out / "config.json"), "--positions",
                        str(I.TEST_POSITIONS), "--out", str(replay_db), "--setup", setup], cwd=I.CODE,
                       capture_output=True, text=True)
    server.shutdown()
    (out / "ask.log").write_text(r.stdout + r.stderr)

    replayed = answers(replay_db, setup) if replay_db.exists() else {}
    diffs = []
    for pid in sorted(set(stored) | set(replayed)):
        s, p = stored.get(pid), replayed.get(pid)
        if s is None or p is None:
            diffs.append(dict(position=pid, missing="replay" if p is None else "stored"))
            continue
        for f in ANSWER_FIELDS:
            if s[f] != p[f]:
                diffs.append(dict(position=pid, field=f, stored=s[f], replayed=p[f]))
    positions = {p["id"]: p for p in I.test_set()["positions"]}
    m_stored = I.metrics_from(list(stored.values()), positions)
    m_replayed = I.metrics_from(list(replayed.values()), positions)
    metric_diffs = {f: [m_stored[f], m_replayed[f]] for f in METRIC_FIELDS if m_stored[f] != m_replayed[f]}
    left = sum(len(q) for q in Replay.replies.values())
    checks = dict(runner_exit=r.returncode == 0, answers_identical=not diffs, metrics_identical=not metric_diffs,
                  requests_byte_identical=not Replay.unmatched, every_stored_request_sent=left == 0)
    report = dict(model=a.model, step=a.step, setup=setup, source_db=str(source_db),
                  pin=dict(path=str(bin_path), commit=bin_path.name.removeprefix("jevgammon-"),
                           sha256=I.sha256_file(bin_path)), at=I.now(),
                  stored_requests=total, requests_matched=Replay.sent, requests_unmatched=len(Replay.unmatched),
                  stored_requests_not_sent=left, other_requests=Replay.other, runner_exit=r.returncode,
                  metrics={f: m_stored[f] for f in METRIC_FIELDS}, metric_diffs=metric_diffs,
                  answer_diffs=len(diffs), first_answer_diffs=diffs[:20], checks=checks,
                  result="PASS" if all(checks.values()) else "FAIL")
    (out / "parity.json").write_text(json.dumps(report, indent=1, default=str))
    if a.record and report["result"] == "PASS":
        I.write_atomic(I.parity_path(report["pin"]["commit"]), json.dumps(report, indent=1, default=str))
    if Replay.unmatched:
        (out / "unmatched-requests.jsonl").write_text("\n".join(Replay.unmatched) + "\n")
    print(f"{report['result']} {a.model} {a.step} on {bin_path.name} (sha256 {report['pin']['sha256'][:16]}): "
          f"requests {Replay.sent}/{total} byte-identical, {len(Replay.unmatched)} unmatched, {left} not sent; "
          f"answers {I.POSITIONS - len({d['position'] for d in diffs})}/{I.POSITIONS} identical; metrics "
          f"{'identical' if not metric_diffs else metric_diffs} (invalid {m_stored['invalid']}, risks found "
          f"{m_stored['risks_found']}); report {out / 'parity.json'}")
    sys.exit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
