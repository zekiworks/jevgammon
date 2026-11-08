# Did they improve? Runner binary provenance: Qwen3.8 Flash (off), OpenRouter lane

Written 2026-11-08 by the experiment's agent. This is a disclosure of a gap: the OpenRouter lane (systemd unit `improve-openrouter`, started 16:10:46 UTC) ran the unpinned path `/home/cbasaran/code/jevgammon-improve/target/release/jevgammon`. I rebuilt that path twice while Qwen3.8 Flash was running, to prepare the other lanes. Each `jevgammon` process keeps the binary it was started with. A process started after a rebuild ran the new one.

## The three builds at that path

| Build | Written at (UTC) | Built from | sha256 | Copy kept |
|---|---|---|---|---|
| B0 | about 16:09–16:10 (exact mtime lost: overwritten) | branch `improve`, worktree clean at 88e5da0 (= src of 0c9270c; 88e5da0 only adds run_queue.sh) | **unknown** | no |
| B1 | 16:24:05.8 (seen as the file's mtime at the time) | working tree = the non-test src of 1270c04, before its tests were added [INFERENCE: edit order in my session; see below] | `2360ace5669d12055e3610c552ee3cd94c10df7e59e6ab30149a23a0d8cbaa9a` | yes: `target/improve-bin/jevgammon-B1-recovered-from-pid3875115` (copied from `/proc/3875115/exe` of the running S1 match) |
| B2 | 16:26:50.165 | 1270c04 (committed, clean) | `19357c4e46af78eb07bc8125d7bf7f99e9b463464951caea41d5f4f18dd7fa11` | yes: identical to `target/improve-bin/jevgammon-1270c04` (the local and subscription lanes' pinned copy) |

The path has not changed since 16:26:50: its mtime is 16:26:50.165 and its sha256 equals B2's, checked at 16:36. Later builds went to separate target directories (`target/codex`). I will not rebuild `target/release` again while the lane uses it.

## Which build ran each Qwen3.8 Flash step

Rule: a process ran the build present at the path when it started.

| Step | Processes | Started (UTC) | Build | How known |
|---|---|---|---|---|
| setup | `jevgammon rank --dry-run` (schema only, no request) | 16:10:46 | B0 | before 16:24:05 |
| E1 (200 answers, empty context) | one `jevgammon ask` process, one round only: `test-E1.log` has a single "round 1" header; all 200 answered by 16:26:08 | 16:10:46 | **B0** | started before 16:24:05 and ran as one process to the end. B0's hash cannot be given: no copy was kept and the path was overwritten |
| S1 games (10 games) | the match process, pid 3875115 | 16:26:08 | **B1** | `ps` start time 16:26:08 lies between 16:24:05 and 16:26:50. `/proc/3875115/exe` → `target/release/jevgammon (deleted)`, sha256 2360ace5…, copied |
| S1 lesson calls (`jevgammon lesson`, one per game) | started from the after-game hook | game 1's at 16:28:55, later ones after it | **B2** | started after 16:26:50, and the path has held B2 since |
| S1 T10 (asked in the hook after game 10; any re-ask) | `jevgammon ask` | after game 10 | **B2** | after 16:26:50 |
| S2 to S5, E2, E3 | match, lesson and ask processes | after 16:26:50 | **B2** | the path holds B2 for the rest of Qwen's run; nothing rebuilds it |

Exact: the S1 games (B1, hash from the live process) and everything from S1's lessons onward (B2, hash).
Not exact: E1's binary. The build source (0c9270c) is known; the hash is not.

## Source differences, 0c9270c → 1270c04, limited to what Qwen3.8 Flash sends and receives

`git diff 0c9270c 1270c04 -- src` touches src/http.rs, src/players/llm.rs, src/players/mod.rs and src/players/decision.rs (133+, 36−). The non-test parts:

1. **http.rs:** `send` and `send_metered` take a `Guard { stop, quota_fatal }` in place of the stop latch alone. `quota_fatal` makes a 429 final at once. Qwen's player config does not set `quota_pause`, so `quota_fatal` is false and 429 handling is the league's, as in B0. The stop latch is checked exactly as in B0.
2. **llm.rs `ExpectRoute`:** `provider` became optional and the model/provider fields are read by JSON pointer, defaulting to `/model` and `/provider`. Qwen's config sets `models` and `provider: "Alibaba"` with no pointers, so the same two fields are compared against the same values. New fields (`model_pointer`, `provider_pointer`, `allow_dated`) default to off.
3. **llm.rs/mod.rs:** a `quota_pause` option, false for Qwen. `LlmClient::guard()` builds the Guard from the latch and that option.
4. **decision.rs:** decision services pass an empty Guard; Qwen does not use them.

Not touched between the builds: the request builders (`constrained_request`/`schema_body`, `choose_compatible`'s readout requests, `free_text_request`), `merged` (the setup's extra fields), the prompts, the option order, the ledger, `parse_chat_completion`, and how answers are stored.

## Check on the stored requests

The first stored E1 request (B0) and the first stored game request (B1) have identical fields except the letter enum, which follows the position's option count: keys `logprobs, max_tokens, messages, model, provider, reasoning, response_format, temperature, top_logprobs, usage`. The values are the same: `max_tokens` 16, `model` qwen/qwen3.8-flash, provider `{order: [alibaba], allow_fallbacks: false, require_parameters: true}`, `reasoning {enabled: false}`, temperature 1.0, `top_logprobs` 5, `usage {include: true}`. The system prompt is identical.

## Conclusion

Nothing Qwen3.8 Flash sends changed between the builds, and the identity check on what it receives compares the same fields. This rests on the source diff above and the stored-request comparison. E1 was answered by a binary whose source is known (0c9270c) but whose hash is not, and this note says so.

## From now on

- Every lane runs a pinned, immutable copy named by commit: `target/improve-bin/jevgammon-<commit>`. Local and subscription lanes: `jevgammon-1270c04` (sha256 19357c4e…). The Codex lane: `jevgammon-6e5a15e`, built in its own target directory.
- `improve.py` (5ac479e and later) writes the binary's path, sha256, commit and mtime into every step's `step_start` log line. It refuses a real run on an unpinned binary.
- The OpenRouter lane will be restarted on a pinned copy when its held models (GLM-5.3, Kimi K3.1 Pro, DeepSeek) are released. Qwen3.8 Flash's remaining steps keep running in the already-started process on the path, which holds B2. Its later step lines therefore carry no binary field (the module was loaded before 5ac479e); this note covers them.
