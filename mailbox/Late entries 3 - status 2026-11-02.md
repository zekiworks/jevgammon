# Late entries 3 - status 2026-11-02

**Plan B is running on Can's go (2 Nov).** The plan is in `mailbox/Late entries 3 - plan 2026-11-02.md`.

Three entrants each play all 19 setups of the original League 1 table: 57 matches.

| entrant | late-entry league |
|---|---|
| Base Labs Elephant-1 | its own hidden league |
| Base Labs Mammoth-1 | its own hidden league |
| SubQ Snap 1.1 | its own hidden league |

Every league plays only its entrant's pairs, under League 1's rules, with `stage = 'late-entry'`.

- **Runner.** `target/late3/release/jevgammon`, built from branch `late3-baselabs` at 104103a, clean, in the worktree `/home/cbasaran/code/jevgammon-late3`.
- **Order (so nothing idles):**
  1. **Now:** the 8 API setups, the 3 programs, Fastino GLiDE v1.2 (local) on GPU 3, and Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B on GPU 1. Compactor freed GPU 1 for about 3 h.
  2. **Once GPU 2 is actually free:** Clef and Cygnet. Can releases GPU 2 in about 2 h; ComfyUI and ai-toolkit are never touched.
  3. **After Clef and Cygnet:** Open-Jev.
  4. **Decider v1.1 27B:** on GPU 3 once GLiDE v1.2 is done, if there is room; otherwise on GPU 2 after Open-Jev.
- **Automation.** The unit `late3-orch` (`workspace/late3/orchestrate.sh`) checks every 5 min, adds these opponents by `league-add`, stops each server once it has played all three entrants, and stops everything if billed spend passes **$2**.

## Smoke tests (before any match)

20 stored League 1 requests each, the 3 largest at 118 options included.

| entrant | answers passed | probability sums | 118 options | 5–32 options | GPU memory |
|---|---|---|---|---|---|
| Elephant-1 | **20/20** | within 6-decimal rounding | 13,858–14,346 input tokens (inside 16,384); 1.1 s | 0.18–0.32 s | GPU 3 ≈ 22.3 GB |
| Mammoth-1 | **20/20** | within 6-decimal rounding | 3.4–3.6 s | 0.58–1.06 s | GPU 0 ≈ 57–59 GB |

## Free checks at go (GETs only)

- SubQ `/v1/models` lists `subq-snap-1.1`, `subq-snap-latest` and `subq-snap-preview`, so **SubQ Snap Preview stays in**.
- OpenRouter has **$0.99** free, so **Mercury Decide stays in**.

## Log
- 2026-11-02T18:29:26Z leagues started (units late3-base-labs-elephant-1, late3-base-labs-mammoth-1, late3-subq-snap-1-1)
- 2026-11-02T18:30:15Z orchestrator up (first match #772)
- 2026-11-02T18:55:19Z GLiDE v1.2 (local) played all three: stopped (GPU 3)
- 2026-11-02T18:55:22Z GPU 1 FREE: Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B played all three and are stopped; GPU 1 can go back to compactor
- 2026-11-02T18:55:42Z started: DECIDER_GPU=3 tools/v3/servers/decider.sh start (GPU memory 0, 59472 MiB 1, 20 MiB 2, 79509 MiB 3, 79500 MiB )
- 2026-11-02T18:55:42Z Decider v1.1 27B added to league #13 (Base Labs Elephant-1)
- 2026-11-02T18:55:42Z Decider v1.1 27B added to league #14 (Base Labs Mammoth-1)
- 2026-11-02T18:55:42Z Decider v1.1 27B added to league #12 (SubQ Snap 1.1)
- 2026-11-02T18:55:42Z late3-base-labs-elephant-1 (re)started for Base Labs Elephant-1's open pairs
- 2026-11-02T18:55:42Z late3-base-labs-mammoth-1 (re)started for Base Labs Mammoth-1's open pairs
- 2026-11-02T18:55:42Z late3-subq-snap-1-1 (re)started for SubQ Snap 1.1's open pairs
- 2026-11-02T19:05:44Z Decider v1.1 27B played all three: stopped (GPU 3)
- 2026-11-02T19:43:39Z started: CLEF_GPU=2 tools/v3/servers/clef.sh start && CYGNET_GPU=2 CYGNET_UTIL=0.34 tools/v3/servers/cygnet.sh start (GPU memory 0, 59472 MiB 1, 85887 MiB 2, 85705 MiB 3, 29137 MiB )
- 2026-11-02T19:43:39Z Clef added to league #13 (Base Labs Elephant-1)
- 2026-11-02T19:43:39Z Clef added to league #14 (Base Labs Mammoth-1)
- 2026-11-02T19:43:39Z Clef added to league #12 (SubQ Snap 1.1)
- 2026-11-02T19:43:39Z Cygnet (Gemma 4 12B) added to league #13 (Base Labs Elephant-1)
- 2026-11-02T19:43:40Z Cygnet (Gemma 4 12B) added to league #14 (Base Labs Mammoth-1)
- 2026-11-02T19:43:40Z Cygnet (Gemma 4 12B) added to league #12 (SubQ Snap 1.1)
- 2026-11-02T19:43:40Z late3-base-labs-elephant-1 (re)started for Base Labs Elephant-1's open pairs
- 2026-11-02T19:43:40Z late3-base-labs-mammoth-1 (re)started for Base Labs Mammoth-1's open pairs
- 2026-11-02T19:43:40Z late3-subq-snap-1-1 (re)started for SubQ Snap 1.1's open pairs
- 2026-11-02T19:53:42Z Clef and Cygnet played all three: stopped (GPU 2)
- 2026-11-02T19:54:03Z started: OPEN_JEV_GPU=2 tools/v3/servers/open-jev.sh start (GPU memory 0, 59472 MiB 1, 88019 MiB 2, 53052 MiB 3, 29137 MiB )
- 2026-11-02T19:54:03Z Open-Jev 27B v1.1 added to league #13 (Base Labs Elephant-1)
- 2026-11-02T19:54:03Z Open-Jev 27B v1.1 added to league #14 (Base Labs Mammoth-1)
- 2026-11-02T19:54:03Z Open-Jev 27B v1.1 added to league #12 (SubQ Snap 1.1)
- 2026-11-02T19:54:03Z late3-base-labs-elephant-1 (re)started for Base Labs Elephant-1's open pairs
- 2026-11-02T19:54:03Z late3-base-labs-mammoth-1 (re)started for Base Labs Mammoth-1's open pairs
- 2026-11-02T19:54:03Z late3-subq-snap-1-1 (re)started for SubQ Snap 1.1's open pairs
- 2026-11-02T20:04:10Z Base Labs Mammoth-1 played all 19: its server stopped
- 2026-11-02T20:09:12Z Open-Jev played all three: stopped (GPU 2)
- 2026-11-02T20:09:16Z Base Labs Elephant-1 played all 19: its server stopped
- 2026-11-02T20:09:16Z ALL DONE: billed $0.8020
- 2026-11-02T20:09:16Z Release (jevgammon late entries 3, plan B done 2026-11-02T20:09:16Z): bariton GPU 0 (Mammoth-1) and GPU 2 (Clef, Cygnet, Open-Jev) are free again; on GPU 3 Elephant-1, GLiDE v1.2 and Decider v1.1 are stopped (Hilde's lfm3-audio untouched). GPU 1 went back to compactor earlier (2026-11-02T18:55:22Z).

## Results (done 2026-11-02 20:09 UTC)

All **57 of 57** matches finished and are valid, with `stage = 'late-entry'`.

- **Match ids:** #772 to #828.
- **Leagues:** #12 SubQ Snap 1.1, #13 Base Labs Elephant-1, #14 Base Labs Mammoth-1. All three are finished and hidden.
- **Wall time:** 18:29 to 20:05 UTC. About 70 min of that was waiting for GPU 2.

| entrant | W-D-L | points | game points for–against | decisions | invalid | lists split | s per decision | cost |
|---|---|---|---|---|---|---|---|---|
| Base Labs Mammoth-1 | **16-1-2** | 49 | 90–43 | 2,021 | 0 | 12 | 0.87 | $0.78 API-equivalent (Baseten list), $0 billed |
| SubQ Snap 1.1 | 12-0-7 | 36 | 79–61 | 2,326 | 0 | 2 | 0.23 | **$0.35 billed** |
| Base Labs Elephant-1 | 11-0-8 | 33 | 80–59 | 2,044 | 0 | 7 | 0.36 | $0.27 API-equivalent (Baseten list), $0 billed |

- **Billed spend, all late-entry matches: $0.80.** That is SubQ Snap 1.1 $0.35 plus the API opponents $0.45:

  | opponent | billed |
  |---|---|
  | GPT-6 Luna | $0.085 |
  | SubQ Snap Preview | $0.075 |
  | Jev 1.14.0 | $0.060 |
  | Celeris-1 Decision | $0.058 |
  | Liquid d1-ultra | $0.056 |
  | Fastino GLiDE | ≈ $0.05 (estimated at $0.04/M; its settings carry no price) |
  | Jev 1.13.0 | $0.045 |
  | Mercury Decide | $0.024 (OpenRouter) |

  The $2 cap was never near.
- **Failures:** none left.
  - Matches #817 (Decider v1.1 v SubQ Snap 1.1) and #818 (Mammoth-1 v Decider v1.1) each hit 4× HTTP 529 ("model busy") from the Decider v1.1 server, which answers one request at a time. Both were deferred, resumed from their last stored turn, and finished. The error text stays on the match row.
  - No invalid answers from any setup.
  - No request was refused for length: the biggest Base Labs request was 118 options; lists over 120 options were split.

## Release (for Main to post)

> Release (jevgammon late entries 3, plan B done 2026-11-02 20:09 UTC): bariton GPU 0 (Mammoth-1) and GPU 2 (Clef, Cygnet, Open-Jev) are free again; on GPU 3 Elephant-1, GLiDE v1.2 and Decider v1.1 are stopped (Hilde's lfm3-audio untouched). GPU 1 went back to compactor earlier (18:55 UTC).

Every `late3`/`v3-*` server and unit is stopped, and `late3-orch` has exited. What is on the GPUs now is not ours:

| GPU | in use | by |
|---|---|---|
| 0 | 41 MiB | — |
| 1 | 61.5 GB | compactor's vLLM |
| 2 | 20 MiB | — |
| 3 | 17.8 GB | lfm3-audio and Can's ComfyUI |
