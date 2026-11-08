"""nav-ct review 3 (Ümit #2921): late entries in the leaderboard ranking. Reads only; no compute.
Usage: review3.py SRC_HEAD OLD_RENDER NEW_RENDER S_PICKLE OUT_DIR
SRC_HEAD: the extracted tools/site of nav-ct's HEAD (its formatting functions); OLD_RENDER: 90cd56e's retained render;
NEW_RENDER: HEAD's. Writes OUT_DIR/{render-diff.txt, numbers.csv, top15.md, text-moved.md, browser.csv, screenshots/}.
Exits 1 on any number difference, lost text or failed browser check."""
import csv
import mimetypes
import pickle
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

src, old, new, spk, out = (Path(a) for a in sys.argv[1:6])
sys.path.insert(0, str(src / "tools/site"))
import home as H  # noqa: E402
import pages as P  # noqa: E402
import story as St  # noqa: E402
from common import LATE_ENTRY, count, fmt, pct  # noqa: E402

out.mkdir(parents=True, exist_ok=True)
(out / "screenshots").mkdir(exist_ok=True)
S = pickle.load(open(spk, "rb"))
fail = []
log = lambda *a, **k: print(*a, flush=True, **k)

# --- 1. Render diff: every file identical except the home page, About and bg.css ---------------------------------------
fa = {p.relative_to(old) for p in old.rglob("*") if p.is_file()}
fb = {p.relative_to(new) for p in new.rglob("*") if p.is_file()}
diff = sorted(str(r) for r in fa & fb if (old / r).read_bytes() != (new / r).read_bytes())
expect = {"index.html", "about/index.html", "bg.css"}
lines = [f"{len(fa)} / {len(fb)} files; only in one: {sorted(map(str, fa ^ fb))}",
         f"identical {len(fa & fb) - len(diff)}; differing: {diff}"]
if fa ^ fb or set(diff) - expect:
    fail.append("render diff: unexpected files differ")
(out / "render-diff.txt").write_text("\n".join(lines) + "\n")
log(*lines, sep="\n")

soup = lambda root, p="": BeautifulSoup((root / p / "index.html").read_text(), "html.parser")
ho, hn = soup(old), soup(new)
txt = lambda el: re.sub(r"\s+", " ", el.get_text(" ")).strip()

# The rest of the home page (outside the leaderboard card and the result cards) is unchanged.
for h in (ho, hn):
    for el in h.select("#leaderboard, .result-cards"):
        el.decompose()
rest_same = txt(ho.body) == txt(hn.body)
log("home outside #leaderboard and the result cards unchanged:", rest_same)
if not rest_same:
    fail.append("home page changed outside the leaderboard and the cards")
ho, hn = soup(old), soup(new)

# --- 2. Numbers: every number of every leaderboard row, details box and result card against S (label-aware) ------------
setups = {}
for lg in S["leagues"]:
    for n, s in lg["setups"].items():
        setups[(lg["dataset"], P.meta(S, lg["dataset"], n)["slug"])] = (lg, n, s)
late = {(LATE_ENTRY, e["slug"]): e for e in S["late_entries"]}
risk = {}
for lg, n, r, ref in H.all_rows(S):
    risk[(lg["dataset"], H.slug_name(n))] = (lg, n, r)
    if not ref:
        risk[(lg["dataset"], P.meta(S, lg["dataset"], n)["slug"])] = (lg, n, r)
rows_csv, nd = [], 0


def expected(ds, slug):
    """{label: expected text} of the setup's numbers, from S."""
    e = late.get((ds, slug))
    if e:
        r, q, rec, name = e["risk"]["main"], e["quality"], e["record"], e["name"]
    else:
        lg, name, r = risk[(ds, slug)]
        q = lg["setups"][name]["quality"] if name in lg["setups"] else None
        rec = next((s for s in lg["standings"] if s["name"] == name), None)
    x = {"judgement": f'{fmt(r["judgement"])} (95%: {fmt(r["judgement_lo"])}\u2013{fmt(r["judgement_hi"])})',
         "bar": f'{fmt(r["judgement"])} {fmt(r["judgement_lo"])} to {fmt(r["judgement_hi"])}'}
    f, sf = r["found"], r["right_safety"]
    if f["den"]:
        x["found"], x["took"] = pct(f["share"]), f'{H.n_(f["n"])} of {H.n_(f["den"])}'
    if sf["den"]:
        x["safe"], x["safe_n"] = pct(sf["share"]), f'{H.n_(sf["n"])} of {H.n_(sf["den"])}'
    if q and q.get("error_rate") is not None and not q.get("too_few"):
        x["error"] = f'{fmt(q["error_rate"])} (95%: {fmt(q["error_lo"])}\u2013{fmt(q["error_hi"])})'
    if rec:
        x["record"] = f'{count(rec["won"])}\u2013{count(rec["drawn"])}\u2013{count(rec["lost"])}'
    if q and q.get("usd_per_1000") is not None:
        x["cost"] = f'${fmt(q["usd_per_1000"], 3)}'
    if q:
        x["decisions"] = count(q["decisions"])
    if e and e["status"] == P.PROVISIONAL:
        x["played"] = f'{count(e["played"])} of {count(e["total"])}'
    if e:
        x["field"] = f'League {e["field_league"]} field'
    return x


PAT = {"judgement": r"Risk judgement ([\d.]+ \(95%: [\d.]+\u2013[\d.]+\))", "found": r"Risks found ([\d.]+%)",
       "safe": r"safe right ([\d.]+%)", "took": r"Took ([\d,]+ of [\d,]+) risks", "safe_n": r"played safe in ([\d,]+ of [\d,]+) positions",
       "error": r"Error rate ([\d.]+ \(95%: [\d.]+\u2013[\d.]+\))", "record": r"record (\d+\u2013\d+\u2013\d+)",
       "cost": r"(\$[\d.,]+) per 1,000", "decisions": r"(?<!per )(?<![\d,])([\d,]+) decisions", "played": r"Provisional: (\d+ of \d+) matches",
       "field": r"original (League \d field) after the league finished \(late entry\)"}
hl = hn.find(id="headline-table")
for tr in hl.select("tbody tr[data-setup]"):
    k = (tr["data-dataset"], tr["data-setup"])
    if "reference" in (tr.get("class") or []) and k not in late and k not in risk:
        continue
    want = expected(*k)
    box = tr.find(class_="hl-box")
    bt = box.get_text(" ")
    bt = re.sub(r"\s+", " ", bt)
    got = {lab: (m.group(1) if (m := re.search(p, bt)) else None) for lab, p in PAT.items()}
    bar = tr.find(class_="hl-val")
    got["bar"] = re.sub(r"\s+", " ", bar.get_text(" ")).strip() if bar else None
    for lab in set(want) | {g for g, v in got.items() if v is not None}:
        ok = want.get(lab) == got.get(lab)
        rows_csv.append(["leaderboard", f"{k[0]}/{k[1]}", lab, want.get(lab), got.get(lab), "ok" if ok else "DIFF"])
        nd += not ok

# The result cards, against the same values recomputed here from S (late entries counted).
cand = [(n, f'League {lg["id"]}', P.origin_meta(S, lg["dataset"], n), r, lg["setups"][n]["quality"] if n in lg["setups"] else None)
        for lg, n, r, ref in H.all_rows(S) if not ref]
cand += [(e["name"], f'late entry, League {e["field_league"]} field', S["setups_meta"].get((LATE_ENTRY, e["name"])) or {},
          e["risk"]["main"], e["quality"]) for e in S["late_entries"]]
j = [c for c in cand if c[3]["judgement"] is not None]
best = max(j, key=lambda c: c[3]["judgement"])
dec = max((c for c in j if H.kind(c[2]) == "decision"), key=lambda c: c[3]["judgement"])
low = min((c for c in cand if c[4] and c[4].get("error_rate") is not None and not c[4].get("too_few")),
          key=lambda c: c[4]["error_rate"])
want_cards = [f'{fmt(best[3]["judgement"])} /100, higher is better {best[0]} · {best[1]} · 95% interval {fmt(best[3]["judgement_lo"])} to {fmt(best[3]["judgement_hi"])}',
              f'{fmt(dec[3]["judgement"])} /100, higher is better {dec[0]} · {dec[1]} · 95% interval {fmt(dec[3]["judgement_lo"])} to {fmt(dec[3]["judgement_hi"])}',
              f'{fmt(low[4]["error_rate"])} PR, lower is better {low[0]} · {low[1]} · 95% interval {fmt(low[4]["error_lo"])} to {fmt(low[4]["error_hi"])}']
got_cards = [txt(c)[len(txt(c.h2)):].strip() for c in hn.select(".result-cards .result-card")]
for i, (w, g) in enumerate(zip(want_cards, got_cards), 1):
    rows_csv.append(["result card", str(i), "card", w, g, "ok" if w == g else "DIFF"])
    nd += w != g
nd += len(want_cards) != len(got_cards)
old_cards = [txt(c) for c in ho.select(".result-cards .result-card")]
with open(out / "numbers.csv", "w", newline="") as f:
    csv.writer(f).writerows([["where", "setup", "label", "data (S)", "page", "result"]] + rows_csv)
log(f"numbers: {len(rows_csv)} values, {nd} differences")
log("cards before:", old_cards)
log("cards now:", got_cards)
if nd:
    fail.append(f"{nd} number differences")

# --- 3. Top 15 and the moved text -----------------------------------------------------------------------------------
ranked, progs = St.leaderboard_rows(S)
oldrank = [txt(tr.find(class_="model-name")) for tr in ho.find(id="headline-table").select("tbody tr[data-setup]:not(.hl-sub):not(.reference)")]
md = ["| # | Row | Setup shown | Setting | Risk judgement (95%) | Tag | Other settings | Rank at 90cd56e |", "|---:|---|---|---|---|---|---|---:|"]
for i, (x, others, name, g) in enumerate(ranked, 1):
    r = x["r"]
    md.append(f'| {i} | {name} | {x["name"]} | {x["setting"] or "(single setup)"} | {fmt(r["judgement"])} ({fmt(r["judgement_lo"])}\u2013'
              f'{fmt(r["judgement_hi"])}) | {St.late_tag(x) or ""} | {", ".join(y["name"] + (" (late entry)" if y["late"] else "") for y in others)} | '
              f'{oldrank.index(name) + 1 if name in oldrank else "not ranked"} |')
(out / "ranking.md").write_text("\n".join(md) + "\n")
log("\n".join(md[:17]))

ab = txt(soup(new, "about").find(id="leaderboard"))
abt = lambda s: re.sub(r"\s+", " ", s).strip()
moved = [txt(ho.select_one(".headline-scope")), txt(ho.select_one(".hl-legend")), txt(ho.select_one(".headline-rule"))]
newtop = [txt(hn.select_one("#leaderboard .chart-sub")), txt(hn.select_one(".headline-scope"))]
# Each sentence of the old text above and under the table, on About (as worded there).
REWORD = {"A fixed table: the filters below do not change it.": "A fixed table: the filters below the leaderboard do not change it.",
          "Tap a model (or point at it) for its details and its decisions; how each row is chosen is under the table.":
              "Tap a model (or point at it) for its details and its decisions.",
          "# is the rank among all models, in every view; the programs are reference rows in every view.":
              "# is the rank among all models, in every view of the table's All · Chat models · Decision models filter; the programs are reference rows in every view."}
tm = ["| Old text (90cd56e home) | On About (#leaderboard) | Found |", "|---|---|---|"]
for block in moved:
    for s in re.split(r"(?<=\.) (?=[A-Z#])", block):
        w = REWORD.get(s, s)
        w2 = w.replace("never its best score.", "never its best score;")
        found = w in ab or w2 in ab or w.rstrip(".") in ab
        tm.append(f"| {s} | {w if w != s else '(same)'} | {'yes' if found else 'NO'} |")
        if not found:
            fail.append(f"text lost: {s}")
tm.append("")
tm.append("Above the table now: " + " / ".join(newtop))
tm.append("Under the table (rule line): " + txt(hn.select_one(".headline-rule")))
(out / "text-moved.md").write_text("\n".join(tm) + "\n")
log("\n".join(tm))

# --- 4. Browser: 1280 and 390, light and dark --------------------------------------------------------------------------
def router(root):
    def serve(route):
        f = root / unquote(urlparse(route.request.url).path).lstrip("/")
        if f.is_dir():
            f = f / "index.html"
        if not f.is_file():
            return route.fulfill(status=404, body="not found")
        route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or "application/octet-stream")
    return serve


SITE = "http://site.test/"
late_rows = {e["slug"]: e for e in S["late_entries"]}
sub_late = {y["late"]["slug"]: name for x, others, name, g in ranked for y in others if y["late"]}
n_ranked = len(ranked)
br_rows = []
check = lambda w, t, name, obs, ok: (br_rows.append([w, t, name, obs, "ok" if ok else "WRONG"]), ok or fail.append(f"browser {w} {t}: {name}"))
with sync_playwright() as p:
    br = p.chromium.launch()
    for width in (1280, 390):
        touch = width < 500
        for theme in ("light", "dark"):
            ctx = br.new_context(viewport={"width": width, "height": 900 if not touch else 844}, has_touch=touch, is_mobile=touch)
            ctx.add_init_script(f"try {{ localStorage.setItem('theme','{theme}'); }} catch (e) {{}}")
            ctx.route("http://site.test/**", router(new))
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(SITE)
            page.wait_for_timeout(500)
            shot = lambda n: page.screenshot(path=str(out / "screenshots" / f"{n}-{width}-{theme}.png"))
            th = page.evaluate("document.documentElement.dataset.theme || document.documentElement.className")
            check(width, theme, "theme applied", th, theme in str(th))
            # Top boxes.
            cards = page.eval_on_selector_all(".result-cards .result-card", "e => e.map(c => c.innerText.replace(/\\s+/g,' ').trim())")
            check(width, theme, "result cards: 3 visible, Astra (high) 8.8 late entry lowest error rate",
                  " | ".join(cards), len(cards) == 3 and "8.8" in cards[2] and "GPT-6 Astra (high)" in cards[2] and "late entry" in cards[2])
            page.locator(".result-cards").scroll_into_view_if_needed()
            shot("result-cards")
            # Rows: ranks 1..N in order, programs after.
            rows = page.evaluate("""() => [...document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub)')]
                .filter(e => e.offsetParent).map(r => [r.cells[0].innerText.trim(), r.querySelector('.model-name').innerText.trim(),
                r.classList.contains('reference'), (r.querySelector('.hl-tag') || {}).innerText || ''])""")
            ranks = [r[0] for r in rows if not r[2]]
            check(width, theme, f"ranked rows 1..{n_ranked} in order, 3 programs", f"{len(ranks)} ranked, {sum(r[2] for r in rows)} programs; top 5 "
                  + ", ".join(r[1] for r in rows[:5]), ranks == [str(i) for i in range(1, n_ranked + 1)] and sum(r[2] for r in rows) == 3
                  and [r[1] for r in rows if not r[2]] == [t[2] for t in ranked])
            tags = {r[1]: r[3] for r in rows if r[3]}
            want_tags = {name: St.late_tag(x) for x, o, name, g in ranked if x["late"]}
            check(width, theme, f"tags on the {len(want_tags)} late-entry rows", "; ".join(f"{k}: {v}" for k, v in tags.items()),
                  tags == want_tags)
            page.evaluate("document.getElementById('leaderboard').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(150)
            shot("leaderboard-top")
            # Details boxes of every late entry (Drex 2.0 (local) through its expander).
            okn, bad = 0, []
            for slug, e in late_rows.items():
                tr = page.locator(f'#headline-table tr[data-dataset="{LATE_ENTRY}"][data-setup="{slug}"]')
                if slug in sub_late:
                    parent = page.locator('#headline-table tr:not(.hl-sub)', has=page.locator(".model-name", has_text=sub_late[slug])).first
                    btn = parent.locator(".hl-more")
                    if btn.get_attribute("aria-expanded") != "true":
                        btn.click()
                    sub_tag = tr.locator(".hl-tag").inner_text()
                    if sub_tag != St.late_tag({"late": e}):
                        bad.append(f"{e['name']} sub-row tag {sub_tag!r}")
                name = tr.locator(".model-name")
                name.scroll_into_view_if_needed()
                (name.tap() if touch else name.hover())
                page.wait_for_timeout(150)
                box = tr.locator(".hl-box")
                vis = box.is_visible()
                bt = box.inner_text() if vis else ""
                need = [f"Played the original League {e['field_league']} field after the league finished (late entry)"]
                if e["status"] == P.PROVISIONAL:
                    need.append(f"Provisional: {e['played']} of {e['total']} matches")
                    need += [f"not played: {g['opponent']} ({g['reason']})" for g in e["not_played"]]
                if e["name"] == P.SUBQ_11:
                    need.append(P.SUBQ_SELF)
                miss = [n for n in need if n not in bt]
                if vis and not miss:
                    okn += 1
                else:
                    bad.append(f"{e['name']}: visible {vis}, missing {miss}")
                if e["name"] in ("GPT-6 Astra (high)", "REAX 1.3", "SubQ Snap 1.1", "Drex 2.0 (local)"):
                    shot("box-" + slug)
                if touch:
                    name.tap()  # second tap closes
                    page.wait_for_timeout(100)
                else:
                    page.mouse.move(1, 1)
                    page.wait_for_timeout(100)
            check(width, theme, f"details box of every late entry ({len(late_rows)}): late line, provisional line, SubQ note",
                  f"{okn} ok; " + "; ".join(bad), okn == len(late_rows) and not bad)
            # Filter: chat / decision / all keep the ranks and the late entries of that type.
            for state in ("chat", "decision", "all"):
                page.locator(f'[data-hl-filter="{state}"]').click()
                page.wait_for_timeout(100)
                vis = page.evaluate("""() => [...document.querySelectorAll('#headline-table tbody tr[data-setup]:not(.hl-sub)')]
                    .filter(e => e.offsetParent).map(r => [r.cells[0].innerText.trim(), r.querySelector('.model-name').innerText.trim(),
                    r.dataset.hlType])""")
                want = [(str(i), t[2]) for i, t in enumerate(ranked, 1) if state == "all" or St.model_type(S, t[0]) == state]
                got = [(a, b) for a, b, c in vis if c != "program"]
                lates = [b for a, b in got if b in want_tags]
                check(width, theme, f"filter {state}: rows, ranks kept, programs shown",
                      f"{len(got)} rows, late entries shown: {', '.join(lates)}; programs {sum(c == 'program' for a, b, c in vis)}",
                      got == want and sum(c == "program" for a, b, c in vis) == 3)
                if state == "decision":
                    page.evaluate("document.getElementById('headline-table').scrollIntoView({block: 'start'})")
                    page.wait_for_timeout(150)
                    shot("filter-decision")
            page.goto(SITE + "about/#leaderboard")
            page.wait_for_timeout(300)
            at = page.locator("#leaderboard").inner_text()
            check(width, theme, "About: How the leaderboard is built", at[:90].replace("\n", " ") + "…", "highest reasoning setting" in at)
            shot("about-leaderboard")
            page.goto(SITE)
            page.wait_for_timeout(300)
            sw = page.evaluate("document.documentElement.scrollWidth")
            check(width, theme, "home page no wider than the window", f"scrollWidth {sw}", sw <= width)
            check(width, theme, "script errors", "; ".join(errs) or "none", not errs)
            ctx.close()
    br.close()
with open(out / "browser.csv", "w", newline="") as f:
    csv.writer(f).writerows([["width", "theme", "check", "observed", "result"]] + br_rows)
log(f"browser: {sum(r[4] == 'ok' for r in br_rows)}/{len(br_rows)} ok")
for r in br_rows:
    if r[4] != "ok":
        log("WRONG:", r)
log("failures:", fail or "none")
sys.exit(1 if fail else 0)
