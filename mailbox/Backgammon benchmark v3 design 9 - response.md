# Backgammon benchmark v3: response to version 9

Oct 13, 2026 · reply to "Backgammon benchmark v3 design 9"

Version 9 settles every point from the last reply, and the reasons are sound:

- **H3 as non-inferiority:** with League 2's margin of 4 and a half-width of about ±2.6, it passes when the open model is within about 1.4 points of the closed one. It can now succeed in practice.
- **Keeping the 4,000-position extension:** H5's selectors are scored on held-out halves of 3,000 positions each, so the extra positions earn their place.
- **One position per game and phase, and resampling by source game:** that fixes the independence problem.

One point remains.

## H3 picks its "best" setups from the same positions it tests

"Best open" and "best closed" are chosen by error rate on the same positions that then test the difference. The best of several setups looks better than it is, because it was partly lucky on those positions. The more setups it is chosen from, the larger that bias:

- **League 2:** best of 6 closed setups against best of 6 open setups. Roughly balanced.
- **League 3:** best of 6 closed setups (Astra, Opus, Argon, each low and high) against best of 2 open setups (DeepSeek V4 Pro off and on). The closed side gets the larger lucky boost, which biases H3 against the open model.

Either fix works:

1. **Choose the best setups on one half of the positions and test on the other**, as A6 and A7 already do. This costs power, but League 3's frontier pairs have room (about ±1.3 at 2,000 positions, about ±1.8 at 1,000).
2. **Name the compared setups before the freeze**, for example each model's highest reasoning setting. Then the "best" setups are fixed in advance.

I would take option 2: it is simpler and keeps all positions for the test.
