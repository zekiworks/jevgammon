"""params-align (logic #3508/#3550, Main #3506; Zeki #3510/#3529/#3574): the pinned base render (origin/main at the
commit named in build-main.log) against the candidate's, both from the same frozen state. Reads only.

    python3 compare.py REPO BASE_RENDER NEW_RENDER OUT_DIR

1. Files: every file but index.html byte-identical.
2. index.html, every leaderboard row (same rows, same order): the row's HTML equal to origin/main's once the box line
   'Parameters: …' and the attribute data-hl-small are taken out of both; so its numbers (row + box) equal; the page
   outside the leaderboard table equal in text.
3. Parameters line vs content/model_params.json: every model row has exactly one, equal to the file's entry of the
   row's model (setups.json 'model' of the box's setup name, else the name): the card's own terms where 'terms' is
   set; else '31B', 'T total / A active', 'T total; active not disclosed by maker', 'E effective (T total)', linked
   to the source; or 'not disclosed by maker' (no link); programs none. origin/main's line beside it (old -> new).
4. Small models: a main row has data-hl-small="yes" exactly when its model's total_b is at most 15; its
   other-settings rows carry the main row's flag; programs none.
Writes OUT_DIR/compare.md, numbers.csv, params.csv, manifest-main.tsv, manifest-candidate.tsv; exits 1 on any failure."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

repo, base, new, out = (Path(a) for a in sys.argv[1:5])
SMALL_MAX_B = 15
PARAMS = json.loads((repo / "tools/site/content/model_params.json").read_text())["models"]
MODEL = {s["name"]: s.get("model") or s["name"]
         for s in json.loads((repo / "tools/site/content/setups.json").read_text())["setups"] if s.get("name")}
fail, lines = [], []
NUM = re.compile(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: Counter(x.replace(",", "").replace("\u2212", "-").lstrip("+") for x in NUM.findall(t))  # noqa: E731
text = lambda el: re.sub(r"\s+", " ", el.get_text(" ")).strip()  # noqa: E731


def human(b):
    return f"{b / 1000:g}T" if b >= 1000 else f"{b:g}B"


def expected(model):
    p = PARAMS[model]
    t = p["total_b"]
    if p.get("terms"):
        return p["terms"], p["source"]
    if t is None:
        return "not disclosed by maker", None
    if p["effective_b"] is not None:
        s = f"{human(p['effective_b'])} effective ({human(t)} total)"
    elif p["active_b"] is not None:
        s = f"{human(t)} total / {human(p['active_b'])} active"
    elif p["moe"]:
        s = f"{human(t)} total; active not disclosed by maker"
    else:
        s = human(t)
    return s, p["source"]


digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
fb = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
fn = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
hb, hn = {p: digest(base / p) for p in fb}, {p: digest(new / p) for p in fn}
changed = sorted(str(p) for p in fb & fn if hb[p] != hn[p])
only = sorted(str(p) for p in fb ^ fn)
lines.append(f"## 1. Files\n{len(fb)} files in origin/main's render, {len(fn)} in the candidate's; only in one: "
             f"{only or 'none'}; different: {changed}\n")
if only or set(changed) - {"index.html"}:
    fail.append(f"files: only {only}, changed {changed}")

sb, sn = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (base, new))
rb, rn = sb.select("#headline-table tbody tr[data-box]"), sn.select("#headline-table tbody tr[data-box]")
lines.append(f"## 2. Rows and numbers\nLeaderboard rows with a details box: origin/main {len(rb)}, candidate {len(rn)}.\n")
if len(rb) != len(rn):
    fail.append("row counts differ")
num_rows, par_rows, row_diff, num_diff = [], [], 0, 0
flat = lambda c: " ".join(sorted(c.elements(), key=lambda v: (float(v), v)))  # noqa: E731
main_small = None
for a, b in zip(rb, rn):
    box = a.get("data-box")
    if box != b.get("data-box"):
        fail.append(f"row order {box} / {b.get('data-box')}")
    prog = "reference" in (b.get("class") or [])
    sub = "hl-sub" in (b.get("class") or [])
    def strip(row):
        c = BeautifulSoup(str(row), "html.parser")
        sm = c.select_one("tr").attrs.pop("data-hl-small", None)
        pl = [p for p in c.select(".hl-box > p") if text(p).startswith("Parameters:")]
        g = [(text(p).removeprefix("Parameters:").strip(), p.select_one("a").get("href") if p.select_one("a") else None)
             for p in pl]
        for p in pl:
            p.decompose()
        return c, sm, g
    ca, small_old, got_old = strip(a)
    cb, small, got = strip(b)
    same = str(cb) == str(ca)
    row_diff += not same
    if not same:
        fail.append(f"{box}: row differs from origin/main beyond the Parameters line and data-hl-small")
    na, nb_ = nums(text(ca)), nums(text(cb))
    num_diff += na != nb_
    num_rows.append((box, sum(na.values()), flat(na), flat(nb_), "yes" if na == nb_ else "NO"))
    if na != nb_:
        fail.append(f"{box}: numbers differ")
    setup = text(b.select_one(".hl-box p strong"))
    model = None if prog else MODEL.get(setup, setup)
    if prog:
        want, want_small = [], None
        ok = not got and small is None
    else:
        e = expected(model)
        want = [e]
        t = PARAMS[model]["total_b"]
        if not sub:
            main_small = "yes" if t is not None and t <= SMALL_MAX_B else None
        want_small = main_small
        ok = got == want and small == want_small
    if not ok:
        fail.append(f"{box}: parameters {got} expected {want}; small {small!r} expected {want_small!r}")
    par_rows.append((box, "program" if prog else "model", "other" if sub else "main", setup, model or "",
                     got_old[0][0] if got_old else "", small_old or "",
                     got[0][0] if got else "", got[0][1] or "" if got else "", small or "",
                     "same" if got == got_old and small == small_old else "CHANGED", "yes" if ok else "NO"))
lines.append(f"Rows differing from origin/main beyond the Parameters line and data-hl-small: {row_diff}. Rows whose "
             f"numbers (row + box, Parameters line out) differ: {num_diff}.\n")
for s in (sb, sn):
    s.select_one("#headline-table").decompose()
same_rest = text(sb) == text(sn)
lines.append(f"Home page outside the leaderboard table: text "
             f"{'identical' if same_rest else 'DIFFERENT'}.\n")
if not same_rest:
    fail.append("home text outside the leaderboard differs")
bad = sum(r[-1] != "yes" for r in par_rows)
lines.append(f"## 3-4. Parameters line and Small models flag vs model_params.json (threshold {human(SMALL_MAX_B)})\n"
             f"{len(par_rows) - bad} of {len(par_rows)} rows ok; {sum(r[10] == 'CHANGED' for r in par_rows)} rows changed.\n\n"
             "| Box | Row | Setup | Model | origin/main | small (main) | candidate | Link | small | Change | OK |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|")
lines += [f"| {r[0]} | {r[1]}/{r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} |"
          for r in par_rows]
out.mkdir(parents=True, exist_ok=True)
for name, root, h in (("main", base, hb), ("candidate", new, hn)):
    (out / f"manifest-{name}.tsv").write_text("path\tsha256\tbytes\n" + "".join(
        f"{p}\t{h[p]}\t{(root / p).stat().st_size}\n" for p in sorted(h, key=str)))
with (out / "numbers.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["box", "numbers", "main (sorted, row + box, Parameters line out)", "candidate (same)", "equal"])
    w.writerows(num_rows)
with (out / "params.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["box", "kind", "row", "setup", "model", "parameters main", "data-hl-small main", "parameters shown", "link",
                "data-hl-small", "change", "ok"])
    w.writerows(par_rows)
(out / "compare.md").write_text("# Render comparison\n\n" + "\n".join(lines) + f"\n\n**Failures: {len(fail)}**\n"
                                + "".join(f"- {f}\n" for f in fail))
print(f"compare: {len(fail)} failures")
for f_ in fail[:20]:
    print(" FAIL", f_)
sys.exit(1 if fail else 0)
