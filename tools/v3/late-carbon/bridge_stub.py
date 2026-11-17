#!/usr/bin/env python3
"""Offline stand-in for Can's Antigravity bridge (agbench), for testing this entry without calling it: the bridge's
GET /health and GET /quota shapes (parsed.weekly_used_percent, a number, and the summary's gemini-weekly bucket) and an
OpenAI-format POST /v1/chat/completions that
answers a random option letter as {"choice": "X"} from the request's json_schema enum, with usage, no logprobs.

A request is refused (400) unless it is the body player.json makes the runner send to the bridge: model
gemini-4-carbon, a system and a user message, temperature, max_tokens and a strict json_schema response_format whose
`choice` is an enum of letters, and none of logprobs, top_logprobs, reasoning_effort. Every request goes to LOG as one
JSON line (body and status).

  bridge_stub.py PORT LOG QUOTA_FILE    QUOTA_FILE holds the weekly use reported (e.g. 64.8), re-read on every
                                        /health and /quota; when it is missing both answer 503
"""
import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT, LOG, QUOTA = int(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ALLOWED = {"model", "messages", "temperature", "max_tokens", "response_format"}


def problems(body: dict) -> list[str]:
    out = []
    if body.get("model") != "gemini-4-carbon":
        out.append(f"model {body.get('model')!r}")
    extra = set(body) - ALLOWED
    if extra:
        out.append(f"unexpected fields {sorted(extra)}")
    roles = [m.get("role") for m in body.get("messages", [])]
    if roles != ["system", "user"]:
        out.append(f"roles {roles}")
    rf = body.get("response_format") or {}
    schema = (rf.get("json_schema") or {}).get("schema") or {}
    enum = ((schema.get("properties") or {}).get("choice") or {}).get("enum")
    if rf.get("type") != "json_schema" or not (rf.get("json_schema") or {}).get("strict") or not enum:
        out.append("no strict json_schema letter enum")
    return out


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path not in ("/health", "/quota"):
            return self.reply(404, {"error": "not found"})
        try:
            used = float(QUOTA.read_text())
        except (OSError, ValueError):
            return self.reply(503, {"status": "down"})
        if self.path == "/quota":
            return self.reply(200, {
                "summary": {"groups": [{"displayName": "Gemini Models", "buckets": [
                    {"bucketId": "gemini-weekly", "window": "weekly", "remainingFraction": (100 - used) / 100,
                     "resetTime": "2026-11-20T22:51:48Z"},
                    {"bucketId": "gemini-5h", "window": "5h", "remainingFraction": 0.999,
                     "resetTime": "2026-11-17T19:51:47Z"}]}]},
                "parsed": {"weekly_used_percent": used, "weekly_remaining_percent": 100 - used,
                           "five_hour_remaining_percent": 99.9, "reserve_threshold_used_fraction": 0.85}})
        self.reply(200, {"status": "ok", "circuit_breaker": False, "circuit_breaker_reason": None,
                         "antigravity_connected": True, "queue_depth": 0, "active_requests": 0, "max_concurrency": 4,
                         "conversation_timeout_seconds": 1500,
                         "quota": {"weekly_used_percent": f"{used:.1f}%", "weekly_remaining_percent": f"{100 - used:.1f}%",
                                   "five_hour_remaining_percent": "99.97%", "reserve_threshold_percent": "85%"}})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        bad = problems(body) if self.path == "/v1/chat/completions" else [f"path {self.path}"]
        with LOG.open("a") as f:
            f.write(json.dumps({"at": time.time(), "status": 400 if bad else 200, "problems": bad, "body": body}) + "\n")
        if bad:
            return self.reply(400, {"error": {"message": "; ".join(bad)}})
        letters = body["response_format"]["json_schema"]["schema"]["properties"]["choice"]["enum"]
        self.reply(200, {
            "id": f"chatcmpl-stub-{time.time_ns()}", "object": "chat.completion", "created": int(time.time()),
            "model": "gemini-4-carbon",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": json.dumps({"choice": random.choice(letters)})}}],
            "usage": {"prompt_tokens": 11000, "completion_tokens": 900, "total_tokens": 11900},
        })

    def log_message(self, *_):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
