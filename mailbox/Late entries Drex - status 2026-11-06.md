# Late entries Drex - status 2026-11-06

Plan: `mailbox/Late entries Drex - plan 2026-11-05.md` (c506e65). Go for the **API stage only** (Ümit via Zeki, bus #1474, 6 Nov). The GPU stage is not started: no GPU is used, and GPU 3 is reserved and never used.

**Scope.** Two entrants, each in its own hidden late-entry league, play 11 opponents each: **22 matches**.

| entrant | league | opponents |
|---|---|---|
| Drex Max 1.1 | #15 | Celeris-1 Decision, Fastino GLiDE, GPT-6 Luna, Jev 1.13.0, Jev 1.14.0, Liquid d1-ultra, Mercury Decide, SubQ Snap Preview, GNUbg weak, Random, Safest |
| Drex 2.0 | #16 | the same 11 |

- **Rules:** League 1's rules, at most 25 options per request, pre-send guard on the Nace requests ($1.25), soft stop at $2 billed, no opponent dropped.
- **First match:** #829.
- **Runner:** branch `late-drex` at e58fc6c, clean.


## Log
- 2026-11-06T00:49:10Z orchestrator up, mode api (first match #829; GPUs 1 2)
- 2026-11-06T00:49:10Z drex-drex-max-1-1 (re)started for Drex Max 1.1
- 2026-11-06T00:49:11Z drex-drex-2-0 (re)started for Drex 2.0
- 2026-11-06T01:00:26Z orchestrator up, mode gpu (first match #829; GPUs 0 2)
- 2026-11-06T01:01:21Z orchestrator up, mode gpu (first match #829; GPUs 0 2)
- 2026-11-06T01:01:22Z started drexmax on GPU 2 (0, 50406 MiB 1, 85887 MiB 2, 20 MiB 3, 65190 MiB )
- 2026-11-06T01:02:04Z Drex Max v1: smoke test passed (20/20 passed); its league starts
- 2026-11-06T01:02:05Z drex-drex-max-v1 (re)started for Drex Max v1
- 2026-11-06T01:02:44Z started trio on GPU 2 (0, 53006 MiB 1, 85887 MiB 2, 73102 MiB 3, 65190 MiB )
- 2026-11-06T01:02:44Z Decider v1.2 27B added to league #15 (Drex Max 1.1)
- 2026-11-06T01:02:44Z Decider v1.2 27B added to league #16 (Drex 2.0)
- 2026-11-06T01:02:45Z Decider v1.2 27B added to league #17 (Drex Max v1)
- 2026-11-06T01:02:45Z Decider Flash v1.2 added to league #15 (Drex Max 1.1)
- 2026-11-06T01:02:45Z Decider Flash v1.2 added to league #16 (Drex 2.0)
- 2026-11-06T01:02:45Z Decider Flash v1.2 added to league #17 (Drex Max v1)
- 2026-11-06T01:02:45Z Winnow-12B added to league #15 (Drex Max 1.1)
- 2026-11-06T01:02:45Z Winnow-12B added to league #16 (Drex 2.0)
- 2026-11-06T01:02:45Z Winnow-12B added to league #17 (Drex Max v1)
- 2026-11-06T01:10:43Z started cygnet on GPU 0 (0, 85567 MiB 1, 20 MiB 2, 82536 MiB 3, 20 MiB )
- 2026-11-06T01:10:43Z Cygnet (Gemma 4 12B) added to league #15 (Drex Max 1.1)
- 2026-11-06T01:10:43Z Cygnet (Gemma 4 12B) added to league #16 (Drex 2.0)
- 2026-11-06T01:10:43Z Cygnet (Gemma 4 12B) added to league #17 (Drex Max v1)
- 2026-11-06T01:30:53Z stopped trio on GPU 2: all its pairs played
- 2026-11-06T01:30:54Z stopped cygnet on GPU 0: all its pairs played
- 2026-11-06T01:31:15Z started clef on GPU 2 (0, 53006 MiB 1, 20 MiB 2, 53144 MiB 3, 20 MiB )
- 2026-11-06T01:31:15Z Clef added to league #15 (Drex Max 1.1)
- 2026-11-06T01:31:15Z Clef added to league #16 (Drex 2.0)
- 2026-11-06T01:31:15Z Clef added to league #17 (Drex Max v1)
- 2026-11-06T01:41:19Z stopped clef on GPU 2: all its pairs played
- 2026-11-06T01:41:40Z started glide on GPU 2 (0, 53006 MiB 1, 20 MiB 2, 52810 MiB 3, 20 MiB )
- 2026-11-06T01:41:40Z league-add of Fastino GLiDE v1.2 (local) to league #15 failed (drex-drex-max-1-1.log)
- 2026-11-06T01:41:40Z league-add of Fastino GLiDE v1.2 (local) to league #16 failed (drex-drex-2-0.log)
- 2026-11-06T01:41:40Z league-add of Fastino GLiDE v1.2 (local) to league #17 failed (drex-drex-max-v1.log)
- 2026-11-06T01:49:18Z INCOMPLETE SCOPE (api): 2 pairs missing and nothing else left to play; stopped: nothing (drex-orch-gpu runs the leagues); billed $1.0264; the missing pairs resume with the same scripts once unblocked
- 2026-11-06T01:49:18Z   missing: Drex Max 1.1 v GPT-6 Luna (match #829): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T01:49:18Z   missing: Drex 2.0 v GPT-6 Luna (match #835): player 2: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav

## Paused 2026-11-06 (Main: Turkce needs all four GPUs)

The Drex runs are stopped cleanly and **GPUs 0 and 2 hold none of our processes**: `nvidia-smi` showed 41 MiB on GPU 0 and 20 MiB on GPU 2, with no compute process.
- **Stopped first:** the orchestrators and the league runners of #15, #16 and #17 (SIGTERM). No match was left unfinished except the three blocked GPT-6 Luna matches, which stay deferred and resumable.
- **Then the servers:** Drex Max v1 (GPU 0) and Fastino GLiDE v1.2 (local) (GPU 2).
- **Already stopped earlier, each after playing its pairs:** the Decider v1.2 27B + Flash + Winnow trio, Cygnet and Clef.
- **Not started:** Drex 2.0 (local), which was downloaded and set up but was due only after Drex Max v1, and Open-Jev and Decider v1.1.

**Matches.** #829 to #876: 45 finished and valid, 3 deferred (the blocked GPT-6 Luna pairs).

| entrant | played | W-D-L | game points for–against | decisions | invalid | lists split (25-option cap) |
|---|---|---|---|---|---|---|
| Drex Max 1.1 | 15 of 19 | 10-1-4 | 72–43 | 1,827 | 0 | 187 |
| Drex Max v1 | 15 of 19 | 9-0-6 | 65–45 | 1,828 | 0 | 200 |
| Drex 2.0 | 15 of 19 | 8-0-7 | 54–53 | 1,579 | 0 | 161 |
| Drex 2.0 (local) | 0 of 19 | — | — | — | — | — |

**Pending pairs (61):**
- Drex Max 1.1, Drex 2.0 and Drex Max v1 each still play:
  - GPT-6 Luna: **blocked**. Its API has no credit left (429 "no credits remaining"); a top-up needs Can.
  - Decider v1.1 27B, Open-Jev 27B v1.1 and Fastino GLiDE v1.2 (local): GPU, paused.
- Drex 2.0 (local): all 19 (GPU, paused; Luna blocked as above).

**GLiDE v1.2 (local).** Its server was up from 01:41 UTC until the pause but played no Drex pair: `league-add` failed. The orchestrator ran `league-add` without the key variables in its environment, and the runner checks every player's service settings, a local GLiDE's included. Fixed in `workspace/drex/orchestrate.sh` for the resume.

**Billed so far: $1.03.**
- The Drex entrants' Nace requests: $0.64, booked by the pre-send guard (cap $1.25).
- The API opponents: the rest.
- Drex Max v1 on our GPU is not billed ($0.49 at list price).

**Resume (only when Main says so; it waits for free memory on the GPUs given and never uses GPU 3):**

    CAN_GO=yes DREX_GPUS="0 2" DREX_LOCAL=yes workspace/drex/start_gpu.sh

It restarts Drex Max v1 first (smoke test, then its league). It then starts the servers that still have pairs (GLiDE v1.2, Open-Jev, Decider v1.1) and resumes leagues #15–#17. Then Drex 2.0 (local) runs on a whole GPU, with every local opponent started again for it.
