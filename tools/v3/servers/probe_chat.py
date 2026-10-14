#!/usr/bin/env python3
"""Probe an OpenAI-compatible chat server the way the v3 runner uses it.

    python3 tools/v3/servers/probe_chat.py http://127.0.0.1:8896/v1 qwen3.8-flash-next

Four requests: thinking off with logprobs (max_tokens 1, top_logprobs 20); thinking off with
room to write (it must not reason); thinking on (short); and an assistant prefill continued
with continue_final_message. Thinking is switched with chat_template_kwargs.enable_thinking.
Exits non-zero when a check fails.
"""

import json
import sys
import urllib.request

QUESTION = (
    "Which option is a fruit?\nA: a car\nB: an apple\nC: a chair\n"
    "Answer with the letter of the option only."
)


def post(base: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{base}/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def top(choice: dict, n: int = 6) -> list:
    first = choice["logprobs"]["content"][0]
    return len(first["top_logprobs"]), [(t["token"], round(t["logprob"], 3)) for t in first["top_logprobs"][:n]]


def reasoning(message: dict) -> str:
    return message.get("reasoning_content") or message.get("reasoning") or ""


def main() -> None:
    base, model = sys.argv[1].rstrip("/"), sys.argv[2]
    failures = []
    with urllib.request.urlopen(f"{base}/models", timeout=10) as r:
        info = json.loads(r.read())["data"][0]
    print(f"model {info['id']} max_model_len {info.get('max_model_len')}")
    off = {"chat_template_kwargs": {"enable_thinking": False}}
    on = {"chat_template_kwargs": {"enable_thinking": True}}
    user = [{"role": "user", "content": QUESTION}]

    r = post(base, {"model": model, "messages": user, "max_tokens": 1, "temperature": 1.0,
                    "logprobs": True, "top_logprobs": 20, **off})
    c = r["choices"][0]
    count, best = top(c)
    print(f"thinking off, max_tokens 1: content {c['message']['content']!r}, {count} top_logprobs: {best}")
    if count != 20:
        failures.append("top_logprobs != 20")

    r = post(base, {"model": model, "messages": user, "max_tokens": 64, "temperature": 0, **off})
    m = r["choices"][0]["message"]
    print(f"thinking off, max_tokens 64: reasoning {len(reasoning(m))} chars, content {m['content']!r}")
    if reasoning(m) or "think" in (m["content"] or "").lower():
        failures.append("thinking off still reasons")

    r = post(base, {"model": model, "messages": user, "max_tokens": 1024, "temperature": 1.0, **on})
    m, usage = r["choices"][0]["message"], r["usage"]
    print(f"thinking on, max_tokens 1024: reasoning {len(reasoning(m))} chars {reasoning(m)[:120]!r}..., "
          f"content {m['content']!r}, completion_tokens {usage['completion_tokens']}, "
          f"finish {r['choices'][0]['finish_reason']}")
    if not reasoning(m):
        failures.append("thinking on gave no reasoning")

    prefill = user + [{"role": "assistant", "content": "Answer:"}]
    r = post(base, {"model": model, "messages": prefill, "max_tokens": 1, "temperature": 1.0,
                    "logprobs": True, "top_logprobs": 20, "continue_final_message": True,
                    "add_generation_prompt": False, **off})
    c = r["choices"][0]
    count, best = top(c)
    print(f"prefill 'Answer:' + continue_final_message: content {c['message']['content']!r}, "
          f"{count} top_logprobs: {best}")
    if count != 20 or "B" not in best[0][0]:
        failures.append("prefill continuation did not answer B")

    print("OK" if not failures else f"FAILED: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
