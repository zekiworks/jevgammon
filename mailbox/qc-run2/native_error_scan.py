"""QC 2026-11-12, Zeki #5362 item 5: stored replies whose only provider-error marker is
choices[0].native_finish_reason == "error" (the 018138f detector checks top-level `error`, choices[0].error and
choices[0].finish_reason == "error", not native_finish_reason). Read-only; counts only, per source.
Sources: the league database (v3.db exchanges), the learning lanes (smoke/improve/*.db answer_exchanges and
exchanges, lesson call files under workspace/improve/runs), and the Run 2 databases (smoke/improve-run2/db/*.db,
workspace/late-ember/run2/*.db, Run 2 lesson call files).
Usage: python3 native_error_scan.py"""
import glob, json, sqlite3
from pathlib import Path

ROOT = Path("/home/cbasaran/code/jevgammon")


def classify(raw, c):
    c["replies"] += 1
    try:
        v = json.loads(raw)
    except (TypeError, ValueError):
        c["not_json"] += 1
        return
    if not isinstance(v, dict):
        c["not_object"] += 1
        return
    ch = v.get("choices")
    ch = ch[0] if isinstance(ch, list) and ch and isinstance(ch[0], dict) else {}
    present = lambda x: x is not None and x != "" and x is not False  # noqa: E731
    caught = present(v.get("error")) or present(ch.get("error")) or ch.get("finish_reason") == "error"
    native = ch.get("native_finish_reason") == "error"
    c["caught_by_018138f"] += caught
    c["native_finish_reason_error"] += native
    c["native_error_only"] += native and not caught


def scan_db(path, tables):
    c = dict(replies=0, not_json=0, not_object=0, caught_by_018138f=0, native_finish_reason_error=0, native_error_only=0)
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    for t in tables:
        if t in have:
            for (raw,) in db.execute(f"SELECT response FROM {t} WHERE response IS NOT NULL"):
                classify(raw, c)
    db.close()
    return c


def scan_calls(pattern):
    c = dict(replies=0, not_json=0, not_object=0, caught_by_018138f=0, native_finish_reason_error=0, native_error_only=0)
    for f in glob.glob(pattern, recursive=True):
        for x in json.loads(Path(f).read_text()).get("exchanges", []):
            if x.get("response") is not None:
                classify(x["response"], c)
    return c


out = {"league v3.db exchanges": scan_db(ROOT / "v3.db", ["exchanges"])}
for p in sorted(glob.glob(str(ROOT / "smoke/improve/*.db"))):
    if not p.endswith("-plays.db"):
        out[f"learning {Path(p).name}"] = scan_db(p, ["answer_exchanges", "exchanges"])
out["learning lesson calls (incl. archived attempts)"] = scan_calls(str(ROOT / "workspace/improve/runs/**/lessons-g*.call.json"))
for p in sorted(glob.glob(str(ROOT / "smoke/improve-run2/db/*.db"))) + sorted(glob.glob(str(ROOT / "workspace/late-ember/run2/*.db"))):
    if not p.endswith("-plays.db"):
        out[f"run2 {Path(p).name}"] = scan_db(p, ["answer_exchanges", "exchanges"])
out["run2 lesson calls"] = scan_calls(str(ROOT / "smoke/improve-run2/runs/**/lessons-g*.call.json"))
tot = {}
for v in out.values():
    for k, n in v.items():
        tot[k] = tot.get(k, 0) + n
out["TOTAL"] = tot
print(json.dumps(out, indent=1))
