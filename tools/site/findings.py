"""Published findings and their machine checks (brief v12 B4, B1).

Findings go up only after Ümit approves them. Each one is stored in content/findings.json with a check of its claim,
read from the site's own data files (OUT/data/...), so the check sees exactly what the site publishes. The one-line
lead-in above the bullets is itself a finding ("lead_in" in findings.json, checked and approved the same way):

    {"id": "risk-1", "tab": "risk", "label": "Risk judgement", "text": "...",
     "check": {"type": "lower", "data": "v3/league-3.json",
               "a": ["setups", "X", "quality"], "b": ["setups", "Y", "quality"]}}

Check types:
    bound   {"data", "path", "below"?, "above"?}       the value at path is below / above the bound
    lower   {"data", "a", "b"}                          a's 95% interval (error_lo, error_hi) lies entirely below b's;
                                                        for league data, an unpaired comparison ("lower error rate in
                                                        league play")
    higher_judgement {"data", "a", "b"}                 a's risk judgement interval (judgement_lo, judgement_hi) lies
                                                        entirely above b's (unpaired in league play)
    paired  {"data", "path", "sign": "negative"|"positive"}
                                                        a paired difference {diff, lo, hi} whose 95% interval excludes
                                                        zero on that side
    no_leader {"data", "measures": [[path, "high"|"low"], ...]}
                                                        "None led on every measure": the setup with the best value
                                                        differs between at least two of the measures

Before every deploy, checks.py reruns every check (evaluate); a finding that no longer holds stops the deploy, and
update.sh writes which one failed and what the data now shows to mailbox/.
"""

import json
from pathlib import Path

from common import CONTENT


def _store() -> dict:
    path = CONTENT / "findings.json"
    return json.loads(path.read_text()) if path.exists() else {}


def published() -> list[dict]:
    return _store().get("findings", [])


def lead_in() -> dict | None:
    return _store().get("lead_in")


def _get(out: Path, rel: str, path: list):
    v = json.loads((out / "data" / rel).read_text())
    for k in path:
        v = v[k]
    return v


def evaluate(out: Path, f: dict) -> tuple[bool, str]:
    """(holds, what the data now shows)."""
    c = f["check"]
    try:
        if c["type"] == "bound":
            v = _get(out, c["data"], c["path"])
            ok = (c.get("below") is None or v < c["below"]) and (c.get("above") is None or v > c["above"])
            return ok, f"{'/'.join(map(str, c['path']))} = {v!r} in data/{c['data']}"
        if c["type"] == "lower":
            a, b = _get(out, c["data"], c["a"]), _get(out, c["data"], c["b"])
            ok = None not in (a.get("error_hi"), b.get("error_lo")) and a["error_hi"] < b["error_lo"]
            return ok, (f"{c['a'][-2]}: {a.get('error_rate')} [{a.get('error_lo')}, {a.get('error_hi')}]; "
                        f"{c['b'][-2]}: {b.get('error_rate')} [{b.get('error_lo')}, {b.get('error_hi')}] in data/{c['data']}")
        if c["type"] == "paired":
            p = _get(out, c["data"], c["path"])
            ok = p["hi"] < 0 if c["sign"] == "negative" else p["lo"] > 0
            return ok, f"difference {p['diff']} [{p['lo']}, {p['hi']}] in data/{c['data']}"
        if c["type"] == "higher_judgement":
            a, b = _get(out, c["data"], c["a"]), _get(out, c["data"], c["b"])
            ok = None not in (a.get("judgement_lo"), b.get("judgement_hi")) and a["judgement_lo"] > b["judgement_hi"]
            return ok, (f"{a.get('judgement')} [{a.get('judgement_lo')}, {a.get('judgement_hi')}] vs "
                        f"{b.get('judgement')} [{b.get('judgement_lo')}, {b.get('judgement_hi')}] in data/{c['data']}")
        if c["type"] == "no_leader":
            setups = _get(out, c["data"], ["setups"])
            leaders = []
            for path, way in c["measures"]:
                vals = {}
                for n, s in setups.items():
                    v = s
                    for k in path:
                        v = v.get(k) if isinstance(v, dict) else None
                    if isinstance(v, (int, float)):
                        vals[n] = v
                leaders.append((max if way == "high" else min)(vals, key=vals.get))
            return len(set(leaders)) > 1, f"leaders per measure: {leaders} in data/{c['data']}"
        return False, f"unknown check type {c['type']!r}"
    except (KeyError, FileNotFoundError, TypeError, IndexError, ValueError) as e:
        return False, f"the value the finding rests on is missing ({e!r})"


def failures(out: Path) -> list[str]:
    bad = []
    items = published() + ([lead_in()] if lead_in() else [])
    for f in items:
        ok, now = evaluate(out, f)
        if not ok:
            bad.append(f"Finding {f['id']} no longer holds: \"{f['text']}\". The data now shows: {now}.")
    return bad
