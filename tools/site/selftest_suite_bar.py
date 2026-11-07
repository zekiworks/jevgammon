#!/usr/bin/env python3
"""Self-test of the suite strip's one exception to the private-strings check (check 4, checks.scan_file; Ümit, bus #2270;
Zeki, bus #2287, #2310): writes small files to a temp dir and runs the check's own per-file scan on each, and on the
HTML pages the link check as run() does.

    python3 tools/site/selftest_suite_bar.py

  1. the shared strip (common.SUITE_BAR) exactly as published, in an HTML page's sticky header: passes both checks;
  2. the same address or the same link outside the strip, with the strip present or not: fails;
  3. a strip that differs from the shared one (its link text, its address, or the current site marked on another link):
     fails;
  4. the exact strip twice on one page: the second one fails (the exception holds once per page);
  5. the exact strip in a file that is not an HTML page (a data JSON file, a text file, an .html.gz file and a .json.gz
     file, scanned decompressed): fails, as any other occurrence.
Exit 0 when every case comes out as expected; 1 otherwise. Writes nothing outside a temp dir."""

import gzip
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks  # noqa: E402
from common import SUITE_BAR  # noqa: E402

OUTSIDE_LINK = '<p><a href="/analysis/decision-models/">English &amp; Turkish Reading</a></p>'
OUTSIDE_TEXT = '<p>See https://zekiworks.github.io/analysis/decision-models/ for the reading test.</p>'


def page(body: str) -> str:
    return (f'<!doctype html><html lang="en"><head><title>t</title></head><body><div class="site-header">{body}</div>'
            f'<main id="main"><p>Page</p></main></body></html>')


# (name, file name, file bytes, expected to pass)
CASES = [
    ("1 the exact shared strip in an HTML page", "index.html", page(SUITE_BAR).encode(), True),
    ("2a the strip's first link outside the strip", "index.html", page(SUITE_BAR + OUTSIDE_LINK).encode(), False),
    ("2b the address in the page text", "index.html", page(SUITE_BAR + OUTSIDE_TEXT).encode(), False),
    ("2c the link alone, no strip", "index.html", page(OUTSIDE_LINK).encode(), False),
    ("3a strip with other link text", "index.html",
     page(SUITE_BAR.replace("English &amp; Turkish Reading", "English Reading")).encode(), False),
    ("3b strip with another address", "index.html",
     page(SUITE_BAR.replace('href="/analysis/decision-models/"', 'href="/analysis/decision-models/method/"')).encode(), False),
    ("3c strip marking another site", "index.html",
     page(SUITE_BAR.replace(' aria-current="page"', "").replace(
         '<a href="/analysis/logic/">', '<a href="/analysis/logic/" aria-current="page">')).encode(), False),
    ("4 the exact strip twice", "index.html", page(SUITE_BAR + SUITE_BAR).encode(), False),
    ("5a the exact strip in a data JSON file", "data.json", json.dumps({"header": SUITE_BAR}).encode(), False),
    ("5b the exact strip in a text file", "notes.txt", SUITE_BAR.encode(), False),
    ("5c the exact strip in an .html.gz file (scanned decompressed)", "page.html.gz", gzip.compress(page(SUITE_BAR).encode()), False),
    ("5d the exact strip in a .json.gz file (scanned decompressed)", "decisions.json.gz",
     gzip.compress(json.dumps({"html": SUITE_BAR}).encode()), False),
]


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for name, fname, data, should_pass in CASES:
            f = out / fname
            f.write_bytes(data)
            banned = checks.scan_file(f)
            links = []
            if f.suffix == ".html":
                tree = checks.Tree()
                tree.feed(checks.without_suite_bar(f.read_text()))
                links = checks.check_links(f, tree.root, out)
            passed = banned is None and not links
            why = (f"banned {banned.group(0)!r}" if banned else "") + (f" {len(links)} unresolved links" if links else "")
            good = passed == should_pass
            ok &= good
            print(f"{'ok  ' if good else 'FAIL'} {name}: {'passes' if passed else 'fails'}"
                  f"{' (' + why.strip() + ')' if why else ''}; expected to {'pass' if should_pass else 'fail'}")
            f.unlink()
    print("all cases as expected" if ok else "SOME CASES NOT AS EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
