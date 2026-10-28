# OpenRouter usage, 28 October 2026

Question: during the four DeepSeek V4.1 Flash 1017 (on) gap matches, OpenRouter usage rose $5.48, but the matches cost $1.744. Where did the other $3.74 go?

Answer: the Turkish benchmark (`~/T7/code/data/eval/benchmarks/Turkce`, its own omp session) ran GLM-5.3 and Kimi K3.1 Pro through OpenRouter with the same key, from 14:33 to 15:07 UTC. Those runs cost about $3.72. That accounts for the gap.

## Window

- Matches #754–757 (v3.db) started at 11:44:00 UTC. They finished at 12:22:34 (#755), 12:45:41 (#754), 12:47:35 (#757) and 15:10:52 UTC (#756).
- `smoke/deepseek-1017-on-budget.db` has 572 settled attempts from 11:44:00 to 15:06:55 UTC, totalling $1.744379 (budget cap $3.60).
- The window is therefore 11:44–15:11 UTC, not 09:30–13:30.

## What the key shows

The key is `OPENROUTER_API_KEY` from `~/.keys`. Nothing was changed.

| Endpoint | Works with this key? | Result (read about 15:29 UTC) |
|---|---|---|
| `/api/v1/key` | yes | usage_daily $5.506147, weekly $18.24, monthly/total $118.25; limit $200, $81.75 left |
| `/api/v1/credits` | yes | total_credits $120, total_usage $118.252939 (same as this key's total, so this key accounts for all account usage) |
| `/api/v1/activity` | no | 403 "Only management keys can fetch activity for an account". It needs a provisioning/management key. I did not try to get one. |
| `/api/v1/generation?id=` | needs a generation id | Our databases don't store generation ids, so I couldn't look anything up per request. |

So the per-model daily breakdown from OpenRouter itself is not available with this key. The table below comes from our own records. Together they explain the $5.506 daily total to within about $0.02.

## Usage on 28 Oct (UTC) by model and time

| Time (UTC) | Model / endpoint | Project | Requests | Cost (USD) | Source |
|---|---|---|---|---|---|
| 00:37–02:00 | deepseek/deepseek-v4.1-flash-1017 (off), DeepSeek endpoint | jevgammon, match #752 (before the window) | 68 turns | 0.0229 | v3.db turns.cost_usd |
| 11:44–15:10 | deepseek/deepseek-v4.1-flash-1017 (on, low), DeepSeek endpoint | **jevgammon gap matches #754–757** | 572 | **1.7444** | deepseek-1017-on-budget.db (v3.db turns: 0.4378 + 0.2801 + 0.6134 + 0.4131 = 1.7444) |
| 14:33:28 | deepseek/deepseek-v4.1-flash-1017 | Turkce benchmark run 309 | 0 (failed at start) | 0 | Turkce benchmark-results.sqlite |
| 14:33:28–14:33:36 | moonshotai/kimi-k3.1-pro (none), Moonshot mxfp4 | Turkce run 308 (32-question smoke) | 2 | 0.0275 | benchmark-results.md run 308 |
| 14:33:28–14:33:44 | z-ai/glm-5.3 (low), Fireworks | Turkce run 307 (32-question smoke) | 2 | 0.0265 | benchmark-results.md run 307 |
| 14:52:06–14:55:37 | moonshotai/kimi-k3.1-pro (none), Moonshot mxfp4 | Turkce run 315 (full, 2,198 questions) | 138 | 1.8758 | benchmark-results.md run 315 (778,642 in, 31,856 out at $2/$10 per 1M tokens) |
| 14:52:06–15:07:25 | z-ai/glm-5.3 (low), Fireworks (mostly the spot endpoint) | Turkce run 314 (full, 2,198 questions) | 138 | ≈1.79 billed (2.556 at standard rates) | benchmark-results.md run 314; see note |

Totals:
- Ours (jevgammon): 1.7673 for the day, of which 1.7444 is in the window.
- Turkce benchmark: ≈3.72.
- All together: ≈5.49, against the key's usage_daily of 5.506.

Note on GLM-5.3: the recorded `cost_usd` of $2.556 prices run 314's tokens at Fireworks' standard rates ($1.40 input, $0.26 cached, $4.40 output). The Turkce harness's price table, edited today, says OpenRouter billed 135 of the run's 138 requests at Fireworks' **spot** rates ($0.98 input, $0.182 cached, $3.08 output). At spot rates the run costs:

- 532,386 uncached input tokens × $0.98/1M = $0.522
- 25,563 cached tokens × $0.182/1M = $0.005
- 410,088 output tokens × $3.08/1M = $1.263
- Total ≈ $1.79

With that figure the Turkce total is ≈$3.72, which matches the unexplained $3.74.

## Attribution

- **Ours: $1.744.** These are the four DeepSeek V4.1 Flash 1017 (on) gap matches, 11:44–15:10 UTC. The budget ledger and v3.db turns agree to the cent. No other jevgammon OpenRouter calls happened in the window:
  - The other seats in these matches were GPT-6.1 Sol (ChatGPT subscription) and LFM2.5 (local vLLM).
  - The newest smoke DB, `astra-high-smoke.db` (14:46), is a GPT-6 Astra run, which is not on OpenRouter.
  - The other smoke and budget ledgers were last written before today (nack-paired.db at 00:59).
- **The other $3.72 is the Turkish benchmark** (`~/T7/code/data/eval/benchmarks/Turkce`, omp session `-T7-code-data-eval-benchmarks-Turkce`). Evidence:
  - It ran OpenRouter runs 307/308 (smokes) and 314/315 (full GLM-5.3 and Kimi K3.1 Pro runs) between 14:33 and 15:07 UTC. They overlap only match #756's last stretch.
  - Its `run_openrouter_*.sh` scripts were written at 14:22–14:29 UTC.
  - Its harness reads the same `OPENROUTER_API_KEY`.
  - The agent bus has no posts about OpenRouter today. The only other projects active on the machine (hilde redesign, compactor, ai-toolkit, tb-next, analysis) showed no OpenRouter runs in the window.
- **Unknown:** about $0.02, within the rounding of the GLM spot/standard split. OpenRouter's own per-model breakdown would need a management key (`/api/v1/activity`).
