# Old URLs and anchors

334 checks: 334 ok. urls.csv has every one.

Static: every page of the live mirror and of the leaderboard-ct render (frozen archive/ and results/ snapshots aside, which deploy copies) is a page of nav-ct at the same path, and every id on it (every #anchor) is still on the nav-ct page. checks.run (checks-run.txt) also resolves every relative link and #anchor of every nav-ct page.

Browser (1280 and 390 px, request routing, no server): every link of the old navigation (leaderboard-ct's pages row and Part row) and the home page's part links, and the deep links listed in review.py, opened on nav-ct: status 200, the #anchor's element exists and its top is below the sticky header, and the tab marked in the header is the page's tab.
