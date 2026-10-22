#!/usr/bin/env python3
"""Candidate positions for the hero board (Can's follow-up to brief v6 B3). Reads a built site's decision files,
picks three candidates by fixed rules, and renders each as the hero would look (1280 px, dark and light). The site
itself is not changed: build.showcase keeps its rule until a candidate is chosen.

    python3 tools/site/hero_candidates.py BUILD_DIR OUT_DIR

Rules (B6 classes and numbers exactly as exported to Every decision; programs left out):
  A  typical Risk pays where most setups went wrong. Only the v1 set has many setups on the same position (league
     games give every setup different positions), so A is an Earlier-version position: among the v1 Risk pays
     positions whose best-safe-play loss lies between the 40th and 60th percentile, the one where the largest share
     of the valid answers played safe (ties: closest to the median, then lowest id).
  B  typical Safety pays: League 3 (latest finished), a model took a needless risk; the decision whose equity lost
     is closest to the median loss of all such decisions (ties: lowest id).
  C  middle of the road: League 3, a Risk pays decision in which the model took the risk with the engine's best
     play; best-safe-play loss closest to the median of all League 3 Risk pays decisions (ties: lowest id).
Writes OUT_DIR/candidates.json (numbers), OUT_DIR/hero-<A|B|C>-<dark|light>.png.
"""

import gzip
import json
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pages  # noqa: E402

LEAGUE = "league-3"


def decisions(build: Path, ds: str):
    idx = json.loads((build / "decisions/index.json").read_text())
    entry = next(x for x in idx["datasets"] if x["id"] == ds)
    for s in entry["setups"]:
        if s.get("program"):
            continue
        for p in range(1, s["pages"] + 1):
            doc = json.loads(gzip.decompress((build / "decisions" / ds / s["slug"] / f"{p}.json.gz").read_bytes()))
            for d in doc["decisions"]:
                if not d["program"] and d.get("risk"):
                    yield s["slug"], p, d


def gap(d) -> float:
    hr = [p["hitting_rolls"] for p in d["plays"]]
    return min(p["loss"] for p, h in zip(d["plays"], hr) if h == min(hr))


def pct_rank(values: list[float], v: float) -> float:
    return sum(1 for x in values if x <= v) / len(values)


def closest(items, target, key):
    return min(items, key=lambda it: (abs(key(it) - target), it[2]["id"] if isinstance(it[2]["id"], int) else 0))


def candidate_a(build: Path) -> dict:
    by_pos = defaultdict(list)
    for sl, p, d in decisions(build, "v1-set"):
        by_pos[d["id"]].append((sl, p, d))
    risk = {pid: rows for pid, rows in by_pos.items() if rows[0][2]["risk"]["class"] == "risk"}
    gaps = {pid: gap(rows[0][2]) for pid, rows in risk.items()}
    q = statistics.quantiles(sorted(gaps.values()), n=10)
    lo, hi, med = q[3], q[5], statistics.median(gaps.values())
    pool = [pid for pid, g in gaps.items() if lo <= g <= hi]
    wrong = {pid: sum(1 for _, _, d in risk[pid] if not d["risk"]["took"]) for pid in pool}
    pid = min(pool, key=lambda i: (-wrong[i] / len(risk[i]), abs(gaps[i] - med), str(i)))
    rows = risk[pid]
    safe = [r for r in rows if not r[2]["risk"]["took"]]
    common = max({r[2]["plays"][r[2]["chosen"]]["notation"] for r in safe},
                 key=lambda n: (sum(1 for r in safe if r[2]["plays"][r[2]["chosen"]]["notation"] == n), n))
    sl, p, d = next(r for r in safe if r[2]["plays"][r[2]["chosen"]]["notation"] == common)
    who = f"{len(safe)} of the {len(rows)} setups that answered it"
    sc = pages.hero_numbers(d, "Earlier version (v1 set), the same position for every setup", who, sl, p, earlier=True)
    sc["why"] = (f"Typical Risk pays position (best-safe-play loss at the {100 * pct_rank(list(gaps.values()), gaps[pid]):.0f}th "
                 f"percentile of the {len(gaps):,} v1 Risk pays positions) where most setups went wrong: {len(safe)} of "
                 f"{len(rows)} played safe; the most common safe play, {common}, was chosen by "
                 f"{sum(1 for r in safe if r[2]['plays'][r[2]['chosen']]['notation'] == common)}.")
    sc["setups_safe"], sc["setups_answered"] = len(safe), len(rows)
    sc["setups_took_best"] = sum(1 for r in rows if r[2]["chosen"] == r[2]["best"])
    return sc


def league_rows(build: Path):
    return list(decisions(build, LEAGUE))


def candidate_b(rows) -> dict:
    pool = [r for r in rows if r[2]["risk"]["class"] == "safety" and r[2]["risk"]["took"]]
    losses = [r[2]["plays"][r[2]["chosen"]]["loss"] for r in pool]
    med = statistics.median(losses)
    sl, p, d = closest(pool, med, lambda r: r[2]["plays"][r[2]["chosen"]]["loss"])
    sc = pages.hero_numbers(d, "League 3", d["setup"], sl, p)
    sc["why"] = (f"Typical Safety pays decision gone wrong: of the {len(pool):,} League 3 decisions where a model took a "
                 f"needless risk, the median equity lost is {med:.3f}; this one loses {sc['chosen']['loss']:.3f}.")
    return sc


def candidate_c(rows) -> dict:
    risk = [r for r in rows if r[2]["risk"]["class"] == "risk"]
    med = statistics.median(gap(r[2]) for r in risk)
    pool = [r for r in risk if r[2]["risk"]["took"] and r[2]["chosen"] == r[2]["best"]]
    sl, p, d = closest(pool, med, lambda r: gap(r[2]))
    sc = pages.hero_numbers(d, "League 3", d["setup"], sl, p)
    sc["why"] = (f"Middle of the road: a Risk pays decision with the median stake (best-safe-play loss {med:.3f} is the "
                 f"median of the {len(risk):,} League 3 Risk pays decisions; this one {sc['best_safe']['loss']:.3f}), "
                 f"and the model got it right: it took the risk with the engine's best play.")
    return sc


def render(build: Path, out: Path, cands: dict) -> None:
    from playwright.sync_api import sync_playwright
    home = (build / "index.html").read_text()
    start = home.index('<figure class="hero-board"')
    end = home.index("</figure>", start) + len("</figure>")
    tmp = out / "_site"
    tmp.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "bg.css", "decisions.css", "site.js", "tables.js", "bg.js"):
        shutil.copy(build / name, tmp / name)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for key, sc in cands.items():
            (tmp / f"{key}.html").write_text(home[:start] + pages.hero_figure(sc) + home[end:])
            for scheme in ("dark", "light"):
                page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
                page.goto((tmp / f"{key}.html").as_uri())
                page.wait_for_timeout(300)
                page.locator("header.hero").screenshot(path=str(out / f"hero-{key}-{scheme}.png"))
                page.close()
        browser.close()
    shutil.rmtree(tmp)


def main():
    build, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = league_rows(build)
    cands = {"A": candidate_a(build), "B": candidate_b(rows), "C": candidate_c(rows)}
    keep = ("why", "label", "who", "dataset", "id", "slug", "page", "phase", "dice", "kind", "took", "min_risk",
            "best", "best_safe", "chosen", "setups_safe", "setups_answered", "setups_took_best")
    (out / "candidates.json").write_text(json.dumps({k: {f: v[f] for f in keep if f in v} for k, v in cands.items()},
                                                    indent=1, ensure_ascii=False) + "\n")
    render(build, out, cands)
    print(json.dumps({k: {f: v[f] for f in ("dataset", "id", "kind", "took", "why") if f in v} for k, v in cands.items()},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
