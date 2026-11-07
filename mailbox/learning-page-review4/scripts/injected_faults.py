"""Injected-fault tests of the learning page's checks: each fault is put into a fresh copy of a rendered page (running
state, results not complete) and learning_page.check (checks.py checks 1, 3, 4, 5 and 7) must report it.

    python3 injected_faults.py SITE_TOOLS RENDERED_OUT BUILT_SITE TEST_SET

Evaluation-set values (ids, board keys, boards) never reach the output: every check message is printed with any such
value, whole or cut, replaced by [REDACTED], and the faults are described without them.
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

tools, rendered, site, test_set = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(tools))
import checks  # noqa: E402
import learning_page as LP  # noqa: E402

secrets = checks._test_set_strings(test_set)
eval_id, eval_board = secrets[0], secrets[2]


def redact(msg: str) -> str:
    for s in secrets:
        for v in (s, s[:24]):
            msg = msg.replace(v, "[REDACTED]")
    return re.sub(r"evaluation-set position .*?\u2026", "evaluation-set position [REDACTED]\u2026", msg)


def page_fault(snippet):
    def f(out):
        p = out / LP.PATH / "index.html"
        p.write_text(p.read_text().replace("<h2>Results</h2>", "<h2>Results</h2>" + snippet, 1))
    return f


def data_fault(change):
    def f(out):
        p = out / LP.DATA
        d = json.loads(p.read_text())
        change(d)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return f


FAULTS = [
    ("made-up number in the page", page_fault("<p>Lift 4.567 points.</p>"), "not found in any data file"),
    ("private address in the page", page_fault("<p>Served from 192.168.7.7.</p>"), "banned string"),
    ("dead anchor in the page", page_fault('<p><a href="#no-such-block">see</a></p>'), "anchor #no-such-block missing"),
    ("learning-lift block before complete", page_fault('<div id="learning-lift"></div>'),
     "block #learning-lift shown before the results are complete"),
    ("signal key in the data file before complete", data_fault(lambda d: d["results"].update(signal={})),
     "signal published before the results are complete"),
    ("evaluation-set id in a published lesson (data file)",
     data_fault(lambda d: d["lessons"].append(dict(series=1, game=1, won=None, result=None, points=None,
                                                   text="see " + eval_id))), "evaluation-set position"),
    ("evaluation-set board string in the page", page_fault("<p>" + eval_board.replace("'", "&#x27;") + "</p>"),
     "evaluation-set position"),
]

L = json.loads((rendered / LP.DATA).read_text())
assert not (L["results"] or {}).get("complete"), "run the faults on a not-complete render"
print(f"baseline ({rendered}): ", end="")
base = LP.check(rendered, site, L, test_set)
print(f"{len(base)} failure(s)")
passed = 0
for name, inject, expect in FAULTS:
    with tempfile.TemporaryDirectory(prefix="lp-fault-") as t:
        out = Path(t) / "out"
        shutil.copytree(rendered, out)
        inject(out)
        bad = LP.check(out, site, json.loads((out / LP.DATA).read_text()), test_set)
        hit = any(expect in b for b in bad)
        passed += hit
        print(f"\n== {name}: {'DETECTED' if hit else 'NOT DETECTED'} ({len(bad)} failure(s))")
        for b in bad:
            print("   ", redact(b.replace(str(out), "OUT")))
print(f"\n{passed} / {len(FAULTS)} injected faults detected")
sys.exit(0 if passed == len(FAULTS) and not base else 1)
