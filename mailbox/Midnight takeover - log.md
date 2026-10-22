# Midnight takeover - log

bariton's four GPUs, taken over at 00:00 UTC on 2026-10-22 by `tools/v3/midnight_takeover.sh`
(timer `midnight-takeover.timer`). Full log: `midnight-takeover.log`; smoke test output:
`smoke/takeover-*.log`, table `smoke/takeover-report.txt`.

## What happened

- 21:28 UTC: [00:00] GPUs free for us: 0 1 2 3
- 21:28 UTC: smoke tests in parallel: d3-turbo on GPU 0, Nemotron BF16 on GPUs 2,3 (24GB fallback on GPU 2)
- 21:30 UTC: d3: done
- 21:32 UTC: nemotron-bf16: failed (exit 1, see smoke/takeover-nemotron-bf16.log)
- 22:00 UTC: nemotron: done
- 22:00 UTC: smoke report: smoke/takeover-report.txt and smoke/part-a.json
- 22:00 UTC: [step 2] GPUs free for us: 0 1 2 3
- 22:02 UTC: DeepSeek V4.1 Flash ready after 121 s (http://127.0.0.2:8010/v1)
- 22:02 UTC: 20-request check: same top letter 19/20, max |dp| 0.310, median |dp| 0.0952, median latency 0.49s
- 22:02 UTC: league2 started: 5 of 136 matches left
- 06:14 UTC: takeover script exiting early (signal or error)

## Smoke test table

```
| Setup | Answers / failed / timed out | Invalid | Probabilities | Groups | p50 / p90 s | Retry+wait s mean / max | Tokens in / out / reasoning | $ per 1,000 | Error rate [95% CI] | Δ vs Gemini 3.8 Flash (low) [antigravity] [95% CI] | Δ vs Gemini 3.8 Flash (low) [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gemini 3.8 Flash (low) [antigravity] | 50 / 0 / 0 | 0% | none (choice only) | one request | 2.9 / 6.0 | 0.0 / 0.0 | 3244 / 276 / 273 | 3.47 | 13.6 [5.4, 24.3] | +0.0 [+0.0, +0.0] (n=50) | +5.0 [-2.9, +15.1] (n=50) |
| Claude Haiku 5.5 (low) | 50 / 0 / 0 | 0% | none (choice only) | one request | 1.4 / 1.6 | 0.0 / 0.0 | 4271 / 20 / 9 | 0.44 | 18.0 [9.1, 28.0] | +4.4 [-7.1, +15.2] (n=50) | +9.5 [+2.7, +17.7] (n=50) |
| Claude Haiku 5.5 (high) | 50 / 0 / 0 | 0% | none (choice only) | one request | 3.2 / 6.2 | 0.0 / 0.0 | 4271 / 526 / 515 | 0.69 | 21.1 [10.1, 33.9] | +7.5 [-0.6, +17.1] (n=50) | +12.5 [+3.0, +24.0] (n=50) |
| Claude Fable 5.1 (low) | 50 / 0 / 0 | 0% | none (choice only) | one request | 1.7 / 2.5 | 0.0 / 0.0 | 4271 / 82 / 71 | 46.83 | 11.7 [4.8, 20.5] | -1.9 [-12.7, +7.8] (n=50) | +3.2 [-0.7, +8.6] (n=50) |
| Claude Fable 5.1 (high) | 50 / 0 / 0 | 0% | none (choice only) | one request | 6.7 / 30.8 | 0.0 / 0.0 | 4271 / 719 / 708 | 78.66 | 9.0 [2.2, 18.5] | -4.5 [-9.2, -1.0] (n=50) | +0.5 [-6.6, +9.6] (n=50) |
| Mercury 3 (off) | 50 / 0 / 0 | 2% | none (choice only) | one request | 0.5 / 1.5 | 0.0 / 0.0 | 2990 / 4 / 0 | 0.29 | 22.9 [12.8, 34.3] | +9.0 [-3.5, +21.4] (n=49) | +14.2 [+6.5, +23.9] (n=49) |
| Mercury 3 (low) | 50 / 0 / 0 | 10% | none (choice only) | one request | 23.0 / 78.7 | 0.0 / 0.0 | 2987 / 13524 / 13519 | 4.85 | 23.6 [10.5, 39.0] | +12.2 [+2.0, +26.0] (n=45) | +17.8 [+5.5, +33.7] (n=45) |
| MiMo V2.6 Pro (off) | 50 / 0 / 0 | 0% | none (choice only) | one request | 2.2 / 3.4 | 0.0 / 0.0 | 3209 / 8 / 0 | 0.64 | 25.9 [11.9, 42.9] | +12.3 [-2.6, +29.1] (n=50) | +17.4 [+5.8, +32.2] (n=50) |
| MiMo V2.6 Pro (high) | 42 / 0 / 8 | 0% | none (choice only) | one request | 23.6 / 346.1 | 0.0 / 0.0 | 3132 / 4333 / 4324 | 4.05 | 7.2 [2.0, 14.0] | -1.7 [-13.3, +7.5] (n=42) | +2.7 [-1.5, +7.9] (n=42) |
| Beam 1.0 (low) | 50 / 0 / 0 | 0% | letter logprobs | one request | 7.7 / 16.2 | 0.0 / 0.0 | 3248 / 1548 / 1539 | 1.99 | 15.1 [7.3, 24.2] | +1.6 [-9.0, +10.6] (n=50) | +6.6 [+1.0, +13.3] (n=50) |
| Beam 1.0 (high) | 50 / 0 / 0 | 0% | letter logprobs | one request | 34.5 / 72.9 | 0.0 / 0.0 | 3249 / 8227 / 8218 | 8.67 | 15.0 [5.9, 26.7] | +1.4 [-8.9, +12.2] (n=50) | +6.5 [-3.8, +18.4] (n=50) |
| MiMo V2.6 Flash (off) | 50 / 0 / 0 | 10% | letter logprobs | one request | 0.9 / 2.7 | 0.0 / 0.0 | 3209 / 31 / 0 | 0.14 | 12.5 [5.7, 20.6] | +0.8 [-10.8, +11.1] (n=45) | +6.4 [+0.6, +13.8] (n=45) |
| MiMo V2.6 Flash (off, unconstrained) | 50 / 0 / 0 | 4% | letter logprobs | one request | 0.8 / 1.6 | 0.0 / 0.0 | 3209 / 3 / 0 | 0.02 | 15.9 [7.9, 25.7] | +5.3 [-7.2, +17.1] (n=48) | +10.1 [+3.0, +19.3] (n=48) |
| MiMo V2.6 Flash (low) | 50 / 0 / 0 | 28% | letter logprobs | one request | 39.5 / 332.7 | 0.0 / 0.0 | 3207 / 12660 / 12653 | 3.62 | 7.7 [1.6, 15.4] | +4.4 [-0.2, +11.4] (n=36) | +3.9 [+0.1, +9.6] (n=36) |
| Kimi K3 (low) | 50 / 0 / 0 | 0% | none (choice only) | one request | 16.5 / 42.2 | 0.6 / 15.2 | 3232 / 723 / 716 | 9.35 | 16.7 [7.2, 28.2] | +3.2 [-1.7, +9.9] (n=50) | +8.2 [+0.6, +18.4] (n=50) |
| Hy4 Preview (off) | 50 / 0 / 0 | 0% | none (choice only) | one request | 2.7 / 4.0 | 0.0 / 0.0 | 3069 / 8 / 0 | 1.71 | 20.9 [10.8, 33.5] | +7.3 [-5.0, +20.5] (n=50) | +12.4 [+4.1, +23.8] (n=50) |
| MiniMax M3.1 Flash (low) | 50 / 0 / 0 | 0% | none (choice only) | one request | 4.3 / 10.7 | 7.1 / 11.9 | 3225 / 393 / 391 | 0.72 | 22.1 [9.4, 38.3] | +8.6 [-6.4, +25.9] (n=50) | +13.6 [+2.3, +29.0] (n=50) |
| Grok 4.7 (low) | 50 / 0 / 0 | 0% | none (choice only) | one request | 18.7 / 64.2 | 0.0 / 0.0 | 4354 / 2011 / 2005 | 20.77 | 9.5 [2.8, 18.0] | -4.1 [-14.9, +5.0] (n=50) | +0.9 [-2.6, +5.9] (n=50) |
| Grok 4.7 (high) | 46 / 0 / 4 | 0% | none (choice only) | one request | 69.2 / 264.6 | 0.0 / 0.0 | 4336 / 9178 / 9172 | 63.74 | 6.5 [0.9, 14.7] | -6.9 [-17.6, +2.0] (n=46) | -1.4 [-4.1, +0.7] (n=46) |
| d3-turbo | 50 / 0 / 0 | 0% | decision model | one request | 0.6 / 0.8 | 0.0 / 0.0 | 3351 / 0 / – | – | 34.5 [17.8, 53.7] | +20.9 [+6.3, +39.2] (n=50) | +26.0 [+10.1, +45.0] (n=50) |
| Nemotron 3.5 Bolt (off) | 50 / 0 / 0 | 0% | letter logprobs | one request | 2.7 / 14.0 | 0.0 / 0.0 | 3228 / 1 / 0 | – | 23.2 [12.5, 35.0] | +9.6 [-3.4, +22.7] (n=50) | +14.6 [+5.8, +25.7] (n=50) |
| Nemotron 3.5 Bolt (on) | 50 / 0 / 0 | 0% | letter logprobs | one request | 218.0 / 303.4 | 0.0 / 0.0 | 29616 / 23169 / 0 | – | 11.6 [5.1, 19.8] | -2.0 [-11.7, +5.6] (n=50) | +3.1 [+0.6, +6.4] (n=50) |
```

## End state (2026-10-22 06:14 UTC)

- League 2: running, 4 of 136 matches not finished
- bariton GPUs: 0, 85844 MiB;1, 86253 MiB;2, 85844 MiB;3, 85844 MiB;
