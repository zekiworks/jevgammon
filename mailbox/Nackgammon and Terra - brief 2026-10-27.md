Replaces all my earlier messages on Nackgammon and Terra. League renaming and GLiDE task B wait. No model call before my go. Writing the roster and building and freezing the position sets (GNUbg only) need no go.

1. HYPE CUP ROSTER
Write the 8 teams from the final tables to mailbox/, as defined in mailbox/backgammon-ladder-cup.md. No Cup matches yet. Both Nackgammon parts below use these 8 teams.

2. NACKGAMMON PAIRED TEST (new to you; the research finding)

What it is
- Nackgammon: the same rules as backgammon; only the start differs. Each side starts with 2 checkers on its 24-point, 2 on the 23-point, 4 on the midpoint (13), 3 on the 8-point and 4 on the 6-point. GNUbg supports the variant.
- Question: when the rules stay the same, how much does a new starting setup change each setup's decision quality and risk calls? It measures how well a whole setup (model, settings and prompt) transfers. A larger drop is consistent with relying on familiar positions but is not proof, because Nackgammon positions also differ in structure. Never write "memorized" or "what it was trained on". "Performance kept" is a valid result.
- This replaces the Nackgammon part of the shared positions in Method (the 500 Nackgammon positions). Add a dated amendment and keep the old text, marked superseded. The 200-position opening control stays in Method but is not part of this run.

Position set (build once; freeze and hash before any model call)
- Generate from GNUbg self-play. Take at most one position from each source game, counting the main set and the reserve together. Record every position's source game ID. Remove repeated board + dice states.
- Main set: 200 Nackgammon–standard pairs, matched on game phase, number of legal plays, the gap between the two best plays and, where possible, position class (Risk pays / Safety pays / No trade-off).
- Reserve: 300 more pairs, built the same way, used only for extensions. Every extended setup gets the same reserve pairs, in the same order.
- Freeze in Method: the phase definitions, the matching tolerances, the assignment rules for game-plan tags (blitz, back game, holding, low-anchor, priming, other) and for position classes, and the number of pairs per phase and per class. Report the balance of each matching variable and the tag mix of both sets.
- Score with GNUbg 2-ply.

Prompt and answers
- Prompt: v3 WITHOUT the standard opening table on BOTH sets. The two prompts differ only in the line naming the starting setup (standard or Nackgammon). If a Nackgammon prompt already exists, check it matches this.
- Invalid or missing answers (after the usual retries) are never dropped. Primary rule: such an answer scores the position's random-play error (the average error over all legal plays). Sensitivity checks: score those answers with the worst legal play's error instead, and separately leave those pairs out for that setup. Report the count per setup and set.

Plan in Method (dated, before any model call, never changed afterwards)
a) Hypothesis: error rates rise from standard to Nackgammon positions, most in the opening and less later in the game, and the rise differs between setups.
b) Per-setup stopping rule, two looks: after 200 pairs, compute each setup's drop (Nackgammon − standard) with a 97.5% interval. Extend that setup with the 300 reserve pairs only if the interval contains 0 AND also contains +5 or −5 PR. Examples: [−2, 6] is extended; [−2, 3] and [3, 9] are not. Report every setup's final interval at 97.5% as well. Splitting the error over the two looks targets about 95% coverage; bootstrap intervals are approximate, so write it that way.
c) Outcome label per setup, from its final 97.5% interval: "kept" if the whole interval lies between −5 and +5 PR; "worse" if it lies entirely above 0 and is not "kept"; "better" if it lies entirely below 0 and is not "kept"; "unclear" otherwise. At the first look, "unclear" is exactly what gets extended.
d) Groups, each setup weighted equally: decision models = every League 1 decision model, including those in the Cup; workhorses = the Cup teams from League 2, plus Terra if it runs; frontier = the Cup teams from League 3. The yardsticks belong to no group. List every member by name.
e) The primary comparisons, secondary analyses and engine check below.

Setups
- All League 1 decision models; two yardsticks, the GNUbg weak anchor and the Random program (its error rate is the average error over all legal plays, computed exactly from GNUbg's evaluations, no calls); the 8 Hype Cup teams; and GPT-6.1 Terra if its smoke test passes (point 4).
- Each setup runs once, even if it is both in League 1 and in the Cup. Decision models first. Slowest setups last: Gemma 4 31B (on) goes last only if it is one of the 8; do not add it otherwise.
- If no open-weights chat model is among the 8, tell me and propose one hosted open-weights setup.

Results per setup
- Standard error rate, Nackgammon error rate and the drop, always shown together, never a ranking by drop alone. Also by phase and by game-plan tag, with cost per decision alongside.
- Extensions refine each setup's own estimate and are reported per setup, separate from the primary comparisons.
- Chart: each setup's standard error rate against its Nackgammon error rate, with GNUbg weak and Random marked.

Primary comparisons (on the first 200 pairs only, which every setup answered)
- Computed directly as A's drop − B's drop, with an interval from a paired bootstrap over pairs. Bonferroni: the 5% error is divided, not the 95%. With M primary comparisons, each interval's confidence level is 1 − 0.05/M (for example, M = 3 gives 98.33%). Fix M from the final roster (the 3 group comparisons plus the effort pairs that are in the run) and write it in Method before any model call. (Correction by Can, 2026-10-27; replaces "at 95% divided by the number of primary comparisons".) Show both groups' standard and Nackgammon error rates next to every difference.
  1) The three groups against each other (mean drop per group, each setup weighted equally).
  2) The same model at two effort settings (low vs high, off vs on), wherever both are in the run.
- Scope: these results hold for these rosters only. League 1 is the full league; the other two groups are the Cup's selected top setups. Say so wherever group results appear.

Secondary analyses (fixed now, labelled secondary, no extra model calls)
  1) Kept advantage over random play: (Random's Nackgammon error − setup's Nackgammon error) ÷ (Random's standard error − setup's standard error). 1 means the setup keeps its whole advantage over random play; 0 means it falls to random. Bootstrap interval. Flag setups whose standard advantage over random is small, because the ratio is unstable there.
  2) Ranking: Spearman correlation between setups' standard and Nackgammon error rates, with a bootstrap interval over pairs. List the largest rank changes by name.
  3) Risk, from the same answers: classify every position with the existing rules (Risk pays / Safety pays / No trade-off) and every answer's risk call (right risk, wrong risk, needless risk, missed risk, right safety). Per setup and set: ability and caution, and their change from standard to Nackgammon, with intervals. Report the number of positions per class; where a class is thin, say so instead of reading much into it.
  Everything else (for example Terra vs Sol low) is exploratory and labelled so.

Engine check (no model calls; engine time only)
- Before any model call, choose 40 pairs (80 positions), spread across phases and both sets, and freeze the list.
- After the answers are in, roll out GNUbg's top 5 plays at 2-ply plus every play any setup chose in those positions. Record the rollout settings.
- On this subset, recompute error rates, drops and the primary comparisons with rollout values and with 2-ply values side by side. Report whether any comparison changes direction.

Release
- Prepare a release bundle: positions with source game IDs, pairs, matching rules, prompts, settings, raw answers, scores and analysis code. Do not publish before my go.

3. NACKGAMMON KNOCKOUT (hype, not the research finding)
- The 8 Hype Cup teams, knockout: 7 matches, Hype Cup bracket and draw rules. No GNUbg anchor.
- Same match rules as the leagues, including the same-dice rule (two games per round, seats swapped, same rolls). Start from the Nackgammon setup; same prompt as the Nackgammon side of point 2.
- Report each team's Nackgammon error rate next to its standard league error rate, labelled "rough: different positions and opponents, not paired".

4. NEW SETUP: GPT-6.1 Terra
- openai/gpt-6.1-terra on OpenRouter, released 26 Oct 2026, $1 / $5 per million tokens. Reasoning effort low, the same as GPT-6.1 Sol (low).
- Its smoke test (same as for earlier new setups) also waits for my go.
- If it passes: add it to the paired test (point 2), and to League 2 (workhorses) as the next season under the new rule. It plays every League 2 setup once; no other placement changes. It is not in the Hype Cup or the knockout.

5. BUDGET AND GO
$7.27 of the $115 is left. Before any model call, send a table to mailbox/ with cost and time, kept separate for the start and the possible extension:
  a) Terra smoke test
  b) Paired test start (400 decisions per setup): decision models and the GNUbg anchor (Random needs no calls)
  c) Paired test start: Cup teams not in League 1, plus Terra
  d) Paired test extension, worst case (every setup extended to 1,000 decisions)
  e) Nackgammon knockout
  f) Terra's League 2 season
  g) Engine time only: building the position sets and the rollout check
Base each estimate on the existing call logs: real tokens including thinking tokens, the retry rate, and for matches the real number of turns per game. Mark which setups cost OpenRouter money and which cost only time (subscriptions, our GPUs). Say what fits in $7.27. Wait for my go on every model-call row.
