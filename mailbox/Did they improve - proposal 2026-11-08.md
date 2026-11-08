# "Did they improve?" — one proposal (for Ümit and Can)

Draft, not the pre-registration. No model call has been made. Details and per-model numbers: `Did they improve - plan draft 2026-11-08.md` (0567bb2).

## The experiment in one paragraph

Every chat model on the leaderboard, at its leaderboard setting, plays 5 series of 10 games against GNUbg weak. After each game it writes up to 5 lessons (150 words) and carries them into the next game of the same series. After game 10 it answers the pilot's 200 test positions with that series' lessons in the prompt. Separately, it answers the same 200 positions 3 times with an empty context, spread through the run. "Improved" compares the two.

## The rule

**Improved** = risks found with lessons (mean of the 5 tests after game 10) minus risks found with no memory (mean of the 3 empty runs) is **more than the model's threshold**, and right safety drops by **no more than 5 points**.

**Threshold = the larger of (a) the range (max − min) of the model's own 3 empty runs and (b) 3 points.**

Why not (a) alone: in the Gemma pilot, five repeated empty runs gave exactly the same risks found (28.0 every time, range 0), yet an earlier empty run of the same prompts gave 25.0 and the 20 empty-context budget tests ranged from 24 to 30. A range of 0 from 3 runs would let a change of one position (1 point, out of 100 risk-pays positions) count as learning, although the same model moved 3 points with no memory at all. 3 points is the largest difference we observed between an empty run and the later empty runs of the same prompts on the same server; it is a floor, not a significance test. If a model's own range is larger, its own range is used.

This rule is a decision rule, not a statistical test. The page says so.

## Fixed in the design (proposed; no decision needed unless you object)

- Settings: each model at its league settings. Temperature 1.0 where the route accepts it; no route lets us send a common seed, and some (Astra, Sol, Claude) don't let us set temperature. The page lists what each model accepted.
- Series run one at a time, so every test runs under the same load.
- A model gets yes/no only when all 5 series, all 5 tests after game 10 and all 3 empty runs are complete. Failed requests are re-asked; invalid answers are left out of the shares and their count is shown.
- Games played with lessons count in no ranking.
- The Gemma pilot keeps its own pre-registered verdict, marked "pilot (different design)".
- Before the first call, the page shows the rule, the lesson prompt, the model list and "Results will be published whichever way they go."

## Real decisions

**Scope (Ümit):**
1. Cygnet: leave out (its route doesn't pass the lessons to the model), or pay for a change and verify it.
2. DeepSeek V4.1 Flash: include via OpenRouter (not its league route; labelled), or leave out.
3. The 3-point floor above: accept, or another value.

**Order (Ümit):**
4. API models first, cheapest first, while the bariton GPUs are taken (until ~08:00 UTC tomorrow); local models after.
5. ChatGPT quota after 13 Nov 11:38 UTC: the Astra (high) re-ask first, then Sol and Astra here.

**Money:**
6. Can: OpenRouter has ~$13. This experiment needs ~$103 billed (Qwen3.8 Flash, GLM-5.3, Kimi K3.1 Pro, DeepSeek); logic's and turkce's Flash runs need ~$101 + turkce's share from the same account.
7. Ümit: after each API model's 1-series cost check, I send $ and time and wait for your go. Subscriptions cost $0 billed but use quota (~$1,500 list-price equivalent in total).
