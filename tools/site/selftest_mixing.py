#!/usr/bin/env python3
"""Self-test of the no-mixing pre-deploy check (checks.check_mixing, brief B1/B10): writes the site's pages twice
from the same data, once as built and once deliberately mixed, and runs the check on both.

    python3 tools/site/selftest_mixing.py BUILD_DIR [--state STATE]

BUILD_DIR is a finished build (its data/ is reused). The mixed build:
  1. adds a v1-set row to every league's quality table (v1 and v3 rows in one table);
  2. adds a v1-set tile to every league's 2x2 wall (v1 and v3 in one chart);
  3. adds a v1-set table, outside any Earlier-version block, under every league's reasoning table;
  4. adds a League 3 table inside every Earlier-version (v1) block.
Exit 0 when the clean pages pass and every kind of mixing is caught; 1 otherwise. Writes nothing outside a temp dir.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
import checks  # noqa: E402
import pages  # noqa: E402


def mixing_failures(out: Path, S: dict) -> list[str]:
    bad = []
    for page in sorted(out.rglob("index.html")):
        tree = checks.Tree()
        tree.feed(page.read_text())
        bad += checks.check_mixing(page.relative_to(out), tree.root, S)
    return bad


def mix(S: dict):
    """Monkeypatches pages to mix v1 and v3 in tables, walls and Earlier-version blocks; returns the undo function."""
    v1 = S["v1"]["setups"]
    one = next(iter(v1))
    lg3 = S["leagues"][-1]
    orig = dict(quality_rows=pages.quality_rows, risk_tiles=pages.risk_tiles,
                league_reasoning_table=pages.league_reasoning_table, earlier_block=pages.earlier_block)

    def quality_rows(S_, rel, ds, setups):
        rows = orig["quality_rows"](S_, rel, ds, setups)
        return rows + orig["quality_rows"](S_, rel, "v1-set", {one: v1[one]}) if ds != "v1-set" else rows

    def risk_tiles(S_, rel, ds, setups, image=None):
        html = orig["risk_tiles"](S_, rel, ds, setups, image=image)
        if ds == "v1-set":
            return html
        tag = f'<div class="r2-wall" data-dataset="{ds}">'
        return html.replace(tag, tag + pages.r2_tile(S_, rel, "v1-set", one, v1[one]["risk"]), 1)

    def league_reasoning_table(S_, lg):
        return orig["league_reasoning_table"](S_, lg) + pages.table(
            pages.QUALITY_HEAD, orig["quality_rows"](S_, "", "v1-set", v1), "v1 rows outside an Earlier-version block")

    def earlier_block(S_, inner, title):
        return orig["earlier_block"](S_, inner + pages.table(
            pages.QUALITY_HEAD, orig["quality_rows"](S_, "", lg3["dataset"], lg3["setups"]), "v3 rows in a v1 block",
            attrs=f' data-dataset="{lg3["dataset"]}"'), title)

    pages.quality_rows, pages.risk_tiles = quality_rows, risk_tiles
    pages.league_reasoning_table, pages.earlier_block = league_reasoning_table, earlier_block

    def undo():
        for k, f in orig.items():
            setattr(pages, k, f)
    return undo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_dir")
    ap.add_argument("--state", default="~/.local/state/bg-site")
    args = ap.parse_args()
    built = Path(args.build_dir)
    S = build.compute(argparse.Namespace(state=args.state))
    sc = json.loads((built / "data/showcase.json").read_text())
    S.update(hash="selftest", decision_files=0, image=None, risk_images={}, showcase=sc or None)
    result = {}
    with tempfile.TemporaryDirectory() as tmp:
        for label in ("clean", "mixed"):
            out = Path(tmp) / label
            shutil.copytree(built / "data", out / "data")
            undo = mix(S) if label == "mixed" else (lambda: None)
            try:
                pages.write_all(S, out, build.BASE)
            finally:
                undo()
            result[label] = mixing_failures(out, S)
    mixed = result["mixed"]
    kinds = {"table mixes": any("a table mixes datasets" in f for f in mixed),
             "wall mixes": any("a 2x2 wall mixes datasets" in f for f in mixed),
             "v1 outside Earlier version": any("v1 rows outside an Earlier-version block" in f for f in mixed),
             "v3 inside Earlier version": any("in an Earlier-version block holds v3 rows" in f for f in mixed)}
    print(f"clean build: {len(result['clean'])} mixing failures")
    for f in result["clean"][:10]:
        print("  ", f)
    print(f"mixed build: {len(mixed)} mixing failures; caught: {kinds}")
    seen = set()
    for f in mixed:
        kind = f.split(": ", 1)[1].split(" [")[0]
        if kind not in seen:
            seen.add(kind)
            print("  ", f)
    ok = not result["clean"] and all(kinds.values())
    print("SELFTEST", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
