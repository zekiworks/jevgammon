"""Shared helpers for the backgammon site build: slugs, formatting, thresholds."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = Path(__file__).resolve().parent
CONTENT = SITE / "content"

THRESHOLDS = json.loads((CONTENT / "thresholds.json").read_text())
# The values of the Method specification of 24 Oct 2026 (content/method-spec-2026-10-24.md), fixed before computing.
SPEC = json.loads((CONTENT / "analysis_2026-10-24.json").read_text())

# Status words (brief B10).
PUBLISHED, PROVISIONAL, EARLIER, PENDING, NOT_MEASURED, NA = (
    "Published", "Provisional", "Earlier version", "Analysis pending", "Not measured", "N/A")
TOO_FEW = "Too few decisions"
PROVISIONAL_NOTE = "Provisional: league still running"
# The line above the home page's All leagues table (Can, approved by Ümit, 30 Oct 2026), verbatim.
ALL_NOTE = "Leagues played different positions; close scores across leagues need not mean a real difference."
# Late entries (matches.stage 'late-entry'): their own dataset id, label and status note; never in a standings table.
LATE_ENTRY = "late-entry"
LATE_ENTRY_LABEL = "Late entry, not in standings"
LATE_ENTRY_NOTE = "Provisional: late entry still playing"
# Pairs outside the requested scope (Ümit via Zeki #5220, 12 Nov 2026): a late entry's or repeat's pair with these
# opponents (raw player names) is not work still to do. The pair stays unplayed, never a score or a loss, and the reason
# it was not played stays beside this label; results recorded before are kept.
OUT_OF_SCOPE = "outside the requested scope (Ümit, 12 Nov)"
OUT_OF_SCOPE_OPPONENTS = frozenset({"GPT-6 Luna", "Mercury Decide"})


def unplayed_text(g: dict) -> str:
    """One unplayed pair of a late entry (build.late_entry_summaries' not_played item), plain text: 'not played: X
    (reason)', or for a pair outside the requested scope 'X: outside the requested scope (Ümit, 12 Nov); not played
    (reason)'."""
    if g.get("out_of_scope"):
        return f'{g["opponent"]}: {OUT_OF_SCOPE}; not played ({g["reason"]})'
    return f'not played: {g["opponent"]} ({g["reason"]})'


# Setups not shown yet (content/held_setups.json, name: reason): a late entry still playing is held until its entry is
# complete, so no moving partial numbers are published; analysis.late_entries and cup.classify leave them out, so no
# page, data file, leaderboard row, bench score or model list carries them.
_HELD_FILE = json.loads((CONTENT / "held_setups.json").read_text())
HELD = _HELD_FILE["held"]
# Held late entries shown while they play (held_setups.json "running", name: its late-entry league and what the row's
# details say): one unranked row on the home leaderboard, no score anywhere (analysis.running_entries,
# story.running_rows); every other page, data file and bench score still leaves them out, as HELD says.
RUNNING = _HELD_FILE.get("running", {})
assert set(RUNNING) <= set(HELD), "held_setups.json: a running entry must also be held"
# Results under QC (content/qc_status.json; QC 2026-11-12, Ümit via Zeki #5264/#5276), shown until their Run 2 lands:
# "improve" by 'Did they improve?' model key, "setups" by shown setup name, each with its note.
_QC_FILE = json.loads((CONTENT / "qc_status.json").read_text())
QC_LABEL = "QC-pending"
QC_IMPROVE = _QC_FILE["improve"]
QC_SETUPS = _QC_FILE["setups"]
# Published Run 2 reports of 'Did they improve?' (content/run2/<model key>.json, copied unchanged from the QC rerun's
# run2-report.json), by model key: the row's verdict is Run 2's; the original stays in improve.json and the details box.
RUN2 = {r["model"]: r for r in (json.loads(p.read_text()) for p in sorted((CONTENT / "run2").glob("*.json")))}
# Close choices, stage B: scope note (Ümit, 2026-10-25; Method spec 2026-10-24 §9.13 addendum of 16:05 UTC), verbatim on
# the home page and the Method page.
CLOSE_B_SCOPE_NOTE = ("Gemma 4 31B (on) was started but not completed: two reboots and a GPU fault interrupted it, and it "
                      "was stopped after 311 of 500 play calls on 2026-10-25. Its partial data is not reported.")
# Nackgammon paired test: scope note (Method spec 2026-10-24 §10.14(c), replacing §10.10's), verbatim wherever group
# results appear; nack_paired_verify.py checks it against the scorer's "scope_note".
NACK_SCOPE_NOTE = ("These results hold for these rosters only; each group is the setups in the run from that original "
                   "league.")
EARLIER_NOTE = ("Earlier version: plays were listed in the runner's order, which tends to put the best play early.")

# B7 publishing rule: no internal hostnames, IP addresses, ports, server paths, keys, tokens or request headers in any
# published file (pages, JSON downloads, decision files); the pre-deploy check scans every file for these.
BANNED = re.compile(r"192\.168\.|127\.0\.0|\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d|localhost|"
                    r"https?://[\w.-]+:\d{2,5}|/home/|/root/|/mnt/|bariton|spark-|\bsk-[\w-]{8}|base_url|"
                    r"api[_-]key|Bearer [\w.-]{8}|[Aa]uthorization:|x-api-key|decision-models")

# The suite strip at the top of every page (Ümit, bus #2270; the shared component of the Decision models site, #2290):
# content/suite-bar.html is its snippet, copied verbatim; this site marks its own link (Backgammon) as the current page.
# Its first link names the other benchmark's address, which BANNED forbids; the one exception (Zeki, bus #2287, from
# Ümit #2270) is this exact element, once per page, which checks.py takes out of a page before its private-strings scan.
_SUITE_HTML = (CONTENT / "suite-bar.html").read_text()
SUITE_BAR = re.search(r'<nav class="suite-bar".*?</nav>', _SUITE_HTML, re.S).group(0).replace(
    '<a href="/analysis/backgammon/">', '<a href="/analysis/backgammon/" aria-current="page">')
assert SUITE_BAR.count('aria-current="page"') == 1


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Setup display names (content/labels.json, 28 Oct 2026): setups are named by the reasoning effort they sent. The
# databases keep the old names; the site computes with them and shows the new ones.
LABELS = json.loads((CONTENT / "labels.json").read_text())
# Model display names (labels.json "models", Ümit #4282 item 4): the Logic & Math and Reading feeds' name for the model.
MODEL_NAMES = {old: v["name"] for old, v in LABELS["models"].items()}
_MODEL = re.compile(r"^(" + "|".join(re.escape(m) for m in sorted(MODEL_NAMES, key=len, reverse=True))
                    + r")((?: \([^()]*\))*)$")
_EFFORT = {old: v["name"] for old, v in LABELS["renamed"].items()}


def label(name: str) -> str:
    """The name a setup or model is shown under: its effort name (labels.json "renamed"), then its model's display
    name ("models") for '<model>' and '<model> (<setting>)'. Exact forms only; other strings are untouched."""
    name = _EFFORT.get(name, name)
    m = _MODEL.match(name)
    return MODEL_NAMES[m.group(1)] + m.group(2) if m else name


# Every renamed setup or model name on record (labels.json, setups.json) -> its shown name.
_SETUPS = json.loads((CONTENT / "setups.json").read_text())["setups"]
RENAMED = {old: label(old) for old in [*_EFFORT, *MODEL_NAMES, *(s[k] for s in _SETUPS for k in ("name", "model"))]
           if label(old) != old}
INTERNAL = {}
for _old, _new in RENAMED.items():
    # The first old name on record wins: a league setup's (labels.json's effort renames come first).
    INTERNAL.setdefault(_new, _old)
# Outside the leagues (the v1 set, smoke rows): (dataset, shown name) -> the setups.json name its slug comes from.
_RECORDED = {(s["dataset"], label(s["name"])): s["name"] for s in _SETUPS if not s["dataset"].startswith("league-")}
# What a shown name does not tell (on the setup's model page), by shown name.
NAME_NOTES = LABELS["notes"]
# What the Reasoning tab says about how a model's two settings differ, by model (where its names don't tell).
REASONING_NOTES = LABELS["reasoning_notes"]

# Names (Ümit #4445; logic #4447/#4487/#4517, turkce #4449, Zeki #4448/#4484; content/labels.json "_names_about"): a page
# shows the maker's official model name only; how we ran a setup (setting, route, snapshot) is the small grey tag beside
# it. The model-level facts come from the three sites' shared names file (content/model_names.json, its sha256 pinned
# in labels.json) by model key; the routes are this site's (labels.json "routes", "routes_v1"). The computed state, data
# files, slugs and keys keep the shown names above: the split is made where a name is shown.
MODEL_NAMES_FILE = CONTENT / "model_names.json"
NAMES_SHA256 = LABELS["model_names_sha256"]
SHARED_NAMES = {v["model_key"]: v for v in json.loads(MODEL_NAMES_FILE.read_text())["models"].values()}
_NAME_KEYS = LABELS["name_keys"]
ROUTES = LABELS["routes"]
ROUTES_V1 = LABELS["routes_v1"]
_ROUTE_WORDS = set(LABELS["route_words"])
PROGRAM_NAMES = ("GNUbg weak", "Random", "Safest")


def model_key(model: str) -> str:
    """The model's cross-site key (bench-scores.json model_key, content/model_names.json): its shown name without a
    parenthesised note, lower case, spaces to '-', dots kept: 'gpt-6-astra', 'perplexity-decider-27b-v1.2'."""
    return re.sub(r"\s+", "-", re.sub(r"\s*\([^)]*\)", "", model).strip().lower())


def shared_entry(model: str) -> dict:
    """The model's row in the shared names files (logic's file first), {} where it has none."""
    key = model_key(model)
    return SHARED_NAMES.get(_NAME_KEYS.get(key, key)) or {}


def official(model: str) -> str:
    """The maker's official name of a shown model name (the shared rows'), else the shown name without '(…)'."""
    return shared_entry(model).get("name") or re.sub(r"\s*\([^)]*\)", "", model).strip()


def snapshot(model: str) -> str | None:
    """The snapshot or version that tells this model apart from another of the same official name ('1017', 'v1.2')."""
    return shared_entry(model).get("snapshot")


def base_model(model: str) -> str | None:
    return shared_entry(model).get("base_model")


# Every shown model name on record (setups.json, the planned rows of "Did they improve?", the Nackgammon-only setups,
# the parameter file), longest first: a setup's name is its model's name and its suffixes.
_PLANNED = json.loads((CONTENT / "improve_planned.json").read_text())["rows"]
_NACK_ONLY = json.loads((CONTENT / "nack_setup_types.json").read_text())["setups"]
_MODELS_SHOWN = sorted({label(s["model"]) for s in _SETUPS} | {label(r["params_model"]) for r in _PLANNED if r["params_model"]}
                       | {label(v["model"]) for v in _NACK_ONLY.values()}
                       | {label(m) for m in json.loads((CONTENT / "model_params.json").read_text())["models"]},
                       key=len, reverse=True)
_SUFFIXES = re.compile(r"(?: \([^()]*\)| \[[^\[\]]*\])*")


def _model_and_suffixes(shown: str) -> tuple[str, list[str]]:
    """(model, the parenthesised or bracketed suffixes after it) of a shown setup name; a name of no known model: the
    name without its trailing suffixes."""
    for m in _MODELS_SHOWN:
        if shown.startswith(m) and _SUFFIXES.fullmatch(shown[len(m):]):
            break
    else:
        m = re.sub(r"(?: \([^()]*\)| \[[^\[\]]*\])+$", "", shown)
    return m, re.findall(r" [(\[]([^()\[\]]*)[)\]]", shown[len(m):])


def route(shown: str, dataset: str | None = None) -> str | None:
    """How a setup ran, as its tag names it (labels.json "routes"): the machine on our hardware, 'API' where another
    setup of the same name ran otherwise, 'Decisions API'. The v1 set its own (routes_v1); a smoke-test or Nackgammon
    setup none (not on record)."""
    if dataset is None or dataset.startswith("league-") or dataset == LATE_ENTRY:
        return ROUTES.get(shown)
    return ROUTES_V1.get(shown) if dataset == "v1-set" else None


def name_and_tag(shown: str, dataset: str | None = None) -> tuple[str, list[str]]:
    """(official name, tag parts) of a shown setup or model name: setting · route · snapshot ('low · API · 1017'); a
    version that tells apart two models of one product name stands before the route ('v1.2 · NVIDIA RTX PRO 6000
    Blackwell', GLiDE: Main's brief, logic #4447); a program (GNUbg weak, Safest, Random) as it is. dataset: the
    setup's (its route), None for the leagues and late entries."""
    if shown.split(" (")[0] in PROGRAM_NAMES:
        return shown, []
    model, extra = _model_and_suffixes(shown)
    way, snap = route(shown, dataset), snapshot(model)
    if way:
        extra = [x for x in extra if x not in _ROUTE_WORDS]
    parts = [*extra, snap, way] if snap and re.match(r"v\d", snap) else [*extra, way, snap]
    return official(model), [p for p in parts if p]


def tag_text(parts) -> str:
    return " \u00b7 ".join(p for p in parts if p)


def name_text(shown: str, dataset: str | None = None) -> str:
    """The name with its tag as plain text (option lists, tooltips, aria labels, chart text, download fields):
    'Gemma 4 31B (on · …)', as logic's Run.shown."""
    name, parts = name_and_tag(shown, dataset)
    return f"{name} ({tag_text(parts)})" if parts else name


def tag_html(text: str) -> str:
    """A setup's tag as the small grey text after its name (Ümit #4445); '' without one."""
    return f'<span class="name-tag">{esc(text)}</span>' if text else ""


def name_html(shown: str, dataset: str | None = None) -> str:
    """The official name, then its tag."""
    name, parts = name_and_tag(shown, dataset)
    return esc(name) + tag_html(tag_text(parts))


# The shown names a page must not show as they are: every name whose official name differs (a suffix, a route, a
# snapshot or a rename), longest first. A name equal to its official name (Clef, DeepSeek-V4.1-Flash) is left alone in
# running text: its route and snapshot are in the tables' tags.
_NAMES_SHOWN = ({label(s[k]) for s in _SETUPS for k in ("name", "model")} | set(_MODELS_SHOWN)
                | {label(r["setup"]) for r in _PLANNED} | {label(s) for s in _NACK_ONLY})
SPLIT = sorted((n for n in _NAMES_SHOWN if name_and_tag(n)[0] != n), key=len, reverse=True)
_SPLIT_IN_TEXT = re.compile("|".join(rf"(?<![\w-]){re.escape(n)}(?![\w-]|\.\d)" for n in SPLIT))


def split_spans(text: str):
    """(start, end, shown name) of every shown name in text that a page must split (SPLIT); a name whose official name
    begins with it ('Gemma 4 12B' in 'Gemma 4 12B Unified') is not one where the official name stands."""
    for m in _SPLIT_IN_TEXT.finditer(text):
        o = name_and_tag(m.group(0))[0]
        if len(o) > len(m.group(0)) and o.startswith(m.group(0)) and text.startswith(o, m.start()):
            continue
        yield m.start(), m.end(), m.group(0)


def split_names(text: str, dataset: str | None = None, plain: bool = False) -> str:
    """text (escaped HTML text, or an attribute's value with plain) with every SPLIT name as its official name and
    tag: the tag's markup, or plain 'name (tag)'."""
    out, at = [], 0
    for s, e, n in split_spans(text):
        out += [text[at:s], esc(name_text(n, dataset)) if plain else name_html(n, dataset)]
        at = e
    return "".join(out) + text[at:]


def aliases(name: str) -> list[str]:
    """Earlier names of a shown setup (empty when it was never renamed)."""
    return [INTERNAL[name]] if name in INTERNAL else []


def effort_aliases(name: str) -> list[str]:
    """A shown setup's earlier effort name (labels.json "renamed", 28 Oct 2026) under its model's shown name: the
    model renames (labels.json "models") are display names, not renames of a setup."""
    old = INTERNAL.get(name)
    if old not in _EFFORT:
        return []
    m = _MODEL.match(old)
    return [MODEL_NAMES[m.group(1)] + m.group(2) if m else old]


# Old model names inside text (prose, tables, notes): a page shows the model's display name instead. An old name that
# is part of its own new name ('Decider Flash v1.2' in 'Perplexity Decider Flash v1.2') is left alone, and so is one that
# is its model's official name again ('Mercury Decide', 'GPT-6 Luna').
_OLD = sorted((o for o in MODEL_NAMES if official(MODEL_NAMES[o]) != o), key=len, reverse=True)
_OLD_IN_TEXT = re.compile("|".join(rf"(?<![\w-]){re.escape(o)}(?![\w-])" for o in _OLD))
_INSIDE_NEW = [(o, n, n.find(o)) for o in _OLD for n in set(MODEL_NAMES.values()) if o in n]


def old_model_spans(text: str):
    """(start, end, old name) of every old model name in text that is not part of a shown name."""
    for m in _OLD_IN_TEXT.finditer(text):
        s, o = m.start(), m.group(0)
        if not any(oo == o and text[s - k:s - k + len(n)] == n for oo, n, k in _INSIDE_NEW if s >= k):
            yield s, m.end(), o


def shown_names(text: str) -> str:
    """text with every old model name (not part of a shown name) replaced by the model's display name."""
    out, at = [], 0
    for s, e, o in old_model_spans(text):
        out += [text[at:s], MODEL_NAMES[o]]
        at = e
    return "".join(out) + text[at:]


_RAW = ("script", "style", "pre", "code", "textarea")
# Elements whose text takes no markup: a name in them is 'name (tag)' as plain text.
_PLAIN = ("option", "title", "text", "tspan", "desc")
_ATTRS = re.compile(r'( (?:title|aria-label|data-note|data-tip|alt|content)=")([^"]*)"')


def shown_names_html(page: str, dataset: str | None = None) -> str:
    """An HTML page's text and its title, aria-label, data-note, data-tip, alt and content attributes with every old
    model name as its display name (shown_names), then every shown name a page must split (SPLIT) as the official name
    and its tag (split_names: the tag's markup in text, 'name (tag)' in an attribute or an element whose text takes no
    markup). Tags, URLs and the raw text of script, style, pre, code and textarea stay as they are. dataset: the page's
    setups' (their routes), None for a page of the leagues."""
    parts, raw, plain = re.split(r"(<[^>]*>)", page), 0, 0
    for i, p in enumerate(parts):
        if p.startswith("<"):
            t = re.match(r"</?\s*([a-zA-Z0-9]+)", p)
            tag = t.group(1).lower() if t else ""
            if tag in _RAW and not p.endswith("/>"):
                raw += -1 if p.startswith("</") else 1
            elif tag in _PLAIN and not p.endswith("/>"):
                plain += -1 if p.startswith("</") else 1
            if not p.startswith("</") and _ATTRS.search(p):
                parts[i] = _ATTRS.sub(lambda m: m.group(1) + split_names(shown_names(m.group(2)), dataset, True) + '"', p)
        elif not raw:
            parts[i] = split_names(shown_names(p), dataset, plain > 0)
    return "".join(parts)


def setup_slug(dataset: str, name: str) -> str:
    """URL slug of a setup: from its name before the relabel, so links and data ids keep working."""
    if dataset.startswith("league-"):
        return slug(INTERNAL.get(name, name))
    return slug(_RECORDED.get((dataset, name)) or INTERNAL.get(name, name))


def relabel(obj):
    """`obj` with every string equal to a renamed setup's or model's old name (as a value, a dict key or inside a tuple
    key) replaced by its shown name (label). Exact forms only; numbers and other strings are untouched; an "aliases"
    list keeps the old names. Two keys of one dict that show as one name fail."""
    if isinstance(obj, str):
        return label(obj)
    if isinstance(obj, dict):
        out = {relabel(k): v if k == "aliases" else relabel(v) for k, v in obj.items()}
        if len(out) != len(obj):
            raise ValueError(f"relabel: two keys show as one name among {sorted(map(str, obj))[:20]}")
        return out
    if isinstance(obj, list):
        return [relabel(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(relabel(x) for x in obj)
    if isinstance(obj, (set, frozenset)):
        return type(obj)(relabel(x) for x in obj)
    return obj


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def fmt(x, digits=1, signed=False) -> str:
    if x is None:
        return ""
    s = f"{x:+,.{digits}f}" if signed else f"{x:,.{digits}f}"
    return s.replace("-", "\u2212")


def pct(x, digits=1) -> str:
    return "" if x is None else f"{100 * x:.{digits}f}%"


def count(n) -> str:
    return f"{n:,}"


def status_badge(status: str) -> str:
    """The one status of a section or metric (B10), as a small labelled badge."""
    return f'<span class="status status-{slug(status.split(" (")[0].split(":")[0])}">{esc(status)}</span>'


def nm(text: str) -> str:
    """A status in place of a value (never a placeholder number)."""
    return f'<span class="nm">{esc(text)}</span>'
