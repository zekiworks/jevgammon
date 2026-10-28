# Nackgammon paired test: Gemini 4 Argon (low), estimate (2026-10-28)

For Can. **Not run: no Argon (low) call has been made. This waits for your go.** Method §10.14(h) (commit cbb9c87): Argon (on) is dropped, and Argon (low) is proposed instead as exploratory (no group, no primary comparison, M unchanged), under the same rules, including the 32,768-token output limit.

## Setup

- **Gemini 4 Argon (low)** is the stored setup "Gemini 4 Argon (off)" (v3.db `players.settings`, unchanged): `antigravity/gemini-4-argon`, `reasoning: "low"` (Antigravity model id `gemini-4-argon-low`, thinking level low), Antigravity subscription (Google AI Ultra, OMP's login), `parallel` 4, list price $2/$10 per M tokens (until 2026-12-01). It keeps its stored name, "Gemini 4 Argon (off)", in the paired test.
- **Output limit:** the Antigravity route sends no output limit. The provider's limit there is 32,768, as seen in Argon (on)'s smoke test, which matches the rule. Argon (low) never came near it in the league (at most 308 output tokens).

## Its League 3 logs (`v3.db`, valid matches, late-entry matches excluded)

| Decisions (model + fallback) | Invalid (fallback) | Input tok / dec | Output tok / dec (reasoning) | Max output | Request s, mean / max | Decisions with a retry | Off-clock s / dec | API-eq. $ / dec |
|---|---|---|---|---|---|---|---|---|
| 3,698 (2026-10-20 to 10-26) | **0** | 4,898 | 26.2 (0) | 308 | 5.75 / 66.6 | 268 (7%) | 0.13 | $0.0101 |

In the paired prompt the input is smaller. Gemini 3.8 Flash (low), on the same route and tokenizer, averaged 2,692 input tokens in `smoke/nack-paired.db`. Argon (low) is taken as about 2,690.

## Estimate

Money billed: **$0** (subscription). Dollar figures are the API list-price equivalent (not money). Central: 2,690 input and 26 output tokens per decision. High: the league's 4,898 input and 308 output tokens.

| Row | Decisions | API-eq., central | API-eq., high | Wall time at parallel 4, central / worst (2× for retries and slow days) | Expected invalid |
|---|---|---|---|---|---|
| Start: main 200 pairs, both sides | 400 | $2.26 | $5.15 | 10 min / 20 min | 0 (0 of 3,698 in the league) |
| Worst-case extension (+600 reserve) | +600 | $3.38 | $7.73 | 15 min / 30 min | 0 |
| **Total, up to 1,000** | **1,000** | **$5.64** | **$12.88** | **25 min / 50 min** | |

- **No smoke test is needed:** this exact setup has 3,698 league decisions with 0 invalid. If you want one anyway, it is 50 positions (about 2 min, about $0.30 API-eq.).
- **Subscription:** Antigravity runs one job at a time. Argon (off) is now playing its late-entry match against GPT-6 Astra (high) (match #762), and the subscription probe (RelabelSweep) waits for the Gemini subscription after that. Argon (low)'s paired run would come after both and run alone on Gemini.
- **No GPU and no OpenRouter.**

Waiting for Can's go.
