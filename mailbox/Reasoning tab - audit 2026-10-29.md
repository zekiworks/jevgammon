# Reasoning tab: audit of Ümit's findings (2026-10-29)

Saved data only. No model calls, no reruns, no change to any score, method, data value or privacy exclusion; v3.db read read-only.
Sources:
- risk judgement (`risk.main.judgement`, margin 0.001), its saved 95% interval, error rate and median s per decision: the published per-league files `~/.local/state/bg-site/analysis/backgammon/data/v3/league-N.json` (results 91487d22);
- the setting sent: every stored request body (`v3.db` exchanges) of each setup's model/fallback decisions in that league's matches, cross-checked against `mailbox/Setup relabel - proposal 2026-10-28.md` and `mailbox/Reasoning settings per model 2026-10-28.md`;
- provenance: `turns.provider` for the same decisions, and `setups.json`.

## 1. The nine same-league comparisons

The change is higher minus lower, from unrounded values. "Overlap" means the two saved 95% risk-judgement intervals overlap. That describes the intervals; it is not a test. All nine are unpaired: the two settings met different positions.

| # | Dataset (published) | Model | Settings sent (request logs) | Provenance (turns.provider) | Risk judgement, lower → higher [95% intervals] | Δ (unrounded) | Overlap | Error rate (PR), lower → higher [95%] | Median s/decision, lower → higher |
|---|---|---|---|---|---|---|---|---|---|
| 1 | league-1 | LFM2.5-24B-A2B | off: no reasoning field, prefilled empty `<think></think>` (2,410 req.) → on: thinking request `reasoning_effort: "low"` (template ignores it) + readout with no level (2,777 + 2,777) | local: `local-vllm` (1,952 / 2,193 decisions) | 45.739 [43.2, 48.1] → 52.414 [50.3, 54.5] | +6.675 | **no** | 61.47 [56.3, 66.8] → 47.69 [44.1, 51.2] | 0.14 → 324.81 (+324.7) |
| 2 | league-2 | Gemma 4 31B | `enable_thinking: false` (2,308) → `enable_thinking: true`, no level (5,682) | local: `local-vllm` (1,847 / 2,122) | 62.647 [60.4, 65.0] → 64.491 [62.9, 66.2] | +1.843 | yes | 22.48 [19.9, 25.3] → 19.58 [17.5, 21.7] | 0.31 → 120.60 |
| 3 | league-2 | DeepSeek V4.1 Flash 1017 | `reasoning.enabled: false` (2,508) → `reasoning_effort: "low"` (2,938) | API: `openrouter:deepseek` (2,034 / 2,234) | 58.532 [56.6, 60.5] → 68.496 [66.4, 70.6] | +9.964 | **no** | 35.25 [31.8, 38.8] → 17.14 [15.1, 19.2] | 0.84 → 22.33 |
| 4 | league-2 | Claude Sonnet 5.5 | `output_config.effort` low (2,739) → high (2,794) | Claude subscription (2,150 / 2,164) | 63.525 [61.6, 65.4] → 68.196 [66.3, 70.0] | +4.671 | **no** | 20.15 [17.8, 22.4] → 16.72 [14.9, 18.7] | 1.51 → 6.63 |
| 5 | league-3 | Gemini 4 Argon | `thinkingLevel` low (2,046) → high (1,932) | Antigravity subscription (1,484 / 1,368) | 69.239 [66.2, 72.3] → 74.089 [72.0, 76.1] | +4.850 | yes | 16.46 [13.7, 19.5] → 12.57 [10.5, 14.8] | 3.82 → 27.53 |
| 6 | league-3 | Claude Opus 5.5 | `output_config.effort` low (1,875) → high (1,955) | Claude subscription (1,411 / 1,477) | 66.945 [64.7, 69.2] → 69.959 [67.3, 72.6] | +3.014 | yes | 15.45 [13.1, 18.0] → 14.44 [12.1, 17.0] | 3.92 → 6.35 |
| 7 | league-2 | Gemini 3.8 Flash | `thinkingLevel` low (2,617) → high (2,798) | Antigravity subscription (2,053 / 2,168) | 65.143 [63.5, 66.8] → 66.863 [65.2, 68.5] | +1.720 | yes | 16.33 [14.5, 18.2] → 14.95 [12.9, 17.0] | 2.16 → 9.59 |
| 8 | league-3 | GPT-6 Astra | `reasoning.effort` low (1,721) → medium (1,870) | ChatGPT subscription (1,251 / 1,362) | 75.792 [73.1, 78.5] → 74.679 [71.9, 77.3] | −1.113 | yes | 11.81 [9.5, 14.2] → 11.10 [9.5, 12.9] | 3.94 → 4.40 |
| 9 | league-3 | GPT-6.1 Sol | `reasoning.effort` low (1,886) → high (2,155) | ChatGPT subscription (1,344 / 1,389) | 72.733 [69.9, 75.5] → 72.163 [69.5, 74.9] | −0.570 | yes | 12.13 [10.5, 13.7] → 9.90 [8.6, 11.3] | 4.33 → 13.10 |

Error-rate intervals overlap for 7 of the 9 pairs. They do not overlap for LFM2.5 and DeepSeek 1017, so the site reads "lower error rate in league play" for those two and "no clear difference in league play" for the other seven.

## 2. Ümit's findings

- **Her table: holds.** All 18 values, the nine changes, the settings, local vs API, and the overlap column match the saved data. Her roundings are correct; Argon's +4.850 rounds to +4.9.
- **"7 of 9 higher at the higher setting": holds.** Astra (−1.113) and Sol (−0.570) are the two lower.
- **Non-overlapping risk-judgement intervals: holds.** Exactly LFM2.5, DeepSeek 1017 and Sonnet, so "only Sonnet" is wrong.
- **LFM, DeepSeek 1017 and Sol missing from the Reasoning tab: true at 20:05 UTC, partly outdated now.**
  - DeepSeek 1017 has been on the tab since the build after 220411e (29 Oct 00:35 UTC); the published 91487d22 shows it.
  - LFM2.5 (League 1) and Sol (League 3) were still missing.
  - Cause: the tab paired setups through `setups.json` keyed by (dataset, name). Both models moved league in the ladder, and their `setups.json` entries sit under league-2, their original league, so they had no setting in the dataset where they are published.
- **Qwen3.8-27B is cross-league: holds.** (off) is published in league-1 (57.6) and (low) in league-2 (62.0). It is kept out of the pairs.
- **LFM2.5 has no effort knob: holds, with one precision.**
  - (off) prefills an empty thinking block. (on) lets it think.
  - Its (on) thinking requests do carry `reasoning_effort: "low"` (2,777 of them), but `setups.json` records that its template has no switch or effort setting and ignores it.
  - The display name stays Can's decision; it is unchanged here.
  - The median time rises by 324.7 s per decision (0.14 → 324.81), which matches her "about 325 s".
- **The Reasoning tab's "no clear difference" is about error rate: holds.** The tab used to show error rate only. That reading must not move to risk judgement. The candidate shows the two side by side and says so.
- **Not a proven effect of reasoning: holds.** The positions are not paired, and overlap is not a test.

### Discrepancies and additions she did not list
- **More cross-league pairs besides Qwen** (also kept out, same reason):
  - DeepSeek V4.1 Flash (non-1017): (off) in league-1, (low) in league-2;
  - Claude Fable 5.1: (low) in league-2, (high) in league-3;
  - Grok 4.7: (low) in league-2, (high) in league-3.
- **The nine are complete.** No other model has both settings in one published league.
- **"Only Sonnet" does not appear anywhere on the site.** I searched the site code, content and published pages, and the mailbox/workspace, and found no "only Sonnet" or similar claim. The site's risk cards (`share/risk-card-league-*.png`, one per league winner) carry no reasoning text. The claim must be in her own card draft, outside the repo. Nothing to correct on the site. For the card, the data supports this wording: "7 of 9 higher at the higher setting; risk-judgement intervals do not overlap for LFM2.5, DeepSeek V4.1 Flash 1017 and Claude Sonnet 5.5; unpaired, so not a shown effect of reasoning".

## 3. Candidate (for Zeki's technical review; not merged, not deployed)

- **Branch:** `reasoning-fix`, commit **919f83d** (on main 220411e). Worktree: `/tmp/reasoning-fix`.
- **What changed:**
  - `build.py` `league_reasoning`: a setup published in another league than the one its `setups.json` entry is under takes its model and setting from that entry. This is safe because `players.name` is unique, so the name is the setup identity. It adds `risk` = {change (unrounded), overlap} per pair.
  - `pages.py` Reasoning table:
    - new columns: risk judgement lower and higher with intervals, the change, whether the intervals overlap, and median s per decision at both settings;
    - the error-rate column is renamed "Error rate, in league play";
    - notes: the two measures are separate, overlap is not a test, and the comparison is unpaired with no causal claim;
    - an LFM2.5 note from the new `labels.json` `reasoning_notes`.
  - `method.py` and the `home.py` docstring: scope "Leagues 2 and 3" becomes "every model with both settings in one league's games". League 1 now gets the Risk tab's ability/caution table for LFM2.5.
- **Changed public files:**
  - `index.html` (Reasoning tab of Leagues 1–3, and the Risk tab's "by reasoning setting" table: LFM2.5 and Sol rows);
  - `leagues/index.html` (+2 notes);
  - `method/index.html` (1 phrase);
  - `data/results.json` and `data/v3/league-{1,2,3}.json` (added pairs and `risk` fields);
  - `data/index.html` and `data/manifest.json` (sizes and hashes);
  - `share/risk-card-league-*.png`: renamed only (the name hashes the footer's results hash).
  - Results hash: 57715425 (base, same snapshot) → 310bdf60.
- **Checks:**
  - `build.py` with `checks.run` exited 0 on both base and candidate (`/tmp/rf-{base,cand}-build.out`, copied to the evidence folder).
  - Numeric invariance: no existing value changed or was removed, in data or on pages; only additions, plus the replaced note sentence, one header rename and the League 1 "N/A" line. Details: `mailbox/reasoning-tab-audit-2026-10-29/invariance.txt`.
  - The base build's data JSON is byte-identical to the published 91487d22.
- **Evidence:** `mailbox/reasoning-tab-audit-2026-10-29/` holds the screenshots `reasoning-league-{1,2,3}.png`, `invariance.txt`, the build outputs and `rf-build.sh`, which builds a commit's `tools/site` the way `update.sh` does into `/tmp/rf-<label>-out`. The build outputs are in `/tmp/rf-base-out` and `/tmp/rf-cand-out`.
- **After Zeki accepts:** merge `reasoning-fix` into main; `bg-site-preview.timer` then deploys it.
