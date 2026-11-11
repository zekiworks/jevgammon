# Late entries Muse Ember - status 2026-11-10

Go: Can, bus #4144 (Main's recommendation #4142: backgammon late entry now). First match id: #923.

Muse Ember (max) joins the **original League 1 table** as a late entry, in the format of the Base Labs, SubQ Snap 1.1, Drex and REAX 1.3 late entries: its own hidden late-entry league (**#20**) that plays only its pairs, once each, against the 19 original setups.

## Procedure (as REAX 1.3, `workspace/reax/`)

- **Player** `Muse Ember (max)` (players #61, new name): the smoke config (`workspace/ember-smoke-2026-11-10/muse-ember-max/settings.json`: `openai-compatible/meta/muse-ember` via OpenRouter, provider `only: [meta]`, no fallbacks, `reasoning` `max`, `letter_readout` `answer`, `logprobs`/`top_logprobs` removed, $0.10/M in, $0.50/M out) plus `parallel` 4 (as the smoke and Kimi K3.1 Pro (off)) and a budget ledger (`workspace/late-ember/state/ember-budget.db`, hard pre-send cap $19.50). Price re-read 2026-11-10 from OpenRouter's endpoints list: Meta $0.10/M prompt, $0.50/M completion.
- **Rules:** League 1's seed 2567889193785291627 with pair-v1 dice, `bg-v2`, option-order seed 1190975713392774006, `mirror_concurrent`, 3 rounds, no clock, delay 30 s, 300 turns; `only_pairs_of`, `hidden`; `stage = 'late-entry'` through v3.db's `late_entry_stage` trigger (name added). Opponent settings byte-for-byte from `players.settings`. Not eligible for the Hype Cup.
- **Runner:** branch `late-ember` (origin/main 8cd2302 + scripts only), clean worktree `~/code/jevgammon-ember`, binary `target/ember/release/jevgammon`; matches record the harness commit, clean. Scripts: `tools/v3/late-ember/` (`player.json`, `ember.py`, `run_league.sh`, `start.sh`, `locals.sh`).
- **Units:** `late-ember` (start.sh: v3.db backup `v3.db.bak-*-before-ember.zst`, trigger, config, then the guard) and `late-ember-league` (the league runner, log `late-ember.log`).
- **Money guard (every 60 s):** stops the league when OpenRouter's balance is under $41 (keeps $40) or when Ember's ledger plus the paid opponents' cost reaches $19.75 (the run's $20 with margin: a reservation books 32,768 output tokens, Meta's max reasoning can pass that; smoke maximum 83,103).
- **Opponents now (10):** GNUbg weak, Random, Safest; Celeris-1 Decision, Fastino GLiDE, Jev 1.13.0, Jev 1.14.0, Liquid d1-ultra, Mercury Decide (OpenRouter), SubQ Snap Preview. **GPT-6 Luna deferred** (OpenAI out of credit, as REAX).
- **Queued (8 local):** Cygnet (Gemma 4 12B) 32.6 GB, Winnow-12B 13.4 GB, Decider Flash v1.2 9.4 GB, Decider v1.2 27B 50.4 GB, Fastino GLiDE v1.2 (local) 52.8 GB, Clef 53.1 GB, Open-Jev 27B v1.1 53.1 GB, Decider v1.1 27B 50.4 GB (measured 7 Nov). No shared server matches (Main, bus resources). They run one at a time on bariton GPU 0 (reservation r_57d739c4cd53) after Gemma 4 31B's 'Did they improve?' run, on Main's word:

      systemd-run --user --unit=late-ember-locals --working-directory=/home/cbasaran/code/jevgammon \
        -E OPP_GPU=0 -E RES=r_57d739c4cd53 /home/cbasaran/code/jevgammon-ember/tools/v3/late-ember/locals.sh

## Log
- 2026-11-10T14:44:59Z guard up: runner ca1783c clean; OpenRouter $79.4584; floor $41; run cap $19.75 (Ember ledger + paid opponents from #923); 10 opponents (GPT-6 Luna deferred: no OpenAI credit; 8 local setups queued for a GPU)
- 2026-11-10T15:57:21Z Mercury Decide (match #932) deferred by the runner: OpenRouter 404 'No endpoints found for inception/mercury-decide' at the warm-up (its endpoints list is empty now; not billed); kept in the league, retried with backoff, reported missing if it stays unavailable (as Drex's Luna pairs)
- 2026-11-10T16:39:29Z API stage stopped by EmberLate: 9 of the 10 pairs played (#923-#931); Mercury Decide still has no OpenRouter endpoint (404, unbilled): pair open, blocked, kept in league #20 (missing, never dropped); units late-ember and late-ember-league stopped (no idle retries)

## API stage results (10 Nov, 14:45 to 16:38 UTC)

League #20, matches #923-#931: all 9 finished, valid, `stage = 'late-entry'`, harness ca1783c clean. Ember's score first.

| match | opponent | score | result | Ember model decisions | invalid (fallback) | Ember $ | mean s/decision |
|---|---|---|---|---|---|---|---|
| #923 | Fastino GLiDE | 4-2 | W | 117 | 1 | 0.977 | 30.3 |
| #924 | Celeris-1 Decision | 2-4 | L | 133 | 5 | 0.967 | 26.0 |
| #925 | GNUbg weak | 2-6 | L | 95 | 2 | 0.652 | 24.9 |
| #926 | Random | 5-0 | W | 37 | 2 | 0.267 | 27.0 |
| #927 | Safest | 7-1 | W | 117 | 1 | 0.695 | 21.9 |
| #928 | Liquid d1-ultra | 7-1 | W | 76 | 0 | 0.388 | 19.0 |
| #929 | Jev 1.14.0 | 5-2 | W | 133 | 5 | 1.002 | 27.1 |
| #930 | Jev 1.13.0 | 7-2 | W | 81 | 2 | 0.481 | 21.6 |
| #931 | SubQ Snap Preview | 3-4 | L | 130 | 4 | 1.128 | 31.7 |

- **Record 6-0-3.** Ember: 919 model decisions + 22 invalid answers (2.3%, each replaced by the fallback play), 3.97 M input / 12.32 M output tokens (12.14 M reasoning).
- **Route:** all 1,222 Ember exchanges answered by `meta/muse-ember`, provider Meta.
- **Spend:** Ember ledger $6.558 (1,222 attempts settled, none lost); paid opponents $0.100; run $6.66 of the $20 cap. OpenRouter balance $62.67 at 16:39 (shared with other lanes).
- **Open:** Mercury Decide (OpenRouter has no endpoint for `inception/mercury-decide`: 404, unbilled; blocked, kept), GPT-6 Luna (OpenAI out of credit; not added), the 8 local setups (queued for GPU 0).
- 2026-11-10T16:41:09Z Mercury Decide checked (Main): its stored settings (players #28) are spec openrouter-decisions/inception/mercury-decide, provider 'openrouter (inception)'; all 3,141 of its stored turns since 2026-10-20 (League 1, late entries, last REAX #922 on 7 Nov) went through OpenRouter's System One route with OPENROUTER_API_KEY; ~/.keys has no Inception key. OpenRouter now lists the model with 0 endpoints (warm-up 404 'No endpoints found', unbilled). Inception's own public /v1/models (no key, free GET) still lists mercury-decide. So: not played, the stored route has no endpoint; the model is not gone at Inception; the pair stays open (playing it via Inception would need a key and a changed config).
- 2026-11-11T11:00:55Z locals up: opponents one at a time on GPU 0 (reservation r_57d739c4cd53)
- 2026-11-11T11:03:22Z locals: started Cygnet (Gemma 4 12B) on GPU 0 (0, 32584 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T11:03:23Z locals: Cygnet (Gemma 4 12B) added to league #20
- 2026-11-11T11:39:39Z locals: Cygnet (Gemma 4 12B) played; its server stopped
- 2026-11-11T11:40:02Z locals: started Winnow-12B on GPU 0 (0, 13394 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T11:40:02Z locals: Winnow-12B added to league #20
- 2026-11-11T12:02:10Z locals: Winnow-12B played; its server stopped
- 2026-11-11T12:02:21Z locals: started Decider Flash v1.2 on GPU 0 (0, 9370 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T12:02:21Z locals: Decider Flash v1.2 added to league #20
- 2026-11-11T12:15:24Z locals: Decider Flash v1.2 played; its server stopped
- 2026-11-11T12:15:50Z locals: started Decider v1.2 27B on GPU 0 (0, 50384 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T12:15:50Z locals: Decider v1.2 27B added to league #20
- 2026-11-11T12:36:56Z locals: Decider v1.2 27B played; its server stopped
- 2026-11-11T12:37:16Z locals: started Fastino GLiDE v1.2 (local) on GPU 0 (0, 52810 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T12:37:16Z locals: Fastino GLiDE v1.2 (local) added to league #20
- 2026-11-11T13:09:24Z locals: Fastino GLiDE v1.2 (local) played; its server stopped
- 2026-11-11T13:09:45Z locals: started Clef on GPU 0 (0, 53144 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T13:09:45Z locals: Clef added to league #20
- 2026-11-11T13:39:55Z locals: Clef played; its server stopped
- 2026-11-11T13:40:26Z locals: started Open-Jev 27B v1.1 on GPU 0 (0, 53052 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T13:40:26Z locals: Open-Jev 27B v1.1 added to league #20
- 2026-11-11T14:08:38Z locals: Open-Jev 27B v1.1 played; its server stopped
- 2026-11-11T14:09:04Z locals: started Decider v1.1 27B on GPU 0 (0, 50384 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
- 2026-11-11T14:09:04Z locals: Decider v1.1 27B added to league #20
- 2026-11-11T14:32:09Z locals: Decider v1.1 27B played; its server stopped
- 2026-11-11T14:32:10Z locals: done; run spent $12.1908; GPU 0 free of us (0, 20 MiB 1, 93069 MiB 2, 92490 MiB 3, 87901 MiB )
