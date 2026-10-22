# v3 leagues: state and how to restart (2026-10-22)

League 1 was **reopened on 2026-10-22** for a late joiner, Fastino GLiDE v1.2 (local), and is **paused since
17:22 UTC** (Can) with 17 of its 18 matches left (section below). League 3 has finished. League 2 (unit `league2`) is
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
DeepSeek's own server (`~/code/deepseek-v4.1-flash-4x-rtx-pro-6000`) and League 2's Spark copies stay stopped.
League 1's Spark servers (Clef and Cygnet on spark, Decider v1.1 on spark3) are **running** for League 1.

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

## Resume League 1 (Fastino GLiDE v1.2's matches)

League 1 (unit `league1`) paused 2026-10-22 17:22 UTC (SIGINT) after 6 minutes of play. Fastino GLiDE v1.2
(local) has 1 of 18 matches played (lost 2-4 to SubQ Snap Preview); 4 started matches (v Open-Jev, Clef,
Cygnet, Decider v1.1 27B) resume from their last stored turn and 13 have not started. It needs 3 bariton
GPUs, and League 2's servers take all 4, so play them **before or after League 2**, not together (about
1-3 h; the slow part is Clef and Decider v1.1 on the Sparks, one match at a time each).

1. Claim the GPUs on the bus (compactor) and wait for the release; check `nvidia-smi` (GPUs 0, 1, 3 free).
2. The Spark servers should still be up: `. tools/v3/servers/_lib.sh; systemone_probe http://192.168.1.127:18091 clef`
   (and `:18093 cygnet`, `http://192.168.1.139:18097 pplx-decider-v1.1-27b`). If not, start them without Gemma
   (`spark.sh start` would also start Gemma on spark3): for spark `cygnet.sh`, then `clef.sh`; for spark3
   `decider.sh`; each as `ssh sparkX 'cd ~/code/v3-servers && BIND_HOST=0.0.0.0 CYGNET_UTIL=0.28 CLEF_GPU=0
   DECIDER_GPU=0 ./NAME.sh start'` after `bash -c "source ./_lib.sh && free_page_cache"` there.
3. Start the bariton servers (about 2 min):
   ```
   cd ~/code/jevgammon/tools/v3/servers
   GLIDE_GPU=0 ./glide-v12.sh start && ./glide-v12.sh probe
   OPEN_JEV_GPU=3 ./open-jev.sh start
   DECIDER_V12_GPU=1 ./decider-v1.2.sh 27b start && DECIDER_V12_GPU=1 ./decider-v1.2.sh flash start && WINNOW_GPU=1 ./winnow.sh start
   ```
4. Resume: `systemctl --user reset-failed league1; systemd-run --user --unit=league1
   --working-directory=$HOME/code/jevgammon /usr/bin/bash -c "tools/v3/run_league1.sh >> league1.log 2>&1"`.
5. When League 1 finishes (19 entrants, 171 + 18 = 189 matches): stop the five bariton servers (`stop`
   instead of `start`) and the Spark servers (`./NAME.sh stop` on each Spark), post the release on the bus,
   `systemctl --user start v3-page-refresh.service`, and add the results to `mailbox/GLiDE v1.2 - log.md`.

Pause again: `systemctl --user kill -s SIGINT league1`, then stop the servers as in step 5.

## When League 2 has finished

Stop the three bariton servers (above), then `systemctl --user start v3-page-refresh.service` and
`systemctl --user start bg-site-preview.service`, check https://zekiworks.github.io/analysis/backgammon/,
post the release on the bus, and write `mailbox/League 2 final - log.md` (timeline, checks, spend,
final top 5). `resume-league2` / `midnight_takeover.sh` is not used any more (stopped 22 Oct 15:27 UTC).
