# Heading asked for: "Thinking helps open models, not frontier ones"

Source: the live site's published data files (results f45081f6, data as of 2026-11-07T18:20Z): data/v3/league-1.json, league-2.json, league-3.json ("reasoning": every model with two reasoning settings in that league's games) and data/setups.json (weights). Read-only; every number below is copied from those files as printed.

Pairs: 9 (3 open weights, 6 closed). Error-rate reading as published on the Reasoning tab; risk-judgement change = higher setting minus lower; overlap of the two risk-judgement intervals as published.

| League | Model | Weights | Settings | Error rate, in league play | Risk judgement change | Intervals overlap |
|---|---|---|---|---|---:|---|
| 1 | LFM2.5-24B-A2B | open | off → on | lower error rate in league play | +6.7 | no |
| 2 | Claude Sonnet 5.5 | closed | low → high | no clear difference in league play | +4.7 | no |
| 2 | DeepSeek V4.1 Flash 1017 | open | off → low | lower error rate in league play | +10.0 | no |
| 2 | Gemini 3.8 Flash | closed | low → high | no clear difference in league play | +1.7 | yes |
| 2 | Gemma 4 31B | open | off → on | no clear difference in league play | +1.8 | yes |
| 3 | Claude Opus 5.5 | closed | low → high | no clear difference in league play | +3.0 | yes |
| 3 | GPT-6 Astra | closed | low → medium | no clear difference in league play | -1.1 | yes |
| 3 | GPT-6.1 Sol | closed | low → high | no clear difference in league play | -0.6 | yes |
| 3 | Gemini 4 Argon | closed | low → high | no clear difference in league play | +4.9 | yes |

Result: **not shown on the page**.
- Open weights: 2 of 3 read "lower error rate in league play" (LFM2.5-24B-A2B, DeepSeek V4.1 Flash 1017); Gemma 4 31B: no clear difference.
- Closed weights: 0 of 6 read lower error rate; in risk judgement, Claude Sonnet 5.5 has intervals that do not overlap.
- "Frontier" (League 3, the frontier chat models): all four pairs no clear difference.
- The pattern "open models gain, frontier ones do not" is in these rows only partly (one of three open models shows nothing; one closed non-frontier model moves in risk judgement), and the Reasoning tab itself says the comparison "is not paired and shows no effect of the setting: a higher or lower value at the higher setting is not evidence that reasoning caused it"; whether two intervals overlap "describes them; it is not a test of a difference" (Zeki #2578 likewise). A heading saying thinking helps (or does not help) would claim an effect the data cannot show. Dropped, as the brief allows ("reword or drop"); the Reasoning tab keeps the table.
