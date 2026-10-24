# Reviewed backgammon brief (handoff ZEKI-HANDOFF-1563450109356806227-BG): status

## Acknowledgement (Oct 24, 07:30 UTC)

- Marker `ZEKI-HANDOFF-1563450109356806227-BG` received.
- Brief read in full: `BG-brief.md`, 117 lines, SHA256 `48793261cc49c937cd7888e20f270ad5a60866fe965365d4f6afd2dedc46dcb3` (matches the handoff).
- Authorization as stated in the handoff: Ümit's Discord message `1563352977106796575`; Can resumed pending work in `1563450109356806227`.

## Queued, not started

Work starts after the current job finishes: League 2's last 4 ladder round-1 matches (Gemma 4 31B (on) and Qwen3.8-27B (on) against Liquid d1-ultra and Claude Fable 5.1 (off)), still running on bariton GPUs 0 and 1. Those matches are not interrupted, and only one writer at a time uses `v3.db`.

## Gates kept

- No league match for Liquid d1.1 or Kimi K3.1 Pro (off) before the smoke rows and Kimi's measured cost projection are in this folder.
- Kimi: one $30 hard cap at list prices, covering smoke tests, retries, (off)'s League 3 games and (on)'s 200 fixed positions. Kimi (on) is first-look only, never in a league.
- No model server is started, stopped or reconfigured on bariton or the Sparks.
- Site changes (title and subtitle, Risk tab, ability and caution, Confidence tab, Method) are built and reported here first; nothing is published without approval. The live site's update loop deploys whatever is on `main`, so this work stays on a branch until approval.
- This brief doesn't settle the other pending questions (findings, computed reference rows, hero, ladder round 2).

## Milestones

Reported below as each part is done.
