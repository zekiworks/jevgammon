#!/usr/bin/env python3
"""Offline stand-in for SubQ's Chat Completions API (https://api.subq.ai/v1/chat/completions) serving subq-savant-1.4,
for testing this entry without calling SubQ: answers a random option letter as {"choice": "X"} from the request's
json_schema enum, with SubQ's separate message.reasoning, usage (prompt_tokens_details.cached_tokens,
completion_tokens_details.reasoning_tokens) and the served model name; no logprobs.

As SubQ documents for Savant (docs.subq.ai/endpoints/chat-completions-api, read 2026-11-18), a request is refused
(400) when it sends logprobs or top_logprobs (unsupported_parameter), a temperature other than 1 or a reasoning_effort
other than low, high or max (unsupported_value); and also unless it is the body player.json makes the runner send:
model subq-savant-1.4, a bearer key, a system and a user message, temperature 1, max_tokens, reasoning_effort high and
a strict json_schema response_format whose `choice` is an enum of letters. Every request goes to LOG as one JSON line
(body and status).

  subq_stub.py PORT LOG
"""
import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT, LOG = int(sys.argv[1]), Path(sys.argv[2])
ALLOWED = {"model", "messages", "temperature", "max_tokens", "reasoning_effort", "response_format"}


def refusal(body: dict, auth: str | None) -> tuple[str, str, str] | None:
    """(code, param, message) of SubQ's 400/401 for this body, or None."""
    if not (auth or "").startswith("Bearer ") or len(auth) <= 7:
        return ("invalid_api_key", "", "missing bearer key")
    for p in ("logprobs", "top_logprobs"):
        if p in body:
            return ("unsupported_parameter", p, f"{p} is not supported for this model.")
    if body.get("temperature", 1) != 1:
        return ("unsupported_value", "temperature", "temperature is fixed at 1")
    if body.get("reasoning_effort", "high") not in ("low", "high", "max"):
        return ("unsupported_value", "reasoning_effort", "reasoning_effort must be low, high or max")
    out = []
    if body.get("model") != "subq-savant-1.4":
        out.append(f"model {body.get('model')!r}")
    extra = set(body) - ALLOWED
    if extra:
        out.append(f"fields {sorted(extra)}")
    if body.get("reasoning_effort") != "high":
        out.append(f"reasoning_effort {body.get('reasoning_effort')!r}")
    if not isinstance(body.get("max_tokens"), int):
        out.append("max_tokens")
    roles = [m.get("role") for m in body.get("messages", [])]
    if roles != ["system", "user"]:
        out.append(f"roles {roles}")
    rf = body.get("response_format") or {}
    js = rf.get("json_schema") or {}
    enum = (((js.get("schema") or {}).get("properties") or {}).get("choice") or {}).get("enum")
    if rf.get("type") != "json_schema" or js.get("strict") is not True or not enum:
        out.append("response_format")
    return ("validation_error", "", "; ".join(out)) if out else None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, status: int, obj: dict) -> None:
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        bad = refusal(body, self.headers.get("Authorization"))
        status = 200 if bad is None else (401 if bad[0] == "invalid_api_key" else 400)
        with LOG.open("a") as f:
            f.write(json.dumps({"status": status, "refusal": bad, "body": body}) + "\n")
        if bad:
            code, param, msg = bad
            return self.reply(status, {"error": {"message": msg, "type": "invalid_request_error", "code": code,
                                                 "param": param}})
        enum = body["response_format"]["json_schema"]["schema"]["properties"]["choice"]["enum"]
        time.sleep(0.01)
        self.reply(200, {
            "id": f"chatcmpl-stub-{random.getrandbits(32):08x}", "object": "chat.completion",
            "created": int(time.time()), "model": "subq-savant-1.4",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps({"choice": random.choice(enum)}),
                "reasoning": "stub reasoning"}}],
            "usage": {"prompt_tokens": 1800, "completion_tokens": 600, "total_tokens": 2400,
                      "prompt_tokens_details": {"cached_tokens": 1024},
                      "completion_tokens_details": {"reasoning_tokens": 590}},
            "metadata": {},
        })


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
