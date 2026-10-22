# Backgammon benchmark site: plan

I suggest presenting this as a benchmark of "which model makes better decisions under which conditions?", not as a "which model won at backgammon?" site. The leagues are one part of it. The main story is decision quality, the return on reasoning, risk, confidence, time and cost.

Can's v3 design has 12 main analyses and an optional cube test. Below I list all of them, the existing method checks, and the measurements I suggest adding for the question "when does high reasoning hurt?". This is a scope list. It does not mean that all of them have results. (raw.githubusercontent.com)

## Website: same design, different questions

Keep the Turkish benchmark's question-led opening, short findings summary, filters, Table/Charts view and detail pages. That structure suits this work. (zekiworks.github.io)

Suggested title:

How well do models decide under risk?

Subtitle:

We compare move quality, reasoning, confidence and cost using engine-scored backgammon decisions.

Suggested home page order:

- Short findings: Who has the lowest move error? Where does high reasoning help? Does choosing by confidence work? Is there a cheaper option that keeps the quality?
- Main comparison table: model and setting, move error, uncertainty interval, blunder rate, time and cost.
- Reasoning section: the same model at low vs high, or off vs on.
- Risk and confidence section: the bad decisions that average performance hides, and whether the model notices them.
- Game phases: where each model is strong and where it is weak.
- Routing and teams: which decisions can we leave to a small model?
- Leagues: winners and match results, separate from the main quality ranking.
- Method / Data: experimental conditions, limits, versions and recomputation.

Build the main table on shared positions. Do not turn the scores of different leagues into one overall ranking. The design also keeps in-league competition apart from the shared-position comparison. (raw.githubusercontent.com)

The Turkish benchmark's detail pages map like this:

- Every decision: board, dice, options, the information the model saw, its choice and the engine's evaluation.
- Where models disagree: positions where models pick different plays.
- Phases: game phases instead of topics.
- Compare: two models, or one model at two reasoning settings, side by side.

## Full analysis list of the current scope

### A1. Decision quality
- Expected value lost per move: equity loss.
- Its scaled summary: PR / error rate. Lower is better.
- Share of decisions where the model picks the engine's best play.
- Blunder rate: the share of big errors.
- Uncertainty intervals for quality differences.

The site must show not only "did it choose right?" but also how much the model lost when it chose wrong. The current report already publishes these basic measurements. (zekiworks.github.io)

### A2. Effect of the information given to the model
Compare three input formats: play notation only, plays with their computed consequences, and plays with the recent move history. This separates the model's own skill from the contribution of the input we prepare for it. (raw.githubusercontent.com)

### A3. Return on more reasoning
Paired error difference between low and high, or off and on; gain per game phase; extra cost and time. (raw.githubusercontent.com)

### A4. In which positions is a model good?
- Phases: opening, contact, holding game, race, bear-off.
- Strategy tags: blitz, back game, holding, priming, low anchor, other.
- Also break down by number of options and by the equity gap between the two best plays.

This lets us say "good at this kind of decision" instead of "good on average". (raw.githubusercontent.com)

### A5. How reliable is confidence?
AUROC, ECE, Brier score, the risk–coverage curve by confidence, and option-position bias. (raw.githubusercontent.com)

One important limit: for a model that returns only a choice, the recorded value 1 is not real 100% confidence. Show confidence metrics as N/A for setups that give no probabilities. (raw.githubusercontent.com)

### A6. Routing from a small model to a large one
When a cheap model hands decisions to a strong one: quality, total cost, acceptance rate and the routing threshold. (raw.githubusercontent.com)

### A7. Can a team beat a single model?
The current team code has these rules:
- Pick the answer with the highest raw confidence.
- Pick the answer with the highest calibrated confidence.
- Pick the answer with the lowest expected loss.
- Combine the models' option probabilities.
- Compare with the theoretical upper bound that always knows the best answer any team member gave.

The v3 plan also includes selection by agreement and by game phase. Do not present the theoretical upper bound as the result of a working system. (raw.githubusercontent.com)

### A8. Repeatability
How often the model changes its play when the same position is asked again. (raw.githubusercontent.com)

### A9. Time and cost
- Time per decision and cost per 1,000 decisions.
- Median and P90 latency next to the mean.
- Quality vs cost comparison.
- Request time kept separate from retry/wait time.

The current v3 report has the mean request time and the costs that can be priced. Median and P90 are within the design's scope. Do not mix the hardware cost of local runs with estimates computed from API prices. (zekiworks.github.io)

### A10. Real game results and in-game risk
League points, wins/draws/losses, games won and lost, gammon results, the share of decisions where the model picks the safest play, and the hitting rolls left to the opponent. (raw.githubusercontent.com)

### A11. Cube decisions (optional)
Offering and accepting the doubling cube, and the equity lost on those decisions. A separate study, not part of the main league. (raw.githubusercontent.com)

### A12. Contribution of known opening knowledge
With vs without the opening table; a Nackgammon comparison. A familiarity test alone does not prove memorization.

### A13. Does the benchmark score predict real play?
Agreement between the shared-position ranking and the league ranking; the link between fixed-test error and move error in matches. (raw.githubusercontent.com)

## Measurements I suggest adding for "when does high reasoning hurt?"

These are proposals for extra analyses, not finished results.

**Decisions that high fixes and breaks**
How many of low's bad decisions does high fix? How many of low's good decisions does it break? Show not only the counts but also the size of the loss in both directions. Many small fixes must not hide a few heavy breakages.

**Risk in the worst decisions**
Next to the mean error:
- The P95 point of the error distribution.
- The mean loss of the worst 5% of decisions.
- The share of decisions over a big-error threshold set in advance.

**Confident and badly wrong**
How often is the model both very confident and seriously wrong? If high raises confidence without raising quality, show that separately.

**Risk of going over a time budget**
The share of decisions over a set time limit. The current v3 leagues had no clock, so the absence of losses on time in the leagues does not measure this risk. (zekiworks.github.io)

**High only when needed**
Compare three policies:
- Always low.
- Always high.
- Switch to high under set conditions.

Build the switching rule on separate data and test it on positions it has not seen. If high is called after low, count the time and cost of both calls.

## Result labels for the site

- High helps: a supported improvement in decision quality.
- No clear benefit: no benefit was shown. Do not say "they are the same".
- High hurts: a supported worsening in a paired comparison.
- Depends on the position: the effect changes in certain phases or decision types.
- Not measured: this comparison was not done.

Also keep two kinds of downside apart:

- Decision harm: worse plays.
- Economic burden: more time or cost with no shown benefit.

Do not squeeze these into one "high is bad" label.

## Work that must not get lost in the Method section

**Dice-sharing experiment:** it examined how different ways of sharing dice between players affect the score distribution, the agreement of rankings, and the chance that the stronger player finishes on top. This is a method experiment run with GNUbg players. Do not present it as an LLM result. (raw.githubusercontent.com)

**Reference-player check:** it examined the weak GNUbg player's behavior on x86 vs ARM, the reproduction of recorded decisions, gammon rates and the sensitivity of the scoring. Publish this as a method finding too, separate from model performance. (raw.githubusercontent.com)

On top of these, every view must show the sample size, invalid answers, missing measurements, failed requests and cost coverage. The runner can turn an invalid answer into a random legal play, so never treat that play as the model's valid choice. (raw.githubusercontent.com)

## The most important publishing distinction

Every section has a clear status:

Published · Earlier version · Analysis pending · Not measured · N/A

What I verified in this review: the v3 publication of league results, move quality and time/cost; the harness and team findings of the earlier version; and v3's wider analysis plan. I did not verify finished results for all the shared-position, routing, repeatability and familiarity analyses. Data that is ready, or analysis code that runs, does not mean the results are finished. (zekiworks.github.io)

In short: keep the Turkish benchmark's look, but answer "which model and which reasoning setting for which decision?" instead of naming one "best model". I made no changes to the site and started no new experiments.
