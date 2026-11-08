# e. Nackgammon

Source: tools/site/content/nack_paired_results.json (drop = Nackgammon PR − standard PR; positive = worse on Nackgammon) and nack_paired_late.json. No per-group drop interval exists in the data; the group-level intervals are the primary comparisons (`primary.<rule>[kind=group].ci_99`, difference of group drops), and per setup the final 97.5% interval (`setups.<s>.final.drop_975`, labels from it).

Criterion: KEEP 'A new starting position: no clear drop.' only if every group's change interval includes 0.

Group comparisons (primary rule `random`, with additions; 99% intervals):
- decision models − workhorses: diff -1.44 [-8.85, +4.96] — includes 0: True (group drops -1.93 / -0.49)
- decision models − frontier: diff -1.04 [-14.19, +10.26] — includes 0: True (group drops -1.93 / -0.89)
- workhorses − frontier: diff +0.40 [-6.68, +6.96] — includes 0: True (group drops -0.49 / -0.89)
- LFM2.5-24B-A2B (on) − LFM2.5-24B-A2B (off): diff -3.88 [-26.98, +21.76] — includes 0: True (group drops -0.65 / +3.23)
- GPT-6.1 Sol (high) − GPT-6.1 Sol (low): diff -0.19 [-3.00, +2.63] — includes 0: True (group drops -1.45 / -1.26)
All 4 rules × 5 comparisons, with and without the additions (`primary`, `primary_original_members`): every 99% interval includes 0 = True.
Group drops (rule random): decision models −1.93, workhorses −0.49, frontier −0.89 PR.

Per setup (final look, 97.5%):
- Fastino GLiDE v1.2 (local) (decision models): +1.60 [-5.33, +8.30] unclear
- Fastino GLiDE (decision models): +3.07 [-3.84, +9.81] unclear
- Liquid d1-ultra (decision models): +6.17 [-2.06, +13.95] unclear
- Jev 1.13.0 (decision models): +2.77 [-5.20, +10.44] unclear
- GPT-6 Luna (decision models): +5.87 [-4.27, +15.07] unclear
- Celeris-1 Decision (decision models): +4.08 [-4.58, +12.64] unclear
- Decider v1.1 27B (decision models): +0.81 [-7.98, +9.24] unclear
- Cygnet (Gemma 4 12B) (decision models): +0.20 [-7.64, +7.43] unclear
- SubQ Snap Preview (decision models): +1.62 [-7.07, +10.07] unclear
- Mercury Decide (decision models): +2.73 [-5.94, +10.85] unclear
- Winnow-12B (decision models): +2.68 [-6.26, +11.16] unclear
- Decider v1.2 27B (decision models): -2.68 [-11.03, +5.25] unclear
- Decider Flash v1.2 (decision models): +7.78 [-2.16, +18.39] unclear
- Open-Jev 27B v1.1 (decision models): -3.08 [-13.33, +6.76] unclear
- GPT-6.1 Sol (high) (workhorses): -2.03 [-5.57, +1.38] unclear
- GPT-6.1 Sol (low) (workhorses): -1.46 [-5.01, +2.05] unclear
- Claude Sonnet 5.5 (low) (workhorses): -1.15 [-5.89, +3.32] unclear
- Gemini 3.8 Flash (low) (workhorses): -1.30 [-5.48, +2.90] unclear
- Gemma 4 31B (on) (workhorses): -1.13 [-6.19, +4.39] unclear
- DeepSeek V4.1 Flash (off) (workhorses): +5.94 [-2.48, +13.87] unclear
- Qwen3.8-27B (off) (workhorses): +4.76 [-3.56, +12.53] unclear
- LFM2.5-24B-A2B (on) (workhorses): +4.77 [-4.14, +13.49] unclear
- LFM2.5-24B-A2B (off) (workhorses): +4.43 [-6.53, +15.38] unclear
- Claude Fable 5.1 (high) (frontier): +1.16 [-2.17, +4.40] kept
- GPT-6 Astra (medium) (frontier): -1.99 [-5.52, +1.47] unclear
- Grok 4.7 (high) (frontier): +0.85 [-3.74, +5.35] unclear
- GPT-6.1 Terra (no group (exploratory)): +3.04 [-0.94, +7.39] unclear
- Gemini 4 Argon (low) (no group (exploratory)): +2.71 [-2.06, +7.62] unclear
- GNUbg weak (yardstick): -4.57 [-10.32, +1.34] unclear
- Random (yardstick): -3.73 [-11.43, +3.74] unclear
Late entries (exploratory, no group; nack_paired_late.json `setups`):
- SubQ Snap 1.1: +1.62 [-7.07, +10.07] unclear
- Drex Max 1.1: +0.69 [-6.03, +7.48] unclear
- Drex 2.0: +1.95 [-6.39, +9.95] unclear
- Base Labs Elephant-1: +8.66 [+0.42, +16.02] worse
- Base Labs Mammoth-1: +1.84 [-5.72, +8.72] unclear
- Drex Max v1: +1.71 [-6.67, +9.37] unclear
- Drex 2.0 (local): +1.60 [-6.90, +9.75] unclear

Random reference: drop -4.56 PR on the main 200 pairs (`setups.Random.first.drop`; live wording 'Random play's own drop is −4.6 PR on the main 200 pairs: the Nackgammon positions were slightly easier for random play'), -3.73 on 500 pairs.
Note to keep (nack_section.py:17, live index.html): 'Unclear means the test can’t tell, not that the scores are equal.'

Result: every group interval includes 0, and every grouped setup's interval includes 0 (26 unclear, 1 kept: Claude Fable 5.1 (high)). Exception outside the groups: late entry Base Labs Elephant-1 (a ranked model) +8.66 [+0.42, +16.02], label 'worse' (shown as 'dropped').

Verdict (superseded, see below): KEEP 'A new starting position: no clear drop.' — this was wrong: see the correction.

**Correction (Zeki #2961; site from commit after ace14d5): heading NEUTRAL, "A new starting position".** What the data
test, exactly: `primary.<rule>` and `primary_original_members.<rule>` hold, for kind "group", three BETWEEN-group
comparisons (decision models − workhorses, decision models − frontier, workhorses − frontier), each the difference of
two group drops with a 99% interval (`ci_99`). All of them include 0 (every rule, with and without the additions). That
says the test cannot show the groups' drops to DIFFER; it says nothing about whether a group's own drop is unclear —
there is no interval for a single group's drop in the data (line 3 above). So "no clear drop" in any form is not
supported. The two kind "setup" comparisons (GPT-6.1 Sol high − low, LFM2.5 on − off) are not used.

On the site (story.nack_finding): heading always "A new starting position"; the sentence reports the comparison as a
between-group one ("Compared group against group (one group's drop minus another's: …), every 99% interval includes 0,
so the test does not show the groups' drops to differ."); kept: Random's drop as the reference, the Elephant-1
exception (+8.66 PR, 97.5% interval +0.42 to +16.02) and "Unclear means the test can't tell, not that the scores are
equal."
