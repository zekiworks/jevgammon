# Clear-risk scan: method (pre-registration, 2026-10-29)

Written and committed on 2026-10-29, before any result of the scan exists (no position binned, no gap computed, no
rollout run). It is a mailbox file, not an addition to `tools/site/content/method-spec-2026-10-24.md`: the site's
Method page renders that file from §10 to its end (`tools/site/method.py`, `nack_spec_text`), so appending there
would change the website. The commit of this file is the timestamp.

## Thresholds (Can, 2026-10-29)

- **Clearly safe**: the play leaves 0 hitting rolls.
- **Clearly unsafe**: the play leaves 12 or more hitting rolls.
- **In between**: 1–11 hitting rolls.
- **Clear gap**: 0.04 equity.

## Equity

The league games are played with **no doubling cube**; a win scores 1, 2 or 3 points (single, gammon, backgammon),
in matches of rounds of two games (3 rounds, or first to 5 points after a full round; v3 design, match rules). There
is no match-score equity in the scoring: every engine value on the site is GNUbg 1.08 **cubeless money equity** for
the mover, at 2-ply (`tools/v3/engine.py` `PLY2`: cubeless, 2-ply, deterministic, prune, no noise; written by
`tools/site/score_plays.py` into `STATE/plays/s*.db`). The scan uses that equity everywhere, the Bray validation
included (its 1-1 to 7 score and centred cube are not used), and the rollouts are cubeless money rollouts.

## Data

- League decisions = the three league datasets as published: the shown leagues 1, 2 and 3, their
  `league_match_view` with late-entry matches left out (`matches.stage = 'late-entry'`, as `tools/site/snapshot.py`
  does), turns decided by the model or by fallback (`analysis.load_leagues`), read from `v3.db` read-only
  (`file:…?mode=ro`). Invalid answers (fallback) are counted and left out, as everywhere on the site (Method spec §0).
- Hitting rolls: the site's existing counter (`tools/site/describe.py` `hitting_rolls` = `Board::hitting_rolls`):
  how many of the opponent's 36 rolls hit at least one of the mover's blots after the play; the number stored per
  play in `STATE/plays` (the number shown to the model).
- 2-ply equities: the recorded ones in `STATE/plays`. A decision or play without one is evaluated by the same code
  and settings, GNUbg on CPU only (Method spec §0: `nice -n 19`, at most 8 processes, never the GPUs); the count is
  reported.

## Step 2: sort plays and skip

Each legal play goes into one bin by its hitting rolls: safe (0), in between (1–11), unsafe (≥ 12). A decision is
skipped for the first reason that applies, in this order, and the skips are counted per reason and league:

1. forced move (1 legal play); 2. two legal plays; 3. no contact (GNUbg position class race or bear-off,
`classifypos` < 9; crashed and contact positions stay); 4. safe bin empty; 5. unsafe bin empty.

## Step 3: flag

Best safe = the highest 2-ply equity in the safe bin; best unsafe = the highest in the unsafe bin;
gap = best unsafe − best safe (unrounded).

- **Risk wins**: gap ≥ +0.04. **Safety wins**: gap ≤ −0.04. Otherwise not flagged.

Counts reported per league and in total. Nothing is rolled out for the leagues until Can's go.

## Step 1: Bray validation ("Understanding Risk")

`XGID=-BB-BaB-B---cBa-bb-d-bC---:0:0:-1:00:1:1:0:7:10`, Red (bottom) to play 42, set by hand (the XGID's turn and
dice fields are not used). The imported board is rendered as text and checked against: Red 2 checkers on 1, 2, 4,
6, 8, 13 and 3 on 22; White blots on 5 and 14. Steps 2–3 run on it (all legal plays scored at 2-ply on CPU), then the
step-4 rollout of the best safe and best unsafe play. Expected: Risk wins, with 22/20 22/18 (36 hitting rolls) or a
close unsafe play beating 8/6 8/4 (0 hitting rolls). Otherwise: stop and report.

Rollout settings (Bray now; the leagues only after Can's go): GNUbg 1.08 on CPU, 1,296 games per play, variance
reduction on, quasi-random dice, fixed seed, no truncation, cubeless, checker play at the scorer's 2-ply settings,
each play rolled out as the position after it with the opponent on roll. Keep (step 4) if the rollout gap ≥ 0.04 and
> 3 standard errors of the gap (standard errors of the two plays combined as independent).

## Step-4 estimate

CPU time per 1,296-game rollout of one play, measured on the Bray run on this machine, × 2 × flagged positions.

## Amendment, 2026-10-29T18:10Z: Step 4 replaced (Can, 2026-10-29)

Written, committed and pushed before any step-4 computation (no 3-ply value of any league position exists yet). It
replaces the step-4 rollout rule above for the leagues; the Bray rollout already reported stays as it was.

- **No rollouts.** For every flagged decision, both plays (best safe and best unsafe from step 3) are evaluated with
  GNUbg 1.08 at **3-ply**: cubeless money equity, the position after the play with the opponent on roll, otherwise
  the 2-ply scorer's settings: `{"cubeful": 0, "plies": 3, "deterministic": 1, "prune": 1, "noise": 0.0}` (`PLY2`
  of `tools/v3/engine.py` with `plies` 3), money cube `gnubg.cubeinfo(1, 0, 1, 0)`, via `engine.equity` (a play
  that ends the game keeps its exact 1, 2 or 3 points). GNUbg on CPU only, `nice -n 19`, at most 8 processes. Each
  distinct (position, dice, play) is evaluated once and reused.
- **Keep** a flagged decision only if (a) |gap| ≥ 0.04 at both 2-ply and 3-ply, (b) the two gaps have the same sign
  (Risk wins or Safety wins at both), and (c) |gap3 − gap2| ≤ 0.02. Otherwise it is **unstable** and dropped,
  counted by the first failing condition in the order (b), (a), (c). Unstable positions are rolled out only if Can
  asks later.
- **Rationale:** stability across search depths is used as the signal for positions GNUbg evaluates poorly; it is
  not a substitute for a rollout and is not claimed to be one.
- **Known weak spots:** back games, prime-vs-prime and containment positions. The repo has a simple classifier
  (`tools/v3/classify.py`): kept and unstable positions are reported as counts only for its **back game** rule
  (2+ anchors on the side's points 18–24, either side) and for **prime-vs-prime** defined with its `longest_prime`
  (both sides have a prime of 4+). There is no containment classifier in the repo, so nothing is claimed about
  containment positions.
- **Bray first:** the Bray position is evaluated at 3-ply before the leagues and must be kept as Risk wins;
  otherwise stop and report.
- Steps 5 and 6 (shares per setup, bias, reference rows, hand-check samples) then run on kept positions only.
