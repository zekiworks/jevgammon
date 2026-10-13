# Backgammon benchmark v3: response to version (3)

Oct 13, 2026 · reply to "Backgammon benchmark v3 design (3)"

Version (3) takes in every point from the last reply. One total is off by 100, and one point about the opening control is new.

## Checked

- **Opening control:** it now appears consistently in the summary, the Shared positions table, the budget and the run order. The open question about it is closed.
- **A12:** the three error rates and two effects are well defined. Weak GNUbg is a sanity anchor only, and the scoring limit is stated.
- **A7 and H5:** they now agree on what Leagues 2 and 3 can test.
- **Runner list:** twelve items, including prompt versions and the public repo.
- **14%:** right (22,400 / about 163,300).
- **Astra low:** about 8,620 calls and about $314, so "8,600" and "$315" are fine.

## One figure

**Total calls:** the budget rows add up to 185,700, not 185,600 (19,300 + 16,600 + 7,400 + 64,000 + 16,000 + 6,400 + 32,000 + 24,000).

## One new point: where the opening table applies

The table effect is measured on the new set's 200 opening positions. The opening table in the prompt covers only the first roll of a game, the 15 non-double opening rolls. It says nothing about the second or later moves. If most of the 200 "opening" positions come after the first move, removing the table changes almost nothing there, and the table effect will be near zero by construction.

Two options:

1. **Define the opening phase to include a fixed share of first-roll positions,** and report the table effect on those positions separately.
2. **Keep the definition as it is,** and state in A12 that the table effect only covers the share of positions where the table applies.

The phase rules are still open, so this can be settled with them.
