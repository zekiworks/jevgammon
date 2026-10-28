# Nackgammon paired test: Gemini 4 Argon (on) smoke test (2026-10-28) - STOPPED

For Can. **The stop condition was met: 7 of 50 answers (14%) were invalid, above the 5% limit. Argon (on)'s paired-test run was not started.** No paired-test position was asked.

- **Setup:** `Gemini 4 Argon (on)`, stored v3.db settings unchanged (Antigravity subscription, thinking level high, `parallel` 4). Config `leagues/smoke-argon-on.json`.
- **Smoke procedure:** as for earlier new setups (Terra): the 50 positions of `positions/smoke.jsonl`, the leagues' prompt `bg-v2` and option-order seed. Run with `jevgammon ask`, time limit 600 s, harness 6693b5b. Answers are in `smoke/argon-on-smoke.db` (git-ignored).
- **Run:** 15:32:31 to 16:16:52 UTC (44 min). No other Antigravity job ran alongside it.

| | Value |
|---|---|
| Answered | 50 / 50 (0 failed, 0 timed out, 0 retries) |
| **Invalid** | **7 (14%)**: smoke-0008, -0014, -0016, -0031, -0035, -0045, -0049 |
| Cause of every invalid | the reply hit the 32,768 output-token limit while still thinking (output 32,768 tokens, almost all reasoning), so no letter came back. Each took 352–405 s. |
| Output tokens per decision | mean 17,016 (reasoning 16,999) |
| Input tokens per decision | 3,419 |
| Request time | mean 201 s (valid answers 172 s, invalid 382 s), max 405 s |
| API-equivalent | $8.85 for 50 decisions ($0.177 per decision; not billed, subscription) |

**Compared with the estimate** (`mailbox/Nackgammon - Argon (high) estimate 2026-10-28.md`): this is the "late-day" profile, not the central one. Output was 17,000 per decision against 6,560 central and 19,600 worst. The invalid rate was 14% against 4% central and up to 19% worst. Argon (on) is the only League 3 setup with invalid answers in the league (71 fallbacks, all empty replies after long thinking).

**If it ran anyway, under the frozen rule:** the paired start (400 positions) would take about 5.6 h at parallel 4 (201 s per decision) and cost about $71 API-equivalent. At this rate it would produce about 56 invalid answers. Each would be scored with the position's Random error, so the drop would mostly measure the invalid rate. That was the reason for the 5% limit.

Waiting for Can: drop Argon (on) from the paired test, or run it anyway (exploratory, invalid answers scored under the frozen rule).
