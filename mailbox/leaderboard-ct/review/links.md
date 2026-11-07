# Links and deep links: leaderboard-ct render

3604 checks: 3 build.py-only asset, absent from the origin/main render too, 21 external, 2551 ok, 206 same, 823 same as live (unresolved statically in both). links.csv has every one.

| Check | Result | Count |
|---|---|---:|
| address, branch only | ok | 6 |
| address, live vs branch | same | 206 |
| branch home link | ok | 407 |
| branch home link | same as live (unresolved statically in both) | 823 |
| branch home link (external, not fetched) | external | 21 |
| decision link: dataset and setup in Every decision's index | ok | 867 |
| live home link kept on the branch | build.py-only asset, absent from the origin/main render too | 3 |
| live home link kept on the branch | ok | 1201 |
| script errors | ok | 2 |
| tap a model: Every decision filtered to the setup | ok | 68 |

Existing links: every href of the live home page must still be on the branch home page (count ≥ 1). Branch links: the file in the render and its #fragment an id of the target page (external links listed, not fetched; an href unresolved statically in live and branch alike is 'same as live'); each decisions/?d=…&s=… link's dataset and setup are in Every decision's index with decisions. Addresses: opened at 1280 px and 390 px (Playwright, request routing, no server) on the live mirror and the branch; compared: the address after the page's script ran, the selected tabs, League and Model type filters, the rows shown in the open Every number tab, and for an #anchor whether its element is at the top of the window. Tap: each ranked row's and program row's model name clicked; Every decision must open with that dataset and setup (its script keeps s= only for a setup it found) and show decision cards.
