# Did they improve? Runner binary provenance: Qwen3.8 Flash (off), OpenRouter lane

Written 2026-11-08 by the experiment's agent. This is a disclosure of a gap: the OpenRouter lane (systemd unit `improve-openrouter`, started 16:10:46 UTC) ran the unpinned path `/home/cbasaran/code/jevgammon-improve/target/release/jevgammon`. I rebuilt that path twice while Qwen3.8 Flash was running, to prepare the other lanes. Each `jevgammon` process keeps the binary it was started with. A process started after a rebuild ran the new one.

## The three builds at that path

| Build | Written at (UTC) | Built from | sha256 | Copy kept |
|---|---|---|---|---|
| B0 | about 16:09–16:10 (exact mtime lost: overwritten) | from my session record: `git status` showed no tracked change, then `cargo build --release` at 88e5da0 (= src of 0c9270c; 88e5da0 only adds run_queue.sh). Not attested by a kept binary | **unknown** | no |
| B1 | 16:24:05.8 (seen as the file's mtime at the time) | **INFERRED**: an uncommitted working tree that I believe equals the non-test src of 1270c04, before its tests were added. The basis is the order of my edits in the session; no commit or build record ties B1 to a source | `2360ace5669d12055e3610c552ee3cd94c10df7e59e6ab30149a23a0d8cbaa9a` | yes: `target/improve-bin/jevgammon-B1-recovered-from-pid3875115` (copied from `/proc/3875115/exe` of the running S1 match) |
| B2 | 16:26:50.165 | built by `cargo build --release` right after committing 1270c04 (session record) | `19357c4e46af78eb07bc8125d7bf7f99e9b463464951caea41d5f4f18dd7fa11` | yes: identical to `target/improve-bin/jevgammon-1270c04` (the local and subscription lanes' pinned copy) |

The path has not changed since 16:26:50: its mtime is 16:26:50.165 and its sha256 equals B2's, checked at 16:36. Later builds went to separate target directories (`target/codex`). I will not rebuild `target/release` again while the lane uses it.

## Which build ran each Qwen3.8 Flash step

Rule: a process ran the build present at the path when it started.

| Step | Processes | Started (UTC) | Build | How known |
|---|---|---|---|---|
| setup | `jevgammon rank --dry-run` (schema only, no request) | 16:10:46 | B0 | before 16:24:05 |
| E1 (200 answers, empty context) | one `jevgammon ask` process, one round only: `test-E1.log` has a single "round 1" header; all 200 answered by 16:26:08 | 16:10:46 | **B0** | started before 16:24:05 and ran as one process to the end. B0's hash cannot be given: no copy was kept and the path was overwritten |
| S1 games (10 games) | the match process, pid 3875115 | 16:26:08 | **B1** | `ps` start time 16:26:08 lies between 16:24:05 and 16:26:50. `/proc/3875115/exe` → `target/release/jevgammon (deleted)`, sha256 2360ace5…, copied |
| S1 lesson calls (`jevgammon lesson`, one per game) | started from the after-game hook | game 1's at 16:28:55, later ones after it | **B2** | started after 16:26:50, and the path has held B2 since |
| S1 T10 (asked in the hook after game 10; any re-ask) | `jevgammon ask` | after game 10 | **expected B2** | it starts after 16:26:50; confirmed only when its receipt is appended below |
| S2 to S5, E2, E3 | match, lesson and ask processes | after 16:26:50 | **expected B2** | the path is expected to hold B2 for the rest of Qwen's run (nothing is to rebuild it); each step's receipt is appended below as it happens |

Observed: the S1 games (B1, hash read from the live process) and S1's lesson calls (B2: they started after 16:26:50, and the path held B2 when checked at 16:36).
Not exact: E1's binary (hash unknown; source from my session record only), and B1's source (inferred).
Expected, not yet observed: the later steps (see the receipts below).

## Source differences, 0c9270c → 1270c04, limited to what Qwen3.8 Flash sends and receives

`git diff 0c9270c 1270c04 -- src` touches src/http.rs, src/players/llm.rs, src/players/mod.rs and src/players/decision.rs (133+, 36−). The non-test parts:

1. **http.rs:** `send` and `send_metered` take a `Guard { stop, quota_fatal }` in place of the stop latch alone. `quota_fatal` makes a 429 final at once. Qwen's player config does not set `quota_pause`, so `quota_fatal` is false and 429 handling is the league's, as in B0. The stop latch is checked exactly as in B0.
2. **llm.rs `ExpectRoute`:** `provider` became optional and the model/provider fields are read by JSON pointer, defaulting to `/model` and `/provider`. Qwen's config sets `models` and `provider: "Alibaba"` with no pointers, so the same two fields are compared against the same values. The new pointer fields (`model_pointer`, `provider_pointer`) default to off. (`allow_dated` is not in this diff: it came in the later Codex commit 6e5a15e, which no OpenRouter-lane binary contains.)
3. **llm.rs/mod.rs:** a `quota_pause` option, false for Qwen. `LlmClient::guard()` builds the Guard from the latch and that option.
4. **decision.rs:** decision services pass an empty Guard; Qwen does not use them.

Not touched between the builds: the request builders (`constrained_request`/`schema_body`, `choose_compatible`'s readout requests, `free_text_request`), `merged` (the setup's extra fields), the prompts, the option order, the ledger, `parse_chat_completion`, and how answers are stored.

## Check on the stored requests (two samples, not an audit)

This compares two requests only; it is not an audit of all requests. The first stored E1 request (B0) and the first stored game request (B1) have identical fields except the letter enum, which follows the position's option count: keys `logprobs, max_tokens, messages, model, provider, reasoning, response_format, temperature, top_logprobs, usage`. The values are the same: `max_tokens` 16, `model` qwen/qwen3.8-flash, provider `{order: [alibaba], allow_fallbacks: false, require_parameters: true}`, `reasoning {enabled: false}`, temperature 1.0, `top_logprobs` 5, `usage {include: true}`. The system prompt is identical.

## Conclusion

Nothing Qwen3.8 Flash sends changed between the builds, and the identity check on what it receives compares the same fields. This rests on the source diff above (B0 and B1 sources as qualified above) and a two-request sample. E1 was answered by a binary whose hash is unknown; its source comes from my session record only. Per Zeki and Ümit, the runs are kept as they are, the unknowns are marked here, and nothing is replayed or invalidated because the builds changed.

## From now on

- Every lane runs a pinned, immutable copy named by commit: `target/improve-bin/jevgammon-<commit>`. Local and subscription lanes: `jevgammon-1270c04` (sha256 19357c4e…). The Codex lane: `jevgammon-938c842` (sha256 0a342d9e…; Zeki's GO #3245), built in its own target directory.
- `improve.py` (5ac479e and later) writes the binary's path, sha256, commit and mtime into every step's `step_start` log line. It refuses a real run on an unpinned binary. **Limitation:** the commit and the "pinned" flag come from the file name. That is a naming convention, not a build attestation; the sha256 identifies the file but does not prove which source built it.
- The OpenRouter lane will be restarted on a pinned copy when its held models (GLM-5.3, Kimi K3.1 Pro, DeepSeek) are released. Qwen3.8 Flash's remaining steps keep running in the already-started process on the path, which holds B2. Its later step lines therefore carry no binary field (the module was loaded before 5ac479e); this note covers them.

## Correction to the Codex review notes

`mailbox/improve-codex-review2/README.md` said rejected replies are logged "with … the raw reply and the reported cost. This includes a Codex stream without `response.completed`". For that case the log line has `response` and `reported_cost_usd` null: the stream could not be parsed, so no raw reply or cost is kept for it. Nothing recovers a truncated stream. Its spend, if any, is not in that log line; a Codex lane is $0 billed (subscription).

## Receipts of later Qwen3.8 Flash steps (appended as they happen)

Each receipt names the `jevgammon` process that started the step and the binary it ran: `/proc/<pid>/exe` and its sha256 when the process could be caught; otherwise the binary at the path at its start time.
- **S1 T10 (hook's first asking):** `jevgammon ask` pid 3934684, started 16:45:18 UTC. `/proc/3934684/exe` → `target/release/jevgammon` (not deleted), sha256 `19357c4e46af78eb07bc8125d7bf7f99e9b463464951caea41d5f4f18dd7fa11` = **B2**, observed 16:4x UTC. Its parent, the S1 match (pid 3875115, B1), was still running the after-game hook at that time.
- **S2 games:** match pid 4051283, started 17:00:45 UTC. `/proc/4051283/exe` → `target/release/jevgammon` (not deleted), sha256 `19357c4e…` = **B2**, observed 17:01 UTC. S1 finished at 17:00:45; its T10 re-ask round (if any) started after 16:26:50 = B2 by the path rule.

## Execution conditions: GPU power limit (local lane)

- About 2026-11-09 07:37 UTC Can lowered the power limit of all four bariton GPUs from the default 600 W to 400 W (bus #3385; `nvidia-smi` power.limit 400 W, power.default_limit 600 W). It affects speed and latency (time is a recorded metric), not answers by design. Gemma 4 31B (on)'s S1 attempt 3 (started 01:54 UTC on GPU-1115ade0) straddles the change; nothing was restarted for it. A `power_limit` event is in each local model's run log.

## Local lanes split across two GPUs (Can #3383), 2026-11-09

- From 07:41:07 UTC a second local lane, `improve-local3`, runs on GPU-e4f2a538 (index 3; device e1:00.0, root port e0:01.1; Can: "yes try it, I check the card and riser each time"). It runs Qwen3.8-27B (on), then LFM2.5-24B-A2B (on). Its watcher `improve-xid-watch3` stops only `improve-local3` and its containers. `improve-local` on GPU-1115ade0 keeps Gemma 4 31B (on). Each model is claimed by exactly one lane (`runs/<model>/lane.json`). Per model nothing changes: one model per GPU, its league server script and arguments, and the same concurrency policy. This is an execution change, not a protocol change, and it is recorded as `lanes_split` in the three models' logs.
- The GPU-0 lane was started at 01:52 with the earlier `run_local.sh`, whose queue still lists Qwen3.8-27B and LFM2.5. Its loop starts a model's server container (fixed league container names) before improve.py's claim check. So it could reach and stop lane 3's container. The script files were replaced by rename, but the running bash keeps its loaded copy.
- **SIGSTOP/SIGCONT episode:** at 07:38:25 UTC I sent SIGSTOP to that lane's shell (pid 806805) to keep it from proceeding past Gemma. At 07:39:14 I sent SIGCONT after Main asked not to freeze it. Only the shell was stopped, for 49 s, while it was waiting on its child. Gemma's run (pid 812671, S1 attempt 3) was never signalled and kept running.
- **Guard instead:** `improve-lane0-guard` (`lane0_guard.sh 812671 806805`, started 07:40:48 UTC, logged as `lane0_guard_start` in Gemma's log) checks once a second. It fires as soon as Gemma's run process exits (normally, paused or stopped), or as soon as the lane's shell starts any child for Qwen3.8-27B or LFM2.5. It then stops `improve-local` and the container `v3-gemma4-31b`, and nothing else. Gemma's run is never touched. The GPU-0 watcher was restarted at 07:41:05 with the per-lane script, so it now stops only `improve-local` and `v3-gemma4-31b`.

## 2026-11-12: switch to the fixed runner jevgammon-8b6f9a1 at step boundaries (QC 2026-11-12 D1; Ümit via Zeki #5264)

- **Why.** `jevgammon-1270c04` read an HTTP-200 reply carrying a provider error (`choices[0].error`, `finish_reason: "error"`, top-level `error`) as a model reply with no letter: stored invalid (tests) or a random play (games). The fix is 018138f on main (merged by 175141f). That build cannot run the lanes, because main lacks `lesson`, `--after-game`, `--model1-config` and the route checks. The fix was therefore ported to the lanes' runner:
  - **`jevgammon-8b6f9a1`** = 1270c04 + the fix (branch `improve-error-reply-fix`), sha256 `e415773e876670f4d5cc1379705acc0f65b4acd02c613b91941c8175ed181661`; Rust 83 passed;
  - **`jevgammon-724406a`** for the Codex lane = 938c842 + the same change (branch `improve-codex-error-reply-fix`), sha256 `1e529cdb7a210f8fcf7e133a52addd9f41e69fab65dc38d44af16b51bcfc95fe`; Rust 88 passed.

  Both are built in their own worktrees (`~/.cache/wt/…`, own `target/`) and copied read-only to `target/improve-bin/`. Patches, test output and build inputs are in `mailbox/qc-run2/`.
- **What changes in behaviour.** Only such an error reply: it is now a failed attempt, retried like a 5xx (4 attempts). Out of retries, the decision fails as transport: a test position stays failed and is re-asked by `run_test`; a match fails and the series is replayed from game 1 with the same dice (plan §5). No request builder, prompt, option order, route check, ledger or scorer changed. Also, `harness_commit` now records the binary's own build commit (git in its build tree), not the jevgammon-improve HEAD.
- **When.** Never inside a step. `workspace/improve/switch_at_boundary.sh` (improve 0771b84) waits for the model's current step's `aggregate.json`, writes the operator hold, waits for the lane to exit paused, removes the hold, logs a `binary_switch` event, and restarts the lane with its committed start script, now pinned to 8b6f9a1.
  - **Qwen3.8-27B (on)** (unit `improve-switch-local3`): S4 (games, lessons, full T10) finished on 1270c04 at 11:29:53 UTC. E3's `step_start` was logged on 1270c04 and paused before any request (0 E3 answers on 1270c04). Lane `improve-local3` and its watcher were restarted at 11:29:58. E3 `step_start` at 11:32:50 is on 8b6f9a1 (sha256 e415773e…), and the E3 answers carry harness 8b6f9a1, clean. E3 and S5 run on 8b6f9a1.
  - **LFM2.5-24B-A2B (on)**: every step runs on 8b6f9a1. It follows Qwen in the restarted `improve-local3`.
  - **Grok 4.7 (on)** (unit `improve-switch-xai`): S4 (games 4–10 and T10) finishes on 1270c04. The switch comes after S4's aggregate, and E3 and S5 run on 8b6f9a1. If the hold lands after E3's own hold check (a few seconds' race), E3 runs whole on 1270c04 and the switch comes before S5, still at a step boundary. Each step's `step_start` line names its binary.
  - **GPT-6.1 Sol (high), GPT-6 Astra (high)** (Codex lane, not started): started with `IMPROVE_PIN=724406a workspace/improve/run_lane.sh <lane> gpt-6.1-sol-high gpt-6-astra-high`, so every step runs on 724406a.
  - All other start and restart scripts (`run_lane.sh`, `run_local_start.sh`, `provider_wait_restart.sh`, `claude_wait_restart.sh`, `run_openrouter.sh`, `run_subs.sh`) now pin 8b6f9a1. Any Run 2 of a finished arm uses it too.
- **Already-run steps stay as they ran on 1270c04.** The QC found error replies scored as answers only in DeepSeek V4.1 Flash (on): 6 test answers and 1 game turn, handled by its Run 2 (`mailbox/qc-run2/README.md`).
