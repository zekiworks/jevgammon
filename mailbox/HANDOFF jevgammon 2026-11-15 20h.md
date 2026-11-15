# jevgammon state, 15 Nov 2026 ~19:15 UTC (for a restarted session)

## Running (all systemd, survive a session restart)
- GPU 3, booking r_29f4c003a973 (to 03:46 UTC 16 Nov): Qwen3.5-4B (on) backgammon first stage, units `late-smallchat-qwen3.5-4b-on(-league)`, server = logic's `small_models.py serve qwen3.5-4b` container.
  - `stage-done-watch-qwen.service` stops both units at 9 required pairs, then stops the server. After it ends: append "first stage done" to `mailbox/Late entries smallchat - qwen3.5-4b-on - status.md`, commit that file by name, push, and RELEASE r_29f4c003a973 (card then idle).
- GPU 2, booking r_265f5494128e (ends 23:39 UTC 15 Nov): lent to logic (MiniCPM5-2B thinking-off seeds) then turkce (English seeds + run 1299). Release it ONLY when toolbench posts 'ready' (Toolbench's queued r_8f72ee288455 would otherwise start its 90 min). If logic/turkce are still on it near 23:39, extend it.
- Learning lanes all on hold (hold.json in workspace/improve/runs/*): Ümit #8603/Zeki #8637. Don't restart.

## Paused by Ümit #9200/#9201 ("only the models I named", "stop the website")
- No backgammon site work.
- Thinking-on chain (`workspace/on-chain.sh`, GPU=3) NOT to be restarted until Ümit allows: remaining lfm3-1.7b-vllm:lfm3-1.7b-on qwen3.5-9b:qwen3.5-9b-on qwen3.5-2b:qwen3.5-2b-on qwen3.5-2b-nothink:qwen3.5-2b-off gemma-4-e2b-it:gemma-4-e2b-on gemma-4-e2b-it:gemma-4-e2b-off granite-4.2-8b (turkce English hold after) granite-4.2-3b. Live tree late-smallchat-on = ac16de1, runner sha 81bd4548.
  - Before a test, move any stale ~/.cache/smallchat/test/<key> dir aside (old failed answers.db makes test.sh report a stale failure).
- Thinking-on first stages done today: MiniCPM5-2B, LFM2.5-2.6B, LFM2.5-8B-A1B (need 8 local matches before scoring). Spark-X2.6-4B (on) stopped as too slow; Granite 4.2 3B (on) paused, both resume later on same pins.

## Ready, waiting
- MiniCPM5-2B (off) pinned-seed repeat: `~/code/jevgammon-small-repeat` small-repeat = 34f4337 (Zeki released SR1 #8926, tests ALL PASSED). Starts only after Toolbench finishes+publishes and a MiniCPM5-2B thinking-off server is handed over. Send Zeki start + final 9-pair receipts. Six opponents are paid APIs.
- Gemma 4 E4B (off/on) local matches: need two free bariton cards.

## Never
- `git add mailbox` (untracked 384 MB tarball). Stage files by name.
- Touch uncommitted src/*.rs in the main checkout (not ours).
