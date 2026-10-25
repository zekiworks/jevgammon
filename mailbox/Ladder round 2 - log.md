# Ladder round 2: log

Approved by Can; run as in `Ladder round 2 - request.md`. **Status (Oct 25, 19:05 UTC): round 2 is finished.** Leagues 1, 2 and 3 are done (League 2 at 19:00:53 UTC). Argon (off)'s early start for round 3 is done too (hidden league #4). Round 3 is written, provisional and not applied: `Ladder round 3 - request.md`.

## Timeline (UTC)

- Oct 24, 15:38: `tools/ladder.py plan` re-run: identical to the request. `apply --db v3.db --round 2` did the 4 league-removes, but its first league-add failed: `FASTINO_API_KEY` was not in the environment. I ran the 4 league-adds by hand with `~/.keys` loaded, using the same entries and freeze logs. No v3.db backup was made.
- 15:39: block 1 started (systemd user units `league2`, `league3`). GPU claim on the bus (#60).
- 18:20: OpenRouter credit ran out (402). DeepSeek (on) and GLM matches were deferred; Can added $30 ($105 total), and they resumed on their own.
- 18:39: late entries (Can): Kimi K3.1 Pro (off) into League 3, DeepSeek V4.1 Flash 1017 (off)/(on) into League 2. `target/release/jevgammon` was replaced by the budget-ledger build (`target/parta`, commit 6fbf445; additive only). League 3 was restarted so that Kimi plays under the $30 cap. DeepSeek 1017: see `DeepSeek V4.1 Flash 1017 - log.md`.
- 16:45 (bus #62): compactor released GPUs 0-3. 16:48: LFM2.5 (GPU 3), GLiDE v1.2 (GPU 0), Decider v1.2 27B + Flash, Winnow (GPU 1), Decider v1.1 (GPU 2); `league1` started.
- 21:10: Cygnet on GPU 0 (`CYGNET_UTIL=0.34`). Clef did not fit next to Decider v1.1 (it needs about 51 GB).
- ~23:45: block 1 done (27 of 27). The last was #581, GPT-6.1 Sol (high) v Grok 4.7 (on).
- Oct 25, 02:39: Kimi's League 3 matches done; League 3 finished.
- 02:39-05:34: as League 1 matches finished, servers were swapped: Winnow, Decider Flash and 27B stopped; Open-Jev on GPU 1 (05:09); Decider v1.1 stopped and Clef on GPU 2 (05:34); GLiDE v1.2 stopped.
- 07:55: Cygnet stopped; Gemma 4 31B on GPU 0 (`GEMMA_GPUS=0 GEMMA_MAX_SEQS=24`, proxy :8894). League 2 restarted to cut its back-off.
- 09:49: Open-Jev stopped; Qwen3.8-27B on GPU 1 (`QWEN27_GPU=1`, :8897).
- 10:27: League 1 finished. Clef and LFM2.5 stopped; GPUs 2 and 3 released (bus #67).
- ~11:46: first bariton reboot (see `AFTER_REBOOT.md`). Gemma and Qwen restarted, League 2 resumed from its last moves.
- 12:16-12:17: early start for round 3 (Can): runner options `leagues.only_pairs_of` and `leagues.hidden` (487c372, 413e565); hidden league #4 started 12:17:33 (unit `league2early`), playing only Gemini 4 Argon (off)'s pairs.
- ~12:20: second reboot; same restarts.
- 13:05:40: GPU 2 (compactor's) fell off the bus (Xid 79); the driver marked the other GPUs "Node Reboot Required". Qwen died at 13:06 and would not restart; Gemma kept playing. Can rebooted bariton; 13:55:48 Gemma (GPU 0), Qwen (GPU 1), `league2` and `league2early` back.
- 16:45:28: hidden league #4 finished: 15 Argon (off) matches (#652-666); its other 3 League 2 pairs (GNUbg weak, Claude Fable 5.1 (off), Grok 4.7 (off)) were already played in earlier rounds.
- 18:16: League 2's Gemma matches done; Gemma stopped, GPU 0 released on the bus (#83).
- 19:00:53: League 2 finished (last: Grok 4.7 (off) v Qwen3.8-27B (on)). 19:01: Qwen stopped, GPU 1 released (#84). `tools/site/score.sh v3.db ~/.local/state/bg-site/plays` (on v3.db, no copy): 4 decisions newly scored.
- 19:01: `tools/ladder.py plan` stopped on Argon's unscored hidden-league decisions: the site scorer skipped matches held only by a hidden league. They are valid matches and count in every error rate (Method), so `tools/site/score_plays.py` now scores them too; `score.sh v3.db ~/.local/state/bg-site/plays` (no copy) scored 3,483 more decisions, none left pending. Only the 16 setups of the early-start matches changed error rate (e.g. Argon (off) 15.93 to 15.84). The plan then ran: round 3, 37 new pairings, 27 reused.
- Device notes in v3.db were updated for every server move up to 10:27. The restarts after the reboots kept the same servers on the same GPUs; the final stops (Gemma 18:16, Qwen 19:01) are not in the device notes.

## Spend

- Round 2, at list price (turns.cost_usd, matches 555-601 and 620-623): **about $4.80**. OpenRouter Fireworks $4.62; alibaba $0.06; Liquid, Jev, SubQ, Luna, Celeris and Mercury a few cents each. Fastino: no price recorded.
- OpenRouter counter: $71.26 before the round, $94.44 at 10:27 Oct 25. That includes Kimi (ledger about $14 including smoke) and DeepSeek 1017.
- League 2 after 10:27 Oct 25 (turns.cost_usd): $6.84 at list price.
- Early start (hidden league #4, matches 652-666), at list price: Gemini 4 Argon (off) $17.58, Gemini 3.8 Flash (high) $2.89, Claude Sonnet 5.5 (high) $2.65, (low) $1.61 (subscriptions, API-equivalent, not billed); OpenRouter-billed opponents (DeepSeek V4.1 Flash (on)/(off), 1017 (on)/(off), GLM-5.3 (on), Qwen3.8 Flash (off)) $2.37; Liquid and Jev a few cents.

## Early start for round 3 (Gemini 4 Argon (off) in League 2): done

- Can approved starting Argon (off)'s round 3 League 2 matches early; `ladder.py plan` relegates Argon (off), with no lock rule (confirmed again by the round 3 plan).
- Played in hidden league #4 (`only_pairs_of` = Gemini 4 Argon (off), hidden from the site, the dashboard and the ladder tools), 2026-10-25 12:17:33-16:45:28 UTC, across two reboots (resumed from the last stored turns): 15 matches, #652-666, GNUbg-scored. Round 3 reuses them (listed under "Reused pairings" in its request).
- Can skipped Argon (off)'s two pairs with Gemini 3.8 Flash (low) and Qwen3.8-27B (off) in the early start: both leave League 2 in round 3, so after the moves they are not League 2 pairings. No round-3 pairing is skipped.

## Next

- Round 3: `Ladder round 3 - request.md`, provisional (late entries), waiting for Can's approval; not applied.
