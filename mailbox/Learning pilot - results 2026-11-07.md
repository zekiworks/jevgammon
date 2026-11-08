# Learning pilot: results (run 7–8 Nov 2026)

**Results will be published whichever way they go, including no lift.**

The plan for this run is `mailbox/Learning pilot - plan 2026-11-07.md` (sha256 `1e9bc932…e8f6`, commits 5af8842 → 7719e1a), and it was all committed before the first model call. Four arms were run: control, records, lessons and budget. Each ran 10 series of 10 games against GNU Backgammon Beginner, and the 200-position evaluation set was asked once before game 1 (shared by all arms), then again after games 5 and 10.

- **Model and settings:** Gemma 4 31B (off), with League 2's settings, served by spark3.
- **Lesson prompt sha256:** `d7550015…550e`.
- **Evaluation set sha256:** `6c92e741…18e6`.
- **Harness:** branch `learning-pilot` at ba8b011 for the first smoke start, then e18ff59.
- **Cost:** $0 in API fees. The cost of local compute is not estimated.
- **Content:** this file holds aggregates only. It has no positions, no per-position answers and no lesson text.

## Verdict

**No arm meets the pre-registered signal rule (plan §8).** The rule requires two things, each averaged over the arm's 10 series:
- risks found after game 10 minus before game 1 is at least +10 points;
- right safety after game 10 minus before game 1 is at least −5 points.

| Arm | Risks found change | Right safety change | Rule met? |
|---|---|---|---|
| lessons | +8.3 pp (95% CI 7.1–9.4) | +1.1 pp | no: risks found falls short of 10 |
| records | +3.3 pp | +1.3 pp | no |
| budget | +2.8 pp | +0.8 pp | no |

Right safety held up in every arm.

**A17 learning lift: no arm improved in its games more than control did.** The lift is the error rate in games 1–3 minus games 8–10, compared with control's lift and paired by series. All three arms come out at −2.0 to −3.9 PR relative to control. For records and lessons the intervals include zero.

The budget arm's interval does not include zero, but that comparison is A/A: budget and control saw the same input (caveat 2). That interval therefore reflects variation from repeated identical runs, not an effect, and these intervals should be read as narrower than the true uncertainty.

## Evaluation set (200 positions: 100 Risk wins, 100 Safety wins), by arm and checkpoint

| Arm | Evaluation | Series | Error rate (PR) | Risk judgement | Risks found % | Right safety % | Risk appetite % | Invalid | Failed | Input tokens / decision | Records dropped (games) | Request time (h) | Median request (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all arms (shared) | T0 | 1 run | 55.6 | 60.5 | 25.0 | 96.0 | 18.0 | 0 | 0 | 4853 | 0 | 0.29 | 3.72 |
| records | T5 | 10 | 53.0 | 62.5 | 28.8 | 96.2 | 20.1 | 0 | 0 | 27374 | 0 | 3.06 | 3.75 |
| records | T10 | 10 | 53.1 | 62.8 | 28.3 | 97.3 | 19.4 | 0 | 0 | 39323 | 23 | 4.10 | 4.87 |
| lessons | T5 | 10 | 46.1 | 65.5 | 34.6 | 96.3 | 21.7 | 0 | 0 | 5744 | 0 | 2.93 | 3.66 |
| lessons | T10 | 10 | 46.4 | 65.2 | 33.3 | 97.1 | 20.4 | 0 | 0 | 6600 | 0 | 2.50 | 2.98 |
| budget | T5 | 10 | 54.0 | 62.8 | 28.7 | 96.8 | 18.9 | 0 | 0 | 4853 | 50 | 2.57 | 3.12 |
| budget | T10 | 10 | 54.7 | 62.3 | 27.8 | 96.8 | 18.6 | 0 | 0 | 4853 | 100 | 2.09 | 2.53 |

How to read the table:

- **Metric values** are means over series. The definitions are the site's: PR = 500 × mean 2-ply equity loss; risk judgement = 50 × (right risks ÷ Risk pays + right safety ÷ Safety pays). Plan §7 has the rest.
- **Control** has no T5 or T10 evaluation, because its context is always empty; its evaluation is T0.
- **Input tokens per decision** sums over the requests in a decision. Positions with more than 26 options are asked in groups.
- **Records dropped** counts whole earlier games left out of the context, summed over 10 series. For records, games are dropped once the context passes the limit. For budget, they are dropped once the context passes the lessons arm's token count.

## Signal rule (plan §8): T10 − T0, mean over 10 series, 95% bootstrap over whole series

| Arm | Risks found change (pp) [95% CI] | Right safety change (pp) [95% CI] | Rule met (≥ +10 and ≥ −5) |
|---|---:|---:|---|
| records | +3.3 [2.6, 4.1] | +1.3 [0.8, 1.8] | no |
| lessons | +8.3 [7.1, 9.4] | +1.1 [0.6, 1.6] | no |
| budget | +2.8 [1.7, 3.7] | +0.8 [0.4, 1.0] | no |

## Games against GNU Backgammon Beginner (100 games per arm)

| Arm | Series | Games | Decisions | Invalid | Error rate (PR) | Wins | Input tokens / decision | Median decision latency (s) | Records dropped (games, summed) | Context-limit drop steps | Empty budget points |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control | 10 | 100 | 2392 | 0 | 28.8 | 52 | 4355 | 3.62 | – | 0 | – |
| records | 10 | 100 | 2283 | 0 | 29.7 | 52 | 22848 | 3.22 | 23 | 40 | – |
| lessons | 10 | 100 | 2425 | 0 | 27.4 | 47 | 5115 | 3.74 | – | 0 | – |
| budget | 10 | 100 | 2383 | 0 | 29.7 | 52 | 4344 | 3.23 | 100 | 0 | 100 |

## A17 learning lift: error rate in games 1–3 minus games 8–10 (positive = better later), paired by series, 95% bootstrap over whole series

| Arm | Lift (PR) [95% CI] | Lift − control's lift (PR) [95% CI] |
|---|---:|---:|
| control | +0.48 [−6.55, 6.10] | – |
| records | −1.49 [−7.47, 5.33] | −1.98 [−8.71, 5.22] |
| lessons | −3.37 [−7.88, 1.52] | −3.85 [−11.09, 3.93] |
| budget | −2.57 [−9.09, 3.11] | −3.05 [−4.92, −1.18] |

Secondary comparison (records vs lessons vs budget, descriptive): on the evaluation set, lessons moved most from T0. Its error rate fell 9.2 PR and risks found rose 8.3 pp at T10. Records and budget moved about a third as much. In the games, no arm's error rate fell from early games to late ones by more than control's did.

## Caveats

1. **Small and narrow.** There are 10 series per arm, one model (Gemma 4 31B with reasoning off), one opponent (GNU Backgammon Beginner) and a single run. All numbers here are descriptive and outside the Holm correction.
2. **The budget arm never received records.** Its context was empty at all 100 of 100 points, because no whole game record ever fit within the lessons arm's token count. The plan's fixed reading (§11) applies: **"with this budget, record memory could not be provided"**, not "record memory didn't help". That makes budget an A/A comparison in two ways:
   - **In the games**, budget and control received the same input. Their differences come only from server-side numerical non-determinism: requests are batched differently, and the model runs fp8 on vLLM. The interval on budget's lift minus control's lift excludes zero all the same (−3.05 [−4.92, −1.18]). These series-bootstrap intervals therefore understate the true uncertainty.
   - **In the evaluations**, budget's T5 and T10 requests are identical to the T0 requests. Its change from T0 (+2.8 pp risks found, +0.8 pp right safety, −0.9 PR) therefore measures how much repeated runs of the same prompts differ from the single shared T0 run. T0 ran with 4 requests in flight, the later evaluations with 1. Part of every arm's change from T0 is this shift. Taken against budget rather than against T0, lessons is about +5.5 pp risks found and records about +0.5 pp. This comparison was not pre-registered and is descriptive only.
3. **T0 is one run.** The signal rule compares each arm's T10 mean, taken over 10 series, with a single shared T0 run. The bootstrap over series does not include T0's own measurement error.
4. **Records arm.** The context limit (26,879 tokens) was hit 40 times, and each time the oldest whole game was dropped. After game 10, between 1 and 4 earlier games were left out per series (23 in total: 2, 2, 1, 3, 1, 1, 3, 3, 3, 4). Records decisions carried about 23k input tokens on average, against about 4.4k for control.
5. **Smoke incident.** At the first smoke start, the systemd unit's Python had no `tokenizers` module.
   - The hook that runs after each game crashed after game 1 of records s1 and lessons s1.
   - Both series were replayed from game 1 with the same dice. Seeds, opening rolls and all 63 rolls of game 1 were compared and are identical.
   - The 2 aborted matches stay in the database.
   - One extra lesson call, made in the aborted lessons attempt, is archived and was not used.
   - Prompt, scoring, arms and the evaluation set were unchanged, so per the plan the smoke series count toward the 10.
   - Details are in `mailbox/learning-pilot-smoke-manifest/` and `mailbox/learning-pilot-manifest-final/`.
6. **Positions are not public.** The evaluation positions and the per-position answers stay private. No evaluation position appeared in any arm's context (0 excluded decisions).
7. **Run totals.**
   - 12,200 evaluation answers, all valid.
   - 9,483 game decisions, all valid.
   - 100 lesson calls; none was cut to fit the 5-lesson / 150-word limit.
   - Time: 17:57Z on 7 Nov to 07:28Z on 8 Nov, including the smoke and its restart. Series 4–10 took 8 h 57 min.
