# front-story review packet

Branch `front-story` (b43fe74), rebased onto `origin/learning-page` 678b225. This is a candidate only: it is not merged and not deployed. Render-only: no build.py main, no update.sh, no server, no model calls.

- `source.patch`: `git diff origin/learning-page...front-story -- tools/site`.
- `../checks-run.txt`: whole-site renders of origin/main and of front-story from one copy of the live state (results 04493cf3), each followed by `checks.run`. Both have **0 failures**.
- `numbers.md` / `numbers.csv`: the branch render compared with the live mirror.
  - Every live home table cell: 16,080 compared, 0 differences.
  - Headline table cells against the live cell of the same setup: 160, 0 differences.
  - Finding values and the numbers in their sentences against `data/v3/clear-risk.json`: 70, 0 differences.
  - Data files: 103, 0 differences.
  - Other pages: 110, 2 differences. Both come from the base branch and are listed in `page-diffs.md`:
    - `data/index.html` lists `learning-pilot.json`, a learning-page addition.
    - `method/index.html` lacks §10.14(i) "Late entries, exploratory", which is on origin/main (d72bd46…) but not on `origin/learning-page`, because that branch is behind main.
- `links.md` / `links.csv`: 2,782 checks at 1280 and 390 px.
  - 0 broken links. 823 links do not resolve statically on either live or branch: decision anchors that the Every decision page's script creates, and sibling-site paths.
  - 192 addresses give the same result on live and branch.
  - 32 new addresses are OK.
  - The headline toggle works.
  - Nackgammon Decision / Chat / All works: in every state the "Unclear …" note and the additions note stay visible, the yardstick rows are always shown, and the row counts are 15 / 16 / 30.
  - No script errors.
- `screenshots/`: 1280 and 390 px, light and dark. Shots: home top, leaderboard, the two findings, risk judgement, Every number, Nackgammon (All, Decision, Chat), and the full home page.
- `../evidence/`: one file per finding heading, the dropped third heading, and the headline selection with release months. Taken from the live data files (results 04493cf3).
- `nack_paired_verify.py --saved-only` gives the same result on the branch render as on main. Its 110 "private string 'decision-models'" lines on model pages are pre-existing. One more on `learning/index.html` comes from learning-page. The new Nackgammon table is checked cell by cell and in row order.
