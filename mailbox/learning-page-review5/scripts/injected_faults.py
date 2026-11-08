"""Injected-fault tests of the learning page's checks (review 5, Ümit #2925): each fault is put into a fresh copy of a
rendered page (its HTML and/or its data file) and learning_page.check (checks.py number, mixing, link, private-string
and learning checks) must report it.

    python3 injected_faults.py SITE_TOOLS RUNNING_OUT COMPLETE_OUT BUILT_SITE TEST_SET

RUNNING_OUT: the SYNTHETIC running render (not complete, --with-results); COMPLETE_OUT: the REAL complete render
(--with-results, review only). Evaluation-set values (ids, board keys, boards) never reach the output: every check
message is printed with any such value, whole or cut, replaced by [REDACTED], and the faults are described without
them.
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

tools, running, complete, site, test_set = (Path(a) for a in sys.argv[1:6])
sys.path.insert(0, str(tools))
import checks  # noqa: E402
import learning_page as LP  # noqa: E402

secrets = checks._test_set_strings(test_set)
eval_id, eval_key, eval_board = secrets[0], secrets[1], secrets[2]


def redact(msg: str) -> str:
    for s in secrets:
        for v in (s, s[:24]):
            msg = msg.replace(v, "[REDACTED]")
    return re.sub(r"evaluation-set position .*?\u2026", "evaluation-set position [REDACTED]\u2026", msg)


def page_sub(pattern, repl, count=1):
    """A regex substitution in the page; the fault is void (and reported as such) if the pattern is not there."""
    def f(out):
        p = out / LP.PATH / "index.html"
        t, n = re.subn(pattern, repl, p.read_text(), count=count, flags=re.S)
        assert n, f"pattern not in page: {pattern}"
        p.write_text(t)
    return f


def page_insert(snippet, after='<h2>Results</h2>'):
    return page_sub(re.escape(after), lambda m: m.group(0) + snippet)


def data_change(change):
    def f(out):
        p = out / LP.DATA
        d = json.loads(p.read_text())
        change(d)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return f


def both(*fs):
    def f(out):
        for g in fs:
            g(out)
    return f


def first_lesson(d):
    return d["lessons"][0]


def unescape_first_lesson(out):
    """The first lesson's text gains literal HTML, written into the page unescaped (and into the data file as text)."""
    raw = '<img src="x" onerror="alert(1)">Hit more.'
    d = json.loads((out / LP.DATA).read_text())
    x = d["lessons"][0]
    old = LP.esc(x["text"])
    x["text"] += "\n" + raw
    (out / LP.DATA).write_text(json.dumps(d, indent=1, ensure_ascii=False))
    p = out / LP.PATH / "index.html"
    t = p.read_text()
    assert old in t
    p.write_text(t.replace(old, old + "\n" + raw, 1))


# (name, base: "running" | "complete", inject, expected substring of a failure)
FAULTS = [
    # Status line.
    ("status line lying: N one higher than the data", "running",
     page_sub(r'(data-phase="running">Running: )5( of 10)', r"\g<1>6\g<2>"), "status line says"),
    ("status line lying: 'Done' while running", "running",
     page_sub(r'data-phase="running">Running: 5 of 10 series per arm', 'data-phase="done">Done'), "status line says"),
    ("status line lying: 'Smoke running' after the smoke", "running",
     page_sub(r'>Running: 5 of 10 series per arm<', '>Smoke running: 2 of 3 series per arm<'), "status line says"),
    ("status line time not the data's last update", "running",
     page_sub(r'(<time datetime=")[^"]+', r"\g<1>2026-11-09T00:00:00+00:00"), "status line time"),
    ("status line removed", "running", page_sub(r'id="learning-status-line"', 'id="x-status"'),
     "status line missing"),
    ("data file's status line not the one its data imply", "running",
     data_change(lambda d: d["status"].update(line="Done")), "data file's status line"),
    # Charts and tables.
    ("chart number not in the data (risks dot value)", "running",
     page_sub(r'(data-arm="lessons" data-x="T10" data-value=")[^"]+', r"\g<1>41.7"), "chart learning-risks point"),
    ("chart number not in the data (games dot value)", "running",
     page_sub(r'(<svg[^>]*data-chart="learning-games".*?data-arm="records" data-x="3" data-value=")[^"]+',
              r"\g<1>12.3"), "chart learning-games point"),
    ("chart point dropped (no dot for budget, game 10)", "running",
     page_sub(r'<circle class="lp-dot" data-arm="budget" data-x="10"[^>]*>.*?</circle>', ""),
     "chart learning-games point"),
    ("table number not in the data (risks table cell)", "running",
     page_sub(r'(data-arm="records" data-x="T10">)[^<]+', r"\g<1>77.7"), "table under learning-risks"),
    ("table number not in the data (games table cell)", "running",
     page_sub(r'(data-arm="control" data-x="4">)[^<]+', r"\g<1>12.9"), "table under learning-games"),
    ("table number absent from every data file (games table cell 987.6)", "running",
     page_sub(r'(data-arm="lessons" data-x="9">)[^<]+', r"\g<1>987.6"), "not found in any data file"),
    ("control line not dashed", "running",
     page_sub(r'(data-arm="control" style="[^"]*") stroke-dasharray="[^"]*"', r"\g<1>"), "control is not a flat"),
    ("control line not flat (end raised)", "running",
     page_sub(r'(data-arm="control" style="[^"]*" stroke-dasharray="[^"]*" points="[\d.]+,[\d.]+ [\d.]+,)[\d.]+',
              r"\g<1>40.0"), "control is not a flat"),
    ("another arm's line dashed (records)", "running",
     page_sub(r'(<polyline class="lp-line" data-arm="records" style="[^"]*")', r'\g<1> stroke-dasharray="6 4"'),
     "line is dashed"),
    ("arm colour not the fixed one (records drawn in lessons' colour)", "running",
     page_sub(r'(class="lp-dot" data-arm="records" data-x="T5" data-value="[^"]*" style="--lp:)var\(--reading\)',
              r"\g<1>var(--good)"), "not in its fixed colour"),
    ("risks chart removed while series are finished", "running",
     page_sub(r'data-chart="learning-risks"', 'data-chart="x-risks"'), "chart learning-risks missing"),
    # Verdict and lift before complete.
    ("verdict block shown before complete", "running",
     page_insert('<div id="learning-verdict"><p>No arm reached the threshold.</p></div>'),
     "block #learning-verdict shown before the results are complete"),
    ("learning-lift block shown before complete", "running", page_insert('<div id="learning-lift"></div>'),
     "block #learning-lift shown before the results are complete"),
    ("learning_lift key in the data file before complete", "running",
     data_change(lambda d: d["results"].update(learning_lift={})), "learning_lift published before"),
    ("signal key in the data file before complete", "running",
     data_change(lambda d: d["results"].update(signal={})), "signal published before"),
    ("'N of 10 series done' wrong while running", "running",
     page_sub(r"5 of 10 series done", "6 of 10 series done"), "does not say '5 of 10 series done'"),
    ("data file claims complete, validator did not (results.complete true, validation.complete false)", "running",
     data_change(lambda d: d["results"].update(complete=True)), "results.complete and validation.complete disagree"),
    # Verdict when complete (REAL render).
    ("verdict contradicts the data's signal (lessons 'reached')", "complete",
     page_sub(r'(data-arm="lessons"><strong>lessons</strong>: )threshold not reached', r"\g<1>threshold reached"),
     "contradicts the data's signal"),
    ("budget's fixed reading removed although its context was always empty", "complete",
     page_sub(re.escape(LP.BUDGET_VERDICT), "record memory did not help"), "budget reading"),
    ("verdict block removed when complete", "complete", page_sub(r'id="learning-verdict"', 'id="x-verdict"'),
     "complete, but no verdict"),
    # Lessons.
    ("lesson without its game (data: game result removed)", "complete",
     data_change(lambda d: first_lesson(d).update(won=None, result=None, points=None)), "without its game"),
    ("lesson of an unfinished/unknown series (data: series 99)", "complete",
     data_change(lambda d: first_lesson(d).update(series=99)), "without its game"),
    ("lesson shown without its series and game (page attributes removed)", "complete",
     page_sub(r'<li class="lp-lesson" data-series="1" data-game="1">', '<li class="lp-lesson">'),
     "a lesson without its series and game"),
    ("lesson shown without its game line", "complete",
     page_sub(r'(data-series="1" data-game="2"><p class="small">).*?</p>', r"\g<1></p>"),
     "not shown with its game and result"),
    ("lesson dropped from the page", "complete",
     page_sub(r'<li class="lp-lesson" data-series="2" data-game="5">.*?</li>', ""), "missing from the page"),
    ("lesson text edited in the page", "complete",
     page_sub(r'(data-series="3" data-game="7">.*?<pre class="citation">)', r"\g<1>Always double. "),
     "text is not the data's"),
    ("unescaped lesson text (literal HTML in the page)", "complete", unescape_first_lesson,
     "text is not the data's"),
    # Evaluation positions (strings redacted in this output).
    ("evaluation-set id in a published lesson (data file and page)", "complete",
     both(data_change(lambda d: first_lesson(d).update(text=first_lesson(d)["text"] + " see " + eval_id)),
          page_sub(r'(data-series="1" data-game="1">.*?<pre class="citation">)', lambda m: m.group(1) + eval_id + " ")),
     "evaluation-set position"),
    ("evaluation-set board key in the page", "running", page_insert("<p>" + eval_key + "</p>"),
     "evaluation-set position"),
    ("evaluation-set board string in the page", "running",
     page_insert("<p>" + LP.esc(eval_board) + "</p>"), "evaluation-set position"),
    ("evaluation-set board string in the data file", "running",
     data_change(lambda d: d["results"]["provenance"].update(note=eval_board)), "evaluation-set position"),
    # Generic page checks still apply.
    ("made-up number in the page", "running", page_insert("<p>Lift 4.567 points.</p>"),
     "not found in any data file"),
]

bases = {"running": running, "complete": complete}
for name, out in bases.items():
    L = json.loads((out / LP.DATA).read_text())
    assert bool(L["results"]["complete"]) == (name == "complete"), name
    base = LP.check(out, site, L, test_set)
    print(f"baseline {name} ({out}): {len(base)} failure(s)")
    for b in base:
        print("   ", redact(b))
passed = 0
for name, base, inject, expect in FAULTS:
    with tempfile.TemporaryDirectory(prefix="lp-fault-") as t:
        out = Path(t) / "out"
        shutil.copytree(bases[base], out)
        try:
            inject(out)
        except AssertionError as e:
            print(f"\n== {name} [{base}]: FAULT NOT INJECTED ({e})")
            continue
        bad = LP.check(out, site, json.loads((out / LP.DATA).read_text()), test_set)
        hit = any(expect in b for b in bad)
        passed += hit
        print(f"\n== {name} [{base}]: {'DETECTED' if hit else 'NOT DETECTED'} ({len(bad)} failure(s))")
        for b in bad:
            print("   ", redact(b.replace(str(out), "OUT")))
print(f"\n{passed} / {len(FAULTS)} injected faults detected")
sys.exit(0 if passed == len(FAULTS) else 1)
