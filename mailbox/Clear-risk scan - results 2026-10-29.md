# Clear-risk scan: step 4 (3-ply stability) and steps 5–6 (2026-10-29)

Offline. No model calls, and no change to the site or to Ümit's thread. GNUbg 1.08.003 ran on CPU only (`nice -n 19`,
8 single-threaded processes, no GPU). Data: `v3.db` read-only and the site's GNUbg shards, as in the steps 0–3 report.
Step 4 follows the amendment "Step 4 replaced (Can, 2026-10-29)" in `mailbox/Clear-risk scan - method 2026-10-29.md`,
commit **`619eb3c1883a31df6b27842136fea04f1bd8e9a6`** (2026-10-29T18:10:35Z), pushed before any 3-ply value was
computed. No rollouts were run for the leagues.

**3-ply settings.** `{"cubeful": 0, "plies": 3, "deterministic": 1, "prune": 1, "noise": 0.0}`, which is the scorer's
`PLY2` with `plies` set to 3. Money cube `gnubg.cubeinfo(1, 0, 1, 0)`, via `engine.equity`: the position after the
play, opponent on roll, equity for the mover. `set threads 1` per process. As a check, the same run recomputed 2-ply
for every play: it matches the stored values exactly (max difference 0).

**Keep rule.** (a) \|gap\| ≥ 0.04 at 2-ply and at 3-ply; (b) same direction; (c) \|gap3 − gap2\| ≤ 0.02.
Otherwise the decision is unstable and dropped. Unstable decisions are counted by the first failing condition, in the
order (b), (a), (c).

## Bray at 3-ply: kept as Risk wins

| play | 2-ply | 3-ply | hitting rolls |
|---|---:|---:|---:|
| 22/18 22/20 (best unsafe) | −0.3922 | −0.3900 | 36 |
| 8/4 8/6 (best safe) | −0.4973 | −0.4847 | 0 |

gap2 = +0.1051, gap3 = **+0.0947**, \|gap3 − gap2\| = 0.0104 ≤ 0.02. All three conditions pass, so it is **kept as
Risk wins**. At 3-ply the same two plays are still the best in their bins. 3-ply cost about 0.14 s per play.

## 3-ply pass on the 32,840 flagged decisions

- **Time:** 733 s wall (18:11:11–18:23:24 UTC) and 5,005 CPU-s, on 8 processes.
- **Plays evaluated:** 61,508 distinct (position, dice, play), out of the 65,680 needed. The other 4,172 reused an
  earlier result.

| league | group | flagged | kept | unstable: direction flips | unstable: \|gap3\| < 0.04 | unstable: \|gap3 − gap2\| > 0.02 |
|---|---|---:|---:|---:|---:|---:|
| 1 | Risk wins | 4,498 | 3,353 | 5 | 167 | 973 |
| 2 | Risk wins | 4,304 | 3,337 | 2 | 141 | 824 |
| 3 | Risk wins | 1,645 | 1,307 | 1 | 65 | 272 |
| all | **Risk wins** | 10,447 | **7,997** | **8** | **373** | **2,069** |
| 1 | Safety wins | 8,186 | 6,223 | 3 | 176 | 1,784 |
| 2 | Safety wins | 9,960 | 7,704 | 4 | 187 | 2,065 |
| 3 | Safety wins | 4,247 | 3,275 | 2 | 65 | 905 |
| all | **Safety wins** | 22,393 | **17,202** | **9** | **428** | **4,754** |
| all | **both** | 32,840 | **25,199** | **17** | **801** | **6,823** |

- **Kept: 25,199 of 32,840 (76.7%).** Most of the drops fail (c), the depth shift: 6,823.
  Only 17 decisions flip direction.
- **Known weak spots (counts only).** These use the repo's classifier, `tools/v3/classify.py`, on the position before
  the play, checking both sides.
  - **Back game** (its `back_game` rule): 924 kept, 461 unstable. That is 33.3% unstable, against 23.3% overall.
  - **Prime-vs-prime** (both sides have `longest_prime` ≥ 4): 2,144 kept, 787 unstable (26.9%).
  - **Containment:** the repo has no classifier for it, so nothing is claimed.

## Steps 5–6: per setup, kept positions only

**Definitions.** Each setup's own kept decisions, split by group. The chosen play is put in a bin by its hitting rolls,
the number stored in `STATE/plays`.
- **Missed risks:** Risk-wins decisions where the setup played safe (0 hitting rolls).
- **Needless risks:** Safety-wins decisions where it played unsafe (12 or more).
- **In-between:** decisions where the chosen play leaves 1–11 hitting rolls, given for each group separately.
- **Bias** = missed − needless, in percentage points. Positive means too cautious.

Every share is shown with its count. A group under 30 positions would be marked "few positions"; no group is.

**Reference rows** use all of the league's kept decisions:
- **Safest program:** always plays a 0-roll play, which every flagged decision has. Missed 100%, needless 0%.
- **Random legal play:** the expected shares, i.e. each decision's fraction of legal plays in each bin, summed.

**Setups met different positions.** The rows are not paired, so they compare only loosely.

**Thread number** ("took a risk when risk paid"). This is the site's published **Risks found**: the field
`risk.main.found` (`share`, shown with `n`/`den`) at margin 0.001 (main). It comes from
`~/.local/state/bg-site/analysis/backgammon/results/a12573f2/data/v3/league-N/<setup>.json`, the deployed results
`a12573f2`. It is computed on all of a setup's Risk pays decisions at margin 0.001, a different and much larger set
than the kept clear-risk positions here. Note that the two do not measure the same thing: risks found counts a right
risk, while missed risks here counts playing safe.

### League 1

| setup | Risk wins kept | missed risks (played safe) | in-between (Risk wins) | Safety wins kept | needless risks (played unsafe) | in-between (Safety wins) | bias = missed − needless | thread: risks found |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Celeris-1 Decision | 168 | 81.5% (137/168) | 13.1% (22/168) | 408 | 1.0% (4/408) | 4.2% (17/408) | +80.6 pp | 23.9% (163/683) |
| Cygnet (Gemma 4 12B) | 240 | 75.8% (182/240) | 13.8% (33/240) | 297 | 3.4% (10/297) | 6.4% (19/297) | +72.5 pp | 27.3% (205/750) |
| Decider Flash v1.2 | 160 | 51.9% (83/160) | 15.6% (25/160) | 339 | 13.9% (47/339) | 10.0% (34/339) | +38.0 pp | 31.3% (223/712) |
| Decider v1.1 27B | 175 | 67.4% (118/175) | 16.6% (29/175) | 369 | 7.3% (27/369) | 10.6% (39/369) | +60.1 pp | 33.1% (233/703) |
| Decider v1.2 27B | 145 | 66.9% (97/145) | 16.6% (24/145) | 361 | 4.4% (16/361) | 10.8% (39/361) | +62.5 pp | 33.4% (244/731) |
| DeepSeek V4.1 Flash (off) | 194 | 62.9% (122/194) | 26.3% (51/194) | 299 | 1.3% (4/299) | 10.4% (31/299) | +61.5 pp | 29.1% (192/659) |
| Fastino GLiDE v1.2 (local) | 139 | 63.3% (88/139) | 17.3% (24/139) | 417 | 6.5% (27/417) | 7.0% (29/417) | +56.8 pp | 33.0% (219/664) |
| GNUbg weak | 104 | 3.8% (4/104) | 16.3% (17/104) | 312 | 15.1% (47/312) | 24.0% (75/312) | -11.2 pp | 66.6% (410/616) |
| GPT-6 Luna | 197 | 80.2% (158/197) | 14.2% (28/197) | 330 | 2.1% (7/330) | 8.5% (28/330) | +78.1 pp | 21.6% (160/740) |
| Jev 1.13.0 | 185 | 77.3% (143/185) | 13.5% (25/185) | 354 | 0.8% (3/354) | 4.5% (16/354) | +76.4 pp | 27.0% (190/705) |
| LFM2.5-24B-A2B (off) | 178 | 64.6% (115/178) | 9.0% (16/178) | 278 | 10.4% (29/278) | 13.3% (37/278) | +54.2 pp | 28.8% (206/715) |
| LFM2.5-24B-A2B (on) | 185 | 55.7% (103/185) | 13.5% (25/185) | 356 | 12.1% (43/356) | 9.3% (33/356) | +43.6 pp | 31.5% (248/788) |
| Mercury Decide | 217 | 77.4% (168/217) | 16.1% (35/217) | 307 | 1.3% (4/307) | 10.1% (31/307) | +76.1 pp | 18.7% (129/690) |
| Open-Jev 27B v1.1 | 137 | 50.4% (69/137) | 16.8% (23/137) | 306 | 20.3% (62/306) | 11.4% (35/306) | +30.1 pp | 37.3% (264/708) |
| Qwen3.8-27B (off) | 231 | 74.9% (173/231) | 20.8% (48/231) | 331 | 1.8% (6/331) | 4.8% (16/331) | +73.1 pp | 23.5% (178/756) |
| Random | 80 | 23.8% (19/80) | 17.5% (14/80) | 131 | 65.6% (86/131) | 12.2% (16/131) | -41.9 pp | 24.8% (112/452) |
| Safest | 233 | 100.0% (233/233) | 0.0% (0/233) | 329 | 0.0% (0/329) | 0.0% (0/329) | +100.0 pp | 0.0% (0/785) |
| SubQ Snap Preview | 180 | 52.8% (95/180) | 25.6% (46/180) | 388 | 7.2% (28/388) | 12.6% (49/388) | +45.6 pp | 37.9% (297/783) |
| Winnow-12B | 205 | 61.5% (126/205) | 21.0% (43/205) | 311 | 7.4% (23/311) | 8.7% (27/311) | +54.1 pp | 33.7% (263/780) |
| *Safest program (reference)* | 3353 | 100.0% (3353/3353) | 0.0% (0/3353) | 6223 | 0.0% (0/6223) | 0.0% (0/6223) | +100.0 pp | |
| *Random legal play (expected)* | 3353 | 16.3% (547.1/3353) | 11.5% (384.9/3353) | 6223 | 59.4% (3694.0/6223) | 17.2% (1068.4/6223) | -43.0 pp | |

### League 2

| setup | Risk wins kept | missed risks (played safe) | in-between (Risk wins) | Safety wins kept | needless risks (played unsafe) | in-between (Safety wins) | bias = missed − needless | thread: risks found |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (off) | 165 | 44.2% (73/165) | 31.5% (52/165) | 385 | 2.1% (8/385) | 5.7% (22/385) | +42.2 pp | 41.0% (270/658) |
| Claude Sonnet 5.5 (high) | 194 | 53.1% (103/194) | 26.8% (52/194) | 428 | 0.5% (2/428) | 7.2% (31/428) | +52.6 pp | 41.8% (308/737) |
| Claude Sonnet 5.5 (low) | 170 | 61.8% (105/170) | 27.1% (46/170) | 466 | 0.6% (3/466) | 3.2% (15/466) | +61.1 pp | 30.9% (204/661) |
| Clef | 182 | 54.9% (100/182) | 16.5% (30/182) | 340 | 10.6% (36/340) | 14.1% (48/340) | +44.4 pp | 39.5% (263/666) |
| DeepSeek V4.1 Flash (on) | 187 | 48.1% (90/187) | 25.1% (47/187) | 472 | 1.9% (9/472) | 9.5% (45/472) | +46.2 pp | 45.0% (338/751) |
| DeepSeek V4.1 Flash 1017 (off) | 194 | 72.2% (140/194) | 19.1% (37/194) | 395 | 0.8% (3/395) | 11.4% (45/395) | +71.4 pp | 25.4% (181/713) |
| DeepSeek V4.1 Flash 1017 (on) | 185 | 49.7% (92/185) | 30.8% (57/185) | 476 | 2.1% (10/476) | 9.7% (46/476) | +47.6 pp | 42.5% (321/755) |
| Fastino GLiDE | 156 | 50.6% (79/156) | 21.8% (34/156) | 410 | 4.4% (18/410) | 11.2% (46/410) | +46.3 pp | 36.9% (249/675) |
| GLM-5.3 (on) | 193 | 73.6% (142/193) | 19.7% (38/193) | 365 | 0.3% (1/365) | 9.0% (33/365) | +73.3 pp | 30.7% (205/668) |
| GNUbg weak | 121 | 7.4% (9/121) | 20.7% (25/121) | 409 | 21.5% (88/409) | 26.4% (108/409) | -14.1 pp | 62.7% (483/770) |
| Gemini 3.8 Flash (high) | 170 | 53.5% (91/170) | 27.1% (46/170) | 454 | 0.2% (1/454) | 4.0% (18/454) | +53.3 pp | 36.1% (264/731) |
| Gemini 3.8 Flash (low) | 151 | 57.6% (87/151) | 19.9% (30/151) | 421 | 1.4% (6/421) | 2.6% (11/421) | +56.2 pp | 33.8% (214/633) |
| Gemma 4 31B (off) | 133 | 60.9% (81/133) | 22.6% (30/133) | 371 | 1.6% (6/371) | 3.2% (12/371) | +59.3 pp | 33.2% (194/584) |
| Gemma 4 31B (on) | 190 | 57.4% (109/190) | 21.6% (41/190) | 435 | 0.0% (0/435) | 3.9% (17/435) | +57.4 pp | 31.9% (223/700) |
| Grok 4.7 (off) | 182 | 46.2% (84/182) | 34.6% (63/182) | 414 | 0.0% (0/414) | 9.2% (38/414) | +46.2 pp | 42.3% (295/697) |
| Jev 1.14.0 | 187 | 74.3% (139/187) | 17.1% (32/187) | 347 | 2.9% (10/347) | 7.2% (25/347) | +71.4 pp | 29.1% (184/632) |
| Liquid d1-ultra | 171 | 49.1% (84/171) | 29.2% (50/171) | 414 | 4.3% (18/414) | 10.6% (44/414) | +44.8 pp | 42.0% (289/688) |
| Qwen3.8 Flash (off) | 218 | 55.0% (120/218) | 25.2% (55/218) | 334 | 3.3% (11/334) | 13.8% (46/334) | +51.8 pp | 34.4% (243/706) |
| Qwen3.8-27B (on) | 188 | 62.2% (117/188) | 21.8% (41/188) | 368 | 3.3% (12/368) | 5.2% (19/368) | +59.0 pp | 33.8% (242/715) |
| *Safest program (reference)* | 3337 | 100.0% (3337/3337) | 0.0% (0/3337) | 7704 | 0.0% (0/7704) | 0.0% (0/7704) | +100.0 pp | |
| *Random legal play (expected)* | 3337 | 16.9% (563.3/3337) | 11.3% (376.8/3337) | 7704 | 57.2% (4408.4/7704) | 18.2% (1403.6/7704) | -40.3 pp | |

### League 3

| setup | Risk wins kept | missed risks (played safe) | in-between (Risk wins) | Safety wins kept | needless risks (played unsafe) | in-between (Safety wins) | bias = missed − needless | thread: risks found |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Fable 5.1 (on) | 102 | 35.3% (36/102) | 32.4% (33/102) | 295 | 2.4% (7/295) | 8.1% (24/295) | +32.9 pp | 50.7% (215/424) |
| Claude Opus 5.5 (off) | 119 | 47.1% (56/119) | 26.1% (31/119) | 289 | 1.7% (5/289) | 8.3% (24/289) | +45.3 pp | 40.1% (187/466) |
| Claude Opus 5.5 (on) | 117 | 48.7% (57/117) | 29.9% (35/117) | 260 | 1.5% (4/260) | 5.4% (14/260) | +47.2 pp | 43.4% (199/459) |
| GNUbg weak | 111 | 10.8% (12/111) | 13.5% (15/111) | 245 | 14.7% (36/245) | 22.9% (56/245) | -3.9 pp | 58.8% (288/490) |
| GPT-6 Astra (off) | 105 | 39.0% (41/105) | 30.5% (32/105) | 261 | 1.1% (3/261) | 11.1% (29/261) | +37.9 pp | 57.2% (226/395) |
| GPT-6 Astra (on) | 117 | 35.0% (41/117) | 38.5% (45/117) | 280 | 0.7% (2/280) | 8.9% (25/280) | +34.3 pp | 54.9% (245/446) |
| GPT-6.1 Sol (high) | 88 | 31.8% (28/88) | 27.3% (24/88) | 334 | 1.8% (6/334) | 10.8% (36/334) | +30.0 pp | 50.6% (212/419) |
| GPT-6.1 Sol (low) | 108 | 32.4% (35/108) | 32.4% (35/108) | 302 | 1.0% (3/302) | 10.3% (31/302) | +31.4 pp | 51.7% (198/383) |
| Gemini 4 Argon (off) | 115 | 54.8% (63/115) | 20.9% (24/115) | 297 | 2.4% (7/297) | 6.4% (19/297) | +52.4 pp | 47.8% (209/437) |
| Gemini 4 Argon (on) | 101 | 42.6% (43/101) | 20.8% (21/101) | 237 | 0.4% (1/237) | 7.2% (17/237) | +42.2 pp | 50.8% (224/441) |
| Grok 4.7 (on) | 139 | 52.5% (73/139) | 26.6% (37/139) | 250 | 1.6% (4/250) | 9.6% (24/250) | +50.9 pp | 44.0% (190/432) |
| Kimi K3.1 Pro (off) | 85 | 45.9% (39/85) | 25.9% (22/85) | 225 | 2.2% (5/225) | 10.2% (23/225) | +43.7 pp | 42.4% (153/361) |
| *Safest program (reference)* | 1307 | 100.0% (1307/1307) | 0.0% (0/1307) | 3275 | 0.0% (0/3275) | 0.0% (0/3275) | +100.0 pp | |
| *Random legal play (expected)* | 1307 | 18.9% (247.3/1307) | 10.5% (137.4/1307) | 3275 | 54.6% (1789.7/3275) | 18.6% (609.9/3275) | -35.7 pp | |

The CSV of this table: `mailbox/Clear-risk scan - results 2026-10-29.csv`.

**"Maybe we will have sufficient positions?"** Yes. All **50 of 50** setups have at least 30 kept positions in each
group. Risk wins ranges from 80 kept positions (Random, League 1) to 240. Safety wins ranges from 131 to 476.

## 10 kept positions per group for hand checking

Drawn at random with seed 20261029 from the kept decisions of all leagues, ordered by turn id.
- **Position ID:** GNUbg position ID with the mover on roll.
- **Board:** shown from the mover's side (mover moves 24→1).
- **Equities:** cubeless money for the mover, after the play.
- **Hitting rolls:** checked again with `describe_with_shots`; all match.
- **Played:** the setup's chosen play, with its hitting rolls.

| # | group | league · setup (played) | position ID (mover on roll) | dice | best safe: 2-ply / 3-ply (hitting rolls) | best unsafe: 2-ply / 3-ply (hitting rolls) | gap 2-ply / 3-ply | board (mover's numbering, 24→1) |
|---|---|---|---|---|---|---|---|---|
| 1 | Risk wins | L1 · Fastino GLiDE v1.2 (local) (6/5 6/3, 0) | `X+cBABhn2zAABg` | 13 | 6/5 6/3: +0.3295 / +0.3308 (0) | 21/18 18/17: +0.6695 / +0.6570 (12) | +0.3400 / +0.3262 | mover 1:3 3:2 4:2 5:2 6:2 10:2 21:2; bar 0, off 0 / opponent 2:2 20:4 22:3 23:1 24:5; bar 0, off 0 |
| 2 | Risk wins | L3 · Gemini 4 Argon (on) (bar/22 22/17, 0) | `/tkDAADb3QEgIA` | 53 | bar/22 22/17: -0.9994 / -0.9994 (0) | bar/22 18/13: -0.8154 / -0.8020 (20) | +0.1841 / +0.1974 | mover 2:2 3:2 4:3 5:3 6:3 18:1; bar 1, off 0 / opponent 20:4 21:2 23:8; bar 0, off 1 |
| 3 | Risk wins | L1 · Decider v1.1 27B (10/5 4/1, 0) | `tvWAARjHbYjBAA` | 53 | 10/5 4/1: -0.0414 / -0.0581 (0) | 13/8 8/5: +0.0159 / +0.0190 (17) | +0.0573 / +0.0771 | mover 1:3 4:3 5:2 6:2 10:1 13:2 18:2; bar 0, off 0 / opponent 2:2 12:2 19:4 20:1 21:2 22:2 23:2; bar 0, off 0 |
| 4 | Risk wins | L2 · Gemini 3.8 Flash (low) (13/7 7/2, 0) | `NvuAAQzYzsEBMA` | 65 | 13/7 7/2: -0.1353 / -0.1370 (0) | 24/18 18/13: -0.0854 / -0.0942 (34) | +0.0499 / +0.0428 | mover 4:2 5:2 6:3 8:3 13:3 24:2; bar 0, off 0 / opponent 3:2 12:2 19:5 20:2 22:2 23:2; bar 0, off 0 |
| 5 | Risk wins | L2 · Gemma 4 31B (off) (13/11 24/20*, 27) | `jrbBwQBszeABMA` | 24 | 8/6 8/4: -0.1443 / -0.1650 (0) | 5/3 24/20*: +0.2449 / +0.2170 (21) | +0.3892 / +0.3820 | mover 3:2 4:2 5:1 6:2 8:2 13:4 24:2; bar 0, off 0 / opponent 7:2 12:3 17:2 18:2 19:2 20:1 23:3; bar 0, off 0 |
| 6 | Risk wins | L2 · Gemma 4 31B (on) (4/3 8/3, 0) | `yDvGADTsmYMBAw` | 15 | 4/3 8/3: +0.3084 / +0.2621 (0) | 8/7 7/2*: +0.3960 / +0.3662 (14) | +0.0876 / +0.1040 | mover 3:2 4:4 6:2 8:3 13:2 20:2; bar 0, off 0 / opponent 1:2 2:1 12:2 15:2 18:3 19:4 21:1; bar 0, off 0 |
| 7 | Risk wins | L3 · GPT-6 Astra (on) (20/14 16/11, 0) | `4NcDAFZs24ERAg` | 65 | 20/14 14/9: +1.1209 / +1.1037 (0) | 7/1* 13/8: +1.2908 / +1.2870 (12) | +0.1699 / +0.1833 | mover 3:2 4:2 5:2 6:2 7:3 13:2 16:1 20:1; bar 0, off 0 / opponent 1:1 2:2 17:4 18:1 19:6; bar 1, off 0 |
| 8 | Risk wins | L2 · Qwen3.8 Flash (off) (11/5 5/2, 0) | `mOeGAQzOPMgBMA` | 63 | 11/5 5/2: -0.5371 / -0.5406 (0) | 24/18 18/15: -0.2911 / -0.2889 (32) | +0.2460 / +0.2517 | mover 2:3 4:2 6:4 11:1 13:3 24:2; bar 0, off 0 / opponent 3:2 12:2 16:2 17:3 19:4 21:2; bar 0, off 0 |
| 9 | Risk wins | L1 · Safest (13/7* 7/2, 0) | `frsBQCB+3gABMA` | 65 | 13/7* 7/2: -0.3543 / -0.3320 (0) | 13/7* 24/19: -0.2012 / -0.1965 (21) | +0.1531 / +0.1355 | mover 2:6 4:4 5:2 13:1 24:2; bar 0, off 0 / opponent 1:1 7:1 20:2 21:3 22:2 23:6; bar 0, off 0 |
| 10 | Risk wins | L1 · LFM2.5-24B-A2B (on) (24/22 9/5, 36) | `/timAADPBQHgMQ` | 24 | 4/2 9/5: -1.1159 / -1.0959 (0) | 21/17 17/15*: -0.9561 / -0.9536 (15) | +0.1598 / +0.1423 | mover 1:4 3:3 4:1 9:1 21:4 24:2; bar 0, off 0 / opponent 15:1 16:1 18:2 19:2 20:2 23:7; bar 0, off 0 |
| 11 | Safety wins | L2 · Grok 4.7 (off) (9/7 7/3, 0) | `e7sBABjc3VkAAA` | 24 | 3/1 9/5: +0.8200 / +0.8204 (0) | 8/6 9/5: +0.4619 / +0.4643 (13) | -0.3581 / -0.3561 | mover 3:3 4:3 5:3 6:3 8:2 9:1; bar 0, off 0 / opponent 2:2 20:2 21:3 22:2 23:4 24:2; bar 0, off 0 |
| 12 | Safety wins | L2 · DeepSeek V4.1 Flash 1017 (on) (8/4 7/4, 0) | `md0MADjgewcHAA` | 43 | 8/4 7/4: +0.7144 / +0.7057 (0) | 13/9 6/3: +0.2371 / +0.2411 (15) | -0.4773 / -0.4646 | mover 6:5 7:4 8:3 13:3; bar 0, off 0 / opponent 1:3 16:2 18:2 19:3 20:2 22:2 24:1; bar 0, off 0 |
| 13 | Safety wins | L1 · Winnow-12B (10/8 8/6 6/4 6/4, 0) | `2LaDATAOzzkAMA` | 22 | 24/22 24/22 6/4 6/4: -0.3663 / -0.3648 (0) | 24/22 24/22 8/6 6/4: -0.5602 / -0.5600 (13) | -0.1939 / -0.1952 | mover 2:3 6:4 8:3 10:3 24:2; bar 0, off 0 / opponent 1:2 12:2 17:3 18:2 19:2 20:2 21:2; bar 0, off 0 |
| 14 | Safety wins | L1 · Mercury Decide (9/4 7/2 7/2 7/2, 0) | `PM6YATDY7YQBMA` | 55 | 13/8 13/8 8/3 8/3: +0.8391 / +0.8302 (0) | 13/8 13/8 9/4 8/3: +0.5906 / +0.5917 (14) | -0.2485 / -0.2385 | mover 4:2 5:3 6:2 7:3 9:1 13:2 24:2; bar 0, off 0 / opponent 1:2 12:2 14:2 17:2 19:3 22:4; bar 0, off 0 |
| 15 | Safety wins | L1 · Fastino GLiDE v1.2 (local) (23/18 23/17, 0) | `n3sOAAC59gAYGA` | 56 | 17/12 17/11: -0.8596 / -0.8696 (0) | 23/18 18/12: -1.0389 / -1.0549 (27) | -0.1793 / -0.1853 | mover 1:1 3:3 4:1 5:2 6:4 17:2 23:2; bar 0, off 0 / opponent 19:3 21:4 22:3 24:5; bar 0, off 0 |
| 16 | Safety wins | L1 · GPT-6 Luna (11/6 11/8, 0) | `2z8AATD8tokBAA` | 53 | 11/6 11/8: +0.8562 / +0.8924 (0) | 8/3 6/3: +0.5208 / +0.5555 (13) | -0.3354 / -0.3369 | mover 3:6 4:2 5:2 6:2 8:1 11:2; bar 0, off 0 / opponent 1:2 12:1 22:8 23:2 24:2; bar 0, off 0 |
| 17 | Safety wins | L2 · DeepSeek V4.1 Flash 1017 (on) (15/11 11/9*, 4) | `7+4CIAB7MzgYAA` | 42 | 10/6 6/4: -0.7480 / -0.7588 (0) | 10/6 15/13: -0.8756 / -0.8847 (26) | -0.1276 / -0.1259 | mover 1:2 2:4 3:2 5:2 10:3 15:2; bar 0, off 0 / opponent 9:1 20:1 21:3 22:3 23:3 24:4; bar 0, off 0 |
| 18 | Safety wins | L3 · Gemini 4 Argon (on) (13/11 13/11 7/5* 7/5, 0) | `xNuDAwLc3MAcAA` | 22 | 15/13 13/11 7/5* 7/5: +0.9837 / +0.9546 (0) | 7/5* 7/5 6/4 4/2: +0.7389 / +0.7131 (12) | -0.2447 / -0.2414 | mover 3:3 4:2 6:3 7:2 13:2 15:3; bar 0, off 0 / opponent 5:1 12:3 17:4 18:2 19:4 22:1; bar 0, off 0 |
| 19 | Safety wins | L2 · Qwen3.8 Flash (off) (4/off 4/3, 0) | `7/YAQEB3GwAAAA` | 51 | 4/off 4/3: +1.4717 / +1.4627 (0) | 4/off 3/2: +0.9547 / +0.9645 (20) | -0.5170 / -0.4982 | mover 1:3 2:3 3:2 4:2; bar 0, off 5 / opponent 7:1 21:4 22:2 23:3 24:4; bar 1, off 0 |
| 20 | Safety wins | L1 · SubQ Snap Preview (22/19* 22/19 6/3 6/3, 0) | `f/MEAIB7mwEABg` | 33 | 22/19* 22/19 19/16 16/13: +0.1968 / +0.1988 (0) | 22/19* 19/16 16/13 6/3: -0.3521 / -0.3582 (13) | -0.5490 / -0.5570 | mover 1:3 2:4 3:2 4:2 6:2 22:2; bar 0, off 0 / opponent 19:1 21:4 23:2 24:7; bar 0, off 1 |
