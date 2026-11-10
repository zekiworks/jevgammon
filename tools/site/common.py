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
# Setups not shown yet (content/held_setups.json, name: reason): a late entry still playing is held until its entry is
# complete, so no moving partial numbers are published; analysis.late_entries and cup.classify leave them out, so no
# page, data file, leaderboard row, bench score or model list carries them.
HELD = json.loads((CONTENT / "held_setups.json").read_text())["held"]
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
# is part of its own new name ('Mercury Decide' in 'Inception Mercury Decide') is left alone.
_OLD_IN_TEXT = re.compile("|".join(rf"(?<![\w-]){re.escape(o)}(?![\w-])"
                                   for o in sorted(MODEL_NAMES, key=len, reverse=True)))
_INSIDE_NEW = [(o, n, n.find(o)) for o in MODEL_NAMES for n in set(MODEL_NAMES.values()) if o in n]


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


def shown_names_html(page: str) -> str:
    """shown_names on an HTML page's text and its title attributes; tags, URLs and the raw text of script, style,
    pre, code and textarea stay as they are."""
    parts, raw = re.split(r"(<[^>]*>)", page), 0
    for i, p in enumerate(parts):
        if p.startswith("<"):
            t = re.match(r"</?\s*([a-zA-Z0-9]+)", p)
            if t and t.group(1).lower() in _RAW and not p.endswith("/>"):
                raw += -1 if p.startswith("</") else 1
            elif ' title="' in p or ' aria-label="' in p or ' data-note="' in p:
                parts[i] = re.sub(r'( (?:title|aria-label|data-note)=")([^"]*)"',
                                  lambda m: m.group(1) + shown_names(m.group(2)) + '"', p)
        elif not raw:
            parts[i] = shown_names(p)
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
