"""The learning page's review states for the exploratory block, in snapshot.py's STATE/learning layout, made with the
branch's own snapshot.snapshot_learning (read-only reads of the pilot's files and of the exploratory file).

    python3 make_states.py SITE_TOOLS ROOT OUT_DIR

- OUT_DIR/no-explore/learning: the REAL complete pilot, no exploratory file (snapshot_learning with the exploratory file
  hidden from it: a root whose workspace/learning-retest is absent);
- OUT_DIR/explore/learning: the REAL complete pilot and the REAL exploratory file, exactly as snapshot_learning copies
  them (explore/explore.json);
- OUT_DIR/malformed-explore/learning: SYNTHETIC: the explore state with its explore.json given an unknown top-level key
  (a malformed file: the site must refuse it and show none of it).
Prints each state's learning key (snapshot_learning's return value) and the exploratory file's sha256.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

tools, root, out = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(tools))
import snapshot  # noqa: E402


def snap(src_root: Path, name: str) -> str:
    state = out / name
    shutil.rmtree(state, ignore_errors=True)
    state.mkdir(parents=True)
    return snapshot.snapshot_learning(str(src_root), str(state))


with tempfile.TemporaryDirectory(prefix="lp-root-") as t:
    # a root with the pilot and the plan but no workspace/learning-retest
    r = Path(t)
    (r / "workspace").mkdir()
    os.symlink(root / snapshot.LEARNING_SOURCE, r / snapshot.LEARNING_SOURCE)
    (r / "mailbox").mkdir()
    os.symlink(root / snapshot.LEARNING_PLAN, r / snapshot.LEARNING_PLAN)
    print(f"no-explore: learning key {snap(r, 'no-explore')}")
print(f"explore: learning key {snap(root, 'explore')}")
e = out / "explore/learning/explore/explore.json"
print(f"explore: explore.json sha256 {hashlib.sha256(e.read_bytes()).hexdigest()}; "
      f"retest_answer_counts {json.loads(e.read_text())['retest_answer_counts']}")
m = out / "malformed-explore"
shutil.rmtree(m, ignore_errors=True)
shutil.copytree(out / "explore", m)
p = m / "learning/explore/explore.json"
d = json.loads(p.read_text())
d["SYNTHETIC_unknown_key"] = 1
p.write_text(json.dumps(d, indent=1))
print("malformed-explore: SYNTHETIC: the explore state's explore.json with an unknown top-level key")
