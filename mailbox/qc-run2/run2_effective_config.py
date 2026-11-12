"""QC 2026-11-12, Zeki #5362 items 3/4: the frozen effective config of every Run 2 step as the runner received it
(read-only). For MODEL in the Run 2 root: each step's test config (test-*.json), game player (player.json) and lesson
player (lesson-player.json), with the file's sha256 and its route fields (spec, provider, reasoning, request,
max_tokens, expect_route, parallel). A prompt note in a test config is replaced by its sha256 (no lesson text).
Also, when the Run 2 process is alive, the IMPROVE_RUN2* environment of `improve.py run` (/proc/PID/environ),
which every after-game hook and lesson call inherits.
Usage: python3 run2_effective_config.py MODEL"""
import hashlib, json, os, sys
from pathlib import Path

key = sys.argv[1]
ROOT = Path("/home/cbasaran/code/jevgammon/smoke/improve-run2/runs") / key
FIELDS = ("name", "spec", "provider", "reasoning", "request", "max_tokens", "temperature", "expect_route", "parallel",
          "quota_pause", "letter_readout", "base_url")


def view(p):
    v = {k: p.get(k) for k in FIELDS if k in p}
    if "prompt_note" in p:
        v["prompt_note_sha256"] = hashlib.sha256(p["prompt_note"].encode()).hexdigest()
    if "prompt_note_file" in p:
        v["prompt_note_file"] = Path(p["prompt_note_file"]).name
    if "budget" in p:
        v["budget_cap_usd"] = p["budget"].get("cap_usd")
    return v


out = dict(model=key, root=str(ROOT), steps={})
for d in sorted(x for x in ROOT.iterdir() if x.is_dir()):
    files = {}
    for f in sorted(d.glob("test-*.json")) + [d / "player.json", d / "lesson-player.json"]:
        if not f.exists():
            continue
        c = json.loads(f.read_text())
        players = c.get("players", [c])
        files[f.name] = dict(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                             rules={k: c[k] for k in ("rounds", "max_turns", "clock", "prompt_version", "order_seed") if k in c},
                             players=[view(p) for p in players])
    out["steps"][d.name] = files
procs = []
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        if b"run" in cmd and key.encode() in cmd and any(x.endswith(b"improve.py") for x in cmd):
            env = dict(x.split("=", 1) for x in Path(f"/proc/{pid}/environ").read_bytes().decode().split("\0") if "=" in x)
            procs.append(dict(pid=int(pid), cmdline=[x.decode() for x in cmd if x],
                              env={k: v for k, v in env.items() if k.startswith("IMPROVE_")}))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
out["live_process_env"] = procs
print(json.dumps(out, indent=1))
