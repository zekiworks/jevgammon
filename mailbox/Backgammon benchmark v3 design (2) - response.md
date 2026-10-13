# Backgammon benchmark v3: response to version (2)

Oct 13, 2026 · reply to "Backgammon benchmark v3 design (2)"

Version (2) takes in four points: the H5 scope, the known probability support, the DeepSeek smoke data, and the opening control in the summary. Three edits look unfinished, and one figure is off.

## The opening control is counted in the summary only

Lines 7 and 14 now count the 200 standard opening positions (22,400 calls with the control). The rest of the document still treats them as undecided or leaves them out:

- **Shared positions (line 145)** still asks "do we add 200 standard opening positions …?". The Shared positions table has no row for them.
- **Budget (line 221 and the table)** still says "about 179,000" and "the Nackgammon positions add 16,000", and has no row for the control. With the row (32 setups × 200 = 6,400), the total is about 185,700.
- **"13% more" (line 7):** without change 4 the total is about 163,300, so 22,400 is 13.7%, about 14%. The earlier "16,000, or 10%" was 9.8%.

## A12 still uses weak GNUbg as the reference (line 178)

The A12 row still reads "GNUbg at weak level recalls nothing, so its change is the reference for the variant's difficulty". The point from the last reply stands. GNUbg is a network trained on standard backgammon, and its weak level adds noise to the same evaluation that scores every move. So its change under Nackgammon does not measure difficulty for a player without book knowledge.

With the opening control now in, A12 can say directly:

> Each setup's error rate on Nackgammon positions minus its rate on the standard opening positions without the table. Weak GNUbg is shown as a sanity anchor, not as the reference.

The note that GNUbg scores early Nackgammon positions with a net trained on standard play is also still missing from "Scoring is not perfect".

## Runner list: two items still missing

The list still has ten items; these two from the last reply are not there:

- **Prompt versions.** The runner's only prompt today includes the last 10 moves, added for League #13, so it is not bg-v2. bg-v2 and A2's three prompts need to be selectable, each with a version name logged per decision.
- **Harness commit.** Done since the last reply: jevgammon now has its first commit (`e8542a9`), so a harness commit can be logged. It has no remote yet; the Outputs table needs a public repo to link to.
