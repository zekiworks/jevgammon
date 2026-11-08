"""name-chip (Ümit #3193): the origin/main render against the candidate render, both from the same state. Reads only.

    python3 compare.py BASE_RENDER NEW_RENDER OUT_DIR

1. Every file but index.html and bg.css byte-identical (data, decision files, other pages, bg.js, tables.js).
2. index.html: every leaderboard row's details box identical (text and HTML); the numbers of every row (row + box,
   without the chip and the old 'other setting of …' line) equal as multisets; the page outside the leaderboard
   identical in text.
3. Every row has exactly one chip and no other small text after the name; the chip equals what the data says:
   setting (the box's first line, last part, where it is a setting) · type (the box's first line: chat/decision) ·
   origin/main's late-entry tag; a program 'program' (an other-league row 'League n · program', n from its box). The
   visible name equals origin/main's minus a trailing '(<setting>)', and the link (href) is unchanged.
Writes OUT_DIR/compare.md, numbers.csv, chips.csv, manifest-main.tsv, manifest-candidate.tsv; exits 1 on any failure."""
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

digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
fb = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
fn = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
hb, hn = {p: digest(base / p) for p in fb}, {p: digest(new / p) for p in fn}
changed = sorted(str(p) for p in fb & fn if hb[p] != hn[p])
only = sorted(str(p) for p in fb ^ fn)
lines.append(f"## 1. Files\n{len(fb)} files in origin/main's render, {len(fn)} in the candidate's; only in one: "
             f"{only or 'none'}; different: {changed}\n")
if only or set(changed) - {"index.html", "bg.css"}:
    fail.append(f"files: only {only}, changed {changed}")

sb, sn = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (base, new))
rb, rn = sb.select("#headline-table tbody tr[data-box]"), sn.select("#headline-table tbody tr[data-box]")
lines.append(f"## 2. Numbers and boxes\nLeaderboard rows with a details box: origin/main {len(rb)}, candidate {len(rn)}.\n")
if len(rb) != len(rn):
    fail.append("row counts differ")
num_rows, chip_rows, num_diff, box_diff, chip_bad = [], [], 0, 0, 0
flat = lambda c: " ".join(sorted(c.elements(), key=lambda v: (float(v), v)))  # noqa: E731
TYPES = {"chat model": "chat", "decision model": "decision"}
for a, b in zip(rb, rn):
    box = a.get("data-box")
    if box != b.get("data-box"):
        fail.append(f"row order {box} / {b.get('data-box')}")
    if str(a.select_one(".hl-box")) != str(b.select_one(".hl-box")):
        box_diff += 1
        fail.append(f"{box}: box differs")
    # Numbers: row + box, the chip and the old small line out.
    ca, cb = BeautifulSoup(str(a), "html.parser"), BeautifulSoup(str(b), "html.parser")
    for el in ca.select("td.model > .hl-tag, td.model > span.small") + cb.select("td.model > .hl-tag, td.model > span.small"):
        el.decompose()
    na, nb_ = nums(text(ca)), nums(text(cb))
    eq = na == nb_
    num_diff += not eq
    num_rows.append((box, sum(na.values()), flat(na), flat(nb_), "yes" if eq else "NO"))
    if not eq:
        fail.append(f"{box}: numbers differ {na - nb_} / {nb_ - na}")
    # Chip against the data.
    sub, prog = "hl-sub" in (b.get("class") or []), "reference" in (b.get("class") or [])
    first = text(b.select_one(".hl-box p")).split(DOT)
    old_tag = text(a.select_one(".hl-tag")) if a.select_one(".hl-tag") else ""
    if prog:
        lg = next((m.group(1) for p in b.select(".hl-box p") if (m := re.fullmatch(r"League (\d+)", text(p)))), None)
        expect = DOT.join(([f"League {lg}"] if sub else []) + ["program"])
        setting = None
    else:
        kind = next((TYPES[p] for p in first if p in TYPES), None)
        i = first.index(next(p for p in first if p in TYPES)) if kind else None
        setting = first[i + 1] if kind and i + 1 < len(first) else None
        expect = DOT.join(p for p in (setting, kind, old_tag) if p)
    chips = b.select("td.model > .hl-tag")
    smalls = b.select("td.model > span.small")
    got = text(chips[0]) if chips else None
    old_name, new_name = text(a.select_one(".model-name")), text(b.select_one(".model-name"))
    want_name = old_name.removesuffix(f" ({setting})") if setting else old_name
    href_same = a.select_one(".model-name").get("href") == b.select_one(".model-name").get("href")
    ok = len(chips) == 1 and not smalls and got == expect and new_name == want_name and href_same
    chip_bad += not ok
    if not ok:
        fail.append(f"{box}: chip {got!r} (n={len(chips)}, smalls={len(smalls)}), expected {expect!r}; name {new_name!r} "
                    f"expected {want_name!r}; href same {href_same}")
    chip_rows.append((box, "program" if prog else "model", "other" if sub else "main", old_name, new_name, got, expect,
                      " · ".join(first), "yes" if ok else "NO"))
lines.append(f"Boxes differing: {box_diff}. Rows whose numbers (row + box, chip and old small line out) differ: {num_diff}.\n")
sb2, sn2 = (BeautifulSoup((d / "index.html").read_text(), "html.parser") for d in (base, new))
sb2.select_one("#headline-table").decompose()
sn2.select_one("#headline-table").decompose()
same_rest = text(sb2) == text(sn2)
lines.append(f"Home page outside the leaderboard table: text {'identical' if same_rest else 'DIFFERENT'}.\n")
if not same_rest:
    fail.append("home text outside the leaderboard differs")
lines.append(f"## 3. Chip and name vs data\n{len(chip_rows) - chip_bad} of {len(chip_rows)} rows ok (one chip, no other "
             f"small line; chip = setting · type from the box's first line + origin/main's late tag; programs 'program' / "
             f"'League n · program'; name = origin/main's minus ' (<setting>)'; link unchanged).\n\n"
             "| Box | Row | Name (main) | Name (candidate) | Chip | Expected | OK |\n|---|---|---|---|---|---|---|")
lines += [f"| {r[0]} | {r[1]}/{r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[8]} |" for r in chip_rows]
out.mkdir(parents=True, exist_ok=True)
for name, root, h in (("main", base, hb), ("candidate", new, hn)):
    (out / f"manifest-{name}.tsv").write_text("path\tsha256\tbytes\n" + "".join(
        f"{p}\t{h[p]}\t{(root / p).stat().st_size}\n" for p in sorted(h, key=str)))
with (out / "numbers.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["box", "numbers", "main (sorted, row + box, chip/small line out)", "candidate (same)", "equal"])
    w.writerows(num_rows)
with (out / "chips.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["box", "kind", "row", "name main", "name candidate", "chip", "expected", "box first line", "ok"])
    w.writerows(chip_rows)
(out / "compare.md").write_text("# Render comparison\n\n" + "\n".join(lines) + f"\n\n**Failures: {len(fail)}**\n"
                                + "".join(f"- {f}\n" for f in fail))
print(f"compare: {len(fail)} failures")
sys.exit(1 if fail else 0)
