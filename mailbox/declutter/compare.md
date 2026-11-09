# Render comparison: origin/main against declutter

## 1. Files
2,552 files in origin/main's render, 2,552 in the candidate's; only in one: none; different: ['about/index.html', 'bg.css', 'index.html'].

Hero board: on About with the same markup (links one level up): yes; ids it carries: ['bd-arrow', 'bd-arrow-alt'].

## 2. Front page
origin/main's page, the moved blocks taken out and each finding's kept sentences put in: text identical to the candidate's. Kept sentences each part of the old paragraph: yes.

Required lines on the candidate's front page, verbatim:

| Line | On the page |
|---|---|
| Risk judgement: 100 = every call right, 50 = always safe; higher is better. | yes |
| One row per model at its highest reasoning setting, never its best score; late entries included. | yes |
| Ranks show observed scores; small gaps need not be meaningful. | yes |
| Leagues played different positions | yes |
| Unclear means the test can’t tell, not that the scores are equal. | yes |
| every 99% interval includes 0, so the test does not show the groups' drops to differ. | yes |
| Not paired: models met different positions in different leagues. | yes |
| Models without a documented release month are left out. | yes |
| Preliminary: two plays shown, not league play. | yes |
| Not paired: each setting played its own games; these are observed differences. | yes |
| Paired positions, not league play; a drop mixes the new start with how hard the positions are. | yes |
| One model, a small pilot; the plan, every number and the lessons are on its page. | yes |
| Outside the groups, the late entry | yes |
| No arm reached the pre-registered signal threshold (plan section 8). | yes |

## 3. About
Candidate's about/index.html without 'From the front page' (section and nav link): text identical to origin/main's.

## 4. Numbers
Front page: origin/main's numbers = the candidate's - its kept sentences + the moved blocks: yes (6,403 numbers before, 6,317 after, 93 in moved blocks). About: the candidate's numbers = origin/main's + its new section's: yes; in that section beyond the moved blocks: none. No number changed: every number that left the front page is on About in the same sentence.

## 5. Anchors
Front page: 134 ids on origin/main's, 132 on the candidate's; lost (not on the page, not in the moved-anchors map): none. About: 16 ids before, 26 after; lost: none; new: ['bd-arrow', 'bd-arrow-alt', 'front-example', 'front-intro', 'front-page', 'text-finding-cautious', 'text-finding-flinch', 'text-finding-nackgammon', 'text-finding-reasoning', 'text-finding-release']. Board ids lost: none.


**Failures: 0**
