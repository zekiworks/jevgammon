# Close choices, stage B: positions, method and estimate

Oct 24, 2026 · for Ümit · request: `mailbox/Close choices - request 2026-10-24.md`, section B. Stage B **has not run**. **Updated Oct 24 with Can's decisions (section 5): 8 teams incl. Gemma 4 31B (on) on spark3; no stage B call until the ladder settles. Second update (19:40 UTC): positions refrozen from `new.jsonl`, stratified by risk class (v2 freeze); settings rule; estimate redone for the new 100.**

**No model requests were made for this note.** That means no prediction call, no play call, no smoke test, probe or preflight, and no local model server started. Here is what I did:

- read `v3.db` read-only (`file:v3.db?mode=ro`) to measure tokens and latency;
- read the position files and froze 100 rows from them;
- described the legal plays of the frozen positions offline with `tools/site/describe.py` (pure Python, no engine, no model);
- ran three web searches for documented default temperatures (sources in B.6).

Nothing was merged or deployed. The `brief-2026-10-24` worktree was not touched.

The scoring rules are fixed in **Method §9.9 "Stage B scoring (B4)"**: `tools/site/content/method-spec-2026-10-24.md` on branch `brief-2026-10-24`, commit `be887d3` ("Method §9 close choices …, fixed 2026-10-24 15:15 UTC before computing"). This plan cites that section and does not restate it differently.

## 1. Positions: v2 freeze (supersedes the 20-per-phase freeze)

### Which set and why

- **Can's decision (2026-10-24): take the 100 from `positions/new.jsonl`, if the Cup teams also answer that set in the shared-position run.**
- **Checked: they do.** The shared-position run gives every setup, Cup teams included, the same base of 2,700 decisions: the 2,000 shared standard positions (`positions/v1.jsonl` 1,000 + `positions/new.jsonl` 1,000, prompt `bg-v2`), 500 Nackgammon and 200 opening controls.
  - `mailbox/Shared positions - review and estimates 2026-10-24.md`: "Base per setup: 2,700 decisions (2,000 standard + 500 Nackgammon + 200 control)", and its Cup scenario table prices "Base 2,700" for each of the six Cup setups.
  - `freeze.json` hashes `positions/new.jsonl` (sha256 `ad06427c…`, 1,000 rows), the file `tools/v3/build.py` writes (1,000 positions, 200 per phase, 2–25 legal plays, prompt `bg-v2`).
  - So `new.jsonl` is half of the shared standard set the Cup teams answer; it is not the whole set (the other half is `v1.jsonl`).

### Rule, fixed in Method before selection

- Method §9.10 on `brief-2026-10-24`, commit `c265db3` (19:22:31 UTC; header time fixed in `9140007`), before the engine values were computed and before selection.
- **Excluded:** fewer than 2 legal plays (0 of 1,000).
- **Position class at margin 0.001** by the site's rule: hitting rolls as shown with each option; losses from GNUbg 1.08 2-ply, cubeless, the existing settings (`tools/v3/score.py evaluate`), run on CPU (nice 19, 8 processes, 16 s) into `~/.local/state/bg-site/shared/new-2ply-s0..s7.db`.
- **Targets:** 40 Risk pays, 40 Safety pays, 20 No trade-off, evenly over the five phases (8/8/4 per phase). Per (class, phase) cell, the ids with the smallest `sha256("close-choices-b-v2-2026-10-24:" + id)`. A short cell's places go to the other phases of the same class, in phase order.
- Script: `tools/site/close_choices_b_freeze.py` (branch).

### Result

- `positions/close-choices-b-v2.jsonl` (branch): **100 rows, sha256 `88bc3904595c6dccc3f6fe015e865b7b23e3ed81b9be1ad8d1e7efcf5848410c`**, byte-identical to the source lines. Record `freeze/close-choices-b-v2.json` (branch), frozen 2026-10-24T19:23:47Z.
- **The list of 100 ids and the hash are published in Method §9.11** (branch commit `60bebef`), before any stage B call.
- Race and bear-off positions have no contact, so all 400 are No trade-off. The Risk pays and Safety pays places of those phases went to opening, contact and holding by the shortfall rule:

| Class | Opening | Contact | Holding | Race | Bear-off | Total |
| --- | --- | --- | --- | --- | --- | --- |
| Risk pays (eligible) | 14 (124) | 13 (46) | 13 (34) | 0 (0) | 0 (0) | 40 |
| Safety pays (eligible) | 14 (73) | 13 (128) | 13 (142) | 0 (0) | 0 (0) | 40 |
| No trade-off (eligible) | 3 (3) | 5 (26) | 4 (24) | 4 (200) | 4 (200) | 20 |

- Opening No trade-off has only 3 eligible positions; its fourth place went to contact.
- Options: 2–25 per position, **1,204 in all** (the old freeze had 1,065). No decision is split into groups.
- **The earlier freeze** (`freeze/close-choices-b.json`, `positions/close-choices-b.jsonl`, 20 per phase from v1 + new) is **superseded**. Both files are kept on main, and the record is marked superseded.

### Offline preview: which features can differ at all

This was computed with `describe.py` over every legal play. It is a property of the positions, not a result.

| Feature | Risk pays (40) | Safety pays (40) | No trade-off (20) |
| --- | --- | --- | --- |
| Hitting risk | 40 | 40 | 0 (by definition) |
| Making a point | 22 | 25 | 6 |
| Race (pip counts) | 13 | 14 | 0 |
| Prime | 24 | 22 | 13 |

- **7 positions** (all No trade-off) where no feature can differ. Any repeat set there has an empty observed set.
- The observed set O can never contain a feature that cannot differ in that position.

## 2. Cup teams, as currently documented

### Count: 8 or 9 (open question, please decide)

- `mailbox/backgammon-ladder-cup.md` line 7: "This file replaces all earlier Champions Cup plans: the 9-team format, …". Its section "Teams (8)" defines eight teams:
  - the top 2 models of each league;
  - plus the two 3rd-placed models with the lowest error rates.
- `mailbox/backgammon-ladder-cup - response.md` (Oct 23) confirms that format.
- Your earlier brief said "9 Cup teams". The shared-positions review (decision D2) asked whether that meant the 8-team Hype Cup or a separate nine-setup list. That question is still open, and I found no nine-setup list anywhere in `mailbox/`, `workspace/` or `tools/ladder.py`.
- **Decided (Can, 2026-10-24): 8 teams**, the Cup's documented format. No ninth team.

### The roster is not final

The ladder has no steady state yet.

- Round 1 is done (`Ladder round 1 - log.md`).
- Round 2 waits for Can (`Ladder round 2 - request.md`, 12:44 UTC). It would move:
  - Fastino GLiDE from League 1 to League 2;
  - LFM2.5-24B-A2B (on) from League 2 to League 1;
  - GPT-6.1 Sol (high) from League 2 to League 3;
  - Grok 4.7 (off) from League 3 to League 2.
- The Cup is drawn only at a steady state. The list below is a **dated snapshot, not a roster**: the tables of the round-2 request (Oct 24, 12:44 UTC), with the Cup rule applied, the same as scenario 4.2 of the shared-positions review.
- **Decided (Can, 2026-10-24): wait for the ladder to settle. No stage B call until then.** The teams are taken from the Cup roster at the steady state, so Table B1 may still change; any one-letter replacement is priced in Table B3.

### Who counts as "one-letter"

A setup whose recorded answers are one option letter with no probability distribution: `turns.probability_source = choice_only` on every decision. This follows the request's "decide by the content of the record".

### Table B1: snapshot Cup teams (8)

| Seed | Team | League now | Record (`probability_source`, all decisions) | One-letter? | Model id | Setting | Provider / route |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GPT-6.1 Sol (low) | League 3 #1 | choice_only 3,270/3,270 | **yes** | `openai/gpt-6.1-sol` | reasoning effort low | ChatGPT subscription |
| 2 | GPT-6 Astra (on) | League 3 #2 | choice_only 1,385/1,385 | **yes** | `openai/gpt-6-astra` | reasoning effort medium (model default) | ChatGPT subscription (Codex backend) |
| 3 | GPT-6.1 Sol (high) | League 2 #1 (League 3 after round 2) | choice_only 2,381/2,381 | **yes** | `openai/gpt-6.1-sol` | reasoning effort high | ChatGPT subscription |
| 4 | Gemini 3.8 Flash (low) | League 2 #2 | choice_only 2,382/2,382 | **yes** | `antigravity/gemini-3.8-flash` (Antigravity id `gemini-3.8-flash-low`) | thinking level low | Google Antigravity subscription |
| 5 | Fastino GLiDE | League 1 #1 model (GNUbg weak ranks first but never enters) | decision 2,193/2,193 | no (decision model, full probabilities) | `fastino` | — | Fastino hosted API |
| 6 | Jev 1.14.0 | League 1 #2 model | decision 2,099/2,099 | no (decision model) | `jev/jev-1.14.0` | — | TypeSafe API |
| 7 | Claude Opus 5.5 (on) | League 3 #3, error rate 14.0 | choice_only 1,559/1,559 | **yes** | `anthropic/claude-opus-5-5` | effort high (default, adaptive thinking) | Claude subscription |
| 8 | Gemma 4 31B (on) | League 2 #3, error rate 19.2 | logprobs 3,761/3,761 | no by record (letter probabilities) | `local/gemma-4-31B-it` | thinking on (template default) | own GPU, vLLM fp8 |

The third 3rd place, Jev 1.13.0 (League 1, error rate 34.5), drops out.

**Five one-letter teams in this snapshot:** GPT-6.1 Sol (low), GPT-6 Astra (on), GPT-6.1 Sol (high), Gemini 3.8 Flash (low) and Claude Opus 5.5 (on). **Stage B teams in this snapshot: these five plus Gemma 4 31B (on), six in all** (GLiDE and Jev are decision models and cannot answer the prediction).

- **Decision models (GLiDE, Jev):** they only pick among options and cannot answer a free-text prediction question, so they are not in stage B.
- **Gemma 4 31B (on):**
  - **Label fixed (branch `brief-2026-10-24` only):** `tools/site/content/setups.json` labelled Gemma 4 31B (on) and (off) "chat model, one letter", but their records hold letter log-probabilities. Both now read "chat model, answer-letter probabilities", confidence source "letter probability", as for the other letter-readout setups.
  - **Decided (Can, 2026-10-24): included**, on the Gemma server already running on spark3. See "Gemma 4 31B (on): device and pre-run check" in section 4. It is in stage B as a Cup team that can answer the prediction question; by its record it is not one-letter, and the report says so.

## 3. Method for B

The scoring rules are Method §9.9 (cited above). B1–B7 are applied as written in the request.

### B1. Prediction call

One separate call per team and position. It shows the same system prompt and the same position text and options, in the same order, as the play call (`bg-v2` letter prompt, `src/players/prompt.rs` `letter_user`). In place of the letter instruction it ends with the request's question, verbatim:

> If you answered this position again independently, on which features might your chosen plays differ: hitting risk, making a point, the race or the prime? You may name several, or none.

- **Format line, approved by Can on 2026-10-24** (the question itself stays verbatim): "Answer with the features you name, using only these words: hitting risk, making a point, the race, the prime; or the single word none."
- **Constraint:** every one-letter route already constrains the letter: ChatGPT, Claude and xAI with a JSON schema (`src/players/llm.rs` `letter_schema`), Gemini with an enum. The prediction answer is constrained the same way. It becomes a JSON list of unique items from the four names, and an empty list means "none".
- **Parsing and validity:**
  - Each named item must map to exactly one of the four features. Duplicates collapse.
  - "none" alone, or an empty list, is a **valid empty set**.
  - "none" together with a feature, an unknown word, an empty reply, a refusal or an error is **invalid**.
  - No repair, no re-ask.
- **Not built yet:** the runner has no prediction request. After approval it is built and unit-tested offline (no model call), with the rendered prompt hashed before any call.

### B2. Five play calls

- **Command:** `jevgammon ask --positions positions/close-choices-b-v2.jsonl --repeats 5` with each team's league settings JSON unchanged (`players.settings`), into a separate answers database, never `v3.db`.
- **Prompt:** `bg-v2` from each row, with no `--prompt-version` flag (the review's warning).
- **Independence:** each call is a fresh, stateless request. The prediction is never shown to the play calls.
- **Same option order in all five:**
  - `ask` computes the order from the frozen option-order seed (`seeds.json`: 1190975713392774006) and the position key. It does not depend on the repeat number (`src/ask.rs`, `Position::order`).
  - It also refuses a row whose stored `option_order` differs. So each position has one seeded order, shared by its prediction call and its five play calls.
- **Validity of a play call:** one option letter that the runner parses. An invalid answer gets the runner's random fallback play, and an HTTP error is a failure. Both are invalid for stage B, with no re-ask after the run (in-call network retries for HTTP 408/429/5xx stay as in the leagues).
- **Group splitting:** none. At most 24 legal plays, against the limit of 26.
- **Clock:** none, as in the leagues.

### Settings and temperature (Method §9.10, Can's decision 2026-10-24)

- **Each setup keeps its league settings exactly:** temperature (or none sent), reasoning setting, prompt version and format, max tokens, provider route. Nothing is tuned for stage B.
- **Temperature** is recorded where known (the value sent, or the documented default) and as **"not disclosed"** where not.
- **Deterministic setups:** a setup that gives five identical answers on every scored position is reported as deterministic on these positions. Settings are never changed to create variation.

| Team(s) | What our runner sends | What is recorded | Source |
| --- | --- | --- | --- |
| GPT-6.1 Sol (low, high), GPT-6 Astra (on) | nothing (setups.json "not sent (API default)") | **not disclosed** for the ChatGPT subscription route | OpenAI's API docs describe reasoning models' temperature as fixed at its default of 1, per search summaries of platform.openai.com pages (checked 2026-10-24). Not verified for these models or this route, so not claimed |
| Claude Opus 5.5 (on) | nothing | **1.0, Anthropic's documented Messages API default** (newer models accept only 1.0) | [Messages API reference](https://platform.claude.com/docs/en/api/http/beta/messages/create), checked 2026-10-24 via web search; the subscription route uses the same Messages API |
| Gemini 3.8 Flash (low) | `temperature: 1.0` (`src/players/llm.rs` line 463, every Gemini/Antigravity call) | **1.0, Google's documented default** | [Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3) (keep the 1.0 default) and the [text generation page](https://ai.google.dev/gemini-api/docs/text-generation) (3.6+ and 4 ignore custom values), checked 2026-10-24. Proposal: keep the league call unchanged, since the value sent equals the default |
| Gemma 4 31B (on) | `temperature: 1.0` (our own vLLM server: we are the provider) | 1.0 | `llm.rs` lines 312, 338 |

The Google and Anthropic default values (1.0) are documented in their docs as linked above. Whether each applies to the specific subscription route is an inference, labelled as such on the page.

### B3. Observed feature set O

These are the §9.5 features, read from the option description of each selected play (`describe.py`, exactly as the model was shown it):

- hitting risk = the opponent's hitting rolls;
- making a point = the set of newly made points;
- race = both players' pip counts;
- prime = the longest prime length.

O holds every feature on which any two of the five selected plays differ.

### B4. Scoring

As in Method §9.9:

- **P (predicted set):** a valid "none" is the empty set. A missing, invalid or failed prediction is not a prediction.
- **Scored positions:** a position is scored only when its prediction and all five play responses are valid. Excluded positions are reported separately, by reason (invalid prediction, failed prediction, invalid play, failed play).
- **Primary score:** exact agreement, 1 if P = O, else 0. An extra predicted feature is a mismatch.
- **Secondary score**, declared secondary: |P ∩ O| ÷ |P ∪ O|. It is 1 when both sets are empty and 0 when exactly one is empty.
- **Baseline:**
  - predictions shuffled across positions within the same setup and phase;
  - **1,000 seeded permutations** (`analysis.boot` seeds);
  - scored the same way, with the same conventions;
  - a (setup, phase) group with one scored position keeps its own prediction.
- **Reported per setup, for both scores:** observed mean, baseline mean, the baseline's 2.5–97.5 percentiles, and the share of shuffles scoring at least the observed mean.

### B5. Two empty-O cases, reported separately

- (a) The selected play did not change across the five calls.
- (b) The play changed, but the measured features are identical.

Each comes with a count and a denominator per setup.

### B6. Wording limits

- Five repeats are a small sample of one setting on 100 positions. A change, or no change, is not presented as a measure of the model's whole behaviour or of its reasoning.
- Nothing is concluded about inner reasoning or the cause of a choice.
- The offline preview above (9 positions where no feature can differ) is printed next to the results.
- Results are not used to rank setups.

### B8. Site

Stage B results are added to the site separately, only after the experiment is complete. Nothing is added before then, and the stage A pages are unchanged by stage B.

## 4. Cost and time

### How the numbers are built

- **Calls:** 600 per team = 100 positions × (1 prediction + 5 plays). Network retries inside a call are allowed for in the conservative figure (+5%). Nothing is re-asked after the run.
- **Play-call tokens are measured** (redone for the v2 100, 19:40 UTC). They come from each team's scored league decisions in the site snapshot of 12:51 UTC (valid, one request, not grouped), with each decision's position class at 0.001 and phase.
  - **Input** = per-setup linear fit of `input_tokens` on the number of options, applied to the v2 positions (1,204 options).
  - **Output** and **seconds** = the team's league mean in the same (class, phase) cell as each frozen position; a cell with fewer than 20 league decisions uses the class mean. Reasoning tokens are included.
  - The risk-class mix moves output by −1% to +5% against the league mean (Gemini 3.8 Flash (low) 195 vs 187 tokens; Gemma 4 31B (on) 4,040 vs 3,901).
- **Prediction-call tokens are estimated, not measured.**
  - Input = play input + 70 tokens (the question and the format line replace the letter instruction, about 14 tokens; all three are token-count estimates).
  - Output: central = play output + 15; conservative = 2 × play output + 50 (the setup reasons before naming features).
- **Central** = measured play output; **conservative** = play output × 1.5, prediction as above, everything × 1.05.
  - Check: Gemini 3.8 Flash (low)'s antigravity smoke test averaged 292 output tokens (`Reviewed brief 2026-10-24 - status.md`), against 186 in the league and 279 in this conservative case.
- **Money:**
  - **Billed:** API keys only. It is **$0** for every one-letter team, because all run on subscriptions.
  - **API-equivalent:** at list prices, for scale only; it is never spent. Subscriptions cost $0 at the margin but use quota, and the quota limits are **unknown**.
  - **Own GPU:** in hours.
  - An unknown price is "unknown", never $0.
- **Prices:**
  - roster list prices (`players.price`), confirmed against the OpenRouter models API fetched Oct 24, 2026, 10:31–10:40 UTC (shared-positions review, "Price sources");
  - Gemini 3.8 Flash at that fetch's $0.825/$4.125 per M (the roster has $0.75/$3.75);
  - Gemma 4 31B at OpenRouter's $0.20/$0.40, hypothetical, because it runs on our GPU.
- **Time:**
  - central = 6 × the sum over the 100 positions of the cell's mean request seconds ÷ parallel;
  - conservative = central × 1.5 × 1.05;
  - parallel is each setup's configured request limit, as used in the leagues (4; Grok 4.7 (on) 8; Gemma 24 sequences).
  - Latency columns: p50 / mean request / mean total, in seconds.

### Table B2: stage B teams on the v2 100 (snapshot roster)

| Team | Route | League decisions used | Input tok/play call | Output tok/play call (league mean) | Mean s per call | Parallel | Price $/M in / out | API-eq. central | API-eq. conservative | Billed | Time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-6.1 Sol (low) | ChatGPT subscription | 1,009 | 3,209 | 74 (75) | 4.5 | 4 | $2 / $10 | $4.33 | $4.85 | $0 | 11–18 min |
| GPT-6 Astra (on) | ChatGPT subscription | 1,054 | 3,208 | 74 (75) | 4.6 | 4 | $10 / $50 | $21.61 | $24.23 | $0 | 11–18 min |
| GPT-6.1 Sol (high) | ChatGPT subscription | 1,537 | 3,207 | 289 (292) | 10.1 | 4 | $2 / $10 | $5.61 | $6.99 | $0 | 25–40 min |
| Gemini 3.8 Flash (low) | Antigravity subscription | 1,588 | 3,377 | 195 (187) | 3.5 | 4 | $0.825 / $4.125 | $2.17 | $2.59 | $0 | 9–14 min |
| Claude Opus 5.5 (on) | Claude subscription | 1,218 | 4,426 | 433 (440) | 6.5 | 4 | $4 / $20 | $15.88 | $19.93 | $0 | 16–26 min |
| Gemma 4 31B (on) | own server, spark3 (vLLM, 2 requests per play decision) | 1,654 | 10,823 per decision | 4,040 (3,901) | Spark: see below | 24 sequences | ($0.20 / $0.40, hypothetical) | ($2.27) | ($2.98) | $0 | **about 16–26 Spark hours** |
| **Total, 6 teams** | 3 subscriptions + spark3 | | | | | | | **$49.60** (subscriptions) | **$58.59** | **$0** | see below |

**Totals:**

- **Calls:** 3,600 (600 per team: 100 predictions + 500 plays); Gemma's 500 play decisions are 1,000 requests, so 4,100 requests in all. Up to about 5% more with in-call network retries.
- **Tokens (5 subscription teams):** about 10.5 M input; output 0.65 M central, 1.09 M conservative. **Gemma:** 6.5–6.8 M input, 2.43 M output central, 4.04 M conservative.
- **Billed: $0.** API-equivalent (never spent): $49.60 central, $58.59 conservative (ChatGPT $31.55–36.07, Claude $15.88–19.93, Antigravity $2.17–2.59). Gemma at a hypothetical $2.27–2.98.
- **Wall time:** the three ChatGPT teams one after another 48–76 min; Claude 16–26 min and Antigravity 9–14 min side by side. **Gemma on spark3: about 16 h central, 26 h conservative** (output tokens ÷ 43 tokens/s, below), the bound on the run.
- **Quota:** limits unknown. Reference: ladder round 1 used about $185 API-equivalent of subscription capacity in one night without a reported stop.
- [INFERENCE] Gemma's prediction call is one request, not two, so its input estimate is on the high side.

### Gemma 4 31B (on): device and pre-run check (decided 2026-10-24)

**Device change from bariton.** Stage B runs Gemma 4 31B (on) on the Gemma server **already serving on spark3** (`192.168.1.139:8894`, vLLM, model id `gemma-4-31B-it`, `max_model_len` 32,768, logprobs allowed). No bariton GPU is used. Nothing on the Spark is started, stopped or reconfigured. The league setup ran on bariton (RTX PRO 6000) for most of its decisions, and on a DGX Spark (`spark-194d`, not spark3) in some windows (roster device note in `v3.db`). Stage B's device is recorded per decision, and the device note gets this change.

**Settings to verify before any stage-B call** (read-only: the server's `/v1/models` and its launch arguments; no generation), against the league player config (`players.settings` of Gemma 4 31B (on)):

| Setting | League (`players.settings`) | spark3 (to verify) |
| --- | --- | --- |
| Weights | `gemma-4-31B-it`, same checkpoint as in the leagues | model id `gemma-4-31B-it`; checkpoint path and hash to match |
| Quantization | fp8: bf16 checkpoint quantized by vLLM at load; fp8 KV cache | the same flags |
| Chat template | the checkpoint's template; `chat_template_kwargs: {enable_thinking: true}` | the same template file (hash) |
| Reasoning | on (`enable_thinking: true`, template default; no effort knob) | thinking text present in the check below |
| Max tokens | `max_tokens` 24,000 per request | 24,000 sent; prompt (~5.3k tokens per request) + 24,000 fits within `max_model_len` 32,768. The league server's `max_model_len` is to be read and compared too |
| Temperature | 1.0 sent by the runner | 1.0 sent |
| Logprobs | top log-probabilities for the letter readout | allowed (per Can) |

Any mismatch stops the run before any stage-B call, and it is reported here.

**20-request comparison** (the precedent of every earlier Gemma device move, `v3.db` device note: "20 stored League 2 (off) requests replayed there: same top letter 20/20, max |dp| …", and Decider v1.1's move in `Night run - log.md`, rule "same play in at least 19 of 20"):
- **(a) Equivalence, 20 stored League 2 Gemma 4 31B (off) requests** (thinking off, so the letter readout is deterministic enough to compare), replayed from `prompts.db` exactly as sent. **Pass: same top letter in at least 19 of 20.** Reported: max and median |dp|. This checks weights, quantization and chat template.
- **(b) Reasoning on, 20 stored League 2 Gemma 4 31B (on) requests**, replayed the same way. Thinking is sampled at temperature 1.0, so no play-agreement threshold. **Pass: every response has thinking text, a valid letter, and no request cut at 24,000 tokens beyond the league's own rate.** Reported: same play x/20 as information, reasoning tokens, seconds per request.
- These 40 requests are check calls, made only after approval of the run and before any stage-B call. They are not stage-B data.
- **Cost:** local, **$0 billed**. Time on spark3: (a) about 2 minutes (league (off) readouts take a few seconds each); (b) about 20 × 3,900 output tokens ≈ 78k tokens ≈ **0.5 h** batched, up to **7 h** if the server runs them one at a time (3 tokens/s, below).

**Spark hours (estimate).**
- Measured on a DGX Spark in the leagues (`spark-194d`, `v3.db`, Gemma 4 31B (on) decisions in its Spark windows, 94 decisions): about **3 output tokens/s per request** when one request ran at a time (e.g. 3,285 tokens in 1,090 s; 17,512 in 5,824 s), and about **43 tokens/s in total** in the busiest hour (Oct 19, 20:00 UTC: 46 (on) decisions × 3,407 tokens, alongside 714 (off) readouts).
- Stage B output for Gemma on the v2 100: 500 play decisions × 4,040 tokens (the league mean of each position's class and phase cell; measured, mostly bariton) + 100 predictions (estimated as in "How the numbers are built") = **2.43 M tokens central, 4.04 M conservative**.
- At 43 tokens/s in total: **about 16 h central, 26 h conservative**, with requests sent in parallel (the server's 24 sequences). One at a time it would take weeks, so the run sends in parallel.
- [INFERENCE] spark3 is assumed to be the same hardware class (GB10) as `spark-194d`; its real throughput is unmeasured, and so is any load from other work on it. Check (b) measures it before the run, and this estimate is updated then.
- Billed $0; electricity and the Spark's time are not priced (unknown, not $0).

### Table B3: unit cost of every other one-letter setup in Leagues 2 and 3

Computed for the superseded 20-per-phase freeze (1,065 options), not redone: on the v2 100 (1,204 options) input is about 3–5% higher, and output moves by the class mix as in Table B2.

Use it if the roster changes (round 2, a steady state, or a ninth team). Same method as Table B2, 600 calls each, billed $0 for all (subscriptions).

| Setup | League now | Route | Decisions used | Input tok/call | Output tok/call (reasoning) | Latency p50 / req. mean / mean, s | Parallel | Price $/M in / out | API-eq. central | API-eq. conservative | Time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Fable 5.1 (off) | League 2 | Claude subscription | 2,807 | 4,298 | 64 (53) | 1.5 / 2.4 / 2.4 | 4 | $10 / $50 | $27.86 | $30.62 | 6–8 min |
| Claude Sonnet 5.5 (high) | League 2 | Claude subscription | 1,954 | 4,300 | 606 (595) | 6.0 / 6.3 / 6.6 | 4 | $2 / $10 | $8.83 | $11.53 | 16–23 min |
| Claude Sonnet 5.5 (low) | League 2 | Claude subscription | 1,778 | 4,299 | 152 (141) | 1.5 / 2.6 / 2.6 | 4 | $2 / $10 | $6.10 | $7.00 | 6–9 min |
| Gemini 3.8 Flash (high) | League 2 | Antigravity subscription | 1,971 | 3,276 | 3,958 (3,955) | 11.7 / 14.6 / 17.9 | 4 | $0.825 / $4.125 | $11.43 | $18.02 | 36–63 min |
| Claude Fable 5.1 (on) | League 3 | Claude subscription | 1,127 | 4,301 | 793 (782) | 10.0 / 12.2 / 13.0 | 4 | $10 / $50 | $49.74 | $66.98 | 30–45 min |
| Claude Opus 5.5 (off) | League 3 | Claude subscription | 1,272 | 4,299 | 181 (170) | 3.3 / 3.7 / 3.8 | 4 | $4 / $20 | $12.55 | $14.59 | 9–13 min |
| GPT-6 Astra (off) | League 3 | ChatGPT subscription | 1,182 | 3,113 | 65 (48) | 3.6 / 4.2 / 4.5 | 4 | $10 / $50 | $20.76 | $23.18 | 11–16 min |
| Gemini 4 Argon (off) | League 3 | Antigravity subscription | 1,304 | 3,449 | 19 (0) | 3.6 / 4.4 / 4.5 | 4 | $2 / $10 | $4.28 | $4.60 | 11–16 min |
| Gemini 4 Argon (on) | League 3 | Antigravity subscription | 1,196 | 3,448 | 2,083 (2,063) | 30.5 / 29.5 / 38.8 | 4 | $2 / $10 | $16.66 | $25.18 | 74 min–2.3 h |
| Grok 4.7 (off) | League 3 (League 2 after round 2) | xAI subscription | 1,156 | 4,376 | 2,374 (2,368) | 45.1 / 32.8 / 53.5 | 4 | $2 / $6 | $13.82 | $19.77 | 82 min–3.1 h |
| Grok 4.7 (on) | League 3 | xAI subscription | 1,178 | 4,376 | 11,300 (11,294) | 93.3 / 155.5 / 159.4 | 8 | $2 / $6 | $45.95 | $73.19 | 3.2–4.6 h |

### What could move the numbers

- **Prediction-call output** is not measured. For reasoning setups it could fall outside the range.
- **Class and phase mix:** the v2 100 hold 40 Risk pays and 40 Safety pays positions, more than league play. The estimate uses each team's league output per (class, phase) cell, so the mix is in it; how reasoning length varies inside a cell is not.
- **Quotas:** unknown. A quota stop changes time, not money.
- **Price drift:** the dated prices above, checked Oct 24.

## 5. Decisions

Recorded 2026-10-24 (Can's answers, via Main):

1. **8 teams** (the Cup's documented format). **Wait for the ladder to settle; no stage B until then.** The roster is taken at the steady state.
2. **Gemma 4 31B (on): included**, on the Gemma server already on spark3; device change from bariton; settings check and 20-request comparison before any call (section 4).
3. **The prediction format line (B1): approved**, with the answer constrained to the four names.
4. **Failed calls are final**, with no re-ask after the run: **approved**.

Recorded 2026-10-24, second round (Can, via Main):

5. **Positions:** 100 from `positions/new.jsonl` (checked: part of the set the Cup teams answer in the shared-position run), positions with one legal play excluded, stratified 40 Risk pays / 40 Safety pays / 20 No trade-off at 0.001 over the phases, fixed seed published; rule in Method before selection; list and hash in Method before any call. Done: v2 freeze (section 1). The 20-per-phase freeze is superseded.
6. **Settings:** each setup keeps its league settings exactly; temperature recorded where known, "not disclosed" where not; a deterministic setup is reported, never adjusted. In Method §9.10 and section 3.

Nothing is open in the plan. The run waits for Can's go and for the ladder to settle; the teams are then taken from the settled Cup roster.


Checks to run before the first call, after approval:

- re-hash `positions/close-choices-b-v2.jsonl` against `freeze/close-choices-b-v2.json` and Method §9.11;
- render hashes of the play prompt and the prediction prompt;
- unit tests of the prediction parser.
- Gemma 4 31B (on) on spark3: settings verification and the 20-request comparison (section 4).

Waiting for Can's go (and the ladder to settle)

## Approval

2026-10-24: Can approved stage B ("go") on this plan and estimate. It starts when the ladder has settled; the teams are the final 8-team Cup roster. Until then, no stage B call.

## Addendum, 2026-10-25: offline build done; waiting for the ladder (Can)

**Status:** approved, not run. **No stage B call has been made, schema acceptance calls included.** On 2026-10-25 Can decided that stage B keeps waiting for the ladder to settle; that decision overrides the earlier relayed "don't wait".

**Built and tested offline (main):**
- `ef991ab`: the prediction request.
  - `prompts/prediction.txt`: the question verbatim, then the approved format line.
  - Prediction prompt and parser; each route's constrained prediction request, with the play call's settings.
  - Commands `render-stage-b` (offline render with hashes) and `predict` (one call per team and position; a stored row, even a failed one, is never asked again).
  - `leagues/close-choices-b.json`: the 5 teams' roster settings, unchanged.
  - 63 unit tests pass.
  - The renderer reproduced the stored smoke requests byte for byte: Gemini 50/50, both Sol settings 50/50 each, Astra and Claude 10/10 each.
- `3e99825`: 500 play and 500 prediction requests rendered (5 teams × the v2 100).
  - Record: `freeze/close-choices-b-v2-requests.json`, with a sha256 per request and per team.
  - Rendered file sha256: `0e551aec…a898b`.
- `e7f0146`: Method §9.12 (dated 2026-10-25): the five team names resolved to their roster rows, the prediction request, the parsing rules and the offline checks.
- `464586e`: the live Method page now reads "Approved, not run; starts after the ladder settles (Can, 2026-10-25). No stage B call has been made." Its positions bullet describes the v2 selection.

**Open decisions (held for Can and Ümit):**
1. **System prompt of the prediction call.** The plan reuses the play call's system prompt, which tells the model to reply with one letter and nothing else; the answer schema still forces the feature-list format. Keep it, or use a neutral system prompt for the prediction call only?
2. **Schema acceptance.** Whether each provider accepts the prediction schema can't be seen offline. A rejection would fail every prediction on that route, and failed calls are final. Proposal: one acceptance call per route on a smoke position outside the 100, after approval.
3. **Play calls are run once.** `jevgammon ask --repeats 5` asks failed play calls again if it is rerun, so it must be run once per team to keep "failed is final".
4. **Gemma 4 31B (on) and changed teams** join once the ladder settles (spark3 checks as in section 4).

Waiting for the ladder (Can).
