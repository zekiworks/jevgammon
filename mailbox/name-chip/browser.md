# Browser checks

375, 390 and 1280 px, light and dark, Chromium (Playwright), served over HTTP; the candidate's home page (the 375 px two-screen line also measures origin/main's render of the same state).

**42 of 42 ok.**

| Width | Theme | Check | Measured | OK |
|---:|---|---|---|---|
| 375 | light | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 80}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 75}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "medium \` | yes |
| 375 | light | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 375 | light | chips on the name's line / wrapped whole to the next line (measured) | `{"onNameLine": 28, "rows": 63}` | yes |
| 375 | light | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 375 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 375 | light | no script error | `[]` | yes |
| 375 | light | hero + first 3 rows within two screens (measured, origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1280, "row3Bottom": 1430.46875, "rowsInTwoScreens": 6}, "candidate": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1281.359375, "row3Bottom": 1442.390625, "rowsInTwoScreens": 6}}` | yes |
| 375 | dark | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 80}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 75}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "me` | yes |
| 375 | dark | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 375 | dark | chips on the name's line / wrapped whole to the next line (measured) | `{"onNameLine": 28, "rows": 63}` | yes |
| 375 | dark | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 375 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 375 | dark | no script error | `[]` | yes |
| 375 | dark | hero + first 3 rows within two screens (measured, origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1280, "row3Bottom": 1430.46875, "rowsInTwoScreens": 6}, "candidate": {"screen": 844, "heroBottom": 913.515625, "row1Bottom": 1281.359375, "row3Bottom": 1442.390625, "rowsInTwoScreens": 6}}` | yes |
| 390 | light | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 80}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 75}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "medium \` | yes |
| 390 | light | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 390 | light | chips on the name's line / wrapped whole to the next line (measured) | `{"onNameLine": 28, "rows": 63}` | yes |
| 390 | light | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 390 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 390 | light | no script error | `[]` | yes |
| 390 | light | hero + first 3 rows within two screens (measured, origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1271.4375, "row3Bottom": 1421.90625, "rowsInTwoScreens": 6}, "candidate": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1272.796875, "row3Bottom": 1433.828125, "rowsInTwoScreens": 6}}` | yes |
| 390 | dark | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 80}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 75}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "me` | yes |
| 390 | dark | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 390 | dark | chips on the name's line / wrapped whole to the next line (measured) | `{"onNameLine": 28, "rows": 63}` | yes |
| 390 | dark | box opens, first line name · maker · type · setting, every ranked row (tap on name, bar and score; second tap closes; no navigation) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 390 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 390 | dark | no script error | `[]` | yes |
| 390 | dark | hero + first 3 rows within two screens (measured, origin/main → candidate) | `{"main": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1271.4375, "row3Bottom": 1421.90625, "rowsInTwoScreens": 6}, "candidate": {"screen": 844, "heroBottom": 904.953125, "row1Bottom": 1272.796875, "row3Bottom": 1433.828125, "rowsInTwoScreens": 6}}` | yes |
| 1280 | light | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 78}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(75, 73, 68)", "size": "11.84px", "height": 79}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "medium \` | yes |
| 1280 | light | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 1280 | light | every chip on its name's line (wide window) | `{"offLine": []}` | yes |
| 1280 | light | box opens, first line name · maker · type · setting, every ranked row (hover on name, bar, score and empty space) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 1280 | light | keyboard focus beats the pointer (row 1 focused, mouse on row 3) | `{"focusedOpens": true, "heldWhileMouseOnRow3": true}` | yes |
| 1280 | light | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 1280 | light | no script error | `[]` | yes |
| 1280 | dark | chip per row (all rows, expanders open) = data; name = data; one chip, one line, within its cell | `{"rows": 63, "expected": 63, "bad": [], "sample": [{"box": "hl-1-box", "name": "GPT-6 Astra", "chip": "high \u00b7 chat \u00b7 late entry", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 78}, {"box": "hl-1-1-box", "name": "GPT-6 Astra", "chip": "low \u00b7 chat", "colour": "rgb(186, 183, 176)", "size": "11.84px", "height": 79}, {"box": "hl-1-2-box", "name": "GPT-6 Astra", "chip": "me` | yes |
| 1280 | dark | no sideways overflow (expanders open) | `{"overflow": 0}` | yes |
| 1280 | dark | every chip on its name's line (wide window) | `{"offLine": []}` | yes |
| 1280 | dark | box opens, first line name · maker · type · setting, every ranked row (hover on name, bar, score and empty space) | `{"rows": 38, "ok": 38, "bad": []}` | yes |
| 1280 | dark | keyboard focus beats the pointer (row 1 focused, mouse on row 3) | `{"focusedOpens": true, "heldWhileMouseOnRow3": true}` | yes |
| 1280 | dark | filter All / Chat / Decision | `{"chat": {"shown": 19, "types": ["chat", "program"], "boxOk": true}, "decision": {"shown": 25, "types": ["decision", "program"], "boxOk": true}, "all": {"shown": 41, "types": ["chat", "decision", "program"], "boxOk": true}}` | yes |
| 1280 | dark | no script error | `[]` | yes |
