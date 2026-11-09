"""narrow.py BASE NEW OUT: the changed parts of the three changed files, one tag per line, as unified diffs."""
import difflib
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

base, new, out = (Path(a) for a in sys.argv[1:4])
tags = lambda html: re.sub(r">\s*<", ">\n<", html).splitlines()  # noqa: E731


def part(path, sel):
    s = BeautifulSoup((path).read_text(), "html.parser")
    return "\n".join(str(e) for e in s.select(sel))


for name, rel, sel in (("render-front.diff", "index.html", "main > section.hero-card, #findings"),
                       ("render-about.diff", "about/index.html", "nav.face-nav, section#front-page")):
    a, b = tags(part(base / rel, sel)), tags(part(new / rel, sel))
    (out / name).write_text("\n".join(difflib.unified_diff(a, b, f"origin/main/{rel}", f"declutter/{rel}", lineterm="", n=1)) + "\n")
a, b = (base / "bg.css").read_text().splitlines(), (new / "bg.css").read_text().splitlines()
(out / "render-bg.css.diff").write_text("\n".join(difflib.unified_diff(a, b, "origin/main/bg.css", "declutter/bg.css", lineterm="", n=1)) + "\n")
