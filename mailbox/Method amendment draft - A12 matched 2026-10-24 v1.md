# Method amendment draft: A12, matched Nackgammon contrast (v1)

Oct 24, 2026 · private draft for Ümit's review · brief `ZEKI-BG-SHARED-1563492796520861757`

**Status: proposal only. Nothing in it is frozen, computed or published.** It does not change the site, the frozen files (`freeze.json`, `freeze/league*.json`), the position files, the prompts or any raw result. Once Ümit approves it, it is frozen as its own versioned file, and only then is anything computed. A later change gets a new version (v2, ...). This file never changes in place.

Report this draft belongs to: `mailbox/Shared positions - review and estimates 2026-10-24.md`.

## 1. Corrected counts (text only; the freeze stays as it is)

- Nackgammon set (`positions/nackgammon.jsonl`, sha256 `383ab82c…`): 500 positions. 300 come from turns 1 to 6 and 200 from later turns. Of the 300, 14 are first-roll positions.
- The Nackgammon first roll 3-2 has 27 legal plays, so the frozen 2-to-25 rule left it out (`positions/build-log.json`: `"first_rolls_excluded": {"3-2": 27}`). The design text (design final, lines 121, 135, 154 and 187) still says "15 first-roll positions". From now on the text says 14 for Nackgammon and 15 for the standard opening control. The excluded case is not added back, and the freeze does not change.
- Same-roll first-turn comparisons use only the 14 rolls both sets have, and they stay descriptive. The standard 3-2 position (in the control) has no Nackgammon partner. It stays in the table on/off contrast only.

## 2. Table on/off contrast (separate, unchanged)

- The 200 opening-control rows (`ctl-*`, prompt `nack-v2`) pair with their exact standard IDs (`new-*`, prompt `bg-v2`). Both use the same board, dice, side to move, turn and option order. Offline check, Oct 24: all 200 of 200 pairs match on position, dice, position key, option order and option texts. The control state is the standard state with exactly the opening-table block removed.
- Table effect = PR(control, no table) − PR(same standard positions, with table). It is reported for the 15 first-roll positions (descriptive) and for the other 185 opening positions.
- This contrast is never merged with the Nackgammon contrast below.

## 3. Matched within-setup Nackgammon contrast (new)

### 3.1 Estimand

For each setup *s* and stratum *k* (early, later):

ΔPR(s, k) = 500 × mean over matched pairs of [loss(s, Nackgammon position) − loss(s, matched standard position)]

**Both sides use the no-opening-table prompt.** A positive value means worse on Nackgammon; a negative value means better. No drop is assumed. A standard answer given *with* the table is never the baseline here.

### 3.2 When the matching is done, and what it may use

- The matching is built and frozen before any tested setup answers any Nackgammon or matched standard position. One mapping serves every setup.
- It uses only frozen board data and engine-derived features (section 3.4). The engine features are used for matching only. They are never shown to a model.

### 3.3 Donor pools (standard GNUbg expert self-play only)

| Stratum | Nackgammon positions | Standard donor pool |
| --- | --- | --- |
| Early: turns 1–6 | 300 (turn 1: 14, 2: 60, 3: 51, 4: 54, 5: 66, 6: 55) | the 200 opening-control positions (turns 1–6), plus the 800 opening positions of `positions/extension.jsonl` (turns 2–6) |
| Later: turn 7 or later | 200 (contact 148, race 28, bear-off 19, crashed 5, by GNUbg class) | the 800 non-opening positions of `positions/new.jsonl`, plus the 3,200 non-opening positions of `positions/extension.jsonl` |

- The v1 set is never a donor: its positions come from games between weak models.
- A donor that is not one of the 200 control rows is asked once per setup with the `nack-v2` prompt. These are **extra matched no-table calls**, counted and priced separately. They are not part of the 2,700. Asking extension positions this way does not run the 4,000-position extension (that stays an optional, separate item).

### 3.4 Features (GNUbg 1.08, the scoring settings: every legal play at 2-ply, cubeless money equity)

Exact strata (a pair must agree on all of these):

1. Stratum (early or later).
2. Early: the exact turn number. Turn 1 also needs the exact roll.
3. Later: GNUbg class group (contact including crashed; race; bear-off).
4. Legal-play band: 2–5, 6–10, 11–15, 16–20 or 21–25.

Distance features (each standardised by its pooled SD within the exact cell):

- f1: top-two equity gap, best minus second best, capped at 0.5. **Weight 2.**
- f2: share of legal plays within 0.02 of the best.
- f3: share of legal plays losing more than 0.08.
- f4: mean loss over the legal plays, each play's loss capped at 1.0.
- f5: log of the number of legal plays.
- f6 (later stratum only): the mover's pip lead.

### 3.5 Calipers, matching, ties

- **Caliper:** |Δf1| ≤ 0.25 SD and a total weighted distance ≤ 1.0. A Nackgammon position with no donor inside the caliper stays unmatched and is counted. The caliper is never loosened to raise coverage.
- **Matching:** 1:1 without replacement, solved as an optimal assignment (minimum total distance) within each exact cell. Each pair has weight 1.
- **Turn 1:** each of the 14 Nackgammon first-roll positions pairs with the control's first-roll position for the same roll. This needs no distance and is descriptive only.
- **Tie rule:** when total costs are equal, donors are ordered by sha256(`a12-match-v1:3723441206:` + donor id) (`3723441206` is the frozen sampling seed in `seeds.json`), and the lowest comes first.
- **No donor priority:** control rows are not preferred to save calls. The extra calls follow from the distances and are priced before anything runs.

### 3.6 Exclusions (applied before matching, counted)

- Any position whose GNUbg evaluation fails.
- More than one donor from the same source game in one stratum: the first in tie-rule order is kept.
- Unmatched Nackgammon positions are kept in the counts. They are not dropped from the Nackgammon set's own error rate.

### 3.7 Freeze, coverage, balance

- New files, each hashed in a new `freeze/a12-match-v1.json`: the feature table (all Nackgammon positions and donors); the mapping (Nackgammon id → donor id, cell, distance); `positions/a12-matched-standard.jsonl` (the donors that are not control rows, prompt `nack-v2`, ids `a12m-<original id>`, `paired_with` the original id); the GNUbg build and settings; and the seed string. Old freeze files stay untouched.
- Reported: coverage per stratum (matched / 300, matched / 200, unmatched counts per cell), and balance per stratum (standardised mean difference of f1–f6, turn, pip count and class share). Balance is reported whether or not it is good.

### 3.8 Analysis and uncertainty

- Early and later ΔPR are each reported per setup. Combined ΔPR is secondary, weighted by matched pairs per stratum.
- **95% interval:** paired cluster bootstrap, 2,000 resamples, fixed seed. The unit is the Nackgammon source game: each of the 300 games contributes its one or two positions together with their donors, so dependence within a game is respected.
- A pair counts for a setup only when both sides have a scored decision. Invalid answers are scored as the random legal play the runner played (main rule). Timed-out decisions are left out and counted.
- Differences between setups (ΔPR of setup A minus ΔPR of setup B) use the same resamples. A12 has no pre-registered hypothesis, so no Holm step applies. It is descriptive with intervals.

### 3.9 Interpretation (printed next to the result)

- These are matched *different* positions, not identical positions. The contrast does not isolate a causal memorisation effect.
- GNUbg's network learned standard play, so its scores for early Nackgammon positions are likely less accurate. This limitation sits next to every A12 number.
- Weak GNUbg is a sanity anchor only.
- The old unmatched "unfamiliar-start effect" (early Nackgammon minus control) is no longer an A12 result. If it is shown at all, it is labelled "unmatched, different positions".

## 4. Prompt wording (decision pending, no change made)

`prompts/nack-v2.md` (sha256 `fa7397be…`, frozen) keeps the standard Setup sentence: "two on the 24-point, five on the 13-point (the midpoint), three on the 8-point, and five on the 6-point." The Nackgammon start is two each on the 24- and 23-points, four on the 13-point, three on the 8-point and four on the 6-point. All 14 turn-1 Nackgammon requests show that board under the standard sentence. The prompt never says "Nackgammon".

Options for Ümit:

- (a) Keep `nack-v2` and document the mismatch.
- (b) Freeze a new version (for example `nack-v3`) whose only change is a truthful setup sentence for Nackgammon rows. The matched standard rows keep `nack-v2`, so the two sides differ only in that sentence.

Nothing is edited until Ümit chooses.

## 5. Runner rules for the eventual run

- Never pass `--prompt-version` to `jevgammon ask` for these files. That flag overrides each row's `prompt`. Without it, the row's `prompt` wins over the config's `bg-v2`.
- Write answers to a separate SQLite file (not `v3.db`). `v3.db` keeps its single writer.
- Reuse an answer only when the setup name, position id, prompt version, order seed **and** the setup's settings JSON are identical. `ask` checks only the first three, so the run script checks the settings hash too.
- Before each set, re-render it offline and compare the decision-route and chat-route hashes with the values in the report. Stop on any difference.
