"""The Highlights page's finding cards (Ümit #4178): four short cards under the decision slot, each one finding the
site already publishes (its title, two or three plain sentences in the source's own wording, one number line and a
link to the page that shows it).

Every number on a card is a span naming where the built site holds it: data-src (a file under the build's output),
data-path (a JSON list; an object in it picks the list element whose keys match) and data-fmt (how the page writes
it). The cards are rendered from S, the same values the source page shows; problems() re-reads every span from the
built files and fails the build where a card's number differs, or where a card shows a digit outside its number and
name spans. Three kinds are not in a data file and are read from the built source page instead: "rank" (the
leaderboard row's rank on index.html) and "quote" (a count of the finding, which must sit in the finding's own
sentence, data-path [sentence], on the source page)."""

import html
import json
import re
from pathlib import Path

import improve_page as IP
import story as ST
from common import count, esc, fmt, pct

LEAGUE_DATA = "data/v3/{}.json"
LATE_DATA = "data/v3/late-entries.json"
LEADERBOARD = "index.html"
SPAN = re.compile(r'<span class="hc-num" data-src="([^"]*)" data-path="([^"]*)" data-fmt="([^"]*)">([^<]*)</span>')
NAME = re.compile(r'<span class="hc-name">[^<]*</span>')


def num(text: str, src: str, path: list, kind: str) -> str:
    return (f'<span class="hc-num" data-src="{esc(src)}" data-path="{esc(json.dumps(path))}" data-fmt="{kind}">'
            f'{esc(text)}</span>')


def name(text: str) -> str:
    return f'<span class="hc-name">{esc(text)}</span>'


def row_path(x, *keys) -> tuple[str, list]:
    """(data file, path) of a leaderboard row's stored value: its league file, or the late-entries file."""
    if x["late"]:
        return LATE_DATA, ["entries", {"name": x["name"]}, *keys]
    return LEAGUE_DATA.format(x["ds"]), ["setups", x["name"], *keys]


def row_num(x, kind: str, part: str, *keys) -> str:
    """A leaderboard row's value as a number span: part "r" its risk metrics (stored under risk/main), "q" its quality."""
    v = x[part]
    for k in keys:
        v = v[k]
    stored = ("risk", "main", *keys) if part == "r" else ("quality", *keys)
    return num(pct(v) if kind == "pct" else fmt(v), *row_path(x, *stored), kind)


def tagged(x) -> str:
    """The row's name and, where the row has it, its late-entry tag (with provisional), for inside brackets."""
    tag = ST.late_tag(x)
    return name(x["name"]) + (f", {esc(tag)}" if tag else "")


def improve_card(S) -> dict:
    L = S["improve"]
    done = [(pm, m) for pm, _, m in IP.result_rows(L) if m is not None and m["verdict"]]
    src = IP.DATA
    line = " \u00b7 ".join(
        f'{name(pm["setup"])} '
        + num(fmt(m["before"]["risks_found"]), src, ["results", "models", {"setup": pm["setup"]}, "before", "risks_found"], "1")
        + " \u2192 "
        + num(fmt(m["after"]["risks_found"]), src, ["results", "models", {"setup": pm["setup"]}, "after", "risks_found"], "1")
        + ": " + num(m["status"], src, ["results", "models", {"setup": pm["setup"]}, "status"], "str")
        for pm, m in done)
    return dict(id="improve", title=IP.title(L), status=IP.eyebrow(L),
                text=("Each chat model wrote its own lessons over its games against GNUbg weak, then took the risk test "
                      "again. Yes or No is the pre-registered rule's: risks found must rise by more than the model's "
                      "threshold while right safety drops by no more than the plan allows; an operational threshold, not "
                      "a statistical test. The other models are still running; their numbers are not results yet."),
                line=f"Risks found before \u2192 after, finished models: {line}" if done else
                "No model has finished yet: every model is still running.",
                link=(IP.PATH, "Open Did they improve?"))


def cautious_card(S) -> dict:
    N = ST.two_skill_numbers(S)
    (f_lo, f_hi), (s_lo, s_hi) = N["ends"]["found"], N["ends"]["right_safety"]
    every = len(N["below"]) == len(N["models"])
    g = N["gnu"]
    line = ((num(count(len(N["models"])), "bench-scores.json", ["models"], "len") + " ranked models"
             if every else
             num(count(len(N["below"])), LEADERBOARD, [f'{count(len(N["below"]))} of the {count(len(N["models"]))} '
                                                      'ranked models'], "quote") + " of "
             + num(count(len(N["models"])), "bench-scores.json", ["models"], "len") + " ranked models")
            + f' \u00b7 risks found {row_num(f_lo, "pct", "r", "found", "share")} ({tagged(f_lo)}) to '
            f'{row_num(f_hi, "pct", "r", "found", "share")} ({tagged(f_hi)}) \u00b7 safe right '
            f'{row_num(s_lo, "pct", "r", "right_safety", "share")} ({tagged(s_lo)}) to '
            f'{row_num(s_hi, "pct", "r", "right_safety", "share")} ({tagged(s_hi)})'
            + (f' \u00b7 {name("GNUbg weak")}: {row_num(g, "pct", "r", "found", "share")} risks found, '
               f'{row_num(g, "pct", "r", "right_safety", "share")} safe right' if g else ""))
    return dict(id="cautious", title=N["heading"].rstrip("."), status=None,
                text=(f'{"Every" if every else "Most" if 2 * len(N["below"]) > len(N["models"]) else "Some"} ranked '
                      f'model{"" if every else "s"} found a worthwhile risk in a '
                      "smaller share of the positions where risk paid than the share of positions where safety paid "
                      f'that {"it" if every else "they"} played safe. GNUbg weak, a weak setting of the engine, is close '
                      "to even. Not paired: "
                      "models met different positions in different leagues."),
                line=line, link=("#finding-cautious", "The finding on the leaderboard page"))


def leaderboard_card(S) -> dict | None:
    ranked, _ = ST.leaderboard_rows(S)
    top = {}
    for i, (x, *_) in enumerate(ranked, 1):
        top.setdefault(ST.model_type(S, x), (i, x))
    if "chat" not in top or "decision" not in top:
        return None
    (ci, c), (di, d) = top["chat"], top["decision"]
    first, second = ("chat", "decision") if ci < di else ("decision", "chat")

    def part(i, x, typ):
        tag = ST.late_tag(x)
        return (f'{name(x["name"])} ({typ} model{", " + esc(tag) if tag else ""}): rank '
                f'{num(str(i), LEADERBOARD, [x["name"]], "rank")}, risk judgement {row_num(x, "1", "r", "judgement")}')
    return dict(id="leaderboard", title="Decision models and chat models at the top of the leaderboard", status=None,
                text=(f"The leaderboard ranks one row per model by risk judgement (higher is better). The "
                      f"best-ranked {second} model sits below the top {first} model. Models played in different "
                      "leagues, and a late entry played its league's field after the league finished, so the rows "
                      "compare only loosely."),
                line=f"{part(ci, c, 'chat')} \u00b7 {part(di, d, 'decision')}",
                link=("#headline-table", "Open the leaderboard"))


def reasoning_card(S) -> dict | None:
    N = ST.reasoning_numbers(S)
    if N is None:
        return None
    n, lo, hi = N["n"], N["er_lower"], N["rj_higher"]
    q = lambda v, sentence: num(count(v), LEADERBOARD, [sentence], "quote")  # noqa: E731
    model, _, xs = N["ex"]
    late = [f'{esc(x["setting"] or "")}: {esc(ST.late_tag(x))}' for x in xs if x["late"]]
    trend = ("Error rate fell for more of them than risk judgement rose." if lo > hi else
             "Risk judgement rose for as many of them as error rate fell, or more.")
    line = (f'{q(n, N["lead"])} models · lower error rate at the highest setting: {q(lo, N["counts"])} of '
            f'{q(n, N["counts"])} · higher risk judgement: {q(hi, N["counts"])} of {q(n, N["counts"])} · '
            f'{name(model)}, {esc(xs[0]["setting"] or "")} to {esc(xs[-1]["setting"] or "")}'
            + (f' ({"; ".join(late)})' if late else "")
            + f': risk judgement {", ".join(row_num(x, "1", "r", "judgement") for x in xs)}; error rate '
            + ", ".join(row_num(x, "1", "q", "error_rate") for x in xs))
    return dict(id="reasoning", title=N["heading"], status=None,
                text=("The same model at its lowest and its highest reasoning setting, in the same league. " + trend
                      + " Not paired: each setting played its own games; these are observed differences."),
                line=line, link=("#finding-reasoning", "The finding on the leaderboard page"))


def cards(S) -> list[dict]:
    return [c for c in (improve_card(S), cautious_card(S), leaderboard_card(S), reasoning_card(S)) if c]


def card_html(c: dict, status_badge) -> str:
    href = f"../{c['link'][0]}"
    return (f'<section class="card highlight-slot highlight-finding" id="highlight-{c["id"]}" data-slot="finding">'
            f'<h2>{esc(c["title"])}</h2>{status_badge(c["status"]) if c["status"] else ""}<p>{c["text"]}</p>'
            f'<p class="hc-line">{c["line"]}</p><p><a href="{href}">{esc(c["link"][1])}</a></p></section>')


# --- The build-time check ----------------------------------------------------------------------------------------

def _text(page: Path) -> str:
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", page.read_text(), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _resolve(out: Path, src: str, path: list):
    v = json.loads((out / src).read_text())
    for k in path:
        v = next(e for e in v if all(e.get(a) == b for a, b in k.items())) if isinstance(k, dict) else v[k]
    return v


def _shown(out: Path, src: str, path: list, kind: str, texts: dict):
    """What the built site holds for one span, written as the card writes it."""
    if kind == "rank":
        m = re.search(r'id="hl-(\d+)-box" role="group" aria-label="' + re.escape(esc(path[0])) + ': details"',
                      (out / src).read_text())
        return m and m.group(1)
    if kind == "quote":
        texts.setdefault(src, _text(out / src))
        return path[0] if path[0] in texts[src] else None
    v = _resolve(out, src, path)
    return dict(pct=pct, len=lambda v: count(len(v)), str=str).get(kind, fmt)(v)


def problems(out: Path, page: str = "highlights/index.html") -> list[str]:
    body = (out / page).read_text()
    secs = re.findall(r'<section class="card highlight-slot highlight-finding" id="([^"]+)".*?</section>', body, re.S)
    blocks = re.findall(r'<section class="card highlight-slot highlight-finding".*?</section>', body, re.S)
    bad = [] if len(blocks) == 4 else [f"{page}: {len(blocks)} finding cards, not 4"]
    texts = {}
    for cid, block in zip(secs, blocks):
        spans = SPAN.findall(block)
        if not spans:
            bad.append(f"{page}: card {cid} has no number span")
        for src, raw, kind, text in spans:
            path = json.loads(html.unescape(raw))
            text = html.unescape(text)
            try:
                want = _shown(out, src, path, kind, texts)
            except (KeyError, IndexError, StopIteration, FileNotFoundError, TypeError) as e:
                bad.append(f"{page}: card {cid}: {text!r} from {src} {path}: not in the built site ({e!r})")
                continue
            if kind == "quote" and (want is None or not re.search(rf"(?<![\d.]){re.escape(text)}(?![\d.])", want)):
                bad.append(f"{page}: card {cid}: {text!r}: the sentence {path[0]!r} is not on {src} with it")
            elif kind != "quote" and text != want:
                bad.append(f"{page}: card {cid}: shows {text!r}, the built {src} {path} gives {want!r}")
        rest = html.unescape(re.sub(r"<[^>]+>", " ", NAME.sub(" ", SPAN.sub(" ", block))))
        if re.search(r"\d", rest):
            bad.append(f"{page}: card {cid}: a digit outside its number spans: {rest.strip()[:120]!r}")
    return bad
