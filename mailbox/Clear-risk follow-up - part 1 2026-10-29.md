# Clear-risk follow-up: Part 1 (checks 2–4, check-1 sample and rollout estimate) and the Part 2 estimate (2026-10-29)

Offline. No model was called, nothing was rolled out on the sample, and the site and the thread were not changed.
GNUbg 1.08.003 ran on CPU only (`nice -n 19`, at most 8 threads, no GPU). Data: `v3.db` read-only, the site's GNUbg
shards (`~/.local/state/bg-site/plays/s*.db`) and the kept decisions of the scan
(`mailbox/Clear-risk scan - results 2026-10-29.md`: 25,199 kept, 7,997 Risk wins, 17,202 Safety wins).

**Waiting for Can's go on two things:** (1) the check-1 rollouts (the decisions are listed at the end), and (2) Part 2.

**Files.**
- `… - check 2.csv`: missed and needless risks per setup and band.
- `… - check 3.csv`: equity lost per setup, group and bin.
- `… - sample.csv`: the 200 sample positions.

All three are in `mailbox/` and start with "Clear-risk follow-up - part 1 2026-10-29".

**Conventions.**
- **Bands** are \|3-ply gap\|: 0.04–0.08, 0.08–0.15 and 0.15+. The lower edge of each band is included.
- **Bins** go by the hitting rolls stored in `STATE/plays`: safe is 0, in between is 1–11, unsafe is 12 or more.
- **"Setups (pooled)"** means the 45 setups other than the three programs, Random, Safest and GNUbg weak. Each
  decision counts once.
- **"(few)"** marks a cell with under 30 positions.

## Check 4: where the best play is (said first, as asked)

**The best legal play is in between in 22% of Risk wins and 16% of Safety wins.** That is about one decision in five
or six. It is not the majority, but in those decisions neither of the two plays we compare is the best play.

By construction, the best play can never be in the "wrong" bin. In a Risk win the best unsafe play beats the best safe
play by 0.04 or more, so the best play is unsafe or in between, and the reverse holds for Safety wins. The best play
is taken at 2-ply over all legal plays. There are no ties across bins.

| | best play safe | best play in between | best play unsafe | kept decisions |
|---|---:|---:|---:|---:|
| **Risk wins**, all leagues | 0 | **22.4% (1,793)** | 77.6% (6,204) | 7,997 |
| Risk wins, L1 / L2 / L3 | 0 / 0 / 0 | 23.8% (799) / 21.4% (715) / 21.3% (279) | 2,554 / 2,622 / 1,028 | 3,353 / 3,337 / 1,307 |
| Risk wins, band 0.04–0.08 / 0.08–0.15 / 0.15+ | 0 | 29.1% (677) / 19.2% (426) / 20.0% (690) | 1,646 / 1,792 / 2,766 | 2,323 / 2,218 / 3,456 |
| **Safety wins**, all leagues | 84.0% (14,443) | **16.0% (2,759)** | 0 | 17,202 |
| Safety wins, L1 / L2 / L3 | 5,185 / 6,459 / 2,799 | 16.7% (1,038) / 16.2% (1,245) / 14.5% (476) | 0 | 6,223 / 7,704 / 3,275 |
| Safety wins, band 0.04–0.08 / 0.08–0.15 / 0.15+ | 1,721 / 3,396 / 9,326 | 23.4% (527) / 18.6% (777) / 13.5% (1,455) | 0 | 2,248 / 4,173 / 10,781 |

Counted over distinct (position, dice) instead of decisions, the shares are about the same: 21.3% (1,507 of 7,086)
for Risk wins and 16.7% (2,670 of 16,016) for Safety wins. In-between is most often best in the smallest band
(0.04–0.08).

## Check 2: missed and needless risks per 3-ply gap band

Same definitions as the scan:
- **Missed:** a Risk win played safe.
- **Needless:** a Safety win played unsafe.
- **Bias** = missed% − needless%.

The tables per setup are in the appendix and in the CSV.

| band | setups (pooled): missed | needless | bias | median setup bias | *random legal play, L1 / L2 / L3: missed · needless* |
|---|---:|---:|---:|---:|---|
| 0.04–0.08 | 59.1% (1,250/2,114) | 6.0% (123/2,060) | +53.2 pp | +50.7 pp | 16.6 / 17.4 / 18.6% · 66.0 / 63.2 / 61.7% |
| 0.08–0.15 | 65.4% (1,340/2,048) | 4.7% (179/3,778) | +60.7 pp | +60.0 pp | 17.7 / 17.8 / 20.8% · 65.8 / 64.0 / 62.5% |
| 0.15+ | 54.5% (1,735/3,186) | 2.4% (239/9,938) | +52.1 pp | +47.1 pp | 15.3 / 15.9 / 17.7% · 55.2 / 53.4 / 50.6% |

- **Missed risks do not fall as the gap grows** (59%, then 65%, then 55%). Needless risks do fall (6.0%, 4.7%,
  2.4%).
- **Bias by setup:** it is higher in the 0.15+ band than in the 0.04–0.08 band for 19 of 45 setups, and lower for 26.
- **Small cells:** 10 setup × band cells have fewer than 30 positions in one group (5 in each of the two lower bands).

The five Part-2 models (missed n/N · needless n/N · bias):

| setup (league) | 0.04–0.08 | 0.08–0.15 | 0.15+ |
|---|---|---|---|
| Celeris-1 Decision (L1) | 33/41 · 0/53 · +80.5 | 41/50 · 0/96 · +82.0 | 63/77 · 4/259 · +80.3 |
| Jev 1.14.0 (L2) | 37/60 · 1/45 · +59.4 | 49/62 · 4/88 · +74.5 | 53/65 · 5/214 · +79.2 |
| Liquid d1-ultra (L2) | 16/37 · 6/57 · +32.7 | 32/65 · 6/90 · +42.6 | 36/69 · 6/267 · +49.9 |
| Claude Sonnet 5.5 (high) (L2) | 28/52 · 1/53 · +52.0 | 36/60 · 0/102 · +60.0 | 39/82 · 1/273 · +47.2 |
| GPT-6.1 Sol (high) (L3) | 9/28 (few) · 0/38 · +32.1 | 14/29 (few) · 3/68 · +43.9 | 5/31 · 3/228 · +14.8 |

## Check 3: equity lost per bin

**Equity lost** is the 2-ply equity of the best legal play minus the 2-ply equity of the chosen play. Each cell gives
the mean, then the count in brackets.

**Took the right risk:** a Risk win played unsafe, where the chosen play is within 0.02 of the best unsafe play.

| | Risk wins: chose safe | in between | unsafe | took the right risk | Safety wins: chose safe | in between | unsafe |
|---|---:|---:|---:|---:|---:|---:|---:|
| setups (pooled) | 0.205 (4,325) | 0.073 (1,617) | 0.095 (1,406) | 53.3% (749/1,406) | 0.035 (13,928) | 0.084 (1,307) | 0.280 (541) |
| *GNUbg weak, all leagues* | | | | 53.5% (136/254) | | | |
| *Random, L1* | | | | 6.4% (3/47) | | | |
| Celeris-1 Decision | 0.222 (137) | 0.055 (22) | 0.055 (9) | 5/9 (few) | 0.052 (387) | 0.093 (17) | 0.304 (4) |
| Jev 1.14.0 | 0.185 (139) | 0.094 (32) | 0.074 (16) | 37.5% (6/16) (few) | 0.041 (312) | 0.082 (25) | 0.251 (10) |
| Liquid d1-ultra | 0.241 (84) | 0.070 (50) | 0.088 (37) | 48.6% (18/37) | 0.042 (352) | 0.072 (44) | 0.243 (18) |
| Claude Sonnet 5.5 (high) | 0.173 (103) | 0.031 (52) | 0.064 (39) | 59.0% (23/39) | 0.018 (395) | 0.043 (31) | 0.150 (2) |
| GPT-6.1 Sol (high) | 0.122 (28) | 0.038 (24) | 0.032 (36) | 69.4% (25/36) | 0.012 (292) | 0.013 (36) | 0.191 (6) |

- **In Risk wins, playing safe costs about 0.2 per decision on average.** An in-between play (0.073) or an unsafe play
  (0.095) costs far less.
- **About half of the unsafe choices in Risk wins took the right risk.** The pooled setups reach 53%, the same as
  GNUbg weak.

## Check 1: the 200-position sample (drawn) and the rollout estimate (not run)

### Draw rule and seed

- **Pool:** the scan's kept decisions, split into 6 strata: group (Risk wins / Safety wins) × 3-ply band.
- **One entry per position:** within a stratum, each distinct (position from the mover's side, dice) counts once. The
  representative is its earliest turn id. Other kept turns of the same position are listed in the CSV; 4 sample
  positions have one.
- **Bray excluded:** the exclusion was checked by board. No kept decision has the Bray board, which is not league data.
- **Quotas per group:** 34 / 33 / 33 for the bands 0.04–0.08 / 0.08–0.15 / 0.15+, so 100 per group and 200 in all.
- **Draw:** Python `random.Random(2026102901).sample(pool, quota)`. Each stratum's pool is sorted by turn id. The
  strata are drawn in the order Risk 0.04–0.08, 0.08–0.15, 0.15+, then Safety in the same band order, from one
  generator.
- **Pool sizes (distinct positions):**

  | group | 0.04–0.08 | 0.08–0.15 | 0.15+ |
  |---|---:|---:|---:|
  | Risk wins | 1,767 | 2,043 | 3,276 |
  | Safety wins | 2,136 | 3,598 | 10,282 |

- **Code:** `/tmp/clearrisk/fu.py` (draw) and `samplecsv.py` (CSV, with GNUbg position IDs, and the hitting rolls of
  both plays checked again with `describe_with_shots`; all match).

**What the sample holds**
- **By league:** 72 positions from L1, 101 from L2 and 27 from L3.
- **Back game:** **8** positions (3 Risk, 5 Safety).
- **Prime-vs-prime:** **9** (6 Risk, 3 Safety).
- **With an in-between play:** 138.
- **With a play at least 0.10 below the shown plays at 2-ply:** 170.
- **With both:** 125.

### Rollout settings (as in the Bray rollout, except where marked)

- **Engine:** GNUbg 1.08.003 on CPU, `nice -n 19`, `set threads 8`.
- **Games:** 1,296 per play. Variance reduction (lookahead) on. Quasi-random dice. Mersenne Twister with seed
  20261029; both plays use the same seed.
- **Length:** no truncation. GNUbg ends cubeless games at its one-sided bear-off database.
- **Cube:** cubeless, in a money session (`matchto` 0). The initial-position option, the "later" settings and the
  STD/JSD stops are all off.
- **Checker play:** cubeless, prune, noise 0, deterministic, with GNUbg's default move filter. The plies are
  **Can's decision (0 or 2)**. Cube-decision plies are set to the same value, but they are not used cubelessly.
- **What is rolled out:** the position after the play, with the opponent on roll and the dice not rolled. GNUbg prints
  the equity for the opponent; it is negated.
- **Scoring is 1/2/3 points.** The printed cubeless equity counts gammons and backgammons. Bray's −0.403 equals
  2·0.355 − 1 + (0.138 − 0.240) + (0.004 − 0.015).
- **Jacoby:**
  - The session default has Jacoby on, so the session's cubeinfo shows gammon price 0.
  - I checked whether it changes cubeless rollouts. On the 8 timing rollouts at 0-ply, Jacoby on and off gave
    **identical** results (8 of 8). It does not change cubeless rollouts.
  - I would still set it off explicitly, so the record is unambiguous.
- **Agreement rule (Can's):** same direction and \|rollout gap\| ≥ 0.04. The scan's pre-registration had a further
  condition, gap > 3 standard errors. **Can should decide whether to add it.**

### CPU time

**Measured on 4 kept positions not in the sample.**
- **Choice:** one per group in the 0.04–0.08 band and one per group in the 0.15+ band, drawn with seed 2026102902. No
  sample position was rolled out.
- **Size:** their total pip counts are 280, 240, 288 and 122. The sample averages 242 (median 257), and Bray has 270.

| position | play | 0-ply checker play: wall / CPU | 2-ply checker play: wall / CPU |
|---|---|---:|---:|
| Risk, 0.04–0.08 (turn 29322) | safe / unsafe | 2.9 s / 22.9 s · 2.8 s / 21.7 s | 68.8 s / 548 s · 64.5 s / 514 s |
| Risk, 0.15+ (turn 44334) | safe / unsafe | 1.7 / 13.5 · 1.8 / 14.0 | not timed |
| Safety, 0.04–0.08 (turn 92426) | safe / unsafe | 3.1 / 24.7 · 3.4 / 26.8 | not timed |
| Safety, 0.15+ (turn 187946) | safe / unsafe | 0.2 / 1.1 · 0.3 / 1.9 | 3.5 / 28 · 8.7 / 69 |
| Bray (earlier run) | safe / unsafe | 2.2 / ≈18 · 2.9 / ≈23 (wall × 8) | 75.3 / 601 · 77.0 / 612 |

- **0-ply:** a mean of **≈ 17 CPU-s per rollout** (10 rollouts).
- **2-ply over 0-ply:** 24–37 times as long, mean ≈ 28 (6 pairs). That gives **≈ 470 CPU-s per 2-ply rollout**. The
  measured 2-ply rollouts average 395 CPU-s, and Bray is the longest at about 606.

| 400 rollouts (200 positions × 2 plays) | CPU | wall at 8 threads |
|---|---:|---:|
| 0-ply checker play | ≈ 1.9 CPU-h (max ≈ 3 if every position were as long as the longest timed) | **≈ 15–25 min** |
| **2-ply checker play** | ≈ 53 CPU-h (range 44–67, the top being every position as long as Bray) | **≈ 6.5 h (5.5–8.5 h)** |

**Recommendation: 2-ply checker play.**
- It is the pre-registered setting and the one used for Bray.
- At about 6.5 hours (overnight on 8 threads) it is affordable.
- 0-ply checker play makes more mistakes inside the games, which matters most in the back-game and prime-vs-prime
  positions Can wants reported. It also uses the same network that the 2-ply and 3-ply values we are testing are
  built from, so it is a less independent check.
- Illustration only, on the one timed middle-game position (not in the sample): the rollout gap was +0.077 at 0-ply
  and +0.099 at 2-ply.

## Part 2: cost and time estimate (nothing built, nothing called)

### Requests

Requests = models × positions × (Q1 + Q2 + Q3 requests) × 2 versions. The positions are at most 200; only those the
rollout confirms will be used.

| | Q3 requests | requests per position | requests (200 positions) |
|---|---:|---:|---:|
| Chat models (Sonnet, Sol) | 1 | 3 × 2 = 6 | 1,200 each |
| Decision models (Celeris, Jev, Liquid) | 4 (one per value; 3 when there is no in-between play) | 6 × 2 = 12 | 2,400 each |
| **Total** | | | **9,600** (upper bound) |

### Tokens, price and time

- **Tokens and time** are each model's league averages per request (`v3.db`, the model's valid decisions, tokens in
  `turns` ÷ requests per decision). League prompts list every legal play, while these list 2 to 5, so **input tokens
  are an upper bound**. [INFERENCE] Output for Q3 may be longer than in league play.
- **Prices** come from `tools/site/content/setups.json`.
- **Wall times** use the league's parallelism (2 for decision models, 4 for chat models).

| model | how it runs | requests | in tokens / req | out tokens / req | price per Mtok in / out | cost | s / req | wall |
|---|---|---:|---:|---:|---|---:|---:|---:|
| Celeris-1 Decision | hosted API (`inference.celeris.ai`) | 2,400 | 3,719 | 0 | $0.04 / free | **$0.36** | 0.21 | ≈ 4 min |
| Jev 1.14.0 | hosted API (TypeSafe, `api.typesafe.ai`) | 2,400 | 4,055 | 279 | $0.042 / free | **$0.41** | 0.22 | ≈ 4 min |
| Liquid d1-ultra | hosted API (`api.liquid.ai/decisions`, paid tier) | 2,400 | 3,403 | 0 | $0.042 / free | **$0.34** | 0.34 | ≈ 7 min |
| Claude Sonnet 5.5 (high) | Claude subscription (senarantv@gmail.com) | 1,200 | 4,407 | 650 | $2 / $10, API-equivalent | **$18.38 equiv.** | 7.0 | ≈ 35 min |
| GPT-6.1 Sol (high) | ChatGPT/Codex subscription | 1,200 | 3,297 | 321 | $2 / $10, API-equivalent | **$11.76 equiv.** | 17.1 | ≈ 1.5 h |

- **Cost:** about **$1.11 cash** for the three hosted decision APIs, plus about **$30 API-equivalent** on the
  subscriptions.
- **Claude limit:** about 4% of the Claude 5-hour window, which is about $450 API-equivalent according to
  `mailbox/Nackgammon - Argon (high) estimate 2026-10-28.md`. No numeric ChatGPT limit is recorded.
- **Total wall:** about 2 hours of model time, provided the subscriptions are free.

**Correction to the brief: there is no local GPU model.**
- Celeris-1 Decision and Jev 1.14.0 played the league through hosted APIs, not on our GPUs.
- Evidence: `players.settings` in `v3.db` gives the providers `celeris` and `jev`. In `src/players/decision.rs` these
  are `https://inference.celeris.ai/celeris-1-decision/v1/systemone` and TypeSafe `https://api.typesafe.ai/v1/systemone`.
  No `*_BASE_URL` override was found.
- So no server or GPU of ours is involved. I did not check whether the APIs are up, because that needs a request.
- This machine's 4 GPUs are busy with other work: exp-grpo, pplx-decider + vLLM, and ai-toolkit.

**Subscriptions now (19:44 UTC).** `season2-queue` is active, running `run_knockout_nack.sh`.
- **Claude, busy now:** semi-final B is running, Claude Fable 5.1 (on) on the Claude subscription v Grok 4.7. It has
  run since 15:26 and stood 3–3 after 2 of 3 rounds.
- **Queued next:**
  1. The final: Sol (high) on ChatGPT v the SF-B winner. If Fable wins, that uses Claude again.
  2. The Codex effort sweep: 6 rows, all ChatGPT.
- **When Part 2 can run:**
  - **Sonnet** only after SF-B ends, and after the final too if Fable wins.
  - **Sol** only after the final and the sweep, unless Can reorders the queue.
  - The three decision models can run at any time.
- [INFERENCE] The queue files give no end time. Past matches suggest SF-B needs 1–2 h more and the final 1–7 h, so
  the ChatGPT subscription is likely busy into 30 Oct.

## Decisions for Can

**Part 1, rollouts**
1. **Go**, with checker play at **2-ply** (recommended; about 53 CPU-h, about 6.5 h wall on 8 threads) or at 0-ply
   (about 2 CPU-h, about 20 min).
2. Should the confirmation rule add **> 3 SE** (the pre-registered rule) to "same direction and gap ≥ 0.04"?
3. **Back-game and prime-vs-prime agreement:** the random sample holds only **8 and 9** such positions, too few for
   shares. Should those strata be oversampled (for example, an extra 30 each, rolled out separately and not part of the
   200)?
4. Set Jacoby off explicitly? It makes no difference to the results (checked), but it makes the record clear.

**Part 2, design**
5. **Decision models answer with probabilities, not letters.**
   - The proposed reading takes the highest-probability option as the answer and keeps all the probabilities.
   - Celeris rounds its probabilities to 2 decimals, so ties such as 0.50/0.50 can happen. They need a rule: wrong,
     or half right.
   - "Share of A answers" for decision models would then mean the first option shown.
6. **Q2 does not test much in the "with numbers" version.** The usual prompt prints hits, new points made and the
   longest prime for every play, so 3 of the 4 options can be read off the text.
7. **Q2 scoring, on the sample** (consequences computed from the boards, B = best unsafe, A = best safe):
   - **121 of 200** items have no option that is true for B and not for A. Under the rule as written, "none" is the
     right answer **60.5%** of the time, so a model that always says "none" scores 60.5%.
   - **43** of those items have an option true for both A and B. Can should say whether "none" is right there.
   - **15** items have two right options.
   - How often each option is right: hits 39, moves out of the opponent's home board 40, new point 9, longer prime 6.
   - **Random baseline:** 21.5% if "none" is right when no option is true for B and not A; 17.2% if "none" is right
     only when nothing is true for B (43 items then have no right answer).
   - **Decide:** the rule for "none", and whether to keep only items with exactly one right answer.
8. **Q3 items**
   - **62 of 200** positions have no in-between play, so they get 3 values.
   - **30 of 200** have no play at least 0.10 below the shown plays at 2-ply. Drop the blunder there, or use the worst
     legal play anyway?
   - The in-between and blunder plays need 3-ply values. These are not computed yet; they are cheap, about 0.14 CPU-s
     per play.
9. **Q3 for decision models**
   - The four questions are independent, so the answers need not be one-to-one: two values can go to the same play.
   - **Pair-order scoring needs a rule:** take the argmax per value and count the duplicates' pairs as wrong, or take
     the most probable one-to-one assignment from the probabilities.
   - **For chat models:** require a one-to-one mapping in the JSON schema, and treat any other answer as invalid?
   - Decision models get 4 requests for Q3 and chat models 1, so their Q3 numbers are not on the same footing.
10. **"Board only" prompt**
    - The runner already has the `bg-v2-notation` variant (plays as bare notation, ablation A2), which can be reused.
    - Its state still shows **the race (pip counts)**. Are pip counts "computed numbers" to remove?
11. **Temperature:** none of the five sends a temperature in league play, so each runs at the provider's default.
    Record it as "not sent (provider default)". Reasoning effort is high for Sonnet and Sol; Sonnet has max_tokens
    32,000.
12. **Building Part 2 needs new runner code.** Q1 fits the league's choice format. Q2 (5 options) and Q3 (a value-to-play
    mapping) are new question types for chat models, and Q3 adds a per-value question for decision models.
13. **Schedule for the subscription runs:** put the Sonnet and Sol runs into the season-2 queue, which runs one job per
    subscription at a time, or pause the queue?
14. **League comparison is not paired.** The five models played in different leagues (Celeris in L1; Jev, Liquid and
    Sonnet in L2; Sol in L3). Most sample positions were played by other setups. The "compare with league numbers" rows
    therefore compare loosely.

## Appendix A: check 2 per setup (missed · needless · bias, per 3-ply gap band)

Cells: share (n/N); "(few)" = under 30 positions. Bias in percentage points. Same data in `… - check 2.csv`.

### League 1

| setup | 0.04-0.08: missed | 0.04-0.08: needless | 0.04-0.08: bias | 0.08-0.15: missed | 0.08-0.15: needless | 0.08-0.15: bias | 0.15+: missed | 0.15+: needless | 0.15+: bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Celeris-1 Decision | 80.5% (33/41) | 0.0% (0/53) | +80.5 pp | 82.0% (41/50) | 0.0% (0/96) | +82.0 pp | 81.8% (63/77) | 1.5% (4/259) | +80.3 pp |
| Cygnet (Gemma 4 12B) | 82.2% (60/73) | 0.0% (0/35) | +82.2 pp | 75.5% (40/53) | 8.7% (6/69) | +66.8 pp | 71.9% (82/114) | 2.1% (4/193) | +69.9 pp |
| Decider Flash v1.2 | 62.2% (28/45) | 15.0% (9/60) | +47.2 pp | 51.7% (15/29) (few) | 18.3% (17/93) | +33.4 pp | 46.5% (40/86) | 11.3% (21/186) | +35.2 pp |
| Decider v1.1 27B | 59.6% (31/52) | 11.4% (4/35) | +48.2 pp | 78.7% (37/47) | 6.8% (6/88) | +71.9 pp | 65.8% (50/76) | 6.9% (17/246) | +58.9 pp |
| Decider v1.2 27B | 58.8% (20/34) | 8.3% (4/48) | +50.5 pp | 70.3% (26/37) | 4.4% (4/91) | +65.9 pp | 68.9% (51/74) | 3.6% (8/222) | +65.3 pp |
| DeepSeek V4.1 Flash (off) | 69.4% (34/49) | 0.0% (0/41) | +69.4 pp | 70.8% (34/48) | 1.4% (1/71) | +69.4 pp | 55.7% (54/97) | 1.6% (3/187) | +54.1 pp |
| Fastino GLiDE v1.2 (local) | 63.3% (31/49) | 13.0% (7/54) | +50.3 pp | 69.0% (20/29) (few) | 8.0% (7/88) | +61.0 pp | 60.7% (37/61) | 4.7% (13/275) | +55.9 pp |
| GNUbg weak | 10.0% (4/40) | 28.6% (10/35) | -18.6 pp | 0.0% (0/25) (few) | 31.8% (27/85) | -31.8 pp | 0.0% (0/39) | 5.2% (10/192) | -5.2 pp |
| GPT-6 Luna | 80.6% (54/67) | 4.3% (2/46) | +76.2 pp | 90.5% (38/42) | 1.2% (1/85) | +89.3 pp | 75.0% (66/88) | 2.0% (4/199) | +73.0 pp |
| Jev 1.13.0 | 78.6% (33/42) | 0.0% (0/43) | +78.6 pp | 80.4% (45/56) | 0.0% (0/88) | +80.4 pp | 74.7% (65/87) | 1.3% (3/223) | +73.4 pp |
| LFM2.5-24B-A2B (off) | 78.4% (40/51) | 22.0% (9/41) | +56.5 pp | 69.4% (34/49) | 8.9% (7/79) | +60.5 pp | 52.6% (41/78) | 8.2% (13/158) | +44.3 pp |
| LFM2.5-24B-A2B (on) | 65.2% (43/66) | 33.3% (14/42) | +31.8 pp | 61.0% (25/41) | 12.5% (12/96) | +48.5 pp | 44.9% (35/78) | 7.8% (17/218) | +37.1 pp |
| Mercury Decide | 61.3% (38/62) | 2.2% (1/45) | +59.1 pp | 86.8% (46/53) | 1.4% (1/74) | +85.4 pp | 82.4% (84/102) | 1.1% (2/188) | +81.3 pp |
| Open-Jev 27B v1.1 | 33.3% (11/33) | 26.3% (10/38) | +7.0 pp | 53.7% (22/41) | 19.4% (18/93) | +34.3 pp | 57.1% (36/63) | 19.4% (34/175) | +37.7 pp |
| Qwen3.8-27B (off) | 60.9% (28/46) | 3.6% (2/55) | +57.2 pp | 78.7% (59/75) | 2.5% (2/80) | +76.2 pp | 78.2% (86/110) | 1.0% (2/196) | +77.2 pp |
| Random | 13.0% (3/23) (few) | 78.3% (18/23) (few) | -65.2 pp | 25.0% (4/16) (few) | 76.1% (35/46) | -51.1 pp | 29.3% (12/41) | 53.2% (33/62) | -24.0 pp |
| Safest | 100.0% (70/70) | 0.0% (0/48) | +100.0 pp | 100.0% (72/72) | 0.0% (0/103) | +100.0 pp | 100.0% (91/91) | 0.0% (0/178) | +100.0 pp |
| SubQ Snap Preview | 47.3% (26/55) | 17.6% (9/51) | +29.6 pp | 61.4% (27/44) | 10.0% (9/90) | +51.4 pp | 51.9% (42/81) | 4.0% (10/247) | +47.8 pp |
| Winnow-12B | 58.7% (27/46) | 12.2% (6/49) | +46.5 pp | 69.7% (46/66) | 6.5% (5/77) | +63.2 pp | 57.0% (53/93) | 6.5% (12/185) | +50.5 pp |
| *Random legal play (expected)* | 16.6% (156.6/944) | 66.0% (555.4/842) | -49.4 pp | 17.7% (154.9/873) | 65.8% (1047.0/1592) | -48.0 pp | 15.3% (235.6/1536) | 55.2% (2091.6/3789) | -39.9 pp |

### League 2

| setup | 0.04-0.08: missed | 0.04-0.08: needless | 0.04-0.08: bias | 0.08-0.15: missed | 0.08-0.15: needless | 0.08-0.15: bias | 0.15+: missed | 0.15+: needless | 0.15+: bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (off) | 50.0% (26/52) | 5.1% (2/39) | +44.9 pp | 69.8% (30/43) | 5.6% (5/90) | +64.2 pp | 24.3% (17/70) | 0.4% (1/256) | +23.9 pp |
| Claude Sonnet 5.5 (high) | 53.8% (28/52) | 1.9% (1/53) | +52.0 pp | 60.0% (36/60) | 0.0% (0/102) | +60.0 pp | 47.6% (39/82) | 0.4% (1/273) | +47.2 pp |
| Claude Sonnet 5.5 (low) | 63.0% (34/54) | 0.0% (0/61) | +63.0 pp | 68.5% (37/54) | 3.1% (3/96) | +65.4 pp | 54.8% (34/62) | 0.0% (0/309) | +54.8 pp |
| Clef | 56.9% (29/51) | 18.9% (10/53) | +38.0 pp | 63.3% (31/49) | 14.4% (15/104) | +48.8 pp | 48.8% (40/82) | 6.0% (11/183) | +42.8 pp |
| DeepSeek V4.1 Flash (on) | 56.5% (35/62) | 3.0% (2/66) | +53.4 pp | 64.6% (31/48) | 5.1% (6/118) | +59.5 pp | 31.2% (24/77) | 0.3% (1/288) | +30.8 pp |
| DeepSeek V4.1 Flash 1017 (off) | 66.0% (33/50) | 1.8% (1/56) | +64.2 pp | 76.4% (42/55) | 2.0% (2/99) | +74.3 pp | 73.0% (65/89) | 0.0% (0/240) | +73.0 pp |
| DeepSeek V4.1 Flash 1017 (on) | 55.2% (32/58) | 7.7% (5/65) | +47.5 pp | 59.6% (28/47) | 2.6% (3/114) | +56.9 pp | 40.0% (32/80) | 0.7% (2/297) | +39.3 pp |
| Fastino GLiDE | 65.8% (25/38) | 0.0% (0/73) | +65.8 pp | 51.9% (27/52) | 6.2% (6/96) | +45.7 pp | 40.9% (27/66) | 5.0% (12/241) | +35.9 pp |
| GLM-5.3 (on) | 75.5% (40/53) | 0.0% (0/52) | +75.5 pp | 79.1% (34/43) | 1.1% (1/92) | +78.0 pp | 70.1% (68/97) | 0.0% (0/221) | +70.1 pp |
| GNUbg weak | 11.1% (4/36) | 40.7% (22/54) | -29.6 pp | 6.2% (2/32) | 37.1% (36/97) | -30.9 pp | 5.7% (3/53) | 11.6% (30/258) | -6.0 pp |
| Gemini 3.8 Flash (high) | 56.9% (29/51) | 0.0% (0/60) | +56.9 pp | 62.2% (28/45) | 0.0% (0/106) | +62.2 pp | 45.9% (34/74) | 0.3% (1/288) | +45.6 pp |
| Gemini 3.8 Flash (low) | 54.5% (30/55) | 4.5% (2/44) | +50.0 pp | 68.8% (22/32) | 2.0% (2/99) | +66.7 pp | 54.7% (35/64) | 0.7% (2/278) | +54.0 pp |
| Gemma 4 31B (off) | 53.3% (16/30) | 1.9% (1/53) | +51.4 pp | 80.0% (36/45) | 1.2% (1/86) | +78.8 pp | 50.0% (29/58) | 1.7% (4/232) | +48.3 pp |
| Gemma 4 31B (on) | 59.1% (39/66) | 0.0% (0/53) | +59.1 pp | 68.5% (37/54) | 0.0% (0/96) | +68.5 pp | 47.1% (33/70) | 0.0% (0/286) | +47.1 pp |
| Grok 4.7 (off) | 45.6% (26/57) | 0.0% (0/39) | +45.6 pp | 47.7% (21/44) | 0.0% (0/97) | +47.7 pp | 45.7% (37/81) | 0.0% (0/278) | +45.7 pp |
| Jev 1.14.0 | 61.7% (37/60) | 2.2% (1/45) | +59.4 pp | 79.0% (49/62) | 4.5% (4/88) | +74.5 pp | 81.5% (53/65) | 2.3% (5/214) | +79.2 pp |
| Liquid d1-ultra | 43.2% (16/37) | 10.5% (6/57) | +32.7 pp | 49.2% (32/65) | 6.7% (6/90) | +42.6 pp | 52.2% (36/69) | 2.2% (6/267) | +49.9 pp |
| Qwen3.8 Flash (off) | 52.5% (32/61) | 1.8% (1/57) | +50.7 pp | 59.0% (36/61) | 5.1% (4/79) | +54.0 pp | 54.2% (52/96) | 3.0% (6/198) | +51.1 pp |
| Qwen3.8-27B (on) | 63.8% (37/58) | 6.5% (3/46) | +57.3 pp | 70.6% (36/51) | 4.8% (4/83) | +65.8 pp | 55.7% (44/79) | 2.1% (5/239) | +53.6 pp |
| *Random legal play (expected)* | 17.4% (171.0/981) | 63.2% (648.6/1026) | -45.8 pp | 17.8% (167.8/942) | 63.9% (1171.5/1832) | -46.1 pp | 15.9% (224.5/1414) | 53.4% (2588.3/4846) | -37.5 pp |

### League 3

| setup | 0.04-0.08: missed | 0.04-0.08: needless | 0.04-0.08: bias | 0.08-0.15: missed | 0.08-0.15: needless | 0.08-0.15: bias | 0.15+: missed | 0.15+: needless | 0.15+: bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (on) | 41.2% (14/34) | 2.5% (1/40) | +38.7 pp | 46.4% (13/28) (few) | 2.7% (2/75) | +43.8 pp | 22.5% (9/40) | 2.2% (4/180) | +20.3 pp |
| Claude Opus 5.5 (off) | 62.5% (25/40) | 3.3% (1/30) | +59.2 pp | 43.9% (18/41) | 2.6% (2/78) | +41.3 pp | 34.2% (13/38) | 1.1% (2/181) | +33.1 pp |
| Claude Opus 5.5 (on) | 53.1% (17/32) | 4.8% (1/21) (few) | +48.4 pp | 52.6% (20/38) | 4.3% (3/69) | +48.3 pp | 42.6% (20/47) | 0.0% (0/170) | +42.6 pp |
| GNUbg weak | 17.5% (7/40) | 35.7% (10/28) (few) | -18.2 pp | 12.0% (3/25) (few) | 23.4% (15/64) | -11.4 pp | 4.3% (2/46) | 7.2% (11/153) | -2.8 pp |
| GPT-6 Astra (off) | 31.2% (10/32) | 0.0% (0/29) (few) | +31.2 pp | 58.1% (18/31) | 6.5% (3/46) | +51.5 pp | 31.0% (13/42) | 0.0% (0/186) | +31.0 pp |
| GPT-6 Astra (on) | 41.9% (13/31) | 5.4% (2/37) | +36.5 pp | 44.4% (16/36) | 0.0% (0/51) | +44.4 pp | 24.0% (12/50) | 0.0% (0/192) | +24.0 pp |
| GPT-6.1 Sol (high) | 32.1% (9/28) (few) | 0.0% (0/38) | +32.1 pp | 48.3% (14/29) (few) | 4.4% (3/68) | +43.9 pp | 16.1% (5/31) | 1.3% (3/228) | +14.8 pp |
| GPT-6.1 Sol (low) | 30.6% (11/36) | 8.0% (2/25) (few) | +22.6 pp | 43.8% (14/32) | 1.5% (1/67) | +42.3 pp | 25.0% (10/40) | 0.0% (0/210) | +25.0 pp |
| Gemini 4 Argon (off) | 69.7% (23/33) | 3.0% (1/33) | +66.7 pp | 60.0% (27/45) | 5.1% (3/59) | +54.9 pp | 35.1% (13/37) | 1.5% (3/205) | +33.7 pp |
| Gemini 4 Argon (on) | 44.1% (15/34) | 3.2% (1/31) | +40.9 pp | 40.6% (13/32) | 0.0% (0/67) | +40.6 pp | 42.9% (15/35) | 0.0% (0/139) | +42.9 pp |
| Grok 4.7 (on) | 61.5% (24/39) | 2.4% (1/41) | +59.1 pp | 61.5% (24/39) | 5.8% (3/52) | +55.8 pp | 41.0% (25/61) | 0.0% (0/157) | +41.0 pp |
| Kimi K3.1 Pro (off) | 42.1% (8/19) (few) | 3.7% (1/27) (few) | +38.4 pp | 55.6% (15/27) (few) | 1.9% (1/53) | +53.7 pp | 41.0% (16/39) | 2.1% (3/145) | +39.0 pp |
| *Random legal play (expected)* | 18.6% (74.1/398) | 61.7% (234.6/380) | -43.1 pp | 20.8% (83.9/403) | 62.5% (468.3/749) | -41.7 pp | 17.7% (89.4/506) | 50.6% (1086.8/2146) | -33.0 pp |

## Appendix B: check 3 per setup (mean equity lost at 2-ply (n); took the right risk = share (n/N))

Same data in `… - check 3.csv`.

### League 1

| setup | Risk wins: safe | Risk wins: in between | Risk wins: unsafe | Risk wins: took the right risk | Safety wins: safe | Safety wins: in between | Safety wins: unsafe |
|---|---:|---:|---:|---:|---:|---:|---:|
| Celeris-1 Decision | 0.222 (137) | 0.055 (22) | 0.055 (9) | 55.6% (5/9) | 0.052 (387) | 0.093 (17) | 0.304 (4) |
| Cygnet (Gemma 4 12B) | 0.217 (182) | 0.064 (33) | 0.123 (25) | 36.0% (9/25) | 0.038 (268) | 0.140 (19) | 0.216 (10) |
| Decider Flash v1.2 | 0.229 (83) | 0.170 (25) | 0.254 (52) | 17.3% (9/52) | 0.074 (258) | 0.130 (34) | 0.333 (47) |
| Decider v1.1 27B | 0.223 (118) | 0.084 (29) | 0.110 (28) | 50.0% (14/28) | 0.039 (303) | 0.124 (39) | 0.381 (27) |
| Decider v1.2 27B | 0.216 (97) | 0.065 (24) | 0.114 (24) | 37.5% (9/24) | 0.051 (306) | 0.081 (39) | 0.283 (16) |
| DeepSeek V4.1 Flash (off) | 0.206 (122) | 0.111 (51) | 0.117 (21) | 57.1% (12/21) | 0.050 (264) | 0.092 (31) | 0.294 (4) |
| Fastino GLiDE v1.2 (local) | 0.254 (88) | 0.069 (24) | 0.097 (27) | 48.1% (13/27) | 0.058 (361) | 0.075 (29) | 0.244 (27) |
| GNUbg weak | 0.058 (4) | 0.020 (17) | 0.058 (83) | 53.0% (44/83) | 0.013 (190) | 0.042 (75) | 0.192 (47) |
| GPT-6 Luna | 0.218 (158) | 0.105 (28) | 0.122 (11) | 27.3% (3/11) | 0.044 (295) | 0.138 (28) | 0.171 (7) |
| Jev 1.13.0 | 0.220 (143) | 0.068 (25) | 0.193 (17) | 47.1% (8/17) | 0.040 (335) | 0.031 (16) | 0.190 (3) |
| LFM2.5-24B-A2B (off) | 0.192 (115) | 0.083 (16) | 0.208 (47) | 36.2% (17/47) | 0.065 (212) | 0.164 (37) | 0.330 (29) |
| LFM2.5-24B-A2B (on) | 0.202 (103) | 0.087 (25) | 0.197 (57) | 35.1% (20/57) | 0.052 (280) | 0.134 (33) | 0.342 (43) |
| Mercury Decide | 0.273 (168) | 0.102 (35) | 0.173 (14) | 28.6% (4/14) | 0.053 (272) | 0.113 (31) | 0.227 (4) |
| Open-Jev 27B v1.1 | 0.265 (69) | 0.075 (23) | 0.220 (45) | 28.9% (13/45) | 0.080 (209) | 0.158 (35) | 0.378 (62) |
| Qwen3.8-27B (off) | 0.250 (173) | 0.134 (48) | 0.088 (10) | 40.0% (4/10) | 0.056 (309) | 0.062 (16) | 0.172 (6) |
| Random | 0.429 (19) | 0.339 (14) | 0.283 (47) | 6.4% (3/47) | 0.106 (29) | 0.168 (16) | 0.438 (86) |
| Safest | 0.227 (233) | – (0) | – (0) | – (0) | 0.082 (329) | – (0) | – (0) |
| SubQ Snap Preview | 0.295 (95) | 0.151 (46) | 0.165 (39) | 38.5% (15/39) | 0.052 (311) | 0.129 (49) | 0.293 (28) |
| Winnow-12B | 0.250 (126) | 0.110 (43) | 0.120 (36) | 44.4% (16/36) | 0.078 (261) | 0.109 (27) | 0.255 (23) |

### League 2

| setup | Risk wins: safe | Risk wins: in between | Risk wins: unsafe | Risk wins: took the right risk | Safety wins: safe | Safety wins: in between | Safety wins: unsafe |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (off) | 0.148 (73) | 0.056 (52) | 0.047 (40) | 62.5% (25/40) | 0.028 (355) | 0.074 (22) | 0.146 (8) |
| Claude Sonnet 5.5 (high) | 0.173 (103) | 0.031 (52) | 0.064 (39) | 59.0% (23/39) | 0.018 (395) | 0.043 (31) | 0.150 (2) |
| Claude Sonnet 5.5 (low) | 0.180 (105) | 0.036 (46) | 0.074 (19) | 52.6% (10/19) | 0.028 (448) | 0.053 (15) | 0.115 (3) |
| Clef | 0.191 (100) | 0.086 (30) | 0.115 (52) | 38.5% (20/52) | 0.044 (256) | 0.095 (48) | 0.189 (36) |
| DeepSeek V4.1 Flash (on) | 0.140 (90) | 0.085 (47) | 0.065 (50) | 58.0% (29/50) | 0.024 (418) | 0.045 (45) | 0.151 (9) |
| DeepSeek V4.1 Flash 1017 (off) | 0.246 (140) | 0.099 (37) | 0.140 (17) | 58.8% (10/17) | 0.036 (347) | 0.075 (45) | 0.263 (3) |
| DeepSeek V4.1 Flash 1017 (on) | 0.165 (92) | 0.059 (57) | 0.040 (36) | 75.0% (27/36) | 0.018 (420) | 0.035 (46) | 0.217 (10) |
| Fastino GLiDE | 0.171 (79) | 0.123 (34) | 0.063 (43) | 55.8% (24/43) | 0.043 (346) | 0.127 (46) | 0.277 (18) |
| GLM-5.3 (on) | 0.218 (142) | 0.066 (38) | 0.109 (13) | 53.8% (7/13) | 0.033 (331) | 0.057 (33) | 0.108 (1) |
| GNUbg weak | 0.199 (9) | 0.052 (25) | 0.060 (87) | 58.6% (51/87) | 0.022 (213) | 0.066 (108) | 0.207 (88) |
| Gemini 3.8 Flash (high) | 0.163 (91) | 0.044 (46) | 0.048 (33) | 60.6% (20/33) | 0.012 (435) | 0.011 (18) | 0.794 (1) |
| Gemini 3.8 Flash (low) | 0.172 (87) | 0.014 (30) | 0.032 (34) | 70.6% (24/34) | 0.022 (404) | 0.048 (11) | 0.209 (6) |
| Gemma 4 31B (off) | 0.177 (81) | 0.047 (30) | 0.098 (22) | 59.1% (13/22) | 0.029 (353) | 0.080 (12) | 0.246 (6) |
| Gemma 4 31B (on) | 0.163 (109) | 0.038 (41) | 0.056 (40) | 62.5% (25/40) | 0.029 (418) | 0.064 (17) | – (0) |
| Grok 4.7 (off) | 0.188 (84) | 0.061 (63) | 0.052 (35) | 60.0% (21/35) | 0.017 (376) | 0.100 (38) | – (0) |
| Jev 1.14.0 | 0.185 (139) | 0.094 (32) | 0.074 (16) | 37.5% (6/16) | 0.041 (312) | 0.082 (25) | 0.251 (10) |
| Liquid d1-ultra | 0.241 (84) | 0.070 (50) | 0.088 (37) | 48.6% (18/37) | 0.042 (352) | 0.072 (44) | 0.243 (18) |
| Qwen3.8 Flash (off) | 0.223 (120) | 0.113 (55) | 0.126 (43) | 27.9% (12/43) | 0.038 (277) | 0.119 (46) | 0.340 (11) |
| Qwen3.8-27B (on) | 0.218 (117) | 0.061 (41) | 0.074 (30) | 60.0% (18/30) | 0.040 (337) | 0.076 (19) | 0.203 (12) |

### League 3

| setup | Risk wins: safe | Risk wins: in between | Risk wins: unsafe | Risk wins: took the right risk | Safety wins: safe | Safety wins: in between | Safety wins: unsafe |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (on) | 0.131 (36) | 0.019 (33) | 0.059 (33) | 60.6% (20/33) | 0.016 (264) | 0.043 (24) | 0.224 (7) |
| Claude Opus 5.5 (off) | 0.143 (56) | 0.034 (31) | 0.043 (32) | 75.0% (24/32) | 0.022 (260) | 0.056 (24) | 0.199 (5) |
| Claude Opus 5.5 (on) | 0.171 (57) | 0.041 (35) | 0.033 (25) | 68.0% (17/25) | 0.010 (242) | 0.017 (14) | 0.135 (4) |
| GNUbg weak | 0.163 (12) | 0.023 (15) | 0.074 (84) | 48.8% (41/84) | 0.021 (153) | 0.102 (56) | 0.191 (36) |
| GPT-6 Astra (off) | 0.157 (41) | 0.027 (32) | 0.026 (32) | 75.0% (24/32) | 0.010 (229) | 0.009 (29) | 0.160 (3) |
| GPT-6 Astra (on) | 0.129 (41) | 0.049 (45) | 0.023 (31) | 74.2% (23/31) | 0.012 (253) | 0.022 (25) | 0.081 (2) |
| GPT-6.1 Sol (high) | 0.122 (28) | 0.038 (24) | 0.032 (36) | 69.4% (25/36) | 0.012 (292) | 0.013 (36) | 0.191 (6) |
| GPT-6.1 Sol (low) | 0.163 (35) | 0.032 (35) | 0.027 (38) | 65.8% (25/38) | 0.012 (268) | 0.044 (31) | 0.072 (3) |
| Gemini 4 Argon (off) | 0.148 (63) | 0.048 (24) | 0.035 (28) | 71.4% (20/28) | 0.021 (271) | 0.052 (19) | 0.286 (7) |
| Gemini 4 Argon (on) | 0.181 (43) | 0.039 (21) | 0.009 (37) | 83.8% (31/37) | 0.018 (219) | 0.029 (17) | 0.045 (1) |
| Grok 4.7 (on) | 0.162 (73) | 0.100 (37) | 0.072 (29) | 72.4% (21/29) | 0.013 (222) | 0.072 (24) | 0.105 (4) |
| Kimi K3.1 Pro (off) | 0.195 (39) | 0.110 (22) | 0.048 (24) | 66.7% (16/24) | 0.035 (197) | 0.152 (23) | 0.487 (5) |
