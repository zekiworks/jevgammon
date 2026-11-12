"""QC 2026-11-12: the step-boundary binary switches actually logged in the learning lanes' run logs (read-only).
Per model with a binary_switch event: the last step started on the old build (with its step_done), any step that
started on the old build and paused before a request, the binary_switch event itself, and the first step started on
the new build. Prints JSON lines (no prompt or answer text: events carry steps, times, binaries and hashes only).
Usage: python3 boundary_events.py > step-boundary-events.jsonl"""
import json
from pathlib import Path

RUNS = Path("/home/cbasaran/code/jevgammon/workspace/improve/runs")
for log in sorted(RUNS.glob("*/log.jsonl")):
    model = log.parent.name
    ev = [json.loads(x) for x in log.read_text().splitlines()]
    sw = [i for i, e in enumerate(ev) if e["event"] == "binary_switch"]
    for i in sw:
        s = ev[i]
        old = Path(s["from"]).name.split("-", 1)[1]
        new = Path(s["to"]).name.split("-", 1)[1]
        starts = [(j, e) for j, e in enumerate(ev) if e["event"] == "step_start"]
        before = [(j, e) for j, e in starts if j < i and (e.get("binary") or {}).get("commit") == old]
        after = [(j, e) for j, e in starts if j > i and (e.get("binary") or {}).get("commit") == new]
        done = {e["step"]: e["at"] for e in ev if e["event"] == "step_done"}
        last_done_old = [e for j, e in before if e["step"] in done and done[e["step"]] <= s["at"]]
        paused_old = [e for j, e in before if e["step"] not in done or done[e["step"]] > s["at"]]

        def row(kind, e, **kw):
            b = e.get("binary") or {}
            return dict(model=model, kind=kind, at=e["at"], event=e["event"], step=e.get("step"),
                        binary_commit=b.get("commit"), binary_sha256=b.get("sha256"), **kw)

        if last_done_old:
            e = last_done_old[-1]
            print(json.dumps(row("last step on the old build", e, step_done_at=done[e["step"]])))
        for e in paused_old:
            pauses = [p for p in ev if p["event"] == "paused" and p["at"] >= e["at"] and p["at"] <= s["at"]]
            print(json.dumps(row("started on the old build, paused by the switch hold before any request", e,
                                 paused_at=pauses[-1]["at"] if pauses else None)))
        print(json.dumps(dict(model=model, kind="binary_switch", **s)))
        if after:
            print(json.dumps(row("first step on the new build", after[0][1])))
