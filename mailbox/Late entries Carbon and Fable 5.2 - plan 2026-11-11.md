# Late entries Gemini 4 Carbon (high) and Claude Fable 5.2 (max) - plan 2026-11-11

Ümit via Zeki #4676. Prepared, nothing started. Scripts: `tools/v3/late-carbon-fable` (branch `late-carbon-fable`).
Site entries (held): branch `carbon-fable-site` (Carbon class on its standard $4.00: Flagship, as Argon, Ümit #4399).

## Identity

| Setup | Model id | Levels (maker) | Highest | Source |
|---|---|---|---|---|
| Gemini 4 Carbon (high) | `gemini-4-carbon` | low, medium (default), high | high | Google, 10 Nov 2026 |
| Claude Fable 5.2 (max) | `claude-fable-5-2` | low, medium, high (API default), xhigh, max | max | Anthropic, 9 Nov 2026 |

- https://blog.google/innovation-and-ai/technology/developers-tools/gemini-4-carbon-developers/ (10 Nov): "Starting
  today, developers can build with Gemini 4 Carbon"; paid API tier, and Google AI Ultra subscribers in AI Studio and
  Antigravity.
- https://ai.google.dev/gemini-api/docs/thinking: "gemini-4-carbon | On (medium) | low, medium, high";
  https://ai.google.dev/gemini-api/docs/models: "Model code gemini-4-carbon".
- https://www.anthropic.com/claude-fable-and-mythos-5-2 (9 Nov): "$8 per million input tokens and $40 per million output
  tokens".
- https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2: "Claude Fable 5.2 | claude-fable-5-2";
  "Effort: all five effort levels: low, medium, high, xhigh, and max. The API default is high."; "Reserve max for
  measuring the model's ceiling and for the rare task where time and tokens don't matter."; 128k max output tokens.

## Measured: $0 tests on the subscriptions (no money moved)

Dollar figures here are list-price equivalents of $0 subscription requests, not spending.

| Test | Route, request | Position | Tokens | Time | Answer |
|---|---|---|---|---|---|
| Carbon smoke | Antigravity, our runner: gemini-4-carbon-high, thinkingLevel high; echoed modelVersion gemini-4-carbon | smoke-0001 | 3,981 in, 19 out + 8,462 thinking | 102 s | M (13/9* 9/8); list-price equivalent $0.093 |
| Fable smoke | Claude subscription, our runner: claude-fable-5-2, output_config.effort max, max_tokens 32,000; echoed claude-fable-5-2 (msg_011Cgw6WLQ1PfYa31bH1kGAh) | smoke-0001 | 4,941 in, 32,000 out (all thinking), stop_reason max_tokens | 349 s | none (invalid, random play); list-price equivalent $1.32 |
| Fable via Claude Code | `claude --print --model claude-fable-5-2 --effort max --system-prompt-file <our system> --tools "" --output-format json`, our user prompt on stdin (session 1ed824ab-0a50-4be5-9eaf-a25afa210f51) | smoke-0004 | 4 separate attempts, each capped at 32,000 output tokens: the first, then 3 automatic continuations by Claude Code after each max_tokens stop (num_turns 4); 32,000 out (thinking) each, 128,000 summed (127,999 thinking); 20,416 in (cache write) | 1,395 s for the 4 | none: "API Error: Claude's response exceeded the 32000 output token maximum"; Claude Code's list-price figure $2.72 for the 4 |

Request shapes (Claude Code's captured on a local listener, nothing sent): Claude Code sends `max_tokens` 32,000,
`thinking: {"type": "adaptive"}`, `output_config: {"effort": "max"}`, `stream: true`, betas incl. `effort-2025-11-24`
and `interleaved-thinking-2025-05-14`. Ours: `max_tokens` 32,000, no `thinking` field (adaptive is the model's only mode),
`output_config: {"effort": "max", "format": <json_schema of the letter>}`, betas `claude-code-20250219,oauth-2025-04-20`,
not streamed. Neither sends a thinking budget (`budget_tokens`). Claude Code's own request thought past 32,000 on our
prompt in each of its 4 attempts, so the no-answer comes from the backgammon prompt at max, not from our request shape.
The 4 attempts are not one 128,000-token request and not evidence that a 128,000 cap would answer: each continuation
was a separate request under the 32,000 cap. Any future smoke must fix and record continuation behaviour (turn it off,
or count the attempts), so runner and Claude Code budgets are never mixed. The third allowed test (our runner with
Claude Code's shape) was not run, to spare the shared quota. Logic's and turkce's max runs (166-364 output tokens per
Math question; ~560 thinking per Turkish question) are other tasks.

Antigravity: OMP has paused the route (account risk) since the Carbon smoke; not used again.

## Extrapolated (not measured), ~2,082 decisions (109.6 per late-entry match x 19)

- Carbon (high) on OpenRouter pinned to google-ai-studio ($2/$10 through 30 Nov, $4/$20 from 1 Dec), paid: at the
  smoke's tokens, $0.093 per decision -> ~$193 (Argon (high)'s league mean $0.086: $179); from 1 Dec ~$386. Stage 1 (10
  opponents) ~$100. ~102 s per decision, 2 in flight: ~30 h. The OpenRouter request shape is not yet exercised by our
  runner (turkce: that route works).
- Fable 5.2 (max) at 32,000 output tokens: every decision ends without an answer (2 of 2 positions; the second over 4
  attempts of 32,000), so the entry cannot be played as set: at least $1.32 list price per decision and 349 s each,
  and no plays. Whether any larger cap answers is not known (never tested); at 128,000 a decision would cost up to
  $5.16 list price.
- OpenRouter balance 2026-11-11 12:05 UTC: $76.54 (floor $40). Google API: out of credit (402, turkce #4686).

## Decision for Ümit

Fable 5.2 at max does not answer a backgammon decision within 32,000 output tokens. Options: a larger output cap (a
paid or quota-heavy experiment of unknown length), or a lower effort (xhigh/high) as the entry's highest setting that
answers. Carbon (high) on OpenRouter is paid: a balance top-up alone is not approval; start.sh and locals.sh refuse
`carbon` without an explicit approval id (`start.sh carbon '#NNNN'`), and nothing starts it when credit arrives.

## Start (after Main merges the site branch and gives the go)

```
systemd-run --user --unit=late-carbon --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/start.sh carbon '#<approval>'
systemd-run --user --unit=late-fable --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/start.sh fable
# stage 2 (8 local opponents), once start.sh has exited and Main hands over a GPU:
systemd-run --user --unit=late-carbon-locals --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E OPP_GPU=<n> -E RES=<reservation> \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/locals.sh carbon '#<approval>'
```

Runner: target/carbon-fable/release/jevgammon (built from this branch's base, 9529596). start.sh refuses to start
(exit 3) while the Claude lane (improve-subs-claude, improve-claude-wait) runs, for fable, and pauses the entry if it
starts; it stops at a route limit (429), at OpenRouter < $40, at paid opponents >= $5, at Carbon's own cost >= $250
(OWN_CAP), on blocked pairs, after 48 h.
