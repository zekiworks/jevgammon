# Close choices — Leagues 2 and 3 (stage A)

**Probabilities over plays, not sampled reasoning.**

The definitions, Method (§9, commit be887d3 on `brief-2026-10-24`, fixed 15:15 UTC before computing), record version and conventions are the same as in `mailbox/Close choices - League 1.md`:
- snapshot 2026-10-24 12:51 UTC, `snap.db` sha256 `0e11c1793efe5ccde9b7bf57f00a3cbbeaaddb818303515ee5fd20ddc3b011d9`;
- plays sha256 `161ab5e07a53587a60caba0543a9d1561ccb6e4dc052693c7fb54a92d9f14e1f`;
- audit sha256 `4ad35193ab2d505585c0f76e61243999383c50941a31fa9411b1aabbf3628789`.

No model was called, and no engine value was missing. **†** marks a denominator under 200. Rows are in alphabetical order, with no ranking.

## League 2 totals

- **Decisions:** 30,792. **Eligible: 6,460.**
- **Excluded by reason:**
  - one letter only, or a program: 13,099. The N/A setups are Claude Fable 5.1 (off), Claude Sonnet 5.5 (high), Claude Sonnet 5.5 (low), Gemini 3.8 Flash (high), Gemini 3.8 Flash (low), GPT-6.1 Sol (high) and GNUbg weak;
  - incomplete distribution: 9,643;
  - asked in groups of options: 1,562;
  - invalid: 28.
- **Close choices:** 1,862. **Ties affecting the top two:** 229 (all at a positive probability); 143 of them are close choices.
- **Limit (League 2):** for the letter-readout setups, the complete records are the positions where every option letter fit among the returned top log-probabilities. These are mostly positions with few options. They are a **selected, not representative, subset** of each setup's decisions:
  - DeepSeek V4.1 Flash (off/on), Gemma 4 31B (off/on), GLM-5.3 (on), LFM2.5-24B-A2B (on), Qwen3.8 Flash (off) and Qwen3.8-27B (on): 104–644 eligible of 1,600–1,950;
  - Qwen3.8-27B (off): 1,383 of 1,673.
  - Only Liquid d1-ultra (a decision service: 1,737 of 1,738) is close to complete.
  - The "(on)" settings with 0 close choices (DeepSeek V4.1 Flash (on) 0 / 446, Qwen3.8-27B (on) 0 / 369, and Gemma 4 31B (on) 1 / 198) put probability ≈ 1 on one letter after reasoning. Their missed-risk comparison is N/A because the group of close choices is empty.

## League 3 totals

- **Decisions:** 13,928. **Eligible: 0.**
- Every setup is choice-only (one letter, no probabilities) or a program: 13,928 decisions under "one letter only, or a program". **Every League 3 setup is N/A:** no close-choice share, features, stake bands or missed-risk comparison exist for this league.

### League 2

Missing engine values among probability-complete decisions: 0.

#### Eligibility and close choices

| Setup | decisions | eligible | excluded by reason | close choices ÷ eligible | ties affecting the top two (positive / at 0; order / membership) | risk close choices ÷ close choices | risk close ÷ eligible |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (off) | 1,879 | 0 | one letter only, or a program 1,879 | N/A: no full probability distribution | — | — | — |
| Claude Sonnet 5.5 (high) | 2,018 | 0 | one letter only, or a program 2,018 | N/A: no full probability distribution | — | — | — |
| Claude Sonnet 5.5 (low) | 1,850 | 0 | one letter only, or a program 1,850 | N/A: no full probability distribution | — | — | — |
| DeepSeek V4.1 Flash (off) | 1,800 | 598 | asked in groups of options 187; incomplete distribution (an option without its own probability) 1,015 | 13.2% (79 / 598) | 15 (15 / 0; 5 / 10) | 22.8% (18 / 79)† | 3.0% (18 / 598) |
| DeepSeek V4.1 Flash (on) | 1,944 | 446 | invalid answer 27; asked in groups of options 231; incomplete distribution (an option without its own probability) 1,240 | 0.0% (0 / 446) | 17 (17 / 0; 0 / 17) | N/A (0 / 0) | 0.0% (0 / 446) |
| Gemini 3.8 Flash (high) | 2,013 | 0 | one letter only, or a program 2,013 | N/A: no full probability distribution | — | — | — |
| Gemini 3.8 Flash (low) | 1,745 | 0 | one letter only, or a program 1,745 | N/A: no full probability distribution | — | — | — |
| Gemma 4 31B (off) | 1,628 | 466 | asked in groups of options 152; incomplete distribution (an option without its own probability) 1,010 | 2.8% (13 / 466) | 1 (1 / 0; 0 / 1) | 30.8% (4 / 13)† | 0.9% (4 / 466) |
| Gemma 4 31B (on) | 1,855 | 198 | asked in groups of options 201; incomplete distribution (an option without its own probability) 1,456 | 0.5% (1 / 198)† | 0 (0 / 0; 0 / 0) | 0.0% (0 / 1)† | 0.0% (0 / 198)† |
| GLM-5.3 (on) | 1,756 | 515 | invalid answer 1; asked in groups of options 175; incomplete distribution (an option without its own probability) 1,065 | 5.6% (29 / 515) | 13 (13 / 0; 2 / 11) | 31.0% (9 / 29)† | 1.7% (9 / 515) |
| GNUbg weak | 1,785 | 0 | one letter only, or a program 1,785 | N/A: no full probability distribution | — | — | — |
| GPT-6.1 Sol (high) | 1,809 | 0 | one letter only, or a program 1,809 | N/A: no full probability distribution | — | — | — |
| LFM2.5-24B-A2B (on) | 1,622 | 104 | asked in groups of options 147; incomplete distribution (an option without its own probability) 1,371 | 1.9% (2 / 104)† | 1 (1 / 0; 0 / 1) | 50.0% (1 / 2)† | 1.0% (1 / 104)† |
| Liquid d1-ultra | 1,738 | 1,737 | asked in groups of options 1 | 61.3% (1,064 / 1,737) | 127 (127 / 0; 53 / 74) | 41.4% (440 / 1,064) | 25.3% (440 / 1,737) |
| Qwen3.8 Flash (off) | 1,894 | 644 | asked in groups of options 156; incomplete distribution (an option without its own probability) 1,094 | 39.3% (253 / 644) | 46 (46 / 0; 25 / 21) | 28.1% (71 / 253) | 11.0% (71 / 644) |
| Qwen3.8-27B (off) | 1,673 | 1,383 | asked in groups of options 140; incomplete distribution (an option without its own probability) 150 | 30.4% (421 / 1,383) | 9 (9 / 0; 3 / 6) | 34.0% (143 / 421) | 10.3% (143 / 1,383) |
| Qwen3.8-27B (on) | 1,783 | 369 | asked in groups of options 172; incomplete distribution (an option without its own probability) 1,242 | 0.0% (0 / 369) | 0 (0 / 0; 0 / 0) | N/A (0 / 0) | 0.0% (0 / 369) |

#### p1, p2 and p1 + p2 (means; medians in brackets)

| Setup | close: p1 | close: p2 | close: p1 + p2 | other: p1 | other: p2 | other: p1 + p2 |
|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | 0.550 [0.557] | 0.393 [0.385] | 0.943 [0.977] | 0.889 [0.925] | 0.094 [0.060] | 0.983 [0.996] |
| DeepSeek V4.1 Flash (on) | — | — | — | 1.000 [1.000] | 0.000 [0.000] | 1.000 [1.000] |
| Gemma 4 31B (off) | 0.556 [0.561] | 0.414 [0.424] | 0.969 [0.999] | 0.978 [1.000] | 0.021 [0.000] | 0.998 [1.000] |
| Gemma 4 31B (on) | 0.500 [0.500] | 0.500 [0.500] | 1.000 [1.000] | 1.000 [1.000] | 0.000 [0.000] | 1.000 [1.000] |
| GLM-5.3 (on) | 0.520 [0.525] | 0.372 [0.372] | 0.892 [0.944] | 0.955 [0.982] | 0.036 [0.012] | 0.991 [0.998] |
| LFM2.5-24B-A2B (on) | 0.510 [0.510] | 0.308 [0.308] | 0.818 [0.818] | 0.997 [1.000] | 0.003 [0.000] | 1.000 [1.000] |
| Liquid d1-ultra | 0.301 [0.272] | 0.221 [0.200] | 0.522 [0.469] | 0.548 [0.552] | 0.151 [0.145] | 0.699 [0.703] |
| Qwen3.8 Flash (off) | 0.495 [0.498] | 0.357 [0.349] | 0.852 [0.853] | 0.721 [0.731] | 0.188 [0.191] | 0.909 [0.914] |
| Qwen3.8-27B (off) | 0.475 [0.478] | 0.342 [0.343] | 0.817 [0.841] | 0.791 [0.800] | 0.134 [0.121] | 0.924 [0.950] |
| Qwen3.8-27B (on) | — | — | — | 1.000 [1.000] | 0.000 [0.000] | 1.000 [1.000] |

#### Features that differ between the two candidates (share of the group; several can differ)

| Setup | group | n | hitting rolls | newly made points | pip counts | longest prime | none / 1 / 2 / 3 / 4 differ |
|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | close choices | 79 | 22.8% (18 / 79)† | 10.1% (8 / 79)† | 10.1% (8 / 79)† | 15.2% (12 / 79)† | 47 / 19 / 12 / 1 / 0 |
| DeepSeek V4.1 Flash (off) | other decisions | 519 | 30.6% (159 / 519) | 10.6% (55 / 519) | 8.3% (43 / 519) | 26.0% (135 / 519) | 221 / 213 / 76 / 9 / 0 |
| DeepSeek V4.1 Flash (on) | close choices | 0 | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | 0 / 0 / 0 / 0 / 0 |
| DeepSeek V4.1 Flash (on) | other decisions | 446 | 43.0% (192 / 446) | 13.7% (61 / 446) | 16.8% (75 / 446) | 28.0% (125 / 446) | 136 / 185 / 108 / 16 / 1 |
| Gemma 4 31B (off) | close choices | 13 | 30.8% (4 / 13)† | 15.4% (2 / 13)† | 0.0% (0 / 13)† | 23.1% (3 / 13)† | 7 / 3 / 3 / 0 / 0 |
| Gemma 4 31B (off) | other decisions | 453 | 36.0% (163 / 453) | 13.0% (59 / 453) | 12.1% (55 / 453) | 23.4% (106 / 453) | 182 / 176 / 79 / 15 / 1 |
| Gemma 4 31B (on) | close choices | 1 | 0.0% (0 / 1)† | 0.0% (0 / 1)† | 0.0% (0 / 1)† | 0.0% (0 / 1)† | 1 / 0 / 0 / 0 / 0 |
| Gemma 4 31B (on) | other decisions | 197 | 38.1% (75 / 197)† | 11.2% (22 / 197)† | 17.3% (34 / 197)† | 27.9% (55 / 197)† | 65 / 83 / 44 / 5 / 0 |
| GLM-5.3 (on) | close choices | 29 | 31.0% (9 / 29)† | 20.7% (6 / 29)† | 6.9% (2 / 29)† | 20.7% (6 / 29)† | 16 / 6 / 4 / 3 / 0 |
| GLM-5.3 (on) | other decisions | 486 | 39.7% (193 / 486) | 14.6% (71 / 486) | 14.2% (69 / 486) | 27.0% (131 / 486) | 151 / 219 / 103 / 13 / 0 |
| LFM2.5-24B-A2B (on) | close choices | 2 | 50.0% (1 / 2)† | 0.0% (0 / 2)† | 0.0% (0 / 2)† | 100.0% (2 / 2)† | 0 / 1 / 1 / 0 / 0 |
| LFM2.5-24B-A2B (on) | other decisions | 102 | 39.2% (40 / 102)† | 6.9% (7 / 102)† | 11.8% (12 / 102)† | 29.4% (30 / 102)† | 31 / 55 / 14 / 2 / 0 |
| Liquid d1-ultra | close choices | 1,064 | 49.2% (524 / 1,064) | 30.7% (327 / 1,064) | 11.1% (118 / 1,064) | 25.7% (273 / 1,064) | 306 / 402 / 241 / 102 / 13 |
| Liquid d1-ultra | other decisions | 673 | 55.1% (371 / 673) | 41.0% (276 / 673) | 14.0% (94 / 673) | 33.0% (222 / 673) | 106 / 269 / 213 / 72 / 13 |
| Qwen3.8 Flash (off) | close choices | 253 | 28.9% (73 / 253) | 10.3% (26 / 253) | 3.6% (9 / 253) | 16.6% (42 / 253) | 139 / 85 / 22 / 7 / 0 |
| Qwen3.8 Flash (off) | other decisions | 391 | 40.2% (157 / 391) | 14.6% (57 / 391) | 10.7% (42 / 391) | 29.4% (115 / 391) | 120 / 179 / 85 / 6 / 1 |
| Qwen3.8-27B (off) | close choices | 421 | 37.5% (158 / 421) | 20.2% (85 / 421) | 7.1% (30 / 421) | 22.6% (95 / 421) | 178 / 148 / 69 / 22 / 4 |
| Qwen3.8-27B (off) | other decisions | 962 | 45.6% (439 / 962) | 29.7% (286 / 962) | 7.7% (74 / 962) | 28.2% (271 / 962) | 267 / 408 / 207 / 72 / 8 |
| Qwen3.8-27B (on) | close choices | 0 | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | 0 / 0 / 0 / 0 / 0 |
| Qwen3.8-27B (on) | other decisions | 369 | 37.1% (137 / 369) | 14.9% (55 / 369) | 14.4% (53 / 369) | 28.7% (106 / 369) | 118 / 168 / 67 / 15 / 1 |

#### Engine values (GNUbg 2-ply, equity): gap between the candidates and each one's loss against the engine's best play (mean [median])

| Setup | group | n | gap |e1 − e2| | candidate 1 loss | candidate 2 loss |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | close choices | 79 | 0.0594 [0.0133] | 0.0510 [0.0023] | 0.0205 [0.0007] |
| DeepSeek V4.1 Flash (off) | other decisions | 519 | 0.1140 [0.0362] | 0.0251 [0.0000] | 0.1033 [0.0235] |
| DeepSeek V4.1 Flash (on) | close choices | 0 | — | — | — |
| DeepSeek V4.1 Flash (on) | other decisions | 446 | 0.1465 [0.0623] | 0.0135 [0.0000] | 0.1426 [0.0514] |
| Gemma 4 31B (off) | close choices | 13 | 0.0544 [0.0209] | 0.0326 [0.0018] | 0.0322 [0.0060] |
| Gemma 4 31B (off) | other decisions | 453 | 0.1060 [0.0335] | 0.0267 [0.0000] | 0.0946 [0.0247] |
| Gemma 4 31B (on) | close choices | 1 | 0.0094 [0.0094] | 0.0000 [0.0000] | 0.0094 [0.0094] |
| Gemma 4 31B (on) | other decisions | 197 | 0.1335 [0.0494] | 0.0076 [0.0000] | 0.1289 [0.0321] |
| GLM-5.3 (on) | close choices | 29 | 0.1247 [0.0402] | 0.0735 [0.0030] | 0.0760 [0.0046] |
| GLM-5.3 (on) | other decisions | 486 | 0.1336 [0.0546] | 0.0271 [0.0000] | 0.1261 [0.0356] |
| LFM2.5-24B-A2B (on) | close choices | 2 | 0.2469 [0.2469] | 0.0000 [0.0000] | 0.2469 [0.2469] |
| LFM2.5-24B-A2B (on) | other decisions | 102 | 0.1268 [0.0469] | 0.0623 [0.0000] | 0.0883 [0.0000] |
| Liquid d1-ultra | close choices | 1,064 | 0.1086 [0.0558] | 0.0788 [0.0204] | 0.1006 [0.0398] |
| Liquid d1-ultra | other decisions | 673 | 0.1554 [0.0872] | 0.0337 [0.0000] | 0.1551 [0.0789] |
| Qwen3.8 Flash (off) | close choices | 253 | 0.0674 [0.0209] | 0.0380 [0.0002] | 0.0570 [0.0042] |
| Qwen3.8 Flash (off) | other decisions | 391 | 0.1252 [0.0495] | 0.0223 [0.0000] | 0.1153 [0.0345] |
| Qwen3.8-27B (off) | close choices | 421 | 0.1010 [0.0362] | 0.0835 [0.0154] | 0.0843 [0.0183] |
| Qwen3.8-27B (off) | other decisions | 962 | 0.1188 [0.0652] | 0.0679 [0.0001] | 0.1256 [0.0641] |
| Qwen3.8-27B (on) | close choices | 0 | — | — | — |
| Qwen3.8-27B (on) | other decisions | 369 | 0.1307 [0.0528] | 0.0291 [0.0000] | 0.1209 [0.0369] |

#### Margin 0.001: close choices by position class and by stake band (Risk pays only)

| Setup | Risk pays: close ÷ eligible | Safety pays: close ÷ eligible | No trade-off: close ÷ eligible | Risk pays: risk close ÷ close | Safety pays: risk close ÷ close | small stake | medium stake | big stake |
|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | 12.9% (9 / 70)† | 13.6% (23 / 169)† | 13.1% (47 / 359) | 77.8% (7 / 9)† | 47.8% (11 / 23)† | 11.1% (1 / 9)† | 11.1% (3 / 27)† | 14.7% (5 / 34)† |
| DeepSeek V4.1 Flash (on) | 0.0% (0 / 56)† | 0.0% (0 / 165)† | 0.0% (0 / 225) | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 10)† | 0.0% (0 / 20)† | 0.0% (0 / 26)† |
| Gemma 4 31B (off) | 4.9% (4 / 82)† | 1.4% (2 / 148)† | 3.0% (7 / 236) | 50.0% (2 / 4)† | 100.0% (2 / 2)† | 7.1% (1 / 14)† | 7.1% (2 / 28)† | 2.5% (1 / 40)† |
| Gemma 4 31B (on) | 0.0% (0 / 17)† | 0.0% (0 / 63)† | 0.8% (1 / 118)† | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 5)† | 0.0% (0 / 10)† | 0.0% (0 / 2)† |
| GLM-5.3 (on) | 5.3% (4 / 76)† | 4.2% (7 / 165)† | 6.6% (18 / 274) | 100.0% (4 / 4)† | 71.4% (5 / 7)† | 0.0% (0 / 10)† | 7.7% (2 / 26)† | 5.0% (2 / 40)† |
| LFM2.5-24B-A2B (on) | 0.0% (0 / 17)† | 3.6% (1 / 28)† | 1.7% (1 / 59)† | N/A (0 / 0) | 100.0% (1 / 1)† | 0.0% (0 / 1)† | 0.0% (0 / 7)† | 0.0% (0 / 9)† |
| Liquid d1-ultra | 66.4% (372 / 560) | 54.1% (377 / 697) | 65.6% (315 / 480) | 64.8% (241 / 372) | 52.8% (199 / 377) | 62.5% (40 / 64)† | 61.5% (120 / 195)† | 70.4% (212 / 301) |
| Qwen3.8 Flash (off) | 43.7% (38 / 87)† | 29.6% (61 / 206) | 43.9% (154 / 351) | 73.7% (28 / 38)† | 70.5% (43 / 61)† | 53.8% (7 / 13)† | 40.5% (15 / 37)† | 43.2% (16 / 37)† |
| Qwen3.8-27B (off) | 30.2% (124 / 411) | 27.3% (132 / 483) | 33.7% (165 / 489) | 66.9% (83 / 124)† | 45.5% (60 / 132)† | 30.0% (12 / 40)† | 36.2% (51 / 141)† | 26.5% (61 / 230) |
| Qwen3.8-27B (on) | 0.0% (0 / 44)† | 0.0% (0 / 115)† | 0.0% (0 / 210) | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 6)† | 0.0% (0 / 19)† | 0.0% (0 / 19)† |

#### Margin 0.001: missed risks in Risk pays positions whose candidates are a safe play and a riskier one

| Setup | group | close choices: missed ÷ n | other: missed ÷ n | crude difference [95%] | adjusted: close | adjusted: other (standardised) | adjusted difference [95%] | close choices covered | resamples left out (crude / adjusted) |
|---|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | 57 | 57.1% (4 / 7)† | 84.0% (42 / 50)† | -26.9 pts [-59.7, +19.6] | 66.7% | 83.1% | -16.4 pts [-54.3, +27.1] | 85.7% (6 / 7)† | 8 / 8 |
| DeepSeek V4.1 Flash (on) | 48 | N/A (0 / 0) | 68.8% (33 / 48)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| Gemma 4 31B (off) | 57 | 0.0% (0 / 2)† | 65.5% (36 / 55)† | -65.5 pts [-78.4, -51.9] | 0.0% | 50.0% | -50.0 pts [-100.0, +0.0] | 100.0% (2 / 2)† | 235 / 392 |
| Gemma 4 31B (on) | 16 | N/A (0 / 0) | 87.5% (14 / 16)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| GLM-5.3 (on) | 65 | 25.0% (1 / 4)† | 85.2% (52 / 61)† | -60.2 pts [-91.4, +12.6] | 25.0% | 83.6% | -58.6 pts [-94.7, +19.9] | 100.0% (4 / 4)† | 31 / 31 |
| LFM2.5-24B-A2B (on) | 15 | N/A (0 / 0) | 80.0% (12 / 15)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| Liquid d1-ultra | 346 | 56.4% (136 / 241) | 61.0% (64 / 105)† | -4.5 pts [-15.3, +5.8] | 56.8% | 62.9% | -6.1 pts [-17.3, +3.2] | 97.1% (234 / 241) | 0 / 0 |
| Qwen3.8 Flash (off) | 68 | 57.1% (16 / 28)† | 85.0% (34 / 40)† | -27.9 pts [-45.4, -7.2] | 57.1% | 85.6% | -28.5 pts [-46.4, -4.4] | 100.0% (28 / 28)† | 0 / 0 |
| Qwen3.8-27B (off) | 297 | 55.4% (46 / 83)† | 76.6% (164 / 214) | -21.2 pts [-35.6, -8.5] | 54.9% | 76.9% | -22.0 pts [-35.6, -9.8] | 98.8% (82 / 83)† | 0 / 0 |
| Qwen3.8-27B (on) | 34 | N/A (0 / 0) | 67.6% (23 / 34)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |

#### Margin 0.02: close choices by position class and by stake band (Risk pays only)

| Setup | Risk pays: close ÷ eligible | Safety pays: close ÷ eligible | No trade-off: close ÷ eligible | Risk pays: risk close ÷ close | Safety pays: risk close ÷ close | small stake | medium stake | big stake |
|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | 13.1% (8 / 61)† | 13.5% (24 / 178)† | 13.1% (47 / 359) | 87.5% (7 / 8)† | 45.8% (11 / 24)† | N/A (0 / 0) | 11.1% (3 / 27)† | 14.7% (5 / 34)† |
| DeepSeek V4.1 Flash (on) | 0.0% (0 / 46)† | 0.0% (0 / 175)† | 0.0% (0 / 225) | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 20)† | 0.0% (0 / 26)† |
| Gemma 4 31B (off) | 4.4% (3 / 68)† | 1.9% (3 / 162)† | 3.0% (7 / 236) | 66.7% (2 / 3)† | 66.7% (2 / 3)† | N/A (0 / 0) | 7.1% (2 / 28)† | 2.5% (1 / 40)† |
| Gemma 4 31B (on) | 0.0% (0 / 12)† | 0.0% (0 / 68)† | 0.8% (1 / 118)† | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 10)† | 0.0% (0 / 2)† |
| GLM-5.3 (on) | 6.1% (4 / 66)† | 4.0% (7 / 175)† | 6.6% (18 / 274) | 100.0% (4 / 4)† | 71.4% (5 / 7)† | N/A (0 / 0) | 7.7% (2 / 26)† | 5.0% (2 / 40)† |
| LFM2.5-24B-A2B (on) | 0.0% (0 / 16)† | 3.4% (1 / 29)† | 1.7% (1 / 59)† | N/A (0 / 0) | 100.0% (1 / 1)† | N/A (0 / 0) | 0.0% (0 / 7)† | 0.0% (0 / 9)† |
| Liquid d1-ultra | 66.9% (332 / 496) | 54.8% (417 / 761) | 65.6% (315 / 480) | 65.4% (217 / 332) | 53.5% (223 / 417) | N/A (0 / 0) | 61.5% (120 / 195)† | 70.4% (212 / 301) |
| Qwen3.8 Flash (off) | 41.9% (31 / 74)† | 31.1% (68 / 219) | 43.9% (154 / 351) | 77.4% (24 / 31)† | 69.1% (47 / 68)† | N/A (0 / 0) | 40.5% (15 / 37)† | 43.2% (16 / 37)† |
| Qwen3.8-27B (off) | 30.2% (112 / 371) | 27.5% (144 / 523) | 33.7% (165 / 489) | 68.8% (77 / 112)† | 45.8% (66 / 144)† | N/A (0 / 0) | 36.2% (51 / 141)† | 26.5% (61 / 230) |
| Qwen3.8-27B (on) | 0.0% (0 / 38)† | 0.0% (0 / 121)† | 0.0% (0 / 210) | N/A (0 / 0) | N/A (0 / 0) | N/A (0 / 0) | 0.0% (0 / 19)† | 0.0% (0 / 19)† |

#### Margin 0.02: missed risks in Risk pays positions whose candidates are a safe play and a riskier one

| Setup | group | close choices: missed ÷ n | other: missed ÷ n | crude difference [95%] | adjusted: close | adjusted: other (standardised) | adjusted difference [95%] | close choices covered | resamples left out (crude / adjusted) |
|---|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash (off) | 50 | 57.1% (4 / 7)† | 83.7% (36 / 43)† | -26.6 pts [-60.5, +20.0] | 66.7% | 84.1% | -17.5 pts [-57.2, +25.0] | 85.7% (6 / 7)† | 7 / 7 |
| DeepSeek V4.1 Flash (on) | 38 | N/A (0 / 0) | 60.5% (23 / 38)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| Gemma 4 31B (off) | 48 | 0.0% (0 / 2)† | 58.7% (27 / 46)† | -58.7 pts [-72.1, -43.2] | 0.0% | 50.0% | -50.0 pts [-100.0, +0.0] | 100.0% (2 / 2)† | 252 / 544 |
| Gemma 4 31B (on) | 11 | N/A (0 / 0) | 90.9% (10 / 11)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| GLM-5.3 (on) | 56 | 25.0% (1 / 4)† | 82.7% (43 / 52)† | -57.7 pts [-90.4, +1.1] | 25.0% | 83.6% | -58.6 pts [-95.1, +12.2] | 100.0% (4 / 4)† | 13 / 13 |
| LFM2.5-24B-A2B (on) | 14 | N/A (0 / 0) | 78.6% (11 / 14)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |
| Liquid d1-ultra | 304 | 56.2% (122 / 217) | 59.8% (52 / 87)† | -3.5 pts [-15.1, +8.7] | 56.6% | 61.5% | -4.9 pts [-17.4, +7.0] | 97.7% (212 / 217) | 0 / 0 |
| Qwen3.8 Flash (off) | 58 | 58.3% (14 / 24)† | 82.4% (28 / 34)† | -24.0 pts [-42.5, -4.3] | 58.3% | 83.2% | -24.9 pts [-44.6, -0.4] | 100.0% (24 / 24)† | 0 / 0 |
| Qwen3.8-27B (off) | 273 | 55.8% (43 / 77)† | 76.0% (149 / 196)† | -20.2 pts [-34.7, -6.8] | 54.7% | 76.6% | -22.0 pts [-35.4, -9.9] | 97.4% (75 / 77)† | 0 / 0 |
| Qwen3.8-27B (on) | 31 | N/A (0 / 0) | 64.5% (20 / 31)† | N/A: no close choices in this group | N/A | N/A | N/A | — | — |

### League 3

Missing engine values among probability-complete decisions: 0.

#### Eligibility and close choices

| Setup | decisions | eligible | excluded by reason | close choices ÷ eligible | ties affecting the top two (positive / at 0; order / membership) | risk close choices ÷ close choices | risk close ÷ eligible |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (on) | 1,190 | 0 | one letter only, or a program 1,190 | N/A: no full probability distribution | — | — | — |
| Claude Opus 5.5 (off) | 1,292 | 0 | one letter only, or a program 1,292 | N/A: no full probability distribution | — | — | — |
| Claude Opus 5.5 (on) | 1,371 | 0 | one letter only, or a program 1,371 | N/A: no full probability distribution | — | — | — |
| Gemini 4 Argon (off) | 1,338 | 0 | one letter only, or a program 1,338 | N/A: no full probability distribution | — | — | — |
| Gemini 4 Argon (on) | 1,287 | 0 | one letter only, or a program 1,287 | N/A: no full probability distribution | — | — | — |
| GNUbg weak | 1,433 | 0 | one letter only, or a program 1,433 | N/A: no full probability distribution | — | — | — |
| GPT-6 Astra (off) | 1,196 | 0 | one letter only, or a program 1,196 | N/A: no full probability distribution | — | — | — |
| GPT-6 Astra (on) | 1,226 | 0 | one letter only, or a program 1,226 | N/A: no full probability distribution | — | — | — |
| GPT-6.1 Sol (low) | 1,214 | 0 | one letter only, or a program 1,214 | N/A: no full probability distribution | — | — | — |
| Grok 4.7 (off) | 1,178 | 0 | one letter only, or a program 1,178 | N/A: no full probability distribution | — | — | — |
| Grok 4.7 (on) | 1,203 | 0 | one letter only, or a program 1,203 | N/A: no full probability distribution | — | — | — |

No setup in this league has an eligible decision: every column below is N/A.



## Reading limits

- These are probabilities over plays, not sampled reasoning. They say nothing about how a model reasoned or why it chose.
- Setups played different positions, so comparisons across setups are not paired.
- League 2: the eligible subset is selected by how many options fit the returned log-probabilities (see above).
- The missed-risk comparisons for setups with very small groups (e.g. Gemma 4 31B (off): 2 close choices) have degenerate bootstrap intervals. Read them as counts only.
