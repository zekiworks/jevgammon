"""Smoke-test table (design, run order step 1): one row per setup of leagues/league*.json from the
answers `jevgammon ask` stored and GNUbg's equities of the smoke positions.

    python3 tools/v3/smoke_report.py smoke/answers.db smoke/score.db > table.md

Columns: answers stored and failed requests; probabilities returned (logprobs or a decision model's
distribution, else choice only); median and 90th-percentile request seconds (retries excluded);
invalid share (random play made); mean input, output and reasoning tokens per decision; dollars per
1,000 decisions (provider-reported or list price); error rate (mean 2-ply equity loss x 500, invalid
answers scored by the random play made); best-play share (loss < 0.001); blunder share (> 0.08).
Standard library only.
"""

import json
import sqlite3
import statistics
import sys


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


if __name__ == "__main__":
    main()
