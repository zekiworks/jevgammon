# Clear-risk scan: steps 0–3 (2026-10-29)

Offline. No model calls, and no change to the site or the thread. GNUbg 1.08.003 ran on CPU only (Method spec §0:
`nice -n 19`, at most 8 threads, no GPU). League data came from `v3.db`, opened read-only (`file:…?mode=ro`), and
from the site's GNUbg shards (`~/.local/state/bg-site/plays/s*.db`). **Step 4 is waiting for Can's go.**

## Step 0: method, committed before any computation

- The thresholds and rules are in `mailbox/Clear-risk scan - method 2026-10-29.md`, commit
  **`a1fb143a8916baa7d388cb2b18a12d8ecd97d859`** (2026-10-29T17:42:00Z), pushed before any board was parsed or any
  gap was computed. The thresholds: clearly safe = 0 hitting rolls, clearly unsafe = 12 or more, in between = 1–11,
  clear gap = 0.04 equity.
- These are not in the Method spec file (`tools/site/content/method-spec-2026-10-24.md`). The site's Method page
  renders that file from §10 to its end (`tools/site/method.py`, `nack_spec_text`), so adding text there would change
  the website.
- **Equity used.** The league games have **no doubling cube**. A game scores 1, 2 or 3 points (single, gammon,
  backgammon). A match is rounds of two games: 3 rounds, or first to 5 points after a full round. No match-score
  equity is used anywhere. Every engine value on the site is GNUbg 1.08 **cubeless money equity** for the mover at
  2-ply (`engine.PLY2`: cubeless, 2-ply, deterministic, prune, no noise), as written by `score_plays.py`. That same
  equity is used everywhere below. For Bray, this means his 1-1 to 7 score and the centred cube are ignored. The
  rollouts are cubeless money rollouts.

## Step 1: Bray validation ("Understanding Risk")

`XGID=-BB-BaB-B---cBa-bb-d-bC---:0:0:-1:00:1:1:0:7:10`. The position string was parsed by hand. Red (bottom,
uppercase) is set to play 42 by hand.

```
Red (bottom, X, to play 42, moves 24->1) / White (top, O)
 13  14  15  16  17  18  19  20  21  22  23  24
 2X  1O   .  2O  2O   .  4O   .  2O  3X   .   .
 3O   .   .   .  2X   .  2X  1O  2X   .  2X  2X
 12  11  10   9   8   7   6   5   4   3   2   1
bar: Red 0, White 0; off: Red 0, White 0
Red checkers (point: n): {1: 2, 2: 2, 4: 2, 6: 2, 8: 2, 13: 2, 22: 3}
White checkers (Red's numbering, point: n): {5: 1, 12: 3, 14: 1, 16: 2, 17: 2, 19: 4, 21: 2}
```

- **Board check: no mismatch.** Red has 2 checkers on 1, 2, 4, 6, 8 and 13, and 3 on 22. White has blots on 5 and 14
  (plus 3 on 12, and 2, 2, 4 and 2 on 16, 17, 19 and 21). GNUbg's position class is contact.
- **XGID cross-check.** GNUbg's own import of the full XGID (`setgnubgid`) gives the same board, with **White on roll
  and the dice not rolled** (posinfo turn 0, dice (0, 0)), at 1-1 in a 7-point match. This confirms Can's warning.
  Its position ID, `m5nBAA6YZ5MDAg`, is exactly my parse seen from White's side. Red on roll is `mGeTAwKbmcEADg`.
- Hitting rolls come from the site's counter (`describe.py` `hitting_rolls`, the number shown to the models).
  **22/18 22/20 → 36, 8/4 8/6 → 0**, as expected. The runner's notation is used throughout: 22/18 22/20 is Bray's
  22/20 22/18, and 8/4 8/6 is his 8/6 8/4.

All 20 legal plays, with 2-ply cubeless money equity for Red:

| play | 2-ply | hitting rolls | bin |
|---|---:|---:|---|
| 22/18 22/20 | −0.3922 | 36 | unsafe |
| 22/18 8/6 | −0.4055 | 35 | unsafe |
| 13/9 22/20 | −0.4873 | 34 | unsafe |
| 8/4 22/20 | −0.4890 | 34 | unsafe |
| 8/4 8/6 | −0.4973 | 0 | safe |
| 22/18 13/11 | −0.5343 | 35 | unsafe |
| 13/9 13/11 | −0.5789 | 23 | unsafe |
| 22/18 4/2 | −0.5817 | 33 | unsafe |
| 22/18 6/4 | −0.6116 | 33 | unsafe |
| 13/9 9/7 | −0.6372 | 23 | unsafe |
| 8/4 4/2 | −0.6392 | 13 | unsafe |
| 6/2 6/4 | −0.6466 | 0 | safe |
| 6/2 22/20 | −0.6710 | 34 | unsafe |
| 13/9 8/6 | −0.7013 | 30 | unsafe |
| 8/4 13/11 | −0.7508 | 31 | unsafe |
| 8/4 6/4 | −0.7645 | 20 | unsafe |
| 13/9 6/4 | −0.7695 | 25 | unsafe |
| 13/9 4/2 | −0.7731 | 25 | unsafe |
| 6/2 13/11 | −0.8295 | 26 | unsafe |
| 6/2 4/2 | −0.8457 | 11 | in between |

- **Step 3 at 2-ply: Risk wins.** The best unsafe play is 22/18 22/20 (−0.3922, 36 hitting rolls). The best safe play
  is 8/4 8/6 (−0.4973, 0 hitting rolls). Gap = **+0.1051** (≥ 0.04).
- **Step 4 rollout (the validation only): Risk wins, kept.**

  | play | rollout equity for Red | SE | W / WG / WBG – L / LG / LBG (Red) |
  |---|---:|---:|---|
  | 22/18 22/20 | **−0.403** | 0.004 | 0.355 / 0.138 / 0.004 – 0.645 / 0.240 / 0.015 |
  | 8/4 8/6 | **−0.503** | 0.003 | 0.282 / 0.068 / 0.001 – 0.718 / 0.131 / 0.005 |

  The rollout gap is **+0.100**. Its SE is about 0.005 (the two SEs combined as independent), so the gap is about
  20 SE. That passes both conditions: gap ≥ 0.04 and more than 3 SE. Both plays used the same seed, so this way of
  combining the SEs is conservative.
- **Rollout settings.** GNUbg 1.08.003 on CPU, `nice -n 19`, 8 threads.
  - 1,296 games per play, no truncation (GNUbg ends cubeless games at its one-sided bear-off database, which is exact).
  - Variance reduction (lookahead) on, quasi-random dice, Mersenne Twister with seed 20261029.
  - Cubeless, in a money session.
  - Checker play at 2-ply, cubeless, pruning, no noise (the scorer's settings). GNUbg's default move filter was used.
  - Each play was rolled out as the position after it, with White on roll and the dice not rolled. The printed
    equity is White's and is negated above.
  - Position IDs, with White on roll: `m3PAAA6YZ5MDAg` (after 8/4 8/6) and `m5nBIAmYZ5MDAg` (after 22/18 22/20).
- **Time:** 600.7 CPU-s (75.3 s wall) for 8/4 8/6 and 612.1 CPU-s (77.0 s wall) for 22/18 22/20, so about
  **606 CPU-s per 1,296-game rollout of one play**. The machine's load average was about 5–9 out of 48 cores.

## Steps 2–3: league decisions

**Data.** The three league datasets as published: leagues 1–3, each league's `league_match_view` without late-entry
matches, and turns decided by the model or by fallback.

- The counts (36,995 / 39,538 / 16,355) are the same as in the site's `snap.db`.
- Leagues 1–3 contain 0 late-entry decisions.
- No turn is in two leagues.
- Every valid decision has 2-ply values for all of its legal plays in the shards: plays = `legal_count`, checked on
  each one. **No play was missing, so GNUbg evaluated nothing new for the leagues.**
- Not asked, and not counted as decisions: the runner plays forced moves (1 legal play) itself, 15,831 of them
  (6,853 / 6,539 / 2,439), and turns with no legal move, 7,348 of them (2,532 / 3,345 / 1,471). So the reason
  "forced move" below counts 0.

Each decision is skipped for the first reason that applies, in the pre-registered order:

| | League 1 | League 2 | League 3 | Total |
|---|---:|---:|---:|---:|
| league decisions | 36,995 | 39,538 | 16,355 | 92,888 |
| skip: invalid answer (fallback) | 0 | 50 | 36 | 86 |
| skip: forced move (1 play) | 0 | 0 | 0 | 0 |
| skip: 2 legal plays | 3,661 | 3,819 | 1,385 | 8,865 |
| skip: no contact (race or bear-off) | 5,184 | 5,677 | 2,499 | 13,360 |
| skip: safe bin empty | 10,828 | 10,095 | 4,070 | 24,993 |
| skip: unsafe bin empty | 1,937 | 2,589 | 1,227 | 5,753 |
| **scanned** (both bins non-empty) | 15,385 | 17,308 | 7,138 | 39,831 |
| **Risk wins** (gap ≥ +0.04) | 4,498 | 4,304 | 1,645 | **10,447** |
| **Safety wins** (gap ≤ −0.04) | 8,186 | 9,960 | 4,247 | **22,393** |
| not flagged (\|gap\| < 0.04) | 2,701 | 3,044 | 1,246 | 6,991 |
| **flagged** | 12,684 | 14,264 | 5,892 | **32,840** |

- Median |2-ply gap| among the flagged decisions: 0.136 for Risk wins and 0.208 for Safety wins.
- The 32,840 flagged decisions contain **30,649 distinct (position, dice) pairs**, with the position taken from the
  mover's side.

## Step 4 estimate (not run)

The step-4 settings are the same as in the Bray run, which cost about 606 CPU-s per play.

| | rollouts | CPU time | wall at 8 processes (§0 limit) |
|---|---:|---:|---:|
| all flagged decisions (2 × 32,840) | 65,680 | ≈ 11,060 CPU-h | ≈ 1,380 h ≈ 58 days |
| distinct (position, dice) only (2 × 30,649) | 61,298 | ≈ 10,320 CPU-h | ≈ 1,290 h ≈ 54 days |

[INFERENCE] The Bray position is a middle-game contact position. Many flagged positions come later in the game,
with shorter games left, so they should roll out faster than Bray. The figures above are therefore likely an upper
bound. Most of the cost comes from 2-ply checker play, which was pre-registered. Cheaper settings would need Can's
decision.
