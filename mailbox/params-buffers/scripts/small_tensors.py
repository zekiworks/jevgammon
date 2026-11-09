"""List the small and buffer-like tensors of a Hugging Face safetensors checkpoint from its shard headers only (bounded,
fail-closed range reads as st_header_count.py), grouped by name pattern (layer numbers replaced by N). Reads only.

    python3 small_tensors.py REPO REVISION [SUBDIR/] [--max=NUMEL]"""
import json
import re
import struct
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from math import prod

MAX_HEADER = 64 << 20
args = [a for a in sys.argv[1:] if not a.startswith("--")]
repo, rev = args[0], args[1]
sub = args[2] if len(args) > 2 else ""
mx = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--max=")), "10000"))


def get(url, a, b):
    req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req) as r:
        if r.status != 206 or not re.fullmatch(rf"bytes {a}-{b}/\d+", r.headers.get("Content-Range", "")):
            raise SystemExit(f"{url}: not an exact 206 range response; nothing read")
        data = r.read(b - a + 1)
        if len(data) != b - a + 1:
            raise SystemExit(f"{url}: short read")
        return data


base = f"https://huggingface.co/{repo}/resolve/{rev}/{sub}"
try:
    with urllib.request.urlopen(base + "model.safetensors.index.json") as r:
        shards = sorted(set(json.loads(r.read(16 << 20))["weight_map"].values()))
except urllib.error.HTTPError as e:  # a single-file checkpoint
    if e.code != 404:
        raise
    shards = ["model.safetensors"]
total, groups = 0, defaultdict(lambda: [0, 0, None])
for s in shards:
    n = struct.unpack("<Q", get(base + s, 0, 7))[0]
    if not 0 < n <= MAX_HEADER:
        raise SystemExit(f"{s}: header size {n}")
    h = json.loads(get(base + s, 8, 8 + n - 1))
    h.pop("__metadata__", None)
    for k, t in h.items():
        e = prod(t["shape"])
        total += e
        if e <= mx:
            g = groups[re.sub(r"\.\d+\.", ".N.", k)]
            g[0] += 1
            g[1] += e
            g[2] = (t["shape"], t["dtype"])
print(f"{repo} @ {rev} {sub or ''}: {len(shards)} shards, all tensor elements {total:,}")
for k, (c, e, st) in sorted(groups.items(), key=lambda x: -x[1][1]):
    print(f"  {k}: {c} tensors, {e:,} elements, shape/dtype {st}")
