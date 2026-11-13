#!/usr/bin/env python3
"""Recording replay stub: one port per player; every POST body is looked up byte for byte among the stored
exchanges (export.py) and answered with the stored response of the first unused identical request (the last one
again once all are used); an unknown body gets 400 (the client then fails that decision). A decision service's
warm-up (two-option 'Warm-up request before a backgammon match.') gets 200 {}. Every request is logged as one JSON
line: port, player, path, matched, warm-up, sha256 and, when unmatched, the body itself.

  stub.py exchanges.json LOG PLAYER=PORT...
"""
import hashlib
import json
import sys
import threading
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

data = json.load(open(sys.argv[1]))
log = open(sys.argv[2], "a", buffering=1)
ports = {int(p): n for n, p in (a.rsplit("=", 1) for a in sys.argv[3:])}
stored = defaultdict(deque)
last = {}
for e in data["exchanges"]:
    stored[e["request"].encode()].append(e["response"])
    last[e["request"].encode()] = e["response"]
lock = threading.Lock()
WARM = b"Warm-up request before a backgammon match."


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def reply(self, status, text):
        b = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        port = self.server.server_address[1]
        log.write(json.dumps(dict(port=port, player=ports[port], method="GET", path=self.path)) + "\n")
        self.reply(404, '{"error": "replay stub: no GET"}')

    def do_POST(self):
        port = self.server.server_address[1]
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        warm = WARM in body
        with lock:
            q = stored.get(body)
            resp = (q.popleft() if q else last[body]) if body in last else None
        rec = dict(port=port, player=ports[port], path=self.path, warm_up=warm, matched=resp is not None,
                   sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
        if resp is None and not warm:
            rec["body"] = body.decode("utf-8", "replace")
        log.write(json.dumps(rec) + "\n")
        if warm:
            self.reply(200, "{}")
        elif resp is None:
            self.reply(400, '{"error": "replay stub: request not among the stored exchanges"}')
        else:
            self.reply(200, resp)


for port in ports:
    s = ThreadingHTTPServer(("127.0.0.1", port), H)
    s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
print("stub up on", sorted(ports), flush=True)
threading.Event().wait()
