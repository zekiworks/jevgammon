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

### 9.10 Stage B amendment (2026-10-24, 19:22 UTC; Can's decisions, before any stage B call and before selection)

Replaces the position source of §9.9. The scoring rules of §9.9 are unchanged.

**Positions (v2 freeze).**
- Pool: `positions/new.jsonl` (sha256 `ad06427c4106e8d889b027dc49f79557fb2739b8fd278f8fa2f05da72dc12d69`, 1,000 rows,
  200 per phase). This file is part of the shared standard set the Cup teams answer in the shared-position run
  (v1 set + new set, prompt `bg-v2`).
- Excluded: positions with fewer than 2 legal plays (none expected: the file was built with 2–25 legal plays).
- Position class at margin 0.001, by the site's rule (`analysis.play_call`): hitting rolls = the number shown with each
  option (`describe.py`); losses = GNUbg 1.08 2-ply, cubeless, the existing settings (`tools/v3/score.py evaluate`,
  `engine.PLY2`), computed on CPU (`nice -n 19`, at most 8 processes). No trade-off when every legal play leaves the
  same number of hitting rolls; otherwise stake = the loss of the best minimum-hitting play; Risk pays when the stake is
  at least 0.001, else Safety pays.
- Targets: 40 Risk pays, 40 Safety pays, 20 No trade-off. Within a class, the target is spread evenly over the five
  phases (opening, contact, holding, race, bear-off): 8 per phase for Risk pays and Safety pays, 4 per phase for No
  trade-off. In each (class, phase) cell, the eligible ids with the smallest hex
  sha256(`close-choices-b-v2-2026-10-24:` + id) are taken.
- Shortfall: when a cell holds fewer eligible ids than its quota, all of them are taken and the missing places go to the
  other phases of the same class, one at a time, in the phase order above, to phases that still have unselected ids
  (next smallest hash). A class is never filled from another class; if a class has fewer eligible ids than its target,
  all are taken and the shortfall is reported.
- Each row keeps its stored `option_order`; every call for a position uses that one order. Rows are written
  byte-identical to the source to `positions/close-choices-b-v2.jsonl`; the record is `freeze/close-choices-b-v2.json`
  (rule, seed text, source hash, engine values' file hash, per-cell counts, ids, output hash). The earlier freeze
  (`freeze/close-choices-b.json`, 20 per phase from v1 + new) is superseded and kept, marked as such.
- The list of the 100 ids and the output hash are published below (9.11) before any stage B call.

**Settings.** Every setup keeps its league settings exactly: temperature (or none sent), reasoning setting, prompt
version and format, max tokens, provider route. Temperature is recorded per setup where known (the value sent, or the
provider's documented default) and as "not disclosed" where not. A setup that gives five identical answers on every
scored position is reported as deterministic on these positions; settings are never changed to create variation.

### 9.11 Stage B positions, v2 freeze (published 2026-10-24 19:23 UTC, before any stage B call)

- File `positions/close-choices-b-v2.jsonl`: 100 rows, sha256 `88bc3904595c6dccc3f6fe015e865b7b23e3ed81b9be1ad8d1e7efcf5848410c`. Record `freeze/close-choices-b-v2.json`;
  script `tools/site/close_choices_b_freeze.py`. Source `positions/new.jsonl` sha256 `ad06427c4106e8d889b027dc49f79557fb2739b8fd278f8fa2f05da72dc12d69`.
- Engine values: GNUbg 2-ply of every legal play of the 1,000 pool positions (sha256 of the sorted position/play/equity
  lines `fe5ed3a3a6128450a9a01d87f551558917c0107462de2a341da005b856ac24f0`). Excluded for fewer than 2 legal plays: 0.
- Race and bear-off positions have no contact, so every one is No trade-off; the Risk pays and Safety pays quotas of those
  phases moved to opening, contact and holding by the shortfall rule. Shortfall per class: none.
- Options per position: 2–25, 1,204 in all (no decision is split into groups).

| Class / phase | Eligible | Selected | Ids (in hash order) |
| --- | --- | --- | --- |
| Risk pays / opening | 124 | 14 | new-0160, new-0002, new-0119, new-0175, new-0122, new-0092, new-0069, new-0009, new-0007, new-0149, new-0016, new-0111, new-0046, new-0107 |
| Risk pays / contact | 46 | 13 | new-0356, new-0274, new-0353, new-0254, new-0337, new-0256, new-0385, new-0239, new-0297, new-0328, new-0244, new-0349, new-0361 |
| Risk pays / holding | 34 | 13 | new-0532, new-0469, new-0598, new-0511, new-0588, new-0572, new-0474, new-0550, new-0554, new-0413, new-0525, new-0459, new-0593 |
| Risk pays / race | 0 | 0 | — |
| Risk pays / bear-off | 0 | 0 | — |
| Safety pays / opening | 73 | 14 | new-0200, new-0155, new-0156, new-0190, new-0131, new-0112, new-0040, new-0043, new-0050, new-0147, new-0188, new-0053, new-0041, new-0070 |
| Safety pays / contact | 128 | 13 | new-0263, new-0371, new-0264, new-0250, new-0377, new-0330, new-0237, new-0344, new-0249, new-0383, new-0362, new-0307, new-0270 |
| Safety pays / holding | 142 | 13 | new-0494, new-0467, new-0513, new-0562, new-0529, new-0575, new-0518, new-0410, new-0564, new-0422, new-0546, new-0465, new-0582 |
| Safety pays / race | 0 | 0 | — |
| Safety pays / bear-off | 0 | 0 | — |
| No trade-off / opening | 3 | 3 | new-0062, new-0165, new-0024 |
| No trade-off / contact | 26 | 5 | new-0388, new-0278, new-0331, new-0329, new-0281 |
| No trade-off / holding | 24 | 4 | new-0447, new-0591, new-0537, new-0430 |
| No trade-off / race | 200 | 4 | new-0679, new-0618, new-0626, new-0706 |
| No trade-off / bear-off | 200 | 4 | new-0999, new-0814, new-0801, new-0919 |

### 9.12 Stage B prediction request (2026-10-25; built and tested offline, no model call; approved, not run)

Ümit's instruction of 2026-10-25 (ZEKI-BG-CLOSE-CHOICES-1563831405077725236): stage B no longer waits for the
ladder. The run waits for confirmation with Can. Gemma 4 31B (on) and any changed team join after the ladder settles.

**Teams.** Each name resolves to exactly one `v3.db` roster row. Its settings are copied unchanged into
`leagues/close-choices-b.json` (they equal the League 2 and 3 config entries):

| Team | Roster id | Spec | Route | Model id sent | Setting | Temperature |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-6.1 Sol (low) | 23 | `openai/gpt-6.1-sol` | ChatGPT subscription, Codex Responses API | `gpt-6.1-sol` | reasoning effort low | none sent; not disclosed |
| GPT-6.1 Sol (high) | 45 | `openai/gpt-6.1-sol` | same | `gpt-6.1-sol` | reasoning effort high | none sent; not disclosed |
| GPT-6 Astra (on) | 47 | `openai/gpt-6-astra` | same | `gpt-6-astra` | reasoning effort medium (the model's default) | none sent; not disclosed |
| Gemini 3.8 Flash (low) | 17 | `antigravity/gemini-3.8-flash` | Google Antigravity subscription (generateContent) | `gemini-3.8-flash-low` | thinking level low | 1.0, sent |
| Claude Opus 5.5 (on) | 34 | `anthropic/claude-opus-5-5` | Claude subscription, Messages API | `claude-opus-5-5` | effort high (default, adaptive thinking) | none sent; 1.0 is Anthropic's documented default |

The match context shown is that of Leagues 2 and 3: prompt `bg-v2`, option-order seed 1190975713392774006, 3 rounds,
no clock, 300 turns.

**Prediction request.** `prompt::prediction_user` returns the play call's user text (`letter_user`: the state, the
instructions and the options lettered in the stored order). Only its last line, the letter instruction, is replaced by
`prompts/prediction.txt`:
- the request's question, verbatim;
- on the next line, the approved format line: "Answer with the features you name, using only these words: hitting
  risk, making a point, the race, the prime; or the single word none."

Everything else is the play call's:
- the system prompt (Cygnet's letter-readout system prompt, as in the leagues);
- the model id, reasoning or thinking setting, temperature (or none), token limit and configured extra fields.

**Answer constraint.** As with the letter, the provider constrains the answer:
- ChatGPT and Claude: JSON schema `{"features": [...]}`, each item one of the four feature words or `none`.
- Gemini: `application/json` with the same object schema.

The schema does not exclude duplicates, or `none` together with a feature; the parser judges those.

**Parsing (`prompt::parse_prediction`; no repair, no re-ask).**
- Valid answers:
  - JSON `{"features": [...]}` with no other key, or a bare JSON list, optionally after `<think>` reasoning or inside a
    code fence;
  - every item one of the four words or `none`, case and outer spaces ignored;
  - duplicates collapse.
  - `none` alone, or an empty list, is the valid empty set.
- Invalid answers: `none` with a feature, an unknown or non-string item, prose (including a bare `none` that is not
  JSON), a refusal, or an empty reply.
- A failed request is final.
- Mapping to the §9.5 feature ids: hitting risk → hitting, making a point → points, the race → race,
  the prime → prime.

**Run commands.**
- `jevgammon predict`: one prediction call per team and position, into table `predictions`. A stored row, valid,
  invalid or failed, is never asked again.
- `jevgammon ask --repeats 5`: the five play calls, the league request unchanged. It is run once per team and not
  rerun, so a failed play call stays failed.
- The prediction is never shown to a play call; every call is a separate, stateless request.

**Offline checks (2026-10-25, harness `ef991ab`).**
- Unit tests, 63 passing:
  - the prediction prompt differs from the letter prompt only in its last line;
  - on every route the prediction body keeps every play setting;
  - synthetic answers parse as above;
  - synthetic Codex, Claude and Antigravity replies parse.
- `jevgammon render-stage-b` rebuilt the stored smoke requests of these exact settings byte for byte:
  - Gemini 3.8 Flash (low) [antigravity]: 50 of 50;
  - GPT-6.1 Sol (low) and (high): 50 of 50 each, with that run's clock;
  - GPT-6 Astra (on) and Claude Opus 5.5 (on): 10 of 10 each.
- Rendered for the 5 teams × the 100 v2 positions: 500 play requests and 500 prediction requests, with option orders
  equal to the stored ones and no other difference between play and prediction.
  - The record is `freeze/close-choices-b-v2-requests.json`, with the file `freeze/close-choices-b-v2-requests.jsonl.gz`
    (jsonl sha256 `0e551aecc353f00fe750f54a6297231cc5a1846d433ad4cc96eaea2f007a898b`).
  - It holds one sha256 per request and one per team.

**Not checked offline:** whether each provider accepts the prediction schema. That can only be seen in a response.
