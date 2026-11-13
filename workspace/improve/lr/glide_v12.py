"""Lr renderer (decision.py preflight-render) for Fastino GLiDE v1.2 (local): the final inference input of
glide/server.py at the pinned snapshot, rendered on CPU with the snapshot's own code and tokenizer (no weights).

    PYTHONPATH=<snapshot> ~/code/glide/.venv/bin/python lr/glide_v12.py --model <snapshot> [--max-len 40000]

The server (glide/server.py) passes {"state", "questions"} to Glide.decide_batch (glide/model.py:270). This runs that
path up to the forward pass: Glide._prepare (model.py:305; prompt.Prompter.text builds one prompt per question),
the batch tokenization (model.py:282, add_special_tokens=False) and the only length gate (model.py:287: a prompt
of len + 8 > max_len is refused with RequestError -> HTTP 422; nothing is truncated). max_len is GLIDE_MAX_LEN,
unset by tools/v3/servers/glide-v12.sh, so the server default 40000 (server.py Settings). Declared transformations
(prompt.py): a non-string state is JSON-encoded, non-string instructions rendered by as_text, option lines
"(code) key: description"; strings pass unchanged.
Input/output: workspace/improve/lr contract (one JSON object per line, see decision.py lr_render).
"""
import argparse
import json
import os
import sys
import types


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-len", type=int, default=int(os.environ.get("GLIDE_MAX_LEN") or 40000))
    a = ap.parse_args()
    from transformers import AutoTokenizer
    from glide.model import DECISION_CONFIG, Glide, _check_codes
    from glide.prompt import Prompter, RequestError
    tok = AutoTokenizer.from_pretrained(a.model)
    with open(os.path.join(a.model, DECISION_CONFIG)) as f:
        config = json.load(f)
    _check_codes(tok, config)
    # The attributes Glide.__init__ (model.py:193) sets that _prepare reads, without the network.
    me = types.SimpleNamespace(prompter=Prompter(tok, list(config["codes"])), vision=False)
    for line in sys.stdin:
        if not line.strip():
            continue
        x = json.loads(line)
        body = x["body"]
        out = dict(id=x["id"], status="ok", error=None, sequences=[], limits=dict(max_len=a.max_len), cut=False,
                   missing=[], transformed=[], roundtrip=True)
        try:
            entries, _ = Glide._prepare(me, {"state": body["state"], "questions": body["questions"]})
        except RequestError as e:
            out.update(status="refused", error=str(e))
            print(json.dumps(out), flush=True)
            continue
        texts = [e[3] for e in entries]
        ids = tok(texts, add_special_tokens=False)["input_ids"]
        out["sequences"] = [len(i) for i in ids]
        if any(len(i) + 8 > a.max_len for i in ids):
            out.update(status="refused", error="prompt exceeds the maximum context length")
        out["roundtrip"] = all(tok.decode(i) == t for i, t in zip(ids, texts))
        out["missing"] = sorted(k for k, v in x["pieces"].items() if not all(v in t for t in texts))
        print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
