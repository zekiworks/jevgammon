# Method specification: reviewed brief of 24 Oct 2026, items 3–6

Fixed on **2026-10-24, 12:55 UTC**, committed on branch `brief-2026-10-24` before any number below was computed.
Not changed after seeing results; a bug found later is fixed in a dated amendment at the end of this file.
The machine-readable values are in `analysis_2026-10-24.json` next to this file. This file is not a deploy
approval.

## 0. Data and shared rules

- Source: the site snapshot (`STATE/snap.db`, `STATE/plays/s*.db`) copied at 2026-10-24 12:51 UTC, all three
  leagues Finished. Decisions are the site's league decisions (`analysis.load_leagues`): `decided_by` model or
  fallback, in the league's current match view. Invalid answers (fallback) are left out, as everywhere on the site.
- Every legal play already has a GNUbg 1.08 2-ply value in `STATE/plays`. A selected play without one would be
  evaluated with `tools/site/score.sh` (GNUbg on CPU, 2-ply, `nice -n 19`, at most 8 processes); the count of such
  plays is reported (expected 0).
- Risk classes, risk calls, stakes, the two margins (0.001 main, 0.02 robustness), risk judgement
  (`50 × (right risks / Risk pays + right safety / Safety pays)`), error rate (PR = 500 × mean 2-ply equity loss)
  and the 200-decision minimum (`min_decisions_per_cell`) are the existing ones (`analysis.play_call`,
  `analysis.risk_metrics`, `thresholds.json`). Nothing here changes them.
- **Block map.** One global map per league: a block is a (match, round): the two games of a round, the second with
  seats swapped and the same dice. Checked on the data before any result: in every valid league (match, round) the two
  games have the same roll sequence turn by turn (unordered dice per turn), and no valid league match shares a dice
  seed with another match (shared seeds occur only between a voided match and its replay, and voided matches are not in
  any league view). All splits, folds and bootstrap resamples of items 4–5 use these blocks, for every setup alike.
- Seeds: `bootstrap_seed` (20261021) plus the stable text hash of `analysis.boot` of a label naming the analysis,
  league, setup and margin.

## 1. Probability support audit (items 3–5)

A record is **eligible for probability analyses** only when its option probabilities are verifiably complete. The
audit reads the raw exchanges in `v3.db` read-only (`mode=ro`); it writes `content/probability_audit.json.gz`
(turn id → status). Status, in this order of precedence:

1. `invalid`: fallback answer.
2. `no_probabilities`: program, `choice_only` (one constrained letter at probability 1) or no probability source.
3. `grouped`: the plays were split into groups (`group_size` set): no single probability over all legal plays.
4. `no_raw`: no exchange with a response.
5. `unverified`: no response of the turn reproduces the stored probability vector (|difference| ≤ 1e-9 per option).
6. `sparse`: the reproducing response does not give an explicit probability for every legal option.
   - decision services: every shown candidate notation must appear in the response's `probabilities` with a
     finite value ≥ 0;
   - letter log-probabilities: every one of the option letters A.. must appear (any surface form the runner
     accepts: `C`, ` C`, `C.`) among the top log-probabilities of the answer token that reproduces the stored
     vector. A letter missing there was zero-filled by the runner and renormalised: such a record is `sparse`,
     whatever the vector's length or sum.
7. `complete`: none of the above.

Only `complete` records enter items 5A, 5B (both events) and 5D. Every other status is counted and shown per setup.
The existing Confidence tab and "Confidence on the call" keep their existing eligibility (probability present, not
grouped); item 3 only changes the wording and footnote.

## 2. Item 4: ability and caution (both margins, every setup with decisions, the computed reference rows too)

Counts per setup and margin (weights for the computed Random row): R = Risk pays decisions, S = Safety pays
decisions, T = risks taken in Risk pays (right + wrong risks), N = needless risks, n_M = missed risks.

- Hit rate H = (T + 0.5) / (R + 1); false-alarm rate F = (N + 0.5) / (S + 1) (log-linear correction).
- Ability d′ = z(H) − z(F). Caution c = −(z(H) + z(F)) / 2; positive = cautious, negative = bold.
- **Missing class:** R = 0 or S = 0 → d′, c, c* all "N/A: no <class> decisions". The correction is never used to
  produce a value for an absent class.
- Aim = right risks / (right + wrong risks); denominator 0 → "N/A" with the count 0 / 0.
- 95% interval of d′ and c: block bootstrap, 2,000 resamples (resample blocks with replacement, recompute the
  counts and the corrected rates).
- **Cost-derived SDT reference** c* = ln(β) / d′, β = (S / R) × (L_N / L_M); L_N = mean equity lost (2-ply loss of
  the chosen play against the engine's best) per needless risk, L_M = the same per missed risk, from the setup's own
  decisions at that margin. Rules, in order:
  1. a class absent → N/A (above);
  2. N = 0 or n_M = 0 → "N/A: no needless (missed) risks to price";
  3. L_N ≤ 0, L_M ≤ 0, or β not a finite number above 0 → "N/A: nonpositive cost";
  4. d′ ≤ 0 → "N/A: no ability (d′ ≤ 0)";
  5. **near-zero d′**: the lower end of the d′ 95% interval ≤ 0 → value shown, labelled "unstable: d′ near zero";
  6. N < 200 or n_M < 200 (the site's minimum for an average) → value shown, labelled "unstable: fewer than 200
     needless (missed) risks behind a mean cost";
  7. otherwise valid.
  A reference mark is drawn on the chart **only** in case 7.
- c* is a reference under an equal-variance signal-detection utility model with the setup's observed conditional
  costs; those costs depend on the setup's own policy. It is not called best caution or an optimum.
- Leagues 2 and 3, by reasoning setting: for each model with both settings in the same league (setups.json `model`
  and `setting`), lower and higher setting side by side with d′, c and the higher − lower change, median seconds per
  decision and mean output tokens per decision; labelled UNPAIRED (different positions). No Kimi K3.1 Pro (on) row.

## 3. Item 5A: re-read risk call (main margin 0.001)

- Records: `complete` (section 1). Setup shown when it has ≥ 200 complete records, else "Too few decisions" with
  the counts.
- P(risk) = Σ p over legal plays leaving more hitting rolls than the minimum / Σ p over all legal plays.
- Re-read on a trade-off decision: if P(risk) ≥ t, the risky play with the highest p, else the safe (minimum hitting
  rolls) play with the highest p; equal p → the play shown earlier. No-trade-off decisions keep the played move.
- Candidates for t: 0.00, 0.05, …, 1.00 (t = 0 is "always risky") and "always safe" (t = ∞). Objective: the risk
  judgement on the training half's complete trade-off records (re-read calls). Ties (within 1e-9): the candidate
  nearest 0.5, then the smaller t; ∞ is farthest from 0.5. A training half without Risk pays or without Safety pays:
  the split has no fit for that setup and is counted.
- Splits: 300 per league; each takes ⌊B/2⌋ of the league's B blocks at random for training, the rest for test; the
  same split is used for every setup in the league. No Platt step is inside this selection.
- Test comparison on exactly the same complete test records: risk judgement as played and re-read (trade-off
  records; a test half lacking a class gives N/A for that split, counted, left out of the mean), and PR as played and
  re-read over all complete test records (non-trade-off keep the played move). Reported: means over splits of each and
  of the differences (re-read − as played); split-to-split 5th–95th percentile of the differences, called
  "stability", not an interval; how often each endpoint was chosen.
- Uncertainty: block bootstrap of the whole procedure: 200 replicates; each resamples the league's blocks with
  replacement and runs 30 splits in which every resampled block (with its copies) falls in one half; the 95%
  interval is the 2.5–97.5 percentiles of the replicate means of the differences. No independent-split standard
  error is computed.
- Label everywhere: "re-read from the model's probabilities, not played". Counterfactual scoring of recorded
  positions, not a league result.
- **Hypothesis (recorded before computing):** gains will be largest for setups with high ability whose caution is
  well above the cost-derived SDT reference. This is a hypothesis, not a claim that c* is optimal. Test: per split,
  from the setup's training-half decisions (all its valid scored decisions in the training blocks, main margin),
  X = d′ × (c − c*); X is undefined in a split when c* falls under rules 1–4 or d′ < 0.2 (the split-level
  near-zero rule; the bootstrap rule 5 is not run per split). A setup's X = mean over its defined splits; a setup with
  fewer than 150 defined splits is left out of the test (counted). Y = mean over splits of the test-half
  judgement difference. Statistic: Spearman ρ(X, Y) across setups, all leagues pooled (and per league as
  description). Supported only if ρ > 0 and its 95% bootstrap interval (same replicates, X and Y recomputed) is above
  0; ρ > 0 with an interval reaching 0 is "inconclusive"; otherwise "not supported".

## 4. Item 5B: calibration as shipped and after a Platt refit

- Event 1, chosen play: p = the probability of the chosen play (as stored), y = 1 when the chosen play lost less than
  0.001 (the site's "engine's best play" event). All complete records.
- Event 2, risk class: P(risk) (section 3), y = 1[Risk pays at 0.001]; complete trade-off records. Labelled
  separately; never mixed with event 1.
- Platt: logistic regression of y on logit(p), p clipped to [1e-6, 1 − 1e-6]; Newton–Raphson, at most 50 steps,
  converged when the step is below 1e-10. Cross-fitted: the league's blocks in 5 folds (seeded shuffle); each fold is
  predicted by a fit on the other 4. A fold whose training part has one class only or does not converge: its records
  are left out of both before and after (paired), counted.
- Reliability: 10 fixed bins [0, 0.1), …, [0.8, 0.9), [0.9, 1.0]; per bin n, mean p, observed share. Brier score
  before and after on the same records. Setup shown when ≥ 200 paired records.
- The refit is not used in item 5A's or 5C's selection.

## 5. Item 5C: minimum bar, then cheapest

- Bar (fixed): risk judgement ≥ 60 (main margin) and error rate ≤ 35 PR (500 × mean equity loss; not a mistake rate).
- Candidates: the model setups of the league (programs left out), as played, all valid scored decisions.
- Per split (the 300 splits of section 3): on the training half, a setup qualifies when both bars hold (judgement
  N/A → not qualifying). Price: $ per 1,000 decisions on its training decisions, only when every one of them has a
  recorded cost (the site's coverage rule); otherwise unpriced, never "cheapest". Chosen: the qualifying priced setup
  with the lowest price; ties → lower training PR, then name. The chosen setup is then scored on the test half:
  bar cleared or not.
- Reported per league: per setup the training qualification share, how often chosen, and the held-out clearance share
  when chosen; splits with no qualifying setup; splits with qualifying setups but none priced; price coverage per
  setup. The bar is never loosened and test outcomes never select.

## 6. Item 5D: confidence distributions

- Population: complete records (section 1). Probability: the chosen play's probability (never P(risk)).
- Chart 1: right (lost < 0.001) vs wrong decisions. Chart 2: right risks vs wrong + needless risks (main margin,
  risks taken on trade-off records). Same 10 fixed bins as 5B, shares with counts. A group with fewer than 200
  records shows its counts and "Too few decisions".

## 7. Item 6: Safest

- Read the program's code (`src/players/baseline.rs`) and its League 1 records; report the share of its decisions on a
  minimum-hitting-roll play and on the engine's best safe play, and the right-safety PR contribution with its
  denominator and the conditional mean over right-safety decisions, side by side.
