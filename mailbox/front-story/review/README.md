# front-story review packet

Branch `front-story` (5dd69fd), rebased onto `origin/main` 6d3664f. That base already includes learning-page 89c0f01 (pre-registration-only mode, `PREREGISTRATION_ONLY = True`) and the REAX / late-entry commits 4f6d556 and 2848e1f.

The rebase had no conflicts. `learning_page.py`, `learning_validate.py` and `checks.py` check 7 are main's, unchanged; the branch changes only `story.py`, `home.py`, `nack_section.py`, `pages.py` and the assets.

This is a candidate: it is not merged and not deployed. The review was render-only: no build.py main, no update.sh, no server and no model calls.

- `source.patch`: `git diff origin/main...front-story -- tools/site`.
- `../checks-run.txt`: whole-site renders of origin/main and of front-story from one copy of the live state (results f45081f6), each followed by `checks.run`. Both have **0 failures**.
- `numbers.md` / `numbers.csv`: the branch render against the live mirror. **0 differences:**
  - every live home-page table cell: 16,085
  - headline table cells against the live cell of the same setup: 160
  - finding values and the numbers in their sentences against `data/v3/clear-risk.json`: 70
  - main content of every other page: 111
  - data files: 104

  The comparison ignores the render time stamp. It leaves out the frozen `results/` snapshots, which are copied at deploy and not rendered.
- `page-diffs.md`: the other pages that differ. None now.
- `links.md` / `links.csv`: 2,786 checks at 1280 and 390 px.
  - No link is broken.
  - 823 links can't be resolved statically on either the live site or the branch. They are anchors that the Every decision page's script creates, and paths into the sibling site.
  - 192 addresses behave the same on live and branch.
  - The new addresses are all OK.
  - The headline toggle works.
  - Nackgammon Decision / Chat / All: in every state the "Unclear …" note and the additions note stay visible, and the yardstick rows are always shown. Decision shows 15 rows, Chat 16, All 30.
  - No script errors.
- `screenshots/`: 1280 and 390 px, light and dark: home top, leaderboard, the two findings, risk judgement, Every number, Nackgammon (All, Decision, Chat), and the whole home page.
- `../evidence/`: one file per finding heading, plus the dropped third heading and the headline selection with release months. All are from the live data files (results f45081f6).

## Notes for Ümit

- **Label "dropped" (Ümit #2651):** the Nackgammon table keeps the data's own word, "worse", next to "kept" and "unclear". "Dropped" would clash with the sensitivity rule "the pair is left out (drop)". No setup has the label "worse" at present.
- **Late entries (Zeki #2656):** the "4 setups were added after the results were read" note counts only the 28 Oct §10.14(g) additions. The 8 late entries have no Nackgammon results yet, so they have no block. When results exist, they get their own "Late entries / exploratory" block, separate from that note.
- **GPT-6.1 Terra:** it has no `setups.json` entry, so it is shown only under All.
