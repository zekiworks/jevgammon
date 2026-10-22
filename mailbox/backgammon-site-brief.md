BACKGAMMON BENCHMARK: WEBSITE + SMOKE TESTS (brief v6)

This brief replaces every earlier version and the separate messages about the rebuild.
Two jobs:
- Part B, the website: start now.
- Part A, smoke tests for candidate models: keep going in the background.
Background for Part B: backgammon-site-plan.md (in mailbox/). It has the full analysis list (A1–A13). Where the plan and this brief differ, follow this brief.
Reply in mailbox/.
0. MATCHES MAY STILL BE RUNNING. READ THIS FIRST. (Applies to both parts.)
- Do not touch the league runner (jevgammon), its output folders, the model servers or the GPUs the leagues use. Do not restart, pause or reconfigure anything.
- Read league data only from a copy (a snapshot). Never write into the runner's folders.
- Local model runs never share a GPU with the leagues. They run only on a GPU the leagues are not using, or they wait until the leagues finish. Low priority (nice) does not apply to GPUs and is no substitute for a free GPU.
- CPU jobs (GNUbg re-evaluation, builds) run on CPU cores the leagues are not using, or at low priority (nice) so they do not slow the matches.
==================================================
PART B: THE WEBSITE (start now)
==================================================

Task: rebuild https://zekiworks.github.io/analysis/backgammon/ as a multi-page benchmark site.
Do not wait for the smoke tests. Smoke-test numbers never enter a ranking, chart or finding: they come from 50 positions outside the shared sets. They get their own page, "New models: first look" (B5).
B0. FRAMING: EVERY SECTION SERVES THE CORE QUESTION
The core question: can a model tell when a risk is worth taking?
The site studies it through five threads. Each home section and each tab belongs to one of them:
1. Decision quality under risk: how much equity each move gives away, judged by the engine, not by wins.
2. What the input adds: how much of a model's play comes from the information we compute for it. (v1: computing each play's consequences in code cut the error rate by about two thirds. This is the strongest finding so far; keep it prominent.)
3. Confidence: does a model know when it is likely wrong?
4. Cost: what each level of quality costs in time and money, including what more reasoning buys.
5. Learning from experience: not measured yet. Every decision is a separate request.
Material that serves none of these (league standings, runner history, the anchor bug, hardware moves) goes to Leagues or Method, not the home page.
This is a standalone study. Do not mention or link the decision-models benchmark anywhere in the text. No finance framing. English only.
B1. LIVE DATA: THE SITE UPDATES AS RESULTS COME IN
- A build script generates every page from data files. Nobody types a number into the HTML by hand.
- Update loop: when new results land (a finished match, a finished league, a new smoke-test row), take a new snapshot, score the new decisions with GNUbg at low priority (nice), rerun the build and deploy. At most once every 15 minutes. If nothing changed, do nothing.
- The loop must survive restarts and report its own failures. If it stops, write why to mailbox/.
- Before each deploy, run checks: every number traces back to a data file, counts add up, no leagues or versions are mixed, every published finding still holds (B4), and no published file contains a private address or credential (B7). If a check fails, do not deploy. Write what failed to mailbox/.
- Every page shows "Data as of <date, time>" and the results hash.
- Each league has a status: Running (matches done / total) · Finished · Stopped.
- A running league's numbers do appear, marked "Provisional: league still running", and only in that league's own tables. They enter no cross-league ranking, chart or finding until the league finishes.
B2. DEPLOYMENT
- Build on a preview path or branch. Do not change the live page except for live-page fixes Ümit asks for. The update loop deploys to the preview from day one.
- Switch the live URL to the new site only after Ümit approves it. From then on, the update loop deploys data updates to the live site by itself. New sections, layout changes and findings text still need Ümit's approval.
- After the switch, the old URL keeps working. The current page's content stays available: move it into Method and Leagues.
B3. DESIGN
Base: our decision-models site (the Turkish benchmark). The new site is its sibling: the same house style, adapted to backgammon. Its source is in our site repo (analysis/decision-models/). It is our own code, so reuse its build setup, templates, CSS and components (header nav, question-led hero, stats strip, findings list, filters, Table/Charts toggle, tabs, detail pages, JSON downloads, results line, social preview). The pages the site needs are set by this brief (B4, B5). Use these pages as the model for their counterparts:
- Home: https://zekiworks.github.io/analysis/decision-models/
- Every question → Every decision: https://zekiworks.github.io/analysis/decision-models/questions/
- Where models disagree: https://zekiworks.github.io/analysis/decision-models/disagreements/
- Topics → Phases: https://zekiworks.github.io/analysis/decision-models/topics/
- Compare: https://zekiworks.github.io/analysis/decision-models/compare/
- Model page: https://zekiworks.github.io/analysis/decision-models/models/199/
No text, names or links from that benchmark go on the new site. No other outside site is a reference.

Forms to keep from decision-models:
- Title as a question, then the subtitle, then a 2–3 sentence intro that ends with "Every decision is public."
- Downloads: decisions and results as JSON files, linked from the hero and from Data.
- A Method page for the method, rules and fixed thresholds.
- A social preview image, generated from the current results.

Backgammon's own touches, so it is a sibling, not a clone:
- The backgammon board is the visual signature: use it in the hero, the social preview and Every decision.
- The risk 2×2 from B6 is the second signature element; design it to be read at a glance and to work as an image on X.
- A different accent colour is fine, within the same house style.
- Before building, write a short design note to mailbox/: what you reuse from decision-models and what is new. Keep it to half a page.

Also:
- Mobile: wide tables scroll sideways ("Swipe for more columns"). The board fits a 360 px screen.
- Every section and every tab gets a stable anchor, so a post on X can link straight to it.
B4. HOME PAGE, in this order
1. Hero.
   Title: "Can a model tell when a risk is worth taking?"
   Subtitle: "We score every backgammon decision with an engine and compare decision quality, what the input adds, confidence and cost across <N> model setups." (<N> comes from the build.)
   Then the download links and the link to Method (B3).
   Stats strip: decisions scored · leagues · setups · models.
   Results line: "Results <hash>, updated <date>".
2. Findings: 4 short bullets, one per thread, each linking to its section. The first bullet answers the core question.
   Findings come from findings-draft.md and go up only after Ümit approves them. Until then show: "Findings will be written when the current leagues finish."
   Store every finding with a machine check of its claim (for example: "X's error rate is lower than Y's, and their paired 95% interval excludes zero"). Before every deploy, rerun the check of every published finding. If one no longer holds, stop the deploy (B1) and write to mailbox/ which finding failed and what the data now shows. Ümit decides the new wording. After each update, also refresh the draft.
3. Leaderboard (thread 1). Table/Charts toggle. League is a selector: one league at a time, never merged. Add a "Shared positions" view only once that data exists; until then it shows its status.
   Filters: league, model type, open/closed weights, runs on, reasoning setting.
   Columns: model + setting, error rate (PR) with 95% interval, band on the human scale (approximate), engine's best play %, blunder rate, median / P90 time per decision, $ per 1,000 decisions, decisions scored, invalid answers.
   Tabs: Quality · Risk · Confidence · Reasoning · Cost · Stability.
   Charts view: error vs cost (log cost axis, line through the best-value setups), error vs median time, paired low→high dot plot per model, risk–coverage curves, phase × model heatmap, the risk 2×2 from B6.
4. Is the risk worth it? (core question, B6). Give it the most space after the leaderboard.
5. What the input adds (thread 2): the prompt history from v1, with the table of what changed and the error rate after each step, and the "computed consequences" finding. Mark it Earlier version.
6. Confidence (thread 3): does confidence track error, per confidence source; "confident and badly wrong"; tail risk (P95 error, mean loss of the worst 5% of decisions).
7. Cost and reasoning (thread 4): the quality vs cost chart; what more reasoning buys per model (paired difference, extra time and cost, verdict from B9); routing and teams.
8. Learning from experience (thread 5). Status: Not measured. One line: "Every decision is a separate request; models are not told how earlier games went." Do not describe future plans.
9. Links to Leagues, Method and Data.
B5. SUB-PAGES (nav)
- Every decision: the board drawn as SVG, plus the position as text exactly as the model saw it; dice; legal plays with their computed consequences; the model's choice and probability; the engine's equity for every play; equity lost; whether this model's plays were split into groups. Mark each decision Risk pays, Safety pays or No hit-risk trade-off (B6), and whether the model took a risk; make both filterable. Paginated. Loads its data on demand.
- Where models disagree: positions where models pick different plays.
- Phases: opening, contact, holding game, race, bear-off. Also break down by strategy tag, number of options, and the gap between the two best plays.
- Compare: two models, or one model at two reasoning settings, side by side, paired on the same positions.
- Model pages: one per setup, with the metadata in B7.
- Leagues: one table per league. Never merge leagues into one overall score. A running league's table is marked Provisional. League notes are generated from the same data as the tables.
- New models: first look: one row per smoke-tested setup. Columns: probabilities (yes/no, and what kind), reasoning settings, median / P90 time, cost per 1,000 decisions, invalid share, and the error rate on the 50 positions with its interval and its paired difference from the reference setup. Sort by name, not by score. Top line: "50 positions each, outside the shared sets. Error rates are rough (about ±10 to ±25): enough to spot a clearly weak model, not to rank models." This page feeds no ranking, chart or finding. The minimum-sample rule in B9 does not apply here: show every value with its count and interval.
- Method: setup, the prompt and its history, the error-rate definition, the human scale and why it is approximate (human ratings include doubling-cube decisions; these games have none), limits, the statistical rules and fixed thresholds from B9, the play-order note from B8, the anchor note (GNUbg Beginner, x86-64 build), the runner changes during the leagues, and the two method experiments (dice-sharing; GNUbg reference-player checks). Label the method experiments as method findings, not model results.
- Data: downloads, versions, how to recompute. Split data files per version, league and model, small enough to load on a phone. No single huge file.
B6. CORE ANALYSIS: IS THE RISK WORTH IT?
Hitting rolls are read from the numbers the model was shown: for each legal play, how many of the opponent's 36 rolls hit.
- Minimum risk: the fewest hitting rolls any legal play leaves in that position.
- Best safe play: among the plays that leave the minimum, the one the engine rates best.
- Classify every scored decision with one rule, so no decision can fall into two classes:
  No hit-risk trade-off: every legal play leaves the same number of hitting rolls. The model has no risk choice here. Show the count of these decisions, and leave them out of all risk shares.
  Safety pays: the best safe play loses less than 0.001 equity against the engine's best play.
  Risk pays: the best safe play loses 0.001 equity or more against the engine's best play.
- What the model did: it took a risk if its chosen play leaves more hitting rolls than the minimum. Otherwise it played safe.
- For each model, show a 2×2: Risk pays / Safety pays × took a risk / played safe. Each cell shows its raw count, its share of the row, and its mean equity lost. The denominator of a share is the total number of decisions in that row's class (Risk pays or Safety pays).
- Two headline numbers per model: in Risk pays decisions, the share where the model took a risk; in Safety pays decisions, the share where it took a needless risk. Show each with its count and denominator.
- Show the Safest program as a reference row: it never takes a risk, so it shows what pure caution costs. A cell with no decisions shows its count, 0, and no mean. It never shows "Too few decisions".
- Also break it down by phase. For models that give probabilities, add confidence per cell.
- If any play in the minimum-risk set has no 2-ply evaluation, evaluate those plays with GNUbg on CPU. No model requests. Follow the CPU rule in section 0.
- The 0.001 threshold is fixed in Method before computing results (B9).
- Limit: this measures one kind of risk, being hit. Gammon risk and priming are not in it. State this next to the 2×2 and every risk chart, not only in Method.
B7. MODEL SETUPS ARE NOT IDENTICAL. SHOW IT.
Record these for every setup and show them on its model page:
- model ID string, provider or endpoint, date run, price date
- model type: decision model · chat model read through answer-letter probabilities · chat model answering one letter (filter)
- weights: open · closed (filter)
- runs on: our GPUs · API · subscription (filter)
- reasoning setting (filter)
- confidence source: decision-model probability · letter probability · none (column on the Confidence tab)
- rules text: short (decision models) or long (chat models)
- option groups: the group size, if this model's plays are split into groups and the group winners compared
- sampling settings (temperature and so on)
When a ranking puts side by side setups that got different inputs (rules text, option groups), mark those rows.
Publishing rule: show the provider by name and the public model ID only. Never publish internal hostnames, IP addresses, ports, server paths, API keys, tokens, account IDs or request headers, on the pages or in the JSON downloads. Strip them when exporting data. The pre-deploy check (B1) scans every published file for them and blocks the deploy if it finds one.
B8. VERSIONS
- Never put numbers from different benchmark versions or prompt formats in one ranking or chart. Every number carries its version.
- Earlier versions listed the plays in the runner's order, which tends to put the best play early. Mark earlier-version numbers with this note. (Re-run with shuffled plays: Gemini 4 Argon's error rate rose by 1.9, 95% interval −0.3 to 4.1, so not proven.)
B9. STATISTICS AND VERDICTS
- Intervals: bootstrap by game for league decisions, because moves within a game are not independent. Bootstrap by position for the shared positions.
- A comparison of two setups on the same positions is always paired. League games are not the same positions, so league comparisons are not paired; say so wherever one appears.
- Verdict rule for reasoning (and any A vs B comparison on the same positions):
  High helps: the paired 95% interval of the error difference is entirely below zero.
  High hurts: the interval is entirely above zero.
  No clear benefit: the interval includes zero. Never write "they are the same", "level" or "gains nothing".
  Depends on the position: phase-level effects point in different directions, each with an interval that excludes zero. Mark every phase-level verdict as exploratory.
- For league (unpaired) comparisons, use only: "no clear difference in league play" or "lower/higher error rate in league play", never a verdict label.
- Minimum sample: an average (error rate, mean equity lost, a calibration metric) over fewer than 200 decisions shows "Too few decisions" instead of a value. Raw counts are always shown. A share is always shown with its count and denominator. State the minimum in Method.
- Exception: the "New models: first look" page (B5). Its 50-position error rates are shown with their intervals, as the smoke test intends.
- Fix these thresholds in Method before computing results, and do not change them after seeing results: blunder (0.08 equity, as now), "badly wrong", "very confident", and the time budget.
- Keep "worse moves" and "more time or cost with no shown gain" as two separate findings. Never merge them into "high is bad".
B10. STATUS
Every section and every metric shows one status: Published · Provisional · Earlier version · Analysis pending · Not measured · N/A.
Provisional means the numbers come from a league that is still running and will change.
Leagues also use Running · Finished · Stopped. An average below the minimum sample shows "Too few decisions" (B9).
If the data does not exist, show the status. Never show a placeholder number.
B11. RULES
- Confidence metrics (AUROC, ECE, Brier, risk–coverage) are N/A for setups that return only a choice. A recorded 1.0 from those setups is not 100% confidence. Compare confidence only between setups with the same confidence source.
- Invalid answers: count them and show them. The runner replaces an invalid answer with a random legal play. Never count that play as the model's choice: leave invalid answers out of the error rate and show their share next to it.
- The team "oracle" (the best answer any member gave) is an upper bound. Style it differently and never present it as a working system.
- Cost has three labels that never mix: API price estimate, API-equivalent (subscription runs), own hardware. A model on our GPUs shown at its maker's list price is labelled "list-price estimate; runs on our GPUs".
- Keep request time separate from retry/wait time. The v3 leagues had no clock, so do not claim the time-budget risk was measured.
- Every view shows the sample size, failed requests and cost coverage.
B12. SCOPE
- No new model requests beyond the Part A smoke tests. No new experiments.
- Offline analyses on recorded decisions are allowed for the analyses in the plan and in this brief, including the "When does high hurt?" set. Every number on the site comes from a script in the repo.
- Do not invent numbers, and do not turn existing numbers into new claims.
B13. FIRST DELIVERY (on the preview)
1. The design note from B3, then snapshot + build script + the update loop (B1) with its pre-deploy checks.
2. Home page with hero, leaderboard (league selector), and "Is the risk worth it?" computed for the finished leagues (provisional for any running league).
3. Every decision and Method, filled with the data that exists.
4. Every other section in place, showing its status.
5. A list mapping each analysis (A1–A13, the high-hurts set, Is the risk worth it?) to its status, the data file it comes from, and whether it waits for the running leagues.
6. A list of setups with missing metadata from B7.
7. The preview URL.
==================================================
PART A: SMOKE TESTS FOR CANDIDATE MODELS (background, no league play)
==================================================

When to run:
- API models: run now.
- Models on our servers (d3-turbo, Nemotron): run only on a GPU the leagues are not using. Otherwise wait until the leagues finish. If one runs next to a league, mark its timing "measured while leagues ran".

How to run:
- Run the usual 50-position smoke test, outside the shared sets, for each model below.
- Use the v3 prompt and shuffled play order, the same as the leagues.
- Use the same 50 positions for every model.
- Also run one reference setup we already know well on the same 50 positions (a cheap API one if the GPUs are busy), so every error rate has a paired comparison.
- Don't add any of these models to a league.
- How you build the adapters is your call. Skip any that take long and say why.

Limits:
- Spending cap for all of Part A: $50 at list prices. Track spend as you go. When it reaches $40, start no new setups and report in mailbox/.
- Retries: at most 2 per request, with backoff, and only for transport errors (rate limit, server error, dropped connection). Never retry because an answer was invalid.
- Timeout: 600 seconds per decision, for every setting. A request that hits it counts as timed out, not as invalid.

Report per setup (these fields also feed B7 and the "New models: first look" page):
- Model ID string, provider (pinned), date run.
- Which reasoning settings exist.
- Whether it returns probabilities (per option, per answer letter, or none).
- Context limit, and whether the plays had to be split into groups.
- Which rules text it got (short or long).
- Invalid share. Failed and timed-out requests counted separately.
- Median and 90th-percentile time per decision. Request time separate from retry/wait time.
- Input and output tokens, and cost per 1,000 decisions, with the price used and its date. Label it API price, API-equivalent (subscription) or own hardware.
- Error rate on the 50 positions with its interval, and the paired difference from the reference setup.

Models:
1. d3-turbo (Hugging Face vllm-sr/d3-turbo, 26B, Apache 2.0). It runs on transformers with trust_remote_code=True, because vLLM doesn't support it yet. Read the remote code before running it on our servers, then load that exact revision (commit hash), so the code you read is the code that runs. It returns a probability per option without generating text.
2. Claude Haiku 5.5, low and high.
3. Mercury 3 (Inception), through Inception's API or OpenRouter with the provider pinned. It's a diffusion LLM; check whether it returns token probabilities.
4. Nemotron 3.5 Bolt 74B-A9B, off and on, on our servers.
5. MiMo V2.6 Pro (Xiaomi): check the provider and settings.
6. Beam 1.0 (Reflection), OpenRouter slug beam-1.0-501b-a23b, at low and high reasoning effort.
7. Claude Fable 5.1, low and high.
8. Mistral Large 4: no test yet. Just check whether its weights are out.

If the adapters are quick: MiMo V2.6 Flash, Kimi K3, Hy4 Preview, Grok 4.7 and MiniMax M3.1 Flash. For MiniMax, also check whether its weights are open, since sources disagree.

Reply in mailbox/ with one table and anything that blocked you.

Smoke-test error rates are rough: 50 positions give intervals of about ±10 for the strongest models and ±15–25 for weaker ones. Enough to spot a clearly weak model, not to rank close ones.
