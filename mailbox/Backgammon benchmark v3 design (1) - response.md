# Backgammon benchmark v3: response to the revised design

Oct 13, 2026 · reply to "Backgammon benchmark v3 design (1)"

The revision takes in every point from the first reply correctly. Two of its new claims need changing (A12's reference, and the smoke data for DeepSeek). Two items are missing from the runner list, and one gap matters for H5.

## Checked and correct

- **Call counts:** League 1 has 12 model setups and 3 non-model players: 66 model-vs-model matches and 36 against a baseline or the anchor, so 19,320 calls. League 2 comes to 16,560 and League 3 to 7,360; the total is 179,300. The extra standard opening positions would add 6,400 (32 setups × 200). GPT-6 Astra low makes about 8,420 calls, about $307 at $36.45 per 1,000.
- **Human scale:** the "30 or more distracted" band matches eXtreme Gammon's documentation as reproduced on [manualzz](https://manualzz.com/doc/23492071/gamesite-2000-version-2-extreme-gammon-documentation). It names the band "Distracted" and excludes forced or obvious decisions from PR, as the design does. The live page gives the scale only up to beginner; I will add the last band.
- **Option-order figure (0.38)** and the description of v1's invalid-answer rule are right.
- **Rollout ordering:** sound. With 32 setups, few near-ties will lack a chooser, as the design says.

## Change these

### A12: weak GNUbg is not a knowledge-free reference

The design says GNUbg at weak level "recalls nothing", so its change under Nackgammon is the reference for the variant's difficulty. That does not hold. GNUbg is a neural network trained by self-play on standard backgammon, so it carries standard opening knowledge in its weights. Its weak levels add noise to the same evaluation that scores every move. Its error rate under Nackgammon therefore mostly measures how that noise interacts with the scorer, not how hard the variant is for a player without book knowledge.

Proposal: keep weak GNUbg as a sanity anchor, not as the reference. Read A12 as each setup's change in error rate compared with the other setups' changes, and add the 200 standard opening positions without the table, the open question in Shared positions. That pair separates "the table was removed" from "the position is unfamiliar", which the anchor cannot.

A related limit: GNUbg also scores Nackgammon's early positions with a net trained on standard play. Its evaluation is likely less accurate there than in standard openings, and the rollouts matter more. That belongs under "Scoring is not perfect".

### DeepSeek's 209 stored answers are not smoke data for League 2

The design uses DeepSeek V4.1 Flash's 209 thinking answers as its smoke data. They came from our own server, in v1's option order, at the lowest reasoning effort. League 2 runs DeepSeek through a pinned paid provider. Its speed, its reasoning settings and whether it returns letter probabilities all depend on that provider. The 209 answers show the clock problem exists, but the smoke test still has to run against the provider.

## Add to the runner work list

- **The current prompt is not bg-v2.** League #13 added the last 10 moves to the prompt, and that is still the runner's only prompt. bg-v2 (the League #8 format, no history) and A2's three prompts (notation only, + consequences, + consequences and history) need to be selectable versions with their own identifiers, logged per decision.
- **The runner is not under version control.** The jevgammon repository has no commits yet, so "harness commit" cannot be logged and the Outputs table has nothing to link to. Commit it before the freeze.

## H5 can mostly be tested only in League 1

A7's first two selectors (highest probability, calibrated probability) need probabilities. In Leagues 2 and 3, most setups have none:

- **Gemini 3.8 Flash:** its API refuses token probabilities ("Logprobs is not enabled for this model").
- **GPT-6 Astra and Claude Opus 5.5:** their subscriptions return none.
- **Claude Sonnet, GPT-6.1 Sol and Gemini 4 Argon:** almost certainly the same, though not checked.

Only the open-weight setups might have probabilities, depending on the provider. So in Leagues 2 and 3, A7 can use only agreement count and game phase. The design should say this, and decide whether H5 is judged on League 1 alone or per league with the selectors each league allows.
