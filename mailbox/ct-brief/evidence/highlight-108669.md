# Highlight: decision 108669 (GPT-6 Astra (low), League 3)

## Source
- Export: `/tmp/ctb/live/decisions/league-3/gpt-6-astra-off/12.json.gz`, `.decisions[]` with `id == 108669` (page 12 of 26; the page header gives `dataset: "league-3"`, `setup: "GPT-6 Astra (low)"`, `slug: "gpt-6-astra-off"`).
- Setup listing: `/tmp/ctb/live/decisions/index.json` `.datasets[id=="league-3"].setups[slug=="gpt-6-astra-off"]` (1251 decisions, 26 pages).
- Risk index: `.../gpt-6-astra-off/risk.json.gz` row `[12, 108669, "r", "mr", "b", null]` (page 12, risk, missed risk, big).
- State DB `/tmp/lct/state/snap.db` (read-only): `turns.id=108669` → game 2182, turn 13, white, dice 4-3, `move="7/3 7/4"`, `letter="B"`, `chosen_index=1`, `legal_count=6`, `prompt_version="bg-v2"`, `decided_by="model"`; `position.points` is identical to the export board. `turns.player=1` is the match seat: game 2182 → match 451 `player1=3` = `GPT-6 Astra (off)` (DB name; site label "(low)"), `label="matchday 9: GPT-6 Astra (off) v Claude Opus 5.5 (on)"`.
- Full JSON record + rendering fields: `/tmp/ctb/highlight-108669.json`.

## Facts
- Board (as exported, `.board`): points `[-2,3,2,3,0,3,2,0,0,0,0,0,0,-1,0,0,-2,-3,-3,-2,0,-2,0,2]`, bar `[0,0]`, off `[0,0]`. Same as the prompt: you 24:2 7:2 6:3 4:3 3:2 2:3; opponent 1:2 14:1 17:2 18:3 19:3 20:2 22:2.
- Dice `[4,3]`; pips `[104,130]`; phase `contact`; tag `priming`; game 2182, turn 13, side white.
- Model's play (`.chosen=1`, `.plays[1]`, letter B): `7/3 7/4`, equity −0.7278, loss 0.2238, `hitting_rolls` 0. Description: "leaves 0 blots, the opponent hits with 0 of 36 rolls".
- Engine's best play (`.best=2`, `.plays[2]`, letter C): `6/2 24/21`, equity −0.5040, loss 0.0, `hitting_rolls` 36. Description: "leaves 2 blots, the opponent hits with 36 of 36 rolls" (the blots are on 24 and 21, in the opponent's home board).
- Difference: −0.5040 − (−0.7278) = **0.2238**. This equals `plays[1].loss` and `.risk.stake`.
- `.risk`: `{"class":"risk","call":"missed","call_robust":"missed","band":"big","stake":0.2238,"best_safe":1}`. So the model's play is also the best safe play.
- Other options: A `7/3 24/21` also has 36/36 (−0.7152); D/E/F each leave 1 blot hit by 13/36.
- href (in the form home.py builds, `tools/site/home.py:1304`): `decisions/?d=league-3&s=gpt-6-astra-off&p=12#d108669` (written as `&amp;` in HTML).
- Rendering: `board_svg(record["board"], [4,3], [104,130], play="6/2 24/21", alt="7/3 7/4")`. The export's board shape (`points`/`bar`/`off` lists) is the shape `tools/site/board.py:78` reads.

## Verdicts
1. Zero-blot model play: **CONFIRMED**. `7/3 7/4` leaves 0 blots and `hitting_rolls` is 0.
2. Best play leaves a shot on 36 of 36 rolls: **CONFIRMED**. `6/2 24/21` has `hitting_rolls` 36, and the description says "the opponent hits with 36 of 36 rolls". It leaves 2 blots, not 1, and both are back checkers on 24 and 21. If the copy says "a shot", "two blots" is more accurate.
3. Worth 0.224 more: **CONFIRMED**. The exact value is 0.2238 (−0.5040 vs −0.7278), which rounds to 0.224.

No mismatches.
