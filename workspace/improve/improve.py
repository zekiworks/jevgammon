"""Did they improve? (pre-registration: mailbox/Did they improve - plan 2026-11-08.md, the single source).

Per model, at its leaderboard setting: 5 series of 10 games against GNUbg weak with one lesson call after each game
(the pilot's lesson prompt and cut rule), the 200-position test after game 10 of every series (T10) with that
series' lessons, and 3 empty runs of the same test interleaved through the run. One model's steps run one at a
time, in this order: E1, S1, (cost check), S2, E2, S3, S4, E3, S5.

    python3 workspace/improve/improve.py run --model qwen3.8-flash-off [--until S1] [--base-url URL]
    python3 workspace/improve/improve.py status [--model KEY]
    python3 workspace/improve/improve.py summary
    IMPROVE_DRY=1 python3 workspace/improve/improve.py run --model qwen3.8-flash-off --until S1   # no model call

Code lives on branch `improve` (this worktree); the runner binary is this worktree's target/release/jevgammon.
Private outputs go next to v3.db (IMPROVE_ROOT, default /home/cbasaran/code/jevgammon), never committed:
smoke/improve/<key>.db (games, test answers, every request), smoke/improve/<key>-plays.db (2-ply scores),
workspace/improve/runs/<key>/ (lessons, contexts, logs, step ledgers), workspace/improve/out/improve.json (the
page's aggregates; no test position, no per-position answer). IMPROVE_DRY=1: the `safest` program plays and
answers in the model's seat, lessons are canned, nothing is billed; everything goes to *-dry paths.

Money (plan §9): billed models (OpenRouter) carry a hard budget ledger per step attempt whose cap is
min(1.5 x estimate - model billed, $110 - total billed, live balance - $5); every request reserves its worst case
before it is sent (the runner's ledger), so a cap is enforced before a request starts. Before every billed step:
rule (b) (total + expected step cost > $110: stop) and the balance check (balance - $5 < expected: pause). After
E1 and S1: rule (a) (5 x S1 + 3 x E1 > 1.5 x estimate: stop).
"""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
BIN = Path(os.environ.get("IMPROVE_BIN", CODE / "target/release/jevgammon"))  # a lane may pin a copy
STATE_ROOT = Path(os.environ.get("IMPROVE_ROOT", "/home/cbasaran/code/jevgammon"))
DRY = os.environ.get("IMPROVE_DRY") == "1"
SUFFIX = "-dry" if DRY else ""
V3_DB = STATE_ROOT / "v3.db"
PILOT_PRIVATE = STATE_ROOT / "workspace/learning-pilot"
TEST_SET = PILOT_PRIVATE / "test_set.json"
TEST_POSITIONS = PILOT_PRIVATE / "test_positions.jsonl"
PILOT_CODE = CODE / "workspace/learning-pilot"
LESSONS_SYSTEM = PILOT_CODE / "lessons_system.txt"
LESSONS_USER = PILOT_CODE / "lessons_user.txt"
SCORER = PILOT_CODE / "score_games.py"
SMOKE = STATE_ROOT / f"smoke/improve{SUFFIX}"
RUNS = STATE_ROOT / f"workspace/improve/runs{SUFFIX}"
OUT = STATE_ROOT / f"workspace/improve/out{SUFFIX}"
PLAN = STATE_ROOT / "mailbox/Did they improve - plan 2026-11-08.md"

# Fixed by the plan.
PLAN_SHA256 = "85a970d09cf1ae40d5567a7540ec0f607133314589119391bd71584b5ef78542"  # main 7e2bf78
LESSON_PROMPT_SHA256 = "d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e"
TEST_SET_SHA256 = "6c92e7416745125ca3ea09c9e41e450a52716f8ad018772278b07f992f7318e6"
TEST_POSITIONS_SHA256 = "ff509ea102b4fcd2faca3402d585b05ba6d7dc0014a7c5f9dabbe48b13a3467f"
MASTER_SEED = "learning-pilot 2026-11-07"  # the pilot's dice, series 1-5
ORDER_SEED = 1190975713392774006  # League 2's option-order seed
PROMPT_VERSION = "bg-v2"
TEST_CONTEXT = dict(rounds=3, max_turns=300, clock=0)  # the pilot's test config (base.json)
GAMES = 10
SERIES = 5
EMPTY_RUNS = 3
POSITIONS = 200
STEPS = ["E1", "S1", "S2", "E2", "S3", "S4", "E3", "S5"]
TEST_PARALLEL = 4
FLOOR_POINTS = 5.0
SAFETY_DROP = 5.0
TOTAL_CAP_USD = 110.0
ESTIMATE_FACTOR = 1.5
BALANCE_RESERVE_USD = 5.0
MAX_LESSONS, MAX_WORDS = 5, 150
OPEN = "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
CLOSE = "=== END OF NOTES ==="
LESSONS_INTRO = "Lessons you wrote for yourself after your earlier games in this series, oldest first:"
MARGIN = 0.001  # the site's risk margin
SCALE = 500  # error rate = 500 x mean 2-ply equity loss
MARKS = [(0.16, "very bad"), (0.08, "bad"), (0.04, "doubtful")]
CREDITS_URL = "https://openrouter.ai/api/v1/credits"
STOP, PAUSE = 2, 3  # exit codes of `run`

# The 15 chat models (plan §3). `settings` = the v3.db setup whose players.settings is used unchanged except name,
# parallel, prompt_note_file, budget and (local servers) base_url. Billed models: list prices for the ledger, the
# plan's estimates (§9), and the OpenRouter response fields every response must carry (route check).
MODELS = {
    "qwen3.8-flash-off": dict(setup="Qwen3.8 Flash (off)", lane="openrouter", billed=True,
                              estimate=2.30, S=0.35, E=0.18, price=(0.15, 0.016, 0.47),
                              expect=dict(models=["qwen/qwen3.8-flash", "qwen/qwen3.8-flash-20260826"],
                                          provider="Alibaba")),
    "glm-5.3-on": dict(setup="GLM-5.3 (on)", lane="openrouter", billed=True,
                       estimate=22.00, S=3.35, E=1.75, price=(1.4, 0.26, 4.4),
                       expect=dict(models=["z-ai/glm-5.3", "z-ai/glm-5.3-20260816"], provider="Fireworks")),
    "kimi-k3.1-pro-off": dict(setup="Kimi K3.1 Pro (off)", lane="openrouter", billed=True,
                              estimate=35.00, S=5.34, E=2.77, price=(2.0, 0.2, 10.0),
                              expect=dict(models=["moonshotai/kimi-k3.1-pro", "moonshotai/kimi-k3.1-pro-20261023"],
                                          provider="Moonshot AI")),
    "deepseek-v4.1-flash-on": dict(setup="DeepSeek V4.1 Flash (on)", lane="openrouter", billed=True,
                                   estimate=44.00, S=6.96, E=3.07, price=(0.3, 0.006, 1.2),
                                   expect=dict(models=["deepseek/deepseek-v4.1-flash",
                                                       "deepseek/deepseek-v4.1-flash-20260910"],
                                               provider="Fireworks")),
    # Subscriptions: the identity each route's reply carries, as the league's own stored replies of the setup show it
    # (Antigravity: response.modelVersion; Anthropic and xAI: model). Claude: a 429 usage-limit reply pauses.
    "gemini-3.8-flash-high": dict(setup="Gemini 3.8 Flash (high)", lane="subscription",
                                  expect=dict(models=["gemini-3.8-flash"], model_pointer="/response/modelVersion")),
    "claude-sonnet-5.5-high": dict(setup="Claude Sonnet 5.5 (high)", lane="subscription", quota_pause=True,
                                   expect=dict(models=["claude-sonnet-5-5"])),
    "claude-opus-5.5-on": dict(setup="Claude Opus 5.5 (on)", lane="subscription", quota_pause=True,
                               expect=dict(models=["claude-opus-5-5"])),
    "gemini-4-argon-on": dict(setup="Gemini 4 Argon (on)", lane="subscription",
                              expect=dict(models=["gemini-4-argon", "gemini-4-argon-d"], model_pointer="/response/modelVersion")),
    "grok-4.7-on": dict(setup="Grok 4.7 (on)", lane="subscription", expect=dict(models=["grok-4.7"])),
    "claude-fable-5.1-on": dict(setup="Claude Fable 5.1 (on)", lane="subscription", quota_pause=True,
                                expect=dict(models=["claude-fable-5-1"])),
    "gemma-4-31b-on": dict(setup="Gemma 4 31B (on)", lane="local", expect=dict(models=["gemma-4-31B-it"])),
    "qwen3.8-27b-on": dict(setup="Qwen3.8-27B (on)", lane="local", expect=dict(models=["qwen3.8-27b"])),
    "lfm2.5-24b-a2b-on": dict(setup="LFM2.5-24B-A2B (on)", lane="local", expect=dict(models=["lfm2.5-24b-a2b"])),
    # Codex: the stream's served model (response.completed -> response.model), checked against the requested id (a
    # dated snapshot of it allowed): the league stored the answer text only, so there is no league evidence.
    "gpt-6.1-sol-high": dict(setup="GPT-6.1 Sol (high)", lane="subscription",
                             expect=dict(models=["gpt-6.1-sol"], allow_dated=True)),
    "gpt-6-astra-high": dict(setup="GPT-6 Astra (high)", lane="subscription",
                             expect=dict(models=["gpt-6-astra"], allow_dated=True)),
}


class Stop(Exception):
    """A pre-registered stop rule fired (rule a or b, a route check): the model stops."""


class Pause(Exception):
    """The live balance does not cover the next step: pause there and resume later."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def lesson_prompt_sha256() -> str:
    return hashlib.sha256(LESSONS_SYSTEM.read_bytes() + LESSONS_USER.read_bytes()).hexdigest()


def write_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")  # writers in several processes never share a temp file
    tmp.write_text(text)
    tmp.replace(path)


def series_seed(s: int) -> int:
    """The pilot's dice for series s (pilot.py series_seed)."""
    return int(hashlib.sha256(f"{MASTER_SEED} series {s}".encode()).hexdigest()[:16], 16) & (2**63 - 1)


# --- Paths and names -------------------------------------------------------------------------------------------

def mdir(key):
    return RUNS / key


def step_dir(key, step):
    return mdir(key) / step


def db_path(key):
    return SMOKE / f"{key}.db"


def plays_path(key):
    return SMOKE / f"{key}-plays.db"


def series_of(step):
    return int(step[1:]) if step.startswith("S") else None


def attempt_of(key, step):
    """The current attempt of a series step: 1 + archived attempts."""
    return 1 + sum(1 for _ in step_dir(key, step).glob("attempt-*"))


def game_name(key, s, attempt):
    return f"{MODELS[key]['setup']} | improve | s{s:02d} | a{attempt}"


def test_name(key, step, attempt=None):
    if step.startswith("E"):
        return f"{MODELS[key]['setup']} | improve | {step}"
    return f"{game_name(key, series_of(step), attempt)} | T10"


def log(key, event, **kw):
    mdir(key).mkdir(parents=True, exist_ok=True)
    with open(mdir(key) / "log.jsonl", "a") as f:
        f.write(json.dumps(dict(at=now(), event=event, **kw)) + "\n")


def events(key):
    f = mdir(key) / "log.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []


# --- Player config ---------------------------------------------------------------------------------------------

def league_settings(setup: str) -> dict:
    db = sqlite3.connect(f"file:{V3_DB}?mode=ro", uri=True, timeout=60)
    row = db.execute("SELECT settings FROM players WHERE name = ?", (setup,)).fetchone()
    db.close()
    if row is None:
        raise SystemExit(f"no setup {setup!r} in {V3_DB}")
    return json.loads(row[0])


def player_config(key, name, parallel, note_file=None, ledger=None, base_url=None) -> dict:
    """The leaderboard setup's settings, unchanged except name, parallel, prompt_note_file, budget, base_url."""
    m = MODELS[key]
    p = league_settings(m["setup"])
    if DRY:
        p = dict(name=name, spec="safest", note="dry run: the safest program in the model's seat")
    p.update(name=name, parallel=parallel)
    p.pop("max_matches", None)
    if note_file is not None:
        p["prompt_note_file"] = str(note_file)
    if base_url:
        p["base_url"] = base_url
    if ledger is not None and not DRY:
        cin, ccached, cout = m["price"]
        p["budget"] = dict(ledger=str(ledger["path"]), cap_usd=round(ledger["cap"], 6), input_per_mtok=cin,
                           cached_input_per_mtok=ccached, output_per_mtok=cout)
    if m.get("expect") and not DRY:
        # Every response is checked by the runner before it is used (llm::route_identity); a failure stops the
        # player's requests and is logged with its raw response here.
        p["expect_route"] = dict({k: v for k, v in m["expect"].items() if v is not None},
                                 reject_log=str(mdir(key) / "route-rejections.jsonl"))
    if m.get("quota_pause") and not DRY:
        p["quota_pause"] = True  # Claude: a 429 usage-limit reply ends the request at once; the run pauses
    return p


def base_url_of(key):
    f = mdir(key) / "base_url.txt"
    return f.read_text().strip() if f.exists() else None


# --- Money -----------------------------------------------------------------------------------------------------

def ledger_spent(path: Path):
    """(booked, reported, reserved_open) of one ledger: booked = settled cost + lost worst cases."""
    if not path.exists():
        return 0.0, 0.0, 0.0
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    try:
        booked, reported, reserved = db.execute(
            "SELECT COALESCE(SUM(CASE status WHEN 'settled' THEN cost_usd WHEN 'lost' THEN reserved_usd END), 0),"
            "       COALESCE(SUM(reported_cost_usd), 0),"
            "       COALESCE(SUM(CASE status WHEN 'open' THEN reserved_usd END), 0) FROM attempts").fetchone()
    except sqlite3.OperationalError:
        booked = reported = reserved = 0.0
    db.close()
    return booked, reported, reserved


def ledgers(key, step=None):
    d = mdir(key) / "ledgers"
    if not d.exists():
        return []
    return sorted(d.glob(f"{step}-a*.db" if step else "*.db"))


def billed(key, step=None) -> float:
    """Booked dollars of a model (or one of its steps), open reservations included (they count until settled)."""
    return sum(b + r for b, _, r in map(ledger_spent, ledgers(key, step)))


def reported(key) -> float:
    return sum(x for _, x, _ in map(ledger_spent, ledgers(key)))


def billed_total(keys=None) -> float:
    return sum(billed(k) for k in (keys or MODELS) if MODELS[k].get("billed"))


def step_estimate(key, step) -> float:
    """Expected cost of a step: the plan's S or E until the cost check, then the model's measured S1 or E1."""
    m = MODELS[key]
    if cost_check(key) is not None:
        return billed(key, "S1") if step.startswith("S") else billed(key, "E1")
    return m["S"] if step.startswith("S") else m["E"]


def cost_check(key):
    f = mdir(key) / "cost_check.json"
    return json.loads(f.read_text()) if f.exists() else None


def projected_full(s1: float, e1: float) -> float:
    """Plan §9: projected full cost = 5 x S1 + 3 x E1."""
    return SERIES * s1 + EMPTY_RUNS * e1


def rule_a(key, s1: float, e1: float):
    """None, or the reason rule (a) fires: projected full cost > 1.5 x the model's estimate."""
    limit = ESTIMATE_FACTOR * MODELS[key]["estimate"]
    p = projected_full(s1, e1)
    if round(p, 6) > round(limit, 6):  # cents compared exactly, not 1.5 x 2.30 = 3.4499...
        return (f"rule (a): projected full cost ${p:.2f} (5 x S1 ${s1:.2f} + 3 x E1 ${e1:.2f}) > 1.5 x estimate "
                f"${MODELS[key]['estimate']:.2f} = ${limit:.2f}")
    return None


def rule_b(total: float, expected: float):
    if round(total + expected, 6) > TOTAL_CAP_USD:
        return (f"rule (b): billed total ${total:.2f} + expected step cost ${expected:.2f} would pass "
                f"${TOTAL_CAP_USD:.0f}")
    return None


def share_cap():
    """The experiment's share of the shared balance (Main), a pause limit below $110; None = no share limit."""
    f = RUNS / "share_cap.json"
    return json.loads(f.read_text())["usd"] if f.exists() else None


def share_exceeded(total: float, expected: float, share):
    if share is not None and round(total + expected, 6) > share:
        return (f"share limit: billed total ${total:.2f} + expected step cost ${expected:.2f} would pass this "
                f"experiment's share ${share:.2f}")
    return None


def balance_shortfall(balance: float, expected: float):
    if round(balance - BALANCE_RESERVE_USD, 6) < round(expected, 6):
        return (f"balance ${balance:.2f} - ${BALANCE_RESERVE_USD:.0f} reserve does not cover the step's expected "
                f"cost ${expected:.2f}")
    return None


def ledger_cap(key, balance: float, model_billed: float, total: float, share=None):
    """The step ledger's hard cap and the limit that binds it (rule a or b: stop; balance or share: pause)."""
    limits = {"rule (a) limit": ESTIMATE_FACTOR * MODELS[key]["estimate"] - model_billed,
              "rule (b) limit": TOTAL_CAP_USD - total,
              "balance": balance - BALANCE_RESERVE_USD}
    if share is not None:
        limits["share"] = share - total
    binding = min(limits, key=limits.get)
    return limits[binding], binding, limits


def openrouter_balance() -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise Pause("OPENROUTER_API_KEY is not set: the live balance cannot be read")
    req = urllib.request.Request(CREDITS_URL, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())["data"]
    return dict(total_credits=d["total_credits"], total_usage=d["total_usage"],
                balance=d["total_credits"] - d["total_usage"], at=now())


def money_gate(key, step, balance_reader=openrouter_balance):
    """Before a billed step: rule (b), then the live balance. Returns the step ledger's cap and its record."""
    expected = step_estimate(key, step)
    total = billed_total()
    why = rule_b(total, expected)
    if why:
        raise Stop(why)
    share = share_cap()
    why = share_exceeded(total, expected, share)
    if why:
        raise Pause(why)
    bal = balance_reader()
    why = balance_shortfall(bal["balance"], expected)
    if why:
        raise Pause(why)
    cap, binding, limits = ledger_cap(key, bal["balance"], billed(key), total, share)
    return dict(step=step, expected=expected, billed_total=total, model_billed=billed(key), credits=bal, cap=cap,
                binding=binding, limits=limits, share=share)


# --- Lessons ---------------------------------------------------------------------------------------------------

def limit_lessons(text):
    """The pilot's cut rule (pilot.py limit_lessons): lines starting '- ' are lessons (if none, every non-empty line
    is one); at most 5 lessons and 150 words: extra lessons, then extra words, are cut."""
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
    cut.update(lessons_kept=len(out), words_kept=words,
               cut=cut["lessons_written"] > len(out) or cut["words_written"] > words)
    return "\n".join(out), cut


def lessons_context(blocks):
    """The play call's note: every lesson so far in the series, oldest first, between the pilot's delimiters."""
    blocks = [(g, t) for g, t in blocks if t]
    if not blocks:
        return ""
    return "\n".join([OPEN, LESSONS_INTRO, ""] + [f"After game {g}:\n{t}\n" for g, t in blocks] + [CLOSE])


# --- Game records (the pilot's) ----------------------------------------------------------------------------------

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


def test_set():
    return json.loads(TEST_SET.read_text())


def test_board_keys():
    return {p["board_key"] for p in test_set()["positions"]}


def score_match(key, match_id):
    env = dict(os.environ, SCORE_ARGS=f"{db_path(key)} {plays_path(key)} {match_id}")
    r = subprocess.run(["nice", "-n", "19", "gnubg", "-t", "-q", "-p", str(SCORER)], cwd=CODE, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gnubg scoring failed: {r.stderr[-2000:]}")


def game_decisions(key, match_id, upto=GAMES):
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
    db.row_factory = sqlite3.Row
    turns = db.execute("""
        SELECT t.id, t.turn_no, t.die1, t.die2, t.position, t.side, t.decided_by, t.in_flight, g.round_no, g.leg
        FROM turns t JOIN games g ON g.id = t.game_id
        WHERE g.match_id = ? AND t.player = 1 AND t.decided_by IN ('model', 'fallback')
        ORDER BY g.round_no, g.leg, t.turn_no""", (match_id,)).fetchall()
    db.close()
    scored = {}
    if plays_path(key).exists():
        pdb = sqlite3.connect(f"file:{plays_path(key)}?mode=ro", uri=True, timeout=60)
        scored = {r[0]: r for r in pdb.execute(
            "SELECT turn_id, chosen, loss, board_key, data FROM plays WHERE match_id = ?", (match_id,))}
        pdb.close()
    out = []
    for t in turns:
        g = 2 * (t["round_no"] - 1) + t["leg"]
        if g > upto:
            continue
        s = scored.get(t["id"])
        d = dict(turn_id=t["id"], game=g, turn_no=t["turn_no"], dice=(t["die1"], t["die2"]),
                 position=json.loads(t["position"]), side=t["side"], invalid=t["decided_by"] == "fallback",
                 scored=s is not None, in_flight=t["in_flight"])
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


def game_results(key, match_id):
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
    rows = db.execute("SELECT round_no, leg, winner_player, result, points FROM games WHERE match_id = ?",
                      (match_id,)).fetchall()
    db.close()
    return {2 * (r[0] - 1) + r[1]: dict(won=r[2] == 1, result=r[3], points=r[4]) for r in rows}


def board_text(position, side):
    sys.path.insert(0, str(CODE / "tools" / "v3"))
    from rules import from_json
    pts, bar, off = from_json(position, side)
    mine = " ".join(f"{i + 1}:{n}" for i, n in enumerate(pts) if n > 0)
    theirs = " ".join(f"{i + 1}:{-n}" for i, n in enumerate(pts) if n < 0)
    return (f"your checkers {mine or '-'} (bar {bar[0]}, off {off[0]}); "
            f"opponent's checkers {theirs or '-'} (bar {bar[1]}, off {off[1]})")


def mark_of(d):
    if d["loss"] < 1e-9:
        return "best play"
    for edge, mark in MARKS:
        if d["loss"] >= edge:
            return mark
    return "small error"


def record_line(d):
    return (f"- Turn {d['turn_no']}, dice {d['dice'][0]}-{d['dice'][1]}; {board_text(d['position'], d['side'])}. "
            f"You played {d['plays'][d['chosen']]}. GNUbg's best play: {d['plays'][d['best']]}. "
            f"Equity lost: {d['loss']:.3f} ({mark_of(d)}; risk call: {LABELS[d['call']]}).")


def game_header(g, results):
    res = results.get(g)
    outcome = (f"you {'won' if res['won'] else 'lost'} {res['points']} point(s), {res['result']}" if res
               else "result unknown")
    return f"Game {g} ({outcome}):"


def eligible(decs, exclude):
    """Scored, valid decisions whose board is not a test position (the pilot's leakage rule)."""
    return [d for d in decs if d["scored"] and not d["invalid"] and d["board_key"] not in exclude]


# --- Steps -----------------------------------------------------------------------------------------------------

def ensure_runner_db(key):
    """Create the runner's schema once (`jevgammon rank --dry-run` opens the file, then stops: no such league)."""
    SMOKE.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(BIN), "rank", "--db", str(db_path(key)), "--dry-run", "--scores", str(HERE)], cwd=CODE,
                   capture_output=True, text=True)
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master")}
    db.close()
    if not {"matches", "games", "turns"} <= tables:
        raise SystemExit(f"could not create the runner schema in {db_path(key)}")


def vllm_load(key):
    """Running and waiting requests of a local vLLM server (/metrics), or None."""
    url = base_url_of(key) or (league_settings(MODELS[key]["setup"]).get("base_url") if not DRY else None)
    if MODELS[key]["lane"] != "local" or not url or DRY:
        return None
    try:
        with urllib.request.urlopen(url.rsplit("/v1", 1)[0] + "/metrics", timeout=10) as r:
            text = r.read().decode()
    except Exception as e:  # recorded, never fatal
        return dict(error=str(e)[:200])
    out = {}
    for line in text.splitlines():
        for name in ("vllm:num_requests_running", "vllm:num_requests_waiting"):
            if line.startswith(name):
                out[name.split(":")[1]] = float(line.rsplit(" ", 1)[1])
    return out


def fit_check(key, fetch=None):
    """Local servers (plan §10): the KV cache must hold at least 4 sequences at the full max-model-len (the tests'
    4 in flight). Reads /v1/models (max_model_len) and /metrics (vllm:cache_config_info num_gpu_blocks, block_size).
    Returns the record; raises SystemExit (the run does not start) on a shortfall or an unreadable server."""
    url = base_url_of(key) or league_settings(MODELS[key]["setup"]).get("base_url")
    fetch = fetch or (lambda u: urllib.request.urlopen(u, timeout=20).read().decode())
    try:
        models = json.loads(fetch(f"{url}/models"))["data"]
        max_len = max(int(x["max_model_len"]) for x in models)
        info = next(line for line in fetch(url.rsplit("/v1", 1)[0] + "/metrics").splitlines()
                    if line.startswith("vllm:cache_config_info{"))
        fields = dict(part.split("=", 1) for part in info[info.index("{") + 1:info.index("}")].split(","))
        blocks, block = int(fields["num_gpu_blocks"].strip('"')), int(fields["block_size"].strip('"'))
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"{key}: fit check could not read the server at {url}: {e}") from None
    rec = dict(url=url, max_model_len=max_len, kv_tokens=blocks * block, sequences=blocks * block / max_len)
    log(key, "fit_check", **rec)
    if rec["sequences"] < TEST_PARALLEL:
        raise SystemExit(f"{key}: KV cache holds {rec['sequences']:.2f} sequences of {max_len} tokens, "
                         f"fewer than {TEST_PARALLEL}: not started")
    return rec


def run_test(key, step, name, note, workdir, ledger=None, rounds=30):
    """The 200-position test with `note` (empty = the league request) and 4 decisions in flight; failed requests
    are asked again (same prompt and context) until 200 of 200 or the rounds run out (resumable)."""
    workdir.mkdir(parents=True, exist_ok=True)
    cfg = dict(TEST_CONTEXT, prompt_version=PROMPT_VERSION, order_seed=ORDER_SEED,
               players=[dict(player_config(key, name, TEST_PARALLEL, ledger=ledger, base_url=base_url_of(key)),
                             **({"prompt_note": note} if note else {}))])
    path = workdir / f"test-{step}.json"
    path.write_text(json.dumps(cfg, indent=1))
    route = answer_error(key, name, "ROUTE CHECK") if db_path(key).exists() else None
    if route:  # never re-ask a test whose replies failed the route check
        raise Stop(f"{step}: {route[:600]}")
    load_before = vllm_load(key)
    started = time.time()
    for k in range(rounds):
        r = subprocess.run([str(BIN), "ask", "--config", str(path), "--positions", str(TEST_POSITIONS), "--out",
                            str(db_path(key)), "--setup", name], cwd=CODE, capture_output=True, text=True)
        with open(workdir / f"test-{step}.log", "a") as f:
            f.write(f"--- {now()} round {k + 1}\n{r.stdout}{r.stderr}")
        m = test_metrics(key, name)
        route = answer_error(key, name, "ROUTE CHECK")
        if route:
            raise Stop(f"{step}: {route[:600]}")
        quota = answer_error(key, name, "QUOTA:")
        if quota:
            raise Pause(f"{step}: usage limit (429) on the subscription: {quota[:600]}")
        budget = answer_error(key, name, "BUDGET CAP")
        if budget:
            raise BudgetRefused(budget)
        if r.returncode != 0 and m["answered"] == 0:
            raise RuntimeError(f"test {name} failed: {r.stderr[-1500:]}")
        if m["answered"] == POSITIONS and m["failed"] == 0:
            break
        time.sleep(min(600, 30 * (k + 1)))  # quota waits
    m = test_metrics(key, name)
    m.update(wall_seconds=round(time.time() - started, 1), load_before=load_before, load_after=vllm_load(key))
    return m


class BudgetRefused(Exception):
    """The step ledger refused a request (its cap): stop or pause, by the binding limit."""


def answer_error(key, name, marker):
    """The first stored test error of `name` carrying `marker` (BUDGET CAP, ROUTE CHECK), or None."""
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
    try:
        row = db.execute("SELECT error FROM answers WHERE setup = ? AND error LIKE ? LIMIT 1",
                         (name, f"%{marker}%")).fetchone()
    except sqlite3.OperationalError:
        row = None
    db.close()
    return row[0] if row else None


def test_answers(key, name):
    if not db_path(key).exists():
        return []
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
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


def metrics_from(rows, positions):
    """Shares over valid answers (the site's): risks found, right safety, error rate; invalid and failed counted."""
    calls = dict(right_risk=0, wrong_risk=0, needless=0, missed=0, right_safety=0, none=0)
    rp = sp = invalid = failed = 0
    losses, in_flight = [], []
    for r in rows:
        p = positions[r["position_id"]]
        if r["in_flight"] is not None:
            in_flight.append(r["in_flight"])
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
    pct = lambda n, d: 100 * n / d if d else None  # noqa: E731
    return dict(answered=len(rows), expected=POSITIONS, valid=len(losses), invalid=invalid, failed=failed,
                risk_pays=rp, safety_pays=sp, risks_found=pct(calls["right_risk"], rp),
                right_safety=pct(calls["right_safety"], sp),
                error_rate=SCALE * sum(losses) / len(losses) if losses else None,
                answer_rate=100 * len(losses) / POSITIONS, in_flight_max=max(in_flight, default=0))


def test_metrics(key, name):
    return metrics_from(test_answers(key, name), {p["id"]: p for p in test_set()["positions"]})


def test_complete(m):
    return bool(m) and m["answered"] == POSITIONS and m["failed"] == 0


def match_of(key, name):
    if not db_path(key).exists():
        return None
    db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
    try:
        row = db.execute("SELECT id, status FROM matches WHERE model1 = ? ORDER BY id DESC LIMIT 1",
                         (name,)).fetchone()
    except sqlite3.OperationalError:
        row = None
    db.close()
    return row


def archive_attempt(key, step, reason):
    """A series cut off part-way is played again from game 1 with the same dice; the failed attempt's files move
    to attempt-N/ (its lessons are not used; its spend stays in its ledger)."""
    d = step_dir(key, step)
    n = attempt_of(key, step)
    old = d / f"attempt-{n}"
    old.mkdir(parents=True)
    for f in list(d.iterdir()):
        if not f.name.startswith("attempt-"):
            f.rename(old / f.name)
    log(key, "series_restarted", step=step, attempt_archive=old.name, reason=reason[-300:] if reason else None)


def new_ledger(key, step, gate):
    if gate is None:
        return None
    d = mdir(key) / "ledgers"
    d.mkdir(parents=True, exist_ok=True)
    n = 1 + len(ledgers(key, step))
    return dict(path=d / f"{step}-a{n}.db", cap=gate["cap"], binding=gate["binding"])


def run_empty(key, step, gate):
    d = step_dir(key, step)
    ledger = new_ledger(key, step, gate)
    if ledger:
        write_atomic(d / "ledger.json", json.dumps(dict(ledger, path=str(ledger["path"]), gate=gate), indent=1))
    m = run_test(key, step, test_name(key, step), "", d, ledger=ledger)
    if not test_complete(m):
        raise RuntimeError(f"{step}: {m['answered']} answered, {m['failed']} failed; run again to re-ask")
    write_atomic(d / "aggregate.json", json.dumps(dict(step=step, finished_at=now(), test=m), indent=1))


def run_series(key, step, gate):
    s = series_of(step)
    d = step_dir(key, step)
    d.mkdir(parents=True, exist_ok=True)
    attempt = attempt_of(key, step)
    name = game_name(key, s, attempt)
    prior = match_of(key, name)
    if prior is not None and not (d / "match.done").exists():
        archive_attempt(key, step, (d / "failed").read_text() if (d / "failed").exists() else f"match {prior}")
        d.mkdir(parents=True, exist_ok=True)
        attempt = attempt_of(key, step)
        name = game_name(key, s, attempt)
    ledger = new_ledger(key, step, gate)
    if ledger:
        write_atomic(d / "ledger.json", json.dumps(dict(ledger, path=str(ledger["path"]), gate=gate), indent=1))
    player = player_config(key, name, 1, note_file=d / "note.txt", ledger=ledger, base_url=base_url_of(key))
    if not (d / "match.done").exists():
        log(key, "series_start", step=step, attempt=attempt, seed=series_seed(s),
            lesson_prompt_sha256=lesson_prompt_sha256())
        (d / "note.txt").write_text("")
        write_atomic(d / "player.json", json.dumps(player, indent=1))
        hook = f"{sys.executable} {Path(__file__).resolve()} after-game --model {key} --series {s}"
        r = subprocess.run([str(BIN), "--model1-config", str(d / "player.json"), "--model2", "gnubg-weak",
                            "--seed", str(series_seed(s)), "--order-seed", str(ORDER_SEED), "--rounds",
                            str(GAMES // 2), "--fixed-rounds", "--clock", "0", "--max-turns",
                            str(TEST_CONTEXT["max_turns"]), "--prompt-version", PROMPT_VERSION, "--quiet", "--db",
                            str(db_path(key)), "--after-game", hook], cwd=CODE, capture_output=True, text=True,
                           env=dict(os.environ))
        (d / "match.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            (d / "failed").write_text(r.stderr[-2000:])
            log(key, "series_failed", step=step, attempt=attempt, stderr=r.stderr[-1000:])
            if "ROUTE CHECK" in r.stderr:
                raise Stop(f"{step}: {r.stderr[-600:]}")
            if "QUOTA:" in r.stderr:
                raise Pause(f"{step}: usage limit (429) on the subscription: {r.stderr[-600:]}")
            if "BUDGET CAP" in r.stderr:
                raise BudgetRefused(r.stderr[-500:])
            raise RuntimeError(f"{key} {step}: match failed: {r.stderr[-800:]}")
        write_atomic(d / "match.done", str(match_of(key, name)[0]))
    # T10: asked in the hook after game 10; failed positions are asked again here with the stored context.
    context = (d / "contexts" / "after-g10.txt").read_text() if (d / "contexts" / "after-g10.txt").exists() else ""
    m = run_test(key, step, test_name(key, step, attempt), context, d, ledger=ledger)
    # The test's wall time: the hook's first asking plus any re-asking here.
    m["wall_seconds"] = round(m["wall_seconds"] + sum(e.get("wall_seconds", 0) for e in events(key) if e["event"] ==
                                                      "t10_asked" and e["step"] == step and e.get("attempt") == attempt), 1)
    if not test_complete(m):
        raise RuntimeError(f"{step} T10: {m['answered']} answered, {m['failed']} failed; run again to re-ask")
    write_aggregate(key, step, attempt, m)


def after_game(key, s):
    """The runner's after-game hook: score the game, one lesson call, the next game's note; T10 after game 10."""
    step = f"S{s}"
    d = step_dir(key, step)
    attempt = attempt_of(key, step)
    match_id = int(os.environ["MATCH_ID"])
    g = 2 * (int(os.environ["GAME_ROUND"]) - 1) + int(os.environ["GAME_LEG"])
    if DRY and os.environ.get("IMPROVE_DRY_FAIL_AFTER_GAME") == str(g):
        raise SystemExit(f"dry-run fault injection after game {g}")  # exercises the restart rule offline
    score_match(key, match_id)
    exclude = test_board_keys()
    decs = game_decisions(key, match_id, g)
    excluded = sum(1 for x in decs if x["scored"] and x["game"] == g and x["board_key"] in exclude)
    if excluded:
        log(key, "test_positions_excluded", step=step, game=g, n=excluded)
    results = game_results(key, match_id)
    ok = [x for x in eligible(decs, exclude) if x["game"] == g]
    record = "\n".join([game_header(g, results)] + [record_line(x) for x in ok])
    text, info = write_lessons(key, step, g, record)
    blocks = [(k, (d / f"lessons-g{k:02d}.txt").read_text().strip()) for k in range(1, g + 1)]
    note = lessons_context(blocks)
    write_atomic(d / "note.txt", note)
    (d / "contexts").mkdir(exist_ok=True)
    (d / "contexts" / f"after-g{g:02d}.txt").write_text(note)
    log(key, "context", step=step, after_game=g, chars=len(note), sha256=hashlib.sha256(note.encode()).hexdigest())
    if g == GAMES:
        # Asked once here; positions still unanswered (a failed request or a refused budget reservation) are asked
        # again by run_series with the stored context, so T10 never replays the series' games.
        ledger = json.loads((d / "ledger.json").read_text()) if (d / "ledger.json").exists() else None
        try:
            m = run_test(key, step, test_name(key, step, attempt), note, d, ledger=ledger, rounds=1)
            log(key, "t10_asked", step=step, attempt=attempt, answered=m["answered"], failed=m["failed"],
                wall_seconds=m["wall_seconds"])
        except Exception as e:  # noqa: BLE001
            log(key, "t10_deferred", step=step, error=str(e)[-500:])


def write_lessons(key, step, g, record):
    """One lesson call after game g, through the model's own route (`jevgammon lesson`), retried until it returns;
    a refused budget reservation stops at once."""
    d = step_dir(key, step)
    user = LESSONS_USER.read_text().format(game=g, record=record)
    system = LESSONS_SYSTEM.read_text().strip()
    (d / "lesson-system.txt").write_text(system)
    (d / f"lessons-g{g:02d}.user.txt").write_text(user)
    call = d / f"lessons-g{g:02d}.call.json"
    if DRY:
        raw = "\n".join(f"- (dry run) game {g} lesson {k}: " + " ".join(["placeholder"] * 24) for k in range(1, 7))
        out = dict(text=raw, dry=True, input_tokens=0, output_tokens=0, cost_usd=None, reported_cost_usd=None,
                   in_flight=1, wall_ms=0, exchanges=[])
        write_atomic(call, json.dumps(out, indent=1))
    else:
        ledger = json.loads((d / "ledger.json").read_text()) if (d / "ledger.json").exists() else None
        cfg = player_config(key, game_name(key, series_of(step), attempt_of(key, step)), 1, ledger=ledger,
                            base_url=base_url_of(key))
        (d / "lesson-player.json").write_text(json.dumps(cfg, indent=1))
        for k in range(20):
            r = subprocess.run([str(BIN), "lesson", "--player", str(d / "lesson-player.json"), "--system",
                                str(d / "lesson-system.txt"), "--user", str(d / f"lessons-g{g:02d}.user.txt"),
                                "--out", str(call)], cwd=CODE, capture_output=True, text=True)
            if r.returncode == 0:
                break
            log(key, "lesson_call_failed", step=step, game=g, attempt=k + 1, stderr=r.stderr[-500:])
            if "ROUTE CHECK" in r.stderr:
                raise SystemExit(f"ROUTE CHECK: lesson call rejected: {r.stderr[-600:]}")
            if "QUOTA:" in r.stderr:
                raise SystemExit(f"QUOTA: lesson call hit the usage limit: {r.stderr[-600:]}")
            if "BUDGET CAP" in r.stderr:
                raise SystemExit(f"BUDGET CAP: lesson call refused: {r.stderr[-300:]}")
            time.sleep(min(600, 30 * (k + 1)))
        else:
            raise SystemExit(f"lesson call after game {g} failed 20 times")
        out = json.loads(call.read_text())
    text, cut = limit_lessons((out.get("text") or "").strip())
    write_atomic(d / f"lessons-g{g:02d}.txt", text + "\n")
    log(key, "lesson_call", step=step, game=g, input_tokens=out.get("input_tokens"),
        output_tokens=out.get("output_tokens"), cost_usd=out.get("cost_usd"),
        reported_cost_usd=out.get("reported_cost_usd"), in_flight=out.get("in_flight"), wall_ms=out.get("wall_ms"),
        empty=not text, **cut)
    return text, cut


def write_aggregate(key, step, attempt, t10):
    d = step_dir(key, step)
    match_id = int((d / "match.done").read_text())
    decs = game_decisions(key, match_id)
    results = game_results(key, match_id)
    ev = [e for e in events(key) if e.get("step") == step]
    calls = [e for e in ev if e["event"] == "lesson_call"][-GAMES:]
    lessons = [dict(game=g, text=(d / f"lessons-g{g:02d}.txt").read_text().strip())
               for g in range(1, GAMES + 1) if (d / f"lessons-g{g:02d}.txt").exists()]
    agg = dict(step=step, series=series_of(step), attempt=attempt, seed=series_seed(series_of(step)),
               finished_at=now(), games=len(results), wins=sum(r["won"] for r in results.values()),
               game_decisions=len(decs), game_invalid=sum(x["invalid"] for x in decs),
               game_in_flight_max=max((x["in_flight"] or 0 for x in decs), default=0),
               lesson_calls=len(calls), lessons_cut=sum(bool(e.get("cut")) for e in calls),
               lessons_empty=sum(bool(e.get("empty")) for e in calls), restarts=attempt - 1, lessons=lessons,
               lesson_files={x["game"]: sha256_file(d / f"lessons-g{x['game']:02d}.txt") for x in lessons},
               test_positions_excluded=sum(e["n"] for e in ev if e["event"] == "test_positions_excluded"),
               t10=t10, lesson_prompt_sha256=lesson_prompt_sha256(), test_set_sha256=sha256_file(TEST_SET))
    write_atomic(d / "aggregate.json", json.dumps(agg, indent=1))


def step_done(key, step):
    return (step_dir(key, step) / "aggregate.json").exists()


def next_step(key):
    return next((s for s in STEPS if not step_done(key, s)), None)


# --- Route check (OpenRouter) ----------------------------------------------------------------------------------

def response_ids(key, step):
    """(model, provider) of every stored OpenRouter response of a step: games, tests and lesson calls."""
    out = []
    d = step_dir(key, step)
    names = [test_name(key, step)] if step.startswith("E") else []
    if step.startswith("S"):
        for a in range(1, attempt_of(key, step) + 1):
            names += [game_name(key, series_of(step), a), test_name(key, step, a)]
    if db_path(key).exists():
        db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
        q = ["SELECT x.response FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id WHERE a.setup = ?",
             "SELECT x.response FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games g ON g.id = t.game_id "
             "JOIN matches m ON m.id = g.match_id WHERE m.model1 = ? AND t.player = 1"]
        for name in names:
            for sql in q:
                try:
                    out += [r[0] for r in db.execute(sql, (name,))]
                except sqlite3.OperationalError:
                    pass
        db.close()
    for f in d.rglob("lessons-g*.call.json"):
        out += [x.get("response") for x in json.loads(f.read_text()).get("exchanges", [])]
    exp = MODELS[key].get("expect") or {}
    ids = []
    for raw in out:
        try:
            v = json.loads(raw)
        except (TypeError, ValueError):
            ids.append((None, None))  # unreadable identity fails the check
            continue
        ids.append((pointer(v, exp.get("model_pointer") or "/model"),
                    pointer(v, exp.get("provider_pointer") or "/provider") if exp.get("provider") else None))
    return ids


def pointer(value, path):
    for part in path.strip("/").split("/"):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def route_check(key, ids):
    """None, or why the responses do not name the pre-registered model and provider."""
    exp = MODELS[key].get("expect")
    if not exp:
        return None
    if not ids:
        return "route check: no response identity found for the step (fails closed)"
    bad = sorted({(m, p) for m, p in ids if m not in exp["models"] or p != exp.get("provider")}, key=str)
    if bad:
        return f"route check: responses named {bad[:5]}, expected model in {exp['models']} on {exp.get('provider')}"
    return None


# --- Run -------------------------------------------------------------------------------------------------------

def plan_identity(key):
    """The plan hash stored for a model before its first call (None before)."""
    f = mdir(key) / "plan.json"
    return json.loads(f.read_text())["plan_sha256"] if f.exists() else None


def bind_plan(key):
    """Before a model's first call, store the published plan's hash in its run directory and database; on every
    start and resume, the current plan file must still have that hash (else the run is refused)."""
    current = sha256_file(PLAN)
    stored = plan_identity(key)
    if stored is None:
        if current != PLAN_SHA256:
            raise SystemExit(f"{PLAN} ({current}) is not the published pre-registration {PLAN_SHA256}")
        write_atomic(mdir(key) / "plan.json", json.dumps(dict(plan_sha256=current, bound_at=now()), indent=1))
        db = sqlite3.connect(db_path(key), timeout=60)
        db.execute("CREATE TABLE IF NOT EXISTS improve_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT OR REPLACE INTO improve_identity VALUES ('plan_sha256', ?)", (current,))
        db.commit()
        db.close()
        log(key, "plan_bound", plan_sha256=current)
        return current
    if current != stored:
        raise SystemExit(f"{key}: the plan file now hashes {current}, but this model's run is bound to {stored}: "
                         f"resume refused")
    return stored


def binary_identity():
    """The runner binary of this step: path, sha256, and the commit it was built from (a lane's pinned copy is named
    jevgammon-<commit>; anything else is recorded as unpinned)."""
    name = BIN.name
    commit = name.split("-", 1)[1] if name.startswith("jevgammon-") else None
    return dict(path=str(BIN), sha256=sha256_file(BIN), commit=commit, pinned=commit is not None,
                mtime=datetime.fromtimestamp(BIN.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"))


def check_inputs():
    if sha256_file(PLAN) != PLAN_SHA256:
        raise SystemExit(f"{PLAN} differs from the pre-registration this harness is bound to ({PLAN_SHA256[:8]}…)")
    if lesson_prompt_sha256() != LESSON_PROMPT_SHA256:
        raise SystemExit("lesson prompt hash differs from the plan's")
    if sha256_file(TEST_SET) != TEST_SET_SHA256 or sha256_file(TEST_POSITIONS) != TEST_POSITIONS_SHA256:
        raise SystemExit("test set hash differs from the plan's")
    if not BIN.exists():
        raise SystemExit(f"build the runner first: {BIN}")
    if not DRY and not binary_identity()["pinned"]:
        raise SystemExit(f"{BIN}: real runs use a pinned binary copy named by commit (IMPROVE_BIN=.../jevgammon-<commit>)")


def run(key, until=None, balance_reader=openrouter_balance):
    """Runs the model's next steps in order; returns 0 (done or reached `until`), STOP or PAUSE."""
    m = MODELS[key]
    hold = mdir(key) / "hold.json"  # an operator hold (e.g. shared-balance priority): pause before the next step
    if hold.exists():
        why = json.loads(hold.read_text())["reason"]
        write_atomic(mdir(key) / "paused.json", json.dumps(dict(at=now(), reason=why), indent=1))
        log(key, "paused", reason=why)
        print(f"PAUSED {key}: {why}", file=sys.stderr)
        return PAUSE
    check_inputs()
    mdir(key).mkdir(parents=True, exist_ok=True)
    lock = open(mdir(key) / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f"{key}: another run holds the lock") from None
    if (mdir(key) / "stopped.json").exists():
        print(f"{key}: stopped: {json.loads((mdir(key) / 'stopped.json').read_text())['reason']}")
        lock.close()
        return STOP
    (mdir(key) / "paused.json").unlink(missing_ok=True)
    ensure_runner_db(key)
    bind_plan(key)
    if m["lane"] == "local" and not DRY:
        fit_check(key)
    billed_model = m.get("billed") and not DRY
    try:
        while (step := next_step(key)) is not None:
            rejected = mdir(key) / "route-rejections.jsonl"
            if rejected.exists() and rejected.stat().st_size:
                raise Stop(f"route check: {rejected.read_text().splitlines()[0][:600]}")
            gate = money_gate(key, step, balance_reader) if billed_model else None
            log(key, "step_start", step=step, gate=gate, binary=binary_identity())
            try:
                (run_empty if step.startswith("E") else run_series)(key, step, gate)
            except BudgetRefused as e:
                binding = (gate or {}).get("binding", "")
                if binding in ("balance", "share"):
                    raise Pause(f"{step}: the step ledger's balance limit refused a request: {e}") from None
                raise Stop(f"{step}: {binding} reached before a request: {e}") from None
            if m.get("expect") and not DRY:
                why = route_check(key, response_ids(key, step))
                if why:
                    raise Stop(f"{step}: {why}")
            log(key, "step_done", step=step, billed=billed(key, step))
            if billed_model and step_done(key, "E1") and step_done(key, "S1") and cost_check(key) is None:
                s1, e1 = billed(key, "S1"), billed(key, "E1")
                why = rule_a(key, s1, e1)
                write_atomic(mdir(key) / "cost_check.json", json.dumps(
                    dict(at=now(), S1=s1, E1=e1, projected=projected_full(s1, e1), estimate=m["estimate"],
                         limit=ESTIMATE_FACTOR * m["estimate"], fired=why), indent=1))
                if why:
                    raise Stop(why)
            summary()
            if step == until:
                return 0
        return 0
    except Stop as e:
        write_atomic(mdir(key) / "stopped.json", json.dumps(dict(at=now(), reason=str(e)), indent=1))
        log(key, "stopped", reason=str(e))
        print(f"STOPPED {key}: {e}", file=sys.stderr)
        return STOP
    except Pause as e:
        write_atomic(mdir(key) / "paused.json", json.dumps(dict(at=now(), reason=str(e)), indent=1))
        log(key, "paused", reason=str(e))
        print(f"PAUSED {key}: {e}", file=sys.stderr)
        return PAUSE
    finally:
        summary()
        lock.close()


# --- Summary (the page's data; plan §6, contract in tools/site/improve_validate.py) ----------------------------

CHATGPT_RESET = "waiting for the ChatGPT reset 2026-11-13 11:38 UTC"
TURN = "waiting for its turn in its lane"


def started(key):
    return any(e["event"] == "step_start" for e in events(key))


def model_state(key):
    """(state, reason): stopped / paused / complete / running from the run directory; a model whose first step has
    not started is paused: held (hold.json), Codex before the ChatGPT reset, or waiting for its turn in its lane."""
    if (mdir(key) / "stopped.json").exists():
        return "stopped", json.loads((mdir(key) / "stopped.json").read_text())["reason"]
    if (mdir(key) / "paused.json").exists():
        return "paused", json.loads((mdir(key) / "paused.json").read_text())["reason"]
    if all(step_done(key, s) for s in STEPS):
        return "complete", None
    if not started(key):
        if (mdir(key) / "hold.json").exists():
            return "paused", json.loads((mdir(key) / "hold.json").read_text())["reason"]
        if key in ("gpt-6.1-sol-high", "gpt-6-astra-high") and now() < "2026-11-13T11:38":
            return "paused", CHATGPT_RESET
        return "paused", TURN
    return "running", None


# The page's fixed status reasons (improve_validate, Ümit #3219).
PROGRESS_REASONS = ("shared-balance priority", "waiting for the ChatGPT reset 13 Nov", "waiting for its turn",
                    "usage limit")


def progress_reason(reason):
    """The page's fixed reason for a paused model's free-text reason."""
    if reason == CHATGPT_RESET:
        return "waiting for the ChatGPT reset 13 Nov"
    if reason == TURN:
        return "waiting for its turn"
    if "usage limit (429)" in reason:  # the harness's Claude/subscription QUOTA pause
        return "usage limit"
    if "shared-balance" in reason or "balance" in reason or "share limit" in reason:
        return "shared-balance priority"
    raise ValueError(f"no page reason for a pause: {reason!r}")  # e.g. a Claude usage limit: needs a page text


def progress(key, state, reason):
    status = {"complete": "done", "stopped": "stopped", "paused": "paused", "running": "running"}[state]
    ev = events(key)
    return dict(status=status, reason=progress_reason(reason) if status == "paused" else None,
                series_done=sum(step_done(key, f"S{s}") for s in range(1, SERIES + 1)),
                updated_at=ev[-1]["at"] if ev else not_started_since(key))


PHASE2_START = "2026-11-08T16:10:46+00:00"  # the first lane's start (plan §10: the first model call came after it)


def not_started_since(key):
    """A stable time for a model with no event yet (so the exporter's file only changes when a model does): its
    hold's time, else Phase 2's start."""
    hold = mdir(key) / "hold.json"
    if hold.exists():
        at = json.loads(hold.read_text()).get("at")
        if at:
            return datetime.fromisoformat(at.replace("Z", "+00:00")).isoformat(timespec="seconds")
    return PHASE2_START


def api_equivalent(key):
    total = 0.0
    if db_path(key).exists():
        db = sqlite3.connect(f"file:{db_path(key)}?mode=ro", uri=True, timeout=60)
        for sql in ("SELECT COALESCE(SUM(cost_usd), 0) FROM turns WHERE player = 1",
                    "SELECT COALESCE(SUM(cost_usd), 0) FROM answers"):
            try:
                total += db.execute(sql).fetchone()[0]
            except sqlite3.OperationalError:
                pass
        db.close()
    for f in mdir(key).rglob("lessons-g*.call.json"):
        total += json.loads(f.read_text()).get("cost_usd") or 0.0
    return round(total, 4)


def model_summary(key):
    m = MODELS[key]
    state, reason = model_state(key)
    empty = []
    for step in ("E1", "E2", "E3"):
        f = step_dir(key, step) / "aggregate.json"
        if f.exists():
            t = json.loads(f.read_text())["test"]
            empty.append({k: t[k] for k in TEST_KEYS})
    series = []
    for s in range(1, SERIES + 1):
        f = step_dir(key, f"S{s}") / "aggregate.json"
        if not f.exists():
            continue
        a = json.loads(f.read_text())
        series.append(dict(series=s, finished=True, games=a["games"], wins=a["wins"],
                           game_decisions=a["game_decisions"], game_invalid=a["game_invalid"],
                           lesson_calls=a["lesson_calls"], lessons_cut=a["lessons_cut"],
                           lessons_empty=a["lessons_empty"], restarts=a["restarts"], lessons=a["lessons"],
                           t10={k: a["t10"][k] for k in TEST_KEYS}))
    settings = {} if DRY else league_settings(m["setup"])
    route = settings.get("provider") or m["lane"]
    return dict(key=key, setup=m["setup"], route=route, billed=bool(m.get("billed")), state=state, reason=reason,
                progress=progress(key, state, reason),
                steps_done=[s for s in STEPS if step_done(key, s)], empty=empty, series=series,
                cost=dict(billed_usd=round(billed(key), 4) if m.get("billed") else 0.0,
                          reported_usd=round(reported(key), 4) if m.get("billed") else None,
                          api_equivalent_usd=api_equivalent(key), estimate_usd=m.get("estimate")))


TEST_KEYS = ("answered", "expected", "valid", "invalid", "failed", "risk_pays", "safety_pays", "risks_found",
             "right_safety", "error_rate", "answer_rate", "in_flight_max", "wall_seconds")


def bound_plan(keys):
    """The plan identity the results are bound to: the hash stored per model before its first call (never the
    current file's); the harness's own bound hash while no model has started."""
    stored = {plan_identity(k) for k in keys} - {None}
    if len(stored) > 1:
        raise SystemExit(f"models are bound to different plans: {sorted(stored)}")
    return stored.pop() if stored else PLAN_SHA256


def summary(only_if_changed=False):
    """The page's file: every plan model, with its progress. `only_if_changed`: leave the file alone when nothing but
    `updated_at` would change (the exporter's path trigger fires on its own write)."""
    keys = list(MODELS) if not DRY else [k for k in MODELS if mdir(k).exists()]
    previous = {}
    if (OUT / "improve.json").exists():
        try:
            previous = {m["key"]: m for m in json.loads((OUT / "improve.json").read_text()).get("models", [])}
        except (ValueError, KeyError, TypeError, AttributeError):
            previous = {}
    models = []
    for k in keys:
        try:
            models.append(model_summary(k))
        except ValueError as e:
            # A pause the page has no text for: never invent one. Keep the model's last exported entry (or leave it
            # out), log the error, and write everything else.
            print(f"improve export: {k}: {e}; keeping its previous entry", file=sys.stderr)
            with open(RUNS / "export-errors.log", "a") as f:
                f.write(json.dumps(dict(at=now(), model=k, error=str(e))) + "\n")
            if k in previous:
                models.append(previous[k])
    out = dict(updated_at=now(),
               protocol=dict(plan_sha256=bound_plan(keys), lesson_prompt_sha256=lesson_prompt_sha256(),
                             test_set_sha256=sha256_file(TEST_SET), series_per_model=SERIES,
                             games_per_series=GAMES, empty_runs=EMPTY_RUNS, test_positions=POSITIONS, steps=STEPS,
                             floor_points=FLOOR_POINTS, safety_drop_points=SAFETY_DROP, dry_run=DRY),
               money=dict(total_cap_usd=TOTAL_CAP_USD, billed_total_usd=round(billed_total(), 4)),
               models=models)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prompt").mkdir(exist_ok=True)
    shutil.copyfile(LESSONS_SYSTEM, OUT / "prompt/lessons_system.txt")
    shutil.copyfile(LESSONS_USER, OUT / "prompt/lessons_user.txt")
    if only_if_changed and (OUT / "improve.json").exists():
        try:
            old = json.loads((OUT / "improve.json").read_text())
        except ValueError:
            old = None
        if old is not None and {**old, "updated_at": None} == {**out, "updated_at": None}:
            return out
    write_atomic(OUT / "improve.json", json.dumps(out, indent=1))
    return out


def receipts():
    """Per model, from the private files: first call (time, served identity, tokens, cost), cost check, pauses and
    stops, binaries per step. For reports; no outcome numbers."""
    for k in MODELS:
        ev = events(k)
        if not ev and not (mdir(k) / "hold.json").exists():
            continue
        st, why = model_state(k)
        print(f"== {MODELS[k]['setup']} [{k}]: {st}{' (' + why + ')' if why else ''}; "
              f"steps done {[x for x in STEPS if step_done(k, x)]}")
        first = None
        if db_path(k).exists():
            db = sqlite3.connect(f"file:{db_path(k)}?mode=ro", uri=True, timeout=60)
            try:
                first = db.execute("SELECT a.created_at, a.cost_usd, x.response FROM answers a JOIN answer_exchanges x "
                                   "ON x.answer_id = a.id ORDER BY x.id LIMIT 1").fetchone()
            except sqlite3.OperationalError:
                first = None
            db.close()
        if first:
            exp = MODELS[k].get("expect") or {}
            try:
                v = json.loads(first[2])
                ident = dict(model=pointer(v, exp.get("model_pointer") or "/model"),
                             provider=pointer(v, exp.get("provider_pointer") or "/provider"))
            except (TypeError, ValueError):
                ident = "not JSON"
            print(f"   first call {first[0]}: identity {ident}, cost ${first[1] or 0:.6f}")
        cc = cost_check(k)
        if cc:
            print(f"   cost check {cc['at']}: S1 ${cc['S1']:.4f}, E1 ${cc['E1']:.4f}, projected ${cc['projected']:.2f} "
                  f"vs limit ${cc['limit']:.2f}: {'FIRED ' + cc['fired'] if cc['fired'] else 'continue'}")
        for e in ev:
            if e["event"] in ("paused", "stopped", "series_restarted", "fit_check"):
                print(f"   {e['at']} {e['event']}: {e.get('reason') or e.get('sequences') or ''}")
            if e["event"] == "step_start" and e.get("binary"):
                b = e["binary"]
                print(f"   {e['at']} {e['step']} binary {b.get('commit')} {str(b.get('sha256'))[:16]}")
        print(f"   billed ${billed(k):.4f}, API-equivalent ${api_equivalent(k):.4f}")


def status(key=None):
    for k in [key] if key else MODELS:
        if not mdir(k).exists():
            continue
        st, why = model_state(k)
        print(f"{k}: {st}{' (' + why + ')' if why else ''}; done {[s for s in STEPS if step_done(k, s)]}; "
              f"next {next_step(k)}; billed ${billed(k):.4f}")
    print(f"billed total ${billed_total():.4f} of ${TOTAL_CAP_USD:.0f}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True, choices=sorted(MODELS))
    r.add_argument("--until", choices=STEPS)
    r.add_argument("--base-url", help="local servers: the experiment's server (recorded)")
    h = sub.add_parser("after-game")
    h.add_argument("--model", required=True)
    h.add_argument("--series", type=int, required=True)
    sc = sub.add_parser("share-cap", help="set this experiment's share of the balance (a pause limit; Main)")
    sc.add_argument("--usd", type=float, required=True)
    sc.add_argument("--note", required=True)
    st = sub.add_parser("status")
    st.add_argument("--model")
    sub.add_parser("summary")
    sub.add_parser("receipts", help="first calls, cost checks, pauses and stops per model")
    sub.add_parser("export", help="write improve.json from the run directories (for a timer or path trigger)")
    a = ap.parse_args()
    if a.cmd == "after-game":
        after_game(a.model, a.series)
    elif a.cmd == "status":
        status(a.model)
    elif a.cmd == "summary":
        summary()
    elif a.cmd == "receipts":
        receipts()
    elif a.cmd == "export":
        summary(only_if_changed=True)
    elif a.cmd == "share-cap":
        write_atomic(RUNS / "share_cap.json", json.dumps(dict(usd=a.usd, note=a.note, at=now()), indent=1))
        with open(RUNS / "share_cap.log", "a") as f:
            f.write(json.dumps(dict(usd=a.usd, note=a.note, at=now())) + "\n")
    else:
        if a.base_url:
            write_atomic(mdir(a.model) / "base_url.txt", a.base_url)
            log(a.model, "base_url", url=a.base_url)
        sys.exit(run(a.model, a.until))


if __name__ == "__main__":
    main()
