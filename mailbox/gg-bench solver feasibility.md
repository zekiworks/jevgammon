# gg-bench: can an exact solver referee its games?

Date: 2026-10-14. No model/API calls and no game generation were made. Everything below comes from runs on this machine.

## What ships with the repo

Cloned https://github.com/vivek3141/gg-bench (MIT, commit bca0e6a). It does not use Git LFS: `.gitattributes` has a single line, `*.txt linguist-vendored`. The games ship in full, so nothing has to be regenerated. `gg_bench/data/` contains 1000 generated Gym environments (`envs/env_N.py`), their rulebooks (`descriptions/N.txt`) and move descriptions (`actions/N.txt`). It also has trained PPO/DQN agent checkpoints for 538 environments (about 1.3 GB). The benchmark itself is the 126 games in `splits/valid_envs.json`, each paired with an agent checkpoint. Evaluation results for 7 models are in `results/`. The repo also contains a depth-limited minimax (`utils/minimax.py`), but it is not used for refereeing.

The referee rules the solver follows come from the code (`scripts/eval/eval.py` and `utils/game_stats.py`), not from the rulebooks. Seats strictly alternate, and the mover picks from `env.valid_moves()`. The game ends when `step()` returns done. The terminal reward is read from the mover's side: 1 is a win, −1 a loss, 0 a draw. A −10 reward, a crash or an empty move list counts as a fault. The env is wrapped in `TimeoutEnv(100)`, so a 100th `step()` raises and the game gives no result.

## How the games were picked

All 126 environments use only `numpy` and `gymnasium`. 24 of them draw random numbers; I read the source of each one:

- 9 randomise only the setup, and the result is public (for example a random start number or a random first player).
- 10 have the env play a random "opponent" inside `step()`. These are simultaneous-move games implemented incorrectly.
- 5 have hidden information: shuffled decks or a secret target.

The 10 picked games are 6 deterministic and 4 with public chance at setup. They include the four paper examples that are among the 126: Palindrome Duel, Reach 27, Light Out Duel and Divide and Conquer. Order Challenge is not among the 126. I read the rulebooks of all 10 to exclude hidden information. Among the 126 there is no clean perfect-information game with chance during play (dice-like), so the chance in the picked games is all at setup. As an extra check, the same solver was also run on all 126 games.

## Solver

`/home/cbasaran/code/ggbench-check/solver.py` works generically over the Gym envs: negamax with memoisation, plus expectimax at chance nodes.

- **State key:** a 128-bit hash of a canonical serialisation of the env's `__dict__`. RNG objects and spaces are left out.
- **Chance:** every call to `np.random.*`, `random.*`, `self.np_random`, `default_rng` and `space.sample()` goes to a chooser that enumerates every discrete outcome with its probability. Continuous draws are rejected as "not enumerable".
- **Rejection-sampling loops** (`while True: draw; if ok: break`) would make the outcome tree infinite. The solver drops the retry branches and renormalises; this is exact because the retries are i.i.d.
- **Setups too large to enumerate** (Digit Dilemma deals 20 random digits, 10²⁰ deals): the solver solves 5 sampled deals instead.
- **Legal moves:** only `valid_moves()` counts. If a listed move returns −10 or crashes, that is logged as an env anomaly and scored 0.
- **Cycles or games past 100 plies:** the solve restarts with the ply count in the key, and the 100th step scores 0, as in the harness.
- **Budget:** 600 s CPU per game, 44 games in parallel.

To run it:

`cd /home/cbasaran/code/ggbench-check && .venv/bin/python run.py --all && .venv/bin/python summarize.py`

- The venv was created with `uv venv .venv -p 3.12 && uv pip install -p .venv gymnasium numpy==2.2.2`.
- `run.py` with no flags runs only the 10 picked games.
- One game: `.venv/bin/python solver.py <id>`.
- The full sweep took 11 minutes of wall time. Raw results are in `results/all.jsonl` and the tables in `results/summary.md`.

## Results for the 10 picked games

"Decisions" means reachable non-terminal states with at least 2 legal moves. "Non-uniform" means the legal moves do not all have the same solved value. The start value is from the first mover's side: +1 means the first player wins, 0 a draw or no result, −1 the second player wins. With chance it is an expectation.

| id | game | chance | solved | states | CPU s | start value | decisions | share non-uniform | mean distinct values |
|---|---|---|---|---|---|---|---|---|---|
| 272 | Palindrome Duel | – | yes | 8 | 0.00 | draw (every ending scores 0) | 8 | 0.00 | 1.00 |
| 840 | Reach 27 | – | yes | 52 | 0.02 | P1 wins | 50 | 0.92 | 1.92 |
| 891 | Light Out Duel | – | yes | 220 | 0.05 | P1 wins | 206 | 0.66 | 1.66 |
| 897 | Isolation (13 squares) | – | yes | 3,151 | 0.46 | P1 wins | 2,381 | 0.31 | 1.31 |
| 799 | Gridlock (4×4) | – | yes | 65,401 | 13.9 | P2 wins | 57,861 | 0.54 | 1.54 |
| 333 | Quad Block (5×5) | – | **no** | 2,077,676 when stopped | 600 | – | (2,044,945 so far) | (0.68) | (1.78) |
| 154 | Divide and Conquer | random start number | yes | 1,300 | 0.24 | E = −0.12 over 1,412 starts | 1,210 | 0.00 | 1.00 |
| 985 | Divisor Duel | random N in 50–100 | yes | 197 | 0.04 | E = +0.02 over 51 starts | 147 | 0.66 | 1.66 |
| 114 | Alpha Chase | random public words | **no** | 6,385,126 when stopped | 600 | – | (2,669,130 so far) | (0.19) | (1.19) |
| 646 | Digit Dilemma | 20 random digits | yes (5 sampled deals) | 3,650,470 | 360 | +1, −1, +1, −1, −1 | 3,650,470 | ≈0 (2·10⁻⁶) | 1.00 |

Results across all 126 games:

- **How many were solved within 10 CPU-minutes:**
  - 94 of 126 in total.
  - 78 of 102 deterministic games. Median time 0.3 s; only 9 took more than 60 s.
  - 8 of 9 games with setup chance.
  - Every game that ran out of budget was stopped with 0.04–8 million states (892 crashes in `step()` on most moves, so it stalls). The rest are mostly 5×5 grids and games with large number ranges. In pure Python the solver handles roughly 0.3k–13k states per second.
- **Start values of the 78 solved deterministic games:**
  - 55 are forced first-player wins.
  - 12 are second-player wins.
  - 11 are draws or no result.
- **How coarse the move scores are:**
  - Across the 86 solved deterministic and setup-chance games, the share of non-uniform decisions has quartiles 0.36 / 0.63 / 0.72.
  - The mean number of distinct move values per decision has quartiles 1.36 / 1.63 / 1.75.
  - Only 1.4% of all decisions have three or more distinct values (possible only through draws, timeouts or chance).
  - 6 games have a share below 0.1: 272, 154, 243, 721, 327 and 646.

## Caveats

- **The solver solves the code, not the rulebook.** Many envs encode "the mover loses" as reward 0, which the harness logs as a draw. In Palindrome Duel (272) the rulebook says that making a palindrome loses, but all 8 reachable endings return 0, so under the referee every game is a draw. The same is true of 243 and 327. In 663 the env lists moves in `valid_moves()` that it then punishes with −10. In Quad Block, 3,896 positions are full boards with no winner, which the harness treats as a fault. A solver-referee inherits these bugs, but it also finds them cheaply. In the 10 picked games, that is how they turned up.
- **A score of 0 mixes three things:** draws, the 100-step timeout, and env errors.
- **State counts are inflated.** The state key includes the env's bookkeeping (move history, player labels, full digit strings), so counts can exceed the true game's state space. This costs speed but not correctness.
- **"Deterministic" is a judgement made from the code.** I did not audit all 102 rulebooks for secret or simultaneous moves; 327 "Secret Sum" is one such game. Envs with hidden information cannot be refereed by solving the env state: that would be a clairvoyant solve. The 2 hidden-information games that "solved" (758 and 624) are meaningless for that reason.
- **The non-uniform share counts every reachable state equally,** including states that only arise after silly play. It is not weighted by the positions that real matches reach. Games that are decided early make the share very small even when the opening matters. In Digit Dilemma only the first couple of picks ever matter.
- **Correctness spot checks:**
  - Reach 27: P1 wins by heading for 7 and 17, and 46 of 50 decisions are non-uniform, which matches a hand analysis.
  - Isolation: an independent bitmask solver also gives "P1 wins".

## Verdict

An exact solver can referee most of gg-bench as shipped. Three quarters of the 126 games (94) are solved exactly in under 10 CPU-minutes, most in under a second. The setup randomness, which is the only clean chance in the set, enumerates fine, and for very large setups you only need to solve the deal actually played. The games it cannot solve in budget are a minority of larger boards, which a faster solver or more time would probably cover [INFERENCE]. The real limits are elsewhere:

- The solver referees the env code, so env bugs become rules (all-draw games, legal moves that are punished).
- About 15 of the 126 games involve hidden information or are broken simultaneous-move games, and those need a different referee.

The move scores are coarse. With win/draw/loss outcomes a move is essentially one bit, "keeps the result" or "throws it", with 1.6 distinct values per decision on average and almost never three. In a typical game about a third of decisions are positions where no move matters. Some games (Divide and Conquer, Palindrome Duel, Digit Dilemma) carry almost no move-level signal at all, and 55 of the 78 solved deterministic games are forced first-player wins. Used as a move-quality scorer, the solver is a good blunder detector and a cheap filter for degenerate games. Getting finer grades would need something extra, such as distance-to-win tie-breaks, or scoring moves by their win rate against a fallible reference opponent.
