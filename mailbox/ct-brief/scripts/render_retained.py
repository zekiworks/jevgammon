"""(ct-brief copy of mailbox/nav-ct/scripts/render_retained.py, plus the AS_OF label.)
render_site.py without build.compute(): the pages and data files rendered from a RETAINED computed state S (a pickle
written once by compute_retained.py, i.e. build.compute() on the copy of the live state, results 7b40b30e), so no
statistics run again (Zeki #2790, Main: no model/statistics reruns). Otherwise as render_site.py: no build.py main, no
preview image, no deploy, nothing written outside OUT.

    python3 render_retained.py SRC STATE OUT RESULTS_HASH S_PICKLE [--checks]

--checks runs checks.run(S, OUT) and exits 1 if any check fails.
"""
import shutil
import sys
from pathlib import Path

src, state, out, rhash, spk = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4], sys.argv[5]
sys.path.insert(0, str(src / "tools/site"))
import build as B  # noqa: E402
import decisions_export  # noqa: E402
import pages  # noqa: E402
from common import EARLIER, PROVISIONAL, PUBLISHED  # noqa: E402

assert Path(B.__file__).resolve().parent == (src / "tools/site").resolve(), B.__file__
out.mkdir(parents=True, exist_ok=True)
import pickle  # noqa: E402
S = pickle.load(open(spk, "rb"))
# ct-brief: the data-as-of label set to the live manifest's (AS_OF), so the renders compare with live text for text; a label, not a number.
import os  # noqa: E402
S["as_of"] = os.environ.get("AS_OF", S["as_of"])
# The learning page's data is a file read, not a computation (learning_page.from_state: the plan and the snapshot under
# STATE/learning); read again from STATE, whose snapshot (19:35 UTC) is newer than the retained S (19:18 UTC).
import learning_page  # noqa: E402
S["learning"] = learning_page.from_state(Path(state))
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
for name in getattr(B, "ASSETS", ("site.css", "site.js", "tables.js", "png.js", "bg.css", "suite-bar.css", "bg.js", "decisions.css", "decisions.js")):
    if (B.SITE / "assets" / name).exists():
        shutil.copy(B.SITE / "assets" / name, out / name)
pages.write_all(S, out, B.BASE)
B.archive_pre_switch(out)
print(f"rendered {out} with {src / 'tools/site'}")
if "--checks" in sys.argv[6:]:
    import checks
    failures = checks.run(S, out)
    print(f"checks.run: {len(failures)} failure(s)")
    for f in failures:
        print(" -", f)
    sys.exit(1 if failures else 0)
