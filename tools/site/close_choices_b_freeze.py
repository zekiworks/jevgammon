#!/usr/bin/env python3
"""Close choices, stage B: the v2 freeze of 100 positions (Method spec 2026-10-24 §9.10).

    python3 tools/site/close_choices_b_freeze.py POOL EQUITIES_DIR OUT_JSONL OUT_RECORD

POOL is positions/new.jsonl. EQUITIES_DIR holds the GNUbg 2-ply values of every legal play of the pool
(`tools/v3/score.py evaluate`, files new-2ply-s*.db, table `equities`). Position class at margin 0.001 by the site's
rule (analysis.play_call): hitting rolls as shown with each option (describe.py), losses from the 2-ply values.
Targets 40 Risk pays, 40 Safety pays, 20 No trade-off, spread evenly over the phases; in each (class, phase) cell the
ids with the smallest sha256(SEED + id); shortfalls go to the other phases of the same class in phase order.
Rows are copied byte-identical; the record holds the rule, hashes, counts and ids.
"""

import hashlib
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE.parent / "v3"))

from describe import hitting_rolls  # noqa: E402
from rules import flip, from_json, legal_plays  # noqa: E402

SEED = "close-choices-b-v2-2026-10-24:"
MARGIN = 0.001
PHASES = ["opening", "contact", "holding", "race", "bear-off"]
TARGET = {"risk": 40, "safety": 40, "none": 20}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_equities(folder: Path) -> tuple[dict, str]:
    eq = defaultdict(dict)
    for p in sorted(folder.glob("new-2ply-s*.db")):
        db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        for pos, play, e in db.execute("SELECT position, play, equity FROM equities"):
            eq[pos][play] = e
        db.close()
    canon = "\n".join(f"{p}\t{n}\t{eq[p][n]!r}" for p in sorted(eq) for n in sorted(eq[p]))
    return eq, sha(canon)


def classify(row: dict, eq: dict) -> dict:
    d1, d2 = row["dice"]
    pos = from_json(row["position"], row["side"])
    plays = legal_plays(pos, d1, d2)
    names = [n for n, _ in plays]
    if names != row["legal_plays"]:
        raise SystemExit(f"{row['id']}: legal plays differ from the stored ones")
    shots = [hitting_rolls(flip(after)) for _, after in plays]
    e = [eq[row["id"]][n] for n in names]
    best = max(e)
    losses = [best - x for x in e]
    least = min(shots)
    if least == max(shots):
        return dict(cls="none", stake=None, n=len(names))
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    return dict(cls="risk" if stake >= MARGIN else "safety", stake=stake, n=len(names))


def quotas(target: int) -> dict:
    base, extra = divmod(target, len(PHASES))
    return {ph: base + (i < extra) for i, ph in enumerate(PHASES)}


def main():
    pool, eq_dir, out_jsonl, out_record = (Path(a) for a in sys.argv[1:5])
    raw = pool.read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    rows = [json.loads(l) for l in lines]
    eq, eq_hash = load_equities(eq_dir)
    info, cells, excluded = {}, defaultdict(list), 0
    for r in rows:
        if len(r["legal_plays"]) < 2:
            excluded += 1
            continue
        c = classify(r, eq)
        info[r["id"]] = c
        cells[(c["cls"], r["phase"])].append(r["id"])
    for k in cells:
        cells[k].sort(key=lambda i: sha(SEED + i))
    chosen, shortfall = {}, {}
    for cls, target in TARGET.items():
        q = quotas(target)
        take = {ph: min(q[ph], len(cells[(cls, ph)])) for ph in PHASES}
        missing = target - sum(take.values())
        while missing:
            room = [ph for ph in PHASES if take[ph] < len(cells[(cls, ph)])]
            if not room:
                break
            for ph in room:
                if not missing:
                    break
                take[ph] += 1
                missing -= 1
        shortfall[cls] = missing
        for ph in PHASES:
            chosen[(cls, ph)] = cells[(cls, ph)][:take[ph]]
    ids = {i for v in chosen.values() for i in v}
    out_lines = [l for l, r in zip(lines, rows) if r["id"] in ids]
    out = "".join(out_lines)
    out_jsonl.write_text(out)
    record = dict(
        set="close-choices-b-v2",
        method="tools/site/content/method-spec-2026-10-24.md §9.10 (branch brief-2026-10-24)",
        supersedes="freeze/close-choices-b.json (main; 20 per phase from v1 + new)",
        source=dict(file="positions/new.jsonl", sha256=hashlib.sha256(raw).hexdigest(), rows=len(rows)),
        engine_values=dict(tool="tools/v3/score.py evaluate (GNUbg 1.08, 2-ply cubeless, engine.PLY2), CPU nice 19, 8 shards",
                           files="~/.local/state/bg-site/shared/new-2ply-s0..s7.db",
                           sha256_of_sorted_position_play_equity_lines=eq_hash, positions=len(eq)),
        rule=("Position class at margin 0.001 (analysis.play_call); targets 40 Risk pays, 40 Safety pays, 20 No trade-off, "
              "evenly over the phases (8/8/4 per phase); per (class, phase) cell the ids with the smallest "
              f"sha256('{SEED}' + id); shortfall to other phases of the same class in phase order; rows byte-identical."),
        seed_text=SEED, excluded_fewer_than_2_legal_plays=excluded,
        eligible={f"{c}/{ph}": len(cells[(c, ph)]) for c in TARGET for ph in PHASES},
        selected_per_cell={f"{c}/{ph}": len(chosen[(c, ph)]) for c in TARGET for ph in PHASES},
        shortfall=shortfall,
        file=str(out_jsonl.name), sha256=hashlib.sha256(out.encode()).hexdigest(), rows=len(out_lines),
        options=dict(min=min(info[i]["n"] for i in ids), max=max(info[i]["n"] for i in ids),
                     total=sum(info[i]["n"] for i in ids)),
        frozen_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        selected={f"{c}/{ph}": [dict(id=i, stake=info[i]["stake"], options=info[i]["n"]) for i in chosen[(c, ph)]]
                  for c in TARGET for ph in PHASES})
    out_record.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("eligible", "selected_per_cell", "shortfall", "sha256", "rows", "options")}, indent=1))


if __name__ == "__main__":
    main()
