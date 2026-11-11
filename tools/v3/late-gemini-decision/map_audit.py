#!/usr/bin/env python3
"""Offline audit of every stored Gemini Decision 1 answer under the runner's map-check v2 (src/players/decision.rs
map_fault; Zeki #4985): a probability map is usable only when it has exactly one entry per shown id (none missing,
unknown or repeated), every value a finite number in [0, 1], and the values sum to 1 within 1e-6 (no frozen sum
tolerance existed; 1e-6 chosen 11 Nov for Gemini Decision 1 only). Reads the raw response text stored in
exchanges.response (the HTTP body as received) with every JSON object kept as its key/value pairs, so a repeated key
shows (a plain dict keeps only the last), and as strict JSON: a bare NaN/Infinity token makes the response unreadable,
as the runner's serde_json does (an invalid answer there). Read-only on v3.db; metadata only (counts, ids of failing
exchanges, max |sum - 1|), never a probability is changed.

    map_audit.py [V3_DB]          audit (default: the main checkout's v3.db)
    map_audit.py --controls       run the predicate on hand-made bad maps (each must be rejected) and a valid one,
                                  and the raw-text reader on a repeated key and a NaN token
"""
import json
import math
import sqlite3
import sys

NAME = "Gemini Decision 1"
SUM_TOLERANCE = 1e-6
KINDS = ("missing", "unknown", "repeated", "not a number", "not finite", "below 0", "above 1", "sum")


def faults(entries, shown) -> set[str]:
    """entries: [(id, value)] as sent (repeats kept); shown: the request's ids. The causes that fail the map."""
    ids = [i for i, _ in entries]
    out = set()
    if any(s not in ids for s in shown):
        out.add("missing")
    if any(i not in shown for i in ids):
        out.add("unknown")
    if any(ids.count(s) > 1 for s in shown):
        out.add("repeated")
    nums = [v for _, v in entries if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(nums) < len(entries):
        out.add("not a number")
    if any(not math.isfinite(v) for v in nums):
        out.add("not finite")
    if any(v < 0 for v in nums if math.isfinite(v)):
        out.add("below 0")
    if any(v > 1 for v in nums if math.isfinite(v)):
        out.add("above 1")
    if len(nums) == len(entries) and all(math.isfinite(v) for v in nums) and abs(sum(nums) - 1) > SUM_TOLERANCE:
        out.add("sum")
    return out


class Pairs(dict):
    """A JSON object as parsed (last value per key, for lookups) with every key/value pair as sent in `pairs`."""

    def __init__(self, pairs):
        super().__init__(pairs)
        self.pairs = pairs


def strict(token):
    raise ValueError(f"non-standard JSON token {token}")


def parse(text: str):
    return json.loads(text, object_pairs_hook=Pairs, parse_constant=strict)


def entries_of(probabilities):
    if isinstance(probabilities, list):
        return [(p.get("value"), p.get("probability")) for p in probabilities]
    if isinstance(probabilities, Pairs):
        return list(probabilities.pairs)
    return []


def audit(db: str) -> None:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
    rows = conn.execute(
        """SELECT e.id, t.id, m.id, e.request, e.response, e.error, t.probability_source FROM exchanges e
           JOIN turns t ON t.id = e.turn_id JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
           JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
           WHERE p.name = ? ORDER BY e.id""", (NAME,)).fetchall()
    counts = dict.fromkeys(KINDS, 0)
    audited = no_answer = unreadable = failed = 0
    worst = 0.0
    bad = []
    matches = sorted({r[2] for r in rows})
    for eid, tid, mid, request, response, error, source in rows:
        try:
            shown = list(json.loads(request)["questions"]["play"]["criteria"])
            parsed = parse(response or "")
        except ValueError:
            unreadable += 1
            continue
        try:
            answer = parsed["answers"]["play"]
        except (KeyError, TypeError):
            no_answer += 1
            continue
        if answer.get("type") != "choice" or "probabilities" not in answer:
            no_answer += 1
            continue
        audited += 1
        entries = entries_of(answer["probabilities"])
        nums = [v for _, v in entries if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums and all(math.isfinite(v) for v in nums):
            worst = max(worst, abs(sum(nums) - 1))
        f = faults(entries, shown)
        for k in f:
            counts[k] += 1
        if f:
            failed += 1
            bad.append(f"exchange {eid} (turn {tid}, match #{mid}): {', '.join(sorted(f))}")
    print(f"{NAME}: {len(rows)} exchanges in matches {', '.join(f'#{m}' for m in matches)}, raw response text stored "
          f"for {sum(1 for r in rows if r[4])}; {audited} answers with a probability map audited, {unreadable} "
          f"unreadable as strict JSON, {no_answer} without a choice answer")
    print("| failing maps | " + " | ".join(KINDS) + " | max abs(sum - 1) |")
    print("|---" * (len(KINDS) + 2) + "|")
    print(f"| {failed} | " + " | ".join(str(counts[k]) for k in KINDS) + f" | {worst:.3g} |")
    for line in bad:
        print(line)


def controls() -> None:
    shown = ["a", "b"]
    cases = [
        ("valid", [("a", 0.25), ("b", 0.75)], set()),
        ("missing", [("a", 1.0)], {"missing"}),
        ("extra", [("a", 0.5), ("b", 0.5), ("c", 0.0)], {"unknown"}),
        ("repeated", [("a", 0.25), ("a", 0.25), ("b", 0.5)], {"repeated"}),
        ("NaN", [("a", float("nan")), ("b", 0.5)], {"not finite"}),
        ("inf", [("a", float("inf")), ("b", 0.0)], {"not finite"}),
        ("string", [("a", "0.5"), ("b", 0.5)], {"not a number"}),
        ("below 0", [("a", -0.5), ("b", 1.5)], {"below 0", "above 1"}),
        ("sum 1 + 2e-6", [("a", 0.5), ("b", 0.5 + 2e-6)], {"sum"}),
        ("sum 1 + 4e-7 (inside)", [("a", 0.5 + 4e-7), ("b", 0.5)], set()),
    ]
    ok = True
    for name, entries, want in cases:
        got = faults(entries, shown)
        ok &= got == want
        print(f"{'ok ' if got == want else 'BAD'} {name}: {sorted(got) or 'accepted'}")
    # The raw-text reader: a repeated key in the object (a plain dict would keep one) and a bare NaN token.
    raw = '{"answers":{"play":{"type":"choice","choice":"a","probabilities":{"a":0.5,"a":0.0,"b":0.5}}}}'
    got = faults(entries_of(parse(raw)["answers"]["play"]["probabilities"]), shown)
    ok &= got == {"repeated"}
    print(f"{'ok ' if got == {'repeated'} else 'BAD'} raw text, repeated key: {sorted(got) or 'accepted'}")
    try:
        parse('{"answers":{"play":{"probabilities":{"a":NaN,"b":0.5}}}}')
        ok = False
        print("BAD raw text, NaN token: read")
    except ValueError as e:
        print(f"ok  raw text, NaN token: unreadable ({e})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if sys.argv[1:] == ["--controls"]:
        controls()
    else:
        audit(sys.argv[1] if len(sys.argv) > 1 else "/home/cbasaran/code/jevgammon/v3.db")
