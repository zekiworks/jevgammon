# Clear-risk follow-up: check-1 rollouts (2026-10-30)

**The rollouts confirm 189 of the 200 sample positions (94.5%): 93 of 100 Risk wins and 96 of 100 Safety wins.**
- No position flipped direction. All 11 that failed have a rollout gap below 0.04, and all 11 are in the smallest band
  (0.04–0.08).
- **Back games and prime-vs-prime agree too:** 39 of 40 back-game positions and 40 of 40 prime-vs-prime positions are
  confirmed. These counts combine the sample with the oversample.

The rule, the settings and the oversample were fixed in `Clear-risk scan - method 2026-10-29.md` (amendment
2026-10-29T20:45Z), which was pushed before the first rollout. The website and the thread were not changed.

## Rule and settings

**Confirmed** means all three hold:
- the rollout gap (best unsafe − best safe) points the same way as the scan's group;
- |rollout gap| ≥ 0.04;
- |rollout gap| > 3 standard errors of the gap.

The standard error of the gap combines the two plays' SEs as if they were independent.

**Engine and run**
- GNUbg 1.08.003 on CPU, as a transient systemd user unit (`clearrisk-rollouts`).
- `nice` 19, 8 threads, no GPU.
- 520 rollouts (260 positions × 2 plays) in about 9.1 h of rollout wall time (mean 63 s per rollout). The run went
  from 20:42 to 05:51 UTC.

**Rollout settings**
- 1,296 games per play, variance reduction on, quasi-random dice.
- Mersenne Twister, seed 20261029, the same seed for both plays.
- No truncation. Cubeless, in a money session, with Jacoby set off explicitly. The initial-position option, the "later"
  settings and the STD/JSD stops are off.
- Checker play: **2-ply**, cubeless, prune, noise 0, deterministic.
- What is rolled out: the position after the play, with the opponent on roll.
- GNUbg's cubeless equity counts gammons and backgammons, so scoring is 1/2/3 points.
- All 520 rollouts ran their full 1,296 games.

**Code and data** (in `/tmp/clearrisk`)
- `roll.py` and `rollwrap.py`: the rollout itself; results go to `roll_res.jsonl`, the raw output to `roll.raw`.
- `over.py`: the oversample draw.
- `rollrep.py`: the tables below.

## Agreement per group and gap band (the 200; band = |3-ply gap|)

| group | 0.04–0.08 | 0.08–0.15 | 0.15+ | all | not confirmed: why |
|---|---:|---:|---:|---:|---|
| Risk wins | 79% (27/34) | 100% (33/33) | 100% (33/33) | **93% (93/100)** | gap < 0.04: 7 |
| Safety wins | 88% (30/34) | 100% (33/33) | 100% (33/33) | **96% (96/100)** | gap < 0.04: 4 |
| **both** | 84% (57/68) | 100% (66/66) | 100% (66/66) | **94.5% (189/200)** | gap < 0.04: 11 |

- **The SE condition removed nothing.** "Same direction and ≥ 0.04" gives the same 189. Each play's SE is 0.001–0.008,
  and the largest SE of a gap is 0.011.
- **The 3-ply gaps were accurate on average.** The mean of (rollout gap − 3-ply gap) is +0.003, and the mean of its
  absolute value is 0.013.
  - Only 6 of the 200 differ by more than 0.04.
  - 172 of 200 stay in the same band.
- **The 11 positions that were not confirmed** all have a 3-ply gap of 0.040–0.062 and a rollout gap of 0.021–0.038 in
  the same direction:

| sample id | group | league, turn | best safe | best unsafe | gap 2-ply / 3-ply / rollout (SE) |
|---|---|---|---|---|---|
| 4 | Risk wins | L3, 116765 | 24/20 13/7 | 20/16 16/10* | +0.051 / +0.040 / +0.036 (0.006) |
| 5 | Risk wins | L2, 152982 | 10/4 8/4 | 24/18 7/3 | +0.044 / +0.046 / +0.038 (0.004) |
| 11 | Risk wins | L2, 26735 | 4/2 5/1 | 13/11 11/7 | +0.045 / +0.040 / +0.022 (0.004) |
| 13 | Risk wins | L3, 116069 | 4/3 6/1 | 23/22 6/1 | +0.040 / +0.046 / +0.021 (0.005) |
| 18 | Risk wins | L1, 150391 | 24/22 24/22 6/4 6/4 | 24/22 13/11 13/11 6/4 | +0.047 / +0.041 / +0.037 (0.006) |
| 26 | Risk wins | L1, 184833 | 13/7 7/3 | 24/18 18/14 | +0.046 / +0.045 / +0.032 (0.001) |
| 30 | Risk wins | L1, 180726 | 6/3 3/2 | 6/3 24/23 | +0.059 / +0.062 / +0.027 (0.006) |
| 104 | Safety wins | L2, 89016 | 6/4 8/4 | 5/3* 8/4 | −0.061 / −0.047 / −0.029 (0.003) |
| 107 | Safety wins | L3, 152696 | 18/14 14/10 11/7 10/6 | 18/14 14/10 11/7 7/3 | −0.044 / −0.052 / −0.034 (0.004) |
| 112 | Safety wins | L3, 113656 | 13/10 10/8 | 24/21 13/11 | −0.041 / −0.047 / −0.037 (0.006) |
| 123 | Safety wins | L2, 159719 | 13/9 13/8 | 8/4 9/4 | −0.056 / −0.047 / −0.021 (0.004) |

## Back games and prime-vs-prime

**Classifier rules:** the same as in the scan's step-4 amendment.
- **Back game:** 2 or more anchors on the side's points 18–24, for either side.
- **Prime-vs-prime:** both sides have a prime of 4 or more (`longest_prime`).

**Oversample**
- **Draw:** 30 back-game and 30 prime-vs-prime kept positions, not in the 200, Bray excluded. Each distinct (position,
  dice) counts once.
- **Seed:** `random.Random(2026103003)`. The back games were drawn first, then prime-vs-prime from what was left.
- **Pools:** 907 back-game and 2,108 prime-vs-prime positions.
- **Overlap:** 2 of the prime-vs-prime draws are also back games, and 1 back-game draw is also prime-vs-prime. They
  count in both rows.
- **Not used in Part 2.**

**Group and band**
- **The draws are mostly Safety wins:** 22 of 30 back games and 28 of 30 prime-vs-prime positions.
- **Most are in the 0.15+ band:** 19 back games and 26 prime-vs-prime positions.

| positions | Risk wins | Safety wins | all | not confirmed: why |
|---|---:|---:|---:|---|
| back game: in the 200 | 67% (2/3) | 100% (5/5) | **88% (7/8)** | gap < 0.04: 1 (sample 13) |
| back game: oversample (30) | 100% (8/8) | 100% (22/22) | **100% (30/30)** | – |
| back game: both | 91% (10/11) | 100% (29/29) | **98% (39/40)** | gap < 0.04: 1 |
| prime-vs-prime: in the 200 | 100% (6/6) | 100% (3/3) | **100% (9/9)** | – |
| prime-vs-prime: oversample (30) | 100% (2/2) | 100% (28/28) | **100% (30/30)** | – |
| prime-vs-prime: both | 100% (8/8) | 100% (32/32) | **100% (40/40)** | – |
| neither, in the 200 | 93% (85/91) | 96% (88/92) | **95% (173/183)** | gap < 0.04: 10 |

In the oversample, the mean of (rollout gap − 3-ply gap) is −0.004, and the mean of its absolute value is 0.015. 4 of
the 60 differ by more than 0.04.

[INFERENCE] Every back-game and prime-vs-prime position here was already kept by the step-4 3-ply stability check, and
most are large-gap Safety wins. So these figures say the kept positions of these types are reliable. They say nothing
about the positions step 4 dropped.

## Consequence for Part 2

**Part 2 uses the 189 confirmed positions** (93 Risk wins, 96 Safety wins). The results are in
`Clear-risk follow-up - part 2 2026-10-30.md`.
