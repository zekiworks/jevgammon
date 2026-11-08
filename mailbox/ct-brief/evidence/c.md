# c. Clear risk: numbers on screen

Source: tools/site/content/clear_risk_results.json `sections[id=clear-risk-part2].tables[caption^='Q1']` (status: `status` = "Preliminary / partial"; `label` = "Preliminary / partial. Two or four plays shown, not league play."). Live heading today: "With the numbers on screen, every model asked played safer" (index.html #finding-flinch; rule story.py:457-464 compares Q1 bias with numbers vs board only).

Criterion: KEEP if every model asked has a higher safe-play share with numbers shown than board only. Safe-play share = (missed: Risk wins → safe, n) + (Safety wins right, n) over the answered items of the two groups.

| Model | With numbers: safe share | Board only: safe share | Higher with numbers? | Bias numbers / board |
|---|---|---|---|---|
| Celeris-1 Decision | 95.8% (181/189) | 43.2% (80/185) | yes | +91 pp / -14 pp |
| Jev 1.14.0 | 96.3% (180/187) | 38.9% (72/185) | yes | +92 pp / -22 pp |
| Liquid d1-ultra | 87.3% (165/189) | 39.4% (71/180) | yes | +74 pp / -21 pp |
| Claude Sonnet 5.5 (high) | 83.1% (157/189) | 71.4% (135/189) | yes | +66 pp / +42 pp |
| GPT-6.1 Sol (high) | 77.2% (146/189) | 52.4% (99/189) | yes | +54 pp / +4 pp |
| Kimi K3.1 Pro (off) | 85.2% (161/189) | 37.6% (71/189) | yes | +70 pp / -25 pp |
| GLM-5.3 (on) | 88.9% (168/189) | 59.3% (112/189) | yes | +78 pp / +18 pp |
| Claude Opus 5.5 (on) | 78.3% (148/189) | 73.5% (139/189) | yes | +56 pp / +46 pp |

Result: 8 of 8 models asked have a higher safe-play share (and a higher bias) with the numbers shown. Only 8 models were asked (not all 38 ranked), so the heading must say 'every model asked'. Live text: from the board alone, 4 of them (Celeris-1 Decision, Jev 1.14.0, Liquid d1-ultra, Kimi K3.1 Pro (off)) took more needless risks than they missed (bias < 0). Name note: data says 'Claude Opus 5.5 (on)' / 'GLM-5.3 (on)'; live page displays 'Claude Opus 5.5 (high)'.

Status: Preliminary / partial (two plays shown, not league play).

Verdict: **KEEP** — heading: **With the numbers on screen, every model asked played safer.** (add 'asked'; the brief's 'every model' overstates: 8 models).
