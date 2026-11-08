"""Run manifest (smoke manifest of Zeki #2841, extended to the whole run with --series 1-10): counts, hashes, times and token sizes only. No outcome numbers (no error rate, risks
found, right safety, risk judgement, risk appetite, lift), no positions, no contexts, no lesson text.
Read-only over the pilot's files and smoke/learning-pilot.db; writes mailbox/learning-pilot-smoke-manifest/.

    /home/cbasaran/.pyenv/versions/3.12.13/bin/python3 workspace/learning-pilot/smoke_manifest.py
"""

import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = HERE / "runs"
DB = ROOT / "smoke/learning-pilot.db"
import sys
ARG = sys.argv[1] if len(sys.argv) > 1 else "1-3"
OUT = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "mailbox/learning-pilot-smoke-manifest")
BRANCH = ROOT.parent / "jevgammon-learning-pilot"
ARMS = ["control", "records", "lessons", "budget"]
SERIES = list(range(int(ARG.split("-")[0]), int(ARG.split("-")[1]) + 1))
PLAN = ROOT / "mailbox/Learning pilot - plan 2026-11-07.md"


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def git_blob_sha256(commit, path):
    r = subprocess.run(["git", "-C", str(BRANCH), "show", f"{commit}:{path}"], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def dice_comparison(db, old_id: int, new_id: int) -> dict:
    """The stored dice of an aborted match and its replacement, compared: the match seed (matches.seed), each common
    game's dice seed and opening roll (games), and each common game's roll sequence (turns.die1/die2 in turn order) over
    the turns both games played. The rolls come from the dice seed alone, so equal seeds give equal rolls turn by turn;
    the games can differ in length because the plays differ (temperature 1)."""
    seed = {m: db.execute("SELECT seed FROM matches WHERE id = ?", (m,)).fetchone()[0] for m in (old_id, new_id)}
    games = {m: {(r[0], r[1]): r[2:] for r in db.execute(
        "SELECT round_no, leg, id, dice_seed, opening_white, opening_black FROM games WHERE match_id = ?", (m,))}
        for m in (old_id, new_id)}
    per_game = []
    for key in sorted(set(games[old_id]) & set(games[new_id])):
        (gid_a, ds_a, ow_a, ob_a), (gid_b, ds_b, ow_b, ob_b) = games[old_id][key], games[new_id][key]
        rolls = {g: [(r[0], r[1]) for r in db.execute(
            "SELECT die1, die2 FROM turns WHERE game_id = ? ORDER BY turn_no", (g,))] for g in (gid_a, gid_b)}
        n = min(len(rolls[gid_a]), len(rolls[gid_b]))
        seq_a, seq_b = rolls[gid_a][:n], rolls[gid_b][:n]
        per_game.append(dict(
            round=key[0], leg=key[1], aborted_game_id=gid_a, replacement_game_id=gid_b,
            aborted_dice_seed=ds_a, replacement_dice_seed=ds_b, dice_seed_equal=ds_a == ds_b,
            aborted_opening=[ow_a, ob_a], replacement_opening=[ow_b, ob_b], opening_equal=(ow_a, ob_a) == (ow_b, ob_b),
            aborted_turns=len(rolls[gid_a]), replacement_turns=len(rolls[gid_b]), compared_turns=n,
            rolls_sha256_aborted=hashlib.sha256(json.dumps(seq_a).encode()).hexdigest(),
            rolls_sha256_replacement=hashlib.sha256(json.dumps(seq_b).encode()).hexdigest(),
            rolls_equal_over_compared_turns=seq_a == seq_b,
            first_unequal_turn=next((i + 1 for i in range(n) if seq_a[i] != seq_b[i]), None)))
    return dict(aborted_match_seed=seed[old_id], replacement_match_seed=seed[new_id],
                match_seed_equal=seed[old_id] == seed[new_id], games_compared=per_game,
                same_dice=seed[old_id] == seed[new_id] and bool(per_game)
                and all(g["dice_seed_equal"] and g["opening_equal"] and g["rolls_equal_over_compared_turns"]
                        for g in per_game))


def events(path: Path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    pilot_now = sha(HERE / "pilot.py")
    harness = {c: git_blob_sha256(c, "workspace/learning-pilot/pilot.py") for c in ("ba8b011", "e18ff59")}
    out = dict(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        note="Counts, hashes, times and token sizes only; no outcome numbers.",
        hashes=dict(plan_sha256=sha(PLAN), lesson_prompt_sha256=hashlib.sha256(
            (HERE / "lessons_system.txt").read_bytes() + (HERE / "lessons_user.txt").read_bytes()).hexdigest(),
            test_set_sha256=sha(HERE / "test_set.json"), test_positions_sha256=sha(HERE / "test_positions.jsonl"),
            base_config_sha256=sha(HERE / "configs/base.json"),
            pilot_py_sha256_by_commit=harness, pilot_py_sha256_now=pilot_now,
            runner_binary_sha256=sha(BRANCH / "target/release/jevgammon")),
        harness=dict(first_start="ba8b011 (pilot.py as committed there), 2026-11-07T17:57:04Z: T0 and control s1-s3",
                     restart="e18ff59, 2026-11-07T18:20:13Z: records s1-s3, lessons s1-s3, budget s1-s3",
                     series_4_10="e18ff59, 2026-11-07T22:31:14Z to 2026-11-08T07:28:06Z: all arms s4-s10 "
                                 "(systemd unit learning-pilot-main, run_main.sh)",
                     differences_ba8b011_to_e18ff59="restart bookkeeping (attempt-N archive, stale failure markers "
                                                     "cleared) and a tokenizer check before any game; prompt, "
                                                     "scoring, arms and evaluation set unchanged"),
    )
    t0 = json.loads((RUNS / "t0/aggregate.json").read_text())
    t0_rows = db.execute("SELECT COUNT(*), SUM(error IS NOT NULL), SUM(invalid), MIN(created_at), MAX(created_at) "
                         "FROM answers WHERE setup = 'Gemma 4 31B (off) | T0 shared'").fetchone()
    out["t0"] = dict(answers=t0_rows[0], failed=t0_rows[1], invalid=t0_rows[2], first_answer_at=t0_rows[3],
                     last_answer_at=t0_rows[4], wall_seconds=t0["wall_seconds"],
                     test_set_sha256=t0.get("test_set_sha256"), aggregate_sha256=sha(RUNS / "t0/aggregate.json"))
    series = []
    for arm in ARMS:
        for s in SERIES:
            d = RUNS / arm / f"s{s:02d}"
            a = json.loads((d / "aggregate.json").read_text())
            ev = events(d / "log.jsonl")
            name = f"Gemma 4 31B (off) | {arm} | s{s:02d}"
            matches = [dict(r) for r in db.execute(
                "SELECT id, status, started_at, finished_at, seed, rounds_planned, rounds_played FROM matches "
                "WHERE model1 = ? ORDER BY id", (name,))]
            games = [dict(game=2 * (r["round_no"] - 1) + r["leg"], game_id=r["id"], turns=r["turns"],
                          started_at=r["started_at"], finished_at=r["finished_at"])
                     for r in db.execute("SELECT id, round_no, leg, turns, started_at, finished_at FROM games "
                                         "WHERE match_id = ? ORDER BY round_no, leg", (matches[-1]["id"],))]
            evals = {}
            for cp in ("T5", "T10"):
                r = db.execute("SELECT COUNT(*), SUM(error IS NOT NULL), SUM(invalid), MIN(created_at), "
                               "MAX(created_at) FROM answers WHERE setup = ?", (f"{name} | {cp}",)).fetchone()
                if r[0]:
                    evals[cp] = dict(answers=r[0], failed=r[1], invalid=r[2], first_answer_at=r[3], last_answer_at=r[4])
            starts = [e["at"] for e in ev if e["event"] == "series_start"]
            series.append(dict(
                arm=arm, series=s, dice_seed=a["seed"], match_id=matches[-1]["id"], match_status=matches[-1]["status"],
                started_at=starts[-1] if starts else None, finished_at=a["finished_at"], wall_seconds=a["wall_seconds"],
                games=[g["game"] for g in games], game_rows=games, decisions_per_game=[g["decisions"] for g in a["games"]],
                invalid_decisions=sum(g["invalid"] for g in a["games"]),
                unscored_decisions=sum(g["unscored"] for g in a["games"]),
                evaluations=evals, lessons_files=a.get("lessons_files", {}),
                lessons_calls=len(a.get("lessons_calls", [])),
                lessons_cut=sum(1 for c in a.get("lessons_calls", []) if c.get("cut")),
                context_tokens_after_game=a["context_tokens_after_game"],
                records_dropped_after_game=a["records_dropped_after_game"],
                budget_points=a.get("budget_points", []),
                evaluation_positions_excluded=a["evaluation_positions_excluded"], restarts=a["restarts"],
                test_set_sha256=a.get("test_set_sha256"), lesson_prompt_sha256=a.get("lesson_prompt_sha256"),
                aggregate_sha256=sha(d / "aggregate.json"), log_sha256=sha(d / "log.jsonl"),
                match_log_sha256=sha(d / "match.log")))
    out["series"] = series
    # Failed first attempt -> replay.
    replays = []
    for arm in ARMS:
        for s in SERIES:
            d = RUNS / arm / f"s{s:02d}"
            for e in events(d / "log.jsonl"):
                if e["event"] == "series_restarted":
                    old = d / e["attempt_archive"]
                    old_match = db.execute("SELECT id, status, started_at, error FROM matches WHERE id = ?",
                                           (e["old_match"],)).fetchone()
                    old_games = db.execute("SELECT COUNT(*), SUM(finished_at IS NOT NULL) FROM games WHERE match_id = ?",
                                           (e["old_match"],)).fetchone()
                    new = next(x for x in series if x["arm"] == arm and x["series"] == s)
                    replays.append(dict(
                        arm=arm, series=s, restarted_at=e["at"], aborted_match_id=e["old_match"],
                        aborted_match_status=old_match["status"], aborted_match_started_at=old_match["started_at"],
                        aborted_match_games_started=old_games[0], aborted_match_games_finished=old_games[1],
                        aborted_match_error=(old_match["error"] or "")[:300],
                        replacement_match_id=new["match_id"], **dice_comparison(db, e["old_match"], new["match_id"]),
                        archive_path=str(old.relative_to(ROOT)),
                        archive_files={str(p.relative_to(old)): sha(p) for p in sorted(old.rglob("*")) if p.is_file()},
                        failure_reason=(e.get("reason") or "")[-300:]))
    out["replays"] = replays
    # Records-arm context-limit events: drop-oldest-whole-game.
    drops = []
    for s in SERIES:
        d = RUNS / "records" / f"s{s:02d}"
        ev = events(d / "log.jsonl")
        ctx = {e["after_game"]: e for e in ev if e["event"] == "context"}
        by_game = {}
        for e in ev:
            if e["event"] == "context_drop":
                by_game.setdefault(e["after_game"], []).append(e)
        for g, ds in sorted(by_game.items()):
            final = ctx[g]
            drops.append(dict(
                series=s, after_game=g, budget_tokens=ds[0]["budget"],
                steps=[dict(tokens_before_drop=x["tokens"], dropped_whole_game=x["dropped_game"]) for x in ds],
                games_shown_after=final.get("games_shown"), tokens_after=final["tokens"],
                rule="the oldest whole game is dropped while the context exceeds the budget; nothing is trimmed, "
                     "skipped or refused"))
    out["records_context_limit_events"] = drops
    out["records_context_limit_event_count"] = sum(len(x["steps"]) for x in drops)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(series=len(series), replays=len(replays), drop_points=len(drops),
                          drop_steps=out["records_context_limit_event_count"])))


main()
