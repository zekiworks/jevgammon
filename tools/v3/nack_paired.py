"""Nackgammon paired test (Method spec 2026-10-24 §10): candidates, matched sets, 2-ply scores,
engine-check subset, balance and Random's error rates. Plays no model.

Three steps, from the repo root:

    # 1. Candidates, inside gnubg's embedded Python, one process per shard (2-ply for every legal play):
    V3_ARGS="candidates VARIANT SHARD SHARDS OUT.jsonl.gz" nice -n 19 gnubg -t -q -p tools/v3/nack_paired.py
    # 2. Sets, plain Python (numpy only for the bootstrap of Random's rates):
    python3 tools/v3/nack_paired.py build
    # 3. Freeze (hashes of the sets, games, candidates, code and prompts):
    python3 tools/v3/nack_paired.py freeze GNUBG_VERSION METHOD_COMMIT

Step 1 reads positions/nack-paired/games/VARIANT-*.jsonl.gz (tools/v3/selfplay.py, seed token
np20261027); per game and phase it draws at most 2 turns with 2 to 25 legal plays
(random.Random(f"{SEED}:{variant}:{game}:{phase}")) and writes every legal play's 2-ply cubeless
equity (engine.PLY2, as tools/v3/score.py evaluate) and hitting rolls (describe.hitting_rolls).

Step 2 matches the pairs (§10.7) and writes positions/nack-paired/{main,reserve}.jsonl (the rows the
runner reads, interleaved npn/nps by pair), pairs.jsonl, scores-2ply.jsonl, engine-check.json and
build-log.json (pool sizes, shortfalls, balance, tag mix, Random's error rates).
"""

import glob
import gzip
import hashlib
import json
import os
import random
import sys

ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "tools", "v3"))  # gnubg runs scripts without __file__
sys.path.insert(0, os.path.join(ROOT, "tools", "site"))

import classify  # noqa: E402
from rules import legal_plays, pips, to_json  # noqa: E402

SEED = "nack-paired-2026-10-27"
GAME_SEED = "np20261027"
OUT = os.environ.get("NP_OUT", "positions/nack-paired")  # NP_OUT only for offline tests
MIN_PLAYS, MAX_PLAYS = 2, 25
PER_PHASE = 2
MARGIN = 0.001
GAP_CAP = 0.25
PROMPTS = {"standard": "bg-v3-std-notable", "nackgammon": "bg-v3-nack"}
PREFIX = {"standard": "nps", "nackgammon": "npn"}
CLASSES = ("risk", "safety", "none")
# §10.7: pairs per (phase, class).
QUOTAS = {
    "main": {"opening": (30, 30, 0), "contact": (24, 24, 12), "holding": (12, 12, 6),
             "race": (0, 0, 25), "bear-off": (0, 0, 25)},
    "reserve": {"opening": (45, 45, 0), "contact": (36, 36, 18), "holding": (18, 18, 9),
                "race": (0, 0, 38), "bear-off": (0, 0, 37)},
}
ENGINE_CHECK = {"opening": 12, "contact": 12, "holding": 6, "race": 5, "bear-off": 5}


def h(text):
    return hashlib.sha256(f"{SEED}:{text}".encode()).hexdigest()


# --- Step 1: candidates (inside gnubg) ----------------------------------------------------------

def candidates(variant, shard, shards, out):
    import engine
    from describe import hitting_rolls
    from rules import flip

    paths = sorted(glob.glob(f"{OUT}/games/{variant}-*.jsonl.gz"))
    n_out = 0
    with gzip.open(out, "wt") as f:
        for path in paths:
            with gzip.open(path, "rt") as g:
                for line in g:
                    game = json.loads(line)
                    if game["game"] % shards != shard:
                        continue
                    by_phase = {}
                    for t in game["turns"]:
                        if not MIN_PLAYS <= t["n"] <= MAX_PLAYS:
                            continue
                        pos = (t["pts"], t["bar"], t["off"])
                        by_phase.setdefault(classify.phase(pos, t["cls"], t["t"]), []).append((t, pos))
                    for ph in classify.PHASES:
                        items = by_phase.get(ph, [])
                        rng = random.Random(f"{SEED}:{variant}:{game['game']}:{ph}")
                        for t, pos in rng.sample(items, min(PER_PHASE, len(items))):
                            hi, lo = max(t["dice"]), min(t["dice"])
                            plays = legal_plays(pos, hi, lo)
                            assert len(plays) == t["n"]
                            eq = [engine.equity(p, engine.PLY2) for _, p in plays]
                            shots = [hitting_rolls(flip(p)) for _, p in plays]
                            f.write(json.dumps({
                                "game": f"{variant}:{GAME_SEED}:{game['game']}", "variant": variant,
                                "turn": t["t"], "side": t["side"], "dice": [hi, lo], "pid": t["pid"],
                                "cls": t["cls"], "phase": ph, "pts": pos[0], "bar": pos[1], "off": pos[2],
                                "plays": [n for n, _ in plays], "equity": eq, "shots": shots},
                                separators=(",", ":")) + "\n")
                            n_out += 1
    print(f"candidates {variant} shard {shard}/{shards}: {n_out}", flush=True)


# --- Step 2: sets (plain Python) -----------------------------------------------------------------

def play_call(shots, losses, i, margin=MARGIN):
    """analysis.play_call (B6.1), copied so this step needs no site import."""
    least = min(shots)
    if least == max(shots):
        return "none", None, None
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call, stake


def enrich(c):
    best = max(c["equity"])
    c["loss"] = [best - e for e in c["equity"]]
    top = sorted(c["equity"], reverse=True)
    c["gap"] = top[0] - top[1]
    c["n"] = len(c["plays"])
    c["class"], _, c["stake"] = play_call(c["shots"], c["loss"], 0)
    c["random_loss"] = sum(c["loss"]) / c["n"]
    c["worst_loss"] = max(c["loss"])
    pos = (c["pts"], c["bar"], c["off"])
    c["tag"] = classify.tag(pos, c["phase"])
    mine, theirs = pips(pos)
    c["pips"], c["pip_lead"] = mine, theirs - mine
    c["key"] = f"{c['game']}:{c['turn']}"
    c["state"] = (c["pid"], c["dice"][0], c["dice"][1])
    return c


def load_pool(variant):
    pool = []
    for path in sorted(glob.glob(f"{OUT}/candidates/{variant}-*.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            pool.extend(enrich(json.loads(line)) for line in f)
    return pool


def tol_n(n):
    return 1 if n <= 10 else 2


def tol_g(g):
    return max(0.005, 0.1 * min(g, GAP_CAP))


def fits(a, b):
    """Every §10.7 tolerance for standard candidate b against Nackgammon candidate a."""
    if a["phase"] != b["phase"] or a["class"] != b["class"]:
        return None
    if a["phase"] == "opening" and abs(a["turn"] - b["turn"]) > 1:
        return None
    dn = abs(a["n"] - b["n"])
    dg = abs(min(a["gap"], GAP_CAP) - min(b["gap"], GAP_CAP))
    tn, tg = tol_n(a["n"]), tol_g(a["gap"])
    if dn > tn or dg > tg:
        return None
    return dn / tn + dg / tg


def match(nack, std, quotas, used_games, used_states, log_name, log):
    """§10.7 steps 1 and 3: greedy in h-order, shortfall moved within the phase, then to contact."""
    import bisect
    index = {}
    for b in std:
        index.setdefault((b["phase"], b["class"], b["n"]), []).append((min(b["gap"], GAP_CAP), h(b["key"]), b))
    for items in index.values():
        items.sort(key=lambda x: (x[0], x[1]))
    gaps = {k: [x[0] for x in v] for k, v in index.items()}
    order = sorted(nack, key=lambda a: h(a["key"]))
    want = {(ph, cls): q for ph, qs in quotas.items() for cls, q in zip(CLASSES, qs)}
    pairs, moves = [], []
    while True:
        for a in order:
            cell = (a["phase"], a["class"])
            if want.get(cell, 0) <= 0 or a["game"] in used_games or a["state"] in used_states:
                continue
            g, tg, tn = min(a["gap"], GAP_CAP), tol_g(a["gap"]), tol_n(a["n"])
            best = None
            for n in range(a["n"] - tn, a["n"] + tn + 1):
                k = (*cell, n)
                if k not in index:
                    continue
                lo = bisect.bisect_left(gaps[k], g - tg)
                hi = bisect.bisect_right(gaps[k], g + tg)
                for _, hb, b in index[k][lo:hi]:
                    if b["game"] in used_games or b["state"] in used_states or b["state"] == a["state"]:
                        continue
                    d = fits(a, b)
                    if d is not None and (best is None or (d, hb) < best[:2]):
                        best = (d, hb, b)
            if best is None:
                continue
            d, _, b = best
            used_games.update((a["game"], b["game"]))
            used_states.update((a["state"], b["state"]))
            pairs.append((a, b, d))
            want[cell] -= 1
        short = {c: q for c, q in want.items() if q > 0}
        if not short:
            break
        moved = False
        for (ph, cls), q in sorted(short.items()):
            targets = [(ph, c) for c in (("safety", "none") if cls == "risk" else ("risk", "none") if cls == "safety" else ())]
            if ph != "contact":
                targets.append(("contact", cls))
            for t in targets:
                if t in short or t == (ph, cls):
                    continue
                want[t] = want.get(t, 0) + q
                want[(ph, cls)] = 0
                moves.append({"from": f"{ph}/{cls}", "to": f"{t[0]}/{t[1]}", "pairs": q})
                moved = True
                break
        if not moved:
            moves.append({"unfilled": {f"{p}/{c}": q for (p, c), q in short.items()}})
            break
    log[log_name + "_shortfall_moves"] = moves
    return pairs


def row(c, set_name, pid, pair_id, option_seed):
    from order import option_order, position_key
    hi, lo = c["dice"]
    pkey = position_key(c["pid"], hi, lo, c["side"])
    pos = (c["pts"], c["bar"], c["off"])
    assert [n for n, _ in legal_plays(pos, hi, lo)] == c["plays"]
    r = {"id": pid, "set": set_name, "pair": pair_id, "variant": c["variant"], "prompt": PROMPTS[c["variant"]],
         "phase": c["phase"], "class": c["class"], "tag": c["tag"], "gnubg_class": c["cls"],
         "position_id": c["pid"], "position_key": pkey, "dice": [hi, lo], "side": c["side"], "turn": c["turn"],
         "first_roll": c["turn"] == 1, "source_game": c["game"], "legal_plays": c["plays"],
         "option_order": option_order(option_seed, pkey, len(c["plays"])), "position": to_json(pos, c["side"])}
    if c["phase"] == "holding":
        r["race_deficit"] = classify.race_deficit(pos)
    return r


def stats_of(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    mean = sum(xs) / n
    sd = (sum((x - mean) ** 2 for x in xs) / (n - 1)) ** 0.5 if n > 1 else 0.0
    med = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    return mean, med, sd


BALANCE = {"legal_plays": "n", "gap": "gap", "turn": "turn", "pips": "pips", "pip_lead": "pip_lead",
           "random_error_pr": "random_loss", "stake": "stake"}


def balance(pairs):
    out = {}
    for name, field in BALANCE.items():
        scale = 500 if field == "random_loss" else 1
        a = [p[0][field] * scale for p in pairs if p[0][field] is not None]
        b = [p[1][field] * scale for p in pairs if p[1][field] is not None]
        sa, sb = stats_of(a), stats_of(b)
        if not sa or not sb:
            out[name] = None
            continue
        pooled = ((sa[2] ** 2 + sb[2] ** 2) / 2) ** 0.5
        out[name] = {"nackgammon": {"mean": round(sa[0], 4), "median": round(sa[1], 4)},
                     "standard": {"mean": round(sb[0], 4), "median": round(sb[1], 4)},
                     "smd": round((sa[0] - sb[0]) / pooled, 3) if pooled else 0.0, "n": len(a)}
    return out


def mix(pairs, field, side):
    out = {}
    for p in pairs:
        k = str(p[side][field])
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def random_rates(pairs, label):
    """Random's PR per set (exact over legal plays) and its drop with a 95% paired bootstrap."""
    import numpy as np
    nack = np.array([500 * p[0]["random_loss"] for p in pairs])
    std = np.array([500 * p[1]["random_loss"] for p in pairs])
    rng = np.random.default_rng(int(h("bootstrap:random:" + label)[:16], 16))
    idx = rng.integers(0, len(pairs), size=(10000, len(pairs)))
    drops = nack[idx].mean(axis=1) - std[idx].mean(axis=1)
    lo, hi = np.quantile(drops, [0.025, 0.975])
    return {"pairs": len(pairs), "standard_pr": round(float(std.mean()), 2), "nackgammon_pr": round(float(nack.mean()), 2),
            "drop": round(float(nack.mean() - std.mean()), 2), "drop_95": [round(float(lo), 2), round(float(hi), 2)]}


def build():
    with open("seeds.json") as f:
        option_seed = json.load(f)["option_order_seed"]
    nack, std = load_pool("nackgammon"), load_pool("standard")
    log = {"pool": {}}
    for name, pool in (("nackgammon", nack), ("standard", std)):
        cells = {}
        for c in pool:
            k = f"{c['phase']}/{c['class']}"
            cells[k] = cells.get(k, 0) + 1
        log["pool"][name] = {"candidates": len(pool), "games": len({c["game"] for c in pool}),
                             "per_cell": dict(sorted(cells.items()))}
    used_games, used_states = set(), set()
    sets = {}
    for set_name in ("main", "reserve"):
        pairs = match(nack, std, QUOTAS[set_name], used_games, used_states, set_name, log)
        pairs.sort(key=lambda p: h("order:" + p[0]["key"]))
        sets[set_name] = pairs
    os.makedirs(OUT, exist_ok=True)
    rows, pair_rows, score_rows = {"main": [], "reserve": []}, [], []
    number = 0
    for set_name in ("main", "reserve"):
        for a, b, d in sets[set_name]:
            number += 1
            pair_id = f"np-{number:04d}"
            ids = {}
            for c in (a, b):
                pid = f"{PREFIX[c['variant']]}-{number:04d}"
                ids[c["variant"]] = pid
                rows[set_name].append(row(c, f"nack-paired-{set_name}", pid, pair_id, option_seed))
                score_rows.append({"id": pid, "plays": [
                    {"play": n, "equity": e, "loss": l, "hitting_rolls": s}
                    for n, e, l, s in zip(c["plays"], c["equity"], c["loss"], c["shots"])],
                    "random_loss": c["random_loss"], "worst_loss": c["worst_loss"], "gap": c["gap"],
                    "stake": c["stake"]})
            pair_rows.append({"pair": pair_id, "set": set_name, "nackgammon": ids["nackgammon"],
                              "standard": ids["standard"], "phase": a["phase"], "class": a["class"],
                              "turn": [a["turn"], b["turn"]], "legal_plays": [a["n"], b["n"]],
                              "gap": [round(a["gap"], 6), round(b["gap"], 6)], "distance": round(d, 4),
                              "source_game": [a["game"], b["game"]]})
    for set_name, rs in rows.items():
        with open(f"{OUT}/{set_name}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
    for name, items in (("pairs", pair_rows), ("scores-2ply", score_rows)):
        with open(f"{OUT}/{name}.jsonl", "w") as f:
            for r in items:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
    # §10.12: 40 main pairs, per phase the smallest h("engine:" + pair id).
    main_pairs = [p for p in pair_rows if p["set"] == "main"]
    engine = []
    for ph, k in ENGINE_CHECK.items():
        engine += sorted((p for p in main_pairs if p["phase"] == ph), key=lambda p: h("engine:" + p["pair"]))[:k]
    engine.sort(key=lambda p: p["pair"])
    with open(f"{OUT}/engine-check.json", "w") as f:
        json.dump({"rule": "Method §10.12: per phase opening 12, contact 12, holding 6, race 5, bear-off 5 of the "
                           "main pairs, smallest sha256('nack-paired-2026-10-27:engine:' + pair id)",
                   "pairs": [p["pair"] for p in engine],
                   "positions": [x for p in engine for x in (p["nackgammon"], p["standard"])],
                   "per_phase": {ph: sum(p["phase"] == ph for p in engine) for ph in ENGINE_CHECK},
                   "per_class": {c: sum(p["class"] == c for p in engine) for c in CLASSES}}, f, indent=1)
        f.write("\n")
    for set_name, pairs in sets.items():
        per = {}
        for a, _, _ in pairs:
            per.setdefault(a["phase"], {}).setdefault(a["class"], 0)
            per[a["phase"]][a["class"]] += 1
        log[set_name] = {
            "pairs": len(pairs), "per_phase_class": per,
            "class_matched": sum(a["class"] == b["class"] for a, b, _ in pairs),
            "balance": balance(pairs),
            "balance_by_phase": {ph: balance([p for p in pairs if p[0]["phase"] == ph]) for ph in classify.PHASES},
            "gnubg_class_mix": {"nackgammon": mix(pairs, "cls", 0), "standard": mix(pairs, "cls", 1)},
            "tag_mix": {"nackgammon": mix(pairs, "tag", 0), "standard": mix(pairs, "tag", 1)},
            "first_roll_positions": {"nackgammon": sum(a["turn"] == 1 for a, _, _ in pairs),
                                     "standard": sum(b["turn"] == 1 for _, b, _ in pairs)},
            "random": {"all": random_rates(pairs, set_name),
                       "by_phase": {ph: random_rates([p for p in pairs if p[0]["phase"] == ph], f"{set_name}:{ph}")
                                    for ph in classify.PHASES if any(p[0]["phase"] == ph for p in pairs)},
                       "by_class": {c: random_rates([p for p in pairs if p[0]["class"] == c], f"{set_name}:{c}")
                                    for c in CLASSES if any(p[0]["class"] == c for p in pairs)}},
        }
    both = sets["main"] + sets["reserve"]
    log["main_plus_reserve"] = {"random": random_rates(both, "all500"),
                                "tag_mix": {"nackgammon": mix(both, "tag", 0), "standard": mix(both, "tag", 1)}}
    games = [g for p in pair_rows for g in p["source_game"]]
    states = [(r["position_id"], *r["dice"]) for rs in rows.values() for r in rs]
    log["checks"] = {"games_distinct": len(games) == len(set(games)), "states_distinct": len(states) == len(set(states)),
                     "positions": len(states)}
    with open(f"{OUT}/build-log.json", "w") as f:
        json.dump(log, f, indent=1)
        f.write("\n")
    print(json.dumps({k: log[k] for k in ("pool", "checks", "main_shortfall_moves", "reserve_shortfall_moves")}, indent=1))


def sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


FROZEN_CODE = ["tools/v3/nack_paired.py", "tools/v3/selfplay.py", "tools/v3/classify.py", "tools/v3/engine.py",
               "tools/v3/rules.py", "tools/v3/order.py", "tools/site/describe.py", "seeds.json",
               "prompts/bg-v3-std-notable.md", "prompts/bg-v3-nack.md", "prompts/instructions.txt",
               "prompts/question.txt", "prompts/letter-system.txt", "src/players/prompt.rs"]


def freeze(gnubg_version, method_commit, out="freeze/nack-paired.json"):
    """freeze/nack-paired.json: sha256 of every set file, the games and candidates, the code and prompts."""
    import platform
    import subprocess
    import numpy
    files = {p: {"sha256": sha256(p), "bytes": os.path.getsize(p)}
             for p in sorted(glob.glob(f"{OUT}/*.jsonl") + glob.glob(f"{OUT}/*.json"))}
    for p in files:
        if p.endswith(".jsonl"):
            with open(p, "rb") as f:
                files[p]["rows"] = sum(1 for _ in f)
    raw = {p: sha256(p) for p in sorted(glob.glob(f"{OUT}/games/*.jsonl.gz") + glob.glob(f"{OUT}/candidates/*.jsonl.gz"))}
    with open(f"{OUT}/engine-check.json") as f:
        engine_check = json.load(f)
    with open(f"{OUT}/build-log.json") as f:
        log = json.load(f)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    record = {
        "set": "nack-paired",
        "method": f"tools/site/content/method-spec-2026-10-24.md §10 (committed {method_commit}, before the build)",
        "brief": "mailbox/Nackgammon and Terra - brief 2026-10-27.md",
        "frozen_before_any_model_call": True,
        "harness_commit": commit,
        "tools": {"gnubg": gnubg_version, "python": platform.python_version(), "numpy": numpy.__version__,
                  "engine": "engine.PLY2: 2-ply, cubeless money equity, deterministic, prune on",
                  "selfplay": "tools/v3/selfplay.py, GNUbg expert level (0-ply, no noise, cubeless)"},
        "seeds": {"selfplay_seed_token": GAME_SEED, "games_per_variant": [0, 10000], "shards": 16,
                  "sampling_and_order_seed_text": SEED + ":", "option_order_seed": "seeds.json option_order_seed",
                  "bootstrap_seed": "first 8 bytes of sha256('nack-paired-2026-10-27:bootstrap:<look>')"},
        "rules": {"candidates_per_game_and_phase": PER_PHASE, "legal_plays": [MIN_PLAYS, MAX_PLAYS], "class_margin": MARGIN,
                  "gap_cap": GAP_CAP, "tol_legal_plays": "1 if n <= 10 else 2", "tol_gap": "max(0.005, 0.1 * gap)",
                  "opening_turn_tolerance": 1, "quotas": QUOTAS, "engine_check_per_phase": ENGINE_CHECK,
                  "prompts": PROMPTS},
        "counts": {s: {"pairs": log[s]["pairs"], "per_phase_class": log[s]["per_phase_class"],
                       "shortfall_moves": log[s + "_shortfall_moves"]} for s in ("main", "reserve")},
        "checks": log["checks"],
        "engine_check": {"pairs": engine_check["pairs"], "positions": engine_check["positions"]},
        "files": files,
        "raw_files_sha256": raw,
        "code_and_prompts_sha256": {p: sha256(p) for p in FROZEN_CODE},
    }
    with open(out, "w") as f:
        json.dump(record, f, indent=1)
        f.write("\n")
    print(f"{out}: {len(files)} set files, {len(raw)} raw files, {len(FROZEN_CODE)} code and prompt files")


def main():
    args = os.environ.get("V3_ARGS", "").split() or sys.argv[1:]
    if args[0] == "candidates":
        candidates(args[1], int(args[2]), int(args[3]), args[4])
    elif args[0] == "build":
        build()
    elif args[0] == "freeze":
        freeze(args[1], args[2])
    else:
        raise SystemExit(f"unknown mode {args[0]}")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    os._exit(1)
sys.stdout.flush()
if os.environ.get("V3_ARGS"):
    os._exit(0)  # gnubg: leave without its shell
