# League 3 - GPT-6 Astra (high) estimate 2026-10-28

Oct 28, 2026 · for Can. **No league match has run.** Only the approved 20-position smoke test ran (answers in `smoke/astra-high-smoke.db`, git-ignored; config `smoke/astra-high/config.json`, positions `smoke/astra-high/positions.jsonl`). v3.db was only read.

## Setup

- **GPT-6 Astra (high)**: same entry as GPT-6 Astra (on) in v3.db `players.settings` (id 47: spec `openai/gpt-6-astra`, provider `chatgpt-subscription`, Codex backend, subscription login, price $10/M in, $50/M out, `parallel` 4). Only `reasoning` changes: `medium` (Astra (on), the model default) to **`high`**.
- **High works on this route.** The ChatGPT route (`Route::OpenAiSubscription`, `src/players/llm.rs`) sends the configured effort unchanged as `"reasoning": {"effort": ...}`; the harness has no effort allow-list. The smoke requests went out with `"reasoning":{"effort":"high"}`: 20/20 answered, no errors, no retries, and reasoning tokens went up (below). An earlier `GPT-6 Astra (high)` smoke run (Oct 14, `smoke/answers.db`, 28 answers) had also been accepted.
- **League 3 rules, unchanged:** original League 3 seed 3685413082999515901 with the same pair seed derivation (`pair-v1`), prompt `bg-v2`, option-order seed 1190975713392774006, `mirror_concurrent`, 3 rounds, no clock, delay 30 s, 300 max turns.
- **Late entry**, Can's decision: Astra (high) joins the **original League 3 table** (`tools/original_league.py`), not the final ladder table. **Entry date: on approval** (the day its first match starts).
- **Not eligible for the coming Hype Cup.**

## Smoke test (20 positions, run 2026-10-28)

Command: `jevgammon ask --config smoke/astra-high/config.json --positions smoke/astra-high/positions.jsonl --out smoke/astra-high-smoke.db --time-limit 600` (harness be0ee152). It took 72 s. API-eq. $0.84, billed $0.

Positions: Astra (on) has stored `bg-v2` answers on only **10 smoke positions** (smoke-0001 to 0010, `smoke/league3.db`, Oct 20). The other 10 come from the first 10 close-choices stage B positions (`positions/close-choices-b-v2.jsonl`, from `positions/new.jsonl`). Astra (on) answered each of those 5 times (`smoke/close-choices-b.db`, Oct 25). Its repeat 1 is the reference. Same prompt, option-order seed and match context.

| Position | Input tok | Output tok (high) | of which reasoning | Output tok Astra (on) | Latency s | Retries | Invalid | Astra (high) play | Astra (on) play | Same |
|---|---|---|---|---|---|---|---|---|---|---|
| new-0002 | 3,375 | 36 | 19 | 15 | 3.4 | 0 | 0 | 13/11 6/5 | 13/11 6/5 | yes (5/5 of on's repeats) |
| new-0007 | 2,647 | 189 | 172 | 205 | 9.8 | 0 | 0 | bar/20 20/14 | bar/20 13/7 | no (3/5 of on's repeats) |
| new-0009 | 2,906 | 15 | 0 | 15 | 2.7 | 0 | 0 | 13/8 24/23 | 13/8 24/23 | yes (5/5 of on's repeats) |
| new-0016 | 2,726 | 398 | 381 | 63 | 21.7 | 0 | 0 | bar/23 23/18 | bar/23 23/18 | yes (2/5 of on's repeats) |
| new-0024 | 2,718 | 178 | 161 | 148 | 9.9 | 0 | 0 | bar/22 22/16 | bar/22 22/16 | yes (5/5 of on's repeats) |
| new-0040 | 3,815 | 259 | 242 | 144 | 13.9 | 0 | 0 | 21/15* 8/3* | 21/15* 8/3* | yes (5/5 of on's repeats) |
| new-0041 | 3,321 | 61 | 44 | 38 | 4.4 | 0 | 0 | 13/7 7/4* | 13/7 7/4* | yes (5/5 of on's repeats) |
| new-0043 | 3,660 | 144 | 127 | 50 | 9.8 | 0 | 0 | bar/21 bar/21 21/17* 21/17 | bar/21 bar/21 21/17* 21/17 | yes (5/5 of on's repeats) |
| new-0046 | 3,866 | 575 | 558 | 139 | 28.3 | 0 | 0 | 21/15 13/11 | 24/18 13/11 | no (1/5 of on's repeats) |
| new-0050 | 3,117 | 53 | 36 | 15 | 4.0 | 0 | 0 | 13/7 8/7 | 13/7 8/7 | yes (5/5 of on's repeats) |
| smoke-0001 | 3,593 | 305 | 288 | 107 | 18.3 | 0 | 0 | 13/9* 9/8 | 13/9* 9/8 | yes |
| smoke-0002 | 3,257 | 116 | 99 | 87 | 6.8 | 0 | 0 | 24/21 21/16* | 24/21 21/16* | yes |
| smoke-0003 | 3,597 | 15 | 0 | 15 | 3.6 | 0 | 0 | 8/4* 6/4 | 8/4* 6/4 | yes |
| smoke-0004 | 3,527 | 251 | 234 | 217 | 15.9 | 0 | 0 | 13/8 6/5 | 13/8 24/23 | no |
| smoke-0005 | 3,929 | 180 | 163 | 136 | 11.1 | 0 | 0 | 24/18 18/16 | 24/18 18/16 | yes |
| smoke-0006 | 2,724 | 83 | 66 | 33 | 6.1 | 0 | 0 | bar/20* 13/10 | bar/20* 13/10 | yes |
| smoke-0007 | 3,255 | 84 | 67 | 73 | 5.6 | 0 | 0 | 24/20 13/11 | 24/20 13/11 | yes |
| smoke-0008 | 3,248 | 136 | 119 | 84 | 9.3 | 0 | 0 | 13/8 24/20 | 13/8 24/20 | yes |
| smoke-0009 | 3,612 | 508 | 491 | 149 | 27.7 | 0 | 0 | 24/18 24/18 8/2* 8/2 | 24/18 24/18 13/7 13/7 | no |
| smoke-0010 | 2,582 | 88 | 71 | 38 | 6.2 | 0 | 0 | bar/23 13/7 | bar/23 13/7 | yes |

**Totals, high vs Astra (on) (medium) on the same 20:**

| | Astra (high) | Astra (on) | Ratio |
|---|---|---|---|
| Output tokens (reasoning included) | 3,674 (184 per decision) | 1,771 (89) | **2.07×** |
| Reasoning tokens | 3,338 (167) | 1,439 (72) | 2.32× |
| Input tokens | 65,475 (3,274) | same prompts | 1× |
| Mean latency | 10.9 s (max 28.3 s) | 6.5 s | 1.68× (different days) |
| Retries / invalid / timeouts | 0 / 0 / 0 | 0 / 0 / 0 | |
| Same play as Astra (on) | **16/20** (smoke: 8/10, new: 8/10) | | |

Where the two differ: smoke-0004 and smoke-0009 (Astra (on) has 1 answer for each) and new-0007 and new-0046. Astra (on) did not always choose the same play on those two: high's play matches 3 and 1 of Astra (on)'s 5 repeats. On new-0016, high agrees with Astra (on)'s repeat 1, which matches only 2 of its 5 repeats.

## Opponents: original League 3 (12 matches)

`tools/original_league.py` lists 12 setups in League 3, GNUbg weak included: Claude Fable 5.1 (off), (on); Claude Opus 5.5 (off), (on); Gemini 4 Argon (off), (on); GPT-6 Astra (off), (on); Grok 4.7 (off), (on); Kimi K3.1 Pro (off); GNUbg weak. v3.db agrees: Astra (on) and Astra (off) each have one valid finished match against each of the other 11 setups, and also against Sol (low), Sol (high) and Gemini 3.8 Flash (low), which joined through the ladder and are not in the original table.

**One difference to flag:** Can wrote "the other 11 setups". Astra (high) is not one of those 12. Playing every setup in the table means **12 matches**: the 11 that Astra (on)/(off) played, plus Astra (on) itself. For 11 matches, Can would need to say which one to drop. Each row below stands alone, so it can be removed from the total. (The final ladder table also has 12 setups: Sol (low) and Sol (high) instead of Fable (off) and Grok (off). Can ruled it out.)

## Estimate

Method:
- **Decisions:** Astra (high)'s decisions in each match = Astra (on)'s model decisions (forced and no-move turns not counted) in its own League 3 match against the same opponent. The match uses the same pair dice, but games can end differently. Against Astra (on), the basis is match #431 (Astra (off) v Astra (on)), from Astra (on)'s side. Overall: **121–124 decisions per match**; 4 to 8 games per match (6 on average).
- **Price:** $50.27 per 1,000 decisions is Astra (on)'s API-equivalent price on the subscription. Can confirmed this from the site; nothing is billed. Check against v3.db: the 14 valid Astra (on) matches give **$50.07** per 1,000 model decisions ($86.03 / 1,718). Its 11 original-league matches give $50.67. $50.27 is between the two, but I could not reproduce it exactly from v3.db.
- **Most of that price is input:** about 4,456 input tokens = $44.56 at $10/M, plus 110 output tokens = $5.50 at $50/M. Input does not change with effort. Only the output part is scaled by the measured **2.07×**: $50.27 − $5.50 + $5.50 × 2.07 = **$56.18 per 1,000 decisions**. Upper bound if the whole $50.27 were scaled by 2.07: $104.3 per 1,000.
- **Time:** Astra (on) averaged 7.4 s per decision in League 3. High ≈ 7.4 × 1.68 = **12.4 s**. Each match then takes about (decisions × 5 s extra) / 2 longer than its basis match, because the mirrored legs run at the same time.

| # | Opponent | Opponent route | Basis: Astra (on) match | Games | Astra (high) decisions | Astra (high) API-eq. (not billed) | Opponent decisions | Opponent API-eq. / billed | Opponent s/decision | Basis match min | Est. match wall min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Claude Fable 5.1 (off) | Claude subscription | #455 | 6 | 159 | $8.93 | 133 | $7.88 / $0 | 2.8 | 14 | 21 |
| 2 | Claude Fable 5.1 (on) | Claude subscription | #461 | 4 | 85 | $4.78 | 75 | $11.81 / $0 | 24.8 | 22 | 26 |
| 3 | Claude Opus 5.5 (off) | Claude subscription | #433 | 6 | 115 | $6.46 | 135 | $4.43 / $0 | 6.2 | 18 | 23 |
| 4 | Claude Opus 5.5 (on) | Claude subscription | #435 | 6 | 154 | $8.65 | 123 | $3.93 / $0 | 9.8 | 25 | 31 |
| 5 | GNUbg weak | local | #430 | 6 | 138 | $7.75 | 136 | $0 | 0.0 | 8 | 14 |
| 6 | GPT-6 Astra (off) | ChatGPT subscription | #431 | 6 | 144 | $8.09 | 146 | $6.62 / $0 | 6.3 | 17 | 23 |
| 7 | GPT-6 Astra (on) | ChatGPT subscription | #431 (Astra (on)'s side) | 6 | 144 | $8.09 | 146 | $7.31 / $0 | 7.4 | 17 | 23 |
| 8 | Gemini 4 Argon (off) | Antigravity subscription | #445 | 4 | 91 | $5.11 | 90 | $0.93 / $0 | 6.6 | 10 | 14 |
| 9 | Gemini 4 Argon (on) | Antigravity subscription | #462 | 8 | 182 | $10.22 | 149 | $6.05 / $0 | 50.1 | 81 | 89 |
| 10 | Grok 4.7 (off) | xAI subscription | #466 | 6 | 112 | $6.29 | 126 | $4.09 / $0 | 75.9 | 94 | 99 |
| 11 | Grok 4.7 (on) | xAI subscription | #476 | 4 | 76 | $4.27 | 77 | $8.48 / $0 | 229.2 | 195 | 198 |
| 12 | Kimi K3.1 Pro (off) | OpenRouter (billed) | #604 | 6 | 111 | $6.24 | 115 | **$0.42 OpenRouter** | 3.0 | 11 | 16 |
| | **Total (12 matches)** | | | 68 | **1,511** | **$84.89** | 1,451 | $61.53 API-eq. + $0.42 OpenRouter | | 512 | |

**Summary**

| | Value |
|---|---|
| Matches | 12 (11 if Can drops one; see above) |
| Astra (high) decisions | **≈ 1,511** |
| Astra (high) API-equivalent | **≈ $85** ($56.18/1,000), upper bound $158 (whole $50.27 × 2.07). Astra (on) at medium for the same decisions: $76 |
| Astra (high) billed | **$0** (ChatGPT subscription) |
| Opponents on subscriptions (Claude, Gemini, Grok, GPT) | $0 billed; time only (≈ $62 API-eq., for reference) |
| Opponents on OpenRouter | **Kimi K3.1 Pro (off) only**: ≈ **$0.42** (Kimi's 14 v3.db matches: $0.24–0.61 each) |
| Wall-clock, all 12 started together as in League 3 | **≈ 3.5 h**: the longest match is Grok 4.7 (on), ≈ 3.3 h, set by Grok's 229 s per decision. 11 of the 12 finish within ≈ 1.5 h. Astra's own request time is 1,511 × 12.4 s ≈ 5.2 h, which `parallel` 4 brings to ≥ 1.3 h. |
| Wall-clock, one match at a time | ≈ 9.5 h |

**Subscription quota / rate-limit risk: low.** `league3.log` has no 429, rate-limit or usage-limit lines for Astra. The only quota errors in it are OpenRouter's 403 "Key limit exceeded" for Kimi. In v3.db, 232 of Astra (on)'s 1,718 decisions needed more than one attempt (up to 13). That added 553 s in total, and the stored exchanges do not give a reason. High sends the same number of requests with about 2× the output, so it uses more Codex quota per request. Astra (off), Astra (on), Sol (low) and Sol (high) share the same ChatGPT login, but none of them is playing now.

## OpenRouter credit (Kimi's match)

`/api/v1/credits` now (2026-10-28): $120.00 total − $114.53 used = **$5.47 left**. Can's planned ≈ $2 top-up does not show yet.

Order of claims on that credit, worst cases:

| Step | Claim | Left after |
|---|---|---|
| 0 | Now | $5.47 |
| 1 | 4 DeepSeek V4.1 Flash 1017 (on) gap matches (running): cap $3.60, ledger shows $1.72 spent, so up to $1.88 more | $3.59 |
| 2 | Terra (high), if approved: smoke $0.37 + (b) worst $2.90 | $0.32 |
| 3 | Kimi K3.1 Pro (off) v Astra (high): est. $0.42, worst $0.61 | **−$0.10 to −$0.29** |
| — | Argon (high) (subscription) | $0 |

- **Fits:** DeepSeek gaps + Kimi (≈ $3.0 left), or DeepSeek gaps + Terra (high).
- **Does not fit at worst case:** all three. That needs about $0.30 more credit; the ≈ $2 top-up covers it.
- Kimi's own ledger (`smoke/kimi-k31-budget.db`) has $9.73 of its $30 cap spent, so the cap is not the limit.

## Open question

Which roster: Can chose the **original League 3 table**. That means **12 opponents** (the 10 non-Astra setups, GNUbg weak included, plus Astra (on) and Astra (off)). Can wrote 11: is it 12 matches, or which one should be dropped?

Waiting for Can's approval.
