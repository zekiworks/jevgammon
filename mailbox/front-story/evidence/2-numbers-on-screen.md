# Heading asked for: "A number on screen makes models flinch"

Source: the live site's published data files (results f45081f6, data as of 2026-11-07T17:50Z): data/v3/clear-risk.json, section clear-risk-part2, table "Q1: share right per group, missed and needless, bias (two plays shown, not league play)". Read-only; every number below is copied from those files as printed.

Claim checked: on Q1 (best safe vs best unsafe play, the same 189 rollout-confirmed positions asked twice), each model's bias is higher (more cautious) with numbers than board only.

Result: direction **consistent**: 8 of 8 models have a higher bias with numbers (differences +10 to +114 pp, as the difference of the two printed biases). Board only, 4 models have a negative bias.

Wording on the page: "With the numbers on screen, every model asked played safer". It says what the two versions showed. The asked-for "makes models flinch" is causal; the comparison does hold the positions fixed (each model answered both versions of the same items), but no test of the difference is published and Zeki (bus #2578) asked for no new statistics, so the heading reports the observed direction only. 8 models, 189 positions, two plays shown (not league play): the section's caveat.

| Model | Missed, with numbers | Missed, board only | Needless, with numbers | Needless, board only | Bias, with numbers | Bias, board only | Difference (pp) |
|---|---|---|---|---|---:|---:|---:|
| Celeris-1 Decision | 94% (87/93) | 25% (23/92) | 2% (2/96) | 39% (36/93) | +91 pp | -14 pp | +105 |
| Jev 1.14.0 | 96% (87/91) | 33% (31/93) | 3% (3/96) | 55% (51/92) | +92 pp | -22 pp | +114 |
| Liquid d1-ultra | 81% (75/93) | 32% (30/93) | 6% (6/96) | 53% (46/87) | +74 pp | -21 pp | +95 |
| Claude Sonnet 5.5 (high) | 68% (63/93) | 48% (45/93) | 2% (2/96) | 6% (6/96) | +66 pp | +42 pp | +24 |
| GPT-6.1 Sol (high) | 56% (52/93) | 23% (21/93) | 2% (2/96) | 19% (18/96) | +54 pp | +4 pp | +50 |
| Kimi K3.1 Pro (off) | 76% (71/93) | 30% (28/93) | 6% (6/96) | 55% (53/96) | +70 pp | -25 pp | +95 |
| GLM-5.3 (low) | 86% (80/93) | 49% (46/93) | 8% (8/96) | 31% (30/96) | +78 pp | +18 pp | +60 |
| Claude Opus 5.5 (high) | 60% (56/93) | 51% (47/93) | 4% (4/96) | 4% (4/96) | +56 pp | +46 pp | +10 |
