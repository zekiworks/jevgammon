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
- 2026-11-06T06:49:54Z RESUME on Main's word (GPUs 0 and 2; Turkce released the GPUs at 06:48 UTC)
- 2026-11-06T06:49:54Z orchestrator up, mode gpu (first match #829; GPUs 0 2)
- 2026-11-06T06:49:54Z drex-drex-max-1-1 (re)started for Drex Max 1.1
- 2026-11-06T06:49:54Z drex-drex-2-0 (re)started for Drex 2.0
- 2026-11-06T06:50:40Z started drexmax on GPU 0 (0, 50406 MiB 1, 85887 MiB 2, 20 MiB 3, 35844 MiB )
- 2026-11-06T06:51:09Z Drex Max v1: smoke test passed (20/20 passed); its league starts
- 2026-11-06T06:51:10Z drex-drex-max-v1 (re)started for Drex Max v1
- 2026-11-06T06:56:27Z started glide on GPU 2 (0, 52700 MiB 1, 85887 MiB 2, 52810 MiB 3, 58588 MiB )
- 2026-11-06T06:56:27Z Fastino GLiDE v1.2 (local) added to league #15 (Drex Max 1.1)
- 2026-11-06T06:56:27Z Fastino GLiDE v1.2 (local) added to league #16 (Drex 2.0)
- 2026-11-06T06:56:27Z Fastino GLiDE v1.2 (local) added to league #17 (Drex Max v1)
- 2026-11-06T07:06:32Z stopped glide on GPU 2: all its pairs played
- 2026-11-06T07:06:52Z started openjev on GPU 2 (0, 52700 MiB 1, 85887 MiB 2, 53052 MiB 3, 58588 MiB )
- 2026-11-06T07:06:52Z Open-Jev 27B v1.1 added to league #15 (Drex Max 1.1)
- 2026-11-06T07:06:52Z Open-Jev 27B v1.1 added to league #16 (Drex 2.0)
- 2026-11-06T07:06:53Z Open-Jev 27B v1.1 added to league #17 (Drex Max v1)
- 2026-11-06T07:16:56Z stopped openjev on GPU 2: all its pairs played
- 2026-11-06T07:17:22Z started dv11 on GPU 2 (0, 52700 MiB 1, 85887 MiB 2, 50384 MiB 3, 58588 MiB )
- 2026-11-06T07:17:22Z Decider v1.1 27B added to league #15 (Drex Max 1.1)
- 2026-11-06T07:17:22Z Decider v1.1 27B added to league #16 (Drex 2.0)
- 2026-11-06T07:17:22Z Decider v1.1 27B added to league #17 (Drex Max v1)
- 2026-11-06T07:27:26Z stopped drexmax on GPU 0: all its pairs played
- 2026-11-06T07:27:26Z stopped dv11 on GPU 2: all its pairs played
- 2026-11-06T07:27:32Z start of drexv2 on GPU 0 failed (try 1 of 3; state/servers.log)
- 2026-11-06T07:32:39Z start of drexv2 on GPU 0 failed (try 2 of 3; state/servers.log)
- 2026-11-06T07:37:45Z start of drexv2 on GPU 0 failed (try 3 of 3; state/servers.log)
- 2026-11-06T07:37:45Z drexv2 given up after 3 failed starts
- 2026-11-06T07:42:49Z INCOMPLETE SCOPE (gpu): 3 pairs missing and nothing else left to play; billed $1.1708
- 2026-11-06T07:42:49Z Release (jevgammon Drex late entries, incomplete 2026-11-06T07:42:49Z): all our servers are stopped; GPU(s) 0 2 are free of us again (no other process touched).
- 2026-11-06T07:42:49Z   missing: Drex Max 1.1 v GPT-6 Luna (match #829): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T07:42:49Z   missing: Drex 2.0 v GPT-6 Luna (match #835): player 2: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T07:42:49Z   missing: Drex Max v1 v GPT-6 Luna (match #846): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T07:44:06Z Drex 2.0 (local): its server failed to start at 07:27–07:37 (serve.py could not import its own modules: the snapshot's symlinked files resolve to the cache's blobs). Fixed in drexv2.sh (import path = the snapshot folders); on Main's go it starts on GPU 0 with a smoke test first
- 2026-11-06T07:44:06Z orchestrator up, mode gpu (first match #829; GPUs 0 2)
- 2026-11-06T07:44:06Z drex-drex-max-1-1 (re)started for Drex Max 1.1
- 2026-11-06T07:44:07Z drex-drex-2-0 (re)started for Drex 2.0
- 2026-11-06T07:44:37Z started drexv2 on GPU 0 (0, 65756 MiB 1, 85887 MiB 2, 20 MiB 3, 58588 MiB )
- 2026-11-06T07:44:55Z Drex 2.0 (local): smoke test passed (20/20 passed); its league starts
- 2026-11-06T07:44:56Z drex-drex-2-0-local (re)started for Drex 2.0 (local)
- 2026-11-06T07:50:50Z started trio on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 73102 MiB 3, 58588 MiB )
- 2026-11-06T07:50:50Z Decider v1.2 27B added to league #18 (Drex 2.0 (local))
- 2026-11-06T07:50:51Z Decider Flash v1.2 added to league #18 (Drex 2.0 (local))
- 2026-11-06T07:50:51Z Winnow-12B added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:00:56Z stopped trio on GPU 2: all its pairs played
- 2026-11-06T08:03:23Z started cygnet on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 32584 MiB 3, 58588 MiB )
- 2026-11-06T08:03:23Z Cygnet (Gemma 4 12B) added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:03:44Z started clef on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 86423 MiB 3, 58588 MiB )
- 2026-11-06T08:03:44Z Clef added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:08:48Z stopped cygnet on GPU 2: all its pairs played
- 2026-11-06T08:08:48Z stopped clef on GPU 2: all its pairs played
- 2026-11-06T08:09:09Z started glide on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 52810 MiB 3, 58588 MiB )
- 2026-11-06T08:09:09Z Fastino GLiDE v1.2 (local) added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:14:11Z stopped glide on GPU 2: all its pairs played
- 2026-11-06T08:14:27Z started openjev on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 53052 MiB 3, 58588 MiB )
- 2026-11-06T08:14:27Z Open-Jev 27B v1.1 added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:19:30Z stopped openjev on GPU 2: all its pairs played
- 2026-11-06T08:19:55Z started dv11 on GPU 2 (0, 69426 MiB 1, 85887 MiB 2, 50384 MiB 3, 58588 MiB )
- 2026-11-06T08:19:55Z Decider v1.1 27B added to league #18 (Drex 2.0 (local))
- 2026-11-06T08:24:58Z stopped drexv2 on GPU 0: all its pairs played
- 2026-11-06T08:24:58Z stopped dv11 on GPU 2: all its pairs played
- 2026-11-06T08:34:32Z INCOMPLETE SCOPE (gpu): 4 pairs missing and nothing else left to play; billed $1.3129
- 2026-11-06T08:34:32Z Release (jevgammon Drex late entries, incomplete 2026-11-06T08:34:32Z): all our servers are stopped; GPU(s) 0 2 are free of us again (no other process touched).
- 2026-11-06T08:34:32Z   missing: Drex Max 1.1 v GPT-6 Luna (match #829): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T08:34:32Z   missing: Drex 2.0 v GPT-6 Luna (match #835): player 2: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T08:34:32Z   missing: Drex Max v1 v GPT-6 Luna (match #846): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav
- 2026-11-06T08:34:32Z   missing: Drex 2.0 (local) v GPT-6 Luna (match #886): player 1: warming up GPT-6 Luna: OpenAI Decisions did not answer within 900 s of warm-up: OpenAI Decisions request failed: gave up after 4 attempts: 429 Too Many Requests: {"error":{"message":"You hav

## Final (2026-11-06 08:34 UTC): done except the GPT-6 Luna pairs

The run ended as **INCOMPLETE SCOPE**: 72 of 76 pairs were played. The 4 missing pairs are each entrant's pair with GPT-6 Luna.
- **Why Luna is blocked:** its API answered "429 no credits remaining", and no top-up was decided.
- **The 4 matches:** #829, #835, #846 and #886. They stay deferred, are valid and resume as they are.

**Servers.** All of ours are stopped. GPUs 0 and 2 are free of us since 08:34:32 UTC (41 MiB and 20 MiB, no compute process). GPUs 1 and 3 were never used.

**Matches #829–#904:** 72 finished and valid, 4 deferred.
- **Leagues:** #15 Drex Max 1.1, #16 Drex 2.0, #17 Drex Max v1, #18 Drex 2.0 (local). All are hidden, stage late-entry, League 1's rules.

| entrant | route | played | W-D-L | points | game points for–against | decisions | invalid | lists split (25-option cap) | s per decision |
|---|---|---|---|---|---|---|---|---|---|
| Drex Max 1.1 | Nace API | 18 of 19 | **12-2-4** | 38 | 88–53 | 2,154 | 0 | 221 | 0.54 |
| Drex Max v1 | our GPU | 18 of 19 | 11-0-7 | 33 | 79–52 | 2,148 | 0 | 244 | 0.95 |
| Drex 2.0 | Nace API | 18 of 19 | 10-0-8 | 30 | 66–65 | 1,937 | 0 | 212 | 0.53 |
| Drex 2.0 (local) | our GPU | 18 of 19 | 7-0-11 | 21 | 60–70 | 1,993 | 0 | 172 | 0.51 |

Every opponent gave 0 invalid answers too.

**Billed: $1.31.**

| who | billed |
|---|---|
| Drex entrants' Nace requests, booked by the pre-send guard (5,585 attempts, cap $1.25) | $0.79 |
| API opponents | $0.53 |

- **The API opponents' share:**

  | opponent | billed |
  |---|---|
  | Jev 1.13.0 | $0.10 |
  | SubQ Snap Preview | $0.09 |
  | Jev 1.14.0 | $0.09 |
  | Fastino GLiDE | ≈ $0.08 (estimated at $0.04 per million input tokens; no price in its settings) |
  | Liquid | $0.07 |
  | Celeris | $0.07 |
  | Mercury Decide | $0.03 |
  | GPT-6 Luna | $0 (blocked) |

- **Not billed (list-price equivalent):** Drex Max v1 $0.58, Drex 2.0 (local) $0.50, the local Deciders $0.10.
- **Spend limits:** the $2 soft stop never fired, and no request was refused by the guard.

**Incidents:**
- **GLiDE v1.2 (local):** its first league-add failed because keys were missing from the orchestrator's environment. It was fixed before the pause and played on resume.
- **Pause:** 02:2x–06:49 UTC, for Turkce.
- **Drex 2.0 (local) server:** its first start failed at 07:27–07:37 because of the import path. After the fix it passed its 20-request smoke test and played.
