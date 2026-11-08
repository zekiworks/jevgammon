# Numbers: the ct-brief render against live

Live: the mirror of https://zekiworks.github.io/analysis/backgammon/ (results a8708ed6). The new render is rendered from the retained computed state (no compute), data-as-of label set to live's.

| Check | Items | Values | Differences |
|---|---:|---:|---:|
| Live home tables, cell by cell (header and row label), where each now is | 173 | 17,377 | 0 |
| Live home id'd blocks (every id, nested ones too): numbers as a multiset where each now is | 215 | 215 | 4 |
| Leaderboard rows (rank, model, risk judgement), details-box numbers, wide cells within their box | 63 | 63 | 0 |
| Too safe bars | 39 | 39 | 0 |
| Clear-risk bias bars (home -> Clear risk page) | 50 | 50 | 0 |
| Numbers on screen bars (finding c) | 8 | 8 | 0 |
| Pages compared, main content text against live: 114 compared, 107 equal, 7 expected changes (the pages this change touches); differences count unexpected changes only | 114 | 114 | 0 |
| Data files and decision pages: equal after gunzip of .gz files, data/manifest.json excluded from the comparison (not literal raw-byte identity); new files: none | 2,403 | 2,403 | 0 |

**Total differences: 4**, of which 4 explained and 0 unexplained. Every difference is in `numbers.csv`. The script still exits 1 on any difference.

- explained: `#leagues-tabs` — old wrapper held the league sections; now the Leagues tab bar
- explained: `#board-panel` — Risk call card line (build.py image step only)
- explained: `#charts` — Risk call card line
- explained: `#chart-risk` — Risk call card line

Pages whose main content changed (expected: the pages this change touches):

- `about/`
- `clear-risk/`
- `decisions/`
- `experiments/`
- `highlights/`
- `home`
- `leagues/`
