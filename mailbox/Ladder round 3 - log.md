# Ladder round 3: log

Approved by Can; run as in `Ladder round 3 - request.md`. **Status (Oct 26, 03:30 UTC): 33 of 37 new pairings played; 4 are blocked by the OpenRouter key limit** ($100.02 of $100.00 used on the key, 403 "Key limit exceeded"; the account still has about $5 credit). The runners (`league2`, `league3`) keep retrying them hourly and play them once Can raises the key limit. Round 4 is not written yet: its plan depends on those 4 matches.

## Timeline (UTC)

- Oct 25, 19:58: `tools/ladder.py plan` re-run: identical to the request (apart from its hand-written notes). `apply --db v3.db --round 3` (with `~/.keys` loaded): 4 removes, 4 adds; Gemini 4 Argon (off) joined League 2 with 0 new matches, so its 15 early matches (#652-666) count and were not replayed. No v3.db backup.
- 20:00: block 1 started (units `league2`, `league3`). OpenRouter: $105 credit, $98.36 used. GPU claim on the bus (#85).
- 20:04 (bus #86/87): compactor gave GPUs 0 and 1: Gemma 4 31B on GPU 0 (`GEMMA_GPUS=0 GEMMA_MAX_SEQS=24`), Qwen3.8-27B on GPU 1 (`QWEN27_GPU=1`). `league2` restarted to cut its back-off; `league1` started (Qwen (off) v the API/program setups).
- 20:26 (bus #88): GPUs 2 and 3 released by compactor. Decider v1.2 27B + Flash and Winnow on GPU 2, Decider v1.1 on GPU 3 (GLiDE v1.2 did not fit next to it). Block 1 of League 1 done by ~20:43; those servers stopped; GLiDE v1.2 on GPU 3, Clef on GPU 2, Cygnet on GPU 3 (`CYGNET_UTIL=0.34`; it did not fit next to Clef). `cygnet.sh` got a `CYGNET_GPU` option (default 0, as before) for this.
- 20:48-21:48: pause by Can (GPUs to compactor). Main took over the pause at ~21:00: league1 and every GPU server stopped, league2/league3 kept playing API/subscription matches (bus #91).
- 21:48 (bus #96): GPUs back. Gemma (0), Qwen (1), Open-Jev (2), Cygnet (3); league1 and league2 restarted. Cygnet's match ended at once: Cygnet stopped, GPU 3 released. I posted GPU 2 free too early (my log check matched an older Open-Jev v Qwen (off) match from matchday 10), restarted Open-Jev and posted a correction; its match ended ~22:00, Open-Jev stopped, GPU 2 released. League 1 finished.
- Oct 26, 00:22: Jev 1.14.0 v Gemma 4 31B (on) done; Gemma stopped, GPU 0 released on the bus.
- 01:21: Jev 1.14.0 v Qwen3.8-27B (on) done; Qwen stopped, GPU 1 released. No GPU job of ours runs.
- 03:22: last subscription match (#678, Gemini 3.8 Flash (low) v Gemini 4 Argon (on)) done.
- 03:25: `tools/site/score.sh v3.db ~/.local/state/bg-site/plays` (on v3.db, no copy): 4 decisions newly scored.
- No Xid 79 / GPU drop this round. Disk: / at 151 GB free at the start, 50 GB at 23:00 (not from us: v3.db 31 GB, logs small); reported to Main, nothing deleted.

## Blocked (OpenRouter key limit)

- #675 DeepSeek V4.1 Flash (on) v Jev 1.14.0
- #699 Gemini 3.8 Flash (low) v Kimi K3.1 Pro (off)
- #702 DeepSeek V4.1 Flash 1017 (off) v Jev 1.14.0
- #703 DeepSeek V4.1 Flash 1017 (on) v Jev 1.14.0

All four are partly played and resume from their last stored turn. A trial `ladder.py plan` now (not written to the mailbox) gives round 4 as Clef L1→L2, Jev 1.14.0 L2→L1, Gemini 4 Argon (off) L2→L3, Kimi K3.1 Pro (off) L3→L2; Jev and Kimi both still have blocked matches, so this can change.

## Spend

- Round 3 at list price (turns.cost_usd, matches 667-703): OpenRouter-billed setups about $1.65 (DeepSeek V4.1 Flash (on) $0.78, Kimi K3.1 Pro (off) $0.49, GLM-5.3 (on) $0.29, DeepSeek (off) and Qwen3.8 Flash (off) a few cents); Jev, Luna, SubQ, Celeris, Mercury, Deciders a few cents each. Subscriptions (API-equivalent, not billed): Gemini 4 Argon (on) $36.83, Claude Fable 5.1 (on) $15.64, Grok 4.7 (on) $13.53, the rest smaller.
- OpenRouter counter: $98.36 before the round, $100.02 now (key limit $100 reached).

## Next

- Can: raise the OpenRouter key limit; the 4 matches then play by themselves (hourly retry).
- Then: score (`tools/site/score.sh v3.db ~/.local/state/bg-site/plays`), `tools/ladder.py plan --db v3.db --out "mailbox/Ladder round 4 - request.md"` (or "ladder settled").
