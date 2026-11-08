"""(nav-ct: leaderboard-ct's copy, except that it copies build.ASSETS where the tree defines it.)
Renders every page of the site with one tools/site tree, as build.py main() does, without build.py itself: no
preview image, no redirects, no deploy, nothing written outside OUT. The results hash is fixed (the live build's), so
two trees rendered from the same state compare file by file.

    python3 render_site.py SRC STATE OUT RESULTS_HASH [--checks]

SRC is a mirror of the repository whose tools/site is the tree under test (update.sh's layout); STATE a copy of the
site's state. --checks runs checks.run(S, OUT), the full pre-deploy checks, and prints every failure.
"""
import argparse
import shutil
import sys
from pathlib import Path

src, state, out, rhash = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4]
sys.path.insert(0, str(src / "tools/site"))
import build as B  # noqa: E402
import decisions_export  # noqa: E402
import pages  # noqa: E402
from common import EARLIER, PROVISIONAL, PUBLISHED, relabel  # noqa: E402

assert Path(B.__file__).resolve().parent == (src / "tools/site").resolve(), B.__file__
out.mkdir(parents=True, exist_ok=True)
S = relabel(B.compute(argparse.Namespace(state=state)))
S["base"] = B.BASE
B.write_data(S, out)
datasets = [dict(id=lg["dataset"], label=f"League {lg['id']}", version="v3", league_id=lg["id"],
                 status=PUBLISHED if lg["metric_status"] == PUBLISHED else PROVISIONAL) for lg in S["leagues"]]
datasets.append(dict(id="v1-set", label=f"v1 set ({S['v1']['positions']:,} positions)", version="v1",
                     status=EARLIER, note=pages.play_order_note(S)))
S["decisions_export"] = decisions_export.export(
    out, S["_state"] / "snap.db", S["_state"] / "plays", S["_state"] / "prompts.db", B.ROOT / "replay.db",
    B.ROOT / "positions/v1.jsonl", datasets, S["_close"])
S["decision_files"] = sum(1 for p in (out / "decisions").rglob("*") if p.is_file())
S["showcase"] = B.showcase(S, decisions_export.SHOWCASE)
B.write_json(out, "data/showcase.json", S["showcase"] or {})
S["hash"] = rhash
B.manifest(S, out)
S["image"], S["risk_cards"] = None, {}
# build.ASSETS where the tree has it (nav-ct: the Hilde leaf added), else the list build.py main() copied before it.
for name in getattr(B, "ASSETS", ("site.css", "site.js", "tables.js", "png.js", "bg.css", "suite-bar.css", "bg.js",
                                  "decisions.css", "decisions.js")):
    if (B.SITE / "assets" / name).exists():
        shutil.copy(B.SITE / "assets" / name, out / name)
pages.write_all(S, out, B.BASE)
B.archive_pre_switch(out)
print(f"rendered {out} with {src / 'tools/site'}")
if "--checks" in sys.argv[5:]:
    import checks
    failures = checks.run(S, out)
    print(f"checks.run: {len(failures)} failure(s)")
    for f in failures:
        print(" -", f)
    sys.exit(1 if failures else 0)  # a failing check fails the process (Zeki #2790)
