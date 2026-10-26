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
