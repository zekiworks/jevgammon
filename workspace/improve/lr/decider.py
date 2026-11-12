"""Lr renderer (decision.py preflight-render) for Decider v1.2 27B: the final inference input of
pplx_decider_server.py (~/code/pplx-decider) on the checkpoint's own pplx_decider package (source/src), rendered on
CPU with the checkpoint's processor (no weights).

    ~/code/pplx-decider/.venv-v1.2/bin/python lr/decider.py --model <checkpoint>

The server pops the model field and calls Decider.decide on the reference path (fast=False) with the default
max_length (pplx_decider_server.py main; model.py DEFAULT_MAX_LENGTH 262,144). Decider._run (model.py:240) calls
Encoder.plan(request, max_length) (protocol.py), which validates the request (RequestError -> HTTP 400), encodes it
as one sequence and only when it exceeds max_length bisects the questions (every chunk keeps the full state); a
single question over max_length raises LengthError (HTTP 400). Nothing is truncated. The processor, codes check and
Encoder are built as Decider.__init__ does (model.py:121-148), without the backbone. Declared transformation
(protocol.py Encoder._text): literal special tokens in state, instructions and descriptions are neutralized to
full-width brackets; a non-string value is JSON-encoded. Option lines are "<code>: <key>: <description>".
"""
import argparse
import json
import string
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.model / "source" / "src"))
    from transformers import AutoProcessor
    from pplx_decider.model import DEFAULT_MAX_LENGTH
    from pplx_decider.protocol import (LEGACY_MAX_PIXELS, MAX_OPTIONS, MIN_PIXELS, PROTOCOL, Encoder, LengthError,
                                       RequestError, load_json)
    ck = a.model
    if load_json(ck / "joint_config.json") != PROTOCOL:
        raise SystemExit("checkpoint does not declare protocol v3")
    config = load_json(ck / "decision_config.json")
    codes = list(config["codes"])
    processor = AutoProcessor.from_pretrained(str(ck))
    processor.tokenizer.padding_side = "left"
    processor.image_processor.size = {"shortest_edge": MIN_PIXELS,
                                      "longest_edge": int(config.get("max_pixels") or LEGACY_MAX_PIXELS)}
    tok = processor.tokenizer
    if len(codes) != MAX_OPTIONS or any(tok.encode(c, add_special_tokens=False) != [t]
                                        for c, t in zip(codes, config["token_ids"], strict=True)):
        raise SystemExit("checkpoint answer codes differ from its tokenizer")
    if any(not set(c) <= set(string.ascii_uppercase) for c in codes):
        raise SystemExit("unexpected answer codes")
    enc = Encoder(processor, codes)
    for line in sys.stdin:
        if not line.strip():
            continue
        x = json.loads(line)
        request = dict(x["body"])
        request.pop("model", None)
        out = dict(id=x["id"], status="ok", error=None, sequences=[], limits=dict(max_length=DEFAULT_MAX_LENGTH),
                   cut=False, missing=[], transformed=[], roundtrip=True)
        try:
            plan = enc.plan(request, DEFAULT_MAX_LENGTH)
        except (RequestError, LengthError) as e:
            out.update(status="refused", error=str(e))
            print(json.dumps(out), flush=True)
            continue
        out["sequences"] = [c.length for c in plan]
        if len(plan) > 1:  # questions split into chunks: each keeps the full state; reported, not a cut
            out["chunks"] = len(plan)
        texts = [tok.decode(c.input_ids.tolist()) for c in plan]
        rendered = [enc.text({**request, "questions": dict((k, request["questions"][k]) for k in c.keys)})
                    for c in plan]
        out["roundtrip"] = texts == rendered
        out["transformed"] = sorted(k for k, v in x["pieces"].items() if enc._text(v) != v)
        out["missing"] = sorted(k for k, v in x["pieces"].items() if not all(enc._text(v) in t for t in rendered))
        print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
