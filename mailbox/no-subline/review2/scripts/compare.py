"""no-subline (Ümit #3039): the origin/main render against the candidate render, both from the same state. Reads only.

    python3 compare.py BASE_RENDER NEW_RENDER OUT_DIR

1. Every file but index.html, bg.css, bg.js and tables.js byte-identical (data, decision files, other pages).
2. index.html: the numbers of every leaderboard row (row text + its box, without the old sub-line and the box's first
   line, which 3 checks word for word) equal as multisets; the page's text outside the leaderboard identical.
3. Every row's box first line is '<name> · <maker> · <type> · <setting>': for each main row, the old first line
   (name · maker, 'Maker not recorded' left out) joined with the old sub-line (without its late tag); for a program,
   name · its reference label. Each other-settings row: old first line + its type + the setting of its old 'Setting'
   line (a program's other league: + the reference label of its main row). No row keeps a sub-line; the late tags equal.
Writes OUT_DIR/compare.md, numbers.csv (per row: the number multisets of both renders), manifest-main.tsv and
manifest-candidate.tsv (every file of each render: path, sha256, bytes); exits 1 on any failure."""
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

base, new, out = (Path(a) for a in sys.argv[1:4])
fail, lines = [], []
DOT = " \u00b7 "
NUM = re.compile(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: Counter(x.replace(",", "").replace("\u2212", "-").lstrip("+") for x in NUM.findall(t))  # noqa: E731
text = lambda el: re.sub(r"\s+", " ", el.get_text(" ")).strip()  # noqa: E731

# 1. Files.
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
fb = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
fn = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
hb, hn = {p: digest(base / p) for p in fb}, {p: digest(new / p) for p in fn}
changed = sorted(str(p) for p in fb & fn if hb[p] != hn[p])
only = sorted(str(p) for p in fb ^ fn)
lines.append(f"## 1. Files\n{len(fb)} files in origin/main's render, {len(fn)} in the candidate's; only in one: {only or 'none'}; "
             f"different: {changed}\n")
if only or set(changed) - {"index.html", "bg.css", "bg.js", "tables.js"}:
    fail.append(f"files: only {only}, changed {changed}")

# 2. Home numbers and text.
sb, sn = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (base, new))
tb, tn = sb.select_one("#headline-table"), sn.select_one("#headline-table")
rb, rn = tb.select("tbody tr[data-box]"), tn.select("tbody tr[data-box]")
lines.append(f"## 2. Numbers\nLeaderboard rows with a details box: origin/main {len(rb)}, candidate {len(rn)}.\n")
if len(rb) != len(rn):
    fail.append("row counts differ")
num_diff, num_rows = 0, []
for a, b in zip(rb, rn):
    box = a.get("data-box")
    a, b = BeautifulSoup(str(a), "html.parser"), BeautifulSoup(str(b), "html.parser")
    for el in a.select(".hl-type") + a.select(".hl-box p:first-child") + b.select(".hl-box p:first-child"):
        el.decompose()
    for p in a.select(".hl-box p"):  # the old 'Setting X · League N' line: the setting is on the first line now
        if text(p).startswith("Setting "):
            p.string = text(p).split(DOT, 1)[1] if DOT in text(p) else ""
    na, nb_ = nums(text(a)), nums(text(b))
    flat = lambda c: " ".join(sorted(c.elements(), key=lambda v: (float(v), v)))  # noqa: E731
    num_rows.append((box, sum(na.values()), flat(na), flat(nb_), "yes" if box == b.tr.get("data-box") and na == nb_ else "NO"))
    if box != b.tr.get("data-box") or na != nb_:
        num_diff += 1
        fail.append(f"row {box}: numbers differ {na - nb_} / {nb_ - na}")
tb.decompose()
tn.decompose()
same_rest = text(sb) == text(sn)
lines.append(f"Rows whose numbers (row + box) differ: {num_diff}. Home page outside the leaderboard table: text "
             f"{'identical' if same_rest else 'DIFFERENT'}.\n")
if not same_rest:
    fail.append("home text outside the leaderboard differs")

# 3. First lines.
sb, sn = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (base, new))
rb, rn = sb.select("#headline-table tbody tr[data-box]"), sn.select("#headline-table tbody tr[data-box]")
TYPE = {"chat": "chat model", "decision": "decision model"}
rows, bad, parent_under = [], 0, []
for a, b in zip(rb, rn):
    first_old = text(a.select_one(".hl-box p")).split(DOT)
    first_old = [p for p in first_old if p != "Maker not recorded"]
    first_new = text(b.select_one(".hl-box p"))
    tag_old = text(a.select_one(".hl-tag")) if a.select_one(".hl-tag") else ""
    tag_new = text(b.select_one(".hl-tag")) if b.select_one(".hl-tag") else ""
    sub = "hl-sub" in (a.get("class") or [])
    if not sub:
        st = a.select_one(".hl-type")
        if st.select_one(".hl-tag"):
            st.select_one(".hl-tag").decompose()
        under = [p for p in text(st).split(DOT) if p]
        expect = DOT.join(first_old[:1] + under) if "reference" in (a.get("class") or []) else DOT.join(first_old + under[1:] if under and len(first_old) > 1 and under[0] == first_old[1] else first_old + under)
        parent_under = under
    else:
        setting = next((m.group(1) for p in a.select(".hl-box p") if (m := re.match(r"Setting (\S+)", text(p)))), None)
        ref = "reference" in (b.get("class") or [])
        expect = DOT.join(first_old + (parent_under if ref else [x for x in (TYPE.get(b.get("data-hl-type")), setting) if x]))
    subline = b.select_one("td.model .hl-type") or (None if sub else b.select_one("td.model > span.small"))
    ok = first_new == expect and tag_old == tag_new and subline is None
    bad += not ok
    if not ok:
        fail.append(f"{a.get('data-box')}: first line {first_new!r}, expected {expect!r}; tags {tag_old!r}/{tag_new!r}; sub-line {subline}")
    rows.append(f"| {a.get('data-box')} | {'other setting' if sub else 'program' if 'reference' in (a.get('class') or []) else 'ranked'} "
                f"| {first_new} | {tag_new} | {'yes' if ok else 'NO'} |")
lines.append(f"## 3. Box first line\n{len(rows) - bad} of {len(rows)} rows ok (expected = origin/main's first line + its "
             f"sub-line; 'Maker not recorded' left out; late tag unchanged; no sub-line).\n\n| Box | Row | First line | Tag | OK |\n|---|---|---|---|---|")
lines += rows
out.mkdir(parents=True, exist_ok=True)
# The two renders' manifests (every file: path, sha256, bytes) and the per-row number multisets.
for name, root, h in (("main", base, hb), ("candidate", new, hn)):
    (out / f"manifest-{name}.tsv").write_text("path\tsha256\tbytes\n" + "".join(
        f"{p}\t{h[p]}\t{(root / p).stat().st_size}\n" for p in sorted(h, key=str)))
with (out / "numbers.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["box", "numbers", "main (sorted, row + box without sub-line / first line)", "candidate (same)", "equal"])
    w.writerows(num_rows)
(out / "compare.md").write_text("# Render comparison\n\n" + "\n".join(lines) + f"\n\n**Failures: {len(fail)}**\n" + "".join(f"- {f}\n" for f in fail))
print(f"compare: {len(fail)} failures")
sys.exit(1 if fail else 0)
