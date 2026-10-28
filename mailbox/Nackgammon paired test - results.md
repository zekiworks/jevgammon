# Nackgammon paired test: results

2026-10-28 · Method §10 (`tools/site/content/method-spec-2026-10-24.md`, with the addenda of 2026-10-27, §10.14 and its
dated correction (f) of 2026-10-28). Brief: `mailbox/Nackgammon and Terra - brief 2026-10-27.md`. Saved scores:
`positions/nack-paired/results/results.json` (sha256 `0832f78d6e9dd85751013f62b0159ae67fbbc627751761865a5c9e977326e8dd`; the scorer's output of 2026-10-28 with one text field,
`groups_rule`, corrected by a string edit on 2026-10-28; every number unchanged). This report is assembled from that
file by data key (`tools/v3/nack_paired_report.py`; `verify` checks every table cell against it).

**Scope:** These results hold for these rosters only; each group is the setups in the run from that original league. The frontier group currently has 1 setup (GPT-6 Astra (on)); comparisons 2 and 3 rest on it.

**Groups and disclosure:** Groups by original league (Method §10.14, amendment of 2026-10-27). Method §10 and its notes were committed before any model call, and the per-setup first looks were computed under the frozen extension rule. Separately, before the amendment, six full-report calls were issued on partial data under the earlier group definitions; that all six completed successfully has not been independently established. One returned numeric old-group primary results into the site agent's context before the amendment. Whether a person saw them, and any causation, is not established. Nothing was published before the amendment; the aggregate report and data were pushed to the public repository in commit 3e4f413 on 2026-10-28 (01:03 UTC), before release approval. See §10.14(e) and its dated correction (f) of 2026-10-28.

What this measures: how much a new starting setup (same rules) changes each setup's (model, settings and prompt)
decision quality. A larger drop is consistent with relying on familiar positions but is not proof, because Nackgammon
positions also differ in structure. "Kept" is a valid result. The paired test's standard prompt (`bg-v3-std-notable`)
differs from the league prompt (no opening table; the setup sentence on its own line), so the standard error rates
here are not compared directly with league error rates. **Random is slightly better on Nackgammon** on these pairs: its
own drop is shown next to every result.

## What ran

- 24 asked setups: 12 decision models, 9 workhorses, 1 frontier setup (original leagues, §10.14), GPT-6.1 Terra (no
  group, exploratory; passed its smoke test, 50/50 valid, 9.8 PR) and GNUbg weak (yardstick). **Random** (yardstick)
  is computed exactly from GNUbg's 2-ply values (mean loss over all legal plays): it was never asked and is not
  subject to the stopping rule; it is reported on the main 200 pairs and on all 500.
- Every asked setup was asked the main 400 positions (200 pairs). Every first look was "unclear" (97.5% intervals
  about ±4 to ±18 PR), so the frozen rule sent every asked setup the 300 reserve pairs (600 positions). **Each asked
  setup has 1,000 recorded positions.** For 23 setups all 1,000 hold a valid answer. **LFM2.5-24B-A2B (on)** has 107
  records without a choice (timed out at the 600 s limit: 38 of the main 400, 69 of the reserve 600; scored split
  52 Nackgammon / 55 standard positions over all 500 pairs, 16 / 22 on the main 200). These are never dropped: they score the
  position's Random error (primary rule), with both sensitivity checks below. Usual retries only, no re-asks.
- Raw answers, logs and the per-attempt ledgers are kept privately; a release bundle is prepared locally and not published.

## Per setup

Standard, Nackgammon and the drop together; not a ranking (rows by group, then standard PR). Drop = Nackgammon PR −
standard PR on the same pairs (positive = worse on Nackgammon). First look on the main 200 pairs, final look on all 500.
Label from the final 97.5% interval. Bootstrap intervals are approximate.

| Setup | Group | Standard PR (200) | Nackgammon PR (200) | Drop [97.5%] (200) | Random's drop (200) | Standard / Nackgammon PR (500) | Drop [97.5%] (500) | Random's drop (500) | Asked the reserve under the rule | Label (final) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 22.74 | 24.91 | +2.18 [-7.3, +11.9] | -4.56 | 26.33 / 27.93 | +1.60 [-5.3, +8.3] | -3.73 | yes | unclear |
| Jev 1.13.0 | decision models | 26.53 | 24.17 | -2.37 [-17.7, +10.0] | -4.56 | 24.67 / 27.44 | +2.77 [-5.2, +10.4] | -3.73 | yes | unclear |
| GPT-6 Luna | decision models | 28.27 | 34.11 | +5.84 [-10.6, +20.5] | -4.56 | 29.56 / 35.44 | +5.87 [-4.3, +15.1] | -3.73 | yes | unclear |
| Celeris-1 Decision | decision models | 29.71 | 28.47 | -1.24 [-18.3, +14.6] | -4.56 | 26.86 / 30.93 | +4.08 [-4.6, +12.6] | -3.73 | yes | unclear |
| Decider v1.1 27B | decision models | 30.42 | 28.64 | -1.78 [-17.3, +11.9] | -4.56 | 31.27 / 32.08 | +0.81 [-8.0, +9.2] | -3.73 | yes | unclear |
| Cygnet (Gemma 4 12B) | decision models | 31.33 | 24.48 | -6.85 [-22.4, +5.4] | -4.56 | 28.46 / 28.66 | +0.20 [-7.6, +7.4] | -3.73 | yes | unclear |
| SubQ Snap Preview | decision models | 31.91 | 29.66 | -2.25 [-18.1, +11.9] | -4.56 | 31.25 / 32.87 | +1.62 [-7.1, +10.1] | -3.73 | yes | unclear |
| Mercury Decide | decision models | 32.74 | 28.46 | -4.28 [-20.1, +8.8] | -4.56 | 31.34 / 34.08 | +2.73 [-5.9, +10.8] | -3.73 | yes | unclear |
| Winnow-12B | decision models | 34.33 | 33.43 | -0.89 [-18.0, +15.0] | -4.56 | 31.93 / 34.61 | +2.68 [-6.3, +11.2] | -3.73 | yes | unclear |
| Decider v1.2 27B | decision models | 34.68 | 22.80 | -11.87 [-27.9, +1.0] | -4.56 | 31.72 / 29.03 | -2.68 [-11.0, +5.2] | -3.73 | yes | unclear |
| Decider Flash v1.2 | decision models | 39.77 | 42.86 | +3.09 [-12.1, +20.1] | -4.56 | 40.23 / 48.01 | +7.78 [-2.2, +18.4] | -3.73 | yes | unclear |
| Open-Jev 27B v1.1 | decision models | 52.08 | 40.96 | -11.12 [-29.5, +6.8] | -4.56 | 47.07 / 43.99 | -3.08 [-13.3, +6.8] | -3.73 | yes | unclear |
| GPT-6.1 Sol (high) | workhorses | 9.88 | 8.43 | -1.45 [-5.6, +2.7] | -4.56 | 11.14 / 9.12 | -2.03 [-5.6, +1.4] | -3.73 | yes | unclear |
| GPT-6.1 Sol (low) | workhorses | 11.15 | 9.90 | -1.26 [-5.7, +3.3] | -4.56 | 12.21 / 10.75 | -1.46 [-5.0, +2.0] | -3.73 | yes | unclear |
| Claude Sonnet 5.5 (low) | workhorses | 13.96 | 14.50 | +0.54 [-5.0, +6.0] | -4.56 | 16.45 / 15.30 | -1.15 [-5.9, +3.3] | -3.73 | yes | unclear |
| Gemini 3.8 Flash (low) | workhorses | 15.92 | 11.81 | -4.11 [-9.7, +1.0] | -4.56 | 16.71 / 15.41 | -1.30 [-5.5, +2.9] | -3.73 | yes | unclear |
| Gemma 4 31B (on) | workhorses | 18.35 | 13.38 | -4.97 [-11.8, +1.8] | -4.56 | 17.97 / 16.84 | -1.13 [-6.2, +4.4] | -3.73 | yes | unclear |
| DeepSeek V4.1 Flash (off) | workhorses | 23.91 | 27.90 | +3.98 [-11.7, +18.0] | -4.56 | 23.35 / 29.29 | +5.94 [-2.5, +13.9] | -3.73 | yes | unclear |
| Qwen3.8-27B (off) | workhorses | 28.13 | 28.43 | +0.30 [-14.5, +12.1] | -4.56 | 26.89 / 31.65 | +4.76 [-3.6, +12.5] | -3.73 | yes | unclear |
| LFM2.5-24B-A2B (on) | workhorses | 38.20 | 37.55 | -0.65 [-15.2, +14.4] | -4.56 | 37.78 / 42.54 | +4.77 [-4.1, +13.5] | -3.73 | yes | unclear |
| LFM2.5-24B-A2B (off) | workhorses | 50.75 | 53.98 | +3.23 [-16.9, +22.1] | -4.56 | 46.44 / 50.87 | +4.43 [-6.5, +15.4] | -3.73 | yes | unclear |
| GPT-6 Astra (on) | frontier | 9.66 | 7.30 | -2.37 [-6.7, +1.8] | -4.56 | 10.86 / 8.88 | -1.99 [-5.5, +1.5] | -3.73 | yes | unclear |
| GPT-6.1 Terra | no group (exploratory) | 13.52 | 14.40 | +0.89 [-5.7, +8.6] | -4.56 | 13.18 / 16.22 | +3.04 [-0.9, +7.4] | -3.73 | yes | unclear |
| GNUbg weak | yardstick | 27.69 | 24.13 | -3.56 [-13.9, +7.3] | -4.56 | 25.35 / 20.78 | -4.57 [-10.3, +1.3] | -3.73 | yes | unclear |
| Random | yardstick | 87.45 | 82.89 | -4.56 [-18.0, +7.9] | -4.56 | 85.16 / 81.43 | -3.73 [-11.4, +3.7] | -3.73 | no | unclear |

**Labels:** every asked setup and GNUbg weak is **"unclear"** at the final look (Random too, reported for reference):
every 97.5% interval contains 0 and reaches past ±5 PR. "Unclear" means the interval is too wide to decide; it is
**not** evidence of equivalence ("kept" would need the whole interval within ±5 PR). No setup is "kept", "worse" or
"better" on this evidence.

## Invalid or missing answers and sensitivity

| Setup | Invalid or missing, Nackgammon / standard (200 pairs) | Same (500 pairs) | Primary drop [97.5%] (200) | (i) worst play: drop [97.5%] | (ii) pairs left out: pairs, drop [97.5%] |
| --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 0 / 0 | 0 / 0 | +2.18 [-7.3, +11.9] | +2.18 [-7.3, +11.9] | 200, +2.18 [-7.3, +11.9] |
| Jev 1.13.0 | 0 / 0 | 0 / 0 | -2.37 [-17.7, +10.0] | -2.37 [-17.7, +10.0] | 200, -2.37 [-17.7, +10.0] |
| GPT-6 Luna | 0 / 0 | 0 / 0 | +5.84 [-10.6, +20.5] | +5.84 [-10.6, +20.5] | 200, +5.84 [-10.6, +20.5] |
| Celeris-1 Decision | 0 / 0 | 0 / 0 | -1.24 [-18.3, +14.6] | -1.24 [-18.3, +14.6] | 200, -1.24 [-18.3, +14.6] |
| Decider v1.1 27B | 0 / 0 | 0 / 0 | -1.78 [-17.3, +11.9] | -1.78 [-17.3, +11.9] | 200, -1.78 [-17.3, +11.9] |
| Cygnet (Gemma 4 12B) | 0 / 0 | 0 / 0 | -6.85 [-22.4, +5.4] | -6.85 [-22.4, +5.4] | 200, -6.85 [-22.4, +5.4] |
| SubQ Snap Preview | 0 / 0 | 0 / 0 | -2.25 [-18.1, +11.9] | -2.25 [-18.1, +11.9] | 200, -2.25 [-18.1, +11.9] |
| Mercury Decide | 0 / 0 | 0 / 0 | -4.28 [-20.1, +8.8] | -4.28 [-20.1, +8.8] | 200, -4.28 [-20.1, +8.8] |
| Winnow-12B | 0 / 0 | 0 / 0 | -0.89 [-18.0, +15.0] | -0.89 [-18.0, +15.0] | 200, -0.89 [-18.0, +15.0] |
| Decider v1.2 27B | 0 / 0 | 0 / 0 | -11.87 [-27.9, +1.0] | -11.87 [-27.9, +1.0] | 200, -11.87 [-27.9, +1.0] |
| Decider Flash v1.2 | 0 / 0 | 0 / 0 | +3.09 [-12.1, +20.1] | +3.09 [-12.1, +20.1] | 200, +3.09 [-12.1, +20.1] |
| Open-Jev 27B v1.1 | 0 / 0 | 0 / 0 | -11.12 [-29.5, +6.8] | -11.12 [-29.5, +6.8] | 200, -11.12 [-29.5, +6.8] |
| GPT-6.1 Sol (high) | 0 / 0 | 0 / 0 | -1.45 [-5.6, +2.7] | -1.45 [-5.6, +2.7] | 200, -1.45 [-5.6, +2.7] |
| GPT-6.1 Sol (low) | 0 / 0 | 0 / 0 | -1.26 [-5.7, +3.3] | -1.26 [-5.7, +3.3] | 200, -1.26 [-5.7, +3.3] |
| Claude Sonnet 5.5 (low) | 0 / 0 | 0 / 0 | +0.54 [-5.0, +6.0] | +0.54 [-5.0, +6.0] | 200, +0.54 [-5.0, +6.0] |
| Gemini 3.8 Flash (low) | 0 / 0 | 0 / 0 | -4.11 [-9.7, +1.0] | -4.11 [-9.7, +1.0] | 200, -4.11 [-9.7, +1.0] |
| Gemma 4 31B (on) | 0 / 0 | 0 / 0 | -4.97 [-11.8, +1.8] | -4.97 [-11.8, +1.8] | 200, -4.97 [-11.8, +1.8] |
| DeepSeek V4.1 Flash (off) | 0 / 0 | 0 / 0 | +3.98 [-11.7, +18.0] | +3.98 [-11.7, +18.0] | 200, +3.98 [-11.7, +18.0] |
| Qwen3.8-27B (off) | 0 / 0 | 0 / 0 | +0.30 [-14.5, +12.1] | +0.30 [-14.5, +12.1] | 200, +0.30 [-14.5, +12.1] |
| LFM2.5-24B-A2B (on) | 16 / 22 | 52 / 55 | -0.65 [-15.2, +14.4] | -7.10 [-27.4, +13.3] | 166, +2.32 [-12.3, +18.1] |
| LFM2.5-24B-A2B (off) | 0 / 0 | 0 / 0 | +3.23 [-16.9, +22.1] | +3.23 [-16.9, +22.1] | 200, +3.23 [-16.9, +22.1] |
| GPT-6 Astra (on) | 0 / 0 | 0 / 0 | -2.37 [-6.7, +1.8] | -2.37 [-6.7, +1.8] | 200, -2.37 [-6.7, +1.8] |
| GPT-6.1 Terra | 0 / 0 | 0 / 0 | +0.89 [-5.7, +8.6] | +0.89 [-5.7, +8.6] | 200, +0.89 [-5.7, +8.6] |
| GNUbg weak | 0 / 0 | 0 / 0 | -3.56 [-13.9, +7.3] | -3.56 [-13.9, +7.3] | 200, -3.56 [-13.9, +7.3] |
| Random | 0 / 0 | 0 / 0 | -4.56 [-18.0, +7.9] | -4.56 [-18.0, +7.9] | 200, -4.56 [-18.0, +7.9] |

## By phase

Main 200 pairs, descriptive, 95% intervals.

| Setup | opening | contact | holding | race | bear-off | opening − other phases [95%] |
| --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | +9.2 [-2.3, +20.7] | -10.2 [-28.8, +7.8] | +17.2 [-11.0, +52.4] | +3.4 [-5.6, +14.6] | -4.4 [-9.8, -0.4] | +10.1 [-5.6, +25.6] |
| Jev 1.13.0 | +3.5 [-7.3, +14.0] | -3.6 [-21.5, +13.8] | -21.2 [-97.5, +36.0] | +4.5 [-4.5, +15.5] | +2.4 [-3.1, +11.9] | +8.4 [-10.2, +29.8] |
| GPT-6 Luna | +18.9 [+6.0, +31.4] | -9.5 [-31.2, +11.0] | +4.3 [-74.8, +63.7] | +16.3 [-5.7, +51.1] | +2.6 [-6.0, +13.9] | +18.7 [-2.7, +42.6] |
| Celeris-1 Decision | -9.1 [-26.1, +6.2] | -5.0 [-22.4, +12.2] | +8.5 [-74.2, +83.5] | +12.3 [-7.0, +45.4] | +1.4 [-9.0, +13.6] | -11.2 [-36.4, +14.3] |
| Decider v1.1 27B | +17.7 [+4.3, +31.3] | -13.4 [-30.5, +3.9] | -17.6 [-95.1, +44.3] | +2.4 [-6.0, +13.2] | -6.0 [-14.0, -0.2] | +27.8 [+7.2, +50.6] |
| Cygnet (Gemma 4 12B) | -1.1 [-15.9, +13.2] | -6.7 [-24.7, +11.3] | -35.2 [-109.3, +16.0] | +7.2 [-1.3, +18.1] | -1.1 [-5.9, +4.8] | +8.2 [-12.7, +31.4] |
| SubQ Snap Preview | +7.4 [-6.5, +21.1] | -3.5 [-23.5, +18.4] | -17.9 [-94.9, +42.3] | -2.5 [-8.1, +3.0] | -3.4 [-7.9, -0.1] | +13.8 [-7.2, +37.1] |
| Mercury Decide | +3.5 [-10.1, +15.9] | -17.5 [-35.8, -0.6] | -12.4 [-88.5, +41.1] | +18.1 [-4.7, +52.5] | -3.8 [-8.4, -0.7] | +11.1 [-9.5, +33.4] |
| Winnow-12B | +8.0 [-6.2, +21.7] | -12.1 [-31.8, +7.0] | +3.5 [-84.5, +79.9] | +1.7 [-7.1, +10.2] | -3.0 [-9.4, +3.8] | +12.6 [-10.3, +37.0] |
| Decider v1.2 27B | -0.1 [-13.6, +12.9] | -18.2 [-39.0, +1.1] | -40.1 [-114.0, +16.9] | +0.9 [-9.2, +12.6] | -3.8 [-8.5, -0.5] | +16.8 [-4.0, +39.7] |
| Decider Flash v1.2 | +0.9 [-15.8, +18.4] | -11.4 [-40.8, +18.8] | +28.8 [-24.0, +99.7] | +13.8 [-1.7, +32.9] | +1.8 [-6.8, +11.6] | -3.2 [-29.2, +21.5] |
| Open-Jev 27B v1.1 | -15.9 [-34.9, +3.0] | -27.9 [-63.6, +5.2] | +18.7 [-49.4, +90.1] | -0.6 [-13.6, +12.6] | -5.8 [-13.0, -0.6] | -6.8 [-35.8, +21.7] |
| GPT-6.1 Sol (high) | +0.8 [-6.6, +8.3] | -2.4 [-9.8, +5.0] | -6.3 [-19.6, +3.9] | -0.2 [-1.0, +0.4] | +0.0 [+0.0, +0.0] | +3.2 [-5.1, +12.1] |
| GPT-6.1 Sol (low) | +3.7 [-4.1, +12.1] | -3.7 [-12.3, +4.6] | -6.3 [-19.7, +3.5] | -0.9 [-2.6, +0.3] | -1.6 [-4.8, +0.0] | +7.1 [-1.9, +16.6] |
| Claude Sonnet 5.5 (low) | +4.5 [-3.8, +13.6] | -0.1 [-12.5, +11.7] | -6.1 [-19.3, +3.6] | +1.0 [-3.9, +7.1] | +0.1 [+0.0, +0.2] | +5.6 [-4.3, +16.3] |
| Gemini 3.8 Flash (low) | +1.1 [-5.5, +7.3] | -12.3 [-25.0, -0.1] | -0.9 [-14.6, +10.2] | -2.7 [-6.9, +0.6] | -2.1 [-6.0, +0.0] | +7.4 [-1.5, +16.4] |
| Gemma 4 31B (on) | +0.0 [-9.8, +10.1] | -13.7 [-29.6, +2.2] | -1.5 [-15.2, +9.5] | -3.2 [-6.9, -0.3] | -2.0 [-5.9, +0.1] | +7.1 [-5.2, +19.7] |
| DeepSeek V4.1 Flash (off) | +14.6 [+3.9, +25.4] | -10.6 [-31.1, +9.0] | +15.2 [-64.8, +76.6] | +7.7 [-3.7, +25.0] | -3.5 [-8.3, -0.1] | +15.1 [-4.9, +37.4] |
| Qwen3.8-27B (off) | +13.2 [-0.1, +25.9] | -9.4 [-24.0, +4.8] | -12.4 [-89.0, +41.0] | +4.3 [-4.5, +15.3] | +4.0 [-4.3, +15.0] | +18.4 [-1.2, +40.0] |
| LFM2.5-24B-A2B (on) | +3.2 [-13.6, +21.6] | -24.9 [-54.3, +5.5] | +29.4 [-14.3, +77.6] | +8.0 [-7.2, +27.9] | +3.8 [-4.5, +14.9] | +5.4 [-18.5, +30.0] |
| LFM2.5-24B-A2B (off) | +15.5 [-2.6, +33.8] | -0.0 [-28.2, +29.2] | -14.3 [-107.3, +69.0] | +1.4 [-14.4, +21.5] | +4.5 [-7.0, +17.1] | +17.5 [-10.8, +47.1] |
| GPT-6 Astra (on) | +3.3 [-3.0, +9.7] | -6.5 [-14.9, +1.8] | -8.9 [-22.1, +1.1] | -0.6 [-2.2, +0.4] | +0.0 [+0.0, +0.1] | +8.1 [+0.5, +16.1] |
| GPT-6.1 Terra | +7.4 [+1.1, +13.9] | -6.6 [-18.8, +5.7] | +5.7 [-18.1, +40.1] | +0.1 [-1.0, +1.4] | -1.8 [-5.1, +0.0] | +9.3 [-1.7, +19.6] |
| GNUbg weak | -7.5 [-21.3, +6.5] | -5.8 [-32.0, +20.2] | +3.4 [-12.5, +21.1] | +3.0 [-0.0, +7.8] | -3.6 [-10.5, +0.7] | -5.6 [-23.3, +11.9] |
| Random | -11.3 [-23.3, +0.4] | -9.3 [-27.3, +8.8] | +7.6 [-57.2, +63.1] | +3.4 [-7.7, +16.9] | +0.5 [-5.6, +6.9] | -9.7 [-28.7, +9.8] |

Cost per recorded position over all 1,000 (recorded cost and API-equivalent are never added; 0 = none of that kind; setups on our GPUs have no list price). Recorded cost is the cost stored with each answer: the provider's reported cost per response where the route reports one, otherwise the runner's list-price computation (Mercury Decide; its provider-billed amount is unknown). No invoice was checked.

| Setup | Positions recorded (all) | Recorded cost $ per decision (provider-reported; Mercury Decide: list price) | API-equivalent $ per decision |
| --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 1000 | 0.00000 | 0.00000 |
| Jev 1.13.0 | 1000 | 0.00013 | 0.00000 |
| GPT-6 Luna | 1000 | 0.00027 | 0.00000 |
| Celeris-1 Decision | 1000 | 0.00011 | 0.00000 |
| Decider v1.1 27B | 1000 | 0.00006 | 0.00000 |
| Cygnet (Gemma 4 12B) | 1000 | 0.00000 | 0.00000 |
| SubQ Snap Preview | 1000 | 0.00014 | 0.00000 |
| Mercury Decide | 1000 | 0.00006 | 0.00000 |
| Winnow-12B | 1000 | 0.00000 | 0.00000 |
| Decider v1.2 27B | 1000 | 0.00006 | 0.00000 |
| Decider Flash v1.2 | 1000 | 0.00003 | 0.00000 |
| Open-Jev 27B v1.1 | 1000 | 0.00000 | 0.00000 |
| GPT-6.1 Sol (high) | 1000 | 0.00807 | 0.00000 |
| GPT-6.1 Sol (low) | 1000 | 0.00602 | 0.00000 |
| Claude Sonnet 5.5 (low) | 1000 | 0.00873 | 0.00000 |
| Gemini 3.8 Flash (low) | 1000 | 0.00288 | 0.00000 |
| Gemma 4 31B (on) | 1000 | 0.00000 | 0.00000 |
| DeepSeek V4.1 Flash (off) | 1000 | 0.00027 | 0.00000 |
| Qwen3.8-27B (off) | 1000 | 0.00000 | 0.00000 |
| LFM2.5-24B-A2B (on) | 1000 | 0.00000 | 0.00000 |
| LFM2.5-24B-A2B (off) | 1000 | 0.00000 | 0.00000 |
| GPT-6 Astra (on) | 1000 | 0.02951 | 0.00000 |
| GPT-6.1 Terra | 1000 | 0.00371 | 0.00000 |
| GNUbg weak | 1000 | 0.00000 | 0.00000 |

By game-plan tag: PR per tag and set in `results.json` (`setups.<name>.tags`; descriptive, tags are not matched; the
back-game row is too thin to read, 10 Nackgammon against 2 standard, and partly reflects Nackgammon's starting anchors).

## Primary comparisons

Main 200 pairs, M = 5, each interval at 99%.

Groups by original league (Method §10.14, amendment of 2026-10-27). Method §10 and its notes were committed before any model call, and the per-setup first looks were computed under the frozen extension rule. Separately, before the amendment, six full-report calls were issued on partial data under the earlier group definitions; that all six completed successfully has not been independently established. One returned numeric old-group primary results into the site agent's context before the amendment. Whether a person saw them, and any causation, is not established. Nothing was published before the amendment; the aggregate report and data were pushed to the public repository in commit 3e4f413 on 2026-10-28 (01:03 UTC), before release approval. See §10.14(e) and its dated correction (f) of 2026-10-28.

The frontier group currently has 1 setup (GPT-6 Astra (on)); comparisons 2 and 3 rest on it. These results hold for these rosters only; each group is the setups in the run from that original league.

**Primary rule: an invalid or missing answer scores the position's Random error.**

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop (200) |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 23.36 / 22.88 / -0.49 | -2.14 [-10.07, +4.88] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.64, +12.04] | -4.56 |
| workhorses − frontier | 23.36 / 22.88 / -0.49 | 9.66 / 7.30 / -2.37 | +1.88 [-5.73, +9.33] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 38.20 / 37.55 / -0.65 | 50.75 / 53.98 / +3.23 | -3.88 [-26.98, +21.76] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.00, +2.63] | -4.56 |

**Sensitivity (i): an invalid or missing answer scores the worst legal play's loss.**

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop (200) |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 24.90 / 23.70 / -1.20 | -1.43 [-9.56, +5.66] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.64, +12.04] | -4.56 |
| workhorses − frontier | 24.90 / 23.70 / -1.20 | 9.66 / 7.30 / -2.37 | +1.17 [-6.49, +8.72] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 52.06 / 44.97 / -7.10 | 50.75 / 53.98 / +3.23 | -10.33 [-38.92, +19.74] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.00, +2.63] | -4.56 |

**Sensitivity (ii): the setup's pairs with an invalid or missing answer left out.**

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop (200) |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 22.52 / 22.36 / -0.16 | -2.47 [-10.57, +4.72] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.64, +12.04] | -4.56 |
| workhorses − frontier | 22.52 / 22.36 / -0.16 | 9.66 / 7.30 / -2.37 | +2.21 [-5.45, +9.55] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 30.59 / 32.91 / +2.32 | 50.75 / 53.98 / +3.23 | -0.91 [-24.13, +25.20] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.00, +2.63] | -4.56 |

No primary interval excludes 0, under the primary rule or either sensitivity rule.

## Secondary 1: kept advantage over random play

Labelled secondary. K = (Random's Nackgammon PR − setup's Nackgammon PR) ÷ (Random's standard PR − setup's standard
PR); 1 = keeps its whole advantage over random play.

**Main 200 pairs.**

| Setup | K [95%] | Standard advantage over Random (PR) [95%] | Unstable |
| --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 0.90 [0.73, 1.09] | 64.7 [52.9, 77.5] | no |
| Jev 1.13.0 | 0.96 [0.80, 1.16] | 60.9 [50.6, 71.4] | no |
| GPT-6 Luna | 0.82 [0.64, 1.03] | 59.2 [49.1, 69.5] | no |
| Celeris-1 Decision | 0.94 [0.76, 1.15] | 57.7 [47.5, 68.7] | no |
| Decider v1.1 27B | 0.95 [0.76, 1.17] | 57.0 [46.9, 67.5] | no |
| Cygnet (Gemma 4 12B) | 1.04 [0.86, 1.27] | 56.1 [46.1, 66.5] | no |
| SubQ Snap Preview | 0.96 [0.76, 1.19] | 55.5 [45.3, 66.1] | no |
| Mercury Decide | 0.99 [0.81, 1.21] | 54.7 [45.1, 65.0] | no |
| Winnow-12B | 0.93 [0.74, 1.16] | 53.1 [43.3, 63.1] | no |
| Decider v1.2 27B | 1.14 [0.93, 1.39] | 52.8 [42.9, 62.9] | no |
| Decider Flash v1.2 | 0.84 [0.58, 1.16] | 47.7 [36.5, 60.4] | no |
| Open-Jev 27B v1.1 | 1.19 [0.84, 1.83] | 35.4 [23.0, 48.6] | no |
| GPT-6.1 Sol (high) | 0.96 [0.82, 1.11] | 77.6 [65.5, 90.8] | no |
| GPT-6.1 Sol (low) | 0.96 [0.81, 1.12] | 76.3 [64.2, 89.4] | no |
| Claude Sonnet 5.5 (low) | 0.93 [0.78, 1.10] | 73.5 [61.6, 86.2] | no |
| Gemini 3.8 Flash (low) | 0.99 [0.83, 1.18] | 71.5 [59.3, 84.6] | no |
| Gemma 4 31B (on) | 1.01 [0.84, 1.21] | 69.1 [57.1, 82.1] | no |
| DeepSeek V4.1 Flash (off) | 0.87 [0.71, 1.05] | 63.5 [53.1, 74.3] | no |
| Qwen3.8-27B (off) | 0.92 [0.76, 1.10] | 59.3 [49.5, 69.7] | no |
| LFM2.5-24B-A2B (on) | 0.92 [0.68, 1.22] | 49.2 [38.3, 61.5] | no |
| LFM2.5-24B-A2B (off) | 0.79 [0.51, 1.19] | 36.7 [25.6, 47.9] | no |
| GPT-6 Astra (on) | 0.97 [0.83, 1.13] | 77.8 [65.5, 90.8] | no |
| GPT-6.1 Terra | 0.93 [0.78, 1.10] | 73.9 [61.8, 86.8] | no |
| GNUbg weak | 0.98 [0.77, 1.25] | 59.8 [47.6, 72.8] | no |

**All 500 pairs.**

| Setup | K [95%] | Standard advantage over Random (PR) [95%] | Unstable |
| --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 0.91 [0.79, 1.05] | 58.8 [52.1, 65.7] | no |
| Jev 1.13.0 | 0.89 [0.80, 1.00] | 60.5 [54.0, 67.1] | no |
| GPT-6 Luna | 0.83 [0.72, 0.96] | 55.6 [49.0, 62.2] | no |
| Celeris-1 Decision | 0.87 [0.76, 0.99] | 58.3 [51.6, 65.1] | no |
| Decider v1.1 27B | 0.92 [0.80, 1.05] | 53.9 [47.4, 60.5] | no |
| Cygnet (Gemma 4 12B) | 0.93 [0.83, 1.05] | 56.7 [50.3, 63.4] | no |
| SubQ Snap Preview | 0.90 [0.78, 1.03] | 53.9 [47.3, 60.5] | no |
| Mercury Decide | 0.88 [0.77, 1.01] | 53.8 [47.3, 60.3] | no |
| Winnow-12B | 0.88 [0.77, 1.01] | 53.2 [46.8, 59.8] | no |
| Decider v1.2 27B | 0.98 [0.84, 1.14] | 53.4 [46.7, 60.4] | no |
| Decider Flash v1.2 | 0.74 [0.59, 0.92] | 44.9 [37.9, 52.1] | no |
| Open-Jev 27B v1.1 | 0.98 [0.81, 1.23] | 38.1 [30.7, 45.5] | no |
| GPT-6.1 Sol (high) | 0.98 [0.88, 1.08] | 74.0 [66.8, 81.5] | no |
| GPT-6.1 Sol (low) | 0.97 [0.87, 1.08] | 73.0 [65.8, 80.4] | no |
| Claude Sonnet 5.5 (low) | 0.96 [0.86, 1.08] | 68.7 [61.6, 76.2] | no |
| Gemini 3.8 Flash (low) | 0.96 [0.86, 1.08] | 68.5 [61.3, 75.9] | no |
| Gemma 4 31B (on) | 0.96 [0.85, 1.08] | 67.2 [60.1, 74.6] | no |
| DeepSeek V4.1 Flash (off) | 0.84 [0.75, 0.95] | 61.8 [55.2, 68.5] | no |
| Qwen3.8-27B (off) | 0.85 [0.76, 0.96] | 58.3 [52.0, 64.5] | no |
| LFM2.5-24B-A2B (on) | 0.82 [0.68, 0.98] | 47.4 [40.6, 54.2] | no |
| LFM2.5-24B-A2B (off) | 0.79 [0.61, 1.00] | 38.7 [31.8, 45.6] | no |
| GPT-6 Astra (on) | 0.98 [0.88, 1.08] | 74.3 [67.1, 81.8] | no |
| GPT-6.1 Terra | 0.91 [0.81, 1.01] | 72.0 [64.8, 79.5] | no |
| GNUbg weak | 1.01 [0.88, 1.16] | 59.8 [52.5, 67.4] | no |

## Secondary 2: ranking

Labelled secondary. Model setups only (yardsticks left out).

| Model setups | Spearman ρ [95%] |
| --- | --- |
| 23 | 0.87 [0.73, 0.91] |

Five largest rank changes (1 = lowest error rate; ties by name).

| Setup | Standard rank | Nackgammon rank | Change |
| --- | --- | --- | --- |
| Decider v1.2 27B | 19 | 8 | -11 |
| GPT-6 Luna | 12 | 19 | +7 |
| Cygnet (Gemma 4 12B) | 15 | 10 | -5 |
| DeepSeek V4.1 Flash (off) | 9 | 12 | +3 |
| Fastino GLiDE v1.2 (local) | 8 | 11 | +3 |

## Secondary 3: risk

Labelled secondary. Main 200 pairs; invalid or missing answers with Random's weights; d′ ability, c caution (§2 rules).

| Setup | Risk pays / Safety pays positions, Nackgammon; standard | d′ standard | d′ Nackgammon | Δd′ [95%] | c standard | c Nackgammon | Δc [95%] | Thin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 66 / 66; 66 / 66 | 0.82 | 0.37 | -0.45 [-1.15, +0.19] | 0.60 | 0.65 | +0.05 [-0.29, +0.38] | no |
| Jev 1.13.0 | 66 / 66; 66 / 66 | 0.59 | 1.10 | +0.51 [-0.17, +1.25] | 0.60 | 0.66 | +0.06 [-0.28, +0.43] | no |
| GPT-6 Luna | 66 / 66; 66 / 66 | 0.95 | 0.14 | -0.81 [-1.57, -0.11] | 0.66 | 0.66 | +0.00 [-0.36, +0.38] | no |
| Celeris-1 Decision | 66 / 66; 66 / 66 | 0.43 | 0.85 | +0.42 [-0.32, +1.11] | 0.86 | 0.65 | -0.21 [-0.56, +0.15] | no |
| Decider v1.1 27B | 66 / 66; 66 / 66 | 0.44 | 0.45 | +0.01 [-0.67, +0.66] | 0.56 | 0.61 | +0.05 [-0.27, +0.38] | no |
| Cygnet (Gemma 4 12B) | 66 / 66; 66 / 66 | 0.62 | 0.52 | -0.10 [-0.79, +0.60] | 0.70 | 0.69 | -0.01 [-0.34, +0.35] | no |
| SubQ Snap Preview | 66 / 66; 66 / 66 | 0.56 | 0.29 | -0.27 [-0.95, +0.34] | 0.36 | 0.45 | +0.09 [-0.23, +0.42] | no |
| Mercury Decide | 66 / 66; 66 / 66 | 0.31 | 0.48 | +0.17 [-0.51, +0.86] | 0.79 | 0.83 | +0.04 [-0.29, +0.37] | no |
| Winnow-12B | 66 / 66; 66 / 66 | 0.40 | 0.39 | -0.01 [-0.65, +0.60] | 0.35 | 0.23 | -0.12 [-0.43, +0.18] | no |
| Decider v1.2 27B | 66 / 66; 66 / 66 | 0.30 | 0.88 | +0.58 [-0.10, +1.27] | 0.53 | 0.63 | +0.10 [-0.25, +0.45] | no |
| Decider Flash v1.2 | 66 / 66; 66 / 66 | 0.30 | 0.53 | +0.23 [-0.42, +0.85] | 0.08 | 0.04 | -0.04 [-0.35, +0.25] | no |
| Open-Jev 27B v1.1 | 66 / 66; 66 / 66 | 0.42 | 0.23 | -0.19 [-0.82, +0.43] | 0.06 | 0.23 | +0.17 [-0.14, +0.46] | no |
| GPT-6.1 Sol (high) | 66 / 66; 66 / 66 | 1.18 | 2.05 | +0.87 [+0.16, +1.71] | 0.63 | 0.76 | +0.13 [-0.22, +0.54] | no |
| GPT-6.1 Sol (low) | 66 / 66; 66 / 66 | 1.14 | 1.86 | +0.72 [+0.04, +1.56] | 0.65 | 0.85 | +0.20 [-0.12, +0.63] | no |
| Claude Sonnet 5.5 (low) | 66 / 66; 66 / 66 | 0.99 | 1.44 | +0.45 [-0.32, +1.27] | 0.80 | 0.91 | +0.11 [-0.25, +0.51] | no |
| Gemini 3.8 Flash (low) | 66 / 66; 66 / 66 | 0.79 | 2.17 | +1.38 [+0.73, +1.92] | 0.90 | 1.35 | +0.45 [+0.12, +0.72] | no |
| Gemma 4 31B (on) | 66 / 66; 66 / 66 | 0.66 | 1.56 | +0.90 [+0.04, +1.81] | 1.17 | 1.00 | -0.17 [-0.61, +0.30] | no |
| DeepSeek V4.1 Flash (off) | 66 / 66; 66 / 66 | 0.78 | 0.60 | -0.18 [-0.90, +0.55] | 0.50 | 0.65 | +0.15 [-0.20, +0.49] | no |
| Qwen3.8-27B (off) | 66 / 66; 66 / 66 | 0.31 | 0.37 | +0.06 [-0.64, +0.78] | 0.79 | 0.82 | +0.03 [-0.29, +0.36] | no |
| LFM2.5-24B-A2B (on) | 66 / 66; 66 / 66 | 0.53 | 0.47 | -0.06 [-0.70, +0.52] | 0.17 | 0.23 | +0.06 [-0.24, +0.35] | no |
| LFM2.5-24B-A2B (off) | 66 / 66; 66 / 66 | 0.23 | 0.45 | +0.22 [-0.39, +0.86] | 0.19 | -0.00 | -0.19 [-0.49, +0.11] | no |
| GPT-6 Astra (on) | 66 / 66; 66 / 66 | 1.53 | 2.05 | +0.52 [-0.18, +1.32] | 0.73 | 0.76 | +0.03 [-0.32, +0.43] | no |
| GPT-6.1 Terra | 66 / 66; 66 / 66 | 0.91 | 1.44 | +0.53 [-0.29, +1.45] | 0.76 | 1.06 | +0.30 [-0.07, +0.75] | no |
| GNUbg weak | 66 / 66; 66 / 66 | 0.71 | 0.95 | +0.24 [-0.37, +0.82] | -0.28 | -0.47 | -0.19 [-0.48, +0.09] | no |
| Random | 66 / 66; 66 / 66 | 0.27 | 0.37 | +0.10 [-0.11, +0.30] | -0.77 | -0.82 | -0.05 [-0.15, +0.04] | no |

Exploratory (not tested): GPT-6.1 Terra against GPT-6.1 Sol (low) appears in the tables above; no comparison is drawn.

## Engine check

40 frozen pairs (80 positions). Rollouts: GNUbg 1.08.003 rollout: 1,296 trials per play, cubeless, variance reduction on, quasi-random dice, no truncation, no late evaluation, chequer play 1-ply, seed 1, 8 threads, nice 19; candidates: top 5 at 2-ply plus every play any setup chose. 436 plays rolled out;
a play without a rollout used its 2-ply value plus the position's mean shift (447
uses, mostly Random's all-plays mean). No comparison changes direction.

| Comparison (40 pairs) | 2-ply A − B [99%] | Rollout A − B [99%] | Direction changed |
| --- | --- | --- | --- |
| decision models − workhorses | +6.36 [-3.28, +18.64] | +6.17 [-3.57, +18.72] | no |
| decision models − frontier | +16.49 [-1.68, +40.04] | +16.11 [-2.20, +39.49] | no |
| workhorses − frontier | +10.13 [-1.63, +24.58] | +9.94 [-1.64, +24.21] | no |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | -14.59 [-55.64, +18.77] | -15.61 [-56.62, +17.00] | no |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | +1.76 [-2.81, +6.99] | +2.73 [-1.97, +8.46] | no |

| Setup | 2-ply standard / Nackgammon / drop | Rollout standard / Nackgammon / drop |
| --- | --- | --- |
| Fastino GLiDE v1.2 (local) | 13.43 / 20.28 / +6.86 | 14.30 / 19.14 / +4.85 |
| Jev 1.13.0 | 14.66 / 25.27 / +10.61 | 15.82 / 23.79 / +7.97 |
| GPT-6 Luna | 11.27 / 38.90 / +27.63 | 12.17 / 36.34 / +24.17 |
| Celeris-1 Decision | 19.94 / 53.19 / +33.24 | 20.90 / 51.27 / +30.37 |
| Decider v1.1 27B | 17.21 / 23.64 / +6.43 | 18.36 / 21.31 / +2.95 |
| Cygnet (Gemma 4 12B) | 17.71 / 22.08 / +4.37 | 19.07 / 19.93 / +0.85 |
| SubQ Snap Preview | 17.11 / 35.79 / +18.67 | 18.47 / 34.63 / +16.16 |
| Mercury Decide | 15.28 / 32.27 / +16.99 | 16.11 / 30.64 / +14.54 |
| Winnow-12B | 19.40 / 40.94 / +21.54 | 20.82 / 39.56 / +18.74 |
| Decider v1.2 27B | 15.09 / 20.47 / +5.39 | 16.17 / 19.36 / +3.19 |
| Decider Flash v1.2 | 29.51 / 63.81 / +34.31 | 32.15 / 60.75 / +28.60 |
| Open-Jev 27B v1.1 | 51.03 / 54.35 / +3.31 | 52.10 / 52.82 / +0.72 |
| GPT-6.1 Sol (high) | 11.73 / 10.46 / -1.28 | 12.53 / 8.87 / -3.66 |
| GPT-6.1 Sol (low) | 13.56 / 10.52 / -3.04 | 15.09 / 8.70 / -6.39 |
| Claude Sonnet 5.5 (low) | 12.96 / 18.62 / +5.66 | 14.17 / 17.06 / +2.89 |
| Gemini 3.8 Flash (low) | 15.21 / 10.19 / -5.02 | 16.33 / 8.38 / -7.95 |
| Gemma 4 31B (on) | 14.93 / 18.07 / +3.13 | 16.05 / 16.73 / +0.69 |
| DeepSeek V4.1 Flash (off) | 10.19 / 22.97 / +12.78 | 11.05 / 20.58 / +9.53 |
| Qwen3.8-27B (off) | 9.63 / 23.71 / +14.08 | 10.52 / 22.07 / +11.55 |
| LFM2.5-24B-A2B (on) | 24.08 / 46.03 / +21.95 | 25.81 / 44.33 / +18.51 |
| LFM2.5-24B-A2B (off) | 36.14 / 72.68 / +36.54 | 37.09 / 71.22 / +34.12 |
| GPT-6 Astra (on) | 8.46 / 7.75 / -0.71 | 9.60 / 6.25 / -3.35 |
| GPT-6.1 Terra | 11.43 / 8.61 / -2.81 | 12.64 / 6.74 / -5.90 |
| GNUbg weak | 25.27 / 29.43 / +4.16 | 28.12 / 28.10 / -0.02 |
| Random | 83.84 / 93.55 / +9.72 | 86.10 / 92.24 / +6.14 |

## OpenRouter accounting

From the retained budget ledgers and the answers' recorded costs only (no request). "Ledger-accounted" is what the
ledger booked against the caps: per attempt the larger of the list-price cost and the provider-reported cost.
"Provider-reported" is OpenRouter's `usage.cost` per response. Mercury Decide is on no ledger (its route allows none):
its recorded cost is the runner's list-price computation; its provider-billed amount was not retained (unknown).

| Run | Row | Ledger attempts (Mercury Decide: final answer records, no attempt ledger) | Ledger-accounted $ (booked: max of list price and provider-reported) | Provider-reported $ | Source |
| --- | --- | --- | --- | --- | --- |
| GPT-6.1 Terra smoke (50 positions) | a | 100 | $0.21256375 | $0.21256375 | budget ledger |
| DeepSeek V4.1 Flash (off), main 400 | b | 403 | $0.17848470 | $0.11737138 | budget ledger |
| GPT-6.1 Terra, main 400 | c | 400 | $1.48939450 | $1.48939450 | budget ledger |
| DeepSeek V4.1 Flash (off), reserve 600 | d | 602 | $0.23559354 | $0.14983871 | budget ledger |
| GPT-6.1 Terra, reserve 600 | d | 600 | $2.22006875 | $2.22006875 | budget ledger |
| Mercury Decide, main 400 | b | 400 | $0.02232026 | unknown | answers' recorded cost (runner list price; no ledger) |
| Mercury Decide, reserve 600 | d | 600 | $0.03351938 | unknown | answers' recorded cost (runner list price; no ledger) |

- Open or lost reservations in the three ledgers: 0 (every attempt settled).
- Row d, ledger setups only: ledger-accounted $2.45566229, provider-reported $2.36990746. Adding Mercury Decide's recorded reserve cost ($0.03351938, list price) gives $2.48918167: the "$2.489" quoted earlier was this ledger-accounted figure including Mercury, against the $2.55 cap (ledger cap $2.51 + Mercury limit $0.035). Provider-reported row d including Mercury is unknown (Mercury's billed amount was not retained); with Mercury at its list-price record it would be $2.40342684.
- Rows a–d: ledger-accounted $4.39194488 (incl. Mercury at list price; the "$4.39" quoted earlier); provider-reported $4.18923709 for the ledger runs plus Mercury unknown (list-price record $0.05583964).
- DeepSeek V4.1 Flash (off) books above its provider-reported cost because the ledger's list price ($0.30/$1.20 per M) exceeds what OpenRouter reported; GPT-6.1 Terra books at its provider-reported cost, which exceeds list price because OpenRouter billed each prompt as a cache write ($1.25 per M).
- Not on any ledger: before the smoke test, direct probe requests to openai/gpt-6.1-terra outside the runner; one answered probe reported $0.000033, one answered probe's cost was not retained (unknown); the rest were refused by routing (404): none has a reported cost and none was booked; the billed amount is unknown. The smoke test's first attempt (50 requests) was refused by routing (404) and booked at $0 (no reported cost; the billed amount is unknown).
- The OpenRouter account's usage rose by $4.99 between 18:05 UTC on 2026-10-27 and about 01:00 UTC on 2026-10-28; the difference from the figures above is not attributable from retained data (other runs on the same account in that window): unknown.

## Update 2026-10-28: Cup-roster additions (§10.14(g)) and Argon (low) (§10.14(h))

Written 2026-10-28 by the run's agent. **Not published:** no site push (release candidate `d125adb` is held by Can; a new release goes to Zeki as a new candidate). The earlier text above is unchanged. Results file: `positions/nack-paired/results-2026-10-28/results.json` (sha256 `1c8af11dce2b2e18…`), built by `tools/v3/nack_paired_score.py report --rollouts smoke/nack-engine-check-g.db --out positions/nack-paired/results-2026-10-28`. The frozen 2026-10-27 results (`positions/nack-paired/results/`) are untouched.

**Timing (stated wherever these results appear):** the additions were made after this test's results had been computed and read. They follow the Cup roster (§10.14(b), (g)), not the results. Method notes committed before the first call of each new setup: §10.14(g) `1acbdae`; §10.14(h) `cbb9c87` (Argon (on) dropped, Argon (low) exploratory, output-limit rule) and `97f782a` ("past 32,768, no limit sent" flag).

**Display names:** after the relabel, the database setups "Grok 4.7 (on)" and "Gemini 4 Argon (off)" are displayed as Grok 4.7 (high) and Gemini 4 Argon (low). Both names are used below.

### Runs

| Setup | Group | Route | Run (UTC, 2026-10-28) | Records | No answer | Cut off at the limit | Past 32,768, no limit sent | Recorded cost, all 1,000 |
|---|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (on) | frontier | Claude subscription | 15:33–16:20 | 1,000 | 0 | 0 | 0 | $73.67 (API-equivalent, not billed) |
| Grok 4.7 (high) | frontier | xAI subscription | 15:33–20:50 | 1,000 | 34 | 0 | 17 | $63.44 (API-equivalent, not billed) |
| Liquid d1-ultra | decision models | Liquid API | 15:33–15:35 | 1,000 | 0 | 0 | 0 | $0.11 (billed) |
| Fastino GLiDE | decision models | Fastino API (glide_v2) | 18:19–18:21 (after a new key; the first start at 15:33 got 401 and stored nothing) | 1,000 | 0 | 0 | 0 | $0.00 (billed) |
| Gemini 4 Argon (low) | no group (exploratory) | Antigravity subscription | 21:08–21:23 | 1,000 | 0 | 0 | 0 | $5.91 (API-equivalent, not billed) |

Grok 4.7 (high)'s 34 records without an answer all hit the 600 s time limit: 15 main, 19 reserve. They score the position's Random error under the frozen rule, with both sensitivity checks below. Its 17 answers past 32,768 output tokens come from a run that sent no limit and started before the rule. They are flagged and keep their scores. Gemini 4 Argon (on) was dropped after its smoke test: 7 of 50 answers were cut off at 32,768 tokens (`mailbox/Nackgammon - Argon (on) smoke 2026-10-28.md`). None of its paired positions was asked.

### Per setup: first look, extension, final look (97.5% intervals)

| Setup | Group | First look: std / Nack / drop [97.5%] | Extended | Final (500 pairs): std / Nack / drop [97.5%] | Label | Sensitivity (main 200): worst / pair dropped / cut-off left out |
|---|---|---|---|---|---|---|
| Claude Fable 5.1 (on) | frontier | 9.13 / 9.51 / +0.38 [-4.64, +5.07] | yes | 9.64 / 10.8 / +1.16 [-2.17, +4.40] | **kept** | +0.38 [-4.64, +5.07] / +0.38 [-4.64, +5.07] (200 pairs) / +0.38 [-4.64, +5.07] |
| Grok 4.7 (high) | frontier | 15.2 / 14.53 / -0.67 [-6.58, +5.07] | yes | 15.68 / 16.53 / +0.85 [-3.74, +5.35] | **unclear** | -0.46 [-6.52, +5.59] / -0.84 [-7.17, +5.33] (186 pairs) / -0.67 [-6.58, +5.07] |
| Liquid d1-ultra | decision models | 24.25 / 28.27 / +4.01 [-11.37, +17.17] | yes | 25.3 / 31.47 / +6.17 [-2.06, +13.95] | **unclear** | +4.01 [-11.37, +17.17] / +4.01 [-11.37, +17.17] (200 pairs) / +4.01 [-11.37, +17.17] |
| Fastino GLiDE | decision models | 22.93 / 23.38 / +0.45 [-8.03, +8.77] | yes | 25.73 / 28.8 / +3.07 [-3.84, +9.81] | **unclear** | +0.45 [-8.03, +8.77] / +0.45 [-8.03, +8.77] (200 pairs) / +0.45 [-8.03, +8.77] |
| Gemini 4 Argon (low) | no group (exploratory) | 13.79 / 15.71 / +1.92 [-4.33, +8.42] | yes | 14.71 / 17.42 / +2.71 [-2.06, +7.62] | **unclear** | +1.92 [-4.33, +8.42] / +1.92 [-4.33, +8.42] (200 pairs) / +1.92 [-4.33, +8.42] |

**Claude Fable 5.1 (on) is the first setup in this test labelled "kept".** Its final 97.5% interval [−2.17, +4.40] lies within ±5 PR. Every other setup, old and new, stays "unclear". For every earlier setup, the per-setup first and final looks are identical to the frozen 2026-10-27 file: the bootstrap indices depend only on the look, and the check found 0 changes.

### Primary comparisons (main 200 pairs, M = 5, 99% intervals)

(ii), with the §10.14(g) additions, is the **primary result** per §10.14(b). (i), with the original members only (the 22 setups of §10.14(d)), reproduces the frozen 2026-10-27 primary results exactly. Argon (low) is in no group. Scope: these results hold for these rosters only; each group is the setups in the run from that original league. Frontier now has 3 setups (GPT-6 Astra (on), Claude Fable 5.1 (on), Grok 4.7 (high)) instead of 1. Decision models now has 14 (+ Liquid d1-ultra, Fastino GLiDE).

| Comparison | (i) original members: diff [99%] | (ii) with additions (primary): diff [99%] | (ii) A drop / B drop | (ii) worst-play rule | (ii) pairs dropped | (ii) cut-off pairs left out |
|---|---|---|---|---|---|---|
| decision models − workhorses | -2.14 [-10.07, +4.88] | **-1.44 [-8.85, +4.96]** | -1.93 / -0.49 | -0.73 [-8.24, +5.88] | -1.77 [-9.22, +4.92] | -1.44 [-8.85, +4.96] |
| decision models − frontier | -0.26 [-14.64, +12.04] | **-1.04 [-14.19, +10.26]** | -1.93 / -0.89 | -1.12 [-14.14, +10.21] | -0.99 [-14.18, +10.32] | -1.04 [-14.19, +10.26] |
| workhorses − frontier | +1.88 [-5.73, +9.33] | **+0.40 [-6.68, +6.96]** | -0.49 / -0.89 | -0.39 [-7.62, +6.32] | +0.78 [-6.32, +7.42] | +0.40 [-6.68, +6.96] |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | -3.88 [-26.98, +21.76] | **-3.88 [-26.98, +21.76]** | -0.65 / +3.23 | -10.33 [-38.92, +19.74] | -0.91 [-24.13, +25.20] | -3.88 [-26.98, +21.76] |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | -0.19 [-3.00, +2.63] | **-0.19 [-3.00, +2.63]** | -1.45 / -1.26 | -0.19 [-3.00, +2.63] | -0.19 [-3.00, +2.63] | -0.19 [-3.00, +2.63] |

**No primary interval excludes 0, either way or under any rule.** The effort pairs (comparisons 4 and 5) are unchanged by the additions.

### Secondary (labelled secondary)

**Kept advantage K** (95% intervals; none unstable):

| Setup | K, main 200 | K, all 500 |
|---|---|---|
| Claude Fable 5.1 (on) | 0.94 [+0.80, +1.09] | 0.94 [+0.85, +1.03] |
| Grok 4.7 (high) | 0.95 [+0.79, +1.12] | 0.93 [+0.83, +1.05] |
| Liquid d1-ultra | 0.86 [+0.71, +1.05] | 0.83 [+0.74, +0.94] |
| Fastino GLiDE | 0.92 [+0.75, +1.13] | 0.89 [+0.78, +1.00] |
| Gemini 4 Argon (low) | 0.91 [+0.77, +1.07] | 0.91 [+0.81, +1.01] |

**Ranking:** Spearman ρ over the 28 model setups (yardsticks left out; Argon (low) and Terra included as before) = **0.9 [+0.79, +0.92]** (95%). It was 0.87 over 23 setups. Largest rank changes: Decider v1.2 27B 24→11 (-13); GPT-6 Luna 17→24 (+7); Cygnet (Gemma 4 12B) 20→14 (-6); Fastino GLiDE v1.2 (local) 11→15 (+4); Gemini 3.8 Flash (low) 9→5 (-4).

**Risk** (main 200 pairs; 66 Risk pays / 66 Safety pays per set, none thin; 95% paired intervals):

| Setup | d′ std → Nack | Δd′ | c std → Nack | Δc |
|---|---|---|---|---|
| Claude Fable 5.1 (on) | 1.33 → 2.01 | +0.68 [+0.00, +1.47] | 0.55 → 0.78 | +0.23 [-0.11, +0.62] |
| Grok 4.7 (high) | 0.63 → 1.47 | +0.84 [+0.16, +1.76] | 0.47 → 0.89 | +0.42 [+0.09, +0.87] |
| Liquid d1-ultra | 0.91 → 0.52 | -0.39 [-1.15, +0.27] | 0.49 → 0.52 | +0.03 [-0.32, +0.37] |
| Fastino GLiDE | 0.72 → 0.48 | -0.24 [-0.87, +0.38] | 0.59 → 0.71 | +0.12 [-0.19, +0.45] |
| Gemini 4 Argon (low) | 1.17 → 1.26 | +0.09 [-0.48, +0.71] | 0.36 → 0.67 | +0.31 [+0.02, +0.61] |

**By phase** (descriptive, main 200, 95%): per setup in `results.json` (`setups.<name>.phases`).

### Engine check (40 frozen pairs)

The new setups' chosen plays that had no rollout yet (6 plays on 5 positions) were rolled out with the §10.12 settings (GNUbg 1.08.003, 1,296 trials, cubeless, variance reduction, quasi-random dice, 1-ply chequer play, seed 1, 8 threads, nice 19). They were added to a copy of the stored rollouts: `smoke/nack-engine-check-g.db`, 442 plays. The 436 earlier rollouts are unchanged. These 6 plays were rolled out alone, not alongside the other candidates of their positions. Adjusted 2-ply values used: 441. Adding the 6 new rollouts changes each position's mean (rollout − 2-ply) shift, which feeds the imputed values. That moves one saved rollout figure in (i): LFM2.5-24B-A2B (on) − (off), −15.61 → −15.63.

| Comparison | (i) 2-ply → rollout | (ii) 2-ply → rollout | Direction changed |
|---|---|---|---|
| decision models − workhorses | +6.36 → +6.17 | +5.57 → +5.35 | no |
| decision models − frontier | +16.49 → +16.11 | +15.03 → +14.90 | no |
| workhorses − frontier | +10.13 → +9.94 | +9.46 → +9.55 | no |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | -14.59 → -15.63 | -14.59 → -15.63 | no |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | +1.76 → +2.73 | +1.76 → +2.73 | no |

**No comparison changes direction, either way.**

### Cost and time of the new runs (all 1,000 recorded positions)

| Setup | Recorded cost / decision | Kind | Median request s |
|---|---|---|---|
| Claude Fable 5.1 (on) | $0.07367 | API-equivalent (subscription, not billed) | 8.9825 |
| Grok 4.7 (high) | $0.06344 | API-equivalent (subscription, not billed) | 94.778 |
| Liquid d1-ultra | $0.00011 | billed | 0.22 |
| Fastino GLiDE | $0.00000 | billed | 0.397 |
| Gemini 4 Argon (low) | $0.00591 | API-equivalent (subscription, not billed) | 3.1865 |

OpenRouter: $0 for these runs. GPU: none.

