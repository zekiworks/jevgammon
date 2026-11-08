# ct-brief: Ümit's brief (bus #2938) against what is live

Live = origin/main e70840e (nav-ct c780767 + learning page), mirror of https://zekiworks.github.io/analysis/backgammon/
(results a8708ed6). Status: **done** = live already does it; **partly**; **missing**; **conflict** = live does something
the brief changes. The branch changes only what is not **done**.

## 1 Navigation

| Item | Live | Status | Branch |
|---|---|---|---|
| Slim Hilde site row; top bar leaf + "Backgammon bench" + 5 tabs, active underline, phone tab row scrolls, top bar fixed | yes (nav-ct) | done | unchanged |
| PART row, PAGES row removed | yes | done | unchanged |
| In-page chip rows ("Risk judgement · Error rate · Cost · Time · Leagues and matches · Every number · Findings · Method") | hero `face-nav` + More pages row + the filter row's "Measure" part links | conflict | removed from home (the filters move to Leagues without their part-link chips) |
| "Filters and parts of this page" section | on home | conflict | removed from home; the filter controls (league, model type, More filters) sit on Leagues above the measure sections and Every number they filter (title "Filters") |
| Decisions tab links Where models disagree, Phases, Compare | no (only via More pages) | missing | link row under the Decisions page's first card |
| Experiments: Clear risk, Nackgammon, Learning from experience | yes | partly | statuses changed (below) |
| About: text from backgammon_rules_page.md; links Method, Data, Leagues, Matches | old About (prompt rules quote, Method, Data, …) | missing | Ümit's 4 sections from `content/about.md` (CHECK-LINES.md), then a link row Method · Data · Leagues · Matches · GitHub; the old About sections kept below them (their anchors land) |
| One name "Learning from experience" | yes on Experiments and the page title | done | the home finding links it by that name |

## 2 Front page

| Item | Live | Status | Branch |
|---|---|---|---|
| Hero: question, one paragraph, example board + caption | yes, plus eyebrow, subtitle, version line, 3 result boxes, What this measures, match winners, leaders, facts, chips, More pages | partly | hero is only: question (h1), paragraph, counts line, 3 buttons, board + caption |
| Counts line "92,888 decisions scored · 3 leagues · 45 setups · 38 models · updated <date>" | readouts, no date | missing | `home.counts_line` from S["counts"] and the as-of date |
| Buttons Every decision, Highlights, Read the method | Read the method, Right risk calls…, Every decision | conflict | the 3 named buttons |
| Leaderboard second | yes | done | text around it cut to 2 lines (below) |
| Finding sections a–f, each heading a finding + one chart + 2–3 sentences + one link | 2 sections (Too cautious = clear-risk bias bars; Numbers on screen) + Too safe bars under the table | partly | 6 sections in order; each heading decided by a rule on the shown values (evidence/a.md … f.md) |
| a Two-skill chart risks found vs safe right, maker colours, GNUbg weak grey | Too safe paired bars (same values) | conflict | scatter, maker colours, GNUbg weak grey square; the old bars kept under it in "Every model's two values"; the old clear-risk bias chart moved to the Clear risk page (#clear-risk-bias) |
| b Release-date chart, documented months only, heading only if data shows it | missing | missing | chart; heading **neutral** ("Risk judgement by release date") |
| c Clear risk kept | yes | done | link to Clear risk (preliminary) instead of Method |
| d Reasoning across models with ≥2 settings | missing | missing | chart over the 9 such models; heading **neutral** ("What thinking adds") |
| e Nackgammon, Random as reference, keep "unclear means…" | paired test section on home (no finding heading) | partly | finding section with the test's own chart; heading "A new starting position: no clear drop in any group"; the full test moved to its own page |
| f Learning status + chart | missing on home | missing | status line, the published verdict sentence, the risks-found chart |
| "How the scores work": 5 bullets | "How the scoring works": 5 Method quotes | conflict | Ümit's 5 bullets; the Method quotes moved to About under "How the scores work" |
| Footer About · Method · Data · GitHub | downloads + version only | missing | footer link row on every page (GitHub = https://github.com/zekiworks/jevgammon, public) |
| Move to Leagues: 3 boxes, leaders, Scorer/Results/Published, per-metric × league sections, Starting groups, After league moves, notes/quality/cost, Cups, Hype Cup, knockout, Late entries, Every number | on home (league block as a copy with lg- ids; the Leagues page already had the league sections) | missing | Leagues page: overview (3 boxes, What this measures, match winners, leaders, facts) → league tabs (as before) → filters → measure sections → Every number (+ charts) → Risk pays vs safety pays → Close choices stage B. The two last blocks were not named by the brief; they left the front page with Every number. |
| Old anchors land on the moved section | n/a | missing | the build writes every moved id into `#moved-anchors` on home; bg.js sends `#id` (and the old `#lg-…` ids) to `leagues/#id` or `nackgammon/#id`, query string kept |

## 3 Leaderboard

| Item | Live | Status | Branch |
|---|---|---|---|
| One row per model at highest setting, rule stated | yes | done | rule in one line under the table |
| Late entries tagged and ranked; versions separate; DeepSeek 1017 folded | yes | done | unchanged |
| Row: rank · dot · name with type under · bar (whisker, white tick at 50) · score | tick is grey (`--text-2`) | partly | white tick with a thin dark edge |
| Wide screens: risks found, safe right, error rate, $ per 1,000 | missing | missing | 4 columns shown at ≥ 900 px, each the box's stored value |
| Details box lines in Ümit's order | same lines, other order (setting/league line second) | partly | name · maker / risk judgement / both halves / raw counts / error rate · record · late entry, then the other stored lines |
| Filter All · Chat · Decision, All setups toggle | yes | done | unchanged |
| Text around table: two lines; the four sentences and "Released:" to About | 5 notes | conflict | line 1 the score's meaning, line 2 the row rule (with the All leagues note the checks require); the rest on About #leaderboard |

## 4 Highlights

| Item | Live | Status | Branch |
|---|---|---|---|
| Astra (low), League 3, decision 108669: board, model play, engine play | candidate label only | missing | slot 1 from the export, its facts checked at build (`content/highlights.json`); story "Story coming" |
| Other slots | 6 candidate/empty slots | partly | labels follow the brief's list (Sol with/without numbers, great risk, blunder, decision-model surprise, a lesson later) |

## 5 Experiments

| Item | Live | Status | Branch |
|---|---|---|---|
| Clear risk "preliminary" | "Preliminary / partial" | partly | "Preliminary" |
| Nackgammon "finished", own page from nack-paired data (per-setup table + method text) | section on home, no status | missing | `nackgammon/` (the section as it was, links rebased), card status Finished |
| Learning status running/done | "Complete" | conflict | the learning page's own status line ("Done") |
| Learning page status line, results, charts, lessons | yes (e70840e) | done | unchanged (two functions factored, output identical) |

## 6 About

| Item | Live | Status | Branch |
|---|---|---|---|
| backgammon_rules_page.md text, 5 [check] lines fixed | missing (file arrived bus #2939) | missing | done; CHECK-LINES.md |
| Links Method, Data, Leagues, Matches, GitHub | partly (More pages) | partly | link row |

## Checks in the brief

All run in `review/` (README: Results).
