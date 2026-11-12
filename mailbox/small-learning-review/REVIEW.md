# Small-model learning: bounded review package (Zeki #5697, #5699)

**Superseded in part by `DELTA-2026-11-12b.md` (Zeki #5705): merge targets are now improve-small-2 d2acecd and improve-decision-small 0333578, merged with `merge/merge_coupled.sh` after the site branch `site-improve-amendment`; v3_players.py rollback works from an insert manifest.**

Nothing in production is written by this package. The two branches are pushed and **not merged**. Checksums: `SHA256SUMS`.

## 1. What to review

| Branch | Base | Asked commit | Head now | What the head adds |
|---|---|---|---|---|
| `improve-small` (chat) | `improve` a76fdc9 | 1d3f9bc | **2c72e14** | `IMPROVE_EXPORT=0`: summary() writes nothing (for the unmerged worktree run, §6); run_local_start.sh passes it through |
| `improve-decision-small` | `improve-decision` d9c3cbd | 227ccc7 | **ec21352** | fence pin re-pointed to 2c72e14's improve.py (22ab77b); KnowLine server pin (§4) |

- **Diffs:** `diffs/improve-small-{1d3f9bc,2c72e14}-vs-a76fdc9.diff` and `diffs/improve-decision-small-{227ccc7,ec21352}-vs-d9c3cbd.diff`.
- **Full chat improve.py** (the file the decision fence hashes, `/home/cbasaran/code/jevgammon-improve/workspace/improve/improve.py`):
  - `improve.py/improve.py@a76fdc9`: sha256 90fe6b0ead90ff4d3d32ec80e5932a8c113456b05ee76e6bb9c5e39a56df9875 (today's file and today's pin).
  - `improve.py/improve.py@1d3f9bc`: sha256 20eb62c31dbcff958559dcb388432d5dce531eae3e33ae3ef0764437d8c20437.
  - `improve.py/improve.py@2c72e14`: sha256 8c4d7033c9805317c1ea794b8d6c29cd02f3ac5a989e93db18341acf719a865f.
- **Fence pin** (`decision.py` `CHAT_IMPROVE_SHA256`):
  - Before: 90fe6b0e…9875 (improve.py @ 1a27793, Zeki #3798).
  - After at 227ccc7: 20eb62c3…0437.
  - After at ec21352: **8c4d7033…865f**, diff sha256 2b0eb1b2079f85c778f5a8dbd3ed21169a1f05d4d1e07c424142d9b4773ad1ab.
  - `BILLED_CHAT` and the run_queue.sh pin are unchanged. The 9 new rows are local and unbilled, so the fence's worker scan ignores them.
- **Tests, retained `-v` outputs** (run from detached worktrees of each commit):

| Output file | Result |
|---|---|
| `tests/test_improve-1d3f9bc.txt` | 35 OK |
| `tests/test_improve-2c72e14.txt` | 36 OK |
| `tests/test_decision-227ccc7.txt` | 49 OK |
| `tests/test_decision-ec21352.txt` | 51 OK |

## 2. Coupled merge and rollback (keeps the GPU 2 arms running)

**Facts the order rests on:**
- The decision lane hashes the chat improve.py above when it admits each billed step (the notes arms' writer). A mismatch makes that arm **pause** (exit 3; run_decision_local.sh retries after 300 s). Nothing is lost, but it must not be left mismatched.
- Running Python processes keep the code they loaded. New processes use the merged files: after-game hooks, the next arm, the exporter.
- `git merge --ff-only` and `git reset --hard` replace files with new inodes, so running bash scripts keep reading their old copy.
- The running improve-decision-local unit keeps its old SETUPS list. Decider Flash runs only through its own unit (plan §4).
- The merged diffs touch no code path of the running arms. Run identities (RUN_DEFINING) of existing rows are unchanged; only new rows were added.

**When:** right after the running GPU 2 arm logs a `step_start`. Read `~/code/jevgammon/workspace/improve/runs/decision/<arm>/log.jsonl`: the last line should be a step_start under a minute old. Its next fence check is then a full step away.

**Merge, two commands back to back:**

```bash
git -C ~/code/jevgammon-improve fetch -q && git -C ~/code/jevgammon-improve-decision fetch -q
git -C ~/code/jevgammon-improve rev-parse --short HEAD            # a76fdc9 expected
git -C ~/code/jevgammon-improve-decision rev-parse --short HEAD   # d9c3cbd expected
git -C ~/code/jevgammon-improve merge --ff-only origin/improve-small && \
git -C ~/code/jevgammon-improve-decision merge --ff-only origin/improve-decision-small
python3 -c "import hashlib; print(hashlib.sha256(open('/home/cbasaran/code/jevgammon-improve/workspace/improve/improve.py','rb').read()).hexdigest())"   # 8c4d7033…865f
cd ~/code/jevgammon-improve-decision && python3 workspace/improve/decision.py arm-state --arm decision/<running arm>   # unchanged
git -C ~/code/jevgammon-improve push -q origin improve && git -C ~/code/jevgammon-improve-decision push -q origin improve-decision
```

**Expected after merge:**
- The exporter (`improve-export.*`, run from ~/code/jevgammon-improve) writes 24 rows plus `amendments`. Gemma 4 E4B (on) appears with the steps already done.
- **Transient:** the chat runs still on old code (Qwen3.8-27B S5, the Grok lane) write a 15-row improve.json at each of their step ends. The exporter rewrites it within a minute, until those runs end.
- Main checks that the site's page readers accept the `amendments` key before the push.

**Rollback** (same timing rule; only for these two ff merges):

```bash
git -C ~/code/jevgammon-improve-decision reset --hard d9c3cbd && git -C ~/code/jevgammon-improve reset --hard a76fdc9
```

- After a push, restore the remote branches with the same commits.
- The E4B run (§6) is not affected either way: it runs from its own worktree.

## 3. Roster amendment records (no hashed text edited)

- **Chat:** MODELS rows and `AMENDMENTS` (exported as `amendments`) for 9 models.
- **Decision:** `decision_cohort.json` gets 18 rows and an `amendments` entry citing Ümit native 1570509348072063026 and 1570507658425933987. It is exported as `amendments` on the decision page file.
- The plan and addendum files and their sha256 bindings are unchanged.

## 4. KnowLine identity fix (ec21352)

Every KnowLine server answers `model: "m"`, so the reply id alone cannot tell 0.8B, 2B and 4B apart.

- **What the rows carry:** each KnowLine cohort row now also has `server_pin`:
  - `pins/knowline-<size>.sh`: the league entries' own `healthy()` and `pinned()` checks, copied verbatim (0.8B, 2B from late-tiny8 `models/*/pins.sh`; 4B from late-knowline4b `start.sh`) and bound by sha256;
  - the endpoint `url` (spark2 :19450 / :19490 / :19400);
  - the ssh host `spark2`.
- **The check:** `server_pin_check` runs before every step, ahead of any money gate.
  - `healthy()`: `/health` answers exactly as the pinned server.
  - `pinned()`: over read-only ssh, `ps -eo args` shows the pinned snapshot's `knowline_server.py --model <snapshot@revision>` on that port, plus the SGLang process on the same snapshot with the pinned flags.
  - Unhealthy → pause. Not the pinned process → stop.
  - The record goes into `step_start`.
- **Limit:** the check runs per step, not per request. A server swapped in the middle of a step is not caught until the next step.

## 5. Path (b): frozen chat settings as v3.db players rows without play (Zeki #5699; not written to production)

Files are in `v3-players/`.

- **`rows.json`:** the settings of 4 rows, each identical (parsed JSON) to its prepared late-entry `player.json` at late-smallchat 171698f: MiniCPM5-2B (on), LFM2.5-2.6B (on), LFM2.5-8B-A1B (on), LFM3-1.7B (on). Source paths and file sha256 are recorded per row.
- **The other 4 cannot be built "identical to the prepared player.json"** because none exists: Gemma 4 E2B (on), Gemma 4 12B (on), Erk-14B (on), Qwen3-14B (on). They are listed in `not_yet_prepared` with logic's pins. Preparing their late entries (models.json row, pins.sh, test.sh) comes first; nothing is invented.
- **`v3_players.py check|insert|rollback --db DB`:**
  - `insert` is idempotent. It refuses, writing nothing, if a name exists with other settings. It fills the columns the runner fills (settings as compact JSON in file order, as the runner stores it).
  - `rollback` deletes exactly these ids, only if no `matches` or `league_players` row references them.
  - No turns, replies, matches or league rows are written. No ranking baseline: these rows rank as "no baseline".
- **`test_v3_players.py`:** in-memory scratch DB with v3.db's own schema, read-only from production; 4 tests OK (`test_v3_players-output.txt`). It shows:
  - insert is exact and idempotent;
  - a name conflict is refused with nothing written;
  - on a copy of today's players rows, insert only adds (no existing row changes);
  - rollback refuses while a row is referenced, then deletes exactly these rows.
- **Production run, once approved (not done here):** take the backup first, as the late entries do (VACUUM INTO + zstd -t), then `python3 v3_players.py check --db ~/code/jevgammon/v3.db`, then `insert`.

## 6. Running now from the unmerged branch

- **What:** Gemma 4 E4B (on) learning, started ~19:12Z on GPU 0 (GPU-1115ade0-3068-1856-5889-5855079d97f7).
- **Where:** from the worktree `~/code/jevgammon-improve-small` at 2c72e14, with `IMPROVE_EXPORT=0`; units `improve-local-small` and `improve-xid-watch-small`.
- **Progress:** fit check passed (60.5 sequences at 69,632 tokens), E1 started. State is in `~/code/jevgammon/workspace/improve/runs/gemma-4-e4b-on/` and the run DB in `smoke/improve/`.
- **Not touched by this package:** the worktree and the run. It is $0 (local, self-written notes).

## 7. Cash

- **Enforcement is not written and cash stays off.** The proposed batch-ceiling check (per-entry CAP from the environment, booked spend + next cap ≤ ceiling before each start) is a design only.
- Implementing it must not block no-cash work. The no-cash arms (Arm W, chat self-notes) have no cash path to wait on.
- **Batch under path (b):**
  - Arm N writer: 18 × $0.03 = $0.54 expected, cap 18 × $0.045 = $0.81.
  - The 5 decision first stages (real prerequisites: league replies and stored requests): 5 × ~$0.09 = $0.45 expected, cap 5 × $0.50 = $2.50.
  - **Expected $0.99; item caps $3.31; ceiling $3.50.**
- **Separate:** Drex Max 1.1 worst needs the Nace subcap raised by +$0.52.
