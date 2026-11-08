# Browser checks

375, 390 and 1280 px, light and dark, Chromium (Playwright), served over HTTP; the candidate's home page (the 375 px two-screen line also measures origin/main's render of the same state).

**42 of 42 ok.**

| Width | Theme | Check | Measured | OK |
|---:|---|---|---|---|
| 375 | light | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 375 | light | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 375 | light | no sideways overflow | `{"overflow": 0}` | yes |
| 375 | light | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 375 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 375 | light | no script error | `[]` | yes |
| 375 | light | hero + first 3 rows within two screens (origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1328.625, "row3Bottom": 1551.75, "rowsInTwoScreens": 4}, "candidate": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1280, "row3Bottom": 1430.46875, "rowsInTwoScreens": 6}}` | yes |
| 375 | dark | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 375 | dark | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 375 | dark | no sideways overflow | `{"overflow": 0}` | yes |
| 375 | dark | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 375 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 375 | dark | no script error | `[]` | yes |
| 375 | dark | hero + first 3 rows within two screens (origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1328.625, "row3Bottom": 1551.75, "rowsInTwoScreens": 4}, "candidate": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1280, "row3Bottom": 1430.46875, "rowsInTwoScreens": 6}}` | yes |
| 390 | light | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 390 | light | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 390 | light | no sideways overflow | `{"overflow": 0}` | yes |
| 390 | light | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 390 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 390 | light | no script error | `[]` | yes |
| 390 | light | hero + first 3 rows within two screens (origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1299.375, "row3Bottom": 1522.5, "rowsInTwoScreens": 4}, "candidate": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1271.4375, "row3Bottom": 1421.90625, "rowsInTwoScreens": 6}}` | yes |
| 390 | dark | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 390 | dark | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 390 | dark | no sideways overflow | `{"overflow": 0}` | yes |
| 390 | dark | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 390 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 390 | dark | no script error | `[]` | yes |
| 390 | dark | hero + first 3 rows within two screens (origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1299.375, "row3Bottom": 1522.5, "rowsInTwoScreens": 4}, "candidate": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1271.4375, "row3Bottom": 1421.90625, "rowsInTwoScreens": 6}}` | yes |
| 1280 | light | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 1280 | light | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 1280 | light | no sideways overflow | `{"overflow": 0}` | yes |
| 1280 | light | box opens, first line name · maker · type · setting, every ranked row (hover on name, bar, score and empty space) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 1280 | light | keyboard focus beats the pointer (row 1 focused, mouse on row 3) | `{"focusedOpens": true, "heldWhileMouseOnRow3": true}` | yes |
| 1280 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 1280 | light | no script error | `[]` | yes |
| 1280 | dark | no sub-line under any name | `{"sublines": 0, "rankedRows": 38}` | yes |
| 1280 | dark | late tags small on the name's line | `{"tags": [{"name": "GPT-6 Astra", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Base Labs Mammoth-1", "tag": "late entry", "sameLine": true, "size": "12.48px"}, {"name": "Drex Max v1", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "REAX 1.3", "tag": "late entry \u00b7 provisional", "sameLine": true, "size": "12.48px"}, {"name": "Drex ` | yes |
| 1280 | dark | no sideways overflow | `{"overflow": 0}` | yes |
| 1280 | dark | box opens, first line name · maker · type · setting, every ranked row (hover on name, bar, score and empty space) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 1280 | dark | keyboard focus beats the pointer (row 1 focused, mouse on row 3) | `{"focusedOpens": true, "heldWhileMouseOnRow3": true}` | yes |
| 1280 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 1280 | dark | no script error | `[]` | yes |
