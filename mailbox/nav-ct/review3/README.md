# nav-ct review 3: Ümit #2921 (late entries in the ranking)

Branch `nav-ct`, HEAD 88e0257 = 90cd56e + 3 commits (b8c1c4c, 5d13bf0, 88e0257). Candidate: not merged, not deployed. `delta-vs-90cd56e.patch` is `git diff 90cd56e HEAD -- tools/site`: 5 files, +106 −74 (story.py, home.py, pages.py, checks.py, bg.css).

## What ran (no compute)

- `scripts/run_retained3.sh` rendered 90cd56e and HEAD from the **retained** `/tmp/lct/S.pkl` (results 7b40b30e, made 7 Nov, not re-run) with `render_retained.py`, each followed by `checks.run`: **0 failures on both, exit 0** (`r3-runs.txt`). No `build.compute()`, bootstrap, model call or scorer ran. `render_retained.py` no longer sets `story.LATE_ROWS`: the switch is gone.
- `scripts/review3.py` (`review3-run.txt`, exit 0):
  - Render diff: of 2,549 files, 2,546 are identical. Only `index.html`, `about/index.html` and `bg.css` differ. On the home page, everything outside the leaderboard card and the result cards is unchanged.
  - Numbers: 544 values checked against S, label-aware (`numbers.csv`): **0 differences**. That is every row's bar value and interval, and every line of every details box (judgement, risks found, safe right, took n of N, played safe m of M, error rate, record, cost, decisions, the late line and the provisional line), on all 54 rows. It also covers the 3 result cards.
  - Moved text: each sentence above and under the old table is on About (`text-moved.md`).
  - Browser: **44/44 ok** at 1280 and 390, light and dark (`browser.csv`). Checked: theme; the 3 cards; ranked rows 1..38 in order plus 3 programs; tags on the 8 late-entry rows; the details box of all 9 late entries, by hover at 1280 and by tap at 390 (Drex 2.0 (local) through its expander), each with its late line, its provisional line and the SubQ note; the filter in All, Chat and Decision (ranks kept, programs shown); About #leaderboard; page no wider than the window; no script errors.
  - 32 screenshots in `screenshots/`: cards, leaderboard top, filter Decision, the boxes of Astra (high), REAX 1.3, SubQ Snap 1.1 and Drex 2.0 (local), and About.

## Changes

1. **Row rule.** Late-entry setups join their model's setups. The rule is unchanged: the highest reasoning setting; a model with one setup uses it. On a tie at the same setting, the first in league order wins, then the setup name, never the score. A late entry stands in the league order of the field it played. **Under the table**, one line: "Row rule: each model's highest reasoning setting (off < minimal < low < medium < high < xhigh < max), late entries included; a model with one setup uses it; several setups at that setting: the first in league order, then by setup name, never by score."
2. **Late entries are ranked.** Each has a tag under its name: "late entry", or "late entry · provisional" when its status in the data is Provisional. Each details box has the line "Played the original League N field after the league finished (late entry)". A provisional entry's box also has "Provisional: 18 of 19 matches · not played: GPT-6 Luna (opponent's API out of credit)". SubQ Snap 1.1's box has the identity note (`pages.SUBQ_SELF`). The "Leagues played different positions" caveat is kept. The grey late-entry group and `LATE_ROWS` are removed.
3. **DeepSeek V4.1 Flash 1017** still sits in DeepSeek V4.1 Flash's row: the row is (low) 69.0, and the other settings are 1017 (low), (off) and 1017 (off).
4. **Result cards** now count late entries:
   - Lowest error rate: **GPT-6 Astra (high) 8.8** (7.4 to 10.3), "late entry, League 3 field". It was GPT-6.1 Sol (high) 9.9.
   - Highest risk judgement, every setup: unchanged, **GPT-6 Astra (low) 75.8** (League 3). The card is per setup, not per row; Astra (high) is 74.4.
   - Highest risk judgement, decision models: unchanged, **Liquid d1-ultra 64.0**. Mammoth-1 is 63.2.
5. **Above the table, two lines:** the score ("Risk judgement: 100 = every call right, 50 = always safe · higher is better"), then "One row per model: its highest reasoning setting, late entries included, never its best score (more in About)". The fixed-table note, the rank legend and the long rule moved to a new first About section, **How the leaderboard is built** (`about/#leaderboard`). Three sentences were reworded for their new place (`text-moved.md`).
6. **checks.run:** the All-leagues mixing check now allows late-entry rows in the leaderboard table (`id="headline-table"`) only.

Kept as defaults: other makers grey, Zeki's rank note, Nackgammon per-model rule, layout, Highlights (6 slots, 4 labels), rules quoted as in the prompt.

## Ranking (top 15; all 38 in `ranking.md`)

| # | Row (setup) | Judgement | Tag |
|---:|---|---|---|
| 1 | GPT-6 Astra (high) | 74.4 | late entry |
| 2 | Gemini 4 Argon (high) | 74.1 | |
| 3 | Claude Fable 5.1 (high) | 72.3 | |
| 4 | GPT-6.1 Sol (high) | 72.2 | |
| 5 | Claude Opus 5.5 (high) | 70.0 | |
| 6 | DeepSeek V4.1 Flash (low) | 69.0 | |
| 7 | Grok 4.7 (high) | 68.5 | |
| 8 | Claude Sonnet 5.5 (high) | 68.2 | |
| 9 | Gemini 3.8 Flash (high) | 66.9 | |
| 10 | Kimi K3.1 Pro (off) | 65.9 | |
| 11 | Gemma 4 31B (on) | 64.5 | |
| 12 | Liquid d1-ultra | 64.0 | |
| 13 | Base Labs Mammoth-1 | 63.2 | late entry |
| 14 | Drex Max v1 | 62.9 | late entry · provisional |
| 15 | Qwen3.8-27B (low) | 62.0 | |

The other late entries: REAX 1.3 17th (60.5), Drex Max 1.1 22nd (59.1), Drex 2.0 24th (58.1), Base Labs Elephant-1 27th (57.7), SubQ Snap 1.1 31st (56.7). That makes 38 ranked rows (31 before) and 3 programs.

## Differences from Ümit's expected list

- The top 5 and Mammoth-1 / Drex Max v1 just below d1-ultra are as she expected.
- **GPT-6 Astra:** the (low) and (medium) setups (75.8 and 74.7) are now under Astra's other settings. Before, Astra's row was Astra (medium) 74.7.
- **Grok 4.7 (high)** stays ranked (7th): no Grok late entry exists, so its row does not change.
- **Drex 2.0 (local)** is not its own row. Its setups.json model is "Drex 2.0", so the rule puts it under Drex 2.0's other settings. Both have no setting, so the tie goes to "Drex 2.0" by setup name. It is still shown, tagged and boxed. Giving it its own row needs a model_identity decision.
- **"Provisional" on Drex too.** All four Drex entries, like REAX 1.3, are Provisional in the data: 18 of 19, GPT-6 Luna not played (opponent's API out of credit). So they are tagged "late entry · provisional", not just REAX.
- The Leagues/About late-entry text ("Its games count in no standings table, no league table, … and no other setup's numbers") is unchanged. The leaderboard is not a standings table, but Ümit may want a sentence there saying late entries are ranked on the leaderboard.
