# Backgammon benchmark v3: response to version 10

Oct 13, 2026 · reply to "Backgammon benchmark v3 design 10"

Version 10 fixes H3 correctly, and I have nothing further.

- **No selection bias:** the compared setups are named before the freeze (closed high, open on), so nothing is chosen on the positions that test it.
- **Each open setup's test is valid without correction:** it must stay non-inferior against every closed setup in its league. Each comparison can run at the full 5% without a correction inside the open setup, because all of them must pass. Holm across the open setups, for "at least one passes", is the right correction on top.
- **The expected result is stated honestly:** in effect each open model is compared with the strongest closed one, so "not shown" is the likely result unless an open model nearly matches it.

From my side the design is done.
