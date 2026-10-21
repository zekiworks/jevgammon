"""Smoke-test tables from the answers `jevgammon ask` stored and GNUbg's equities of the smoke
positions. Standard library only.

v3 rosters (design, run order step 1), one row per setup of leagues/league*.json:

    python3 tools/v3/smoke_report.py smoke/answers.db smoke/score.db > table.md

Columns: answers stored and failed requests; probabilities returned (logprobs or a decision
model's distribution, else choice only); median and 90th-percentile request seconds (retries
excluded); invalid share (random play made); mean input, output and reasoning tokens per
decision; dollars per 1,000 decisions (provider-reported or list price); error rate (mean 2-ply
equity loss x 500, invalid answers scored by the random play made); best-play share (loss <
0.001); blunder share (> 0.08).

Candidate setups with intervals and paired differences (Part A of the site brief):

    python3 tools/v3/smoke_report.py paired --score smoke/score.db \\
        --setups leagues/smoke-parta.json=smoke/part-a.db \\
        --reference "Gemini 3.8 Flash (low) [antigravity]=smoke/part-a.db" \\
        --reference "Gemini 3.8 Flash (low)=smoke/answers.db" [--json out.json]

One row per player of each config (answers from the db after `=`). Error rate here counts valid
answers only (an invalid answer's random play is not the model's choice) with a 95% bootstrap
interval over positions; failed requests and decisions over the time limit (`timed out`) are
counted apart. Each reference adds a column: the paired difference in error rate (setup minus
reference) on the positions both answered validly, with a 95% bootstrap interval over those
positions (10,000 resamples, fixed seed). Request seconds exclude retries and waits, which are
shown apart. Dollars per 1,000 decisions: provider-reported cost (OpenRouter, as billed) where
it is above zero, else tokens x the config's list price (subscriptions, free endpoints).
"""

import argparse
import json
import random
import sqlite3
import statistics
import sys

BOOTSTRAP = 10_000
TIMED_OUT = "timed out"


def pct(values, q):
    values = sorted(values)
    if not values:
        return None
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def fmt(x, spec):
    return "–" if x is None else format(x, spec)


def main():
    answers, score = sys.argv[1], sys.argv[2]
    db = sqlite3.connect(f"file:{answers}?mode=ro", uri=True)
    db.execute("ATTACH DATABASE ? AS s", (f"file:{score}?mode=ro",))
    rosters = []
    for n in (1, 2, 3):
        with open(f"leagues/league{n}.json") as f:
            for p in json.load(f)["players"]:
                rosters.append((n, p))
    print("| League | Setup | Reasoning | Answers | Failed | Probabilities | p50 s | p90 s | Invalid | "
          "Tokens in / out / reasoning | $ per 1,000 | Error rate | Best play | Blunders |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    seen = set()
    for league, p in rosters:
        name = p["name"]
        if name in seen:
            continue
        seen.add(name)
        rows = db.execute(
            """SELECT a.request_ms, a.invalid, a.input_tokens, a.output_tokens, a.reasoning_tokens,
                      a.cost_usd, a.probability_source, e.loss
               FROM answers a LEFT JOIN s.equities e ON e.position = a.position_id AND e.play = a.move
               WHERE a.setup = ? AND a.error IS NULL""", (name,)).fetchall()
        failed = db.execute("SELECT COUNT(*), MAX(error) FROM answers WHERE setup = ? AND error IS NOT NULL",
                            (name,)).fetchone()
        chat = p["spec"].split("/")[0] in ("openai-compatible", "local", "openai", "anthropic", "gemini", "ollama")
        effort = p.get("reasoning") or ("off" if chat else "–")
        if not rows:
            reason = (failed[1] or "not run")[:90].replace("|", "/")
            print(f"| {league} | {name} | {effort} | 0 | {failed[0]} | blocked: {reason} | | | | | | | | |")
            continue
        n = len(rows)
        secs = [r[0] / 1000 for r in rows]
        invalid = sum(1 for r in rows if r[1]) / n
        sources = {r[6] for r in rows} - {None}
        probs = ("yes" if sources & {"logprobs", "decision"} and "choice_only" not in sources else
                 "partly" if sources & {"logprobs", "decision"} else
                 "choice only" if "choice_only" in sources else "none (engine)")
        tin = statistics.mean(r[2] or 0 for r in rows)
        tout = statistics.mean(r[3] or 0 for r in rows)
        rts = [r[4] for r in rows if r[4] is not None]
        reasoning = fmt(statistics.mean(rts), ".0f") if rts else "n/a"
        costs = [r[5] for r in rows if r[5] is not None]
        per_k = statistics.mean(costs) * 1000 if costs else None
        losses = [r[7] for r in rows if r[7] is not None]
        err = statistics.mean(losses) * 500 if losses else None
        best = sum(1 for x in losses if x < 0.001) / len(losses) if losses else None
        blunder = sum(1 for x in losses if x > 0.08) / len(losses) if losses else None
        print(f"| {league} | {name} | {effort} | {n} | {failed[0]} | {probs} | {pct(secs, .5):.1f} | "
              f"{pct(secs, .9):.1f} | {invalid:.0%} | {tin:.0f} / {tout:.0f} / {reasoning} | "
              f"{fmt(per_k, '.2f')} | {fmt(err, '.1f')} | {fmt(best, '.0%')} | {fmt(blunder, '.0%')} |")


def bootstrap_mean(values, seed):
    """Mean and 95% percentile-bootstrap interval of `values` (resampled with replacement)."""
    if not values:
        return None, None, None
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(BOOTSTRAP))
    return statistics.mean(values), means[int(0.025 * BOOTSTRAP)], means[int(0.975 * BOOTSTRAP) - 1]


def setup_answers(db_path, name):
    """Rows of one setup, by position: valid answers with their 2-ply loss, plus the rest."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db.execute("SELECT * FROM answers WHERE setup = ? AND repeat = 1", (name,)).fetchall()


def losses(rows, score):
    out = {}
    for r in rows:
        if r["error"] is None and not r["invalid"]:
            loss = score.get((r["position_id"], r["move"]))
            if loss is not None:
                out[r["position_id"]] = loss
    return out


def summarize(name, player, rows, score, references):
    answered = [r for r in rows if r["error"] is None]
    timed_out = sum(1 for r in rows if r["error"] and r["error"].startswith(TIMED_OUT))
    failed = sum(1 for r in rows if r["error"] and not r["error"].startswith(TIMED_OUT))
    n = len(answered)
    own = losses(rows, score)
    seed = sum(map(ord, name))
    err, lo, hi = bootstrap_mean([v * 500 for v in own.values()], seed)
    sources = {r["probability_source"] for r in answered} - {None}
    probs = ("letter logprobs" if sources == {"logprobs"} else
             "decision model" if sources == {"decision"} else
             "none (choice only)" if sources == {"choice_only"} else
             "mixed: " + ", ".join(sorted(sources)) if sources else "–")
    groups = sorted({r["group_size"] for r in answered if r["group_size"]})
    price = player.get("price") or {}
    costs = []
    for r in answered:
        if r["cost_usd"]:
            costs.append(r["cost_usd"])
        elif price:
            costs.append(((r["input_tokens"] or 0) * price["input_per_mtok"]
                          + (r["output_tokens"] or 0) * price["output_per_mtok"]) / 1e6)
    rts = [r["reasoning_tokens"] for r in answered if r["reasoning_tokens"] is not None]
    row = {
        "setup": name,
        "spec": player["spec"],
        "provider": player.get("provider"),
        "quantization": player.get("quantization"),
        "reasoning": player.get("reasoning") or "off",
        "run_dates": sorted({r["created_at"][:10] for r in rows}),
        "harness": sorted({(r["harness_commit"] or "")[:8] + ("+dirty" if r["harness_dirty"] else "")
                           for r in rows}),
        "asked": len(rows),
        "answered": n,
        "failed": failed,
        "timed_out": timed_out,
        "invalid": sum(1 for r in answered if r["invalid"]),
        "probabilities": probs,
        "group_sizes": groups,
        "request_s_p50": pct([r["request_ms"] / 1000 for r in answered], .5),
        "request_s_p90": pct([r["request_ms"] / 1000 for r in answered], .9),
        "retry_s_mean": statistics.mean(r["retry_ms"] / 1000 for r in answered) if answered else None,
        "retry_s_max": max((r["retry_ms"] / 1000 for r in answered), default=None),
        "tokens_in": statistics.mean(r["input_tokens"] or 0 for r in answered) if answered else None,
        "tokens_out": statistics.mean(r["output_tokens"] or 0 for r in answered) if answered else None,
        "tokens_reasoning": statistics.mean(rts) if rts else None,
        "usd_per_1000": statistics.mean(costs) * 1000 if costs else None,
        "usd_total": sum(costs),
        "error_positions": len(own),
        "error_rate": err,
        "error_ci": [lo, hi],
        "best_play": sum(1 for v in own.values() if v < 0.001) / len(own) if own else None,
        "blunders": sum(1 for v in own.values() if v > 0.08) / len(own) if own else None,
        "paired": [],
    }
    for ref_name, ref in references:
        common = sorted(own.keys() & ref.keys())
        d, dlo, dhi = bootstrap_mean([(own[p] - ref[p]) * 500 for p in common], seed + 1)
        row["paired"].append({"reference": ref_name, "positions": len(common), "diff": d,
                              "ci": [dlo, dhi]})
    return row


def paired(argv):
    parser = argparse.ArgumentParser(prog="smoke_report.py paired")
    parser.add_argument("--score", required=True)
    parser.add_argument("--setups", action="append", required=True, metavar="CONFIG=DB")
    parser.add_argument("--reference", action="append", default=[], metavar="SETUP=DB")
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    sdb = sqlite3.connect(f"file:{args.score}?mode=ro", uri=True)
    score = {(p, m): loss for p, m, loss in sdb.execute("SELECT position, play, loss FROM equities")}
    references = []
    for item in args.reference:
        name, db_path = item.rsplit("=", 1)
        references.append((name, losses(setup_answers(db_path, name), score)))
    out = []
    for item in args.setups:
        config, db_path = item.rsplit("=", 1)
        with open(config) as f:
            players = json.load(f)["players"]
        for p in players:
            rows = setup_answers(db_path, p["name"])
            if rows:
                out.append(summarize(p["name"], p, rows, score, references))
    refs = " | ".join(f"Δ vs {name} [95% CI]" for name, _ in references)
    print(f"| Setup | Answers / failed / timed out | Invalid | Probabilities | Groups | p50 / p90 s | "
          f"Retry+wait s mean / max | Tokens in / out / reasoning | $ per 1,000 | Error rate [95% CI] | "
          f"{refs} |")
    print("|" + " --- |" * (10 + len(references)))
    for r in out:
        diffs = " | ".join(
            f"{fmt(d['diff'], '+.1f')} [{fmt(d['ci'][0], '+.1f')}, {fmt(d['ci'][1], '+.1f')}] (n={d['positions']})"
            for d in r["paired"])
        print(f"| {r['setup']} | {r['answered']} / {r['failed']} / {r['timed_out']} | "
              f"{r['invalid'] / r['answered']:.0%} | {r['probabilities']} | "
              f"{','.join(map(str, r['group_sizes'])) or 'one request'} | "
              f"{fmt(r['request_s_p50'], '.1f')} / {fmt(r['request_s_p90'], '.1f')} | "
              f"{fmt(r['retry_s_mean'], '.1f')} / {fmt(r['retry_s_max'], '.1f')} | "
              f"{fmt(r['tokens_in'], '.0f')} / {fmt(r['tokens_out'], '.0f')} / {fmt(r['tokens_reasoning'], '.0f')} | "
              f"{fmt(r['usd_per_1000'], '.2f')} | "
              f"{fmt(r['error_rate'], '.1f')} [{fmt(r['error_ci'][0], '.1f')}, {fmt(r['error_ci'][1], '.1f')}] | "
              f"{diffs} |")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["paired"]:
        paired(sys.argv[2:])
    else:
        main()
