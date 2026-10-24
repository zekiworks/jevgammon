# Close choices — League 1 (stage A)

**Probabilities over plays, not sampled reasoning.**

Request: `mailbox/Close choices - request 2026-10-24.md`, stage A. No model was called. Branch `brief-2026-10-24` only; nothing merged or deployed.

## Definitions (Method, fixed before computing)

- Method: `tools/site/content/method-spec-2026-10-24.md` §9 + `close_choices_2026-10-24.json`, committed on `brief-2026-10-24` as **be887d3**, 2026-10-24 15:16 UTC. Nothing was computed before that commit, and §9 hasn't changed since.
- **Close choice:** "A decision is a close choice when the second most likely play has at least half the probability of the first (internally: split)." That is, p2 ≥ 0.5 × p1, where p1 and p2 are the two highest probabilities over legal plays (the stored vector divided by its sum).
- **Ties:** equal probabilities are ordered by the recorded option order (the shuffled order shown to the model), earlier first, and never by engine values. A tie **affects the top two** when p1 = p2 (the order of the two candidates comes from the option order) or p2 = p3 (which play is candidate 2 comes from the option order). Ties are reported in two parts: at a positive probability, and at 0 (p2 = 0, where every play but one has probability 0). A tie never changes whether a decision is a close choice; it only changes which plays are compared.
- **Eligible:** probability audit status `complete` (§1 of the same spec; `tools/site/prob_audit.py`), decided by the record's content, plus an engine value for every legal play. Excluded and counted by reason:
  - invalid answer;
  - asked in groups of options;
  - incomplete distribution (sparse);
  - unverified, no raw response, not audited;
  - no engine value;
  - one letter only, or a program. A setup with no eligible decision shows **N/A**.
- **Features** compared between candidate 1 and candidate 2, read from the option text the model was shown:
  - hitting rolls (the opponent's);
  - set of newly made points;
  - both pip counts;
  - longest prime.

  Every feature that differs is recorded, and none is picked as the cause. Engine values are GNUbg 1.08 2-ply cubeless equity, with the existing settings. The gap is |e1 − e2|, and each candidate's loss is measured against the engine's best play.
- **Risk close choice:** a close choice where one candidate leaves the minimum hitting rolls among all legal plays and the other leaves more (a "risk pair"). It doesn't depend on the margin.
- **Position class, stake band and risk call** come from the site (`analysis.play_call`) at margins 0.001 and 0.02. Stake bands apply to Risk pays positions only: small < 0.02 ≤ medium ≤ 0.08 < big. At 0.02, Risk pays requires a stake ≥ 0.02, so the small band is empty by construction (N/A 0 / 0). A big stake means playing safe costs more by the engine's value. It isn't decision difficulty, and nothing here assumes good setups have more or fewer close choices there.
- **Missed risks:** group G = eligible decisions in Risk pays positions whose two candidates are a risk pair. The outcome is the risk class of the play actually made (missed risk = a minimum-hitting play where the risk paid). The table compares close choices with the other decisions in G:
  - **crude:** the raw rates and their difference;
  - **adjusted:** strata = phase × number of options (2–5, 6–10, 11–15, 16–25, 26+) × the engine gap between its two best plays (< 0.02, 0.02–0.08, > 0.08). Only strata holding both groups count. The other decisions are standardised to the close choices' stratum mix, and coverage = close choices in the counted strata.
  - **95% intervals:** 2,000 bootstrap resamples of the setup's matches. Decisions of the same match stay together.
  - Empty comparison groups show N/A. This is an association within recorded decisions, not a cause.
- Shares always carry count and denominator. **†** = denominator under 200, the site's minimum. The value is still shown.
- A share of close choices isn't presented as good or bad, and setups aren't ranked by it. Rows are in alphabetical order.

## Record version (fixed snapshot)

This is the same snapshot as the ability and caution analyses: site snapshot copied **2026-10-24 12:51 UTC**, with all three leagues Finished.
- `snap.db` sha256 `0e11c1793efe5ccde9b7bf57f00a3cbbeaaddb818303515ee5fd20ddc3b011d9`
- GNUbg scores `plays/s0..s31.db` (concatenated in that order) sha256 `161ab5e07a53587a60caba0543a9d1561ccb6e4dc052693c7fb54a92d9f14e1f`
- probability audit `content/probability_audit.json.gz` sha256 `4ad35193ab2d505585c0f76e61243999383c50941a31fa9411b1aabbf3628789`
- Code: `tools/site/close_choices.py` on `brief-2026-10-24`. Rerun with `python3 tools/site/close_choices.py STATE 1`.
- `v3.db` wasn't opened for this analysis. The audit had already read it, read-only. No running league or existing result was changed.
- **Missing engine values: 0.** No GNUbg run was needed, because every legal play of every probability-complete decision already has a 2-ply value.

## League 1 totals

- **Decisions:** 36,804 league decisions. **Eligible: 30,262.**
- **Excluded by reason:**
  - one letter only, or a program: 5,227 (GNUbg weak, Random and Safest are N/A);
  - asked in groups of options: 1,055;
  - incomplete distribution: 260 (LFM2.5-24B-A2B (off));
  - invalid: 0; unverified, no raw, not audited, no engine value: 0.
- **Close choices:** 15,123 of 30,262 eligible.
- **Ties affecting the top two:** 1,553 (1,550 at a positive probability, 3 at 0). 832 of them are close choices.

## League 1 tables

Missing engine values among probability-complete decisions: 0.

#### Eligibility and close choices

| Setup | decisions | eligible | excluded by reason | close choices ÷ eligible | ties affecting the top two (positive / at 0; order / membership) | risk close choices ÷ close choices | risk close ÷ eligible |
|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 2,055 | 2,055 | none | 29.1% (597 / 2,055) | 283 (283 / 0; 18 / 266) | 32.0% (191 / 597) | 9.3% (191 / 2,055) |
| Clef | 2,013 | 1,998 | asked in groups of options 15 | 86.0% (1,719 / 1,998) | 25 (25 / 0; 10 / 15) | 43.3% (744 / 1,719) | 37.2% (744 / 1,998) |
| Cygnet (Gemma 4 12B) | 1,984 | 1,846 | asked in groups of options 138 | 21.6% (398 / 1,846) | 34 (34 / 0; 11 / 23) | 37.4% (149 / 398) | 8.1% (149 / 1,846) |
| Decider Flash v1.2 | 1,867 | 1,660 | asked in groups of options 207 | 68.0% (1,128 / 1,660) | 124 (124 / 0; 44 / 85) | 42.6% (480 / 1,128) | 28.9% (480 / 1,660) |
| Decider v1.1 27B | 2,020 | 1,795 | asked in groups of options 225 | 40.3% (724 / 1,795) | 83 (83 / 0; 42 / 41) | 45.6% (330 / 724) | 18.4% (330 / 1,795) |
| Decider v1.2 27B | 1,909 | 1,721 | asked in groups of options 188 | 53.6% (922 / 1,721) | 117 (117 / 0; 33 / 84) | 43.4% (400 / 922) | 23.2% (400 / 1,721) |
| Fastino GLiDE | 2,062 | 2,060 | asked in groups of options 2 | 49.7% (1,023 / 2,060) | 0 (0 / 0; 0 / 0) | 45.4% (464 / 1,023) | 22.5% (464 / 2,060) |
| Fastino GLiDE v1.2 (local) | 1,917 | 1,915 | asked in groups of options 2 | 55.7% (1,066 / 1,915) | 143 (143 / 0; 60 / 85) | 42.4% (452 / 1,066) | 23.6% (452 / 1,915) |
| GNUbg weak | 1,778 | 0 | one letter only, or a program 1,778 | N/A: no full probability distribution | — | — | — |
| GPT-6 Luna | 1,931 | 1,931 | none | 43.4% (838 / 1,931) | 137 (136 / 1; 36 / 101) | 38.5% (323 / 838) | 16.7% (323 / 1,931) |
| Jev 1.13.0 | 1,849 | 1,849 | none | 42.7% (790 / 1,849) | 117 (115 / 2; 22 / 95) | 42.3% (334 / 790) | 18.1% (334 / 1,849) |
| Jev 1.14.0 | 1,951 | 1,950 | asked in groups of options 1 | 43.5% (849 / 1,950) | 120 (120 / 0; 28 / 93) | 40.9% (347 / 849) | 17.8% (347 / 1,950) |
| LFM2.5-24B-A2B (off) | 1,962 | 1,516 | asked in groups of options 186; incomplete distribution (an option without its own probability) 260 | 57.8% (877 / 1,516) | 277 (277 / 0; 118 / 169) | 42.1% (369 / 877) | 24.3% (369 / 1,516) |
| Mercury Decide | 1,814 | 1,814 | none | 15.6% (283 / 1,814) | 93 (93 / 0; 32 / 62) | 27.9% (79 / 283) | 4.4% (79 / 1,814) |
| Open-Jev 27B v1.1 | 2,076 | 2,076 | none | 97.9% (2,032 / 2,076) | 0 (0 / 0; 0 / 0) | 37.6% (765 / 2,032) | 36.8% (765 / 2,076) |
| Random | 1,371 | 0 | one letter only, or a program 1,371 | N/A: no full probability distribution | — | — | — |
| Safest | 2,078 | 0 | one letter only, or a program 2,078 | N/A: no full probability distribution | — | — | — |
| SubQ Snap Preview | 2,158 | 2,157 | asked in groups of options 1 | 49.9% (1,076 / 2,157) | 0 (0 / 0; 0 / 0) | 33.8% (364 / 1,076) | 16.9% (364 / 2,157) |
| Winnow-12B | 2,009 | 1,919 | asked in groups of options 90 | 41.7% (801 / 1,919) | 0 (0 / 0; 0 / 0) | 36.2% (290 / 801) | 15.1% (290 / 1,919) |

#### p1, p2 and p1 + p2 (means; medians in brackets)

| Setup | close: p1 | close: p2 | close: p1 + p2 | other: p1 | other: p2 | other: p1 + p2 |
|---|---|---|---|---|---|---|
| Celeris-1 Decision | 0.419 [0.420] | 0.303 [0.300] | 0.722 [0.720] | 0.774 [0.810] | 0.106 [0.090] | 0.880 [0.920] |
| Clef | 0.252 [0.204] | 0.191 [0.157] | 0.443 [0.360] | 0.407 [0.366] | 0.155 [0.130] | 0.563 [0.496] |
| Cygnet (Gemma 4 12B) | 0.449 [0.450] | 0.316 [0.309] | 0.765 [0.777] | 0.728 [0.741] | 0.119 [0.105] | 0.847 [0.859] |
| Decider Flash v1.2 | 0.298 [0.266] | 0.219 [0.197] | 0.518 [0.465] | 0.522 [0.525] | 0.163 [0.152] | 0.685 [0.684] |
| Decider v1.1 27B | 0.393 [0.389] | 0.280 [0.273] | 0.673 [0.668] | 0.717 [0.730] | 0.134 [0.133] | 0.851 [0.889] |
| Decider v1.2 27B | 0.351 [0.336] | 0.256 [0.240] | 0.607 [0.583] | 0.604 [0.599] | 0.158 [0.153] | 0.762 [0.780] |
| Fastino GLiDE | 0.340 [0.326] | 0.245 [0.235] | 0.585 [0.566] | 0.608 [0.620] | 0.152 [0.148] | 0.761 [0.787] |
| Fastino GLiDE v1.2 (local) | 0.311 [0.295] | 0.222 [0.208] | 0.532 [0.507] | 0.580 [0.583] | 0.149 [0.147] | 0.729 [0.752] |
| GPT-6 Luna | 0.409 [0.410] | 0.297 [0.300] | 0.707 [0.715] | 0.679 [0.680] | 0.150 [0.150] | 0.829 [0.860] |
| Jev 1.13.0 | 0.398 [0.390] | 0.286 [0.280] | 0.684 [0.680] | 0.678 [0.680] | 0.148 [0.150] | 0.826 [0.840] |
| Jev 1.14.0 | 0.383 [0.380] | 0.274 [0.270] | 0.657 [0.650] | 0.660 [0.670] | 0.148 [0.150] | 0.808 [0.820] |
| LFM2.5-24B-A2B (off) | 0.313 [0.288] | 0.232 [0.219] | 0.546 [0.504] | 0.607 [0.590] | 0.158 [0.158] | 0.765 [0.742] |
| Mercury Decide | 0.488 [0.500] | 0.348 [0.349] | 0.835 [0.876] | 0.888 [0.945] | 0.074 [0.036] | 0.962 [0.989] |
| Open-Jev 27B v1.1 | 0.206 [0.150] | 0.174 [0.131] | 0.379 [0.279] | 0.419 [0.313] | 0.178 [0.128] | 0.597 [0.430] |
| SubQ Snap Preview | 0.342 [0.333] | 0.248 [0.236] | 0.590 [0.574] | 0.595 [0.596] | 0.148 [0.141] | 0.743 [0.751] |
| Winnow-12B | 0.399 [0.394] | 0.291 [0.285] | 0.691 [0.684] | 0.719 [0.729] | 0.131 [0.129] | 0.850 [0.885] |

#### Features that differ between the two candidates (share of the group; several can differ)

| Setup | group | n | hitting rolls | newly made points | pip counts | longest prime | none / 1 / 2 / 3 / 4 differ |
|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | close choices | 597 | 38.9% (232 / 597) | 25.3% (151 / 597) | 11.7% (70 / 597) | 21.3% (127 / 597) | 223 / 222 / 108 / 34 / 10 |
| Celeris-1 Decision | other decisions | 1,458 | 56.9% (829 / 1,458) | 33.7% (492 / 1,458) | 13.2% (193 / 1,458) | 29.8% (434 / 1,458) | 279 / 625 / 361 / 171 / 22 |
| Clef | close choices | 1,719 | 61.4% (1,055 / 1,719) | 32.2% (553 / 1,719) | 14.1% (243 / 1,719) | 26.9% (463 / 1,719) | 336 / 715 / 441 / 191 / 36 |
| Clef | other decisions | 279 | 64.2% (179 / 279) | 47.3% (132 / 279) | 18.6% (52 / 279) | 38.0% (106 / 279) | 29 / 86 / 110 / 53 / 1 |
| Cygnet (Gemma 4 12B) | close choices | 398 | 43.7% (174 / 398) | 18.8% (75 / 398) | 10.3% (41 / 398) | 18.8% (75 / 398) | 159 / 144 / 66 / 27 / 2 |
| Cygnet (Gemma 4 12B) | other decisions | 1,448 | 56.4% (816 / 1,448) | 31.6% (458 / 1,448) | 10.9% (158 / 1,448) | 27.3% (395 / 1,448) | 342 / 581 / 343 / 168 / 14 |
| Decider Flash v1.2 | close choices | 1,128 | 60.5% (682 / 1,128) | 29.1% (328 / 1,128) | 11.6% (131 / 1,128) | 23.2% (262 / 1,128) | 237 / 514 / 256 / 107 / 14 |
| Decider Flash v1.2 | other decisions | 532 | 60.5% (322 / 532) | 43.0% (229 / 532) | 11.7% (62 / 532) | 27.6% (147 / 532) | 85 / 215 / 160 / 63 / 9 |
| Decider v1.1 27B | close choices | 724 | 53.2% (385 / 724) | 27.6% (200 / 724) | 14.1% (102 / 724) | 29.1% (211 / 724) | 183 / 280 / 175 / 76 / 10 |
| Decider v1.1 27B | other decisions | 1,071 | 53.7% (575 / 1,071) | 33.7% (361 / 1,071) | 12.4% (133 / 1,071) | 30.3% (324 / 1,071) | 233 / 426 / 283 / 115 / 14 |
| Decider v1.2 27B | close choices | 922 | 52.8% (487 / 922) | 25.2% (232 / 922) | 12.3% (113 / 922) | 26.5% (244 / 922) | 252 / 372 / 206 / 76 / 16 |
| Decider v1.2 27B | other decisions | 799 | 60.3% (482 / 799) | 33.8% (270 / 799) | 15.4% (123 / 799) | 29.0% (232 / 799) | 144 / 326 / 223 / 89 / 17 |
| Fastino GLiDE | close choices | 1,023 | 58.8% (602 / 1,023) | 34.5% (353 / 1,023) | 16.0% (164 / 1,023) | 30.9% (316 / 1,023) | 201 / 374 / 306 / 119 / 23 |
| Fastino GLiDE | other decisions | 1,037 | 57.8% (599 / 1,037) | 35.4% (367 / 1,037) | 12.3% (128 / 1,037) | 30.1% (312 / 1,037) | 206 / 416 / 268 / 134 / 13 |
| Fastino GLiDE v1.2 (local) | close choices | 1,066 | 51.2% (546 / 1,066) | 37.9% (404 / 1,066) | 14.2% (151 / 1,066) | 32.9% (351 / 1,066) | 235 / 392 / 279 / 138 / 22 |
| Fastino GLiDE v1.2 (local) | other decisions | 849 | 54.5% (463 / 849) | 38.3% (325 / 849) | 11.7% (99 / 849) | 30.5% (259 / 849) | 177 / 324 / 234 / 102 / 12 |
| GPT-6 Luna | close choices | 838 | 42.7% (358 / 838) | 22.2% (186 / 838) | 11.9% (100 / 838) | 20.2% (169 / 838) | 309 / 318 / 146 / 57 / 8 |
| GPT-6 Luna | other decisions | 1,093 | 55.4% (606 / 1,093) | 37.3% (408 / 1,093) | 10.5% (115 / 1,093) | 34.1% (373 / 1,093) | 180 / 466 / 319 / 114 / 14 |
| Jev 1.13.0 | close choices | 790 | 50.3% (397 / 790) | 32.4% (256 / 790) | 13.3% (105 / 790) | 27.5% (217 / 790) | 229 / 285 / 156 / 102 / 18 |
| Jev 1.13.0 | other decisions | 1,059 | 56.3% (596 / 1,059) | 39.2% (415 / 1,059) | 12.0% (127 / 1,059) | 31.4% (333 / 1,059) | 197 / 429 / 275 / 140 / 18 |
| Jev 1.14.0 | close choices | 849 | 47.1% (400 / 849) | 29.9% (254 / 849) | 11.0% (93 / 849) | 28.0% (238 / 849) | 251 / 322 / 179 / 83 / 14 |
| Jev 1.14.0 | other decisions | 1,101 | 56.4% (621 / 1,101) | 35.2% (388 / 1,101) | 13.9% (153 / 1,101) | 33.9% (373 / 1,101) | 187 / 465 / 297 / 132 / 20 |
| LFM2.5-24B-A2B (off) | close choices | 877 | 60.0% (526 / 877) | 27.4% (240 / 877) | 13.2% (116 / 877) | 22.8% (200 / 877) | 190 / 381 / 226 / 71 / 9 |
| LFM2.5-24B-A2B (off) | other decisions | 639 | 58.2% (372 / 639) | 28.3% (181 / 639) | 16.3% (104 / 639) | 25.5% (163 / 639) | 120 / 277 / 189 / 47 / 6 |
| Mercury Decide | close choices | 283 | 30.7% (87 / 283) | 26.5% (75 / 283) | 9.5% (27 / 283) | 25.1% (71 / 283) | 128 / 81 / 49 / 19 / 6 |
| Mercury Decide | other decisions | 1,531 | 50.9% (780 / 1,531) | 33.7% (516 / 1,531) | 10.1% (155 / 1,531) | 28.3% (434 / 1,531) | 338 / 663 / 381 / 136 / 13 |
| Open-Jev 27B v1.1 | close choices | 2,032 | 55.8% (1,134 / 2,032) | 36.5% (741 / 2,032) | 8.7% (176 / 2,032) | 31.1% (631 / 2,032) | 421 / 812 / 548 / 230 / 21 |
| Open-Jev 27B v1.1 | other decisions | 44 | 40.9% (18 / 44)† | 54.5% (24 / 44)† | 6.8% (3 / 44)† | 43.2% (19 / 44)† | 9 / 12 / 17 / 6 / 0 |
| SubQ Snap Preview | close choices | 1,076 | 50.7% (545 / 1,076) | 29.3% (315 / 1,076) | 11.1% (119 / 1,076) | 26.8% (288 / 1,076) | 302 / 408 / 251 / 103 / 12 |
| SubQ Snap Preview | other decisions | 1,081 | 55.9% (604 / 1,081) | 32.0% (346 / 1,081) | 11.1% (120 / 1,081) | 27.6% (298 / 1,081) | 236 / 458 / 260 / 118 / 9 |
| Winnow-12B | close choices | 801 | 50.9% (408 / 801) | 21.2% (170 / 801) | 14.1% (113 / 801) | 20.2% (162 / 801) | 262 / 317 / 144 / 64 / 14 |
| Winnow-12B | other decisions | 1,118 | 56.6% (633 / 1,118) | 42.8% (479 / 1,118) | 9.4% (105 / 1,118) | 30.4% (340 / 1,118) | 210 / 420 / 341 / 133 / 14 |

#### Engine values (GNUbg 2-ply, equity): gap between the candidates and each one's loss against the engine's best play (mean [median])

| Setup | group | n | gap |e1 − e2| | candidate 1 loss | candidate 2 loss |
|---|---|---|---|---|---|
| Celeris-1 Decision | close choices | 597 | 0.1110 [0.0528] | 0.0741 [0.0184] | 0.0986 [0.0381] |
| Celeris-1 Decision | other decisions | 1,458 | 0.1406 [0.0853] | 0.0616 [0.0000] | 0.1336 [0.0718] |
| Clef | close choices | 1,719 | 0.1415 [0.0719] | 0.0821 [0.0138] | 0.1332 [0.0579] |
| Clef | other decisions | 279 | 0.1728 [0.1113] | 0.0275 [0.0000] | 0.1807 [0.1175] |
| Cygnet (Gemma 4 12B) | close choices | 398 | 0.1153 [0.0518] | 0.0920 [0.0184] | 0.1026 [0.0368] |
| Cygnet (Gemma 4 12B) | other decisions | 1,448 | 0.1390 [0.0727] | 0.0676 [0.0045] | 0.1480 [0.0799] |
| Decider Flash v1.2 | close choices | 1,128 | 0.1390 [0.0768] | 0.1254 [0.0476] | 0.1498 [0.0636] |
| Decider Flash v1.2 | other decisions | 532 | 0.1584 [0.1033] | 0.0667 [0.0000] | 0.1547 [0.0899] |
| Decider v1.1 27B | close choices | 724 | 0.1327 [0.0707] | 0.0999 [0.0336] | 0.1068 [0.0458] |
| Decider v1.1 27B | other decisions | 1,071 | 0.1448 [0.0775] | 0.0499 [0.0000] | 0.1405 [0.0647] |
| Decider v1.2 27B | close choices | 922 | 0.1280 [0.0717] | 0.0891 [0.0298] | 0.1117 [0.0367] |
| Decider v1.2 27B | other decisions | 799 | 0.1551 [0.0984] | 0.0470 [0.0000] | 0.1550 [0.0909] |
| Fastino GLiDE | close choices | 1,023 | 0.1380 [0.0791] | 0.0979 [0.0326] | 0.1258 [0.0575] |
| Fastino GLiDE | other decisions | 1,037 | 0.1409 [0.0893] | 0.0483 [0.0000] | 0.1301 [0.0733] |
| Fastino GLiDE v1.2 (local) | close choices | 1,066 | 0.1252 [0.0694] | 0.0946 [0.0288] | 0.1161 [0.0469] |
| Fastino GLiDE v1.2 (local) | other decisions | 849 | 0.1376 [0.0870] | 0.0419 [0.0000] | 0.1339 [0.0696] |
| GPT-6 Luna | close choices | 838 | 0.1031 [0.0522] | 0.1000 [0.0268] | 0.1136 [0.0441] |
| GPT-6 Luna | other decisions | 1,093 | 0.1367 [0.0815] | 0.0667 [0.0017] | 0.1536 [0.0932] |
| Jev 1.13.0 | close choices | 790 | 0.1120 [0.0573] | 0.0922 [0.0191] | 0.1044 [0.0474] |
| Jev 1.13.0 | other decisions | 1,059 | 0.1514 [0.0929] | 0.0506 [0.0000] | 0.1511 [0.0879] |
| Jev 1.14.0 | close choices | 849 | 0.1074 [0.0559] | 0.0934 [0.0340] | 0.1125 [0.0449] |
| Jev 1.14.0 | other decisions | 1,101 | 0.1591 [0.0934] | 0.0586 [0.0000] | 0.1571 [0.0889] |
| LFM2.5-24B-A2B (off) | close choices | 877 | 0.1429 [0.0801] | 0.1216 [0.0446] | 0.1316 [0.0661] |
| LFM2.5-24B-A2B (off) | other decisions | 639 | 0.1615 [0.0826] | 0.0752 [0.0040] | 0.1457 [0.0644] |
| Mercury Decide | close choices | 283 | 0.1003 [0.0493] | 0.1236 [0.0437] | 0.1282 [0.0461] |
| Mercury Decide | other decisions | 1,531 | 0.1345 [0.0731] | 0.0891 [0.0106] | 0.1587 [0.0814] |
| Open-Jev 27B v1.1 | close choices | 2,032 | 0.1464 [0.0816] | 0.1309 [0.0347] | 0.1722 [0.0838] |
| Open-Jev 27B v1.1 | other decisions | 44 | 0.1446 [0.1377] | 0.0000 [0.0000] | 0.1446 [0.1377] |
| SubQ Snap Preview | close choices | 1,076 | 0.1276 [0.0659] | 0.1161 [0.0427] | 0.1397 [0.0554] |
| SubQ Snap Preview | other decisions | 1,081 | 0.1382 [0.0732] | 0.0683 [0.0000] | 0.1453 [0.0742] |
| Winnow-12B | close choices | 801 | 0.1306 [0.0593] | 0.1103 [0.0289] | 0.1195 [0.0423] |
| Winnow-12B | other decisions | 1,118 | 0.1510 [0.0816] | 0.0849 [0.0085] | 0.1559 [0.0771] |

#### Margin 0.001: close choices by position class and by stake band (Risk pays only)

| Setup | Risk pays: close ÷ eligible | Safety pays: close ÷ eligible | No trade-off: close ÷ eligible | Risk pays: risk close ÷ close | Safety pays: risk close ÷ close | small stake | medium stake | big stake |
|---|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 28.9% (209 / 722) | 23.8% (203 / 852) | 38.5% (185 / 481) | 58.9% (123 / 209) | 33.5% (68 / 203) | 27.1% (26 / 96)† | 28.1% (64 / 228) | 29.9% (119 / 398) |
| Clef | 90.1% (661 / 734) | 83.7% (680 / 812) | 83.6% (378 / 452) | 49.3% (326 / 661) | 61.5% (418 / 680) | 91.4% (74 / 81)† | 89.9% (205 / 228) | 89.9% (382 / 425) |
| Cygnet (Gemma 4 12B) | 22.5% (152 / 676) | 20.5% (143 / 699) | 21.9% (103 / 471) | 57.9% (88 / 152)† | 42.7% (61 / 143)† | 22.1% (15 / 68)† | 21.4% (46 / 215) | 23.2% (91 / 393) |
| Decider Flash v1.2 | 75.8% (441 / 582) | 62.5% (388 / 621) | 65.4% (299 / 457) | 55.8% (246 / 441) | 60.3% (234 / 388) | 67.2% (45 / 67)† | 75.5% (142 / 188)† | 77.7% (254 / 327) |
| Decider v1.1 27B | 48.7% (277 / 569) | 39.7% (297 / 748) | 31.4% (150 / 478) | 66.8% (185 / 277) | 48.8% (145 / 297) | 49.2% (29 / 59)† | 44.9% (79 / 176)† | 50.6% (169 / 334) |
| Decider v1.2 27B | 58.9% (354 / 601) | 49.8% (353 / 709) | 52.3% (215 / 411) | 60.7% (215 / 354) | 52.4% (185 / 353) | 63.9% (46 / 72)† | 55.5% (106 / 191)† | 59.8% (202 / 338) |
| Fastino GLiDE | 55.0% (394 / 716) | 48.2% (418 / 868) | 44.3% (211 / 476) | 58.4% (230 / 394) | 56.0% (234 / 418) | 47.8% (43 / 90)† | 51.0% (126 / 247) | 59.4% (225 / 379) |
| Fastino GLiDE v1.2 (local) | 61.5% (394 / 641) | 54.2% (422 / 778) | 50.4% (250 / 496) | 61.4% (242 / 394) | 49.8% (210 / 422) | 63.3% (50 / 79)† | 55.8% (121 / 217) | 64.6% (223 / 345) |
| GPT-6 Luna | 43.7% (311 / 711) | 36.2% (251 / 694) | 52.5% (276 / 526) | 65.6% (204 / 311) | 47.4% (119 / 251) | 43.0% (34 / 79)† | 38.3% (87 / 227) | 46.9% (190 / 405) |
| Jev 1.13.0 | 52.4% (345 / 659) | 33.7% (258 / 765) | 44.0% (187 / 425) | 64.3% (222 / 345) | 43.4% (112 / 258) | 45.7% (32 / 70)† | 49.2% (90 / 183)† | 54.9% (223 / 406) |
| Jev 1.14.0 | 49.2% (367 / 746) | 37.0% (278 / 752) | 45.1% (204 / 452) | 61.9% (227 / 367) | 43.2% (120 / 278) | 40.0% (32 / 80)† | 47.9% (114 / 238) | 51.6% (221 / 428) |
| LFM2.5-24B-A2B (off) | 63.9% (322 / 504) | 57.4% (333 / 580) | 51.4% (222 / 432) | 60.6% (195 / 322) | 52.3% (174 / 333) | 77.0% (47 / 61)† | 55.8% (87 / 156)† | 65.5% (188 / 287) |
| Mercury Decide | 15.3% (102 / 667) | 13.1% (83 / 634) | 19.1% (98 / 513) | 59.8% (61 / 102)† | 21.7% (18 / 83)† | 16.7% (10 / 60)† | 18.8% (39 / 208) | 13.3% (53 / 399) |
| Open-Jev 27B v1.1 | 99.2% (720 / 726) | 97.4% (782 / 803) | 96.9% (530 / 547) | 46.2% (333 / 720) | 55.2% (432 / 782) | 98.8% (84 / 85)† | 98.7% (231 / 234) | 99.5% (405 / 407) |
| SubQ Snap Preview | 53.6% (408 / 761) | 46.8% (408 / 872) | 49.6% (260 / 524) | 45.8% (187 / 408) | 43.4% (177 / 408) | 50.5% (47 / 93)† | 56.5% (131 / 232) | 52.8% (230 / 436) |
| Winnow-12B | 41.9% (306 / 730) | 38.6% (265 / 687) | 45.8% (230 / 502) | 52.9% (162 / 306) | 48.3% (128 / 265) | 58.4% (45 / 77)† | 42.1% (99 / 235) | 38.8% (162 / 418) |

#### Margin 0.001: missed risks in Risk pays positions whose candidates are a safe play and a riskier one

| Setup | group | close choices: missed ÷ n | other: missed ÷ n | crude difference [95%] | adjusted: close | adjusted: other (standardised) | adjusted difference [95%] | close choices covered | resamples left out (crude / adjusted) |
|---|---|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 484 | 55.3% (68 / 123)† | 80.9% (292 / 361) | -25.6 pts [-35.5, -16.0] | 54.5% | 82.6% | -28.0 pts [-37.6, -16.4] | 98.4% (121 / 123)† | 0 / 0 |
| Clef | 369 | 56.7% (185 / 326) | 55.8% (24 / 43)† | +0.9 pts [-12.6, +11.7] | 59.0% | 62.3% | -3.4 pts [-21.4, +15.5] | 77.0% (251 / 326) | 0 / 0 |
| Cygnet (Gemma 4 12B) | 465 | 47.7% (42 / 88)† | 77.7% (293 / 377) | -30.0 pts [-37.4, -22.1] | 47.7% | 79.0% | -31.3 pts [-41.4, -22.4] | 97.7% (86 / 88)† | 0 / 0 |
| Decider Flash v1.2 | 344 | 55.7% (137 / 246) | 74.5% (73 / 98)† | -18.8 pts [-30.0, -7.2] | 55.2% | 73.7% | -18.4 pts [-32.5, -5.0] | 97.2% (239 / 246) | 0 / 0 |
| Decider v1.1 27B | 393 | 58.4% (108 / 185)† | 72.6% (151 / 208) | -14.2 pts [-22.4, -6.0] | 59.3% | 72.9% | -13.6 pts [-22.5, -3.0] | 95.7% (177 / 185)† | 0 / 0 |
| Decider v1.2 27B | 397 | 55.8% (120 / 215) | 70.3% (128 / 182)† | -14.5 pts [-24.8, -5.8] | 55.6% | 65.9% | -10.3 pts [-21.2, -1.3] | 99.5% (214 / 215) | 0 / 0 |
| Fastino GLiDE | 424 | 47.8% (110 / 230) | 69.6% (135 / 194)† | -21.8 pts [-30.4, -14.2] | 48.4% | 69.7% | -21.3 pts [-32.8, -11.9] | 95.2% (219 / 230) | 0 / 0 |
| Fastino GLiDE v1.2 (local) | 411 | 64.5% (156 / 242) | 66.3% (112 / 169)† | -1.8 pts [-10.6, +8.1] | 65.8% | 74.9% | -9.1 pts [-18.6, +3.0] | 96.7% (234 / 242) | 0 / 0 |
| GPT-6 Luna | 502 | 57.8% (118 / 204) | 80.5% (240 / 298) | -22.7 pts [-28.6, -17.1] | 57.9% | 77.6% | -19.7 pts [-28.0, -13.2] | 99.0% (202 / 204) | 0 / 0 |
| Jev 1.13.0 | 444 | 58.1% (129 / 222) | 80.2% (178 / 222) | -22.1 pts [-29.1, -14.8] | 57.5% | 79.9% | -22.4 pts [-28.9, -14.5] | 98.6% (219 / 222) | 0 / 0 |
| Jev 1.14.0 | 494 | 57.7% (131 / 227) | 80.9% (216 / 267) | -23.2 pts [-31.8, -14.8] | 57.8% | 78.3% | -20.4 pts [-30.3, -12.9] | 98.2% (223 / 227) | 0 / 0 |
| LFM2.5-24B-A2B (off) | 336 | 60.5% (118 / 195)† | 80.1% (113 / 141)† | -19.6 pts [-29.3, -9.1] | 60.0% | 84.4% | -24.4 pts [-34.4, -12.7] | 97.4% (190 / 195)† | 0 / 0 |
| Mercury Decide | 453 | 54.1% (33 / 61)† | 80.1% (314 / 392) | -26.0 pts [-36.5, -14.2] | 55.9% | 77.1% | -21.1 pts [-34.3, -11.3] | 96.7% (59 / 61)† | 0 / 0 |
| Open-Jev 27B v1.1 | 333 | 56.5% (188 / 333) | N/A (0 / 0) | N/A: no other decisions in this group | N/A | N/A | N/A | — | — |
| SubQ Snap Preview | 379 | 52.9% (99 / 187)† | 68.2% (131 / 192)† | -15.3 pts [-25.1, -3.7] | 52.5% | 67.3% | -14.8 pts [-28.1, -0.6] | 96.8% (181 / 187)† | 0 / 0 |
| Winnow-12B | 426 | 59.9% (97 / 162)† | 67.4% (178 / 264) | -7.5 pts [-16.3, +1.8] | 59.7% | 69.2% | -9.5 pts [-19.6, +1.8] | 98.1% (159 / 162)† | 0 / 0 |

#### Margin 0.02: close choices by position class and by stake band (Risk pays only)

| Setup | Risk pays: close ÷ eligible | Safety pays: close ÷ eligible | No trade-off: close ÷ eligible | Risk pays: risk close ÷ close | Safety pays: risk close ÷ close | small stake | medium stake | big stake |
|---|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 29.2% (183 / 626) | 24.2% (229 / 948) | 38.5% (185 / 481) | 59.6% (109 / 183)† | 35.8% (82 / 229) | N/A (0 / 0) | 28.1% (64 / 228) | 29.9% (119 / 398) |
| Clef | 89.9% (587 / 653) | 84.4% (754 / 893) | 83.6% (378 / 452) | 47.9% (281 / 587) | 61.4% (463 / 754) | N/A (0 / 0) | 89.9% (205 / 228) | 89.9% (382 / 425) |
| Cygnet (Gemma 4 12B) | 22.5% (137 / 608) | 20.6% (158 / 767) | 21.9% (103 / 471) | 59.1% (81 / 137)† | 43.0% (68 / 158)† | N/A (0 / 0) | 21.4% (46 / 215) | 23.2% (91 / 393) |
| Decider Flash v1.2 | 76.9% (396 / 515) | 62.9% (433 / 688) | 65.4% (299 / 457) | 56.1% (222 / 396) | 59.6% (258 / 433) | N/A (0 / 0) | 75.5% (142 / 188)† | 77.7% (254 / 327) |
| Decider v1.1 27B | 48.6% (248 / 510) | 40.4% (326 / 807) | 31.4% (150 / 478) | 67.7% (168 / 248) | 49.7% (162 / 326) | N/A (0 / 0) | 44.9% (79 / 176)† | 50.6% (169 / 334) |
| Decider v1.2 27B | 58.2% (308 / 529) | 51.1% (399 / 781) | 52.3% (215 / 411) | 61.4% (189 / 308) | 52.9% (211 / 399) | N/A (0 / 0) | 55.5% (106 / 191)† | 59.8% (202 / 338) |
| Fastino GLiDE | 56.1% (351 / 626) | 48.1% (461 / 958) | 44.3% (211 / 476) | 58.4% (205 / 351) | 56.2% (259 / 461) | N/A (0 / 0) | 51.0% (126 / 247) | 59.4% (225 / 379) |
| Fastino GLiDE v1.2 (local) | 61.2% (344 / 562) | 55.1% (472 / 857) | 50.4% (250 / 496) | 61.6% (212 / 344) | 50.8% (240 / 472) | N/A (0 / 0) | 55.8% (121 / 217) | 64.6% (223 / 345) |
| GPT-6 Luna | 43.8% (277 / 632) | 36.9% (285 / 773) | 52.5% (276 / 526) | 67.5% (187 / 277) | 47.7% (136 / 285) | N/A (0 / 0) | 38.3% (87 / 227) | 46.9% (190 / 405) |
| Jev 1.13.0 | 53.1% (313 / 589) | 34.7% (290 / 835) | 44.0% (187 / 425) | 64.5% (202 / 313) | 45.5% (132 / 290) | N/A (0 / 0) | 49.2% (90 / 183)† | 54.9% (223 / 406) |
| Jev 1.14.0 | 50.3% (335 / 666) | 37.3% (310 / 832) | 45.1% (204 / 452) | 60.6% (203 / 335) | 46.5% (144 / 310) | N/A (0 / 0) | 47.9% (114 / 238) | 51.6% (221 / 428) |
| LFM2.5-24B-A2B (off) | 62.1% (275 / 443) | 59.3% (380 / 641) | 51.4% (222 / 432) | 60.4% (166 / 275) | 53.4% (203 / 380) | N/A (0 / 0) | 55.8% (87 / 156)† | 65.5% (188 / 287) |
| Mercury Decide | 15.2% (92 / 607) | 13.4% (93 / 694) | 19.1% (98 / 513) | 62.0% (57 / 92)† | 23.7% (22 / 93)† | N/A (0 / 0) | 18.8% (39 / 208) | 13.3% (53 / 399) |
| Open-Jev 27B v1.1 | 99.2% (636 / 641) | 97.5% (866 / 888) | 96.9% (530 / 547) | 44.5% (283 / 636) | 55.7% (482 / 866) | N/A (0 / 0) | 98.7% (231 / 234) | 99.5% (405 / 407) |
| SubQ Snap Preview | 54.0% (361 / 668) | 47.2% (455 / 965) | 49.6% (260 / 524) | 46.0% (166 / 361) | 43.5% (198 / 455) | N/A (0 / 0) | 56.5% (131 / 232) | 52.8% (230 / 436) |
| Winnow-12B | 40.0% (261 / 653) | 40.6% (310 / 764) | 45.8% (230 / 502) | 51.7% (135 / 261) | 50.0% (155 / 310) | N/A (0 / 0) | 42.1% (99 / 235) | 38.8% (162 / 418) |

#### Margin 0.02: missed risks in Risk pays positions whose candidates are a safe play and a riskier one

| Setup | group | close choices: missed ÷ n | other: missed ÷ n | crude difference [95%] | adjusted: close | adjusted: other (standardised) | adjusted difference [95%] | close choices covered | resamples left out (crude / adjusted) |
|---|---|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 424 | 54.1% (59 / 109)† | 80.0% (252 / 315) | -25.9 pts [-37.4, -15.1] | 52.9% | 81.6% | -28.7 pts [-39.1, -15.8] | 95.4% (104 / 109)† | 0 / 0 |
| Clef | 317 | 56.6% (159 / 281) | 52.8% (19 / 36)† | +3.8 pts [-12.3, +18.3] | 59.1% | 59.2% | -0.1 pts [-20.3, +26.2] | 76.5% (215 / 281) | 0 / 0 |
| Cygnet (Gemma 4 12B) | 420 | 45.7% (37 / 81)† | 76.1% (258 / 339) | -30.4 pts [-39.4, -21.1] | 46.2% | 77.3% | -31.0 pts [-43.3, -20.0] | 98.8% (80 / 81)† | 0 / 0 |
| Decider Flash v1.2 | 303 | 55.4% (123 / 222) | 75.3% (61 / 81)† | -19.9 pts [-32.0, -7.7] | 55.5% | 74.2% | -18.7 pts [-33.1, -4.4] | 98.2% (218 / 222) | 0 / 0 |
| Decider v1.1 27B | 353 | 58.3% (98 / 168)† | 73.0% (135 / 185)† | -14.6 pts [-23.7, -4.8] | 59.4% | 73.0% | -13.6 pts [-22.6, -2.0] | 95.2% (160 / 168)† | 0 / 0 |
| Decider v1.2 27B | 352 | 57.1% (108 / 189)† | 70.6% (115 / 163)† | -13.4 pts [-22.2, -4.9] | 57.1% | 66.7% | -9.5 pts [-19.5, -0.8] | 100.0% (189 / 189)† | 0 / 0 |
| Fastino GLiDE | 364 | 46.8% (96 / 205) | 66.7% (106 / 159)† | -19.8 pts [-29.5, -10.7] | 46.7% | 68.8% | -22.1 pts [-33.3, -12.0] | 96.1% (197 / 205) | 0 / 0 |
| Fastino GLiDE v1.2 (local) | 358 | 65.1% (138 / 212) | 65.8% (96 / 146)† | -0.7 pts [-11.0, +10.6] | 66.3% | 74.1% | -7.8 pts [-17.4, +5.5] | 96.7% (205 / 212) | 0 / 0 |
| GPT-6 Luna | 453 | 58.3% (109 / 187)† | 79.3% (211 / 266) | -21.0 pts [-26.8, -15.3] | 58.4% | 77.0% | -18.7 pts [-26.6, -11.9] | 98.9% (185 / 187)† | 0 / 0 |
| Jev 1.13.0 | 400 | 57.9% (117 / 202) | 78.3% (155 / 198)† | -20.4 pts [-27.7, -12.3] | 57.3% | 79.2% | -21.9 pts [-29.1, -13.9] | 98.5% (199 / 202) | 0 / 0 |
| Jev 1.14.0 | 433 | 57.6% (117 / 203) | 80.0% (184 / 230) | -22.4 pts [-31.7, -13.8] | 57.5% | 77.2% | -19.7 pts [-31.1, -11.3] | 98.5% (200 / 203) | 0 / 0 |
| LFM2.5-24B-A2B (off) | 297 | 59.6% (99 / 166)† | 80.9% (106 / 131)† | -21.3 pts [-29.9, -11.7] | 59.3% | 84.6% | -25.3 pts [-34.9, -12.7] | 97.6% (162 / 166)† | 0 / 0 |
| Mercury Decide | 424 | 52.6% (30 / 57)† | 79.8% (293 / 367) | -27.2 pts [-38.6, -16.1] | 54.5% | 76.5% | -21.9 pts [-35.7, -11.5] | 96.5% (55 / 57)† | 0 / 0 |
| Open-Jev 27B v1.1 | 283 | 56.2% (159 / 283) | N/A (0 / 0) | N/A: no other decisions in this group | N/A | N/A | N/A | — | — |
| SubQ Snap Preview | 323 | 53.6% (89 / 166)† | 65.6% (103 / 157)† | -12.0 pts [-23.9, +0.3] | 53.7% | 66.3% | -12.6 pts [-25.7, +3.9] | 97.6% (162 / 166)† | 0 / 0 |
| Winnow-12B | 379 | 61.5% (83 / 135)† | 66.0% (161 / 244) | -4.5 pts [-13.8, +5.8] | 61.1% | 66.9% | -5.8 pts [-17.7, +7.6] | 97.0% (131 / 135)† | 0 / 0 |

## Reading limits

- These are probabilities over plays, not sampled reasoning. They say nothing about how a model reasoned or why it chose.
- Setups played different positions, so comparisons across setups are not paired.
- The missed-risk comparison is conditional on the recorded decisions in group G, which differs per setup. The adjusted figure accounts only for phase, number of options and the engine gap.
