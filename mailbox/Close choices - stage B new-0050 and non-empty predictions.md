# Close choices – stage B: new-0050 and non-empty predictions

[ZEKI-BG-MAILBOX-1564075421648293960]

Source: `smoke/close-choices-b.db` (opened read-only), prompt version bg-v2, position set `new`,
and the score file `close-choices-b-score-5teams.json` (copied unchanged into this mailbox).
The five published teams only. Gemma 4 31B's partial data is left out (scope rule).

## Positions with a non-empty predicted feature set

The prediction call returns a set of features (hitting, points, race, prime). An empty set `[]` is a valid "none" answer.
No prediction was invalid or failed for these five teams.

| Team | Non-empty predicted set | Denominator | "none" |
|---|---:|---:|---:|
| Claude Opus 5.5 (on) | 70 | 100 | 30 |
| GPT-6 Astra (on) | 82 | 100 | 18 |
| GPT-6.1 Sol (high) | 86 | 100 | 14 |
| GPT-6.1 Sol (low) | 89 | 100 | 11 |
| Gemini 3.8 Flash (low) | 99 | 100 | 1 |

The "none" counts match the `predicted_sets.none` values in the score file.

## Position new-0050

It is in the frozen 100: `freeze/close-choices-b-v2.json`, `selected` → `safety/opening`
(class "Safety pays", opening phase). It has 11 legal plays.

| Team | Predicted feature set | 5 chosen plays (repeats 1–5) |
|---|---|---|
| Claude Opus 5.5 (on) | hitting, points | 13/7 8/7 ×5 |
| GPT-6 Astra (on) | none `[]` | 13/7 8/7 ×5 |
| GPT-6.1 Sol (high) | none `[]` | 13/7 8/7 ×5 |
| GPT-6.1 Sol (low) | none `[]` | 13/7 8/7 ×5 |
| Gemini 3.8 Flash (low) | hitting, points, prime | 13/7 8/7 ×5 |

Every team chose the same play, 13/7 8/7, all 25 times. The teams differ only in the predicted set.
