"""declutter (Ümit via Zeki #3521): origin/main's render against the candidate's, both built by build.py --no-image from
the same frozen live-state copy. Reads only.

usage: compare.py BASE_OUT NEW_OUT OUT_DIR
1. Files: every file of both renders hashed; only index.html, about/index.html and bg.css may differ.
2. Front page: origin/main's page with the moved blocks taken out (the hero's description, its three buttons, its board
   and each finding section's sentences, which the candidate replaces by its kept sentences) has the same text as the
   candidate's; each kept sentence is part of the old paragraph; the required caveats are on the candidate's page.
3. About: origin/main's text equal to the candidate's without 'From the front page' (section and its nav link); every
   moved block's text is in that section verbatim (the board: same SVG markup, links one level up).
4. Numbers: the numbers of both front pages plus About's moved section balance exactly (multiset).
5. Anchors: every id of origin/main's index.html and about/index.html exists on the same candidate page, or (front
   page) in its moved-anchors map; every id the moved board carries exists on About.
Writes OUT_DIR/compare.md, moved.csv, manifest-main.tsv, manifest-candidate.tsv; exits 1 on any failure."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

base, new, out = (Path(a) for a in sys.argv[1:4])
fail, lines = [], []
NUM = re.compile(r"[\u2212+-]?\d[\d,]*(?:\.\d+)?")
nums = lambda t: Counter(x.replace(",", "").replace("\u2212", "-").lstrip("+") for x in NUM.findall(t))  # noqa: E731
text = lambda el: re.sub(r"\s+", " ", el.get_text(" ")).strip()  # noqa: E731
soup = lambda p: BeautifulSoup(p.read_text(), "html.parser")  # noqa: E731
REQUIRED = [
    "Risk judgement: 100 = every call right, 50 = always safe; higher is better.",
    "One row per model at its highest reasoning setting, never its best score; late entries included.",
    "Ranks show observed scores; small gaps need not be meaningful.",
    "Leagues played different positions",
    "Unclear means the test can\u2019t tell, not that the scores are equal.",
    "every 99% interval includes 0, so the test does not show the groups' drops to differ.",
    "Not paired: models met different positions in different leagues.",
    "Models without a documented release month are left out.",
    "Preliminary: two plays shown, not league play.",
    "Not paired: each setting played its own games; these are observed differences.",
    "Paired positions, not league play; a drop mixes the new start with how hard the positions are.",
    "One model, a small pilot; the plan, every number and the lessons are on its page.",
    "Outside the groups, the late entry",
    "No arm reached the pre-registered signal threshold (plan section 8).",
]

# 1. Files
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
fb = {p.relative_to(base) for p in base.rglob("*") if p.is_file()}
fn = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
hb, hn = {p: digest(base / p) for p in fb}, {p: digest(new / p) for p in fn}
changed = sorted(str(p) for p in fb & fn if hb[p] != hn[p])
only = sorted(str(p) for p in fb ^ fn)
lines.append(f"## 1. Files\n{len(fb):,} files in origin/main's render, {len(fn):,} in the candidate's; only in one: "
             f"{only or 'none'}; different: {changed}.\n")
if only or set(changed) - {"index.html", "about/index.html", "bg.css"}:
    fail.append(f"files: only {only}, changed {changed}")

# 2. Front page
hb_, hn_ = soup(base / "index.html"), soup(new / "index.html")
ab_, an_ = soup(base / "about/index.html"), soup(new / "about/index.html")
sec = an_.select_one("section#front-page")
sec_text = text(sec) if sec else ""
moved, moved_rows = [], []


def take(el, what, where):
    t = text(el)
    ok = t in sec_text
    moved.append(t)
    moved_rows.append((what, where, len(t), sum(nums(t).values()), "yes" if ok else "NO", t))
    if not ok:
        fail.append(f"moved block not on About verbatim: {what}")
    el.decompose()


take(hb_.select_one(".hero-card .intro"), "hero description (p.intro)", "About #front-intro")
nav = hb_.select_one(".hero-card nav.hero-links")
moved_rows.append(("hero buttons: " + " / ".join(text(a) for a in nav.select("a")), "removed (the top bar's tabs: "
                   "Decisions, Highlights; Method in the footer/About)", len(text(nav)), 0, "n/a", text(nav)))
nav.decompose()
board_b = hb_.select_one(".hero-card figure.hero-board")
board_n = sec.select_one("figure.hero-board") if sec else None
same_board = bool(board_n) and str(board_b).replace('href="decisions/', 'href="../decisions/') == str(board_n)
board_ids = [e["id"] for e in board_b.select("[id]")]
lines.append(f"Hero board: on About with the same markup (links one level up): {'yes' if same_board else 'NO'}; "
             f"ids it carries: {board_ids or 'none'}.\n")
if not same_board:
    fail.append("hero board differs on About")
take(board_b, "hero board and caption (figure.hero-board)", "About #front-example")
kept_ok, kept_n = True, Counter()
for s in hb_.select("section.finding"):
    p = s.select_one("p.finding-text")
    p_new = hn_.select_one(f"section#{s['id']} p.finding-text")
    kept = text(p_new) if p_new else ""
    pieces = [x for x in re.split(r"(?<=\.)\s+(?=[A-Z])", kept) if x]
    if any(x not in text(p) for x in pieces):
        kept_ok = False
        fail.append(f"{s['id']}: a kept sentence is not in the old paragraph")
    if kept == text(p):
        moved_rows.append((f"#{s['id']} sentences", "kept in full on the front page", len(kept), sum(nums(kept).values()),
                           "n/a", kept))
        continue
    t = text(p)
    on_about = t in sec_text
    moved.append(t)
    kept_n += nums(kept)
    moved_rows.append((f"#{s['id']} sentences", f"About #text-{s['id']}" + (f"; front page keeps: {kept}" if kept else ""),
                       len(t), sum(nums(t).values()), "yes" if on_about else "NO", t))
    if not on_about:
        fail.append(f"{s['id']}: sentences not on About verbatim")
    if p_new:
        p.replace_with(BeautifulSoup(str(p_new), "html.parser"))
    else:
        p.decompose()
rest_b, rest_n = text(hb_), text(hn_)
same_home = rest_b == rest_n
lines.append(f"## 2. Front page\norigin/main's page, the moved blocks taken out and each finding's kept sentences put in: "
             f"text {'identical to' if same_home else 'DIFFERENT from'} the candidate's. Kept sentences each part of the "
             f"old paragraph: {'yes' if kept_ok else 'NO'}.\n")
if not same_home:
    fail.append("front page text differs beyond the moved blocks")
    import difflib
    lines.append("```\n" + "\n".join(difflib.unified_diff(rest_b.split(". "), rest_n.split(". "), lineterm="", n=0))[:4000] + "\n```\n")
home_new = text(soup(new / "index.html"))
req = [(r, r in home_new) for r in REQUIRED]
lines.append("Required lines on the candidate's front page, verbatim:\n\n| Line | On the page |\n|---|---|\n"
             + "".join(f"| {r} | {'yes' if ok else 'NO'} |\n" for r, ok in req))
fail += [f"required line missing: {r}" for r, ok in req if not ok]

# 3. About
an2 = soup(new / "about/index.html")
an2.select_one("section#front-page").decompose()
an2.select_one('a[href="#front-page"]').decompose()
same_about = text(an2) == text(ab_)
lines.append(f"## 3. About\nCandidate's about/index.html without 'From the front page' (section and nav link): text "
             f"{'identical to' if same_about else 'DIFFERENT from'} origin/main's.\n")
if not same_about:
    fail.append("about differs beyond the added section")

# 4. Numbers: old front page = new front page - the kept sentences + the moved blocks (whole); About gains exactly its
# new section, which holds the moved blocks plus the repeated headings.
old_home, new_home = nums(text(soup(base / "index.html"))), nums(home_new)
moved_n = sum((nums(t) for t in moved), Counter())
balance = old_home == (new_home - kept_n) + moved_n
old_about, new_about, sec_n = nums(text(ab_)), nums(text(soup(new / "about/index.html"))), nums(sec_text)
about_balance = new_about == old_about + sec_n
extra = sec_n - moved_n
lines.append(f"## 4. Numbers\nFront page: origin/main's numbers = the candidate's - its kept sentences + the moved blocks: "
             f"{'yes' if balance else 'NO'} ({sum(old_home.values()):,} numbers before, {sum(new_home.values()):,} after, "
             f"{sum(moved_n.values()):,} in moved blocks). About: the candidate's numbers = origin/main's + its new section's: "
             f"{'yes' if about_balance else 'NO'}; in that section beyond the moved blocks: {dict(extra) or 'none'}. No number changed: every number that left the front page is on About "
             f"in the same sentence.\n")
if not (balance and about_balance and not (moved_n - sec_n)):
    fail.append("numbers do not balance")

# 5. Anchors
ids = lambda s: {e["id"] for e in s.select("[id]")}  # noqa: E731
mv = json.loads(soup(new / "index.html").select_one("#moved-anchors").string)
home_ids_b, home_ids_n = ids(soup(base / "index.html")), ids(soup(new / "index.html"))
about_ids_b, about_ids_n = ids(ab_), ids(soup(new / "about/index.html"))
lost_home = sorted(i for i in home_ids_b - home_ids_n if i not in mv and i not in board_ids)
lost_board = sorted(i for i in board_ids if i not in about_ids_n)
lost_about = sorted(about_ids_b - about_ids_n)
lines.append(f"## 5. Anchors\nFront page: {len(home_ids_b):,} ids on origin/main's, {len(home_ids_n):,} on the "
             f"candidate's; lost (not on the page, not in the moved-anchors map): {lost_home or 'none'}. About: "
             f"{len(about_ids_b):,} ids before, {len(about_ids_n):,} after; lost: {lost_about or 'none'}; new: "
             f"{sorted(about_ids_n - about_ids_b)}. Board ids lost: {lost_board or 'none'}.\n")
if lost_home or lost_about or lost_board:
    fail.append(f"anchors lost: {lost_home + lost_about + lost_board}")

out.mkdir(parents=True, exist_ok=True)
for name, root, h in (("main", base, hb), ("candidate", new, hn)):
    (out / f"manifest-{name}.tsv").write_text("path\tsha256\tbytes\n" + "".join(
        f"{p}\t{h[p]}\t{(root / p).stat().st_size}\n" for p in sorted(h, key=str)))
with (out / "moved.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["block (origin/main front page)", "where it is now", "characters", "numbers", "on About verbatim", "text"])
    w.writerows(moved_rows)
(out / "compare.md").write_text("# Render comparison: origin/main against declutter\n\n" + "\n".join(lines)
                                + f"\n\n**Failures: {len(fail)}**\n" + "".join(f"- {f}\n" for f in fail))
print(f"compare: {len(fail)} failures")
for f_ in fail[:20]:
    print(" FAIL", f_)
sys.exit(1 if fail else 0)
