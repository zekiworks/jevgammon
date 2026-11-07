"""Learning pilot (learning track, four arms): series of 10 games of Gemma 4 31B (off) against GNUbg weak, the
200-position test before game 1, after game 5 and after game 10 of each series, each with the arm's current
context. Plan: mailbox/Learning pilot - plan 2026-11-07.md (the single source of every rule used here).

    python3 workspace/learning-pilot/pilot.py run --series 1-3 [--arms control,records,lessons,top10]
    python3 workspace/learning-pilot/pilot.py summary

Run from the repo root. One worker per arm, all arms side by side; each arm has one model request in flight at
a time (games are sequential, the test asks one position at a time, the lessons call runs between games), so
spark3 sees at most four. Dice: series s uses one seed in every arm; game g is round ceil(g/2), leg 2 - g % 2
of a 5-round match with --fixed-rounds, so games 2k-1 and 2k are a mirrored pair (same dice, seats swapped).

Private outputs only: smoke/learning-pilot.db (games, test answers), smoke/learning-pilot-plays.db (2-ply
scores), workspace/learning-pilot/runs/ (contexts, logs, per-series aggregates). Nothing here is committed.
"""

import argparse
import hashlib
import json
import os
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
# PILOT_DRY=1: an offline harness check with no model call: the `safest` program plays in Gemma's seat, tests
# and lesson calls are skipped, and everything goes to separate -dry files.
DRY = os.environ.get("PILOT_DRY") == "1"
SUFFIX = "-dry" if DRY else ""
DB = ROOT / f"smoke/learning-pilot{SUFFIX}.db"
PLAYS = ROOT / f"smoke/learning-pilot-plays{SUFFIX}.db"
RUNS = HERE / f"runs{SUFFIX}"
TEST_SET = HERE / "test_set.json"
TEST_POSITIONS = HERE / "test_positions.jsonl"
BASE = json.loads((HERE / "configs/base.json").read_text())
PLAYER = dict(BASE["players"][0], spec="safest") if DRY else BASE["players"][0]
ORDER_SEED = BASE["order_seed"]
SERVER = PLAYER["base_url"]
MODEL = "gemma-4-31B-it"
MASTER_SEED = "learning-pilot 2026-11-07"
GAMES = 10
TESTS_AFTER = (5, 10)  # plus T0 before game 1
ARMS = ["control", "records", "lessons", "top10"]
MARGIN = 0.001  # the site's risk margin (content/thresholds.json risk_margin)
SCALE = 500  # the site's equity scale: error rate = 500 x mean 2-ply equity loss
CONTEXT_LIMIT = 32768  # spark3's max_model_len
PROMPT_MAX = 4389  # largest test prompt (system + user, tokens), measured; game prompts are the same format
NOTE_BUDGET = CONTEXT_LIMIT - PROMPT_MAX - 1500  # tokens left for a context; the rest is margin
TOP_N = 10
# GNUbg's default skill marks (equity lost): doubtful 0.04, bad 0.08, very bad 0.16.
MARKS = [(0.16, "very bad"), (0.08, "bad"), (0.04, "doubtful")]
OPEN = "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
CLOSE = "=== END OF NOTES ==="
LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


# --- Tokens ------------------------------------------------------------------------------------------------

_TOK = None


def tokens(text: str) -> int:
    global _TOK
    if _TOK is None:
        from tokenizers import Tokenizer
        _TOK = Tokenizer.from_file("/home/cbasaran/code/models/gemma-4-31B-it/tokenizer.json")
    return len(_TOK.encode(text).ids)


# --- Test set and scoring ----------------------------------------------------------------------------------

def test_set():
    return json.loads(TEST_SET.read_text())


def test_board_keys():
    return {p["board_key"] for p in test_set()["positions"]}


def play_call(shots, losses, i, margin=MARGIN):
    """tools/site/analysis.py play_call: (class, call, stake, extra hitting rolls)."""
    least = min(shots)
    if all(s == least for s in shots):
        return "none", "none", 0.0, 0
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call, stake, shots[i] - least


LABELS = {"missed": "missed risk", "needless": "needless risk", "wrong_risk": "wrong risk",
          "right_risk": "right risk call (a weaker risky play)", "right_safety": "right safety call (a weaker safe play)",
          "none": "no risk trade-off"}


def score_match(match_id: int):
    """2-ply scores of the match's model decisions (gnubg, tools/site rules), incremental."""
    env = dict(os.environ, SCORE_ARGS=f"{DB} {PLAYS} {match_id}")
    r = subprocess.run(["gnubg", "-t", "-q", "-p", str(HERE / "score_games.py")], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gnubg scoring failed: {r.stderr[-2000:]}")


def game_decisions(match_id: int, upto: int):
    """Scored model decisions of games 1..upto of the match, oldest first, with the game number."""
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    turns = db.execute("""
        SELECT t.id, t.turn_no, t.die1, t.die2, t.position, t.side, t.decided_by, g.round_no, g.leg
        FROM turns t JOIN games g ON g.id = t.game_id
        WHERE g.match_id = ? AND t.player = 1 AND t.decided_by IN ('model', 'fallback') ORDER BY g.round_no, g.leg, t.turn_no""",
                       (match_id,)).fetchall()
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
                 scored=s is not None)
        if s is not None:
            data = json.loads(s[4])
            eq = [x[1] for x in data]
            best = max(eq)
            losses = [best - e for e in eq]
            shots = [x[2] for x in data]
            cls, call, stake, extra = play_call(shots, losses, s[1])
            d.update(chosen=s[1], loss=s[2], board_key=s[3], plays=[x[0] for x in data], descriptions=[x[3] for x in data],
                     best=eq.index(best), losses=losses, shots=shots, cls=cls, call=call)
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
        return "GNUbg's best play"
    for edge, mark in MARKS:
        if d["loss"] >= edge:
            return mark
    return "small error"


def record_line(d, with_verdict: bool) -> str:
    head = f"Turn {d['turn_no']}, dice {d['dice'][0]}-{d['dice'][1]}; {board_text(d['position'], d['side'])}. You played {d['plays'][d['chosen']] or 'no move'}."
    if not with_verdict:
        return head
    return (head + f" GNUbg's best play: {d['plays'][d['best']]}. Equity lost: {d['loss']:.3f} ({verdict(d)}; "
            f"risk call: {LABELS[d['call']]}).")


def game_record(g: int, decs: list, result: dict, with_verdict: bool) -> str:
    res = result.get(g, {})
    outcome = (f"you {'won' if res.get('won') else 'lost'} {res.get('points')} point(s) ({res.get('result')})"
               if res else "result unknown")
    lines = [f"Game {g} ({outcome}):"]
    lines += ["- " + record_line(d, with_verdict) for d in decs]
    return "\n".join(lines)


def eligible(decs, exclude):
    """Scored, valid decisions whose board is not a test position (leakage rule)."""
    return [d for d in decs if d["scored"] and not d["invalid"] and d["board_key"] not in exclude]


def ctx_records(decs, results, exclude, arm, s):
    games = sorted({d["game"] for d in decs})
    blocks = {g: game_record(g, [d for d in eligible(decs, exclude) if d["game"] == g], results, True) for g in games}
    intro = ("Below are the full records of your earlier games in this series against the same opponent: every "
             "decision you made, with the GNUbg engine's verdict (2-ply). Boards are given in your point numbering.")
    kept = list(games)
    while kept:
        text = "\n".join([OPEN, intro, ""] + [blocks[g] + "\n" for g in kept] + [CLOSE])
        if tokens(text) <= NOTE_BUDGET:
            return text
        log(arm, s, "context_truncated", dropped_game=kept[0], tokens=tokens(text), budget=NOTE_BUDGET)
        kept = kept[1:]
    return ""


def ctx_top10(decs, exclude):
    items = sorted(eligible(decs, exclude), key=lambda d: (-d["loss"], d["turn_id"]))[:TOP_N]
    if not items:
        return ""
    lines = [OPEN, f"The {len(items)} decisions from your earlier games in this series that lost the most equity, "
                   "as judged by the GNUbg engine (2-ply). Boards are given in your point numbering.", ""]
    for k, d in enumerate(items, 1):
        lines.append(f"{k}. Dice {d['dice'][0]}-{d['dice'][1]}; {board_text(d['position'], d['side'])}. "
                     f"Your play: {d['plays'][d['chosen']]}. GNUbg's best play: {d['plays'][d['best']]}. "
                     f"Equity lost: {d['loss']:.3f}. Risk call: {LABELS[d['call']]}.")
    lines += ["", CLOSE]
    return "\n".join(lines)


LESSONS_SYSTEM = (HERE / "lessons_system.txt")
LESSONS_USER = (HERE / "lessons_user.txt")


def chat(messages, max_tokens):
    body = dict(model=MODEL, messages=messages, temperature=1.0, max_tokens=max_tokens,
                chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(f"{SERVER}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    started = time.time()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                out = json.loads(r.read())
            return out, time.time() - started, body
        except Exception as e:  # network or server error: retried as the runner does (3 retries)
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def ctx_lessons(decs, results, exclude, arm, s, g, previous):
    """The model rewrites its lessons after game g from that game's record (lessons_user.txt says what it sees)."""
    record = game_record(g, [d for d in eligible(decs, exclude) if d["game"] == g], results,
                         with_verdict=LESSONS_VERDICT)
    user = LESSONS_USER.read_text().format(lessons=previous or "(none yet)", record=record, game=g)
    messages = [{"role": "system", "content": LESSONS_SYSTEM.read_text().strip()}, {"role": "user", "content": user}]
    if DRY:
        return f"- (dry run) lesson after game {g}"
    out, secs, body = chat(messages, LESSONS_MAX_TOKENS)
    text = (out["choices"][0]["message"].get("content") or "").strip()
    usage = out.get("usage", {})
    log(arm, s, "lessons_call", game=g, seconds=round(secs, 2), input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"), finish=out["choices"][0].get("finish_reason"))
    (run_dir(arm, s) / f"lessons-g{g:02d}.json").write_text(json.dumps(dict(request=body, response=out), indent=1))
    return text


LESSONS_VERDICT = True  # whether the game record shown for lesson writing carries GNUbg's verdicts (A17 decides)
LESSONS_MAX_TOKENS = 1024


def lessons_note(lessons: str) -> str:
    if not lessons:
        return ""
    return "\n".join([OPEN, "Lessons you wrote for yourself after your earlier games in this series:", "", lessons,
                      "", CLOSE])


def build_context(arm, s, match_id, g):
    """The arm's context after game g (written to note.txt; read before every play call of the next game)."""
    d = run_dir(arm, s)
    if arm == "control":
        return ""
    exclude = test_board_keys()
    decs = game_decisions(match_id, g)
    excluded = sum(1 for x in decs if x["scored"] and x["board_key"] in exclude)
    if excluded:
        log(arm, s, "test_positions_excluded", game=g, n=excluded)
    results = game_results(match_id)
    if arm == "records":
        return ctx_records(decs, results, exclude, arm, s)
    if arm == "top10":
        return ctx_top10(decs, exclude)
    if arm == "lessons":
        prev_file = d / "lessons.txt"
        previous = prev_file.read_text() if prev_file.exists() else ""
        lessons = ctx_lessons(decs, results, exclude, arm, s, g, previous)
        prev_file.write_text(lessons)
        return lessons_note(lessons)
    raise ValueError(arm)


def write_note(arm, s, g, text):
    d = run_dir(arm, s)
    tmp = d / "note.txt.tmp"
    tmp.write_text(text)
    tmp.replace(d / "note.txt")
    (d / "contexts").mkdir(exist_ok=True)
    (d / "contexts" / f"after-g{g:02d}.txt").write_text(text)
    log(arm, s, "context", after_game=g, tokens=tokens(text) if text else 0, chars=len(text))


# --- Test rounds -------------------------------------------------------------------------------------------

def test_name(arm, s, cp):
    return f"{player_name(arm, s)} | T{cp}"


def run_test(arm, s, cp, note):
    d = run_dir(arm, s)
    if DRY:
        log(arm, s, "test_done", checkpoint=cp, wall_seconds=0, note_tokens=tokens(note) if note else 0, dry=True)
        return 0
    cfg = dict(BASE)
    p = dict(PLAYER, name=test_name(arm, s, cp), parallel=1)
    if note:
        p["prompt_note"] = note
    cfg["players"] = [p]
    path = d / f"test-T{cp}.json"
    path.write_text(json.dumps(cfg, indent=1))
    started = time.time()
    r = subprocess.run([str(BIN), "ask", "--config", str(path), "--positions", str(TEST_POSITIONS), "--out", str(DB),
                        "--setup", p["name"]], cwd=ROOT, capture_output=True, text=True)
    (d / f"test-T{cp}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"test T{cp} failed: {r.stderr[-2000:]}")
    log(arm, s, "test_done", checkpoint=cp, wall_seconds=round(time.time() - started, 1),
        note_tokens=tokens(note) if note else 0)
    return time.time() - started


def test_metrics(name):
    ts = {p["id"]: p for p in test_set()["positions"]}
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("SELECT * FROM answers WHERE setup = ? AND repeat = 1 ORDER BY id", (name,)).fetchall()
    except sqlite3.OperationalError:  # no test asked yet (dry run)
        rows = []
    db.close()
    latest = {}
    for r in rows:
        latest[r["position_id"]] = r
    return position_metrics([(ts[pid], r) for pid, r in latest.items()], expected=len(ts))


def position_metrics(pairs, expected):
    calls = dict(right_risk=0, wrong_risk=0, needless=0, missed=0, right_safety=0, none=0)
    rp = sp = 0
    losses = []
    invalid = failed = 0
    req_ms = tin = tout = 0
    for p, r in pairs:
        req_ms += r["request_ms"] or 0
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
        cls, call, _, _ = play_call(p["shots"], p["losses"], i)
        calls[call] += 1
        rp += cls == "risk"
        sp += cls == "safety"
    taken = calls["right_risk"] + calls["wrong_risk"] + calls["needless"]
    pct = lambda n, d: 100 * n / d if d else None  # noqa: E731
    return dict(
        answered=len(pairs), expected=expected, valid=len(losses), invalid=invalid, failed=failed,
        error_rate=SCALE * sum(losses) / len(losses) if losses else None,
        risk_judgement=50 * (calls["right_risk"] / rp + calls["right_safety"] / sp) if rp and sp else None,
        risks_found=pct(calls["right_risk"], rp), right_safety=pct(calls["right_safety"], sp),
        risk_appetite=pct(taken, rp + sp), risk_pays=rp, safety_pays=sp, calls=calls,
        request_seconds=round(req_ms / 1000, 1), input_tokens=tin, output_tokens=tout, cost_usd=0.0)


# --- Series ------------------------------------------------------------------------------------------------

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


def run_series(arm, s):
    d = run_dir(arm, s)
    if (d / "aggregate.json").exists():
        return
    prior = match_of(arm, s)
    if prior is not None:
        # A series cut off part-way is played again from game 1 with the same dice (logged); its old match stays.
        log(arm, s, "series_restarted", old_match=prior[0], old_status=prior[1])
        for f in ["note.txt", "lessons.txt"]:
            (d / f).unlink(missing_ok=True)
    d.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log(arm, s, "series_start", seed=series_seed(s))
    run_test(arm, s, 0, "")
    (d / "note.txt").write_text("")
    cfg = dict(PLAYER, name=player_name(arm, s), prompt_note_file=str(d / "note.txt"), parallel=1)
    (d / "player.json").write_text(json.dumps(cfg, indent=1))
    hook = f"{sys.executable} {Path(__file__).resolve()} after-game --arm {arm} --series {s}"
    r = subprocess.run([str(BIN), "--model1-config", str(d / "player.json"), "--model2", "gnubg-weak",
                        "--seed", str(series_seed(s)), "--order-seed", str(ORDER_SEED), "--rounds", str(GAMES // 2),
                        "--fixed-rounds", "--clock", "0", "--max-turns", str(BASE["max_turns"]),
                        "--prompt-version", BASE["prompt_version"], "--quiet", "--db", str(DB), "--after-game", hook],
                       cwd=ROOT, capture_output=True, text=True)
    (d / "match.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        log(arm, s, "series_failed", stderr=r.stderr[-2000:])
        raise RuntimeError(f"{arm} s{s}: match failed: {r.stderr[-1000:]}")
    write_aggregate(arm, s, time.time() - started)


def after_game(arm, s):
    match_id = int(os.environ["MATCH_ID"])
    g = 2 * (int(os.environ["GAME_ROUND"]) - 1) + int(os.environ["GAME_LEG"])
    score_match(match_id)
    text = build_context(arm, s, match_id, g)
    write_note(arm, s, g, text)
    if g in TESTS_AFTER:
        run_test(arm, s, g, text)


def game_metrics(match_id):
    decs = game_decisions(match_id, GAMES)
    results = game_results(match_id)
    out = []
    for g in range(1, GAMES + 1):
        gd = [d for d in decs if d["game"] == g]
        valid = [d for d in gd if d["scored"] and not d["invalid"]]
        out.append(dict(game=g, decisions=len(gd), invalid=sum(d["invalid"] for d in gd),
                        unscored=sum(not d["scored"] for d in gd),
                        error_rate=SCALE * sum(d["loss"] for d in valid) / len(valid) if valid else None,
                        loss_sum=sum(d["loss"] for d in valid), valid=len(valid),
                        **{k: v for k, v in results.get(g, {}).items() if k in ("won", "result", "points", "turns")}))
    return out


def pooled_rate(games, lo, hi):
    sel = [x for x in games if lo <= x["game"] <= hi]
    n = sum(x["valid"] for x in sel)
    return SCALE * sum(x["loss_sum"] for x in sel) / n if n else None


def write_aggregate(arm, s, wall):
    d = run_dir(arm, s)
    m = match_of(arm, s)
    games = game_metrics(m[0])
    events = [json.loads(l) for l in (d / "log.jsonl").read_text().splitlines()]
    ctx = [e for e in events if e["event"] == "context"]
    agg = dict(
        arm=arm, series=s, seed=series_seed(s), match_id=m[0], finished_at=now(), wall_seconds=round(wall, 1),
        tests={f"T{cp}": test_metrics(test_name(arm, s, cp)) for cp in (0,) + TESTS_AFTER},
        games=[{k: v for k, v in x.items() if k != "loss_sum"} for x in games],
        games_error_rate_1_3=pooled_rate(games, 1, 3), games_error_rate_8_10=pooled_rate(games, 8, 10),
        context_tokens_after_game={e["after_game"]: e["tokens"] for e in ctx},
        context_truncations=[{k: e[k] for k in ("dropped_game", "tokens", "budget")} for e in events
                             if e["event"] == "context_truncated"],
        test_positions_excluded=sum(e["n"] for e in events if e["event"] == "test_positions_excluded"),
        lessons_calls=[{k: e.get(k) for k in ("game", "seconds", "input_tokens", "output_tokens", "finish")}
                       for e in events if e["event"] == "lessons_call"],
        restarts=sum(e["event"] == "series_restarted" for e in events), cost_usd=0.0)
    a, b = agg["games_error_rate_1_3"], agg["games_error_rate_8_10"]
    agg["games_lift"] = a - b if a is not None and b is not None else None
    (d / "aggregate.json").write_text(json.dumps(agg, indent=1))


# --- Summary -----------------------------------------------------------------------------------------------

def summary(planned: int):
    aggs = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for f in sorted((RUNS / arm).glob("s*/aggregate.json")) if (RUNS / arm).exists() else []:
            aggs[arm].append(json.loads(f.read_text()))
    keys = ["error_rate", "risk_judgement", "risks_found", "right_safety", "risk_appetite"]
    mean = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    table = {}
    for arm, rows in aggs.items():
        table[arm] = {}
        for cp in ["T0", "T5", "T10"]:
            ms = [r["tests"][cp] for r in rows]
            table[arm][cp] = {k: mean([m[k] for m in ms if m[k] is not None]) for k in keys}
            table[arm][cp].update(invalid=sum(m["invalid"] for m in ms), failed=sum(m["failed"] for m in ms),
                                  request_seconds=sum(m["request_seconds"] for m in ms), cost_usd=0.0,
                                  series=len(ms))
    done = {arm: len(rows) for arm, rows in aggs.items()}
    complete = all(n >= planned for n in done.values())
    out = dict(updated_at=now(), planned_series_per_arm=planned, series_done=done, complete=complete,
               display_rule="Numbers per arm x test round as series finish; no verdict and no learning lift until "
                            "all planned series of every arm are done.",
               table=table,
               series=[{k: v for k, v in r.items()} for rows in aggs.values() for r in rows])
    if complete:
        lift = {arm: mean([r["games_lift"] for r in rows if r["games_lift"] is not None]) for arm, rows in aggs.items()}
        out["learning_lift"] = dict(per_arm=lift, vs_control={a: (lift[a] - lift["control"]) if lift[a] is not None
                                                               and lift["control"] is not None else None
                                                               for a in ARMS if a != "control"})
    (HERE / "learning-pilot.json").write_text(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--series", required=True, help="e.g. 1-3")
    r.add_argument("--arms", default=",".join(ARMS))
    r.add_argument("--planned", type=int, default=10)
    h = sub.add_parser("after-game")
    h.add_argument("--arm", required=True)
    h.add_argument("--series", type=int, required=True)
    sm = sub.add_parser("summary")
    sm.add_argument("--planned", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "after-game":
        after_game(a.arm, a.series)
    elif a.cmd == "summary":
        print(json.dumps(summary(a.planned)["series_done"]))
    else:
        lo, hi = (int(x) for x in a.series.split("-"))
        errors = []

        def worker(arm):
            for s in range(lo, hi + 1):
                try:
                    run_series(arm, s)
                    with LOCK:
                        summary(a.planned)
                except Exception as e:  # stop this arm; the others go on
                    errors.append(f"{arm} s{s}: {e}")
                    return
        threads = [threading.Thread(target=worker, args=(arm,)) for arm in a.arms.split(",")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        summary(a.planned)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            sys.exit(1)


main()
