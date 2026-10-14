#!/usr/bin/env python3
"""Replays recorded league positions to every decision model, for building and testing teams.

    python3 tools/replay.py sample --db league.db --eval gnubg_eval.db --out replay.db --count 1000
    JEV_API_KEY=... OPENAI_API_KEY=... python3 tools/replay.py ask --out replay.db

`sample` picks recorded decisions (leagues 8, 11, 12 and 13 by default) that were sent as a
single request with at most 25 legal plays, so every model can answer them in one request
(the smallest option limit is the local Decider's 25), and stores the exact state text and
options the original model saw. `ask` sends each stored position to every model in MODELS and
stores the full probability distribution it returns; it can be stopped and run again, and only
asks what is missing. Every option's equity is then added by tools/gnubg_eval.py in replay
mode, so any team rule can be scored offline from `replay.db`.

Standard library only.
"""

import argparse
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

MAX_OPTIONS = 25

# name: (url, model field or None, OpenAI Decisions format, key variable, parallel requests)
MODELS = {
    "Jev 1.13.0": ("https://api.typesafe.ai/v1/systemone", "jev-1.13.0", False, "JEV_API_KEY", 4),
    "GPT-6 Luna": ("https://api.openai.com/v1/decisions", "gpt-6-luna", True, "OPENAI_API_KEY", 4),
    "Decider v1.1 27B": ("http://127.0.0.1:18097/v1/systemone", "pplx-decider-v1.1-27b", False, None, 1),
    "Clef": ("http://127.0.0.1:18091/v1/systemone", "clef", False, None, 1),
    "Open-Jev 27B": ("http://127.0.0.1:8791/v1/systemone", None, False, None, 1),
    "Cygnet": ("http://127.0.0.1:18093/v1/systemone", "cygnet", False, None, 4),
    "Gemma 4 31B": ("http://127.0.0.1:18094/v1/systemone", "gemma-4-31B-it", False, None, 4),
    # DeepSeek V4.1 Flash (SGLang) behind Cygnet's letter-reading server and
    # tools/sglang_choice_proxy.py; calibration temperature off (1.0).
    "DeepSeek V4.1 Flash": ("http://127.0.0.1:18095/v1/systemone", "deepseek-v4.1-flash", False, None, 4),
    # Qwen3.8-Flash-Next-FP8 (vLLM, TP4) behind Cygnet's letter-reading server; temperature 1.0.
    "Qwen3.8 Flash Next": ("http://127.0.0.1:18096/v1/systemone", "qwen3.8-flash-next", False, None, 4),
    # GLM-4.7-Flash (BF16, vLLM) behind Cygnet's letter-reading server; temperature 1.0.
    "GLM-4.7-Flash": ("http://127.0.0.1:18098/v1/systemone", "glm-4.7-flash", False, None, 4),
    # Gemini 3.8 Flash: no token probabilities ("Logprobs is not enabled for this model") and no way
    # to switch thinking off, so it gets Cygnet's letter prompt with the answer constrained to the
    # option letters, thinking level low, and is stored as choice only (probability 1).
    "Gemini 3.8 Flash": ("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                         "gemini-3.8-flash", False, "GEMINI_API_KEY", 4),
    # GPT-6 Astra through the ChatGPT subscription (Codex backend, login from `codex login`): Cygnet's letter
    # prompt, answer constrained to the option letters by a JSON schema, reasoning effort low. The backend
    # returns no token probabilities, so it is stored as choice only (probability 1), like Gemini.
    "GPT-6 Astra": ("https://chatgpt.com/backend-api/codex/responses", "gpt-6-astra", False, None, 4),
    # Claude Opus 5.5 through the Claude subscription (login of the Claude Code CLI): the same letter prompt,
    # answer constrained to the option letters by a JSON schema (forced tool calls are not allowed for this
    # model), effort low. Choice only.
    "Claude Opus 5.5": ("https://api.anthropic.com/v1/messages", "claude-opus-5-5", False, None, 4),
    # DeepSeek V4.1 Flash on our GPUs (SGLang, deepseek-v41.service), with reasoning: the same letter prompt,
    # answer constrained by a JSON schema, thinking on at its lowest effort ("low" = 25 of 100). Choice only.
    # Up to 8 requests in flight, the server's MAX_RUNNING_REQUESTS.
    "DeepSeek V4.1 Flash (thinking)": ("http://127.0.0.1:8010/v1/chat/completions", "deepseek-v4.1-flash", False, None, 8),
    # Gemini 4 Argon: Gemini 3.8 Flash's setup (letter prompt, answer constrained to the letters, thinking
    # level low, choice only). It has no "minimal" thinking level and returns no token probabilities.
    "Gemini 4 Argon": ("https://generativelanguage.googleapis.com/v1beta/models/gemini-4-argon:generateContent",
                       "gemini-4-argon", False, "GEMINI_API_KEY", 4),
    # The same, with the options in a seeded random order per position (see SHUFFLED), to measure the
    # effect of the v1 move-generation order.
    "Gemini 4 Argon (shuffled)": ("https://generativelanguage.googleapis.com/v1beta/models/gemini-4-argon:generateContent",
                                  "gemini-4-argon", False, "GEMINI_API_KEY", 4),
 }

# Models whose options are shown in a random order, seeded by the position id, instead of the
# move-generation order the original model saw.
SHUFFLED = {"Gemini 4 Argon (shuffled)"}


def shuffled(options, position_id):
    items = list(options.items())
    random.Random(f"order-{position_id}").shuffle(items)
    return dict(items)


SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    -- The recorded decision this position comes from (league.db turns.id).
    turn_id INTEGER UNIQUE, league_id INTEGER, played_by TEXT, plays INTEGER,
    -- White's view of the board (turns.position), side to move, dice: for the engine.
    position TEXT, side TEXT, die1 INTEGER, die2 INTEGER,
    -- Exactly what the original model was sent.
    state TEXT, instructions TEXT,
    -- JSON object: play notation -> option description.
    options TEXT
);
CREATE TABLE IF NOT EXISTS answers (
    position_id INTEGER, model TEXT,
    choice TEXT,
    -- JSON object: play notation -> probability.
    probabilities TEXT,
    latency_ms INTEGER, error TEXT,
    -- As reported by the API (Gemini, GPT-6 Astra); NULL where the service reports none.
    input_tokens INTEGER, output_tokens INTEGER,
    PRIMARY KEY (position_id, model)
);
-- Filled by tools/gnubg_eval.py in replay mode.
CREATE TABLE IF NOT EXISTS equities (
    position_id INTEGER, play TEXT, equity REAL, loss REAL,
    PRIMARY KEY (position_id, play)
);
"""


def options_of(request):
    """(state, instructions, {play: description}) from a stored request in either format."""
    q = request["questions"]
    if isinstance(q, list):
        return request["input"], q[0]["instructions"], {c["value"]: c["description"] for c in q[0]["choices"]}
    question = next(iter(q.values()))
    return request["state"], question["instructions"], question["criteria"]


def sample(args):
    out = sqlite3.connect(args.out)
    out.executescript(SCHEMA)
    ev = sqlite3.connect(f"file:{args.eval}?mode=ro", uri=True)
    leagues = [int(x) for x in args.leagues.split(",")]
    marks = ",".join("?" * len(leagues))
    candidates = [r[0] for r in ev.execute(
        f"SELECT turn_id FROM decisions WHERE league_id IN ({marks}) AND plays BETWEEN 2 AND ?",
        (*leagues, MAX_OPTIONS))]
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rng = random.Random(args.seed)
    rng.shuffle(candidates)
    have = {r[0] for r in out.execute("SELECT turn_id FROM positions")}
    added = 0
    for tid in candidates:
        if len(have) + added >= args.count:
            break
        if tid in have:
            continue
        reqs = db.execute("SELECT request FROM exchanges WHERE turn_id = ?", (tid,)).fetchall()
        if len(reqs) != 1:
            continue
        lid, model = ev.execute("SELECT league_id, model FROM decisions WHERE turn_id = ? AND league_id IN (%s)" % marks,
                                (tid, *leagues)).fetchone()
        position, side, d1, d2, plays = db.execute(
            "SELECT position, side, die1, die2, legal_count FROM turns WHERE id = ?", (tid,)).fetchone()
        state, instructions, options = options_of(json.loads(reqs[0][0]))
        if len(options) != plays:
            continue
        out.execute("INSERT INTO positions (turn_id, league_id, played_by, plays, position, side, die1, die2, state, "
                    "instructions, options) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (tid, lid, model, plays, position, side, d1, d2, state, instructions, json.dumps(options)))
        added += 1
    out.commit()
    print(f"{added} positions added, {len(have) + added} in {args.out}")


GEMINI = "generativelanguage.googleapis.com"
CODEX = "chatgpt.com/backend-api/codex"
CODEX_AUTH = os.path.expanduser("~/.codex/auth.json")
ANTHROPIC = "api.anthropic.com"
SGLANG_THINKING = "127.0.0.1:8010/v1/chat/completions"
CLAUDE_AUTH = os.path.expanduser("~/.claude/.credentials.json")
# Anthropic serves subscription tokens only when this is the first system block.
CLAUDE_CODE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
SESSION = str(uuid.uuid4())


def letter_schema(letters):
    return {"type": "object", "properties": {"choice": {"type": "string", "enum": list(letters)}},
            "required": ["choice"], "additionalProperties": False}


def letter_prompt(state, instructions, options):
    """Cygnet's letter prompt (the one Gemma, DeepSeek and Qwen get) and the letter -> play map."""
    sys.path.insert(0, os.environ.get("CYGNET_SHIM", os.path.expanduser("~/code/cygnet/shim")))
    import cygnet_shim as shim
    opts = [(shim.LETTERS[i], k, v) for i, (k, v) in enumerate(options.items())]
    return shim.SYSTEM, shim.build_prompt(state, instructions, opts), {l: k for l, k, _ in opts}


def body(model, state, instructions, options):
    url, name, openai, _, _ = MODELS[model]
    if GEMINI in url:
        system, prompt, letters = letter_prompt(state, instructions, options)
        return {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "text/x.enum",
                                     "responseSchema": {"type": "STRING", "enum": list(letters)},
                                     "temperature": 1.0, "thinkingConfig": {"thinkingLevel": "low"}},
                "_letters": letters}
    if CODEX in url:
        system, prompt, letters = letter_prompt(state, instructions, options)
        return {"model": name, "instructions": system,
                "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                "reasoning": {"effort": "low"}, "stream": True, "store": False,
                "text": {"format": {"type": "json_schema", "name": "backgammon_play",
                                    "schema": letter_schema(letters), "strict": True}},
                "_letters": letters}
    if SGLANG_THINKING in url:
        system, prompt, letters = letter_prompt(state, instructions, options)
        return {"model": name, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                "temperature": 1.0, "max_tokens": 32768, "reasoning_effort": "low",
                "chat_template_kwargs": {"thinking": True},
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "play", "schema": letter_schema(letters), "strict": True}},
                "_letters": letters}
    if ANTHROPIC in url:
        system, prompt, letters = letter_prompt(state, instructions, options)
        return {"model": name, "max_tokens": 1024,
                "system": [{"type": "text", "text": CLAUDE_CODE_IDENTITY}, {"type": "text", "text": system}],
                "messages": [{"role": "user", "content": prompt}],
                "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": letter_schema(letters)}},
                "_letters": letters}
    b = {} if name is None else {"model": name}
    if openai:
        b["input"] = state
        b["questions"] = [{"type": "choice", "name": "play", "instructions": instructions,
                           "choices": [{"value": k, "description": v} for k, v in options.items()]}]
    else:
        b["state"] = state
        b["questions"] = {"play": {"type": "choice", "instructions": instructions, "criteria": options}}
    return b


def codex_reply(stream):
    """Text and (input, output) tokens from a Codex responses SSE stream, as in src/players/llm.rs."""
    text, done, usage = "", None, None
    for line in stream.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "response.output_text.delta":
            text += event.get("delta", "")
        elif kind == "response.output_text.done":
            done = event.get("text")
        elif kind == "response.completed":
            usage = event["response"].get("usage") or {}
        elif kind in ("response.failed", "response.incomplete", "error"):
            raise RuntimeError(f"Codex response failed: {line[:300]}")
    if usage is None:
        raise RuntimeError("Codex stream ended before response.completed")
    return done if done is not None else text, (usage.get("input_tokens"), usage.get("output_tokens"))


def parse(model, text, letters=None):
    """(choice, {play: probability}, (input tokens, output tokens))."""
    url = MODELS[model][0]
    if GEMINI in url or CODEX in url or ANTHROPIC in url or SGLANG_THINKING in url:
        if SGLANG_THINKING in url:
            r = json.loads(text)
            letter = json.loads(r["choices"][0]["message"]["content"])["choice"]
            u = r.get("usage", {})
            tokens = (u.get("prompt_tokens"), u.get("completion_tokens"))
        elif ANTHROPIC in url:
            r = json.loads(text)
            letter = json.loads(next(c["text"] for c in r["content"] if c["type"] == "text"))["choice"]
            u = r.get("usage", {})
            tokens = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                      u.get("output_tokens"))
        elif GEMINI in url:
            r = json.loads(text)
            letter = r["candidates"][0]["content"]["parts"][-1]["text"].strip()
            u = r.get("usageMetadata", {})
            tokens = (u.get("promptTokenCount"), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0))
        else:
            reply, tokens = codex_reply(text)
            letter = json.loads(reply)["choice"]
        if letter not in letters:
            return None, None, tokens
        return letters[letter], {letters[letter]: 1.0}, tokens
    a = json.loads(text)["answers"]
    if MODELS[model][2]:
        a = next(x for x in a if x.get("name") == "play")
        if a.get("type") == "refusal":
            return None, None, (None, None)
        return a["choice"], {p["value"]: p["probability"] for p in a["probabilities"]}, (None, None)
    a = a["play"]
    return a["choice"], a["probabilities"], (None, None)


def send(model, payload):
    """POST with retries on 408/425/429/5xx and network errors (1 s doubling to 60 s, 10 tries)."""
    url, _, _, key_var, _ = MODELS[model]
    headers = {"Content-Type": "application/json"}
    if key_var and GEMINI in url:
        headers["x-goog-api-key"] = os.environ[key_var]
    elif key_var:
        headers["Authorization"] = f"Bearer {os.environ[key_var]}"
    elif ANTHROPIC in url:
        token = json.load(open(CLAUDE_AUTH))["claudeAiOauth"]["accessToken"]
        headers.update({"Authorization": f"Bearer {token}", "anthropic-version": "2023-06-01",
                        "anthropic-beta": "claude-code-20250219,oauth-2025-04-20"})
    elif CODEX in url:
        # ChatGPT subscription login of the Codex CLI (`codex login`); not refreshed here.
        tokens = json.load(open(CODEX_AUTH))["tokens"]
        headers.update({"Authorization": f"Bearer {tokens['access_token']}", "OAI-Product-Sku": "codex",
                        "originator": "codex_cli_rs", "session_id": SESSION, "accept": "text/event-stream",
                        "ChatGPT-Account-Id": tokens["account_id"]})
    data = json.dumps({k: v for k, v in payload.items() if not k.startswith("_")}).encode()
    wait = 1
    for attempt in range(10):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=3600) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            if e.code not in (408, 409, 425, 429, 529) and e.code < 500 or attempt == 9:
                raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 9:
                raise RuntimeError(f"network: {e}")
        time.sleep(wait)
        wait = min(wait * 2, 60)


def ask(args):
    out = sqlite3.connect(args.out, check_same_thread=False)
    out.executescript(SCHEMA)
    columns = {r[1] for r in out.execute("PRAGMA table_info(answers)")}
    for column in ("input_tokens", "output_tokens"):
        if column not in columns:
            out.execute(f"ALTER TABLE answers ADD COLUMN {column} INTEGER")
    lock = threading.Lock()
    models = [m for m in MODELS if not args.models or m in args.models.split(",")]
    for m in models:
        key = MODELS[m][3]
        if key and not os.environ.get(key):
            raise SystemExit(f"{m} needs {key}")
    positions = out.execute("SELECT id, state, instructions, options FROM positions ORDER BY id").fetchall()
    if args.limit:
        positions = positions[:args.limit]
    done = {(p, m) for p, m in out.execute("SELECT position_id, model FROM answers WHERE error IS NULL")}
    counts = {m: 0 for m in models}

    def one(model, pid, state, instructions, options):
        started = time.monotonic()
        try:
            options = json.loads(options)
            if model in SHUFFLED:
                options = shuffled(options, pid)
            payload = body(model, state, instructions, options)
            text = send(model, payload)
            choice, probs, tokens = parse(model, text, payload.get("_letters"))
            error = None if choice is not None else "refusal"
        except Exception as e:  # stored and retried on the next run
            choice, probs, tokens, error = None, None, (None, None), str(e)[:500]
        ms = int(1000 * (time.monotonic() - started))
        with lock:
            out.execute("INSERT OR REPLACE INTO answers (position_id, model, choice, probabilities, latency_ms, error, "
                        "input_tokens, output_tokens) VALUES (?,?,?,?,?,?,?,?)",
                        (pid, model, choice, json.dumps(probs) if probs else None, ms, error, *tokens))
            counts[model] += 1
            if sum(counts.values()) % 10 == 0:
                out.commit()
                print(" ".join(f"{m.split()[0]}:{n}" for m, n in counts.items()), flush=True)

    pools = {m: ThreadPoolExecutor(MODELS[m][4]) for m in models}
    futures = [pools[m].submit(one, m, *p) for p in positions for m in models if (p[0], m) not in done]
    for f in futures:
        f.result()
    out.commit()
    errors = out.execute("SELECT model, COUNT(*) FROM answers WHERE error IS NOT NULL GROUP BY 1").fetchall()
    print("done;", f"{len(futures)} requests;", "errors:", errors or "none")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--db", default="league.db")
    s.add_argument("--eval", default="gnubg_eval.db")
    s.add_argument("--out", default="replay.db")
    s.add_argument("--leagues", default="8,11,12,13")
    s.add_argument("--count", type=int, default=1000)
    s.add_argument("--seed", type=int, default=1)
    a = sub.add_parser("ask")
    a.add_argument("--out", default="replay.db")
    a.add_argument("--models", help="comma-separated subset of model names")
    a.add_argument("--limit", type=int, help="only the first N positions (by id)")
    args = p.parse_args()
    {"sample": sample, "ask": ask}[args.cmd](args)


if __name__ == "__main__":
    main()
