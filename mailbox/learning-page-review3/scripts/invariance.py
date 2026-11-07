"""File-level invariance inventory of two whole-site renders (render_site.py): main's tools/site against the branch's,
same state, same results hash. A changed file is explained only if undoing the branch's expected markup changes, one
named rule at a time, gives main's file back byte for byte; the rules applied are its "why". Anything else is
"unexplained". Numbers are never rewritten by a rule, so a number change can only show up as unexplained.

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
OLD_TITLE = "Can a model tell when a risk is worth taking?"
NEW_TITLE = "Backgammon: do models take the right risks, and do they learn from their games?"
ADDED = {"learning/index.html": "the new Learning across games page",
         "data/v3/learning-pilot.json": "the new page's data file (aggregates only)"}


def sub(pattern, repl="", flags=0, count=0):
    rx = re.compile(pattern, flags)
    return lambda t: rx.sub(repl, t, count=count)


def css_block(start: str, n_lines: int):
    """Removes the n lines starting with `start` (one added CSS block)."""
    def f(t):
        i = t.find(start)
        if i < 0:
            return t
        j = i
        for _ in range(n_lines):
            j = t.index("\n", j) + 1
        return t[:i] + t[j:]
    return f


# (name, applies to, undo): HTML rules for every page, then the home page's own, then the data page's, then CSS.
RULES = [
    ("site title (new home title; the <title>, social tags, meta description and data-site-title of every page)",
     ".html", lambda t: t.replace(NEW_TITLE, OLD_TITLE)),
    ("Part row in the view bar (Risk calls / Learning across games, on every page)", ".html",
     sub(r'<div class="view-row view-tests view-parts".*?</ul></div>', count=1, flags=re.S)),
    ("view bar label names the Part row", ".html",
     lambda t: t.replace('aria-label="View: part, league, models and measure"',
                         'aria-label="View: league, models and measure"').replace('aria-label="View: part"',
                                                                                  'aria-label="View"')),
    ("Analyses nav link to learning/", ".html",
     sub(r'<li><a href="(?:\.\./)*learning/"(?: aria-current=page)?>Learning from experience \(preliminary, '
         r'running\)</a></li>', count=1)),
    ("home: the four main links under the title", "index.html",
     sub(r'\n\s*<nav class="hero-links" aria-label="Main parts">.*?</nav>', count=1, flags=re.S)),
    ("home: 'How the numbers work' (Method sentences)", "index.html",
     sub(r'\n\s*<section class="card how-numbers" id="how-numbers">.*?</section>', count=1, flags=re.S)),
    ("home: ranking note under the risk judgement chart (Zeki #2578)", "index.html",
     sub(r'<p class="table-note">Ranks show observed scores; small gaps need not be meaningful\.</p>', count=1)),
    ("data page: row for data/v3/learning-pilot.json", "data/index.html",
     sub(r'<tr><td><a href="\.\./data/v3/learning-pilot\.json">data/v3/learning-pilot\.json</a></td>'
         r'<td class="num">[\d,]+</td><td><code>[0-9a-f]{12}</code></td></tr>', count=1)),
    ("site.css: hero links, how-numbers, blockquote and phone Part-row rules", "site.css",
     lambda t: css_block("  .view-row.view-parts ul", 2)(css_block("blockquote {", 2)(
         css_block("/* The home page's main links under the title", 8)(t)))),
    ("bg.css: the Learning chart's arm colours and the tab rule box", "bg.css",
     css_block("/* The Learning tab's chart", 10)),
]


def applies(scope: str, rel: str) -> bool:
    return rel.endswith(scope) if scope.startswith(".") else rel == scope


def explain(rel: str, a: bytes, b: bytes) -> tuple[str, str]:
    if rel == "data/manifest.json":
        ma, mb = json.loads(a), json.loads(b)
        if ma == dict(mb, files=[f for f in mb["files"] if f["path"] != "data/v3/learning-pilot.json"]):
            return "explained", "manifest entry for data/v3/learning-pilot.json"
        return "unexplained", ""
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
