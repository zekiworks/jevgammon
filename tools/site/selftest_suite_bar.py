#!/usr/bin/env python3
"""Self-test of the suite strip's one exception to the private-strings check (checks.banned_in, check 4; Ümit, bus #2270;
Zeki, bus #2287): writes small pages to a temp dir and runs the private-strings scan and the link check on each.

    python3 tools/site/selftest_suite_bar.py

  1. the shared strip (common.SUITE_BAR) exactly as published, in the page's sticky header: passes both checks;
  2. the same address or the same link outside the strip, with the strip present or not: fails;
  3. a strip that differs from the shared one (its link text, its address, or the current site marked on another link):
     fails;
  4. the exact strip twice on one page: the second one fails (the exception holds once per page).
Exit 0 when every case comes out as expected; 1 otherwise. Writes nothing outside a temp dir."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks  # noqa: E402
from common import SUITE_BAR  # noqa: E402

OUTSIDE_LINK = '<p><a href="/analysis/decision-models/">English &amp; Turkish Reading</a></p>'
OUTSIDE_TEXT = '<p>See https://zekiworks.github.io/analysis/decision-models/ for the reading test.</p>'
CASES = [
    ("1 the exact shared strip", SUITE_BAR, True),
    ("2a the strip's first link outside the strip", SUITE_BAR + OUTSIDE_LINK, False),
    ("2b the address in the page text", SUITE_BAR + OUTSIDE_TEXT, False),
    ("2c the link alone, no strip", OUTSIDE_LINK, False),
    ("3a strip with other link text", SUITE_BAR.replace("English &amp; Turkish Reading", "English Reading"), False),
    ("3b strip with another address", SUITE_BAR.replace('href="/analysis/decision-models/"',
                                                        'href="/analysis/decision-models/method/"'), False),
    ("3c strip marking another site", SUITE_BAR.replace(' aria-current="page"', "").replace(
        '<a href="/analysis/logic/">', '<a href="/analysis/logic/" aria-current="page">'), False),
    ("4 the exact strip twice", SUITE_BAR + SUITE_BAR, False),
]


def page(body: str) -> str:
    return (f'<!doctype html><html lang="en"><head><title>t</title></head><body><div class="site-header">{body}</div>'
            f'<main id="main"><p>Page</p></main></body></html>')


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for name, body, should_pass in CASES:
            f = out / "index.html"
            f.write_text(page(body))
            text = f.read_text()
            banned = checks.banned_in(text)
            tree = checks.Tree()
            tree.feed(checks.without_suite_bar(text))
            links = checks.check_links(f, tree.root, out)
            passed = banned is None and not links
            why = (f"banned {banned.group(0)!r}" if banned else "") + (f" links {links}" if links else "")
            good = passed == should_pass
            ok &= good
            print(f"{'ok  ' if good else 'FAIL'} {name}: {'passes' if passed else 'fails'}"
                  f"{' (' + why.strip() + ')' if why else ''}; expected to {'pass' if should_pass else 'fail'}")
    print("all cases as expected" if ok else "SOME CASES NOT AS EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
