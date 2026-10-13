# Backgammon benchmark v3: response to version 8

Oct 13, 2026 · reply to "Backgammon benchmark v3 design 8"

Version 8 takes in every point from the last reply, and its figures check out: 12 League 1 setups × 4,000 = 48,000, 233,700 in total, 43% more. I ran three more checks on v1 data. The League 1 extension is larger than it needs to be, H3 in League 2 will almost certainly come out inconclusive, and positions should be spread across games.

## H2 and H5: 6,000 positions is more than enough

Power on 6,000 paired positions, using v1 spreads for League 1-type pairs (per-position spread of 53 to 63 PR points):

| True gain | Power at 6,000 positions | At 4,000 |
| --- | --- | --- |
| 3 points | 96% to 99% | about 90% |
| 2 points | 69% to 83% | lower |

"Sized for a 3-point gain" holds with room to spare. An extension of 2,000 positions instead of 4,000 (4,000 in total) still gives about 90% power for 3 points and saves 24,000 calls. Either is defensible, since most of these calls run on our GPUs. If you keep 4,000, say that the sample can also resolve gains of about 2 points.

## H3 in League 2: equivalence within ±3 is very unlikely to pass

The v1 pairs closest to League 2's comparison, best closed workhorse against best open model, have wide intervals at 2,000 positions:

| Pair | Half-width at 2,000 | Passes ±3 only if the observed difference is under |
| --- | --- | --- |
| Gemini 3.8 Flash vs DeepSeek V4.1 Flash | ±2.56 | 0.44 |
| Gemini 3.8 Flash vs Qwen3.8 Flash Next | ±2.68 | 0.32 |

(DeepSeek and Qwen here are reasoning off.)

So H3 in League 2 passes only if the two models are almost exactly equal. Otherwise it will read "not shown", even when they are close. League 3's frontier pairs (about ±1.3) are fine. Options:

1. **Widen League 2's margin to ±4,** matching the design's own rule that 4 points is the meaningful difference for open models.
2. **Extend League 2's shared positions,** at a cost: these setups run on paid providers and subscriptions.
3. **Keep ±3 and state in advance** that League 2 is expected to be inconclusive.

Related: H3's ±3 sits between the tier rules (2 for closed, 4 for open). Say why it is 3, or set it per league.

## Draw positions from many games

Positions from the same game are not independent, but the intervals resample single positions. On v1 this matters little: the 1,000 shared positions come from 396 games, 2.5 on average and at most 9 per game. My power figures above and in the last reply assume independent positions, so they are slightly optimistic.

For the new GNUbg self-play sets (the new set, the extension, Nackgammon), games are cheap. Take at most one or two positions per game per phase, and log the game each position came from. Then either resampling positions is close to correct, or the intervals can resample by game. Add this to the sampling rules.
