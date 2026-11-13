# Small late entries' repeats (Run 2): GLiDE 2B and MiniCPM5-2B (off) — review package

Ümit #6410; plan `mailbox/small-backgammon-bench-2026-11-13.md` §9. **Prepared only.** Nothing was started: no model server, league unit, GPU job or repeat run. Nothing was written to the production v3.db; only read-only reads (`mode=ro`, and `jevgammon admit`'s immutable open). Checksums: `SHA256SUMS`.

## 1. Branches (pushed, not merged)

| Branch | Base | Head | What |
|---|---|---|---|
| `small-repeat-runner` | runner 0e66836 (`target/pinned-late`, Zeki-reviewed) | **6578a73** | src patches: the late-tiny8 decision clients, the late-smallchat-on reasoning keys, admission of openai-compatible clients |
| `small-repeat` | launcher 33fa52b (launcher-bind / pinned-pairs) | **7b39482** | repeat entries `glide-2b-r1` and `minicpm5-2b-off-r1`; server kind `pinned`; OPP_GPU/RES optional without locals; the original's concurrency; tests |
| `small-repeat-held` | origin/main 7cd7506 | **f669702** | `tools/site/content/held_setups.json`: holds 'GLiDE 2B [repeat 1]' and 'MiniCPM5-2B (off) [repeat 1]' (never shown as a setup). Same pattern as Gemini's 7708a51. |

**Diffs** (`diffs/`):
- `runner-small-repeat-runner-6578a73-vs-0e66836.diff`: src only, 5 files, +611 −23.
- `launcher-small-repeat-7b39482-vs-33fa52b.diff`: the full diff. `…no-manifest.diff` leaves out the 2,782 appended manifest lines.
- `site-small-repeat-held-f669702.diff`.
- The two src inputs as applied: `input-late-tiny8-small3-8ebad40-vs-18cc78d-src.patch` and `input-late-smallchat-on-a083fb4-vs-171698f-src.patch`.

## 2. Runner 6578a73 (vs 0e66836)

- **late-tiny8-small3 8ebad40's src** (contains late-tiny8 e4ce0e9..a72223d), applied with `git apply -3` over 0e66836. It adds these decision services: knowline, startlux, glide, glide-0.4b, onejev, gliclass, sieve, turion-jev, d1-local, strands and metask. `main.rs` gets a help line, and `players/mod.rs` gets the services' stub tests.
  - The one conflict was SERVICES in `decision.rs`, and it was purely additive. 0e66836's baselabs, nace, drex-max, drex-local and reax entries are kept beside the new ones.
  - The three new stub tests got 0e66836's fifth `DecisionClient::new` argument, `budget: None`.
- **late-smallchat 171698f's src is its merge base 18cc78d**, which 0e66836 already contains (`git diff 18cc78d 171698f -- src` is empty). The chat client MiniCPM5-2B (off) played with (letter readout, groups of at most 26, logprobs) differs in 0e66836 only by rustfmt and the `http::send_metered` hook. The hook is used only with a budget, and MiniCPM has none.
- **late-smallchat-on a083fb4's player keys `reasoning_prefill` and `reasoning_field`.** This was cheap and is byte-identity-safe: without the keys, the read-out message is the same JSON as before, and the replay below confirms it. 8ebad40's d1-local is included too, so the later repeats (LFM3 (on), d1-2B, MiniCPM (on)) need no other runner. They do still need their own entries and replays.
- **Admission roster: `openai-compatible` added** in `Player::for_admission`. Without it, `jevgammon admit` refuses MiniCPM5-2B (off)'s client, and check can never pass.
  - Its constructor sends no request and needs no login. The only key it can read comes from the variable the settings name (MiniCPM names none), and a budget ledger is opened read-only.
  - The subscription logins and the other chat routes (local, ollama, gemini …) stay refused.
  - `admit.rs`'s test now expects the openai-compatible player with a missing ledger to be refused as "does not exist", and the ledger is not created.
  - **Zeki: this widens what admission builds.**
- pinned_pairs, league-add `--pin`, admit and the admitted-settings record are unchanged.
- **cargo test**: 103 passed, 0 failed, run in the committed clean tree (`tests/cargo-test-6578a73.log`).
- **Binary**: `/home/cbasaran/code/jevgammon/target/small-repeat/release/jevgammon`
  - sha256 **79409d713a5992556d47dd06adf3a8d793fbea2eb039a178736b55dc1213615b**.
  - Built 2026-11-13T16:32Z from the clean detached tree `/home/cbasaran/code/jevgammon-small-repeat-runner` with `cargo build --release --locked` (rustc/cargo 1.97.1); see `tests/build-6578a73.log`.
  - The 18 build inputs outside src have RUNNER's recorded sha256.

## 3. Byte identity (`byte-identity/`)

**Method.** `replay.py` replays each original's 9 finished matches in a scratch league with all of the following:
- the original league's seed, option-order seed, bg-v2, 3 rounds, 300 turns and mirror_concurrent;
- the original's players.settings, with only base_url changed to a stub;
- the 6 API opponents' settings, also with only base_url changed;
- the programs.

Every requesting player gets its own port of `stub.py`. The stub answers each request with the stored response of the byte-identical stored request (v3.db `exchanges`, read-only via `export.py`) and answers 400 to any other body. A decision service's warm-up gets `{}`.

After the league ends, each player's stored `exchanges.request` texts are matched as a multiset (sha256) against the bodies its port received. The replayed matches' turns (round, leg, turn, side, dice, position, option order, chosen index, move) are compared with the original turns.

There are two modes:
- **repeat**: the entrant is named '<original> [repeat 1]' and the config carries `pinned_pairs`, exactly as the repeat's league config.
- **original**: the original name and no pins, for the original runners, which derive seeds from names.

**Results:**

| Entrant | Binary | Entrant requests identical | Opponents' requests identical | Received but not stored | Pairs finished | Turns identical | Seed, seat and score as original |
|---|---|---|---|---|---|---|---|
| GLiDE 2B (#1191–#1199) | **6578a73** (repeat mode, pins) | **820 / 820** | 558 / 558 | 0 | 9/9 | 9/9 | 9/9 |
| GLiDE 2B | e4ce0e9 rebuilt (original mode) | 820 / 820 | 558 / 558 | 0 | 9/9 | 9/9 | 9/9 |
| MiniCPM5-2B (off) (#1171, #1173–#1180) | **6578a73** (repeat mode, pins) | **1,300 / 1,300** | 676 / 676 | 0 | 9/9 | 9/9 | 9/9 |
| MiniCPM5-2B (off) | 171698f rebuilt (original mode) | 1,300 / 1,300 | 676 / 676 | 0 | 9/9 | 9/9 | 9/9 |

Coverage and binaries:
- **All stored exchanges were compared, not a sample.** GLiDE 2B has 820 exchanges over 818 decision turns. MiniCPM5-2B (off) has 1,300 exchanges over 976 turns: group splits of at most 26, then a final.
- Every entrant request went to the original path: `/v1/systemone` for GLiDE and `/v1/chat/completions` for MiniCPM.
- The original binaries were rebuilt from clean detached worktrees of e4ce0e9 and 171698f:
  - e4ce0e9 → `target/small-repeat/orig-e4ce0e9`, sha256 0ae2efd4…
  - 171698f → `target/small-repeat/orig-171698f`, sha256 a7f6e420…
- `target/tiny8` and `target/smallchat` were not touched. Their current sha256 (fccf3dec…, 7a0ee89a…) differ from these rebuilds. [INFERENCE] They were rebuilt at later commits of their branches.

**Negative controls** (`byte-identity/controls.md`): MiniCPM with `top_logprobs` 19 gives 0 of 1,300 identical (all 13 requests sent were refused). GLiDE 2B run as provider `glide-0.4b` (groups of at most 74 options) matches its first 46 requests, then is refused at its first split group (68 options of the first list longer than 74). The stub does detect a difference.

## 4. Launcher 7b39482 (vs 33fa52b)

**Repeat entries**
- Names: `glide-2b-r1` → 'GLiDE 2B [repeat 1]' (display 'GLiDE 2B', original league 41, stage late-entry), and `minicpm5-2b-off-r1` → 'MiniCPM5-2B (off) [repeat 1]' (original league 39).
- The manifest entries were appended by `repeats.py manifest glide-2b-r1 minicpm5-2b-off-r1` (v3.db read-only). The six existing entries and the top level are byte-identical to 33fa52b. The league configs come from `configs ID…`.
- Copies are in `entries/`: manifest entries, league configs, and the production admitted-settings records.

**Pairs.** Only the pairs the original played are pinned and played: 9 each, with the original match seed (u64) and seating.

| Repeat | Matches | Not required (`coverage_required`) |
|---|---|---|
| GLiDE 2B | #1191–#1199 | Mercury Decide (#1200, aborted at warm-up), GPT-6 Luna (never scheduled), the 8 locals (0/8 played) |
| MiniCPM5-2B (off) | #1171, #1173–#1180 | Mercury Decide (#1172, aborted at warm-up), GPT-6 Luna, the 8 locals |

Each has 9 required, 9 played, 9 pinned and 9 matched fixtures.

**Settings**
- `settings_change {}`. The repeat changes only `name` and `note`.
- With `settings_as_original`, `max_matches` is not forced to 1, and check refuses any change to it.
- GLiDE 2B keeps max_matches 1, parallel 1 (one match at a time). MiniCPM5-2B (off) keeps 16, 16.
- How MiniCPM's concurrency was set in its original:
  - late-smallchat 95c5f96 "up to 16 matches and 16 requests at once per setup" (player.json max_matches/parallel 16; `start.sh` guard text "up to 16 matches at once").
  - Its 9 matches all started at 13:47:39Z.
- `rules.mirror_concurrent` is true, as in both originals.

**Runner.** `RUNNER_SMALL` (6578a73, binary sha256 above, tree `/home/cbasaran/code/jevgammon-small-repeat-runner`) is bound by check exactly as RUNNER is: commit, clean src and inputs, input sha256, binary sha256. `attempts()` records each repeat's own runner. `differences` lists the runner change and the replay counts.

**Server kind `pinned`** (repeats.py, run.sh)
- No start or stop, no GPU of ours, ENTRANT_MIB 0.
- **Pin files.** The late entry's own pins.sh is copied byte for byte into `tools/v3/repeats/pins/ID/` and bound by sha256:
  - GLiDE 2B: late-tiny8 a72223d `models/glide-2b/pins.sh` (blob ebd8047, the same at e4ce0e9).
  - MiniCPM5-2B (off): late-smallchat 171698f `pins.sh` plus `models.json` (blobs 5081854, 8ce1456).
- **How it runs.** `repeats.py pins ID` sources the copy with the variables its start.sh sets, then runs `healthy` and then `pinned`:
  - GLiDE 2B: URL http://192.168.1.131:19330, PORT 19330, SSH_HOST spark2.
  - MiniCPM5-2B (off): KEY minicpm5-2b-off, T = the copies' folder, URL http://127.0.0.1:18614/v1, PORT 18614, SERVED minicpm5-2b.
- **Where it runs:**
  - inside `check`, before admission. A failure refuses: exit 1, no admission, no backup, no trigger, no state;
  - in run.sh again before the smoke and the first match;
  - at every guard tick, via `healthy()`. 3 failures in a row stop the run.
- **Smoke.** `jevgammon ask` (runner 6578a73) on `positions/smoke.jsonl`, using `tools/v3/repeats/smoke/ID.json` (the original's players.settings unchanged). It needs 50/50 answers with probabilities, like glide-v1.2-r1's smoke.

**OPP_GPU / RES.** run.sh asks for them only when the plan has a local opponent (`repeats.py env` LOCALS). That is 0 for both repeats here and still 8 for e.g. Mammoth-1.

**Concurrency.** `repeats.py env` CONCURRENT is 1 when the repeat's max_matches is over 1. In that case run.sh league-adds every paid opponent (`join()`, the former inline league-add) before the per-opponent waits, so the league plays all 9 pairs at once, as MiniCPM's original did. For CONCURRENT 0, the behaviour is unchanged.

## 5. Tests (scratch databases only)

`tests/test_launcher-7b39482.log`: **97 ok, 0 FAIL, ALL PASSED**, exit 0. This is the whole suite: the existing cases plus the new ones below.

The scratch database gets the runner's own schema plus fixture rows as before, plus the originals' leagues #39/#41, their league_players, and matches #1171–#1180/#1191–#1200 copied read-only from v3.db. curl, ssh and docker stand-ins answer pins.sh.

New cases:

| Case | Result |
|---|---|
| `plan-glide-2b-r1`, `plan-minicpm5-2b-off-r1` | plan = exactly 9 pairs. The config pins equal the original matches' seed (u64) and seating, read from the copied rows. No Mercury Decide or locals pinned. |
| `concurrency-*`, `concurrency` | Config max_matches/parallel = the original's (1/1, 16/16). env KIND=pinned, ENTRANT_MIB=0, LOCALS=0. CONCURRENT is 0 for GLiDE and 1 for MiniCPM (0 for Mammoth-1). |
| `minicpm-one-at-a-time` | max_matches 1 refused before any write: "repeat settings change max_matches beyond the listed changes". |
| `pinned-ok-*` | Healthy and pinned: check exit 3 (trigger only), run.sh --prepare-only prepares (backup verified, trigger), then check exit 0 with all 10 clients admitted by 6578a73 (MiniCPM's openai-compatible client included). **The originals' rows have the same sha256 before and after.** |
| `wrong-pin-*` | Server answers but is on another port (spark2 ps) or another revision (container args): refused, no write, **no admission**, originals' rows unchanged. |
| `unhealthy-*` | No /health or /v1/models: refused before any write and before admission. |
| `pins-edited-*` | An edited pins.sh copy is refused by its sha256. |
| `opp-gpu-optional` | GLiDE 2B run.sh (not --prepare-only) with no OPP_GPU/RES: neither is asked for. It goes on to the check, which is refused here by a wrong pin, and nothing is written. |
| `opp-gpu-required`, `-res` | Mammoth-1 (LOCALS=8) without OPP_GPU, then without RES: stops before the check, nothing written. |
| `not-held-glide-2b-r1`, `not-held-minicpm5-2b-off-r1` | Until main holds the names, check refuses on that alone (with the trigger). |

`tests/cargo-test-6578a73.log`: 103 passed.

## 6. Read-only checks on production (2026-11-13 ~16:48Z)

- **`tests/admission-production.log`**: `jevgammon admit` (6578a73) on production v3.db, opened read-only and immutable, sends no request. All 10 clients of each league config were built. The admitted-settings records are `entries/admitted-*.json`.
- **`tests/check-production.log`** (`repeats.py check`): each repeat refuses with exit 1 on three things only, nothing written:
  - not held in main;
  - the pinned server not healthy (both servers are down now);
  - the trigger missing.
- **`tests/pins-now.log`** (`repeats.py pins`): GLiDE 2B at 192.168.1.131:19330 gives connection refused. MiniCPM's 127.0.0.1:18614 does not answer /v1/models.

## 7. Start commands (not run)

Before starting, in this order:
1. Merge `small-repeat-held` f669702 into main, so check finds the names.
2. logic brings up GLiDE 2B on spark2 :19330 (handoff) and/or the MiniCPM5-2B vLLM container on bariton :18614.
3. `repeats.py pins ID` passes.

Then:

```bash
# Optional dry preparation (check; backup + trigger only when that is the one failure; nothing plays):
/home/cbasaran/code/jevgammon-small-repeat/tools/v3/repeats/run.sh glide-2b-r1 --prepare-only
/home/cbasaran/code/jevgammon-small-repeat/tools/v3/repeats/run.sh minicpm5-2b-off-r1 --prepare-only
# The runs (no GPU, OPP_GPU or RES: no card of ours, no local opponent):
systemd-run --user --unit=repeat-glide-2b-r1 --working-directory=/home/cbasaran/code/jevgammon /home/cbasaran/code/jevgammon-small-repeat/tools/v3/repeats/run.sh glide-2b-r1
systemd-run --user --unit=repeat-minicpm5-2b-off-r1 --working-directory=/home/cbasaran/code/jevgammon /home/cbasaran/code/jevgammon-small-repeat/tools/v3/repeats/run.sh minicpm5-2b-off-r1
```

**Expected cost** (manifest `cost_basis`: the paid opponents' cost in the original matches): $0.088 (GLiDE 2B) and $0.1073 (MiniCPM5-2B (off)). The cap is $5 each, and the OpenRouter floor is $40.

**Preparation backup.** The first run.sh of each writes the usual VACUUM INTO + zstd backup of v3.db before the trigger, about 5.8 GB each. Two repeats mean two backups unless they are prepared one after the other.

## 8. Open items for Zeki

1. **Admission roster widened to `openai-compatible`** (runner, §2). Please review `Player::for_admission` and the admit test change.
2. **The `pinned` guard checks `pinned` every minute**, where the originals checked it once at start. For GLiDE 2B that is an ssh to spark2 each minute, and an ssh failure counts as a failed check (3 in a row stop the run).
3. **MiniCPM's pins.sh** (the original's, 171698f) pins checkpoint, revision, dtype, context and port, **not the vLLM image** (v0.30.0). a083fb4's PIN_IMAGE applies only where models.json names an image, and MiniCPM has none. Left as the original had it; adding an image pin would be a change from the original.
4. **The manifest is the shared `manifest-2026-11-11.json`**, as Gemini's entry was. Once `small-repeat` is merged, the Experiments page (Repeat checks) lists the two as queued. Merging the launcher branch to main is not done here.
5. **Concurrency pre-pass (`join()` before the loop) for CONCURRENT repeats.** Only the prepare path and env are tested, not a live league. [INFERENCE] With max_matches 16, the league runner then plays the programs and the 6 paid pairs at once, as in league #39.
6. The ask smoke has not been exercised against a live server; both servers are down.
7. Later repeats (LFM3-1.7B (on), d1-2B, MiniCPM5-2B (on)): the runner already carries their clients. Each needs its own entry, pins and replay once its original has run.
