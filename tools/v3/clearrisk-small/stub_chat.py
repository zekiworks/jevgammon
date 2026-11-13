#!/usr/bin/env python3
"""Offline stand-in for an OpenAI-compatible chat server (llama.cpp / vLLM as logic's small_models.py runs them), for
dry runs of `jevgammon quiz` without a GPU or a model: GET /v1/models lists MODEL; POST /v1/chat/completions answers
a request constrained by response_format json_schema with {"choice": <the schema's first enum value>} after a short
reasoning_content, with usage; every INVALID-th request (0 = never) answers prose instead (an invalid answer). Requests
for another model are refused (404); MODEL '*' serves any model. /health reports the request count.

usage (bound to 127.0.0.1): stub_chat.py MODEL PORT [INVALID]
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL, PORT = sys.argv[1], int(sys.argv[2])
INVALID = int(sys.argv[3]) if len(sys.argv) > 3 else 0
LOCK = threading.Lock()
STATS = {"requests": 0, "refused": 0}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/v1/models"):
            self.send(200, {"object": "list", "data": [{"id": MODEL, "object": "model"}]})
        elif self.path.startswith("/health"):
            with LOCK:
                self.send(200, {"status": "ok", **STATS})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        if not self.path.startswith("/v1/chat/completions") or MODEL not in ("*", body.get("model")):
            with LOCK:
                STATS["refused"] += 1
            return self.send(404, {"error": {"message": f"model {body.get('model')!r} not served"}})
        with LOCK:
            STATS["requests"] += 1
            n = STATS["requests"]
        schema = body["response_format"]["json_schema"]["schema"]
        first = schema["properties"]["choice"]["enum"][0]
        content = "I think so." if INVALID and n % INVALID == 0 else json.dumps({"choice": first})
        prompt = sum(len(m["content"]) for m in body["messages"]) // 4
        self.send(200, {
            "id": f"stub-{n}", "object": "chat.completion", "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content, "reasoning_content": "Stub reasoning."}}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": 12, "total_tokens": prompt + 12,
                      "completion_tokens_details": {"reasoning_tokens": 4}}})

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
