"""Learning pilot (v5 design A17, learning track): series of 10 games of Gemma 4 31B (off) against GNUbg weak (GNU
Backgammon 1.08 Beginner, the league anchor) in four arms, and the 200-position evaluation with each arm's current
context. Plan and rules: mailbox/Learning pilot - plan 2026-11-07.md (the single source).

    python3 workspace/learning-pilot/pilot.py t0                     # the shared evaluation before game 1 (once)
    python3 workspace/learning-pilot/pilot.py run --series 1-3       # smoke; later --series 4-10
    python3 workspace/learning-pilot/pilot.py summary

Run from the repo root. Arms: control (no context), records (all earlier games of the series with GNUbg's evaluation
of each decision), lessons (one lesson call after each game; the context is every lesson written so far in the
series), budget (the most recent records that fit the token count of the lessons arm's context at the same point of
the same series; runs after the lessons arm's series). One worker per arm, one model request in flight per arm, so
spark3 sees at most four. Series s uses one dice seed in every arm; game g is round ceil(g/2), leg 2 - g % 2 of a
5-round match with --fixed-rounds (games 2k-1 and 2k: same dice, seats swapped). Evaluations: T0 once in total (no
context: every arm's starting point and the control's evaluation), then after games 5 and 10 for the three
non-control arms.

Private outputs (never committed): smoke/learning-pilot.db (games, evaluation answers, every request),
smoke/learning-pilot-plays.db (2-ply scores), workspace/learning-pilot/runs/ (contexts, lessons, logs, per-series
aggregates), learning.jsonl, seeds.json, learning-pilot.json.
"""

import argparse
import hashlib
import json
import os
import random
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BIN = ROOT.parent / "jevgammon-learning-pilot/target/release/jevgammon"
# PILOT_DRY=1: an offline harness check with no model call: the `safest` program plays in Gemma's seat, evaluations
# are skipped and lessons are canned; everything goes to separate -dry files.
DRY = os.environ.get("PILOT_DRY") == "1"
SUFFIX = "-dry" if DRY else ""
DB = ROOT / f"smoke/learning-pilot{SUFFIX}.db"
PLAYS = ROOT / f"smoke/learning-pilot-plays{SUFFIX}.db"
RUNS = HERE / f"runs{SUFFIX}"
OUTPUTS = HERE / f"out{SUFFIX}"
TEST_SET = HERE / "test_set.json"
TEST_POSITIONS = HERE / "test_positions.jsonl"
BASE = json.loads((HERE / "configs/base.json").read_text())
PLAYER = dict(BASE["players"][0], spec="safest") if DRY else BASE["players"][0]
ORDER_SEED = BASE["order_seed"]
SERVER = BASE["players"][0]["base_url"]
MODEL = "gemma-4-31B-it"
MASTER_SEED = "learning-pilot 2026-11-07"
BOOT_SEED = 20261107
BOOT = 10000
GAMES = 10
PLANNED = 10  # series per arm, fixed by the plan; a smoke summary can never be complete
CHECKPOINTS = (5, 10)  # after these games, for the non-control arms; T0 is shared
ARMS = ["control", "records", "lessons", "budget"]
MARGIN = 0.001  # the site's risk margin
SCALE = 500  # the site's equity scale: error rate = 500 x mean 2-ply equity loss
CONTEXT_LIMIT = 32768  # spark3's max_model_len
PROMPT_MAX = 4389  # largest evaluation prompt (system + user, Gemma tokens), measured
NOTE_BUDGET = CONTEXT_LIMIT - PROMPT_MAX - 1500  # tokens for a context; the rest is margin
MARKS = [(0.16, "very bad"), (0.08, "bad"), (0.04, "doubtful")]  # GNUbg's default skill marks
OPEN = "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
CLOSE = "=== END OF NOTES ==="
LESSONS_SYSTEM = HERE / "lessons_system.txt"
LESSONS_USER = HERE / "lessons_user.txt"
LESSONS_MAX_TOKENS = 400
MAX_LESSONS, MAX_WORDS = 5, 150
LOCK = threading.Lock()
T0_NAME = "Gemma 4 31B (off) | T0 shared"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_atomic(path: Path, text: str):
    """Write then rename, so the site's snapshot never copies a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def lesson_prompt_sha256() -> str:
    return hashlib.sha256(LESSONS_SYSTEM.read_bytes() + LESSONS_USER.read_bytes()).hexdigest()


def series_seed(s: int) -> int:
    return int(hashlib.sha256(f"{MASTER_SEED} series {s}".encode()).hexdigest()[:16], 16) & (2**63 - 1)


def run_dir(arm: str, s: int) -> Path:
    return RUNS / arm / f"s{s:02d}"


def player_name(arm: str, s: int) -> str:
    return f"Gemma 4 31B (off) | {arm} | s{s:02d}"


def log(arm, s, event, **kw):
    d = run_dir(arm, s)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "log.jsonl", "a") as f:
        f.write(json.dumps(dict(at=now(), event=event, **kw)) + "\n")


def events(arm, s):
    f = run_dir(arm, s) / "log.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []


_TOK = None


def tokens(text: str) -> int:
    global _TOK
    if not text:
        return 0
    if _TOK is None:
        from tokenizers import Tokenizer
        _TOK = Tokenizer.from_file("/home/cbasaran/code/models/gemma-4-31B-it/tokenizer.json")
    return len(_TOK.encode(text).ids)


# --- Evaluation set and scoring ----------------------------------------------------------------------------

def test_set():
    return json.loads(TEST_SET.read_text())


def test_board_keys():
    return {p["board_key"] for p in test_set()["positions"]}


def play_call(shots, losses, i, margin=MARGIN):
    """tools/site/analysis.py play_call: (class, call)."""
    least = min(shots)
    if all(s == least for s in shots):
        return "none", "none"
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call


LABELS = {"missed": "missed risk", "needless": "needless risk", "wrong_risk": "wrong risk",
          "right_risk": "right risk call", "right_safety": "right safety call", "none": "no risk trade-off"}


def score_match(match_id: int):
    env = dict(os.environ, SCORE_ARGS=f"{DB} {PLAYS} {match_id}")
    r = subprocess.run(["nice", "-n", "19", "gnubg", "-t", "-q", "-p", str(HERE / "score_games.py")], cwd=ROOT,
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gnubg scoring failed: {r.stderr[-2000:]}")


def game_decisions(match_id: int, upto: int = GAMES):
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    turns = db.execute("""
        SELECT t.id, t.turn_no, t.die1, t.die2, t.position, t.side, t.decided_by, t.latency_ms, t.request_ms,
               t.input_tokens, t.output_tokens, t.option_order, g.round_no, g.leg
        FROM turns t JOIN games g ON g.id = t.game_id
        WHERE g.match_id = ? AND t.player = 1 AND t.decided_by IN ('model', 'fallback')
        ORDER BY g.round_no, g.leg, t.turn_no""", (match_id,)).fetchall()
    db.close()
    pdb = sqlite3.connect(f"file:{PLAYS}?mode=ro", uri=True, timeout=60)
    scored = {r[0]: r for r in pdb.execute("SELECT turn_id, chosen, loss, board_key, data FROM plays WHERE match_id = ?",
                                           (match_id,))}
    pdb.close()
    out = []
    for t in turns:
        g = 2 * (t["round_no"] - 1) + t["leg"]
        if g > upto:
            continue
        s = scored.get(t["id"])
        d = dict(turn_id=t["id"], game=g, turn_no=t["turn_no"], dice=(t["die1"], t["die2"]),
                 position=json.loads(t["position"]), side=t["side"], invalid=t["decided_by"] == "fallback",
                 scored=s is not None, request_ms=t["request_ms"] if t["request_ms"] is not None else t["latency_ms"],
                 input_tokens=t["input_tokens"], output_tokens=t["output_tokens"],
                 option_order=json.loads(t["option_order"]) if t["option_order"] else None)
        if s is not None:
            data = json.loads(s[4])
            eq = [x[1] for x in data]
            best = max(eq)
            losses = [best - e for e in eq]
            shots = [x[2] for x in data]
            cls, call = play_call(shots, losses, s[1])
            d.update(chosen=s[1], loss=s[2], board_key=s[3], plays=[x[0] for x in data], best=eq.index(best),
                     cls=cls, call=call)
        out.append(d)
    return out


def game_results(match_id: int):
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    rows = db.execute("SELECT round_no, leg, winner_player, result, points, turns FROM games WHERE match_id = ?",
                      (match_id,)).fetchall()
    db.close()
    return {2 * (r[0] - 1) + r[1]: dict(won=r[2] == 1, result=r[3], points=r[4], turns=r[5]) for r in rows}


# --- Contexts ----------------------------------------------------------------------------------------------

def board_text(position: dict, side: str) -> str:
    """The board from the mover's side, in the mover's point numbering (as in the game prompt)."""
    sys.path.insert(0, str(ROOT / "tools" / "v3"))
    from rules import from_json
    pts, bar, off = from_json(position, side)
    mine = " ".join(f"{i + 1}:{n}" for i, n in enumerate(pts) if n > 0)
    theirs = " ".join(f"{i + 1}:{-n}" for i, n in enumerate(pts) if n < 0)
    return (f"your checkers {mine or '-'} (bar {bar[0]}, off {off[0]}); "
            f"opponent's checkers {theirs or '-'} (bar {bar[1]}, off {off[1]})")


def verdict(d) -> str:
    if d["loss"] < 1e-9:
        return "best play"
    for edge, mark in MARKS:
        if d["loss"] >= edge:
            return mark
    return "small error"


def record_line(d) -> str:
    return (f"- Turn {d['turn_no']}, dice {d['dice'][0]}-{d['dice'][1]}; {board_text(d['position'], d['side'])}. "
            f"You played {d['plays'][d['chosen']]}. GNUbg's best play: {d['plays'][d['best']]}. "
            f"Equity lost: {d['loss']:.3f} ({verdict(d)}; risk call: {LABELS[d['call']]}).")


def game_header(g, results):
    res = results.get(g)
    outcome = (f"you {'won' if res['won'] else 'lost'} {res['points']} point(s), {res['result']}" if res
               else "result unknown")
    return f"Game {g} ({outcome}):"


def eligible(decs, exclude):
    """Scored, valid decisions whose board is not an evaluation position (leakage rule)."""
    return [d for d in decs if d["scored"] and not d["invalid"] and d["board_key"] not in exclude]


RECORDS_INTRO = ("Below are the records of your earlier games in this series against the same opponent: each decision "
                 "you made, with the GNU Backgammon engine's evaluation of it (2-ply). Boards are given in your point "
                 "numbering.")


def records_text(lines_by_game, results):
    body = []
    for g in sorted(lines_by_game):
        if lines_by_game[g]:
            body += [game_header(g, results)] + lines_by_game[g] + [""]
    return "\n".join([OPEN, RECORDS_INTRO, ""] + body + [CLOSE]) if body else ""


def ctx_records(decs, results, exclude, arm, s, g):
    """Every earlier game in full; the oldest games are dropped first if the context limit is exceeded."""
    ok = eligible(decs, exclude)
    games = list(range(1, g + 1))
    while games:
        text = records_text({k: [record_line(d) for d in ok if d["game"] == k] for k in games}, results)
        n = tokens(text)
        if n <= NOTE_BUDGET:
            return text, dict(games_shown=games, games_dropped=g - len(games),
                              records_dropped=g - len(games))
        log(arm, s, "context_drop", after_game=g, dropped_game=games[0], tokens=n, budget=NOTE_BUDGET)
        games = games[1:]
    return "", dict(games_shown=[], games_dropped=g, records_dropped=g)


def ctx_budget(decs, results, exclude, arm, s, g, budget_tokens):
    """A17's budget-matched records: the most recent FULL game records (whole games, newest first) whose context
    fits in the token count of the lessons arm's context after the same game of the same series. If not even the
    newest game fits, the context is empty at that point (logged)."""
    ok = eligible(decs, exclude)
    limit = min(budget_tokens, NOTE_BUDGET)
    shown, text = [], ""
    for k in range(g, 0, -1):  # newest game first; stop at the first game that does not fit
        trial = [k] + shown
        t = records_text({x: [record_line(d) for d in ok if d["game"] == x] for x in trial}, results)
        if tokens(t) > limit:
            break
        shown, text = trial, t
    if not shown:
        log(arm, s, "budget_context_empty", after_game=g, budget_tokens=budget_tokens,
            newest_game_tokens=tokens(records_text({g: [record_line(d) for d in ok if d["game"] == g]}, results)))
    return text, dict(budget_tokens=budget_tokens, games_shown=shown, games_dropped=g - len(shown),
                      records_dropped=g - len(shown))


def chat(messages, max_tokens):
    body = dict(model=MODEL, messages=messages, temperature=1.0, max_tokens=max_tokens,
                chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(f"{SERVER}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    started = time.time()
    for attempt in range(4):  # network and server errors: 3 retries, as in the leagues
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read()), time.time() - started, body
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def limit_lessons(text):
    """At most 5 lessons and 150 words: lines starting with '- ' are lessons; extra lessons, then extra words, are cut."""
    items = [x.strip() for x in text.splitlines() if x.strip().startswith("- ")]
    if not items:
        items = ["- " + x.strip().lstrip("-*0123456789. ") for x in text.splitlines() if x.strip()]
    cut = dict(lessons_written=len(items), words_written=sum(len(x[2:].split()) for x in items))
    items = items[:MAX_LESSONS]
    out, words = [], 0
    for x in items:
        w = x[2:].split()
        if words + len(w) > MAX_WORDS:
            w = w[:MAX_WORDS - words]
        if w:
            out.append("- " + " ".join(w))
        words += len(w)
        if words >= MAX_WORDS:
            break
    cut.update(lessons_kept=len(out), words_kept=words, cut=cut["lessons_written"] > len(out) or cut["words_written"] > words)
    return "\n".join(out), cut


def write_lessons(decs, results, exclude, arm, s, g):
    """One lesson call after game g: that game's record with GNUbg's evaluation of each decision, nothing else."""
    ok = [d for d in eligible(decs, exclude) if d["game"] == g]
    record = "\n".join([game_header(g, results)] + [record_line(d) for d in ok])
    user = LESSONS_USER.read_text().format(game=g, record=record)
    messages = [{"role": "system", "content": LESSONS_SYSTEM.read_text().strip()}, {"role": "user", "content": user}]
    if DRY:
        # Dry run: lessons at the allowed maximum (5 lessons, 150 words), so the budget arm's matching is exercised.
        raw = "\n".join(f"- (dry run) game {g} lesson {k}: " + " ".join(["placeholder"] * 24) for k in range(1, 6))
        secs, usage, finish, body, out = 0.0, {}, "dry", None, None
    else:
        out, secs, body = chat(messages, LESSONS_MAX_TOKENS)
        raw = (out["choices"][0]["message"].get("content") or "").strip()
        usage, finish = out.get("usage", {}), out["choices"][0].get("finish_reason")
    text, cut = limit_lessons(raw)
    d = run_dir(arm, s)
    write_atomic(d / f"lessons-g{g:02d}.txt", text + "\n")
    (d / f"lessons-g{g:02d}.json").write_text(json.dumps(dict(prompt_sha256=lesson_prompt_sha256(), request=body,
                                                              response=out, raw=raw, kept=text, **cut), indent=1))
    log(arm, s, "lessons_call", game=g, seconds=round(secs, 2), input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"), finish=finish, **cut)
    return text


LESSONS_INTRO = "Lessons you wrote for yourself after your earlier games in this series, oldest first:"


def ctx_lessons(arm, s, g):
    d = run_dir(arm, s)
    blocks = [(k, (d / f"lessons-g{k:02d}.txt").read_text().strip()) for k in range(1, g + 1)]
    blocks = [(k, t) for k, t in blocks if t]
    while blocks:
        text = "\n".join([OPEN, LESSONS_INTRO, ""] + [f"After game {k}:\n{t}\n" for k, t in blocks] + [CLOSE])
        n = tokens(text)
        if n <= NOTE_BUDGET:
            return text, dict(lessons_games=[k for k, _ in blocks])
        log(arm, s, "context_drop", after_game=g, dropped_game=blocks[0][0], tokens=n, budget=NOTE_BUDGET)
        blocks = blocks[1:]
    return "", dict(lessons_games=[])


def lessons_tokens_after(s, g):
    for e in events("lessons", s):
        if e["event"] == "context" and e["after_game"] == g:
            return e["tokens"]
    raise RuntimeError(f"lessons arm, series {s}: no context after game {g} yet")


def build_context(arm, s, match_id, g):
    if arm == "control":
        return "", {}
    exclude = test_board_keys()
    decs = game_decisions(match_id, g)
    excluded = sum(1 for x in decs if x["scored"] and x["game"] == g and x["board_key"] in exclude)
    if excluded:
        log(arm, s, "evaluation_positions_excluded", game=g, n=excluded)
    results = game_results(match_id)
    if arm == "records":
        return ctx_records(decs, results, exclude, arm, s, g)
    if arm == "lessons":
        write_lessons(decs, results, exclude, arm, s, g)
        return ctx_lessons(arm, s, g)
    if arm == "budget":
        return ctx_budget(decs, results, exclude, arm, s, g, lessons_tokens_after(s, g))
    raise ValueError(arm)


def write_context(arm, s, g, text, info):
    d = run_dir(arm, s)
    tmp = d / "note.txt.tmp"
    tmp.write_text(text)
    tmp.replace(d / "note.txt")
    (d / "contexts").mkdir(exist_ok=True)
    (d / "contexts" / f"after-g{g:02d}.txt").write_text(text)
    log(arm, s, "context", after_game=g, tokens=tokens(text), chars=len(text),
        sha256=hashlib.sha256(text.encode()).hexdigest(), **info)


# --- Evaluations -------------------------------------------------------------------------------------------

def run_eval(name, note, workdir, parallel=1):
    workdir.mkdir(parents=True, exist_ok=True)
    tag = name.split(" | ")[-1]
    if DRY:
        return dict(name=name, wall_seconds=0.0, dry=True)
    cfg = dict(BASE)
    p = dict(PLAYER, name=name, parallel=parallel)
    if note:
        p["prompt_note"] = note
    cfg["players"] = [p]
    path = workdir / f"eval-{tag}.json"
    path.write_text(json.dumps(cfg, indent=1))
    started = time.time()
    r = subprocess.run([str(BIN), "ask", "--config", str(path), "--positions", str(TEST_POSITIONS), "--out", str(DB),
                        "--setup", name], cwd=ROOT, capture_output=True, text=True)
    (workdir / f"eval-{tag}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"evaluation {name} failed: {r.stderr[-2000:]}")
    return dict(name=name, wall_seconds=round(time.time() - started, 1))


def eval_answers(name):
    if not DB.exists():
        return []
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("SELECT * FROM answers WHERE setup = ? AND repeat = 1 ORDER BY id", (name,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    db.close()
    latest = {}
    for r in rows:
        latest[r["position_id"]] = r
    return list(latest.values())


def eval_metrics(name):
    ts = {p["id"]: p for p in test_set()["positions"]}
    rows = eval_answers(name)
    calls = dict(right_risk=0, wrong_risk=0, needless=0, missed=0, right_safety=0, none=0)
    rp = sp = 0
    losses, req_ms = [], []
    invalid = failed = tin = tout = 0
    for r in rows:
        p = ts[r["position_id"]]
        req_ms.append(r["request_ms"] or 0)
        tin += r["input_tokens"] or 0
        tout += r["output_tokens"] or 0
        if r["error"]:
            failed += 1
            continue
        if r["invalid"] or r["chosen_index"] is None:
            invalid += 1
            continue
        i = r["chosen_index"]
        losses.append(p["losses"][i])
        cls, call = play_call(p["shots"], p["losses"], i)
        calls[call] += 1
        rp += cls == "risk"
        sp += cls == "safety"
    taken = calls["right_risk"] + calls["wrong_risk"] + calls["needless"]
    pct = lambda n, d: 100 * n / d if d else None  # noqa: E731
    n = len(rows)
    return dict(
        answered=n, expected=len(ts), valid=len(losses), invalid=invalid, failed=failed,
        error_rate=SCALE * sum(losses) / len(losses) if losses else None,
        risk_judgement=50 * (calls["right_risk"] / rp + calls["right_safety"] / sp) if rp and sp else None,
        risks_found=pct(calls["right_risk"], rp), right_safety=pct(calls["right_safety"], sp),
        risk_appetite=pct(taken, rp + sp), risk_pays=rp, safety_pays=sp, calls=calls,
        input_tokens_per_decision=tin / n if n else None, output_tokens_per_decision=tout / n if n else None,
        request_seconds=round(sum(req_ms) / 1000, 1),
        latency_median_s=sorted(req_ms)[len(req_ms) // 2] / 1000 if req_ms else None, cost_usd=0.0)


# --- Series ------------------------------------------------------------------------------------------------

def init_runner_db():
    """Create the runner's schema once before the arms start: several runner processes creating it at the same time
    on a fresh file race on CREATE VIEW. `jevgammon rank` opens (and so creates) the database, then stops with "no such
    league"; only the schema is checked."""
    subprocess.run([str(BIN), "rank", "--db", str(DB), "--dry-run", "--scores", str(HERE)], cwd=ROOT,
                   capture_output=True, text=True)
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master")}
    db.close()
    if not {"matches", "games", "turns", "league_match_view"} <= tables:
        sys.exit(f"could not create the runner schema in {DB}")


def match_of(arm, s):
    if not DB.exists():
        return None
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    try:
        row = db.execute("SELECT id, status FROM matches WHERE model1 = ? ORDER BY id DESC LIMIT 1",
                         (player_name(arm, s),)).fetchone()
    except sqlite3.OperationalError:
        row = None
    db.close()
    return row


def run_t0():
    d = RUNS / "t0"
    if (d / "aggregate.json").exists():
        return
    info = run_eval(T0_NAME, "", d, parallel=4)
    write_atomic(d / "aggregate.json", json.dumps(dict(info, finished_at=now(), metrics=eval_metrics(T0_NAME),
                                                       test_set_sha256=file_sha256(TEST_SET)), indent=1))


def run_series(arm, s):
    d = run_dir(arm, s)
    if (d / "aggregate.json").exists():
        return
    if arm == "budget":
        while not (run_dir("lessons", s) / "aggregate.json").exists():
            if (run_dir("lessons", s) / "failed").exists():
                raise RuntimeError(f"lessons arm series {s} failed; the budget arm cannot run it")
            time.sleep(30)
    prior = match_of(arm, s)
    if prior is not None:
        # A series cut off part-way is played again from game 1 with the same dice (logged); its old match stays.
        # The failed attempt's files move to attempt-N/, so the new attempt's log and lessons start clean.
        n = 1 + sum(1 for _ in d.glob("attempt-*"))
        old = d / f"attempt-{n}"
        old.mkdir(parents=True)
        for f in (list(d.glob("lessons-g*")) + list(d.glob("eval-*")) + [d / "contexts", d / "note.txt", d / "failed",
                                                                          d / "failed.previous",
                                                                          d / "log.jsonl", d / "match.log",
                                                                          d / "player.json"]):
            if f.exists():
                f.rename(old / f.name)
        why = next((old / x for x in ("failed", "failed.previous") if (old / x).exists()), None)
        log(arm, s, "series_restarted", old_match=prior[0], old_status=prior[1], attempt_archive=old.name,
            reason=why.read_text()[-300:] if why else None)
    d.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log(arm, s, "series_start", seed=series_seed(s), lesson_prompt_sha256=lesson_prompt_sha256())
    (d / "note.txt").write_text("")
    cfg = dict(PLAYER, name=player_name(arm, s), prompt_note_file=str(d / "note.txt"), parallel=1)
    (d / "player.json").write_text(json.dumps(cfg, indent=1))
    hook = f"{sys.executable} {Path(__file__).resolve()} after-game --arm {arm} --series {s}"
    r = subprocess.run([str(BIN), "--model1-config", str(d / "player.json"), "--model2", "gnubg-weak",
                        "--seed", str(series_seed(s)), "--order-seed", str(ORDER_SEED), "--rounds", str(GAMES // 2),
                        "--fixed-rounds", "--clock", "0", "--max-turns", str(BASE["max_turns"]),
                        "--prompt-version", BASE["prompt_version"], "--quiet", "--db", str(DB), "--after-game", hook],
                       cwd=ROOT, capture_output=True, text=True, env=dict(os.environ))
    (d / "match.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        log(arm, s, "series_failed", stderr=r.stderr[-2000:])
        (d / "failed").write_text(r.stderr[-2000:])
        raise RuntimeError(f"{arm} s{s}: match failed: {r.stderr[-1000:]}")
    write_aggregate(arm, s, time.time() - started)


def after_game(arm, s):
    match_id = int(os.environ["MATCH_ID"])
    g = 2 * (int(os.environ["GAME_ROUND"]) - 1) + int(os.environ["GAME_LEG"])
    score_match(match_id)
    text, info = build_context(arm, s, match_id, g)
    write_context(arm, s, g, text, info)
    if arm != "control" and g in CHECKPOINTS:
        info = run_eval(f"{player_name(arm, s)} | T{g}", text, run_dir(arm, s))
        log(arm, s, "evaluation_done", checkpoint=g, context_tokens=tokens(text), **info)


def game_metrics(match_id):
    decs = game_decisions(match_id)
    results = game_results(match_id)
    out = []
    for g in range(1, GAMES + 1):
        gd = [d for d in decs if d["game"] == g]
        valid = [d for d in gd if d["scored"] and not d["invalid"]]
        lat = sorted(d["request_ms"] or 0 for d in gd)
        out.append(dict(game=g, decisions=len(gd), invalid=sum(d["invalid"] for d in gd),
                        unscored=sum(not d["scored"] for d in gd), valid=len(valid),
                        loss_sum=sum(d["loss"] for d in valid),
                        error_rate=SCALE * sum(d["loss"] for d in valid) / len(valid) if valid else None,
                        input_tokens_per_decision=sum(d["input_tokens"] for d in gd) / len(gd) if gd else None,
                        latency_median_s=lat[len(lat) // 2] / 1000 if lat else None,
                        request_seconds=sum(lat) / 1000,
                        **{k: v for k, v in results.get(g, {}).items()}))
    return out


def pooled_rate(games, lo, hi):
    sel = [x for x in games if lo <= x["game"] <= hi]
    n = sum(x["valid"] for x in sel)
    return SCALE * sum(x["loss_sum"] for x in sel) / n if n else None


def write_aggregate(arm, s, wall):
    d = run_dir(arm, s)
    m = match_of(arm, s)
    games = game_metrics(m[0])
    ev = events(arm, s)
    agg = dict(
        arm=arm, series=s, seed=series_seed(s), finished_at=now(), wall_seconds=round(wall, 1),
        evaluations={f"T{cp}": eval_metrics(f"{player_name(arm, s)} | T{cp}") for cp in CHECKPOINTS}
        if arm != "control" else {},
        games=games, games_error_rate_1_3=pooled_rate(games, 1, 3), games_error_rate_8_10=pooled_rate(games, 8, 10),
        context_tokens_after_game={e["after_game"]: e["tokens"] for e in ev if e["event"] == "context"},
        records_dropped_after_game={e["after_game"]: e.get("records_dropped", 0) for e in ev if e["event"] == "context"},
        budget_context_empty_after_game=[e["after_game"] for e in ev if e["event"] == "budget_context_empty"],
        budget_points=[dict(after_game=e["after_game"], games_shown=e.get("games_shown", []),
                            games_dropped=e.get("games_dropped", 0), tokens=e["tokens"],
                            budget_tokens=e.get("budget_tokens"))
                       for e in ev if e["event"] == "context"] if arm == "budget" else [],
        context_drops=[{k: e[k] for k in ("after_game", "dropped_game", "tokens", "budget")} for e in ev
                       if e["event"] == "context_drop"],
        evaluation_positions_excluded=sum(e["n"] for e in ev if e["event"] == "evaluation_positions_excluded"),
        lessons_calls=[{k: e.get(k) for k in ("game", "seconds", "input_tokens", "output_tokens", "finish",
                                              "lessons_written", "words_written", "cut")}
                       for e in ev if e["event"] == "lessons_call"],
        restarts=sum(e["event"] == "series_restarted" for e in ev), lesson_prompt_sha256=lesson_prompt_sha256(),
        test_set_sha256=file_sha256(TEST_SET),
        lessons_files={str(g): file_sha256(d / f"lessons-g{g:02d}.txt") for g in range(1, GAMES + 1)
                       if (d / f"lessons-g{g:02d}.txt").exists()},
        cost_usd=0.0)
    write_atomic(d / "aggregate.json", json.dumps(agg, indent=1))


# --- Summary -----------------------------------------------------------------------------------------------

KEYS = ["error_rate", "risk_judgement", "risks_found", "right_safety", "risk_appetite"]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sub(a, b):
    return a - b if a is not None and b is not None else None


def boot_ci(values_by_series, rng_seed):
    """95% percentile interval of the mean, resampling whole series by index: the same seed draws the same series
    for every arm and measure, so the dice schedules stay paired across arms. A series without a value is left
    out of the resample's mean."""
    n = len(values_by_series)
    if sum(v is not None for v in values_by_series) < 2:
        return None
    rng = random.Random(rng_seed)
    means = []
    for _ in range(BOOT):
        draw = [values_by_series[rng.randrange(n)] for _ in range(n)]
        draw = [v for v in draw if v is not None]
        if draw:
            means.append(sum(draw) / len(draw))
    means.sort()
    return [means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1]]


def file_sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def protocol():
    """The registered protocol this run is bound to; the site compares it with its own fixed copy."""
    return dict(arms=ARMS, planned_series_per_arm=PLANNED, games_per_series=GAMES,
                checkpoints=dict(shared=["T0"], non_control=[f"T{cp}" for cp in CHECKPOINTS]),
                evaluation_positions=len(test_set()["positions"]), lesson_prompt_sha256=lesson_prompt_sha256(),
                test_set_sha256=file_sha256(TEST_SET), dry_run=DRY)


def series_finished(arm, a):
    """A series counts only with all 10 games, both evaluations answered in full (non-control arms) and, for the
    lessons arm, a lesson file after every game."""
    if [g["game"] for g in a["games"]] != list(range(1, GAMES + 1)) or any(not g["decisions"] for g in a["games"]):
        return False
    if arm != "control" and any(a["evaluations"].get(f"T{cp}", {}).get("answered") != len(test_set()["positions"])
                                for cp in CHECKPOINTS):
        return False
    if arm == "lessons" and sorted(int(g) for g in a.get("lessons_files", {})) != list(range(1, GAMES + 1)):
        return False
    return a.get("test_set_sha256") == file_sha256(TEST_SET) and a.get("lesson_prompt_sha256") == lesson_prompt_sha256()


def summary():
    planned = PLANNED
    t0 = json.loads((RUNS / "t0/aggregate.json").read_text()) if (RUNS / "t0/aggregate.json").exists() else None
    aggs = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for f in sorted((RUNS / arm).glob("s*/aggregate.json")) if (RUNS / arm).exists() else []:
            a = json.loads(f.read_text())
            aggs[arm][a["series"]] = a
    table = {arm: {} for arm in ARMS}
    t0m = t0["metrics"] if t0 else None
    for arm in ARMS:
        table[arm]["T0"] = dict(t0m, shared=True) if t0m else None
        if arm == "control":
            continue
        for cp in CHECKPOINTS:
            ms = [a["evaluations"][f"T{cp}"] for a in aggs[arm].values()]
            row = {k: mean([m[k] for m in ms]) for k in KEYS + ["input_tokens_per_decision", "latency_median_s"]}
            row.update(invalid=sum(m["invalid"] for m in ms), failed=sum(m["failed"] for m in ms),
                       request_seconds=round(sum(m["request_seconds"] for m in ms), 1), cost_usd=0.0, series=len(ms),
                       records_dropped=sum(a["records_dropped_after_game"].get(str(cp), a["records_dropped_after_game"]
                                                                                .get(cp, 0)) for a in aggs[arm].values()))
            table[arm][f"T{cp}"] = row
    games = {}
    for arm in ARMS:
        gs = [g for a in aggs[arm].values() for g in a["games"]]
        lat = [g["latency_median_s"] for g in gs if g["latency_median_s"] is not None]
        games[arm] = dict(series=len(aggs[arm]), games=len(gs), decisions=sum(g["decisions"] for g in gs),
                          invalid=sum(g["invalid"] for g in gs),
                          error_rate=SCALE * sum(g["loss_sum"] for g in gs) / max(1, sum(g["valid"] for g in gs)) if gs else None,
                          input_tokens_per_decision=mean([g["input_tokens_per_decision"] for g in gs]),
                          latency_median_s=sorted(lat)[len(lat) // 2] if lat else None,
                          records_dropped=sum(max(a["records_dropped_after_game"].values() or [0]) for a in aggs[arm].values()),
                          context_drops=sum(len(a["context_drops"]) for a in aggs[arm].values()),
                          budget_empty_points=sum(len(a.get("budget_context_empty_after_game", []))
                                                  for a in aggs[arm].values()),
                          wins=sum(bool(g.get("won")) for g in gs), cost_usd=0.0)
    done = {arm: len(aggs[arm]) for arm in ARMS}
    finished = {arm: sorted(s for s, a in aggs[arm].items() if series_finished(arm, a)) for arm in ARMS}
    t0_ok = bool(t0) and t0["metrics"]["answered"] == len(test_set()["positions"])
    complete = (not DRY and t0_ok and all(finished[arm] == list(range(1, PLANNED + 1)) for arm in ARMS))
    out = dict(updated_at=now(), protocol=protocol(), planned_series_per_arm=planned, series_done=done,
               series_finished=finished, complete=complete,
               lesson_prompt_sha256=lesson_prompt_sha256(), t0_done=t0_ok,
               inventory={arm: {str(s): dict(games=[g["game"] for g in a["games"]],
                                             lessons_files=a.get("lessons_files", {}),
                                             test_set_sha256=a.get("test_set_sha256"),
                                             lesson_prompt_sha256=a.get("lesson_prompt_sha256"))
                                for s, a in sorted(aggs[arm].items())} for arm in ARMS},
               display_rule="Numbers per arm and evaluation as series finish; no verdict and no learning lift until "
                            "every planned series of every arm is done.",
               table=table, games=games,
               series=[{k: v for k, v in a.items() if k != "games"} | dict(games=[{k: v for k, v in g.items()
                                                                                    if k != "loss_sum"}
                                                                                   for g in a["games"]])
                       for arm in ARMS for a in aggs[arm].values()])
    if complete:
        series = sorted(set.intersection(*(set(aggs[a]) for a in ARMS)))
        signal, lift = {}, {}
        for arm in ARMS[1:]:
            rf = [sub(aggs[arm][s]["evaluations"]["T10"]["risks_found"], t0m["risks_found"]) for s in series]
            rs = [sub(aggs[arm][s]["evaluations"]["T10"]["right_safety"], t0m["right_safety"]) for s in series]
            ok = mean(rf) is not None and mean(rs) is not None
            signal[arm] = dict(risks_found_change=mean(rf), risks_found_ci=boot_ci(rf, BOOT_SEED),
                               right_safety_change=mean(rs), right_safety_ci=boot_ci(rs, BOOT_SEED),
                               signal=(mean(rf) >= 10 and mean(rs) >= -5) if ok else None)
        for arm in ARMS:
            own = [sub(aggs[arm][s]["games_error_rate_1_3"], aggs[arm][s]["games_error_rate_8_10"]) for s in series]
            row = dict(lift=mean(own), lift_ci=boot_ci(own, BOOT_SEED))
            if arm != "control":
                vs = [sub(o, sub(aggs["control"][s]["games_error_rate_1_3"], aggs["control"][s]["games_error_rate_8_10"]))
                      for o, s in zip(own, series)]
                row.update(vs_control=mean(vs), vs_control_ci=boot_ci(vs, BOOT_SEED))
            lift[arm] = row
        out.update(signal=signal, learning_lift=lift, paired_series=series)
    OUTPUTS.mkdir(exist_ok=True)
    write_atomic(OUTPUTS / "learning-pilot.json", json.dumps(out, indent=1))
    write_records(aggs, t0)
    return out


def write_records(aggs, t0):
    """learning.jsonl: every pilot game and evaluation by arm and series, the context each decision saw, the lessons;
    seeds.json: dice seeds per series, the option-order seed and the option order of every position."""
    ts = test_set()["positions"]
    seeds = dict(master=MASTER_SEED, option_order_seed=ORDER_SEED, evaluation_set_seed=test_set()["meta"]["seed"],
                 series={s: series_seed(s) for s in sorted({s for a in aggs.values() for s in a})},
                 evaluation_option_order={p["id"]: p["option_order"] for p in ts}, game_option_order={})
    with open(OUTPUTS / "learning.jsonl", "w") as f:
        if t0:
            f.write(json.dumps(dict(kind="evaluation", arm="all", series=None, checkpoint="T0", context="",
                                    answers=[dict(position=r["position_id"], chosen_index=r["chosen_index"],
                                                  invalid=r["invalid"], error=r["error"])
                                             for r in eval_answers(T0_NAME)])) + "\n")
        for arm, by_s in aggs.items():
            for s in sorted(by_s):
                d = run_dir(arm, s)
                m = match_of(arm, s)
                decs = game_decisions(m[0])
                ctx = lambda g: (d / "contexts" / f"after-g{g:02d}.txt").read_text() if g and (d / "contexts" / f"after-g{g:02d}.txt").exists() else ""  # noqa: E731,E501
                for g in range(1, GAMES + 1):
                    gd = [x for x in decs if x["game"] == g]
                    seeds["game_option_order"][f"{arm}/s{s:02d}/g{g:02d}"] = {x["turn_id"]: x["option_order"] for x in gd}
                    lessons = (d / f"lessons-g{g:02d}.txt").read_text().strip() if (d / f"lessons-g{g:02d}.txt").exists() else None
                    f.write(json.dumps(dict(kind="game", arm=arm, series=s, game=g, context=ctx(g - 1),
                                            decisions=[dict(turn_id=x["turn_id"], chosen=x.get("chosen"),
                                                            loss=x.get("loss"), invalid=x["invalid"]) for x in gd],
                                            lessons_written=lessons)) + "\n")
                for cp in CHECKPOINTS if arm != "control" else ():
                    f.write(json.dumps(dict(kind="evaluation", arm=arm, series=s, checkpoint=f"T{cp}", context=ctx(cp),
                                            answers=[dict(position=r["position_id"], chosen_index=r["chosen_index"],
                                                          invalid=r["invalid"], error=r["error"])
                                                     for r in eval_answers(f"{player_name(arm, s)} | T{cp}")])) + "\n")
    (OUTPUTS / "seeds.json").write_text(json.dumps(seeds, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--series", required=True, help="e.g. 1-3")
    r.add_argument("--arms", default=",".join(ARMS))
    sub.add_parser("t0")
    h = sub.add_parser("after-game")
    h.add_argument("--arm", required=True)
    h.add_argument("--series", type=int, required=True)
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "after-game":
        after_game(a.arm, a.series)
    elif a.cmd == "t0":
        run_t0()
    elif a.cmd == "summary":
        print(json.dumps(summary()["series_finished"]))
    else:
        if not (RUNS / "t0/aggregate.json").exists():
            sys.exit("run the shared T0 evaluation first: pilot.py t0")
        tokens("check")  # the after-game hook runs with this interpreter and needs the tokenizer; fail before any game
        init_runner_db()
        lo, hi = (int(x) for x in a.series.split("-"))
        for arm in a.arms.split(","):
            for s in range(lo, hi + 1):
                # A failed series is restarted by its own worker; clear its marker first so the budget arm, which
                # waits on the lessons arm's series, does not see the old failure.
                if not (run_dir(arm, s) / "aggregate.json").exists() and (run_dir(arm, s) / "failed").exists():
                    (run_dir(arm, s) / "failed").rename(run_dir(arm, s) / "failed.previous")
        errors = []

        def worker(arm):
            for s in range(lo, hi + 1):
                try:
                    run_series(arm, s)
                    with LOCK:
                        summary()
                except Exception as e:  # stop this arm; the others go on
                    errors.append(f"{arm} s{s}: {e}")
                    return
        threads = [threading.Thread(target=worker, args=(arm,)) for arm in a.arms.split(",")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        with LOCK:
            summary()
        if errors:
            print("\n".join(errors), file=sys.stderr)
            sys.exit(1)


main()
