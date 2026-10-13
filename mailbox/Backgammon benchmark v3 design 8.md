# Backgammon benchmark v3: design

Oct 13, 2026 · @Can Basaran

## What changed from v2

v3 keeps v2's leagues, prompt, match rules and hypotheses H1 to H5. It adds changes drawn from related work and from checks on v1 data, and corrects the error-rate scale. Changes 4 and 10 add model calls: about 70,400 in all, or 43% more. Change 10's calls run almost all on our GPUs or cheap decision APIs.

| # | Change | Where | Why | Extra calls |
| --- | --- | --- | --- | --- |
| 1 | Error-rate scale corrected; forced moves excluded; labelled as checker-play PR | Goal, Scoring, Limits | v2's human bands were wrong, and PR counts only decisions with a real choice | 0 |
| 2 | New A13 and H6: do fixed positions predict league results? | Hypotheses, Analyses | In PokerBench, a model that won on the benchmark lost at the table | 0 |
| 3 | Rollouts: near-ties that a setup chose go first | Scoring | Bhardwaj et al. spend the scoring budget where agents disagree | 0 |
| 4 | A12 (Nackgammon start) moved from optional to core | Shared positions, Analyses | Novelty is gg-bench's one clear advantage over us | About 22,400, with the opening control |
| 5 | A3 splits the reasoning gain by game phase | Analyses | Bhardwaj et al. read a gain that is flat across phases as a better evaluation, not deeper search | 0 |
| 6 | A4 splits errors by the equity gap between the top two plays | Analyses | A wrong play in a clear position is a blunder; in a close call it is mostly noise | 0 |
| 7 | A5 runs on shared positions only; option order is fixed by seed and logged | Protocol, Analyses | v1's play order put the best play early; Kadavath et al.: calibration depends on the answer format | 0 |
| 8 | A2 reports blunder share as well as error rate | Analyses | In LLM Chess, move history barely changed results but cut blunders sharply | 0 |
| 9 | Related work section; Scoring credits Bhardwaj et al. | Scoring, Related work | Our scoring method follows theirs | 0 |
| 10 | League 1 extension; superiority bars test the interval, not the point estimate; meaningful difference set per tier | Hypotheses, Shared positions, Budget | v1 data: at 2,000 positions, most pairs cannot resolve 2 points | About 48,000 |

## Goal

The benchmark measures how well AI models decide under risk, with an exact referee for every move. Backgammon has dice, so every decision carries risk. GNU Backgammon (GNUbg) scores each move, whatever the dice do next. Finance has no such referee.

It answers eight questions:

1. **Harness vs model:** how much of a decision's quality comes from what the model is shown, and how much from the model?
2. **Reasoning:** does thinking before the answer lower the error rate, what does each point of improvement cost, and in which game phases does the gain appear?
3. **Tiers:** how far apart are decision models, open models, workhorses and frontier models? Is an open model behind a closed model of the same tier?
4. **Confidence:** does a model's probability for its chosen move show when the move is right?
5. **Routing and teams:** can a cheap model answer first and a strong model answer only the hard positions? Can a selector find the best answer among several models?
6. **Cost and speed:** what does each model's error rate cost in dollars and seconds?
7. **Familiarity:** how much does known opening knowledge help? Do error rates rise more than expected from an unfamiliar starting position (Nackgammon)?
8. **Validity:** do scores on fixed positions predict results in played games?

Terms used in this doc:

- **Decision:** one play chosen from the full list of legal plays. The program generates the list, so a model can never make an illegal move. A forced move (only one legal play) is not a decision.
- **Equity:** expected points per game.
- **Error rate:** the average equity a model gives away per decision, times 500. Lower is better. This is the performance rating (PR) that backgammon players use, here for checker plays only.
- **Human scale (eXtreme Gammon):** under 2.5 world champion, 2.5 to 5 world class, 5 to 7.5 expert, 7.5 to 12.5 advanced, 12.5 to 17.5 intermediate, 17.5 to 22.5 casual, 22.5 to 30 beginner, 30 or more distracted. Every v1 decision model sits in that last band (31.8 to 59.9). Human ratings also count cube decisions, so our comparison with them is approximate.
- **Setup:** one model with one set of settings. Gemma 4 31B with reasoning off and with reasoning on are two setups.

## Hypotheses, fixed before match 1

We write down each hypothesis and its bar before any run, so the bar cannot move to fit the result. The bars below are proposals; we confirm or change them before the freeze. A result that misses its bar is published too.

| ID | Hypothesis | Counts as yes | Analysis |
| --- | --- | --- | --- |
| H1 | Computed consequences lower every model's error rate | For each of the 6 ablation models, the error rate with consequences is at most half the notation-only error rate, and the paired 95% interval excludes 0 | A2 |
| H2 | Reasoning lowers the error rate | Primary: Gemma 4 31B with reasoning on beats reasoning off, with a 95% interval of the gain that excludes 0, on 6,000 positions (sized for a 3-point gain). Every other off/on and low/high pair gets the same test on its positions and is reported on its own | A3 |
| H3 | At the same tier, the best open model is close to the best closed model | The 95% interval of the difference between the best open and the best closed setup lies inside ±3 PR points (an equivalence test), in League 2 and in League 3 | A1 |
| H4 | A cheap first model plus a frontier model matches the frontier model alone, for less | The 95% interval of (cascade minus Astra low alone) stays below +2 PR points (non-inferiority), at half Astra low's cost or less; cutoff chosen on half the positions | A6 |
| H5 | A selector beats the best single model | In League 1, on 6,000 positions, the selector beats its best member on held-out positions, with an interval that excludes 0 (sized for a gain of about 3 points). Leagues 2 and 3 are reported, not tested, because most of their setups have no probabilities | A7 |
| H6 (new) | Scores on fixed positions predict league results | Among model setups only, ranking them by shared-position error rate and by league points gives a Spearman correlation that is positive in every league and at least 0.6 when the three leagues are combined, weighted by league size | A13 |

Proposed rules behind the bars. The smallest difference we treat as meaningful depends on the tier: 2 PR points among frontier and closed workhorse setups, 4 among decision models and open models, whose errors are larger and vary more. A check on v1 data set this: across 1,000 positions and 91 setup pairs, the 95% half-width at 2,000 positions is about ±1.3 for frontier pairs, ±2.6 for the median pair and up to ±4.1. Superiority tests (H2, H5) therefore require the interval to exclude 0, with the sample sized for the expected gain. They no longer require the point estimate to reach that gain, which would pass only half the time even when the gain is real. League 1 gets 4,000 extra positions for this, because its setups run on our GPUs or cheap decision APIs. A result that misses its bar is reported as "not shown", not as "no difference". H3 and H4 are now interval tests, because a point estimate inside a margin proves nothing. H4's margin rises from 1 to 2 PR points, since a 1-point margin is likely narrower than the interval itself. H6 leaves out the baselines and the anchor, because they sit at the extremes of both rankings and would inflate the correlation. League 3 has only 8 model setups, so the bar sits on the combined test, which merges per-league correlations because points are not comparable across leagues.

## Leagues and players

Three leagues, each a single round robin with the v1 match rules: 37 players and 219 matches in total. Unchanged from v2. League tables only compare players inside one league. The shared positions (below) compare all setups across leagues. GNUbg at a weak level plays in every league as a fixed anchor. Two setups of one model (off and on, low and high) meet like any other pair. This is intended: it is a head-to-head test of reasoning.

### League 1: decision models and models that run on our own hardware (15 players, 105 matches)

| Player | Kind | Runs on | Setups |
| --- | --- | --- | --- |
| Jev 1.13.0 | Decision model | TypeSafe API | 1 |
| GPT-6 Luna | Decision model | OpenAI Decisions API | 1 |
| Decider v1.1 27B | Decision model | Perplexity API (frees our GPUs) | 1 |
| SubQ Snap Preview | Decision model | SubQ API | 1 |
| Fastino GLiDE | Decision model | Fastino API | 1 |
| Celeris-1 Decision | Decision model | Celeris API | 1 |
| Clef | Decision model | Our GPUs | 1 |
| Open-Jev 27B v1.1 | Decision model | Our GPUs | 1 |
| Cygnet (Gemma 4 12B) | Answer-letter probabilities | Our GPUs or a Spark | 1 |
| Gemma 4 31B | Answer-letter probabilities | Our GPUs, 1 card | 2: reasoning off, on |
| Qwen3.8-27B | Answer-letter probabilities | Our GPUs or a Spark | 1: reasoning off |
| Random legal play | Baseline | CPU | 1 |
| Safest play (fewest hitting rolls) | Baseline | CPU | 1 |
| GNUbg, weak level | Anchor | CPU | 1 |

### League 2: workhorses, closed and open (13 players, 78 matches)

| Player | Kind | Runs on | Setups |
| --- | --- | --- | --- |
| Gemini 3.8 Flash | Closed | Gemini API | 2: low, high |
| Claude Sonnet 5.5 | Closed | Claude subscription | 2: low, high |
| GPT-6.1 Sol | Closed | ChatGPT subscription | 2: low, high |
| DeepSeek V4.1 Flash (552B) | Open weights | Paid provider, pinned | 2: off, on |
| Qwen3.8 Flash Next | Open weights | Paid provider, pinned | 2: off, on |
| GLM-5.3 (743B) | Open weights | Paid provider, pinned | 2: off, on |
| GNUbg, weak level | Anchor | CPU | 1 |

### League 3: frontier, closed and open (9 players, 36 matches; starts when Gemini 4 Argon is out)

| Player | Kind | Runs on | Setups |
| --- | --- | --- | --- |
| GPT-6 Astra | Closed | ChatGPT subscription | 2: low, high |
| Claude Opus 5.5 | Closed | Claude subscription | 2: low, high |
| Gemini 4 Argon | Closed | Gemini API | 2: low, high |
| DeepSeek V4 Pro (1.6T) | Open weights | Paid provider, pinned | 2: off, on |
| GNUbg, weak level | Anchor | CPU | 1 |

If Qwen3.8-Max (2.4T) has open weights by the freeze, it joins League 3 with two setups: 11 players, 55 matches. Left out: Liquid d1 (its free tier stopped a v1 league), GLM-4.7-Flash and GLM-5.3-Flash (replaced by the full GLM-5.3).

Open questions: does each paid provider return answer-letter probabilities (top\_logprobs)? A model without them answers with one letter and is left out of the confidence analyses. Are the GLM-5.3 weights out, and on which provider? Known so far: Gemini 3.8 Flash's API refuses token probabilities, and the GPT-6 Astra and Claude Opus 5.5 subscriptions return none. Claude Sonnet 5.5, GPT-6.1 Sol and Gemini 4 Argon are likely the same but unchecked. Does Perplexity host Decider v1.1? v1 used its hosted v1, and League 1 relies on it to free our GPUs.

## Protocol

Every player gets the same prompt, the same rules and the same dice, and nothing changes after match 1.

- **Match rules:** unchanged from v1. Rounds of two games with the same dice and swapped seats; 3 rounds, or first to 5 points after a full round; 300-turn limit; no doubling cube. Dice seeds are fixed per league and published.
- **One prompt for all, version bg-v2:** the League #8 format. Rules and strategy (the short text), score and time, position, race line, dice, the question, then every legal play with its computed consequences. No move history, because it made no measurable difference in v1. The longer chat-model prompt from v1 is retired.
- **Option order (new):** the legal plays appear in a fixed random order per position, drawn from a published seed. The order never comes from an engine's ranking. The letter of the chosen play is logged, so a bias toward early or late letters can be checked. This rule is required: in v1 the runner listed plays in move-generation order, which put the best play early. On the v1 set its average position was 0.38, where 0.5 means no effect.
- **Long play lists:** when a position has more legal plays than a model's limit, the plays are split into equal groups. The model picks a winner in each group, then chooses among the winners. The group size is logged with every decision, and these decisions are left out of the confidence analysis (A5).
- **Reading the answer:**
  - Decision models: their probability for each option.
  - Open models: the probability of each answer letter. With reasoning on, the model reasons first; then the runner adds "Answer:" and reads the letter probabilities.
  - Models without probabilities: one letter, constrained to the option letters. These are labelled and left out of the confidence analyses.
- **Clock:** 30 seconds free per decision, then a 5-minute bank per game. Before Leagues 2 and 3, each setup answers 50 positions as a smoke test. If its 90th-percentile time is above 30 seconds, that league plays without a clock, and the page says so. Expect this for some reasoning-on setups: locally, DeepSeek V4.1 Flash with thinking took about 2 minutes per decision. Those 209 answers came from our own server, so they show the problem exists; the smoke test still runs against the pinned provider.
- **Invalid answers:** not repaired and not retried. The runner plays a random legal play, marks the decision invalid, and reports the share of invalid decisions per setup. v1 differed: it re-asked up to 3 times, then played the first legal play, which v1's order favoured.
- **Retries:** network and server errors (HTTP 408, 429, 5xx) are retried up to 3 times with backoff. Retry time is logged but not charged to the clock.
- **Closed-book:** CLI runs start in an empty folder with web search and tools turned off, as in the Turkish runner.
- **Freeze:** roster, prompt, settings, dice seeds, option-order seed, providers and quantization are hashed before match 1. A player that fails mid-league keeps its finished matches; its remaining matches are forfeits. No reruns.
- **Logged per decision:** league, match, game, turn, setup, prompt version, harness commit, provider, quantization, option order, letter chosen, all option probabilities, request time, tokens and cost.

Open question: with reasoning on, does each paid provider continue a prefilled "Answer:" and return the letter probabilities? Locally, DeepSeek V4.1 Flash with thinking and a JSON schema returned a letter but no probabilities. A setup without them answers with one letter and leaves the confidence analyses.

## Shared positions

Every setup in every league answers the same 2,000 positions with the bg-v2 prompt, plus 500 positions from an unfamiliar starting position and a 200-position control. This set, not the league tables, compares models across leagues.

| Part | Positions | Source | Why |
| --- | --- | --- | --- |
| v1 set | 1,000 | Leagues #8 to #13, 2 to 25 legal plays | Comparable with v1, except that v1 listed plays in generation order |
| New set | 1,000 | GNUbg self-play at expert level, 200 per phase: opening, contact, holding, race, bear-off | v1 positions come from games between weak models, so they over-represent odd positions |
| Nackgammon (new, core) | 500 | GNUbg self-play from the Nackgammon start: 300 from turns 1 to 6, including each of its 15 first-roll positions once, and 200 from later turns | Tests how much known opening knowledge helps (A12) |
| Opening control (new) | 200 | The new set's 200 opening positions, including all 15 first-roll positions, with the opening table removed from the prompt | Separates the missing table from the unfamiliar start (A12) |
| League 1 extension (new) | 4,000 | More GNUbg expert self-play positions, same phase mix as the new set; League 1 setups only | Gives H2 and H5 enough power, where extra positions cost GPU time, not money |

- Every position has 2 to 25 legal plays, so no model needs group splitting on this set.
- Consistency: a fixed subset of 200 positions is asked 5 times for every setup.
- The harness ablation (A2) runs on the 2,000 standard positions.
- Nackgammon changes only the starting position, not the rules, and games drift back into ordinary middlegames. Its prompt drops the opening table, whose plays are wrong for Nackgammon, and keeps the strategy principles.
- The v1 positions are stored in generation order, so they are reshuffled with the option-order seed. All position files are frozen with a sha256 hash before any run.

Settled: GNUbg 1.08 scores Nackgammon; its start evaluates at +0.147 equity for the side to move, against +0.068 for the standard start. Hypergammon is out: it returns invalid results without its separate databases, and the runner assumes 15 checkers. GNUbg classifies positions only as contact, crashed, race or bear-off, so the rules below add opening and holding. They are proposals; confirm them before the freeze.

Proposed phase rules, applied in this order (the first rule that matches wins):

1. **Opening:** turns 1 to 6, that is, each side's first three moves. Contains each of the 15 first-roll positions once, because the opening table covers only the first roll.
2. **Bear-off:** any of GNUbg's bear-off classes.
3. **Race:** GNUbg's race class.
4. **Holding:** a contact position after turn 6 where one side has escaped all its back checkers (none on the bar or on its points 14 to 24), and the other side keeps one high anchor: 2 or more checkers on its 18-, 20- or 21-point (the opponent's bar, 5- or 4-point) and no other checkers on its points 18 to 24. This follows The Gammon Press's definition of a holding game. The race deficit is reported, not required.
5. **Contact:** every other position, including GNUbg's rare crashed class.

Duplicates are removed in every phase. A position means the board, the dice and the side to move together, so the 15 first-roll positions stay distinct. Holding positions may be scarce in expert self-play: collect them first, and if fewer than 200 distinct ones appear, use all of them and log the count.

Proposed game-plan tags, for analysis only (A4), not for sampling. Each contact position after the opening gets the first tag that matches:

1. **Blitz:** one side has a checker on the bar against a home board with 3 or more made points.
2. **Back game:** one side holds 2 or more anchors on its points 18 to 24.
3. **Holding:** the holding rule above.
4. **Low-anchor game:** one side's only anchor in the opponent's home board is on its 22-, 23- or 24-point (the opponent's 3-, 2- or ace-point).
5. **Priming:** one side has 4 or more made points in a row.
6. **Other:** everything else.

Sources for the rules (the page cites only The Gammon Press and describes the tags itself): [The Gammon Press, lesson 9](https://thegammonpress.com/backgammon-lesson-9-holding-games/) for holding and low anchors; the game-plan order is adapted from a [hobby backgammon AI](https://github.com/TzameretIshay/Backgammon/blob/b4d0a9380e62ed904c26b12df3868e5edc7cea67/back-gammon/scripts/AI.gd).

Proposed Nackgammon split: 300 of the 500 come from turns 1 to 6, including its 15 first-roll positions; 200 come from later turns. The early 300 pair with the standard opening phase in A12. The later 200 show whether the effect fades as games drift back into ordinary middlegames.

## Scoring

GNUbg 1.08 scores every decision, in the leagues and on the shared positions. The method follows [Bhardwaj, Jaiswal and Pathak (2026)](https://neurips.cc/virtual/2026/172941), who rate agents by their loss per decision against GNUbg instead of by results.

- Every legal play is evaluated at 0-ply. The five best plays and the chosen play are evaluated again at 2-ply. The loss is the 2-ply equity of the best play minus that of the chosen play.
- **Forced moves (new):** a position with only one legal play is not a decision. It counts in no rate.
- **Rollouts for close calls (changed):** on the shared positions, every near-tie is rolled out, and near-ties that a setup chose go first. A near-tie means the two best plays are within 0.02 equity at 2-ply. When no setup chose either play, a rollout shifts every setup's loss there by the same amount. That changes no comparison, but it moves absolute error rates, which the human scale compares against. So these go last, and only they are skipped if scoring time runs out.
- **Error rate (PR):** mean loss × 500 over decisions, printed next to the human scale and labelled "checker-play PR".
- **Best-play share:** decisions with a loss below 0.001. This is the closest analogue of the accuracy that PokerBench reports.
- **Blunder share:** decisions with a loss above 0.08.
- **League measures:** points, matches won-drawn-lost, gammons, share of safest plays, hitting rolls left.
- Equity is cubeless money equity; match score is ignored, as in v1.

Open question: how many games per rollout? It sets both accuracy and scoring time. With 32 setups, few near-ties will have no chooser, so the ordering saves little; we count them once the answers are in. Rollouts through GNUbg's Python interface are not tested yet.

## Analyses

Twelve analyses run on every result; the cube track stays optional. Changes from v2 are marked.

| ID | Question | Data | How | Hypothesis |
| --- | --- | --- | --- | --- |
| A1 | How good is each setup? | Shared positions; league decisions | Error rate, best-play share and blunder share, each with a 95% interval, next to the human scale and cost | H3 |
| A2 | How much does the harness do? | Shared positions; 6 setups, reasoning off or low: Gemma 4 31B, Decider v1.1, Jev 1.13.0, DeepSeek V4.1 Flash, Gemini 3.8 Flash low, GPT-6 Astra low | Three prompts: notation only; + computed consequences; + consequences and the last 10 moves. Paired difference per position. **Changed:** error rate and blunder share for every prompt | H1 |
| A3 | How much does reasoning do? | Every off/on and low/high pair | Paired difference per position; extra dollars and seconds per PR point gained. **Changed:** the gain split by the five phases of the new set | H2 |
| A4 | Where do models fail? | Shared positions | Error rate by game phase and by number of legal plays. **Changed:** also by the equity gap between the top two plays: under 0.02, 0.02 to 0.08, over 0.08; and by game-plan tag (blitz, back game, holding, low-anchor, priming, other) | none |
| A5 | Does confidence show when a move is right? | Setups with probabilities. **Changed:** shared positions only | AUROC ("right" = best play), ECE with 10 bins, Brier score, risk-coverage curve; letter-position bias | none |
| A6 | Can a cheap model go first? | First: Decider v1.1, Jev, Gemma 4 31B. Second: Astra low, Opus low | Keep the first model's play above a cutoff, else ask the second. Cutoff chosen on half the positions, scored on the other half, 300 splits. Error rate against cost | H4 |
| A7 | Can a team beat its best member? | All setups in a league | Selectors: highest probability; calibrated probability; agreement count; game phase. Cross-fitted. Oracle (best answer any member gave) as the upper bound. In Leagues 2 and 3 only agreement count and game phase apply, because most setups there have no probabilities | H5 |
| A8 | Does a model repeat its play? | 200 positions × 5 runs | Share of positions where the chosen play changed | none |
| A9 | What does it cost? | All setups | Dollars per 1,000 decisions; median and 90th-percentile seconds; error rate against cost | none |
| A10 | Who won each league? | League games | Standings, wins-draws-losses, gammons, safest-play share, hitting rolls left | none |
| A12 | How much does known opening knowledge help? **Changed:** now core, Nackgammon | 500 Nackgammon positions and the 200-position opening control; all setups | Three error rates per setup: standard opening positions with the table, the same positions without it, and early Nackgammon positions. Table effect = second minus first, reported separately for the 15 first-roll positions, where the table gives the answer, and for later opening positions, where it can only distract. With only 15 positions, the first-roll result is descriptive. The 15 Nackgammon first-roll positions pair with the 15 standard ones without the table, at the single move where book knowledge matters most (also descriptive); unfamiliar-start effect = third minus second, read against the other setups' changes. Weak GNUbg is a sanity anchor only: its network learned standard play | none |
| A13 | Do fixed positions predict league results? **New** | Shared positions; league games | Per league: Spearman correlation between shared-position error rate and league points; also league-decision error rate against shared-position error rate | H6 |

How to read A3's phase split: a reasoning gain concentrated in contact positions suggests the model is searching ahead. A gain that is flat across phases suggests a better judgement of positions instead.

Optional track, if time allows:

- **A11, doubling cube:** 500 positions with double/no double and take/pass decisions, scored by GNUbg cube equity. These are yes/no decisions, a fair test for decision models.

## Statistics

Intervals resample whole positions or whole games, not single decisions, because moves inside one game are not independent. v1 treated them as independent, so its intervals were too narrow.

- **95% intervals:** bootstrap with 2,000 resamples and a fixed seed. Shared positions resample positions; league results resample games.
- **Paired comparisons:** on the shared positions, the per-position difference in loss between two setups, with a paired bootstrap interval.
- **Multiple tests:** Holm correction across the pre-registered comparisons, H1 to H6. Comparison-group letters across all pairs, as on the Turkish page.
- **Cutoffs and selectors:** chosen on one half of the positions and scored on the other, over 300 random splits. We report the mean and the share of splits where the rule beats its baseline.
- **Calibration fits** (isotonic regression) are cross-fitted, so no rule is scored on the positions it was fitted on.
- **Rank correlations (new, A13):** the interval resamples league games and shared positions together, then recomputes points, error rates and the correlation.
- **League placings** are descriptive only. Middle places move between leagues with the dice.

## Outputs and openness

Everything needed to recompute the page goes into `zekiworks/analysis/backgammon/`. Backgammon positions carry no copyright, so this benchmark can be fully open.

| File | Contents |
| --- | --- |
| Runner | jevgammon code, or a link to its repo |
| `prompts/` | The bg-v2 prompt, the variant prompt and the ablation prompts, each with its version |
| `positions.json` | The 2,000 shared positions and the 500 variant positions, with their sha256 hashes |
| `seeds.json` | Dice seeds per league and the option-order seed |
| `decisions.jsonl` | Every decision with the fields logged in the protocol |
| `evaluations.jsonl` | GNUbg's equity for every legal play, including rollouts |
| `results.json` | Every number on the page |
| `reproduce.py` | Recomputes `results.json` from the logs |
| `CONTRIBUTING.md`, `CITATION.cff` | How to report a scoring error or ask for a model; how to cite |

The page follows the Turkish page: question-led headline, what we did, what we found, then the error-rate table across all setups. Then harness, reasoning, confidence, routing, teams, familiarity, validity, cost and speed, league tables, related work, limits and method. It links to the repo folder.

Open question: the title. "Decision models play backgammon" no longer fits, because chat models now play too.

## Budget and run order

About 233,700 model calls in total. The Nackgammon positions and their opening control add 22,400, and the League 1 extension adds 48,000, almost all on our GPUs or cheap decision APIs. The league counts are now corrected: a match against a baseline or the anchor has only one model player. Most calls are cheap or run on our own hardware; the cost driver is the frontier models at high reasoning, known only after the smoke test.

| Run | Model calls, approx. | Basis |
| --- | --- | --- |
| League 1 | 19,300 | 66 matches between models × 2 players, plus 36 matches against a baseline or the anchor × 1, × about 115 decisions (v1 average) |
| League 2 | 16,600 | 66 × 2 + 12 × 1, × 115 |
| League 3 | 7,400 | 28 × 2 + 8 × 1, × 115 |
| Shared positions | 64,000 | 32 model setups × 2,000 |
| Nackgammon positions (new) | 16,000 | 32 setups × 500 |
| Repeats | 32,000 | 32 setups × 200 positions × 5 |
| Harness ablation | 24,000 | 6 setups × 2,000 × 2 extra prompts |
| Opening control (new) | 6,400 | 32 setups × 200 |
| League 1 extension (new) | 48,000 | 12 League 1 model setups × 4,000 |

Known v1 prices per 1,000 decisions, at API list prices: GPT-6 Astra low $36.45, Claude Opus 5.5 low $21.65, Gemini 3.8 Flash low $3.25, Jev $0.16. Astra low makes about 8,600 calls here, so about $315 API-equivalent. It runs on a subscription, so its usage limit matters more than dollars. If high-reasoning setups cost too much, they skip the repeats.

Run order:

1. Finish the runner work below. Smoke test: 50 positions per setup, drawn outside the shared sets. Check probabilities come back, the clock fits, invalid answers are rare, and the cost per decision. Re-check the error spreads behind the bars on these answers.
2. Confirm the bars for H1 to H6, the phase rules and the Nackgammon split. Then freeze and hash roster, prompt, settings, seeds and positions.
3. Shared positions, Nackgammon positions, the opening control, repeats and ablation for every setup, plus the League 1 extension. These do not depend on the leagues.
4. League 1, then League 2. League 3 once Gemini 4 Argon is out.
5. GNUbg scoring, with rollouts for near-ties, those a setup chose first.
6. Analyses, `results.json`, page and repo.

### Runner work before the freeze

The design assumes thirteen things the runner does not do yet. Each one gates the freeze.

- [ ] Chat-model players use the bg-v2 letter prompt. Today they use the retired long prompt with a numbered list and a JSON answer; bg-v2 exists only in the replay tool.
- [ ] Reasoning on, then letter probabilities: build it and test it with each paid provider.
- [ ] New players: random legal play, safest play, GNUbg at weak level.
- [ ] Invalid answers: no re-ask, random legal play as the fallback. Today: up to 3 re-asks, then the first legal play.
- [ ] Network retries: up to 3, not charged to the clock. Today: up to 10, charged.
- [ ] Seeded option order, and a reshuffle of the stored v1 positions.
- [ ] Per-decision logging of option order, letter chosen, provider, quantization and cost.
- [ ] Scorer: rollouts through GNUbg's Python interface. Today: 0-ply and 2-ply only.
- [ ] Phase labels: our rules for opening and holding, on top of GNUbg's classes.
- [ ] Nackgammon position generator: GNUbg self-play from the Nackgammon start.
- [ ] Prompt versions: bg-v2 (the League #8 format, no history) and A2's three prompts become selectable versions with their own identifiers, logged per decision. Today the runner's only prompt is League #13's, with the last 10 moves.
- [ ] Public repo: jevgammon now has its first commit (e8542a9), so each decision can log its harness commit. It still needs a public remote for the Outputs table to link to.
- [ ] Classifier tests: before labelling the position sets, run the phase rules and game-plan tags on textbook positions, such as the concept positions in [transformer-backgammon's board.py](https://github.com/wmhowell18/claude-code/blob/8bcf45d468afc36a3a48b324b1fce89ead7a96cb/transformer-backgammon/src/backgammon/core/board.py). Each must get its textbook label. The tests also pin GNUbg's class numbers (contact, crashed, race, bear-off) against its source.

## Related work

Scoring decisions with an engine is not new, and gg-bench is the closest benchmark in setup. Our new parts are the combination, the harness test and the confidence data. This text also goes on the page.

[gg-bench](https://arxiv.org/abs/2505.07215) (Verma et al., 2025) is the closest benchmark in setup. A language model (o1) wrote 1,000 two-player games, and 126 passed the authors' filters. The games are meant to differ from well-known games, so models are unlikely to have trained on them. The model under test sees the rules, the board, the legal moves and a description of what each move means. It plays 30 games of each game against an agent trained by self-play reinforcement learning. Its score is its average win rate. Non-reasoning models won about 7 to 9.5% of games and reasoning models 31 to 36%. The authors name two main failures: planning over several turns, and applying the written rules to new situations. Their example loss shows a model that did not see what a trade would cost later. We test one part of this directly. Our program computes the immediate result of every legal play (blots left, the opponent's hitting rolls, points made) and adds it to the prompt. In v1, the error rate of the whole field, scored by GNUbg, fell from about 130 in leagues 1 to 6 to about 38 from league 7 on. That was a before-and-after comparison across leagues; A2 repeats it as a controlled test on fixed positions. gg-bench keeps one clear advantage: its games are new, while backgammon strategy is widely published. A12 is our partial answer.

Scoring each decision with an engine is an established method. [Regan and Haworth (2011)](https://ojs.aaai.org/index.php/AAAI/article/view/7951) rated chess players by the engine-judged quality of their moves, not by their results. [Bhardwaj, Jaiswal and Pathak (2026)](https://neurips.cc/virtual/2026/172941) are the closest work in method. They use GNUbg to find the equity of every legal move and rate each agent by its loss per decision, because dice noise buries small skill gaps in win rates. With this method, they needed 8.1 times fewer trials than points per game to separate two agents at the same precision. Their agents are trained networks (value-based, policy-gradient, search-trained, AlphaZero); ours are language models. [LLM Chess](https://arxiv.org/abs/2512.01992) (Kolasani et al., 2025) grades language models' chess moves with Stockfish. [SPIN-Bench](https://arxiv.org/abs/2503.12349) (Yao et al., 2025) compares their moves with a solver's or Stockfish's top moves. None of those games has dice.

[PokerBench](https://arxiv.org/abs/2501.08328) (Zhuang et al., 2025) is the closest benchmark for decisions under chance. It has 11,000 poker spots, each labelled with the action a game-theory solver chooses. It scores whether the model's action, and its bet size, match that label. The best untuned model, GPT-4, matched about 54% exactly. Fine-tuned checkpoints with higher scores won more over 50,000 hands. But the best fine-tuned model lost a 1,000-hand match to GPT-4, which it had beaten on the benchmark. We score the equity a play gives away, not a match, so a near-best play costs almost nothing and a blunder costs a lot. We also keep league games next to the fixed positions and test whether they agree (A13).

[lmgame-Bench](https://arxiv.org/abs/2505.15146) (Hu et al., 2026) also separates harness from model. Its perception, memory and reasoning modules can be switched on and off to probe one skill at a time. In LLM Chess, putting the board and the legal moves straight into the prompt, instead of behind tool calls, raised o4-mini's score against a random opponent from 73% to 97%. Our ablation switches one ingredient: the computed consequences of each play.

[Kadavath et al. (2022)](https://arxiv.org/abs/2207.05221) found that larger models are well calibrated on multiple-choice questions when the options appear as letters. We read the same answer-letter probabilities and test whether they show when a play is right (A5). [FrugalGPT](https://arxiv.org/abs/2305.05176) (Chen et al., 2024) uses a cascade of models. It matched the best single model at up to 98% lower cost on language tasks. We test a two-model cascade on decisions under risk, where an engine scores every answer (A6).

To our knowledge, no earlier benchmark combines all of these parts: language models, decisions under dice risk, an engine score for every decision, a harness ablation and each model's probability for every option.

Open question: Bhardwaj et al. is a NeurIPS 2026 listing with anonymous code. Confirm the final title and authors before the page cites it.

## Limits and what we will not claim

The benchmark measures decisions with computed numbers in front of the model. It does not measure backgammon strength in general.

- **Strategy text is in training data.** Rules, opening tables and strategy articles are online; models were not trained to play, but the principles are familiar. Backgammon is not an unfamiliar task. A12 tests how much this helps, but only near the opening: Nackgammon changes the start, and games drift back into ordinary middlegames.
- **The prompt steers.** The strategy text and the question say what a good move looks like. Results measure how well models follow that guidance with the numbers, as much as how well they play.
- **Scoring is not perfect.** 2-ply evaluation with rollouts only for close calls; cubeless money equity; match score ignored. GNUbg's network learned standard play, so its scores for early Nackgammon positions are likely less accurate. A12 therefore compares setups with each other, not with an absolute reference.
- **Checker plays only (new).** Our error rate leaves out cube decisions, which human ratings include. The human scale is a rough guide, not a direct comparison.
- **Providers vary.** A hosted model can change without notice, and providers differ in quantization. We pin and log them; we cannot control them.
- **Group splitting differs by model** in league games with more than 25 legal plays. The shared positions avoid it.

We will not claim:

- that any model plays strong backgammon. GNUbg plays far better than every model;
- that these results carry over to finance on their own. They show which setup works; a finance benchmark still has to test it;
- that a middle place in a league table means one model is better than its neighbour;
- that engine scoring of decisions is our idea. It follows Regan and Haworth (2011) and Bhardwaj et al. (2026).
