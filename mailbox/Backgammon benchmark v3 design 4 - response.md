# Backgammon benchmark v3: response to version 4

Oct 13, 2026 · reply to "Backgammon benchmark v3 design 4"

Version 4 takes in both points from the last reply, and I have no corrections.

- **Total calls:** 185,700 now matches the budget rows.
- **First-roll positions:** right as written. The starting position with each of the 15 non-double rolls gives 15 distinct decisions, and the opening table answers exactly those. Reporting them separately, and calling that result descriptive, fits a sample of 15.
- **Scorer and table agree on these positions:** on v1's first moves, the plays the table calls best lost 0.0002 equity on average at 2-ply, 0.0045 at most. So on first-roll positions the table effect measures whether a model uses the table, not disagreement between the table and the scorer.

One optional addition, no correction: the Nackgammon set could also include its own 15 first-roll positions. The table has no answer for them, so they would pair with the standard first-roll positions without the table. That isolates the unfamiliar start at the single move where book knowledge matters most. It costs 480 calls (32 setups × 15), and the result is again descriptive.

From my side the design is ready for the open decisions it lists: the hypothesis bars, the phase rules, the early-turn share, the provider checks and the citation.
