#!/usr/bin/env python3
"""Freezes the v3 benchmark inputs: the sha256 of every position file, the prompt files, seeds.json
and the roster, written to freeze.json with the harness commit.

    python3 tools/v3/freeze.py [--out freeze.json] [--check]

--check recomputes every hash and exits with status 1 if any file changed or is missing.
Standard library only; run from the repo root.
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

GROUPS = {
    "positions": ["positions/*.jsonl", "positions/build-log.json"],
    # Prompt texts and the code that renders them (bg-v2.md serves bg-v2, bg-v2-notation and
    # bg-v2-history; nack-v2.md).
    "prompts": ["prompts/*.md", "prompts/*.txt", "src/players/prompt.rs"],
    "seeds": ["seeds.json"],
    # League configs: roster, providers, quantization, reasoning, prices, dice and order seeds,
    # prompt version, clock.
    "roster": ["leagues/*.json"],
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lines(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def collect():
    out = {}
    for group, patterns in GROUPS.items():
        files = {}
        for pattern in patterns:
            for path in sorted(glob.glob(pattern)):
                files[path] = {"sha256": sha256(path), "bytes": os.path.getsize(path)}
                if path.endswith(".jsonl"):
                    files[path]["rows"] = lines(path)
        out[group] = files
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="freeze.json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = collect()
    if a.check:
        with open(a.out) as f:
            frozen = json.load(f)
        bad = [(g, p) for g, fs in frozen["files"].items() for p, v in fs.items()
               if files.get(g, {}).get(p, {}).get("sha256") != v["sha256"]]
        for g, p in bad:
            print(f"changed or missing: {g} {p}")
        print("ok" if not bad else f"{len(bad)} files differ")
        sys.exit(1 if bad else 0)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    empty = [g for g, fs in files.items() if not fs]
    with open(a.out, "w") as f:
        json.dump({"harness_commit": commit, "files": files, "groups_without_files": empty,
                   "patterns": GROUPS}, f, indent=2)
        f.write("\n")
    n = sum(len(fs) for fs in files.values())
    print(f"{a.out}: {n} files hashed" + (f"; no files for {', '.join(empty)}" if empty else ""))


if __name__ == "__main__":
    main()
