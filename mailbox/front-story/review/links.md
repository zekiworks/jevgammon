# Links and deep links: front-story render

2782 checks: 26 external, 1741 ok, 192 same, 823 same as live (unresolved statically in both). links.csv has every one.

| Check | Result | Count |
|---|---|---:|
| address, branch only | ok | 32 |
| address, live vs branch | same | 192 |
| headline toggle | ok | 2 |
| home link | ok | 1697 |
| home link | same as live (unresolved statically in both) | 823 |
| home link (external, not fetched) | external | 26 |
| nackgammon type keys | ok | 8 |
| script errors | ok | 2 |

Home links: every href of the branch home page, the file in the render and its #fragment an id of the target page (external links listed, not fetched). Addresses: opened at 1280 px and 390 px (Playwright, request routing, no server) on the live mirror and the branch; compared: the address after the page's script ran, the selected tabs, the League (keys now All/1/2/3, mapped from the live labels) and Model type filters, the rows shown in the open Every number tab, and for an #anchor whether its element exists and is at the top of the window below a sticky bar. Branch-only addresses (new anchors, hero buttons' targets): loaded, target in view, no horizontal overflow.
