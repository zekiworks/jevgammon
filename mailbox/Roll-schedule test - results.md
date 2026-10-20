# Roll-schedule test: results

**Question.** In a round robin, how much luck do shared roll schedules remove from the standings?

**Answer.** None. In this test they added a little. Scheme B (round r of every match uses
roll schedule r) leaves the expected table unchanged. Compared with the current scheme A, it makes
league points **about 10% more scattered**: the SD ratio B/A is 1.10 [1.06, 1.14] and the variance
ratio is 1.20 [1.11, 1.29]. Rank correlation with the true order is **slightly worse**:
ρ = 0.864 vs 0.890, B − A = −0.026 [−0.038, −0.014]. The stronger neighbour finishes above the
weaker one about equally often under both schemes (72% under each).

Everything ran on the CPU of bariton with GNUbg 1.08 players only and no model calls. It used at
most 24 processes under `nice -n 19`. Nothing running or paused was touched: v3.db, league.db
and replay.db were opened read-only. Scripts: `experiments/roll-schedule/`.

## Setup

### Players and true strength

There are eight cubeless GNUbg configurations. All use deterministic noise. The named ones are
GNUbg's predefined levels (eval.c): **Beginner = 0-ply, noise 0.060, deterministic**, our league
anchor "GNUbg weak". The near-equal pair is **Casual (0.050) vs n0.055**, which differ only by
noise 0.050 vs 0.055.

The true order comes from the **error rate on the v1 set**: replay.db, 1,000 positions, each
option's 2-ply equity from `tools/gnubg_eval.py`, PR = 500 × mean loss. Each configuration's play
is `gnubg.findbestmove` with its own eval context.

I used PR because it separates every neighbouring pair clearly. The paired SE over positions puts
every gap at ≥ 3.2 SE, including the near-equal pair at 1.83 ± 0.58. PR also costs 1 minute
instead of hours.

An independent long run then checked the order: 400 matches per pair for all 28 pairs, 11,200
matches in total, under the same match rules. **In all 28 pairs the PR-stronger player scores more
league points per match.**

| # | player | gnubg context | v1 PR | PR gap to next (paired SE) | long run v next: W / D / L % | league pts/match diff (SE) | points/game diff (SE) |
|---|---|---|---:|---|---|---|---|
| 1 | 1-ply | 1-ply, noise 0 | 0.51 | 3.50 (0.35) | 62.3 / 5.0 / 32.8 | +0.89 (0.14) | +0.185 (0.033) |
| 2 | Advanced | 0-ply, noise 0.015 | 4.01 | 4.93 (0.53) | 65.5 / 2.2 / 32.2 | +1.00 (0.14) | +0.267 (0.036) |
| 3 | n0.030 | 0-ply, noise 0.030 | 8.94 | 4.25 (0.65) | 68.8 / 3.5 / 27.8 | +1.23 (0.13) | +0.251 (0.037) |
| 4 | Intermediate | 0-ply, noise 0.040 | 13.18 | 3.46 (0.61) | 64.5 / 2.8 / 32.8 | +0.95 (0.14) | +0.247 (0.048) |
| 5 | Casual | 0-ply, noise 0.050 | 16.65 | **1.83 (0.58)** | **56.8 / 1.5 / 41.8** | **+0.45 (0.15)** | **+0.101 (0.049)** |
| 6 | n0.055 | 0-ply, noise 0.055 | 18.48 | 3.32 (0.77) | 59.5 / 1.2 / 39.2 | +0.61 (0.15) | +0.200 (0.058) |
| 7 | **Beginner** (anchor) | 0-ply, noise 0.060 | 21.80 | 18.68 (2.25) | 72.0 / 2.0 / 26.0 | +1.38 (0.13) | +0.589 (0.063) |
| 8 | n0.100 | 0-ply, noise 0.100 | 40.48 | | | | |

Other configurations were measured and left out:

| configuration | v1 PR |
|---|---:|
| Expert (0-ply, noise 0) | 1.30 |
| 1-ply with pruning | 0.52 |
| 1-ply, noise 0.02 | 1.12 |
| 0-ply, noise 0.005 / 0.010 / 0.020 / 0.025 / 0.035 / 0.045 | 1.7 / 2.4 / 5.6 / 7.3 / 11.2 / 15.1 |
| 0-ply, noise 0.070 / 0.080 / 0.120 | 26.7 / 30.9 / 43.4 |
| non-deterministic noise 0.030 / 0.060 | 7.7 / 17.1 |

Expert was left out because its gap to 1-ply (0.8 PR) would have formed a second near-equal pair.

### Match and league rules

These follow `src/runner.rs`, `src/dice.rs` and `src/league.rs` as v1 leagues are configured
(`rounds 3`, `max_turns 300`, fixtures not decisive).

- **Rounds:** each round is two games on the same round seed, with model1 white in game 1 and
  model2 white in game 2.
- **Opening:** the opening roll (one die per side, ties rerolled) is the first turn's roll, and
  the higher die starts.
- **Ending a match:** a match lasts 3 rounds, or ends after the round in which a player reaches
  5 if that player is ahead. A level score at that point, or after round 3, adds **exactly one**
  extra round, and a tie after it is a draw (`rounds_after` with `decisive = false`).
- **Turn limit:** turn 300 ends the game on pip count. Lower pips wins; equal pips goes to the
  side due to roll next. The win is worth 1 point.
- **Scoring:** there is no cube. Single, gammon and backgammon score 1, 2 and 3.
- **Turns without a choice:** a turn with one distinct legal result is forced and a turn with
  none is a pass; neither asks the player, as in the runner. Legal plays come from
  `tools/v3/rules.py`.
- **League table:** a win is worth 3 points and a draw 1. Players are ranked by points, then
  games won, then fewer games lost. Playoffs (decisive matches for tied top-3 places) are not
  simulated; ties on the full key are reported separately and occur 0–1.2% of the time per pair.
- **Fixture:** `draw_fixture` (circle method on a shuffled list, model1 drawn per match),
  replicated exactly.

The Python port of `Dice`, `derive_seed`, `round_seed` and `draw_fixture` reproduces league 13 of
league.db exactly: its fixture, all 21 match seeds, and 1,187 recorded rolls from 5 matches with
openings.

### Schemes

Replay i has league seed `derive_seed(20261020, "replay i")`, and A and B share it. There are
**500 replays per scheme**.

- **A (current):** match seed = `derive_seed(league seed, "matchday D: M1 v M2")`. Round r of
  that match rolls from `round_seed(match seed, r)`. This is the runner's dependence structure,
  bit for bit.
- **B (shared):** round r of *every* match rolls from schedule r, `Dice::new(round_seed(
  derive_seed(league seed, "shared schedule"), r))`. This includes the opening roll. Both games
  of the round use the schedule with seats swapped, exactly as in A, and extra rounds use
  schedules 4, 5 and so on. The schedule is an unbounded SplitMix64 stream, so no game can run
  out of rolls: at most 299 rolls plus the opening are needed.

## Results

### (1) Scatter of league points across replays (pure luck, since the players are fixed)

| player | mean A | mean B | SD A | SD B | SD B/A |
|---|---:|---:|---:|---:|---:|
| 1-ply | 18.44 | 18.32 | 2.49 | 2.92 | 1.17 |
| Advanced | 16.75 | 16.90 | 2.67 | 2.91 | 1.09 |
| n0.030 | 13.74 | 13.95 | 3.00 | 3.58 | 1.19 |
| Intermediate | 11.46 | 11.58 | 3.22 | 3.39 | 1.05 |
| Casual | 8.47 | 8.52 | 3.14 | 3.37 | 1.07 |
| n0.055 | 7.17 | 7.12 | 3.13 | 3.24 | 1.04 |
| Beginner | 5.74 | 5.69 | 2.99 | 3.19 | 1.07 |
| n0.100 | 1.86 | 1.60 | 2.10 | 2.34 | 1.11 |
| **mean SD over players** | | | **2.84** [2.77, 2.91] | **3.12** [3.02, 3.20] | **1.097 [1.056, 1.139]** |

- **CIs:** brackets are 95% bootstrap CIs over replays (4,000 resamples, each scheme resampled
  independently).
- **Variance ratio B/A:** 1.20 [1.11, 1.29].
- **SD of finishing place:** 1.00 under A, 1.12 under B.
- **Means:** the means agree, so B is unbiased; it is only noisier.

The table is decided by differences between neighbours, so I also looked at the SD of each
neighbouring pair's points difference. The B/A ratio is between 0.98 and 1.16. B is never
significantly lower, and it is significantly higher for Advanced v n0.030, at 1.16 [1.06, 1.26].

### (2) Spearman correlation of each replay's standings with the true order

| | mean ρ [95% CI] | median ρ | exact true order | top place right |
|---|---|---:|---:|---:|
| A | 0.890 [0.882, 0.897] | 0.905 | 3.6% | 62.2% |
| B | 0.864 [0.854, 0.873] | 0.898 | 3.2% | 59.0% |
| **B − A** | **−0.026 [−0.038, −0.014]** | | | |

### (3) Stronger above weaker: % of replays above / tied / below on the league key

| pair (stronger v weaker) | ΔPR | A | B | B − A, above [95% CI] |
|---|---:|---|---|---|
| 1-ply v Advanced | 3.5 | 67.8 / 0.2 / 32.0 | 65.8 / 0.4 / 33.8 | −2.0 [−7.6, 3.8] |
| Advanced v n0.030 | 4.9 | 77.6 / 0.4 / 22.0 | 76.4 / 0.8 / 22.8 | −1.2 [−6.4, 4.2] |
| n0.030 v Intermediate | 4.2 | 70.6 / 0.8 / 28.6 | 72.0 / 0.4 / 27.6 | +1.4 [−4.2, 7.0] |
| Intermediate v Casual | 3.5 | 75.4 / 0.2 / 24.4 | 73.0 / 1.2 / 25.8 | −2.4 [−7.8, 2.6] |
| **Casual v n0.055 (near-equal pair)** | 1.8 | **62.4 / 0.6 / 37.0** | **62.6 / 1.0 / 36.4** | +0.2 [−5.6, 6.2] |
| n0.055 v Beginner | 3.3 | 64.2 / 0.0 / 35.8 | 66.2 / 0.2 / 33.6 | +2.0 [−4.0, 8.0] |
| Beginner v n0.100 | 18.7 | 86.8 / 0.8 / 12.4 | 85.4 / 0.0 / 14.6 | −1.4 [−5.6, 3.0] |
| mean of the 7 neighbouring pairs | | 72.1 / 0.4 / 27.5 | 71.6 / 0.6 / 27.8 | |
| mean of all 28 pairs | | 88.9 / 0.2 / 10.9 | 87.5 / 0.2 / 12.3 | |

On league points alone, ignoring the games-won tiebreaks, a neighbouring pair is level in 11–18%
of replays under both schemes. Under that view the near-equal pair is 51.4 / 18.4 / 30.2 (A) and
53.0 / 17.2 / 29.8 (B).

### (4) Oddities and diagnostics

**Why B is worse: correlated matches.** I took each match's league points (3/1/0), centred them
per pairing, and correlated two matches of the same player in the same replay.

- **A:** the correlation is **+0.001**.
- **B:** it is **+0.042**.

With 7 matches per player, a correlation of 0.042 inflates the variance of a player's total by
about 1 + 6 × 0.042 ≈ 1.25, close to the observed 1.20.

The cause: mirroring already cancels most of the dice luck *within* a match. Sharing the schedule
*across* matches cancels nothing more in the table, because league points come from results
against different opponents. What it does do is put a player's 7 matches on the same dice, so a
schedule that suits that player's style tends to suit it against every opponent, and the luck
adds up instead of averaging out.

The deterministic noise makes this worse: GNUbg seeds it from the position, so all of a player's
games under one schedule start out nearly identical.

**Schedules have visible common effects in B.** Rounds 1–3 were grouped by (replay, round). In B
each group is one shared schedule; in A the same grouping is a null, with independent dice per
match. The table shows the share of variance (η²) explained by the group, with the chance level
in brackets.

| measure per match-round | A | B |
|---|---|---|
| net points for the stronger player | 0.043 (0.046) | 0.089 (0.046) |
| total points in the round (gammons) | 0.045 (0.046) | 0.105 (0.046) |
| upset (weaker player ahead after the round) | 0.049 (0.046) | 0.077 (0.046) |
| split round (1–1, equal points) | 0.047 (0.046) | 0.070 (0.046) |

So a schedule explains about 4–6 percentage points of variance above chance. No single schedule
dominates, but extremes are wider than independent dice produce. Over 1,000 schedules with
≥ 20 matches each:

| measure per schedule | A | B |
|---|---|---|
| upset rate, range | 0–43% | 0–57% |
| upset rate, SD | 0.075 | 0.099 |
| mean net points for the stronger player | −0.20 to +2.44 | −1.00 to +3.29 |
| mean points per round | 2.85–3.96 | 2.57–4.42 |
| share of split rounds | 0–46% | 0–72% |

The correlation between a player's net points in one round and its league total is 0.43–0.45 for
rounds 1–2 under both schemes, so no single round decides the table more in B.

**Match and game statistics.** These are identical across schemes, as they should be.

| | A | B |
|---|---:|---:|
| games | 65,850 | 65,914 |
| games per match | 4.70 | 4.71 |
| matches drawn | 1.3% | 1.2% |
| matches needing the extra round | 4.9% | 4.8% |
| split rounds (1–1, equal points) | 21.4% | 21.4% |
| turns per game, mean | 64.3 | 64.4 |
| GNUbg decisions per game (non-forced) | 47.6 | 47.8 |
| turn-limit games | 0.02% (20 of 131,764 in A+B; 13 of 52,842 in the long run) | 0.02% |
| gammons or backgammons | **57.9%** | **58.0%** |
| backgammons | 10.3% | 10.1% |

**Gammon rate.** The 58% is far above the expected 20–25%. It is not a rules bug:

- Expert (0-ply, no noise) in self-play gammons in 22% of games (13 of 60), with games of 57
  turns. 1-ply self-play gives 27%.
- Beginner in self-play gammons or backgammons in 75% of games, and n0.100 in 83%.
- GNUbg's noise is added to each of its five outputs, gammon outputs included, so noisy levels
  get into blitzes and backgames.
- This matches the league: in v3.db, games involving gnubg-weak have 17–100% gammons or
  backgammons per pairing, most of them 25–50% (12 pairings, 6–23 games each).

The consequence for this test is that the field is gammon-heavy and matches are short: 4.7 games
on average, often ended by first to 5.

**Near-equal pair.**

- Casual and n0.055 differ by 0.10 ± 0.05 points per game in the long run.
- Casual is above in 62% of single round robins and below in 37%, under both schemes.
- B is no help here either: +0.2 percentage points [−5.6, 6.2].

## Runtime

Wall time is dominated by GNUbg 1.08's 10 ms polling floor per `findbestmove` call (multithread.c,
already noted in `tools/v3/engine.py`). The processes mostly sleep: 24 workers averaged about 1.4
busy cores.

| step | processes | wall | CPU (user + sys) |
|---|---:|---:|---:|
| v1-set PR, 22 candidate configurations | 22 | 51 s | — |
| pilot, 5 replays × 2 schemes | 10 | 72 s | — |
| main run, 500 replays × 2 schemes (131,764 games) | 24 | 46.6 min (2,793 s) | 3,826 s (1.06 h) |
| long-run check, 11,200 matches (52,842 games) | 24 | 18.9 min (1,134 s) | 1,668 s (0.46 h) |
| **total** | | **≈ 67 min** | **≈ 1.5 CPU-hours** |

One replay of the round robin (28 matches, about 132 games) takes 65 s of wall time in one
process and 3.8 s of CPU.

The pilot results looked like backgammon:

- Games averaged 64 turns.
- There was one 300-turn game in 1,290.
- Gammons were high for the reason above, which I checked before the full run.

## Caveats

- **GNUbg players are not LLMs.**
  - GNUbg's deterministic noise is seeded from the position, so the noise is the same for every
    configuration up to scale. The configurations are therefore much more alike than different
    models are, and the near-equal pair often plays identical moves.
  - Sampling LLM players would probably correlate less across matches under B [INFERENCE]. That
    would make B's penalty smaller, but nothing here suggests a mechanism by which B would *help*
    the table.
- **Field size.** The field has 8 players, 7 matches each. A bigger league compounds the B
  correlation over more matches: variance factor ≈ 1 + (k − 1)ρ [INFERENCE].
- **PR reference.** The PR reference is GNUbg 2-ply, which may flatter the 1-ply player a little.
  The long run confirms its place anyway: it beats Advanced 62 / 5 / 33.
- **Not simulated.** Playoffs were not simulated; full-key ties are reported instead. Clocks and
  timeouts were also not simulated, since the GNUbg players have no clock.
- **Who is model1.** A and B use the same fixture per replay, including who is model1. Mirroring
  makes this immaterial.

## Conclusion

Shared roll schedules do not take luck out of a round robin under the v1 match format. They put a
little in. The mirrored round already cancels the dice luck that a common schedule could cancel
within a match. Making every match's round r use the same schedule adds no further cancellation
to league points, which come from results against different opponents. Instead it correlates
each player's matches, about +0.04 per pair of matches. As a result:

- the scatter of league points rises about 10% (variance about 20%) with a tight CI;
- Spearman agreement with the true order drops by 0.026;
- neighbour and near-equal-pair orderings do not move (all within ±2.5 percentage points, CIs
  spanning zero);
- some schedules produce visibly lopsided rounds across the whole league (up to 57% upsets in one
  round).

**Keep scheme A.** Common dice would only reduce noise with duplicate-style scoring, where players
are compared on the same dice against the same opponent and seat [INFERENCE, not tested here].
