# Night run, 22–23 Oct 2026: League 1 and League 2 finished

Both leagues are finished, all bariton servers are stopped, and the release was posted to compactor at 02:53 UTC. The public page (https://zekiworks.github.io/analysis/backgammon/) shows data as of 23 Oct 02:50 UTC and says: "League 1 has finished; League 2 has finished; League 3 has finished".

## Timeline (UTC)

- 22:19: compactor's release (bus #35). GPUs 0–3 empty in `nvidia-smi`. OpenRouter credit $6.01.
- Spark checks: Clef and Cygnet (spark) answered. Decider v1.1 (spark3) was down: it was OOM-killed at 19:34. It could not restart because a docker container `glide` (vLLM `v0.30.0`, `glide.server`, port 8888, started 19:54, not ours) holds about 56 GB of spark3's memory. I left that container alone and asked on the bus whose it is (#36); nobody has answered.
- 22:21: bariton servers started with the same scripts and arguments:
  - GLiDE v1.2 on GPU 0
  - Decider v1.2 27B, Decider Flash v1.2 and Winnow-12B on GPU 1
  - Open-Jev on GPU 2
  - LFM2.5-24B-A2B on GPU 3 (ready 22:23)

  League 1 resumed at 22:21:54.
- 22:23:52: League 2 resumed. The LFM matches (#311, #348) played; Gemma's match (#349) backed off until Gemma was up.
- 22:40: Open-Jev's only match ended (Open-Jev 2–5 GLiDE v1.2). I stopped Open-Jev and started Decider v1.1 on bariton GPU 2 (`DECIDER_GPU=2 ./decider.sh start`), with the same checkpoint and arguments it used on bariton before 16 Oct.
  - Replay check, 20 stored League 1 requests (`/tmp/decider_equiv.py`): same play in 19/20, max |dp| 0.017, median 0.008, median latency 0.65 s. 19/20 is within the one-in-20 rule.
  - I set the roster `base_url` to `http://127.0.0.1:18097` and updated the device note.
- 22:46–22:51: restarted League 1 so it would read the new URL.
  - SIGINT cancelled the matches, but the runner kept retrying Decider's warm-up against spark3 and did not exit, so I sent SIGTERM.
  - The first new start at 22:48:51 exited at once ("league #1 is being played by another process": the old heartbeat was still fresh).
  - It resumed at 22:51:05.
- 22:55: League 1 finished (19 entrants, 171 matches).
- 22:57: bariton servers stopped (GLiDE, Decider v1.1, Decider v1.2 27B/Flash, Winnow), and so were the Spark servers (Clef, Cygnet).
- 22:57–22:59: Gemma 4 31B started on GPUs 0 and 1 with the same command as at 15:37: two replicas behind the least-busy proxy on :8894, `GEMMA_MAX_SEQS=24`. I didn't run the 20-request check (same server, arguments and GPU type).
  - Gemma's back-off kept #349 waiting until 23:27, then it resumed.
- 00:05: #311 finished: DeepSeek V4.1 Flash (off) 2–6 LFM2.5-24B-A2B (on).
- 00:07: #348 finished: DeepSeek V4.1 Flash (on) 6–0 LFM2.5-24B-A2B (on).
- 02:50: #349 finished: Gemma 4 31B (on) 1–7 DeepSeek V4.1 Flash (on). League 2 finished.
- 02:52: Gemma replicas, proxy and LFM2.5 stopped; no processes left on the GPUs. Pages refreshed with `v3-page-refresh.service`.
- 02:53: release posted to compactor on the bus (#37).

## Final standings, top 5

League 1 (decision models; P W D L Pts):

1. Liquid d1-ultra: 18 16 0 2 48
2. GNUbg weak: 18 16 0 2 48
3. Fastino GLiDE: 18 12 1 5 37
4. Decider v1.2 27B: 18 12 0 6 36
5. Jev 1.14.0: 18 12 0 6 36

Fastino GLiDE v1.2 (local) finished 10th: 10 wins, 8 losses, 30 points. Its match list is in `mailbox/GLiDE v1.2 - log.md`.

League 2 (workhorse chat models; 136 matches):

1. GPT-6.1 Sol (low): 16 15 0 1 45
2. Gemma 4 31B (on): 16 12 0 4 36
3. GPT-6.1 Sol (high): 16 12 0 4 36
4. Gemini 3.8 Flash (low): 16 11 1 4 34
5. Claude Sonnet 5.5 (high): 16 11 0 5 33

## Spend

- OpenRouter usage went from $58.99 to $60.95, so tonight cost **$1.96**, all of it DeepSeek V4.1 Flash on Fireworks. That is 157 decisions to 01:01 with `provider = openrouter:fireworks`, plus the rest of #349.
- Credit left: $4.05.

## Records

- Roster device notes in `v3.db` now include tonight's server start times and GPUs for these players: GLiDE v1.2, Open-Jev, Decider v1.2 27B/Flash, Winnow, Decider v1.1 (move to bariton, check result, stop time), LFM2.5 (off/on) and Gemma 4 31B (off/on).
- Per-decision `provider` is recorded as before: `local-vllm` for Gemma and LFM, `openrouter:fireworks` for DeepSeek.

## Issues

- **spark3:** the unknown `glide` container (see 22:21 above) is still running. Decider v1.1's spark3 server is stopped.
- **League 1 restart:** `systemctl kill -s SIGINT` does not end the runner while a player's warm-up keeps failing; a SIGTERM was needed. The league runner code is unchanged.
- **`leagues/league1.json`** still lists Decider v1.1 at spark3's URL. `--resume` uses the roster in `v3.db`.
- **Slow last match:** #349 took about 3.5 h after Gemma came back. Gemma decisions with thinking sometimes took 200–1,400 s.
- **Unattended service:** `v3-page-refresh.timer` shows as `not-found failed`. The page refresh still ran by hand, and the preview timer (`bg-site-preview.timer`) is active.
