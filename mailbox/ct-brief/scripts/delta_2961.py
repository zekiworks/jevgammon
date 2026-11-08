"""Zeki #2961 delta: every file of the 2c41357 render against the ace14d5 render (gz decompressed); the only change may
be the home page's #finding-nackgammon section. Prints its old and new heading and text, and checks that every number in
the new section was in the old one (no new number)."""
import gzip, re, sys
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
a, b = Path(sys.argv[1]), Path(sys.argv[2])
fa = {p.relative_to(a) for p in a.rglob("*") if p.is_file()}
fb = {p.relative_to(b) for p in b.rglob("*") if p.is_file()}
diff = []
for r in sorted(fa & fb):
    x, y = (a / r).read_bytes(), (b / r).read_bytes()
    if r.suffix == ".gz":
        x, y = gzip.decompress(x), gzip.decompress(y)
    if x != y:
        diff.append(str(r))
print("files only in one:", sorted(map(str, fa ^ fb)))
print("files differing:", diff)
sa, sb = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (a, b))
ea, eb = sa.find(id="finding-nackgammon"), sb.find(id="finding-nackgammon")
ea.extract(); eb.extract()
same_rest = str(sa) == str(sb)
print("home page outside #finding-nackgammon identical:", same_rest)
t = lambda e: re.sub(r"\s+", " ", e.get_text(" ")).strip()
for n, e in (("old", ea), ("new", eb)):
    print(f"{n} heading:", t(e.find("h2"))); print(f"{n} text:", t(e.find(class_="finding-text")))
num = lambda s: Counter(x.rstrip(",") for x in re.findall(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?", s))
extra = num(t(eb)) - num(t(ea))
# "99": the comparisons' interval level (nack-paired.json primary_level / ci_99), now named; checks.run traces it.
level = {k: v for k, v in extra.items() if k == "99"}
extra = {k: v for k, v in extra.items() if k != "99"}
print("interval level now named:", level)
print("numbers in the new section not in the old one:", dict(extra))
ok = not (fa ^ fb) and diff == ["index.html"] and same_rest and not extra
print("delta check:", "ok" if ok else "FAILED"); sys.exit(0 if ok else 1)
