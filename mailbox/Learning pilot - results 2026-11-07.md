# Learning pilot: results (run 7–8 Nov 2026)

**Results will be published whichever way they go, including no lift.**

One model: Gemma 4 31B (reasoning off, our GPUs) · opponent: GNUbg weak · 4 kinds of memory (one of them is no memory) · 10 series of 10 games each.

The plan for this run is `mailbox/Learning pilot - plan 2026-11-07.md` (sha256 `1e9bc932…e8f6`, commits 5af8842 → 7719e1a), and it was all committed before the first model call. Four arms were run: no memory (control), full records (records), own lessons (lessons) and budget (empty: no game fit) (budget). Each ran 10 series of 10 games against GNU Backgammon Beginner, and the 200-position evaluation set was asked once before game 1 (shared by all arms), then again after games 5 and 10.

- **Model and settings:** Gemma 4 31B (off), with League 2's settings, served by spark3.
- **Lesson prompt sha256:** `d7550015…550e`.
- **Evaluation set sha256:** `6c92e741…18e6`.
- **Harness:** branch `learning-pilot` at ba8b011 for the first smoke start, then e18ff59.
- **Cost:** $0 in API fees. The cost of local compute is not estimated.
- **Content:** this file holds aggregates only. It has no positions, no per-position answers and no lesson text.

## Verdict

**No arm reached the pre-registered signal threshold (plan §8).** The rule requires two things, each averaged over the arm's 10 series:
- risks found after game 10 minus before game 1 is at least +10 points;
- right safety after game 10 minus before game 1 is at least −5 points.

| Arm | Risks found change | Right safety change | Rule met? |
|---|---|---|---|
| own lessons | +8.3 pp (95% CI 7.1–9.4) | +1.1 pp | no: risks found falls short of 10 |
| full records | +3.3 pp | +1.3 pp | no |
| budget (empty: no game fit) | +2.8 pp | +0.8 pp | no |

Right safety held up in every arm.

**A17 learning lift: all observed game-lift differences are below control.** The lift is the error rate in games 1–3 minus games 8–10, compared with control's lift and paired by series. All three arms come out at −2.0 to −3.9 PR relative to control. For records and lessons the intervals include zero. This is not a finding of "no effect"; it is what was observed in this pilot.

The budget arm's interval does not include zero, although budget and control had the same memory policy (an empty context) and the same dice seeds (caveat 2). The source of this unexpected difference and the calibration of the intervals were not determined in this pilot.

## Evaluation set (200 positions: 100 Risk wins, 100 Safety wins), by arm and checkpoint

| Arm | Evaluation | Series | Error rate (PR) | Risk judgement | Risks found % | Right safety % | Risk appetite % | Invalid | Failed | Input tokens / decision | Records dropped (games) | Request time (h) | Median request (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all arms (shared) | T0 | 1 run | 55.6 | 60.5 | 25.0 | 96.0 | 18.0 | 0 | 0 | 4853 | 0 | 0.29 | 3.72 |
| full records | T5 | 10 | 53.0 | 62.5 | 28.8 | 96.2 | 20.1 | 0 | 0 | 27374 | 0 | 3.06 | 3.75 |
| full records | T10 | 10 | 53.1 | 62.8 | 28.3 | 97.3 | 19.4 | 0 | 0 | 39323 | 23 | 4.10 | 4.87 |
| own lessons | T5 | 10 | 46.1 | 65.5 | 34.6 | 96.3 | 21.7 | 0 | 0 | 5744 | 0 | 2.93 | 3.66 |
| own lessons | T10 | 10 | 46.4 | 65.2 | 33.3 | 97.1 | 20.4 | 0 | 0 | 6600 | 0 | 2.50 | 2.98 |
| budget (empty: no game fit) | T5 | 10 | 54.0 | 62.8 | 28.7 | 96.8 | 18.9 | 0 | 0 | 4853 | 50 | 2.57 | 3.12 |
| budget (empty: no game fit) | T10 | 10 | 54.7 | 62.3 | 27.8 | 96.8 | 18.6 | 0 | 0 | 4853 | 100 | 2.09 | 2.53 |

How to read the table:

- **Metric values** are means over series. The definitions are the site's: PR = 500 × mean 2-ply equity loss; risk judgement = 50 × (right risks ÷ Risk pays + right safety ÷ Safety pays). Plan §7 has the rest.
- **Control** has no T5 or T10 evaluation, because its context is always empty; its evaluation is T0.
- **Input tokens per decision** sums over the requests in a decision. Positions with more than 26 options are asked in groups.
- **Records dropped** counts whole earlier games left out of the context, summed over 10 series. For records, games are dropped once the context passes the limit. For budget, they are dropped once the context passes the lessons arm's token count.

## Signal rule (plan §8): T10 − T0, mean over 10 series, 95% bootstrap over whole series

| Arm | Risks found change (pp) [95% CI] | Right safety change (pp) [95% CI] | Rule met (≥ +10 and ≥ −5) |
|---|---:|---:|---|
| full records | +3.3 [2.6, 4.1] | +1.3 [0.8, 1.8] | no |
| own lessons | +8.3 [7.1, 9.4] | +1.1 [0.6, 1.6] | no |
| budget (empty: no game fit) | +2.8 [1.7, 3.7] | +0.8 [0.4, 1.0] | no |

## Games against GNU Backgammon Beginner (100 games per arm)

| Arm | Series | Games | Decisions | Invalid | Error rate (PR) | Wins | Input tokens / decision | Median decision latency (s) | Records dropped (games, summed) | Context-limit drop steps | Empty budget points |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| no memory | 10 | 100 | 2392 | 0 | 28.8 | 52 | 4355 | 3.62 | – | 0 | – |
| full records | 10 | 100 | 2283 | 0 | 29.7 | 52 | 22848 | 3.22 | 23 | 40 | – |
| own lessons | 10 | 100 | 2425 | 0 | 27.4 | 47 | 5115 | 3.74 | – | 0 | – |
| budget (empty: no game fit) | 10 | 100 | 2383 | 0 | 29.7 | 52 | 4344 | 3.23 | 100 | 0 | 100 |

## A17 learning lift: error rate in games 1–3 minus games 8–10 (positive = better later), paired by series, 95% bootstrap over whole series

| Arm | Lift (PR) [95% CI] | Lift − control's lift (PR) [95% CI] |
|---|---:|---:|
| no memory | +0.48 [−6.55, 6.10] | – |
| full records | −1.49 [−7.47, 5.33] | −1.98 [−8.71, 5.22] |
| own lessons | −3.37 [−7.88, 1.52] | −3.85 [−11.09, 3.93] |
| budget (empty: no game fit) | −2.57 [−9.09, 3.11] | −3.05 [−4.92, −1.18] |

Secondary comparison (records vs lessons vs budget, descriptive): on the evaluation set, lessons moved most from T0. Its error rate fell 9.2 PR and risks found rose 8.3 pp at T10. Records and budget moved about a third as much. How much of each change comes from the batch change between T0 and the later evaluations was not measured (caveat 2). In the games, every observed lift difference against control is below zero.

## Exploratory, after the results (not part of the pre-registered verdict)

Added on 8 Nov 2026 at Ümit's request (bus #2950, #2952), with Zeki's wording rules (#2929, #2964). Everything above this section, including the verdict, is unchanged. Nothing in this section was pre-registered.

### 1. Own lessons − budget and full records − budget (budget: empty, no game fit), paired by series

The budget arm's context was empty at every point, so its T5 and T10 evaluations are empty-context retests of the T0 prompts. That makes budget the noise baseline for the evaluation set.

- **Pairing:** two comparisons, own lessons − budget and full records − budget: the arm's value minus budget's value at the same checkpoint, within the same series id (same dice seed; the games differ once plays differ).
- **Summary:** mean over the 10 series.
- **Intervals:** 95% percentile bootstrap over whole series, the pilot's own (10,000 resamples). The calibration of these intervals was not determined.

| Comparison | Checkpoint | Risks found (pp) [95% CI] | Right safety (pp) [95% CI] | Error rate (PR) [95% CI] | Risk judgement [95% CI] |
|---|---|---:|---:|---:|---:|
| full records − budget | T5 | +0.1 [-1.6, 1.7] | -0.6 [-1.1, -0.1] | -1.03 [-2.33, 0.36] | -0.25 [-1.25, 0.70] |
| full records − budget | T10 | +0.5 [-0.5, 1.5] | +0.5 [-0.1, 1.1] | -1.61 [-2.42, -0.73] | +0.50 [-0.20, 1.25] |
| own lessons − budget | T5 | +5.9 [4.5, 7.2] | -0.5 [-0.9, -0.1] | -7.89 [-8.70, -7.08] | +2.70 [2.15, 3.20] |
| own lessons − budget | T10 | +5.5 [3.7, 7.3] | +0.3 [-0.2, 0.8] | -8.29 [-9.03, -7.44] | +2.90 [1.85, 3.90] |

### 2. Five more empty-context runs of the evaluation set

The 200-position evaluation was run 5 more times with exactly the T0 prompts and settings: the same config file and option order, 4 requests in flight as at T0.

- **When and where:** 8 Nov 2026, 10:35–10:56 UTC, on the same spark3 server.
- **Calls:** 1,000 answers (1,385 requests). All valid, 0 failed, 0 invalid.
- **Storage:** a separate private store. The pilot's files and hashes are untouched.

The 20 budget evaluations ran with 1 request in flight, during the pilot.

| Empty-context run | Requests in flight | Risks found % | Right safety % | Error rate (PR) | Risk judgement | Risk appetite % | Answered / valid |
|---|---:|---:|---:|---:|---:|---:|---:|
| T0 (shared) | 4 | 25.0 | 96.0 | 55.6 | 60.5 | 18.0 | 200 / 200 |
| retest r1 | 4 | 28.0 | 97.0 | 54.7 | 62.5 | 18.5 | 200 / 200 |
| retest r2 | 4 | 28.0 | 97.0 | 54.7 | 62.5 | 19.0 | 200 / 200 |
| retest r3 | 4 | 28.0 | 97.0 | 54.7 | 62.5 | 18.5 | 200 / 200 |
| retest r4 | 4 | 28.0 | 97.0 | 54.4 | 62.5 | 19.0 | 200 / 200 |
| retest r5 | 4 | 28.0 | 97.0 | 54.7 | 62.5 | 19.0 | 200 / 200 |

| Spread (min–max, SD) | n | Risks found % | Right safety % | Error rate (PR) | Risk judgement |
|---|---:|---:|---:|---:|---:|
| 5 retests only (r1–r5) | 5 | 28.0–28.0 (SD 0.00) | 97.0–97.0 (SD 0.00) | 54.4–54.7 (SD 0.11) | 62.5–62.5 (SD 0.00) |
| T0 + 5 retests | 6 | 25.0–28.0 (SD 1.22) | 96.0–97.0 (SD 0.41) | 54.4–55.6 (SD 0.39) | 60.5–62.5 (SD 0.82) |
| 20 budget evaluations (T5, T10) | 20 | 24.0–30.0 (SD 1.41) | 95.0–97.0 (SD 0.52) | 52.5–56.9 (SD 0.85) | 59.5–63.5 (SD 0.85) |
| all 26 empty-context runs | 26 | 24.0–30.0 (SD 1.38) | 95.0–97.0 (SD 0.49) | 52.5–56.9 (SD 0.78) | 59.5–63.5 (SD 0.84) |

| Answer agreement: positions (of 200) where two runs chose different plays | Pairs | Mean | Min–max |
|---|---:|---:|---:|
| T0 vs retests | 5 | 9.0 | 8–11 |
| retest vs retest | 10 | 1.4 | 0–3 |
| T0 vs budget | 20 | 9.2 | 7–12 |
| retests vs budget | 100 | 5.0 | 1–14 |
| budget vs budget | 190 | 6.0 | 0–14 |

**Every retest gave the same risks found and right safety, 28.0% and 97.0%.** The retests also chose the same plays almost everywhere: only 3 of the 200 positions were not unanimous across the five. These agreement counts come from the private per-position answers; only their totals are published. T0 differs from every later empty-context run, on 8–11 positions against the retests and 7–12 against the budget evaluations. T0 differs from the later empty-context runs; the cause was not verified.

Read descriptively, about +3 pp of every arm's risks-found change from T0 (section "Signal rule") also appears with no memory at all. The signal rule and its verdict are as pre-registered and stay unchanged.

### 3. Settings of the evaluation calls

Taken from the request code (`src/players/llm.rs`, prefill readout with reasoning off) and a stored T0 request.

**Sent, per request:**
- temperature 1.0;
- max_tokens 1;
- logprobs true, top_logprobs 20;
- the assistant turn prefilled with `Answer:`, with continue_final_message (add_generation_prompt false);
- chat_template_kwargs.enable_thinking false;
- no top_p, top_k or seed sent.

**Server's effective defaults (read-only check of spark3):**
- The vLLM log states: "Default vLLM sampling parameters have been overridden by the model's `generation_config.json`: {'temperature': 1.0, 'top_k': 64, 'top_p': 0.95}".
- That file is identical on spark3 and in our copy of the model.
- No seed was sent. The server's seed behaviour was not checked.

**How the answer is chosen:**
- The play is the argmax of the returned option-letter probabilities; several tokens per letter are summed (`src/players/prompt.rs`). The cause of differences between empty-context runs was not verified.
- Positions with more than 26 options (32 of the 200) are asked in groups, then among the group winners. Each request is read the same way.
- **What was checked in the stored records** (T0, the 5 retests, the 20 budget evaluations):
  - all 5,200 answers have probability source `logprobs`;
  - all 7,202 requests are the prefill readout (max_tokens 1, continue_final_message);
  - none carries `response_format`, so the constrained-letter fallback (`src/players/llm.rs`) never fired;
  - no request recorded an error.
- Whether vLLM returned raw or processed logprobs (before or after temperature, top_k and top_p) cannot be shown from the stored records; it was not determined.
- The retests measure variability; they do not establish its cause. Server-side numerical variation (batching, fp8) is a hypothesis only.

### 4. Next version (not run)

Budget-match the records at the decision level: the most recent decisions, with GNU Backgammon's verdicts, that fit within the lessons arm's token count at the same point. Under the whole-game rule used here, no game ever fit.

## Caveats

1. **Small and narrow.** There are 10 series per arm, one model (Gemma 4 31B with reasoning off), one opponent (GNU Backgammon Beginner) and a single run. All numbers here are descriptive and outside the Holm correction.
2. **The budget arm never received records.** Its context was empty at all 100 of 100 points, because no whole game record ever fit within the lessons arm's token count. The plan's fixed reading (§11) applies: **"with this budget, record memory could not be provided"**, not "record memory didn't help". So in the games budget had the same memory policy as control, and in the evaluations it repeated the T0 prompts:
   - **In the games**, budget and control had the same memory policy (an empty context) and the same dice seeds. That does not make their realized game prompts the same: once a play differs, the games diverge. The interval on budget's lift minus control's lift excludes zero (−3.05 [−4.92, −1.18]). One hypothesis is server-side numerical non-determinism (requests batched differently, fp8 on vLLM) starting the divergence; it was not tested, and no controlled decomposition was done. The source of this unexpected difference and the calibration of the intervals were not determined in this pilot.
   - **In the evaluations**, budget's T5 and T10 requests are identical to the T0 requests. Its change from T0 (+2.8 pp risks found, +0.8 pp right safety, −0.9 PR) is therefore the difference between repeated runs of the same prompts and the single shared T0 run. T0 ran with 4 requests in flight, the later evaluations with 1; how much this batch change contributes to each arm's difference from T0 was not measured. **Exploratory, not pre-registered:** taken against budget rather than against T0, lessons is about +5.5 pp risks found and records about +0.5 pp.
3. **T0 is one run.** The signal rule compares each arm's T10 mean, taken over 10 series, with a single shared T0 run. T0's own uncertainty is not in the bootstrap, so the T10 − T0 intervals are conditional on the one observed T0. This applies to the signal-rule intervals only; the game-lift intervals do not use T0.
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
