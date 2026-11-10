# job5-preview (backgammon): class row, no-tiers note, Nackgammon classes, one name per model, Same positions

Ümit #4282 (items 1–5), Zeki #4287 (Same positions from the stored E1 answers; Cygnet as a decision model in the
preview), logic #4284 (Cygnet evidence). The branch `job5-preview` is a **candidate only and is not merged**:
merged-in origin/main 39ba32d, head dc0704b (pushed). No model calls, no GPU, no service changes.

## Builds and checks
- **Frozen state:** a copy of the live state, `/tmp/job5-state`, taken 2026-11-10T16:36:11Z right after a finished
  update cycle (data as of 16:20Z, results 0d2b3e49). The live state was only read. Repo inputs that are not in git
  (replay.db, smoke/part-a.json, workspace/learning-pilot) were copied in.
- **Full `build.py --state /tmp/job5-state --no-image`:** origin/main 39ba32d **exit 0**, branch dc0704b
  **exit 0**, which includes checks.run and the new old-name check (logs `job5-backgammon-preview/build-*.log`).
- **Numbers unchanged:** all 2,400 files under data/ and decisions/ (JSON and .json.gz) hold the same numbers in
  both builds. The one exception is data/manifest.json, whose file byte sizes change because the names change. On
  the pages (`numbers.txt`), the number tokens differ only in:
  - the results hash in the version line;
  - the digits of names: "Cygnet (Gemma 4 12B)" is now "Cygnet";
  - the download sizes and hashes on Data;
  - the new Same positions panel (home);
  - "League 1/2/3 group" (Nackgammon).

  On Leagues, Cygnet's rows move from the chat lists to the decision lists, with the same values.
- **Feed:** bench-scores.json has the same rows and numbers. Two things change: the row 'DeepSeek V4.1 Flash (low)'
  is now 'DeepSeek-V4.1-Flash (low)', and Cygnet's kind is now decision.
- **Screenshots** (Chromium, light, 1280 and 375 px; `mailbox/job5-backgammon-preview/`, untracked):
  `leaderboard-{1280,375}.png`, `leaderboard-same-positions-{1280,375}.png`, `nackgammon-{1280,375}.png`. No page
  scrolls sideways in any shot. The script is `shots.py`; the numbers comparison is `numbers.py`.
- **Live site note:** at 16:36Z the live page (zekiworks.github.io/analysis/backgammon/) did not yet show the
  Class row from main (no "Tiny" anywhere in its HTML), while a build of main has it. Possibly a deploy lag; I did not
  investigate.

## 1. Class row against the other sites (differences only)
- **Keys:** ours match Logic & Math's exactly: Class: All · Tiny · Small · Medium · Large · Efficient · Workhorse ·
  Flagship · Undisclosed, with ids tiny … undisclosed. Reading calls its row **"Size:"** and has only All · Tiny ·
  Small · Medium · Large · Undisclosed, with no price classes.
- **Rule line under the keys:** Logic & Math adds "Undisclosed: neither a disclosed size nor a list price." Ours
  stops after "Flagship over $3." and gives the Undisclosed definition only on About.
- **About page:** our list "class: All · Tiny · Small · Medium · Large · Efficient · Workhorse · Flagship" leaves out
  Undisclosed, although the key is on the row (hidden while it is empty).
- **Hiding empty keys:** both sites hide them in JS, so all keys are present in the static HTML of both. I did not
  check the hiding in a browser on the other sites.
- No change made for item 1 (report only).

## 2. League leaderboard: # and the not-paired note
Kept: # (the rank among all models) and the approved note "Leagues played different positions; close scores across
leagues need not mean a real difference." Added after it, under the table: "# is the rank only, with no tiers: a
tier needs a paired test (McNemar, Holm) over positions every model answered, and each league played its own
positions, so models in different leagues never answered the same ones. Same positions (preview) has tiers: there
every model answered the same 200 positions." (`story.NO_TIERS`).

## 3. Nackgammon: class names instead of 'frontier' / 'workhorses'
The paired test's groups are not classes: under Method §10.14 each group is the set of setups from one original
league. The table below shows that the groups mix classes. So:
- **Under each setup's name** (every table, and the chart tooltips) the page now shows its **class**, taken from
  `P.model_class` (the leaderboard's Class row; nothing typed by hand), then its group. Example: "Medium · League 2 group".
- **The groups** are renamed for display: decision models → **League 1 group**, workhorses → **League 2 group**,
  frontier → **League 3 group**. This applies to the comparison names ("League 1 group − League 2 group"), the
  scorer's group notes, the additions note, the chart legend and the home-page finding. The data file keeps its group
  ids, and the numbers are unchanged. 'frontier' and 'workhorses' no longer appear in the page text.
- Not changed: the Method page's verbatim §10 pre-registration still says "Workhorses" and "Frontier", because it is
  the frozen spec. The chart colours are still by group.

Old group → each member's new class (`P.model_class`):

| Old group | Setup → class |
|---|---|
| decision models (→ League 1 group) | Fastino GLiDE v1.2 Medium; Fastino GLiDE Efficient (added); Liquid d1-ultra Efficient (added); Jev 1.13.0 Efficient; GPT-6 Luna (Decisions API) Efficient; Celeris-1 Decision Efficient; Perplexity Decider 27B v1.1 (local GPU) Medium; Cygnet Small; SubQ Snap Preview Efficient; Inception Mercury Decide Efficient; Winnow-12B Small; Perplexity Decider 27B v1.2 (local GPU) Medium; Perplexity Decider Flash v1.2 Tiny; Open-Jev 27B v1.1 Medium |
| workhorses (→ League 2 group) | GPT-6.1 Sol (high) Workhorse; GPT-6.1 Sol (low) Workhorse; Claude Sonnet 5.5 (low) Workhorse; Gemini 3.8 Flash (low) Workhorse; Gemma 4 31B (on) Medium; DeepSeek-V4.1-Flash (off) Large; Qwen3.8-27B (off) Medium; LFM2.5-24B-A2B (on) Medium; LFM2.5-24B-A2B (off) Medium |
| frontier (→ League 3 group) | Claude Fable 5.1 (high) Flagship; GPT-6 Astra (medium) Flagship; Grok 4.7 (high) **Workhorse** (added) |
| no group (exploratory) | GPT-6.1 Terra: no class (not in model_params.json); Gemini 4 Argon (low) Workhorse |

So the old "workhorses" group holds 4 Workhorse, 4 Medium and 1 Large setup, and the old "frontier" group holds one
Workhorse-class setup (Grok 4.7). This is why the groups cannot simply take a class name.

## 4. One name and one type per model
Display names are in `content/labels.json` → `models` (old model name → feed name, with the feed evidence).
`common.label` shows `<model>` and `<model> (<setting>)` under the new name everywhere: the computed state, the
content tables keyed by model (params, prices, release months, identity, Nackgammon types, improve planned rows) and
the text of every page (`common.shown_names_html` in `pages.layout` and the league fragments; `<code>`/`<pre>` are
left alone). setups.json keys, slugs, URLs and data ids are unchanged: `setup_slug` maps back to the recorded name.
In the data files, old names stay only as aliases. **The build fails** when any page outside the frozen archive/ and
results/ shows an old model name (`checks.old_model_names`). bench_scores now uses the shown names, so its
FEED_NAMES list is reduced to the rows that need a note (setting or route) plus the Decider v1.2 checkpoint
(`FEED_ROWS`, `CHECKPOINTS`).

| Old (site) | New (site, feed) | Feed evidence |
|---|---|---|
| Base Labs Mammoth-1 | Mammoth-1 | Logic & Math, Reading 'Mammoth-1' |
| Base Labs Elephant-1 | Elephant-1 | Logic & Math, Reading 'Elephant-1' |
| Cygnet (Gemma 4 12B) | Cygnet | Logic & Math, Reading 'Cygnet' |
| Decider v1.2 27B | Perplexity Decider 27B v1.2 (local GPU) | Reading's own name, same route (self-hosted) |
| Decider v1.1 27B | Perplexity Decider 27B v1.1 (local GPU) | Reading 'Perplexity Decider 27B v1.1' is the API; ours ran on our GPUs, so a route suffix |
| Decider Flash v1.2 | Perplexity Decider Flash v1.2 | Logic & Math, Reading |
| Mercury Decide | Inception Mercury Decide | Logic & Math, Reading |
| GPT-6 Luna | GPT-6 Luna (Decisions API) | Reading (not its 'GPT-6 Luna (chat API)') |
| Fastino GLiDE v1.2 (local) | Fastino GLiDE v1.2 | Logic & Math, Reading: the same self-hosted route, so no suffix |
| DeepSeek V4.1 Flash | DeepSeek-V4.1-Flash | **Decision for Ümit:** spelled as Logic & Math spells it; Reading calls it 'DeepSeek-V4.1-Flash, first release' |
| DeepSeek V4.1 Flash 1017 | DeepSeek-V4.1-Flash 1017 | Logic & Math |
| MiniMax M3.1 Flash | MiniMax-M3.1-Flash | Logic & Math, Reading (smoke row) |

Left as they are (not in either feed, or already identical): Qwen3.8 Flash, LFM2.5-24B-A2B, GLM-5.3-Flash NVFP4 (a
quantization suffix: Logic & Math's 'GLM-5.3-Flash' is a different setup), Drex 2.0 (local) (a route suffix: ours on
our GPU, theirs the API), and every other leaderboard name, which already equals the feeds'. "Earlier name" on a model
page now shows only the 28 Oct effort renames, written with the model's new name.

### Cygnet: chat or decision (for Ümit)
| Where | Type today (main) | Evidence |
|---|---|---|
| Leaderboard row, Leagues, model page, settings line | chat | setups.json league-1 'Cygnet (Gemma 4 12B)': model_type "chat model, answer-letter probabilities"; notes: "Google's gemma-4-12B-it behind a server that labels the options with letters and reads the letter probabilities"; reasoning "none (letter read directly)" |
| v1 set | chat | setups.json v1-set 'Cygnet': the same type; provider "our GPUs (letter-reading server)" |
| bench-scores feed (ours) | chat | kind from the setups.json type |
| Nackgammon | type chat, but in the "decision models" group (original League 1) | nack_section (group by league) |
| Did they improve? (planned row) | decision | content/improve_planned.json: group "decision", "not tested: excluded (#3111)" |
| Logic & Math, Reading feeds | decision | 'Cygnet' kind decision; logic #4284: a decision runner behind the cygnet-recipe shim 3cf591c, Gemma 4 12B IT on vLLM, per-option probabilities |
| model_params.json | (size) | google/gemma-4-12B-it at the revision cygnet-recipe serves, unchanged ("no fine-tuning"), card 11.95B |

**In the preview:** following Zeki #4287, both Cygnet entries in setups.json are "decision model" (all three sites run
the cygnet-recipe letter-probability server, #3899/#4284). On backgammon this is a **type change** for Ümit to see:
Cygnet moves from the Chat to the Decision view (class Small) and into the decision lists of Leagues; its rank and
numbers are unchanged. The choice stays Ümit's.

## 5. Same positions
**Prompt check:** E1's prompt and setting **equal the league row's**, so the view is called "Same positions". The check
looked up the league prompt of the same League 2 turn (STATE/prompts.db) verbatim in E1's stored requests:
- Chat models: about 134 of 200 positions match exactly. About 13 more differ only in the final request of a split
  play list, which picks among the model's own group winners, so it is expected to differ. Gemini 4 Argon has 3 more
  where an invalid answer cut the split short. No other differences.
- Drex Max 1.1 and SubQ Snap 1.1: 44 positions can be compared and all 44 match; the other turns are stored in the
  chat format.
- 9 positions have no stored league prompt.
- Spec, provider, effort and request options equal the league player's for all 12 models.
- SubQ Snap 1.1's two arms have identical E1 answers (0 of 200 differ). Drex Max 1.1 has one arm.

**Preview view** (leaderboard key "Same positions"; data in `content/same_positions_preview.json`, computed by
`tools/site/same_positions_publish.py` from smoke/improve/*.db):
- **Correct** = the engine's best play: the play loses under 0.001 against GNUbg 2-ply's best (test_set.json). Invalid
  answers count as wrong.
- **Tiers:** exact two-sided McNemar test on every pair (66 pairs), Holm-adjusted at 0.05. Tier 1 is the model with
  the most correct answers plus every model not significantly different from it; then the same for the models left.
  23 of the 66 pairs differ.

| Tier | Model | Correct of 200 | Invalid | League # |
|---|---|---|---|---|
| 1 | Claude Fable 5.1 (high) | 106 | 0 | 3 |
| 1 | Gemini 4 Argon (high) | 101 | 45 | 2 |
| 1 | DeepSeek-V4.1-Flash (low) | 100 | 1 | 6 |
| 1 | Gemini 3.8 Flash (high) | 97 | 0 | 9 |
| 1 | Grok 4.7 (high) | 97 | 0 | 7 |
| 1 | Gemma 4 31B (on) | 92 | 0 | 11 |
| 1 | Kimi K3.1 Pro (off) | 85 | 0 | 10 |
| 1 | GLM-5.3 (low) | 83 | 0 | 16 |
| 2 | Qwen3.8-27B (low) | 78 | 0 | 15 |
| 2 | Drex Max 1.1 | 67 | 0 | 22 |
| 2 | Qwen3.8 Flash (off) | 66 | 0 | 20 |
| 2 | SubQ Snap 1.1 | 60 | 0 | 31 |

Gemini 4 Argon's 45 invalid answers count as wrong, so its 101 is a floor. Claude Sonnet 5.5 (high) has only 111 of
200 E1 answers stored, so it is not in the tiers.

### Cost and time to ask the 26 missing ranked models (read-only estimate)
Each model gets the 200 positions, one position per request, with the league prompt.
- **Cost per decision:** from v3.db league turns.cost_usd (list price × tokens; no billed figures exist for these
  models). Fastino GLiDE has no stored cost, so it is input price × mean league input tokens.
- **Time:** the median league seconds per decision × 200, one request after another.
- Subscription models cost $0 extra but use quota. Local models cost $0 in API fees but need a GPU (server script
  shown).

| League # | Model (old name in the estimate) | Route | GPU (server) | $ / decision (source) | $ for 200 | Median s / decision (league n) | Hours for 200 | Available now |
|---|---|---|---|---|---|---|---|---|
| 1 | GPT-6 Astra (high) | subscription | no | 0.00000 ($0 marginal; list-equivalent $0.0594) | 0.000 | 9.83 (1,489) | 0.55 | no: ChatGPT subscription quota until 13 Nov |
| 4 | GPT-6.1 Sol (high) | subscription | no | 0.00000 ($0 marginal; list-equivalent $0.0142) | 0.000 | 10.39 (3,362) | 0.58 | no: ChatGPT subscription quota until 13 Nov |
| 5 | Claude Opus 5.5 (high) | subscription | no | 0.00000 ($0 marginal; list-equivalent $0.0361) | 0.000 | 6.33 (2,092) | 0.35 | no: Claude subscription limit |
| 8 | Claude Sonnet 5.5 (high) | subscription | no | 0.00000 ($0 marginal; list-equivalent $0.0201) | 0.000 | 6.49 (3,065) | 0.36 | no: Claude subscription limit; 111/200 E1 stored |
| 12 | Liquid d1-ultra | hosted API | no | 0.00014 (turns.cost_usd) | 0.029 | 0.24 (5,363) | 0.01 | yes |
| 13 | Mammoth-1 | local GPU | yes (baselabs_server.py) | 0 | 0.000 | 0.72 (2,021) | 0.04 | yes |
| 14 | Drex Max v1 | local GPU | yes (drex_max_server.py) | 0 | 0.000 | 0.68 (2,148) | 0.04 | yes |
| 17 | REAX 1.3 | local GPU | yes (reax13 serve.py) | 0 | 0.000 | 1.74 (1,998) | 0.10 | yes |
| 18 | Fastino GLiDE | hosted API | no | 0.00015 (list price × mean input tokens) | 0.031 | 0.45 (5,452) | 0.02 | yes |
| 19 | Jev 1.13.0 | hosted API | no | 0.00016 (turns.cost_usd) | 0.033 | 0.21 (3,296) | 0.01 | yes |
| 21 | Jev 1.14.0 | hosted API | no | 0.00017 (turns.cost_usd) | 0.034 | 0.20 (5,002) | 0.01 | yes |
| 23 | Fastino GLiDE v1.2 | local GPU | yes (glide-v12.sh) | 0 | 0.000 | 1.65 (3,493) | 0.09 | yes |
| 24 | Drex 2.0 | hosted API | no | 0.00026 (turns.cost_usd) | 0.052 | 0.42 (1,937) | 0.02 | yes |
| 25 | Perplexity Decider 27B v1.2 (local GPU) | local GPU | yes (decider-v1.2.sh 27b) | 0 | 0.000 | 1.02 (3,399) | 0.06 | yes |
| 26 | Celeris-1 Decision | hosted API | no | 0.00015 (turns.cost_usd) | 0.030 | 0.17 (5,137) | 0.01 | yes |
| 27 | Elephant-1 | local GPU | yes (baselabs_server.py) | 0 | 0.000 | 0.26 (2,044) | 0.01 | yes |
| 28 | Clef | local GPU | yes (clef.sh) | 0 | 0.000 | 1.33 (4,845) | 0.07 | yes |
| 29 | Cygnet | local GPU | yes (cygnet.sh) | 0 | 0.000 | 0.47 (3,501) | 0.03 | yes |
| 30 | Perplexity Decider 27B v1.1 (local GPU) | local GPU | yes (decider.sh) | 0 | 0.000 | 0.92 (3,246) | 0.05 | yes |
| 32 | SubQ Snap Preview | hosted API | no | 0.00019 (turns.cost_usd) | 0.038 | 0.24 (3,760) | 0.01 | yes |
| 33 | GPT-6 Luna (Decisions API) | hosted API | no | 0.00033 (turns.cost_usd) | 0.067 | 0.23 (2,679) | 0.01 | **no: no OpenAI API credit** |
| 34 | Winnow-12B | local GPU | yes (winnow.sh) | 0 | 0.000 | 1.71 (3,310) | 0.09 | yes |
| 35 | Inception Mercury Decide | hosted API | no | 0.00007 (turns.cost_usd) | 0.014 | 0.49 (3,141) | 0.03 | yes |
| 36 | LFM2.5-24B-A2B (on) | local GPU | yes (lfm25-24b.sh) | 0 | 0.000 | 302.87 (4,025) | 16.83 | yes |
| 37 | Perplexity Decider Flash v1.2 | local GPU | yes (decider-v1.2.sh flash) | 0 | 0.000 | 0.55 (3,212) | 0.03 | yes |
| 38 | Open-Jev 27B v1.1 | local GPU | yes (open-jev.sh) | 0 | 0.000 | 1.74 (3,256) | 0.10 | yes |
| | **Total: 26 models** | 9 hosted, 4 subscription, 13 local | **13 need a GPU: 17.5 GPU hours** | | **$0.33** hosted ($0.26 for those available now) | | **19.5 h** one after another | **5 unavailable now** |

- **Unavailable now:** GPT-6 Astra (high) and GPT-6.1 Sol (high) (ChatGPT quota until 13 Nov), Claude Opus 5.5
  (high) and Claude Sonnet 5.5 (high) (Claude subscription limit), GPT-6 Luna (no OpenAI credit).
- LFM2.5-24B-A2B (on) takes 16.8 of the 19.5 hours, at a league median of 303 s per decision.
- Three local servers (Mammoth/Elephant, Drex Max v1, REAX 1.3) are not under tools/v3/servers; their scripts are
  named in the table.
- The ranked list was read from the built leaderboard.

## Files (branch)
tools/site: common.py (label, shown_names_html, setup_slug), content/labels.json (models), content/setups.json (Cygnet
type), content/families.json (Perplexity/Inception prefixes), pages.py, home.py, story.py (NO_TIERS, Same positions
view), nack_section.py, nack_paired_verify.py (shown group names), bench_scores.py (FEED_ROWS), checks.py
(old_model_names), decisions_export.py (v1 under shown names, old slugs), improve_page.py, starting_groups.py,
method.py, build.py (load_setups through the shown name), content/same_positions_preview.json,
same_positions_publish.py (the read-only computation; it reads the live state and smoke/improve and writes /tmp/job5).
**Not run:** nack_paired_verify. On origin/main it already reports 118 mismatches, mostly the suite-bar
'decision-models' string, so it is not a gate.

## Update 1 (Ümit #4313): Tier column on the league leaderboard
Branch head after this update: 754718f (pushed, not merged). League play stays the default view, and the Same
positions view is unchanged.
- **New column "Tier (same positions)"** after the four wide columns. It shows each ranked row's tier from the Same
  positions computation: 8 rows in tier 1 and 4 in tier 2. The cell is **empty** for models not in that computation
  (the 26 not asked, and Claude Sonnet 5.5 with 111/200), for other-settings rows and for programs. It is never a guess
  and never a dash.
- **One line under the table, exactly:** "Rank comes from league play; tier comes from the same 200 positions for
  every model."
- The no-tiers sentence in the note below now begins "# is the league rank, which has no tiers: …" and ends "The Tier
  column and Same positions (preview) come from 200 positions every model there answered."
- **Phone:** like the other wide columns, the column is hidden below 900 px. The row's details box then shows "Tier
  (same positions) N" (12 boxes).
- **Fit at 1280:** the wide column heads now wrap; their cells do not. At 1280 the table fits its box (1,056 px wide
  in a 1,056 px box). Without the wrap it was 67 px too wide and the Tier column was cut off.
- **Unchanged by this update:**
  - At 375 the table is 340 px in a 328 px box, the same as on origin/main.
  - At 900 the table still scrolls inside its box: 51 px too wide (on main it is 90 px too wide).
- **Checks:** branch build exit 0. All 2,400 data and decision files hold the same numbers; data/manifest.json still
  differs only in file byte sizes. On the home page, the new number tokens are the 12 tier cells plus the 12 detail
  lines. Screenshots in `job5-backgammon-preview/` are refreshed at 1280 and 375, with no sideways page scroll.
