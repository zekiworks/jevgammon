# Ladder round 2: log

Approved by Can; run as in `Ladder round 2 - request.md`. **Status (Oct 25, ~11:00 UTC): round 2 is not finished.** Leagues 1 and 3 are done. League 2's last block (Gemma 4 31B and Qwen3.8-27B matches, including DeepSeek 1017's) is still playing on bariton GPUs 0 and 1. Round 3 has not been written yet.

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
- Device notes in v3.db were updated for every server move above.

## Spend

- Round 2, at list price (turns.cost_usd, matches 555-601 and 620-623): **about $4.80**. OpenRouter Fireworks $4.62; alibaba $0.06; Liquid, Jev, SubQ, Luna, Celeris and Mercury a few cents each. Fastino: no price recorded.
- OpenRouter counter: $71.26 before the round, $94.44 at 10:27 Oct 25. That includes Kimi (ledger about $14 including smoke) and DeepSeek 1017.

## Early start for round 3 (Gemini 4 Argon (off) in League 2): not started

- Can approved starting Argon (off)'s round 3 League 2 matches early. The check passed: `ladder.py plan` relegates Argon (off), with no lock rule.
- It is not started, because the runner cannot play only those pairs:
  - A separate hidden league would also play other unplayed pairs among its entrants: Jev 1.14.0 against the League 2 members, and the DeepSeek 1017 / Gemma / Qwen pairs that League 2 is still playing.
  - It needs either a fixture filter in the runner, or one two-player league per pairing, plus a site exclusion flag.
- Round 3 must list Gemini 3.8 Flash (low) and Qwen3.8-27B (off) as "not played: skipped by Can" if they come up.

## Still to do

1. Finish League 2's Gemma/Qwen matches. Then stop Gemma (ask CloseChoices first: its stage-B run uses the Gemma server) and Qwen, and release GPUs 0 and 1 on the bus.
2. Score with `tools/site/score.sh v3.db ~/.local/state/bg-site/plays`. Then run `tools/ladder.py plan` to write `Ladder round 3 - request.md`; it is provisional because of the late entries.
