#!/usr/bin/env python3
"""Snapshot of v3.db for the site, and the prompts every league decision was sent.

    python3 tools/site/snapshot.py V3_DB STATE_DIR
    python3 tools/site/snapshot.py --verify N V3_DB STATE_DIR

1. One read transaction on V3_DB (read-only URI) copies every table except `exchanges`, indexes
   included, to STATE_DIR/snap.db.tmp, renamed to snap.db once complete (the method of
   tools/v3/page_refresh.sh step 1). In the same transaction it lists the exchanges of the
   league decisions not yet in STATE_DIR/prompts.db (seen or skipped) and reads the first batch
   of their requests.
2. The other requests are read in batches, each in its own short read transaction, so the
   leagues keep writing and the WAL can be checkpointed.
3. Each request keeps only what the model was sent as system or user content (no assistant
   turns, no API parameters). The state (decision format) or the user message (letter format) is
   split where the turn part starts ("Score: you "): the shared rules text before it is stored
   once in `contexts`, the turn part in `seen.requests`, and context + separator + text must give
   the original string back exactly. Identical requests of a decision (retries, the steps of a
   two-step reasoning flow) are kept once; group splits keep every distinct request in send order.
4. Prints one line of JSON: decisions extracted, skipped by reason, contexts, and a fingerprint
   that changes whenever the league data changes.

Schema of prompts.db: see the site contract (local://site-contract.md). Anthropic requests send
the Claude Code identity block before the system prompt: it is kept as "system_prefix" (list of
str) in that request object and, once, in meta key `anthropic_system_prefix`.

--verify N: for N random extracted decisions, re-reads the original requests and checks that
every system/user string sent equals its reconstruction from prompts.db, and that the options
match turns.legal_count / group_size and the shown order (turns.option_order over
tools/v3/rules.py legal_plays). Prints a JSON report.
"""

import hashlib
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter

# The runner's engines (src/players/mod.rs): they decide locally and send no request.
ENGINE_SPECS = {"random", "safest", "gnubg-weak"}
TURN_START = "Score: you "
# Exchanges read per batch (about 12 kB of request each); one read transaction per batch.
BATCH_EXCHANGES = 1000
PROMPTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS contexts(hash TEXT PRIMARY KEY, text TEXT);
CREATE TABLE IF NOT EXISTS seen(turn_id INTEGER PRIMARY KEY, league_id INTEGER, format TEXT,
    context TEXT, separator TEXT, requests TEXT);
CREATE TABLE IF NOT EXISTS skipped(turn_id INTEGER PRIMARY KEY, reason TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""
LEAGUE_DECISIONS = """
SELECT t.id, lm.league_id, CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END
FROM {p}turns t JOIN {p}games g ON g.id = t.game_id JOIN {p}league_match_view lm ON lm.match_id = g.match_id
JOIN {p}leagues l ON l.id = lm.league_id
WHERE t.decided_by IN ('model', 'fallback') AND {shown}
"""


def shown(db, prefix=""):
    """SQL condition on `leagues l` leaving out hidden leagues (`leagues.hidden`, e.g. an early start
    for the next ladder round; league_web.shown): the site never shows them."""
    if "hidden" not in {r[1] for r in db.execute(f"PRAGMA {prefix}table_info(leagues)")}:
        return "1"
    return "COALESCE(l.hidden, 0) = 0"


class Skip(Exception):
    """A decision that cannot be extracted; the message is the skip reason."""


def background():
    os.nice(max(0, 19 - os.nice(0)))
    subprocess.run(["ionice", "-c", "3", "-p", str(os.getpid())], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_prompts(path):
    db = sqlite3.connect(path, isolation_level=None)
    db.executescript(PROMPTS_SCHEMA)
    return db


# ---------------------------------------------------------------- request parsing


def content_text(content):
    """The text of a message content: a string, or a list of exactly one text part."""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict) \
            and content[0].get("type") in ("text", "input_text") and isinstance(content[0].get("text"), str):
        return content[0]["text"]
    raise Skip("unknown content shape")


def parse_request(body):
    """What the model was sent: ("decision", state, instructions, options) or
    ("letters", system, system_prefix, user)."""
    if "questions" in body:
        questions = body["questions"]
        if isinstance(questions, dict):  # {state, questions.play.{instructions, criteria}}
            state = body.get("state")
            if len(questions) != 1 or "play" not in questions:
                raise Skip("unknown decision question")
            play = questions["play"]
            options = [[k, v] for k, v in play["criteria"].items()]
        elif isinstance(questions, list):  # OpenAI Decisions {input, questions[{choices}]}
            state = body.get("input")
            if len(questions) != 1:
                raise Skip("unknown decision question")
            play = questions[0]
            options = [[c["value"], c["description"]] for c in play["choices"]]
        else:
            raise Skip("unknown decision question")
        if not isinstance(state, str) or not isinstance(play.get("instructions"), str) \
                or not all(isinstance(s, str) for o in options for s in o):
            raise Skip("unknown decision request")
        return ("decision", state, play["instructions"], options)
    systems, users = [], []
    if "messages" in body:  # Anthropic {system[], messages[]}, OpenAI-compatible {messages}
        if "system" in body:
            system = body["system"]
            if isinstance(system, str):
                systems.append(system)
            elif isinstance(system, list):
                for block in system:
                    if not (isinstance(block, dict) and block.get("type") == "text"):
                        raise Skip("unknown system shape")
                    systems.append(block["text"])
            else:
                raise Skip("unknown system shape")
        for message in body["messages"]:
            role = message.get("role")
            if role == "system":
                systems.append(content_text(message["content"]))
            elif role == "user":
                users.append(content_text(message["content"]))
            elif role != "assistant":
                raise Skip(f"unknown role {role}")
    elif "contents" in body:  # Gemini {systemInstruction, contents}
        for part in body.get("systemInstruction", {}).get("parts", []):
            systems.append(part["text"])
        for message in body["contents"]:
            role = message.get("role")
            if role == "user":
                parts = message.get("parts", [])
                if len(parts) != 1 or set(parts[0]) != {"text"}:
                    raise Skip("unknown content shape")
                users.append(parts[0]["text"])
            elif role != "model":
                raise Skip(f"unknown role {role}")
    elif isinstance(body.get("input"), list):  # OpenAI Responses {instructions, input[...]}
        if "instructions" in body:
            systems.append(body["instructions"])
        for message in body["input"]:
            role = message.get("role")
            if role in ("system", "developer"):
                systems.append(content_text(message["content"]))
            elif role == "user":
                users.append(content_text(message["content"]))
            elif role != "assistant":
                raise Skip(f"unknown role {role}")
    else:
        raise Skip("unknown request format")
    if len(users) != 1:
        raise Skip("not exactly one user message")
    if len(systems) > 1 and "messages" not in body:
        raise Skip("several system prompts")
    if not all(isinstance(s, str) for s in systems + users):
        raise Skip("unknown content shape")
    system = systems[-1] if systems else None
    return ("letters", system, systems[:-1], users[0])


def split_turn(text):
    """(context, separator, turn text) with context + separator + turn text == text."""
    at = text.find(TURN_START)
    if at < 0:
        raise Skip("no turn part")
    context = text[:at].rstrip()
    separator = text[len(context):at]
    turn = text[at:]
    if not context or context + separator + turn != text:
        raise Skip("split does not reproduce the text")
    return context, separator, turn


def context_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def extract(bodies, meta):
    """(format, context text, separator, requests) for one decision's request bodies in send
    order; `meta` holds the Anthropic identity block(s) seen so far."""
    parsed, kept = [], set()
    for raw in bodies:
        try:
            body = json.loads(raw)
        except ValueError:
            raise Skip("request is not JSON")
        if not isinstance(body, dict):
            raise Skip("unknown request format")
        request = parse_request(body)
        key = json.dumps(request)
        if key not in kept:
            kept.add(key)
            parsed.append(request)
    formats = {r[0] for r in parsed}
    if len(formats) != 1:
        raise Skip("mixed formats")
    fmt = formats.pop()
    contexts, requests = set(), []
    for request in parsed:
        if fmt == "decision":
            _, state, instructions, options = request
            context, separator, text = split_turn(state)
            out = {"system": None, "instructions": instructions, "text": text, "options": options}
        else:
            _, system, prefix, user = request
            context, separator, text = split_turn(user)
            out = {"system": system, "instructions": None, "text": text, "options": None}
            if prefix:
                known = meta.setdefault("anthropic_system_prefix", prefix)
                if known != prefix:
                    raise Skip("system prefix differs")
                out["system_prefix"] = prefix
        contexts.add((context, separator))
        requests.append(out)
    if len(contexts) != 1:
        raise Skip("requests differ in context")
    context, separator = contexts.pop()
    return fmt, context, separator, requests


# ---------------------------------------------------------------- snapshot and extraction


def engine_setups(db, prefix=""):
    """Names of the runner's engines (players.spec), which send no requests."""
    marks = ",".join("?" * len(ENGINE_SPECS))
    return {name for (name,) in db.execute(f"SELECT name FROM {prefix}players WHERE spec IN ({marks})",
                                            sorted(ENGINE_SPECS))}


def fingerprint(db):
    turns = db.execute("SELECT count(*), coalesce(max(id), 0) FROM turns").fetchone()
    parts = [f"t{turns[0]}/{turns[1]}"]
    # Per league: status, finished matches of its table / pairs of current participants.
    for league_id, status, done, n in db.execute(
            "SELECT l.id, l.status,"
            " (SELECT count(*) FROM league_match_view v JOIN matches m ON m.id = v.match_id"
            "  WHERE v.league_id = l.id AND m.status = 'finished'),"
            " (SELECT count(*) FROM league_players lp WHERE lp.league_id = l.id AND lp.left_at IS NULL)"
            f" FROM leagues l WHERE {shown(db)} ORDER BY l.id"):
        parts.append(f"l{league_id}:{status}:{done}/{n * (n - 1) // 2}")
    return " ".join(parts)


def fetch(db, schema, turns):
    """{turn_id: [request, ...] in send order} for `turns` = [(turn_id, [exchange id, ...])]."""
    ids = [i for _, exchange_ids in turns for i in exchange_ids]
    rows = {}
    for start in range(0, len(ids), 900):
        chunk = ids[start:start + 900]
        marks = ",".join("?" * len(chunk))
        for exchange_id, request in db.execute(
                f"SELECT id, request FROM {schema}exchanges WHERE id IN ({marks})", chunk):
            rows[exchange_id] = request
    return {turn_id: [rows[i] for i in exchange_ids if i in rows] for turn_id, exchange_ids in turns}


def store(prompts, targets, fetched, meta, counts):
    prompts.execute("BEGIN")
    for turn_id, bodies in fetched.items():
        if not bodies:  # deleted since it was listed: try again next run
            continue
        try:
            fmt, context, separator, requests = extract(bodies, meta)
        except Skip as skip:
            prompts.execute("INSERT INTO skipped VALUES (?, ?)", (turn_id, str(skip)))
            counts["skipped"][str(skip)] += 1
            continue
        digest = context_hash(context)
        prompts.execute("INSERT OR IGNORE INTO contexts VALUES (?, ?)", (digest, context))
        prompts.execute("INSERT INTO seen VALUES (?, ?, ?, ?, ?, ?)",
                        (turn_id, targets[turn_id], fmt, digest, separator,
                         json.dumps(requests, ensure_ascii=False)))
        counts["new"] += 1
        counts["formats"][fmt] += 1
    if "anthropic_system_prefix" in meta:
        prompts.execute("INSERT OR REPLACE INTO meta VALUES ('anthropic_system_prefix', ?)",
                        (json.dumps(meta["anthropic_system_prefix"], ensure_ascii=False),))
    prompts.execute("COMMIT")


def batches(listed):
    batch, size = [], 0
    for item in listed:
        batch.append(item)
        size += len(item[1])
        if size >= BATCH_EXCHANGES:
            yield batch
            batch, size = [], 0
    if batch:
        yield batch


def run(v3, state):
    started = time.monotonic()
    os.makedirs(state, exist_ok=True)
    snap, tmp = os.path.join(state, "snap.db"), os.path.join(state, "snap.db.tmp")
    prompts = open_prompts(os.path.join(state, "prompts.db"))
    done = {r[0] for r in prompts.execute("SELECT turn_id FROM seen UNION ALL SELECT turn_id FROM skipped")}
    meta = {k: json.loads(v) for k, v in prompts.execute(
        "SELECT key, value FROM meta WHERE key = 'anthropic_system_prefix'")}
    counts = {"new": 0, "skipped": Counter(), "formats": Counter()}
    source = f"file:{os.path.abspath(v3)}?mode=ro"

    # 1. Snapshot, the exchange list and the first batch: one read transaction.
    for path in (tmp, tmp + "-journal"):
        if os.path.exists(path):
            os.remove(path)
    db = sqlite3.connect(tmp, uri=True, isolation_level=None)
    db.execute("ATTACH ? AS src", (source,))
    db.execute("BEGIN")
    tables = db.execute("SELECT name, sql FROM src.sqlite_master WHERE type = 'table' AND name != 'exchanges'"
                        " AND name NOT LIKE 'sqlite_%'").fetchall()
    for name, sql in tables:
        db.execute(sql)
        db.execute(f'INSERT INTO main."{name}" SELECT * FROM src."{name}"')
    for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
                             " AND tbl_name != 'exchanges'").fetchall():
        db.execute(sql)
    # Views (league_match_view) after the tables they read: their names resolve to main's copies.
    for (sql,) in db.execute("SELECT sql FROM src.sqlite_master WHERE type = 'view' ORDER BY rowid").fetchall():
        db.execute(sql)
    engines = engine_setups(db, "main.")
    targets = {}
    for turn_id, league_id, setup in db.execute(LEAGUE_DECISIONS.format(p="main.", shown=shown(db, "main."))):
        if turn_id not in done and setup not in engines:
            targets[turn_id] = league_id
    exchanges = {}
    if targets:
        for exchange_id, turn_id, attempt in db.execute(
                "SELECT id, turn_id, attempt FROM src.exchanges WHERE turn_id >= ?", (min(targets),)):
            if turn_id in targets:
                exchanges.setdefault(turn_id, []).append((attempt, exchange_id))
    listed = [(t, [i for _, i in sorted(exchanges[t])]) for t in sorted(exchanges)]
    pending = batches(listed)
    first = next(pending, None)
    fetched = fetch(db, "src.", first) if first else {}
    db.execute("COMMIT")
    db.execute("DETACH src")
    print_fingerprint = fingerprint(db)
    db.close()
    os.replace(tmp, snap)
    snapshot_seconds = time.monotonic() - started

    # Decisions of models that sent nothing.
    missing = sorted(set(targets) - set(exchanges))
    if missing:
        prompts.execute("BEGIN")
        prompts.executemany("INSERT INTO skipped VALUES (?, 'no exchanges')", [(t,) for t in missing])
        prompts.execute("COMMIT")
        counts["skipped"]["no exchanges"] += len(missing)

    # 2. The other batches, one short read transaction each.
    if first:
        store(prompts, targets, fetched, meta, counts)
        src = sqlite3.connect(source, uri=True, isolation_level=None)
        for batch in pending:
            src.execute("BEGIN")
            fetched = fetch(src, "", batch)
            src.execute("COMMIT")
            store(prompts, targets, fetched, meta, counts)
        src.close()

    prompts.execute("INSERT OR REPLACE INTO meta VALUES ('fingerprint', ?)", (print_fingerprint,))
    prompts.execute("INSERT OR REPLACE INTO meta VALUES ('updated_at', ?)",
                    (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    summary = {
        "new": counts["new"],
        "formats": dict(counts["formats"]),
        "skipped": dict(counts["skipped"]),
        "seen_total": prompts.execute("SELECT count(*) FROM seen").fetchone()[0],
        "skipped_total": prompts.execute("SELECT count(*) FROM skipped").fetchone()[0],
        "contexts": prompts.execute("SELECT count(*) FROM contexts").fetchone()[0],
        "fingerprint": print_fingerprint,
        "snapshot_seconds": round(snapshot_seconds, 1),
        "seconds": round(time.monotonic() - started, 1),
    }
    prompts.close()
    print(json.dumps(summary))


# ---------------------------------------------------------------- verification

# Top-level request keys that carry what the model reads; everything else is an API parameter.
CONTENT_KEYS = {"system", "messages", "instructions", "input", "contents", "systemInstruction", "state",
                "questions"}
# Keys inside them that name structure, not content.
STRUCTURE_KEYS = {"type", "role", "name"}
LETTER_LINE = re.compile(r"^[A-Z]\. (.*)$")


def sent_strings(body):
    """Every string of system or user content in a request body, found by walking it (not by
    the extraction's parser): assistant/model turns and API parameters left out."""
    out = []

    def walk(value, key=None):
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            if value.get("role") in ("assistant", "model"):
                return
            for k, v in value.items():
                if k in STRUCTURE_KEYS and isinstance(v, str):
                    continue
                if key == "criteria":
                    out.append(k)
                walk(v, k)

    for key, value in body.items():
        if key in CONTENT_KEYS:
            walk(value, key)
    return out


def reconstructed(request, context, separator):
    """The strings of a stored request in the order the request body carries them."""
    text = context + separator + request["text"]
    if request["options"] is not None:  # decision: state, instructions, options
        strings = [text, request["instructions"]]
        for notation, description in request["options"]:
            strings += [notation, description]
        return strings
    system = [request["system"]] if request["system"] is not None else []
    return list(request.get("system_prefix") or []) + system + [text]


def shown(request):
    """Notations of the options of a stored request, in the order shown."""
    if request["options"] is not None:
        return [n for n, _ in request["options"]]
    lines = request["text"].split("\n\nOptions:\n", 1)[1].split("\n\n")[0].split("\n")
    out = []
    for line in lines:
        m = LETTER_LINE.match(line)
        if not m:
            raise ValueError(f"not an option line: {line[:60]}")
        out.append(m.group(1).split(": ", 1)[0])
    return out


def verify(v3, state, n):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v3"))
    from rules import from_json, legal_plays

    started = time.monotonic()
    prompts = sqlite3.connect(os.path.join(state, "prompts.db"))
    snap = sqlite3.connect(os.path.join(state, "snap.db"))
    contexts = dict(prompts.execute("SELECT hash, text FROM contexts"))
    ids = [r[0] for r in prompts.execute("SELECT turn_id FROM seen")]
    sample = sorted(random.Random(20261021).sample(ids, min(n, len(ids))))
    seen = {r[0]: r[1:] for r in prompts.execute(
        "SELECT turn_id, format, context, separator, requests FROM seen WHERE turn_id IN (%s)"
        % ",".join(map(str, sample)))}
    turns = {r[0]: r[1:] for r in snap.execute(
        "SELECT id, position, side, die1, die2, legal_count, group_size, option_order, decided_by FROM turns"
        " WHERE id IN (%s)" % ",".join(map(str, sample)))}
    src = sqlite3.connect(f"file:{os.path.abspath(v3)}?mode=ro", uri=True, isolation_level=None)
    raw = {}
    for start in range(0, len(sample), 250):
        chunk = sample[start:start + 250]
        src.execute("BEGIN")
        for turn_id, attempt, eid, request in src.execute(
                "SELECT turn_id, attempt, id, request FROM exchanges WHERE turn_id IN (%s) ORDER BY attempt, id"
                % ",".join(map(str, chunk))):
            raw.setdefault(turn_id, []).append(request)
        src.execute("COMMIT")
    src.close()

    problems, stats = [], Counter()
    for turn_id in sample:
        fmt, digest, separator, requests = seen[turn_id]
        requests = json.loads(requests)
        context = contexts[digest]
        position, side, d1, d2, legal_count, group_size, option_order, decided_by = turns[turn_id]
        stats[fmt] += 1
        stats["requests"] += len(requests)
        stats["exchanges"] += len(raw.get(turn_id, []))
        # Every string sent equals a reconstruction; every stored request was sent; send order kept.
        stored = [reconstructed(r, context, separator) for r in requests]
        order = []
        for body in raw.get(turn_id, []):
            strings = sent_strings(json.loads(body))
            stats["strings"] += len(strings)
            if strings not in stored:
                problems.append((turn_id, "sent strings differ from every stored request"))
                break
            k = stored.index(strings)
            if k not in order:
                order.append(k)
        else:
            if order != list(range(len(stored))):
                problems.append((turn_id, f"stored requests not in send order or not sent: {order}"))
        # Options: counts and the shown order.
        notations = [notation for notation, _ in legal_plays(from_json(json.loads(position), side), d1, d2)]
        if len(notations) != legal_count:
            problems.append((turn_id, "rules.py legal plays differ from legal_count"))
            continue
        order_shown = [notations[i] for i in json.loads(option_order)]
        lists = [shown(r) for r in requests]
        if group_size is None:
            if [len(x) for x in lists] != [legal_count] or lists[0] != order_shown:
                problems.append((turn_id, f"options {[len(x) for x in lists]} != legal_count {legal_count}"))
            continue
        stats["group_split"] += 1
        chunks = [order_shown[k:k + group_size] for k in range(0, legal_count, group_size)]
        asked = [c for c in chunks if len(c) > 1]
        first = lists[:len(asked)]
        complete = len(lists) >= len(asked)
        if first != asked[:len(first)] or any(len(x) > group_size for x in lists) \
                or (not complete and decided_by != "fallback"):
            problems.append((turn_id, f"group split options {[len(x) for x in lists]} vs size {group_size}"
                                      f" of {legal_count}"))
    report = {
        "sampled": len(sample),
        "stats": dict(stats),
        "mismatches": len(problems),
        "examples": problems[:20],
        "seconds": round(time.monotonic() - started, 1),
    }
    print(json.dumps(report))


def main(argv):
    background()
    if argv[:1] == ["--verify"] and len(argv) == 4:
        verify(argv[2], argv[3], int(argv[1]))
    elif len(argv) == 2:
        run(*argv)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
