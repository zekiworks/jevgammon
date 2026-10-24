# Ladder round 1: log

Approved by Can; run as in `Ladder round 1 - request.md`. Status: **51 of 55 new pairings played; 4 League 2 matches wait for bariton's GPUs** (one GPU fell off the bus during the round, see below). Round 2's request is not written yet: those 4 matches can change who is promoted from League 2.

## Timeline (UTC)

- Oct 23, 20:49: backup `v3.db.bak-20261023-before-ladder-r1`.
- 20:50: `python3 tools/ladder.py apply --db v3.db --round 1` (4 moves, see below).
- 20:51: block 1 (API and subscription) started: systemd user units `league2`, `league3` (`tools/v3/run_league<N>.sh`). League 2's GPU pairings failed and backed off until their servers came up. GPU claim posted to compactor on the agent bus (#45).
- 21:07: compactor released GPUs 0-3 (bus #47).
- 21:08-21:16: League 1 servers up (layout below); `league1` unit started 21:15.
- 21:19-21:20: GLiDE v1.2, Cygnet and Decider v1.1 done and stopped; Clef (GPU 0) and Open-Jev (GPU 2) started. `league1` restarted for Clef's new URL (SIGINT did not stop it while it retried Clef's old URL; SIGTERM, as in the night run).
- 21:28-21:34: Decider v1.2 27B, Decider Flash v1.2 and Winnow stopped; Gemma 4 31B on GPU 1 (21:31); League 1 finished (21:30); Clef and Open-Jev stopped; Qwen3.8-27B on GPU 0 (21:34). GPU 2 handed back to compactor (bus #49).
- 22:36:37: **the GPU at PCI c1:00 (uuid bee4b5d4, index 1) fell off the bus** (kernel: Xid 79). The Gemma replica on it died; the matches of Gemma 4 31B (on) were deferred (502 from the proxy).
- 23:09: Qwen3.8-27B on GPU 0 died (`CUDA error: unknown error` allocating pinned memory). A restart on GPU 0 at 23:28 failed the same way: new CUDA processes do not start until the driver is reset. Reported to Main; compactor told on the bus (#51).
- 23:26: Claude Fable 5.1 (off) v LFM2.5-24B-A2B (on) finished; Oct 24 00:44 Liquid d1-ultra v LFM2.5 (on) finished. 01:09: LFM2.5 stopped, GPU 3 back to compactor (bus #52).
- Oct 24, 02:53: block 1 finished (last: Grok 4.7 (on) v GPT-6.1 Sol (low), slowed by xAI 503s).

## Moves (in v3.db: league-remove / league-add with their notes; freeze/league<N>-additions.json)

| Setup | From | To | Reason |
| --- | --- | --- | --- |
| Liquid d1-ultra | League 1 | League 2 | promoted |
| LFM2.5-24B-A2B (off) | League 2 | League 1 | relegated |
| GPT-6.1 Sol (low) | League 2 | League 3 | promoted |
| Claude Fable 5.1 (off) | League 3 | League 2 | relegated |

## Results (match ids 500-554; first-named setup's score first)

**League 3, GPT-6.1 Sol (low)** (9 of 9; 7 won): Astra (off) 1-5 Sol; Astra (on) 5-1 Sol; Sol 7-6 Opus (off); Opus (on) 5-3 Sol; Sol 8-1 Fable (on); Sol 4-3 Argon (off); Argon (on) 2-5 Sol; Grok (off) 1-5 Sol; Grok (on) 0-6 Sol.

**League 2, Claude Fable 5.1 (off)** (13 of 15; 7 won): Fable v Gemini 3.8 Flash (low) 1-5; v Sonnet 5.5 (high) 5-1; v Gemini 3.8 Flash (high) 4-5; Sonnet 5.5 (low) 1-5 Fable; Sol (high) 5-4 Fable; DeepSeek (off) 2-9 Fable; Fable 1-5 DeepSeek (on); GLM-5.3 (on) 4-3 Fable; Qwen3.8 Flash (off) 2-7 Fable; Liquid 1-5 Fable; Fable 7-0 LFM2.5 (on); Gemma 4 31B (off) 6-1 Fable; Qwen3.8-27B (off) 3-5 Fable. Pending: v Gemma 4 31B (on) (#551, 1-2), v Qwen3.8-27B (on) (#554, 0-0).

**League 2, Liquid d1-ultra** (12 of 14; 4 won): Gemini Flash (high) 5-1 Liquid; Liquid 3-4 Sonnet (high); Sonnet (low) 5-1 Liquid; Gemini Flash (low) 5-2 Liquid; Liquid 0-7 Sol (high); DeepSeek (off) 2-4 Liquid; Liquid 2-8 DeepSeek (on); GLM 5-4 Liquid; Qwen3.8 Flash 2-4 Liquid; Liquid 7-1 LFM2.5 (on); Liquid 2-5 Gemma (off); Liquid 5-1 Qwen3.8-27B (off). Pending: v Gemma 4 31B (on) (#522, 1-1), v Qwen3.8-27B (on) (#525, 0-0).

**League 1, LFM2.5-24B-A2B (off)** (17 of 17 incl. the reused GNUbg weak #338; 2 won): Random 1-6 LFM; Safest 5-3 LFM; LFM 2-9 Clef; Decider Flash v1.2 2-8 LFM; LFM 1-5 Fastino GLiDE; LFM 1-5 Celeris; LFM 0-7 Decider v1.1; LFM 0-5 Luna; Open-Jev 4-5 LFM; LFM 2-4 Cygnet; Jev 1.14.0 5-4 LFM; Jev 1.13.0 7-1 LFM; LFM 4-7 Decider v1.2 27B; LFM 2-4 SubQ; LFM 4-6 Winnow; LFM 0-6 Mercury; GLiDE v1.2 (local) 5-3 LFM.

## Spend

- API price (billed), from the stored turns: **$3.37**. OpenRouter $3.05 (DeepSeek V4.1 Flash (on) $2.32, GLM-5.3 $0.58, Qwen3.8 Flash $0.07, DeepSeek (off) $0.07, Mercury $0.01), matching the credit counter (used $60.95 before, $64.00 after; Can topped up to $75, $11.00 left). Liquid $0.21, GPT-6 Luna $0.03, SubQ $0.03, Jev $0.04, Celeris $0.01. Fastino GLiDE: no price recorded.
- API-equivalent of the subscription matches (not billed): about $185 (Claude Fable 5.1 (off) $97).

## GPU and device use

| Server | Where | Time (UTC) | Check |
| --- | --- | --- | --- |
| LFM2.5-24B-A2B (`LFM_GPU=3`) | bariton GPU 3 | Oct 23 21:15 - Oct 24 01:09 | same device type as before |
| Cygnet (`CYGNET_UTIL=0.34`) | bariton GPU 0 (spark busy with others' servers) | 21:11-21:19 | 20 stored requests: same play 20/20, max dp 0.055 |
| Fastino GLiDE v1.2 (`GLIDE_GPU=0`) | bariton GPU 0 | 21:12-21:19 | |
| Decider v1.2 27B + Flash, Winnow (`DECIDER_V12_GPU=1`, `WINNOW_GPU=1`) | bariton GPU 1 | 21:11-21:28 | |
| Decider v1.1 27B (`DECIDER_GPU=2`) | bariton GPU 2 | 21:12-21:19 | |
| Clef (`CLEF_GPU=0`) | bariton GPU 0 (spark busy) | 21:20-21:31 | 20 stored requests: same play 20/20, max dp 0.026 |
| Open-Jev 27B v1.1 (`OPEN_JEV_GPU=2`) | bariton GPU 2 | 21:20-21:31 | |
| Gemma 4 31B, one replica + proxy (`GEMMA_GPUS=1 GEMMA_MAX_SEQS=24`) | bariton GPU 1 | 21:31-22:36 (GPU lost) | |
| Qwen3.8-27B (`QWEN27_GPU=0`) | bariton GPU 0 | 21:34-23:09 (died) | |

Clef's and Cygnet's roster `base_url` now point to `127.0.0.1` (18091, 18093); device notes in v3.db record every change above. The Sparks run servers that are not ours (spark: `vllm_ds4_vision`; spark3: `qwen3.8-27b-sglang`, `gemma4-31b`); left untouched.

## Still to do

1. Reset or reboot bariton (GPU c1:00 is off the bus; GPU 0 no longer starts CUDA processes). Needs Can (compactor's jobs use the GPUs too).
2. Then claim 2 GPUs from compactor, start `GEMMA_GPUS=<n> GEMMA_MAX_SEQS=24 gemma4-31b-replicas.sh start` and `QWEN27_GPU=<m> qwen38-27b.sh start` (20-request check if the GPU differs in type), and let `league2` (still running, backing off) resume #522, #525, #551, #554 (about 5-7 h each, in parallel).
3. Then `tools/ladder.py plan` for round 2. A preview now would promote GPT-6.1 Sol (high) (39 pts) from League 2, but Gemma 4 31B (on) (36 pts) still has 2 matches and could pass it.
