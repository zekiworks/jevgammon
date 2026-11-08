"""File-level invariance inventory of two whole-site renders (render_site.py): origin/main's tools/site against the branch's,
same state, same results hash. A changed file is explained only if undoing the branch's expected markup changes, one
named rule at a time, gives main's file back byte for byte; the rules applied are its "why". Anything else is
"unexplained". Numbers are never rewritten by a rule, so a number change can only show up as unexplained.

    python3 invariance.py OUT_MAIN OUT_BRANCH CSV SUMMARY
"""
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

A, B, csv_path, summary_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
ADDED = {}
MARK_END = "\n\n/* --- Dashboard layout"


def css_region(t: str, start: str) -> tuple[int, int]:
    i = t.find(start)
    return (i, t.find(MARK_END, i)) if i >= 0 else (-1, -1)


def bg_css_learning_block(t: str) -> str:
    """Puts main's Learning-chart block of bg.css back in place of the branch's (the whole block, as main has it)."""
    i, j = css_region(t, "/* The Learning page's charts")
    m = (A / "bg.css").read_text()
    mi, mj = css_region(m, "/* The Learning tab's chart")
    if i < 0 or mi < 0:
        return t
    return t[:i] + m[mi:mj] + t[j:]


# (name, applies to, undo). Main already has the Learning page (pre-registration only, 89c0f01); this branch changes,
# outside the page's results view (not rendered by the default build), only bg.css's Learning-chart block.
RULES = [
    ("bg.css: the Learning charts' block (arm colours from learning_page.ARM_COLOUR as --lp, control's dashed swatch, "
     "the charts stacked with their tables, the status line and the lessons' series boxes)", "bg.css",
     bg_css_learning_block),
]


def applies(scope: str, rel: str) -> bool:
    return rel.endswith(scope) if scope.startswith(".") else rel == scope


def explain(rel: str, a: bytes, b: bytes) -> tuple[str, str]:
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
lines += ["", f"unexplained: {counts.get('unexplained', 0)}"] + [f"  {r[0]}: {r[4]}" for r in rows if r[3] == "unexplained"]
summary_path.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if counts.get("unexplained") else 0)
