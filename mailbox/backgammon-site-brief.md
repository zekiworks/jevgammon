BACKGAMMON BENCHMARK: WEBSITE + SMOKE TESTS (brief v11)

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


B3. DESIGN: KEEP THE CURRENT PREVIEW LOOK
First rule, above everything else in B3 and B4: keep the current preview's look. Ümit approved it. Do not redesign, restyle or re-lay-out the existing pages. Apply only the content and function changes this brief asks for. Decision-models is the reference only for elements the preview does not have yet; build those in the same style as the preview.
Background: the preview already follows our decision-models site (https://zekiworks.github.io/analysis/decision-models/?tab=confidence), and that is the house style. The points below describe it; they are not instructions to rebuild anything that already exists.
- Copy its CSS, fonts, colours, spacing, components and page layout from our site repo (analysis/decision-models/). It is our own code. Do not design new styles.
- Dark and light mode exactly as decision-models: the same toggle, the same colours, the same behaviour.
- The same top bar form and brand prefix as decision-models.
- New elements (the risk map, the risk call card, the board on Every decision) are built from the same components and colours.
- Less text. The home page has only: the intro (at most 3 sentences), the findings bullets, one-line captions under tables and charts, and footnote marks. No other prose: no "About this table" blocks, no thread headings, no paragraphs of notes. Anything longer than one line goes to Method, and the table links to it.
- When done, save 8 screenshots to mailbox/: both home pages side by side, desktop and phone, dark and light.
Use these pages as the model for their counterparts:
- Home: https://zekiworks.github.io/analysis/decision-models/
- Every question → Every decision: https://zekiworks.github.io/analysis/decision-models/questions/
- Where models disagree: https://zekiworks.github.io/analysis/decision-models/disagreements/
- Topics → Phases: https://zekiworks.github.io/analysis/decision-models/topics/
- Compare: https://zekiworks.github.io/analysis/decision-models/compare/
- Model page: https://zekiworks.github.io/analysis/decision-models/models/199/
No text, names or links from that benchmark go on the new site. No other outside site is a reference.

The backgammon board is the site's visual signature: one board in the hero, plus Every decision and the social preview image. Draw it as the preview does now: the engine's best play as arrows, the best safe play dashed.

Also:
- Mobile: wide tables scroll sideways ("Swipe for more columns"). The board fits a 360 px screen.
- Every section and every tab gets a stable anchor, so a post on X can link straight to it.


B4. HOME PAGE: THE SAME ORDER AND PARTS AS DECISION-MODELS, NOTHING ELSE
0. Top bar and nav, as on decision-models: Every decision · Where models disagree · Phases · Compare · Leagues · Method · Data. Model pages open from the table rows. "New models" is linked from Data. Add "Cup" when the Cup exists.
1. Hero, as on decision-models.
   Title: "Can a model tell when a risk is worth taking?"
   Intro, at most 3 sentences, ending "Every decision is public." For example: "Models play backgammon, and an engine scores every move they make. We measure whether each risk a model takes is the right one, and what that costs. Every decision is public."
   Stats strip: decisions scored · leagues · setups · models.
   Results line: "Results <hash>, updated <date>; scored by GNU Backgammon 1.08, 2-ply."
   Hero board: keep the board and its one-line callout with the "Open this decision" link. Use a typical Risk pays position: a stake of about 0.05 to 0.15. Not an extreme case. Say "models split" only if the same position (same board, same dice, same conditions) has recorded answers from several models, for example from the shared positions. League positions were answered only by the model that moved, so until shared positions exist, the callout explains one model's risk call and makes no claim about other models. No other buttons in the hero; the downloads sit in the downloads line.
   Champions: one compact row in the same style as the stats strip, labelled "League winners · match results": "League 1: <winner> · League 2: <winner> · League 3: <winner>", each linking to its model page. The label makes clear the row is about matches won, not the best risk judgement or the lowest error rate.
2. Findings, in the decision-models form: a one-line lead-in, then 4 bullets, each starting with a linked label that opens its tab. The lead-in is itself a finding: "None led on every measure" may be used only if the results show it, and it is checked and approved like every other finding. The first two answer the core question: the best risk judgement, and the clearest risk-call pattern (for example, too cautious or too bold). The other two cover error rate and cost.
   Findings come from findings-draft.md and go up only after Ümit approves them. Until then show one line: "Findings will be published after review."
   Store every finding with a machine check of its claim (for example: "X's error rate is lower than Y's, and their paired 95% interval excludes zero"). Before every deploy, rerun the check of every published finding. If one no longer holds, stop the deploy (B1) and write to mailbox/ which finding failed and what the data now shows. Ümit decides the new wording. After each update, also refresh the draft.
3. Filters block, as on decision-models: the heading "Filters", then League (League 1 · League 2 · League 3 · Shared positions), Model type (All · Decision · Chat · Program), Phase, Reasoning, Runs on, Weights. The setup counter ("19 of 42 setups") and Reset with "Nothing to reset: the filters show the defaults." Default: League 1. One league at a time, never merged. "Shared positions" shows its status until that data exists.
4. Leaderboard, as on decision-models: the heading "Leaderboard", the Table/Charts toggle, then ONE tab row: Risk · Quality · Confidence · Reasoning · Cost · Stability. Risk opens by default. ONE table at a time, no thread headings.
   Model cell: the linked name, with one settings line under it (for example "decision model · API" or "reasoning on · letter probabilities · our GPU"). Value cells: the number, with its 95% interval under it.
   Risk tab: the columns in B6.2.
   Quality tab: error rate (PR) with 95% interval, band on the human scale (approx.), engine's best play, blunder rate, median / P90 s per decision, $ per 1,000 decisions, decisions scored, invalid answers.
   Confidence tab (N/A for setups without probabilities): confidence source; at the cutoffs 0.90 and 0.99 (fixed in Method before computing), decisions kept, blunders among kept and mean equity lost among kept; error rate in the surest quarter; ranking score (AUROC) for the best play and for warning before a blunder; calibration gap (ECE); confident and badly wrong. A cutoff chosen on half of the games and tested on the other half (300 splits, split by game) goes to Method.
   Reasoning tab: lower vs higher setting, error rates, verdict wording from B9, extra time and cost.
   Cost and Stability tabs: as now.
   Under the table: one caption line and short footnote marks only (§ list-price estimate on our GPUs · † plays split into groups · Not measured), plus "Swipe for more columns →" on phones.
   Limits that change how a result reads stay as one line under the table or chart they limit, never only in Method. At least: "Setups played different positions; league comparisons are not paired." and "Hit risk only: being hit. Gammon risk and priming are not in it."
5. Charts, as on decision-models: panels with small tabs, "Download PNG" on each, and "Show all <N>".
   Panel "Risk": risk map · error split · stake chart (B6.5).
   Panel "Error rate, time and cost": three tabs.
   Panel "Trade-off": cost · time.
6. "Risk pays vs safety pays": the section in the place and form of "Reading vs grammar" on decision-models. One sentence per league, then one chart.
7. Downloads line, as on decision-models: "Download: results.json · decisions.json".
Nothing else on the home page. "What the input adds" (Earlier version), learning from experience (Not measured, one line), routing and teams, tail risk and every long explanation go to Method; Leagues tables go to the Leagues page.


B5. SUB-PAGES (nav)
- Every decision: the board drawn as SVG, plus the position as text exactly as the model saw it; dice; legal plays with their computed consequences; the model's choice and probability; the engine's equity for every play; equity lost; whether this model's plays were split into groups. Mark each decision with its position class (Risk pays, Safety pays, No trade-off), its stake, and its risk call (right risk, wrong risk, needless risk, missed risk, right safety), as defined in B6.1. Make all three filterable, so a reader can open, for example, every needless risk a model took with a big stake. Show the best safe play next to the chosen play. Paginated. Loads its data on demand.
- Where models disagree: positions where models pick different plays.
- Phases: opening, contact, holding game, race, bear-off. Also break down by strategy tag, number of options, and the gap between the two best plays.
- Compare: two models, or one model at two reasoning settings, side by side, paired on the same positions.
- Model pages: one per setup, with the metadata in B7.
- Leagues: one table per league. Never merge leagues into one overall score. A running league's table is marked Provisional. League notes are generated from the same data as the tables.
- New models: first look: one row per smoke-tested setup. Columns: probabilities (yes/no, and what kind), reasoning settings, median / P90 time, cost per 1,000 decisions, invalid share, and the error rate on the 50 positions with its interval and its paired difference from the reference setup. Sort by name, not by score. Top line: "50 positions each, outside the shared sets. Error rates are rough (about ±10 to ±25): enough to spot a clearly weak model, not to rank models." This page feeds no ranking, chart or finding. The minimum-sample rule in B9 does not apply here: show every value with its count and interval.
- Method: setup, the prompt and its history, the error-rate definition, the human scale and why it is approximate (human ratings include doubling-cube decisions; these games have none), limits, the statistical rules and fixed thresholds from B9, the play-order note from B8, the anchor note (GNUbg Beginner, x86-64 build), the runner changes during the leagues, and the two method experiments (dice-sharing; GNUbg reference-player checks). Label the method experiments as method findings, not model results.
- Data: downloads, versions, how to recompute. Split data files per version, league and model, small enough to load on a phone. No single huge file.


B6. CORE ANALYSIS: WAS IT THE RIGHT RISK?
The site measures one thing above all: when a model takes a risk, is it the right risk? And when it plays safe, was safe right? Every metric in this section serves that question.

B6.1 Definitions (use these exact terms everywhere on the site, one term per concept)
- Hitting rolls: for each legal play, how many of the opponent's 36 rolls hit, read from the numbers the model was shown.
- Minimum risk: the fewest hitting rolls any legal play leaves in that position.
- Best safe play: among the plays that leave the minimum risk, the one the engine rates best.
- Stake: the equity difference between the engine's best play and the best safe play. It says how much the risk call is worth in that position.
- Position class (a property of the position, one rule, no overlap):
  No trade-off: every legal play leaves the same number of hitting rolls. Count these decisions; leave them out of every risk metric.
  Safety pays: stake below 0.001.
  Risk pays: stake 0.001 or more.
- Took a risk: the chosen play leaves more hitting rolls than the minimum. Otherwise the model played safe.
- Risk call (a property of the decision), comparing the chosen play with the best safe play:
  Right risk: took a risk, and the chosen play is at least 0.001 better than the best safe play.
  Wrong risk: took a risk in a Risk pays position, but the chosen play is not at least 0.001 better than the best safe play. A risk was right here, but not this one.
  Needless risk: took a risk in a Safety pays position.
  Missed risk: played safe in a Risk pays position.
  Right safety: played safe in a Safety pays position.
Every decision with a trade-off gets exactly one risk call.

B6.2 Metrics per setup (the Risk tab, in this column order)
1. Risk judgement (headline): the average of two shares: right risks among Risk pays decisions, and right safety among Safety pays decisions. 100 means every call was right. Because it averages the two shares, it does not depend on how many positions of each class a setup met: the Safest program scores exactly 50 (0 and 100) whatever the mix, so 50 is the "always safe" line. Show it with a 95% interval (bootstrap by game).
   If a setup has no Risk pays decisions or no Safety pays decisions, risk judgement cannot be computed: show "N/A: no <class> decisions". Never treat the empty class as 0 or 100. (Safest scores exactly 50 only because both classes exist.)
2. Risks found: right risks ÷ Risk pays decisions. The first part of item 1.
3. Right safety: right safety ÷ Safety pays decisions. The second part of item 1.
   Items 2 and 3 always sit right next to item 1, each with count and denominator. The headline is never shown without its two parts.
4. Good risks: right risks ÷ all risks taken. "When it takes a risk, how often is it worth it?"
5. Missed risks: missed risks ÷ Risk pays decisions (too cautious).
6. Needless risks: needless risks ÷ Safety pays decisions (too bold).
7. Wrong risks: wrong risks ÷ Risk pays decisions (bold at the right time, wrong play).
8. Error rate by risk-call category: the setup's error rate (PR) split by where the equity was lost, in six parts: needless risks, missed risks, wrong risks, right risks, right safety, and No trade-off decisions. A right risk or right safety call can still lose equity, because the chosen play need not be the engine's best play; those losses are their own parts. The six parts add up exactly to the setup's error rate. Use this title; it describes where losses happened, not what caused them.
9. Decisions with a trade-off, and the counts per class.
Every share shows its count and denominator (B9). Every metric is computed per league; league comparisons are not paired.

B6.3 Breakdowns
- By stake, for Risk pays decisions only: small (below 0.02), medium (0.02 to 0.08), big (above 0.08). Show risks found, missed risks and wrong risks per band. Missing a big risk costs more than missing a small one, so show "big risks found" on its own.
- Needless risks have no stake band: they happen only in Safety pays positions, where the stake is below the margin by definition. Weigh them instead by the equity the chosen play lost: small (below 0.02), medium (0.02 to 0.08), big (above 0.08). Show "big needless risks" by that measure.
- Risk size: extra hitting rolls over the minimum, averaged for right risks and for wrong and needless risks. Does the model take big risks only when they pay?
- By phase: risk judgement per phase (phase × model heatmap).
- Confidence on the call (setups with probabilities only; N/A otherwise): among risks taken, the ranking score (AUROC) of confidence for "right risk". Also the average confidence on missed risks. This asks "is the model surer when its risk is the right one?"
  The model's confidence is the probability it gave its chosen play. It is not the probability that the risk beats the best safe play. So for risk calls report only the ranking score, not a calibration gap, and state that line under the metric. The calibration gap (ECE) is reported only for the event the confidence stands for: the chosen play is the engine's best play (Confidence tab).

B6.4 Reference rows (shown, never ranked, never champions)
- Safest: always plays safe. Risk judgement 50, needless risks 0, missed risks 100%.
- Random: a random legal play.
- GNUbg weak: labelled "x86-64 build: its noise is shifted, so it overplays gammons" (see About the anchor).
A cell with no decisions shows its count, 0, and no average. It never shows "Too few decisions".

B6.5 Charts (all with Download PNG and a stable anchor)
- Risk map (the signature chart): x = Risk pays decisions without the right risk (missed risks + wrong risks, as a share of Risk pays decisions), y = needless risks (share of Safety pays decisions). With these axes, risk judgement = 100 − (x + y) / 2, so (0, 0) is exactly risk judgement 100. Draw risk judgement as faint diagonal lines (50, 60, 70, 80, 90). Colour each point by its share of wrong risks among the Risk pays decisions without the right risk, so a model that takes wrong risks is never hidden among cautious ones. Safest, Random and GNUbg weak are drawn as reference points.
- Error rate by risk-call category: a stacked bar per setup from B6.2 item 8, six parts.
- Risk call card per setup, made to post on X: risk judgement in large type, then the five risk calls as bars with counts, then the hit-risk limit line.
- Stake chart: risks found, missed risks and wrong risks by stake band (Risk pays only), and needless risks by equity lost (B6.3).
- Every downloaded PNG must make sense away from the site. It carries, in small type: the league, the margin used (0.001 or 0.02), the number of decisions behind it, the results version (hash and date), and the site URL. The download keeps the filters and the theme (dark or light) selected at that moment, and the PNG lists the active filters.

B6.6 Robustness
At 2-ply, the engine can misjudge close plays by more than 0.001. So compute every risk metric twice: with the 0.001 margin (main) and with a 0.02 margin (in every place where 0.001 appears above). Show the 0.02 results next to the main ones on the Risk tab and in Method. If a finding holds at one margin but not the other, say so in the finding.

B6.7 Practical rules
- If any play in the minimum-risk set, or the chosen play, has no 2-ply evaluation, evaluate it with GNUbg on CPU. No model requests. Follow the CPU rule in section 0.
- Fix every threshold here (0.001, 0.02, the stake bands) in Method before computing results (B9).
- Limit: this measures one kind of risk, being hit. Gammon risk and priming are not in it. State this next to the Risk tab and every risk chart, not only in Method.


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
- Fix these thresholds in Method before computing results, and do not change them after seeing results: blunder (0.08 equity, as now), "badly wrong", "very confident", the time budget, and the risk thresholds from B6 (the 0.001 margin, the 0.02 robustness margin, and the stake bands 0.02 and 0.08).
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
1. Snapshot + build script + the update loop (B1) with its pre-deploy checks.
2. Home page in the decision-models look and order (B3, B4), with the Risk tab first and every B6 metric computed for all three finished leagues, at both margins, with the risk map, the error split and one risk call card per league champion. Then the 8 side-by-side screenshots from B3.
3. Every decision and Method, filled with the data that exists.
4. Every other section in place, showing its status.
5. A list mapping each analysis (A1–A13, the high-hurts set, the B6 risk metrics) to its status, the data file it comes from, and whether it waits for the running leagues.
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
