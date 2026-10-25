# Reviewed backgammon brief (handoff ZEKI-HANDOFF-1563450109356806227-BG): status

## Acknowledgement (Oct 24, 07:30 UTC)

- Marker `ZEKI-HANDOFF-1563450109356806227-BG` received.
- Brief read in full: `BG-brief.md`, 117 lines, SHA256 `48793261cc49c937cd7888e20f270ad5a60866fe965365d4f6afd2dedc46dcb3` (matches the handoff).
- Authorization as stated in the handoff: Ümit's Discord message `1563352977106796575`; Can resumed pending work in `1563450109356806227`.

## Queued, not started

Work starts after the current job finishes: League 2's last 4 ladder round-1 matches (Gemma 4 31B (on) and Qwen3.8-27B (on) against Liquid d1-ultra and Claude Fable 5.1 (off)), still running on bariton GPUs 0 and 1. Those matches are not interrupted, and only one writer at a time uses `v3.db`.

## Gates kept

- No league match for Liquid d1.1 or Kimi K3.1 Pro (off) before the smoke rows and Kimi's measured cost projection are in this folder.
- Kimi: one $30 hard cap at list prices, covering smoke tests, retries, (off)'s League 3 games and (on)'s 200 fixed positions. Kimi (on) is first-look only, never in a league.
- No model server is started, stopped or reconfigured on bariton or the Sparks.
- Site changes (title and subtitle, Risk tab, ability and caution, Confidence tab, Method) are built and reported here first; nothing is published without approval. The live site's update loop deploys whatever is on `main`, so this work stays on a branch until approval.
- This brief doesn't settle the other pending questions (findings, computed reference rows, hero, ladder round 2).

## Milestones

Reported below as each part is done.

## Items 2–6 (site work on branch `brief-2026-10-24`, not merged, not deployed) — Oct 24, 13:40 UTC

Worked in a separate worktree (`../jevgammon-brief`); `v3.db` opened read-only only (probability audit). Data: site snapshot of 12:51 UTC (all three leagues Finished). Preview built to `/tmp/bgbrief/out` with `tools/site/build.py`; its pre-deploy checks (`checks.run`: numbers trace, counts, mixing, banned strings/hosts/keys, links) passed (results `ec6cf150`). Screenshots: `/tmp/bgbrief/screens/` (hero, Risk table SDT columns). Social preview image: `/tmp/bgbrief/out/share/preview-*.png`. **Nothing deployed; needs approval.**

**Method specification** fixed and committed before computing: `tools/site/content/method-spec-2026-10-24.md` + `analysis_2026-10-24.json` (commit e48bf72, 12:54 UTC). No amendment since.

### Already done / changed / blocked
- Already done (verified on the live site, not duplicated): 0.02 robustness tables for all three leagues; margin in table-PNG and chart-PNG footers.
- Item 2 changed: subtitle "And when does playing safe cost more?" in hero, meta description (title + subtitle prepended), og/twitter title, social preview card (replaces "Every backgammon move scored by an engine: …"), header line of table/page/chart PNGs and risk call card. Title and intro unchanged.
- Item 3 changed: "<N> risks with a probability‡" + footnote; grouped (and other) exclusions counted per row; footer text exactly as briefed.
- Item 4 changed: d′, c, aim, c* columns on both Risk tables (0.001 and 0.02), "Ability and caution" chart tab (both margins, programs as squares, c* bar only where valid, limit line), "by reasoning setting (UNPAIRED)" table in Leagues 2 and 3, Method "Ability and caution" subsection.
- Item 5 changed: probability audit (`tools/site/prob_audit.py` → `content/probability_audit.json.gz`), 5A/5B/5D on Confidence tab, 5C on Cost tab, Method section "Re-read, refit, bar and distributions" (`tools/site/offline.py`).
- GNUbg CPU scoring: not needed — every legal play of every league decision already has a 2-ply value (no selected play lacked one).
- Blocked/not done: no deploy (approval gate); no Kimi K3.1 Pro (on) row (first-look only, BriefPart1's item).

### Probability support audit (raw responses vs stored vectors)
complete 49,253 · sparse 16,860 · grouped 4,122 · invalid 211 · no probabilities (choice-only, programs) 45,749 · unverified 0 · no raw 0. Every stored vector was reproduced from its raw response. Sparse = a legal letter missing from the returned top log-probabilities (zero-filled and renormalised by the runner). League 1 decision services are all complete (except LFM2.5 (off): 260 sparse); League 2 letter-readout models are mostly sparse (e.g. DeepSeek V4.1 Flash (off) 598 complete / 1,015 sparse; Gemma 4 31B (on) 198 / 1,456; LFM2.5 (on) 104 / 1,371); Liquid d1-ultra 1,737 complete. League 3: choice-only, no probabilities → 5A/5B/5D N/A.
**Limit:** complete letter-readout records are positions with few options (all letters fit in the top-k), so in League 2 they are a selected, not representative, subset.

### Ability and caution (item 4; counts raw, rates log-linear corrected; c* rules from the spec)

### League 1, margin 0.001

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 0.87 [0.68, 1.06] | +0.94 [+0.85, +1.03] | 221/722 | 72/852 | 181/221 | -0.09 | unstable: fewer than 200 needless risks behind a mean cost |
| Clef | 0.93 [0.80, 1.08] | +0.13 [+0.05, +0.20] | 470/742 | 226/817 | 338/470 | +0.29 | valid |
| Cygnet (Gemma 4 12B) | 0.72 [0.59, 0.86] | +0.80 [+0.73, +0.87] | 242/733 | 94/765 | 186/242 | +0.10 | unstable: fewer than 200 needless risks behind a mean cost |
| Decider Flash v1.2 | 0.62 [0.50, 0.75] | +0.10 [+0.02, +0.17] | 395/674 | 245/717 | 216/395 | +0.62 | valid |
| Decider v1.1 27B | 0.68 [0.55, 0.80] | +0.52 [+0.45, +0.60] | 292/682 | 164/840 | 231/292 | +0.52 | unstable: fewer than 200 needless risks behind a mean cost |
| Decider v1.2 27B | 0.77 [0.67, 0.88] | +0.54 [+0.47, +0.61] | 307/700 | 141/792 | 237/307 | +0.31 | unstable: fewer than 200 needless risks behind a mean cost |
| Fastino GLiDE | 0.86 [0.72, 0.99] | +0.28 [+0.20, +0.37] | 401/718 | 206/868 | 285/401 | +0.53 | valid |
| Fastino GLiDE v1.2 (local) | 0.76 [0.63, 0.89] | +0.58 [+0.50, +0.67] | 270/642 | 130/778 | 217/270 | +0.27 | unstable: fewer than 200 needless risks behind a mean cost |
| GNUbg weak | 1.70 [1.52, 1.90] | -0.43 [-0.51, -0.36] | 568/631 | 270/801 | 414/568 | +0.52 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6 Luna | 0.68 [0.51, 0.85] | +0.91 [+0.82, +1.00] | 201/711 | 73/694 | 160/201 | -0.07 | unstable: fewer than 200 needless risks behind a mean cost |
| Jev 1.13.0 | 0.99 [0.78, 1.21] | +0.86 [+0.78, +0.96] | 235/659 | 67/765 | 178/235 | -0.20 | unstable: fewer than 200 needless risks behind a mean cost |
| Jev 1.14.0 | 0.76 [0.59, 0.94] | +0.80 [+0.72, +0.89] | 252/746 | 89/753 | 206/252 | +0.05 | unstable: fewer than 200 needless risks behind a mean cost |
| LFM2.5-24B-A2B (off) | 0.37 [0.24, 0.50] | +0.20 [+0.13, +0.29] | 346/701 | 267/765 | 194/346 | +1.36 | valid |
| Mercury Decide | 0.49 [0.36, 0.63] | +0.93 [+0.84, +1.02] | 164/667 | 75/634 | 120/164 | +0.23 | unstable: fewer than 200 needless risks behind a mean cost |
| Open-Jev 27B v1.1 | 0.65 [0.53, 0.78] | -0.05 [-0.12, +0.01] | 470/726 | 315/803 | 272/470 | +0.70 | valid |
| Random | 0.17 [0.02, 0.32] | -0.76 [-0.88, -0.64] | 379/473 | 368/491 | 120/379 | +2.71 | unstable: fewer than 200 missed risks behind a mean cost |
| Safest | -0.01 [-0.05, 0.02] | +3.22 [+3.21, +3.23] | 0/795 | 0/758 | N/A 0/0 | — | N/A: no needless risks to price |
| SubQ Snap Preview | 0.75 [0.61, 0.91] | +0.24 [+0.17, +0.31] | 423/762 | 235/872 | 291/423 | +0.37 | valid |
| Winnow-12B | 0.66 [0.55, 0.77] | +0.38 [+0.30, +0.45] | 370/768 | 174/728 | 259/370 | +0.26 | unstable: fewer than 200 needless risks behind a mean cost |

### League 1, margin 0.02

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Celeris-1 Decision | 0.86 [0.69, 1.02] | +0.88 [+0.80, +0.97] | 204/626 | 89/948 | 160/204 | -0.15 | unstable: fewer than 200 needless risks behind a mean cost |
| Clef | 0.94 [0.81, 1.10] | +0.07 [-0.01, +0.15] | 433/661 | 263/898 | 308/433 | +0.27 | valid |
| Cygnet (Gemma 4 12B) | 0.75 [0.61, 0.88] | +0.76 [+0.69, +0.84] | 229/658 | 107/840 | 174/229 | +0.11 | unstable: fewer than 200 needless risks behind a mean cost |
| Decider Flash v1.2 | 0.57 [0.44, 0.70] | +0.06 [-0.01, +0.14] | 351/597 | 289/794 | 183/351 | +0.74 | valid |
| Decider v1.1 27B | 0.66 [0.53, 0.80] | +0.49 [+0.42, +0.56] | 268/613 | 188/909 | 210/268 | +0.55 | unstable: fewer than 200 needless risks behind a mean cost |
| Decider v1.2 27B | 0.71 [0.60, 0.81] | +0.49 [+0.42, +0.57] | 274/616 | 174/876 | 211/274 | +0.32 | unstable: fewer than 200 needless risks behind a mean cost |
| Fastino GLiDE | 0.87 [0.73, 1.01] | +0.23 [+0.15, +0.31] | 365/628 | 242/958 | 256/365 | +0.52 | valid |
| Fastino GLiDE v1.2 (local) | 0.73 [0.60, 0.88] | +0.54 [+0.45, +0.63] | 243/563 | 157/857 | 190/243 | +0.22 | unstable: fewer than 200 needless risks behind a mean cost |
| GNUbg weak | 1.69 [1.51, 1.89] | -0.56 [-0.65, -0.48] | 490/532 | 348/900 | 359/490 | +0.46 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6 Luna | 0.65 [0.48, 0.84] | +0.87 [+0.79, +0.96] | 185/632 | 89/773 | 145/185 | -0.03 | unstable: fewer than 200 needless risks behind a mean cost |
| Jev 1.13.0 | 0.93 [0.72, 1.16] | +0.80 [+0.72, +0.89] | 217/589 | 85/835 | 159/217 | -0.30 | unstable: fewer than 200 needless risks behind a mean cost |
| Jev 1.14.0 | 0.75 [0.59, 0.91] | +0.76 [+0.67, +0.85] | 234/666 | 107/833 | 188/234 | +0.04 | unstable: fewer than 200 needless risks behind a mean cost |
| LFM2.5-24B-A2B (off) | 0.35 [0.22, 0.47] | +0.18 [+0.10, +0.27] | 309/623 | 304/843 | 166/309 | +1.66 | valid |
| Mercury Decide | 0.51 [0.37, 0.64] | +0.91 [+0.83, +1.00] | 155/607 | 84/694 | 108/155 | +0.21 | unstable: fewer than 200 needless risks behind a mean cost |
| Open-Jev 27B v1.1 | 0.66 [0.52, 0.81] | -0.09 [-0.16, -0.02] | 425/641 | 360/888 | 239/425 | +0.74 | valid |
| Random | 0.15 [0.01, 0.31] | -0.76 [-0.89, -0.64] | 341/426 | 406/538 | 102/341 | +3.33 | unstable: fewer than 200 missed risks behind a mean cost |
| Safest | 0.05 [0.01, 0.08] | +3.22 [+3.20, +3.23] | 0/712 | 0/841 | N/A 0/0 | — | N/A: no needless risks to price |
| SubQ Snap Preview | 0.75 [0.59, 0.90] | +0.19 [+0.12, +0.27] | 383/669 | 275/965 | 256/383 | +0.43 | valid |
| Winnow-12B | 0.66 [0.54, 0.78] | +0.34 [+0.26, +0.42] | 341/687 | 203/809 | 231/341 | +0.29 | valid |

### League 2, margin 0.001

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (off) | 1.49 [1.30, 1.70] | +0.82 [+0.73, +0.93] | 297/635 | 45/779 | 260/297 | +0.24 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Sonnet 5.5 (high) | 1.59 [1.42, 1.78] | +0.93 [+0.85, +1.02] | 299/666 | 35/834 | 281/299 | +0.02 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Sonnet 5.5 (low) | 1.27 [1.11, 1.45] | +1.06 [+0.96, +1.16] | 194/576 | 36/805 | 173/194 | +0.35 | unstable: fewer than 200 needless risks behind a mean cost |
| DeepSeek V4.1 Flash (off) | 1.03 [0.89, 1.19] | +0.79 [+0.72, +0.88] | 235/601 | 62/657 | 187/235 | +0.25 | unstable: fewer than 200 needless risks behind a mean cost |
| DeepSeek V4.1 Flash (on) | 1.59 [1.43, 1.77] | +0.74 [+0.64, +0.85] | 324/623 | 53/857 | 283/324 | +0.44 | unstable: fewer than 200 needless risks behind a mean cost |
| GLM-5.3 (on) | 1.11 [0.93, 1.31] | +0.87 [+0.79, +0.96] | 206/548 | 54/704 | 174/206 | -0.03 | unstable: fewer than 200 needless risks behind a mean cost |
| GNUbg weak | 1.38 [1.23, 1.55] | -0.30 [-0.39, -0.20] | 528/629 | 270/778 | 396/528 | +0.53 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6.1 Sol (high) | 1.74 [1.55, 1.95] | +0.70 [+0.62, +0.80] | 348/614 | 44/771 | 323/348 | -0.10 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemini 3.8 Flash (high) | 1.70 [1.52, 1.92] | +1.14 [+1.06, +1.23] | 259/670 | 19/838 | 237/259 | -0.16 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemini 3.8 Flash (low) | 1.46 [1.28, 1.69] | +1.08 [+0.99, +1.19] | 195/537 | 26/750 | 179/195 | +0.31 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemma 4 31B (off) | 1.21 [1.04, 1.39] | +0.80 [+0.72, +0.89] | 218/518 | 56/712 | 177/218 | +0.43 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemma 4 31B (on) | 1.46 [1.30, 1.66] | +1.14 [+1.05, +1.24] | 206/601 | 25/827 | 190/206 | +0.01 | unstable: fewer than 200 needless risks behind a mean cost |
| LFM2.5-24B-A2B (on) | 0.71 [0.58, 0.85] | +0.27 [+0.19, +0.36] | 283/531 | 170/644 | 172/283 | +1.06 | unstable: fewer than 200 needless risks behind a mean cost |
| Liquid d1-ultra | 1.11 [0.96, 1.26] | +0.53 [+0.44, +0.62] | 287/561 | 97/697 | 231/287 | +0.06 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8 Flash (off) | 0.96 [0.78, 1.14] | +0.58 [+0.50, +0.66] | 297/645 | 102/704 | 209/297 | +0.07 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8-27B (off) | 0.84 [0.67, 1.02] | +0.96 [+0.88, +1.06] | 169/576 | 49/592 | 138/169 | +0.15 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8-27B (on) | 1.01 [0.82, 1.23] | +0.74 [+0.66, +0.84] | 243/599 | 71/676 | 196/243 | +0.31 | unstable: fewer than 200 needless risks behind a mean cost |
| Random (computed) | 0.39 [0.37, 0.41] | -0.76 [-0.77, -0.75] | 8421/10130 | 9024/12625 | 2569/8421 | +2.37 | valid |
| Safest (computed) | 0.05 [0.04, 0.06] | +3.92 [+3.92, +3.93] | 0/10130 | 0/12625 | N/A 0/0 | — | N/A: no needless risks to price |

### League 2, margin 0.02

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (off) | 1.51 [1.34, 1.71] | +0.72 [+0.64, +0.82] | 282/549 | 60/865 | 240/282 | +0.23 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Sonnet 5.5 (high) | 1.57 [1.39, 1.77] | +0.84 [+0.75, +0.93] | 287/599 | 47/901 | 268/287 | -0.11 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Sonnet 5.5 (low) | 1.27 [1.11, 1.44] | +0.97 [+0.88, +1.06] | 182/493 | 48/888 | 161/182 | +0.22 | unstable: fewer than 200 needless risks behind a mean cost |
| DeepSeek V4.1 Flash (off) | 1.01 [0.87, 1.14] | +0.74 [+0.66, +0.83] | 221/544 | 76/714 | 171/221 | +0.17 | unstable: fewer than 200 needless risks behind a mean cost |
| DeepSeek V4.1 Flash (on) | 1.59 [1.44, 1.76] | +0.61 [+0.52, +0.70] | 301/524 | 76/956 | 262/301 | +0.34 | unstable: fewer than 200 needless risks behind a mean cost |
| GLM-5.3 (on) | 1.12 [0.93, 1.32] | +0.81 [+0.73, +0.89] | 195/487 | 65/765 | 165/195 | -0.04 | unstable: fewer than 200 needless risks behind a mean cost |
| GNUbg weak | 1.43 [1.28, 1.61] | -0.43 [-0.54, -0.32] | 456/522 | 342/885 | 330/456 | +0.39 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6.1 Sol (high) | 1.73 [1.58, 1.89] | +0.55 [+0.48, +0.64] | 325/523 | 67/862 | 290/325 | -0.27 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Gemini 3.8 Flash (high) | 1.62 [1.46, 1.80] | +0.97 [+0.89, +1.05] | 243/558 | 35/950 | 219/243 | -0.40 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemini 3.8 Flash (low) | 1.49 [1.31, 1.69] | +0.99 [+0.90, +1.09] | 187/462 | 34/825 | 169/187 | +0.26 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemma 4 31B (off) | 1.26 [1.07, 1.45] | +0.73 [+0.66, +0.82] | 207/452 | 67/778 | 171/207 | +0.38 | unstable: fewer than 200 needless risks behind a mean cost |
| Gemma 4 31B (on) | 1.50 [1.34, 1.68] | +1.06 [+0.97, +1.16] | 200/530 | 31/898 | 182/200 | +0.06 | unstable: fewer than 200 needless risks behind a mean cost |
| LFM2.5-24B-A2B (on) | 0.73 [0.59, 0.87] | +0.23 [+0.15, +0.32] | 260/471 | 193/704 | 150/260 | +1.12 | unstable: fewer than 200 needless risks behind a mean cost |
| Liquid d1-ultra | 1.08 [0.92, 1.25] | +0.46 [+0.38, +0.54] | 264/497 | 120/761 | 201/264 | +0.08 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8 Flash (off) | 0.93 [0.77, 1.09] | +0.53 [+0.45, +0.61] | 275/579 | 124/770 | 191/275 | +0.03 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8-27B (off) | 0.74 [0.56, 0.92] | +0.91 [+0.83, +1.00] | 153/517 | 65/651 | 123/153 | +0.04 | unstable: fewer than 200 needless risks behind a mean cost |
| Qwen3.8-27B (on) | 0.94 [0.74, 1.12] | +0.68 [+0.59, +0.77] | 221/530 | 93/745 | 173/221 | +0.26 | unstable: fewer than 200 needless risks behind a mean cost |
| Random (computed) | 0.39 [0.37, 0.41] | -0.79 [-0.80, -0.77] | 7395/8837 | 10050/13918 | 2102/7395 | +2.59 | valid |
| Safest (computed) | 0.11 [0.10, 0.12] | +3.92 [+3.91, +3.92] | 0/8837 | 0/13918 | N/A 0/0 | — | N/A: no needless risks to price |

### League 3, margin 0.001

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (on) | 1.63 [1.47, 1.85] | +0.70 [+0.58, +0.84] | 210/385 | 34/537 | 188/210 | +0.32 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Claude Opus 5.5 (off) | 1.43 [1.19, 1.69] | +0.89 [+0.77, +1.03] | 191/445 | 27/509 | 172/191 | +0.30 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Opus 5.5 (on) | 1.80 [1.61, 2.03] | +0.98 [+0.86, +1.12] | 200/428 | 17/587 | 178/200 | +0.00 | unstable: fewer than 200 needless risks behind a mean cost |
| GNUbg weak | 1.36 [1.16, 1.55] | -0.30 [-0.39, -0.22] | 406/485 | 212/601 | 289/406 | +0.65 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6 Astra (off) | 1.82 [1.61, 2.10] | +0.71 [+0.60, +0.85] | 225/387 | 26/498 | 212/225 | -0.24 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| GPT-6 Astra (on) | 1.80 [1.61, 2.06] | +0.72 [+0.62, +0.86] | 222/389 | 27/529 | 212/222 | +0.08 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| GPT-6.1 Sol (low) | 1.77 [1.58, 1.97] | +0.76 [+0.65, +0.90] | 197/359 | 28/569 | 180/197 | +0.02 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Gemini 4 Argon (off) | 1.36 [1.16, 1.59] | +0.63 [+0.54, +0.72] | 212/407 | 51/543 | 190/212 | +0.20 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Gemini 4 Argon (on) | 1.97 [1.74, 2.30] | +0.92 [+0.79, +1.10] | 211/402 | 14/511 | 196/211 | -0.39 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Grok 4.7 (off) | 1.33 [1.14, 1.52] | +0.71 [+0.61, +0.82] | 175/364 | 40/477 | 155/175 | +0.45 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Grok 4.7 (on) | 1.37 [1.16, 1.63] | +0.73 [+0.63, +0.85] | 186/387 | 33/430 | 170/186 | -0.14 | unstable: fewer than 200 needless risks behind a mean cost |
| Random (computed) | 0.40 [0.37, 0.42] | -0.73 [-0.75, -0.72] | 3660/4438 | 4076/5791 | 1106/3660 | +2.51 | valid |
| Safest (computed) | 0.07 [0.05, 0.08] | +3.72 [+3.71, +3.73] | 0/4438 | 0/5791 | N/A 0/0 | — | N/A: no needless risks to price |

### League 3, margin 0.02

| Setup | d′ [95%] | c [95%] | taken/Risk pays | needless/Safety pays | aim | c* | c* status |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 (on) | 1.62 [1.45, 1.83] | +0.59 [+0.47, +0.73] | 197/336 | 47/586 | 174/197 | +0.20 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Claude Opus 5.5 (off) | 1.42 [1.20, 1.69] | +0.80 [+0.68, +0.95] | 181/389 | 37/565 | 155/181 | +0.22 | unstable: fewer than 200 needless risks behind a mean cost |
| Claude Opus 5.5 (on) | 1.76 [1.57, 1.99] | +0.86 [+0.72, +0.99] | 191/375 | 26/640 | 169/191 | -0.16 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| GNUbg weak | 1.32 [1.14, 1.52] | -0.38 [-0.48, -0.29] | 358/420 | 260/666 | 249/358 | +0.60 | unstable: fewer than 200 missed risks behind a mean cost |
| GPT-6 Astra (off) | 1.68 [1.50, 1.89] | +0.58 [+0.49, +0.69] | 210/350 | 41/535 | 194/210 | -0.49 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| GPT-6 Astra (on) | 1.81 [1.61, 2.02] | +0.62 [+0.52, +0.73] | 213/347 | 36/571 | 195/213 | -0.07 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| GPT-6.1 Sol (low) | 1.79 [1.57, 2.02] | +0.61 [+0.50, +0.73] | 184/300 | 41/628 | 166/184 | -0.10 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Gemini 4 Argon (off) | 1.34 [1.15, 1.54] | +0.54 [+0.44, +0.63] | 196/356 | 67/594 | 178/196 | +0.06 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Gemini 4 Argon (on) | 1.86 [1.67, 2.06] | +0.73 [+0.62, +0.86] | 198/343 | 27/570 | 188/198 | -0.42 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Grok 4.7 (off) | 1.42 [1.22, 1.63] | +0.61 [+0.51, +0.73] | 166/308 | 49/533 | 140/166 | +0.31 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Grok 4.7 (on) | 1.34 [1.14, 1.58] | +0.65 [+0.55, +0.75] | 175/343 | 44/474 | 153/175 | -0.22 | unstable: fewer than 200 needless and missed risks behind a mean cost |
| Random (computed) | 0.41 [0.38, 0.43] | -0.76 [-0.77, -0.74] | 3216/3867 | 4520/6362 | 902/3216 | +2.63 | valid |
| Safest (computed) | 0.13 [0.11, 0.14] | +3.72 [+3.71, +3.73] | 0/3867 | 0/6362 | N/A 0/0 | — | N/A: no needless risks to price |

### League 1: as played vs re-read — re-read from the model's probabilities, not played
Complete records only; means over 300 block splits, scored on the held-out half; same decisions in both columns. [95%] = block bootstrap of the whole procedure (200 × 30 splits); stability = 5th–95th percentile over splits (not an interval).

| Setup | complete (trade-off) | judgement played → re-read | Δ [95%] · stability 5–95 | PR played → re-read | ΔPR [95%] · stability | most chosen t |
|---|---|---|---|---|---|---|
| Celeris-1 Decision | 2055 (1574) | 58.4 → 58.6 | +0.2 [-1.0, +1.7] · -1.4 to +1.2 | 32.7 → 35.0 | +2.3 [+1.1, +3.6] · +0.8 to +4.4 | 0.30 (92/300) |
| Clef | 1998 (1546) | 58.9 → 60.9 | +2.0 [-0.5, +3.9] · -0.2 to +4.0 | 37.3 → 38.4 | +1.1 [-1.5, +3.7] · -1.3 to +3.7 | 0.80 (263/300) |
| Cygnet (Gemma 4 12B) | 1846 (1375) | 56.0 → 56.1 | +0.1 [-1.5, +2.0] · -1.3 to +1.1 | 36.4 → 38.3 | +1.9 [+0.2, +3.1] · -0.5 to +4.1 | 0.35 (116/300) |
| Decider Flash v1.2 | 1660 (1203) | 49.3 → 52.2 | +2.9 [+0.8, +4.9] · +0.9 to +4.6 | 53.3 → 48.8 | -4.5 [-7.7, -0.4] · -9.7 to +0.8 | 0.90 (131/300) |
| Decider v1.1 27B | 1795 (1317) | 57.1 → 58.1 | +1.0 [-0.4, +2.7] · -1.2 to +2.5 | 35.1 → 36.7 | +1.6 [-0.9, +3.8] · -1.7 to +5.9 | 0.55 (79/300) |
| Decider v1.2 27B | 1721 (1310) | 59.0 → 60.1 | +1.2 [-0.7, +2.9] · -0.5 to +2.8 | 34.8 → 37.1 | +2.2 [+0.4, +4.3] · +0.2 to +4.4 | 0.65 (205/300) |
| Fastino GLiDE | 2060 (1584) | 58.0 → 58.9 | +0.9 [-0.8, +2.4] · -1.0 to +2.5 | 36.5 → 36.0 | -0.5 [-2.3, +2.2] · -2.9 to +3.9 | 0.75 (183/300) |
| Fastino GLiDE v1.2 (local) | 1915 (1419) | 58.6 → 58.6 | -0.0 [-2.0, +2.3] · -1.9 to +1.9 | 35.8 → 38.6 | +2.8 [+0.8, +5.0] · +0.6 to +5.7 | 0.65 (117/300) |
| GPT-6 Luna | 1931 (1405) | 55.9 → 56.3 | +0.5 [-1.4, +1.9] · -0.8 to +1.7 | 40.7 → 43.0 | +2.3 [+0.6, +4.1] · +0.8 to +3.8 | 0.55 (129/300) |
| Jev 1.13.0 | 1849 (1424) | 59.1 → 62.6 | +3.4 [+1.1, +5.7] · +1.5 to +5.1 | 34.0 → 34.0 | -0.0 [-1.4, +2.1] · -1.7 to +1.9 | 0.45 (129/300) |
| Jev 1.14.0 | 1950 (1498) | 57.8 → 61.4 | +3.5 [+1.6, +5.4] · +2.0 to +5.1 | 36.8 → 38.4 | +1.6 [-0.4, +3.3] · -0.2 to +3.3 | 0.45 (216/300) |
| LFM2.5-24B-A2B (off) | 1516 (1084) | 46.6 → 49.9 | +3.3 [+0.7, +6.3] · +1.2 to +5.4 | 50.9 → 42.9 | -8.0 [-13.4, -2.7] · -14.2 to -2.2 | 0.95 (108/300) |
| Mercury Decide | 1814 (1301) | 53.1 → 53.4 | +0.2 [-0.8, +1.4] · -1.1 to +1.2 | 47.3 → 48.2 | +0.9 [-0.5, +2.6] · -0.6 to +2.9 | 0.25 (141/300) |
| Open-Jev 27B v1.1 | 2076 (1529) | 49.1 → 54.0 | +5.0 [+2.6, +6.9] · +3.3 to +6.7 | 64.0 → 55.6 | -8.3 [-11.3, -5.2] · -10.9 to -5.7 | 0.90 (300/300) |
| SubQ Snap Preview | 2157 (1633) | 55.6 → 57.1 | +1.5 [+0.2, +3.4] · +0.3 to +2.7 | 46.2 → 44.6 | -1.6 [-4.3, +0.6] · -4.3 to +0.9 | 0.80 (117/300) |
| Winnow-12B | 1919 (1417) | 55.0 → 57.0 | +2.0 [+0.3, +3.4] · +0.4 to +3.3 | 47.7 → 45.1 | -2.6 [-4.8, -0.0] · -4.6 to -0.6 | 0.70 (136/300) |

Hypothesis (recorded before computing; gains largest for high-ability setups with caution well above c*): ρ = -0.39 [-0.57, -0.15] over 24 setups (200 replicates): not supported; left out: none; per league: {'league-1': {'rho': -0.37941176470588234, 'setups': 16}, 'league-2': {'rho': -0.15569141404872366, 'setups': 8}, 'league-3': {'rho': None, 'setups': 0}}

### 5C minimum bar (judgement ≥ 60, PR ≤ 35), then cheapest
- League 1: no qualifier 186/300, only unpriced qualifiers 26/300, chosen in 88 splits, held-out bar cleared in 0; chosen: Celeris-1 Decision 18 (cleared 0), Decider v1.1 27B 1 (cleared 0), Decider v1.2 27B 3 (cleared 0), Jev 1.13.0 62 (cleared 0), Jev 1.14.0 4 (cleared 0)
- League 2: no qualifier 0/300, only unpriced qualifiers 0/300, chosen in 300 splits, held-out bar cleared in 297; chosen: GLM-5.3 (on) 1 (cleared 1), Liquid d1-ultra 297 (cleared 296), Qwen3.8 Flash (off) 2 (cleared 0)
- League 3: no qualifier 0/300, only unpriced qualifiers 0/300, chosen in 300 splits, held-out bar cleared in 300; chosen: GPT-6.1 Sol (low) 31 (cleared 31), Gemini 4 Argon (off) 269 (cleared 269)
(League 1: in 186/300 splits nobody cleared the bar on training; the chosen setups never cleared it on the held-out half.)

### Safest (item 6)
- Code (`src/players/baseline.rs`): fewest hitting rolls, ties → fewer blots → larger pip lead → earlier shown option; never consults the engine.
- League 1 data: min-hitting-roll play in 2,078/2,078 decisions; engine's best safe play in 1,398/2,078.
- Right-safety PR: **8.86** now = 500 × loss on 758 right-safety decisions ÷ 2,078 scored decisions (a contribution, not a conditional mean; the conditional mean is 24.30 PR). The reviewed **8.89** was 2,119 decisions / 761 right safety: the difference is ladder round 1 — League 1's view now holds Safest v LFM2.5 (off) (match 532) instead of Safest v Liquid d1-ultra (match 191) because the view only keeps current members. Live site already shows 8.86 since the 12:51 deploy.
- Method text now says: League 1 Safest = the played program with its own tie-break; Leagues 2–3 Safest (computed) = engine's best safe play reference, not directly comparable.

### Verification limits
- Summary claims rechecked by the build's finding check (passed); I did not re-verify findings by hand.
- Visual check: hero and Risk table screenshots only; chart PNG/table PNG downloads not clicked through; mobile layout not checked.
- Late entries (BriefPart1) will add unaudited decisions: they show as "not audited" and stay out of 5A/5B/5D until `prob_audit.py` is rerun; League 1/3 roster changes also change these tables before ladder round 2.

## Item 1: smoke tests, Kimi cost projection and gate (Oct 24, 14:20 UTC)

**Outcome: the Kimi gate FAILED. No league match was scheduled and no first-look position was asked. Question for Ümit at the end of this section.**

### Identity and settings verified (B7 fields)

| Field | Liquid d1.1 | Kimi K3.1 Pro (off) | Kimi K3.1 Pro (on) |
|---|---|---|---|
| Request model | `d1.1` | `moonshotai/kimi-k3.1-pro` | same |
| Response-resolved model | `d1.1` (50/50 responses) | `moonshotai/kimi-k3.1-pro`; generation API: `moonshotai/kimi-k3.1-pro-20261023` | same |
| Provider / endpoint | Liquid decisions API, `api.liquid.ai/decisions/v1/systemone` | OpenRouter pinned `provider.order = ["moonshotai/mxfp4"]`, `allow_fallbacks: false` | same |
| Endpoint identity check | — | The endpoints API lists two Moonshot AI endpoints: `moonshotai/mxfp4` (service_tier null, $2/$10) and `moonshotai/highspeed` (service_tier `priority`, $4/$20). Every response had `provider: Moonshot AI` and `service_tier: null`; billed costs match $2/$10 to the cent. So the standard endpoint answered, not Highspeed. | same |
| Explicit setting | none (decision model) | `reasoning_effort: none` | `reasoning_effort: max` |
| Probabilities | per legal option (decision model distribution; all legal plays present, sums to 1) | **none**: `logprobs: true, top_logprobs: 20` were sent and every response returned `logprobs: null`. The endpoint doesn't list logprobs. So it's choice only. | same: choice only |
| Prompt caching | n/a | Implicit (endpoint `supports_implicit_caching: true`). The rules text is the prompt's prefix. **Measured**: 105,216 of 165,193 input tokens cached (64%). | Measured: 72,960 of 117,449 (62%) |
| Run date | 2026-10-24 | 2026-10-24 | 2026-10-24 |
| Price and price date | **Assumption:** $0.02/M input. liquid.ai/pricing has no d1.1 row on 2026-10-24, and $0.02 is its row labelled `d1`. Conservative projections use d1-ultra's $0.042. | $2/M in, $0.20/M cached in, $10/M out (OpenRouter endpoints API, 2026-10-24) | same |
| Official source | `GET api.liquid.ai/decisions/v1/models` lists `d1.1` (release_date 2026-10-19). docs.liquid.ai/lfm/models/d1 calls `d1.1` the "default hosted decision model". There's no blog post yet. Checked 2026-10-24. | openrouter.ai/api/v1/models and `/models/moonshotai/kimi-k3.1-pro/endpoints`, 2026-10-24 | same |

**Change from the reviewed mapping: (off) = `none`, not `low`.** On 2026-10-24, OpenRouter's model metadata for `moonshotai/kimi-k3.1-pro` reads `reasoning: {mandatory: false, default_enabled: true, supported_efforts: [max, high, low, none], default_effort: max}`. On the pinned standard endpoint, `none` was accepted, used 0 reasoning tokens on all 52 decisions (50 smoke + 2 probe), and gave valid answers. This follows League 3's rule ("reasoning off; its lowest setting where it has no off"): Astra and Grok are at `low` only because they reject `none`. Main approved this. (on) = `max` is the model's documented default and matches the reviewed mapping.

**Plain `d1`** still answers as `d1`. It doesn't resolve to d1.1: the two picked the same play on 35 of 50 positions, with a largest probability gap of 0.70. The historical d1 results are untouched.

### Smoke rows (50 positions, `positions/smoke.jsonl`, bg-v2, order seed 1190975713392774006, 600 s limit)

Config `leagues/smoke-brief-1024.json`, answers `smoke/brief-1024.db`, table `smoke/brief-1024.json`. Runner: commit e78a5cf plus the budget change (dirty), committed with this report. Scored with `smoke/score.db` (GNUbg 1.08, 2-ply). Read any difference under about 10 as noise (Part A).

| Setup | Answers / failed / timed out | Invalid | Probabilities | p50 / p90 s | Tokens in / out / reasoning | $ per 1,000 | Error rate [95% CI] | Δ vs Gemini 3.8 Flash (low) today | Δ vs Liquid d1-ultra today |
|---|---|---|---|---|---|---|---|---|---|
| **Liquid d1.1** | 50 / 0 / 0 | 0% | decision model | 0.2 / 0.3 | 3000 / 0 / – | 0.06 | 23.4 [11.9, 36.6] | +15.0 [+4.2, +27.4] | −5.9 [−22.5, +7.9] |
| Liquid d1-ultra (same day) | 50 / 0 / 0 | 0% | decision model | 0.2 / 0.3 | 3000 / 0 / – | 0.13 | 29.3 [15.5, 45.6] | +20.9 [+7.8, +36.7] | reference |
| Liquid d1 (same day) | 50 / 0 / 0 | 0% | decision model | 0.3 / 0.4 | 3000 / 0 / – | 0.06 | 24.7 [13.2, 37.9] | +16.3 [+5.5, +28.8] | −4.6 [−18.7, +6.8] |
| Gemini 3.8 Flash (low) [antigravity], reference | 50 / 0 / 0 | 0% | none (choice only) | 2.0 / 5.3 | 3244 / 292 / 289 | 3.53 (API-eq.) | 8.4 [3.0, 15.8] | reference | −20.9 [−36.7, −7.9] |
| **Kimi K3.1 Pro (off)** (`none`) | 50 / 0 / 0 | 0% | none (choice only) | 3.3 / 4.3 | 3164 / 15 / 0 | 2.69 | 20.3 [8.7, 34.9] | +11.9 [+1.4, +26.1] | −9.0 [−20.1, +0.6] |
| **Kimi K3.1 Pro (on)** (`max`) | 37 / 0 / **13** | 0% | none (choice only) | 154.5 / 491.0 | 3174 / 9810 / 9790 | 100.90 | 3.5 [0.3, 9.2] (n=37; the 13 timeouts are probably the hard ones, so this is biased low) | +1.6 [−2.3, +7.5] (n=37) | −16.5 [−29.6, −6.0] (n=37) |

Failures:
- **Liquid:** 8 requests (d1.1: 4, d1: 4) failed with Liquid's `502 All upstream backends failed` after 4 attempts, and the runner's warm-up probes failed the same way. A rerun 1 hour later answered all of them. No invalid answers.
- **Kimi (on):** 13 of 50 decisions hit the 600 s limit (26%). OpenRouter billed them anyway; see the ledger.

### Kimi hard cap: implementation

- New `src/budget.rs`, wired into `src/http.rs` and `src/players/llm.rs`.
- **Config.** A player config with `budget: {ledger, cap_usd, input_per_mtok, cached_input_per_mtok, output_per_mtok}` (OpenAI-compatible specs only) shares a SQLite ledger with every process that names it. Both Kimi settings use `smoke/kimi-k31-budget.db`, cap $30.
- **Reservation.** Before **every attempt**, retries included, the runner reserves that attempt's worst case: request bytes × input price + `max_tokens` (32,768) × output price, about $0.35. In one transaction, it refuses the call when spent + open reservations + this one would pass $30. The refusal is an error ("BUDGET CAP … stopped before the call"): a league match aborts and resumes later, and `ask` stores a failure. No random play is made.
- **Settlement.**
  - An answered attempt is booked at max(list-price cost, OpenRouter's reported cost). List cost = uncached input × $2 + cached × $0.20 + all completion tokens (reasoning included) × $10, so nothing is counted twice.
  - An error status books $0.
  - No response (timeout, dropped decision, crash) keeps the worst case ("lost").
- **Tests:** `budget::tests`, `http::tests::metered_attempts_reserve_before_sending`; all 59 runner tests pass.

### Spend ledger (Kimi, at list prices)

| | Attempts | Input (cached) | Output (reasoning) | Booked |
|---|---|---|---|---|
| (off), smoke + 2 probe decisions | 52 settled | 165,193 (105,216) | 780 (0) | $0.1488 |
| (on), answered | 37 settled | 117,449 (72,960) | 362,979 (362,239) | $3.7334 |
| (on), no response (13 timeouts + 4 in flight when my shell killed the first run at 13:54:48 UTC; booked by hand as lost) | 17 lost | – | – | $5.9573 (worst case) |
| **Ledger total (conservative)** | | | | **$9.84** |
| OpenRouter actual (`/credits` usage 63.9992 → 71.2627) | | | | **$7.26** (so each timeout was billed about $0.20) |

**OpenRouter credit left: $3.74** ($75.00 total, $71.26 used, 14:08 UTC).

### Projection from measured tokens (each setting's own)

- **Rates:** $2/M input, $0.20/M cached input, $10/M output (2026-10-24).
- **Off: League 3 late entry.**
  - Measured per decision: 3,177 input tokens (2,023 cached), 15 output, 0 reasoning, **$0.00286**.
  - Workload is not fixed. Kimi (off) would play 11 matches, one against each of League 3's 11 current entrants (3 rounds). Finished League 3 matches give 126.6 decisions per player per match (SD 28.2, range 64–187, 110 player-matches). Resampling 11 matches gives 1,392 decisions (p50), 1,547 (p95) and 2,057 at most.
  - About 14% of League 3 decisions have more than 26 plays and are split into groups. That makes a decision cost 1.35–1.53× an ungrouped one (League 3's chat models).
  - **Projected:** $5.78 central (1,392 × 1.45 × $0.00286); $6.77 at p95 (1,547 × 1.53); $15.39 at p95 with no cache hits.
- **On: 200 fixed first-look positions.**
  - Measured: $0.1009 per answered decision (9,790 reasoning tokens); 26% timed out, each billed about $0.20 (up to $0.35 worst case).
  - The frozen 200 render to the same prompt length as the smoke positions (21,342 vs 21,441 characters).
  - **Projected:** $25.28 (actual timeout cost), $33.18 (worst-case timeouts).
- **Combined:**

| | Incurred | Off remaining | On 200 | Total |
|---|---|---|---|---|
| Central | $7.26 | $5.78 | $25.28 | **$38.32** |
| Optimistic (no groups; timeouts free) | $7.26 | $3.98 | $20.18 | **$31.42** |
| Conservative (ledger, p95, worst-case timeouts) | $9.84 | $6.77 | $33.18 | **$49.79** |

### Gate decision

1. **Incurred plus projected exceeds $30 in every scenario.** Under the brief, I stop and ask Ümit. I did not shrink the 200 positions, change the effort, drop the roster or raise the cap.
2. **OpenRouter credit ($3.74 left) can't cover even (off)'s League 3 entry** (about $5.8). No top-up was requested.
3. So **Kimi (off) is not entered in League 3** and **Kimi (on) has not been asked any first-look position.** League 3 stays final, and its table, champions and Cup roster are unchanged.

**Question for Ümit:**
1. With the measured costs, the brief's Kimi work needs about $38 at list prices, against a $30 cap and $3.74 of OpenRouter credit. Options:
   - (a) raise the cap and have Can add credit;
   - (b) run (off)'s League 3 entry only (about $6–7, needs credit) and drop or postpone (on)'s first look;
   - (c) change (on)'s plan, e.g. fewer positions or a longer time limit (timeouts cost money but give no answer);
   - (d) stop Kimi here.

   Nothing runs until you choose.
2. Liquid d1.1's League 1 entry is gated separately; see below.

### Frozen first-look set (prepared, not asked)

`positions/first-look-kimi.jsonl`: 200 positions, sha256 `dbec41a1640043deb23e728c3b48582a70da4d4c1ad1f7fa15c4a5d2b9506a29`.
- **Source:** `positions/new.jsonl` (sha256 `ad06427c…`, as in `freeze.json`).
- **Selection:** 40 per phase, the ids with the smallest sha256(`kimi-k3.1-pro-first-look-2026-10-24:` + id). Rows are byte-identical to the source.
- **Size:** 2–25 legal plays, so no decision is split into groups.
- **Record:** `freeze/first-look-kimi.json` (rule, ids, hashes, frozen 14:00 UTC). These positions are not yet GNUbg-scored. That's a CPU job, to do before any scoring.

### Liquid d1.1 → League 1: not scheduled

- **Smoke gate passed:** model identity verified, valid answers, full option probabilities, cost $0.003 per 50.
- **Roster check:** I can't verify against the original brief's 19 names, because the original Discord messages aren't available to me (Main doesn't have them either). The current League 1 roster in `v3.db` has 19 entrants: Celeris-1 Decision, Clef, Cygnet (Gemma 4 12B), Decider Flash v1.2, Decider v1.1 27B, Decider v1.2 27B, Fastino GLiDE, Fastino GLiDE v1.2 (local), GNUbg weak, GPT-6 Luna, Jev 1.13.0, Jev 1.14.0, LFM2.5-24B-A2B (off), Mercury Decide, Open-Jev 27B v1.1, Random, Safest, SubQ Snap Preview, Winnow-12B.
  - **Discrepancy:** if the original brief was written before ladder round 1 (Oct 23, 20:49 UTC), its 19 included **Liquid d1-ultra** (now in League 2) and not **LFM2.5-24B-A2B (off)** (now in League 1).
  - **Please confirm the opponent list.** Not scheduled until then.
- **Local servers:** 9 of the 19 opponents need local model servers that are **not running** now: Clef, Cygnet, Decider Flash v1.2, Decider v1.1 27B, Decider v1.2 27B, Fastino GLiDE v1.2 (local), LFM2.5-24B-A2B (off), Open-Jev 27B v1.1, Winnow-12B. All their ports refused connections at 14:15 UTC. Those matches are blocked until Can brings the servers up. I didn't start any.
- **Interaction with ladder round 2:** League 1/3 late entries change the rosters and tables that ladder round 2 (pending) would use. Nothing changed, because nothing was entered.

### Changes during the leagues

- **2026-10-24 18:39 UTC: Kimi K3.1 Pro (off) late entry in League 3** (Can's approval, via Main). It is the smoke-tested entry exactly (`leagues/smoke-brief-1024.json`, effort `none`, Moonshot standard endpoint pinned, `$30` cap in `smoke/kimi-k31-budget.db`). `league-add` gave 11 fixtures, logged in `freeze/league3-additions.json`. League 3's runner was restarted at 18:40 on a binary with the budget ledger (`target/parta` build of 6fbf445, installed as `target/release/jevgammon`; the earlier binary had no cap code). Every Kimi attempt in the ledger since then comes from that process. Round 2's running match resumed from its stored turn. League 3 is **provisional** until these matches finish. Kimi (on)'s first look is still not run (it needs Ümit).

## Item 7: A2 on shared positions, status only (no paid calls)

- **Build:** done. The runner has the A2 prompt versions `bg-v2-notation` (plays as notation only) and `bg-v2-history` (`src/players/prompt.rs`, `prompts/instructions-notation.txt`).
- **Freeze:** the shared position files are hashed in `freeze.json` (`positions/new.jsonl` etc.). No A2-specific freeze or matched-position mapping exists. The shared-positions run is still waiting for Ümit (`mailbox/Shared positions - review and estimates 2026-10-24.md`).
- **Results:** none. Every `answers` table in the repo's databases (smoke/*.db; `v3.db` not counted) holds `bg-v2` answers only, and no `bg-v2-notation`/`bg-v2-history` answers exist. The v12 site delivery lists A2 as "Analysis pending (ablation answers)".
- **So A2 has not been run.** It needs the shared positions first. Until a valid paired result exists, "the prompt mattered more than the model" stays an **Earlier version (v1)** finding.
