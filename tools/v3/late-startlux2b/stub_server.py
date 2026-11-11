#!/usr/bin/env python3
"""Offline stand-in for StartLux-Decision's /v1/systemone server (startlux-decide serve @ a99977d, Instant folder,
serve's defaults), for testing the runner's startlux client without a GPU or a model: the same request and response
shapes and limits, and fixed read-outs instead of a model. A choice question needs 2 or more options (ids non-empty,
single-line, at most 200 characters, distinct), otherwise HTTP 422 with the server's error layout. As serve does by
default (none_check), every pass carries a hidden 'None of the above' option, so one pass reads at most 25 listed
options; a longer list is knocked out as the server does (near-equal groups of at most 25, the 3 best of each to the
final, at most 25 finalists; the others share 0.001 in proportion to their group read-out). A read-out over k options
gives option j (shown order) weight 1/(j+1), and the hidden option 0.05 of the whole, so the first shown option wins.
The answer: {"type": "choice", "choice", "confidence", "probabilities" (unrounded, over the listed options),
"none_probability"}, "usage" {"input_tokens", "output_tokens": 0} (here: characters / 4) and "model". Any "model" field
in the request is ignored, as by the real server. Requests in flight are counted; /health reports the peak.

  python3 stub_server.py [port=19439] [delay=0.05]     GET /health, GET /v1/models, POST /v1/systemone
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "StartLux-Decision-v1.1-2B-Instant@f1e6cd147dda82c9ffa3e8e725d5c1f175566fb1"
GROUP, KEEP, RESIDUAL, PASS = 25, 3, 0.001, 25
DELAY = 0.05
LOCK = threading.Lock()
STATE = {"in_flight": 0, "peak": 0, "requests": 0}


class RequestError(ValueError):
    pass


def read(keys):
    """One pass over `keys` with the hidden extra option: listed probabilities renormalised, and the extra's share."""
    w = [1 / (j + 1) for j in range(len(keys))]
    s = sum(w)
    return {k: x / s for k, x in zip(keys, w)}, 0.05


def groups(keys):
    n = -(-len(keys) // GROUP)
    size, extra = divmod(len(keys), n)
    out, start = [], 0
    for g in range(n):
        end = start + size + (1 if g < extra else 0)
        out.append(keys[start:end])
        start = end
    return out


def answer(state, spec):
    if spec.get("type", "choice") != "choice":
        raise RequestError("this stub answers choice questions only")
    crit = spec.get("criteria")
    if not isinstance(crit, dict):
        raise RequestError("a choice question needs criteria: {option: description or null} or a list of options")
    keys = list(crit)
    for k in keys:
        if not k.strip() or "\n" in k or "\r" in k or len(k) > 200:
            raise RequestError(f"bad option id {k!r}: ids must be non-empty single-line strings of at most 200 "
                               "characters")
    if len(keys) < 2:
        raise RequestError(f"a question needs 2 to 26 options in one pass, got {len(keys)}")
    text = len(state) + len(spec.get("instructions", ""))
    if len(keys) <= PASS:
        dist, none = read(keys)
        tokens = (text + sum(len(k) + len(str(crit[k])) for k in keys)) // 4
    else:
        first, finalists, tokens = {}, [], 0
        for g in groups(keys):
            p, _ = read(g)
            first.update(p)
            finalists += sorted(g, key=lambda c: -p[c])[:KEEP]
            tokens += (text + sum(len(k) + len(str(crit[k])) for k in g)) // 4
        finalists = sorted(finalists, key=lambda c: -first[c])[:PASS] if len(finalists) > PASS else finalists
        final, none = read(finalists)
        tokens += (text + sum(len(k) + len(str(crit[k])) for k in finalists)) // 4
        rest = [c for c in keys if c not in final]
        mass = sum(first[c] for c in rest)
        dist = {c: final[c] * (1 - RESIDUAL) if c in final else RESIDUAL * first[c] / mass for c in keys}
    top = max(dist, key=dist.get)
    return {"type": "choice", "choice": top, "confidence": dist[top], "probabilities": dist,
            "none_probability": none}, tokens


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            with LOCK:
                peak, n = STATE["peak"], STATE["requests"]
            self.reply(200, {"status": "ok", "model": MODEL, "kind": "instant", "prompt_attention": "bidirectional",
                             "stub": True, "requests": n, "peak_in_flight": peak})
        elif self.path == "/v1/models":
            self.reply(200, {"models": [{"name": MODEL, "description": "offline stub"}]})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/v1/systemone", "/v1/decisions"):
            return self.reply(404, {"error": "not found"})
        with LOCK:
            STATE["in_flight"] += 1
            STATE["requests"] += 1
            STATE["peak"] = max(STATE["peak"], STATE["in_flight"])
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            questions = body.get("questions")
            if not isinstance(questions, dict) or not questions:
                raise RequestError("questions must be a non-empty object")
            state = body.get("state") if isinstance(body.get("state"), str) else json.dumps(body.get("state"))
            answers, tokens = {}, 0
            for key, spec in questions.items():
                answers[key], t = answer(state, spec)
                tokens += t
            time.sleep(DELAY)
            self.reply(200, {"answers": answers, "usage": {"input_tokens": tokens, "output_tokens": 0},
                             "model": MODEL})
        except (RequestError, json.JSONDecodeError) as e:
            self.reply(422, {"error": str(e), "detail": [{"loc": ["body"], "msg": str(e), "type": "value_error"}]})
        finally:
            with LOCK:
                STATE["in_flight"] -= 1
                peak = STATE["peak"]
            sys.stderr.write(f"request {STATE['requests']} done; peak in flight {peak}\n")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 19439
    DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else DELAY
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
