"""Offline check (no model call): the test positions' play prompts, rendered by the pilot harness from
test_positions.jsonl, equal the user text the league sent for the original decision (any setup's stored
exchange: the user text does not depend on the setup). Single-request positions (<= 26 options) only;
render-stage-b refuses group-split ones."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BIN = ROOT.parent / "jevgammon-learning-pilot/target/release/jevgammon"


def user_text(request: dict):
    """The longest string in the request that holds the game prompt."""
    best = None

    def walk(v):
        nonlocal best
        if isinstance(v, str):
            if "You are playing a backgammon game" in v and (best is None or len(v) > len(best)):
                best = v
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(request)
    return best


def main():
    rows = [json.loads(l) for l in (HERE / "test_positions.jsonl").read_text().splitlines()]
    single = [r for r in rows if len(r["legal_plays"]) <= 26]
    tmp = HERE / "render_input.jsonl"
    tmp.write_text("".join(json.dumps(r) + "\n" for r in single))
    out = subprocess.run([str(BIN), "render-stage-b", "--config", str(HERE / "configs/base.json"),
                          "--positions", str(tmp)], capture_output=True, text=True, check=True).stdout
    rendered = {json.loads(l)["position_id"]: json.loads(l)["play"]["user"] for l in out.splitlines()}
    v3 = sqlite3.connect(f"file:{ROOT / 'v3.db'}?mode=ro", uri=True)
    same = state_same = differ = missing = 0
    for r in single:
        tid = int(r["id"].split("-")[1])
        req = v3.execute("SELECT request FROM exchanges WHERE turn_id = ? ORDER BY attempt LIMIT 1", (tid,)).fetchone()
        stored = user_text(json.loads(req[0])) if req else None
        if stored is None:
            missing += 1
        elif stored == rendered[r["id"]]:
            same += 1
        elif rendered[r["id"]].startswith(stored.rstrip()):
            # A decision service's request: the state is sent apart from the options and the question.
            state_same += 1
        else:
            differ += 1
            print("differs:", r["id"], file=sys.stderr)
    tmp.unlink()
    print(json.dumps(dict(single_request=len(single), same=same, state_same_service_request=state_same,
                          differ=differ, no_stored_exchange=missing)))


main()
