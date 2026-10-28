#!/usr/bin/env python3
"""Nackgammon paired test: check every published value against its sources. Exit 1 on any mismatch.

    python3 tools/site/nack_paired_verify.py OUT_DIR RESULTS_JSON [--rollouts DB | --saved-only]

OUT_DIR is a built site (build.py --out); RESULTS_JSON the scorer's output (positions/nack-paired/results/results.json);
--rollouts the engine-check rollout database, needed once results.json has an engine check (as for the scorer). Checked:
- the site's data file (OUT_DIR/data/v3/nack-paired.json) equals content/nack_paired_results.json, which equals
  nack_paired_publish.build() of RESULTS_JSON and of a fresh recomputation (tools/v3/nack_paired_score.py report run
  into a temporary directory from the scored data); the fresh results.json equals RESULTS_JSON;
- the data file holds no position ids or answers;
- on the home page: every table cell with data-k (each printed number equals its data-file value at the printed
  decimals; yes/no and labels as text), the rows of every table, the fixed row order (group, then standard PR), every
  header unsortable, every chart point and its group class, the legend; the scope note verbatim and equal to the
  scorer's; the §10.14(e) groups note and the frontier note verbatim after every table of primary comparisons, and
  the frontier note next to every scope note; setups with no group labelled "no group (exploratory)"; the reading and
  prompt notes, no forbidden wording;
- the Method page: every heading, paragraph, list item (nested and lettered too) and table cell of §10 through §10.14
  (with both dated notes) from the spec file;
- no private artifact anywhere in OUT_DIR (local addresses, ports 8894/8095, artifact:// links, the answers database,
  keys).
--saved-only skips the fresh recomputation: every published value is checked against the frozen RESULTS_JSON only (no
scorer run, the answers database is not read).
"""

import argparse
import contextlib
import gzip
import html
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent.parent
sys.path.insert(0, str(SITE))

import nack_section as NS  # noqa: E402
from checks import Tree, text_of, walk  # noqa: E402
from common import BANNED, CONTENT, NACK_SCOPE_NOTE, esc  # noqa: E402
from method import nack_spec_text  # noqa: E402
from nack_paired_publish import GROUP_ORDER, build  # noqa: E402

NUM = re.compile(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?")
# Anywhere in the build (the existing data/setups.json names smoke/part-a.json as a source: public, not this run's).
PRIVATE = re.compile(r"smoke/nack|smoke/[\w.-]+\.db|127\.0\.0\.1|localhost|:8894\b|:8095\b|artifact://|nack-paired\.db|"
                     r"\bsk-[\w-]{8}|api[_-]key|Bearer [\w.-]{8}")
FORBIDDEN = re.compile(r"memori[sz]|trained on", re.I)


def norm(s: str) -> str:
    return " ".join(s.split())


def leaves(v) -> list:
    if isinstance(v, list):
        return [x for e in v for x in leaves(e)]
    return [v]


def check_cell(text: str, vals: list) -> str | None:
    nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for v in vals:
        if isinstance(v, bool) and ("yes" if v else "no") not in text:
            return f"{v!r} not shown"
        if isinstance(v, str) and v not in text:
            return f"{v!r} not shown"
    shown = NUM.findall(text if not any(isinstance(v, str) for v in vals)
                        else text.replace(next(v for v in vals if isinstance(v, str)), ""))
    if len(shown) != len(nums):
        return f"{len(shown)} numbers shown, {len(nums)} expected"
    for tok, v in zip(shown, nums):
        x = float(tok.replace("\u2212", "-").replace(",", ""))
        d = len(tok.split(".")[1]) if "." in tok else 0
        if x != round(float(v), d) and not (d == 0 and x == v):
            return f"{tok} shown for {v!r}"
    return None


def fresh_results(rollouts: str | None) -> dict:
    sys.path.insert(0, str(ROOT / "tools/v3"))
    import nack_paired_score as S
    with tempfile.TemporaryDirectory() as tmp:
        S.OUT = tmp
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                S.report(argparse.Namespace(rollouts=rollouts))
        finally:
            os.chdir(cwd)
        return json.loads((Path(tmp) / "results.json").read_text())


def check_home(out: Path, N: dict, bad: list):
    tree = Tree()
    tree.feed((out / "index.html").read_text())
    secs = [n for n in walk(tree.root) if n.attrs.get("id") == NS.SECTION_ID]
    if len(secs) != 1:
        bad.append(f"home page: {len(secs)} Nackgammon sections")
        return
    sec = secs[0]
    text = norm(text_of(sec))
    for want in (NACK_SCOPE_NOTE, NS.READING, NS.PROMPT_NOTE, NS.TITLE):
        if want not in text:
            bad.append(f"home page: {want!r} missing")
    if text.count(NACK_SCOPE_NOTE) < 4:
        bad.append("home page: the scope note is not next to every group result")
    for k in ("scope_note", "groups_rule", "frontier_note"):
        if N[k] not in text:
            bad.append(f"home page: {k} {N[k]!r} missing")
    if N["scope_note"] != NACK_SCOPE_NOTE:
        bad.append(f"scope note: published {NACK_SCOPE_NOTE!r}, scorer {N['scope_note']!r}")
    if FORBIDDEN.search(text):
        bad.append(f"home page: forbidden wording {FORBIDDEN.search(text).group(0)!r}")
    order = list(N["setups"])
    want_order = sorted(order, key=lambda s: (GROUP_ORDER.index(N["setups"][s]["group"]),
                                              N["setups"][s]["first"]["standard_pr"], s))
    if order != want_order:
        bad.append("data file: setups not in group, standard-PR order")
    tables = [n for n in walk(sec) if n.tag == "table"]
    seen = 0
    for t in tables:
        tid, src = t.attrs.get("id"), t.attrs.get("data-src")
        if src is None:
            bad.append(f"home table {tid}: no data-src")
            continue
        if any(n.tag == "th" and n.attrs.get("scope") == "col" and "data-nosort" not in n.attrs for n in walk(t)):
            bad.append(f"home table {tid}: a header can be sorted")
        coll = NS.resolve(N, N, src)
        rows = [n for n in walk(t) if n.tag == "tr" and "data-row" in n.attrs]
        keys = [r.attrs["data-row"] for r in rows]
        if src == "setups":
            want = [s for s in order if tid not in ("nack-cost", "nack-risk-main", "nack-risk-all")
                    or (tid == "nack-cost" and N["setups"][s]["cost"])
                    or (tid.startswith("nack-risk") and N["setups"][s]["risk"][tid[10:]])]
            if keys != want:
                bad.append(f"home table {tid}: rows {keys} != {want}")
        elif isinstance(coll, list) and keys != [str(i) for i in range(len(coll))]:
            bad.append(f"home table {tid}: rows {keys} != {len(coll)} entries")
        elif isinstance(coll, dict) and src != "" and src != "secondary" and keys != list(coll):
            bad.append(f"home table {tid}: rows {keys} != {list(coll)}")
        for r in rows:
            rec = NS.resolve(N, N, "/".join(p for p in (src, r.attrs["data-row"]) if p))
            for c in walk(r):
                if c.tag != "td" or "data-k" not in c.attrs:
                    continue
                seen += 1
                vals = [x for p in c.attrs["data-k"].split("|") for x in leaves(NS.resolve(N, rec, p))
                        if x is not None]
                err = check_cell(norm(text_of(c)), vals)
                if err:
                    bad.append(f"home table {tid} row {r.attrs['data-row']} [{c.attrs['data-k']}]: {err}")
    if not seen:
        bad.append("home page: no checked cells")
    pts = {g.attrs["data-setup"]: g for g in walk(sec) if g.tag == "g" and "data-setup" in g.attrs}
    if list(pts) != [p["setup"] for p in N["chart"]]:
        bad.append(f"chart: points {list(pts)} != {[p['setup'] for p in N['chart']]}")
    for p in N["chart"]:
        s = N["setups"][p["setup"]]
        if (p["standard_pr"], p["nackgammon_pr"]) != (s["first"]["standard_pr"], s["first"]["nackgammon_pr"]):
            bad.append(f"chart data {p['setup']}: not the first-look PRs")
        g = pts.get(p["setup"])
        if g is not None and (float(g.attrs["data-x"]), float(g.attrs["data-y"])) != (p["standard_pr"], p["nackgammon_pr"]):
            bad.append(f"chart {p['setup']}: ({g.attrs['data-x']}, {g.attrs['data-y']}) != data")
    for yard in ("GNUbg weak", "Random"):
        if yard in N["setups"] and yard not in pts:
            bad.append(f"chart: {yard} not marked")
    for name, g in pts.items():
        group = N["setups"][name]["group"] if name in N["setups"] else None
        want = "nack-yard" if group == "yardstick" else NS.GROUP_CLASS.get(group)
        if not any(want in (n.attrs.get("class") or "").split() for n in walk(g)):
            bad.append(f"chart {name}: not drawn as {group!r}")
    legend = " ".join(norm(text_of(n)) for n in walk(sec) if "chart-legend" in (n.attrs.get("class") or ""))
    for group in {v["group"] for v in N["setups"].values()} - {"yardstick"}:
        if group not in legend:
            bad.append(f"chart legend: {group!r} missing")
    for s, v in N["setups"].items():
        if v["group"] == "no group (exploratory)":
            ths = [norm(text_of(n)) for n in walk(sec) if n.tag == "th" and n.parent is not None
                   and n.parent.attrs.get("data-row") == s]
            if not ths or any("no group (exploratory)" not in t for t in ths):
                bad.append(f"home tables: {s} not labelled 'no group (exploratory)'")
    # §10.14: the groups-rule note and the frontier note, verbatim, right after every table of primary comparisons.
    page = (out / "index.html").read_text()
    notes = (f'<p class="table-note nack-groups-rule">{esc(N["groups_rule"])}</p>'
             f'<p class="table-note nack-frontier-note">{esc(N["frontier_note"])}</p>')
    tids = [f"nack-primary-{r}" for r in ("random", "worst", "drop")] + (["nack-engine-primary"] if N["engine_check"] else [])
    for tid in tids:
        at = page.find(f'id="{tid}"')
        end = page.find("</table></div>", at) + len("</table></div>")
        if at < 0 or not page.startswith(notes, end):
            bad.append(f"home table {tid}: the \u00a710.14(e) groups note and the frontier note do not follow it verbatim")
    if text.count(N["frontier_note"]) < text.count(NACK_SCOPE_NOTE) + len(tids):
        bad.append("home page: the frontier note is not next to every scope note and every primary table")


def spec_items(md: str) -> list[str]:
    """Plain text of every heading, paragraph, list item and table cell of the spec text (marks removed)."""
    out, cur = [], []

    def flush():
        if cur:
            out.append(" ".join(cur))
            cur.clear()
    for line in md.splitlines():
        if not line.strip():
            flush()
        elif line.startswith("#"):
            flush()
            out.append(line.lstrip("#").strip())
        elif line.startswith("|"):
            flush()
            out += [c.strip() for c in line.strip().strip("|").split("|") if not set(c.strip()) <= {"-"}]
        elif re.match(r"\s*(- |\d+\. |[a-z]\) )", line):
            flush()
            cur.append(re.sub(r"^\s*(- |\d+\. )", "", line).strip())
        else:
            cur.append(line.strip())
    flush()
    return [norm(re.sub(r"\*\*|`|(?<![\w*])\*|\*(?![\w*])", "", s)) for s in out if s.strip()]


def check_method(out: Path, bad: list):
    page = (out / "method/index.html").read_text()
    starts = [m.start() for m in re.finditer(f'<section [^>]*id="{NS.SECTION_ID}"', page)]
    if len(starts) != 1:
        bad.append(f"method page: {len(starts)} Nackgammon sections")
        return
    sec = page[starts[0]:page.index("</section>", starts[0])]
    text = norm(html.unescape(re.sub(r"<[^>]+>", "", sec)))  # document order (checks.text_of is not)
    spec = nack_spec_text()
    items = spec_items(spec)
    for it in items:
        if it not in text:
            bad.append(f"method page: spec text missing: {it[:90]!r}")
    for note in ("Standard prompt (note to 10.8, Can's answer 2):", "Back-game tag (note to 10.4, Can's answer 3):"):
        if note not in text:
            bad.append(f"method page: dated note {note!r} missing")
    if NACK_SCOPE_NOTE not in text:
        bad.append("method page: scope note missing")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("results")
    ap.add_argument("--rollouts")
    ap.add_argument("--saved-only", action="store_true",
                    help="check against the frozen RESULTS_JSON only; no recomputation from the answers")
    args = ap.parse_args()
    out, bad = Path(args.out), []
    N = json.loads((CONTENT / "nack_paired_results.json").read_text())
    site = json.loads((out / "data/v3/nack-paired.json").read_text())
    if site.pop("version", None) != "v3" or site != N:
        bad.append("data/v3/nack-paired.json differs from content/nack_paired_results.json")
    R = json.loads(Path(args.results).read_text())
    if build(R) != N:
        bad.append(f"content/nack_paired_results.json differs from nack_paired_publish.build({args.results})")
    if args.saved_only:
        print("saved-only: no recomputation; checked against the frozen results file only")
    elif R.get("engine_check") and not args.rollouts:
        bad.append("results.json has an engine check: pass --rollouts DB for the recomputation")
    else:
        F = fresh_results(args.rollouts)
        if F != R:
            diff = sorted(k for k in set(F) | set(R) if F.get(k) != R.get(k))
            who = sorted(s for s in set(F.get("setups", {})) | set(R.get("setups", {}))
                         if F.get("setups", {}).get(s) != R.get("setups", {}).get(s))
            bad.append(f"fresh recomputation differs from {args.results} in {diff} (setups: {who}); if the run is "
                       f"still answering, re-run report, publish and build, then verify")
        if build(F) != N:
            bad.append("content/nack_paired_results.json differs from the fresh recomputation")
    dump = json.dumps(N)
    if "smoke/" in dump:
        bad.append("data file names a smoke/ path")
    for pat in (r"\bnp[ns]?-\d{4}\b", r'"(move|raw|answer|response|position_id|request_ms)"'):
        if re.search(pat, dump):
            bad.append(f"data file holds per-position data ({pat})")
    check_home(out, N, bad)
    check_method(out, bad)
    for p in out.rglob("*"):
        if not p.is_file() or p.suffix == ".png":
            continue
        data = (gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()).decode("utf-8", "replace")
        for rx in (PRIVATE, BANNED):
            m = rx.search(data)
            if m:
                bad.append(f"{p.relative_to(out)}: private string {m.group(0)!r}")
    for b in bad:
        print("MISMATCH", b)
    print(f"nackgammon paired test: {len(N['setups'])} setups; {'OK' if not bad else f'{len(bad)} mismatches'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
