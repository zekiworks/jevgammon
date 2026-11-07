# Heading: "Models are too cautious"

Source: the live site's published data files (results 04493cf3, data as of 2026-11-07T17:35Z): data/v3/clear-risk.json, section clear-risk-setups ("Missed and needless risks per setup", kept decisions only). Read-only; every number below is copied from those files as printed.

Claim checked: in the clear-risk scan, bias = missed − needless is positive for every model setup, and not for the programs.

Result: **holds**. 45 model setups, all with a positive bias (lowest +30.0 pp, GPT-6.1 Sol (high), League 3; highest +80.6 pp, Celeris-1 Decision, League 1). Programs: 4 of 5 rows negative (GNUbg weak L1 -11.2 pp, Random L1 -41.9 pp, GNUbg weak L2 -14.1 pp, GNUbg weak L3 -3.9 pp); Safest is +100 by construction (it never plays an unsafe play), which the page says.

Scope: kept clear-risk decisions only (the scan's 2-ply/3-ply stability rule), not every league decision; setups met different positions (not paired). The page shows this as the section's one caveat.

| League | Setup | Missed risks | Needless risks | Bias | Program |
|---|---|---|---|---:|---|
| 1 | Celeris-1 Decision | 81.5% (137/168) | 1.0% (4/408) | +80.6 pp |  |
| 1 | GPT-6 Luna | 80.2% (158/197) | 2.1% (7/330) | +78.1 pp |  |
| 1 | Jev 1.13.0 | 77.3% (143/185) | 0.8% (3/354) | +76.4 pp |  |
| 1 | Mercury Decide | 77.4% (168/217) | 1.3% (4/307) | +76.1 pp |  |
| 2 | GLM-5.3 (low) | 73.6% (142/193) | 0.3% (1/365) | +73.3 pp |  |
| 1 | Qwen3.8-27B (off) | 74.9% (173/231) | 1.8% (6/331) | +73.1 pp |  |
| 1 | Cygnet (Gemma 4 12B) | 75.8% (182/240) | 3.4% (10/297) | +72.5 pp |  |
| 2 | DeepSeek V4.1 Flash 1017 (off) | 72.2% (140/194) | 0.8% (3/395) | +71.4 pp |  |
| 2 | Jev 1.14.0 | 74.3% (139/187) | 2.9% (10/347) | +71.4 pp |  |
| 1 | Decider v1.2 27B | 66.9% (97/145) | 4.4% (16/361) | +62.5 pp |  |
| 1 | DeepSeek V4.1 Flash (off) | 62.9% (122/194) | 1.3% (4/299) | +61.5 pp |  |
| 2 | Claude Sonnet 5.5 (low) | 61.8% (105/170) | 0.6% (3/466) | +61.1 pp |  |
| 1 | Decider v1.1 27B | 67.4% (118/175) | 7.3% (27/369) | +60.1 pp |  |
| 2 | Gemma 4 31B (off) | 60.9% (81/133) | 1.6% (6/371) | +59.3 pp |  |
| 2 | Qwen3.8-27B (low) | 62.2% (117/188) | 3.3% (12/368) | +59.0 pp |  |
| 2 | Gemma 4 31B (on) | 57.4% (109/190) | 0.0% (0/435) | +57.4 pp |  |
| 1 | Fastino GLiDE v1.2 (local) | 63.3% (88/139) | 6.5% (27/417) | +56.8 pp |  |
| 2 | Gemini 3.8 Flash (low) | 57.6% (87/151) | 1.4% (6/421) | +56.2 pp |  |
| 1 | LFM2.5-24B-A2B (off) | 64.6% (115/178) | 10.4% (29/278) | +54.2 pp |  |
| 1 | Winnow-12B | 61.5% (126/205) | 7.4% (23/311) | +54.1 pp |  |
| 2 | Gemini 3.8 Flash (high) | 53.5% (91/170) | 0.2% (1/454) | +53.3 pp |  |
| 2 | Claude Sonnet 5.5 (high) | 53.1% (103/194) | 0.5% (2/428) | +52.6 pp |  |
| 3 | Gemini 4 Argon (low) | 54.8% (63/115) | 2.4% (7/297) | +52.4 pp |  |
| 2 | Qwen3.8 Flash (off) | 55.0% (120/218) | 3.3% (11/334) | +51.8 pp |  |
| 3 | Grok 4.7 (high) | 52.5% (73/139) | 1.6% (4/250) | +50.9 pp |  |
| 2 | DeepSeek V4.1 Flash 1017 (low) | 49.7% (92/185) | 2.1% (10/476) | +47.6 pp |  |
| 3 | Claude Opus 5.5 (high) | 48.7% (57/117) | 1.5% (4/260) | +47.2 pp |  |
| 2 | Fastino GLiDE | 50.6% (79/156) | 4.4% (18/410) | +46.3 pp |  |
| 2 | DeepSeek V4.1 Flash (low) | 48.1% (90/187) | 1.9% (9/472) | +46.2 pp |  |
| 2 | Grok 4.7 (low) | 46.2% (84/182) | 0.0% (0/414) | +46.2 pp |  |
| 1 | SubQ Snap Preview | 52.8% (95/180) | 7.2% (28/388) | +45.6 pp |  |
| 3 | Claude Opus 5.5 (low) | 47.1% (56/119) | 1.7% (5/289) | +45.3 pp |  |
| 2 | Liquid d1-ultra | 49.1% (84/171) | 4.3% (18/414) | +44.8 pp |  |
| 2 | Clef | 54.9% (100/182) | 10.6% (36/340) | +44.4 pp |  |
| 3 | Kimi K3.1 Pro (off) | 45.9% (39/85) | 2.2% (5/225) | +43.7 pp |  |
| 1 | LFM2.5-24B-A2B (on) | 55.7% (103/185) | 12.1% (43/356) | +43.6 pp |  |
| 2 | Claude Fable 5.1 (low) | 44.2% (73/165) | 2.1% (8/385) | +42.2 pp |  |
| 3 | Gemini 4 Argon (high) | 42.6% (43/101) | 0.4% (1/237) | +42.2 pp |  |
| 1 | Decider Flash v1.2 | 51.9% (83/160) | 13.9% (47/339) | +38.0 pp |  |
| 3 | GPT-6 Astra (low) | 39.0% (41/105) | 1.1% (3/261) | +37.9 pp |  |
| 3 | GPT-6 Astra (medium) | 35.0% (41/117) | 0.7% (2/280) | +34.3 pp |  |
| 3 | Claude Fable 5.1 (high) | 35.3% (36/102) | 2.4% (7/295) | +32.9 pp |  |
| 3 | GPT-6.1 Sol (low) | 32.4% (35/108) | 1.0% (3/302) | +31.4 pp |  |
| 1 | Open-Jev 27B v1.1 | 50.4% (69/137) | 20.3% (62/306) | +30.1 pp |  |
| 3 | GPT-6.1 Sol (high) | 31.8% (28/88) | 1.8% (6/334) | +30.0 pp |  |
| 1 | Safest | 100.0% (233/233) | 0.0% (0/329) | +100.0 pp | yes |
| 3 | GNUbg weak | 10.8% (12/111) | 14.7% (36/245) | -3.9 pp | yes |
| 1 | GNUbg weak | 3.8% (4/104) | 15.1% (47/312) | -11.2 pp | yes |
| 2 | GNUbg weak | 7.4% (9/121) | 21.5% (88/409) | -14.1 pp | yes |
| 1 | Random | 23.8% (19/80) | 65.6% (86/131) | -41.9 pp | yes |
