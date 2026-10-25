# After the reboot of Oct 25, 2026 (ladder round 2, League 2 block)

State before the reboot: League 1 and League 3 finished. League 2 had 8 matches left (Gemma 4 31B (on) and Qwen3.8-27B (on) against Fastino GLiDE, Grok 4.7 (off) and DeepSeek V4.1 Flash 1017). Close choices stage B: the 5 subscription teams were done (600 predictions in the store, Gemma's included); Gemma (on)'s play calls were in progress (2,522 of 3,000 play answers stored in total). Argon (off)'s early start for round 3 was being set up, possibly not started yet.

1. Check all 4 GPUs: `nvidia-smi`. Only GPUs 0 and 1 are ours (2 and 3 went back to compactor).
2. The dashboard comes back by itself (league-web is an enabled user service). Check http://192.168.1.126:8095.
3. Start Gemma 4 31B on GPU 0 behind the proxy :8894 (`GEMMA_GPUS=0`, one replica, same args) and Qwen3.8-27B on GPU 1 at :8897 (`QWEN27_GPU=1`). Commands: mailbox/Ladder round 1 - log.md. Post the claim on the bus.
4. Resume League 2: `systemctl --user reset-failed league2; systemd-run --user --unit=league2 --working-directory=$HOME/code/jevgammon bash -c 'tools/v3/run_league2.sh >> league2.log 2>&1'`. Matches resume from their last move.
5. Stage B, Gemma: do NOT rerun `ask` (one run, no re-ask). The calls cut off by the reboot are reported as excluded, with reason "run interrupted by reboot". Decide with Can whether the remaining Gemma positions get a new run, recorded in Method first.
6. Argon (off) early start: check whether its early-start league row exists and resume or create it (see the round-2 log).

deepseek-v41.service stays disabled.
