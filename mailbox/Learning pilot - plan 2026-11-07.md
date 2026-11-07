# Learning pilot - plan 2026-11-07

This is the pre-registration of the learning pilot: Ümit's brief (bus #2372), merged with the v5 design's A17, "learning track" (Ümit, bus #2429; A17 overrides the earlier briefs where they differ). It includes Zeki's rules (#2378, #2383, #2432) and Ümit's addenda (#2379, #2384, #2385, #2387).

This file is the single source for the site page "Learning from experience (preliminary, running)". It was committed and pushed before any model call of the pilot. The page went live with it before the first model call.

**Results will be published whichever way they go, including no lift.**

## 1. Question

Does Gemma 4 31B (off) play better backgammon after seeing its own earlier games? Does the form of that experience matter: full game records with GNU Backgammon's evaluation of every decision, lessons the model writes for itself, or records cut to the size of those lessons?

This is measured in two places: in games against GNU Backgammon's Beginner level, and on a fixed 200-position evaluation set.

## 2. Model and settings

- **Model:** Gemma 4 31B with reasoning off, set up exactly as in League 2: same weights, precision, prompt and request settings. Only the server address differs.
- **Server:** our own vLLM server on a DGX Spark (GB10). It was checked against League 2's server before any call. The check was read-only: the model list, the container's arguments and the checkpoint files.
  - The image is the same: vLLM 0.30.0.
  - The checkpoint is the same: `gemma-4-31B-it`, bf16. Both weight-file sizes match, and so do the checksums of the config, the weight index, the chat template, the generation config and the tokenizer config.
  - The precision is the same: bf16 weights quantized to fp8 at load, and an fp8 KV cache.
  - Context length 32,768, generation config from the checkpoint, Gemma 4 reasoning parser, up to 20 log-probabilities.
  - It differs from League 2 in four ways: at most 8 sequences at once (League 2: 16 or 24), a different memory share, a tool-call parser that is enabled, and the GB10 hardware (League 2 also ran some periods on a GB10).
- **Request (as in League 2):**
  - prompt version `bg-v2` and League 2's option-order seed;
  - reasoning off (`enable_thinking = false`) and temperature 1.0;
  - the answer is read by prefilling `Answer:`, generating 1 token and taking the top 20 log-probabilities; the play is the most probable option letter;
  - positions with more than 26 legal plays are asked in groups, as in the league;
  - no clock, and a turn limit of 300.
- **Where the context goes:** after the league's system prompt and a blank line, between the lines `=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===` and `=== END OF NOTES ===`. The user prompt is unchanged. With no context, the request is exactly the league's.
- **Context limit:** the context may use 26,879 tokens, counted with Gemma's tokenizer. That is 32,768, minus the largest evaluation prompt measured (4,389 tokens), minus a 1,500-token margin. When a context would exceed it, the oldest games are dropped first, and every drop is logged.
- **Load:** each arm has at most one model request in flight, so the server never has more than 4. Games are played one after another, the evaluation asks one position at a time, and the lesson call runs between games. The one exception is the shared evaluation before game 1: it runs alone, with 4 requests in flight.
- **Cost:** $0, because the model runs locally. Time is recorded for every evaluation, game decision and lesson call.

## 3. Opponent

The opponent is GNU Backgammon 1.08 at its Beginner level (0-ply, deterministic noise 0.060, cubeless), x86-64 build. It is the runner's `gnubg-weak`, the fixed anchor of every league; the site's Method section "The anchor" describes it. This is A17's "GNUbg Beginner anchor".

## 4. Arms

There are exactly four arms. Every series starts with an empty context, and nothing carries over from one series to the next.

| Arm | Context during the games and evaluations of a series |
| --- | --- |
| **control** | None (no history). |
| **records** | Full records of all earlier games of this series, with GNU Backgammon's evaluation of each decision. |
| **lessons** | Every lesson the model has written so far in this series, and nothing else. |
| **budget** | Budget-matched records: the most recent records of this series that fit within the lessons arm's context size at the same point of the same series. |

### Records (records and budget arms)

- **Board:** given in the player's own point numbering, as in the game prompt. Example: `your checkers 6:5 8:3 13:5 24:2 (bar 0, off 0); opponent's checkers 1:2 12:5 17:3 19:5 (bar 0, off 0)`.
- **Game header:** one per game, giving the result, e.g. `Game k (you won 1 point(s), single):`.
- **Decision line:** one per decision. Each line gives:
  - turn and dice;
  - the board;
  - the play made and GNU Backgammon's best play;
  - the equity lost, to 3 decimals;
  - GNU Backgammon's default mark: best play; small error (below 0.04); doubtful (from 0.04); bad (from 0.08); very bad (from 0.16);
  - the risk call, using the site's definition with margin 0.001: missed risk, needless risk, wrong risk, right risk call, right safety call, or no risk trade-off.
- **Evaluations** are GNU Backgammon 1.08 at 2-ply, scored as on the site, with the same scorer settings, rules, play descriptions and hitting rolls.
- **Leakage:** decisions whose board is an evaluation position are left out (section 8).

### Lessons arm

After each game there is exactly ONE lesson call.

- **Input:** the record of that game, with GNU Backgammon's evaluation of each decision, in the format above. The call sees nothing else: no earlier lessons and no earlier games.
- **Settings:** reasoning off, temperature 1.0, at most 400 output tokens.
- **Output:** at most 5 lessons and at most 150 words in total.
- **Over-long output:** if the model writes more, the harness keeps the first 5 lines that start with `- ` and then the first 150 words. Each cut is logged and counted.
- **Context:** the lessons arm's context is every lesson kept so far in the series, oldest first, each block labelled "After game k:".

### Budget arm

- After game g of series s, the budget arm's context is no longer, in Gemma tokens, than the lessons arm's context after game g of series s.
- That makes the budget arm's series s start only after the lessons arm's series s has finished.
- The unit is the decision line. The newest lines are taken first, while the whole context, including the delimiters and headers, still fits. They are then shown in game order under their game headers.

### Lesson prompt

The lesson prompt is written once and fixed before any model call.

- Files on branch `learning-pilot`: `workspace/learning-pilot/lessons_system.txt` and `lessons_user.txt`. The user file's `{game}` and `{record}` are filled in.
- **sha256 of the system file's bytes followed by the user file's bytes:** `d755001513b60546cbcc4159db0965dbeda09a65d65377d874b22e247f74550e`.

System:

```
You are a backgammon player reviewing one of your own games against the GNU Backgammon engine's evaluation, to play better in your next games. You write short, general lessons for yourself.
```

User:

```
You just played game {game} of a series of games against the same opponent. Below is the record of that game: every decision you made, with the GNU Backgammon engine's evaluation of it (2-ply: its best play, the equity you lost, and its verdict). Boards are given in your point numbering.

{record}

Write at most 5 lessons for your next games in this series, at most 150 words in total. Each lesson is one line starting with "- ", general advice rather than a comment on one specific position. Reply with the lessons only.
```

## 5. Structure

- **Series:** 10 games against the anchor, played as a 5-round match with no early end at 5 points and no tie-break round. Games 2k−1 and 2k are a mirrored pair: same dice, seats swapped. After every game, the game is scored and the arm's context is updated. The next game reads the new context before every decision.
- **Dice:** series s uses one dice seed in every arm, derived from a fixed master string; every seed is kept in `seeds.json`. The arms share dice schedules; their games differ once their plays differ.
- **Evaluations (the 200-position set):**
  - **T0:** ONE shared run before game 1, with an empty context. It is every arm's starting point and the control arm's evaluation. It is run once in total, not once per series.
  - **T5 and T10:** after game 5 and after game 10 of every series, for records, lessons and budget, each with the arm's current context.
  - **Counts:** 200 + 3 arms × 10 series × 2 × 200 = **12,200** evaluation answers. The smoke run (3 series) needs 3,800.
- **Smoke:**
  - 3 series per arm first. If the smoke is clean, the run continues to **10 series in total per arm**.
  - "Clean" means technical and protocol cleanliness only. It is never a positive learning result.
  - The smoke series count toward the 10 only if the prompt, the scoring, the arms and the evaluation set are unchanged after the smoke. If any of these changes, the smoke series are run again and the reason is logged.
- **Restarts:** a series cut off part-way is played again from game 1 with the same dice. The restart is logged, and the old match stays in the database.

## 6. Evaluation set

- **Source:** the Clear-risk scan's kept decisions from League 2 (`mailbox/Clear-risk scan - method 2026-10-29.md` and its amendments). In each one, the best unsafe play (12 or more hitting rolls) and the best safe play (0 hitting rolls) differ by at least 0.04 equity at both 2-ply and 3-ply, in the same direction, and the 2-ply and 3-ply gaps differ by at most 0.02. League 2 has 3,337 kept Risk wins and 7,704 kept Safety wins.
- **Exclusions, in order:**
  1. one legal play (none: the scan already skips one and two legal plays);
  2. a repeated position, meaning the same board from the mover's side and the same dice (787 removed);
  3. a position whose class under the site's rule (margin 0.001) disagrees with its scan group. This keeps "risks found" and "right safety" on the site's definitions for every position. 1,188 Safety wins were removed because an in-between play beats the best safe play.
- **Draw:** from the remaining pools (3,004 Risk wins, 6,062 Safety wins), 100 Risk wins and 100 Safety wins, with a fixed seed kept in the private files.
- **Positions with more than 26 legal plays:** 32 in total (18 Risk wins, 14 Safety wins). They are asked in groups, as in the league.
- **Median absolute 3-ply gap:** 0.129 for Risk wins, 0.234 for Safety wins.
- **Context:** each position is shown as it was in the league, with the same board, dice, score, round, game, turn and option order.
- **Offline check, with no model call:** 160 single-request positions have a stored league exchange. For all 160, the prompt the harness renders matches the prompt the league sent: 125 identical in full, and 35 with identical state text (those were sent to decision services). The other 8 single-request positions have no stored exchange.
- **Privacy:** the positions, the answers and the per-position results are never published (section 9).

## 7. Metrics

The definitions are the site's (`tools/site/analysis.py`). Every share is taken over valid answers.

**For each arm and evaluation (T0 shared; T5 and T10 for records, lessons and budget):**

- **Error rate (PR):** 500 × the mean 2-ply equity loss.
- **Risk judgement:** 50 × (right risks ÷ Risk pays + right safety ÷ Safety pays).
- **Risks found:** right risks ÷ Risk pays positions.
- **Right safety:** right safety calls ÷ Safety pays positions.
- **Risk appetite:** the share of the Risk pays and Safety pays positions where the chosen play leaves more hitting rolls than the best safe play, right or wrong.
- **Invalid answers:** answers that name no option. They are left out of every quality number, as on the site. Failed requests are counted separately.
- **Tokens per decision.**
- **Records dropped:** older games or decision lines that were left out of the context.
- **Cost** ($0) and **time**.

**For each arm, from its games:**

- the error rate of every game;
- decision latency;
- tokens per decision;
- wins.

**A17 learning lift:** for each arm and series, the error rate in games 1–3 minus the error rate in games 8–10. Decisions are pooled within each group of games. A positive value means the arm played better later. It is compared with the control arm's change, paired by series: (arm's lift − control's lift), averaged over the series.

**Secondary:** records against lessons against budget.

All of these are descriptive and outside the Holm correction. Each interval is a 95% percentile bootstrap: 10,000 resamples of whole series, fixed seed, with the same series drawn for every arm, so each resample keeps the dice schedules paired across arms.

## 8. Signal rule

A17 fixed this rule before the first model call. It replaces every earlier version.

For each non-control arm (records, lessons, budget), averaged over its series:

> **risks found after game 10 (T10) − risks found before game 1 (T0) ≥ +10 points, AND right safety (T10) − right safety (T0) ≥ −5 points.**

- Points are percentage points.
- T0 is the shared run.
- The rule is reported for every arm, with the learning lift against control next to it as the second measure.

## 9. Leakage, isolation and publication

**Leakage and isolation:**

- Evaluation positions never appear in any context, record or lesson input. A game decision on a board equal to an evaluation position's board (mover's side, any dice) is left out, and the number left out is counted.
- Evaluation answers and their scores never feed any context, lesson call or later prompt.
- The arms never see each other's games. Each arm's context comes only from its own game records in the current series. The budget arm reads only the lessons arm's token count, never its content.
- Pilot data are kept apart from the leagues and the site's inputs. They are not in `v3.db`, not under `tools/site/content`, and not in any public export.

**Display:**

- The page shows the protocol, the lesson prompt with its hash, this signal rule and the commitment sentence before the first model call.
- Numbers (a table per arm and evaluation, and progress as series done out of planned) update after each series.
- No verdict ("learns" / "doesn't learn") and **no learning lift** are published until all planned series of every arm are done, even if games 8–10 already exist for some series.
- Every lesson the model wrote is published next to the game it came from.

**What is committed:**

- To the repo: this plan and the results page, aggregates only.
- Kept private and uncommitted, in `workspace/learning-pilot/` and `smoke/`: raw files (`learning.jsonl`, `seeds.json`, the evaluation set, answers, and contexts with real positions).

## 10. Outputs and harness

**Outputs:**

- `learning.jsonl`: every pilot game and evaluation, by arm and series, with the context each decision saw and the lessons written.
- `seeds.json`: the dice seed of every series, the option-order seed, and the option order of every position.
- `learning-pilot.json`: aggregates.
- The results table: `mailbox/Learning pilot - results 2026-11-07.md`.

**Harness:** on branch `learning-pilot`, not main.

Runner changes:

- `prompt_note` and `prompt_note_file` in a player config: text appended to the system prompt;
- for a single match: `--model1-config`, `--fixed-rounds`, and `--after-game` (a command run between games, which scores the game and updates the context).

Scripts in `workspace/learning-pilot/`:

- `build_test_set.py`: the evaluation set;
- `check_render.py`: the offline prompt check;
- `score_games.py`: GNU Backgammon 2-ply scoring;
- `pilot.py`: the shared T0, the series, contexts, lesson calls, evaluations, aggregates, `learning.jsonl` and `seeds.json`;
- `report.py`: the table.

**Dry run:** an offline run with the Safest program in Gemma's seat played series of all four arms end to end, with no model call. Evaluations and lessons were stubbed.
