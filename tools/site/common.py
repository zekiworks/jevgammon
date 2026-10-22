"""Shared helpers for the backgammon site build: slugs, formatting, thresholds."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = Path(__file__).resolve().parent
CONTENT = SITE / "content"

THRESHOLDS = json.loads((CONTENT / "thresholds.json").read_text())

# Status words (brief B10).
PUBLISHED, PROVISIONAL, EARLIER, PENDING, NOT_MEASURED, NA = (
    "Published", "Provisional", "Earlier version", "Analysis pending", "Not measured", "N/A")
TOO_FEW = "Too few decisions"
PROVISIONAL_NOTE = "Provisional: league still running"
EARLIER_NOTE = ("Earlier version: plays were listed in the runner's order, which tends to put the best play early.")

# B7 publishing rule: no internal hostnames, IP addresses, ports, server paths, keys, tokens or request headers in any
# published file (pages, JSON downloads, decision files); the pre-deploy check scans every file for these.
BANNED = re.compile(r"192\.168\.|127\.0\.0|\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d|localhost|"
                    r"https?://[\w.-]+:\d{2,5}|/home/|/root/|/mnt/|bariton|spark-|\bsk-[\w-]{8}|base_url|"
                    r"api[_-]key|Bearer [\w.-]{8}|[Aa]uthorization:|x-api-key|decision-models")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


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
