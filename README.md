# jevgammon

Terminal backgammon where both players are AI models — a decision model (Jev and the other
System One services, OpenAI's Decisions API) or an LLM. Every
round is played twice with the seats swapped and identical dice, and every roll, move,
and model exchange is stored in SQLite. It has a ratatui interface with adjustable speed
and a headless mode for benchmarking.

```sh
./jevgammon --model1 openai/gpt-5.6-Sol --model2 jev
./jevgammon --model1 anthropic/claude-sonnet-4-5 --model2 jev --quiet --rounds 10 --seed 7
./jevgammon league GLiDE=fastino Clef=clef Cygnet=cygnet "Open-Jev=open-jev"
```

## Build

Requires Rust 1.88+ (edition 2024). SQLite is bundled; nothing else needs installing.

```sh
cargo build --release
cp target/release/jevgammon .
```

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--model1 <spec>` | required | First player (see [Players](#players)) |
| `--model2 <spec>` | required | Second player |
| `--rounds <n>` | `5` | Rounds per match; each round is two games |
| `--speed <1-6\|max>` | `4` | Initial interface speed |
| `--quiet` (alias `--quite`) | off | No interface; print the score when it changes |
| `--db <path>` | `jevgammon.db` | SQLite database file (created if missing) |
| `--seed <u64>` | random | Match seed; fixes every roll of every round |
| `--clock <seconds>` | `300` | Thinking-time bank per player per game; `0` disables the clock (see [Clock](#clock)) |
| `--delay <seconds>` | `30` | Free time per decision before the bank is used |
| `--max-turns <n>` | `300` | Turn limit per game, decided on pip count; `0` = no limit (see [Turn limit](#turn-limit)) |
| `--qfork-root <dir>` | `~/.qfork/glyph` | qfork/Glyph credential root (env `JEVGAMMON_QFORK_ROOT`) |
| `--local-url <url>` | `http://localhost:8080/v1` | Server behind `local/<model>` (env `JEVGAMMON_LOCAL_URL`) |

Exit status: `0` when the match finished, `1` when it was aborted or failed (the reason is
printed and stored in `matches.error`), `2` for invalid arguments.

## Match format

- A **round** is two games with the same dice. In leg 1 `--model1` plays white (○); in
  leg 2 the seats swap and `--model2` plays white. Dice come from a per-round seed and
  are drawn per turn, so each seat gets the identical roll sequence, opening roll
  included, whatever either model plays.
- A **match** is `--rounds` rounds (default 5, i.e. 5 × 2 games), or ends earlier after
  the round in which a player reaches 5 points: the mirror game is always played, then the
  player ahead wins. If the score is tied when the match would end (after the planned
  rounds, or level at 5+), exactly one extra round is played; a tie after that is a draw.
  League playoffs keep adding rounds until one player leads (see [League](#league)).
- Games are scored in points: single 1, gammon 2, backgammon 3. There is no doubling cube.
- Thinking time uses the WBGF Simple Delay clock: 30 s free per decision, then a 5-minute
  bank per player per game. An empty bank loses that game for 1 point (see [Clock](#clock)).
- A game still running after 300 turns is won by the lower pip count for 1 point (see
  [Turn limit](#turn-limit)).
- The engine generates every legal full-turn play. Plays that reach the same position are
  listed once. Turns with no legal play, or exactly one, are played without calling the
  model.

## Players

| Spec | Provider | Credentials |
| --- | --- | --- |
| `jev`, `jev/<model>` | TypeSafe System One API (`jev-latest` default) | `TYPESAFE_API_KEY` or `JEV_API_KEY` |
| `fastino`, `fastino/<model>` | Fastino System One API (`fastino/GLiDE` default) | `FASTINO_API_KEY` |
| `openai-decisions`, `openai-decisions/<model>` | OpenAI Decisions API (`gpt-6-luna` default) | `OPENAI_API_KEY` (an API key with billing) |
| `perplexity`, `perplexity/<model>` | Perplexity Decisions API (`pplx-decider-v1-27b` default) | `PERPLEXITY_API_KEY` |
| `liquid`, `liquid/<model>` | Liquid AI System One API (`d1:free` default) | `LIQUID_API_KEY` |
| `clef` | Self-hosted Clef server, `http://127.0.0.1:18091` | none |
| `open-jev` | Self-hosted Open-Jev server, `http://127.0.0.1:8791` (takes no model name) | none |
| `cygnet` | Self-hosted Cygnet decision server, `http://127.0.0.1:18093` | optional `CYGNET_API_KEY` |
| `gemma` | A second Cygnet decision server (same option-letter readout) in front of a `gemma-4-31B-it` vLLM server, `http://127.0.0.1:18094` | optional `GEMMA_API_KEY` |
| `openai/<model>` | ChatGPT subscription (Codex backend) | qfork store or `~/.codex/auth.json` |
| `anthropic/<model>`, `claude/<model>` | Claude subscription | qfork store or `~/.claude/.credentials.json` |
| `gemini/<model>`, `google/<model>` | Gemini API | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or qfork `credentials/gemini.json` |
| `ollama/<model>` | Ollama (OpenAI-compatible API) | `OLLAMA_HOST` (default `localhost:11434`) |
| `local/<model>` | Any OpenAI-compatible server (llama.cpp, LM Studio, vLLM) | `--local-url`, optional `LOCAL_API_KEY` |

Examples: `openai/gpt-5.6-sol`, `anthropic/claude-sonnet-4-5`, `gemini/gemini-2.5-flash`,
`ollama/qwen3`, `jev`, `jev/jev-1.13.0`. OpenAI model names are lowercased (`gpt-5.6-Sol` →
`gpt-5.6-sol`), as the subscription endpoint requires. A model name containing `/` goes
after the provider unchanged (`fastino/fastino/GLiDE`). Each decision service's host can be
overridden: `TYPESAFE_BASE_URL`, `FASTINO_BASE_URL`, `OPENAI_DECISIONS_BASE_URL`,
`PERPLEXITY_BASE_URL`, `LIQUID_BASE_URL`, `CLEF_BASE_URL`, `OPEN_JEV_BASE_URL`,
`CYGNET_BASE_URL`, `GEMMA_BASE_URL`, `PPLX_LOCAL_BASE_URL` (`pplx-local`: pplx-decider-v1.1-27b served by `~/code/pplx-decider/server.py` on port 18097).

Missing credentials are reported at startup, before a match is created.

### What the models see

Every player gets text in this order. Earlier games of the match are not described, and
only the last 10 moves of the current game are:

1. [`PROMPT.md`](PROMPT.md) with this match's rounds, turn limit, and clock filled in (the
   turn-limit and clock rules are dropped when the match has none). LLMs get all of it.
   Decision models get only the rules, strategy principles, opening rolls, and match rules
   (about 8,000 characters): self-hosted ones such as Open-Jev and Cygnet accept 4,096
   tokens, and the full file is about 5,500.
2. **Score**: both scores and whether it leads or trails, round and game number.
3. **Time**: the turn number and the turn limit, the delay for this decision, and both
   players' bank left in this game.
4. **Position** from its own side (you move from 24 toward 1 and bear off past 1):
   checkers, bar, borne off, pip counts, and the **race**: the pip lead and whether the
   checkers are still in contact. Then the **last 10 moves** of this game, oldest first,
   both sides, in its own numbering (the opponent's moves are converted), so it can follow
   how the position came about. Ten keeps Open-Jev's prompt plus one option under its
   4,096 tokens.
5. **Dice**, then the question "Which of the following moves makes a point in front of
   the opponent's checkers, or reduces your single pieces, or gets you closer to your
   home?".
6. **Legal plays**, each in standard notation (`bar/22 13/11*`, `6/off`, `*` = hit) followed
   by what the position looks like after it, computed exactly in `src/players/prompt.rs`:
   checkers hit, points newly made, blots left and how many of the opponent's 36 rolls can
   hit one of them (by generating the opponent's legal plays for every roll), points held
   and how many in the home board, longest prime, and both pip counts.

The "Your turn" and "Example" sections of `PROMPT.md` show the exact format.

How they answer:

- **LLMs** get `PROMPT.md` as the system prompt and items 2-6 as the user message, with
  the plays numbered, and answer `{"choice": N}`. OpenAI, Gemini, and local servers get a
  JSON schema; Anthropic gets a forced tool call. A reply that doesn't parse or is out of
  range is re-asked with the reason, up to three replies. After that the first legal play is used
  and the turn is marked `fallback`.
- **Decision models** get items 1-5 as a string in `state` (OpenAI's Decisions API: in
  `input`) and one `choice` question whose options are the legal plays: keyed by notation,
  so the answer is always legal, with the described play as the option text. Each service
  has an option limit: 255 for hosted services, 110 for Clef (16,384-token option list),
  26 for Cygnet and Gemma (one letter per option), 25 for the local Decider v1.1 (8,192
  tokens, and GPU memory). Longer play lists are split into equal chunks, a winner is
  picked per chunk, then a final choice is made among the winners. A refusal (OpenAI)
  plays the first candidate and marks the turn `fallback`.
- Transient HTTP failures (network errors, 408/409/425/429/5xx/529) are retried up to ten
  times with exponential backoff from 1 s to 60 s (about 4 minutes in all). `Retry-After`
  can lengthen a wait but never shorten it. The waits count against the mover's clock. Any
  other failure, or running out of retries, aborts the match.

### Clock

Thinking time follows the Simple Delay method of the WBGF Tournament Rules (section 3.5):
each decision first gets `--delay` seconds free (default 30), which do not accumulate;
only time beyond that comes out of the player's bank of `--clock` seconds (default 300)
for the game. Both banks are full again at the start of every game, including the second
leg of a round. A model that answers within the delay at its normal pace never touches
its bank, and the bank absorbs the occasional slow decision. Forced moves, turns with no
legal move, and the pause between moves are free. The time includes HTTP retries and
re-asks, because they happen inside the decision.

Unlike WBGF, where running out of time loses the match, an empty bank loses only the
game: the request is abandoned, the turn is recorded with `decided_by = 'timeout'`, and
the opponent wins the game for 1 point (`games.result = 'timeout'`), whatever the
position.

The models know about the clock: the rule is part of the rules they get, every request
shows the delay and both banks, and a game lost on time is listed with its reason in the
earlier-games list of every later request (see [What the models see](#what-the-models-see)).

### Turn limit

WBGF rules play every game to completion, but two models that hit each other's blots at
every chance can keep a game going indefinitely (a test game passed 1,100 turns). So a
game still running after `--max-turns` turns (default 300, both sides counted) ends there:
the side with the lower pip count wins a single game for 1 point, and with equal pip
counts the side due to roll next wins. It is recorded as `games.result = 'turn_limit'`.
Models see the turn number and the limit in every request.

### Latency

Models run with their provider's default settings. Reasoning models can be slow. On a
ChatGPT subscription, `gpt-5.6-sol` took about 3 minutes for one decision at the default
(medium) reasoning effort, which empties a 5-minute bank within two decisions. Claude
Sonnet without extended thinking takes about 1–2 s per decision. Decision services take
0.2–2 s; self-hosted Open-Jev scores every play separately, so a decision takes about
0.4 s per legal play (around 30 s for 70 plays).

### Subscription logins

jevgammon has no login flow of its own; it reuses existing logins. It looks in these
places and uses the token that expires last:

- qfork/Glyph credential envelopes under `--qfork-root`: `credentials/openai.json`,
  `credentials/anthropic.json`
- Codex CLI: `$CODEX_HOME/auth.json` (default `~/.codex`)
- Claude Code: `$CLAUDE_CONFIG_DIR/.credentials.json` (default `~/.claude`)

To log in, use qfork, `codex login`, or `claude`.

Tokens are refreshed when they expire within five minutes, or once after a 401/403.
Refreshing rotates the refresh token, so the new tokens are written back to the store they
came from; otherwise the owning tool would be logged out. For qfork, the token is added
as a new active revision under qfork's own `locks/<provider>*.lock` file locks. Codex and
Claude files are updated in place, atomically, with mode 0600.

## Interface

Speeds 1–6 draw the board and pause 3000 / 1500 / 800 / 400 / 150 / 50 ms after each
move. Speed `max` hides the board: the score sits in the middle with rolls and moves
flashing below it, as fast as the models answer. White is ○, black is ●; each move is
written in the mover's own point numbering.

The current roll is drawn as two dice in the middle of the board, in the mover's half:
white's roll on the right, black's on the left. It stays there, in the mover's colour,
until the next roll. The line under the board (and under the score at max speed) repeats
it, along with how long the model has been thinking.

Each player's bank left (`⏱ 4:12`) is shown next to its name on the score line. The
thinking player's bank counts down in bold once its delay has passed and turns red under
30 seconds. A game lost on time appears in the move list as `⌛ out of time`.

| Key | Action |
| --- | --- |
| `+` / `-`, arrow keys | faster / slower |
| `1`–`6` | set speed |
| `m` or `0` | max speed |
| `space` or `p` | pause / resume |
| `q`, `Esc`, `Ctrl-C` | quit (a running match is recorded as aborted) |

## Quiet mode

`--quiet` runs without the interface at max speed. It prints one line when the match
starts, one line per finished game (the score changes after every game), and the result:

```
match #3: anthropic/claude-sonnet-4-5 vs jev · 1 rounds · clock 5:00 · seed 5 · db jevgammon.db
round 1 leg 1: anthropic/claude-sonnet-4-5 wins a gammon (+2) · score anthropic/claude-sonnet-4-5 2 - 0 jev
round 1 leg 2: anthropic/claude-sonnet-4-5 wins a backgammon (+3) · score anthropic/claude-sonnet-4-5 5 - 0 jev
final after 1 rounds: anthropic/claude-sonnet-4-5 5 - 0 jev · winner anthropic/claude-sonnet-4-5
```

`Ctrl-C` aborts the match and records it as aborted. A process killed with `SIGKILL`
leaves its match in `running`.

## League

`jevgammon league` plays a single round robin between the listed models (`NAME=SPEC`, or
a bare spec that is also its name):

```sh
./jevgammon league "Gemma 4 31B=gemma" "GPT-6 Luna=openai-decisions" "Decider 27B=perplexity" \
  "Jev 1.13.0=jev/jev-1.13.0" Clef=clef d1=liquid "Open-Jev 27B=open-jev" Cygnet=cygnet \
  --note "move metrics in every option" --db league.db
./jevgammon league --resume 1 --db league.db
```

`--note` records what the league tests (a prompt change, a model swap) in `leagues.note`;
the dashboard shows it in the league history.

- **Fixture:** drawn from the league seed (`--seed`, random by default) by the circle
  method on a shuffled entry list: with 8 models, 7 matchdays of 4 matches, every model
  playing once per matchday (an odd count gives one model a bye each matchday). Which model
  is `model1` (white in the first game of every round) is drawn per match; the opening roll
  then decides who moves first, and the second game repeats the rolls with seats swapped,
  so the other model moves first with the same roll.
- **Matches** use the normal format (`--rounds`, `--clock`, `--delay`, `--max-turns`). A
  match starts as soon as both its models are free, in fixture order: a model never plays
  two matches at once, but nobody waits for the rest of a matchday to finish. Every match
  has its own seed, derived from the league seed and the fixture.
- **Table:** a win is 3 league points, a draw (still tied after the extra round) 1. Ties
  are broken by more games won, then fewer games lost. Backgammon points scored and
  conceded are shown but not used.
- **Playoffs:** a tie still standing that involves any of the first three places is played
  off: two models play one match whose tie adds rounds until one leads; three or more play a
  round robin of such matches, ranked like the league, with any tie inside it played off
  again. Ties below third place share their place.
- **Warm-up:** before every match (league or single) each decision service gets a
  two-option request, repeated until it answers (up to 15 minutes), so a cold start such
  as Fastino's HTTP 425 "warming up" never runs on a clock.
- **Failed matches:** a match that aborts (for example, a provider outage that outlasts
  the HTTP retries) is replayed from the start with the same seed after 2 minutes, up to 3
  attempts. If the last attempt fails too, no new match starts and the league stops once
  the running ones finish; `--resume <id>` keeps every finished match and replays
  unfinished ones from the start with the same seed.

The table is printed each time every match of a matchday has finished, then the final
table and ranking.

### Dashboard

`tools/league_web.py` serves one page for every league in the database. It needs only
Python 3.10+, reads the database read-only, and refreshes every 5 s:

```sh
python3 tools/league_web.py --db league.db --port 8095   # http://<host>:8095/
```

- **History:** every league, newest first: live (moved in the last 10 minutes), finished,
  or stopped part-way; start, duration, models, rounds, matches finished, games, share of
  games ending at the turn limit, leader, and the note. Clicking a league shows it below
  (`?league=<id>` in the address).
- **Places:** for each model, how many times it finished 1st, 2nd, 3rd, … over the
  finished leagues only (stopped and running ones are left out), best record first.
- **League on view:** table (`‹` `›` step through the finished leagues and the live one),
  per-model decision stats, the fixture with results, and recent
  games. While it is live, every running game shows its board and last move; `«`, `»` and
  `⏮ round start` step through the rolls of the current round, `live` returns to the game
  in progress, and `context` shows what was sent to the model for that roll and its answer.

`--league <id>` picks the league shown by default (otherwise the latest); `--host` defaults
to `0.0.0.0`, so the page is reachable from the LAN without authentication.

### Engine evaluation

`tools/gnubg_eval.py` scores every model decision with GNU Backgammon (`apt install
gnubg`). It runs inside gnubg's embedded Python, which passes no command-line arguments,
so they come from `GNUBG_EVAL_ARGS`; split the work into shards and run them in parallel:

```sh
for s in $(seq 0 39); do
  GNUBG_EVAL_ARGS="league.db eval-$s.db $s 40 8 11 12" gnubg -t -q -p tools/gnubg_eval.py &
done; wait
```

Each decision's legal plays are generated again with the rules of `src/board.rs`, ported in
`tools/v3/rules.py` (the count must match `turns.legal_count`, otherwise the decision is
listed in `skipped`). Every play
is evaluated at 0-ply, the five best and the chosen one again at 2-ply, in cubeless money
equity. The `decisions` table holds the best and chosen equity and the loss. The error rate
is the mean loss × 500. A shard that is run again skips decisions it already scored.

### Benchmark v3 positions

`tools/v3/` builds and scores the v3 shared position sets. The gnubg scripts run from the
repo root inside gnubg's embedded Python and take their arguments from `V3_ARGS`:

```sh
gnubg -t -q -p tools/v3/test_classify.py      # phase rules, game-plan tags, gnubg class numbers
V3_ARGS="standard 1711332899 0 300 positions/games/standard-00.jsonl.gz" \
  gnubg -t -q -p tools/v3/selfplay.py          # expert self-play games (one shard)
gnubg -t -q -p tools/v3/build.py               # positions/*.jsonl and positions/build-log.json
V3_ARGS="evaluate out=score.db positions=positions/new.jsonl" gnubg -t -q -p tools/v3/score.py
V3_ARGS="rollout out=score.db positions=positions/new.jsonl chosen=chosen.json" \
  gnubg -t -q -p tools/v3/score.py             # rollouts of near-ties, chosen ones first
python3 tools/v3/freeze.py                     # sha256 of positions, prompts, seeds, roster
```

`seeds.json` holds the option-order seed and the self-play and sampling seeds; the games in
`positions/games/` (not committed) are reproduced from them. `tools/v3/order.py` is the
Python twin of `src/players/order.rs` (test vectors in `tools/v3/order_vectors.json`). Each
position row lists its legal plays in `Board::legal_plays` order and `option_order[k]`, the
index of the play shown as option k.

## Database

The database has six tables:

| Table | Contents |
| --- | --- |
| `matches` | models, seed, planned and played rounds, clock bank and delay seconds (NULL = off), turn limit, score, winner (`1`, `2`, or NULL for draw), status `running\|finished\|aborted`, error |
| `games` | round, leg, white player, dice seed, opening roll, winner, result (`single\|gammon\|backgammon\|timeout\|turn_limit`), points, turn count |
| `turns` | side, player, dice, position before the move (JSON, white's perspective), number of legal plays, chosen index, move (mover's numbering), `decided_by` (`model\|forced\|no_move\|fallback\|timeout`), latency, tokens, mover's bank left after the turn (`clock_ms`) |
| `exchanges` | every model request body, reply text, rejection reason, latency; one row per request |
| `leagues` | seed, rounds, clock bank and delay, turn limit, entrants (JSON `{name, spec}`), status, final ranking, note (`--note`) |
| `league_matches` | stage (`league\|playoff`), label, matchday, model names, seed, latest `match_id` |

Seeds are unsigned 64-bit values stored in SQLite's signed INTEGER; cast back to `u64` to
reuse them. Passing the same `--seed` replays the same dice for every round.

```sql
-- Points per pairing across finished matches
SELECT model1, model2, COUNT(*) AS matches, SUM(score1), SUM(score2)
FROM matches WHERE status = 'finished' GROUP BY 1, 2;

-- Average decision time and tokens per model
SELECT CASE t.player WHEN 1 THEN m.model1 ELSE m.model2 END AS model,
       COUNT(*) AS decisions, AVG(t.latency_ms), SUM(t.input_tokens), SUM(t.output_tokens),
       SUM(t.decided_by = 'fallback') AS fallbacks, SUM(t.decided_by = 'timeout') AS timeouts
FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
WHERE t.decided_by IN ('model', 'fallback', 'timeout') GROUP BY 1;

-- Same round, both legs: how each model played the same dice
SELECT g.round_no, g.leg, t.turn_no, t.side, t.die1, t.die2, t.move
FROM turns t JOIN games g ON g.id = t.game_id
WHERE g.match_id = 1 AND g.round_no = 1 ORDER BY t.turn_no, g.leg;
```

## Development

```sh
cargo test
cargo run -- --model1 ollama/qwen3 --model2 jev --speed 5
```

| File | Responsibility |
| --- | --- |
| `src/board.rs` | rules, legal play generation, game results |
| `src/dice.rs` | seeded dice (SplitMix64, implemented locally so seeds stay reproducible across dependency upgrades) |
| `src/runner.rs` | match flow, mirrored legs, tie-break round, pacing and pause |
| `src/players/` | prompts, LLM providers, decision services (System One, OpenAI Decisions) |
| `src/league.rs` | league fixture, parallel matchdays, table, playoffs, resume |
| `src/auth.rs` | subscription credential stores and refresh |
| `src/http.rs` | retries and backoff |
| `src/db.rs` | SQLite schema and writes |
| `src/ui.rs` | ratatui interface |
