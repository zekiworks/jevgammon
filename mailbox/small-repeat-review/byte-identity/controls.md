# Negative controls: the stub detects a changed request

The same replay (repeat mode, runner 6578a73) with one entrant setting changed (`REPLAY_MUTATE`), bounded at 90 s
(`REPLAY_LEAGUE_TIMEOUT`; refused requests back off for minutes). Each summary is in the folder of the same name.

| Control | Entrant requests identical | Received | Received but not stored (answered 400) | Pairs finished |
|---|---|---|---|---|
| MiniCPM5-2B (off), `top_logprobs` 19 instead of 20 | 0 of 1,300 | 13 | 13 | 0 |
| GLiDE 2B as provider `glide-0.4b` (the same request format, but groups of at most 74 options) | 46 of 820 | 47 | 1 (a 68-option group: the first list longer than 74 options, split) | 0 |

So a one-field difference in the chat request is never matched, and a decision request differs exactly where the
request would differ (the 46 decisions before the first long option list still match).
