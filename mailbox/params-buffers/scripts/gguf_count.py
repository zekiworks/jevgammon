"""Logical parameter count of a GGUF file: the sum over its tensor infos of the product of each tensor's dimensions
(the logical shape, whatever the storage type, e.g. Q8_0 blocks and their scales are not counted as elements).
Reads the header only. Prints tensor count, type counts, the total and the file's sha256 (when --sha).

    python3 gguf_count.py FILE.gguf [--sha]"""
import hashlib
import struct
import sys
from collections import Counter

path = sys.argv[1]
f = open(path, "rb")
rd = lambda fmt: struct.unpack("<" + fmt, f.read(struct.calcsize("<" + fmt)))[0]  # noqa: E731


def string():
    return f.read(rd("Q")).decode("utf-8", "replace")


SIZES = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}


def value(t):
    if t == 8:
        return string()
    if t == 9:
        et, n = rd("I"), rd("Q")
        return [value(et) for _ in range(n)]
    return rd(SIZES[t])


assert f.read(4) == b"GGUF", "not a GGUF file"
version, n_tensors, n_kv = rd("I"), rd("Q"), rd("Q")
meta = {}
for _ in range(n_kv):
    k = string()
    v = value(rd("I"))
    meta[k] = v if not isinstance(v, list) or len(v) < 20 else f"[{len(v)} items]"
# Tensors that are buffers, not trained parameters (Zeki #3574; turkce #3592): RoPE frequency factors, and Gemma 4's
# per-layer scalar (GGUF blk.N.layer_output_scale = transformers' layer_scalar, an nn.Buffer in modeling_gemma4.py).
BUFFERS = {"rope_freqs", "layer_output_scale"}
total, types, prefixes = 0, Counter(), Counter()
for _ in range(n_tensors):
    name = string()
    dims = [rd("Q") for _ in range(rd("I"))]
    ttype = rd("I")
    rd("Q")  # offset
    n = 1
    for d in dims:
        n *= d
    total += n
    types[ttype] += 1
    prefixes[name.split(".")[2] if name.startswith("blk.") and name.split(".")[2] in BUFFERS else name.split(".")[0]] += n
print(f"file: {path}\nGGUF version {version}; tensors {n_tensors}; metadata keys {n_kv}")
print("general.architecture:", meta.get("general.architecture"), "| general.name:", meta.get("general.name"))
print("tensor types (ggml type id: count):", dict(types))
print("tensor elements by name prefix:", dict(prefixes))
buffers = {k: v for k, v in prefixes.items() if k in BUFFERS}
print(f"all tensor elements: {total:,}; non-parameter buffers {buffers}")
print(f"logical parameter total (buffers excluded): {total - sum(buffers.values()):,}")
if "--sha" in sys.argv:
    h = hashlib.sha256()
    with open(path, "rb") as g:
        for chunk in iter(lambda: g.read(1 << 24), b""):
            h.update(chunk)
    print("sha256:", h.hexdigest())
