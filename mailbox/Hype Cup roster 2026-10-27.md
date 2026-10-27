# Hype Cup roster (2026-10-27)

From the final tables of the ladder (it ended Oct 26 with round 6's final swap), under the Cup rules in `mailbox/backgammon-ladder-cup.md`, Part 2. No Cup match has been played or started. The roster below is used by both Nackgammon parts of Can's brief of 2026-10-27 (the paired test and the Nackgammon knockout).

Source: `v3.db`, read-only, through the dashboard (`/api/state?league=1..3`, all three leagues `finished` at 2026-10-26 15:46:30 UTC) and `tools/ladder.py` (stored pairings). Ranking as in the leagues: points, then games won, then fewer games lost, then the lower error rate. Error rate = 500 × mean GNUbg 1.08 2-ply equity loss over all of a setup's valid matches (as on the site). Programs (GNUbg weak, Random, Safest) never enter the Cup; when the rule picks one, the next model is taken.

## Final tables (top of each, programs marked)

| League | 1st | 2nd | 3rd | 4th |
| --- | --- | --- | --- | --- |
| League 1 (19) | GNUbg weak (program) 48 pts | Celeris-1 Decision 38 pts, 57-39, 33.1 | SubQ Snap Preview 37 pts, 66-38, 43.9 | Cygnet (Gemma 4 12B) 37 pts, 60-40, 38.0 |
| League 2 (19) | Gemini 3.8 Flash (low) 44 pts, 63-39, 17.4 | Claude Sonnet 5.5 (low) 40 pts, 65-41, 19.8 | Gemma 4 31B (on) 39 pts, 62-42, 19.3 | DeepSeek V4.1 Flash 1017 (on) 37 pts |
| League 3 (12) | GPT-6.1 Sol (low) 27 pts, 41-25, 11.5 | GPT-6 Astra (on) 24 pts, 36-26, 11.5 | GPT-6.1 Sol (high) 21 pts, 38-26, 10.7 | Grok 4.7 (on) 19 pts |

## The rule, step by step

1. **Top 2 models of each league** (programs skipped):
   - League 1: GNUbg weak is 1st but a program, so the models are **Celeris-1 Decision** (#1 model) and **SubQ Snap Preview** (#2 model). SubQ and Cygnet both have 37 points; SubQ ranks ahead on games won (66 against 60).
   - League 2: **Gemini 3.8 Flash (low)** and **Claude Sonnet 5.5 (low)**.
   - League 3: **GPT-6.1 Sol (low)** and **GPT-6 Astra (on)**.
2. **The 3rd-placed models** (the next model after the top 2): League 1 Cygnet (Gemma 4 12B), error rate 38.0; League 2 Gemma 4 31B (on), 19.3; League 3 GPT-6.1 Sol (high), 10.7.
3. **The two 3rd places with the lowest error rates:** **GPT-6.1 Sol (high)** (10.7) and **Gemma 4 31B (on)** (19.3). Cygnet (38.0) drops out.

## The 8 teams and their seeds

| Seed | Team | From | Rule | Error rate (all valid matches) |
| --- | --- | --- | --- | --- |
| 1 | GPT-6.1 Sol (low) | League 3 #1 | top 2 | 11.5 |
| 2 | GPT-6 Astra (on) | League 3 #2 | top 2 | 11.5 |
| 3 | Gemini 3.8 Flash (low) | League 2 #1 | top 2 | 17.4 |
| 4 | Claude Sonnet 5.5 (low) | League 2 #2 | top 2 | 19.8 |
| 5 | Celeris-1 Decision | League 1 #1 model | top 2 (GNUbg weak skipped) | 33.1 |
| 6 | SubQ Snap Preview | League 1 #2 model | top 2 | 43.9 |
| 7 | GPT-6.1 Sol (high) | League 3 #3 | better 3rd place (lower error rate) | 10.7 |
| 8 | Gemma 4 31B (on) | League 2 #3 | other 3rd place | 19.3 |

## Quarter-final draw

Seeds 1 to 4 pick in that order; each takes the lowest-seeded remaining team from a different league.

1. Seed 1, GPT-6.1 Sol (low) (League 3): lowest-seeded remaining is seed 8, Gemma 4 31B (on), League 2: a different league, taken.
2. Seed 2, GPT-6 Astra (on) (League 3): lowest-seeded remaining is seed 7, GPT-6.1 Sol (high), League 3: same league, skipped. Next, seed 6, SubQ Snap Preview (League 1): taken.
3. Seed 3, Gemini 3.8 Flash (low) (League 2): lowest-seeded remaining is seed 7, GPT-6.1 Sol (high) (League 3): taken.
4. Seed 4, Claude Sonnet 5.5 (low) (League 2): the one left, seed 5, Celeris-1 Decision (League 1): a different league, taken.

No quarter-final pairs two models from the same league, so the swap rule is not needed.

## Bracket

- **QF1:** GPT-6.1 Sol (low) (1) v Gemma 4 31B (on) (8)
- **QF2:** GPT-6 Astra (on) (2) v SubQ Snap Preview (6)
- **QF3:** Gemini 3.8 Flash (low) (3) v GPT-6.1 Sol (high) (7)
- **QF4:** Claude Sonnet 5.5 (low) (4) v Celeris-1 Decision (5)
- **Semi-final A:** winner QF1 v winner QF4
- **Semi-final B:** winner QF2 v winner QF3
- **Final:** winner SF A v winner SF B

## Stored results (Cup rule: a pairing already played stands; no match is played now)

Read with `tools/ladder.py`'s pairing store (valid matches, any stage but legacy playoffs):

| Pairing | Stored | Result |
| --- | --- | --- |
| QF1 Sol (low) v Gemma 4 31B (on) | #200, League 2, 2026-10-19 | Sol (low) won 6-5 |
| QF2 Astra (on) v SubQ Snap Preview | none | new match needed |
| QF3 Gemini 3.8 Flash (low) v Sol (high) | #135, League 2 | Sol (high) won 5-0 |
| QF4 Sonnet 5.5 (low) v Celeris-1 Decision | #735, ladder round 5 early start (hidden league #5) | Sonnet 5.5 (low) won 5-1 |
| SF A Sol (low) v Sonnet 5.5 (low) | #109, League 2 | Sol (low) won 5-1 |
| SF B Astra (on) v Sol (high) (if Astra wins QF2) | #555, League 3 | Sol (high) won 5-3 |
| SF B SubQ v Sol (high) (if SubQ wins QF2) | none | new match needed |
| Final Sol (low) v Sol (high) | #126, League 2 | Sol (low) won 5-2 |
| Final Sol (low) v SubQ (if SubQ reaches it) | none | new match needed |

So the standard Hype Cup needs 1 to 3 new matches: QF2 always; SF B and the final only if SubQ Snap Preview wins QF2. If Astra (on) wins QF2, the stored results make GPT-6.1 Sol (low) the champion. None is played without Can's go. The Nackgammon knockout (brief, point 3) is a separate event: Nackgammon start, 7 new matches, no stored result applies.

## Open-weights chat model among the 8

Yes: **Gemma 4 31B (on)** (Google's open-weights Gemma 4 31B, served by us on the RTX PRO 6000 with vLLM, reasoning on). No hosted open-weights setup needs to be proposed. Celeris-1 Decision and SubQ Snap Preview are hosted decision services, not chat models. Note: Gemma 4 31B (on) is the slowest of the 8 (about 211 s per league decision, 2 calls per decision), so it goes last in the paired test. Its bariton GPU host had three interruptions on Oct 25 (Method §9.13 addenda).
