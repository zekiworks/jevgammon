# Live switch: log

Oct 23, 2026, 18:04 UTC · B2 switch, approved by Ümit (relayed by Can).

**Live:** https://zekiworks.github.io/analysis/backgammon/ now serves the new site.
- Results `ce40d3b0`, data as of 23 Oct 18:02 UTC.
- Analysis repo commit `b4fd12ac`.
- Code: jevgammon `bfa544f`.
- Findings still read "Findings will be published after review."

## What changed

1. **The build targets the live address.**
   - `build.BASE` is now `https://zekiworks.github.io/analysis/backgammon/`. Every canonical, `og:url`, `og:image`/`twitter:image` and risk-call-card URL uses it. The PNG downloads print the page's own address, which is now the live one.
   - Internal links were already relative.
   - The `noindex` the preview carried is gone: the live page had none before either.
   - The brand line now reads "Zeki Works · Backgammon benchmark · v3" (no "preview").
2. **The update loop deploys to the live site** (`tools/site/update.sh`).
   - It builds into `analysis/backgammon/` and commits only `backgammon/` and `backgammon-preview/`.
   - Pre-deploy checks are unchanged, and a failed check still blocks the deploy.
   - The timer keeps its old name, `bg-site-preview.timer`, and runs every 15 minutes. It ran at 18:05 and found nothing new.
   - The first live deploy ran at 18:02 (`--force`). The timer was paused during the switch and is active again.
3. **The preview path redirects.** I chose redirects over a mirror:
   - every page under `/analysis/backgammon-preview/` is now a redirect to the same page on the live address, keeping the query and the anchor;
   - the redirect is a `location.replace` plus a meta refresh, with `noindex` and a canonical pointing to the live page;
   - data files under the old preview path (for example `backgammon-preview/data/results.json`) are gone; only pages redirect.
4. **The old page is kept.**
   - The page that was live until now (final data, 23 Oct 02:50 UTC) is frozen at https://zekiworks.github.io/analysis/backgammon/archive/2026-10-23/. Its `v3-results.json` sits beside it.
   - It has an "Archived" banner and a canonical pointing to itself, and it is linked from Leagues (`#pre-switch`) and from the Method intro.
   - The pre-deploy checks treat it as frozen: its links are checked and the private-data scan covers it. The number-trace and mixing checks skip it, because its numbers come from its own data file.
   - The old top-level `backgammon/v3-results.json` moved into the archive folder.
5. **The old anchors still work.** On the new home page, an old anchor that the new page lacks opens its new place:

   | Old anchor | Opens |
   | --- | --- |
   | `#v3`, `#v3-title` | `leagues/` |
   | `#v3-l1/l2/l3`, `#v3-league1/2/3` | `leagues/#league-N` |
   | `#v3-anchor` | `method/#v3-anchor` |
   | `#v3-dice` | `method/#exp-dice` |
   | `#v3-changes` | `method/#v3-changes` |
   | `#setup`, `#models`, `#error-rate`, `#results`, `#allstar`, `#speed-cost`, `#limits` | `leagues/#v1-…` (the collapsed "Earlier version" block opens) |
   | `#prompt` | `method/#v1-prompt` |
   | `#changes` | `method/#v1-why` |

   Each `-title` variant of these anchors opens the same place.
6. **The old pipeline is retired.**
   - Its timer had already removed itself on 23 Oct 02:52.
   - I removed the remaining `v3-page-refresh.service` link and **masked** both `v3-page-refresh.service` and `v3-page-refresh.timer`.
   - `tools/v3/page_refresh.sh` now exits at once with "retired" unless an explicit override variable is set. So the midnight-takeover script, which still names that service, cannot overwrite the site either.

## Nothing from the old page is lost

I compared the old page's text, sentence by sentence, with the new build:
- **v1 sections** (setup, models, prompt, why it looks like this, error rate, results, teams, speed and cost, limits) are all present:
  - Leagues holds `#v1-*`;
  - Method holds `#v1-prompt` and `#v1-why`.
  - The only unmatched sentences are section titles glued to their first sentence, plus one wording change made on purpose in v6 ("level" became "no clear difference").
- **v3 section:**
  - **Tables and league notes:** now generated from the current data on Leagues.
  - **The anchor note:** in Method, `#v3-anchor` and `#exp-anchor`.
  - **Shared dice:** in Method, `#exp-dice`.
  - **Changes during the leagues:** in Method, `#v3-changes`.
  - **Setup prose and the off/on definitions:** reworded in Method `#setup`; the off/on definitions are also on each model page.
  - **Exact sentences:** some of the old v3 prose and the old generated league notes were reworded rather than copied. Every one of them is unchanged in the frozen archive page, so nothing is lost.

## Checks on the public URL (exercised, after the deploy)

- **Plain fetch, as a visitor** (urllib, no JavaScript):
  - `/analysis/backgammon/` returns 200.
  - Title: "Can a model tell when a risk is worth taking? · Zeki Works".
  - Results line: "Results ce40d3b0, updated 23 October 2026, 18:02 UTC; scored by GNU Backgammon 1.08, 2-ply." It matches `data/manifest.json` (ce40d3b0, 18:02Z).
  - Findings line: "Findings will be published after review."
  - The canonical is the live URL, and "backgammon-preview" appears 0 times.
- **Banned-string scan of what a visitor downloads:** 118 files, 0 hits, 0 fetch failures. They are:
  - every page;
  - all 83 data files in the manifest;
  - `decisions/index.json`;
  - the scripts and stylesheets;
  - the 15 phase fragments;
  - the archive page and its JSON.
- **Headless Chromium at 1280 and 390 px, dark and light:** 64 page loads, **0 console errors**, 0 elements wider than the screen.
  - Pages: home and its tab/league views, Leagues, Phases, Compare, Where models disagree, Method, Data, New models, Models, a model page, two filtered Every decision views.
  - The home page opens on League 1 with the Risk tab and "19 of 19 setups". The Phase filter (Race) loads its fragment. Model type = Decision gives "15 of 19".
- **Old anchors on the live home page:** all 12 tested go to the targets in the table above, and each target exists and is not hidden in a closed block.
- **Preview redirects:** each of these reached the same page on the live address, query and anchor kept:
  - `/backgammon-preview/`
  - `?tab=quality#board`
  - a filtered `decisions/?…` link
  - `method/#risk`
  - `leagues/#league-2`
- **Archive page:** it loads with its banner and gives no console errors.
