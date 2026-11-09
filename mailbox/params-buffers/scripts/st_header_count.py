"""Logical parameter count of one safetensors file on Hugging Face from its header only: the sum of the products of
its tensors' shapes, per dtype; no weights downloaded.

Fails closed (Zeki #3574): every request must come back as HTTP 206 with a Content-Range for exactly the bytes asked
for; reads are bounded to those bytes; the declared header size must be at most MAX_HEADER. A server that ignores the
Range header is never read past the requested length.

    python3 st_header_count.py REPO REVISION FILE [FILE ...] [--only=SUBSTRING]   (--only: count tensors whose name
    contains SUBSTRING, e.g. '.visual.', and print the rest of the file separately)"""
import json
import re
import struct
import sys
import urllib.request
from math import prod

MAX_HEADER = 64 << 20  # 64 MiB; real safetensors headers are kilobytes to a few MiB
only = next((a.split("=", 1)[1] for a in sys.argv[3:] if a.startswith("--only=")), None)
repo, rev, files = sys.argv[1], sys.argv[2], [a for a in sys.argv[3:] if not a.startswith("--only=")]


def get(url: str, a: int, b: int) -> bytes:
    """Bytes a..b inclusive, only from a 206 response whose Content-Range is exactly 'bytes a-b/…'."""
    req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req) as r:
        if r.status != 206:
            raise SystemExit(f"{url}: HTTP {r.status}, not 206 (Range ignored?); nothing read")
        cr = r.headers.get("Content-Range", "")
        if not re.fullmatch(rf"bytes {a}-{b}/\d+", cr):
            raise SystemExit(f"{url}: Content-Range {cr!r} is not bytes {a}-{b}/…; nothing read")
        n = b - a + 1
        data = r.read(n)
        if len(data) != n:
            raise SystemExit(f"{url}: got {len(data)} bytes, expected {n}")
        return data


for fn in files:
    url = f"https://huggingface.co/{repo}/resolve/{rev}/{fn}"
    n = struct.unpack("<Q", get(url, 0, 7))[0]
    if not 0 < n <= MAX_HEADER:
        raise SystemExit(f"{url}: declared header size {n} outside 1..{MAX_HEADER}")
    head = json.loads(get(url, 8, 8 + n - 1))
    meta = head.pop("__metadata__", None)
    picked = [k for k in head if only is None or only in k]
    by = {}
    for name in picked:
        t = head[name]
        by[t["dtype"]] = by.get(t["dtype"], 0) + prod(t["shape"])
    rest = sum(prod(t["shape"]) for k, t in head.items() if k not in picked)
    print(f"{repo} @ {rev} {fn}{f' [names containing {only!r}]' if only else ''}: tensors {len(picked)}; logical "
          f"parameters {sum(by.values()):,} {by}" + (f"; other tensors in the file {rest:,}" if only else "")
          + f"; names {sorted(picked)[:6]}{' …' if len(picked) > 6 else ''}; metadata {meta}")
