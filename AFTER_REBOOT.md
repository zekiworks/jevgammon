# After the reboot of Oct 25, 2026 (ladder round 2, League 2 block)

State before the reboot: League 1 and League 3 finished. League 2 had 8 matches left (Gemma 4 31B (on) and Qwen3.8-27B (on) against Fastino GLiDE, Grok 4.7 (off) and DeepSeek V4.1 Flash 1017). Close choices stage B: the 5 subscription teams were done (600 predictions in the store, Gemma's included); Gemma (on)'s play calls were in progress (2,522 of 3,000 play answers stored in total). Argon (off)'s early start for round 3 was being set up, possibly not started yet.

1. Check all 4 GPUs: `nvidia-smi`. Only GPUs 0 and 1 are ours (2 and 3 went back to compactor).
2. The dashboard comes back by itself (league-web is an enabled user service). Check http://192.168.1.126:8095.
3. Start Gemma 4 31B on GPU 0 behind the proxy :8894 (`GEMMA_GPUS=0`, one replica, same args) and Qwen3.8-27B on GPU 1 at :8897 (`QWEN27_GPU=1`). Commands: mailbox/Ladder round 1 - log.md. Post the claim on the bus.
4. Resume League 2: `systemctl --user reset-failed league2; systemd-run --user --unit=league2 --working-directory=$HOME/code/jevgammon bash -c 'tools/v3/run_league2.sh >> league2.log 2>&1'`. Matches resume from their last move.
5. Stage B, Gemma: do NOT rerun `ask` (one run, no re-ask). The calls cut off by the reboot are reported as excluded, with reason "run interrupted by reboot". Decide with Can whether the remaining Gemma positions get a new run, recorded in Method first.
6. Argon (off) early start: check whether its early-start league row exists and resume or create it (see the round-2 log).

deepseek-v41.service stays disabled.

## Second reboot (Oct 25, ~12:20 UTC)

Running before it: league2 (last matches), league2early (Argon (off) early start for round 3, a hidden league row), ccb-gemma-s2 (Gemma stage B session 2, 44 of 500 Gemma play answers stored).
1. Start Gemma (GPU 0) and Qwen (GPU 1) as above; claim them on the bus.
2. `systemctl --user reset-failed league2 league2early` and start both again the same way (see `systemctl --user cat` of each, or the round-2 log). Matches resume from their last move.
3. Gemma stage B: a third session for the play calls with no stored answer needs Can's OK and a Method addendum first. Same skip check (dry run on a copy of the store).
- league2early: `systemd-run --user --unit=league2early --working-directory=$HOME/code/jevgammon bash -c 'tools/v3/run_league2_early.sh >> league2-early.log 2>&1'`
- Gemma stage B session 3 (only after Can's OK + Method addendum): same command as session 2, `jevgammon-ccb2/target/release/jevgammon ask --config leagues/close-choices-b-gemma.json --positions positions/close-choices-b-v2.jsonl --out smoke/close-choices-b.db --repeats 5 --once --retries 2` (it skips stored answers).

## Third reboot (Oct 25, after 13:40 UTC; GPU fault)

Cause: 13:05:40 UTC GPU 2 (PCI e1:00) fell off the bus (Xid 79); the driver marked the others "Node Reboot Required" (Xid 154). Qwen died 13:06 and would not restart ("CUDA unknown error"). Gemma (GPU 0) kept serving League 2.
Done before it: Method §9.13 third-session addendum live (13:32 UTC, commit e17fcc9, deployed 13:35); skip dry run passed (455 asked, 45 stored untouched); 5-team stage B report written (`mailbox/Close choices - stage B results (5 teams).md`). Fixed snapshot.py name clash (143ab65) that had broken the update loop.
1. Gemma (GPU 0), Qwen (GPU 1) as above; bus claim. `reset-failed` and restart `league2`, `league2early` as above.
2. Start Gemma stage B session 3 (NOT started yet), unit `ccb-gemma-s3`, same command as session 2 with "session 3" in the echo lines and log `smoke/close-choices-b-gemma-session3.log`. If anything was stored meanwhile (it should not be), re-run the dry run first.
3. Then: Gemma section in the stage B report (three-session note), Method live status, round 3 request, round-2 log (see the Round2Finish2 task list).
