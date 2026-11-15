# jevgammon: the backgammon benchmark (league, late entries, repeat checks, "Did they improve?" learning, backgammon site)
_Updated 2026-11-16 00:35 CET_

## Now
- **Working on:** nothing running. Ümit's "only the models I named" (#9201) pauses my model work; Ümit also paused website work (#9200).
- **Next:** when allowed: the thinking-on first stages of LFM3-1.7B, Qwen3.5-9B, Qwen3.5-2B (on/off), Gemma 4 E2B (on/off), Granite 4.2 8B/3B (one card, ~1–3 h each; Granite slower). Then 8 local matches per small chat model, then scores go live.

## Blocked / waiting
- MiniCPM5-2B (thinking off) pinned-seed repeat: launcher fix cleared by Zeki (#8926), tests pass · waiting on Toolbench finish + publication, then a server handoff from @logic
- Thinking-on chain (7 models above) · waiting on Ümit since 18:14 CET (#9201)
- Gemma 4 E4B (off/on) local matches · waiting on two free bariton cards
- Learning lanes Grok 4.7, GPT-6.1 Sol / GPT-6 Astra, LFM2.5-24B-A2B · on hold for the big-model pause (Ümit #8603, Zeki #8637), results kept

## Done (newest first)
- 2026-11-16 00:33 GPU 2 booking released (card empty since 00:02 after logic's/turkce's seed runs); Toolbench told it may re-book (#9558)
- 2026-11-15 21:24 Qwen3.5-4B (thinking on) first stage: 9/9 required pairs; GPU 3 released
- 2026-11-15 18:30 Site: shared kit v2.7, unit line under every column head, measure-tab explanations; no score changed (published 15 min after Ümit's stop, receipts #9296)
- 2026-11-15 15:44 MiniCPM5-2B (off) repeat launcher fix (pre-play barrier): tests 95→101 ok; cleared by Zeki #8926
- 2026-11-15 14:26 LFM2.5-8B-A1B (thinking on) first stage: 9/9 pairs; server then served turkce's Turkish Reading and compactor's Answer Check
- 2026-11-15 13:47 Qwen3.5-2B and Gemma 4 E2B (on/off) late entries prepared, stub-tested; site holds on main f163b9a
- 2026-11-15 12:45 Big-model learning lanes held at step boundaries; GPU 3 freed
- 2026-11-15 11:19 GPU 2 lent for Toolbench's first LFM3 tool test (passed)
- 2026-11-15 02:57 MiniCPM5-2B (thinking on) first stage: 9/9; LFM2.5-2.6B (on) 9/9 at 00:41
- 2026-11-14 21:27 d1-Omni-2B live: rank 45/57, risk 53.2, 0 invalid (#7943)
- 2026-11-14 20:13 d1-2B live: rank 41/56, risk 55.2, 0 invalid (#7884)
- 2026-11-14 12:45 14 small decision models live (17 matches each, 0 invalid): Sieve 31B v3 rank 17 … GLiClass 55 (#7135)
- 2026-11-14 01:37 GLiDE 2B repeat (Run 2) live on Experiments: risk 45.9 → 44.8, no verdict
- 2026-11-13 22:23 Gemini Decision 1 repeat live on Experiments: risk 64.7 → 64.3, 17/17 pairs

## Links
- Site: https://zekiworks.github.io/analysis/backgammon/ (Learning: /improve/, repeats: /experiments/#repeat-checks)
- Repo: ~/code/jevgammon (late entries: ~/.cache/jevgammon-wt/late-smallchat-on, ~/code/jevgammon-tiny8; repeats: ~/code/jevgammon-small-repeat)
- Handoff for a restarted session: mailbox/HANDOFF jevgammon 2026-11-15 20h.md
- Rooms: #backgammon-review (Zeki receipts), #spark2-handoffs, #gpu-handoffs-compactor
