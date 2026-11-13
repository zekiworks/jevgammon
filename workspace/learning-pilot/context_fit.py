"""Context fit for the learning runs of the small models (Ümit #6225): CPU only, no model call, no GPU.

    python3 workspace/learning-pilot/context_fit.py chat [--json PATH]      # LFM3-1.7B (on), MiniCPM5-2B (on)
    python3 workspace/learning-pilot/context_fit.py decision [--json PATH]  # the 13 decision models

chat: for every keyed config in configs/ (configs/<key>.json, run by pilot.py with PILOT_CONFIG), the Gemma pilot's
stored requests rendered through the model's own chat template (the pinned snapshot's chat_template.jinja, with the
config's chat_template_kwargs and the generation prompt, as the reasoning request of the runner's (on) readout sends
them) and counted with its own tokenizer: the largest T0 evaluation prompt (the config's prompt_max), the longest
stored pilot request (a records-arm T10 evaluation at Gemma's 26,879-token context limit), and the largest stored
records context. A request fits when its prompt plus the reasoning allowance (max_output_tokens) is within the
server's context per sequence (context_limit).

decision: one full game record as the pilot's records arm feeds it (records_text of a single game: delimiters,
intro, header and every decision line) from the Gemma pilot's stored records contexts (the largest and the median
game), put at the start of `state` as the decision runner places a block (improve-decision-small,
src/players/decision.rs state_with_block: block.trim_end() + blank line + state), on each model's largest and median
League 1 request (v3.db, its own setup; the largest League 1 request of the cohort for a model with no league record),
counted with the model's own tokenizer: GLiDE 2B/0.8B through their snapshot's own prompt renderer (glide/model.py
_prepare, prompt.Prompter, ~/code/glide/.venv), every other model on the plain text (state, instructions, one
"key: description" line per option; its server's wrapper tokens not added). Each total is compared with the limit
the model's server or card states (player notes, server code, config).

Inputs, read-only: PILOT_SOURCE (default the main checkout, where the pilot's private files are kept):
smoke/learning-pilot.db and workspace/learning-pilot/runs/records/s*/contexts; v3.db; tokenizers in the Hugging Face
cache and in ~/.cache/small-bench-tok (tokenizer and server files copied from spark2's snapshots, no weights).
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("PILOT_SOURCE", "/home/cbasaran/code/jevgammon"))
PILOT_DB = SOURCE / "smoke/learning-pilot.db"
RECORDS = SOURCE / "workspace/learning-pilot/runs/records"
V3_DB = Path(os.environ.get("V3_DB", "/home/cbasaran/code/jevgammon/v3.db"))
HUB = Path.home() / ".cache/huggingface/hub"
COPIES = Path.home() / ".cache/small-bench-tok"
GEMMA_TOKENIZER = "/home/cbasaran/code/models/gemma-4-31B-it/tokenizer.json"
GLIDE_PYTHON = Path.home() / "code/glide/.venv/bin/python"
OPEN = "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
CLOSE = "=== END OF NOTES ==="
RECORDS_INTRO = ("Below are the records of your earlier games in this series against the same opponent: each decision "
                 "you made, with the GNU Backgammon engine's evaluation of it (2-ply). Boards are given in your point "
                 "numbering.")
GAME_HEADER = re.compile(r"^Game \d+ \(")
CANDIDATES = 40  # longest stored pilot requests (by bytes) rendered per table


# --- Tokenizers --------------------------------------------------------------------------------------------------

_TOKS = {}


def tokenizer(path):
    if path not in _TOKS:
        from tokenizers import Tokenizer
        t = Tokenizer.from_file(str(path))
        t.no_truncation()  # a tokenizer.json may carry the model's cut (Strands: 4,096); every token is counted here
        t.no_padding()
        _TOKS[path] = t
    return _TOKS[path]


def count(path, text, special=False):
    return len(tokenizer(path).encode(text, add_special_tokens=special).ids) if text else 0


def render_chat(snapshot, messages, kwargs):
    """The chat template of the pinned snapshot, as the server applies it to the reasoning request (generation
    prompt on, the request's chat_template_kwargs)."""
    from transformers.utils.chat_template_utils import render_jinja_template
    tc = json.loads((Path(snapshot) / "tokenizer_config.json").read_text())
    out, _ = render_jinja_template(conversations=[messages], chat_template=(Path(snapshot) / "chat_template.jinja")
                                   .read_text(), add_generation_prompt=True, bos_token=tc.get("bos_token") or "",
                                   eos_token=tc.get("eos_token"), **kwargs)
    return out[0]


# --- The Gemma pilot's stored inputs -----------------------------------------------------------------------------

def pilot_requests():
    """(kind, id, setup, messages) of the T0 evaluation requests and of the longest stored requests (games and
    evaluations); system + user only (the prefilled answer of Gemma's (off) readout is not part of the prompt)."""
    db = sqlite3.connect(f"file:{PILOT_DB}?mode=ro", uri=True)
    rows = [("t0",) + r for r in db.execute(
        "SELECT ae.id, a.setup, ae.request FROM answer_exchanges ae JOIN answers a ON a.id = ae.answer_id "
        "WHERE a.setup LIKE '% | T0 shared'")]
    rows += [("evaluation",) + r for r in db.execute(
        "SELECT ae.id, a.setup, ae.request FROM answer_exchanges ae JOIN answers a ON a.id = ae.answer_id "
        "ORDER BY length(ae.request) DESC LIMIT ?", (CANDIDATES,))]
    rows += [("game",) + r for r in db.execute(
        "SELECT x.id, m.model1, x.request FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games g "
        "ON g.id = t.game_id JOIN matches m ON m.id = g.match_id ORDER BY length(x.request) DESC LIMIT ?",
        (CANDIDATES,))]
    db.close()
    return [(k, i, s, json.loads(r)["messages"][:2]) for k, i, s, r in rows]


def records_contexts():
    return sorted(RECORDS.glob("s*/contexts/after-g*.txt"))


def game_records():
    """Every single-game record of the records arm, wrapped as the arm feeds one game (records_text of one game):
    {(series, header): text}. A game's block is the same in every context that shows it."""
    out = {}
    for f in records_contexts():
        series = f.parts[-3]
        lines = f.read_text().splitlines()
        if not lines or lines[0] != OPEN:
            continue
        body = lines[3:lines.index(CLOSE)]
        starts = [i for i, x in enumerate(body) if GAME_HEADER.match(x)] + [len(body)]
        for a, b in zip(starts, starts[1:]):
            block = [x for x in body[a:b] if x]
            out.setdefault((series, block[0]), "\n".join([OPEN, RECORDS_INTRO, ""] + block + ["", CLOSE]))
    return out


def largest_and_median(records):
    """The largest and the median single-game record by characters (the same two texts for every model)."""
    texts = sorted(records.items(), key=lambda kv: (len(kv[1]), kv[0]))
    return dict(largest=texts[-1], median=texts[(len(texts) - 1) // 2])


# --- Chat models -------------------------------------------------------------------------------------------------

def chat_configs():
    return [json.loads(p.read_text()) | dict(path=p.name) for p in sorted((HERE / "configs").glob("*.json"))
            if "key" in json.loads(p.read_text()) and json.loads(p.read_text()).get("mode") != "decision"]


def chat_fit(cfg, requests=None, contexts=None):
    requests = requests if requests is not None else pilot_requests()
    contexts = contexts if contexts is not None else records_contexts()
    snap = Path(cfg["tokenizer_file"]).parent
    kwargs = cfg["players"][0].get("request", {}).get("chat_template_kwargs", {})
    tok = cfg["tokenizer_file"]
    t0, longest = None, None
    for kind, xid, setup, messages in requests:
        n = count(tok, render_chat(snap, messages, kwargs))
        row = dict(kind=kind, id=xid, setup=setup, tokens=n, chars=sum(len(m["content"]) for m in messages))
        if kind == "t0" and (t0 is None or n > t0["tokens"]):
            t0 = row
        if longest is None or n > longest["tokens"]:
            longest = row
    big = sorted(contexts, key=lambda p: p.stat().st_size, reverse=True)[:10]
    ctx = max(((count(tok, p.read_text(), special=True), count(GEMMA_TOKENIZER, p.read_text(), special=True),
                str(p.relative_to(RECORDS))) for p in big), default=(0, 0, None))
    limit, out_tokens = cfg["context_limit"], cfg["max_output_tokens"]
    budget = limit - out_tokens - t0["tokens"] - 1500
    return dict(model=cfg["players"][0]["name"], config=cfg["path"], tokenizer=cfg["tokenizer_source"],
                served_context=limit, max_output_tokens=out_tokens, prompt_max_t0=t0, longest_stored_request=longest,
                longest_needs=longest["tokens"] + out_tokens, longest_fits=longest["tokens"] + out_tokens <= limit,
                note_budget=budget, config_prompt_max=cfg.get("prompt_max"),
                largest_records_context=dict(file=ctx[2], tokens=ctx[0], gemma_tokens=ctx[1],
                                             fits_note_budget=ctx[0] <= budget))


# --- Decision models ---------------------------------------------------------------------------------------------

def snap(repo, rev):
    return HUB / f"models--{repo.replace('/', '--')}/snapshots/{rev}"


def copy(name):
    return COPIES / name


# limit: what the total is compared with; skip_reason: why a fitting total would still not deliver the block.
DECISION = [
    dict(key="d1-2b", name="d1-2B (LiquidAI/d1-2B)", setup=None, source="LiquidAI/d1-2B@10e7671d",
         tok=snap("LiquidAI/d1-2B", "10e7671d44e4b37700020b1eed3f594c5f2af0b4") / "tokenizer.json", method="plain",
         limit=128000, limit_basis="card 'Context length 128,000 tokens' (config text_config.max_position_embeddings "
         "128,000); card: answers less reliable past ~64K tokens of state",
         route="no backgammon route or League 1 record (logic: no d1 environment on spark2; bariton card)"),
    dict(key="glide-2b", name="GLiDE 2B", setup="GLiDE 2B", source="fastino/GLiDE-2B@00f122c1",
         tok=snap("fastino/GLiDE-2B", "00f122c120cdeed82284106cb77d9bab5a50ad16"), method="glide",
         limit=40000 - 8, limit_basis="glide.server GLIDE_MAX_LEN 40,000: a question prompt of len + 8 > 40,000 is "
         "refused (422), never cut"),
    dict(key="glide-0.8b", name="GLiDE 0.8B", setup="GLiDE 0.8B", source="fastino/GLiDE-0.8B@9eacdeec",
         tok=snap("fastino/GLiDE-0.8B", "9eacdeec79fa48ec52a8d6f54b331376b4bbfaf0"), method="glide",
         limit=40000 - 8, limit_basis="glide.server GLIDE_MAX_LEN 40,000 (as GLiDE 2B)"),
    dict(key="glide-0.4b", name="GLiDE 0.4B", setup="GLiDE 0.4B", source="fastino/GLiDE-0.4B@6bda7ab9",
         tok=snap("fastino/GLiDE-0.4B", "6bda7ab91aeb36dcad6d27828a8871e548c7fc71") / "tokenizer.json",
         method="plain", limit=7999, limit_basis="encoder max_len 7,999 (glide/encoder.py would shorten a longer "
         "prompt to the first 1,024 tokens + the tail); served with GLIDE_MAX_LEN=8006, which refuses (422) such a "
         "prompt before it is shortened; plain text undercounts the card's prompt (League 1 largest: 7,833 with it)"),
    dict(key="knowline-4b", name="KnowLine 4B Gen5.5", setup="KnowLine 4B Gen5.5",
         source="PelaAI/KnowLine-4B-Gen5.5@779944d2",
         tok=copy("KnowLine-4B-Gen5.5@779944d2cc8ffa19cef386aee83c83bcb967ade2/tokenizer.json"), method="plain",
         limit=262144 - 6, limit_basis="SGLang context 262,144 - 6, refused above (no --allow-auto-truncate)",
         twice=3000),
    dict(key="knowline-2b", name="KnowLine-2B-Gen1", setup="KnowLine-2B-Gen1",
         source="PelaAI/KnowLine-2B-Gen1@53245d47",
         tok=copy("KnowLine-2B-Gen1@53245d470a4ce316e32fd0d18c24e142c697f40b/tokenizer.json"), method="plain",
         limit=262144 - 6, limit_basis="SGLang context 262,144 - 6, refused above", twice=3000),
    dict(key="knowline-0.8b", name="KnowLine-0.8B-Gen1", setup="KnowLine-0.8B-Gen1",
         source="PelaAI/KnowLine-0.8B-Gen1@6b27831f",
         tok=copy("KnowLine-0.8B-Gen1@6b27831f7b783c03278bd946d4d8f4f7a98a3798/tokenizer.json"), method="plain",
         limit=262144 - 6, limit_basis="SGLang context 262,144 - 6, refused above", twice=3000),
    dict(key="startlux-2b", name="StartLux-Decision v1.1 2B (Instant)", setup="StartLux-Decision v1.1 2B",
         source="startlux-models/StartLux-Decision-v1.1-2B-Instant@f1e6cd14",
         tok=copy("StartLux-Decision-v1.1-2B-Instant@f1e6cd147dda82c9ffa3e8e725d5c1f175566fb1/tokenizer.json"),
         method="plain", limit=131072, limit_basis="startlux-decide --launch-vllm: Instant folders served at "
         "131,072 (launch.py), vLLM refuses above; each pass holds the state and <= 25 options (whole request "
         "counted here: an upper bound)"),
    dict(key="startlux-0.8b", name="StartLux-Decision-v1.1-0.8B-Instant", setup="StartLux-Decision-v1.1-0.8B-Instant",
         source="startlux-models/StartLux-Decision-v1.1-0.8B-Instant@6496ae64",
         tok=copy("StartLux-Decision-v1.1-0.8B-Instant@6496ae641cc71b149ce9dad69bd97f2a44e7bf11/tokenizer.json"),
         method="plain", limit=131072, limit_basis="as StartLux 2B: 131,072, refused above"),
    dict(key="onejev1.6-0.8b", name="OneJev1.6-0.8B", setup="OneJev1.6-0.8B", source="OmniJev/OneJev1.6-0.8B@bcd88a38",
         tok=copy("OneJev1.6-0.8B@bcd88a382f314b26cb7b1b7f369c1ed3502ee7a0/tokenizer.json"), method="plain",
         limit=32768, limit_basis="flide serve (onejev-slot-v2): state + one question over 32,768 tokens is refused "
         "(422); a request over 65,536"),
    dict(key="strands", name="Strands Decider 2B", setup=None,
         source="StrandsAgents/strands-decider-2B-hobson-v21@2b52a623",
         tok=Path.home() / "code/strands-decider/model/tokenizer.json", method="plain", limit=4096,
         limit_basis="strands_decider_config.json max_length 4,096; served with --strict-window (late-tiny8-small3 "
         "8ebad40): a prompt over 4,096 tokens is refused (422), never cut; max_choices 13",
         route="no League 1 record (late entry prepared on late-tiny8-small3, not started)"),
    dict(key="decider-flash-v1.2", name="Decider Flash v1.2", setup="Decider Flash v1.2",
         source="perplexity-ai/pplx-decider-flash-v1.2 (release-manifest repo_id; checkpoint "
         "~/code/pplx-decider/checkpoint-flash-v1.2, no HF cache revision)",
         tok=Path.home() / "code/pplx-decider/checkpoint-flash-v1.2/tokenizer.json", method="plain",
         limit=262144, limit_basis="pplx_decider model.py DEFAULT_MAX_LENGTH 262,144 (lr/decider.py): the encoder "
         "bisects the questions past it, a single question over it is refused (400), nothing truncated"),
    dict(key="metask", name="Metask-Jev-4B", setup=None, source="metask-ai/metask-jev@ea20fe85",
         tok=Path.home() / "code/metask-jev/model/tokenizer.json", method="plain", limit=4096,
         limit_basis="~/code/metask-jev/server.py MAX_INPUT_TOKENS 4,096 (jev_schema: longer prompts refused, "
         "nothing truncated)", route="no backgammon route or League 1 record"),
    dict(key="gliclass-v4-edge", name="GLiClass v4 Edge", setup="GLiClass v4 Edge",
         source="knowledgator/gliclass-v4-edge@885af1af",
         tok=copy("gliclass-v4-edge@885af1af8a07edf4ed34df83ca0d995ed8201283/tokenizer.json"), method="plain",
         limit=16384, limit_basis="gliclass_server.py: state, instructions and up to max_choices 218 labels share "
         "one 16,384-token input, refused (422) above, never cut", labels="description"),
]


def league_requests(setup):
    """The setup's largest and median stored League 1 request (valid matches, with a response), by bytes."""
    db = sqlite3.connect(f"file:{V3_DB}?mode=ro", uri=True, timeout=60)
    (pid,) = db.execute("SELECT id FROM players WHERE name = ?", (setup,)).fetchone()
    sizes = db.execute(
        "SELECT x.id, length(CAST(x.request AS BLOB)) FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games gm "
        "ON gm.id = t.game_id JOIN matches m ON m.id = gm.match_id WHERE m.valid = 1 AND x.response IS NOT NULL AND "
        "((m.player1 = ? AND t.player = 1) OR (m.player2 = ? AND t.player = 2)) ORDER BY 2 DESC, 1", (pid, pid)
    ).fetchall()
    pick = dict(largest=sizes[0], median=sizes[(len(sizes) - 1) // 2])
    out = {}
    for k, (xid, n) in pick.items():
        (body,) = db.execute("SELECT request FROM exchanges WHERE id = ?", (xid,)).fetchone()
        out[k] = dict(exchange=xid, bytes=n, body=json.loads(body))
    db.close()
    return out, len(sizes)


def with_block(body, block):
    return dict(body, state=f"{block.rstrip()}\n\n{body['state']}" if block else body["state"])


def league_request_bodies(setup):
    """Every stored League 1 request of the setup (valid matches, with a response)."""
    db = sqlite3.connect(f"file:{V3_DB}?mode=ro", uri=True, timeout=60)
    (pid,) = db.execute("SELECT id FROM players WHERE name = ?", (setup,)).fetchone()
    rows = [json.loads(r) for (r,) in db.execute(
        "SELECT x.request FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games gm ON gm.id = t.game_id JOIN "
        "matches m ON m.id = gm.match_id WHERE m.valid = 1 AND x.response IS NOT NULL AND ((m.player1 = ? AND "
        "t.player = 1) OR (m.player2 = ? AND t.player = 2))", (pid, pid))]
    db.close()
    return rows


def over_limit(m, records):
    """For a partial fit: how many of the setup's stored League 1 requests pass the limit with each game record."""
    bodies = league_request_bodies(m["setup"])
    out = dict(requests=len(bodies))
    for g in ("median", "largest"):
        out[g] = sum(count(m["tok"], plain_text(with_block(b, records[g][1]), m.get("labels", "key"))) > m["limit"]
                     for b in bodies)
    return out


def plain_text(body, labels="key"):
    """state, then per question its instructions and one line per option: 'key: description', or the description
    alone (labels='description': GLiClass, whose labels are the descriptions)."""
    parts = [body["state"]]
    for q in body["questions"].values():
        crit = q.get("criteria") or {}
        items = crit.items() if isinstance(crit, dict) else ((str(i), c) for i, c in enumerate(crit))
        lines = [v if labels == "description" else f"{k}: {v}" for k, v in items]
        parts.append("\n".join([q.get("instructions") or ""] + lines))
    return "\n\n".join(parts)


def glide_tokens(snapshot, bodies):
    """Token count of the longest question prompt of each body through the snapshot's own renderer."""
    payload = "".join(json.dumps(b, ensure_ascii=False) + "\n" for b in bodies)
    r = subprocess.run([str(GLIDE_PYTHON), str(Path(__file__).resolve()), "glide-render", "--model", str(snapshot)],
                       input=payload, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(snapshot)))
    if r.returncode != 0:
        raise RuntimeError(f"glide renderer failed: {r.stderr[-2000:]}")
    return [json.loads(x)["tokens"] for x in r.stdout.splitlines() if x.strip()]


def glide_render(model):
    """Run under ~/code/glide/.venv with PYTHONPATH=<snapshot>: glide/model.py _prepare (prompt.Prompter.text per
    question) and the batch tokenization of decide_batch (add_special_tokens=False), as lr/glide_v12.py does."""
    import types
    from transformers import AutoTokenizer
    from glide.model import DECISION_CONFIG, Glide, _check_codes
    from glide.prompt import Prompter
    tok = AutoTokenizer.from_pretrained(model)
    config = json.loads((Path(model) / DECISION_CONFIG).read_text())
    _check_codes(tok, config)
    me = types.SimpleNamespace(prompter=Prompter(tok, list(config["codes"])), vision=False)
    for line in sys.stdin:
        if line.strip():
            body = json.loads(line)
            entries, _ = Glide._prepare(me, {"state": body["state"], "questions": body["questions"]})
            ids = tok([e[3] for e in entries], add_special_tokens=False)["input_ids"]
            print(json.dumps(dict(tokens=max(len(i) for i in ids))), flush=True)


def decision_fit(m, records, requests):
    """Token counts of one game record on the model's largest and median League 1 request, against its limit."""
    bodies = {f"{r}+{g}": with_block(requests[r]["body"], records[g][1] if g != "none" else "")
              for r in ("largest", "median") for g in ("none", "median", "largest")}
    if m["method"] == "glide":
        n = dict(zip(bodies, glide_tokens(m["tok"], list(bodies.values()))))
        tok_source = m["tok"] / "tokenizer.json"
    else:
        n = {k: count(m["tok"], plain_text(b, m.get("labels", "key"))) for k, b in bodies.items()}
        tok_source = m["tok"]
    block = {g: count(tok_source, records[g][1]) for g in ("median", "largest")}
    lim = m["limit"]
    fits = {k: v <= lim for k, v in n.items()}
    if not fits["median+median"]:
        verdict = "skip"
        why = f"a median game record on a median request is {n['median+median']:,} tokens > {lim:,}"
    elif not fits["largest+largest"]:
        verdict = "skip" if m.get("capped") else "partial"
        why = (f"the largest record on the largest request is {n['largest+largest']:,} tokens > {lim:,}"
               + (" (the excess would be cut/shortened: block not seen in full)" if m.get("capped") else
                  " (refused, not cut: those decisions fail unless the request is split further)"))
    else:
        verdict, why = "fit", f"largest record on the largest request: {n['largest+largest']:,} <= {lim:,}"
    note = []
    if m.get("twice"):
        note.append(f"read twice only up to {m['twice']:,} tokens: with the block every request is read once "
                    f"(median request alone: {n['median+none']:,} tokens)")
    if m.get("route"):
        note.append(m["route"])
    return dict(model=m["name"], key=m["key"], tokenizer=m["source"], method=m["method"], limit=lim,
                limit_basis=m["limit_basis"], block_tokens=block, tokens=n, verdict=verdict, why=why, notes=note,
                requests={k: dict(exchange=v["exchange"], bytes=v["bytes"], setup=v.get("setup"))
                          for k, v in requests.items()})


def decision_all(models=DECISION):
    records = game_records()
    pick = largest_and_median(records)
    own, cohort_largest = {}, None
    for m in models:
        if m["setup"]:
            req, n = league_requests(m["setup"])
            for v in req.values():
                v["setup"] = m["setup"]
            own[m["key"]] = req
            if cohort_largest is None or req["largest"]["bytes"] > cohort_largest["largest"]["bytes"]:
                cohort_largest = req
    rows = [decision_fit(m, pick, own.get(m["key"]) or cohort_largest) for m in models]
    for m, row in zip(models, rows):
        if row["verdict"] == "partial" and m["setup"] and m["method"] == "plain":
            row["over_limit"] = over_limit(m, pick)
    return dict(records=dict(count=len(records), largest=dict(game=list(pick["largest"][0]),
                                                              chars=len(pick["largest"][1])),
                             median=dict(game=list(pick["median"][0]), chars=len(pick["median"][1]))),
                models=rows)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("chat", "decision"):
        sub.add_parser(name).add_argument("--json")
    sub.add_parser("glide-render").add_argument("--model", required=True)
    a = ap.parse_args()
    if a.cmd == "glide-render":
        return glide_render(a.model)
    if a.cmd == "chat":
        reqs, ctxs = pilot_requests(), records_contexts()
        out = [chat_fit(c, reqs, ctxs) for c in chat_configs()]
    else:
        out = decision_all()
    text = json.dumps(out, indent=1, default=str)
    if a.json:
        Path(a.json).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
