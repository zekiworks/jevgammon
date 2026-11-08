# review2-extra (Zeki #2735): the saved outputs behind review2's claims

Nothing here was re-run. I only copied existing files and hashed or compared files already on disk.

## 1. nack_paired_verify --saved-only output

`nack_paired_verify-branch.txt` is the saved stdout and stderr of the run on the branch render. It was written at 18:36 UTC to `/tmp/fs/nv-branch.txt` and copied here unchanged; it has 113 lines.

```
cd /tmp/fs/src-branch && PATH=$HOME/.pyenv/shims:$PATH python3 tools/site/nack_paired_verify.py /tmp/fs/out-branch \
  positions/nack-paired/results-2026-10-28/results.json --saved-only > /tmp/fs/nv-branch.txt 2>&1
```

The verify script in `/tmp/fs/src-branch` was the branch's version from commit ef3ed0e, copied in before this run.

The file contains:
- the "saved-only" line;
- 111 `MISMATCH … private string 'decision-models'` lines;
- the summary line `nackgammon paired test: 30 setups; 111 mismatches`.

No other MISMATCH line is present. There is none for a table, cell, row order, data file, late file, label, note or chart. That is what "no Nackgammon mismatch" in review2 meant.

The comparison with main is **not saved**. Review2 said the 111 lines are 110 on main plus 1 on `learning/`. That comes from a run on the earlier render, results 04493cf3, at about 17:50 UTC. Its files (`review/nack-verify-{main,branch}.txt`) were deleted before packet 1 was committed, so that main/branch split is not backed by a saved output for this render. Only the branch output above is saved.

## 2. Republishing the 28 Oct file gives identical bytes

The command, run at 18:21 UTC in the worktree after the rebase onto 76b39de with the refactored `nack_paired_publish.py`:

```
~/.pyenv/shims/python3 tools/site/nack_paired_publish.py /dev/stdin /tmp/fs/nack-check.json \
  < positions/nack-paired/results-2026-10-28/results.json \
  && cmp /tmp/fs/nack-check.json tools/site/content/nack_paired_results.json && echo SAME-28
```

It printed `…: 30 setups; engine check present` and `SAME-28`; `cmp` was silent.

The sha256 values were taken now from the same files, which are still on disk:

| File | sha256 |
|---|---|
| `/tmp/fs/nack-check.json` (republished) | `0a80d8a44b445cc2c0b948805904898fd743028a9503a834fc39a2cfbdf8d7ee` |
| `tools/site/content/nack_paired_results.json` (pinned) | `0a80d8a44b445cc2c0b948805904898fd743028a9503a834fc39a2cfbdf8d7ee` |

Both files are 219,692 bytes.

## 3. The late file: 45,324 / 077d6e914617… on the Data page against 45,306 / 57b7e7ebd37e… pinned

| File | Bytes | sha256 |
|---|---:|---|
| `tools/site/content/nack_paired_late.json` (pinned) | 45,306 | `57b7e7ebd37eeb86860298111be840db4ddcbdc5d3ab9b1b48bfb3b358322601` |
| `/tmp/fs/out-branch/data/v3/nack-paired-late.json` (branch render) | 45,324 | `077d6e914617b3f03318988af0d918f64fa073bef4b6d58a37266a9984bcd989` |

**The difference is a build transformation, and no value differs.** `build.write_json` writes every data file as:

```
json.dumps(dict(version="v3", **S["nack_late"]), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
```

That writes the same values with sorted keys and one added field, `"version": "v3"`. The pinned content file keeps the publisher's insertion order and has no `version` field.

- **Values:** the site file minus `version` equals the content file as a JSON value (Python `==`). The only key that is new at any level is the top-level `version`.
- **Bytes:** serialising the content file exactly as `write_json` does reproduces the site file byte for byte (`late-file-equivalence.txt`: `True`).
- **Size:** the 18 extra bytes are `,\n "version": "v3"` (18 characters). Both files end in one newline.
- **Diff:** `late-file-sorted.diff` compares both files after `json.tool --sort-keys`. The only difference is that `"version": "v3"` line, plus the comma it adds to the line before it.
- **Same for the 28 Oct file:** it gets the same transformation. `nack_paired_verify` compares site and content files after removing `version`, as it already did for `nack-paired.json`.

No number, label or string differs.
