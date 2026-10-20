"""Compares the x86 and ARM runs of moves.py (plain Python 3; prints markdown).

    python3 compare.py data/x86.json data/arm.json

- Moves: positions where the two machines choose different plays, per context, with the 2-ply
  equity gap between the two plays and whether the position is a near-tie (best two plays within
  0.02 at 2-ply); 2-ply equities and losses are replay.db's (tools/gnubg_eval.py), exported by
  export.py. PR = 500 x mean 2-ply loss of the chosen play.
- Evaluations: the 0-ply outputs without noise (floating point), and the noise (noisy minus clean
  output) against a re-implementation of gnubg 1.08's deterministic Noise() (eval.c): md5 of the
  50 board bytes, sum of the 16 hash bytes read as `char`, minus 2040, over 295.6, times the noise
  (x 0.25 for gammons, x 0.01 for backgammons). `char` is signed on x86-64 and unsigned on aarch64.
- v3: the anchor's recorded league decisions replayed on both machines.
"""

import hashlib
import json
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools", "v3"))

from rules import apply_notation, flip, from_json, gnubg_board, key, legal_plays  # noqa: E402

x86, arm = (json.load(open(p)) for p in sys.argv[1:3])
data = json.load(open(os.path.join(HERE, "data", "positions.json")))
NOISE = 0.06
SCALE = [1.0, 0.25, 0.01, 0.25, 0.01]  # win, wg, wbg, lg, lbg


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def noise(board, output, signed):
    """gnubg 1.08 eval.c Noise() with fDeterministic, char signed or unsigned."""
    raw = [board[0][i] if j == 0 else board[1][i] for i in range(25) for j in (0, 1)]
    raw[0] = (raw[0] + output) & 0xFF
    digest = hashlib.md5(bytes(b & 0xFF for b in raw)).digest()
    total = sum((b - 256 if b >= 128 else b) if signed else b for b in digest)
    return f32(f32(f32(total) - 2040.0) / 295.6) * f32(NOISE) * SCALE[output], digest


def eq_lookup(p):
    pos = from_json(p["position"], p["side"])
    return {key(apply_notation(pos, n)): (e, l) for n, (e, l) in p["equities"].items()}


print(f"x86: {x86['machine']} {x86['arch']}, Python {x86['python'].split()[0]}; "
      f"ARM: {arm['machine']} {arm['arch']}, Python {arm['python'].split()[0]}")
print(f"seconds x86 {x86['seconds']}, ARM {arm['seconds']}\n")

# --- move choice on the v1 set -------------------------------------------------------------
print("## v1 set: chosen plays\n")
print("| context | positions | same play | different | PR x86 | PR ARM |")
print("|---|---:|---:|---:|---:|---:|")
diffs = {}
for name in ("n0.06", "n0"):
    rows, pr = [], {"x86": [], "arm": []}
    for p, a, b in zip(data["v1"], x86["v1"], arm["v1"]):
        assert p["id"] == a["id"] == b["id"] and a["plays"] == b["plays"]
        pos = from_json(p["position"], p["side"])
        by_key = eq_lookup(p)
        plays = {i: key(apply_notation(pos, n)) for i, n in enumerate(a["plays"])}
        ea, eb = by_key[plays[a[name]["index"]]], by_key[plays[b[name]["index"]]]
        pr["x86"].append(ea[1])
        pr["arm"].append(eb[1])
        if a[name]["index"] != b[name]["index"]:
            top = sorted((e for e, _ in by_key.values()), reverse=True)
            near = len(top) > 1 and top[0] - top[1] <= 0.02
            rows.append((p["id"], a["plays"][a[name]["index"]], b["plays"][b[name]["index"]],
                         ea[0], eb[0], ea[0] - eb[0], ea[1], eb[1], near, len(top)))
    diffs[name] = rows
    n = len(data["v1"])
    print(f"| {name} | {n} | {n - len(rows)} | {len(rows)} | "
          f"{500 * sum(pr['x86']) / n:.2f} | {500 * sum(pr['arm']) / n:.2f} |")

for name, rows in diffs.items():
    if not rows:
        continue
    near = sum(r[8] for r in rows)
    gaps = sorted(abs(r[5]) for r in rows)
    x_better = sum(r[5] > 0 for r in rows)
    print(f"\n### {name}: {len(rows)} positions with different plays\n")
    print(f"- near-ties (best two plays within 0.02 at 2-ply): {near} of {len(rows)}")
    print(f"- |2-ply equity gap| between the two plays: median {gaps[len(gaps) // 2]:.3f}, "
          f"mean {sum(gaps) / len(gaps):.3f}, max {gaps[-1]:.3f}; "
          f"gap ≤ 0.02: {sum(g <= 0.02 for g in gaps)}, > 0.1: {sum(g > 0.1 for g in gaps)}")
    print(f"- x86 play better at 2-ply: {x_better}, ARM better: "
          f"{sum(r[5] < 0 for r in rows)}, equal: {sum(r[5] == 0 for r in rows)}")
    print(f"- mean 2-ply loss on these positions: x86 {sum(r[6] for r in rows) / len(rows):.4f}, "
          f"ARM {sum(r[7] for r in rows) / len(rows):.4f}\n")
    if len(rows) <= 40:
        print("| id | x86 play | ARM play | 2-ply eq x86 | 2-ply eq ARM | gap (x86 − ARM) "
              "| near-tie | legal plays |")
        print("|---:|---|---|---:|---:|---:|---|---:|")
        for r in rows:
            print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:+.3f} | {r[4]:+.3f} | {r[5]:+.3f} | "
                  f"{'yes' if r[8] else 'no'} | {r[9]} |")

# --- raw evaluations ---------------------------------------------------------------------------
print("\n## v1 set: raw 0-ply evaluations (position on roll + every legal result)\n")
evals = {"n0": [0, 0, 0.0], "n0.06": [0, 0, 0.0]}  # count, bit-equal, max |diff|
noise_check = Counter()
noise_units = {"x86": [], "arm": []}
step_hist = Counter()
FP_BINS = (0.0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1.0)
fp_hist = Counter()
predicted = {"x86": [], "arm": []}
for p, a, b in zip(data["v1"], x86["v1"], arm["v1"]):
    pos = from_json(p["position"], p["side"])
    boards = [gnubg_board(pos)] + [gnubg_board(flip(r)) for _, r in legal_plays(pos, *p["dice"])]
    for name in evals:
        va = [a[name]["eval_root"]] + a[name]["eval_results"]
        vb = [b[name]["eval_root"]] + b[name]["eval_results"]
        for xa, xb in zip(va, vb):
            for u, v in zip(xa, xb):
                evals[name][0] += 1
                evals[name][1] += u == v
                evals[name][2] = max(evals[name][2], abs(u - v))
                if name == "n0":
                    fp_hist[next(t for t in FP_BINS if abs(u - v) <= t)] += 1
    clean_a = [a["n0"]["eval_root"]] + a["n0"]["eval_results"]
    clean_b = [b["n0"]["eval_root"]] + b["n0"]["eval_results"]
    noisy_a = [a["n0.06"]["eval_root"]] + a["n0.06"]["eval_results"]
    noisy_b = [b["n0.06"]["eval_root"]] + b["n0.06"]["eval_results"]
    for board, ca, cb, na, nb in zip(boards, clean_a, clean_b, noisy_a, noisy_b):
        for o in range(5):
            if ca[o] in (0.0, 1.0) and o != 0:
                continue  # an output gnubg pins (e.g. no gammon possible) says nothing
            for machine, clean, noisy, signed in (("x86", ca, na, True), ("arm", cb, nb, False)):
                pred, digest = noise(board, o, signed)
                units = pred / (NOISE * SCALE[o])
                predicted[machine].append(units)
                expect = min(max(clean[o] + pred, 0.0), 1.0)
                if 0.0 < expect < 1.0:
                    ok = abs(noisy[o] - expect) < 2e-5
                    noise_check[(machine, ok)] += 1
                    if ok:
                        noise_units[machine].append((noisy[o] - clean[o]) / (NOISE * SCALE[o]))
                if machine == "x86":
                    step_hist[sum(b >= 128 for b in digest)] += 1
print("| context | outputs compared | bit-identical | max abs difference |")
print("|---|---:|---:|---:|")
for name, (n, same, mx) in evals.items():
    print(f"| {name} | {n} | {same} ({100 * same / n:.2f}%) | {mx:.3g} |")
print("\nNoise-free outputs, |x86 − ARM|: " + ", ".join(
    f"≤ {t:g}: {fp_hist[t]}" for t in FP_BINS))


def mean_sd(u):
    mean = sum(u) / len(u)
    return mean, (sum((x - mean) ** 2 for x in u) / len(u)) ** 0.5


print("\nDeterministic noise in units of noise × scale (0.06 for wins, 0.015 for gammons, "
      "0.0006 for backgammons). Predicted: the re-implemented Noise() over every call "
      "(signed `char` on x86, unsigned on ARM). Checked: outputs not clamped at 0 or 1, observed "
      "noisy − clean against clamp(clean + predicted).\n")
print("| machine | predicted mean | predicted SD | checked outputs | match | observed mean "
      "(matching) | observed SD |")
print("|---|---:|---:|---:|---:|---:|---:|")
for machine in ("x86", "arm"):
    pm, ps = mean_sd(predicted[machine])
    om, osd = mean_sd(noise_units[machine])
    ok = noise_check[(machine, True)]
    total = ok + noise_check[(machine, False)]
    print(f"| {machine} | {pm:+.3f} | {ps:.3f} | {total} | {ok} ({100 * ok / total:.1f}%) | "
          f"{om:+.3f} | {osd:.3f} |")
print("\nHash bytes ≥ 128 per Noise() call (each lowers the x86 value by 256/295.6 = 0.866 "
      f"units): mean {sum(k * v for k, v in step_hist.items()) / sum(step_hist.values()):.2f}")

# --- v3 anchor decisions -----------------------------------------------------------------------
print("\n## v3: the anchor's recorded league decisions replayed\n")
rec = {p["turn_id"]: p["chosen_index"] for p in data["v3"]}
n = len(data["v3"])
xa = sum(r["index"] == rec[r["turn_id"]] for r in x86["v3"])
ar = sum(r["index"] == rec[r["turn_id"]] for r in arm["v3"])
xy = sum(r["index"] == s["index"] for r, s in zip(x86["v3"], arm["v3"]))
print("| decisions | x86 = recorded | ARM = recorded | x86 = ARM |")
print("|---:|---:|---:|---:|")
print(f"| {n} | {xa} ({100 * xa / n:.1f}%) | {ar} ({100 * ar / n:.1f}%) | {xy} ({100 * xy / n:.1f}%) |")
