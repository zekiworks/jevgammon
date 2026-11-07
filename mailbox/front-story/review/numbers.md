# Numbers: front-story render against live

Live: the deployed site's mirror (/home/cbasaran/.local/state/bg-site/analysis/backgammon); branch: the render of front-story (5dd69fd) from a copy of the live state, the same results hash. numbers.csv has one line per compared value.

| Compared | Values | Differences | New in branch, not in live |
|---|---:|---:|---:|
| Home page: every live table cell (Risk, Quality, Confidence, Reasoning, Cost tabs, both margins, All leagues and each league; Leagues block; Close choices; Nackgammon) against the branch | 16,085 | 0 | 1,236 |
| Headline table (new): risk judgement and interval, risks found, right safety (All leagues Risk table, margin 0.001), error rate and interval, $ per 1,000 decisions (the league's Quality table) against the live cell of the same setup | 160 | 0 | 0 |
| Finding sections (new): every value beside a bar, and every number in the sentences, against data/v3/clear-risk.json (scan per-setup bias; Part 2 Q1 bias with numbers and board only) | 70 | 0 | 0 |
| Every other page: the main content, byte for byte after the render time stamp (100 frozen snapshots under results/ and archive/ are copied at deploy, not rendered, and left out) | 111 | 0 | 0 |
| Data files under data/, byte for byte (manifest.json without its generated time) | 104 | 0 | 0 |
