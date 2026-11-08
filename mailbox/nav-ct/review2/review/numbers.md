# Numbers: nav-ct render against live and leaderboard-ct

Live: the deployed site's mirror; nav-ct: the render of 90cd56e; leaderboard-ct: the render of d345323 from the same copy of the live state and results hash. Every comparison is label-aware: a value is compared with the value of the same setup under the same label (table, row and column; box line; chart bar). numbers.csv has one line per compared value.

| Compared | Values | Differences | New in nav-ct |
|---|---:|---:|---:|
| Home page: every live table cell, by table, row and column (every tab, both margins, All leagues and each league, the All setups panel, Leagues block, Close choices, Nackgammon; the leaderboard in the next rows) | 17,377 | 0 | 0 |
| Home page: every leaderboard-ct render table cell, by table, row and column (every tab, both margins, All leagues and each league, the All setups panel, Leagues block, Close choices, Nackgammon; the leaderboard in the next rows) | 17,377 | 0 | 0 |
| Leaderboard rows (ranked, other settings, programs): the risk judgement and its 95% interval against the live All leagues Risk table, same setup and label | 54 | 0 | 0 |
| Details boxes: every line of every row's box (setup and maker, setting and league, risk judgement and interval, risks found and safe right, took n of N and played safe m of M, error rate and interval, record, cost with its price label and decisions, release month, links) against the data files (data/v3/<league>/<setup>.json, data/v3/<league>.json standings, data/setups.json, content makers and release months), text equal | 445 | 0 | 0 |
| Details boxes against the live page's own tables, label by label (risks found and right safety: share, n and N, live All leagues Risk table; error rate and interval and $ per 1,000 with its price label, live Quality tab; decisions, live Cost tab) | 208 | 0 | 0 |
| Measure charts (Risk judgement, Error rate, Cost, Time): every bar, label and value, live against nav-ct | 398 | 0 | 0 |
| Finding sections: every bar, label and value, live against nav-ct | 58 | 0 | 0 |
| Too safe chart: every bar, label and value, leaderboard-ct render against nav-ct | 32 | 0 | 0 |
| Every other page (live): the main content, byte for byte after the render time stamp (100 frozen snapshots under results/ and archive/ are copied at deploy, not rendered, and left out) | 111 | 0 | 0 |
| Every other page (leaderboard-ct render): the main content, byte for byte after the render time stamp (0 frozen snapshots under results/ and archive/ are copied at deploy, not rendered, and left out) | 111 | 0 | 0 |
| Data files under data/ (live), byte for byte (manifest.json: every file entry and every field but its generated time) | 105 | 0 | 0 |
| Data files under data/ (leaderboard-ct render), byte for byte (manifest.json: every file entry and every field but its generated time) | 105 | 0 | 0 |
