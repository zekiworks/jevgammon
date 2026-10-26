# Site simplification, 26 Oct 2026

The backgammon site is at https://zekiworks.github.io/analysis/backgammon/. Part 1 is live. Part 2 is a proposal only. Screenshots are in `mailbox/site-simplification/` (WebP, 1× pixel density, 1.8 MB for all 45 files).

## Part 1: flat style (done, live)

### What changed
Two files changed: `tools/site/assets/site.css` and `tools/site/assets/bg.css`. No data, numbers, URLs or HTML changed.

- **Variables removed** from both files, in both themes (the light `:root` block and the dark block): `--shadow`, `--key-shadow`, `--key-inset` and `--lamp-glow`. `--accent-soft` was only used by the old selected state, so it went as well. One variable was added: `--on-accent`, the text colour on an accent fill (light `#ffffff`, dark `#0f172a`).
- **Places that used them**, now flat:
  - `button.key`, including its `:active`, pressed and disabled rules. `:active` now uses the flat `--sunk` fill instead of an inset shadow.
  - `button.mode` (the leaderboard tabs), including `:active` and selected.
  - `button.pick` and its pressed state.
  - `.panel` and `.card`, `.mini-chart` and `.worked-example`.
  - `.lamp`: the 1px inset ring is gone, and so is the on-state glow.
  - The `box-shadow: none` overrides in bg.css and on `.board-panel .chart-card` were removed, because there is nothing left to override.
- **New look**:
  - Every control keeps its 1px border in the existing tokens (`--control-edge`, `--edge`), with flat fills.
  - **Selected state:** the pill is filled with the accent and has an accent border. Text and lamp are drawn in `--on-accent`. Contrast is 5.5:1 in light (white on `#0f766e`) and 9.6:1 in dark (`#0f172a` on `#2dd4bf`).
  - This applies to the filters, the league pick, the theme switch, Table / Charts, the six leaderboard tabs, the chart tabs, the margin keys and Show all.
  - The old selected rule in site.css had higher specificity than the one in bg.css, so pressed filter keys used to show a dark edge while selected tabs showed the teal edge. Now both look the same.
- **Kept on purpose**: a few flat lines are drawn with `box-shadow` but are not shadows.
  - 1px inset lines that act as borders on sticky table headers and sticky first columns: `.table-wrap thead th`, `.table-wrap td:first-child`, `#close-b-table tbody th`, the sticky column of `.heatmap-table` and the phone sticky column. With `border-collapse`, a normal border does not stay with a sticky cell.
  - The 1px edge of the `i.ramp` swatch.
  - The 3px bar that marks a selected row (`table.board tr.is-selected td.model`) and the chosen play on Every decision (`decisions.css`).
- **Inline styles in `tools/site/*.py`**: none use a shadow. I checked them all.
- **Not changed:** `tools/site/archive_page/index.html` still has its own `--shadow`. This is the frozen copy of the page from before the switch, served under `archive/<date>/`. It was outside the stated scope (assets and inline styles in the .py files), so I left it as it is.

### Commit, deploy, live check
- Commit `2043317` ("site: flat style - remove key shadows, panel shadows and lamp glow; selected pills filled with the accent") contains only the two CSS files. It went in after `pull --rebase --autostash` and was pushed to main.
- **Deploy**:
  - I started `bg-site-preview.service` once. The run went from 14:24:46 to 14:26:40 UTC and pushed analysis commit `5ecb7733c` (data as of 14:24Z, results 318f520b).
  - The CSS actually reached the live site one run earlier. The 14:20 timer run (analysis commit `1dba55194`) copied the assets from the working tree, which already held my edits before I committed at 14:24:40.
  - The content is identical to the commit. This happens because update.sh builds from the working tree, while its change key uses the committed `tools/site`.
- **Live check with curl** (cache-busting query string):
  - `site.css`, `bg.css` and `decisions.css` contain no match for `--key-shadow|--key-inset|--lamp-glow|--shadow`.
  - The served `bg.css` contains `--on-accent` (4 hits), so the new file is the one being served.
- **Local build:** `build.py` was run into a throwaway folder in /tmp and `checks.py` passed (exit 0, no failures). That build prints results hash `dfe49442`, which is not the published one; it only served the screenshots. The published results hash after the deploy is still 318f520b.

### Screenshots (`mailbox/site-simplification/`)
- **Pages:**
  - home = the home page top;
  - board = the home leaderboard scrolled to the Filters, which shows the league view with the league pick, the filters, Table / Charts and the six tabs;
  - model = `models/league-1/gpt-6-luna/`;
  - decisions = `decisions/` (Every decision).
- **Before** (live site, before the change): `before-{home,board,model,decisions}-{light,dark}-{1280,390}.webp` (16 files).
- **After** (local build): `after-{home,board,model,decisions}-{light,dark}-{1280,390}.webp` (16 files).
- **Keyboard focus**, reached by pressing Tab in the browser (desktop 1280, both themes):
  - `after-focus-league1-{light,dark}-1280.webp`: focus on the selected League 1 pill.
  - `after-focus-league2-{light,dark}-1280.webp`: focus on an unselected pill.
  - `after-focus-quality-{light,dark}-1280.webp`: focus on the Quality tab, next to the selected Risk tab and Table.
- **Light and dark**: the after shots show the theme switch with the chosen theme filled. Selected pills and tabs are clearly filled in both themes, and unselected ones are flat with a 1px edge.
- **Focus**: the `:focus-visible` rule is unchanged (2px solid `--focus`, offset 2px).
  - Computed values on the focused pills and tabs: `matches(':focus-visible')` is true, the outline is 2px solid `rgb(15,118,110)` in light and `rgb(94,234,212)` in dark, and box-shadow is none.
  - Because of the 2px offset, the ring is also visible around an accent-filled pill.

### Decision-models page
It does not share these files.
- Its pages (`decision-models/` in the analysis repository; I checked the copy the update service clones) load their own `v3.css` (`../v3.css`, `../../v3.css`). They do not load `backgammon/site.css` or `bg.css`.
- `v3.css` comes from the same design, but it is a separate file (it differs from `backgammon/site.css`). It still has its own shadow and lamp-glow variables (20 matches).
- The update service only builds and commits `backgammon/` and `backgammon-preview/`, so I left decision-models as it is. The backgammon site still neither mentions nor links it.

## Part 2: fewer controls on the first screen (proposal only, not built)

### What the first screen holds now
- **Desktop 1280×800**: the brand, 7 nav links, Export page as PNG, the Dark / Light switch, the two league-winner links and Open this decision. Then most of the Filters panel:
  - League (4 pills) and Model type (4);
  - Phase (select) and Reasoning (6);
  - Runs on (5) and Weights (3);
  - the setups count and Reset are just below the fold.
- That is 38 controls on the first screen, counting the skip link.
- **Phone 390×844**: the brand, the nav (a strip that scrolls sideways; 4 of 7 links visible), Export page as PNG on its own row, the Dark / Light switch, and the two league-winner links. The Filters panel is below the fold.

### Proposal
Make two folds that open when needed:
- **"More options" button in the top bar**: it replaces Export page as PNG and the theme switch, and holds both.
- **"More filters" key in the Filters panel**: it holds Phase, Reasoning, Runs on and Weights. It opens by itself when one of those filters is not at its default (for example from a shared link), and while it is closed its label says how many hidden filters are active. The setups count and Reset stay visible, so a filtered table never looks unfiltered.

| Control | Purpose | Proposal | Reason |
|---|---|---|---|
| Skip to content (hidden until Tab) | Keyboard users jump past the header | Stay | Accessibility; takes no space |
| Brand link "Hilde · Backgammon benchmark · v3" | Back to home | Stay | Identity and way home |
| Nav: Every decision, Where models disagree, Phases, Compare, Leagues, Method, Data | Site navigation | Stay | Main way through the site; already one line (a sideways strip on phone) |
| Export page as PNG | Saves the page as an image | More options | Occasional, for sharing; not needed to read results. On phone it takes a whole row of the first screen |
| Theme switch: Dark background / Light background | Colour theme | More options | The site already follows the system setting and remembers a choice. Changed once, not on every visit; two wide buttons at the top right |
| League winners: GNUbg weak, Gemini 3.8 Flash (low) | Open the winning model pages | Stay | Content links that are part of the headline result |
| Open this decision (under the board) | Opens the decision shown on the board | Stay | Content link of the hero example |
| League: League 1 / 2 / 3 / Shared positions | Which league every table and chart shows | Stay | The main choice; changes everything below |
| Model type: All / Decision / Chat / Program | Filter rows by model type | Stay | Short, often used, explains the three model families |
| Phase (select) | Filter decisions by game phase | More filters | Detail for readers who want to dig deeper; the default (all phases) is what most readers need |
| Reasoning: All / High / Low / Off / On / None | Filter by reasoning setting | More filters | Six pills; mainly matters for chat models |
| Runs on: All / API / CPU / Our GPUs / Subscription | Filter by where the model runs | More filters | Detail; five pills |
| Weights: All / Closed / Open | Filter by open or closed weights | More filters | Detail; three pills |
| "N of N setups" and Reset (just below the fold on desktop) | Shows the effect of the filters and resets them | Stay | Must stay visible when filters are folded away, so a filtered table is never hidden |
| Table / Charts and the six leaderboard tabs (below the fold) | Result views | Stay (not on the first screen) | Main navigation of the results; unchanged |

Effect:
- Desktop goes from 38 controls on the first screen to 22: brand, 7 nav links, More options, 3 content links, 8 filter pills, More filters, and the skip link.
- Phone loses the Export row and the two theme buttons: the title moves up by one row, and the top bar has one button instead of three.

### Screenshots (`mailbox/site-simplification/`)
- **Before**: `before-home-{light,dark}-1280.webp` and `before-home-{light,dark}-390.webp` (live).
- **Mock after**: a throwaway mock (the local build with its DOM changed in the browser; nothing committed to `tools/site`):
  - desktop, closed: `mock-after-home-{light,dark}-1280.webp`;
  - desktop, both folds open: `mock-after-home-dark-open-1280.webp`;
  - desktop, Filters with More filters open: `mock-after-filters-dark-open-1280.webp`;
  - phone, closed: `mock-after-home-{light,dark}-390.webp`;
  - phone, More options open: `mock-after-home-dark-open-390.webp`.

Part 2 waiting for approval

## update.sh publishes only committed site code (fix, before Part 2)
On 26 Oct the 14:20 timer run published the Part 1 CSS from the working tree a few minutes before it was committed. The cause: `update.sh` named the committed `tools/site` in its change key, but it built from the working tree.

- **Fix**: commit `1d59c08` changes `tools/site/update.sh`, and the change is pushed.
  - Every step now runs from `~/.local/state/bg-site/src`: the snapshot, the GNUbg scoring, the build and checks, and the findings draft.
  - That folder mirrors the repository with one symlink per top-level entry and per entry of `tools/`.
  - Its `tools/site` is the committed tree, extracted with `git archive` from `HEAD:tools/site`. This is the same tree id the change key uses.
  - It is rebuilt on every run, under the existing lock. Working-tree edits under `tools/site` cannot reach the site.
  - When the working tree has some, the run logs: `tools/site has uncommitted changes; ignored: building the committed tree <id>`.
  - Data files (v3.db, replay.db, positions, leagues, smoke) are read through the symlinks, as before.
  - `update.sh` itself is still run from the working tree by systemd.
- **Test with a dirty working tree**:
  - I appended an uncommitted marker comment to `tools/site/assets/bg.css` and started `bg-site-preview.service` once (15:00 UTC).
  - The log shows the "uncommitted changes; ignored" line, and the run deployed (analysis commit `5573ff448`).
  - The marker was in neither the built `backgammon/bg.css` nor the live `bg.css` (curl: 0 matches). I then removed the marker.
  - The 15:05 timer run hit the same case for real: my uncommitted Part 2 edits were in the working tree. It logged the same line, and the live HTML had no Part 2 markup until the commit below.
- **Test with a clean working tree**: the committed Part 2 (below) was published by the next run.

## Part 2 built (approved by Can with three additions)
Commit `92da8a1` changes only `tools/site`: `pages.py`, `home.py`, `assets/site.css`, `bg.css`, `site.js` and `bg.js`. It is pushed.

### What is on the site now
- **More options (top bar, every page)**: a key at the top right. It opens a panel with:
  - "Colour theme": Dark background / Light background;
  - "Share": Export page as PNG.
  - Only the page export moved. Each chart and table still has its own Download PNG where it was.
  - The page export closes the panel before it reads the page, so the PNG never shows the open panel. I checked this in the browser: the panel was hidden at the moment png.js read the page.
- **More filters (Filters panel on home)**: League and Model type stay in view. Phase, Reasoning, Runs on and Weights sit in a fold under a "More filters" key.
  - While closed, the key names the active non-default values and counts them, e.g. "More filters · Reasoning: High (1 active)" or "More filters · Phase: Race, Reasoning: High (2 active)".
  - With nothing active it reads "More filters · phase, reasoning, runs on, weights". When open it shows only the count.
  - The setups count and Reset stay visible next to it.
- **Auto-open**: the fold opens by itself when a folded filter is not at its default as the page is shown.
  - Only the league is in the address, so in practice this is the Phase the browser keeps on back / forward.
  - The browser fills that choice in after the scripts have run, so the page now loads that phase and opens the fold on `pageshow`.
  - Before this, the select showed the kept phase while the tables showed all phases.
  - Tested: Phase Race, fold closed, go to Method, then Back. The fold was open, the key read "More filters (1 active)" and Reset was active.
- **Extra fix**: the line "Nothing to reset: the filters show the defaults." used to stay visible next to an active Reset, because `.small` overrode `[hidden]`. This was already the case on the live site. One CSS line fixes it.
- **Old rules removed**: the earlier rules that gave Export page as PNG its own top-bar grid cell and its own row on phones are gone.

### Keyboard, ARIA, tap targets (measured in the browser on the local build)
- **Tab order** from the top: Skip to content → brand → More options → (when open) Dark background → Light background → Export page as PNG → the 7 nav links → the page.
  - The menu now comes right after the brand in the HTML, so the order matches what is on screen.
  - In the fold the order is: More filters → (when open) Phase → Reasoning keys → Runs on keys → Weights keys → Reset.
- **Escape**:
  - In the open menu, from the Light key: the menu closes, `aria-expanded` goes to `false` and the focus goes back to More options.
  - Escape inside the open fold also closes it and focuses More filters.
  - Tabbing out of the menu closes it (the focus moved on to "Every decision"), and so does a click outside.
- **ARIA**:
  - More options has `aria-expanded` and `aria-controls="more-options"`; the panel is `id="more-options" hidden` when closed. Same for More filters → `id="filters-more"`.
  - Both targets exist and their ids are unique: checks.py checks ids and anchors.
  - Each key's accessible name includes its summary.
  - The theme group is labelled by "Colour theme" (`aria-labelledby`).
- **Focus ring**: unchanged from Part 1 (2px `--focus`, offset 2px). `:focus-visible` was true on the focused key in every focus screenshot.
- **Phone tap targets (390 px)**: I measured 29 controls in light and dark: the menu key, Dark, Light and Export page as PNG in the open menu, plus every key and the select in the Filters panel with the fold open. The smallest height is 44 px and the smallest width is 55 px.
  - The rule `min-height/min-width: 2.75rem` applies on phones to `.more-menu .key`, `.filters .key` and `.filters select`.

### First-screen controls (counted in the browser; skip link included)
- **Desktop 1280×800: 38 → 23.**
  - Skip, brand, More options, 7 nav links, 3 content links, League ×4, Model type ×4, More filters and Reset.
  - Reset now fits above the fold because the Filters panel is shorter.
- **Phone 390×844: 11 → 10.**
  - Skip, brand, More options, 4 visible nav links (the rest scroll sideways) and 3 content links.
  - Without the Export row, "Open this decision" now reaches the first screen.

### Build, checks, deploy, live check
- **Local build:** `build.py` with checks.py, run in a throwaway folder: exit 0, no failures. I rebuilt once more after the last CSS/JS change; it passed again, and the built assets are identical to the commit.
- **Deploy:** I started `bg-site-preview.service` once (15:13:50–15:15:10 UTC) and it pushed analysis commit `d26deba63` (data as of 15:13Z, results 318f520b). That run built from a clean `tools/site`.
- **Live curl** of `https://zekiworks.github.io/analysis/backgammon/`, with a cache-busting query string:
  - `aria-expanded="false" aria-controls="more-options"` 1, `id="more-options" hidden` 1;
  - `data-more-filters` 1, `aria-controls="filters-more"` 1, `id="filters-more" hidden` 1, `data-more-summary` 1;
  - `data-page-png` 1 (inside the menu);
  - the Method page has the menu too;
  - the served `bg.js` has `showFold` and the served `site.js` has `moreOptions`.
- **Live in the browser:**
  - Enter on More options opens the menu;
  - Escape closes it and gives the focus back to the key;
  - with League 2 and Reasoning High, the closed key reads "More filters · Reasoning: High (1 active)".

### Screenshots (`mailbox/site-simplification/part2/`, local build, 28 WebP files, 1.3 MB)
Each set exists in `{light,dark}` × `{1280,390}`:
- `p2-home-closed-*`: the first screen with both folds closed;
- `p2-menu-open-*`: More options open;
- `p2-filters-closed-*`: the Filters panel with More filters closed;
- `p2-filters-open-*`: the fold open;
- `p2-filters-active-*`: the closed key with an active non-default filter (League 2, Reasoning: High, "2 of 19 setups"). In League 1, Reasoning High matches no setup, which is why League 2 is shown.
- `p2-focus-menu-*`: keyboard focus on the Light key inside the open menu;
- `p2-focus-fold-*`: keyboard focus on the Reasoning "All" key inside the open fold.

The "before" screenshots for this part are Part 1's `after-home-*` and `after-board-*` (the site with the flat style, before the folds).
