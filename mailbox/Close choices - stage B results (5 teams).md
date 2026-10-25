# Close choices, stage B: five teams

Oct 25, 2026 · for Ümit and Can · rules: Method §9.9 (scoring), §9.10-9.11 (positions, v2 freeze), §9.12-9.13 (request and run conditions, scope change 16:05 UTC) in `tools/site/content/method-spec-2026-10-24.md`. Published on the site (Ümit, 2026-10-25).

**Scope.** Gemma 4 31B (on) was started but not completed: two reboots and a GPU fault interrupted it, and it was stopped after 311 of 500 play calls on 2026-10-25. Its partial data is not reported.

## Run

- Store: `smoke/close-choices-b.db` (`predictions`, `answers`); positions `positions/close-choices-b-v2.jsonl` (100, frozen v2).
- One run per team, `predict` then `ask --repeats 5 --once --retries 2`. No call was asked twice.
- Scoring: `python3 tools/site/close_choices_b_score.py smoke/close-choices-b.db positions/close-choices-b-v2.jsonl smoke/close-choices-b-score-5teams.json` (2026-10-25 ~13:40 UTC).

| Team | Predictions (UTC) | Play calls (UTC) | Cost at list price |
|---|---|---|---|
| Claude Opus 5.5 (on) | 10:23:57-10:26:28 | 10:29:44-10:45:14 | $2.54 + $13.88 |
| GPT-6 Astra (on) | 10:23:57-10:25:47 | 10:29:44-10:44:23 | $3.45 + $17.96 |
| GPT-6.1 Sol (high) | 10:24:02-10:29:42 | 10:29:45-11:02:29 | $0.92 + $4.72 |
| GPT-6.1 Sol (low) | 10:23:56-10:24:55 | 10:29:45-10:43:29 | $0.67 + $3.63 |
| Gemini 3.8 Flash (low) | 10:23:56-10:24:44 | 10:29:43-10:34:18 | $0.32 + $1.70 |

All 500 predictions and 2,500 play answers of these teams are valid (no error, none invalid); no position is excluded.

## Results

Per team, 100 scored positions. Primary: exact match of the predicted feature set P with the observed set O (features that differ between any of the five chosen plays). Secondary: overlap |P∩O|/|P∪O|. Baseline: the team's own predictions shuffled within phase, 1,000 seeded permutations; mean [2.5-97.5 %]; p = share of shuffles at least the observed mean.

| Team | Scored | Exact | Baseline | p | Overlap | Baseline | p | Same play ×5 | Play changed, features equal | O non-empty | Mean size of P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Opus 5.5 (on) | 100 | 0.34 | 0.275 [0.23, 0.32] | 0.004 | 0.402 | 0.315 [0.268, 0.365] | 0.000 | 71 | 10 | 19 | 1.19 |
| GPT-6 Astra (on) | 100 | 0.20 | 0.176 [0.15, 0.20] | 0.054 | 0.213 | 0.189 [0.160, 0.212] | 0.023 | 90 | 5 | 5 | 1.72 |
| GPT-6.1 Sol (high) | 100 | 0.20 | 0.139 [0.11, 0.17] | 0.000 | 0.223 | 0.163 [0.127, 0.193] | 0.000 | 80 | 10 | 10 | 1.64 |
| GPT-6.1 Sol (low) | 100 | 0.13 | 0.111 [0.08, 0.14] | 0.154 | 0.169 | 0.135 [0.102, 0.165] | 0.010 | 80 | 10 | 10 | 1.75 |
| Gemini 3.8 Flash (low) | 100 | 0.06 | 0.018 [0.01, 0.04] | 0.000 | 0.065 | 0.037 [0.024, 0.050] | 0.000 | 92 | 2 | 6 | 2.12 |

What it shows:
- Most positions have an empty O: the five answers chose the same play (71-92 of 100), or changed play without changing a feature. So most of the score comes from predicting "nothing" where the team does not hesitate.
- Claude Opus 5.5 (on) predicts the fewest features (1.19) and scores highest on both scores, above its shuffled baseline. GPT-6.1 Sol (high) and Gemini 3.8 Flash (low) are also above their baselines on both. GPT-6 Astra (on) and GPT-6.1 Sol (low) are not clearly above it on the exact score (p 0.054 and 0.154).
- Every team predicts hesitation far more often than it shows it (predicted feature shares are several times the observed ones; per-team detail in the JSON).
- The baseline is per team, so the teams are compared with themselves; the scores are not a ranking (Method §9.9).

Per-phase counts, the predicted and observed sets and the per-position P/O are in `smoke/close-choices-b-score-5teams.json` (local, not in git).

## Gemma 4 31B (on): stopped, not reported

100 predictions (10:40:53-11:33:04 UTC). Play calls: session 1 11:33:49-11:45:01 (cut by a reboot ~11:46), session 2 12:08:07-12:17:53 (cut by a reboot ~12:20), session 3 13:55:48-16:01:51 (after a GPU fault at 13:05 and a third reboot), stopped on purpose at 16:02:00 UTC (Ümit). 311 of 500 play answers stored (count only). Not scored; the 5-team score JSON's Gemma entry is ignored. Journal: `smoke/close-choices-b-gemma-session3.log`.
