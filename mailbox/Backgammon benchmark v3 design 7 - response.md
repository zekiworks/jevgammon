# Backgammon benchmark v3: response to version 7

Oct 13, 2026 · reply to "Backgammon benchmark v3 design 7"

Version 7 asks for a check on v1 data before the freeze. I ran it, and the result changes the bars: at 2,000 positions, a 2 PR point difference is not reliably detectable for most pairs of setups. The phase rules are sound, with three small fixes.

## The 2-point check, on v1 data

**Data:** the 1,000 v1 shared positions, answered by 13 setups (GLM-5.3-Flash left out as a failed run). For each of the 91 pairs, I took the per-position difference in loss, in PR points, and scaled its spread to other position counts.

| Positions | 95% half-width, best-behaved pair | Median pair | Widest pair |
| --- | --- | --- | --- |
| 1,000 | ±1.20 | ±3.66 | ±5.85 |
| 2,000 | ±0.85 | ±2.59 | ±4.14 |
| 4,000 | ±0.60 | ±1.83 | ±2.93 |
| 8,000 | ±0.42 | ±1.30 | ±2.07 |

The spread depends on the tier: strong models make fewer, smaller errors, so their differences vary less.

| Pair | Half-width at 2,000 | Positions needed for ±1 |
| --- | --- | --- |
| GPT-6 Astra vs Claude Opus 5.5 | ±1.26 | about 3,200 |
| Claude Opus 5.5 vs Gemini 3.8 Flash | ±1.24 | about 3,100 |
| Gemma 4 31B vs DeepSeek V4.1 Flash | ±2.35 | about 11,000 |
| Decider v1.1 vs Jev 1.13.0 | ±2.77 | about 15,400 |

**Power:** for the median pair at 2,000 positions, a true 2-point difference reaches a two-sided 5% test about one time in three.

By the design's own rule (detectable if narrower than ±1 at 2,000), 2 points fails for every pair except the best-behaved ones, and narrowly fails even for the frontier pairs.

**Caveats:**
- **Option order:** v1 answers used generation order.
- **Position mix:** the new set's positions come from GNUbg self-play rather than weak models' games, and may be easier or harder.

The numbers are a guide, not a guarantee. Re-run the check on the smoke-test answers before the freeze.

### What this means for each hypothesis

- **H2** (at least 3 points better, interval excludes 0). The Gemma off/on pair will likely have a half-width of about ±2.3. A real 3-point gain passes about half the time.
- **H3** (equivalence within ±3). The interval's half-width plus the observed difference must stay under 3. League 3's frontier pairs (about ±1.3) can pass. League 2's workhorse pairs are likely wider, so H3 there may come out inconclusive even when the models are equal.
- **H4** (non-inferiority, +2). The cascade and Astra alone give the same play wherever the cascade hands over to Astra, so their per-position differences are mostly zero. Its interval is likely much narrower than a typical pair's. I can't size it without a cascade run.
- **H5** (League 1, at least 2 points better, interval excludes 0). Decision-model pairs have about ±2.8 at 2,000. A selector shares many answers with its best member, which narrows this, but a 2-point gain will likely not exclude 0.

### Options

1. **Per-tier bars.** Keep 2 points for comparisons between frontier and workhorse setups (half-width about ±1.3). Use about 4 points for decision models and other weaker setups, matching their spread.
2. **More positions where the bar matters most.** For example, 4,000 positions for the setups in H2 and H5 only. That gives about ±1.8 for a median pair.
3. **Accept low power and say so:** report every result with its interval, and treat a miss as "not shown" rather than "no difference".

I would combine 1 and 3. Option 2 costs about 2,000 more calls per affected setup.

## Phase rules

The rules are well ordered, and the holding definition maps correctly onto our numbering: the opponent's bar, 5- and 4-points are the holder's 18-, 20- and 21-points. Three fixes:

- **Duplicates.** "Duplicate positions are removed in every phase" must compare the board and the dice together. The 15 first-roll positions share one board and differ only by dice, so removing duplicates by board alone would keep one of them.
- **GNUbg's class numbers.** GNUbg's `classifypos` returns an integer. The standard start returned 10, which is contact. In GNUbg's numbering, as I recall it and have not checked against the source, 4 to 7 are the bear-off classes, 8 is race, 9 is crashed and 10 is contact; 1 to 3 belong to Hypergammon, which is out. Pin the mapping in the classifier tests.
- **Holding positions may be scarce.** Expert self-play reaches a one-anchor holding game less often than contact or race positions, so 200 distinct holding positions may take many games to collect. Collect them before fixing the per-phase count at 200, or allow fewer holding positions with the count logged. I have not measured how scarce they are.

The game-plan order cites a hobby AI's source code. That is fine for analysis-only tags, but the page should cite The Gammon Press and describe the tags itself, rather than point readers to the hobby code.
