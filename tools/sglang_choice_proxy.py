#!/usr/bin/env python3
"""Lets Cygnet's letter-reading decision server (written for vLLM) drive an SGLang server.

    python3 tools/sglang_choice_proxy.py --listen 8011 --upstream http://127.0.0.1:8010

The decision server constrains the one-token answer with vLLM's `structured_outputs: {"choice":
[...]}` and turns reasoning off with `chat_template_kwargs: {"enable_thinking": false}`. SGLang
ignores both: DeepSeek V4.1 then starts thinking ("We ...") and no option letter can be read.
This proxy rewrites them to SGLang's `regex` and DeepSeek's `{"thinking": false}`; every other
request and response passes through unchanged. Standard library only.
"""

import argparse
import json
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Proxy(BaseHTTPRequestHandler):
    upstream = ""

    def forward(self, body):
        req = urllib.request.Request(self.upstream + self.path, data=body, method=self.command,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                status, data = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, data = e.code, e.read()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.forward(None)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        choice = body.pop("structured_outputs", {}).get("choice")
        if choice:
            body["regex"] = "(" + "|".join(re.escape(c) for c in choice) + ")"
        kwargs = body.get("chat_template_kwargs")
        if kwargs and "enable_thinking" in kwargs:
            kwargs["thinking"] = kwargs.pop("enable_thinking")
        self.forward(json.dumps(body).encode())

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--listen", type=int, default=8011)
    ap.add_argument("--upstream", default="http://127.0.0.1:8010")
    args = ap.parse_args()
    Proxy.upstream = args.upstream.rstrip("/")
    ThreadingHTTPServer(("127.0.0.1", args.listen), Proxy).serve_forever()


if __name__ == "__main__":
    main()
