# Nackgammon paired test, Cup-roster additions: short summary (2026-10-28)

For Can. **Nothing is published:** no site push; `d125adb` is still on hold. The details are in the new dated section of `mailbox/Nackgammon paired test - results.md`. The results file is `positions/nack-paired/results-2026-10-28/results.json`; the frozen 2026-10-27 results are unchanged.

- **Added under §10.14(g):**
  - Frontier: Claude Fable 5.1 (on) and Grok 4.7 (high) (the database setup "Grok 4.7 (on)").
  - Decision models: Liquid d1-ultra and Fastino GLiDE (hosted API).
  - Exploratory, no group (§10.14(h)): Gemini 4 Argon (low). Argon (on) was dropped after its smoke test: 14% of its answers were cut off at 32,768 tokens.
- **All five ran under the frozen rules:** the 400 main positions, then the extension. The frozen rule extended every one of them, so each has 1,000 records.
  - Only Grok 4.7 (high) has records without an answer: 34 (3.4%), all the 600 s time limit. They score the position's Random error, and both sensitivity checks are reported.
  - No answer from any setup was cut off at the output limit.
  - 17 of Grok's answers went past 32,768 output tokens. Its run sent no limit, so they are flagged and keep their scores.
- **Per setup, drop on 500 pairs with 97.5% intervals:**

  | Setup | Drop | 97.5% interval | Label |
  |---|---|---|---|
  | Claude Fable 5.1 (on) | +1.16 | [−2.17, +4.40] | **kept**, the first "kept" label in this test |
  | Grok 4.7 (high) | +0.85 | [−3.74, +5.35] | unclear |
  | Liquid d1-ultra | +6.17 | [−2.06, +13.95] | unclear |
  | Fastino GLiDE | +3.07 | [−3.84, +9.81] | unclear |
  | Gemini 4 Argon (low) | +2.71 | [−2.06, +7.62] | unclear |

- **Primary comparisons, M = 5, 99%, reported both ways:**
  - (i) original members only: reproduces the frozen results exactly.
  - (ii) with the additions, the primary result: decision models − workhorses −1.44 [−8.85, +4.96]; decision models − frontier −1.04 [−14.19, +10.26]; workhorses − frontier +0.40 [−6.68, +6.96]. The effort pairs are unchanged.
  - **No interval excludes 0**, either way and under every sensitivity rule.
- **Secondary:**
  - Spearman ρ = 0.90 [0.79, 0.92] over 28 setups (it was 0.87 over 23).
  - K is 0.86–0.95 for the new setups; none is unstable.
- **Engine check:** 6 new plays were rolled out. No comparison changes direction, either way.
- **Timing caveat, printed with the results:** these additions were made after the test's results had been read. They follow the Cup roster, not the results.
