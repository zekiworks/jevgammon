# Backgammon site: design note (brief v6, B3)

Oct 22, 2026 · written before the v6 build. Preview: https://zekiworks.github.io/analysis/backgammon-preview/

## Reused from decision-models (our own site, analysis/decision-models/)
- **House style:** the slate palette, the dark/light modes (system default, one switch kept for the whole site), the system font stack, cards, pill controls. Can asked today that the look follow the Turkish dashboard: dark/light, clickable and sortable tables, text not the primary element. That is already on the preview and stays.
- **Components:** the header nav, a question-led hero, the stats strip, the findings list, filters, the Table/Charts toggle with metric tabs, the "Results <hash>, updated <date>" line, detail pages (one per setup), JSON downloads, and the social preview generated from the current results.
- **Page structure:** Home, Every question → Every decision, Where models disagree, Topics → Phases, Compare, Model page.
- **Build setup:** a Python build writes static pages and JSON into the site repo, and the pre-deploy checks run first.
- None of that benchmark's text, names or links goes on the site.
- Reuse depends on the licence check (decision-bench origin). No new decision-models code is copied until it reports. If it finds anything from decision-bench in a reused part, that part gets rewritten or gets the notice it requires.

## New for backgammon (sibling, not clone)
- **The board as the visual signature:**
  - **Hero:** a real position from the data, drawn as SVG next to the title. It is a Risk pays decision, with the engine's best play marked.
  - **Social preview image:** the same board beside the current headline numbers.
  - **Every decision:** a board on each card (already there).
- **The risk 2×2 as the second signature:**
  - Each cell is a square tile with one big share, its count and denominator in small type, and the mean equity lost.
  - Colour shows good calls (risk taken when it pays, safe play when safety pays) against bad calls.
  - It reads at a glance and is also exported as a standalone image for X.
  - The hit-risk limit sits next to it.
- **Accent colour:** felt green (teal, #0f766e light / #2dd4bf dark) replaces decision-models' blue for links, active tabs and sort marks. Data colours are unchanged.
- **Framing (B0):** each home section and tab belongs to one of the five threads (decision quality, what the input adds, confidence, cost, learning). Standings, runner history, the anchor note and hardware moves go to Leagues or Method.
