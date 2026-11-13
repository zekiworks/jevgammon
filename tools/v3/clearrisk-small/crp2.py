#!/usr/bin/env python3
"""Clear-risk Part 2 for the small models (Ümit #6225): Q1 (with numbers, board only) and Q2 (board only) on the same
items the eight Part 2 models answered, asked through `jevgammon quiz` (branch quiz-command, a52da92) with each
model's league settings (models.json: the player.json of its late-entry branch, sha256-pinned).

    crp2.py check-items [SCRATCH]          items_q1q2.jsonl == the Q1/Q2 lines of SCRATCH/items_{chat,decision}.jsonl
    crp2.py player KEY                     the pinned league settings of KEY (JSON)
    crp2.py config KEY OUT [--base-url U]  league config for `jevgammon quiz` (one player); U only for stub tests
    crp2.py plan [--requests TSV]          every request per model (dry run, nothing sent), counts, fit, estimates
    crp2.py score DB [--setup NAME ...]    frozen Part 2 scoring (p2rep.py's parse_json/pick, verbatim) of Q1/Q2
                                           and the invalid-answer share, as markdown

Items: items_q1q2.jsonl holds the 438 Q1/Q2 lines (189 Q1 with numbers, 189 Q1 board only, 60 Q2 board only) of the
Part 2 items, byte-identical; each line carries both forms (decision: name/state/instructions/options; chat:
system/user/schema), the same ids. meta.json is the Part 2 meta.json (right/safe/unsafe play per position).
"""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
ITEMS = HERE / "items_q1q2.jsonl"
META = HERE / "meta.json"
ITEMS_SHA = "1344aa4a37df678b1db2ce56e9131510ab70607ea4c623224a721ced90a40c58"
META_SHA = "654e6a7862669301bdb2fde21464925acbca465884738562042ce693e4abd031"
# The Part 2 sources (workspace/clearrisk-scratch, as asked on 30 Oct).
SOURCE_SHA = {"items_chat.jsonl": "672cf015057e6c4551fc543e53c8fa1d074b1640d323869a3c09942b9cc51429",
              "items_decision.jsonl": "c752c58cb4074aeb8a585d9964974467a577d30e1a37dcd869336ba56bb63bec"}
EXPECTED = {"Q1:numbers": 189, "Q1:board": 189, "Q2:board": 60}
# Part 2's chat setups (p2rep.py CHAT) and its time limits per question (part2.sh).
PART2_CHAT = {"Claude Sonnet 5.5 (high)", "GPT-6.1 Sol (high)", "Kimi K3.1 Pro (off)", "GLM-5.3 (on)",
              "Claude Opus 5.5 (on)"}
TIME_LIMIT = {"decision": 300, "chat": 900}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def models():
    return {k: v for k, v in json.loads((HERE / "models.json").read_text()).items() if not k.startswith("_")}


def items():
    assert sha256(ITEMS) == ITEMS_SHA, f"{ITEMS} changed"
    return [json.loads(line) for line in ITEMS.read_text().splitlines()]


def kind(item_id):
    return ":".join(item_id.split(":")[1:3])


def check_items(scratch):
    scratch = Path(scratch)
    for name, digest in SOURCE_SHA.items():
        assert sha256(scratch / name) == digest, f"{name}: not the Part 2 source"
        lines = [l for l in (scratch / name).read_text().splitlines(keepends=True)
                 if kind(json.loads(l)["id"]).split(":")[0] in ("Q1", "Q2")]
        assert "".join(lines) == ITEMS.read_text(), f"{name}: Q1/Q2 lines differ from {ITEMS.name}"
    assert sha256(scratch / "meta.json") == META_SHA == sha256(META)
    counts = Counter(kind(i["id"]) for i in items())
    assert counts == EXPECTED, counts
    print(f"items ok: {dict(counts)} = {sum(counts.values())}, byte-identical to both Part 2 item files")


def player(key):
    m = models()[key]
    if m["source"].startswith("file:"):  # settings copied byte-exact from v3.db players.settings (test_crp2 checks)
        text = (HERE / m["source"][5:]).read_bytes()
    else:
        text = subprocess.run(["git", "-C", str(ROOT), "show", m["source"]], check=True, capture_output=True).stdout
    assert hashlib.sha256(text).hexdigest() == m["sha256"], f"{key}: {m['source']} is not the pinned file"
    p = json.loads(text)
    assert p["name"] == m["name"], (p["name"], m["name"])
    return p


def config(key, out, base_url=None):
    p = player(key)
    if base_url:
        p["base_url"] = base_url
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({"players": [p], "note": (
        f"Clear-risk Part 2, small models (Ümit #6225): {p['name']} at its league settings ({models()[key]['source']})"
        + (f"; base_url replaced by {base_url} (stub test)" if base_url else ""))}, indent=1) + "\n")
    return p


def plan(requests_tsv=None):
    its = items()
    rows, out = [], []
    for key, m in models().items():
        n = len(its)
        if m["kind"] == "decision":
            bad = [i["id"] for i in its if not 2 <= len(i["options"]) <= m["max_choices"]]
            assert not bad, (key, bad[:3])
            if "league_ms_le4" in m:
                ms, basis = m["league_ms_le4"], f"league median at ≤4 plays (n = {m['league_n_le4']})"
            else:
                ms, basis = m["est_ms"], m["est_basis"]
            est = (f"{n * ms / 60000:.1f} [INFERENCE: {n} × {ms:g} ms, {basis}; one request at a time; server "
                   f"start/handover not included]")
        else:
            est = ("10–140 [INFERENCE: no (on) league record; 438 requests at 16 in parallel × 22.6 s (Gemma 4 E4B (on), "
                   "median 2,100 output tokens) to 303 s (LFM2.5-24B-A2B (on), median 17,168); output cap 32,768]")
        out.append(f"| {m['name']} | {m['kind']} | yes | {n} | {est} | {m['server']} |")
        for i in its:
            body = (i["state"] + i["instructions"] + "".join(t for _, t in i["options"])) if m["kind"] == "decision" \
                else (i["system"] + i["user"])
            rows.append((key, m["name"], m["kind"], i["id"], kind(i["id"]), len(i["options"]), len(body)))
    if requests_tsv:
        with open(requests_tsv, "w") as f:
            f.write("key\tsetup\tform\titem_id\tquestion\toptions\tprompt_chars\n")
            for r in rows:
                f.write("\t".join(map(str, r)) + "\n")
    per = Counter(r[0] for r in rows)
    by_q = Counter((r[0], r[4]) for r in rows)
    print("| model | form | runnable | requests | est. GPU minutes | server |\n|---|---|---|---:|---|---|")
    print("\n".join(out))
    print(f"\nrequests listed: {len(rows)} ({len(per)} runnable models × "
          f"{', '.join(f'{q} {by_q[(next(iter(per)), q)]}' for q in EXPECTED)})")
    return rows


# ---- frozen scoring: parse_json and pick are p2rep.py's (workspace/clearrisk-scratch/p2rep.py, 30 Oct), verbatim;
# only `ans`, `items`, `invalid`, `ties` and CHAT are module state filled by score().
ans, ITEM, invalid, ties, CHAT = {}, {}, defaultdict(int), defaultdict(int), set()


def parse_json(text):
    if text is None:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def pick(model, item_id):
    """Chosen option value of a choice item, or None (missing, failed, invalid, tie)."""
    a = ans.get((model, item_id))
    if a is None or a[3] is not None:
        invalid[(model, "failed or missing")] += 1; return None
    it = ITEM[item_id]
    if model in CHAT:
        j = parse_json(a[2]); ch = j.get("choice") if isinstance(j, dict) else None
        vals = [v for v, _ in it["options"]]
        labels = [str(i + 1) for i in range(len(vals))] if item_id.split(":")[1] == "Q2" else list("ABCD"[: len(vals)])
        if ch not in labels:
            invalid[(model, "invalid")] += 1; return None
        return vals[labels.index(ch)]
    probs = a[1] or {}
    if a[0] is None or not probs:
        invalid[(model, "invalid")] += 1; return None
    top = max(probs.values())
    if sum(p == top for p in probs.values()) > 1:
        ties[model] += 1; return None
    return max(probs, key=probs.get)


def pct(n, d):
    return f"{100 * n / d:.0f}% ({n}/{d})" if d else "– (0)"


def score(db, setups=None):
    """Q1/Q2 counts per (model, version) as p2rep.py's R (q1_* and q2_* keys), and the markdown report."""
    import sqlite3
    ans.clear(); ITEM.clear(); invalid.clear(); ties.clear(); CHAT.clear()
    CHAT.update(PART2_CHAT | {m["name"] for m in models().values() if m["kind"] == "chat"})
    ITEM.update({i["id"]: i for i in items()})
    meta = {int(k): v for k, v in json.loads(META.read_text()).items()}
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    ans.update({(s, i): (ch, json.loads(p) if p else None, t, e) for s, i, ch, p, t, e in
                c.execute("SELECT setup, item_id, choice, probabilities, text, error FROM quiz_answers")})
    stored = {s: (n, f) for s, n, f in c.execute(
        "SELECT setup, COUNT(*), SUM(error IS NOT NULL) FROM quiz_answers WHERE item_id NOT LIKE '%:Q3:%' GROUP BY setup")}
    setups = setups or sorted(stored)
    R = {}
    for model in setups:
        for version in ("numbers", "board"):
            r = R[(model, version)] = defaultdict(int)
            for sid, m in meta.items():
                g = "R" if m["grp"] == "Risk wins" else "S"
                ch = pick(model, f"{sid}:Q1:{version}")
                if ch is not None:
                    r[f"q1_{g}_n"] += 1
                    r[f"q1_{g}_right"] += ch == m["q1"]["right"]
                    r[f"q1_{g}_safe"] += ch == m["q1"]["safe"]
                    r[f"q1_{g}_unsafe"] += ch == m["q1"]["unsafe"]
                    r["q1_A"] += ch == m["q1"]["order"][0]; r["q1_answered"] += 1
                r[f"q1_{g}_items"] += 1
                if "order" in m["q2"] and version == "board":
                    c2 = pick(model, f"{sid}:Q2:board")
                    r["q2_items"] += 1; r["q2_right"] += c2 == m["q2"]["rights"][0]
    md = ["### Q1: share right per group, missed and needless, bias (two plays shown, not league play)\n",
          "| model | version | Risk wins right | Safety wins right | missed (Risk wins → safe) | needless (Safety wins → "
          "unsafe) | bias | share of A answers | Q1 not answered |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for model in setups:
        for version in ("numbers", "board"):
            r = R[(model, version)]
            mi = r["q1_R_safe"] / r["q1_R_n"] if r["q1_R_n"] else None
            ne = r["q1_S_unsafe"] / r["q1_S_n"] if r["q1_S_n"] else None
            bias = f"{100 * (mi - ne):+.0f} pp" if mi is not None and ne is not None else "–"
            unanswered = r["q1_R_items"] + r["q1_S_items"] - r["q1_R_n"] - r["q1_S_n"]
            md.append(f"| {model} | {'with numbers' if version == 'numbers' else 'board only'} | "
                      f"{pct(r['q1_R_right'], r['q1_R_n'])} | {pct(r['q1_S_right'], r['q1_S_n'])} | "
                      f"{pct(r['q1_R_safe'], r['q1_R_n'])} | {pct(r['q1_S_unsafe'], r['q1_S_n'])} | {bias} | "
                      f"{pct(r['q1_A'], r['q1_answered'])} | {unanswered} |")
    md += ["\n### Q2 (board only): share right vs random\n", "| model | right | random baseline |", "|---|---:|---:|"]
    md += [f"| {m} | {pct(R[(m, 'board')]['q2_right'], R[(m, 'board')]['q2_items'])} | 25% (4 options, one right) |"
           for m in setups]
    md += ["\n### Invalid-answer share (Q1 + Q2)\n",
           "| model | expected requests | answer rows | request errors | invalid answers | exact ties (decision) | "
           "usable | invalid share (of rows without a request error) | no-answer share (errors + invalid + ties, of "
           "expected) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    expected = sum(EXPECTED.values())
    for m in setups:
        n, failed = stored.get(m, (0, 0))
        missing = invalid[(m, "failed or missing")]
        bad, tie = invalid[(m, "invalid")], ties[m]
        answered = n - failed
        md.append(f"| {m} | {expected} | {n} | {failed} | {bad} | {tie} | {expected - missing - bad - tie} | "
                  f"{pct(bad, answered)} | {pct(missing + bad + tie, expected)} |")
    return R, "\n".join(md) + "\n"


def main(argv):
    cmd = argv[0] if argv else "help"
    if cmd == "check-items":
        check_items(argv[1] if len(argv) > 1 else ROOT / "workspace" / "clearrisk-scratch")
    elif cmd == "player":
        print(json.dumps(player(argv[1]), indent=1))
    elif cmd == "config":
        base = argv[argv.index("--base-url") + 1] if "--base-url" in argv else None
        config(argv[1], argv[2], base)
    elif cmd == "plan":
        plan(argv[argv.index("--requests") + 1] if "--requests" in argv else None)
    elif cmd == "score":
        setups = [argv[k + 1] for k, a in enumerate(argv) if a == "--setup"]
        print(score(argv[1], setups or None)[1], end="")
    elif cmd == "field":  # one field of models.json for shell scripts: field KEY NAME
        m = models()[argv[1]]
        print(m.get(argv[2], "") if argv[2] != "time_limit" else TIME_LIMIT[m["kind"]])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
