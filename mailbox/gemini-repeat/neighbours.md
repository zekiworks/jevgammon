# Gemini Decision 1 — neighbours (metadata only)

Feed https://zekiworks.github.io/analysis/backgammon/bench-scores.json updated 2026-11-12T12:50Z; metric "error rate (PR, lower is better)". Gemini PR 27.97, league #26, 17 required pairs. Written 2026-11-12T13:01:24Z.

| Setup (v3.db #) | Kind | PR | Dist | In 25.0–31.1 | League(s) (matches) | Opp. = Gemini 17 | Shared pair seeds | Settings | Retained repeat |
|---|---|---|---|---|---|---|---|---|---|
| Kimi K3.1 Pro (off) (feed: Kimi K3.1 Pro) (#51) | chat | 28.05 | 0.076 | yes | #3 League 3 (11); #6 Gap matches League 3 (2) | 1/17 (13 opp.) | 0 | openrouter:moonshotai/mxfp4, mxfp4, reasoning none, letter_readout answer, parallel 4 | none |
| REAX 1.3 (#60) | decision | 27.77 | 0.198 | yes | #19 L1 late entry (18) | 17/17 (18 opp.) | 0 | local (reax13 serve.py), fp8, parallel 1 | #24 stopped, 0; #34 finished, 17 matched (compatible) |
| Base Labs Mammoth-1 (feed: Mammoth-1) (#55) | decision | 28.54 | 0.573 | yes | #14 L1 late entry (19) | 17/17 (19 opp.) | 0 | local (baselabs_server.py), bf16, parallel 1 | #31 finished, 17 matched (compatible) |
| Qwen3.8-27B (on) (feed: Qwen3.8-27B) (#20) | chat | 29.03 | 1.063 | yes | #2 League 2 (18); #4 Early start for round 3 League 2 (2); #5 Early start for round 5 League 2 (1) | 6/17 (21 opp.) | 0 | local-vllm, fp16 (bf16 checkpoint served in fp16 by vLLM; fp16 KV cache), reasoning low, letter_readout prefill, parallel 16, max_matches 16 | none |
| KnowLine 31B Gen1.5 (feed: KnowLine-31B-Gen1.5) (#62) | decision | 26.21 | 1.755 | yes | #21 L1 late entry (17) | 17/17 (17 opp.) | 0 | local (knowline_server.py), bf16, parallel 1, max_matches 1 | none |
| Liquid d1-ultra (feed: d1-ultra) (#27) | decision | 30.34 | 2.367 | yes | #2 League 2 (18); #4 Early start for round 3 League 2 (2); #5 Early start for round 5 League 2 (1) | 5/17 (21 opp.) | 0 | liquid, parallel 2 | #28 finished, 16 matched |
| Drex Max v1 (feed: Drex Max) (#58) | decision | 30.40 | 2.429 | yes | #17 L1 late entry (18) | 17/17 (18 opp.) | 0 | local (drex_max_server.py), bf16, parallel 1 | #32 finished, 17 matched (compatible) |
| GLM-5.3 (on) (feed: GLM-5.3) (#26) | chat | 30.87 | 2.896 | yes | #2 League 2 (18); #4 Early start for round 3 League 2 (2); #5 Early start for round 5 League 2 (1) | 6/17 (21 opp.) | 0 | openrouter:fireworks, reasoning low, letter_readout answer, parallel 8 | none |
| Qwen3.8 Flash (off) (feed: Qwen3.8 Flash) (#25) | chat | 33.58 | 5.608 | no | #2 League 2 (18); #4 Early start for round 3 League 2 (2); #5 Early start for round 5 League 2 (1) | 6/17 (21 opp.) | 0 | openrouter:alibaba, letter_readout answer, parallel 8 | none |
| Muse Ember (max) (feed: Muse Ember) (#61) | chat | 20.11 | 7.864 | no | #20 L1 late entry (17) | 17/17 (17 opp.) | 0 | openrouter:meta, reasoning max, letter_readout answer, parallel 4 | none |

- Decision K=3: REAX 1.3 (0.198), Mammoth-1 (0.573), KnowLine-31B-Gen1.5 (1.755); K=5: REAX 1.3 (0.198), Mammoth-1 (0.573), KnowLine-31B-Gen1.5 (1.755), d1-ultra (2.367), Drex Max (2.429)
- Chat K=3: Kimi K3.1 Pro (0.076), Qwen3.8-27B (1.063), GLM-5.3 (2.896); K=5: Kimi K3.1 Pro (0.076), Qwen3.8-27B (1.063), GLM-5.3 (2.896), Qwen3.8 Flash (5.608), Muse Ember (7.864)
- Combined K=3: Kimi K3.1 Pro (0.076), REAX 1.3 (0.198), Mammoth-1 (0.573); K=5: Kimi K3.1 Pro (0.076), REAX 1.3 (0.198), Mammoth-1 (0.573), Qwen3.8-27B (1.063), KnowLine-31B-Gen1.5 (1.755)

- K is open (Ümit/Main decide); selection measure = absolute difference in the feed's PR (error rate, lower is better) from 27.97, in PR points; ties (none occur at 3 decimals) broken by lower PR, then feed name. Inside 25.0–31.1 (Main's interval): Kimi K3.1 Pro, REAX 1.3, Mammoth-1, Qwen3.8-27B, KnowLine-31B-Gen1.5, d1-ultra, Drex Max, GLM-5.3, Drex Max v1.1.
- Shared pair seeds = opponents where matches.seed equals Gemini's seed v that opponent: 0 for every setup (also none equal Gemini's aborted Mercury #1016 seed). Rules: all L1 late entries equal league #26 (pair-v1, bg-v2, order seed 1190975713392774006, mirror_concurrent 1, 3 rounds, 300 turns, no clock).
- Matched pairs (repeat pinned to original seed+seat): REAX 1.3 [repeat 1] #24 stopped (0 matches), #34 17/17 (orig #905–922 minus Mercury); Mammoth-1 [repeat 1] #31 17 (Mercury, Luna blocked); Drex Max v1 [repeat 1] #32 17; d1-ultra [repeat 1] #28 16 of its pre-promotion League 1 matches, mirror_concurrent 0 (not compatible). Per-pair ids in neighbours.json.
