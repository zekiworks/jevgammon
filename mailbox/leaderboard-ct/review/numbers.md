# Numbers: leaderboard-ct render against live

Live: the deployed site's mirror; branch: the render of leaderboard-ct (5ca56de) and origin/main (a25b75e) from one copy of the live state, the same results hash. numbers.csv has one line per compared value (vs origin/main only where different).

| Compared | Values | Differences | New in branch |
|---|---:|---:|---:|
| Home page: every live table cell (every tab, both margins, All leagues and each league, All setups panel, Leagues block, Close choices, Nackgammon; the headline table in the next row) against the branch | 17,377 | 0 | 0 |
| Home page: every origin/main render table cell (every tab, both margins, All leagues and each league, All setups panel, Leagues block, Close choices, Nackgammon; the headline table in the next row) against the branch | 17,377 | 0 | 0 |
| Headline table, every row (ranked, other settings, programs): risk judgement and interval, risks found, right safety (live All leagues Risk table, 0.001), error rate and interval (every number), $ per 1,000 with its price label (whole cell), decisions (live Cost tab Decisions and Every decision's index), setting (setups.json), league | 432 | 0 | 0 |
| Too safe chart (new): right safety and risks found of each bar against the live All leagues Risk table | 32 | 0 | 0 |
| Finding sections: every value beside a bar against data/v3/clear-risk.json | 58 | 0 | 0 |
| Measure charts (Risk judgement, Error rate, Cost, Time): every bar's value, live against branch | 398 | 0 | 0 |
| Every other page: the main content, byte for byte after the render time stamp (100 frozen snapshots under results/ and archive/ are copied at deploy, not rendered, and left out) | 111 | 0 | 0 |
| Data files under data/, byte for byte (manifest.json without its generated time) | 105 | 0 | 0 |
