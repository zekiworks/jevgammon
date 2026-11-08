"""File-level invariance inventory of two whole-site renders (render_site.py, production mode): origin/main's
tools/site against the branch's, same state (STATE/learning with the exploratory file), same results hash. A changed
file is explained only if undoing the branch's expected changes, one named rule at a time, gives main's file back byte
for byte; the rules applied are its "why". The learning page and its data file are the change under review ("subject":
checked by 02 and 03, not by a rule). Anything else is "unexplained".

    python3 invariance.py OUT_MAIN OUT_BRANCH CSV SUMMARY
"""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

A, B, csv_path, summary_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
ADDED = {}
SUBJECT = {"learning/index.html": "the learning page: the change under review (Ümit #2950/#2952; 02, 03)",
           "data/v3/learning-pilot.json": "the learning page's data file: the change under review (02, 03)"}
LEARNING_DATA = "data/v3/learning-pilot.json"
MARK_END = "\n\n/* --- Dashboard layout"
DATA_ROW = re.compile(r'<tr><td><a href="\.\./data/v3/learning-pilot\.json">data/v3/learning-pilot\.json</a></td>'
                      r'.*?</tr>', re.S)


def css_region(t: str, start: str) -> tuple[int, int]:
    i = t.find(start)
    return (i, t.find(MARK_END, i)) if i >= 0 else (-1, -1)


def bg_css_learning_block(t: str) -> str:
    """Puts main's Learning block of bg.css back in place of the branch's (the whole block, as main has it)."""
    i, j = css_region(t, "/* The Learning page's charts")
    m = (A / "bg.css").read_text()
    mi, mj = css_region(m, "/* The Learning page's charts")
    if i < 0 or mi < 0:
        return t
    return t[:i] + m[mi:mj] + t[j:]


def data_page_row(t: str) -> str:
    """Puts main's row for the learning data file back (its size and hash change with the file; nothing else)."""
    m = DATA_ROW.search((A / "data/index.html").read_text())
    return DATA_ROW.sub(lambda _: m.group(0), t, count=1) if m else t


HOME_CHART = re.compile(r'<figure class="lp-chart" id="finding-learning-chart">.*?</figure>', re.S)


def home_learning_chart(t: str) -> str:
    """Puts main's learning chart of the home page's finding f back (learning_page.risks_figure, shared with the
    learning page: the arms' display names in its legend, table and note, and the model in its title)."""
    m = HOME_CHART.search((A / "index.html").read_text())
    return HOME_CHART.sub(lambda _: m.group(0), t, count=1) if m else t


# (name, applies to, undo).
RULES = [
    ("bg.css: the Learning block gains the top line's and the exploratory block's rules (4 lines)", "bg.css",
     bg_css_learning_block),
    ("data page: the size and hash of data/v3/learning-pilot.json", "data/index.html", data_page_row),
    ("home page, finding f: the learning page's risks chart (shared code) with the arms' display names and the model "
     "in its title", "index.html", home_learning_chart),
]


def applies(scope: str, rel: str) -> bool:
    return rel.endswith(scope) if scope.startswith(".") else rel == scope


def explain(rel: str, a: bytes, b: bytes) -> tuple[str, str]:
    if rel in SUBJECT:
        return "subject", SUBJECT[rel]
    if rel == "data/manifest.json":
        ma, mb = json.loads(a), json.loads(b)
        strip = lambda m: dict(m, files=[f for f in m["files"] if f["path"] != LEARNING_DATA])  # noqa: E731
        return (("explained", f"manifest: the entry of {LEARNING_DATA} (its size and hash)") if strip(ma) == strip(mb)
                else ("unexplained", ""))
    try:
        t, want = b.decode(), a.decode()
    except UnicodeDecodeError:
        return "unexplained", "binary file differs"
    used = []
    for name, scope, undo in RULES:
        if applies(scope, rel):
            u = undo(t)
            if u != t:
                used.append(name)
                t = u
    return ("explained", "; ".join(used)) if t == want else ("unexplained", "after: " + "; ".join(used))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


fa = {str(p.relative_to(A)) for p in A.rglob("*") if p.is_file()}
fb = {str(p.relative_to(B)) for p in B.rglob("*") if p.is_file()}
rows = []
for rel in sorted(fa | fb):
    pa, pb = A / rel, B / rel
    if rel not in fb:
        status, why = "unexplained", "only in main's render"
    elif rel not in fa:
        status, why = ("added", ADDED[rel]) if rel in ADDED else ("unexplained", "only in the branch's render")
    elif pa.read_bytes() == pb.read_bytes():
        status, why = "identical", ""
    else:
        status, why = explain(rel, pa.read_bytes(), pb.read_bytes())
    rows.append([rel, sha(pa), sha(pb), status, why])
with csv_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["path", "sha256_main", "sha256_branch", "status", "why"])
    w.writerows(rows)
counts = Counter(r[3] for r in rows)
reasons = Counter(r[4] for r in rows if r[3] == "explained")
lines = [f"main render:   {A} ({len(fa)} files)", f"branch render: {B} ({len(fb)} files)", ""]
lines += [f"{k}: {v}" for k, v in sorted(counts.items())]
lines += ["", "explained changes, by reason (files):"] + [f"  {n:5d}  {r}" for r, n in reasons.most_common()]
lines += ["", "the change under review (subject):"] + [f"  {r[0]}: {r[4]}" for r in rows if r[3] == "subject"]
lines += ["", f"unexplained: {counts.get('unexplained', 0)}"] + [f"  {r[0]}: {r[4]}" for r in rows if r[3] == "unexplained"]
summary_path.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if counts.get("unexplained") else 0)
