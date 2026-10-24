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

## 9. Close choices (section added 2026-10-24, 15:15 UTC, before any close-choice number was computed)

Request: `mailbox/Close choices - request 2026-10-24.md` (stage A now, stage B only prepared). Values in
`close_choices_2026-10-24.json`. Code: `tools/site/close_choices.py`. Not changed after seeing results; a bug found later
is fixed in a dated amendment at the end of this file. Inspired by "Can LLMs Anticipate Their Cruxes?"
(arXiv 2610.21006). Nothing here concludes anything about a model's inner reasoning or the cause of its decision.

### 9.1 Term (A3)

One term on the site: **close choice**. Definition, written once: "A decision is a close choice when the second most
likely play has at least half the probability of the first (internally: split)." Every result carries the label
"Probabilities over plays, not sampled reasoning."

### 9.2 Data (A1)

- The same fixed snapshot as §0 and the ability and caution analyses: `snap.db` copied 2026-10-24 12:51 UTC
  (sha256 `0e11c179…b011d9`), GNUbg scores `plays/s0..s31.db` (sha256 of the 32 files concatenated in that order
  `161ab5e0…f14e1f`), probability audit `content/probability_audit.json.gz` (sha256 `4ad35193…628789`).
  Full hashes in the JSON file.
- Decisions: the site's league decisions (`analysis.load_leagues`), the three leagues kept separate. No league,
  result or record is changed; no model is called; `v3.db` is not opened for this section (the audit already read it,
  read-only).

### 9.3 Eligibility (A2)

- Eligible: audit status `complete` (§1: the record itself gives an explicit probability for every legal option,
  decided by the record's content, not by model type) **and** an engine value for every legal play.
- Excluded, counted per setup by reason: `invalid` (invalid answer, fallback), `grouped` (asked in groups of
  options), `sparse` (incomplete distribution: an option without an explicit probability), `unverified`, `no_raw`,
  `not_audited` (no audit status), `not_scored` (complete but no engine value; see 9.5), `no_probabilities`
  (one letter only, or a program).
- A setup with no eligible decision shows **N/A** ("no full probability distribution"). Missing probabilities are
  never filled by new calls.
- Shares are always shown with count and denominator. A denominator under 200 (the site's minimum,
  `min_decisions_per_cell`) is shown with the note "fewer than 200 decisions"; it is not hidden.

### 9.4 Close-choice rule and ties (A3)

- The probabilities are the stored vector over legal plays (`pvec`), each divided by their sum (the stored vectors
  already sum to 1 up to rounding; the rule does not depend on it).
- Plays are ordered by probability, highest first; equal probabilities (exact equality, no tolerance) are ordered by
  the recorded option order (the shuffled order shown to the model), earlier first; never by engine values.
- Candidate 1 and candidate 2 are the first two; p1 and p2 their probabilities. **Close choice ⇔ p2 ≥ 0.5 × p1.**
  Stored for every eligible decision: p1, p2, p1 + p2, both candidate plays.
- **Ties that affect the top two**: p1 = p2 (the order of the two candidates comes from the option order) or p2 equals
  the probability of the third play (which play is candidate 2 comes from the option order). Counted per setup and
  reported in two parts: at a positive probability (p2 > 0) and at zero (p2 = 0: every play but one has probability 0;
  such a decision is never a close choice). A tie never changes whether a decision is a close choice; it changes which
  plays are compared.

### 9.5 Features and engine values (A4)

- From the option text the model was shown (`describe.py`, stored with every legal play in `plays.data`), for
  candidate 1 against candidate 2:
  - **hitting**: the opponent's hitting rolls ("the opponent hits with N of 36 rolls");
  - **points**: the set of newly made points ("makes the … point(s)" / "makes no new point");
  - **race**: both players' pip counts (differs when either player's count differs);
  - **prime**: the longest prime length.
- Every feature that differs is recorded (a set of 0–4 features). When several differ, none is picked as the cause.
- Engine values: both candidates' GNUbg 1.08 2-ply values (cubeless money equity for the mover, the site's existing
  settings), the gap |e1 − e2|, and each candidate's loss against the engine's best play (best − e). Two candidates
  can be close to each other and both lose a lot.
- The same features and values are recorded for the top two plays of decisions that are not close choices, for
  comparison.
- Summaries per setup, close choices and the other eligible decisions separately: the share of decisions where each
  feature differs, the count by number of differing features (0–4), mean and median of the gap, of candidate 1's loss
  and of candidate 2's loss.
- Missing engine values: any eligible-by-probability decision without them would be scored with
  `tools/site/score.sh` (GNUbg on CPU, 2-ply, `nice -n 19`, at most 8 processes, the existing settings) into the
  site's scores store (`STATE/plays`), never on the leagues' GPUs. The count is reported (expected 0, as in §0).

### 9.6 Risk close choices and stake bands (A5)

- Minimum hitting risk = the smallest number of hitting rolls among all legal plays (the numbers the model was
  shown). The two candidates form a **risk pair** when one of them leaves the minimum and the other leaves more.
- **Risk close choice** = a close choice whose candidates form a risk pair (does not depend on the margin).
  Per setup: risk close choices ÷ close choices (count and denominator; this is the site's share), and ÷ eligible
  decisions.
- At each margin (0.001 main, 0.02 robustness; the close-choice rule is the same at both): the position class of each
  decision (`analysis.play_call`: Risk pays, Safety pays, No trade-off) and, per class, close choices and risk close
  choices with their denominators (eligible decisions of that class).
- **Stake bands**, at each margin, Risk pays positions only, as on the site: stake = the best safe play's loss
  against the engine's best play; small < 0.02 ≤ medium ≤ 0.08 < big (`thresholds.json`). Per band: close choices ÷
  all eligible decisions in that band.
- Wording: a big stake means playing safe is more expensive by the engine's value. It is not decision difficulty, and
  nothing assumes that good setups have more (or fewer) close choices there. A share of close choices is never called
  good or bad, and setups are never sorted or ranked by it.

### 9.7 Missed risks (A6), at each margin

- Group G: eligible decisions in Risk pays positions whose two candidates form a risk pair (9.6). Within G, close
  choices (C) are compared with the other decisions (O).
- Outcome: the risk class of the play actually made: **missed risk** (`play_call` call `missed`: a minimum-hitting
  play in a Risk pays position).
- Crude rates: missed ÷ n in C and in O; difference = rate(C) − rate(O).
- **Adjusted** (shown on the site): strata = phase (5) × number of options (`option_buckets`, 5) × the engine gap
  between its two best plays (`gap_buckets`: under 0.02, 0.02 to 0.08, over 0.08). Only strata holding both C and O
  decisions count. Adjusted rate(C) = missed C ÷ C in those strata; adjusted rate(O) = O's stratum rates weighted by
  C's counts in the same strata (O standardised to C's mix); difference = adjusted rate(C) − adjusted rate(O).
  Coverage reported: C decisions in counted strata ÷ all C.
- 95% interval of both differences: bootstrap by match, 2,000 resamples of the setup's matches with replacement (all
  decisions of a match move together), percentiles 2.5 and 97.5; a resample where the difference is undefined is
  left out and counted. Seed: `analysis.boot` of a label naming league, setup, margin and estimate.
- **N/A** when C or O is empty (crude), or when no stratum holds both (adjusted).
- Wording: an association within recorded decisions, not a cause.

### 9.8 Site (no change to the Risk tab)

Confidence tab column "Close choices" (share, count, denominator; N/A as in 9.3; not sortable), details per setup
(9.6 risk share, 9.5 engine values, 9.7 missed risks; margin shown as on the Risk tab), chart panel "close choices by
stake band (Risk pays only)" with Download PNG; model page with the full breakdown; Every decision "Close choice"
filter with p1, p2 and both candidate plays. The label of 9.1 under the column, the details and the chart.

### 9.9 Stage B scoring (B4), fixed now, before any stage B call

- Positions: 100, frozen from the prepared shared standard pool (`freeze/close-choices-b.json`). Teams: the one-letter
  Cup teams (plan in `mailbox/Close choices - stage B plan and estimate.md`).
- Observed feature set O (per setup and position): the features of 9.5 (same fixed mapping: hitting risk = the
  opponent's hitting rolls; making a point = the set of newly made points; race = both players' pip counts; prime =
  the longest prime length) that differ between any two of the plays selected across the five repeat calls.
- Predicted set P: the features named in the separate prediction call. A valid answer of "none" is the empty set; a
  missing, invalid or failed response is not a prediction.
- A position is scored only when its prediction and all five play responses are valid; excluded positions are
  reported separately with their reasons.
- **Primary score**: exact agreement, 1 when P = O, else 0 (an extra predicted feature is a mismatch, so naming all
  four does not automatically succeed). **Secondary score**, declared secondary: partial overlap |P ∩ O| ÷ |P ∪ O|;
  1 when both sets are empty; 0 when exactly one is empty.
- Baseline: the predictions shuffled across positions within the same setup and phase (1,000 seeded permutations,
  `analysis.boot` seeds), scored the same way with the same conventions; reported: observed mean, baseline mean, the
  baseline's 2.5–97.5 percentiles, and the share of shuffles scoring at least the observed mean. A (setup, phase)
  group with one scored position keeps its own prediction.
- Reported separately, both with an empty O: (a) the selected play did not change across the five calls; (b) the play
  changed but the measured features are identical.
- Five repeats are not presented as a measure of the model's whole behaviour. Stage B results go on the site
  separately, after the experiment is complete.
