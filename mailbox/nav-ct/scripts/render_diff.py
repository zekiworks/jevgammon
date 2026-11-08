"""Every file of the two retained renders: identical, or (HTML) differing only by the tab row's id="view-part"."""
import sys
from pathlib import Path
a, b = Path(sys.argv[1]), Path(sys.argv[2])
fa = {p.relative_to(a) for p in a.rglob("*") if p.is_file()}
fb = {p.relative_to(b) for p in b.rglob("*") if p.is_file()}
same = idonly = 0; other = []
for r in sorted(fa & fb):
    x, y = (a / r).read_bytes(), (b / r).read_bytes()
    if x == y: same += 1
    elif x.replace(b'<nav class="site-tabs" aria-label', b'<nav class="site-tabs" id="view-part" aria-label') == y: idonly += 1
    else: other.append(str(r))
print(f"{len(fa)} / {len(fb)} files; only in one: {sorted(map(str, fa ^ fb))}")
print(f"identical {same}; differing only by the tab row's id=\"view-part\" {idonly}; other differences: {other}")
sys.exit(0 if not (fa ^ fb) and set(other) <= {"bg.js", "bg.css"} else 1)
