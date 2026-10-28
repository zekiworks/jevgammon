# Nackgammon paired test: summary for Can (2026-10-28)

**On hold.** The release candidate `d125adb` (branch `nack-release-candidate`, worktree `jev-nackrc`) is on hold until Can has read this. Nothing from it was published: it is not pushed and not deployed to the site. (As the report's own disclosure says, the earlier commit `3e4f413`, with the aggregate report and `results.json`, was pushed to the public repository on 2026-10-28 at 01:03 UTC, before release approval; the site was not deployed.)

**Sources, read only.** Everything below is copied from the saved files of `d125adb`: `positions/nack-paired/results/results.json` (frozen; sha256 `0832f78d…26e8dd`, as stated in the report), `positions/nack-paired/results/accounting.json` and `mailbox/Nackgammon paired test - results.md` (built by `tools/v3/nack_paired_report.py`). No model call, no rescoring, no new bootstrap; no saved result changed. Two things are added and labelled where they appear: (a) equal-weight group averages of saved per-setup numbers (plain arithmetic means, no interval), and (b) seconds per decision, a descriptive read of the latency logged in the answers database `smoke/nack-paired.db` (opened read-only). Method: `tools/site/content/method-spec-2026-10-24.md` §10; groups by original league (§10.14): decision models (12), workhorses (9), frontier (1: GPT-6 Astra (on)); GPT-6.1 Terra is in no group (exploratory); GNUbg weak and Random are yardsticks, marked *(yardstick)*. These results hold for these rosters only; each group is the setups in the run from that original league. The frontier group has 1 setup.

**What "unclear" means.** "Unclear" means the setup's final 97.5% interval for the drop is too wide to tell whether its performance was kept within ±5 PR or dropped. Every setup in this test, including both yardsticks, is labelled **unclear**. Drop = Nackgammon PR − standard PR on the same pairs; positive = worse on Nackgammon.

## Roster: the 23 model setups and the two yardsticks

Groups by original league (§10.14(d)), each setup weighted equally in group means. Names checked against `results.json` (`groups`, `setups`), §10.14(d) and the answers database: **no difference** (same 23 model names in all three, plus GNUbg weak in the database and both yardsticks in `results.json`). The only change of membership is the documented one: §10.14 replaces the groups of §10.8, which had placed DeepSeek V4.1 Flash (off), both LFM2.5-24B-A2B setups and Qwen3.8-27B (off) among the decision models (League 1 by the ladder), GPT-6.1 Sol (low) and (high) in the frontier group (Cup teams from League 3) and Terra among the workhorses.

- **Decision models (original League 1), 12:** Fastino GLiDE v1.2 (local), Jev 1.13.0, GPT-6 Luna, Celeris-1 Decision, Decider v1.1 27B, Cygnet (Gemma 4 12B), SubQ Snap Preview, Mercury Decide, Winnow-12B, Decider v1.2 27B, Decider Flash v1.2, Open-Jev 27B v1.1.
- **Workhorses (original League 2), 9:** GPT-6.1 Sol (high), GPT-6.1 Sol (low), Claude Sonnet 5.5 (low), Gemini 3.8 Flash (low), Gemma 4 31B (on), DeepSeek V4.1 Flash (off), Qwen3.8-27B (off), LFM2.5-24B-A2B (on), LFM2.5-24B-A2B (off).
- **Frontier (original League 3), 1:** GPT-6 Astra (on).
- **No group (exploratory), 1:** GPT-6.1 Terra.
- **Yardsticks (no group, not among the 23):** GNUbg weak (GNUbg 1.08 Beginner, answered through the harness) and Random (no calls; exact mean loss over all legal plays from GNUbg's 2-ply values).

**GPT-6.1 Terra passed its smoke test**: 50 / 50 valid (50 answers, 0 failed, 0 timed out, 0% invalid), error rate 9.8 PR [3.4, 18.4] (95%), $0.213 OpenRouter (ledger row a: $0.21256375, provider-reported and ledger-accounted alike), choice only (no letter probabilities: OpenRouter's endpoint takes no `logprobs`; every paired-test exchange logs "no letter logprobs returned; choice only"). Smoke test on the 50 standard smoke positions with the league prompt `bg-v2`; source `mailbox/Nackgammon and Terra - cost and time 2026-10-27.md` (row a) and `accounting.json`; the smoke result is not part of `results.json`. Terra is one of the 23 paired-test model setups, in no group (exploratory): it enters no primary comparison, but it is among the 23 setups of the Spearman ranking.

## 1. Final drop per setup (97.5% interval)

Final look = all 500 pairs: every asked setup was extended under the frozen rule, and Random is reported on all 500. Width = upper − lower bound of the saved interval.

| Setup | Group | Pairs used | Drop | Final 97.5% interval | Width (PR) | Label |
| --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 500 | +1.60 | [-5.33, +8.30] | 13.63 | unclear |
| Jev 1.13.0 | decision models | 500 | +2.77 | [-5.20, +10.44] | 15.64 | unclear |
| GPT-6 Luna | decision models | 500 | +5.87 | [-4.27, +15.07] | 19.34 | unclear |
| Celeris-1 Decision | decision models | 500 | +4.08 | [-4.58, +12.64] | 17.22 | unclear |
| Decider v1.1 27B | decision models | 500 | +0.81 | [-7.98, +9.24] | 17.22 | unclear |
| Cygnet (Gemma 4 12B) | decision models | 500 | +0.20 | [-7.64, +7.43] | 15.07 | unclear |
| SubQ Snap Preview | decision models | 500 | +1.62 | [-7.07, +10.07] | 17.14 | unclear |
| Mercury Decide | decision models | 500 | +2.73 | [-5.94, +10.85] | 16.79 | unclear |
| Winnow-12B | decision models | 500 | +2.68 | [-6.26, +11.16] | 17.42 | unclear |
| Decider v1.2 27B | decision models | 500 | -2.68 | [-11.03, +5.25] | 16.28 | unclear |
| Decider Flash v1.2 | decision models | 500 | +7.78 | [-2.16, +18.39] | 20.55 | unclear |
| Open-Jev 27B v1.1 | decision models | 500 | -3.08 | [-13.33, +6.76] | 20.09 | unclear |
| GPT-6.1 Sol (high) | workhorses | 500 | -2.03 | [-5.57, +1.38] | 6.95 | unclear |
| GPT-6.1 Sol (low) | workhorses | 500 | -1.46 | [-5.01, +2.05] | 7.06 | unclear |
| Claude Sonnet 5.5 (low) | workhorses | 500 | -1.15 | [-5.89, +3.32] | 9.21 | unclear |
| Gemini 3.8 Flash (low) | workhorses | 500 | -1.30 | [-5.48, +2.90] | 8.38 | unclear |
| Gemma 4 31B (on) | workhorses | 500 | -1.13 | [-6.19, +4.39] | 10.58 | unclear |
| DeepSeek V4.1 Flash (off) | workhorses | 500 | +5.94 | [-2.48, +13.87] | 16.35 | unclear |
| Qwen3.8-27B (off) | workhorses | 500 | +4.76 | [-3.56, +12.53] | 16.09 | unclear |
| LFM2.5-24B-A2B (on) | workhorses | 500 | +4.77 | [-4.14, +13.49] | 17.63 | unclear |
| LFM2.5-24B-A2B (off) | workhorses | 500 | +4.43 | [-6.53, +15.38] | 21.91 | unclear |
| GPT-6 Astra (on) | frontier | 500 | -1.99 | [-5.52, +1.47] | 6.99 | unclear |
| GPT-6.1 Terra | no group (exploratory) | 500 | +3.04 | [-0.94, +7.39] | 8.33 | unclear |
| GNUbg weak *(yardstick)* | yardstick | 500 | -4.57 | [-10.32, +1.34] | 11.66 | unclear |
| Random *(yardstick)* | yardstick | 500 | -3.73 | [-11.43, +3.74] | 15.17 | unclear |

**Largest upper bound across all setups: Decider Flash v1.2 (decision models), +18.39 PR** (drop +7.78, interval [-2.16, +18.39]). Next: LFM2.5-24B-A2B (off) +15.38, GPT-6 Luna +15.07. Widths run from 6.95 (GPT-6.1 Sol (high)) to 21.91 (LFM2.5-24B-A2B (off)). Every interval contains 0 and reaches past +5 or −5 PR.

LFM2.5-24B-A2B (on): 107 of its 1,000 records hold no choice (timed out at 600 s; 52 Nackgammon / 55 standard over all 500 pairs, 16 / 22 on the main 200). They score the position's Random error (primary rule). The saved sensitivity checks are on the main 200 pairs only: primary −0.65 [−15.2, +14.4]; (i) worst play −7.10 [−27.4, +13.3]; (ii) affected pairs left out (166 of 200 pairs used), +2.32 [−12.3, +18.1]. All other setups: 0 invalid or missing.

## 2. Secondary analyses (as saved, labelled secondary)

### 2a. Kept advantage over random play (K)

K = (Random's Nackgammon PR − setup's Nackgammon PR) ÷ (Random's standard PR − setup's standard PR); 1 = the setup's whole advantage over random play carries over, 0 = it falls to random. 95% intervals. "Unstable" is flagged when the setup's standard advantage over Random is below 20 PR or its 95% interval reaches 0 (§10.11.1): no setup is flagged on either look. Random is the reference, so it has no K.

| Setup | Group | K, main 200 [95%] | Unstable (200) | K, all 500 [95%] | Unstable (500) |
| --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 0.90 [0.73, 1.09] | no | 0.91 [0.79, 1.05] | no |
| Jev 1.13.0 | decision models | 0.96 [0.80, 1.16] | no | 0.89 [0.80, 1.00] | no |
| GPT-6 Luna | decision models | 0.82 [0.64, 1.03] | no | 0.83 [0.72, 0.96] | no |
| Celeris-1 Decision | decision models | 0.94 [0.76, 1.15] | no | 0.87 [0.76, 0.99] | no |
| Decider v1.1 27B | decision models | 0.95 [0.76, 1.17] | no | 0.92 [0.80, 1.05] | no |
| Cygnet (Gemma 4 12B) | decision models | 1.04 [0.86, 1.27] | no | 0.93 [0.83, 1.05] | no |
| SubQ Snap Preview | decision models | 0.96 [0.76, 1.19] | no | 0.90 [0.78, 1.03] | no |
| Mercury Decide | decision models | 0.99 [0.81, 1.21] | no | 0.88 [0.77, 1.01] | no |
| Winnow-12B | decision models | 0.93 [0.74, 1.16] | no | 0.88 [0.77, 1.01] | no |
| Decider v1.2 27B | decision models | 1.14 [0.93, 1.39] | no | 0.98 [0.84, 1.14] | no |
| Decider Flash v1.2 | decision models | 0.84 [0.58, 1.16] | no | 0.74 [0.59, 0.92] | no |
| Open-Jev 27B v1.1 | decision models | 1.19 [0.84, 1.83] | no | 0.98 [0.81, 1.23] | no |
| GPT-6.1 Sol (high) | workhorses | 0.96 [0.82, 1.11] | no | 0.98 [0.88, 1.08] | no |
| GPT-6.1 Sol (low) | workhorses | 0.96 [0.81, 1.12] | no | 0.97 [0.87, 1.08] | no |
| Claude Sonnet 5.5 (low) | workhorses | 0.93 [0.78, 1.10] | no | 0.96 [0.86, 1.08] | no |
| Gemini 3.8 Flash (low) | workhorses | 0.99 [0.83, 1.18] | no | 0.96 [0.86, 1.08] | no |
| Gemma 4 31B (on) | workhorses | 1.01 [0.84, 1.21] | no | 0.96 [0.85, 1.08] | no |
| DeepSeek V4.1 Flash (off) | workhorses | 0.87 [0.71, 1.05] | no | 0.84 [0.75, 0.95] | no |
| Qwen3.8-27B (off) | workhorses | 0.92 [0.76, 1.10] | no | 0.85 [0.76, 0.96] | no |
| LFM2.5-24B-A2B (on) | workhorses | 0.92 [0.68, 1.22] | no | 0.82 [0.68, 0.98] | no |
| LFM2.5-24B-A2B (off) | workhorses | 0.79 [0.51, 1.19] | no | 0.79 [0.61, 1.00] | no |
| GPT-6 Astra (on) | frontier | 0.97 [0.83, 1.13] | no | 0.98 [0.88, 1.08] | no |
| GPT-6.1 Terra | no group (exploratory) | 0.93 [0.78, 1.10] | no | 0.91 [0.81, 1.01] | no |
| GNUbg weak *(yardstick)* | yardstick | 0.98 [0.77, 1.25] | no | 1.01 [0.88, 1.16] | no |

As saved: on the main 200 every K interval contains 1. On all 500 the interval lies wholly below 1 for GPT-6 Luna, Celeris-1 Decision, Decider Flash v1.2, DeepSeek V4.1 Flash (off), Qwen3.8-27B (off), LFM2.5-24B-A2B (on); every other interval contains 1.

### 2b. Ranking: Spearman correlation, standard vs Nackgammon PR

Main 200 pairs, the 23 model setups (yardsticks left out): **ρ = 0.87 [0.73, 0.91]** (95%). Five largest rank changes (1 = lowest error rate; negative change = a better rank on Nackgammon; ties by name):

| Setup | Group | Standard rank | Nackgammon rank | Change |
| --- | --- | --- | --- | --- |
| Decider v1.2 27B | decision models | 19 | 8 | -11 |
| GPT-6 Luna | decision models | 12 | 19 | +7 |
| Cygnet (Gemma 4 12B) | decision models | 15 | 10 | -5 |
| DeepSeek V4.1 Flash (off) | workhorses | 9 | 12 | +3 |
| Fastino GLiDE v1.2 (local) | decision models | 8 | 11 | +3 |

### 2c. Risk: ability d′ and caution c, standard → Nackgammon

Positions per class and set (frozen position files): main 200 pairs: 66 Risk pays, 66 Safety pays, 68 No trade-off in each set; all 500 pairs: 165 / 165 / 170 in each set. d′ and c use the Risk pays and Safety pays positions. **Thin classes: none.** A class is thin below 50 positions (§10.11.3); the smallest class here has 66, and the saved `thin` flag is "no" for every setup. Invalid or missing answers count with Random's weights. 95% paired intervals. The report shows the main 200; `results.json` also holds the same analysis on all 500 pairs (`risk_all`, asked setups only), given in the last two columns.

| Setup | Group | d′ std → Nack (200) | Δd′ [95%] (200) | c std → Nack (200) | Δc [95%] (200) | Thin | Δd′ [95%] (500) | Δc [95%] (500) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 0.82 → 0.37 | -0.45 [-1.15, +0.19] | 0.60 → 0.65 | +0.05 [-0.29, +0.38] | no | -0.12 [-0.54, +0.30] | +0.00 [-0.21, +0.21] |
| Jev 1.13.0 | decision models | 0.59 → 1.10 | +0.51 [-0.17, +1.25] | 0.60 → 0.66 | +0.06 [-0.28, +0.43] | no | +0.05 [-0.40, +0.48] | -0.18 [-0.39, +0.04] |
| GPT-6 Luna | decision models | 0.95 → 0.14 | -0.81 [-1.57, -0.11] | 0.66 → 0.66 | +0.00 [-0.36, +0.38] | no | -0.39 [-0.86, +0.02] | -0.21 [-0.43, +0.01] |
| Celeris-1 Decision | decision models | 0.43 → 0.85 | +0.42 [-0.32, +1.11] | 0.86 → 0.65 | -0.21 [-0.56, +0.15] | no | +0.06 [-0.38, +0.46] | -0.22 [-0.44, -0.01] |
| Decider v1.1 27B | decision models | 0.44 → 0.45 | +0.01 [-0.67, +0.66] | 0.56 → 0.61 | +0.05 [-0.27, +0.38] | no | +0.03 [-0.38, +0.42] | +0.07 [-0.13, +0.27] |
| Cygnet (Gemma 4 12B) | decision models | 0.62 → 0.52 | -0.10 [-0.79, +0.60] | 0.70 → 0.69 | -0.01 [-0.34, +0.35] | no | -0.29 [-0.70, +0.13] | -0.11 [-0.33, +0.09] |
| SubQ Snap Preview | decision models | 0.56 → 0.29 | -0.27 [-0.95, +0.34] | 0.36 → 0.45 | +0.09 [-0.23, +0.42] | no | -0.19 [-0.57, +0.19] | +0.00 [-0.20, +0.20] |
| Mercury Decide | decision models | 0.31 → 0.48 | +0.17 [-0.51, +0.86] | 0.79 → 0.83 | +0.04 [-0.29, +0.37] | no | -0.09 [-0.52, +0.33] | -0.01 [-0.23, +0.21] |
| Winnow-12B | decision models | 0.40 → 0.39 | -0.01 [-0.65, +0.60] | 0.35 → 0.23 | -0.12 [-0.43, +0.18] | no | -0.15 [-0.53, +0.22] | -0.18 [-0.38, +0.02] |
| Decider v1.2 27B | decision models | 0.30 → 0.88 | +0.58 [-0.10, +1.27] | 0.53 → 0.63 | +0.10 [-0.25, +0.45] | no | +0.29 [-0.10, +0.67] | +0.06 [-0.13, +0.27] |
| Decider Flash v1.2 | decision models | 0.30 → 0.53 | +0.23 [-0.42, +0.85] | 0.08 → 0.04 | -0.04 [-0.35, +0.25] | no | +0.09 [-0.30, +0.48] | -0.10 [-0.29, +0.10] |
| Open-Jev 27B v1.1 | decision models | 0.42 → 0.23 | -0.19 [-0.82, +0.43] | 0.06 → 0.23 | +0.17 [-0.14, +0.46] | no | -0.28 [-0.66, +0.11] | -0.01 [-0.19, +0.19] |
| GPT-6.1 Sol (high) | workhorses | 1.18 → 2.05 | +0.87 [+0.16, +1.71] | 0.63 → 0.76 | +0.13 [-0.22, +0.54] | no | +0.41 [-0.06, +0.89] | +0.05 [-0.18, +0.29] |
| GPT-6.1 Sol (low) | workhorses | 1.14 → 1.86 | +0.72 [+0.04, +1.56] | 0.65 → 0.85 | +0.20 [-0.12, +0.63] | no | +0.15 [-0.32, +0.61] | +0.04 [-0.18, +0.28] |
| Claude Sonnet 5.5 (low) | workhorses | 0.99 → 1.44 | +0.45 [-0.32, +1.27] | 0.80 → 0.91 | +0.11 [-0.25, +0.51] | no | +0.14 [-0.31, +0.58] | -0.07 [-0.29, +0.16] |
| Gemini 3.8 Flash (low) | workhorses | 0.79 → 2.17 | +1.38 [+0.73, +1.92] | 0.90 → 1.35 | +0.45 [+0.12, +0.72] | no | +0.36 [-0.12, +0.89] | +0.03 [-0.21, +0.30] |
| Gemma 4 31B (on) | workhorses | 0.66 → 1.56 | +0.90 [+0.04, +1.81] | 1.17 → 1.00 | -0.17 [-0.61, +0.30] | no | +0.10 [-0.50, +0.65] | -0.29 [-0.57, -0.02] |
| DeepSeek V4.1 Flash (off) | workhorses | 0.78 → 0.60 | -0.18 [-0.90, +0.55] | 0.50 → 0.65 | +0.15 [-0.20, +0.49] | no | -0.22 [-0.67, +0.20] | -0.06 [-0.27, +0.15] |
| Qwen3.8-27B (off) | workhorses | 0.31 → 0.37 | +0.06 [-0.64, +0.78] | 0.79 → 0.82 | +0.03 [-0.29, +0.36] | no | -0.05 [-0.52, +0.37] | -0.03 [-0.24, +0.19] |
| LFM2.5-24B-A2B (on) | workhorses | 0.53 → 0.47 | -0.06 [-0.70, +0.52] | 0.17 → 0.23 | +0.06 [-0.24, +0.35] | no | -0.36 [-0.74, +0.00] | -0.01 [-0.19, +0.18] |
| LFM2.5-24B-A2B (off) | workhorses | 0.23 → 0.45 | +0.22 [-0.39, +0.86] | 0.19 → -0.00 | -0.19 [-0.49, +0.11] | no | +0.40 [+0.01, +0.80] | -0.23 [-0.44, -0.03] |
| GPT-6 Astra (on) | frontier | 1.53 → 2.05 | +0.52 [-0.18, +1.32] | 0.73 → 0.76 | +0.03 [-0.32, +0.43] | no | +0.24 [-0.21, +0.72] | -0.02 [-0.25, +0.22] |
| GPT-6.1 Terra | no group (exploratory) | 0.91 → 1.44 | +0.53 [-0.29, +1.45] | 0.76 → 1.06 | +0.30 [-0.07, +0.75] | no | -0.14 [-0.64, +0.36] | -0.05 [-0.31, +0.19] |
| GNUbg weak *(yardstick)* | yardstick | 0.71 → 0.95 | +0.24 [-0.37, +0.82] | -0.28 → -0.47 | -0.19 [-0.48, +0.09] | no | +0.12 [-0.27, +0.50] | -0.11 [-0.30, +0.09] |
| Random *(yardstick)* | yardstick | 0.27 → 0.37 | +0.10 [-0.11, +0.30] | -0.77 → -0.82 | -0.05 [-0.15, +0.04] | no | not saved | not saved |

Saved intervals that exclude 0 (secondary; §10.11 sets no multiplicity correction for them): main 200, Δd′: GPT-6 Luna (−), GPT-6.1 Sol (high) (+), GPT-6.1 Sol (low) (+), Gemini 3.8 Flash (low) (+), Gemma 4 31B (on) (+); Δc: Gemini 3.8 Flash (low) (+). All 500, Δd′: LFM2.5-24B-A2B (off) (+); Δc: Celeris-1 Decision (−), Gemma 4 31B (on) (−), LFM2.5-24B-A2B (off) (−). All others contain 0.

## 3. Drop by phase (descriptive, main 200 pairs, 95% intervals)

Pairs per phase: opening 60, contact 60, holding 30, race 25, bear-off 25. §10.9 is descriptive (part of hypothesis (a), not a test). Last column: opening against the other four phases pooled.

| Setup | Group | opening | contact | holding | race | bear-off | opening − other phases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | +9.2 [-2.3, +20.7] | -10.2 [-28.8, +7.8] | +17.2 [-11.0, +52.4] | +3.4 [-5.6, +14.6] | -4.4 [-9.8, -0.4] | +10.1 [-5.6, +25.6] |
| Jev 1.13.0 | decision models | +3.5 [-7.3, +14.0] | -3.6 [-21.5, +13.8] | -21.2 [-97.5, +36.0] | +4.5 [-4.5, +15.5] | +2.4 [-3.1, +11.9] | +8.4 [-10.2, +29.8] |
| GPT-6 Luna | decision models | +18.9 [+6.0, +31.4] | -9.5 [-31.2, +11.0] | +4.3 [-74.8, +63.7] | +16.3 [-5.7, +51.1] | +2.6 [-6.0, +13.9] | +18.7 [-2.7, +42.6] |
| Celeris-1 Decision | decision models | -9.1 [-26.1, +6.2] | -5.0 [-22.4, +12.2] | +8.5 [-74.2, +83.5] | +12.3 [-7.0, +45.4] | +1.4 [-9.0, +13.6] | -11.2 [-36.4, +14.3] |
| Decider v1.1 27B | decision models | +17.7 [+4.3, +31.3] | -13.4 [-30.5, +3.9] | -17.6 [-95.1, +44.3] | +2.4 [-6.0, +13.2] | -6.0 [-14.0, -0.2] | +27.8 [+7.2, +50.6] |
| Cygnet (Gemma 4 12B) | decision models | -1.1 [-15.9, +13.2] | -6.7 [-24.7, +11.3] | -35.2 [-109.3, +16.0] | +7.2 [-1.3, +18.1] | -1.1 [-5.9, +4.8] | +8.2 [-12.7, +31.4] |
| SubQ Snap Preview | decision models | +7.4 [-6.5, +21.1] | -3.5 [-23.5, +18.4] | -17.9 [-94.9, +42.3] | -2.5 [-8.1, +3.0] | -3.4 [-7.9, -0.1] | +13.8 [-7.2, +37.1] |
| Mercury Decide | decision models | +3.5 [-10.1, +15.9] | -17.5 [-35.8, -0.6] | -12.4 [-88.5, +41.1] | +18.1 [-4.7, +52.5] | -3.8 [-8.4, -0.7] | +11.1 [-9.5, +33.4] |
| Winnow-12B | decision models | +8.0 [-6.2, +21.7] | -12.1 [-31.8, +7.0] | +3.5 [-84.5, +79.9] | +1.7 [-7.1, +10.2] | -3.0 [-9.4, +3.8] | +12.6 [-10.3, +37.0] |
| Decider v1.2 27B | decision models | -0.1 [-13.6, +12.9] | -18.2 [-39.0, +1.1] | -40.1 [-114.0, +16.9] | +0.9 [-9.2, +12.6] | -3.8 [-8.5, -0.5] | +16.8 [-4.0, +39.7] |
| Decider Flash v1.2 | decision models | +0.9 [-15.8, +18.4] | -11.4 [-40.8, +18.8] | +28.8 [-24.0, +99.7] | +13.8 [-1.7, +32.9] | +1.8 [-6.8, +11.6] | -3.2 [-29.2, +21.5] |
| Open-Jev 27B v1.1 | decision models | -15.9 [-34.9, +3.0] | -27.9 [-63.6, +5.2] | +18.7 [-49.4, +90.1] | -0.6 [-13.6, +12.6] | -5.8 [-13.0, -0.6] | -6.8 [-35.8, +21.7] |
| GPT-6.1 Sol (high) | workhorses | +0.8 [-6.6, +8.3] | -2.4 [-9.8, +5.0] | -6.3 [-19.6, +3.9] | -0.2 [-1.0, +0.4] | +0.0 [+0.0, +0.0] | +3.2 [-5.1, +12.1] |
| GPT-6.1 Sol (low) | workhorses | +3.7 [-4.1, +12.1] | -3.7 [-12.3, +4.6] | -6.3 [-19.7, +3.5] | -0.9 [-2.6, +0.3] | -1.6 [-4.8, +0.0] | +7.1 [-1.9, +16.6] |
| Claude Sonnet 5.5 (low) | workhorses | +4.5 [-3.8, +13.6] | -0.1 [-12.5, +11.7] | -6.1 [-19.3, +3.6] | +1.0 [-3.9, +7.1] | +0.1 [+0.0, +0.2] | +5.6 [-4.3, +16.3] |
| Gemini 3.8 Flash (low) | workhorses | +1.1 [-5.5, +7.3] | -12.3 [-25.0, -0.1] | -0.9 [-14.6, +10.2] | -2.7 [-6.9, +0.6] | -2.1 [-6.0, +0.0] | +7.4 [-1.5, +16.4] |
| Gemma 4 31B (on) | workhorses | +0.0 [-9.8, +10.1] | -13.7 [-29.6, +2.2] | -1.5 [-15.2, +9.5] | -3.2 [-6.9, -0.3] | -2.0 [-5.9, +0.1] | +7.1 [-5.2, +19.7] |
| DeepSeek V4.1 Flash (off) | workhorses | +14.6 [+3.9, +25.4] | -10.6 [-31.1, +9.0] | +15.2 [-64.8, +76.6] | +7.7 [-3.7, +25.0] | -3.5 [-8.3, -0.1] | +15.1 [-4.9, +37.4] |
| Qwen3.8-27B (off) | workhorses | +13.2 [-0.1, +25.9] | -9.4 [-24.0, +4.8] | -12.4 [-89.0, +41.0] | +4.3 [-4.5, +15.3] | +4.0 [-4.3, +15.0] | +18.4 [-1.2, +40.0] |
| LFM2.5-24B-A2B (on) | workhorses | +3.2 [-13.6, +21.6] | -24.9 [-54.3, +5.5] | +29.4 [-14.3, +77.6] | +8.0 [-7.2, +27.9] | +3.8 [-4.5, +14.9] | +5.4 [-18.5, +30.0] |
| LFM2.5-24B-A2B (off) | workhorses | +15.5 [-2.6, +33.8] | -0.0 [-28.2, +29.2] | -14.3 [-107.3, +69.0] | +1.4 [-14.4, +21.5] | +4.5 [-7.0, +17.1] | +17.5 [-10.8, +47.1] |
| GPT-6 Astra (on) | frontier | +3.3 [-3.0, +9.7] | -6.5 [-14.9, +1.8] | -8.9 [-22.1, +1.1] | -0.6 [-2.2, +0.4] | +0.0 [+0.0, +0.1] | +8.1 [+0.5, +16.1] |
| GPT-6.1 Terra | no group (exploratory) | +7.4 [+1.1, +13.9] | -6.6 [-18.8, +5.7] | +5.7 [-18.1, +40.1] | +0.1 [-1.0, +1.4] | -1.8 [-5.1, +0.0] | +9.3 [-1.7, +19.6] |
| GNUbg weak *(yardstick)* | yardstick | -7.5 [-21.3, +6.5] | -5.8 [-32.0, +20.2] | +3.4 [-12.5, +21.1] | +3.0 [-0.0, +7.8] | -3.6 [-10.5, +0.7] | -5.6 [-23.3, +11.9] |
| Random *(yardstick)* | yardstick | -11.3 [-23.3, +0.4] | -9.3 [-27.3, +8.8] | +7.6 [-57.2, +63.1] | +3.4 [-7.7, +16.9] | +0.5 [-5.6, +6.9] | -9.7 [-28.7, +9.8] |

**Per group, equal weight per setup.** `results.json` holds no group-level phase result, so no group interval was saved (§10.9 asks for one per group; this is a gap in the saved results, not filled here). The rows below are plain means of the saved per-setup point drops, each setup weighted equally, **without intervals**; Terra and the yardsticks are in no group.

| Group (setups) | opening | contact | holding | race | bear-off | opening − other phases |
| --- | --- | --- | --- | --- | --- | --- |
| decision models (12) | +3.6 | -11.6 | -5.3 | +6.5 | -1.9 | +8.9 |
| workhorses (9) | +6.3 | -8.6 | -0.4 | +1.7 | +0.4 | +9.7 |
| frontier (1) | +3.3 | -6.5 | -8.9 | -0.6 | +0.0 | +8.1 |

## 4. Engine rollout check (40 frozen pairs)

**Done.** 40 pairs (80 positions), frozen before any model call (`freeze/nack-paired.json`). Settings as saved: GNUbg 1.08.003 rollout: 1,296 trials per play, cubeless, variance reduction on, quasi-random dice, no truncation, no late evaluation, chequer play 1-ply, seed 1, 8 threads, nice 19; candidates: top 5 at 2-ply plus every play any setup chose. 436 plays rolled out; a play without a rollout used its 2-ply value plus the position's mean (rollout − 2-ply) shift, 447 uses (mostly Random's all-plays mean). **Direction changed (sign of the point estimate): no, for all 5 primary comparisons.**

| Comparison (40 pairs) | 2-ply A − B [99%] | Rollout A − B [99%] | Direction changed |
| --- | --- | --- | --- |
| decision models − workhorses | +6.36 [-3.28, +18.64] | +6.17 [-3.57, +18.72] | no |
| decision models − frontier | +16.49 [-1.68, +40.04] | +16.11 [-2.20, +39.49] | no |
| workhorses − frontier | +10.13 [-1.63, +24.58] | +9.94 [-1.64, +24.21] | no |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | -14.59 [-55.64, +18.77] | -15.61 [-56.62, +17.00] | no |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | +1.76 [-2.81, +6.99] | +2.73 [-1.97, +8.46] | no |

Per setup on the same 40 pairs (saved), the sign of the drop differs between 2-ply and rollout only for: GNUbg weak (+4.16 → -0.02). The rollout drop is smaller than the 2-ply drop for 25 of 25 rows. These 40 pairs are a subset; their drops are not the test's estimates. GNUbg's network learned standard play, so its early Nackgammon values are likely less accurate; this check bounds that, it does not remove it (§10.12).

## 5. Cost and seconds per decision, next to the final look

PR and drop: final look, all 500 pairs (as in item 1). Cost: saved in `results.json` (`cost_all`, all 1,000 recorded positions), labelled as in the corrected report: **recorded cost** is the cost stored with each answer, i.e. the provider's reported cost per response where the route reports one, otherwise the runner's list-price computation (Mercury Decide: list price; its provider-billed amount is unknown); **API-equivalent** is shown separately and never added to it (0 = none of that kind; setups on our GPUs have no list price). No invoice was checked.

**Seconds per decision: a descriptive read of logged latency, not a new result.** From `smoke/nack-paired.db` (opened read-only), per setup, over its 1,000 recorded positions (the paired-test sets only): **request s** = mean `request_ms`, the time on the clock (the answering attempt(s), including a second call where the setup's protocol makes one); **off-clock s** = mean `retry_ms`, which the runner keeps off the clock: failed attempts, backoff waits, request pacing and waiting for a request slot (`src/http.rs`, `src/players/llm.rs`, `src/players/mod.rs`). So request s **excludes retries and waits**; request + off-clock is the wall time per decision. Timed-out records **are included** in the means unless stated: LFM2.5-24B-A2B (on)'s 107 records without a choice each hit the 600 s limit (`request_ms` 600,000–600,003, no off-clock time). The scorer's saved `median_request_s` (median of `request_ms`) is given for reference.

| Setup | Group | Standard PR | Nackgammon PR | Drop | Recorded cost $/decision (provider-reported; Mercury Decide: list price) | API-equivalent $/decision | Request s, mean | Off-clock s, mean | Request + off-clock s, mean | Saved median request s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 26.33 | 27.93 | +1.60 | 0.00000 | 0.00000 | 2.60 | 0.00 | 2.60 | 2.35 |
| Jev 1.13.0 | decision models | 24.67 | 27.44 | +2.77 | 0.00013 | 0.00000 | 0.15 | 0.00 | 0.15 | 0.15 |
| GPT-6 Luna | decision models | 29.56 | 35.44 | +5.87 | 0.00027 | 0.00000 | 0.24 | 0.00 | 0.24 | 0.25 |
| Celeris-1 Decision | decision models | 26.86 | 30.93 | +4.08 | 0.00011 | 0.00000 | 0.17 | 0.00 | 0.17 | 0.17 |
| Decider v1.1 27B | decision models | 31.27 | 32.08 | +0.81 | 0.00006 | 0.00000 | 0.59 | 0.00 | 0.59 | 0.57 |
| Cygnet (Gemma 4 12B) | decision models | 28.46 | 28.66 | +0.20 | 0.00000 | 0.00000 | 0.72 | 0.00 | 0.72 | 0.64 |
| SubQ Snap Preview | decision models | 31.25 | 32.87 | +1.62 | 0.00014 | 0.00000 | 0.23 | 0.00 | 0.23 | 0.23 |
| Mercury Decide | decision models | 31.34 | 34.08 | +2.73 | 0.00006 | 0.00000 | 0.53 | 0.01 | 0.54 | 0.48 |
| Winnow-12B | decision models | 31.93 | 34.61 | +2.68 | 0.00000 | 0.00000 | 3.58 | 0.00 | 3.58 | 3.52 |
| Decider v1.2 27B | decision models | 31.72 | 29.03 | -2.68 | 0.00006 | 0.00000 | 1.27 | 0.00 | 1.27 | 1.08 |
| Decider Flash v1.2 | decision models | 40.23 | 48.01 | +7.78 | 0.00003 | 0.00000 | 0.53 | 0.00 | 0.53 | 0.51 |
| Open-Jev 27B v1.1 | decision models | 47.07 | 43.99 | -3.08 | 0.00000 | 0.00000 | 1.20 | 0.00 | 1.20 | 1.17 |
| GPT-6.1 Sol (high) | workhorses | 11.14 | 9.12 | -2.03 | 0.00807 | 0.00000 | 13.22 | 0.00 | 13.22 | 8.68 |
| GPT-6.1 Sol (low) | workhorses | 12.21 | 10.75 | -1.46 | 0.00602 | 0.00000 | 5.64 | 0.00 | 5.64 | 4.53 |
| Claude Sonnet 5.5 (low) | workhorses | 16.45 | 15.30 | -1.15 | 0.00873 | 0.00000 | 2.38 | 0.00 | 2.38 | 1.34 |
| Gemini 3.8 Flash (low) | workhorses | 16.71 | 15.41 | -1.30 | 0.00288 | 0.00000 | 2.68 | 0.00 | 2.68 | 2.11 |
| Gemma 4 31B (on) | workhorses | 17.97 | 16.84 | -1.13 | 0.00000 | 0.00000 | 219.11 | 0.00 | 219.11 | 208.61 |
| DeepSeek V4.1 Flash (off) | workhorses | 23.35 | 29.29 | +5.94 | 0.00027 | 0.00000 | 0.51 | 25.92 | 26.43 | 0.46 |
| Qwen3.8-27B (off) | workhorses | 26.89 | 31.65 | +4.76 | 0.00000 | 0.00000 | 1.56 | 0.00 | 1.56 | 1.58 |
| LFM2.5-24B-A2B (on) | workhorses | 37.78 | 42.54 | +4.77 | 0.00000 | 0.00000 | 383.78 | 0.00 | 383.78 | 374.25 |
| LFM2.5-24B-A2B (off) | workhorses | 46.44 | 50.87 | +4.43 | 0.00000 | 0.00000 | 0.35 | 0.00 | 0.35 | 0.34 |
| GPT-6 Astra (on) | frontier | 10.86 | 8.88 | -1.99 | 0.02951 | 0.00000 | 5.60 | 0.00 | 5.60 | 4.16 |
| GPT-6.1 Terra | no group (exploratory) | 13.18 | 16.22 | +3.04 | 0.00371 | 0.00000 | 2.71 | 10.55 | 13.26 | 2.50 |
| GNUbg weak *(yardstick)* | yardstick | 25.35 | 20.78 | -4.57 | 0.00000 | 0.00000 | 0.01 | 0.00 | 0.01 | 0.01 |
| Random *(yardstick)* | yardstick | 85.16 | 81.43 | -3.73 | no calls | no calls | no calls | no calls | no calls | no calls |

LFM2.5-24B-A2B (on): request s 383.78 with the 107 timeouts (1,000 records); **357.87 without them** (893 answered records). Nonzero off-clock time: DeepSeek V4.1 Flash (off) 25.92 s, GPT-6.1 Terra 10.55 s, Mercury Decide 0.01 s per decision; every other setup 0.00. Answers ran concurrently, so these per-decision times do not add up to run time.

**Per group, equal weight per setup** (plain means of the per-setup values above; no interval; descriptive). Terra and the yardsticks are in no group; Terra's own row is above.

| Group (setups) | Standard PR | Nackgammon PR | Drop | Recorded cost $/decision | API-equivalent $/decision | Request s, mean | Off-clock s, mean | Request + off-clock s, mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| decision models (12) | 31.72 | 33.76 | +2.03 | 0.00007 | 0.00000 | 0.99 | 0.00 | 0.99 |
| workhorses (9) | 23.22 | 24.64 | +1.43 | 0.00288 | 0.00000 | 69.91 | 2.88 | 72.79 |
| frontier (1) | 10.86 | 8.88 | -1.99 | 0.02951 | 0.00000 | 5.60 | 0.00 | 5.60 |

Workhorses without LFM2.5-24B-A2B (on)'s 107 timeouts (that setup at its 893 answered records): request s 67.04, request + off-clock s 69.92 (with them: 69.91 / 72.79). The group request means are dominated by two slow setups, Gemma 4 31B (on) (219.1 s) and LFM2.5-24B-A2B (on). The group PR and drop means here are on all 500 pairs and are not the primary comparisons (those are on the main 200 at 99%; report, Primary comparisons). For reference, the saved main-200 group drops: decision models −2.63, workhorses −0.49, frontier −2.37; no primary interval excludes 0.

