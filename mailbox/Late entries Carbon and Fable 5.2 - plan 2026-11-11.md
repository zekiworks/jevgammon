# Late entries Gemini 4 Carbon (high) and Claude Fable 5.2 (max) - plan 2026-11-11

Ümit via Zeki #4676. Prepared, nothing started. Scripts: `tools/v3/late-carbon-fable` (branch `late-carbon-fable`).
Site entries (held): branch `carbon-fable-site`.

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

## Route smoke (one position each, `jevgammon ask --limit 1 --retries 0`, workspace/late-carbon-fable/smoke.db)

| | Carbon, Antigravity subscription | Fable 5.2, Claude subscription |
|---|---|---|
| Sent | gemini-4-carbon-high, thinkingLevel high | claude-fable-5-2, output_config.effort max, max_tokens 32,000 |
| Echoed | modelVersion gemini-4-carbon, finishReason STOP | model claude-fable-5-2, msg_011Cgw6WLQ1PfYa31bH1kGAh, stop_reason max_tokens |
| Tokens | 3,981 in, 19 out + 8,462 thinking | 4,941 in, 32,000 out (all thinking) |
| Time | 102 s | 349 s |
| List-price equivalent | $0.0928 | $1.3195 |
| Answer | M (13/9* 9/8) | none: invalid, random play |

Billed $0 (subscriptions). OMP has since paused the Antigravity route (account risk): Carbon plays on OpenRouter, pinned
to Google AI Studio (`player-carbon.json`). Fable 5.2 at max thinks past 32,000 tokens: `player-fable.json` sets
max_tokens 128,000 (the model's limit; not yet exercised).

## Cost (no calls), ~2,082 decisions (109.6 per late-entry match x 19)

- Carbon (high), OpenRouter google-ai-studio, $2/$10 through 30 Nov ($4/$20 from 1 Dec): $0.093 per decision (smoke)
  -> ~$193 (Argon (high)'s league mean, $0.086: $179); from 1 Dec ~$386. Stage 1 (10 opponents) ~$100. ~102 s per
  decision, 2 in flight: ~30 h.
- Fable 5.2 (max), $8/$40 (Claude subscription $0; OpenRouter the same list price): at least $1.32 per decision ->
  at least ~$2,750; up to $5.16 per decision at 128,000 output tokens. At least 349 s per decision: ~100 h at 2 in
  flight. Fable 5.1 (high)'s league record: 1,367 output tokens per decision; this is 23x that or more.
- OpenRouter balance 2026-11-11 12:05 UTC: $76.54 (floor $40). Google API: out of credit (402, turkce #4686).

## Start (after Main merges the site branch and gives the go)

```
cd ~/code/jevgammon && CARGO_TARGET_DIR=target/carbon-fable cargo build --release --manifest-path ~/code/jevgammon-carbon-fable/Cargo.toml
systemd-run --user --unit=late-carbon --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/start.sh carbon
systemd-run --user --unit=late-fable --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/start.sh fable
# stage 2 (8 local opponents), once start.sh has exited and Main hands over a GPU:
systemd-run --user --unit=late-carbon-locals --working-directory=/home/cbasaran/code/jevgammon \
  -E PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin -E OPP_GPU=<n> -E RES=<reservation> \
  /home/cbasaran/code/jevgammon-carbon-fable/tools/v3/late-carbon-fable/locals.sh carbon
```

start.sh refuses to start (exit 3) while the Claude lane (improve-subs-claude, improve-claude-wait) runs, for fable,
and pauses the entry if it starts; it stops at a route limit (429), at OpenRouter < $40, at paid opponents >= $5, at
Carbon's own cost >= $250 (OWN_CAP), on blocked pairs, after 48 h.
