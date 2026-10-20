# Anchor checks: results

The v3 league anchor is "GNUbg weak": GNUbg 1.08 Beginner, 0-ply, deterministic noise 0.06,
cubeless.

**Check 1: same play on x86 and ARM? No.** With the anchor's settings, the same GNUbg package
(1.08.003-3build1) with byte-identical weights picks a **different play in 659 of the 1,000 v1
positions** on aarch64 than on x86-64. Without noise, only 6 differ, and in all 6 every play has
the same 2-ply equity.

The cause is not floating point. It is in GNUbg's deterministic `Noise()` (eval.c): the code sums
the 16 MD5 bytes as `char` and then subtracts the *unsigned* mean, 2040. `char` is signed on
x86-64 and unsigned on aarch64. The effect on each architecture:

- **ARM:** the noise is what GNUbg intends, N(0, 1) × 0.06.
- **x86:** every noise draw is shifted by **−6.9 SD**. The win output loses about 0.42 and each
  gammon output about 0.10, and the results are then clamped to [0, 1].

The earlier unverified note was right. The v3 leagues ran only on bariton (x86), and an x86
replay reproduces **all 4,387** recorded anchor decisions. So the anchor that played in v3 is
this "x86 Beginner". On the v1 set it scores PR 21.8; the intended Beginner scores PR 16.8 (on
ARM, about Casual's level). The x86 Beginner also plays for gammons: in self-play it gammons
**72%** of games, against **40%** for the same settings on ARM and 30% for noise-free 0-ply.

**Check 2: gammon rates.** In counted league matches:

| games | gammon or backgammon |
|---|---:|
| involving the anchor, League 1 | 57% |
| involving the anchor, League 2 | 50% |
| model v model, League 1 | 25% |
| model v model, League 2 | 27% |
| Random/Safest, League 1 | 33% |

No game ended by the 300-turn limit or a timeout.

The anchor won 14 of 16 finished matches in League 1 and 8 of 15 in League 2. **Every one of
those 22 wins included at least one gammon or backgammon by the anchor.** Scored at 1 point per
game, only 8 of the 22 (6 in L1, 2 in L2) are certain wins. None is certainly lost. The other 14
would have needed games that were never played, because the match stopped at first-to-5. If
each missing game is a coin flip, the expected wins at 1 point per game are 11.3 (L1) and 6.8
(L2).

Nothing running or paused was touched:

- v3.db and replay.db were opened read-only.
- On bariton, at most 2 gnubg processes ran under `nice -n 19`.
- On spark2 (idle), one Docker container ran with `--cpus 4` under `nice -n 19`.

Scripts are in `experiments/anchor-checks/`.

---

## Check 1: x86 vs ARM

### 1. Where the anchor ran in v3

| item | finding |
|---|---|
| machine | **bariton only**: AMD Ryzen Threadripper PRO 9965WX, x86_64. Leagues run as `league1.service` / `league2.service` (systemd-run on bariton) via `tools/v3/run_league{1,2}.sh` → `./target/release/jevgammon league … --db v3.db`. |
| gnubg binary | `src/players/gnubg.rs` starts `$GNUBG` or else `gnubg` on PATH. The run scripts and `~/.keys` do not set `GNUBG`, so it is `/usr/games/gnubg`. |
| version | `GNU Backgammon 1.08.003 20260122`; Ubuntu package `gnubg 1.08.003-3build1 amd64` and `gnubg-data 1.08.003-3build1`. Installed 2026-10-09 18:56 (dpkg.log), before League 1 started (2026-10-15), and not changed since. |
| build | Ubuntu `debian/rules`: amd64 `--enable-simd=sse2`, every other arch `--enable-simd=no`; also `--with-gtk3 --with-board3d --with-sqlite --with-python=/usr/bin/python3 --enable-threads`, `hardening=+all`. The binary contains "SSE/SSE2 supported." and SSE packed-float code (`mulps`/`addps`, no AVX). Embedded Python 3.14.4. |
| binary sha256 | `7b79dca8…6bb1` (`/usr/games/gnubg`) |
| weights | `/usr/lib/gnubg/gnubg.wd` (`/usr/share/gnubg/gnubg.wd` is a symlink to it): sha256 `bb045bb416c70706ba34ad64595af2b43cac3722560b6ab01829eb719417153b`. One-sided bearoff database `/usr/share/gnubg/gnubg_os0.bd`: sha256 `38089567e87a681682bb4ff53f30d781af215fc04debbdff3f61b6db68547a49`. There is no `gnubg.weights` text file. |
| v3.db provenance | Anchor turns record `provider = 'local'` and `quantization` NULL; there is no device column. `harness_commit` takes 10 values across the anchor's league matches, some marked dirty. The logs (`league1.log`, `league2.log`) give no host. |
| decisive evidence | Replaying all **4,387** anchor decisions in v3.db (`decided_by = 'model'`, all matches with `gnubg-weak`) on bariton with the player's settings gives the recorded `chosen_index` in **4,387 / 4,387** cases. The same replay on ARM matches only 1,359 (31.0%). The anchor has only ever played the x86 build. |

### 2. The ARM install (spark2)

spark2 runs Ubuntu 24.04, which ships only gnubg 1.07, and there is no sudo. I used the Ubuntu
26.04 (resolute) **arm64 build of the same package** in Docker. That is the same source, the same
Debian patches and the same build rules.

```
FROM ubuntu:26.04          # ubuntu@sha256:c098726dd9b9733f3e885f8de0ef375206a311b0a317eadc40d347b1115fb944
RUN apt-get install gnubg=1.08.003-3build1 gnubg-data=1.08.003-3build1 binutils
# image sha256:4907e6c432a087167fd05489afd182e09d082c192db46a41f06182f89188a28b, tag anchor-gnubg:1.08.003-3build1
```

| item | ARM build |
|---|---|
| package | `gnubg 1.08.003-3build1 arm64` |
| binary sha256 | `cbca0d26…4495` (it is a different architecture, so the hash differs) |
| SIMD | none: `--enable-simd=no` per `debian/rules`, and no "SSE … supported"/NEON string in the binary |
| weights | `gnubg.wd` and `gnubg_os0.bd` sha256 **identical** to bariton's |
| Python | 3.14.4 |

The scripts and inputs were identical on both machines: `tools/v3/rules.py`, `tools/v3/engine.py`
and `moves.py` copied over, with matching sha256s.

### 3. Method

- **Positions:** the 1,000 v1 positions from `replay.db`, converted with `rules.from_json` as in
  `experiments/roll-schedule/pr.py`.
- **Move choice:** `engine.best_move` = `gnubg.findbestmove(board, CUBE, ctx, dice)`, the call
  `tools/gnubg_player.py` makes. The context is the player's:
  `{"cubeful": 0, "plies": 0, "deterministic": 1, "prune": 0, "noise": 0.06}`, and again with
  `noise 0`.
- **Seed:** deterministic noise has no seed; it is a function of the board.
- **Raw evaluations:** for every position and every legal result, `gnubg.evaluate` at 0-ply,
  with and without noise. That is 62,634 output values per context per machine.
- **2-ply reference:** replay.db's `equities` table, with every play's 2-ply equity from
  `tools/gnubg_eval.py`.
- **Near-tie:** the best two plays are within 0.02 at 2-ply.

### 4. Results

| context | positions | same play | **different** | PR x86 | PR ARM |
|---|---:|---:|---:|---:|---:|
| Beginner (noise 0.06, deterministic) | 1,000 | 341 | **659** | 21.80 | 16.77 |
| noise 0 | 1,000 | 994 | **6** | 1.30 | 1.30 |

PR = 500 × mean 2-ply loss. The x86 figure, 21.80, equals the Beginner PR in the roll-schedule
note.

**Noise 0.06: 659 positions differ.**

- 308 of them are near-ties.
- The 2-ply gap between the two plays has median 0.053, mean 0.081 and max 0.612. It is ≤ 0.02
  in 185 positions and > 0.1 in 196.
- The x86 play is better in 331 positions, the ARM play in 321, and 7 are equal. On these 659
  positions the mean loss is 0.0639 on x86 and 0.0486 on ARM.

So neither build is simply better position by position, but the ARM one is clearly better on
average.

**Noise 0: 6 positions differ.**

- All 6 are no-decision bearoffs (ids 147, 235, 548, 586, 596, 972). Every play there has the
  same 2-ply equity: −1.000, or −0.992 for id 586.
- All 6 count as near-ties.
- The gap is 0.000 to three decimals.

**Floating point (noise 0):**

- Only 14.9% of the 62,634 output values are bit-identical.
- Most differ by ≤ 1e-5. The breakdown of |x86 − ARM|: 9,353 exactly equal, 13,117 ≤ 1e-6,
  19,123 ≤ 1e-5, 19,959 ≤ 1e-4, 1,067 ≤ 1e-3, 15 ≤ 0.01. The maximum is 0.0026.
- This is the SSE2 and scalar network code computing different roundings [INFERENCE about which
  part of the code; the size is measured].
- It flips move choice only between exactly equal plays.

### 5. Why the noise differs

GNUbg 1.08, `eval.c` `Noise()`, deterministic branch:

```c
char auchBoard[50], auch[16];          /* plain char */
... md5_buffer(auchBoard, 50, auch);
r = 0.0f; for (i = 0; i < 16; i++) r += auch[i];
r -= 2040.0f;  r /= 295.6f;            /* 2040 = 16 x 127.5, 295.6 = SD of 16 uniform 0..255 */
r *= pec->rNoise;  /* x 0.25 for gammon outputs, x 0.01 for backgammon outputs */
```

After this, `arOutput[i] += Noise(...)`, then a clamp to [0, 1], then `SanityCheck`. That covers
gammons ≤ wins, lose-gammons ≤ 1 − win, and tiny contact gammons set to 0.

The constants assume unsigned bytes. On x86-64, `char` is signed, so each hash byte ≥ 128 counts
256 less. That gives r_x86 = r_ARM − 0.866·k, where k ~ Bin(16, ½) is the number of such bytes
(mean 8).

I re-implemented `Noise()` in Python (`compare.py`) and checked it against the observed
noisy-minus-clean outputs. Units are noise × scale: 0.06 for wins, 0.015 for gammons, 0.0006 for
backgammons.

| machine | predicted mean | predicted SD | checked outputs (not clamped) | match the re-implementation | observed mean | observed SD |
|---|---:|---:|---:|---:|---:|---:|
| x86 (signed `char`) | **−6.925** | 0.998 | 28,004 | 25,259 (90.2%) | −6.862 | 0.986 |
| ARM (unsigned `char`) | **+0.003** | 0.998 | 41,912 | 41,473 (99.0%) | +0.043 | 0.982 |

The remaining mismatches are outputs that `SanityCheck` rewrote after the noise. On x86 they are
more common, because the win output drops below the gammon output [INFERENCE from the
SanityCheck code; not counted rule by rule].

Consequences for play (the second half of this list is [INFERENCE] from the code above):

- **What the shift does:** `findbestmove` scores each play by the opponent's evaluation after it.
  On x86 that evaluation has P(win) lowered by about 0.42 and the gammon outputs lowered by about
  0.10, each clamped at 0.
- **When the mover is ahead:** while the opponent's true winning chance is below about 42%, its
  clamped P(win) is 0 for every candidate play. Gammon chances above about 0.10 are then the only
  thing that separates the plays. Below that threshold they are clamped too, so only noise is
  left.
- **Result:** the x86 Beginner goes for gammons whenever it is ahead and largely ignores how
  risky that is. This fits the self-play result and the league numbers below.

**Self-play.** I used 300 games per setup with `experiments/roll-schedule/common.py` (the
runner's game flow and dice). Game i uses seed `derive_seed(20261020, "anchor selfplay i")` on
both machines.

| setup | machine | single | gammon | backgammon | gammon + bg (±1 SE) | mean turns | same winner, result and length as the other machine |
|---|---|---:|---:|---:|---:|---:|---:|
| Beginner (0-ply, det. noise 0.06) | x86 | 85 | 167 | 48 | **71.7% ± 2.6** | 72.6 | 3 / 300 |
| Beginner (0-ply, det. noise 0.06) | ARM | 179 | 107 | 14 | **40.3% ± 2.8** | 67.5 | |
| Expert (0-ply, noise 0) | x86 | 210 | 88 | 2 | 30.0% ± 2.6 | 55.3 | 293 / 300 |
| Expert (0-ply, noise 0) | ARM | 208 | 90 | 2 | 30.7% ± 2.7 | 55.2 | |

The roll-schedule note's "Beginner gammons ~75%" is this x86 effect. The intended noise (ARM)
still raises gammons above noise-free play, from 30% to 40%, but by far less.

### What this means

- **Reproducibility:** the v3 anchor is reproducible bit for bit on x86-64 with this package.
  4,387 of 4,387 decisions replay identically. It is *not* reproducible on aarch64, and probably
  not on any build where `char` is unsigned [INFERENCE: e.g. `-funsigned-char`, or other ARM or
  PowerPC Linux builds]. There, 69% of its decisions change.
- **Strength:** the anchor is not GNUbg's "Beginner" as GNUbg defines it. It is a Beginner with a
  −6.9 SD bias plus clamping: PR 21.8 against 16.8 on the v1 set, and much more gammon-prone.
  Anyone re-running the anchor elsewhere, or comparing it with published "GNUbg Beginner"
  numbers, will get a different player.
- **Possible fixes (not applied):**
  - Pin the anchor to x86-64.
  - Or describe it as "GNUbg 1.08 Beginner, x86-64 build", and record the arch in the result
    (e.g. as the turn's `provider`/`quantization`).
  - A corrected player that is the same everywhere would need gnubg patched to `unsigned char`,
    or to subtract the signed mean. That would change the anchor that v3 has measured so far.

---

## Check 2: gammon rates in v3 leagues

**Method.**

- **Matches counted:** matches linked from `league_matches.match_id` (stage `league`; voided and
  removed matches are not linked), as `tools/v3/page_v3.py` counts them.
- **Games counted:** all games with a winner in those matches. That includes the finished games
  of the 20 linked matches whose latest attempt is `aborted` (paused leagues); 16 fixtures have
  no match yet.
- **Column semantics:**
  - `games.result` is `single | gammon | backgammon | timeout | turn_limit`.
  - `games.points` is the winner's points (1/2/3).
  - `games.winner_player` is the player number (1 = `matches.model1`).
  - Checked: summing points by `winner_player` reproduces `score1`/`score2` for all 344
    finished matches.
- **Turn limit and timeouts:** neither occurs in v3.db (0 games).

### Game endings (finished games, counted league matches)

| league | games involving | games | single | gammon | backgammon | gammon + bg |
|---|---|---:|---:|---:|---:|---:|
| L1 | the anchor (GNUbg weak) | 70 | 30 (42.9%) | 30 (42.9%) | 10 (14.3%) | **57.1%** |
| L1 | Random or Safest (no anchor) | 142 | 95 (66.9%) | 29 (20.4%) | 18 (12.7%) | 33.1% |
| L1 | two models | 525 | 393 (74.9%) | 109 (20.8%) | 23 (4.4%) | **25.1%** |
| L1 | all | 737 | 518 (70.3%) | 168 (22.8%) | 51 (6.9%) | 29.7% |
| L2 | the anchor | 68 | 34 (50.0%) | 28 (41.2%) | 6 (8.8%) | **50.0%** |
| L2 | Random or Safest | 0 | – | – | – | – (not in League 2) |
| L2 | two models | 571 | 418 (73.2%) | 131 (22.9%) | 22 (3.9%) | **26.8%** |
| L2 | all | 639 | 452 (70.7%) | 159 (24.9%) | 28 (4.4%) | 29.3% |

Turn-limit or timeout games: 0 in every row. Anchor v Random/Safest games count under "the
anchor".

Anchor games by winner:

| league | anchor won: single / gammon / bg | anchor lost: single / gammon / bg |
|---|---|---|
| L1 | 17 / 21 / 10 | 13 / 9 / 0 |
| L2 | 16 / 14 / 5 | 18 / 14 / 1 |

In L1, 31 of the anchor's 48 game wins are gammons or backgammons (65%). In L2 it is 19 of 35
(54%).

### The anchor's matches

**Rescoring approach.**

- **Stopping rule:** I replayed the runner's rule (`src/runner.rs` `play_match`/`rounds_after`)
  on the recorded games, in round and leg order, with every game worth 1 point. A match is
  rounds of two games, 3 planned rounds, or over after the round in which someone reaches 5 and
  is ahead. A level score adds exactly one extra round, and a level score after that is a draw.
- **Sanity check:** the same replay with the recorded points reproduces all 253 finished league
  matches' scores.
- **When recorded games run out:** at 1 point per game, nobody reaches 5 as early, so the rule
  often asks for round 3, or an extra round, that was never played. In that case I enumerate
  every outcome of the missing games, at 1 point each, under two assumptions:
  - each missing game is won by the anchor with p = 0.5;
  - or with p = the anchor's game-win share in that league (L1 0.686, L2 0.515).
- **Labels:** "certain" means the anchor wins (or doesn't) whatever happens in the missing games.

| league | finished | won | drawn | lost | wins with ≥1 anchor gammon/bg | wins certain at 1 pt/game | wins certainly not won | wins open | expected wins, p = 0.5 | expected wins, p = share | expected wins over all its matches, p = 0.5 / share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L1 | 16 | **14** | 0 | 2 | **14** | **6** | 0 | 8 | 11.31 | 12.62 | 11.38 / 12.84 |
| L2 | 15 | **8** | 0 | 7 | **8** | **2** | 0 | 6 | 6.81 | 6.91 | 7.12 / 7.24 |

Per won match:

| league | match | opponent | recorded score (anchor first) | games | anchor gammons/bg | 1-pt score after recorded games, rounds | more games needed | P(anchor wins), p = 0.5 | P(anchor wins), p = share | P(draw / loss), p = 0.5 |
|---|---:|---|---|---:|---:|---|---|---:|---:|---|
| L1 | 72 | Open-Jev 27B v1.1 | 7–0 | 4 | 3 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L1 | 74 | Safest | 7–3 | 6 | 2 | 4–2, 3 | no | 1.000 | 1.000 | 0 / 0 |
| L1 | 75 | Cygnet (Gemma 4 12B) | 7–0 | 4 | 2 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L1 | 76 | Decider v1.1 27B | 5–1 | 4 | 1 | 3–1, 2 | yes | 0.812 | 0.948 | 0.125 / 0.062 |
| L1 | 78 | Clef | 5–2 | 6 | 1 | 4–2, 3 | no | 1.000 | 1.000 | 0 / 0 |
| L1 | 79 | SubQ Snap Preview | 5–1 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.948 | 0.125 / 0.062 |
| L1 | 83 | Random | 5–0 | 2 | 2 | 2–0, 1 | yes | 0.750 | 0.945 | 0.125 / 0.125 |
| L1 | 192 | Liquid d1-ultra | 6–5 | 6 | 3 | 3–3, 3 | yes | 0.250 | 0.470 | 0.500 / 0.250 |
| L1 | 236 | Decider Flash v1.2 | 9–0 | 4 | 3 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L1 | 239 | Winnow-12B | 5–4 | 6 | 2 | 3–3, 3 | yes | 0.250 | 0.470 | 0.500 / 0.250 |
| L1 | 263 | Jev 1.14.0 | 7–2 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.948 | 0.125 / 0.062 |
| L1 | 273 | GPT-6 Luna | 5–1 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.948 | 0.125 / 0.062 |
| L1 | 364 | Mercury Decide | 8–0 | 4 | 3 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L1 | 374 | Fastino GLiDE | 5–1 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.948 | 0.125 / 0.062 |
| L2 | 100 | DeepSeek V4.1 Flash (off) | 5–1 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.827 | 0.125 / 0.062 |
| L2 | 101 | GPT-6.1 Sol (high) | 5–1 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.827 | 0.125 / 0.062 |
| L2 | 107 | GLM-5.3 (on) | 5–2 | 4 | 1 | 3–1, 2 | yes | 0.812 | 0.827 | 0.125 / 0.062 |
| L2 | 121 | Gemini 3.8 Flash (high) | 5–0 | 4 | 1 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L2 | 227 | Gemma 4 31B (off) | 5–2 | 4 | 2 | 3–1, 2 | yes | 0.812 | 0.827 | 0.125 / 0.062 |
| L2 | 323 | LFM2.5-24B-A2B (on) | 7–2 | 4 | 3 | 3–1, 2 | yes | 0.812 | 0.827 | 0.125 / 0.062 |
| L2 | 327 | Qwen3.8-27B (off) | 7–0 | 4 | 2 | 4–0, 2 | yes | 1.000 | 1.000 | 0 / 0 |
| L2 | 338 | LFM2.5-24B-A2B (off) | 5–0 | 2 | 2 | 2–0, 1 | yes | 0.750 | 0.772 | 0.125 / 0.125 |

How the matches shorten:

- 18 of the 22 wins ended at first-to-5 after 1–2 rounds, only because of gammons.
- At 1 point per game, the six 4–0 wins after round 2 stay certain wins: round 3 can only bring
  the score to 4–2.
- 3–1 after two rounds becomes a loss or draw if the opponent wins both round-3 games and then
  the extra round.
- Two L1 wins (Liquid d1-ultra 6–5, Winnow-12B 5–4) are 3–3 after three rounds at 1 point. They
  would go to an extra round that can end in a draw.

### For comparison: every finished league match at 1 pt/game (missing games at p = 0.5)

| league | category | finished | needs more games | result certainly same | certainly different | open | expected share with the same result |
|---|---|---:|---:|---:|---:|---:|---:|
| L1 | anchor | 16 | 14 | 7 | 0 | 9 | 82.0% |
| L1 | Random/Safest | 29 | 20 | 18 | 0 | 11 | 84.3% |
| L1 | model v model | 92 | 41 | 58 | 2 | 32 | 82.7% |
| L2 | anchor | 15 | 11 | 7 | 0 | 8 | 85.8% |
| L2 | model v model | 101 | 45 | 69 | 1 | 31 | 86.9% |

The anchor's matches are about as sensitive to 1-point scoring as everyone else's (82–86%
expected to keep their result). The difference is that every one of its wins involved gammons,
and most were decided early by them.

---

## Runtime

| step | where | wall | CPU |
|---|---|---:|---:|
| export positions (`export.py`) | bariton | 1 s | — |
| moves + raw evaluations, 1,000 v1 positions × 2 contexts + 4,387 v3 decisions | bariton, 1 process | 4 min 36 s | 8.8 s |
| same | spark2, Docker, `--cpus 4` | 4 min 56 s | — |
| ARM image build (apt install) | spark2 | 43 s | — |
| self-play, 2 × 300 games | bariton, 1 process | 4 min 56 s | 20.2 s |
| same | spark2 | 5 min 9 s | — |
| `compare.py`, `gammons.py` | bariton | < 2 s each | — |

As before, the wall time is mostly gnubg's 10 ms task-polling floor; the processes sleep.

## Blockers and caveats

- **No 1.08 for Ubuntu 24.04 on spark2, and no sudo.** I used the identical Ubuntu package
  (1.08.003-3build1, resolute arm64) in Docker instead of building from source. It is the same
  source and patches, and the same rules as the amd64 build apart from the SIMD flag. The source
  (`gnubg_1.08.003.orig.tar.gz` sha256 `6f7d969b…5979`, `debian.tar.xz` `389dd846…ba1a`) was
  downloaded to inspect `eval.c` and `debian/rules`.
- **SIMD vs scalar.** These differ (SSE2 on x86, none on arm64). That accounts for the tiny
  noise-free differences, not for the 659. The 659 come from `char` signedness, which the
  re-implemented `Noise()` predicts output by output.
- **The v3 replay uses today's `tools/v3/rules.py`/`engine.py`.** The runner embeds them at build
  time. The 100% reproduction shows they are equivalent for this purpose.
- **"Wins certainly not won" is 0, but "open" wins are open.** Under 1-point scoring the missing
  games would have been played with different dice, positions and noise, so the p = 0.5 and
  p = share figures are illustrations, not predictions.

## Files

`experiments/anchor-checks/`:

- `export.py`: v1 positions with 2-ply equities, and the anchor's v3 decisions, to
  `data/positions.json` (read-only DBs).
- `moves.py`: runs inside gnubg on either machine; move choice and raw evaluations.
- `selfplay.py`: self-play gammon rates; reuses `experiments/roll-schedule/common.py`.
- `compare.py`: the Check 1 tables, including the `Noise()` re-implementation.
- `gammons.py`: the Check 2 tables.

The `data/` folder is git-ignored. The ARM image `anchor-gnubg:1.08.003-3build1` and
`~/anchor-check/` remain on spark2.
