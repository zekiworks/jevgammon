"""Run ONCE (19:18 UTC, 7 Nov, on the copy of the live state, results 7b40b30e): build.compute() of the site, which
includes the bootstrap loops of offline.py, pickled to /tmp/lct/S.pkl as the retained fixture that render_retained.py
renders from. Not re-run for review2 (no statistics reruns).
    python3 compute_retained.py SRC"""
import argparse, pickle, sys
from pathlib import Path
src = Path(sys.argv[1])
sys.path.insert(0, str(src / "tools/site"))
import build as B
from common import relabel
S = relabel(B.compute(argparse.Namespace(state="/tmp/lct/state")))
S["base"] = B.BASE
pickle.dump(S, open("/tmp/lct/S.pkl", "wb"))
print("ok", len(S["leagues"]))
