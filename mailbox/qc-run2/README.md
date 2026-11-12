# QC 2026-11-12 Run 2: fixed runner builds and plans

Authority: Ümit via Zeki #5264 and #5276. Source: `mailbox/backgammon-qc-2026-11-12.md`, defects 1–3.

Nothing paid has run. No v3.db row and no lane DB row was written. The checks here are read-only (sqlite `mode=ro`).

## 1. The parser fix and the builds

**Patch.** `parser-patch-1d08e51..018138f.diff` is `git diff 1d08e51..018138f`, the fix as merged into main by 175141f. A 200 reply that carries a provider error (top-level `error`, `choices[0].error`, or `finish_reason: "error"`) now counts as a failed attempt and is retried like a 5xx. Once out of retries, the decision fails as transport and is never stored as invalid. The change is in `http::send_with_backoff`.

**Ports for the learning lanes.** The lanes' runner is on branch `improve` (1270c04). It is not an ancestor of main: it has `lesson`, `--after-game`, `--model1-config` and the route identity checks. A 175141f build therefore cannot run a lane. The same fix was ported twice:
- `port-8b6f9a1-on-1270c04.patch`: branch `improve-error-reply-fix`, commit 8b6f9a1 = 1270c04 + the fix. There was one conflict in `http::send_until`, resolved so the improve-only `quota_fatal` 429 rule stays. The fix's test helper was adapted to the improve `Options`/`Player` fields. No request builder changed.
- `port-724406a-on-938c842.patch`: branch `improve-codex-error-reply-fix`, commit 724406a = 938c842 (the Codex lane's runner) + 8b6f9a1's change. The cherry-pick applied cleanly.

| Binary | Built from | Worktree (own `target/`) | sha256 | Tests |
|---|---|---|---|---|
| league runner | 175141f (tree 1b58848), clean | `~/.cache/wt/runner-175141f/target/release/jevgammon` | `034a39b491e955e7182c51e4708009fe386600e3cd2e7141434c8d5ee9ca0e27` | 75 passed (`test-runner-175141f.txt`) |
| lanes: `jevgammon-8b6f9a1` | 8b6f9a1 (tree ffb0be4), clean | `~/.cache/wt/improve-error-reply-fix`; pinned copy `~/code/jevgammon-improve/target/improve-bin/jevgammon-8b6f9a1` (read-only) | `e415773e876670f4d5cc1379705acc0f65b4acd02c613b91941c8175ed181661` | 83 passed (`test-improve-error-reply-fix.txt`) |
| Codex lane: `jevgammon-724406a` | 724406a (tree 21a5b6e), clean | `~/.cache/wt/improve-codex-error-reply-fix`; pinned copy `…/improve-bin/jevgammon-724406a` (read-only) | `1e529cdb7a210f8fcf7e133a52addd9f41e69fab65dc38d44af16b51bcfc95fe` | 88 passed (`test-improve-codex-error-reply-fix.txt`) |

**Build inputs (all three):**
- Command: `CARGO_TARGET_DIR=<worktree>/target cargo build --release`, run in each worktree.
- Toolchain: rustc 1.97.1 (8bab26f4f 2026-07-14), cargo 1.97.1.
- `Cargo.lock` sha256 `d7048551…88494`; `Cargo.toml` sha256 `bf64a9f1…0ed4b` (identical in all three).

The two new tests (`error_reply_is_retried_and_the_next_answer_used`, `error_replies_only_fail_the_decision_as_transport`) pass in all three.

**Note.** At startup the runner records `harness_commit`/`harness_dirty` by running git in its build tree (`CARGO_MANIFEST_DIR`). The new builds will therefore record 8b6f9a1 / 724406a / 175141f. The old 1270c04 build recorded the jevgammon-improve checkout's HEAD. The build worktrees must stay while their binaries run.

## 2. DeepSeek V4.1 Flash (on): plan (Zeki #5276)

**Series reset, checked from stored hashes and wiring.** Script: `verify_series_reset.py`; output: `deepseek-reset.json`. In all 5 series:
- Each game's play requests carry exactly that series' `contexts/after-g(N-1)`. Game 1 has no notes. Mismatches: 0 (S1 259, S2 295, S3 300, S4 289, S5 365 exchanges).
- Each T10 request carries that series' own `after-g10`: 276 of 276 in S5, with sha256 `19f30d96…` equal to the log's `context` hash. S1 shows the same.
- Every `after-gN` recomputes from that series' `lessons-g01..gN` (10/10). Every lesson file recomputes from its call (10/10).
- The lesson calls send only `lesson-system.txt` plus that game's record. The template fields are `{game}` and `{record}`. No lesson line from any series appears in any lesson call.
- No lesson line of another series appears in any game or T10 request: 0 everywhere.
- The E runs carry no notes.

Each series therefore starts from a reset. S2–S5 do not depend on S1, and S5's 4 items can be refilled alone.

**Run 2:**
- **(a) S1 whole.** Seed 5588155524604542475, the same dice. 10 games, 10 lessons regenerated, the full 200-position T10. Fixed binary jevgammon-8b6f9a1, same route: OpenRouter → Fireworks, `deepseek/deepseek-v4.1-flash`, reasoning low, max_tokens 32,768, the same player config.
- **(b) S5-T10 refill.** Answers 1465, 1466, 1491 and 1492 (lp-31646, lp-173367, lp-90458, lp-18007) are re-asked. The config is the stored `S5/test-S5.json`: `prompt_note` sha256 = S5 `after-g10` = `19f30d96…`; order_seed, bg-v2, 4 in flight.
- Both are stored in a separate Run 2 state root. The original rows are kept, and the site's main results are not touched.
- Game turn 19 is part of S1 and is replayed with it.

**Mechanism.** No code exists yet; it is to be built on approval, on a branch, and dry-run first (`IMPROVE_DRY=1`):
- improve.py runs under `IMPROVE_ROOT=<run2 root>` from a worktree of branch `improve`, with two additions:
  - a step filter (`S1` only);
  - `billed_total` that also counts the original root's ledgers, so rule (b), the share and the balance gate see $78.14 already billed.
- A `refill` command asks the 4 positions with the stored S5 config, under a new setup name `… | s05 | a1 | T10 | run2`.
- The live improve.py, which the running lanes' hooks load, is not edited.

**Money.**
- Billed now: experiment total $78.1389. DeepSeek $50.3232: E1 4.03, S1 6.61, S2 7.84, E2 3.88, S3 7.17, S4 7.76, E3 3.87, S5 9.15.
- Expected: S1 replay ≈ $6.6 (S1 was $6.61; the other series $7.17–9.15) plus refill ≈ $0.1. Worst case for the refill: 4 × 32,768 output tokens × $1.2/M ≈ $0.16, plus retries.
- Limits:
  - rule (a) for DeepSeek: 1.5 × $44 − $50.32 = **$15.68** (binding);
  - share: $107 − $78.14 = $28.86;
  - rule (b): $110 − $78.14 = $31.86.
- Step ledger cap: $15.68 (hard, before each request).

**Time.** S1 took 4 h 58 min (13:03–18:01 UTC on 9 Nov, T10 68 min). The refill takes minutes.

**Verdict** (output: `deepseek-verdict.json`):
- Stored (original run, as published): Yes. Change in risks found +7.21 against a threshold of 5.00. Change in right safety −4.17, against a limit of −5.
- Run 2: **verdict pending until Run 2 completes** (S1 is being replayed). No bound is claimed. An earlier draft said the S5 refill could not flip the verdict; that claim is withdrawn (Zeki #5319).
- The refill itself has finished (counts below, under "Run 2 progress"). The final Run 2 verdict comes from `run2-report.json` (improve.py `run2-report`: the site's rule, original and Run 2 side by side, every step named run2, refill or reused).
- The site shows DeepSeek as QC-pending.

## 3. Muse Ember (max) #926: full-match Run 2 (proposal, not run)

The original #926 row, its score and League #20's table stay unchanged. Run 2 is played in its **own database**, with no void and no splice.

Inside v3.db it could not work:
- the runner reuses a pair's existing valid match wherever the pair met, so it would not replay;
- a hidden league's matches "still count wherever both players meet", which would double count.

Same dice:
- League dice come from the two names and the rules (`Rules::pair_seed`, `Rules::sides`).
- Recomputed offline from #926's stored rules (`rules-v1 rounds=3 clock=- delay=- max_turns=300 prompt=bg-v2 order_seed=1190975713392774006 mirror=1`): pair seed −7919611811006792258 = #926's seed, and Muse Ember (max) is model1. The new database gets this pair as new, so it gets this seed and these seats.

Config: `ember-926-run2.json`.
- League #20's rules fields unchanged.
- Players: `Muse Ember (max)` and `Random`, each equal to v3.db `players.settings`. Ember keeps OpenRouter → Meta only, fallbacks off, reasoning max, max_tokens 32,768, and the shared ledger `workspace/late-ember/state/ember-budget.db` with its $19.50 hard cap.
- `only_pairs_of` Muse Ember (max), hidden.

Commands (run from the main checkout; Ümit's go first):

```
cd /home/cbasaran/code/jevgammon
B=/home/cbasaran/.cache/wt/runner-175141f/target/release/jevgammon   # sha256 034a39b4…, 175141f clean
sha256sum "$B"
mkdir -p workspace/late-ember/run2
cp mailbox/qc-run2/ember-926-run2.json workspace/late-ember/run2/
systemd-run --user --unit qc-run2-ember-926 --working-directory="$PWD" bash -c \
  "set -a; . ~/.keys; set +a; exec $B league --config workspace/late-ember/run2/ember-926-run2.json \
   --db workspace/late-ember/run2/ember-926-run2.db >> workspace/late-ember/run2/run2.log 2>&1"
# after: one match, seed -7919611811006792258, model1 Muse Ember (max), harness 175141f clean
sqlite3 -readonly workspace/late-ember/run2/ember-926-run2.db \
  "select id,seed,model1,model2,score1,score2,status,harness_commit,harness_dirty from matches"
```

Money and time:
- Ember ledger: settled $13.274 (`SUM(cost_usd)`; the brief says $13.71). Left under the $19.50 hard cap: $6.23 (or $5.79 at $13.71).
- #926 cost $0.267 for 1 round (39 Ember turns: 37 model, 2 fallback) in 18.5 min. Rounds 3, with one more on a tie: at most ≈ $1.1 and ≈ 75 min.

**Site effect.**
- None on any table or score: v3.db is untouched, and the site does not read the Run 2 database.
- The Ember row note on branch `site-qc-pending` ("one decision under QC (match #926 Run 2 pending)") stays until Run 2 is reported. It then changes to the Run 2 result, marked as not counted, with the original standing.

## 4. Gemini 4 Argon (on): Run 2 plan (read-only)

**Served model.**
- improve.py route: `antigravity/gemini-4-argon`, reasoning high (Antigravity id `gemini-4-argon-high`). `expect.models = ["gemini-4-argon", "gemini-4-argon-d"]` at `/response/modelVersion`.
- Last replies (2026-11-10, S5 to 22:09:37 UTC) are all `gemini-4-argon`: games 418, lessons 10, T10 277. No Argon reply is stored after that.
- In the league on 2026-10-28, both were served: match 762 `gemini-4-argon` (182), then match 761 `gemini-4-argon-d` (125). So the backend has alternated before. Whether `gemini-4-argon` is served *now* needs one $0 probe, which was not sent.

**Separability.** Script: `verify_series_reset.py`; output: `argon-reset.json`. modelVersion tallies are per step:
- **Context.** Each series starts from a reset: own contexts only, game 1 without notes, 0 lesson lines of another series in any request. E runs carry no notes.
- **Backend.**
  - E2 (277), E3 (277), and S3–S5 (games, lessons, T10) are 100% `gemini-4-argon`.
  - `-d` replies are confined to E1 (257), all of S1, and S2 games 1–6 plus S2 lessons g1–5. S2 game 6 is mixed: 10 `-d`, 31 not.

**Run 2:**
- **Run again:** E1, S1, and the whole of S2 (10 games, 10 lessons, T10). Use `expect.models = ["gemini-4-argon"]` only, so a `-d` reply stops the run (route check, fail closed). Same Antigravity route; $0 subscription.
- **Reused:** E2, E3 and S3–S5, disclosed as reused rather than fresh.
- **Whole arm:** not needed, because the parts are separable.

**"128".** In the stored data:
- `words_written: 128` is the lesson written *after* S2 game 1. It first enters S2 game 2's prompt (`after-g01`) and is not cross-series.
- Answer id 128 is an E1 answer, which carries no notes.

Under either reading, the hashes show no context crossing series. [INFERENCE: which "128" was meant.]

**Time.**
- On `gemini-4-argon`, the original steps took: E2 43 min, E3 44 min, S3 3 h 44 min, S4 4 h 17 min, S5 3 h 59 min. Run 2 (E1 + S1 + S2) ≈ **8 h 45 min** (range 8 h 15 min – 9 h 20 min).
- Under `-d`: E1 took 3 h 14 min and S1 15 h 31 min. If `-d` is served, Run 2 stops at once instead. Antigravity quota pauses would come on top.
- A whole-arm re-run would take ≈ 22 h.

**Verdict** (`argon-verdict.json`):
- Stored (original run, as published): No. Change in risks found +6.48 against a threshold of 12.67. That threshold was E1's 66.7 (under `-d`, 45 invalid) minus E3's 54.0.
- Run 2 uses the **same threshold formula**: max(range of the empty runs' risks found over E1 (Run 2, corrected) + E2 + E3, 5), as `tools/site/improve_validate.py` and improve.py `verdict_of`. The old 12.67 is not reused, and no threshold is chosen after the fact.
- Run 2: **verdict pending until Run 2 completes**. The site shows QC-pending.

## Run 2 progress (2026-11-12, approved by Main within Zeki #5264/#5276)

Components, run ids, units, binaries, seeds, routes and reused steps: `run2-manifest.json`. Build identity: `build-identity.txt`. Step-boundary switches in the live lanes: `step-boundary-events.jsonl` (regenerate with `boundary_events.py`). Argon's served identity per step: `argon-served-identity.json` (`served_identity.py`).

- **Ember #926 Run 2.** Done 11:38–11:49 UTC, own database, match 1.
  - Seed −7919611811006792258, Muse Ember (max) model1, harness 175141f clean.
  - Muse Ember (max) 6–0 Random (original #926: 5–0), 1 round.
  - 52 Ember turns: 36 model, 12 forced, 2 no-move, 2 fallback. Both fallbacks are model replies cut at the output limit (`finish_reason` length at 32,939 and 32,944 tokens), scored invalid as in the original; 0 provider error replies.
  - 50/50 exchanges `meta/muse-ember` / Meta. Cost $0.2864.
  - The original #926 row and League #20's table are unchanged.
- **DeepSeek, S5-T10 refill.** Done.
  - 4/4 answered, 0 invalid, 0 failed, billed $0.1191, harness 8b6f9a1 clean.
  - Each position's first request is byte-identical to the original's.
  - S5-T10 with the refill: valid 193 → 197, invalid 7 → 3, risks found 52.13 → 53.06, right safety 84.85 (unchanged: all 4 are risk positions).
- **DeepSeek, S1.** Running since 11:54:21 UTC.
  - Game 1's first decision: the same dice (4-1), the same position, and a byte-identical request as the original's.
  - Step ledger cap $15.6768 (rule (a)).
- **Argon E1, S1, S2.** Running since 11:48:16 UTC. At 12:07 UTC: E1 87/200, 0 failed, 0 invalid; 116/116 replies `gemini-4-argon`.
- Final numbers and `run2-report.json` per model are added when each run completes. They contain counts only: no question, option or answer text.
