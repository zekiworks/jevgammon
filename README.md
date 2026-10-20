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
| `--order-seed <u64>` | random | Option-order seed; fixes the order in which every position's legal plays are shown (see [What the models see](#what-the-models-see)) |
| `--prompt-version <id>` | `bg-v2` | `bg-v2`, `bg-v2-notation`, `bg-v2-history`, or `nack-v2` (see [Prompt versions](#prompt-versions)) |
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
| `liquid`, `liquid/<model>` | Liquid AI System One API (`d1:free` default; `d1`, `d1-ultra` paid) | `LIQUID_API_KEY` or `LIQUIDAI_API_KEY` |
| `subq`, `subq/<model>` | SubQ System One API (`subq-snap-preview` default) | `SUBQ_API_KEY` |
| `celeris`, `celeris/<model>` | Celeris System One API (`celeris-1-decision` default) | `CELERIS_API_KEY` |
| `openrouter-decisions/<vendor>/<model>` | OpenRouter's System One route for the decision models it lists (`inception/mercury-decide` default) | `OPENROUTER_API_KEY` |
| `random`, `safest`, `gnubg-weak` | Baselines on the CPU: a random legal play, the play the opponent hits with the fewest rolls, GNUbg 1.08 at its Beginner level | none |
| `clef` | Self-hosted Clef server, `http://127.0.0.1:18091` | none |
| `open-jev` | Self-hosted Open-Jev server, `http://127.0.0.1:8791` (takes no model name) | none |
| `cygnet` | Self-hosted Cygnet decision server, `http://127.0.0.1:18093` | optional `CYGNET_API_KEY` |
| `gemma` | A second Cygnet decision server (same option-letter readout) in front of a `gemma-4-31B-it` vLLM server, `http://127.0.0.1:18094` | optional `GEMMA_API_KEY` |
| `pplx-local/<model>` | Self-hosted Perplexity Decider server, `http://127.0.0.1:18097` (`base_url` picks another); the model must name the loaded checkpoint (`pplx-decider-v1.1-27b` default, `pplx-decider-v1.2`, `pplx-decider-flash-v1.2`) | none |
| `winnow`, `winnow/<model>` | Self-hosted Winnow-12B server (`winnow-inference`), `http://127.0.0.1:8091` (`winnow-12b` default) | none |
| `openai/<model>` | ChatGPT subscription (Codex backend) | qfork store or `~/.codex/auth.json` |
| `anthropic/<model>`, `claude/<model>` | Claude subscription | qfork store or `~/.claude/.credentials.json` |
| `gemini/<model>`, `google/<model>` | Gemini API | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or qfork `credentials/gemini.json` |
| `antigravity/<model>`, `google-antigravity/<model>` | Gemini through the Google Antigravity subscription (Cloud Code Assist `daily-cloudcode-pa`, `v1internal:generateContent`) | OMP's login in `~/.omp/agent/agent.db` (read-only) |
| `xai/<model>`, `xai-oauth/<model>`, `grok/<model>` | Grok through the xAI subscription (SuperGrok; `api.x.ai/v1/responses`, JSON-schema-constrained letter) | OMP's `xai-oauth` login in `~/.omp/agent/agent.db` (read-only); xAI rotates refresh tokens, so an expiring token is refreshed by OMP (`omp token xai-oauth --force-refresh`; binary from `OMP_BIN` or `~/.local/bin/omp`) and read back |
| `ollama/<model>` | Ollama (OpenAI-compatible API) | `OLLAMA_HOST` (default `localhost:11434`) |
| `local/<model>` | Any OpenAI-compatible server (SGLang, vLLM, llama.cpp, LM Studio) | `--local-url` (or `base_url` in a player config), optional `LOCAL_API_KEY` (or `api_key_env`) |
| `openai-compatible/<model>` | Any OpenAI-compatible provider, from a [player config](#player-configs) | `base_url`, and the key in the variable named by `api_key_env` |

Examples: `openai/gpt-5.6-sol`, `anthropic/claude-sonnet-4-5`, `gemini/gemini-2.5-flash`,
`antigravity/gemini-3.8-flash`, `xai/grok-4.7`,
`ollama/qwen3`, `jev`, `jev/jev-1.13.0`. OpenAI model names are lowercased (`gpt-5.6-Sol` →
`gpt-5.6-sol`), as the subscription endpoint requires. A model name containing `/` goes
after the provider unchanged (`fastino/fastino/GLiDE`). Antigravity lists each Gemini model
per thinking level, so the config's `reasoning` is appended to the model id
(`antigravity/gemini-3.8-flash` at `low` asks for `gemini-3.8-flash-low`) and also sent as
`thinkingLevel`; the request is the `gemini/` one (same prompt, enum-constrained letter)
inside Antigravity's envelope. Each decision service's host can be
overridden: `TYPESAFE_BASE_URL`, `FASTINO_BASE_URL`, `OPENAI_DECISIONS_BASE_URL`,
`PERPLEXITY_BASE_URL`, `LIQUID_BASE_URL`, `CLEF_BASE_URL`, `OPEN_JEV_BASE_URL`,
`CYGNET_BASE_URL`, `GEMMA_BASE_URL`, `SUBQ_BASE_URL`, `CELERIS_BASE_URL`, `PPLX_LOCAL_BASE_URL` (`pplx-local`: pplx-decider-v1.1-27b served by `~/code/pplx-decider/server.py` on port 18097).

Missing credentials are reported at startup, before a match is created.

### Player configs

A league can take its roster from a JSON file (`jevgammon league --config FILE`), where each
player carries what a spec alone cannot:

```json
{
  "prompt_version": "bg-v2", "seed": 1, "order_seed": 2, "rounds": 3, "max_turns": 300,
  "clock": 300, "delay": 30, "note": "League 1",
  "players": [
    {"name": "Random", "spec": "random"},
    {"name": "DeepSeek V4.1 Flash (on)", "spec": "local/deepseek-v4.1-flash",
     "base_url": "http://127.0.0.1:8010/v1", "provider": "local-sglang", "quantization": null,
     "reasoning": "low", "request": {"chat_template_kwargs": {"thinking": true}},
     "max_tokens": 32768, "price": {"input_per_mtok": 0.1, "output_per_mtok": 0.4}}
  ]
}
```

- `provider` and `quantization` are logged with every decision (`provider` defaults to the
  spec's prefix; `quantization` may be null).
- `reasoning` is the reasoning effort (`low`, `high`, ...), sent as `reasoning_effort` to
  OpenAI-compatible servers. Left out, an OpenAI-compatible model answers without reasoning;
  subscription models then use their provider's default.
- `request` is merged into every request body (e.g. `chat_template_kwargs` to switch a
  model's thinking on or off, OpenRouter's `provider` pinning and `reasoning`); a `null`
  value removes a field the runner would send, e.g. `"response_format": null` for an
  endpoint without JSON-schema support (the letter is then unconstrained) or
  `"reasoning_effort": null` for a local model whose thinking has no effort knob.
- `letter_readout`: `prefill` (default) continues a prefilled `Answer:`, as SGLang and vLLM
  allow; `answer` reads the answer letter's log-probabilities from the ordinary response
  (after the reasoning, when on), for servers that start a new turn instead of continuing a
  prefill (Fireworks, Novita and Together through OpenRouter). The answer readout takes the
  last one-uppercase-letter token whose following tokens end the reply (some providers list
  the reasoning's tokens too, or leave tokens out); a reply without a letter, or a letter
  that differs from the token read, makes the decision invalid. `top_logprobs` lowers the
  20 alternatives asked per token (Fireworks allows 5; letters outside them get 0).
- `answer_prefix` replaces `Answer:` as the prefill when reasoning is off, e.g.
  `<think></think>Answer:` for a model whose chat template opens a reasoning block on every
  answer with no switch (LFM2.5).
- `price` (dollars per million input and output tokens) gives `turns.cost_usd` when the
  provider reports no cost (OpenRouter does, in `usage.cost`, and that is used); without
  either the cost is NULL. Reasoning tokens are logged in `turns.reasoning_tokens` when the
  provider reports them (Anthropic does not).
- `parallel` caps the player's decisions in flight, over all its league matches and both
  games of a round (more queue; the wait is logged in `retry_ms`, off the clock); default
  unlimited, and 4 for `jevgammon ask`. `max_matches` is how many league matches the player
  plays at once: default 4, unlimited for the local engines `random`, `safest` and
  `gnubg-weak` (one gnubg process per player answers its matches one decision at a time).
  `rpm` caps chat-model requests per minute, shared by every player of a `rate_group`
  (default: same base URL and spec, so both setups of one OpenRouter model share it), in
  leagues and `ask` alike; waits for a slot are logged in `retry_ms`. `note` is free text, and
  so is `device`, the hardware a self-hosted player's server runs on (shown on the league
  page).
- `base_url` is required for `openai-compatible/`, overrides `--local-url` for `local/`, and
  for a decision service (e.g. `clef`, `pplx-local`) overrides its URL and its environment
  variable (`CLEF_BASE_URL`, ...): the server root, without `/v1/systemone`.

The top-level settings override the command line; `seed`, `order_seed`, `prompt_version`
and `mirror_concurrent` are stored with the league, so `--resume` keeps them. The v3 rosters
are `leagues/league1.json`, `league2.json` and `league3.json`.

### Stored positions

`jevgammon ask --config FILE --positions FILE [--setup NAME]... [--out answers.db]
[--limit N] [--repeats N] [--max-cost USD]` sends stored positions (the format of
`positions/*.jsonl`) to players of a league config, through the same players, prompt, option
order and fallbacks as the leagues, and stores every answer in table `answers` (the per-decision
fields of `turns`, plus the setup, position id, repeat and error) with its requests in
`answer_exchanges`. The match context shown is the config's (round 1 of its rounds, its turn
limit and a full clock); the clock is not enforced. A rerun asks only what is missing or
failed; `--max-cost` stops a setup taking new positions once its answers cost more.
`tools/v3/smoke_positions.py` draws the 50 smoke-test positions (`positions/smoke.jsonl`)
and `tools/v3/smoke_report.py` turns the answers and GNUbg's equities into the smoke table.

### Prompt versions

Every decision logs its prompt version (`turns.prompt_version`). The texts are in
[`prompts/`](prompts/):

| Version | State | Options |
| --- | --- | --- |
| `bg-v2` | `prompts/bg-v2.md` (League #8's rules, strategy, opening table, match rules), then the turn | every play with its consequences |
| `bg-v2-notation` | as bg-v2 | notation only (`prompts/instructions-notation.txt`) |
| `bg-v2-history` | as bg-v2, plus the last 10 moves of the game before the dice (League #13's format) | as bg-v2 |
| `nack-v2` | `prompts/nack-v2.md`: bg-v2 without the opening table, for Nackgammon and the opening control | as bg-v2 |

bg-v2 reproduces League #8 exactly: a unit test renders a stored League #8 request
(`src/players/testdata/league8_request.json`, from `league.db`) and compares the state,
instructions, and every option text. `jevgammon render --order-seed N [--prompt-version V]
[--input FILE]` prints what a model is sent for stored positions: one JSON line in per
position (`position` as in `turns.position`, `dice`, optional score, round, turn, clock and
history fields), one JSON line out with the state, instructions, letter prompt, options in
the seeded order, and position key.

### What the models see

Every player gets text in this order. Earlier games of the match are not described:

1. The version's rules text with this match's rounds, turn limit, and clock filled in (the
   turn-limit and clock rules are dropped when the match has none).
2. **Score**: both scores and whether it leads or trails, round and game number.
3. **Time**: the turn number and the turn limit, the delay for this decision, and both
   players' bank left in this game.
4. **Position** from its own side (you move from 24 toward 1 and bear off past 1):
   checkers, bar, borne off, pip counts, and the **race**: the pip lead and whether the
   checkers are still in contact. bg-v2-history adds the **last 10 moves** of this game,
   oldest first, both sides, in its own numbering.
5. **Dice**, then the question "Which of the following moves makes a point in front of
   the opponent's checkers, or reduces your single pieces, or gets you closer to your
   home?".
6. **Legal plays** in the seeded option order, each in standard notation (`bar/22 13/11*`,
   `6/off`, `*` = hit) followed (except in bg-v2-notation) by what the position looks like
   after it, computed exactly in `src/players/prompt.rs`: checkers hit, points newly made,
   blots left and how many of the opponent's 36 rolls can hit one of them, points held and
   how many in the home board, longest prime, and both pip counts.

**Option order.** The plays are shown in a fixed random order per position, never in
move-generation or engine order: a Fisher-Yates shuffle driven by SplitMix64, seeded with
the first 8 bytes of SHA-256(`"{order_seed}:{position_key}"`), where the position key is
GNUbg's position ID, the dice high then low, and the side to move
(`4HPwATDgc/ABMA:21:white`). `src/players/order.rs` and its Python twin `tools/v3/order.py`
share the test vectors in `tools/v3/order_vectors.json`. `turns.option_order` stores the
order and `turns.letter` / `turns.chosen_position` where the chosen play was shown.

How they answer:

- **Chat models** get Cygnet's letter prompt: system prompt `prompts/letter-system.txt`,
  user message = items 1-5, the instructions (`prompts/instructions.txt`), the options
  lettered A, B, C..., and "Answer with the letter of exactly one option, and nothing
  else:". The answer is constrained to the option letters (JSON schema enum; Gemini an
  enum MIME type).
  - **OpenAI-compatible servers** return letter probabilities. With reasoning on, request 1
    lets the model reason (`reasoning_effort`, answer constrained to the letters); request 2
    sends the conversation back with the reasoning in `<think>` tags and a prefilled
    `Answer:` (`continue_final_message`), `max_tokens` 1, `logprobs` and 20
    `top_logprobs`, and the option letters' probabilities (summed over surface forms such
    as ` C`, normalised over the option letters) are stored; the most probable letter is
    played. Reasoning off is request 2 alone. A server that returns no logprobs falls back
    to the constrained letter, stored as `probability_source = 'choice_only'` (the chosen
    play gets probability 1), and later decisions skip the logprobs request.
  - **Subscriptions** (OpenAI, Anthropic, Gemini) return no probabilities: one constrained
    letter, choice only, at the configured reasoning effort.
- **Decision models** get items 1-5 as a string in `state` (OpenAI's Decisions API: in
  `input`) and one `choice` question whose options are the legal plays in the seeded order,
  keyed by notation, with the option text as description; their probability for every
  option is stored (`probability_source = 'decision'`).
- **Long play lists:** each player has an option limit: 26 letters for chat models, 255
  for hosted decision services, 110 for Clef, 26 for Cygnet and Gemma, 25 for the local
  Decider v1.1. Longer lists are split into equal groups, a winner is picked per group,
  then among the winners; `turns.group_size` records the group size.
- **Invalid answers** (a reply that names no option, a letter outside the options, a
  refusal) are not repaired or re-asked: the runner plays a uniformly random legal play,
  seeded per decision, and records `decided_by = 'fallback'`, `invalid = 1`.
- **Network and server errors** (connection failures, HTTP 408, 429, 5xx) are retried up to
  3 times with backoff (2, 4, 8 s; after a 429, 15, 30, 60 s; `Retry-After` can lengthen a wait
  up to 60 s). The time
  spent is logged in `turns.retry_ms` and not charged to the clock. Any other failure, or
  running out of retries, aborts the match; a league resumes it later from its last
  stored turn (see [League](#league)).

### Clock

Thinking time follows the Simple Delay method of the WBGF Tournament Rules (section 3.5):
each decision first gets `--delay` seconds free (default 30), which do not accumulate;
only time beyond that comes out of the player's bank of `--clock` seconds (default 300)
for the game. Both banks are full again at the start of every game, including the second
leg of a round. A model that answers within the delay at its normal pace never touches
its bank, and the bank absorbs the occasional slow decision. Forced moves, turns with no
legal move, and the pause between moves are free, and so is the time spent on HTTP
retries: it extends the deadline and is not taken from the bank, and so is a wait for one
of the player's request slots (`parallel`). A resumed match restores each bank from the
last stored turn's `clock_ms`; the time of a decision cut off in flight is not charged.

Unlike WBGF, where running out of time loses the match, an empty bank loses only the
game: the request is abandoned, the turn is recorded with `decided_by = 'timeout'`, and
the opponent wins the game for 1 point (`games.result = 'timeout'`), whatever the
position.

The models know about the clock: the rule is part of the rules they get, and every
request shows the delay and both banks.

### Turn limit

WBGF rules play every game to completion, but two models that hit each other's blots at
every chance can keep a game going indefinitely (a test game passed 1,100 turns). So a
game still running after `--max-turns` turns (default 300, both sides counted) ends there:
the side with the lower pip count wins a single game for 1 point, and with equal pip
counts the side due to roll next wins. It is recorded as `games.result = 'turn_limit'`.
Models see the turn number and the limit in every request.

### Latency

Models run with their provider's default settings unless a player config sets `reasoning`. Reasoning models can be slow. On a
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

The Google Antigravity login is OMP's (`/login` in omp): its `google-antigravity` row in
`~/.omp/agent/agent.db` is read read-only and never written. Google does not rotate the
refresh token, so an expired access token is refreshed with Antigravity's OAuth client
(the installed-app client OMP uses; kept out of the repository because GitHub push
protection rejects Google OAuth client credentials) from `ANTIGRAVITY_OAUTH_CLIENT_ID` and
`ANTIGRAVITY_OAUTH_CLIENT_SECRET` (in `~/.keys` for the league scripts), and cached in
`~/.local/state/jevgammon/google-antigravity.json` (mode 0600); the freshest of the two is
used. Without those variables a player runs while OMP's own token is fresh.

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
the dashboard shows it in the league history. `--config FILE` takes the roster and
settings from a [player config](#player-configs) file instead of `NAME=SPEC` arguments;
`--prompt-version` and `--order-seed` set the prompt version and option-order seed, stored
in `leagues.prompt_version` and `leagues.order_seed` (a league stored before versions
existed resumes with `bg-v2-history`, the prompt the runner then sent).

- **Fixture:** drawn from the league seed (`--seed`, random by default) by the circle
  method on a shuffled entry list: with 8 models, 7 matchdays of 4 matches, every model
  playing once per matchday (an odd count gives one model a bye each matchday). Which model
  is `model1` (white in the first game of every round) is drawn per match; the opening roll
  then decides who moves first, and the second game repeats the rolls with seats swapped,
  so the other model moves first with the same roll.
- **Matches** use the normal format (`--rounds`, `--clock`, `--delay`, `--max-turns`). A
  match starts as soon as both its models are below their `max_matches` (default 4, local
  engines unlimited), in fixture order: earlier matchdays get the free places first, and
  nobody waits for the rest of a matchday to finish. Every match has its own seed, derived
  from the league seed and the fixture, so results do not depend on what runs at once.
- **Mirror games at once:** with `--mirror-concurrent` (`"mirror_concurrent": true` in the
  config; stored in `leagues.mirror_concurrent` and printed in the league's header line) the
  two games of a round are played at the same time, and both show the score at the start
  of the round. Without it (the default, and League 1) game 2 starts after game 1 and shows
  the score after it. Rounds stay one after the other either way, since whether another
  round is played depends on the score. Turns, dice, events and scores are recorded the
  same way; the round's score is stored when both games have finished.
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
- **Failed matches:** a match that fails (a provider outage that outlasts the HTTP
  retries, an account out of credit, a warm-up that never answers) is deferred: the error
  and time go to `league_matches.error` and `failed_at`, and the model to blame (the one
  whose request failed) backs off: none of its matches starts for 2 minutes, doubling with
  every failure in a row up to 1 hour, reset when one of its matches finishes. A failure no
  model is to blame for backs off only that match. Every other match goes on. When only
  deferred matches are left the league waits for the next backoff to end and tries again,
  logging what waits and why, so topping up credit later lets it finish by itself.
  Playoffs start only once every fixture has finished; a failing playoff match is retried
  the same way. A model whose client cannot be built (a missing key, say) is tried again
  every 30 s while its matches wait.
- **Resuming:** a match cut off part-way (a failure, Ctrl-C or SIGTERM, a killed process, a
  reboot) keeps its match id and resumes from its last stored turn: the stored games count
  as played, and the unfinished game is replayed from the stored turns, checking every
  roll, position and play against the match seed, which restores the board, side to move,
  turn number, move history, banks, and the position in the dice stream, so the remaining
  rolls are those of an uninterrupted match. A decision in flight at the cut is asked
  again. Ctrl-C and SIGTERM stop the league cleanly (running matches are marked `aborted`
  with the error `cancelled`, the heartbeat is cleared); `--resume <id>` continues.

The table is printed each time every match of a matchday has finished, then the final
table and ranking.

### Adding a player later

A player that could not play at the start (no key yet, say) can join a running or finished
league and play only its own matches:

```sh
./jevgammon league-add --db v3.db --league 1 --player "Jev 1.13.0=jev/jev-1.13.0"
./jevgammon league-add --db v3.db --league 1 --config leagues/league1.json --name "Jev 1.13.0"
./jevgammon league-add --db v3.db --league 1 --entry '{"name": "Jev 1.13.0", "spec": "jev/jev-1.13.0"}'
```

- The player's client is built first, so a missing key fails here, not mid-league.
- The entry is appended to `leagues.models`, with one fixture against every current player
  (baselines and anchor included) on a new matchday after the last. Which side is `model1`
  is drawn from the league seed and the two names; each match seed is
  `derive_seed(league seed, label)`, the rule of the original fixture. The prompt version and
  option-order seed stay the league's.
- The league note gets "NAME added on DATE.", and the addition (time, harness commit, the
  entry and its sha256, the fixtures) is appended to `freeze/league<ID>-additions.json`
  (`--freeze-log` to change it).
- Playoffs wait until every fixture, added ones included, has been played. Playoffs played
  before the addition are kept but marked stale (stage `playoff-stale`, label suffixed
  `[stale <time>]`); the league is set running again and plays off afresh.
- **Running leagues** pick added players up by themselves: a league process re-reads the
  roster and fixtures every 30 s and signs `leagues.heartbeat_at`, and `league-add` says
  whether such a process holds the league. A runner older than this feature does not pick
  up; `league-add` then says so (it sees recent turns but no heartbeat): let it finish or
  stop it with Ctrl-C, then `league --resume` plays the added matches. `league --resume`
  refuses while another process is playing the league.

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
- **League on view:** header with rules and seed (plus the prompt version and option-order
  seed for leagues that stored them), table (`‹` `›` step through the finished leagues and
  the live one), per-model decision stats, the fixture with results (a failed match waiting
  for its model's backoff shows `deferred`, with the error and time on hover), and recent
  games. The
  model stats list each player's spec, provider and quantization; decisions, mean and
  longest decision time, hit share, **Invalid** (`decided_by = 'fallback'`: the answer named
  no option and a random legal play was made) and timeouts; on databases with the
  per-decision columns also the share of decisions with probabilities
  (`probability_source` set), the mean request time (`request_ms`, retries excluded) and the
  total cost (`cost_usd`). Older databases show the page without those three columns.
- **Live:** while the league is live, every running match shows its board and last move
  (with the games of a round played at once, the game that moved last);
  `«`, `»` and `⏮ round start` step through the rolls of the current round, `live` returns
  to the game in progress, and `context` shows what was sent to the model for that roll and
  its answer, with the decision's letter, probability source, request time, cost, provider,
  quantization and prompt version when recorded (local players such as baselines and gnubg
  send no request, so they show none).

`--league <id>` picks the league shown by default (otherwise the latest); `--host` defaults
to `0.0.0.0`, so the page is reachable from the LAN without authentication.

**Pause / Resume (both leagues).** With `--control tools/v3/league_control.sh` the header
shows a button: `Pause (frees GPUs)` while League 1 runs, `Resume` while it is paused, and a
spinner while either is under way, with the state, since when and the last message beside
it. Each asks for confirmation. `tools/v3/league_control.sh pause [all]|free|resume|status`
does the work and can also be run by hand. The servers it handles on this machine (from
2026-10-19 22:26 UTC): GPU 0 Gemma 4 31B (replica + proxy), GPU 1 Qwen3.8-27B (Decider v1.2
27B once Qwen's matches are played), GPU 2 LFM2.5-24B-A2B, all League 2 except Decider; GPU 3
League 1's Open-Jev, Winnow-12B and Decider Flash v1.2.

- **pause** sends SIGINT to the `league1` and `league2` systemd user units (the runners
  stop; unfinished matches resume from their last stored turn), waits until both are
  inactive, notes which GPU 0-2 servers were up (`league_control.servers`) and stops them.
  GPU 3's servers keep running; `pause all` stops them too. About a minute.
- **free** is pause (GPUs 0-2 only) followed by starting `league1` and `league2` again, so
  both leagues play on with GPU 3, the DGX Sparks and the APIs while GPUs 0-2 are free;
  matches of the stopped local models are deferred and retried with back-off.
- **resume** starts the GPU 3 servers that are down, then the GPU 0-2 servers the last pause
  noted (each start waits until it answers), checks Gemma answers a chat request, then starts
  `league1` and `league2` (`run_league1.sh`, `run_league2.sh`, which resume them). About
  4 minutes. The decision servers on the DGX Sparks are not touched.
- All are idempotent, hold `league_control.lock` (a second click is refused while one runs)
  and log to `league_control.log`; `status` prints one JSON line (`state` of League 1:
  running, pausing, paused, resuming or error; `league2`: its runner's state).

The page runs them in a transient systemd user unit (`league-control`), so a pause or resume
carries on if the page or the server goes away. The server accepts `POST /api/control` only
from `127.0.0.1` and `192.168.1.0/24` and only with the `X-League-Control` header the page
sends (no other authentication); the database stays read-only.

```sh
setsid nohup python3 tools/league_web.py --db v3.db --port 8095 --host 0.0.0.0 \
  --control tools/v3/league_control.sh >> league_web.log 2>&1 < /dev/null &
```

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
| `matches` | models, seed, planned and played rounds, clock bank and delay seconds (NULL = off), turn limit, score, winner (`1`, `2`, or NULL for draw), status `running\|finished\|aborted` (an aborted league match resumes, back to `running`), error (the last stop), prompt version, option-order seed, harness commit and dirty flag |
| `games` | round, leg, white player, dice seed, opening roll, winner, result (`single\|gammon\|backgammon\|timeout\|turn_limit`), points, turn count |
| `turns` | side, player, dice, position before the move (JSON, white's perspective), number of legal plays, chosen index, move (mover's numbering), `decided_by` (`model\|forced\|no_move\|fallback\|timeout`; `fallback` = invalid answer, random play), latency, tokens, mover's bank left after the turn (`clock_ms`); per decision: `prompt_version`, `harness_commit` (`git rev-parse HEAD` at startup) and `harness_dirty`, `provider`, `quantization`, `option_order` (JSON: legal-play index shown as option k), `letter` and `chosen_position`, `probabilities` (JSON aligned with `option_order`), `probability_source` (`logprobs\|decision\|choice_only`), `request_ms`, `retry_ms`, `cost_usd`, `invalid`, `group_size`, `reasoning_tokens` |
| `exchanges` | every model request body, reply text, rejection reason, latency; one row per request |
| `leagues` | seed, rounds, clock bank and delay, turn limit, entrants (JSON player configs: `{name, spec, ...}`), status, final ranking, note (`--note`), prompt version, option-order seed, `mirror_concurrent` |
| `league_matches` | stage (`league\|playoff`), label, matchday, model names, seed, `match_id` (resumed until it finishes), last failure `error` and `failed_at` |

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
| `src/runner.rs` | match flow, mirrored legs (one after the other or at once), resuming from stored turns, tie-break round, pacing and pause |
| `src/players/` | prompt versions and the letter prompt (`prompt.rs`, texts in `prompts/`), seeded option order (`order.rs`), LLM providers, decision services (System One, OpenAI Decisions), invalid-answer fallback and group splits (`mod.rs`) |
| `src/league.rs` | league fixture, match limits, deferral and backoff, table, playoffs, resume |
| `src/auth.rs` | subscription credential stores and refresh |
| `src/http.rs` | retries and backoff |
| `src/db.rs` | SQLite schema and writes |
| `src/ui.rs` | ratatui interface |
