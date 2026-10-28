# Hype Cup roster (2026-10-28)

Built from the **original-league tables** (`mailbox/Original-league tables 2026-10-28.md`, all three complete round robins), under the Cup rules in `mailbox/backgammon-ladder-cup.md`, Part 2, with the amendments of 2026-10-27 (original-league tables) and 2026-10-28 (tiebreak: points, head-to-head, lower error rate). **This replaces `mailbox/Hype Cup roster 2026-10-27.md`**, which was built from the final ladder tables. **No Cup match and no Nackgammon knockout match has been started.**

Reproduce: `python3 tools/original_league.py cup` (read-only on `v3.db`; stored results by pairing from `tools/ladder.py`'s pairing store). Error rates in this file are each setup's rate over the matches of its own original-league table.

## Rules applied

- **Teams (8):** the top 2 models of each original-league table, plus the two 3rd-placed models with the lowest error rates. Programs (GNUbg weak, Random, Safest) are skipped: when the rule picks a program, the next model is taken.
- **Seeds:** 1 = League 3 #1, 2 = League 3 #2, 3 = League 2 #1, 4 = League 2 #2, 5 = League 1 #1, 6 = League 1 #2, 7 = the better 3rd place, 8 = the other 3rd place.
- **Quarter-final draw:** seeds 1–4 pick in that order. Each takes the lowest-seeded remaining team from a *different* league. If the last pick would pair two setups of one league, it swaps opponents with the previous pick.
- **Semi-finals:** A = winners of the seed-1 and seed-4 quarter-finals; B = winners of the seed-2 and seed-3 quarter-finals.
- **Stored results:** a pairing already played in any valid match stands.
- **GPT-6 Astra (high) is not eligible** for this Cup (Can, 2026-10-28). It will be a late entry to the original League 3 table. It is not in any table yet. If its matches are played before the Cup, it is skipped for the roster like a program (`NOT_IN_CUP` in the tool).

## Top of each original-league table (models; programs marked)

| League | 1st | 2nd | 3rd | 4th |
| --- | --- | --- | --- | --- |
| League 1 (19) | GNUbg weak (program), 48 pts, won the head-to-head; then **Liquid d1-ultra**, 48 | **Fastino GLiDE**, 37 | Jev 1.13.0, 36 (mini-table over Jev 1.14.0 and Decider v1.2 27B) | Jev 1.14.0, 36 |
| League 2 (19) | **GPT-6.1 Sol (low)**, 48 | **GPT-6.1 Sol (high)**, 42 | Gemma 4 31B (on), 39 (beat Sonnet 5.5 (high) 4–2, #202) | Claude Sonnet 5.5 (high), 39 |
| League 3 (12) | **GPT-6 Astra (on)**, 27 | **Claude Fable 5.1 (on)**, 24 | Grok 4.7 (on), 19 | Claude Opus 5.5 (on), 18 |

3rd-placed models by error rate: Grok 4.7 (on) 16.29 and **Gemma 4 31B (on) 18.92 are in**. Jev 1.13.0 (34.83) is out.

## Changes from the 2026-10-27 roster (ladder tables)

- **In:** Claude Fable 5.1 (on), Liquid d1-ultra, Fastino GLiDE, Grok 4.7 (on).
- **Out:** Gemini 3.8 Flash (low), Claude Sonnet 5.5 (low), Celeris-1 Decision, SubQ Snap Preview.
- **Kept, with new seeds:** GPT-6 Astra (on) (2 → 1), GPT-6.1 Sol (low) (1 → 3), GPT-6.1 Sol (high) (7 → 4), Gemma 4 31B (on) (8 → 8).

## The 8 teams and their seeds

| Seed | Team | From | Error rate (in its original-league table) |
|---|---|---|---|
| 1 | GPT-6 Astra (on) | League 3 #1 | 12.24 |
| 2 | Claude Fable 5.1 (on) | League 3 #2 | 13.07 |
| 3 | GPT-6.1 Sol (low) | League 2 #1 | 10.72 |
| 4 | GPT-6.1 Sol (high) | League 2 #2 | 10.81 |
| 5 | Liquid d1-ultra | League 1 #1 model | 29.98 |
| 6 | Fastino GLiDE | League 1 #2 model | 37.12 |
| 7 | Grok 4.7 (on) | League 3 3rd model, better 3rd place | 16.29 |
| 8 | Gemma 4 31B (on) | League 2 3rd model, other 3rd place | 18.92 |

3rd-placed models: League 3 Grok 4.7 (on) 16.29; League 2 Gemma 4 31B (on) 18.92; League 1 Jev 1.13.0 34.83.

Not eligible: GPT-6 Astra (high), late entry to League 3, not eligible for the coming Hype Cup (Can, 2026-10-28); not in any original-league table yet.

## Quarter-final draw

1. Seed 1, GPT-6 Astra (on) (League 3) takes seed 8, Gemma 4 31B (on) (League 2): the lowest-seeded remaining team, from a different league.
2. Seed 2, Claude Fable 5.1 (on) (League 3) takes seed 6, Fastino GLiDE (League 1): lower seeds skipped (same league): seed 7.
3. Seed 3, GPT-6.1 Sol (low) (League 2) takes seed 7, Grok 4.7 (on) (League 3): the lowest-seeded remaining team, from a different league.
4. Seed 4, GPT-6.1 Sol (high) (League 2) takes seed 5, Liquid d1-ultra (League 1): the lowest-seeded remaining team, from a different league.

No quarter-final pairs two setups of one league, so the swap rule is not needed.

## Bracket

- **QF1:** GPT-6 Astra (on) (1) v Gemma 4 31B (on) (8)
- **QF2:** Claude Fable 5.1 (on) (2) v Fastino GLiDE (6)
- **QF3:** GPT-6.1 Sol (low) (3) v Grok 4.7 (on) (7)
- **QF4:** GPT-6.1 Sol (high) (4) v Liquid d1-ultra (5)
- **Semi-final A:** winner QF1 v winner QF4
- **Semi-final B:** winner QF2 v winner QF3
- **Final:** winner SF A v winner SF B

## Stored results (a pairing already played stands)

| Round | Pairing | Stored | Result |
|---|---|---|---|
| QF | GPT-6 Astra (on) (1) v Gemma 4 31B (on) (8) | none | new match needed |
| QF | Claude Fable 5.1 (on) (2) v Fastino GLiDE (6) | none | new match needed |
| QF | GPT-6.1 Sol (low) (3) v Grok 4.7 (on) (7) | #550, League 3 | GPT-6.1 Sol (low) beat Grok 4.7 (on) 6–0 (#550) |
| QF | GPT-6.1 Sol (high) (4) v Liquid d1-ultra (5) | #512, League 2 | GPT-6.1 Sol (high) beat Liquid d1-ultra 7–0 (#512) |
| SF | GPT-6 Astra (on) (1) v GPT-6.1 Sol (high) (4) | #555, League 3 | GPT-6.1 Sol (high) beat GPT-6 Astra (on) 5–3 (#555) |
| SF | GPT-6 Astra (on) (1) v Liquid d1-ultra (5) | none | new match needed |
| SF | Gemma 4 31B (on) (8) v GPT-6.1 Sol (high) (4) | #210, League 2 | GPT-6.1 Sol (high) beat Gemma 4 31B (on) 5–2 (#210) |
| SF | Gemma 4 31B (on) (8) v Liquid d1-ultra (5) | #522, League 2 | Gemma 4 31B (on) beat Liquid d1-ultra 4–2 (#522) |
| SF | Claude Fable 5.1 (on) (2) v GPT-6.1 Sol (low) (3) | #516, League 3 | GPT-6.1 Sol (low) beat Claude Fable 5.1 (on) 8–1 (#516) |
| SF | Claude Fable 5.1 (on) (2) v Grok 4.7 (on) (7) | #423, League 3 | Claude Fable 5.1 (on) beat Grok 4.7 (on) 5–1 (#423) |
| SF | Fastino GLiDE (6) v GPT-6.1 Sol (low) (3) | none | new match needed |
| SF | Fastino GLiDE (6) v Grok 4.7 (on) (7) | none | new match needed |
| Final | GPT-6 Astra (on) (1) v Claude Fable 5.1 (on) (2) | #461, League 3 | GPT-6 Astra (on) beat Claude Fable 5.1 (on) 5–3 (#461) |
| Final | GPT-6 Astra (on) (1) v GPT-6.1 Sol (low) (3) | #509, League 3 | GPT-6 Astra (on) beat GPT-6.1 Sol (low) 5–1 (#509) |
| Final | GPT-6 Astra (on) (1) v Fastino GLiDE (6) | none | new match needed |
| Final | GPT-6 Astra (on) (1) v Grok 4.7 (on) (7) | #476, League 3 | GPT-6 Astra (on) beat Grok 4.7 (on) 5–1 (#476) |
| Final | GPT-6.1 Sol (high) (4) v Claude Fable 5.1 (on) (2) | #576, League 3 | GPT-6.1 Sol (high) beat Claude Fable 5.1 (on) 4–2 (#576) |
| Final | GPT-6.1 Sol (high) (4) v GPT-6.1 Sol (low) (3) | #126, League 2 | GPT-6.1 Sol (low) beat GPT-6.1 Sol (high) 5–2 (#126) |
| Final | GPT-6.1 Sol (high) (4) v Fastino GLiDE (6) | none | new match needed |
| Final | GPT-6.1 Sol (high) (4) v Grok 4.7 (on) (7) | #581, League 3 | Grok 4.7 (on) beat GPT-6.1 Sol (high) 5–3 (#581) |
| Final | Gemma 4 31B (on) (8) v Claude Fable 5.1 (on) (2) | none | new match needed |
| Final | Gemma 4 31B (on) (8) v GPT-6.1 Sol (low) (3) | #200, League 2 | GPT-6.1 Sol (low) beat Gemma 4 31B (on) 6–5 (#200) |
| Final | Gemma 4 31B (on) (8) v Fastino GLiDE (6) | #571, League 2 | Gemma 4 31B (on) beat Fastino GLiDE 4–2 (#571) |
| Final | Gemma 4 31B (on) (8) v Grok 4.7 (on) (7) | none | new match needed |
| Final | Liquid d1-ultra (5) v Claude Fable 5.1 (on) (2) | none | new match needed |
| Final | Liquid d1-ultra (5) v GPT-6.1 Sol (low) (3) | none | new match needed |
| Final | Liquid d1-ultra (5) v Fastino GLiDE (6) | #376, League 1 | Liquid d1-ultra beat Fastino GLiDE 5–3 (#376) |
| Final | Liquid d1-ultra (5) v Grok 4.7 (on) (7) | none | new match needed |

### What the stored results decide

- **New matches needed: 2 to 4.** QF1 and QF2 are always new. QF3 and QF4 are stored: GPT-6.1 Sol (low) and GPT-6.1 Sol (high) go through.
- **Semi-final A:** GPT-6.1 Sol (high) against the QF1 winner is stored either way. It beat GPT-6 Astra (on) 5–3 (#555) and Gemma 4 31B (on) 5–2 (#210), so **GPT-6.1 Sol (high) reaches the final** whoever wins QF1.
- **Semi-final B:**
  - If Claude Fable 5.1 (on) wins QF2: stored, GPT-6.1 Sol (low) won 8–1 (#516). The final is then stored too: GPT-6.1 Sol (low) beat GPT-6.1 Sol (high) 5–2 (#126), so **GPT-6.1 Sol (low) is champion with 2 new matches**.
  - If Fastino GLiDE wins QF2: SF B, Fastino GLiDE v GPT-6.1 Sol (low), is new. If Fastino GLiDE also wins that, the final Fastino GLiDE v GPT-6.1 Sol (high) is new as well (4 new matches in all).
- **Level matches:** a level Cup match goes to the lower error rate in that match (`tools/ladder.py cup-winner`), as before.

## Cup teams and the Nackgammon paired test

Adding a setup = 1000 answers (500 positions × the standard and the Nackgammon prompt, as every setup in the test). Estimated from the setup's own league decisions with 2–25 legal plays (no group split): input × 0.89, output as measured (low) to × 1.2 (high), +2% attempts (+5% when it thinks); money at the roster list price; time = answers × p50 request time ÷ parallel (low) to attempts × mean × 1.2 ÷ parallel (high). Not run.

| Team | In the paired test | Route | League decisions used | Input tok | Output tok | Cost of 1,000 answers | Time (parallel) |
|---|---|---|---|---|---|---|---|
| GPT-6 Astra (on) | yes | chatgpt-subscription | – | – | – | – | – |
| Claude Fable 5.1 (on) | **no** | claude-subscription | 1396 | 4236 | 822 | $78.81–91.39 list price | 40–67 min (4) |
| GPT-6.1 Sol (low) | yes | chatgpt-subscription | – | – | – | – | – |
| GPT-6.1 Sol (high) | yes | chatgpt-subscription | – | – | – | – | – |
| Liquid d1-ultra | **no** | liquid | 3680 | 2959 | 0 | $0.11–0.11 list price | 2–3 min (2) |
| Fastino GLiDE | **no** | fastino | 3674 | 3284 | 0 | no list price | 7–11 min (unset, timed at 1) |
| Grok 4.7 (on) | **no** | xai-subscription | 1494 | 4341 | 11607 | $77.37–95.86 list price | 3.2–6.9 h (8) |
| Gemma 4 31B (on) | yes | local-vllm | – | – | – | – | – |

**Not yet in the paired test: 4 of the 8 teams.** Claude Fable 5.1 (on), Liquid d1-ultra, Fastino GLiDE (the API setup; the test has Fastino GLiDE v1.2 (local)) and Grok 4.7 (on). Adding all four, not run:

| | Claude Fable 5.1 (on) | Liquid d1-ultra | Fastino GLiDE | Grok 4.7 (on) |
| --- | --- | --- | --- | --- |
| Route | Claude subscription | own key | own key | xAI subscription |
| Billed | none | about $0.11, by Liquid | not known: no list price on record | none |
| API-equivalent | $79–91 | — | — | $77–96 |
| Time | 40–67 min | 2–3 min | 7–11 min | 3.2–6.9 h (11,607 output tokens and about 160 s per league decision) |

- **No GPU:** none of the four needs one.
- **OpenRouter:** $0.
- **Wall time:** about 3.5–7 h, set by Grok 4.7 (on) when the others run alongside it.

**Check against setups already in the test.** The same estimate for setups that answered all 1,000 matches the real cost well:

| Setup | Estimated API-eq. | Real API-eq. |
| --- | --- | --- |
| GPT-6.1 Sol (low) | $6.23–6.70 | $6.02 |
| GPT-6.1 Sol (high) | $8.40–9.42 | $8.07 |
| GPT-6 Astra (on) | $31.1–33.5 | $29.5 |

Time ran longer than estimated, because the setups shared the run: Sol (low) took about 42 min against 15–23 min estimated, Sol (high) 70 min against 34–62 min, and Astra (on) 32 min against 15–26 min. Read the times above as up to about twice as long when run side by side.

Not checked: whether the Fastino GLiDE and Liquid d1-ultra API keys still work today. No call was made.

## Not changed

- **`leagues/knockout-nack.json`** still lists the 2026-10-27 roster (Sol (low), Astra (on), Gemini 3.8 Flash (low), Sonnet 5.5 (low), Celeris-1 Decision, SubQ Snap Preview, Sol (high), Gemma 4 31B (on)). It has to be rewritten with the 8 teams above in seed order before any Nackgammon knockout starts. I left it alone: no knockout start was asked for.
- **The site** is unchanged.
