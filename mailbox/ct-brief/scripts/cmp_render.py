"""Compare two site trees: every file present in both, .gz decompressed, HTML compared as visible text with the
results/as-of stamp lines kept. Prints identical counts and the differing files (with a short text diff for HTML)."""
import difflib, gzip, sys
from pathlib import Path
from bs4 import BeautifulSoup
a, b = Path(sys.argv[1]), Path(sys.argv[2]); show = int(sys.argv[3]) if len(sys.argv) > 3 else 6
skip = ("results/", "archive/")
fa = {p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()}
fb = {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()}
txt = lambda p: [l for l in BeautifulSoup(p.read_text(), "html.parser").get_text("\n").split("\n") if l.strip()]
same = 0; diff = []
for r in sorted(fa & fb):
    if r.startswith(skip): continue
    x, y = (a / r).read_bytes(), (b / r).read_bytes()
    if r.endswith(".gz"): x, y = gzip.decompress(x), gzip.decompress(y)
    if x == y: same += 1; continue
    diff.append(r)
print(f"only in {a}: {len([r for r in fa - fb if not r.startswith(skip)])}; only in {b}: {sorted(r for r in fb - fa if not r.startswith(skip))[:40]}")
print(f"identical {same}; differ {len(diff)}")
for r in diff:
    print("##", r)
    if r.endswith(".html"):
        d = [l for l in difflib.unified_diff(txt(a / r), txt(b / r), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        for l in d[:show]: print("   ", l[:200])
        if len(d) > show: print(f"    … {len(d) - show} more")
