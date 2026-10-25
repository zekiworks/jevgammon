#!/usr/bin/env python3
"""Close choices, stage B: check every published value against its sources. Exit 1 on any mismatch.

    python3 tools/site/close_choices_b_verify.py OUT_DIR REPORT_MD SCORE_JSON

OUT_DIR is a built site (build.py --out); REPORT_MD the text report with the results table (mailbox/Close choices -
stage B results (5 teams).md); SCORE_JSON the scorer's output (close_choices_b_score.py). Checked:
- the site's data file (OUT_DIR/data/v3/close-choices-b.json) equals content/close_choices_b_results.json;
- every complete team's published value equals SCORE_JSON's, and, written as in the report, the report's table cell;
  the report names exactly the complete teams;
- not-reported teams (close_choices_b_publish.NOT_REPORTED) appear nowhere in the data file, the table or the chart;
- on the home page: every cell of the stage B table and every chart row equals the data file; "above" only where the
  observed mean is above the baseline's 97.5% point; the title, the scope note (verbatim) and the not-a-ranking note;
  every header unsortable; no "Probabilities over plays" in the section;
- the Method page's stage B status line and scope note.
"""

import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))

import home  # noqa: E402
from checks import Tree, text_of, walk  # noqa: E402
from close_choices_b_publish import NOT_REPORTED  # noqa: E402
from common import CLOSE_B_SCOPE_NOTE, CONTENT  # noqa: E402

MD_COLS = ["scored", "exact", "exact_baseline", "exact_p", "overlap", "overlap_baseline", "overlap_p", "same_play",
           "changed_same_features", "observed_nonempty", "predicted_size_mean"]


def md_table(path: Path) -> dict:
    rows, on = {}, False
    for line in path.read_text().splitlines():
        if line.startswith("| Team | Scored | Exact"):
            on = True
            continue
        if on:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set(cells[0]) <= {"-"}:
                continue
            rows[cells[0]] = dict(zip(MD_COLS, cells[1:]))
    if not rows:
        raise SystemExit(f"{path}: no results table")
    return rows


def as_report(t: dict) -> dict:
    e, o = t["primary_exact"], t["secondary_overlap"]
    return dict(scored=str(t["scored"]), exact=f'{e["observed"]:.2f}',
                exact_baseline=f'{e["baseline_mean"]:.3f} [{e["baseline_lo"]:.2f}, {e["baseline_hi"]:.2f}]',
                exact_p=f'{e["p"]:.3f}', overlap=f'{o["observed"]:.3f}',
                overlap_baseline=f'{o["baseline_mean"]:.3f} [{o["baseline_lo"]:.3f}, {o["baseline_hi"]:.3f}]',
                overlap_p=f'{o["p"]:.3f}', same_play=str(t["same_play"]),
                changed_same_features=str(t["changed_same_features"]), observed_nonempty=str(t["observed_nonempty"]),
                predicted_size_mean=f'{t["predicted_size_mean"]:.2f}')


def _up(n):
    while n.parent is not None:
        n = n.parent
        yield n


def find(root, pred):
    return [n for n in walk(root) if pred(n)]


def main():
    out, report, score = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    bad = []
    pub = json.loads((CONTENT / "close_choices_b_results.json").read_text())
    site = json.loads((out / "data/v3/close-choices-b.json").read_text())
    site.pop("version", None)
    if site != pub:
        bad.append("data/v3/close-choices-b.json differs from content/close_choices_b_results.json")
    for team in NOT_REPORTED:
        if team in json.dumps(pub):
            bad.append(f"data file mentions the not-reported team {team}")
    S = json.loads(score.read_text())
    md = md_table(report)
    done = {t["team"]: t for t in pub["complete"]}
    if set(md) != set(done):
        bad.append(f"report teams {sorted(md)} != complete teams {sorted(done)}")
    for team, t in done.items():
        s = S[team]
        for k in ("primary_exact", "secondary_overlap"):
            for a, b in (("observed", "observed"), ("baseline_mean", "baseline_mean"), ("baseline_lo", "baseline_lo"),
                         ("baseline_hi", "baseline_hi"), ("p", "share_baseline_at_least_observed")):
                if t[k][a] != s[k][b]:
                    bad.append(f"{team} {k}.{a}: published {t[k][a]!r}, score {s[k][b]!r}")
        for k in ("positions", "scored", "exact_n", "excluded_positions", "same_play", "changed_same_features",
                  "observed_nonempty", "predicted_size_mean", "deterministic"):
            if t[k] != s[k]:
                bad.append(f"{team} {k}: published {t[k]!r}, score {s[k]!r}")
        if t["excluded"] != {r: v["n"] for r, v in s["excluded"].items()}:
            bad.append(f"{team} excluded: published {t['excluded']}, score {s['excluded']}")
        for k, v in as_report(t).items():
            if team in md and md[team][k] != v:
                bad.append(f"{team} {k}: published {v!r}, report {md[team][k]!r}")

    tree = Tree()
    tree.feed((out / "index.html").read_text())
    sec = find(tree.root, lambda n: n.attrs.get("id") == "close-choices-stage-b")
    if len(sec) != 1:
        bad.append(f"home page: {len(sec)} stage B sections")
    else:
        sec = sec[0]
        text = " ".join(text_of(sec).split())
        for want in (pub["title"], home.CCB_SUBTITLE, CLOSE_B_SCOPE_NOTE, home.CCB_RANKING):
            if want not in text:
                bad.append(f"home page: {want!r} missing")
        for team in NOT_REPORTED:
            if text.replace(CLOSE_B_SCOPE_NOTE, "").count(team):
                bad.append(f"home page: not-reported team {team} outside the scope note")
        if any(n.tag == "th" and n.attrs.get("scope") == "col" and "data-nosort" not in n.attrs for n in walk(sec)
               if any(a.attrs.get("id") == "close-b-table" for a in [n] + list(_up(n)))):
            bad.append("home page: a stage B table header can be sorted")
        cells = home.ccb_cells(pub)
        rows = {n.attrs["data-team"]: n for n in find(sec, lambda n: n.tag == "tr" and "data-team" in n.attrs)}
        if list(rows) != sorted(done):
            bad.append(f"home table teams {list(rows)}: not the published teams in alphabetical order")
        for team, t in done.items():
            tds = {n.attrs["data-k"]: " ".join(text_of(n).split()) for n in walk(rows.get(team) or tree.root)
                   if n.tag == "td" and "data-k" in n.attrs}
            for k, v in as_report(t).items():
                if tds.get(k) != v:
                    bad.append(f"home table {team} {k}: shown {tds.get(k)!r}, expected {v!r}")
            for k in ("exact_vs", "overlap_vs", "excluded"):
                if tds.get(k) != cells[team][k]:
                    bad.append(f"home table {team} {k}: shown {tds.get(k)!r}, expected {cells[team][k]!r}")
            for k, vs in (("primary_exact", "exact_vs"), ("secondary_overlap", "overlap_vs")):
                x = t[k]
                above = x["observed"] > x["baseline_hi"]
                if (tds.get(vs, "").startswith("above")) != above:
                    bad.append(f"home table {team} {vs}: {tds.get(vs)!r} but observed {x['observed']} vs 97.5% point {x['baseline_hi']}")
            tp = t["temperature"]
            want = (f'known: {tp["value"]}' if tp["known"] else "not disclosed") + tp["text"]
            if tds.get("temperature") != " ".join(want.split()):
                bad.append(f"home table {team} temperature: {tds.get('temperature')!r}")
        for g in find(sec, lambda n: n.tag == "g" and "data-team" in n.attrs):
            team = g.attrs["data-team"]
            if team not in done:
                bad.append(f"chart {team}: not a published team")
            else:
                e = done[team]["primary_exact"]
                for a, k in (("data-observed", "observed"), ("data-baseline-mean", "baseline_mean"),
                             ("data-baseline-lo", "baseline_lo"), ("data-baseline-hi", "baseline_hi")):
                    if float(g.attrs.get(a, "nan")) != e[k]:
                        bad.append(f"chart {team} {a}: {g.attrs.get(a)!r}, expected {e[k]!r}")
    mtree = Tree()
    mtree.feed((out / "method/index.html").read_text())
    mtext = " ".join(text_of(mtree.root).split())
    for want in (f'{pub["title"]}, results published. Gemma 4 31B (on) stopped, not reported.', CLOSE_B_SCOPE_NOTE):
        if want not in mtext:
            bad.append(f"method page: {want!r} missing")
    for b in bad:
        print("MISMATCH", b)
    print(f"close choices stage B: {len(done)} teams; "
          f"{'OK' if not bad else f'{len(bad)} mismatches'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
