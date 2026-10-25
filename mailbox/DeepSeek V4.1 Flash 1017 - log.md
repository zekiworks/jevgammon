# DeepSeek V4.1 Flash 1017: log

Oct 24, 2026 · late League 2 entry, approved by Can: "DeepSeek V4.1 Flash 1017 (off)" and "(on)". Can skipped the separate 50-position smoke test. Instead, the first league decisions were watched live (below).

## Setups

- Model `deepseek/deepseek-v4.1-flash-1017` on OpenRouter, pinned to DeepSeek first-party (`provider: {order: [deepseek], allow_fallbacks: false, require_parameters: true}`, usage included). The existing DeepSeek V4.1 Flash (off)/(on) stay on Fireworks. `turns.provider` records the provider of each decision (`openrouter:deepseek`).
- Price: $0.15/M input, $0.60/M output. Source: OpenRouter endpoint list, 2026-10-24.
- Otherwise the same settings as DeepSeek V4.1 Flash (off)/(on): (off) sends `reasoning.enabled false`; (on) uses reasoning effort `low`; letter read from the answer, `top_logprobs` 5, parallel 8, rpm 18.
- Full entries: `leagues/deepseek-1017-entries.json`; join log: `freeze/league2-additions.json`.
- **Provider trains on paid prompts; allowed by Can, 2026-10-24.** Until Can changed the OpenRouter privacy setting, every request got 404 ("Filter by Guardrails removed deepseek"). Nothing was billed for those requests.
- **No JSON schema.** DeepSeek's endpoint does not support structured outputs, so with `require_parameters` OpenRouter still filtered it out (404, "Filter by Parameters"). Both setups therefore send `request.response_format: null`: no `response_format`, and the answer letter is read from the free answer and its logprobs. The Fireworks setups keep the schema. A 6-position test (`jevgammon ask`, `positions/smoke.jsonl`) gave 12/12 valid answers with probabilities, for $0.02. The change went into `v3.db` at about 20:30 UTC, before any league decision of these setups.

## Timeline (UTC)

- 18:39: `league-add` into League 2: 17 fixtures each, plus (off) v (on).
- 18:40-20:29: every request got 404, as described above; the runner backed off.
- ~20:30: `response_format` set to null; League 2's runner restarted (running matches resumed from their stored turns).

## First live decisions (to 20:45 UTC)

| Setup | Decisions | Requests (incl. group splits) | Errors | Without probabilities | Provider | Reasoning tokens per request (mean / min) | Tokens in / out per decision | Median s per decision | $ per decision (OpenRouter `usage.cost`) |
|---|---|---|---|---|---|---|---|---|---|
| (off) | 108 | 137 | 0 | 0 | DeepSeek (all) | 0 / 0 | 4,158 / 1 | 37.5 | $0.00026 |
| (on) | 76 | 88 | 0 | 0 | DeepSeek (all) | 3,686 / 53 | 3,656 / 4,271 | 50.4 | $0.00278 |

Every answer was valid, with logprob probabilities.

## Cost projection (League 2, 18 matches each)

Decisions per match come from the 16 finished League 2 matches of the matching Fireworks setup, resampled 5,000 times over 18 matches. Cost per decision is the measured rate above.

| Setup | Decisions p50 / p95 | Cost p50 / p95 |
|---|---|---|
| (off) | 2,057 / 2,204 | $0.53 / $0.56 |
| (on) | 2,198 / 2,376 | $6.10 / $6.60 |
| **Both** | | **$6.63 / $7.16** |
