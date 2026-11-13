#!/usr/bin/env python3
"""Offline stand-in for a small chat setup's server (logic's llama.cpp or vLLM server, tools/v3/late-smallchat), for a
dry run of test.sh KEY through the real chat client without a GPU or a model (as tools/v3/late-tiny8/stub_server.py).
It serves KEY's served name at /v1/models and answers /v1/chat/completions with the request rules of the setup and the
server, fixed read-outs instead of a model (the reasoning request answers {"choice": "B"}, the prefill read-out gives
B the highest probability), and refuses with 400 what the setup must never send:

  - a model field other than the served name (404, as vLLM);
  - chat_template_kwargs.enable_thinking other than player.json's, or a reasoning_effort field;
  - (on) request 1: max_tokens other than player.json's, no letter schema in response_format;
  - the read-out request: not continue_final_message true / add_generation_prompt false / max_tokens 1 / logprobs with
    player.json's top_logprobs, or (on) an assistant message other than the one the runner must build from the stub's
    reasoning ("\nstub reasoning\n"): with player.json's reasoning_field, content Answer: and the reasoning in that
    field; else content in player.json's reasoning_prefill layout, else <think>REASONING</think>Answer:;
  - a chat template error (the prompt rendered with transformers as vLLM does: continue_final_message refused when the
    template rewrites the prefilled message), as vLLM answers it: 400; the messages are given to the template as vLLM
    gives them (models.json content_format 'openai': every content a list of text parts, vLLM's auto-detection for
    LFM3's template; else strings; an assistant reasoning field also as reasoning_content);
  - a wrong read-out prompt, even without an error: the rendered read-out must be the reasoning request's rendered
    prompt (its generation prompt included) followed by text without another <think> (and, (on), with the reasoning),
    ending in Answer: (LFM3's template under content format openai opens an extra <think></think> otherwise);
  - prompt tokens + max_tokens over CONTEXT (69,632: logic's servers, 65,536 + 4,096 per sequence or llama.cpp slot),
    counted with the model's own tokenizer and the pinned repo's chat_template.jinja (the template the server applies),
    as vLLM refuses (llama.cpp would cut the reply instead; the client must never get there).
usage (bound to 127.0.0.1): stub_chat.py KEY PORT LOG   (LOG: one JSON line per request, with the counted tokens)
Needs transformers (STUB_PYTHON, see stub_test.sh: transformers 5.22.2, the vLLM be47189f3 image's); the HF cache must
hold the pin.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from transformers import AutoTokenizer

KEY, PORT, LOG = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
HERE = Path(__file__).resolve().parent
PLAYER = json.loads((HERE / "models" / KEY / "player.json").read_text())
MODEL = KEY.removesuffix("-on").removesuffix("-off")
PIN = json.loads((HERE / "models.json").read_text())[MODEL]
SERVED = PLAYER["spec"].split("/", 1)[1]
THINKING = PLAYER["request"]["chat_template_kwargs"]["enable_thinking"]
REASONING = "\nstub reasoning\n"  # with outer newlines, as Qwen-style parsers often return it
FIELD = PLAYER.get("reasoning_field")
if FIELD:
    EXPECTED = {"role": "assistant", "content": "Answer:", FIELD: REASONING}
elif "reasoning_prefill" in PLAYER:
    EXPECTED = {"role": "assistant", "content": PLAYER["reasoning_prefill"].replace("{reasoning}", REASONING.strip("\n"))}
else:
    EXPECTED = {"role": "assistant", "content": f"<think>{REASONING}</think>Answer:"}
CONTENT_FORMAT = PIN.get("content_format", "string")
CONTEXT = 69632
SNAP = Path.home() / ".cache/huggingface/hub" / f"models--{PIN['repo'].replace('/', '--')}" / "snapshots" / PIN["rev"]
TOKENIZER = AutoTokenizer.from_pretrained(SNAP)
TEMPLATE = (SNAP / "chat_template.jinja").read_text()
LOCK = threading.Lock()


def as_vllm(messages):
    """The messages as vLLM hands them to the chat template."""
    out = []
    for m in messages:
        m = dict(m)
        if CONTENT_FORMAT == "openai" and isinstance(m.get("content"), str):
            m["content"] = [{"type": "text", "text": m["content"]}]
        if m.get("reasoning") is not None:
            m["reasoning_content"] = m["reasoning"]
        out.append(m)
    return out


def render(messages, **kwargs):
    return TOKENIZER.apply_chat_template(as_vllm(messages), chat_template=TEMPLATE, tokenize=False,
                                         enable_thinking=THINKING, **kwargs)


def prompt(body):
    """Rendered prompt and its token count; the read-out's wrong-prompt reason or None. ValueError: template error."""
    readout = bool(body.get("continue_final_message"))
    text = render(body["messages"], add_generation_prompt=body.get("add_generation_prompt", True),
                  continue_final_message=readout)
    tokens = len(TOKENIZER.encode(text, add_special_tokens=False))
    wrong = None
    if readout:
        head = render(body["messages"][:-1], add_generation_prompt=True)
        rest = text[len(head):] if text.startswith(head) else None
        if rest is None or "<think>" in rest or not rest.endswith("Answer:") or (THINKING and "stub reasoning" not in rest):
            wrong = f"read-out prompt is not the reasoning request's prompt + reasoning + Answer: (assistant turn {text[len(head) - 40:]!r})"
    return tokens, wrong


def check(body):
    """The refusal reason, or None; and whether this is the read-out request."""
    readout = bool(body.get("continue_final_message"))
    kwargs = body.get("chat_template_kwargs") or {}
    if kwargs.get("enable_thinking") is not THINKING:
        return f"enable_thinking {kwargs.get('enable_thinking')!r}, setup has {THINKING!r}", readout
    if "reasoning_effort" in body:
        return f"reasoning_effort {body['reasoning_effort']!r} sent", readout
    if readout:
        last = body["messages"][-1]
        rules = [(body.get("add_generation_prompt") is False, "add_generation_prompt must be false"),
                 (body.get("max_tokens") == 1, "read-out max_tokens must be 1"),
                 (body.get("logprobs") is True, "read-out without logprobs"),
                 (body.get("top_logprobs") == PLAYER["top_logprobs"], "read-out top_logprobs differs from player.json"),
                 (last["role"] == "assistant" and last["content"].endswith("Answer:"), "no prefilled Answer:"),
                 (not THINKING or last == EXPECTED, f"(on) read-out message is not {EXPECTED!r}")]
    else:
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("schema", {})
        rules = [(not THINKING or body.get("max_tokens") == PLAYER["max_tokens"], "max_tokens differs from player.json"),
                 (not THINKING or "choice" in schema.get("properties", {}), "no letter schema")]
    for ok, reason in rules:
        if not ok:
            return reason, readout
    return None, readout


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") == "/v1/models":
            self.send(200, {"object": "list", "data": [{"id": SERVED, "object": "model"}]})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/chat/completions":
            return self.send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body.get("model") != SERVED:
            return self.send(404, {"error": f"model {body.get('model')!r} does not exist; served: {SERVED}"})
        reason, readout = check(body)
        try:
            tokens, wrong = prompt(body)
            reason = wrong or reason  # a wrong prompt is reported before the stub's rules
        except ValueError as error:  # vLLM answers a chat template error with 400 (reported first)
            tokens, reason = None, f"chat template: {str(error).split('Rendered chat')[0].strip()}"
        if reason is None and tokens + body.get("max_tokens", 0) > CONTEXT:
            reason = f"{tokens} prompt tokens + max_tokens {body.get('max_tokens')} > context {CONTEXT}"
        with LOCK, LOG.open("a") as log:
            log.write(json.dumps({"readout": readout, "prompt_tokens": tokens, "max_tokens": body.get("max_tokens"),
                                  "refused": reason, "body": body}) + "\n")
        if reason:
            return self.send(400, {"error": {"message": reason, "type": "BadRequestError", "code": 400}})
        usage = {"prompt_tokens": tokens, "completion_tokens": 1 if readout else 12}
        if readout:
            top = [{"token": letter, "logprob": lp} for letter, lp in (("B", -0.2), ("A", -1.9), ("C", -3.0))]
            message = {"role": "assistant", "content": "B"}
            logprobs = {"content": [{"token": "B", "logprob": -0.2, "top_logprobs": top}]}
        else:
            message = {"role": "assistant", "content": '{"choice": "B"}',
                       "reasoning_content": REASONING if THINKING else None}
            logprobs = None
        self.send(200, {"object": "chat.completion", "model": SERVED, "usage": usage, "choices": [
            {"index": 0, "message": message, "logprobs": logprobs, "finish_reason": "stop"}]})

    def log_message(self, *_):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
