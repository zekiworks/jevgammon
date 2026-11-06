# Late entries on the site - report 2026-11-06

Ümit's request (bus #1159/#1270), items 5 and 6. Published: the seven late entries to the original League 1 table on the Late entries tab, a page each, setups.json entries and a Method changelog line. Late entries stay out of every standings table, Cup input and other setup's numbers (existing filter and build check).

## What changed

- **Site commit:** d72bd46 (tools/site only), pushed to main; deployed by the scheduled timer (bg-site-preview). Mirror commit and results id: see "Live" below.
- **Late-entry table and pages:** three new columns, the engine's best play, median s per decision and $ per 1,000 decisions. Each cost shows its price label, source and the date it was read.
- **Not played:** each Drex setup's pair with GPT-6 Luna shows "Not played (opponent's API out of credit)", with no score. It is not a loss, and the status badge reads "Provisional: 1 pair not played". Source: content/late_entries.json, from mailbox/Late entries Drex - status 2026-11-06.md (matches #829, #835, #846 and #886 were blocked by OpenAI 429, no credit, and deferred).
- **setups.json:** one entry each for the seven (dataset late-entry) and for GPT-6 Astra (high). Each entry has the route and provider, the revision (pinned model id or Hugging Face commit), the option cap (25 for Drex, 120 for Base Labs, 255 for SubQ) and the probability notes:
  - SubQ: 32-bit floats.
  - Base Labs: rounded to 6 decimals by the loader.
  - Drex 2.0 (hosted and local): rounded to 4 decimals.
  - Drex Max 1.1 and Drex Max v1: stored as returned. Our records show no rounding for these two (aggregate check only).
- **Prices (source, date read):**

  | setup | price | label | source | read |
  |---|---|---|---|---|
  | SubQ Snap 1.1 | $0.04/M input, output free | billed | docs.subq.ai/using-the-api/models | 2026-11-01 |
  | Base Labs Elephant-1 | $0.035/M | Baseten list price for the hosted model, not billed | Baseten Model API | 2026-11-01 |
  | Base Labs Mammoth-1 | $0.10/M | Baseten list price for the hosted model, not billed | Baseten Model API | 2026-11-01 |
  | Drex Max 1.1 | list $0.06/M, shown next to the billed launch price $0.03/M | list and billed, labelled separately | nace.ai/drex and console.nace.ai/docs/drex/reference/pricing | 2026-11-05 |
  | Drex 2.0 | $0.06/M | list = billed | console.nace.ai/docs/drex/reference/pricing | 2026-11-05 |
  | Drex Max v1 | $0.06/M | list price for the hosted model, not billed | nace.ai/drex | 2026-11-05 |
  | Drex 2.0 (local) | $0.06/M | list price for the hosted model, not billed | console.nace.ai/docs/drex/reference/pricing | 2026-11-05 |
- **Method changelog:** an entry dated 6 Nov 2026.
- **Probabilities:** no per-turn answer is shown anywhere. Only aggregates are published.

## Checks (render-only candidate, no build.py or update.sh, no server, no timer action)

- **Candidate:** built from a copy of the snapshot (STATE/snap.db) and STATE/plays, read-only.
- **Old tree reproduces the live site:** HEAD's old tree rebuilt the live Leagues body, the home block, all 8 late-entry pages and the late-entry JSON byte for byte.
- **New tree changes only the expected pages:** Leagues, home, Method and the 8 late-entry pages, besides the results id. Among the data files only the late-entry files, setups.json and the manifest change.
- **No existing number changed:** every existing value in the late-entry JSON is identical. The added keys are `price`, `not_played` and (Drex Max 1.1) `usd_per_1000_billed`.
- **checks.py page checks** on the 30 changed pages and Method passed: numbers trace, no mixing, links and anchors resolve, no banned string.

## Table

The numbers come from the published site: data/v3/late-entries.json, and league-1.json / league-2.json for the decision models of the original League 1 field.

- Risk judgement is at margin 0.001. Error rate is PR.
- Both have 95% intervals.
- Time is the median request seconds per decision.

Turkish accuracy: the Decision Models page, zekiworks.github.io/analysis/decision-models/, Accuracy table (2,198 native-Turkish questions, results 7899a84b, updated 6 November 2026, read 2026-11-06). The name used there is in brackets where it differs.

| setup | where | risk judgement (95% interval) | error rate PR (95% interval) | median s per decision | $ per 1,000 decisions | Turkish accuracy % |
|---|---|---|---|---|---|---|
| SubQ Snap 1.1 | late entry, 19/19 | 56.7 (54.8–58.6) | 40.2 (36.7–43.8) | 0.23 | $0.150 (billed API price) | 63.9 |
| Base Labs Elephant-1 | late entry, 19/19 | 57.7 (55.8–59.6) | 44.6 (40.3–48.9) | 0.26 | $0.133 (Baseten list, not billed) | 52.4 (Elephant-1) |
| Base Labs Mammoth-1 | late entry, 19/19 | 63.2 (61.2–65.2) | 28.5 (26.2–31.1) | 0.72 | $0.387 (Baseten list, not billed) | 67.1 (Mammoth-1) |
| Drex Max 1.1 | late entry, 18/19 (Luna not played) | 59.1 (57.0–61.3) | 30.9 (28.2–33.7) | 0.44 | $0.265 at list; $0.132 billed (launch price) | 67.4 |
| Drex 2.0 | late entry, 18/19 (Luna not played) | 58.1 (55.7–60.4) | 38.4 (35.6–41.4) | 0.42 | $0.258 (list = billed) | 55.7 (hosted, Nace API) |
| Drex Max v1 | late entry, 18/19 (Luna not played) | 62.9 (61.1–64.7) | 30.4 (27.4–33.4) | 0.68 | $0.271 (hosted list, not billed) | 67.7 |
| Drex 2.0 (local) | late entry, 18/19 (Luna not played) | 53.0 (50.5–55.2) | 42.9 (39.1–47.1) | 0.40 | $0.250 (hosted list, not billed) | not on the page (hosted Drex 2.0: 55.7) |
| Celeris-1 Decision | League 1 | 57.8 (55.9–59.7) | 35.6 (32.0–39.4) | 0.17 | $0.150 (API price) | 60.5 |
| Clef | League 2* | 57.5 (55.4–59.8) | 36.5 (33.5–39.6) | 1.13 | not measured | 57.3 |
| Decider Flash v1.2 | League 1 | 49.1 (46.5–51.6) | 59.6 (54.9–64.5) | 0.56 | $0.045 (list-price estimate, our GPUs) | 47.8 (Perplexity Decider Flash v1.2) |
| Decider v1.1 27B | League 1 | 56.9 (54.9–58.8) | 38.8 (35.3–42.5) | 1.97 | $0.090 (list-price estimate, our GPUs) | 66.9 (Perplexity Decider 27B v1.1) |
| Decider v1.2 27B | League 1 | 57.9 (56.0–59.9) | 36.9 (33.9–40.1) | 0.94 | $0.087 (list-price estimate, our GPUs) | 67.1 (Perplexity Decider 27B v1.2, local GPU) |
| Fastino GLiDE | League 2* | 60.4 (58.3–62.6) | 33.2 (30.2–36.4) | 0.48 | not measured | 67.9 |
| Fastino GLiDE v1.2 (local) | League 1 | 58.8 (56.7–60.8) | 35.0 (31.6–39.0) | 1.41 | not measured | 68.5 (Fastino GLiDE v1.2) |
| GPT-6 Luna | League 1 | 55.7 (53.8–57.6) | 43.3 (39.7–46.9) | 0.23 | $0.335 (API price) | 63.6 (GPT-6 Luna, Decisions API) |
| Jev 1.13.0 | League 1 | 59.5 (57.4–61.6) | 34.4 (31.0–38.0) | 0.22 | $0.166 (API price) | 57.5 |
| Jev 1.14.0 | League 2* | 59.3 (57.1–61.4) | 31.7 (28.3–35.7) | 0.19 | $0.173 (API price) | 59.2 |
| Liquid d1-ultra | League 2* | 64.0 (61.7–66.3) | 30.3 (27.3–33.4) | 0.23 | $0.145 (API price) | 77.1 |
| Mercury Decide | League 1 | 53.4 (51.5–55.2) | 47.9 (43.3–52.9) | 0.48 | $0.071 (API price) | 58.3 (Inception Mercury Decide) |
| Open-Jev 27B v1.1 | League 1 | 48.5 (46.1–50.9) | 65.6 (59.7–71.9) | 1.57 | not measured | 55.7 |
| SubQ Snap Preview | League 1 | 56.5 (53.8–59.1) | 43.9 (39.3–48.8) | 0.24 | $0.193 (API price) | 65.2 |
| Winnow-12B | League 1 | 55.2 (52.9–57.2) | 49.7 (45.9–53.6) | 2.46 | not measured | 55.5 |

\* Moved to League 2 by the ladder. The published numbers are their League 2 ones.

Cygnet (Gemma 4 12B) is a chat model, so it is left out. The programs (GNUbg weak, Safest, Random) are left out too.

The late entries' games are different positions from the league games, so close values are not a ranking. The late entries are never ranked on the site.

## Live
- **Deploy:** timer run 08:50 UTC built site code d72bd46 (tools/site tree 0373b0d) with checks passing, no failure file.
- **Mirror:** commit b44880845 (zekiworks/analysis), "data as of 2026-11-06T08:50Z", **results 2f496968**.
- **Same data as the candidate:** the deployed data/ equals the candidate's except the manifest and data/index.html (as-of time).
- **Readback with curl, all 200 and Results 2f496968:**
  - https://zekiworks.github.io/analysis/backgammon/leagues/#late-entries: 4× "Not played (opponent's API out of credit)"; new headers "Engine's best play", "Median s per decision", "$ per 1,000 decisions".
  - https://zekiworks.github.io/analysis/backgammon/ (the home Leagues block, #lg-late-entries)
  - https://zekiworks.github.io/analysis/backgammon/method/ (changelog of 6 Nov)
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/subq-snap-1-1/
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/base-labs-elephant-1/
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/base-labs-mammoth-1/
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/drex-max-1-1/: "billed at Nace's launch price, $0.03 per million input tokens: 0.132"
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/drex-2-0/
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/drex-max-v1/
  - https://zekiworks.github.io/analysis/backgammon/models/late-entry/drex-2-0-local/
  - https://zekiworks.github.io/analysis/backgammon/data/v3/late-entries.json
- **Readback in a browser at 1400 px and 390 px:**
  - Leagues → Late entries: the Drex Max 1.1 row reads "Provisional: 1 pair not played", 18 / 19 with "not played: GPT-6 Luna (opponent's API out of credit)", 12–2–4, best play 46.8%, 0.44 s, $0.265 with the list label and the billed $0.132.
  - Pages: no horizontal page overflow at either width (the tables swipe), no page errors.
  - Drex Max 1.1 page: the facts list and "How we called it" show the price source and date and the 25-option cap.
