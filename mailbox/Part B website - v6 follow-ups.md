# Part B website: v6 follow-ups

Oct 22, 2026 · Can's three follow-ups to `Part B website - v6 delivery.md`.

**Preview:** https://zekiworks.github.io/analysis/backgammon-preview/ (deployed by the update loop: results `562f092b`, data as of 22 Oct 14:42 UTC, code `44f6f07`). The live URL is unchanged.

## 1. Hero board: three candidates (not switched)

The hero still shows the current position. Every file is in `mailbox/hero-candidates/`:
- `hero-<A|B|C>-<dark|light>.png`: the hero as it would look at 1280 px, rendered from the real home page with only the board swapped.
- `hero-current-*.png`: the hero as it is now, for comparison.
- `candidates.json`: the numbers behind each candidate.

**How the candidates were picked.** `tools/site/hero_candidates.py BUILD_DIR OUT_DIR` reads the exported decisions (the same files Every decision uses) and picks each candidate by a fixed rule, written at the top of the script. It leaves programs out.

**How the board is drawn.** Solid green arrows show the engine's best play. When the model played something else, its play is drawn as dashed red arrows; this is new. "Gives away" means equity lost against the engine's best play (GNUbg 2-ply).

### A: typical Risk pays position where most setups went wrong

| | |
| --- | --- |
| Position | v1-set `v1-0709`, contact, dice 3-2 |
| Opens at | `decisions/?d=v1-set&s=claude-opus-5-5&p=15#dv1-0709` |
| Fewest hitting rolls any play leaves | 0 |
| Engine's best play | `4/1 24/22`, leaves 32 hitting rolls |
| Best safe play | `4/1 3/1`, 0 hitting rolls, gives away 0.088 |
| What the setups did | 17 of 17 played safe. The most common play was `4/1 4/2` (12 setups), which gives away 0.112. None played the engine's best. |

**Why it fits.** Its stake (0.088) is at the 48th percentile of the 355 v1 Risk pays positions. Within the middle fifth of stakes, it is the position with the highest share of setups playing safe.

**Caveat.** Only the v1 set has many setups answering the same position. League games give every setup a different position, so "most setups went wrong" can only come from the v1 set. The hero therefore marks this candidate **Earlier version**, and its figure carries `data-version="v1"`. The 17 setups include Gemini 4 Argon twice (the shuffled replay). When the shared positions are answered, the same rule can pick a v3 position instead.

### B: typical Safety pays decision (a needless risk)

| | |
| --- | --- |
| Decision | League 3, `102778`, Claude Opus 5.5 (on), contact, dice 3-2 |
| Opens at | `decisions/?d=league-3&s=claude-opus-5-5-on&p=1#d102778` |
| Engine's best play | `10/7 7/5`, leaves 0 hitting rolls (it is also the best safe play) |
| The model played | `13/10 13/11`, leaves 2 hitting rolls, gives away 0.060 |

**Why it fits.** League 3 has 324 decisions in which a model took a needless risk, and their median loss is 0.061. This one is the closest to that median. It shows the second way of going wrong, with stakes that are ordinary rather than dramatic.

### C: middle of the road (the risk paid, and the model took it)

| | |
| --- | --- |
| Decision | League 3, `104334`, Claude Fable 5.1 (off), opening phase, dice 5-5, the model starts with a checker on the bar |
| Opens at | `decisions/?d=league-3&s=claude-fable-5-1-off&p=4#d104334` |
| Fewest hitting rolls any play leaves | 24 |
| Best safe play | `bar/20 20/15 8/3 8/3`, leaves 24 hitting rolls, gives away 0.089 |
| Engine's best play | `bar/20 13/8 8/3 8/3`, leaves 27 hitting rolls. The model played it. |

**Why it fits.** Its stake (0.089) is the median of the 4,152 League 3 Risk pays decisions. It shows a model getting the core question right on an ordinary decision.

**Caveat.** The risk difference is small (27 against 24 hitting rolls), so it reads less starkly than A.

### Current: the extreme case, for comparison

| | |
| --- | --- |
| Decision | League 3, `108032`, Gemini 4 Argon (off), dice 2-3 |
| Engine's best play | `3/1* 21/18*`, leaves 11 hitting rolls |
| The model played | `5/3 5/2`, the best safe play: 0 hitting rolls, gives away 1.494 |

The new caption code changed this hero in one way: the model's play is now drawn dashed.

**Switching.** Once Can chooses, I'll make `build.showcase` use that candidate's rule, so the hero still follows the data. The social preview image follows the hero.

## 2. Evidence

### (a) "No hit-risk trade-off" follows v6 line 103

**Code.** `tools/site/analysis.py`:
- `risk_class`, lines 324–336, takes the classes in this order:
  1. Invalid or unscored decisions get no class.
  2. `least = min(shots)`; `if least == max(shots)` (line 333), meaning every legal play leaves the same number of hitting rolls: class `"none"`.
  3. Otherwise Safety pays or Risk pays, by the best safe play's loss against 0.001.

  So a decision gets exactly one class. The hitting rolls are the numbers shown to the model: `describe.py` reproduces the runner's option text, and the v1 numbers are parsed from that text.
- `risk()`, lines 339–378:
  - `"none"` decisions are only counted (`no_risk_choice`).
  - Every share uses its row's class as denominator: `takes_risk = took_when_pays / risk_pays` and `needless_risk = took_needless / safety_pays`. Each cell's `den` is its row total.
  - `"none"` decisions are in no denominator.

**Where the count is shown:**
- every 2×2 tile ("N with no hit-risk trade-off, left out");
- the Risk tab column "No hit-risk trade-off (left out)";
- the 2×2 table;
- each model page;
- the Every decision filter "No hit-risk trade-off (N)";
- in the data files as `risk.no_risk_choice`.

**Pre-deploy checks** (`tools/site/checks.py`):
- line 183: risk decisions + no-choice = scored decisions, per setup;
- line 208: the per-decision marks on Every decision equal the analysis counts.

**Independent recount.** A separate script read every exported decision file (not the analysis code) and classed "none" directly as "all legal plays have equal hitting rolls". It then compared the result with the published `risk` block of each setup. For every setup it checked:
- the none / Risk pays / Safety pays counts match;
- none + Risk pays + Safety pays = scored decisions;
- `takes_risk == took_when_pays / risk_pays` and `needless_risk == took_needless / safety_pays`;
- the cells sum to Risk pays + Safety pays, and every cell's denominator is its row's class total.

| Dataset | Setups matching | No trade-off | Risk pays | Safety pays | Scored |
| --- | --- | --- | --- | --- | --- |
| League 1 | 18 / 18 | 8,238 | 11,949 | 13,068 | 33,255 |
| League 2 | 17 / 17 | 7,521 | 9,625 | 12,120 | 29,266 (+19 invalid, unclassed) |
| League 3 | 11 / 11 | 3,797 | 4,665 | 6,042 | 14,504 |
| v1 set (Earlier version) | 17 / 17 | 4,692 | 6,035 | 6,273 | 17,000 |

0 mismatches.

### (b) No v1/v3 mixing, enforced before every deploy

**What exists by construction:**
- **Rankings.** Every ranking (`pages.by_error`) sorts the setups of one dataset.
- **Leaderboard and sections.** One league view is built at a time (`pages.per_view`). The v1 set is its own view, wrapped in an Earlier-version block (`data-version="v1"`).
- **Data files.** The download `data/results.json` holds leagues only, and the stats strip counts leagues only (77,044 = 33,255 + 29,285 + 14,504). v1 numbers live only in `data/v1/`.
- **Findings.** Each finding's machine check reads one data file (`tools/site/findings.py`), so a check cannot combine versions. None is published yet.

**The check.** `tools/site/checks.py` `check_mixing` (lines 215–241) was tightened today:
- **Coverage.** It now covers every table, every 2×2 wall and every chart SVG. It previously checked tables only.
- **Rule 1.** Every element inside such a unit that names a dataset (rows, tiles, points or the unit itself) must name the same one. This also catches two leagues mixed together.
- **Rule 2.** A unit inside an Earlier-version block may hold no v3 rows.
- **Rule 3.** v1 rows may sit only inside an Earlier-version block. The old rule also accepted a `data-dataset="v1-set"` section. The Phases page's v1 section relied on that, so it now also carries `data-version="v1"`.

**How it blocks a deploy:**
- `checks.run` calls the check on every page (line 282).
- `build.py` exits 2 when any check fails (line 328).
- `update.sh` then does not deploy and writes `mailbox/Backgammon site preview - check failed.md` (line 77 on).

**Census of the deployed build:**

| Units | Count |
| --- | --- |
| Tables holding a single v3 league | 52 |
| v1-only tables, all inside Earlier-version blocks | 13 |
| 2×2 walls holding a single v3 league | 6 |
| v1 2×2 walls, inside Earlier-version blocks | 2 |
| Smoke-test tables (New models) | 2 |
| Tables with no dataset (Method, Data, prompt history) | 81 |
| v1 dot-plot chart, inside its Earlier-version figure | 1 |
| Units mixing datasets | 0 |

**Failing on a deliberately mixed build.** `python3 tools/site/selftest_mixing.py BUILD_DIR` writes every page twice from the same data: once as built, once deliberately mixed. The mixed build:
1. puts a v1 row into each league's quality table;
2. puts a v1 tile into each league's 2×2 wall;
3. puts a v1 table outside any Earlier-version block;
4. puts a League 3 table inside each Earlier-version block.

Output:

```
clean build: 0 mixing failures
mixed build: 39 mixing failures; caught: {'table mixes': True, 'wall mixes': True, 'v1 outside Earlier version': True, 'v3 inside Earlier version': True}
   index.html: a table mixes datasets ['league-1', 'v1-set']
   index.html: v1 rows outside an Earlier-version block
   index.html: a table in an Earlier-version block holds v3 rows ['league-3']
   index.html: a 2x2 wall mixes datasets ['league-1', 'v1-set']
SELFTEST PASSED
```

The full build with the tightened check passed, and the loop deployed it (`562f092b`).

## 3. Preview URL

https://zekiworks.github.io/analysis/backgammon-preview/
