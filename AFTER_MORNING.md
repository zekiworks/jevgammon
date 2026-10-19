# After the morning (bariton GPUs 0-2 back to you)

Overnight from 2026-10-19 22:26 UTC, bariton's GPUs serve League 2 (and, later, one League 1
player). Details and measurements: `tools/v3/servers/README.md`, section "League 2 overnight on
bariton GPUs 0-2".

| GPU | server | script | players |
|---|---|---|---|
| 0 | Gemma 4 31B, one vLLM replica (`v3-gemma4-31b-g0`, :8900) behind the proxy (`v3-gemma-proxy`, :8894) | `GEMMA_GPUS=0 GEMMA_MAX_SEQS=24 tools/v3/servers/gemma4-31b-replicas.sh` | League 2: Gemma 4 31B (off), (on) |
| 1 | Qwen3.8-27B fp16 (`v3-qwen38-27b`, :8897); once its playable matches are done, Decider v1.2 27B (`v3-decider-v12`, :18099) | `tools/v3/servers/qwen38-27b.sh`; `DECIDER_V12_GPU=1 tools/v3/servers/decider-v1.2.sh 27b` | League 2: Qwen3.8-27B (off), (on); then League 1: Decider v1.2 27B |
| 2 | LFM2.5-24B-A2B bf16 (`v3-lfm25-24b`, :8898) | `tools/v3/servers/lfm25-24b.sh` | League 2: LFM2.5-24B-A2B (off), (on) |
| 3 | Open-Jev (`v3-open-jev`), Winnow-12B (`v3-winnow`), Decider Flash v1.2 (`v3-decider-flash-v12`) | `open-jev.sh` (`OPEN_JEV_GPU=3`), `winnow.sh`, `decider-v1.2.sh flash` | League 1 (unchanged) |

The swap on GPU 1 is automatic: the `v3-swap-qwen-decider` unit (`tools/v3/swap_qwen_decider.sh`)
waits until Qwen3.8-27B has no League 2 fixture left to play except against OpenRouter
players, then stops Qwen, starts Decider v1.2 27B and runs `league-add` for it in League 1
(after a v3.db backup). See whether it happened: `journalctl --user -u v3-swap-qwen-decider`.

## Free GPUs 0-2 (one command)

```sh
tools/v3/league_control.sh free
```

It stops both league runners, stops the swap watcher, stops every server on GPUs 0-2 (noting
which were up), then starts `league1` and `league2` again: both leagues keep playing on GPU 3,
the DGX Sparks and the APIs. Unfinished Gemma / Qwen / LFM2.5 (and Decider v1.2 27B) matches
are deferred and retried with back-off; they resume from their last stored turn once their
servers are back. Log: `league_control.log`.

- `tools/v3/league_control.sh pause` stops the leagues as well (they stay stopped);
  `pause all` also stops GPU 3's League 1 servers.
- `tools/v3/league_control.sh resume` brings back the servers the last pause noted, then both
  leagues (about 4 minutes).

## Still to do

- Unfinished Gemma 4 31B matches without bariton: `tools/v3/servers/spark.sh start` starts
  Gemma on spark3 again (Decider is left as it is), then set both Gemma entries' `base_url` back
  to `http://192.168.1.139:8894/v1` in v3.db (`leagues.models`, league 2) and
  `leagues/league2-l1chat.json`, note the move in `device` and the league note, and restart
  `league2` (back up v3.db first).
- spark2 hung: power-cycle it, then on spark2 `systemctl --user disable --now
  qwen36-nvfp4.service` (approved), or that unit takes about 100 GB again.
- OpenRouter is out of credit (HTTP 402 since at least 22:26 UTC): League 2's DeepSeek V4.1
  Flash (off, on), GLM-5.3 (on) and Qwen3.8 Flash (off) back off until it is topped up; their
  fixtures against Qwen3.8-27B then need `qwen38-27b.sh` running again.
- DeepSeek V4.1 Flash on our own GPUs (`deepseek-v41.service` needs all four) was skipped
  tonight.
