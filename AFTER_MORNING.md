# v3 leagues: state and how to restart (2026-10-22)

League 1 finished on 2026-10-20 20:41:52 UTC; League 3 has finished. League 2 (unit `league2`) is
**paused since 2026-10-22 16:20 UTC** (Can: bariton's GPUs go to compactor until tonight). Unfinished
(DeepSeek V4.1 Flash's last matches): #311 DeepSeek (off) v LFM2.5-24B-A2B (on), #348 DeepSeek (on) v
LFM2.5 (on), #349 Gemma 4 31B (on) v DeepSeek (on), plus whatever the league has not started yet. They
resume from their last stored turn. Details, equivalence checks and history: `tools/v3/servers/README.md`,
`freeze/league2-changes.json`, and the players' `device` fields in `v3.db` (`leagues.models`, league 2).

The roster in `v3.db` is already set for the resume (since 2026-10-22 15:37 UTC; no change needed):

| player | where | URL in v3.db |
|---|---|---|
| DeepSeek V4.1 Flash (off, on) | Fireworks via OpenRouter, pinned (`order: [fireworks]`, `allow_fallbacks: false`), rpm 18 | `https://openrouter.ai/api/v1` |
| Gemma 4 31B (off, on) | bariton GPUs 0 and 1, two replicas behind the least-busy proxy | `http://127.0.0.1:8894/v1` |
| LFM2.5-24B-A2B (off, on) | bariton GPU 2 | `http://127.0.0.1:8898/v1` |
| Qwen3.8-27B (off, on) | bariton GPU 3 | `http://127.0.0.1:8897/v1` |

OpenRouter credit at the pause: $6.01 left (League 2 spent $0.31 on Fireworks in 43 min).
DeepSeek's own server (`~/code/deepseek-v4.1-flash-4x-rtx-pro-6000`) and the Spark copies stay stopped.

## Resume League 2 tonight

1. Check bariton's GPUs are free (`nvidia-smi`; ComfyUI's small share on GPUs 2 and 3 is fine) and
   that compactor is done (`~/agent-bus/bus`). Check credit: `set -a; . ~/.keys; set +a; curl -s
   https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPENROUTER_API_KEY"` (over $3).
2. Start the servers (about 7 min in total):
   ```
   cd ~/code/jevgammon/tools/v3/servers
   GEMMA_GPUS="0 1" GEMMA_MAX_SEQS=24 ./gemma4-31b-replicas.sh start
   LFM_GPU=2 ./lfm25-24b.sh start
   QWEN27_GPU=3 ./qwen38-27b.sh start
   ```
3. Optional re-check (20 stored requests each; 22 Oct: Gemma 20/20, LFM2.5 17/20, Qwen 20/20):
   `python3 -u /tmp/equiv.py gemma-off http://127.0.0.1:8894/v1` (and `lfm-off` `:8898`, `qwen-off` `:8897`).
4. Resume: `systemctl --user reset-failed league2; systemd-run --user --unit=league2
   --working-directory=$HOME/code/jevgammon /usr/bin/bash -c "tools/v3/run_league2.sh >> league2.log 2>&1"`.
5. Post on the bus to compactor that GPUs 0-3 hold League 2 until it ends.

Pause again: `systemctl --user kill -s SIGINT league2`, then `./gemma4-31b-replicas.sh stop;
./lfm25-24b.sh stop; ./qwen38-27b.sh stop` (same directory).

## When League 2 has finished

Stop the three bariton servers (above), then `systemctl --user start v3-page-refresh.service` and
`systemctl --user start bg-site-preview.service`, check https://zekiworks.github.io/analysis/backgammon/,
post the release on the bus, and write `mailbox/League 2 final - log.md` (timeline, checks, spend,
final top 5). `resume-league2` / `midnight_takeover.sh` is not used any more (stopped 22 Oct 15:27 UTC).
