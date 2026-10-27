# Backgammon: inter-league ladder and Hype Cup

**Core question: can a model tell when a risk is worth taking?**

This file says *what* to build. You decide *how*. Push back in mailbox/ if any rule conflicts with the runner.

This file replaces all earlier Champions Cup plans: the 9-team format, the group stage, point matches and the match clock.


## Timing

- Start the ladder only after every league has finished.
- Do not change the runner while a league is playing.

## Common rules (ladder and Cup)

- **No repeats.** Two models play each other at most once, across leagues, ladder and Cup. Store every result by pairing. Reuse a stored result instead of playing the match again.
- **Same match format.** Ladder and Cup matches use the league match rules: the same format and the same dice method.
- **Programs never move.** GNU Backgammon (GNUbg) setups never move between leagues and never enter the Cup. When a rule picks a program, take the next model in the table.
- **League ranking** stays as it is now: points, then games, then the lower error rate. *(Superseded for the Cup 2026-10-27 by Can: the Cup uses the original-league tables and a tiebreak still to be decided; see the amendment in Part 2.)*

## Part 1: inter-league ladder

The leagues, from bottom to top: League 1 (decision models), League 2 (workhorses), League 3 (frontier models).

**Each round:**

1. Find the movers at both boundaries:
   - The League 1 winner swaps with the League 2 last.
   - The League 2 winner swaps with the League 3 last.
   - Both swaps happen at the same time.
2. Each mover plays every model in its new league that it has not played yet. League 2 can get two newcomers in one round, and they play each other too.
3. Remove a leaver's matches from the table of the league it left. Each table is then a full round robin of its current members.
4. Recompute all tables.

**Amendment, 2026-10-26 (Can): no lock; the ladder ends when a round needs no new matches.** This replaces the lock rule and the stop rule below, which are kept for the record, marked superseded.

- **No lock.** The lock rule and its exception are dropped. Models move up and down by the normal rules every round, with no limit on repeats.
- **End.** The ladder ends when a round would need no new matches: every pairing its moves create is already stored.
- **Final swap** (second decision, 2026-10-26, Can; replaces the final placement below): when the ladder ends, that last round's swap is made one final time, and every model stays where it puts it. Reason: models added later are like the next season, and the ladder continues from there. Logged as moves with the reason "final swap (ladder ended)". Programs never move (unchanged).
- *Final placement (superseded 2026-10-26 by Can, by the final swap above):* At the end, a model whose position is oscillating (the end round would move it again) is placed in whichever of the two leagues it alternates between is closer to its original league (its league before any ladder move). A model that is not oscillating stays where it is. Programs never move (unchanged). Placements are logged as moves with the reason "final placement".

**Lock rule** (superseded 2026-10-26 by Can, see the amendment above):

- A model that is relegated from the same league a second time stays in the lower league.
- Exception: if the upper league now contains a model that the locked model has not played, the locked model moves up and plays the missing matches. Then the normal rules apply again.
- If a league's winner is locked and has played every model in the upper league, nobody is promoted at that boundary in that round. Do not pass the promotion to the next model.

**Stop** (superseded 2026-10-26 by Can, see the amendment above): when a round has no moves, the leagues are in a steady state.

**Budget guard:**

- Before each round, write the list of new pairings and their estimated cost to mailbox/.
- Stop if the ladder's total cost goes past the budget. If no budget is set yet, ask in mailbox/ before round 1.

**Log every move:** round, model, from league, to league, and reason (promoted, relegated, locked, or frozen boundary). Since the amendments of 2026-10-26: promoted, relegated, or final swap (ladder ended).

**Error-rate flag:** flag each swap where the promoted model has a worse error rate than the model it replaced.

## Part 2: Hype Cup

One Hype Cup runs for each steady state. A new model entering a league starts a new ladder, which leads to a new steady state and a new Cup.

**Amendment, 2026-10-27 (Can): the Cup roster comes from the original-league tables.** Reason and figures: `mailbox/Original-league tables - what Can found 2026-10-27.md`. This replaces "the top 2 models from each league" meaning the final ladder tables; the text below is kept, read with this amendment.

- **Original-league tables.** Each setup is counted in its original league: the league it was in before any ladder move. GNUbg weak, the anchor, is in all three leagues. Only matches between setups of the same original league count: 3 points for a win, 1 for a draw, 0 for a loss.
- **Cup roster.** "League" in Teams and Seeds below means these original-league tables, not the final ladder tables.
- **The ladder's final placement stays as its own result.** The ladder tables and the final swap are unchanged; they are not used for the Cup.
- **Late entries.** Pairings missing because a setup joined after others had left its league are played (same rules and format as the leagues, stored as normal valid matches), so every original league is a complete round robin before the roster is built.
- **Tiebreak: pending Can's decision.** Under discussion: points, then the head-to-head result, then the lower error rate. Games won is unsuitable, because match length varies (2–8 games: a match ends after the round in which someone reaches 5 points).

**Teams (8):**

- The top 2 models from each league. *(Superseded in part 2026-10-27 by Can: "each league" is now each original-league table, see the amendment above.)*
- The two 3rd-placed models with the lowest error rates. Points do not compare across leagues of different sizes, so error rate picks these two.

**Seeds:**

1. League 3 #1
2. League 3 #2
3. League 2 #1
4. League 2 #2
5. League 1 #1
6. League 1 #2
7. The better 3rd place (lower error rate)
8. The other 3rd place

**Quarter-final draw:**

- Seeds 1, 2, 3 and 4 pick in that order. Each takes the lowest-seeded remaining team from a *different* league.
- No quarter-final pairs two models from the same league. If the draw would end with one, swap opponents with the previous pick.

**Bracket:**

- Semi-final A: the winners of the seed-1 and seed-4 quarter-finals.
- Semi-final B: the winners of the seed-2 and seed-3 quarter-finals.
- Final: the two semi-final winners. The final's winner is the Hype Cup champion.

**Stored results:** if a Cup pairing was already played (in a league, the ladder or an earlier Cup), that result stands and no new match is played. The page shows where the match was played and links to it.

## Part 3: website

- **Ladder section:** the current lineup of each league, every round's moves, locks, frozen boundaries, the error-rate flags, and a "steady state" marker.
- **Hype Cup page:** the bracket, every result, a mark on each stored result with a link to the original match, and the champion.
- **Champions strip (home page):** the Hype Cup champion is the cross-league champion.
- **Honesty line on every Cup page:** "The Cup is an event. The error rate is the ranking."
- GNUbg stays labelled as a program or reference everywhere, never as a champion.

**Rules explanation on the page.** Add a short, plain explanation of the ladder and the Cup, a few lines each, on the ladder section and the Cup page. Suggested text (adjust it if needed):

> **How the leagues connect.** Time is frozen here, so there are no new seasons. Instead, the leagues trade models until nothing changes. Each league's best model moves up one league, and its worst model moves down. Each model that moves plays every model in its new league once. Two models never play each other twice, because we already know that result. A model that drops out of the same league twice stays in the lower league, unless a model it has not played joins the upper league. Reference programs, like GNU Backgammon, stay in place. When no model moves, the leagues are settled.
>
> *(Superseded 2026-10-26 by Can: the "drops out twice" and "when no model moves" sentences. New text for them: "Models can move back and forth. The ladder ends when a round would need no new matches: that last swap is made once more, and every model stays where it lands. Models added later start the next season, and the ladder goes on from there." An earlier replacement of the same day, "A model still going back and forth then stays in whichever of its two leagues is closer to the league it started in.", is superseded too.)*
>
> **The Hype Cup.** When the leagues settle, 8 models play a knockout cup: the top 2 of each league and the two best 3rd-placed models. Points do not compare across leagues of different sizes, so the 3rd places are picked by lowest error rate. In the quarter-finals, strong models meet weak models, never two models from the same league. If two models already played each other, the stored result counts. This is a benchmark, not a game: a replay would only change the dice.
>
> The Cup is an event. The error rate is the ranking.

## Reply in mailbox/

- Confirm the plan, or say what conflicts with the runner.
- How results are stored by pairing, and how the ladder reuses them.
- An estimated cost for ladder round 1 and for the Cup.
- The budget question, if no budget is set yet.
