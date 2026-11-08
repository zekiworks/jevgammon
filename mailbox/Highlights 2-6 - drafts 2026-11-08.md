# Highlights 2–6: drafts (2026-11-08) — DRAFT, NOT PUBLISHED

**Everything in this file is DRAFT.** Nothing was deployed and the site was not changed. No model was called. The learning pilot's test set was never opened: the script reads only the pilot's game tables.

- **Rules:** Ümit #3113 (slots 2–5) and #3126/#3128/#3138 (slot 6).
- **Selection script (one script for every slot):** `mailbox/highlights-drafts/select_highlights.py`, run from the repo root. It opens everything read-only.
- **Its outputs:**
  - `mailbox/highlights-drafts/facts.json`: every candidate list and the full facts of each pick and runner-up.
  - The board PNGs: the site's `tools/site/board.py` `board_svg`, with the site CSS in the light theme, rendered by headless Chrome.
- **Equities:** GNU Backgammon 2-ply, cubeless money equity for the side to move, as stored with the decisions.
  - For the quiz positions, I checked the 2-ply values against the exported decision records. They are identical.
  - The quiz's 3-ply values and 1296-game rollouts are also given.
- **"Hitting rolls":** the number of the 36 rolls on which the opponent hits, as shown to the models.
- **Boards:** drawn from the mover's side, with the mover at the bottom moving 24 → 1. Solid arrows show the risky (or the engine's) play; dashed arrows show the other play. The legend on each PNG says which is which.

## Flags (read first)

1. **Slots 2, 3 and 5 come from the Clear-risk Part 2 quiz.**
   - It is labelled "Two or four plays shown, not league play." Any caption must keep that label.
   - The site publishes only aggregate quiz results. `clear_risk_publish.py` says the position-to-choice records stay private.
   - So a quiz highlight would be **the first per-position quiz answer made public**. Publishing one needs Ümit's or Can's OK.
2. **Slot 5 (revised per Zeki #3216): "most" = more than half; two named cohorts.**
   - Cohort A: the five quiz chat models: Claude Sonnet 5.5 (high), GPT-6.1 Sol (high), Kimi K3.1 Pro (off), GLM-5.3 (low), Claude Opus 5.5 (high). Cohort B: the three of them that are League 3 setups: Sol (high), Kimi K3.1 Pro (off), Opus 5.5 (high).
   - Decision models allowed: Liquid d1-ultra, Base Labs Mammoth-1, Drex Max v1, REAX 1.3. Only d1-ultra took the quiz, so every quiz qualifier is d1-ultra.
   - Quiz qualifiers: 26 item-versions (cohort A), 21 (cohort B). League-play qualifiers: 11 positions (A), 5 (B), all opening replies or turn 3, gaps ≤ 0.097, and most have n = 1 cohort decision.
   - My pick (my criterion, not Ümit's: the largest gap among qualifiers): **quiz item 74, board only**, gap 0.370. It qualifies in both cohorts (A 3 of 5, B 2 of 3).
3. **Slot 4 (revised per Zeki #3216): the pick is the largest loss, as requested.** The 0.25 margin was my addition and is removed. Kimi K3.1 Pro (off) 153929, the largest needless risk, is shown only as an optional editorial alternative, for Ümit to choose ("preferably a needless risk").
4. **Slot 3: the strict "exactly one model took the risk" rule was applied.**
   - "Most" means 70% or more of the answers in the same-position population.
   - Without "exactly one", the best league-play group would have two risk-takers.
   - The quiz pick (n = 8) beats every league-play group, where the largest gain with exactly one risk-taker is 0.148, n = 4.
5. **Slot 6: the pick meets every part of the rule.** It is in series 1, game 5, after the game-3 lesson. Board, dice, turn and the prompt's match score are all identical in both arms. It also has the largest gain of the 14 qualifying divergence points.

## Changes in this revision (Zeki #3216; no new inference, existing data only)

- **Slot 2:** the draft text cut from 5 sentences to 3; it keeps the warning that the engine's overall best was not one of the two plays shown.
- **Slot 4:** the 0.25 needless-risk margin is removed from the rule. The pick (Argon 108032) is unchanged. Kimi 153929 is now an optional editorial alternative, not a margin result.
- **Slot 5:** re-evaluated with "most" = majority for both named cohorts, quiz and league play, every qualifier listed. The pick changed from item 89 (which came from a 70% threshold that slot 5 does not have) to item 74 (board only). The board was re-rendered (`hl5-decision-model-clearrisk-74.png`; the item-89 PNG was removed).
- `select_highlights.py` and `facts.json` updated to match. Slots 3 and 6 are unchanged.
- Quiz examples stay private: these are mailbox drafts only; nothing is published.

---

## Slot 2: GPT-6.1 Sol (high): took the good risk with the board only, played safe when shown the numbers

**Selection** (`select_highlights.py`, section "slot 2"):
- **Population:** Clear-risk Part 2, the 93 rollout-confirmed "Risk wins" items.
- **Condition:** Sol's Q1 answer was the risky play in the board-only version and the safe play in the with-numbers version.
- **Parsing:** exactly as the frozen `p2rep.py` (the chat answer's JSON `choice`; failed or invalid answers count as no answer).
- **Result:** 36 items meet it. Pick = the largest 2-ply gap between the two plays shown.

**Pick: quiz item 98.** Gap 0.7289, the largest by far.
**Runner-up: item 71** (gap 0.3941; 6/3 24/22\* vs 6/3 3/1, dice 3-2, from League 2 decision 30614, Gemini 3.8 Flash (high)).

**Facts**

| | |
|---|---|
| Source | League 2 decision 33340 (Claude Sonnet 5.5 (high), which played 22/18\* 18/17), `decisions/?d=league-2&s=claude-sonnet-5-5-high&p=15#d33340` |
| Side to move, dice, pips | white, 1-4, 86 vs 44 |
| Board (mover's numbering) | you 1:2 2:2 3:3 4:3 5:3 22:2; opponent 18:1 20:4 23:7 24:3 |
| Plays shown (in order) | A 2/1 22/18\*, B 4/3 5/1 |
| Sol, board only | **2/1 22/18\*** (the risky play) |
| Sol, with numbers | **4/3 5/1** (the safe play) |
| 2/1 22/18\* | 2-ply −0.0932; hits on 12 of 36 rolls; 3-ply −0.1049; rollout −0.074 ± 0.002 |
| 4/3 5/1 | 2-ply −0.8221; hits on 0 of 36 rolls; 3-ply −0.8374; rollout −0.838 ± 0.001 |
| Gap (risky − safe) | **0.7289** (2-ply); 0.7325 (3-ply) |
| Engine's best of all 12 legal plays | 22/18\* 18/17, 2-ply +0.1755, 2 hitting rolls (not one of the two plays shown) |
| Other models on this item | Board only: all 8 chose the risky play. With numbers: Sonnet, GLM and Opus chose it; Celeris, Jev, d1-ultra, Sol and Kimi chose the safe play |

**Draft text (DRAFT)**
> White trails the race 86 pips to 44, with two checkers back on its 22 point and an opponent blot on 18. Shown only the board and two plays, GPT-6.1 Sol (high) chose 2/1 22/18\*, hitting and leaving a shot on 12 of 36 rolls; shown the same two plays with their computed numbers, it chose 4/3 5/1, which leaves no shot. The hit is worth 0.729 more in equity (GNU Backgammon 2-ply), though the engine's best play, 22/18\* 18/17, was not one of the two shown.

Label to keep: "Two plays shown, not league play."
Board: `mailbox/highlights-drafts/hl2-sol-clearrisk-98.png` (solid: 2/1 22/18\*; dashed: 4/3 5/1).

---

## Slot 3: a great risk: most models played safe, one took the risk, and the engine agrees

**Selection** (section "slot 3"):
- **Same-position populations, both searched:**
  - (a) **Clear-risk Part 2 Q1.** Each version of each Risk-wins item is one population, n = the 8 models that answered: Celeris-1 Decision, Jev 1.14.0, Liquid d1-ultra, Claude Sonnet 5.5 (high), GPT-6.1 Sol (high), Kimi K3.1 Pro (off), GLM-5.3 (low), Claude Opus 5.5 (high).
  - (b) **Identical positions in league play** (same board from the mover's side and same dice) across all leagues and late-entry matches. Programs (GNUbg weak, Safest, Random) are left out, and the engine's class must be "risk".
- **Rule:** 70% or more safe; exactly one model took the (right) risk.
- **Gain:** the risk play's equity minus the best safe play's equity.

**Pick: quiz item 79, with numbers.** n = 8, 7 safe (88%); gain 0.5082.
**Runner-up: quiz item 97, with numbers.** n = 8, 7 safe; Claude Sonnet 5.5 (high) took 18/15 15/11; gain 0.3840.
**Best in league play:**
- League 1 decision 199003: DeepSeek V4.1 Flash (off) played 13/11 11/5 with 2-6; 3 of 4 decisions safe; gain 0.148.
- Largest with n ≥ 9: decision 201076 (a valid match outside the shown leagues), LFM2.5-24B-A2B (on) played 24/20\* 20/18 with 4-2 at turn 2; 10 decisions by 9 models, 9 of them safe; gain 0.133.

**Facts**

| | |
|---|---|
| Source | League 2 decision 160825 (DeepSeek V4.1 Flash 1017 (off), which played the safe 2/1 3/1), `decisions/?d=league-2&s=deepseek-v4-1-flash-1017-off&p=17#d160825` |
| Side to move, dice, pips | white, 1-2, 103 vs 126 |
| Board (mover's numbering) | you 2:4 3:3 4:2 6:2 11:2 22:2; opponent 5:2 12:2 16:1 17:2 19:3 20:1 21:2 23:2 |
| Plays shown | A 2/1 3/1, B 2/1 22/20\* |
| With numbers: safe 2/1 3/1 | Celeris, Jev, d1-ultra, Sonnet, Sol, Kimi, GLM (**7 of 8**) |
| With numbers: risky 2/1 22/20\* | **Claude Opus 5.5 (high)** only |
| 2/1 22/20\* | 2-ply +0.3526; hits on 18 of 36 rolls; 3-ply +0.3271; rollout +0.359 ± 0.004 |
| 2/1 3/1 | 2-ply −0.1557; hits on 0 of 36 rolls; 3-ply −0.1659; rollout −0.183 ± 0.003 |
| Gain | **0.5082** (2-ply); 0.4930 (3-ply) |
| Engine's best of all 20 legal plays | 2/1 22/20\* (the risky play shown) |
| For context | Board only, 6 of 8 chose the hit (only Sol and GLM played safe). The crowd went safe once the numbers were shown |

**Draft text (DRAFT)**
> White has two back checkers on its 22 point, and the opponent has left a blot on 20, right in front of them. Shown two plays with their computed numbers, seven of eight models chose 2/1 3/1, which makes the 1 point and leaves no shot. Claude Opus 5.5 (high) alone chose 2/1 22/20\*, hitting the blot and leaving a shot on 18 of 36 rolls. The engine's best play is that hit, worth 0.508 more in equity than the safe play (GNU Backgammon 2-ply).

Label to keep: "Two plays shown, not league play."
Board: `mailbox/highlights-drafts/hl3-great-risk-clearrisk-79.png` (solid: 2/1 22/20\*; dashed: 2/1 3/1).

---

## Slot 4: a frontier blunder (largest equity loss by a League 3 model)

**Selection** (section "slot 4"):
- **Population:** every published League 3 decision (`decisions/league-3/*/N.json.gz`), excluding programs and invalid answers. The loss is the chosen play's `loss`.
- **Rule:** the largest loss (Ümit: "largest equity loss by a League 3 model, preferably a needless risk"). The largest needless risk is listed separately as an optional editorial alternative.

**Ranking:**

| rank | decision | setup | loss | call |
|---|---|---|---:|---|
| 1 | 108032 | Gemini 4 Argon (low) | 1.4936 | missed risk |
| 2 | 157908 | Grok 4.7 (high) | 1.2742 | missed risk |
| 3 | 144040 | Grok 4.7 (high) | 1.1431 | right risk (a worse risky play than the best) |
| 4 | 153929 | Kimi K3.1 Pro (off) | 1.0309 | **largest needless risk** |
| 5 | 155214 | Kimi K3.1 Pro (off) | 1.0004 | needless risk |

**Pick: 108032, the largest loss (a missed risk, not a needless one).** Optional editorial alternative: 153929, the largest needless risk (loss 1.0309, 0.4627 smaller). Ümit may prefer it under "preferably a needless risk".

**Facts (pick)**

| | |
|---|---|
| Decision | 108032, League 3, Gemini 4 Argon (low); game 2158, turn 22; `decisions/?d=league-3&s=gemini-4-argon-off&p=11#d108032` |
| Side to move, dice, pips | black, 2-3, 93 vs 133 |
| Board (mover's numbering) | you 2:3 3:3 4:2 5:2 6:3 21:2; opponent 1:1 12:2 15:2 17:2 18:1 19:5 20:2 (a five-point board, opponent blots on 1 and 18) |
| Argon's play | **5/3 5/2**: equity −0.2042; leaves 0 blots, hit on 0 of 36 rolls (the only zero-shot play of the 16) |
| Engine's best | **3/1\* 21/18\***: equity +1.2894; hits 2; leaves 3 blots, hit on 11 of 36 rolls |
| Loss | **1.4936**; the risk class is "risk", call missed (also by the robust margin), stake 1.4936 |

**Draft text (DRAFT)**
> Gemini 4 Argon (low) had 2-3 to play with a five-point board, and the opponent had left blots on its 1 point and on 18. It played 5/3 5/2, the only play that leaves no shot. The engine's best play, 3/1\* 21/18\*, hits both blots and leaves a shot on 11 of 36 rolls. It is worth 1.494 more in equity (GNU Backgammon 2-ply), the largest single loss by any League 3 model.

Board: `mailbox/highlights-drafts/hl4-frontier-blunder-108032.png` (solid: 3/1\* 21/18\*; dashed: 5/3 5/2).

**Optional editorial alternative (Ümit's choice): 153929, the largest needless risk**
- Kimi K3.1 Pro (off), game 3062, turn 41, white, dice 2-4, pips 30 vs 154; the opponent has 2 checkers on the bar.
- `decisions/?d=league-3&s=kimi-k3-1-pro-off&p=10#d153929`.
- Kimi played 2/off 4/off: equity +0.6988; 2 blots, hit on 20 of 36 rolls. The engine's best is 4/2 4/off: +1.7297, 0 rolls. Loss 1.0309.
- Alternative draft (DRAFT): "Kimi K3.1 Pro (off) was bearing off with two of the opponent's checkers on the bar. It played 2/off 4/off, which leaves two blots that the opponent hits on 20 of 36 rolls. The engine's best play, 4/2 4/off, also bears a checker off and leaves no shot; it is worth 1.031 more in equity (GNU Backgammon 2-ply). This was the largest needless risk by a League 3 model." (No PNG rendered for the alternative.)

---

## Slot 5: a decision-model surprise: the right risk while the frontier models played safe

**Selection** (`select_highlights.py`, section "slot 5"; revised per Zeki #3216):
- **Decision models:** Liquid d1-ultra, Base Labs Mammoth-1, Drex Max v1, REAX 1.3. A position counts if one of them took the right risk (the engine's class is "risk", call right risk; in the quiz, the risky play of a Risk-wins item).
- **"Most frontier models played safe":** more than half of the named cohort's answers on that same position were safe (2 of 3 counts). There is no 70% threshold here.
  - **Cohort A**, the 5 quiz chat models: Claude Sonnet 5.5 (high), GPT-6.1 Sol (high), Kimi K3.1 Pro (off), GLM-5.3 (low), Claude Opus 5.5 (high).
  - **Cohort B**, the 3 League 3 models among them: GPT-6.1 Sol (high), Kimi K3.1 Pro (off), Claude Opus 5.5 (high).
- **Populations:**
  - **Quiz:** each version of each Risk-wins item; n = cohort answers (5 or 3). Only d1-ultra of the four took the quiz.
  - **League play:** identical board (mover's side) and dice across all leagues and late-entry matches; n = cohort decisions on that position (a setup can appear more than once).
- **Gap:** quiz = the risky play minus the safe play shown; league = the decision model's play minus the best safe play (2-ply).
- **Selection among qualifiers (my criterion, not Ümit's):** the largest gap. All qualifiers are listed below, so another criterion can be applied.

**Cohort “5 quiz chat models”, quiz: 26 qualifying item-versions** (decision model: Liquid d1-ultra in every row)

| item | version | gap | cohort safe / n | cohort risk-takers |
|---|---|---:|---:|---|
| 74 | board only | 0.3700 | 3/5 | Claude Sonnet 5.5 (high), GPT-6.1 Sol (high) |
| 89 | board only | 0.1697 | 4/5 | GPT-6.1 Sol (high) |
| 91 | board only | 0.1670 | 4/5 | GPT-6.1 Sol (high) |
| 72 | with numbers | 0.1534 | 3/5 | Kimi K3.1 Pro (off), GLM-5.3 (low) |
| 72 | board only | 0.1534 | 3/5 | GPT-6.1 Sol (high), GLM-5.3 (low) |
| 50 | board only | 0.1364 | 5/5 | — |
| 41 | board only | 0.1343 | 4/5 | Kimi K3.1 Pro (off) |
| 47 | with numbers | 0.1244 | 4/5 | Kimi K3.1 Pro (off) |
| 47 | board only | 0.1244 | 4/5 | Kimi K3.1 Pro (off) |
| 43 | with numbers | 0.1213 | 3/5 | GPT-6.1 Sol (high), Claude Opus 5.5 (high) |
| 65 | with numbers | 0.1162 | 4/5 | GPT-6.1 Sol (high) |
| 56 | board only | 0.1143 | 3/5 | GPT-6.1 Sol (high), Kimi K3.1 Pro (off) |
| 55 | board only | 0.0978 | 3/5 | GPT-6.1 Sol (high), Kimi K3.1 Pro (off) |
| 53 | board only | 0.0977 | 4/5 | Kimi K3.1 Pro (off) |
| 39 | with numbers | 0.0927 | 3/5 | GPT-6.1 Sol (high), Kimi K3.1 Pro (off) |
| 27 | with numbers | 0.0888 | 4/5 | Claude Opus 5.5 (high) |
| 27 | board only | 0.0888 | 4/5 | GPT-6.1 Sol (high) |
| 48 | board only | 0.0880 | 3/5 | GPT-6.1 Sol (high), Claude Opus 5.5 (high) |
| 17 | board only | 0.0685 | 3/5 | GPT-6.1 Sol (high), Claude Opus 5.5 (high) |
| 21 | with numbers | 0.0646 | 4/5 | GLM-5.3 (low) |
| 8 | board only | 0.0601 | 3/5 | GPT-6.1 Sol (high), Kimi K3.1 Pro (off) |
| 25 | board only | 0.0587 | 4/5 | GPT-6.1 Sol (high) |
| 14 | with numbers | 0.0469 | 5/5 | — |
| 14 | board only | 0.0469 | 5/5 | — |
| 16 | with numbers | 0.0460 | 4/5 | Claude Sonnet 5.5 (high) |
| 16 | board only | 0.0460 | 4/5 | GPT-6.1 Sol (high) |

**Cohort “5 quiz chat models”, league play (identical board and dice): 11 positions**

| dice, turn | decision model(s) (decision id, play) | gap | cohort safe / n | cohort decisions (id, play, call) |
|---|---|---:|---:|---|
| 4-5, turn 2 | Drex Max v1 (236134, 13/8 24/20); Liquid d1-ultra (210423, 24/20 13/8) | 0.0969 | 1/1 | Kimi K3.1 Pro (off) (199732, 13/8 6/2, missed) |
| 4-3, turn 3 | Liquid d1-ultra (37961, 13/9 13/10) | 0.0532 | 1/1 | GLM-5.3 (low) (79114, 13/10 10/6, missed) |
| 1-4, turn 2 | Base Labs Mammoth-1 (216777, 13/9 24/23); Drex Max v1 (226106, 24/23 13/9); Liquid d1-ultra (241128, 13/9 24/23) | 0.0375 | 2/2 | Claude Sonnet 5.5 (high) (88470, 13/9 9/8, missed); Claude Sonnet 5.5 (high) (129404, 13/9 9/8, missed) |
| 3-2, turn 2 | REAX 1.3 (247131, 24/21 13/11) | 0.0371 | 1/1 | GLM-5.3 (low) (24461, 13/11 11/8, missed) |
| 1-2, turn 2 | Drex Max v1 (228482, 13/11 6/5) | 0.0335 | 1/1 | Claude Sonnet 5.5 (high) (27223, 13/11 11/10, missed) |
| 4-5, turn 2 | Liquid d1-ultra (39482, 24/20 13/8) | 0.0283 | 1/1 | Claude Opus 5.5 (high) (177853, 13/8 13/9, missed) |
| 4-5, turn 2 | Liquid d1-ultra (129343, 24/20 13/8); Liquid d1-ultra (141796, 13/8 24/20) | 0.0247 | 2/2 | GPT-6.1 Sol (high) (87213, 13/8 13/9, missed); Claude Sonnet 5.5 (high) (129376, 13/9 13/8, missed) |
| 4-1, turn 2 | Liquid d1-ultra (165419, 24/23 13/9) | 0.0234 | 2/3 | Claude Sonnet 5.5 (high) (76604, 13/9 9/8, missed); Claude Sonnet 5.5 (high) (131635, 13/9 9/8, missed); GPT-6.1 Sol (high) (148586, 13/9 6/5, wrong risk) |
| 5-5, turn 2 | Liquid d1-ultra (133324, 8/3 8/3 6/1* 6/1) | 0.0152 | 1/1 | GLM-5.3 (low) (133337, 13/8 13/8 6/1* 6/1, missed) |
| 2-3, turn 2 | REAX 1.3 (245762, 24/21 13/11) | 0.0136 | 2/3 | Claude Sonnet 5.5 (high) (92548, 13/10 10/8, missed); Claude Opus 5.5 (high) (120669, 13/10 13/11, wrong risk); GLM-5.3 (low) (162618, 13/10 10/8, missed) |
| 5-1, turn 2 | Liquid d1-ultra (85825, 8/7* 13/8) | 0.0114 | 1/1 | Kimi K3.1 Pro (off) (183199, 8/7* 6/1*, missed) |

**Cohort “3 League 3 models”, quiz: 21 qualifying item-versions** (decision model: Liquid d1-ultra in every row)

| item | version | gap | cohort safe / n | cohort risk-takers |
|---|---|---:|---:|---|
| 74 | board only | 0.3700 | 2/3 | GPT-6.1 Sol (high) |
| 96 | board only | 0.2589 | 2/3 | Kimi K3.1 Pro (off) |
| 89 | board only | 0.1697 | 2/3 | GPT-6.1 Sol (high) |
| 91 | board only | 0.1670 | 2/3 | GPT-6.1 Sol (high) |
| 72 | with numbers | 0.1534 | 2/3 | Kimi K3.1 Pro (off) |
| 72 | board only | 0.1534 | 2/3 | GPT-6.1 Sol (high) |
| 50 | board only | 0.1364 | 3/3 | — |
| 41 | board only | 0.1343 | 2/3 | Kimi K3.1 Pro (off) |
| 47 | with numbers | 0.1244 | 2/3 | Kimi K3.1 Pro (off) |
| 47 | board only | 0.1244 | 2/3 | Kimi K3.1 Pro (off) |
| 65 | with numbers | 0.1162 | 2/3 | GPT-6.1 Sol (high) |
| 53 | board only | 0.0977 | 2/3 | Kimi K3.1 Pro (off) |
| 27 | with numbers | 0.0888 | 2/3 | Claude Opus 5.5 (high) |
| 27 | board only | 0.0888 | 2/3 | GPT-6.1 Sol (high) |
| 21 | with numbers | 0.0646 | 3/3 | — |
| 25 | board only | 0.0587 | 2/3 | GPT-6.1 Sol (high) |
| 14 | with numbers | 0.0469 | 3/3 | — |
| 14 | board only | 0.0469 | 3/3 | — |
| 16 | with numbers | 0.0460 | 3/3 | — |
| 16 | board only | 0.0460 | 2/3 | GPT-6.1 Sol (high) |
| 6 | board only | 0.0440 | 2/3 | Kimi K3.1 Pro (off) |

**Cohort “3 League 3 models”, league play (identical board and dice): 5 positions**

| dice, turn | decision model(s) (decision id, play) | gap | cohort safe / n | cohort decisions (id, play, call) |
|---|---|---:|---:|---|
| 4-5, turn 2 | Drex Max v1 (236134, 13/8 24/20); Liquid d1-ultra (210423, 24/20 13/8) | 0.0969 | 1/1 | Kimi K3.1 Pro (off) (199732, 13/8 6/2, missed) |
| 4-5, turn 2 | Liquid d1-ultra (39482, 24/20 13/8) | 0.0283 | 1/1 | Claude Opus 5.5 (high) (177853, 13/8 13/9, missed) |
| 4-5, turn 2 | Liquid d1-ultra (129343, 24/20 13/8); Liquid d1-ultra (141796, 13/8 24/20) | 0.0247 | 1/1 | GPT-6.1 Sol (high) (87213, 13/8 13/9, missed) |
| 3-4, turn 2 | Base Labs Mammoth-1 (218672, 24/20 13/10) | 0.0232 | 1/1 | Claude Opus 5.5 (high) (105202, 13/9 9/6, missed) |
| 5-1, turn 2 | Liquid d1-ultra (85825, 8/7* 13/8) | 0.0114 | 1/1 | Kimi K3.1 Pro (off) (183199, 8/7* 6/1*, missed) |

**My pick: quiz item 74, board only.** It has the largest gap of any qualifier (0.3700) and qualifies in both cohorts: cohort A 3 of 5 safe, cohort B 2 of 3 safe.
- **Why not league play:** every league qualifier is an opening reply (turn 2) or turn 3, gaps ≤ 0.097, and n is 1 in most rows (n ≤ 3 everywhere). That is too thin for "most frontier models".
- **Next by gap:** item 96, board only (0.2589; qualifies in cohort B only, 2 of 3 safe; in cohort A only 2 of 5 were safe); then item 89, board only (0.1697; A 4/5, B 2/3); then item 91, board only (0.1670; A 4/5, B 2/3).
- **If a unanimous cohort is preferred:** item 50, board only (0.1364; A 5/5, B 3/3; Jev 1.14.0 also took the risk).
- **Weak point of the pick:** the majority is thin, since Sonnet 5.5 (high) and Sol (high) also took the risk with the board only. And with the numbers shown, d1-ultra (and all eight models) chose the safe 5/2 6/2.

**Facts (pick)**

| | |
|---|---|
| Source | League 2 decision 129710 (Claude Sonnet 5.5 (high), which played 13/10 13/9), `decisions/?d=league-2&s=claude-sonnet-5-5-high&p=28#d129710` |
| Side to move, dice, pips | white, 3-4, 123 vs 112 |
| Board (mover's numbering) | you 2:2 4:3 5:3 6:3 13:2 24:2; opponent 1:2 15:1 18:3 19:3 22:3 23:3 |
| Plays shown (in order) | A 24/21 21/17, B 5/2 6/2 |
| Board only: risky 24/21 21/17 | **Liquid d1-ultra**; Claude Sonnet 5.5 (high), GPT-6.1 Sol (high) |
| Board only: safe 5/2 6/2 | Celeris-1 Decision, Jev 1.14.0; **Kimi K3.1 Pro (off), GLM-5.3 (low), Claude Opus 5.5 (high)** |
| With numbers | all 8 chose 5/2 6/2 |
| 24/21 21/17 | 2-ply +0.5209; hits on 33 of 36 rolls; 3-ply +0.5679; rollout +0.608 ± 0.004 |
| 5/2 6/2 | 2-ply +0.1509; hits on 0 of 36 rolls; 3-ply +0.1857; rollout +0.195 ± 0.004 |
| Gap | **0.3700** (2-ply); 0.3822 (3-ply) |
| Engine's best of all 14 legal plays | 24/21 21/17 (the risky play shown) |

**Draft text (DRAFT)**
> White has 3-4 to play, 11 pips behind in the race, with two back checkers still on its 24 point. Shown only the board and two plays, the decision model Liquid d1-ultra chose 24/21 21/17, running a back checker and leaving shots on 33 of 36 rolls. Three of the five chat models, Kimi K3.1 Pro (off), GLM-5.3 (low) and Claude Opus 5.5 (high), chose 5/2 6/2, which leaves none. The engine's best play is d1-ultra's, worth 0.370 more in equity (GNU Backgammon 2-ply).

Label to keep: "Two plays shown, not league play." If this is used, disclose that with the numbers shown d1-ultra also played safe.
Board: `mailbox/highlights-drafts/hl5-decision-model-clearrisk-74.png` (solid: 24/21 21/17; dashed: 5/2 6/2).

---

## Slot 6: learning pilot: where the own-lessons arm and the no-memory arm split

**Selection** (section "slot 6"):
- **Data:** `smoke/learning-pilot.db` and `smoke/learning-pilot-plays.db`, games only. The `answers` table (evaluations) and the test-set files are never read.
- **Matches:** for each series s01–s10 and game 1–10, the finished control match and lessons match.
- **Walk:** the turns of both arms in order. Up to the first different play, every turn's turn number, side, mover, dice and board must be identical; the script asserts this.
- **Keep:** the divergences where:
  - the first different play is Gemma's;
  - the lessons arm's play is a right risk;
  - the control arm's play is a missed risk (the engine's class is "risk").
- **Result:** 14 points qualify.
- **Pick:** prefer series 1, game 4 or later (after the "Stop playing too safely" lesson written after game 3), then the largest gain.

**Pick: series 1, game 5, turn 11.** It is the only series-1 qualifier after game 3, and also the largest gain of the 14 (0.6265).
**Runner-up: series 9, game 7, turn 15.**
- Lessons played 5/4\* 13/8 (−0.0527, 12 rolls); control played 6/5 6/1 (−0.4226, 11 rolls); gain 0.3699.
- The board is identical, but the prompt's match score differs: 5-4 for lessons, 6-4 for control.

**Facts (pick)**

| | |
|---|---|
| Ids | series 1, game 5 (round 3, leg 1); control match 1, turn id 335; lessons match 6, turn id 2642 |
| Side to move, dice, pips | Gemma 4 31B (off) as white, 4-6, 132 vs 137 |
| Prompt lines (identical in both arms) | "Score: you 5, opponent 0 (you lead by 5)." / "Match: round 3 of 5, game 1 of 2 in this round." / turn 11 |
| Board (mover's numbering) | you 2:2 5:3 6:3 7:3 13:2 24:2; opponent 4:2 12:2 17:3 18:1 19:5 21:2 |
| No-memory (control) arm | **5/1 7/1**: 2-ply −0.2608; hit on 0 of 36 rolls (call: missed risk) |
| Own-lessons arm | **24/18\* 18/14**: 2-ply +0.3657; hit on 19 of 36 rolls (call: right risk) |
| Engine's best of 17 legal plays | 24/18\* 18/14 (the lessons arm's play) |
| Gap | **0.6265** |
| Lessons in context | the notes written after games 1–4 of series 1, including "Stop playing too safely; prioritize hitting the opponent's blots…" (after game 3) |

**Draft text (DRAFT)**
> In series 1, game 5, both arms of Gemma 4 31B (off) reached this position with the same dice, 4-6, and the same 5-0 score. The no-memory arm played 5/1 7/1, which leaves no shot. The own-lessons arm, whose notes since game 3 included "Stop playing too safely", played 24/18\* 18/14, hitting and leaving a shot on 19 of 36 rolls. The engine's best play is the hit, worth 0.626 more in equity (GNU Backgammon 2-ply).
>
> One position where the two arms split. This board illustrates, it does not prove: on the test set, own lessons found 5.5 more of every 100 good risks than the empty-context retest (exploratory, after the results); the pre-registered threshold was not met.

(The caption, the second paragraph, is verbatim from Ümit.)
Board: `mailbox/highlights-drafts/hl6-learning-pilot-s01g05.png`. Both plays are on one board: solid 24/18\* 18/14 (own lessons, also the engine's best); dashed 5/1 7/1 (no memory).
