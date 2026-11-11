#!/usr/bin/env python3
"""Offline stand-in for the tiny8 entrants' /v1/systemone servers, for a dry run of the runner's clients without a GPU
or a model: the request and response shapes and the request rules of each server kind, fixed read-outs instead of a
model (option j in shown order gets weight 1/(j+1), so the first shown option wins), and the most options seen in one
question reported by /health. Kinds (the server each one stands for, and what it refuses with 422 / 404):

  knowline    knowline_server.py: model field "m"; 2..255 options
  startlux    startlux-decide serve: no model field needed (ignored); 2..255 options (knocked out by the server)
  onejev      flide serve --name OmniJev/OneJev1.6-0.8B: model field that name (404 otherwise); 2..255 options
  gliclass    gliclass_server.py: model field absent or knowledgator/gliclass-v4-edge; no GET route (501); refuses
              more than 218 options here, so a dry run shows the client splits at its cap (the real server refuses by
              tokens, 16,384)
  glide       glide.server (0.8B, 2B): model field ignored; 1..255 options
  glide-0.4b  glide.server with the 0.4B: as glide, but refuses more than 74 options here, so a dry run shows the
              client splits at its cap (the real model would shorten such prompts; GLIDE_MAX_LEN=8006 refuses them)

usage (bound to 127.0.0.1): stub_server.py KIND PORT
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KIND, PORT = sys.argv[1], int(sys.argv[2])
CAP = {"gliclass": 218, "glide-0.4b": 74}.get(KIND, 255)
MODEL_RULE = {
    "knowline": lambda m: m == "m",
    "onejev": lambda m: m == "OmniJev/OneJev1.6-0.8B",
    "gliclass": lambda m: m in (None, "knowledgator/gliclass-v4-edge"),
}.get(KIND, lambda m: True)
LOCK = threading.Lock()
STATS = {"requests": 0, "refused": 0, "most_options": 0, "options_seen": {}}


def answer(spec):
    crit = spec.get("criteria") if isinstance(spec, dict) else None
    if spec.get("type") != "choice" or not isinstance(crit, dict):
        raise ValueError("a choice question with criteria is required")
    keys = list(crit)
    if not 2 <= len(keys) <= CAP:
        raise ValueError(f"{len(keys)} options: this server takes 2 to {CAP}")
    w = [1 / (j + 1) for j in range(len(keys))]
    s = sum(w)
    probs = {k: x / s for k, x in zip(keys, w)}
    return {"type": "choice", "choice": keys[0], "confidence": probs[keys[0]], "probabilities": probs}, len(keys)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if KIND == "gliclass":
            self.send(501, {"error": "no GET route"})
        elif self.path.startswith("/health"):
            with LOCK:
                self.send(200, {"status": "ok", "stub": KIND, "cap": CAP, **STATS})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        if not MODEL_RULE(body.get("model")):
            with LOCK:
                STATS["refused"] += 1
            return self.send(404 if KIND == "onejev" else 422, {"error": f"model {body.get('model')!r} not served"})
        try:
            answers, n = {}, 0
            for qid, spec in body["questions"].items():
                answers[qid], k = answer(spec)
                n = max(n, k)
        except (KeyError, ValueError, AttributeError) as exc:
            with LOCK:
                STATS["refused"] += 1
            return self.send(422, {"error": str(exc)})
        with LOCK:
            STATS["requests"] += 1
            STATS["most_options"] = max(STATS["most_options"], n)
            STATS["options_seen"][n] = STATS["options_seen"].get(n, 0) + 1
        tokens = len(json.dumps(body)) // 4
        self.send(200, {"model": body.get("model") or KIND, "answers": answers,
                        "usage": {"input_tokens": tokens, "output_tokens": 0}})

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
