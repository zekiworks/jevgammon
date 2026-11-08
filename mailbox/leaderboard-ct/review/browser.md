# Browser tests from file:// (1280 and 390 px, light and dark)

44 checks: 44 ok. browser.csv has every one.

The branch render's index.html opened from file:// (no server, no routing). For each filter state (by address: type, league, phase; by clicking a key of the filter row) the leaderboard must keep every row shown and every other-settings row hidden, the Too safe chart every bar; then every row's expander is clicked: it must show exactly its own rows (aria-expanded true), no other row, and hide them again on a second click. Then the All setups key and back with an expander open. Expected counts come from the static HTML.
