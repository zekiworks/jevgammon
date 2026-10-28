# Nackgammon paired test — exploratory: GPT-6.1 Sol (low) vs (high), standard positions (2026-10-28)

**Exploratory.** This is not one of the frozen primary comparisons. Primary comparison 5 is already Sol (high) against Sol (low) on the *Nackgammon drop*. This note compares the two setups' *level* on the standard side only. No model was called. The frozen results (`positions/nack-paired/results/results.json`) were not rerun or changed.

**Data.** `smoke/nack-paired.db` (read-only), answers with `repeat = 1`. The positions are the 500 frozen standard positions (`nps-*`) of the pairs: 200 main and 300 reserve. Both setups answered every one of the 500 with no error, so n = 500 (main: 200). The two setups chose the same play on 440 of 500 positions (170 of 200 main).

**Rules.** I used the scorer's own functions from `tools/v3/nack_paired_score.py`: `Data`, `Data.outcome` and `play_call`.
- **Error rate (PR):** 500 × mean GNUbg 2-ply loss. Under the frozen rule, an invalid, failed or missing answer would score the position's Random error. Neither setup had one.
- **Risk judgement:** the site definition, 50 × (risks found / Risk pays + right safety / Safety pays), i.e. the average of the two shares × 100. Margin 0.001. The class is the frozen position class: 165 Risk pays, 165 Safety pays and 170 with no trade-off among the 500 (66 / 66 / 68 among the main 200). These classes match `play_call` on the 2-ply scores for all 500 positions. An invalid answer would count with weight 1/n per legal play, as in the scorer.
- **Intervals:** 95% percentile, paired bootstrap over positions. There were 10,000 resamples, and the same indices were used for both setups and both measures. Generator: numpy `default_rng`, seeded the scorer's way (`rng_for`: first 8 bytes of sha256("nack-paired-2026-10-27:bootstrap:<look>")). The looks are `exploratory:sol-low-vs-high` for the 500 (seed 11554278864356261774) and `exploratory:sol-low-vs-high:main` for the main 200 (seed 14621529024168735346).

## Results

| Positions | n | Setup | Error rate (PR) [95%] | Risk judgement [95%] | Risks found | Right safety | Invalid |
|---|---|---|---|---|---|---|---|
| Main + reserve | 500 | Sol (low) | 12.21 [9.77, 14.87] | 66.4 [62.0, 70.6] | 69 / 165 | 150 / 165 | 0 |
| | | Sol (high) | 11.14 [8.68, 13.85] | 67.9 [63.5, 72.2] | 74 / 165 | 150 / 165 | 0 |
| | | **high − low** | **−1.06 [−2.27, +0.18]** | **+1.5 [−1.0, +4.1]** | +5 | 0 | |
| Main only | 200 | Sol (low) | 11.15 [8.11, 14.51] | 64.4 [57.5, 71.3] | 26 / 66 | 59 / 66 | 0 |
| | | Sol (high) | 9.88 [7.09, 13.06] | 66.7 [59.4, 73.7] | 29 / 66 | 59 / 66 | 0 |
| | | **high − low** | **−1.27 [−3.07, +0.20]** | **+2.3 [−2.2, +6.8]** | +3 | 0 | |

The standard PRs are the same as the frozen `results.json` values: 12.21 / 11.15 for Sol (low) and 11.14 / 9.88 for Sol (high), on 500 / 200 positions.

**Reading.** On these standard positions, high effort makes about 1 PR fewer errors than low effort. It also finds a few more risks (+5 of 165) and keeps the same right-safety count. Both 95% intervals include 0, though only just for PR: 4.4% of the resamples (5.0% on the main 200) have high ≥ low. So this is a direction, not an established difference. It is in line with the league figures (error rate 9.90 high vs 12.13 low on the site).

*Computed with a throwaway script that imports the scorer. It is not committed; the numbers above can be rebuilt from the rules stated.*
