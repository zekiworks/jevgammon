# Nackgammon paired test: results

2026-10-28 · Method §10 (`tools/site/content/method-spec-2026-10-24.md`, with the addenda of 2026-10-27, §10.14 and its
correction (f)). Brief: `mailbox/Nackgammon and Terra - brief 2026-10-27.md`. Scores: `positions/nack-paired/results/results.json`
(sha256 `723da2a105624103198fc200406ddd384f034a0e442745bc7adf66964b68349a`), from `python3 tools/v3/nack_paired_score.py report --rollouts smoke/nack-engine-check.db`.

**Scope:** These results hold for these rosters only; each group is the setups in the run from that original league. The frontier group currently has 1 setup (GPT-6 Astra (on)); comparisons 2 and 3 rest on it.
**Groups:** Groups by original league (Method §10.14, amendment of 2026-10-27). It was written after the per-setup first looks and after six full-report calls on partial data had computed group results under the earlier group definitions; one returned those results into an agent's context. Whether a person saw them is not established. Nothing was published. See §10.14(e) and its correction (f) of 2026-10-28.

What this measures: how much a new starting setup (same rules) changes each setup's (model, settings and prompt) decision quality.
A larger drop is consistent with relying on familiar positions but is not proof, because Nackgammon positions also differ in
structure. "Kept" is a valid result. The paired test's standard prompt (`bg-v3-std-notable`) differs from the league prompt (no
opening table; the setup sentence on its own line), so the standard error rates here are not compared directly with league error rates.
**Random is slightly better on Nackgammon** on these pairs: its own drop is shown next to every result.

## What ran

- 24 setups + Random (no calls): 12 decision models, 9 workhorses, 1 frontier (original leagues, §10.14), GNUbg weak, and Terra. GPT-6.1 Terra
  passed its smoke test (50/50 valid, 9.8 PR) and belongs to no group (exploratory).
- Every setup answered the main 400 positions (200 pairs). **Every first look was "unclear"** (97.5% intervals about ±5 to ±20 PR),
  so the frozen rule extended every setup with the 300 reserve pairs (600 positions); every setup answered all 1,000.
- Answers: `smoke/nack-paired.db` (separate from v3.db). Runner built at 35cb13d; the stored `harness_commit` is the working tree's
  HEAD at run time (35cb13d → fbe9095 → 80c9807, "dirty" from uncommitted files: the knockout start option and configs, none used by `ask`).
- GPUs (bariton, claimed from compactor, released on the bus): GPU 0 GLiDE v1.2 + Cygnet, then Decider v1.1, Open-Jev, then
  Gemma 4 31B (on) (one replica behind the :8894 proxy, League 2 settings, 24 in flight); GPU 1 Decider v1.2 27B, Decider Flash,
  Winnow, then Qwen3.8-27B (off); GPU 3 LFM2.5-24B-A2B (on/off) (shared from ~01:00 with MissingPairs' gap matches; they stop it).
- **Invalid or missing answers** (never dropped): only **LFM2.5-24B-A2B (on)**: 107 of 1,000 timed out (600 s limit, no answer;
  main 200 pairs: 16 Nackgammon / 22 standard; all 500: 52 / 55). Every other setup: 0. Usual retries only.
- **Money (OpenRouter):** smoke $0.213; start: DeepSeek V4.1 Flash (off) $0.18 (ledger; provider-reported $0.117), Mercury
  Decide $0.022, Terra $1.489; extension (d): DeepSeek $0.236, Terra $2.220, Mercury $0.034 = **$2.489 of the $2.55 cap**.
  Total ≈ $4.39. Caps enforced by ledgers (`smoke/nack-paired-budget-{abc,c,d}.db`); Terra's last 3 extension positions were
  refused by the d ledger and finished at parallel 1 within it.
- Wall time: start 18:07–20:53 UTC (LFM2.5 (on) the long pole: 2.6 h; Gemma 4 31B (on) 400 in 63 min at 24 in flight),
  extensions to 00:59 UTC (LFM2.5 (on) +600: 4.1 h; Gemma +600: 93 min).

## Per setup (standard, Nackgammon and the drop together; not a ranking)

Drop = Nackgammon PR − standard PR on the same pairs (positive = worse on Nackgammon). First look on the main 200 pairs; final
on all 500 (every setup extended). Label from the final 97.5% interval. Bootstrap intervals are approximate. Rows by group, then
standard PR. Cost per decision over all 1,000 decisions (billed or API-equivalent; GPU setups have no list price).

| Setup | Group | Standard PR (200) | Nackgammon PR (200) | Drop [97.5%] (200) | Random's drop (200) | Standard / Nackgammon PR (500) | Drop [97.5%] (500) | Random's drop (500) | Label | Invalid N / S | $ per decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fastino GLiDE v1.2 (local) | decision models | 22.74 | 24.91 | +2.18 [-7.3, +11.9] | -4.56 | 26.33 / 27.93 | +1.60 [-5.3, +8.3] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| Jev 1.13.0 | decision models | 26.53 | 24.17 | -2.37 [-17.7, +10.0] | -4.56 | 24.67 / 27.44 | +2.77 [-5.2, +10.4] | -3.73 | unclear | 0 / 0 | $0.00013 billed |
| GPT-6 Luna | decision models | 28.27 | 34.11 | +5.84 [-10.6, +20.5] | -4.56 | 29.56 / 35.44 | +5.87 [-4.3, +15.1] | -3.73 | unclear | 0 / 0 | $0.00027 billed |
| Celeris-1 Decision | decision models | 29.71 | 28.47 | -1.24 [-18.3, +14.6] | -4.56 | 26.86 / 30.93 | +4.08 [-4.6, +12.6] | -3.73 | unclear | 0 / 0 | $0.00011 billed |
| Decider v1.1 27B | decision models | 30.42 | 28.64 | -1.78 [-17.3, +11.9] | -4.56 | 31.27 / 32.08 | +0.81 [-8.0, +9.2] | -3.73 | unclear | 0 / 0 | $0.00006 billed |
| Cygnet (Gemma 4 12B) | decision models | 31.33 | 24.48 | -6.85 [-22.4, +5.4] | -4.56 | 28.46 / 28.66 | +0.20 [-7.6, +7.4] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| SubQ Snap Preview | decision models | 31.91 | 29.66 | -2.25 [-18.1, +11.9] | -4.56 | 31.25 / 32.87 | +1.62 [-7.1, +10.1] | -3.73 | unclear | 0 / 0 | $0.00014 billed |
| Mercury Decide | decision models | 32.74 | 28.46 | -4.28 [-20.1, +8.8] | -4.56 | 31.34 / 34.08 | +2.73 [-5.9, +10.8] | -3.73 | unclear | 0 / 0 | $0.00006 billed |
| Winnow-12B | decision models | 34.33 | 33.43 | -0.89 [-18.0, +15.0] | -4.56 | 31.93 / 34.61 | +2.68 [-6.3, +11.2] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| Decider v1.2 27B | decision models | 34.68 | 22.80 | -11.87 [-27.9, +1.0] | -4.56 | 31.72 / 29.03 | -2.68 [-11.0, +5.2] | -3.73 | unclear | 0 / 0 | $0.00006 billed |
| Decider Flash v1.2 | decision models | 39.77 | 42.86 | +3.09 [-12.1, +20.1] | -4.56 | 40.23 / 48.01 | +7.78 [-2.2, +18.4] | -3.73 | unclear | 0 / 0 | $0.00003 billed |
| Open-Jev 27B v1.1 | decision models | 52.08 | 40.96 | -11.12 [-29.5, +6.8] | -4.56 | 47.07 / 43.99 | -3.08 [-13.3, +6.8] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| GPT-6.1 Sol (high) | workhorses | 9.88 | 8.43 | -1.45 [-5.6, +2.7] | -4.56 | 11.14 / 9.12 | -2.03 [-5.6, +1.4] | -3.73 | unclear | 0 / 0 | $0.00807 billed |
| GPT-6.1 Sol (low) | workhorses | 11.15 | 9.90 | -1.26 [-5.7, +3.3] | -4.56 | 12.21 / 10.75 | -1.46 [-5.0, +2.0] | -3.73 | unclear | 0 / 0 | $0.00602 billed |
| Claude Sonnet 5.5 (low) | workhorses | 13.96 | 14.50 | +0.54 [-5.0, +6.0] | -4.56 | 16.45 / 15.30 | -1.15 [-5.9, +3.3] | -3.73 | unclear | 0 / 0 | $0.00873 billed |
| Gemini 3.8 Flash (low) | workhorses | 15.92 | 11.81 | -4.11 [-9.7, +1.0] | -4.56 | 16.71 / 15.41 | -1.30 [-5.5, +2.9] | -3.73 | unclear | 0 / 0 | $0.00288 billed |
| Gemma 4 31B (on) | workhorses | 18.35 | 13.38 | -4.97 [-11.8, +1.8] | -4.56 | 17.97 / 16.84 | -1.13 [-6.2, +4.4] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| DeepSeek V4.1 Flash (off) | workhorses | 23.91 | 27.90 | +3.98 [-11.7, +18.0] | -4.56 | 23.35 / 29.29 | +5.94 [-2.5, +13.9] | -3.73 | unclear | 0 / 0 | $0.00027 billed |
| Qwen3.8-27B (off) | workhorses | 28.13 | 28.43 | +0.30 [-14.5, +12.1] | -4.56 | 26.89 / 31.65 | +4.76 [-3.6, +12.5] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| LFM2.5-24B-A2B (on) | workhorses | 38.20 | 37.55 | -0.65 [-15.2, +14.4] | -4.56 | 37.78 / 42.54 | +4.77 [-4.1, +13.5] | -3.73 | unclear | 52 / 55 | n/a (GPU) |
| LFM2.5-24B-A2B (off) | workhorses | 50.75 | 53.98 | +3.23 [-16.9, +22.1] | -4.56 | 46.44 / 50.87 | +4.43 [-6.5, +15.4] | -3.73 | unclear | 0 / 0 | n/a (GPU) |
| GPT-6 Astra (on) | frontier | 9.66 | 7.30 | -2.37 [-6.7, +1.8] | -4.56 | 10.86 / 8.88 | -1.99 [-5.5, +1.5] | -3.73 | unclear | 0 / 0 | $0.02951 billed |
| GPT-6.1 Terra | no group (exploratory) | 13.52 | 14.40 | +0.89 [-5.7, +8.6] | -4.56 | 13.18 / 16.22 | +3.04 [-0.9, +7.4] | -3.73 | unclear | 0 / 0 | $0.00371 billed |
| GNUbg weak | yardstick | 27.69 | 24.13 | -3.56 [-13.9, +7.3] | -4.56 | 25.35 / 20.78 | -4.57 [-10.3, +1.3] | -3.73 | unclear | 0 / 0 | — |
| Random | yardstick | 87.45 | 82.89 | -4.56 [-18.0, +7.9] | -4.56 | 85.16 / 81.43 | -3.73 [-11.4, +3.7] | -3.73 | unclear | 0 / 0 | — |

**Labels:** every setup, GNUbg weak and Random are **"unclear"** at the final look: every 97.5% interval contains 0 and reaches
past ±5 PR. No setup is "kept", "worse" or "better" on this evidence.

### By phase (main 200 pairs; descriptive, 95%)

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

By game-plan tag: PR per tag and set in `results.json` (`setups.<name>.tags`; descriptive, tags are not matched; the back-game row
is too thin to read, 10 Nackgammon vs 2 standard, and partly reflects Nackgammon's starting anchors).

## Primary comparisons (main 200 pairs, M = 5, 99% each)

Groups by original league (Method §10.14, amendment of 2026-10-27). It was written after the per-setup first looks and after six full-report calls on partial data had computed group results under the earlier group definitions; one returned those results into an agent's context. Whether a person saw them is not established. Nothing was published. See §10.14(e) and its correction (f) of 2026-10-28.
The frontier group currently has 1 setup (GPT-6 Astra (on)); comparisons 2 and 3 rest on it.
These results hold for these rosters only; each group is the setups in the run from that original league.

**primary rule (invalid = Random's error)**

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 23.36 / 22.88 / -0.49 | -2.14 [-10.1, +4.9] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.6, +12.0] | -4.56 |
| workhorses − frontier | 23.36 / 22.88 / -0.49 | 9.66 / 7.30 / -2.37 | +1.88 [-5.7, +9.3] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 38.20 / 37.55 / -0.65 | 50.75 / 53.98 / +3.23 | -3.88 [-27.0, +21.8] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.0, +2.6] | -4.56 |

**sensitivity (i): worst legal play**

**No primary interval excludes 0**, under the primary rule or either sensitivity rule. The effort pairs and group differences are
all small relative to their intervals.

## Secondary analyses (labelled secondary)

**1. Kept advantage over random play** (main 200; 1 = keeps its whole advantage over random play):

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 24.90 / 23.70 / -1.20 | -1.43 [-9.6, +5.7] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.6, +12.0] | -4.56 |
| workhorses − frontier | 24.90 / 23.70 / -1.20 | 9.66 / 7.30 / -2.37 | +1.17 [-6.5, +8.7] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 52.06 / 44.97 / -7.10 | 50.75 / 53.98 / +3.23 | -10.33 [-38.9, +19.7] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.0, +2.6] | -4.56 |

**2. Ranking.** **sensitivity (ii): pairs left out**

**3. Risk** (main 200 pairs; 66 Risk pays and 66 Safety pays positions per set, none thin; invalid answers with Random's weights):

| Comparison | A: standard / Nackgammon / drop | B: standard / Nackgammon / drop | A − B [99%] | Random's drop |
| --- | --- | --- | --- | --- |
| decision models − workhorses | 32.88 / 30.25 / -2.63 | 22.52 / 22.36 / -0.16 | -2.47 [-10.6, +4.7] | -4.56 |
| decision models − frontier | 32.88 / 30.25 / -2.63 | 9.66 / 7.30 / -2.37 | -0.26 [-14.6, +12.0] | -4.56 |
| workhorses − frontier | 22.52 / 22.36 / -0.16 | 9.66 / 7.30 / -2.37 | +2.21 [-5.5, +9.6] | -4.56 |
| LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off) | 30.59 / 32.91 / +2.32 | 50.75 / 53.98 / +3.23 | -0.91 [-24.1, +25.2] | -4.56 |
| GPT-6.1 Sol (high) − GPT-6.1 Sol (low) | 9.88 / 8.43 / -1.45 | 11.15 / 9.90 / -1.26 | -0.19 [-3.0, +2.6] | -4.56 |

Exploratory (not tested): GPT-6.1 Terra against GPT-6.1 Sol (low) is in the tables above, no comparison is drawn.

## Engine check (40 frozen pairs, 80 positions)

Rollouts: GNUbg 1.08.003 rollout: 1,296 trials per play, cubeless, variance reduction on, quasi-random dice, no truncation, no late evaluation, chequer play 1-ply, seed 1, 8 threads, nice 19; candidates: top 5 at 2-ply plus every play any setup chose. 436 plays rolled out (45 min);
plays without a rollout used 2-ply + the position's mean shift (447 uses, mostly Random's all-plays mean).
**No comparison changes direction.**

| Setup | K [95%] | Standard advantage over Random (PR) | unstable |
| --- | --- | --- | --- |
| GNUbg weak | 0.98 [+0.8, +1.2] | 59.8 | no |
| Celeris-1 Decision | 0.94 [+0.8, +1.1] | 57.7 | no |
| SubQ Snap Preview | 0.96 [+0.8, +1.2] | 55.5 | no |
| Cygnet (Gemma 4 12B) | 1.04 [+0.9, +1.3] | 56.1 | no |
| Decider v1.2 27B | 1.14 [+0.9, +1.4] | 52.8 | no |
| Fastino GLiDE v1.2 (local) | 0.90 [+0.7, +1.1] | 64.7 | no |
| DeepSeek V4.1 Flash (off) | 0.87 [+0.7, +1.1] | 63.5 | no |
| Jev 1.13.0 | 0.96 [+0.8, +1.2] | 60.9 | no |
| GPT-6 Luna | 0.82 [+0.6, +1.0] | 59.2 | no |
| Decider v1.1 27B | 0.95 [+0.8, +1.2] | 57.0 | no |
| LFM2.5-24B-A2B (on) | 0.92 [+0.7, +1.2] | 49.2 | no |
| Qwen3.8-27B (off) | 0.92 [+0.8, +1.1] | 59.3 | no |
| Mercury Decide | 0.99 [+0.8, +1.2] | 54.7 | no |
| Winnow-12B | 0.93 [+0.7, +1.2] | 53.1 | no |
| LFM2.5-24B-A2B (off) | 0.79 [+0.5, +1.2] | 36.7 | no |
| Open-Jev 27B v1.1 | 1.19 [+0.8, +1.8] | 35.4 | no |
| Decider Flash v1.2 | 0.84 [+0.6, +1.2] | 47.7 | no |
| Gemini 3.8 Flash (low) | 0.99 [+0.8, +1.2] | 71.5 | no |
| Claude Sonnet 5.5 (low) | 0.93 [+0.8, +1.1] | 73.5 | no |
| GPT-6.1 Sol (low) | 0.96 [+0.8, +1.1] | 76.3 | no |
| GPT-6 Astra (on) | 0.97 [+0.8, +1.1] | 77.8 | no |
| GPT-6.1 Sol (high) | 0.96 [+0.8, +1.1] | 77.6 | no |
| Gemma 4 31B (on) | 1.01 [+0.8, +1.2] | 69.1 | no |
| GPT-6.1 Terra | 0.93 [+0.8, +1.1] | 73.9 | no |

Spearman ρ = 0.87 [+0.7, +0.9] over 23 model setups. Largest rank changes (1 = lowest error rate): Decider v1.2 27B 19 → 8; GPT-6 Luna 12 → 19; Cygnet (Gemma 4 12B) 15 → 10; DeepSeek V4.1 Flash (off) 9 → 12; Fastino GLiDE v1.2 (local) 8 → 11.

## Files

- Scorer `tools/v3/nack_paired_score.py`; results `positions/nack-paired/results/results.json` + `standard-vs-nackgammon.svg`.
- Configs `leagues/nack-paired.json`, `leagues/nack-paired-d.json`, `leagues/smoke-terra.json`; rollouts `smoke/nack-engine-check.db`.
- Release bundle (local, not published): `release/nack-paired/`.
