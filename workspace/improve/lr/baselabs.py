"""Lr renderer (decision.py `preflight-render`) for Base Labs Elephant-1 / Mammoth-1: what the decision-models runner's
servers/baselabs_server.py (analysis/decision-models 12a2ea1, sha256 36bbf7c4…) would run for a System One request,
computed by qev's own server and engine code inside image baselabs-serve:81ce62f, with the tokenizer only.

Run (CPU only, no network, no weights; the hub is mounted whole because snapshot files are symlinks into blobs/; the
entrypoint is python itself because the image's nvidia_entrypoint.sh prints a banner on stdout):

    docker run --rm -i --network none -e HF_HUB_OFFLINE=1 -e CUDA_VISIBLE_DEVICES= \
        -v ~/.cache/huggingface/hub:/hf:ro -v <worktree>/workspace/improve/lr:/lr:ro \
        --entrypoint /opt/conda/bin/python baselabs-serve:81ce62f /lr/baselabs.py \
        --model /hf/models--baselabs--elephant-1/snapshots/b3f8a93462fb1051a9de031e94a7ff380e254072 \
        --name baselabs/elephant-1

Flags: --model the snapshot directory (as the server's --checkpoint); --name the server's --name, which every
request's model field must give (workspace/late3/baselabs.sh: baselabs/elephant-1, baselabs/mammoth-1).
stdin/stdout: the Lr contract (JSONL in, JSONL out, same order). stderr: provenance and diagnostics.

How (line numbers are of the image's /work/OneJev/qev at 81ce62f + serve.patch; engine.py sha256 dc3eb95e…,
prompt.py f0763b5f…, server.py 51ddaafe…, readout.py e084edea…, schema.py bce4b7d3…):
- DecisionEngine.__init__ (engine.py:61-125) loads the weights, so it is not called. The engine object is made with
  __new__ and given exactly the attributes __init__ sets that rendering and the gates read: the limits from the
  constructor's own defaults (max_branch_tokens 32768, max_request_tokens 65536, style DEFAULT_STYLE; engine.py:68-73,
  read through inspect, and baselabs_server.py passes none of them), AutoTokenizer/AutoConfig from the local snapshot
  with the same arguments (engine.py:90-97), template_kwargs (engine.py:105), the slot check via the engine's own
  _verify_slots (engine.py:106, 143-163), the readout config via ReadoutConfig.load (engine.py:107, readout.py:74-86)
  and its max_slots cap (engine.py:111-112), and fork_mode "sequential".
- The request goes through qev's own app, create_app(engine, model_name=--name) (server.py:35-86; baselabs_server.py
  serves exactly that), via Starlette's TestClient: the same JSON parsing, SystemOneRequest validation (422), model
  check (404), QEV_DEBIAS default (server.py:39) and DecisionEngine.decide (engine.py:391-421: render_question per
  question, chunking above max_slots, _prefix_and_suffix_ids, the two token gates → ValueError → 422).
- Past the gates decide calls _run_sequential (engine.py:433), which is replaced here by a stub that runs the engine's
  own _split (engine.py:204-226, the first thing _run_sequential:270 and _run_batched:322 both do; with the
  checkpoint's noncausal attention it checks the token layout, whose ValueError is also a 422) and then stops before
  any forward. _prefix_and_suffix_ids (engine.py:242-256) is wrapped only to record its inputs and outputs.
- Sequences: one per rendered branch, prefix + suffix tokens (= encode(_render_prompt(state, suffix)), engine.py:245).
  Final input text: engine._render_prompt (engine.py:165-167: build_messages + the checkpoint's chat template).
- Transformation, as qev declares it: state and block → prompt.render_state (prompt.py:60-65; identity for a string
  state; for a non-string state the piece is checked as JSON-escaped inside json.dumps); instructions and
  option:<key> → prompt.render_entry (prompt.py:51-57; strips a string).
- cut: true when a choice is chunked (decide, engine.py:399-405: more options than max_slots, each chunk gets a
  "none of the options listed here" slot and only its own options). No truncation path exists in qev.
"""
import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
import types
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


class _Stop(Exception):
    """Raised by the _run_sequential stub once the engine has split the request; no forward runs."""


def build_engine(model_path: str):
    import torch
    import transformers
    from qev import engine as qe
    from qev import readout as ro
    from qev.calibrate import Calibration

    defaults = {k: p.default for k, p in inspect.signature(qe.DecisionEngine.__init__).parameters.items()}
    eng = qe.DecisionEngine.__new__(qe.DecisionEngine)
    eng.model_path = model_path
    eng.device = torch.device("cpu")
    eng.calibration = Calibration()
    eng.max_branch_tokens = defaults["max_branch_tokens"]
    eng.max_request_tokens = defaults["max_request_tokens"]
    eng.fork_token_budget = defaults["fork_token_budget"]
    eng.fork_tolerance = defaults["fork_tolerance"]
    eng.style = defaults["style"]
    local = Path(model_path).exists()
    common = {"local_files_only": local, "trust_remote_code": False}
    config = transformers.AutoConfig.from_pretrained(model_path, **common)
    eng.tokenizer = transformers.AutoTokenizer.from_pretrained(model_path, **common)
    if config.model_type in {"qwen3_5", "qwen3_5_text"}:
        config = config.get_text_config()
    eng.model_type = config.model_type
    eng.template_kwargs = {"enable_thinking": False} if "qwen" in eng.model_type else {}
    eng.slot_ids = eng._verify_slots()
    rcfg = ro.ReadoutConfig.load(model_path) if local else ro.ReadoutConfig()
    eng.readout = types.SimpleNamespace(config=rcfg, head=None, capture=None)
    if rcfg.head:
        eng.max_slots = min(eng.max_slots, rcfg.n_slots)
    eng.pad_id = eng.tokenizer.pad_token_id if eng.tokenizer.pad_token_id is not None else eng.tokenizer.eos_token_id
    eng.info = qe.EngineInfo(model_path=model_path, model_type=eng.model_type, dtype="bfloat16", device="cpu",
                             fork_mode="sequential", fork_max_abs_diff=None,
                             transformers_version=transformers.__version__, torch_version=torch.__version__,
                             extra={"attention": rcfg.attention, "readout": rcfg.readout, "renderer": "no weights"})

    record = {}
    real_split_ids = eng._prefix_and_suffix_ids

    def prefix_and_suffix_ids(state, rendered):
        prefix_ids, suffixes = real_split_ids(state, rendered)
        record.update(state=state, rendered=list(rendered), prefix_ids=prefix_ids, suffixes=suffixes)
        return prefix_ids, suffixes

    def run_sequential(state, rendered):
        eng._split(state, rendered)
        raise _Stop()

    eng._prefix_and_suffix_ids = prefix_and_suffix_ids
    eng._run_sequential = run_sequential
    return eng, record, rcfg


def provenance(model_path: str, rcfg) -> dict:
    import qev
    import torch
    import transformers

    root = Path(qev.__file__).resolve().parent
    out = {"python": sys.version.split()[0], "qev": str(root), "transformers": transformers.__version__,
           "torch": torch.__version__, "attention": rcfg.attention, "readout": rcfg.readout, "n_slots": rcfg.n_slots}
    git = root.parent
    try:
        out["onejev_head"] = subprocess.run(["git", "-C", str(git), "rev-parse", "HEAD"], capture_output=True,
                                            text=True, check=True).stdout.strip()
        out["onejev_dirty"] = subprocess.run(["git", "-C", str(git), "status", "--short"], capture_output=True,
                                             text=True).stdout.split("\n")
    except (OSError, subprocess.CalledProcessError) as exc:
        out["onejev_head"] = f"unknown ({exc})"
    out["sha256"] = {f"qev/{n}": hashlib.sha256((root / n).read_bytes()).hexdigest()[:16]
                     for n in ("engine.py", "prompt.py", "server.py", "readout.py", "schema.py")}
    for n in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "readout.json", "config.json"):
        p = Path(model_path) / n
        if p.exists():
            out["sha256"][n] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out


def transform(name: str, text: str, state_is_str: bool) -> str:
    from qev.prompt import render_entry, render_state

    if name in ("state", "block"):
        return render_state(text) if state_is_str else json.dumps(text, ensure_ascii=False)[1:-1]
    return render_entry(text)


def check(eng, record, client, rcfg, item: dict) -> dict:
    from qev.schema import MAX_CHOICE_OPTIONS

    body, pieces = item["body"], item.get("pieces") or {}
    record.clear()
    status, error = "ok", None
    try:
        r = client.post("/v1/systemone", content=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        status, error = "refused", f"HTTP {r.status_code}: {r.text}"
    except _Stop:
        pass
    limits = {"max_branch_tokens": eng.max_branch_tokens, "max_request_tokens": eng.max_request_tokens,
              "max_slots": eng.max_slots, "max_choice_options": MAX_CHOICE_OPTIONS}
    out = {"id": item["id"], "status": status, "error": error, "sequences": [], "limits": limits, "cut": False,
           "missing": [], "transformed": [], "roundtrip": False}
    if not record:  # refused before rendering (validation, model name)
        out["missing"] = sorted(pieces)
        return out
    from qev.engine import NONE_OPTION

    rendered, prefix_ids, suffixes = record["rendered"], record["prefix_ids"], record["suffixes"]
    out["sequences"] = [len(prefix_ids) + len(s) for s in suffixes]
    out["cut"] = any(NONE_OPTION in r.labels and NONE_OPTION not in (body["questions"][r.qid].get("criteria") or {})
                     for r in rendered)
    texts = [eng._render_prompt(record["state"], r.suffix) for r in rendered]
    out["roundtrip"] = all(eng.tokenizer.decode(prefix_ids + s, skip_special_tokens=False) == t
                           for s, t in zip(suffixes, texts))
    state_is_str = isinstance(record["state"], str)
    for name, text in pieces.items():
        t = transform(name, text, state_is_str)
        if t != text:
            out["transformed"].append(name)
        if not all(t in x for x in texts):
            out["missing"].append(name)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="the snapshot directory (the server's --checkpoint)")
    ap.add_argument("--name", required=True, help="the server's --name, e.g. baselabs/elephant-1")
    a = ap.parse_args()
    stdout, sys.stdout = sys.stdout, sys.stderr  # stdout carries only the JSONL results
    model = str(Path(a.model).resolve())
    if not (Path(model) / "readout.json").is_file():
        raise SystemExit(f"{model} has no readout.json: give the downloaded snapshot directory")

    from fastapi.testclient import TestClient
    from qev.server import create_app

    eng, record, rcfg = build_engine(model)
    print(json.dumps({"provenance": provenance(model, rcfg), "model": a.name,
                      "max_slots": eng.max_slots, "debias": os.environ.get("QEV_DEBIAS", "1")}), file=sys.stderr)
    with TestClient(create_app(eng, model_name=a.name), raise_server_exceptions=True) as client:
        for line in sys.stdin:
            if line.strip():
                stdout.write(json.dumps(check(eng, record, client, rcfg, json.loads(line))) + "\n")
                stdout.flush()


if __name__ == "__main__":
    main()
