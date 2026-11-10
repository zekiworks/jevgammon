#!/usr/bin/env python3
"""Offline stand-in for KnowLine's /v1/systemone front end (knowline_server.py @ 8e56aa1), for testing the runner's
knowline client without a GPU or a model: the same request and response shapes and the same limits (1..64 questions,
choice 2..255 criteria, otherwise HTTP 422 'unsupported'/ValueError text as the real server), and fixed probabilities
instead of a model: option k of n (shown order) gets weight 1/(k+1), normalised, so the first shown option is chosen.

  python3 stub_server.py [port=19399]       GET /health, GET /v1/models, POST /v1/systemone; logs one line per request
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_LABELS = 255
MAX_QUESTIONS = 64


def answer(q):
    typ = q.get("type")
    crit = q.get("criteria")
    if typ == "noul":
        keys = ["true", "false"]
    elif typ == "choice":
        if not isinstance(crit, dict) or not 2 <= len(crit) <= MAX_LABELS:
            raise ValueError(f"choice needs 2..{MAX_LABELS} criteria")
        keys = list(crit)
    else:
        raise ValueError(f"unsupported question type {typ!r}")
    w = [1 / (k + 1) for k in range(len(keys))]
    s = sum(w)
    dist = {k: x / s for k, x in zip(keys, w)}
    out = {"type": typ, "probabilities": dist, "confidence": 0.0}
    if typ == "noul":
        out["answer"] = dist["true"] >= dist["false"]
    else:
        out["choice"] = keys[0]
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._send(200, {"status": "ok", "model": "m", "stub": True})
        if self.path.startswith("/v1/models"):
            return self._send(200, {"object": "list", "data": [{"id": "m", "object": "model", "owned_by": "stub"}]})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/v1/systemone"):
            return self._send(404, {"error": "not found"})
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            body = json.loads(raw or b"{}")
            questions = body.get("questions") or {}
            if not 1 <= len(questions) <= MAX_QUESTIONS:
                raise ValueError(f"1..{MAX_QUESTIONS} questions, got {len(questions)}")
            answers = {qid: answer(q) for qid, q in questions.items()}
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            print(f"422 {exc}", flush=True)
            return self._send(422, {"error": str(exc)})
        n = [len(q.get("criteria") or {}) for q in questions.values()]
        print(f"200 options {n} bytes {len(raw)}", flush=True)
        self._send(200, {"id": "jev-stub", "model": body.get("model") or "m", "answers": answers,
                         "usage": {"input_tokens": len(raw) // 4, "output_tokens": len(questions)}})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 19399
    print(f"KnowLine stub /v1/systemone on http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
