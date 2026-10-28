# Nackgammon: Gemini 4 Argon (high), cost and time estimate (2026-10-28)

Can's ask: add Gemini 4 Argon at thinking level **high** to the Nackgammon paired test, as was done for Terra (high). **Before any model call.** Nothing below has been run, and no model was called. The databases were opened read-only (`v3.db`, `smoke/nack-paired.db`, `smoke/antigravity.db`).

**Everything here is an estimate.** Argon has no Nackgammon answers yet. The figures come from Argon's real league logs in `v3.db`.

## What "Argon (high)" is

- **"Gemini 4 Argon (on)" already is high.** Its stored settings (`v3.db` players, `leagues/league3.json`) are `antigravity/gemini-4-argon`, `reasoning: "high"` ("thinking level high, Gemini's default"). The Antigravity model id is `gemini-4-argon-high`, and `thinkingLevel` high is sent in the request (`antigravity_model` in `src/players/llm.rs`). "Argon (off)" is `reasoning: "low"` (`gemini-4-argon-low`, which spends no reasoning tokens).
- Antigravity offers `gemini-4-argon-low`, `-medium` and `-high` (Antigravity probe, history://Antigravity). High is the highest level, and it is a different setting from medium.
- So **Argon (high) = Argon (on)'s settings**: Antigravity subscription (Google AI Ultra, OMP's login), list price $2/$10 per M tokens (until 2026-12-01; $4/$20 after that), `parallel` 4. It would use the paired run's prompts (bg-v3-nack / bg-v3-std-notable) and option-order seed, with its own setup name, e.g. "Gemini 4 Argon (high)" or simply "Gemini 4 Argon (on)". It would be the same kind of entry as "Gemini 3.8 Flash (low)" in `leagues/nack-paired.json`. **No effort multiplier is needed**, because the logs are already at this level.

## Status

**Exploratory.** It is added after the paired results were known. It is not a primary comparison, and it has no effect on the group results (M stays 5). Argon's original league is League 3 (frontier). Under §10.14(b), a setup added later "joins its original league's group" only when it was added because of the Cup roster, and this addition was not. So it is treated here as exploratory. **Whether it should count in the frontier group is Can's decision.**

## Argon: real league logs (`v3.db`, all on Antigravity)

| Setup | Decisions (model + fallback) | Input tok/dec | Output tok/dec (thinking) | Median / p90 / max output | Mean / max latency | Decisions with a retry | Invalid (fallback) | API-equivalent $/dec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Argon (on) = high | 1,770 | 4,993 | 6,561 (6,535) | 1,990 / 13,607 / 86,686 | 90.9 s / 1,997 s | 713 (40%), average 7.7 s, 3.6 h in total | **71 (4.0%)** | $0.0756 ($133.81 in total) |
| Argon (off) = low | 3,698 | 4,898 | 26 (0) | — / — / 308 | 5.9 s / 66.6 s | 268 (7%) | 0 | $0.0101 |

- **Latency follows output.** Throughput was steady at 63–84 tokens/s, so latency is set by thinking length, not by queueing. The output per decision of Argon (on) changed a lot by day: about 3,100–3,500 tokens on 10-20/21/23 (latency 46–55 s), then **14,800–24,700 on 10-24/25/26** (180–297 s, 366 decisions, about 19,600 and 235 s on average).
- **Invalid answers:** all 71 fallbacks came on those late days (71 of 366, 19%). Each was an empty reply after on average 41,400 thinking tokens, logged as "reply is not one of the letters". In the paired test such an answer counts as invalid.
- **Quota and rate limits:** `v3.db` exchanges and the league logs contain **no 429 or quota error for Argon**, and no Argon match was stopped or deferred. Retries happened without a logged error (only `retry_ms` was recorded, on 10-20/21/25), so their cause is unknown. From the Antigravity probe (rough, linear): the Gemini group shares a quota of about **$1,800 API-equivalent per week and about $450 per 5 hours**, used up in proportion to token cost.
- Input in the paired prompt: Gemini 3.8 Flash (low), with the same tokenizer and route, averaged 2,692 input tokens in `smoke/nack-paired.db`. Argon is taken as about **2,690**. In the 5-position Antigravity probe (bg-v2) Argon (high) used 3,907 input and 2,200 output tokens at 42.5 s.

**Used per decision:** central output 6,560 (the league mean, including fallbacks), latency about 91 s. Worst case: output 19,600 and latency 235 s (the late-day profile, which may fit the paired test's notable positions better), plus 5% for retries. API-equivalent cost: central 2,690 × $2/M + 6,560 × $10/M = **$0.071**; worst (2,690 × $2/M + 19,600 × $10/M) × 1.05 = **$0.21**. Smoke test (input about 3,900): central $0.073, worst $0.214.

## The three rows

**Money billed: $0 in every row** (Antigravity subscription). The dollar figures are the API list-price equivalent: **not money**. They also measure the quota used.

| Row | What | Decisions | Money | API-equivalent, central (not money) | API-equivalent, worst (not money) | Wall time, central / worst (parallel 4) | Share of weekly Gemini quota, central / worst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a | Smoke test: the 50 positions of `positions/smoke.jsonl`, bg-v2, the leagues' option-order seed, and the reference comparisons (Δ against Argon's own stored league/probe answers and against Gemini 3.8 Flash (low) / GPT-6.1 Sol (low); stored answers, no calls) | 50 | $0 | $3.7 | $10.7 | about 20 min / 50 min | 0.2% / 0.6% |
| b | Paired start: main 200 pairs, both sides | 400 | $0 | $28.5 | $84.6 | about 2.5 h / 6.5 h | 1.6% / 4.7% |
| c | Worst-case extension to 1,000 (+600 reserve) | +600 | $0 | $42.7 | $126.9 | about 3.8 h / 9.8 h | 2.4% / 7.1% |

a + b + c: $75 central, $222 worst, API-equivalent (not money). Time: about 6.5 h central and about 17 h worst. Single decisions took up to 33 minutes in the league.

- **Rate:** at parallel 4 that is about 2.6 decisions a minute (central) or 1 a minute (worst), which uses about $56–64 API-equivalent per 5 hours. That is well under the 5-hour limit of about $450, so the quota should not set the pace. Latency does. The weekly worst case is about 12% for a + b + c.
- **Quality risk:** expect 4% invalid answers centrally, and up to about 19% if the paired positions behave like the late-league ones. Row a will show which profile applies before b starts.

## Competition with the DeepSeek V4.1 Flash 1017 (on) gap matches

**None for money.** Argon runs on the Antigravity subscription, not the OpenRouter credit. The 4 DeepSeek gap matches (est. $2.39, worst $3.60) and Terra (high) keep the whole OpenRouter balance. The two can also run at the same time: different providers, and Argon needs no local GPU.

Waiting for Can's go.
