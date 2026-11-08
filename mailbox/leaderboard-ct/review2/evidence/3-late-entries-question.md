# 3. Late entries in the leaderboard: open question for Ümit

Default: **not shown** (they are in no standings table). `story.LATE_ROWS = False`; set to True they appear as a separate grey group, **Late entries (not ranked)**, under the programs, one row per model by the same highest-setting rule over their own late-entry setups, never in the ranking; the name links to the late entry's page (Every decision does not hold late entries). Screenshots of that state: `review/screenshots/leaderboard-late-on-*.png` (a render of the same data with the constant set, not the candidate).

| Late entry | Model | Setting | Risk judgement |
|---|---|---|---|
| GPT-6 Astra (high) | GPT-6 Astra | high | 74.4 |
| SubQ Snap 1.1 | SubQ Snap 1.1 | — | 56.7 |
| Base Labs Elephant-1 | Base Labs Elephant-1 | — | 57.7 |
| Base Labs Mammoth-1 | Base Labs Mammoth-1 | — | 63.2 |
| Drex Max 1.1 | Drex Max 1.1 | — | 59.1 |
| Drex 2.0 | Drex 2.0 | — | 58.1 |
| Drex Max v1 | Drex Max v1 | — | 62.9 |
| Drex 2.0 (local) | Drex 2.0 | — | 53.0 |
| REAX 1.3 | REAX 1.3 | — | 60.5 |

What LATE_ROWS = True does, precisely: it **adds** a separate grey, unranked group under the programs; the ranked rows do not change. GPT-6 Astra keeps its ranked row at **medium** (League 3); its late entry GPT-6 Astra (high) appears only as an extra row in the late group. The open question for Ümit is therefore whether to show that extra group at all, not whether late entries change a model's ranked setting (they do not, in either state).
