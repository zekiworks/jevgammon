#!/usr/bin/env python3
"""Probability support audit (Method specification 2026-10-24, section 1): which league decisions have verifiably
complete option probabilities.

    python3 tools/site/prob_audit.py V3_DB SNAP_DB [OUT]

Reads the raw exchanges of V3_DB read-only (mode=ro) and the turns of the site snapshot SNAP_DB; writes OUT
(default tools/site/content/probability_audit.json.gz): {"statuses": {turn id: status}, "counts": {...}} for every
model decision (decided_by model or fallback). Statuses, in order of precedence: invalid, no_probabilities, grouped,
no_raw, unverified, sparse, complete. A record is complete only when the response that reproduces the stored
probability vector gives an explicit probability for every legal option: every candidate notation for a decision
service, every option letter among the answer token's top log-probabilities for a letter readout (a letter missing
there was zero-filled by the runner and renormalised).
"""

import gzip
import json
import math
import sqlite3
import sys
from collections import Counter
from pathlib import Path

TOL = 1e-9
OPEN = "([{'\""
CLOSE = ".,:)]}'\""


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def letter_index(token: str, count: int):
    """The option index a top-logprob token stands for, as the runner reads it (prompt.rs letter_probabilities):
    any mix of whitespace and opening marks trimmed from the start, whitespace and closing marks from the end."""
    core = token
    while core and (core[0].isspace() or core[0] in OPEN):
        core = core[1:]
    while core and (core[-1].isspace() or core[-1] in CLOSE):
        core = core[:-1]
    b = core.encode()
    if len(b) != 1 or not chr(b[0]).isascii() or not chr(b[0]).isalpha():
        return None
    k = ord(chr(b[0]).upper()) - ord("A")
    return k if k < count else None


def letter_vector(top: list, count: int):
    """(normalised vector, set of letters present) as the runner computes it; None when no letter appears."""
    mass = [0.0] * count
    seen = set()
    for alt in top:
        tok, lp = alt.get("token"), alt.get("logprob")
        if not isinstance(tok, str) or not isinstance(lp, (int, float)):
            continue
        k = letter_index(tok, count)
        if k is None:
            continue
        mass[k] += math.exp(lp)
        seen.add(k)
    total = sum(mass)
    if not seen or total <= 0:
        return None
    return [m / total for m in mass], seen


def tops(node):
    """Every top_logprobs list in a parsed response."""
    if isinstance(node, dict):
        t = node.get("top_logprobs")
        if isinstance(t, list):
            yield t
        for v in node.values():
            yield from tops(v)
    elif isinstance(node, list):
        for v in node:
            yield from tops(v)


def same(a, b) -> bool:
    return len(a) == len(b) and all(x is not None and y is not None and abs(x - y) <= TOL for x, y in zip(a, b))


def audit_letters(responses, stored):
    count = len(stored)
    reproduced = False
    for resp in responses:
        for top in tops(resp):
            got = letter_vector(top, count)
            if got and same(got[0], stored):
                reproduced = True
                if len(got[1]) == count:
                    return "complete"
    return "sparse" if reproduced else "unverified"


def candidates(request: dict):
    q = request.get("questions")
    if isinstance(q, dict) and isinstance(q.get("play"), dict):
        return list((q["play"].get("criteria") or {}).keys())
    if isinstance(q, list):
        for item in q:
            if item.get("name") == "play":
                return [c.get("value") for c in item.get("choices") or []]
    return None


def answer_probabilities(resp: dict):
    ans = resp.get("answers")
    if isinstance(ans, dict):
        ans = ans.get("play")
    elif isinstance(ans, list):
        ans = next((a for a in ans if a.get("name") == "play"), None)
    if not isinstance(ans, dict):
        return None
    pr = ans.get("probabilities")
    if isinstance(pr, list):
        out = {}
        for p in pr:
            if isinstance(p, dict) and isinstance(p.get("value"), str) and isinstance(p.get("probability"), (int, float)):
                out.setdefault(p["value"], p["probability"])
        return out
    if isinstance(pr, dict):
        return {k: v for k, v in pr.items() if isinstance(v, (int, float))}
    return None


def audit_decision(exchanges, stored):
    reproduced = False
    for req, resp in exchanges:
        names = candidates(req)
        probs = answer_probabilities(resp)
        if not names or probs is None or len(names) != len(stored):
            continue
        vec = [probs.get(n) for n in names]
        if not same(vec, stored):
            continue
        reproduced = True
        if all(v is not None and math.isfinite(v) and v >= 0 for v in vec) and len(set(names)) == len(names):
            return "complete"
    return "sparse" if reproduced else "unverified"


def main():
    v3, snap = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).resolve().parent / "content/probability_audit.json.gz"
    sdb, vdb = ro(snap), ro(v3)
    statuses = {}
    todo = []
    for tid, decided_by, source, probs, group in sdb.execute(
            "SELECT id, decided_by, probability_source, probabilities, group_size FROM turns "
            "WHERE decided_by IN ('model', 'fallback')"):
        if decided_by == "fallback":
            statuses[tid] = "invalid"
        elif source not in ("decision", "logprobs") or not probs:
            statuses[tid] = "no_probabilities"
        elif group:
            statuses[tid] = "grouped"
        else:
            todo.append((tid, source, json.loads(probs)))
    # One pass over the exchanges (no index on turn_id): each response is judged on its own; a turn is complete when any
    # of its responses is, sparse when one reproduces the stored vector without full support, unverified otherwise.
    want = {tid: (source, stored) for tid, source, stored in todo}
    rank = {"unverified": 1, "sparse": 2, "complete": 3}
    best = {}
    for tid, req, resp in vdb.execute("SELECT turn_id, request, response FROM exchanges WHERE response IS NOT NULL"):
        if tid not in want or best.get(tid) == "complete":
            continue
        try:
            req, resp = json.loads(req), json.loads(resp)
        except (TypeError, ValueError):
            continue
        source, stored = want[tid]
        s = audit_decision([(req, resp)], stored) if source == "decision" else audit_letters([resp], stored)
        if rank[s] > rank.get(best.get(tid), 0):
            best[tid] = s
    for tid in want:
        statuses[tid] = best.get(tid, "no_raw")
    counts = Counter(statuses.values())
    doc = {"about": "Probability support audit, Method specification 2026-10-24 section 1 (tools/site/prob_audit.py).",
           "counts": dict(sorted(counts.items())), "statuses": {str(k): v for k, v in sorted(statuses.items())}}
    out.write_bytes(gzip.compress(json.dumps(doc, separators=(",", ":")).encode(), compresslevel=9, mtime=0))
    print(json.dumps(doc["counts"]))


if __name__ == "__main__":
    main()
