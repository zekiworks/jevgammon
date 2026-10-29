# Trade-off CSV for Ümit (2026-10-29)

Files:
- `trade_off.csv`: 50 rows, one per setup per league table (League 1: 19, League 2: 19, League 3: 12).
- `trade_off_late_entry.csv`: 1 row, GPT-6 Astra (high). It was a late entry to League 3 and is kept apart.

All figures come from saved data. No model was called and no position was rescored. Dot is the decimal mark, and numbers have 4 decimals.

**These definitions are my reading of the request. Ümit has not confirmed them yet.**

## Sources
- `v3.db`, opened read-only (`file:...?mode=ro`), read on 2026-10-29 around 12:00 UTC. It supplies turns, games, matches, players and `players.settings`. The site's snapshot leaves late-entry matches out of `league_match_view`. Here the same filter is a TEMP view over the read-only connection (`stage <> 'late-entry'`), so nothing is written to `v3.db`.
- GNUbg 2-ply scores of every legal play: the site's shards `~/.local/state/bg-site/plays/s*.db`.
- Code: the site's own `tools/site/analysis.py`. `load_leagues` gives each league's decisions exactly as the site loads them. `decision_from_plays` gives per-play equity losses and hitting rolls. `play_call` gives the position class at margin 0.001 (`content/thresholds.json` `risk_margin`).
- Names: `tools/site/content/labels.json`. Prices: `tools/site/content/setups.json`.
- Cross-check: the published per-setup files `~/.local/state/bg-site/analysis/backgammon/data/v3/league-N/<slug>.json` (build data as of 2026-10-29 11:09 UTC; all three leagues Finished).

## Rows
- One row per setup in each league table the site publishes. `setup_id` is the slug of the data file (`data/v3/league-N/<setup_id>.json`), so it uses the old internal name.
- The decisions are the setup's own league decisions in that league's valid matches, as the site counts them. That means `league_match_view` without late-entry matches, and turns decided by `model` or `fallback`. All 830 of these matches are finished.
- A setup that moved league in the ladder appears in the league where the site publishes it. Examples: Qwen3.8-27B (off) in League 1; Claude Fable 5.1 (low) and Grok 4.7 (low) in League 2; GPT-6.1 Sol in League 3.
- Programs (GNUbg weak, Safest, Random) are included, and their `display_name` ends in " (program)". The site's computed reference rows ("Safest (computed)", "Random (computed)") are not setups and are left out.
- GPT-6 Astra (high) is not in the main file. Its row is in `trade_off_late_entry.csv`: its own decisions in its 11 finished late-entry matches against League 3 setups. The site publishes no numbers for it, so that row has no cross-check.

## Columns
- `display_name`: the shown name (`labels.json` relabel; otherwise the name is unchanged).
- `setting_sent`: the reasoning setting in the setup's stored request settings (`players.settings`).
  - `low`, `medium` or `high`: the effort or thinking level sent.
  - `none`: reasoning was switched off or set to none. That is `request.reasoning.enabled: false` for DeepSeek V4.1 Flash (off), DeepSeek V4.1 Flash 1017 (off) and Qwen3.8 Flash (off), and `reasoning: "none"` for Kimi K3.1 Pro (off).
  - `on` or `off`: thinking was switched on or off with no level the model reads. That covers Gemma 4 31B (`enable_thinking`), LFM2.5-24B-A2B (empty think-block prefill for off; for on, its requests carry `"low"`, which its template ignores, as `labels.json` records) and Qwen3.8-27B (off) (`enable_thinking: false`).
  - Empty for programs, and for decision models, which have no reasoning setting and send none.
  - Known detail (`labels.json` note): 232 early DeepSeek V4.1 Flash (off) requests sent no reasoning field; every response had 0 reasoning tokens.
- `trade_off_decisions`: decisions the site's rule classes as Risk pays or Safety pays at margin 0.001. This is `play_call(...)` with class ≠ `none`: not every legal play leaves the same number of hitting rolls. It is exactly the site's risk-judgement denominator (`risk.main.trade_off` = Risk pays + Safety pays).
- `risks_taken`: trade-off decisions where the play made leaves more hitting rolls than the minimum (the site's right risk + wrong risk + needless).
- `safe_plays`: the rest. `risks_taken + safe_plays = trade_off_decisions`.
- `risk_win` and `risk_loss`: over the decisions where it took a risk, the sums of max(0, eq(play made) − eq(best safe play)) and max(0, eq(best safe play) − eq(play made)).
  - The best safe play is the best play by 2-ply equity among those that leave the minimum number of hitting rolls.
- `safe_win` and `safe_loss`: the same over the decisions where it played safe, against the best risky play (the best play among those leaving more hitting rolls than the minimum).
- Scale for those four columns: points = 500 × GNUbg 2-ply equity (the site's error-rate scale), per 1,000 trade-off decisions. Each is total × 500 ÷ `trade_off_decisions` × 1000.
- Invalid answers follow the site's rule for risk calls: answers decided by `fallback` (the runner's random play) are left out of every risk number (`risk_metrics` uses only valid, scored decisions). They are not in `trade_off_decisions`, the sums, the tokens or the cost. Three setups have invalid decisions; all others have none:
  - DeepSeek V4.1 Flash (low), League 2: 38 of 2,226 decisions.
  - DeepSeek V4.1 Flash 1017 (low), League 2: 12 of 2,234.
  - Gemini 4 Argon (high), League 3: 36 of 1,368.
- Every valid decision is scored, so none is unscored.
- `usd_trade_off`: total dollars for the row's trade-off decisions. It is the sum of (input tokens × input price + output tokens × output price) ÷ 10⁶, with the prices from `setups.json`. This is the site's price-table method (`Player::cost`).
  - Subscriptions are priced the same way (API-list-price equivalent, not money paid).
  - OpenRouter chat setups are also priced at list price × logged tokens, for consistency, not at OpenRouter's billed `usage.cost`. These are DeepSeek V4.1 Flash, DeepSeek V4.1 Flash 1017, GLM-5.3, Qwen3.8 Flash and Kimi K3.1 Pro. The site's `turns.cost_usd` stores the billed amount, which is lower: for example GLM-5.3 $9.61 here against $4.46 billed, and Kimi $7.73 against $3.55.
  - For every other priced setup (Mercury Decide via OpenRouter included), the figure equals the sum of `turns.cost_usd` over the same decisions.
  - Empty where no price exists: programs, "own hardware" setups on our GPUs, Fastino GLiDE (hosted API with no recorded price), Fastino GLiDE v1.2 (local), and Qwen3.8-27B (low).
- `tokens_in_mean` and `tokens_out_mean`: mean `turns.input_tokens` and `turns.output_tokens` per trade-off decision. Every model row has tokens logged for all its trade-off decisions. Programs have none and are left empty.
  - Option groups: a turn already stores the sum over all of the decision's requests. `src/players/llm.rs` and `src/players/decision.rs` add every request's usage into the decision, and the runner writes that to the turn. Nothing more had to be summed.

## Reasoning tokens in `tokens_out` (checked per route)
`output_tokens` already includes reasoning on every route, so no `reasoning_tokens` were added anywhere. Evidence from the parsers in `src/players/llm.rs` and from the data (all league decisions, `output_tokens − reasoning_tokens` is never negative):

| Route (turns.provider) | What output_tokens is | Data check |
|---|---|---|
| claude-subscription (Anthropic Messages) | `usage.output_tokens`, thinking included | output ≥ reasoning + 11 on every decision |
| chatgpt-subscription (Codex Responses) | `usage.output_tokens`, reasoning included (`output_tokens_details.reasoning_tokens` is a part of it) | output ≥ reasoning + 15 |
| xai-subscription (xAI Responses) | `usage.output_tokens` | output ≥ reasoning + 6 on all decisions; every Grok decision reports reasoning |
| antigravity-subscription (Gemini) | the harness stores `candidatesTokenCount + thoughtsTokenCount` | output ≥ reasoning + 3 |
| openrouter:* (fireworks, deepseek, alibaba, moonshotai, inception) | `usage.completion_tokens`, reasoning included | output ≥ reasoning + 1 |
| local-vllm, local-sglang | `usage.completion_tokens` (every generated token) | Gemma (on) and Qwen3.8-27B (low) report reasoning ≤ output. LFM2.5 (on) reports 0 reasoning tokens but has about 22k output tokens per decision, so its thinking is in output_tokens |
| decision-model APIs and local decision servers | as reported (0 or 1; Jev about 300) | no reasoning reported |

## Missing data and caveats
- Fastino GLiDE (League 2) and Fastino GLiDE v1.2 (local) (League 1) have no price in `setups.json`, so `usd_trade_off` is empty.
- Mixed routes:
  - DeepSeek V4.1 Flash (off), League 1: 80 of its 1,333 trade-off decisions ran on our SGLang server.
  - DeepSeek V4.1 Flash (low), League 2: 494 of 1,709 ran there.
  - All of these are priced at the setup's OpenRouter/Fireworks list price, as the site does.
  - Qwen3.8-27B (low): 1 trade-off decision ran on OpenRouter/Cerebras. Its `usd_trade_off` is empty because `setups.json` marks it as own hardware.
- Decider v1.1 27B, Decider v1.2 27B and Decider Flash v1.2 run on our GPUs but have a list price (the site labels it "list-price estimate; runs on our GPUs"). They are priced like the site, so `usd_trade_off` is filled for them. **Open point:** the request said "empty for models on our GPUs (no list price)". If Ümit wants these empty too, drop those three values.
- GPT-6 Astra (high) is not in `setups.json`. Its late-entry row uses the price in its `players.settings` ($10 / $50 per M tokens, the same as GPT-6 Astra (low) and (medium)).

## Cross-check against the published site
For every setup, `trade_off_decisions` equals the site's `risk.main.trade_off` (Risk pays + Safety pays), and `risks_taken` equals the site's right risk + wrong risk + needless (`risk.main.calls`). **50 of 50 rows match, with no mismatch.** The table also shows the site's published risk counts (risks found = right risks / Risk pays; right safety / Safety pays).

| league | setup_id | trade-off (ours / site) | risks taken (ours / site right+wrong+needless) | site: risks found (right risk / Risk pays) | site: right safety (/ Safety pays) | match |
|---|---|---|---|---|---|---|
| league-1 | decider-v1-1-27b | 1548 / 1548 | 463 / 463 | 233 / 703 | 682 / 845 | yes |
| league-1 | subq-snap-preview | 1679 / 1679 | 647 / 647 | 297 / 783 | 673 / 896 | yes |
| league-1 | open-jev-27b-v1-1 | 1469 / 1469 | 768 / 768 | 264 / 708 | 455 / 761 | yes |
| league-1 | cygnet-gemma-4-12b | 1539 / 1539 | 367 / 367 | 205 / 750 | 685 / 789 | yes |
| league-1 | random | 936 / 936 | 728 / 728 | 112 / 452 | 121 / 484 | yes |
| league-1 | safest | 1534 / 1534 | 0 / 0 | 0 / 785 | 749 / 749 | yes |
| league-1 | gnubg-weak | 1404 / 1404 | 805 / 805 | 410 / 616 | 533 / 788 | yes |
| league-1 | jev-1-13-0 | 1476 / 1476 | 308 / 308 | 190 / 705 | 710 / 771 | yes |
| league-1 | gpt-6-luna | 1449 / 1449 | 284 / 284 | 160 / 740 | 636 / 709 | yes |
| league-1 | decider-flash-v1-2 | 1488 / 1488 | 665 / 665 | 223 / 712 | 519 / 776 | yes |
| league-1 | winnow-12b | 1528 / 1528 | 540 / 540 | 263 / 780 | 573 / 748 | yes |
| league-1 | mercury-decide | 1352 / 1352 | 252 / 252 | 129 / 690 | 583 / 662 | yes |
| league-1 | decider-v1-2-27b | 1558 / 1558 | 466 / 466 | 244 / 731 | 682 / 827 | yes |
| league-1 | fastino-glide-v1-2-local | 1489 / 1489 | 400 / 400 | 219 / 664 | 698 / 825 | yes |
| league-1 | lfm2-5-24b-a2b-off | 1465 / 1465 | 648 / 648 | 206 / 715 | 470 / 750 | yes |
| league-1 | lfm2-5-24b-a2b-on | 1670 / 1670 | 650 / 650 | 248 / 788 | 647 / 882 | yes |
| league-1 | qwen3-8-27b-off | 1488 / 1488 | 281 / 281 | 178 / 756 | 671 / 732 | yes |
| league-1 | deepseek-v4-1-flash-off | 1333 / 1333 | 310 / 310 | 192 / 659 | 603 / 674 | yes |
| league-1 | celeris-1-decision | 1500 / 1500 | 268 / 268 | 163 / 683 | 749 / 817 | yes |
| league-2 | gemini-3-8-flash-high | 1610 / 1610 | 302 / 302 | 264 / 731 | 858 / 879 | yes |
| league-2 | claude-sonnet-5-5-low | 1579 / 1579 | 263 / 263 | 204 / 661 | 883 / 918 | yes |
| league-2 | claude-sonnet-5-5-high | 1626 / 1626 | 376 / 376 | 308 / 737 | 841 / 889 | yes |
| league-2 | deepseek-v4-1-flash-on | 1709 / 1709 | 450 / 450 | 338 / 751 | 891 / 958 | yes |
| league-2 | glm-5-3-on | 1451 / 1451 | 303 / 303 | 205 / 668 | 726 / 783 | yes |
| league-2 | gnubg-weak | 1672 / 1672 | 1003 / 1003 | 483 / 770 | 558 / 902 | yes |
| league-2 | qwen3-8-flash-off | 1431 / 1431 | 446 / 446 | 243 / 706 | 613 / 725 | yes |
| league-2 | gemma-4-31b-on | 1604 / 1604 | 272 / 272 | 223 / 700 | 878 / 904 | yes |
| league-2 | gemma-4-31b-off | 1379 / 1379 | 306 / 306 | 194 / 584 | 732 / 795 | yes |
| league-2 | qwen3-8-27b-on | 1530 / 1530 | 378 / 378 | 242 / 715 | 735 / 815 | yes |
| league-2 | liquid-d1-ultra | 1504 / 1504 | 461 / 461 | 289 / 688 | 702 / 816 | yes |
| league-2 | claude-fable-5-1-off | 1484 / 1484 | 349 / 349 | 270 / 658 | 781 / 826 | yes |
| league-2 | fastino-glide | 1575 / 1575 | 475 / 475 | 249 / 675 | 756 / 900 | yes |
| league-2 | grok-4-7-off | 1613 / 1613 | 413 / 413 | 295 / 697 | 852 / 916 | yes |
| league-2 | deepseek-v4-1-flash-1017-off | 1458 / 1458 | 288 / 288 | 181 / 713 | 683 / 745 | yes |
| league-2 | deepseek-v4-1-flash-1017-on | 1678 / 1678 | 413 / 413 | 321 / 755 | 872 / 923 | yes |
| league-2 | jev-1-14-0 | 1367 / 1367 | 309 / 309 | 184 / 632 | 657 / 735 | yes |
| league-2 | clef | 1464 / 1464 | 560 / 560 | 263 / 666 | 603 / 798 | yes |
| league-2 | gemini-3-8-flash-low | 1542 / 1542 | 265 / 265 | 214 / 633 | 877 / 909 | yes |
| league-3 | gpt-6-astra-off | 910 / 910 | 269 / 269 | 226 / 395 | 486 / 515 | yes |
| league-3 | gpt-6-astra-on | 1020 / 1020 | 289 / 289 | 245 / 446 | 542 / 574 | yes |
| league-3 | claude-opus-5-5-off | 1043 / 1043 | 242 / 242 | 187 / 466 | 541 / 577 | yes |
| league-3 | claude-opus-5-5-on | 1070 / 1070 | 244 / 244 | 199 / 459 | 590 / 611 | yes |
| league-3 | claude-fable-5-1-on | 987 / 987 | 279 / 279 | 215 / 424 | 529 / 563 | yes |
| league-3 | gemini-4-argon-on | 938 / 938 | 253 / 253 | 224 / 441 | 484 / 497 | yes |
| league-3 | grok-4-7-on | 920 / 920 | 248 / 248 | 190 / 432 | 454 / 488 | yes |
| league-3 | gnubg-weak | 1124 / 1124 | 627 / 627 | 288 / 490 | 415 / 634 | yes |
| league-3 | gpt-6-1-sol-low | 1025 / 1025 | 254 / 254 | 198 / 383 | 602 / 642 | yes |
| league-3 | gpt-6-1-sol-high | 1025 / 1025 | 271 / 271 | 212 / 419 | 568 / 606 | yes |
| league-3 | kimi-k3-1-pro-off | 826 / 826 | 233 / 233 | 153 / 361 | 416 / 465 | yes |
| league-3 | gemini-4-argon-off | 1036 / 1036 | 292 / 292 | 209 / 437 | 543 / 599 | yes |
