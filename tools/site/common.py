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


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Setup display names (content/labels.json, 28 Oct 2026): setups are named by the reasoning effort they sent. The
# databases keep the old names; the site computes with them and shows the new ones.
LABELS = json.loads((CONTENT / "labels.json").read_text())
RENAMED = {old: v["name"] for old, v in LABELS["renamed"].items()}
INTERNAL = {new: old for old, new in RENAMED.items()}
# What a shown name does not tell (on the setup's model page), by shown name.
NAME_NOTES = LABELS["notes"]
# What the Reasoning tab says about how a model's two settings differ, by model (where its names don't tell).
REASONING_NOTES = LABELS["reasoning_notes"]


def label(name: str) -> str:
    """The name a setup is shown under."""
    return RENAMED.get(name, name)


def aliases(name: str) -> list[str]:
    """Earlier names of a shown setup (empty when it was never renamed)."""
    return [INTERNAL[name]] if name in INTERNAL else []


def setup_slug(dataset: str, name: str) -> str:
    """URL slug of a league setup: from its name before the relabel, so links keep working."""
    return slug(INTERNAL.get(name, name) if dataset.startswith("league-") else name)


def relabel(obj):
    """`obj` with every string equal to a renamed setup's old name (as a value, a dict key or inside a tuple key)
    replaced by its shown name. Exact matches only; numbers and other strings are untouched; an "aliases" list keeps
    the old names."""
    if isinstance(obj, str):
        return RENAMED.get(obj, obj)
    if isinstance(obj, dict):
        return {relabel(k): v if k == "aliases" else relabel(v) for k, v in obj.items()}
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
