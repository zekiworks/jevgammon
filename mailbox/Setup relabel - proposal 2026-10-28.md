# Setup relabel: proposal (2026-10-28)

**To apply after the post; waiting for Can's go.**

Can's rule (2026-10-28): rename each setup after the effort level its requests actually sent, for example "Gemini 4 Argon (high)" or "DeepSeek V4.1 Flash 1017 (low)". Keep "(on)" only where no level was sent (thinking switched on and nothing more). Keep the old name as an alias so existing links still work. **This is a proposal only.** Nothing has been renamed or deployed, and no site file has been changed. `v3.db` and `smoke/*.db` were opened read-only.

**Verified from the request logs (every stored request), not from the settings.** The effort field was read from every request body: `v3.db` exchanges (200,274 requests, all matches), `smoke/nack-paired.db` answer_exchanges, `smoke/part-a.db`, `smoke/argon-on-smoke.db`, `smoke/astra-high-smoke.db` and `smoke/terra-codex-smoke.db`. The fields read were `reasoning.effort`, `output_config.effort`, `generationConfig.thinkingConfig.thinkingLevel`, `reasoning_effort`, `reasoning.enabled` and `chat_template_kwargs.enable_thinking`. Each setup sent a single level throughout. The only differences are the readout requests of the two-request local setups, which carry only `enable_thinking` (counts in §2).

Other sources: `tools/site/content/setups.json`; the published build under `~/.local/state/bg-site/analysis/backgammon/` (15:35 UTC); logged reasoning tokens (v3.db turns, valid matches).

## 1. Rules proposed

- **The label is the effort value sent**: `(low)`, `(medium)`, `(high)`, and later `(xhigh)` / `(max)`. The value is the exact string in the request: `reasoning.effort` (Codex, xAI), `output_config.effort` (Claude), `thinkingLevel` plus the model id suffix (Antigravity), or `reasoning_effort` (OpenRouter, vLLM).
- **Setups that send no reasoning keep `(off)`, not `(none)`.** Reasons:
  1. Only one of them, Kimi K3.1 Pro, sends the effort string `"none"`. The others turn reasoning off with a switch: `reasoning.enabled: false` (DeepSeek, Qwen3.8 Flash), `chat_template_kwargs.enable_thinking: false` (Qwen3.8-27B, Gemma 4 31B, Qwen3.8 Flash Next, Nemotron), or a prefilled empty `<think></think>` (LFM2.5). "(none)" would name one API's value and misdescribe six of the seven. "(off)" describes all of them.
  2. Every one of them logged **0 reasoning tokens**: DeepSeek (off), 1017 (off), Qwen3.8 Flash (off), Qwen3.8-27B (off), Gemma (off), LFM (off) and Kimi (off) all average 0 in v3.db. Today's probe agrees: Kimi `none` gave 0 reasoning tokens, and DeepSeek 1017 `reasoning.enabled:false` gave 0. After the relabel, "(off)" means exactly "no reasoning". It never again means "the lowest effort".
  3. Their slugs (`…-off`) do not change, so these 8 published pages need no redirect.
- **`(on)` stays only where the requests sent no level**: thinking switched on (`enable_thinking: true`) with no effort field. These are Gemma 4 31B (on), Qwen3.8 Flash Next (on) and Nemotron 3.5 Bolt (on).
- **Setups already named by effort stay as they are**: Sol (low)/(high), Sonnet (low)/(high), Gemini 3.8 Flash (low)/(high) and Astra (high).
- **Decision models and programs carry no label** (Jev, Luna, Celeris, SubQ, Mercury Decide, Deciders, Liquid, Fastino, Cygnet, Clef, Open-Jev, Winnow, GNUbg weak, Random, Safest). They are unchanged.

## 2. Full list: every setup in v3.db and the paired test

The "Used in" column abbreviates as follows: L1/L2/L3 = original league; site = published dataset (`models/<ds>/<slug>/`, `data/v3/<ds>/<slug>.json`, `decisions/<ds>/<slug>/`); NP = Nackgammon paired test (`leagues/nack-paired.json`, `smoke/nack-paired.db`, `positions/nack-paired/results/results.json`); CCB = close choices stage B (`content/close_choices_b_results.json`).

### Renamed (16)

| # | Old name → **new name** | Level in the requests (logs; request counts) | Logged reasoning tok/dec | Old slug → new slug | Used in |
|---|---|---|---|---|---|
| 1 | GPT-6 Astra (off) → **GPT-6 Astra (low)** | Codex `reasoning.effort: "low"` (none/minimal rejected) | 78 | gpt-6-astra-off → gpt-6-astra-low | L3; site league-3 |
| 2 | GPT-6 Astra (on) → **GPT-6 Astra (medium)** | `"medium"` (model default) | 87 | gpt-6-astra-on → gpt-6-astra-medium | L3; site league-3; NP (grouped member, `ORIGINAL_MEMBERS`); CCB team |
| 3 | Claude Opus 5.5 (off) → **Claude Opus 5.5 (low)** | `output_config.effort: "low"` (thinking disabled rejected) | 251 | claude-opus-5-5-off → claude-opus-5-5-low | L3; site league-3 |
| 4 | Claude Opus 5.5 (on) → **Claude Opus 5.5 (high)** | `"high"` (default) | 631 | claude-opus-5-5-on → claude-opus-5-5-high | L3; site league-3; CCB team |
| 5 | Claude Fable 5.1 (off) → **Claude Fable 5.1 (low)** | `"low"` (thinking disabled rejected) | 101 | claude-fable-5-1-off → claude-fable-5-1-low | L3; site **league-2** |
| 6 | Claude Fable 5.1 (on) → **Claude Fable 5.1 (high)** | `"high"` (default) | 1,346 | claude-fable-5-1-on → claude-fable-5-1-high | L3; site league-3; NP (§10.14(g) addition, running) |
| 7 | Gemini 4 Argon (off) → **Gemini 4 Argon (low)** | `thinkingLevel: "low"`, id `gemini-4-argon-low` | **0** (the setting text should say "spends no reasoning tokens") | gemini-4-argon-off → gemini-4-argon-low | L3; site league-3 |
| 8 | Gemini 4 Argon (on) → **Gemini 4 Argon (high)** | `"high"`, id `gemini-4-argon-high` | 6,535 | gemini-4-argon-on → gemini-4-argon-high | L3; site league-3; NP (exploratory, `EXPLORATORY`); `leagues/smoke-argon-on.json` |
| 9 | Grok 4.7 (off) → **Grok 4.7 (low)** | xAI `reasoning.effort: "low"` (none rejected, minimal served as low) | 3,400 | grok-4-7-off → grok-4-7-low | L3; site **league-2** |
| 10 | Grok 4.7 (on) → **Grok 4.7 (high)** | `"high"` (default) | 17,081 | grok-4-7-on → grok-4-7-high | L3; site league-3; NP (§10.14(g) addition, running) |
| 11 | DeepSeek V4.1 Flash (on) → **DeepSeek V4.1 Flash (low)** | `reasoning_effort: "low"` (OpenRouter/Fireworks, then our SGLang) | 9,579 | deepseek-v4-1-flash-on → deepseek-v4-1-flash-low | L2; site league-2 |
| 12 | DeepSeek V4.1 Flash 1017 (on) → **DeepSeek V4.1 Flash 1017 (low)** | `reasoning_effort: "low"` (OpenRouter → DeepSeek) | 7,026 | deepseek-v4-1-flash-1017-on → deepseek-v4-1-flash-1017-low | L2 (late entry); site league-2 (not in setups.json: uses the `slug(name)` fallback) |
| 13 | GLM-5.3 (on) → **GLM-5.3 (low)** | `reasoning_effort: "low"` (reasoning mandatory; the probe confirms `none` is rejected) | 107 | glm-5-3-on → glm-5-3-low | L2; site league-2 |
| 14 | Qwen3.8-27B (on) → **Qwen3.8-27B (low)** | Thinking requests: `reasoning_effort: "low"` + `enable_thinking: true` (3,874 via vLLM; 2,241 earlier via Cerebras/OpenRouter with `"low"`). Readout requests: only `enable_thinking: true` (3,874) | 5,537 | qwen3-8-27b-on → qwen3-8-27b-low | L2; site league-2 |
| 15 | LFM2.5-24B-A2B (on) → **LFM2.5-24B-A2B (low)** | Thinking requests: `reasoning_effort: "low"` (6,270 in v3.db; 893 in NP). Readout requests: no level (5,220; NP 893) | 0 reported (it always reasons: 21,557 output tok/dec as content) | lfm2-5-24b-a2b-on → lfm2-5-24b-a2b-low | L1; site **league-1**; NP grouped member (`ORIGINAL_MEMBERS`, comparison 4: LFM (on) − (off)). **Flag:** the setting note says its template has no switch or effort knob and ignores "low". Can's rule names it after what is sent, so "(low)". The setting text should add "low is sent; the template has no effort setting". |
| 16 | GPT-6.1 Terra (paired, OpenRouter) → **GPT-6.1 Terra (low, OpenRouter)** | `reasoning_effort: "low"` (NP 1,000 requests) | 79 | (not published) | NP only. The route is in the name because the planned Codex setups are "GPT-6.1 Terra (low)" and "(high)" (`smoke/terra-codex-smoke.db`: `"low"` 20, `"high"` 20). |

Request-log check for rows 1–13: Astra (off) `low` 2,529; Astra (on) `medium` 2,528 (NP 1,000); Opus (off) `low` 2,314; Opus (on) `high` 2,514; Fable (off) `low` 5,069; Fable (on) `high` 2,358 (NP 1,000); Argon (off) `low` 5,071; Argon (on) `high` 2,454 (smoke 50); Grok (off) `low` 4,742; Grok (on) `high` 2,457 (NP 164); DeepSeek V4.1 Flash (on) `low` 4,269 (1,362 of them on our SGLang with `thinking: true`); DeepSeek 1017 (on) `low` 4,199; GLM-5.3 (on) `low` 3,787. The setups that are already effort-named match their names too: Astra (high) `high` 555 (smoke 20); Sol `low` 4,916 / `high` 5,438; Sonnet `low` 4,373 / `high` 4,479; Gemini 3.8 Flash `low` 5,128 / `high` 4,715.

### Unchanged (with what is sent)

| Setup | Sent | Reason |
|---|---|---|
| GPT-6 Astra (high) | `"high"` | already effort-named (late L3 entry; not published yet) |
| GPT-6.1 Sol (low) / (high) | `"low"` / `"high"` | already effort-named; NP primary comparison 5 |
| Claude Sonnet 5.5 (low) / (high) | `"low"` / `"high"` | already effort-named; NP (low) |
| Gemini 3.8 Flash (low) / (high) | `"low"` / `"high"` + model id suffix | already effort-named; NP (low) |
| DeepSeek V4.1 Flash (off) | `reasoning.enabled: false` (5,637; NP 1,000), on our SGLang `thinking: false` (232); 0 reasoning tok | real off; L1 site, NP grouped member |
| DeepSeek V4.1 Flash 1017 (off) | `reasoning.enabled: false` (3,666); 0 | real off |
| Qwen3.8 Flash (off) | `reasoning.enabled: false` (4,982, OpenRouter → Alibaba); 0 | real off |
| Qwen3.8-27B (off) | `enable_thinking: false` (7,008; NP 1,000); `reasoning.enabled: false` before 10-19 (1,860); 0 | real off; NP grouped member |
| Gemma 4 31B (off) | `enable_thinking: false` (5,342); 0 | real off |
| LFM2.5-24B-A2B (off) | no level and no switch (5,471; NP 1,000): prefilled `<think></think>Answer:`; 0 | real off; NP grouped member (comparison 4) |
| Kimi K3.1 Pro (off) | `reasoning_effort: "none"` (1,933); 0 (probe: 0) | real off; site league-3 (fallback slug) |
| Qwen3.8 Flash Next (off) | `enable_thinking: false` (1,012) | real off (withdrawn) |
| **Gemma 4 31B (on)** | `enable_thinking: true` only, **no level** (12,198; NP 2,000); 5,476 reasoning tok | **keep "(on)"** (template default) |
| **Qwen3.8 Flash Next (on)** | `enable_thinking: true` only, no level (108) | **keep "(on)"** (withdrawn) |
| **Nemotron 3.5 Bolt (off) / (on)** (smoke-part-a) | `enable_thinking` false (50) / true only, no level (100) | real off / **keep "(on)"** |
| Smoke Part A (off): Mercury 3, MiMo V2.6 Pro, MiMo V2.6 Flash (incl. "unconstrained"), Hy4 Preview | `reasoning.enabled: false` (50 each) | real off: keep |
| Smoke Part A effort-named: Haiku, Fable, Grok, Mercury 3, MiMo, Beam, Kimi K3, MiniMax, Gemini (low)/(high) | as named | already effort-named. Note that smoke "Claude Fable 5.1 (low)/(high)" and "Grok 4.7 (low)/(high)" will share names with the renamed league setups. This is correct: same effort, different dataset, and their slugs keep the `smoke-` prefix. |
| v1-set (earlier version), e.g. "DeepSeek V4.1 Flash (thinking)" | — | frozen earlier version: leave as is |

## 3. How the old labels keep working (aliases)

**Proposal: relabel at the display layer and leave the records alone.** `v3.db`, `smoke/*.db`, `leagues/*.json` and `freeze/*.json` keep the old names. Reasons:
- The freeze entries carry `entry_sha256` over the roster entry, which includes the name.
- Running jobs address setups by name: the Astra (high) league in `league3-astra-high.json` and Season2's NP runs for Fable (on), Grok (on) and Argon (on).
- `players.name` is UNIQUE and is repeated inside `players.settings`, `leagues.ranking` and the notes.

Renaming the records would break the hashes and could disturb running jobs, and it buys nothing for readers.

How the site builds names today, as found in the code:
- `slug(name) = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")` (`tools/site/common.py:34-35`).
- Page URLs use the `slug` field of `tools/site/content/setups.json`, keyed by `(dataset, name)`. If a name is missing there, they fall back to `slug(name)` (`pages.py:92-101`).
- Data JSON and decisions always use `slug(name)` (`analysis.py:679`, `build.py:196-203`, `decisions_export.py:79-81`).
- Every build deletes and rewrites `models/`, `data/` and `decisions/` (`pages.py:974-977`, `build.py:183-184`, `decisions_export.py:352-354`). No alias mechanism exists. The only redirect code is `preview_redirects` (`build.py:350-366`: `<meta refresh>` plus `location.replace` stubs).

The changes:
1. **New `tools/site/content/labels.json`: the alias table.** It holds `{old name: {"name": new name, "since": date, "sent": effort value}}` for the 16 renames. It is the one source for the site, the dashboard and the paper tables.
2. **`tools/site/snapshot.py` `run()`.** Right after the tables are copied into `snap.db` (lines 331-341), apply the table to the snapshot only. That means `players.name`, the `name` inside `players.settings`, and names inside `leagues.ranking`. `league_match_view`, `analysis.py`, `decisions_export.py` and `findings` all read the snapshot, so every page then shows the new names from one cut point. `v3.db` stays read-only. (About 20 lines.)
3. **`content/setups.json`.** For the 14 renamed entries present there: new `name`, `slug`, `setting` (`low`/`medium`/`high`) and `reasoning` text, plus `"aliases": [old name]` and `"old_slugs": [old slug]`. Add entries for the setups now on the fallback (DeepSeek 1017 (off)/(low), Kimi K3.1 Pro (off), Astra (high)) so that they get a `setting` and pair correctly.
4. **Old URLs, built by `build.py` next to `preview_redirects`:**
   - `models/<ds>/<old-slug>/index.html`: redirect stub to the new page, with a canonical link.
   - `data/v3/<ds>/<old-slug>.json`: GitHub Pages cannot redirect a JSON file, so write a full copy with `"alias_of": "<new path>"`. That is 15 files of about 52 KB each, about 0.8 MB.
   - The per-setup JSON and `data/setups.json` carry `"aliases": [old names]`.
   - `decisions/`: the viewer resolves an old `?s=<old-slug>` through `data/setups.json` aliases (a few lines of JS). The 15 old decision directories (part of 73 MB) are **not** duplicated.
5. **`checks.py`.** Every alias resolves to a current setup, no alias equals a current name, and every old slug has its stub.
6. **Pairing code that would otherwise break:**
   - `build.py:153` `order = {"off": 0, "low": 0, "on": 1, "high": 1}` has no `medium`.
   - `build.py:156` keeps only models with exactly 2 settings.
   - Proposed: order off < low < medium < high < xhigh < max. Pair each model's lowest setting with each higher one in the same league. So Astra gives low → medium, and later low → high once Astra (high) is published.
   - `pages.py:431` then renders "Claude Opus 5.5, low → high" with no text change.
   - `home.py:43` (`f"reasoning {setting}"`) should print "effort low" for effort values and "reasoning off" / "thinking on (template default)" for off/on.
7. **Dashboard** (`tools/league_web.py`, names from the DB at `:198`, `:479`, `:664`): apply the same `labels.json` when it displays a name (about 10 lines), and keep the old name in a tooltip. Internal tool: optional.
8. **Nackgammon paired test and paper.** `positions/nack-paired/results/results.json`, `release/nack-paired*/` and `freeze/nack-paired.json` are frozen and stay as they are. `nack_paired_score.py` keeps the old names in `EXPLORATORY`, `ORIGINAL_MEMBERS` and `PRIMARY` (frozen inputs). Its report tables and the paper show `labels.json` names, each with a footnote giving the old name once.
   - There is no paper source in the repo (`**/*paper*` finds nothing), so this list is the source for the paper's setup table.

## 4. "off → on" wording: every occurrence and the proposed wording

| Where | Now | Proposed |
|---|---|---|
| `tools/site/method.py:158-159` (Method → Setup) | "a model with reasoning off and the same model with reasoning on are two setups." | "the same model at two reasoning settings (for example effort low and effort high, or reasoning off and effort low) is two setups. A setup is named by the setting sent: (off) = no reasoning; (low), (medium), (high), … = the effort value sent; (on) = thinking at a chat template's default, where no effort can be set." |
| `method.py:166-167` | "League 2: workhorse chat models, closed and open, each in two settings (reasoning low and high, or off and on)." | "… each in two settings: two effort levels (low and high), or reasoning off and effort low (open models), or off and the template default (on)." |
| `method.py:168-169` | "League 3: frontier chat models played through their subscriptions, each with reasoning off and on." | "… each at its lowest effort (low; none of them accepts reasoning off) and its default effort (high; medium for GPT-6 Astra)." |
| `tools/site/pages.py:431` (generated league note "Model, off → on: …") | from `setups.json` `setting` | no code change: it renders "low → high", "low → medium", "off → low" once `setting` is updated |
| `tools/site/home.py:43` | "reasoning off" / "reasoning on" under each name | "effort low" / "effort high" / "reasoning off" / "thinking on (template default)" |
| `content/setups.json` `reasoning` texts | e.g. `:1292` "…the lowest gpt-6-astra accepts (labelled off)"; `:1364`, `:1436`, `:1508`, `:1580` "(labelled off)"; `:2381`, `:2801` "also in League 3 as (off)"; `:2411`, `:2831` "as (on)" | drop "(labelled off)", e.g. "reasoning effort low, the lowest gpt-6-astra accepts"; "also in League 3 as (low)" / "(high)" |
| `content/analysis_status.json:44` | "Return on more reasoning (paired low vs high, off vs on)" | "Return on more reasoning (the same model at a lower and a higher setting)" |
| `content/close_choices_b_results.json:10,45` | teams "Claude Opus 5.5 (on)", "GPT-6 Astra (on)" | mapped through `labels.json` at build time (published file shows "(high)", "(medium)"; frozen stage B inputs unchanged) |
| `content/method-spec-2026-10-24.md` (about 29 name lines, e.g. `:78-80`, `:733`) | frozen Method spec | **unchanged** (frozen). Add a dated note at its top: "Setup names relabelled 2026-10-xx; see labels.json." |
| `tools/site/archive_page/index.html` (frozen 2026-10-23), e.g. `:94`, `:130-132`, `:261-271`, `:315-316` ("On is the model's default…; off is its lowest…") | archive | **unchanged** (frozen archive). One line above it: "Names as of 2026-10-23; current names: …" |
| v3.db `leagues.note` id 3 (and `leagues/league3.json:2`) | "v3 League 3: frontier, closed models on subscriptions, each with reasoning off (its lowest setting where it has no off) and on (its default setting)." | Not rendered by the site: `analysis.py` reads league rows, and no site code renders `note`. Do not rewrite; it is a record. If Can wants it changed, append a dated line: "Relabel 2026-10-xx: setups are named by the effort sent: (off) → (low); (on) → (high), Astra (on) → (medium)." |
| v3.db `leagues.note` id 2 | "LFM2.5-24B-A2B (off, on)…", "Gemma 4 31B (off, on)…", "Qwen3.8-27B (off, on)…", "DeepSeek V4.1 Flash (off) and (on)…" | record: unchanged; the LFM, Qwen27 and DeepSeek "(on)" names resolve through the alias table |
| v3.db `players.settings` `$.note`, ids 3, 21, 22, 24, 46: "…, labelled off." | record | unchanged; the site shows `setups.json` `reasoning`, not this note |
| `tools/v3/rosters.py:6-8` | "Open models' "on" setups use the lowest effort their API offers …" | "Open models' reasoning setups send the lowest effort their API offers (named by it, e.g. (low)); local templates with no effort knob think at the default and are named (on)." |
| `tools/v3/page_v3.py:656`, `:455`, `:604` (old pre-switch generator) | "each with reasoning off and on" | not used by the live site: leave it, or delete it if it is dead |
| `README.md:254`, `:260` ("With reasoning on…", "Reasoning off is request 2 alone") | protocol text, not labels | unchanged (correct as written) |
| `tools/v3/servers/README.md:59`, `:64`, `:371-372` | "Thinking on and off" (template switch) | unchanged (describes the switch, which is right for those servers) |
| `mailbox/backgammon-site-brief.md:93` | "reasoning on · letter probabilities · our GPU" | "effort low · letter probabilities · our GPU" |
| `mailbox/backgammon-site-plan.md:23`, `:54` (= `workspace/` copies, and `workspace/backgammon-site-brief.md:107`) | "the same model at low vs high, or off vs on" | "the same model at a lower and a higher setting (effort values, or off vs effort low)" |

**Published mailbox reports:** none is rendered as a page. The site cites mailbox files only as provenance: `setups.json` `sources`, `content/experiments.json:4,27` and `content/human_scale.json`. The cited files ("Backgammon benchmark v3 design final", "Part A smoke tests - results", "Roll-schedule test - results", "Anchor checks - results") need no edit, because their numbers do not depend on names. In all, 49 of 87 mailbox reports mention an (off)/(on) name. They are dated records, and the alias table covers them.

## 5. Every file the relabel touches

- **Site code:** `tools/site/snapshot.py` (apply aliases), `build.py` (pairing order, alias data, redirect stubs), `checks.py` (alias checks), `home.py:43` (setting chip text), `method.py:158-169` (Method → Setup, Leagues), decisions viewer JS (old `?s=` slugs). `pages.py:431` needs no change.
- **Site content:** new `content/labels.json`; `content/setups.json` (14 entries renamed and 4 added); `content/analysis_status.json:44`; one dated line on `method-spec-2026-10-24.md` and on the archive page.
- **Published output** (on the next build, after approval):
  - `models/league-1/`: 1 renamed page plus 1 stub (lfm2-5-24b-a2b-on).
  - `models/league-2/`: 6 renamed pages plus 6 stubs (fable-off, deepseek-1017-on, deepseek-on, glm-on, grok-off, qwen27-on).
  - `models/league-3/`: 8 renamed pages plus 8 stubs (fable-on, opus off/on, argon off/on, astra off/on, grok-on).
  - The matching `data/v3/league-{1,2,3}/*.json` (15 new plus 15 alias copies) and `decisions/league-{1,2,3}/` (15 directories renamed).
  - `data/v3/league-{1,2,3}.json`, `data/setups.json`, `data/v3/close-choices-b.json`, the home page, the league pages and Method.
- **Dashboard:** `tools/league_web.py` display mapping (optional).
- **Paper / Nackgammon report:** display names from `labels.json`; frozen files unchanged.
- **Not touched:** `v3.db`, `smoke/*.db`, `leagues/*.json`, `freeze/*.json`, `positions/nack-paired/results/*`, `release/*`, `nack_paired_score.py` name sets.

## 6. Size

- About 150–250 changed lines of code:
  - snapshot about 20
  - build about 50 (pairing plus stubs plus alias copies)
  - checks about 25
  - home about 5
  - viewer JS about 10
  - dashboard about 10
- One new data file (labels.json, about 80 lines).
- About 70 lines of `setups.json` and about 10 lines of Method text.
- Output: 15 pages, data files and decisions directories renamed, 15 redirect stubs, 15 alias JSON copies (about 0.8 MB).
- About half a day including a preview build and the checks (`python3 tools/site/build.py` with `checks.run`, `close_choices_b_verify.py`).
- One review round with Can on the names in §2, mainly LFM2.5-24B-A2B (low) (the level is sent, but its template ignores it) and the Terra route suffix.

Nothing deployed and no site change made. **To apply after the post; waiting for Can's go.**
