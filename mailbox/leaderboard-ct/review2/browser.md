# Browser tests (1280 and 390 px)

54 checks: 54 ok. browser.csv has every one.

Filters and expanders: the render's index.html opened from file:// (no server), light and dark. For each filter state (by address: type, league; by clicking a key of the filter row) the leaderboard must keep every row shown and every other-settings row hidden, and the Too safe chart every bar. Then every parent row's expander is clicked: the rows it shows must equal that parent's expected alternatives in evidence/expected-families.json (derived from the data files by evidence.py, not from the page's aria-controls), and a second click must hide them. Then All setups and back with an expander open.

Phase: the same render through request routing (bg.js fetches fragments/<league>-<phase>.html, which file:// refuses). The real control is used (More filters, then the Phase select) for every phase and back to All phases: the select's value, every phase slot's rows and cells against that phase's fragment file (All phases: against the page as loaded), the leaderboard and Too safe text unchanged, the DeepSeek row's open expander still open, no dialog, no script error (none excluded). The address does not carry the phase (bg.js reads ?league= and ?type= only): ?phase=race is checked to leave All phases and every slot as loaded.
