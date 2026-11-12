"""Did they improve? Part 3: decision models (pre-registration: the live plan, mailbox/Did they improve - plan
2026-11-08.md, and its addendum, mailbox/Did they improve - decision models - addendum 2026-11-09.md).

Per decision model of the cohort (decision_cohort.json: the top 8 of the live leaderboard), two arms, each judged on
its own under the live plan's rule, each with its own games, run directory and (D1, proposed default) its own 3 empty
runs, on the chat models' schedule (E1, S1, cost check, S2, E2, S3, S4, E3, S5):

- notes ("helper-written notes"): after each game a fixed writer (Qwen3.8 Flash (off) via OpenRouter, the live plan's
  lesson call unchanged, pinned for the whole cohort) reads the model's graded game record (test positions removed
  first) with the pilot's lesson prompt; the pilot's cut rule keeps at most 5 lessons and 150 words; the block (intro
  "Notes a helper wrote from your earlier games in this series, oldest first:") goes at the start of `state`.
- worst ("worst mistakes"): after each game a script puts the 5 costliest decisions of this series so far (GNUbg 2-ply,
  test positions removed before selection) at the start of `state` as solved examples.

Blocks reset every series and are never shortened; every request passes the runner's context gate, and a gate
failure or the service's own refusal stops the arm as incomplete.

    python3 workspace/improve/decision.py status
    python3 workspace/improve/decision.py preflight-guard            # no call: the conservative guard on league requests
    python3 workspace/improve/decision.py preflight-render --setup glide-v1.2-local  # no call, no GPU: Lr (§6.1)
    python3 workspace/improve/decision.py run --arm decision/jev-1.14.0-notes [--until S1]
    IMPROVE_DRY=1 python3 workspace/improve/decision.py run --arm decision/fastino-glide-worst --until S1  # no call
    python3 workspace/improve/decision.py probe-p1 --setup jev-1.14.0 --send   # billed (< $0.001); never run by tests

Private outputs as in improve.py, under the arm key: smoke/improve/decision/<arm>.db, workspace/improve/runs/
decision/<arm>/ (notes: the writer's raw reply, kept notes, delivered blocks by hash; worst: the selected turn ids and
board keys per game), workspace/improve/runs/decision/preflight/ (guard, P1, render checks), and
workspace/improve/out/improve-decision.json (aggregates only).

Money: the live plan's rules (the $110 total with every decision-model ledger counted, the $5 OpenRouter reserve,
rule a at 1.5 x the arm's estimate) plus the hosted allowance per provider (D6, open: $0 refuses every billed hosted
call) and the provider subcaps (Nace $1.25, counted with the league's own Nace ledger). Every request, writer call and
probe reserves its worst case in the step's ledger before it is sent.
"""

import argparse
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import improve as I  # noqa: E402

COHORT_FILE = HERE / "decision_cohort.json"
ADDENDUM = I.STATE_ROOT / "mailbox/Did they improve - decision models - addendum 2026-11-09.md"
ADDENDUM_SHA256 = "b370f4dc9660a618aece4586b8c8f5259688372fab580305b4454aaa2d71a967"  # main 02d6145
ARMS = {"notes": "helper-written notes", "worst": "worst mistakes"}
NOTES_INTRO = "Notes a helper wrote from your earlier games in this series, oldest first:"
WORST_OPEN = "=== WORST MISTAKES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
WORST_INTRO = "Your costliest decisions so far in this series, by GNU Backgammon's 2-ply equity loss, largest first:"
WORST_CLOSE = "=== END OF WORST MISTAKES ==="
WORST_N = 5
POSITION_HEAD = "Position (your numbering; you move 24 -> 1):"
GNUBG = "GNU Backgammon 1.08, 2-ply (score_games.py)"
WRITER_KEY = "qwen3.8-flash-off"  # the live plan's Qwen3.8 Flash (off) lesson call, unchanged
WRITER_SUFFIX = " | writer"
WRITER_CALL_RESERVE = 0.018  # worst case per writer call: input bytes + 32,768 output tokens at $0.47/M
# Requests per arm (draft §7): 5 series of (about 210 game requests + a 200-position T10) and 3 empty runs of 200.
SERIES_SHARE, EMPTY_SHARE = 410 / 2650, 200 / 2650
# The synthetic maximum blocks of the guard preflight (addendum): Arm N 10 games x 5 lessons x 30 words of 12 bytes
# (the pilot's cut rule bounds lessons and words, not bytes; the longest chat notes measured 9,535 bytes / 1,460
# words, 6.5 bytes a word); Arm W 5 examples with the largest rendered League position blocks and longest plays.
MAX_WORD = "x" * 12
PREFLIGHT = lambda: I.RUNS / "decision" / "preflight"  # noqa: E731
DECISION_OUT = lambda: I.OUT / "improve-decision.json"  # noqa: E731
# The bounded envelope (Zeki #3788): the billed chat models run only through one serial systemd unit, from pinned code.
CHAT_CODE = Path("/home/cbasaran/code/jevgammon-improve/workspace/improve")
CHAT_IMPROVE_SHA256 = "90fe6b0ead90ff4d3d32ec80e5932a8c113456b05ee76e6bb9c5e39a56df9875"  # improve.py @ 1a27793 (Zeki #3798: export-only delta from 56a93b4/0e6314d, patch sha256 e0b3ee66…)
CHAT_QUEUE_SHA256 = "e53fa11b4d31dd289e3a62ce74d66dfe227aeb3e58240e19b4d8565c85f13a74"  # run_queue.sh (for-loop, serial)
BILLED_CHAT = ("qwen3.8-flash-off", "glm-5.3-on", "kimi-k3.1-pro-off", "deepseek-v4.1-flash-on")  # MODELS billed=True
CHAT_UNIT = "improve-openrouter.service"


def billed_chat_fence(proc="/proc", sha=None):
    """Fail-closed check of the chat side, inside the admission lock: the pinned chat code and its serial queue are
    unchanged, and at most one `improve.py run --model <billed chat model>` process exists, inside the
    improve-openrouter unit's cgroup. Anything unreadable or ambiguous refuses. Returns the workers seen."""
    sha = sha or I.sha256_file
    for path, want in ((CHAT_CODE / "improve.py", CHAT_IMPROVE_SHA256), (CHAT_CODE / "run_queue.sh", CHAT_QUEUE_SHA256)):
        if sha(path) != want:
            raise Refused(f"chat fence: {path} no longer has the reviewed sha256 {want[:12]}…", pause=True)
    workers = []
    try:
        entries = [d for d in Path(proc).iterdir() if d.name.isdigit()]
    except OSError as e:
        raise AccountingError(f"chat fence: {proc} unreadable: {e}") from None
    for d in entries:
        try:
            args = [a.decode(errors="replace") for a in (d / "cmdline").read_bytes().split(b"\0") if a]
            if not any(a.endswith("improve.py") for a in args) or "run" not in args:
                continue
            cgroup = (d / "cgroup").read_text()
        except FileNotFoundError:
            continue  # exited between the listing and the read
        except OSError as e:
            raise AccountingError(f"chat fence: /proc/{d.name} unreadable: {e}") from None
        models = [args[i + 1] for i, a in enumerate(args[:-1]) if a == "--model"] + \
            [a.split("=", 1)[1] for a in args if a.startswith("--model=")]
        if len(models) != 1:
            raise AccountingError(f"chat fence: ambiguous improve.py run process {d.name}: {args}")
        if models[0] in BILLED_CHAT:
            workers.append(dict(pid=int(d.name), model=models[0], cgroup=cgroup.strip()))
    if len(workers) > 1:
        raise Refused(f"chat fence: {len(workers)} billed chat workers at once: {workers}", pause=True)
    for w in workers:
        if not any(line.endswith("/" + CHAT_UNIT) for line in w["cgroup"].splitlines()):
            raise Refused(f"chat fence: billed chat worker {w['pid']} ({w['model']}) outside {CHAT_UNIT}", pause=True)
    return workers


FENCE = billed_chat_fence


# --- Cohort ----------------------------------------------------------------------------------------------------

def cohort():
    return json.loads(COHORT_FILE.read_text())


def decided(name):
    return cohort()["decisions"][name]["value"]


def setups():
    return {s["slug"]: s for s in cohort()["setups"]}


def arm_key(slug, arm):
    return f"decision/{slug}-{arm}"


def split(key):
    slug, arm = key.split("/", 1)[1].rsplit("-", 1)
    return slug, arm


def register():
    """Every testable arm of the cohort into improve.ENTRIES, for the shared helpers (names, estimates, route check)."""
    for s in cohort()["setups"]:
        if "estimate" not in s:
            continue
        for arm, label in ARMS.items():
            est = s["estimate"][arm]
            I.ENTRIES[arm_key(s["slug"], arm)] = dict(
                setup=s["setup"], label=f"{s['setup']} · {label}", lane=f"decision-{s['lane']}", slug=s["slug"],
                arm=arm, hosted=s["lane"] == "hosted", provider=s.get("provider"), gate=s["gate"],
                price=s.get("price"), estimate=est, S=est * SERIES_SHARE, E=est * EMPTY_SHARE,
                expect=dict(models=s["expect"]))


register()


def arm_keys():
    return sorted(I.ENTRIES)


def guard_record():
    f = PREFLIGHT() / "guard.json"
    return json.loads(f.read_text()) if f.exists() else None


def evidence_record(kind, slug):
    f = PREFLIGHT() / f"{kind}-{slug}.json"
    return json.loads(f.read_text()) if f.exists() else None


def arm_state(slug, arm, dry=None):
    """(state, reason) of an arm before it runs: eligible, 'not tested' (shown with its reason) or 'pending' (a
    human decision or a preflight is missing). Dry runs skip only the billing and evidence preconditions."""
    dry = I.DRY if dry is None else dry
    s = setups()[slug]
    if s.get("not_tested"):
        return "not tested", s["not_tested"]
    if s.get("not_started"):
        return "not started", s["not_started"]
    if (s.get("arm_not_tested") or {}).get(arm):
        return "not tested", s["arm_not_tested"][arm]
    need = s.get("needs")
    if need == "D5_edge_settings" and arm in s.get("needs_arms", ARMS):
        v = decided(need)
        if v == "pending":
            return "pending", "D5 (edge settings): Ümit's decision"
        if v == "not_tested":
            return "not tested", "edge settings (D5)"
    if (s.get("arm_pending") or {}).get(arm):
        return "pending", s["arm_pending"][arm]
    if s["gate"]["kind"] == "client":
        if s["gate"].get("limit_tokens") is None:
            return "not tested", "native context limit unverified"  # no documented limit: the guard fails closed
        g = guard_record()
        row = (g or {}).get("setups", {}).get(slug)
        if row is None:
            return "pending", "conservative context guard preflight not run"
        if row["refused"]["none"] or row["refused"][arm]:
            return "not tested", "conservative context guard"
    if dry:
        return "eligible", None
    if s["lane"] == "hosted":
        if not (decided("D6_hosted_allowance_usd").get(s["provider"]) or 0) > 0:
            return "pending", "D6 open: hosted spending outside OpenRouter not authorised"
        subcap = cohort().get("provider_subcaps_usd", {}).get(s["provider"])
        if subcap is not None and subcap - provider_spent(s["provider"]) < s["estimate"][arm]:
            left = subcap - provider_spent(s["provider"])
            return "pending", (f"{s['provider']} subcap: ${left:.2f} left of ${subcap:.2f} (its ledgers), below this "
                               f"arm's ${s['estimate'][arm]:.2f} estimate; needs a subcap decision")
        p1 = evidence_record("p1", slug)
        if not (p1 and p1.get("passed")):
            return "pending", "accounting probe P1 not passed"
        if p1.get("identity_sha256") != digest(run_identity(slug)):
            return "pending", "accounting probe P1 was run under other settings (or records none): run it again"
    else:
        lr = evidence_record("render", slug)
        if not (lr or {}).get("arms", {}).get(arm):
            return "pending", "local render check (Lr) not passed"
    return "eligible", None


# --- Plan binding ----------------------------------------------------------------------------------------------

def check_addendum():
    current = I.sha256_file(ADDENDUM)
    if current != ADDENDUM_SHA256:
        raise SystemExit(f"{ADDENDUM} ({current}) is not the published addendum {ADDENDUM_SHA256}")


# The settings that define an arm's run: bound before its first call and never changed after (a change refuses the
# resume). Money terms may change only through an explicit amendment record in the cohort file (`amendments`:
# {path, from, to, source, at}), applied in order.
RUN_DEFINING = ("setup", "lane", "provider", "evidence", "gate", "expect", "price", "estimate", "needs", "needs_arms")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run_identity(slug):
    """The run-defining settings of a setup as they take effect: its cohort row, the league settings actually loaded
    from v3.db for it, any base URL override of its arms, D1, the writer and the bound texts."""
    s = setups()[slug]
    return dict(setup={k: s.get(k) for k in RUN_DEFINING}, league=I.league_settings(s["setup"]),
                base_urls={arm: I.base_url_of(arm_key(slug, arm)) for arm in ARMS},
                D1_empty_runs=decided("D1_empty_runs"), writer=WRITER_KEY, writer_expect=writer_expect(),
                lesson_prompt_sha256=I.LESSON_PROMPT_SHA256, addendum_sha256=ADDENDUM_SHA256)


def money_terms(slug):
    c, p = cohort(), setups()[slug].get("provider")
    return {"decision_lane_cap_usd": c["decision_lane_cap_usd"],
            f"provider_subcaps_usd.{p}": c.get("provider_subcaps_usd", {}).get(p),
            f"D6_hosted_allowance_usd.{p}": decided("D6_hosted_allowance_usd").get(p)}


def amended(path, old, new):
    """Whether the cohort file's amendment records lead `path` from `old` to `new`, in order."""
    value = old
    for a in cohort().get("amendments", []):
        if a.get("path") == path and a.get("from") == value and a.get("source"):
            value = a.get("to")
    return value == new


def bind_run(key):
    """Before an arm's first call, store the addendum hash, the run-defining settings and the money terms; on every
    start and resume the addendum and settings must be unchanged, and a changed money term needs its amendments."""
    slug, _ = split(key)
    f = I.mdir(key) / "run.json"
    current = I.sha256_file(ADDENDUM)
    identity, money = run_identity(slug), money_terms(slug)
    if not f.exists():
        if current != ADDENDUM_SHA256:
            raise SystemExit(f"{ADDENDUM} ({current}) is not the published addendum {ADDENDUM_SHA256}")
        stored = dict(addendum_sha256=current, identity=identity, identity_sha256=digest(identity), money=money,
                      bound_at=I.now())
        I.write_atomic(f, json.dumps(stored, indent=1))
        I.log(key, "run_bound", addendum_sha256=current, identity_sha256=stored["identity_sha256"], money=money)
        return stored
    stored = json.loads(f.read_text())
    if current != stored["addendum_sha256"]:
        raise SystemExit(f"{key}: the addendum now hashes {current}, but this arm is bound to "
                         f"{stored['addendum_sha256']}: refused")
    if digest(identity) != stored["identity_sha256"]:
        changed = sorted(k for k in identity if identity[k] != stored["identity"].get(k))
        raise SystemExit(f"{key}: run-defining settings changed since the arm was bound ({changed}): refused")
    for path, value in money.items():
        if value != stored["money"].get(path) and not amended(path, stored["money"].get(path), value):
            raise SystemExit(f"{key}: {path} changed from {stored['money'].get(path)} to {value} without an "
                             "amendment record: refused")
    return stored


def bound_run(key):
    f = I.mdir(key) / "run.json"
    return json.loads(f.read_text()) if f.exists() else None


# --- Player and writer configs ---------------------------------------------------------------------------------

def player_config(key, name, parallel, note_file=None, ledger=None):
    """The leaderboard setup's settings (v3.db), unchanged except name, parallel (never above the league's),
    prompt_note_file, budget (this experiment's step ledger, never the league's), expect_route and context_gate."""
    m = I.entry(key)
    if I.DRY:
        p = dict(name=name, spec="safest", note="dry run: the safest program in the decision model's seat")
    else:
        p = I.league_settings(m["setup"])
    league_parallel = p.get("parallel")
    p.update(name=name, parallel=min(parallel, league_parallel) if league_parallel else parallel)
    p.pop("max_matches", None)
    p.pop("budget", None)
    if note_file is not None:
        p["prompt_note_file"] = str(note_file)
    if base := I.base_url_of(key):
        p["base_url"] = base
    if I.DRY:
        return p
    if ledger is not None:
        cin, ccached, cout = m["price"] or (0.0, 0.0, 0.0)
        p["budget"] = dict(ledger=str(ledger["path"]), cap_usd=round(ledger["cap"], 6), input_per_mtok=cin,
                           cached_input_per_mtok=ccached, output_per_mtok=cout)
    p["expect_route"] = dict(models=m["expect"]["models"], reject_log=str(I.mdir(key) / "route-rejections.jsonl"))
    p["context_gate"] = m["gate"]
    return p


def writer_config(key, name, ledger):
    """The writer: the live plan's Qwen3.8 Flash (off) lesson-call config (improve.player_config, unchanged) in this
    arm's step ledger, with its own route check and rejection log."""
    cfg = I.player_config(WRITER_KEY, name + WRITER_SUFFIX, 1, ledger=ledger)
    cfg["expect_route"]["reject_log"] = str(I.mdir(key) / "writer-rejections.jsonl")
    return cfg


def writer_expect():
    return I.MODELS[WRITER_KEY]["expect"]


# --- Money -----------------------------------------------------------------------------------------------------

class AccountingError(Exception):
    """A ledger exists but cannot be read or holds invalid amounts: nothing is admitted (fails closed)."""


class Refused(Exception):
    """The admission refused a step or probe; `pause` when only a later balance or decision can lift it."""

    def __init__(self, reason, pause=False):
        super().__init__(reason)
        self.pause = pause


def ledger_read(path, writer=None):
    """One read of a ledger: (booked, unbilled). Booked = settled at cost, lost and open at their reservation;
    unbilled = the open and lost reservations (sent or not, possibly not yet charged: they stay liabilities against
    the live balance until reconciled). All rows or only the writer's / the player's. A file the runner never
    created holds nothing; an existing file that cannot be read, lacks its table or holds an invalid status or amount
    raises AccountingError."""
    import sqlite3
    path = Path(path)
    if not path.exists():
        return 0.0, 0.0
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
        try:
            rows = db.execute("SELECT status, reserved_usd, cost_usd, setup FROM attempts").fetchall()
        finally:
            db.close()
    except sqlite3.Error as e:
        raise AccountingError(f"ledger {path} unreadable: {e}") from None
    booked = unbilled = 0.0
    for status, reserved, cost, setup in rows:
        if writer is not None and str(setup or "").endswith(WRITER_SUFFIX) != writer:
            continue
        value = {"settled": cost, "lost": reserved, "open": reserved}.get(status, "bad")
        if not isinstance(value, (int, float)) or value != value or value < 0:
            raise AccountingError(f"ledger {path}: invalid row ({status!r}, {reserved!r}, {cost!r})")
        booked += value
        if status != "settled":
            unbilled += value
    return booked, unbilled


def booked_rows(path, writer=None):
    return ledger_read(path, writer)[0]


def arm_ledgers(key):
    d = I.mdir(key) / "ledgers"
    return sorted(d.glob("*.db")) if d.exists() else []


def arm_booked(key):
    return sum(booked_rows(p) for p in arm_ledgers(key))


def chat_booked():
    """Every chat-model ledger of the experiment (runs/<model>/ledgers), read strictly."""
    return sum(booked_rows(p) for p in sorted(I.RUNS.glob("*/ledgers/*.db")))


def chat_liabilities(reads=None):
    """The chat lanes' open steps: a chat step fixes its ledger cap at its start (improve.py run -> money_gate ->
    new_ledger, written to <model>/<step>/ledger.json with the gate, including the share it read) and may spend up to
    it until it ends. Every chat step directory with a ledger record and no aggregate is open, also when no process
    runs it (a resume opens a new ledger, so this only over-counts). `reads`: ledger path -> (booked, unbilled)
    from one read (missing ones are read here, once). Strict."""
    reads = {} if reads is None else reads
    out = []
    for f in sorted(I.RUNS.glob("*/*/ledger.json")):
        if f.parent.parent.name == "decision" or (f.parent / "aggregate.json").exists():
            continue
        try:
            rec = json.loads(f.read_text())
            cap, path = float(rec["cap"]), str(rec["path"])
        except (ValueError, KeyError, TypeError) as e:
            raise AccountingError(f"chat step record {f} unreadable: {e}") from None
        if path not in reads:
            reads[path] = ledger_read(path)
        booked = reads[path][0]
        share = (rec.get("gate") or {}).get("share")
        out.append(dict(model=f.parent.parent.name, step=f.parent.name, ledger=path, cap=cap, booked=booked,
                        headroom=max(cap - booked, 0.0), share=share))
    return out


def chat_accounting():
    """The chat side from one read per ledger: booked (every chat ledger), unused capacity of open steps (an open
    step contributes max(booked, cap)), unbilled reservations, and the open steps whose cap was fixed under a share
    above the chat partition ($110 - the decision lane cap) or under no recorded share: while one exists, the
    $107 + $3.00 partition does not hold and the decision lane waits."""
    reads = {str(p): ledger_read(p) for p in sorted(I.RUNS.glob("*/ledgers/*.db"))}
    steps = chat_liabilities(reads)
    partition = I.TOTAL_CAP_USD - cohort()["decision_lane_cap_usd"]
    blocks = [dict(model=s["model"], step=s["step"], share=s["share"], cap=s["cap"]) for s in steps
              if not isinstance(s["share"], (int, float)) or s["share"] > partition + 1e-9]
    booked = sum(b for b, _ in reads.values())
    unused = sum(s["headroom"] for s in steps)
    return dict(booked=booked, unused=unused, total=booked + unused, unbilled=sum(u for _, u in reads.values()),
                steps=steps, partition=partition, blocks=blocks)


def provider_of(key):
    """The provider of a decision run directory (None for a local setup); an unknown setup raises AccountingError:
    its spend could not be attributed to a subcap."""
    slug = key.split("/", 1)[1].rsplit("-", 1)[0]
    if slug not in setups():
        raise AccountingError(f"decision directory {key} belongs to no cohort setup: its spend is unattributed")
    return setups()[slug].get("provider")


def needs_ledger(key, step):
    m = I.entry(key)
    return m["hosted"] or (m["arm"] == "notes" and step.startswith("S"))


def admission_db():
    import sqlite3
    path = I.RUNS / "decision" / "admission.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=120, isolation_level=None)
    db.execute("CREATE TABLE IF NOT EXISTS allocations (id INTEGER PRIMARY KEY, key TEXT NOT NULL, step TEXT NOT NULL, "
               "provider TEXT, ledger TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL, opened_at TEXT NOT "
               "NULL, closed_at TEXT, booked REAL, binding TEXT, limits TEXT)")
    return db


def committed(row, booked=None):
    """What an allocation holds: an open one its whole amount (or more, if its ledger booked more), a closed one what
    its ledger booked."""
    _, _, _, ledger, amount, status = row
    spent = booked_rows(ledger) if booked is None else booked
    return max(amount, spent) if status == "open" else spent


def admit(key, step, ledger_path, expected, balance=None, want=None):
    """The one atomic admission (one SQLite write lock over every decision process) for a player step, a writer step
    or a probe: it reads every decision allocation (open ones at their full amount), every chat ledger and the
    provider's own ledgers, and grants an allocation (the step ledger's hard cap) only if all of these leave room
    for the step's expected cost: the decision lane's hard cap, the provider subcap, the hosted allowance (D6), the
    $110 total, the chat share (share + lane cap must fit in $110), rule (a) and, with writer calls, the OpenRouter
    balance less the $5 reserve. Concurrent admissions therefore cannot jointly pass a cap. Unreadable accounting
    refuses. Returns the gate record (allocation id, cap, ledger)."""
    m, c = I.entry(key), cohort()
    db = admission_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        rows = db.execute("SELECT id, key, provider, ledger, amount, status FROM allocations").fetchall()
        steps = dict(db.execute("SELECT id, step FROM allocations").fetchall())
        # One read per decision ledger, reused for every limit.
        dread = {}
        for path in [str(Path(r[3])) for r in rows] + [str(p) for p in sorted((I.RUNS / "decision").glob("*/ledgers/*.db"))]:
            if path not in dread:
                dread[path] = ledger_read(path)
        held = {r[0]: committed(r, booked=dread[str(Path(r[3]))][0]) for r in rows}
        # Every other decision ledger (none should exist outside an allocation) counts too, attributed to its
        # provider (an unattributable one refuses).
        allocated = {str(Path(r[3])) for r in rows}
        loose = [(provider_of(f"decision/{Path(p).parent.parent.name}"), b) for p, (b, _) in dread.items()
                 if p not in allocated]
        lane_used = sum(held.values()) + sum(v for _, v in loose)
        lane_cap = c["decision_lane_cap_usd"]
        share = I.share_cap()
        if share is not None and share + lane_cap > I.TOTAL_CAP_USD + 1e-9:
            raise Refused(f"the chat share ${share:.2f} plus the decision lane cap ${lane_cap:.2f} exceed "
                          f"${I.TOTAL_CAP_USD:.0f}: not hard allocations")
        fence = FENCE()
        acct = chat_accounting()
        if acct["blocks"]:
            # The partition ($110 - lane cap for the chat lanes, which they read at every step start) holds only once
            # no open chat step was capped under a larger (or unrecorded) share: wait for those steps to end.
            raise Refused("partition not yet in force: waiting for chat steps capped under a share above "
                          f"${acct['partition']:.2f}: " + ", ".join(f"{b['model']} {b['step']} (share {b['share']}, cap "
                                                                      f"${b['cap']:.2f})" for b in acct["blocks"]),
                          pause=True)
        chat, chat_open = acct["booked"], acct["unused"]
        limits = {"decision lane cap": lane_cap - lane_used,
                  "rule (b) limit": I.TOTAL_CAP_USD - acct["total"] - lane_used,
                  "rule (a) limit": I.ESTIMATE_FACTOR * m["estimate"] - arm_booked(key)}
        provider = m.get("provider") if m["hosted"] else None
        if provider:
            if not (decided("D6_hosted_allowance_usd").get(provider) or 0) > 0:
                raise Refused(f"D6: no hosted allowance for {provider}; no billed call", pause=True)
            subcap = c.get("provider_subcaps_usd", {}).get(provider)
            if subcap is not None:
                outside = sum(booked_rows(I.STATE_ROOT / rel) for rel in c.get("provider_ledgers", {}).get(provider, []))
                ours = sum(held[r[0]] for r in rows if r[2] == provider) + sum(v for p, v in loose if p == provider)
                limits["provider subcap"] = subcap - outside - ours
        if balance is not None:
            # OpenRouter money promised but possibly not yet charged, under the same lock: open writer allocations
            # (notes arms' series steps), unbilled (open or lost) reservations of every other decision ledger and of
            # every chat ledger, and the unused capacity of open chat steps (all billed chat models use OpenRouter).
            writers = sum(held[r[0]] for r in rows if r[5] == "open" and r[1].endswith("-notes")
                          and str(steps[r[0]]).startswith("S"))
            open_ids = {str(Path(r[3])) for r in rows if r[5] == "open"}
            decision_unbilled = sum(u for p, (_, u) in dread.items() if p not in open_ids)
            limits["balance"] = (balance - I.BALANCE_RESERVE_USD - writers - decision_unbilled - acct["unbilled"]
                                 - chat_open)
        if want is not None:
            limits["requested"] = want
        binding = min(limits, key=limits.get)
        amount = limits[binding]
        if round(amount, 6) < round(expected, 6):
            raise Refused(f"{step}: {binding} leaves ${amount:.4f}, below the expected ${expected:.4f} "
                          f"(limits {json.dumps({k: round(v, 4) for k, v in limits.items()})})",
                          pause=binding in ("balance",))
        cur = db.execute("INSERT INTO allocations (key, step, provider, ledger, amount, status, opened_at, binding, "
                         "limits) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)",
                         (key, step, provider, str(ledger_path), amount, I.now(), binding, json.dumps(limits)))
        db.execute("COMMIT")
        return dict(allocation=cur.lastrowid, step=step, expected=expected, cap=amount, binding=binding,
                    limits=limits, ledger=str(ledger_path), share=share, chat_booked=chat, chat_open_headroom=chat_open,
                    chat_unbilled=acct["unbilled"], partition=acct["partition"], lane_used=lane_used,
                    chat_workers=fence)
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def release(gate):
    """Close an allocation at what its ledger booked; on unreadable accounting it stays open (held in full)."""
    db = admission_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        booked = booked_rows(gate["ledger"])
        db.execute("UPDATE allocations SET status = 'closed', closed_at = ?, booked = ? WHERE id = ?",
                   (I.now(), booked, gate["allocation"]))
        db.execute("COMMIT")
    except AccountingError as e:
        db.execute("ROLLBACK")
        print(f"allocation {gate['allocation']} kept open: {e}", file=sys.stderr)
    finally:
        db.close()


def next_ledger(key, step):
    d = I.mdir(key) / "ledgers"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{step}-a{1 + len(list(d.glob(f'{step}-a*.db')))}.db"


def money_gate(key, step, balance_reader=I.openrouter_balance):
    """Before a billed step: the atomic admission with the step's expected cost; with writer calls, the OpenRouter
    balance first (its $5 reserve). The step ledger's cap is the allocation."""
    expected = I.step_estimate(key, step)
    balance = None
    if I.entry(key)["arm"] == "notes" and step.startswith("S"):
        balance = balance_reader()["balance"]
    return admit(key, step, next_ledger(key, step), expected, balance=balance,
                 want=I.ESTIMATE_FACTOR * I.entry(key)["estimate"])


def provider_spent(provider):
    """A provider's booked dollars: its own outside ledgers (Nace: the league's) and every decision ledger of it."""
    outside = sum(booked_rows(I.STATE_ROOT / rel) for rel in cohort().get("provider_ledgers", {}).get(provider, []))
    root = I.RUNS / "decision"
    dirs = [p for p in root.glob("*") if p.is_dir() and (p / "ledgers").exists()
            and provider_of(f"decision/{p.name}") == provider] if root.exists() else []
    return outside + sum(booked_rows(f) for p in dirs for f in sorted((p / "ledgers").glob("*.db")))


# --- Arm W: the worst-mistakes selector ------------------------------------------------------------------------

def select_worst(decs, exclude, n=WORST_N):
    """Addendum §5: eligible = model-decided, valid, GNUbg-scored decisions whose board is not a frozen test
    position (removed before selection) and whose loss does not print as 0.000; largest loss first at full
    precision, ties by earlier game, lower turn number, lower turn id. Returns (selected, excluded test positions)."""
    scored = [d for d in decs if d["scored"] and not d["invalid"]]
    excluded = [d for d in scored if d["board_key"] in exclude]
    pool = [d for d in scored if d["board_key"] not in exclude and f"{d['loss']:.3f}" != "0.000"]
    pool.sort(key=lambda d: (-d["loss"], d["game"], d["turn_no"], d["turn_id"]))
    return pool[:n], excluded


def render_states(rows):
    """The league state text (`jevgammon render`, prompt bg-v2, League 2's order seed) for rows of
    {position, dice}: the runner's own rendering, no model call."""
    payload = "".join(json.dumps(dict(position=r["position"], dice=list(r["dice"]), prompt=I.PROMPT_VERSION)) + "\n"
                      for r in rows)
    out = subprocess.run([str(I.BIN), "render", "--order-seed", str(I.ORDER_SEED)], input=payload, cwd=I.CODE,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"render failed: {out.stderr[-1000:]}")
    return [json.loads(x) for x in out.stdout.splitlines() if x.strip()]


def position_block(state):
    """The league prompt's position block, verbatim: 'Position (your numbering; you move 24 -> 1):' through the
    'Dice: a-b' line (the last one: a block at the start of the state may hold earlier examples)."""
    i = state.rfind(POSITION_HEAD)
    j = state.index("\nDice: ", i)
    k = state.index("\n", j + 1)
    return state[i:k]


def worst_block(chosen, blocks):
    """The addendum's serialization: board, chosen play, best play and loss only."""
    if not chosen:
        return ""
    lines = [WORST_OPEN, WORST_INTRO, ""]
    for k, (d, pos) in enumerate(zip(chosen, blocks), 1):
        lines += [f"Example {k} (game {d['game']}, turn {d['turn_no']}):", pos,
                  f"You played: {d['plays'][d['chosen']]}. GNUbg's best play: {d['plays'][d['best']]}. "
                  f"Equity lost: {d['loss']:.3f}.", ""]
    return "\n".join(lines + [WORST_CLOSE])


# --- Steps -----------------------------------------------------------------------------------------------------

def test_config(key):
    return lambda name, parallel, ledger: player_config(key, name, parallel, ledger=ledger)


def run_empty(key, step, gate):
    d = I.step_dir(key, step)
    ledger = dict(path=Path(gate["ledger"]), cap=gate["cap"], binding=gate["binding"]) if gate else None
    if ledger:
        I.write_atomic(d / "ledger.json", json.dumps(dict(ledger, path=str(ledger["path"]), gate=gate), indent=1))
    m = I.run_test(key, step, I.test_name(key, step), "", d, ledger=ledger, config=test_config(key))
    if not I.test_complete(m):
        raise RuntimeError(f"{step}: {m['answered']} answered, {m['failed']} failed; run again to re-ask")
    I.write_atomic(d / "aggregate.json", json.dumps(dict(step=step, finished_at=I.now(), test=m), indent=1))


def shared_empty(key, step):
    """D1 shared: the worst arm's empty runs are the notes arm's (same setup, same schedule); it waits for them."""
    slug, _ = split(key)
    src = I.step_dir(arm_key(slug, "notes"), step) / "aggregate.json"
    if not src.exists():
        raise I.Pause(f"{step}: waiting for the shared empty run of {arm_key(slug, 'notes')} (D1 shared)")
    agg = json.loads(src.read_text())
    I.write_atomic(I.step_dir(key, step) / "aggregate.json",
                   json.dumps(dict(agg, shared_from=arm_key(slug, "notes")), indent=1))


def run_series(key, step, gate):
    s = I.series_of(step)
    d = I.step_dir(key, step)
    d.mkdir(parents=True, exist_ok=True)
    attempt = I.attempt_of(key, step)
    name = I.game_name(key, s, attempt)
    prior = I.match_of(key, name)
    if prior is not None and not (d / "match.done").exists():
        I.archive_attempt(key, step, (d / "failed").read_text() if (d / "failed").exists() else f"match {prior}")
        d.mkdir(parents=True, exist_ok=True)
        attempt = I.attempt_of(key, step)
        name = I.game_name(key, s, attempt)
    ledger = dict(path=Path(gate["ledger"]), cap=gate["cap"], binding=gate["binding"]) if gate else None
    if ledger:
        I.write_atomic(d / "ledger.json", json.dumps(dict(ledger, path=str(ledger["path"]), gate=gate), indent=1))
    player = player_config(key, name, 1, note_file=d / "note.txt", ledger=ledger)
    I.held(key, step)
    if not (d / "match.done").exists():
        I.log(key, "series_start", step=step, attempt=attempt, seed=I.series_seed(s), arm=I.entry(key)["arm"],
              lesson_prompt_sha256=I.lesson_prompt_sha256())
        (d / "note.txt").write_text("")  # the series starts with no block (reset)
        I.write_atomic(d / "player.json", json.dumps(player, indent=1))
        hook = f"{sys.executable} {Path(__file__).resolve()} after-game --arm {key} --series {s}"
        r = subprocess.run([str(I.BIN), "--model1-config", str(d / "player.json"), "--model2", "gnubg-weak",
                            "--seed", str(I.series_seed(s)), "--order-seed", str(I.ORDER_SEED), "--rounds",
                            str(I.GAMES // 2), "--fixed-rounds", "--clock", "0", "--max-turns",
                            str(I.TEST_CONTEXT["max_turns"]), "--prompt-version", I.PROMPT_VERSION, "--quiet",
                            "--db", str(I.db_path(key)), "--after-game", hook], cwd=I.CODE, capture_output=True,
                           text=True, env=dict(os.environ))
        (d / "match.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            (d / "failed").write_text(r.stderr[-2000:])
            I.log(key, "series_failed", step=step, attempt=attempt, stderr=r.stderr[-1000:])
            if stop := I.context_stop(r.stderr):
                raise stop  # the games so far stay stored; nothing is replayed, shortened or scored from a subset
            if "ROUTE CHECK" in r.stderr:
                raise I.Stop(f"{step}: {r.stderr[-600:]}")
            if (text := I.key_limit_text(r.stderr)) or "KEY LIMIT:" in r.stderr:
                I.key_limit_pause(key, step, text or r.stderr[-600:])
            if "BUDGET CAP" in r.stderr:
                raise I.BudgetRefused(r.stderr[-500:])
            raise RuntimeError(f"{key} {step}: match failed: {r.stderr[-800:]}")
        I.write_atomic(d / "match.done", str(I.match_of(key, name)[0]))
    context = (d / "contexts" / "after-g10.txt").read_text() if (d / "contexts" / "after-g10.txt").exists() else ""
    m = I.run_test(key, step, I.test_name(key, step, attempt), context, d, ledger=ledger, config=test_config(key))
    m["wall_seconds"] = round(m["wall_seconds"] + sum(e.get("wall_seconds", 0) for e in I.events(key) if e["event"] ==
                                                      "t10_asked" and e["step"] == step and e.get("attempt") == attempt), 1)
    if not I.test_complete(m):
        raise RuntimeError(f"{step} T10: {m['answered']} answered, {m['failed']} failed; run again to re-ask")
    write_aggregate(key, step, attempt, m)


def after_game(key, s):
    """The runner's after-game hook: score the game; notes: one writer call; worst: the selector; the next game's
    block; T10 after game 10 with the series' last block."""
    step = f"S{s}"
    d = I.step_dir(key, step)
    attempt = I.attempt_of(key, step)
    match_id = int(os.environ["MATCH_ID"])
    g = 2 * (int(os.environ["GAME_ROUND"]) - 1) + int(os.environ["GAME_LEG"])
    if I.DRY and os.environ.get("IMPROVE_DRY_FAIL_AFTER_GAME") == str(g):
        raise SystemExit(f"dry-run fault injection after game {g}")
    I.score_match(key, match_id)
    exclude = I.test_board_keys()
    decs = I.game_decisions(key, match_id, g)
    excluded = sum(1 for x in decs if x["scored"] and x["game"] == g and x["board_key"] in exclude)
    I.log(key, "test_positions_excluded", step=step, game=g, n=excluded)
    if I.entry(key)["arm"] == "notes":
        results = I.game_results(key, match_id)
        ok = [x for x in I.eligible(decs, exclude) if x["game"] == g]
        record = "\n".join([I.game_header(g, results)] + [I.record_line(x) for x in ok])
        write_notes(key, step, g, record)
        blocks = [(k, (d / f"notes-g{k:02d}.txt").read_text().strip()) for k in range(1, g + 1)]
        block = I.lessons_context(blocks, intro=NOTES_INTRO)
    else:
        chosen, _ = select_worst(decs, exclude)
        states = render_states(chosen) if chosen else []
        block = worst_block(chosen, [position_block(x["state"]) for x in states])
        I.write_atomic(d / f"worst-g{g:02d}.json", json.dumps(dict(
            after_game=g, gnubg=GNUBG, scores=str(I.plays_path(key)), scores_sha256=I.sha256_file(I.plays_path(key)),
            test_positions_excluded_so_far=sum(1 for x in decs if x["scored"] and x["board_key"] in exclude),
            selected=[dict(turn_id=x["turn_id"], game=x["game"], turn_no=x["turn_no"], board_key=x["board_key"],
                           loss=x["loss"]) for x in chosen]), indent=1))
        I.log(key, "worst_selected", step=step, after_game=g, n=len(chosen))
    I.write_atomic(d / "note.txt", block)
    (d / "contexts").mkdir(exist_ok=True)
    (d / "contexts" / f"after-g{g:02d}.txt").write_text(block)
    I.log(key, "context", step=step, after_game=g, chars=len(block),
          sha256=hashlib.sha256(block.encode()).hexdigest())
    if g == I.GAMES:
        ledger = json.loads((d / "ledger.json").read_text()) if (d / "ledger.json").exists() else None
        try:
            m = I.run_test(key, step, I.test_name(key, step, attempt), block, d, ledger=ledger, rounds=1,
                           config=test_config(key))
            I.log(key, "t10_asked", step=step, attempt=attempt, answered=m["answered"], failed=m["failed"],
                  wall_seconds=m["wall_seconds"])
        except Exception as e:  # noqa: BLE001  (re-asked, or stopped, by run_series)
            I.log(key, "t10_deferred", step=step, error=str(e)[-500:])


def write_notes(key, step, g, record):
    """One writer call after game g (the pilot's prompt, byte-identical), retried until it returns; a refused budget
    reservation or a failed route check stops at once. Stores the raw reply, the kept notes and the cut counts."""
    d = I.step_dir(key, step)
    user = I.LESSONS_USER.read_text().format(game=g, record=record)
    system = I.LESSONS_SYSTEM.read_text().strip()
    (d / "writer-system.txt").write_text(system)
    (d / f"writer-g{g:02d}.user.txt").write_text(user)
    call = d / f"writer-g{g:02d}.call.json"
    if I.DRY:
        raw = "\n".join(f"- (dry run) game {g} note {k}: " + " ".join(["placeholder"] * 24) for k in range(1, 7))
        out = dict(text=raw, dry=True, input_tokens=0, output_tokens=0, cost_usd=None, reported_cost_usd=None,
                   in_flight=1, wall_ms=0, exchanges=[])
        I.write_atomic(call, json.dumps(out, indent=1))
    else:
        ledger = json.loads((d / "ledger.json").read_text()) if (d / "ledger.json").exists() else None
        cfg = writer_config(key, I.game_name(key, I.series_of(step), I.attempt_of(key, step)), ledger)
        (d / "writer-player.json").write_text(json.dumps(cfg, indent=1))
        for k in range(20):
            r = subprocess.run([str(I.BIN), "lesson", "--player", str(d / "writer-player.json"), "--system",
                                str(d / "writer-system.txt"), "--user", str(d / f"writer-g{g:02d}.user.txt"),
                                "--out", str(call)], cwd=I.CODE, capture_output=True, text=True)
            if r.returncode == 0:
                break
            I.log(key, "writer_call_failed", step=step, game=g, attempt=k + 1, stderr=r.stderr[-500:])
            if "ROUTE CHECK" in r.stderr:
                raise SystemExit(f"ROUTE CHECK: writer call rejected: {r.stderr[-600:]}")
            if text := I.key_limit_text(r.stderr):
                I.write_atomic(I.mdir(key) / "hold.json", json.dumps(dict(
                    reason="paused: shared-balance priority (provider account limit: HTTP 403 key limit / 402 credits)",
                    at=I.now(), step=step), indent=1))
                raise SystemExit(f"KEY LIMIT: writer call after game {g}: {text[:300]}")
            if "BUDGET CAP" in r.stderr:
                raise SystemExit(f"BUDGET CAP: writer call refused: {r.stderr[-300:]}")
            time.sleep(min(600, 30 * (k + 1)))
        else:
            raise SystemExit(f"writer call after game {g} failed 20 times")
        out = json.loads(call.read_text())
    raw = out.get("text") or ""
    (d / f"writer-g{g:02d}.raw.txt").write_text(raw)
    text, cut = I.limit_lessons(raw.strip())
    I.write_atomic(d / f"notes-g{g:02d}.txt", text + "\n")
    I.log(key, "writer_call", step=step, game=g, input_tokens=out.get("input_tokens"),
          output_tokens=out.get("output_tokens"), cost_usd=out.get("cost_usd"),
          reported_cost_usd=out.get("reported_cost_usd"), wall_ms=out.get("wall_ms"), empty=not text, **cut)
    return text, cut


def write_aggregate(key, step, attempt, t10):
    d = I.step_dir(key, step)
    match_id = int((d / "match.done").read_text())
    decs = I.game_decisions(key, match_id)
    results = I.game_results(key, match_id)
    ev = [e for e in I.events(key) if e.get("step") == step]
    calls = [e for e in ev if e["event"] == "writer_call"][-I.GAMES:]
    agg = dict(step=step, series=I.series_of(step), attempt=attempt, arm=I.entry(key)["arm"],
               seed=I.series_seed(I.series_of(step)), finished_at=I.now(), games=len(results),
               wins=sum(r["won"] for r in results.values()), game_decisions=len(decs),
               game_invalid=sum(x["invalid"] for x in decs),
               game_in_flight_max=max((x["in_flight"] or 0 for x in decs), default=0),
               writer_calls=len(calls), notes_cut=sum(bool(e.get("cut")) for e in calls),
               notes_empty=sum(bool(e.get("empty")) for e in calls),
               worst_blocks=sum(1 for e in ev if e["event"] == "worst_selected"), restarts=attempt - 1,
               context_sha256={e["after_game"]: e["sha256"] for e in ev if e["event"] == "context"},
               test_positions_excluded=sum(e["n"] for e in ev if e["event"] == "test_positions_excluded"),
               t10=t10, lesson_prompt_sha256=I.lesson_prompt_sha256(), test_set_sha256=I.sha256_file(I.TEST_SET))
    I.write_atomic(d / "aggregate.json", json.dumps(agg, indent=1))


def writer_route_check(key, step):
    """None, or why a writer reply of the step does not name the pinned writer model and provider."""
    exp = writer_expect()
    ids = []
    for f in I.step_dir(key, step).rglob("writer-g*.call.json"):
        for x in json.loads(f.read_text()).get("exchanges", []):
            try:
                v = json.loads(x.get("response"))
                ids.append((I.pointer(v, "/model"), I.pointer(v, "/provider")))
            except (TypeError, ValueError):
                ids.append((None, None))
    bad = sorted({(m, p) for m, p in ids if m not in exp["models"] or p != exp["provider"]}, key=str)
    if bad:
        return f"writer route check: replies named {bad[:5]}, expected {exp['models']} on {exp['provider']}"
    return None


# --- Run -------------------------------------------------------------------------------------------------------

def run(key, until=None, balance_reader=I.openrouter_balance):
    """Runs the arm's next steps in order; returns 0 (done or reached `until`), STOP or PAUSE (also for an arm that
    is not eligible: nothing is called)."""
    slug, arm = split(key)
    m = I.entry(key)
    state, why = arm_state(slug, arm)
    if state != "eligible":
        print(f"{key}: {state}: {why}; nothing called", file=sys.stderr)
        return I.PAUSE if state == "pending" else I.STOP
    hold = I.mdir(key) / "hold.json"
    if hold.exists():
        why = json.loads(hold.read_text())["reason"]
        I.write_atomic(I.mdir(key) / "paused.json", json.dumps(dict(at=I.now(), reason=why), indent=1))
        I.log(key, "paused", reason=why)
        return I.PAUSE
    I.check_inputs()
    check_addendum()
    I.mdir(key).mkdir(parents=True, exist_ok=True)
    lock = open(I.mdir(key) / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f"{key}: another run holds the lock") from None
    hosted_lock = None
    if m["hosted"]:
        # One hosted arm at a time: the provider subcaps and the $110 are checked per step, never by two at once.
        (I.RUNS / "decision").mkdir(parents=True, exist_ok=True)
        hosted_lock = open(I.RUNS / "decision" / "hosted.lock", "w")
        try:
            fcntl.flock(hosted_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise SystemExit(f"{key}: another hosted decision arm is running") from None
    if (I.mdir(key) / "stopped.json").exists():
        print(f"{key}: stopped: {json.loads((I.mdir(key) / 'stopped.json').read_text())['reason']}")
        lock.close()
        return I.STOP
    (I.mdir(key) / "paused.json").unlink(missing_ok=True)
    I.ensure_runner_db(key)
    I.bind_plan(key)
    bind_run(key)
    shared = decided("D1_empty_runs") == "shared"
    try:
        while (step := I.next_step(key)) is not None:
            for f in ("route-rejections.jsonl", "writer-rejections.jsonl"):
                rejected = I.mdir(key) / f
                if rejected.exists() and rejected.stat().st_size:
                    raise I.Stop(f"route check: {rejected.read_text().splitlines()[0][:600]}")
            if shared and arm == "worst" and step.startswith("E"):
                shared_empty(key, step)
                I.log(key, "step_done", step=step, shared_from=arm_key(slug, "notes"))
                continue
            try:
                gate = money_gate(key, step, balance_reader) if needs_ledger(key, step) and not I.DRY else None
            except Refused as e:
                raise (I.Pause if e.pause else I.Stop)(f"{step}: admission refused: {e}") from None
            except AccountingError as e:
                raise I.Pause(f"{step}: accounting unreadable, nothing admitted: {e}") from None
            I.log(key, "step_start", step=step, gate=gate, binary=I.binary_identity(),
                  cohort_sha256=I.sha256_file(COHORT_FILE))
            try:
                (run_empty if step.startswith("E") else run_series)(key, step, gate)
            except I.BudgetRefused as e:
                binding = (gate or {}).get("binding", "")
                if binding in ("balance", "share"):
                    raise I.Pause(f"{step}: the step ledger's balance limit refused a request: {e}") from None
                raise I.Stop(f"{step}: {binding} reached before a request: {e}") from None
            finally:
                if gate:
                    release(gate)
            if not I.DRY:
                why = I.route_check(key, I.response_ids(key, step)) or writer_route_check(key, step)
                if why:
                    raise I.Stop(f"{step}: {why}")
            I.log(key, "step_done", step=step, billed=I.billed(key, step))
            if needs_ledger(key, "S1") and not I.DRY and I.step_done(key, "E1") and I.step_done(key, "S1") \
                    and I.cost_check(key) is None:
                s1, e1 = I.billed(key, "S1"), I.billed(key, "E1")
                why = I.rule_a(key, s1, e1)
                I.write_atomic(I.mdir(key) / "cost_check.json", json.dumps(
                    dict(at=I.now(), S1=s1, E1=e1, projected=I.projected_full(s1, e1), estimate=m["estimate"],
                         limit=I.ESTIMATE_FACTOR * m["estimate"], fired=why), indent=1))
                if why:
                    raise I.Stop(why)
            summary()
            if step == until:
                return 0
        return 0
    except (I.Stop, I.Pause) as e:
        kind = "paused" if isinstance(e, I.Pause) else "stopped"
        I.write_atomic(I.mdir(key) / f"{kind}.json", json.dumps(dict(at=I.now(), reason=str(e)), indent=1))
        I.log(key, kind, reason=str(e))
        print(f"{kind.upper()} {key}: {e}", file=sys.stderr)
        return I.PAUSE if kind == "paused" else I.STOP
    finally:
        summary()
        lock.close()
        if hosted_lock:
            hosted_lock.close()


# --- Preflight: the conservative context guard on retained league requests (no call) ---------------------------

def synthetic_notes_block():
    """The largest notes block the cut rule allows: 10 games x 5 lessons x 30 words (12 bytes a word)."""
    lesson = "- " + " ".join([MAX_WORD] * 30)
    return I.lessons_context([(g, "\n".join([lesson] * I.MAX_LESSONS)) for g in range(1, I.GAMES + 1)],
                             intro=NOTES_INTRO)


def checker_text_length(position):
    """An upper estimate of the checker lists' length of a stored position (either numbering), for picking the
    League positions whose rendered position block can be the largest."""
    pts = position["points"]

    def side(sign, numbering):
        return sum(len(f"{numbering(i)}:{abs(n)} ") for i, n in enumerate(pts) if n * sign > 0)
    return sum(max(side(s, f) for f in (lambda i: i + 1, lambda i: 24 - i)) for s in (1, -1))


def league_rows(candidates=2000):
    """The `candidates` distinct model-decided League positions of v3.db (board and dice) with the longest checker
    lists: the rendered position block is those lists plus fixed lines and a few digits, so the largest blocks are
    among them (rendering all 185,900 takes over 15 minutes)."""
    import sqlite3
    db = sqlite3.connect(f"file:{I.V3_DB}?mode=ro", uri=True, timeout=60)
    rows = [dict(position=json.loads(p), dice=(a, b))
            for p, a, b in db.execute("SELECT DISTINCT position, die1, die2 FROM turns WHERE decided_by = 'model'")]
    db.close()
    rows.sort(key=lambda r: checker_text_length(r["position"]), reverse=True)
    return rows[:candidates]


def longest_play():
    """The longest play notation any League decision chose (v3.db turns.move)."""
    import sqlite3
    db = sqlite3.connect(f"file:{I.V3_DB}?mode=ro", uri=True, timeout=60)
    (move,) = db.execute("SELECT move FROM turns ORDER BY length(move) DESC LIMIT 1").fetchone()
    db.close()
    return move


def synthetic_worst_block(rows=None):
    """The largest worst-mistakes block: the 5 largest rendered League position blocks, the longest League play
    notation as both plays, two-digit game and three-digit turn numbers, a four-digit loss."""
    states = render_states(rows if rows is not None else league_rows())
    blocks = sorted((position_block(x["state"]) for x in states), key=lambda b: len(b.encode()), reverse=True)[:WORST_N]
    longest = longest_play()
    chosen = [dict(game=10, turn_no=299, plays=[longest], chosen=0, best=0, loss=9.999) for _ in blocks]
    return worst_block(chosen, blocks)


def added_bytes(block):
    """Bytes a block adds to a request body: the JSON-escaped block and its blank-line separator."""
    return len(json.dumps(block + "\n\n", ensure_ascii=False).encode()) - 2


def guard_preflight(write=True, notes=None, worst=None):
    """Per hosted setup with a client gate: of its retained league requests (v3.db, valid matches), how many the
    conservative guard (request bytes + wrapper + output > documented limit) refuses with no block, with the largest
    notes block and with the largest worst-mistakes block. A setup with any refusal is 'not tested: conservative
    context guard' for that arm (none: both arms). Recorded in preflight/guard.json; no call."""
    import sqlite3
    notes = notes if notes is not None else synthetic_notes_block()
    worst = worst if worst is not None else synthetic_worst_block()
    extra = dict(none=0, notes=added_bytes(notes), worst=added_bytes(worst))
    db = sqlite3.connect(f"file:{I.V3_DB}?mode=ro", uri=True, timeout=60)
    out = dict(at=I.now(), method="v3.db exchanges of the setup's valid matches with a response; bound = request bytes"
               " + block bytes + wrapper (4,096 when undocumented) + output tokens", added_bytes=extra,
               notes_block_sha256=hashlib.sha256(notes.encode()).hexdigest(),
               worst_block_sha256=hashlib.sha256(worst.encode()).hexdigest(), setups={})
    for s in cohort()["setups"]:
        g = s.get("gate")
        if not g or g["kind"] != "client":
            continue
        (pid,) = db.execute("SELECT id FROM players WHERE name = ?", (s["setup"],)).fetchone()
        sizes = [r[0] for r in db.execute(
            "SELECT length(CAST(x.request AS BLOB)) FROM exchanges x JOIN turns t ON t.id = x.turn_id "
            "JOIN games gm ON gm.id = t.game_id JOIN matches m ON m.id = gm.match_id WHERE m.valid = 1 AND "
            "x.response IS NOT NULL AND ((m.player1 = ? AND t.player = 1) OR (m.player2 = ? AND t.player = 2))",
            (pid, pid))]
        wrapper = g.get("wrapper_tokens") or 4096
        limit = g.get("limit_tokens")
        refused = {k: (len(sizes) if limit is None else sum(1 for b in sizes if b + e + wrapper +
                                                            g.get("output_tokens", 0) > limit))
                   for k, e in extra.items()}
        out["setups"][s["slug"]] = dict(setup=s["setup"], requests=len(sizes), max_bytes=max(sizes, default=0),
                                        limit_tokens=limit, wrapper_tokens=wrapper, refused=refused,
                                        refused_share={k: (v / len(sizes) if sizes else None) for k, v in refused.items()})
    db.close()
    if write:
        I.write_atomic(PREFLIGHT() / "guard.json", json.dumps(out, indent=1))
    return out


# --- Preflight: the local render check Lr (no call, no GPU) ----------------------------------------------------

HF_HUB = Path.home() / ".cache/huggingface/hub"
LR_DIR = HERE / "lr"
LR_SAMPLE = 50  # stored league requests per setup: the largest plus evenly spaced ones by size


def lr_routes():
    """Per local setup: the renderer lr/<route>.py, run under the server's own environment and pinned code, and the
    server files whose hashes the record keeps. Renderer contract: stdin one JSON line per case {id, body (the System
    One body as the runner sends it), pieces {name: text}}; stdout one line per case, in order, {id, status ok|refused
    (the server's own pre-inference gate), error, sequences (token count of every inference sequence), limits, cut
    (any truncation or content-dropping path), missing (pieces not in full in every sequence's final input after the
    route's declared transformation), transformed, roundtrip (the token ids decode to the final input)}."""
    glide = HF_HUB / "models--fastino--GLiDE/snapshots/a7e45896be7c96ba3354891da790c5ec99c30b6c"
    decider = HF_HUB / "models--perplexity-ai--pplx-decider-v1.2/snapshots/225c913ddc8761a8264f04f64548e1f97e443eb3"
    pkg = decider / "source/src/pplx_decider"
    flash = Path.home() / "code/pplx-decider/checkpoint-flash-v1.2"
    fpkg = flash / "source/src/pplx_decider"
    return {
        "glide-v1.2-local": dict(
            route="glide/server.py (tools/v3/servers/glide-v12.sh)", renderer=LR_DIR / "glide_v12.py",
            cmd=[str(Path.home() / "code/glide/.venv/bin/python"), str(LR_DIR / "glide_v12.py"), "--model", str(glide)],
            env=dict(PYTHONPATH=str(glide)),
            code=[glide / "glide" / f for f in ("server.py", "model.py", "prompt.py")] + [glide / "tokenizer.json"]),
        "decider-v1.2-27b": dict(
            route="pplx_decider_server.py (tools/v3/servers/decider-v1.2.sh 27b)", renderer=LR_DIR / "decider.py",
            cmd=[str(Path.home() / "code/pplx-decider/.venv-v1.2/bin/python"), str(LR_DIR / "decider.py"),
                 "--model", str(decider)],
            env={}, code=[Path.home() / "code/pplx-decider/pplx_decider_server.py", pkg / "model.py",
                          pkg / "protocol.py", decider / "tokenizer.json"]),
        # Decider Flash v1.2 (cohort amendment 2026-11-12): the same server and renderer on the Flash checkpoint and
        # the pplx_decider package it ships (tools/v3/servers/decider-v1.2.sh flash).
        "decider-flash-v1.2": dict(
            route="pplx_decider_server.py (tools/v3/servers/decider-v1.2.sh flash)", renderer=LR_DIR / "decider.py",
            cmd=[str(Path.home() / "code/pplx-decider/.venv-v1.2/bin/python"), str(LR_DIR / "decider.py"),
                 "--model", str(flash)],
            env={}, code=[Path.home() / "code/pplx-decider/pplx_decider_server.py", fpkg / "model.py",
                          fpkg / "protocol.py", flash / "tokenizer.json"]),
        "baselabs-elephant-1": baselabs_route("elephant-1", "b3f8a93462fb1051a9de031e94a7ff380e254072"),
        "baselabs-mammoth-1": baselabs_route("mammoth-1", "61cec44c281c693992e3d6ebeb44dd3402dfa186"),
    }


def baselabs_route(model, revision):
    """baselabs_server.py (decision-models 12a2ea1) in image baselabs-serve:81ce62f, as workspace/late3/baselabs.sh
    serves it (--name baselabs/<model>): the renderer runs in the image, CPU only, no network."""
    snap = HF_HUB / f"models--baselabs--{model}/snapshots/{revision}"
    return dict(
        route="baselabs_server.py (decision-models 12a2ea1, image baselabs-serve:81ce62f)",
        renderer=LR_DIR / "baselabs.py",
        cmd=["docker", "run", "--rm", "-i", "--network", "none", "-e", "HF_HUB_OFFLINE=1", "-e", "CUDA_VISIBLE_DEVICES=",
             "-v", f"{HF_HUB}:/hf:ro", "-v", f"{LR_DIR}:/lr:ro", "--entrypoint", "/opt/conda/bin/python",
             "baselabs-serve:81ce62f", "/lr/baselabs.py", "--model", f"/hf/{snap.relative_to(HF_HUB)}",
             "--name", f"baselabs/{model}"],
        env={}, code=[Path.home() / "code/analysis/decision-models/runner/servers/baselabs_server.py"]
        + [snap / f for f in ("engine.py", "serve.patch", "tokenizer.json", "readout.json", "config.json")])


def stored_requests(setup, n=LR_SAMPLE):
    """(exchange id, request body) of the setup's retained league requests (valid matches, with a response): the
    largest and n - 1 more evenly spaced by size, largest first; and the number retained."""
    import sqlite3
    db = sqlite3.connect(f"file:{I.V3_DB}?mode=ro", uri=True, timeout=60)
    (pid,) = db.execute("SELECT id FROM players WHERE name = ?", (setup,)).fetchone()
    q = ("FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games gm ON gm.id = t.game_id JOIN matches m "
         "ON m.id = gm.match_id WHERE m.valid = 1 AND x.response IS NOT NULL AND ((m.player1 = ? AND t.player = 1) "
         "OR (m.player2 = ? AND t.player = 2))")
    sizes = db.execute(f"SELECT x.id, length(CAST(x.request AS BLOB)) {q} ORDER BY 2 DESC, 1", (pid, pid)).fetchall()
    pick = {sizes[round(i * (len(sizes) - 1) / max(n - 1, 1))][0] for i in range(n)} if sizes else set()
    size = dict(sizes)
    rows = [(i, json.loads(r)) for i, r in db.execute(
        f"SELECT id, request FROM exchanges WHERE id IN ({','.join('?' * len(pick))})", sorted(pick))]
    db.close()
    return sorted(rows, key=lambda r: (-size[r[0]], r[0])), len(sizes)


def lr_cases(rows, blocks):
    """Renderer input lines: every stored request with no block and with each arm's largest block at the start of
    `state` as the runner puts it (src/players/decision.rs state_with_block: block.trim_end() + blank line + state)."""
    out = []
    for xid, body in rows:
        for kind, block in blocks.items():
            b = dict(body, state=f"{block.rstrip()}\n\n{body['state']}" if block else body["state"])
            pieces = dict(state=body["state"])
            for qk, q in body["questions"].items():
                pieces[f"instructions:{qk}"] = q.get("instructions") or ""
                pieces.update({f"option:{qk}:{k}": v for k, v in (q.get("criteria") or {}).items()
                               if isinstance(v, str) and v})
            if block:
                pieces["block"] = block.rstrip()
            out.append(dict(id=f"{xid}:{kind}", body=b, pieces=pieces))
    return out


def lr_judge(results):
    """Per kind (none, notes, worst): counts, the largest sequence, and every failing case. A case passes when the
    server's gate accepts it, no cut path is taken, every piece is present in full and the tokens decode back."""
    kinds = {}
    for r in results:
        xid, kind = r["id"].rsplit(":", 1)
        k = kinds.setdefault(kind, dict(cases=0, passed=0, refused=0, cut=0, missing=0, roundtrip_failed=0,
                                        max_tokens=0, max_tokens_exchange=None, limits=r.get("limits"), failures=[]))
        k["cases"] += 1
        bad = [why for why, hit in (("refused", r["status"] != "ok"), ("cut", r["cut"]), ("missing", r["missing"]),
                                    ("roundtrip_failed", not r["roundtrip"])) if hit]
        for why in bad:
            k[why] += 1
        if bad:
            k["failures"].append(dict(exchange=int(xid), why=bad, error=r.get("error"), missing=r["missing"]))
        else:
            k["passed"] += 1
        top = max(r["sequences"] or [0])
        if top > k["max_tokens"]:
            k["max_tokens"], k["max_tokens_exchange"] = top, int(xid)
    return kinds


def render_check(slug, write=True, run=subprocess.run, notes=None, worst=None):
    """Addendum §6.1 (Lr): a CPU-only render, with the server's own code at its pinned commit, of the final
    inference input of stored league requests (the largest included) with no block and with each arm's largest block
    (the guard preflight's: notes 10 games x 5 lessons x 30 words of 12 bytes; worst the 5 largest rendered League
    position blocks). An arm passes when every case with no block and with its block passes (lr_judge). Recorded in
    preflight/render-<slug>.json; no model call."""
    s, route = setups()[slug], lr_routes()[slug]
    rows, retained = stored_requests(s["setup"])
    blocks = dict(none="", notes=notes if notes is not None else synthetic_notes_block(),
                  worst=worst if worst is not None else synthetic_worst_block())
    payload = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in lr_cases(rows, blocks))
    out = run(route["cmd"], input=payload, capture_output=True, text=True, env=dict(os.environ, **route["env"]))
    if out.returncode != 0:
        raise RuntimeError(f"{slug} renderer failed: {out.stderr[-2000:]}")
    kinds = lr_judge([json.loads(x) for x in out.stdout.splitlines() if x.strip()])
    answered = sum(k["cases"] for k in kinds.values())
    if answered != len(rows) * len(blocks):
        raise RuntimeError(f"{slug} renderer answered {answered} of {len(rows) * len(blocks)} cases")
    ok = {k: v["passed"] == v["cases"] for k, v in kinds.items()}
    arms = {arm: ok["none"] and ok[arm] for arm in ARMS}
    rec = dict(at=I.now(), setup=s["setup"], route=route["route"], command=route["cmd"], env=route["env"],
               renderer_sha256=I.sha256_file(route["renderer"]),
               code_sha256={str(p): I.sha256_file(p) for p in route["code"]},
               retained_requests=retained, rendered_requests=len(rows), largest_request_exchange=rows[0][0],
               largest_request_bytes=len(json.dumps(rows[0][1], ensure_ascii=False).encode()),
               block_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in blocks.items() if v},
               kinds=kinds, arms=arms, passed=all(arms.values()))
    if write:
        I.write_atomic(PREFLIGHT() / f"render-{slug}.json", json.dumps(rec, indent=1))
    return rec


# --- Preflight: hosted accounting probe P1 (billed; implemented, run only by an operator) ------------------------

def p1_answer(db_path, name, expect):
    """The input tokens of the one fresh answer of `name` in this attempt's own database: a valid, unfailed answer
    whose reply names a frozen model id and reports usage; else None and why."""
    import sqlite3
    if not Path(db_path).exists():
        return None, "no answer database"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=60)
    try:
        rows = conn.execute("SELECT a.error, x.response FROM answers a JOIN answer_exchanges x ON x.answer_id = a.id "
                            "WHERE a.setup = ?", (name,)).fetchall()
    finally:
        conn.close()
    if len(rows) != 1:
        return None, f"{len(rows)} exchanges for {name}"
    error, response = rows[0]
    if error:
        return None, f"failed: {error[:300]}"
    try:
        value = json.loads(response)
    except (TypeError, ValueError):
        return None, "reply is not JSON"
    if value.get("model") not in expect:
        return None, f"reply names {value.get('model')!r}, not one of {expect}"
    tokens = I.pointer(value, "/usage/input_tokens")
    if not isinstance(tokens, int):
        return None, "no usage.input_tokens"
    return tokens, None


def probe_p1(slug, send=False, run=subprocess.run):
    """Addendum §6.1(b): one stored 2-option League request of the setup, sent without and with the largest notes
    block through the runner (`jevgammon ask`, context gate and route check on). The probe passes the same atomic
    admission as every step (its allocation is the ledger's cap), runs under a fresh attempt id with its own answer
    database, and passes only when both runs exit 0 with one fresh valid answer each, naming a frozen model id, and
    the reported input tokens rise. Billed: refuses unless `send`."""
    import sqlite3
    import uuid
    s = setups()[slug]
    if s.get("evidence") not in ("Hc", "unverified") or s["lane"] != "hosted":
        raise SystemExit(f"{slug}: P1 applies to hosted rows run by the cohort only")
    if not send:
        raise SystemExit(f"{slug}: P1 sends two billed requests; pass --send")
    I.check_inputs()
    check_addendum()
    key = f"decision/{slug}-probe"
    I.ENTRIES[key] = dict(I.ENTRIES[arm_key(slug, "notes")], arm="probe", estimate=0.01)
    attempt = uuid.uuid4().hex[:12]
    d = I.mdir(key) / f"P1-{attempt}"
    d.mkdir(parents=True)
    gate = admit(key, "P1", next_ledger(key, f"P1-{attempt}"), 0.002, want=0.01)  # Refused / AccountingError: no call
    try:
        db = sqlite3.connect(f"file:{I.V3_DB}?mode=ro", uri=True, timeout=60)
        (pid,) = db.execute("SELECT id FROM players WHERE name = ?", (s["setup"],)).fetchone()
        row = db.execute("SELECT t.position, t.die1, t.die2 FROM turns t JOIN games gm ON gm.id = t.game_id JOIN "
                         "matches m ON m.id = gm.match_id WHERE m.valid = 1 AND t.legal_count = 2 AND t.decided_by = "
                         "'model' AND ((m.player1 = ? AND t.player = 1) OR (m.player2 = ? AND t.player = 2)) "
                         "ORDER BY t.id LIMIT 1", (pid, pid)).fetchone()
        db.close()
        (d / "position.jsonl").write_text(json.dumps(dict(id="p1", position=json.loads(row[0]),
                                                          dice=[row[1], row[2]], prompt=I.PROMPT_VERSION)) + "\n")
        ledger = dict(path=Path(gate["ledger"]), cap=gate["cap"])
        out_db = d / "answers.db"
        tokens, why = {}, {}
        for variant, note in (("plain", ""), ("block", synthetic_notes_block())):
            name = f"{s['setup']} | improve | P1 {attempt} | {variant}"
            cfg = dict(I.TEST_CONTEXT, prompt_version=I.PROMPT_VERSION, order_seed=I.ORDER_SEED,
                       players=[dict(player_config(key, name, 1, ledger=ledger),
                                     **({"prompt_note": note} if note else {}))])
            (d / f"{variant}.json").write_text(json.dumps(cfg, indent=1))
            r = run([str(I.BIN), "ask", "--config", str(d / f"{variant}.json"), "--positions",
                     str(d / "position.jsonl"), "--out", str(out_db), "--setup", name], cwd=I.CODE,
                    capture_output=True, text=True)
            (d / f"{variant}.log").write_text((r.stdout or "") + (r.stderr or ""))
            if r.returncode != 0:
                tokens[variant], why[variant] = None, f"runner exit {r.returncode}"
                break
            tokens[variant], why[variant] = p1_answer(out_db, name, s["expect"])
            if tokens[variant] is None:
                break
    finally:
        release(gate)
    passed = all(tokens.get(v) is not None for v in ("plain", "block")) and tokens["block"] > tokens["plain"]
    rec = dict(at=I.now(), setup=s["setup"], attempt=attempt, input_tokens=tokens, failures=why, passed=passed,
               allocation=gate["allocation"], identity_sha256=digest(run_identity(slug)),
               note="accounting evidence only: billing can precede a cut (addendum §6.1)")
    I.write_atomic(d / "p1.json", json.dumps(rec, indent=1))
    I.write_atomic(PREFLIGHT() / f"p1-{slug}.json", json.dumps(rec, indent=1))
    return rec


# --- Summary (aggregates only; the page's decision rows) -------------------------------------------------------

def arm_summary(slug, arm):
    s = setups()[slug]
    key = arm_key(slug, arm)
    pre_state, pre_reason = arm_state(slug, arm)
    row = dict(setup=s["setup"], arm=arm, label=f"{s['setup']} · {ARMS[arm]}", chosen_by=s.get("chosen_by"),
               lane=s["lane"], evidence=s.get("evidence"), delivery_flag=s.get("delivery_flag"),
               page_note=s.get("page_note"), state=pre_state, reason=pre_reason)
    if key in I.ENTRIES and I.mdir(key).exists() and any(e["event"] == "step_start" for e in I.events(key)):
        state, reason = I.model_state(key)
        if state == "stopped" and reason.startswith("incomplete"):
            state = "incomplete"
        row.update(state=state, reason=reason)
        row["empty"] = [{k: json.loads((I.step_dir(key, e) / "aggregate.json").read_text())["test"][k]
                         for k in I.TEST_KEYS} for e in ("E1", "E2", "E3") if I.step_done(key, e)]
        row["series"] = []
        for n in range(1, I.SERIES + 1):
            f = I.step_dir(key, f"S{n}") / "aggregate.json"
            if f.exists():
                a = json.loads(f.read_text())
                row["series"].append(dict(series=n, games=a["games"], wins=a["wins"], writer_calls=a["writer_calls"],
                                          notes_cut=a["notes_cut"], worst_blocks=a["worst_blocks"],
                                          test_positions_excluded=a["test_positions_excluded"],
                                          t10={k: a["t10"][k] for k in I.TEST_KEYS}))
        row["cost"] = dict(booked_usd=round(I.billed(key), 4), estimate_usd=I.entry(key)["estimate"])
    if bound := bound_run(key):  # a started arm is shown with the settings it is bound to, never today's file
        row.update(bound_identity_sha256=bound["identity_sha256"], bound_setup=bound["identity"]["setup"],
                   bound_money=bound["money"], bound_addendum_sha256=bound["addendum_sha256"])
    return row


def summary():
    rows = [arm_summary(s["slug"], arm) for s in cohort()["setups"] for arm in ARMS]
    out = dict(updated_at=I.now(), addendum_sha256=ADDENDUM_SHA256, cohort_sha256=I.sha256_file(COHORT_FILE),
               amendments=cohort().get("amendments", []),
               writer=dict(setup=I.MODELS[WRITER_KEY]["setup"], label="helper-written notes → decision player"),
               decisions={k: v for k, v in cohort()["decisions"].items()}, dry_run=I.DRY, rows=rows)
    I.write_atomic(DECISION_OUT(), json.dumps(out, indent=1))
    return out


def status():
    for s in cohort()["setups"]:
        for arm in ARMS:
            r = arm_summary(s["slug"], arm)
            print(f"{r['label']}: {r['state']}{' (' + r['reason'] + ')' if r['reason'] else ''}")


def arm_state_cli(key):
    """Exit code of `arm-state` (no call): 0 the arm has steps to run (eligible, not finished or stopped), 3 pending
    (a decision or a preflight is missing), 2 nothing to run (complete, stopped, incomplete, not tested, not started).
    Prints the state and reason; run_decision_local.sh starts a server only for an arm that exits 0."""
    slug, arm = split(key)
    r = arm_summary(slug, arm)
    print(f"{r['label']}: {r['state']}{' (' + r['reason'] + ')' if r['reason'] else ''}")
    pre, _ = arm_state(slug, arm)
    if pre == "pending":
        return I.PAUSE
    return 0 if pre == "eligible" and r["state"] not in ("complete", "stopped", "incomplete") else I.STOP


def probe_p1_cli(slug, send, probe=None):
    """Exit code of `probe-p1`: 0 passed, 2 failed or stopped (stop that setup), 3 refused for now (pause: the
    old-share wait, the chat fence, a balance or subcap pause, unreadable accounting); the reason goes to stderr."""
    try:
        rec = (probe or probe_p1)(slug, send)
    except (Refused, AccountingError, I.Pause, I.Stop) as e:
        pause = isinstance(e, (AccountingError, I.Pause)) or (isinstance(e, Refused) and e.pause)
        print(f"{'PAUSED' if pause else 'STOPPED'} P1 {slug}: {e}", file=sys.stderr)
        return I.PAUSE if pause else I.STOP
    print(json.dumps(rec, indent=1))
    if not rec["passed"]:
        print(f"FAILED P1 {slug}: {rec['failures']}", file=sys.stderr)
    return 0 if rec["passed"] else I.STOP


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", required=True, choices=arm_keys())
    r.add_argument("--until", choices=I.STEPS)
    h = sub.add_parser("after-game")
    h.add_argument("--arm", required=True)
    h.add_argument("--series", type=int, required=True)
    p = sub.add_parser("probe-p1", help="billed: the hosted accounting probe of one setup")
    p.add_argument("--setup", required=True)
    p.add_argument("--send", action="store_true")
    st = sub.add_parser("arm-state", help="0 the arm has steps to run, 3 pending, 2 nothing to run (no call)")
    st.add_argument("--arm", required=True, choices=arm_keys())
    sub.add_parser("preflight-guard", help="the conservative guard on retained league requests (no call)")
    lr = sub.add_parser("preflight-render", help="the local render check Lr of one local setup (no call, no GPU)")
    lr.add_argument("--setup", required=True, choices=sorted(lr_routes()))
    sub.add_parser("status")
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "after-game":
        after_game(a.arm, a.series)
    elif a.cmd == "probe-p1":
        sys.exit(probe_p1_cli(a.setup, a.send))
    elif a.cmd == "preflight-guard":
        out = guard_preflight()
        print(f"added bytes: {out['added_bytes']}")
        for slug, x in out["setups"].items():
            print(f"{x['setup']}: {x['requests']} requests, max {x['max_bytes']} B, limit {x['limit_tokens']}; "
                  f"refused none {x['refused']['none']}, notes {x['refused']['notes']}, worst {x['refused']['worst']}")
    elif a.cmd == "preflight-render":
        rec = render_check(a.setup)
        for kind, k in rec["kinds"].items():
            print(f"{rec['setup']} {kind}: {k['passed']}/{k['cases']} passed, max {k['max_tokens']} tokens "
                  f"(exchange {k['max_tokens_exchange']}), limits {k['limits']}; refused {k['refused']}, cut "
                  f"{k['cut']}, missing {k['missing']}, round trip failed {k['roundtrip_failed']}")
        print(f"arms: {rec['arms']}")
    elif a.cmd == "status":
        status()
    elif a.cmd == "arm-state":
        sys.exit(arm_state_cli(a.arm))
    elif a.cmd == "summary":
        summary()
    else:
        sys.exit(run(a.arm, a.until))


if __name__ == "__main__":
    main()
