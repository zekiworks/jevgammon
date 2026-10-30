# Clear-risk follow-up: Part 2, asking the models (2026-10-30)

All 8 models are complete. Two or four plays are shown in each question; this is not league play. The page is labelled Preliminary: https://zekiworks.github.io/analysis/backgammon/clear-risk/.

## Summary

- **Items:** the 189 rollout-confirmed positions from check 1 (93 Risk wins, 96 Safety wins; 11 of the 200 were not confirmed). Each question is its own request with no shared context.
  - Q1: 189 items × 2 versions.
  - Q2: 60 items, board only.
  - Q3: 189 items × 2 versions.
  - Requests: 816 per chat model and 1,782 per decision model (Q3 is one question per value).
- **Models from the brief:** Celeris-1 Decision, Jev 1.14.0, Liquid d1-ultra, Claude Sonnet 5.5 (high), GPT-6.1 Sol (high).
- **Extra models, added 30 Oct (Zeki / Ümit), not in the original brief:**
  - Kimi K3.1 Pro (off) and GLM-5.3 (low), both via OpenRouter.
  - Claude Opus 5.5 (high), on the Claude subscription.
  - They use the same items, league settings and the frozen scoring.
  - The v3 setup names are "Claude Opus 5.5 (on)" and "GLM-5.3 (on)". This report uses the site's display names from labels.json.
- **Q1 with numbers:** every model leans to the safe play, with a bias of +54 to +92 percentage points.
  - In the Risk wins group, the three decision models pick the risky play only 4–19% of the time.
  - The chat models pick it 14–44% of the time.
- **Q1 board only:** without the numbers, the decision models and Kimi lean the other way (−14 to −25 pp). Sonnet (+42) and Opus (+46) stay safe-leaning. GLM is at +18 and Sol at +4.
- **Q2 (what the risky play does):** 62–100% right, against a 25% random baseline.
- **Q3 (matching values to plays):**
  - The decision models order 6–19% of pairs right. That is at or below their ~10% random baseline, and below it in the board-only version.
  - The chat models order 66–89% of pairs right (55% for Kimi board only), against a 50% baseline.
- **Risk wins cross-table:** most missed risks fall under "doesn't see the value" (Q3 pair wrong). "Doesn't know the game" is rare (0–11 items).

## Run and scoring

- **Scoring:** frozen. This is the `p2rep.py` scoring of the 06:25 report (`p2rep_062550.md`). Before any later model was added, the publish script checked that the earlier models' rows came out identical.
- **Temperature:** none was sent. All models used the provider default.
- **Decision models:** the answer is the top-probability option, and an exact tie at the top counts as no answer.
- **Run times (UTC, 30 Oct):**

  | model | first answer | last answer |
  |---|---|---|
  | Celeris, Jev, Liquid | 05:51 | 05:54 |
  | Sonnet | 05:54 | 06:15 |
  | Sol | 10:34 | 12:06 |
  | Kimi | 11:24 | 11:34 |
  | Opus | 11:24 | 11:46 |
  | GLM, first part | 11:24 | about 11:55 |
  | GLM, resumed | 14:18 | 14:32 |

- **GLM-5.3 (low) resume:**
  - The first part stopped at its $3.00 cap with 558 of 816 answers. It recorded $3.04, because the requests already in flight finished.
  - After Can's go it resumed with a $4.60 total cap and asked only the 258 missing items. None failed.
  - The old and new rows use the same route and settings (spec `openai-compatible/z-ai/glm-5.3`, provider `openrouter:fireworks`, reasoning `low`).
  - The harness commit recorded in the rows differs: 2c62337 for the old rows and 271ab96 for the new ones, and both have uncommitted changes. Those two commits changed only site and mailbox files. The runner code itself was the same uncommitted code in both runs.
- **Sol, 1 error row:**
  - Item `136:Q3:board` has a request error: "reading the response failed: error decoding response body" from the ChatGPT Codex endpoint, at 11:41:44Z.
  - It stays as stored. The rules allow no retries, so it counts as failed and is not in the usable answers.
- **Q3 random baselines (timing disclosure):**
  - The baselines were added after the first score output and were not pre-registered.
  - Timestamps: first score at 2026-10-30T06:25:29.387Z, baseline edit at 06:25:46.496Z, baseline output at 06:25:50.444Z.
  - Method: a simulation with seed 2026103005 and 200 draws per item, rounded to whole percent.
  - The scoring itself did not change.

## Cost

List-price and API-equivalent figures are kept apart from money billed.

| model | how it was paid | cost | kind |
|---|---|---:|---|
| Celeris-1 Decision, Jev 1.14.0, Liquid d1-ultra | hosted decision services | $0.19, $0.22, $0.18 (about $0.59) | list price; cash cap $3. Not checked against an invoice |
| Claude Sonnet 5.5 (high) | Claude subscription | $10.75 | API-equivalent, not money paid |
| Claude Opus 5.5 (high) | Claude subscription | $19.26 | API-equivalent, not money paid |
| GPT-6.1 Sol (high) | ChatGPT subscription | $8.53 | API-equivalent, not money paid |
| Kimi K3.1 Pro (off) | OpenRouter | $1.39 | billed: the cost OpenRouter reports per response |
| GLM-5.3 (low) | OpenRouter | $4.30 ($3.04 + $1.26 for the resume) | billed: the cost OpenRouter reports per response |

- **OpenRouter billed total:** $5.69, from the per-response costs.
- **Cross-check against the account balance:** during the GLM resume, the balance fell from $2.745 (14:18:14Z) to $1.589 (14:32:47Z), so $1.16. The answer rows record $1.26 for the resume. The balance poll ran every 30 s and its last reading came before the final answers, so the two do not match exactly.
- **No invoice checked:** none of these figures was checked against an invoice.
- **Cash-paid cost in the tables below:** the "API-equiv." label in the token table also covers Kimi and GLM. For those two, the figure is the OpenRouter-reported cost, which is what was paid.

## Checks requested on 30 Oct

### Scan sections between results 1082e024 and 656dc3d3

None of the scan sections changed between these results. I compared the analysis mirror commits d801893f0 (deploy 1) and 267b4b616 (deploy 2).

- **`data/v3/clear-risk.json`:** these sections are deep-equal in both commits:
  - `clear-risk-scan` (with the step 2–4 counts)
  - `clear-risk-setups` (per-setup missed / needless / bias)
  - `clear-risk-checks` (checks 2–4)
  - `clear-risk-rollouts`

  Only these changed:
  - `clear-risk-part2`
  - `pending`
  - the new key `scan_as_of`
- **`clear-risk/index.html`:** the same four sections are byte-identical. Only these changed:
  - the hero intro
  - `clear-risk-status` (the as-of note and the pending line)
  - `clear-risk-part2`
  - the "Results … updated" footer line (1082e024 at 10:05 → 656dc3d3 at 12:10)

### Q2: what the right answers are

- **Items:** all 60 Q2 items are board only. Each shows 4 options. "None of these" is never right and is not shown, because only items where exactly one option is true of play B and not of play A were asked.
- **Right answer per item:**
  - moves a checker out of the opponent's home board: 26
  - hits a checker: 25
  - makes a new point: 6
  - makes your longest prime longer: 3
- **So the right answer is not always about hitting.** "Hits" is right in 25 of 60.
- **Three examples** (options in the order shown; safe play A | unsafe play B):
  - **Position 7 (Risk wins), 13/11 13/7 | 24/18 18/16:** makes a new point / hits a checker / moves a checker out of the opponent's home board / makes your longest prime longer. Right: **moves a checker out of the opponent's home board**.
  - **Position 10 (Risk wins), 13/8 8/6 | 6/1\* 24/22:** hits a checker / makes your longest prime longer / moves a checker out of the opponent's home board / makes a new point. Right: **hits a checker**.
  - **Position 12 (Risk wins), 6/5 6/2 | 5/4\* 4/off:** moves a checker out of the opponent's home board / makes a new point / hits a checker / makes your longest prime longer. Right: **hits a checker**.

## Results (frozen scoring; every model complete)

## Q1: share right per group, missed and needless, bias (two plays shown, not league play)

| model | version | Risk wins right | Safety wins right | missed (Risk wins → safe) | needless (Safety wins → unsafe) | bias | league: missed · needless · bias (all legal plays) | share of A answers | Q1 not answered |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| Celeris-1 Decision | with numbers | 6% (6/93) | 98% (94/96) | 94% (87/93) | 2% (2/96) | +91 pp | 82% (137/168) · 1% (4/408) · +81 pp | 47% (88/189) | 0 |
| Celeris-1 Decision | board only | 75% (69/92) | 61% (57/93) | 25% (23/92) | 39% (36/93) | -14 pp |  | 48% (88/185) | 4 |
| Jev 1.14.0 | with numbers | 4% (4/91) | 97% (93/96) | 96% (87/91) | 3% (3/96) | +92 pp | 74% (139/187) · 3% (10/347) · +71 pp | 50% (94/187) | 2 |
| Jev 1.14.0 | board only | 67% (62/93) | 45% (41/92) | 33% (31/93) | 55% (51/92) | -22 pp |  | 47% (87/185) | 4 |
| Liquid d1-ultra | with numbers | 19% (18/93) | 94% (90/96) | 81% (75/93) | 6% (6/96) | +74 pp | 49% (84/171) · 4% (18/414) · +45 pp | 51% (96/189) | 0 |
| Liquid d1-ultra | board only | 68% (63/93) | 47% (41/87) | 32% (30/93) | 53% (46/87) | -21 pp |  | 62% (112/180) | 9 |
| Claude Sonnet 5.5 (high) | with numbers | 32% (30/93) | 98% (94/96) | 68% (63/93) | 2% (2/96) | +66 pp | 53% (103/194) · 0% (2/428) · +53 pp | 50% (94/189) | 0 |
| Claude Sonnet 5.5 (high) | board only | 52% (48/93) | 94% (90/96) | 48% (45/93) | 6% (6/96) | +42 pp |  | 54% (102/189) | 0 |
| GPT-6.1 Sol (high) | with numbers | 44% (41/93) | 98% (94/96) | 56% (52/93) | 2% (2/96) | +54 pp | 32% (28/88) · 2% (6/334) · +30 pp | 50% (95/189) | 0 |
| GPT-6.1 Sol (high) | board only | 77% (72/93) | 81% (78/96) | 23% (21/93) | 19% (18/96) | +4 pp |  | 46% (86/189) | 0 |
| Kimi K3.1 Pro (off) | with numbers | 24% (22/93) | 94% (90/96) | 76% (71/93) | 6% (6/96) | +70 pp | 46% (39/85) · 2% (5/225) · +44 pp | 49% (92/189) | 0 |
| Kimi K3.1 Pro (off) | board only | 70% (65/93) | 45% (43/96) | 30% (28/93) | 55% (53/96) | -25 pp |  | 65% (122/189) | 0 |
| GLM-5.3 (low) | with numbers | 14% (13/93) | 92% (88/96) | 86% (80/93) | 8% (8/96) | +78 pp | 74% (142/193) · 0% (1/365) · +73 pp | 59% (111/189) | 0 |
| GLM-5.3 (low) | board only | 51% (47/93) | 69% (66/96) | 49% (46/93) | 31% (30/96) | +18 pp |  | 65% (123/189) | 0 |
| Claude Opus 5.5 (high) | with numbers | 40% (37/93) | 96% (92/96) | 60% (56/93) | 4% (4/96) | +56 pp | 49% (57/117) · 2% (4/260) · +47 pp | 48% (91/189) | 0 |
| Claude Opus 5.5 (high) | board only | 49% (46/93) | 96% (92/96) | 51% (47/93) | 4% (4/96) | +46 pp |  | 48% (90/189) | 0 |

## Q2 (board only): share right vs random

| model | right | random baseline |
|---|---:|---:|
| Celeris-1 Decision | 92% (55/60) | 25% (4 options, one right) |
| Jev 1.14.0 | 62% (37/60) | 25% (4 options, one right) |
| Liquid d1-ultra | 92% (55/60) | 25% (4 options, one right) |
| Claude Sonnet 5.5 (high) | 100% (60/60) | 25% (4 options, one right) |
| GPT-6.1 Sol (high) | 100% (60/60) | 25% (4 options, one right) |
| Kimi K3.1 Pro (off) | 92% (55/60) | 25% (4 options, one right) |
| GLM-5.3 (low) | 95% (57/60) | 25% (4 options, one right) |
| Claude Opus 5.5 (high) | 100% (60/60) | 25% (4 options, one right) |

## Q3: share of pairs in the right order (pairs ≥ 0.04 apart at 3-ply)

| model | version | all pairs | safe-vs-unsafe pair |
|---|---|---:|---:|
| Celeris-1 Decision | with numbers | 10% (87/834) | 10% (18/189) |
| Celeris-1 Decision | board only | 6% (46/834) | 5% (10/189) |
| Jev 1.14.0 | with numbers | 17% (138/834) | 17% (32/189) |
| Jev 1.14.0 | board only | 7% (59/834) | 11% (21/189) |
| Liquid d1-ultra | with numbers | 19% (157/834) | 17% (33/189) |
| Liquid d1-ultra | board only | 6% (49/834) | 5% (9/189) |
| Claude Sonnet 5.5 (high) | with numbers | 81% (674/834) | 62% (118/189) |
| Claude Sonnet 5.5 (high) | board only | 82% (682/834) | 68% (129/189) |
| GPT-6.1 Sol (high) | with numbers | 89% (742/834) | 72% (137/189) |
| GPT-6.1 Sol (high) | board only | 88% (736/834) | 79% (150/189) |
| Kimi K3.1 Pro (off) | with numbers | 75% (622/834) | 55% (104/189) |
| Kimi K3.1 Pro (off) | board only | 55% (458/834) | 54% (103/189) |
| GLM-5.3 (low) | with numbers | 73% (610/834) | 55% (104/189) |
| GLM-5.3 (low) | board only | 66% (552/834) | 53% (100/189) |
| Claude Opus 5.5 (high) | with numbers | 82% (681/834) | 63% (120/189) |
| Claude Opus 5.5 (high) | board only | 83% (691/834) | 70% (132/189) |
| *random one-to-one mapping (chat-style)* | | 50% | 50% |
| *random play per value, independently (decision-style)* | | 10% | 11% |

## Risk wins cross-table (counts)

| model | version | Risk wins with a safe-vs-unsafe Q3 pair | sees the value, plays safe (Q3 pair right, Q1 safe) | sees the value, takes the risk (Q3 right, Q1 unsafe) | doesn't see the value (Q3 pair wrong) | doesn't know the game (Q2 and Q3 wrong; of Q3-wrong items with a Q2 item) |
|---|---|---:|---:|---:|---:|---:|
| Celeris-1 Decision | with numbers | 93 | 2 | 0 | 91 | 1 of 38 |
| Celeris-1 Decision | board only | 93 | 1 | 2 | 90 | 1 of 37 |
| Jev 1.14.0 | with numbers | 93 | 1 | 0 | 91 | 11 of 36 |
| Jev 1.14.0 | board only | 93 | 5 | 8 | 80 | 10 of 30 |
| Liquid d1-ultra | with numbers | 93 | 0 | 0 | 93 | 1 of 38 |
| Liquid d1-ultra | board only | 93 | 0 | 4 | 89 | 1 of 36 |
| Claude Sonnet 5.5 (high) | with numbers | 93 | 6 | 17 | 70 | 0 of 26 |
| Claude Sonnet 5.5 (high) | board only | 93 | 6 | 36 | 51 | 0 of 17 |
| GPT-6.1 Sol (high) | with numbers | 93 | 16 | 30 | 47 | 0 of 19 |
| GPT-6.1 Sol (high) | board only | 93 | 12 | 57 | 24 | 0 of 15 |
| Kimi K3.1 Pro (off) | with numbers | 93 | 10 | 9 | 74 | 0 of 31 |
| Kimi K3.1 Pro (off) | board only | 93 | 14 | 49 | 30 | 0 of 14 |
| GLM-5.3 (low) | with numbers | 93 | 7 | 6 | 80 | 1 of 31 |
| GLM-5.3 (low) | board only | 93 | 10 | 24 | 59 | 1 of 21 |
| Claude Opus 5.5 (high) | with numbers | 93 | 4 | 22 | 67 | 0 of 24 |
| Claude Opus 5.5 (high) | board only | 93 | 7 | 33 | 53 | 0 of 18 |

## Answers, failures, tokens

| model | answers stored | failed requests | invalid / no answer | exact ties at the top (decision) | input tokens | output tokens | reasoning tokens | cost |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Celeris-1 Decision | 1782 | 0 | Q3 two values on one play (pairs) 333 | 26 | 4,759,594 | 0 | 0 | $0.19 |
| Jev 1.14.0 | 1782 | 0 | Q3 two values on one play (pairs) 315 | 41 | 5,186,004 | 140,677 | 0 | $0.22 |
| Liquid d1-ultra | 1782 | 0 | Q3 two values on one play (pairs) 287 | 99 | 4,364,915 | 0 | 0 | $0.18 |
| Claude Sonnet 5.5 (high) | 816 | 0 | 0 | 0 | 2,845,140 | 506,104 | 492,088 | $10.75 API-equiv. |
| GPT-6.1 Sol (high) | 816 | 1 | failed or missing 1 | 0 | 2,027,910 | 447,317 | 429,686 | $8.53 API-equiv. |
| Kimi K3.1 Pro (off) | 816 | 0 | 0 | 0 | 2,091,754 | 16,300 | 0 | $1.39 API-equiv. |
| GLM-5.3 (low) | 816 | 0 | invalid 7 | 0 | 1,990,210 | 787,791 | 607,727 | $4.30 API-equiv. |
| Claude Opus 5.5 (high) | 816 | 0 | 0 | 0 | 2,845,140 | 393,825 | 379,806 | $19.26 API-equiv. |
