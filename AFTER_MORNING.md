# v3 leagues: state and how to restart (2026-10-21)

League 1 finished on 2026-10-20 20:41:52 UTC. League 3 (unit `league3`) uses subscriptions only
and needs no local server. League 2 (unit `league2`) has DeepSeek V4.1 Flash's last matches left,
against the thinking players (Gemma 4 31B (on), LFM2.5-24B-A2B (on), Qwen3.8-27B (on)). Details,
equivalence checks and history: `tools/v3/servers/README.md`, `freeze/league2-changes.json`, and
the players' `device` fields in `v3.db` (`leagues.models`, league 2).

Scheduled: at 00:00 UTC on 2026-10-22 `midnight-takeover.timer` (one-shot, `tools/v3/systemd/`) runs
`tools/v3/midnight_takeover.sh`: stops the user's GPU jobs (docker stop / SIGINT, SIGTERM; never
SIGKILL), runs the Part A local smoke tests (d3-turbo, Nemotron 3.5 Bolt), resumes League 2 as below
(check: `tools/v3/ds_equiv.py`), and when it has finished does the shutdown below and writes
`mailbox/Midnight takeover - log.md`. Log: `midnight-takeover.log`. Preview: `--dry-run`. Cancel:
`systemctl --user disable --now midnight-takeover.timer` (or stop `midnight-takeover.service`).

## Servers League 2 uses now

| where | server | URL in v3.db | start |
|---|---|---|---|
| bariton, all four GPUs | DeepSeek V4.1 Flash (SGLang, 2026-10-17 revision) | `http://127.0.0.2:8010/v1` | `cd ~/code/deepseek-v4.1-flash-4x-rtx-pro-6000 && BIND_ADDRESS=127.0.0.2 docker compose -f compose.yaml up -d` (about 2 min); stop: `docker compose -f compose.yaml stop`. `deepseek-v41.service` stays disabled. |
| spark3 | Gemma 4 31B (`v3-gemma4-31b`) | `http://192.168.1.139:8894/v1` | on spark3, `cd ~/code/v3-servers && BIND_HOST=0.0.0.0 GEMMA_MAX_SEQS=24 ./gemma4-31b.sh start`, **before** LFM2.5 (it is OOM-killed when started after it) |
| spark3 | LFM2.5-24B-A2B (`v3-lfm25-24b`) | `http://192.168.1.139:8898/v1` | on spark3, `cd ~/code/v3-servers && BIND_HOST=0.0.0.0 LFM_GPU=0 ./lfm25-24b.sh start` |
| spark | Qwen3.8-27B (`v3-qwen38-27b`) | `http://192.168.1.127:8897/v1` | on spark, `cd ~/code/v3-servers && BIND_HOST=0.0.0.0 QWEN27_GPU=0 ./qwen38-27b.sh start` |

spark2 holds the user's own container: not used.

## Pause and resume League 2

- Pause: `systemctl --user kill -s SIGINT league2` (matches keep their stored turns), then stop
  DeepSeek (`docker compose -f compose.yaml stop` in its directory) to empty bariton's GPUs.
- Resume: check `nvidia-smi` shows no other process on bariton's GPUs, start DeepSeek (above), wait
  until `curl http://127.0.0.2:8010/v1/models` answers, optionally re-check with `/tmp/equiv.py ds-off
  http://127.0.0.2:8010/v1` (17/20 at each check so far), then
  `systemctl --user reset-failed league2; systemd-run --user --unit=league2 --working-directory=$HOME/code/jevgammon /usr/bin/bash -c "tools/v3/run_league2.sh >> league2.log 2>&1"`.

## When League 2 has finished

Stop DeepSeek (above), and the Spark servers League 3 does not need: on spark3
`./gemma4-31b.sh stop; ./lfm25-24b.sh stop`, on spark `./qwen38-27b.sh stop` (in
`~/code/v3-servers`). League 1's Spark servers (Clef and Cygnet on spark, Decider v1.1 27B on
spark3) are already stopped (since 2026-10-20 21:10 UTC); to bring them back, stop the League 2
servers on the Sparks first, then `tools/v3/servers/spark.sh start` (about 10 min to load; it also
starts Gemma 4 31B on spark3 after Decider).
The v3 page refreshes itself (`v3-page-refresh.timer`); a final refresh:
`systemctl --user start v3-page-refresh.service`.
