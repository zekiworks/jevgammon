#!/usr/bin/env python3
"""Self-test of the Leagues page's Starting groups (ZEKI-BG-STARTING-GROUPS-CORRECTION, Ümit 31 Oct 2026), on a built
page, offline (reads files only; no server, no build).

    python3 tools/site/selftest_starting_groups.py LEAGUES_PAGE [--before OLD_LEAGUES_PAGE]

Checks:
  1. the three groups are named exactly Decision, Workhorse, Frontier (heading and table caption);
  2. the subtitle element is exactly "Groups reflect model profiles, not tournament rankings." and the cohort
     explanation is a separate note element right after it;
  3. GNUbg weak has a row in all three group tables and its later-league starting group reads all three groups;
  4. Safest and Random have rows in the Decision table only, and their later-league starting group is the original
     League 1 only;
  5. with --before: the two pages are identical once the display labels this correction may change are masked (group
     names, the subtitle and cohort note, the Starting group cells of the later leagues), so every recorded number,
     move, badge, link and id is unchanged.
Exit 0 when every check passes; prints each check."""

import argparse
import html
import re
import sys
from pathlib import Path

NAMES = {1: "Decision", 2: "Workhorse", 3: "Frontier"}
text = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def group_section(page: str) -> str:
    return page[page.index('<section class="card" id="starting-groups">'):page.index('<section class="card" id="after-league-moves">')]


def group_rows(sec: str, lid: int) -> list[str]:
    i = sec.index(f'<h3 id="group-{lid}">')
    j = sec.index(f'<h3 id="group-{lid + 1}">') if lid < 3 else len(sec)
    body = re.search(r"<tbody>(.*?)</tbody>", sec[i:j], re.S).group(1)
    return re.findall(r"<tr\b.*?</tr>", body, re.S)


def later_rows(page: str, lid: int) -> list[list[str]]:
    s = page[page.index(f'<section class="card" id="league-{lid}"'):]
    body = re.search(r"<tbody>(.*?)</tbody>", s, re.S).group(1)
    return [re.findall(r"<td[^>]*>.*?</td>", r, re.S) for r in re.findall(r"<tr\b.*?</tr>", body, re.S)]


def row_name(cells_or_row) -> str:
    s = cells_or_row if isinstance(cells_or_row, str) else cells_or_row[0]
    return html.unescape(re.search(r'class="model-name"[^>]*>([^<]*)<', s).group(1))


def mask(page: str) -> str:
    """The page with the display labels this correction may change replaced by a placeholder."""
    page = re.sub(r'(<h3 id="group-\d">).*?(<span class="small inline">)', r"\1LABEL \2", page)
    page = re.sub(r"<caption>(?:Decision models|Workhorses|Frontier|Decision|Workhorse): the original League",
                  "<caption>LABEL: the original League", page)
    page = re.sub(r'<p class="subtitle-line">.*?</p>(<p class="note cohort-note">.*?</p>)?', "SUBTITLE", page, flags=re.S)
    for lid in (1, 2, 3):
        a = page.index(f'<section class="card" id="league-{lid}"')
        b = page.index("</tbody>", a)
        # The Starting group cell: the one cell without attributes after the To play cell, up to its own </td>.
        body = re.sub(r'(<td class="num">\d+</td>)<td>(?:(?!</td>).)*</td>(<td class="badges">|<td></td>)',
                      r"\1<td>LABEL</td>\2", page[a:b], flags=re.S)
        page = page[:a] + body + page[b:]
    return page


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("page", type=Path)
    ap.add_argument("--before", type=Path)
    args = ap.parse_args()
    page = args.page.read_text()
    sec = group_section(page)
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(f'{"PASS" if ok else "FAIL"}  {name}{": " + detail if detail else ""}')

    for lid, want in NAMES.items():
        h = re.search(rf'<h3 id="group-{lid}">(.*?)<span', sec, re.S).group(1).strip()
        cap = re.search(r"<caption>([^:<]*):", sec[sec.index(f'<h3 id="group-{lid}">'):]).group(1)
        check(f"group {lid} named exactly {want!r}", h == want and cap == want, f"heading {h!r}, caption {cap!r}")
    m = re.search(r'<p class="subtitle-line">(.*?)</p><p class="note cohort-note">(.*?)</p>', sec, re.S)
    check("subtitle element exact", bool(m) and text(m.group(1)) == "Groups reflect model profiles, not tournament rankings.",
          repr(text(m.group(1))) if m else "no subtitle followed by a cohort note")
    check("cohort note separate and retained", bool(m) and text(m.group(2)) == ("These are fixed starting cohorts, not current "
          "ladder ranks or mutually exclusive universal model types.") and "cohort" not in text(m.group(1)),
          repr(text(m.group(2))) if m else "")
    tables = {lid: [row_name(r) for r in group_rows(sec, lid)] for lid in NAMES}
    check("GNUbg weak in all three group tables", all("GNUbg weak" in t for t in tables.values()),
          ", ".join(f"group {k}: {len(v)} rows" for k, v in tables.items()))
    for p in ("Safest", "Random"):
        rows = [r for r in group_rows(sec, 1) if row_name(r) == p]
        check(f"{p} row in the Decision table only, a reference row", len(rows) == 1 and 'class="reference"' in rows[0]
              and all(p not in tables[k] for k in (2, 3)), f"rows in groups: {[k for k, v in tables.items() if p in v]}")
    labels = {}
    for lid in (1, 2, 3):
        for cells in later_rows(page, lid):
            labels.setdefault(row_name(cells), set()).add(text(cells[8]))
    check("GNUbg weak's later-league starting group: all three groups",
          labels.get("GNUbg weak") == {"Decision, Workhorse, Frontier program, original Leagues 1, 2, 3"}, str(labels.get("GNUbg weak")))
    for p in ("Safest", "Random"):
        check(f"{p}'s later-league starting group: the original League 1 only",
              labels.get(p) == {"Decision program, original League 1"}, str(labels.get(p)))
    if args.before:
        before = args.before.read_text()
        same = mask(before) == mask(page)
        check("before/after identical except the authorized display labels", same,
              f"{len(before)} -> {len(page)} bytes")
    print(f"{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
