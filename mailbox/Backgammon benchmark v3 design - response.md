# Backgammon benchmark v3: response to the design

Oct 13, 2026 · reply to "Backgammon benchmark v3 design"

The design holds up. Two of its open questions can be answered from v1 data and the installed tools, and both answers change the protocol. One finding affects the live page.

## Answers to open questions

### How the plays are ordered in the bg-v2 prompt

The order is not an evaluation, but it is not neutral either. The runner lists plays in the order its move generator finds them: the dice in the order rolled, then reversed (doubles in one pass), and the checkers from the bar, then from point 24 down to point 1. When two plays reach the same position, the first one found is kept. Plays that move the rearmost checkers therefore come first, and that order tracks quality. On the 1,000 v1 shared positions, scored by GNUbg:

| | Best play's position in the list |
| --- | --- |
| Average (0 = first, 1 = last) | 0.38; 0.50 would mean no order effect |
| Positions with 5+ plays: best play in the first fifth | 256 |
| Best play in the middle | 352 |
| Best play in the last fifth | 71 |

Consequences:

- **The seeded random order is necessary, not optional.** In v1, a model that leans toward early letters scores better than it deserves. GLM-5.3-Flash picked A or B 46% of the time.
- **The stored v1 positions keep their options in generation order**, so reusing them needs a reshuffle.
- **v1-to-v3 differences on the v1 set will include the order change.** The design should say so where it promises comparability with v1.

### Does GNUbg 1.08 score Nackgammon or Hypergammon?

Tested through GNUbg's Python interface:

- **Nackgammon works.** Its starting position evaluates normally: equity +0.147 for the side to move, against +0.068 for the standard start.
- **Hypergammon does not, as installed.** It returns an invalid result: a win chance of 0 and equity of exactly −1. GNUbg most likely needs its separate Hypergammon endgame databases. Only the standard bear-off database (`gnubg_os0.bd`) is installed. The runner's move generator and win check also assume 15 checkers.

Consequences for A12:

- **In practice the variant is Nackgammon.**
- **Nackgammon changes only the starting position, not the rules.** "Unfamiliar rules" overstates it; it is an unfamiliar opening structure. Self-play games drift back into ordinary middlegames, so the novelty sits mostly early in the game. Proposal: draw the 500 variant positions mostly from the early phase.
- **Drop the opening table from the variant prompt.** Its plays are wrong for Nackgammon. This settles part of the open question about the strategy text; the strategy principles can stay.

## The live page uses the wrong human scale

Change #1 is right, and the published page has the old scale. It says "below 3.5 world class … above 10 casual", calls GPT-6 Astra "near casual human play", and says every model plays "far below a casual human". On the design's scale:

| Player | Checker-play PR | Band |
| --- | --- | --- |
| GPT-6 Astra (low) | 11.2 | advanced |
| Claude Opus 5.5 (low) | 17.3 | intermediate |
| Gemini 3.8 Flash (low) | 18.3 | casual |
| Gemma 4 31B | 23.5 | beginner |
| Every decision model | 31.8–59.9 | above the scale |

The design's scale stops at 30, and most decision models are above it. It should name the band above 30.

Fixed on the live page on Oct 13 (analysis commit 3fd18c7): the scale above, "checker plays only", and the three sentences that used the old bands.

The other half of change #1 already holds for the v1 numbers: forced moves were never sent to a model and never scored.

## What the runner does not do yet

The design assumes several things the runner does not do today:

- **Prompt for chat models:** the runner's LLM players still use the retired long prompt, with a numbered list and a JSON answer. The bg-v2 letter prompt exists only in the replay tool.
- **Reasoning on, then letter probabilities:** this is not built or tested. Locally, DeepSeek V4.1 Flash with thinking and a JSON schema returned a letter but no letter probabilities. With paid providers it depends on whether they continue a prefilled answer with token probabilities. Add this to the provider question.
- **New players:** there is no random-play baseline, safest-play baseline or GNUbg player yet.
- **Invalid answers and retries:** today the runner re-asks up to 3 times and falls back to the first legal play, not a random one. Network retries go up to 10 and are charged to the clock. Both differ from the protocol.
- **Logging:** option order, the letter chosen, provider, quantization and cost are not yet recorded per decision.
- **Rollouts:** the scorer does 0-ply and 2-ply evaluation only. Rollouts through GNUbg's Python interface are untested.
- **Game phases:** GNUbg classifies positions as contact, race, crashed or bear-off. "Opening" and "holding" need our own definitions for the new set and for A3 and A4.

## Smaller points

- **Clock:** with thinking on, DeepSeek V4.1 Flash took about 2 minutes per decision on our GPUs at its lowest effort. That was about 4,800 reasoning tokens, with 8 requests in flight. A provider may be faster, but expect the 30-second smoke rule to trigger for some reasoning-on setups. The 209 answers already stored can serve as its smoke data.
- **Rollout rule:** skipping rollouts nobody chose leaves comparisons between setups unchanged. It still moves absolute error rates, and those are what the human scale compares against.
- **H6:** a Spearman test on 9 players has wide intervals. Consider also reporting it pooled across the three leagues.
- **Budget:** the league call counts assume two model players per match. Matches against the baselines and the GNUbg anchor have one, so the total is slightly overstated.
- **Missing specifics:**
  - **Decider v1.1:** v1 used Perplexity's hosted v1, not v1.1. Check that v1.1 is hosted before relying on it to free our GPUs.
  - **A2:** it names DeepSeek V4.1 Flash but not which setup, off or on.
  - **League 3:** a model plays itself across settings (Astra low vs high). State that this is intended.
