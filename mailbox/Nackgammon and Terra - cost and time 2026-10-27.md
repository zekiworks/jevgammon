# Nackgammon and Terra: cost and time (2026-10-27)

Before any model call, as asked in `mailbox/Nackgammon and Terra - brief 2026-10-27.md`, point 5. **Nothing below has been run** except the engine work of row g (position sets built and frozen, `freeze/nack-paired.json`; Method §10 committed first). No model, no anchor through the harness, no smoke, no server started.

## How the numbers are built

- **Source:** `v3.db` (read-only), every setup's own valid league, ladder and Cup decisions on its stored route (`turns` joined through `matches.player1/2` to `players`). For the paired test only decisions with 2–25 legal plays and no group split are used (the sets have 2–25 plays); for matches, all decisions.
- **Tokens** are real per-decision means: input, output **including thinking** (the reasoning tokens the provider reports are part of `output_tokens`; shown in brackets where reported). The paired prompts drop the opening table (1,256 characters, about 370 tokens), so paired input is scaled by 0.89. Output is taken as measured (low end) to measured × 1.2 (high end); the opening-heavy sets may change thinking length.
- **Retries:** failed-request share = decisions with at least one failed provider request in `exchanges` (all setups 0.0% except LFM2.5-24B-A2B (on), 5.6%). `retry_ms` is not used: it also holds pacing and queue waits. Allowance on the high end: +2% attempts (no-thinking setups), +5% (thinking setups). Invalid answers in league play: 0.0% for every setup here.
- **Money:** list price × tokens. **OpenRouter** = billed from the $7.27 left. **Own key** = billed by that vendor (Celeris, SubQ, TypeSafe/Jev, OpenAI Decisions/Luna, Liquid, Fastino), not OpenRouter. **API-eq.** = subscription or our GPU at list price, not billed (time only). OpenRouter prices checked today 16:23 UTC (`/api/v1/models` and the pinned endpoints): `openai/gpt-6.1-terra` $1/$5 per M (OpenAI endpoint), Fireworks DeepSeek V4.1 Flash $0.30/$1.20, Fireworks GLM-5.3 $1.40/$4.40, Alibaba Qwen3.8 Flash $0.15/$0.47, DeepSeek V4.1 Flash 1017 (DeepSeek) $0.15/$0.60: all equal to the roster prices. Mercury Decide (OpenRouter decisions route) at the roster's $0.02/M.
- **Time:** low = decisions × p50 latency ÷ the setup's parallel requests; high = attempts × mean latency × 1.2 ÷ parallel; OpenRouter setups at least decisions ÷ 18 rpm (`rpm: 18`). Own-GPU latencies are league latencies (they include queueing). Matches: the ladder's formula (decisions × (seconds of both) × 0.56, measured concurrency of the same-dice games).
- **Real turns per game (matches):** stored valid matches: 51.3 turns per game, 5.49 games per match, 20.6 decisions per side per game; per-setup decisions per match from `tools/ladder.py` (e.g. GPT-6.1 Sol (low) 114). **Nackgammon:** in our GNUbg self-play (10,000 games each) a Nackgammon game has 67.1 turns against 55.4, and 54.4 decisions with 2+ plays against 43.5: ×1.25, applied to the knockout ([INFERENCE] that models' games lengthen like GNUbg's).
- **GPT-6.1 Terra has no logs.** Its tokens, latency and decisions per match are **estimates from GPT-6.1 Sol (low)** (same family, same effort low): 3,075 input and 76 output (60 thinking) tokens per paired-type decision; 4,497 / 115 over all league decisions; 114 decisions per match. At $1/$5 it costs exactly half of Sol (low) at its $2/$10 list price. Re-estimated after its smoke test.

## Summary table (rows a–g)

| Row | What | Decisions | OpenRouter $ (billed) | Own-key $ (billed, not OpenRouter) | Subscription API-eq. (not billed) | Our GPU / CPU time | Wall time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a | Terra smoke test (50 positions of `positions/smoke.jsonl`, bg-v2, as for earlier new setups) | 50 | **$0.17–0.18** | $0 | $0 | — | about 3 min (18 rpm) |
| b | Paired test **start**: 16 decision models + GNUbg weak anchor, 400 each (Random: no calls) | 6,800 | **$0.35–0.36** (DeepSeek V4.1 Flash (off) $0.33–0.34, Mercury Decide $0.02) | $0.27 (Celeris, SubQ, Jev 1.13.0, Luna) | $0 (Deciders $0.06 API-eq.) | GPU 3.7–5.9 h summed (LFM2.5 (on) 2.8–3.7 h of it); GNUbg weak < 1 min CPU | about 3–4 h (GPU servers side by side; LFM2.5 (on) sets it) |
| c | Paired test **start**: Cup teams not in League 1 (5 subscription + Gemma 4 31B (on)), plus Terra, 400 each | 2,800 | **$1.25–1.34** (Terra only) | $0 | $23.0–25.0 (GPT-6 Astra (on) $12.5–13.4 of it) | GPU 0.5–0.9 h (Gemma 4 31B (on), last) | about 1.5–2.5 h in order, Gemma last |
| d | Paired test **extension**, worst case: every setup of b and c extended by 600 to 1,000 | 14,400 | **$2.40–2.55** (Terra $1.87–2.01, DeepSeek (off) $0.50–0.51, Mercury $0.03) | $0.40 | $34.6–37.5 | GPU 6.3–10.1 h summed | about 5–7 h |
| e | Nackgammon knockout: 8 Cup teams, 7 matches, same-dice rule, prompt `bg-v3-nack` | about 2,000 (≈ 290 per match) | **$0** | $0.05–0.09 (Celeris, SubQ) | $12.7–32.4 (depends on who advances) | Gemma 4 31B (on): 4.7–5.3 h per match, 1 to 3 matches | 5.0–15.1 h |
| f | Terra's League 2 season: 19 matches, one against each League 2 setup | 2,167 Terra + 2,176 opponents | **$13.5–14.2** (Terra $11.0–11.5; OpenRouter opponents $2.5–2.7) | $0.03 | $18.6 (opponents) | GPU 9.9 h (Qwen3.8-27B (on) 5.5 h, Gemma 4 31B (on) 3.9 h) | about 5.5–17 h |
| g | Engine only: building the sets (done) and the rollout check (after the answers) | — | $0 | $0 | $0 | Built: self-play 11.7 min + 2-ply candidates 21.5 min wall at 16 processes (nice 19), matching 6 s. Rollout check: about 560–720 plays × ~21 s (1-ply, 1,296 trials, 8 threads) = 3.3–4.2 h on one 8-thread process, 1.7–2.1 h on two | done / 2–4 h |

Start and extension are kept separate: rows b and c are the start (400 decisions per setup), row d the worst-case extension only (+600 per setup). The stopping rule (Method §10.8) extends only "unclear" setups, so d is an upper bound.

## Per-setup detail (paired test: rows b, c, d)

Route: OpenRouter (billed from the $7.27), own API key (billed elsewhere), subscription (time only), our GPU (time only), program.

| Setup | Route | League decisions used (≤25 plays) | Input tok/decision | Output tok/decision (of which thinking) | Calls/decision | Failed-request share | 400 decisions (start) | Time start | +600 (extension) | Time extension |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Celeris-1 Decision | own API key | 3,621 | 3,290 | 0 | 1 | 0.0% | $0.05 billed on own key | 1 min | $0.07 billed on own key | 1 min |
| SubQ Snap Preview | own API key | 2,296 | 3,309 | 0 | 1 | 0.0% | $0.06 billed on own key | 0 min | $0.09 billed on own key | 1 min |
| Cygnet (Gemma 4 12B) | our GPU | 2,333 | 3,459 | 1 | 1 | 0.0% | n/a (no list price) | 1 min–2 min | n/a (no list price) | 1 min–3 min |
| Decider v1.2 27B | our GPU | 2,174 | 3,270 | 0 | 1 | 0.0% | $0.02 API-eq. (not billed) | 18 min–25 min | $0.03 API-eq. (not billed) | 27 min–37 min |
| Fastino GLiDE v1.2 (local) | our GPU | 2,154 | 3,283 | 0 | 1 | 0.0% | n/a (no list price) | 2 min | n/a (no list price) | 4 min–5 min |
| DeepSeek V4.1 Flash (off) | OpenRouter | 3,766 | 3,060 | 7 | 1 | 0.0% | **$0.33–0.34 OpenRouter** | 22 min | **$0.50–0.51 OpenRouter** | 33 min |
| Jev 1.13.0 | own API key | 2,068 | 3,538 | 166 | 1 | 0.0% | $0.05 billed on own key | 1 min | $0.08 billed on own key | 1 min |
| GPT-6 Luna | own API key | 2,234 | 3,048 | 0 | 1 | 0.0% | $0.11 billed on own key | 1 min | $0.16 billed on own key | 1 min |
| Decider v1.1 27B | our GPU | 2,156 | 3,302 | 0 | 1 | 0.0% | $0.02 API-eq. (not billed) | 11 min–54 min | $0.04 API-eq. (not billed) | 17 min–81 min |
| LFM2.5-24B-A2B (on) | our GPU | 3,395 | 22,576 | 17,196 (thinking not split out by the server) | 2 | 5.6% | n/a (no list price) | 2.8 h–3.7 h | n/a (no list price) | 4.2 h–5.5 h |
| Qwen3.8-27B (off) | our GPU | 3,692 | 3,189 | 2 | 1 | 0.0% | n/a (no list price) | 1 min | n/a (no list price) | 1 min–2 min |
| Mercury Decide | OpenRouter | 2,100 | 3,204 | 1 | 1 | 0.0% | **$0.02 OpenRouter** | 2 min | **$0.03 OpenRouter** | 2 min |
| Winnow-12B | our GPU | 2,210 | 3,370 | 0 | 1 | 0.0% | n/a (no list price) | 4 min–5 min | n/a (no list price) | 6 min–7 min |
| LFM2.5-24B-A2B (off) | our GPU | 2,899 | 3,028 | 1 | 1 | 0.0% | n/a (no list price) | 0 min | n/a (no list price) | 0 min |
| Open-Jev 27B v1.1 | our GPU | 2,222 | 24,039 | 0 | 1 | 0.0% | n/a (no list price) | 11 min–31 min | n/a (no list price) | 16 min–46 min |
| Decider Flash v1.2 | our GPU | 2,055 | 3,306 | 0 | 1 | 0.0% | $0.01 API-eq. (not billed) | 4 min–10 min | $0.02 API-eq. (not billed) | 7 min–15 min |
| GNUbg weak | program, CPU | 4,129 | 0 | 0 | 1 | — | $0 (CPU) | 0 min | $0 (CPU) | 0 min |
| Gemini 3.8 Flash (low) | subscription | 3,235 | 3,208 | 180 (177) | 1 | 0.0% | $1.13–1.24 API-eq. (not billed) | 3 min–6 min | $1.69–1.86 API-eq. (not billed) | 5 min–10 min |
| Claude Sonnet 5.5 (low) | subscription | 2,651 | 4,187 | 155 (144) | 1 | 0.0% | $3.60–3.91 API-eq. (not billed) | 2 min–5 min | $5.40–5.87 API-eq. (not billed) | 4 min–8 min |
| GPT-6.1 Sol (low) | subscription | 2,501 | 3,075 | 76 (60) | 1 | 0.0% | $2.49–2.68 API-eq. (not billed) | 6 min–10 min | $3.74–4.02 API-eq. (not billed) | 9 min–15 min |
| GPT-6 Astra (on) | subscription | 1,471 | 3,090 | 73 (57) | 1 | 0.0% | $12.46–13.39 API-eq. (not billed) | 7 min–11 min | $18.69–20.08 API-eq. (not billed) | 10 min–17 min |
| GPT-6.1 Sol (high) | subscription | 2,594 | 3,099 | 287 (270) | 1 | 0.0% | $3.36–3.76 API-eq. (not billed) | 17 min–31 min | $5.03–5.65 API-eq. (not billed) | 25 min–46 min |
| Gemma 4 31B (on) | our GPU | 2,684 | 10,344 | 3,904 (3,891) | 2 | 0.0% | n/a (no list price) | 30 min–54 min | n/a (no list price) | 45 min–80 min |
| GPT-6.1 Terra (estimate from GPT-6.1 Sol (low) logs; no Terra logs) | OpenRouter | Sol (low): 2,501 | 3,075 | 76 (60) | 1 | 0.0% | **$1.25–1.34 OpenRouter** | 22 min–23 min | **$1.87–2.01 OpenRouter** | 33 min–35 min |

Order in the run (Method §10.8): GNUbg weak and the decision models first, then Gemini 3.8 Flash (low), Claude Sonnet 5.5 (low), GPT-6.1 Sol (low), GPT-6 Astra (on), GPT-6.1 Sol (high), then Terra if it runs, and Gemma 4 31B (on) last. Celeris-1 Decision and SubQ Snap Preview run once (League 1 and Cup). Random needs no calls: its error rates are already computed (Main 200 pairs: standard 87.45 PR, Nackgammon 82.89 PR; `positions/nack-paired/build-log.json`).

## Row e: Nackgammon knockout (Hype Cup bracket, `mailbox/Hype Cup roster 2026-10-27.md`)

Real decisions per match from each team's stored matches × 1.25 (Nackgammon games run longer), prompt `bg-v3-nack` (input × 0.89). No OpenRouter setup is among the 8. No GNUbg anchor.

| Quarter-final | Decisions (both sides) | OpenRouter $ | Subscription API-eq. | Own key $ | Wall time | GPU |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-6.1 Sol (low) v Gemma 4 31B (on) | 291 | $0 | $1.29 | $0 | 4.9 h | Gemma 4 31B (on) on our GPU |
| GPT-6 Astra (on) v SubQ Snap Preview | 304 | $0 | $6.84 | $0.03 | 11 min | — |
| Gemini 3.8 Flash (low) v GPT-6.1 Sol (high) | 287 | $0 | $2.37 | $0 | 35 min | — |
| Claude Sonnet 5.5 (low) v Celeris-1 Decision | 284 | $0 | $1.71 | $0.02 | 5 min | — |

- **Semi-finals and final** depend on the winners. SF A (QF1 v QF4 winners): $0–3.00 API-eq., 9 min–4.9 h (4.7–4.9 h if Gemma 4 31B (on) is in it). SF B (QF2 v QF3 winners): $0.52–8.69 API-eq. (GPT-6 Astra (on) v GPT-6.1 Sol (high) the most), 5 min–41 min. Final: $0–8.55 API-eq., 1 min–5.3 h (Gemma 4 31B (on) v GPT-6.1 Sol (high) the longest).
- **Total:** 7 matches, about 2,000 decisions, $0 OpenRouter, $12.7–32.4 subscription API-eq., 5.0–6.3 h (Gemma 4 31B (on) out in QF1) to 15.1 h (Gemma in all three rounds) wall time, quarter-finals side by side.
- **Prerequisite (not done):** the league runner starts every game from the standard position; a Nackgammon start option is needed before the knockout (runner change, no model call). The prompt version exists (`bg-v3-nack`).
- Report: each team's Nackgammon error rate next to its standard league error rate, labelled "rough: different positions and opponents, not paired".

## Row f: GPT-6.1 Terra's League 2 season (next season under the new rule; it plays every League 2 setup once)

Terra's side per match: 114 decisions (Sol (low)'s real decisions per match) × $0.00507 (Sol (low)'s league cost per decision at half its price) = $0.58, OpenRouter. Estimates, since Terra has no logs.

| Opponent | Route | Its decisions per match | Opponent's cost | Terra's side (OpenRouter) | Match time |
| --- | --- | --- | --- | --- | --- |
| Gemini 3.8 Flash (low) | subscription | 113 | $0.47 API-eq. | **$0.58** | 11 min |
| Claude Sonnet 5.5 (low) | subscription | 114 | $1.53 API-eq. | **$0.58** | 11 min |
| Gemma 4 31B (on) | our GPU | 118 | n/a | **$0.58** | 3.9 h |
| DeepSeek V4.1 Flash 1017 (on) | OpenRouter | 125 | **$0.60 OpenRouter** | **$0.58** | 70 min |
| Claude Sonnet 5.5 (high) | subscription | 118 | $2.37 API-eq. | **$0.58** | 17 min |
| DeepSeek V4.1 Flash (on) | OpenRouter | 122 | **$1.57 OpenRouter** | **$0.58** | 1.6 h |
| Gemini 3.8 Flash (high) | subscription | 120 | $2.74 API-eq. | **$0.58** | 30 min |
| Grok 4.7 (off) | subscription | 116 | $3.76 API-eq. | **$0.58** | 73 min |
| Claude Fable 5.1 (off) | subscription | 121 | $7.77 API-eq. | **$0.58** | 11 min |
| Gemma 4 31B (off) | our GPU | 102 | n/a | **$0.58** | 10 min |
| Qwen3.8-27B (on) | our GPU | 112 | $0.54 API-eq. | **$0.58** | 5.5 h |
| GNUbg weak | program, CPU | 114 | n/a | **$0.58** | 7 min |
| GLM-5.3 (on) | OpenRouter | 106 | **$0.31 OpenRouter** | **$0.58** | 18 min |
| Liquid d1-ultra | own API key | 116 | $0.02 own key | **$0.58** | 8 min |
| DeepSeek V4.1 Flash 1017 (off) | OpenRouter | 114 | **$0.03 OpenRouter** | **$0.58** | 32 min |
| Fastino GLiDE | own API key | 117 | n/a | **$0.58** | 8 min |
| Jev 1.14.0 | own API key | 106 | $0.02 own key | **$0.58** | 7 min |
| Qwen3.8 Flash (off) | OpenRouter | 112 | **$0.03 OpenRouter** | **$0.58** | 21 min |
| Clef | our GPU | 110 | n/a | **$0.58** | 14 min |

Totals: Terra $10.99 (+5% allowance: $11.54), OpenRouter opponents $2.54–2.67 (DeepSeek V4.1 Flash (on) $1.57, DeepSeek V4.1 Flash 1017 (on) $0.60, GLM-5.3 (on) $0.31, the two (off) $0.06), so **$13.5–14.2 OpenRouter**; subscriptions $18.6 API-eq.; GPU 9.9 h (Qwen3.8-27B (on), Gemma 4 31B (on), Gemma 4 31B (off), Clef). Terra's 2,167 decisions take at least 2.0 h at 18 rpm; with 4 matches at once about 5.5–17 h.

## Row g, done: the position sets as built (Method §10, frozen in `freeze/nack-paired.json`)

- Built after Method §10 was committed (fa704da), frozen in bd85d73. GNUbg 1.08.003 self-play, 10,000 games per variant (seed token `np20261027`); 75,251 Nackgammon and 74,062 standard candidates with 2-ply values for every legal play. Every (phase, class) cell filled: no shortfall move. 1,000 positions from 1,000 distinct source games, no repeated board + dice state (checked). Every pair matches phase and class exactly. Offline render (`jevgammon render`, no request): all 1,000 rows parse with their own prompt version; every rendered setup line names the right start; the runner's hitting rolls equal ours on all 11,073 options.
- Pairs per phase and class: main 200 = opening 30 risk / 30 safety, contact 24/24/12 none, holding 12/12/6, race 25 none, bear-off 25 none; reserve 300 = 1.5 × that (race 38, bear-off 37). Engine-check subset: 40 main pairs (opening 12, contact 12, holding 6, race 5, bear-off 5; 10 Risk pays, 14 Safety pays, 16 No trade-off).

**Balance, main 200 pairs** (SMD = standardised mean difference, Nackgammon − standard):

| Variable | Nackgammon mean (median) | Standard mean (median) | SMD |
| --- | --- | --- | --- |
| Legal plays | 11.05 (10) | 11.04 (10) | +0.003 |
| Gap, two best (2-ply equity) | 0.0616 (0.0171) | 0.0587 (0.0172) | +0.024 |
| Turn | 31.9 (31.5) | 24.98 (23.5) | +0.289 |
| Mover pip count | 116.1 (116) | 105.1 (99.5) | +0.188 |
| Mover pip lead | -1.765 (-5) | -1.56 (-2.5) | -0.006 |
| Random's error (PR) | 82.89 (67.76) | 87.45 (64.6) | -0.051 |
| Stake (trade-off positions) | 0.0586 (0.0011) | 0.044 (0.0006) | +0.144 |

**Balance, reserve 300 pairs:**

| Variable | Nackgammon mean (median) | Standard mean (median) | SMD |
| --- | --- | --- | --- |
| Legal plays | 11.08 (10) | 11.1 (10) | -0.002 |
| Gap, two best (2-ply equity) | 0.0664 (0.0226) | 0.0644 (0.0226) | +0.014 |
| Turn | 30.24 (30) | 25.06 (22) | +0.235 |
| Mover pip count | 116.5 (114) | 106.4 (108) | +0.179 |
| Mover pip lead | -0.7433 (-4) | -6.033 (-4.5) | +0.142 |
| Random's error (PR) | 80.46 (65.95) | 83.63 (67.47) | -0.038 |
| Stake (trade-off positions) | 0.0762 (0.0027) | 0.0593 (0.0017) | +0.109 |

Legal plays and gap are matched (SMD ≤ 0.03). Turn and pip count are not matching variables and differ structurally: Nackgammon games run longer (67 against 55 turns), so its later-phase positions come later in the game, and its start has 194 pips against 167 (opening pip count SMD +3.4; opening turn is matched within 1, SMD −0.25 main). Per-phase balance is in `positions/nack-paired/build-log.json`.

**Tag mix** (contact and holding only; None = opening, race, bear-off):

| Set | blitz | back game | holding | priming | low-anchor | other | None |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Main** | | | | | | | |
| nackgammon | 17 | 10 | 30 | 15 | 7 | 11 | 110 |
| standard | 23 | 2 | 30 | 17 | 8 | 10 | 110 |
| **Reserve** | | | | | | | |
| nackgammon | 28 | 11 | 45 | 24 | 4 | 23 | 165 |
| standard | 32 | 0 | 45 | 37 | 2 | 19 | 165 |

As fixed in §10.4, a Nackgammon side that keeps its starting 23- and 24-points meets the back-game rule: 10 main and 11 reserve Nackgammon back games against 2 and 0 standard.

**Random's error rates** (exact: mean 2-ply loss over all legal plays; drop = Nackgammon − standard, 95% paired bootstrap):

| Main 200: phase (pairs) | Standard PR | Nackgammon PR | Drop [95%] |
| --- | --- | --- | --- |
| all | 87.5 | 82.9 | -4.6 [-16.2, +6.4] |
| opening (60) | 95.6 | 84.3 | -11.3 [-23.3, +0.5] |
| contact (60) | 125.3 | 116.0 | -9.3 [-26.8, +9.1] |
| holding (30) | 113.6 | 121.2 | +7.6 [-54.9, +62.6] |
| race (25) | 19.2 | 22.6 | +3.4 [-7.7, +16.4] |
| bear-off (25) | 13.9 | 14.5 | +0.5 [-5.6, +7.0] |

| Reserve 300: phase (pairs) | Standard PR | Nackgammon PR | Drop [95%] |
| --- | --- | --- | --- |
| all | 83.6 | 80.5 | -3.2 [-11.2, +5.1] |
| opening (90) | 84.8 | 77.5 | -7.3 [-15.4, +1.1] |
| contact (90) | 124.9 | 109.1 | -15.7 [-31.4, -0.6] |
| holding (45) | 96.0 | 120.4 | +24.4 [-6.4, +58.3] |
| race (38) | 27.8 | 34.1 | +6.3 [-11.6, +31.4] |
| bear-off (37) | 22.8 | 17.0 | -5.8 [-28.5, +7.9] |

All 500 pairs: standard 85.2, Nackgammon 81.4, drop -3.7 [-10.4, +2.9].

## What fits in $7.27, and in what order

Only rows a, b, c, d and f cost OpenRouter money (e and g cost none).

1. **a. Terra smoke test: $0.18** (cumulative $0.18). Decides whether Terra joins c, d and f.
2. **b. Paired start, decision models + anchor: $0.36** ($0.54).
3. **c. Paired start, Cup teams + Terra: $1.34** ($1.88; without Terra $0 here).
4. **d. Extension, worst case: $2.55** ($4.43; without Terra $0.54).
5. **e. Knockout: $0 OpenRouter** ($4.43); subscriptions and Gemma's GPU time only. Needs the runner's Nackgammon start first.
6. **f. Terra's League 2 season: $13.5–14.2.** **Does not fit**: after a–e at their worst, $2.84 is left (the $7.27 minus $4.43), less than Terra's own side ($11.0). It needs about $10.7–11.4 more OpenRouter credit (or Terra on a non-OpenRouter key).

So a–e fit in $7.27 with $2.84 to spare at the worst case; f does not. All OpenRouter figures except b's two setups depend on Terra's real token use, known after a.

Waiting for Can's go on every model-call row.

## Update 2026-10-27 18:20 UTC: row a done (Terra smoke), Terra re-estimate, wall-clock times for c, d, e

Can's go of 2026-10-27: a, b, c, d (d capped at $2.55 OpenRouter), e runner change only (no knockout), f skipped.
OpenRouter credit at the start: $115.00 − $107.73 used = **$7.27** (`/api/v1/credits`, 18:05 UTC).

### Row a: GPT-6.1 Terra smoke test (passed)

`jevgammon ask --config leagues/smoke-terra.json --positions positions/smoke.jsonl --out smoke/terra-smoke.db --time-limit 600`
(the 50 smoke positions, bg-v2, the leagues' option-order seed: the procedure of the Part A smoke tests and GLiDE v1.2).

- Setup: `openai/gpt-6.1-terra` (endpoint `openai/gpt-6.1-terra-20261026`) via OpenRouter, pinned to OpenAI's standard
  endpoint (`order: [openai]`, fallbacks off, `require_parameters`; served tier `default`, not flex or fast), reasoning
  effort low, letter constrained by the JSON schema, `max_tokens` 8000 (bounds the budget ledger's worst case).
- First attempt: all 50 refused by OpenRouter with 404 "Filter by Parameters" (no endpoint takes `temperature` or
  `logprobs`; nothing billed). The entry now drops both (`request`: `temperature`, `logprobs`, `top_logprobs` null), so
  Terra is choice only, as GPT-6.1 Sol on the subscription. Then:

| Setup | Answers / failed / timed out | Invalid | p50 / p90 s | Tokens in / out (reasoning) per decision | $ per decision (billed) | Error rate [95% CI] | Δ vs GPT-6.1 Sol (low) (smoke, 2026-10-14) | Δ vs Gemini 3.8 Flash (low) [antigravity] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-6.1 Terra | 50 / 0 / 0 | 0% | 2.4 / 3.7 | 3,087 / 79 (65); max out 446 | $0.00425 | 9.8 [3.4, 18.4] | +4.0 [−0.6, +11.6] (n=50) | −3.8 [−13.6, +4.3] (n=50) |

- **Spent: $0.213 OpenRouter** (estimate was $0.17–0.18). Why higher: OpenRouter bills every Terra prompt as a
  **cache write at $1.25 per M** (`cache_write_tokens` = the prompt, `cached_tokens` 0 in every response), not $1.00.

### Terra re-estimate (from its real smoke tokens)

Input per paired decision 2,943 (smoke 3,087 × Sol's paired/smoke ratio) to 3,087; output 79 to 95 (× 1.2); input at
$1.25 per M (cache write), output $5 per M; +5% retries on the high end. **$0.0041–0.0046 per decision.**

| Row | Terra decisions | Before (Sol-based) | **Re-estimate** | Wall time (18 rpm) |
| --- | --- | --- | --- | --- |
| c (start) | 400 | $1.25–1.34 | **$1.63–1.82** | 22–25 min |
| d (extension, if Terra extends) | +600 | $1.87–2.01 | **$2.44–2.73** | 33–35 min |

**Caps as run** (each enforced by a budget ledger: every attempt reserves its worst case first, `src/budget.rs`):

- a + b: ledger `smoke/nack-paired-budget-abc.db`, cap $1.88 (Terra smoke, DeepSeek V4.1 Flash (off)). Mercury Decide
  (`openrouter-decisions`, no ledger possible) runs under `--max-cost` (b $0.04; real $0.022).
- c (Terra): ledger `smoke/nack-paired-budget-c.db`, **cap $1.82** = the re-estimate's high end.
- d: ledger `smoke/nack-paired-budget-d.db`, cap $2.52 for the ledger setups plus Mercury `--max-cost` $0.03:
  **$2.55 in total**. If Terra extends, its +600 alone may need more than the cap ($2.44–2.73): it then stops at the
  cap and is reported with what it answered (no other spending).
- Worst case a + b + c + d: $0.21 + $0.20 + $1.82 + $2.55 = **$4.78** of the $7.27.

### Wall-clock times (sent before c starts)

- **c (start: Gemini 3.8 Flash (low), Claude Sonnet 5.5 (low), GPT-6.1 Sol (low), GPT-6 Astra (on), GPT-6.1 Sol (high),
  then Terra, Gemma 4 31B (on) last):** the five subscription setups one after another, 35–65 min; Terra 22–25 min;
  Gemma 1.0–1.5 h, started last when its GPU is free. **About 1.5–2.5 h** from the start of c.
- **Gemma 4 31B (on):** bariton **GPU 0**, one replica behind the proxy at `http://127.0.0.1:8894/v1`
  (`GEMMA_GPUS=0 tools/v3/servers/gemma4-31b-replicas.sh`, memory share 0.85, 24 sequences): the League 2 server, same
  image, checkpoint and arguments as League 2 and ladder round 2. Runs with **24 decisions in flight** (`parallel` 24).
  Measured in League 2 on one replica (`v3.db`, 2026-10-19/20): 300–313 decisions per hour at about 17 in flight, about
  200 s per decision; sequentially about 130–210 s per decision, so 400 decisions would be **14–23 h one at a time**.
  With 24 in flight: **about 1.0–1.5 h for the 400** (paired decisions have ≤ 25 plays, no group splits), 1.5–2.3 h for
  a +600 extension.
- **d (extension, worst case: every setup extends):** the setups extend side by side, each after its own first look;
  the long poles are LFM2.5-24B-A2B (on) (4.2–5.5 h on GPU 3) and Gemma 4 31B (on) (1.5–2.3 h); the API and
  subscription setups 1–2 h. **About 5.5–6 h worst case**; only "unclear" setups extend, so likely less.
- **e (knockout, not run now):** 5.0–15.1 h as in the table above (Gemma 4 31B (on) 4.7–5.3 h per match on the same
  GPU 0 server); it waits for c and the roster.
