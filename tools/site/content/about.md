<!-- About page text: Ümit, bus #2939 (backgammon_rules_page.md), with the [check] lines fixed and the two flagged
     rank sentences (mailbox/ct-brief/CHECK-LINES.md). Sections in order; the 'Leaderboard box' section is the home
     page's 'How the scores work' (pages.about_sections). -->

## 1. Backgammon in one page

**The goal.** Two players race their 15 checkers around the board and off it. The first player to bear off all 15 checkers wins.

**The board.** The board has 24 narrow triangles, called **points**. Each player moves in the opposite direction. Each player's last six points are their **home board**.

**Moving.** A player rolls two dice and moves checkers by those two numbers. One checker can take both numbers, or two checkers can take one each. A roll of doubles (for example 4-4) is played four times. A checker cannot land on a point that holds two or more of the opponent's checkers.

**Hitting.** A single checker alone on a point is a **blot**. If the opponent lands on it, the blot is **hit**: it goes to the middle of the board (the **bar**). It must come back in through the opponent's home board before any other checker can move. Being hit costs a lot of time in the race.

**Bearing off.** When all 15 of a player's checkers are in their home board, that player can start taking them off the board.

**Gammons.** If the loser has borne off no checkers, the winner wins a **gammon**, worth 2 points. If the loser also still has a checker on the bar or in the winner's home board, it is a **backgammon**, worth 3 points.

**Why this is a test of risk.** Almost every turn asks the same question. A safe play leaves no blot. A bolder play leaves a blot but builds a better position. The dice decide whether the risk pays off this time. A strong player takes the risk when it is worth it on average, not only when it feels safe.

**Nackgammon.** Nackgammon is backgammon with a different starting position. Each player moves one checker from the 13-point and one from the 6-point to their opponent's side, so each side starts with four back checkers instead of two. We use it to test whether a model still plays well when the opening positions are new.

## 2. How the benchmark works

- **Leagues of full games.** Each model setup plays full games against every other setup in its league. There are three leagues, and they are never merged.
- **One decision, one request.** Every move is sent as its own request. A model sees the match score, but not the moves of earlier turns or earlier games.
- **What the model sees.** Each request shows the score, the board with pip counts, the race, the dice and every legal play. Next to each play the program lists: checkers hit, points made, blots left and how many of the opponent's 36 rolls hit them, points held, longest prime and pip counts.
- **Two kinds of model.** Decision models return a probability for every legal play. Chat models choose one play.
- **A program judges, not a model.** GNU Backgammon 1.08 scores every legal play in every position at 2-ply. No language model judges any move.
- **Settings.** Each setup is one model at one reasoning setting (off, low, medium, high). We record the time and the tokens of every decision, and its cost where a price is known.
- **Reference programs.** Three programs are shown as yardsticks and are never ranked: GNUbg weak (a weak setting of the engine, played in every league), Safest and Random. In League 1, Safest picks the play that leaves the fewest hitting rolls, then the fewest blots, then the biggest pip lead. In Leagues 2 and 3, Safest and Random are computed, not played: Safest is the engine's best of the safest plays, Random the average of all legal plays.
- **Late entries.** A setup added after a league finished plays that league's original field. It is ranked on the risk leaderboard, but it does not change league match-points standings, Cups, or other setups' results.
- **Everything is public.** Every position, every legal play, the engine's value for each play and every model's choice.

## 3. How the scores work

- **Risk call.** A position is a risk call when its legal plays leave different numbers of hitting rolls. The engine compares its best play with the best safe play: if the best play is at least 0.001 better, **risk pays**; otherwise **safety pays**.
- **Risks found.** The share of risk-pays positions where the model chose a worthwhile risky play: one at least 0.001 better than the best safe play. A risky play that is not that good counts as a wrong risk, not a risk found.
- **Safe right.** The share of safety-pays positions where the model played safe.
- **Risk judgement.** The average of risks found and safe right, from 0 to 100. A model that always plays safe scores 50. A model that gets every call right scores 100.
- **Error rate.** How much a model's moves give away, as judged by the engine: the PR scale that human players use. Lower is better. A move that matches the engine's best play costs nothing.
- **Uncertainty.** Each score has a 95% interval. Intervals resample whole games, not single moves, because moves inside one game are not independent. Ranks show observed scores; small gaps need not be meaningful.

## 4. Leaderboard rules

- **One row per model.** The row uses a setting fixed by rule, not the best score: the model's highest reasoning setting. A model with one setup uses that setup.
- **Versions.** Different version names (Jev 1.13.0 and 1.14.0) are separate rows. A dated checkpoint of the same model (DeepSeek V4.1 Flash 1017) is the same model, and its row shows the original.
- **Late entries count on the leaderboard,** with a "late entry" tag, because they play the same league field.
- **Order.** Rows are sorted by risk judgement. The rank is a sort order, not a verdict. Ranks show observed scores; small gaps need not be meaningful.
- **Tap a row** to see both halves of its score, the raw counts, its error rate, its record and a link to every decision it made.

## Leaderboard box

1. Models play full games of backgammon. GNU Backgammon scores every move.
2. Risk judgement: did the model find a worthwhile risk when risk paid, and play safe when safe was right? 50 = always plays safe, 100 = every call right.
3. Error rate: how much a move gives away, judged by the engine (lower is better).
4. Everything is public: every position, every legal play, the engine's value for each.
5. Leagues played different positions, so close scores across leagues are not a clear ranking.
