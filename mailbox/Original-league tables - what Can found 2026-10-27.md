# Original-league tables: what Can found and what we are doing (2026-10-27)

## What Can found

The Hype Cup roster was built from the **final ladder tables**. Those tables mix setups that moved between leagues, and that produced results that don't make sense:

- **Liquid d1-ultra** won League 1's first season (48 points, level with GNUbg weak). It then moved up to League 2 in ladder round 1, finished 14th there, and so is not in the Cup at all. League 1's Cup places went to Celeris-1 Decision and SubQ Snap Preview, which were 10th and 11th among League 1's original setups.
- **The League 1 tiebreak** (points, then games, then error rate) put SubQ Snap Preview ahead of Cygnet on 37 points each. But matches don't have a fixed length: a match ends after the round in which someone reaches 5 points (2, 4, 6 or 8 games). A setup that wins quickly plays fewer games, so **games won is not a fair tiebreak**. Cygnet also beat SubQ head-to-head, 7–3.

In short: the ladder tables measure where a setup ended up after moving, not how it did against its own league. Ranking the Cup from them lost the original league winner and decided a tie on a measure that depends on match length.

## The new way (Can's rule)

1. Put every setup back in its **original league** (the league it was in before any ladder move). GNUbg weak, the anchor, is in all three.
2. Count **only the matches between setups of the same original league**: 3 points for a win, 1 for a draw.
3. Build the Cup from these tables.

Tiebreak under discussion (not yet confirmed): points, then the head-to-head result, then the lower error rate. Games won drops out.

## What the tables show (provisional)

- League 1 (19 setups, all 171 pairings played): Liquid d1-ultra 48 and GNUbg weak 48 at the top; Fastino GLiDE 37; Decider v1.2 27B, Jev 1.14.0 and Jev 1.13.0 36 each.
- League 2 (19 setups): GPT-6.1 Sol (low) 45; Gemma 4 31B (on) and Claude Sonnet 5.5 (high) 39 each; Gemini 3.8 Flash (low) 38.
- League 3 (12 setups): GPT-6 Astra (on) 27; Claude Fable 5.1 (on) 24; Grok 4.7 (on) 19.

## The remaining gap: late entries

Three setups joined after other setups had already left their league, so 10 pairings never happened:

- League 2: DeepSeek V4.1 Flash 1017 (on) and (off) never played GPT-6.1 Sol (low), Sol (high), LFM2.5-24B-A2B (on) or (off): 8 matches.
- League 3: Kimi K3.1 Pro (off) never played Claude Fable 5.1 (off) or Grok 4.7 (off): 2 matches.

To make every original league a complete round robin, we play these 10 matches, with the same rules and format as the leagues. They are stored as normal valid matches and are not shown as a separate league.

## Status

- The 10 matches are estimated at about $3.36 on OpenRouter, mostly DeepSeek 1017 (on)'s reasoning ($2.39). About $2.00 of credit is free once the Nackgammon test's reserve is set aside. Can is choosing between: play the 6 cheap matches now and the 4 DeepSeek 1017 (on) matches later, add credit, or wait until the Nackgammon test finishes.
- When the 10 matches are done: the three original-league tables are recomputed and checked for completeness, then the Cup roster, draw and stored Cup pairings are redone from them once Can confirms the tiebreak.
- The Nackgammon paired test continues meanwhile. It uses every League 1 decision model, so it is not affected. The Nackgammon knockout waits for the corrected roster.
