"""The "Every decision" page (brief B5): every scored decision, page by page, as the model saw it.

    export(out, snap, plays_dir, prompts_db, replay_db, v1_positions, datasets) -> counts per dataset and setup
    body() -> the inner HTML of <main> for decisions/index.html

Writes, under out/decisions/:
    index.json                                  datasets, their status and setups (name, slug, decisions, invalid, pages)
    <dataset>/<setup slug>/<page>.json.gz       PAGE_SIZE decisions per page, pages numbered from 1 (gzip, mtime 0, so an
                                                unchanged page is byte-identical from one build to the next)
    contexts/<hash>.txt                         the shared rules text of the prompts (hash = sha256(text)[:12])

League decisions are the scored ones (STATE/plays, tools/site/score_plays.py) joined with the snapshot's turns and
STATE/prompts.db; decisions not scored yet are not exported. The v1 set is one decision per (position, v1 model) of
replay.db. Plays are listed in the order the model was shown them; the viewer is assets/decisions.js.
"""

import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE.parent / "v3"))
sys.path.insert(0, str(SITE.parent))

from common import EARLIER, PROVISIONAL, PROVISIONAL_NOTE, slug  # noqa: E402
from rules import from_json, pips  # noqa: E402
import replay  # noqa: E402

PAGE_SIZE = 50
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TURN_PART = "Score: you "
# leagues.models[].spec of the players that are programs: they get no prompt and give no probabilities.
PROGRAM_SPECS = {"random", "safest", "gnubg-weak"}
HITS = re.compile(r"the opponent hits with (\d+) of 36 rolls")
EARLIER_BADGE = "Earlier version: plays listed in the runner's order"
# replay.py sent these endpoints its letter prompt (system + one user message) instead of a decision request.
LETTER_ENDPOINTS = (replay.GEMINI, replay.CODEX, replay.ANTHROPIC, replay.SGLANG_THINKING)


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def context_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def split_context(s):
    """(context, separator, turn text) with context + separator + text == s, split as prompts.db does: at the first
    "Score: you ", the context rstripped."""
    i = s.find(TURN_PART)
    if i < 0:
        raise ValueError("prompt without a turn part")
    context = s[:i].rstrip()
    return context, s[len(context):i], s[i:]


def r4(x):
    return None if x is None else round(x, 4)


def board(pos):
    pts, bar, off = pos
    return {"points": list(pts), "bar": list(bar), "off": list(off)}


def write_page(root, ds, setup, page, pages, decisions):
    path = root / ds / slug(setup) / f"{page}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"dataset": ds, "setup": setup, "slug": slug(setup), "page": page, "pages": pages, "decisions": decisions}
    raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def pages_of(items):
    return [items[i:i + PAGE_SIZE] for i in range(0, len(items), PAGE_SIZE)]


def shown_plays(entries, order, probs, program, cycle=None):
    """The plays in shown order: entries[legal index] = (notation, equity, hitting rolls, description).

    Letters: A, B, ... in shown order (none past Z, none for programs). When a chat model's plays were split into groups
    of `cycle`, group i is plays i*cycle .. i*cycle+cycle-1 of the shown order, lettered from A in its own request."""
    equities = [e[1] for e in entries if e[1] is not None]
    top = max(equities) if equities else None
    plays = []
    for k, li in enumerate(order):
        notation, equity, hits, desc = entries[li]
        j = k % cycle if cycle else k
        plays.append({"letter": LETTERS[j] if j < len(LETTERS) and not program else None,
                      "notation": notation, "description": desc, "equity": r4(equity),
                      "loss": r4(top - equity) if equity is not None else None,
                      "probability": r4(probs[k]) if probs and probs[k] is not None else None,
                      "hitting_rolls": hits})
    best = None
    for k, p in enumerate(plays):
        if p["equity"] is not None and (best is None or p["equity"] > plays[best]["equity"]):
            best = k
    return plays, best


# League decisions.

TURNS = """
SELECT t.id, t.game_id, t.turn_no, t.side, t.die1, t.die2, t.position, t.option_order, t.probabilities,
       t.probability_source, t.decided_by, t.group_size, t.request_ms, t.retry_ms, t.cost_usd
FROM turns t JOIN games g ON g.id = t.game_id JOIN league_matches lm ON lm.match_id = g.match_id
WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')
"""


def export_league(root, ds, sdb, shards, pdb, contexts):
    league = ds["league_id"]
    models = json.loads(sdb.execute("SELECT models FROM leagues WHERE id = ?", (league,)).fetchone()[0])
    programs = {m["name"] for m in models if m.get("spec") in PROGRAM_SPECS}
    turns = {r[0]: r for r in sdb.execute(TURNS, (league,))}
    by_setup = {m["name"]: [] for m in models}
    for db in shards.values():
        for tid, model in db.execute("SELECT turn_id, model FROM plays WHERE league_id = ?", (league,)):
            if tid not in turns:
                raise RuntimeError(f"scored turn {tid} is not a decision of league {league} in the snapshot")
            by_setup.setdefault(model, []).append(tid)
    out = {}
    for setup in sorted(by_setup, key=str.lower):
        ids = sorted(by_setup[setup])
        program = setup in programs
        invalid = 0
        chunks = pages_of(ids)
        for page, chunk in enumerate(chunks, 1):
            rows = {}
            for tid in chunk:
                rows[tid] = shards[tid % len(shards)].execute(
                    "SELECT game_id, chosen, phase, tag, data FROM plays WHERE turn_id = ?", (tid,)).fetchone()
            prompts = {}
            if pdb is not None and not program:
                marks = ",".join("?" * len(chunk))
                for tid, fmt, ctx, sep, reqs in pdb.execute(
                        f"SELECT turn_id, format, context, separator, requests FROM seen WHERE turn_id IN ({marks})", chunk):
                    prompts[tid] = {"format": fmt, "context": ctx, "separator": sep, "requests": json.loads(reqs)}
                    if ctx is not None:
                        contexts.add(ctx)
            decisions = []
            for tid in chunk:
                (_, game, turn_no, side, d1, d2, position, order, probs, source, decided_by, group_size,
                 request_ms, retry_ms, cost) = turns[tid]
                _, chosen, phase, tag, data = rows[tid]
                entries = json.loads(data)
                pos = from_json(json.loads(position), side)
                order = json.loads(order) if order else list(range(len(entries)))
                if sorted(order) != list(range(len(entries))):
                    raise RuntimeError(f"turn {tid}: option_order does not match the {len(entries)} legal plays")
                # A choice-only setup records 1.0 for its pick: that is not a probability (brief B11).
                probs = json.loads(probs) if probs and source != "choice_only" else None
                prompt = prompts.get(tid)
                cycle = group_size if prompt and prompt["format"] == "letters" else None
                plays, best = shown_plays(entries, order, probs, program, cycle)
                bad = decided_by == "fallback"
                invalid += bad
                decisions.append({
                    "id": tid, "dataset": ds["id"], "setup": setup, "league": league, "game": game, "turn_no": turn_no,
                    "side": side, "dice": [d1, d2], "board": board(pos), "phase": phase, "tag": tag,
                    "pips": list(pips(pos)), "program": program, "prompt": prompt, "plays": plays,
                    "chosen": order.index(chosen), "best": best, "decided_by": decided_by, "invalid": bad,
                    "group_size": group_size, "probability_source": source,
                    "request_seconds": None if request_ms is None else request_ms / 1000,
                    "retry_seconds": None if retry_ms is None else retry_ms / 1000, "cost_usd": cost})
            write_page(root, ds["id"], setup, page, len(chunks), decisions)
        out[setup] = {"slug": slug(setup), "decisions": len(ids), "invalid": invalid, "pages": len(chunks),
                      "program": program}
    return out


# The v1 set.

def v1_prompt(model, pid, state, instructions, options):
    """What replay.py sent `model` for this position, split like prompts.db."""
    url = replay.MODELS[model][0] if model in replay.MODELS else ""
    if any(e in url for e in LETTER_ENDPOINTS):
        system, prompt, _ = replay.letter_prompt(state, instructions, options)
        context, sep, text = split_context(prompt)
        req = {"system": system, "instructions": None, "text": text, "options": None}
        if replay.ANTHROPIC in url:
            req = {"system_prefix": [replay.CLAUDE_CODE_IDENTITY], **req}
        return "letters", context, sep, req
    context, sep, text = split_context(state)
    return "decision", context, sep, {"system": None, "instructions": instructions, "text": text,
                                      "options": [[n, d] for n, d in options.items()]}


def export_v1(root, ds, rdb, v1_positions, contexts):
    labels = {}
    with open(v1_positions) as f:
        for line in f:
            r = json.loads(line)
            labels[r["replay_position_id"]] = r
    positions = {r[0]: r for r in rdb.execute(
        "SELECT id, position, side, die1, die2, state, instructions, options FROM positions ORDER BY id")}
    equities = {}
    for pid, play, eq in rdb.execute("SELECT position_id, play, equity FROM equities"):
        equities[(pid, play)] = eq
    answers = {}
    for row in rdb.execute("SELECT model, position_id, choice, probabilities, latency_ms, error FROM answers "
                           "ORDER BY model, position_id"):
        answers.setdefault(row[0], []).append(row[1:])
    out = {}
    for model in sorted(answers, key=str.lower):
        rows = answers[model]
        # Choice-only runs record their pick as {play: 1.0}: no probability (brief B11).
        choice_only = all(p is None or len(json.loads(p)) == 1 and next(iter(json.loads(p).values())) == 1.0
                          for _, _, p, _, _ in rows)
        source = "choice_only" if choice_only else "decision"
        invalid = 0
        chunks = pages_of(rows)
        for page, chunk in enumerate(chunks, 1):
            decisions = []
            for pid, choice, probs, latency_ms, error in chunk:
                _, position, side, d1, d2, state, instructions, options = positions[pid]
                options = json.loads(options)
                if model in replay.SHUFFLED:
                    options = replay.shuffled(options, pid)
                fmt, context, sep, request = v1_prompt(model, pid, state, instructions, options)
                h = context_hash(context)
                contexts[h] = context
                names = list(options)
                probs = json.loads(probs) if probs and not choice_only else None
                entries = []
                for n in names:
                    m = HITS.search(options[n])
                    entries.append((n, equities.get((pid, n)), int(m.group(1)) if m else None, options[n]))
                plays, best = shown_plays(entries, range(len(names)),
                                          [probs.get(n) for n in names] if probs else None, False)
                bad = error is not None or choice not in options
                invalid += bad
                pos = from_json(json.loads(position), side)
                lab = labels[pid]
                decisions.append({
                    "id": lab["id"], "dataset": ds["id"], "setup": model, "league": None, "game": None,
                    "turn_no": lab["turn"], "side": side, "dice": [d1, d2], "board": board(pos), "phase": lab["phase"],
                    "tag": lab["tag"], "pips": list(pips(pos)), "program": False,
                    "prompt": {"format": fmt, "context": h, "separator": sep, "requests": [request]},
                    "plays": plays, "chosen": None if bad else names.index(choice), "best": best,
                    "decided_by": "invalid" if bad else "model", "invalid": bad, "group_size": None,
                    "probability_source": source,
                    "request_seconds": None if latency_ms is None else latency_ms / 1000,
                    "retry_seconds": None, "cost_usd": None})
            write_page(root, ds["id"], model, page, len(chunks), decisions)
        out[model] = {"slug": slug(model), "decisions": len(rows), "invalid": invalid, "pages": len(chunks),
                      "program": False}
    return out


def badge(status):
    return {PROVISIONAL: PROVISIONAL_NOTE, EARLIER: EARLIER_BADGE}.get(status, status)


def export(out: Path, snap: Path, plays_dir: Path, prompts_db: Path, replay_db: Path, v1_positions: Path,
           datasets: list[dict]) -> dict:
    root = Path(out) / "decisions"
    if root.exists():
        shutil.rmtree(root)
    (root / "contexts").mkdir(parents=True)
    sdb = ro(snap)
    shard_paths = {int(p.stem[1:]): p for p in Path(plays_dir).glob("s*.db") if p.stem[1:].isdigit()}
    if shard_paths and sorted(shard_paths) != list(range(len(shard_paths))):
        raise RuntimeError(f"plays shards are not s0..s{len(shard_paths) - 1}: {sorted(shard_paths)}")
    shards = {k: ro(p) for k, p in sorted(shard_paths.items())}
    pdb = ro(prompts_db) if Path(prompts_db).exists() else None
    rdb = ro(replay_db)
    league_contexts, v1_contexts = set(), {}
    result, index = {}, []
    for ds in datasets:
        if ds["version"] == "v1":
            setups = export_v1(root, ds, rdb, v1_positions, v1_contexts)
        else:
            setups = export_league(root, ds, sdb, shards, pdb, league_contexts)
        result[ds["id"]] = {name: {k: v for k, v in s.items() if k != "program"} for name, s in setups.items()}
        index.append({"id": ds["id"], "label": ds["label"], "version": ds["version"], "status": ds["status"],
                      "badge": badge(ds["status"]), "note": ds.get("note"), "league_id": ds.get("league_id"),
                      "setups": [dict(name=name, **s) for name, s in setups.items()]})
    for h in league_contexts:
        row = pdb.execute("SELECT text FROM contexts WHERE hash = ?", (h,)).fetchone()
        if row is None:
            raise RuntimeError(f"prompts.db: context {h} is missing")
        (root / "contexts" / f"{h}.txt").write_text(row[0])
    for h, text in v1_contexts.items():
        (root / "contexts" / f"{h}.txt").write_text(text)
    (root / "index.json").write_text(json.dumps({"page_size": PAGE_SIZE, "datasets": index}, ensure_ascii=False,
                                                separators=(",", ":")))
    return result


def body() -> str:
    return f"""<section class="hero">
<p class="eyebrow">Every decision</p>
<h1>What did each model see, and what did it play?</h1>
<p class="intro">Every scored decision, {PAGE_SIZE} to a page: the board, the position exactly as the model saw it, every
legal play with its consequences, the engine's equity for each play, the equity the chosen play lost and the model's
probability where it gives one.</p>
</section>
<div id="dec-controls" class="panel dec-controls" hidden></div>
<noscript><p class="note">This page loads its decisions on demand with JavaScript. The same data is in
<code>decisions/index.json</code> and the gzip-compressed JSON page files listed there.</p></noscript>
<p id="dec-status" class="note" role="status"></p>
<div id="dec-list" class="dec-list"></div>
<nav id="dec-pager-bottom" class="dec-pager" aria-label="Pages" hidden></nav>
"""
