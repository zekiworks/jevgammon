# front-story: resume notes (2026-11-07, before the 16:33 UTC reboot)

Task: Ümit, bus #2570 (via Main). Zeki #2578 corrections applied. This is a candidate only: not merged, render-only.

## Where things are

- **Branch:** `front-story`, pushed. Last commit is `4fcd7a1`, a work-in-progress commit on top of `origin/learning-page` `587e57f`, which is on main `7719e1a`.
  - Worktree: `~/code/jevgammon-front`.
  - Rebase onto `origin/learning-page` again when it moves; it will still get #2575 validation changes. Do not touch `learning_page.py` or `checks.py` check 7.
- **Files in `mailbox/front-story/`:** not committed in the main checkout; they survive the reboot because they are in `~/code`.
  - `scripts/run_render.sh`: full-site renders of origin/main and the front-story worktree HEAD from a copy of the live state, then `checks.run`, both teed into `checks-run.txt`. It copies the state to `/tmp/fs` first.
  - `scripts/render_site.py`: copied from `mailbox/learning-page-review3`, the same method Learning used.
  - `scripts/evidence.py`: writes the evidence files from the live site's data files.
  - `evidence/1-4*.md`: generated and current.
- **Interrupted:** the render run (`run_render.sh`) was stopped for the reboot. Nothing in `/tmp` is needed; the script rebuilds `/tmp/fs`.

## What is implemented (tools/site)

- **`story.py` (new):**
  - Headline table, "Risk calls leaderboard" (`#leaderboard`): one named setup per model, the model's setting with the highest stored risk judgement (Zeki #2578). Columns: rank, maker colour and icon, Released, risk judgement bar with its interval and the 50 line, risks found, right safety, error rate, cost. "All setups" toggle shows `home.all_risk_table`.
  - Section "Models are too cautious": clear-risk scan bias. Holds: all 45 model setups positive, GNUbg weak and Random negative.
  - Section "With the numbers on screen, every model asked played safer": Clear risk Part 2, Q1, with numbers vs board only. The direction holds for 8 of 8 models. The wording is an observation, per Zeki #2578.
  - Third heading (thinking / reasoning): dropped. Evidence in `evidence/3-thinking-dropped.md`; the Reasoning tab itself says its comparison is not paired and shows no effect of the setting.
  - One caveat per section, plus a "More caveats: Method" link.
- **`content/release_months.json` (new):** maker pages read 2026-11-07, with verbatim quotes. 26 models have a month; 6 are "—": Cygnet, Jev 1.13.0, Open-Jev 27B v1.1, Winnow-12B, SubQ Snap Preview (page names "SubQ Snap") and Qwen3.8 Flash (identity unconfirmed).
- **`home.py`:**
  - `HERO_LINKS` = the 3 buttons: "Read the method" (method/; no write-up exists); "Right risk calls, decision by decision" (`decisions/?r=risk&c=rr`, because Every decision has no engine's-best-play filter, so "Best decisions" could not be honest); "Every decision".
  - `filters()` is now one compact in-page nav row (`#filters`, the same bg.js hooks): League · Models · Measure links (Leaderboard, Risk judgement, Error rate, Cost, Time, Every number) · More filters (quick view, phase, reasoning, runs on, weights) · count · Reset.
  - The view bar's League/Models/Measure rows are removed (`home.view_rows` deleted; `write_all` no longer passes them).
  - `how_numbers` is renamed to "How the scoring works" and sits after the story sections.
  - Measure charts: one caveat each.
  - Home order: hero → filter row → leaderboard → findings ×2 → how scoring works → findings block → measure charts → leagues → every number → …
- **`bg.js`:** the anchor-key code of the old view-bar rows is removed; the headline toggle is added.
- **`bg.css`:** headline table, findings and filter-row styles.

## Next steps

1. `bash mailbox/front-story/scripts/run_render.sh ~/code/jevgammon-front`, then read `checks-run.txt`. Expect 0 failures on the branch.
2. Numbers against live: compare the branch render with the live mirror (the `mailbox/pws-style/packet_build.py` comparisons; adapt the league-pick state to `data-league-pick`, since the key labels changed to All/1/2/3). Also compare the headline cells and finding values with the live table cells and the clear-risk data file.
3. Links and deep links at 1280 and 390 px: `?league=`, `?type=`, `?tab=`, `#board`, `#lg-…`, `#leaderboard`, `#risk-judgement` … (Playwright with request routing; no server).
4. Screenshots at 1280 and 390, light and dark.
5. Build `mailbox/front-story-review.zip`: the diff (`git diff origin/learning-page...front-story -- tools/site`), checks, numbers, links, screenshots and the evidence files. Then report to Main.

## Open questions for Ümit

- **"Best decisions" button:** there is no engine's-best-play filter on Every decision, so the right-risk filter stands in. Should such a filter be built?
- **Third heading:** "Thinking helps open models…" was dropped; the evidence is in `evidence/3-thinking-dropped.md`.
- **"Read the write-up":** the button points to Method until a write-up exists.
